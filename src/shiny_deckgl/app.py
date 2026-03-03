"""Comprehensive shiny_deckgl demo — showcases every feature of the library.

Run with:
    shiny run shiny_deckgl.app:app --port 19876

Tabs (10):
  1. deck.gl Layers    – all 24 typed layer helpers with Baltic Sea sample
                          data, toggle each on/off, basemap + navigation
  2. MapLibre Controls  – basemap switching, navigation, geolocate,
                          globe, terrain, legend, opacity controls,
                          GeoJSON clustering, cooperative gestures
  3. Events & Tooltips  – live click/hover/viewport readback, drag marker,
                          dynamic tooltip customisation
  4. Colour Scales      – palette swatches, color_range, color_bins,
                          color_quantiles, interactive colour-mapped
                          bathymetry columns / scatter / heatmap
  5. Advanced           – 3-D column map with lighting, binary transport,
                          DataFilterExtension, BrushingExtension, transitions
  6. Export             – standalone HTML export, JSON round-trip
  7. Drawing            – MapboxDraw tools (point/line/polygon), markers
                          with popups, spatial query, interaction logging
  8. 3-D Visualisation  – bathymetry columns, fish observations, 3-D arcs,
                          lighting (ambient, point, directional),
                          post-processing (brightness/contrast),
                          camera pitch/bearing
  9. Seal IBM           – Individual-Based Model of Baltic seal movement,
                          animated foraging trips from haul-out colonies,
                          TripsLayer animation, GreatCircleLayer, GridLayer
 10. Widgets Gallery    – Interactive showcase of all 17 deck.gl widgets,
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
    bitmap_layer,
    wms_layer,
    point_cloud_layer,
    simple_mesh_layer,
    terrain_layer,
    # v0.7.0 layer helpers
    arc_layer,
    icon_layer,
    column_layer,
    heatmap_layer,
    path_layer,
    line_layer,
    text_layer,
    polygon_layer,
    # v0.9.0 layer helpers
    trips_layer,
    great_circle_layer,
    contour_layer,
    grid_layer,
    screen_grid_layer,
    hexagon_layer,
    h3_hexagon_layer,
    mvt_layer,
    # Color utilities
    # (color_range, color_bins, color_quantiles available in library)
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

from .effects import (
    ambient_light,
    point_light,
    directional_light,
    sun_light,
    lighting_effect,
    post_process_effect,
)

from .colors import (
    color_range,
    color_bins,
    color_quantiles,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
)

from ._demo_data import (
    PORTS,
    ROUTES,
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
    SHYFEM_VIEW,
    make_h3_data,
    make_point_cloud_data,
    make_shyfem_polygon_data,
    make_shyfem_mesh_data,
    # Mesh file paths
    CURONIAN_GRD_PATH as _CURONIAN_GRD_STR,
    POLYGON_GRD_PATH as _POLYGON_GRD_STR,
    # Fish species colours
    fish_species_color as _species_color,
    # Gallery data factories
    make_gallery_port_data,
    make_gallery_arc_data,
    make_gallery_line_data,
    make_gallery_path_data,
    make_gallery_text_data,
    make_gallery_icon_data,
    make_gallery_column_data,
    # Legend metadata
    LAYER_LEGEND_META,
    # Seal IBM
    make_seal_trips,
    make_seal_trips_ibm,
    make_seal_haulout_data,
    make_seal_foraging_areas,
)
from .ibm import ICON_ATLAS, ICON_MAPPING, trips_animation_ui, trips_animation_server
from .colors import depth_color as _bathy_color
from ._demo_css import MARINE_CSS, sidebar_hint, about_row as _about_row

from .components import CARTO_POSITRON
from .layers import custom_geometry
from .extensions import (
    brushing_extension,
    data_filter_extension,
)
from ._version import __version__ as SHINY_DECKGL_VERSION
from ._version import python_version as _python_version
from ._version import shiny_version as _shiny_version
from ._cdn import (
    DECKGL_VERSION,
    MAPLIBRE_VERSION,
    MAPBOX_DRAW_VERSION,
    MAPLIBRE_LEGEND_VERSION,
    MAPLIBRE_OPACITY_VERSION,
)


# ---------------------------------------------------------------------------
# Map widget instances — one per tab that needs a map
# ---------------------------------------------------------------------------

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

# ===========================================================================
# UI layout
# ===========================================================================

app_ui = ui.page_navbar(
    head_includes(),

    # -- Tab 1: deck.gl Layers (gallery — all 24 layer helpers) ---------
    ui.nav_panel(
        "\U0001F30A deck.gl Layers",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small(
                    "24 layer helpers",
                    class_="badge text-bg-success mb-2",
                ),
                sidebar_hint(
                    "Toggle each layer type to see it on the map. "
                    "All 24 typed helper functions from "
                    "shiny_deckgl.layers are demonstrated here "
                    "with Baltic Sea sample data."
                ),
                ui.accordion(
                    # -- Basemap ------------------------------------------
                    ui.accordion_panel(
                        "\u2693 Basemap",
                        ui.input_select(
                            "basemap", "Basemap style",
                            choices=list(BASEMAP_CHOICES.keys()),
                        ),
                    ),
                    # -- Core layers --------------------------------------
                    ui.accordion_panel(
                        "\U0001F7E2 Core Layers",
                        ui.tooltip(
                            ui.input_switch(
                                "gl_scatterplot", "ScatterplotLayer",
                                value=True,
                            ),
                            "deck.gl \u2014 Renders circles at geographic "
                            "positions. Use for: sensor stations, port "
                            "locations, point observations. "
                            "\U0001F4E6 Data: generated (Baltic ports).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_geojson", "GeoJsonLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders GeoJSON Features "
                            "(points, lines, polygons). Use for: EEZ "
                            "boundaries, coastline outlines, survey areas. "
                            "\U0001F30A Source: HELCOM Marine Protected Areas "
                            "(bundled GeoJSON).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_arc", "ArcLayer", value=False,
                            ),
                            "deck.gl \u2014 Draws raised arcs between "
                            "origin/destination pairs. Use for: ship "
                            "routes, trade flows, migration paths. "
                            "\U0001F4E6 Data: generated (shipping routes).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_line", "LineLayer", value=False,
                            ),
                            "deck.gl \u2014 Draws flat straight lines "
                            "between two points. Use for: simple "
                            "connections, distance indicators. "
                            "\U0001F4E6 Data: generated (port pairs).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_path", "PathLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders polylines from lists "
                            "of coordinates. Use for: vessel tracks, "
                            "survey transects, pipeline routes. "
                            "\U0001F4E6 Data: generated (route waypoints).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_icon", "IconLayer", value=False,
                            ),
                            "deck.gl \u2014 Places raster icons at "
                            "positions. Use for: port markers, buoy "
                            "symbols, categorical map pins. "
                            "\U0001F4E6 Data: generated (port locations).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_text", "TextLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders text labels at "
                            "positions. Use for: port names, station "
                            "IDs, annotation overlays. "
                            "\U0001F4E6 Data: generated (port names).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_column", "ColumnLayer", value=False,
                            ),
                            "deck.gl \u2014 Draws extruded cylinders at "
                            "positions. Use for: cargo volumes, depth "
                            "values, 3-D bar charts on a map. "
                            "\U0001F4E6 Data: generated (cargo tonnage).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_polygon", "PolygonLayer", value=False,
                            ),
                            "deck.gl \u2014 Fills and strokes arbitrary "
                            "polygons. Use for: finite-element model grids, "
                            "habitat zones, administrative regions. "
                            "\U0001F30A Source: SHYFEM model grid "
                            "(MM_coarse_smooth.grd \u2014 Mar Piccolo) / "
                            "generated (port bounding boxes).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_great_circle", "GreatCircleLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Draws great-circle arcs "
                            "following Earth curvature. Use for: "
                            "intercontinental routes, long-range links. "
                            "\U0001F4E6 Data: generated (route endpoints).",
                        ),
                    ),
                    # -- Aggregation layers --------------------------------
                    ui.accordion_panel(
                        "\U0001F4CA Aggregation Layers",
                        ui.tooltip(
                            ui.input_switch(
                                "gl_heatmap", "HeatmapLayer", value=False,
                            ),
                            "deck.gl \u2014 Gaussian kernel density "
                            "heatmap. Use for: AIS density, species "
                            "sighting hotspots, pollution intensity. "
                            "\U0001F4E6 Data: generated (random points).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_hexagon", "HexagonLayer", value=False,
                            ),
                            "deck.gl \u2014 Aggregates points into "
                            "hexagonal bins (3-D). Use for: catch "
                            "statistics, traffic density, spatial binning. "
                            "\U0001F4E6 Data: generated (random points).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_grid", "GridLayer", value=False,
                            ),
                            "deck.gl \u2014 Aggregates points into a "
                            "regular grid. Use for: trawl density, "
                            "sampling grid, rectangular spatial stats. "
                            "\U0001F4E6 Data: generated (random points).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_screen_grid", "ScreenGridLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Screen-space grid heatmap "
                            "(bins resize on zoom). Use for: real-time "
                            "density overview, quick point clustering. "
                            "\U0001F4E6 Data: generated (random points).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_contour", "ContourLayer", value=False,
                            ),
                            "deck.gl \u2014 Generates contour lines / "
                            "filled bands from point data. Use for: "
                            "isotherms, depth contours, isobars. "
                            "\U0001F4E6 Data: generated (random points).",
                        ),
                    ),
                    # -- Geo-spatial layers --------------------------------
                    ui.accordion_panel(
                        "\U0001F30D Geo-spatial Layers",
                        ui.tooltip(
                            ui.input_switch(
                                "gl_h3_hexagon", "H3HexagonLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders Uber\u2019s H3 "
                            "hexagonal cells by index. Use for: H3-"
                            "indexed oceanographic grids, spatial "
                            "aggregation at multiple resolutions. "
                            "\U0001F4E6 Data: generated (H3 res-5 cells, Klaip\u0117da).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_trips", "TripsLayer", value=False,
                            ),
                            "deck.gl \u2014 Animates timestamped paths "
                            "with a fading trail. Use for: vessel track "
                            "playback, drifter trajectories, AIS replay. "
                            "\U0001F4E6 Data: generated (synthetic tracks).",
                        ),
                    ),
                    # -- Tile / raster layers ------------------------------
                    ui.accordion_panel(
                        "\U0001F5FA Tile & Raster Layers",
                        ui.tooltip(
                            ui.input_switch(
                                "gl_tile", "TileLayer (OSM)", value=False,
                            ),
                            "deck.gl \u2014 Loads XYZ / TMS raster tiles "
                            "on demand. Use for: custom basemaps, "
                            "satellite imagery, cached tile services. "
                            "\U0001F310 Source: OpenStreetMap tile server.",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_bitmap", "BitmapLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders a single image "
                            "anchored to geo bounds. Use for: charts, "
                            "georeferenced photos, static overlays. "
                            "\U0001F310 Source: Wikimedia (Baltic Sea map).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_mvt", "MVTLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders Mapbox Vector Tiles "
                            "from a tile endpoint. Use for: large "
                            "vector datasets, OpenMapTiles, Tippecanoe. "
                            "\U0001F310 Source: Stadia Maps (OpenMapTiles).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_wms", "WMSLayer (EMODnet)",
                                value=False,
                            ),
                            "deck.gl \u2014 Fetches OGC WMS GetMap "
                            "images as map tiles. Use for: EMODnet "
                            "bathymetry, HELCOM layers, INSPIRE services. "
                            "\U0001F310 Source: EMODnet WMS service.",
                        ),
                    ),
                    # -- 3D / mesh layers ----------------------------------
                    ui.accordion_panel(
                        "\U0001F4D0 3-D / Mesh Layers",
                        ui.tooltip(
                            ui.input_switch(
                                "gl_point_cloud", "PointCloudLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders a cloud of 3-D "
                            "points. Use for: LiDAR scans, multibeam "
                            "sonar, 3-D scatter data. "
                            "\U0001F4E6 Data: generated (synthetic rings).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_simple_mesh", "SimpleMeshLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders the mesh surface "
                            "with depth-coloured vertex nodes overlaid. "
                            "Use for: bathymetric surfaces, finite-element "
                            "model results, engineering meshes. "
                            "\U0001F30A Mesh: Curonian Lagoon "
                            "(curoninan.grd \u2014 98\u202Fk nodes, "
                            "143\u202Fk triangles).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_terrain", "TerrainLayer", value=False,
                            ),
                            "deck.gl \u2014 Reconstructs mesh surfaces "
                            "from raster elevation tiles. Use for: "
                            "seabed bathymetry, terrain visualization. "
                            "\U0001F310 Source: AWS Terrain Tiles + OSM.",
                        ),
                    ),
                    # -- Navigation ---------------------------------------
                    ui.accordion_panel(
                        "\u2708 Navigation",
                        ui.input_action_button("fly_klaipeda",
                                               "\u2708 Fly to Klaip\u0117da"),
                        ui.input_action_button("ease_stockholm",
                                               "\u27A1 Ease to Stockholm"),
                        ui.input_action_button("fly_baltic",
                                               "\U0001F30D Reset Baltic view"),
                    ),
                    id="gallery_accordion",
                    open=["\U0001F7E2 Core Layers"],
                    multiple=True,
                ),
                width=300,
            ),
            ui.card(
                ui.card_header(
                    "\U0001F30A deck.gl Layer Gallery \u2014 24 Helpers"
                ),
                gallery_widget.ui(height="65vh"),
            ),
            ui.card(
                ui.card_header("\U0001F4CB Active Layers"),
                ui.output_text_verbatim("gl_status"),
            ),
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
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small(
                    "color utilities",
                    class_="badge text-bg-info mb-2",
                ),
                sidebar_hint(
                    "Demonstrates the three palette mapping functions "
                    "shipped with shiny_deckgl: color_range (linear "
                    "interpolation), color_bins (equal-width bins), "
                    "and color_quantiles (equal-count bins). Choose "
                    "a palette and mode, then observe how Baltic "
                    "Sea bathymetry columns change colour."
                ),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F3A8 Palette",
                        ui.input_select(
                            "pal_name", "Palette",
                            choices=list(PALETTE_CHOICES.keys()),
                            selected="Ocean",
                        ),
                        ui.input_select(
                            "pal_mode", "Colour mode",
                            choices={
                                "bins": "color_bins (equal-width)",
                                "quantiles": "color_quantiles (equal-count)",
                                "range": "color_range (linear N colours)",
                            },
                            selected="bins",
                        ),
                        ui.input_slider(
                            "pal_nbins", "Number of bins / stops",
                            min=3, max=12, value=6, step=1,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CA Swatch Preview",
                        ui.output_ui("pal_swatch"),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CF Layer Type",
                        ui.input_select(
                            "pal_layer",
                            "Visualise as",
                            choices={
                                "columns": "\U0001F4CA 3-D Columns",
                                "scatter": "\u26AB Scatterplot",
                                "heatmap": "\U0001F525 Heatmap (fixed palette)",
                            },
                            selected="columns",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F5FA Basemap",
                        ui.input_select(
                            "pal_basemap", "Basemap style",
                            choices=list(BASEMAP_CHOICES.keys()),
                            selected="Dark Matter",
                        ),
                    ),
                    id="pal_accordion",
                    open=["\U0001F3A8 Palette", "\U0001F4CA Swatch Preview"],
                    multiple=True,
                ),
                width=300,
            ),
            ui.card(
                ui.card_header(
                    "\U0001F3A8 Colour Scales \u2014 Baltic Sea Bathymetry"
                ),
                palette_widget.ui(height="60vh"),
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("\U0001F4CB Colour Statistics"),
                    ui.output_text_verbatim("pal_stats"),
                ),
                ui.card(
                    ui.card_header("\U0001F4DD Code Example"),
                    ui.output_text_verbatim("pal_code"),
                ),
                col_widths=[6, 6],
            ),
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
                        "\U0001F3AC Transitions (v0.8.0)",
                        sidebar_hint(
                            "Push a layer with animated radius transitions."
                        ),
                        ui.input_action_button(
                            "push_transitions",
                            "\U0001F3AC Push Animated Layer",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F9E9 BrushingExtension",
                        sidebar_hint(
                            "Highlights features near the cursor. "
                            "Move your mouse over the map to see the "
                            "brushing radius in action."
                        ),
                        ui.input_switch(
                            "v1_brushing", "Enable brushing",
                            value=False,
                        ),
                        ui.input_slider(
                            "v1_brush_radius", "Brush radius (m)",
                            min=5000, max=200000, value=50000, step=5000,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F50D DataFilter (Interactive)",
                        sidebar_hint(
                            "GPU-based numeric filtering. Only ports "
                            "within the cargo range are rendered — "
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

    # -- Tab 8: 3-D Visualization -----------------------------------------
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
                        ui.input_switch(
                            "td_directional", "Directional light",
                            value=False,
                        ),
                        ui.input_slider(
                            "td_dir_intensity", "Directional intensity",
                            min=0.0, max=3.0, value=0.6, step=0.1,
                        ),
                        ui.tags.hr(),
                        ui.tags.strong("Camera"),
                        ui.input_slider(
                            "td_pitch", "Camera pitch (\u00b0)",
                            min=0, max=85, value=45, step=5,
                        ),
                        ui.input_slider(
                            "td_bearing", "Camera bearing (\u00b0)",
                            min=-180, max=180, value=-15, step=5,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F3A8 Post-Processing",
                        sidebar_hint(
                            "Apply screen-space effects using the "
                            "effects module (PostProcessEffect)."
                        ),
                        ui.input_switch(
                            "td_pp_brightness", "Brightness/Contrast",
                            value=False,
                        ),
                        ui.input_slider(
                            "td_brightness", "Brightness",
                            min=-1, max=1, step=0.05, value=0.0,
                        ),
                        ui.input_slider(
                            "td_contrast", "Contrast",
                            min=-1, max=1, step=0.05, value=0.0,
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

    # -- Tab 9: Seal IBM (Individual-Based Model) -------------------------
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
                        ui.input_switch(
                            "seal_routes", "Colony route arcs",
                            value=False,
                        ),
                        ui.input_switch(
                            "seal_grid", "Haulout density grid",
                            value=False,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4D6 Animation Method",
                        sidebar_hint(
                            "This tab demonstrates deck.gl TripsLayer "
                            "animation \u2014 the core technique used for "
                            "all temporal track visualisations."
                        ),
                        ui.tags.p(
                            ui.tags.strong("trips_layer()"),
                            " renders animated trails that advance "
                            "over time. Each trip is a list of "
                            "[lon, lat, timestamp] waypoints.",
                            class_="small mb-2",
                        ),
                        ui.tags.p(
                            ui.tags.strong("_tripsAnimation"),
                            " config enables client-side "
                            "requestAnimationFrame looping: "
                            "loopLength (time units) and speed.",
                            class_="small mb-2",
                        ),
                        ui.tags.p(
                            ui.tags.strong("format_trips()"),
                            " normalises raw coordinate lists into "
                            "the dict format trips_layer() expects, "
                            "with auto-generated timestamps.",
                            class_="small mb-2",
                        ),
                        ui.tags.p(
                            ui.tags.strong("trips_animation_ui/server"),
                            " \u2014 reusable Shiny module providing "
                            "Play/Pause/Reset + speed & trail sliders "
                            "(used in the Animation Controls above).",
                            class_="small mb-2",
                        ),
                        ui.tags.p(
                            "Toggle \u201cColony route arcs\u201d above to "
                            "see GreatCircleLayer (geodesic arcs) and "
                            "\u201cHaulout density grid\u201d for GridLayer "
                            "(3-D extruded spatial binning).",
                            class_="small text-muted",
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

    # -- Tab 10: Widgets Gallery -----------------------------------------
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

    # =================================================================
    # Tab 1 — deck.gl Layers  (gallery — basemap + navigation)
    # =================================================================

    # Basemap switching (gallery widget on Tab 1)
    @reactive.Effect
    @reactive.event(input.basemap)
    async def _switch_basemap():
        style_url = BASEMAP_CHOICES.get(input.basemap(), CARTO_POSITRON)
        await gallery_widget.set_style(session, style_url)

    # Fly-to / ease-to transitions (gallery widget on Tab 1)
    @reactive.Effect
    @reactive.event(input.fly_klaipeda)
    async def _fly_klaipeda():
        await gallery_widget.fly_to(session, 21.13, 55.71, zoom=10, speed=1.5)

    @reactive.Effect
    @reactive.event(input.ease_stockholm)
    async def _ease_stockholm():
        await gallery_widget.ease_to(
            session, 18.07, 59.33, zoom=10, duration=2000,
        )

    @reactive.Effect
    @reactive.event(input.fly_baltic)
    async def _fly_baltic():
        await gallery_widget.fly_to(
            session, 19.5, 57.0, zoom=5, pitch=0, bearing=0,
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

    # Clusters (merged from former Tab 10)
    @reactive.Effect
    @reactive.event(input.v1_show_clusters, input.v1_cluster_radius)
    async def _v1_clusters():
        if input.v1_show_clusters():
            await maplibre_widget.add_cluster_layer(
                session,
                "v1-clusters",
                make_port_geojson(),
                cluster_radius=input.v1_cluster_radius(),
                cluster_color="#14919b",
                point_color="#e65100",
                point_radius=6,
            )
        else:
            await maplibre_widget.remove_cluster_layer(session, "v1-clusters")

    @reactive.Effect
    @reactive.event(input.v1_cooperative)
    async def _v1_cooperative():
        await maplibre_widget.set_cooperative_gestures(
            session, input.v1_cooperative()
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

    # Pre-compute bathymetry grid once per session
    _pal_bathy = make_bathymetry_grid(cols=25, rows=15)
    _pal_depths = [pt["depth_m"] for pt in _pal_bathy]

    # Basemap switching for palette tab
    @reactive.Effect
    @reactive.event(input.pal_basemap)
    async def _pal_switch_basemap():
        style_url = BASEMAP_CHOICES.get(input.pal_basemap(), CARTO_POSITRON)
        await palette_widget.set_style(session, style_url)

    @reactive.Calc
    def _pal_colors() -> list[list[int]]:
        """Compute per-point colours from current palette settings."""
        pal = PALETTE_CHOICES.get(input.pal_name(), PALETTE_VIRIDIS)
        n = input.pal_nbins()
        mode = input.pal_mode()
        if mode == "bins":
            return color_bins(_pal_depths, n_bins=n, palette=pal)
        elif mode == "quantiles":
            return color_quantiles(_pal_depths, n_bins=n, palette=pal)
        else:  # "range" — assign N-colour linear ramp via bins
            return color_bins(_pal_depths, n_bins=n, palette=pal)

    @reactive.Calc
    def _pal_range_colors() -> list[list[int]]:
        """Compute the swatch colours (N evenly-spaced stops)."""
        pal = PALETTE_CHOICES.get(input.pal_name(), PALETTE_VIRIDIS)
        return color_range(input.pal_nbins(), palette=pal)

    # Swatch preview
    @render.ui
    def pal_swatch():
        colours = _pal_range_colors()
        cells = []
        for i, c in enumerate(colours):
            hex_col = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
            cells.append(
                ui.tags.div(
                    style=(
                        f"display:inline-block;width:32px;height:24px;"
                        f"background:{hex_col};border:1px solid #666;"
                        f"border-radius:3px;margin:1px;"
                    ),
                    title=f"Stop {i+1}: rgb({c[0]}, {c[1]}, {c[2]})",
                )
            )
        return ui.div(
            ui.tags.div(
                *cells,
                style="display:flex;flex-wrap:wrap;gap:2px;margin-bottom:6px;",
            ),
            ui.tags.small(
                f"{len(colours)} stops from {input.pal_name()} palette",
                style="color:#888;",
            ),
        )

    # Stats output
    @render.text
    def pal_stats():
        colours = _pal_colors()
        n = input.pal_nbins()
        mode_label = {
            "bins": "color_bins (equal-width)",
            "quantiles": "color_quantiles (equal-count)",
            "range": "color_range (linear interpolation)",
        }.get(input.pal_mode(), input.pal_mode())

        lo, hi = min(_pal_depths), max(_pal_depths)
        unique_cols = len(set(tuple(c) for c in colours))
        return (
            f"Palette:    {input.pal_name()}\n"
            f"Mode:       {mode_label}\n"
            f"Bins/stops: {n}\n"
            f"Data range: {lo:.1f} \u2013 {hi:.1f} m\n"
            f"Points:     {len(_pal_bathy)}\n"
            f"Unique colours assigned: {unique_cols}"
        )

    # Code example output
    @render.text
    def pal_code():
        mode = input.pal_mode()
        pal_name = input.pal_name().upper()
        pal_const = f"PALETTE_{pal_name}" if pal_name != "CHLOROPHYLL" else "PALETTE_CHLOROPHYLL"
        n = input.pal_nbins()
        if mode == "bins":
            return (
                f"from shiny_deckgl import color_bins, {pal_const}\n\n"
                f"depths = [10.5, 45.2, 120.0, 250.3, \u2026]\n"
                f"colors = color_bins(depths, n_bins={n}, palette={pal_const})\n"
                f"# \u2192 one [R, G, B, A] per depth value"
            )
        elif mode == "quantiles":
            return (
                f"from shiny_deckgl import color_quantiles, {pal_const}\n\n"
                f"depths = [10.5, 45.2, 120.0, 250.3, \u2026]\n"
                f"colors = color_quantiles(depths, n_bins={n}, palette={pal_const})\n"
                f"# \u2192 one [R, G, B, A] per value (equal-count bins)"
            )
        else:
            return (
                f"from shiny_deckgl import color_range, {pal_const}\n\n"
                f"colors = color_range(n={n}, palette={pal_const})\n"
                f"# \u2192 {n} evenly-spaced [R, G, B, A] colours"
            )

    # Push palette-coloured layers to the palette map
    @reactive.Effect
    @reactive.event(
        input.pal_name, input.pal_mode, input.pal_nbins,
        input.pal_layer,
    )
    async def _pal_update_map():
        colours = _pal_colors()
        lo, hi = min(_pal_depths), max(_pal_depths)
        layer_type = input.pal_layer()

        # Build coloured data
        coloured_data = []
        for pt, c in zip(_pal_bathy, colours):
            bin_idx = int((pt["depth_m"] - lo) / max(hi - lo, 1) * (input.pal_nbins() - 1))
            bin_idx = max(0, min(bin_idx, input.pal_nbins() - 1))
            coloured_data.append({
                **pt,
                "color": c,
                "bin_label": f"Bin {bin_idx + 1}/{input.pal_nbins()}",
            })

        layers: list[dict] = []

        if layer_type == "columns":
            layers.append(column_layer(
                "pal-columns", coloured_data,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor="@@=d.color",
                radius=20000,
                elevationScale=1,
                extruded=True,
                pickable=True,
            ))
        elif layer_type == "scatter":
            layers.append(scatterplot_layer(
                "pal-scatter", coloured_data,
                getPosition="@@=d.position",
                getFillColor="@@=d.color",
                getRadius="@@=d.depth_m * 5",
                radiusMinPixels=4,
                radiusMaxPixels=25,
                pickable=True,
            ))
        else:  # heatmap (ignores palette — uses its own gradient)
            layers.append(layer(
                "HeatmapLayer", "pal-heat",
                data=coloured_data,
                getPosition="@@=d.position",
                getWeight="@@=d.depth_m",
                radiusPixels=40,
                intensity=1,
                threshold=0.05,
                pickable=False,
            ))

        # Build legend entries from swatch colours
        swatch = _pal_range_colors()
        legend_entries = []
        for i, c in enumerate(swatch):
            # Compute approximate depth range for label
            bin_lo = lo + (hi - lo) * i / len(swatch)
            bin_hi = lo + (hi - lo) * (i + 1) / len(swatch)
            legend_entries.append({
                "layer_id": f"pal-bin-{i}",
                "label": f"{bin_lo:.0f}\u2013{bin_hi:.0f} m",
                "color": c[:3],
                "shape": "rect",
            })

        widgets = [
            zoom_widget(), compass_widget(),
            fullscreen_widget(), scale_widget(),
        ]

        await palette_widget.update(
            session, layers, widgets=widgets,
            transition_duration=600,
        )
        await palette_widget.set_controls(
            session,
            [deck_legend_control(
                entries=legend_entries,
                position="bottom-right",
                title=f"{input.pal_name()} \u2014 {input.pal_mode()}",
                show_checkbox=False,
                collapsed=False,
            )],
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
            amb = ambient_light(intensity=input.ambient())
            pl = point_light(
                position=[19.5, 57.0, 80000],
                color=(255, 255, 220),
                intensity=input.point_intensity(),
            )
            le = lighting_effect(amb, pl)
            effects = [le]
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
        layers, _names = _gl_layers()
        path = os.path.join(
            tempfile.gettempdir(), "shiny_deckgl_demo_export.html",
        )
        gallery_widget.to_html(layers, path=path, title="shiny_deckgl Export")
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
        layers, _names = _gl_layers()
        spec = gallery_widget.to_json(layers)
        ellip = "\u2026" if len(spec) > 2000 else ""
        _export_log.set(
            f"JSON spec ({len(spec):,} chars):\n\n{spec[:2000]}{ellip}"
        )

    @reactive.Effect
    @reactive.event(input.roundtrip_json)
    async def _do_roundtrip():
        layers, _names = _gl_layers()
        spec_json = gallery_widget.to_json(layers)
        w2, layers2 = MapWidget.from_json(spec_json)
        checks = [
            f"Original widget id:     {gallery_widget.id}",
            f"Restored widget id:     {w2.id}",
            f"IDs match:              {gallery_widget.id == w2.id}",
            f"Style match:            {gallery_widget.style == w2.style}",
            f"View state match:       "
            f"{gallery_widget.view_state == w2.view_state}",
            f"Tooltip match:          "
            f"{gallery_widget.tooltip == w2.tooltip}",
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

    # Brushing & DataFilter extensions (merged from former Tab 9)

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
        await adv_widget.update(session, layers)

    # =================================================================
    # Tab 7: 3-D Visualisation
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
        input.td_directional, input.td_dir_intensity,
        input.td_pp_brightness, input.td_brightness, input.td_contrast,
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
            amb = ambient_light(intensity=input.td_ambient())
            pl = point_light(
                position=[19.5, 57.0, 80000],
                color=(255, 255, 220),
                intensity=input.td_point_light(),
            )
            lights = [pl]
            if input.td_directional():
                dl = directional_light(
                    direction=[-1, -3, -1],
                    intensity=input.td_dir_intensity(),
                )
                lights.append(dl)
            le = lighting_effect(amb, *lights)
            effects = [le]
        if input.td_pp_brightness():
            pp = post_process_effect(
                "brightnessContrast",
                brightness=input.td_brightness(),
                contrast=input.td_contrast(),
            )
            effects = effects or []
            effects.append(pp)

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

    # =================================================================
    # Tab 8 — Seal IBM (Individual-Based Model)
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
        input.seal_routes,
        input.seal_grid,
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

        # GreatCircleLayer — geodesic arcs between haulout colonies
        if input.seal_routes():
            gc_data = []
            for t in filtered_trips:
                wps = [p[:2] for p in t["path"]]
                if len(wps) >= 2:
                    gc_data.append({
                        "sourcePosition": wps[0],
                        "targetPosition": wps[-1],
                        "name": t.get("name", ""),
                    })
            if gc_data:
                layers.append(
                    great_circle_layer(
                        "seal_gc_routes",
                        gc_data,
                        getSourceColor=[100, 180, 220, 120],
                        getTargetColor=[100, 180, 220, 120],
                        getWidth=1,
                    )
                )

        # GridLayer — 3-D extruded density grid from haulout positions
        if input.seal_grid():
            grid_pts = [
                h["position"]
                for h in _seal_haulout_data
                if h["species"] in selected
                for _ in range(int(h.get("radius", 5)))
            ]
            if grid_pts:
                layers.append(
                    grid_layer(
                        "seal_density_grid",
                        grid_pts,
                        cellSize=30000,
                        elevationScale=200,
                        extruded=True,
                        pickable=False,
                        opacity=0.4,
                    )
                )

        await seal_widget.update(
            session, layers,
            widgets=[loading_widget()],
        )

    # ===================================================================
    # Tab 9: Widgets Gallery
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

    # ===================================================================
    # Tab 1: Layer Gallery — all 24 layer helpers
    # ===================================================================

    # -- Pre-computed gallery data (generated once per session) ----------
    _gl_port_data = make_gallery_port_data()
    _gl_arc_data = make_gallery_arc_data()
    _gl_line_data = make_gallery_line_data()
    _gl_path_data = make_gallery_path_data()
    _gl_text_data = make_gallery_text_data()
    _gl_icon_data = make_gallery_icon_data()
    _gl_column_data = make_gallery_column_data()

    _gl_polygon_data = make_shyfem_polygon_data(_POLYGON_GRD_STR)
    _gl_shyfem_mesh = make_shyfem_mesh_data(_CURONIAN_GRD_STR, z_scale=500.0)

    # Pre-compute mesh node points for the "Show mesh nodes" overlay
    _gl_mesh_node_data: list[dict] | None = None
    if _gl_shyfem_mesh is not None:
        _pos = _gl_shyfem_mesh["positions"]
        _col = _gl_shyfem_mesh.get("colors", [])
        _n = _gl_shyfem_mesh["n_vertices"]
        _gl_mesh_node_data = []
        for _i in range(_n):
            _r = round(_col[_i * 3] * 255) if _col else 120
            _g = round(_col[_i * 3 + 1] * 255) if _col else 170
            _b = round(_col[_i * 3 + 2] * 255) if _col else 210
            _gl_mesh_node_data.append({
                "position": [
                    _pos[_i * 3],
                    _pos[_i * 3 + 1],
                    _pos[_i * 3 + 2],
                ],
                "color": [_r, _g, _b, 220],
                "name": f"Node {_i}",
                "layerType": "MeshNode",
            })
        del _pos, _col, _n, _i, _r, _g, _b

    _gl_great_circle_data = [
        {
            "sourcePosition": r["waypoints"][0],
            "targetPosition": r["waypoints"][-1],
            "name": f"{r['from']} \u2192 {r['to']} (geodesic)",
            "layerType": "GreatCircleLayer",
        }
        for r in ROUTES
    ]

    _gl_heatmap_pts = make_heatmap_points(400)
    _gl_trips_data = make_trips_data(1800)

    _gl_h3_data = make_h3_data()

    _gl_point_cloud = make_point_cloud_data()

    # GeoJSON for gallery — HELCOM Marine Protected Areas
    _gl_geojson = MPA_GEOJSON

    # -- Reactive: build layer list from toggles -------------------------

    @reactive.Calc
    def _gl_layers() -> tuple[list[dict], list[str]]:
        """Build layers from toggle switches. Returns (layers, names)."""
        layers: list[dict] = []
        names: list[str] = []

        if input.gl_scatterplot():
            layers.append(scatterplot_layer(
                "gl-scatter", _gl_port_data,
                getPosition="@@=d.position",
                getRadius="@@=d.cargo_mt * 80",
                getFillColor=[20, 130, 180, 200],
                radiusMinPixels=4,
                radiusMaxPixels=30,
                pickable=True,
            ))
            names.append("ScatterplotLayer")

        if input.gl_geojson():
            layers.append(geojson_layer(
                "gl-geojson", _gl_geojson,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
                pickable=True,
            ))
            names.append("GeoJsonLayer")

        if input.gl_arc():
            layers.append(arc_layer(
                "gl-arcs", _gl_arc_data,
                getSourceColor=[0, 128, 255],
                getTargetColor=[255, 80, 80],
                getWidth=2,
                pickable=True,
            ))
            names.append("ArcLayer")

        if input.gl_line():
            layers.append(line_layer(
                "gl-lines", _gl_line_data,
                getColor=[80, 80, 80, 180],
                getWidth=2,
                pickable=True,
            ))
            names.append("LineLayer")

        if input.gl_path():
            layers.append(path_layer(
                "gl-paths", _gl_path_data,
                getPath="@@=d.path",
                getColor="@@=d.color",
                widthMinPixels=2,
                pickable=True,
            ))
            names.append("PathLayer")

        if input.gl_icon():
            layers.append(icon_layer(
                "gl-icons", _gl_icon_data,
                getPosition="@@=d.position",
                iconAtlas="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
                iconMapping={
                    "marker": {"x": 0, "y": 0, "width": 128,
                               "height": 128, "anchorY": 128},
                },
                getIcon="marker",
                getSize=32,
                pickable=True,
            ))
            names.append("IconLayer")

        if input.gl_text():
            layers.append(text_layer(
                "gl-text", _gl_text_data,
                getPosition="@@=d.position",
                getText="@@=d.text",
                getSize=14,
                getColor=[0, 0, 0, 255],
                getTextAnchor="middle",
                getAlignmentBaseline="center",
                fontWeight="bold",
                pickable=True,
            ))
            names.append("TextLayer")

        if input.gl_column():
            layers.append(column_layer(
                "gl-columns", _gl_column_data,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor=[14, 145, 155, 200],
                radius=8000,
                elevationScale=1,
                extruded=True,
                pickable=True,
            ))
            names.append("ColumnLayer")

        if input.gl_polygon():
            layers.append(polygon_layer(
                "gl-polygons", _gl_polygon_data,
                getPolygon="@@=d.polygon",
                getFillColor="@@=d.color",
                getLineColor=[40, 80, 120, 200],
                getLineWidth=1,
                lineWidthMinPixels=1,
                pickable=True,
            ))
            names.append("PolygonLayer")

        if input.gl_great_circle():
            layers.append(great_circle_layer(
                "gl-gc", _gl_great_circle_data,
                getSourceColor=[0, 200, 80],
                getTargetColor=[200, 0, 180],
                getWidth=2,
                pickable=True,
            ))
            names.append("GreatCircleLayer")

        # -- Aggregation layers ---
        if input.gl_heatmap():
            layers.append(heatmap_layer(
                "gl-heatmap", _gl_heatmap_pts,
                radiusPixels=40,
                intensity=1.2,
                threshold=0.05,
            ))
            names.append("HeatmapLayer")

        if input.gl_hexagon():
            layers.append(hexagon_layer(
                "gl-hexagons", _gl_heatmap_pts,
                radius=20000,
                elevationScale=50,
                extruded=True,
                pickable=True,
            ))
            names.append("HexagonLayer")

        if input.gl_grid():
            layers.append(grid_layer(
                "gl-grid", _gl_heatmap_pts,
                cellSize=20000,
                elevationScale=50,
                extruded=True,
                pickable=True,
            ))
            names.append("GridLayer")

        if input.gl_screen_grid():
            layers.append(screen_grid_layer(
                "gl-screen-grid", _gl_heatmap_pts,
                cellSizePixels=20,
            ))
            names.append("ScreenGridLayer")

        if input.gl_contour():
            layers.append(contour_layer(
                "gl-contour", _gl_heatmap_pts,
                cellSize=20000,
                contours=[
                    {"threshold": 1, "color": [255, 0, 0],
                     "strokeWidth": 2},
                    {"threshold": 5, "color": [0, 200, 0],
                     "strokeWidth": 3},
                    {"threshold": [6, 100], "color": [0, 100, 255, 128]},
                ],
            ))
            names.append("ContourLayer")

        # -- Geo-spatial layers ---
        if input.gl_h3_hexagon():
            layers.append(h3_hexagon_layer(
                "gl-h3", _gl_h3_data,
                getHexagon="@@=d.hex",
                getFillColor="@@=d.color",
                extruded=False,
                pickable=True,
            ))
            names.append("H3HexagonLayer")

        if input.gl_trips():
            layers.append(trips_layer(
                "gl-trips", _gl_trips_data,
                getPath="@@=d.path",
                getTimestamps="@@=d.timestamps",
                getColor=[253, 128, 93],
                widthMinPixels=3,
                trailLength=300,
                currentTime=500,
            ))
            names.append("TripsLayer")

        # -- Tile / raster layers ---
        if input.gl_tile():
            layers.append(tile_layer(
                "gl-tiles",
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                minZoom=0,
                maxZoom=19,
                tileSize=256,
                opacity=0.6,
            ))
            names.append("TileLayer")

        if input.gl_bitmap():
            layers.append(bitmap_layer(
                "gl-bitmap",
                image=(
                    "https://ows.emodnet-bathymetry.eu/wms"
                    "?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
                    "&LAYERS=emodnet:mean_atlas_land"
                    "&STYLES=&SRS=EPSG:4326"
                    "&BBOX=9.0,53.0,30.5,66.0"
                    "&WIDTH=1024&HEIGHT=768"
                    "&FORMAT=image/png&TRANSPARENT=true"
                ),
                bounds=[9.0, 53.0, 30.5, 66.0],
                opacity=0.7,
            ))
            names.append("BitmapLayer")

        if input.gl_mvt():
            layers.append(mvt_layer(
                "gl-mvt",
                "https://tiles.stadiamaps.com/data/openmaptiles/{z}/{x}/{y}.pbf",
                minZoom=0,
                maxZoom=14,
                getFillColor=[140, 170, 200, 100],
                getLineColor=[0, 0, 0, 80],
                lineWidthMinPixels=1,
                pickable=True,
            ))
            names.append("MVTLayer")

        if input.gl_wms():
            layers.append(wms_layer(
                "gl-wms",
                EMODNET_WMS_URL,
                layers=["emodnet:mean_atlas_land"],
                transparent=True,
                opacity=0.6,
            ))
            names.append("WMSLayer")

        # -- 3-D / mesh layers ---
        if input.gl_point_cloud():
            layers.append(point_cloud_layer(
                "gl-pointcloud", _gl_point_cloud,
                getPosition="@@=d.position",
                getColor="@@=d.color",
                pointSize=4,
                pickable=True,
            ))
            names.append("PointCloudLayer")

        if input.gl_simple_mesh():
            if _gl_shyfem_mesh is not None:
                layers.append(simple_mesh_layer(
                    "gl-mesh",
                    **custom_geometry(_gl_shyfem_mesh),
                    pickable=True,
                    wireframe=False,
                ))
            else:
                # Fallback: cubes at port locations
                _mesh_data = [
                    {
                        "position": [p["lon"], p["lat"], 500],
                        "name": p["name"],
                        "layerType": "SimpleMeshLayer",
                    }
                    for p in PORTS
                ]
                layers.append(simple_mesh_layer(
                    "gl-mesh", _mesh_data,
                    getPosition="@@=d.position",
                    getColor=[255, 180, 60, 220],
                    mesh="@@CubeGeometry",
                    sizeScale=20000,
                    pickable=True,
                ))
            # Always show node overlay alongside mesh surface
            if _gl_mesh_node_data is not None:
                ctr = _gl_shyfem_mesh["center"]
                layers.append(scatterplot_layer(
                    "gl-mesh-nodes",
                    _gl_mesh_node_data,
                    getPosition="@@=d.position",
                    getFillColor="@@=d.color",
                    getRadius=30,
                    radiusMinPixels=1,
                    radiusMaxPixels=4,
                    coordinateSystem=2,
                    coordinateOrigin=[ctr[0], ctr[1]],
                    pickable=True,
                ))
                names.append("MeshNodes")
            names.append("SimpleMeshLayer")

        if input.gl_terrain():
            layers.append(terrain_layer(
                "gl-terrain",
                elevationData="https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
                texture="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                elevationDecoder={
                    "rScaler": 25600, "gScaler": 100,
                    "bScaler": 100 / 256, "offset": -3276800,
                },
                meshMaxError=4.0,
            ))
            names.append("TerrainLayer")

        return layers, names

    # -- Legend colour map for gallery layers ------------------------------
    _GL_LEGEND_META = LAYER_LEGEND_META

    # -- Push layers to the gallery map ----------------------------------

    @reactive.Effect
    @reactive.event(
        input.gl_scatterplot, input.gl_geojson, input.gl_arc,
        input.gl_line, input.gl_path, input.gl_icon, input.gl_text,
        input.gl_column, input.gl_polygon, input.gl_great_circle,
        input.gl_heatmap, input.gl_hexagon, input.gl_grid,
        input.gl_screen_grid, input.gl_contour,
        input.gl_h3_hexagon, input.gl_trips,
        input.gl_tile, input.gl_bitmap, input.gl_mvt, input.gl_wms,
        input.gl_point_cloud, input.gl_simple_mesh, input.gl_terrain,
    )
    async def _gl_update_map():
        layers, names = _gl_layers()

        # Build dynamic legend entries for active layers
        legend_entries = []
        for name in names:
            meta = _GL_LEGEND_META.get(name, ([128, 128, 128], "circle"))
            legend_entries.append({
                "layer_id": name,
                "label": name,
                "color": meta[0],
                "shape": meta[1],
            })

        widgets = [
            zoom_widget(), compass_widget(),
            fullscreen_widget(), scale_widget(),
            loading_widget(label="Loading layers\u2026"),
        ]

        # Switch to a pitched 3-D view when 3-D layers are active
        _3d_layers = {
            "TerrainLayer", "PointCloudLayer", "SimpleMeshLayer",
            "ColumnLayer", "HexagonLayer", "GridLayer",
        }
        needs_3d = bool(_3d_layers & set(names))

        # Curonian Lagoon mesh — fly there when SimpleMeshLayer is active
        _mesh_layers = {"SimpleMeshLayer"}
        if (_mesh_layers & set(names)) and _CURONIAN_GRD_STR:
            vs = {**SHYFEM_VIEW, "pitch": 50, "bearing": -15} if needs_3d else SHYFEM_VIEW
        elif needs_3d:
            vs = {**BALTIC_VIEW, "pitch": 50, "bearing": -15, "zoom": 6}
        else:
            vs = BALTIC_VIEW

        await gallery_widget.update(
            session, layers, widgets=widgets,
            view_state=vs, transition_duration=800,
        )
        # Push deck_legend_control via set_controls (MapLibre control)
        if legend_entries:
            await gallery_widget.set_controls(
                session,
                [deck_legend_control(
                    entries=legend_entries,
                    position="bottom-right",
                    title="Active Layers",
                    show_checkbox=False,
                    collapsed=False,
                )],
            )
        else:
            await gallery_widget.set_controls(session, [])
        # Build status text
        lines = [f"Active layers: {len(names)} / 24", ""]
        if names:
            for n in names:
                lines.append(f"  \u2022 {n}")
        else:
            lines.append("  (no layers active)")
        _gl_log.set("\n".join(lines))

    _gl_log: reactive.Value[str] = reactive.Value("")

    @render.text
    def gl_status():
        return (
            _gl_log.get()
            or "Toggle layers in the sidebar to see them on the map."
        )

app = App(app_ui, server)
