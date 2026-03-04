"""Sample data and helper functions for the shiny_deckgl demo app.

Baltic Sea ports, shipping routes, MPA GeoJSON, and WMS layer definitions.
"""

from __future__ import annotations

import base64 as _b64
import functools
import json
import random
import zlib as _zlib
from pathlib import Path
from typing import Any, cast

from .colors import (
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    PALETTE_OCEAN,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
)

# ---------------------------------------------------------------------------
# Baltic Sea ports
# ---------------------------------------------------------------------------

PORTS = [
    {"name": "Klaipėda",    "country": "LT", "lon": 21.13, "lat": 55.71, "cargo_mt": 42.5},
    {"name": "Gdańsk",      "country": "PL", "lon": 18.65, "lat": 54.35, "cargo_mt": 53.2},
    {"name": "Stockholm",   "country": "SE", "lon": 18.07, "lat": 59.33, "cargo_mt": 8.1},
    {"name": "Helsinki",    "country": "FI", "lon": 24.94, "lat": 60.17, "cargo_mt": 14.3},
    {"name": "Riga",        "country": "LV", "lon": 24.11, "lat": 56.95, "cargo_mt": 28.7},
    {"name": "Tallinn",     "country": "EE", "lon": 24.75, "lat": 59.44, "cargo_mt": 22.1},
    {"name": "Copenhagen",  "country": "DK", "lon": 12.57, "lat": 55.68, "cargo_mt": 6.4},
    {"name": "Rostock",     "country": "DE", "lon": 12.10, "lat": 54.09, "cargo_mt": 26.8},
    {"name": "Kaliningrad", "country": "RU", "lon": 20.45, "lat": 54.71, "cargo_mt": 12.3},
    {"name": "Ventspils",   "country": "LV", "lon": 21.56, "lat": 57.39, "cargo_mt": 18.5},
]

# ---------------------------------------------------------------------------
# Real Baltic Sea ferry / shipping routes with charted waypoints
# ---------------------------------------------------------------------------

ROUTES = [
    {   # Klaipėda–Kiel (DFDS Seaways freight+passenger via Langeland Belt)
        "from": "Klaipėda", "to": "Kiel",
        "operator": "DFDS Seaways", "type": "freight",
        "color": [0, 180, 230, 180],
        "waypoints": [
            [21.13, 55.71], [20.40, 55.40], [19.80, 55.10],
            [18.50, 54.90], [16.50, 55.00], [14.50, 54.80],
            [12.30, 54.60], [11.00, 54.50], [10.15, 54.33],
        ],
    },
    {   # Klaipėda–Karlshamn (DFDS Seaways freight)
        "from": "Klaipėda", "to": "Karlshamn",
        "operator": "DFDS Seaways", "type": "freight",
        "color": [0, 200, 120, 180],
        "waypoints": [
            [21.13, 55.71], [20.40, 55.50], [19.50, 55.50],
            [18.20, 55.60], [16.50, 55.80], [14.86, 56.17],
        ],
    },
    {   # Helsinki–Tallinn (Tallink / Viking Line, ~80 km)
        "from": "Helsinki", "to": "Tallinn",
        "operator": "Tallink / Viking Line", "type": "passenger",
        "color": [255, 140, 0, 180],
        "waypoints": [
            [24.94, 60.17], [24.90, 60.05], [24.85, 59.85],
            [24.80, 59.65], [24.75, 59.44],
        ],
    },
    {   # Riga–Stockholm (Tallink, via Irbe Strait & Gotland)
        "from": "Riga", "to": "Stockholm",
        "operator": "Tallink", "type": "passenger",
        "color": [180, 0, 200, 180],
        "waypoints": [
            [24.11, 56.95], [23.00, 57.20], [21.80, 57.50],
            [20.50, 57.80], [19.50, 58.30], [18.60, 58.90],
            [18.07, 59.33],
        ],
    },
    {   # Copenhagen–Rostock (Scandlines, Gedser–Rostock crossing)
        "from": "Copenhagen", "to": "Rostock",
        "operator": "Scandlines", "type": "passenger",
        "color": [255, 80, 80, 180],
        "waypoints": [
            [12.57, 55.68], [12.30, 55.40], [12.10, 55.00],
            [12.00, 54.60], [12.10, 54.30], [12.10, 54.09],
        ],
    },
    {   # Gdańsk–Nynäshamn (Polferries)
        "from": "Gdańsk", "to": "Stockholm",
        "operator": "Polferries", "type": "passenger",
        "color": [100, 200, 100, 180],
        "waypoints": [
            [18.65, 54.35], [18.80, 54.80], [19.00, 55.50],
            [18.80, 56.50], [18.50, 57.50], [18.20, 58.40],
            [17.95, 58.75], [18.07, 59.33],
        ],
    },
    {   # Ventspils–Nynäshamn (Stena Line)
        "from": "Ventspils", "to": "Stockholm",
        "operator": "Stena Line", "type": "passenger",
        "color": [200, 200, 0, 180],
        "waypoints": [
            [21.56, 57.39], [20.50, 57.60], [19.50, 57.90],
            [18.80, 58.30], [18.30, 58.80], [18.07, 59.33],
        ],
    },
    {   # Klaipėda–Travemünde (DFDS Seaways freight+passenger)
        "from": "Klaipėda", "to": "Travemünde",
        "operator": "DFDS Seaways", "type": "freight",
        "color": [60, 180, 200, 180],
        "waypoints": [
            [21.13, 55.71], [20.40, 55.40], [19.80, 55.10],
            [18.40, 54.90], [16.50, 55.00], [14.50, 54.70],
            [12.80, 54.40], [11.80, 54.10], [10.87, 53.96],
        ],
    },
]

# ---------------------------------------------------------------------------
# Marine Protected Areas — real HELCOM data (188 polygons, simplified)
# ---------------------------------------------------------------------------

_MPA_PATH = Path(__file__).parent / "data" / "helcom_mpa.geojson"


@functools.lru_cache(maxsize=1)
def _load_mpa_geojson() -> dict:
    """Lazy-load and cache the HELCOM MPA GeoJSON (avoids import-time I/O).

    Uses ``lru_cache`` for thread-safe, one-shot caching.
    """
    with open(_MPA_PATH) as f:
        data = json.load(f)
    # Normalise property keys to lower-case for tooltip consistency
    for feat in data["features"]:
        feat["properties"] = {k.lower(): v for k, v in feat["properties"].items()}
    return data


def __getattr__(name: str):
    """Module-level lazy accessor for ``MPA_GEOJSON``."""
    if name == "MPA_GEOJSON":
        return _load_mpa_geojson()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# ---------------------------------------------------------------------------
# EMODnet WMS layers (discovered via OWSLib GetCapabilities)
# ---------------------------------------------------------------------------

EMODNET_WMS_URL = "https://ows.emodnet-bathymetry.eu/wms"

# Fallback choices if OWSLib query fails (network unavailable, timeout, etc.)
_WMS_LAYER_FALLBACK: dict[str, str] = {
    "": "(none)",
    "emodnet:mean": "Mean depth  [emodnet:mean]",
    "emodnet:mean_atlas_land": "Mean depth + land  [emodnet:mean_atlas_land]",
    "emodnet:mean_multicolour": "Mean depth multi-colour  [emodnet:mean_multicolour]",
    "emodnet:mean_rainbowcolour": "Mean depth rainbow  [emodnet:mean_rainbowcolour]",
    "coastlines": "Coastlines  [coastlines]",
    "emodnet:contours": "Depth contours  [emodnet:contours]",
}


def _fetch_wms_layer_choices() -> dict[str, str]:
    """Query EMODnet WMS GetCapabilities via OWSLib and build a choices dict.

    Returns the fallback static list if the request fails.
    """
    try:
        from owslib.wms import WebMapService

        wms = WebMapService(EMODNET_WMS_URL, version="1.3.0", timeout=10)
        choices: dict[str, str] = {"": "(none)"}
        for name, layer in wms.contents.items():
            title = layer.title or name
            choices[name] = f"{title}  [{name}]"
        return choices
    except ImportError:
        # owslib not installed -> fallback list (no warning needed)
        return _WMS_LAYER_FALLBACK
    except (TimeoutError, ConnectionError, OSError) as e:
        # Network failure -> fallback list with warning
        import logging
        logging.getLogger(__name__).debug("WMS network error: %s", e)
        return _WMS_LAYER_FALLBACK
    except Exception as e:
        # XML parse errors, unexpected owslib errors, etc.
        import logging
        logging.getLogger(__name__).warning("Failed to fetch WMS: %s", e)
        return _WMS_LAYER_FALLBACK


_WMS_LAYER_CHOICES_CACHE: dict[str, str] | None = None


def get_wms_layer_choices() -> dict[str, str]:
    """Return WMS layer choices, fetching from EMODnet on first call.

    The network request is deferred from import time to the first
    invocation, avoiding a 10-second timeout when the module is
    imported without network access.
    """
    global _WMS_LAYER_CHOICES_CACHE
    if _WMS_LAYER_CHOICES_CACHE is None:
        _WMS_LAYER_CHOICES_CACHE = _fetch_wms_layer_choices()
    return _WMS_LAYER_CHOICES_CACHE


# Backward-compatible alias — existing code referencing the module-level
# constant ``WMS_LAYER_CHOICES`` will now get a lazy wrapper.  Direct
# dict usage (iteration, .get, .items, etc.) still works because the
# underlying object is a real dict once resolved.
WMS_LAYER_CHOICES = _WMS_LAYER_FALLBACK  # fast static default; call get_wms_layer_choices() for live data

# ---------------------------------------------------------------------------
# Lookup dicts for basemaps and palettes
# ---------------------------------------------------------------------------

BASEMAP_CHOICES = {
    "Positron (light)": CARTO_POSITRON,
    "Dark Matter": CARTO_DARK,
    "Voyager": CARTO_VOYAGER,
    "OSM Liberty": OSM_LIBERTY,
}

PALETTE_CHOICES = {
    "Viridis": PALETTE_VIRIDIS,
    "Plasma": PALETTE_PLASMA,
    "Ocean": PALETTE_OCEAN,
    "Thermal": PALETTE_THERMAL,
    "Chlorophyll": PALETTE_CHLOROPHYLL,
}

# ---------------------------------------------------------------------------
# Shared view state
# ---------------------------------------------------------------------------

BALTIC_VIEW = {
    "longitude": 19.5,
    "latitude": 57.0,
    "zoom": 5,
    "pitch": 0,
    "bearing": 0,
    "minZoom": 3,
    "maxZoom": 16,
}

# Default tooltip style used by most map widgets
TOOLTIP_STYLE = {
    "backgroundColor": "#0b2140",
    "color": "#d0f0fa",
    "fontSize": "13px",
    "borderLeft": "3px solid #1db9c3",
    "borderRadius": "6px",
    "padding": "8px 12px",
}

DEFAULT_TOOLTIP_HTML = "<b>{name}</b>"


# ---------------------------------------------------------------------------
# Data builder helpers
# ---------------------------------------------------------------------------

def port_by_name(name: str) -> dict:
    return next(p for p in PORTS if p["name"] == name)


@functools.lru_cache(maxsize=32)
def make_arc_data() -> list[dict]:
    """Build arc data from routes (using first/last waypoints)."""
    arcs = []
    for r in ROUTES:
        wp = r["waypoints"]
        arcs.append({
            "sourcePosition": wp[0],
            "targetPosition": wp[-1],
            "sourceColor": r["color"],
            "targetColor": r["color"],
            "name": f"{r['from']} \u2192 {r['to']}",
            "operator": r["operator"],
            "type": r["type"],
        })
    return arcs


@functools.lru_cache(maxsize=32)
def make_heatmap_points(n: int = 300) -> list[list[float]]:
    """Generate random observation points clustered around Baltic ports."""
    random.seed(42)
    pts: list[list[float]] = []
    for _ in range(n):
        port = random.choice(PORTS)
        lon = float(port["lon"]) + random.gauss(0, 1.5)
        lat = float(port["lat"]) + random.gauss(0, 0.8)
        weight = random.uniform(1, 10)
        pts.append([lon, lat, weight])
    return pts


@functools.lru_cache(maxsize=32)
def make_path_data() -> list[dict]:
    """Build path data — polylines using actual route waypoints."""
    paths = []
    for r in ROUTES:
        paths.append({
            "path": r["waypoints"],
            "name": f"{r['from']} \u2192 {r['to']}",
            "operator": r["operator"],
            "type": r["type"],
            "color": r["color"],
        })
    return paths


@functools.lru_cache(maxsize=32)
def make_port_data_simple() -> list[dict]:
    """Port data for events / advanced maps (no dynamic colours)."""
    return [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "country": p["country"],
            "cargo_mt": p["cargo_mt"],
        }
        for p in PORTS
    ]


@functools.lru_cache(maxsize=32)
def make_port_geojson() -> dict:
    """Convert port data to a GeoJSON FeatureCollection (for native layers)."""
    features = []
    for p in PORTS:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
            "properties": {
                "name": p["name"],
                "country": p["country"],
                "cargo_mt": p["cargo_mt"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


@functools.lru_cache(maxsize=32)
def make_trips_data(loop_length: int = 1800) -> list[dict]:
    """Build TripsLayer data from Baltic shipping routes.

    Each route generates a "trip" with a ``path`` array of
    ``[lon, lat, timestamp]`` triplets and a ``timestamps`` array.
    Timestamps are evenly spaced over the segment from ``0`` to
    ``loop_length``.
    """
    trips: list[dict] = []
    for r in ROUTES:
        wps = cast(list[list[float]], r["waypoints"])
        n = len(wps)
        if n < 2:
            continue
        timestamps = [int(i * loop_length / (n - 1)) for i in range(n)]
        path = [[float(wp[0]), float(wp[1]), ts] for wp, ts in zip(wps, timestamps)]
        trips.append({
            "path": path,
            "timestamps": timestamps,
            "name": f"{r['from']} → {r['to']}",
            "operator": r.get("operator", ""),
            "type": r.get("type", ""),
            "color": r.get("color", [253, 128, 93]),
        })
    return trips


# ---------------------------------------------------------------------------
# Drawing tools sample data — polygon for area of interest demo
# ---------------------------------------------------------------------------

SAMPLE_STUDY_AREA = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Sample Study Area"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [20.0, 55.0], [22.0, 55.0], [22.0, 56.5],
                    [20.0, 56.5], [20.0, 55.0],
                ]],
            },
        }
    ],
}


# ---------------------------------------------------------------------------
# 3-D visualisation data — Baltic Sea bathymetry & marine observations
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=32)
def make_bathymetry_grid(
    cols: int = 30,
    rows: int = 20,
    *,
    lon_min: float = 12.0,
    lon_max: float = 30.0,
    lat_min: float = 54.0,
    lat_max: float = 66.0,
) -> list[dict]:
    """Generate a synthetic Baltic Sea bathymetry grid.

    Returns a list of dicts, each with ``position`` ([lon, lat]),
    ``depth_m`` (negative = below sea level, 0–459 m range reflecting
    real Baltic bathymetry; deepest at the Landsort Deep ~459 m),
    and ``elevation`` (positive value = column height for deck.gl).

    The depth model is a deterministic combination of distance from the
    basin centre (≈ 18.2°E, 58.6°N — near _Landsort Deep_) plus a
    gentle sinusoidal ripple that mimics sub-basins.

    Parameters
    ----------
    cols, rows
        Grid dimensions (default 30 × 20 = 600 cells).
    lon_min, lon_max, lat_min, lat_max
        Geographic extent (default: full Baltic Sea).
    """
    import math

    # Landsort Deep approximate location
    centre_lon, centre_lat = 18.2, 58.6
    max_depth = 459.0  # metres — deepest point in the Baltic

    lon_step = (lon_max - lon_min) / (cols - 1)
    lat_step = (lat_max - lat_min) / (rows - 1)

    points: list[dict] = []
    for r in range(rows):
        lat = lat_min + r * lat_step
        for c in range(cols):
            lon = lon_min + c * lon_step

            # Distance fraction from the basin centre (0 = centre, 1 = edge)
            d_lon = (lon - centre_lon) / ((lon_max - lon_min) / 2)
            d_lat = (lat - centre_lat) / ((lat_max - lat_min) / 2)
            dist = math.sqrt(d_lon ** 2 + d_lat ** 2)
            dist = min(dist, 1.0)

            # Depth envelope: deepest at centre, tapering to 5 m at edges
            base = max_depth * (1.0 - dist ** 1.4)

            # Sub-basin ripple (deterministic)
            ripple = 30 * math.sin(lon * 1.7) * math.cos(lat * 2.3)

            depth = max(5.0, base + ripple)
            depth = round(depth, 1)

            points.append({
                "position": [round(lon, 4), round(lat, 4)],
                "depth_m": -depth,
                "elevation": depth,
                "lon": round(lon, 4),
                "lat": round(lat, 4),
            })
    return points


@functools.lru_cache(maxsize=32)
def make_fish_observations(n: int = 80) -> list[dict]:
    """Generate synthetic fish / marine species depth observations.

    Each record contains a Baltic Sea location, a species name, the
    observation depth (metres below surface), and a ``position`` in
    ``[lon, lat, -depth]`` triplet format suitable for deck.gl 3-D layers.

    Parameters
    ----------
    n
        Number of observations to generate (default 80).
    """
    species = [
        ("Atlantic cod",       20, 120),
        ("Baltic herring",      5,  80),
        ("European sprat",     10,  90),
        ("Atlantic salmon",     2,  60),
        ("European flounder",  15, 100),
        ("Pike-perch",          3,  40),
        ("Three-spined stickleback", 1, 25),
        ("Ringed seal",         0,  50),
    ]

    random.seed(99)
    obs: list[dict] = []
    for i in range(n):
        sp_name, d_min, d_max = species[i % len(species)]
        # Pick a random port as anchor for geographic clustering
        port = random.choice(PORTS)
        lon = round(port["lon"] + random.gauss(0, 1.2), 4)
        lat = round(port["lat"] + random.gauss(0, 0.6), 4)
        depth = round(random.uniform(d_min, d_max), 1)

        obs.append({
            "position": [lon, lat],
            "position_3d": [lon, lat, -depth],
            "species": sp_name,
            "depth_m": depth,
            "elevation": depth,          # positive for column_layer height
            "lon": lon,
            "lat": lat,
        })
    return obs


@functools.lru_cache(maxsize=32)
def make_bathymetry_geojson(cols: int = 15, rows: int = 10) -> dict:
    """Generate a GeoJSON FeatureCollection of bathymetry point features.

    Each feature is a ``Point`` with ``depth_m`` and ``elevation``
    properties — suitable for ``geojson_layer(extruded=True)``.

    Parameters
    ----------
    cols, rows
        Grid dimensions (smaller default than ``make_bathymetry_grid``
        because GeoJSON has more overhead per feature).
    """
    grid = make_bathymetry_grid(cols, rows)
    features = []
    for pt in grid:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": pt["position"],
            },
            "properties": {
                "depth_m": pt["depth_m"],
                "elevation": pt["elevation"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


@functools.lru_cache(maxsize=32)
def make_3d_arc_data() -> list[dict]:
    """Build 3-D arc data where source/target have altitude (z) components.

    Uses real Baltic port-to-port shipping routes with synthetic
    altitude values representing flight / drone corridors — handy for
    demonstrating ``arc_layer`` in a pitched 3-D view.
    """
    arcs = []
    for r in ROUTES:
        wp = cast(list[list[float]], r["waypoints"])
        # Height proportional to route length (longer = higher arc)
        alt = len(wp) * 500.0
        arcs.append({
            "sourcePosition": [float(wp[0][0]), float(wp[0][1]), 0],
            "targetPosition": [float(wp[-1][0]), float(wp[-1][1]), 0],
            "sourceColor": r["color"],
            "targetColor": r["color"],
            "name": f"{r['from']} → {r['to']}",
            "height": alt,
        })
    return arcs


# Pre-canned 3-D view state (pitched camera over central Baltic)
BALTIC_VIEW_3D = {
    "longitude": 19.5,
    "latitude": 57.0,
    "zoom": 5,
    "pitch": 45,
    "bearing": -15,
    "minZoom": 3,
    "maxZoom": 16,
}

# Standard lighting effect for 3-D scenes
LIGHTING_EFFECT_3D = {
    "type": "LightingEffect",
    "ambientLight": {"color": [255, 255, 255], "intensity": 1.0},
    "pointLights": [
        {
            "color": [255, 255, 255],
            "intensity": 2.0,
            "position": [19.5, 57.0, 80000],
        }
    ],
}


# ---------------------------------------------------------------------------
# Mesh view state (Curonian Lagoon, Lithuania)
# ---------------------------------------------------------------------------

SHYFEM_VIEW = {
    "longitude": 21.07,
    "latitude": 55.31,
    "zoom": 9,
    "pitch": 0,
    "bearing": 0,
}


# ---------------------------------------------------------------------------
# Layer gallery data factory helpers
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=32)
def make_h3_data() -> list[dict]:
    """Generate H3 hexagon demo data (7 resolution-3 cells in central Baltic)."""
    _h3_palette = [
        [255, 140, 0], [0, 200, 120], [200, 0, 100],
        [60, 180, 220], [160, 80, 200], [80, 200, 160],
    ]
    _h3_hexes = [
        "830892fffffffff", "831f74fffffffff", "831f75fffffffff",
        "831f66fffffffff", "830893fffffffff", "830890fffffffff",
        "830896fffffffff",
    ]
    random.seed(42)
    return [
        {
            "hex": h,
            "count": random.randint(3, 20),
            "color": [*_h3_palette[i % len(_h3_palette)], 180],
            "name": f"H3 cell {i + 1}",
            "layerType": "H3HexagonLayer",
        }
        for i, h in enumerate(_h3_hexes)
    ]


@functools.lru_cache(maxsize=32)
def make_point_cloud_data() -> list[dict]:
    """Generate synthetic 3-D point cloud around Baltic ports."""
    import math as _math
    pts: list[dict] = []
    for _i, _p in enumerate(PORTS):
        for _j in range(20):
            _angle = _j * _math.pi * 2 / 20
            pts.append({
                "position": [
                    float(_p["lon"]) + 0.05 * _math.cos(_angle),
                    float(_p["lat"]) + 0.03 * _math.sin(_angle),
                    float(_p["cargo_mt"]) * 50 + _j * 100,
                ],
                "color": [200, 100 + _j * 5, 50],
                "name": _p["name"],
                "layerType": "PointCloudLayer",
            })
    return pts


@functools.lru_cache(maxsize=32)
def make_shyfem_polygon_data(grd_path: str | None = None) -> list[dict]:
    """Load SHYFEM .grd as PolygonLayer data (with fallback to port boxes).

    Parameters
    ----------
    grd_path
        Path to the ``.grd`` file.  When ``None`` or the file doesn't
        exist, returns simple bounding-box polygons around Baltic ports.
    """
    from pathlib import Path
    if grd_path is not None and Path(grd_path).exists():
        from .parsers import parse_shyfem_grd
        return parse_shyfem_grd(grd_path)
    # Fallback
    return [
        {
            "polygon": [
                [float(p["lon"]) - 0.3, float(p["lat"]) - 0.15],
                [float(p["lon"]) + 0.3, float(p["lat"]) - 0.15],
                [float(p["lon"]) + 0.3, float(p["lat"]) + 0.15],
                [float(p["lon"]) - 0.3, float(p["lat"]) + 0.15],
            ],
            "name": p["name"],
            "depth": 0,
            "layerType": "PolygonLayer",
        }
        for p in PORTS
    ]


@functools.lru_cache(maxsize=32)
def make_shyfem_mesh_data(
    grd_path: str | None = None,
    z_scale: float = 50.0,
) -> dict | None:
    """Load SHYFEM .grd as SimpleMeshLayer geometry arrays.

    Parameters
    ----------
    grd_path
        Path to the ``.grd`` file.  Returns ``None`` when the file
        doesn't exist or ``grd_path`` is ``None``.
    z_scale
        Vertical exaggeration for depth visualisation.
    """
    from pathlib import Path
    if grd_path is not None and Path(grd_path).exists():
        from .parsers import parse_shyfem_mesh
        return parse_shyfem_mesh(grd_path, z_scale=z_scale)
    return None


# ---------------------------------------------------------------------------
# Seal IBM (Individual-Based Model) — movement simulation
# ---------------------------------------------------------------------------
# The visual assets (SVG sprites, icon mapping, colours) live in ibm.py
# under generic names.  This module contains the SIMULATION / coordinate
# generation algorithms and seal-specific reference data that produce
# data the demo feeds into deck.gl.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Land/sea mask — embedded 0.5° grid derived from EMODnet Bathymetry
# (emodnet:mean layer, GetFeatureInfo on a 43×27 grid).  1 = sea, 0 = land.
# See https://ows.emodnet-bathymetry.eu/wms for the source WMS.
# ---------------------------------------------------------------------------

_SEA_MASK_B64 = (
    "eJwdjSESQjEMRF+JKO5b/gxDr4DE/Rv88zCY9mCIOBxnqEOCrGB+SIjYye5mN+CzD9jN"
    "4wyrvXyf6hfmxSD12uEqzp+8HxQ9WZeP2J0jxSJoGgnbQA65k7YQa4h5/P2AKTg3aF7J"
    "BUrLShrhLlr8h8pocfMDPY8m5Q=="
)
_SEA_GRID_SHAPE = (27, 43)  # (lat_rows, lon_cols)
_SEA_LON_MIN, _SEA_LON_MAX = 9.0, 30.0
_SEA_LAT_MIN, _SEA_LAT_MAX = 53.0, 66.0
_SEA_RES = 0.5  # degrees


@functools.lru_cache(maxsize=1)
def _load_sea_mask():
    """Decode the embedded sea mask into a 2-D list of lists.

    This may be moderately expensive due to base64/zlib decoding, so it
    is cached.  The public accessor :func:`_get_sea_mask` allows the
    mask to be loaded lazily on first use instead of at import time.
    """
    raw = _zlib.decompress(_b64.b64decode(_SEA_MASK_B64))
    bits: list[int] = []
    for byte in raw:
        for bit in range(7, -1, -1):
            bits.append((byte >> bit) & 1)
    total = _SEA_GRID_SHAPE[0] * _SEA_GRID_SHAPE[1]
    flat = bits[:total]
    grid: list[list[int]] = []
    cols = _SEA_GRID_SHAPE[1]
    for r in range(_SEA_GRID_SHAPE[0]):
        grid.append(flat[r * cols : (r + 1) * cols])
    return grid


# Internal cache placeholder; use :func:`_get_sea_mask` for access.
_SEA_MASK: list[list[int]] | None = None


def _get_sea_mask() -> list[list[int]]:
    """Return the decoded sea mask, loading it lazily on demand."""
    global _SEA_MASK
    if _SEA_MASK is None:
        _SEA_MASK = _load_sea_mask()
    return _SEA_MASK


def is_sea(lon: float, lat: float) -> bool:
    """Return True if *(lon, lat)* is over sea according to the embedded mask.

    Uses the 0.5° EMODnet bathymetry grid.  Points outside the grid
    (beyond Baltic bounds) are treated as land.
    """
    if lon < _SEA_LON_MIN or lon > _SEA_LON_MAX:
        return False
    if lat < _SEA_LAT_MIN or lat > _SEA_LAT_MAX:
        return False
    col = int(round((lon - _SEA_LON_MIN) / _SEA_RES))
    row = int(round((lat - _SEA_LAT_MIN) / _SEA_RES))
    col = max(0, min(col, _SEA_GRID_SHAPE[1] - 1))
    row = max(0, min(row, _SEA_GRID_SHAPE[0] - 1))
    mask = _get_sea_mask()
    return mask[row][col] == 1

from .ibm import SPECIES_COLORS  # noqa: E402

# ---------------------------------------------------------------------------
# Colony / haul-out reference data (demo-only, not part of the library)
# ---------------------------------------------------------------------------

#: Real Baltic Sea haul-out / breeding sites for three seal species.
_SEAL_HAULOUT_SITES: list[dict] = [
    # Grey seal (Halichoerus grypus) — large offshore sandbanks & skerries
    {"name": "Gotland NW skerries",   "species": "Grey seal",    "lon": 18.15, "lat": 57.95, "population": 120},
    {"name": "Åland archipelago",      "species": "Grey seal",    "lon": 20.00, "lat": 60.50, "population": 200},
    {"name": "Klaipėda offshore bank", "species": "Grey seal",    "lon": 20.85, "lat": 55.85, "population":  80},
    {"name": "Hiiumaa west",           "species": "Grey seal",    "lon": 22.00, "lat": 58.95, "population": 150},
    {"name": "Stockholm outer arch.",  "species": "Grey seal",    "lon": 18.80, "lat": 59.20, "population":  90},
    # Ringed seal (Pusa hispida botnica) — ice-breeding, northern Baltic
    {"name": "Bothnian Bay south",     "species": "Ringed seal",  "lon": 22.50, "lat": 64.00, "population": 250},
    {"name": "Gulf of Finland east",   "species": "Ringed seal",  "lon": 27.50, "lat": 60.10, "population":  60},
    {"name": "Kvarken archipelago",    "species": "Ringed seal",  "lon": 21.20, "lat": 63.20, "population": 180},
    {"name": "Gulf of Riga",           "species": "Ringed seal",  "lon": 23.80, "lat": 57.60, "population":  40},
    # Harbour seal (Phoca vitulina) — southern/western Baltic
    {"name": "Kattegat coast",         "species": "Harbour seal", "lon": 11.80, "lat": 56.80, "population": 300},
    {"name": "Storebælt",              "species": "Harbour seal", "lon": 11.00, "lat": 55.50, "population": 110},
    {"name": "Kalmar Strait",          "species": "Harbour seal", "lon": 16.50, "lat": 56.00, "population":  85},
    {"name": "Wismar Bay",             "species": "Harbour seal", "lon": 11.50, "lat": 54.10, "population":  70},
]

# Typical foraging trip parameters by species (from telemetry literature)
_SEAL_TRIP_PARAMS: dict[str, dict] = {
    "Grey seal":    {"range_deg": 1.8, "step": 0.06, "legs": 30, "turn": 0.6},
    "Ringed seal":  {"range_deg": 0.8, "step": 0.03, "legs": 20, "turn": 0.9},
    "Harbour seal": {"range_deg": 1.2, "step": 0.04, "legs": 25, "turn": 0.7},
}


@functools.lru_cache(maxsize=32)
def make_seal_trips(
    n_seals: int = 25,
    loop_length: int = 600,
    *,
    seed: int = 77,
) -> list[dict]:
    """Generate mock seal movement tracks using a correlated random walk.

    Each seal starts at a haul-out site, performs a foraging trip
    (outbound leg), then returns to the haul-out (inbound leg).
    The path is a correlated random walk where turn angles are drawn
    from a wrapped Cauchy distribution (parameterised per species)
    producing realistic-looking looping foraging trips.

    Parameters
    ----------
    n_seals
        Number of individual seal tracks to generate.
    loop_length
        Total animation loop length in time units.
    seed
        Random seed for reproducibility.

    Returns
    -------
    list[dict]
        Each dict has ``path`` (list of [lon, lat, timestamp]),
        ``timestamps``, ``name``, ``species``, ``haulout``,
        ``color``, and ``seal_id``.
    """
    import math
    from .ibm import format_trips

    rng = random.Random(seed)
    trips: list[dict] = []

    for seal_idx in range(n_seals):
        # Pick a haul-out site (weighted by population)
        site = rng.choices(
            _SEAL_HAULOUT_SITES,
            weights=[s["population"] for s in _SEAL_HAULOUT_SITES],
            k=1,
        )[0]
        species = site["species"]
        params = _SEAL_TRIP_PARAMS[species]

        # Starting position (jittered around haul-out)
        start_lon = site["lon"] + rng.gauss(0, 0.05)
        start_lat = site["lat"] + rng.gauss(0, 0.03)
        # Safeguard: if jitter pushed start onto a land cell, snap back
        if not is_sea(start_lon, start_lat):
            start_lon, start_lat = site["lon"], site["lat"]

        # Correlated random walk — outbound foraging leg
        n_legs = params["legs"] + rng.randint(-5, 5)
        n_legs = max(10, n_legs)
        step_size = params["step"] * rng.uniform(0.6, 1.4)
        heading = rng.uniform(0, 2 * math.pi)

        outbound: list[list[float]] = [[start_lon, start_lat]]
        lon, lat = start_lon, start_lat

        for _ in range(n_legs):
            # Wrapped Cauchy turn (concentration = params["turn"])
            u = rng.random()
            rho = params["turn"]
            turn = math.atan2(
                (1 - rho**2) * math.sin(2 * math.pi * u),
                (1 + rho**2) * math.cos(2 * math.pi * u) - 2 * rho,
            )
            heading += turn
            new_lon = lon + step_size * math.cos(heading) * rng.uniform(0.7, 1.3)
            new_lat = lat + step_size * math.sin(heading) * 0.6 * rng.uniform(0.7, 1.3)
            # Clamp to Baltic bounds
            new_lon = max(9.0, min(30.0, new_lon))
            new_lat = max(53.0, min(66.0, new_lat))
            # Land avoidance — reject step if it lands on terrestrial ground
            if not is_sea(new_lon, new_lat):
                # Try up to 5 alternative headings before giving up
                for _retry in range(5):
                    heading += math.pi / 3  # rotate 60° and try again
                    new_lon = lon + step_size * math.cos(heading) * rng.uniform(0.7, 1.3)
                    new_lat = lat + step_size * math.sin(heading) * 0.6 * rng.uniform(0.7, 1.3)
                    new_lon = max(9.0, min(30.0, new_lon))
                    new_lat = max(53.0, min(66.0, new_lat))
                    if is_sea(new_lon, new_lat):
                        break
                else:
                    # All retries hit land — stay in place
                    continue
            lon, lat = new_lon, new_lat
            outbound.append([round(lon, 5), round(lat, 5)])

        # Inbound leg — return to haul-out along a smoothed shortcut
        inbound_steps = max(5, n_legs // 3)
        inbound: list[list[float]] = []
        for i in range(1, inbound_steps + 1):
            t = i / inbound_steps
            # Lerp with slight random jitter
            ret_lon = lon + (start_lon - lon) * t + rng.gauss(0, 0.02)
            ret_lat = lat + (start_lat - lat) * t + rng.gauss(0, 0.01)
            # Land avoidance on return leg — snap to last sea position
            if not is_sea(ret_lon, ret_lat):
                # Use pure interpolation without jitter (straighter path)
                ret_lon = lon + (start_lon - lon) * t
                ret_lat = lat + (start_lat - lat) * t
                if not is_sea(ret_lon, ret_lat):
                    continue  # skip this waypoint entirely
            inbound.append([round(ret_lon, 5), round(ret_lat, 5)])

        # Combine: haul-out → foraging → return → haul-out
        full_path = outbound + inbound + [[round(start_lon, 5), round(start_lat, 5)]]

        # Use format_trips() to assign timestamps and build the dict
        formatted = format_trips(
            [full_path],
            loop_length=loop_length,
            properties=[{
                "name": f"Seal #{seal_idx + 1}",
                "species": species,
                "haulout": site["name"],
                "color": SPECIES_COLORS[species],
                "seal_id": seal_idx + 1,
            }],
        )
        trips.append(formatted[0])

    return trips


@functools.lru_cache(maxsize=32)
def make_seal_haulout_data() -> list[dict]:
    """Build scatterplot data for haul-out sites with population sizing."""
    return [
        {
            "position": [s["lon"], s["lat"]],
            "name": s["name"],
            "species": s["species"],
            "population": s["population"],
            "radius": max(4, s["population"] / 20),
            "color": SPECIES_COLORS[s["species"]],
        }
        for s in _SEAL_HAULOUT_SITES
    ]


@functools.lru_cache(maxsize=32)
def make_seal_foraging_areas() -> dict:
    """Build GeoJSON polygons approximating foraging ranges around haul-outs.

    Each haul-out gets an elliptical polygon whose size is based on the
    species' typical foraging range.
    """
    import math

    features = []
    for site in _SEAL_HAULOUT_SITES:
        params = _SEAL_TRIP_PARAMS[site["species"]]
        r = params["range_deg"] * 0.5  # semi-axis in degrees
        lon0, lat0 = site["lon"], site["lat"]
        # Build ellipse (lon-stretched because of latitude)
        coords = []
        for i in range(25):
            angle = 2 * math.pi * i / 24
            px = lon0 + r * 1.4 * math.cos(angle)
            py = lat0 + r * 0.8 * math.sin(angle)
            coords.append([round(px, 4), round(py, 4)])
        coords.append(coords[0])  # close ring
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {
                "name": f"{site['name']} foraging area",
                "species": site["species"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


@functools.lru_cache(maxsize=32)
def make_seal_haulout_icons() -> list[dict]:
    """Build IconLayer data for haul-out sites with species-specific icons.

    Each entry has ``position``, ``icon`` (species name mapping into
    the library's :data:`~shiny_deckgl.ibm.ICON_MAPPING`), ``name``,
    ``species``, ``population``, and ``size`` (proportional to log of
    population).

    Returns
    -------
    list[dict]
        Ready for ``icon_layer(data=...)``.
    """
    import math

    return [
        {
            "position": [s["lon"], s["lat"]],
            "icon": s["species"],
            "name": s["name"],
            "species": s["species"],
            "population": s["population"],
            "size": max(24, int(math.log2(s["population"] + 1) * 8)),
        }
        for s in _SEAL_HAULOUT_SITES
    ]


# ---------------------------------------------------------------------------
# McConnell et al. (2017) mechanistic IBM — energy-budget seal movement
# ---------------------------------------------------------------------------
# Adapted from McConnell, Smout & Wu (2017) "Modelling Harbour Seal
# Movements" (Scottish Marine & Freshwater Science Vol 8 No 20).
# The model couples an energy budget (metabolic cost / foraging gain /
# haulout recovery) with habitat-biased movement on a 2-D raster.
# ---------------------------------------------------------------------------

def _build_baltic_habitat(
    resolution: float = 0.25,
) -> tuple:
    """Build a Baltic Sea habitat-quality raster from the embedded sea mask.

    Returns ``(habitat_2d, bounds, haulout_xy, site_quality)`` where
    *habitat_2d* is a numpy array (ny × nx) in [0, 1] — 0 = land,
    positive = sea with foraging-quality gradient.

    Foraging hotspots are placed as Gaussian patches centred on each
    haulout site, overlaid on a base sea value.

    The original implementation used Python loops to sample ``is_sea``
    for every cell; this version leverages numpy vectorisation which is
    substantially quicker for high-resolution rasters.
    """
    import numpy as np

    lon_min, lon_max = _SEA_LON_MIN, _SEA_LON_MAX
    lat_min, lat_max = _SEA_LAT_MIN, _SEA_LAT_MAX

    nx = int(round((lon_max - lon_min) / resolution))
    ny = int(round((lat_max - lat_min) / resolution))

    # Create coordinate grids
    lons = np.linspace(lon_min, lon_max, nx)
    lats = np.linspace(lat_min, lat_max, ny)
    LON, LAT = np.meshgrid(lons, lats)

    # Vectorised sea mask lookup ------------------------------------------------
    mask = np.array(_get_sea_mask(), dtype=bool)
    # Map each raster cell to corresponding mask index
    col_idx = np.clip(np.round((LON - lon_min) / _SEA_RES).astype(int), 0, _SEA_GRID_SHAPE[1] - 1)
    row_idx = np.clip(np.round((LAT - lat_min) / _SEA_RES).astype(int), 0, _SEA_GRID_SHAPE[0] - 1)
    sea_mask_arr = mask[row_idx, col_idx]

    # Base habitat: assign 0.3 to sea cells
    habitat = np.zeros((ny, nx), dtype=np.float64)
    habitat[sea_mask_arr] = 0.3

    # Add Gaussian foraging hotspots near each haulout
    for site in _SEAL_HAULOUT_SITES:
        sigma_lon = _SEAL_TRIP_PARAMS[site["species"]]["range_deg"] * 0.35
        sigma_lat = sigma_lon * 0.6
        patch = 0.7 * np.exp(
            -(((LON - site["lon"]) / sigma_lon) ** 2
              + ((LAT - site["lat"]) / sigma_lat) ** 2) / 2
        )
        habitat += patch

    # Zero out land cells (mask) — already zero by construction

    # Normalize to [0, 1]
    if sea_mask_arr.any():
        hmax = habitat[sea_mask_arr].max()
        if hmax > 0:
            habitat[sea_mask_arr] = habitat[sea_mask_arr] / hmax

    bounds = (lon_min, lon_max, lat_min, lat_max)

    # Haulout coordinates as numpy array
    haulout_xy = np.array(
        [[s["lon"], s["lat"]] for s in _SEAL_HAULOUT_SITES],
        dtype=np.float64,
    )
    # Site quality proportional to population (log-scaled)
    site_quality = np.array(
        [np.log2(s["population"] + 1) / 10.0 for s in _SEAL_HAULOUT_SITES],
        dtype=np.float64,
    )

    return habitat, bounds, haulout_xy, site_quality


# Cache the habitat raster (built lazily on first call)
_BALTIC_HABITAT_CACHE: dict = {}


def _get_baltic_habitat(resolution: float = 0.25) -> tuple:
    """Return cached (habitat, bounds, haulout_xy, site_quality)."""
    if resolution not in _BALTIC_HABITAT_CACHE:
        _BALTIC_HABITAT_CACHE[resolution] = _build_baltic_habitat(resolution)
    return _BALTIC_HABITAT_CACHE[resolution]


@functools.lru_cache(maxsize=32)
def make_seal_trips_ibm(
    n_seals: int = 25,
    sim_hours: int = 168,
    loop_length: int = 600,
    *,
    seed: int = 42,
) -> list[dict]:
    """Generate seal movement tracks using a McConnell-style energy-budget IBM.

    Implements a mechanistic individual-based model following McConnell,
    Smout & Wu (2017) where each seal has:

    - **Energy budget**: metabolic cost while swimming, foraging gain
      proportional to habitat quality, haulout recovery.
    - **Habitat-biased movement**: drift toward higher-quality foraging
      areas via the habitat gradient, plus diffusive random component.
    - **State switching**: seals haul out when energy is depleted or
      max-at-sea time is exceeded, and depart when energy recovers.
    - **Land avoidance**: steps onto land cells are reflected/rejected.

    Each agent's at-sea segments are extracted as separate foraging
    trips and formatted via :func:`format_trips`.

    Parameters
    ----------
    n_seals
        Number of individual seals to simulate.
    sim_hours
        Duration of the simulation in hours (default 168 = one week).
    loop_length
        Animation loop length for ``format_trips()``.
    seed
        Random seed for reproducibility.

    Returns
    -------
    list[dict]
        Same format as :func:`make_seal_trips` — each dict has
        ``path``, ``timestamps``, ``name``, ``species``, ``haulout``,
        ``color``, ``seal_id``.
    """
    import numpy as np
    from .ibm import format_trips

    rng = np.random.default_rng(seed)

    # -- Build environment ------------------------------------------------
    habitat, bounds, haulout_xy, site_quality = _get_baltic_habitat(0.25)
    xmin, xmax, ymin, ymax = bounds
    ny, nx = habitat.shape

    # Precompute gradient field
    gy, gx = np.gradient(habitat)

    def _habitat_value(xy):
        """Bilinear sample of habitat raster at (lon, lat)."""
        u = (xy[0] - xmin) / (xmax - xmin) * (nx - 1)
        v = (xy[1] - ymin) / (ymax - ymin) * (ny - 1)
        if u < 0 or u > nx - 1 or v < 0 or v > ny - 1:
            return 0.0
        u0 = int(np.floor(u))
        v0 = int(np.floor(v))
        u1 = min(u0 + 1, nx - 1)
        v1 = min(v0 + 1, ny - 1)
        du, dv = u - u0, v - v0
        return float(
            (1 - du) * (1 - dv) * habitat[v0, u0]
            + du * (1 - dv) * habitat[v0, u1]
            + (1 - du) * dv * habitat[v1, u0]
            + du * dv * habitat[v1, u1]
        )

    def _gradient_at(xy):
        """Approximate habitat gradient at (lon, lat)."""
        u = np.clip(
            (xy[0] - xmin) / (xmax - xmin) * (nx - 1), 0, nx - 1
        )
        v = np.clip(
            (xy[1] - ymin) / (ymax - ymin) * (ny - 1), 0, ny - 1
        )
        u0, v0 = int(np.floor(u)), int(np.floor(v))
        return np.array([gx[v0, u0], gy[v0, u0]], dtype=np.float64)

    def _softmax(x, tau=0.5):
        x = np.asarray(x, dtype=np.float64)
        x = x - x.max()
        ex = np.exp(x / max(1e-9, tau))
        s = ex.sum()
        return ex / s if s > 0 else np.ones_like(x) / len(x)

    # -- IBM parameters (adapted for lon/lat degrees) ---------------------
    # Typical seal swim speed: 5–7 km/h ≈ 0.05° lat/h
    SPEED_MAX = 0.06          # max displacement per step (degrees)
    DIFFUSIVE_SIGMA = 0.018   # random movement component
    BIAS_STRENGTH = 0.025     # habitat-gradient following
    METABOLIC_COST = 0.04     # energy lost per hour at sea
    FORAGING_SCALE = 0.06     # energy gain * habitat_value per hour
    HAULOUT_RECOVERY = 0.15   # energy recovery per hour hauled out
    ENERGY_LOW = 0.25         # haul-out trigger threshold
    ENERGY_MAX = 1.0
    MIN_HAULOUT_H = 4         # minimum rest hours
    MAX_AT_SEA_H = 72         # maximum hours before forced haulout
    DEPART_ENERGY = 0.85      # energy to re-depart from haulout
    SITE_DIST_PENALTY = 0.3   # utility penalty per degree distance

    # -- Species-specific scaling -----------------------------------------
    _SPECIES_SPEED = {
        "Grey seal": 1.3,     # largest, fastest
        "Ringed seal": 0.75,  # smallest, shortest trips
        "Harbour seal": 1.0,  # reference
    }

    # -- Initialize agents ------------------------------------------------
    n_sites = len(_SEAL_HAULOUT_SITES)
    pop_weights = np.array(
        [s["population"] for s in _SEAL_HAULOUT_SITES], dtype=np.float64
    )
    pop_weights /= pop_weights.sum()

    class _AgentState:
        __slots__ = (
            "xy", "energy", "at_sea", "hours_since_haulout",
            "hours_on_haulout", "current_site", "site_idx",
            "species", "speed_scale",
        )

        # type annotations for mypy
        xy: Any
        energy: float
        at_sea: bool
        hours_since_haulout: float
        hours_on_haulout: float
        current_site: Any | None
        site_idx: int
        species: str
        speed_scale: float

    agents: list = []
    for _ in range(n_seals):
        idx = int(rng.choice(n_sites, p=pop_weights))
        site = _SEAL_HAULOUT_SITES[idx]
        a = _AgentState()
        a.xy = haulout_xy[idx].copy() + rng.normal(0, 0.01, size=2)
        if not is_sea(float(a.xy[0]), float(a.xy[1])):
            a.xy = haulout_xy[idx].copy()
        a.energy = float(rng.uniform(0.7, 1.0))
        a.at_sea = True
        a.hours_since_haulout = 0
        a.hours_on_haulout = 0
        a.current_site = None
        a.site_idx = idx
        a.species = site["species"]
        a.speed_scale = _SPECIES_SPEED[site["species"]]
        agents.append(a)

    # -- Run simulation ---------------------------------------------------
    trajectories: list[list[tuple]] = [[] for _ in range(n_seals)]

    for t in range(sim_hours):
        for i, a in enumerate(agents):
            trajectories[i].append(
                (round(float(a.xy[0]), 5),
                 round(float(a.xy[1]), 5),
                 a.at_sea, a.energy)
            )

            if a.at_sea:
                # -- At-sea step --
                hval = _habitat_value(a.xy)
                a.energy = max(
                    0.0,
                    a.energy - METABOLIC_COST + FORAGING_SCALE * hval,
                )
                a.energy = min(ENERGY_MAX, a.energy)
                a.hours_since_haulout += 1

                # Movement: diffusive + habitat-biased
                grad = _gradient_at(a.xy)
                gnorm = float(np.linalg.norm(grad))
                if gnorm > 0:
                    grad = grad / gnorm

                step = (
                    rng.normal(0, DIFFUSIVE_SIGMA * a.speed_scale, size=2)
                    + BIAS_STRENGTH * a.speed_scale * grad
                )
                speed_lim = SPEED_MAX * a.speed_scale
                L = float(np.linalg.norm(step))
                if L > speed_lim:
                    step = step / L * speed_lim

                new_xy = a.xy + step
                new_xy[0] = np.clip(new_xy[0], xmin + 0.1, xmax - 0.1)
                new_xy[1] = np.clip(new_xy[1], ymin + 0.1, ymax - 0.1)

                # Land avoidance: reflect, perpendicular, or stay
                if not is_sea(float(new_xy[0]), float(new_xy[1])):
                    new_xy = a.xy - step * 0.5
                    new_xy[0] = np.clip(new_xy[0], xmin + 0.1, xmax - 0.1)
                    new_xy[1] = np.clip(new_xy[1], ymin + 0.1, ymax - 0.1)
                    if not is_sea(float(new_xy[0]), float(new_xy[1])):
                        perp = np.array([-step[1], step[0]])
                        new_xy = a.xy + perp * 0.5
                        new_xy[0] = np.clip(
                            new_xy[0], xmin + 0.1, xmax - 0.1
                        )
                        new_xy[1] = np.clip(
                            new_xy[1], ymin + 0.1, ymax - 0.1
                        )
                        if not is_sea(
                            float(new_xy[0]), float(new_xy[1])
                        ):
                            new_xy = a.xy.copy()

                a.xy = new_xy

                # Haulout decision
                need_rest = (
                    a.energy <= ENERGY_LOW
                    or a.hours_since_haulout >= MAX_AT_SEA_H
                )
                if need_rest:
                    dists = np.linalg.norm(
                        haulout_xy - a.xy[np.newaxis, :], axis=1
                    )
                    util = site_quality - SITE_DIST_PENALTY * dists
                    probs = _softmax(util)
                    site_idx = int(rng.choice(n_sites, p=probs))
                    a.xy = haulout_xy[site_idx].copy()
                    a.at_sea = False
                    a.hours_on_haulout = 0
                    a.current_site = site_idx

            else:
                # -- Hauled-out step --
                a.hours_on_haulout += 1
                a.energy = min(
                    ENERGY_MAX, a.energy + HAULOUT_RECOVERY
                )
                if (
                    a.hours_on_haulout >= MIN_HAULOUT_H
                    and a.energy >= DEPART_ENERGY
                ):
                    a.at_sea = True
                    a.hours_since_haulout = 0
                    a.current_site = None
                    push = rng.normal(0, 0.02, size=2)
                    new_xy = a.xy + push
                    if is_sea(float(new_xy[0]), float(new_xy[1])):
                        a.xy = new_xy

    # -- Extract foraging trips from trajectories -------------------------
    trips: list[dict] = []
    trip_id = 0

    for agent_idx in range(n_seals):
        traj = trajectories[agent_idx]
        a = agents[agent_idx]
        site = _SEAL_HAULOUT_SITES[a.site_idx]

        current_trip: list[list[float]] = []
        prev_at_sea = False

        for lon, lat, at_sea, energy in traj:
            if at_sea:
                current_trip.append([lon, lat])
                prev_at_sea = True
            else:
                if prev_at_sea and len(current_trip) >= 3:
                    current_trip.append([lon, lat])
                    trip_id += 1
                    formatted = format_trips(
                        [current_trip],
                        loop_length=loop_length,
                        properties=[{
                            "name": (
                                f"Seal #{agent_idx + 1} "
                                f"trip {trip_id}"
                            ),
                            "species": a.species,
                            "haulout": site["name"],
                            "color": SPECIES_COLORS[a.species],
                            "seal_id": agent_idx + 1,
                        }],
                    )
                    trips.append(formatted[0])
                current_trip = []
                prev_at_sea = False

        # Trip still in progress at end of simulation
        if prev_at_sea and len(current_trip) >= 3:
            trip_id += 1
            formatted = format_trips(
                [current_trip],
                loop_length=loop_length,
                properties=[{
                    "name": f"Seal #{agent_idx + 1} trip {trip_id}",
                    "species": a.species,
                    "haulout": site["name"],
                    "color": SPECIES_COLORS[a.species],
                    "seal_id": agent_idx + 1,
                }],
            )
            trips.append(formatted[0])

    return trips


# ---------------------------------------------------------------------------
# .grd demo mesh paths (resolved relative to package root)
# ---------------------------------------------------------------------------

_EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"

_CURONIAN_GRD = _EXAMPLES_DIR / "curoninan.grd"
CURONIAN_GRD_PATH: str | None = str(_CURONIAN_GRD) if _CURONIAN_GRD.exists() else None
"""Absolute path to the Curonian Lagoon ``curoninan.grd`` demo mesh, or
``None`` if the file is not present (e.g. installed without the examples)."""

_POLYGON_GRD = _EXAMPLES_DIR / "MM_coarse_smooth.grd"
POLYGON_GRD_PATH: str | None = str(_POLYGON_GRD) if _POLYGON_GRD.exists() else None
"""Absolute path to the Mar Piccolo ``MM_coarse_smooth.grd`` demo mesh,
or ``None`` if the file is not present."""


# ---------------------------------------------------------------------------
# Fish species colour map (used by Tab 8 — 3-D Visualisation)
# ---------------------------------------------------------------------------

FISH_SPECIES_COLORS: dict[str, list[int]] = {
    "Atlantic cod":       [230, 25, 75, 200],
    "Baltic herring":     [60, 180, 75, 200],
    "European sprat":     [255, 225, 25, 200],
    "Atlantic salmon":    [0, 130, 200, 200],
    "European flounder":  [245, 130, 48, 200],
    "Pike-perch":         [145, 30, 180, 200],
    "Three-spined stickleback": [70, 240, 240, 200],
    "Ringed seal":        [240, 50, 230, 200],
}


def fish_species_color(species: str) -> list[int]:
    """Return an RGBA colour for a Baltic Sea fish species.

    Falls back to grey ``[180, 180, 180, 200]`` for unknown species.
    """
    return FISH_SPECIES_COLORS.get(species, [180, 180, 180, 200])


# ---------------------------------------------------------------------------
# Gallery data factories (Tab 1 — all 24 layer helpers)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=32)
def make_gallery_port_data() -> list[dict]:
    """Ports formatted for ScatterplotLayer (gallery)."""
    return [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "country": p["country"],
            "cargo_mt": p["cargo_mt"],
            "layerType": "ScatterplotLayer",
        }
        for p in PORTS
    ]


@functools.lru_cache(maxsize=32)
def make_gallery_arc_data() -> list[dict]:
    """Route endpoints for ArcLayer (gallery)."""
    return [
        {
            "sourcePosition": r["waypoints"][0],
            "targetPosition": r["waypoints"][-1],
            "name": f"{r['from']} \u2192 {r['to']}",
            "layerType": "ArcLayer",
        }
        for r in ROUTES
    ]


@functools.lru_cache(maxsize=32)
def make_gallery_line_data() -> list[dict]:
    """Adjacent port pairs for LineLayer (gallery)."""
    return [
        {
            "sourcePosition": [PORTS[i]["lon"], PORTS[i]["lat"]],
            "targetPosition": [PORTS[(i + 1) % len(PORTS)]["lon"],
                               PORTS[(i + 1) % len(PORTS)]["lat"]],
            "name": (
                f"{PORTS[i]['name']} \u2192 "
                f"{PORTS[(i + 1) % len(PORTS)]['name']}"
            ),
            "layerType": "LineLayer",
        }
        for i in range(len(PORTS))
    ]


@functools.lru_cache(maxsize=32)
def make_gallery_path_data() -> list[dict]:
    """Route waypoints for PathLayer (gallery)."""
    return [
        {
            "path": r["waypoints"],
            "name": f"{r['from']} \u2192 {r['to']}",
            "color": r["color"],
            "layerType": "PathLayer",
        }
        for r in ROUTES
    ]


@functools.lru_cache(maxsize=32)
def make_gallery_text_data() -> list[dict]:
    """Port name labels for TextLayer (gallery)."""
    return [
        {
            "position": [p["lon"], p["lat"]],
            "text": p["name"],
            "name": p["name"],
            "layerType": "TextLayer",
        }
        for p in PORTS
    ]


@functools.lru_cache(maxsize=32)
def make_gallery_icon_data() -> list[dict]:
    """Port positions for IconLayer (gallery)."""
    return [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "layerType": "IconLayer",
        }
        for p in PORTS
    ]


@functools.lru_cache(maxsize=32)
def make_gallery_column_data() -> list[dict]:
    """Port cargo as 3-D columns for ColumnLayer (gallery)."""
    return [
        {
            "position": [p["lon"], p["lat"]],
            "elevation": p["cargo_mt"] * 200,
            "name": p["name"],
            "cargo_mt": p["cargo_mt"],
            "layerType": "ColumnLayer",
        }
        for p in PORTS
    ]


# ---------------------------------------------------------------------------
# Default legend metadata for layer gallery
# ---------------------------------------------------------------------------

LAYER_LEGEND_META: dict[str, tuple[list[int], str]] = {
    "ScatterplotLayer": ([0, 180, 120], "circle"),
    "GeoJsonLayer": ([0, 180, 120], "rect"),
    "ArcLayer": ([200, 80, 80], "arc"),
    "LineLayer": ([120, 120, 200], "line"),
    "PathLayer": ([180, 100, 60], "line"),
    "IconLayer": ([220, 150, 30], "circle"),
    "TextLayer": ([100, 100, 100], "rect"),
    "ColumnLayer": ([160, 80, 200], "rect"),
    "PolygonLayer": ([0, 160, 180], "rect"),
    "GreatCircleLayer": ([200, 60, 150], "arc"),
    "HeatmapLayer": ([255, 80, 0], "gradient"),
    "HexagonLayer": ([80, 160, 80], "rect"),
    "GridLayer": ([0, 120, 200], "rect"),
    "ScreenGridLayer": ([200, 200, 0], "rect"),
    "ContourLayer": ([100, 0, 200], "line"),
    "H3HexagonLayer": ([255, 140, 0], "rect"),
    "TripsLayer": ([253, 128, 93], "line"),
    "TileLayer": ([100, 140, 100], "rect"),
    "BitmapLayer": ([180, 140, 100], "rect"),
    "MVTLayer": ([0, 150, 136], "rect"),
    "WMSLayer": ([70, 130, 180], "rect"),
    "PointCloudLayer": ([200, 100, 50], "circle"),
    "SimpleMeshLayer": ([80, 160, 220], "rect"),
    "MeshNodes": ([255, 200, 60], "circle"),
    "TerrainLayer": ([120, 160, 80], "rect"),
}
"""Layer-type → (colour, shape) mapping for ``deck_legend_control``."""
