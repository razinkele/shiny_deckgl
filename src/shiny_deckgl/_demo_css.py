"""Marine-themed CSS and small UI helpers for the demo app."""

from __future__ import annotations

from shiny import ui

# ---------------------------------------------------------------------------
# Marine-themed CSS
# ---------------------------------------------------------------------------

MARINE_CSS = """
/* -- Google Font --------------------------------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* -- Design tokens ------------------------------------------------------- */
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

/* -- Base ---------------------------------------------------------------- */
body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  background: var(--sea-50) !important;
  color: #1c2d3f;
}

/* -- Navbar -------------------------------------------------------------- */
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

/* -- Sidebar ------------------------------------------------------------- */
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

/* -- Cards --------------------------------------------------------------- */
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

/* -- Map containers ------------------------------------------------------ */
.shiny-deckgl-container {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(8, 30, 60, 0.12);
  border: 1px solid var(--card-border);
}

/* -- Tab content padding ------------------------------------------------- */
.tab-content > .tab-pane { padding-top: 0.5rem; }

/* -- Colour-scales tables ------------------------------------------------ */
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

/* -- Footer -------------------------------------------------------------- */
.marine-footer {
  text-align: center;
  font-size: 0.75rem;
  color: rgba(200,220,232,0.45);
  padding: 0.6rem 0;
  border-top: 1px solid rgba(78,197,224,0.12);
  margin-top: 0.5rem;
}

/* -- Misc ---------------------------------------------------------------- */
::selection { background: var(--sea-200); color: var(--sea-900); }

/* -- Sidebar accordions -------------------------------------------------- */
.bslib-sidebar-layout > .sidebar .accordion {
  --bs-accordion-bg: transparent;
  --bs-accordion-border-color: rgba(78, 197, 224, 0.15);
  --bs-accordion-btn-padding-x: 0.5rem;
  --bs-accordion-btn-padding-y: 0.5rem;
  --bs-accordion-body-padding-x: 0.3rem;
  --bs-accordion-body-padding-y: 0.4rem;
  border: none !important;
  background: transparent !important;
}
.bslib-sidebar-layout > .sidebar .accordion-item {
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid rgba(78, 197, 224, 0.12) !important;
}
.bslib-sidebar-layout > .sidebar .accordion-button {
  background: transparent !important;
  color: var(--sea-300) !important;
  font-size: 0.78rem !important;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.55rem 0.5rem !important;
  box-shadow: none !important;
}
.bslib-sidebar-layout > .sidebar .accordion-button::after {
  filter: invert(0.7) sepia(1) saturate(3) hue-rotate(160deg);
  width: 0.9rem;
  height: 0.9rem;
}
.bslib-sidebar-layout > .sidebar .accordion-button:not(.collapsed) {
  color: var(--sea-200) !important;
  background: rgba(255,255,255,0.03) !important;
}
.bslib-sidebar-layout > .sidebar .accordion-body {
  background: transparent !important;
  padding: 0.3rem 0.3rem 0.5rem !important;
}
"""


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------

def sidebar_section(icon: str, title: str) -> ui.TagChild:
    """Styled sidebar section header."""
    return ui.h5(ui.HTML(f"{icon}&ensp;{title}"))


def sidebar_hint(text: str) -> ui.TagChild:
    """Subtle descriptive text inside sidebar."""
    return ui.p(text, class_="sidebar-hint")


def about_row(lib: str, ver: str) -> ui.Tag:
    """One ``<tr>`` for the About version table in the navbar menu."""
    return ui.tags.tr(
        ui.tags.td(
            lib,
            style="padding:3px 12px 3px 0;color:#666;white-space:nowrap;",
        ),
        ui.tags.td(
            ui.tags.code(ver),
            style="padding:3px 0;font-weight:600;",
        ),
    )
