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


def test_the_draw_buttons_can_be_clicked():
    """mapbox-gl-draw names its control for Mapbox GL (``mapboxgl-ctrl``).

    MapLibre styles its own class (``maplibregl-ctrl``) and lets the pointer
    reach only that one: the control corner is ``pointer-events: none``. With
    Mapbox's names the draw buttons were bare and every click on them fell
    through to the map.
    """
    with running_app("draw_app", PORT + 1):
        with browser_page(f"http://127.0.0.1:{PORT + 1}/", "#dmap") as pg:
            pg.wait_for_selector("#dmap .mapbox-gl-draw_polygon", timeout=30000)
            pg.wait_for_timeout(500)
            state = pg.evaluate(
                """() => {
                    const b = document.querySelector('#dmap .mapbox-gl-draw_polygon');
                    const r = b.getBoundingClientRect();
                    const top = document.elementFromPoint(
                        r.x + r.width / 2, r.y + r.height / 2);
                    const group = b.parentElement;
                    return {
                        onTop: top === b,
                        group: group.className,
                        background: getComputedStyle(group).backgroundColor,
                    };
                }""")
            assert state["onTop"], state
            assert "maplibregl-ctrl-group" in state["group"], state
            assert state["background"] not in ("rgba(0, 0, 0, 0)", "transparent"), state

            pg.click("#dmap .mapbox-gl-draw_polygon")
            pg.wait_for_function(
                "() => window.__deckgl_instances.dmap.draw.getMode() === 'draw_polygon'",
                timeout=5000)

            # ...and a polygon can then be drawn: three corners, the last
            # one double-clicked.
            box = pg.locator("#dmap").bounding_box()
            corners = [(0.4, 0.4), (0.6, 0.4), (0.5, 0.7)]
            points = [(box["x"] + fx * box["width"], box["y"] + fy * box["height"])
                      for fx, fy in corners]
            for x, y in points[:-1]:
                pg.mouse.click(x, y)
                pg.wait_for_timeout(250)
            pg.mouse.dblclick(*points[-1])
            # draw_polygon adds a draft Polygon as soon as the mode starts, so
            # require the mode to have ended and a closed ring of three corners.
            pg.wait_for_function(
                """() => {
                    const d = window.__deckgl_instances.dmap.draw;
                    if (d.getMode() !== 'simple_select') return false;
                    const f = d.getAll().features;
                    if (f.length !== 1 || f[0].geometry.type !== 'Polygon') return false;
                    const ring = f[0].geometry.coordinates[0];
                    if (!ring || ring.length < 4) return false;
                    const first = ring[0], last = ring[ring.length - 1];
                    if (first[0] !== last[0] || first[1] !== last[1]) return false;
                    const distinct = new Set(ring.slice(0, -1).map(c => c.join(',')));
                    return distinct.size >= 3;
                }""",
                timeout=5000)
