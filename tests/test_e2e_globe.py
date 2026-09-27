"""The overlay is deck.gl's MapLibre integration, and layers follow globe projection.

MapLibreOverlay is the integration deck.gl 9.4 recommends for MapLibre. The
globe test is a regression guard (MapboxOverlay 9.4 already handled it); the
instanceof test is what changes with the switch.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18776

_LAYER_PRESENT = """() => {
  const i = window.__deckgl_instances && window.__deckgl_instances.gmap;
  return !!(i && i.overlay._deck && i.overlay._deck.props.layers.some(l => l.id === 'pts'));
}"""


@pytest.fixture(scope="module")
def page():
    with running_app("globe_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#gmap .maplibregl-canvas") as pg:
            pg.wait_for_function(_LAYER_PRESENT, timeout=30000)
            yield pg


def test_overlay_is_the_maplibre_integration(page):
    assert page.evaluate("() => typeof deck.MapLibreOverlay === 'function'")
    assert page.evaluate("() => window.__deckgl_instances.gmap.overlay instanceof deck.MapLibreOverlay")


def test_point_stays_on_its_location_in_globe_projection(page):
    page.evaluate("() => window.__deckgl_instances.gmap.map.setProjection({type: 'globe'})")
    page.wait_for_timeout(1500)
    got = page.evaluate("""() => {
      const i = window.__deckgl_instances.gmap;
      const dk = i.overlay._deck;
      const view = dk.getViewports()[0];
      const p = view.project([21.1, 55.7]);
      const info = dk.pickObject({x: p[0], y: p[1], radius: 8});
      return { projection: i.map.getProjection().type, picked: info ? info.layer.id : null };
    }""")
    assert got == {"projection": "globe", "picked": "pts"}
