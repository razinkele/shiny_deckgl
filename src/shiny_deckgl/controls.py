"""MapLibre GL control helpers and deck.gl legend control."""

from __future__ import annotations

__all__ = [
    "geolocate_control",
    "globe_control",
    "terrain_control",
    "legend_control",
    "opacity_control",
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
    reverse_order: bool = True,
    title: str | None = None,
) -> dict:
    """Create a legend control spec (``@watergis/maplibre-gl-legend``).

    Displays a collapsible legend panel generated from the MapLibre style.
    Layer visibility can optionally be toggled with checkboxes.  Only native
    MapLibre layers appear; deck.gl overlay layers need
    :func:`~shiny_deckgl.layer_legend_widget`.

    Parameters
    ----------
    targets
        Dict mapping MapLibre layer ids to display labels, e.g.
        ``{"water": "Water bodies", "roads": "Roads"}``.  When ``None``
        (default), the legend lists the native layers the app added with
        ``add_maplibre_layer`` / ``add_geodataframe`` / ``add_cluster_layer``
        (labelled by id), and follows them as they are added or removed.
        Pass ``{}`` to list every layer of the style, basemap included.
    position
        Control position (default ``"bottom-left"``).
    show_default
        When ``True`` the panel starts open and stays open.  When ``False``
        (default) it starts closed and closes again on any click outside it.
    show_checkbox
        Whether to show visibility checkboxes (``True``).  Toggles only
        change the browser; the server is not told.
    only_rendered
        Show only layers that are currently rendered (``True``).  Either
        way the plugin runs a full ``queryRenderedFeatures()`` on every pan
        and style change, which can take tens of milliseconds on dense
        vector basemaps.
    reverse_order
        List layers top-most first, the way they are stacked on the map
        (``True``, the plugin's own default).
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
# Control type & position constants
# ---------------------------------------------------------------------------

CONTROL_TYPES = {
    "navigation", "scale", "fullscreen", "geolocate",
    "globe", "terrain", "attribution",
    "legend", "opacity",
}
CONTROL_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}
