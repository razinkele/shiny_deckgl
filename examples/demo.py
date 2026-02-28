"""Comprehensive shiny_deckgl demo — showcases every feature of the library.

Run with:
    micromamba run -n shiny python -m shiny run examples/demo.py --port 19876

Tabs:
  1. Interactive Map  – basemaps, palettes, color modes, layer visibility,
                        WMS (EMODnet via OWSLib), fly-to, drag marker
  2. Events & Tooltips – live click/hover/viewport readback, drag marker,
                         dynamic tooltip customisation
  3. Colour Scales     – palette swatches, color_bins, color_quantiles tables
  4. Advanced          – 3-D column map with lighting effects,
                         binary transport (numpy), DataFilterExtension
  5. Export            – standalone HTML export, JSON round-trip
"""
from __future__ import annotations

import json
import os
import random
import tempfile

from owslib.wms import WebMapService
from shiny import App, reactive, render, Session, ui

from shiny_deckgl import (
    MapWidget,
    head_includes,
    # Layer helpers
    layer,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    bitmap_layer,
    # Basemap constants
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    # Color utilities
    color_range,
    color_bins,
    color_quantiles,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
    # Binary transport
    encode_binary_attribute,
    # View helpers
    map_view,
    first_person_view,
)

# Re-export names used in docstring / manual testing only
_ = (bitmap_layer, map_view, first_person_view)


# ---------------------------------------------------------------------------
# Sample data — Baltic Sea ports, routes, and marine observations
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

ROUTES = [
    {"from": "Klaipėda",   "to": "Gdańsk",     "color": [0, 180, 230, 180]},
    {"from": "Klaipėda",   "to": "Stockholm",   "color": [0, 200, 120, 180]},
    {"from": "Helsinki",   "to": "Tallinn",     "color": [255, 140, 0, 180]},
    {"from": "Riga",       "to": "Stockholm",   "color": [180, 0, 200, 180]},
    {"from": "Copenhagen", "to": "Rostock",     "color": [255, 80, 80, 180]},
    {"from": "Gdańsk",     "to": "Kaliningrad", "color": [100, 200, 100, 180]},
    {"from": "Ventspils",  "to": "Stockholm",   "color": [200, 200, 0, 180]},
]

# Marine Protected Area polygons (simplified)
MPA_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Curonian Lagoon MPA", "area_km2": 1584},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [20.85, 55.25], [21.25, 55.25], [21.30, 55.50],
                    [21.25, 55.75], [21.10, 55.90], [20.95, 55.90],
                    [20.85, 55.70], [20.80, 55.45], [20.85, 55.25],
                ]],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Gotland Basin", "area_km2": 3200},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [18.00, 57.00], [20.00, 57.00], [20.50, 57.80],
                    [20.00, 58.50], [18.50, 58.50], [17.50, 57.80],
                    [18.00, 57.00],
                ]],
            },
        },
    ],
}


def _port_by_name(name: str) -> dict:
    return next(p for p in PORTS if p["name"] == name)


def _make_arc_data() -> list[dict]:
    """Build arc data from routes."""
    arcs = []
    for r in ROUTES:
        src = _port_by_name(r["from"])
        tgt = _port_by_name(r["to"])
        arcs.append({
            "sourcePosition": [src["lon"], src["lat"]],
            "targetPosition": [tgt["lon"], tgt["lat"]],
            "sourceColor": r["color"],
            "targetColor": r["color"],
            "from": r["from"],
            "to": r["to"],
        })
    return arcs


def _make_heatmap_points(n: int = 300) -> list[list[float]]:
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


def _make_path_data() -> list[dict]:
    """Build path data — polylines for shipping routes."""
    paths = []
    for r in ROUTES:
        src = _port_by_name(r["from"])
        tgt = _port_by_name(r["to"])
        waypoints = []
        for i in range(11):
            t = i / 10
            waypoints.append([
                src["lon"] + (tgt["lon"] - src["lon"]) * t,
                src["lat"] + (tgt["lat"] - src["lat"]) * t,
            ])
        paths.append({
            "path": waypoints,
            "name": f"{r['from']} → {r['to']}",
            "color": r["color"],
        })
    return paths


def _make_port_data_simple() -> list[dict]:
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


# ---------------------------------------------------------------------------
# EMODnet WMS layer discovery (via OWSLib)
# ---------------------------------------------------------------------------

EMODNET_WMS_URL = "https://ows.emodnet-bathymetry.eu/wms"

try:
    _wms = WebMapService(EMODNET_WMS_URL, version="1.3.0")
    WMS_LAYER_CHOICES: dict[str, str] = {"": "(none)"}
    for layer_name, layer_meta in _wms.contents.items():
        WMS_LAYER_CHOICES[layer_name] = f"{layer_meta.title}  [{layer_name}]"
except Exception:
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
# Basemap & palette lookup dicts
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
# Three map widgets — one per tab that needs a map
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

# Tab 1 — Interactive Map
map_widget = MapWidget(
    "demo_map",
    tooltip={
        "html": "<b>{name}</b><br/>Country: {country}<br/>Cargo: {cargo_mt} Mt",
        "style": {"backgroundColor": "#0b2140", "color": "#d0f0fa",
                  "fontSize": "13px", "borderLeft": "3px solid #1db9c3",
                  "borderRadius": "6px", "padding": "8px 12px"},
    },
    view_state=BALTIC_VIEW,
)

# Tab 2 — Events & Tooltips (tooltip updated dynamically)
DEFAULT_TOOLTIP_HTML = "<b>{name}</b><br/>Country: {country}<br/>Cargo: {cargo_mt} Mt"

events_widget = MapWidget(
    "events_map",
    tooltip={
        "html": DEFAULT_TOOLTIP_HTML,
        "style": {"backgroundColor": "#0b2140", "color": "#d0f0fa",
                  "fontSize": "13px", "borderLeft": "3px solid #1db9c3",
                  "borderRadius": "6px", "padding": "8px 12px"},
    },
    view_state=BALTIC_VIEW,
)

# Tab 4 — Advanced (3-D columns for lighting demo)
adv_widget = MapWidget(
    "adv_map",
    tooltip={
        "html": "<b>{name}</b><br/>Cargo: {cargo_mt} Mt",
        "style": {"backgroundColor": "#0b2140", "color": "#d0f0fa",
                  "fontSize": "13px", "borderLeft": "3px solid #14919b",
                  "borderRadius": "6px", "padding": "8px 12px"},
    },
    view_state={**BALTIC_VIEW, "pitch": 45},
)


# ═══════════════════════════════════════════════════════════════════════════
# UI — Marine-themed design
# ═══════════════════════════════════════════════════════════════════════════

MARINE_CSS = """
/* ── Google Font ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Design tokens ───────────────────────────────────────────────────── */
:root {
  --sea-900: #071526;
  --sea-800: #0b2140;
  --sea-700: #0d3158;
  --sea-600: #124a78;
  --sea-500: #1a6fa0;
  --sea-400: #2196c8;
  --sea-300: #4ec5e0;
  --sea-200: #99ddf0;
  --sea-100: #d0f0fa;
  --sea-50:  #edf8fd;
  --teal-600: #0d7377;
  --teal-500: #14919b;
  --teal-400: #1db9c3;
  --foam-500: #5ce0d2;
  --foam-200: #b5f0e8;
  --sand-50:  #f8f6f3;
  --coral-500: #e8604c;
  --amber-500: #f0a830;
  --navy-text: #c8dce8;
  --sidebar-bg: #091e36;
  --sidebar-border: rgba(30, 120, 180, 0.20);
  --card-border: rgba(20, 100, 160, 0.15);
  --card-shadow: 0 1px 4px rgba(8, 30, 60, 0.08), 0 4px 12px rgba(8, 30, 60, 0.05);
}

/* ── Base ────────────────────────────────────────────────────────────── */
body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  background: var(--sea-50) !important;
  color: #1c2d3f;
}

/* ── Navbar ──────────────────────────────────────────────────────────── */
.navbar {
  background: linear-gradient(135deg, var(--sea-900) 0%, var(--sea-700) 100%) !important;
  border-bottom: 2px solid var(--sea-400) !important;
  box-shadow: 0 2px 16px rgba(7, 21, 38, 0.35);
  padding: 0 1rem;
  min-height: 52px;
}
.navbar-brand {
  font-weight: 700 !important;
  font-size: 1.15rem !important;
  color: #fff !important;
  letter-spacing: -0.02em;
}
.navbar-brand:hover { color: var(--sea-200) !important; }

/* Tabs in navbar */
.navbar-nav .nav-link {
  color: var(--navy-text) !important;
  font-weight: 500;
  font-size: 0.88rem;
  padding: 0.65rem 1rem !important;
  border-radius: 6px 6px 0 0;
  transition: color 0.2s, background 0.2s;
  margin: 0 1px;
}
.navbar-nav .nav-link:hover {
  color: #fff !important;
  background: rgba(255,255,255,0.08);
}
.navbar-nav .nav-link.active,
.navbar-nav .nav-item.active > .nav-link {
  color: #fff !important;
  background: var(--sea-600) !important;
  border-bottom: 2px solid var(--sea-300);
}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
.bslib-sidebar-layout > .sidebar {
  background: var(--sidebar-bg) !important;
  border-right: 1px solid var(--sidebar-border) !important;
  color: var(--navy-text) !important;
}
.bslib-sidebar-layout > .sidebar label,
.bslib-sidebar-layout > .sidebar .control-label,
.bslib-sidebar-layout > .sidebar .form-label {
  color: var(--sea-200) !important;
  font-weight: 500;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.bslib-sidebar-layout > .sidebar .form-select,
.bslib-sidebar-layout > .sidebar .form-control {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(100,180,220,0.18) !important;
  color: #e0eef8 !important;
  font-size: 0.85rem;
  border-radius: 6px;
}
.bslib-sidebar-layout > .sidebar .form-select:focus,
.bslib-sidebar-layout > .sidebar .form-control:focus {
  border-color: var(--sea-400) !important;
  box-shadow: 0 0 0 2px rgba(33, 150, 200, 0.25) !important;
}
.bslib-sidebar-layout > .sidebar .form-select option {
  background: var(--sea-800);
  color: #e0eef8;
}

/* Radio buttons / switches inside sidebar */
.bslib-sidebar-layout > .sidebar .form-check-label {
  color: var(--navy-text) !important;
  font-size: 0.85rem;
  text-transform: none;
  letter-spacing: normal;
}
.bslib-sidebar-layout > .sidebar .form-check-input:checked {
  background-color: var(--teal-500) !important;
  border-color: var(--teal-500) !important;
}
.bslib-sidebar-layout > .sidebar .form-switch .form-check-input:checked {
  background-color: var(--teal-400) !important;
  border-color: var(--teal-400) !important;
}

/* Sidebar section headers */
.bslib-sidebar-layout > .sidebar h5,
.bslib-sidebar-layout > .sidebar .sidebar-section-title {
  color: var(--sea-300) !important;
  font-size: 0.78rem !important;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 0.8rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid rgba(78, 197, 224, 0.15);
}

/* Sidebar description text */
.bslib-sidebar-layout > .sidebar .sidebar-hint {
  font-size: 0.78rem;
  color: rgba(200, 220, 232, 0.55);
  line-height: 1.4;
  margin-bottom: 0.6rem;
}

/* Sidebar hr */
.bslib-sidebar-layout > .sidebar hr {
  border-color: rgba(78, 197, 224, 0.12) !important;
  margin: 0.6rem 0;
}

/* Sidebar buttons */
.bslib-sidebar-layout > .sidebar .btn-default,
.bslib-sidebar-layout > .sidebar .btn.action-button {
  background: linear-gradient(135deg, var(--sea-600) 0%, var(--teal-600) 100%) !important;
  border: 1px solid rgba(78, 197, 224, 0.25) !important;
  color: #fff !important;
  font-weight: 600;
  font-size: 0.82rem;
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  transition: all 0.2s;
  width: 100%;
  text-align: center;
  margin-bottom: 0.35rem;
}
.bslib-sidebar-layout > .sidebar .btn-default:hover,
.bslib-sidebar-layout > .sidebar .btn.action-button:hover {
  background: linear-gradient(135deg, var(--sea-500) 0%, var(--teal-500) 100%) !important;
  border-color: var(--sea-300) !important;
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(13, 49, 88, 0.3);
}

/* Sidebar verbatim output */
.bslib-sidebar-layout > .sidebar pre.shiny-text-output {
  background: rgba(0,0,0,0.25) !important;
  border: 1px solid rgba(78, 197, 224, 0.12) !important;
  color: var(--foam-500) !important;
  border-radius: 6px;
  font-size: 0.78rem;
  padding: 0.5rem 0.7rem;
}

/* Slider tracks */
.bslib-sidebar-layout > .sidebar .irs--shiny .irs-bar {
  background: var(--teal-400) !important;
  border-top-color: var(--teal-400) !important;
  border-bottom-color: var(--teal-400) !important;
}
.bslib-sidebar-layout > .sidebar .irs--shiny .irs-single {
  background: var(--teal-500) !important;
  color: #fff;
}
.bslib-sidebar-layout > .sidebar .irs--shiny .irs-handle {
  border-color: var(--teal-400) !important;
}
.bslib-sidebar-layout > .sidebar .irs--shiny .irs-line {
  background: rgba(255,255,255,0.08) !important;
  border-color: transparent !important;
}
.bslib-sidebar-layout > .sidebar .irs--shiny .irs-min,
.bslib-sidebar-layout > .sidebar .irs--shiny .irs-max {
  color: rgba(200,220,232,0.45) !important;
  background: transparent !important;
}

/* ── Cards ───────────────────────────────────────────────────────────── */
.card {
  border: 1px solid var(--card-border) !important;
  border-radius: 10px !important;
  box-shadow: var(--card-shadow);
  overflow: hidden;
}
.card-header {
  background: linear-gradient(135deg, var(--sea-800) 0%, var(--sea-700) 100%) !important;
  color: #fff !important;
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.01em;
  border-bottom: 1px solid rgba(78, 197, 224, 0.2) !important;
  padding: 0.55rem 1rem;
}
.card-body {
  background: #fff;
}
.card-body pre.shiny-text-output {
  background: var(--sea-50) !important;
  border: 1px solid rgba(20, 100, 160, 0.1);
  border-radius: 6px;
  font-size: 0.82rem;
  color: var(--sea-800);
}

/* ── Map containers ──────────────────────────────────────────────────── */
.shiny-deckgl-container {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(8, 30, 60, 0.12);
  border: 1px solid var(--card-border);
}

/* ── Tab content padding ─────────────────────────────────────────────── */
.tab-content > .tab-pane { padding-top: 0.5rem; }

/* ── Colour-scales tables ────────────────────────────────────────────── */
.colour-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.85rem;
}
.colour-table th {
  background: var(--sea-50);
  color: var(--sea-700);
  font-weight: 600;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.4rem 0.8rem;
  border-bottom: 2px solid var(--sea-200);
}
.colour-table td {
  padding: 0.35rem 0.8rem;
  border-bottom: 1px solid rgba(20,100,160,0.07);
}
.colour-table tr:hover td { background: var(--sea-50); }
.colour-swatch {
  display: inline-block;
  width: 36px;
  height: 22px;
  border-radius: 4px;
  border: 1px solid rgba(0,0,0,0.08);
}
.palette-swatch-block {
  display: inline-block;
  width: 36px;
  height: 26px;
  border-radius: 3px;
  margin-right: 1px;
}

/* ── Export tab buttons ──────────────────────────────────────────────── */
.sidebar .btn-export {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* ── Footer ──────────────────────────────────────────────────────────── */
.marine-footer {
  text-align: center;
  font-size: 0.75rem;
  color: rgba(200,220,232,0.45);
  padding: 0.6rem 0;
  border-top: 1px solid rgba(78,197,224,0.12);
  margin-top: 0.5rem;
}

/* ── Misc ────────────────────────────────────────────────────────────── */
::selection { background: var(--sea-200); color: var(--sea-900); }
"""


def _sidebar_section(icon: str, title: str) -> ui.TagChild:
    """Styled sidebar section header."""
    return ui.h5(
        ui.HTML(f"{icon}&ensp;{title}"),
    )


def _sidebar_hint(text: str) -> ui.TagChild:
    """Subtle descriptive text inside sidebar."""
    return ui.p(text, class_="sidebar-hint")


app_ui = ui.page_navbar(
    head_includes(),

    # ── Tab 1: Interactive Map ──────────────────────────────────────────
    ui.nav_panel(
        "\U0001F30A Interactive Map",
        ui.layout_sidebar(
            ui.sidebar(
                _sidebar_section("\u2693", "Basemap"),
                ui.input_select(
                    "basemap", "Basemap style",
                    choices=list(BASEMAP_CHOICES.keys()),
                ),
                ui.hr(),
                _sidebar_section("\u2728", "Symbology"),
                ui.input_select(
                    "palette", "Port colour palette",
                    choices=list(PALETTE_CHOICES.keys()),
                    selected="Ocean",
                ),
                ui.input_radio_buttons(
                    "color_mode", "Colour mode",
                    choices=["Equal-width bins", "Quantile bins", "Fixed range"],
                    selected="Equal-width bins",
                ),
                ui.hr(),
                _sidebar_section("\u2630", "Layers"),
                ui.input_switch("show_ports", "Ports (scatter)", value=True),
                ui.input_switch("show_mpa", "Marine Protected Areas", value=True),
                ui.input_switch("show_routes", "Shipping routes (arcs)", value=True),
                ui.input_switch("show_paths", "Route paths", value=False),
                ui.input_select(
                    "wms_layer", "EMODnet WMS overlay",
                    choices=WMS_LAYER_CHOICES,
                    selected="emodnet:mean_atlas_land",
                ),
                ui.input_switch("show_heatmap", "Observation heatmap", value=False),
                ui.hr(),
                _sidebar_section("\u2708", "Navigation"),
                ui.input_action_button("fly_klaipeda", "\u2693 Fly to Klaip\u0117da"),
                ui.input_action_button("fly_stockholm", "\u2693 Fly to Stockholm"),
                ui.input_action_button("place_marker", "\U0001F4CD Place drag marker"),
                ui.hr(),
                _sidebar_section("\U0001F4CD", "Drag Marker"),
                ui.output_text_verbatim("drag_info"),
                width=310,
            ),
            map_widget.ui(height="85vh"),
        ),
    ),

    # ── Tab 2: Events & Tooltips ────────────────────────────────────────
    ui.nav_panel(
        "\U0001F4E1 Events & Tooltips",
        ui.layout_sidebar(
            ui.sidebar(
                _sidebar_section("\U0001F4AC", "Tooltip Template"),
                _sidebar_hint(
                    "Edit the HTML template below. Use {field} "
                    "placeholders to interpolate feature properties."
                ),
                ui.input_text_area(
                    "tooltip_template", "HTML template",
                    value=DEFAULT_TOOLTIP_HTML,
                    rows=3,
                ),
                ui.input_text("tooltip_bg", "Background colour", value="#1a1a2e"),
                ui.input_text("tooltip_fg", "Text colour", value="#eeeeee"),
                ui.hr(),
                _sidebar_section("\U0001F4CD", "Drag Marker"),
                ui.input_action_button("events_marker", "\U0001F4CD Place drag marker"),
                ui.output_text_verbatim("events_drag"),
                width=310,
            ),
            events_widget.ui(height="50vh"),
            ui.layout_columns(
                ui.card(
                    ui.card_header("\U0001F5B1\uFE0F Click Event"),
                    ui.output_text_verbatim("click_info"),
                ),
                ui.card(
                    ui.card_header("\U0001F50D Hover Event"),
                    ui.output_text_verbatim("hover_info"),
                ),
                ui.card(
                    ui.card_header("\U0001F30D Current Viewport"),
                    ui.output_text_verbatim("viewport_info"),
                ),
                ui.card(
                    ui.card_header("\U0001F4CD Drag Marker"),
                    ui.output_text_verbatim("events_drag2"),
                ),
                col_widths=[6, 6, 6, 6],
            ),
        ),
    ),

    # ── Tab 3: Colour Scales ────────────────────────────────────────────
    ui.nav_panel(
        "\U0001F3A8 Colour Scales",
        ui.layout_columns(
            ui.card(
                ui.card_header("\U0001F308 color_range() \u2014 Palette Preview"),
                ui.output_ui("palette_preview"),
            ),
            ui.card(
                ui.card_header("\U0001F4CA color_bins() \u2014 Equal-Width Classification"),
                ui.output_ui("bins_preview"),
            ),
            ui.card(
                ui.card_header("\U0001F4C8 color_quantiles() \u2014 Quantile Classification"),
                ui.output_ui("quantiles_preview"),
            ),
            col_widths=[12, 6, 6],
        ),
    ),

    # ── Tab 4: Advanced ─────────────────────────────────────────────────
    ui.nav_panel(
        "\u2699 Advanced",
        ui.layout_sidebar(
            ui.sidebar(
                _sidebar_section("\U0001F4A1", "Lighting Effects"),
                _sidebar_hint(
                    "The map shows 3-D cargo columns. Enable lighting "
                    "to see ambient and point-light shading."
                ),
                ui.input_switch("enable_lighting", "Enable lighting", value=False),
                ui.input_slider(
                    "ambient", "Ambient intensity", 0.0, 2.0, 1.0, step=0.1,
                ),
                ui.input_slider(
                    "point_intensity", "Point light intensity",
                    0.0, 3.0, 1.5, step=0.1,
                ),
                ui.hr(),
                _sidebar_section("\u26A1", "Binary Transport"),
                _sidebar_hint("Push 2,500 random points encoded as numpy binary arrays."),
                ui.input_action_button("push_binary", "\u26A1 Push Binary ScatterplotLayer"),
                ui.hr(),
                _sidebar_section("\U0001F50E", "Data Filter Extension"),
                _sidebar_hint("Filter ports by cargo tonnage using GPU-accelerated DataFilterExtension."),
                ui.input_action_button(
                    "push_filtered", "\U0001F50E Push Filtered Layer",
                ),
                ui.input_slider(
                    "filter_value", "Max cargo filter (Mt)",
                    min=0, max=60, value=60, step=1,
                ),
                width=300,
            ),
            adv_widget.ui(height="55vh"),
            ui.card(
                ui.card_header("\U0001F4DF Status Console"),
                ui.output_text_verbatim("advanced_status"),
            ),
        ),
    ),

    # ── Tab 5: Export & Serialisation ───────────────────────────────────
    ui.nav_panel(
        "\U0001F4E6 Export",
        ui.layout_sidebar(
            ui.sidebar(
                _sidebar_section("\U0001F4E4", "Export Actions"),
                _sidebar_hint("Export the current map state to standalone HTML or JSON format."),
                ui.input_action_button("export_html", "\U0001F310 Export HTML File"),
                ui.input_action_button("export_json", "\U0001F4CB Serialise to JSON"),
                ui.input_action_button("roundtrip_json", "\U0001F504 JSON Round-Trip Test"),
                width=280,
            ),
            ui.card(
                ui.card_header("\U0001F4C4 Output"),
                ui.output_text_verbatim("export_output"),
            ),
        ),
    ),

    title="\U0001F30A shiny_deckgl",
    id="navbar",
    header=ui.tags.style(MARINE_CSS),
)


# ═══════════════════════════════════════════════════════════════════════════
# Server
# ═══════════════════════════════════════════════════════════════════════════

def server(input, output, session: Session):
    # Shared reactive stores
    _main_layers: reactive.Value[list[dict]] = reactive.Value([])
    _adv_layers: reactive.Value[list[dict]] = reactive.Value([])
    _export_log: reactive.Value[str] = reactive.Value("")
    _advanced_log: reactive.Value[str] = reactive.Value("")

    # ===================================================================
    # Tab 1 — Interactive Map
    # ===================================================================

    def _build_main_layers() -> list[dict]:
        """Build the layer stack for the main interactive map."""
        layers: list[dict] = []
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)
        cargo_values = [p["cargo_mt"] for p in PORTS]

        mode = input.color_mode()
        if mode == "Equal-width bins":
            port_colors = color_bins(cargo_values, 6, palette)
        elif mode == "Quantile bins":
            port_colors = color_quantiles(cargo_values, 6, palette)
        else:
            port_colors = color_range(len(PORTS), palette)

        # WMS tile layer (EMODnet bathymetry via OWSLib discovery)
        wms_layer_name = input.wms_layer()
        if wms_layer_name:
            wms_url = (
                f"{EMODNET_WMS_URL}?"
                "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
                "&FORMAT=image/png&TRANSPARENT=true"
                f"&LAYERS={wms_layer_name}"
                "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
                "&BBOX={bbox-epsg-3857}"
            )
            safe_id = wms_layer_name.replace(":", "_")
            layers.append(tile_layer(f"wms-{safe_id}", wms_url))

        # GeoJSON — Marine Protected Areas
        if input.show_mpa():
            layers.append(geojson_layer(
                "mpa-zones", MPA_GEOJSON,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
            ))

        # Heatmap — random observation density
        if input.show_heatmap():
            layers.append(layer(
                "HeatmapLayer", "observation-heat",
                data=_make_heatmap_points(300),
                getPosition="@@d",
                getWeight="@@=d[2]",
                radiusPixels=40, intensity=1.5, threshold=0.1,
            ))

        # Paths — shipping routes as polylines
        if input.show_paths():
            layers.append(layer(
                "PathLayer", "route-paths",
                data=_make_path_data(),
                getPath="@@=d.path",
                getColor="@@=d.color",
                getWidth=3, widthMinPixels=2, pickable=True,
            ))

        # Arcs — connections between ports
        if input.show_routes():
            layers.append(layer(
                "ArcLayer", "port-arcs",
                data=_make_arc_data(),
                getSourcePosition="@@=d.sourcePosition",
                getTargetPosition="@@=d.targetPosition",
                getSourceColor="@@=d.sourceColor",
                getTargetColor="@@=d.targetColor",
                getWidth=2, pickable=True,
            ))

        # Scatterplot — ports with dynamic palette colours
        if input.show_ports():
            port_data = []
            for i, p in enumerate(PORTS):
                port_data.append({
                    "position": [p["lon"], p["lat"]],
                    "name": p["name"],
                    "country": p["country"],
                    "cargo_mt": p["cargo_mt"],
                    "color": port_colors[i],
                    "radius": max(5, p["cargo_mt"] / 3),
                })
            layers.append(scatterplot_layer(
                "ports", port_data,
                getPosition="@@=d.position",
                getFillColor="@@=d.color",
                getRadius="@@=d.radius",
                radiusScale=1000,
                radiusMinPixels=6,
                radiusMaxPixels=30,
                pickable=True,
            ))

        return layers

    # Initial push
    @reactive.Effect
    async def _main_init():
        layers = _build_main_layers()
        _main_layers.set(layers)
        await map_widget.update(session, layers)

    # Reactive rebuild on any control change
    @reactive.Effect
    @reactive.event(
        input.palette, input.color_mode,
        input.show_ports, input.show_mpa, input.show_routes,
        input.show_paths, input.wms_layer, input.show_heatmap,
    )
    async def _main_rebuild():
        layers = _build_main_layers()
        _main_layers.set(layers)
        await map_widget.update(session, layers)

    # Basemap switching
    @reactive.Effect
    @reactive.event(input.basemap)
    async def _switch_basemap():
        style_url = BASEMAP_CHOICES.get(input.basemap(), CARTO_POSITRON)
        await map_widget.set_style(session, style_url)

    # Fly-to transitions
    @reactive.Effect
    @reactive.event(input.fly_klaipeda)
    async def _fly_klaipeda():
        await map_widget.update(
            session, _main_layers.get(),
            view_state={"longitude": 21.13, "latitude": 55.71, "zoom": 10},
            transition_duration=2000,
        )

    @reactive.Effect
    @reactive.event(input.fly_stockholm)
    async def _fly_stockholm():
        await map_widget.update(
            session, _main_layers.get(),
            view_state={"longitude": 18.07, "latitude": 59.33, "zoom": 10},
            transition_duration=2000,
        )

    # Layer visibility toggle (without resending data)
    @reactive.Effect
    @reactive.event(input.show_ports)
    async def _toggle_ports():
        await map_widget.set_layer_visibility(session, {"ports": input.show_ports()})

    @reactive.Effect
    @reactive.event(input.show_mpa)
    async def _toggle_mpa():
        await map_widget.set_layer_visibility(
            session, {"mpa-zones": input.show_mpa()},
        )

    # Drag marker (main map)
    @reactive.Effect
    @reactive.event(input.place_marker)
    async def _place_drag():
        await map_widget.add_drag_marker(session)

    @render.text
    def drag_info():
        pos = input[map_widget.drag_input_id]()
        if pos is None:
            return "Place a marker first…"
        return f"lon: {pos.get('longitude', 0):.6f}\nlat: {pos.get('latitude', 0):.6f}"

    # ===================================================================
    # Tab 2 — Events & Tooltips
    # ===================================================================

    @reactive.Effect
    async def _events_init():
        """Push interactive layers to the events map."""
        port_data = _make_port_data_simple()
        layers = [
            geojson_layer(
                "ev-mpa", MPA_GEOJSON,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
            ),
            layer(
                "ArcLayer", "ev-arcs",
                data=_make_arc_data(),
                getSourcePosition="@@=d.sourcePosition",
                getTargetPosition="@@=d.targetPosition",
                getSourceColor="@@=d.sourceColor",
                getTargetColor="@@=d.targetColor",
                getWidth=2, pickable=True,
            ),
            scatterplot_layer(
                "ev-ports", port_data,
                getPosition="@@=d.position",
                getFillColor=[200, 0, 80, 180],
                radiusMinPixels=8, pickable=True,
            ),
        ]
        await events_widget.update(session, layers)

    # Dynamic tooltip customisation
    @reactive.Effect
    @reactive.event(
        input.tooltip_template, input.tooltip_bg, input.tooltip_fg,
        ignore_init=True,
    )
    async def _update_tooltip():
        template = input.tooltip_template()
        if not template.strip():
            await events_widget.update_tooltip(session, None)
            return
        await events_widget.update_tooltip(session, {
            "html": template,
            "style": {
                "backgroundColor": input.tooltip_bg(),
                "color": input.tooltip_fg(),
                "fontSize": "13px",
            },
        })

    # Drag marker (events map)
    @reactive.Effect
    @reactive.event(input.events_marker)
    async def _events_place_marker():
        await events_widget.add_drag_marker(session)

    @render.text
    def events_drag():
        pos = input[events_widget.drag_input_id]()
        if pos is None:
            return "Place a marker to see position…"
        return f"lon: {pos.get('longitude', 0):.6f}\nlat: {pos.get('latitude', 0):.6f}"

    @render.text
    def events_drag2():
        pos = input[events_widget.drag_input_id]()
        if pos is None:
            return "No drag marker placed."
        return f"lon: {pos.get('longitude', 0):.6f}\nlat: {pos.get('latitude', 0):.6f}"

    # Event readback outputs
    @render.text
    def click_info():
        data = input[events_widget.click_input_id]()
        if data is None:
            return "Click a port or arc on the map…"
        obj_str = json.dumps(data.get("object"), indent=2, default=str)
        return (
            f"Layer:  {data.get('layerId')}\n"
            f"Coords: {data.get('coordinate')}\n"
            f"Object: {obj_str}"
        )

    @render.text
    def hover_info():
        data = input[events_widget.hover_input_id]()
        if data is None:
            return "Hover over a feature…"
        return (
            f"Layer: {data.get('layerId')}\n"
            f"Coords: [{data.get('coordinate', [0, 0])[0]:.4f}, "
            f"{data.get('coordinate', [0, 0])[1]:.4f}]"
        )

    @render.text
    def viewport_info():
        vs = input[events_widget.view_state_input_id]()
        if vs is None:
            return "Pan or zoom the map…"
        return (
            f"Longitude: {vs.get('longitude', 0):.4f}\n"
            f"Latitude:  {vs.get('latitude', 0):.4f}\n"
            f"Zoom:      {vs.get('zoom', 0):.2f}\n"
            f"Pitch:     {vs.get('pitch', 0):.1f}°\n"
            f"Bearing:   {vs.get('bearing', 0):.1f}°"
        )

    # ===================================================================
    # Tab 3 — Colour Scales
    # ===================================================================

    @render.ui
    def palette_preview():
        """Show all 5 palettes with 10-stop color_range swatches."""
        html_parts = []
        for pal_name, pal in PALETTE_CHOICES.items():
            stops = color_range(10, pal)
            swatches = "".join(
                f'<span class="palette-swatch-block" '
                f'style="background:rgb({c[0]},{c[1]},{c[2]});"></span>'
                for c in stops
            )
            html_parts.append(
                f'<div style="margin-bottom:10px;">'
                f'<strong style="font-size:0.9rem;color:#0d3158;">{pal_name}</strong>'
                f'<br/><div style="margin-top:4px;">{swatches}</div></div>'
            )
        return ui.HTML("".join(html_parts))

    @render.ui
    def bins_preview():
        """Show color_bins classification of port cargo values."""
        cargo = [p["cargo_mt"] for p in PORTS]
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)
        colors = color_bins(cargo, 6, palette)
        rows = "".join(
            f'<tr>'
            f'<td>{PORTS[i]["name"]}</td>'
            f'<td>{cargo[i]} Mt</td>'
            f'<td><span class="colour-swatch" '
            f'style="background:rgb({c[0]},{c[1]},{c[2]});"></span></td>'
            f'</tr>'
            for i, c in enumerate(colors)
        )
        return ui.HTML(
            f'<table class="colour-table">'
            f'<tr><th>Port</th><th>Cargo</th><th>Bin Colour</th></tr>'
            f'{rows}</table>'
        )

    @render.ui
    def quantiles_preview():
        """Show color_quantiles classification of port cargo values."""
        cargo = [p["cargo_mt"] for p in PORTS]
        palette = PALETTE_CHOICES.get(input.palette(), PALETTE_OCEAN)
        colors = color_quantiles(cargo, 6, palette)
        rows = "".join(
            f'<tr>'
            f'<td>{PORTS[i]["name"]}</td>'
            f'<td>{cargo[i]} Mt</td>'
            f'<td><span class="colour-swatch" '
            f'style="background:rgb({c[0]},{c[1]},{c[2]});"></span></td>'
            f'</tr>'
            for i, c in enumerate(colors)
        )
        return ui.HTML(
            f'<table class="colour-table">'
            f'<tr><th>Port</th><th>Cargo</th><th>Quantile Colour</th></tr>'
            f'{rows}</table>'
        )

    # ===================================================================
    # Tab 4 — Advanced
    # ===================================================================

    def _adv_base_layers() -> list[dict]:
        """3-D cargo columns — good for demonstrating lighting effects."""
        column_data = [
            {
                "position": [p["lon"], p["lat"]],
                "elevation": p["cargo_mt"] * 200,
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "color": [0, 160, 230, 200],
            }
            for p in PORTS
        ]
        return [
            layer(
                "ColumnLayer", "cargo-columns",
                data=column_data,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor="@@=d.color",
                diskResolution=12,
                radius=15000,
                extruded=True,
                pickable=True,
            ),
        ]

    @reactive.Effect
    async def _adv_init():
        layers = _adv_base_layers()
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)

    # Lighting
    @reactive.Effect
    @reactive.event(input.enable_lighting, input.ambient, input.point_intensity)
    async def _apply_lighting():
        layers = _adv_layers.get()
        effects = None
        if input.enable_lighting():
            effects = [{
                "type": "LightingEffect",
                "ambientLight": {
                    "color": [255, 255, 255],
                    "intensity": input.ambient(),
                },
                "pointLights": [{
                    "color": [255, 255, 220],
                    "intensity": input.point_intensity(),
                    "position": [19.5, 57.0, 80000],
                }],
            }]
            _advanced_log.set(
                f"Lighting ON\n"
                f"  Ambient intensity: {input.ambient()}\n"
                f"  Point light intensity: {input.point_intensity()}\n"
                f"  Point light position: [19.5, 57.0, 80000]"
            )
        else:
            _advanced_log.set("Lighting OFF")
        await adv_widget.update(session, layers, effects=effects)

    # Binary transport (numpy)
    @reactive.Effect
    @reactive.event(input.push_binary)
    async def _push_binary():
        try:
            import numpy as np

            lons = np.linspace(10.0, 30.0, 50, dtype="float32")
            lats = np.linspace(53.0, 62.0, 50, dtype="float32")
            grid_lon, grid_lat = np.meshgrid(lons, lats)
            positions = np.column_stack([
                grid_lon.ravel(), grid_lat.ravel(),
            ]).astype("float32")
            binary_pos = encode_binary_attribute(positions)

            binary_lyr = layer(
                "ScatterplotLayer", "binary-scatter",
                data={"length": len(positions)},
                getPosition=binary_pos,
                getFillColor=[255, 100, 50, 200],
                radiusMinPixels=3, radiusMaxPixels=8, pickable=False,
            )

            layers = [
                lyr for lyr in _adv_layers.get()
                if lyr.get("id") != "binary-scatter"
            ] + [binary_lyr]
            _adv_layers.set(layers)
            await adv_widget.update(session, layers)
            _advanced_log.set(
                f"Binary transport layer pushed!\n"
                f"  Points: {len(positions):,}\n"
                f"  Array dtype: {positions.dtype}\n"
                f"  Array shape: {positions.shape}\n"
                f"  Base64 payload: {len(binary_pos['value']):,} chars"
            )
        except ImportError:
            _advanced_log.set(
                "numpy is not installed.\n"
                "Install with: micromamba install -n shiny numpy"
            )

    # Extensions (DataFilterExtension)
    @reactive.Effect
    @reactive.event(input.push_filtered)
    async def _push_filtered():
        max_cargo = input.filter_value()
        filtered_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "filterValue": p["cargo_mt"],
            }
            for p in PORTS
        ]
        filtered_lyr = layer(
            "ScatterplotLayer", "filtered-ports",
            data=filtered_data,
            getPosition="@@=d.position",
            getFillColor=[255, 200, 0, 220],
            getRadius=8, radiusScale=1000, radiusMinPixels=20, pickable=True,
            extensions=["DataFilterExtension"],
            getFilterValue="@@=d.filterValue",
            filterRange=[0, max_cargo],
            parameters={"depthCompare": "always"},
        )
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") != "filtered-ports"
        ] + [filtered_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        visible = sum(1 for p in PORTS if p["cargo_mt"] <= max_cargo)
        _advanced_log.set(
            f"DataFilterExtension layer pushed!\n"
            f"  Filter range: [0, {max_cargo}] Mt\n"
            f"  Ports visible: {visible}/{len(PORTS)}\n"
            f"  Extension: DataFilterExtension"
        )

    @reactive.Effect
    @reactive.event(input.filter_value)
    async def _update_filter():
        """Re-push the filtered layer when the slider changes (if active)."""
        layers = _adv_layers.get()
        if not any(lyr.get("id") == "filtered-ports" for lyr in layers):
            return
        max_cargo = input.filter_value()
        filtered_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "filterValue": p["cargo_mt"],
            }
            for p in PORTS
        ]
        filtered_lyr = layer(
            "ScatterplotLayer", "filtered-ports",
            data=filtered_data,
            getPosition="@@=d.position",
            getFillColor=[255, 200, 0, 220],
            getRadius=8, radiusScale=1000, radiusMinPixels=20, pickable=True,
            extensions=["DataFilterExtension"],
            getFilterValue="@@=d.filterValue",
            filterRange=[0, max_cargo],
            parameters={"depthCompare": "always"},
        )
        new_layers = [
            lyr for lyr in layers if lyr.get("id") != "filtered-ports"
        ] + [filtered_lyr]
        _adv_layers.set(new_layers)
        await adv_widget.update(session, new_layers)

    @render.text
    def advanced_status():
        return _advanced_log.get() or "Use the controls to test advanced features…"

    # ===================================================================
    # Tab 5 — Export & Serialisation
    # ===================================================================

    @reactive.Effect
    @reactive.event(input.export_html)
    async def _do_export_html():
        layers = _main_layers.get()
        path = os.path.join(tempfile.gettempdir(), "shiny_deckgl_demo_export.html")
        map_widget.to_html(layers, path=path, title="shiny_deckgl Export")
        fsize = os.path.getsize(path)
        _export_log.set(
            f"HTML exported successfully!\n"
            f"Path: {path}\n"
            f"Size: {fsize:,} bytes\n"
            f"Layers: {len(layers)}"
        )
        ui.notification_show(f"Exported to {path}", type="message")

    @reactive.Effect
    @reactive.event(input.export_json)
    async def _do_export_json():
        layers = _main_layers.get()
        spec = map_widget.to_json(layers)
        _export_log.set(
            f"JSON spec ({len(spec):,} chars):\n\n"
            f"{spec[:2000]}{'…' if len(spec) > 2000 else ''}"
        )

    @reactive.Effect
    @reactive.event(input.roundtrip_json)
    async def _do_roundtrip():
        layers = _main_layers.get()
        spec_json = map_widget.to_json(layers)
        w2, layers2 = MapWidget.from_json(spec_json)
        checks = [
            f"Original widget id:     {map_widget.id}",
            f"Restored widget id:     {w2.id}",
            f"IDs match:              {map_widget.id == w2.id}",
            f"Style match:            {map_widget.style == w2.style}",
            f"View state match:       {map_widget.view_state == w2.view_state}",
            f"Tooltip match:          {map_widget.tooltip == w2.tooltip}",
            f"Layer count match:      {len(layers)} == {len(layers2)}",
            f"Layer IDs (original):   {[lyr.get('id') for lyr in layers]}",
            f"Layer IDs (restored):   {[lyr.get('id') for lyr in layers2]}",
            "\n\u2713 JSON round-trip successful!",
        ]
        _export_log.set("\n".join(checks))

    @render.text
    def export_output():
        return _export_log.get() or "Click an export button…"


app = App(app_ui, server)
