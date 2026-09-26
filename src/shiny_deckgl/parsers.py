"""Finite-element mesh parsers for shiny_deckgl.

Currently supports SHYFEM ``.grd`` grid files.  This module provides
two public functions:

- :func:`parse_shyfem_grd` — parse a ``.grd`` file and return
  deck.gl ``PolygonLayer``-ready data (triangles with depth colours).
- :func:`parse_shyfem_mesh` — parse a ``.grd`` file and return
  ``SimpleMeshLayer``-compatible geometry arrays (positions, normals,
  colours, and triangle indices).

Coordinate system:
  Pass ``crs=`` (an EPSG code or any pyproj CRS string, e.g. ``3346`` for
  LKS94 or ``32634`` for UTM zone 34N) and the nodes are projected to WGS84
  with `pyproj`.  Without it, lon/lat grids are used directly and projected
  grids are assumed to be UTM zone 33N (EPSG:32633) -- with a warning,
  since a wrong guess silently puts the mesh in the wrong place.
"""

from __future__ import annotations

import functools
import math
import warnings
from pathlib import Path
from typing import Union

#: A CRS as an EPSG code or anything pyproj accepts ("EPSG:3346", ...).
CrsLike = Union[int, str]

#: What a projected grid given without ``crs=`` is assumed to be in.
DEFAULT_PROJECTED_CRS = "EPSG:32633"

__all__ = [
    "parse_shyfem_grd",
    "parse_shyfem_mesh",
]


# ---------------------------------------------------------------------------
# Internal: coordinate transformer (lazy-loaded, cached)
# ---------------------------------------------------------------------------


def _crs_key(crs: CrsLike) -> str:
    return f"EPSG:{crs}" if isinstance(crs, int) else str(crs)


@functools.lru_cache(maxsize=8)
def _get_transformer(crs: str = DEFAULT_PROJECTED_CRS):
    """Lazy-load a pyproj Transformer from *crs* to WGS84 lon/lat.

    Returns ``None`` if pyproj is not installed.
    """
    try:
        from pyproj import Transformer
        return Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    except ImportError:
        return None


def _utm_to_wgs84(
    x: float, y: float, crs: str = DEFAULT_PROJECTED_CRS,
) -> tuple[float, float]:
    """Convert a projected coordinate (UTM Zone 33N by default) to WGS84 lon/lat.

    Raises
    ------
    RuntimeError
        If pyproj is not installed.
    ValueError
        If coordinate transformation fails (e.g., invalid coordinates).
    """
    t = _get_transformer(crs)
    if t is None:
        raise RuntimeError("pyproj is required: micromamba install -n shiny pyproj")
    try:
        result = t.transform(x, y)
        return (float(result[0]), float(result[1]))
    except Exception as e:
        raise ValueError(f"Coordinate transformation failed for ({x}, {y}): {e}") from e


def _depth_to_rgb(t: float) -> tuple[int, int, int]:
    """Convert normalized depth (0=shallow, 1=deep) to RGB color.

    Returns a blue color ramp: shallow = light blue, deep = dark blue.

    Parameters
    ----------
    t
        Normalized depth value in [0, 1] range.

    Returns
    -------
    tuple[int, int, int]
        RGB color tuple (0-255 range).
    """
    r = int(30 + (1 - t) * 150)
    g = int(60 + (1 - t) * 160)
    b = int(180 + (1 - t) * 40)
    return r, g, b


# ---------------------------------------------------------------------------
# Internal: common .grd reader
# ---------------------------------------------------------------------------

def _read_grd(path: Path, crs: CrsLike | None = None) -> tuple[
    dict[int, tuple[float, float]],
    list[dict],
    dict[int, float],
]:
    """Read a SHYFEM ``.grd`` file and return (nodes, elements, node_depths).

    Nodes are projected from *crs* to WGS84.  Without *crs*, lon/lat
    grids are used as-is and projected ones (any coordinate outside the
    lon/lat range) are assumed UTM Zone 33N, with a warning.

    Parameters
    ----------
    path
        Path to the ``.grd`` file.
    crs
        CRS of the node coordinates (EPSG code or pyproj string).

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

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            rec_type = parts[0]

            if rec_type == "1":
                if len(parts) < 5:
                    continue
                nid = int(parts[1])
                x, y = float(parts[3]), float(parts[4])
                raw_nodes[nid] = (x, y)
                if len(parts) > 5:
                    node_depths[nid] = float(parts[5])

            elif rec_type == "2":
                if len(parts) < 5:
                    continue
                eid = int(parts[1])
                nvert = int(parts[3])
                if len(parts) < 4 + nvert:
                    continue
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

    if crs is None:
        projected = any(abs(x) > 180 or abs(y) > 90 for x, y in raw_nodes.values())
        if not projected:
            return raw_nodes, elements, node_depths  # already lon/lat
        warnings.warn(
            f"SHYFEM grid {path.name} has projected coordinates and no crs=; "
            f"assuming UTM zone 33N ({DEFAULT_PROJECTED_CRS}). Pass crs= to be "
            "explicit, e.g. crs=3346 for LKS94 or crs=32634 for UTM zone 34N.",
            UserWarning,
            stacklevel=3,
        )
        crs_key = DEFAULT_PROJECTED_CRS
    else:
        crs_key = _crs_key(crs)
        if crs_key.upper() in ("EPSG:4326", "OGC:CRS84"):
            return raw_nodes, elements, node_depths

    nodes: dict[int, tuple[float, float]] = {
        nid: _utm_to_wgs84(x, y, crs_key) for nid, (x, y) in raw_nodes.items()
    }

    return nodes, elements, node_depths


# ---------------------------------------------------------------------------
# Public: PolygonLayer-ready data
# ---------------------------------------------------------------------------

def parse_shyfem_grd(path: str | Path, *, crs: CrsLike | None = None) -> list[dict]:
    """Parse a SHYFEM ``.grd`` file and return PolygonLayer-ready data.

    Each element (triangle or quad) is converted to a closed polygon
    with a depth-mapped blue colour ramp.

    Parameters
    ----------
    path
        Path to the ``.grd`` file.
    crs
        CRS of the node coordinates, e.g. ``3346`` (LKS94) or ``32634``
        (UTM zone 34N).  See the module docstring for the default.

    Returns
    -------
    list[dict]
        Each dict has keys: ``polygon`` (list of ``[lon, lat]``),
        ``depth`` (float), ``element_id`` (int), ``color`` (``[r,g,b,a]``),
        ``layerType`` (str).
    """
    nodes, elements, _nd = _read_grd(Path(path), crs)

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
        r, g, b = _depth_to_rgb(t)

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

def parse_shyfem_mesh(
    path: str | Path, z_scale: float = 50.0, *, crs: CrsLike | None = None,
) -> dict:
    """Parse a SHYFEM ``.grd`` file into SimpleMeshLayer geometry.

    Vertex positions are in **metres** relative to the mesh centre,
    suitable for the deck.gl ``METER_OFFSETS`` coordinate system
    (``coordinateSystem="meter-offsets"``).

    Parameters
    ----------
    path
        Path to the ``.grd`` file.
    z_scale
        Vertical exaggeration factor for depth (default 50).
    crs
        CRS of the node coordinates; see :func:`parse_shyfem_grd`.

    Returns
    -------
    dict
        Keys: ``positions``, ``normals``, ``colors`` (flat float lists),
        ``indices`` (flat int list), ``center`` (``[lon, lat]``),
        ``n_vertices``, ``n_triangles``, ``depth_range``.
    """
    import numpy as np

    nodes, elements, node_depths = _read_grd(Path(path), crs)

    if not nodes or not elements:
        raise ValueError(f"No nodes or elements parsed from {path}")

    # Build node_id to index mapping
    node_ids = np.array(list(nodes.keys()))
    nid_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    n_vertices = len(node_ids)

    # Coordinates array
    node_coords = np.array(list(nodes.values())) # shape (N, 2)
    lons = node_coords[:, 0]
    lats = node_coords[:, 1]

    ctr_lon = float(lons.mean())
    ctr_lat = float(lats.mean())

    m_per_deg_lon = 111_320 * math.cos(math.radians(ctr_lat))
    m_per_deg_lat = 110_540

    # Initialize positions (X, Y, Z)
    positions = np.zeros((n_vertices, 3), dtype=np.float32)
    positions[:, 0] = (lons - ctr_lon) * m_per_deg_lon
    positions[:, 1] = (lats - ctr_lat) * m_per_deg_lat

    # Per-vertex depth
    if node_depths:
        # Vectorized lookup
        depths_arr = np.array([node_depths.get(nid, 0.0) for nid in node_ids], dtype=np.float32)
    else:
        # Fallback to averaging elements
        sum_depths = np.zeros(n_vertices, dtype=np.float32)
        cnt_depths = np.zeros(n_vertices, dtype=np.float32)
        for elem in elements:
            d = elem["depth"]
            for v in elem["verts"]:
                if v in nid_to_idx:
                    idx = nid_to_idx[v]
                    sum_depths[idx] += d
                    cnt_depths[idx] += 1
        
        valid = cnt_depths > 0
        depths_arr = np.zeros(n_vertices, dtype=np.float32)
        depths_arr[valid] = sum_depths[valid] / cnt_depths[valid]

    d_min = float(depths_arr.min())
    d_max = float(depths_arr.max())
    d_range = d_max - d_min if d_max > d_min else 1.0

    # Assign Z (remember to negate)
    positions[:, 2] = -depths_arr * z_scale

    # Per-vertex colours (vectorized version of _depth_to_rgb formula)
    t = (depths_arr - d_min) / d_range
    colors = np.zeros((n_vertices, 3), dtype=np.float32)
    colors[:, 0] = (30 + (1 - t) * 150) / 255.0  # R: shallow=light, deep=dark
    colors[:, 1] = (60 + (1 - t) * 160) / 255.0  # G
    colors[:, 2] = (180 + (1 - t) * 40) / 255.0  # B

    # Build triangle indices
    indices_list = []
    for elem in elements:
        vs = elem["verts"]
        if len(vs) >= 3:
            try:
                i0, i1, i2 = nid_to_idx[vs[0]], nid_to_idx[vs[1]], nid_to_idx[vs[2]]
            except KeyError:
                continue
            indices_list.extend([i0, i1, i2])
            if len(vs) == 4:
                try:
                    i3 = nid_to_idx[vs[3]]
                    indices_list.extend([i0, i2, i3])
                except KeyError:
                    pass
    
    indices = np.array(indices_list, dtype=np.int32)

    # Compute normals using advanced indexing
    normals = np.zeros_like(positions)
    p0 = positions[indices[0::3]]
    p1 = positions[indices[1::3]]
    p2 = positions[indices[2::3]]
    
    e1 = p1 - p0
    e2 = p2 - p0
    
    face_normals = np.cross(e1, e2)
    
    np.add.at(normals, indices[0::3], face_normals)
    np.add.at(normals, indices[1::3], face_normals)
    np.add.at(normals, indices[2::3], face_normals)
    
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths == 0] = 1.0
    normals /= lengths

    return {
        "positions": np.round(positions.flatten(), 2).tolist(),
        "normals": np.round(normals.flatten(), 4).tolist(),
        "colors": np.round(colors.flatten(), 3).tolist(),
        "indices": indices.tolist(),
        "center": [round(ctr_lon, 5), round(ctr_lat, 5)],
        "n_vertices": n_vertices,
        "n_triangles": len(indices) // 3,
        "depth_range": [round(d_min, 2), round(d_max, 2)],
    }
