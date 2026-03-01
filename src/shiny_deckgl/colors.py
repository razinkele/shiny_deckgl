"""Basemap style constants and color-scale utilities."""

from __future__ import annotations

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


def color_range(
    n: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Generate *n* evenly-spaced RGBA colours by linearly interpolating a palette.

    Parameters
    ----------
    n
        Number of output colours (default 6).
    palette
        Source palette as a list of ``[R, G, B]`` or ``[R, G, B, A]`` stops.
        Defaults to ``PALETTE_VIRIDIS``.

    Returns
    -------
    list[list[int]]
        ``n`` colours, each ``[R, G, B, 255]``.
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
        a = palette[lo]
        b = palette[hi]
        r = int(a[0] + (b[0] - a[0]) * frac)
        g = int(a[1] + (b[1] - a[1]) * frac)
        bl = int(a[2] + (b[2] - a[2]) * frac)
        result.append([r, g, bl, 255])
    return result


def color_bins(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a colour using equal-width bins.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of colour bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` colour per input value.
    """
    if not values:
        return []
    colours = color_range(n_bins, palette)
    lo = min(values)
    hi = max(values)
    span = hi - lo if hi != lo else 1.0
    result: list[list[int]] = []
    for v in values:
        idx = int((v - lo) / span * (n_bins - 1))
        idx = max(0, min(idx, n_bins - 1))
        result.append(colours[idx])
    return result


def color_quantiles(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]:
    """Map each value to a colour using quantile-based bins.

    Each bin contains approximately the same number of values.

    Parameters
    ----------
    values
        Numeric values to classify.
    n_bins
        Number of colour bins.
    palette
        Source palette (defaults to ``PALETTE_VIRIDIS``).

    Returns
    -------
    list[list[int]]
        One ``[R, G, B, A]`` colour per input value.
    """
    if not values:
        return []
    colours = color_range(n_bins, palette)
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

    return [colours[_bin(v)] for v in values]
