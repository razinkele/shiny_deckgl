"""applyDarkMode / watchBootstrapTheme / handleSetDarkMode (v1.13.0).

A dark app (Bootstrap's data-bs-theme="dark" on <html>) gets the map's
dark_style and dark deck widgets; the swap goes through applyStyle(), so the
native-layer warning and tracker reset apply as for set_style().
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, requires_node, run_js  # noqa: E402

_FAKES = r"""
var sent = [];
var Shiny = { setInputValue: function (n, v, o) { sent.push({ name: n, value: v }); } };
var applied = [];
function applyStyle(instance, style, diff) { applied.push([style, diff]); instance.currentStyle = style; }
function makeEl() {
  var cls = {};
  return { dataset: {}, classList: { toggle: function (c, on) { cls[c] = !!on; }, contains: function (c) { return !!cls[c]; } } };
}
var observers = [];
function MutationObserver(cb) { this.cb = cb; observers.push(this); }
MutationObserver.prototype.observe = function (target, opts) { this.target = target; this.opts = opts; };
MutationObserver.prototype.disconnect = function () { this.disconnected = true; };
var htmlAttrs = {};
var document = { documentElement: { getAttribute: function (k) { return htmlAttrs[k] === undefined ? null : htmlAttrs[k]; } } };
function makeInstance(opts) {
  var el = makeEl();
  return { el: el, lightStyle: 'LIGHT', darkStyle: opts && opts.dark === null ? null : 'DARK', currentStyle: 'LIGHT', dark: false };
}
var mapInstances = {};
"""


def _prelude(*names):
    return "\n".join([_FAKES] + [extract_function(n) for n in names])


def _js(names, body):
    return run_js(_prelude(*names), "(function(){" + body + "})()")


@requires_node
class TestApplyDarkMode:
    def test_dark_swaps_style_toggles_class_and_reports(self):
        got = _js(["applyDarkMode"], """
            var inst = makeInstance(); mapInstances.m = inst;
            applyDarkMode(inst, 'm', true);
            return { applied: applied, cls: inst.el.classList.contains('deckgl-dark'), dark: inst.dark, sent: sent };
        """)
        assert got == {"applied": [["DARK", False]], "cls": True, "dark": True,
                       "sent": [{"name": "m_dark_mode", "value": {"dark": True, "style": "DARK"}}]}

    def test_light_again_restores_the_light_style(self):
        got = _js(["applyDarkMode"], """
            var inst = makeInstance();
            applyDarkMode(inst, 'm', true); applyDarkMode(inst, 'm', false);
            return { applied: applied, cls: inst.el.classList.contains('deckgl-dark') };
        """)
        assert got == {"applied": [["DARK", False], ["LIGHT", False]], "cls": False}

    def test_same_mode_twice_does_not_reload_the_style(self):
        got = _js(["applyDarkMode"], """
            var inst = makeInstance();
            applyDarkMode(inst, 'm', true); applyDarkMode(inst, 'm', true);
            return applied.length;
        """)
        assert got == 1

    def test_without_a_dark_style_only_the_widgets_change(self):
        # Review Focus 3 companion: no style swap, so native layers are untouched.
        got = _js(["applyDarkMode"], """
            var inst = makeInstance({ dark: null });
            applyDarkMode(inst, 'm', true);
            return { applied: applied, cls: inst.el.classList.contains('deckgl-dark'), sent: sent[0].value };
        """)
        assert got == {"applied": [], "cls": True, "sent": {"dark": True, "style": "LIGHT"}}


@requires_node
class TestWatchBootstrapTheme:
    def test_observer_follows_the_html_attribute(self):
        got = _js(["applyDarkMode", "watchBootstrapTheme"], """
            var inst = makeInstance(); inst.el.dataset.darkStyle = 'DARK';
            watchBootstrapTheme(inst, 'm');
            var ob = observers[0];
            htmlAttrs['data-bs-theme'] = 'dark'; ob.cb([]);
            var afterDark = inst.dark;
            htmlAttrs['data-bs-theme'] = 'light'; ob.cb([]);
            return { target: ob.target === document.documentElement, filter: ob.opts.attributeFilter, afterDark: afterDark, afterLight: inst.dark, applied: applied };
        """)
        assert got == {"target": True, "filter": ["data-bs-theme"], "afterDark": True, "afterLight": False,
                       "applied": [["DARK", False], ["LIGHT", False]]}

    def test_following_can_be_switched_off(self):
        got = _js(["applyDarkMode", "watchBootstrapTheme"], """
            var inst = makeInstance(); inst.el.dataset.darkStyle = 'DARK'; inst.el.dataset.followDarkMode = 'false';
            return { obs: watchBootstrapTheme(inst, 'm'), n: observers.length };
        """)
        assert got == {"obs": None, "n": 0}


@requires_node
def test_handle_set_dark_mode_message():
    got = _js(["applyDarkMode", "handleSetDarkMode"], """
        var inst = makeInstance(); mapInstances.m = inst;
        handleSetDarkMode({ id: 'm', dark: true }); handleSetDarkMode({ id: 'zz', dark: true }); handleSetDarkMode(null);
        return { dark: inst.dark, applied: applied };
    """)
    assert got == {"dark": True, "applied": [["DARK", False]]}
