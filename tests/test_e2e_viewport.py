"""on_viewport_change must debounce without blocking the server (P7).

The debounce awaited asyncio.sleep() inside a reactive effect. Shiny runs
effects under its global reactive lock, so no newer call could start during
the sleep: it never debounced anything, and each camera move stalled every
session for debounce_ms.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18771


@pytest.fixture(scope="module")
def page():
    with running_app("viewport_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#vmap .maplibregl-canvas") as pg:
            pg.wait_for_function("() => /calls=[1-9]/.test(document.getElementById('calls').innerText)",
                                 timeout=30000)
            # A real viewport ends the start-up polling (one retry a second
            # until the map reports its view), which would add stray calls.
            _move(pg, 21.1)
            pg.wait_for_timeout(2000)
            yield pg


def _calls(page) -> int:
    return int(re.search(r"calls=(\d+)", page.inner_text("#calls")).group(1))


def _move(page, lon):
    page.evaluate(
        "(lon) => Shiny.setInputValue('vmap_view_state', {longitude: lon, latitude: 55.7,"
        " zoom: 6, pitch: 0, bearing: 0, bounds: {sw: [lon - 1, 55], ne: [lon + 1, 56]}},"
        " {priority: 'event'})", lon)


def test_a_burst_of_moves_loads_once(page):
    before = _calls(page)
    for i in range(6):
        _move(page, 21.0 + i * 0.1)
        page.wait_for_timeout(60)
    page.wait_for_timeout(1500)
    assert _calls(page) - before == 1


def test_other_inputs_are_not_blocked_while_debouncing(page):
    n = int(page.inner_text("#pong").split()[-1])
    _move(page, 22.0)
    t0 = time.perf_counter()
    page.click("#ping")
    page.wait_for_function(f"() => document.getElementById('pong').innerText === 'pong {n + 1}'",
                           timeout=5000)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.4, f"ping took {elapsed:.2f}s during a 0.5 s debounce"
    page.wait_for_timeout(1000)


def test_dependency_read_in_the_loader_still_refires_it(page):
    before = _calls(page)
    page.evaluate("() => { const el = document.getElementById('dep'); el.value = '7';"
                  " el.dispatchEvent(new Event('change', {bubbles: true})); }")
    page.wait_for_function("() => /dep=7/.test(document.getElementById('calls').innerText)",
                           timeout=5000)
    assert _calls(page) == before + 1
