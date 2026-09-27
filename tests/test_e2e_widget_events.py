"""Real deck.gl widgets report their state changes as a Shiny input.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18777


@pytest.fixture(scope="module")
def page():
    with running_app("widget_events_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#wmap .maplibregl-canvas") as pg:
            pg.wait_for_selector("#wmap .deck-widget-timeline", timeout=30000)
            yield pg


def test_toggle_click_reaches_the_server(page):
    page.click("#wmap .deck-widget-toggle button")
    page.wait_for_function("() => document.getElementById('last').innerText === 'tg:change:True'", timeout=5000)


def test_timeline_play_reaches_the_server(page):
    # The play click fires onPlayingChange, then the tick fires onTimeChange;
    # either proves the path, under the spec's id (not deck.gl's 'timeline').
    page.click("#wmap .deck-widget-timeline-play")
    page.wait_for_function("() => /^tl:(playingChange|timeChange):/.test(document.getElementById('last').innerText)", timeout=5000)
