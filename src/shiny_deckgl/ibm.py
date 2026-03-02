"""Individual-Based Model (IBM) movement-visualisation helpers.

This module provides ready-to-use data generators and SVG sprite assets
for visualising animal movement tracks on a deck.gl map.  The current
implementation uses Baltic Sea seal species as a reference case, but the
patterns are intentionally generic enough to adapt to other taxa.

Public API
----------
**Constants**

* ``SEAL_HAULOUT_SITES``   – 13 real colony locations (3 species)
* ``SEAL_SPECIES_COLORS``  – RGBA look-up per species
* ``SEAL_TRIP_PARAMS``     – per-species foraging trip parameters
* ``SEAL_ICON_ATLAS``      – base64 data-URI of a 192×64 SVG sprite sheet
* ``SEAL_ICON_MAPPING``    – deck.gl icon-mapping dict keyed by species

**Generators**

* ``make_seal_trips()``          – correlated random-walk tracks
* ``make_seal_haulout_data()``   – scatterplot data for colony sites
* ``make_seal_foraging_areas()`` – GeoJSON elliptical foraging ranges
* ``make_seal_haulout_icons()``  – IconLayer data for haul-out markers
"""

from __future__ import annotations

import math
import random as _random

__all__ = [
    "SEAL_HAULOUT_SITES",
    "SEAL_SPECIES_COLORS",
    "SEAL_TRIP_PARAMS",
    "SEAL_ICON_ATLAS",
    "SEAL_ICON_MAPPING",
    "make_seal_trips",
    "make_seal_haulout_data",
    "make_seal_foraging_areas",
    "make_seal_haulout_icons",
]

# ---------------------------------------------------------------------------
# Colony / haul-out reference data
# ---------------------------------------------------------------------------

#: Real Baltic Sea haul-out / breeding sites for three seal species.
#: Coordinates are approximate centres of documented colony locations.
SEAL_HAULOUT_SITES: list[dict] = [
    # Grey seal (Halichoerus grypus) — large offshore sandbanks & skerries
    {"name": "Gotland NW skerries",   "species": "Grey seal",    "lon": 18.15, "lat": 57.95, "population": 120},
    {"name": "Åland archipelago",      "species": "Grey seal",    "lon": 20.10, "lat": 60.15, "population": 200},
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
    {"name": "Limfjorden",             "species": "Harbour seal", "lon": 12.20, "lat": 55.30, "population": 110},
    {"name": "Kalmar Strait",          "species": "Harbour seal", "lon": 16.60, "lat": 56.60, "population":  85},
    {"name": "Wismar Bay",             "species": "Harbour seal", "lon": 11.50, "lat": 54.10, "population":  70},
]

#: RGBA colours per species for consistent rendering across layers.
SEAL_SPECIES_COLORS: dict[str, list[int]] = {
    "Grey seal":    [100, 100, 100, 220],   # slate grey
    "Ringed seal":  [70, 140, 220, 220],    # icy blue
    "Harbour seal": [180, 140, 80, 220],    # sandy brown
}

#: Typical foraging-trip parameters by species (from telemetry literature).
#:
#: * ``range_deg`` – approximate foraging range in degrees
#: * ``step``      – step size per leg (degrees)
#: * ``legs``      – mean number of legs in a foraging trip
#: * ``turn``      – concentration of the wrapped-Cauchy turn distribution
SEAL_TRIP_PARAMS: dict[str, dict] = {
    "Grey seal":    {"range_deg": 1.8, "step": 0.06, "legs": 30, "turn": 0.6},
    "Ringed seal":  {"range_deg": 0.8, "step": 0.03, "legs": 20, "turn": 0.9},
    "Harbour seal": {"range_deg": 1.2, "step": 0.04, "legs": 25, "turn": 0.7},
}

# ---------------------------------------------------------------------------
# SVG icon atlas (base64-encoded sprite sheet for deck.gl IconLayer)
# ---------------------------------------------------------------------------
# Three 64×64 species-coloured seal silhouettes in a 192×64 strip.
# Each species has its own fill colour, a darker accent stroke for
# definition, a lighter belly patch, and a tiny eye dot.
# Base64 encoding is used for reliable loading across browsers.
# viewBox is 0 0 192 64, aligned with the on-screen sprite dimensions.
# Each species is drawn with SVG <path> elements for a realistic
# swimming-seal silhouette (torpedo body, rounded head, hind flippers).
#
# Grey seal    (x=0):   #7a8a8a slate-grey, bulky body, broad snout
# Ringed seal  (x=64):  #4a8cdc icy blue, slender body, small head
# Harbour seal (x=128): #c8a050 sandy gold, medium build, rounded head

#: Base64-encoded data-URI of the 192×64 SVG sprite-sheet.  Pass this as
#: ``iconAtlas`` to ``icon_layer()`` or the ``_tripsHeadIcons`` dict.
SEAL_ICON_ATLAS: str = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIx"
    "OTIiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCAxOTIgNjQiPjxnIHRyYW5zZm9y"
    "bT0idHJhbnNsYXRlKDAsMCkiPjxwYXRoIGQ9Ik0gNiwzNCBDIDQsMzAgMywyOCA2"
    "LDI2IEwgOCwyNCBDIDEwLDIyIDEwLDI2IDEyLDI4IEMgMTYsMjIgMjQsMTggMzQs"
    "MTggQyA0MiwxOCA0OCwyMCA1MiwyNCBDIDU2LDI2IDU4LDI4IDU4LDMwIEMgNjAs"
    "MzEgNjAsMzMgNTgsMzQgQyA1NiwzNiA1NCwzOCA1MCwzOCBDIDQ2LDQwIDQwLDQy"
    "IDM0LDQyIEMgMjQsNDIgMTYsNDAgMTIsMzYgQyAxMCwzOCAxMCwzNiA4LDM4IEwg"
    "Niw0MCBDIDMsMzggNCwzNiA2LDM0IFoiIGZpbGw9IiM3YThhOGEiIHN0cm9rZT0i"
    "IzVhNmE2YSIgc3Ryb2tlLXdpZHRoPSIwLjgiLz48cGF0aCBkPSJNIDIwLDMwIEMg"
    "MjYsMjggNDAsMjggNDgsMzAgQyA0OCwzNCA0MCwzOCAzNCwzOCBDIDI2LDM4IDIw"
    "LDM0IDIwLDMwIFoiIGZpbGw9IiM5NWE1YTAiIG9wYWNpdHk9IjAuNCIvPjxlbGxp"
    "cHNlIGN4PSI0MCIgY3k9IjQwIiByeD0iNSIgcnk9IjIiIGZpbGw9IiM1YTZhNmEi"
    "IHRyYW5zZm9ybT0icm90YXRlKC0xNSw0MCw0MCkiLz48Y2lyY2xlIGN4PSIxMCIg"
    "Y3k9IjI2IiByPSIxLjIiIGZpbGw9IiMyMjIiIG9wYWNpdHk9IjAuNyIvPjwvZz48"
    "ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSg2NCwwKSI+PHBhdGggZD0iTSA4LDM0IEMg"
    "NiwzMSA1LDI5IDgsMjcgTCAxMCwyNSBDIDExLDIzIDExLDI3IDE0LDI5IEMgMTgs"
    "MjMgMjYsMjAgMzUsMjAgQyA0MiwyMCA0NywyMiA1MCwyNSBDIDUzLDI3IDU1LDI5"
    "IDU1LDMxIEMgNTcsMzIgNTcsMzQgNTUsMzUgQyA1MywzNyA1MSwzOCA0OCwzOCBD"
    "IDQ0LDQwIDM4LDQxIDM1LDQxIEMgMjYsNDEgMTgsMzkgMTQsMzYgQyAxMSwzNyAx"
    "MSwzNiAxMCwzOCBMIDgsMzkgQyA1LDM4IDYsMzYgOCwzNCBaIiBmaWxsPSIjNGE4"
    "Y2RjIiBzdHJva2U9IiMzNDZhYjAiIHN0cm9rZS13aWR0aD0iMC44Ii8+PHBhdGgg"
    "ZD0iTSAyMiwzMCBDIDI4LDI4IDQwLDI5IDQ3LDMxIEMgNDcsMzQgMzksMzcgMzUs"
    "MzcgQyAyNywzNyAyMiwzNCAyMiwzMCBaIiBmaWxsPSIjNmVhYWYwIiBvcGFjaXR5"
    "PSIwLjQiLz48ZWxsaXBzZSBjeD0iMzgiIGN5PSIzOS41IiByeD0iNCIgcnk9IjEu"
    "NSIgZmlsbD0iIzM0NmFiMCIgdHJhbnNmb3JtPSJyb3RhdGUoLTEyLDM4LDM5LjUp"
    "Ii8+PGNpcmNsZSBjeD0iMTIiIGN5PSIyNyIgcj0iMSIgZmlsbD0iIzIyMiIgb3Bh"
    "Y2l0eT0iMC43Ii8+PC9nPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEyOCwwKSI+"
    "PHBhdGggZD0iTSA3LDM0IEMgNSwzMSA0LDI5IDcsMjcgTCA5LDI1IEMgMTAsMjMg"
    "MTAsMjcgMTMsMjkgQyAxNywyMiAyNSwxOSAzNCwxOSBDIDQyLDE5IDQ3LDIxIDUx"
    "LDI0IEMgNTQsMjYgNTYsMjggNTYsMzEgQyA1OCwzMiA1OCwzNCA1NiwzNSBDIDU0"
    "LDM3IDUyLDM4IDQ5LDM4IEMgNDUsNDAgMzksNDIgMzQsNDIgQyAyNSw0MiAxNyw0"
    "MCAxMywzNiBDIDEwLDM3IDEwLDM2IDksMzggTCA3LDQwIEMgNCwzOCA1LDM2IDcs"
    "MzQgWiIgZmlsbD0iI2M4YTA1MCIgc3Ryb2tlPSIjOWE3YTMwIiBzdHJva2Utd2lk"
    "dGg9IjAuOCIvPjxwYXRoIGQ9Ik0gMjEsMzAgQyAyNywyOCA0MCwyOCA0OCwzMSBD"
    "IDQ4LDM0IDQwLDM4IDM0LDM4IEMgMjYsMzggMjEsMzQgMjEsMzAgWiIgZmlsbD0i"
    "I2UwYzg3OCIgb3BhY2l0eT0iMC40Ii8+PGVsbGlwc2UgY3g9IjM5IiBjeT0iNDAi"
    "IHJ4PSI0LjUiIHJ5PSIxLjgiIGZpbGw9IiM5YTdhMzAiIHRyYW5zZm9ybT0icm90"
    "YXRlKC0xNCwzOSw0MCkiLz48Y2lyY2xlIGN4PSIxMSIgY3k9IjI3IiByPSIxLjEi"
    "IGZpbGw9IiMyMjIiIG9wYWNpdHk9IjAuNyIvPjwvZz48L3N2Zz4="
)

#: deck.gl icon-mapping dict keyed by species name.
#: ``anchorY=32`` centres the icon vertically on the point.
SEAL_ICON_MAPPING: dict[str, dict] = {
    "Grey seal":    {"x": 0,   "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Ringed seal":  {"x": 64,  "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Harbour seal": {"x": 128, "y": 0, "width": 64, "height": 64, "anchorY": 32},
}


# ---------------------------------------------------------------------------
# Data generators
# ---------------------------------------------------------------------------

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
        Each dict has ``path`` (list of ``[lon, lat, timestamp]``),
        ``timestamps``, ``name``, ``species``, ``haulout``,
        ``color``, and ``seal_id``.

    Example
    -------
    >>> from shiny_deckgl.ibm import make_seal_trips
    >>> trips = make_seal_trips(n_seals=10, loop_length=300)
    >>> len(trips)
    10
    """
    rng = _random.Random(seed)
    trips: list[dict] = []

    for seal_idx in range(n_seals):
        # Pick a haul-out site (weighted by population)
        site = rng.choices(
            SEAL_HAULOUT_SITES,
            weights=[s["population"] for s in SEAL_HAULOUT_SITES],
            k=1,
        )[0]
        species = site["species"]
        params = SEAL_TRIP_PARAMS[species]

        # Starting position (jittered around haul-out)
        start_lon = site["lon"] + rng.gauss(0, 0.05)
        start_lat = site["lat"] + rng.gauss(0, 0.03)

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
            lon += step_size * math.cos(heading) * rng.uniform(0.7, 1.3)
            lat += step_size * math.sin(heading) * 0.6 * rng.uniform(0.7, 1.3)
            # Clamp to Baltic bounds
            lon = max(9.0, min(30.0, lon))
            lat = max(53.0, min(66.0, lat))
            outbound.append([round(lon, 5), round(lat, 5)])

        # Inbound leg — return to haul-out along a smoothed shortcut
        inbound_steps = max(5, n_legs // 3)
        inbound: list[list[float]] = []
        for i in range(1, inbound_steps + 1):
            t = i / inbound_steps
            # Lerp with slight random jitter
            ret_lon = lon + (start_lon - lon) * t + rng.gauss(0, 0.02)
            ret_lat = lat + (start_lat - lat) * t + rng.gauss(0, 0.01)
            inbound.append([round(ret_lon, 5), round(ret_lat, 5)])

        # Combine: haul-out → foraging → return → haul-out
        full_path = outbound + inbound + [[round(start_lon, 5), round(start_lat, 5)]]

        # Assign timestamps evenly over the loop
        n_pts = len(full_path)
        timestamps = [int(i * loop_length / (n_pts - 1)) for i in range(n_pts)]
        path_3d = [[pt[0], pt[1], ts] for pt, ts in zip(full_path, timestamps)]

        trips.append({
            "path": path_3d,
            "timestamps": timestamps,
            "name": f"Seal #{seal_idx + 1}",
            "species": species,
            "haulout": site["name"],
            "color": SEAL_SPECIES_COLORS[species],
            "seal_id": seal_idx + 1,
        })

    return trips


def make_seal_haulout_data() -> list[dict]:
    """Build scatterplot data for haul-out sites with population sizing.

    Returns
    -------
    list[dict]
        Each dict has ``position``, ``name``, ``species``,
        ``population``, ``radius``, and ``color``.
    """
    return [
        {
            "position": [s["lon"], s["lat"]],
            "name": s["name"],
            "species": s["species"],
            "population": s["population"],
            "radius": max(4, s["population"] / 20),
            "color": SEAL_SPECIES_COLORS[s["species"]],
        }
        for s in SEAL_HAULOUT_SITES
    ]


def make_seal_foraging_areas() -> dict:
    """Build GeoJSON polygons approximating foraging ranges around haul-outs.

    Each haul-out gets an elliptical polygon whose size is based on the
    species' typical foraging range.

    Returns
    -------
    dict
        A GeoJSON ``FeatureCollection``.
    """
    features = []
    for site in SEAL_HAULOUT_SITES:
        params = SEAL_TRIP_PARAMS[site["species"]]
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
    """Build IconLayer data for haul-out sites with species-specific seal icons.

    Each entry has ``position``, ``icon`` (species name mapping into
    :data:`SEAL_ICON_MAPPING`), ``name``, ``species``, ``population``,
    and ``size`` (proportional to log of population).

    Returns
    -------
    list[dict]
        Ready for ``icon_layer(data=...)``.
    """
    return [
        {
            "position": [s["lon"], s["lat"]],
            "icon": s["species"],
            "name": s["name"],
            "species": s["species"],
            "population": s["population"],
            "size": max(24, int(math.log2(s["population"] + 1) * 8)),
        }
        for s in SEAL_HAULOUT_SITES
    ]
