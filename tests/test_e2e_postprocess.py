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


OVERTAKE_PORT = 18787

OVERTAKE_STATE = """() => { const i = window.__deckgl_instances.omap;
  const d = i && i.overlay && (i.overlay._deck || i.overlay.deck);
  return d && d.props.layers.length ? {
    layers: d.props.layers.filter(Boolean).map(l => l.id),
    effects: (d.props.effects || []).length,
  } : null; }"""


def test_an_overtaken_update_keeps_its_effects():
    """A newer layers-only update must not drop the effects of the one it overtook.

    The first update waits for its effect module; the second one, sent at once,
    claims a newer generation, so the first is dropped as stale when it resumes.
    Its effects used to go with it although the second update (effects omitted)
    keeps effects.
    """
    with running_app("postprocess_overtake_app", OVERTAKE_PORT):
        with browser_page(f"http://127.0.0.1:{OVERTAKE_PORT}/", "#omap") as pg:
            pg.wait_for_function(OVERTAKE_STATE, timeout=30000)   # map is up
            pg.click("#go")
            pg.wait_for_function(
                OVERTAKE_STATE.replace("return d &&", "return d && d.props.layers.some("
                                       "l => l && l.id === 'second') &&"), timeout=30000)
            pg.wait_for_function(
                "() => window.lumaEffects && window.lumaEffects.vignette", timeout=30000)
            pg.wait_for_timeout(2500)
            state = pg.evaluate(OVERTAKE_STATE)
            assert state["layers"] == ["second"]
            assert state["effects"] == 1, state
