"""shiny_deckgl.testing imports without a browser and maps widget names to deck.gl classes."""
from __future__ import annotations


def test_import_needs_no_browser():
    import shiny_deckgl.testing as t
    assert t.__all__ == ["MapWidgetController"]


def test_widget_css_class_mapping():
    from shiny_deckgl.testing import _widget_css_class as f
    assert f("ZoomWidget") == "deck-widget-zoom"
    assert f("_TimelineWidget") == "deck-widget-timeline"
    assert f("ResetViewWidget") == "deck-widget-reset-view"
    assert f("FullscreenWidget") == "deck-widget-fullscreen"


def test_controller_is_a_shiny_ui_controller():
    from shiny_deckgl.testing import MapWidgetController

    class _Page:
        def locator(self, sel):
            return ("locator", sel)

    c = MapWidgetController(_Page(), "gallery_map")
    assert c.id == "gallery_map" and c.loc == ("locator", "#gallery_map")
