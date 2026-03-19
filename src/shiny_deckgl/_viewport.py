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
    return sw[0] <= lon <= ne[0] and sw[1] <= lat <= ne[1]
