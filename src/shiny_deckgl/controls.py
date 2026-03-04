"""MapLibre GL control helpers and deck.gl legend control."""

from __future__ import annotations

__all__ = [
    "geolocate_control",
    "globe_control",
    "terrain_control",
    "legend_control",
    "opacity_control",
    "deck_legend_control",
    "CONTROL_TYPES",
    "CONTROL_POSITIONS",
]


# ---------------------------------------------------------------------------
# MapLibre GL control convenience helpers
# ---------------------------------------------------------------------------

def geolocate_control(position: str = "top-right", **options) -> dict:
    """Create a MapLibre ``GeolocateControl`` spec.

    Adds a button that uses the browser Geolocation API to locate the user
    on the map.

    Parameters
    ----------
    position
        Control position (default ``"top-right"``).
    **options
        Control options, e.g. ``trackUserLocation=True``,
        ``showAccuracyCircle=True``, ``positionOptions={"enableHighAccuracy": True}``.
    """
    return {"type": "geolocate", "position": position, "options": options}


def globe_control(position: str = "top-right", **options) -> dict:
    """Create a MapLibre ``GlobeControl`` spec (flat / globe toggle).

    Requires MapLibre GL JS >= 5.0.

    Parameters
    ----------
    position
        Control position (default ``"top-right"``).
    **options
        Control options forwarded to the MapLibre ``GlobeControl``
        constructor.
    """
    return {"type": "globe", "position": position, "options": options}


def terrain_control(position: str = "top-right", **options) -> dict:
    """Create a MapLibre ``TerrainControl`` spec (3-D terrain toggle).

    Requires MapLibre GL JS >= 5.0 and a terrain source in the style.

    Parameters
    ----------
    position
        Control position (default ``"top-right"``).
    **options
        Control options, e.g. ``source`` (terrain source id),
        ``exaggeration`` (height multiplier).
    """
    return {"type": "terrain", "position": position, "options": options}


def legend_control(
    targets: dict[str, str] | None = None,
    position: str = "bottom-left",
    *,
    show_default: bool = False,
    show_checkbox: bool = True,
    only_rendered: bool = True,
    reverse_order: bool = False,
    title: str | None = None,
) -> dict:
    """Create a legend control spec (``@watergis/maplibre-gl-legend``).

    Displays a collapsible legend panel generated from the MapLibre style.
    Layer visibility can optionally be toggled with checkboxes.

    Parameters
    ----------
    targets
        Dict mapping MapLibre layer ids to display labels, e.g.
        ``{"water": "Water bodies", "roads": "Roads"}``.  When ``None``
        (default), all layers are shown.
    position
        Control position (default ``"bottom-left"``).
    show_default
        Whether the legend panel is visible by default (``False``).
    show_checkbox
        Whether to show visibility checkboxes (``True``).
    only_rendered
        Show only layers that are currently rendered (``True``).
    reverse_order
        Reverse the layer order in the legend (``False``).
    title
        Legend panel title text.  ``None`` uses the plugin default.
    """
    opts: dict = {
        "showDefault": show_default,
        "showCheckbox": show_checkbox,
        "onlyRendered": only_rendered,
        "reverseOrder": reverse_order,
    }
    if targets is not None:
        opts["targets"] = targets
    if title is not None:
        opts["title"] = title
    return {"type": "legend", "position": position, "options": opts}


def opacity_control(
    position: str = "top-left",
    *,
    base_layers: dict[str, str] | None = None,
    over_layers: dict[str, str] | None = None,
    opacity_control_enabled: bool = True,
) -> dict:
    """Create an opacity / layer-switcher control (``maplibre-gl-opacity``).

    Displays radio buttons for base layers and checkboxes with opacity
    sliders for overlay layers.

    Parameters
    ----------
    position
        Control position (default ``"top-left"``).
    base_layers
        Dict mapping MapLibre layer ids to display labels for mutually
        exclusive base layers (radio buttons), e.g.
        ``{"osm": "OpenStreetMap", "satellite": "Satellite"}``.
    over_layers
        Dict mapping MapLibre layer ids to display labels for overlay
        layers (checkboxes + opacity slider), e.g.
        ``{"heatmap": "Heatmap", "contours": "Contours"}``.
    opacity_control_enabled
        Whether to show the opacity slider for overlay layers (``True``).
    """
    opts: dict = {
        "baseLayers": base_layers or {},
        "overLayers": over_layers or {},
        "opacityControl": opacity_control_enabled,
    }
    return {"type": "opacity", "position": position, "options": opts}


# ---------------------------------------------------------------------------
# Deck.gl legend control
# ---------------------------------------------------------------------------

def deck_legend_control(
    entries: list[dict],
    position: str = "bottom-right",
    *,
    show_checkbox: bool = True,
    collapsed: bool = False,
    title: str | None = None,
) -> dict:
    """Create a legend control for **deck.gl overlay layers**.

    Unlike :func:`legend_control` (which drives the ``@watergis/maplibre-gl-legend``
    plugin and can only see native MapLibre style layers), this control displays
    user-defined entries with color swatches and optional visibility checkboxes
    that toggle deck.gl layers on and off.

    Parameters
    ----------
    entries
        List of legend entry dicts.  Each entry supports:

        * ``layer_id`` — deck.gl layer id (used for the visibility checkbox).
        * ``label`` — human-readable display label.
        * ``color`` — ``[r, g, b]`` or ``[r, g, b, a]`` or CSS color string.
        * ``shape`` — swatch shape: ``"circle"`` (default), ``"rect"``,
          ``"line"``, ``"arc"``, or ``"gradient"``.
        * ``color2`` — second color for ``"arc"`` shape (gradient end).
        * ``colors`` — list of colors for ``"gradient"`` shape (e.g. for
          HeatmapLayer ``colorRange``).

        Example::

            entries=[
                {"layer_id": "ports", "label": "Ports", "color": [65, 182, 196], "shape": "circle"},
                {"layer_id": "mpa-zones", "label": "MPAs", "color": [0, 128, 0, 100], "shape": "rect"},
                {"layer_id": "port-arcs", "label": "Arcs", "color": [255, 140, 0],
                 "color2": [200, 0, 80], "shape": "arc"},
                {"layer_id": "observation-heat", "label": "Heat",
                 "colors": [[0, 25, 0], [0, 209, 0], [255, 255, 0], [255, 0, 0]],
                 "shape": "gradient"},
            ]

    position
        Control position (default ``"bottom-right"``).
    show_checkbox
        Show a checkbox per entry to toggle deck.gl layer visibility.
    collapsed
        Start the panel in collapsed state.
    title
        Optional header text.  When provided the panel is collapsible.
    """
    opts: dict = {
        "entries": list(entries),
        "showCheckbox": show_checkbox,
        "collapsed": collapsed,
    }
    if title is not None:
        opts["title"] = title
    return {"type": "deck_legend", "position": position, "options": opts}


# ---------------------------------------------------------------------------
# Control type & position constants
# ---------------------------------------------------------------------------

CONTROL_TYPES = {
    "navigation", "scale", "fullscreen", "geolocate",
    "globe", "terrain", "attribution",
    "legend", "opacity", "deck_legend",
}
CONTROL_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}
