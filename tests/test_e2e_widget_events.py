"""Real deck.gl widgets report their state changes as a Shiny input.

Written with shiny_deckgl.testing.MapWidgetController (v1.13.0).
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

from shiny_deckgl.testing import MapWidgetController  # noqa: E402

PORT = 18777


@pytest.fixture(scope="module")
def m():
    with running_app("widget_events_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#wmap .maplibregl-canvas") as pg:
            ctl = MapWidgetController(pg, "wmap")
            ctl.wait_ready(layers=False)
            ctl.expect_widget("TimelineWidget")
            ctl.expect_widget("ToggleWidget")
            pg.wait_for_selector("#wmap .deck-widget-timeline", timeout=30000)
            yield ctl


def test_toggle_click_reaches_the_server(m):
    m.page.click("#wmap .deck-widget-toggle button")
    m.page.wait_for_function("() => document.getElementById('last').innerText === 'tg:change:True'", timeout=5000)


def test_timeline_play_reaches_the_server(m):
    # The play click fires onPlayingChange, then the tick fires onTimeChange;
    # either proves the path, under the spec's id (not deck.gl's 'timeline').
    m.page.click("#wmap .deck-widget-timeline-play")
    m.page.wait_for_function("() => /^tl:(playingChange|timeChange):/.test(document.getElementById('last').innerText)", timeout=5000)
