"""MapboxDraw's own style layers load under MapLibre 6.

mapbox-gl-draw 1.5.1's default theme wrote ``line-dasharray`` arrays inside a
``case`` expression without ``["literal", ...]``. MapLibre 6 rejects that, so
enabling drawing logged two style errors and the draw line layers were never
added. 1.5.2 wraps them. Needs chromium and network.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18784


def test_draw_line_layers_are_added_without_style_errors():
    with running_app("draw_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#dmap") as pg:
            pg.wait_for_function(
                "() => { const i = window.__deckgl_instances && window.__deckgl_instances.dmap;"
                " const s = i && i.map && i.map.getStyle();"
                " return !!(s && s.layers && s.layers.some(l => l.id.startsWith('gl-draw'))); }",
                timeout=30000)
            pg.wait_for_timeout(1000)
            draw_ids = pg.evaluate(
                "() => window.__deckgl_instances.dmap.map.getStyle().layers"
                ".map(l => l.id).filter(id => id.startsWith('gl-draw'))")
            assert any(i.startswith("gl-draw-lines") for i in draw_ids), draw_ids
            errors = [t for t in pg.console_log if "line-dasharray" in t]
            assert not errors, errors
