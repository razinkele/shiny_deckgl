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

from typing import Union

#: Type returned by all extension helpers — either a bare class-name
#: string (no-arg extensions) or a ``[name, options]`` pair.
Extension = Union[str, list[Union[str, dict]]]

__all__ = [
    "Extension",
    "brushing_extension",
    "collision_filter_extension",
    "data_filter_extension",
    "mask_extension",
    "clip_extension",
    "terrain_extension",
    "fill_style_extension",
    "path_style_extension",
    "fp64_extension",
]


def brushing_extension() -> Extension:
    """``BrushingExtension`` — highlight features near the cursor.

    Layer props enabled:

    * ``brushingRadius`` — radius in metres
    * ``brushingEnabled`` — toggle on/off
    * ``brushingTarget`` — ``"source"`` | ``"target"`` | ``"source_target"``
    """
    return "BrushingExtension"


def collision_filter_extension() -> Extension:
    """``CollisionFilterExtension`` — hide overlapping labels/icons.

    Layer props enabled:

    * ``collisionEnabled`` — toggle on/off (default ``True``)
    * ``collisionGroup`` — group name string
    * ``collisionTestProps`` — dict of test properties
    * ``getCollisionPriority`` — accessor for collision priority
    """
    return "CollisionFilterExtension"


def data_filter_extension(filter_size: int = 1) -> Extension:
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


def mask_extension() -> Extension:
    """``MaskExtension`` — clip layer rendering to a GeoJSON mask.

    Layer props enabled:

    * ``maskId`` — id of a ``GeoJsonLayer`` whose features define the mask
    * ``maskByInstance`` — if True, mask by instance centroid
    * ``maskInverted`` — if True, show outside the mask area
    """
    return "MaskExtension"


def clip_extension() -> Extension:
    """``ClipExtension`` — clip layer rendering to the current view bounds.

    Useful for layers whose data extends far beyond the viewport
    (e.g. large GeoJSON polygons) to improve rendering performance.
    """
    return "ClipExtension"


def terrain_extension() -> Extension:
    """``TerrainExtension`` — drape layers onto a 3D terrain surface.

    Requires a terrain source to be active on the map.

    Layer props enabled:

    * ``terrainDrawMode`` — ``"offset"`` (default) or ``"drape"``
    """
    return "TerrainExtension"


def fill_style_extension(pattern: bool = True) -> Extension:
    """``FillStyleExtension`` — apply fill patterns to polygon layers.

    Parameters
    ----------
    pattern
        Whether to enable pattern fills (default ``True``).

    Layer props enabled:

    * ``fillPatternAtlas`` — URL/image of the pattern atlas
    * ``fillPatternMapping`` — dict mapping pattern names to atlas regions
    * ``fillPatternMask`` — whether pattern replaces fill color
    * ``getFillPattern`` — accessor returning pattern name per feature
    * ``getFillPatternScale`` — accessor for pattern scale
    * ``getFillPatternOffset`` — accessor for pattern offset
    """
    return ["FillStyleExtension", {"pattern": pattern}]


def path_style_extension(dash: bool = False, high_precision: bool = False) -> Extension:
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


def fp64_extension() -> Extension:
    """``Fp64Extension`` — 64-bit floating point rendering.

    Enables double-precision (fp64) calculations on the GPU for layers
    that need extremely precise positioning.  Useful when visualising
    data at very high zoom levels or with coordinates that span a wide
    range of values.

    This extension adds the ``fp64`` prop to the layer; set it to ``True``
    to activate.

    Layer props enabled:

    * ``fp64`` — enable 64-bit mode (``True``/``False``)
    """
    return "Fp64Extension"
