"""deck.gl widget themes reach the widget container and follow dark mode.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18788

VAR = ("v => { const c = document.querySelector('#tmap .deck-widget-container');"
       " return c ? c.style.getPropertyValue(v) : null; }")


def _wait_var(pg, name: str, value: str) -> None:
    pg.wait_for_function(
        f"() => {{ const c = document.querySelector('#tmap .deck-widget-container');"
        f" return !!c && c.style.getPropertyValue('{name}') === '{value}'; }}", timeout=15000)


def test_themes_apply_follow_dark_mode_and_clear():
    with running_app("widget_theme_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#tmap") as pg:
            # light-glass: deck.gl's own LightGlassTheme values
            expected = pg.evaluate("() => deck.LightGlassTheme['--button-backdrop-filter']")
            _wait_var(pg, "--button-backdrop-filter", expected)
            # dark mode: the dark theme replaces it
            pg.evaluate("() => document.documentElement.setAttribute('data-bs-theme', 'dark')")
            dark_bg = pg.evaluate("() => deck.DarkTheme['--button-background']")
            _wait_var(pg, "--button-background", dark_bg)
            assert pg.evaluate(VAR, "--button-backdrop-filter") in ("", "unset",
                pg.evaluate("() => deck.DarkTheme['--button-backdrop-filter'] || ''"))
            # back to light, then cleared from the server
            pg.evaluate("() => document.documentElement.setAttribute('data-bs-theme', 'light')")
            _wait_var(pg, "--button-backdrop-filter", expected)
            assert pg.evaluate("() => document.getElementById('tmap').dataset.widgetTheme") \
                == '"light-glass"'
            pg.click("#plain")
            _wait_var(pg, "--button-backdrop-filter", "")
            assert pg.evaluate(VAR, "--button-background") == ""
            # Recorded on the element too, so a context-loss rebuild keeps it.
            assert pg.evaluate("() => document.getElementById('tmap').dataset.widgetTheme") is None
