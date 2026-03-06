"""Tests for the _data_utils module (data serialization helpers).

Tests cover:
- _serialise_data() for DataFrame/GeoDataFrame conversion
- encode_binary_attribute() for numpy array encoding
- Edge cases and error handling
"""
from __future__ import annotations

import base64
import json

import pytest

from shiny_deckgl._data_utils import _serialise_data, encode_binary_attribute


# ---------------------------------------------------------------------------
# Test _serialise_data function
# ---------------------------------------------------------------------------

class TestSerialiseData:
    """Tests for the _serialise_data function."""

    def test_list_passthrough(self):
        """Plain list should pass through unchanged."""
        data = [{"x": 1}, {"x": 2}]
        result = _serialise_data(data)
        assert result is data  # Same object

    def test_dict_passthrough(self):
        """Plain dict should pass through unchanged."""
        data = {"type": "FeatureCollection", "features": []}
        result = _serialise_data(data)
        assert result is data

    def test_string_passthrough(self):
        """String should pass through unchanged."""
        data = "https://example.com/data.json"
        result = _serialise_data(data)
        assert result is data

    def test_none_passthrough(self):
        """None should pass through unchanged."""
        result = _serialise_data(None)
        assert result is None

    def test_number_passthrough(self):
        """Number should pass through unchanged."""
        result = _serialise_data(42)
        assert result == 42

    @pytest.mark.skipif(
        pytest.importorskip("pandas", reason="pandas not installed") is None,
        reason="pandas not installed"
    )
    def test_dataframe_to_records(self):
        """DataFrame should convert to list of dicts."""
        import pandas as pd
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        result = _serialise_data(df)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == {"x": 1, "y": 4}

    @pytest.mark.skipif(
        pytest.importorskip("pandas", reason="pandas not installed") is None,
        reason="pandas not installed"
    )
    def test_dataframe_empty(self):
        """Empty DataFrame should convert to empty list."""
        import pandas as pd
        df = pd.DataFrame()
        result = _serialise_data(df)
        assert result == []

    @pytest.mark.skipif(
        pytest.importorskip("pandas", reason="pandas not installed") is None,
        reason="pandas not installed"
    )
    def test_dataframe_with_nan(self):
        """DataFrame with NaN should convert (NaN becomes None in JSON)."""
        import pandas as pd
        import numpy as np
        df = pd.DataFrame({"x": [1, np.nan, 3]})
        result = _serialise_data(df)
        assert len(result) == 3
        # NaN in pandas becomes None when converted to dict
        assert result[1]["x"] is None or (isinstance(result[1]["x"], float) and result[1]["x"] != result[1]["x"])

    @pytest.mark.skipif(
        pytest.importorskip("geopandas", reason="geopandas not installed") is None,
        reason="geopandas not installed"
    )
    def test_geodataframe_to_geojson(self):
        """GeoDataFrame should convert to GeoJSON dict."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {"name": ["A", "B"]},
            geometry=[Point(0, 0), Point(1, 1)],
            crs="EPSG:4326"
        )
        result = _serialise_data(gdf)
        assert isinstance(result, dict)
        assert result["type"] == "FeatureCollection"
        assert "features" in result
        assert len(result["features"]) == 2

    @pytest.mark.skipif(
        pytest.importorskip("geopandas", reason="geopandas not installed") is None,
        reason="geopandas not installed"
    )
    def test_geodataframe_properties_preserved(self):
        """GeoDataFrame properties should be in GeoJSON features."""
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            {"name": ["Point A"], "value": [42]},
            geometry=[Point(10, 20)],
        )
        result = _serialise_data(gdf)
        props = result["features"][0]["properties"]
        assert props["name"] == "Point A"
        assert props["value"] == 42

    def test_json_serializable_output(self):
        """Output should always be JSON-serializable."""
        # Test with various inputs
        test_cases = [
            [{"x": 1}],
            {"key": "value"},
            None,
            "string",
            42,
            3.14,
            True,
        ]
        for data in test_cases:
            result = _serialise_data(data)
            # Should not raise
            json.dumps(result)


# ---------------------------------------------------------------------------
# Test encode_binary_attribute function
# ---------------------------------------------------------------------------

class TestEncodeBinaryAttribute:
    """Tests for the encode_binary_attribute function."""

    @pytest.fixture
    def numpy(self):
        """Import numpy or skip test."""
        return pytest.importorskip("numpy")

    def test_float32_encoding(self, numpy):
        """Float32 array should encode correctly."""
        arr = numpy.array([1.0, 2.0, 3.0], dtype="float32")
        result = encode_binary_attribute(arr)

        assert result["@@binary"] is True
        assert result["dtype"] == "float32"
        assert result["size"] == 1
        assert isinstance(result["value"], str)

    def test_float64_encoding(self, numpy):
        """Float64 array should encode correctly."""
        arr = numpy.array([1.0, 2.0, 3.0], dtype="float64")
        result = encode_binary_attribute(arr)

        assert result["@@binary"] is True
        assert result["dtype"] == "float64"

    def test_2d_array_size(self, numpy):
        """2D array should have correct size (number of columns)."""
        arr = numpy.array([[1, 2], [3, 4], [5, 6]], dtype="float32")
        result = encode_binary_attribute(arr)

        assert result["size"] == 2  # 2 columns

    def test_3d_positions(self, numpy):
        """3D positions [x, y, z] should have size=3."""
        arr = numpy.array([[1, 2, 3], [4, 5, 6]], dtype="float32")
        result = encode_binary_attribute(arr)

        assert result["size"] == 3

    def test_roundtrip_decode(self, numpy):
        """Encoded data should decode back to original values."""
        original = numpy.array([1.5, 2.5, 3.5], dtype="float32")
        result = encode_binary_attribute(original)

        # Decode
        decoded_bytes = base64.b64decode(result["value"])
        decoded = numpy.frombuffer(decoded_bytes, dtype="float32")

        numpy.testing.assert_array_equal(decoded, original)

    def test_2d_roundtrip(self, numpy):
        """2D array should roundtrip correctly."""
        original = numpy.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32")
        result = encode_binary_attribute(original)

        decoded_bytes = base64.b64decode(result["value"])
        decoded = numpy.frombuffer(decoded_bytes, dtype="float32").reshape(original.shape)

        numpy.testing.assert_array_equal(decoded, original)

    def test_int_array_converted_to_float32(self, numpy):
        """Integer array should be converted to float32."""
        arr = numpy.array([1, 2, 3], dtype="int64")
        result = encode_binary_attribute(arr)

        assert result["dtype"] == "float32"

    def test_uint8_preserved(self, numpy):
        """uint8 array should be preserved (common for colors)."""
        arr = numpy.array([255, 128, 0], dtype="uint8")
        result = encode_binary_attribute(arr)

        assert result["dtype"] == "uint8"

    def test_int32_preserved(self, numpy):
        """int32 array should be preserved."""
        arr = numpy.array([1, 2, 3], dtype="int32")
        result = encode_binary_attribute(arr)

        assert result["dtype"] == "int32"

    def test_empty_array(self, numpy):
        """Empty array should encode (edge case)."""
        arr = numpy.array([], dtype="float32")
        result = encode_binary_attribute(arr)

        assert result["@@binary"] is True
        assert result["value"] == ""  # Empty base64

    def test_large_array(self, numpy):
        """Large array should encode without issues."""
        arr = numpy.random.rand(10000, 3).astype("float32")
        result = encode_binary_attribute(arr)

        assert result["@@binary"] is True
        assert result["size"] == 3
        # Verify it's valid base64
        decoded = base64.b64decode(result["value"])
        assert len(decoded) == arr.nbytes

    def test_json_serializable(self, numpy):
        """Output should be JSON-serializable."""
        arr = numpy.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32")
        result = encode_binary_attribute(arr)

        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_non_contiguous_array(self, numpy):
        """Non-contiguous array should be handled (made contiguous)."""
        arr = numpy.array([[1, 2, 3], [4, 5, 6]], dtype="float32")
        # Transpose creates non-contiguous array
        transposed = arr.T
        assert not transposed.flags["C_CONTIGUOUS"]

        result = encode_binary_attribute(transposed)

        # Should still work
        assert result["@@binary"] is True


# ---------------------------------------------------------------------------
# Edge cases for data serialization
# ---------------------------------------------------------------------------

class TestDataSerializationEdgeCases:
    """Edge case tests for data serialization."""

    def test_nested_dict(self):
        """Nested dict should pass through."""
        data = {"outer": {"inner": {"deep": [1, 2, 3]}}}
        result = _serialise_data(data)
        assert result is data

    def test_mixed_list(self):
        """List with mixed types should pass through."""
        data = [1, "two", 3.0, None, True]
        result = _serialise_data(data)
        assert result is data

    def test_custom_class_passthrough(self):
        """Custom class without DataFrame interface should pass through."""
        class CustomData:
            def __init__(self):
                self.value = 42

        data = CustomData()
        result = _serialise_data(data)
        assert result is data

    @pytest.mark.skipif(
        pytest.importorskip("pandas", reason="pandas not installed") is None,
        reason="pandas not installed"
    )
    def test_dataframe_subclass(self):
        """DataFrame subclass should be detected via MRO."""
        import pandas as pd

        class CustomDF(pd.DataFrame):
            pass

        df = CustomDF({"x": [1, 2, 3]})
        result = _serialise_data(df)

        # Should use DataFrame path
        assert isinstance(result, list)
        assert result[0] == {"x": 1}
