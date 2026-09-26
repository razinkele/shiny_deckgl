"""One frame loop per map (shared frame loop, part B).

The trips loop and the @@animate loop each set the whole layer list from
their own clone: a map using both alternated between frames with head icons
and trips time and frames without. A paused animation also lost its time and
head icons whenever anything else re-rendered, and binary layers were decoded
again on every frame.

Needs chromium and network access for the CDN bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18773

# Record the layers deck.gl is given on each of the next N frames.
_SAMPLE = """async (n) => {
  const i = window.__deckgl_instances.fmap, dk = i.overlay._deck;
  const frames = [];
  for (let k = 0; k < n; k++) {
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const ls = dk.props.layers;
    const by = id => ls.find(l => l.id === id);
    frames.push({
      time: by('trips') ? by('trips').props.currentTime : null,
      heads: !!by('trips_heads'),
      r: by('spin') ? by('spin').props.radiusScale : null,
      binData: by('bin') ? by('bin').props.data : null,
    });
  }
  const sameData = frames.every(f => f.binData && f.binData === frames[0].binData);
  return { frames: frames.map(f => ({ time: f.time, heads: f.heads, r: f.r })), sameData };
}"""


@pytest.fixture(scope="module")
def page():
    with running_app("frame_loop_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#fmap .maplibregl-canvas") as pg:
            # Wait until heads are drawn (the PNG atlas has loaded).
            pg.wait_for_function(
                "() => { const i = window.__deckgl_instances && window.__deckgl_instances.fmap;"
                " return !!(i && i.overlay._deck.props.layers.some(l => l.id === 'trips_heads')); }",
                timeout=30000)
            yield pg


def test_every_frame_has_trips_time_heads_and_the_animated_value(page):
    """Regression guard: this also passed with the two old loops (they did
    not collide in the sampled frames), so it is not evidence of the fix;
    the next two tests are."""
    got = page.evaluate(_SAMPLE, 12)
    frames = got["frames"]
    assert all(f["heads"] for f in frames), frames
    times = [f["time"] for f in frames]
    assert all(t is not None for t in times) and times == sorted(times) and times[-1] > times[0], times
    rs = [f["r"] for f in frames]
    assert rs == sorted(rs) and rs[-1] > rs[0], rs


def test_binary_data_is_not_rebuilt_per_frame(page):
    assert page.evaluate(_SAMPLE, 6)["sameData"] is True


def test_paused_frame_survives_a_rerender(page):
    page.click("#pause")
    page.wait_for_timeout(500)
    before = page.evaluate(_SAMPLE, 3)["frames"][-1]
    page.click("#trail")
    page.wait_for_timeout(800)
    after = page.evaluate(_SAMPLE, 3)["frames"]
    assert all(f["heads"] for f in after), after
    assert all(abs(f["time"] - before["time"]) < 1e-6 for f in after), (before, after)
    # The @@animate layer keeps animating while the trips are paused.
    assert after[-1]["r"] > before["r"]
