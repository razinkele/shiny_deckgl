"""MapLibre control handling in deckgl-init.js (M1, M2 of the 2026-09-26 review).

M1: set_controls() removed and re-created every control on each call. The
watergis legend never detaches its map listeners on removal, so each rebuild
leaked them, and an open legend panel closed.

M2: legend_control() without targets listed every layer of the basemap
style (about 100 on CARTO). It now lists the app's own native layers, from a
live object kept in step as layers are added and removed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

_FAKES = r"""
var created = [];
var maplibregl = {
  NavigationControl: function (o) { this.kind = 'navigation'; this.opts = o; created.push(this); },
  ScaleControl: function (o) { this.kind = 'scale'; this.opts = o; created.push(this); },
};
var MaplibreLegendControl = { MaplibreLegendControl: function (targets, o) {
  this.kind = 'legend'; this.targets = targets; this.opts = o; this.redraws = 0; created.push(this);
  this.redraw = function () { this.redraws++; };
} };
function makeInstance() {
  var log = [];
  return {
    log: log,
    controls: {},
    nativeLayers: {},
    _legendAutoTargets: newLegendTargets(),
    map: {
      addControl: function (c, p) { log.push('add ' + c.kind + '@' + p); },
      removeControl: function (c) { log.push('remove ' + c.kind); },
      handlers: {},
      once: function (ev, fn) { this.handlers[ev] = fn; },
      off: function (ev) { delete this.handlers[ev]; },
    },
  };
}
"""


def _prelude() -> str:
    return "\n".join([
        _FAKES,
        extract_var("LEGEND_NO_TARGET"),
        extract_function("newLegendTargets"),
        extract_function("trackNativeLayer"),
        extract_function("refreshLegendWhenDrawn"),
        extract_function("resetNativeLayers"),
        extract_function("controlKey"),
        extract_function("applyControls"),
        extract_function("createControl"),
    ])


def _js(body: str):
    return run_js(_prelude(), "(function(){" + body + "})()")


@requires_node
class TestApplyControls:
    def test_unchanged_controls_are_kept(self):
        got = _js("""
            var i = makeInstance();
            var specs = [{ type: 'navigation', position: 'top-right', options: {} },
                         { type: 'legend', position: 'bottom-left', options: { showDefault: true } }];
            applyControls(i, specs);
            var first = i.controls.legend.control;
            i.log.length = 0;
            applyControls(i, JSON.parse(JSON.stringify(specs)));
            return { log: i.log, same: i.controls.legend.control === first, made: created.length };
        """)
        assert got == {"log": [], "same": True, "made": 2}

    def test_changed_control_is_replaced_and_others_kept(self):
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'navigation', options: {} },
                              { type: 'legend', position: 'bottom-left', options: { showDefault: false } }]);
            i.log.length = 0;
            applyControls(i, [{ type: 'navigation', options: {} },
                              { type: 'legend', position: 'bottom-left', options: { showDefault: true } }]);
            return i.log;
        """)
        assert got == ["remove legend", "add legend@bottom-left"]

    def test_dropped_control_is_removed(self):
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'navigation', options: {} }, { type: 'scale', options: {} }]);
            i.log.length = 0;
            applyControls(i, [{ type: 'scale', options: {} }]);
            return { log: i.log, types: Object.keys(i.controls) };
        """)
        assert got == {"log": ["remove navigation"], "types": ["scale"]}

    def test_moved_control_is_re_added(self):
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'scale', position: 'top-left', options: {} }]);
            i.log.length = 0;
            applyControls(i, [{ type: 'scale', position: 'bottom-left', options: {} }]);
            return i.log;
        """)
        assert got == ["remove scale", "add scale@bottom-left"]


@requires_node
class TestLegendDefaultTargets:
    def test_no_targets_means_the_live_native_layer_object(self):
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'legend', options: {} }]);
            var t = i.controls.legend.control.targets;
            var live = t === i._legendAutoTargets;
            trackNativeLayer(i, 'mpa-fill', true);
            trackNativeLayer(i, 'ports', true);
            trackNativeLayer(i, 'ports', false);
            return { live: live, keys: Object.keys(t) };
        """)
        assert got["live"] is True
        # The sentinel keeps the plugin from treating it as "all layers".
        assert got["keys"] == ["__shiny_deckgl_no_layer__", "mpa-fill"]

    def test_explicit_targets_are_passed_through(self):
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'legend', options: { targets: { water: 'Water' }, title: 'T' } }]);
            var c = i.controls.legend.control;
            return { targets: c.targets, opts: c.opts };
        """)
        assert got == {"targets": {"water": "Water"}, "opts": {"title": "T"}}

    def test_empty_targets_still_mean_every_layer(self):
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'legend', options: { targets: {} } }]);
            return i.controls.legend.control.targets;
        """)
        assert got == {}

    def test_style_reset_clears_the_live_targets(self):
        got = _js("""
            var i = makeInstance();
            trackNativeLayer(i, 'a', true);
            var t = i._legendAutoTargets;
            resetNativeLayers(i);
            trackNativeLayer(i, 'b', true);
            return { same: t === i._legendAutoTargets, keys: Object.keys(t), native: Object.keys(i.nativeLayers) };
        """)
        assert got == {"same": True, "keys": ["__shiny_deckgl_no_layer__", "b"], "native": ["b"]}

    def test_spec_options_are_not_mutated(self):
        got = _js("""
            var i = makeInstance();
            var spec = { type: 'legend', options: { targets: { w: 'W' } } };
            applyControls(i, [spec]);
            return spec.options;
        """)
        assert got == {"targets": {"w": "W"}}

    def test_legend_redraws_once_the_new_layer_is_drawn(self):
        # The plugin's own 'styledata' refresh runs before the layer is drawn,
        # so with onlyRendered the new layer would stay out of the legend.
        got = _js("""
            var i = makeInstance();
            applyControls(i, [{ type: 'legend', options: {} }]);
            var c = i.controls.legend.control;
            trackNativeLayer(i, 'a', true);
            trackNativeLayer(i, 'b', true);   // coalesced into one pending redraw
            var before = c.redraws;
            i.map.handlers.idle();
            return { before: before, after: c.redraws, pending: !!i._legendRefreshPending };
        """)
        assert got == {"before": 0, "after": 1, "pending": False}
