"""Deck.gl widget helpers (v0.8.0+)."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# deck.gl Widget helpers (v0.8.0)
# ---------------------------------------------------------------------------

def zoom_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``ZoomWidget`` spec (zoom-in / zoom-out buttons)."""
    return {"@@widgetClass": "ZoomWidget", "placement": placement, **kwargs}


def compass_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``CompassWidget`` spec (bearing indicator / reset)."""
    return {"@@widgetClass": "CompassWidget", "placement": placement, **kwargs}


def fullscreen_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``FullscreenWidget`` spec (toggle fullscreen)."""
    return {"@@widgetClass": "FullscreenWidget", "placement": placement, **kwargs}


def scale_widget(placement: str = "bottom-left", **kwargs) -> dict:
    """Create a ``ScaleWidget`` spec (distance scale bar)."""
    return {"@@widgetClass": "_ScaleWidget", "placement": placement, **kwargs}


def gimbal_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``GimbalWidget`` spec (3D camera gimbal control)."""
    return {"@@widgetClass": "GimbalWidget", "placement": placement, **kwargs}


def reset_view_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``ResetViewWidget`` spec (reset camera to initial state)."""
    return {"@@widgetClass": "ResetViewWidget", "placement": placement, **kwargs}


def screenshot_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``ScreenshotWidget`` spec (take a screenshot button)."""
    return {"@@widgetClass": "ScreenshotWidget", "placement": placement, **kwargs}


def fps_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create an ``FpsWidget`` spec (frames-per-second counter)."""
    return {"@@widgetClass": "_FpsWidget", "placement": placement, **kwargs}


def loading_widget(**kwargs) -> dict:
    """Create a ``LoadingWidget`` spec (spinner during layer loading)."""
    return {"@@widgetClass": "_LoadingWidget", **kwargs}


def timeline_widget(placement: str = "bottom-left", **kwargs) -> dict:
    """Create a ``TimelineWidget`` spec (time scrubber for animated layers)."""
    return {"@@widgetClass": "_TimelineWidget", "placement": placement, **kwargs}


def geocoder_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create a ``GeocoderWidget`` spec (address search)."""
    return {"@@widgetClass": "_GeocoderWidget", "placement": placement, **kwargs}


def theme_widget(**kwargs) -> dict:
    """Create a ``ThemeWidget`` spec (light/dark theme toggle)."""
    return {"@@widgetClass": "_ThemeWidget", **kwargs}


# ---------------------------------------------------------------------------
# deck.gl Experimental Widget helpers (v9.2+)
# ---------------------------------------------------------------------------

def context_menu_widget(**kwargs) -> dict:
    """Create a ``ContextMenuWidget`` spec (right-click context menu).

    Experimental — requires deck.gl >= 9.2.

    Parameters
    ----------
    **kwargs
        Widget properties, e.g. ``items`` list of menu items.
    """
    return {"@@widgetClass": "_ContextMenuWidget", **kwargs}


def info_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create an ``InfoWidget`` spec (displays layer hover/pick information).

    Experimental — requires deck.gl >= 9.2.

    Parameters
    ----------
    placement
        Widget placement (default ``"top-left"``).
    **kwargs
        Widget properties, e.g. ``text``, ``visible``, ``mode``.
    """
    return {"@@widgetClass": "_InfoWidget", "placement": placement, **kwargs}


def splitter_widget(**kwargs) -> dict:
    """Create a ``SplitterWidget`` spec (split-screen view divider).

    Experimental — requires deck.gl >= 9.2.  Allows the user to drag a
    handle to compare two overlapping views.

    Parameters
    ----------
    **kwargs
        Widget properties, e.g. ``viewId1``, ``viewId2``,
        ``orientation`` (``"horizontal"`` / ``"vertical"``),
        ``initialSplit`` (0–1 ratio).
    """
    return {"@@widgetClass": "_SplitterWidget", **kwargs}


def stats_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create a ``StatsWidget`` spec (GPU/CPU performance statistics).

    Experimental — requires deck.gl >= 9.2.

    Parameters
    ----------
    placement
        Widget placement (default ``"top-left"``).
    **kwargs
        Widget properties, e.g. ``type``, ``title``,
        ``framesPerUpdate``.
    """
    return {"@@widgetClass": "_StatsWidget", "placement": placement, **kwargs}


def view_selector_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create a ``ViewSelectorWidget`` spec (switch between view modes).

    Experimental — requires deck.gl >= 9.2.

    Parameters
    ----------
    placement
        Widget placement (default ``"top-left"``).
    **kwargs
        Widget properties, e.g. ``initialViewMode``.
    """
    return {"@@widgetClass": "_ViewSelectorWidget", "placement": placement, **kwargs}
