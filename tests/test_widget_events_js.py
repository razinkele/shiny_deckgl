"""buildWidgets() reports deck.gl widget state changes to Shiny (roadmap 2.3).

deck.gl >= 9.3 widgets take callback props (onTimeChange, onChange, onClick,
...) and read them from `this.props` at event time. attachWidgetEvents()
patches those props on the constructed instance so every callback also sets
one Shiny input per map, <mapId>_widget_event = {id, widget, event, value}.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

# Fake widget classes with deck.gl's shape: props merged over defaultProps,
# `id` taken from them, and setProps() merging like Widget.setProps.
_FAKES = r"""
var sent = [];
var Shiny = { setInputValue: function (n, v, o) { sent.push({name: n, value: v, opts: o}); } };
var document = { getElementById: function () { return null; } };
function makeClass(defaultId, clobberId) {
  function W(props) {
    this.props = Object.assign({ id: defaultId }, props);
    // deck.gl 9.4's TimelineWidget declares a class field `id = 'timeline'`
    // that runs after super(props) and overwrites the id the spec set.
    this.id = clobberId ? defaultId : this.props.id;
  }
  W.defaultProps = { id: defaultId };
  W.prototype.setProps = function (p) { Object.assign(this.props, p); };
  return W;
}
var deck = { TimelineWidget: makeClass('timeline', true), ToggleWidget: makeClass('toggle'),
             IconWidget: makeClass('icon'), ZoomWidget: makeClass('zoom'), _GeocoderWidget: makeClass('geocoder') };
function createDeckLayerLegendWidget(p) { return new (makeClass('deck-layer-legend'))(p); }
"""


def _prelude():
    return "\n".join([
        _FAKES,
        extract_var("WIDGET_EVENTS"),
        extract_function("resolveWidgetClass"),
        extract_function("attachWidgetEvents"),
        extract_function("buildWidgets"),
    ])


def _js(body):
    return run_js(_prelude(), "(function(){" + body + "})()")


@requires_node
class TestWidgetEvents:
    def test_timeline_changes_reach_shiny(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': '_TimelineWidget', id: 'tl', timeRange: [0, 10] }], 'm')[0];
            w.props.onTimeChange(4); w.props.onPlayingChange(true);
            return sent;
        """)
        assert got == [
            {"name": "m_widget_event", "value": {"id": "tl", "widget": "TimelineWidget", "event": "timeChange", "value": 4}, "opts": {"priority": "event"}},
            {"name": "m_widget_event", "value": {"id": "tl", "widget": "TimelineWidget", "event": "playingChange", "value": True}, "opts": {"priority": "event"}},
        ]

    def test_spec_id_wins_over_a_clobbered_widget_id(self):
        # TimelineWidget's class field sets widget.id = 'timeline' after
        # super(props); the spec's id survives only in props.id.
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': '_TimelineWidget', id: 'tl', timeRange: [0, 10] }], 'm')[0];
            w.props.onTimeChange(1);
            return { widgetId: w.id, reported: sent[0].value.id };
        """)
        assert got == {"widgetId": "timeline", "reported": "tl"}

    def test_unset_id_reports_the_classes_default_id(self):
        # Review Focus 1: deck.gl's default id is per class ("toggle"), not "widget".
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'ToggleWidget', icon: 'x' }], 'm')[0];
            w.props.onChange(true);
            return sent[0].value;
        """)
        assert got == {"id": "toggle", "widget": "ToggleWidget", "event": "change", "value": True}

    def test_callback_without_argument_sends_null(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'IconWidget', id: 'i', icon: 'info' }], 'm')[0];
            w.props.onClick();
            return sent[0].value;
        """)
        assert got == {"id": "i", "widget": "IconWidget", "event": "click", "value": None}

    def test_object_payloads_pass_through(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'ZoomWidget', id: 'z' }], 'm')[0];
            w.props.onZoom({ zoom: 5, direction: 'in' });
            return sent[0].value.value;
        """)
        assert got == {"zoom": 5, "direction": "in"}

    def test_existing_js_callback_is_still_called(self):
        got = _js("""
            var calls = 0;
            var w = buildWidgets([{ '@@widgetClass': 'ToggleWidget', id: 't', icon: 'x', onChange: function () { calls++; } }], 'm')[0];
            w.props.onChange(false);
            return { calls: calls, sent: sent.length };
        """)
        assert got == {"calls": 1, "sent": 1}

    def test_shim_survives_a_setProps_merge(self):
        # Review Focus 4: set_widgets() later merges new props into the instance.
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'ToggleWidget', id: 't', icon: 'x' }], 'm')[0];
            w.setProps({ icon: 'y', label: 'L' });
            w.props.onChange(true);
            return sent.length;
        """)
        assert got == 1

    def test_widgets_without_events_are_untouched(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': '_DeckLayerLegendWidget', id: 'l' }], 'm')[0];
            return Object.keys(w.props).filter(function (k) { return k.indexOf('on') === 0; });
        """)
        assert got == []
