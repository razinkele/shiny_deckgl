"""Transition helper for deck.gl layer property animations."""

from __future__ import annotations


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
