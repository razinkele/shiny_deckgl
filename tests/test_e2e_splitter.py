"""SplitterWidget builds on deck.gl 9.4, and a bad widget cannot sink an update.

deck.gl 9.4 replaced the SplitterWidget props with a ``viewLayout``; the
helper still sent the 9.3 props, the constructor threw reading
``viewLayout.minSplit``, and because widgets were built inside deck_update
the whole update failed -- the map lost its layers too. The helper now sends
a viewLayout (view specs built into View instances on the client), and a
widget whose constructor throws is skipped with a console error.
Needs chromium and network.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18785

STATE = """() => { const i = window.__deckgl_instances.smap;
  const d = i && i.overlay && (i.overlay._deck || i.overlay.deck);
  return d && d.props.widgets && d.props.layers.length ? {
    widgets: d.props.widgets.map(w => w.id),
    layers: d.props.layers.filter(Boolean).map(l => l.id),
  } : null; }"""


def test_splitter_builds_and_a_broken_widget_is_skipped():
    with running_app("splitter_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#smap") as pg:
            pg.wait_for_function(STATE, timeout=30000)
            state = pg.evaluate(STATE)
            assert state["layers"] == ["pts"]
            assert "splitter-widget" in state["widgets"]
            assert "zoom" in state["widgets"]
            assert "broken" not in state["widgets"]
            assert any("failed to build and was skipped" in t for t in pg.console_log)
            assert not any("deck_update rendering failed" in t for t in pg.console_log)
