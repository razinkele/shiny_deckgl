# shiny_deckgl — Detailed Implementation Plan

> Code-level blueprint for v0.2.0 through v0.5.0
> Companion to ROADMAP.md — each feature includes exact file changes,
> function signatures, JS handler code, and test patterns.

---

## Architecture Reference

### Current Communication Pattern

**Python → JS** (5 channels):
```
MapWidget method → session.send_custom_message(channel, payload)
    → Shiny delivers JSON to browser
    → Shiny.addCustomMessageHandler(channel, callback) in deckgl-init.js
```

**JS → Python** (4 inputs):
```
map events → Shiny.setInputValue(mapId + "_suffix", data)
    → input.{mapId}_{suffix}() in server
```

### Files Touched by Every New Feature

| File | What changes |
|------|-------------|
| `src/shiny_deckgl/components.py` | New `async def` method on `MapWidget` |
| `src/shiny_deckgl/resources/deckgl-init.js` | New `Shiny.addCustomMessageHandler(...)` |
| `src/shiny_deckgl/__init__.py` | Export new symbols if any |
| `tests/test_basic.py` | New test class with `FakeSession` pattern |

### FakeSession Test Pattern (reused everywhere)
```python
import asyncio

class FakeSession:
    def __init__(self):
        self.messages = []
    async def send_custom_message(self, handler, payload):
        self.messages.append((handler, payload))

fake = FakeSession()
asyncio.run(widget.some_method(fake, ...))
assert fake.messages[0] == ("channel_name", {...})
```

---

## Phase 1: v0.2.0 — Foundation

### 1.1 Upgrade MapLibre GL JS v3.6.2 → v5.3

**Why**: Enables globe projection, 3D terrain improvements, cooperative gestures,
GlobeControl/TerrainControl, `queryTerrainElevation()`, Sky API. Two major
versions behind is a liability.

#### Files Changed

**`src/shiny_deckgl/ui.py`** — Change 2 CDN URLs in `head_includes()`:
```python
# BEFORE (lines 39-41):
head=(
    '<script src="https://cdn.jsdelivr.net/npm/deck.gl@9.1.4/dist.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>\n'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/dist/maplibre-gl.css"/>'
),

# AFTER:
head=(
    '<script src="https://cdn.jsdelivr.net/npm/deck.gl@9.1.4/dist.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.js"></script>\n'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.css"/>'
),
```

**`src/shiny_deckgl/components.py`** — Change 2 CDN URLs in `to_html()`:
```python
# BEFORE (lines ~644-646):
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/dist/maplibre-gl.css"/>

# AFTER:
<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.css"/>
```

#### Compatibility Verification Checklist
- [ ] `MapboxOverlay` from `@deck.gl/mapbox` still works with MapLibre v5
- [ ] `maplibregl.NavigationControl()` API unchanged
- [ ] `maplibregl.Marker({draggable: true})` API unchanged
- [ ] `map.flyTo()`, `map.jumpTo()` API unchanged
- [ ] `map.setStyle()` API unchanged
- [ ] `map.getCenter()`, `map.getZoom()`, etc. — same return types
- [ ] CSS class `.maplibregl-map`, `.maplibregl-ctrl` — verify no regressions
- [ ] All 101 existing tests still pass

#### Risk Mitigation
deck.gl v9.1.4 officially supports MapLibre GL JS v3.x. MapLibre v5 changed
internal WebGL handling. If `MapboxOverlay` breaks:
1. Check `@deck.gl/mapbox@9.1.x` release notes
2. Try deck.gl v9.1.7+ (may have v5 patches)
3. Worst case: pin `maplibre-gl@4.7.1` (last v4)

#### Tests
```python
class TestMapLibreVersion:
    def test_head_includes_maplibre_v5(self):
        dep = head_includes()
        # HTMLDependency.head is a string with CDN tags
        assert "maplibre-gl@5.3" in str(dep._head)

    def test_to_html_maplibre_v5(self):
        w = MapWidget("v5test")
        html = w.to_html([])
        assert "maplibre-gl@5.3" in html
        assert "maplibre-gl@3.6" not in html
```

---

### 1.2 Map Controls API

**Why**: ScaleControl is essential for scientific maps. FullscreenControl and
GeolocateControl improve UX. Currently only NavigationControl is added
(hardcoded).

#### Python API — `components.py`

Add two new methods to `MapWidget`:

```python
# Valid control types
CONTROL_TYPES = {
    "navigation", "scale", "fullscreen", "geolocate",
    "globe", "terrain", "attribution",
}
CONTROL_POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right"}

async def add_control(
    self,
    session,
    control_type: str,
    position: str = "top-right",
    *,
    options: dict | None = None,
) -> None:
    """Add a MapLibre control to the map.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    control_type
        One of: ``"navigation"``, ``"scale"``, ``"fullscreen"``,
        ``"geolocate"``, ``"globe"``, ``"terrain"``, ``"attribution"``.
    position
        Corner position: ``"top-left"``, ``"top-right"`` (default),
        ``"bottom-left"``, ``"bottom-right"``.
    options
        Optional dict of control-specific options, e.g.
        ``{"maxWidth": 200, "unit": "metric"}`` for ScaleControl,
        ``{"source": "terrain-dem", "exaggeration": 1.5}`` for TerrainControl.
    """
    if control_type not in CONTROL_TYPES:
        raise ValueError(
            f"Unknown control type {control_type!r}. "
            f"Valid types: {sorted(CONTROL_TYPES)}"
        )
    if position not in CONTROL_POSITIONS:
        raise ValueError(
            f"Unknown position {position!r}. "
            f"Valid positions: {sorted(CONTROL_POSITIONS)}"
        )
    await session.send_custom_message("deck_add_control", {
        "id": self.id,
        "controlType": control_type,
        "position": position,
        "options": options or {},
    })


async def remove_control(
    self,
    session,
    control_type: str,
) -> None:
    """Remove a previously added MapLibre control.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    control_type
        The control type string to remove (e.g. ``"scale"``).
    """
    await session.send_custom_message("deck_remove_control", {
        "id": self.id,
        "controlType": control_type,
    })
```

#### JS Handler — `deckgl-init.js`

**Modify `initMap()`**: Store controls in instance so they can be removed later.
```javascript
// In initMap(), change:
map.addControl(new maplibregl.NavigationControl(), 'top-right');

// To:
var navControl = new maplibregl.NavigationControl();
map.addControl(navControl, 'top-right');

// And extend the instance object:
mapInstances[mapId] = {
    map: map,
    overlay: overlay,
    tooltipConfig: tooltipConfig,
    dragMarker: null,
    lastLayers: [],
    controls: { navigation: { control: navControl, position: 'top-right' } }
};
```

**New handler `deck_add_control`**:
```javascript
// -----------------------------------------------------------------------
// deck_add_control — add a MapLibre control
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_add_control", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var type = payload.controlType;
    var position = payload.position || 'top-right';
    var opts = payload.options || {};

    // Remove existing control of same type first
    if (instance.controls[type]) {
        map.removeControl(instance.controls[type].control);
        delete instance.controls[type];
    }

    var control;
    switch (type) {
        case 'navigation':
            control = new maplibregl.NavigationControl(opts);
            break;
        case 'scale':
            control = new maplibregl.ScaleControl(opts);
            break;
        case 'fullscreen':
            control = new maplibregl.FullscreenControl(opts);
            break;
        case 'geolocate':
            control = new maplibregl.GeolocateControl(Object.assign({
                positionOptions: { enableHighAccuracy: true },
                trackUserLocation: false
            }, opts));
            break;
        case 'globe':
            // MapLibre v5+ only
            if (maplibregl.GlobeControl) {
                control = new maplibregl.GlobeControl(opts);
            } else {
                console.warn('[shiny_deckgl] GlobeControl requires MapLibre v5+');
                return;
            }
            break;
        case 'terrain':
            // MapLibre v5+ only
            if (maplibregl.TerrainControl) {
                control = new maplibregl.TerrainControl(opts);
            } else {
                console.warn('[shiny_deckgl] TerrainControl requires MapLibre v5+');
                return;
            }
            break;
        case 'attribution':
            control = new maplibregl.AttributionControl(opts);
            break;
        default:
            console.warn('[shiny_deckgl] Unknown control type: ' + type);
            return;
    }

    map.addControl(control, position);
    instance.controls[type] = { control: control, position: position };
});
```

**New handler `deck_remove_control`**:
```javascript
// -----------------------------------------------------------------------
// deck_remove_control — remove a MapLibre control
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_remove_control", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var type = payload.controlType;
    if (instance.controls[type]) {
        instance.map.removeControl(instance.controls[type].control);
        delete instance.controls[type];
    }
});
```

#### Constructor Parameter (optional enhancement)

Add `controls` parameter to `MapWidget.__init__()` for initial controls:
```python
def __init__(
    self,
    id: str,
    view_state: dict | None = None,
    style: str = CARTO_POSITRON,
    tooltip: dict | None = None,
    mapbox_api_key: str | None = None,
    controls: list[dict] | None = None,  # NEW
):
    ...
    self.controls = controls or [
        {"type": "navigation", "position": "top-right"},
    ]
```

Add `data-controls` attribute in `ui()` method:
```python
if self.controls:
    attrs["data_controls"] = json.dumps(self.controls)
```

Read and apply in `initMap()`:
```javascript
// Parse controls config
var controlsConfig = [];
if (el.dataset.controls) {
    try { controlsConfig = JSON.parse(el.dataset.controls); } catch (_) {}
}
// Apply each control from config
controlsConfig.forEach(function(cfg) {
    // ... same switch logic as deck_add_control handler
});
```

#### Tests
```python
class TestAddControl:
    def test_add_control_scale(self):
        import asyncio
        w = MapWidget("ctrl1")
        fake = FakeSession()
        asyncio.run(w.add_control(fake, "scale", "bottom-left"))
        assert fake.messages[0] == ("deck_add_control", {
            "id": "ctrl1",
            "controlType": "scale",
            "position": "bottom-left",
            "options": {},
        })

    def test_add_control_with_options(self):
        import asyncio
        w = MapWidget("ctrl2")
        fake = FakeSession()
        asyncio.run(w.add_control(fake, "scale", "bottom-left",
                                   options={"maxWidth": 200, "unit": "metric"}))
        assert fake.messages[0][1]["options"] == {"maxWidth": 200, "unit": "metric"}

    def test_add_control_invalid_type_raises(self):
        import asyncio, pytest
        w = MapWidget("ctrl3")
        fake = FakeSession()
        with pytest.raises(ValueError, match="Unknown control type"):
            asyncio.run(w.add_control(fake, "invalid"))

    def test_add_control_invalid_position_raises(self):
        import asyncio, pytest
        w = MapWidget("ctrl4")
        fake = FakeSession()
        with pytest.raises(ValueError, match="Unknown position"):
            asyncio.run(w.add_control(fake, "scale", "middle"))

    def test_remove_control(self):
        import asyncio
        w = MapWidget("ctrl5")
        fake = FakeSession()
        asyncio.run(w.remove_control(fake, "navigation"))
        assert fake.messages[0] == ("deck_remove_control", {
            "id": "ctrl5",
            "controlType": "navigation",
        })
```

---

### 1.3 `fit_bounds()` Method

**Why**: "Zoom to study area" is the most common operation in marine GIS apps.
Currently requires manually computing a view state with matching zoom level.

#### Python API — `components.py`

```python
async def fit_bounds(
    self,
    session,
    bounds: list[list[float]],
    *,
    padding: int | dict[str, int] = 50,
    max_zoom: float | None = None,
    duration: int = 0,
) -> None:
    """Fly/jump the map to fit the given bounds.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    bounds
        ``[[sw_lng, sw_lat], [ne_lng, ne_lat]]`` in WGS 84.
        Example: ``[[10.0, 54.0], [30.0, 66.0]]`` for the Baltic Sea.
    padding
        Pixels of padding around the bounds. Can be an ``int`` (uniform)
        or a dict ``{"top": 10, "bottom": 10, "left": 10, "right": 10}``.
    max_zoom
        Maximum zoom level to use (prevents over-zooming on small areas).
    duration
        Animation duration in milliseconds. ``0`` (default) = instant.
    """
    payload: dict = {
        "id": self.id,
        "bounds": bounds,
        "padding": padding,
    }
    if max_zoom is not None:
        payload["maxZoom"] = max_zoom
    if duration > 0:
        payload["duration"] = duration
    await session.send_custom_message("deck_fit_bounds", payload)
```

#### JS Handler — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_fit_bounds — fit map to geographic bounds
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_fit_bounds", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var bounds = payload.bounds;  // [[sw_lng, sw_lat], [ne_lng, ne_lat]]
    var opts = {};

    if (payload.padding != null) {
        opts.padding = payload.padding;
    }
    if (payload.maxZoom != null) {
        opts.maxZoom = payload.maxZoom;
    }
    if (payload.duration != null && payload.duration > 0) {
        opts.duration = payload.duration;
    } else {
        opts.duration = 0;  // instant
    }

    instance.map.fitBounds(bounds, opts);
});
```

#### Convenience: `fit_bounds_from_data()`

Optional helper that computes bounds from a GeoJSON feature collection:
```python
@staticmethod
def compute_bounds(geojson: dict) -> list[list[float]]:
    """Compute [[sw_lng, sw_lat], [ne_lng, ne_lat]] from GeoJSON."""
    coords = []
    def _extract(geom):
        if geom["type"] == "Point":
            coords.append(geom["coordinates"][:2])
        elif geom["type"] in ("MultiPoint", "LineString"):
            coords.extend(c[:2] for c in geom["coordinates"])
        elif geom["type"] in ("MultiLineString", "Polygon"):
            for ring in geom["coordinates"]:
                coords.extend(c[:2] for c in ring)
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                for ring in poly:
                    coords.extend(c[:2] for c in ring)
        elif geom["type"] == "GeometryCollection":
            for g in geom["geometries"]:
                _extract(g)

    if geojson.get("type") == "FeatureCollection":
        for f in geojson["features"]:
            if f.get("geometry"):
                _extract(f["geometry"])
    elif geojson.get("type") == "Feature":
        if geojson.get("geometry"):
            _extract(geojson["geometry"])
    elif geojson.get("type"):
        _extract(geojson)

    if not coords:
        return [[-180, -90], [180, 90]]

    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [[min(lngs), min(lats)], [max(lngs), max(lats)]]
```

#### Tests
```python
class TestFitBounds:
    def test_fit_bounds_basic(self):
        import asyncio
        w = MapWidget("fb1")
        fake = FakeSession()
        asyncio.run(w.fit_bounds(fake, [[10, 54], [30, 66]]))
        msg = fake.messages[0]
        assert msg[0] == "deck_fit_bounds"
        assert msg[1]["bounds"] == [[10, 54], [30, 66]]
        assert msg[1]["padding"] == 50

    def test_fit_bounds_with_options(self):
        import asyncio
        w = MapWidget("fb2")
        fake = FakeSession()
        asyncio.run(w.fit_bounds(fake, [[10, 54], [30, 66]],
                                  padding={"top": 20, "bottom": 20, "left": 10, "right": 10},
                                  max_zoom=12, duration=1000))
        msg = fake.messages[0][1]
        assert msg["maxZoom"] == 12
        assert msg["duration"] == 1000
        assert msg["padding"]["top"] == 20

    def test_compute_bounds_feature_collection(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10, 50]}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [30, 60]}},
            ]
        }
        bounds = MapWidget.compute_bounds(geojson)
        assert bounds == [[10, 50], [30, 60]]

    def test_compute_bounds_empty(self):
        bounds = MapWidget.compute_bounds({"type": "FeatureCollection", "features": []})
        assert bounds == [[-180, -90], [180, 90]]
```

---

### 1.4 Map Bounds Feedback

**Why**: Enables "load data for visible area" — a critical pattern for marine
data portals where datasets cover entire ocean basins but the user only
needs data in the current viewport.

#### JS Change — `deckgl-init.js`

Extend the existing `moveend` handler (currently at ~line 92):
```javascript
// BEFORE:
map.on('moveend', function () {
    const center = map.getCenter();
    Shiny.setInputValue(mapId + '_view_state', {
        longitude: center.lng,
        latitude: center.lat,
        zoom: map.getZoom(),
        pitch: map.getPitch(),
        bearing: map.getBearing()
    });
});

// AFTER:
map.on('moveend', function () {
    var center = map.getCenter();
    var bounds = map.getBounds();
    Shiny.setInputValue(mapId + '_view_state', {
        longitude: center.lng,
        latitude: center.lat,
        zoom: map.getZoom(),
        pitch: map.getPitch(),
        bearing: map.getBearing(),
        bounds: {
            sw: [bounds.getSouthWest().lng, bounds.getSouthWest().lat],
            ne: [bounds.getNorthEast().lng, bounds.getNorthEast().lat]
        }
    });
});
```

#### Python Property — `components.py`

Add a property to `MapWidget` for documentation clarity:
```python
@property
def bounds_input_id(self) -> str:
    """The Shiny input name for the current viewport bounds.

    The view state input now includes a ``bounds`` key with
    ``{"sw": [lng, lat], "ne": [lng, lat]}``.
    Access via ``input.{id}_view_state()["bounds"]``.
    """
    return f"{self.id}_view_state"
```

#### Usage Example
```python
@reactive.Effect
@reactive.event(input.my_map_view_state)
def on_view_change():
    vs = input.my_map_view_state()
    bounds = vs.get("bounds")
    if bounds:
        sw_lng, sw_lat = bounds["sw"]
        ne_lng, ne_lat = bounds["ne"]
        # Query database for data within these bounds
        filtered = load_stations_in_bbox(sw_lng, sw_lat, ne_lng, ne_lat)
```

#### Tests
No new Python methods to test — this is purely a JS-side change. Verify
manually that `input.{id}_view_state()` now includes a `bounds` key.

---

### 1.5 Map Click Events (MapLibre-level)

**Why**: Currently, deck.gl layer clicks send `{mapId}_click` with the picked
layer object. But clicking on an *empty* area of the map sends nothing.
Marine apps need "click anywhere to get coordinates" (e.g., for placing
stations, drawing transects, querying WMS GetFeatureInfo).

#### JS Change — `deckgl-init.js`

Add inside `initMap()`, after the `moveend` handler:
```javascript
// Send map-level click coordinates to Shiny (fires even on empty areas)
map.on('click', function (e) {
    Shiny.setInputValue(mapId + '_map_click', {
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        point: { x: e.point.x, y: e.point.y }
    }, { priority: "event" });
});

// Context menu (right-click) for secondary actions
map.on('contextmenu', function (e) {
    Shiny.setInputValue(mapId + '_map_contextmenu', {
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        point: { x: e.point.x, y: e.point.y }
    }, { priority: "event" });
});
```

#### Python Property — `components.py`

```python
@property
def map_click_input_id(self) -> str:
    """Shiny input for map-level click events (fires even on empty areas).

    Returns ``{longitude, latitude, point: {x, y}}``.
    """
    return f"{self.id}_map_click"

@property
def map_contextmenu_input_id(self) -> str:
    """Shiny input for right-click / context-menu events on the map."""
    return f"{self.id}_map_contextmenu"
```

#### Usage Example
```python
@reactive.Effect
@reactive.event(input.my_map_map_click)
def on_map_click():
    click = input.my_map_map_click()
    lng, lat = click["longitude"], click["latitude"]
    # Place marker, query WMS, etc.
```

#### Tests
Properties are trivial string returns — test pattern:
```python
class TestMapClickInputIds:
    def test_map_click_input_id(self):
        w = MapWidget("mc1")
        assert w.map_click_input_id == "mc1_map_click"

    def test_map_contextmenu_input_id(self):
        w = MapWidget("mc2")
        assert w.map_contextmenu_input_id == "mc2_map_contextmenu"
```

---

### Phase 1 Summary — `__init__.py` Exports

New symbols to add to `__init__.py`:
```python
from .components import (
    ...
    # Existing exports unchanged
    # New:
    CONTROL_TYPES,    # set of valid control type strings
    CONTROL_POSITIONS,  # set of valid position strings
)
```

No new top-level functions — all new features are `MapWidget` methods.

### Phase 1 Summary — JS Handler Count

| Handler | Channel | Direction |
|---------|---------|-----------|
| deck_add_control | Py→JS | NEW |
| deck_remove_control | Py→JS | NEW |
| deck_fit_bounds | Py→JS | NEW |
| `{id}_map_click` | JS→Py | NEW (setInputValue) |
| `{id}_map_contextmenu` | JS→Py | NEW (setInputValue) |
| `{id}_view_state` (bounds) | JS→Py | MODIFIED (add bounds field) |

**deckgl-init.js estimated size after Phase 1**: ~700 lines (+~110 lines)

---

## Phase 2: v0.3.0 — Native MapLibre Rendering

### 2.1 Native Sources & Layers

**Why**: MapLibre can render GeoJSON, raster tiles (WMS), and vector tiles
natively — without going through deck.gl. This is superior for:
- Static reference layers (EEZ boundaries, MPAs, coastlines)
- WMS/WMTS services (EMODnet bathymetry, Copernicus Marine)
- Vector tile basemap overlays

deck.gl remains the primary engine for data-heavy interactive layers.

#### Python API — `components.py`

```python
async def add_source(
    self,
    session,
    source_id: str,
    source_spec: dict,
) -> None:
    """Add a native MapLibre source.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        Unique source identifier.
    source_spec
        MapLibre source specification dict. Must include ``"type"``
        (``"geojson"``, ``"raster"``, ``"vector"``, ``"raster-dem"``,
        ``"image"``).

    Examples
    --------
    GeoJSON source::

        widget.add_source(session, "eez", {
            "type": "geojson",
            "data": eez_geojson_dict
        })

    WMS raster tiles::

        widget.add_source(session, "bathymetry", {
            "type": "raster",
            "tiles": ["https://ows.emodnet-bathymetry.eu/wms?...&BBOX={bbox-epsg-3857}"],
            "tileSize": 256
        })

    Vector tiles (PMTiles)::

        widget.add_source(session, "land", {
            "type": "vector",
            "url": "pmtiles://https://example.com/land.pmtiles"
        })
    """
    await session.send_custom_message("deck_add_source", {
        "id": self.id,
        "sourceId": source_id,
        "spec": source_spec,
    })


async def add_maplibre_layer(
    self,
    session,
    layer_spec: dict,
    *,
    before_id: str | None = None,
) -> None:
    """Add a native MapLibre rendering layer.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_spec
        MapLibre layer specification dict with at minimum ``"id"``,
        ``"type"``, and ``"source"``.
    before_id
        Insert this layer before the given layer ID in the stack.
        ``None`` adds on top of all MapLibre layers (but still below
        the deck.gl overlay when ``interleaved=False``).

    Examples
    --------
    Fill layer::

        widget.add_maplibre_layer(session, {
            "id": "eez-fill",
            "type": "fill",
            "source": "eez",
            "paint": {
                "fill-color": "#088",
                "fill-opacity": 0.4
            }
        })

    Raster layer (for WMS)::

        widget.add_maplibre_layer(session, {
            "id": "bathymetry-layer",
            "type": "raster",
            "source": "bathymetry",
            "paint": {"raster-opacity": 0.7}
        })

    Line layer::

        widget.add_maplibre_layer(session, {
            "id": "eez-outline",
            "type": "line",
            "source": "eez",
            "paint": {
                "line-color": "#333",
                "line-width": 2
            }
        })
    """
    payload: dict = {
        "id": self.id,
        "layerSpec": layer_spec,
    }
    if before_id is not None:
        payload["beforeId"] = before_id
    await session.send_custom_message("deck_add_maplibre_layer", payload)


async def remove_maplibre_layer(
    self,
    session,
    layer_id: str,
) -> None:
    """Remove a native MapLibre layer.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_id
        The ``id`` of the MapLibre layer to remove.
    """
    await session.send_custom_message("deck_remove_maplibre_layer", {
        "id": self.id,
        "layerId": layer_id,
    })


async def remove_source(
    self,
    session,
    source_id: str,
) -> None:
    """Remove a native MapLibre source.

    All layers using this source must be removed first.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        The source identifier to remove.
    """
    await session.send_custom_message("deck_remove_source", {
        "id": self.id,
        "sourceId": source_id,
    })


async def set_source_data(
    self,
    session,
    source_id: str,
    data: dict | str,
) -> None:
    """Update the data of an existing GeoJSON source.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        The source identifier (must be a GeoJSON source).
    data
        New GeoJSON dict or URL string.
    """
    serialised = _serialise_data(data)
    await session.send_custom_message("deck_set_source_data", {
        "id": self.id,
        "sourceId": source_id,
        "data": serialised,
    })
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_add_source — add a native MapLibre source
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_add_source", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var sourceId = payload.sourceId;
    var spec = payload.spec;

    // Remove existing source if present (along with its layers)
    if (map.getSource(sourceId)) {
        // Find and remove layers using this source first
        var style = map.getStyle();
        if (style && style.layers) {
            style.layers.forEach(function (l) {
                if (l.source === sourceId) {
                    map.removeLayer(l.id);
                }
            });
        }
        map.removeSource(sourceId);
    }

    map.addSource(sourceId, spec);
});


// -----------------------------------------------------------------------
// deck_add_maplibre_layer — add a native MapLibre rendering layer
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_add_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var layerSpec = payload.layerSpec;
    var beforeId = payload.beforeId || undefined;

    // Remove existing layer with same id
    if (map.getLayer(layerSpec.id)) {
        map.removeLayer(layerSpec.id);
    }

    map.addLayer(layerSpec, beforeId);
});


// -----------------------------------------------------------------------
// deck_remove_maplibre_layer — remove a native MapLibre layer
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_remove_maplibre_layer", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (instance.map.getLayer(payload.layerId)) {
        instance.map.removeLayer(payload.layerId);
    }
});


// -----------------------------------------------------------------------
// deck_remove_source — remove a native MapLibre source
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_remove_source", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (instance.map.getSource(payload.sourceId)) {
        instance.map.removeSource(payload.sourceId);
    }
});


// -----------------------------------------------------------------------
// deck_set_source_data — update GeoJSON source data
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_source_data", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var source = instance.map.getSource(payload.sourceId);
    if (source && typeof source.setData === 'function') {
        source.setData(payload.data);
    }
});
```

#### Tests
```python
class TestNativeSources:
    def test_add_source_geojson(self):
        import asyncio
        w = MapWidget("ns1")
        fake = FakeSession()
        spec = {"type": "geojson", "data": {"type": "FeatureCollection", "features": []}}
        asyncio.run(w.add_source(fake, "my-source", spec))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_source"
        assert msg[1]["sourceId"] == "my-source"
        assert msg[1]["spec"]["type"] == "geojson"

    def test_add_source_raster_wms(self):
        import asyncio
        w = MapWidget("ns2")
        fake = FakeSession()
        spec = {
            "type": "raster",
            "tiles": ["https://ows.emodnet.eu/wms?...&BBOX={bbox-epsg-3857}"],
            "tileSize": 256,
        }
        asyncio.run(w.add_source(fake, "bathy", spec))
        assert fake.messages[0][1]["spec"]["type"] == "raster"

    def test_add_maplibre_layer(self):
        import asyncio
        w = MapWidget("ns3")
        fake = FakeSession()
        layer_spec = {
            "id": "eez-fill",
            "type": "fill",
            "source": "eez",
            "paint": {"fill-color": "#088", "fill-opacity": 0.4},
        }
        asyncio.run(w.add_maplibre_layer(fake, layer_spec))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_maplibre_layer"
        assert msg[1]["layerSpec"]["id"] == "eez-fill"

    def test_add_maplibre_layer_with_before_id(self):
        import asyncio
        w = MapWidget("ns4")
        fake = FakeSession()
        asyncio.run(w.add_maplibre_layer(fake, {"id": "a", "type": "fill", "source": "s"},
                                          before_id="other-layer"))
        assert fake.messages[0][1]["beforeId"] == "other-layer"

    def test_remove_maplibre_layer(self):
        import asyncio
        w = MapWidget("ns5")
        fake = FakeSession()
        asyncio.run(w.remove_maplibre_layer(fake, "eez-fill"))
        assert fake.messages[0] == ("deck_remove_maplibre_layer", {
            "id": "ns5", "layerId": "eez-fill"
        })

    def test_remove_source(self):
        import asyncio
        w = MapWidget("ns6")
        fake = FakeSession()
        asyncio.run(w.remove_source(fake, "eez"))
        assert fake.messages[0] == ("deck_remove_source", {
            "id": "ns6", "sourceId": "eez"
        })

    def test_set_source_data(self):
        import asyncio
        w = MapWidget("ns7")
        fake = FakeSession()
        new_data = {"type": "FeatureCollection", "features": []}
        asyncio.run(w.set_source_data(fake, "my-source", new_data))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_source_data"
        assert msg[1]["data"]["type"] == "FeatureCollection"
```

---

### 2.2 Runtime Style Mutation

**Why**: After adding native MapLibre layers, users need to dynamically change
paint properties (opacity, color), layout properties (visibility), and
data-driven filters.

#### Python API — `components.py`

```python
async def set_paint_property(
    self,
    session,
    layer_id: str,
    name: str,
    value,
) -> None:
    """Set a paint property on a native MapLibre layer.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_id
        The MapLibre layer id.
    name
        Paint property name (e.g. ``"fill-opacity"``, ``"line-color"``).
    value
        New value (number, string, array, or MapLibre expression).
    """
    await session.send_custom_message("deck_set_paint_property", {
        "id": self.id,
        "layerId": layer_id,
        "name": name,
        "value": value,
    })


async def set_layout_property(
    self,
    session,
    layer_id: str,
    name: str,
    value,
) -> None:
    """Set a layout property on a native MapLibre layer.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_id
        The MapLibre layer id.
    name
        Layout property name (e.g. ``"visibility"``).
    value
        New value (e.g. ``"visible"`` or ``"none"``).
    """
    await session.send_custom_message("deck_set_layout_property", {
        "id": self.id,
        "layerId": layer_id,
        "name": name,
        "value": value,
    })


async def set_filter(
    self,
    session,
    layer_id: str,
    filter_expr: list | None = None,
) -> None:
    """Set a data-driven filter on a native MapLibre layer.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_id
        The MapLibre layer id.
    filter_expr
        A MapLibre filter expression, e.g.
        ``[">=", ["get", "depth"], 100]``. Pass ``None`` to clear.
    """
    await session.send_custom_message("deck_set_filter", {
        "id": self.id,
        "layerId": layer_id,
        "filter": filter_expr,
    })
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_set_paint_property
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_paint_property", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.map.setPaintProperty(payload.layerId, payload.name, payload.value);
});


// -----------------------------------------------------------------------
// deck_set_layout_property
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_layout_property", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.map.setLayoutProperty(payload.layerId, payload.name, payload.value);
});


// -----------------------------------------------------------------------
// deck_set_filter
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_filter", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;
    instance.map.setFilter(payload.layerId, payload.filter || null);
});
```

#### Tests
```python
class TestStyleMutation:
    def test_set_paint_property(self):
        import asyncio
        w = MapWidget("sp1")
        fake = FakeSession()
        asyncio.run(w.set_paint_property(fake, "eez-fill", "fill-opacity", 0.8))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_paint_property"
        assert msg[1]["layerId"] == "eez-fill"
        assert msg[1]["name"] == "fill-opacity"
        assert msg[1]["value"] == 0.8

    def test_set_layout_property(self):
        import asyncio
        w = MapWidget("sp2")
        fake = FakeSession()
        asyncio.run(w.set_layout_property(fake, "labels", "visibility", "none"))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_layout_property"
        assert msg[1]["value"] == "none"

    def test_set_filter(self):
        import asyncio
        w = MapWidget("sp3")
        fake = FakeSession()
        asyncio.run(w.set_filter(fake, "stations", [">=", ["get", "depth"], 100]))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_filter"
        assert msg[1]["filter"] == [">=", ["get", "depth"], 100]

    def test_set_filter_clear(self):
        import asyncio
        w = MapWidget("sp4")
        fake = FakeSession()
        asyncio.run(w.set_filter(fake, "stations", None))
        assert fake.messages[0][1]["filter"] is None
```

---

## Phase 3: v0.4.0 — 3D, Globe & Advanced Interaction

### 3.1 Globe Projection

**Why**: Requires MapLibre v4+ (delivered in 1.1). Globe projection is
visually stunning for showing global ocean data, basins, and currents.
The flat Mercator distortion at high latitudes misrepresents Arctic/Antarctic
marine areas.

#### Python API — `components.py`

```python
async def set_projection(
    self,
    session,
    projection: str = "mercator",
) -> None:
    """Set the map projection.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    projection
        ``"mercator"`` (default flat map) or ``"globe"`` (3D sphere).
        Requires MapLibre GL JS v4+.
    """
    if projection not in ("mercator", "globe"):
        raise ValueError(
            f"Unknown projection {projection!r}. Use 'mercator' or 'globe'."
        )
    await session.send_custom_message("deck_set_projection", {
        "id": self.id,
        "projection": projection,
    })
```

#### JS Handler — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_set_projection — switch between mercator and globe
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_projection", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof instance.map.setProjection === 'function') {
        instance.map.setProjection({ type: payload.projection || 'mercator' });
    } else {
        console.warn('[shiny_deckgl] setProjection requires MapLibre v4+');
    }
});
```

#### deck.gl Compatibility Note
When globe projection is active, deck.gl `MapboxOverlay` may not render
correctly because the coordinate system changes. Two strategies:
1. **Disable deck.gl overlay in globe mode** — show only native MapLibre layers
2. **Use `interleaved: true`** — some deck.gl layers work in globe mode

Needs empirical testing. Start with strategy 1 (warn users that deck.gl
layers are hidden in globe mode) and iterate.

#### Tests
```python
class TestSetProjection:
    def test_set_projection_globe(self):
        import asyncio
        w = MapWidget("proj1")
        fake = FakeSession()
        asyncio.run(w.set_projection(fake, "globe"))
        assert fake.messages[0] == ("deck_set_projection", {
            "id": "proj1", "projection": "globe",
        })

    def test_set_projection_mercator(self):
        import asyncio
        w = MapWidget("proj2")
        fake = FakeSession()
        asyncio.run(w.set_projection(fake, "mercator"))
        assert fake.messages[0][1]["projection"] == "mercator"

    def test_set_projection_invalid_raises(self):
        import asyncio, pytest
        w = MapWidget("proj3")
        fake = FakeSession()
        with pytest.raises(ValueError, match="Unknown projection"):
            asyncio.run(w.set_projection(fake, "orthographic"))
```

---

### 3.2 3D Terrain

**Why**: Coastal terrain visualisation for bathymetric and topographic context.
Requires MapLibre v4+ and a `raster-dem` source (e.g. MapTiler, Mapzen,
or custom DEM tiles). Depends on Phase 2 `add_source()` for the DEM source.

#### Python API — `components.py`

```python
async def set_terrain(
    self,
    session,
    source: str | None = None,
    exaggeration: float = 1.0,
) -> None:
    """Enable or disable 3D terrain rendering.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source
        The id of a ``raster-dem`` source previously added via
        ``add_source()``. Pass ``None`` to disable terrain.
    exaggeration
        Vertical exaggeration factor (default 1.0 = real scale).
        Values like 1.5–3.0 make subtle terrain more visible.

    Example
    -------
    ::

        # First add a DEM source
        await widget.add_source(session, "dem", {
            "type": "raster-dem",
            "url": "https://demotiles.maplibre.org/terrain-tiles/tiles.json",
            "tileSize": 256,
        })
        # Then enable terrain
        await widget.set_terrain(session, source="dem", exaggeration=1.5)
        # Disable terrain
        await widget.set_terrain(session, source=None)
    """
    terrain = None
    if source is not None:
        terrain = {"source": source, "exaggeration": exaggeration}
    await session.send_custom_message("deck_set_terrain", {
        "id": self.id,
        "terrain": terrain,
    })


async def set_sky(
    self,
    session,
    sky: dict | None = None,
) -> None:
    """Set the sky/atmosphere properties (works best with terrain enabled).

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    sky
        Sky specification dict, e.g.
        ``{"sky-color": "#199EF3", "sky-horizon-blend": 0.5,
          "horizon-color": "#ffffff", "horizon-fog-blend": 0.5,
          "fog-color": "#0000ff", "fog-ground-blend": 0.5}``.
        Pass ``None`` to reset to default.
    """
    await session.send_custom_message("deck_set_sky", {
        "id": self.id,
        "sky": sky,
    })
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_set_terrain — enable/disable 3D terrain
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_terrain", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof instance.map.setTerrain === 'function') {
        instance.map.setTerrain(payload.terrain);
    } else {
        console.warn('[shiny_deckgl] setTerrain requires MapLibre v4+');
    }
});


// -----------------------------------------------------------------------
// deck_set_sky — atmosphere/sky properties
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_sky", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (typeof instance.map.setSky === 'function') {
        instance.map.setSky(payload.sky || {});
    }
});
```

#### Performance Note
The target machine has no discrete GPU and 16 GB RAM. 3D terrain is
CPU-intensive on WebGL. Recommend:
- Limit terrain to small viewports or low-zoom overviews
- Use `exaggeration >= 2.0` to make subtle coastal terrain visible
- Provide a toggle to disable terrain for performance

#### Tests
```python
class TestTerrain:
    def test_set_terrain_enable(self):
        import asyncio
        w = MapWidget("ter1")
        fake = FakeSession()
        asyncio.run(w.set_terrain(fake, source="dem", exaggeration=1.5))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_terrain"
        assert msg[1]["terrain"] == {"source": "dem", "exaggeration": 1.5}

    def test_set_terrain_disable(self):
        import asyncio
        w = MapWidget("ter2")
        fake = FakeSession()
        asyncio.run(w.set_terrain(fake, source=None))
        assert fake.messages[0][1]["terrain"] is None

    def test_set_sky(self):
        import asyncio
        w = MapWidget("ter3")
        fake = FakeSession()
        sky = {"sky-color": "#199EF3", "sky-horizon-blend": 0.5}
        asyncio.run(w.set_sky(fake, sky))
        assert fake.messages[0] == ("deck_set_sky", {
            "id": "ter3", "sky": sky,
        })

    def test_set_sky_none_resets(self):
        import asyncio
        w = MapWidget("ter4")
        fake = FakeSession()
        asyncio.run(w.set_sky(fake, None))
        assert fake.messages[0][1]["sky"] is None
```

---

### 3.3 Native Popups

**Why**: MapLibre `Popup` objects are better for native layers than the
custom tooltip DIV used by deck.gl hover. They anchor to map coordinates,
follow the map during pan/zoom, and have a standard close button.
Depends on Phase 2 native layers (2.1).

#### Python API — `components.py`

```python
async def add_popup(
    self,
    session,
    layer_id: str,
    template: str,
    *,
    close_button: bool = True,
    close_on_click: bool = True,
    max_width: str = "300px",
    anchor: str | None = None,
) -> None:
    """Attach a click popup to a native MapLibre layer.

    When the user clicks a feature in the specified layer, a popup
    appears at the click location with HTML content populated from
    the feature's properties.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_id
        The MapLibre layer id to attach the popup to.
    template
        HTML template string with ``{property}`` placeholders that are
        filled from feature properties on click.  Example:
        ``"<b>{name}</b><br>Depth: {depth} m"``.
    close_button
        Show a close button (default True).
    close_on_click
        Close when clicking elsewhere on the map (default True).
    max_width
        CSS max-width of the popup container (default ``"300px"``).
    anchor
        Popup anchor position relative to the coordinate:
        ``"top"``, ``"bottom"``, ``"left"``, ``"right"``,
        ``"top-left"``, ``"top-right"``, ``"bottom-left"``,
        ``"bottom-right"``, or ``None`` (auto).
    """
    payload: dict = {
        "id": self.id,
        "layerId": layer_id,
        "template": template,
        "closeButton": close_button,
        "closeOnClick": close_on_click,
        "maxWidth": max_width,
    }
    if anchor is not None:
        payload["anchor"] = anchor
    await session.send_custom_message("deck_add_popup", payload)


async def remove_popup(
    self,
    session,
    layer_id: str,
) -> None:
    """Remove a previously attached popup handler from a native layer.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    layer_id
        The MapLibre layer id whose popup handler should be removed.
    """
    await session.send_custom_message("deck_remove_popup", {
        "id": self.id,
        "layerId": layer_id,
    })
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_add_popup — attach click popup to a native MapLibre layer
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_add_popup", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var layerId = payload.layerId;
    var template = payload.template;

    // Store handler references for cleanup
    if (!instance.popupHandlers) instance.popupHandlers = {};

    // Remove existing handler for this layer
    if (instance.popupHandlers[layerId]) {
        map.off('click', layerId, instance.popupHandlers[layerId].click);
        map.off('mouseenter', layerId, instance.popupHandlers[layerId].enter);
        map.off('mouseleave', layerId, instance.popupHandlers[layerId].leave);
        delete instance.popupHandlers[layerId];
    }

    var clickHandler = function (e) {
        if (!e.features || !e.features.length) return;
        var props = e.features[0].properties || {};
        var html = interpolateTemplate(template, props);

        var popupOpts = {
            closeButton: payload.closeButton !== false,
            closeOnClick: payload.closeOnClick !== false,
            maxWidth: payload.maxWidth || '300px'
        };
        if (payload.anchor) popupOpts.anchor = payload.anchor;

        new maplibregl.Popup(popupOpts)
            .setLngLat(e.lngLat)
            .setHTML(html)
            .addTo(map);

        // Also send click info to Shiny
        Shiny.setInputValue(payload.id + '_feature_click', {
            layerId: layerId,
            properties: props,
            longitude: e.lngLat.lng,
            latitude: e.lngLat.lat
        }, { priority: "event" });
    };

    var enterHandler = function () {
        map.getCanvas().style.cursor = 'pointer';
    };
    var leaveHandler = function () {
        map.getCanvas().style.cursor = '';
    };

    map.on('click', layerId, clickHandler);
    map.on('mouseenter', layerId, enterHandler);
    map.on('mouseleave', layerId, leaveHandler);

    instance.popupHandlers[layerId] = {
        click: clickHandler,
        enter: enterHandler,
        leave: leaveHandler
    };
});


// -----------------------------------------------------------------------
// deck_remove_popup — detach popup handler from a native layer
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_remove_popup", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.popupHandlers) return;

    var layerId = payload.layerId;
    if (instance.popupHandlers[layerId]) {
        instance.map.off('click', layerId, instance.popupHandlers[layerId].click);
        instance.map.off('mouseenter', layerId, instance.popupHandlers[layerId].enter);
        instance.map.off('mouseleave', layerId, instance.popupHandlers[layerId].leave);
        delete instance.popupHandlers[layerId];
    }
});
```

#### New Shiny Input: `{id}_feature_click`

When a popup opens, the feature's properties and coordinates are sent to
Python as `input.{id}_feature_click()`:
```python
@property
def feature_click_input_id(self) -> str:
    """Shiny input for native layer feature clicks (with popup).

    Returns ``{layerId, properties, longitude, latitude}``.
    """
    return f"{self.id}_feature_click"
```

#### Tests
```python
class TestPopups:
    def test_add_popup(self):
        import asyncio
        w = MapWidget("pop1")
        fake = FakeSession()
        asyncio.run(w.add_popup(fake, "stations", "<b>{name}</b>"))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_popup"
        assert msg[1]["layerId"] == "stations"
        assert msg[1]["template"] == "<b>{name}</b>"
        assert msg[1]["closeButton"] is True

    def test_add_popup_with_options(self):
        import asyncio
        w = MapWidget("pop2")
        fake = FakeSession()
        asyncio.run(w.add_popup(fake, "eez", "{name}",
                                 close_button=False, max_width="400px",
                                 anchor="bottom"))
        msg = fake.messages[0][1]
        assert msg["closeButton"] is False
        assert msg["maxWidth"] == "400px"
        assert msg["anchor"] == "bottom"

    def test_remove_popup(self):
        import asyncio
        w = MapWidget("pop3")
        fake = FakeSession()
        asyncio.run(w.remove_popup(fake, "stations"))
        assert fake.messages[0] == ("deck_remove_popup", {
            "id": "pop3", "layerId": "stations",
        })

    def test_feature_click_input_id(self):
        w = MapWidget("pop4")
        assert w.feature_click_input_id == "pop4_feature_click"
```

---

### 3.4 Spatial Queries

**Why**: `queryRenderedFeatures()` and `querySourceFeatures()` are essential
for "what's here?" interactions — clicking on the map and discovering which
native MapLibre features (EEZ boundaries, MPAs, stations) are present at
that location. Also enables spatial selection (lasso, bbox) workflows.

#### Python API — `components.py`

```python
async def query_rendered_features(
    self,
    session,
    *,
    point: list[float] | None = None,
    bounds: list[list[float]] | None = None,
    layers: list[str] | None = None,
    filter_expr: list | None = None,
    request_id: str = "default",
) -> None:
    """Query visible features at a point or within a bounding box.

    The result is delivered asynchronously as a Shiny input
    ``input.{id}_query_result()``.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    point
        ``[x, y]`` pixel coordinates on the map canvas.
        Mutually exclusive with ``bounds``.
    bounds
        ``[[x1, y1], [x2, y2]]`` pixel bounding box. Mutually exclusive
        with ``point``.
    layers
        Optional list of layer ids to restrict the query. If ``None``,
        all layers are queried.
    filter_expr
        Optional MapLibre filter expression to further restrict results.
    request_id
        An identifier included in the result so the caller can match
        requests to responses (useful for concurrent queries).

    Example
    -------
    ::

        # Query features at a click location
        @reactive.Effect
        @reactive.event(input.my_map_map_click)
        async def on_click():
            click = input.my_map_map_click()
            await widget.query_rendered_features(
                session,
                point=[click["point"]["x"], click["point"]["y"]],
                layers=["eez-fill", "stations"],
                request_id="click-query"
            )

        @reactive.Effect
        @reactive.event(input.my_map_query_result)
        def on_query_result():
            result = input.my_map_query_result()
            # result = {"requestId": "click-query", "features": [...]}
    """
    payload: dict = {
        "id": self.id,
        "requestId": request_id,
    }
    if point is not None:
        payload["point"] = point
    elif bounds is not None:
        payload["bounds"] = bounds
    if layers is not None:
        payload["layers"] = layers
    if filter_expr is not None:
        payload["filter"] = filter_expr
    await session.send_custom_message("deck_query_features", payload)
```

#### JS Handler — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_query_features — query rendered features and return to Shiny
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_query_features", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var queryOpts = {};

    if (payload.layers) {
        queryOpts.layers = payload.layers;
    }
    if (payload.filter) {
        queryOpts.filter = payload.filter;
    }

    var features;
    if (payload.point) {
        // Point query
        features = map.queryRenderedFeatures(payload.point, queryOpts);
    } else if (payload.bounds) {
        // Bounding box query
        features = map.queryRenderedFeatures(payload.bounds, queryOpts);
    } else {
        // No geometry — query all visible features in the given layers
        features = map.queryRenderedFeatures(queryOpts);
    }

    // Simplify: extract GeoJSON-compatible features (strip internal props)
    var simplified = features.map(function (f) {
        return {
            type: "Feature",
            geometry: f.geometry,
            properties: f.properties,
            layer: { id: f.layer ? f.layer.id : null },
            source: f.source || null
        };
    });

    Shiny.setInputValue(payload.id + '_query_result', {
        requestId: payload.requestId || 'default',
        features: simplified
    }, { priority: "event" });
});
```

#### New Shiny Input: `{id}_query_result`

```python
@property
def query_result_input_id(self) -> str:
    """Shiny input for spatial query results.

    Returns ``{requestId: str, features: [GeoJSON features]}``.
    """
    return f"{self.id}_query_result"
```

#### Convenience: `query_at_lnglat()`

Higher-level method that converts lon/lat to pixel coords first:
```python
async def query_at_lnglat(
    self,
    session,
    longitude: float,
    latitude: float,
    *,
    layers: list[str] | None = None,
    request_id: str = "default",
) -> None:
    """Query features at a geographic coordinate.

    Internally converts to pixel coordinates using map.project() on the
    JS side, then calls queryRenderedFeatures.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    longitude, latitude
        Geographic coordinates (WGS 84).
    layers
        Optional list of layer ids to restrict the query.
    request_id
        Identifier included in the result for request matching.
    """
    await session.send_custom_message("deck_query_at_lnglat", {
        "id": self.id,
        "longitude": longitude,
        "latitude": latitude,
        "layers": layers,
        "requestId": request_id,
    })
```

JS handler for the lon/lat variant:
```javascript
// -----------------------------------------------------------------------
// deck_query_at_lnglat — project to pixels then query
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_query_at_lnglat", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var point = map.project([payload.longitude, payload.latitude]);

    var queryOpts = {};
    if (payload.layers) queryOpts.layers = payload.layers;

    var features = map.queryRenderedFeatures(
        [point.x, point.y], queryOpts
    );

    var simplified = features.map(function (f) {
        return {
            type: "Feature",
            geometry: f.geometry,
            properties: f.properties,
            layer: { id: f.layer ? f.layer.id : null },
            source: f.source || null
        };
    });

    Shiny.setInputValue(payload.id + '_query_result', {
        requestId: payload.requestId || 'default',
        features: simplified
    }, { priority: "event" });
});
```

#### Tests
```python
class TestSpatialQueries:
    def test_query_rendered_features_point(self):
        import asyncio
        w = MapWidget("sq1")
        fake = FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, point=[100, 200], layers=["eez-fill"],
            request_id="test-1"
        ))
        msg = fake.messages[0]
        assert msg[0] == "deck_query_features"
        assert msg[1]["point"] == [100, 200]
        assert msg[1]["layers"] == ["eez-fill"]
        assert msg[1]["requestId"] == "test-1"

    def test_query_rendered_features_bounds(self):
        import asyncio
        w = MapWidget("sq2")
        fake = FakeSession()
        asyncio.run(w.query_rendered_features(
            fake, bounds=[[50, 50], [200, 200]]
        ))
        msg = fake.messages[0][1]
        assert msg["bounds"] == [[50, 50], [200, 200]]
        assert "point" not in msg

    def test_query_at_lnglat(self):
        import asyncio
        w = MapWidget("sq3")
        fake = FakeSession()
        asyncio.run(w.query_at_lnglat(fake, 21.1, 55.7,
                                        layers=["stations"],
                                        request_id="click"))
        msg = fake.messages[0]
        assert msg[0] == "deck_query_at_lnglat"
        assert msg[1]["longitude"] == 21.1
        assert msg[1]["latitude"] == 55.7
        assert msg[1]["requestId"] == "click"

    def test_query_result_input_id(self):
        w = MapWidget("sq4")
        assert w.query_result_input_id == "sq4_query_result"
```

---

### 3.5 Multiple Markers

**Why**: Currently limited to a single draggable marker via `add_drag_marker()`.
Marine apps need multiple station markers with custom colors, popups,
and individual click/drag events.

#### Python API — `components.py`

```python
async def add_marker(
    self,
    session,
    marker_id: str,
    longitude: float,
    latitude: float,
    *,
    color: str = "#3FB1CE",
    draggable: bool = False,
    popup_html: str | None = None,
) -> None:
    """Add a named marker to the map.

    Unlike ``add_drag_marker()`` (limited to 1), this supports any
    number of markers, each identified by ``marker_id``.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    marker_id
        Unique identifier for this marker. Used for removal and
        Shiny input events.
    longitude, latitude
        Marker position in WGS 84.
    color
        CSS color string for the default marker pin.
    draggable
        Whether the marker can be dragged by the user.
    popup_html
        HTML content for a popup shown when the marker is clicked.
    """
    await session.send_custom_message("deck_add_marker", {
        "id": self.id,
        "markerId": marker_id,
        "longitude": longitude,
        "latitude": latitude,
        "color": color,
        "draggable": draggable,
        "popupHtml": popup_html,
    })


async def remove_marker(
    self,
    session,
    marker_id: str,
) -> None:
    """Remove a named marker from the map.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    marker_id
        The marker identifier to remove.
    """
    await session.send_custom_message("deck_remove_marker", {
        "id": self.id,
        "markerId": marker_id,
    })


async def clear_markers(
    self,
    session,
) -> None:
    """Remove all named markers from the map.

    Does not affect the legacy ``add_drag_marker()`` single marker.
    """
    await session.send_custom_message("deck_clear_markers", {
        "id": self.id,
    })
```

#### New Shiny Inputs
```python
@property
def marker_click_input_id(self) -> str:
    """Shiny input for named marker click events.

    Returns ``{markerId, longitude, latitude}``.
    """
    return f"{self.id}_marker_click"

@property
def marker_drag_input_id(self) -> str:
    """Shiny input for named marker drag-end events.

    Returns ``{markerId, longitude, latitude}``.
    """
    return f"{self.id}_marker_drag"
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_add_marker — add or replace a named marker
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_add_marker", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    if (!instance.markers) instance.markers = {};
    var mapId = payload.id;

    // Remove existing marker with same id
    if (instance.markers[payload.markerId]) {
        instance.markers[payload.markerId].remove();
    }

    var marker = new maplibregl.Marker({
        color: payload.color || '#3FB1CE',
        draggable: payload.draggable || false
    }).setLngLat([payload.longitude, payload.latitude]);

    // Optional popup
    if (payload.popupHtml) {
        var popup = new maplibregl.Popup({ offset: 25 })
            .setHTML(payload.popupHtml);
        marker.setPopup(popup);
    }

    marker.addTo(instance.map);
    instance.markers[payload.markerId] = marker;

    // Click event → Shiny
    marker.getElement().addEventListener('click', function () {
        Shiny.setInputValue(mapId + '_marker_click', {
            markerId: payload.markerId,
            longitude: marker.getLngLat().lng,
            latitude: marker.getLngLat().lat
        }, { priority: "event" });
    });

    // Drag end event → Shiny
    if (payload.draggable) {
        marker.on('dragend', function () {
            var lngLat = marker.getLngLat();
            Shiny.setInputValue(mapId + '_marker_drag', {
                markerId: payload.markerId,
                longitude: lngLat.lng,
                latitude: lngLat.lat
            }, { priority: "event" });
        });
    }
});


// -----------------------------------------------------------------------
// deck_remove_marker — remove a named marker
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_remove_marker", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.markers) return;

    if (instance.markers[payload.markerId]) {
        instance.markers[payload.markerId].remove();
        delete instance.markers[payload.markerId];
    }
});


// -----------------------------------------------------------------------
// deck_clear_markers — remove all named markers
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_clear_markers", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.markers) return;

    Object.keys(instance.markers).forEach(function (mid) {
        instance.markers[mid].remove();
    });
    instance.markers = {};
});
```

#### Tests
```python
class TestMultipleMarkers:
    def test_add_marker_basic(self):
        import asyncio
        w = MapWidget("mm1")
        fake = FakeSession()
        asyncio.run(w.add_marker(fake, "station-1", 21.1, 55.7))
        msg = fake.messages[0]
        assert msg[0] == "deck_add_marker"
        assert msg[1]["markerId"] == "station-1"
        assert msg[1]["longitude"] == 21.1
        assert msg[1]["color"] == "#3FB1CE"
        assert msg[1]["draggable"] is False

    def test_add_marker_with_options(self):
        import asyncio
        w = MapWidget("mm2")
        fake = FakeSession()
        asyncio.run(w.add_marker(fake, "buoy-A", 20.0, 56.0,
                                  color="#ff6600", draggable=True,
                                  popup_html="<b>Buoy A</b>"))
        msg = fake.messages[0][1]
        assert msg["color"] == "#ff6600"
        assert msg["draggable"] is True
        assert msg["popupHtml"] == "<b>Buoy A</b>"

    def test_remove_marker(self):
        import asyncio
        w = MapWidget("mm3")
        fake = FakeSession()
        asyncio.run(w.remove_marker(fake, "station-1"))
        assert fake.messages[0] == ("deck_remove_marker", {
            "id": "mm3", "markerId": "station-1",
        })

    def test_clear_markers(self):
        import asyncio
        w = MapWidget("mm4")
        fake = FakeSession()
        asyncio.run(w.clear_markers(fake))
        assert fake.messages[0] == ("deck_clear_markers", {"id": "mm4"})

    def test_marker_click_input_id(self):
        w = MapWidget("mm5")
        assert w.marker_click_input_id == "mm5_marker_click"

    def test_marker_drag_input_id(self):
        w = MapWidget("mm6")
        assert w.marker_drag_input_id == "mm6_marker_drag"
```

---

## Phase 4: v0.5.0 — Drawing, Data Integration & Export

### 4.1 Drawing Tools

**Why**: Polygon/line/point drawing is essential for:
- Defining study areas (draw a polygon → query data within it)
- Digitising transect lines for cross-section analysis
- Placing new station points manually

Uses the MapLibre Draw plugin (`@mapbox/mapbox-gl-draw` or a
MapLibre-compatible fork like `maplibre-gl-draw`).

#### CDN Dependency — `ui.py`

Add the draw plugin to `head_includes()`:
```python
head=(
    '<script src="https://cdn.jsdelivr.net/npm/deck.gl@9.1.4/dist.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.js"></script>\n'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/dist/maplibre-gl.css"/>\n'
    # NEW for v0.5.0:
    '<script src="https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@1.4.3/dist/mapbox-gl-draw.js"></script>\n'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@mapbox/mapbox-gl-draw@1.4.3/dist/mapbox-gl-draw.css"/>'
),
```

> **Alternative**: Use `maplibre-gl-draw` (community fork) if `mapbox-gl-draw`
> has compatibility issues with MapLibre v5.

#### Python API — `components.py`

```python
# Drawing mode constants
DRAW_POINT = "draw_point"
DRAW_LINE = "draw_line_string"
DRAW_POLYGON = "draw_polygon"
DRAW_MODES = {DRAW_POINT, DRAW_LINE, DRAW_POLYGON}


async def enable_draw(
    self,
    session,
    *,
    modes: list[str] | None = None,
    controls: dict[str, bool] | None = None,
    default_mode: str = "simple_select",
) -> None:
    """Enable drawing tools on the map.

    When the user draws a feature, it is sent to
    ``input.{id}_drawn_features()`` as a GeoJSON FeatureCollection.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    modes
        Which drawing modes to enable. Defaults to all:
        ``["draw_point", "draw_line_string", "draw_polygon"]``.
    controls
        Override individual control visibility, e.g.
        ``{"point": True, "line_string": True, "polygon": True,
          "trash": True, "combine_features": False,
          "uncombine_features": False}``.
    default_mode
        Initial mode: ``"simple_select"`` or ``"direct_select"``.

    Example
    -------
    ::

        await widget.enable_draw(session, modes=["draw_polygon"])

        @reactive.Effect
        @reactive.event(input.my_map_drawn_features)
        def on_draw():
            fc = input.my_map_drawn_features()
            # fc is a GeoJSON FeatureCollection of all drawn features
    """
    payload: dict = {
        "id": self.id,
        "defaultMode": default_mode,
    }
    if modes is not None:
        payload["modes"] = modes
    if controls is not None:
        payload["controls"] = controls
    await session.send_custom_message("deck_enable_draw", payload)


async def disable_draw(
    self,
    session,
) -> None:
    """Remove drawing tools from the map."""
    await session.send_custom_message("deck_disable_draw", {
        "id": self.id,
    })


async def get_drawn_features(
    self,
    session,
) -> None:
    """Request the current set of drawn features.

    Result is delivered as ``input.{id}_drawn_features()``.
    """
    await session.send_custom_message("deck_get_drawn_features", {
        "id": self.id,
    })


async def delete_drawn_features(
    self,
    session,
    feature_ids: list[str] | None = None,
) -> None:
    """Delete drawn features.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    feature_ids
        List of feature IDs to delete. If ``None``, deletes all.
    """
    await session.send_custom_message("deck_delete_drawn", {
        "id": self.id,
        "featureIds": feature_ids,
    })
```

#### New Shiny Inputs
```python
@property
def drawn_features_input_id(self) -> str:
    """Shiny input for drawn GeoJSON features.

    Returns a GeoJSON ``FeatureCollection`` of all drawn features.
    Updated on every draw.create, draw.update, and draw.delete event.
    """
    return f"{self.id}_drawn_features"

@property
def draw_mode_input_id(self) -> str:
    """Shiny input for the current drawing mode.

    Returns the active mode string (e.g. ``"draw_polygon"``,
    ``"simple_select"``).
    """
    return f"{self.id}_draw_mode"
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_enable_draw — add MapboxDraw to the map
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_enable_draw", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    // Check if MapboxDraw is available
    if (typeof MapboxDraw === 'undefined') {
        console.warn('[shiny_deckgl] MapboxDraw not loaded. '
            + 'Include mapbox-gl-draw CDN in head_includes().');
        return;
    }

    // Remove existing draw control
    if (instance.draw) {
        instance.map.removeControl(instance.draw);
    }

    var drawOpts = {
        displayControlsDefault: false,
    };

    // Set up controls based on modes or explicit controls
    if (payload.controls) {
        drawOpts.controls = payload.controls;
    } else {
        var modes = payload.modes || ['draw_point', 'draw_line_string', 'draw_polygon'];
        drawOpts.controls = {
            point: modes.indexOf('draw_point') !== -1,
            line_string: modes.indexOf('draw_line_string') !== -1,
            polygon: modes.indexOf('draw_polygon') !== -1,
            trash: true
        };
    }

    var draw = new MapboxDraw(drawOpts);
    instance.map.addControl(draw, 'top-left');
    instance.draw = draw;

    if (payload.defaultMode && payload.defaultMode !== 'simple_select') {
        draw.changeMode(payload.defaultMode);
    }

    // Helper to send all features to Shiny
    var mapId = payload.id;
    function sendFeatures() {
        var fc = draw.getAll();
        Shiny.setInputValue(mapId + '_drawn_features', fc, { priority: "event" });
    }

    // Wire draw events
    instance.map.on('draw.create', sendFeatures);
    instance.map.on('draw.update', sendFeatures);
    instance.map.on('draw.delete', sendFeatures);
    instance.map.on('draw.modechange', function (e) {
        Shiny.setInputValue(mapId + '_draw_mode', e.mode);
    });

    instance._drawSendFeatures = sendFeatures;
});


// -----------------------------------------------------------------------
// deck_disable_draw — remove draw control
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_disable_draw", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.draw) return;

    instance.map.removeControl(instance.draw);
    delete instance.draw;
});


// -----------------------------------------------------------------------
// deck_get_drawn_features — request current features
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_get_drawn_features", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.draw) return;

    var fc = instance.draw.getAll();
    Shiny.setInputValue(payload.id + '_drawn_features', fc, { priority: "event" });
});


// -----------------------------------------------------------------------
// deck_delete_drawn — delete specific or all drawn features
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_delete_drawn", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance || !instance.draw) return;

    if (payload.featureIds) {
        instance.draw.delete(payload.featureIds);
    } else {
        instance.draw.deleteAll();
    }
    // Send updated features
    if (instance._drawSendFeatures) instance._drawSendFeatures();
});
```

#### Tests
```python
class TestDrawingTools:
    def test_enable_draw_default(self):
        import asyncio
        w = MapWidget("dr1")
        fake = FakeSession()
        asyncio.run(w.enable_draw(fake))
        msg = fake.messages[0]
        assert msg[0] == "deck_enable_draw"
        assert msg[1]["defaultMode"] == "simple_select"

    def test_enable_draw_polygon_only(self):
        import asyncio
        w = MapWidget("dr2")
        fake = FakeSession()
        asyncio.run(w.enable_draw(fake, modes=["draw_polygon"]))
        assert fake.messages[0][1]["modes"] == ["draw_polygon"]

    def test_disable_draw(self):
        import asyncio
        w = MapWidget("dr3")
        fake = FakeSession()
        asyncio.run(w.disable_draw(fake))
        assert fake.messages[0][0] == "deck_disable_draw"

    def test_delete_drawn_features(self):
        import asyncio
        w = MapWidget("dr4")
        fake = FakeSession()
        asyncio.run(w.delete_drawn_features(fake, feature_ids=["abc", "def"]))
        assert fake.messages[0][1]["featureIds"] == ["abc", "def"]

    def test_delete_all_drawn(self):
        import asyncio
        w = MapWidget("dr5")
        fake = FakeSession()
        asyncio.run(w.delete_drawn_features(fake))
        assert fake.messages[0][1]["featureIds"] is None

    def test_drawn_features_input_id(self):
        w = MapWidget("dr6")
        assert w.drawn_features_input_id == "dr6_drawn_features"
```

---

### 4.2 GeoPandas Integration

**Why**: GeoPandas is the standard for geospatial data in Python. Currently,
`_serialise_data()` already handles GeoDataFrame → GeoJSON for deck.gl
layers. Phase 2 native sources need the same treatment, plus convenience
methods for common workflows.

#### Python API — `components.py`

```python
async def add_geodataframe(
    self,
    session,
    source_id: str,
    gdf,
    *,
    layer_type: str = "fill",
    paint: dict | None = None,
    layout: dict | None = None,
    before_id: str | None = None,
    popup_template: str | None = None,
) -> None:
    """Add a GeoPandas GeoDataFrame as a native MapLibre layer.

    Convenience method that:
    1. Serialises the GeoDataFrame to GeoJSON
    2. Calls ``add_source()`` with the GeoJSON data
    3. Calls ``add_maplibre_layer()`` with the specified style
    4. Optionally attaches a popup

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        Unique source/layer identifier. The layer id will be
        ``"{source_id}-layer"``.
    gdf
        A ``geopandas.GeoDataFrame``.
    layer_type
        MapLibre layer type: ``"fill"``, ``"line"``, ``"circle"``,
        ``"symbol"``, ``"fill-extrusion"`` (default ``"fill"``).
    paint
        Paint properties dict. Defaults vary by ``layer_type``:
        - fill: ``{"fill-color": "#088", "fill-opacity": 0.5}``
        - line: ``{"line-color": "#333", "line-width": 2}``
        - circle: ``{"circle-radius": 5, "circle-color": "#088"}``
    layout
        Layout properties dict (e.g. for symbol layers).
    before_id
        Insert layer before this layer id.
    popup_template
        If provided, attach a popup with this HTML template.

    Example
    -------
    ::

        import geopandas as gpd
        eez = gpd.read_file("eez_boundaries.geojson")
        await widget.add_geodataframe(session, "eez", eez,
                                       layer_type="line",
                                       paint={"line-color": "#ff6600", "line-width": 2},
                                       popup_template="<b>{GEONAME}</b>")
    """
    # Serialise GeoDataFrame → GeoJSON dict
    geojson = _serialise_data(gdf)

    # Add source
    await self.add_source(session, source_id, {
        "type": "geojson",
        "data": geojson,
    })

    # Build default paint
    default_paint = {
        "fill": {"fill-color": "#088", "fill-opacity": 0.5},
        "line": {"line-color": "#333", "line-width": 2},
        "circle": {"circle-radius": 5, "circle-color": "#088"},
    }
    final_paint = paint or default_paint.get(layer_type, {})

    # Add layer
    layer_id = f"{source_id}-layer"
    layer_spec: dict = {
        "id": layer_id,
        "type": layer_type,
        "source": source_id,
        "paint": final_paint,
    }
    if layout:
        layer_spec["layout"] = layout

    await self.add_maplibre_layer(session, layer_spec, before_id=before_id)

    # Optional popup
    if popup_template:
        await self.add_popup(session, layer_id, popup_template)


async def update_geodataframe(
    self,
    session,
    source_id: str,
    gdf,
) -> None:
    """Update the data of an existing GeoDataFrame source.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        The source identifier (must have been created via
        ``add_geodataframe()`` or ``add_source()`` with type geojson).
    gdf
        New ``geopandas.GeoDataFrame``.
    """
    geojson = _serialise_data(gdf)
    await self.set_source_data(session, source_id, geojson)
```

#### Tests
```python
class TestGeoPandas:
    def test_add_geodataframe(self):
        """add_geodataframe should call add_source + add_maplibre_layer."""
        import asyncio
        w = MapWidget("gp1")
        fake = FakeSession()

        # Minimal GeoJSON (simulating what _serialise_data returns)
        # We can test with a dict since we're not importing geopandas
        mock_geojson = {"type": "FeatureCollection", "features": []}

        # Monkey-patch _serialise_data to return our mock
        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: mock_geojson

        try:
            asyncio.run(w.add_geodataframe(fake, "test-src", "fake_gdf",
                                            layer_type="line",
                                            paint={"line-color": "#f00"}))
            # Should have 2 messages: add_source + add_maplibre_layer
            assert len(fake.messages) == 2
            assert fake.messages[0][0] == "deck_add_source"
            assert fake.messages[0][1]["sourceId"] == "test-src"
            assert fake.messages[1][0] == "deck_add_maplibre_layer"
            assert fake.messages[1][1]["layerSpec"]["id"] == "test-src-layer"
            assert fake.messages[1][1]["layerSpec"]["paint"]["line-color"] == "#f00"
        finally:
            comp._serialise_data = original

    def test_add_geodataframe_with_popup(self):
        """add_geodataframe with popup_template should send 3 messages."""
        import asyncio
        w = MapWidget("gp2")
        fake = FakeSession()

        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: {"type": "FeatureCollection", "features": []}

        try:
            asyncio.run(w.add_geodataframe(fake, "eez", "fake_gdf",
                                            popup_template="<b>{name}</b>"))
            # 3 messages: add_source + add_maplibre_layer + add_popup
            assert len(fake.messages) == 3
            assert fake.messages[2][0] == "deck_add_popup"
            assert fake.messages[2][1]["template"] == "<b>{name}</b>"
        finally:
            comp._serialise_data = original

    def test_update_geodataframe(self):
        import asyncio
        w = MapWidget("gp3")
        fake = FakeSession()

        import shiny_deckgl.components as comp
        original = comp._serialise_data
        comp._serialise_data = lambda x: {"type": "FeatureCollection", "features": []}

        try:
            asyncio.run(w.update_geodataframe(fake, "eez", "fake_gdf"))
            assert fake.messages[0][0] == "deck_set_source_data"
            assert fake.messages[0][1]["sourceId"] == "eez"
        finally:
            comp._serialise_data = original
```

---

### 4.3 Feature State Management

**Why**: MapLibre's feature state system allows interactive highlighting
without modifying source data — ideal for hover/select effects on native
layers. Combined with data-driven paint expressions like
`["case", ["boolean", ["feature-state", "hover"], false], "#f00", "#088"]`,
it enables performant interactive styling.

#### Python API — `components.py`

```python
async def set_feature_state(
    self,
    session,
    source_id: str,
    feature_id: str | int,
    state: dict,
    *,
    source_layer: str | None = None,
) -> None:
    """Set the state of a feature in a source.

    Feature state is used with data-driven styling expressions like
    ``["feature-state", "hover"]`` in paint properties.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        The source containing the feature.
    feature_id
        The feature's unique identifier (from GeoJSON ``id`` property
        or ``promoteId`` option).
    state
        State properties to set, e.g. ``{"hover": True, "selected": False}``.
    source_layer
        Required for vector tile sources. Not needed for GeoJSON.
    """
    payload: dict = {
        "id": self.id,
        "sourceId": source_id,
        "featureId": feature_id,
        "state": state,
    }
    if source_layer is not None:
        payload["sourceLayer"] = source_layer
    await session.send_custom_message("deck_set_feature_state", payload)


async def remove_feature_state(
    self,
    session,
    source_id: str,
    feature_id: str | int | None = None,
    *,
    key: str | None = None,
    source_layer: str | None = None,
) -> None:
    """Remove feature state.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    source_id
        The source containing the feature(s).
    feature_id
        Feature to clear state for. ``None`` clears all features.
    key
        Specific state key to remove. ``None`` removes all state keys.
    source_layer
        Required for vector tile sources.
    """
    payload: dict = {
        "id": self.id,
        "sourceId": source_id,
    }
    if feature_id is not None:
        payload["featureId"] = feature_id
    if key is not None:
        payload["key"] = key
    if source_layer is not None:
        payload["sourceLayer"] = source_layer
    await session.send_custom_message("deck_remove_feature_state", payload)
```

#### JS Handlers — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_set_feature_state
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_set_feature_state", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var target = { source: payload.sourceId, id: payload.featureId };
    if (payload.sourceLayer) target.sourceLayer = payload.sourceLayer;

    instance.map.setFeatureState(target, payload.state);
});


// -----------------------------------------------------------------------
// deck_remove_feature_state
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_remove_feature_state", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var target = { source: payload.sourceId };
    if (payload.featureId != null) target.id = payload.featureId;
    if (payload.sourceLayer) target.sourceLayer = payload.sourceLayer;

    if (payload.key) {
        instance.map.removeFeatureState(target, payload.key);
    } else {
        instance.map.removeFeatureState(target);
    }
});
```

#### Usage Example
```python
# Paint expression using feature state
await widget.add_maplibre_layer(session, {
    "id": "stations-circles",
    "type": "circle",
    "source": "stations",
    "paint": {
        "circle-radius": [
            "case",
            ["boolean", ["feature-state", "hover"], False],
            10, 5
        ],
        "circle-color": [
            "case",
            ["boolean", ["feature-state", "selected"], False],
            "#ff0000", "#0088cc"
        ],
    }
})

# On hover (from JS → Python → set_feature_state)
@reactive.Effect
@reactive.event(input.map_feature_click)
async def on_feature_click():
    click = input.map_feature_click()
    feature_id = click["properties"].get("id")
    if feature_id:
        await widget.set_feature_state(session, "stations", feature_id,
                                        {"selected": True})
```

#### Tests
```python
class TestFeatureState:
    def test_set_feature_state(self):
        import asyncio
        w = MapWidget("fs1")
        fake = FakeSession()
        asyncio.run(w.set_feature_state(fake, "stations", 42,
                                          {"hover": True, "selected": False}))
        msg = fake.messages[0]
        assert msg[0] == "deck_set_feature_state"
        assert msg[1]["sourceId"] == "stations"
        assert msg[1]["featureId"] == 42
        assert msg[1]["state"] == {"hover": True, "selected": False}

    def test_set_feature_state_vector_source(self):
        import asyncio
        w = MapWidget("fs2")
        fake = FakeSession()
        asyncio.run(w.set_feature_state(fake, "osm", "abc",
                                          {"hover": True},
                                          source_layer="buildings"))
        assert fake.messages[0][1]["sourceLayer"] == "buildings"

    def test_remove_feature_state_specific(self):
        import asyncio
        w = MapWidget("fs3")
        fake = FakeSession()
        asyncio.run(w.remove_feature_state(fake, "stations", 42, key="hover"))
        msg = fake.messages[0]
        assert msg[0] == "deck_remove_feature_state"
        assert msg[1]["featureId"] == 42
        assert msg[1]["key"] == "hover"

    def test_remove_feature_state_all(self):
        import asyncio
        w = MapWidget("fs4")
        fake = FakeSession()
        asyncio.run(w.remove_feature_state(fake, "stations"))
        msg = fake.messages[0][1]
        assert "featureId" not in msg
        assert "key" not in msg
```

---

### 4.4 Map Export / Screenshot

**Why**: Users need to export their map view as an image for publications,
reports, and presentations. `map.getCanvas().toDataURL()` provides a
quick screenshot, while `map.getCanvas().toBlob()` can produce a
downloadable file.

#### Python API — `components.py`

```python
async def export_image(
    self,
    session,
    *,
    format: str = "png",
    quality: float = 0.92,
    request_id: str = "default",
) -> None:
    """Request a screenshot of the map.

    The base64-encoded image is returned asynchronously as
    ``input.{id}_export_result()``.

    Parameters
    ----------
    session
        The active Shiny ``Session``.
    format
        Image format: ``"png"`` (default) or ``"jpeg"``.
    quality
        JPEG quality (0.0–1.0). Ignored for PNG.
    request_id
        Identifier included in the result for request matching.

    Example
    -------
    ::

        await widget.export_image(session, format="png")

        @reactive.Effect
        @reactive.event(input.my_map_export_result)
        def on_export():
            result = input.my_map_export_result()
            data_url = result["dataUrl"]  # "data:image/png;base64,..."
            # Write to file, display in UI, etc.
    """
    await session.send_custom_message("deck_export_image", {
        "id": self.id,
        "format": format,
        "quality": quality,
        "requestId": request_id,
    })
```

#### New Shiny Input: `{id}_export_result`
```python
@property
def export_result_input_id(self) -> str:
    """Shiny input for map export results.

    Returns ``{requestId: str, dataUrl: str, width: int, height: int}``.
    """
    return f"{self.id}_export_result"
```

#### JS Handler — `deckgl-init.js`

```javascript
// -----------------------------------------------------------------------
// deck_export_image — screenshot the map canvas
// -----------------------------------------------------------------------
Shiny.addCustomMessageHandler("deck_export_image", function (payload) {
    if (!payload || !payload.id) return;
    var instance = ensureInstance(payload.id);
    if (!instance) return;

    var map = instance.map;
    var canvas = map.getCanvas();
    var format = payload.format === 'jpeg' ? 'image/jpeg' : 'image/png';
    var quality = payload.quality || 0.92;

    // Force a render before capturing
    map.triggerRepaint();

    // Use requestAnimationFrame to ensure the frame is rendered
    requestAnimationFrame(function () {
        var dataUrl = canvas.toDataURL(format, quality);
        Shiny.setInputValue(payload.id + '_export_result', {
            requestId: payload.requestId || 'default',
            dataUrl: dataUrl,
            width: canvas.width,
            height: canvas.height
        }, { priority: "event" });
    });
});
```

#### Important: `preserveDrawingBuffer`

For `toDataURL()` to work, MapLibre must be initialised with
`preserveDrawingBuffer: true`. This must be added to `initMap()`:

```javascript
// In initMap(), add to mapOpts:
var mapOpts = {
    container: mapId,
    style: mapStyle,
    center: [initLon, initLat],
    zoom: initZoom,
    pitch: initPitch,
    bearing: initBearing,
    minZoom: initMinZoom,
    maxZoom: initMaxZoom,
    preserveDrawingBuffer: true   // NEW — required for export_image()
};
```

> **Note**: `preserveDrawingBuffer: true` has a minor performance cost.
> Consider making this opt-in via a `MapWidget` constructor parameter
> or data attribute.

#### Tests
```python
class TestExportImage:
    def test_export_image_png(self):
        import asyncio
        w = MapWidget("exp1")
        fake = FakeSession()
        asyncio.run(w.export_image(fake, format="png"))
        msg = fake.messages[0]
        assert msg[0] == "deck_export_image"
        assert msg[1]["format"] == "png"
        assert msg[1]["quality"] == 0.92

    def test_export_image_jpeg(self):
        import asyncio
        w = MapWidget("exp2")
        fake = FakeSession()
        asyncio.run(w.export_image(fake, format="jpeg", quality=0.8,
                                    request_id="report"))
        msg = fake.messages[0][1]
        assert msg["format"] == "jpeg"
        assert msg["quality"] == 0.8
        assert msg["requestId"] == "report"

    def test_export_result_input_id(self):
        w = MapWidget("exp3")
        assert w.export_result_input_id == "exp3_export_result"
```

---

## Implementation Order & Dependencies

```
Phase 1 (v0.2.0) — Foundation:
┌─────────────────────────────────────────────┐
│ 1.1 MapLibre v5 upgrade  ← DO FIRST        │
│     (unlocks globe, terrain, controls)      │
├─────────────────────────────────────────────┤
│ 1.2 Controls API         ← independent     │
│ 1.3 fit_bounds()         ← independent     │
│ 1.4 Bounds feedback      ← independent     │
│ 1.5 Map click events     ← independent     │
└─────────────────────────────────────────────┘

Phase 2 (v0.3.0) — Native Rendering:
┌─────────────────────────────────────────────┐
│ 2.1 Sources & Layers     ← DO FIRST        │
│     (2.2 depends on this)                   │
├─────────────────────────────────────────────┤
│ 2.2 Style mutation       ← needs 2.1       │
└─────────────────────────────────────────────┘

Phase 3 (v0.4.0) — 3D & Advanced Interaction:
┌─────────────────────────────────────────────┐
│ 3.1 Globe projection     ← needs 1.1       │
│ 3.2 3D Terrain + Sky     ← needs 1.1 + 2.1 │
│ 3.3 Native popups        ← needs 2.1       │
│ 3.4 Spatial queries      ← needs 2.1       │
│ 3.5 Multiple markers     ← independent     │
└─────────────────────────────────────────────┘

Phase 4 (v0.5.0) — Data & Export:
┌─────────────────────────────────────────────┐
│ 4.1 Drawing tools        ← independent     │
│ 4.2 GeoPandas helper     ← needs 2.1 + 3.3 │
│ 4.3 Feature state        ← needs 2.1       │
│ 4.4 Export / screenshot   ← independent     │
└─────────────────────────────────────────────┘
```

---

## Estimated Line Counts

| Feature | components.py | deckgl-init.js | test_basic.py |
|---------|:---:|:---:|:---:|
| **Phase 1 (v0.2.0)** | | | |
| 1.1 MapLibre upgrade | ~4 | 0 | ~10 |
| 1.2 Controls | ~60 | ~70 | ~30 |
| 1.3 fit_bounds() | ~40 | ~20 | ~30 |
| 1.4 Bounds feedback | ~8 | ~6 | 0 |
| 1.5 Map click | ~12 | ~16 | ~10 |
| **Phase 1 total** | **~124** | **~112** | **~80** |
| **Phase 2 (v0.3.0)** | | | |
| 2.1 Sources & layers | ~100 | ~80 | ~50 |
| 2.2 Style mutation | ~60 | ~30 | ~25 |
| **Phase 2 total** | **~160** | **~110** | **~75** |
| **Phase 3 (v0.4.0)** | | | |
| 3.1 Globe projection | ~20 | ~12 | ~15 |
| 3.2 3D Terrain + Sky | ~40 | ~20 | ~20 |
| 3.3 Native popups | ~45 | ~55 | ~20 |
| 3.4 Spatial queries | ~55 | ~50 | ~25 |
| 3.5 Multiple markers | ~55 | ~55 | ~30 |
| **Phase 3 total** | **~215** | **~192** | **~110** |
| **Phase 4 (v0.5.0)** | | | |
| 4.1 Drawing tools | ~70 | ~80 | ~30 |
| 4.2 GeoPandas helper | ~60 | 0 | ~30 |
| 4.3 Feature state | ~45 | ~25 | ~20 |
| 4.4 Export / screenshot | ~25 | ~20 | ~15 |
| **Phase 4 total** | **~200** | **~125** | **~95** |
| | | | |
| **Grand total (all phases)** | **~699** | **~539** | **~360** |

Post-implementation estimated file sizes:
- `components.py`: ~1,506 lines (currently 807)
- `deckgl-init.js`: ~1,128 lines (currently 589)
- `test_basic.py`: ~1,210 lines (currently ~850)
- **Total**: ~3,844 lines (currently 2,246)

---

## Cumulative Message Handler Inventory

### Py → JS Custom Message Handlers

| Channel | Phase | Method |
|---------|:---:|--------|
| `deck_update` | v0.1.0 | `update()` |
| `deck_layer_visibility` | v0.1.0 | `set_layer_visibility()` |
| `deck_add_drag_marker` | v0.1.0 | `add_drag_marker()` |
| `deck_set_style` | v0.1.0 | `set_style()` |
| `deck_update_tooltip` | v0.1.0 | `update_tooltip()` |
| `deck_add_control` | v0.2.0 | `add_control()` |
| `deck_remove_control` | v0.2.0 | `remove_control()` |
| `deck_fit_bounds` | v0.2.0 | `fit_bounds()` |
| `deck_add_source` | v0.3.0 | `add_source()` |
| `deck_add_maplibre_layer` | v0.3.0 | `add_maplibre_layer()` |
| `deck_remove_maplibre_layer` | v0.3.0 | `remove_maplibre_layer()` |
| `deck_remove_source` | v0.3.0 | `remove_source()` |
| `deck_set_source_data` | v0.3.0 | `set_source_data()` |
| `deck_set_paint_property` | v0.3.0 | `set_paint_property()` |
| `deck_set_layout_property` | v0.3.0 | `set_layout_property()` |
| `deck_set_filter` | v0.3.0 | `set_filter()` |
| `deck_set_projection` | v0.4.0 | `set_projection()` |
| `deck_set_terrain` | v0.4.0 | `set_terrain()` |
| `deck_set_sky` | v0.4.0 | `set_sky()` |
| `deck_add_popup` | v0.4.0 | `add_popup()` |
| `deck_remove_popup` | v0.4.0 | `remove_popup()` |
| `deck_query_features` | v0.4.0 | `query_rendered_features()` |
| `deck_query_at_lnglat` | v0.4.0 | `query_at_lnglat()` |
| `deck_add_marker` | v0.4.0 | `add_marker()` |
| `deck_remove_marker` | v0.4.0 | `remove_marker()` |
| `deck_clear_markers` | v0.4.0 | `clear_markers()` |
| `deck_enable_draw` | v0.5.0 | `enable_draw()` |
| `deck_disable_draw` | v0.5.0 | `disable_draw()` |
| `deck_get_drawn_features` | v0.5.0 | `get_drawn_features()` |
| `deck_delete_drawn` | v0.5.0 | `delete_drawn_features()` |
| `deck_set_feature_state` | v0.5.0 | `set_feature_state()` |
| `deck_remove_feature_state` | v0.5.0 | `remove_feature_state()` |
| `deck_export_image` | v0.5.0 | `export_image()` |

### JS → Py Shiny Inputs

| Input | Phase | Trigger |
|-------|:---:|---------|
| `{id}_view_state` | v0.1.0 | `moveend` (+ bounds in v0.2.0) |
| `{id}_click` | v0.1.0 | deck.gl layer onClick |
| `{id}_hover` | v0.1.0 | deck.gl layer onHover |
| `{id}_drag` | v0.1.0 | drag marker dragend |
| `{id}_map_click` | v0.2.0 | MapLibre map click |
| `{id}_map_contextmenu` | v0.2.0 | MapLibre right-click |
| `{id}_feature_click` | v0.4.0 | Native layer popup click |
| `{id}_query_result` | v0.4.0 | queryRenderedFeatures result |
| `{id}_marker_click` | v0.4.0 | Named marker click |
| `{id}_marker_drag` | v0.4.0 | Named marker dragend |
| `{id}_drawn_features` | v0.5.0 | Draw create/update/delete |
| `{id}_draw_mode` | v0.5.0 | Draw mode change |
| `{id}_export_result` | v0.5.0 | Canvas toDataURL result |

---

## Version Bump & Release Checklist

### v0.2.0 (Phase 1)
- [ ] Update `_version.py`: `__version__ = "0.2.0"`
- [ ] Update `pyproject.toml`: `version = "0.2.0"`
- [ ] Update `conda.recipe/meta.yaml`: `version: "0.2.0"`
- [ ] Update `HTMLDependency` version in `ui.py`
- [ ] Update CDN URLs in `ui.py` and `components.py` (MapLibre v5.3)
- [ ] Verify deck.gl `MapboxOverlay` works with MapLibre v5
- [ ] Run all tests (target: ~115 tests)
- [ ] Manual browser test with demo app
- [ ] Update README.md with new features
- [ ] Git tag `v0.2.0`, push to GitHub

### v0.3.0 (Phase 2)
- [ ] Same version bump pattern
- [ ] Run all tests (target: ~140 tests)
- [ ] Create WMS + native layers demo (EMODnet, HELCOM)
- [ ] Test with real WMS services (EMODnet bathymetry, Copernicus Marine)
- [ ] Git tag `v0.3.0`, push to GitHub

### v0.4.0 (Phase 3)
- [ ] Same version bump pattern
- [ ] Test globe projection with deck.gl overlay (note limitations)
- [ ] Test 3D terrain performance on target hardware (no GPU)
- [ ] Verify popup + feature click interaction with native layers
- [ ] Run all tests (target: ~175 tests)
- [ ] Create marine portal demo combining all features
- [ ] Git tag `v0.4.0`, push to GitHub

### v0.5.0 (Phase 4)
- [ ] Same version bump pattern
- [ ] Add `mapbox-gl-draw` CDN to `head_includes()` (conditional)
- [ ] Test MapboxDraw compatibility with MapLibre v5
- [ ] Test with real GeoPandas data (coastlines, EEZ shapefiles)
- [ ] Verify `preserveDrawingBuffer` for export_image()
- [ ] Run all tests (target: ~210 tests)
- [ ] Update README.md with complete feature overview
- [ ] Git tag `v0.5.0`, push to GitHub

---

## Marine Science Demo App (v0.4.0)

Target demo combining all features through Phase 3:

```python
from shiny import App, reactive, ui
import shiny_deckgl as sdgl

widget = sdgl.MapWidget(
    "map",
    view_state={"longitude": 20, "latitude": 58, "zoom": 5},
    style=sdgl.CARTO_POSITRON,
    tooltip={"html": "<b>{name}</b><br>Depth: {depth} m"},
)

app_ui = ui.page_navbar(
    sdgl.head_includes(),
    ui.nav_panel("Baltic Sea",
        widget.ui(height="100vh"),
        ui.output_text("click_info"),
    ),
    title="Marine Data Portal",
)

def server(input, output, session):
    @reactive.Effect
    async def setup():
        # Controls
        await widget.add_control(session, "scale", "bottom-left",
                                  options={"unit": "nautical"})
        await widget.add_control(session, "fullscreen", "top-left")

        # EMODnet bathymetry (WMS raster via native source)
        await widget.add_source(session, "bathy", {
            "type": "raster",
            "tiles": [
                "https://ows.emodnet-bathymetry.eu/wms?"
                "SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
                "&LAYERS=emodnet:mean_atlas_land"
                "&SRS=EPSG:3857&FORMAT=image/png&TRANSPARENT=true"
                "&WIDTH=256&HEIGHT=256&BBOX={bbox-epsg-3857}"
            ],
            "tileSize": 256,
        })
        await widget.add_maplibre_layer(session, {
            "id": "bathy-layer",
            "type": "raster",
            "source": "bathy",
            "paint": {"raster-opacity": 0.6},
        })

        # EEZ boundaries (native GeoJSON)
        await widget.add_source(session, "eez", {
            "type": "geojson",
            "data": "https://example.com/baltic-eez.geojson",
        })
        await widget.add_maplibre_layer(session, {
            "id": "eez-line",
            "type": "line",
            "source": "eez",
            "paint": {"line-color": "#ff6600", "line-width": 2,
                      "line-dasharray": [4, 2]},
        })
        await widget.add_popup(session, "eez-line",
                                "<b>{GEONAME}</b><br>Area: {AREA_KM2} km²")

        # Station markers
        for station in STATIONS:
            await widget.add_marker(session, station["id"],
                                     station["lng"], station["lat"],
                                     color="#0088cc",
                                     popup_html=f"<b>{station['name']}</b>")

        # Fit to Baltic Sea
        await widget.fit_bounds(session, [[9, 53], [31, 66]], padding=30)

        # deck.gl heatmap overlay
        heatmap = sdgl.layer("HeatmapLayer", "obs-heat",
                              data=observations,
                              getPosition="@@=d.coordinates",
                              getWeight="@@=d.count",
                              radiusPixels=40)
        await widget.update(session, [heatmap])

    @reactive.Effect
    @reactive.event(input.map_map_click)
    async def on_click():
        click = input.map_map_click()
        # Spatial query at click location
        await widget.query_rendered_features(
            session,
            point=[click["point"]["x"], click["point"]["y"]],
            layers=["eez-line"],
            request_id="eez-check"
        )

    @reactive.Effect
    @reactive.event(input.map_query_result)
    def on_query():
        result = input.map_query_result()
        features = result.get("features", [])
        if features:
            name = features[0]["properties"].get("GEONAME", "Unknown")
            print(f"Clicked inside: {name}")

app = App(app_ui, server)
```
