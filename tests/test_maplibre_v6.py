"""End-to-end tests for the MapLibre GL JS v6 (ESM) migration.

MapLibre v6 ships no UMD/IIFE build -- `dist/` contains only `.mjs` -- so the
classic `<script src=...maplibre-gl.js>` tag that published the `maplibregl`
global no longer exists. These tests drive a real Chromium via Playwright to
prove the replacement loader actually produces a working map, because nothing
short of a browser can verify an ESM module graph.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[1]


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            b.close()
        return True
    except Exception:
        return False


requires_browser = pytest.mark.skipif(
    not _chromium_available(), reason="Playwright Chromium not available"
)


# ---------------------------------------------------------------------------
# Static contract: no UMD tag, config exposed as a non-executable data block
# ---------------------------------------------------------------------------

class TestMapLibreLoaderContract:
    def test_no_classic_maplibre_script_tag_remains(self):
        """v6 has no .js build; a <script src=...maplibre-gl.js> would 404."""
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT
        assert "maplibre-gl.js" not in CDN_HEAD_FRAGMENT

    def test_maplibre_module_url_points_at_the_esm_build(self):
        from shiny_deckgl._cdn import MAPLIBRE_JS, MAPLIBRE_VERSION
        assert MAPLIBRE_JS.endswith(".mjs")
        assert f"maplibre-gl@{MAPLIBRE_VERSION}" in MAPLIBRE_JS

    def test_cdn_config_is_a_json_data_block_not_executable_script(self):
        """A JSON data block is inert, so a strict script-src CSP allows it."""
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT
        assert 'type="application/json"' in CDN_HEAD_FRAGMENT
        assert 'id="shiny-deckgl-cdn"' in CDN_HEAD_FRAGMENT

    def test_head_fragment_carries_no_inline_executable_javascript(self):
        import re
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT
        for m in re.finditer(r"<script([^>]*)>(.*?)</script>", CDN_HEAD_FRAGMENT, re.S):
            attrs, body = m.group(1), m.group(2).strip()
            if "application/json" in attrs:
                continue
            assert not body, f"inline executable script in head fragment: {body[:80]!r}"

    def test_config_block_parses_and_names_the_module(self):
        import re
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT, MAPLIBRE_JS
        m = re.search(
            r'<script type="application/json" id="shiny-deckgl-cdn">(.*?)</script>',
            CDN_HEAD_FRAGMENT, re.S,
        )
        assert m, "config block not found"
        assert json.loads(m.group(1))["maplibre"] == MAPLIBRE_JS


# ---------------------------------------------------------------------------
# The real thing: a browser
# ---------------------------------------------------------------------------

@requires_browser
class TestStandaloneExportInABrowser:
    """to_html() must produce a page that renders deck.gl layers over MapLibre.

    The standalone bootstrap calls initMap() synchronously, so the ESM load has
    to be awaited before init -- a polling gate alone (which the Shiny path
    uses) is not enough here.
    """

    @staticmethod
    def _export(tmp_path) -> Path:
        from shiny_deckgl import MapWidget, scatterplot_layer, text_layer
        lyr = scatterplot_layer(
            "pts",
            [{"position": [21.0, 55.0]}, {"position": [22.0, 56.0]}],
            getPosition="@@=d.position",
            getRadius=40000,
            getFillColor=[255, 0, 0],
        )
        # Lithuanian label: deck.gl's default ASCII font atlas cannot render
        # this, and logs "Missing character" -- which the no-console-errors
        # test below turns into a failure.
        labels = text_layer(
            "labels",
            [{"position": [21.14, 55.70], "text": "Klaip\u0117da"}],
            getPosition="@@=d.position",
            getText="@@=d.text",
        )
        w = MapWidget("export_map", view_state={"longitude": 21.5, "latitude": 55.5, "zoom": 5})
        out = tmp_path / "export.html"
        w.to_html([lyr, labels], path=str(out), title="v6 export")
        return out

    @pytest.fixture(scope="class")
    def rendered(self, tmp_path_factory):
        from playwright.sync_api import sync_playwright

        tmp_path = tmp_path_factory.mktemp("export")
        page_path = self._export(tmp_path)
        errors: list[str] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console",
                    lambda m: errors.append(f"console.error: {m.text}")
                    if m.type == "error" else None)
            page.goto(page_path.as_uri())
            try:
                page.wait_for_function(
                    "window.maplibregl && window.__deckgl_instances "
                    "&& Object.keys(window.__deckgl_instances).length > 0",
                    timeout=60000,
                )
                try:
                    page.wait_for_function(
                        "(() => { const i = window.__deckgl_instances['export_map'];"
                        " return i && i.map && i.map.loaded() && i.map.areTilesLoaded(); })()",
                        timeout=45000,
                    )
                except Exception:
                    pass
                page.wait_for_timeout(2000)
                state = page.evaluate("""
                  (() => {
                    const inst = window.__deckgl_instances['export_map'];
                    if (!inst) return {ok: false, why: 'no instance'};
                    const dk = inst.overlay && (inst.overlay._deck || inst.overlay.deck);
                    return {
                      ok: true,
                      maplibreVersion: window.maplibregl.getVersion(),
                      mapLoaded: !!inst.map,
                      hasDeckCanvas: !!(dk && (typeof dk.getCanvas === 'function'
                                               ? dk.getCanvas() : dk.canvas)),
                      layerCount: (dk && dk.props && dk.props.layers)
                                  ? dk.props.layers.length : -1,
                      tilesLoaded: !!(inst.map && inst.map.loaded()
                                      && inst.map.areTilesLoaded()),
                      center: inst.map ? inst.map.getCenter() : null,
                    };
                  })()
                """)
            finally:
                browser.close()
        return state, errors

    def test_page_loads_without_javascript_errors(self, rendered):
        _, errors = rendered
        assert not errors, "browser reported errors:\n" + "\n".join(errors[:8])

    def test_export_runs_the_umd_build_not_the_esm_one(self, rendered):
        """file:// exports must stay on v5: see TestExportsCannotUseV6."""
        from shiny_deckgl._cdn import MAPLIBRE_EXPORT_VERSION
        state, _ = rendered
        assert state["ok"], state
        assert state["maplibreVersion"] == MAPLIBRE_EXPORT_VERSION

    def test_basemap_tiles_actually_load_from_disk(self, rendered):
        """The regression that version-split exists to prevent.

        Under MapLibre 6 the deck.gl layers still draw but the basemap never
        arrives, so this fails silently unless asserted explicitly.
        """
        state, _ = rendered
        assert state["tilesLoaded"] is True, "basemap tiles never loaded from file://"

    def test_the_map_initialised(self, rendered):
        state, _ = rendered
        assert state["mapLoaded"] is True
        assert state["center"]["lng"] == pytest.approx(21.5, abs=0.01)

    def test_deck_layers_render_over_the_basemap(self, rendered):
        state, _ = rendered
        assert state["hasDeckCanvas"] is True, "deck.gl produced no canvas"
        assert state["layerCount"] == 2


@requires_browser
class TestShinyHeadFragmentInABrowser:
    """The Shiny path loads deckgl-init.js *before* the CDN head fragment.

    The loader therefore has to cope with being defined before its config block
    exists in the DOM, which is why the existing readiness gate polls.
    """

    @pytest.fixture(scope="class")
    def probe(self, tmp_path_factory):
        from playwright.sync_api import sync_playwright
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT

        js = (ROOT / "src" / "shiny_deckgl" / "resources" / "deckgl-init.js").read_text(
            encoding="utf-8")
        tmp = tmp_path_factory.mktemp("shinyish")
        # Mirror the real ordering: local init script first, CDN fragment after.
        (tmp / "page.html").write_text(
            "<!doctype html><html><head>\n"
            "<script>window.Shiny={setInputValue(){},addCustomMessageHandler(){}};</script>\n"
            f"<script>{js}</script>\n"
            f"{CDN_HEAD_FRAGMENT}\n"
            "</head><body></body></html>",
            encoding="utf-8",
        )
        errors: list[str] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.goto((tmp / "page.html").as_uri())
            try:
                page.wait_for_function(
                    "typeof window.__deckgl_loadMapLibre === 'function'", timeout=30000)
                got = page.evaluate("""
                  (async () => {
                    try {
                      const ns = await window.__deckgl_loadMapLibre();
                      return {ok: true, version: ns.getVersion(),
                              onWindow: typeof window.maplibregl.Map};
                    } catch (e) { return {ok: false, error: String(e)}; }
                  })()
                """)
            finally:
                browser.close()
        return got, errors

    def test_loader_resolves_the_module_from_its_config_block(self, probe):
        got, errors = probe
        assert got["ok"], got
        assert not errors, errors[:5]

    def test_loader_publishes_the_global_the_init_gate_polls_for(self, probe):
        from shiny_deckgl._cdn import MAPLIBRE_VERSION
        got, _ = probe
        assert got["version"] == MAPLIBRE_VERSION
        assert got["onWindow"] == "function"


class TestExportsCannotUseV6:
    """MapLibre 6 cannot run from a file:// page, so exports stay on v5.

    v6 spawns its tile worker as `new Worker(blob:..., {type: "module"})`. On an
    opaque (null) origin that worker cannot resolve its own module imports and
    dies without firing a map error -- deck.gl layers still draw, but the
    basemap silently never loads. v5 used a classic worker, which blob:null
    allows. Verified in Chromium: v5 file:// loads tiles, v6 file:// does not,
    v6 http:// does.
    """

    def test_export_head_uses_a_classic_script_tag(self):
        from shiny_deckgl import MapWidget
        html = MapWidget("m").to_html([])
        assert "maplibre-gl.js" in html, "export must load the UMD build"
        assert "maplibre-gl.mjs" not in html, "export must not load the ESM build"

    def test_export_pin_is_the_last_v5_release(self):
        from shiny_deckgl._cdn import MAPLIBRE_EXPORT_VERSION
        assert MAPLIBRE_EXPORT_VERSION.startswith("5.")

    def test_served_pages_still_get_v6(self):
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT, MAPLIBRE_VERSION
        assert MAPLIBRE_VERSION.startswith("6.")
        assert f"maplibre-gl@{MAPLIBRE_VERSION}" in CDN_HEAD_FRAGMENT

    def test_the_two_pins_are_independent(self):
        from shiny_deckgl._cdn import MAPLIBRE_EXPORT_VERSION, MAPLIBRE_VERSION
        assert MAPLIBRE_EXPORT_VERSION != MAPLIBRE_VERSION


@requires_browser
class TestShinyConnectedIsReceived:
    """deckgl-init.js listened for `shiny:connected` with addEventListener.

    Shiny dispatches that event through jQuery -- `$(document).trigger({type:
    "shiny:connected"})` -- and a jQuery-triggered event never reaches a native
    addEventListener handler. The initial-load init gate therefore never ran, so
    the map on the first tab stayed blank; only maps whose tab was switched to
    came up, because `shown.bs.tab` is a genuine native Bootstrap event.
    """

    @staticmethod
    def _page_html():
        from shiny_deckgl._cdn import CDN_HEAD_FRAGMENT
        js = (ROOT / "src" / "shiny_deckgl" / "resources" / "deckgl-init.js").read_text(
            encoding="utf-8")
        return (
            "<!doctype html><html><head>"
            '<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>'
            "<script>window.Shiny={setInputValue(){},addCustomMessageHandler(){}};</script>"
            f"<script>{js}</script>{CDN_HEAD_FRAGMENT}</head><body>"
            '<div id="jq_map" class="deckgl-map" style="width:600px;height:400px"'
            ' data-initial-longitude="21.2" data-initial-latitude="55.7"'
            ' data-initial-zoom="8" data-style="https://basemaps.cartocdn.com/gl/'
            'positron-nolabels-gl-style/style.json"></div></body></html>'
        )

    def _init_via(self, trigger_js):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            try:
                page.set_content(self._page_html())
                page.wait_for_function(
                    "typeof window.jQuery === 'function' && typeof deck !== 'undefined'",
                    timeout=60000)
                page.evaluate(trigger_js)
                try:
                    page.wait_for_function(
                        "window.__deckgl_instances "
                        "&& window.__deckgl_instances['jq_map']", timeout=30000)
                    return True
                except Exception:
                    return False
            finally:
                browser.close()

    def test_jquery_triggered_event_initialises_the_map(self):
        """This is how Shiny actually signals readiness."""
        assert self._init_via(
            "jQuery(document).trigger({type: 'shiny:connected'})"
        ), "a jQuery-triggered shiny:connected did not initialise the map"

    def test_native_event_still_initialises_the_map(self):
        """Standalone/other hosts may dispatch a real DOM event."""
        assert self._init_via(
            "document.dispatchEvent(new Event('shiny:connected'))"
        ), "a native shiny:connected did not initialise the map"
