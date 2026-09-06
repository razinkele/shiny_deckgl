"""Viewport-aware data loading helpers."""

from __future__ import annotations

from typing import Any

__all__ = ["in_bounds", "on_viewport_change"]


def in_bounds(point: dict[str, Any], bounds: dict[str, list[float]] | None) -> bool:
    """Check if a point falls within viewport bounds.

    Parameters
    ----------
    point
        Dict with either ``lon``/``lat`` keys or a ``position`` key
        containing ``[lon, lat, ...]``.
    bounds
        Dict with ``sw`` and ``ne`` keys, each ``[lon, lat]``.
        If ``None``, returns ``True`` (no filtering).

    Returns
    -------
    bool
        ``True`` if the point center is within bounds (inclusive).

    Note
    ----
    Checks the point center only, not area. Grid cells whose center
    is outside the viewport but whose area overlaps will be excluded.
    """
    if bounds is None:
        return True

    if "position" in point:
        lon, lat = point["position"][0], point["position"][1]
    else:
        lon, lat = point["lon"], point["lat"]

    sw = bounds["sw"]
    ne = bounds["ne"]
    if sw[0] <= ne[0]:
        lon_ok = sw[0] <= lon <= ne[0]
    else:
        # Antimeridian wrap: sw.lng > ne.lng
        lon_ok = lon >= sw[0] or lon <= ne[0]
    return lon_ok and sw[1] <= lat <= ne[1]


MAX_FALLBACK_POLLS = 10
"""How many times the viewport fallback re-arms before giving up."""


def _should_repoll(viewport_available: bool, attempts: int) -> bool:
    """Whether the viewport fallback should schedule another poll.

    Once the real view state has arrived the ordinary reactive dependency takes
    over, and an unbounded poll would keep re-pushing layers forever on a map
    the user never interacts with.
    """
    if viewport_available:
        return False
    return attempts < MAX_FALLBACK_POLLS


def on_viewport_change(
    widget: Any,
    input: Any,
    session: Any,
    *,
    debounce_ms: int = 300,
):
    """Decorator that calls a function when the map viewport changes.

    The decorated async function receives ``(bounds, zoom)`` and should
    return a list of layer dicts.  The decorator calls
    ``widget.update(session, layers)`` with the returned layers.

    Inside the decorated function, any Shiny reactive value that is read
    (e.g. ``tl.index()``) automatically becomes a dependency — the
    function re-fires when that value changes, not only on viewport moves.

    On first call (before any ``moveend`` event), the decorator fires
    once using ``widget.view_state`` to derive initial bounds.

    Parameters
    ----------
    widget
        A :class:`~shiny_deckgl.MapWidget` instance.
    input
        The Shiny ``input`` object from the server function.
    session
        The active Shiny ``Session``.
    debounce_ms
        Milliseconds to debounce viewport changes (default 300).

    Returns
    -------
    callable
        A decorator.  Use as ``@on_viewport_change(widget, input, session)``.
    """
    if debounce_ms < 0:
        raise ValueError(f"debounce_ms must be >= 0, got {debounce_ms}")

    from .map_widget import MapWidget

    if not isinstance(widget, MapWidget):
        raise TypeError(
            f"widget must be a MapWidget instance, got {type(widget).__name__}"
        )

    def decorator(fn):
        if input is None or session is None:
            # Allow construction without session for testing
            return fn

        from shiny import reactive

        _generation = [0]
        _fallback_attempts = [0]

        @reactive.Effect
        async def _viewport_watcher():
            # Read the view state input (creates reactive dependency).
            # On initial load, the input doesn't exist yet (no moveend
            # has fired), so Shiny raises SilentException.  We catch it
            # and fall back to the widget's configured view_state.
            try:
                vs = input[widget.view_state_input_id]()
            except Exception:
                vs = None

            if vs is not None and "bounds" in vs:
                bounds = vs["bounds"]
                zoom = vs.get("zoom", 0)
                _fallback_attempts[0] = 0
            else:
                # Initial load — use widget's configured view_state
                vs0 = widget.view_state
                lon = vs0.get("longitude", 0)
                lat = vs0.get("latitude", 0)
                z = vs0.get("zoom", 5)
                # Approximate bounds from center + zoom
                span = 180 / (2 ** z)
                bounds = {
                    "sw": [lon - span, lat - span / 2],
                    "ne": [lon + span, lat + span / 2],
                }
                zoom = z
                # Poll for the real view state, but only for a bounded number
                # of attempts. Re-arming unconditionally meant a map the user
                # never touched re-ran the loader and re-pushed every layer
                # once a second for the whole session.
                _fallback_attempts[0] += 1
                if _should_repoll(False, _fallback_attempts[0]):
                    reactive.invalidate_later(1.0)

            _generation[0] += 1
            my_gen = _generation[0]

            # Debounce: wait briefly, skip if superseded
            if debounce_ms > 0:
                import asyncio
                await asyncio.sleep(debounce_ms / 1000.0)

            # Last-write-wins: skip if a newer call started
            if my_gen != _generation[0]:
                return

            layers = await fn(bounds, zoom)

            # Check again after fn() in case a newer call arrived
            if my_gen != _generation[0]:
                return

            if layers is not None:
                await widget.update(session, layers)

        return fn

    return decorator
