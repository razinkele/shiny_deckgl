"""Finite-element mesh parsers for shiny_deckgl.

Currently supports SHYFEM ``.grd`` grid files.  This module provides
two public functions:

- :func:`parse_shyfem_grd` — parse a ``.grd`` file and return
  deck.gl ``PolygonLayer``-ready data (triangles with depth colours).
- :func:`parse_shyfem_mesh` — parse a ``.grd`` file and return
  ``SimpleMeshLayer``-compatible geometry arrays (positions, normals,
  colours, and triangle indices).

Coordinate system auto-detection:
  If node X values exceed 100 000, the file is assumed to be in
  UTM Zone 33N (EPSG:32633) and `pyproj` is used for conversion.
  Otherwise coordinates are treated as WGS84 (lon/lat) directly.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

__all__ = [
    "parse_shyfem_grd",
    "parse_shyfem_mesh",
]


# ---------------------------------------------------------------------------
# Internal: coordinate transformer (lazy-loaded)
# ---------------------------------------------------------------------------

_TRANSFORMER: Any = None
_TRANSFORMER_LOADED = False


def _get_transformer():
    """Lazy-load pyproj Transformer (UTM Zone 33N → WGS84)."""
    global _TRANSFORMER, _TRANSFORMER_LOADED
    if not _TRANSFORMER_LOADED:
        try:
            from pyproj import Transformer
            _TRANSFORMER = Transformer.from_crs(
                "EPSG:32633", "EPSG:4326", always_xy=True,
            )
        except ImportError:
            _TRANSFORMER = None
        _TRANSFORMER_LOADED = True
    return _TRANSFORMER


def _utm_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert UTM Zone 33N to WGS84 lon/lat."""
    t = _get_transformer()
    if t is not None:
        return t.transform(x, y)
    raise RuntimeError("pyproj is required: micromamba install -n shiny pyproj")


# ---------------------------------------------------------------------------
# Internal: common .grd reader
# ---------------------------------------------------------------------------

def _read_grd(path: Path) -> tuple[
    dict[int, tuple[float, float]],
    list[dict],
    dict[int, float],
]:
    """Read a SHYFEM ``.grd`` file and return (nodes, elements, node_depths).

    Coordinate system is auto-detected: if node X values exceed
    100 000, coordinates are assumed UTM Zone 33N and projected to
    WGS84 via pyproj.  Otherwise they are taken as lon/lat directly.

    Parameters
    ----------
    path
        Path to the ``.grd`` file.

    Returns
    -------
    nodes
        ``{node_id: (lon, lat)}`` in WGS84.
    elements
        List of ``{"id", "verts", "depth"}`` dicts.
    node_depths
        ``{node_id: depth}`` from the 6th column of type-1 lines.
    """
    # First pass: collect raw node coordinates and elements
    raw_nodes: dict[int, tuple[float, float]] = {}
    node_depths: dict[int, float] = {}
    elements: list[dict] = []

    with open(path) as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            rec_type = parts[0]

            if rec_type == "1":
                nid = int(parts[1])
                x, y = float(parts[3]), float(parts[4])
                raw_nodes[nid] = (x, y)
                if len(parts) > 5:
                    node_depths[nid] = float(parts[5])

            elif rec_type == "2":
                eid = int(parts[1])
                nvert = int(parts[3])
                verts = [int(parts[4 + i]) for i in range(nvert)]
                # Depth field is optional (present in some .grd flavours)
                depth_idx = 4 + nvert
                if depth_idx < len(parts):
                    depth = float(parts[depth_idx])
                elif node_depths:
                    # Average depth from vertex nodes
                    d_vals = [node_depths.get(v, 0.0) for v in verts]
                    depth = sum(d_vals) / len(d_vals) if d_vals else 0.0
                else:
                    depth = 0.0
                elements.append({"id": eid, "verts": verts, "depth": depth})

    if not raw_nodes:
        return {}, elements, node_depths

    # Auto-detect CRS: UTM values have X > 100 000
    sample_x = next(iter(raw_nodes.values()))[0]
    is_utm = abs(sample_x) > 100_000

    nodes: dict[int, tuple[float, float]] = {}
    if is_utm:
        for nid, (x, y) in raw_nodes.items():
            lon, lat = _utm_to_wgs84(x, y)
            nodes[nid] = (lon, lat)
    else:
        # Already WGS84 (lon, lat)
        nodes = raw_nodes

    return nodes, elements, node_depths


# ---------------------------------------------------------------------------
# Public: PolygonLayer-ready data
# ---------------------------------------------------------------------------

def parse_shyfem_grd(path: str | Path) -> list[dict]:
    """Parse a SHYFEM ``.grd`` file and return PolygonLayer-ready data.

    Each element (triangle or quad) is converted to a closed polygon
    with a depth-mapped blue colour ramp.

    Parameters
    ----------
    path
        Path to the ``.grd`` file.

    Returns
    -------
    list[dict]
        Each dict has keys: ``polygon`` (list of ``[lon, lat]``),
        ``depth`` (float), ``element_id`` (int), ``color`` (``[r,g,b,a]``),
        ``layerType`` (str).
    """
    nodes, elements, _nd = _read_grd(Path(path))

    if not elements:
        return []

    depths = [e["depth"] for e in elements]
    d_min, d_max = min(depths), max(depths)
    d_range = d_max - d_min if d_max > d_min else 1.0

    result: list[dict] = []
    for elem in elements:
        try:
            coords = [list(nodes[v]) for v in elem["verts"]]
        except KeyError:
            continue
        coords.append(coords[0])  # close the polygon
        depth = elem["depth"]

        # Colour: shallow = light blue → deep = dark blue
        t = (depth - d_min) / d_range
        r = int(30 + (1 - t) * 150)
        g = int(60 + (1 - t) * 160)
        b = int(180 + (1 - t) * 40)

        result.append({
            "polygon": coords,
            "depth": round(depth, 2),
            "element_id": elem["id"],
            "color": [r, g, b, 180],
            "layerType": "SHYFEM Mesh",
        })

    return result


# ---------------------------------------------------------------------------
# Public: SimpleMeshLayer geometry arrays
# ---------------------------------------------------------------------------

def parse_shyfem_mesh(path: str | Path, z_scale: float = 50.0) -> dict:
    """Parse a SHYFEM ``.grd`` file into SimpleMeshLayer geometry.

    Vertex positions are in **metres** relative to the mesh centre,
    suitable for the deck.gl ``METER_OFFSETS`` coordinate system
    (``coordinateSystem=2``).

    Parameters
    ----------
    path
        Path to the ``.grd`` file.
    z_scale
        Vertical exaggeration factor for depth (default 50).

    Returns
    -------
    dict
        Keys: ``positions``, ``normals``, ``colors`` (flat float lists),
        ``indices`` (flat int list), ``center`` (``[lon, lat]``),
        ``n_vertices``, ``n_triangles``, ``depth_range``.
    """
    nodes, elements, node_depths = _read_grd(Path(path))

    if not nodes or not elements:
        raise ValueError(f"No nodes or elements parsed from {path}")

    # Centre in lon/lat
    all_lons = [v[0] for v in nodes.values()]
    all_lats = [v[1] for v in nodes.values()]
    ctr_lon = (min(all_lons) + max(all_lons)) / 2
    ctr_lat = (min(all_lats) + max(all_lats)) / 2

    # Metres-per-degree at centre latitude
    m_per_deg_lon = 111_320 * math.cos(math.radians(ctr_lat))
    m_per_deg_lat = 110_540

    # Build vertex list (node id → index)
    nid_to_idx: dict[int, int] = {}
    positions: list[float] = []
    idx = 0
    for nid, (lon, lat) in nodes.items():
        nid_to_idx[nid] = idx
        dx = (lon - ctr_lon) * m_per_deg_lon
        dy = (lat - ctr_lat) * m_per_deg_lat
        positions.extend([dx, dy, 0.0])
        idx += 1

    # Per-vertex depth: prefer per-node depths when available,
    # otherwise average from adjacent elements.
    vertex_depth: dict[int, float] = {}
    if node_depths:
        vertex_depth = dict(node_depths)
    else:
        _vd_sum: dict[int, float] = {nid: 0.0 for nid in nodes}
        _vd_cnt: dict[int, int] = {nid: 0 for nid in nodes}
        for elem in elements:
            for v in elem["verts"]:
                _vd_sum[v] += elem["depth"]
                _vd_cnt[v] += 1
        for nid in nodes:
            cnt = _vd_cnt[nid]
            vertex_depth[nid] = _vd_sum[nid] / cnt if cnt else 0.0

    # Depth range across vertices
    all_depths = list(vertex_depth.values())
    d_min, d_max = min(all_depths), max(all_depths)
    d_range = d_max - d_min if d_max > d_min else 1.0

    # Assign vertex Z from depth
    for nid in nodes:
        vi = nid_to_idx[nid]
        positions[vi * 3 + 2] = -vertex_depth.get(nid, 0.0) * z_scale

    # Per-vertex colours (depth-mapped blue ramp, values 0..1)
    colors: list[float] = []
    for nid in nodes:
        d = vertex_depth.get(nid, 0.0)
        t = (d - d_min) / d_range
        r = (30 + (1 - t) * 150) / 255
        g = (60 + (1 - t) * 160) / 255
        b = (180 + (1 - t) * 40) / 255
        colors.extend([round(r, 3), round(g, 3), round(b, 3)])

    # Build triangle indices
    indices: list[int] = []
    for elem in elements:
        vs = elem["verts"]
        if len(vs) >= 3:
            try:
                i0, i1, i2 = nid_to_idx[vs[0]], nid_to_idx[vs[1]], nid_to_idx[vs[2]]
            except KeyError:
                continue
            indices.extend([i0, i1, i2])
            if len(vs) == 4:
                try:
                    i3 = nid_to_idx[vs[3]]
                except KeyError:
                    continue
                indices.extend([i0, i2, i3])

    # Compute per-vertex normals (average of face normals)
    normals = [0.0] * len(positions)
    for fi in range(0, len(indices), 3):
        i0, i1, i2 = indices[fi], indices[fi + 1], indices[fi + 2]
        p0 = positions[i0 * 3: i0 * 3 + 3]
        p1 = positions[i1 * 3: i1 * 3 + 3]
        p2 = positions[i2 * 3: i2 * 3 + 3]
        e1 = [p1[j] - p0[j] for j in range(3)]
        e2 = [p2[j] - p0[j] for j in range(3)]
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        for vi in (i0, i1, i2):
            normals[vi * 3] += nx
            normals[vi * 3 + 1] += ny
            normals[vi * 3 + 2] += nz
    for vi in range(len(positions) // 3):
        nx, ny, nz = normals[vi * 3], normals[vi * 3 + 1], normals[vi * 3 + 2]
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        normals[vi * 3] = round(nx / length, 4)
        normals[vi * 3 + 1] = round(ny / length, 4)
        normals[vi * 3 + 2] = round(nz / length, 4)

    positions = [round(v, 2) for v in positions]

    return {
        "positions": positions,
        "normals": normals,
        "colors": colors,
        "indices": indices,
        "center": [round(ctr_lon, 5), round(ctr_lat, 5)],
        "n_vertices": len(positions) // 3,
        "n_triangles": len(indices) // 3,
        "depth_range": [round(d_min, 2), round(d_max, 2)],
    }
