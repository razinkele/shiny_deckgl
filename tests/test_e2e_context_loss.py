"""A map whose WebGL context the browser drops is rebuilt with its layers.

Chrome keeps at most 16 live WebGL contexts and drops the oldest; with two
per map, a page with many maps sees one go blank (the demo's 3-D tab did).
WEBGL_lose_context lets a test force the loss deterministically.

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

PORT = 18783

_LOSE = """(id) => { const c = document.querySelector('#' + id + ' canvas.maplibregl-canvas');
  const gl = c.getContext('webgl2') || c.getContext('webgl');
  const ext = gl.getExtension('WEBGL_lose_context'); ext.loseContext(); return true; }"""
_LOST = """(id) => { const c = document.querySelector('#' + id + ' canvas.maplibregl-canvas');
  const gl = c && (c.getContext('webgl2') || c.getContext('webgl')); return gl ? gl.isContextLost() : null; }"""


@pytest.fixture(scope="module")
def page():
    with running_app("context_loss_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#amap .maplibregl-canvas") as pg:
            MapWidgetController(pg, "amap").wait_ready()
            yield pg


def test_visible_map_is_rebuilt_with_layers_and_camera(page):
    m = MapWidgetController(page, "amap")
    m.expect_layers(["pts"])
    m.jump_to(23.0, 57.5, 7.5)
    m.expect_zoom(7.5)
    page.evaluate(_LOSE, "amap")
    page.wait_for_function("() => window.__deckgl_instances.amap && window.__deckgl_instances.amap._rebuilds === 1", timeout=20000)
    m.wait_ready()
    m.expect_layers(["pts"])
    m.expect_layer_visible("pts", True)
    m.expect_widget("ZoomWidget")
    m.expect_zoom(7.5)
    assert page.evaluate(_LOST, "amap") is False
    page.wait_for_function("() => document.getElementById('events').innerText.includes('amap:webgl-context-lost')", timeout=5000)


def test_hidden_map_is_rebuilt_when_its_tab_is_shown(page):
    page.click("a.nav-link:has-text('B')")
    mb = MapWidgetController(page, "bmap")
    mb.wait_ready()
    mb.expect_layers(["pts_b"])
    page.click("a.nav-link:has-text('A')")
    page.wait_for_timeout(300)
    page.evaluate(_LOSE, "bmap")                       # lost while hidden
    page.wait_for_function("() => window.__deckgl_instances.bmap && window.__deckgl_instances.bmap._contextLost === true", timeout=5000)
    assert page.evaluate("() => window.__deckgl_instances.bmap._rebuilds || 0") == 0   # not yet: hidden
    page.click("a.nav-link:has-text('B')")
    page.wait_for_function("() => window.__deckgl_instances.bmap && window.__deckgl_instances.bmap._rebuilds === 1", timeout=20000)
    mb.wait_ready()
    mb.expect_layers(["pts_b"])
    assert page.evaluate(_LOST, "bmap") is False
