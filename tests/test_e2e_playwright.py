"""End-to-end Playwright tests for shiny_deckgl demo app.

These tests verify actual browser rendering and functionality.
Run with: pytest tests/test_e2e_playwright.py -v

Requires:
    pip install pytest-playwright
    playwright install chromium
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest

# Skip all tests if playwright is not installed
pytest.importorskip("playwright")

from playwright.sync_api import Page, sync_playwright, Browser


PORT = 18766  # Different port to avoid conflicts
URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def demo_server() -> Generator[subprocess.Popen, None, None]:
    """Start the demo server against the working tree and wait for the port.

    PYTHONPATH is set explicitly: pytest's `pythonpath = ["src"]` only affects
    this process, so without it the subprocess would import whatever
    shiny_deckgl happens to be installed in site-packages and the tests would
    silently exercise the wrong code.
    """
    import os
    import socket

    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")

    # Refuse to run against a listener we did not start: an interrupted run can
    # leave a stale server holding the port, and the readiness check below would
    # happily connect to it, silently testing whatever code it was started with.
    with socket.socket() as probe_sock:
        probe_sock.settimeout(1.0)
        if probe_sock.connect_ex(("127.0.0.1", PORT)) == 0:
            pytest.fail(
                f"port {PORT} is already in use -- most likely a stale demo "
                "server from an interrupted run. Kill it before re-running.")

    proc = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", "shiny_deckgl.app:app",
         "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(root),
    )

    deadline = time.time() + 90
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            pytest.fail(f"demo server exited early (code {proc.returncode}):\n{out[-3000:]}")
        with socket.socket() as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                break
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail(f"demo server did not accept connections on port {PORT} within 90s")

    yield proc
    _stop_server(proc)


def _stop_server(proc: subprocess.Popen) -> None:
    """Stop the server *and its children*.

    `shiny run` spawns uvicorn as a child, and on Windows terminating the
    parent leaves that child holding the port. A stale listener is worse than a
    noisy failure: the next run's port check connects to it and the tests
    silently exercise whatever code the zombie was started with.
    """
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True, check=False)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.fixture(scope="module")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for the test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


#: Console errors seen on the shared demo page, collected from first load.
CONSOLE_ERRORS: list[str] = []


def _open_demo(browser: Browser) -> Page:
    """Open the demo and wait until the first map has actually initialised.

    `wait_until="networkidle"` is wrong here -- a Shiny app holds a websocket
    open, so the network never goes idle. Wait on the app's own state instead.

    Console errors are captured from before navigation so that tests can assert
    on them without opening a second page: two heavyweight WebGL pages at once
    exhausts memory on smaller machines and makes the second load time out.
    """
    page = browser.new_page()
    CONSOLE_ERRORS.clear()
    page.on("console",
            lambda m: CONSOLE_ERRORS.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: CONSOLE_ERRORS.append(f"pageerror: {e}"))
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function(
        "window.__deckgl_instances && window.__deckgl_instances['gallery_map']"
        " && window.__deckgl_instances['gallery_map'].map",
        timeout=90000,
    )
    page.wait_for_timeout(3000)   # let the first deck_update land
    return page


@pytest.fixture(scope="module")
def page(browser: Browser, demo_server: subprocess.Popen) -> Generator[Page, None, None]:
    """One demo page shared by the read-only tests.

    Module-scoped on purpose: the demo is a heavy WebGL app with eleven maps,
    and opening a fresh page per test costs a full re-init each time. These
    tests only read state, so they can share one page. Tests that need a clean
    page (console-error capture) open their own.
    """
    page = _open_demo(browser)
    yield page
    page.close()


class TestDemoAppLoads:
    """Tests that verify the demo app loads correctly."""

    def test_page_has_title(self, page: Page):
        """Page should have a non-empty title."""
        title = page.title()
        assert title, "Page title should not be empty"

    def test_deckgl_script_loaded(self, page: Page):
        """deck.gl script tag should be present."""
        deck_script = page.query_selector('script[src*="deck.gl"]')
        assert deck_script is not None, "deck.gl script tag should be present"

    def test_maplibre_module_config_present(self, page: Page):
        """MapLibre 6 is ESM-only, so it arrives via a JSON config block.

        There is no <script src=...maplibre-gl.js> tag any more; deckgl-init.js
        reads this block and import()s the module URL.
        """
        block = page.query_selector('script#shiny-deckgl-cdn')
        assert block is not None, "CDN config block should be present"
        import json as _json
        cfg = _json.loads(block.inner_text())
        assert cfg["maplibre"].endswith(".mjs")

    def test_maplibre_css_loaded(self, page: Page):
        """maplibre-gl CSS should be present."""
        maplibre_css = page.query_selector('link[href*="maplibre-gl"]')
        assert maplibre_css is not None, "maplibre-gl CSS should be present"


class TestMapRendering:
    """Tests that verify the map renders correctly."""

    def test_map_div_exists(self, page: Page):
        """Map container div should exist."""
        map_div = page.query_selector('#gallery_map')
        assert map_div is not None, "Map div #gallery_map should exist"

    def test_map_div_has_size(self, page: Page):
        """Map div should have non-zero dimensions."""
        map_div = page.query_selector('#gallery_map')
        assert map_div is not None
        bbox = map_div.bounding_box()
        assert bbox is not None, "Map div should have a bounding box"
        assert bbox["width"] > 0, "Map div should have positive width"
        assert bbox["height"] > 0, "Map div should have positive height"

    def test_maplibre_canvas_exists(self, page: Page):
        """MapLibre GL canvas should be rendered."""
        canvas = page.query_selector('#gallery_map canvas.maplibregl-canvas')
        assert canvas is not None, "MapLibre canvas should exist inside map div"


class TestJavaScriptGlobals:
    """Tests that verify JavaScript globals are properly initialized."""

    def test_maplibregl_defined(self, page: Page):
        """window.maplibregl should be defined."""
        has_maplibre = page.evaluate("typeof maplibregl !== 'undefined'")
        assert has_maplibre, "window.maplibregl should be defined"

    def test_deck_defined(self, page: Page):
        """window.deck should be defined."""
        has_deck = page.evaluate("typeof deck !== 'undefined'")
        assert has_deck, "window.deck should be defined"

    def test_deckgl_instances_defined(self, page: Page):
        """window.__deckgl_instances should be defined."""
        has_instances = page.evaluate(
            "typeof window.__deckgl_instances !== 'undefined'"
        )
        assert has_instances, "window.__deckgl_instances should be defined"

    def test_map_instance_created(self, page: Page):
        """At least one map instance should be created."""
        instance_keys = page.evaluate(
            "Object.keys(window.__deckgl_instances || {})"
        )
        assert len(instance_keys) > 0, "At least one map instance should exist"
        assert "gallery_map" in instance_keys, "demo_map instance should exist"


class TestShinyConnection:
    """Tests that verify Shiny is properly connected."""

    def test_shiny_client_is_connected(self, page: Page):
        """The Shiny client reports a live server connection.

        This replaces a check for `shiny-busy`/`shiny-idle` on <html>, which is
        an R-Shiny convention: Shiny for Python renders through bslib and leaves
        documentElement.className empty, so that assertion could never pass.
        """
        state = page.evaluate(
            "({socket: !!(window.Shiny && Shiny.shinyapp && Shiny.shinyapp.$socket),"
            " connected: !!(window.Shiny && Shiny.shinyapp"
            "               && Shiny.shinyapp.isConnected && Shiny.shinyapp.isConnected())})"
        )
        assert state["socket"], "Shiny websocket is not open"
        assert state["connected"], "Shiny client reports it is not connected"

    def test_shiny_app_exists(self, page: Page):
        """Shiny.shinyapp should exist."""
        has_shiny = page.evaluate(
            "typeof Shiny !== 'undefined' && typeof Shiny.shinyapp !== 'undefined'"
        )
        assert has_shiny, "Shiny.shinyapp should be defined"


class TestMapDataAttributes:
    """Tests that verify map data attributes are set correctly."""

    def test_initial_longitude_set(self, page: Page):
        """Map div should have data-initial-longitude attribute."""
        map_div = page.query_selector('#gallery_map')
        assert map_div is not None
        lon = map_div.get_attribute("data-initial-longitude")
        assert lon is not None, "data-initial-longitude should be set"
        assert float(lon), "longitude should be a valid number"

    def test_initial_latitude_set(self, page: Page):
        """Map div should have data-initial-latitude attribute."""
        map_div = page.query_selector('#gallery_map')
        assert map_div is not None
        lat = map_div.get_attribute("data-initial-latitude")
        assert lat is not None, "data-initial-latitude should be set"
        assert float(lat), "latitude should be a valid number"

    def test_style_attribute_set(self, page: Page):
        """Map div should have data-style attribute."""
        map_div = page.query_selector('#gallery_map')
        assert map_div is not None
        style = map_div.get_attribute("data-style")
        assert style is not None, "data-style should be set"
        assert len(style) > 0, "style URL should not be empty"


class TestNoJavaScriptErrors:
    """Tests that verify no JavaScript errors occur."""

    def test_no_page_errors(self, browser: Browser, demo_server: subprocess.Popen):
        """Page should load without JavaScript errors."""
        errors: list[str] = []
        page = browser.new_page()
        page.on("pageerror", lambda err: errors.append(str(err)))

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        page.close()
        assert len(errors) == 0, f"JavaScript errors detected: {errors}"


class TestServedPathRendersRealLayers:
    """End-to-end coverage of the Shiny path with actual layer data.

    The standalone export proves layers draw from disk; this proves the same
    through the live websocket, which is the path deck_update actually uses.
    It is also the only end-to-end check that deck.gl accepts the
    coordinateSystem values the Python side emits (deck.gl 9 wants strings such
    as "lnglat"; the enum used to emit deck.gl 8's integers, which deck.gl
    rejects at draw time with "Invalid coordinateSystem").
    """

    def test_deck_layers_are_present_on_the_gallery_map(self, page: Page):
        layers = page.evaluate("""
          (() => {
            const i = window.__deckgl_instances['gallery_map'];
            if (!i) return null;
            const dk = i.overlay && (i.overlay._deck || i.overlay.deck);
            return (dk && dk.props && dk.props.layers || []).map(l => l.id);
          })()
        """)
        assert layers, "no deck.gl layers reached the gallery map"

    def test_no_invalid_coordinate_system_errors(self, page: Page):
        """deck.gl must accept every coordinateSystem the package emits.

        Reads the errors the shared page collected during load rather than
        opening its own: deck.gl 9 rejects deck.gl 8's integer constants with
        "Invalid coordinateSystem" at draw time.
        """
        bad = [e for e in CONSOLE_ERRORS if "coordinateSystem" in e]
        assert not bad, "deck.gl rejected a coordinateSystem value:\n" + "\n".join(bad[:5])

    def test_layer_coordinate_systems_are_deckgl_9_strings(self, page: Page):
        systems = page.evaluate("""
          (() => {
            const out = new Set();
            Object.values(window.__deckgl_instances).forEach(i => {
              const dk = i.overlay && (i.overlay._deck || i.overlay.deck);
              (dk && dk.props && dk.props.layers || []).forEach(l => {
                if (l.props.coordinateSystem != null)
                  out.add(String(l.props.coordinateSystem));
              });
            });
            return Array.from(out);
          })()
        """)
        for cs in systems:
            assert not cs.strip("-").isdigit(), (
                f"layer still carries a numeric coordinateSystem: {cs!r}")
