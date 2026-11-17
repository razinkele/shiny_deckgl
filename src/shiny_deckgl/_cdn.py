"""CDN URL constants — single source of truth for all external assets."""

DECKGL_VERSION = "9.4.1"
# Served pages and standalone to_html() exports both use this. Exports used to
# stay on MapLibre 5: before 6.17, MapLibre 6 started its tile worker as a
# module worker from a blob URL, which dies on a file:// page (opaque origin),
# so the basemap of an export opened from disk silently never loaded. 6.17
# starts a classic worker instead (maplibre-gl-js#8912); verified loading tiles
# from file:// in Chromium and Firefox, and tests/test_maplibre_v6.py guards it.
MAPLIBRE_VERSION = "6.19.0"
MAPBOX_DRAW_VERSION = "1.5.2"
MAPLIBRE_LEGEND_VERSION = "2.0.7"
MAPLIBRE_OPACITY_VERSION = "1.8.0"
H3_JS_VERSION = "4.5.0"
# PostProcessEffect shader modules. deck.gl's bundle has none, and neither
# whole-package build works beside it (the UMD dist.min.js ships luma.gl core
# instead of the effects; the ESM entry pulls in a second @luma.gl/core, which
# throws). The client import()s single self-contained module files from here.
LUMA_EFFECTS_VERSION = "9.4.2"

DECKGL_JS = f"https://cdn.jsdelivr.net/npm/deck.gl@{DECKGL_VERSION}/dist.min.js"
H3_JS = f"https://cdn.jsdelivr.net/npm/h3-js@{H3_JS_VERSION}/dist/h3-js.umd.js"
LUMA_EFFECTS_BASE = (
    f"https://cdn.jsdelivr.net/npm/@luma.gl/effects@{LUMA_EFFECTS_VERSION}"
    "/dist/passes/postprocessing/"
)
DECKGL_WIDGETS_JS = f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist.min.js"
DECKGL_WIDGETS_CSS = f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist/stylesheet.css"
# MapLibre GL JS 6 is ESM-only: the UMD/IIFE build (maplibre-gl.js) and the
# CSP build were both dropped, so this is an ES module URL, loaded at runtime
# by deckgl-init.js via dynamic import() rather than a <script src> tag.
MAPLIBRE_JS = f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.mjs"
MAPLIBRE_CSS = f"https://cdn.jsdelivr.net/npm/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.css"
MAPBOX_DRAW_JS = f"https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@{MAPBOX_DRAW_VERSION}/dist/mapbox-gl-draw.js"
MAPBOX_DRAW_CSS = f"https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@{MAPBOX_DRAW_VERSION}/dist/mapbox-gl-draw.css"

# Third-party MapLibre plugin CDN URLs
MAPLIBRE_LEGEND_JS = f"https://unpkg.com/@watergis/maplibre-gl-legend@{MAPLIBRE_LEGEND_VERSION}/dist/maplibre-gl-legend.umd.js"
MAPLIBRE_LEGEND_CSS = f"https://unpkg.com/@watergis/maplibre-gl-legend@{MAPLIBRE_LEGEND_VERSION}/dist/maplibre-gl-legend.css"
MAPLIBRE_OPACITY_JS = f"https://cdn.jsdelivr.net/npm/maplibre-gl-opacity@{MAPLIBRE_OPACITY_VERSION}/build/maplibre-gl-opacity.umd.js"
MAPLIBRE_OPACITY_CSS = f"https://cdn.jsdelivr.net/npm/maplibre-gl-opacity@{MAPLIBRE_OPACITY_VERSION}/build/maplibre-gl-opacity.css"

# MapLibre's module URL is published as an inert JSON data block rather than an
# inline module script: a <script type="application/json"> body is never
# executed, so a strict script-src Content-Security-Policy allows it without
# 'unsafe-inline'. deckgl-init.js reads this block and import()s the URLs
# (MapLibre at start-up, a luma.gl effect module when an effect needs one).
CDN_CONFIG_JSON = (
    '<script type="application/json" id="shiny-deckgl-cdn">'
    f'{{"maplibre": "{MAPLIBRE_JS}", "lumaEffects": "{LUMA_EFFECTS_BASE}"}}'
    '</script>'
)

CDN_HEAD_FRAGMENT = (
    f'<script src="{H3_JS}"></script>\n'
    f'<script src="{DECKGL_JS}"></script>\n'
    f'<script src="{DECKGL_WIDGETS_JS}"></script>\n'
    f'<link rel="stylesheet" href="{DECKGL_WIDGETS_CSS}"/>\n'
    f'{CDN_CONFIG_JSON}\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_CSS}"/>\n'
    f'<script src="{MAPBOX_DRAW_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPBOX_DRAW_CSS}"/>\n'
    f'<script src="{MAPLIBRE_LEGEND_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_LEGEND_CSS}"/>\n'
    f'<script src="{MAPLIBRE_OPACITY_JS}"></script>\n'
    f'<link rel="stylesheet" href="{MAPLIBRE_OPACITY_CSS}"/>'
)
