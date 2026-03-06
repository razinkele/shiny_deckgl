"""Export mixin for MapWidget — serialization and HTML export."""

from __future__ import annotations

import html as _html_mod
import json
import pathlib
from functools import lru_cache
from importlib import resources as impresources
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import Session


# ---------------------------------------------------------------------------
# Cached resource reader (avoid re-reading on every to_html call)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _read_bundled_resources() -> tuple[str, str]:
    """Read and cache the bundled JS and CSS files."""
    res = impresources.files("shiny_deckgl.resources")
    js_src = (res / "deckgl-init.js").read_text(encoding="utf-8")
    css_src = (res / "styles.css").read_text(encoding="utf-8")
    return js_src, css_src


class ExportMixin:
    """Mixin providing export and serialization methods.

    Methods
    -------
    export_image
        Request a screenshot of the map.
    export_result_input_id
        Shiny input ID for export results.
    has_image_input_id
        Shiny input ID for has_image results.
    to_json
        Serialize map spec to JSON.
    from_json
        Reconstruct MapWidget from JSON.
    to_html
        Export as standalone HTML.
    """

    # These attributes are defined in MapWidget but declared here for type checking
    id: str
    _bare_id: str
    view_state: dict
    style: str
    tooltip: dict | None
    mapbox_api_key: str | None

    async def export_image(
        self,
        session: "Session",
        *,
        format: str = "png",
        quality: float = 0.92,
        request_id: str = "default",
    ) -> None:
        """Request a screenshot of the map.

        The base64-encoded image is returned asynchronously as
        ``input.{id}_export_result()``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        format
            Image format: ``"png"`` (default), ``"jpeg"``, or ``"webp"``.
        quality
            JPEG/WebP quality (0.0–1.0). Ignored for PNG.
        request_id
            Identifier included in the result for request matching.
        """
        await session.send_custom_message("deck_export_image", {
            "id": self.id,
            "format": format,
            "quality": quality,
            "requestId": request_id,
        })

    @property
    def export_result_input_id(self) -> str:
        """Shiny input for map export results.

        Returns ``{requestId: str, dataUrl: str, width: int, height: int}``.
        """
        return f"{self._bare_id}_export_result"

    @property
    def has_image_input_id(self) -> str:
        """Shiny input for :meth:`has_image` results.

        Returns ``{imageId: str, exists: bool}``.
        """
        return f"{self._bare_id}_has_image"

    def to_json(self, layers: list[dict], effects: list[dict] | None = None) -> str:
        """Serialize the map spec (view state, style, layers, effects) to JSON.

        Parameters
        ----------
        layers
            List of layer dicts produced by ``layer()`` / ``*_layer()``
            helpers.
        effects
            Optional list of effects dicts.

        Returns
        -------
        str
            A JSON string with keys ``id``, ``viewState``, ``style``,
            ``tooltip``, ``layers``, and optionally ``effects``.
        """
        spec: dict = {
            "id": self.id,
            "viewState": self.view_state,
            "style": self.style,
            "layers": layers,
        }
        if self.tooltip is not None:
            spec["tooltip"] = self.tooltip
        if self.mapbox_api_key is not None:
            spec["mapboxApiKey"] = self.mapbox_api_key
        if effects:
            spec["effects"] = effects
        return json.dumps(spec, indent=2)

    @classmethod
    def from_json(cls, spec_json: str) -> tuple[Any, list[dict]]:
        """Reconstruct a ``MapWidget`` and layer list from a JSON spec.

        Parameters
        ----------
        spec_json
            JSON string previously produced by ``to_json()``.

        Returns
        -------
        tuple[MapWidget, list[dict]]
            ``(widget, layers)`` ready for ``widget.update(session, layers)``.
        """
        from ..colors import CARTO_POSITRON

        spec = json.loads(spec_json)
        # Mixin expects cls to be MapWidget (not ExportMixin) at runtime
        widget = cls(  # type: ignore[call-arg]
            id=spec["id"],
            view_state=spec.get("viewState"),
            style=spec.get("style", CARTO_POSITRON),
            tooltip=spec.get("tooltip"),
            mapbox_api_key=spec.get("mapboxApiKey"),
        )
        layers = spec.get("layers", [])
        return widget, layers

    def to_html(
        self,
        layers: list[dict],
        path: str | pathlib.Path | None = None,
        effects: list[dict] | None = None,
        title: str = "shiny_deckgl Map",
    ) -> str:
        """Export the map as a standalone HTML file.

        The HTML file embeds CDN links for deck.gl and MapLibre, inlines
        the layer data, and can be opened in any browser without Shiny.

        Parameters
        ----------
        layers
            List of layer dicts.
        path
            Optional file path to write.  If ``None`` the HTML string is
            returned but not written to disk.
        effects
            Optional list of effects dicts.
        title
            HTML ``<title>`` content.

        Returns
        -------
        str
            The full HTML document.
        """
        from .._cdn import (
            DECKGL_JS,
            DECKGL_WIDGETS_JS,
            DECKGL_WIDGETS_CSS,
            MAPLIBRE_JS,
            MAPLIBRE_CSS,
            MAPBOX_DRAW_JS,
            MAPBOX_DRAW_CSS,
            MAPLIBRE_LEGEND_JS,
            MAPLIBRE_LEGEND_CSS,
            MAPLIBRE_OPACITY_JS,
            MAPLIBRE_OPACITY_CSS,
        )

        js_src, css_src = _read_bundled_resources()

        vs = self.view_state
        tooltip_attr = ""
        if self.tooltip is not None:
            tooltip_json = json.dumps(self.tooltip)
            tooltip_attr = f' data-tooltip="{_html_mod.escape(tooltip_json, quote=True)}"'

        mapbox_attr = ""
        if self.mapbox_api_key:
            # Escape the API key to prevent XSS in HTML attribute context
            escaped_key = _html_mod.escape(self.mapbox_api_key, quote=True)
            mapbox_attr = f' data-mapbox-api-key="{escaped_key}"'

        layers_json = json.dumps(layers, indent=2)
        effects_json = json.dumps(effects or [], indent=2)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<script src="{DECKGL_JS}"></script>
<script src="{DECKGL_WIDGETS_JS}"></script>
<link rel="stylesheet" href="{DECKGL_WIDGETS_CSS}"/>
<script src="{MAPLIBRE_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_CSS}"/>
<script src="{MAPBOX_DRAW_JS}"></script>
<link rel="stylesheet" href="{MAPBOX_DRAW_CSS}"/>
<script src="{MAPLIBRE_LEGEND_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_LEGEND_CSS}"/>
<script src="{MAPLIBRE_OPACITY_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_OPACITY_CSS}"/>
<style>{css_src}</style>
</head>
<body>
<div id="{self.id}" class="deckgl-map"
     style="width:100%;height:100vh;"
     data-initial-longitude="{vs.get('longitude', 0)}"
     data-initial-latitude="{vs.get('latitude', 0)}"
     data-initial-zoom="{vs.get('zoom', 1)}"
     data-initial-pitch="{vs.get('pitch', 0)}"
     data-initial-bearing="{vs.get('bearing', 0)}"
     data-initial-min-zoom="{vs.get('minZoom', 0)}"
     data-initial-max-zoom="{vs.get('maxZoom', 24)}"
     data-style="{_html_mod.escape(self.style)}"
     {tooltip_attr}{mapbox_attr}></div>
<script>
// Shim: standalone pages have no Shiny runtime
if (typeof Shiny === 'undefined') {{
  window.Shiny = {{
    setInputValue: function() {{}},
    addCustomMessageHandler: function() {{}}
  }};
}}
</script>
<script>{js_src}</script>
<script>
(function() {{
  var initMap = window.__deckgl_initMap;
  var instances = window.__deckgl_instances;
  var buildDeckLayers = window.__deckgl_buildDeckLayers;
  var buildEffects = window.__deckgl_buildEffects;

  // Trigger init manually (no shiny:connected event in standalone mode)
  document.querySelectorAll('.deckgl-map').forEach(initMap);

  // Push layers & effects into the already-initialised overlay
  var layersData = {layers_json};
  var effectsData = {effects_json};

  Object.keys(instances).forEach(function(mapId) {{
    var inst = instances[mapId];
    var deckLayers = buildDeckLayers(
      structuredClone(layersData), mapId, inst.tooltipConfig
    );
    var overlayProps = {{ layers: deckLayers }};
    var effects = buildEffects(effectsData);
    if (effects) overlayProps.effects = effects;
    inst.map.on('load', function() {{
      inst.overlay.setProps(overlayProps);
    }});
  }});
}})();
</script>
</body>
</html>"""

        if path is not None:
            p = pathlib.Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html, encoding="utf-8")
        return html
