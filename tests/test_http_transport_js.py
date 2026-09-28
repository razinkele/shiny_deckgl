"""fetchPayload() and the per-map ordering behind a pending fetch (v1.13.0)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

_FAKES = r"""
var applied = [], log = [], errors = [];
var console = { error: function () { errors.push(Array.prototype.join.call(arguments, ' ')); }, warn: function () {} };
function onDeckUpdate(p) { applied.push(p); log.push('update:' + (p.layers ? p.layers.map(function (l) { return l.id; }).join(',') : '?')); }
var fetchCalls = [], pendingResolvers = [];
function fetch(url, opts) {
  fetchCalls.push([url, opts && opts.cache]);
  return new Promise(function (resolve) { pendingResolvers.push(function (body, ok) {
    resolve({ ok: ok !== false, status: ok === false ? 500 : 200, json: function () { return Promise.resolve(body); } }); }); });
}
var mapInstances = { m: {} };
var Shiny = { handlers: {}, addCustomMessageHandler: function (n, fn) { this.handlers[n] = fn; } };
var document = { getElementById: function () { return { id: 'm' }; } };
function deferMessage() { log.push('deferred'); }
var _handlerFns = {};
function tick() { return new Promise(function (r) { setTimeout(r, 0); }); }
"""


def _prelude():
    return "\n".join([_FAKES, extract_var("FETCH_ORDERED"), extract_function("fetchPayload"), extract_function("addDeferrable")])


def _js(body):
    return run_js(_prelude() + "\nvar __out = (async function(){" + body + "})();", "await __out")


@requires_node
class TestFetchPayload:
    def test_fetches_the_url_and_applies_the_json(self):
        got = _js("""
            fetchPayload(mapInstances.m, { id: 'm', url: 'session/S/dynamic_route/m_payload?nonce=a&v=1', seq: 1 });
            var pending = !!mapInstances.m._pendingFetch;
            await tick();                       // fetch() is called inside a .then()
            pendingResolvers[0]({ id: 'm', layers: [{ id: 'big' }] });
            await tick(); await tick();
            return { fetchCalls: fetchCalls, pending: pending, applied: applied, cleared: mapInstances.m._pendingFetch === null };
        """)
        assert got == {"fetchCalls": [["session/S/dynamic_route/m_payload?nonce=a&v=1", "no-store"]], "pending": True,
                       "applied": [{"id": "m", "layers": [{"id": "big"}]}], "cleared": True}

    def test_http_error_is_reported_not_thrown(self):
        got = _js("""
            fetchPayload(mapInstances.m, { id: 'm', url: 'u' });
            await tick();
            pendingResolvers[0](null, false);
            await tick(); await tick();
            return { applied: applied.length, errors: errors.length, cleared: mapInstances.m._pendingFetch === null };
        """)
        assert got == {"applied": 0, "errors": 1, "cleared": True}


@requires_node
class TestOrderingBehindAFetch:
    def test_layer_messages_wait_for_the_fetched_update(self):
        # Review Focus 5: a partial_update arriving during the fetch applies after it.
        got = _js("""
            addDeferrable('deck_partial_update', function (p) { log.push('partial:' + p.layers[0].id); });
            addDeferrable('deck_fly_to', function (p) { log.push('fly'); });
            fetchPayload(mapInstances.m, { id: 'm', url: 'u', seq: 1 });
            Shiny.handlers['deck_partial_update']({ id: 'm', layers: [{ id: 'big', getRadius: 9 }] });
            Shiny.handlers['deck_fly_to']({ id: 'm' });        // not layer-ordered: runs at once
            var before = log.slice();
            await tick();
            pendingResolvers[0]({ id: 'm', layers: [{ id: 'big' }] });
            await tick(); await tick(); await tick();
            return { before: before, after: log };
        """)
        assert got["before"] == ["fly"]
        assert got["after"] == ["fly", "update:big", "partial:big"]

    def test_without_a_pending_fetch_handlers_run_immediately(self):
        got = _js("""
            addDeferrable('deck_layer_visibility', function (p) { log.push('vis'); });
            Shiny.handlers['deck_layer_visibility']({ id: 'm', visibility: {} });
            return log;
        """)
        assert got == ["vis"]
