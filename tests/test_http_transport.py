"""update(transport=): large payloads go over HTTP via session.dynamic_route().

The websocket message then carries {id, url, seq, bytes} and the runtime
fetches the JSON; the route serves this session's latest payload.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import _FakeSession  # noqa: E402


class _RouteSession(_FakeSession):
    def __init__(self):
        super().__init__()
        self.routes: dict[str, object] = {}
        self.registrations = 0

    def dynamic_route(self, name, handler):
        self.routes[name] = handler
        self.registrations += 1
        return f"session/S/dynamic_route/{name}?nonce=abc"


def _served(s, name="m_payload"):
    resp = s.routes[name](object())          # starlette Response; body is bytes
    return json.loads(resp.body), resp.media_type


def _big_layers(n=40000):
    from shiny_deckgl import scatterplot_layer
    return [scatterplot_layer("big", [[21.0 + i * 1e-5, 55.0 + i * 1e-5] for i in range(n)], getPosition="@@d")]


def test_auto_uses_websocket_for_small_payloads():
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _RouteSession()
    asyncio.run(w.update(s, [scatterplot_layer("a", [[1, 2]])]))
    assert s.messages[-1][0] == "deck_update" and "layers" in s.messages[-1][1]
    assert s.registrations == 0


def test_auto_switches_to_http_above_the_threshold():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RouteSession()
    w.http_transport_threshold = 500_000            # the 40k-point layer is ~0.8 MB
    asyncio.run(w.update(s, _big_layers(), picking_radius=3))
    handler, msg = s.messages[-1]
    assert handler == "deck_update"
    assert set(msg) == {"id", "url", "seq", "bytes"}
    assert msg["url"].startswith("session/S/dynamic_route/m_payload?nonce=abc&v=")
    assert msg["bytes"] > w.http_transport_threshold
    body, media = _served(s)
    assert media == "application/json"
    assert body["id"] == "m" and body["layers"][0]["id"] == "big" and body["pickingRadius"] == 3
    assert len(body["layers"][0]["data"]) == 40000


def test_route_is_registered_once_and_serves_the_latest_payload():
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _RouteSession()
    asyncio.run(w.update(s, _big_layers(), transport="http"))
    asyncio.run(w.update(s, [scatterplot_layer("small", [[1, 2]])], transport="http"))
    assert s.registrations == 1
    seqs = [p["seq"] for h, p in s.messages if h == "deck_update"]
    assert seqs == [1, 2]
    body, _ = _served(s)
    assert [lyr["id"] for lyr in body["layers"]] == ["small"]


def test_explicit_ws_never_registers_a_route():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RouteSession()
    asyncio.run(w.update(s, _big_layers(), transport="ws"))
    assert s.registrations == 0 and "layers" in s.messages[-1][1]


def test_resend_uses_the_same_transport_decision():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _RouteSession()
    w.http_transport_threshold = 500_000
    asyncio.run(w.update(s, _big_layers()))
    n = len(s.messages)
    assert asyncio.run(w.resend_last_update(s)) is True
    assert len(s.messages) == n + 1 and "url" in s.messages[-1][1]
    assert s.messages[-1][1]["seq"] == 2
    body, _ = _served(s)
    assert body["layers"][0]["id"] == "big"


def test_threshold_is_configurable_per_widget():
    from shiny_deckgl import MapWidget, scatterplot_layer
    w, s = MapWidget("m"), _RouteSession()
    w.http_transport_threshold = 10
    asyncio.run(w.update(s, [scatterplot_layer("a", [[1, 2]])]))
    assert "url" in s.messages[-1][1]


def test_invalid_transport_is_rejected():
    from shiny_deckgl import MapWidget, scatterplot_layer
    with pytest.raises(ValueError, match="transport"):
        asyncio.run(MapWidget("m").update(_RouteSession(), [scatterplot_layer("a", [])], transport="carrier-pigeon"))


def test_session_without_dynamic_route_falls_back_to_websocket():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _FakeSession()
    w.http_transport_threshold = 10
    asyncio.run(w.update(s, _big_layers(100)))
    assert "layers" in s.messages[-1][1]
