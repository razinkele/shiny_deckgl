"""CDN URL constants — single source of truth for all external assets."""

DECKGL_VERSION = "9.2.10"
MAPLIBRE_VERSION = "5.3.1"
MAPBOX_DRAW_VERSION = "1.4.3"

DECKGL_JS = f"https://cdn.jsdelivr.net/npm/deck.gl@{DECKGL_VERSION}/dist.min.js"
DECKGL_WIDGETS_JS = f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist.min.js"
DECKGL_WIDGETS_CSS = f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist/stylesheet.css"
MAPLIBRE_JS = f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.js"
MAPLIBRE_CSS = f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.css"
MAPBOX_DRAW_JS = f"https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@{MAPBOX_DRAW_VERSION}/dist/mapbox-gl-draw.js"
MAPBOX_DRAW_CSS = f"https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@{MAPBOX_DRAW_VERSION}/dist/mapbox-gl-draw.css"

CDN_HEAD_FRAGMENT = (
    f'<script src="{DECKGL_JS}"></script>\n'
    f'<script src="{DECKGL_WIDGETS_JS}"></script>\n'
    f'<link rel="stylesheet" href="{DECKGL_WIDGETS_CSS}"/>\n'
    f'<script src="{MAPLIBRE_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_CSS}"/>\n'
    f'<script src="{MAPBOX_DRAW_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPBOX_DRAW_CSS}"/>'
)
