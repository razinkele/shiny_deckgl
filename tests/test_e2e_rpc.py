"""MapWidget.rpc() end to end: the browser answers a request awaited in an
extended_task (any Shiny) or in a plain effect (Shiny >= 1.9).

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18779


@pytest.fixture(scope="module")
def page():
    with running_app("rpc_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#rmap .maplibregl-canvas") as pg:
            pg.wait_for_function(
                "() => window.__deckgl_instances && window.__deckgl_instances.rmap"
                " && window.__deckgl_instances.rmap.overlay._deck.props.layers.length === 1",
                timeout=30000)
            yield pg


def test_view_state_and_features_come_back(page):
    page.click("#ask")
    page.wait_for_function("() => document.getElementById('answer').innerText.startsWith('zoom=')", timeout=10000)
    text = page.inner_text("#answer")
    assert text.startswith("zoom=6.0 bounds=True features="), text
    assert int(re.search(r"features=(\d+)", text).group(1)) >= 0


@pytest.mark.skipif(
    not hasattr(__import__("shiny").Session, "run_once_when_idle"),
    reason="awaiting rpc() inside a plain effect needs Shiny >= 1.9",
)
def test_rpc_awaited_in_a_plain_effect_on_shiny_1_9(page):
    page.click("#ask_effect")
    page.wait_for_function("() => document.getElementById('effect_out').innerText.startsWith('effect ')", timeout=10000)
    assert page.inner_text("#effect_out") == "effect zoom=6.0"


def test_image_bytes_come_back(page):
    page.click("#shot")
    page.wait_for_function("() => /^bytes=\\d+$/.test(document.getElementById('shot_size').innerText)", timeout=15000)
    assert int(page.inner_text("#shot_size").split("=")[1]) > 1000
