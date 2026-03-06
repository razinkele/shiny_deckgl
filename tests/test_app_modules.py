"""Tests for the demo application modules.

Tests verify that:
- App modules can be imported
- Lazy app loading works correctly
- Widget instances are accessible
- UI builder returns proper structure
- Server function has correct signature
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Test app module imports
# ---------------------------------------------------------------------------

class TestAppModuleImports:
    """Tests that app modules can be imported."""

    def test_app_module_importable(self):
        """app module should be importable."""
        from shiny_deckgl import app as app_module
        assert app_module is not None

    def test_app_widgets_importable(self):
        """_app_widgets module should be importable."""
        from shiny_deckgl._app_widgets import gallery_widget
        assert gallery_widget is not None

    def test_app_ui_build_function_importable(self):
        """_app_ui build_ui function should be importable."""
        from shiny_deckgl._app_ui import build_ui
        assert callable(build_ui)

    def test_app_server_function_importable(self):
        """_app_server server function should be importable."""
        from shiny_deckgl._app_server import server
        assert callable(server)


# ---------------------------------------------------------------------------
# Test widget instances
# ---------------------------------------------------------------------------

class TestWidgetInstances:
    """Tests for pre-instantiated widget instances."""

    def test_gallery_widget_exists(self):
        """gallery_widget should be a MapWidget instance."""
        from shiny_deckgl.app import gallery_widget
        from shiny_deckgl import MapWidget

        assert isinstance(gallery_widget, MapWidget)

    def test_maplibre_widget_exists(self):
        """maplibre_widget should be a MapWidget instance."""
        from shiny_deckgl.app import maplibre_widget
        from shiny_deckgl import MapWidget

        assert isinstance(maplibre_widget, MapWidget)

    def test_events_widget_exists(self):
        """events_widget should be a MapWidget instance."""
        from shiny_deckgl.app import events_widget
        from shiny_deckgl import MapWidget

        assert isinstance(events_widget, MapWidget)

    def test_palette_widget_exists(self):
        """palette_widget should be a MapWidget instance."""
        from shiny_deckgl.app import palette_widget
        from shiny_deckgl import MapWidget

        assert isinstance(palette_widget, MapWidget)

    def test_adv_widget_exists(self):
        """adv_widget should be a MapWidget instance."""
        from shiny_deckgl.app import adv_widget
        from shiny_deckgl import MapWidget

        assert isinstance(adv_widget, MapWidget)

    def test_draw_widget_exists(self):
        """draw_widget should be a MapWidget instance."""
        from shiny_deckgl.app import draw_widget
        from shiny_deckgl import MapWidget

        assert isinstance(draw_widget, MapWidget)

    def test_three_d_widget_exists(self):
        """three_d_widget should be a MapWidget instance."""
        from shiny_deckgl.app import three_d_widget
        from shiny_deckgl import MapWidget

        assert isinstance(three_d_widget, MapWidget)

    def test_seal_widget_exists(self):
        """seal_widget should be a MapWidget instance."""
        from shiny_deckgl.app import seal_widget
        from shiny_deckgl import MapWidget

        assert isinstance(seal_widget, MapWidget)

    def test_widgets_gallery_widget_exists(self):
        """widgets_gallery_widget should be a MapWidget instance."""
        from shiny_deckgl.app import widgets_gallery_widget
        from shiny_deckgl import MapWidget

        assert isinstance(widgets_gallery_widget, MapWidget)

    def test_all_widgets_have_unique_ids(self):
        """All widget instances should have unique IDs."""
        from shiny_deckgl.app import (
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

        ids = [
            gallery_widget.id,
            maplibre_widget.id,
            events_widget.id,
            palette_widget.id,
            adv_widget.id,
            draw_widget.id,
            three_d_widget.id,
            seal_widget.id,
            widgets_gallery_widget.id,
        ]

        # All IDs should be unique
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Test lazy app loading
# ---------------------------------------------------------------------------

class TestLazyAppLoading:
    """Tests for lazy app loading mechanism."""

    def test_app_lazy_loading(self):
        """App should be lazily loaded via __getattr__."""
        import shiny_deckgl.app as app_module

        # Access the app attribute (triggers lazy load)
        app = app_module.app
        assert app is not None

    def test_app_is_shiny_app(self):
        """app should be a Shiny App instance."""
        from shiny import App
        from shiny_deckgl.app import app

        assert isinstance(app, App)

    def test_app_is_cached(self):
        """app should be cached after first access."""
        from shiny_deckgl import app as app_module

        app1 = app_module.app
        app2 = app_module.app

        assert app1 is app2

    def test_invalid_attr_raises_error(self):
        """Accessing invalid attribute should raise AttributeError."""
        import shiny_deckgl.app as app_module

        with pytest.raises(AttributeError):
            _ = app_module.nonexistent_attribute


# ---------------------------------------------------------------------------
# Test UI builder
# ---------------------------------------------------------------------------

class TestUIBuilder:
    """Tests for UI builder function."""

    def test_build_ui_returns_tag(self):
        """build_ui should return a Shiny UI tag."""
        from shiny_deckgl._app_ui import build_ui
        from htmltools import Tag, TagList

        ui = build_ui()

        # Should be a Tag or TagList
        assert isinstance(ui, (Tag, TagList))

    def test_build_ui_callable_multiple_times(self):
        """build_ui should be callable multiple times."""
        from shiny_deckgl._app_ui import build_ui

        ui1 = build_ui()
        ui2 = build_ui()

        # Both should be valid
        assert ui1 is not None
        assert ui2 is not None


# ---------------------------------------------------------------------------
# Test server function
# ---------------------------------------------------------------------------

class TestServerFunction:
    """Tests for server function."""

    def test_server_is_callable(self):
        """server should be callable."""
        from shiny_deckgl._app_server import server

        assert callable(server)

    def test_server_has_correct_signature(self):
        """server should have input, output, session parameters."""
        import inspect
        from shiny_deckgl._app_server import server

        sig = inspect.signature(server)
        params = list(sig.parameters.keys())

        assert "input" in params
        assert "output" in params
        assert "session" in params


# ---------------------------------------------------------------------------
# Test app __all__ exports
# ---------------------------------------------------------------------------

class TestAppExports:
    """Tests for app module exports."""

    def test_app_all_exports(self):
        """app module should have __all__ defined."""
        from shiny_deckgl import app as app_module

        assert hasattr(app_module, "__all__")
        assert isinstance(app_module.__all__, list)

    def test_app_exports_app(self):
        """app module should export 'app'."""
        from shiny_deckgl import app as app_module

        assert "app" in app_module.__all__

    def test_app_exports_widgets(self):
        """app module should export widget instances."""
        from shiny_deckgl import app as app_module

        expected_widgets = [
            "gallery_widget",
            "maplibre_widget",
            "events_widget",
            "palette_widget",
            "adv_widget",
            "draw_widget",
            "three_d_widget",
            "seal_widget",
            "widgets_gallery_widget",
        ]

        for widget_name in expected_widgets:
            assert widget_name in app_module.__all__


# ---------------------------------------------------------------------------
# Test demo data module
# ---------------------------------------------------------------------------

class TestDemoData:
    """Tests for demo data module."""

    def test_demo_data_importable(self):
        """_demo_data module should be importable."""
        from shiny_deckgl._demo_data import SHYFEM_VIEW
        assert SHYFEM_VIEW is not None

    def test_demo_data_factories(self):
        """Demo data factory functions should be importable."""
        from shiny_deckgl import (
            make_h3_data,
            make_point_cloud_data,
            make_shyfem_polygon_data,
            make_shyfem_mesh_data,
        )

        assert callable(make_h3_data)
        assert callable(make_point_cloud_data)
        assert callable(make_shyfem_polygon_data)
        assert callable(make_shyfem_mesh_data)

    def test_shyfem_view_structure(self):
        """SHYFEM_VIEW should have proper view state structure."""
        from shiny_deckgl._demo_data import SHYFEM_VIEW

        assert "longitude" in SHYFEM_VIEW
        assert "latitude" in SHYFEM_VIEW
        assert "zoom" in SHYFEM_VIEW


# ---------------------------------------------------------------------------
# Test demo CSS module
# ---------------------------------------------------------------------------

class TestDemoCSS:
    """Tests for demo CSS module."""

    def test_demo_css_importable(self):
        """_demo_css module should be importable."""
        from shiny_deckgl import _demo_css
        assert _demo_css is not None


# ---------------------------------------------------------------------------
# Test CLI module
# ---------------------------------------------------------------------------

class TestCLIModule:
    """Tests for CLI module."""

    def test_cli_main_importable(self):
        """cli.main should be importable."""
        from shiny_deckgl.cli import main
        assert callable(main)

    def test_cli_main_has_no_required_args(self):
        """cli.main should have no required arguments."""
        import inspect
        from shiny_deckgl.cli import main

        sig = inspect.signature(main)
        params = sig.parameters

        # All parameters should have defaults or be empty
        for name, param in params.items():
            if param.default is inspect.Parameter.empty:
                if param.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD
                ):
                    pytest.fail(f"Parameter {name} has no default")


# ---------------------------------------------------------------------------
# Test integration between modules
# ---------------------------------------------------------------------------

class TestModuleIntegration:
    """Tests for integration between app modules."""

    def test_widgets_used_in_ui(self):
        """Widget instances should be referenced in UI."""
        from shiny_deckgl._app_widgets import gallery_widget
        from shiny_deckgl._app_ui import build_ui

        ui = build_ui()

        # UI should contain widget ID reference
        ui_str = str(ui)
        assert gallery_widget.id in ui_str or "gallery" in ui_str.lower()

    def test_app_uses_ui_and_server(self):
        """App should combine UI and server correctly."""
        from shiny_deckgl.app import app, _build_ui, _get_server

        # App should have been built from these components
        assert app is not None
        assert callable(_build_ui)
        assert callable(_get_server)
