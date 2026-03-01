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
    # v0.7.0 layer helpers
    arc_layer,
    column_layer,
    heatmap_layer,
    path_layer,
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
    fps_widget,
    # v0.8.0 transitions
    transition,
    # MapLibre control helpers
    geolocate_control,
    globe_control,
    terrain_control,
    # Third-party MapLibre plugin controls
    legend_control,
    opacity_control,
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
)
from ._demo_css import MARINE_CSS, sidebar_hint

from .components import CARTO_POSITRON, PALETTE_OCEAN
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
                ui.accordion(
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
                        ui.input_switch("ml_terrain",
                                        "TerrainControl", value=False),
                    ),
                    ui.accordion_panel(
                        "\U0001F4DC Legend Plugin",
                        sidebar_hint(
                            "watergis/maplibre-gl-legend — auto-generates "
                            "a legend panel from the MapLibre style. "
                            "Toggle layer visibility with checkboxes."
                        ),
                        ui.input_switch("ml_legend",
                                        "Legend panel", value=True),
                        ui.input_switch("ml_legend_checkbox",
                                        "Show checkboxes", value=True),
                        ui.input_switch("ml_legend_default",
                                        "Open by default", value=False),
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
                        ui.input_switch("adv_zoom_widget",
                                        "Zoom widget", value=False),
                        ui.input_switch("adv_compass_widget",
                                        "Compass widget", value=False),
                        ui.input_switch("adv_fps_widget",
                                        "FPS widget", value=False),
                        ui.input_switch("adv_fullscreen_widget",
                                        "Fullscreen widget", value=False),
                        ui.input_switch("adv_scale_widget",
                                        "Scale widget", value=False),
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

    # =================================================================
    # Tab 1 — deck.gl Layers
    # =================================================================

    def _build_main_layers() -> list[dict]:
        """Build the layer stack for the main interactive map."""
        layers: list[dict] = []
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)
        cargo_values = [p["cargo_mt"] for p in PORTS]

        mode = input.color_mode()
        if mode == "Equal-width bins":
            port_colors = color_bins(cargo_values, 6, palette)
        elif mode == "Quantile bins":
            port_colors = color_quantiles(cargo_values, 6, palette)
        else:
            port_colors = color_range(len(PORTS), palette)

        # WMS tile layer (EMODnet bathymetry)
        wms_layer_name = input.wms_layer()
        if wms_layer_name:
            wms_url = (
                f"{EMODNET_WMS_URL}?"
                "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
                "&FORMAT=image/png&TRANSPARENT=true"
                f"&LAYERS={wms_layer_name}"
                "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
                "&BBOX={{bbox-epsg-3857}}"
            )
            safe_id = wms_layer_name.replace(":", "_")
            layers.append(tile_layer(f"wms-{safe_id}", wms_url))

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
                data=make_heatmap_points(300),
                getPosition="@@d",
                getWeight="@@=d[2]",
                radiusPixels=40, intensity=1.5, threshold=0.1,
            ))

        # Paths — shipping routes as polylines
        if input.show_paths():
            layers.append(path_layer(
                "route-paths",
                data=make_path_data(),
                getPath="@@=d.path",
                getColor="@@=d.color",
                getWidth=3, widthMinPixels=2, pickable=True,
            ))

        # Arcs — connections between ports
        if input.show_routes():
            layers.append(arc_layer(
                "port-arcs",
                data=make_arc_data(),
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

    # Initial push (with widgets)
    @reactive.Effect
    async def _main_init():
        layers = _build_main_layers()
        _main_layers.set(layers)
        await map_widget.update(session, layers, widgets=MAP_WIDGETS)

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

    # Layer visibility toggle
    @reactive.Effect
    @reactive.event(input.show_ports)
    async def _toggle_ports():
        await map_widget.set_layer_visibility(
            session, {"ports": input.show_ports()},
        )

    @reactive.Effect
    @reactive.event(input.show_mpa)
    async def _toggle_mpa():
        await map_widget.set_layer_visibility(
            session, {"mpa-zones": input.show_mpa()},
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

    @reactive.Effect
    async def _ml_init():
        """Push initial layers + controls to the MapLibre tab."""
        layers = [
            geojson_layer(
                "ml-mpa", MPA_GEOJSON,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
                pickable=True,
            ),
            scatterplot_layer(
                "ml-ports", make_port_data_simple(),
                getPosition="@@=d.position",
                getFillColor=[0, 140, 200, 200],
                radiusMinPixels=7,
                radiusMaxPixels=20,
                pickable=True,
            ),
        ]
        controls = _build_ml_controls()
        await maplibre_widget.update(session, layers)
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
                position="bottom-left",
                show_default=input.ml_legend_default(),
                show_checkbox=input.ml_legend_checkbox(),
            ))
        if input.ml_opacity():
            ctrls.append(opacity_control(position="top-left"))
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

    # Basemap switching
    @reactive.Effect
    @reactive.event(input.ml_basemap)
    async def _ml_switch_basemap():
        style_url = BASEMAP_CHOICES.get(
            input.ml_basemap(), CARTO_POSITRON,
        )
        await maplibre_widget.set_style(session, style_url)

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
                data=make_arc_data(),
                getSourcePosition="@@=d.sourcePosition",
                getTargetPosition="@@=d.targetPosition",
                getSourceColor="@@=d.sourceColor",
                getTargetColor="@@=d.targetColor",
                getWidth=2, pickable=True,
            ),
            scatterplot_layer(
                "ev-ports", make_port_data_simple(),
                getPosition="@@=d.position",
                getFillColor=[200, 0, 80, 180],
                radiusMinPixels=8, pickable=True,
            ),
        ]
        await events_widget.update(session, layers)

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

    # Lighting
    @reactive.Effect
    @reactive.event(
        input.enable_lighting, input.ambient, input.point_intensity,
    )
    async def _apply_lighting():
        layers = _adv_layers.get()
        effects = None
        if input.enable_lighting():
            effects = [{
                "type": "LightingEffect",
                "ambientLight": {
                    "color": [255, 255, 255],
                    "intensity": input.ambient(),
                },
                "pointLights": [{
                    "color": [255, 255, 220],
                    "intensity": input.point_intensity(),
                    "position": [19.5, 57.0, 80000],
                }],
            }]
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
    @reactive.Effect
    @reactive.event(input.push_filtered)
    async def _push_filtered():
        max_cargo = input.filter_value()
        filtered_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "filterValue": p["cargo_mt"],
            }
            for p in PORTS
        ]
        filtered_lyr = layer(
            "ScatterplotLayer", "filtered-ports",
            data=filtered_data,
            getPosition="@@=d.position",
            getFillColor=[255, 200, 0, 220],
            getRadius=8, radiusScale=1000, radiusMinPixels=20,
            pickable=True,
            extensions=["DataFilterExtension"],
            getFilterValue="@@=d.filterValue",
            filterRange=[0, max_cargo],
            parameters={"depthCompare": "always"},
        )
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
        filtered_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "filterValue": p["cargo_mt"],
            }
            for p in PORTS
        ]
        filtered_lyr = layer(
            "ScatterplotLayer", "filtered-ports",
            data=filtered_data,
            getPosition="@@=d.position",
            getFillColor=[255, 200, 0, 220],
            getRadius=8, radiusScale=1000, radiusMinPixels=20,
            pickable=True,
            extensions=["DataFilterExtension"],
            getFilterValue="@@=d.filterValue",
            filterRange=[0, max_cargo],
            parameters={"depthCompare": "always"},
        )
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

    # Widgets toggle (v0.8.0)
    @reactive.Effect
    @reactive.event(
        input.adv_zoom_widget, input.adv_compass_widget,
        input.adv_fps_widget, input.adv_fullscreen_widget,
        input.adv_scale_widget,
    )
    async def _toggle_adv_widgets():
        widgets: list[dict] = []
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


app = App(app_ui, server)
