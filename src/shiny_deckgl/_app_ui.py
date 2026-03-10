"""UI building function for the demo application.

This module contains the _build_ui() function that constructs the Shiny UI
for the comprehensive shiny_deckgl demo application.
"""

from __future__ import annotations

# Module-level imports needed by _build_ui
from ._demo_data import (
    BASEMAP_CHOICES,
    PALETTE_CHOICES,
    DEFAULT_TOOLTIP_HTML,
)
from ._demo_css import MARINE_CSS, sidebar_hint, about_row as _about_row
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
from .ibm import trips_animation_ui

# Widget instances
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


def build_ui():
    """Build and return the Shiny UI for the demo application."""
    # Local imports to keep top-level light
    from shiny import ui
    from .ui import head_includes

    return ui.page_navbar(
        head_includes(),

        # -- Tab 1: deck.gl Layers (gallery - all 33 layer helpers) ---------
        ui.nav_panel(
        "\U0001F30A deck.gl Layers",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small(
                    "33 layer helpers",
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
                        ui.tooltip(
                            ui.input_switch(
                                "gl_grid_cell", "GridCellLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders individual grid cells "
                            "(pre-aggregated). Use for: model output grids, "
                            "pre-computed spatial bins. "
                            "\U0001F4E6 Data: generated (grid cells).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_lt_bathy", "LT Bathymetry",
                                value=False,
                            ),
                            "deck.gl \u2014 Lithuanian coastal bathymetry from "
                            "bathy.asc (1km resolution). Displays depth as 3D "
                            "extruded cells with color gradient. "
                            "\U0001F30A Data: ESRI ASCII Grid.",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_solid_polygon", "SolidPolygonLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders filled polygons without "
                            "stroke overhead. Use for: fast polygon fills, "
                            "extruded buildings, terrain. "
                            "\U0001F4E6 Data: generated (port bounding boxes).",
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
                        ui.tooltip(
                            ui.input_switch(
                                "gl_a5", "A5Layer", value=False,
                            ),
                            "deck.gl \u2014 Renders A5 pentagon cells "
                            "(icosahedral grid system). Use for: global "
                            "climate models, atmospheric data. "
                            "\U0001F310 Source: SF bike parking (deck.gl sample). "
                            "Note: view flies to San Francisco.",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_geohash", "GeohashLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders Geohash cells. "
                            "Use for: location indexing, spatial hashing, "
                            "tile-based aggregation. "
                            "\U0001F4E6 Data: generated (Baltic geohashes).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_h3_cluster", "H3ClusterLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders clustered H3 hexagons "
                            "as merged polygons. Use for: region outlines, "
                            "aggregated H3 coverage areas. "
                            "\U0001F4E6 Data: generated (H3 clusters).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_quadkey", "QuadkeyLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders Bing Maps quadkey tiles. "
                            "Use for: web map tile indices, quad-tree "
                            "spatial partitioning. "
                            "\U0001F4E6 Data: generated (quadkey cells).",
                        ),
                        ui.tooltip(
                            ui.input_switch(
                                "gl_s2", "S2Layer", value=False,
                            ),
                            "deck.gl \u2014 Renders Google S2 geometry cells. "
                            "Use for: S2-indexed datasets, BigQuery GIS, "
                            "spherical geometry. "
                            "\U0001F4E6 Data: generated (S2 tokens).",
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
                        ui.tooltip(
                            ui.input_switch(
                                "gl_tile_3d", "Tile3DLayer", value=False,
                            ),
                            "deck.gl \u2014 Renders OGC 3D Tiles and "
                            "Esri I3S datasets. Use for: city models, "
                            "point clouds, photogrammetry. "
                            "\U0001F310 Source: 3D Tiles sample dataset.",
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
                        ui.tooltip(
                            ui.input_switch(
                                "gl_scenegraph", "ScenegraphLayer",
                                value=False,
                            ),
                            "deck.gl \u2014 Renders glTF/GLB 3-D models "
                            "at geographic positions. Use for: ship models, "
                            "wind turbines, offshore platforms. "
                            "\U0001F310 Source: sample glTF model.",
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
                    "\U0001F30A deck.gl Layer Gallery \u2014 33 Helpers"
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
                            "maplibre-gl-opacity - layer switcher with "
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
                        "\U0001F3A1 Property Animation (v1.7.0)",
                        sidebar_hint(
                            "Client-side animation via animate_prop(). "
                            "No server round-trips \u2014 the browser drives "
                            "the animation loop at 60 fps."
                        ),
                        ui.input_action_button(
                            "push_anim_rotate",
                            "\U0001F300 Rotating Icons",
                        ),
                        ui.input_action_button(
                            "push_anim_pulse",
                            "\U0001F4AB Pulsing Circles",
                        ),
                        ui.input_action_button(
                            "stop_anim",
                            "\u23F8 Pause Animation",
                        ),
                        ui.input_action_button(
                            "resume_anim",
                            "\u25B6 Resume Animation",
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F50D DataFilter (Interactive)",
                        sidebar_hint(
                            "GPU-based numeric filtering. Only ports "
                            "within the cargo range are rendered - "
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
                    "\U0001F9AD Baltic Sea - Seal Movement (IBM Simulation)"
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
                        ui.input_switch(
                            "wg_layer_legend", "Layer legend widget", True,
                        ),
                        ui.input_switch(
                            "wg_auto_legend", "Auto-introspect layers", False,
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
                    "\U0001F9E9 Widget Gallery - All 18 deck.gl Widgets"
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
                    href="https://github.com/razinka/shiny_deckgl",
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
    header=ui.TagList(
        ui.tags.style(MARINE_CSS),
        # Dismiss Bootstrap tooltips when toggle switches are clicked.
        ui.tags.script(
            "document.addEventListener('click', function(e) {"
            "  if (e.target.closest('.form-switch')) {"
            "    document.querySelectorAll('.tooltip.show').forEach("
            "      function(t) { t.remove(); }"
            "    );"
            "  }"
            "});"
        ),
    ),
)


__all__ = ["build_ui"]
