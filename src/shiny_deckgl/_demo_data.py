"""Sample data and helper functions for the shiny_deckgl demo app.

Baltic Sea ports, shipping routes, MPA GeoJSON, and WMS layer definitions.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from .components import (
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
_MPA_GEOJSON_CACHE: dict | None = None


def _load_mpa_geojson() -> dict:
    """Lazy-load and cache the HELCOM MPA GeoJSON (avoids import-time I/O)."""
    global _MPA_GEOJSON_CACHE
    if _MPA_GEOJSON_CACHE is None:
        with open(_MPA_PATH) as f:
            _MPA_GEOJSON_CACHE = json.load(f)
        # Normalise property keys to lower-case for tooltip consistency
        for feat in _MPA_GEOJSON_CACHE["features"]:
            feat["properties"] = {k.lower(): v for k, v in feat["properties"].items()}
    return _MPA_GEOJSON_CACHE


def __getattr__(name: str):
    """Module-level lazy accessor for ``MPA_GEOJSON``."""
    if name == "MPA_GEOJSON":
        return _load_mpa_geojson()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# ---------------------------------------------------------------------------
# EMODnet WMS layers
# ---------------------------------------------------------------------------

EMODNET_WMS_URL = "https://ows.emodnet-bathymetry.eu/wms"

WMS_LAYER_CHOICES = {
    "": "(none)",
    "emodnet:mean": "Mean depth  [emodnet:mean]",
    "emodnet:mean_atlas_land": "Mean depth + land  [emodnet:mean_atlas_land]",
    "emodnet:mean_multicolour": "Mean depth multi-colour  [emodnet:mean_multicolour]",
    "emodnet:mean_rainbowcolour": "Mean depth rainbow  [emodnet:mean_rainbowcolour]",
    "coastlines": "Coastlines  [coastlines]",
    "emodnet:contours": "Depth contours  [emodnet:contours]",
}

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


def make_heatmap_points(n: int = 300) -> list[list[float]]:
    """Generate random observation points clustered around Baltic ports."""
    random.seed(42)
    pts: list[list[float]] = []
    for _ in range(n):
        port = random.choice(PORTS)
        lon = port["lon"] + random.gauss(0, 1.5)
        lat = port["lat"] + random.gauss(0, 0.8)
        weight = random.uniform(1, 10)
        pts.append([lon, lat, weight])
    return pts


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


def make_trips_data(loop_length: int = 1800) -> list[dict]:
    """Build TripsLayer data from Baltic shipping routes.

    Each route generates a "trip" with a ``path`` array of
    ``[lon, lat, timestamp]`` triplets and a ``timestamps`` array.
    Timestamps are evenly spaced over the segment from ``0`` to
    ``loop_length``.
    """
    trips: list[dict] = []
    for r in ROUTES:
        wps = r["waypoints"]
        n = len(wps)
        if n < 2:
            continue
        timestamps = [int(i * loop_length / (n - 1)) for i in range(n)]
        path = [[wp[0], wp[1], ts] for wp, ts in zip(wps, timestamps)]
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


def make_3d_arc_data() -> list[dict]:
    """Build 3-D arc data where source/target have altitude (z) components.

    Uses real Baltic port-to-port shipping routes with synthetic
    altitude values representing flight / drone corridors — handy for
    demonstrating ``arc_layer`` in a pitched 3-D view.
    """
    arcs = []
    for r in ROUTES:
        wp = r["waypoints"]
        # Height proportional to route length (longer = higher arc)
        alt = len(wp) * 500.0
        arcs.append({
            "sourcePosition": [wp[0][0], wp[0][1], 0],
            "targetPosition": [wp[-1][0], wp[-1][1], 0],
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
