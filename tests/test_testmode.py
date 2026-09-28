"""Test-mode snapshots (v1.13.0): scrubbed map inputs and exported layer state.

With SHINY_TESTMODE=1 Shiny dumps every input at /session/{id}/dataobj/shinytest.
The widget registers preprocessors so the noisy map inputs diff cleanly, and
exports the layer ids/visibility and style so tests can assert on the map
without a browser. Registration is harmless when test mode is off.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import _FakeSession  # noqa: E402


class _TestmodeSession(_FakeSession):
    def __init__(self):
        super().__init__()
        self.preprocess: dict[str, object] = {}

    def set_snapshot_preprocess(self, id, fn):
        self.preprocess[id] = fn


@pytest.fixture
def exports(monkeypatch):
    import shiny_deckgl.map_widget as mw
    captured: dict[str, object] = {}
    monkeypatch.setattr(mw, "_export_test_values", lambda **kw: captured.update(kw))
    return captured


def test_preprocessors_registered_once_per_session(exports):
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _TestmodeSession()
    asyncio.run(w.update(s, [scatterplot_layer("a", [])]))
    asyncio.run(w.update(s, [scatterplot_layer("a", [])]))
    assert set(s.preprocess) == {"m_view_state", "m_click", "m_hover", "m_query_result", "m_export_result"}
    assert set(exports) == {"m_layers", "m_style"}


def test_view_state_is_rounded_and_bounds_dropped(exports):
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _TestmodeSession()
    asyncio.run(w.update(s, [scatterplot_layer("a", [])]))
    out = s.preprocess["m_view_state"]({"longitude": 21.123456789, "latitude": 55.7, "zoom": 6.00001,
                                        "pitch": 0, "bearing": 0, "bounds": {"sw": [1, 2], "ne": [3, 4]}})
    assert out == {"longitude": 21.1235, "latitude": 55.7, "zoom": 6.0, "pitch": 0, "bearing": 0}
    assert s.preprocess["m_view_state"](None) is None


def test_click_and_hover_keep_object_keys_only(exports):
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _TestmodeSession()
    asyncio.run(w.update(s, [scatterplot_layer("a", [])]))
    out = s.preprocess["m_click"]({"layerId": "a", "coordinate": [21.123456789, 55.7],
                                   "object": {"name": "Klaipėda", "cargo": 12.3, "position": [1, 2]}})
    assert out == {"layerId": "a", "coordinate": [21.1235, 55.7], "object_keys": ["cargo", "name", "position"]}
    assert s.preprocess["m_hover"](None) is None


def test_results_drop_request_ids_and_data_urls(exports):
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _TestmodeSession()
    asyncio.run(w.update(s, [scatterplot_layer("a", [])]))
    q = s.preprocess["m_query_result"]({"requestId": "r1", "features": [{"type": "Feature"}]})
    assert q == {"features": 1}
    e = s.preprocess["m_export_result"]({"requestId": "r1", "dataUrl": "data:image/png;base64,AAAA", "width": 3, "height": 2})
    assert e == {"dataUrl_length": 26, "width": 3, "height": 2}


def test_exports_reflect_the_session_snapshot(exports):
    from shiny_deckgl import MapWidget, scatterplot_layer
    from shiny_deckgl.colors import CARTO_POSITRON
    w, s = MapWidget("m"), _TestmodeSession()
    asyncio.run(w.update(s, [scatterplot_layer("a", []), scatterplot_layer("b", [])]))
    asyncio.run(w.set_layer_visibility(s, {"b": False}))
    assert exports["m_layers"]() == [{"id": "a", "visible": True}, {"id": "b", "visible": False}]
    assert exports["m_style"]() == CARTO_POSITRON
    asyncio.run(w.set_style(s, "https://example.com/x.json"))
    assert exports["m_style"]() == "https://example.com/x.json"


def test_sessions_without_testmode_support_are_fine(exports):
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _FakeSession()          # no set_snapshot_preprocess
    asyncio.run(w.update(s, [scatterplot_layer("a", [])]))
    assert s.messages[-1][0] == "deck_update"
