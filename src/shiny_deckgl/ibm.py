"""Individual-Based Model (IBM) movement-visualisation assets.

This module provides visual assets and helpers for rendering animal
movement tracks on a deck.gl map.  Nine Baltic Sea species are included:
seals (3), dolphins (3), and fish (3).

Visual Assets
-------------
* ``SPECIES_COLORS``  – RGBA look-up per species
* ``ICON_ATLAS``      – base64 data-URI of a 192×64 SVG sprite sheet
* ``ICON_MAPPING``    – deck.gl icon-mapping dict keyed by species

Data Helpers
------------
* ``format_trips()``  – convert raw coordinate lists into the dict
  format that ``trips_layer()`` expects

Shiny Modules
-------------
* ``trips_animation_ui()``     – Play/Pause/Reset buttons + speed &
  trail sliders (drop into any Shiny sidebar)
* ``trips_animation_server()`` – wires the buttons to
  ``MapWidget.trips_control()`` and exposes ``speed`` / ``trail``
  reactive inputs back to the caller
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import Session
    from .map_widget import MapWidget

__all__ = [
    "SPECIES_COLORS",
    "ICON_ATLAS",
    "ICON_MAPPING",
    "format_trips",
    "trips_animation_ui",
    "trips_animation_server",
]

# ---------------------------------------------------------------------------
# Species colour palette
# ---------------------------------------------------------------------------

#: RGBA colours per species for consistent rendering across layers.
SPECIES_COLORS: dict[str, list[int]] = {
    # Seals
    "Grey seal":            [100, 100, 100, 220],  # slate grey
    "Ringed seal":          [70, 140, 220, 220],   # icy blue
    "Harbour seal":         [180, 140, 80, 220],   # sandy brown
    # Dolphins
    "Harbour porpoise":     [90, 122, 138, 220],   # steel blue-grey
    "Bottlenose dolphin":   [106, 154, 176, 220],  # ocean blue
    "White-beaked dolphin": [138, 176, 192, 220],  # pale blue
    # Fish
    "Atlantic cod":         [138, 122, 90, 220],   # olive brown
    "Baltic herring":       [122, 138, 170, 220],  # steel blue
    "Atlantic salmon":      [192, 128, 96, 220],   # copper
    "European smelt":       [160, 180, 140, 220],  # olive green
}

# ---------------------------------------------------------------------------
# SVG icon atlas (base64-encoded sprite sheet for deck.gl IconLayer)
# ---------------------------------------------------------------------------
# Ten 64×64 species-coloured dorsal (top-down) silhouettes in a 640×64 strip.
# Each species has its own fill colour, a darker stroke for definition, and a
# midline spine accent.  All face RIGHT so the JS rotation logic (atan2) works.
# Base64 encoding is used for reliable loading across browsers.
#
# Seals (teardrop body, 4 splayed flippers, V-tail):
#   Grey seal         (x=0):   #7a8a8a — widest, bulky oval
#   Ringed seal       (x=64):  #4a8cdc — slender, elongated
#   Harbour seal      (x=128): #c8a050 — medium build
#
# Dolphins (streamlined torpedo, pectoral fin wings, horizontal tail flukes):
#   Harbour porpoise  (x=192): #5a7a8a — smallest, rounded snout
#   Bottlenose dolphin(x=256): #6a9ab0 — larger, pronounced beak
#   White-beaked dolphin(x=320):#8ab0c0 — short beak, wider body
#
# Fish (fusiform body, pectoral fin wings, forked tail):
#   Atlantic cod      (x=384): #8a7a5a — broad head, tapering
#   Baltic herring    (x=448): #7a8aaa — slender, deeply forked
#   Atlantic salmon   (x=512): #c08060 — robust, slightly forked
#   European smelt    (x=576): #a0b48c — small, slender

#: Base64-encoded data-URI of the 640×64 PNG sprite-sheet.  Pass this as
#: ``iconAtlas`` to ``icon_layer()`` or the ``_tripsHeadIcons`` dict.
ICON_ATLAS: str = (
    "data:image/png;base64,"
    "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"
    "AElFTkSuQmCC"
)

#: deck.gl icon-mapping dict keyed by species name.
#: ``anchorY=32`` centres the icon vertically on the point.
ICON_MAPPING: dict[str, dict] = {
    # Seals
    "Grey seal":            {"x": 0,   "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Ringed seal":          {"x": 64,  "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Harbour seal":         {"x": 128, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    # Dolphins
    "Harbour porpoise":     {"x": 192, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Bottlenose dolphin":   {"x": 256, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "White-beaked dolphin": {"x": 320, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    # Fish
    "Atlantic cod":         {"x": 384, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Baltic herring":       {"x": 448, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Atlantic salmon":      {"x": 512, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "European smelt":       {"x": 576, "y": 0, "width": 64, "height": 64, "anchorY": 32},
}


# ---------------------------------------------------------------------------
# Data helper — format_trips
# ---------------------------------------------------------------------------

def format_trips(
    paths: list[list[list[float]]],
    *,
    loop_length: int = 600,
    timestamps: list[list[int | float]] | None = None,
    properties: list[dict] | None = None,
) -> list[dict]:
    """Convert raw coordinate lists into the dict format ``trips_layer()`` expects.

    This bridges the gap between *"I have paths"* and *"trips_layer needs
    this exact dict structure"*.  You supply a list of 2-D paths (each a
    list of ``[lon, lat]`` pairs) and ``format_trips`` adds evenly-spaced
    timestamps, builds the 3-D ``[lon, lat, time]`` arrays, and merges in
    any per-trip metadata you provide.

    Parameters
    ----------
    paths
        One entry per trip.  Each entry is a list of coordinate pairs
        ``[[lon, lat], ...]``.  If a coordinate already has three
        elements ``[lon, lat, time]``, the third element is kept as the
        timestamp and the *timestamps* parameter is ignored for that
        trip.
    loop_length
        Total animation loop duration (arbitrary time units).  Used to
        auto-generate evenly-spaced timestamps when the path has only
        2-D coordinates and no explicit *timestamps* are supplied.
    timestamps
        Optional explicit per-trip timestamp arrays.  Must be the same
        length as *paths* and each inner list must match the
        corresponding path length.  If ``None``, timestamps are
        generated automatically from *loop_length*.
    properties
        Optional list of dicts (one per trip) with arbitrary extra keys
        (e.g. ``name``, ``species``, ``color``).  These are merged into
        the output dicts so that ``trips_layer`` accessors such as
        ``getColor="@@d.color"`` work.

    Returns
    -------
    list[dict]
        Each dict has at least:

        * ``path`` – list of ``[lon, lat, time]`` triplets
        * ``timestamps`` – flat list of time values

        Plus any keys supplied via *properties*.

    Examples
    --------
    >>> from shiny_deckgl.ibm import format_trips
    >>> trips = format_trips(
    ...     paths=[[[20.0, 57.0], [20.5, 57.2], [20.0, 57.0]]],
    ...     loop_length=100,
    ...     properties=[{"name": "Trip 1", "color": [255, 0, 0]}],
    ... )
    >>> trips[0]["path"][0]
    [20.0, 57.0, 0]
    """
    if properties is not None and len(properties) != len(paths):
        raise ValueError(
            f"properties length ({len(properties)}) must match "
            f"paths length ({len(paths)})"
        )
    if timestamps is not None and len(timestamps) != len(paths):
        raise ValueError(
            f"timestamps length ({len(timestamps)}) must match "
            f"paths length ({len(paths)})"
        )

    result: list[dict] = []

    for idx, path in enumerate(paths):
        n_pts = len(path)
        if n_pts == 0:
            continue

        # Determine timestamps for this trip
        has_3d = len(path[0]) >= 3
        if has_3d:
            ts = [pt[2] for pt in path]
            path_3d = [[pt[0], pt[1], pt[2]] for pt in path]
        elif timestamps is not None:
            ts = list(timestamps[idx])
            if len(ts) != n_pts:
                raise ValueError(
                    f"timestamps[{idx}] length ({len(ts)}) != "
                    f"path length ({n_pts})"
                )
            path_3d = [[pt[0], pt[1], t] for pt, t in zip(path, ts)]
        else:
            # Auto-generate evenly spaced
            if n_pts == 1:
                ts = [0]
            else:
                ts = [int(i * loop_length / (n_pts - 1)) for i in range(n_pts)]
            path_3d = [[pt[0], pt[1], t] for pt, t in zip(path, ts)]

        trip: dict[str, Any] = {
            "path": path_3d,
            "timestamps": ts,
        }

        # Merge user-supplied properties
        if properties is not None:
            trip.update(properties[idx])

        result.append(trip)

    return result


# ---------------------------------------------------------------------------
# Shiny module — trips animation controls
# ---------------------------------------------------------------------------

def trips_animation_ui(
    id: str,
    *,
    speed_default: float = 8.0,
    speed_min: float = 0.5,
    speed_max: float = 100.0,
    speed_step: float = 0.5,
    trail_default: int = 180,
    trail_min: int = 20,
    trail_max: int = 400,
    trail_step: int = 10,
):
    """UI fragment for TripsLayer animation controls.

    Drop this into a sidebar or card to get Play / Pause / Reset
    buttons plus speed and trail-length sliders.  Wire it up on the
    server side with :func:`trips_animation_server`.

    Parameters
    ----------
    id
        Shiny module namespace ID (e.g. ``"seal_anim"``).
    speed_default / speed_min / speed_max / speed_step
        Initial value and range for the animation speed slider.
    trail_default / trail_min / trail_max / trail_step
        Initial value and range for the trail length slider.

    Returns
    -------
    shiny.ui.TagList
        Ready to embed in a sidebar or layout.
    """
    from shiny import module, ui as _ui  # deferred to avoid import at load

    @module.ui
    def _inner_ui():
        return _ui.TagList(
            _ui.layout_columns(
                _ui.input_action_button(
                    "play", "\u25B6 Play", class_="btn-sm btn-success",
                ),
                _ui.input_action_button(
                    "pause", "\u23F8 Pause", class_="btn-sm btn-warning",
                ),
                _ui.input_action_button(
                    "reset", "\u23F9 Reset", class_="btn-sm btn-danger",
                ),
                col_widths=(4, 4, 4),
            ),
            _ui.input_slider(
                "speed", "Animation speed",
                min=speed_min, max=speed_max, value=speed_default,
                step=speed_step,
            ),
            _ui.input_slider(
                "trail", "Trail length",
                min=trail_min, max=trail_max, value=trail_default,
                step=trail_step,
            ),
        )

    return _inner_ui(id)


def trips_animation_server(
    id: str,
    *,
    widget: "MapWidget",
    session: "Session",
):
    """Server logic for TripsLayer animation controls.

    Wires the Play / Pause / Reset buttons produced by
    :func:`trips_animation_ui` to the widget's ``trips_control``
    method.  Returns a namespace object whose ``.speed()`` and
    ``.trail()`` reactive accessors mirror the slider values so
    the caller can feed them into ``trips_layer()``.

    Parameters
    ----------
    id
        Must match the *id* passed to :func:`trips_animation_ui`.
    widget
        The :class:`~shiny_deckgl.MapWidget` that hosts the TripsLayer.
    session
        The active Shiny ``Session``.

    Returns
    -------
    types.SimpleNamespace
        ``.speed`` and ``.trail`` — callable reactive values
        (``input.speed`` and ``input.trail`` from the module).

    Example
    -------
    ::

        anim = trips_animation_server("seal_anim", widget=my_widget, session=session)
        # Later, inside a reactive effect:
        speed = anim.speed()
        trail = anim.trail()
    """
    import types
    from shiny import module, reactive

    result_holder: list = []

    @module.server
    def _inner_server(input, output, inner_session):
        @reactive.Effect
        @reactive.event(input.play)
        async def _play():
            await widget.trips_control(session, "resume")

        @reactive.Effect
        @reactive.event(input.pause)
        async def _pause():
            await widget.trips_control(session, "pause")

        @reactive.Effect
        @reactive.event(input.reset)
        async def _reset():
            await widget.trips_control(session, "reset")

        result_holder.append(
            types.SimpleNamespace(speed=input.speed, trail=input.trail)
        )

    _inner_server(id)
    return result_holder[0]
