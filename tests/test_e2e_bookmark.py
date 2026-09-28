"""Bookmarking end to end: move the map, hide a layer, bookmark, reopen the URL.

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

PORT = 18781

_READY = ("() => window.__deckgl_instances && window.__deckgl_instances.bmap"
          " && window.__deckgl_instances.bmap.overlay._deck.props.layers.length === 2")
_STATE = """() => { const i = window.__deckgl_instances.bmap; const c = i.map.getCenter();
  const b = i.overlay._deck.props.layers.find(l => l.id === 'buoys');
  return { lng: c.lng, lat: c.lat, zoom: i.map.getZoom(), buoys: b.props.visible !== false }; }"""


def test_bookmark_restores_camera_and_hidden_layer():
    with running_app("bookmark_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#bmap .maplibregl-canvas") as pg:
            pg.wait_for_function(_READY, timeout=30000)
            pg.evaluate("() => window.__deckgl_instances.bmap.map.jumpTo({center: [24.5, 58.2], zoom: 7.25})")
            pg.wait_for_function("() => Math.abs(window.__deckgl_instances.bmap.map.getZoom() - 7.25) < 0.01", timeout=5000)
            pg.click("#hide")
            pg.wait_for_function(f"() => ({_STATE})().buoys === false", timeout=5000)
            pg.wait_for_timeout(500)                     # let the moveend view_state input land
            pg.click("#save")
            pg.wait_for_function("() => document.getElementById('url').innerText.includes('_state_id_=')"
                                 " || document.getElementById('url').innerText.includes('_inputs_')", timeout=10000)
            url = pg.inner_text("#url")
            assert "bmap_view_state" in url and "bmap_click" not in url
            saved = pg.evaluate(_STATE)

            # A fresh session at the bookmark URL (same page: a new page in the
            # implicit context is not allowed by Playwright).
            pg.goto(url)
            pg.wait_for_selector("#bmap .maplibregl-canvas", timeout=30000)
            pg.wait_for_function(_READY, timeout=30000)
            pg.wait_for_function(f"() => Math.abs(({_STATE})().zoom - 7.25) < 0.05", timeout=15000)
            pg.wait_for_function(f"() => ({_STATE})().buoys === false", timeout=10000)
            restored = pg.evaluate(_STATE)
            assert abs(restored["lng"] - saved["lng"]) < 0.01 and abs(restored["lat"] - saved["lat"]) < 0.01
