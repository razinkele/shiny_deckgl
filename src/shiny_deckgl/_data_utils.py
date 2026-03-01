"""Data serialisation helpers (DataFrame / GeoDataFrame → JSON-safe)."""

from __future__ import annotations

import base64
import json
from typing import Any


def _serialise_data(data: Any) -> Any:
    """Convert pandas/geopandas objects to JSON-safe structures.

    - ``GeoDataFrame`` → GeoJSON ``FeatureCollection`` dict
    - ``DataFrame`` → list of row-dicts
    - Everything else is returned unchanged.
    """
    type_name = type(data).__name__
    if type_name == "GeoDataFrame":
        if hasattr(data, "__geo_interface__"):
            return data.__geo_interface__
        return json.loads(data.to_json())
    if type_name == "DataFrame":
        return data.to_dict(orient="records")
    return data


def encode_binary_attribute(array) -> dict:
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
    """
    import numpy as np  # noqa: local import — numpy is optional

    arr = np.ascontiguousarray(array)
    dtype_str = str(arr.dtype)
    if dtype_str not in ("float32", "float64", "uint8", "int32"):
        arr = arr.astype("float32")
        dtype_str = "float32"
    encoded = base64.b64encode(arr.tobytes()).decode("ascii")
    size = arr.shape[1] if arr.ndim > 1 else 1
    return {
        "@@binary": True,
        "dtype": dtype_str,
        "size": size,
        "value": encoded,
    }
