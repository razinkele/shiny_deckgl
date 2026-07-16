"""Test: render HexSim hex mesh via SimpleMeshLayer.

Loads the Columbia [small] workspace (16M hexagons), extracts water-only
cells, builds a triangle mesh (6 triangles per hex), and renders via
simple_mesh_layer + custom_geometry with METER_OFFSETS coordinate system.

Exports a standalone HTML file for visual inspection.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
import pytest

# ── Paths ───────────────────────────────────────────────────────────────────

_hexsim_root = os.environ.get("SHINY_DECKGL_HEXSIM_ROOT")
_hexsim_workspace = os.environ.get("SHINY_DECKGL_HEXSIM_WORKSPACE")

HEXSIM_ROOT = Path(_hexsim_root).expanduser() if _hexsim_root else None
COLUMBIA_WS = (
    Path(_hexsim_workspace).expanduser()
    if _hexsim_workspace
    else HEXSIM_ROOT / "Columbia [small]" if HEXSIM_ROOT else None
)

if HEXSIM_ROOT is not None:
    sys.path.insert(0, str(HEXSIM_ROOT))

Workspace = pytest.importorskip("heximpy.hxnparser", reason="heximpy not available").Workspace
if COLUMBIA_WS is None or not COLUMBIA_WS.exists():
    pytest.skip(
        "HexSim Columbia workspace not configured; set SHINY_DECKGL_HEXSIM_WORKSPACE",
        allow_module_level=True,
    )


# ── Hex mesh builder ────────────────────────────────────────────────────────


def _compute_centroids(hm, cell_indices, edge):
    """Compute pointy-top hex centroids for selected cells (vectorized)."""
    h, w, flag = hm.height, hm.width, hm.flag
    if flag == 0:
        all_rows = np.repeat(np.arange(h), w)
        all_cols = np.tile(np.arange(w), h)
    else:
        row_list, col_list = [], []
        for r in range(h):
            rw = w if r % 2 == 0 else w - 1
            row_list.append(np.full(rw, r, dtype=np.int32))
            col_list.append(np.arange(rw, dtype=np.int32))
        all_rows = np.concatenate(row_list)
        all_cols = np.concatenate(col_list)

    rows = all_rows[cell_indices].astype(np.float64)
    cols = all_cols[cell_indices].astype(np.float64)
    cx = np.sqrt(3.0) * edge * (cols + 0.5 * (all_rows[cell_indices] % 2))
    cy = 1.5 * edge * rows
    return cx, cy


def _build_hex_mesh(cx, cy, edge, cell_colors):
    """Build a tightly-packed triangle mesh from hex centroids + colors.

    Matches the HexSim viewer PolyCollection style: full-size hexagons,
    solid fill, face-matching edges (no visible gaps).

    Each hex = 1 center + 6 perimeter vertices = 7 verts, 6 triangles.
    """
    n = len(cx)

    # Pointy-top vertex offsets at full edge length
    angles = np.linspace(0, 2 * np.pi, 7)[:-1]
    dx = (edge * np.sin(angles)).astype(np.float32)
    dy = (edge * np.cos(angles)).astype(np.float32)

    # Allocate arrays
    positions = np.empty((n * 7, 3), dtype=np.float32)
    colors = np.empty((n * 7, 4), dtype=np.float32)
    indices = np.empty(n * 18, dtype=np.uint32)

    # Vectorized construction — center vertices
    centers_x = cx.astype(np.float32)
    centers_y = cy.astype(np.float32)
    base_idx = np.arange(n, dtype=np.uint32) * 7

    # Center vertex positions (every 7th slot)
    positions[base_idx, 0] = centers_x
    positions[base_idx, 1] = centers_y
    positions[base_idx, 2] = 0.0

    # Perimeter vertices (6 per hex)
    for v in range(6):
        positions[base_idx + 1 + v, 0] = centers_x + dx[v]
        positions[base_idx + 1 + v, 1] = centers_y + dy[v]
        positions[base_idx + 1 + v, 2] = 0.0

    # All 7 vertices of each hex get the same color
    for v in range(7):
        colors[base_idx + v] = cell_colors

    # Triangle indices: 6 triangles per hex (center, v_i, v_{i+1 mod 6})
    tri_base = np.arange(n, dtype=np.uint32) * 18
    for t in range(6):
        indices[tri_base + t * 3 + 0] = base_idx
        indices[tri_base + t * 3 + 1] = base_idx + 1 + t
        indices[tri_base + t * 3 + 2] = base_idx + 1 + (t + 1) % 6

    return positions, colors, indices


def _depth_colormap(values, vmin=None, vmax=None):
    """Map depth values to RGBA: light blue (shallow) → dark blue (deep)."""
    mask = values != 0.0
    lo = vmin if vmin is not None else float(np.nanmin(values[mask])) if np.any(mask) else 0.0
    hi = vmax if vmax is not None else float(np.nanmax(values))
    rng = hi - lo if hi > lo else 1.0

    t = np.clip((values - lo) / rng, 0.0, 1.0)  # 0=shallow, 1=deep

    colors = np.empty((len(values), 4), dtype=np.float32)
    # Shallow (t=0): [0.68, 0.85, 1.0]  — light sky blue
    # Deep    (t=1): [0.03, 0.19, 0.42] — dark navy blue
    colors[:, 0] = np.float32(0.68 - 0.65 * t)
    colors[:, 1] = np.float32(0.85 - 0.66 * t)
    colors[:, 2] = np.float32(1.00 - 0.58 * t)
    colors[:, 3] = np.float32(0.95)
    colors[~mask] = [0.0, 0.0, 0.0, 0.0]
    return colors


def hexsim_to_mesh(
    workspace_dir: Path,
    extent_layer: str = "River [ extent ]",
    color_layer: str = "River [ depth ]",
    row_range: tuple[int, int] | None = None,
    col_range: tuple[int, int] | None = None,
) -> dict:
    """Load HexSim workspace and build a triangle mesh for SimpleMeshLayer.

    Matches the HexSim viewer style: tightly packed filled hexagons
    colored by value.  Renders ALL water cells (no sampling) for a
    contiguous, solid grid.

    Parameters
    ----------
    row_range : optional (row_start, row_end) to crop rows.
    col_range : optional (col_start, col_end) to crop columns.
        Use both for a square spatial crop.

    Returns a dict compatible with ``custom_geometry()``.
    """
    t0 = time.perf_counter()

    # 1. Load workspace
    ws = Workspace.from_dir(workspace_dir)
    edge = ws.grid.edge
    print(f"[hexsim_to_mesh] Workspace loaded: {ws.grid.n_hexes:,} hexagons, "
          f"edge={edge:.2f}m  ({time.perf_counter() - t0:.1f}s)")

    # 2. Get layers
    extent_hm = ws.hexmaps[extent_layer]
    color_hm = ws.hexmaps.get(color_layer) or extent_hm
    extent = extent_hm.values
    color_vals = color_hm.values

    # 3. Build row/col mapping for the full grid
    h, w, flag = extent_hm.height, extent_hm.width, extent_hm.flag
    if flag == 0:
        all_rows = np.repeat(np.arange(h), w)
        all_cols = np.tile(np.arange(w), h)
    else:
        row_list, col_list = [], []
        for r in range(h):
            rw = w if r % 2 == 0 else w - 1
            row_list.append(np.full(rw, r, dtype=np.int32))
            col_list.append(np.arange(rw, dtype=np.int32))
        all_rows = np.concatenate(row_list)
        all_cols = np.concatenate(col_list)

    # 4. Select water cells, optionally cropped to a spatial box
    water_mask = extent != 0.0
    spatial_mask = water_mask.copy()
    if row_range is not None:
        r0, r1 = row_range
        spatial_mask &= (all_rows >= r0) & (all_rows < r1)
    if col_range is not None:
        c0, c1 = col_range
        spatial_mask &= (all_cols >= c0) & (all_cols < c1)
    cell_indices = np.where(spatial_mask)[0]

    crop_info = ""
    if row_range:
        crop_info += f" rows={row_range}"
    if col_range:
        crop_info += f" cols={col_range}"
    n_cells = len(cell_indices)
    print(f"[hexsim_to_mesh] Water cells to render: {n_cells:,}"
          f"{'  (crop:' + crop_info + ')' if crop_info else ''}"
          f"  ({time.perf_counter() - t0:.1f}s)")

    # 4. Compute centroids
    cx, cy = _compute_centroids(extent_hm, cell_indices, edge)

    # Shift to local origin for float32 precision
    # Negate Y to flip along horizontal axis (HexSim row 0 = top,
    # but map north = up, so invert to match geography).
    origin_x = float(np.mean(cx))
    origin_y = float(np.mean(cy))
    cx_local = cx - origin_x
    cy_local = -(cy - origin_y)

    # 5. Compute colors
    cell_colors = _depth_colormap(color_vals[cell_indices])

    # 6. Build mesh
    print(f"[hexsim_to_mesh] Building mesh: {n_cells * 7:,} vertices, "
          f"{n_cells * 6:,} triangles  ({time.perf_counter() - t0:.1f}s)")

    positions, colors, indices = _build_hex_mesh(
        cx_local, cy_local, edge, cell_colors
    )

    print(f"[hexsim_to_mesh] Mesh built in {time.perf_counter() - t0:.1f}s")

    return {
        "positions": positions,
        "colors": colors,
        "indices": indices,
        "center": [origin_x, origin_y],
        "_n_cells": n_cells,
        "_edge": edge,
    }


# ── Test: build mesh and export HTML ────────────────────────────────────────


def test_hexsim_columbia_mesh():
    """Load Columbia workspace, build hex mesh for a river section, export HTML."""
    from shiny_deckgl import MapWidget, simple_mesh_layer, custom_geometry

    # Build mesh — ALL water cells (no crop)
    mesh_data = hexsim_to_mesh(
        COLUMBIA_WS,
        extent_layer="River [ extent ]",
        color_layer="River [ depth ]",
    )

    n = mesh_data["_n_cells"]
    assert mesh_data["positions"].shape[0] == n * 7
    assert mesh_data["indices"].shape[0] == n * 6 * 3

    # HexSim grid has no real-world CRS. Use METER_OFFSETS from an
    # arbitrary WGS84 point. Positions are zero-centered around mesh mean.
    lyr = simple_mesh_layer(
        "hexsim-mesh",
        **custom_geometry(mesh_data, position=[-121.0, 46.3]),
        opacity=0.95,
        pickable=False,
    )

    widget = MapWidget(
        "hexsim-test",
        view_state={
            "longitude": -121.0,
            "latitude": 46.3,
            "zoom": 7,
            "pitch": 0,
        },
        style="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
    )

    html = widget.to_html(
        [lyr],
        title="HexSim Columbia — Hex Mesh (SimpleMeshLayer)",
    )

    out = Path(__file__).parent.parent / "dist" / "hexsim_columbia_mesh.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"\n[test] Exported: {out}")
    print(f"[test] Mesh: {n:,} cells, {mesh_data['positions'].shape[0]:,} vertices")

    assert out.exists()
    assert len(html) > 1000


def test_hexsim_columbia_all_water():
    """Load ALL water cells (879K) — full river mesh."""
    mesh_data = hexsim_to_mesh(
        COLUMBIA_WS,
        extent_layer="River [ extent ]",
        color_layer="River [ depth ]",
    )

    n = mesh_data["_n_cells"]
    assert n > 800_000  # expect ~880K water cells
    assert mesh_data["positions"].dtype == np.float32
    assert mesh_data["indices"].dtype == np.uint32
    print(f"[test] Full water mesh: {n:,} cells, "
          f"positions: {mesh_data['positions'].nbytes / 1024 / 1024:.1f} MB, "
          f"indices: {mesh_data['indices'].nbytes / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    test_hexsim_columbia_mesh()
