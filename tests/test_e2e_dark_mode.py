"""Dark mode end to end: the Bootstrap switch swaps the basemap and darkens the widgets.

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

PORT = 18780

_STYLE_URL = "() => window.__deckgl_instances.dmap.currentStyle"


@pytest.fixture(scope="module")
def page():
    with running_app("dark_mode_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#dmap .maplibregl-canvas") as pg:
            pg.wait_for_function("() => window.__deckgl_instances && window.__deckgl_instances.dmap"
                                 " && window.__deckgl_instances.dmap.overlay._deck.props.layers.length === 1",
                                 timeout=30000)
            yield pg


def test_starts_light(page):
    assert "positron" in page.evaluate(_STYLE_URL)
    assert not page.evaluate("() => document.getElementById('dmap').classList.contains('deckgl-dark')")


def test_switch_to_dark_swaps_style_widgets_and_reports(page):
    page.evaluate("() => document.documentElement.setAttribute('data-bs-theme', 'dark')")
    page.wait_for_function("() => /dark-matter/.test(window.__deckgl_instances.dmap.currentStyle)", timeout=5000)
    assert page.evaluate("() => document.getElementById('dmap').classList.contains('deckgl-dark')")
    page.wait_for_function("() => document.getElementById('reported').innerText.startsWith('dark=True')", timeout=5000)
    assert "dark-matter" in page.inner_text("#reported")
    # the map itself is on the dark style once it has loaded
    page.wait_for_function("() => { const s = window.__deckgl_instances.dmap.map.getStyle();"
                           " return s && /dark/i.test(s.name || ''); }", timeout=20000)
    # deck widgets pick up the dark variables from the container
    bg = page.evaluate("() => getComputedStyle(document.querySelector('#dmap .deck-widget-container'))"
                       ".getPropertyValue('--button-background').trim()")
    assert bg.startswith("rgba(24, 26, 30")


def test_switch_back_to_light(page):
    page.evaluate("() => document.documentElement.setAttribute('data-bs-theme', 'light')")
    page.wait_for_function("() => /positron/.test(window.__deckgl_instances.dmap.currentStyle)", timeout=5000)
    assert not page.evaluate("() => document.getElementById('dmap').classList.contains('deckgl-dark')")
    page.wait_for_function("() => document.getElementById('reported').innerText.startsWith('dark=False')", timeout=5000)
