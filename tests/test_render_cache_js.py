"""Resolved layer props are cached per source layer (shared frame loop, part A).

Every animation frame used to rebuild every layer from a fresh clone: new
accessor functions (new Function) and freshly decoded binary arrays each
time. deck.gl compares those by identity, so it recomputed attributes and
re-uploaded buffers for every layer, every frame. Re-rendering the same
lastLayers entry must now hand deck.gl the same functions and data.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

_STUBS = r"""
var window = globalThis;
function FakeLayer(props) { this.props = props; }
var deck = { ScatterplotLayer: FakeLayer, IconLayer: FakeLayer, PathLayer: FakeLayer };
var mapInstances = { m: {} };
var Shiny = { setInputValue: function () {} };
function getOrCreateTooltipEl() { return null; }
function sanitizeHtml(s) { return s; }
function interpolateTemplate(s) { return s; }
"""


def _prelude() -> str:
    parts = [_STUBS]
    for v in ["ACCESSOR_DANGEROUS_PROPS_RE", "ACCESSOR_ALLOWED_IDENTS", "ACCESSOR_KEY_RE",
              "LEGACY_COORDINATE_SYSTEMS", "TYPED_ARRAY_MAP", "EASINGS", "WMS_BBOX_RE",
              "RASTER_TYPES", "_svgAtlasCache", "_resolvedLayerCache"]:
        parts.append(extract_var(v))
    for f in ["cloneLayer", "cloneLayersData", "isSafeAccessorExpr", "normaliseCoordinateSystem",
              "resolveAccessors", "resolveWidgetClass", "resolveExtensions", "decodeBinaryValue",
              "resolveBinaryAttributes", "lonToMercX", "latToMercY", "buildDeckLayers",
              "resolveLayerCached", "instantiateLayer", "resolveLayerProps"]:
        parts.append(extract_function(f))
    return "\n".join(parts)


def _b64(values) -> str:
    import struct
    return base64.b64encode(struct.pack(f"<{len(values)}f", *values)).decode()


_LAYERS = json.dumps([
    {"type": "ScatterplotLayer", "id": "pts", "data": [{"p": [1, 2]}],
     "getPosition": "@@=d.p", "getRadius": "@@=d.p[0] * 2"},
    {"type": "PathLayer", "id": "bin", "data": {"length": 2},
     "getPath": {"@@binary": True, "dtype": "float32", "size": 2, "value": _b64([0, 0, 1, 1])}},
    {"type": "ScatterplotLayer", "id": "spin",
     "getAngle": {"@@animate": True, "prop": "a", "speed": 10}},
])


@requires_node
class TestResolvedLayerCache:
    def test_same_source_gives_same_functions_and_data(self):
        got = run_js(_prelude(), f"""(function(){{
            var src = {_LAYERS};
            var a = buildDeckLayers(src, 'm'), b = buildDeckLayers(src, 'm');
            return {{
              getPosition: a[0].props.getPosition === b[0].props.getPosition,
              getRadius: a[0].props.getRadius === b[0].props.getRadius,
              pickHandler: a[0].props.onHover === b[0].props.onHover,
              binaryData: a[1].props.data === b[1].props.data,
              binaryAttr: a[1].props.data.attributes.getPath.value === b[1].props.data.attributes.getPath.value,
              newLayerObjects: a[0] !== b[0],
            }};
        }})()""")
        assert got == {"getPosition": True, "getRadius": True, "pickHandler": True,
                       "binaryData": True, "binaryAttr": True, "newLayerObjects": True}

    def test_replaced_layer_is_resolved_afresh(self):
        got = run_js(_prelude(), f"""(function(){{
            var src = {_LAYERS};
            var a = buildDeckLayers(src, 'm');
            src[0] = Object.assign({{}}, src[0], {{ visible: false }});
            var b = buildDeckLayers(src, 'm');
            return {{ changed: a[0].props.getPosition !== b[0].props.getPosition,
                      visible: b[0].props.visible, otherKept: a[1].props.data === b[1].props.data }};
        }})()""")
        assert got == {"changed": True, "visible": False, "otherKept": True}

    def test_source_objects_are_not_mutated(self):
        got = run_js(_prelude(), f"""(function(){{
            var src = {_LAYERS};
            var before = JSON.stringify(src);
            buildDeckLayers(src, 'm');
            return JSON.stringify(src) === before;
        }})()""")
        assert got is True

    def test_animated_value_is_read_per_render(self):
        got = run_js(_prelude(), f"""(function(){{
            var src = {_LAYERS};
            window._deckgl_anim_m_a = 5;
            var a = buildDeckLayers(src, 'm');
            window._deckgl_anim_m_a = 42;
            var b = buildDeckLayers(src, 'm');
            return [a[2].props.getAngle, b[2].props.getAngle, '_LayerClass' in b[2].props];
        }})()""")
        assert got == [5, 42, False]

    def test_svg_atlas_raster_is_picked_up_once_ready(self):
        got = run_js(_prelude(), """(function(){
            var url = 'data:image/svg+xml;charset=utf-8,%3Csvg%2F%3E';
            var src = [{ type: 'IconLayer', id: 'ic', data: [], iconAtlas: url }];
            var a = buildDeckLayers(src, 'm');
            _svgAtlasCache[url] = { raster: true };
            var b = buildDeckLayers(src, 'm');
            return [typeof a[0].props.iconAtlas, b[0].props.iconAtlas];
        })()""")
        assert got == ["string", {"raster": True}]


@requires_node
def test_beforeId_reaches_the_deck_layer_props():
    # Review Focus 5: deck.gl ignores beforeId when overlaid, so it must pass
    # through unchanged for the same spec to work in both modes.
    got = run_js(_prelude(), """(function(){
        var src = [{ type: 'ScatterplotLayer', id: 'p', data: [], beforeId: 'waterway-label' }];
        return buildDeckLayers(src, 'm')[0].props.beforeId;
    })()""")
    assert got == "waterway-label"


@requires_node
class TestPickable3d:
    """deck.gl 9.3+: pickable may be '3d' (depth picking); keep it, do not flatten to true."""

    def test_3d_is_kept_and_handlers_attached(self):
        got = run_js(_prelude(), """(function(){
            var l = buildDeckLayers([{ type: 'ScatterplotLayer', id: 'p', data: [], pickable: '3d' }], 'm')[0];
            return { pickable: l.props.pickable, click: typeof l.props.onClick, hover: typeof l.props.onHover };
        })()""")
        assert got == {"pickable": "3d", "click": "function", "hover": "function"}

    def test_raster_layer_with_3d_gets_no_handlers(self):
        # Review Focus 2: raster layers skip the pick-handler setup either way.
        got = run_js(_prelude() + "\ndeck.TileLayer = FakeLayer;", """(function(){
            var l = buildDeckLayers([{ type: 'TileLayer', id: 't', data: 'https://x/{z}/{x}/{y}.png', pickable: '3d' }], 'm')[0];
            return { pickable: l.props.pickable, click: typeof l.props.onClick };
        })()""")
        assert got == {"pickable": "3d", "click": "undefined"}


@requires_node
def test_map_options_merge_keeps_container_and_style():
    got = run_js("var console = { warn: function () {} };\n" + extract_function("mergeMapOptions"), """(function(){
        var base = { container: 'm', style: 'S', zoom: 3, maxZoom: 24 };
        return [
          mergeMapOptions(base, { dataset: {} }),
          mergeMapOptions(base, { dataset: { mapOptions: JSON.stringify({ maxZoom: 12, maxBounds: [[20,54],[23,57]], container: 'evil', style: 'evil' }) } }),
          mergeMapOptions(base, { dataset: { mapOptions: '{not json' } }),
        ];
    })()""")
    assert got[0] == {"container": "m", "style": "S", "zoom": 3, "maxZoom": 24}
    assert got[1] == {"container": "m", "style": "S", "zoom": 3, "maxZoom": 12, "maxBounds": [[20, 54], [23, 57]]}
    assert got[2] == got[0]
