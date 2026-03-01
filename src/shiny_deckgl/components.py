from __future__ import annotations

import base64
import html as _html_mod
import json
import pathlib
from functools import lru_cache
from importlib import resources as impresources
from shiny import ui
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import Session

from ._cdn import (
    DECKGL_JS,
    DECKGL_WIDGETS_JS,
    DECKGL_WIDGETS_CSS,
    MAPLIBRE_JS,
    MAPLIBRE_CSS,
    MAPBOX_DRAW_JS,
    MAPBOX_DRAW_CSS,
)

# ---------------------------------------------------------------------------
# Basemap style constants
# ---------------------------------------------------------------------------

CARTO_POSITRON = "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json"
CARTO_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json"
CARTO_VOYAGER = "https://basemaps.cartocdn.com/gl/voyager-nolabels-gl-style/style.json"
OSM_LIBERTY = "https://tiles.openfreemap.org/styles/liberty"


# ---------------------------------------------------------------------------
# Color scale utilities
# ---------------------------------------------------------------------------

# --- Built-in palettes (6 stops each) ---
PALETTE_VIRIDIS: list[list[int]] = [
    [68, 1, 84], [59, 82, 139], [33, 145, 140],
    [94, 201, 98], [253, 231, 37], [240, 249, 33],
]
PALETTE_PLASMA: list[list[int]] = [
    [13, 8, 135], [126, 3, 168], [204, 71, 120],
    [248, 149, 64], [252, 225, 56], [240, 249, 33],
]
PALETTE_OCEAN: list[list[int]] = [
    [0, 0, 40], [0, 30, 80], [0, 80, 120],
    [0, 140, 160], [60, 200, 180], [180, 240, 220],
]
PALETTE_THERMAL: list[list[int]] = [
    [4, 35, 51], [23, 82, 118], [81, 139, 116],
    [186, 177, 82], [227, 103, 55], [192, 39, 41],
]
PALETTE_CHLOROPHYLL: list[list[int]] = [
    [255, 255, 229], [194, 230, 153], [120, 198, 121],
    [49, 163, 84], [0, 104, 55], [0, 69, 41],
]


# ---------------------------------------------------------------------------
# Cached resource reader (O2 – avoid re-reading on every to_html call)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _read_bundled_resources() -> tuple[str, str]:
    """Read and cache the bundled JS and CSS files."""
    res = impresources.files("shiny_deckgl.resources")
    js_src = (res / "deckgl-init.js").read_text(encoding="utf-8")
    css_src = (res / "styles.css").read_text(encoding="utf-8")
    return js_src, css_src


def color_range(
    n: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Generate *n* evenly-spaced RGBA colours by linearly interpolating a palette.

    Parameters
    ----------
    n
        Number of output colours (default 6).
    palette
        Source palette as a list of ``[R, G, B]`` or ``[R, G, B, A]`` stops.
        Defaults to ``PALETTE_VIRIDIS``.

    Returns
    -------
    list[list[int]]
        ``n`` colours, each ``[R, G, B, 255]``.
    """
    palette = palette or PALETTE_VIRIDIS
    if n <= 0:
        return []
    if n == 1:
        c = palette[0]
        return [[c[0], c[1], c[2], c[3] if len(c) > 3 else 255]]
    stops = len(palette)
    result: list[list[int]] = []
    for i in range(n):
        t = i / (n - 1) * (stops - 1)
        lo = int(t)
        hi = min(lo + 1, stops - 1)
        frac = t - lo
        a = palette[lo]
        b = palette[hi]
        r = int(a[0] + (b[0] - a[0]) * frac)
        g = int(a[1] + (b[1] - a[1]) * frac)
        bl = int(a[2] + (b[2] - a[2]) * frac)
        result.append([r, g, bl, 255])
    return result


def color_bins(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a colour using equal-width bins.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of colour bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` colour per input value.
    """
    if not values:
        return []
    colours = color_range(n_bins, palette)
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1.0
    result: list[list[int]] = []
    for v in values:
        idx = int((v - lo) / span * (n_bins - 1))
        idx = max(0, min(idx, n_bins - 1))
        result.append(colours[idx])
    return result


def color_quantiles(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a colour using quantile-based bins.

    Each bin contains approximately the same number of values.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of colour bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` colour per input value.
    """
    if not values:
        return []
    colours = color_range(n_bins, palette)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # Compute quantile breakpoints
    breaks = [
        sorted_vals[min(int(i / n_bins * n), n - 1)]
        for i in range(1, n_bins)
    ]

    def _bin(v: float) -> int:
        for i, br in enumerate(breaks):
            if v <= br:
                return i
        return n_bins - 1

    return [colours[_bin(v)] for v in values]


# ---------------------------------------------------------------------------
# Data serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_data(data: Any) -> Any:
    """Convert pandas/geopandas objects to JSON-safe structures.

    - ``GeoDataFrame`` → GeoJSON ``FeatureCollection`` dict
    - ``DataFrame`` → list of row-dicts
    - Everything else is returned unchanged.
    """
    type_name = type(data).__name__
    if type_name == "GeoDataFrame":
        if hasattr(data, "__geo_interface__"):
            return data.__geo_interface__
        return json.loads(data.to_json())
    if type_name == "DataFrame":
        return data.to_dict(orient="records")
    return data


def encode_binary_attribute(array) -> dict:
    """Encode a numpy array as a base64 binary transport dict.

    deck.gl supports `binary attributes
    <https://deck.gl/docs/developer-guide/performance#supply-attributes-directly>`_
    for large datasets.  This helper converts a numpy array into a dict
    that the JS client decodes into a typed-array attribute.

    Parameters
    ----------
    array
        A ``numpy.ndarray`` (float32 or float64).

    Returns
    -------
    dict
        ``{"@@binary": True, "dtype": "float32", "size": <n_components>,
        "value": "<base64>"}``

    Example
    -------
    >>> import numpy as np
    >>> positions = np.array([[0.0, 51.5], [10.0, 48.8]], dtype="float32")
    >>> layer("ScatterplotLayer", "pts",
    ...       data={"length": len(positions)},
    ...       getPosition=encode_binary_attribute(positions))
    """
    import numpy as np  # noqa: local import — numpy is optional

    arr = np.ascontiguousarray(array)
    dtype_str = str(arr.dtype)
    if dtype_str not in ("float32", "float64", "uint8", "int32"):
        arr = arr.astype("float32")
        dtype_str = "float32"
    encoded = base64.b64encode(arr.tobytes()).decode("ascii")
    size = arr.shape[1] if arr.ndim > 1 else 1
    return {
        "@@binary": True,
        "dtype": dtype_str,
        "size": size,
        "value": encoded,
    }


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------

def map_view(**kwargs) -> dict:
    """Create a ``MapView`` spec.

    Parameters
    ----------
    **kwargs
        Any MapView properties (``controller``, ``x``, ``y``, ``width``,
        ``height``, etc.).
    """
    return {"@@type": "MapView", **kwargs}


def orthographic_view(**kwargs) -> dict:
    """Create an ``OrthographicView`` spec (non-geo flat plane).

    Useful for non-geographic visualisations such as graph plots.
    """
    return {"@@type": "OrthographicView", **kwargs}


def first_person_view(**kwargs) -> dict:
    """Create a ``FirstPersonView`` spec (immersive 3D walkthrough)."""
    return {"@@type": "FirstPersonView", **kwargs}


def globe_view(**kwargs) -> dict:
    """Create a ``GlobeView`` spec for a 3D globe projection.

    Renders the earth as a globe rather than a flat Mercator projection.
    """
    return {"@@type": "GlobeView", **kwargs}


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
    return {"@@widgetClass": "ScaleWidget", "placement": placement, **kwargs}


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
    return {"@@widgetClass": "FpsWidget", "placement": placement, **kwargs}


def loading_widget(**kwargs) -> dict:
    """Create a ``LoadingWidget`` spec (spinner during layer loading)."""
    return {"@@widgetClass": "LoadingWidget", **kwargs}


def timeline_widget(placement: str = "bottom-left", **kwargs) -> dict:
    """Create a ``TimelineWidget`` spec (time scrubber for animated layers)."""
    return {"@@widgetClass": "TimelineWidget", "placement": placement, **kwargs}


def geocoder_widget(placement: str = "top-left", **kwargs) -> dict:
    """Create a ``GeocoderWidget`` spec (address search)."""
    return {"@@widgetClass": "GeocoderWidget", "placement": placement, **kwargs}


def theme_widget(**kwargs) -> dict:
    """Create a ``ThemeWidget`` spec (light/dark theme toggle)."""
    return {"@@widgetClass": "ThemeWidget", **kwargs}


# ---------------------------------------------------------------------------
# Transition helper (v0.8.0)
# ---------------------------------------------------------------------------

def transition(duration: int = 1000, easing: str | None = None,
               type: str = "interpolation", **kwargs) -> dict:
    """Build a transition spec for a layer property.

    Parameters
    ----------
    duration
        Transition duration in milliseconds (used for ``"interpolation"``
        type only).
    easing
        Named easing function.  Supported values:
        ``"ease-in-cubic"``, ``"ease-out-cubic"``,
        ``"ease-in-out-cubic"``, ``"ease-in-out-sine"``.
        The JS client resolves these into real easing functions.
    type
        ``"interpolation"`` (default) or ``"spring"``.
    **kwargs
        Additional transition properties, e.g. ``stiffness``, ``damping``
        for spring type.

    Examples
    --------
    ::

        transitions={
            "getRadius": transition(800, easing="ease-in-out-cubic"),
            "getFillColor": transition(500),
        }
    """
    spec: dict = {"type": type, **kwargs}
    if type == "interpolation":
        spec["duration"] = duration
        if easing:
            spec["@@easing"] = easing
    return spec


CONTROL_TYPES = {
    "navigation", "scale", "fullscreen", "geolocate",
    "globe", "terrain", "attribution",
}
CONTROL_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}


class MapWidget:
    """Reusable deck.gl map widget for Shiny for Python.

    Parameters
    ----------
    id
        Unique HTML element ID for this map instance.
    view_state
        Initial map view state with ``longitude``, ``latitude``, ``zoom``,
        and optionally ``pitch``, ``bearing``, ``minZoom``, ``maxZoom``.
        Defaults to the Baltic Sea (Klaipeda region).
    style
        MapLibre style URL.  Use one of the ``CARTO_*`` / ``OSM_*``
        constants or pass any MapLibre-compatible style URL.
        Defaults to ``CARTO_POSITRON``.
    tooltip
        Tooltip configuration dict with:

        - ``html`` – template string with ``{field}`` placeholders, e.g.
          ``"<b>{name}</b><br/>depth: {depth} m"``
        - ``style`` (optional) – CSS dict, e.g.
          ``{"backgroundColor": "#222", "color": "#fff"}``

        Set to ``None`` (default) to disable tooltips.
    controls
        List of initial controls to add, each a dict with ``type``,
        ``position`` (optional, default ``"top-right"``), and ``options``
        (optional). Defaults to ``[{"type": "navigation"}]``.
    picking_radius
        Extra pixels around the pointer for picking (click/hover).
        Higher values make small objects easier to select.  Default ``0``.
    use_device_pixels
        Whether to use high-resolution rendering on HiDPI displays.
        ``True`` (default) uses the full device pixel ratio; ``False``
        renders at CSS pixels (faster).  An ``int`` value sets an explicit
        ratio.
    animate
        When ``True``, enables the deck.gl animation loop (required for
        ``TripsLayer`` and other time-based layers).  Default ``False``.
    parameters
        WebGL parameters dict, e.g. ``{"depthTest": False}``.
    controller
        Map controller configuration.  ``True`` (default) enables the
        default controller; ``False`` disables all interaction.  A dict
        can fine-tune behaviour, e.g.
        ``{"touchRotate": True, "doubleClickZoom": False}``.
    """

    def __init__(
        self,
        id: str,
        view_state: dict | None = None,
        style: str = CARTO_POSITRON,
        tooltip: dict | None = None,
        mapbox_api_key: str | None = None,
        controls: list[dict] | None = None,
        # Deck-level props (v0.7.0)
        picking_radius: int = 0,
        use_device_pixels: bool | int = True,
        animate: bool = False,
        parameters: dict | None = None,
        controller: bool | dict = True,
    ):
        self.id = id
        self.view_state = view_state or {
            "longitude": 21.1,
            "latitude": 55.7,
            "zoom": 8,
        }
        self.style = style
        self.tooltip = tooltip
        self.mapbox_api_key = mapbox_api_key
        self.controls = controls if controls is not None else [
            {"type": "navigation", "position": "top-right"},
        ]
        self.picking_radius = picking_radius
        self.use_device_pixels = use_device_pixels
        self.animate = animate
        self.parameters = parameters
        self.controller = controller

    # -- Shiny input property helpers -----------------------------------------

    @property
    def click_input_id(self) -> str:
        """The Shiny input name for click events on this map."""
        return f"{self.id}_click"

    @property
    def hover_input_id(self) -> str:
        """The Shiny input name for hover events on this map."""
        return f"{self.id}_hover"

    @property
    def view_state_input_id(self) -> str:
        """The Shiny input name for the current viewport state."""
        return f"{self.id}_view_state"

    @property
    def drag_input_id(self) -> str:
        """The Shiny input name for drag-marker events on this map."""
        return f"{self.id}_drag"

    @property
    def map_click_input_id(self) -> str:
        """Shiny input for map-level click events (fires even on empty areas).

        Returns ``{longitude, latitude, point: {x, y}}``.
        """
        return f"{self.id}_map_click"

    @property
    def map_contextmenu_input_id(self) -> str:
        """Shiny input for right-click / context-menu events on the map."""
        return f"{self.id}_map_contextmenu"

    # -- UI -------------------------------------------------------------------

    def ui(self, width: str = "100%", height: str = "400px") -> ui.Tag:
        """Return a Shiny ``ui.Tag`` div for this map widget.

        Parameters
        ----------
        width
            CSS width (default ``"100%"``).
        height
            CSS height (default ``"400px"``).
        """
        vs = self.view_state
        attrs: dict = {
            "id": self.id,
            "class_": "deckgl-map",
            "style": f"width:{width};height:{height};",
            "data_initial_longitude": str(vs.get("longitude", 0)),
            "data_initial_latitude": str(vs.get("latitude", 0)),
            "data_initial_zoom": str(vs.get("zoom", 1)),
            "data_initial_pitch": str(vs.get("pitch", 0)),
            "data_initial_bearing": str(vs.get("bearing", 0)),
            "data_initial_min_zoom": str(vs.get("minZoom", 0)),
            "data_initial_max_zoom": str(vs.get("maxZoom", 24)),
            "data_style": self.style,
        }
        if self.tooltip is not None:
            attrs["data_tooltip"] = json.dumps(self.tooltip)
        if self.mapbox_api_key is not None:
            attrs["data_mapbox_api_key"] = self.mapbox_api_key
        if self.controls:
            attrs["data_controls"] = json.dumps(self.controls)
        # Deck-level props (v0.7.0)
        if self.picking_radius != 0:
            attrs["data_picking_radius"] = str(self.picking_radius)
        if self.use_device_pixels is not True:
            attrs["data_use_device_pixels"] = json.dumps(self.use_device_pixels)
        if self.animate:
            attrs["data_animate"] = "true"
        if self.parameters is not None:
            attrs["data_parameters"] = json.dumps(self.parameters)
        if self.controller is not True:
            attrs["data_controller"] = json.dumps(self.controller)
        return ui.div(**attrs)

    # -- Server helpers -------------------------------------------------------

    async def update(
        self,
        session: Session,
        layers: list[dict],
        view_state: dict | None = None,
        transition_duration: int = 0,
        effects: list[dict] | None = None,
        views: list[dict] | None = None,
        # Deck-level props (v0.7.0)
        picking_radius: int | None = None,
        use_device_pixels: bool | int | None = None,
        animate: bool | None = None,
        # Widgets (v0.8.0)
        widgets: list[dict] | None = None,
    ) -> None:
        """Push a new set of deck.gl layers to this map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layers
            List of layer dicts (use the ``*_layer()`` helpers or ``layer()``).
        view_state
            Optional new view state to fly/jump to.
        transition_duration
            Milliseconds for a ``flyTo`` animation.  ``0`` (default) uses
            ``jumpTo`` for an instant move.
        effects
            Optional list of lighting/effect dicts, e.g.
            ``[{"type": "LightingEffect", "ambientLight": {...}, "pointLights": [...]}]``.
        views
            Optional list of view dicts (e.g. from ``map_view()``,
            ``orthographic_view()``).  When provided the JS client passes
            them to ``overlay.setProps({views})``.
        picking_radius
            Override picking radius for this update.
        use_device_pixels
            Override device pixel setting for this update.
        animate
            Override animation loop setting for this update.
        widgets
            Optional list of deck.gl widget dicts (e.g. from
            ``zoom_widget()``, ``compass_widget()``).  When provided the
            JS client passes them to ``overlay.setProps({widgets})``.
        """
        payload: dict = {
            "id": self.id,
            "layers": layers,
        }
        if view_state is not None:
            payload["viewState"] = view_state
            if transition_duration > 0:
                payload["transitionDuration"] = transition_duration
        if effects:
            payload["effects"] = effects
        if views:
            payload["views"] = views
        # Deck-level props
        if picking_radius is not None:
            payload["pickingRadius"] = picking_radius
        if use_device_pixels is not None:
            payload["useDevicePixels"] = use_device_pixels
        if animate is not None:
            payload["_animate"] = animate
        # Widgets
        if widgets is not None:
            payload["widgets"] = widgets
        await session.send_custom_message("deck_update", payload)

    async def set_layer_visibility(
        self,
        session: Session,
        visibility: dict[str, bool],
    ) -> None:
        """Toggle layer visibility without resending data.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        visibility
            Mapping of ``{layer_id: True/False}``.
        """
        await session.send_custom_message("deck_layer_visibility", {
            "id": self.id,
            "visibility": visibility,
        })

    async def set_controller(
        self,
        session: Session,
        options: bool | dict,
    ) -> None:
        """Configure map controller behaviour.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        options
            ``True`` enables the default controller.  ``False`` disables
            all map interaction.  A dict fine-tunes behaviour, e.g.
            ``{"touchRotate": True, "doubleClickZoom": False}``.
        """
        await session.send_custom_message("deck_set_controller", {
            "id": self.id,
            "controller": options,
        })

    async def set_widgets(
        self,
        session: Session,
        widgets: list[dict],
    ) -> None:
        """Update the deck.gl widget set without resending layers.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        widgets
            List of widget dicts (use the ``*_widget()`` helpers).
        """
        await session.send_custom_message("deck_set_widgets", {
            "id": self.id,
            "widgets": widgets,
        })

    async def fly_to(
        self,
        session: Session,
        longitude: float,
        latitude: float,
        zoom: float | None = None,
        pitch: float | None = None,
        bearing: float | None = None,
        speed: float = 1.2,
        duration: int | str = "auto",
    ) -> None:
        """Smooth fly-to camera transition using MapLibre ``flyTo``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude
            Target longitude.
        latitude
            Target latitude.
        zoom
            Target zoom level (optional).
        pitch
            Target pitch in degrees (optional).
        bearing
            Target bearing in degrees (optional).
        speed
            Fly speed multiplier (default ``1.2``).
        duration
            Duration in ms, or ``"auto"`` for MapLibre-calculated duration.
        """
        view_state: dict = {"longitude": longitude, "latitude": latitude}
        if zoom is not None:
            view_state["zoom"] = zoom
        if pitch is not None:
            view_state["pitch"] = pitch
        if bearing is not None:
            view_state["bearing"] = bearing
        await session.send_custom_message("deck_fly_to", {
            "id": self.id,
            "viewState": view_state,
            "speed": speed,
            "duration": duration,
        })

    async def ease_to(
        self,
        session: Session,
        longitude: float,
        latitude: float,
        zoom: float | None = None,
        pitch: float | None = None,
        bearing: float | None = None,
        duration: int = 1000,
    ) -> None:
        """Smooth ease-to camera transition using MapLibre ``easeTo``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude
            Target longitude.
        latitude
            Target latitude.
        zoom
            Target zoom level (optional).
        pitch
            Target pitch in degrees (optional).
        bearing
            Target bearing in degrees (optional).
        duration
            Duration in milliseconds (default ``1000``).
        """
        view_state: dict = {"longitude": longitude, "latitude": latitude}
        if zoom is not None:
            view_state["zoom"] = zoom
        if pitch is not None:
            view_state["pitch"] = pitch
        if bearing is not None:
            view_state["bearing"] = bearing
        await session.send_custom_message("deck_ease_to", {
            "id": self.id,
            "viewState": view_state,
            "duration": duration,
        })

    async def add_drag_marker(
        self,
        session: Session,
        longitude: float | None = None,
        latitude: float | None = None,
    ) -> None:
        """Place a draggable marker on the map.

        When the user finishes dragging, the new ``[lng, lat]`` is sent to
        ``input[widget.drag_input_id]()``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude
            Initial longitude (defaults to the centre of the current view).
        latitude
            Initial latitude (defaults to the centre of the current view).
        """
        await session.send_custom_message("deck_add_drag_marker", {
            "id": self.id,
            "longitude": longitude,
            "latitude": latitude,
        })

    async def set_style(
        self,
        session: Session,
        style: str,
    ) -> None:
        """Change the basemap style dynamically.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        style
            URL of the new map style JSON (e.g. a CARTO or MapLibre style).
        """
        self.style = style
        await session.send_custom_message("deck_set_style", {
            "id": self.id,
            "style": style,
        })

    async def update_tooltip(
        self,
        session: Session,
        tooltip: dict | None = None,
    ) -> None:
        """Update the tooltip configuration dynamically.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        tooltip
            New tooltip configuration dict (same format as the constructor's
            ``tooltip`` parameter), or ``None`` to disable tooltips.
        """
        self.tooltip = tooltip
        await session.send_custom_message("deck_update_tooltip", {
            "id": self.id,
            "tooltip": tooltip,
        })

    # -- Controls (v0.2.0) ---------------------------------------------------

    async def add_control(
        self,
        session: Session,
        control_type: str,
        position: str = "top-right",
        *,
        options: dict | None = None,
    ) -> None:
        """Add a MapLibre control to the map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        control_type
            One of: ``"navigation"``, ``"scale"``, ``"fullscreen"``,
            ``"geolocate"``, ``"globe"``, ``"terrain"``, ``"attribution"``.
        position
            Corner position: ``"top-left"``, ``"top-right"`` (default),
            ``"bottom-left"``, ``"bottom-right"``.
        options
            Optional dict of control-specific options, e.g.
            ``{"maxWidth": 200, "unit": "metric"}`` for ScaleControl,
            ``{"source": "terrain-dem", "exaggeration": 1.5}`` for TerrainControl.
        """
        if control_type not in CONTROL_TYPES:
            raise ValueError(
                f"Unknown control type {control_type!r}. "
                f"Valid types: {sorted(CONTROL_TYPES)}"
            )
        if position not in CONTROL_POSITIONS:
            raise ValueError(
                f"Unknown position {position!r}. "
                f"Valid positions: {sorted(CONTROL_POSITIONS)}"
            )
        await session.send_custom_message("deck_add_control", {
            "id": self.id,
            "controlType": control_type,
            "position": position,
            "options": options or {},
        })

    async def remove_control(
        self,
        session: Session,
        control_type: str,
    ) -> None:
        """Remove a previously added MapLibre control.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        control_type
            The control type string to remove (e.g. ``"scale"``).
        """
        await session.send_custom_message("deck_remove_control", {
            "id": self.id,
            "controlType": control_type,
        })

    # -- Bounds & Navigation (v0.2.0) ----------------------------------------

    async def fit_bounds(
        self,
        session: Session,
        bounds: list[list[float]],
        *,
        padding: int | dict[str, int] = 50,
        max_zoom: float | None = None,
        duration: int = 0,
    ) -> None:
        """Fly/jump the map to fit the given bounds.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        bounds
            ``[[sw_lng, sw_lat], [ne_lng, ne_lat]]`` in WGS 84.
            Example: ``[[10.0, 54.0], [30.0, 66.0]]`` for the Baltic Sea.
        padding
            Pixels of padding around the bounds. Can be an ``int`` (uniform)
            or a dict ``{"top": 10, "bottom": 10, "left": 10, "right": 10}``.
        max_zoom
            Maximum zoom level to use (prevents over-zooming on small areas).
        duration
            Animation duration in milliseconds. ``0`` (default) = instant.
        """
        payload: dict = {
            "id": self.id,
            "bounds": bounds,
            "padding": padding,
        }
        if max_zoom is not None:
            payload["maxZoom"] = max_zoom
        if duration > 0:
            payload["duration"] = duration
        await session.send_custom_message("deck_fit_bounds", payload)

    @staticmethod
    def compute_bounds(geojson: dict) -> list[list[float]]:
        """Compute ``[[sw_lng, sw_lat], [ne_lng, ne_lat]]`` from GeoJSON.

        Parameters
        ----------
        geojson
            A GeoJSON ``FeatureCollection``, ``Feature``, or geometry dict.

        Returns
        -------
        list[list[float]]
            ``[[min_lng, min_lat], [max_lng, max_lat]]``.
            Returns ``[[-180, -90], [180, 90]]`` if no coordinates found.
        """
        coords: list[list[float]] = []

        def _extract(geom: dict) -> None:
            gtype = geom.get("type", "")
            if gtype == "Point":
                coords.append(geom["coordinates"][:2])
            elif gtype in ("MultiPoint", "LineString"):
                coords.extend(c[:2] for c in geom["coordinates"])
            elif gtype in ("MultiLineString", "Polygon"):
                for ring in geom["coordinates"]:
                    coords.extend(c[:2] for c in ring)
            elif gtype == "MultiPolygon":
                for poly in geom["coordinates"]:
                    for ring in poly:
                        coords.extend(c[:2] for c in ring)
            elif gtype == "GeometryCollection":
                for g in geom.get("geometries", []):
                    _extract(g)

        if geojson.get("type") == "FeatureCollection":
            for f in geojson.get("features", []):
                if f.get("geometry"):
                    _extract(f["geometry"])
        elif geojson.get("type") == "Feature":
            if geojson.get("geometry"):
                _extract(geojson["geometry"])
        elif geojson.get("type"):
            _extract(geojson)

        if not coords:
            return [[-180, -90], [180, 90]]

        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return [[min(lngs), min(lats)], [max(lngs), max(lats)]]

    # -- Native MapLibre Sources & Layers (v0.3.0) ----------------------------

    async def add_source(
        self,
        session: Session,
        source_id: str,
        source_spec: dict,
    ) -> None:
        """Add a native MapLibre source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            Unique source identifier.
        source_spec
            MapLibre source specification dict. Must include ``"type"``
            (``"geojson"``, ``"raster"``, ``"vector"``, ``"raster-dem"``,
            ``"image"``).
        """
        await session.send_custom_message("deck_add_source", {
            "id": self.id,
            "sourceId": source_id,
            "spec": source_spec,
        })

    async def add_maplibre_layer(
        self,
        session: Session,
        layer_spec: dict,
        *,
        before_id: str | None = None,
    ) -> None:
        """Add a native MapLibre rendering layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_spec
            MapLibre layer specification dict with at minimum ``"id"``,
            ``"type"``, and ``"source"``.
        before_id
            Insert this layer before the given layer ID in the stack.
            ``None`` adds on top of all MapLibre layers.
        """
        payload: dict = {
            "id": self.id,
            "layerSpec": layer_spec,
        }
        if before_id is not None:
            payload["beforeId"] = before_id
        await session.send_custom_message("deck_add_maplibre_layer", payload)

    async def remove_maplibre_layer(
        self,
        session: Session,
        layer_id: str,
    ) -> None:
        """Remove a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The ``id`` of the MapLibre layer to remove.
        """
        await session.send_custom_message("deck_remove_maplibre_layer", {
            "id": self.id,
            "layerId": layer_id,
        })

    async def remove_source(
        self,
        session: Session,
        source_id: str,
    ) -> None:
        """Remove a native MapLibre source.

        All layers using this source must be removed first.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier to remove.
        """
        await session.send_custom_message("deck_remove_source", {
            "id": self.id,
            "sourceId": source_id,
        })

    async def set_source_data(
        self,
        session: Session,
        source_id: str,
        data: dict | str,
    ) -> None:
        """Update the data of an existing GeoJSON source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier (must be a GeoJSON source).
        data
            New GeoJSON dict or URL string.
        """
        serialised = _serialise_data(data)
        await session.send_custom_message("deck_set_source_data", {
            "id": self.id,
            "sourceId": source_id,
            "data": serialised,
        })

    # -- Custom Images / Icons ------------------------------------------------

    async def add_image(
        self,
        session: Session,
        image_id: str,
        url: str,
        *,
        pixel_ratio: float = 1,
        sdf: bool = False,
    ) -> None:
        """Load an image into the map for use with symbol layers.

        The image is fetched by the browser from *url* and registered under
        *image_id*.  Once loaded it can be referenced by a ``symbol`` layer's
        ``layout["icon-image"]`` property.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        image_id
            Unique name to register the image under.
        url
            HTTP(S) URL or data-URI of the image (PNG, JPEG, WebP, SVG).
        pixel_ratio
            Device pixel ratio for retina displays (default ``1``).
        sdf
            If ``True`` the image is treated as a signed-distance-field icon
            that can be recoloured at runtime with ``icon-color`` paint
            property.
        """
        await session.send_custom_message("deck_add_image", {
            "id": self.id,
            "imageId": image_id,
            "url": url,
            "pixelRatio": pixel_ratio,
            "sdf": sdf,
        })

    async def remove_image(
        self,
        session: Session,
        image_id: str,
    ) -> None:
        """Remove a previously loaded image from the map style.

        Any symbol layer still referencing this image will lose its icon.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        image_id
            The image name passed to :meth:`add_image`.
        """
        await session.send_custom_message("deck_remove_image", {
            "id": self.id,
            "imageId": image_id,
        })

    async def has_image(
        self,
        session: Session,
        image_id: str,
    ) -> None:
        """Check whether *image_id* is loaded and report back via input.

        The result is delivered asynchronously as a boolean through
        ``input.<map_id>_has_image``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        image_id
            The image name to check.
        """
        await session.send_custom_message("deck_has_image", {
            "id": self.id,
            "imageId": image_id,
        })

    # -- Runtime Style Mutation (v0.3.0) --------------------------------------

    async def set_paint_property(
        self,
        session: Session,
        layer_id: str,
        name: str,
        value,
    ) -> None:
        """Set a paint property on a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id.
        name
            Paint property name (e.g. ``"fill-opacity"``, ``"line-color"``).
        value
            New value (number, string, array, or MapLibre expression).
        """
        await session.send_custom_message("deck_set_paint_property", {
            "id": self.id,
            "layerId": layer_id,
            "name": name,
            "value": value,
        })

    async def set_layout_property(
        self,
        session: Session,
        layer_id: str,
        name: str,
        value,
    ) -> None:
        """Set a layout property on a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id.
        name
            Layout property name (e.g. ``"visibility"``).
        value
            New value (e.g. ``"visible"`` or ``"none"``).
        """
        await session.send_custom_message("deck_set_layout_property", {
            "id": self.id,
            "layerId": layer_id,
            "name": name,
            "value": value,
        })

    async def set_filter(
        self,
        session: Session,
        layer_id: str,
        filter_expr: list | None = None,
    ) -> None:
        """Set a data-driven filter on a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id.
        filter_expr
            A MapLibre filter expression, e.g.
            ``[">=", ["get", "depth"], 100]``. Pass ``None`` to clear.
        """
        await session.send_custom_message("deck_set_filter", {
            "id": self.id,
            "layerId": layer_id,
            "filter": filter_expr,
        })

    # -- Globe Projection (v0.4.0) -------------------------------------------

    async def set_projection(
        self,
        session: Session,
        projection: str = "mercator",
    ) -> None:
        """Set the map projection.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        projection
            ``"mercator"`` (default flat map) or ``"globe"`` (3D sphere).
            Requires MapLibre GL JS v4+.
        """
        if projection not in ("mercator", "globe"):
            raise ValueError(
                f"Unknown projection {projection!r}. Use 'mercator' or 'globe'."
            )
        await session.send_custom_message("deck_set_projection", {
            "id": self.id,
            "projection": projection,
        })

    # -- 3D Terrain & Sky (v0.4.0) -------------------------------------------

    async def set_terrain(
        self,
        session: Session,
        source: str | None = None,
        exaggeration: float = 1.0,
    ) -> None:
        """Enable or disable 3D terrain rendering.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source
            The id of a ``raster-dem`` source previously added via
            ``add_source()``. Pass ``None`` to disable terrain.
        exaggeration
            Vertical exaggeration factor (default 1.0 = real scale).
        """
        terrain = None
        if source is not None:
            terrain = {"source": source, "exaggeration": exaggeration}
        await session.send_custom_message("deck_set_terrain", {
            "id": self.id,
            "terrain": terrain,
        })

    async def set_sky(
        self,
        session: Session,
        sky: dict | None = None,
    ) -> None:
        """Set the sky/atmosphere properties (works best with terrain).

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        sky
            Sky specification dict. Pass ``None`` to reset to default.
        """
        await session.send_custom_message("deck_set_sky", {
            "id": self.id,
            "sky": sky,
        })

    # -- Native Popups (v0.4.0) ----------------------------------------------

    async def add_popup(
        self,
        session: Session,
        layer_id: str,
        template: str,
        *,
        close_button: bool = True,
        close_on_click: bool = True,
        max_width: str = "300px",
        anchor: str | None = None,
    ) -> None:
        """Attach a click popup to a native MapLibre layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id to attach the popup to.
        template
            HTML template string with ``{property}`` placeholders.
        close_button
            Show a close button (default True).
        close_on_click
            Close when clicking elsewhere on the map (default True).
        max_width
            CSS max-width of the popup container (default ``"300px"``).
        anchor
            Popup anchor position relative to the coordinate, or ``None``.
        """
        payload: dict = {
            "id": self.id,
            "layerId": layer_id,
            "template": template,
            "closeButton": close_button,
            "closeOnClick": close_on_click,
            "maxWidth": max_width,
        }
        if anchor is not None:
            payload["anchor"] = anchor
        await session.send_custom_message("deck_add_popup", payload)

    async def remove_popup(
        self,
        session: Session,
        layer_id: str,
    ) -> None:
        """Remove a previously attached popup handler from a native layer.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The MapLibre layer id whose popup handler should be removed.
        """
        await session.send_custom_message("deck_remove_popup", {
            "id": self.id,
            "layerId": layer_id,
        })

    @property
    def feature_click_input_id(self) -> str:
        """Shiny input for native layer feature clicks (with popup).

        Returns ``{layerId, properties, longitude, latitude}``.
        """
        return f"{self.id}_feature_click"

    # -- Spatial Queries (v0.4.0) ---------------------------------------------

    async def query_rendered_features(
        self,
        session: Session,
        *,
        point: list[float] | None = None,
        bounds: list[list[float]] | None = None,
        layers: list[str] | None = None,
        filter_expr: list | None = None,
        request_id: str = "default",
    ) -> None:
        """Query visible features at a point or within a bounding box.

        The result is delivered asynchronously as a Shiny input
        ``input.{id}_query_result()``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        point
            ``[x, y]`` pixel coordinates on the map canvas.
        bounds
            ``[[x1, y1], [x2, y2]]`` pixel bounding box.
        layers
            Optional list of layer ids to restrict the query.
        filter_expr
            Optional MapLibre filter expression.
        request_id
            Identifier included in the result for request matching.
        """
        payload: dict = {
            "id": self.id,
            "requestId": request_id,
        }
        if point is not None:
            payload["point"] = point
        elif bounds is not None:
            payload["bounds"] = bounds
        if layers is not None:
            payload["layers"] = layers
        if filter_expr is not None:
            payload["filter"] = filter_expr
        await session.send_custom_message("deck_query_features", payload)

    async def query_at_lnglat(
        self,
        session: Session,
        longitude: float,
        latitude: float,
        *,
        layers: list[str] | None = None,
        request_id: str = "default",
    ) -> None:
        """Query features at a geographic coordinate.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        longitude, latitude
            Geographic coordinates (WGS 84).
        layers
            Optional list of layer ids to restrict the query.
        request_id
            Identifier included in the result for request matching.
        """
        msg: dict[str, Any] = {
            "id": self.id,
            "longitude": longitude,
            "latitude": latitude,
            "requestId": request_id,
        }
        if layers is not None:
            msg["layers"] = layers
        await session.send_custom_message("deck_query_at_lnglat", msg)

    @property
    def query_result_input_id(self) -> str:
        """Shiny input for spatial query results.

        Returns ``{requestId: str, features: [GeoJSON features]}``.
        """
        return f"{self.id}_query_result"

    # -- Multiple Markers (v0.4.0) --------------------------------------------

    async def add_marker(
        self,
        session: Session,
        marker_id: str,
        longitude: float,
        latitude: float,
        *,
        color: str = "#3FB1CE",
        draggable: bool = False,
        popup_html: str | None = None,
    ) -> None:
        """Add a named marker to the map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        marker_id
            Unique identifier for this marker.
        longitude, latitude
            Marker position in WGS 84.
        color
            CSS color string for the default marker pin.
        draggable
            Whether the marker can be dragged by the user.
        popup_html
            HTML content for a popup shown when the marker is clicked.
        """
        await session.send_custom_message("deck_add_marker", {
            "id": self.id,
            "markerId": marker_id,
            "longitude": longitude,
            "latitude": latitude,
            "color": color,
            "draggable": draggable,
            "popupHtml": popup_html,
        })

    async def remove_marker(
        self,
        session: Session,
        marker_id: str,
    ) -> None:
        """Remove a named marker from the map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        marker_id
            The marker identifier to remove.
        """
        await session.send_custom_message("deck_remove_marker", {
            "id": self.id,
            "markerId": marker_id,
        })

    async def clear_markers(
        self,
        session: Session,
    ) -> None:
        """Remove all named markers from the map."""
        await session.send_custom_message("deck_clear_markers", {
            "id": self.id,
        })

    @property
    def marker_click_input_id(self) -> str:
        """Shiny input for named marker click events.

        Returns ``{markerId, longitude, latitude}``.
        """
        return f"{self.id}_marker_click"

    @property
    def marker_drag_input_id(self) -> str:
        """Shiny input for named marker drag-end events.

        Returns ``{markerId, longitude, latitude}``.
        """
        return f"{self.id}_marker_drag"

    # -- Drawing Tools (v0.5.0) -----------------------------------------------

    async def enable_draw(
        self,
        session: Session,
        *,
        modes: list[str] | None = None,
        controls: dict[str, bool] | None = None,
        default_mode: str = "simple_select",
    ) -> None:
        """Enable drawing tools on the map.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        modes
            Which drawing modes to enable. Defaults to all:
            ``["draw_point", "draw_line_string", "draw_polygon"]``.
        controls
            Override individual control visibility.
        default_mode
            Initial mode: ``"simple_select"`` or ``"direct_select"``.
        """
        payload: dict = {
            "id": self.id,
            "defaultMode": default_mode,
        }
        if modes is not None:
            payload["modes"] = modes
        if controls is not None:
            payload["controls"] = controls
        await session.send_custom_message("deck_enable_draw", payload)

    async def disable_draw(
        self,
        session: Session,
    ) -> None:
        """Remove drawing tools from the map."""
        await session.send_custom_message("deck_disable_draw", {
            "id": self.id,
        })

    async def get_drawn_features(
        self,
        session: Session,
    ) -> None:
        """Request the current set of drawn features.

        Result is delivered as ``input.{id}_drawn_features()``.
        """
        await session.send_custom_message("deck_get_drawn_features", {
            "id": self.id,
        })

    async def delete_drawn_features(
        self,
        session: Session,
        feature_ids: list[str] | None = None,
    ) -> None:
        """Delete drawn features.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        feature_ids
            List of feature IDs to delete. If ``None``, deletes all.
        """
        await session.send_custom_message("deck_delete_drawn", {
            "id": self.id,
            "featureIds": feature_ids,
        })

    @property
    def drawn_features_input_id(self) -> str:
        """Shiny input for drawn GeoJSON features."""
        return f"{self.id}_drawn_features"

    @property
    def draw_mode_input_id(self) -> str:
        """Shiny input for the current drawing mode."""
        return f"{self.id}_draw_mode"

    # -- GeoPandas Integration (v0.5.0) ---------------------------------------

    async def add_geodataframe(
        self,
        session: Session,
        source_id: str,
        gdf,
        *,
        layer_type: str = "fill",
        paint: dict | None = None,
        layout: dict | None = None,
        before_id: str | None = None,
        popup_template: str | None = None,
    ) -> None:
        """Add a GeoPandas GeoDataFrame as a native MapLibre layer.

        Convenience method that serialises, adds source + layer, and
        optionally attaches a popup.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            Unique source/layer identifier.
        gdf
            A ``geopandas.GeoDataFrame``.
        layer_type
            MapLibre layer type (default ``"fill"``).
        paint
            Paint properties dict.
        layout
            Layout properties dict.
        before_id
            Insert layer before this layer id.
        popup_template
            If provided, attach a popup with this HTML template.
        """
        geojson = _serialise_data(gdf)

        await self.add_source(session, source_id, {
            "type": "geojson",
            "data": geojson,
        })

        default_paint = {
            "fill": {"fill-color": "#088", "fill-opacity": 0.5},
            "line": {"line-color": "#333", "line-width": 2},
            "circle": {"circle-radius": 5, "circle-color": "#088"},
        }
        final_paint = paint or default_paint.get(layer_type, {})

        layer_id = f"{source_id}-layer"
        layer_spec: dict = {
            "id": layer_id,
            "type": layer_type,
            "source": source_id,
            "paint": final_paint,
        }
        if layout:
            layer_spec["layout"] = layout

        await self.add_maplibre_layer(session, layer_spec, before_id=before_id)

        if popup_template:
            await self.add_popup(session, layer_id, popup_template)

    async def update_geodataframe(
        self,
        session: Session,
        source_id: str,
        gdf,
    ) -> None:
        """Update the data of an existing GeoDataFrame source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier.
        gdf
            New ``geopandas.GeoDataFrame``.
        """
        geojson = _serialise_data(gdf)
        await self.set_source_data(session, source_id, geojson)

    # -- Feature State Management (v0.5.0) ------------------------------------

    async def set_feature_state(
        self,
        session: Session,
        source_id: str,
        feature_id: str | int,
        state: dict,
        *,
        source_layer: str | None = None,
    ) -> None:
        """Set the state of a feature in a source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source containing the feature.
        feature_id
            The feature's unique identifier.
        state
            State properties to set, e.g. ``{"hover": True}``.
        source_layer
            Required for vector tile sources.
        """
        payload: dict = {
            "id": self.id,
            "sourceId": source_id,
            "featureId": feature_id,
            "state": state,
        }
        if source_layer is not None:
            payload["sourceLayer"] = source_layer
        await session.send_custom_message("deck_set_feature_state", payload)

    async def remove_feature_state(
        self,
        session: Session,
        source_id: str,
        feature_id: str | int | None = None,
        *,
        key: str | None = None,
        source_layer: str | None = None,
    ) -> None:
        """Remove feature state.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source containing the feature(s).
        feature_id
            Feature to clear state for. ``None`` clears all features.
        key
            Specific state key to remove. ``None`` removes all.
        source_layer
            Required for vector tile sources.
        """
        payload: dict = {
            "id": self.id,
            "sourceId": source_id,
        }
        if feature_id is not None:
            payload["featureId"] = feature_id
        if key is not None:
            payload["key"] = key
        if source_layer is not None:
            payload["sourceLayer"] = source_layer
        await session.send_custom_message("deck_remove_feature_state", payload)

    # -- Map Export / Screenshot (v0.5.0) -------------------------------------

    async def export_image(
        self,
        session: Session,
        *,
        format: str = "png",
        quality: float = 0.92,
        request_id: str = "default",
    ) -> None:
        """Request a screenshot of the map.

        The base64-encoded image is returned asynchronously as
        ``input.{id}_export_result()``.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        format
            Image format: ``"png"`` (default), ``"jpeg"``, or ``"webp"``.
        quality
            JPEG/WebP quality (0.0–1.0). Ignored for PNG.
        request_id
            Identifier included in the result for request matching.
        """
        await session.send_custom_message("deck_export_image", {
            "id": self.id,
            "format": format,
            "quality": quality,
            "requestId": request_id,
        })

    @property
    def export_result_input_id(self) -> str:
        """Shiny input for map export results.

        Returns ``{requestId: str, dataUrl: str, width: int, height: int}``.
        """
        return f"{self.id}_export_result"

    @property
    def has_image_input_id(self) -> str:
        """Shiny input for :meth:`has_image` results.

        Returns ``{imageId: str, exists: bool}``.
        """
        return f"{self.id}_has_image"

    # -- Serialisation --------------------------------------------------------

    def to_json(self, layers: list[dict], effects: list[dict] | None = None) -> str:
        """Serialise the map spec (view state, style, layers, effects) to JSON.

        Parameters
        ----------
        layers
            List of layer dicts produced by ``layer()`` / ``*_layer()``
            helpers.
        effects
            Optional list of effects dicts.

        Returns
        -------
        str
            A JSON string with keys ``id``, ``viewState``, ``style``,
            ``tooltip``, ``layers``, and optionally ``effects``.
        """
        spec: dict = {
            "id": self.id,
            "viewState": self.view_state,
            "style": self.style,
            "layers": layers,
        }
        if self.tooltip is not None:
            spec["tooltip"] = self.tooltip
        if self.mapbox_api_key is not None:
            spec["mapboxApiKey"] = self.mapbox_api_key
        if effects:
            spec["effects"] = effects
        return json.dumps(spec, indent=2)

    @classmethod
    def from_json(cls, spec_json: str) -> tuple["MapWidget", list[dict]]:
        """Reconstruct a ``MapWidget`` and layer list from a JSON spec.

        Parameters
        ----------
        spec_json
            JSON string previously produced by ``to_json()``.

        Returns
        -------
        tuple[MapWidget, list[dict]]
            ``(widget, layers)`` ready for ``widget.update(session, layers)``.
        """
        spec = json.loads(spec_json)
        widget = cls(
            id=spec["id"],
            view_state=spec.get("viewState"),
            style=spec.get("style", CARTO_POSITRON),
            tooltip=spec.get("tooltip"),
            mapbox_api_key=spec.get("mapboxApiKey"),
        )
        layers = spec.get("layers", [])
        return widget, layers

    def to_html(
        self,
        layers: list[dict],
        path: str | pathlib.Path | None = None,
        effects: list[dict] | None = None,
        title: str = "shiny_deckgl Map",
    ) -> str:
        """Export the map as a standalone HTML file.

        The HTML file embeds CDN links for deck.gl and MapLibre, inlines
        the layer data, and can be opened in any browser without Shiny.

        Parameters
        ----------
        layers
            List of layer dicts.
        path
            Optional file path to write.  If ``None`` the HTML string is
            returned but not written to disk.
        effects
            Optional list of effects dicts.
        title
            HTML ``<title>`` content.

        Returns
        -------
        str
            The full HTML document.
        """
        js_src, css_src = _read_bundled_resources()

        vs = self.view_state
        tooltip_attr = ""
        if self.tooltip is not None:
            tooltip_json = json.dumps(self.tooltip)
            tooltip_attr = f' data-tooltip="{_html_mod.escape(tooltip_json, quote=True)}"'

        mapbox_attr = ""
        if self.mapbox_api_key:
            mapbox_attr = f' data-mapbox-api-key="{self.mapbox_api_key}"'

        layers_json = json.dumps(layers, indent=2)
        effects_json = json.dumps(effects or [], indent=2)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<script src="{DECKGL_JS}"></script>
<script src="{DECKGL_WIDGETS_JS}"></script>
<link rel="stylesheet" href="{DECKGL_WIDGETS_CSS}"/>
<script src="{MAPLIBRE_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_CSS}"/>
<script src="{MAPBOX_DRAW_JS}"></script>
<link rel="stylesheet" href="{MAPBOX_DRAW_CSS}"/>
<style>{css_src}</style>
</head>
<body>
<div id="{self.id}" class="deckgl-map"
     style="width:100%;height:100vh;"
     data-initial-longitude="{vs.get('longitude', 0)}"
     data-initial-latitude="{vs.get('latitude', 0)}"
     data-initial-zoom="{vs.get('zoom', 1)}"
     data-initial-pitch="{vs.get('pitch', 0)}"
     data-initial-bearing="{vs.get('bearing', 0)}"
     data-initial-min-zoom="{vs.get('minZoom', 0)}"
     data-initial-max-zoom="{vs.get('maxZoom', 24)}"
     data-style="{_html_mod.escape(self.style)}"
     {tooltip_attr}{mapbox_attr}></div>
<script>
// Shim: standalone pages have no Shiny runtime
if (typeof Shiny === 'undefined') {{
  window.Shiny = {{
    setInputValue: function() {{}},
    addCustomMessageHandler: function() {{}}
  }};
}}
</script>
<script>{js_src}</script>
<script>
(function() {{
  var initMap = window.__deckgl_initMap;
  var instances = window.__deckgl_instances;
  var buildDeckLayers = window.__deckgl_buildDeckLayers;
  var buildEffects = window.__deckgl_buildEffects;

  // Trigger init manually (no shiny:connected event in standalone mode)
  document.querySelectorAll('.deckgl-map').forEach(initMap);

  // Push layers & effects into the already-initialised overlay
  var layersData = {layers_json};
  var effectsData = {effects_json};

  Object.keys(instances).forEach(function(mapId) {{
    var inst = instances[mapId];
    var deckLayers = buildDeckLayers(
      JSON.parse(JSON.stringify(layersData)), mapId, inst.tooltipConfig
    );
    var overlayProps = {{ layers: deckLayers }};
    var effects = buildEffects(effectsData);
    if (effects) overlayProps.effects = effects;
    inst.map.on('load', function() {{
      inst.overlay.setProps(overlayProps);
    }});
  }});
}})();
</script>
</body>
</html>"""

        if path is not None:
            p = pathlib.Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html, encoding="utf-8")
        return html


# ---------------------------------------------------------------------------
# Generic layer helper
# ---------------------------------------------------------------------------

def layer(type: str, id: str, data=None, *, extensions: list | None = None, **kwargs) -> dict:
    """Create an arbitrary deck.gl layer definition.

    Works for *any* deck.gl layer class (e.g. ``"HeatmapLayer"``,
    ``"PathLayer"``, ``"ColumnLayer"``).  The JS client resolves
    ``deck[type]`` dynamically.

    Parameters
    ----------
    type
        deck.gl layer class name (e.g. ``"HeatmapLayer"``).
    id
        Unique layer identifier.
    data
        Layer data – list, dict, URL string, DataFrame, or GeoDataFrame.
    extensions
        Optional list of deck.gl extension specs.  Each element can be:

        - A **string** — extension class name, instantiated with no args::

              extensions=["BrushingExtension", "ClipExtension"]

        - A **[name, options] pair** (list or tuple) — instantiated with
          the given options dict::

              extensions=[["DataFilterExtension", {"filterSize": 2}]]

        Mixed forms are allowed::

              extensions=["ClipExtension",
                          ["DataFilterExtension", {"filterSize": 2}]]
    **kwargs
        Any additional deck.gl properties.  ``visible=False`` hides the
        layer without removing it from the stack.
    """
    lyr: dict = {"type": type, "id": id}
    if data is not None:
        lyr["data"] = _serialise_data(data)
    if extensions:
        resolved: list = []
        for ext in extensions:
            if isinstance(ext, str):
                resolved.append(ext)
            elif isinstance(ext, (list, tuple)) and len(ext) == 2:
                resolved.append({"@@extClass": ext[0], "@@extOpts": ext[1]})
            else:
                raise ValueError(
                    f"Invalid extension spec: {ext!r}. "
                    "Expected a string or a [name, options] pair."
                )
        lyr["@@extensions"] = resolved
    lyr.update(kwargs)
    return lyr


# ---------------------------------------------------------------------------
# Typed layer helpers (convenience wrappers around layer())
# ---------------------------------------------------------------------------

def scatterplot_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ScatterplotLayer`` definition.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points, a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``radiusScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getFillColor": [200, 0, 80, 180],
        "radiusMinPixels": 5,
    }
    defaults.update(kwargs)
    return layer("ScatterplotLayer", id, data, **defaults)


def geojson_layer(id: str, data: dict | list, **kwargs) -> dict:
    """Create a deck.gl ``GeoJsonLayer`` definition.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        A GeoJSON ``FeatureCollection`` or ``Feature`` dict, a URL, or a GeoDataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``lineWidthMinPixels``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getFillColor": [0, 128, 255, 120],
        "getLineColor": [0, 128, 255],
        "lineWidthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("GeoJsonLayer", id, data, **defaults)


def tile_layer(id: str, data: str | list, **kwargs) -> dict:
    """Create a deck.gl ``TileLayer`` for XYZ or WMS raster tiles.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        A URL template.  For XYZ tiles use ``{z}/{x}/{y}`` placeholders.
        For WMS, use a ``{bbox-epsg-3857}`` or ``{bbox-epsg-4326}``
        placeholder in the ``BBOX`` parameter — the JS client automatically
        converts tile bounds to the appropriate projection.  Example::

            "https://ows.emodnet-bathymetry.eu/wms?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            "&FORMAT=image/png&TRANSPARENT=true"
            "&LAYERS=emodnet:mean_atlas_land"
            "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
            "&BBOX={bbox-epsg-3857}"
    """
    defaults: dict[str, Any] = {
        "minZoom": 0,
        "maxZoom": 19,
        "tileSize": 256,
        "renderSubLayers": "@@BitmapLayer",
    }
    defaults.update(kwargs)
    return layer("TileLayer", id, data, **defaults)


def bitmap_layer(id: str, image: str, bounds: list, **kwargs) -> dict:
    """Create a deck.gl ``BitmapLayer`` for a static image overlay.

    Parameters
    ----------
    id
        Unique layer identifier.
    image
        The URL of the image.
    bounds
        ``[left, bottom, right, top]`` in WGS 84.
    """
    return layer("BitmapLayer", id, **{"image": image, "bounds": bounds, **kwargs})


# ---------------------------------------------------------------------------
# Additional layer helpers (v0.7.0)
# ---------------------------------------------------------------------------

def arc_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ArcLayer`` for drawing arcs between two points.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``sourcePosition`` and ``targetPosition`` keys,
        a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getSourceColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getSourceColor": [0, 128, 200],
        "getTargetColor": [200, 0, 80],
        "getWidth": 2,
    }
    defaults.update(kwargs)
    return layer("ArcLayer", id, data, **defaults)


def icon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``IconLayer`` for rendering icons at locations.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts, a remote data URL,
        or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``iconAtlas``, ``iconMapping``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getSize": 24,
        "sizeScale": 1,
    }
    defaults.update(kwargs)
    return layer("IconLayer", id, data, **defaults)


def path_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``PathLayer`` for rendering polylines.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with a ``path`` key (array of coordinates),
        a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPath": "@@d.path",
        "getColor": [0, 128, 255],
        "getWidth": 3,
        "widthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("PathLayer", id, data, **defaults)


def line_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``LineLayer`` for straight lines between two points.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``sourcePosition`` and ``targetPosition`` keys.
    **kwargs
        Extra deck.gl properties (e.g. ``getColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getColor": [0, 0, 0, 128],
        "getWidth": 1,
    }
    defaults.update(kwargs)
    return layer("LineLayer", id, data, **defaults)


def text_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``TextLayer`` for rendering text labels.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with a ``text`` key, a remote data URL,
        or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getText``, ``getSize``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getText": "@@d.text",
        "getSize": 16,
        "getColor": [0, 0, 0, 255],
        "getTextAnchor": "middle",
        "getAlignmentBaseline": "center",
    }
    defaults.update(kwargs)
    return layer("TextLayer", id, data, **defaults)


def column_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ColumnLayer`` for 3D columns.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``elevation`` key, coordinates, etc.
    **kwargs
        Extra deck.gl properties (e.g. ``radius``, ``extruded``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getElevation": "@@d.elevation",
        "getFillColor": [255, 140, 0],
        "radius": 100,
        "extruded": True,
    }
    defaults.update(kwargs)
    return layer("ColumnLayer", id, data, **defaults)


def polygon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``PolygonLayer`` for rendering filled polygons.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with a ``polygon`` key (array of coordinates).
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``extruded``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPolygon": "@@d.polygon",
        "getFillColor": [0, 128, 255, 80],
        "getLineColor": [0, 0, 0, 200],
        "getLineWidth": 1,
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("PolygonLayer", id, data, **defaults)


def heatmap_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``HeatmapLayer`` for density visualisation.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts, a remote data URL,
        or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``radiusPixels``, ``intensity``).
    """
    defaults: dict[str, Any] = {
        "getPosition": "@@d",
        "getWeight": 1,
        "radiusPixels": 30,
        "intensity": 1,
        "threshold": 0.05,
    }
    defaults.update(kwargs)
    return layer("HeatmapLayer", id, data, **defaults)


def hexagon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``HexagonLayer`` for hexagonal binning.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts.
    **kwargs
        Extra deck.gl properties (e.g. ``radius``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "radius": 1000,
        "elevationScale": 4,
        "extruded": True,
    }
    defaults.update(kwargs)
    return layer("HexagonLayer", id, data, **defaults)


def h3_hexagon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``H3HexagonLayer`` for H3 index-based hexagons.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``hex`` (H3 index) and ``color`` keys.
    **kwargs
        Extra deck.gl properties (e.g. ``getHexagon``, ``extruded``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getHexagon": "@@d.hex",
        "getFillColor": "@@d.color",
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("H3HexagonLayer", id, data, **defaults)
