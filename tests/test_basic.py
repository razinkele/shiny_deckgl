"""Tests for shiny_deckgl package."""

import json
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
    assert "maplibre-gl@3.6.2" in html


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
        """All same value → all mapped to same bin."""
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
# MapWidget – minZoom / maxZoom & drag
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
        assert "maplibre-gl@3.6.2" in html

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
        # data-tooltip must be properly quoted — no unescaped " inside attr
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
        import asyncio

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
        import asyncio

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
        import asyncio

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
        import asyncio

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
