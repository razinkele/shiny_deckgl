"""Map widget instances for the demo application.

Each tab that requires a map has its own MapWidget instance defined here.
These are imported by both _app_ui.py and _app_server.py.
"""

from __future__ import annotations

from .map_widget import MapWidget, CARTO_POSITRON
from ._demo_data import (
    BALTIC_VIEW,
    BALTIC_VIEW_3D,
    TOOLTIP_STYLE,
    DEFAULT_TOOLTIP_HTML,
)

# ---------------------------------------------------------------------------
# Map widget instances — one per tab that needs a map
# ---------------------------------------------------------------------------

# Tab 1 — deck.gl Layers / Layer Gallery (all 24 layer helpers)
gallery_widget = MapWidget(
    "gallery_map",
    tooltip={
        "html": (
            "<b>{name}</b><br/>"
            "Type: {layerType}"
        ),
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
    controls=[],
)

# Tab 2 — MapLibre Controls
maplibre_widget = MapWidget(
    "maplibre_map",
    tooltip={"html": "<b>{name}</b><br/>{country}", "style": TOOLTIP_STYLE},
    view_state=BALTIC_VIEW,
    controls=[],
)

# Tab 3 — Events & Tooltips
events_widget = MapWidget(
    "events_map",
    tooltip={"html": DEFAULT_TOOLTIP_HTML, "style": TOOLTIP_STYLE},
    view_state=BALTIC_VIEW,
)

# Tab 4 — Colour Scales
palette_widget = MapWidget(
    "palette_map",
    tooltip={
        "html": (
            "<b>{name}</b><br/>"
            "Depth: {depth_m} m<br/>"
            "Bin: {bin_label}"
        ),
        "style": TOOLTIP_STYLE,
    },
    view_state={**BALTIC_VIEW, "pitch": 45, "bearing": -15},
)

# Tab 5 — Advanced (3-D columns)
adv_widget = MapWidget(
    "adv_map",
    tooltip={
        "html": "<b>{name}</b><br/>Cargo: {cargo_mt} Mt",
        "style": {**TOOLTIP_STYLE, "borderLeft": "3px solid #14919b"},
    },
    view_state={**BALTIC_VIEW, "pitch": 45},
)

# Tab 7 — Drawing Tools
draw_widget = MapWidget(
    "draw_map",
    tooltip={"html": "<b>{name}</b>", "style": TOOLTIP_STYLE},
    view_state=BALTIC_VIEW,
)

# Tab 8 — 3D Visualization
three_d_widget = MapWidget(
    "three_d_map",
    tooltip={
        "html": (
            "<b>{name}</b><br/>"
            "Depth: {depth_m} m<br/>"
            "Species: {species}"
        ),
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW_3D,
)

# Tab 9 — Seal IBM (Individual-Based Model)
seal_widget = MapWidget(
    "seal_map",
    tooltip={
        "html": (
            "<b>{name}</b><br/>"
            "Species: {species}<br/>"
            "Haul-out: {haulout}"
        ),
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
    animate=True,
)

# Tab 10 — Widgets Gallery
widgets_gallery_widget = MapWidget(
    "widgets_gallery_map",
    tooltip={
        "html": "<b>{name}</b><br/>Cargo: {cargo_mt} Mt",
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
    controls=[],
)

# Tab 11 — Time & Space (viewport-aware + timeline)
timespace_widget = MapWidget(
    "timespace_map",
    tooltip={
        "html": (
            "<b>{name}</b><br/>"
            "Temp: {temperature_c}\u00b0C<br/>"
            "Month: {month_label}"
        ),
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
)

# Tab 12 — HexSim Fish (hex grid + animated salmon trips)
hexfish_widget = MapWidget(
    "hexfish_map",
    view_state={"longitude": -121.0, "latitude": 46.3, "zoom": 8, "pitch": 0},
    style=CARTO_POSITRON,
    animate=True,
)

__all__ = [
    "gallery_widget",
    "maplibre_widget",
    "events_widget",
    "palette_widget",
    "adv_widget",
    "draw_widget",
    "three_d_widget",
    "seal_widget",
    "widgets_gallery_widget",
    "timespace_widget",
    "hexfish_widget",
]
