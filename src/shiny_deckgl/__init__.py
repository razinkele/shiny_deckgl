# --- map_widget ---
from .map_widget import MapWidget  # noqa: F401

# --- layers ---
from .layers import (  # noqa: F401
    layer,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    bitmap_layer,
    arc_layer,
    icon_layer,
    path_layer,
    line_layer,
    text_layer,
    column_layer,
    polygon_layer,
    heatmap_layer,
    hexagon_layer,
    h3_hexagon_layer,
    trips_layer,
    great_circle_layer,
    contour_layer,
    grid_layer,
    screen_grid_layer,
    mvt_layer,
    wms_layer,
    point_cloud_layer,
    simple_mesh_layer,
    terrain_layer,
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
    "scatterplot_layer",
    "geojson_layer",
    "tile_layer",
    "bitmap_layer",
    "arc_layer",
    "icon_layer",
    "path_layer",
    "line_layer",
    "text_layer",
    "column_layer",
    "polygon_layer",
    "heatmap_layer",
    "hexagon_layer",
    "h3_hexagon_layer",
    "trips_layer",
    "great_circle_layer",
    "contour_layer",
    "grid_layer",
    "screen_grid_layer",
    "mvt_layer",
    "wms_layer",
    "point_cloud_layer",
    "simple_mesh_layer",
    "terrain_layer",
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
    # Version
    "__version__",
]
