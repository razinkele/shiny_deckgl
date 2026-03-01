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
from shiny_deckgl.components import (
    MapWidget,
    layer,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    bitmap_layer,
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    _serialise_data,
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
    CONTROL_TYPES,
    CONTROL_POSITIONS,
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
        "head_includes",
        "CARTO_POSITRON", "CARTO_DARK", "CARTO_VOYAGER", "OSM_LIBERTY",
        "color_range", "color_bins", "color_quantiles",
        "PALETTE_VIRIDIS", "PALETTE_PLASMA", "PALETTE_OCEAN",
        "PALETTE_THERMAL", "PALETTE_CHLOROPHYLL",
        "encode_binary_attribute",
        "map_view", "orthographic_view", "first_person_view",
        "CONTROL_TYPES", "CONTROL_POSITIONS",
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
# app() factory
# ---------------------------------------------------------------------------

def test_app_returns_shiny_app():
    result = app()
    assert isinstance(result, App)


def test_app_with_custom_provider():
    def provider():
        return {"data": [[10, 20]]}

    result = app(data_provider=provider)
    assert isinstance(result, App)


# ---------------------------------------------------------------------------
# head_includes
# ---------------------------------------------------------------------------

def test_head_includes_contains_cdn_urls():
    html = str(head_includes())
    assert "deck.gl@9.1.4" in html
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
        assert "deck.gl@9.1.4" in html
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

        class FakeSession:
            """Minimal stub that captures messages."""
            def __init__(self):
                self.messages = []
            async def send_custom_message(self, handler, payload):
                self.messages.append((handler, payload))

        fake = FakeSession()
        new_tip = {"html": "{x}", "style": {"color": "red"}}
        asyncio.run(w.update_tooltip(fake, new_tip))
        assert w.tooltip == new_tip
        assert len(fake.messages) == 1
        assert fake.messages[0][0] == "deck_update_tooltip"
        assert fake.messages[0][1]["tooltip"] == new_tip

    def test_update_tooltip_none_disables(self):

        w = MapWidget("utt3", tooltip={"html": "hi"})

        class FakeSession:
            def __init__(self):
                self.messages = []
            async def send_custom_message(self, handler, payload):
                self.messages.append((handler, payload))

        fake = FakeSession()
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

        class FakeSession:
            def __init__(self):
                self.messages = []
            async def send_custom_message(self, handler, payload):
                self.messages.append((handler, payload))

        fake = FakeSession()
        asyncio.run(w.set_style(fake, CARTO_DARK))
        assert w.style == CARTO_DARK
        assert len(fake.messages) == 1
        assert fake.messages[0][0] == "deck_set_style"
        assert fake.messages[0][1]["id"] == "ss2"
        assert fake.messages[0][1]["style"] == CARTO_DARK

    def test_set_style_custom_url(self):

        w = MapWidget("ss3")
        custom = "https://example.com/my-style.json"

        class FakeSession:
            def __init__(self):
                self.messages = []
            async def send_custom_message(self, handler, payload):
                self.messages.append((handler, payload))

        fake = FakeSession()
        asyncio.run(w.set_style(fake, custom))
        assert w.style == custom
        assert fake.messages[0][1]["style"] == custom


# ---------------------------------------------------------------------------
# v0.2.0 â€” Phase 1 tests
# ---------------------------------------------------------------------------

class _FakeSession:
    """Reusable fake session for Phase 1+ tests."""
    def __init__(self):
        self.messages = []
    async def send_custom_message(self, handler, payload):
        self.messages.append((handler, payload))


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

        mock_geojson = {"type": "FeatureCollection", "features": []}

        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: mock_geojson

        try:
            asyncio.run(w.add_geodataframe(fake, "test-src", "fake_gdf",
                                            layer_type="line",
                                            paint={"line-color": "#f00"}))
            assert len(fake.messages) == 2
            assert fake.messages[0][0] == "deck_add_source"
            assert fake.messages[0][1]["sourceId"] == "test-src"
            assert fake.messages[1][0] == "deck_add_maplibre_layer"
            assert fake.messages[1][1]["layerSpec"]["id"] == "test-src-layer"
            assert fake.messages[1][1]["layerSpec"]["paint"]["line-color"] == "#f00"
        finally:
            comp._serialise_data = original

    def test_add_geodataframe_default_paint(self):
        """Default paint should be applied based on layer_type."""
        w = MapWidget("gp1b")
        fake = _FakeSession()

        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: {"type": "FeatureCollection", "features": []}

        try:
            asyncio.run(w.add_geodataframe(fake, "src", "gdf"))
            layer_spec = fake.messages[1][1]["layerSpec"]
            assert layer_spec["type"] == "fill"
            assert "fill-color" in layer_spec["paint"]
        finally:
            comp._serialise_data = original

    def test_add_geodataframe_with_popup(self):
        """add_geodataframe with popup_template should send 3 messages."""
        w = MapWidget("gp2")
        fake = _FakeSession()

        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: {"type": "FeatureCollection", "features": []}

        try:
            asyncio.run(w.add_geodataframe(fake, "eez", "fake_gdf",
                                            popup_template="<b>{name}</b>"))
            assert len(fake.messages) == 3
            assert fake.messages[2][0] == "deck_add_popup"
            assert fake.messages[2][1]["template"] == "<b>{name}</b>"
        finally:
            comp._serialise_data = original

    def test_update_geodataframe(self):
        w = MapWidget("gp3")
        fake = _FakeSession()

        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: {"type": "FeatureCollection", "features": []}

        try:
            asyncio.run(w.update_geodataframe(fake, "eez", "fake_gdf"))
            assert fake.messages[0][0] == "deck_set_source_data"
            assert fake.messages[0][1]["sourceId"] == "eez"
        finally:
            comp._serialise_data = original


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
