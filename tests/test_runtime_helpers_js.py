"""Runtime helpers added by the 2026-09-28 review (docs/2026-09-28-app-review.md).

normaliseProjection: deck.gl 9.4 throws on every render for a MapLibre
projection other than mercator/globe.
dropImplicitNavigation: our default NavigationControl paints over deck's
Zoom/Compass widgets in the same corner.
settleDiffStyle: set_style(diff=True) fires no 'style.load', so the style
guard stalled every native-layer call for 30 s.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

_FAKES = r"""
var warnings = [];
var console = { warn: function () { warnings.push(Array.prototype.join.call(arguments, ' ')); } };
function fakeMap(projection) {
  var m = { _proj: projection, set: [], removed: [], handlers: {}, _deckStyleChanging: true, drained: 0 };
  m.getProjection = function () { return this._proj; };
  m.setProjection = function (p) { this.set.push(p); this._proj = p; };
  m.removeControl = function (c) { this.removed.push(c); };
  m.once = function (ev, fn) { this.handlers[ev] = fn; };
  m.off = function (ev) { delete this.handlers[ev]; };
  m._deckStyleDrainFn = function () { m.drained++; };
  return m;
}
function clearTimeout(id) { cleared.push(id); }
var cleared = [];
"""


def _prelude(*names):
    return "\n".join([_FAKES] + [extract_var("NAV_REPLACING_WIDGETS")] + [extract_function(n) for n in names])


def _js(names, body):
    return run_js(_prelude(*names), "(function(){" + body + "})()")


@requires_node
class TestNormaliseProjection:
    def test_supported_types_are_left_alone(self):
        got = _js(["normaliseProjection"], """
            var a = fakeMap({type: 'mercator'}), b = fakeMap({type: 'globe'}), c = fakeMap(undefined);
            return [normaliseProjection(a), normaliseProjection(b), normaliseProjection(c), a.set.length + b.set.length + c.set.length, warnings.length];
        """)
        assert got == ["mercator", "globe", None, 0, 0]

    def test_expression_and_vertical_perspective_become_globe(self):
        got = _js(["normaliseProjection"], """
            var a = fakeMap({type: ['interpolate', ['linear'], ['zoom'], 10, 'vertical-perspective', 12, 'mercator']});
            var b = fakeMap({type: 'vertical-perspective'});
            return [normaliseProjection(a), a.set, normaliseProjection(b), b.set, warnings.length];
        """)
        assert got == ["globe", [{"type": "globe"}], "globe", [{"type": "globe"}], 2]

    def test_unknown_string_becomes_mercator(self):
        got = _js(["normaliseProjection"], "var m = fakeMap({type: 'equirectangular'}); return [normaliseProjection(m), m.set];")
        assert got == ["mercator", [{"type": "mercator"}]]


@requires_node
class TestDropImplicitNavigation:
    _INST = "var nav = {control: 'NAV'}; var inst = { _implicitNavigation: IMPL, map: fakeMap(), controls: { navigation: nav } };"

    def test_zoom_or_compass_widget_replaces_the_default_control(self):
        got = _js(["dropImplicitNavigation"], self._INST.replace("IMPL", "true") + """
            var r = dropImplicitNavigation(inst, [{'@@widgetClass': 'CompassWidget'}]);
            return [r, inst.map.removed, 'navigation' in inst.controls];
        """)
        assert got == [True, ["NAV"], False]

    def test_other_widgets_keep_it(self):
        got = _js(["dropImplicitNavigation"], self._INST.replace("IMPL", "true") + """
            var r = dropImplicitNavigation(inst, [{'@@widgetClass': '_TimelineWidget'}, {'@@widgetClass': 'ScaleWidget'}]);
            return [r, inst.map.removed.length, 'navigation' in inst.controls];
        """)
        assert got == [False, 0, True]

    def test_an_explicit_navigation_control_is_never_removed(self):
        # The app asked for controls=[navigation_control()]: its choice stands.
        got = _js(["dropImplicitNavigation"], self._INST.replace("IMPL", "false") + """
            return [dropImplicitNavigation(inst, [{'@@widgetClass': 'ZoomWidget'}]), 'navigation' in inst.controls];
        """)
        assert got == [False, True]

    def test_no_widgets_or_no_control_is_a_noop(self):
        got = _js(["dropImplicitNavigation"], """
            var inst = { _implicitNavigation: true, map: fakeMap(), controls: {} };
            return [dropImplicitNavigation(inst, [{'@@widgetClass': 'ZoomWidget'}]), dropImplicitNavigation(inst, undefined), dropImplicitNavigation(null, [])];
        """)
        assert got == [False, False, False]


@requires_node
class TestSettleDiffStyle:
    _INST = """
        var inst = { map: fakeMap(), _styleChangeTimeout: 42, _styleLoadHandler: function () {} };
        inst.map.handlers['style.load'] = inst._styleLoadHandler;
    """

    def test_style_object_settles_synchronously(self):
        got = _js(["settleDiffStyle"], self._INST + """
            settleDiffStyle(inst, {version: 8, layers: []});
            return { changing: inst.map._deckStyleChanging, drained: inst.map.drained, cleared: cleared,
                     timeout: inst._styleChangeTimeout, handler: inst._styleLoadHandler, loadHandlerLeft: 'style.load' in inst.map.handlers };
        """)
        assert got == {"changing": False, "drained": 1, "cleared": [42], "timeout": None, "handler": None, "loadHandlerLeft": False}

    def test_style_url_settles_on_styledata(self):
        got = _js(["settleDiffStyle"], self._INST + """
            settleDiffStyle(inst, 'https://example.com/style.json');
            var before = inst.map._deckStyleChanging;
            inst.map.handlers['styledata']();
            return [before, inst.map._deckStyleChanging, inst.map.drained];
        """)
        assert got == [True, False, 1]

    def test_settling_twice_drains_once(self):
        got = _js(["settleDiffStyle"], self._INST + """
            settleDiffStyle(inst, {version: 8}); settleDiffStyle(inst, {version: 8});
            return inst.map.drained;
        """)
        assert got == 1
