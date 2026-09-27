"""A repeated shiny:connected (a reconnect) tells the server which maps are live.

Shiny's client fires shiny:connected on every socket open. The first one
runs the package's startup; with session.allow_reconnect() (Shiny >= 1.8.0)
later ones mean the websocket came back, and the custom messages that feed
the maps were not replayed -- so each live map reports <id>_reconnected.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

# Every global onShinyConnected touches must exist: the harness runs in
# strict mode. _reconnectCount is extracted from the runtime itself.
_FAKES = r"""
var sent = [];
var Shiny = { setInputValue: function (n, v, o) { sent.push({name: n, value: v, opts: o}); } };
var mapInstances = { a: {}, b: {} };
var _shinyConnectedHandled = false;
function loadMapLibre() { return Promise.resolve(); }
var document = { querySelectorAll: function () { return []; } };
function setTimeout() {}
"""


@requires_node
def test_second_connected_reports_a_reconnect_for_every_map():
    prelude = "\n".join([_FAKES, extract_var("_reconnectCount"), extract_function("onShinyConnected")])
    got = run_js(prelude, """(function(){
        onShinyConnected();            // first connect: no report
        var afterFirst = sent.length;
        onShinyConnected(); onShinyConnected();
        return { afterFirst: afterFirst, sent: sent };
    })()""")
    assert got["afterFirst"] == 0
    assert got["sent"] == [
        {"name": "a_reconnected", "value": {"count": 1}, "opts": {"priority": "event"}},
        {"name": "b_reconnected", "value": {"count": 1}, "opts": {"priority": "event"}},
        {"name": "a_reconnected", "value": {"count": 2}, "opts": {"priority": "event"}},
        {"name": "b_reconnected", "value": {"count": 2}, "opts": {"priority": "event"}},
    ]
