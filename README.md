# shiny_deckgl

## Shiny for Python → deck.gl bridge (Java-free)

A lightweight library for integrating [deck.gl](https://deck.gl/) (v9.2.10) and
[MapLibre GL JS](https://maplibre.org/) (v5.3.1) into
[Shiny for Python](https://shiny.posit.co/py/) applications.
Built for marine science and GIS visualisation — WMS layers, EMODnet,
HELCOM, food web modelling — the package handles CDN asset injection, layer
construction, and bi-directional messaging between the Python server and the
browser, all without Java dependencies.

## Features

### Core (v0.1)

| Capability | Details |
| --- | --- |
| **Reusable `MapWidget`** | Drop-in widget with configurable initial view state, auto-render on connect, and `update()` to push new layers at any time. |
| **Layer helpers** | `scatterplot_layer()`, `geojson_layer()`, `tile_layer()`, `bitmap_layer()` — typed factory functions with sensible defaults and `**kwargs` pass-through. |
| **Generic `layer()`** | Any deck.gl layer class via `layer("HeatmapLayer", ...)`; the JS client resolves `deck[type]` dynamically. |
| **WMS / TileLayer** | First-class WMS support via `tile_layer()` — render EMODnet, GEBCO, or any `{bbox-epsg-3857}` service. |
| **Click & hover events** | Read click/hover results in Python via `input[widget.click_input_id]()` / `input[widget.hover_input_id]()`. |
| **Tooltips** | Configure `tooltip={"html": "<b>{name}</b>"}` on `MapWidget` for automatic hover tooltips with template interpolation. |
| **Viewport read-back** | `input[widget.view_state_input_id]()` gives lon/lat/zoom/pitch/bearing after every camera move. |
| **Basemap styles** | `CARTO_POSITRON`, `CARTO_DARK`, `CARTO_VOYAGER`, `OSM_LIBERTY` — or any MapLibre/Mapbox style URL. |
| **Mapbox API key** | `MapWidget(..., mapbox_api_key="pk.xxx")` to use `mapbox://` style URLs with automatic token injection. |
| **Color scales** | `color_range()`, `color_bins()`, `color_quantiles()` with 5 built-in palettes. |
| **Layer visibility** | `set_layer_visibility(session, {"layer1": False})` toggles layers without resending data. |
| **Draggable markers** | `add_drag_marker(session)` places a marker the user can reposition. |
| **DataFrame support** | Pass pandas DataFrames or GeoDataFrames directly as layer data — auto-converted to records / GeoJSON. |
| **Extensions** | `layer(..., extensions=["DataFilterExtension"])` — resolved on the client. |
| **Binary transport** | `encode_binary_attribute(np_array)` — base64-encodes numpy arrays for high-performance typed-array attributes. |
| **Lighting & effects** | Pass `effects=[{"type": "LightingEffect", ...}]` to `update()` for ambient/point/directional lighting. |
| **Multiple views** | `map_view()`, `orthographic_view()`, `first_person_view()` helpers for multi-view layouts. |
| **HTML export** | `widget.to_html(layers, path="map.html")` — standalone HTML file viewable in any browser. |
| **JSON spec** | `to_json()` / `from_json()` for serialising and restoring map configurations. |
| **`@@` accessor convention** | Python strings like `"@@d"` or `"@@d.position"` are resolved to JS arrow functions on the client. |
| **CDN-pinned assets** | deck.gl 9.2.10, MapLibre GL 5.3.1 — deterministic builds. |
| **Conda recipe** | Bundled `conda.recipe/meta.yaml` for micromamba / conda-build. |

### Phase 1 — Controls & Navigation (v0.2)

| Capability | Details |
| --- | --- |
| **MapLibre v5 upgrade** | Upgraded from MapLibre GL JS v3.6.2 to v5.3.1 (breaking API changes handled). |
| **Map controls** | `add_control(session, "NavigationControl")` — navigation, scale, fullscreen, geolocate, attribution, terrain. |
| **`remove_control()`** | Remove previously added controls by type. |
| **`fit_bounds()`** | Fly the camera to a bounding box with optional padding and animation. |
| **Map click events** | `input[widget.map_click_input_id]()` — clicks on the basemap (not on deck.gl layers). |

### Phase 2 — Native Sources & Layers (v0.3)

| Capability | Details |
| --- | --- |
| **`add_source()`** | Add native MapLibre sources (GeoJSON, vector, raster, raster-dem, image, video). |
| **`remove_source()`** | Remove a previously added source by id. |
| **`add_maplibre_layer()`** | Add native MapLibre style layers (fill, line, circle, symbol, heatmap, fill-extrusion, raster, hillshade). |
| **`remove_maplibre_layer()`** | Remove a native layer by id. |
| **`set_paint_property()` / `set_layout_property()`** | Mutate paint or layout properties on existing native layers. |
| **`set_filter()`** | Set a layer filter expression. |
| **`set_style()`** | Change the entire basemap style dynamically (warns that native layers will be lost). |
| **`add_image()` / `remove_image()`** | Load custom icons (PNG/SVG/WebP) for use with symbol layers; SDF recolouring supported. |

### Phase 3 — Globe, Terrain & Popups (v0.4)

| Capability | Details |
| --- | --- |
| **Globe projection** | `set_projection(session, "globe")` — switch between mercator and globe. |
| **Terrain** | `set_terrain(session, source, exaggeration)` — 3D terrain with DEM source. |
| **Popups** | `add_popup()` / `remove_popup()` — HTML popups on native MapLibre layers. |
| **Spatial queries** | `query_rendered_features()`, `query_at_lnglat()` — query visible features. |
| **Multiple markers** | `add_marker()`, `remove_marker()`, `clear_markers()` — programmatic markers with optional popups and drag support. |

### Phase 4 — Drawing, GeoPandas & Export (v0.5)

| Capability | Details |
| --- | --- |
| **Drawing tools** | `enable_draw()` / `disable_draw()` — MapboxDraw integration with point/line/polygon modes. |
| **Get/delete drawn features** | `get_drawn_features()`, `delete_drawn_features()` — manage drawn geometry. |
| **GeoPandas integration** | `add_geodataframe()` — directly add a GeoDataFrame as a GeoJSON source + native layers. |
| **Feature state** | `set_feature_state()` / `remove_feature_state()` — interactive styling without redrawing. |
| **Map export** | `export_image(format="png"/"jpeg"/"webp")` — screenshot the map as a base64 data URL. |

### Phase 5 — Control Helpers & Legend Plugins (v0.6)

| Capability | Details |
| --- | --- |
| **`set_controls()`** | Replace all MapLibre controls at once with a list of control specs. |
| **Control helpers** | `geolocate_control()`, `globe_control()`, `terrain_control()` — typed factory functions. |
| **Legend control** | `legend_control()` — native MapLibre layer legend with checkboxes (`@watergis/maplibre-gl-legend`). |
| **Opacity control** | `opacity_control()` — layer switcher with opacity sliders (`maplibre-gl-opacity`). |
| **deck.gl legend** | `deck_legend_control()` — custom legend panel for deck.gl overlay layers with 5 swatch shapes. |

### Phase 6 — Extended Layer Helpers (v0.7)

| Capability | Details |
| --- | --- |
| **10 new layer helpers** | `arc_layer()`, `icon_layer()`, `path_layer()`, `line_layer()`, `text_layer()`, `column_layer()`, `polygon_layer()`, `heatmap_layer()`, `hexagon_layer()`, `h3_hexagon_layer()`. |
| **Deck-level properties** | `parameters`, `effects`, `views` — full control over the deck.gl `Deck` instance through `update()`. |
| **Layer extensions** | `layer(..., extensions=["DataFilterExtension"])` with auto-resolution on the client. |

### Phase 7 — Widgets, Camera Transitions & Globe (v0.8)

| Capability | Details |
| --- | --- |
| **deck.gl widgets** | `set_widgets()` with 17 helpers: `zoom_widget()`, `compass_widget()`, `fullscreen_widget()`, `scale_widget()`, `gimbal_widget()`, `reset_view_widget()`, `screenshot_widget()`, `fps_widget()`, `loading_widget()`, `timeline_widget()`, `geocoder_widget()`, `theme_widget()` + 5 experimental. |
| **Camera transitions** | `fly_to(longitude, latitude, zoom, speed)` — smooth MapLibre flyTo animation. |
| | `ease_to(longitude, latitude, zoom, duration)` — linear easeTo animation. |
| **Transition helper** | `transition(duration, easing, type)` — animate layer property changes on data update. |
| **Globe view** | `globe_view()` — render the earth as a 3D globe with `GlobeView`. |
| **deck.gl 9.2.10** | CDN upgraded from 9.1.4 to 9.2.10 with widget support. |

### Phase 8 — Animation, Geo-Layers & Drawing Demo (v0.9)

| Capability | Details |
| --- | --- |
| **TripsLayer** | `trips_layer()` for animated vessel/vehicle tracks with `_tripsAnimation` config. |
| **GreatCircleLayer** | `great_circle_layer()` for geodesic arcs. |
| **ContourLayer** | `contour_layer()` for isoline/isoband visualisations. |
| **GridLayer** | `grid_layer()` for rectangular spatial binning with 3-D extrusion. |
| **ScreenGridLayer** | `screen_grid_layer()` for screen-space density grids. |
| **MVTLayer** | `mvt_layer()` for Mapbox Vector Tiles. |
| **WMSLayer** | `wms_layer()` for deck.gl 9.x native WMS layers. |
| **Interleaved rendering** | `MapWidget(interleaved=True)` for deck/MapLibre layer interleaving. |
| **Client-side animation** | `requestAnimationFrame`-based TripsLayer animation loop — no server polling. |
| **Drawing demo** | Tab 7 — MapboxDraw tools, named markers with popups, spatial query, live interaction log. |
| **Animation demo** | Tab 8 — Animated Baltic shipping tracks, GreatCircleLayer, GridLayer, speed/trail controls. |

### v1.6.2 — Security & Error Handling

| Capability | Details |
| --- | --- |
| **Accessor expression validation** | Regex whitelist + prototype pollution blocklist before `new Function()` — prevents code injection. |
| **Error logging** | All silent `catch` blocks now log `console.warn` (tooltip, controller, controls, WMS, map instance). |
| **HTML escaping** | Title and widget ID properly escaped in `to_html()` export to prevent XSS. |
| **COORDINATE_SYSTEM consolidation** | Single source of truth in `enums.py` with backwards-compatible alias. |
| **Input validation** | `encode_binary_attribute()` raises `TypeError` for non-numpy input. |

### v1.6.1 — Demo Update

| Capability | Details |
| --- | --- |
| **Demo gallery expansion** | All 9 new layer types showcased in Layer Gallery tab with UI toggles. |
| **Updated layer count** | Demo UI reflects "33 layer helpers" (was 24). |
| **Data generator caching** | New layer data generators use `@functools.lru_cache` for efficiency. |

### v1.6.0 — Complete Layer Coverage (33 Layer Types)

| Capability | Details |
| --- | --- |
| **9 new layer helpers** | `grid_cell_layer()`, `solid_polygon_layer()`, `a5_layer()`, `geohash_layer()`, `h3_cluster_layer()`, `quadkey_layer()`, `s2_layer()`, `tile_3d_layer()`, `scenegraph_layer()`. |
| **100% deck.gl coverage** | shiny_deckgl now provides typed helpers for all 33 deck.gl layer types. |
| **LayerType enum** | 9 new enum values for type-safe layer type constants. |
| **Demo gallery update** | Layer Gallery tab showcases all 33 layer types with toggles and live visualization. |

### v1.5.0 — Enum Types & TypedDict Definitions

| Capability | Details |
| --- | --- |
| **12 enum classes** | `ControlPosition`, `WidgetPlacement`, `EasingFunction`, `TransitionType`, `ControlType`, `Projection`, `CoordinateSystem`, `DrawMode`, `LayerType`, `ViewType`, `LightType`, `PostProcessShader`. |
| **TypedDict definitions** | Structured type hints for configuration dicts: `ControlSpec`, `WidgetSpec`, `ViewSpec`, `LayerSpec`, `EffectSpec`, `LightSpec`, `TooltipSpec`, `TransitionSpec`, `ViewState`. |
| **H3HexagonLayer fix** | Correctly normalizes H3 cell IDs to lowercase for deck.gl compatibility. |
| **214 new tests** | Expanded test suite covering enums, TypedDicts, and edge cases. |

### v1.4.0 — Partial Updates, Patch Layer & JS Modernisation

| Capability | Details |
| --- | --- |
| **`partial_update()`** | Push sparse layer patches — only changed properties are sent, avoiding full-stack resend. Auto-serialises DataFrames. |
| **`patch_layer()`** | Convenience wrapper to patch a single layer by ID: `await widget.patch_layer(session, "my_layer", opacity=0.5)`. |
| **Tooltip dismiss** | Map tooltips auto-hide when cursor moves to empty space; Bootstrap switch tooltips no longer persist after toggle. |
| **JS modernisation** | `structuredClone()` replaces `JSON.parse(JSON.stringify())`; all `var` declarations converted to `const`/`let`. |
| **TripsLayer partial fix** | `partial_update` now correctly restarts TripsLayer animation after patching. |

### v1.3.0 — Mesh Parsers, Colour Scales & Library Extraction

| Capability | Details |
| --- | --- |
| **`parsers.py` module** | `parse_shyfem_grd()` and `parse_shyfem_mesh()` — parse SHYFEM `.grd` finite-element meshes into deck.gl layer-ready data. Auto-detects UTM Zone 33N → WGS84 projection. |
| **`custom_geometry()`** | Helper to convert parsed mesh geometry into `simple_mesh_layer()` kwargs with inline `luma.Geometry` vertex arrays. |
| **`COORDINATE_SYSTEM`** | Enum-style constants mirroring deck.gl's coordinate systems: `DEFAULT`, `LNGLAT`, `METER_OFFSETS`, `LNGLAT_OFFSETS`, `CARTESIAN`. |
| **`depth_color()`** | Bathymetric blue-gradient RGBA colour function with configurable max depth and alpha. |
| **Colour Scales tab** | Demo Tab 4 — interactive palette picker (5 palettes × 3 modes), swatch preview, statistics, code examples, and live-coloured bathymetry map. |
| **Demo data factories** | 7 gallery data factories, fish species colours, SHYFEM helpers, and legend metadata extracted from `app.py` into reusable library modules. |
| **Demo refactored** | 10 tabs (was 9); inline helpers extracted into `_demo_data.py`, `_demo_css.py`, `_version.py`, `colors.py`. |

### v1.0.0 — Extensions, Clusters & Modular Architecture

| Capability | Details |
| --- | --- |
| **Module split** | 3 000-line `components.py` monolith split into 8 focused modules with backward-compatible re-export shim. |
| **Extension helpers** | `brushing_extension()`, `collision_filter_extension()`, `data_filter_extension()`, `mask_extension()`, `clip_extension()`, `terrain_extension()`, `fill_style_extension()`, `path_style_extension()` — convenience functions for deck.gl layer extensions. |
| **Cluster layers** | `add_cluster_layer()` / `remove_cluster_layer()` — MapLibre GeoJSON clustering with click-to-zoom, size-stepped circles, and count labels. |
| **Cooperative gestures** | `MapWidget(cooperative_gestures=True)` — require Ctrl+scroll to zoom, two-finger drag on mobile. |
| **Style diff** | `set_style(session, url, diff=True)` — preserves sources/layers across basemap changes. |
| **Demo Tab 9** | Interactive showcase: BrushingExtension, DataFilterExtension, MapLibre clustering, cooperative gestures. |

### v1.1.0 — IBM Helpers, Trips Animation Module & Audit Fixes

| Capability | Details |
| --- | --- |
| **`format_trips()`** | Normalise raw `[lon, lat]` or `[lon, lat, time]` paths into `trips_layer()` dict format with auto-timestamps and per-trip property merge. |
| **`trips_animation_ui()`** | Reusable Shiny module — Play/Pause/Reset buttons + speed & trail sliders, drop into any sidebar. |
| **`trips_animation_server()`** | Wires animation buttons to `MapWidget.trips_control()`, exposes `speed` / `trail` reactive values. |
| **`Extension` type alias** | Unified return type for all 8 extension helpers (`str \| list[str \| dict]`). |
| **`wms_layer()` validation** | Now raises `ValueError` when the required `layers` kwarg is omitted. |
| **Thread-safe MPA cache** | HELCOM GeoJSON loader switched to `@functools.lru_cache`. |
| **Demo Tab 12 rewired** | Seal IBM tab now uses `trips_animation_ui/server` — ~40 lines of boilerplate removed. |

### v1.2.0 — Effects Module, New Layers & Demo Consolidation

| Capability | Details |
| --- | --- |
| **`effects.py` module** | 6 helpers for deck.gl lighting & post-processing: `ambient_light()`, `point_light()`, `directional_light()`, `sun_light()`, `lighting_effect()`, `post_process_effect()`. |
| **`point_cloud_layer()`** | Typed helper for 3-D point cloud rendering. |
| **`simple_mesh_layer()`** | Place 3-D OBJ/PLY models on the map. |
| **`terrain_layer()`** | Reconstruct mesh from Terrain-RGB height-map tiles. |
| **`fp64_extension()`** | Double-precision GPU rendering for extreme zoom levels. |
| **`orbit_view()`** | `OrbitView` — orbit a camera around a 3-D target. |
| **Demo refactored** | 14 → 11 tabs: Effects merged into 3D Visualisation, Clusters into MapLibre Controls, Extensions into Advanced, Animation into Seal IBM; new Layer Gallery tab (all 33 layer helpers). |
| **JS `buildEffects`** | Updated for `SunLight` support via `@@sunLight` marker. |

## Environment & Prerequisites

- **Python ≥ 3.9** and **Shiny ≥ 1.0** are required.
- Any standard Python environment works (venv, conda, micromamba, system).

## Installation

```bash
pip install -e .          # editable install (local package, not on PyPI yet)
```

For binary transport support (numpy):

```bash
pip install -e ".[binary]"
```

For GeoPandas integration:

```bash
pip install -e ".[geopandas]"
```

Or build the conda package:

```bash
conda build conda.recipe/   # or: micromamba build conda.recipe/
```

## Quick Start

```bash
shiny_deckgl-demo
```

This launches a comprehensive demo app centred on the Baltic Sea with scatter
points, WMS layers, controls, drawing tools, markers, popups, terrain, and
HTML export.

## Usage in your own apps

```python
from shiny import App, ui, reactive, Session, render
from shiny_deckgl import MapWidget, scatterplot_layer, head_includes, CARTO_DARK

map_widget = MapWidget(
    "mymap",
    view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 8},
    tooltip={"html": "<b>Point</b><br/>lon: {0}, lat: {1}"},
    style=CARTO_DARK,
)

app_ui = ui.page_fluid(
    head_includes(),
    map_widget.ui(height="80vh"),
    ui.output_text_verbatim("click_info"),
)

def server(input, output, session: Session):
    @reactive.Effect
    async def _push_layers():
        layers = [scatterplot_layer("pts", [[21.12, 55.70], [21.15, 55.72]])]
        await map_widget.update(session, layers)

    @render.text
    def click_info():
        val = input[map_widget.click_input_id]()
        return str(val) if val else "Click a point…"

my_app = App(app_ui, server)
```

```bash
shiny run my_app.py
```

### Using WMS tile layers

```python
from shiny_deckgl import tile_layer

wms_url = (
    "https://ows.emodnet-bathymetry.eu/wms?"
    "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
    "&FORMAT=image/png&TRANSPARENT=true"
    "&LAYERS=emodnet:mean_atlas_land"
    "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
    "&BBOX={bbox-epsg-3857}"
)
layers.append(tile_layer("emodnet-bathy", wms_url))
```

### Color scales

```python
from shiny_deckgl import color_bins, PALETTE_OCEAN

depths = [10.5, 50.2, 120.0, 300.7, 15.3]
colors = color_bins(depths, n_bins=4, palette=PALETTE_OCEAN)
# colors[i] is [R, G, B, 255] for each depth value
```

### HTML export

```python
layers = [scatterplot_layer("pts", [[21.12, 55.70]])]
map_widget.to_html(layers, path="my_map.html", title="Exported Map")
```

### deck.gl legend for overlay layers

```python
from shiny_deckgl import deck_legend_control, scatterplot_layer, arc_layer, heatmap_layer

await widget.set_controls(session, [
    {"type": "navigation", "position": "top-right"},
    deck_legend_control(
        entries=[
            {"layer_id": "ports", "label": "Baltic Ports",
             "color": [65, 182, 196], "shape": "circle"},
            {"layer_id": "routes", "label": "Shipping Routes",
             "color": [255, 140, 0], "color2": [200, 0, 80], "shape": "arc"},
            {"layer_id": "density", "label": "Observation Density",
             "colors": [[0, 25, 0, 255], [0, 209, 0, 255], [255, 255, 0, 255], [255, 0, 0, 255]],
             "shape": "gradient"},
        ],
        position="bottom-right",
        title="Deck.gl Layers",
    ),
])
```

### Widgets and camera transitions

```python
from shiny_deckgl import zoom_widget, compass_widget, fullscreen_widget

await widget.set_widgets(session, [
    zoom_widget(), compass_widget(), fullscreen_widget(),
])

await widget.fly_to(session, longitude=20.0, latitude=55.5, zoom=8, pitch=45)
```

## Codebase Structure

| File | Purpose |
| --- | --- |
| `src/shiny_deckgl/map_widget.py` | `MapWidget` class — core widget with session methods, HTML export, JSON serialisation. |
| `src/shiny_deckgl/layers.py` | Generic `layer()` + 33 typed layer helpers (scatter, arc, trips, grid, point cloud, mesh, terrain, scenegraph, tile3d, …). |
| `src/shiny_deckgl/colors.py` | Color scales (`color_range`, `color_bins`, `color_quantiles`), palettes, basemap constants. |
| `src/shiny_deckgl/views.py` | View helpers (`map_view`, `orthographic_view`, `first_person_view`, `globe_view`, `orbit_view`). |
| `src/shiny_deckgl/widgets.py` | 17 deck.gl widget helpers (zoom, compass, fullscreen, timeline, …). |
| `src/shiny_deckgl/controls.py` | MapLibre control helpers, legend, opacity, deck.gl legend. |
| `src/shiny_deckgl/extensions.py` | 9 extension helpers (brushing, collision filter, data filter, mask, fp64, …). |
| `src/shiny_deckgl/_data_utils.py` | DataFrame/GeoDataFrame serialisation, binary transport. |
| `src/shiny_deckgl/_transitions.py` | `transition()` helper for layer property animations. |
| `src/shiny_deckgl/components.py` | Backward-compatible re-export shim (imports from split modules). |
| `src/shiny_deckgl/effects.py` | Effect helpers: `lighting_effect()`, `post_process_effect()`, and 4 light-source factories. |
| `src/shiny_deckgl/parsers.py` | SHYFEM `.grd` mesh parsers: `parse_shyfem_grd()` (PolygonLayer data) and `parse_shyfem_mesh()` (SimpleMeshLayer geometry). |
| `src/shiny_deckgl/app.py` | Demo `app` instance — 10-tab sidebar UI showcasing all features. |
| `src/shiny_deckgl/ui.py` | `head_includes()` — injects pinned CDN scripts and local JS/CSS. |
| `src/shiny_deckgl/_cdn.py` | CDN URL constants — single source of truth for all external asset URLs. |
| `src/shiny_deckgl/_version.py` | Package version — single source of truth. |
| `src/shiny_deckgl/cli.py` | `shiny_deckgl-demo` CLI entry point. |
| `src/shiny_deckgl/_demo_data.py` | Sample Baltic Sea data (ports, routes, MPA GeoJSON) for the demo app. |
| `src/shiny_deckgl/_demo_css.py` | Marine-themed CSS and UI helpers for the demo app. |
| `src/shiny_deckgl/ibm.py` | IBM (Individual-Based Model) visual assets, `format_trips()` data helper, and `trips_animation_ui/server` Shiny module. |
| `src/shiny_deckgl/resources/deckgl-init.js` | Frontend: MapLibre init, deck.gl overlay, message handlers, draw tools, popups, terrain. |
| `src/shiny_deckgl/resources/styles.css` | Minimal layout + tooltip styles for `.deckgl-map` containers. |
| `conda.recipe/meta.yaml` | Conda build recipe (version synced with `_version.py`). |
| `src/shiny_deckgl/_sealmove.py` | Seal movement simulation engine for the IBM demo tab. |
| `tests/test_basic.py` | 1 078 unit tests covering all features. |

## Performance Patterns

See [docs/performance-patterns.md](docs/performance-patterns.md) for guidance on:

- **Static / Dynamic Layer Split** — use `partial_update()` for frequently-changing layers to reduce serialisation cost by 80–90 %
- **Categorical Data** — use `scatterplot_layer` with pre-computed colors for discrete data classes

## Running Tests

```bash
pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
