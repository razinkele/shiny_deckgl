"""Property-based tests using Hypothesis.

These tests verify invariants and edge cases that are hard to catch
with example-based tests. They generate random inputs to find edge cases.
"""
from __future__ import annotations

import json

import pytest
from hypothesis import given, strategies as st, assume, settings

from shiny_deckgl import (
    MapWidget,
    scatterplot_layer,
    geojson_layer,
    line_layer,
    arc_layer,
    layer,
    color_range,
    color_bins,
    color_quantiles,
    transition,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
)
from shiny_deckgl._mixins import NavigationMixin


# ---------------------------------------------------------------------------
# Strategy definitions
# ---------------------------------------------------------------------------

# Geographic coordinates
longitude = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)
latitude = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
zoom_level = st.floats(min_value=0, max_value=24, allow_nan=False, allow_infinity=False)
pitch = st.floats(min_value=0, max_value=85, allow_nan=False, allow_infinity=False)
bearing = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)

# Color components
color_component = st.integers(min_value=0, max_value=255)
rgb_color = st.tuples(color_component, color_component, color_component)
rgba_color = st.tuples(color_component, color_component, color_component, color_component)

# Numeric values
positive_int = st.integers(min_value=1, max_value=1000)
non_negative_int = st.integers(min_value=0, max_value=1000)
positive_float = st.floats(min_value=0.001, max_value=1000, allow_nan=False, allow_infinity=False)
unit_float = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Layer IDs
layer_id = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
    min_size=1,
    max_size=50,
)

# Simple data point
data_point = st.fixed_dictionaries({
    "position": st.tuples(longitude, latitude),
    "value": st.floats(min_value=0, max_value=100, allow_nan=False),
})


# ---------------------------------------------------------------------------
# MapWidget property tests
# ---------------------------------------------------------------------------

class TestMapWidgetProperties:
    """Property-based tests for MapWidget."""

    @given(
        lng=longitude,
        lat=latitude,
        zoom=zoom_level,
    )
    def test_view_state_preserves_values(self, lng, lat, zoom):
        """View state should preserve the values it's given."""
        w = MapWidget(
            "test",
            view_state={"longitude": lng, "latitude": lat, "zoom": zoom},
        )
        assert w.view_state["longitude"] == lng
        assert w.view_state["latitude"] == lat
        assert w.view_state["zoom"] == zoom

    @given(layer_id=layer_id)
    def test_input_ids_derived_from_widget_id(self, layer_id):
        """All input IDs should be derived from widget ID."""
        assume(len(layer_id) > 0)
        w = MapWidget(layer_id)

        assert layer_id in w.click_input_id
        assert layer_id in w.hover_input_id
        assert layer_id in w.view_state_input_id

    @given(
        lng=longitude,
        lat=latitude,
        zoom=st.one_of(st.none(), zoom_level),
        p=st.one_of(st.none(), pitch),
        b=st.one_of(st.none(), bearing),
    )
    def test_build_view_state_omits_none(self, lng, lat, zoom, p, b):
        """_build_view_state should omit None values."""
        vs = NavigationMixin._build_view_state(lng, lat, zoom, p, b)

        assert vs["longitude"] == lng
        assert vs["latitude"] == lat

        if zoom is None:
            assert "zoom" not in vs
        else:
            assert vs["zoom"] == zoom

        if p is None:
            assert "pitch" not in vs
        else:
            assert vs["pitch"] == p

        if b is None:
            assert "bearing" not in vs
        else:
            assert vs["bearing"] == b


# ---------------------------------------------------------------------------
# Layer property tests
# ---------------------------------------------------------------------------

class TestLayerProperties:
    """Property-based tests for layer functions."""

    @given(id=layer_id, opacity=unit_float)
    def test_scatterplot_layer_preserves_id(self, id, opacity):
        """scatterplot_layer should preserve layer ID."""
        assume(len(id) > 0)
        l = scatterplot_layer(id, data=[], opacity=opacity)
        assert l["id"] == id
        assert l["type"] == "ScatterplotLayer"
        assert l.get("opacity", 1.0) == (opacity if opacity != 1.0 else l.get("opacity", 1.0))

    @given(id=layer_id, line_width=positive_float)
    def test_line_layer_preserves_id(self, id, line_width):
        """line_layer should preserve layer ID and properties."""
        assume(len(id) > 0)
        l = line_layer(id, data=[], getWidth=line_width)  # camelCase for deck.gl
        assert l["id"] == id
        assert l["type"] == "LineLayer"
        assert l["getWidth"] == line_width

    @given(id=layer_id, width=positive_float)
    def test_arc_layer_preserves_id(self, id, width):
        """arc_layer should preserve layer ID."""
        assume(len(id) > 0)
        l = arc_layer(id, data=[], getWidth=width)  # camelCase for deck.gl
        assert l["id"] == id
        assert l["type"] == "ArcLayer"

    @given(
        id=layer_id,
        layer_type=st.sampled_from([
            "ScatterplotLayer", "LineLayer", "ArcLayer", "PathLayer",
            "PolygonLayer", "GeoJsonLayer", "IconLayer", "TextLayer",
        ]),
    )
    def test_generic_layer_preserves_type(self, id, layer_type):
        """Generic layer() should preserve layer type."""
        assume(len(id) > 0)
        l = layer(layer_type, id, data=[])
        assert l["id"] == id
        assert l["type"] == layer_type

    @given(id=layer_id, visible=st.booleans())
    def test_layer_visibility(self, id, visible):
        """Layer visibility should be preserved."""
        assume(len(id) > 0)
        l = scatterplot_layer(id, data=[], visible=visible)
        assert l["visible"] == visible


# ---------------------------------------------------------------------------
# Color function property tests
# ---------------------------------------------------------------------------

class TestColorProperties:
    """Property-based tests for color functions."""

    @given(n=st.integers(min_value=0, max_value=100))
    def test_color_range_returns_n_colors(self, n):
        """color_range should return exactly n colors."""
        result = color_range(n, PALETTE_VIRIDIS)
        assert len(result) == n

    @given(n=st.integers(min_value=1, max_value=50))
    def test_color_range_all_valid_rgba(self, n):
        """All colors from color_range should be valid RGBA."""
        result = color_range(n, PALETTE_VIRIDIS)
        for color in result:
            assert len(color) == 4  # RGBA format
            assert all(0 <= c <= 255 for c in color)

    @given(
        values=st.lists(
            st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=50,
        ),
        n_bins=st.integers(min_value=2, max_value=10),
    )
    def test_color_bins_returns_valid_structure(self, values, n_bins):
        """color_bins should return valid color scale structure."""
        result = color_bins(values, n_bins, PALETTE_VIRIDIS)
        # Should be a list of [threshold, color] pairs or similar structure
        assert isinstance(result, (list, dict))

    @given(
        values=st.lists(
            st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=50,
        ),
        n_bins=st.integers(min_value=2, max_value=10),
    )
    def test_color_quantiles_returns_valid_structure(self, values, n_bins):
        """color_quantiles should return valid structure."""
        result = color_quantiles(values, n_bins, PALETTE_VIRIDIS)
        # Should return one color per input value
        assert isinstance(result, list)
        assert len(result) == len(values)


# ---------------------------------------------------------------------------
# Transition property tests
# ---------------------------------------------------------------------------

class TestTransitionProperties:
    """Property-based tests for transition helper."""

    @given(duration=st.integers(min_value=0, max_value=10000))
    def test_transition_preserves_duration(self, duration):
        """transition should preserve duration for interpolation type."""
        t = transition(duration=duration)  # default type is "interpolation"
        assert t["duration"] == duration

    @given(duration=st.integers(min_value=0, max_value=5000))
    def test_transition_interpolation_preserves_type(self, duration):
        """transition with interpolation type should include duration."""
        t = transition(duration=duration, type="interpolation")
        assert t["type"] == "interpolation"
        assert t["duration"] == duration

    def test_transition_spring_no_duration(self):
        """transition with spring type should not include duration."""
        t = transition(type="spring")
        assert t["type"] == "spring"
        assert "duration" not in t


# ---------------------------------------------------------------------------
# GeoJSON bounds computation property tests
# ---------------------------------------------------------------------------

class TestComputeBoundsProperties:
    """Property-based tests for compute_bounds."""

    @given(
        coords=st.lists(
            st.tuples(longitude, latitude),
            min_size=1,
            max_size=50,
        ),
    )
    def test_compute_bounds_contains_all_points(self, coords):
        """Computed bounds should contain all input points."""
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": list(c)},
            }
            for c in coords
        ]
        geojson = {"type": "FeatureCollection", "features": features}

        bounds = NavigationMixin.compute_bounds(geojson)

        sw_lng, sw_lat = bounds[0]
        ne_lng, ne_lat = bounds[1]

        for lng, lat in coords:
            assert sw_lng <= lng <= ne_lng
            assert sw_lat <= lat <= ne_lat

    @given(
        coords=st.lists(
            st.tuples(longitude, latitude),
            min_size=2,
            max_size=20,
        ),
    )
    def test_compute_bounds_tight(self, coords):
        """Bounds should be tight (exactly touch extreme points)."""
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": list(c)},
            }
            for c in coords
        ]
        geojson = {"type": "FeatureCollection", "features": features}

        bounds = NavigationMixin.compute_bounds(geojson)

        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]

        assert bounds[0][0] == min(lngs)
        assert bounds[0][1] == min(lats)
        assert bounds[1][0] == max(lngs)
        assert bounds[1][1] == max(lats)


# ---------------------------------------------------------------------------
# JSON serialization property tests
# ---------------------------------------------------------------------------

class TestJsonSerializationProperties:
    """Property-based tests for JSON serialization."""

    @given(
        lng=longitude,
        lat=latitude,
        zoom=zoom_level,
    )
    def test_to_json_produces_valid_json(self, lng, lat, zoom):
        """to_json should produce valid JSON."""
        w = MapWidget(
            "test",
            view_state={"longitude": lng, "latitude": lat, "zoom": zoom},
        )
        layers = [scatterplot_layer("l1", data=[])]

        json_str = w.to_json(layers)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert "viewState" in parsed
        assert "layers" in parsed

    @given(
        lng=longitude,
        lat=latitude,
        zoom=zoom_level,
    )
    def test_json_roundtrip_preserves_view_state(self, lng, lat, zoom):
        """JSON roundtrip should preserve view state."""
        original = MapWidget(
            "test",
            view_state={"longitude": lng, "latitude": lat, "zoom": zoom},
        )
        layers = [scatterplot_layer("l1", data=[])]

        json_str = original.to_json(layers)
        restored, restored_layers = MapWidget.from_json(json_str)

        assert restored.view_state["longitude"] == lng
        assert restored.view_state["latitude"] == lat
        assert restored.view_state["zoom"] == zoom


# ---------------------------------------------------------------------------
# Data serialization property tests
# ---------------------------------------------------------------------------

class TestDataSerializationProperties:
    """Property-based tests for data serialization."""

    @given(
        data=st.lists(
            st.fixed_dictionaries({
                "x": st.floats(allow_nan=False, allow_infinity=False),
                "y": st.floats(allow_nan=False, allow_infinity=False),
            }),
            min_size=0,
            max_size=100,
        ),
    )
    def test_list_data_passthrough(self, data):
        """List data should pass through serialization unchanged."""
        from shiny_deckgl._data_utils import _serialise_data

        result = _serialise_data(data)
        assert result is data

    @given(
        data=st.fixed_dictionaries({
            "type": st.just("FeatureCollection"),
            "features": st.just([]),
        }),
    )
    def test_geojson_passthrough(self, data):
        """GeoJSON dict should pass through unchanged."""
        from shiny_deckgl._data_utils import _serialise_data

        result = _serialise_data(data)
        assert result is data


# ---------------------------------------------------------------------------
# Numeric edge case tests
# ---------------------------------------------------------------------------

class TestNumericEdgeCases:
    """Property-based tests for numeric edge cases."""

    @given(
        lng=st.sampled_from([-180.0, 0.0, 180.0]),
        lat=st.sampled_from([-90.0, 0.0, 90.0]),
    )
    def test_extreme_coordinates(self, lng, lat):
        """Extreme geographic coordinates should be handled."""
        w = MapWidget(
            "test",
            view_state={"longitude": lng, "latitude": lat, "zoom": 1},
        )
        assert w.view_state["longitude"] == lng
        assert w.view_state["latitude"] == lat

    @given(
        zoom=st.sampled_from([0.0, 12.0, 24.0]),
    )
    def test_extreme_zoom_levels(self, zoom):
        """Extreme zoom levels should be handled."""
        w = MapWidget(
            "test",
            view_state={"longitude": 0, "latitude": 0, "zoom": zoom},
        )
        assert w.view_state["zoom"] == zoom

    @given(
        opacity=st.sampled_from([0.0, 0.5, 1.0]),
    )
    def test_layer_opacity_bounds(self, opacity):
        """Layer opacity at bounds should work."""
        l = scatterplot_layer("test", data=[], opacity=opacity)
        assert l["opacity"] == opacity
