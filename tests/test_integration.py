"""Integration tests for shiny_deckgl.

These tests verify that multiple components work together correctly,
simulating real-world usage patterns without running a browser.

Tests cover:
- Complete widget lifecycle (create → configure → update → export)
- Layer + control + effect combinations
- Data flow from Python to JSON spec
- Session message handling workflows
"""
from __future__ import annotations

import asyncio
import json

import pytest

from shiny_deckgl import (
    MapWidget,
    # Layers
    scatterplot_layer,
    geojson_layer,
    heatmap_layer,
    trips_layer,
    polygon_layer,
    # Controls
    geolocate_control,
    legend_control,
    # Widgets
    zoom_widget,
    compass_widget,
    fullscreen_widget,
    # Effects
    lighting_effect,
    ambient_light,
    directional_light,
    # Extensions
    brushing_extension,
    data_filter_extension,
    # Colors
    color_range,
    PALETTE_VIRIDIS,
    CARTO_POSITRON,
    CARTO_DARK,
    # Helpers
    transition,
)


class _FakeSession:
    """Mock Shiny session for testing async methods."""

    def __init__(self):
        self.messages: list[tuple[str, dict]] = []

    async def send_custom_message(self, handler: str, payload: dict):
        self.messages.append((handler, payload))

    def clear(self):
        self.messages.clear()


# ---------------------------------------------------------------------------
# Widget lifecycle tests
# ---------------------------------------------------------------------------

class TestWidgetLifecycle:
    """Tests for complete widget lifecycle."""

    def test_create_with_defaults(self):
        """Widget should create with sensible defaults."""
        w = MapWidget("test_map")
        assert w.id == "test_map"
        assert w.style == CARTO_POSITRON
        assert w.view_state is not None
        assert "longitude" in w.view_state

    def test_create_with_custom_view_state(self):
        """Widget should accept custom view state."""
        vs = {"longitude": 10, "latitude": 50, "zoom": 8}
        w = MapWidget("test_map", view_state=vs)
        assert w.view_state == vs

    def test_create_with_custom_style(self):
        """Widget should accept custom style."""
        w = MapWidget("test_map", style=CARTO_DARK)
        assert w.style == CARTO_DARK

    def test_ui_returns_tag(self):
        """ui() should return a Shiny Tag."""
        w = MapWidget("test_map")
        tag = w.ui()
        assert tag is not None
        # Should be renderable
        assert hasattr(tag, "tagify") or hasattr(tag, "render")

    def test_input_ids_generated(self):
        """Input IDs should be properly generated."""
        w = MapWidget("test_map")
        assert w.click_input_id == "test_map_click"
        assert w.hover_input_id == "test_map_hover"
        assert w.view_state_input_id == "test_map_view_state"
        assert w.drag_input_id == "test_map_drag"


# ---------------------------------------------------------------------------
# Layer workflow tests
# ---------------------------------------------------------------------------

class TestLayerWorkflow:
    """Tests for complete layer addition workflows."""

    def test_single_layer_update(self):
        """Should send single layer in update message."""
        w = MapWidget("layer_test")
        session = _FakeSession()

        layer = scatterplot_layer("points", data=[{"pos": [0, 0]}])
        asyncio.run(w.update(session, [layer]))

        handler, payload = session.messages[0]
        assert handler == "deck_update"
        assert len(payload["layers"]) == 1
        assert payload["layers"][0]["id"] == "points"

    def test_multiple_layers_update(self):
        """Should send multiple layers in single update."""
        w = MapWidget("multi_layer")
        session = _FakeSession()

        layers = [
            scatterplot_layer("scatter", data=[]),
            heatmap_layer("heat", data=[]),
            polygon_layer("poly", data=[]),
        ]
        asyncio.run(w.update(session, layers))

        handler, payload = session.messages[0]
        assert len(payload["layers"]) == 3
        layer_ids = [l["id"] for l in payload["layers"]]
        assert layer_ids == ["scatter", "heat", "poly"]

    def test_layer_with_color_scale(self):
        """Layer should work with color scale accessors."""
        colors = color_range(5, PALETTE_VIRIDIS)
        layer = scatterplot_layer(
            "colored",
            data=[{"value": 0.5}],
            getFillColor=colors,
        )
        assert "getFillColor" in layer
        assert isinstance(layer["getFillColor"], list)

    def test_layer_with_extension(self):
        """Layer should work with extensions."""
        layer = scatterplot_layer(
            "extended",
            data=[],
            extensions=[brushing_extension()],
        )
        # Extensions use @@extensions key (resolved to extensions by JS)
        assert "@@extensions" in layer
        assert len(layer["@@extensions"]) == 1

    def test_layer_visibility_toggle(self):
        """Should be able to toggle layer visibility."""
        w = MapWidget("vis_test")
        session = _FakeSession()

        asyncio.run(w.set_layer_visibility(session, {"layer1": True, "layer2": False}))

        handler, payload = session.messages[0]
        assert handler == "deck_layer_visibility"
        assert payload["visibility"]["layer1"] is True
        assert payload["visibility"]["layer2"] is False


# ---------------------------------------------------------------------------
# Partial update workflow tests
# ---------------------------------------------------------------------------

class TestPartialUpdateWorkflow:
    """Tests for partial/patch update workflows."""

    def test_partial_update_single_layer(self):
        """Should send partial update for single layer."""
        w = MapWidget("partial_test")
        session = _FakeSession()

        # partial_update takes list of layer dicts with "id" keys
        asyncio.run(w.partial_update(session, [{"id": "my_layer", "opacity": 0.5}]))

        handler, payload = session.messages[0]
        assert handler == "deck_partial_update"
        assert len(payload["layers"]) == 1
        assert payload["layers"][0]["id"] == "my_layer"
        assert payload["layers"][0]["opacity"] == 0.5

    def test_partial_update_multiple_layers(self):
        """Should send partial updates for multiple layers."""
        w = MapWidget("partial_multi")
        session = _FakeSession()

        layers = [
            {"id": "layer1", "opacity": 0.3},
            {"id": "layer2", "visible": False},
            {"id": "layer3", "radiusScale": 2},
        ]
        asyncio.run(w.partial_update(session, layers))

        handler, payload = session.messages[0]
        assert len(payload["layers"]) == 3

    def test_patch_layer_convenience(self):
        """patch_layer should be convenience wrapper for partial_update."""
        w = MapWidget("patch_test")
        session = _FakeSession()

        asyncio.run(w.patch_layer(session, "my_layer", opacity=0.5, visible=True))

        handler, payload = session.messages[0]
        assert handler == "deck_partial_update"
        assert payload["layers"][0]["id"] == "my_layer"
        assert payload["layers"][0]["opacity"] == 0.5
        assert payload["layers"][0]["visible"] is True


# ---------------------------------------------------------------------------
# Navigation workflow tests
# ---------------------------------------------------------------------------

class TestNavigationWorkflow:
    """Tests for map navigation workflows."""

    def test_fly_to(self):
        """fly_to should send correct message."""
        w = MapWidget("nav_test")
        session = _FakeSession()

        asyncio.run(w.fly_to(session, longitude=10, latitude=50, zoom=8))

        handler, payload = session.messages[0]
        assert handler == "deck_fly_to"
        assert payload["viewState"]["longitude"] == 10
        assert payload["viewState"]["latitude"] == 50
        assert payload["viewState"]["zoom"] == 8

    def test_ease_to(self):
        """ease_to should send correct message with duration."""
        w = MapWidget("ease_test")
        session = _FakeSession()

        asyncio.run(w.ease_to(session, 10, 50, duration=2000))

        handler, payload = session.messages[0]
        assert handler == "deck_ease_to"
        assert payload["duration"] == 2000

    def test_fit_bounds(self):
        """fit_bounds should send correct message."""
        w = MapWidget("bounds_test")
        session = _FakeSession()

        bounds = [[0, 40], [20, 60]]
        asyncio.run(w.fit_bounds(session, bounds))

        handler, payload = session.messages[0]
        assert handler == "deck_fit_bounds"
        assert payload["bounds"] == bounds


# ---------------------------------------------------------------------------
# Control workflow tests
# ---------------------------------------------------------------------------

class TestControlWorkflow:
    """Tests for map control workflows."""

    def test_add_control(self):
        """add_control should send correct message."""
        w = MapWidget("ctrl_test")
        session = _FakeSession()

        asyncio.run(w.add_control(session, "navigation", "top-left"))

        handler, payload = session.messages[0]
        assert handler == "deck_add_control"
        assert payload["controlType"] == "navigation"
        assert payload["position"] == "top-left"

    def test_remove_control(self):
        """remove_control should send correct message."""
        w = MapWidget("ctrl_rm_test")
        session = _FakeSession()

        asyncio.run(w.remove_control(session, "navigation"))

        handler, payload = session.messages[0]
        assert handler == "deck_remove_control"
        assert payload["controlType"] == "navigation"

    def test_set_controls_replaces_all(self):
        """set_controls should replace all controls."""
        w = MapWidget("ctrl_set_test")
        session = _FakeSession()

        controls = [
            {"type": "navigation", "position": "top-right"},
            {"type": "scale", "position": "bottom-left"},
        ]
        asyncio.run(w.set_controls(session, controls))

        handler, payload = session.messages[0]
        assert handler == "deck_set_controls"
        assert len(payload["controls"]) == 2


# ---------------------------------------------------------------------------
# Effect workflow tests
# ---------------------------------------------------------------------------

class TestEffectWorkflow:
    """Tests for lighting and effect workflows."""

    def test_update_with_effects(self):
        """update() should include effects in message."""
        w = MapWidget("effect_test")
        session = _FakeSession()

        effects = [
            lighting_effect(
                ambient_light(intensity=0.5),
                directional_light(direction=[-1, -2, -3], intensity=0.8),
            )
        ]
        asyncio.run(w.update(session, [], effects=effects))

        handler, payload = session.messages[0]
        assert "effects" in payload
        assert len(payload["effects"]) == 1

    def test_effect_structure(self):
        """Effects should have correct structure."""
        effect = lighting_effect(
            ambient_light(color=[255, 255, 255], intensity=0.6),
        )
        assert effect["type"] == "LightingEffect"
        assert "ambientLight" in effect


# ---------------------------------------------------------------------------
# Widget (deck.gl widget) workflow tests
# ---------------------------------------------------------------------------

class TestDeckWidgetWorkflow:
    """Tests for deck.gl widget workflows."""

    def test_set_widgets(self):
        """set_widgets should send widget list."""
        w = MapWidget("widget_test")
        session = _FakeSession()

        widgets = [
            zoom_widget(),
            compass_widget(),
            fullscreen_widget(),
        ]
        asyncio.run(w.set_widgets(session, widgets))

        handler, payload = session.messages[0]
        assert handler == "deck_set_widgets"
        assert len(payload["widgets"]) == 3

    def test_widgets_with_placements(self):
        """Widgets should preserve placement settings."""
        w = MapWidget("placement_test")
        session = _FakeSession()

        widgets = [
            zoom_widget(placement="top-left"),
            compass_widget(placement="bottom-right"),
        ]
        asyncio.run(w.set_widgets(session, widgets))

        handler, payload = session.messages[0]
        assert payload["widgets"][0]["placement"] == "top-left"
        assert payload["widgets"][1]["placement"] == "bottom-right"


# ---------------------------------------------------------------------------
# Export workflow tests
# ---------------------------------------------------------------------------

class TestExportWorkflow:
    """Tests for HTML/JSON export workflows."""

    def test_to_html_basic(self):
        """to_html() should generate valid HTML."""
        w = MapWidget("export_test")
        layers = [scatterplot_layer("pts", data=[])]

        html = w.to_html(layers)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "deck.gl" in html
        assert "maplibre" in html

    def test_to_html_with_title(self):
        """to_html() should include custom title."""
        w = MapWidget("title_test")

        html = w.to_html([], title="My Custom Map")

        assert "<title>My Custom Map</title>" in html

    def test_to_html_with_tooltip(self):
        """to_html() should include tooltip config."""
        w = MapWidget("tooltip_test", tooltip={"html": "<b>{name}</b>"})

        html = w.to_html([])

        assert "data-tooltip" in html

    def test_to_html_with_mapbox_key(self):
        """to_html() should include Mapbox API key (escaped)."""
        w = MapWidget("mapbox_test", mapbox_api_key="pk.test123")

        html = w.to_html([])

        assert 'data-mapbox-api-key="pk.test123"' in html

    def test_to_html_escapes_special_chars(self):
        """to_html() should escape special characters in API key."""
        w = MapWidget("escape_test", mapbox_api_key='key"with<special>&chars')

        html = w.to_html([])

        # Should be HTML-escaped
        assert 'key"with<special>&chars' not in html
        assert "&quot;" in html or "&#" in html or "&lt;" in html

    def test_to_json_roundtrip(self):
        """to_json() → from_json() should preserve state."""
        original = MapWidget(
            "roundtrip_test",
            view_state={"longitude": 10, "latitude": 50, "zoom": 8},
            style=CARTO_DARK,
        )
        layers = [scatterplot_layer("pts", data=[{"x": 1}])]

        json_str = original.to_json(layers)
        restored, restored_layers = MapWidget.from_json(json_str)

        assert restored.view_state == original.view_state
        assert restored.style == original.style
        assert len(restored_layers) == 1

    def test_to_json_valid_json(self):
        """to_json() should produce valid JSON."""
        w = MapWidget("json_test")
        layers = [scatterplot_layer("pts", data=[])]

        json_str = w.to_json(layers)

        # Should parse without error
        parsed = json.loads(json_str)
        assert "viewState" in parsed
        assert "layers" in parsed


# ---------------------------------------------------------------------------
# Combined workflow tests
# ---------------------------------------------------------------------------

class TestCombinedWorkflows:
    """Tests for realistic combined workflows."""

    def test_full_map_setup(self):
        """Complete map setup with layers, controls, widgets."""
        w = MapWidget(
            "full_setup",
            view_state={"longitude": 10, "latitude": 50, "zoom": 6},
            style=CARTO_POSITRON,
            controls=[{"type": "navigation", "position": "top-right"}],
        )
        session = _FakeSession()

        # Add layers
        layers = [
            scatterplot_layer("cities", data=[
                {"name": "Paris", "coordinates": [2.35, 48.85]},
                {"name": "Berlin", "coordinates": [13.4, 52.52]},
            ]),
            heatmap_layer("density", data=[]),
        ]

        # Add widgets
        widgets = [zoom_widget(), compass_widget()]

        # Add effects
        effects = [lighting_effect(ambient_light(intensity=0.8))]

        # Execute workflow
        asyncio.run(w.update(session, layers, effects=effects))
        asyncio.run(w.set_widgets(session, widgets))

        # Verify messages sent
        assert len(session.messages) == 2
        assert session.messages[0][0] == "deck_update"
        assert session.messages[1][0] == "deck_set_widgets"

    def test_interactive_update_sequence(self):
        """Sequence of interactive updates."""
        w = MapWidget("interactive_test")
        session = _FakeSession()

        # Initial setup
        asyncio.run(w.update(session, [scatterplot_layer("pts", data=[])]))

        # User interaction: fly to location
        asyncio.run(w.fly_to(session, longitude=10, latitude=50, zoom=10))

        # Partial update: change layer opacity
        asyncio.run(w.patch_layer(session, "pts", opacity=0.5))

        # Toggle visibility
        asyncio.run(w.set_layer_visibility(session, {"pts": False}))

        # Verify sequence
        handlers = [msg[0] for msg in session.messages]
        assert handlers == [
            "deck_update",
            "deck_fly_to",
            "deck_partial_update",
            "deck_layer_visibility",
        ]

    def test_trips_animation_workflow(self):
        """TripsLayer animation workflow."""
        w = MapWidget("trips_test")
        session = _FakeSession()

        # Create trips layer
        trips_data = [
            {"path": [[0, 0, 0], [1, 1, 100], [2, 2, 200]], "timestamps": [0, 100, 200]},
        ]
        layer = trips_layer(
            "animated",
            data=trips_data,
            getPath="@@d.path",
            getTimestamps="@@d.timestamps",
        )

        asyncio.run(w.update(session, [layer]))

        # Control animation
        asyncio.run(w.trips_control(session, "resume"))
        asyncio.run(w.trips_control(session, "pause"))
        asyncio.run(w.trips_control(session, "reset"))

        # Verify
        handlers = [msg[0] for msg in session.messages]
        assert "deck_trips_control" in handlers

    def test_layer_with_transitions(self):
        """Layer with animated transitions."""
        layer = scatterplot_layer(
            "animated_pts",
            data=[],
            transitions={
                "getRadius": transition(500, easing="ease-in-out-cubic"),
                "getFillColor": transition(300),
            },
        )

        assert "transitions" in layer
        assert "getRadius" in layer["transitions"]
        assert layer["transitions"]["getRadius"]["duration"] == 500


# ---------------------------------------------------------------------------
# GeoDataFrame integration tests
# ---------------------------------------------------------------------------

class TestGeoDataFrameIntegration:
    """Tests for GeoDataFrame integration workflows."""

    @pytest.mark.skipif(
        pytest.importorskip("geopandas", reason="geopandas not installed") is None,
        reason="geopandas not installed"
    )
    def test_geodataframe_layer(self):
        """GeoDataFrame should work directly with geojson_layer."""
        import geopandas as gpd
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"name": ["A", "B"], "value": [10, 20]},
            geometry=[Point(0, 0), Point(1, 1)],
        )

        layer = geojson_layer("gdf_layer", data=gdf)

        # Data should be converted to GeoJSON
        assert layer["data"]["type"] == "FeatureCollection"

    @pytest.mark.skipif(
        pytest.importorskip("pandas", reason="pandas not installed") is None,
        reason="pandas not installed"
    )
    def test_dataframe_layer(self):
        """DataFrame should work with scatterplot_layer."""
        import pandas as pd

        df = pd.DataFrame({
            "lon": [0, 1, 2],
            "lat": [50, 51, 52],
            "value": [10, 20, 30],
        })

        layer = scatterplot_layer(
            "df_layer",
            data=df,
            getPosition="@@d => [d.lon, d.lat]",
            getRadius="@@d.value",
        )

        # Data should be list of dicts
        assert isinstance(layer["data"], list)
        assert len(layer["data"]) == 3
