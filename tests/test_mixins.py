"""Tests for the _mixins module — MapWidget mixin classes.

Tests verify that:
- All mixins can be imported
- Mixin methods have correct signatures
- Static methods work correctly
- The mixins can be composed with a test class
"""
from __future__ import annotations

import asyncio
import inspect

import pytest

from shiny_deckgl._mixins import (
    NavigationMixin,
    MapLibreLayersMixin,
    DrawingMixin,
    ExportMixin,
)


# ---------------------------------------------------------------------------
# Test mixin imports and structure
# ---------------------------------------------------------------------------

class TestMixinImports:
    """Tests that all mixins can be imported."""

    def test_navigation_mixin_importable(self):
        """NavigationMixin should be importable."""
        assert NavigationMixin is not None

    def test_maplibre_layers_mixin_importable(self):
        """MapLibreLayersMixin should be importable."""
        assert MapLibreLayersMixin is not None

    def test_drawing_mixin_importable(self):
        """DrawingMixin should be importable."""
        assert DrawingMixin is not None

    def test_export_mixin_importable(self):
        """ExportMixin should be importable."""
        assert ExportMixin is not None


class TestNavigationMixin:
    """Tests for NavigationMixin."""

    def test_has_fly_to_method(self):
        """NavigationMixin should have fly_to method."""
        assert hasattr(NavigationMixin, "fly_to")
        assert asyncio.iscoroutinefunction(NavigationMixin.fly_to)

    def test_has_ease_to_method(self):
        """NavigationMixin should have ease_to method."""
        assert hasattr(NavigationMixin, "ease_to")
        assert asyncio.iscoroutinefunction(NavigationMixin.ease_to)

    def test_has_fit_bounds_method(self):
        """NavigationMixin should have fit_bounds method."""
        assert hasattr(NavigationMixin, "fit_bounds")
        assert asyncio.iscoroutinefunction(NavigationMixin.fit_bounds)

    def test_has_compute_bounds_static(self):
        """NavigationMixin should have compute_bounds static method."""
        assert hasattr(NavigationMixin, "compute_bounds")
        # compute_bounds is a static method
        assert callable(NavigationMixin.compute_bounds)

    def test_build_view_state_static(self):
        """_build_view_state should build correct view state dict."""
        result = NavigationMixin._build_view_state(10.0, 20.0)
        assert result == {"longitude": 10.0, "latitude": 20.0}

    def test_build_view_state_with_zoom(self):
        """_build_view_state should include optional parameters."""
        result = NavigationMixin._build_view_state(
            10.0, 20.0, zoom=5, pitch=45, bearing=90
        )
        assert result == {
            "longitude": 10.0,
            "latitude": 20.0,
            "zoom": 5,
            "pitch": 45,
            "bearing": 90,
        }

    def test_compute_bounds_feature_collection(self):
        """compute_bounds should work with FeatureCollection."""
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [10, 20]},
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [30, 40]},
                },
            ],
        }
        bounds = NavigationMixin.compute_bounds(geojson)
        assert bounds == [[10, 20], [30, 40]]

    def test_compute_bounds_empty(self):
        """compute_bounds with empty GeoJSON returns world bounds."""
        geojson = {"type": "FeatureCollection", "features": []}
        bounds = NavigationMixin.compute_bounds(geojson)
        assert bounds == [[-180, -90], [180, 90]]


class TestMapLibreLayersMixin:
    """Tests for MapLibreLayersMixin."""

    def test_has_add_source_method(self):
        """MapLibreLayersMixin should have add_source method."""
        assert hasattr(MapLibreLayersMixin, "add_source")
        assert asyncio.iscoroutinefunction(MapLibreLayersMixin.add_source)

    def test_has_add_maplibre_layer_method(self):
        """MapLibreLayersMixin should have add_maplibre_layer method."""
        assert hasattr(MapLibreLayersMixin, "add_maplibre_layer")
        assert asyncio.iscoroutinefunction(MapLibreLayersMixin.add_maplibre_layer)

    def test_has_set_paint_property_method(self):
        """MapLibreLayersMixin should have set_paint_property method."""
        assert hasattr(MapLibreLayersMixin, "set_paint_property")
        assert asyncio.iscoroutinefunction(MapLibreLayersMixin.set_paint_property)

    def test_has_set_projection_method(self):
        """MapLibreLayersMixin should have set_projection method."""
        assert hasattr(MapLibreLayersMixin, "set_projection")
        assert asyncio.iscoroutinefunction(MapLibreLayersMixin.set_projection)


class TestDrawingMixin:
    """Tests for DrawingMixin."""

    def test_has_enable_draw_method(self):
        """DrawingMixin should have enable_draw method."""
        assert hasattr(DrawingMixin, "enable_draw")
        assert asyncio.iscoroutinefunction(DrawingMixin.enable_draw)

    def test_has_disable_draw_method(self):
        """DrawingMixin should have disable_draw method."""
        assert hasattr(DrawingMixin, "disable_draw")
        assert asyncio.iscoroutinefunction(DrawingMixin.disable_draw)

    def test_has_drawn_features_input_id_property(self):
        """DrawingMixin should have drawn_features_input_id property."""
        assert hasattr(DrawingMixin, "drawn_features_input_id")


class TestExportMixin:
    """Tests for ExportMixin."""

    def test_has_export_image_method(self):
        """ExportMixin should have export_image method."""
        assert hasattr(ExportMixin, "export_image")
        assert asyncio.iscoroutinefunction(ExportMixin.export_image)

    def test_has_to_json_method(self):
        """ExportMixin should have to_json method."""
        assert hasattr(ExportMixin, "to_json")
        assert callable(ExportMixin.to_json)

    def test_has_from_json_method(self):
        """ExportMixin should have from_json class method."""
        assert hasattr(ExportMixin, "from_json")
        # from_json is a classmethod
        assert callable(ExportMixin.from_json)

    def test_has_to_html_method(self):
        """ExportMixin should have to_html method."""
        assert hasattr(ExportMixin, "to_html")
        assert callable(ExportMixin.to_html)


# ---------------------------------------------------------------------------
# Test mixin composition
# ---------------------------------------------------------------------------

class TestMixinComposition:
    """Tests that mixins can be composed into a class."""

    def test_can_compose_all_mixins(self):
        """All mixins should be composable into a single class."""

        class ComposedWidget(
            NavigationMixin,
            MapLibreLayersMixin,
            DrawingMixin,
            ExportMixin,
        ):
            def __init__(self, id: str):
                self.id = id
                self._bare_id = id
                self.view_state = {"longitude": 0, "latitude": 0, "zoom": 1}
                self.style = "https://example.com/style.json"
                self.tooltip = None
                self.mapbox_api_key = None

        widget = ComposedWidget("test_widget")

        # Check all mixin methods are accessible
        assert hasattr(widget, "fly_to")
        assert hasattr(widget, "add_source")
        assert hasattr(widget, "enable_draw")
        assert hasattr(widget, "export_image")

    def test_composed_widget_static_methods_work(self):
        """Static methods should work on composed class."""

        class ComposedWidget(NavigationMixin):
            pass

        # Static method should work
        bounds = ComposedWidget.compute_bounds({
            "type": "Point",
            "coordinates": [10, 20],
        })
        assert bounds == [[10, 20], [10, 20]]


# ---------------------------------------------------------------------------
# Test method signatures match MapWidget
# ---------------------------------------------------------------------------

class TestMethodSignatures:
    """Tests that mixin method signatures match expected patterns."""

    def test_fly_to_signature(self):
        """fly_to should have correct parameter names."""
        sig = inspect.signature(NavigationMixin.fly_to)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "session" in params
        assert "longitude" in params
        assert "latitude" in params

    def test_add_source_signature(self):
        """add_source should have correct parameter names."""
        sig = inspect.signature(MapLibreLayersMixin.add_source)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "session" in params
        assert "source_id" in params
        assert "source_spec" in params

    def test_enable_draw_signature(self):
        """enable_draw should have correct parameter names."""
        sig = inspect.signature(DrawingMixin.enable_draw)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "session" in params
        assert "modes" in params
        assert "default_mode" in params

    def test_to_html_signature(self):
        """to_html should have correct parameter names."""
        sig = inspect.signature(ExportMixin.to_html)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "layers" in params
        assert "path" in params
        assert "effects" in params
        assert "title" in params
