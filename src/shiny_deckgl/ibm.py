"""Individual-Based Model (IBM) movement-visualisation assets.

This module provides **species-agnostic** visual assets and helpers for
rendering animal movement tracks on a deck.gl map.

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
    "Grey seal":    [100, 100, 100, 220],   # slate grey
    "Ringed seal":  [70, 140, 220, 220],    # icy blue
    "Harbour seal": [180, 140, 80, 220],    # sandy brown
}

# ---------------------------------------------------------------------------
# SVG icon atlas (base64-encoded sprite sheet for deck.gl IconLayer)
# ---------------------------------------------------------------------------
# Three 64×64 species-coloured seal silhouettes in a 192×64 strip.
# Each species has its own fill colour, a darker accent stroke for
# definition, a lighter belly patch, and a tiny eye dot.
# Base64 encoding is used for reliable loading across browsers.
# viewBox is 0 0 192 64, aligned with the on-screen sprite dimensions.
# Each species is drawn with SVG <path> elements for a realistic
# swimming-seal silhouette (torpedo body, rounded head, hind flippers).
#
# Grey seal    (x=0):   #7a8a8a slate-grey, bulky body, broad snout
# Ringed seal  (x=64):  #4a8cdc icy blue, slender body, small head
# Harbour seal (x=128): #c8a050 sandy gold, medium build, rounded head

#: Base64-encoded data-URI of the 192×64 SVG sprite-sheet.  Pass this as
#: ``iconAtlas`` to ``icon_layer()`` or the ``_tripsHeadIcons`` dict.
ICON_ATLAS: str = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIx"
    "OTIiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCAxOTIgNjQiPjxnIHRyYW5zZm9y"
    "bT0idHJhbnNsYXRlKDAsMCkiPjxwYXRoIGQ9Ik0gNiwzNCBDIDQsMzAgMywyOCA2"
    "LDI2IEwgOCwyNCBDIDEwLDIyIDEwLDI2IDEyLDI4IEMgMTYsMjIgMjQsMTggMzQs"
    "MTggQyA0MiwxOCA0OCwyMCA1MiwyNCBDIDU2LDI2IDU4LDI4IDU4LDMwIEMgNjAs"
    "MzEgNjAsMzMgNTgsMzQgQyA1NiwzNiA1NCwzOCA1MCwzOCBDIDQ2LDQwIDQwLDQy"
    "IDM0LDQyIEMgMjQsNDIgMTYsNDAgMTIsMzYgQyAxMCwzOCAxMCwzNiA4LDM4IEwg"
    "Niw0MCBDIDMsMzggNCwzNiA2LDM0IFoiIGZpbGw9IiM3YThhOGEiIHN0cm9rZT0i"
    "IzVhNmE2YSIgc3Ryb2tlLXdpZHRoPSIwLjgiLz48cGF0aCBkPSJNIDIwLDMwIEMg"
    "MjYsMjggNDAsMjggNDgsMzAgQyA0OCwzNCA0MCwzOCAzNCwzOCBDIDI2LDM4IDIw"
    "LDM0IDIwLDMwIFoiIGZpbGw9IiM5NWE1YTAiIG9wYWNpdHk9IjAuNCIvPjxlbGxp"
    "cHNlIGN4PSI0MCIgY3k9IjQwIiByeD0iNSIgcnk9IjIiIGZpbGw9IiM1YTZhNmEi"
    "IHRyYW5zZm9ybT0icm90YXRlKC0xNSw0MCw0MCkiLz48Y2lyY2xlIGN4PSIxMCIg"
    "Y3k9IjI2IiByPSIxLjIiIGZpbGw9IiMyMjIiIG9wYWNpdHk9IjAuNyIvPjwvZz48"
    "ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSg2NCwwKSI+PHBhdGggZD0iTSA4LDM0IEMg"
    "NiwzMSA1LDI5IDgsMjcgTCAxMCwyNSBDIDExLDIzIDExLDI3IDE0LDI5IEMgMTgs"
    "MjMgMjYsMjAgMzUsMjAgQyA0MiwyMCA0NywyMiA1MCwyNSBDIDUzLDI3IDU1LDI5"
    "IDU1LDMxIEMgNTcsMzIgNTcsMzQgNTUsMzUgQyA1MywzNyA1MSwzOCA0OCwzOCBD"
    "IDQ0LDQwIDM4LDQxIDM1LDQxIEMgMjYsNDEgMTgsMzkgMTQsMzYgQyAxMSwzNyAx"
    "MSwzNiAxMCwzOCBMIDgsMzkgQyA1LDM4IDYsMzYgOCwzNCBaIiBmaWxsPSIjNGE4"
    "Y2RjIiBzdHJva2U9IiMzNDZhYjAiIHN0cm9rZS13aWR0aD0iMC44Ii8+PHBhdGgg"
    "ZD0iTSAyMiwzMCBDIDI4LDI4IDQwLDI5IDQ3LDMxIEMgNDcsMzQgMzksMzcgMzUs"
    "MzcgQyAyNywzNyAyMiwzNCAyMiwzMCBaIiBmaWxsPSIjNmVhYWYwIiBvcGFjaXR5"
    "PSIwLjQiLz48ZWxsaXBzZSBjeD0iMzgiIGN5PSIzOS41IiByeD0iNCIgcnk9IjEu"
    "NSIgZmlsbD0iIzM0NmFiMCIgdHJhbnNmb3JtPSJyb3RhdGUoLTEyLDM4LDM5LjUp"
    "Ii8+PGNpcmNsZSBjeD0iMTIiIGN5PSIyNyIgcj0iMSIgZmlsbD0iIzIyMiIgb3Bh"
    "Y2l0eT0iMC43Ii8+PC9nPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEyOCwwKSI+"
    "PHBhdGggZD0iTSA3LDM0IEMgNSwzMSA0LDI5IDcsMjcgTCA5LDI1IEMgMTAsMjMg"
    "MTAsMjcgMTMsMjkgQyAxNywyMiAyNSwxOSAzNCwxOSBDIDQyLDE5IDQ3LDIxIDUx"
    "LDI0IEMgNTQsMjYgNTYsMjggNTYsMzEgQyA1OCwzMiA1OCwzNCA1NiwzNSBDIDU0"
    "LDM3IDUyLDM4IDQ5LDM4IEMgNDUsNDAgMzksNDIgMzQsNDIgQyAyNSw0MiAxNyw0"
    "MCAxMywzNiBDIDEwLDM3IDEwLDM2IDksMzggTCA3LDQwIEMgNCwzOCA1LDM2IDcs"
    "MzQgWiIgZmlsbD0iI2M4YTA1MCIgc3Ryb2tlPSIjOWE3YTMwIiBzdHJva2Utd2lk"
    "dGg9IjAuOCIvPjxwYXRoIGQ9Ik0gMjEsMzAgQyAyNywyOCA0MCwyOCA0OCwzMSBD"
    "IDQ4LDM0IDQwLDM4IDM0LDM4IEMgMjYsMzggMjEsMzQgMjEsMzAgWiIgZmlsbD0i"
    "I2UwYzg3OCIgb3BhY2l0eT0iMC40Ii8+PGVsbGlwc2UgY3g9IjM5IiBjeT0iNDAi"
    "IHJ4PSI0LjUiIHJ5PSIxLjgiIGZpbGw9IiM5YTdhMzAiIHRyYW5zZm9ybT0icm90"
    "YXRlKC0xNCwzOSw0MCkiLz48Y2lyY2xlIGN4PSIxMSIgY3k9IjI3IiByPSIxLjEi"
    "IGZpbGw9IiMyMjIiIG9wYWNpdHk9IjAuNyIvPjwvZz48L3N2Zz4="
)

#: deck.gl icon-mapping dict keyed by species name.
#: ``anchorY=32`` centres the icon vertically on the point.
ICON_MAPPING: dict[str, dict] = {
    "Grey seal":    {"x": 0,   "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Ringed seal":  {"x": 64,  "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Harbour seal": {"x": 128, "y": 0, "width": 64, "height": 64, "anchorY": 32},
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
