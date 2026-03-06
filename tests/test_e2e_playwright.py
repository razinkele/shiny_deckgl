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
from typing import Generator

import pytest

# Skip all tests if playwright is not installed
pytest.importorskip("playwright")

from playwright.sync_api import Page, sync_playwright, Browser


PORT = 18766  # Different port to avoid conflicts
URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def demo_server() -> Generator[subprocess.Popen, None, None]:
    """Start the demo server for the test session."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", "examples/demo.py",
         "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Wait for server to start
    time.sleep(6)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for the test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, demo_server: subprocess.Popen) -> Generator[Page, None, None]:
    """Create a new page for each test."""
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(2)  # Allow Shiny to connect
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

    def test_maplibre_script_loaded(self, page: Page):
        """maplibre-gl script tag should be present."""
        maplibre_script = page.query_selector('script[src*="maplibre-gl"]')
        assert maplibre_script is not None, "maplibre-gl script should be present"

    def test_maplibre_css_loaded(self, page: Page):
        """maplibre-gl CSS should be present."""
        maplibre_css = page.query_selector('link[href*="maplibre-gl"]')
        assert maplibre_css is not None, "maplibre-gl CSS should be present"


class TestMapRendering:
    """Tests that verify the map renders correctly."""

    def test_map_div_exists(self, page: Page):
        """Map container div should exist."""
        map_div = page.query_selector('#demo_map')
        assert map_div is not None, "Map div #demo_map should exist"

    def test_map_div_has_size(self, page: Page):
        """Map div should have non-zero dimensions."""
        map_div = page.query_selector('#demo_map')
        assert map_div is not None
        bbox = map_div.bounding_box()
        assert bbox is not None, "Map div should have a bounding box"
        assert bbox["width"] > 0, "Map div should have positive width"
        assert bbox["height"] > 0, "Map div should have positive height"

    def test_maplibre_canvas_exists(self, page: Page):
        """MapLibre GL canvas should be rendered."""
        canvas = page.query_selector('#demo_map canvas.maplibregl-canvas')
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
        assert "demo_map" in instance_keys, "demo_map instance should exist"


class TestShinyConnection:
    """Tests that verify Shiny is properly connected."""

    def test_shiny_html_class(self, page: Page):
        """HTML element should have Shiny state class."""
        html_classes = page.evaluate("document.documentElement.className")
        # Shiny adds shiny-busy or shiny-idle class
        is_shiny = "shiny-busy" in html_classes or "shiny-idle" in html_classes
        assert is_shiny, f"Expected Shiny class, got: {html_classes}"

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
        map_div = page.query_selector('#demo_map')
        assert map_div is not None
        lon = map_div.get_attribute("data-initial-longitude")
        assert lon is not None, "data-initial-longitude should be set"
        assert float(lon), "longitude should be a valid number"

    def test_initial_latitude_set(self, page: Page):
        """Map div should have data-initial-latitude attribute."""
        map_div = page.query_selector('#demo_map')
        assert map_div is not None
        lat = map_div.get_attribute("data-initial-latitude")
        assert lat is not None, "data-initial-latitude should be set"
        assert float(lat), "latitude should be a valid number"

    def test_style_attribute_set(self, page: Page):
        """Map div should have data-style attribute."""
        map_div = page.query_selector('#demo_map')
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

        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        page.close()
        assert len(errors) == 0, f"JavaScript errors detected: {errors}"
