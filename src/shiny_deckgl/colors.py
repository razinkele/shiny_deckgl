"""Basemap style constants and color-scale utilities."""

from __future__ import annotations

__all__ = [
    "CARTO_POSITRON",
    "CARTO_DARK",
    "CARTO_VOYAGER",
    "OSM_LIBERTY",
    "PALETTE_VIRIDIS",
    "PALETTE_PLASMA",
    "PALETTE_OCEAN",
    "PALETTE_THERMAL",
    "PALETTE_CHLOROPHYLL",
    "PALETTE_BLUES",
    "PALETTE_GREENS",
    "PALETTE_REDS",
    "PALETTE_YELLOW_RED",
    "PALETTE_BLUE_WHITE",
    "VIRIDIS",
    "OCEAN_DEPTH",
    "BLUES",
    "GREENS",
    "REDS",
    "YELLOW_RED",
    "BLUE_WHITE",
    "color_range",
    "color_bins",
    "color_quantiles",
    "depth_color",
]

# ---------------------------------------------------------------------------
# Basemap style constants
# ---------------------------------------------------------------------------

CARTO_POSITRON = "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json"
CARTO_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json"
CARTO_VOYAGER = "https://basemaps.cartocdn.com/gl/voyager-nolabels-gl-style/style.json"
OSM_LIBERTY = "https://tiles.openfreemap.org/styles/liberty"


# ---------------------------------------------------------------------------
# Color scale utilities
# ---------------------------------------------------------------------------

# --- Built-in palettes (6 stops each) ---
PALETTE_VIRIDIS: list[list[int]] = [
    [68, 1, 84], [59, 82, 139], [33, 145, 140],
    [94, 201, 98], [253, 231, 37], [240, 249, 33],
]
PALETTE_PLASMA: list[list[int]] = [
    [13, 8, 135], [126, 3, 168], [204, 71, 120],
    [248, 149, 64], [252, 225, 56], [240, 249, 33],
]
PALETTE_OCEAN: list[list[int]] = [
    [0, 0, 40], [0, 30, 80], [0, 80, 120],
    [0, 140, 160], [60, 200, 180], [180, 240, 220],
]
PALETTE_THERMAL: list[list[int]] = [
    [4, 35, 51], [23, 82, 118], [81, 139, 116],
    [186, 177, 82], [227, 103, 55], [192, 39, 41],
]
PALETTE_CHLOROPHYLL: list[list[int]] = [
    [255, 255, 229], [194, 230, 153], [120, 198, 121],
    [49, 163, 84], [0, 104, 55], [0, 69, 41],
]
PALETTE_BLUES: list[list[int]] = [
    [198, 219, 239], [158, 202, 225], [107, 174, 214],
    [66, 146, 198], [33, 113, 181], [8, 69, 148],
]
PALETTE_GREENS: list[list[int]] = [
    [199, 233, 192], [161, 217, 155], [116, 196, 118],
    [65, 171, 93], [35, 139, 69], [0, 90, 50],
]
PALETTE_REDS: list[list[int]] = [
    [254, 229, 217], [252, 174, 145], [251, 106, 74],
    [239, 59, 44], [203, 24, 29], [153, 0, 13],
]
PALETTE_YELLOW_RED: list[list[int]] = [
    [255, 255, 178], [254, 204, 92], [253, 141, 60],
    [240, 59, 32], [189, 0, 38], [128, 0, 38],
]
PALETTE_BLUE_WHITE: list[list[int]] = [
    [8, 48, 107], [33, 113, 181], [66, 146, 198],
    [146, 197, 222], [209, 229, 240], [247, 251, 255],
]

# --- Short-name aliases ---
VIRIDIS = PALETTE_VIRIDIS
OCEAN_DEPTH = PALETTE_OCEAN
BLUES = PALETTE_BLUES
GREENS = PALETTE_GREENS
REDS = PALETTE_REDS
YELLOW_RED = PALETTE_YELLOW_RED
BLUE_WHITE = PALETTE_BLUE_WHITE


def color_range(
    n: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Generate *n* evenly-spaced RGBA colors by linearly interpolating a palette.

    Parameters
    ----------
    n
        Number of output colors (default 6).
    palette
        Source palette as a list of ``[R, G, B]`` or ``[R, G, B, A]`` stops.
        Defaults to ``PALETTE_VIRIDIS``.

    Returns
    -------
    list[list[int]]
        ``n`` colors, each ``[R, G, B, 255]``.
    """
    palette = palette or PALETTE_VIRIDIS
    if n <= 0:
        return []
    if n == 1:
        c = palette[0]
        return [[c[0], c[1], c[2], c[3] if len(c) > 3 else 255]]
    stops = len(palette)
    result: list[list[int]] = []
    for i in range(n):
        t = i / (n - 1) * (stops - 1)
        lo = int(t)
        hi = min(lo + 1, stops - 1)
        frac = t - lo
        c0 = palette[lo]
        c1 = palette[hi]
        r = int(c0[0] + (c1[0] - c0[0]) * frac)
        g = int(c0[1] + (c1[1] - c0[1]) * frac)
        b = int(c0[2] + (c1[2] - c0[2]) * frac)
        result.append([r, g, b, 255])
    return result


def color_bins(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a color using equal-width bins.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of color bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` color per input value.
    """
    if not values:
        return []
    colors = color_range(n_bins, palette)
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1.0
    result: list[list[int]] = []
    for v in values:
        idx = int((v - lo) / span * (n_bins - 1))
        idx = max(0, min(idx, n_bins - 1))
        result.append(colors[idx])
    return result


def color_quantiles(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a color using quantile-based bins.

    Each bin contains approximately the same number of values.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of color bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` color per input value.
    """
    if not values:
        return []
    colors = color_range(n_bins, palette)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # Compute quantile breakpoints
    breaks = [
        sorted_vals[min(int(i / n_bins * n), n - 1)]
        for i in range(1, n_bins)
    ]

    def _bin(v: float) -> int:
        for i, br in enumerate(breaks):
            if v <= br:
                return i
        return n_bins - 1

    return [colors[_bin(v)] for v in values]


def depth_color(
    elevation: float,
    max_depth: float = 459.0,
    alpha: int = 210,
) -> list[int]:
    """Map an elevation / depth value to a blue-gradient RGBA color.

    Produces a smooth dark-blue-to-teal ramp suitable for bathymetric
    visualisations.  At ``elevation=0`` the color is a pale teal
    ``[50, 180, 120, α]``; at ``max_depth`` it is a deep navy
    ``[10, 60, 255, α]``.

    Parameters
    ----------
    elevation
        The depth or elevation value (0 = shallowest).
    max_depth
        The reference maximum depth for normalisation (default 459 m,
        roughly the Baltic Sea's Landsort Deep).
    alpha
        Alpha channel value (0–255, default 210).

    Returns
    -------
    list[int]
        ``[R, G, B, A]`` color.
    """
    t = max(0.0, min(elevation / max_depth, 1.0)) if max_depth else 0.0
    r = int(10 + 40 * (1 - t))
    g = int(60 + 120 * (1 - t))
    b = int(120 + 135 * t)
    return [r, g, b, alpha]
