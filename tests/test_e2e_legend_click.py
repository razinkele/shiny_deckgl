"""A real click on a layer-legend checkbox hides the layer and reaches the server.

MapLibreOverlay mounts deck.gl's widget container inside MapLibre's control
corner, which MapLibre styles `pointer-events: none`; deck.gl's own widgets
opt back in through their stylesheet, and the custom legend has to as well,
or every click falls through to the map canvas. The Node legend tests drive
the widget through a fake DOM, so only a real pointer click catches this.

Written with shiny_deckgl.testing.MapWidgetController (v1.13.0).
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

from shiny_deckgl.testing import MapWidgetController  # noqa: E402

PORT = 18778


@pytest.fixture(scope="module")
def m():
    with running_app("legend_click_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#lmap .maplibregl-canvas") as pg:
            ctl = MapWidgetController(pg, "lmap")
            ctl.wait_ready()
            pg.wait_for_selector("#lmap .deck-legend-cb", timeout=30000)
            ctl.expect_layers(["ports", "buoys"])
            ctl.expect_layer_visible("buoys", True)
            yield ctl


def test_legend_checkbox_receives_the_click(m):
    cb = m.page.locator("#lmap .deck-legend-row", has_text="buoys").locator("input.deck-legend-cb")
    assert cb.is_checked()
    m.click_legend("buoys")          # times out if the map canvas intercepts the pointer
    m.expect_layer_visible("buoys", False)


def test_unticked_layer_is_hidden_and_reported(m):
    assert m.layer_visible("ports") is True
    m.page.wait_for_function("() => document.getElementById('last').innerText === 'buoys:False'", timeout=5000)


def test_ticking_again_shows_the_layer(m):
    m.click_legend("buoys")
    m.expect_layer_visible("buoys", True)
    m.page.wait_for_function("() => document.getElementById('last').innerText === 'buoys:True'", timeout=5000)
