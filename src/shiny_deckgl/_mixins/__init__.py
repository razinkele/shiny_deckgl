"""Mixins for MapWidget to organize functionality into logical groups.

These mixins provide a blueprint for splitting the large MapWidget class
into logical components. They can be used for:
1. Documentation of method groupings
2. Future refactoring to reduce file size
3. Type checking and IDE support

Note: The mixins duplicate code from map_widget.py intentionally.
They are NOT currently used by MapWidget but serve as a reference
implementation for potential future refactoring.
"""

from .navigation import NavigationMixin
from .maplibre_layers import MapLibreLayersMixin
from .drawing import DrawingMixin
from .export import ExportMixin

__all__ = [
    "NavigationMixin",
    "MapLibreLayersMixin",
    "DrawingMixin",
    "ExportMixin",
]

