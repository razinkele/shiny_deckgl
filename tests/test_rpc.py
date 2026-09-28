"""MapWidget.rpc(): a request the browser answers through Shiny.shinyapp.makeRequest().

The runtime replies to a ``deck_request`` by calling the message handler the
widget registered with ``session.set_message_handler("<id>_rpc_reply", fn)``.
The session loop awaits the reactive flush inline, so awaiting a reply inside a
plain reactive effect would deadlock; ``rpc()`` refuses that call site and
documents ``reactive.extended_task``.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import _FakeSession  # noqa: E402


class _RpcSession(_FakeSession):
    """Answers every deck_request through the handler the widget registered."""

    def __init__(self, answers=None, *, reply=True):
        super().__init__()
        self.handlers: dict[str, object] = {}
        self.answers = answers or {}
        self.reply = reply

    def set_message_handler(self, name, handler):
        self.handlers[name] = handler
        return name

    async def send_custom_message(self, handler, payload):
        await super().send_custom_message(handler, payload)
        if handler == "deck_request" and self.reply:
            fn = self.handlers[payload["id"] + "_rpc_reply"]
            ans = self.answers.get(payload["method"])
            if isinstance(ans, Exception):
                await fn(payload["requestId"], None, str(ans))
            else:
                await fn(payload["requestId"], ans, None)


def _requests(s):
    return [p for h, p in s.messages if h == "deck_request"]


def test_rpc_round_trip_and_handler_registered_once():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RpcSession({"getViewState": {"zoom": 4}})
    assert asyncio.run(w.get_view_state(s)) == {"zoom": 4}
    assert asyncio.run(w.get_view_state(s)) == {"zoom": 4}
    assert list(s.handlers) == ["m_rpc_reply"]
    ids = [p["requestId"] for p in _requests(s)]
    assert len(ids) == 2 and ids[0] != ids[1]
    assert _requests(s)[0]["method"] == "getViewState"


def test_error_reply_raises():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RpcSession({"exportImage": RuntimeError("no canvas")})
    with pytest.raises(RuntimeError, match="no canvas"):
        asyncio.run(w.get_image(s))


def test_timeout_when_nothing_replies():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RpcSession(reply=False)
    with pytest.raises(TimeoutError, match="extended_task"):
        asyncio.run(w.rpc(s, "getViewState", timeout=0.05))


def test_stale_reply_is_ignored():
    # Review Focus 2: a reply for an id that timed out (or never existed).
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RpcSession(reply=False)
    with pytest.raises(TimeoutError):
        asyncio.run(w.rpc(s, "getViewState", timeout=0.01))
    asyncio.run(s.handlers["m_rpc_reply"]("nope", {"zoom": 1}, None))   # no exception


def test_rpc_inside_a_reactive_context_is_refused():
    # Review Focus 1: the session loop awaits the flush, so this would deadlock.
    from shiny import reactive
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RpcSession({"getViewState": {}})

    async def inside():
        with reactive.isolate():
            await w.get_view_state(s)

    with pytest.raises(RuntimeError, match="extended_task"):
        asyncio.run(inside())
    assert not _requests(s)


def test_rpc_inside_an_extended_task_context_is_allowed():
    from shiny.reactive._extended_task import DenialContext
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RpcSession({"getViewState": {"zoom": 2}})

    async def inside():
        with DenialContext()():
            return await w.get_view_state(s)

    assert asyncio.run(inside()) == {"zoom": 2}


def test_get_image_decodes_the_data_url():
    from shiny_deckgl import MapWidget
    s = _RpcSession({"exportImage": {"dataUrl": "data:image/png;base64,aGVsbG8=", "width": 2, "height": 1}})
    assert asyncio.run(MapWidget("m").get_image(s)) == b"hello"
    req = _requests(s)[0]
    assert req["params"] == {"format": "png", "quality": 0.92}


def test_get_features_builds_the_params():
    from shiny_deckgl import MapWidget
    s = _RpcSession({"queryFeatures": [{"type": "Feature"}]})
    out = asyncio.run(MapWidget("m").get_features(s, lnglat=[21.1, 55.7], layers=["ports"]))
    assert out == [{"type": "Feature"}]
    req = _requests(s)[0]
    assert req["method"] == "queryFeatures"
    assert req["params"] == {"lnglat": [21.1, 55.7], "layers": ["ports"]}


def test_image_loaded():
    from shiny_deckgl import MapWidget
    s = _RpcSession({"hasImage": True})
    assert asyncio.run(MapWidget("m").image_loaded(s, "anchor")) is True
    assert _requests(s)[0]["params"] == {"imageId": "anchor"}


def test_rpc_state_is_per_session():
    from shiny_deckgl import MapWidget
    w = MapWidget("m")
    s1, s2 = _RpcSession({"hasImage": True}), _RpcSession({"hasImage": False})
    assert asyncio.run(w.image_loaded(s1, "x")) is True
    assert asyncio.run(w.image_loaded(s2, "x")) is False
    assert list(s1.handlers) == ["m_rpc_reply"] and list(s2.handlers) == ["m_rpc_reply"]
