"""shiny_deckgl — deck.gl and MapLibre integration for Shiny for Python.

This package provides a bridge between Shiny for Python and deck.gl/MapLibre,
enabling high-performance, GPU-accelerated geospatial visualizations in
reactive Shiny applications.

Core Components
---------------
MapWidget
    The main widget class for creating deck.gl maps with MapLibre basemaps.
    Supports layers, controls, widgets, effects, and server-side updates.

Layer Functions
---------------
Functions like ``scatterplot_layer``, ``geojson_layer``, ``heatmap_layer``,
etc., create deck.gl layer specifications. Each returns a dict suitable for
``MapWidget.set_layers()`` or ``MapWidget.add_layer()``.

View Functions
--------------
``map_view``, ``globe_view``, ``orbit_view``, etc., create deck.gl view
configurations for multi-view layouts and 3D perspectives.

Widget Functions
----------------
``zoom_widget``, ``compass_widget``, ``scale_widget``, etc., create deck.gl
UI widget specifications for navigation controls and information displays.

Extension Functions
-------------------
``brushing_extension``, ``data_filter_extension``, etc., create deck.gl
layer extension specifications for advanced rendering features.

Control Functions
-----------------
``geolocate_control``, ``terrain_control``, etc., create MapLibre control
specifications for map interaction.

Effect Functions
----------------
``ambient_light``, ``directional_light``, ``lighting_effect``, etc., create
lighting and post-processing effect specifications.

Color Utilities
---------------
``color_range``, ``color_bins``, ``color_quantiles``, and predefined palettes
like ``PALETTE_VIRIDIS`` for data-driven coloring.

Example
-------
>>> from shiny import App, ui, render
>>> from shiny_deckgl import MapWidget, scatterplot_layer
>>>
>>> widget = MapWidget("mymap")
>>>
>>> app_ui = ui.page_fluid(widget.ui())
>>>
>>> def server(input, output, session):
...     @render.effect
...     async def _():
...         await widget.set_layers(session, [
...             scatterplot_layer("points", data=my_data)
...         ])
>>>
>>> app = App(app_ui, server)

See Also
--------
- deck.gl documentation: https://deck.gl/docs
- MapLibre GL JS: https://maplibre.org/maplibre-gl-js/docs/
- Shiny for Python: https://shiny.posit.co/py/
"""

# --- map_widget ---
from .map_widget import MapWidget  # noqa: F401

# --- layers ---
from .layers import (  # noqa: F401
    layer,
    # Core layers
    scatterplot_layer,
    geojson_layer,
    arc_layer,
    bitmap_layer,
    column_layer,
    grid_cell_layer,
    icon_layer,
    line_layer,
    path_layer,
    point_cloud_layer,
    polygon_layer,
    solid_polygon_layer,
    text_layer,
    # Aggregation layers
    contour_layer,
    grid_layer,
    heatmap_layer,
    hexagon_layer,
    screen_grid_layer,
    # Geo layers
    a5_layer,
    geohash_layer,
    great_circle_layer,
    h3_cluster_layer,
    h3_hexagon_layer,
    mvt_layer,
    quadkey_layer,
    s2_layer,
    terrain_layer,
    tile_layer,
    tile_3d_layer,
    trips_layer,
    wms_layer,
    # Mesh layers
    scenegraph_layer,
    simple_mesh_layer,
    # Utilities
    custom_geometry,
    COORDINATE_SYSTEM,
)

# --- colors ---
from .colors import (  # noqa: F401
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    color_range,
    color_bins,
    color_quantiles,
    depth_color,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
)

# --- _data_utils ---
from ._data_utils import encode_binary_attribute  # noqa: F401

# --- views ---
from .views import (  # noqa: F401
    map_view,
    orthographic_view,
    first_person_view,
    globe_view,
    orbit_view,
)

# --- widgets ---
from .widgets import (  # noqa: F401
    zoom_widget,
    compass_widget,
    fullscreen_widget,
    scale_widget,
    gimbal_widget,
    reset_view_widget,
    screenshot_widget,
    fps_widget,
    loading_widget,
    timeline_widget,
    geocoder_widget,
    theme_widget,
    context_menu_widget,
    info_widget,
    splitter_widget,
    stats_widget,
    view_selector_widget,
)

# --- controls ---
from .controls import (  # noqa: F401
    geolocate_control,
    globe_control,
    terrain_control,
    legend_control,
    opacity_control,
    deck_legend_control,
    CONTROL_TYPES,
    CONTROL_POSITIONS,
)

# --- _transitions ---
from ._transitions import transition  # noqa: F401

# --- extensions ---
from .extensions import (  # noqa: F401
    Extension,
    brushing_extension,
    collision_filter_extension,
    data_filter_extension,
    mask_extension,
    clip_extension,
    terrain_extension,
    fill_style_extension,
    path_style_extension,
    fp64_extension,
)

# --- effects ---
from .effects import (  # noqa: F401
    ambient_light,
    point_light,
    directional_light,
    sun_light,
    lighting_effect,
    post_process_effect,
)

# --- parsers ---
from .parsers import parse_shyfem_grd, parse_shyfem_mesh  # noqa: F401

# --- ui ---
from .ui import head_includes  # noqa: F401

# --- IBM visual assets & helpers ---
from .ibm import (  # noqa: F401
    SPECIES_COLORS,
    ICON_ATLAS,
    ICON_MAPPING,
    format_trips,
    trips_animation_ui,
    trips_animation_server,
)

# --- demo data factories ---
from ._demo_data import (  # noqa: F401
    SHYFEM_VIEW,
    make_h3_data,
    make_point_cloud_data,
    make_shyfem_polygon_data,
    make_shyfem_mesh_data,
)

# --- enums ---
from .enums import (  # noqa: F401
    ControlPosition,
    WidgetPlacement,
    EasingFunction,
    TransitionType,
    ControlType,
    Projection,
    CoordinateSystem,
    DrawMode,
    LayerType,
    ViewType,
    LightType,
    PostProcessShader,
)

# --- version ---
from ._version import __version__


def __getattr__(name: str):
    """Lazy-load the built-in demo ``app`` to avoid importing the full Shiny
    application framework when users only need components like ``MapWidget``."""
    if name == "app":
        from .app import app  # noqa: F811

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "app",
    # MapWidget
    "MapWidget",
    # Layers
    "layer",
    # Core layers
    "scatterplot_layer",
    "geojson_layer",
    "arc_layer",
    "bitmap_layer",
    "column_layer",
    "grid_cell_layer",
    "icon_layer",
    "line_layer",
    "path_layer",
    "point_cloud_layer",
    "polygon_layer",
    "solid_polygon_layer",
    "text_layer",
    # Aggregation layers
    "contour_layer",
    "grid_layer",
    "heatmap_layer",
    "hexagon_layer",
    "screen_grid_layer",
    # Geo layers
    "a5_layer",
    "geohash_layer",
    "great_circle_layer",
    "h3_cluster_layer",
    "h3_hexagon_layer",
    "mvt_layer",
    "quadkey_layer",
    "s2_layer",
    "terrain_layer",
    "tile_layer",
    "tile_3d_layer",
    "trips_layer",
    "wms_layer",
    # Mesh layers
    "scenegraph_layer",
    "simple_mesh_layer",
    # Utilities
    "custom_geometry",
    "COORDINATE_SYSTEM",
    # Colors & basemaps
    "CARTO_POSITRON",
    "CARTO_DARK",
    "CARTO_VOYAGER",
    "OSM_LIBERTY",
    "color_range",
    "color_bins",
    "color_quantiles",
    "depth_color",
    "PALETTE_VIRIDIS",
    "PALETTE_PLASMA",
    "PALETTE_OCEAN",
    "PALETTE_THERMAL",
    "PALETTE_CHLOROPHYLL",
    # Binary data transport
    "encode_binary_attribute",
    # Views
    "map_view",
    "orthographic_view",
    "first_person_view",
    "globe_view",
    "orbit_view",
    # Widgets
    "zoom_widget",
    "compass_widget",
    "fullscreen_widget",
    "scale_widget",
    "gimbal_widget",
    "reset_view_widget",
    "screenshot_widget",
    "fps_widget",
    "loading_widget",
    "timeline_widget",
    "geocoder_widget",
    "theme_widget",
    "context_menu_widget",
    "info_widget",
    "splitter_widget",
    "stats_widget",
    "view_selector_widget",
    # Controls
    "geolocate_control",
    "globe_control",
    "terrain_control",
    "legend_control",
    "opacity_control",
    "deck_legend_control",
    "CONTROL_TYPES",
    "CONTROL_POSITIONS",
    # Transitions
    "transition",
    # Extensions
    "Extension",
    "brushing_extension",
    "collision_filter_extension",
    "data_filter_extension",
    "mask_extension",
    "clip_extension",
    "terrain_extension",
    "fill_style_extension",
    "path_style_extension",
    "fp64_extension",
    # Effects
    "ambient_light",
    "point_light",
    "directional_light",
    "sun_light",
    "lighting_effect",
    "post_process_effect",
    # Parsers
    "parse_shyfem_grd",
    "parse_shyfem_mesh",
    # UI
    "head_includes",
    # IBM visual assets & helpers
    "SPECIES_COLORS",
    "ICON_ATLAS",
    "ICON_MAPPING",
    "format_trips",
    "trips_animation_ui",
    "trips_animation_server",
    # Demo data factories
    "SHYFEM_VIEW",
    "make_h3_data",
    "make_point_cloud_data",
    "make_shyfem_polygon_data",
    "make_shyfem_mesh_data",
    # Enums
    "ControlPosition",
    "WidgetPlacement",
    "EasingFunction",
    "TransitionType",
    "ControlType",
    "Projection",
    "CoordinateSystem",
    "DrawMode",
    "LayerType",
    "ViewType",
    "LightType",
    "PostProcessShader",
    # Version
    "__version__",
]
