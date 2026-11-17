"""PostProcessEffect modules load from the CDN and actually change pixels.

deck.gl's bundle carries no @luma.gl/effects shader modules, so every
post_process_effect() was skipped with "shader module not available" -- the
demo's Brightness/Contrast switch did nothing. The client now imports the
module file on demand. Needs chromium and network.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18786

EFFECT_READY = """() => { const i = window.__deckgl_instances.pmap;
  const d = i && i.overlay && (i.overlay._deck || i.overlay.deck);
  return !!(d && d.props.effects && d.props.effects.length
            && window.lumaEffects && window.lumaEffects.brightnessContrast); }"""


def _centre_grey(pg) -> float:
    from PIL import Image, ImageStat
    box = pg.locator("#pmap").bounding_box()
    png = pg.screenshot(clip={"x": box["x"] + box["width"] / 2 - 5,
                              "y": box["y"] + box["height"] / 2 - 5,
                              "width": 10, "height": 10})
    return ImageStat.Stat(Image.open(io.BytesIO(png)).convert("L")).mean[0]


def test_brightness_effect_loads_and_brightens():
    with running_app("postprocess_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#pmap") as pg:
            pg.wait_for_function(EFFECT_READY, timeout=30000)
            pg.wait_for_timeout(1500)
            plain = _centre_grey(pg)
            pg.fill("#brightness", "0.5")
            pg.press("#brightness", "Tab")
            pg.wait_for_timeout(2500)
            bright = _centre_grey(pg)
            assert bright > plain + 60, (plain, bright)
            assert not any("not available" in t for t in pg.console_log), pg.console_log
