"""handleDeckRequest(): the runtime side of MapWidget.rpc().

A deck_request {id, requestId, method, params} runs RPC_METHODS[method] and
sends [requestId, result, error] back through Shiny.shinyapp.makeRequest() to
the "<id>_rpc_reply" handler Python registered.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

_FAKES = r"""
var replies = [];
var window = { Shiny: null };
var Shiny = { shinyapp: { makeRequest: function (name, args, ok, err) { replies.push({ name: name, args: args }); ok(); } } };
window.Shiny = Shiny;
var console = { warn: function () {} };
function whenStyleReady(map, fn) { fn(); }
function simplifyFeature(f) { return { type: 'Feature', geometry: f.geometry, properties: f.properties, layer: { id: f.layer ? f.layer.id : null }, source: f.source || null }; }
function captureMapImage(instance, params, done) { done({ dataUrl: 'data:' + (params.format || 'png') + ';base64,AA==', width: 3, height: 2 }); }
var queries = [];
var mapInstances = { m: { map: {
  getCenter: function () { return { lng: 21.1, lat: 55.7 }; },
  getZoom: function () { return 6; }, getPitch: function () { return 0; }, getBearing: function () { return 30; },
  getBounds: function () { return { getWest: function () { return 20; }, getSouth: function () { return 55; }, getEast: function () { return 22; }, getNorth: function () { return 56; } }; },
  hasImage: function (id) { return id === 'anchor'; },
  project: function (ll) { return { x: ll[0] * 10, y: ll[1] * 10 }; },
  queryRenderedFeatures: function (geom, opts) { queries.push([geom, opts]); return [{ geometry: null, properties: { a: 1 }, layer: { id: 'ports' }, source: 's' }]; },
} } };
function flush() { return new Promise(function (r) { setTimeout(r, 0); }); }
"""


def _prelude():
    return "\n".join([_FAKES, extract_var("RPC_METHODS"), extract_function("rpcReply"), extract_function("handleDeckRequest")])


def _js(body):
    # handleDeckRequest resolves promises asynchronously: await a macrotask, then report.
    return run_js(_prelude() + "\nvar __out = (async function(){" + body + "})();",
                  "await __out")


@requires_node
class TestHandleDeckRequest:
    def test_get_view_state_reply_shape(self):
        got = _js("""
            handleDeckRequest({ id: 'm', requestId: 'r1', method: 'getViewState', params: {} });
            await flush();
            return replies;
        """)
        assert got == [{"name": "m_rpc_reply", "args": ["r1", {
            "longitude": 21.1, "latitude": 55.7, "zoom": 6, "pitch": 0, "bearing": 30,
            "bounds": {"sw": [20, 55], "ne": [22, 56]}}, None]}]

    def test_query_features_by_lnglat_projects_first(self):
        got = _js("""
            handleDeckRequest({ id: 'm', requestId: 'r2', method: 'queryFeatures', params: { lnglat: [2, 3], layers: ['ports'] } });
            await flush();
            return { queries: queries, reply: replies[0].args };
        """)
        assert got["queries"] == [[[20, 30], {"layers": ["ports"]}]]
        assert got["reply"][0] == "r2" and got["reply"][2] is None
        assert got["reply"][1] == [{"type": "Feature", "geometry": None, "properties": {"a": 1}, "layer": {"id": "ports"}, "source": "s"}]

    def test_export_image_and_has_image(self):
        got = _js("""
            handleDeckRequest({ id: 'm', requestId: 'r3', method: 'exportImage', params: { format: 'jpeg' } });
            handleDeckRequest({ id: 'm', requestId: 'r4', method: 'hasImage', params: { imageId: 'anchor' } });
            handleDeckRequest({ id: 'm', requestId: 'r5', method: 'hasImage', params: { imageId: 'nope' } });
            await flush();
            return replies.map(function (r) { return r.args; });
        """)
        assert got == [["r3", {"dataUrl": "data:jpeg;base64,AA==", "width": 3, "height": 2}, None],
                       ["r4", True, None], ["r5", False, None]]

    def test_unknown_method_and_unknown_map_reply_with_an_error(self):
        got = _js("""
            handleDeckRequest({ id: 'm', requestId: 'r6', method: 'launchMissiles', params: {} });
            handleDeckRequest({ id: 'zz', requestId: 'r7', method: 'getViewState', params: {} });
            await flush();
            return replies.map(function (r) { return r.args; });
        """)
        assert got[0][0] == "r6" and got[0][1] is None and "unknown rpc method" in got[0][2]
        assert got[1][0] == "r7" and "no such map" in got[1][2]

    def test_a_throwing_method_replies_with_the_error(self):
        got = _js("""
            mapInstances.m.map.getCenter = function () { throw new Error('boom'); };
            handleDeckRequest({ id: 'm', requestId: 'r8', method: 'getViewState', params: {} });
            await flush();
            return replies[0].args;
        """)
        assert got == ["r8", None, "boom"]

    def test_missing_ids_are_ignored(self):
        got = _js("""
            handleDeckRequest(null); handleDeckRequest({ id: 'm' }); handleDeckRequest({ requestId: 'x' });
            await flush();
            return replies.length;
        """)
        assert got == 0
