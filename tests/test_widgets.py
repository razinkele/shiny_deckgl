"""Tests for the widgets module — deck.gl widget helpers.

Tests verify that:
- All widget functions return proper dict structure
- Widget class markers (@@widgetClass) are correct
- Placement parameter is properly passed
- kwargs are forwarded correctly
- Default placements are appropriate for each widget type
"""

from __future__ import annotations

import pytest

from shiny_deckgl import (
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


# ---------------------------------------------------------------------------
# Test widget structure and markers
# ---------------------------------------------------------------------------

class TestWidgetStructure:
    """Tests that all widgets return proper dict structure."""

    def test_zoom_widget_structure(self):
        """zoom_widget should return dict with @@widgetClass."""
        w = zoom_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "ZoomWidget"

    def test_compass_widget_structure(self):
        """compass_widget should return dict with @@widgetClass."""
        w = compass_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "CompassWidget"

    def test_fullscreen_widget_structure(self):
        """fullscreen_widget should return dict with @@widgetClass."""
        w = fullscreen_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "FullscreenWidget"

    def test_scale_widget_structure(self):
        """scale_widget should return dict with @@widgetClass."""
        w = scale_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_ScaleWidget"

    def test_gimbal_widget_structure(self):
        """gimbal_widget should return dict with @@widgetClass."""
        w = gimbal_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "GimbalWidget"

    def test_reset_view_widget_structure(self):
        """reset_view_widget should return dict with @@widgetClass."""
        w = reset_view_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "ResetViewWidget"

    def test_screenshot_widget_structure(self):
        """screenshot_widget should return dict with @@widgetClass."""
        w = screenshot_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "ScreenshotWidget"

    def test_fps_widget_structure(self):
        """fps_widget should return dict with @@widgetClass."""
        w = fps_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_FpsWidget"

    def test_loading_widget_structure(self):
        """loading_widget should return dict with @@widgetClass."""
        w = loading_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_LoadingWidget"

    def test_timeline_widget_structure(self):
        """timeline_widget should return dict with @@widgetClass."""
        w = timeline_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_TimelineWidget"

    def test_geocoder_widget_structure(self):
        """geocoder_widget should return dict with @@widgetClass."""
        w = geocoder_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_GeocoderWidget"

    def test_theme_widget_structure(self):
        """theme_widget should return dict with @@widgetClass."""
        w = theme_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_ThemeWidget"


class TestExperimentalWidgetStructure:
    """Tests for experimental widgets (deck.gl >= 9.2)."""

    def test_context_menu_widget_structure(self):
        """context_menu_widget should return dict with @@widgetClass."""
        w = context_menu_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_ContextMenuWidget"

    def test_info_widget_structure(self):
        """info_widget should return dict with @@widgetClass."""
        w = info_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_InfoWidget"

    def test_splitter_widget_structure(self):
        """splitter_widget should return dict with @@widgetClass."""
        w = splitter_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_SplitterWidget"

    def test_stats_widget_structure(self):
        """stats_widget should return dict with @@widgetClass."""
        w = stats_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_StatsWidget"

    def test_view_selector_widget_structure(self):
        """view_selector_widget should return dict with @@widgetClass."""
        w = view_selector_widget()
        assert isinstance(w, dict)
        assert "@@widgetClass" in w
        assert w["@@widgetClass"] == "_ViewSelectorWidget"


# ---------------------------------------------------------------------------
# Test default placements
# ---------------------------------------------------------------------------

class TestDefaultPlacements:
    """Tests that widgets have appropriate default placements."""

    def test_zoom_widget_default_placement(self):
        """zoom_widget should default to top-right."""
        w = zoom_widget()
        assert w["placement"] == "top-right"

    def test_compass_widget_default_placement(self):
        """compass_widget should default to top-right."""
        w = compass_widget()
        assert w["placement"] == "top-right"

    def test_fullscreen_widget_default_placement(self):
        """fullscreen_widget should default to top-right."""
        w = fullscreen_widget()
        assert w["placement"] == "top-right"

    def test_scale_widget_default_placement(self):
        """scale_widget should default to bottom-left."""
        w = scale_widget()
        assert w["placement"] == "bottom-left"

    def test_gimbal_widget_default_placement(self):
        """gimbal_widget should default to top-right."""
        w = gimbal_widget()
        assert w["placement"] == "top-right"

    def test_reset_view_widget_default_placement(self):
        """reset_view_widget should default to top-right."""
        w = reset_view_widget()
        assert w["placement"] == "top-right"

    def test_screenshot_widget_default_placement(self):
        """screenshot_widget should default to top-right."""
        w = screenshot_widget()
        assert w["placement"] == "top-right"

    def test_fps_widget_default_placement(self):
        """fps_widget should default to top-left."""
        w = fps_widget()
        assert w["placement"] == "top-left"

    def test_timeline_widget_default_placement(self):
        """timeline_widget should default to bottom-left."""
        w = timeline_widget()
        assert w["placement"] == "bottom-left"

    def test_geocoder_widget_default_placement(self):
        """geocoder_widget should default to top-left."""
        w = geocoder_widget()
        assert w["placement"] == "top-left"

    def test_info_widget_default_placement(self):
        """info_widget should default to top-left."""
        w = info_widget()
        assert w["placement"] == "top-left"

    def test_stats_widget_default_placement(self):
        """stats_widget should default to top-left."""
        w = stats_widget()
        assert w["placement"] == "top-left"

    def test_view_selector_widget_default_placement(self):
        """view_selector_widget should default to top-left."""
        w = view_selector_widget()
        assert w["placement"] == "top-left"


class TestWidgetsWithoutPlacement:
    """Tests for widgets that don't have placement parameter."""

    def test_loading_widget_no_placement(self):
        """loading_widget should not have placement by default."""
        w = loading_widget()
        assert "placement" not in w

    def test_theme_widget_no_placement(self):
        """theme_widget should not have placement by default."""
        w = theme_widget()
        assert "placement" not in w

    def test_context_menu_widget_no_placement(self):
        """context_menu_widget should not have placement by default."""
        w = context_menu_widget()
        assert "placement" not in w

    def test_splitter_widget_no_placement(self):
        """splitter_widget should not have placement by default."""
        w = splitter_widget()
        assert "placement" not in w


# ---------------------------------------------------------------------------
# Test custom placements
# ---------------------------------------------------------------------------

class TestCustomPlacements:
    """Tests that placement can be customized."""

    @pytest.mark.parametrize("placement", [
        "top-left", "top-right", "bottom-left", "bottom-right"
    ])
    def test_zoom_widget_custom_placement(self, placement):
        """zoom_widget should accept custom placement."""
        w = zoom_widget(placement=placement)
        assert w["placement"] == placement

    @pytest.mark.parametrize("placement", [
        "top-left", "top-right", "bottom-left", "bottom-right"
    ])
    def test_compass_widget_custom_placement(self, placement):
        """compass_widget should accept custom placement."""
        w = compass_widget(placement=placement)
        assert w["placement"] == placement

    @pytest.mark.parametrize("placement", [
        "top-left", "top-right", "bottom-left", "bottom-right"
    ])
    def test_scale_widget_custom_placement(self, placement):
        """scale_widget should accept custom placement."""
        w = scale_widget(placement=placement)
        assert w["placement"] == placement

    @pytest.mark.parametrize("placement", [
        "top-left", "top-right", "bottom-left", "bottom-right"
    ])
    def test_fps_widget_custom_placement(self, placement):
        """fps_widget should accept custom placement."""
        w = fps_widget(placement=placement)
        assert w["placement"] == placement


# ---------------------------------------------------------------------------
# Test kwargs forwarding
# ---------------------------------------------------------------------------

class TestKwargsForwarding:
    """Tests that kwargs are properly forwarded to widget dicts."""

    def test_zoom_widget_kwargs(self):
        """zoom_widget should forward kwargs."""
        w = zoom_widget(zoomInLabel="+", zoomOutLabel="-")
        assert w["zoomInLabel"] == "+"
        assert w["zoomOutLabel"] == "-"

    def test_compass_widget_kwargs(self):
        """compass_widget should forward kwargs."""
        w = compass_widget(transitionDuration=500)
        assert w["transitionDuration"] == 500

    def test_fullscreen_widget_kwargs(self):
        """fullscreen_widget should forward kwargs."""
        w = fullscreen_widget(container="map-container")
        assert w["container"] == "map-container"

    def test_scale_widget_kwargs(self):
        """scale_widget should forward kwargs."""
        w = scale_widget(unit="metric", maxWidth=200)
        assert w["unit"] == "metric"
        assert w["maxWidth"] == 200

    def test_gimbal_widget_kwargs(self):
        """gimbal_widget should forward kwargs."""
        w = gimbal_widget(style={"background": "white"})
        assert w["style"] == {"background": "white"}

    def test_fps_widget_kwargs(self):
        """fps_widget should forward kwargs."""
        w = fps_widget(style={"color": "red"})
        assert w["style"] == {"color": "red"}

    def test_loading_widget_kwargs(self):
        """loading_widget should forward kwargs."""
        w = loading_widget(style={"fontSize": "16px"})
        assert w["style"] == {"fontSize": "16px"}

    def test_timeline_widget_kwargs(self):
        """timeline_widget should forward kwargs."""
        w = timeline_widget(duration=10000, getTime="@@d.timestamp")
        assert w["duration"] == 10000
        assert w["getTime"] == "@@d.timestamp"

    def test_geocoder_widget_kwargs(self):
        """geocoder_widget should forward kwargs."""
        w = geocoder_widget(placeholder="Search address...")
        assert w["placeholder"] == "Search address..."

    def test_theme_widget_kwargs(self):
        """theme_widget should forward kwargs."""
        w = theme_widget(defaultTheme="dark")
        assert w["defaultTheme"] == "dark"

    def test_context_menu_widget_kwargs(self):
        """context_menu_widget should forward kwargs."""
        items = [{"label": "Option 1"}, {"label": "Option 2"}]
        w = context_menu_widget(items=items)
        assert w["items"] == items

    def test_info_widget_kwargs(self):
        """info_widget should forward kwargs."""
        w = info_widget(text="Hover info", visible=True)
        assert w["text"] == "Hover info"
        assert w["visible"] is True

    def test_splitter_widget_kwargs(self):
        """splitter_widget should forward kwargs."""
        w = splitter_widget(
            viewId1="view1",
            viewId2="view2",
            orientation="horizontal",
            initialSplit=0.5,
        )
        assert w["viewId1"] == "view1"
        assert w["viewId2"] == "view2"
        assert w["orientation"] == "horizontal"
        assert w["initialSplit"] == 0.5

    def test_stats_widget_kwargs(self):
        """stats_widget should forward kwargs."""
        w = stats_widget(type="memory", framesPerUpdate=30)
        assert w["type"] == "memory"
        assert w["framesPerUpdate"] == 30

    def test_view_selector_widget_kwargs(self):
        """view_selector_widget should forward kwargs."""
        w = view_selector_widget(initialViewMode="globe")
        assert w["initialViewMode"] == "globe"


# ---------------------------------------------------------------------------
# Test widget collections
# ---------------------------------------------------------------------------

class TestWidgetCollections:
    """Tests for creating collections of widgets."""

    def test_multiple_widgets_list(self):
        """Multiple widgets should work in a list."""
        widgets = [
            zoom_widget(),
            compass_widget(),
            fullscreen_widget(),
        ]
        assert len(widgets) == 3
        assert all(isinstance(w, dict) for w in widgets)
        assert all("@@widgetClass" in w for w in widgets)

    def test_common_control_widgets(self):
        """Common control widget combination."""
        widgets = [
            zoom_widget("top-right"),
            compass_widget("top-right"),
            scale_widget("bottom-left"),
        ]
        # Check placements are correct
        assert widgets[0]["placement"] == "top-right"
        assert widgets[1]["placement"] == "top-right"
        assert widgets[2]["placement"] == "bottom-left"

    def test_developer_debug_widgets(self):
        """Developer/debug widget combination."""
        widgets = [
            fps_widget("top-left"),
            stats_widget("bottom-left"),
        ]
        assert widgets[0]["@@widgetClass"] == "_FpsWidget"
        assert widgets[1]["@@widgetClass"] == "_StatsWidget"

    def test_all_widgets_unique_class_or_placement(self):
        """All standard widgets can be instantiated."""
        widgets = [
            zoom_widget(),
            compass_widget(),
            fullscreen_widget(),
            scale_widget(),
            gimbal_widget(),
            reset_view_widget(),
            screenshot_widget(),
            fps_widget(),
            loading_widget(),
            timeline_widget(),
            geocoder_widget(),
            theme_widget(),
            context_menu_widget(),
            info_widget(),
            splitter_widget(),
            stats_widget(),
            view_selector_widget(),
        ]
        assert len(widgets) == 17
        # All should have @@widgetClass
        for w in widgets:
            assert "@@widgetClass" in w


# ---------------------------------------------------------------------------
# Test edge cases
# ---------------------------------------------------------------------------

class TestWidgetEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_widget_with_empty_kwargs(self):
        """Widgets should work with no kwargs."""
        w = zoom_widget()
        assert len(w) == 2  # @@widgetClass and placement

    def test_widget_with_none_value_kwargs(self):
        """Widgets should pass through None values."""
        w = zoom_widget(style=None)
        assert w["style"] is None

    def test_widget_with_complex_kwargs(self):
        """Widgets should handle complex nested kwargs."""
        w = info_widget(
            style={"background": "rgba(0,0,0,0.8)", "padding": "10px"},
            text="<b>Title</b><br/>Description",
        )
        assert w["style"]["background"] == "rgba(0,0,0,0.8)"
        assert "<b>Title</b>" in w["text"]

    def test_widget_placement_override(self):
        """Placement can be overridden via kwargs."""
        # Note: placement as kwarg should also work
        w = zoom_widget("top-left")
        assert w["placement"] == "top-left"

    def test_widget_id_kwarg(self):
        """Widgets should accept id kwarg."""
        w = zoom_widget(id="my-zoom")
        assert w["id"] == "my-zoom"

    def test_widget_class_name_kwarg(self):
        """Widgets should accept className kwarg."""
        w = compass_widget(className="custom-compass")
        assert w["className"] == "custom-compass"
