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
)

# --- _data_utils ---
from ._data_utils import (  # noqa: F401
    _serialise_data,
    encode_binary_attribute,
)

# --- views ---
from .views import (  # noqa: F401
    map_view,
    orthographic_view,
    first_person_view,
    globe_view,
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
)

# --- extensions ---
from .extensions import (  # noqa: F401
    brushing_extension,
    collision_filter_extension,
    data_filter_extension,
    mask_extension,
    clip_extension,
    terrain_extension,
    fill_style_extension,
    path_style_extension,
)

# --- map_widget ---
from .map_widget import MapWidget  # noqa: F401
