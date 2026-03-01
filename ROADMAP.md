# shiny_deckgl — Development Roadmap

> Research report & prioritised feature plan for v0.2.0+
> Generated: 2025-01

---

## 1. Current State (v0.1.0)

### Architecture
- **Python side**: `MapWidget` class wraps deck.gl layer specs, serialises to JSON, sends via Shiny custom messages (`session.send_custom_message`).
- **JS side**: `deckgl-init.js` (~589 lines) creates a MapLibre GL JS map, attaches a `MapboxOverlay` (deck.gl), and listens to 6 message channels.
- **Communication**: Py→JS via 6 channels (`deck_update`, `deck_layer_visibility`, `deck_add_drag_marker`, `deck_set_style`, `deck_update_tooltip`); JS→Py via `Shiny.setInputValue` (view state, marker position).

### What MapLibre GL JS is used for today
| Feature | Usage |
|---------|-------|
| Map creation | `new maplibregl.Map({...})` with style, center, zoom, pitch, bearing |
| NavigationControl | Hardcoded top-right |
| Camera animation | `flyTo()`, `jumpTo()` |
| Style switching | `map.setStyle()` (4 basemap constants) |
| Single draggable marker | `new maplibregl.Marker({draggable: true})` |
| View state feedback | `moveend` event → `Shiny.setInputValue` |
| Resize & repaint | `map.resize()`, `map.triggerRepaint()` |
| deck.gl integration | `MapboxOverlay` with `interleaved: false` |

### What MapLibre GL JS is **NOT** used for
Everything else. MapLibre is treated as a **passive basemap container** — all data visualisation is routed through deck.gl overlay. None of the native MapLibre rendering, interaction, or spatial query capabilities are exposed.

---

## 2. Ecosystem Landscape

### py-maplibregl (package: `maplibre`) — Primary Competitor
- **Version**: 0.3.6 (MapLibre GL JS v5.3.0), 95 GitHub stars
- **Integrations**: Shiny for Python, Marimo, Jupyter, JupyterLite, Streamlit
- **Architecture**: `Map` → `MapContext` (Shiny async updates), `MapWidget` (Jupyter/Marimo)
- **Key features exposed**:
  - `add_source()`, `add_layer()`, `set_data()` — full MapLibre native rendering
  - `set_paint_property()`, `set_layout_property()`, `set_filter()` — runtime style mutation
  - `fit_bounds()`, `set_visibility()`, `set_terrain()`, `set_projection()` (Globe!)
  - `set_sky()`, `set_light()` — atmosphere & lighting
  - All controls: Navigation, Scale, Fullscreen, Geolocate, Globe, Terrain, LayerSwitcher, InfoBox, MapTiler Geocoding
  - Native `Popup`, `Marker` (with popup), `add_popup()`, `add_tooltip()` on layers
  - Deck.GL layers via `add_deck_layers()` / `set_deck_layers()` — **they also support deck.gl!**
  - MapboxDraw plugin for geometry editing
  - Sources: GeoJSON, VectorTile, RasterTile, RasterDEM
  - Reactive inputs: `{id}_clicked`, `{id}_feature_clicked`, `{id}_view_state`
  - `add_call()` — generic method passthrough to JS map instance

### MapLibre GL JS — Latest Version (v5.19.0)
Our CDN uses **v3.6.2** — we are **2 major versions behind**. Key additions since v3.6:
- **Globe projection** (`setProjection({type: 'globe'})`) — v4.0+
- **GlobeControl** — UI toggle between mercator and globe
- **3D terrain** improvements, `queryTerrainElevation()`
- **Sky & atmosphere** (`setSky()`, atmosphere blend)
- **Camera roll** (`setRoll()`, `getRoll()`)
- **Global state** (`setGlobalStateProperty()`) for data-driven styling
- **Level of Detail** tile control (`setSourceTileLodParams()`)
- **Cooperative gestures** handler
- Performance improvements, WebGL2 by default

### Other Python Mapping Libraries
| Library | Rendering | Shiny? | Strengths | Weaknesses |
|---------|-----------|--------|-----------|------------|
| **pydeck** | deck.gl via Jupyter widget | Limited | Official deck.gl bindings | No Shiny integration, limited interactivity |
| **folium** | Leaflet.js | Via `ui.output_ui` | Simple, mature | No deck.gl, no 3D, static |
| **ipyleaflet** | Leaflet.js | Jupyter only | Mature widget | No Shiny, no WebGL layers |
| **lonboard** | deck.gl + GeoArrow | Jupyter/Marimo | Ultra fast binary | No Shiny, no basemap interaction |
| **leafmap** | Multiple backends | Jupyter | High-level GIS | No native Shiny |

### R Ecosystem (Inspiration)
| Package | Notes |
|---------|-------|
| **leaflet** | Gold standard for R Shiny maps, excellent proxy pattern |
| **rdeck** | deck.gl for R, similar to our approach |
| **mapboxer** | Mapbox GL JS for R, good source/layer pattern |
| **mapgl** (by Kyle Walker) | MapLibre for R Shiny, comprehensive |

---

## 3. Strategic Analysis

### Our Unique Position
`shiny_deckgl` is the **only** package that combines:
1. Full deck.gl v9 with binary transport in Shiny for Python
2. 17 deck.gl layer types with extensions (DataFilter, Brushing)
3. Reactive Shiny integration (view state, markers)

### The `py-maplibregl` Overlap Problem
`py-maplibregl` already has deck.gl support via `add_deck_layers()`. However, their deck.gl integration uses a **dictionary-based** `@@type` / `@@=` convention, not Python layer objects. Our approach with full Python classes, binary transport, and named layer helpers is more ergonomic for heavy deck.gl workloads.

### Strategic Options

| Option | Description | Effort | Risk |
|--------|-------------|--------|------|
| **A. Enhance shiny_deckgl** | Add MapLibre native features alongside deck.gl | High | Duplicating py-maplibregl work |
| **B. Merge with py-maplibregl** | Contribute deck.gl improvements upstream | Medium | Loss of control, different architecture |
| **C. Complementary package** | Keep deck.gl focus, add py-maplibregl as dependency | Low | Two packages to maintain |
| **D. Fork py-maplibregl JS** | Use their maplibre-bindings JS, build Python on top | Medium | Keeping in sync |

**Recommendation: Option A (Enhance) for v0.2.0, consider Option B/C for v0.3.0+**

Rationale: Our deck.gl + marine science focus is distinct enough to justify a standalone package. Adding targeted MapLibre features (the ones marine GIS apps actually need) gives us clear value without trying to replicate the full py-maplibregl API.

---

## 4. Prioritised Feature Roadmap

### Phase 1: Foundation (v0.2.0) — High Impact, Moderate Effort

#### 1.1 Upgrade MapLibre GL JS to v5.x
- **Current**: v3.6.2 via CDN
- **Target**: v5.3+ (latest stable)
- **Impact**: Globe projection, terrain improvements, performance, cooperative gestures
- **Effort**: Update CDN URLs in `ui.py`, test for breaking changes with `MapboxOverlay`
- **Risk**: deck.gl v9 compatibility with MapLibre v5 needs verification
- **Marine relevance**: 🌊🌊🌊 Globe projection is excellent for showing ocean basins

#### 1.2 Native MapLibre Controls
Expose Python API for adding/removing controls:
```python
widget.add_control("scale", position="bottom-left")
widget.add_control("fullscreen", position="top-left")
widget.add_control("geolocate", position="top-right")
```
- **Controls to add**: ScaleControl, FullscreenControl, GeolocateControl, GlobeControl, TerrainControl
- **JS changes**: New message handler `deck_add_control` / `deck_remove_control`
- **Marine relevance**: 🌊🌊🌊 Scale bar essential for scientific maps

#### 1.3 `fit_bounds()` Support
```python
widget.fit_bounds(sw=[10.0, 54.0], ne=[30.0, 66.0], padding=50)
# or from data:
widget.fit_bounds(data=geojson_features)
```
- **JS changes**: New message handler calling `map.fitBounds()`
- **Marine relevance**: 🌊🌊🌊 Critical for "zoom to study area" workflows

#### 1.4 Map Bounds Feedback
Send `map.getBounds()` to Python on `moveend`:
```python
# in server:
@reactive.Effect
@reactive.event(input.deckgl_bounds)
def on_bounds_change():
    bounds = input.deckgl_bounds()  # {sw: [lng, lat], ne: [lng, lat]}
```
- **Marine relevance**: 🌊🌊 Enables "load data for visible area" patterns

#### 1.5 Click Events with Coordinates
Wire `map.on('click')` to send click location + any deck.gl picked object:
```python
@reactive.Effect
@reactive.event(input.deckgl_clicked)
def on_click():
    click = input.deckgl_clicked()  # {lng, lat, x, y, object: {...}}
```
- Already partially done via deck.gl `onClick`, but needs MapLibre-level click too
- **Marine relevance**: 🌊🌊🌊 "Click on station to show data" is the #1 marine GIS pattern

### Phase 2: Native Rendering (v0.3.0) — High Impact, High Effort

#### 2.1 Native GeoJSON Sources & Layers
Allow adding MapLibre-native vector layers alongside deck.gl:
```python
widget.add_source("eez", {
    "type": "geojson",
    "data": "https://example.com/eez.geojson"
})
widget.add_layer({
    "id": "eez-fill",
    "type": "fill",
    "source": "eez",
    "paint": {"fill-color": "#088", "fill-opacity": 0.4}
})
```
- **Use case**: Basemap overlays (EEZ boundaries, MPAs, grid lines) that don't need deck.gl's power
- **JS changes**: `deck_add_source`, `deck_add_layer`, `deck_remove_layer`, `deck_set_data` handlers
- **Marine relevance**: 🌊🌊🌊 EEZ/HELCOM boundaries, MPA polygons, coastlines

#### 2.2 WMS/WMTS Raster Tile Sources
```python
widget.add_source("bathymetry", {
    "type": "raster",
    "tiles": ["https://ows.emodnet-bathymetry.eu/wms?...&bbox={bbox-epsg-3857}"],
    "tileSize": 256
})
widget.add_layer({
    "id": "bathymetry-layer",
    "type": "raster",
    "source": "bathymetry"
})
```
- **Marine relevance**: 🌊🌊🌊🌊 EMODnet bathymetry, Copernicus Marine, HELCOM maps — this is a killer feature for marine science

#### 2.3 Vector Tile Sources
Support PMTiles and MVT tile endpoints:
```python
widget.add_source("osm-land", {
    "type": "vector",
    "url": "pmtiles://https://example.com/land.pmtiles"
})
```
- Requires MapLibre PMTiles protocol plugin
- **Marine relevance**: 🌊🌊 Efficient coastline/land boundaries

#### 2.4 Runtime Style Mutation
```python
widget.set_paint_property("eez-fill", "fill-opacity", 0.8)
widget.set_filter("stations", [">=", ["get", "depth"], 100])
widget.set_layout_property("labels", "visibility", "none")
```
- **JS changes**: `deck_set_paint_property`, `deck_set_filter`, `deck_set_layout_property` handlers
- **Marine relevance**: 🌊🌊 Data-driven styling of MapLibre native layers

### Phase 3: 3D & Advanced (v0.4.0) — Moderate Impact, High Effort

#### 3.1 3D Terrain
```python
widget.add_source("terrain-dem", {
    "type": "raster-dem",
    "url": "https://demotiles.maplibre.org/terrain-tiles/tiles.json",
    "tileSize": 256
})
widget.set_terrain(source="terrain-dem", exaggeration=1.5)
widget.set_sky({"atmosphere-blend": 0.8})
```
- **Marine relevance**: 🌊🌊 Coastal terrain visualisation (though no GPU on your machine)

#### 3.2 Native Popups
Replace custom DIV tooltips with MapLibre Popup for native layers:
```python
widget.add_popup("stations-layer", template="<b>{{name}}</b><br>Depth: {{depth}}m")
```
- **Marine relevance**: 🌊🌊 Better UX for station/feature identification

#### 3.3 Spatial Queries
```python
# Query features at a point
features = widget.query_rendered_features(lng=20.5, lat=55.3, layers=["stations"])
```
- Requires JS→Py message with `queryRenderedFeatures()` result
- **Marine relevance**: 🌊🌊🌊 Essential for "what's here?" interactions

#### 3.4 Globe Projection
```python
widget.set_projection("globe")
```
- Requires MapLibre v4+ (Phase 1.1 prerequisite)
- **Marine relevance**: 🌊🌊🌊 Beautiful for showing global ocean data

#### 3.5 Multiple Markers
Support adding/removing multiple markers (currently limited to 1):
```python
for station in stations:
    widget.add_marker(lng=station.lng, lat=station.lat, 
                     popup=f"<b>{station.name}</b>", color="#ff6600")
```
- **Marine relevance**: 🌊🌊 Station markers with popups

### Phase 4: Polish & Ecosystem (v0.5.0+)

#### 4.1 Custom Images / Icons
```python
widget.add_image("buoy-icon", "path/to/buoy.png")
# Then use in a symbol layer
```

#### 4.2 Feature State Management
```python
widget.set_feature_state("stations", feature_id=42, state={"hover": True})
```

#### 4.3 Drawing Tools
Integrate MapboxDraw or similar for polygon/line drawing:
```python
widget.enable_draw(modes=["polygon", "line"])
# input.deckgl_drawn_features → GeoJSON
```

#### 4.4 GeoPandas Integration
```python
import geopandas as gpd
gdf = gpd.read_file("stations.geojson")
widget.add_geodataframe("stations", gdf, paint={...})
```

#### 4.5 Export / Screenshot
```python
widget.export_image()  # map.getCanvas().toDataURL()
```

---

## 5. Technical Implementation Notes

### JS Message Handler Pattern
The current architecture uses `Shiny.addCustomMessageHandler(channel, callback)`. Each new feature needs:
1. A Python method on `MapWidget` that calls `session.send_custom_message(channel, data)`
2. A JS handler in `deckgl-init.js` that processes the message

This scales well. The main risk is `deckgl-init.js` growing too large — consider splitting into modules when it exceeds ~1000 lines.

### CDN Upgrade Path (MapLibre v3 → v5)
```
# Current
https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.2/

# Target
https://cdn.jsdelivr.net/npm/maplibre-gl@5.3.1/
```
Potential breaking changes:
- CSS class names may have changed
- `MapboxOverlay` from `@deck.gl/mapbox` needs testing with v5
- Globe projection only works with v4+

### deck.gl + MapLibre Native Layer Ordering
When `interleaved: false`, deck.gl renders on top of all MapLibre layers. If we add native MapLibre layers, we need to decide:
- Keep `interleaved: false` (deck.gl always on top) — simpler
- Switch to `interleaved: true` — allows mixing layer order, but more complex

**Recommendation**: Default `interleaved: false`, add option to enable interleaving.

---

## 6. Priority Matrix

| Feature | Marine Impact | User Demand | Effort | Priority |
|---------|:---:|:---:|:---:|:---:|
| Upgrade MapLibre to v5 | ★★★ | ★★★ | ★☆☆ | **P0** |
| ScaleControl | ★★★ | ★★★ | ★☆☆ | **P0** |
| fit_bounds() | ★★★ | ★★★ | ★☆☆ | **P0** |
| Click events | ★★★ | ★★★ | ★★☆ | **P0** |
| Map bounds feedback | ★★☆ | ★★☆ | ★☆☆ | **P1** |
| Fullscreen / Geolocate | ★★☆ | ★★★ | ★☆☆ | **P1** |
| WMS raster tiles | ★★★★ | ★★★ | ★★☆ | **P1** |
| Native GeoJSON layers | ★★★ | ★★☆ | ★★★ | **P1** |
| Globe projection | ★★★ | ★★☆ | ★☆☆ | **P1** |
| Paint/filter mutation | ★★☆ | ★★☆ | ★★☆ | **P2** |
| 3D terrain | ★★☆ | ★☆☆ | ★★★ | **P2** |
| Native popups | ★★☆ | ★★☆ | ★★☆ | **P2** |
| Spatial queries | ★★★ | ★☆☆ | ★★★ | **P2** |
| Multiple markers | ★★☆ | ★★☆ | ★★☆ | **P2** |
| Vector tiles / PMTiles | ★★☆ | ★☆☆ | ★★★ | **P3** |
| Drawing tools | ★★☆ | ★☆☆ | ★★★ | **P3** |
| GeoPandas integration | ★★☆ | ★★☆ | ★★☆ | **P3** |
| Feature state | ★☆☆ | ★☆☆ | ★★☆ | **P3** |
| Custom images | ★★☆ | ★☆☆ | ★★☆ | **P3** |
| Export/screenshot | ★☆☆ | ★★☆ | ★★☆ | **P3** |

---

## 7. Differentiation Strategy vs py-maplibregl

Instead of competing head-to-head, position `shiny_deckgl` as:

> **"deck.gl-first mapping for Shiny for Python"** — the best choice when you need
> GPU-accelerated large-dataset visualisation (scatter plots of millions of points,
> heatmaps, 3D columns, arcs, binary transport) on top of a MapLibre basemap.

While `py-maplibregl` is:

> **"MapLibre-first mapping for multiple frameworks"** — the best choice when you need
> rich MapLibre native rendering (vector tiles, expressions, feature state,
> clustering) across Shiny, Jupyter, Marimo, Streamlit.

This means:
1. **Don't** try to replicate every MapLibre feature → focus on the ones marine GIS needs
2. **Do** keep the best deck.gl integration in the ecosystem
3. **Do** add the MapLibre features that complement deck.gl (WMS tiles, GeoJSON boundaries, controls, bounds, click events)
4. Eventually consider making the two packages interoperable

---

## 8. Quick Wins (Can Be Done This Week)

1. **Add ScaleControl** — ~10 lines of JS + ~5 lines of Python
2. **Add FullscreenControl** — same pattern
3. **Wire `map.getBounds()` on moveend** — ~5 lines of JS
4. **Add `fit_bounds()` method** — ~15 lines each side
5. **Wire `map.on('click')` to Shiny** — ~10 lines of JS
6. **Update MapLibre CDN to v5.3** — change 2 URLs in `ui.py`

These 6 items would dramatically improve the package's usefulness for marine science applications with minimal effort.
