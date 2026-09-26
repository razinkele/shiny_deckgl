"""Native MapLibre calls must not wait forever while tiles load (J3).

whenStyleReady() ran a callback immediately only when map.isStyleLoaded()
was true, and otherwise queued it until the next 'style.load'. But
isStyleLoaded() is also false while any source or tile is still loading --
for instance straight after add_source(), or while the user pans -- and
'style.load' only fires again on the next set_style(). Such calls were
queued forever, with nothing logged.

Needs chromium and network access for the CDN bundles and basemap tiles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18768

_HAS_LAYER = """(id) => {
  const inst = window.__deckgl_instances && window.__deckgl_instances.smap;
  return !!(inst && inst.map.getLayer(id));
}"""


@pytest.fixture(scope="module")
def page():
    with running_app("style_queue_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#smap .maplibregl-canvas") as pg:
            # Let the basemap finish its first load so the map is idle.
            pg.wait_for_function(
                "() => { const i = window.__deckgl_instances && window.__deckgl_instances.smap;"
                " return !!(i && i.map.loaded()); }", timeout=30000)
            yield pg


def test_readiness_uses_the_parsed_style_flag(page):
    """isStyleReady() relies on MapLibre's style._loaded; make sure it exists."""
    assert page.evaluate(
        "() => typeof window.__deckgl_instances.smap.map.style._loaded") == "boolean"


def test_layer_added_right_after_its_source_appears(page):
    page.click("#add")
    page.wait_for_function(_HAS_LAYER, arg="pts-circle-1", timeout=10000)


def test_layer_added_while_the_map_is_panning_appears(page):
    # Start a long pan so tiles are loading when the messages arrive.
    page.evaluate("() => window.__deckgl_instances.smap.map.panBy([600, 300], {duration: 3000})")
    page.wait_for_timeout(200)
    page.click("#add")
    page.wait_for_function(_HAS_LAYER, arg="pts-circle-2", timeout=10000)


def test_reapplying_the_current_basemap_settles_quickly(page):
    """J4: set_style() with the style already shown must not stall 30 s.

    MapLibre diffs by default; a no-op diff never fires 'style.load', so the
    guard flag stayed up until the 30 s timeout, which then threw the queued
    calls away. The demo's MapLibre tab lost its native layers this way at
    start-up.
    """
    page.click("#same")
    page.wait_for_function(_HAS_LAYER, arg="same-circle-1", timeout=10000)


@pytest.mark.parametrize("n", [1, 2])
def test_layer_readded_after_a_basemap_swap_appears(page, n):
    page.click("#restyle")
    page.wait_for_function(_HAS_LAYER, arg=f"re-circle-{n}", timeout=20000)
    # The earlier layers went with the old style, as documented.
    assert page.evaluate(_HAS_LAYER, "pts-circle-1") is False


_LEGEND_ROWS = ("() => [...document.querySelectorAll('#smap .legend-table tr')]"
                ".map(r => r.innerText.trim())")


def test_default_legend_lists_only_the_apps_layers(page):
    """M2: legend_control() without targets lists the app's native layers only.

    Also covers the redraw after a layer is added: the plugin's own refresh
    runs before the new layer is drawn, so with only_rendered it would stay
    out of the legend until the next pan.
    """
    page.evaluate("() => window.__deckgl_instances.smap.map.jumpTo({center: [21.1, 55.7], zoom: 6})")
    page.click("#add")  # adds pts-circle-<n> at the map centre
    page.wait_for_function(
        "() => [...document.querySelectorAll('#smap .legend-table tr')]"
        ".some(r => r.innerText.trim().startsWith('pts-circle'))", timeout=10000)
    rows = page.evaluate(_LEGEND_ROWS)
    assert all(r.startswith(("pts-circle", "re-circle", "same-circle")) for r in rows), rows
