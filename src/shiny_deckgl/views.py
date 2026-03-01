"""Deck.gl view helpers (MapView, OrthographicView, etc.)."""

from __future__ import annotations

__all__ = [
    "map_view",
    "orthographic_view",
    "first_person_view",
    "globe_view",
]


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
