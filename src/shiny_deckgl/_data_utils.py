"""Data serialisation helpers (DataFrame / GeoDataFrame → JSON-safe)."""

from __future__ import annotations

import base64
import datetime
import math
import warnings
from decimal import Decimal
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np  # noqa: F401 — type-checking only

__all__ = ["encode_binary_attribute"]


def json_safe(obj: Any) -> Any:
    """Recursively convert *obj* into values the standard ``json`` module accepts.

    - Non-finite floats (``NaN``/``inf``) become ``None``.  ``json.dumps``
      would emit the non-standard ``NaN``/``Infinity`` tokens, which strict
      ``JSON.parse`` consumers (the browser, the HTML export) reject.
    - numpy scalars and arrays become Python numbers and lists.
    - Dates and times (``datetime``, ``pandas.Timestamp``, ``numpy.datetime64``)
      become ISO-8601 strings; durations become seconds.
    - Missing markers (``pandas.NaT``, ``pandas.NA``, ``numpy`` NaT) become
      ``None``; ``Decimal`` becomes ``float``; pandas ``Series``/``Index``
      become lists.

    Shiny serialises custom messages with ``json.dumps``, so any of these
    left in a payload raises ``TypeError`` and closes the session.
    """
    # Most frequent types first: this walks every element of large payloads.
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if obj is None or isinstance(obj, (str, int)):
        return obj
    return _json_safe_scalar(obj)


def _json_safe_scalar(obj: Any) -> Any:
    """Handle the non-builtin types of :func:`json_safe` (numpy, pandas, dates)."""
    cls = type(obj)
    if cls.__name__ in ("NaTType", "NAType"):
        return None
    module = cls.__module__.split(".")[0]
    if module == "numpy":
        kind = getattr(getattr(obj, "dtype", None), "kind", "")
        if getattr(obj, "ndim", 0):
            # datetime/timedelta arrays: .tolist() would give raw integers
            # at ns precision, so convert element by element instead.
            if kind in "mM":
                return [json_safe(v) for v in obj]
            return json_safe(obj.tolist())
        if kind == "M":
            import numpy as np  # noqa: local import — numpy is optional
            return None if np.isnat(obj) else str(obj)
        if kind == "m":
            import numpy as np  # noqa: local import — numpy is optional
            return None if np.isnat(obj) else float(obj / np.timedelta64(1, "s"))
        if hasattr(obj, "item"):
            return json_safe(obj.item())
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, datetime.timedelta):
        return obj.total_seconds()
    if isinstance(obj, Decimal):
        return json_safe(float(obj))
    if module == "pandas" and hasattr(obj, "tolist"):
        return json_safe(obj.tolist())
    return obj


def _geo_to_lon_lat(gdf: Any) -> Any:
    """Return *gdf* in EPSG:4326, which is what deck.gl and MapLibre expect.

    A frame in a projected CRS (UTM, LKS94, ...) is reprojected; the caller's
    frame is not modified.  A frame with no CRS is returned as-is, with a
    warning when its coordinates cannot be longitude/latitude.
    """
    crs = gdf.crs
    if crs is None:
        if len(gdf):
            bounds = gdf.total_bounds
            if all(math.isfinite(b) for b in bounds) and (
                max(abs(bounds[0]), abs(bounds[2])) > 180
                or max(abs(bounds[1]), abs(bounds[3])) > 90
            ):
                warnings.warn(
                    "GeoDataFrame has no CRS and its coordinates are outside "
                    "the longitude/latitude range, so it will not appear on "
                    "the map. Set its CRS (e.g. gdf.set_crs(3346) for LKS94) "
                    "so it can be reprojected to EPSG:4326.",
                    UserWarning,
                    stacklevel=4,
                )
        return gdf
    if crs.equals("EPSG:4326", ignore_axis_order=True):
        return gdf
    return gdf.to_crs(4326)


def _serialise_data(data: Any) -> Any:
    """Convert pandas/geopandas objects to JSON-safe structures.

    - ``GeoDataFrame`` (or subclasses) → GeoJSON ``FeatureCollection`` dict,
      reprojected to EPSG:4326 first when it has another CRS
    - ``DataFrame`` (or subclasses) → list of row-dicts
    - Everything else is returned unchanged.

    .. warning::
       The conversion is unconditional and independent of the target layer.
       A ``GeoDataFrame`` always becomes a ``FeatureCollection`` **dict**,
       which only ``GeoJsonLayer`` consumes — passing one to an array-accessor
       layer (e.g. ``scatterplot_layer`` with the default ``getPosition="@@d"``)
       renders nothing.  A plain ``DataFrame`` becomes row-dicts, so array
       accessors like ``getPosition="@@d"`` must be overridden with a property
       accessor (``"@@d.<col>"``).
    """
    # Check class names in the MRO so subclasses are handled without
    # importing pandas/geopandas (which are optional dependencies).
    mro_names = {cls.__name__ for cls in type(data).__mro__}
    if "GeoDataFrame" in mro_names:
        # __geo_interface__ is always present on GeoDataFrame; the old
        # json.loads(data.to_json()) fallback serialised the entire
        # frame to a string only to immediately deserialise it back —
        # a significant memory and CPU bottleneck for large datasets.
        return _geo_to_lon_lat(data).__geo_interface__
    if "DataFrame" in mro_names:
        return data.to_dict(orient="records")
    return data


def encode_binary_attribute(array: "np.ndarray") -> dict:
    """Encode a numpy array as a base64 binary transport dict.

    deck.gl supports `binary attributes
    <https://deck.gl/docs/developer-guide/performance#supply-attributes-directly>`_
    for large datasets.  This helper converts a numpy array into a dict
    that the JS client decodes into a typed-array attribute.

    Parameters
    ----------
    array
        A ``numpy.ndarray``.  Supported dtypes: ``float32``, ``float64``,
        ``uint8``, ``int32``, ``uint32``.  Other dtypes are silently
        coerced to ``float32``.

    Returns
    -------
    dict
        ``{"@@binary": True, "dtype": "float32", "size": <n_components>,
        "value": "<base64>"}``

    Example
    -------
    >>> import numpy as np
    >>> positions = np.array([[0.0, 51.5], [10.0, 48.8]], dtype="float32")
    >>> layer("ScatterplotLayer", "pts",
    ...       data={"length": len(positions)},
    ...       getPosition=encode_binary_attribute(positions))

    Raises
    ------
    TypeError
        If `array` is not a numpy ndarray.
    """
    # Reject obvious non-ndarrays *before* importing numpy, so a bad input
    # raises the documented TypeError even when numpy is not installed.
    if type(array).__module__.split(".")[0] != "numpy":
        raise TypeError(
            f"encode_binary_attribute() expects numpy.ndarray, got {type(array).__name__}"
        )

    import numpy as np  # noqa: local import — numpy is optional

    if not isinstance(array, np.ndarray):
        raise TypeError(
            f"encode_binary_attribute() expects numpy.ndarray, got {type(array).__name__}"
        )

    arr = np.ascontiguousarray(array)
    dtype_str = str(arr.dtype)
    SUPPORTED_DTYPES = ("float32", "float64", "uint8", "int32", "uint32")
    if dtype_str not in SUPPORTED_DTYPES:
        arr = arr.astype("float32", copy=False)
        dtype_str = "float32"
    encoded = base64.b64encode(arr.tobytes()).decode("ascii")
    size = arr.shape[1] if arr.ndim > 1 else 1
    return {
        "@@binary": True,
        "dtype": dtype_str,
        "size": size,
        "value": encoded,
    }
