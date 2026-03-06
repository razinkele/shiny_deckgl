"""Backward-compatibility shim -- re-exports everything from split modules.

Prior to v1.0.0 this file contained all public symbols.  It has been
split into focused modules for maintainability:

- `colors`        -- basemap constants, palettes, color_range/bins/quantiles
- `_data_utils`   -- _serialise_data, encode_binary_attribute
- `views`         -- map_view, orthographic_view, first_person_view, globe_view
- `widgets`       -- zoom_widget, compass_widget, ... (17 widget helpers)
- `controls`      -- geolocate_control, legend_control, ... + constants
- `_transitions`  -- transition()
- `layers`        -- layer() + 22 typed *_layer helpers
- `map_widget`    -- MapWidget class

All symbols are re-exported here so that existing `from shiny_deckgl.components
import X` statements continue to work unchanged.
"""

# --- colors ---
from .colors import (  # noqa: F401
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
    color_range,
    color_bins,
    color_quantiles,
    depth_color,
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

# --- map_widget ---
from .map_widget import MapWidget  # noqa: F401
