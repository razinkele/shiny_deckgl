"""MapWidget.enable_bookmarking(): camera, style and layer visibility survive a bookmark.

Shiny serialises every input into the bookmark; the widget excludes its
transient ones, stores its per-session layer visibility and style in
state.values on bookmark, and on restore flies to the saved view_state input,
swaps the style and re-applies the visibility.
"""
from __future__ import annotations

import asyncio
import sys
import types
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import _FakeSession  # noqa: E402


class _FakeBookmark:
    def __init__(self, store="url"):
        self.exclude: list[str] = []
        self.store = store
        self._on_bookmark = []
        self._on_restored = []

    def on_bookmark(self, fn):
        self._on_bookmark.append(fn)

    def on_restored(self, fn):
        self._on_restored.append(fn)


class _BookmarkSession(_FakeSession):
    def __init__(self, store="url"):
        super().__init__()
        self.bookmark = _FakeBookmark(store)


def _state(**kw):
    st = types.SimpleNamespace(input={}, values={})
    for k, v in kw.items():
        setattr(st, k, v)
    return st


async def _fire(fns, state):
    for fn in fns:
        out = fn(state)
        if asyncio.iscoroutine(out):
            await out


def test_transient_inputs_are_excluded_and_hooks_registered():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _BookmarkSession()
    w.enable_bookmarking(s)
    for suffix in ("_click", "_hover", "_map_click", "_map_contextmenu", "_query_result",
                   "_export_result", "_has_image", "_widget_event", "_reconnected", "_dark_mode", "_drag"):
        assert "m" + suffix in s.bookmark.exclude, suffix
    assert "m_view_state" not in s.bookmark.exclude
    assert len(s.bookmark._on_bookmark) == 1 and len(s.bookmark._on_restored) == 1


def test_on_bookmark_stores_visibility_and_style():
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _BookmarkSession()
    w.enable_bookmarking(s)
    asyncio.run(w.update(s, [scatterplot_layer("a", []), scatterplot_layer("b", [])]))
    asyncio.run(w.set_layer_visibility(s, {"b": False}))
    asyncio.run(w.set_style(s, "https://example.com/dark.json"))
    st = _state()
    asyncio.run(_fire(s.bookmark._on_bookmark, st))
    assert st.values["m"] == {"visible": {"a": True, "b": False}, "style": "https://example.com/dark.json"}


def test_on_restored_flies_sets_style_and_visibility():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _BookmarkSession()
    w.enable_bookmarking(s)
    st = _state(
        input={"m_view_state": {"longitude": 21.1, "latitude": 55.7, "zoom": 7.5, "pitch": 30, "bearing": 10}},
        values={"m": {"visible": {"a": True, "b": False}, "style": "https://example.com/dark.json"}},
    )
    asyncio.run(_fire(s.bookmark._on_restored, st))
    handlers = [h for h, _ in s.messages]
    assert handlers == ["deck_set_style", "deck_fly_to", "deck_layer_visibility"]
    fly = dict(s.messages[1][1])
    assert fly["viewState"]["longitude"] == 21.1 and fly["viewState"]["zoom"] == 7.5
    assert s.messages[2][1]["visibility"] == {"a": True, "b": False}
    assert w.current_style(s) == "https://example.com/dark.json"


def test_on_restored_without_map_state_is_a_noop():
    # Review Focus 4: first visit, or the map was added after the bookmark.
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _BookmarkSession()
    w.enable_bookmarking(s)
    asyncio.run(_fire(s.bookmark._on_restored, _state(input={"other": 1}, values={})))
    assert s.messages == []


def test_unchanged_style_is_not_reapplied():
    from shiny_deckgl import MapWidget
    from shiny_deckgl.colors import CARTO_POSITRON
    w, s = MapWidget("m"), _BookmarkSession()
    w.enable_bookmarking(s)
    asyncio.run(_fire(s.bookmark._on_restored, _state(values={"m": {"visible": {}, "style": CARTO_POSITRON}})))
    assert [h for h, _ in s.messages] == []


def test_options_disable_parts():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _BookmarkSession()
    w.enable_bookmarking(s, view=False, layers=False, style=False)
    st = _state(input={"m_view_state": {"longitude": 1, "latitude": 2, "zoom": 3}},
                values={"m": {"visible": {"a": False}, "style": "X"}})
    asyncio.run(_fire(s.bookmark._on_restored, st))
    assert s.messages == []
    assert "m_view_state" in s.bookmark.exclude       # view=False: don't even store it


def test_disabled_store_warns():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _BookmarkSession(store="disable")
    with pytest.warns(UserWarning, match="bookmark_store"):
        w.enable_bookmarking(s)


def test_old_shiny_is_refused(monkeypatch):
    import shiny_deckgl.map_widget as mw
    from shiny_deckgl import MapWidget
    monkeypatch.setattr(mw, "_shiny_version", lambda: (1, 6, 3))
    with pytest.raises(RuntimeError, match="1.6.4"):
        MapWidget("m").enable_bookmarking(_BookmarkSession())


def test_session_without_bookmark_support_is_refused():
    from shiny_deckgl import MapWidget
    with pytest.raises(RuntimeError, match="bookmark"):
        MapWidget("m").enable_bookmarking(_FakeSession())
