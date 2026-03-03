"""Comprehensive shiny_deckgl demo — showcases every feature of the library.

Run with:
    shiny run shiny_deckgl.app:app --port 19876

Tabs:
  1. deck.gl Layers   – palettes, color modes, layer visibility,
                         WMS (EMODnet), fly-to / ease-to, drag marker,
                         deck.gl widgets
  2. MapLibre Controls – basemap switching, navigation, geolocate,
                         globe, terrain, legend, opacity controls
  3. Events & Tooltips – live click/hover/viewport readback, drag marker,
                         dynamic tooltip customisation
  4. Colour Scales     – palette swatches, color_bins, color_quantiles
  5. Advanced          – 3-D column map with lighting, binary transport,
                         DataFilterExtension, widget toggles, transitions
  6. Export            – standalone HTML export, JSON round-trip
  7. Drawing           – MapboxDraw tools (point/line/polygon), markers
                         with popups, spatial query, interaction logging
  8. Animation         – TripsLayer animated vessel tracks, GreatCircleLayer,
                         GridLayer, combined overlays with speed/trail controls
  9. v1.0 Features     – BrushingExtension, DataFilterExtension, MapLibre
                         GeoJSON clustering, cooperative gestures
 10. Extensions        – BrushingExtension, DataFilterExtension demos
 11. 3-D Column        – 3-D column map with terrain, lighting, and
                         orthographic/first-person views
 12. Seal IBM          – Individual-Based Model of Baltic seal movement,
                         animated foraging trips from haul-out colonies
 13. Widgets Gallery   – Interactive showcase of all 17 deck.gl widgets,
                         layer-widget combinations, preset bundles
"""

from __future__ import annotations

import json
import os
import random
import tempfile

from shiny import App, reactive, render, Session, ui

from .ui import head_includes
from .components import (
    MapWidget,
    layer,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    wms_layer,
    # v0.7.0 layer helpers
    arc_layer,
    column_layer,
    heatmap_layer,
    path_layer,
    # v0.9.0 layer helpers
    trips_layer,
    great_circle_layer,
    grid_layer,
    hexagon_layer,
    # Color utilities
    color_range,
    color_bins,
    color_quantiles,
    # Binary transport
    encode_binary_attribute,
    # v0.8.0 widgets
    zoom_widget,
    compass_widget,
    fullscreen_widget,
    scale_widget,
    gimbal_widget,
    reset_view_widget,
    screenshot_widget,
    fps_widget,
    loading_widget,
    theme_widget,
    timeline_widget,
    geocoder_widget,
    # Experimental widgets (deck.gl >= 9.2)
    context_menu_widget,
    info_widget,
    splitter_widget,
    stats_widget,
    view_selector_widget,
    # v0.8.0 transitions
    transition,
    # Views
    map_view,
    # MapLibre control helpers
    geolocate_control,
    globe_control,
    terrain_control,
    # Third-party MapLibre plugin controls
    legend_control,
    opacity_control,
    # Custom deck.gl legend
    deck_legend_control,
)

from ._demo_data import (
    PORTS,
    MPA_GEOJSON,
    EMODNET_WMS_URL,
    WMS_LAYER_CHOICES,
    BASEMAP_CHOICES,
    PALETTE_CHOICES,
    BALTIC_VIEW,
    TOOLTIP_STYLE,
    DEFAULT_TOOLTIP_HTML,
    make_arc_data,
    make_heatmap_points,
    make_path_data,
    make_port_data_simple,
    make_port_geojson,
    make_trips_data,
    make_bathymetry_grid,
    make_fish_observations,
    make_3d_arc_data,
    BALTIC_VIEW_3D,
)
from ._demo_data import (
    make_seal_trips,
    make_seal_trips_ibm,
    make_seal_haulout_data,
    make_seal_foraging_areas,
)
from .ibm import ICON_ATLAS, ICON_MAPPING, trips_animation_ui, trips_animation_server
from ._demo_css import MARINE_CSS, sidebar_hint

from .components import CARTO_POSITRON, PALETTE_OCEAN
from .extensions import (
    brushing_extension,
    data_filter_extension,
)
from ._version import __version__ as SHINY_DECKGL_VERSION
from ._cdn import (
    DECKGL_VERSION,
    MAPLIBRE_VERSION,
    MAPBOX_DRAW_VERSION,
    MAPLIBRE_LEGEND_VERSION,
    MAPLIBRE_OPACITY_VERSION,
)


# ---------------------------------------------------------------------------
# About-panel helpers
# ---------------------------------------------------------------------------

def _python_version() -> str:
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _shiny_version() -> str:
    try:
        from importlib.metadata import version
        return version("shiny")
    except Exception:
        return "unknown"


def _about_row(lib: str, ver: str) -> ui.Tag:
    """One <tr> for the About version table."""
    return ui.tags.tr(
        ui.tags.td(
            lib,
            style="padding:3px 12px 3px 0;color:#666;white-space:nowrap;",
        ),
        ui.tags.td(
            ui.tags.code(ver),
            style="padding:3px 0;font-weight:600;",
        ),
    )


# ---------------------------------------------------------------------------
# Map widget instances — one per tab that needs a map
# ---------------------------------------------------------------------------

# Tab 1 — deck.gl Layers (deck.gl widgets, no MapLibre controls)
map_widget = MapWidget(
    "demo_map",
    tooltip={"html": "<b>{name}</b>", "style": TOOLTIP_STYLE},
    view_state=BALTIC_VIEW,
    controls=[],
)

MAP_WIDGETS = [
    zoom_widget(),
    compass_widget(),
    fullscreen_widget(),
    scale_widget(),
]

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

# Tab 8 — Animation (TripsLayer)
anim_widget = MapWidget(
    "anim_map",
    tooltip={
        "html": "<b>{name}</b><br/>Operator: {operator}<br/>Type: {type}",
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
    animate=True,
)

# Tab 9 — v1.0.0 deck.gl Extensions
v1_deck_widget = MapWidget(
    "v1_deck_map",
    tooltip={"html": "<b>{name}</b><br/>Cargo: {cargo_mt} Mt", "style": TOOLTIP_STYLE},
    view_state=BALTIC_VIEW,
    controls=[],
)

# Tab 10 — v1.0.0 MapLibre Features (Clusters, Cooperative Gestures)
v1_ml_widget = MapWidget(
    "v1_ml_map",
    tooltip={"html": "<b>{name}</b><br/>Cargo: {cargo_mt} Mt", "style": TOOLTIP_STYLE},
    view_state=BALTIC_VIEW,
    controls=[],
)

# Tab 11 — 3D Visualization
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

# Tab 13 — Widgets Gallery
widgets_gallery_widget = MapWidget(
    "widgets_gallery_map",
    tooltip={
        "html": "<b>{name}</b><br/>Cargo: {cargo_mt} Mt",
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
    controls=[],
)

# Tab 12 — Seal IBM (Individual-Based Model)
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


# ===========================================================================
# UI layout
# ===========================================================================

app_ui = ui.page_navbar(
    head_includes(),

    # -- Tab 1: deck.gl Layers --------------------------------------------
    ui.nav_panel(
        "\U0001F30A deck.gl Layers",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\u2693 Basemap",
                        ui.input_select(
                            "basemap", "Basemap style",
                            choices=list(BASEMAP_CHOICES.keys()),
                        ),
                    ),
                    ui.accordion_panel(
                        "\u2728 Symbology",
                        ui.input_select(
                            "palette", "Port colour palette",
                            choices=list(PALETTE_CHOICES.keys()),
                            selected="Ocean",
                        ),
                        ui.input_radio_buttons(
                            "color_mode", "Colour mode",
                            choices=[
                                "Equal-width bins",
                                "Quantile bins",
                                "Fixed range",
                            ],
                            selected="Equal-width bins",
                        ),
                    ),
                    ui.accordion_panel(
                        "\u2630 Layers",
                        ui.input_switch("show_ports", "Ports (scatter)",
                                        value=True),
                        ui.input_switch("show_mpa", "Marine Protected Areas",
                                        value=True),
                        ui.input_switch("show_routes", "Shipping routes (arcs)",
                                        value=True),
                        ui.input_switch("show_paths", "Route paths",
                                        value=False),
                        ui.input_select(
                            "wms_layer", "EMODnet WMS overlay",
                            choices=WMS_LAYER_CHOICES,
                            selected="emodnet:mean_atlas_land",
                        ),
                        ui.input_switch("show_heatmap", "Observation heatmap",
                                        value=False),
                    ),
                    ui.accordion_panel(
                        "\u2708 Navigation",
                        ui.input_action_button("fly_klaipeda",
                                               "\u2708 Fly to Klaip\u0117da"),
                        ui.input_action_button("ease_stockholm",
                                               "\u27A1 Ease to Stockholm"),
                        ui.input_action_button("fly_baltic",
                                               "\U0001F30D Reset Baltic view"),
                        ui.input_action_button("place_marker",
                                               "\U0001F4CD Place drag marker"),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CD Drag Marker",
                        ui.output_text_verbatim("drag_info"),
                    ),
                    id="tab1_accordion",
                    open=False,
                    multiple=True,
                ),
                width=310,
            ),
            map_widget.ui(height="85vh"),
        ),
    ),

    # -- Tab 2: MapLibre Controls -----------------------------------------
    ui.nav_panel(
        "\U0001F5FA MapLibre Controls",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("MapLibre", class_="badge text-bg-success mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\u2693 Basemap",
                        ui.input_select(
                            "ml_basemap", "Basemap style",
                            choices=list(BASEMAP_CHOICES.keys()),
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F9ED Navigation & Location",
                        sidebar_hint(
                            "Toggle native MapLibre controls on the map. "
                            "These are rendered by MapLibre GL JS, not deck.gl."
                        ),
                        ui.input_switch("ml_navigation",
                                        "NavigationControl", value=True),
                        ui.input_switch("ml_geolocate",
                                        "GeolocateControl", value=False),
                        ui.input_switch("ml_globe",
                                        "GlobeControl", value=False),
                        sidebar_hint(
                            "\u2139\uFE0F This tab uses native MapLibre layers "
                            "(not deck.gl overlays), so MPAs and ports "
                            "render correctly on the globe surface."
                        ),
                        ui.input_switch("ml_terrain",
                                        "TerrainControl", value=False),
                        sidebar_hint(
                            "Requires a terrain/DEM source in the basemap "
                            "style (e.g. MapTiler or MapLibre demo tiles). "
                            "Most free CARTO and Stadia styles do not "
                            "include terrain data."
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4DC Legend Plugin",
                        sidebar_hint(
                            "watergis/maplibre-gl-legend \u2014 auto-generates "
                            "a legend panel from the MapLibre style. "
                            "This tab uses native layers, so MPAs and ports "
                            "appear in the legend. Toggle visibility with "
                            "checkboxes."
                        ),
                        ui.input_switch("ml_legend",
                                        "Legend panel", value=True),
                        ui.input_switch("ml_legend_checkbox",
                                        "Show checkboxes", value=True),
                        ui.input_switch("ml_legend_default",
                                        "Open by default", value=True),
                    ),
                    ui.accordion_panel(
                        "\U0001F50D Opacity Plugin",
                        sidebar_hint(
                            "maplibre-gl-opacity — layer switcher with "
                            "opacity sliders for overlay layers."
                        ),
                        ui.input_switch("ml_opacity",
                                        "Opacity control", value=False),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CD Drag Marker",
                        ui.input_action_button("ml_place_marker",
                                               "\U0001F4CD Place drag marker"),
                        ui.output_text_verbatim("ml_drag_info"),
                    ),
                    id="tab2_ml_accordion",
                    open=False,
                    multiple=True,
                ),
                width=310,
            ),
            maplibre_widget.ui(height="85vh"),
        ),
    ),

    # -- Tab 3: Events & Tooltips -----------------------------------------
    ui.nav_panel(
        "\U0001F4E1 Events & Tooltips",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F4AC Tooltip Template",
                        sidebar_hint(
                            "Edit the HTML template below. Use {field} "
                            "placeholders to interpolate feature properties."
                        ),
                        ui.input_text_area(
                            "tooltip_template", "HTML template",
                            value=DEFAULT_TOOLTIP_HTML,
                            rows=3,
                        ),
                        ui.input_text("tooltip_bg", "Background colour",
                                      value="#1a1a2e"),
                        ui.input_text("tooltip_fg", "Text colour",
                                      value="#eeeeee"),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CD Drag Marker",
                        ui.input_action_button("events_marker",
                                               "\U0001F4CD Place drag marker"),
                        ui.output_text_verbatim("events_drag"),
                    ),
                    id="tab3_accordion",
                    open=False,
                    multiple=True,
                ),
                width=310,
            ),
            events_widget.ui(height="50vh"),
            ui.layout_columns(
                ui.card(
                    ui.card_header("\U0001F5B1\uFE0F Click Event"),
                    ui.output_text_verbatim("click_info"),
                ),
                ui.card(
                    ui.card_header("\U0001F50D Hover Event"),
                    ui.output_text_verbatim("hover_info"),
                ),
                ui.card(
                    ui.card_header("\U0001F30D Current Viewport"),
                    ui.output_text_verbatim("viewport_info"),
                ),
                ui.card(
                    ui.card_header("\U0001F4CD Drag Marker"),
                    ui.output_text_verbatim("events_drag2"),
                ),
                col_widths=[6, 6, 6, 6],
            ),
        ),
    ),

    # -- Tab 4: Colour Scales ---------------------------------------------
    ui.nav_panel(
        "\U0001F3A8 Colour Scales",
        ui.layout_columns(
            ui.card(
                ui.card_header(
                    "\U0001F308 color_range() \u2014 Palette Preview"
                ),
                ui.output_ui("palette_preview"),
            ),
            ui.card(
                ui.card_header(
                    "\U0001F4CA color_bins() \u2014 Equal-Width Classification"
                ),
                ui.output_ui("bins_preview"),
            ),
            ui.card(
                ui.card_header(
                    "\U0001F4C8 color_quantiles() \u2014 Quantile "
                    "Classification"
                ),
                ui.output_ui("quantiles_preview"),
            ),
            col_widths=[12, 6, 6],
        ),
    ),

    # -- Tab 5: Advanced --------------------------------------------------
    ui.nav_panel(
        "\u2699 Advanced",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F4A1 Lighting Effects",
                        sidebar_hint(
                            "The map shows 3-D cargo columns. Enable lighting "
                            "to see ambient and point-light shading."
                        ),
                        ui.input_switch("enable_lighting",
                                        "Enable lighting", value=False),
                        ui.input_slider(
                            "ambient", "Ambient intensity",
                            0.0, 2.0, 1.0, step=0.1,
                        ),
                        ui.input_slider(
                            "point_intensity", "Point light intensity",
                            0.0, 3.0, 1.5, step=0.1,
                        ),
                    ),
                    ui.accordion_panel(
                        "\u26A1 Binary Transport",
                        sidebar_hint(
                            "Push 2,500 random points encoded as numpy "
                            "binary arrays."
                        ),
                        ui.input_action_button(
                            "push_binary",
                            "\u26A1 Push Binary ScatterplotLayer",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F50E Data Filter Extension",
                        sidebar_hint(
                            "Filter ports by cargo tonnage using "
                            "GPU-accelerated DataFilterExtension."
                        ),
                        ui.input_action_button(
                            "push_filtered",
                            "\U0001F50E Push Filtered Layer",
                        ),
                        ui.input_slider(
                            "filter_value", "Max cargo filter (Mt)",
                            min=0, max=60, value=60, step=1,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F9E9 Widgets (v0.8.0)",
                        sidebar_hint(
                            "Toggle deck.gl widgets on the Advanced map. "
                            "Widgets are added/removed via set_widgets()."
                        ),
                        ui.tags.strong("Standard"),
                        ui.tooltip(
                            ui.input_switch("adv_zoom_widget",
                                            "Zoom", value=False),
                            "Zoom in/out buttons (ZoomWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_compass_widget",
                                            "Compass", value=False),
                            "Bearing indicator; click to reset north (CompassWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_fps_widget",
                                            "FPS counter", value=False),
                            "Real-time frames-per-second counter (FpsWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_fullscreen_widget",
                                            "Fullscreen", value=False),
                            "Toggle browser fullscreen mode (FullscreenWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_scale_widget",
                                            "Scale bar", value=False),
                            "Distance scale bar in metric units (ScaleWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_gimbal_widget",
                                            "Gimbal (3-D)", value=False),
                            "3-D camera gimbal for pitch & bearing (GimbalWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_reset_view_widget",
                                            "Reset view", value=False),
                            "Reset camera to the initial view state (ResetViewWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_screenshot_widget",
                                            "Screenshot", value=False),
                            "Capture a PNG screenshot of the map (ScreenshotWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_loading_widget",
                                            "Loading spinner", value=False),
                            "Spinner displayed while layers are loading (LoadingWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_theme_widget",
                                            "Theme toggle", value=False),
                            "Switch between light and dark deck.gl theme (ThemeWidget)",
                        ),
                        ui.tags.hr(),
                        ui.tags.strong("Experimental (deck.gl \u2265 9.2)"),
                        ui.tooltip(
                            ui.input_switch("adv_context_menu_widget",
                                            "Context menu", value=False),
                            "Right-click context menu on the map (ContextMenuWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_info_widget",
                                            "Info display", value=False),
                            "Layer hover/pick information panel (InfoWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_splitter_widget",
                                            "Splitter", value=False),
                            "Split-screen view divider to compare layers (SplitterWidget)",
                        ),
                        ui.tooltip(
                            ui.input_switch("adv_stats_widget",
                                            "Stats (GPU/CPU)", value=False),
                            "GPU/CPU performance statistics overlay (StatsWidget)",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F3AC Transitions (v0.8.0)",
                        sidebar_hint(
                            "Push a layer with animated radius transitions."
                        ),
                        ui.input_action_button(
                            "push_transitions",
                            "\U0001F3AC Push Animated Layer",
                        ),
                    ),
                    id="tab5_accordion",
                    open=False,
                    multiple=True,
                ),
                width=300,
            ),
            adv_widget.ui(height="55vh"),
            ui.card(
                ui.card_header("\U0001F4DF Status Console"),
                ui.output_text_verbatim("advanced_status"),
            ),
        ),
    ),

    # -- Tab 6: Export & Serialisation ------------------------------------
    ui.nav_panel(
        "\U0001F4E6 Export",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F4E4 Export Actions",
                        sidebar_hint(
                            "Export the current map state to standalone HTML "
                            "or JSON format."
                        ),
                        ui.input_action_button(
                            "export_html", "\U0001F310 Export HTML File",
                        ),
                        ui.input_action_button(
                            "export_json", "\U0001F4CB Serialise to JSON",
                        ),
                        ui.input_action_button(
                            "roundtrip_json",
                            "\U0001F504 JSON Round-Trip Test",
                        ),
                    ),
                    id="tab6_accordion",
                    open=False,
                    multiple=True,
                ),
                width=280,
            ),
            ui.card(
                ui.card_header("\U0001F4C4 Output"),
                ui.output_text_verbatim("export_output"),
            ),
        ),
    ),

    # -- Tab 7: Drawing Tools ---------------------------------------------
    ui.nav_panel(
        "\u270F\uFE0F Drawing",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("MapLibre", class_="badge text-bg-success mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\u270F\uFE0F Drawing Controls",
                        sidebar_hint(
                            "Use MapboxDraw to draw polygons, lines, and "
                            "points on the map. Drawn features are reported "
                            "back to Python in real time."
                        ),
                        ui.input_action_button(
                            "draw_enable", "\u2705 Enable Drawing",
                        ),
                        ui.input_action_button(
                            "draw_disable", "\u274C Disable Drawing",
                        ),
                        ui.input_action_button(
                            "draw_get", "\U0001F4CB Get Drawn Features",
                        ),
                        ui.input_action_button(
                            "draw_clear", "\U0001F5D1\uFE0F Clear All Drawn",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CD Markers & Popups",
                        sidebar_hint(
                            "Programmatically add named markers with "
                            "optional popups and drag support."
                        ),
                        ui.input_action_button(
                            "add_port_markers",
                            "\U0001F4CD Add Port Markers",
                        ),
                        ui.input_action_button(
                            "clear_all_markers",
                            "\U0001F5D1\uFE0F Clear All Markers",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F50D Spatial Query",
                        sidebar_hint(
                            "Query visible features at a point or by "
                            "geographic coordinates."
                        ),
                        ui.input_action_button(
                            "query_center",
                            "\U0001F50D Query at Map Center",
                        ),
                    ),
                    id="tab7_accordion",
                    open=False,
                    multiple=True,
                ),
                width=280,
            ),
            ui.card(
                ui.card_header("\U0001F5FA\uFE0F Drawing & Interaction Map"),
                draw_widget.ui(height="65vh"),
            ),
            ui.card(
                ui.card_header("\U0001F4CB Interaction Log"),
                ui.output_text_verbatim("draw_log"),
            ),
        ),
    ),

    # -- Tab 8: Animation (TripsLayer) ------------------------------------
    ui.nav_panel(
        "\U0001F6A2 Animation",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F6A2 TripsLayer Animation",
                        sidebar_hint(
                            "Animated vessel tracks using deck.gl TripsLayer. "
                            "Routes are rendered as trails that advance over "
                            "time, simulating real-time vessel movement."
                        ),
                        ui.input_switch(
                            "anim_show_trips", "Show animated tracks",
                            value=True,
                        ),
                        ui.input_slider(
                            "anim_trail_length", "Trail length",
                            min=50, max=500, value=200, step=25,
                        ),
                        ui.input_slider(
                            "anim_speed", "Animation speed",
                            min=0.1, max=20.0, value=1.0, step=0.1,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CA Additional Layers",
                        sidebar_hint(
                            "Toggle background layers shown alongside "
                            "the animated tracks."
                        ),
                        ui.input_switch(
                            "anim_show_ports", "Show ports",
                            value=True,
                        ),
                        ui.input_switch(
                            "anim_show_routes", "Show static routes",
                            value=False,
                        ),
                        ui.input_switch(
                            "anim_show_grid", "Show observation grid",
                            value=False,
                        ),
                    ),
                    id="tab8_accordion",
                    open=False,
                    multiple=True,
                ),
                width=280,
            ),
            ui.card(
                ui.card_header(
                    "\U0001F30A Baltic Sea — Animated Shipping Tracks"
                ),
                anim_widget.ui(height="75vh"),
            ),
        ),
    ),

    # -- Tab 9: v1.0 deck.gl Extensions -----------------------------------
    ui.nav_panel(
        "\u2728 v1.0 Extensions",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F9E9 BrushingExtension",
                        sidebar_hint(
                            "Highlights features near the cursor. "
                            "Move your mouse over the map to see the "
                            "brushing radius in action."
                        ),
                        ui.input_switch(
                            "v1_brushing", "Enable brushing",
                            value=True,
                        ),
                        ui.input_slider(
                            "v1_brush_radius", "Brush radius (m)",
                            min=5000, max=200000, value=50000, step=5000,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F50D DataFilterExtension",
                        sidebar_hint(
                            "GPU-based numeric filtering. Only ports "
                            "within the cargo range are rendered \u2014 "
                            "filtering happens entirely on the GPU."
                        ),
                        ui.input_switch(
                            "v1_data_filter", "Enable data filter",
                            value=False,
                        ),
                        ui.input_slider(
                            "v1_filter_range", "Filter cargo (Mt)",
                            min=0, max=100, value=[10, 80], step=5,
                        ),
                    ),
                    id="tab9_accordion",
                    open=False,
                    multiple=True,
                ),
                width=280,
            ),
            ui.card(
                ui.card_header(
                    "\u2728 v1.0.0 deck.gl Extensions — Brushing & Data Filter"
                ),
                v1_deck_widget.ui(height="75vh"),
            ),
        ),
    ),

    # -- Tab 10: v1.0 MapLibre Features ------------------------------------
    ui.nav_panel(
        "\u2728 v1.0 Clusters",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("MapLibre", class_="badge text-bg-success mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F4CD Clusters",
                        sidebar_hint(
                            "MapLibre GeoJSON clustering groups nearby points "
                            "into circles sized by point count. "
                            "Click a cluster to zoom in and expand it."
                        ),
                        ui.input_switch(
                            "v1_show_clusters", "Show clusters",
                            value=True,
                        ),
                        ui.input_slider(
                            "v1_cluster_radius", "Cluster radius (px)",
                            min=20, max=100, value=50, step=10,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F91D Cooperative Gestures",
                        sidebar_hint(
                            "Require Ctrl+scroll to zoom the map. "
                            "Useful when the map is embedded in a "
                            "scrollable page."
                        ),
                        ui.input_switch(
                            "v1_cooperative", "Cooperative gestures",
                            value=False,
                        ),
                    ),
                    id="tab10_accordion",
                    open=["\U0001F4CD Clusters"],
                    multiple=True,
                ),
                width=280,
            ),
            ui.card(
                ui.card_header(
                    "\u2728 v1.0.0 MapLibre Features — Clusters & Gestures"
                ),
                v1_ml_widget.ui(height="75vh"),
            ),
        ),
    ),

    # -- Tab 11: 3-D Visualization -----------------------------------------
    ui.nav_panel(
        "\U0001F30D 3D Visualisation",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small("deck.gl", class_="badge text-bg-primary mb-2"),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F3D4 Bathymetry",
                        sidebar_hint(
                            "3-D extruded columns showing synthetic Baltic "
                            "Sea bathymetry. Deepest point ~459 m near the "
                            "Landsort Deep."
                        ),
                        ui.input_switch(
                            "td_bathy", "Show bathymetry grid",
                            value=True,
                        ),
                        ui.input_slider(
                            "td_bathy_elev", "Elevation scale",
                            min=1, max=50, value=10, step=1,
                        ),
                        ui.input_switch(
                            "td_bathy_wireframe", "Wireframe",
                            value=False,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F41F Fish Observations",
                        sidebar_hint(
                            "Species depth observations rendered as extruded "
                            "hexagons (aggregated) or individual columns. "
                            "Height encodes observation depth."
                        ),
                        ui.input_switch(
                            "td_fish", "Show fish observations",
                            value=False,
                        ),
                        ui.input_select(
                            "td_fish_mode", "Render mode",
                            choices={
                                "hexagon": "Hexagon aggregation",
                                "column": "Individual columns",
                            },
                        ),
                        ui.input_slider(
                            "td_fish_elev", "Elevation scale",
                            min=1, max=30, value=5, step=1,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F310 3-D Arcs",
                        sidebar_hint(
                            "Port-to-port shipping arcs in 3-D with altitude "
                            "proportional to route length."
                        ),
                        ui.input_switch(
                            "td_arcs", "Show 3-D arcs",
                            value=False,
                        ),
                        ui.input_slider(
                            "td_arc_width", "Arc width (px)",
                            min=1, max=10, value=3, step=1,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4A1 Lighting & Camera",
                        sidebar_hint(
                            "Control the LightingEffect and camera pitch / "
                            "bearing for the 3-D scene."
                        ),
                        ui.input_switch(
                            "td_lighting", "Enable lighting",
                            value=True,
                        ),
                        ui.input_slider(
                            "td_ambient", "Ambient intensity",
                            min=0.0, max=3.0, value=1.0, step=0.1,
                        ),
                        ui.input_slider(
                            "td_point_light", "Point-light intensity",
                            min=0.0, max=5.0, value=2.0, step=0.1,
                        ),
                        ui.input_slider(
                            "td_pitch", "Camera pitch (\u00b0)",
                            min=0, max=85, value=45, step=5,
                        ),
                        ui.input_slider(
                            "td_bearing", "Camera bearing (\u00b0)",
                            min=-180, max=180, value=-15, step=5,
                        ),
                    ),
                    id="tab11_accordion",
                    open=["\U0001F3D4 Bathymetry"],
                    multiple=True,
                ),
                width=300,
            ),
            ui.card(
                ui.card_header(
                    "\U0001F30D 3-D Baltic Sea Visualisation"
                ),
                three_d_widget.ui(height="80vh"),
            ),
        ),
    ),

    # -- Tab 12: Seal IBM (Individual-Based Model) -------------------------
    ui.nav_panel(
        "\U0001F9AD Seal IBM",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small(
                    "deck.gl + IBM", class_="badge text-bg-primary mb-2",
                ),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F9AD Species & Individuals",
                        sidebar_hint(
                            "Individual-Based Model of Baltic Sea seal "
                            "movement. Seals depart from real haul-out "
                            "colonies on correlated random-walk foraging "
                            "trips and return to their colony."
                        ),
                        ui.input_radio_buttons(
                            "seal_model_type", "Movement model",
                            choices={
                                "crw": "\U0001F500 Correlated Random Walk",
                                "mcconnell": "\U0001F9E0 McConnell IBM (energy)",
                            },
                            selected="crw",
                        ),
                        ui.panel_conditional(
                            "input.seal_model_type === 'mcconnell'",
                            sidebar_hint(
                                "McConnell, Smout & Wu (2017) "
                                "energy-budget model: seals forage in "
                                "habitat-quality patches, deplete energy, "
                                "return to haulouts to rest, then "
                                "depart again."
                            ),
                            ui.input_slider(
                                "seal_sim_hours",
                                "Simulation hours",
                                min=24, max=720, value=168, step=24,
                            ),
                        ),
                        ui.input_slider(
                            "seal_n_individuals", "Number of seals",
                            min=5, max=1000, value=30, step=5,
                        ),
                        ui.input_checkbox_group(
                            "seal_species", "Species to show",
                            choices={
                                "Grey seal": "\U0001F9AD Grey seal",
                                "Ringed seal": "\U0001F535 Ringed seal",
                                "Harbour seal": "\U0001F7E4 Harbour seal",
                            },
                            selected=[
                                "Grey seal",
                                "Ringed seal",
                                "Harbour seal",
                            ],
                        ),
                    ),
                    ui.accordion_panel(
                        "\u23F1 Animation Controls",
                        sidebar_hint(
                            "Adjust animation speed and trail length for "
                            "the seal movement tracks."
                        ),
                        trips_animation_ui("seal_anim"),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CD Overlays",
                        sidebar_hint(
                            "Toggle haul-out colony markers, "
                            "estimated foraging-range ellipses, "
                            "and EMODnet bathymetry underlay."
                        ),
                        ui.input_switch(
                            "seal_bathymetry", "EMODnet bathymetry",
                            value=True,
                        ),
                        ui.input_switch(
                            "seal_haulouts", "Show haul-out sites",
                            value=False,
                        ),
                        ui.input_switch(
                            "seal_foraging", "Show foraging areas",
                            value=True,
                        ),
                    ),
                    id="tab12_accordion",
                    open=["\U0001F9AD Species & Individuals"],
                    multiple=True,
                ),
                width=300,
            ),
            ui.card(
                ui.card_header(
                    "\U0001F9AD Baltic Sea — Seal Movement (IBM Simulation)"
                ),
                seal_widget.ui(height="80vh"),
            ),
        ),
    ),

    # -- Tab 13: Widgets Gallery ------------------------------------------
    ui.nav_panel(
        "\U0001F9E9 Widgets",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small(
                    "deck.gl widgets", class_="badge text-bg-primary mb-2",
                ),
                ui.accordion(
                    # -- Standard widgets (v0.8.0) -------------------------
                    ui.accordion_panel(
                        "\U0001F527 Standard Widgets",
                        sidebar_hint(
                            "12 standard deck.gl widgets shipped "
                            "since v0.8.0. Toggle each one to see it "
                            "appear on the map."
                        ),
                        ui.tags.strong("Navigation"),
                        ui.input_switch(
                            "wg_zoom", "Zoom \u00B1", value=True,
                        ),
                        ui.input_switch(
                            "wg_compass", "Compass", value=True,
                        ),
                        ui.input_switch(
                            "wg_gimbal", "Gimbal (3-D)", value=False,
                        ),
                        ui.input_switch(
                            "wg_reset_view", "Reset view", value=False,
                        ),
                        ui.tags.hr(),
                        ui.tags.strong("Display"),
                        ui.input_switch(
                            "wg_fullscreen", "Fullscreen", value=True,
                        ),
                        ui.input_switch(
                            "wg_scale", "Scale bar", value=True,
                        ),
                        ui.input_switch(
                            "wg_screenshot", "Screenshot", value=False,
                        ),
                        ui.input_switch(
                            "wg_fps", "FPS counter", value=False,
                        ),
                        ui.tags.hr(),
                        ui.tags.strong("Behaviour"),
                        ui.input_switch(
                            "wg_loading", "Loading spinner", value=False,
                        ),
                        ui.input_switch(
                            "wg_theme", "Theme toggle", value=False,
                        ),
                        ui.input_switch(
                            "wg_timeline", "Timeline scrubber", value=False,
                        ),
                        ui.input_switch(
                            "wg_geocoder", "Geocoder search", value=False,
                        ),
                    ),
                    # -- Experimental widgets (v9.2+) ----------------------
                    ui.accordion_panel(
                        "\U0001F9EA Experimental (v9.2+)",
                        sidebar_hint(
                            "5 experimental widgets introduced in "
                            "deck.gl 9.2. These require the CDN "
                            "to serve deck.gl \u2265 9.2."
                        ),
                        ui.input_switch(
                            "wg_context_menu", "Context menu", value=False,
                        ),
                        ui.input_switch(
                            "wg_info", "Info panel", value=False,
                        ),
                        ui.input_switch(
                            "wg_splitter", "Splitter", value=False,
                        ),
                        ui.input_switch(
                            "wg_stats", "Stats (GPU/CPU)", value=False,
                        ),
                        ui.input_switch(
                            "wg_view_selector", "View selector", value=False,
                        ),
                    ),
                    # -- Preset bundles ------------------------------------
                    ui.accordion_panel(
                        "\U0001F4E6 Preset Bundles",
                        sidebar_hint(
                            "One-click presets that activate a sensible "
                            "group of widgets for common scenarios."
                        ),
                        ui.input_action_button(
                            "wg_preset_nav",
                            "\U0001F9ED Navigation",
                            class_="btn-sm btn-outline-primary mb-1 w-100",
                        ),
                        ui.input_action_button(
                            "wg_preset_debug",
                            "\U0001F41B Debug / Performance",
                            class_="btn-sm btn-outline-warning mb-1 w-100",
                        ),
                        ui.input_action_button(
                            "wg_preset_presentation",
                            "\U0001F3AC Presentation",
                            class_="btn-sm btn-outline-success mb-1 w-100",
                        ),
                        ui.input_action_button(
                            "wg_preset_all",
                            "\U0001F4A5 All 17 Widgets",
                            class_="btn-sm btn-outline-danger mb-1 w-100",
                        ),
                        ui.input_action_button(
                            "wg_preset_none",
                            "\U0001F6AB Clear All",
                            class_="btn-sm btn-outline-secondary mb-1 w-100",
                        ),
                    ),
                    # -- Layer pairing ------------------------------------
                    ui.accordion_panel(
                        "\U0001F5FA Layer + Widget",
                        sidebar_hint(
                            "Choose a layer type to see it combined "
                            "with contextually appropriate widgets "
                            "on the map."
                        ),
                        ui.input_select(
                            "wg_layer_combo",
                            "Layer scenario",
                            choices={
                                "ports": "\u2693 Ports (ScatterplotLayer)",
                                "heatmap": "\U0001F525 Heatmap (HeatmapLayer)",
                                "arcs": "\U0001F308 Arcs (ArcLayer)",
                                "routes": "\U0001F6A2 Routes (PathLayer)",
                                "3d_columns": "\U0001F4CA 3-D Columns",
                                "hexagons": "\U0001F4D0 Hexagons",
                            },
                            selected="ports",
                        ),
                    ),
                    id="tab13_accordion",
                    open=["\U0001F527 Standard Widgets"],
                    multiple=True,
                ),
                width=300,
            ),
            ui.card(
                ui.card_header(
                    "\U0001F9E9 Widget Gallery — All 17 deck.gl Widgets"
                ),
                widgets_gallery_widget.ui(height="60vh"),
            ),
            ui.card(
                ui.card_header("\U0001F4DF Active Widgets"),
                ui.output_text_verbatim("wg_status"),
            ),
        ),
    ),

    # -- About (right-aligned) --------------------------------------------
    ui.nav_spacer(),
    ui.nav_menu(
        "\u2139\uFE0F About",
        ui.nav_control(
            ui.div(
                ui.tags.h5(
                    "\U0001F30A shiny_deckgl",
                    style="margin:0 0 8px 0;font-weight:700;",
                ),
                ui.tags.table(
                    ui.tags.tbody(
                        _about_row("shiny_deckgl", SHINY_DECKGL_VERSION),
                        _about_row("deck.gl", DECKGL_VERSION),
                        _about_row("MapLibre GL JS", MAPLIBRE_VERSION),
                        _about_row("Mapbox GL Draw", MAPBOX_DRAW_VERSION),
                        _about_row("maplibre-gl-legend", MAPLIBRE_LEGEND_VERSION),
                        _about_row("maplibre-gl-opacity", MAPLIBRE_OPACITY_VERSION),
                        _about_row("Python", _python_version()),
                        _about_row("Shiny", _shiny_version()),
                    ),
                    style=(
                        "width:100%;font-size:0.85rem;"
                        "border-collapse:collapse;"
                    ),
                ),
                ui.tags.hr(style="margin:10px 0;"),
                ui.tags.a(
                    "GitHub repository",
                    href="https://github.com/razinkele/shiny_deckgl",
                    target="_blank",
                    style="font-size:0.85rem;",
                ),
                style="padding:12px 16px;min-width:240px;",
            ),
        ),
        align="right",
    ),

    title="\U0001F30A shiny_deckgl",
    id="navbar",
    header=ui.tags.style(MARINE_CSS),
)


# ===========================================================================
# Server
# ===========================================================================

def server(input, output, session: Session):
    # Shared reactive stores
    _main_layers: reactive.Value[list[dict]] = reactive.Value([])
    _adv_layers: reactive.Value[list[dict]] = reactive.Value([])
    _export_log: reactive.Value[str] = reactive.Value("")
    _advanced_log: reactive.Value[str] = reactive.Value("")

    # -- Pre-computed static data (generated once per session) ----------
    _arc_data = make_arc_data()
    _heatmap_points = make_heatmap_points(300)
    _path_data = make_path_data()
    _port_data_simple = make_port_data_simple()
    _cargo_values = [p["cargo_mt"] for p in PORTS]

    # -- Shared helpers ---------------------------------------------------

    def _make_lighting_effects(
        ambient: float, point_intensity: float,
    ) -> list[dict]:
        """Build a standard Baltic-centered LightingEffect spec."""
        return [{
            "type": "LightingEffect",
            "ambientLight": {
                "color": [255, 255, 255],
                "intensity": ambient,
            },
            "pointLights": [{
                "color": [255, 255, 220],
                "intensity": point_intensity,
                "position": [19.5, 57.0, 80000],
            }],
        }]

    # =================================================================
    # Tab 1 — deck.gl Layers
    # =================================================================

    def _build_main_layers() -> list[dict]:
        """Build the layer stack for the main interactive map."""
        layers: list[dict] = []
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)

        mode = input.color_mode()
        if mode == "Equal-width bins":
            port_colors = color_bins(_cargo_values, 6, palette)
        elif mode == "Quantile bins":
            port_colors = color_quantiles(_cargo_values, 6, palette)
        else:
            port_colors = color_range(len(PORTS), palette)

        # WMS layer (EMODnet bathymetry via OWSLib-validated service)
        wms_layer_name = input.wms_layer()
        if wms_layer_name:
            safe_id = wms_layer_name.replace(":", "_")
            layers.append(wms_layer(
                f"wms-{safe_id}",
                EMODNET_WMS_URL,
                layers=[wms_layer_name],
            ))

        # GeoJSON — Marine Protected Areas (HELCOM)
        if input.show_mpa():
            layers.append(geojson_layer(
                "mpa-zones", MPA_GEOJSON,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
                pickable=True,
            ))

        # Heatmap — random observation density
        if input.show_heatmap():
            layers.append(heatmap_layer(
                "observation-heat",
                data=_heatmap_points,
                getPosition="@@d",
                getWeight="@@=d[2]",
                radiusPixels=40, intensity=1.5, threshold=0.1,
            ))

        # Paths — shipping routes as polylines
        if input.show_paths():
            layers.append(path_layer(
                "route-paths",
                data=_path_data,
                getPath="@@=d.path",
                getColor="@@=d.color",
                getWidth=3, widthMinPixels=2, pickable=True,
            ))

        # Arcs — connections between ports
        if input.show_routes():
            layers.append(arc_layer(
                "port-arcs",
                data=_arc_data,
                getSourcePosition="@@=d.sourcePosition",
                getTargetPosition="@@=d.targetPosition",
                getSourceColor="@@=d.sourceColor",
                getTargetColor="@@=d.targetColor",
                getWidth=2, pickable=True,
            ))

        # Scatterplot — ports with dynamic palette colours
        if input.show_ports():
            port_data = []
            for i, p in enumerate(PORTS):
                port_data.append({
                    "position": [p["lon"], p["lat"]],
                    "name": p["name"],
                    "country": p["country"],
                    "cargo_mt": p["cargo_mt"],
                    "color": port_colors[i],
                    "radius": max(5, p["cargo_mt"] / 3),
                })
            layers.append(scatterplot_layer(
                "ports", port_data,
                getPosition="@@=d.position",
                getFillColor="@@=d.color",
                getRadius="@@=d.radius",
                radiusScale=1000,
                radiusMinPixels=6,
                radiusMaxPixels=30,
                pickable=True,
            ))

        return layers

    def _build_deck_legend() -> dict:
        """Build the deck.gl legend control spec for Tab 1."""
        entries: list[dict] = []
        if input.wms_layer():
            safe_id = input.wms_layer().replace(":", "_")
            entries.append({
                "layer_id": f"wms-{safe_id}",
                "label": f"WMS: {input.wms_layer()}",
                "color": [70, 130, 180],
                "shape": "rect",
            })
        if input.show_mpa():
            entries.append({
                "layer_id": "mpa-zones",
                "label": "Marine Protected Areas",
                "color": [0, 128, 0, 100],
                "shape": "rect",
            })
        if input.show_heatmap():
            entries.append({
                "layer_id": "observation-heat",
                "label": "Observation heatmap",
                "colors": [
                    [0, 25, 0, 25], [0, 85, 0, 85],
                    [0, 170, 0, 170], [0, 255, 0],
                    [255, 255, 0], [255, 0, 0],
                ],
                "shape": "gradient",
            })
        if input.show_paths():
            entries.append({
                "layer_id": "route-paths",
                "label": "Route paths",
                "color": [100, 100, 200],
                "shape": "line",
            })
        if input.show_routes():
            entries.append({
                "layer_id": "port-arcs",
                "label": "Shipping routes",
                "color": [255, 140, 0],
                "color2": [200, 0, 80],
                "shape": "arc",
            })
        if input.show_ports():
            entries.append({
                "layer_id": "ports",
                "label": "Baltic Ports",
                "color": [65, 182, 196],
                "shape": "circle",
            })
        return deck_legend_control(
            entries=entries,
            position="bottom-right",
            title="Deck.gl Layers",
        )

    # Initial push (with widgets)
    @reactive.Effect
    async def _main_init():
        layers = _build_main_layers()
        _main_layers.set(layers)
        await map_widget.update(session, layers, widgets=MAP_WIDGETS)
        # Push deck.gl legend
        await map_widget.set_controls(session, [_build_deck_legend()])

    # Reactive rebuild on control change
    @reactive.Effect
    @reactive.event(
        input.palette, input.color_mode,
        input.show_ports, input.show_mpa, input.show_routes,
        input.show_paths, input.wms_layer, input.show_heatmap,
    )
    async def _main_rebuild():
        layers = _build_main_layers()
        _main_layers.set(layers)
        await map_widget.update(session, layers)
        await map_widget.set_controls(session, [_build_deck_legend()])

    # Basemap switching (Tab 1)
    @reactive.Effect
    @reactive.event(input.basemap)
    async def _switch_basemap():
        style_url = BASEMAP_CHOICES.get(input.basemap(), CARTO_POSITRON)
        await map_widget.set_style(session, style_url)

    # Fly-to / ease-to transitions
    @reactive.Effect
    @reactive.event(input.fly_klaipeda)
    async def _fly_klaipeda():
        await map_widget.fly_to(session, 21.13, 55.71, zoom=10, speed=1.5)

    @reactive.Effect
    @reactive.event(input.ease_stockholm)
    async def _ease_stockholm():
        await map_widget.ease_to(
            session, 18.07, 59.33, zoom=10, duration=2000,
        )

    @reactive.Effect
    @reactive.event(input.fly_baltic)
    async def _fly_baltic():
        await map_widget.fly_to(
            session, 19.5, 57.0, zoom=5, pitch=0, bearing=0,
        )

    # Drag marker (main map)
    @reactive.Effect
    @reactive.event(input.place_marker)
    async def _place_drag():
        await map_widget.add_drag_marker(session)

    @render.text
    def drag_info():
        pos = input[map_widget.drag_input_id]()
        if pos is None:
            return "Place a marker first\u2026"
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    # =================================================================
    # Tab 2 — MapLibre Controls
    # =================================================================

    async def _ml_add_native_layers():
        """Add native MapLibre sources + layers for MPAs and ports.

        Native layers render correctly in globe projection and are
        visible to the legend / opacity plugins (unlike deck.gl overlays).
        """
        # --- MPA polygons (GeoJSON source + fill + line layers) ---
        await maplibre_widget.add_source(session, "mpa-source", {
            "type": "geojson",
            "data": MPA_GEOJSON,
        })
        await maplibre_widget.add_maplibre_layer(session, {
            "id": "mpa-fill",
            "type": "fill",
            "source": "mpa-source",
            "paint": {
                "fill-color": "rgba(0, 180, 120, 0.25)",
                "fill-outline-color": "rgba(0, 180, 120, 0.8)",
            },
        })
        await maplibre_widget.add_maplibre_layer(session, {
            "id": "mpa-line",
            "type": "line",
            "source": "mpa-source",
            "paint": {
                "line-color": "rgba(0, 180, 120, 0.8)",
                "line-width": 2,
            },
        })
        # --- Port circles (GeoJSON source + circle layer) ---
        await maplibre_widget.add_source(session, "ports-source", {
            "type": "geojson",
            "data": make_port_geojson(),
        })
        await maplibre_widget.add_maplibre_layer(session, {
            "id": "ports-circle",
            "type": "circle",
            "source": "ports-source",
            "paint": {
                "circle-radius": 7,
                "circle-color": "rgba(0, 140, 200, 0.8)",
                "circle-stroke-color": "#fff",
                "circle-stroke-width": 1,
            },
        })

    @reactive.Effect
    async def _ml_init():
        """Push initial native layers + controls to the MapLibre tab."""
        # Send an empty deck.gl update so the overlay is initialised
        await maplibre_widget.update(session, [])
        # Add native MapLibre layers (globe-safe, legend/opacity visible)
        await _ml_add_native_layers()
        controls = _build_ml_controls()
        await maplibre_widget.set_controls(session, controls)

    def _build_ml_controls() -> list[dict]:
        """Build the list of MapLibre controls from sidebar switches."""
        ctrls: list[dict] = []
        if input.ml_navigation():
            ctrls.append({
                "type": "navigation",
                "position": "top-right",
                "options": {},
            })
        if input.ml_geolocate():
            ctrls.append(geolocate_control(
                position="top-right",
                trackUserLocation=True,
            ))
        if input.ml_globe():
            ctrls.append(globe_control(position="top-right"))
        if input.ml_terrain():
            ctrls.append(terrain_control(position="top-right"))
        if input.ml_legend():
            ctrls.append(legend_control(
                targets={
                    "mpa-fill": "Marine Protected Areas",
                    "ports-circle": "Baltic Ports",
                },
                position="bottom-left",
                show_default=input.ml_legend_default(),
                show_checkbox=input.ml_legend_checkbox(),
                only_rendered=False,
            ))
        if input.ml_opacity():
            ctrls.append(opacity_control(
                position="top-left",
                over_layers={
                    "mpa-fill": "Marine Protected Areas",
                    "ports-circle": "Baltic Ports",
                },
            ))
        return ctrls

    # Re-build controls when any toggle changes
    @reactive.Effect
    @reactive.event(
        input.ml_navigation, input.ml_geolocate,
        input.ml_globe, input.ml_terrain,
        input.ml_legend, input.ml_legend_checkbox,
        input.ml_legend_default, input.ml_opacity,
    )
    async def _ml_controls_rebuild():
        controls = _build_ml_controls()
        await maplibre_widget.set_controls(session, controls)

    # Basemap switching — re-add native layers after style swap
    @reactive.Effect
    @reactive.event(input.ml_basemap)
    async def _ml_switch_basemap():
        style_url = BASEMAP_CHOICES.get(
            input.ml_basemap(), CARTO_POSITRON,
        )
        await maplibre_widget.set_style(session, style_url)
        # set_style removes all sources/layers; re-add ours
        await _ml_add_native_layers()
        # Re-apply controls so legend picks up the fresh layers
        controls = _build_ml_controls()
        await maplibre_widget.set_controls(session, controls)

    # Drag marker (MapLibre tab)
    @reactive.Effect
    @reactive.event(input.ml_place_marker)
    async def _ml_place_drag():
        await maplibre_widget.add_drag_marker(session)

    @render.text
    def ml_drag_info():
        pos = input[maplibre_widget.drag_input_id]()
        if pos is None:
            return "Place a marker first\u2026"
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    # =================================================================
    # Tab 3 — Events & Tooltips
    # =================================================================

    @reactive.Effect
    async def _events_init():
        """Push interactive layers to the events map."""
        layers = [
            geojson_layer(
                "ev-mpa", MPA_GEOJSON,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
                pickable=True,
            ),
            layer(
                "ArcLayer", "ev-arcs",
                data=_arc_data,
                getSourcePosition="@@=d.sourcePosition",
                getTargetPosition="@@=d.targetPosition",
                getSourceColor="@@=d.sourceColor",
                getTargetColor="@@=d.targetColor",
                getWidth=2, pickable=True,
            ),
            scatterplot_layer(
                "ev-ports", _port_data_simple,
                getPosition="@@=d.position",
                getFillColor=[200, 0, 80, 180],
                radiusMinPixels=8, pickable=True,
            ),
        ]
        await events_widget.update(session, layers)
        await events_widget.set_controls(session, [
            deck_legend_control(
                entries=[
                    {"layer_id": "ev-mpa", "label": "Marine Protected Areas",
                     "color": [0, 180, 120, 60], "shape": "rect"},
                    {"layer_id": "ev-arcs", "label": "Port connections",
                     "color": [255, 140, 0], "color2": [200, 0, 80],
                     "shape": "arc"},
                    {"layer_id": "ev-ports", "label": "Baltic Ports",
                     "color": [200, 0, 80, 180], "shape": "circle"},
                ],
                title="Events Layers",
            ),
        ])

    # Dynamic tooltip customisation
    @reactive.Effect
    @reactive.event(
        input.tooltip_template, input.tooltip_bg, input.tooltip_fg,
        ignore_init=True,
    )
    async def _update_tooltip():
        template = input.tooltip_template()
        if not template.strip():
            await events_widget.update_tooltip(session, None)
            return
        await events_widget.update_tooltip(session, {
            "html": template,
            "style": {
                "backgroundColor": input.tooltip_bg(),
                "color": input.tooltip_fg(),
                "fontSize": "13px",
            },
        })

    # Drag marker (events map)
    @reactive.Effect
    @reactive.event(input.events_marker)
    async def _events_place_marker():
        await events_widget.add_drag_marker(session)

    @render.text
    def events_drag():
        pos = input[events_widget.drag_input_id]()
        if pos is None:
            return "Place a marker to see position\u2026"
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    @render.text
    def events_drag2():
        pos = input[events_widget.drag_input_id]()
        if pos is None:
            return "No drag marker placed."
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    # Event readback outputs
    @render.text
    def click_info():
        data = input[events_widget.click_input_id]()
        if data is None:
            return "Click a port or arc on the map\u2026"
        obj_str = json.dumps(data.get("object"), indent=2, default=str)
        return (
            f"Layer:  {data.get('layerId')}\n"
            f"Coords: {data.get('coordinate')}\n"
            f"Object: {obj_str}"
        )

    @render.text
    def hover_info():
        data = input[events_widget.hover_input_id]()
        if data is None:
            return "Hover over a feature\u2026"
        return (
            f"Layer: {data.get('layerId')}\n"
            f"Coords: [{data.get('coordinate', [0, 0])[0]:.4f}, "
            f"{data.get('coordinate', [0, 0])[1]:.4f}]"
        )

    @render.text
    def viewport_info():
        vs = input[events_widget.view_state_input_id]()
        if vs is None:
            return "Pan or zoom the map\u2026"
        return (
            f"Longitude: {vs.get('longitude', 0):.4f}\n"
            f"Latitude:  {vs.get('latitude', 0):.4f}\n"
            f"Zoom:      {vs.get('zoom', 0):.2f}\n"
            f"Pitch:     {vs.get('pitch', 0):.1f}\u00b0\n"
            f"Bearing:   {vs.get('bearing', 0):.1f}\u00b0"
        )

    # =================================================================
    # Tab 4 — Colour Scales
    # =================================================================

    @render.ui
    def palette_preview():
        """Show all 5 palettes with 10-stop color_range swatches."""
        html_parts = []
        for pal_name, pal in PALETTE_CHOICES.items():
            stops = color_range(10, pal)
            swatches = "".join(
                f'<span class="palette-swatch-block" '
                f'style="background:rgb({c[0]},{c[1]},{c[2]});"></span>'
                for c in stops
            )
            html_parts.append(
                f'<div style="margin-bottom:10px;">'
                f'<strong style="font-size:0.9rem;color:#0d3158;">'
                f'{pal_name}</strong>'
                f'<br/><div style="margin-top:4px;">{swatches}</div></div>'
            )
        return ui.HTML("".join(html_parts))

    @render.ui
    def bins_preview():
        """Show color_bins classification of port cargo values."""
        cargo = [p["cargo_mt"] for p in PORTS]
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)
        colors = color_bins(cargo, 6, palette)
        rows = "".join(
            f'<tr>'
            f'<td>{PORTS[i]["name"]}</td>'
            f'<td>{cargo[i]} Mt</td>'
            f'<td><span class="colour-swatch" '
            f'style="background:rgb({c[0]},{c[1]},{c[2]});"></span></td>'
            f'</tr>'
            for i, c in enumerate(colors)
        )
        return ui.HTML(
            f'<table class="colour-table">'
            f'<tr><th>Port</th><th>Cargo</th><th>Bin Colour</th></tr>'
            f'{rows}</table>'
        )

    @render.ui
    def quantiles_preview():
        """Show color_quantiles classification of port cargo values."""
        cargo = [p["cargo_mt"] for p in PORTS]
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)
        colors = color_quantiles(cargo, 6, palette)
        rows = "".join(
            f'<tr>'
            f'<td>{PORTS[i]["name"]}</td>'
            f'<td>{cargo[i]} Mt</td>'
            f'<td><span class="colour-swatch" '
            f'style="background:rgb({c[0]},{c[1]},{c[2]});"></span></td>'
            f'</tr>'
            for i, c in enumerate(colors)
        )
        return ui.HTML(
            f'<table class="colour-table">'
            f'<tr><th>Port</th><th>Cargo</th><th>Quantile Colour</th></tr>'
            f'{rows}</table>'
        )

    # =================================================================
    # Tab 5 — Advanced
    # =================================================================

    def _adv_base_layers() -> list[dict]:
        """3-D cargo columns — good for demonstrating lighting effects."""
        column_data = [
            {
                "position": [p["lon"], p["lat"]],
                "elevation": p["cargo_mt"] * 200,
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "color": [0, 160, 230, 200],
            }
            for p in PORTS
        ]
        return [
            column_layer(
                "cargo-columns",
                data=column_data,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor="@@=d.color",
                diskResolution=12,
                radius=15000,
                extruded=True,
                pickable=True,
            ),
        ]

    @reactive.Effect
    async def _adv_init():
        layers = _adv_base_layers()
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        await adv_widget.set_controls(session, [
            deck_legend_control(
                entries=[
                    {"layer_id": "cargo-columns", "label": "Cargo (3D columns)",
                     "color": [0, 160, 230, 200], "shape": "rect"},
                ],
                title="Advanced Layers",
            ),
        ])

    # Lighting
    @reactive.Effect
    @reactive.event(
        input.enable_lighting, input.ambient, input.point_intensity,
    )
    async def _apply_lighting():
        layers = _adv_layers.get()
        effects = None
        if input.enable_lighting():
            effects = _make_lighting_effects(
                input.ambient(), input.point_intensity(),
            )
            _advanced_log.set(
                f"Lighting ON\n"
                f"  Ambient intensity: {input.ambient()}\n"
                f"  Point light intensity: {input.point_intensity()}\n"
                f"  Point light position: [19.5, 57.0, 80000]"
            )
        else:
            _advanced_log.set("Lighting OFF")
        await adv_widget.update(session, layers, effects=effects)

    # Binary transport (numpy)
    @reactive.Effect
    @reactive.event(input.push_binary)
    async def _push_binary():
        try:
            import numpy as np

            lons = np.linspace(10.0, 30.0, 50, dtype="float32")
            lats = np.linspace(53.0, 62.0, 50, dtype="float32")
            grid_lon, grid_lat = np.meshgrid(lons, lats)
            positions = np.column_stack([
                grid_lon.ravel(), grid_lat.ravel(),
            ]).astype("float32")
            binary_pos = encode_binary_attribute(positions)

            binary_lyr = layer(
                "ScatterplotLayer", "binary-scatter",
                data={"length": len(positions)},
                getPosition=binary_pos,
                getFillColor=[255, 100, 50, 200],
                radiusMinPixels=3, radiusMaxPixels=8, pickable=False,
            )

            layers = [
                lyr for lyr in _adv_layers.get()
                if lyr.get("id") != "binary-scatter"
            ] + [binary_lyr]
            _adv_layers.set(layers)
            await adv_widget.update(session, layers)
            _advanced_log.set(
                f"Binary transport layer pushed!\n"
                f"  Points: {len(positions):,}\n"
                f"  Array dtype: {positions.dtype}\n"
                f"  Array shape: {positions.shape}\n"
                f"  Base64 payload: {len(binary_pos['value']):,} chars"
            )
        except ImportError:
            _advanced_log.set(
                "numpy is not installed.\n"
                "Install with: micromamba install -n shiny numpy"
            )

    # Extensions (DataFilterExtension)

    # Pre-compute filter data (static; only filterRange changes)
    _filtered_port_data = [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "cargo_mt": p["cargo_mt"],
            "filterValue": p["cargo_mt"],
        }
        for p in PORTS
    ]

    def _make_filtered_layer(max_cargo: float) -> dict:
        """Build a DataFilterExtension scatterplot layer."""
        return layer(
            "ScatterplotLayer", "filtered-ports",
            data=_filtered_port_data,
            getPosition="@@=d.position",
            getFillColor=[255, 200, 0, 220],
            getRadius=8, radiusScale=1000, radiusMinPixels=20,
            pickable=True,
            extensions=["DataFilterExtension"],
            getFilterValue="@@=d.filterValue",
            filterRange=[0, max_cargo],
            parameters={"depthCompare": "always"},
        )

    @reactive.Effect
    @reactive.event(input.push_filtered)
    async def _push_filtered():
        max_cargo = input.filter_value()
        filtered_lyr = _make_filtered_layer(max_cargo)
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") != "filtered-ports"
        ] + [filtered_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        visible = sum(1 for p in PORTS if p["cargo_mt"] <= max_cargo)
        _advanced_log.set(
            f"DataFilterExtension layer pushed!\n"
            f"  Filter range: [0, {max_cargo}] Mt\n"
            f"  Ports visible: {visible}/{len(PORTS)}\n"
            f"  Extension: DataFilterExtension"
        )

    @reactive.Effect
    @reactive.event(input.filter_value)
    async def _update_filter():
        """Re-push the filtered layer when the slider changes."""
        layers = _adv_layers.get()
        if not any(lyr.get("id") == "filtered-ports" for lyr in layers):
            return
        max_cargo = input.filter_value()
        filtered_lyr = _make_filtered_layer(max_cargo)
        new_layers = [
            lyr for lyr in layers if lyr.get("id") != "filtered-ports"
        ] + [filtered_lyr]
        _adv_layers.set(new_layers)
        await adv_widget.update(session, new_layers)

    @render.text
    def advanced_status():
        return (
            _advanced_log.get()
            or "Use the controls to test advanced features\u2026"
        )

    # Widgets toggle (v0.8.0 + experimental v9.2)
    @reactive.Effect
    @reactive.event(
        input.adv_zoom_widget, input.adv_compass_widget,
        input.adv_fps_widget, input.adv_fullscreen_widget,
        input.adv_scale_widget, input.adv_gimbal_widget,
        input.adv_reset_view_widget, input.adv_screenshot_widget,
        input.adv_loading_widget, input.adv_theme_widget,
        input.adv_context_menu_widget, input.adv_info_widget,
        input.adv_splitter_widget, input.adv_stats_widget,
    )
    async def _toggle_adv_widgets():
        widgets: list[dict] = []
        # Standard widgets
        if input.adv_zoom_widget():
            widgets.append(zoom_widget())
        if input.adv_compass_widget():
            widgets.append(compass_widget())
        if input.adv_fps_widget():
            widgets.append(fps_widget())
        if input.adv_fullscreen_widget():
            widgets.append(fullscreen_widget())
        if input.adv_scale_widget():
            widgets.append(scale_widget())
        if input.adv_gimbal_widget():
            widgets.append(gimbal_widget())
        if input.adv_reset_view_widget():
            widgets.append(reset_view_widget())
        if input.adv_screenshot_widget():
            widgets.append(screenshot_widget())
        if input.adv_loading_widget():
            widgets.append(loading_widget())
        if input.adv_theme_widget():
            widgets.append(theme_widget())
        # Experimental widgets (deck.gl >= 9.2)
        if input.adv_context_menu_widget():
            widgets.append(context_menu_widget())
        if input.adv_info_widget():
            widgets.append(info_widget(placement="top-left"))
        if input.adv_splitter_widget():
            widgets.append(splitter_widget(
                orientation="vertical",
            ))
        if input.adv_stats_widget():
            widgets.append(stats_widget(placement="bottom-left"))
        await adv_widget.set_widgets(session, widgets)
        names = [w["@@widgetClass"] for w in widgets]
        _advanced_log.set(
            f"Widgets updated: {len(widgets)} active\n"
            + (
                "\n".join(f"  \u2022 {n}" for n in names)
                if names
                else "  (none)"
            )
        )

    # Transition demo (v0.8.0)
    @reactive.Effect
    @reactive.event(input.push_transitions)
    async def _push_transitions():
        """Push a scatterplot layer with animated transitions."""
        port_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "radius": max(5, p["cargo_mt"] / 2) * (1 + random.random()),
                "color": [
                    random.randint(50, 255),
                    random.randint(50, 255),
                    random.randint(50, 200),
                    200,
                ],
            }
            for p in PORTS
        ]
        animated_lyr = scatterplot_layer(
            "animated-ports",
            data=port_data,
            getPosition="@@=d.position",
            getFillColor="@@=d.color",
            getRadius="@@=d.radius",
            radiusScale=1000,
            radiusMinPixels=6,
            radiusMaxPixels=40,
            pickable=True,
            transitions={
                "getRadius": transition(800, easing="ease-in-out-cubic"),
                "getFillColor": transition(600, easing="ease-out-cubic"),
            },
        )
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") != "animated-ports"
        ] + [animated_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        _advanced_log.set(
            "Transition layer pushed!\n"
            "  Layer: animated-ports (ScatterplotLayer)\n"
            "  getRadius transition: 800ms ease-in-out-cubic\n"
            "  getFillColor transition: 600ms ease-out-cubic\n"
            "\nClick again to see transitions animate with new values."
        )

    # =================================================================
    # Tab 6 — Export & Serialisation
    # =================================================================

    @reactive.Effect
    @reactive.event(input.export_html)
    async def _do_export_html():
        layers = _main_layers.get()
        path = os.path.join(
            tempfile.gettempdir(), "shiny_deckgl_demo_export.html",
        )
        map_widget.to_html(layers, path=path, title="shiny_deckgl Export")
        fsize = os.path.getsize(path)
        _export_log.set(
            f"HTML exported successfully!\n"
            f"Path: {path}\n"
            f"Size: {fsize:,} bytes\n"
            f"Layers: {len(layers)}"
        )
        ui.notification_show(f"Exported to {path}", type="message")

    @reactive.Effect
    @reactive.event(input.export_json)
    async def _do_export_json():
        layers = _main_layers.get()
        spec = map_widget.to_json(layers)
        ellip = "\u2026" if len(spec) > 2000 else ""
        _export_log.set(
            f"JSON spec ({len(spec):,} chars):\n\n{spec[:2000]}{ellip}"
        )

    @reactive.Effect
    @reactive.event(input.roundtrip_json)
    async def _do_roundtrip():
        layers = _main_layers.get()
        spec_json = map_widget.to_json(layers)
        w2, layers2 = MapWidget.from_json(spec_json)
        checks = [
            f"Original widget id:     {map_widget.id}",
            f"Restored widget id:     {w2.id}",
            f"IDs match:              {map_widget.id == w2.id}",
            f"Style match:            {map_widget.style == w2.style}",
            f"View state match:       "
            f"{map_widget.view_state == w2.view_state}",
            f"Tooltip match:          "
            f"{map_widget.tooltip == w2.tooltip}",
            f"Layer count match:      "
            f"{len(layers)} == {len(layers2)}",
            f"Layer IDs (original):   "
            f"{[lyr.get('id') for lyr in layers]}",
            f"Layer IDs (restored):   "
            f"{[lyr.get('id') for lyr in layers2]}",
            "\n\u2713 JSON round-trip successful!",
        ]
        _export_log.set("\n".join(checks))

    @render.text
    def export_output():
        return _export_log.get() or "Click an export button\u2026"

    # =================================================================
    # Tab 7 — Drawing Tools & Interaction
    # =================================================================

    _draw_log = reactive.Value("")

    @reactive.Effect
    @reactive.event(input.draw_enable)
    async def _draw_enable():
        await draw_widget.enable_draw(session)
        _draw_log.set(
            _draw_log.get()
            + "\n✏️  Drawing enabled — use the toolbar on the map."
        )

    @reactive.Effect
    @reactive.event(input.draw_disable)
    async def _draw_disable():
        await draw_widget.disable_draw(session)
        _draw_log.set(_draw_log.get() + "\n❌  Drawing disabled.")

    @reactive.Effect
    @reactive.event(input.draw_get)
    async def _draw_get():
        await draw_widget.get_drawn_features(session)
        _draw_log.set(
            _draw_log.get() + "\n📋  Requesting drawn features…"
        )

    @reactive.Effect
    @reactive.event(input.draw_clear)
    async def _draw_clear():
        await draw_widget.delete_drawn_features(session)
        _draw_log.set(
            _draw_log.get() + "\n🗑️  All drawn features deleted."
        )

    # Show drawn features when they arrive
    @reactive.Effect
    @reactive.event(
        input[draw_widget.drawn_features_input_id],
    )
    def _draw_feat_arrived():
        data = input[draw_widget.drawn_features_input_id]()
        n = len(data.get("features", [])) if isinstance(data, dict) else 0
        pretty = json.dumps(data, indent=2)
        _draw_log.set(
            _draw_log.get()
            + f"\n📋  Drawn features updated — {n} feature(s):"
            + f"\n{pretty}"
        )

    # Draw mode change
    @reactive.Effect
    @reactive.event(input[draw_widget.draw_mode_input_id])
    def _draw_mode_changed():
        mode = input[draw_widget.draw_mode_input_id]()
        _draw_log.set(
            _draw_log.get()
            + f"\n🔧  Draw mode changed → {mode}"
        )

    # -- Markers & Popups -------------------------------------------------

    @reactive.Effect
    @reactive.event(input.add_port_markers)
    async def _add_port_markers():
        for p in PORTS[:5]:
            await draw_widget.add_marker(
                session,
                marker_id=p["name"],
                longitude=p["lon"],
                latitude=p["lat"],
                color="#14919b",
                draggable=True,
                popup_html=(
                    f"<b>{p['name']}</b> ({p['country']})"
                    f"<br/>Cargo: {p['cargo_mt']} Mt"
                ),
            )
        _draw_log.set(
            _draw_log.get()
            + "\n📍  Added 5 port markers (draggable, with popups)."
        )

    @reactive.Effect
    @reactive.event(input.clear_all_markers)
    async def _clear_markers():
        await draw_widget.clear_markers(session)
        _draw_log.set(_draw_log.get() + "\n🗑️  All markers cleared.")

    @reactive.Effect
    @reactive.event(input[draw_widget.marker_click_input_id])
    def _marker_clicked():
        data = input[draw_widget.marker_click_input_id]()
        _draw_log.set(
            _draw_log.get()
            + f"\n🖱️  Marker click: {data.get('markerId')} "
            + f"({data.get('longitude'):.4f}, {data.get('latitude'):.4f})"
        )

    @reactive.Effect
    @reactive.event(input[draw_widget.marker_drag_input_id])
    def _marker_dragged():
        data = input[draw_widget.marker_drag_input_id]()
        _draw_log.set(
            _draw_log.get()
            + f"\n🔄  Marker drag: {data.get('markerId')} → "
            + f"({data.get('longitude'):.4f}, {data.get('latitude'):.4f})"
        )

    # -- Spatial Query ----------------------------------------------------

    @reactive.Effect
    @reactive.event(input.query_center)
    async def _query_center():
        await draw_widget.query_rendered_features(
            session,
            point=[400, 300],
        )
        _draw_log.set(
            _draw_log.get()
            + "\n🔍  Querying features at map center…"
        )

    @reactive.Effect
    @reactive.event(input[draw_widget.query_result_input_id])
    def _query_result():
        data = input[draw_widget.query_result_input_id]()
        n = len(data) if isinstance(data, list) else 0
        _draw_log.set(
            _draw_log.get()
            + f"\n🔍  Query returned {n} feature(s)."
        )

    @render.text
    def draw_log():
        return _draw_log.get() or "Interaction log will appear here…"

    # =================================================================
    # Tab 8 — Animation (TripsLayer)
    # =================================================================

    _trips_data = make_trips_data(loop_length=1800)

    @reactive.Effect
    @reactive.event(
        input.anim_show_trips,
        input.anim_trail_length,
        input.anim_speed,
        input.anim_show_ports,
        input.anim_show_routes,
        input.anim_show_grid,
    )
    async def _anim_layers():
        layers: list[dict] = []

        # TripsLayer (animated)
        if input.anim_show_trips():
            layers.append(
                trips_layer(
                    "animated_trips",
                    _trips_data,
                    trailLength=input.anim_trail_length(),
                    getColor="@@d.color",
                    widthMinPixels=3,
                    _tripsAnimation={
                        "loopLength": 1800,
                        "speed": input.anim_speed(),
                    },
                )
            )

        # GreatCircleLayer (static route arcs)
        if input.anim_show_routes():
            gc_data = []
            for t in _trips_data:
                wps = [p[:2] for p in t["path"]]
                if len(wps) >= 2:
                    gc_data.append({
                        "sourcePosition": wps[0],
                        "targetPosition": wps[-1],
                        "name": t["name"],
                    })
            layers.append(
                great_circle_layer(
                    "gc_routes",
                    gc_data,
                    getSourceColor=[100, 100, 200, 120],
                    getTargetColor=[100, 100, 200, 120],
                    getWidth=1,
                )
            )

        # Ports ScatterplotLayer
        if input.anim_show_ports():
            port_data = [
                {
                    "position": [p["lon"], p["lat"]],
                    "name": p["name"],
                    "cargo_mt": p["cargo_mt"],
                }
                for p in PORTS
            ]
            layers.append(
                scatterplot_layer(
                    "anim_ports",
                    port_data,
                    getPosition="@@=d.position",
                    getRadius=6000,
                    getFillColor=[20, 145, 155, 200],
                    getLineColor=[255, 255, 255, 200],
                    lineWidthMinPixels=1,
                    stroked=True,
                    pickable=True,
                )
            )

        # Observation grid (GridLayer)
        if input.anim_show_grid():
            grid_points = [
                [p["lon"], p["lat"]]
                for p in PORTS
                for _ in range(int(p["cargo_mt"]))
            ]
            layers.append(
                grid_layer(
                    "anim_grid",
                    grid_points,
                    cellSize=30000,
                    elevationScale=200,
                    extruded=True,
                    pickable=False,
                    opacity=0.4,
                )
            )

        await anim_widget.update(session, layers)

    # =================================================================
    # Tab 9: v1.0.0 deck.gl Extensions
    # =================================================================

    _v1_port_data = [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "cargo_mt": p["cargo_mt"],
        }
        for p in PORTS
    ]

    @reactive.Effect
    @reactive.event(
        input.v1_brushing,
        input.v1_brush_radius,
        input.v1_data_filter,
        input.v1_filter_range,
    )
    async def _v1_layers():
        exts: list = []
        extra: dict = {}

        if input.v1_brushing():
            exts.append(brushing_extension())
            extra["brushingRadius"] = input.v1_brush_radius()
            extra["brushingEnabled"] = True

        if input.v1_data_filter():
            exts.append(data_filter_extension(filter_size=1))
            fmin, fmax = input.v1_filter_range()
            extra["getFilterValue"] = "@@d.cargo_mt"
            extra["filterRange"] = [fmin, fmax]
            extra["filterEnabled"] = True

        layers = [
            scatterplot_layer(
                "v1_ports",
                _v1_port_data,
                getPosition="@@=d.position",
                getRadius=8000,
                getFillColor=[20, 145, 155, 200],
                getLineColor=[255, 255, 255],
                lineWidthMinPixels=1,
                stroked=True,
                extensions=exts if exts else None,
                **extra,
            ),
        ]
        await v1_deck_widget.update(session, layers)

    # =================================================================
    # Tab 10: v1.0.0 MapLibre Features
    # =================================================================

    @reactive.Effect
    @reactive.event(input.v1_show_clusters, input.v1_cluster_radius)
    async def _v1_clusters():
        if input.v1_show_clusters():
            await v1_ml_widget.add_cluster_layer(
                session,
                "v1-clusters",
                make_port_geojson(),
                cluster_radius=input.v1_cluster_radius(),
                cluster_color="#14919b",
                point_color="#e65100",
                point_radius=6,
            )
        else:
            await v1_ml_widget.remove_cluster_layer(session, "v1-clusters")

    @reactive.Effect
    @reactive.event(input.v1_cooperative)
    async def _v1_cooperative():
        await v1_ml_widget.set_cooperative_gestures(
            session, input.v1_cooperative()
        )

    # =================================================================
    # Tab 11: 3-D Visualisation
    # =================================================================

    # Pre-generate data (constant for the session)
    _bathy_grid = make_bathymetry_grid()
    _fish_obs = make_fish_observations()
    _arc_3d = make_3d_arc_data()

    @reactive.Effect
    @reactive.event(
        input.td_bathy, input.td_bathy_elev, input.td_bathy_wireframe,
        input.td_fish, input.td_fish_mode, input.td_fish_elev,
        input.td_arcs, input.td_arc_width,
        input.td_lighting, input.td_ambient, input.td_point_light,
        input.td_pitch, input.td_bearing,
    )
    async def _td_rebuild():
        layers: list[dict] = []

        # --- Bathymetry columns ---
        if input.td_bathy():
            bathy_data = [
                {
                    **pt,
                    "color": _bathy_color(pt["elevation"]),
                }
                for pt in _bathy_grid
            ]
            layers.append(
                column_layer(
                    "td-bathy",
                    data=bathy_data,
                    getPosition="@@=d.position",
                    getElevation="@@=d.elevation",
                    getFillColor="@@=d.color",
                    elevationScale=input.td_bathy_elev(),
                    diskResolution=6,
                    radius=12000,
                    extruded=True,
                    wireframe=input.td_bathy_wireframe(),
                    pickable=True,
                    opacity=0.85,
                ),
            )

        # --- Fish observations ---
        if input.td_fish():
            mode = input.td_fish_mode()
            if mode == "hexagon":
                fish_positions = [
                    pt["position"] for pt in _fish_obs
                ]
                layers.append(
                    hexagon_layer(
                        "td-fish-hex",
                        data=fish_positions,
                        getPosition="@@=d",
                        elevationScale=input.td_fish_elev() * 100,
                        radius=25000,
                        extruded=True,
                        pickable=True,
                        colorRange=[
                            [255, 255, 178],
                            [254, 204, 92],
                            [253, 141, 60],
                            [240, 59, 32],
                            [189, 0, 38],
                        ],
                        opacity=0.7,
                    ),
                )
            else:
                fish_data = [
                    {
                        **pt,
                        "color": _species_color(pt["species"]),
                    }
                    for pt in _fish_obs
                ]
                layers.append(
                    column_layer(
                        "td-fish-col",
                        data=fish_data,
                        getPosition="@@=d.position",
                        getElevation="@@=d.elevation",
                        getFillColor="@@=d.color",
                        elevationScale=input.td_fish_elev() * 100,
                        diskResolution=8,
                        radius=8000,
                        extruded=True,
                        pickable=True,
                        opacity=0.8,
                    ),
                )

        # --- 3-D arcs ---
        if input.td_arcs():
            layers.append(
                arc_layer(
                    "td-arcs",
                    data=_arc_3d,
                    getSourcePosition="@@=d.sourcePosition",
                    getTargetPosition="@@=d.targetPosition",
                    getSourceColor="@@=d.sourceColor",
                    getTargetColor="@@=d.targetColor",
                    getHeight="@@=d.height",
                    getWidth=input.td_arc_width(),
                    pickable=True,
                ),
            )

        # --- Lighting ---
        effects = None
        if input.td_lighting():
            effects = _make_lighting_effects(
                input.td_ambient(), input.td_point_light(),
            )

        await three_d_widget.update(session, layers, effects=effects)

        # Fly to the current pitch / bearing
        await three_d_widget.fly_to(
            session,
            longitude=19.5,
            latitude=57.0,
            zoom=5,
            pitch=input.td_pitch(),
            bearing=input.td_bearing(),
        )

    # -- colour helpers (pure functions, no I/O) --

    def _bathy_color(elevation: float) -> list[int]:
        """Map depth (0–459 m) to a blue-gradient RGBA."""
        t = min(elevation / 459.0, 1.0)
        r = int(10 + 40 * (1 - t))
        g = int(60 + 120 * (1 - t))
        b = int(120 + 135 * t)
        return [r, g, b, 210]

    _SPECIES_COLORS: dict[str, list[int]] = {
        "Atlantic cod":       [230, 25, 75, 200],
        "Baltic herring":     [60, 180, 75, 200],
        "European sprat":     [255, 225, 25, 200],
        "Atlantic salmon":    [0, 130, 200, 200],
        "European flounder":  [245, 130, 48, 200],
        "Pike-perch":         [145, 30, 180, 200],
        "Three-spined stickleback": [70, 240, 240, 200],
        "Ringed seal":        [240, 50, 230, 200],
    }

    def _species_color(species: str) -> list[int]:
        return _SPECIES_COLORS.get(species, [180, 180, 180, 200])

    # =================================================================
    # Tab 12 — Seal IBM (Individual-Based Model)
    # =================================================================

    _SEAL_LOOP = 600
    _seal_haulout_data = make_seal_haulout_data()
    _seal_foraging_geojson = make_seal_foraging_areas()

    # Play / Pause / Reset + speed & trail via reusable module
    seal_anim = trips_animation_server(
        "seal_anim", widget=seal_widget, session=session,
    )

    @reactive.Calc
    def _seal_trips():
        """Regenerate trips when model type or parameters change."""
        model = input.seal_model_type()
        n = input.seal_n_individuals()
        if model == "mcconnell":
            sim_h = input.seal_sim_hours()
            return make_seal_trips_ibm(
                n_seals=n,
                sim_hours=sim_h,
                loop_length=_SEAL_LOOP,
            )
        return make_seal_trips(
            n_seals=n,
            loop_length=_SEAL_LOOP,
        )

    @reactive.Effect
    @reactive.event(
        input.seal_model_type,
        input.seal_n_individuals,
        input.seal_sim_hours,
        input.seal_species,
        seal_anim.speed,
        seal_anim.trail,
        input.seal_bathymetry,
        input.seal_haulouts,
        input.seal_foraging,
    )
    async def _seal_layers():
        selected = set(input.seal_species())
        trips = _seal_trips()
        layers: list[dict] = []

        # EMODnet bathymetry WMS underlay (deck.gl native WMSLayer)
        if input.seal_bathymetry():
            layers.append(wms_layer(
                "seal-bathymetry-wms",
                EMODNET_WMS_URL,
                layers=["emodnet:mean_atlas_land"],
            ))

        # Foraging area ellipses (below tracks)
        if input.seal_foraging():
            filtered_features = [
                f for f in _seal_foraging_geojson["features"]
                if f["properties"]["species"] in selected
            ]
            if filtered_features:
                foraging_geojson = {
                    "type": "FeatureCollection",
                    "features": filtered_features,
                }
                layers.append(
                    geojson_layer(
                        "seal_foraging_areas",
                        foraging_geojson,
                        getFillColor=[100, 180, 220, 40],
                        getLineColor=[80, 140, 200, 100],
                        lineWidthMinPixels=1,
                        stroked=True,
                        filled=True,
                    )
                )

        # Animated seal tracks (TripsLayer) with head icons
        filtered_trips = [t for t in trips if t["species"] in selected]
        if filtered_trips:
            layers.append(
                trips_layer(
                    "seal_trips",
                    filtered_trips,
                    trailLength=seal_anim.trail(),
                    getColor="@@d.color",
                    widthMinPixels=3,
                    _tripsAnimation={
                        "loopLength": _SEAL_LOOP,
                        "speed": seal_anim.speed(),
                    },
                    _tripsHeadIcons={
                        "iconAtlas": ICON_ATLAS,
                        "iconMapping": ICON_MAPPING,
                        "iconField": "species",
                        "getSize": 24,
                        "sizeScale": 1,
                        "sizeMinPixels": 10,
                        "sizeMaxPixels": 64,
                    },
                )
            )

        # Haul-out colony markers
        if input.seal_haulouts():
            filtered_haulouts = [
                h for h in _seal_haulout_data
                if h["species"] in selected
            ]
            if filtered_haulouts:
                layers.append(
                    scatterplot_layer(
                        "seal_haulouts",
                        filtered_haulouts,
                        getPosition="@@=d.position",
                        getRadius="@@=d.radius * 800",
                        getFillColor="@@d.color",
                        getLineColor=[255, 255, 255, 200],
                        lineWidthMinPixels=2,
                        stroked=True,
                        pickable=True,
                    )
                )

        await seal_widget.update(
            session, layers,
            widgets=[loading_widget()],
        )

    # ===================================================================
    # Tab 13: Widgets Gallery
    # ===================================================================

    _wg_log: reactive.Value[str] = reactive.Value("")

    # -- Reactive: build widget list from toggles -----------------------

    @reactive.Calc
    def _wg_active_widgets() -> list[dict]:
        """Assemble the active widget list from all toggle switches."""
        widgets: list[dict] = []
        # Standard widgets (v0.8.0)
        if input.wg_zoom():
            widgets.append(zoom_widget())
        if input.wg_compass():
            widgets.append(compass_widget())
        if input.wg_gimbal():
            widgets.append(gimbal_widget())
        if input.wg_reset_view():
            widgets.append(reset_view_widget())
        if input.wg_fullscreen():
            widgets.append(fullscreen_widget())
        if input.wg_scale():
            widgets.append(scale_widget())
        if input.wg_screenshot():
            widgets.append(screenshot_widget(filename="shiny-deckgl-capture"))
        if input.wg_fps():
            widgets.append(fps_widget())
        if input.wg_loading():
            widgets.append(loading_widget(label="Loading layers\u2026"))
        if input.wg_theme():
            widgets.append(theme_widget())
        if input.wg_timeline():
            widgets.append(timeline_widget(min=0, max=1000, step=10))
        if input.wg_geocoder():
            widgets.append(geocoder_widget(placeholder="Search location\u2026"))
        # Experimental widgets (v9.2+)
        if input.wg_context_menu():
            widgets.append(context_menu_widget(items=[
                {"label": "Copy coordinates"},
                {"label": "Zoom to 100%"},
                {"label": "Reset view"},
            ]))
        if input.wg_info():
            widgets.append(info_widget(
                placement="top-left",
                text="Hover over features for details",
            ))
        if input.wg_splitter():
            widgets.append(splitter_widget(orientation="vertical"))
        if input.wg_stats():
            widgets.append(stats_widget(
                placement="bottom-left",
                framesPerUpdate=60,
            ))
        if input.wg_view_selector():
            widgets.append(view_selector_widget(initialViewMode="map"))
        return widgets

    # -- Reactive: build layer list from dropdown -----------------------

    @reactive.Calc
    def _wg_layers() -> list[dict]:
        """Build layer for the selected scenario."""
        choice = input.wg_layer_combo()
        if choice == "ports":
            return [scatterplot_layer(
                "wg-ports",
                _port_data_simple,
                getPosition="@@=d.position",
                getRadius="@@=d.cargo_mt * 80",
                getFillColor=[20, 130, 180, 180],
                radiusMinPixels=4,
                radiusMaxPixels=30,
                pickable=True,
            )]
        elif choice == "heatmap":
            return [heatmap_layer(
                "wg-heat",
                _heatmap_points,
                getPosition="@@=d.position",
                getWeight="@@=d.weight || 1",
                radiusPixels=40,
                intensity=1.2,
                threshold=0.05,
            )]
        elif choice == "arcs":
            return [arc_layer(
                "wg-arcs",
                _arc_data,
                getSourcePosition="@@=d.from",
                getTargetPosition="@@=d.to",
                getSourceColor=[0, 128, 255],
                getTargetColor=[255, 100, 0],
                getWidth=2,
                pickable=True,
            )]
        elif choice == "routes":
            return [path_layer(
                "wg-routes",
                _path_data,
                getPath="@@=d.path",
                getColor="@@=d.color",
                widthMinPixels=2,
                pickable=True,
            )]
        elif choice == "3d_columns":
            return [column_layer(
                "wg-columns",
                _port_data_simple,
                getPosition="@@=d.position",
                getElevation="@@=d.cargo_mt * 500",
                getFillColor=[14, 145, 155, 200],
                radius=8000,
                elevationScale=1,
                extruded=True,
                pickable=True,
            )]
        elif choice == "hexagons":
            return [hexagon_layer(
                "wg-hexagons",
                _heatmap_points,
                getPosition="@@=d.position",
                radius=20000,
                elevationScale=50,
                extruded=True,
                pickable=True,
            )]
        return []

    # -- Push widgets + layers to the map --------------------------------

    @reactive.Effect
    @reactive.event(
        input.wg_zoom, input.wg_compass, input.wg_gimbal,
        input.wg_reset_view, input.wg_fullscreen, input.wg_scale,
        input.wg_screenshot, input.wg_fps, input.wg_loading,
        input.wg_theme, input.wg_timeline, input.wg_geocoder,
        input.wg_context_menu, input.wg_info, input.wg_splitter,
        input.wg_stats, input.wg_view_selector,
        input.wg_layer_combo,
    )
    async def _wg_update_map():
        widgets = _wg_active_widgets()
        layers = _wg_layers()
        await widgets_gallery_widget.update(
            session, layers, widgets=widgets,
        )
        # Update status console
        names = [w["@@widgetClass"] for w in widgets]
        standard = [n for n in names if not n.startswith("_") or n in (
            "_ScaleWidget", "_FpsWidget", "_LoadingWidget",
            "_TimelineWidget", "_GeocoderWidget", "_ThemeWidget",
        )]
        experimental = [n for n in names if n in (
            "_ContextMenuWidget", "_InfoWidget", "_SplitterWidget",
            "_StatsWidget", "_ViewSelectorWidget",
        )]
        status_lines = [
            f"Active widgets: {len(widgets)} / 17",
            f"Layer: {input.wg_layer_combo()}",
            "",
        ]
        if standard:
            status_lines.append("Standard:")
            status_lines.extend(f"  \u2022 {n}" for n in standard)
        if experimental:
            status_lines.append("Experimental (v9.2+):")
            status_lines.extend(f"  \u2022 {n}" for n in experimental)
        if not names:
            status_lines.append("  (no widgets active)")
        _wg_log.set("\n".join(status_lines))

    @render.text
    def wg_status():
        return (
            _wg_log.get()
            or "Toggle widgets in the sidebar to see them on the map."
        )

    # -- Preset buttons --------------------------------------------------

    @reactive.Effect
    @reactive.event(input.wg_preset_nav)
    async def _wg_preset_nav():
        """Navigation preset: zoom, compass, scale, fullscreen, reset."""
        await _wg_apply_preset(
            zoom=True, compass=True, scale=True,
            fullscreen=True, reset_view=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_debug)
    async def _wg_preset_debug():
        """Debug preset: FPS, stats, info, loading."""
        await _wg_apply_preset(
            fps=True, stats=True, info=True, loading=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_presentation)
    async def _wg_preset_presentation():
        """Presentation: fullscreen, screenshot, theme, scale."""
        await _wg_apply_preset(
            fullscreen=True, screenshot=True, theme=True, scale=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_all)
    async def _wg_preset_all():
        """Turn on every widget."""
        await _wg_apply_preset(
            zoom=True, compass=True, gimbal=True, reset_view=True,
            fullscreen=True, scale=True, screenshot=True, fps=True,
            loading=True, theme=True, timeline=True, geocoder=True,
            context_menu=True, info=True, splitter=True, stats=True,
            view_selector=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_none)
    async def _wg_preset_none():
        """Turn off all widgets."""
        await _wg_apply_preset()

    async def _wg_apply_preset(
        zoom=False, compass=False, gimbal=False, reset_view=False,
        fullscreen=False, scale=False, screenshot=False, fps=False,
        loading=False, theme=False, timeline=False, geocoder=False,
        context_menu=False, info=False, splitter=False, stats=False,
        view_selector=False,
    ):
        """Set all widget toggles to the given preset values."""
        ui.update_switch("wg_zoom", value=zoom)
        ui.update_switch("wg_compass", value=compass)
        ui.update_switch("wg_gimbal", value=gimbal)
        ui.update_switch("wg_reset_view", value=reset_view)
        ui.update_switch("wg_fullscreen", value=fullscreen)
        ui.update_switch("wg_scale", value=scale)
        ui.update_switch("wg_screenshot", value=screenshot)
        ui.update_switch("wg_fps", value=fps)
        ui.update_switch("wg_loading", value=loading)
        ui.update_switch("wg_theme", value=theme)
        ui.update_switch("wg_timeline", value=timeline)
        ui.update_switch("wg_geocoder", value=geocoder)
        ui.update_switch("wg_context_menu", value=context_menu)
        ui.update_switch("wg_info", value=info)
        ui.update_switch("wg_splitter", value=splitter)
        ui.update_switch("wg_stats", value=stats)
        ui.update_switch("wg_view_selector", value=view_selector)


app = App(app_ui, server)
