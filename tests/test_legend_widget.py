"""Layer legend widget: Python spec and client-side behaviour.

Findings L1-L6 of docs/2026-09-26-codebase-review.md. The JS tests run the
real `createDeckLayerLegendWidget` from deckgl-init.js under Node against a
minimal fake DOM, with a fake `deck.Widget` base that merges props on
`setProps` the way deck.gl 9.4's does.
"""
from __future__ import annotations

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _js_harness import (  # noqa: E402
    extract_function,
    extract_var,
    requires_node,
    run_js,
)

from shiny_deckgl import MapWidget, layer_legend_widget  # noqa: E402


# ---------------------------------------------------------------------------
# Python spec
# ---------------------------------------------------------------------------

class TestLegendSpec:
    def test_optional_keys_are_always_emitted(self):
        # L5: deck.gl merges new widget props into the old ones, so a key
        # left out of the spec keeps its previous value on the client.
        spec = layer_legend_widget()
        assert spec["title"] is None
        assert spec["excludeLayers"] == []
        assert spec["labelMap"] == {}
        assert spec["includeHidden"] is False

    def test_given_values_are_passed_through(self):
        spec = layer_legend_widget(
            title="Layers", exclude_layers=("a",), label_map={"b": "B"},
        )
        assert spec["title"] == "Layers"
        assert spec["excludeLayers"] == ["a"]
        assert spec["labelMap"] == {"b": "B"}

    def test_spec_is_a_widget(self):
        spec = layer_legend_widget(entries=[{"layer_id": "a"}])
        assert spec["@@widgetClass"] == "_DeckLayerLegendWidget"
        assert spec["entries"] == [{"layer_id": "a"}]


class TestLegendVisibilityInput:
    def test_input_id(self):
        assert MapWidget("m1").legend_visibility_input_id == "m1_legend_visibility"


# ---------------------------------------------------------------------------
# Client behaviour
# ---------------------------------------------------------------------------

_FAKE_ENV = r"""
class El {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.children = []; this.style = {};
    this.className = ''; this.attrs = {}; this.listeners = {};
    this.textContent = ''; this.checked = false; this.parentNode = null;
    var self = this;
    this.classList = { add: function () {
      self.className = (self.className + ' ' + Array.from(arguments).join(' ')).trim();
    } };
  }
  appendChild(c) { this.children.push(c); c.parentNode = this; return c; }
  set innerHTML(v) { this.children = []; this._html = v; }
  get innerHTML() { return this._html || ''; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  fire(t) { var self = this; (this.listeners[t] || []).forEach(function (f) { f.call(self, { target: self }); }); }
  all(cls) {
    var out = [];
    (function walk(n) { n.children.forEach(function (c) {
      if ((' ' + c.className + ' ').indexOf(' ' + cls + ' ') >= 0) out.push(c);
      walk(c);
    }); })(this);
    return out;
  }
  querySelector(sel) { return this.all(sel.slice(1))[0] || null; }
}
globalThis.document = { createElement: function (t) { return new El(t); } };

// deck.gl 9.4 Widget: props = defaults + props; setProps MERGES and re-renders.
class FakeWidget {
  constructor(props) { this.props = Object.assign({ id: 'widget' }, props); this.id = this.props.id; }
  setProps(props) { Object.assign(this.props, props); if (this.rootElement) this.onRenderHTML(this.rootElement); }
}
globalThis.deck = { Widget: FakeWidget };

globalThis.sent = [];
globalThis.Shiny = { setInputValue: function (name, value, opts) { sent.push({ name: name, value: value, opts: opts }); } };

var fakeOverlay = { props: null, setProps: function (p) { this.props = p; } };
var fakeDeck = {};
fakeOverlay._deck = fakeDeck;
var mapInstances = { m1: {
  overlay: fakeOverlay,
  map: { triggerRepaint: function () {} },
  lastLayers: [
    { id: 'a', type: 'ScatterplotLayer', getFillColor: [255, 0, 0] },
    { id: 'b', type: 'PathLayer', getColor: [0, 0, 255] },
  ],
} };
function buildDeckLayers(layers) { return layers; }
function cloneLayersData(layers) { return layers; }

// Mount a widget the way WidgetManager._addWidget does.
function mount(props) {
  var w = createDeckLayerLegendWidget(props);
  w.deck = fakeDeck;
  w.rootElement = new El('div');
  w.onRenderHTML(w.rootElement);
  return w;
}
function rows(w) { return w.rootElement.all('deck-legend-row'); }
function labels(w) { return rows(w).map(function (r) { return r.all('deck-legend-label')[0].textContent; }); }
function box(w, i) { return rows(w)[i].all('deck-legend-cb')[0]; }
function body(w) { return w.rootElement.all('deck-legend-body')[0]; }
function header(w) { return w.rootElement.all('deck-legend-header')[0] || null; }
"""


def _prelude() -> str:
    return "\n".join([
        _FAKE_ENV,
        extract_var("LEGEND_DEFAULTS"),
        "var _DeckLayerLegendWidgetClass = null;",
        extract_function("createDeckLayerLegendWidget"),
        extract_function("buildWidgets"),
    ])


def _js(body: str):
    return run_js(_prelude(), "(function(){" + body + "})()")


@requires_node
class TestLegendClient:
    def test_unchecked_layer_stays_listed_after_refresh(self):
        # L1: a layer hidden from the legend must stay listed (unchecked)
        # or it can never be switched back on.
        got = _js("""
            var w = mount({ autoIntrospect: true });
            var cb = box(w, 0); cb.checked = false; cb.fire('change');
            w._refresh();
            return { labels: labels(w), a: box(w, 0).checked, b: box(w, 1).checked };
        """)
        assert got == {"labels": ["a", "b"], "a": False, "b": True}

    def test_user_hidden_layer_survives_a_server_visibility_patch(self):
        # A later deck_layer_visibility that doesn't mention the layer keeps
        # visible:false in lastLayers; the row must still be there.
        got = _js("""
            var w = mount({ autoIntrospect: true });
            var cb = box(w, 0); cb.checked = false; cb.fire('change');
            mapInstances.m1.lastLayers = mapInstances.m1.lastLayers.map(function (l) { return Object.assign({}, l); });
            w._refresh();
            return { labels: labels(w), a: box(w, 0).checked };
        """)
        assert got == {"labels": ["a", "b"], "a": False}

    def test_server_hidden_layer_is_left_out_by_default(self):
        # "Active layers" legends (the demo's Layers tab) rely on this.
        got = _js("""
            mapInstances.m1.lastLayers[1] = Object.assign({}, mapInstances.m1.lastLayers[1], { visible: false });
            var w = mount({ autoIntrospect: true });
            return labels(w);
        """)
        assert got == ["a"]

    def test_include_hidden_lists_server_hidden_layers_unchecked(self):
        got = _js("""
            mapInstances.m1.lastLayers[1] = Object.assign({}, mapInstances.m1.lastLayers[1], { visible: false });
            var w = mount({ autoIntrospect: true, includeHidden: true });
            return { labels: labels(w), b: box(w, 1).checked };
        """)
        assert got == {"labels": ["a", "b"], "b": False}

    def test_reshown_layer_is_no_longer_pinned(self):
        # Once the server shows the layer again, a later server hide drops it.
        got = _js("""
            var w = mount({ autoIntrospect: true });
            var cb = box(w, 0); cb.checked = false; cb.fire('change');
            mapInstances.m1.lastLayers[0] = Object.assign({}, mapInstances.m1.lastLayers[0], { visible: true });
            w._refresh();
            mapInstances.m1.lastLayers[0] = Object.assign({}, mapInstances.m1.lastLayers[0], { visible: false });
            w._refresh();
            return labels(w);
        """)
        assert got == ["b"]

    def test_toggle_is_reported_to_shiny(self):
        # L2: legend toggles must reach the server.
        got = _js("""
            var w = mount({ autoIntrospect: true });
            var cb = box(w, 1); cb.checked = false; cb.fire('change');
            return { sent: sent, hidden: mapInstances.m1.lastLayers[1].visible };
        """)
        assert got["hidden"] is False
        assert got["sent"] == [{
            "name": "m1_legend_visibility",
            "value": {"layer_id": "b", "visible": False},
            "opts": {"priority": "event"},
        }]

    def test_user_collapse_survives_refresh(self):
        # L3: re-rendering on a layer update must not undo the user's click.
        got = _js("""
            var w = mount({ autoIntrospect: true, title: 'Layers' });
            header(w).fire('click');
            var afterClick = body(w).style.display;
            w._refresh();
            w.setProps({ autoIntrospect: true, title: 'Layers' });
            return { afterClick: afterClick, afterRefresh: body(w).style.display };
        """)
        assert got == {"afterClick": "none", "afterRefresh": "none"}

    def test_changing_the_collapsed_prop_still_applies(self):
        got = _js("""
            var w = mount({ title: 'T', collapsed: false });
            w.setProps({ collapsed: true });
            var collapsed = body(w).style.display;
            w.setProps({ collapsed: false });
            return { collapsed: collapsed, expanded: body(w).style.display };
        """)
        assert got == {"collapsed": "none", "expanded": ""}

    def test_collapsed_without_title_can_be_opened(self):
        # L4: a collapsed legend needs a header or it can never be opened.
        got = _js("""
            var w = mount({ entries: [{ layer_id: 'a', label: 'A' }], collapsed: true });
            var h = header(w);
            if (!h) return { header: false };
            h.fire('click');
            return { header: true, title: h.all('deck-legend-title')[0].textContent,
                     display: body(w).style.display };
        """)
        assert got == {"header": True, "title": "Layers", "display": ""}

    def test_title_is_text_not_html(self):
        got = _js("""
            var w = mount({ title: '<img src=x onerror=alert(1)>' });
            var t = header(w).all('deck-legend-title')[0];
            return { text: t.textContent, html: t.innerHTML };
        """)
        assert got == {"text": "<img src=x onerror=alert(1)>", "html": ""}

    def test_cleared_title_is_removed(self):
        # L5 (client half): an explicit null title replaces the old one.
        got = _js("""
            var w = mount({ title: 'Old' });
            w.setProps({ title: null });
            return header(w) === null;
        """)
        assert got is True

    def test_empty_widget_list_clears_widgets(self):
        # L6: [] must reach overlay.setProps so deck.gl removes the widgets.
        got = _js("""
            return { empty: buildWidgets([], 'm1'), none: buildWidgets(undefined, 'm1') === undefined };
        """)
        assert got == {"empty": [], "none": True}

    def test_remove_unregisters_the_widget(self):
        got = _js("""
            var w = mount({ autoIntrospect: true });
            var registered = mapInstances.m1._legendWidget === w;
            w.onRemove();
            return { registered: registered, after: mapInstances.m1._legendWidget || null };
        """)
        assert got == {"registered": True, "after": None}


# ---------------------------------------------------------------------------
# Swatch colours for auto-introspected entries (L7, L8)
# ---------------------------------------------------------------------------

DECK_DEFAULT_RAMP = [
    [255, 255, 178], [254, 217, 118], [254, 178, 76],
    [253, 141, 60], [240, 59, 32], [189, 0, 38],
]


def _entry_for(layer_js: str):
    """Introspect a single layer and return its legend entry."""
    return _js(f"""
        mapInstances.m1.lastLayers = [{layer_js}];
        var w = mount({{ autoIntrospect: true }});
        return w._introspectLayers()[0];
    """)


@requires_node
class TestSwatchColours:
    def test_hexagon_colour_range_is_a_gradient(self):
        e = _entry_for("{ id: 'h', type: 'HexagonLayer', colorRange: [[1,2,3],[4,5,6]] }")
        assert e["shape"] == "gradient"
        assert e["colors"] == [[1, 2, 3], [4, 5, 6]]

    @pytest.mark.parametrize("layer_type", [
        "HeatmapLayer", "HexagonLayer", "GridLayer", "ScreenGridLayer",
    ])
    def test_aggregation_without_colour_range_uses_deck_default_ramp(self, layer_type):
        e = _entry_for(f"{{ id: 'x', type: '{layer_type}' }}")
        assert e["shape"] == "gradient"
        assert e["colors"] == DECK_DEFAULT_RAMP

    def test_contour_colours_come_from_contours(self):
        e = _entry_for("{ id: 'c', type: 'ContourLayer', contours: ["
                       "{ threshold: 1, color: [255,0,0] }, { threshold: 5, color: [0,0,255] }] }")
        assert e["shape"] == "gradient"
        assert e["colors"] == [[255, 0, 0], [0, 0, 255]]

    def test_accessor_path_is_sampled(self):
        # The row also has a `color` field; the accessor points elsewhere.
        e = _entry_for("{ id: 's', type: 'ScatterplotLayer', getFillColor: '@@=d.fill_color',"
                       " data: [{ fill_color: [1,2,3], color: [9,9,9] }] }")
        assert e["color"] == [1, 2, 3]

    def test_property_accessor_form_is_sampled(self):
        e = _entry_for("{ id: 's', type: 'PathLayer', getColor: '@@d.rgb',"
                       " data: [{ rgb: [10,20,30] }] }")
        assert e["color"] == [10, 20, 30]

    def test_geojson_feature_properties_are_sampled(self):
        e = _entry_for("{ id: 'g', type: 'GeoJsonLayer', getFillColor: '@@=d.properties.c',"
                       " data: { type: 'FeatureCollection', features: ["
                       "{ type: 'Feature', properties: { c: [7,8,9] }, geometry: null }] } }")
        assert e["color"] == [7, 8, 9]

    def test_arc_accessors_are_sampled(self):
        e = _entry_for("{ id: 'a', type: 'ArcLayer', getSourceColor: '@@d.a', getTargetColor: '@@d.b',"
                       " data: [{ a: [1,1,1], b: [2,2,2] }] }")
        assert e["shape"] == "arc"
        assert (e["color"], e["color2"]) == ([1, 1, 1], [2, 2, 2])

    def test_unrelated_color_field_is_not_used_for_an_expression(self):
        # An accessor that can't be read statically must not fall back to a
        # `color` field it never uses.
        e = _entry_for("{ id: 's', type: 'ScatterplotLayer', getFillColor: '@@=d.v > 1 ? [1,1,1] : [2,2,2]',"
                       " data: [{ v: 3, color: [9,9,9] }] }")
        assert e["color"] != [9, 9, 9]
