"""A layer update must not restart a playing trips animation (J6).

startTripsAnimation() carried the elapsed time over only for a *paused*
animation, so every update() / partial_update() -- a trail-length slider, a
speed change -- snapped a running animation back to time 0. A speed change
also has to rescale the time so the trails continue from where they are.

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

PORT = 18772

_TIME = """() => {
  const i = window.__deckgl_instances && window.__deckgl_instances.tmap;
  const l = i && i.overlay._deck.props.layers.find(l => l.id === 'trips');
  return l ? l.props.currentTime : null;
}"""


@pytest.fixture(scope="module")
def page():
    with running_app("trips_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#tmap .maplibregl-canvas") as pg:
            pg.wait_for_function(f"() => ({_TIME})() > 0", timeout=30000)
            yield pg


def _wait_past(page, t):
    page.wait_for_function(f"() => ({_TIME})() > {t}", timeout=15000)


def test_patch_keeps_the_animation_time(page):
    _wait_past(page, 150)
    before = page.evaluate(_TIME)
    page.click("#trail")
    page.wait_for_timeout(400)
    after = page.evaluate(_TIME)
    assert after >= before - 1, f"restarted: {before:.0f} -> {after:.0f}"


def test_speed_change_continues_from_the_same_point(page):
    _wait_past(page, 150)
    before = page.evaluate(_TIME)
    page.click("#speed")
    page.wait_for_timeout(300)
    after = page.evaluate(_TIME)
    # Within ~0.3 s at 10-20 units/s; a restart or a rescaling bug jumps far.
    assert before - 1 <= after <= before + 40, f"{before:.0f} -> {after:.0f}"


def test_reset_still_starts_from_zero(page):
    page.wait_for_timeout(500)
    page.click("#reset")
    page.wait_for_timeout(300)
    assert page.evaluate(_TIME) < 30
