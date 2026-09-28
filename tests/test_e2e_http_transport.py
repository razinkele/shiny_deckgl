"""HTTP transport end to end: a large update is fetched from a session route.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18782

_LAYER = """() => { const i = window.__deckgl_instances && window.__deckgl_instances.hmap;
  const l = i && i.lastLayers && i.lastLayers.find(l => l.id === 'big');
  return l ? { n: l.data.length, radius: l.getRadius } : null; }"""


@pytest.fixture(scope="module")
def page():
    with running_app("http_transport_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#hmap .maplibregl-canvas") as pg:
            pg.wait_for_function(f"() => ({_LAYER})() !== null", timeout=60000)
            yield pg


def test_payload_was_fetched_from_the_session_route(page):
    urls = page.evaluate("() => performance.getEntriesByType('resource').map(e => e.name).filter(u => u.includes('dynamic_route'))")
    assert any("hmap_payload" in u and "&v=1" in u for u in urls), urls
    assert page.evaluate(_LAYER)["n"] == 200_000


def test_patch_sent_behind_the_fetch_applied_after_it(page):
    # Review Focus 5: the partial_update queued during the fetch wins.
    page.wait_for_function(f"() => ({_LAYER})().radius === 999", timeout=10000, polling=200)


def test_later_patch_still_applies(page):
    page.click("#patch")
    seen = []
    deadline = time.time() + 8
    while time.time() < deadline:
        state = page.evaluate("() => { const i = window.__deckgl_instances.hmap; const l = i.lastLayers.find(l => l.id === 'big');"
                              " return [l ? l.getRadius : null, !!i._pendingFetch, (Shiny.shinyapp.$inputValues['patch'] || 0)]; }")
        if not seen or seen[-1] != state:
            seen.append(state)
        if state[0] == 4242:
            break
        page.wait_for_timeout(200)
    assert seen and seen[-1][0] == 4242, (seen, [m for m in page.console_log if "deckgl" in m or "rror" in m][-8:])
