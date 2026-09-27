"""Deck.gl widget helpers (v0.8.0+)."""

from __future__ import annotations

import warnings

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
    # deck.gl 9.3/9.4 additions (1.12.0)
    "popup_widget",
    "icon_widget",
    "toggle_widget",
    "selector_widget",
    "scrollbar_widget",
]


# ---------------------------------------------------------------------------
# deck.gl Widget helpers (v0.8.0)
# ---------------------------------------------------------------------------

def zoom_widget(placement: str = "top-right", *, zoom_step: float | None = None, **kwargs) -> dict:
    """Create a ``ZoomWidget`` spec (zoom-in / zoom-out buttons).

    zoom_step
        Zoom levels per click (deck.gl 9.4; deck.gl's default is 1).
    """
    spec = {"@@widgetClass": "ZoomWidget", "placement": placement, **kwargs}
    if zoom_step is not None:
        spec["zoomStep"] = zoom_step
    return spec


def compass_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``CompassWidget`` spec (bearing indicator / reset)."""
    return {"@@widgetClass": "CompassWidget", "placement": placement, **kwargs}


def fullscreen_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``FullscreenWidget`` spec (toggle fullscreen).

    State changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    return {"@@widgetClass": "FullscreenWidget", "placement": placement, **kwargs}


def scale_widget(placement: str = "bottom-left", **kwargs) -> dict:
    """Create a ``ScaleWidget`` spec (distance scale bar)."""
    return {"@@widgetClass": "_ScaleWidget", "placement": placement, **kwargs}


def gimbal_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``GimbalWidget`` spec (3D camera gimbal control)."""
    return {"@@widgetClass": "GimbalWidget", "placement": placement, **kwargs}


def reset_view_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``ResetViewWidget`` spec (reset camera to initial state).

    State changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    return {"@@widgetClass": "ResetViewWidget", "placement": placement, **kwargs}


def screenshot_widget(placement: str = "top-right", **kwargs) -> dict:
    """Create a ``ScreenshotWidget`` spec (take a screenshot button)."""
    return {"@@widgetClass": "ScreenshotWidget", "placement": placement, **kwargs}


def popup_widget(
    position: list[float],
    content: str | dict,
    *,
    placement: str | None = None,
    **kwargs,
) -> dict:
    """Create a ``PopupWidget`` spec: a popup anchored at a map coordinate.

    Requires deck.gl >= 9.3.

    Parameters
    ----------
    position
        ``[longitude, latitude]`` (or ``[x, y]`` in a non-geospatial view).
    content
        Text, or ``{"text": ...}`` / ``{"html": ...}``.
    placement
        Where the popup sits relative to the anchor: a popover placement such
        as ``"top"`` or ``"bottom-start"`` (not a widget corner).

    Open/close changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    spec = {"@@widgetClass": "PopupWidget", "position": list(position), "content": content, **kwargs}
    if placement is not None:
        spec["placement"] = placement
    return spec


def icon_widget(icon: str, label: str | None = None, *, placement: str = "top-left", **kwargs) -> dict:
    """Create an ``IconWidget`` spec: a single button with a Material Symbols icon.

    Requires deck.gl >= 9.3. Clicks are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    spec = {"@@widgetClass": "IconWidget", "placement": placement, "icon": icon, **kwargs}
    if label is not None:
        spec["label"] = label
    return spec


def toggle_widget(
    icon: str,
    *,
    initial_checked: bool = False,
    on_icon: str | None = None,
    label: str | None = None,
    on_label: str | None = None,
    on_color: str | None = None,
    placement: str = "top-left",
    **kwargs,
) -> dict:
    """Create a ``ToggleWidget`` spec: an on/off button.

    Requires deck.gl >= 9.3. ``on_icon``/``on_label``/``on_color`` apply while
    the toggle is checked. The checked state is reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    spec = {"@@widgetClass": "ToggleWidget", "placement": placement, "icon": icon,
            "initialChecked": initial_checked, **kwargs}
    for key, value in (("onIcon", on_icon), ("label", label), ("onLabel", on_label), ("onColor", on_color)):
        if value is not None:
            spec[key] = value
    return spec


def selector_widget(
    options: list[dict],
    *,
    initial_value=None,
    tooltip: str | None = None,
    placement: str = "top-left",
    **kwargs,
) -> dict:
    """Create a ``SelectorWidget`` spec: a dropdown of options.

    Requires deck.gl >= 9.3.

    Parameters
    ----------
    options
        Each ``{"value": ..., "icon": "<Material Symbols name>", "label": ...}``;
        ``value`` and ``icon`` are required by deck.gl.

    The chosen value is reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    for opt in options:
        if not isinstance(opt, dict) or "value" not in opt or "icon" not in opt:
            raise ValueError("each selector option needs 'value' and 'icon' keys")
    spec = {"@@widgetClass": "SelectorWidget", "placement": placement, "options": list(options), **kwargs}
    if initial_value is not None:
        spec["initialValue"] = initial_value
    if tooltip is not None:
        spec["tooltip"] = tooltip
    return spec


def scrollbar_widget(orientation: str = "vertical", *, placement: str = "bottom-right", **kwargs) -> dict:
    """Create a ``ScrollbarWidget`` spec for large orthographic canvases.

    Requires deck.gl >= 9.4. ``orientation`` is ``"vertical"`` or ``"horizontal"``.
    """
    return {"@@widgetClass": "ScrollbarWidget", "placement": placement, "orientation": orientation, **kwargs}


def fps_widget(placement: str = "top-left", **kwargs) -> dict:
    """Deprecated: deck.gl 9.3 merged ``FpsWidget`` into ``StatsWidget``.

    Returns :func:`stats_widget` with the same arguments and warns. Removed in 2.0.
    """
    warnings.warn(
        "fps_widget() is deprecated: deck.gl 9.3 merged FpsWidget into "
        "StatsWidget. Use stats_widget() instead.",
        DeprecationWarning, stacklevel=2,
    )
    return stats_widget(placement=placement, **kwargs)


def loading_widget(**kwargs) -> dict:
    """Create a ``LoadingWidget`` spec (spinner during layer loading).

    State changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    return {"@@widgetClass": "_LoadingWidget", **kwargs}


def timeline_widget(placement: str = "bottom-left", **kwargs) -> dict:
    """Create a ``TimelineWidget`` spec (time scrubber for animated layers).

    Pass ``initialTime`` for an uncontrolled timeline; passing ``time`` /
    ``playing`` makes it controlled, i.e. it only moves when the server
    sends new values with :meth:`~shiny_deckgl.MapWidget.set_widgets`.

    State changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    return {"@@widgetClass": "_TimelineWidget", "placement": placement, **kwargs}


def geocoder_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create a ``GeocoderWidget`` spec (address search).

    State changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    return {"@@widgetClass": "_GeocoderWidget", "placement": placement, **kwargs}


def theme_widget(**kwargs) -> dict:
    """Create a ``ThemeWidget`` spec (light/dark theme toggle).

    State changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
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

    Expand/collapse changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    return {"@@widgetClass": "_StatsWidget", "placement": placement, **kwargs}


def view_selector_widget(placement: str = "top-left", **kwargs) -> dict:
    """Deprecated: deck.gl 9.x exports no ``ViewSelectorWidget``.

    Returns an empty spec, which the client drops, and warns. Removed in 2.0.
    """
    warnings.warn(
        "view_selector_widget() is deprecated: deck.gl 9.4 exports no "
        "ViewSelectorWidget, so it never rendered. It will be removed in 2.0.",
        DeprecationWarning, stacklevel=2,
    )
    return {}


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
    include_hidden: bool = False,
    **kwargs,
) -> dict:
    """Create a layer legend **widget** for deck.gl overlay layers.

    This is a deck.gl widget that participates in the widget system alongside
    ``ZoomWidget``, ``CompassWidget``, etc.  It can be toggled on/off via the
    ``widgets`` list passed to :meth:`~shiny_deckgl.MapWidget.update`.

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
        Toggles happen in the browser and are reported to the server as
        ``input[widget.legend_visibility_input_id]()``, a
        ``{"layer_id": str, "visible": bool}`` dict.  The next
        :meth:`~shiny_deckgl.MapWidget.update` resends each layer's
        ``visible`` prop, so apps that push updates should keep that
        prop in step with this input.  A layer unticked in the legend
        stays listed, unchecked, so it can be ticked again.
    collapsed
        Start the panel in collapsed state.  Once the user expands or
        collapses the panel, their choice survives layer updates until
        this value changes.
    title
        Optional header text.  When provided the panel is collapsible.
        A collapsed legend without a title gets a "Layers" header so it
        can still be opened.
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
    include_hidden
        Auto-introspect only.  When ``False`` (default), layers the server
        sent with ``visible=False`` are left out of the legend, so it lists
        the active layers.  When ``True``, they are listed unchecked, so the
        legend doubles as a layer switcher.
    """
    opts: dict = {
        "@@widgetClass": "_DeckLayerLegendWidget",
        "id": "deck-layer-legend",
        "placement": placement,
        "entries": list(entries) if entries else [],
        "showCheckbox": show_checkbox,
        "collapsed": collapsed,
        "autoIntrospect": auto_introspect,
        # Always sent, even when empty: deck.gl merges new widget props into
        # the old ones, so an omitted key would keep its previous value.
        "title": title,
        "excludeLayers": list(exclude_layers or []),
        "labelMap": dict(label_map or {}),
        "includeHidden": include_hidden,
        **kwargs,
    }
    return opts
