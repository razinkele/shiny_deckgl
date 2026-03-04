"""Comprehensive shiny_deckgl demo - showcases every feature of the library.

Run with:
    shiny run shiny_deckgl.app:app --port 19876

Tabs (10):
  1. deck.gl Layers    - all 24 typed layer helpers with Baltic Sea sample
                          data, toggle each on/off, basemap + navigation
  2. MapLibre Controls  - basemap switching, navigation, geolocate,
                          globe, terrain, legend, opacity controls,
                          GeoJSON clustering, cooperative gestures
  3. Events & Tooltips  - live click/hover/viewport readback, drag marker,
                          dynamic tooltip customisation
  4. Colour Scales      - palette swatches, color_range, color_bins,
                          color_quantiles, interactive colour-mapped
                          bathymetry columns / scatter / heatmap
  5. Advanced           - 3-D column map with lighting, binary transport,
                          DataFilterExtension, BrushingExtension, transitions
  6. Export             - standalone HTML export, JSON round-trip
  7. Drawing            - MapboxDraw tools (point/line/polygon), markers
                          with popups, spatial query, interaction logging
  8. 3-D Visualisation  - bathymetry columns, fish observations, 3-D arcs,
                          lighting (ambient, point, directional),
                          post-processing (brightness/contrast),
                          camera pitch/bearing
  9. Seal IBM           - Individual-Based Model of Baltic seal movement,
                          animated foraging trips from haul-out colonies,
                          TripsLayer animation, GreatCircleLayer, GridLayer
 10. Widgets Gallery    - Interactive showcase of all 17 deck.gl widgets,
                          layer-widget combinations, preset bundles

Module Organization (v1.4.0+):
  - _app_widgets.py: MapWidget instances for each tab
  - _app_ui.py: UI building function (build_ui)
  - _app_server.py: Server logic function (server)
  - app.py: Entry point with lazy App construction
"""

from __future__ import annotations

from typing import Any

# Re-export widget instances for backward compatibility
from ._app_widgets import (
    gallery_widget,
    maplibre_widget,
    events_widget,
    palette_widget,
    adv_widget,
    draw_widget,
    three_d_widget,
    seal_widget,
    widgets_gallery_widget,
)


def _build_ui():
    """Build the UI - delegates to _app_ui module."""
    from ._app_ui import build_ui
    return build_ui()


def _get_server():
    """Get the server function - delegates to _app_server module."""
    from ._app_server import server
    return server


# ``app`` is produced lazily via module __getattr__ so importing
# this module doesn't build the whole shiny application unless
# it's actually requested.
_app: Any | None = None


def _build_app():
    from shiny import App
    return App(_build_ui(), _get_server())


def __getattr__(name: str) -> Any:  # module-level lazy attribute
    if name == "app":
        global _app
        if _app is None:
            _app = _build_app()
        return _app
    raise AttributeError(name)


__all__ = [
    "app",
    # Widget instances (backward compatibility)
    "gallery_widget",
    "maplibre_widget",
    "events_widget",
    "palette_widget",
    "adv_widget",
    "draw_widget",
    "three_d_widget",
    "seal_widget",
    "widgets_gallery_widget",
]
