"""Client-side property animation helpers."""

from __future__ import annotations

__all__ = ["animate_prop"]


def animate_prop(
    prop: str,
    speed: float = 1.0,
    loop: bool = True,
    range_min: float = 0,
    range_max: float = 360,
) -> dict:
    """Create a client-side animation marker for a layer property.

    When passed as a layer prop value (e.g.
    ``getAngle=animate_prop(...)``), the JavaScript widget starts a
    ``requestAnimationFrame`` loop that increments the property each
    frame --- no server round-trips needed.

    .. note::
       Named ``animate_prop`` (not ``animate``) to avoid collision with
       the ``animate`` parameter on :meth:`MapWidget.update`.

    Parameters
    ----------
    prop
        Name for the animated value (used as a key in the JS animation
        registry and in ``window._deckgl_anim_{widgetId}_{prop}``).
    speed
        Units per second (default 1.0).
    loop
        Whether to wrap the value when it reaches *range_max*
        (default ``True``).  For angles this gives continuous rotation.
    range_min
        Minimum value (default 0).
    range_max
        Maximum / wrap value (default 360).

    Returns
    -------
    dict
        A marker dict recognised by the JS layer builder.  Do not
        modify the returned dict --- pass it directly as a layer property.

    Example
    -------
    >>> from shiny_deckgl import icon_layer, animate_prop
    >>> icon_layer("turbines", data,
    ...     getAngle=animate_prop(prop="rotation", speed=40, loop=True),
    ... )
    """
    return {
        "@@animate": True,
        "prop": prop,
        "speed": speed,
        "loop": loop,
        "range_min": range_min,
        "range_max": range_max,
    }
