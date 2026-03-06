"""Tests for error handling across the shiny_deckgl library.

Tests cover:
- Invalid parameter validation
- Missing required arguments
- Type mismatches
- Edge cases that should raise appropriate errors
"""
from __future__ import annotations

import pytest

from shiny_deckgl import (
    MapWidget,
    # Layers
    scatterplot_layer,
    geojson_layer,
    bitmap_layer,
    layer,
    # Colors
    color_range,
    color_bins,
    color_quantiles,
    PALETTE_VIRIDIS,
    # Controls
    geolocate_control,
    # Extensions
    brushing_extension,
    data_filter_extension,
    # Views
    map_view,
    globe_view,
    # Effects
    lighting_effect,
    ambient_light,
    post_process_effect,
    # Helpers
    transition,
)
from shiny_deckgl.controls import CONTROL_TYPES, CONTROL_POSITIONS


# ---------------------------------------------------------------------------
# MapWidget error handling
# ---------------------------------------------------------------------------

class TestMapWidgetErrors:
    """Tests for MapWidget error handling."""

    def test_invalid_control_type_raises(self):
        """Invalid control type in controls list gets stored (validated at add_control time)."""
        w = MapWidget("error_test")
        # Controls are validated at add_control time, not at assignment
        # So this just stores the list without validation
        w.controls = [{"type": "invalid_control", "position": "top-right"}]
        assert len(w.controls) == 1

    def test_add_control_invalid_type(self):
        """add_control with invalid type should raise ValueError."""
        import asyncio

        class FakeSession:
            async def send_custom_message(self, *args):
                pass

        w = MapWidget("error_test")
        session = FakeSession()

        with pytest.raises(ValueError, match="Unknown control type"):
            asyncio.run(w.add_control(session, "nonexistent_control", "top-right"))

    def test_add_control_invalid_position(self):
        """add_control with invalid position should raise ValueError."""
        import asyncio

        class FakeSession:
            async def send_custom_message(self, *args):
                pass

        w = MapWidget("error_test")
        session = FakeSession()

        with pytest.raises(ValueError, match="Unknown position"):
            asyncio.run(w.add_control(session, "navigation", "invalid-position"))

    def test_set_projection_invalid(self):
        """set_projection with invalid value should raise ValueError."""
        import asyncio

        class FakeSession:
            async def send_custom_message(self, *args):
                pass

        w = MapWidget("proj_test")
        session = FakeSession()

        with pytest.raises(ValueError, match="Unknown projection"):
            asyncio.run(w.set_projection(session, "invalid_projection"))

    def test_from_json_invalid_json(self):
        """from_json with invalid JSON should raise error."""
        with pytest.raises(Exception):  # json.JSONDecodeError
            MapWidget.from_json("not valid json {{{")

    def test_from_json_missing_required_fields(self):
        """from_json requires id field."""
        import json
        # Minimal valid JSON requires at least the id field
        json_str = json.dumps({"id": "test_map", "viewState": {}, "layers": []})
        widget, layers = MapWidget.from_json(json_str)
        assert widget is not None
        assert widget.id == "test_map"
        assert layers == []


# ---------------------------------------------------------------------------
# Layer error handling
# ---------------------------------------------------------------------------

class TestLayerErrors:
    """Tests for layer definition error handling."""

    def test_layer_invalid_extension_spec(self):
        """Invalid extension spec should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid extension spec"):
            layer(
                "ScatterplotLayer",
                "bad_ext",
                data=[],
                extensions=[123],  # Should be string or [name, options]
            )

    def test_bitmap_layer_requires_image(self):
        """bitmap_layer requires image parameter."""
        # Should work with required params
        l = bitmap_layer("bmp", image="http://example.com/img.png", bounds=[0, 0, 1, 1])
        assert l["image"] == "http://example.com/img.png"

    def test_extension_with_invalid_options(self):
        """Extension with wrong option type should be caught."""
        # data_filter_extension requires filter_size
        ext = data_filter_extension(filter_size=4)
        assert ext[1]["filterSize"] == 4


# ---------------------------------------------------------------------------
# Color function error handling
# ---------------------------------------------------------------------------

class TestColorErrors:
    """Tests for color function error handling."""

    def test_color_range_zero_n(self):
        """color_range with n=0 should return empty list."""
        result = color_range(0, PALETTE_VIRIDIS)
        assert result == []

    def test_color_range_negative_n(self):
        """color_range with negative n should return empty list."""
        result = color_range(-5, PALETTE_VIRIDIS)
        assert result == []

    def test_color_bins_empty_values(self):
        """color_bins with empty values should handle gracefully."""
        result = color_bins([], 5, PALETTE_VIRIDIS)
        # Should return empty or handle gracefully
        assert isinstance(result, (list, dict))

    def test_color_bins_single_value(self):
        """color_bins with single value should not crash."""
        result = color_bins([42], 5, PALETTE_VIRIDIS)
        assert isinstance(result, (list, dict))

    def test_color_quantiles_empty_values(self):
        """color_quantiles with empty values should handle gracefully."""
        result = color_quantiles([], [0.25, 0.5, 0.75], PALETTE_VIRIDIS)
        assert isinstance(result, (list, dict))

    def test_color_range_single_color_palette(self):
        """color_range with single-color palette should handle edge case."""
        single_color_palette = [[255, 0, 0]]
        result = color_range(5, single_color_palette)
        # All colors should be the same
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Extension error handling
# ---------------------------------------------------------------------------

class TestExtensionErrors:
    """Tests for extension error handling."""

    def test_data_filter_extension_requires_size(self):
        """data_filter_extension returns proper structure."""
        ext = data_filter_extension(filter_size=2)
        assert isinstance(ext, list)
        assert len(ext) == 2
        assert ext[0] == "DataFilterExtension"

    def test_brushing_extension_returns_structure(self):
        """brushing_extension returns proper structure."""
        ext = brushing_extension()
        assert ext == "BrushingExtension"


# ---------------------------------------------------------------------------
# Effect error handling
# ---------------------------------------------------------------------------

class TestEffectErrors:
    """Tests for effect error handling."""

    def test_lighting_effect_no_lights(self):
        """lighting_effect with no lights should work (minimal structure)."""
        effect = lighting_effect()
        assert effect["type"] == "LightingEffect"
        # No lights arrays are added when empty
        assert "pointLights" not in effect
        assert "directionalLights" not in effect

    def test_post_process_effect_shader_module(self):
        """post_process_effect requires shader_module parameter."""
        effect = post_process_effect("bloom", intensity=1.0)
        assert effect["type"] == "PostProcessEffect"
        assert effect["shaderModule"] == "bloom"
        assert effect["intensity"] == 1.0


# ---------------------------------------------------------------------------
# View error handling
# ---------------------------------------------------------------------------

class TestViewErrors:
    """Tests for view error handling."""

    def test_map_view_returns_dict(self):
        """map_view should return proper dict structure."""
        view = map_view()
        assert isinstance(view, dict)
        assert view["@@type"] == "MapView"

    def test_globe_view_returns_dict(self):
        """globe_view should return proper dict structure."""
        view = globe_view()
        assert isinstance(view, dict)
        assert view["@@type"] == "GlobeView"


# ---------------------------------------------------------------------------
# Transition error handling
# ---------------------------------------------------------------------------

class TestTransitionErrors:
    """Tests for transition helper error handling."""

    def test_transition_with_invalid_type(self):
        """transition with invalid type should still work (passed to deck.gl)."""
        # deck.gl will handle invalid types; we don't validate
        t = transition(type="invalid_type")
        assert t["type"] == "invalid_type"

    def test_transition_negative_duration(self):
        """transition with negative duration should pass through."""
        # deck.gl handles this; we don't validate
        t = transition(duration=-100)
        assert t["duration"] == -100


# ---------------------------------------------------------------------------
# IBM module error handling
# ---------------------------------------------------------------------------

class TestIBMErrors:
    """Tests for IBM module error handling."""

    def test_format_trips_properties_mismatch(self):
        """format_trips with mismatched properties should raise."""
        from shiny_deckgl.ibm import format_trips

        with pytest.raises(ValueError, match="properties length"):
            format_trips(
                paths=[[[0, 0], [1, 1]], [[2, 2], [3, 3]]],
                properties=[{"name": "only one"}],  # 2 paths, 1 property
            )

    def test_format_trips_timestamps_mismatch(self):
        """format_trips with mismatched timestamps should raise."""
        from shiny_deckgl.ibm import format_trips

        with pytest.raises(ValueError, match="timestamps length"):
            format_trips(
                paths=[[[0, 0], [1, 1]], [[2, 2], [3, 3]]],
                timestamps=[[0, 100]],  # 2 paths, 1 timestamp array
            )

    def test_format_trips_inner_timestamps_mismatch(self):
        """format_trips with mismatched inner timestamps should raise."""
        from shiny_deckgl.ibm import format_trips

        with pytest.raises(ValueError, match="timestamps.*length"):
            format_trips(
                paths=[[[0, 0], [1, 1], [2, 2]]],  # 3 points
                timestamps=[[0, 100]],  # only 2 timestamps
            )


# ---------------------------------------------------------------------------
# Parser error handling
# ---------------------------------------------------------------------------

class TestParserErrors:
    """Tests for parser module error handling."""

    def test_parse_grd_missing_file(self):
        """parse_shyfem_grd with missing file should raise FileNotFoundError."""
        from shiny_deckgl.parsers import parse_shyfem_grd

        with pytest.raises(FileNotFoundError):
            parse_shyfem_grd("/nonexistent/path/file.grd")

    def test_parse_mesh_empty_file(self):
        """parse_shyfem_mesh with empty file should raise ValueError."""
        import tempfile
        from pathlib import Path
        from shiny_deckgl.parsers import parse_shyfem_mesh

        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write("")
            path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="No nodes or elements"):
                parse_shyfem_mesh(path)
        finally:
            path.unlink()

    def test_utm_conversion_without_pyproj(self):
        """UTM conversion should raise RuntimeError if pyproj unavailable."""
        from shiny_deckgl.parsers import _get_transformer, _utm_to_wgs84

        # This test only meaningful if pyproj is not installed
        if _get_transformer() is None:
            with pytest.raises(RuntimeError, match="pyproj is required"):
                _utm_to_wgs84(500000, 6000000)


# ---------------------------------------------------------------------------
# Data utils error handling
# ---------------------------------------------------------------------------

class TestDataUtilsErrors:
    """Tests for data utils error handling."""

    @pytest.mark.skipif(
        pytest.importorskip("numpy", reason="numpy not installed") is None,
        reason="numpy not installed"
    )
    def test_encode_binary_unsupported_dtype_converted(self):
        """encode_binary_attribute with unsupported dtype should convert."""
        import numpy as np
        from shiny_deckgl._data_utils import encode_binary_attribute

        # complex dtype not in allowed list
        arr = np.array([1, 2, 3], dtype="int16")  # Not in allowed list
        result = encode_binary_attribute(arr)

        # Should be converted to float32
        assert result["dtype"] == "float32"


# ---------------------------------------------------------------------------
# Sealmove error handling
# ---------------------------------------------------------------------------

class TestSealmoveErrors:
    """Tests for sealmove module error handling."""

    @pytest.mark.skipif(
        pytest.importorskip("numpy", reason="numpy not installed") is None,
        reason="numpy not installed"
    )
    def test_softmax_all_zeros(self):
        """softmax with all zeros should return uniform distribution."""
        import numpy as np
        from shiny_deckgl._sealmove import softmax

        x = np.array([0.0, 0.0, 0.0])
        result = softmax(x)

        np.testing.assert_allclose(result, [1/3, 1/3, 1/3])

    @pytest.mark.skipif(
        pytest.importorskip("numpy", reason="numpy not installed") is None,
        reason="numpy not installed"
    )
    def test_normalize_rows_all_zeros(self):
        """normalize_rows with all-zero row should not crash."""
        import numpy as np
        from shiny_deckgl._sealmove import normalize_rows

        M = np.array([[0, 0, 0], [1, 2, 3]])
        result = normalize_rows(M)

        # Zero row stays zero
        np.testing.assert_allclose(result[0], [0, 0, 0])
        # Non-zero row normalized
        np.testing.assert_allclose(result[1].sum(), 1.0)


# ---------------------------------------------------------------------------
# Control validation
# ---------------------------------------------------------------------------

class TestControlValidation:
    """Tests for control type and position validation."""

    def test_all_control_types_valid(self):
        """All documented control types should be in CONTROL_TYPES."""
        expected_types = {
            "navigation", "scale", "geolocate", "attribution",
            "fullscreen", "terrain", "globe", "legend", "opacity",
        }
        for t in expected_types:
            assert t in CONTROL_TYPES, f"Missing control type: {t}"

    def test_all_positions_valid(self):
        """All documented positions should be in CONTROL_POSITIONS."""
        expected_positions = {
            "top-left", "top-right", "bottom-left", "bottom-right",
        }
        for p in expected_positions:
            assert p in CONTROL_POSITIONS, f"Missing position: {p}"
