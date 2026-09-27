"""A real click on a layer-legend checkbox hides the layer and reaches the server.

MapLibreOverlay mounts deck.gl's widget container inside MapLibre's control
corner, which MapLibre styles `pointer-events: none`; deck.gl's own widgets
opt back in through their stylesheet, and the custom legend has to as well,
or every click falls through to the map canvas. The Node legend tests drive
the widget through a fake DOM, so only a real pointer click catches this.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18778

_VISIBLE = """(id) => {
  const i = window.__deckgl_instances && window.__deckgl_instances.lmap;
  const l = i && i.overlay._deck.props.layers.find(l => l.id === id);
  return l ? l.props.visible !== false : null;
}"""


@pytest.fixture(scope="module")
def page():
    with running_app("legend_click_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#lmap .maplibregl-canvas") as pg:
            pg.wait_for_selector("#lmap .deck-legend-cb", timeout=30000)
            pg.wait_for_function(f"() => ({_VISIBLE})('buoys') === true", timeout=15000)
            yield pg


def test_legend_checkbox_receives_the_click(page):
    cb = page.locator("#lmap .deck-legend-row", has_text="buoys").locator("input.deck-legend-cb")
    assert cb.is_checked()
    cb.click(timeout=5000)          # times out if the map canvas intercepts the pointer
    assert not cb.is_checked()


def test_unticked_layer_is_hidden_and_reported(page):
    page.wait_for_function(f"() => ({_VISIBLE})('buoys') === false", timeout=5000)
    assert page.evaluate(f"() => ({_VISIBLE})('ports')") is True
    page.wait_for_function("() => document.getElementById('last').innerText === 'buoys:False'", timeout=5000)


def test_ticking_again_shows_the_layer(page):
    page.locator("#lmap .deck-legend-row", has_text="buoys").locator("input.deck-legend-cb").click(timeout=5000)
    page.wait_for_function(f"() => ({_VISIBLE})('buoys') === true", timeout=5000)
    page.wait_for_function("() => document.getElementById('last').innerText === 'buoys:True'", timeout=5000)
