"""set_style() replayed into a map that is still loading keeps later layers (J4).

The demo's MapLibre tab re-applied its basemap at start-up. The messages were
deferred while the tab was hidden and replayed when the map was created, so
set_style() ran while the first style was still loading. Without an explicit
diff option MapLibre diffed, and the diff landed after the native layers had
been re-added -- and diffed them away against the bare basemap JSON.

Timing-dependent: this passes on some runs even without the fix; the demo
check in the J4 commit is the stronger evidence. Needs chromium and network.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.browser

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18769


def test_startup_set_style_in_a_hidden_tab_keeps_later_layers():
    with running_app("startup_style_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "a[data-value='Map']") as pg:
            pg.wait_for_timeout(1500)
            pg.click("a[data-value='Map']")
            pg.wait_for_function(
                "() => { const i = window.__deckgl_instances && window.__deckgl_instances.tmap;"
                " return !!(i && i.map.getLayer('pts2-circle')); }", timeout=15000)
            # Stay a moment: a late diff would remove the layer after it appeared.
            pg.wait_for_timeout(3000)
            assert pg.evaluate(
                "() => !!window.__deckgl_instances.tmap.map.getLayer('pts2-circle')")
