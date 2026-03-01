"""Deck.gl extension helpers for common layer extensions.

Extensions modify layer behaviour — collision detection, brushing,
data filtering, terrain snapping, clipping, fill patterns, and more.

Each helper returns a spec that the ``layer()`` function's ``extensions``
parameter understands.  The JS client resolves them into real deck.gl
``Extension`` instances via ``deck[className]``.

Usage
-----
::

    from shiny_deckgl import layer
    from shiny_deckgl.extensions import brushing_extension, data_filter_extension

    layer(
        "ScatterplotLayer", "pts", data=points,
        extensions=[brushing_extension(), data_filter_extension(filter_size=1)],
        brushingRadius=50000,
        brushingEnabled=True,
        getFilterValue="@@d.year",
        filterRange=[2010, 2020],
    )

All helpers return either a **string** (no-arg extension) or a
``[name, options]`` pair, compatible with :func:`shiny_deckgl.layers.layer`.
"""

from __future__ import annotations


def brushing_extension() -> str:
    """``BrushingExtension`` — highlight features near the cursor.

    Layer props enabled:

    * ``brushingRadius`` — radius in metres
    * ``brushingEnabled`` — toggle on/off
    * ``brushingTarget`` — ``"source"`` | ``"target"`` | ``"source_target"``
    """
    return "BrushingExtension"


def collision_filter_extension() -> str:
    """``CollisionFilterExtension`` — hide overlapping labels/icons.

    Layer props enabled:

    * ``collisionEnabled`` — toggle on/off (default ``True``)
    * ``collisionGroup`` — group name string
    * ``collisionTestProps`` — dict of test properties
    * ``getCollisionPriority`` — accessor for collision priority
    """
    return "CollisionFilterExtension"


def data_filter_extension(filter_size: int = 1) -> list:
    """``DataFilterExtension`` — GPU-accelerated data filtering.

    Parameters
    ----------
    filter_size
        Number of filter dimensions (1–4).

    Layer props enabled:

    * ``getFilterValue`` — accessor returning numeric value(s)
    * ``filterRange`` — ``[min, max]`` or nested for multi-dim
    * ``filterSoftRange`` — soft fade range
    * ``filterEnabled`` — toggle on/off
    * ``filterTransformSize`` — scale filtered-out features to 0
    * ``filterTransformColor`` — fade filtered-out features
    """
    return ["DataFilterExtension", {"filterSize": filter_size}]


def mask_extension() -> str:
    """``MaskExtension`` — clip layer rendering to a GeoJSON mask.

    Layer props enabled:

    * ``maskId`` — id of a ``GeoJsonLayer`` whose features define the mask
    * ``maskByInstance`` — if True, mask by instance centroid
    * ``maskInverted`` — if True, show outside the mask area
    """
    return "MaskExtension"


def clip_extension() -> str:
    """``ClipExtension`` — clip layer rendering to the current view bounds.

    Useful for layers whose data extends far beyond the viewport
    (e.g. large GeoJSON polygons) to improve rendering performance.
    """
    return "ClipExtension"


def terrain_extension() -> str:
    """``TerrainExtension`` — drape layers onto a 3D terrain surface.

    Requires a terrain source to be active on the map.

    Layer props enabled:

    * ``terrainDrawMode`` — ``"offset"`` (default) or ``"drape"``
    """
    return "TerrainExtension"


def fill_style_extension(pattern: bool = True) -> list:
    """``FillStyleExtension`` — apply fill patterns to polygon layers.

    Parameters
    ----------
    pattern
        Whether to enable pattern fills (default ``True``).

    Layer props enabled:

    * ``fillPatternAtlas`` — URL/image of the pattern atlas
    * ``fillPatternMapping`` — dict mapping pattern names to atlas regions
    * ``fillPatternMask`` — whether pattern replaces fill colour
    * ``getFillPattern`` — accessor returning pattern name per feature
    * ``getFillPatternScale`` — accessor for pattern scale
    * ``getFillPatternOffset`` — accessor for pattern offset
    """
    return ["FillStyleExtension", {"pattern": pattern}]


def path_style_extension(dash: bool = False, high_precision: bool = False) -> list:
    """``PathStyleExtension`` — dashed/offset path rendering.

    Parameters
    ----------
    dash
        Enable dash patterns.
    high_precision
        Use high-precision dash rendering (slower but pixel-perfect).

    Layer props enabled:

    * ``getDashArray`` — ``[dashLength, gapLength]`` accessor
    * ``dashJustified`` — align dashes to path start/end
    * ``getOffset`` — lateral offset accessor
    """
    return ["PathStyleExtension", {"dash": dash, "highPrecisionDash": high_precision}]
