"""CDN URL constants — single source of truth for all external assets."""

DECKGL_VERSION = "9.2.10"
MAPLIBRE_VERSION = "5.3.1"
MAPBOX_DRAW_VERSION = "1.4.3"
MAPLIBRE_LEGEND_VERSION = "2.0.6"
MAPLIBRE_OPACITY_VERSION = "1.8.0"

DECKGL_JS = f"https://cdn.jsdelivr.net/npm/deck.gl@{DECKGL_VERSION}/dist.min.js"
DECKGL_WIDGETS_JS = f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist.min.js"
DECKGL_WIDGETS_CSS = f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist/stylesheet.css"
MAPLIBRE_JS = f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.js"
MAPLIBRE_CSS = f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.css"
MAPBOX_DRAW_JS = f"https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@{MAPBOX_DRAW_VERSION}/dist/mapbox-gl-draw.js"
MAPBOX_DRAW_CSS = f"https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@{MAPBOX_DRAW_VERSION}/dist/mapbox-gl-draw.css"

# Third-party MapLibre plugin CDN URLs
MAPLIBRE_LEGEND_JS = f"https://unpkg.com/@watergis/maplibre-gl-legend@{MAPLIBRE_LEGEND_VERSION}/dist/maplibre-gl-legend.umd.js"
MAPLIBRE_LEGEND_CSS = f"https://unpkg.com/@watergis/maplibre-gl-legend@{MAPLIBRE_LEGEND_VERSION}/dist/maplibre-gl-legend.css"
MAPLIBRE_OPACITY_JS = f"https://cdn.jsdelivr.net/npm/maplibre-gl-opacity@{MAPLIBRE_OPACITY_VERSION}/build/maplibre-gl-opacity.umd.js"
MAPLIBRE_OPACITY_CSS = f"https://cdn.jsdelivr.net/npm/maplibre-gl-opacity@{MAPLIBRE_OPACITY_VERSION}/build/maplibre-gl-opacity.css"

CDN_HEAD_FRAGMENT = (
    f'<script src="{DECKGL_JS}"></script>\n'
    f'<script src="{DECKGL_WIDGETS_JS}"></script>\n'
    f'<link rel="stylesheet" href="{DECKGL_WIDGETS_CSS}"/>\n'
    f'<script src="{MAPLIBRE_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_CSS}"/>\n'
    f'<script src="{MAPBOX_DRAW_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPBOX_DRAW_CSS}"/>\n'
    f'<script src="{MAPLIBRE_LEGEND_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_LEGEND_CSS}"/>\n'
    f'<script src="{MAPLIBRE_OPACITY_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_OPACITY_CSS}"/>'
)
