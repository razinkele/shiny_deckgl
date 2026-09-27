"""A map re-rendered by render.ui must come back (J2, 2026-09-26 review).

Shiny swaps the output's HTML synchronously, so when the MutationObserver
runs, a new node with the same id is already in the document. The observer
used to skip the dispose because the id still resolved, then skip the init
because mapInstances still held the old map: the new div stayed blank and
the old WebGL context leaked.

Needs chromium and network access for the CDN bundles, like the demo e2e.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18767


@pytest.fixture(scope="module")
def page():
    with running_app("rerender_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#rmap .maplibregl-canvas") as pg:
            yield pg


_STATE = """() => {
  const els = document.querySelectorAll('#rmap');
  const el = els[0];
  return {
    count: els.length,
    canvas: !!(el && el.querySelector('.maplibregl-canvas')),
    marker: el ? el.dataset.probe || null : null,
  };
}"""


def test_rerendered_map_initialises(page):
    # Tag the current node so we can tell the re-rendered one apart.
    page.evaluate("() => { document.getElementById('rmap').dataset.probe = 'old'; }")
    for _ in range(2):  # twice: the second swap exercises a map that was itself re-created
        page.click("#rerender")
        page.wait_for_function(
            "() => { const e = document.getElementById('rmap'); return e && e.dataset.probe !== 'old'; }",
            timeout=15000,
        )
        page.wait_for_selector("#rmap .maplibregl-canvas", timeout=30000)
        state = page.evaluate(_STATE)
        assert state == {"count": 1, "canvas": True, "marker": None}
        page.evaluate("() => { document.getElementById('rmap').dataset.probe = 'old'; }")


def test_update_after_rerender_is_not_dropped(page):
    """The server pushes layers right after each re-render; none may be lost."""
    page.console_log.clear()
    page.click("#rerender")
    page.wait_for_selector("#rmap .maplibregl-canvas", timeout=30000)
    page.wait_for_timeout(1500)
    dropped = [t for t in page.console_log if "not found" in t]
    assert dropped == []


def test_moved_map_is_not_torn_down(page):
    """Detaching and re-attaching a live map node must keep its map."""
    got = page.evaluate("""async () => {
      const el = document.getElementById('rmap');
      const canvas = el.querySelector('.maplibregl-canvas');
      const parent = el.parentNode, next = el.nextSibling;
      parent.removeChild(el);
      parent.insertBefore(el, next);
      await new Promise(r => setTimeout(r, 500));
      return { sameCanvas: el.querySelector('.maplibregl-canvas') === canvas,
               connected: canvas.isConnected };
    }""")
    assert got == {"sameCanvas": True, "connected": True}
