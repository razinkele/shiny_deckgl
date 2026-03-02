"""Sample data and helper functions for the shiny_deckgl demo app.

Baltic Sea ports, shipping routes, MPA GeoJSON, and WMS layer definitions.
"""

from __future__ import annotations

import functools
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
    except Exception:  # noqa: BLE001 — network/parse failures
        return _WMS_LAYER_FALLBACK


WMS_LAYER_CHOICES = _fetch_wms_layer_choices()

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
import base64 as _b64
import zlib as _zlib

_SEA_MASK_B64 = (
    "eJwdjSESQjEMRF+JKO5b/gxDr4DE/Rv88zCY9mCIOBxnqEOCrGB+SIjYye5mN+CzD9jN"
    "4wyrvXyf6hfmxSD12uEqzp+8HxQ9WZeP2J0jxSJoGgnbQA65k7YQa4h5/P2AKTg3aF7J"
    "BUrLShrhLlr8h8pocfMDPY8m5Q=="
)
_SEA_GRID_SHAPE = (27, 43)  # (lat_rows, lon_cols)
_SEA_LON_MIN, _SEA_LON_MAX = 9.0, 30.0
_SEA_LAT_MIN, _SEA_LAT_MAX = 53.0, 66.0
_SEA_RES = 0.5  # degrees


def _load_sea_mask():
    """Decode the embedded sea mask into a 2-D numpy-like list of lists."""
    raw = _zlib.decompress(_b64.b64decode(_SEA_MASK_B64))
    bits: list[int] = []
    for byte in raw:
        for bit in range(7, -1, -1):
            bits.append((byte >> bit) & 1)
    total = _SEA_GRID_SHAPE[0] * _SEA_GRID_SHAPE[1]
    flat = bits[:total]
    grid = []
    cols = _SEA_GRID_SHAPE[1]
    for r in range(_SEA_GRID_SHAPE[0]):
        grid.append(flat[r * cols : (r + 1) * cols])
    return grid


_SEA_MASK: list[list[int]] = _load_sea_mask()


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
    return _SEA_MASK[row][col] == 1

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
