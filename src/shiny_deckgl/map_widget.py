"""MapWidget — the core reusable deck.gl map widget for Shiny for Python."""

from __future__ import annotations

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
    MAPLIBRE_LEGEND_JS,
    MAPLIBRE_LEGEND_CSS,
    MAPLIBRE_OPACITY_JS,
    MAPLIBRE_OPACITY_CSS,
)
from .colors import CARTO_POSITRON
from .controls import CONTROL_TYPES, CONTROL_POSITIONS
from ._data_utils import _serialise_data

__all__ = ["MapWidget"]

# Pre-computed sorted constants for validation error messages (avoid sorting on every error)
_CONTROL_TYPES_SORTED: tuple[str, ...] = tuple(sorted(CONTROL_TYPES))
_CONTROL_POSITIONS_SORTED: tuple[str, ...] = tuple(sorted(CONTROL_POSITIONS))


def _validate_choice(value: str, valid_values: set[str], name: str, sorted_values: tuple[str, ...]) -> None:
    """Validate that value is in valid_values, raising ValueError if not.

    Parameters
    ----------
    value
        The value to validate.
    valid_values
        Set of valid values.
    name
        Human-readable name for error messages (e.g., "control type").
    sorted_values
        Pre-sorted tuple of valid values for error message.

    Raises
    ------
    ValueError
        If value is not in valid_values.
    """
    if value not in valid_values:
        raise ValueError(
            f"Unknown {name} {value!r}. "
            f"Valid {name}s: {sorted_values}"
        )

# Hoist the namespace resolver import to module level so we pay the
# try/except cost once at import time, not on every MapWidget instantiation.
try:
    from shiny._namespaces import resolve_id as _shiny_resolve_id
except (ImportError, AttributeError):  # pragma: no cover — future-proofing
    _shiny_resolve_id = None  # type: ignore[assignment]


def _resolve_ns(raw_id: str) -> str:
    """Resolve *raw_id* through the current Shiny module namespace.

    Inside a ``@module.ui`` or ``@module.server`` context this returns
    the fully-qualified (namespaced) ID, e.g. ``"mod-my_map"``.
    Outside any module the raw ID is returned unchanged.

    The function gracefully falls back to the bare ID when the private
    ``shiny._namespaces`` API is unavailable (future-proofing).
    """
    if _shiny_resolve_id is not None:
        try:
            return str(_shiny_resolve_id(raw_id))
        except (TypeError, ValueError):  # pragma: no cover — defensive
            pass
    return raw_id


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
    cooperative_gestures
        When ``True``, requires Ctrl+scroll to zoom and two-finger drag
        on touch devices.  Useful when the map is embedded in a scrollable
        page.  Default ``False``.
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
        # Rendering mode (v0.9.0)
        interleaved: bool = False,
        # Cooperative gestures (v1.0.0)
        cooperative_gestures: bool = False,
    ):
        # Resolve through the current Shiny module namespace so the
        # widget works identically inside and outside @module.ui /
        # @module.server — no manual module.resolve_id() needed.
        self._bare_id: str = id
        self.id: str = _resolve_ns(id)
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
        self.interleaved = interleaved
        self.cooperative_gestures = cooperative_gestures

    # -- Shiny input property helpers -----------------------------------------

    @property
    def click_input_id(self) -> str:
        """The Shiny input name for click events on this map.

        Returns the *bare* (un-namespaced) name so it can be used
        directly with the module ``input`` object, which auto-prepends
        the namespace.
        """
        return f"{self._bare_id}_click"

    @property
    def hover_input_id(self) -> str:
        """The Shiny input name for hover events on this map."""
        return f"{self._bare_id}_hover"

    @property
    def view_state_input_id(self) -> str:
        """The Shiny input name for the current viewport state."""
        return f"{self._bare_id}_view_state"

    @property
    def drag_input_id(self) -> str:
        """The Shiny input name for drag-marker events on this map."""
        return f"{self._bare_id}_drag"

    @property
    def map_click_input_id(self) -> str:
        """Shiny input for map-level click events (fires even on empty areas).

        Returns ``{longitude, latitude, point: {x, y}}``.
        """
        return f"{self._bare_id}_map_click"

    @property
    def map_contextmenu_input_id(self) -> str:
        """Shiny input for right-click / context-menu events on the map."""
        return f"{self._bare_id}_map_contextmenu"

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
        # Always emit data-controls so JS can distinguish "no controls"
        # (empty list) from "use defaults" (attribute absent).
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
        if self.interleaved:
            attrs["data_interleaved"] = "true"
        if self.cooperative_gestures:
            attrs["data_cooperative_gestures"] = "true"
        return ui.div(**attrs)

    # -- Server helpers -------------------------------------------------------

    async def update(
        self,
        session: "Session",
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

        .. tip::
           ``update()`` serialises **every** layer to JSON on each call.
           For apps that mix infrequently-changing static layers (e.g.
           bathymetry heatmap) with rapidly-updating dynamic layers (e.g.
           agent positions every 100 ms), prefer :meth:`partial_update`
           for the dynamic layers — it only serialises the layers you
           pass and merges by ``id`` on the JS side, reducing
           serialisation cost by 80–90 %.

        See Also
        --------
        partial_update : Sparse layer patches (dynamic layers only).
        patch_layer : Convenience wrapper for patching a single layer.
        set_layer_visibility : Toggle visibility without resending data.
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

    async def partial_update(
        self,
        session: "Session",
        layers: list[dict],
    ) -> None:
        """Push sparse layer patches — only changed **layer** properties are sent.

        Each dict in *layers* must contain an ``"id"`` key matching a
        previously-sent layer.  Only the properties present in the patch
        are overwritten; all other properties (including binary-encoded
        positions) are preserved from the JS-side cache.

        New layer IDs (not in the cache) are appended.

        .. note::
           This method patches **layer** properties only.  Deck-level
           props (``effects``, ``views``, ``widgets``, ``picking_radius``,
           etc.) are not affected — use :meth:`update` for those.

        .. tip::
           **When to use:** Call ``partial_update()`` for layers whose
           data changes frequently (e.g. per simulation tick), while
           keeping static layers untouched.  Only the layers you include
           are serialised and sent over the WebSocket.

        See Also
        --------
        update : Full layer-stack replacement (use for initial load or
            when the entire landscape changes).
        patch_layer : Single-layer convenience wrapper.
        """
        # Serialise any DataFrames / GeoDataFrames in patch data fields
        for lyr in layers:
            if "data" in lyr:
                lyr["data"] = _serialise_data(lyr["data"])
        await session.send_custom_message("deck_partial_update", {
            "id": self.id,
            "layers": layers,
        })

    async def patch_layer(
        self,
        session: "Session",
        layer_id: str,
        **props: Any,
    ) -> None:
        """Patch a single layer's properties without resending the full stack.

        Convenience wrapper around :meth:`partial_update` for the common
        case of tweaking one layer at a time.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The ``id`` of the layer to patch (must match a previously-sent layer).
        **props
            Layer properties to overwrite, e.g. ``radiusPixels=50``,
            ``getFillColor=[255, 0, 0]``, ``visible=False``.

        Example
        -------
        ::

            await widget.patch_layer(session, "heatmap",
                                     radiusPixels=50, intensity=2.0)
        """
        await self.partial_update(session, [{"id": layer_id, **props}])

    async def trips_control(
        self,
        session: "Session",
        action: str = "pause",
    ) -> None:
        """Pause, resume, or reset a TripsLayer animation.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        action
            One of ``"pause"`` (freeze at current time), ``"resume"``
            (continue from paused time), or ``"reset"`` (restart from
            time 0).
        """
        if action not in ("pause", "resume", "reset"):
            raise ValueError(f"action must be 'pause', 'resume', or 'reset', got {action!r}")
        await session.send_custom_message("deck_trips_control", {
            "id": self.id,
            "action": action,
        })

    async def set_layer_visibility(
        self,
        session: "Session",
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
        session: "Session",
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

    async def set_cooperative_gestures(
        self,
        session: "Session",
        enabled: bool,
    ) -> None:
        """Toggle cooperative gestures on the map.

        When cooperative gestures are enabled, the user must hold **Ctrl**
        (or **⌘** on macOS) while scrolling to zoom, and two-finger drag
        is required on touch devices.  This is useful when the map is
        embedded in a scrollable page.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        enabled
            ``True`` to enable cooperative gestures, ``False`` to disable.
        """
        self.cooperative_gestures = enabled
        await session.send_custom_message("deck_set_cooperative_gestures", {
            "id": self.id,
            "enabled": enabled,
        })

    async def set_widgets(
        self,
        session: "Session",
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

    @staticmethod
    def _build_view_state(
        longitude: float,
        latitude: float,
        zoom: float | None = None,
        pitch: float | None = None,
        bearing: float | None = None,
    ) -> dict:
        """Build a partial view-state dict, omitting ``None`` values."""
        vs: dict = {"longitude": longitude, "latitude": latitude}
        if zoom is not None:
            vs["zoom"] = zoom
        if pitch is not None:
            vs["pitch"] = pitch
        if bearing is not None:
            vs["bearing"] = bearing
        return vs

    async def fly_to(
        self,
        session: "Session",
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
        await session.send_custom_message("deck_fly_to", {
            "id": self.id,
            "viewState": self._build_view_state(longitude, latitude, zoom, pitch, bearing),
            "speed": speed,
            "duration": duration,
        })

    async def ease_to(
        self,
        session: "Session",
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
        await session.send_custom_message("deck_ease_to", {
            "id": self.id,
            "viewState": self._build_view_state(longitude, latitude, zoom, pitch, bearing),
            "duration": duration,
        })

    async def add_drag_marker(
        self,
        session: "Session",
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
        session: "Session",
        style: str,
        *,
        diff: bool = False,
    ) -> None:
        """Change the basemap style dynamically.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        style
            URL of the new map style JSON (e.g. a CARTO or MapLibre style).
        diff
            When ``True``, MapLibre computes a diff between the current
            and new style and only applies the changes.  This preserves
            existing sources and layers that are unchanged.  Default
            ``False`` (full style replacement).
        """
        self.style = style
        await session.send_custom_message("deck_set_style", {
            "id": self.id,
            "style": style,
            "diff": diff,
        })

    async def update_tooltip(
        self,
        session: "Session",
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

    async def update_legend(
        self,
        session: "Session",
        entries: list[dict],
        title: str | None = None,
        show_checkbox: bool = True,
        collapsed: bool = False,
        position: str = "bottom-right",
    ) -> None:
        """Update or create a deck.gl legend control dynamically.

        Patches the existing :class:`DeckLegendControl` on the JS side,
        or creates one if none exists yet.  This allows switching legend
        entries when the user toggles between layers with different color
        schemes — without resending the full controls list.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        entries
            Legend entry dicts (same format as
            :func:`~shiny_deckgl.controls.deck_legend_control`).
        title
            Optional header text.
        show_checkbox
            Show a checkbox per entry to toggle layer visibility.
        collapsed
            Start the panel in collapsed state.
        position
            Control position (default ``"bottom-right"``).  Only used
            when creating a new legend; ignored if one already exists.
        """
        _validate_choice(position, CONTROL_POSITIONS, "position", _CONTROL_POSITIONS_SORTED)
        await session.send_custom_message("deck_update_legend", {
            "id": self.id,
            "entries": list(entries),
            "title": title,
            "showCheckbox": show_checkbox,
            "collapsed": collapsed,
            "position": position,
        })

    async def set_animation(
        self,
        session: "Session",
        layer_id: str,
        enabled: bool = True,
    ) -> None:
        """Start or stop a client-side property animation.

        Targets a layer whose properties include :func:`animate_prop`
        markers.  Stopping freezes the animated value at its current
        position; restarting resumes from where it stopped.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The ``id`` of the layer containing animated properties.
        enabled
            ``True`` to start/resume, ``False`` to freeze.
        """
        await session.send_custom_message("deck_set_animation", {
            "id": self.id,
            "layerId": layer_id,
            "enabled": enabled,
        })

    # -- Controls (v0.2.0) ---------------------------------------------------

    async def add_control(
        self,
        session: "Session",
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
            ``"geolocate"``, ``"globe"``, ``"terrain"``, ``"attribution"``,
            ``"legend"``, ``"opacity"``.
        position
            Corner position: ``"top-left"``, ``"top-right"`` (default),
            ``"bottom-left"``, ``"bottom-right"``.
        options
            Optional dict of control-specific options, e.g.
            ``{"maxWidth": 200, "unit": "metric"}`` for ScaleControl,
            ``{"source": "terrain-dem", "exaggeration": 1.5}`` for TerrainControl.
        """
        _validate_choice(control_type, CONTROL_TYPES, "control type", _CONTROL_TYPES_SORTED)
        _validate_choice(position, CONTROL_POSITIONS, "position", _CONTROL_POSITIONS_SORTED)
        await session.send_custom_message("deck_add_control", {
            "id": self.id,
            "controlType": control_type,
            "position": position,
            "options": options or {},
        })

    async def remove_control(
        self,
        session: "Session",
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

    async def set_controls(
        self,
        session: "Session",
        controls: list[dict],
    ) -> None:
        """Replace **all** MapLibre controls on the map at once.

        Existing controls are removed before the new set is applied.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        controls
            A list of control dicts, each containing ``type``,
            ``position`` (default ``"top-right"``), and ``options``
            (default ``{}``).  Use the ``*_control()`` helpers or
            build dicts manually.

        Examples
        --------
        ::

            await widget.set_controls(session, [
                {"type": "navigation", "position": "top-right"},
                legend_control(show_default=True),
                geolocate_control(),
            ])
        """
        payload_controls = []
        for ctrl in controls:
            ct = ctrl.get("type", "")
            _validate_choice(ct, CONTROL_TYPES, "control type", _CONTROL_TYPES_SORTED)
            pos = ctrl.get("position", "top-right")
            _validate_choice(pos, CONTROL_POSITIONS, "control position", _CONTROL_POSITIONS_SORTED)
            payload_controls.append({
                "type": ct,
                "position": pos,
                "options": ctrl.get("options", {}),
            })
        await session.send_custom_message("deck_set_controls", {
            "id": self.id,
            "controls": payload_controls,
        })

    # -- Bounds & Navigation (v0.2.0) ----------------------------------------

    async def fit_bounds(
        self,
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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

    # -- Cluster Layers (v1.0.0) ----------------------------------------------

    async def add_cluster_layer(
        self,
        session: "Session",
        source_id: str,
        data: dict | str | list,
        *,
        cluster_radius: int = 50,
        cluster_max_zoom: int = 14,
        cluster_color: str = "#51bbd6",
        cluster_stroke_color: str = "#ffffff",
        cluster_stroke_width: int = 1,
        cluster_text_color: str = "#ffffff",
        cluster_text_size: int = 12,
        point_color: str = "#11b4da",
        point_radius: int = 5,
        point_stroke_color: str = "#ffffff",
        point_stroke_width: int = 1,
        size_steps: list | None = None,
        cluster_properties: dict | None = None,
    ) -> None:
        """Add clustered GeoJSON points with click-to-zoom.

        Creates a GeoJSON source with ``cluster: true`` plus three MapLibre
        layers (cluster circles, count labels, and unclustered points).
        Clicking a cluster zooms in to expand it.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            Unique source identifier.  Three layers will be created:
            ``{source_id}-clusters``, ``{source_id}-count``, and
            ``{source_id}-unclustered``.
        data
            GeoJSON ``FeatureCollection`` (dict), URL string, or list of
            ``[lon, lat]`` pairs (auto-wrapped into a FeatureCollection).
        cluster_radius
            Pixel radius within which points are merged.
        cluster_max_zoom
            Maximum zoom level at which clusters are generated.
        cluster_color
            Fill color for cluster circles.
        cluster_stroke_color
            Stroke color for cluster circles.
        cluster_stroke_width
            Stroke width for cluster circles.
        cluster_text_color
            Color for cluster count labels.
        cluster_text_size
            Font size for cluster count labels.
        point_color
            Fill color for unclustered point circles.
        point_radius
            Radius for unclustered point circles.
        point_stroke_color
            Stroke color for unclustered point circles.
        point_stroke_width
            Stroke width for unclustered point circles.
        size_steps
            List of ``[count_threshold, circle_radius]`` pairs for
            interpolating cluster circle size.  Defaults to
            ``[[0, 18], [100, 24], [750, 32]]``.
        cluster_properties
            MapLibre ``clusterProperties`` for aggregate computations.
        """
        # Auto-wrap a list of [lon, lat] into a GeoJSON FeatureCollection
        if isinstance(data, list) and data and isinstance(data[0], (list, tuple)):
            data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": pt[:2]},
                        "properties": pt[2] if len(pt) > 2 and isinstance(pt[2], dict) else {},
                    }
                    for pt in data
                ],
            }

        serialised = _serialise_data(data)

        options: dict = {
            "clusterRadius": cluster_radius,
            "clusterMaxZoom": cluster_max_zoom,
            "clusterColor": cluster_color,
            "clusterStrokeColor": cluster_stroke_color,
            "clusterStrokeWidth": cluster_stroke_width,
            "clusterTextColor": cluster_text_color,
            "clusterTextSize": cluster_text_size,
            "pointColor": point_color,
            "pointRadius": point_radius,
            "pointStrokeColor": point_stroke_color,
            "pointStrokeWidth": point_stroke_width,
        }
        if size_steps is not None:
            options["sizeSteps"] = size_steps
        if cluster_properties is not None:
            options["clusterProperties"] = cluster_properties

        await session.send_custom_message("deck_add_cluster_layer", {
            "id": self.id,
            "sourceId": source_id,
            "data": serialised,
            "options": options,
        })

    async def remove_cluster_layer(
        self,
        session: "Session",
        source_id: str,
    ) -> None:
        """Remove a cluster layer group created by :meth:`add_cluster_layer`.

        Removes the three MapLibre layers (``-clusters``, ``-count``,
        ``-unclustered``) and the underlying GeoJSON source.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        source_id
            The source identifier used in :meth:`add_cluster_layer`.
        """
        await session.send_custom_message("deck_remove_cluster_layer", {
            "id": self.id,
            "sourceId": source_id,
        })

    # -- Custom Images / Icons ------------------------------------------------

    async def add_image(
        self,
        session: "Session",
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
            that can be recolored at runtime with ``icon-color`` paint
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
        layer_id: str,
        name: str,
        value: Any,
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
        session: "Session",
        layer_id: str,
        name: str,
        value: Any,
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        return f"{self._bare_id}_feature_click"

    # -- Spatial Queries (v0.4.0) ---------------------------------------------

    async def query_rendered_features(
        self,
        session: "Session",
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
        session: "Session",
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
        return f"{self._bare_id}_query_result"

    # -- Multiple Markers (v0.4.0) --------------------------------------------

    async def add_marker(
        self,
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        return f"{self._bare_id}_marker_click"

    @property
    def marker_drag_input_id(self) -> str:
        """Shiny input for named marker drag-end events.

        Returns ``{markerId, longitude, latitude}``.
        """
        return f"{self._bare_id}_marker_drag"

    # -- Drawing Tools (v0.5.0) -----------------------------------------------

    async def enable_draw(
        self,
        session: "Session",
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
        session: "Session",
    ) -> None:
        """Remove drawing tools from the map."""
        await session.send_custom_message("deck_disable_draw", {
            "id": self.id,
        })

    async def get_drawn_features(
        self,
        session: "Session",
    ) -> None:
        """Request the current set of drawn features.

        Result is delivered as ``input.{id}_drawn_features()``.
        """
        await session.send_custom_message("deck_get_drawn_features", {
            "id": self.id,
        })

    async def delete_drawn_features(
        self,
        session: "Session",
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
        return f"{self._bare_id}_drawn_features"

    @property
    def draw_mode_input_id(self) -> str:
        """Shiny input for the current drawing mode."""
        return f"{self._bare_id}_draw_mode"

    # -- GeoPandas Integration (v0.5.0) ---------------------------------------

    async def add_geodataframe(
        self,
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        session: "Session",
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
        return f"{self._bare_id}_export_result"

    @property
    def has_image_input_id(self) -> str:
        """Shiny input for :meth:`has_image` results.

        Returns ``{imageId: str, exists: bool}``.
        """
        return f"{self._bare_id}_has_image"

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
            # Escape the API key to prevent XSS in HTML attribute context
            escaped_key = _html_mod.escape(self.mapbox_api_key, quote=True)
            mapbox_attr = f' data-mapbox-api-key="{escaped_key}"'

        layers_json = json.dumps(layers, indent=2)
        effects_json = json.dumps(effects or [], indent=2)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{_html_mod.escape(title)}</title>
<script src="{DECKGL_JS}"></script>
<script src="{DECKGL_WIDGETS_JS}"></script>
<link rel="stylesheet" href="{DECKGL_WIDGETS_CSS}"/>
<script src="{MAPLIBRE_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_CSS}"/>
<script src="{MAPBOX_DRAW_JS}"></script>
<link rel="stylesheet" href="{MAPBOX_DRAW_CSS}"/>
<script src="{MAPLIBRE_LEGEND_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_LEGEND_CSS}"/>
<script src="{MAPLIBRE_OPACITY_JS}"></script>
<link rel="stylesheet" href="{MAPLIBRE_OPACITY_CSS}"/>
<style>{css_src}</style>
</head>
<body>
<div id="{_html_mod.escape(self.id)}" class="deckgl-map"
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
      structuredClone(layersData), mapId, inst.tooltipConfig
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
