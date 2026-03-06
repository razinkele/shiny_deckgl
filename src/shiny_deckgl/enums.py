"""Enumeration types for shiny_deckgl.

This module provides enum classes for common string constants used throughout
the library, improving IDE autocomplete and reducing magic string errors.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    # Position enums
    "ControlPosition",
    "WidgetPlacement",
    # Easing functions
    "EasingFunction",
    # Transition types
    "TransitionType",
    # Control types
    "ControlType",
    # Projection types
    "Projection",
    # Coordinate systems
    "CoordinateSystem",
    # Draw modes
    "DrawMode",
    # Layer types
    "LayerType",
    # View types
    "ViewType",
    # Effect types
    "LightType",
    "PostProcessShader",
]


# ---------------------------------------------------------------------------
# Position enums
# ---------------------------------------------------------------------------

class ControlPosition(str, Enum):
    """Valid positions for MapLibre controls."""
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class WidgetPlacement(str, Enum):
    """Valid placements for deck.gl widgets."""
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    FILL = "fill"


# ---------------------------------------------------------------------------
# Transition and animation enums
# ---------------------------------------------------------------------------

class EasingFunction(str, Enum):
    """Easing functions for camera transitions.

    These map to d3-ease functions in the JavaScript client.
    """
    LINEAR = "linear"
    EASE_IN_CUBIC = "ease-in-cubic"
    EASE_OUT_CUBIC = "ease-out-cubic"
    EASE_IN_OUT_CUBIC = "ease-in-out-cubic"
    EASE_IN_SINE = "ease-in-sine"
    EASE_OUT_SINE = "ease-out-sine"
    EASE_IN_OUT_SINE = "ease-in-out-sine"
    EASE_IN_QUAD = "ease-in-quad"
    EASE_OUT_QUAD = "ease-out-quad"
    EASE_IN_OUT_QUAD = "ease-in-out-quad"
    EASE_IN_EXPO = "ease-in-expo"
    EASE_OUT_EXPO = "ease-out-expo"
    EASE_IN_OUT_EXPO = "ease-in-out-expo"


class TransitionType(str, Enum):
    """Transition animation types."""
    INTERPOLATION = "interpolation"
    SPRING = "spring"


# ---------------------------------------------------------------------------
# Control types
# ---------------------------------------------------------------------------

class ControlType(str, Enum):
    """Valid MapLibre control types."""
    NAVIGATION = "navigation"
    SCALE = "scale"
    FULLSCREEN = "fullscreen"
    GEOLOCATE = "geolocate"
    ATTRIBUTION = "attribution"
    GLOBE = "globe"
    TERRAIN = "terrain"
    LEGEND = "legend"
    OPACITY = "opacity"
    DECK_LEGEND = "deck_legend"


# ---------------------------------------------------------------------------
# Map configuration enums
# ---------------------------------------------------------------------------

class Projection(str, Enum):
    """Map projection types."""
    MERCATOR = "mercator"
    GLOBE = "globe"


class CoordinateSystem(int, Enum):
    """Deck.gl coordinate system constants.

    These correspond to deck.gl's COORDINATE_SYSTEM values.
    """
    CARTESIAN = 0
    LNGLAT = 1
    METER_OFFSETS = 2
    LNGLAT_OFFSETS = 3
    IDENTITY = -1


# ---------------------------------------------------------------------------
# Drawing enums
# ---------------------------------------------------------------------------

class DrawMode(str, Enum):
    """Mapbox Draw mode identifiers."""
    SIMPLE_SELECT = "simple_select"
    DIRECT_SELECT = "direct_select"
    DRAW_POINT = "draw_point"
    DRAW_LINE_STRING = "draw_line_string"
    DRAW_POLYGON = "draw_polygon"
    DRAW_RECTANGLE = "draw_rectangle"
    DRAW_CIRCLE = "draw_circle"
    STATIC = "static"


# ---------------------------------------------------------------------------
# Layer types
# ---------------------------------------------------------------------------

class LayerType(str, Enum):
    """Deck.gl layer type identifiers."""
    # Core layers
    SCATTERPLOT = "ScatterplotLayer"
    ARC = "ArcLayer"
    BITMAP = "BitmapLayer"
    COLUMN = "ColumnLayer"
    GEOJSON = "GeoJsonLayer"
    GRID_CELL = "GridCellLayer"
    ICON = "IconLayer"
    LINE = "LineLayer"
    PATH = "PathLayer"
    POINT_CLOUD = "PointCloudLayer"
    POLYGON = "PolygonLayer"
    SOLID_POLYGON = "SolidPolygonLayer"
    TEXT = "TextLayer"
    # Aggregation layers
    CONTOUR = "ContourLayer"
    GRID = "GridLayer"
    HEATMAP = "HeatmapLayer"
    HEXAGON = "HexagonLayer"
    SCREEN_GRID = "ScreenGridLayer"
    # Geo layers
    A5 = "A5Layer"
    GEOHASH = "GeohashLayer"
    GREAT_CIRCLE = "GreatCircleLayer"
    H3_CLUSTER = "H3ClusterLayer"
    H3_HEXAGON = "H3HexagonLayer"
    MVT = "MVTLayer"
    QUADKEY = "QuadkeyLayer"
    S2 = "S2Layer"
    TERRAIN = "TerrainLayer"
    TILE = "TileLayer"
    TILE_3D = "Tile3DLayer"
    TRIPS = "TripsLayer"
    WMS = "WMSLayer"
    # Mesh layers
    SCENEGRAPH = "ScenegraphLayer"
    SIMPLE_MESH = "SimpleMeshLayer"


# ---------------------------------------------------------------------------
# View types
# ---------------------------------------------------------------------------

class ViewType(str, Enum):
    """Deck.gl view type identifiers."""
    MAP = "MapView"
    FIRST_PERSON = "FirstPersonView"
    ORTHOGRAPHIC = "OrthographicView"
    ORBIT = "OrbitView"
    GLOBE = "GlobeView"


# ---------------------------------------------------------------------------
# Effect types
# ---------------------------------------------------------------------------

class LightType(str, Enum):
    """Light source type identifiers."""
    AMBIENT = "ambient"
    POINT = "point"
    DIRECTIONAL = "directional"
    SUN = "sun"


class PostProcessShader(str, Enum):
    """Post-processing shader module identifiers.

    These correspond to luma.gl shader modules available for
    post-processing effects.
    """
    BRIGHTNESS_CONTRAST = "brightnessContrast"
    COLOR_HALFTONE = "colorHalftone"
    DOT_SCREEN = "dotScreen"
    EDGE_WORK = "edgeWork"
    FX_AA = "fxaa"
    HEX_PIXELATE = "hexPixelate"
    HUE_SATURATION = "hueSaturation"
    INK = "ink"
    MAGNIFY = "magnify"
    NOISE = "noise"
    SEPIA = "sepia"
    TILT_SHIFT = "tiltShift"
    TRIANGLE_BLUR = "triangleBlur"
    VIBRANCE = "vibrance"
    VIGNETTE = "vignette"
    ZOOM_BLUR = "zoomBlur"
