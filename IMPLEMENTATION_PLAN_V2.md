# shiny_deckgl — Maximum Implementation Plan v2

> Post-audit roadmap for v0.7.0 through v1.0.0
> Builds on the completed v0.1–v0.6 foundation (310 tests, 38 async methods,
> 36 JS handlers, 5 layer helpers, 3 view helpers, all deck.gl layers accessible).
>
> Based on the deep audit comparing deck.gl v9.1.4 full API surface against
> the current shiny_deckgl v0.6.0 implementation.

---

## Current State (v0.6.0)

### What Works

| Area | Coverage |
|------|----------|
| **Layers** (33 types) | 100% functional — 4 convenience helpers + generic `layer()` |
| **Extensions** (9 types) | ~90% — all available via `@@extensions`, no constructor args |
| **Views** (4 types) | 75% — 3 helpers, GlobeView via generic only |
| **MapLibre controls** | 7 types via `add_control()` |
| **Events** | ~70% — click, hover, move, context menu, marker events |
| **Binary transport** | Full — base64 TypedArray encoding |
| **Camera transitions** | flyTo via `transitionDuration` |
| **3D / Globe / Terrain** | Full — projection, terrain, sky |
| **Drawing** | Full — MapboxDraw integration |
| **Native MapLibre layers** | Full — sources, layers, paint/layout/filter |
| **Export** | Image export (PNG/JPEG/WebP) + standalone HTML |
| **Serialization** | `to_json()` / `from_json()` / `to_html()` |

### What's Missing (from audit)

| Gap | Impact |
|-----|--------|
| Extension constructor options | Can't configure DataFilterExtension, etc. |
| deck.gl Widgets (16 types) | No native deck.gl UI widgets |
| Layer convenience helpers | Only 4 of 33 have helpers |
| Layer prop transitions | Undocumented passthrough, no Python API |
| Deck-level props (pickingRadius, controller, etc.) | 7+ props not configurable |
| GlobeView helper | Missing convenience function |
| Events (drag, onDataLoad, box pick) | ~30% of events not wired |
| Multi-view coordination | Partial — no per-view viewState, no layerFilter |
| TripsLayer animation | Needs `_animate: true` + timer loop |
| Custom renderSubLayers | Only `@@BitmapLayer` shorthand |

---

## Phase 5: v0.7.0 — Extensions, DeckProps & Layer Helpers

**Theme**: Close the gaps in the generic layer/extension pipeline and expose
missing Deck-level configuration. Add convenience helpers for the most popular
layer types.

**Estimated effort**: ~600 lines Python, ~150 lines JS, ~400 lines tests

### 5.1 Extension Constructor Options

**Problem**: `resolveExtensions()` calls `new deck[name]()` with no arguments.
Users can't pass `DataFilterExtension({filterSize: 2})` or
`BrushingExtension({brushRadius: 5000})`.

**Python change** (`components.py`):

```python
def layer(type: str, id: str, data=None, extensions: list | None = None, **kwargs):
    """
    extensions now accepts both strings and [name, options] tuples:
        extensions=["BrushingExtension"]                        # no args
        extensions=[["DataFilterExtension", {"filterSize": 2}]] # with args
        extensions=["ClipExtension", ["MaskExtension", {}]]     # mixed
    """
    spec = {"type": type, "id": id, **kwargs}
    if data is not None:
        spec["data"] = _serialise_data(data)
    if extensions:
        resolved = []
        for ext in extensions:
            if isinstance(ext, str):
                resolved.append(ext)
            elif isinstance(ext, (list, tuple)) and len(ext) == 2:
                resolved.append({"@@extClass": ext[0], "@@extOpts": ext[1]})
            else:
                raise ValueError(f"Invalid extension spec: {ext}")
        spec["@@extensions"] = resolved
    return spec
```

**JS change** (`deckgl-init.js` — `resolveExtensions()`):

```javascript
function resolveExtensions(specList) {
    if (!specList) return undefined;
    return specList.map(item => {
        if (typeof item === 'string') {
            const Cls = deck[item];
            if (!Cls) { console.warn('Unknown extension:', item); return null; }
            return new Cls();
        }
        if (item && item['@@extClass']) {
            const Cls = deck[item['@@extClass']];
            if (!Cls) { console.warn('Unknown extension:', item['@@extClass']); return null; }
            return new Cls(item['@@extOpts'] || {});
        }
        return null;
    }).filter(Boolean);
}
```

**Tests**:
- `test_extension_string_only` — backward compat
- `test_extension_with_options_tuple` — `[["DataFilterExtension", {"filterSize": 2}]]`
- `test_extension_mixed` — strings and tuples together
- `test_extension_invalid_raises` — bad input → ValueError

---

### 5.2 Deck-Level Props

**Problem**: `pickingRadius`, `useDevicePixels`, `_animate`, `parameters`,
`controller`, `getCursor` are not configurable from Python.

**Python change** (`components.py` — `MapWidget.__init__`):

```python
def __init__(
    self,
    id: str,
    view_state: dict | None = None,
    style: str = CARTO_POSITRON,
    tooltip: dict | None = None,
    mapbox_api_key: str | None = None,
    controls: list[dict] | None = None,
    # NEW v0.7.0
    picking_radius: int = 0,
    use_device_pixels: bool | int = True,
    animate: bool = False,
    parameters: dict | None = None,
    controller: bool | dict = True,
):
```

These are stored and passed through the `data-*` attributes on the HTML element,
read by `initMap()` in JS.

**Python change** (`components.py` — `update()`):

```python
async def update(
    self,
    session: Session,
    layers: list[dict],
    view_state: dict | None = None,
    transition_duration: int = 0,
    effects: list[dict] | None = None,
    views: list[dict] | None = None,
    # NEW v0.7.0
    picking_radius: int | None = None,
    use_device_pixels: bool | int | None = None,
    animate: bool | None = None,
):
```

**JS change** (`deckgl-init.js` — `deck_update` handler):

```javascript
// After overlay.setProps({layers, effects, views}), also:
const deckProps = {};
if (msg.pickingRadius !== undefined) deckProps.pickingRadius = msg.pickingRadius;
if (msg.useDevicePixels !== undefined) deckProps.useDevicePixels = msg.useDevicePixels;
if (msg._animate !== undefined) deckProps._animate = msg._animate;
overlay.setProps(deckProps);
```

**New method** — `set_controller()`:

```python
async def set_controller(self, session: Session, options: bool | dict):
    """
    Configure map controller behaviour.
    options=True  → default controller
    options=False → disable interaction
    options={"touchRotate": True, "doubleClickZoom": False, "dragPan": True}
    """
    await session.send_custom_message("deck_set_controller", {
        "id": self.id, "controller": options
    })
```

**Tests**: 10+ tests for each new parameter, boundary values, serialization.

---

### 5.3 Layer Convenience Helpers

Add helpers for the 10 most commonly-used layer types that don't have one yet.

**New functions** (`components.py`):

```python
def arc_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getSourceColor": [0, 128, 200],
        "getTargetColor": [200, 0, 80],
        "getWidth": 2,
    }
    return {**defaults, **kwargs, "type": "ArcLayer", "id": id,
            "data": _serialise_data(data)}

def icon_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getPosition": "@@d",
        "getSize": 24,
        "sizeScale": 1,
    }
    return {**defaults, **kwargs, "type": "IconLayer", "id": id,
            "data": _serialise_data(data)}

def path_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getPath": "@@d.path",
        "getColor": [0, 128, 255],
        "getWidth": 3,
        "widthMinPixels": 1,
    }
    return {**defaults, **kwargs, "type": "PathLayer", "id": id,
            "data": _serialise_data(data)}

def line_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getColor": [0, 0, 0, 128],
        "getWidth": 1,
    }
    return {**defaults, **kwargs, "type": "LineLayer", "id": id,
            "data": _serialise_data(data)}

def text_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getPosition": "@@d",
        "getText": "@@d.text",
        "getSize": 16,
        "getColor": [0, 0, 0, 255],
        "getTextAnchor": "middle",
        "getAlignmentBaseline": "center",
    }
    return {**defaults, **kwargs, "type": "TextLayer", "id": id,
            "data": _serialise_data(data)}

def column_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getPosition": "@@d",
        "getElevation": "@@d.elevation",
        "getFillColor": [255, 140, 0],
        "radius": 100,
        "extruded": True,
    }
    return {**defaults, **kwargs, "type": "ColumnLayer", "id": id,
            "data": _serialise_data(data)}

def polygon_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getPolygon": "@@d.polygon",
        "getFillColor": [0, 128, 255, 80],
        "getLineColor": [0, 0, 0, 200],
        "getLineWidth": 1,
        "extruded": False,
    }
    return {**defaults, **kwargs, "type": "PolygonLayer", "id": id,
            "data": _serialise_data(data)}

def heatmap_layer(id, data, **kwargs):
    defaults = {
        "getPosition": "@@d",
        "getWeight": 1,
        "radiusPixels": 30,
        "intensity": 1,
        "threshold": 0.05,
    }
    return {**defaults, **kwargs, "type": "HeatmapLayer", "id": id,
            "data": _serialise_data(data)}

def hexagon_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getPosition": "@@d",
        "radius": 1000,
        "elevationScale": 4,
        "extruded": True,
    }
    return {**defaults, **kwargs, "type": "HexagonLayer", "id": id,
            "data": _serialise_data(data)}

def h3_hexagon_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "getHexagon": "@@d.hex",
        "getFillColor": "@@d.color",
        "extruded": False,
    }
    return {**defaults, **kwargs, "type": "H3HexagonLayer", "id": id,
            "data": _serialise_data(data)}
```

**`__init__.py` exports**: Add all 10 new functions to imports and `__all__`.

**Tests**: 2 tests per helper (defaults check + kwargs override) = 20 tests.

---

### 5.4 GlobeView Helper

```python
def globe_view(**kwargs):
    """Return a GlobeView spec dict."""
    return {"@@type": "GlobeView", **kwargs}
```

Export from `__init__.py`. 1 test.

---

### 5.5 updateTriggers Documentation & Passthrough Validation

**No code change needed** — `updateTriggers` already passes through as a plain kwarg.
Add a test proving it works:

```python
def test_update_triggers_passthrough():
    spec = layer("ScatterplotLayer", "test", data=[],
                 getRadius="@@d.r",
                 updateTriggers={"getRadius": ["r_version"]})
    assert spec["updateTriggers"] == {"getRadius": ["r_version"]}
```

Document in `docs/api_reference.md` under a new "Advanced Props (Passthrough)" section.

---

## Phase 6: v0.8.0 — deck.gl Widgets & Layer Transitions

**Theme**: Bring deck.gl's native widget system into shiny_deckgl and add
first-class support for layer property transitions/animations.

**Estimated effort**: ~400 lines Python, ~250 lines JS, ~300 lines tests

### 6.1 deck.gl Widgets Support

**CDN change** (`_cdn.py`):

```python
DECKGL_WIDGETS_JS = (
    f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist.min.js"
)
DECKGL_WIDGETS_CSS = (
    f"https://cdn.jsdelivr.net/npm/@deck.gl/widgets@{DECKGL_VERSION}/dist/stylesheet.css"
)
```

Add to `CDN_HEAD_FRAGMENT` and `head_includes()`.

**Python API** (`components.py`):

```python
# Widget helper functions
def zoom_widget(placement: str = "top-right", **kwargs) -> dict:
    return {"@@widgetClass": "ZoomWidget", "placement": placement, **kwargs}

def compass_widget(placement: str = "top-right", **kwargs) -> dict:
    return {"@@widgetClass": "CompassWidget", "placement": placement, **kwargs}

def fullscreen_widget(placement: str = "top-right", **kwargs) -> dict:
    return {"@@widgetClass": "FullscreenWidget", "placement": placement, **kwargs}

def scale_widget(placement: str = "bottom-left", **kwargs) -> dict:
    return {"@@widgetClass": "ScaleWidget", "placement": placement, **kwargs}

def gimbal_widget(placement: str = "top-right", **kwargs) -> dict:
    return {"@@widgetClass": "GimbalWidget", "placement": placement, **kwargs}

def reset_view_widget(placement: str = "top-right", **kwargs) -> dict:
    return {"@@widgetClass": "ResetViewWidget", "placement": placement, **kwargs}

def screenshot_widget(placement: str = "top-right", **kwargs) -> dict:
    return {"@@widgetClass": "ScreenshotWidget", "placement": placement, **kwargs}

def fps_widget(placement: str = "top-left", **kwargs) -> dict:
    return {"@@widgetClass": "FpsWidget", "placement": placement, **kwargs}

def loading_widget(**kwargs) -> dict:
    return {"@@widgetClass": "LoadingWidget", **kwargs}

def timeline_widget(placement: str = "bottom-left", **kwargs) -> dict:
    return {"@@widgetClass": "TimelineWidget", "placement": placement, **kwargs}

def geocoder_widget(placement: str = "top-left", **kwargs) -> dict:
    return {"@@widgetClass": "GeocoderWidget", "placement": placement, **kwargs}

def theme_widget(**kwargs) -> dict:
    return {"@@widgetClass": "ThemeWidget", **kwargs}
```

**Python API** (`update()` method extension):

```python
async def update(self, session, layers, ..., widgets=None):
    payload = {"id": self.id, "layers": [_serialise_data(l) for l in layers]}
    if widgets is not None:
        payload["widgets"] = widgets
    ...
```

**JS change** — new `buildWidgets()` function:

```javascript
function buildWidgets(widgetSpecs) {
    if (!widgetSpecs || !deck.ZoomWidget) return undefined;
    return widgetSpecs.map(spec => {
        const className = spec['@@widgetClass'];
        delete spec['@@widgetClass'];
        const Cls = deck[className];
        if (!Cls) { console.warn('Unknown widget:', className); return null; }
        return new Cls(spec);
    }).filter(Boolean);
}
```

Wire into `deck_update` handler:

```javascript
if (msg.widgets) {
    overlay.setProps({ widgets: buildWidgets(msg.widgets) });
}
```

**New method** — `set_widgets()`:

```python
async def set_widgets(self, session: Session, widgets: list[dict]):
    """Update the deck.gl widget set without resending layers."""
    await session.send_custom_message("deck_set_widgets", {
        "id": self.id, "widgets": widgets
    })
```

**Tests**: 15+ tests covering each widget helper, `buildWidgets` serialization,
`set_widgets` message format.

---

### 6.2 Layer Property Transitions

**Problem**: deck.gl supports `transitions` dict on layers for smooth
attribute animations (e.g. `transitions: {getRadius: 1000}`). Currently passes
through but with no ergonomic Python API.

**Python API** (`components.py`):

```python
# Transition helper
def transition(duration: int = 1000, easing: str | None = None,
               type: str = "interpolation", **kwargs) -> dict:
    """
    Build a transition spec for a single layer property.

    transition(1000)  → {"duration": 1000, "type": "interpolation"}
    transition(type="spring", stiffness=0.05, damping=0.5)
    """
    spec = {"type": type, **kwargs}
    if type == "interpolation":
        spec["duration"] = duration
        if easing:
            spec["@@easing"] = easing
    return spec
```

**JS change** — resolve easing functions in `buildDeckLayers()`:

```javascript
// Inside the layer property walker, handle transitions.*.@@easing
if (spec.transitions) {
    for (const [prop, tSpec] of Object.entries(spec.transitions)) {
        if (tSpec && tSpec['@@easing']) {
            const easingName = tSpec['@@easing'];
            // Built-in easing functions
            const EASINGS = {
                'ease-in-cubic': t => t * t * t,
                'ease-out-cubic': t => 1 - Math.pow(1 - t, 3),
                'ease-in-out-cubic': t => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2,
                'ease-in-out-sine': t => -(Math.cos(Math.PI * t) - 1) / 2,
            };
            tSpec.easing = EASINGS[easingName] || (t => t);
            delete tSpec['@@easing'];
        }
    }
}
```

**Usage example**:

```python
from shiny_deckgl import layer, transition

my_layer = layer("ScatterplotLayer", "scatter", data=points,
    getPosition="@@d",
    getRadius="@@d.radius",
    getFillColor="@@d.color",
    transitions={
        "getRadius": transition(800, easing="ease-in-out-cubic"),
        "getFillColor": transition(500),
    }
)
```

**Tests**: 8 tests — transition dict generation, easing resolution, spring type,
passthrough in layer spec.

---

### 6.3 Camera Transition Interpolators

**Problem**: Only basic `flyTo` is supported. deck.gl offers `FlyToInterpolator`
with `speed` option and `LinearInterpolator` for property-restricted transitions.

**Python API**:

```python
async def fly_to(self, session: Session, longitude: float, latitude: float,
                 zoom: float | None = None, pitch: float | None = None,
                 bearing: float | None = None, speed: float = 1.2,
                 duration: int | str = "auto"):
    """Smooth fly-to camera transition using MapLibre flyTo."""
    view_state = {"longitude": longitude, "latitude": latitude}
    if zoom is not None: view_state["zoom"] = zoom
    if pitch is not None: view_state["pitch"] = pitch
    if bearing is not None: view_state["bearing"] = bearing
    await session.send_custom_message("deck_fly_to", {
        "id": self.id, "viewState": view_state,
        "speed": speed, "duration": duration,
    })

async def ease_to(self, session: Session, longitude: float, latitude: float,
                  zoom: float | None = None, pitch: float | None = None,
                  bearing: float | None = None, duration: int = 1000):
    """Smooth ease-to camera transition using MapLibre easeTo."""
    view_state = {"longitude": longitude, "latitude": latitude}
    if zoom is not None: view_state["zoom"] = zoom
    if pitch is not None: view_state["pitch"] = pitch
    if bearing is not None: view_state["bearing"] = bearing
    await session.send_custom_message("deck_ease_to", {
        "id": self.id, "viewState": view_state, "duration": duration,
    })
```

**JS handlers**:

```javascript
Shiny.addCustomMessageHandler("deck_fly_to", function(msg) {
    const entry = mapInstances[msg.id];
    if (!entry) return;
    const opts = {
        center: [msg.viewState.longitude, msg.viewState.latitude],
        speed: msg.speed || 1.2,
    };
    if (msg.viewState.zoom != null) opts.zoom = msg.viewState.zoom;
    if (msg.viewState.pitch != null) opts.pitch = msg.viewState.pitch;
    if (msg.viewState.bearing != null) opts.bearing = msg.viewState.bearing;
    if (msg.duration !== "auto") opts.duration = msg.duration;
    entry.map.flyTo(opts);
});

Shiny.addCustomMessageHandler("deck_ease_to", function(msg) {
    const entry = mapInstances[msg.id];
    if (!entry) return;
    const opts = {
        center: [msg.viewState.longitude, msg.viewState.latitude],
        duration: msg.duration || 1000,
    };
    if (msg.viewState.zoom != null) opts.zoom = msg.viewState.zoom;
    if (msg.viewState.pitch != null) opts.pitch = msg.viewState.pitch;
    if (msg.viewState.bearing != null) opts.bearing = msg.viewState.bearing;
    entry.map.easeTo(opts);
});
```

**Tests**: 6 tests — parameter assembly, default speed, "auto" duration, etc.

---

## Phase 7: v0.9.0 — Advanced Interaction & Events

**Theme**: Complete the event system, add box/multi-object picking, drag events,
data-load callbacks, and multi-view coordination.

**Estimated effort**: ~500 lines Python, ~300 lines JS, ~350 lines tests

### 7.1 Box Selection (pickObjects)

**Python API**:

```python
async def pick_objects(self, session: Session,
                       x: int, y: int,
                       width: int = 1, height: int = 1,
                       layer_ids: list[str] | None = None,
                       max_objects: int | None = None,
                       request_id: str = "pick_objects"):
    """
    Pick all objects within a bounding box on the screen.
    Results returned via input.{id}_pick_result.
    """
    await session.send_custom_message("deck_pick_objects", {
        "id": self.id,
        "x": x, "y": y, "width": width, "height": height,
        "layerIds": layer_ids,
        "maxObjects": max_objects,
        "requestId": request_id,
    })
```

**JS handler**:

```javascript
Shiny.addCustomMessageHandler("deck_pick_objects", function(msg) {
    const entry = mapInstances[msg.id];
    if (!entry) return;
    const results = entry.overlay._deck.pickObjects({
        x: msg.x, y: msg.y,
        width: msg.width || 1, height: msg.height || 1,
        layerIds: msg.layerIds || undefined,
        maxObjects: msg.maxObjects || undefined,
    });
    const cleaned = results.map(info => ({
        layerId: info.layer?.id,
        index: info.index,
        object: info.object,
        coordinate: info.coordinate,
    }));
    Shiny.setInputValue(msg.id + "_pick_result", {
        requestId: msg.requestId, objects: cleaned
    }, {priority: "event"});
});
```

**New input property**:

```python
@property
def pick_result_input_id(self) -> str:
    return f"{self.id}_pick_result"
```

**Tests**: 5 tests.

---

### 7.2 Multi-Object Picking (pickMultipleObjects)

```python
async def pick_multiple_objects(self, session: Session,
                                 x: int, y: int,
                                 radius: int = 0,
                                 layer_ids: list[str] | None = None,
                                 depth: int = 10,
                                 request_id: str = "pick_multi"):
    """Deep pick at a point, finding overlapping objects."""
    await session.send_custom_message("deck_pick_multiple", {
        "id": self.id,
        "x": x, "y": y, "radius": radius,
        "layerIds": layer_ids, "depth": depth,
        "requestId": request_id,
    })
```

**JS handler**: Similar to pickObjects but calls `overlay._deck.pickMultipleObjects()`.

**Tests**: 4 tests.

---

### 7.3 Layer Drag Events

**Problem**: deck.gl fires `onDragStart`, `onDrag`, `onDragEnd` on layers but
these are not sent back to Python.

**JS change** — wire drag events in `buildDeckLayers()`:

```javascript
// For non-raster, pickable layers:
if (spec.enableDragEvents) {
    layerProps.onDragStart = (info, event) => {
        Shiny.setInputValue(mapId + "_layer_drag", {
            event: "dragstart", layerId: spec.id,
            coordinate: info.coordinate, object: info.object
        }, {priority: "event"});
    };
    layerProps.onDrag = (info, event) => {
        Shiny.setInputValue(mapId + "_layer_drag", {
            event: "drag", layerId: spec.id,
            coordinate: info.coordinate
        }, {priority: "event"});
    };
    layerProps.onDragEnd = (info, event) => {
        Shiny.setInputValue(mapId + "_layer_drag", {
            event: "dragend", layerId: spec.id,
            coordinate: info.coordinate, object: info.object
        }, {priority: "event"});
    };
}
```

**Python**: Opt-in via `enableDragEvents=True` in layer spec. New input property:

```python
@property
def layer_drag_input_id(self) -> str:
    return f"{self.id}_layer_drag"
```

**Tests**: 4 tests.

---

### 7.4 Data Load Callback

```python
async def enable_data_load_events(self, session: Session, layer_ids: list[str]):
    """Enable onDataLoad callbacks for specified layer IDs."""
    await session.send_custom_message("deck_enable_data_events", {
        "id": self.id, "layerIds": layer_ids
    })
```

**JS**: For matching layer IDs during `buildDeckLayers()`, inject:

```javascript
layerProps.onDataLoad = (data, context) => {
    Shiny.setInputValue(mapId + "_data_load", {
        layerId: spec.id,
        count: Array.isArray(data) ? data.length : null,
        timestamp: Date.now()
    }, {priority: "event"});
};
```

**New input property**: `data_load_input_id`

**Tests**: 3 tests.

---

### 7.5 Multi-View ViewState

**Problem**: Can't set per-view camera states for multi-view setups.

**Python API**:

```python
async def set_view_state(self, session: Session,
                         view_states: dict[str, dict],
                         transition_duration: int = 0):
    """
    Set view state per view ID for multi-view setups.
    view_states={"main": {"longitude": -122, ...}, "minimap": {"longitude": -122, ...}}
    """
    await session.send_custom_message("deck_set_view_state", {
        "id": self.id,
        "viewStates": view_states,
        "transitionDuration": transition_duration,
    })
```

**JS**: Apply per-view `initialViewState` to the overlay.

**Tests**: 4 tests.

---

### 7.6 layerFilter

```python
async def set_layer_filter(self, session: Session,
                           rules: dict[str, list[str]]):
    """
    Set layer visibility rules per viewport.
    rules={"minimap": ["geofence"], "main": ["scatter", "heatmap"]}
    Meaning: in viewport "minimap", only show layers "geofence"; in "main",
    only show "scatter" and "heatmap".
    """
    await session.send_custom_message("deck_set_layer_filter", {
        "id": self.id, "rules": rules
    })
```

**JS handler**:

```javascript
Shiny.addCustomMessageHandler("deck_set_layer_filter", function(msg) {
    const entry = mapInstances[msg.id];
    if (!entry) return;
    entry._layerFilterRules = msg.rules;
    entry.overlay.setProps({
        layerFilter: ({layer, viewport}) => {
            const rules = entry._layerFilterRules;
            if (!rules || !rules[viewport.id]) return true;
            return rules[viewport.id].includes(layer.id);
        }
    });
});
```

**Tests**: 5 tests.

---

### 7.7 onViewStateChange Events

**Problem**: Only `moveend` fires. Some apps need real-time viewport tracking
(e.g. for linked views).

```python
async def enable_viewstate_stream(self, session: Session,
                                   throttle_ms: int = 100):
    """
    Enable real-time view state streaming (throttled).
    Events fire to input.{id}_view_state_stream.
    """
    await session.send_custom_message("deck_viewstate_stream", {
        "id": self.id, "throttleMs": throttle_ms
    })
```

**JS**: Add throttled `move` event listener on the MapLibre map.

**Tests**: 3 tests.

---

## Phase 8: v0.10.0 — Performance, Binary & Advanced Layers

**Theme**: Optimize for large datasets with Arrow/binary transport,
add custom renderSubLayers support, and handle advanced layer patterns.

**Estimated effort**: ~500 lines Python, ~200 lines JS, ~300 lines tests

### 8.1 Arrow / Columnar Binary Transport

**Problem**: Currently binary transport is per-attribute via base64 + TypedArrays.
For large datasets (100K+ points), sending a full GeoJSON or list-of-dicts is
slow. Arrow-style columnar transport would be more efficient.

**Python API**:

```python
def encode_columnar_data(df, position_columns=("longitude", "latitude"),
                          columns=None) -> dict:
    """
    Encode a DataFrame into columnar binary format for efficient transport.

    Returns a dict with:
    {
        "@@columnar": True,
        "length": N,
        "attributes": {
            "getPosition": {"@@binary": True, "dtype": "float64", "size": 2, "value": ...},
            "getRadius": {"@@binary": True, "dtype": "float32", "size": 1, "value": ...},
            ...
        }
    }
    """
```

**JS change**: Detect `@@columnar` marker in `buildDeckLayers()` and set up the
layer's `data` property with `{length, attributes}` format that deck.gl
natively supports for binary columnar data.

**Tests**: 8 tests with numpy arrays.

---

### 8.2 Custom renderSubLayers

**Problem**: Only `@@BitmapLayer` shorthand exists. Users can't specify custom
sublayer rendering for TileLayer, MVTLayer, etc.

**Extended JS syntax**:

```javascript
// Python sends:
// "renderSubLayers": {"@@sublayer": "GeoJsonLayer", "props": {...}}
//
// JS resolves to:
// renderSubLayers: (props) => new deck.GeoJsonLayer({...props, ...userProps})
```

**Python helper**:

```python
def sublayer_renderer(type: str, **kwargs) -> dict:
    """
    Create a renderSubLayers spec for TileLayer/MVTLayer.

    Usage:
        tile_layer("tiles", url,
            renderSubLayers=sublayer_renderer("GeoJsonLayer",
                getFillColor=[255, 0, 0],
                getLineWidth=2))
    """
    return {"@@sublayer": type, "props": kwargs}
```

**Tests**: 5 tests.

---

### 8.3 Terrain Layer Helper

```python
def terrain_layer(id, elevation_data, texture=None, **kwargs):
    defaults = {
        "elevationDecoder": {"rScaler": 256, "gScaler": 1, "bScaler": 1/256, "offset": -32768},
        "meshMaxError": 4.0,
    }
    spec = {**defaults, **kwargs, "type": "TerrainLayer", "id": id,
            "elevationData": elevation_data}
    if texture:
        spec["texture"] = texture
    return spec
```

---

### 8.4 MVT Layer Helper

```python
def mvt_layer(id, data, **kwargs):
    defaults = {
        "pickable": True,
        "minZoom": 0,
        "maxZoom": 14,
        "getLineColor": [0, 0, 0, 200],
        "getFillColor": [200, 200, 200, 100],
        "getLineWidth": 1,
        "lineWidthMinPixels": 1,
    }
    return {**defaults, **kwargs, "type": "MVTLayer", "id": id,
            "data": data}
```

---

### 8.5 Trips Layer Helper + Animation Loop

```python
def trips_layer(id, data, **kwargs):
    defaults = {
        "getPath": "@@d.path",
        "getTimestamps": "@@d.timestamps",
        "getColor": [253, 128, 93],
        "getWidth": 5,
        "trailLength": 200,
        "currentTime": 0,
    }
    return {**defaults, **kwargs, "type": "TripsLayer", "id": id,
            "data": _serialise_data(data)}

async def animate_trips(self, session: Session, layer_id: str,
                         time_range: tuple[float, float],
                         duration_ms: int = 10000,
                         loop: bool = True):
    """
    Start client-side animation of a TripsLayer's currentTime.
    Animation runs entirely in the browser for smooth 60fps.
    """
    await session.send_custom_message("deck_animate_trips", {
        "id": self.id,
        "layerId": layer_id,
        "timeRange": list(time_range),
        "durationMs": duration_ms,
        "loop": loop,
    })

async def stop_trips_animation(self, session: Session, layer_id: str):
    """Stop a running TripsLayer animation."""
    await session.send_custom_message("deck_stop_trips_animation", {
        "id": self.id, "layerId": layer_id,
    })
```

**JS handler**: Uses `requestAnimationFrame` to update the TripsLayer's
`currentTime` prop on the overlay, enabling smooth browser-side animation
without round-trips to Python.

**Tests**: 6 tests.

---

### 8.6 WMS Layer Helper

```python
def wms_layer(id, data, service_url, layers, **kwargs):
    """
    Convenience for OGC WMS tile layers.
    Automatically constructs GetMap URL with {bbox-epsg-3857} placeholder.
    """
    defaults = {
        "minZoom": 0,
        "maxZoom": 19,
        "tileSize": 256,
    }
    if "?" not in data:
        # Build WMS GetMap URL
        data = (f"{service_url}?service=WMS&version=1.1.1&request=GetMap"
                f"&layers={layers}&srs=EPSG:3857"
                f"&bbox={{bbox-epsg-3857}}&width=256&height=256&format=image/png"
                f"&transparent=true")
    return {**defaults, **kwargs, "type": "TileLayer", "id": id,
            "data": data, "renderSubLayers": "@@BitmapLayer"}
```

**Tests**: 3 tests.

---

## Phase 9: v0.11.0 — Developer Experience & Documentation

**Theme**: Polish the API surface, add comprehensive docs, gallery examples,
type stubs, and linting.

**Estimated effort**: ~300 lines Python, ~50 lines JS, ~200 lines tests,
significant documentation

### 9.1 Type Stubs / Type Hints

Add comprehensive type hints throughout:

```python
from __future__ import annotations
from typing import Any, Literal

Position = Literal["top-left", "top-right", "bottom-left", "bottom-right"]
ControlType = Literal["navigation", "scale", "fullscreen", "geolocate",
                       "globe", "terrain", "attribution"]
LayerSpec = dict[str, Any]
ViewSpec = dict[str, Any]
WidgetSpec = dict[str, Any]
EffectSpec = dict[str, Any]
TransitionSpec = dict[str, Any]
ColorRGBA = list[int] | tuple[int, ...]
```

Use these types consistently in all function signatures. Add `py.typed` marker file.

---

### 9.2 Input Property Convenience

Add a single `inputs` property that returns all input IDs as a named dict:

```python
@property
def inputs(self) -> dict[str, str]:
    """All Shiny input IDs for this widget."""
    return {
        "click": self.click_input_id,
        "hover": self.hover_input_id,
        "view_state": self.view_state_input_id,
        "map_click": self.map_click_input_id,
        "map_contextmenu": self.map_contextmenu_input_id,
        "feature_click": self.feature_click_input_id,
        "query_result": self.query_result_input_id,
        "marker_click": self.marker_click_input_id,
        "marker_drag": self.marker_drag_input_id,
        "drawn_features": self.drawn_features_input_id,
        "draw_mode": self.draw_mode_input_id,
        "export_result": self.export_result_input_id,
        "has_image": self.has_image_input_id,
        "drag": self.drag_input_id,
        # v0.9.0+
        "pick_result": self.pick_result_input_id,
        "layer_drag": self.layer_drag_input_id,
        "data_load": self.data_load_input_id,
    }
```

---

### 9.3 Gallery Examples

Create an `examples/` directory with self-contained demo apps:

```
examples/
├── 01_basic_scatterplot.py      # Minimal ScatterplotLayer example
├── 02_geojson_choropleth.py     # GeoJSON layer with color_quantiles
├── 03_arc_connections.py        # ArcLayer with tooltip
├── 04_heatmap.py                # HeatmapLayer from CSV
├── 05_hexagon_3d.py             # HexagonLayer extruded
├── 06_icon_markers.py           # IconLayer with atlas
├── 07_wms_tiles.py              # WMS tile overlay
├── 08_mvt_vector_tiles.py       # MVTLayer from PMTiles
├── 09_trips_animation.py        # TripsLayer with browser animation
├── 10_globe_view.py             # GlobeView with satellite tiles
├── 11_terrain_3d.py             # TerrainLayer + sky
├── 12_multi_view.py             # Split screen with layerFilter
├── 13_drawing_tools.py          # MapboxDraw integration
├── 14_binary_large_data.py      # 100K points with binary transport
├── 15_data_filter.py            # DataFilterExtension slider
├── 16_brushing.py               # BrushingExtension interaction
├── 17_collision_labels.py       # CollisionFilterExtension for labels
├── 18_native_maplibre.py        # Native sources + layers + popups
├── 19_widgets_showcase.py       # deck.gl widgets demo
├── 20_marine_dashboard.py       # Full marine science dashboard
```

Each example: ~50-100 lines, self-contained, runnable with `shiny run`.

---

### 9.4 Comprehensive API Reference

Rewrite `docs/api_reference.md` to include:

- Every public function with full parameter docs
- Every MapWidget method with usage examples
- Every input property with event payload format
- All layer helpers with default values
- All widget helpers
- All view helpers
- Extension usage with constructor options
- Binary transport guide
- Transition/animation guide
- Advanced patterns (multi-view, layerFilter, etc.)

---

### 9.5 Contributing Guide

Create `CONTRIBUTING.md`:

- Development setup (micromamba, editable install)
- Test running instructions
- Architecture overview
- Adding a new layer helper checklist
- Adding a new JS handler checklist
- Code style conventions

---

## Phase 10: v1.0.0 — Stability, Testing & Release

**Theme**: Comprehensive test coverage, backwards compatibility guarantees,
CI/CD pipeline, PyPI release.

**Estimated effort**: ~200 lines Python, ~100 lines JS, ~500 lines tests,
CI config

### 10.1 Test Coverage Target: 95%+

Current: 310 tests. Target: ~500+ tests.

| Area | Current Tests | Target Tests |
|------|---------------|--------------|
| Layer helpers | ~20 | ~50 |
| Widget helpers | 0 | ~30 |
| Extension options | 0 | ~15 |
| Deck-level props | 0 | ~20 |
| Transitions | 0 | ~15 |
| Camera methods | ~10 | ~25 |
| Picking (box/multi) | 0 | ~15 |
| Drag events | 0 | ~10 |
| Multi-view | 0 | ~10 |
| layerFilter | 0 | ~10 |
| Binary transport | ~10 | ~25 |
| Serialization | ~10 | ~20 |
| Color utilities | ~10 | ~15 |
| Edge cases / regression | ~20 | ~40 |

---

### 10.2 Integration Tests

Create `tests/test_integration.py` with Playwright-based browser tests:

```python
# Uses shiny's test infrastructure
# Launches actual Shiny app, connects via WebSocket
# Verifies map renders, layers display, events fire

class TestMapRendering:
    def test_map_initializes(self, page):
        """Map canvas appears with correct dimensions."""

    def test_layer_renders(self, page):
        """ScatterplotLayer dots are visible on canvas."""

    def test_click_event(self, page):
        """Clicking on a layer fires input event."""

    def test_tooltip_displays(self, page):
        """Hovering shows tooltip with correct content."""

    def test_export_image(self, page):
        """export_image returns valid PNG data URI."""
```

---

### 10.3 CI/CD Pipeline

Create `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: mamba-org/setup-micromamba@v2
        with:
          environment-name: test
          create-args: >-
            python=${{ matrix.python-version }}
            shiny htmltools geopandas numpy shapely
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --tb=short --cov=shiny_deckgl --cov-report=xml
      - uses: codecov/codecov-action@v4

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/shiny_deckgl/

  build:
    runs-on: ubuntu-latest
    needs: [test, lint]
    steps:
      - uses: actions/checkout@v4
      - run: pip install build
      - run: python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

---

### 10.4 PyPI Release Automation

Create `.github/workflows/release.yml`:

```yaml
name: Release to PyPI
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

---

### 10.5 Backwards Compatibility

- All v0.1–v0.6 API preserved exactly
- New parameters always have defaults matching previous behaviour
- Deprecation warnings for any renamed methods (none expected)
- `__all__` grows but never shrinks

---

### 10.6 Performance Benchmarks

Create `benchmarks/` directory:

```
benchmarks/
├── bench_binary_encode.py     # Time encoding 100K/1M points
├── bench_layer_serialize.py   # Time serializing complex layer specs
├── bench_geodataframe.py      # Time GeoDataFrame → GeoJSON conversion
└── bench_color_utils.py       # Time color_range/bins/quantiles with large data
```

---

## Summary: Release Timeline

| Version | Theme | Key Deliverables | New Tests |
|---------|-------|-----------------|-----------|
| **v0.7.0** | Extensions, DeckProps & Helpers | Extension args, 10 layer helpers, Deck props, globe_view | ~50 |
| **v0.8.0** | Widgets & Transitions | 12 deck.gl widget helpers, layer transitions, fly_to/ease_to | ~30 |
| **v0.9.0** | Advanced Interaction | Box pick, multi-pick, drag events, layerFilter, multi-view | ~30 |
| **v0.10.0** | Performance & Advanced Layers | Columnar binary, custom sublayers, TripsLayer animation, WMS/MVT/Terrain helpers | ~30 |
| **v0.11.0** | Developer Experience | Type stubs, gallery examples, API docs, contributing guide | ~20 |
| **v1.0.0** | Stability & Release | 95%+ coverage, integration tests, CI/CD, PyPI publishing, benchmarks | ~50 |

**Total new features**: ~60 new functions/methods, ~16 new JS handlers,
~50 new exports, 20 gallery examples.

**Total new tests**: ~210 (bringing total from 310 to ~520).

---

## Appendix A: Complete Exports After v1.0.0

```python
__all__ = [
    # Core
    "app", "MapWidget", "head_includes",
    # Basemap styles
    "CARTO_POSITRON", "CARTO_DARK", "CARTO_VOYAGER", "OSM_LIBERTY",
    # Layer helpers (generic)
    "layer",
    # Layer helpers (convenience) — 14 total
    "scatterplot_layer", "geojson_layer", "tile_layer", "bitmap_layer",
    "arc_layer", "icon_layer", "path_layer", "line_layer",
    "text_layer", "column_layer", "polygon_layer",
    "heatmap_layer", "hexagon_layer", "h3_hexagon_layer",
    # Advanced layer helpers
    "mvt_layer", "terrain_layer", "trips_layer", "wms_layer",
    # View helpers
    "map_view", "orthographic_view", "first_person_view", "globe_view",
    # Widget helpers (deck.gl widgets)
    "zoom_widget", "compass_widget", "fullscreen_widget", "scale_widget",
    "gimbal_widget", "reset_view_widget", "screenshot_widget",
    "fps_widget", "loading_widget", "timeline_widget",
    "geocoder_widget", "theme_widget",
    # Color utilities
    "color_range", "color_bins", "color_quantiles",
    "PALETTE_VIRIDIS", "PALETTE_PLASMA", "PALETTE_OCEAN",
    "PALETTE_THERMAL", "PALETTE_CHLOROPHYLL",
    # Binary transport
    "encode_binary_attribute", "encode_columnar_data",
    # Transitions
    "transition",
    # Sublayer rendering
    "sublayer_renderer",
    # Constants
    "CONTROL_TYPES", "CONTROL_POSITIONS",
]
```

---

## Appendix B: Complete MapWidget Methods After v1.0.0

```
Core:           update, set_layer_visibility, set_style, update_tooltip
Camera:         fly_to, ease_to, fit_bounds
Controls:       add_control, remove_control, set_controller
Sources:        add_source, remove_source, set_source_data
Images:         add_image, remove_image, has_image
Native layers:  add_maplibre_layer, remove_maplibre_layer
Style mutation:  set_paint_property, set_layout_property, set_filter
Globe/terrain:  set_projection, set_terrain, set_sky
Popups:         add_popup, remove_popup
Queries:        query_rendered_features, query_at_lnglat
Picking:        pick_objects, pick_multiple_objects
Markers:        add_marker, remove_marker, clear_markers, add_drag_marker
Drawing:        enable_draw, disable_draw, get_drawn_features, delete_drawn_features
GeoPandas:      add_geodataframe, update_geodataframe
Feature state:  set_feature_state, remove_feature_state
Export:         export_image, to_json, from_json, to_html
Widgets:        set_widgets
Multi-view:     set_view_state, set_layer_filter
Events:         enable_data_load_events, enable_viewstate_stream
Animation:      animate_trips, stop_trips_animation
```

**Total**: ~52 async methods + 6 non-async methods.

---

## Appendix C: JS Handler Count After v1.0.0

Current: 36 handlers → Target: ~50 handlers.

New handlers:
```
deck_fly_to, deck_ease_to, deck_set_controller,
deck_set_widgets, deck_pick_objects, deck_pick_multiple,
deck_enable_data_events, deck_set_view_state, deck_set_layer_filter,
deck_viewstate_stream, deck_animate_trips, deck_stop_trips_animation,
deck_set_deck_props
```
