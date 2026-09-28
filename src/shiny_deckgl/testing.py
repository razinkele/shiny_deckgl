"""Playwright helpers for testing apps that use :class:`~shiny_deckgl.MapWidget`.

Built on Shiny's own controller base (``shiny.playwright.controller``), so a
:class:`MapWidgetController` sits next to ``controller.InputSlider`` and
friends in a test::

    from shiny.playwright import controller
    from shiny.run import ShinyAppProc
    from shiny_deckgl.testing import MapWidgetController

    def test_layers(page: Page, local_app: ShinyAppProc):
        page.goto(local_app.url)
        m = MapWidgetController(page, "gallery_map")
        m.wait_ready()
        m.expect_layers(["ports", "routes"])
        controller.InputSwitch(page, "show_routes").set(False)
        m.expect_layer_visible("routes", False)

The controller reads the runtime's ``window.__deckgl_instances[id]`` record
(``map``, ``overlay``, ``lastLayers``), which is a supported test surface.
Playwright is imported lazily, so importing this module needs neither it nor
a browser.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from playwright.sync_api import Page

__all__ = ["MapWidgetController"]

try:  # Shiny >= 1.0 ships the controller base classes
    from shiny.playwright.controller._base import UiBase as _UiBase
except Exception:  # pragma: no cover - older Shiny, or playwright missing
    class _UiBase:  # type: ignore[no-redef]
        def __init__(self, page: Any, *, id: str, loc: Any) -> None:
            self.page = page
            self.id = id
            self.loc = page.locator(loc) if isinstance(loc, str) else loc


def _widget_css_class(class_name: str) -> str:
    """``"ResetViewWidget"`` -> ``"deck-widget-reset-view"`` (deck.gl's widget className).

    The minified bundle mangles ``constructor.name``, so widgets are matched by
    the stable ``className`` every deck.gl widget carries.
    """
    base = re.sub(r"Widget$", "", class_name.lstrip("_"))
    return "deck-widget-" + re.sub(r"(?<!^)(?=[A-Z])", "-", base).lower()


def _js_instance(map_id: str) -> str:
    return f"window.__deckgl_instances && window.__deckgl_instances[{json.dumps(map_id)}]"


class MapWidgetController(_UiBase):
    """Drive and assert on a :class:`~shiny_deckgl.MapWidget` in a Playwright page.

    Parameters
    ----------
    page
        The Playwright ``Page``.
    id
        The widget id (``MapWidget("gallery_map")`` → ``"gallery_map"``); the
        module-resolved DOM id when the widget lives in a Shiny module.
    """

    def __init__(self, page: "Page", id: str) -> None:
        super().__init__(page, id=id, loc=f"#{id}")

    # -- readiness ----------------------------------------------------------

    def wait_ready(self, *, timeout: float = 30000, layers: bool = True) -> None:
        """Wait until the map runtime exists for this id (and, by default,
        until the first ``update()`` has delivered its layers)."""
        inst = _js_instance(self.id)
        self.page.wait_for_selector(f"#{self.id} .maplibregl-canvas", timeout=timeout)
        cond = f"() => !!({inst}) && !!({inst}).map"
        if layers:
            cond = f"() => !!({inst}) && ({inst}).lastLayers && ({inst}).lastLayers.length > 0"
        self.page.wait_for_function(cond, timeout=timeout, polling=100)

    # -- reads ---------------------------------------------------------------

    def _eval(self, body: str) -> Any:
        return self.page.evaluate(f"() => {{ const i = {_js_instance(self.id)}; if (!i) return null; {body} }}")

    def layer_ids(self) -> list[str]:
        """Ids of the layers the last update/patch left on the map (in order)."""
        return self._eval("return i.lastLayers.map(l => l.id);") or []

    def layer(self, layer_id: str) -> dict | None:
        """The raw (JSON) props of one layer as the runtime holds them, or ``None``."""
        return self._eval(f"const l = i.lastLayers.find(l => l.id === {json.dumps(layer_id)});"
                          " if (!l) return null; const o = {}; for (const k in l) if (k !== 'data') o[k] = l[k];"
                          " o.data_length = Array.isArray(l.data) ? l.data.length : null; return o;")

    def layer_visible(self, layer_id: str) -> bool | None:
        """Whether deck.gl currently draws the layer (``None`` if absent)."""
        return self._eval(f"const l = i.overlay._deck.props.layers.find(l => l.id === {json.dumps(layer_id)});"
                          " return l ? l.props.visible !== false : null;")

    def view_state(self) -> dict:
        """``{longitude, latitude, zoom, pitch, bearing}`` from the MapLibre map."""
        return self._eval("const c = i.map.getCenter(); return {longitude: c.lng, latitude: c.lat,"
                          " zoom: i.map.getZoom(), pitch: i.map.getPitch(), bearing: i.map.getBearing()};")

    def widget_classes(self) -> list[str]:
        """The ``className`` of every deck.gl widget on the map, e.g.
        ``["deck-widget-zoom", "deck-widget-timeline"]``."""
        return self._eval("return (i.overlay._deck.props.widgets || []).map(w => w.className || w.constructor.name);") or []

    def style_url(self) -> str | None:
        """The basemap style URL the runtime last applied."""
        return self._eval("return i.currentStyle || null;")

    # -- actions --------------------------------------------------------------

    def click_legend(self, layer_id: str, *, timeout: float = 5000) -> None:
        """Click the layer-legend checkbox for *layer_id* (``layer_legend_widget``)."""
        row = self.page.locator(f"#{self.id} .deck-legend-row", has_text=layer_id)
        row.locator("input.deck-legend-cb").click(timeout=timeout)

    def jump_to(self, longitude: float, latitude: float, zoom: float | None = None) -> None:
        """Move the camera client-side (a ``moveend`` follows, so ``view_state`` inputs fire)."""
        opts = {"center": [longitude, latitude]}
        if zoom is not None:
            opts["zoom"] = zoom
        self._eval(f"i.map.jumpTo({json.dumps(opts)});")

    # -- expectations (poll until true or fail) ---------------------------------

    def _expect(self, predicate_js: str, message: str, timeout: float) -> None:
        self.page.wait_for_function(
            f"() => {{ const i = {_js_instance(self.id)}; if (!i) return false; {predicate_js} }}",
            timeout=timeout, polling=100)

    def expect_layers(self, ids: list[str], *, timeout: float = 5000) -> None:
        """Expect exactly these layer ids (order-insensitive)."""
        want = json.dumps(sorted(ids), separators=(",", ":"))   # JSON.stringify spacing
        self._expect(f"return JSON.stringify(i.lastLayers.map(l => l.id).sort()) === {json.dumps(want)};",
                     f"layers != {ids}", timeout)

    def expect_layer_visible(self, layer_id: str, visible: bool = True, *, timeout: float = 5000) -> None:
        """Expect deck.gl to draw (or not draw) the layer."""
        self._expect(f"const l = i.overlay._deck.props.layers.find(l => l.id === {json.dumps(layer_id)});"
                     f" return !!l && (l.props.visible !== false) === {json.dumps(bool(visible))};",
                     f"{layer_id} visible != {visible}", timeout)

    def expect_widget(self, class_name: str, *, timeout: float = 5000) -> None:
        """Expect a deck.gl widget of this class on the map -- ``"ZoomWidget"``,
        ``"_TimelineWidget"`` or its css class ``"deck-widget-zoom"``."""
        css = class_name if class_name.startswith("deck-") else _widget_css_class(class_name)
        self._expect(f"return (i.overlay._deck.props.widgets || []).some(w => w.className === {json.dumps(css)}"
                     f" || w.constructor.name === {json.dumps(class_name)});", f"no {class_name}", timeout)

    def expect_zoom(self, zoom: float, *, tolerance: float = 0.05, timeout: float = 5000) -> None:
        """Expect the camera zoom to be within *tolerance* of *zoom*."""
        self._expect(f"return Math.abs(i.map.getZoom() - {zoom}) <= {tolerance};", f"zoom != {zoom}", timeout)
