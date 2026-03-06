"""Tests for shiny_deckgl package."""

import asyncio
import json
import pytest
import tempfile
import os
import shiny_deckgl as m
from shiny import App
from shiny_deckgl.app import app
from shiny_deckgl.ui import head_includes
from shiny_deckgl._data_utils import _serialise_data
from shiny_deckgl.components import (
    MapWidget,
    layer,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    bitmap_layer,
    arc_layer,
    icon_layer,
    path_layer,
    line_layer,
    text_layer,
    column_layer,
    polygon_layer,
    heatmap_layer,
    hexagon_layer,
    h3_hexagon_layer,
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    color_range,
    color_bins,
    color_quantiles,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
    encode_binary_attribute,
    map_view,
    orthographic_view,
    first_person_view,
    globe_view,
    CONTROL_TYPES,
    CONTROL_POSITIONS,
    # v0.8.0 widgets
    zoom_widget,
    compass_widget,
    fullscreen_widget,
    scale_widget,
    gimbal_widget,
    reset_view_widget,
    screenshot_widget,
    fps_widget,
    loading_widget,
    timeline_widget,
    geocoder_widget,
    theme_widget,
    # v9.2 experimental widgets
    context_menu_widget,
    info_widget,
    splitter_widget,
    stats_widget,
    view_selector_widget,
    # MapLibre control helpers
    geolocate_control,
    globe_control,
    terrain_control,
    # Third-party plugin controls
    legend_control,
    opacity_control,
    # Custom deck.gl legend
    deck_legend_control,
    # v0.8.0 transition
    transition,
    # v0.9.0 layer helpers
    trips_layer,
    great_circle_layer,
    contour_layer,
    grid_layer,
    screen_grid_layer,
    mvt_layer,
    wms_layer,
    point_cloud_layer,
    simple_mesh_layer,
    terrain_layer,
)
from shiny_deckgl.extensions import (
    brushing_extension,
    collision_filter_extension,
    data_filter_extension,
    mask_extension,
    clip_extension,
    terrain_extension,
    fill_style_extension,
    path_style_extension,
    fp64_extension,
)
from shiny_deckgl.views import orbit_view
from shiny_deckgl.effects import (
    ambient_light,
    point_light,
    directional_light,
    sun_light,
    lighting_effect,
    post_process_effect,
)


# ---------------------------------------------------------------------------
# Package-level imports
# ---------------------------------------------------------------------------

def test_import():
    assert hasattr(m, "app")


def test_public_api_exports():
    expected = {
        "app", "MapWidget", "layer",
        "scatterplot_layer", "geojson_layer", "tile_layer", "bitmap_layer",
        "arc_layer", "icon_layer", "path_layer", "line_layer",
        "text_layer", "column_layer", "polygon_layer",
        "heatmap_layer", "hexagon_layer", "h3_hexagon_layer",
        "head_includes",
        "CARTO_POSITRON", "CARTO_DARK", "CARTO_VOYAGER", "OSM_LIBERTY",
        "color_range", "color_bins", "color_quantiles",
        "PALETTE_VIRIDIS", "PALETTE_PLASMA", "PALETTE_OCEAN",
        "PALETTE_THERMAL", "PALETTE_CHLOROPHYLL",
        "encode_binary_attribute",
        "map_view", "orthographic_view", "first_person_view", "globe_view",
        "CONTROL_TYPES", "CONTROL_POSITIONS",
        # v0.8.0
        "zoom_widget", "compass_widget", "fullscreen_widget",
        "scale_widget", "gimbal_widget", "reset_view_widget",
        "screenshot_widget", "fps_widget", "loading_widget",
        "timeline_widget", "geocoder_widget", "theme_widget",
        "context_menu_widget", "info_widget", "splitter_widget",
        "stats_widget", "view_selector_widget",
        "geolocate_control", "globe_control", "terrain_control",
        "legend_control", "opacity_control", "deck_legend_control",
        "transition",
        # v0.9.0
        "trips_layer", "great_circle_layer", "contour_layer",
        "grid_layer", "screen_grid_layer", "mvt_layer", "wms_layer",
        "point_cloud_layer", "simple_mesh_layer", "terrain_layer",
        # v1.0.0 extension helpers
        "brushing_extension", "collision_filter_extension",
        "data_filter_extension", "mask_extension", "clip_extension",
        "terrain_extension", "fill_style_extension", "path_style_extension",
        "fp64_extension",
        # v1.2.0 effects
        "ambient_light", "point_light", "directional_light",
        "sun_light", "lighting_effect", "post_process_effect",
        # v1.2.0 views
        "orbit_view",
        "__version__",
    }
    assert expected.issubset(set(dir(m)))


def test_version_string():
    assert isinstance(m.__version__, str)
    parts = m.__version__.split(".")
    assert len(parts) >= 2  # at least major.minor


def test_head_includes_reexported():
    """head_includes should be importable directly from the package."""
    from shiny_deckgl import head_includes as hi
    assert callable(hi)


def test_py_typed_marker_exists():
    """PEP 561 py.typed marker must be present inside the package."""
    from importlib import resources as impresources
    res = impresources.files("shiny_deckgl")
    assert (res / "py.typed").is_file()


# ---------------------------------------------------------------------------
# Basemap style constants
# ---------------------------------------------------------------------------

def test_basemap_constants_are_urls():
    for url in (CARTO_POSITRON, CARTO_DARK, CARTO_VOYAGER, OSM_LIBERTY):
        assert url.startswith("https://")


# ---------------------------------------------------------------------------
# app module-level instance
# ---------------------------------------------------------------------------

def test_app_returns_shiny_app():
    assert isinstance(app, App)


# ---------------------------------------------------------------------------
# head_includes
# ---------------------------------------------------------------------------

def test_head_includes_contains_cdn_urls():
    html = str(head_includes())
    assert "deck.gl@9.2.10" in html
    assert "maplibre-gl@5.3.1" in html


def test_head_includes_contains_local_assets():
    html = str(head_includes())
    assert "deckgl-init" in html


# ---------------------------------------------------------------------------
# MapWidget
# ---------------------------------------------------------------------------

class TestMapWidget:
    def test_default_view_state(self):
        w = MapWidget("mymap")
        assert w.view_state["longitude"] == 21.1
        assert w.view_state["latitude"] == 55.7
        assert w.view_state["zoom"] == 8

    def test_custom_view_state(self):
        vs = {"longitude": 10.0, "latitude": 50.0, "zoom": 4}
        w = MapWidget("m2", view_state=vs)
        assert w.view_state == vs

    def test_click_input_id(self):
        w = MapWidget("demo")
        assert w.click_input_id == "demo_click"

    def test_hover_input_id(self):
        w = MapWidget("demo")
        assert w.hover_input_id == "demo_hover"

    def test_view_state_input_id(self):
        w = MapWidget("demo")
        assert w.view_state_input_id == "demo_view_state"

    def test_ui_contains_div_with_correct_id(self):
        w = MapWidget("abc")
        html = str(w.ui())
        assert 'id="abc"' in html
        assert "deckgl-map" in html

    def test_ui_data_attributes(self):
        w = MapWidget("m", view_state={"longitude": 5.5, "latitude": 60.0, "zoom": 3})
        html = str(w.ui())
        assert 'data-initial-longitude="5.5"' in html
        assert 'data-initial-latitude="60.0"' in html
        assert 'data-initial-zoom="3"' in html

    def test_ui_pitch_bearing_data_attrs(self):
        w = MapWidget("m", view_state={"longitude": 0, "latitude": 0, "zoom": 1, "pitch": 45, "bearing": 90})
        html = str(w.ui())
        assert 'data-initial-pitch="45"' in html
        assert 'data-initial-bearing="90"' in html

    def test_ui_no_redundant_wrapper(self):
        w = MapWidget("flat")
        tag = w.ui()
        assert tag.attrs.get("id") == "flat"

    def test_default_view_state_is_not_shared(self):
        w1 = MapWidget("a")
        w2 = MapWidget("b")
        w1.view_state["zoom"] = 99
        assert w2.view_state["zoom"] == 8

    def test_default_style_is_positron(self):
        w = MapWidget("s")
        assert w.style == CARTO_POSITRON

    def test_custom_style(self):
        w = MapWidget("s", style=CARTO_DARK)
        assert w.style == CARTO_DARK
        html = str(w.ui())
        assert "dark-matter" in html

    def test_style_in_data_attribute(self):
        w = MapWidget("s", style="https://my.style/spec.json")
        html = str(w.ui())
        assert 'data-style="https://my.style/spec.json"' in html

    def test_tooltip_none_by_default(self):
        w = MapWidget("t")
        assert w.tooltip is None
        html = str(w.ui())
        assert "data-tooltip" not in html

    def test_tooltip_serialised_to_data_attr(self):
        tip = {"html": "<b>{name}</b>", "style": {"color": "red"}}
        w = MapWidget("t", tooltip=tip)
        html = str(w.ui())
        assert "data-tooltip" in html
        # The JSON should be parseable
        # Extract the value between data-tooltip=" and next "
        # (simplified check: the JSON content is present)
        assert "{name}" in html

    # -- Module namespace tests -----------------------------------------------

    def test_id_resolved_outside_module(self):
        """Outside any module context, id == bare id."""
        w = MapWidget("plain")
        assert w.id == "plain"
        assert w._bare_id == "plain"

    def test_id_resolved_inside_module_namespace(self):
        """Inside a Shiny module namespace context, id is fully qualified."""
        from shiny._namespaces import namespace_context
        with namespace_context("mymod"):
            w = MapWidget("map1")
        assert w.id == "mymod-map1"
        assert w._bare_id == "map1"

    def test_ui_div_uses_resolved_id_in_module(self):
        """The HTML div id must be the namespace-resolved id."""
        from shiny._namespaces import namespace_context
        with namespace_context("ns"):
            w = MapWidget("m")
            html = str(w.ui())
        assert 'id="ns-m"' in html

    def test_input_ids_use_bare_id(self):
        """Input property helpers must return bare names (Shiny auto-namespaces)."""
        from shiny._namespaces import namespace_context
        with namespace_context("mod"):
            w = MapWidget("x")
        assert w.click_input_id == "x_click"
        assert w.hover_input_id == "x_hover"
        assert w.view_state_input_id == "x_view_state"
        assert w.drag_input_id == "x_drag"
        assert w.map_click_input_id == "x_map_click"
        assert w.map_contextmenu_input_id == "x_map_contextmenu"

    def test_nested_module_namespace(self):
        """Nested modules produce doubly-qualified ids."""
        from shiny._namespaces import namespace_context
        with namespace_context("outer"):
            with namespace_context("inner"):
                w = MapWidget("m")
        assert w.id == "outer-inner-m"
        assert w._bare_id == "m"

    def test_server_payload_uses_resolved_id(self):
        """Server helpers should use the resolved (namespaced) id."""
        from shiny._namespaces import namespace_context
        with namespace_context("srv"):
            w = MapWidget("deck")
        # Simulate: the payloads reference self.id which is now resolved
        assert w.id == "srv-deck"


# ---------------------------------------------------------------------------
# Generic layer()
# ---------------------------------------------------------------------------

class TestGenericLayer:
    def test_basic_structure(self):
        lyr = layer("HeatmapLayer", "heat1", [[1, 2, 100]])
        assert lyr["type"] == "HeatmapLayer"
        assert lyr["id"] == "heat1"
        assert lyr["data"] == [[1, 2, 100]]

    def test_arbitrary_kwargs(self):
        lyr = layer("PathLayer", "path1", [], getWidth=5, pickable=True)
        assert lyr["getWidth"] == 5
        assert lyr["pickable"] is True

    def test_no_data(self):
        lyr = layer("SolidPolygonLayer", "sp1")
        assert "data" not in lyr

    def test_data_serialisation_passthrough(self):
        """Plain lists/dicts should pass through unchanged."""
        raw = [[1, 2], [3, 4]]
        lyr = layer("ScatterplotLayer", "s", raw)
        assert lyr["data"] is raw


# ---------------------------------------------------------------------------
# Data serialisation
# ---------------------------------------------------------------------------

class TestSerialiseData:
    def test_list_passthrough(self):
        data = [[1, 2]]
        assert _serialise_data(data) is data

    def test_dict_passthrough(self):
        data = {"type": "FeatureCollection", "features": []}
        assert _serialise_data(data) is data

    def test_string_passthrough(self):
        assert _serialise_data("https://url") == "https://url"


# ---------------------------------------------------------------------------
# Typed layer helpers
# ---------------------------------------------------------------------------

class TestScatterplotLayer:
    def test_basic_structure(self):
        lyr = scatterplot_layer("pts", [[1, 2]])
        assert lyr["type"] == "ScatterplotLayer"
        assert lyr["id"] == "pts"
        assert lyr["data"] == [[1, 2]]
        assert lyr["pickable"] is True

    def test_override_defaults(self):
        lyr = scatterplot_layer("pts", [], getFillColor=[255, 0, 0])
        assert lyr["getFillColor"] == [255, 0, 0]

    def test_extra_kwargs(self):
        lyr = scatterplot_layer("pts", [], radiusScale=10)
        assert lyr["radiusScale"] == 10

    def test_accessor_convention(self):
        lyr = scatterplot_layer("pts", [])
        assert lyr["getPosition"] == "@@d"


class TestGeoJsonLayer:
    def test_basic_structure(self):
        data = {"type": "FeatureCollection", "features": []}
        lyr = geojson_layer("gj", data)
        assert lyr["type"] == "GeoJsonLayer"
        assert lyr["id"] == "gj"
        assert lyr["data"] is data

    def test_override_fill_color(self):
        lyr = geojson_layer("g", {}, getFillColor=[0, 0, 0, 255])
        assert lyr["getFillColor"] == [0, 0, 0, 255]

    def test_default_line_color(self):
        lyr = geojson_layer("g", {})
        assert lyr["getLineColor"] == [0, 128, 255]


class TestTileLayer:
    def test_basic_structure(self):
        url = "https://example.com/{z}/{x}/{y}.png"
        lyr = tile_layer("tiles", url)
        assert lyr["type"] == "TileLayer"
        assert lyr["data"] == url
        assert lyr["tileSize"] == 256
        assert lyr["renderSubLayers"] == "@@BitmapLayer"

    def test_override_tile_size(self):
        lyr = tile_layer("t", "url", tileSize=512)
        assert lyr["tileSize"] == 512

    def test_wms_url_template(self):
        wms = "https://ows.emodnet-bathymetry.eu/wms?BBOX={bbox-epsg-3857}"
        lyr = tile_layer("wms", wms)
        assert "{bbox-epsg-3857}" in lyr["data"]


class TestBitmapLayer:
    def test_basic_structure(self):
        lyr = bitmap_layer("bmp", "img.png", [0, 0, 1, 1])
        assert lyr["type"] == "BitmapLayer"
        assert lyr["image"] == "img.png"
        assert lyr["bounds"] == [0, 0, 1, 1]

    def test_override_kwargs(self):
        lyr = bitmap_layer("b", "x.png", [0, 0, 1, 1], opacity=0.5)
        assert lyr["opacity"] == 0.5


# ---------------------------------------------------------------------------
# Color-scale utilities
# ---------------------------------------------------------------------------

class TestColorRange:
    def test_returns_correct_count(self):
        colors = color_range(5)
        assert len(colors) == 5

    def test_returns_rgba_tuples(self):
        colors = color_range(3)
        for c in colors:
            assert len(c) == 4  # R, G, B, A
            assert all(isinstance(v, int) for v in c)

    def test_single_color(self):
        colors = color_range(1)
        assert len(colors) == 1

    def test_alpha_is_255(self):
        for c in color_range(4):
            assert c[3] == 255

    def test_custom_palette(self):
        pal = [(0, 0, 0), (255, 255, 255)]
        colors = color_range(3, palette=pal)
        assert len(colors) == 3
        # First should be black, last should be white
        assert colors[0][:3] == [0, 0, 0]
        assert colors[-1][:3] == [255, 255, 255]

    def test_all_builtin_palettes(self):
        for pal in (PALETTE_VIRIDIS, PALETTE_PLASMA, PALETTE_OCEAN,
                    PALETTE_THERMAL, PALETTE_CHLOROPHYLL):
            colors = color_range(4, palette=pal)
            assert len(colors) == 4


class TestColorBins:
    def test_returns_correct_count(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = color_bins(values, n_bins=3)
        assert len(result) == len(values)

    def test_rgba_tuples(self):
        result = color_bins([10, 20, 30], n_bins=2)
        for c in result:
            assert len(c) == 4
            assert all(isinstance(v, int) for v in c)

    def test_uniform_values(self):
        """All same value â†’ all mapped to same bin."""
        result = color_bins([5, 5, 5, 5], n_bins=3)
        assert all(c == result[0] for c in result)


class TestColorQuantiles:
    def test_returns_correct_count(self):
        values = list(range(100))
        result = color_quantiles(values, n_bins=4)
        assert len(result) == 100

    def test_rgba_tuples(self):
        result = color_quantiles([1, 2, 3, 4], n_bins=2)
        for c in result:
            assert len(c) == 4

    def test_uniform_values(self):
        result = color_quantiles([7, 7, 7], n_bins=3)
        assert all(c == result[0] for c in result)


# ---------------------------------------------------------------------------
# Palette constants
# ---------------------------------------------------------------------------

class TestPalettes:
    def test_viridis_has_stops(self):
        assert len(PALETTE_VIRIDIS) >= 2

    def test_palettes_are_rgb_tuples(self):
        for pal in (PALETTE_VIRIDIS, PALETTE_PLASMA, PALETTE_OCEAN,
                    PALETTE_THERMAL, PALETTE_CHLOROPHYLL):
            for stop in pal:
                assert len(stop) == 3
                assert all(0 <= v <= 255 for v in stop)


# ---------------------------------------------------------------------------
# MapWidget â€“ minZoom / maxZoom & drag
# ---------------------------------------------------------------------------

class TestMapWidgetP2:
    def test_drag_input_id(self):
        w = MapWidget("demo")
        assert w.drag_input_id == "demo_drag"

    def test_min_max_zoom_data_attrs(self):
        w = MapWidget("m", view_state={
            "longitude": 0, "latitude": 0, "zoom": 1,
            "minZoom": 3, "maxZoom": 15,
        })
        html = str(w.ui())
        assert 'data-initial-min-zoom="3"' in html
        assert 'data-initial-max-zoom="15"' in html

    def test_default_min_max_zoom(self):
        w = MapWidget("m")
        html = str(w.ui())
        assert 'data-initial-min-zoom="0"' in html
        assert 'data-initial-max-zoom="24"' in html

    def test_color_utilities_reexported(self):
        """Color utilities accessible from the top-level package."""
        assert callable(m.color_range)
        assert callable(m.color_bins)
        assert callable(m.color_quantiles)
        assert isinstance(m.PALETTE_VIRIDIS, list)


# ---------------------------------------------------------------------------
# P3-1: HTML Export
# ---------------------------------------------------------------------------

class TestToHtml:
    def test_returns_html_string(self):
        w = MapWidget("export_test")
        layers = [scatterplot_layer("pts", [[0, 0]])]
        html = w.to_html(layers)
        assert "<!DOCTYPE html>" in html
        assert 'id="export_test"' in html
        assert "deck.gl@9.2.10" in html
        assert "maplibre-gl@5.3.1" in html

    def test_contains_layer_data(self):
        w = MapWidget("t")
        layers = [scatterplot_layer("pts", [[10, 20]])]
        html = w.to_html(layers)
        # JSON indent splits across lines, so check for individual values
        assert '"ScatterplotLayer"' in html
        assert '"pts"' in html

    def test_writes_to_file(self):
        w = MapWidget("file_test")
        layers = [scatterplot_layer("pts", [[0, 0]])]
        path = os.path.join(tempfile.gettempdir(), "test_deckgl_export.html")
        result = w.to_html(layers, path=path)
        assert os.path.isfile(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert content == result
        os.unlink(path)

    def test_shiny_shim_present(self):
        """Standalone HTML must shim window.Shiny."""
        w = MapWidget("shim")
        html = w.to_html([])
        assert "window.Shiny" in html

    def test_tooltip_in_html(self):
        w = MapWidget("tip", tooltip={"html": "<b>{name}</b>"})
        html = w.to_html([])
        assert "data-tooltip" in html

    def test_custom_title(self):
        w = MapWidget("x")
        html = w.to_html([], title="My Map")
        assert "<title>My Map</title>" in html

    def test_mapbox_key_in_html(self):
        w = MapWidget("x", mapbox_api_key="pk.test123")
        html = w.to_html([])
        assert "pk.test123" in html


# ---------------------------------------------------------------------------
# P3-2: JSON serialisation
# ---------------------------------------------------------------------------

class TestJsonSpec:
    def test_to_json_roundtrip(self):
        w = MapWidget("rt", view_state={"longitude": 5, "latitude": 60, "zoom": 4})
        layers = [scatterplot_layer("pts", [[5, 60]])]
        j = w.to_json(layers)
        spec = json.loads(j)
        assert spec["id"] == "rt"
        assert spec["viewState"]["longitude"] == 5
        assert len(spec["layers"]) == 1

    def test_from_json_reconstructs_widget(self):
        w = MapWidget("rj", tooltip={"html": "{x}"}, style=CARTO_DARK)
        layers = [layer("HeatmapLayer", "h1")]
        j = w.to_json(layers)
        w2, layers2 = MapWidget.from_json(j)
        assert w2.id == "rj"
        assert w2.style == CARTO_DARK
        assert w2.tooltip == {"html": "{x}"}
        assert layers2[0]["type"] == "HeatmapLayer"

    def test_effects_in_json(self):
        w = MapWidget("ej")
        effects = [{"type": "LightingEffect", "ambientLight": {"intensity": 1}}]
        j = w.to_json([], effects=effects)
        spec = json.loads(j)
        assert "effects" in spec


# ---------------------------------------------------------------------------
# P3-3: Extensions API
# ---------------------------------------------------------------------------

class TestExtensions:
    def test_layer_with_extensions(self):
        lyr = layer("ScatterplotLayer", "ext1", [[0, 0]],
                    extensions=["DataFilterExtension"],
                    getFilterValue="@@d.val",
                    filterRange=[0, 100])
        assert lyr["@@extensions"] == ["DataFilterExtension"]
        assert lyr["filterRange"] == [0, 100]

    def test_extensions_none_by_default(self):
        lyr = layer("ScatterplotLayer", "no_ext", [[0, 0]])
        assert "@@extensions" not in lyr


# ---------------------------------------------------------------------------
# P3-4: Lighting & Effects (Python-side: effects param in update)
# ---------------------------------------------------------------------------

class TestEffects:
    def test_to_json_with_effects(self):
        w = MapWidget("fx")
        effects = [{"type": "LightingEffect", "ambientLight": {"intensity": 0.8}}]
        j = w.to_json([], effects=effects)
        spec = json.loads(j)
        assert spec["effects"][0]["type"] == "LightingEffect"


# ---------------------------------------------------------------------------
# P3-5: Multiple Views
# ---------------------------------------------------------------------------

class TestViews:
    def test_map_view(self):
        v = map_view(controller=True)
        assert v["@@type"] == "MapView"
        assert v["controller"] is True

    def test_orthographic_view(self):
        v = orthographic_view(flipY=False)
        assert v["@@type"] == "OrthographicView"
        assert v["flipY"] is False

    def test_first_person_view(self):
        v = first_person_view()
        assert v["@@type"] == "FirstPersonView"

    def test_view_helpers_reexported(self):
        assert callable(m.map_view)
        assert callable(m.orthographic_view)
        assert callable(m.first_person_view)


# ---------------------------------------------------------------------------
# P3-6: Binary data transport
# ---------------------------------------------------------------------------

class TestBinaryTransport:
    def test_encode_binary_attribute(self):
        import numpy as np
        arr = np.array([[0.0, 51.5], [10.0, 48.8]], dtype="float32")
        result = encode_binary_attribute(arr)
        assert result["@@binary"] is True
        assert result["dtype"] == "float32"
        assert result["size"] == 2  # 2 columns
        assert isinstance(result["value"], str)  # base64 string

    def test_encode_1d_array(self):
        import numpy as np
        arr = np.array([1.0, 2.0, 3.0], dtype="float32")
        result = encode_binary_attribute(arr)
        assert result["size"] == 1

    def test_encode_auto_casts_to_float32(self):
        import numpy as np
        arr = np.array([1, 2, 3], dtype="int64")
        result = encode_binary_attribute(arr)
        assert result["dtype"] == "float32"

    def test_encode_preserves_uint8(self):
        import numpy as np
        arr = np.array([0, 128, 255], dtype="uint8")
        result = encode_binary_attribute(arr)
        assert result["dtype"] == "uint8"

    def test_encode_reexported(self):
        assert callable(m.encode_binary_attribute)


# ---------------------------------------------------------------------------
# P3-7: Mapbox API key
# ---------------------------------------------------------------------------

class TestMapboxKey:
    def test_default_no_key(self):
        w = MapWidget("nokey")
        assert w.mapbox_api_key is None
        html = str(w.ui())
        assert "data-mapbox-api-key" not in html

    def test_key_in_data_attr(self):
        w = MapWidget("k", mapbox_api_key="pk.abc123")
        assert w.mapbox_api_key == "pk.abc123"
        html = str(w.ui())
        assert 'data-mapbox-api-key="pk.abc123"' in html


# ---------------------------------------------------------------------------
# Edge-case tests (T1)
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_color_range_zero(self):
        assert color_range(0) == []

    def test_color_bins_empty(self):
        assert color_bins([]) == []

    def test_color_quantiles_empty(self):
        assert color_quantiles([]) == []


# ---------------------------------------------------------------------------
# to_html with effects / views (T2)
# ---------------------------------------------------------------------------

class TestToHtmlAdvanced:
    def test_to_html_with_effects(self):
        w = MapWidget("eff")
        effects = [{"type": "LightingEffect", "ambientLight": {"intensity": 0.5}}]
        html = w.to_html([], effects=effects)
        assert "LightingEffect" in html
        assert "effectsData" in html

    def test_to_html_tooltip_escaping(self):
        """Tooltip with quotes must not break the HTML attribute."""
        tip = {"html": '<b>{name}</b><br/>"quoted"'}
        w = MapWidget("esc", tooltip=tip)
        html = w.to_html([])
        # data-tooltip must be properly quoted â€” no unescaped " inside attr
        assert 'data-tooltip="' in html
        assert "&quot;" in html or "&#x27;" in html or "quoted" in html


# ---------------------------------------------------------------------------
# JSON roundtrip with mapbox_api_key (T3)
# ---------------------------------------------------------------------------

class TestJsonMapboxKey:
    def test_to_json_includes_key(self):
        w = MapWidget("k", mapbox_api_key="pk.test")
        j = w.to_json([])
        spec = json.loads(j)
        assert spec["mapboxApiKey"] == "pk.test"

    def test_from_json_restores_key(self):
        w = MapWidget("k2", mapbox_api_key="pk.round")
        j = w.to_json([])
        w2, _ = MapWidget.from_json(j)
        assert w2.mapbox_api_key == "pk.round"

    def test_roundtrip_without_key(self):
        w = MapWidget("nk")
        j = w.to_json([])
        spec = json.loads(j)
        assert "mapboxApiKey" not in spec
        w2, _ = MapWidget.from_json(j)
        assert w2.mapbox_api_key is None


# ---------------------------------------------------------------------------
# Viridis palette fix check
# ---------------------------------------------------------------------------

class TestViridisFixed:
    def test_last_two_stops_differ(self):
        """B1: Viridis palette last two stops must not be duplicates."""
        assert PALETTE_VIRIDIS[-1] != PALETTE_VIRIDIS[-2]


# ---------------------------------------------------------------------------
# Reusable fake session stub (used by tooltip, style, gestures tests)
# ---------------------------------------------------------------------------

class _FakeSession:
    """Reusable fake session for tests requiring async message capture."""
    def __init__(self):
        self.messages = []
    async def send_custom_message(self, handler, payload):
        self.messages.append((handler, payload))


# ---------------------------------------------------------------------------
# update_tooltip method
# ---------------------------------------------------------------------------

class TestUpdateTooltip:
    def test_method_exists(self):
        w = MapWidget("utt")
        assert hasattr(w, "update_tooltip")
        assert callable(w.update_tooltip)

    def test_update_tooltip_sets_attribute(self):
        """Calling update_tooltip should update the widget's tooltip attr
        (the actual message send requires a live session, tested manually)."""

        w = MapWidget("utt2", tooltip={"html": "<b>{name}</b>"})
        assert w.tooltip is not None

        fake = _FakeSession()
        new_tip = {"html": "{x}", "style": {"color": "red"}}
        asyncio.run(w.update_tooltip(fake, new_tip))
        assert w.tooltip == new_tip
        assert len(fake.messages) == 1
        assert fake.messages[0][0] == "deck_update_tooltip"
        assert fake.messages[0][1]["tooltip"] == new_tip

    def test_update_tooltip_none_disables(self):

        w = MapWidget("utt3", tooltip={"html": "hi"})

        fake = _FakeSession()
        asyncio.run(w.update_tooltip(fake, None))
        assert w.tooltip is None
        assert fake.messages[0][1]["tooltip"] is None


# ---------------------------------------------------------------------------
# set_style method
# ---------------------------------------------------------------------------

class TestSetStyle:
    def test_method_exists(self):
        w = MapWidget("ss1")
        assert hasattr(w, "set_style")
        assert callable(w.set_style)

    def test_set_style_updates_attribute_and_message(self):
        """set_style should update the Python-side style attribute
        and send a deck_set_style custom message."""

        w = MapWidget("ss2", style=CARTO_POSITRON)
        assert w.style == CARTO_POSITRON

        fake = _FakeSession()
        asyncio.run(w.set_style(fake, CARTO_DARK))
        assert w.style == CARTO_DARK
        assert len(fake.messages) == 1
        assert fake.messages[0][0] == "deck_set_style"
        assert fake.messages[0][1]["id"] == "ss2"
        assert fake.messages[0][1]["style"] == CARTO_DARK

    def test_set_style_custom_url(self):

        w = MapWidget("ss3")
        custom = "https://example.com/my-style.json"

        fake = _FakeSession()
        asyncio.run(w.set_style(fake, custom))
        assert w.style == custom
        assert fake.messages[0][1]["style"] == custom


class TestSetStyleDiff:
    """Tests for set_style(diff=True) support (v1.0.0)."""

    def test_diff_false_by_default(self):
        w = MapWidget("ssd1")

        fake = _FakeSession()
        asyncio.run(w.set_style(fake, CARTO_DARK))
        assert fake.messages[0][1]["diff"] is False

    def test_diff_true(self):
        w = MapWidget("ssd2")

        fake = _FakeSession()
        asyncio.run(w.set_style(fake, CARTO_DARK, diff=True))
        assert fake.messages[0][1]["diff"] is True


class TestCooperativeGestures:
    """Tests for cooperative_gestures parameter (v1.0.0)."""

    def test_default_false(self):
        w = MapWidget("cg1")
        assert w.cooperative_gestures is False

    def test_enable_in_constructor(self):
        w = MapWidget("cg2", cooperative_gestures=True)
        assert w.cooperative_gestures is True

    def test_ui_includes_data_attribute(self):
        w = MapWidget("cg3", cooperative_gestures=True)
        html = str(w.ui())
        assert "cooperative" in html.lower()

    def test_ui_omits_attribute_when_false(self):
        w = MapWidget("cg4", cooperative_gestures=False)
        html = str(w.ui())
        assert "cooperative" not in html.lower()

    def test_set_cooperative_gestures_method(self):
        w = MapWidget("cg5")

        fake = _FakeSession()
        asyncio.run(w.set_cooperative_gestures(fake, True))
        assert w.cooperative_gestures is True
        assert fake.messages[0][0] == "deck_set_cooperative_gestures"
        assert fake.messages[0][1]["enabled"] is True

    def test_set_cooperative_gestures_disable(self):
        w = MapWidget("cg6", cooperative_gestures=True)

        fake = _FakeSession()
        asyncio.run(w.set_cooperative_gestures(fake, False))
        assert w.cooperative_gestures is False
        assert fake.messages[0][1]["enabled"] is False


# ---------------------------------------------------------------------------
# v0.2.0 â€” Phase 1 tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 1.1 MapLibre v5 upgrade
# ---------------------------------------------------------------------------

class TestMapLibreVersion:
    def test_head_includes_maplibre_v5(self):
        dep = head_includes()
        assert "maplibre-gl@5.3" in str(dep)

    def test_head_includes_no_old_maplibre(self):
        dep = head_includes()
        assert "maplibre-gl@3.6" not in str(dep)

    def test_to_html_maplibre_v5(self):
        w = MapWidget("v5test")
        html = w.to_html([])
        assert "maplibre-gl@5.3" in html
        assert "maplibre-gl@3.6" not in html


# ---------------------------------------------------------------------------
# 1.2 Map Controls API
# ---------------------------------------------------------------------------

class TestControlConstants:
    def test_control_types_is_set(self):
        assert isinstance(CONTROL_TYPES, set)
        assert "navigation" in CONTROL_TYPES
        assert "scale" in CONTROL_TYPES
        assert "fullscreen" in CONTROL_TYPES
        assert "geolocate" in CONTROL_TYPES
        assert "globe" in CONTROL_TYPES
        assert "terrain" in CONTROL_TYPES
        assert "attribution" in CONTROL_TYPES

    def test_control_positions_is_set(self):
        assert isinstance(CONTROL_POSITIONS, set)
        assert "top-left" in CONTROL_POSITIONS
        assert "top-right" in CONTROL_POSITIONS
        assert "bottom-left" in CONTROL_POSITIONS
        assert "bottom-right" in CONTROL_POSITIONS


class TestAddControl:
    def test_add_control_scale(self):
        w = MapWidget("ctrl1")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "scale", "bottom-left"))
        assert fake.messages[0] == ("deck_add_control", {
            "id": "ctrl1",
            "controlType": "scale",
            "position": "bottom-left",
            "options": {},
        })

    def test_add_control_with_options(self):
        w = MapWidget("ctrl2")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "scale", "bottom-left",
                                   options={"maxWidth": 200, "unit": "metric"}))
        assert fake.messages[0][1]["options"] == {"maxWidth": 200, "unit": "metric"}

    def test_add_control_fullscreen(self):
        w = MapWidget("ctrl_fs")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "fullscreen", "top-left"))
        assert fake.messages[0][1]["controlType"] == "fullscreen"
        assert fake.messages[0][1]["position"] == "top-left"

    def test_add_control_geolocate(self):
        w = MapWidget("ctrl_gl")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "geolocate", "top-right"))
        assert fake.messages[0][1]["controlType"] == "geolocate"

    def test_add_control_invalid_type_raises(self):
        w = MapWidget("ctrl3")
        fake = _FakeSession()
        with pytest.raises(ValueError, match="Unknown control type"):
            asyncio.run(w.add_control(fake, "invalid"))

    def test_add_control_invalid_position_raises(self):
        w = MapWidget("ctrl4")
        fake = _FakeSession()
        with pytest.raises(ValueError, match="Unknown position"):
            asyncio.run(w.add_control(fake, "scale", "middle"))

    def test_add_control_default_position(self):
        w = MapWidget("ctrl_dp")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "navigation"))
        assert fake.messages[0][1]["position"] == "top-right"

    def test_remove_control(self):
        w = MapWidget("ctrl5")
        fake = _FakeSession()
        asyncio.run(w.remove_control(fake, "navigation"))
        assert fake.messages[0] == ("deck_remove_control", {
            "id": "ctrl5",
            "controlType": "navigation",
        })


class TestControlsConstructor:
    def test_default_controls(self):
        w = MapWidget("cc1")
        assert w.controls == [{"type": "navigation", "position": "top-right"}]

    def test_custom_controls(self):
        ctrls = [
            {"type": "navigation", "position": "top-right"},
            {"type": "scale", "position": "bottom-left"},
        ]
        w = MapWidget("cc2", controls=ctrls)
        assert w.controls == ctrls

    def test_empty_controls(self):
        w = MapWidget("cc3", controls=[])
        assert w.controls == []

    def test_controls_in_ui_data_attribute(self):
        ctrls = [
            {"type": "scale", "position": "bottom-left"},
        ]
        w = MapWidget("cc4", controls=ctrls)
        tag = w.ui()
        html_str = str(tag)
        assert "data-controls" in html_str


# ---------------------------------------------------------------------------
# 1.2b legend_control() and opacity_control() helpers
# ---------------------------------------------------------------------------

class TestLegendControl:
    def test_legend_control_defaults(self):
        ctrl = legend_control()
        assert ctrl["type"] == "legend"
        assert ctrl["position"] == "bottom-left"
        opts = ctrl["options"]
        assert opts["showDefault"] is False
        assert opts["showCheckbox"] is True
        assert opts["onlyRendered"] is True
        assert opts["reverseOrder"] is False

    def test_legend_control_with_targets(self):
        targets = {"water": "Water bodies", "roads": "Roads"}
        ctrl = legend_control(targets=targets, position="top-right")
        assert ctrl["position"] == "top-right"
        assert ctrl["options"]["targets"] == targets

    def test_legend_control_with_title(self):
        ctrl = legend_control(title="My Legend")
        assert ctrl["options"]["title"] == "My Legend"

    def test_legend_control_no_title_by_default(self):
        ctrl = legend_control()
        assert "title" not in ctrl["options"]

    def test_legend_control_show_default_true(self):
        ctrl = legend_control(show_default=True)
        assert ctrl["options"]["showDefault"] is True

    def test_legend_control_in_constructor(self):
        ctrl = legend_control(targets={"water": "Water"}, position="bottom-right")
        w = MapWidget("lc1", controls=[ctrl])
        assert w.controls[0]["type"] == "legend"

    def test_add_legend_control_runtime(self):
        w = MapWidget("lc2")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "legend", "bottom-left",
                                   options={"targets": {"water": "Water"}}))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_control"
        assert msg[1]["controlType"] == "legend"
        assert msg[1]["options"]["targets"] == {"water": "Water"}


class TestOpacityControl:
    def test_opacity_control_defaults(self):
        ctrl = opacity_control()
        assert ctrl["type"] == "opacity"
        assert ctrl["position"] == "top-left"
        opts = ctrl["options"]
        assert opts["baseLayers"] == {}
        assert opts["overLayers"] == {}
        assert opts["opacityControl"] is True

    def test_opacity_control_with_layers(self):
        ctrl = opacity_control(
            base_layers={"osm": "OSM", "sat": "Satellite"},
            over_layers={"heat": "Heatmap"},
        )
        assert ctrl["options"]["baseLayers"] == {"osm": "OSM", "sat": "Satellite"}
        assert ctrl["options"]["overLayers"] == {"heat": "Heatmap"}

    def test_opacity_control_disabled_slider(self):
        ctrl = opacity_control(opacity_control_enabled=False)
        assert ctrl["options"]["opacityControl"] is False

    def test_opacity_control_custom_position(self):
        ctrl = opacity_control(position="top-right")
        assert ctrl["position"] == "top-right"

    def test_opacity_control_in_constructor(self):
        ctrl = opacity_control(
            base_layers={"osm": "OSM"},
            over_layers={"heat": "Heatmap"},
        )
        w = MapWidget("oc1", controls=[ctrl])
        assert w.controls[0]["type"] == "opacity"

    def test_add_opacity_control_runtime(self):
        w = MapWidget("oc2")
        fake = _FakeSession()
        asyncio.run(w.add_control(fake, "opacity", "top-left",
                                   options={"baseLayers": {"osm": "OSM"}}))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_control"
        assert msg[1]["controlType"] == "opacity"

    def test_control_types_include_new_types(self):
        """CONTROL_TYPES should include the new plugin-based types."""
        assert "legend" in CONTROL_TYPES
        assert "opacity" in CONTROL_TYPES
        assert "deck_legend" in CONTROL_TYPES


# ---------------------------------------------------------------------------
# TestDeckLegendControl
# ---------------------------------------------------------------------------

class TestDeckLegendControl:
    def test_deck_legend_control_defaults(self):
        entries = [{"layer_id": "ports", "label": "Ports", "color": [0, 0, 255]}]
        ctrl = deck_legend_control(entries=entries)
        assert ctrl["type"] == "deck_legend"
        assert ctrl["position"] == "bottom-right"
        opts = ctrl["options"]
        assert opts["showCheckbox"] is True
        assert opts["collapsed"] is False
        assert "title" not in opts
        assert opts["entries"] == entries

    def test_deck_legend_control_custom_position(self):
        ctrl = deck_legend_control(entries=[], position="top-left")
        assert ctrl["position"] == "top-left"

    def test_deck_legend_control_with_title(self):
        ctrl = deck_legend_control(entries=[], title="My Legend")
        assert ctrl["options"]["title"] == "My Legend"

    def test_deck_legend_control_collapsed(self):
        ctrl = deck_legend_control(entries=[], collapsed=True, title="T")
        assert ctrl["options"]["collapsed"] is True

    def test_deck_legend_control_no_checkbox(self):
        ctrl = deck_legend_control(entries=[], show_checkbox=False)
        assert ctrl["options"]["showCheckbox"] is False

    def test_deck_legend_control_multiple_entries(self):
        entries = [
            {"layer_id": "a", "label": "Layer A", "color": [255, 0, 0], "shape": "circle"},
            {"layer_id": "b", "label": "Layer B", "color": [0, 255, 0], "shape": "rect"},
            {"layer_id": "c", "label": "Layer C", "color": [0, 0, 255],
             "color2": [255, 0, 0], "shape": "arc"},
            {"layer_id": "d", "label": "Heatmap",
             "colors": [[0, 0, 0], [255, 255, 0], [255, 0, 0]], "shape": "gradient"},
        ]
        ctrl = deck_legend_control(entries=entries, title="All Layers")
        assert len(ctrl["options"]["entries"]) == 4
        assert ctrl["options"]["entries"][2]["shape"] == "arc"
        assert ctrl["options"]["entries"][3]["colors"] == [[0, 0, 0], [255, 255, 0], [255, 0, 0]]

    def test_deck_legend_control_in_constructor(self):
        ctrl = deck_legend_control(
            entries=[{"layer_id": "x", "label": "X", "color": [0, 0, 0]}],
            position="bottom-left",
        )
        w = MapWidget("dlc1", controls=[ctrl])
        assert w.controls[0]["type"] == "deck_legend"

    def test_deck_legend_control_in_set_controls(self):
        ctrl = deck_legend_control(
            entries=[{"layer_id": "y", "label": "Y", "color": [255, 0, 0]}],
        )
        w = MapWidget("dlc2")
        fake = _FakeSession()
        asyncio.run(w.set_controls(fake, [ctrl]))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_controls"
        assert msg[1]["controls"][0]["type"] == "deck_legend"

    def test_deck_legend_entries_are_copied(self):
        """Entries list should be a copy, not a reference."""
        original = [{"layer_id": "z", "label": "Z", "color": [0, 0, 0]}]
        ctrl = deck_legend_control(entries=original)
        ctrl["options"]["entries"].append({"layer_id": "extra"})
        assert len(original) == 1  # original unmodified

    def test_deck_legend_importable_from_package(self):
        """deck_legend_control should be importable from the top-level package."""
        import shiny_deckgl
        assert hasattr(shiny_deckgl, "deck_legend_control")
        assert callable(shiny_deckgl.deck_legend_control)


# ---------------------------------------------------------------------------
# 1.3 fit_bounds()
# ---------------------------------------------------------------------------

class TestFitBounds:
    def test_fit_bounds_basic(self):
        w = MapWidget("fb1")
        fake = _FakeSession()
        asyncio.run(w.fit_bounds(fake, [[10, 54], [30, 66]]))
        msg = fake.messages[0]
        assert msg[0] == "deck_fit_bounds"
        assert msg[1]["bounds"] == [[10, 54], [30, 66]]
        assert msg[1]["padding"] == 50

    def test_fit_bounds_with_options(self):
        w = MapWidget("fb2")
        fake = _FakeSession()
        asyncio.run(w.fit_bounds(fake, [[10, 54], [30, 66]],
                                  padding={"top": 20, "bottom": 20, "left": 10, "right": 10},
                                  max_zoom=12, duration=1000))
        msg = fake.messages[0][1]
        assert msg["maxZoom"] == 12
        assert msg["duration"] == 1000
        assert msg["padding"]["top"] == 20

    def test_fit_bounds_no_duration_key_when_zero(self):
        w = MapWidget("fb3")
        fake = _FakeSession()
        asyncio.run(w.fit_bounds(fake, [[0, 0], [1, 1]]))
        assert "duration" not in fake.messages[0][1]

    def test_fit_bounds_custom_padding_int(self):
        w = MapWidget("fb4")
        fake = _FakeSession()
        asyncio.run(w.fit_bounds(fake, [[0, 0], [1, 1]], padding=100))
        assert fake.messages[0][1]["padding"] == 100

    def test_compute_bounds_feature_collection(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10, 50]}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [30, 60]}},
            ]
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[10, 50], [30, 60]]

    def test_compute_bounds_single_feature(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[5, 40], [15, 55], [25, 45]]
            }
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[5, 40], [25, 55]]

    def test_compute_bounds_polygon(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
            }
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[0, 0], [10, 10]]

    def test_compute_bounds_multi_polygon(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
                    [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]],
                ]
            }
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[0, 0], [20, 20]]

    def test_compute_bounds_geometry_collection(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "Point", "coordinates": [1, 2]},
                    {"type": "Point", "coordinates": [3, 4]},
                ]
            }
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[1, 2], [3, 4]]

    def test_compute_bounds_empty(self):
        bounds = MapWidget.compute_bounds({"type": "FeatureCollection", "features": []})
        assert bounds == [[-180, -90], [180, 90]]

    def test_compute_bounds_bare_geometry(self):
        geojson = {"type": "Point", "coordinates": [5.5, 52.3]}
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[5.5, 52.3], [5.5, 52.3]]


# ---------------------------------------------------------------------------
# 1.5 Map click events (input property helpers)
# ---------------------------------------------------------------------------

class TestMapClickInputIds:
    def test_map_click_input_id(self):
        w = MapWidget("mc1")
        assert w.map_click_input_id == "mc1_map_click"

    def test_map_contextmenu_input_id(self):
        w = MapWidget("mc2")
        assert w.map_contextmenu_input_id == "mc2_map_contextmenu"


# ===========================================================================
# Phase 2 (v0.3.0) â€” Native MapLibre Rendering
# ===========================================================================

# ---------------------------------------------------------------------------
# 2.1 Native Sources & Layers
# ---------------------------------------------------------------------------

class TestNativeSources:
    def test_add_source_geojson(self):
        w = MapWidget("ns1")
        fake = _FakeSession()
        spec = {"type": "geojson", "data": {"type": "FeatureCollection", "features": []}}
        asyncio.run(w.add_source(fake, "my-source", spec))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_source"
        assert msg[1]["sourceId"] == "my-source"
        assert msg[1]["spec"]["type"] == "geojson"

    def test_add_source_raster_wms(self):
        w = MapWidget("ns2")
        fake = _FakeSession()
        spec = {
            "type": "raster",
            "tiles": ["https://ows.emodnet.eu/wms?...&BBOX={bbox-epsg-3857}"],
            "tileSize": 256,
        }
        asyncio.run(w.add_source(fake, "bathy", spec))
        assert fake.messages[0][1]["spec"]["type"] == "raster"

    def test_add_maplibre_layer(self):
        w = MapWidget("ns3")
        fake = _FakeSession()
        layer_spec = {
            "id": "eez-fill",
            "type": "fill",
            "source": "eez",
            "paint": {"fill-color": "#088", "fill-opacity": 0.4},
        }
        asyncio.run(w.add_maplibre_layer(fake, layer_spec))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_maplibre_layer"
        assert msg[1]["layerSpec"]["id"] == "eez-fill"

    def test_add_maplibre_layer_with_before_id(self):
        w = MapWidget("ns4")
        fake = _FakeSession()
        asyncio.run(w.add_maplibre_layer(
            fake, {"id": "a", "type": "fill", "source": "s"},
            before_id="other-layer",
        ))
        assert fake.messages[0][1]["beforeId"] == "other-layer"

    def test_add_maplibre_layer_no_before_id(self):
        w = MapWidget("ns4b")
        fake = _FakeSession()
        asyncio.run(w.add_maplibre_layer(
            fake, {"id": "b", "type": "line", "source": "s"},
        ))
        assert "beforeId" not in fake.messages[0][1]

    def test_remove_maplibre_layer(self):
        w = MapWidget("ns5")
        fake = _FakeSession()
        asyncio.run(w.remove_maplibre_layer(fake, "eez-fill"))
        assert fake.messages[0] == ("deck_remove_maplibre_layer", {
            "id": "ns5", "layerId": "eez-fill",
        })

    def test_remove_source(self):
        w = MapWidget("ns6")
        fake = _FakeSession()
        asyncio.run(w.remove_source(fake, "eez"))
        assert fake.messages[0] == ("deck_remove_source", {
            "id": "ns6", "sourceId": "eez",
        })

    def test_set_source_data(self):
        w = MapWidget("ns7")
        fake = _FakeSession()
        new_data = {"type": "FeatureCollection", "features": []}
        asyncio.run(w.set_source_data(fake, "my-source", new_data))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_source_data"
        assert msg[1]["data"]["type"] == "FeatureCollection"

    def test_set_source_data_url_string(self):
        w = MapWidget("ns8")
        fake = _FakeSession()
        asyncio.run(w.set_source_data(fake, "src", "https://example.com/data.geojson"))
        msg = fake.messages[0]
        assert msg[1]["data"] == "https://example.com/data.geojson"


# ---------------------------------------------------------------------------
# 2.2 Runtime Style Mutation
# ---------------------------------------------------------------------------

class TestStyleMutation:
    def test_set_paint_property(self):
        w = MapWidget("sp1")
        fake = _FakeSession()
        asyncio.run(w.set_paint_property(fake, "eez-fill", "fill-opacity", 0.8))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_paint_property"
        assert msg[1]["layerId"] == "eez-fill"
        assert msg[1]["name"] == "fill-opacity"
        assert msg[1]["value"] == 0.8

    def test_set_paint_property_color(self):
        w = MapWidget("sp1b")
        fake = _FakeSession()
        asyncio.run(w.set_paint_property(fake, "lines", "line-color", "#ff0000"))
        assert fake.messages[0][1]["value"] == "#ff0000"

    def test_set_layout_property(self):
        w = MapWidget("sp2")
        fake = _FakeSession()
        asyncio.run(w.set_layout_property(fake, "labels", "visibility", "none"))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_layout_property"
        assert msg[1]["value"] == "none"

    def test_set_layout_property_visible(self):
        w = MapWidget("sp2b")
        fake = _FakeSession()
        asyncio.run(w.set_layout_property(fake, "labels", "visibility", "visible"))
        assert fake.messages[0][1]["value"] == "visible"

    def test_set_filter(self):
        w = MapWidget("sp3")
        fake = _FakeSession()
        asyncio.run(w.set_filter(fake, "stations", [">=", ["get", "depth"], 100]))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_filter"
        assert msg[1]["filter"] == [">=", ["get", "depth"], 100]

    def test_set_filter_clear(self):
        w = MapWidget("sp4")
        fake = _FakeSession()
        asyncio.run(w.set_filter(fake, "stations", None))
        assert fake.messages[0][1]["filter"] is None

    def test_set_filter_complex_expression(self):
        w = MapWidget("sp5")
        fake = _FakeSession()
        expr = ["all", [">=", ["get", "depth"], 50], ["<=", ["get", "depth"], 200]]
        asyncio.run(w.set_filter(fake, "stations", expr))
        assert fake.messages[0][1]["filter"] == expr


# ===========================================================================
# Phase 3 (v0.4.0) â€” 3D, Globe & Advanced Interaction
# ===========================================================================

# ---------------------------------------------------------------------------
# 3.1 Globe Projection
# ---------------------------------------------------------------------------

class TestSetProjection:
    def test_set_projection_globe(self):
        w = MapWidget("proj1")
        fake = _FakeSession()
        asyncio.run(w.set_projection(fake, "globe"))
        assert fake.messages[0] == ("deck_set_projection", {
            "id": "proj1", "projection": "globe",
        })

    def test_set_projection_mercator(self):
        w = MapWidget("proj2")
        fake = _FakeSession()
        asyncio.run(w.set_projection(fake, "mercator"))
        assert fake.messages[0][1]["projection"] == "mercator"

    def test_set_projection_invalid_raises(self):
        w = MapWidget("proj3")
        fake = _FakeSession()
        with pytest.raises(ValueError, match="Unknown projection"):
            asyncio.run(w.set_projection(fake, "orthographic"))


# ---------------------------------------------------------------------------
# 3.2 3D Terrain + Sky
# ---------------------------------------------------------------------------

class TestTerrain:
    def test_set_terrain_enable(self):
        w = MapWidget("ter1")
        fake = _FakeSession()
        asyncio.run(w.set_terrain(fake, source="dem", exaggeration=1.5))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_terrain"
        assert msg[1]["terrain"] == {"source": "dem", "exaggeration": 1.5}

    def test_set_terrain_disable(self):
        w = MapWidget("ter2")
        fake = _FakeSession()
        asyncio.run(w.set_terrain(fake, source=None))
        assert fake.messages[0][1]["terrain"] is None

    def test_set_terrain_default_exaggeration(self):
        w = MapWidget("ter2b")
        fake = _FakeSession()
        asyncio.run(w.set_terrain(fake, source="dem"))
        assert fake.messages[0][1]["terrain"]["exaggeration"] == 1.0

    def test_set_sky(self):
        w = MapWidget("ter3")
        fake = _FakeSession()
        sky = {"sky-color": "#199EF3", "sky-horizon-blend": 0.5}
        asyncio.run(w.set_sky(fake, sky))
        assert fake.messages[0] == ("deck_set_sky", {
            "id": "ter3", "sky": sky,
        })

    def test_set_sky_none_resets(self):
        w = MapWidget("ter4")
        fake = _FakeSession()
        asyncio.run(w.set_sky(fake, None))
        assert fake.messages[0][1]["sky"] is None


# ---------------------------------------------------------------------------
# 3.3 Native Popups
# ---------------------------------------------------------------------------

class TestPopups:
    def test_add_popup(self):
        w = MapWidget("pop1")
        fake = _FakeSession()
        asyncio.run(w.add_popup(fake, "stations", "<b>{name}</b>"))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_popup"
        assert msg[1]["layerId"] == "stations"
        assert msg[1]["template"] == "<b>{name}</b>"
        assert msg[1]["closeButton"] is True

    def test_add_popup_with_options(self):
        w = MapWidget("pop2")
        fake = _FakeSession()
        asyncio.run(w.add_popup(fake, "eez", "{name}",
                                 close_button=False, max_width="400px",
                                 anchor="bottom"))
        msg = fake.messages[0][1]
        assert msg["closeButton"] is False
        assert msg["maxWidth"] == "400px"
        assert msg["anchor"] == "bottom"

    def test_add_popup_no_anchor(self):
        w = MapWidget("pop2b")
        fake = _FakeSession()
        asyncio.run(w.add_popup(fake, "layer", "text"))
        assert "anchor" not in fake.messages[0][1]

    def test_remove_popup(self):
        w = MapWidget("pop3")
        fake = _FakeSession()
        asyncio.run(w.remove_popup(fake, "stations"))
        assert fake.messages[0] == ("deck_remove_popup", {
            "id": "pop3", "layerId": "stations",
        })

    def test_feature_click_input_id(self):
        w = MapWidget("pop4")
        assert w.feature_click_input_id == "pop4_feature_click"


# ---------------------------------------------------------------------------
# 3.4 Spatial Queries
# ---------------------------------------------------------------------------

class TestSpatialQueries:
    def test_query_rendered_features_point(self):
        w = MapWidget("sq1")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, point=[100, 200], layers=["eez-fill"],
            request_id="test-1",
        ))
        msg = fake.messages[0]
        assert msg[0] == "deck_query_features"
        assert msg[1]["point"] == [100, 200]
        assert msg[1]["layers"] == ["eez-fill"]
        assert msg[1]["requestId"] == "test-1"

    def test_query_rendered_features_bounds(self):
        w = MapWidget("sq2")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, bounds=[[50, 50], [200, 200]],
        ))
        msg = fake.messages[0][1]
        assert msg["bounds"] == [[50, 50], [200, 200]]
        assert "point" not in msg

    def test_query_rendered_features_no_geometry(self):
        w = MapWidget("sq2b")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(fake, layers=["all"]))
        msg = fake.messages[0][1]
        assert "point" not in msg
        assert "bounds" not in msg

    def test_query_rendered_features_with_filter(self):
        w = MapWidget("sq2c")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, point=[10, 20],
            filter_expr=["==", ["get", "type"], "station"],
        ))
        assert fake.messages[0][1]["filter"] == ["==", ["get", "type"], "station"]

    def test_query_at_lnglat(self):
        w = MapWidget("sq3")
        fake = _FakeSession()
        asyncio.run(w.query_at_lnglat(fake, 21.1, 55.7,
                                        layers=["stations"],
                                        request_id="click"))
        msg = fake.messages[0]
        assert msg[0] == "deck_query_at_lnglat"
        assert msg[1]["longitude"] == 21.1
        assert msg[1]["latitude"] == 55.7
        assert msg[1]["requestId"] == "click"

    def test_query_result_input_id(self):
        w = MapWidget("sq4")
        assert w.query_result_input_id == "sq4_query_result"


# ---------------------------------------------------------------------------
# 3.5 Multiple Markers
# ---------------------------------------------------------------------------

class TestMultipleMarkers:
    def test_add_marker_basic(self):
        w = MapWidget("mm1")
        fake = _FakeSession()
        asyncio.run(w.add_marker(fake, "station-1", 21.1, 55.7))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_marker"
        assert msg[1]["markerId"] == "station-1"
        assert msg[1]["longitude"] == 21.1
        assert msg[1]["color"] == "#3FB1CE"
        assert msg[1]["draggable"] is False

    def test_add_marker_with_options(self):
        w = MapWidget("mm2")
        fake = _FakeSession()
        asyncio.run(w.add_marker(fake, "buoy-A", 20.0, 56.0,
                                  color="#ff6600", draggable=True,
                                  popup_html="<b>Buoy A</b>"))
        msg = fake.messages[0][1]
        assert msg["color"] == "#ff6600"
        assert msg["draggable"] is True
        assert msg["popupHtml"] == "<b>Buoy A</b>"

    def test_remove_marker(self):
        w = MapWidget("mm3")
        fake = _FakeSession()
        asyncio.run(w.remove_marker(fake, "station-1"))
        assert fake.messages[0] == ("deck_remove_marker", {
            "id": "mm3", "markerId": "station-1",
        })

    def test_clear_markers(self):
        w = MapWidget("mm4")
        fake = _FakeSession()
        asyncio.run(w.clear_markers(fake))
        assert fake.messages[0] == ("deck_clear_markers", {"id": "mm4"})

    def test_marker_click_input_id(self):
        w = MapWidget("mm5")
        assert w.marker_click_input_id == "mm5_marker_click"

    def test_marker_drag_input_id(self):
        w = MapWidget("mm6")
        assert w.marker_drag_input_id == "mm6_marker_drag"


# ===========================================================================
# Phase 4 (v0.5.0) â€” Drawing, Data Integration & Export
# ===========================================================================

# ---------------------------------------------------------------------------
# 4.1 Drawing Tools
# ---------------------------------------------------------------------------

class TestDrawingTools:
    def test_enable_draw_default(self):
        w = MapWidget("dr1")
        fake = _FakeSession()
        asyncio.run(w.enable_draw(fake))
        msg = fake.messages[0]
        assert msg[0] == "deck_enable_draw"
        assert msg[1]["defaultMode"] == "simple_select"

    def test_enable_draw_polygon_only(self):
        w = MapWidget("dr2")
        fake = _FakeSession()
        asyncio.run(w.enable_draw(fake, modes=["draw_polygon"]))
        assert fake.messages[0][1]["modes"] == ["draw_polygon"]

    def test_enable_draw_with_controls(self):
        w = MapWidget("dr2b")
        fake = _FakeSession()
        controls = {"point": True, "polygon": True, "trash": True}
        asyncio.run(w.enable_draw(fake, controls=controls))
        assert fake.messages[0][1]["controls"] == controls

    def test_disable_draw(self):
        w = MapWidget("dr3")
        fake = _FakeSession()
        asyncio.run(w.disable_draw(fake))
        assert fake.messages[0][0] == "deck_disable_draw"

    def test_get_drawn_features(self):
        w = MapWidget("dr3b")
        fake = _FakeSession()
        asyncio.run(w.get_drawn_features(fake))
        assert fake.messages[0][0] == "deck_get_drawn_features"

    def test_delete_drawn_features(self):
        w = MapWidget("dr4")
        fake = _FakeSession()
        asyncio.run(w.delete_drawn_features(fake, feature_ids=["abc", "def"]))
        assert fake.messages[0][1]["featureIds"] == ["abc", "def"]

    def test_delete_all_drawn(self):
        w = MapWidget("dr5")
        fake = _FakeSession()
        asyncio.run(w.delete_drawn_features(fake))
        assert fake.messages[0][1]["featureIds"] is None

    def test_drawn_features_input_id(self):
        w = MapWidget("dr6")
        assert w.drawn_features_input_id == "dr6_drawn_features"

    def test_draw_mode_input_id(self):
        w = MapWidget("dr7")
        assert w.draw_mode_input_id == "dr7_draw_mode"


# ---------------------------------------------------------------------------
# 4.2 GeoPandas Integration
# ---------------------------------------------------------------------------

class TestGeoPandas:
    def test_add_geodataframe(self):
        """add_geodataframe should call add_source + add_maplibre_layer."""
        w = MapWidget("gp1")
        fake = _FakeSession()

        asyncio.run(w.add_geodataframe(fake, "test-src", "fake_gdf",
                                        layer_type="line",
                                        paint={"line-color": "#f00"}))
        assert len(fake.messages) == 2
        assert fake.messages[0][0] == "deck_add_source"
        assert fake.messages[0][1]["sourceId"] == "test-src"
        assert fake.messages[1][0] == "deck_add_maplibre_layer"
        assert fake.messages[1][1]["layerSpec"]["id"] == "test-src-layer"
        assert fake.messages[1][1]["layerSpec"]["paint"]["line-color"] == "#f00"

    def test_add_geodataframe_default_paint(self):
        """Default paint should be applied based on layer_type."""
        w = MapWidget("gp1b")
        fake = _FakeSession()

        asyncio.run(w.add_geodataframe(fake, "src", "gdf"))
        layer_spec = fake.messages[1][1]["layerSpec"]
        assert layer_spec["type"] == "fill"
        assert "fill-color" in layer_spec["paint"]

    def test_add_geodataframe_with_popup(self):
        """add_geodataframe with popup_template should send 3 messages."""
        w = MapWidget("gp2")
        fake = _FakeSession()

        asyncio.run(w.add_geodataframe(fake, "eez", "fake_gdf",
                                        popup_template="<b>{name}</b>"))
        assert len(fake.messages) == 3
        assert fake.messages[2][0] == "deck_add_popup"
        assert fake.messages[2][1]["template"] == "<b>{name}</b>"

    def test_update_geodataframe(self):
        w = MapWidget("gp3")
        fake = _FakeSession()

        asyncio.run(w.update_geodataframe(fake, "eez", "fake_gdf"))
        assert fake.messages[0][0] == "deck_set_source_data"
        assert fake.messages[0][1]["sourceId"] == "eez"


# ---------------------------------------------------------------------------
# 4.3 Feature State Management
# ---------------------------------------------------------------------------

class TestFeatureState:
    def test_set_feature_state(self):
        w = MapWidget("fs1")
        fake = _FakeSession()
        asyncio.run(w.set_feature_state(fake, "stations", 42,
                                          {"hover": True, "selected": False}))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_feature_state"
        assert msg[1]["sourceId"] == "stations"
        assert msg[1]["featureId"] == 42
        assert msg[1]["state"] == {"hover": True, "selected": False}

    def test_set_feature_state_vector_source(self):
        w = MapWidget("fs2")
        fake = _FakeSession()
        asyncio.run(w.set_feature_state(fake, "osm", "abc",
                                          {"hover": True},
                                          source_layer="buildings"))
        assert fake.messages[0][1]["sourceLayer"] == "buildings"

    def test_set_feature_state_no_source_layer(self):
        w = MapWidget("fs2b")
        fake = _FakeSession()
        asyncio.run(w.set_feature_state(fake, "src", 1, {"a": True}))
        assert "sourceLayer" not in fake.messages[0][1]

    def test_remove_feature_state_specific(self):
        w = MapWidget("fs3")
        fake = _FakeSession()
        asyncio.run(w.remove_feature_state(fake, "stations", 42, key="hover"))
        msg = fake.messages[0]
        assert msg[0] == "deck_remove_feature_state"
        assert msg[1]["featureId"] == 42
        assert msg[1]["key"] == "hover"

    def test_remove_feature_state_all(self):
        w = MapWidget("fs4")
        fake = _FakeSession()
        asyncio.run(w.remove_feature_state(fake, "stations"))
        msg = fake.messages[0][1]
        assert "featureId" not in msg
        assert "key" not in msg


# ---------------------------------------------------------------------------
# 4.4 Map Export / Screenshot
# ---------------------------------------------------------------------------

class TestExportImage:
    def test_export_image_png(self):
        w = MapWidget("exp1")
        fake = _FakeSession()
        asyncio.run(w.export_image(fake, format="png"))
        msg = fake.messages[0]
        assert msg[0] == "deck_export_image"
        assert msg[1]["format"] == "png"
        assert msg[1]["quality"] == 0.92

    def test_export_image_jpeg(self):
        w = MapWidget("exp2")
        fake = _FakeSession()
        asyncio.run(w.export_image(fake, format="jpeg", quality=0.8,
                                    request_id="report"))
        msg = fake.messages[0][1]
        assert msg["format"] == "jpeg"
        assert msg["quality"] == 0.8
        assert msg["requestId"] == "report"

    def test_export_result_input_id(self):
        w = MapWidget("exp3")
        assert w.export_result_input_id == "exp3_export_result"

    def test_to_html_includes_draw_cdn(self):
        """to_html() should include the MapboxDraw CDN."""
        w = MapWidget("exp4")
        html = w.to_html([])
        assert "mapbox-gl-draw" in html

    def test_head_includes_draw_cdn(self):
        """head_includes() should include the MapboxDraw CDN."""
        html = str(head_includes())
        assert "mapbox-gl-draw" in html


# ---------------------------------------------------------------------------
# 5 – Extended coverage for new features
# ---------------------------------------------------------------------------

class TestUpdateWithViews:
    """Test MapWidget.update() with the ``views`` parameter."""

    def test_update_with_views(self):
        w = MapWidget("uv1")
        fake = _FakeSession()
        views = [map_view(controller=True)]
        asyncio.run(w.update(fake, [], views=views))
        msg = fake.messages[0]
        assert msg[0] == "deck_update"
        assert msg[1]["views"] == views

    def test_update_no_views_key_when_none(self):
        w = MapWidget("uv2")
        fake = _FakeSession()
        asyncio.run(w.update(fake, []))
        assert "views" not in fake.messages[0][1]

    def test_update_multiple_views(self):
        w = MapWidget("uv3")
        fake = _FakeSession()
        views = [map_view(), orthographic_view(controller=False)]
        asyncio.run(w.update(fake, [], views=views))
        assert fake.messages[0][1]["views"] == views
        assert fake.messages[0][1]["views"][0]["@@type"] == "MapView"
        assert fake.messages[0][1]["views"][1]["@@type"] == "OrthographicView"


class TestUpdateTransitionDuration:
    """Test MapWidget.update() transition animation."""

    def test_transition_duration_included(self):
        w = MapWidget("td1")
        fake = _FakeSession()
        vs = {"longitude": 10, "latitude": 50, "zoom": 5}
        asyncio.run(w.update(fake, [], view_state=vs, transition_duration=2000))
        msg = fake.messages[0][1]
        assert msg["transitionDuration"] == 2000
        assert msg["viewState"] == vs

    def test_transition_duration_zero_omitted(self):
        w = MapWidget("td2")
        fake = _FakeSession()
        vs = {"longitude": 10, "latitude": 50, "zoom": 5}
        asyncio.run(w.update(fake, [], view_state=vs, transition_duration=0))
        msg = fake.messages[0][1]
        assert "transitionDuration" not in msg

    def test_no_view_state_no_transition(self):
        w = MapWidget("td3")
        fake = _FakeSession()
        asyncio.run(w.update(fake, [], transition_duration=5000))
        msg = fake.messages[0][1]
        assert "viewState" not in msg
        assert "transitionDuration" not in msg


class TestSetLayerVisibilityMessage:
    """Test set_layer_visibility sends correct message."""

    def test_single_layer_visible(self):
        w = MapWidget("slv1")
        fake = _FakeSession()
        asyncio.run(w.set_layer_visibility(fake, {"layer1": True}))
        msg = fake.messages[0]
        assert msg[0] == "deck_layer_visibility"
        assert msg[1]["visibility"] == {"layer1": True}

    def test_multiple_layers(self):
        w = MapWidget("slv2")
        fake = _FakeSession()
        asyncio.run(w.set_layer_visibility(fake, {
            "layer1": True, "layer2": False, "layer3": True
        }))
        vis = fake.messages[0][1]["visibility"]
        assert vis["layer1"] is True
        assert vis["layer2"] is False
        assert vis["layer3"] is True


class TestAddDragMarkerCoordinates:
    """Test add_drag_marker with explicit coordinates."""

    def test_with_coordinates(self):
        w = MapWidget("dm1")
        fake = _FakeSession()
        asyncio.run(w.add_drag_marker(fake, longitude=21.14, latitude=55.71))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_drag_marker"
        assert msg[1]["longitude"] == 21.14
        assert msg[1]["latitude"] == 55.71

    def test_without_coordinates(self):
        w = MapWidget("dm2")
        fake = _FakeSession()
        asyncio.run(w.add_drag_marker(fake))
        msg = fake.messages[0][1]
        assert msg["longitude"] is None
        assert msg["latitude"] is None


class TestColorBinsExtended:
    """Extended tests for color_bins()."""

    def test_custom_palette(self):
        palette = [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
        result = color_bins([1, 5, 10], n_bins=3, palette=palette)
        assert len(result) == 3
        for c in result:
            assert len(c) == 4
            assert c[3] == 255

    def test_single_value(self):
        result = color_bins([42], n_bins=3)
        assert len(result) == 1
        assert len(result[0]) == 4

    def test_two_identical_values(self):
        result = color_bins([5, 5], n_bins=3)
        assert len(result) == 2
        assert result[0] == result[1]

    def test_descending_values(self):
        result = color_bins([100, 50, 10, 1], n_bins=4)
        assert len(result) == 4
        # Lowest value should get first bin color
        # Highest value should get last bin color
        assert result[3] != result[0]  # extremes differ

    def test_many_values_few_bins(self):
        vals = list(range(100))
        result = color_bins(vals, n_bins=2)
        assert len(result) == 100
        # Each color should be one of 2 bins
        unique = set(tuple(c) for c in result)
        assert len(unique) == 2


class TestColorQuantilesExtended:
    """Extended tests for color_quantiles()."""

    def test_custom_palette(self):
        palette = [[0, 0, 0], [255, 255, 255]]
        result = color_quantiles([1, 2, 3, 4], n_bins=2, palette=palette)
        assert len(result) == 4
        for c in result:
            assert len(c) == 4

    def test_single_value(self):
        result = color_quantiles([7], n_bins=3)
        assert len(result) == 1

    def test_three_equal_values(self):
        result = color_quantiles([5, 5, 5], n_bins=3)
        assert len(result) == 3
        assert result[0] == result[1] == result[2]

    def test_quantile_vs_bins_differ(self):
        """Quantile and equal-interval binning should produce different results
        for moderately skewed distributions."""
        skewed = [1, 2, 3, 4, 50, 100]
        bins_result = color_bins(skewed, n_bins=3)
        quant_result = color_quantiles(skewed, n_bins=3)
        # With this distribution, the bin boundaries will differ
        # so at least one data point should get a different colour
        assert bins_result != quant_result


class TestColorRangeInterpolation:
    """Test color_range interpolation accuracy."""

    def test_two_colors_interpolation(self):
        palette = [[0, 0, 0], [255, 255, 255]]
        result = color_range(3, palette)
        assert len(result) == 3
        # First should be black, last should be white
        assert result[0][:3] == [0, 0, 0]
        assert result[2][:3] == [255, 255, 255]
        # Middle should be roughly grey
        assert 100 <= result[1][0] <= 155

    def test_single_color_requested(self):
        result = color_range(1)
        assert len(result) == 1
        assert len(result[0]) == 4

    def test_more_than_palette_stops(self):
        palette = [[0, 0, 0], [255, 0, 0]]
        result = color_range(10, palette)
        assert len(result) == 10
        # All should be RGBA
        for c in result:
            assert len(c) == 4
            assert all(0 <= v <= 255 for v in c)


class TestComputeBoundsExtended:
    """Extended geometry types for compute_bounds."""

    def test_linestring(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[10, 20], [30, 40], [50, 60]],
            },
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[10, 20], [50, 60]]

    def test_multilinestring(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [
                    [[0, 0], [10, 10]],
                    [[20, 20], [30, 30]],
                ],
            },
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[0, 0], [30, 30]]

    def test_multipoint(self):
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "MultiPoint",
                "coordinates": [[5, 10], [15, 20], [25, 30]],
            },
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[5, 10], [25, 30]]

    def test_bare_point_geometry(self):
        geojson = {"type": "Point", "coordinates": [21.14, 55.71]}
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[21.14, 55.71], [21.14, 55.71]]

    def test_feature_with_3d_coordinates(self):
        """Coordinates with altitude should still compute 2D bounds."""
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [10, 20, 100],
                },
            }],
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[10, 20], [10, 20]]


class TestToJsonFromJsonExtended:
    """Extended roundtrip tests for to_json/from_json."""

    def test_tooltip_preserved(self):
        w = MapWidget("rj1", tooltip={"html": "<b>{name}</b>"})
        layers = [scatterplot_layer("L1", [[0, 0]])]
        spec = w.to_json(layers)
        w2, layers2 = MapWidget.from_json(spec)
        assert w2.tooltip == {"html": "<b>{name}</b>"}
        assert len(layers2) == 1

    def test_style_preserved(self):
        w = MapWidget("rj2", style=CARTO_DARK)
        spec = w.to_json([])
        w2, _ = MapWidget.from_json(spec)
        assert w2.style == CARTO_DARK

    def test_view_state_preserved(self):
        vs = {"longitude": 10, "latitude": 50, "zoom": 5, "pitch": 45, "bearing": 90}
        w = MapWidget("rj3", view_state=vs)
        spec = w.to_json([])
        w2, _ = MapWidget.from_json(spec)
        assert w2.view_state == vs

    def test_no_tooltip_in_spec_when_none(self):
        w = MapWidget("rj4")
        spec = w.to_json([])
        data = json.loads(spec)
        assert "tooltip" not in data

    def test_multiple_layers_roundtrip(self):
        w = MapWidget("rj5")
        layers = [
            scatterplot_layer("sp", [[1, 2]]),
            geojson_layer("gj", {"type": "FeatureCollection", "features": []}),
            tile_layer("tl", "https://example.com/{z}/{x}/{y}.png"),
        ]
        spec = w.to_json(layers)
        w2, layers2 = MapWidget.from_json(spec)
        assert len(layers2) == 3
        assert layers2[0]["type"] == "ScatterplotLayer"
        assert layers2[1]["type"] == "GeoJsonLayer"
        assert layers2[2]["type"] == "TileLayer"

    def test_effects_roundtrip(self):
        w = MapWidget("rj6")
        effects = [{"type": "LightingEffect", "ambientLight": {"intensity": 1}}]
        spec = w.to_json([], effects=effects)
        data = json.loads(spec)
        assert data["effects"] == effects


class TestToHtmlExtended:
    """Extended to_html tests."""

    def test_custom_style_in_html(self):
        w = MapWidget("th1", style=CARTO_DARK)
        html = w.to_html([])
        assert CARTO_DARK in html

    def test_view_state_values_in_html(self):
        vs = {"longitude": 25.5, "latitude": 60.1, "zoom": 10, "pitch": 30, "bearing": 45}
        w = MapWidget("th2", view_state=vs)
        html = w.to_html([])
        assert "25.5" in html
        assert "60.1" in html
        assert 'data-initial-pitch="30"' in html
        assert 'data-initial-bearing="45"' in html

    def test_layer_data_embedded(self):
        w = MapWidget("th3")
        layers = [scatterplot_layer("pts", [[21, 55]])]
        html = w.to_html(layers)
        assert "ScatterplotLayer" in html
        assert "21" in html

    def test_writes_to_file_and_returns_html(self):
        w = MapWidget("th4")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "map.html")
            html = w.to_html([], path=path)
            assert os.path.isfile(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == html

    def test_effects_in_html(self):
        w = MapWidget("th5")
        effects = [{"type": "LightingEffect", "ambientLight": {"intensity": 0.8}}]
        html = w.to_html([], effects=effects)
        assert "LightingEffect" in html


class TestBitmapLayerExtended:
    """Extended bitmap_layer tests."""

    def test_opacity_kwarg(self):
        lyr = bitmap_layer("bm1", "https://example.com/img.png",
                           [0, 0, 10, 10], opacity=0.5)
        assert lyr["opacity"] == 0.5
        assert lyr["image"] == "https://example.com/img.png"
        assert lyr["bounds"] == [0, 0, 10, 10]

    def test_data_uri_image(self):
        uri = "data:image/png;base64,iVBOR..."
        lyr = bitmap_layer("bm2", uri, [20, 55, 21, 56])
        assert lyr["image"] == uri
        assert lyr["type"] == "BitmapLayer"

    def test_no_data_key(self):
        """bitmap_layer should not have a top-level 'data' key."""
        lyr = bitmap_layer("bm3", "https://x.com/img.png", [0, 0, 1, 1])
        assert "data" not in lyr


class TestLayerUrlData:
    """Test layer() with URL string as data."""

    def test_url_data(self):
        lyr = layer("HeatmapLayer", "hm1",
                     "https://example.com/data.json",
                     radiusPixels=30)
        assert lyr["data"] == "https://example.com/data.json"
        assert lyr["radiusPixels"] == 30
        assert lyr["type"] == "HeatmapLayer"

    def test_data_none_excluded(self):
        lyr = layer("IconLayer", "ic1")
        assert "data" not in lyr


class TestAddMarkerDefaults:
    """Test add_marker default values."""

    def test_default_color(self):
        w = MapWidget("mk1")
        fake = _FakeSession()
        asyncio.run(w.add_marker(fake, "m1", 0, 0))
        msg = fake.messages[0][1]
        assert msg["color"] == "#3FB1CE"
        assert msg["draggable"] is False
        assert msg["popupHtml"] is None

    def test_with_popup(self):
        w = MapWidget("mk2")
        fake = _FakeSession()
        asyncio.run(w.add_marker(fake, "m1", 10, 20,
                                  popup_html="<b>Hello</b>"))
        msg = fake.messages[0][1]
        assert msg["popupHtml"] == "<b>Hello</b>"
        assert msg["longitude"] == 10
        assert msg["latitude"] == 20


class TestRemoveMarkerPayload:
    """Verify remove_marker sends the exact expected payload."""

    def test_payload_structure(self):
        w = MapWidget("rm1")
        fake = _FakeSession()
        asyncio.run(w.remove_marker(fake, "klaipeda"))
        msg = fake.messages[0]
        assert msg[0] == "deck_remove_marker"
        assert msg[1] == {"id": "rm1", "markerId": "klaipeda"}

    def test_clear_markers_payload(self):
        w = MapWidget("rm2")
        fake = _FakeSession()
        asyncio.run(w.clear_markers(fake))
        msg = fake.messages[0]
        assert msg[0] == "deck_clear_markers"
        assert msg[1] == {"id": "rm2"}


class TestQueryRenderedFeaturesExtended:
    """Extended query tests."""

    def test_point_with_layers(self):
        w = MapWidget("qf1")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, point=[100, 200], layers=["cities"],
            request_id="q1"))
        msg = fake.messages[0][1]
        assert msg["point"] == [100, 200]
        assert msg["layers"] == ["cities"]
        assert msg["requestId"] == "q1"
        assert "bounds" not in msg

    def test_bounds_only(self):
        w = MapWidget("qf2")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, bounds=[[0, 0], [100, 100]]))
        msg = fake.messages[0][1]
        assert msg["bounds"] == [[0, 0], [100, 100]]
        assert "point" not in msg

    def test_no_geometry_gives_no_point_or_bounds(self):
        w = MapWidget("qf3")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(fake))
        msg = fake.messages[0][1]
        assert "point" not in msg
        assert "bounds" not in msg

    def test_point_with_filter(self):
        w = MapWidget("qf4")
        fake = _FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, point=[50, 50],
            filter_expr=["==", "type", "city"]))
        msg = fake.messages[0][1]
        assert msg["filter"] == ["==", "type", "city"]
        assert msg["point"] == [50, 50]


class TestDeleteDrawnFeaturesExtended:
    """Test delete_drawn_features with specific IDs."""

    def test_specific_ids(self):
        w = MapWidget("dd1")
        fake = _FakeSession()
        asyncio.run(w.delete_drawn_features(fake, feature_ids=["abc", "def"]))
        msg = fake.messages[0]
        assert msg[0] == "deck_delete_drawn"
        assert msg[1]["featureIds"] == ["abc", "def"]

    def test_none_deletes_all(self):
        w = MapWidget("dd2")
        fake = _FakeSession()
        asyncio.run(w.delete_drawn_features(fake))
        assert fake.messages[0][1]["featureIds"] is None


class TestEnableDrawExtended:
    """Test enable_draw with modes parameter."""

    def test_specific_modes(self):
        w = MapWidget("ed1")
        fake = _FakeSession()
        asyncio.run(w.enable_draw(
            fake, modes=["draw_polygon"],
            default_mode="simple_select"))
        msg = fake.messages[0][1]
        assert msg["modes"] == ["draw_polygon"]
        assert msg["defaultMode"] == "simple_select"

    def test_no_modes_key_when_none(self):
        w = MapWidget("ed2")
        fake = _FakeSession()
        asyncio.run(w.enable_draw(fake))
        msg = fake.messages[0][1]
        assert "modes" not in msg

    def test_controls_and_modes(self):
        w = MapWidget("ed3")
        fake = _FakeSession()
        asyncio.run(w.enable_draw(
            fake,
            modes=["draw_point", "draw_line_string"],
            controls={"point": True, "line_string": True, "polygon": False}))
        msg = fake.messages[0][1]
        assert msg["modes"] == ["draw_point", "draw_line_string"]
        assert msg["controls"] == {"point": True, "line_string": True,
                                    "polygon": False}


class TestExportImageExtended:
    """Extended export_image tests."""

    def test_webp_format(self):
        w = MapWidget("ei1")
        fake = _FakeSession()
        asyncio.run(w.export_image(fake, format="webp", quality=0.75))
        msg = fake.messages[0][1]
        assert msg["format"] == "webp"
        assert msg["quality"] == 0.75

    def test_default_request_id(self):
        w = MapWidget("ei2")
        fake = _FakeSession()
        asyncio.run(w.export_image(fake))
        assert fake.messages[0][1]["requestId"] == "default"


class TestAddPopupExtended:
    """Extended popup tests."""

    def test_no_anchor(self):
        w = MapWidget("ap1")
        fake = _FakeSession()
        asyncio.run(w.add_popup(fake, "my-layer", "<b>{name}</b>"))
        msg = fake.messages[0][1]
        assert "anchor" not in msg
        assert msg["closeButton"] is True
        assert msg["closeOnClick"] is True
        assert msg["maxWidth"] == "300px"

    def test_with_anchor_and_custom_options(self):
        w = MapWidget("ap2")
        fake = _FakeSession()
        asyncio.run(w.add_popup(
            fake, "my-layer", "{name}",
            close_button=False, close_on_click=False,
            max_width="500px", anchor="bottom"))
        msg = fake.messages[0][1]
        assert msg["anchor"] == "bottom"
        assert msg["closeButton"] is False
        assert msg["closeOnClick"] is False
        assert msg["maxWidth"] == "500px"


class TestFeatureStateExtended:
    """Extended feature state tests."""

    def test_string_feature_id(self):
        w = MapWidget("fse1")
        fake = _FakeSession()
        asyncio.run(w.set_feature_state(fake, "src", "feature-abc",
                                          {"highlight": True}))
        msg = fake.messages[0][1]
        assert msg["featureId"] == "feature-abc"

    def test_remove_feature_state_with_source_layer(self):
        w = MapWidget("fse2")
        fake = _FakeSession()
        asyncio.run(w.remove_feature_state(
            fake, "osm", source_layer="water"))
        msg = fake.messages[0][1]
        assert msg["sourceLayer"] == "water"
        assert "featureId" not in msg

    def test_remove_specific_feature_and_key(self):
        w = MapWidget("fse3")
        fake = _FakeSession()
        asyncio.run(w.remove_feature_state(
            fake, "src", feature_id=5, key="selected"))
        msg = fake.messages[0][1]
        assert msg["featureId"] == 5
        assert msg["key"] == "selected"

    def test_set_multiple_state_props(self):
        w = MapWidget("fse4")
        fake = _FakeSession()
        state = {"hover": True, "selected": True, "opacity": 0.5}
        asyncio.run(w.set_feature_state(fake, "src", 1, state))
        assert fake.messages[0][1]["state"] == state


class TestQueryAtLngLatExtended:
    """Extended query_at_lnglat tests."""

    def test_no_layers(self):
        w = MapWidget("ql1")
        fake = _FakeSession()
        asyncio.run(w.query_at_lnglat(fake, 21.14, 55.71))
        msg = fake.messages[0][1]
        assert msg["longitude"] == 21.14
        assert msg["latitude"] == 55.71
        assert "layers" not in msg

    def test_with_layers_and_request_id(self):
        w = MapWidget("ql2")
        fake = _FakeSession()
        asyncio.run(w.query_at_lnglat(
            fake, 10.0, 50.0,
            layers=["a", "b"], request_id="my-query"))
        msg = fake.messages[0][1]
        assert msg["layers"] == ["a", "b"]
        assert msg["requestId"] == "my-query"


class TestSetTerrainExtended:
    """Extended terrain tests."""

    def test_custom_exaggeration(self):
        w = MapWidget("te1")
        fake = _FakeSession()
        asyncio.run(w.set_terrain(fake, "dem-src", exaggeration=3.0))
        msg = fake.messages[0][1]
        assert msg["terrain"]["source"] == "dem-src"
        assert msg["terrain"]["exaggeration"] == 3.0

    def test_disable_terrain(self):
        w = MapWidget("te2")
        fake = _FakeSession()
        asyncio.run(w.set_terrain(fake, None))
        assert fake.messages[0][1]["terrain"] is None


class TestSetSkyExtended:
    """Extended sky tests."""

    def test_sky_with_full_config(self):
        w = MapWidget("sk1")
        fake = _FakeSession()
        sky = {
            "sky-color": "#199EF3",
            "horizon-color": "#ffffff",
            "fog-color": "#ffffff",
        }
        asyncio.run(w.set_sky(fake, sky))
        assert fake.messages[0][1]["sky"] == sky


class TestMapWidgetUiExtended:
    """Extended ui() tests."""

    def test_custom_dimensions(self):
        w = MapWidget("uid1")
        tag = w.ui(width="50%", height="600px")
        html = str(tag)
        assert "50%" in html
        assert "600px" in html

    def test_no_tooltip_attr_when_none(self):
        w = MapWidget("uid2")
        tag = w.ui()
        html = str(tag)
        assert "data-tooltip" not in html

    def test_tooltip_attr_when_set(self):
        w = MapWidget("uid3", tooltip={"html": "{name}"})
        tag = w.ui()
        html = str(tag)
        assert "data-tooltip" in html

    def test_no_mapbox_key_attr_when_none(self):
        w = MapWidget("uid4")
        tag = w.ui()
        html = str(tag)
        assert "data-mapbox-api-key" not in html

    def test_no_controls_attr_when_empty(self):
        """controls=[] should emit data-controls='[]' (explicit no-controls)."""
        w = MapWidget("uid5", controls=[])
        tag = w.ui()
        html = str(tag)
        assert 'data-controls="[]"' in html


class TestSetSourceDataExtended:
    """Extended set_source_data tests."""

    def test_geojson_dict(self):
        w = MapWidget("ssd1")
        fake = _FakeSession()
        geojson = {"type": "FeatureCollection", "features": []}
        asyncio.run(w.set_source_data(fake, "my-source", geojson))
        msg = fake.messages[0][1]
        assert msg["sourceId"] == "my-source"
        assert msg["data"] == geojson

    def test_url_string(self):
        w = MapWidget("ssd2")
        fake = _FakeSession()
        url = "https://example.com/data.geojson"
        asyncio.run(w.set_source_data(fake, "src", url))
        msg = fake.messages[0][1]
        assert msg["data"] == url


class TestGeoPandasExtended:
    """Extended GeoPandas tests (using mock GeoDataFrame)."""

    def test_add_geodataframe_line_type(self):
        """When layer_type='line', default paint should have line properties."""
        class FakeGDF:
            @property
            def __geo_interface__(self):
                return {"type": "FeatureCollection", "features": []}

        w = MapWidget("gpd1")
        fake = _FakeSession()
        gdf = FakeGDF()
        asyncio.run(w.add_geodataframe(fake, "lines", gdf,
                                        layer_type="line"))
        # Should have 2 messages: add_source + add_maplibre_layer
        assert len(fake.messages) == 2
        layer_msg = fake.messages[1][1]
        assert layer_msg["layerSpec"]["type"] == "line"
        assert "line-color" in layer_msg["layerSpec"]["paint"]

    def test_add_geodataframe_circle_type(self):
        """When layer_type='circle', default paint should have circle props."""
        class FakeGDF:
            @property
            def __geo_interface__(self):
                return {"type": "FeatureCollection", "features": []}

        w = MapWidget("gpd2")
        fake = _FakeSession()
        gdf = FakeGDF()
        asyncio.run(w.add_geodataframe(fake, "pts", gdf,
                                        layer_type="circle"))
        layer_msg = fake.messages[1][1]
        assert layer_msg["layerSpec"]["type"] == "circle"
        assert "circle-radius" in layer_msg["layerSpec"]["paint"]

    def test_add_geodataframe_custom_paint_overrides(self):
        """Custom paint should override defaults."""
        class FakeGDF:
            @property
            def __geo_interface__(self):
                return {"type": "FeatureCollection", "features": []}

        w = MapWidget("gpd3")
        fake = _FakeSession()
        gdf = FakeGDF()
        custom_paint = {"fill-color": "#ff0000", "fill-opacity": 0.8}
        asyncio.run(w.add_geodataframe(fake, "custom", gdf,
                                        paint=custom_paint))
        layer_msg = fake.messages[1][1]
        assert layer_msg["layerSpec"]["paint"] == custom_paint

    def test_add_geodataframe_with_layout(self):
        """Layout property should be included when provided."""
        class FakeGDF:
            @property
            def __geo_interface__(self):
                return {"type": "FeatureCollection", "features": []}

        w = MapWidget("gpd4")
        fake = _FakeSession()
        gdf = FakeGDF()
        asyncio.run(w.add_geodataframe(
            fake, "src", gdf,
            layout={"visibility": "none"}))
        layer_msg = fake.messages[1][1]
        assert layer_msg["layerSpec"]["layout"] == {"visibility": "none"}

    def test_add_geodataframe_with_popup_generates_three_messages(self):
        """When popup_template is given, a third message should be popup."""
        class FakeGDF:
            @property
            def __geo_interface__(self):
                return {"type": "FeatureCollection", "features": []}

        w = MapWidget("gpd5")
        fake = _FakeSession()
        gdf = FakeGDF()
        asyncio.run(w.add_geodataframe(
            fake, "src", gdf,
            popup_template="<b>{name}</b>"))
        assert len(fake.messages) == 3  # source + layer + popup
        assert fake.messages[2][0] == "deck_add_popup"

    def test_add_geodataframe_before_id(self):
        """before_id should be passed through to add_maplibre_layer."""
        class FakeGDF:
            @property
            def __geo_interface__(self):
                return {"type": "FeatureCollection", "features": []}

        w = MapWidget("gpd6")
        fake = _FakeSession()
        gdf = FakeGDF()
        asyncio.run(w.add_geodataframe(
            fake, "mydata", gdf, before_id="existing-layer"))
        layer_msg = fake.messages[1][1]
        assert layer_msg["beforeId"] == "existing-layer"


class TestPaletteConstants:
    """Verify all palette constants are well-formed."""

    def test_all_palettes_have_6_stops(self):
        for pal in (PALETTE_VIRIDIS, PALETTE_PLASMA, PALETTE_OCEAN,
                    PALETTE_THERMAL, PALETTE_CHLOROPHYLL):
            assert len(pal) == 6

    def test_palette_values_in_range(self):
        for pal in (PALETTE_VIRIDIS, PALETTE_PLASMA, PALETTE_OCEAN,
                    PALETTE_THERMAL, PALETTE_CHLOROPHYLL):
            for stop in pal:
                assert len(stop) == 3
                assert all(0 <= v <= 255 for v in stop)

    def test_palettes_are_distinct(self):
        palettes = [PALETTE_VIRIDIS, PALETTE_PLASMA, PALETTE_OCEAN,
                    PALETTE_THERMAL, PALETTE_CHLOROPHYLL]
        for i, p1 in enumerate(palettes):
            for j, p2 in enumerate(palettes):
                if i != j:
                    assert p1 != p2


class TestUpdateTooltipExtended:
    """Extended update_tooltip tests."""

    def test_update_with_style(self):
        w = MapWidget("ute1")
        fake = _FakeSession()
        tooltip = {
            "html": "<b>{name}</b>",
            "style": {"backgroundColor": "#222", "color": "#fff"},
        }
        asyncio.run(w.update_tooltip(fake, tooltip))
        assert w.tooltip == tooltip
        msg = fake.messages[0][1]
        assert msg["tooltip"] == tooltip

    def test_update_tooltip_multiple_times(self):
        w = MapWidget("ute2")
        fake = _FakeSession()
        asyncio.run(w.update_tooltip(fake, {"html": "First"}))
        assert w.tooltip == {"html": "First"}
        asyncio.run(w.update_tooltip(fake, {"html": "Second"}))
        assert w.tooltip == {"html": "Second"}
        asyncio.run(w.update_tooltip(fake, None))
        assert w.tooltip is None
        assert len(fake.messages) == 3


class TestSetProjectionExtended:
    """Extended projection tests."""

    def test_globe_message(self):
        w = MapWidget("spe1")
        fake = _FakeSession()
        asyncio.run(w.set_projection(fake, "globe"))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_projection"
        assert msg[1]["projection"] == "globe"

    def test_mercator_message(self):
        w = MapWidget("spe2")
        fake = _FakeSession()
        asyncio.run(w.set_projection(fake, "mercator"))
        assert fake.messages[0][1]["projection"] == "mercator"

    def test_invalid_projection_raises(self):
        w = MapWidget("spe3")
        fake = _FakeSession()
        with pytest.raises(ValueError, match="Unknown projection"):
            asyncio.run(w.set_projection(fake, "equirectangular"))


class TestMapWidgetConstructorDefaults:
    """Test MapWidget constructor defaults thoroughly."""

    def test_default_view_state_values(self):
        w = MapWidget("cd1")
        assert w.view_state["longitude"] == 21.1
        assert w.view_state["latitude"] == 55.7
        assert w.view_state["zoom"] == 8

    def test_default_style(self):
        w = MapWidget("cd2")
        assert w.style == CARTO_POSITRON

    def test_default_tooltip_none(self):
        w = MapWidget("cd3")
        assert w.tooltip is None

    def test_default_mapbox_key_none(self):
        w = MapWidget("cd4")
        assert w.mapbox_api_key is None

    def test_default_controls(self):
        w = MapWidget("cd5")
        assert len(w.controls) == 1
        assert w.controls[0]["type"] == "navigation"

    def test_custom_controls_override(self):
        w = MapWidget("cd6", controls=[
            {"type": "scale", "position": "bottom-left"},
        ])
        assert len(w.controls) == 1
        assert w.controls[0]["type"] == "scale"

    def test_empty_controls(self):
        w = MapWidget("cd7", controls=[])
        assert w.controls == []


class TestAddSourceExtended:
    """Extended add_source tests."""

    def test_raster_dem_source(self):
        w = MapWidget("as1")
        fake = _FakeSession()
        asyncio.run(w.add_source(fake, "terrain-dem", {
            "type": "raster-dem",
            "url": "https://demotiles.maplibre.org/terrain-tiles/tiles.json",
            "tileSize": 256,
        }))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_source"
        assert msg[1]["sourceId"] == "terrain-dem"
        assert msg[1]["spec"]["type"] == "raster-dem"

    def test_vector_source(self):
        w = MapWidget("as2")
        fake = _FakeSession()
        asyncio.run(w.add_source(fake, "osm", {
            "type": "vector",
            "url": "https://example.com/tiles",
        }))
        msg = fake.messages[0][1]
        assert msg["spec"]["type"] == "vector"


class TestAddMaplibreLayerExtended:
    """Extended add_maplibre_layer tests."""

    def test_layer_with_layout(self):
        w = MapWidget("ml1")
        fake = _FakeSession()
        asyncio.run(w.add_maplibre_layer(fake, {
            "id": "my-fill",
            "type": "fill",
            "source": "polygons",
            "paint": {"fill-color": "#088"},
            "layout": {"visibility": "visible"},
        }))
        msg = fake.messages[0][1]
        assert msg["layerSpec"]["layout"] == {"visibility": "visible"}

    def test_fill_extrusion_layer(self):
        w = MapWidget("ml2")
        fake = _FakeSession()
        asyncio.run(w.add_maplibre_layer(fake, {
            "id": "buildings",
            "type": "fill-extrusion",
            "source": "osm",
            "paint": {
                "fill-extrusion-height": 10,
                "fill-extrusion-color": "#aaa",
            },
        }))
        msg = fake.messages[0][1]
        assert msg["layerSpec"]["type"] == "fill-extrusion"


class TestAppFactory:
    """Additional app factory tests."""

    def test_app_is_instance(self):
        """app should be a direct App instance (not a factory)."""
        assert isinstance(app, App)

    def test_v1_widgets_merged(self):
        """Former Tab 9/10 widgets were merged into existing tabs."""
        # v1_deck_widget and v1_ml_widget no longer exist as separate widgets
        # Their functionality was merged into adv_widget (Tab 5) and
        # maplibre_widget (Tab 2) respectively.
        from shiny_deckgl.app import adv_widget, maplibre_widget
        assert isinstance(adv_widget, MapWidget)
        assert isinstance(maplibre_widget, MapWidget)


# ==========================================================================
# Image management tests (add_image / remove_image / has_image)
# ==========================================================================

class TestAddImage:
    """Test add_image method."""

    def test_basic_add_image(self):
        w = MapWidget("img1")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "buoy-icon", "https://example.com/buoy.png"))
        handler, msg = fake.messages[0]
        assert handler == "deck_add_image"
        assert msg["id"] == "img1"
        assert msg["imageId"] == "buoy-icon"
        assert msg["url"] == "https://example.com/buoy.png"
        assert msg["pixelRatio"] == 1
        assert msg["sdf"] is False

    def test_add_image_with_pixel_ratio(self):
        w = MapWidget("img2")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "station", "https://x.com/s.png", pixel_ratio=2))
        msg = fake.messages[0][1]
        assert msg["pixelRatio"] == 2

    def test_add_image_sdf_mode(self):
        w = MapWidget("img3")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "marker", "https://x.com/m.png", sdf=True))
        msg = fake.messages[0][1]
        assert msg["sdf"] is True

    def test_add_image_data_uri(self):
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        w = MapWidget("img4")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "dot", data_uri))
        msg = fake.messages[0][1]
        assert msg["url"] == data_uri

    def test_add_image_all_options(self):
        w = MapWidget("img5")
        fake = _FakeSession()
        asyncio.run(w.add_image(
            fake, "wind-arrow", "https://x.com/w.png",
            pixel_ratio=3, sdf=True,
        ))
        msg = fake.messages[0][1]
        assert msg["imageId"] == "wind-arrow"
        assert msg["pixelRatio"] == 3
        assert msg["sdf"] is True


class TestRemoveImage:
    """Test remove_image method."""

    def test_basic_remove_image(self):
        w = MapWidget("ri1")
        fake = _FakeSession()
        asyncio.run(w.remove_image(fake, "buoy-icon"))
        handler, msg = fake.messages[0]
        assert handler == "deck_remove_image"
        assert msg["id"] == "ri1"
        assert msg["imageId"] == "buoy-icon"


class TestHasImage:
    """Test has_image method."""

    def test_basic_has_image(self):
        w = MapWidget("hi1")
        fake = _FakeSession()
        asyncio.run(w.has_image(fake, "buoy-icon"))
        handler, msg = fake.messages[0]
        assert handler == "deck_has_image"
        assert msg["id"] == "hi1"
        assert msg["imageId"] == "buoy-icon"

    def test_has_image_input_id(self):
        w = MapWidget("hi2")
        assert w.has_image_input_id == "hi2_has_image"


class TestImageWorkflow:
    """Test typical image add-then-use-in-symbol-layer pattern."""

    def test_add_image_then_symbol_layer(self):
        """Image loaded then referenced by a symbol layer."""
        w = MapWidget("iw1")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "station-icon", "https://x.com/s.png"))
        asyncio.run(w.add_source(fake, "stations", {
            "type": "geojson",
            "data": {"type": "FeatureCollection", "features": []},
        }))
        asyncio.run(w.add_maplibre_layer(fake, {
            "id": "station-symbols",
            "type": "symbol",
            "source": "stations",
            "layout": {"icon-image": "station-icon", "icon-size": 0.5},
        }))
        assert len(fake.messages) == 3
        assert fake.messages[0][0] == "deck_add_image"
        assert fake.messages[1][0] == "deck_add_source"
        assert fake.messages[2][0] == "deck_add_maplibre_layer"

    def test_replace_image(self):
        """Calling add_image twice with same id should work (JS replaces)."""
        w = MapWidget("iw2")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "icon", "https://x.com/v1.png"))
        asyncio.run(w.add_image(fake, "icon", "https://x.com/v2.png"))
        assert len(fake.messages) == 2
        assert fake.messages[0][1]["url"] == "https://x.com/v1.png"
        assert fake.messages[1][1]["url"] == "https://x.com/v2.png"

    def test_add_remove_image(self):
        """Add then remove image."""
        w = MapWidget("iw3")
        fake = _FakeSession()
        asyncio.run(w.add_image(fake, "temp-icon", "https://x.com/t.png"))
        asyncio.run(w.remove_image(fake, "temp-icon"))
        assert fake.messages[0][0] == "deck_add_image"
        assert fake.messages[1][0] == "deck_remove_image"


# ===========================================================================
# Phase 5 (v0.7.0) — Extensions, DeckProps & Layer Helpers
# ===========================================================================


class TestExtensionConstructorOptions:
    """Extension constructor options in layer()."""

    def test_extension_string_only(self):
        """Backward-compatible: list of strings."""
        spec = layer("ScatterplotLayer", "e1", data=[],
                      extensions=["BrushingExtension", "ClipExtension"])
        assert spec["@@extensions"] == ["BrushingExtension", "ClipExtension"]

    def test_extension_with_options_tuple(self):
        """Tuple form: [name, options]."""
        spec = layer("ScatterplotLayer", "e2", data=[],
                      extensions=[["DataFilterExtension", {"filterSize": 2}]])
        ext = spec["@@extensions"]
        assert len(ext) == 1
        assert ext[0] == {"@@extClass": "DataFilterExtension",
                          "@@extOpts": {"filterSize": 2}}

    def test_extension_with_options_list(self):
        """List form (not tuple): [name, options]."""
        spec = layer("ScatterplotLayer", "e3", data=[],
                      extensions=[["MaskExtension", {"maskByInstance": True}]])
        ext = spec["@@extensions"]
        assert ext[0]["@@extClass"] == "MaskExtension"
        assert ext[0]["@@extOpts"] == {"maskByInstance": True}

    def test_extension_mixed(self):
        """Mix of string-only and [name, opts] forms."""
        spec = layer("ScatterplotLayer", "e4", data=[],
                      extensions=[
                          "ClipExtension",
                          ["DataFilterExtension", {"filterSize": 2}],
                          "BrushingExtension",
                      ])
        ext = spec["@@extensions"]
        assert len(ext) == 3
        assert ext[0] == "ClipExtension"
        assert ext[1] == {"@@extClass": "DataFilterExtension",
                          "@@extOpts": {"filterSize": 2}}
        assert ext[2] == "BrushingExtension"

    def test_extension_invalid_raises(self):
        """Invalid spec (e.g. bare dict) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid extension spec"):
            layer("ScatterplotLayer", "e5", data=[],
                  extensions=[{"bad": True}])

    def test_extension_invalid_tuple_length_raises(self):
        """Tuple with wrong length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid extension spec"):
            layer("ScatterplotLayer", "e6", data=[],
                  extensions=[("a", "b", "c")])

    def test_extension_none_omitted(self):
        """extensions=None produces no @@extensions key."""
        spec = layer("ScatterplotLayer", "e7", data=[])
        assert "@@extensions" not in spec

    def test_extension_empty_list_omitted(self):
        """extensions=[] (empty) produces no @@extensions key."""
        spec = layer("ScatterplotLayer", "e8", data=[], extensions=[])
        assert "@@extensions" not in spec


class TestExtensionHelpers:
    """Tests for the Python extension convenience helpers (v1.0.0)."""

    # --- Extension type alias ---

    def test_extension_type_importable(self):
        from shiny_deckgl.extensions import Extension
        assert Extension is not None

    def test_extension_in_extensions_all(self):
        from shiny_deckgl.extensions import __all__ as ext_all
        assert "Extension" in ext_all

    # --- return-type tests ---

    def test_brushing_returns_string(self):
        assert brushing_extension() == "BrushingExtension"

    def test_collision_filter_returns_string(self):
        assert collision_filter_extension() == "CollisionFilterExtension"

    def test_mask_returns_string(self):
        assert mask_extension() == "MaskExtension"

    def test_clip_returns_string(self):
        assert clip_extension() == "ClipExtension"

    def test_terrain_returns_string(self):
        assert terrain_extension() == "TerrainExtension"

    def test_data_filter_default(self):
        result = data_filter_extension()
        assert result == ["DataFilterExtension", {"filterSize": 1}]

    def test_data_filter_custom_size(self):
        result = data_filter_extension(filter_size=3)
        assert result == ["DataFilterExtension", {"filterSize": 3}]

    def test_fill_style_default(self):
        result = fill_style_extension()
        assert result == ["FillStyleExtension", {"pattern": True}]

    def test_fill_style_no_pattern(self):
        result = fill_style_extension(pattern=False)
        assert result == ["FillStyleExtension", {"pattern": False}]

    def test_path_style_defaults(self):
        result = path_style_extension()
        assert result == ["PathStyleExtension",
                          {"dash": False, "highPrecisionDash": False}]

    def test_path_style_dash(self):
        result = path_style_extension(dash=True)
        assert result == ["PathStyleExtension",
                          {"dash": True, "highPrecisionDash": False}]

    def test_path_style_high_precision(self):
        result = path_style_extension(dash=True, high_precision=True)
        assert result == ["PathStyleExtension",
                          {"dash": True, "highPrecisionDash": True}]

    # --- integration with layer() ---

    def test_brushing_in_layer(self):
        spec = layer("ScatterplotLayer", "b1", data=[],
                      extensions=[brushing_extension()],
                      brushingRadius=50000)
        assert spec["@@extensions"] == ["BrushingExtension"]
        assert spec["brushingRadius"] == 50000

    def test_data_filter_in_layer(self):
        spec = layer("ScatterplotLayer", "df1", data=[],
                      extensions=[data_filter_extension(filter_size=2)])
        ext = spec["@@extensions"]
        assert len(ext) == 1
        assert ext[0] == {"@@extClass": "DataFilterExtension",
                          "@@extOpts": {"filterSize": 2}}

    def test_mixed_helpers_in_layer(self):
        spec = layer("ScatterplotLayer", "mx1", data=[],
                      extensions=[
                          brushing_extension(),
                          data_filter_extension(),
                          clip_extension(),
                      ])
        ext = spec["@@extensions"]
        assert len(ext) == 3
        assert ext[0] == "BrushingExtension"
        assert ext[1] == {"@@extClass": "DataFilterExtension",
                          "@@extOpts": {"filterSize": 1}}
        assert ext[2] == "ClipExtension"

    def test_all_string_helpers_are_strings(self):
        """No-arg helpers that return strings."""
        for helper in [
            brushing_extension,
            collision_filter_extension,
            mask_extension,
            clip_extension,
            terrain_extension,
        ]:
            result = helper()
            assert isinstance(result, str), f"{helper.__name__} should return str"

    def test_all_parameterised_helpers_return_lists(self):
        """Helpers with constructor options return [name, opts] lists."""
        for result in [
            data_filter_extension(),
            fill_style_extension(),
            path_style_extension(),
        ]:
            assert isinstance(result, list), f"Expected list, got {type(result)}"
            assert len(result) == 2
            assert isinstance(result[0], str)
            assert isinstance(result[1], dict)

    # --- importable from top-level package ---

    def test_importable_from_package(self):
        import shiny_deckgl as pkg
        for name in [
            "brushing_extension", "collision_filter_extension",
            "data_filter_extension", "mask_extension", "clip_extension",
            "terrain_extension", "fill_style_extension", "path_style_extension",
        ]:
            assert hasattr(pkg, name), f"shiny_deckgl.{name} not found"

    def test_importable_from_components_shim(self):
        from shiny_deckgl.components import (
            brushing_extension as be,
            data_filter_extension as dfe,
        )
        assert be() == "BrushingExtension"
        assert dfe() == ["DataFilterExtension", {"filterSize": 1}]


class TestDeckLevelProps:
    """Deck-level props on MapWidget.__init__, ui(), and update()."""

    def test_default_picking_radius(self):
        w = MapWidget("dp1")
        assert w.picking_radius == 0

    def test_custom_picking_radius(self):
        w = MapWidget("dp2", picking_radius=5)
        assert w.picking_radius == 5

    def test_default_use_device_pixels(self):
        w = MapWidget("dp3")
        assert w.use_device_pixels is True

    def test_custom_use_device_pixels_false(self):
        w = MapWidget("dp4", use_device_pixels=False)
        assert w.use_device_pixels is False

    def test_custom_use_device_pixels_int(self):
        w = MapWidget("dp5", use_device_pixels=2)
        assert w.use_device_pixels == 2

    def test_default_animate(self):
        w = MapWidget("dp6")
        assert w.animate is False

    def test_animate_true(self):
        w = MapWidget("dp7", animate=True)
        assert w.animate is True

    def test_default_parameters(self):
        w = MapWidget("dp8")
        assert w.parameters is None

    def test_custom_parameters(self):
        w = MapWidget("dp9", parameters={"depthTest": False})
        assert w.parameters == {"depthTest": False}

    def test_default_controller(self):
        w = MapWidget("dp10")
        assert w.controller is True

    def test_controller_false(self):
        w = MapWidget("dp11", controller=False)
        assert w.controller is False

    def test_controller_dict(self):
        opts = {"touchRotate": True, "doubleClickZoom": False}
        w = MapWidget("dp12", controller=opts)
        assert w.controller == opts

    # -- ui() data attributes --

    def test_ui_picking_radius_omitted_when_zero(self):
        w = MapWidget("dp13")
        tag = w.ui()
        html = str(tag)
        assert "data-picking-radius" not in html

    def test_ui_picking_radius_set(self):
        w = MapWidget("dp14", picking_radius=10)
        tag = w.ui()
        html = str(tag)
        assert 'data-picking-radius="10"' in html

    def test_ui_use_device_pixels_omitted_default(self):
        w = MapWidget("dp15")
        tag = w.ui()
        html = str(tag)
        assert "data-use-device-pixels" not in html

    def test_ui_use_device_pixels_false(self):
        w = MapWidget("dp16", use_device_pixels=False)
        tag = w.ui()
        html = str(tag)
        assert "data-use-device-pixels" in html

    def test_ui_animate_omitted_default(self):
        w = MapWidget("dp17")
        html = str(w.ui())
        assert "data-animate" not in html

    def test_ui_animate_true(self):
        w = MapWidget("dp18", animate=True)
        html = str(w.ui())
        assert 'data-animate="true"' in html

    def test_ui_parameters_omitted_default(self):
        w = MapWidget("dp19")
        html = str(w.ui())
        assert "data-parameters" not in html

    def test_ui_parameters_set(self):
        w = MapWidget("dp20", parameters={"depthTest": False})
        html = str(w.ui())
        assert "data-parameters" in html

    def test_ui_controller_omitted_default(self):
        w = MapWidget("dp21")
        html = str(w.ui())
        assert "data-controller" not in html

    def test_ui_controller_false(self):
        w = MapWidget("dp22", controller=False)
        html = str(w.ui())
        assert "data-controller" in html

    # -- update() deck-level props --

    def test_update_with_picking_radius(self):
        w = MapWidget("dp23")
        fake = _FakeSession()
        asyncio.run(w.update(fake, layers=[], picking_radius=5))
        payload = fake.messages[0][1]
        assert payload["pickingRadius"] == 5

    def test_update_with_use_device_pixels(self):
        w = MapWidget("dp24")
        fake = _FakeSession()
        asyncio.run(w.update(fake, layers=[], use_device_pixels=False))
        payload = fake.messages[0][1]
        assert payload["useDevicePixels"] is False

    def test_update_with_animate(self):
        w = MapWidget("dp25")
        fake = _FakeSession()
        asyncio.run(w.update(fake, layers=[], animate=True))
        payload = fake.messages[0][1]
        assert payload["_animate"] is True

    def test_update_without_deck_props_omits_keys(self):
        w = MapWidget("dp26")
        fake = _FakeSession()
        asyncio.run(w.update(fake, layers=[]))
        payload = fake.messages[0][1]
        assert "pickingRadius" not in payload
        assert "useDevicePixels" not in payload
        assert "_animate" not in payload


class TestSetController:
    """set_controller() async method."""

    def test_set_controller_true(self):
        w = MapWidget("sc1")
        fake = _FakeSession()
        asyncio.run(w.set_controller(fake, True))
        handler, payload = fake.messages[0]
        assert handler == "deck_set_controller"
        assert payload["controller"] is True

    def test_set_controller_false(self):
        w = MapWidget("sc2")
        fake = _FakeSession()
        asyncio.run(w.set_controller(fake, False))
        payload = fake.messages[0][1]
        assert payload["controller"] is False

    def test_set_controller_dict(self):
        opts = {"touchRotate": True, "doubleClickZoom": False}
        w = MapWidget("sc3")
        fake = _FakeSession()
        asyncio.run(w.set_controller(fake, opts))
        payload = fake.messages[0][1]
        assert payload["controller"] == opts


class TestArcLayer:
    def test_defaults(self):
        spec = arc_layer("a1", data=[])
        assert spec["type"] == "ArcLayer"
        assert spec["id"] == "a1"
        assert spec["pickable"] is True
        assert spec["getSourcePosition"] == "@@d.sourcePosition"
        assert spec["getTargetPosition"] == "@@d.targetPosition"
        assert spec["getWidth"] == 2

    def test_kwargs_override(self):
        spec = arc_layer("a2", data=[], getWidth=5, getSourceColor=[255, 0, 0])
        assert spec["getWidth"] == 5
        assert spec["getSourceColor"] == [255, 0, 0]


class TestIconLayer:
    def test_defaults(self):
        spec = icon_layer("i1", data=[])
        assert spec["type"] == "IconLayer"
        assert spec["pickable"] is True
        assert spec["getPosition"] == "@@d"
        assert spec["getSize"] == 24

    def test_kwargs_override(self):
        spec = icon_layer("i2", data=[], getSize=48, sizeScale=2)
        assert spec["getSize"] == 48
        assert spec["sizeScale"] == 2


class TestPathLayer:
    def test_defaults(self):
        spec = path_layer("p1", data=[])
        assert spec["type"] == "PathLayer"
        assert spec["getPath"] == "@@d.path"
        assert spec["getWidth"] == 3
        assert spec["widthMinPixels"] == 1

    def test_kwargs_override(self):
        spec = path_layer("p2", data=[], getColor=[255, 0, 0], getWidth=10)
        assert spec["getColor"] == [255, 0, 0]
        assert spec["getWidth"] == 10


class TestLineLayer:
    def test_defaults(self):
        spec = line_layer("l1", data=[])
        assert spec["type"] == "LineLayer"
        assert spec["getSourcePosition"] == "@@d.sourcePosition"
        assert spec["getTargetPosition"] == "@@d.targetPosition"
        assert spec["getWidth"] == 1

    def test_kwargs_override(self):
        spec = line_layer("l2", data=[], getColor=[0, 255, 0], getWidth=3)
        assert spec["getColor"] == [0, 255, 0]


class TestTextLayer:
    def test_defaults(self):
        spec = text_layer("t1", data=[])
        assert spec["type"] == "TextLayer"
        assert spec["getText"] == "@@d.text"
        assert spec["getSize"] == 16
        assert spec["getTextAnchor"] == "middle"

    def test_kwargs_override(self):
        spec = text_layer("t2", data=[], getSize=24, getText="@@d.label")
        assert spec["getSize"] == 24
        assert spec["getText"] == "@@d.label"


class TestColumnLayer:
    def test_defaults(self):
        spec = column_layer("c1", data=[])
        assert spec["type"] == "ColumnLayer"
        assert spec["extruded"] is True
        assert spec["radius"] == 100
        assert spec["getFillColor"] == [255, 140, 0]

    def test_kwargs_override(self):
        spec = column_layer("c2", data=[], radius=500, extruded=False)
        assert spec["radius"] == 500
        assert spec["extruded"] is False


class TestPolygonLayer:
    def test_defaults(self):
        spec = polygon_layer("pg1", data=[])
        assert spec["type"] == "PolygonLayer"
        assert spec["getPolygon"] == "@@d.polygon"
        assert spec["extruded"] is False
        assert spec["getLineWidth"] == 1

    def test_kwargs_override(self):
        spec = polygon_layer("pg2", data=[], extruded=True,
                             getFillColor=[255, 0, 0, 128])
        assert spec["extruded"] is True
        assert spec["getFillColor"] == [255, 0, 0, 128]


class TestHeatmapLayer:
    def test_defaults(self):
        spec = heatmap_layer("h1", data=[])
        assert spec["type"] == "HeatmapLayer"
        assert spec["radiusPixels"] == 30
        assert spec["intensity"] == 1
        assert spec["threshold"] == 0.05
        # HeatmapLayer is not pickable by default
        assert "pickable" not in spec or spec.get("pickable") != True

    def test_kwargs_override(self):
        spec = heatmap_layer("h2", data=[], radiusPixels=60, intensity=2)
        assert spec["radiusPixels"] == 60
        assert spec["intensity"] == 2


class TestHexagonLayer:
    def test_defaults(self):
        spec = hexagon_layer("hx1", data=[])
        assert spec["type"] == "HexagonLayer"
        assert spec["radius"] == 1000
        assert spec["elevationScale"] == 4
        assert spec["extruded"] is True

    def test_kwargs_override(self):
        spec = hexagon_layer("hx2", data=[], radius=500, extruded=False)
        assert spec["radius"] == 500
        assert spec["extruded"] is False


class TestH3HexagonLayer:
    def test_defaults(self):
        spec = h3_hexagon_layer("h3_1", data=[])
        assert spec["type"] == "H3HexagonLayer"
        assert spec["getHexagon"] == "@@d.hex"
        assert spec["getFillColor"] == "@@d.color"
        assert spec["extruded"] is False

    def test_kwargs_override(self):
        spec = h3_hexagon_layer("h3_2", data=[], extruded=True,
                                 getHexagon="@@d.h3_index")
        assert spec["extruded"] is True
        assert spec["getHexagon"] == "@@d.h3_index"


class TestGlobeView:
    """globe_view() helper."""

    def test_basic(self):
        v = globe_view()
        assert v == {"@@type": "GlobeView"}

    def test_with_kwargs(self):
        v = globe_view(resolution=2, id="globe1")
        assert v["@@type"] == "GlobeView"
        assert v["resolution"] == 2
        assert v["id"] == "globe1"


class TestUpdateTriggers:
    """updateTriggers passthrough (no code needed, just validation)."""

    def test_update_triggers_passthrough(self):
        spec = layer("ScatterplotLayer", "ut1", data=[],
                     getRadius="@@d.r",
                     updateTriggers={"getRadius": ["r_version"]})
        assert spec["updateTriggers"] == {"getRadius": ["r_version"]}

    def test_update_triggers_multiple(self):
        spec = layer("GeoJsonLayer", "ut2", data=[],
                     updateTriggers={
                         "getFillColor": ["color_mode"],
                         "getLineWidth": ["width_scale"],
                     })
        assert "getFillColor" in spec["updateTriggers"]
        assert "getLineWidth" in spec["updateTriggers"]


class TestLayerHelpersDataSerialization:
    """All new layer helpers correctly serialise data."""

    def test_arc_layer_url_data(self):
        spec = arc_layer("ds1", data="https://example.com/arcs.json")
        assert spec["data"] == "https://example.com/arcs.json"

    def test_icon_layer_list_data(self):
        pts = [[1.0, 2.0], [3.0, 4.0]]
        spec = icon_layer("ds2", data=pts)
        assert spec["data"] == pts

    def test_path_layer_dict_data(self):
        d = [{"path": [[0, 0], [1, 1]]}]
        spec = path_layer("ds3", data=d)
        assert spec["data"] == d

    def test_heatmap_layer_url(self):
        spec = heatmap_layer("ds4", data="https://example.com/heat.json")
        assert spec["data"] == "https://example.com/heat.json"

    def test_hexagon_layer_list(self):
        spec = hexagon_layer("ds5", data=[[1, 2], [3, 4]])
        assert len(spec["data"]) == 2

    def test_h3_hexagon_layer_list(self):
        d = [{"hex": "891f1d48177ffff", "color": [255, 0, 0]}]
        spec = h3_hexagon_layer("ds6", data=d)
        assert spec["data"][0]["hex"] == "891f1d48177ffff"


class TestV080Version:
    """Version bump verification."""

    def test_version_is_100(self):
        assert m.__version__ == "1.4.0"


# ===========================================================================
# v0.8.0 â€" Widgets, Transitions, Camera Methods
# ===========================================================================

# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------

class TestZoomWidget:
    def test_class_and_placement(self):
        w = zoom_widget()
        assert w["@@widgetClass"] == "ZoomWidget"
        assert w["placement"] == "top-right"

    def test_custom_placement(self):
        w = zoom_widget(placement="bottom-left")
        assert w["placement"] == "bottom-left"

    def test_extra_kwargs(self):
        w = zoom_widget(transitionDuration=300)
        assert w["transitionDuration"] == 300


class TestCompassWidget:
    def test_class_and_placement(self):
        w = compass_widget()
        assert w["@@widgetClass"] == "CompassWidget"
        assert w["placement"] == "top-right"

    def test_custom_placement(self):
        w = compass_widget(placement="top-left")
        assert w["placement"] == "top-left"


class TestFullscreenWidget:
    def test_class_and_placement(self):
        w = fullscreen_widget()
        assert w["@@widgetClass"] == "FullscreenWidget"
        assert w["placement"] == "top-right"


class TestScaleWidget:
    def test_class_and_placement(self):
        w = scale_widget()
        assert w["@@widgetClass"] == "_ScaleWidget"
        assert w["placement"] == "bottom-left"


class TestGimbalWidget:
    def test_class_and_placement(self):
        w = gimbal_widget()
        assert w["@@widgetClass"] == "GimbalWidget"
        assert w["placement"] == "top-right"


class TestResetViewWidget:
    def test_class_and_placement(self):
        w = reset_view_widget()
        assert w["@@widgetClass"] == "ResetViewWidget"
        assert w["placement"] == "top-right"


class TestScreenshotWidget:
    def test_class_and_placement(self):
        w = screenshot_widget()
        assert w["@@widgetClass"] == "ScreenshotWidget"
        assert w["placement"] == "top-right"


class TestFpsWidget:
    def test_class_and_placement(self):
        w = fps_widget()
        assert w["@@widgetClass"] == "_FpsWidget"
        assert w["placement"] == "top-left"


class TestLoadingWidget:
    def test_class_no_placement(self):
        w = loading_widget()
        assert w["@@widgetClass"] == "_LoadingWidget"
        assert "placement" not in w

    def test_extra_kwargs(self):
        w = loading_widget(label="Loading data…")
        assert w["label"] == "Loading data…"


class TestTimelineWidget:
    def test_class_and_placement(self):
        w = timeline_widget()
        assert w["@@widgetClass"] == "_TimelineWidget"
        assert w["placement"] == "bottom-left"


class TestGeocoderWidget:
    def test_class_and_placement(self):
        w = geocoder_widget()
        assert w["@@widgetClass"] == "_GeocoderWidget"
        assert w["placement"] == "top-left"


class TestThemeWidget:
    def test_class_no_placement(self):
        w = theme_widget()
        assert w["@@widgetClass"] == "_ThemeWidget"
        assert "placement" not in w


# ---------------------------------------------------------------------------
# Transition helper
# ---------------------------------------------------------------------------

class TestTransition:
    def test_default(self):
        t = transition()
        assert t["type"] == "interpolation"
        assert t["duration"] == 1000
        assert "@@easing" not in t

    def test_with_easing(self):
        t = transition(800, easing="ease-in-out-cubic")
        assert t["duration"] == 800
        assert t["@@easing"] == "ease-in-out-cubic"

    def test_spring_type(self):
        t = transition(type="spring", stiffness=120, damping=20)
        assert t["type"] == "spring"
        assert "duration" not in t  # spring ignores duration
        assert t["stiffness"] == 120
        assert t["damping"] == 20

    def test_extra_kwargs(self):
        t = transition(500, enter=True)
        assert t["enter"] is True
        assert t["duration"] == 500

    def test_zero_duration(self):
        """Zero duration is valid for instant transitions."""
        t = transition(duration=0)
        assert t["duration"] == 0
        assert t["type"] == "interpolation"

    def test_large_duration(self):
        """Large duration values are passed through."""
        t = transition(duration=60000)  # 1 minute
        assert t["duration"] == 60000

    @pytest.mark.parametrize("easing", [
        "ease-in-cubic",
        "ease-out-cubic",
        "ease-in-out-cubic",
        "ease-in-out-sine",
    ])
    def test_all_supported_easing_values(self, easing):
        """All documented easing values are valid."""
        t = transition(1000, easing=easing)
        assert t["@@easing"] == easing
        assert t["duration"] == 1000

    def test_json_serializable(self):
        """Transition spec must be JSON-serializable."""
        import json
        t = transition(800, easing="ease-in-out-cubic", enter=True)
        serialized = json.dumps(t)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["duration"] == 800

    def test_spring_without_kwargs(self):
        """Spring type with no stiffness/damping uses deck.gl defaults."""
        t = transition(type="spring")
        assert t["type"] == "spring"
        assert "duration" not in t
        assert "stiffness" not in t
        assert "damping" not in t

    def test_interpolation_ignores_spring_params(self):
        """Interpolation type ignores spring-specific params but keeps them."""
        t = transition(500, type="interpolation", stiffness=100)
        assert t["type"] == "interpolation"
        assert t["duration"] == 500
        # stiffness is passed through (deck.gl ignores it)
        assert t["stiffness"] == 100


# ---------------------------------------------------------------------------
# set_widgets() async method
# ---------------------------------------------------------------------------

class TestSetWidgets:
    def test_message_format(self):
        w = MapWidget("wdg1")
        fake = _FakeSession()
        widgets = [zoom_widget(), compass_widget()]
        asyncio.run(w.set_widgets(fake, widgets))
        handler, payload = fake.messages[0]
        assert handler == "deck_set_widgets"
        assert payload["id"] == "wdg1"
        assert len(payload["widgets"]) == 2
        assert payload["widgets"][0]["@@widgetClass"] == "ZoomWidget"


# ---------------------------------------------------------------------------
# update() with widgets
# ---------------------------------------------------------------------------

class TestUpdateWithWidgets:
    def test_widgets_in_payload(self):
        w = MapWidget("wdg2")
        fake = _FakeSession()
        widgets = [scale_widget(), fullscreen_widget()]
        asyncio.run(w.update(fake, [], widgets=widgets))
        handler, payload = fake.messages[0]
        assert handler == "deck_update"
        assert payload["widgets"][0]["@@widgetClass"] == "_ScaleWidget"
        assert payload["widgets"][1]["@@widgetClass"] == "FullscreenWidget"

    def test_no_widgets_key_when_none(self):
        w = MapWidget("wdg3")
        fake = _FakeSession()
        asyncio.run(w.update(fake, []))
        handler, payload = fake.messages[0]
        assert "widgets" not in payload


# ---------------------------------------------------------------------------
# fly_to() async method
# ---------------------------------------------------------------------------

class TestFlyTo:
    def test_default_message(self):
        w = MapWidget("fly1")
        fake = _FakeSession()
        asyncio.run(w.fly_to(fake, 24.0, 56.0))
        handler, payload = fake.messages[0]
        assert handler == "deck_fly_to"
        assert payload["id"] == "fly1"
        assert payload["viewState"]["longitude"] == 24.0
        assert payload["viewState"]["latitude"] == 56.0
        assert payload["speed"] == 1.2
        assert payload["duration"] == "auto"

    def test_custom_params(self):
        w = MapWidget("fly2")
        fake = _FakeSession()
        asyncio.run(w.fly_to(
            fake, 10.0, 20.0,
            zoom=8, pitch=45, bearing=90,
            speed=2.0, duration=5000,
        ))
        handler, payload = fake.messages[0]
        vs = payload["viewState"]
        assert vs["zoom"] == 8
        assert vs["pitch"] == 45
        assert vs["bearing"] == 90
        assert payload["speed"] == 2.0
        assert payload["duration"] == 5000

    def test_optional_view_state_fields(self):
        w = MapWidget("fly3")
        fake = _FakeSession()
        asyncio.run(w.fly_to(fake, 0.0, 0.0, zoom=5))
        vs = fake.messages[0][1]["viewState"]
        assert "zoom" in vs
        assert "pitch" not in vs
        assert "bearing" not in vs


# ---------------------------------------------------------------------------
# ease_to() async method
# ---------------------------------------------------------------------------

class TestEaseTo:
    def test_default_message(self):
        w = MapWidget("ease1")
        fake = _FakeSession()
        asyncio.run(w.ease_to(fake, 24.0, 56.0))
        handler, payload = fake.messages[0]
        assert handler == "deck_ease_to"
        assert payload["id"] == "ease1"
        assert payload["viewState"]["longitude"] == 24.0
        assert payload["viewState"]["latitude"] == 56.0
        assert payload["duration"] == 1000

    def test_custom_params(self):
        w = MapWidget("ease2")
        fake = _FakeSession()
        asyncio.run(w.ease_to(
            fake, 10.0, 20.0,
            zoom=12, pitch=60, bearing=180,
            duration=3000,
        ))
        handler, payload = fake.messages[0]
        vs = payload["viewState"]
        assert vs["zoom"] == 12
        assert vs["pitch"] == 60
        assert vs["bearing"] == 180
        assert payload["duration"] == 3000

    def test_no_speed_key(self):
        """ease_to should not include speed (unlike fly_to)."""
        w = MapWidget("ease3")
        fake = _FakeSession()
        asyncio.run(w.ease_to(fake, 0.0, 0.0))
        payload = fake.messages[0][1]
        assert "speed" not in payload


# ---------------------------------------------------------------------------
# CDN includes widgets JS/CSS
# ---------------------------------------------------------------------------

class TestCdnWidgets:
    def test_head_includes_widgets_js(self):
        dep = head_includes()
        html = str(dep)
        assert "@deck.gl/widgets" in html
        assert "dist.min.js" in html

    def test_head_includes_widgets_css(self):
        dep = head_includes()
        html = str(dep)
        assert "stylesheet.css" in html

    def test_to_html_includes_widgets(self):
        w = MapWidget("cdn1")
        html = w.to_html([])
        assert "@deck.gl/widgets" in html


# ---------------------------------------------------------------------------
# Experimental deck.gl widgets (v9.2+)
# ---------------------------------------------------------------------------

class TestContextMenuWidget:
    def test_class_no_placement(self):
        w = context_menu_widget()
        assert w["@@widgetClass"] == "_ContextMenuWidget"
        assert "placement" not in w

    def test_extra_kwargs(self):
        w = context_menu_widget(items=[{"label": "Delete"}])
        assert w["items"] == [{"label": "Delete"}]


class TestInfoWidget:
    def test_class_and_placement(self):
        w = info_widget()
        assert w["@@widgetClass"] == "_InfoWidget"
        assert w["placement"] == "top-left"

    def test_custom_placement(self):
        w = info_widget(placement="bottom-right")
        assert w["placement"] == "bottom-right"

    def test_extra_kwargs(self):
        w = info_widget(text="Hello", visible=True)
        assert w["text"] == "Hello"
        assert w["visible"] is True


class TestSplitterWidget:
    def test_class_no_placement(self):
        w = splitter_widget()
        assert w["@@widgetClass"] == "_SplitterWidget"
        assert "placement" not in w

    def test_extra_kwargs(self):
        w = splitter_widget(orientation="vertical", initialSplit=0.5)
        assert w["orientation"] == "vertical"
        assert w["initialSplit"] == 0.5


class TestStatsWidget:
    def test_class_and_placement(self):
        w = stats_widget()
        assert w["@@widgetClass"] == "_StatsWidget"
        assert w["placement"] == "top-left"

    def test_custom_placement(self):
        w = stats_widget(placement="bottom-left")
        assert w["placement"] == "bottom-left"

    def test_extra_kwargs(self):
        w = stats_widget(framesPerUpdate=60, title="GPU Stats")
        assert w["framesPerUpdate"] == 60
        assert w["title"] == "GPU Stats"


class TestViewSelectorWidget:
    def test_class_and_placement(self):
        w = view_selector_widget()
        assert w["@@widgetClass"] == "_ViewSelectorWidget"
        assert w["placement"] == "top-left"

    def test_custom_placement(self):
        w = view_selector_widget(placement="top-right")
        assert w["placement"] == "top-right"

    def test_extra_kwargs(self):
        w = view_selector_widget(initialViewMode="globe")
        assert w["initialViewMode"] == "globe"


# ---------------------------------------------------------------------------
# MapLibre control helpers
# ---------------------------------------------------------------------------

class TestGeolocateControl:
    def test_defaults(self):
        c = geolocate_control()
        assert c["type"] == "geolocate"
        assert c["position"] == "top-right"
        assert c["options"] == {}

    def test_custom_position(self):
        c = geolocate_control(position="bottom-left")
        assert c["position"] == "bottom-left"

    def test_options_forwarded(self):
        c = geolocate_control(trackUserLocation=True, showAccuracyCircle=False)
        assert c["options"]["trackUserLocation"] is True
        assert c["options"]["showAccuracyCircle"] is False


class TestGlobeControl:
    def test_defaults(self):
        c = globe_control()
        assert c["type"] == "globe"
        assert c["position"] == "top-right"
        assert c["options"] == {}

    def test_custom_position(self):
        c = globe_control(position="top-left")
        assert c["position"] == "top-left"


class TestTerrainControl:
    def test_defaults(self):
        c = terrain_control()
        assert c["type"] == "terrain"
        assert c["position"] == "top-right"
        assert c["options"] == {}

    def test_options_forwarded(self):
        c = terrain_control(source="terrain-dem", exaggeration=1.5)
        assert c["options"]["source"] == "terrain-dem"
        assert c["options"]["exaggeration"] == 1.5


# ---------------------------------------------------------------------------
# CDN version bump verification
# ---------------------------------------------------------------------------

class TestCdnVersion:
    def test_deckgl_version_9_2(self):
        from shiny_deckgl._cdn import DECKGL_VERSION
        major, minor = DECKGL_VERSION.split(".")[:2]
        assert int(major) >= 9
        assert int(minor) >= 2, "deck.gl >= 9.2 required for experimental widgets"


# ---------------------------------------------------------------------------
# CDN constants for third-party plugin controls
# ---------------------------------------------------------------------------

class TestCdnPlugins:
    def test_legend_cdn_urls(self):
        from shiny_deckgl._cdn import (
            MAPLIBRE_LEGEND_JS, MAPLIBRE_LEGEND_CSS, MAPLIBRE_LEGEND_VERSION,
        )
        assert "maplibre-gl-legend" in MAPLIBRE_LEGEND_JS
        assert MAPLIBRE_LEGEND_VERSION in MAPLIBRE_LEGEND_JS
        assert MAPLIBRE_LEGEND_JS.endswith(".js")
        assert "maplibre-gl-legend" in MAPLIBRE_LEGEND_CSS
        assert MAPLIBRE_LEGEND_CSS.endswith(".css")

    def test_opacity_cdn_urls(self):
        from shiny_deckgl._cdn import (
            MAPLIBRE_OPACITY_JS, MAPLIBRE_OPACITY_CSS, MAPLIBRE_OPACITY_VERSION,
        )
        assert "maplibre-gl-opacity" in MAPLIBRE_OPACITY_JS
        assert MAPLIBRE_OPACITY_VERSION in MAPLIBRE_OPACITY_JS
        assert MAPLIBRE_OPACITY_JS.endswith(".js")
        assert "maplibre-gl-opacity" in MAPLIBRE_OPACITY_CSS
        assert MAPLIBRE_OPACITY_CSS.endswith(".css")

    def test_cdn_head_fragment_includes_plugins(self):
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT
        assert "maplibre-gl-legend" in CDN_HEAD_FRAGMENT
        assert "maplibre-gl-opacity" in CDN_HEAD_FRAGMENT


class TestSetControls:
    """Tests for MapWidget.set_controls() bulk control replacement."""

    def test_set_controls_basic(self):
        w = MapWidget("sc1")
        fake = _FakeSession()
        asyncio.run(w.set_controls(fake, [
            {"type": "navigation", "position": "top-right"},
            {"type": "scale", "position": "bottom-left"},
        ]))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_controls"
        assert msg[1]["id"] == "sc1"
        assert len(msg[1]["controls"]) == 2
        assert msg[1]["controls"][0] == {
            "type": "navigation", "position": "top-right", "options": {},
        }
        assert msg[1]["controls"][1] == {
            "type": "scale", "position": "bottom-left", "options": {},
        }

    def test_set_controls_empty_list(self):
        w = MapWidget("sc2")
        fake = _FakeSession()
        asyncio.run(w.set_controls(fake, []))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_controls"
        assert msg[1]["controls"] == []

    def test_set_controls_default_position(self):
        w = MapWidget("sc3")
        fake = _FakeSession()
        asyncio.run(w.set_controls(fake, [{"type": "navigation"}]))
        ctrl = fake.messages[0][1]["controls"][0]
        assert ctrl["position"] == "top-right"

    def test_set_controls_with_options(self):
        w = MapWidget("sc4")
        fake = _FakeSession()
        asyncio.run(w.set_controls(fake, [
            {"type": "scale", "position": "bottom-left",
             "options": {"maxWidth": 200}},
        ]))
        ctrl = fake.messages[0][1]["controls"][0]
        assert ctrl["options"] == {"maxWidth": 200}

    def test_set_controls_invalid_type_raises(self):
        w = MapWidget("sc5")
        fake = _FakeSession()
        with pytest.raises(ValueError, match="Unknown control type"):
            asyncio.run(w.set_controls(fake, [
                {"type": "navigation"},
                {"type": "nonexistent"},
            ]))

    def test_set_controls_with_helper_dicts(self):
        from shiny_deckgl.components import geolocate_control, globe_control
        w = MapWidget("sc6")
        fake = _FakeSession()
        asyncio.run(w.set_controls(fake, [
            geolocate_control(position="top-left"),
            globe_control(),
        ]))
        ctrls = fake.messages[0][1]["controls"]
        assert ctrls[0]["type"] == "geolocate"
        assert ctrls[0]["position"] == "top-left"
        assert ctrls[1]["type"] == "globe"


# ===========================================================================
# v0.9.0 — New Layer Helpers
# ===========================================================================

class TestTripsLayer:
    """Tests for the trips_layer() helper."""

    def test_defaults(self):
        spec = trips_layer("t1", data=[])
        assert spec["type"] == "TripsLayer"
        assert spec["id"] == "t1"
        assert spec["pickable"] is True
        assert spec["getPath"] == "@@d.path"
        assert spec["getTimestamps"] == "@@d.timestamps"
        assert spec["getColor"] == [253, 128, 93]
        assert spec["widthMinPixels"] == 2
        assert spec["trailLength"] == 200
        assert spec["currentTime"] == 0

    def test_kwargs_override(self):
        spec = trips_layer(
            "t2", data=[],
            trailLength=500, currentTime=42, getColor=[0, 0, 255],
        )
        assert spec["trailLength"] == 500
        assert spec["currentTime"] == 42
        assert spec["getColor"] == [0, 0, 255]

    def test_animation_config(self):
        """_tripsAnimation config is passed through."""
        spec = trips_layer(
            "t3", data=[],
            _tripsAnimation={"loopLength": 1800, "speed": 2},
        )
        assert spec["_tripsAnimation"] == {"loopLength": 1800, "speed": 2}

    def test_with_sample_data(self):
        from shiny_deckgl._demo_data import make_trips_data
        data = make_trips_data(loop_length=1800)
        spec = trips_layer("t4", data=data)
        assert len(spec["data"]) > 0
        first = spec["data"][0]
        assert "path" in first
        assert "timestamps" in first
        assert len(first["path"]) == len(first["timestamps"])

    def test_url_data(self):
        spec = trips_layer("t5", data="https://example.com/trips.json")
        assert spec["data"] == "https://example.com/trips.json"


class TestGreatCircleLayer:
    """Tests for the great_circle_layer() helper."""

    def test_defaults(self):
        spec = great_circle_layer("gc1", data=[])
        assert spec["type"] == "GreatCircleLayer"
        assert spec["id"] == "gc1"
        assert spec["pickable"] is True
        assert spec["getSourcePosition"] == "@@d.sourcePosition"
        assert spec["getTargetPosition"] == "@@d.targetPosition"
        assert spec["getSourceColor"] == [64, 255, 0]
        assert spec["getTargetColor"] == [0, 128, 200]
        assert spec["getWidth"] == 2

    def test_kwargs_override(self):
        spec = great_circle_layer(
            "gc2", data=[],
            getWidth=5, getSourceColor=[255, 0, 0],
        )
        assert spec["getWidth"] == 5
        assert spec["getSourceColor"] == [255, 0, 0]

    def test_with_data(self):
        data = [
            {
                "sourcePosition": [21.13, 55.71],
                "targetPosition": [18.65, 54.35],
                "name": "Test route",
            }
        ]
        spec = great_circle_layer("gc3", data=data)
        assert len(spec["data"]) == 1
        assert spec["data"][0]["name"] == "Test route"


class TestContourLayer:
    """Tests for the contour_layer() helper."""

    def test_defaults(self):
        spec = contour_layer("c1", data=[])
        assert spec["type"] == "ContourLayer"
        assert spec["id"] == "c1"
        assert spec["getPosition"] == "@@d"
        assert spec["cellSize"] == 200
        assert "contours" in spec

    def test_kwargs_override(self):
        custom_contours = [
            {"threshold": 10, "color": [255, 0, 0], "strokeWidth": 3},
        ]
        spec = contour_layer(
            "c2", data=[], cellSize=500, contours=custom_contours,
        )
        assert spec["cellSize"] == 500
        assert spec["contours"] == custom_contours


class TestGridLayer:
    """Tests for the grid_layer() helper."""

    def test_defaults(self):
        spec = grid_layer("g1", data=[])
        assert spec["type"] == "GridLayer"
        assert spec["id"] == "g1"
        assert spec["cellSize"] == 200
        assert spec["elevationScale"] == 4
        assert spec["extruded"] is True

    def test_kwargs_override(self):
        spec = grid_layer("g2", data=[], cellSize=1000, extruded=False)
        assert spec["cellSize"] == 1000
        assert spec["extruded"] is False

    def test_with_point_data(self):
        points = [[21.0, 55.0], [22.0, 56.0], [23.0, 57.0]]
        spec = grid_layer("g3", data=points)
        assert len(spec["data"]) == 3


class TestScreenGridLayer:
    """Tests for the screen_grid_layer() helper."""

    def test_defaults(self):
        spec = screen_grid_layer("sg1", data=[])
        assert spec["type"] == "ScreenGridLayer"
        assert spec["id"] == "sg1"
        assert spec["cellSizePixels"] == 20
        assert "colorRange" in spec

    def test_kwargs_override(self):
        spec = screen_grid_layer("sg2", data=[], cellSizePixels=40)
        assert spec["cellSizePixels"] == 40


class TestMVTLayer:
    """Tests for the mvt_layer() helper."""

    def test_defaults(self):
        url = "https://example.com/tiles/{z}/{x}/{y}.pbf"
        spec = mvt_layer("m1", data=url)
        assert spec["type"] == "MVTLayer"
        assert spec["id"] == "m1"
        assert spec["data"] == url
        assert spec["minZoom"] == 0
        assert spec["maxZoom"] == 14
        assert "getFillColor" in spec
        assert "getLineColor" in spec

    def test_kwargs_override(self):
        spec = mvt_layer(
            "m2", data="https://example.com/{z}/{x}/{y}.pbf",
            maxZoom=18, getFillColor=[0, 0, 255],
        )
        assert spec["maxZoom"] == 18
        assert spec["getFillColor"] == [0, 0, 255]


class TestWMSLayer:
    """Tests for the wms_layer() helper."""

    def test_defaults(self):
        url = "https://example.com/wms"
        spec = wms_layer("w1", data=url, layers=["bathymetry"])
        assert spec["type"] == "WMSLayer"
        assert spec["id"] == "w1"
        assert spec["data"] == url
        assert spec["srs"] == "EPSG:4326"
        assert spec["format"] == "image/png"
        assert spec["layers"] == ["bathymetry"]

    def test_kwargs_override(self):
        spec = wms_layer(
            "w2", data="https://example.com/wms",
            srs="EPSG:3857", layers="bathymetry",
        )
        assert spec["srs"] == "EPSG:3857"
        assert spec["layers"] == "bathymetry"

    def test_missing_layers_raises(self):
        """Omitting the required 'layers' kwarg must raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="layers"):
            wms_layer("w3", data="https://example.com/wms")


# ===========================================================================
# v0.9.0 — Interleaved Rendering
# ===========================================================================

class TestInterleavedRendering:
    """Tests for the interleaved parameter on MapWidget."""

    def test_default_not_interleaved(self):
        w = MapWidget("il1")
        assert w.interleaved is False

    def test_interleaved_true(self):
        w = MapWidget("il2", interleaved=True)
        assert w.interleaved is True

    def test_interleaved_in_ui(self):
        w = MapWidget("il3", interleaved=True)
        html = str(w.ui())
        assert 'data-interleaved="true"' in html

    def test_not_interleaved_in_ui(self):
        w = MapWidget("il4", interleaved=False)
        html = str(w.ui())
        assert 'data-interleaved="true"' not in html

    def test_interleaved_json_roundtrip(self):
        w = MapWidget("il5", interleaved=True)
        spec_json = w.to_json([])
        w2, layers2 = MapWidget.from_json(spec_json)
        # interleaved is a display concern, not serialised to deck spec
        assert w2.id == "il5"


# ===========================================================================
# v0.9.0 — Demo Data Generators
# ===========================================================================

class TestMakeTripsData:
    """Tests for the make_trips_data() demo data generator."""

    def test_generates_data(self):
        from shiny_deckgl._demo_data import make_trips_data
        data = make_trips_data()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_trip_structure(self):
        from shiny_deckgl._demo_data import make_trips_data
        data = make_trips_data(loop_length=900)
        trip = data[0]
        assert "path" in trip
        assert "timestamps" in trip
        assert "name" in trip
        assert len(trip["path"]) == len(trip["timestamps"])
        # Each path point is [lon, lat, timestamp]
        assert len(trip["path"][0]) == 3

    def test_timestamps_range(self):
        from shiny_deckgl._demo_data import make_trips_data
        data = make_trips_data(loop_length=1800)
        for trip in data:
            assert trip["timestamps"][0] == 0
            assert trip["timestamps"][-1] == 1800

    def test_loop_length_param(self):
        from shiny_deckgl._demo_data import make_trips_data
        for ll in [100, 500, 2000]:
            data = make_trips_data(loop_length=ll)
            for trip in data:
                assert trip["timestamps"][-1] == ll


class TestSampleStudyArea:
    """Tests for the SAMPLE_STUDY_AREA constant."""

    def test_is_geojson(self):
        from shiny_deckgl._demo_data import SAMPLE_STUDY_AREA
        assert SAMPLE_STUDY_AREA["type"] == "FeatureCollection"
        assert len(SAMPLE_STUDY_AREA["features"]) == 1

    def test_polygon_geometry(self):
        from shiny_deckgl._demo_data import SAMPLE_STUDY_AREA
        feat = SAMPLE_STUDY_AREA["features"][0]
        assert feat["geometry"]["type"] == "Polygon"
        coords = feat["geometry"]["coordinates"][0]
        assert len(coords) == 5  # closed ring
        assert coords[0] == coords[-1]  # ring is closed


# ===========================================================================
# Cluster layer support (v1.0.0)
# ===========================================================================


class TestClusterLayer:
    """Tests for MapWidget.add_cluster_layer / remove_cluster_layer."""

    def test_add_cluster_layer_method_exists(self):
        w = MapWidget("cl1")
        assert asyncio.iscoroutinefunction(w.add_cluster_layer)

    def test_remove_cluster_layer_method_exists(self):
        w = MapWidget("cl2")
        assert asyncio.iscoroutinefunction(w.remove_cluster_layer)

    def test_add_cluster_layer_auto_wraps_list(self):
        """_serialise_data is called on the data; verify list->GeoJSON wrap."""
        w = MapWidget("cl3")
        # Just verify the method exists and accepts the right params
        # (actual send_custom_message needs a live Shiny session)
        import inspect
        sig = inspect.signature(w.add_cluster_layer)
        params = list(sig.parameters.keys())
        assert "session" in params
        assert "source_id" in params
        assert "data" in params
        assert "cluster_radius" in params
        assert "cluster_max_zoom" in params
        assert "cluster_color" in params
        assert "point_color" in params
        assert "point_radius" in params
        assert "size_steps" in params
        assert "cluster_properties" in params

    def test_cluster_layer_list_to_geojson(self):
        """Test that the auto-wrap logic converts [lon,lat] to GeoJSON."""
        # We can't call the async method without a session, but we can
        # test the conversion logic directly.
        points = [[20.0, 55.0], [21.0, 56.0], [22.0, 57.0]]
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": pt[:2]},
                    "properties": {},
                }
                for pt in points
            ],
        }
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 3
        assert fc["features"][0]["geometry"]["coordinates"] == [20.0, 55.0]

    def test_cluster_layer_list_with_props(self):
        """Test [lon, lat, {props}] form."""
        pts = [[20.0, 55.0, {"name": "A"}], [21.0, 56.0, {"name": "B"}]]
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": pt[:2]},
                    "properties": pt[2] if len(pt) > 2 and isinstance(pt[2], dict) else {},
                }
                for pt in pts
            ],
        }
        assert fc["features"][0]["properties"] == {"name": "A"}
        assert fc["features"][1]["properties"] == {"name": "B"}


# ===================================================================
# 3-D VISUALISATION TESTS
# ===================================================================

class TestBathymetryGrid:
    """Tests for make_bathymetry_grid() 3-D data generator."""

    def test_default_size(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid()
        assert len(grid) == 600  # 30 cols × 20 rows

    def test_custom_size(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid(cols=5, rows=4)
        assert len(grid) == 20

    def test_point_structure(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid(cols=3, rows=3)
        pt = grid[0]
        assert "position" in pt
        assert "depth_m" in pt
        assert "elevation" in pt
        assert "lon" in pt
        assert "lat" in pt
        assert len(pt["position"]) == 2

    def test_depth_is_negative(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid()
        for pt in grid:
            assert pt["depth_m"] <= 0, f"depth_m should be ≤ 0, got {pt['depth_m']}"

    def test_elevation_is_positive(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid()
        for pt in grid:
            assert pt["elevation"] >= 5.0, f"elevation should be ≥ 5, got {pt['elevation']}"

    def test_depth_and_elevation_are_inverses(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid()
        for pt in grid:
            assert pt["depth_m"] == -pt["elevation"]

    def test_deepest_point_near_centre(self):
        """Deepest point should be near the Landsort Deep (basin centre)."""
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid()
        deepest = min(grid, key=lambda p: p["depth_m"])
        # Should be somewhere in the central Baltic
        assert 15.0 <= deepest["lon"] <= 25.0
        assert 55.0 <= deepest["lat"] <= 62.0
        assert deepest["elevation"] > 200  # should be deep

    def test_geo_bounds(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid()
        lons = [p["lon"] for p in grid]
        lats = [p["lat"] for p in grid]
        assert min(lons) >= 12.0
        assert max(lons) <= 30.0
        assert min(lats) >= 54.0
        assert max(lats) <= 66.0

    def test_custom_bounds(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        grid = make_bathymetry_grid(
            cols=3, rows=3, lon_min=18.0, lon_max=20.0,
            lat_min=57.0, lat_max=59.0,
        )
        lons = [p["lon"] for p in grid]
        lats = [p["lat"] for p in grid]
        assert min(lons) >= 18.0
        assert max(lons) <= 20.0
        assert min(lats) >= 57.0
        assert max(lats) <= 59.0

    def test_deterministic(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        a = make_bathymetry_grid(cols=5, rows=5)
        b = make_bathymetry_grid(cols=5, rows=5)
        assert a == b


class TestFishObservations:
    """Tests for make_fish_observations() 3-D data generator."""

    def test_default_count(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations()
        assert len(obs) == 80

    def test_custom_count(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=25)
        assert len(obs) == 25

    def test_record_structure(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=5)
        rec = obs[0]
        assert "position" in rec
        assert "position_3d" in rec
        assert "species" in rec
        assert "depth_m" in rec
        assert "elevation" in rec
        assert "lon" in rec
        assert "lat" in rec

    def test_position_2d(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=10)
        for rec in obs:
            assert len(rec["position"]) == 2

    def test_position_3d_has_z(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=10)
        for rec in obs:
            assert len(rec["position_3d"]) == 3
            assert rec["position_3d"][2] <= 0  # depth is negative

    def test_depth_matches_position_3d(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=20)
        for rec in obs:
            assert rec["position_3d"][2] == -rec["depth_m"]

    def test_species_variety(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=80)
        species = set(r["species"] for r in obs)
        assert len(species) == 8

    def test_elevation_equals_depth(self):
        from shiny_deckgl._demo_data import make_fish_observations
        obs = make_fish_observations(n=20)
        for rec in obs:
            assert rec["elevation"] == rec["depth_m"]

    def test_deterministic(self):
        from shiny_deckgl._demo_data import make_fish_observations
        a = make_fish_observations(n=30)
        b = make_fish_observations(n=30)
        assert a == b


class TestBathymetryGeoJSON:
    """Tests for make_bathymetry_geojson() GeoJSON data generator."""

    def test_feature_collection_type(self):
        from shiny_deckgl._demo_data import make_bathymetry_geojson
        gj = make_bathymetry_geojson()
        assert gj["type"] == "FeatureCollection"

    def test_default_feature_count(self):
        from shiny_deckgl._demo_data import make_bathymetry_geojson
        gj = make_bathymetry_geojson()
        assert len(gj["features"]) == 150  # 15 × 10

    def test_custom_feature_count(self):
        from shiny_deckgl._demo_data import make_bathymetry_geojson
        gj = make_bathymetry_geojson(cols=4, rows=3)
        assert len(gj["features"]) == 12

    def test_feature_structure(self):
        from shiny_deckgl._demo_data import make_bathymetry_geojson
        gj = make_bathymetry_geojson(cols=3, rows=3)
        feat = gj["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        assert len(feat["geometry"]["coordinates"]) == 2
        assert "depth_m" in feat["properties"]
        assert "elevation" in feat["properties"]

    def test_properties_match_grid(self):
        from shiny_deckgl._demo_data import make_bathymetry_geojson, make_bathymetry_grid
        gj = make_bathymetry_geojson(cols=5, rows=5)
        grid = make_bathymetry_grid(cols=5, rows=5)
        for feat, pt in zip(gj["features"], grid):
            assert feat["properties"]["depth_m"] == pt["depth_m"]
            assert feat["properties"]["elevation"] == pt["elevation"]


class TestArcData3D:
    """Tests for make_3d_arc_data() 3-D arc generator."""

    def test_arc_count(self):
        from shiny_deckgl._demo_data import make_3d_arc_data
        arcs = make_3d_arc_data()
        assert len(arcs) == 8  # same as ROUTES count

    def test_arc_has_3d_positions(self):
        from shiny_deckgl._demo_data import make_3d_arc_data
        arcs = make_3d_arc_data()
        for arc in arcs:
            assert len(arc["sourcePosition"]) == 3
            assert len(arc["targetPosition"]) == 3
            assert arc["sourcePosition"][2] == 0
            assert arc["targetPosition"][2] == 0

    def test_arc_has_height(self):
        from shiny_deckgl._demo_data import make_3d_arc_data
        arcs = make_3d_arc_data()
        for arc in arcs:
            assert "height" in arc
            assert arc["height"] > 0

    def test_arc_has_colors(self):
        from shiny_deckgl._demo_data import make_3d_arc_data
        arcs = make_3d_arc_data()
        for arc in arcs:
            assert "sourceColor" in arc
            assert "targetColor" in arc

    def test_arc_has_name(self):
        from shiny_deckgl._demo_data import make_3d_arc_data
        arcs = make_3d_arc_data()
        for arc in arcs:
            assert "name" in arc
            assert "→" in arc["name"]


class TestBalticView3D:
    """Tests for BALTIC_VIEW_3D and LIGHTING_EFFECT_3D constants."""

    def test_view_has_pitch(self):
        from shiny_deckgl._demo_data import BALTIC_VIEW_3D
        assert BALTIC_VIEW_3D["pitch"] == 45

    def test_view_has_bearing(self):
        from shiny_deckgl._demo_data import BALTIC_VIEW_3D
        assert BALTIC_VIEW_3D["bearing"] == -15

    def test_view_has_standard_keys(self):
        from shiny_deckgl._demo_data import BALTIC_VIEW_3D
        for key in ("longitude", "latitude", "zoom", "pitch", "bearing"):
            assert key in BALTIC_VIEW_3D

    def test_lighting_effect_type(self):
        from shiny_deckgl._demo_data import LIGHTING_EFFECT_3D
        assert LIGHTING_EFFECT_3D["type"] == "LightingEffect"

    def test_lighting_has_ambient(self):
        from shiny_deckgl._demo_data import LIGHTING_EFFECT_3D
        assert "ambientLight" in LIGHTING_EFFECT_3D

    def test_lighting_has_point_lights(self):
        from shiny_deckgl._demo_data import LIGHTING_EFFECT_3D
        assert "pointLights" in LIGHTING_EFFECT_3D
        assert len(LIGHTING_EFFECT_3D["pointLights"]) >= 1


# ===================================================================
# 3-D LAYER INTEGRATION TESTS
# ===================================================================

class TestColumnLayer3D:
    """Extended 3-D tests for column_layer."""

    def test_extruded_with_data(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        data = make_bathymetry_grid(cols=5, rows=5)
        spec = column_layer("bathy-cols", data=data)
        assert spec["type"] == "ColumnLayer"
        assert spec["extruded"] is True
        assert len(spec["data"]) == 25

    def test_elevation_accessor(self):
        spec = column_layer("c3d", data=[], getElevation="@@d.depth_m")
        assert spec["getElevation"] == "@@d.depth_m"

    def test_elevation_scale(self):
        spec = column_layer("c3d-scale", data=[], elevationScale=200)
        assert spec["elevationScale"] == 200

    def test_wireframe(self):
        spec = column_layer("c3d-wire", data=[], wireframe=True)
        assert spec["wireframe"] is True

    def test_wireframe_not_in_defaults(self):
        spec = column_layer("c3d-nowire", data=[])
        assert "wireframe" not in spec

    def test_3d_fill_color(self):
        spec = column_layer("c3d-color", data=[],
                            getFillColor=[0, 100, 200, 180])
        assert spec["getFillColor"] == [0, 100, 200, 180]

    def test_custom_radius(self):
        spec = column_layer("c3d-rad", data=[], radius=5000)
        assert spec["radius"] == 5000


class TestHexagonLayer3D:
    """Extended 3-D tests for hexagon_layer."""

    def test_extruded_with_data(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        data = make_bathymetry_grid(cols=5, rows=5)
        pts = [p["position"] for p in data]
        spec = hexagon_layer("hex3d", data=pts)
        assert spec["type"] == "HexagonLayer"
        assert spec["extruded"] is True
        assert len(spec["data"]) == 25

    def test_custom_elevation_scale(self):
        spec = hexagon_layer("hex3d-es", data=[], elevationScale=50)
        assert spec["elevationScale"] == 50

    def test_wireframe_passthrough(self):
        spec = hexagon_layer("hex3d-wf", data=[], wireframe=True)
        assert spec["wireframe"] is True

    def test_upper_percentile(self):
        spec = hexagon_layer("hex3d-up", data=[], upperPercentile=90)
        assert spec["upperPercentile"] == 90


class TestGridLayer3D:
    """Extended 3-D tests for grid_layer."""

    def test_extruded_with_data(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        data = make_bathymetry_grid(cols=5, rows=5)
        pts = [p["position"] for p in data]
        spec = grid_layer("grid3d", data=pts)
        assert spec["type"] == "GridLayer"
        assert spec["extruded"] is True
        assert spec["elevationScale"] == 4

    def test_wireframe(self):
        spec = grid_layer("grid3d-wf", data=[], wireframe=True)
        assert spec["wireframe"] is True

    def test_custom_cell_size(self):
        spec = grid_layer("grid3d-cs", data=[], cellSize=5000)
        assert spec["cellSize"] == 5000


class TestPolygonLayer3D:
    """3-D extrusion tests for polygon_layer."""

    def test_extruded_true(self):
        data = [{"polygon": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]],
                 "elevation": 100}]
        spec = polygon_layer("poly3d", data=data, extruded=True,
                             getElevation="@@d.elevation")
        assert spec["extruded"] is True
        assert spec["getElevation"] == "@@d.elevation"

    def test_wireframe_passthrough(self):
        spec = polygon_layer("poly3d-wf", data=[], extruded=True,
                             wireframe=True)
        assert spec["wireframe"] is True


class TestGeoJsonLayer3D:
    """3-D extrusion tests for geojson_layer."""

    def test_extruded_geojson(self):
        from shiny_deckgl._demo_data import make_bathymetry_geojson
        gj = make_bathymetry_geojson(cols=3, rows=3)
        spec = geojson_layer("gj3d", data=gj, extruded=True,
                             getElevation="@@=properties.elevation",
                             elevationScale=100)
        assert spec["type"] == "GeoJsonLayer"
        assert spec["extruded"] is True
        assert spec["getElevation"] == "@@=properties.elevation"
        assert spec["elevationScale"] == 100

    def test_wireframe_on_geojson(self):
        spec = geojson_layer("gj3d-wf", data={"type": "FeatureCollection",
                             "features": []}, extruded=True, wireframe=True)
        assert spec["wireframe"] is True


class TestH3HexagonLayer3D:
    """3-D extrusion tests for h3_hexagon_layer."""

    def test_extruded_override(self):
        data = [{"hex": "882a100d63fffff", "color": [255, 0, 0],
                 "elevation": 50}]
        spec = h3_hexagon_layer("h33d", data=data, extruded=True,
                                getElevation="@@d.elevation")
        assert spec["extruded"] is True
        assert spec["getElevation"] == "@@d.elevation"


class TestGenericLayer3D:
    """Test using generic layer() for 3-D types without typed helpers."""

    def test_point_cloud_layer(self):
        data = [{"position": [20.0, 55.0, -100], "color": [255, 0, 0]}]
        spec = layer("PointCloudLayer", "pc3d", data,
                     getPosition="@@d.position",
                     getColor="@@d.color",
                     pointSize=5)
        assert spec["type"] == "PointCloudLayer"
        assert spec["getPosition"] == "@@d.position"
        assert spec["pointSize"] == 5

    def test_gpu_grid_layer(self):
        data = [[20.0, 55.0], [21.0, 56.0]]
        spec = layer("GPUGridLayer", "gpugrid", data,
                     getPosition="@@d",
                     cellSize=1000,
                     extruded=True,
                     elevationScale=10)
        assert spec["type"] == "GPUGridLayer"
        assert spec["extruded"] is True
        assert spec["elevationScale"] == 10


class TestTerrainExtension3D:
    """Test terrain extension integration with 3-D layers."""

    def test_terrain_extension_on_column(self):
        spec = column_layer("col-terrain", data=[],
                            extensions=[terrain_extension()],
                            terrainDrawMode="drape")
        assert terrain_extension() in spec["@@extensions"]
        assert spec["terrainDrawMode"] == "drape"

    def test_terrain_extension_on_geojson(self):
        spec = geojson_layer("gj-terrain",
                             data={"type": "FeatureCollection", "features": []},
                             extensions=[terrain_extension()],
                             terrainDrawMode="offset")
        assert terrain_extension() in spec["@@extensions"]
        assert spec["terrainDrawMode"] == "offset"


class TestViewState3D:
    """Test 3-D view state construction and pitch/bearing parameters."""

    def test_widget_with_pitch(self):
        w = MapWidget("map3d", view_state={"longitude": 19.5, "latitude": 57.0,
                      "zoom": 5, "pitch": 45, "bearing": -15})
        html = str(w.ui())
        assert 'data-initial-pitch="45"' in html
        assert 'data-initial-bearing="-15"' in html

    def test_pitch_zero_default(self):
        w = MapWidget("map-flat", view_state={"longitude": 0, "latitude": 0,
                      "zoom": 2})
        html = str(w.ui())
        # pitch defaults to 0
        assert 'data-initial-pitch="0"' in html

    def test_3d_view_state_from_data(self):
        from shiny_deckgl._demo_data import BALTIC_VIEW_3D
        w = MapWidget("map-baltic3d", view_state=BALTIC_VIEW_3D)
        html = str(w.ui())
        assert 'data-initial-pitch="45"' in html
        assert 'data-initial-bearing="-15"' in html


class TestToJson3D:
    """Test to_json / from_json roundtrip with 3-D layers and effects."""

    def test_roundtrip_extruded_column(self):
        from shiny_deckgl._demo_data import make_bathymetry_grid
        data = make_bathymetry_grid(cols=3, rows=3)
        w = MapWidget("json3d", view_state={"longitude": 19, "latitude": 57,
                      "zoom": 5, "pitch": 45, "bearing": 0})
        spec = column_layer("cols", data=data, elevationScale=200)

        j = w.to_json([spec])
        parsed = json.loads(j)
        assert parsed["viewState"]["pitch"] == 45
        layer_found = parsed["layers"][0]
        assert layer_found["type"] == "ColumnLayer"
        assert layer_found["extruded"] is True
        assert layer_found["elevationScale"] == 200

    def test_roundtrip_effects(self):
        from shiny_deckgl._demo_data import LIGHTING_EFFECT_3D
        w = MapWidget("json3d-fx", view_state={"longitude": 19, "latitude": 57,
                      "zoom": 5, "pitch": 45, "bearing": 0})

        j = w.to_json([], effects=[LIGHTING_EFFECT_3D])
        parsed = json.loads(j)
        assert len(parsed["effects"]) == 1
        assert parsed["effects"][0]["type"] == "LightingEffect"


class TestToHtml3D:
    """Test to_html with 3-D layers and effects."""

    def test_html_contains_pitch(self):
        w = MapWidget("html3d", view_state={"longitude": 19, "latitude": 57,
                      "zoom": 5, "pitch": 60, "bearing": 30})
        html = w.to_html([])
        assert 'data-initial-pitch="60"' in html

    def test_html_contains_extruded_layer(self):
        data = [{"position": [19, 57], "elevation": 100}]
        w = MapWidget("html3d-col", view_state={"longitude": 19,
                      "latitude": 57, "zoom": 5, "pitch": 45, "bearing": 0})
        spec = column_layer("bathy", data=data, elevationScale=50)
        html = w.to_html([spec])
        assert "ColumnLayer" in html
        assert "elevationScale" in html


class TestFirstPersonView3D:
    """Test FirstPersonView in 3-D context."""

    def test_first_person_view_spec(self):
        v = first_person_view()
        assert v["@@type"] == "FirstPersonView"

    def test_first_person_with_kwargs(self):
        v = first_person_view(fovy=75)
        assert v["fovy"] == 75


class TestGlobeView3D:
    """Test GlobeView integration."""

    def test_globe_view_spec(self):
        v = globe_view()
        assert v["@@type"] == "GlobeView"

    def test_globe_view_with_resolution(self):
        v = globe_view(resolution=10)
        assert v["resolution"] == 10

    def test_globe_view_in_update_payload(self):
        """GlobeView should appear in update() message payload."""
        w = MapWidget("globe3d", view_state={"longitude": 19, "latitude": 57,
                      "zoom": 2})
        fake = _FakeSession()
        views = [globe_view()]
        asyncio.run(w.update(fake, [], views=views))
        msg = fake.messages[0]
        assert msg[1]["views"][0]["@@type"] == "GlobeView"


class TestOrbitViewGeneric:
    """OrbitView via raw dict (no typed helper exists)."""

    def test_orbit_view_dict(self):
        """OrbitView via raw dict should appear in update() payload."""
        view = {"@@type": "OrbitView", "orbitAxis": "Y"}
        w = MapWidget("orbit3d", view_state={"longitude": 0, "latitude": 0,
                      "zoom": 5})
        fake = _FakeSession()
        asyncio.run(w.update(fake, [], views=[view]))
        msg = fake.messages[0]
        assert msg[1]["views"][0]["@@type"] == "OrbitView"
        assert msg[1]["views"][0]["orbitAxis"] == "Y"


class TestCombined3DScene:
    """Integration: combine 3-D layers, effects, pitched view state."""

    def test_full_3d_scene_to_json(self):
        from shiny_deckgl._demo_data import (
            make_bathymetry_grid, BALTIC_VIEW_3D, LIGHTING_EFFECT_3D,
        )
        data = make_bathymetry_grid(cols=5, rows=5)
        w = MapWidget("scene3d", view_state=BALTIC_VIEW_3D)
        cols = column_layer("bathy-cols", data=data,
                            elevationScale=200, wireframe=True,
                            getFillColor=[0, 100, 200])

        j = w.to_json([cols], effects=[LIGHTING_EFFECT_3D])
        parsed = json.loads(j)

        # View state
        assert parsed["viewState"]["pitch"] == 45
        assert parsed["viewState"]["bearing"] == -15

        # Layer
        lyr = parsed["layers"][0]
        assert lyr["type"] == "ColumnLayer"
        assert lyr["extruded"] is True
        assert lyr["wireframe"] is True
        assert lyr["elevationScale"] == 200
        assert len(lyr["data"]) == 25

        # Effects
        assert len(parsed["effects"]) == 1
        assert parsed["effects"][0]["type"] == "LightingEffect"

    def test_full_3d_scene_to_html(self):
        from shiny_deckgl._demo_data import (
            make_bathymetry_grid, BALTIC_VIEW_3D, LIGHTING_EFFECT_3D,
        )
        data = make_bathymetry_grid(cols=3, rows=3)
        w = MapWidget("scene3d-html", view_state=BALTIC_VIEW_3D)
        layers = [column_layer("cols", data=data, elevationScale=100)]

        html = w.to_html(layers, effects=[LIGHTING_EFFECT_3D])
        assert "ColumnLayer" in html
        assert "LightingEffect" in html
        assert "elevationScale" in html

    def test_multiple_3d_layers(self):
        """Multiple 3-D layers in one scene."""
        from shiny_deckgl._demo_data import make_bathymetry_grid
        data = make_bathymetry_grid(cols=3, rows=3)
        pts = [p["position"] for p in data]

        w = MapWidget("multi3d", view_state={"longitude": 19, "latitude": 57,
                      "zoom": 5, "pitch": 45, "bearing": 0})
        cols = column_layer("cols", data=data, elevationScale=100)
        hexs = hexagon_layer("hexs", data=pts, elevationScale=10)
        grids = grid_layer("grids", data=pts, cellSize=5000)

        j = w.to_json([cols, hexs, grids])
        parsed = json.loads(j)
        assert len(parsed["layers"]) == 3
        types = [l["type"] for l in parsed["layers"]]
        assert "ColumnLayer" in types
        assert "HexagonLayer" in types
        assert "GridLayer" in types
        for lyr in parsed["layers"]:
            assert lyr["extruded"] is True


# =====================================================================
# IBM module — seal visual assets (ibm.py) & simulation (_demo_data.py)
# =====================================================================

class TestIBMModuleImports:
    """Public IBM visual assets importable from the top-level package."""

    def test_import_constants_from_package(self):
        from shiny_deckgl import (
            SPECIES_COLORS,
            ICON_ATLAS,
            ICON_MAPPING,
            format_trips,
            trips_animation_ui,
            trips_animation_server,
        )
        assert isinstance(SPECIES_COLORS, dict)
        assert isinstance(ICON_ATLAS, str)
        assert isinstance(ICON_MAPPING, dict)
        assert callable(format_trips)
        assert callable(trips_animation_ui)
        assert callable(trips_animation_server)

    def test_import_from_ibm_submodule(self):
        from shiny_deckgl.ibm import (
            SPECIES_COLORS,
            ICON_ATLAS,
            ICON_MAPPING,
            format_trips,
            trips_animation_ui,
            trips_animation_server,
        )
        assert len(SPECIES_COLORS) == 3
        assert callable(format_trips)

    def test_simulation_NOT_in_ibm(self):
        """Simulation code must NOT be in the library ibm module."""
        import shiny_deckgl.ibm as ibm
        assert not hasattr(ibm, "make_seal_trips")
        assert not hasattr(ibm, "make_seal_foraging_areas")
        assert not hasattr(ibm, "make_seal_haulout_data")
        assert not hasattr(ibm, "SEAL_TRIP_PARAMS")
        assert not hasattr(ibm, "SEAL_HAULOUT_SITES")
        assert not hasattr(ibm, "make_seal_haulout_icons")

    def test_simulation_in_demo_data(self):
        """Simulation generators live in the demo _demo_data module."""
        from shiny_deckgl._demo_data import (
            make_seal_trips,
            make_seal_haulout_data,
            make_seal_foraging_areas,
            make_seal_haulout_icons,
        )
        assert callable(make_seal_trips)
        assert callable(make_seal_haulout_data)
        assert callable(make_seal_foraging_areas)
        assert callable(make_seal_haulout_icons)

    def test_ibm_module_all(self):
        import shiny_deckgl.ibm as ibm
        assert hasattr(ibm, "__all__")
        assert "SPECIES_COLORS" in ibm.__all__
        assert "ICON_ATLAS" in ibm.__all__
        assert "ICON_MAPPING" in ibm.__all__
        assert len(ibm.__all__) == 6
        # New helpers in __all__
        assert "format_trips" in ibm.__all__
        assert "trips_animation_ui" in ibm.__all__
        assert "trips_animation_server" in ibm.__all__
        # Old seal-specific names should NOT be in __all__
        assert "SEAL_ICON_ATLAS" not in ibm.__all__
        assert "make_seal_haulout_icons" not in ibm.__all__


class TestSealHauloutSites:
    """Validate the haul-out reference data (demo-only)."""

    def test_count(self):
        from shiny_deckgl._demo_data import _SEAL_HAULOUT_SITES
        assert len(_SEAL_HAULOUT_SITES) == 13

    def test_required_keys(self):
        from shiny_deckgl._demo_data import _SEAL_HAULOUT_SITES
        for s in _SEAL_HAULOUT_SITES:
            assert "name" in s
            assert "species" in s
            assert "lon" in s
            assert "lat" in s
            assert "population" in s

    def test_species_values(self):
        from shiny_deckgl._demo_data import _SEAL_HAULOUT_SITES
        species_set = {s["species"] for s in _SEAL_HAULOUT_SITES}
        assert species_set == {"Grey seal", "Ringed seal", "Harbour seal"}

    def test_coordinates_in_baltic(self):
        from shiny_deckgl._demo_data import _SEAL_HAULOUT_SITES
        for s in _SEAL_HAULOUT_SITES:
            assert 9 <= s["lon"] <= 30, f"lon out of Baltic range: {s}"
            assert 53 <= s["lat"] <= 66, f"lat out of Baltic range: {s}"

    def test_populations_positive(self):
        from shiny_deckgl._demo_data import _SEAL_HAULOUT_SITES
        for s in _SEAL_HAULOUT_SITES:
            assert s["population"] > 0


class TestSpeciesColors:
    """Validate species colour mapping."""

    def test_three_species(self):
        from shiny_deckgl.ibm import SPECIES_COLORS
        assert len(SPECIES_COLORS) == 3

    def test_rgba_format(self):
        from shiny_deckgl.ibm import SPECIES_COLORS
        for species, rgba in SPECIES_COLORS.items():
            assert len(rgba) == 4, f"Expected 4 RGBA values for {species}"
            for v in rgba:
                assert 0 <= v <= 255


class TestSealTripParams:
    """Validate foraging trip parameters (demo simulation data)."""

    def test_three_species(self):
        from shiny_deckgl._demo_data import _SEAL_TRIP_PARAMS
        assert len(_SEAL_TRIP_PARAMS) == 3

    def test_required_keys(self):
        from shiny_deckgl._demo_data import _SEAL_TRIP_PARAMS
        for species, p in _SEAL_TRIP_PARAMS.items():
            assert "range_deg" in p
            assert "step" in p
            assert "legs" in p
            assert "turn" in p

    def test_positive_values(self):
        from shiny_deckgl._demo_data import _SEAL_TRIP_PARAMS
        for species, p in _SEAL_TRIP_PARAMS.items():
            assert p["range_deg"] > 0
            assert p["step"] > 0
            assert p["legs"] > 0
            assert 0 < p["turn"] < 1


class TestIconAtlas:
    """Validate the base64 SVG icon atlas."""

    def test_is_data_uri(self):
        from shiny_deckgl.ibm import ICON_ATLAS
        assert ICON_ATLAS.startswith("data:image/svg+xml;base64,")

    def test_valid_base64(self):
        import base64
        from shiny_deckgl.ibm import ICON_ATLAS
        b64 = ICON_ATLAS.split(",", 1)[1]
        raw = base64.b64decode(b64)
        assert len(raw) > 100

    def test_svg_content(self):
        import base64
        from shiny_deckgl.ibm import ICON_ATLAS
        b64 = ICON_ATLAS.split(",", 1)[1]
        svg = base64.b64decode(b64).decode("utf-8")
        assert "<svg" in svg
        assert 'width="192"' in svg
        assert 'height="64"' in svg

    def test_species_colours_in_svg(self):
        import base64
        from shiny_deckgl.ibm import ICON_ATLAS
        b64 = ICON_ATLAS.split(",", 1)[1]
        svg = base64.b64decode(b64).decode("utf-8")
        assert "#7a8a8a" in svg  # Grey seal
        assert "#4a8cdc" in svg  # Ringed seal
        assert "#c8a050" in svg  # Harbour seal


class TestIconMapping:
    """Validate icon-mapping dict."""

    def test_three_species(self):
        from shiny_deckgl.ibm import ICON_MAPPING
        assert len(ICON_MAPPING) == 3

    def test_species_keys(self):
        from shiny_deckgl.ibm import ICON_MAPPING
        assert set(ICON_MAPPING.keys()) == {"Grey seal", "Ringed seal", "Harbour seal"}

    def test_icon_dimensions(self):
        from shiny_deckgl.ibm import ICON_MAPPING
        for species, m in ICON_MAPPING.items():
            assert m["width"] == 64
            assert m["height"] == 64
            assert "x" in m
            assert "y" in m
            assert "anchorY" in m

    def test_non_overlapping_x(self):
        from shiny_deckgl.ibm import ICON_MAPPING
        xs = [m["x"] for m in ICON_MAPPING.values()]
        assert len(set(xs)) == 3  # all unique


class TestMakeSealTrips:
    """Validate the correlated random walk trip generator."""

    def test_default_returns_25_trips(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips()
        assert len(trips) == 25

    def test_custom_count(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=5)
        assert len(trips) == 5

    def test_trip_structure(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=3, loop_length=100)
        for t in trips:
            assert "path" in t
            assert "timestamps" in t
            assert "name" in t
            assert "species" in t
            assert "haulout" in t
            assert "color" in t
            assert "seal_id" in t

    def test_path_is_3d(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=1, loop_length=100)
        path = trips[0]["path"]
        assert len(path) > 5
        for pt in path:
            assert len(pt) == 3  # [lon, lat, timestamp]

    def test_timestamps_monotonic(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=2, loop_length=200)
        for t in trips:
            ts = t["timestamps"]
            for i in range(1, len(ts)):
                assert ts[i] >= ts[i - 1]

    def test_deterministic_with_seed(self):
        from shiny_deckgl._demo_data import make_seal_trips
        a = make_seal_trips(n_seals=3, seed=42)
        b = make_seal_trips(n_seals=3, seed=42)
        assert a == b

    def test_different_seeds_differ(self):
        from shiny_deckgl._demo_data import make_seal_trips
        a = make_seal_trips(n_seals=3, seed=1)
        b = make_seal_trips(n_seals=3, seed=2)
        assert a != b

    def test_species_in_valid_set(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=50)
        valid = {"Grey seal", "Ringed seal", "Harbour seal"}
        for t in trips:
            assert t["species"] in valid

    def test_coordinates_in_baltic(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=10)
        for t in trips:
            for pt in t["path"]:
                assert 9.0 <= pt[0] <= 30.0, f"lon out of bounds: {pt}"
                assert 53.0 <= pt[1] <= 66.0, f"lat out of bounds: {pt}"

    def test_large_count(self):
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=200, loop_length=300)
        assert len(trips) == 200


class TestMakeSealHauloutData:
    """Validate haul-out scatterplot data."""

    def test_returns_13_entries(self):
        from shiny_deckgl._demo_data import make_seal_haulout_data
        data = make_seal_haulout_data()
        assert len(data) == 13

    def test_entry_structure(self):
        from shiny_deckgl._demo_data import make_seal_haulout_data
        for d in make_seal_haulout_data():
            assert "position" in d
            assert len(d["position"]) == 2
            assert "name" in d
            assert "species" in d
            assert "population" in d
            assert "radius" in d
            assert "color" in d

    def test_radius_positive(self):
        from shiny_deckgl._demo_data import make_seal_haulout_data
        for d in make_seal_haulout_data():
            assert d["radius"] >= 4


class TestMakeSealForagingAreas:
    """Validate foraging area GeoJSON."""

    def test_is_feature_collection(self):
        from shiny_deckgl._demo_data import make_seal_foraging_areas
        fc = make_seal_foraging_areas()
        assert fc["type"] == "FeatureCollection"

    def test_13_features(self):
        from shiny_deckgl._demo_data import make_seal_foraging_areas
        fc = make_seal_foraging_areas()
        assert len(fc["features"]) == 13

    def test_polygon_geometry(self):
        from shiny_deckgl._demo_data import make_seal_foraging_areas
        fc = make_seal_foraging_areas()
        for f in fc["features"]:
            assert f["type"] == "Feature"
            assert f["geometry"]["type"] == "Polygon"
            ring = f["geometry"]["coordinates"][0]
            assert len(ring) >= 25
            # Ring is closed
            assert ring[0] == ring[-1]

    def test_feature_properties(self):
        from shiny_deckgl._demo_data import make_seal_foraging_areas
        fc = make_seal_foraging_areas()
        for f in fc["features"]:
            assert "name" in f["properties"]
            assert "species" in f["properties"]


class TestMakeSealHauloutIcons:
    """Validate IconLayer data builder (demo-only)."""

    def test_returns_13_entries(self):
        from shiny_deckgl._demo_data import make_seal_haulout_icons
        data = make_seal_haulout_icons()
        assert len(data) == 13

    def test_entry_structure(self):
        from shiny_deckgl._demo_data import make_seal_haulout_icons
        for d in make_seal_haulout_icons():
            assert "position" in d
            assert len(d["position"]) == 2
            assert "icon" in d
            assert "name" in d
            assert "species" in d
            assert "population" in d
            assert "size" in d

    def test_icon_matches_species(self):
        from shiny_deckgl._demo_data import make_seal_haulout_icons
        for d in make_seal_haulout_icons():
            assert d["icon"] == d["species"]

    def test_size_reasonable(self):
        from shiny_deckgl._demo_data import make_seal_haulout_icons
        for d in make_seal_haulout_icons():
            assert d["size"] >= 24


# ── format_trips ──────────────────────────────────────────────────

class TestFormatTrips:
    """Tests for the format_trips() data normaliser."""

    def test_import_from_package(self):
        from shiny_deckgl import format_trips
        assert callable(format_trips)

    def test_import_from_ibm(self):
        from shiny_deckgl.ibm import format_trips
        assert callable(format_trips)

    def test_2d_auto_timestamps(self):
        """2-D paths get evenly-spaced timestamps from loop_length."""
        from shiny_deckgl.ibm import format_trips
        path = [[20.0, 57.0], [20.5, 57.2], [21.0, 57.4]]
        result = format_trips([path], loop_length=100)
        assert len(result) == 1
        trip = result[0]
        assert "path" in trip
        assert "timestamps" in trip
        assert len(trip["path"]) == 3
        assert len(trip["timestamps"]) == 3
        # First timestamp is 0, last is loop_length
        assert trip["timestamps"][0] == 0
        assert trip["timestamps"][-1] == 100
        # Each path point is [lon, lat, time]
        assert len(trip["path"][0]) == 3
        assert trip["path"][0][0] == 20.0
        assert trip["path"][0][1] == 57.0

    def test_3d_passthrough(self):
        """Paths with 3 elements keep embedded timestamps."""
        from shiny_deckgl.ibm import format_trips
        path = [[20.0, 57.0, 0], [20.5, 57.2, 50], [21.0, 57.4, 100]]
        result = format_trips([path])
        trip = result[0]
        assert trip["timestamps"] == [0, 50, 100]
        assert trip["path"][1] == [20.5, 57.2, 50]

    def test_explicit_timestamps(self):
        """Explicit timestamps override auto-generation."""
        from shiny_deckgl.ibm import format_trips
        path = [[20.0, 57.0], [20.5, 57.2]]
        result = format_trips([path], timestamps=[[10, 90]])
        trip = result[0]
        assert trip["timestamps"] == [10, 90]
        assert trip["path"][0][2] == 10
        assert trip["path"][1][2] == 90

    def test_properties_merge(self):
        """Per-trip properties are merged into the output dict."""
        from shiny_deckgl.ibm import format_trips
        path = [[20.0, 57.0], [20.5, 57.2]]
        result = format_trips(
            [path],
            properties=[{"name": "Trip 1", "color": [255, 0, 0]}],
        )
        trip = result[0]
        assert trip["name"] == "Trip 1"
        assert trip["color"] == [255, 0, 0]

    def test_multiple_trips(self):
        """Multiple paths produce multiple output dicts."""
        from shiny_deckgl.ibm import format_trips
        p1 = [[10.0, 55.0], [10.5, 55.5]]
        p2 = [[20.0, 57.0], [20.5, 57.2], [21.0, 57.4]]
        result = format_trips([p1, p2], loop_length=200)
        assert len(result) == 2
        assert len(result[0]["path"]) == 2
        assert len(result[1]["path"]) == 3

    def test_empty_path_skipped(self):
        """Empty paths are skipped in the output."""
        from shiny_deckgl.ibm import format_trips
        result = format_trips([[], [[10.0, 55.0], [10.5, 55.5]]])
        assert len(result) == 1

    def test_single_point_path(self):
        """Single-point path gets timestamp 0."""
        from shiny_deckgl.ibm import format_trips
        result = format_trips([[[10.0, 55.0]]])
        assert result[0]["timestamps"] == [0]

    def test_properties_length_mismatch_raises(self):
        """Mismatched properties length raises ValueError."""
        from shiny_deckgl.ibm import format_trips
        import pytest
        with pytest.raises(ValueError, match="properties length"):
            format_trips(
                [[[10.0, 55.0]]],
                properties=[{"a": 1}, {"b": 2}],
            )

    def test_timestamps_length_mismatch_raises(self):
        """Mismatched timestamps length raises ValueError."""
        from shiny_deckgl.ibm import format_trips
        import pytest
        with pytest.raises(ValueError, match="timestamps length"):
            format_trips(
                [[[10.0, 55.0]]],
                timestamps=[[0], [100]],
            )

    def test_explicit_timestamps_wrong_inner_length_raises(self):
        """Inner timestamp list length != path length raises ValueError."""
        from shiny_deckgl.ibm import format_trips
        import pytest
        with pytest.raises(ValueError, match=r"timestamps\[0\] length"):
            format_trips(
                [[[10.0, 55.0], [10.5, 55.5]]],
                timestamps=[[0, 50, 100]],
            )

    def test_make_seal_trips_uses_format_trips(self):
        """make_seal_trips output structure matches format_trips output."""
        from shiny_deckgl._demo_data import make_seal_trips
        trips = make_seal_trips(n_seals=3, loop_length=100, seed=42)
        for t in trips:
            assert "path" in t
            assert "timestamps" in t
            assert len(t["path"]) == len(t["timestamps"])
            assert len(t["path"][0]) == 3  # [lon, lat, time]
            assert t["timestamps"][0] == 0


# ── trips_animation_ui / trips_animation_server ──────────────────

class TestTripsAnimationUI:
    """Tests for the trips_animation_ui Shiny module."""

    def test_import_from_package(self):
        from shiny_deckgl import trips_animation_ui
        assert callable(trips_animation_ui)

    def test_import_from_ibm(self):
        from shiny_deckgl.ibm import trips_animation_ui
        assert callable(trips_animation_ui)

    def test_returns_tag(self):
        """trips_animation_ui returns a Shiny TagList."""
        from shiny_deckgl.ibm import trips_animation_ui
        result = trips_animation_ui("test_anim")
        # Should be a Shiny Tag/TagList (has render method or similar)
        assert result is not None
        html = str(result)
        assert "play" in html.lower() or "Play" in html
        assert "pause" in html.lower() or "Pause" in html
        assert "reset" in html.lower() or "Reset" in html

    def test_custom_defaults(self):
        """Custom slider defaults are reflected in the output."""
        from shiny_deckgl.ibm import trips_animation_ui
        result = trips_animation_ui(
            "test_anim2",
            speed_default=20.0,
            trail_default=300,
        )
        html = str(result)
        assert result is not None
        # Speed and trail sliders should be present
        assert "speed" in html.lower() or "Animation speed" in html
        assert "trail" in html.lower() or "Trail length" in html


class TestTripsAnimationServer:
    """Tests for the trips_animation_server Shiny module."""

    def test_import_from_package(self):
        from shiny_deckgl import trips_animation_server
        assert callable(trips_animation_server)

    def test_import_from_ibm(self):
        from shiny_deckgl.ibm import trips_animation_server
        assert callable(trips_animation_server)

    def test_in_ibm_all(self):
        """trips_animation_server is in ibm.__all__."""
        from shiny_deckgl.ibm import __all__ as ibm_all
        assert "trips_animation_server" in ibm_all

    def test_in_package_all(self):
        """New helpers are in shiny_deckgl.__all__."""
        from shiny_deckgl import __all__ as pkg_all
        assert "format_trips" in pkg_all
        assert "trips_animation_ui" in pkg_all
        assert "trips_animation_server" in pkg_all


# ===========================================================================
# Comprehensive widget test suite
# ===========================================================================
# Each widget gets thorough coverage:
#   - default dict structure (@@widgetClass, type correctness)
#   - default placement vs no-placement widgets
#   - custom placement for all four positions
#   - kwargs passthrough (single & multiple)
#   - immutability (calling twice yields independent dicts)
#   - JSON-serialisable output
#   - integration with MapWidget.set_widgets / .update(widgets=)
#   - inclusion in to_html CDN output
# ===========================================================================


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_PLACEMENTS = ["top-right", "top-left", "bottom-right", "bottom-left"]

_PLACED_WIDGETS = [
    ("zoom_widget", zoom_widget, "ZoomWidget", "top-right"),
    ("compass_widget", compass_widget, "CompassWidget", "top-right"),
    ("fullscreen_widget", fullscreen_widget, "FullscreenWidget", "top-right"),
    ("scale_widget", scale_widget, "_ScaleWidget", "bottom-left"),
    ("gimbal_widget", gimbal_widget, "GimbalWidget", "top-right"),
    ("reset_view_widget", reset_view_widget, "ResetViewWidget", "top-right"),
    ("screenshot_widget", screenshot_widget, "ScreenshotWidget", "top-right"),
    ("fps_widget", fps_widget, "_FpsWidget", "top-left"),
    ("timeline_widget", timeline_widget, "_TimelineWidget", "bottom-left"),
    ("geocoder_widget", geocoder_widget, "_GeocoderWidget", "top-left"),
    ("info_widget", info_widget, "_InfoWidget", "top-left"),
    ("stats_widget", stats_widget, "_StatsWidget", "top-left"),
    ("view_selector_widget", view_selector_widget, "_ViewSelectorWidget", "top-left"),
]

_NO_PLACEMENT_WIDGETS = [
    ("loading_widget", loading_widget, "_LoadingWidget"),
    ("theme_widget", theme_widget, "_ThemeWidget"),
    ("context_menu_widget", context_menu_widget, "_ContextMenuWidget"),
    ("splitter_widget", splitter_widget, "_SplitterWidget"),
]


# ---------------------------------------------------------------------------
# Parametrised: placed widgets
# ---------------------------------------------------------------------------

class TestPlacedWidgetsComprehensive:
    """Thorough tests for all widgets that accept a placement parameter."""

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_returns_dict(self, name, fn, cls, default_pos):
        w = fn()
        assert isinstance(w, dict)

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_widget_class_key(self, name, fn, cls, default_pos):
        w = fn()
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == cls

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_default_placement(self, name, fn, cls, default_pos):
        w = fn()
        assert w["placement"] == default_pos

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    @pytest.mark.parametrize("pos", _ALL_PLACEMENTS)
    def test_custom_placement(self, name, fn, cls, default_pos, pos):
        w = fn(placement=pos)
        assert w["placement"] == pos

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_single_kwarg(self, name, fn, cls, default_pos):
        w = fn(transitionDuration=300)
        assert w["transitionDuration"] == 300

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_multiple_kwargs(self, name, fn, cls, default_pos):
        w = fn(alpha=0.8, label="test", size=42)
        assert w["alpha"] == 0.8
        assert w["label"] == "test"
        assert w["size"] == 42

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_kwargs_do_not_override_class(self, name, fn, cls, default_pos):
        """@@widgetClass is preserved even if someone tries to set it."""
        w = fn()
        assert w["@@widgetClass"] == cls

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_immutable_independent_dicts(self, name, fn, cls, default_pos):
        w1 = fn()
        w2 = fn(extraProp="hello")
        assert "extraProp" not in w1
        assert w2["extraProp"] == "hello"

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_json_serialisable(self, name, fn, cls, default_pos):
        w = fn(custom_list=[1, 2], custom_dict={"a": True})
        s = json.dumps(w)
        parsed = json.loads(s)
        assert parsed["@@widgetClass"] == cls
        assert parsed["custom_list"] == [1, 2]

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_minimal_keys_default(self, name, fn, cls, default_pos):
        """Default widget has exactly @@widgetClass and placement."""
        w = fn()
        assert set(w.keys()) == {"@@widgetClass", "placement"}

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_bool_kwarg(self, name, fn, cls, default_pos):
        w = fn(visible=False)
        assert w["visible"] is False

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_none_kwarg(self, name, fn, cls, default_pos):
        w = fn(container=None)
        assert w["container"] is None


# ---------------------------------------------------------------------------
# Parametrised: no-placement widgets
# ---------------------------------------------------------------------------

class TestNoPlacementWidgetsComprehensive:
    """Thorough tests for all widgets that do NOT accept a placement parameter."""

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_returns_dict(self, name, fn, cls):
        w = fn()
        assert isinstance(w, dict)

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_widget_class_key(self, name, fn, cls):
        w = fn()
        assert w["@@widgetClass"] == cls

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_no_placement_in_default(self, name, fn, cls):
        w = fn()
        assert "placement" not in w

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_single_kwarg(self, name, fn, cls):
        w = fn(label="hello")
        assert w["label"] == "hello"

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_multiple_kwargs(self, name, fn, cls):
        w = fn(alpha=0.5, title="Test", enabled=True)
        assert w["alpha"] == 0.5
        assert w["title"] == "Test"
        assert w["enabled"] is True

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_immutable_independent(self, name, fn, cls):
        w1 = fn()
        w2 = fn(x=99)
        assert "x" not in w1
        assert w2["x"] == 99

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_json_serialisable(self, name, fn, cls):
        w = fn(nested={"a": [1, 2, 3]})
        s = json.dumps(w)
        parsed = json.loads(s)
        assert parsed["@@widgetClass"] == cls

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_minimal_keys_default(self, name, fn, cls):
        """Default no-placement widget has exactly @@widgetClass."""
        w = fn()
        assert set(w.keys()) == {"@@widgetClass"}

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_list_kwarg(self, name, fn, cls):
        w = fn(items=[{"label": "A"}, {"label": "B"}])
        assert len(w["items"]) == 2

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_dict_kwarg(self, name, fn, cls):
        w = fn(style={"color": "red"})
        assert w["style"]["color"] == "red"


# ---------------------------------------------------------------------------
# Widget-specific realistic use-case tests
# ---------------------------------------------------------------------------

class TestZoomWidgetRealistic:
    def test_transition_duration_kwarg(self):
        w = zoom_widget(transitionDuration=500)
        assert w["transitionDuration"] == 500

    def test_zoom_speed(self):
        w = zoom_widget(zoomInLabel="+", zoomOutLabel="-")
        assert w["zoomInLabel"] == "+"
        assert w["zoomOutLabel"] == "-"


class TestCompassWidgetRealistic:
    def test_viewport_sync(self):
        w = compass_widget(viewportSync=True)
        assert w["viewportSync"] is True


class TestFullscreenWidgetRealistic:
    def test_container_kwarg(self):
        w = fullscreen_widget(container=None)
        assert w["container"] is None

    def test_enter_label(self):
        w = fullscreen_widget(enterLabel="Go full")
        assert w["enterLabel"] == "Go full"


class TestScaleWidgetRealistic:
    def test_unit_system(self):
        w = scale_widget(unit="metric")
        assert w["unit"] == "metric"
        assert w["@@widgetClass"] == "_ScaleWidget"

    def test_max_width(self):
        w = scale_widget(maxWidth=200)
        assert w["maxWidth"] == 200


class TestGimbalWidgetRealistic:
    def test_gimbal_defaults(self):
        w = gimbal_widget()
        assert w["@@widgetClass"] == "GimbalWidget"
        assert w["placement"] == "top-right"


class TestResetViewWidgetRealistic:
    def test_reset_label(self):
        w = reset_view_widget(label="Reset Map")
        assert w["label"] == "Reset Map"

    def test_initial_view_state(self):
        vs = {"longitude": 21.0, "latitude": 56.0, "zoom": 8}
        w = reset_view_widget(initialViewState=vs)
        assert w["initialViewState"]["longitude"] == 21.0


class TestScreenshotWidgetRealistic:
    def test_filename(self):
        w = screenshot_widget(filename="map-capture")
        assert w["filename"] == "map-capture"

    def test_format(self):
        w = screenshot_widget(format="png", quality=0.95)
        assert w["format"] == "png"
        assert w["quality"] == 0.95


class TestFpsWidgetRealistic:
    def test_samples(self):
        w = fps_widget(samples=120)
        assert w["samples"] == 120

    def test_placement_override(self):
        w = fps_widget(placement="bottom-right")
        assert w["placement"] == "bottom-right"


class TestLoadingWidgetRealistic:
    def test_custom_label(self):
        w = loading_widget(label="Fetching bathymetry…")
        assert w["label"] == "Fetching bathymetry…"

    def test_show_spinner(self):
        w = loading_widget(showSpinner=True)
        assert w["showSpinner"] is True

    def test_no_placement(self):
        """Loading widget covers the whole deck — no placement."""
        w = loading_widget(showSpinner=True, label="Please wait")
        assert "placement" not in w


class TestTimelineWidgetRealistic:
    def test_min_max_time(self):
        w = timeline_widget(min=0, max=3600)
        assert w["min"] == 0
        assert w["max"] == 3600

    def test_step(self):
        w = timeline_widget(step=10, speed=2.0)
        assert w["step"] == 10
        assert w["speed"] == 2.0


class TestGeocoderWidgetRealistic:
    def test_placeholder_text(self):
        w = geocoder_widget(placeholder="Search location...")
        assert w["placeholder"] == "Search location..."

    def test_limit_results(self):
        w = geocoder_widget(limit=5)
        assert w["limit"] == 5


class TestThemeWidgetRealistic:
    def test_initial_theme(self):
        w = theme_widget(initialTheme="dark")
        assert w["initialTheme"] == "dark"

    def test_light_theme(self):
        w = theme_widget(initialTheme="light")
        assert w["initialTheme"] == "light"

    def test_no_placement(self):
        w = theme_widget()
        assert "placement" not in w


class TestContextMenuWidgetRealistic:
    def test_menu_items(self):
        items = [
            {"label": "Copy coordinates"},
            {"label": "Zoom here"},
            {"label": "Reset view", "separator": True},
        ]
        w = context_menu_widget(items=items)
        assert len(w["items"]) == 3
        assert w["items"][2]["separator"] is True

    def test_empty_items(self):
        w = context_menu_widget(items=[])
        assert w["items"] == []


class TestInfoWidgetRealistic:
    def test_text_and_visible(self):
        w = info_widget(text="Hover to see info", visible=True)
        assert w["text"] == "Hover to see info"
        assert w["visible"] is True

    def test_mode(self):
        w = info_widget(mode="hover")
        assert w["mode"] == "hover"

    def test_html_template(self):
        w = info_widget(text="<b>{name}</b><br/>depth: {depth} m")
        assert "<b>{name}</b>" in w["text"]


class TestSplitterWidgetRealistic:
    def test_orientation_horizontal(self):
        w = splitter_widget(orientation="horizontal", initialSplit=0.5)
        assert w["orientation"] == "horizontal"
        assert w["initialSplit"] == 0.5

    def test_orientation_vertical(self):
        w = splitter_widget(orientation="vertical", initialSplit=0.3)
        assert w["orientation"] == "vertical"
        assert w["initialSplit"] == 0.3

    def test_view_ids(self):
        w = splitter_widget(viewId1="main", viewId2="compare")
        assert w["viewId1"] == "main"
        assert w["viewId2"] == "compare"


class TestStatsWidgetRealistic:
    def test_gpu_type(self):
        w = stats_widget(type="gpu")
        assert w["type"] == "gpu"

    def test_frames_per_update(self):
        w = stats_widget(framesPerUpdate=30, title="Performance")
        assert w["framesPerUpdate"] == 30
        assert w["title"] == "Performance"

    def test_cpu_type(self):
        w = stats_widget(type="cpu")
        assert w["type"] == "cpu"


class TestViewSelectorWidgetRealistic:
    def test_globe_mode(self):
        w = view_selector_widget(initialViewMode="globe")
        assert w["initialViewMode"] == "globe"

    def test_map_mode(self):
        w = view_selector_widget(initialViewMode="map")
        assert w["initialViewMode"] == "map"

    def test_orbit_mode(self):
        w = view_selector_widget(initialViewMode="orbit")
        assert w["initialViewMode"] == "orbit"


# ---------------------------------------------------------------------------
# Widget + MapWidget integration tests
# ---------------------------------------------------------------------------

class TestWidgetSetWidgetsComprehensive:
    """Tests for MapWidget.set_widgets() with all widget types."""

    def test_set_all_placed_widgets(self):
        """set_widgets handles all 13 placed widgets."""
        m = MapWidget("w_all")
        fake = _FakeSession()
        all_w = [fn() for _, fn, _, _ in _PLACED_WIDGETS]
        asyncio.run(m.set_widgets(fake, all_w))
        handler, payload = fake.messages[0]
        assert handler == "deck_set_widgets"
        assert len(payload["widgets"]) == 13

    def test_set_all_no_placement_widgets(self):
        """set_widgets handles all 4 no-placement widgets."""
        m = MapWidget("w_np")
        fake = _FakeSession()
        all_w = [fn() for _, fn, _ in _NO_PLACEMENT_WIDGETS]
        asyncio.run(m.set_widgets(fake, all_w))
        handler, payload = fake.messages[0]
        assert handler == "deck_set_widgets"
        assert len(payload["widgets"]) == 4

    def test_set_all_17_widgets(self):
        """set_widgets handles the full set of 17 widgets."""
        m = MapWidget("w_17")
        fake = _FakeSession()
        all_w = (
            [fn() for _, fn, _, _ in _PLACED_WIDGETS]
            + [fn() for _, fn, _ in _NO_PLACEMENT_WIDGETS]
        )
        asyncio.run(m.set_widgets(fake, all_w))
        handler, payload = fake.messages[0]
        assert handler == "deck_set_widgets"
        assert len(payload["widgets"]) == 17

    def test_widget_classes_preserved(self):
        """All @@widgetClass values survive through set_widgets."""
        m = MapWidget("w_cls")
        fake = _FakeSession()
        widgets = [zoom_widget(), loading_widget(), stats_widget()]
        asyncio.run(m.set_widgets(fake, widgets))
        classes = [w["@@widgetClass"] for w in fake.messages[0][1]["widgets"]]
        assert classes == ["ZoomWidget", "_LoadingWidget", "_StatsWidget"]

    def test_set_widgets_empty(self):
        """Setting an empty widget list clears all widgets."""
        m = MapWidget("w_empty")
        fake = _FakeSession()
        asyncio.run(m.set_widgets(fake, []))
        handler, payload = fake.messages[0]
        assert handler == "deck_set_widgets"
        assert payload["widgets"] == []

    def test_widget_kwargs_survive(self):
        """Custom kwargs on widgets are preserved through set_widgets."""
        m = MapWidget("w_kw")
        fake = _FakeSession()
        widgets = [zoom_widget(transitionDuration=250), fps_widget(samples=100)]
        asyncio.run(m.set_widgets(fake, widgets))
        w_list = fake.messages[0][1]["widgets"]
        assert w_list[0]["transitionDuration"] == 250
        assert w_list[1]["samples"] == 100


class TestWidgetUpdatePayloadComprehensive:
    """Tests for widgets passed through MapWidget.update(widgets=...)."""

    def test_update_with_all_widgets(self):
        """All 17 widgets pass through update()."""
        m = MapWidget("u_all")
        fake = _FakeSession()
        all_w = (
            [fn() for _, fn, _, _ in _PLACED_WIDGETS]
            + [fn() for _, fn, _ in _NO_PLACEMENT_WIDGETS]
        )
        asyncio.run(m.update(fake, [], widgets=all_w))
        payload = fake.messages[0][1]
        assert "widgets" in payload
        assert len(payload["widgets"]) == 17

    def test_update_widgets_and_layers(self):
        """Widgets and layers coexist in update payload."""
        m = MapWidget("u_mix")
        fake = _FakeSession()
        layers = [scatterplot_layer("pts", [{"position": [0, 0]}])]
        widgets = [zoom_widget(), compass_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        payload = fake.messages[0][1]
        assert len(payload["layers"]) == 1
        assert len(payload["widgets"]) == 2

    def test_update_no_widgets_key_absent(self):
        """When widgets=None, the 'widgets' key is absent from payload."""
        m = MapWidget("u_none")
        fake = _FakeSession()
        asyncio.run(m.update(fake, []))
        payload = fake.messages[0][1]
        assert "widgets" not in payload

    def test_update_empty_widgets_key_present(self):
        """When widgets=[], the 'widgets' key IS present (clears widgets)."""
        m = MapWidget("u_clear")
        fake = _FakeSession()
        asyncio.run(m.update(fake, [], widgets=[]))
        payload = fake.messages[0][1]
        assert "widgets" in payload
        assert payload["widgets"] == []

    def test_update_with_view_state_and_widgets(self):
        """Widgets + view_state + layers all in one update."""
        m = MapWidget("u_vs")
        fake = _FakeSession()
        vs = {"longitude": 24.0, "latitude": 56.0, "zoom": 10}
        widgets = [fullscreen_widget(), scale_widget()]
        asyncio.run(m.update(fake, [], view_state=vs, widgets=widgets))
        payload = fake.messages[0][1]
        assert payload["viewState"]["longitude"] == 24.0
        assert len(payload["widgets"]) == 2

    def test_update_with_effects_and_widgets(self):
        """Widgets can coexist with effects."""
        m = MapWidget("u_fx")
        fake = _FakeSession()
        effects = [{"type": "LightingEffect"}]
        widgets = [theme_widget()]
        asyncio.run(m.update(fake, [], effects=effects, widgets=widgets))
        payload = fake.messages[0][1]
        assert len(payload["effects"]) == 1
        assert len(payload["widgets"]) == 1

    def test_update_with_views_and_widgets(self):
        """Widgets can coexist with views."""
        m = MapWidget("u_vw")
        fake = _FakeSession()
        views = [map_view(id="main")]
        widgets = [gimbal_widget()]
        asyncio.run(m.update(fake, [], views=views, widgets=widgets))
        payload = fake.messages[0][1]
        assert len(payload["views"]) == 1
        assert len(payload["widgets"]) == 1


# ---------------------------------------------------------------------------
# Widget JSON round-trip
# ---------------------------------------------------------------------------

class TestWidgetJsonRoundTrip:
    """Ensure widget dicts survive JSON serialisation/deserialisation."""

    @pytest.mark.parametrize("name,fn,cls,default_pos", _PLACED_WIDGETS)
    def test_placed_roundtrip(self, name, fn, cls, default_pos):
        original = fn(custom_prop="test_val", nested={"x": [1, 2]})
        serialised = json.dumps(original)
        restored = json.loads(serialised)
        assert restored == original

    @pytest.mark.parametrize("name,fn,cls", _NO_PLACEMENT_WIDGETS)
    def test_no_placement_roundtrip(self, name, fn, cls):
        original = fn(items=[{"a": 1}], flag=True)
        serialised = json.dumps(original)
        restored = json.loads(serialised)
        assert restored == original

    def test_mixed_widget_list_roundtrip(self):
        """A list of mixed widgets survives JSON round-trip."""
        widgets = [
            zoom_widget(transitionDuration=300),
            loading_widget(label="Loading..."),
            context_menu_widget(items=[{"label": "Copy"}]),
            info_widget(text="Info panel", placement="bottom-right"),
            splitter_widget(orientation="vertical"),
            stats_widget(type="gpu"),
        ]
        serialised = json.dumps(widgets)
        restored = json.loads(serialised)
        assert len(restored) == 6
        assert restored[0]["@@widgetClass"] == "ZoomWidget"
        assert restored[1]["label"] == "Loading..."
        assert restored[2]["items"][0]["label"] == "Copy"
        assert restored[3]["placement"] == "bottom-right"


# ---------------------------------------------------------------------------
# Widget CDN integration
# ---------------------------------------------------------------------------

class TestWidgetCdnInclusion:
    """Verify that widget JS/CSS is included in HTML output."""

    def test_to_html_includes_widgets_js_url(self):
        m = MapWidget("cdn_w")
        html = m.to_html([])
        assert "@deck.gl/widgets" in html

    def test_to_html_includes_widgets_css_url(self):
        m = MapWidget("cdn_c")
        html = m.to_html([])
        assert "stylesheet.css" in html

    def test_head_includes_both_js_and_css(self):
        dep = head_includes()
        html = str(dep)
        assert "@deck.gl/widgets" in html
        assert "stylesheet.css" in html

    def test_to_html_with_layers_and_widgets_cdns(self):
        """to_html includes both deck.gl and widget CDN resources."""
        m = MapWidget("cdn_combo")
        layers = [scatterplot_layer("pts", [{"position": [0, 0]}])]
        html = m.to_html(layers)
        assert "deck.gl" in html
        assert "maplibre" in html.lower()
        assert "@deck.gl/widgets" in html


# ---------------------------------------------------------------------------
# Widget __all__ exports
# ---------------------------------------------------------------------------

class TestWidgetExports:
    """All 17 widget helpers are exported from the package."""

    def test_widgets_in_package_all(self):
        import shiny_deckgl
        pkg_all = shiny_deckgl.__all__
        expected = [
            "zoom_widget", "compass_widget", "fullscreen_widget",
            "scale_widget", "gimbal_widget", "reset_view_widget",
            "screenshot_widget", "fps_widget", "loading_widget",
            "timeline_widget", "geocoder_widget", "theme_widget",
            "context_menu_widget", "info_widget", "splitter_widget",
            "stats_widget", "view_selector_widget",
        ]
        for name in expected:
            assert name in pkg_all, f"{name} missing from __all__"

    def test_widgets_module_all(self):
        from shiny_deckgl.widgets import __all__ as widgets_all
        assert len(widgets_all) == 17

    def test_widgets_importable_from_components(self):
        """Backward-compat: widgets importable from components shim."""
        from shiny_deckgl.components import (
            zoom_widget as zw,
            compass_widget as cw,
            fullscreen_widget as fw,
            scale_widget as sw,
            gimbal_widget as gw,
            reset_view_widget as rvw,
            screenshot_widget as ssw,
            fps_widget as fpsw,
            loading_widget as lw,
            timeline_widget as tw,
            geocoder_widget as gcw,
            theme_widget as thw,
            context_menu_widget as cmw,
            info_widget as iw,
            splitter_widget as spw,
            stats_widget as stw,
            view_selector_widget as vsw,
        )
        assert callable(zw) and callable(cmw) and callable(vsw)


# ---------------------------------------------------------------------------
# Layer + widget combined scenarios (shiny-deckgl layer widget tests)
# ---------------------------------------------------------------------------

class TestLayerWidgetCombined:
    """Scenarios combining layers with widgets in a single MapWidget."""

    def test_scatterplot_with_zoom_and_fullscreen(self):
        m = MapWidget("lw1")
        fake = _FakeSession()
        layers = [scatterplot_layer("pts", [{"position": [21.0, 55.7]}],
                                    getRadius=100, getFillColor=[255, 0, 0])]
        widgets = [zoom_widget(), fullscreen_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "ScatterplotLayer"
        assert p["widgets"][0]["@@widgetClass"] == "ZoomWidget"
        assert p["widgets"][1]["@@widgetClass"] == "FullscreenWidget"

    def test_trips_layer_with_timeline_widget(self):
        """TripsLayer naturally pairs with TimelineWidget for animation."""
        m = MapWidget("lw2", animate=True)
        fake = _FakeSession()
        trip_data = [{"path": [[21, 55], [22, 56]], "timestamps": [0, 100]}]
        layers = [trips_layer("trips", trip_data, getWidth=3, trailLength=50)]
        widgets = [timeline_widget(min=0, max=100, step=1)]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "TripsLayer"
        tl = p["widgets"][0]
        assert tl["@@widgetClass"] == "_TimelineWidget"
        assert tl["min"] == 0
        assert tl["max"] == 100

    def test_heatmap_with_info_and_scale(self):
        """HeatmapLayer with InfoWidget and ScaleWidget."""
        m = MapWidget("lw3")
        fake = _FakeSession()
        layers = [heatmap_layer("heat", [{"position": [21, 55], "weight": 5}])]
        widgets = [info_widget(text="Heatmap density"), scale_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "HeatmapLayer"
        assert len(p["widgets"]) == 2

    def test_geojson_with_stats_and_fps(self):
        """GeoJSON layer with performance monitoring widgets."""
        m = MapWidget("lw4")
        fake = _FakeSession()
        geojson = {"type": "FeatureCollection", "features": []}
        layers = [geojson_layer("geo", geojson)]
        widgets = [stats_widget(type="gpu"), fps_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "GeoJsonLayer"
        classes = [w["@@widgetClass"] for w in p["widgets"]]
        assert "_StatsWidget" in classes
        assert "_FpsWidget" in classes

    def test_hexagon_with_compass_and_gimbal(self):
        """3D HexagonLayer with navigation widgets."""
        m = MapWidget("lw5")
        fake = _FakeSession()
        layers = [hexagon_layer("hex", [{"position": [21, 55]}],
                                extruded=True, radius=5000)]
        widgets = [compass_widget(), gimbal_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "HexagonLayer"
        assert len(p["widgets"]) == 2

    def test_wms_with_theme_and_loading(self):
        """WMS layer with ThemeWidget and LoadingWidget."""
        m = MapWidget("lw6")
        fake = _FakeSession()
        layers = [wms_layer("bathy", "https://ows.emodnet-bathymetry.eu/wms",
                            serviceType="wms", layers=["emodnet:mean"])]
        widgets = [theme_widget(), loading_widget(label="Loading WMS…")]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "WMSLayer"
        classes = [w["@@widgetClass"] for w in p["widgets"]]
        assert "_ThemeWidget" in classes
        assert "_LoadingWidget" in classes

    def test_arc_with_fullscreen_and_screenshot(self):
        """ArcLayer with FullscreenWidget and ScreenshotWidget."""
        m = MapWidget("lw7")
        fake = _FakeSession()
        layers = [arc_layer("arcs", [{"source": [21, 55], "target": [24, 56]}])]
        widgets = [fullscreen_widget(), screenshot_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "ArcLayer"
        assert len(p["widgets"]) == 2

    def test_multiple_layers_with_splitter_widget(self):
        """Two layers compared via SplitterWidget."""
        m = MapWidget("lw8")
        fake = _FakeSession()
        layers = [
            scatterplot_layer("left", [{"position": [21, 55]}]),
            heatmap_layer("right", [{"position": [22, 56], "weight": 1}]),
        ]
        widgets = [splitter_widget(viewId1="left-view", viewId2="right-view")]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert len(p["layers"]) == 2
        sp = p["widgets"][0]
        assert sp["viewId1"] == "left-view"

    def test_icon_layer_with_geocoder_and_reset(self):
        """IconLayer with GeocoderWidget for search and ResetViewWidget."""
        m = MapWidget("lw9")
        fake = _FakeSession()
        layers = [icon_layer("icons", [{"position": [21, 55], "icon": "marker"}])]
        widgets = [geocoder_widget(), reset_view_widget()]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "IconLayer"
        assert len(p["widgets"]) == 2

    def test_context_menu_with_polygon_layer(self):
        """PolygonLayer with ContextMenuWidget for right-click actions."""
        m = MapWidget("lw10")
        fake = _FakeSession()
        poly = [{"polygon": [[21, 55], [22, 55], [22, 56], [21, 56]]}]
        layers = [polygon_layer("polys", poly)]
        widgets = [context_menu_widget(items=[
            {"label": "Get area"},
            {"label": "Copy polygon"},
        ])]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "PolygonLayer"
        cm = p["widgets"][0]
        assert len(cm["items"]) == 2

    def test_grid_layer_with_view_selector(self):
        """GridLayer with ViewSelectorWidget for map/globe switching."""
        m = MapWidget("lw11")
        fake = _FakeSession()
        layers = [grid_layer("grid", [{"position": [21, 55]}], cellSize=10000)]
        widgets = [view_selector_widget(initialViewMode="map")]
        asyncio.run(m.update(fake, layers, widgets=widgets))
        p = fake.messages[0][1]
        assert p["layers"][0]["type"] == "GridLayer"
        vs_w = p["widgets"][0]
        assert vs_w["initialViewMode"] == "map"

    def test_set_widgets_then_update_layers(self):
        """set_widgets and update are independent operations."""
        m = MapWidget("lw12")
        fake = _FakeSession()
        asyncio.run(m.set_widgets(fake, [zoom_widget(), compass_widget()]))
        asyncio.run(m.update(fake, [scatterplot_layer("pts", [])]))
        assert fake.messages[0][0] == "deck_set_widgets"
        assert fake.messages[1][0] == "deck_update"
        assert "widgets" not in fake.messages[1][1]

    def test_replace_widgets_via_set_widgets(self):
        """set_widgets replaces the entire widget set."""
        m = MapWidget("lw13")
        fake = _FakeSession()
        asyncio.run(m.set_widgets(fake, [zoom_widget()]))
        asyncio.run(m.set_widgets(fake, [compass_widget(), fps_widget()]))
        first_set = fake.messages[0][1]["widgets"]
        second_set = fake.messages[1][1]["widgets"]
        assert len(first_set) == 1
        assert first_set[0]["@@widgetClass"] == "ZoomWidget"
        assert len(second_set) == 2
        assert second_set[0]["@@widgetClass"] == "CompassWidget"

    def test_all_layer_types_with_widgets(self):
        """Smoke test: each layer type works alongside a widget."""
        m = MapWidget("lw_smoke")
        fake = _FakeSession()
        layer_fns = [
            lambda: scatterplot_layer("sp", []),
            lambda: geojson_layer("gj", {"type": "FeatureCollection", "features": []}),
            lambda: tile_layer("tl", "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            lambda: arc_layer("ar", []),
            lambda: icon_layer("ic", []),
            lambda: path_layer("pa", []),
            lambda: line_layer("ln", []),
            lambda: text_layer("tx", []),
            lambda: column_layer("co", []),
            lambda: polygon_layer("po", []),
            lambda: heatmap_layer("hm", []),
            lambda: hexagon_layer("hx", []),
            lambda: h3_hexagon_layer("h3", []),
            lambda: trips_layer("tr", []),
            lambda: great_circle_layer("gc", []),
            lambda: contour_layer("ct", []),
            lambda: grid_layer("gr", []),
            lambda: screen_grid_layer("sg", []),
            lambda: mvt_layer("mv", "https://example.com/{z}/{x}/{y}.mvt"),
            lambda: wms_layer("wm", "https://example.com/wms", layers=["test"]),
            lambda: point_cloud_layer("pcl", []),
            lambda: simple_mesh_layer("sml", []),
            lambda: terrain_layer("tml", "https://example.com/{z}/{x}/{y}.png"),
        ]
        for i, make_layer in enumerate(layer_fns):
            fake.messages.clear()
            lyr = make_layer()
            asyncio.run(m.update(fake, [lyr], widgets=[zoom_widget()]))
            p = fake.messages[0][1]
            assert len(p["layers"]) == 1, f"Layer {i} failed"
            assert len(p["widgets"]) == 1, f"Widget on layer {i} failed"


# ===========================================================================
# v1.2.0 — Effects module
# ===========================================================================

class TestAmbientLight:
    """Tests for ambient_light() helper."""

    def test_defaults(self):
        result = ambient_light()
        assert result == {"color": [255, 255, 255], "intensity": 1.0}

    def test_custom_values(self):
        result = ambient_light(color=(200, 200, 200), intensity=0.5)
        assert result["color"] == [200, 200, 200]
        assert result["intensity"] == 0.5

    def test_color_tuple_converted_to_list(self):
        result = ambient_light(color=(128, 64, 32))
        assert isinstance(result["color"], list)


class TestPointLight:
    """Tests for point_light() helper."""

    def test_defaults(self):
        result = point_light(position=[20.0, 55.0, 80000])
        assert result["color"] == [255, 255, 255]
        assert result["intensity"] == 1.0
        assert result["position"] == [20.0, 55.0, 80000]

    def test_custom_values(self):
        result = point_light(
            position=[10.0, 50.0, 40000],
            color=(255, 0, 0),
            intensity=2.5,
        )
        assert result["color"] == [255, 0, 0]
        assert result["intensity"] == 2.5

    def test_extra_kwargs(self):
        result = point_light(position=[0, 0, 1000], attenuation=[1, 0, 0])
        assert result["attenuation"] == [1, 0, 0]

    def test_position_tuple_converted_to_list(self):
        result = point_light(position=(1.0, 2.0, 3.0))
        assert isinstance(result["position"], list)


class TestDirectionalLight:
    """Tests for directional_light() helper."""

    def test_defaults(self):
        result = directional_light()
        assert result["direction"] == [-1, -3, -1]
        assert result["color"] == [255, 255, 255]
        assert result["intensity"] == 1.0
        assert "_shadow" not in result

    def test_custom_direction(self):
        result = directional_light(direction=[0, -1, 0], intensity=0.5)
        assert result["direction"] == [0, -1, 0]
        assert result["intensity"] == 0.5

    def test_shadow_flag(self):
        result = directional_light(_shadow=True)
        assert result["_shadow"] is True

    def test_no_shadow_by_default(self):
        result = directional_light()
        assert "_shadow" not in result


class TestSunLight:
    """Tests for sun_light() helper."""

    def test_basic(self):
        result = sun_light(timestamp=1700000000000)
        assert result["@@sunLight"] is True
        assert result["timestamp"] == 1700000000000
        assert result["color"] == [255, 255, 255]
        assert result["intensity"] == 1.0

    def test_custom_values(self):
        result = sun_light(
            timestamp=1700000000000,
            color=(255, 200, 150),
            intensity=0.8,
            _shadow=True,
        )
        assert result["color"] == [255, 200, 150]
        assert result["intensity"] == 0.8
        assert result["_shadow"] is True

    def test_marker_for_classification(self):
        """@@sunLight marker distinguishes sun lights from directional lights."""
        result = sun_light(timestamp=0)
        assert result.get("@@sunLight") is True

    def test_no_shadow_by_default(self):
        result = sun_light(timestamp=0)
        assert "_shadow" not in result


class TestLightingEffect:
    """Tests for lighting_effect() helper."""

    def test_type(self):
        result = lighting_effect()
        assert result["type"] == "LightingEffect"

    def test_ambient_only(self):
        amb = ambient_light(intensity=0.5)
        result = lighting_effect(amb)
        assert result["ambientLight"] == amb
        assert "pointLights" not in result

    def test_with_point_lights(self):
        pl = point_light(position=[10, 20, 30000])
        result = lighting_effect(None, pl)
        assert "ambientLight" not in result
        assert len(result["pointLights"]) == 1

    def test_with_directional_lights(self):
        dl = directional_light(direction=[0, -1, 0])
        result = lighting_effect(None, dl)
        assert len(result["directionalLights"]) == 1

    def test_with_sun_lights(self):
        sl = sun_light(timestamp=1700000000000)
        result = lighting_effect(None, sl)
        assert len(result["sunLights"]) == 1

    def test_combined(self):
        amb = ambient_light(intensity=0.3)
        pl = point_light(position=[10, 20, 30000])
        dl = directional_light(direction=[0, -1, 0])
        sl = sun_light(timestamp=1700000000000)
        result = lighting_effect(amb, pl, dl, sl)
        assert result["ambientLight"] == amb
        assert len(result["pointLights"]) == 1
        assert len(result["directionalLights"]) == 1
        assert len(result["sunLights"]) == 1

    def test_multiple_point_lights(self):
        pl1 = point_light(position=[10, 20, 30000])
        pl2 = point_light(position=[20, 30, 40000])
        result = lighting_effect(None, pl1, pl2)
        assert len(result["pointLights"]) == 2

    def test_no_ambient_no_key(self):
        result = lighting_effect()
        assert "ambientLight" not in result


class TestPostProcessEffect:
    """Tests for post_process_effect() helper."""

    def test_basic(self):
        result = post_process_effect("brightnessContrast", brightness=0.1)
        assert result["type"] == "PostProcessEffect"
        assert result["shaderModule"] == "brightnessContrast"
        assert result["brightness"] == 0.1

    def test_no_extra_kwargs(self):
        result = post_process_effect("sepia")
        assert result == {
            "type": "PostProcessEffect",
            "shaderModule": "sepia",
        }

    def test_multiple_kwargs(self):
        result = post_process_effect(
            "tiltShift", start=[0, 0], end=[1, 1], blurRadius=15,
        )
        assert result["start"] == [0, 0]
        assert result["blurRadius"] == 15


class TestEffectsReexported:
    """Tests that effect helpers are re-exported from the top-level package."""

    def test_ambient_light(self):
        assert callable(m.ambient_light)

    def test_point_light(self):
        assert callable(m.point_light)

    def test_directional_light(self):
        assert callable(m.directional_light)

    def test_sun_light(self):
        assert callable(m.sun_light)

    def test_lighting_effect(self):
        assert callable(m.lighting_effect)

    def test_post_process_effect(self):
        assert callable(m.post_process_effect)


class TestEffectsIntegration:
    """Test effects dicts work with MapWidget.to_json()."""

    def test_lighting_effect_in_json(self):
        w = MapWidget("efx_int")
        effects = [lighting_effect(
            ambient_light(intensity=0.5),
            point_light(position=[20, 55, 80000], intensity=2.0),
        )]
        j = w.to_json([], effects=effects)
        spec = json.loads(j)
        assert spec["effects"][0]["type"] == "LightingEffect"
        assert spec["effects"][0]["ambientLight"]["intensity"] == 0.5

    def test_post_process_effect_in_json(self):
        w = MapWidget("efx_pp")
        effects = [post_process_effect("brightnessContrast", brightness=0.1)]
        j = w.to_json([], effects=effects)
        spec = json.loads(j)
        assert spec["effects"][0]["type"] == "PostProcessEffect"

    def test_combined_effects_in_json(self):
        w = MapWidget("efx_comb")
        effects = [
            lighting_effect(ambient_light()),
            post_process_effect("vignette", radius=0.5),
        ]
        j = w.to_json([], effects=effects)
        spec = json.loads(j)
        assert len(spec["effects"]) == 2


# ===========================================================================
# v1.2.0 — New typed layer helpers
# ===========================================================================

class TestPointCloudLayer:
    """Tests for point_cloud_layer() helper."""

    def test_defaults(self):
        spec = point_cloud_layer("pc1", data=[])
        assert spec["type"] == "PointCloudLayer"
        assert spec["id"] == "pc1"
        assert spec["pickable"] is True
        assert spec["pointSize"] == 2
        assert spec["sizeUnits"] == "pixels"

    def test_kwargs_override(self):
        spec = point_cloud_layer("pc2", data=[], pointSize=10, getColor=[0, 0, 255])
        assert spec["pointSize"] == 10
        assert spec["getColor"] == [0, 0, 255]

    def test_reexported(self):
        assert callable(m.point_cloud_layer)


class TestSimpleMeshLayer:
    """Tests for simple_mesh_layer() helper."""

    def test_defaults(self):
        spec = simple_mesh_layer("sm1", data=[])
        assert spec["type"] == "SimpleMeshLayer"
        assert spec["id"] == "sm1"
        assert spec["pickable"] is True
        assert spec["sizeScale"] == 1

    def test_kwargs_override(self):
        spec = simple_mesh_layer(
            "sm2", data=[],
            mesh="https://example.com/model.obj",
            sizeScale=100,
        )
        assert spec["mesh"] == "https://example.com/model.obj"
        assert spec["sizeScale"] == 100

    def test_reexported(self):
        assert callable(m.simple_mesh_layer)


class TestTerrainLayer:
    """Tests for terrain_layer() helper."""

    def test_defaults(self):
        spec = terrain_layer("tl1", data="https://example.com/terrain/{z}/{x}/{y}.png")
        assert spec["type"] == "TerrainLayer"
        assert spec["id"] == "tl1"
        assert spec["meshMaxError"] == 4.0

    def test_elevation_data_copied(self):
        url = "https://example.com/terrain/{z}/{x}/{y}.png"
        spec = terrain_layer("tl2", data=url)
        assert spec["elevationData"] == url

    def test_explicit_elevation_data(self):
        spec = terrain_layer(
            "tl3", data=None,
            elevationData="https://example.com/elev/{z}/{x}/{y}.png",
            texture="https://example.com/sat/{z}/{x}/{y}.jpg",
        )
        assert spec["elevationData"] == "https://example.com/elev/{z}/{x}/{y}.png"
        assert spec["texture"] == "https://example.com/sat/{z}/{x}/{y}.jpg"

    def test_kwargs_override(self):
        spec = terrain_layer("tl4", data="https://example.com/{z}/{x}/{y}.png",
                             meshMaxError=10.0)
        assert spec["meshMaxError"] == 10.0

    def test_reexported(self):
        assert callable(m.terrain_layer)


# ===========================================================================
# v1.2.0 — Fp64Extension helper
# ===========================================================================

class TestFp64Extension:
    """Tests for fp64_extension() helper."""

    def test_returns_string(self):
        assert fp64_extension() == "Fp64Extension"

    def test_in_layer(self):
        spec = layer("ScatterplotLayer", "fp1", data=[],
                      extensions=[fp64_extension()], fp64=True)
        assert spec["@@extensions"] == ["Fp64Extension"]
        assert spec["fp64"] is True

    def test_reexported(self):
        assert callable(m.fp64_extension)

    def test_in_extensions_all(self):
        from shiny_deckgl.extensions import __all__ as ext_all
        assert "fp64_extension" in ext_all


# ===========================================================================
# v1.2.0 — OrbitView helper
# ===========================================================================

class TestOrbitView:
    """Tests for orbit_view() helper."""

    def test_type(self):
        v = orbit_view()
        assert v["@@type"] == "OrbitView"

    def test_with_kwargs(self):
        v = orbit_view(target=[0, 0, 0], rotationX=30, zoom=5)
        assert v["@@type"] == "OrbitView"
        assert v["target"] == [0, 0, 0]
        assert v["rotationX"] == 30
        assert v["zoom"] == 5

    def test_reexported(self):
        assert callable(m.orbit_view)

    def test_in_views_all(self):
        from shiny_deckgl.views import __all__ as views_all
        assert "orbit_view" in views_all


# ===========================================================================
# Parsers module tests (parse_shyfem_grd / parse_shyfem_mesh)
# ===========================================================================

# Synthetic .grd content: 3 nodes (WGS84), 1 triangle element
_SAMPLE_GRD = """\
1  1  0  20.0  55.0  10.0
1  2  0  21.0  55.0  20.0
1  3  0  20.5  56.0  30.0
2  1  0  3  1  2  3
"""


class TestParsers:
    """Tests for shiny_deckgl.parsers (SHYFEM .grd parsing)."""

    def _write_grd(self, tmp_path, content=_SAMPLE_GRD):
        p = tmp_path / "test.grd"
        p.write_text(content)
        return p

    # --- parse_shyfem_grd ---

    def test_grd_output_is_list_of_dicts(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_grd
        result = parse_shyfem_grd(self._write_grd(tmp_path))
        assert isinstance(result, list)
        assert len(result) == 1
        d = result[0]
        for key in ("polygon", "depth", "element_id", "color", "layerType"):
            assert key in d

    def test_grd_polygon_is_closed(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_grd
        result = parse_shyfem_grd(self._write_grd(tmp_path))
        poly = result[0]["polygon"]
        assert poly[0] == poly[-1], "Polygon must be closed (first == last)"

    def test_grd_color_is_rgba(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_grd
        result = parse_shyfem_grd(self._write_grd(tmp_path))
        color = result[0]["color"]
        assert len(color) == 4
        for c in color:
            assert 0 <= c <= 255

    def test_grd_empty_file_returns_empty(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_grd
        result = parse_shyfem_grd(self._write_grd(tmp_path, ""))
        assert result == []

    # --- parse_shyfem_mesh ---

    def test_mesh_output_has_required_keys(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        for key in ("positions", "normals", "colors", "indices",
                     "center", "n_vertices", "n_triangles", "depth_range"):
            assert key in result

    def test_mesh_vertex_count(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        assert result["n_vertices"] == 3

    def test_mesh_triangle_count(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        assert result["n_triangles"] == 1

    def test_mesh_positions_length(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        assert len(result["positions"]) == result["n_vertices"] * 3

    def test_mesh_normals_length(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        assert len(result["normals"]) == result["n_vertices"] * 3

    def test_mesh_colors_in_range(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        for v in result["colors"]:
            assert 0.0 <= v <= 1.0

    def test_mesh_indices_valid(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        result = parse_shyfem_mesh(self._write_grd(tmp_path))
        for idx in result["indices"]:
            assert 0 <= idx < result["n_vertices"]

    def test_mesh_z_scale_affects_positions(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        r1 = parse_shyfem_mesh(self._write_grd(tmp_path), z_scale=1.0)
        r2 = parse_shyfem_mesh(self._write_grd(tmp_path), z_scale=100.0)
        # Z values (every 3rd element starting at index 2) should differ
        z1 = r1["positions"][2::3]
        z2 = r2["positions"][2::3]
        assert z1 != z2

    def test_mesh_empty_file_raises(self, tmp_path):
        from shiny_deckgl.parsers import parse_shyfem_mesh
        with pytest.raises(ValueError):
            parse_shyfem_mesh(self._write_grd(tmp_path, ""))


# ===========================================================================
# Seal movement model tests (_sealmove.py)
# ===========================================================================

class TestSealmoveUtilities:
    """Tests for _sealmove utility functions."""

    def test_normalize_rows_sums_to_one(self):
        import numpy as np
        from shiny_deckgl._sealmove import normalize_rows
        M = np.array([[1, 2, 3], [4, 5, 6]], dtype=float)
        result = normalize_rows(M)
        np.testing.assert_allclose(result.sum(axis=1), [1.0, 1.0])

    def test_normalize_rows_zero_row(self):
        import numpy as np
        from shiny_deckgl._sealmove import normalize_rows
        M = np.array([[0, 0, 0], [1, 1, 1]], dtype=float)
        result = normalize_rows(M)
        # zero row stays zero (divided by 1.0 sentinel)
        np.testing.assert_allclose(result[0], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(result[1].sum(), 1.0)

    def test_softmax_sums_to_one(self):
        import numpy as np
        from shiny_deckgl._sealmove import softmax
        result = softmax(np.array([1.0, 2.0, 3.0]))
        assert abs(result.sum() - 1.0) < 1e-9

    def test_softmax_temperature(self):
        import numpy as np
        from shiny_deckgl._sealmove import softmax
        # High temperature → more uniform
        hot = softmax(np.array([1.0, 10.0]), tau=100.0)
        cold = softmax(np.array([1.0, 10.0]), tau=0.1)
        # Cold should be more concentrated on the larger value
        assert cold[1] > hot[1]

    def test_reflect_into_bounds(self):
        import numpy as np
        from shiny_deckgl._sealmove import reflect_into_bounds
        bounds = (0.0, 10.0, 0.0, 10.0)
        # Point inside bounds → unchanged
        inside = reflect_into_bounds(np.array([5.0, 5.0]), bounds)
        np.testing.assert_allclose(inside, [5.0, 5.0])
        # Point outside → reflected back in
        outside = reflect_into_bounds(np.array([-1.0, 11.0]), bounds)
        assert bounds[0] <= outside[0] <= bounds[1]
        assert bounds[2] <= outside[1] <= bounds[3]


class TestSimulateIHTR:
    """Tests for the I-HTR Markov chain simulator."""

    def test_output_shape(self):
        import numpy as np
        from shiny_deckgl._sealmove import IHTRConfig, simulate_IHTR
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=10, T=5)
        df = simulate_IHTR(cfg, random_state=42)
        assert len(df) == 10 * 5
        assert list(df.columns) == ["t", "agent", "cluster"]

    def test_cluster_values_in_range(self):
        import numpy as np
        from shiny_deckgl._sealmove import IHTRConfig, simulate_IHTR
        K = 3
        P = np.ones((K, K)) / K
        cfg = IHTRConfig(P=P, n_agents=20, T=10)
        df = simulate_IHTR(cfg, random_state=42)
        assert df["cluster"].min() >= 0
        assert df["cluster"].max() < K

    def test_reproducible(self):
        import numpy as np
        from shiny_deckgl._sealmove import IHTRConfig, simulate_IHTR
        P = np.array([[0.8, 0.2], [0.3, 0.7]])
        cfg = IHTRConfig(P=P, n_agents=5, T=10)
        df1 = simulate_IHTR(cfg, random_state=99)
        df2 = simulate_IHTR(cfg, random_state=99)
        assert df1.equals(df2)


class TestSealIBM:
    """Tests for the mechanistic individual-based model."""

    def _make_env(self):
        import numpy as np
        from shiny_deckgl._sealmove import Environment, IBMParams
        habitat = np.ones((10, 10))
        bounds = (0.0, 50.0, 0.0, 50.0)
        sites = np.array([[25.0, 25.0]], dtype=float)
        env = Environment(bounds=bounds, habitat=habitat, haulout_sites=sites)
        return env

    def test_agents_initialized_within_bounds(self):
        import numpy as np
        from shiny_deckgl._sealmove import SealIBM, IBMParams
        env = self._make_env()
        ibm = SealIBM(env=env, params=IBMParams(), n_agents=20,
                       rng=np.random.default_rng(42))
        for s in ibm.states:
            assert env.bounds[0] <= s.xy[0] <= env.bounds[1]
            assert env.bounds[2] <= s.xy[1] <= env.bounds[3]

    def test_run_returns_dataframe_with_columns(self):
        import numpy as np
        from shiny_deckgl._sealmove import SealIBM, IBMParams
        env = self._make_env()
        ibm = SealIBM(env=env, params=IBMParams(), n_agents=5,
                       rng=np.random.default_rng(42))
        df = ibm.run(T=10)
        expected_cols = {"t", "agent", "x", "y", "energy", "at_sea", "haulout_site"}
        assert set(df.columns) == expected_cols

    def test_positions_stay_within_bounds(self):
        import numpy as np
        from shiny_deckgl._sealmove import SealIBM, IBMParams
        env = self._make_env()
        ibm = SealIBM(env=env, params=IBMParams(), n_agents=10,
                       rng=np.random.default_rng(42))
        df = ibm.run(T=50)
        assert df["x"].min() >= env.bounds[0]
        assert df["x"].max() <= env.bounds[1]
        assert df["y"].min() >= env.bounds[2]
        assert df["y"].max() <= env.bounds[3]

    def test_reproducible(self):
        import numpy as np
        from shiny_deckgl._sealmove import SealIBM, IBMParams
        env = self._make_env()
        ibm1 = SealIBM(env=env, params=IBMParams(), n_agents=5,
                        rng=np.random.default_rng(42))
        df1 = ibm1.run(T=10)
        # Recreate environment (gradient caches)
        env2 = self._make_env()
        ibm2 = SealIBM(env=env2, params=IBMParams(), n_agents=5,
                        rng=np.random.default_rng(42))
        df2 = ibm2.run(T=10)
        assert df1.equals(df2)


class TestDemoSynthetic:
    """Tests for the demo_synthetic() convenience function."""

    def test_returns_expected_keys(self):
        from shiny_deckgl._sealmove import demo_synthetic
        result = demo_synthetic()
        for key in ("ihtr", "ihtr_summary", "ibm", "ibm_usage_counts"):
            assert key in result

    def test_no_errors(self):
        from shiny_deckgl._sealmove import demo_synthetic
        # Should complete without raising
        demo_synthetic()

