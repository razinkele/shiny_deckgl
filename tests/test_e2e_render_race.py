"""A change made while an update is still preloading must survive it (J5).

deck_update rasterises SVG icon atlases asynchronously, then rendered the
layer array it had captured at the start. A visibility change (or legend
toggle, or partial update) rendered in the meantime was painted over when the
preload finished: the screen showed the old state while lastLayers held the
new one.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18770

_STATE = """() => {
  const i = window.__deckgl_instances && window.__deckgl_instances.race;
  if (!i) return null;
  const dk = i.overlay._deck || i.overlay.deck;
  const shown = {};
  (dk && dk.props.layers || []).forEach(l => { shown[l.id] = l.props.visible; });
  const cached = {};
  (i.lastLayers || []).forEach(l => { cached[l.id] = l.visible !== false; });
  return { shown, cached };
}"""


def test_visibility_change_during_atlas_preload_is_kept():
    with running_app("render_race_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#race .maplibregl-canvas") as pg:
            pg.wait_for_function(
                "() => { const i = window.__deckgl_instances && window.__deckgl_instances.race;"
                " return !!(i && i.map.loaded()); }", timeout=30000)
            pg.click("#go")
            pg.wait_for_function(
                "() => { const i = window.__deckgl_instances.race; const dk = i.overlay._deck;"
                " return (dk.props.layers || []).some(l => l.id === 'icons'); }", timeout=15000)
            pg.wait_for_timeout(1000)
            state = pg.evaluate(_STATE)
            assert state["cached"] == {"pts": False, "icons": True}
            assert state["shown"]["pts"] is False, f"on screen: {state['shown']}"
