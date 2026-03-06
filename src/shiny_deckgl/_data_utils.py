"""Data serialisation helpers (DataFrame / GeoDataFrame → JSON-safe)."""

from __future__ import annotations

import base64
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np  # noqa: F401 — type-checking only

__all__ = ["encode_binary_attribute"]


def _serialise_data(data: Any) -> Any:
    """Convert pandas/geopandas objects to JSON-safe structures.

    - ``GeoDataFrame`` (or subclasses) → GeoJSON ``FeatureCollection`` dict
    - ``DataFrame`` (or subclasses) → list of row-dicts
    - Everything else is returned unchanged.
    """
    # Check class names in the MRO so subclasses are handled without
    # importing pandas/geopandas (which are optional dependencies).
    mro_names = {cls.__name__ for cls in type(data).__mro__}
    if "GeoDataFrame" in mro_names:
        # __geo_interface__ is always present on GeoDataFrame; the old
        # json.loads(data.to_json()) fallback serialised the entire
        # frame to a string only to immediately deserialise it back —
        # a significant memory and CPU bottleneck for large datasets.
        return data.__geo_interface__
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
        A ``numpy.ndarray`` (float32 or float64).

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
    import numpy as np  # noqa: local import — numpy is optional

    if not isinstance(array, np.ndarray):
        raise TypeError(
            f"encode_binary_attribute() expects numpy.ndarray, got {type(array).__name__}"
        )

    arr = np.ascontiguousarray(array)
    dtype_str = str(arr.dtype)
    if dtype_str not in ("float32", "float64", "uint8", "int32"):
        # astype always copies; ascontiguousarray above already
        # ensured C-contiguity, so replace arr in-place reference.
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
