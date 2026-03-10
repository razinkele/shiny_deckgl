"""Deck.gl widget helpers (v0.8.0+)."""

from __future__ import annotations

__all__ = [
    "zoom_widget",
    "compass_widget",
    "fullscreen_widget",
    "scale_widget",
    "gimbal_widget",
    "reset_view_widget",
    "screenshot_widget",
    "fps_widget",
    "loading_widget",
    "timeline_widget",
    "geocoder_widget",
    "theme_widget",
    "context_menu_widget",
    "info_widget",
    "splitter_widget",
    "stats_widget",
    "view_selector_widget",
    "layer_legend_widget",
]


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


# ---------------------------------------------------------------------------
# shiny_deckgl custom widgets
# ---------------------------------------------------------------------------

def layer_legend_widget(
    entries: list[dict] | None = None,
    placement: str = "top-left",
    *,
    show_checkbox: bool = True,
    collapsed: bool = False,
    title: str | None = None,
    auto_introspect: bool = False,
    exclude_layers: list[str] | None = None,
    label_map: dict[str, str] | None = None,
    **kwargs,
) -> dict:
    """Create a layer legend **widget** for deck.gl overlay layers.

    Unlike :func:`~shiny_deckgl.controls.deck_legend_control` (which is a
    MapLibre IControl), this is a deck.gl widget that participates in the
    widget system alongside ``ZoomWidget``, ``CompassWidget``, etc.  It can
    be toggled on/off via the ``widgets`` list passed to
    :meth:`~shiny_deckgl.MapWidget.update`.

    Parameters
    ----------
    entries
        List of legend entry dicts.  When provided, these are used as-is
        (manual mode).  When ``None`` or empty **and** ``auto_introspect``
        is ``True``, the widget reads the active deck.gl layers at runtime
        and generates entries automatically.

        Each entry supports:

        * ``layer_id`` — deck.gl layer id (used for the visibility checkbox).
        * ``label`` — human-readable display label.
        * ``color`` — ``[r, g, b]`` or ``[r, g, b, a]`` or CSS color string.
        * ``shape`` — swatch shape: ``"circle"`` (default), ``"rect"``,
          ``"line"``, ``"arc"``, or ``"gradient"``.
        * ``color2`` — second color for ``"arc"`` shape.
        * ``colors`` — list of colors for ``"gradient"`` shape.

    placement
        Widget placement (default ``"top-left"``).
    show_checkbox
        Show a checkbox per entry to toggle deck.gl layer visibility.
    collapsed
        Start the panel in collapsed state.
    title
        Optional header text.  When provided the panel is collapsible.
    auto_introspect
        When ``True`` and no manual ``entries`` are given, the widget
        introspects active deck.gl layers on the client side and generates
        legend entries automatically.  It detects layer type → swatch shape,
        and extracts static colors from layer props (``getFillColor``,
        ``getColor``, ``colorRange``, etc.).
    exclude_layers
        Layer IDs to exclude from auto-introspected legend.
    label_map
        ``{layer_id: display_label}`` overrides for auto-introspected labels.
    """
    opts: dict = {
        "@@widgetClass": "_DeckLayerLegendWidget",
        "id": "deck-layer-legend",
        "placement": placement,
        "entries": list(entries) if entries else [],
        "showCheckbox": show_checkbox,
        "collapsed": collapsed,
        "autoIntrospect": auto_introspect,
        **kwargs,
    }
    if title is not None:
        opts["title"] = title
    if exclude_layers:
        opts["excludeLayers"] = list(exclude_layers)
    if label_map:
        opts["labelMap"] = dict(label_map)
    return opts
