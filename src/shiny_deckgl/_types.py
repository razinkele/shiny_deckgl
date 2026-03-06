"""Type definitions for shiny_deckgl configuration structures.

This module provides TypedDict definitions for the various configuration
dictionaries used throughout the library, improving IDE support and
type checking.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict, Union

__all__ = [
    # Control types
    "ControlSpec",
    "ControlOptions",
    # Widget types
    "WidgetSpec",
    # View types
    "ViewSpec",
    "ViewState",
    # Effect types
    "EffectSpec",
    "LightSpec",
    # Layer types
    "LayerSpec",
    "ExtensionSpec",
    # Tooltip types
    "TooltipSpec",
    # Transition types
    "TransitionSpec",
    # Position literals
    "ControlPosition",
    "WidgetPlacement",
]


# ---------------------------------------------------------------------------
# Position literals
# ---------------------------------------------------------------------------

ControlPosition = Literal["top-left", "top-right", "bottom-left", "bottom-right"]
WidgetPlacement = Literal[
    "top-left", "top-right", "bottom-left", "bottom-right",
    "fill"  # Some widgets support fill placement
]


# ---------------------------------------------------------------------------
# View state
# ---------------------------------------------------------------------------

class ViewState(TypedDict, total=False):
    """Camera view state configuration."""
    longitude: float
    latitude: float
    zoom: float
    pitch: float
    bearing: float
    minZoom: float
    maxZoom: float
    minPitch: float
    maxPitch: float


# ---------------------------------------------------------------------------
# Control specifications
# ---------------------------------------------------------------------------

class ControlOptions(TypedDict, total=False):
    """Options for MapLibre controls."""
    # GeolocateControl
    trackUserLocation: bool
    showAccuracyCircle: bool
    showUserHeading: bool
    positionOptions: dict[str, Any]
    # NavigationControl
    showCompass: bool
    showZoom: bool
    visualizePitch: bool
    # ScaleControl
    maxWidth: int
    unit: Literal["imperial", "metric", "nautical"]
    # Legend/Opacity controls
    targets: dict[str, str]
    show_default: bool


class ControlSpec(TypedDict, total=False):
    """MapLibre control specification."""
    type: str
    position: ControlPosition
    options: ControlOptions


# ---------------------------------------------------------------------------
# Widget specifications
# ---------------------------------------------------------------------------

class WidgetSpec(TypedDict, total=False):
    """Deck.gl widget specification."""
    # Widget class marker (@@widgetClass)
    placement: WidgetPlacement
    # Common widget options
    id: str
    style: dict[str, Any]
    className: str
    # ZoomWidget specific
    zoomInLabel: str
    zoomOutLabel: str
    # CompassWidget specific
    transitionDuration: int
    # TimelineWidget specific
    getTime: str
    setTime: str
    duration: int


# ---------------------------------------------------------------------------
# View specifications
# ---------------------------------------------------------------------------

class ViewSpec(TypedDict, total=False):
    """Camera view specification."""
    id: str
    controller: bool | dict[str, Any]
    viewState: ViewState
    # Additional view properties
    x: int | str
    y: int | str
    width: int | str
    height: int | str
    clear: bool
    # OrbitView specific
    orbitAxis: Literal["Y", "Z"]
    # FirstPersonView specific
    fovy: float


# ---------------------------------------------------------------------------
# Effect specifications
# ---------------------------------------------------------------------------

class LightSpec(TypedDict, total=False):
    """Light source specification."""
    type: Literal["ambient", "point", "directional", "sun"]
    color: list[int]  # RGB [0-255]
    intensity: float
    # PointLight specific
    position: list[float]  # [lng, lat, altitude]
    # DirectionalLight specific
    direction: list[float]  # [x, y, z]
    _shadow: bool
    # SunLight specific
    timestamp: int | float  # Unix timestamp


class EffectSpec(TypedDict, total=False):
    """Visual effect specification."""
    type: str  # e.g., "LightingEffect", postprocess shader name
    # LightingEffect
    ambientLight: LightSpec
    directionalLights: list[LightSpec]
    pointLights: list[LightSpec]
    # PostProcessEffect
    uniforms: dict[str, Any]


# ---------------------------------------------------------------------------
# Layer specifications
# ---------------------------------------------------------------------------

class ExtensionSpec(TypedDict, total=False):
    """Layer extension specification (internal format)."""
    pass  # Extensions use @@extClass and @@extOpts markers


# Extension input can be string or [name, options] pair
ExtensionInput = Union[str, list[Union[str, dict[str, Any]]]]


class LayerSpec(TypedDict, total=False):
    """Deck.gl layer specification."""
    # Required
    id: str
    type: str
    # Common properties
    data: Any
    visible: bool
    opacity: float
    pickable: bool
    autoHighlight: bool
    highlightColor: list[int]
    # Coordinate system
    coordinateSystem: int
    coordinateOrigin: list[float]
    # Data accessors (typically @@d.property strings)
    getPosition: Any
    getColor: Any
    getRadius: Any
    getElevation: Any
    # Extensions
    extensions: list[ExtensionInput]
    # Update triggers
    updateTriggers: dict[str, Any]
    # Transitions
    transitions: dict[str, Any]


# ---------------------------------------------------------------------------
# Tooltip specifications
# ---------------------------------------------------------------------------

class TooltipSpec(TypedDict, total=False):
    """Tooltip configuration."""
    html: str
    style: dict[str, str]


# ---------------------------------------------------------------------------
# Transition specifications
# ---------------------------------------------------------------------------

class TransitionSpec(TypedDict, total=False):
    """Animation transition specification."""
    type: Literal["interpolation", "spring"]
    # Interpolation type
    duration: int
    easing: str
    # Spring type
    stiffness: float
    damping: float


# ---------------------------------------------------------------------------
# Coordinate system constants (matching deck.gl COORDINATE_SYSTEM)
# ---------------------------------------------------------------------------

class CoordinateSystem:
    """Deck.gl coordinate system constants."""
    LNGLAT: int = 1
    METER_OFFSETS: int = 2
    LNGLAT_OFFSETS: int = 3
    CARTESIAN: int = 0
    IDENTITY: int = -1


# Make available as module-level constant for backwards compatibility
COORDINATE_SYSTEM = CoordinateSystem()
