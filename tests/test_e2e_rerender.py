"""A map re-rendered by render.ui must come back (J2, 2026-09-26 review).

Shiny swaps the output's HTML synchronously, so when the MutationObserver
runs, a new node with the same id is already in the document. The observer
used to skip the dispose because the id still resolved, then skip the init
because mapInstances still held the old map: the new div stayed blank and
the old WebGL context leaked.

Needs chromium and network access for the CDN bundles, like the demo e2e.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

PORT = 18767
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def server():
    with socket.socket() as s:
        s.settimeout(1.0)
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            pytest.fail(f"port {PORT} already in use (stale server?)")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT / "tests" / "_apps"), env.get("PYTHONPATH", "")])
    proc = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", "rerender_app:app", "--port", str(PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(ROOT),
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            pytest.fail("rerender app exited early:\n" + (proc.stdout.read() if proc.stdout else ""))
        with socket.socket() as s:
            s.settimeout(1.0)
            if s.connect_ex(("127.0.0.1", PORT)) == 0:
                break
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("rerender app did not start")
    yield proc
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)
    else:
        proc.terminate()
    proc.wait(timeout=15)


@pytest.fixture(scope="module")
def page(server):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        pg = browser.new_page()
        pg.console_log = []
        pg.on("console", lambda msg: pg.console_log.append(msg.text))
        pg.goto(f"http://127.0.0.1:{PORT}/")
        pg.wait_for_selector("#rmap .maplibregl-canvas", timeout=30000)
        yield pg
        browser.close()


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
