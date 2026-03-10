# Changelog

All notable changes to **shiny\_deckgl** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and version numbers use [Semantic Versioning](https://semver.org/).

---
## [1.7.0] — 2026-03-10

### Added

- **`layer_legend_widget()` with auto-introspection** — New deck.gl widget that
  generates a legend panel from active layers at runtime. Detects layer type → swatch
  shape (circle, rect, line, arc, gradient) and extracts colors from layer props
  (`getFillColor`, `getSourceColor`/`getTargetColor`, `colorRange`), data items, or
  layer-type defaults. Supports manual entries, visibility checkboxes, collapsible
  header, `exclude_layers`, and `label_map` overrides.
- **Auto-introspect legend in Layer Gallery demo** — Tab 1 now uses
  `layer_legend_widget(auto_introspect=True)` instead of the old manual
  `deck_legend_control`, with live legend updates as layers are toggled.
- **Performance & visualization patterns guide** — New `docs/performance-patterns.md`
  documenting the static/dynamic layer split pattern (`update()` vs `partial_update()`)
  and categorical data visualization with `scatterplot_layer`. Docstrings on `update()`,
  `partial_update()`, and `patch_layer()` now include performance tips and cross-references.
  README links to the new guide.
- **Color ramp constants** — Five new palettes: `PALETTE_BLUES`, `PALETTE_GREENS`,
  `PALETTE_REDS`, `PALETTE_YELLOW_RED`, `PALETTE_BLUE_WHITE` (6-stop RGB, ColorBrewer-inspired).
  Seven short-name aliases: `VIRIDIS`, `OCEAN_DEPTH`, `BLUES`, `GREENS`, `REDS`,
  `YELLOW_RED`, `BLUE_WHITE`.
- **`update_legend()` method** — Dynamically update or create a deck.gl legend control
  without resending the full controls list. Useful for GIS editor patterns where users
  switch between layers with different color schemes.
- **Client-side animation API** — `animate_prop()` helper creates marker dicts that the
  JS widget recognises, starting a `requestAnimationFrame` loop for purely visual
  animations (e.g., rotating turbine blades) with zero server round-trips.
  `set_animation()` method starts/stops animations per layer.

---
## [1.6.2] — 2026-03-06

### Fixed

- **Security: accessor expression validation** — Added regex whitelist validation
  for `@@=expr` accessor expressions before `new Function()` to prevent code injection.
  Only safe patterns allowed: `d`, `d.prop`, `d[0]`, `d["key"]`, and combinations.
- **Error logging for JSON parse failures** — All silent `catch (_) {}` blocks now
  log `console.warn` with details: tooltip, controller, controls, useDevicePixels,
  parameters configurations.
- **WMS tile fetch failure logging** — Failed WMS tile requests now log warnings
  (excluding AbortError) for easier debugging.
- **Map instance lookup logging** — `ensureInstance()` now warns when map ID not
  found, helping diagnose silent Python-to-JS message failures.

### Changed

- **Consolidated COORDINATE_SYSTEM** — Removed duplicate definitions from `_types.py`
  and `layers.py`. Now uses `CoordinateSystem` enum from `enums.py` as single source
  of truth with `DEFAULT` alias for backwards compatibility.
- **Input validation for `encode_binary_attribute()`** — Raises `TypeError` with
  clear message when input is not a numpy array.
- **Updated `.gitignore`** — Added `.hypothesis/`, `run_mypy.py`, `_measure_payload.py`,
  `nul` artifacts.

---
## [1.6.1] — 2026-03-06

### Added

- **Demo update** — All 9 new layer types now showcased in the Layer Gallery tab
  with dedicated UI toggles, demo data generators, and layer creation logic.
- **Updated layer count badges** — Demo UI reflects "33 layer helpers" (was 24).

### Fixed

- **Demo data generator caching** — All new layer data generators use
  `@functools.lru_cache` for efficient reuse across reactive effects.

---
## [1.6.0] — 2026-03-06

### Added

- **9 new layer helpers** for complete deck.gl layer coverage (33 total):
  - **Core layers**: `grid_cell_layer()` (pre-aggregated grid cells),
    `solid_polygon_layer()` (fast polygon fills without stroke).
  - **Geo-spatial layers**: `a5_layer()` (A5 pentagon cells),
    `geohash_layer()` (Geohash cells), `h3_cluster_layer()` (clustered H3
    hexagons), `quadkey_layer()` (Bing Maps quadkeys), `s2_layer()` (Google S2
    cells).
  - **Tile layers**: `tile_3d_layer()` (OGC 3D Tiles / Esri I3S datasets).
  - **Mesh layers**: `scenegraph_layer()` (glTF/GLB 3D models).
- **LayerType enum expansion** — 9 new enum values in `enums.py` for type-safe
  layer type constants.
- **100% deck.gl layer coverage** — shiny_deckgl now provides typed helpers for
  all 33 deck.gl layer types.

### Changed

- **`__init__.py`** — exports 9 new layer helpers with categorized comments.
- **`components.py`** — re-exports new layers for backward compatibility.

---
## [1.5.0] — 2026-03-06

### Added

- **Enum types** (`enums.py`) — 12 new enum classes for type-safe constants:
  `ControlPosition`, `WidgetPlacement`, `EasingFunction`, `TransitionType`,
  `ControlType`, `Projection`, `CoordinateSystem`, `DrawMode`, `LayerType`,
  `ViewType`, `LightType`, `PostProcessShader`. All inherit from `str` for
  seamless use with existing APIs.
- **TypedDict definitions** (`_types.py`) — structured type hints for
  configuration dicts: `ControlSpec`, `WidgetSpec`, `ViewSpec`, `LayerSpec`,
  `EffectSpec`, `LightSpec`, `TooltipSpec`, `TransitionSpec`, `ViewState`.
- **Module docstring** — comprehensive package docstring in `__init__.py`
  documenting all major components and usage patterns.
- **API reference: Enum Types section** — documentation for all enum classes.
- **Test coverage expansion** — 214 new tests across 4 test files:
  - `test_widgets.py` (91 tests) — widget helper functions
  - `test_views.py` (49 tests) — view helper functions
  - `test_extensions.py` (41 tests) — extension helper functions
  - `test_app_modules.py` (33 tests) — app module integration

### Fixed

- **H3HexagonLayer not rendering** — added missing `h3-js` library (v4.1.0) to
  CDN imports. The H3HexagonLayer requires this library to convert H3 indices
  to polygon boundaries.
- **`wms_layer()` validation** — now requires `layers` parameter to be a
  non-empty list (previously accepted strings which caused silent failures).

### Changed

- **Validation helper refactoring** — introduced `_validate_choice()` helper
  function and pre-computed sorted constants to reduce code duplication and
  improve error message consistency in `MapWidget`.

---
## [1.4.0] — 2026-03-04

### Added

- **`partial_update()`** — new `MapWidget` method that pushes sparse layer
  patches (only changed properties) without resending the full layer stack.
  Automatically serialises DataFrames/GeoDataFrames in patched `data` fields.
- **`patch_layer()`** — convenience wrapper around `partial_update()` for the
  common case of tweaking a single layer's properties by `layer_id`.

### Fixed

- **TripsLayer animation after partial update** — `deck_partial_update` JS
  handler now calls `startTripsAnimation()` so TripsLayer continues animating
  after a partial update (previously the animation stopped).
- **Map tooltip stickiness** — added a map-level `mousemove` listener that
  uses `overlay.pickObject()` to dismiss tooltips when the cursor leaves all
  layer extents (previously tooltips stayed visible over empty map space).
- **Bootstrap switch tooltip persistence** — added a document-level click
  listener that removes `.tooltip.show` elements when a `.form-switch` is
  clicked, fixing Bootstrap 5 tooltips that persisted after toggling layers.

### Changed

- **JS: `structuredClone()` replaces `JSON.parse(JSON.stringify())`** — 4
  deep-clone call sites in `deckgl-init.js` upgraded for better performance
  and correctness (preserves `undefined`, `NaN`, `Infinity`).
- **JS: `var` → `const`/`let` modernisation** — all ~156 `var` declarations
  in `deckgl-init.js` converted to `const` (138) or `let` (18) following
  ES6+ best practices.
- **`Sealmove.py` renamed to `_sealmove.py`** — private module naming
  convention applied to the seal movement simulation.

---
## [1.3.0] — 2026-03-03

### Added

- **`parsers.py` module** — SHYFEM finite-element mesh parsers:
  - `parse_shyfem_grd()` — parse a `.grd` file into `PolygonLayer`-ready
    data (triangles with depth colours, auto-detects UTM → WGS84).
  - `parse_shyfem_mesh()` — parse a `.grd` file into `SimpleMeshLayer`
    geometry arrays (positions, normals, colours, indices in metre offsets).
- **`custom_geometry()`** — helper that converts `parse_shyfem_mesh()`
  output into `simple_mesh_layer()` keyword arguments, using the
  `@@CustomGeometry` mesh marker and `luma.Geometry` inline vertex arrays.
- **`COORDINATE_SYSTEM`** — enum-style class mirroring deck.gl's coordinate
  system constants (`DEFAULT`, `LNGLAT`, `METER_OFFSETS`,
  `LNGLAT_OFFSETS`, `CARTESIAN`).
- **`depth_color()`** — bathymetric blue-gradient RGBA colour function with
  configurable `max_depth` and `alpha` parameters.
- **Demo data factories** (in `_demo_data.py`):
  - `SHYFEM_VIEW` — pre-set view state for the Curonian Lagoon.
  - `make_shyfem_polygon_data()` / `make_shyfem_mesh_data()` — load
    SHYFEM `.grd` files with graceful fallback when files are absent.
  - `CURONIAN_GRD_PATH` / `POLYGON_GRD_PATH` — resolved `.grd` file paths.
  - `FISH_SPECIES_COLORS` / `fish_species_color()` — Baltic fish species
    RGBA colour mapping.
  - `make_gallery_port_data()`, `make_gallery_arc_data()`,
    `make_gallery_line_data()`, `make_gallery_path_data()`,
    `make_gallery_text_data()`, `make_gallery_icon_data()`,
    `make_gallery_column_data()` — 7 gallery data factory functions.
  - `LAYER_LEGEND_META` — dict mapping layer type names to colour/shape
    tuples for `deck_legend_control`.
- **`about_row()`** — small HTML helper for the demo About panel
  (`_demo_css.py`).
- **`python_version()`** / **`shiny_version()`** — runtime version queries
  (`_version.py`).
- **Demo Tab 4: Colour Scales** — interactive palette management tab with 5
  palettes, 3 colour modes, swatch preview, statistics, code examples, and
  live map with bathymetry columns coloured by selected scheme.

### Changed

- **Demo app** refactored from 9 → 10 tabs (new Colour Scales tab).
- **`app.py` cleaned up** — inline colour helpers, species colours, gallery
  data comprehensions, and legend metadata extracted from `server()` into
  library modules; `app.py` now imports them.
- **`__init__.py`** — exports `custom_geometry`, `COORDINATE_SYSTEM`,
  `depth_color`, `parse_shyfem_grd`, `parse_shyfem_mesh`,
  `make_shyfem_polygon_data`, `make_shyfem_mesh_data`, `SHYFEM_VIEW`.
- **`components.py`** — re-exports `depth_color` from `colors.py`.
- **CI workflow** — added Python 3.13 to test matrix.

---
## [1.2.0] — 2026-03-03

### Added

- **`effects.py` module** — 6 new helpers for deck.gl lighting and
  post-processing effects:
  - `ambient_light()` — uniform, direction-independent illumination.
  - `point_light()` — positional light source (like a light bulb).
  - `directional_light()` — parallel rays from a distant source.
  - `sun_light()` — directional light based on real sun position at a
    given timestamp.
  - `lighting_effect()` — combines ambient + point/directional/sun lights
    into a single `LightingEffect` spec.
  - `post_process_effect()` — screen-space pixel manipulation
    (brightness, contrast, vignette, blur, etc.).
- **`point_cloud_layer()`** — typed helper for deck.gl `PointCloudLayer`
  (3-D point clouds).
- **`simple_mesh_layer()`** — typed helper for `SimpleMeshLayer` (place
  3-D OBJ/PLY models on the map).
- **`terrain_layer()`** — typed helper for `TerrainLayer` (reconstruct 3-D
  mesh from Terrain-RGB height-map tiles).
- **`fp64_extension()`** — `Fp64Extension` for double-precision GPU
  rendering at extreme zoom levels.
- **`orbit_view()`** — `OrbitView` for orbiting around a 3-D target
  (meshes, point clouds).
- **54 new tests** — test suite now 1 051 tests total (was 997).

### Changed

- **Demo app refactored** from 14 → 11 tabs (10 refactored + 1 new Layer Gallery):
  - Tab 14 (Effects standalone) merged into Tab 11 (3D Visualisation) —
    directional light and post-processing now demonstrated alongside
    terrain and 3-D column layers.
  - Tab 10 (Clusters standalone) merged into Tab 2 (MapLibre Controls) —
    clustering is now a section in the controls tab.
  - Tab 9 (Extensions standalone) merged into Tab 5 (Advanced) —
    BrushingExtension and DataFilterExtension sit beside cooperative
    gestures.
  - Tab 8 (Animation) merged into Tab 9 (Seal IBM) — TripsLayer
    animation method documentation, GreatCircleLayer route arcs, and
    GridLayer haulout density added to the IBM tab.
- **4 `MapWidget` instances removed** — `effects_widget`, `v1_ml_widget`,
  `v1_deck_widget`, `anim_widget` eliminated during tab merges.
- **`_make_lighting_effects` helper removed** — replaced by the new
  `effects` module helpers (`lighting_effect`, `ambient_light`, etc.).
- **JS `buildEffects`** updated to support `SunLight` via `@@sunLight`
  marker in light specs.
- **Layer Gallery tab (Tab 11)** — new tab showcasing all 24 typed layer
  helpers with Baltic Sea sample data and per-layer toggle switches.
- **`app.py` docstring** updated to list 11 tabs.

---
## [1.1.0] — 2026-03-02

### Added

- **`format_trips()`** — data normaliser that converts raw `[lon, lat]` or
  `[lon, lat, time]` coordinate lists into the dict format `trips_layer()`
  expects, with auto-generated timestamps and per-trip property merging.
- **`trips_animation_ui()`** — reusable Shiny module UI fragment with
  Play / Pause / Reset buttons plus speed and trail-length sliders; drop into
  any sidebar to control a TripsLayer animation.
- **`trips_animation_server()`** — companion server logic that wires the
  animation buttons to `MapWidget.trips_control()` and exposes `speed` /
  `trail` reactive values back to the caller.
- **`Extension` type alias** — `str | list[str | dict]` exported from
  `extensions.py`; all 8 extension helpers now annotated `-> Extension`
  instead of the previous mix of `-> str` and `-> list`.
- **3 new test classes** — `TestFormatTrips` (12 tests), `TestTripsAnimationUI`
  (4 tests), `TestTripsAnimationServer` (4 tests); 672 tests total.

### Changed

- **`wms_layer()`** now raises `ValueError` when the required `layers` keyword
  argument is omitted (previously silently defaulted to an empty list,
  producing a blank WMS response).
- **`_demo_data.py`** — `make_seal_trips()` now delegates timestamp/path
  formatting to `format_trips()` instead of inline code; `format_trips` import
  moved to function top (was inside the loop body).
- **`_demo_data.py`** — HELCOM MPA cache replaced from `global` variable with
  `@functools.lru_cache(maxsize=1)` for thread-safe, one-shot caching.
- **Demo app Tab 12** — rewired to use `trips_animation_ui("seal_anim")` /
  `trips_animation_server()`, removing ~40 lines of inline boilerplate.
- **`app.py` module docstring** — now lists all 12 tabs (tabs 10–11 were
  missing).
- **`__init__.py`** — exports `format_trips`, `trips_animation_ui`,
  `trips_animation_server`; removed premature "v1.1.0" comment label.

---
## [1.0.1] â€” 2026-03-01

### Fixed

- **cli.py** â€” `run_app(app(default_provider))` crash replaced with
  `run_app(app)` (the `app` object is a Shiny `App` instance, not a factory).
- **conda.recipe/meta.yaml** â€” version bumped to 1.0.0 (was stuck at
  0.6.0); `htmltools` added to run requirements.

### Changed

- **`__init__.py`** â€” `__all__` now includes 7 missing v0.9.0 layer helpers
  (`trips_layer`, `great_circle_layer`, `contour_layer`, `grid_layer`,
  `screen_grid_layer`, `mvt_layer`, `wms_layer`).
- **`__all__`** added to all 8 split modules for explicit public API control.
- **`_demo_data.py`** â€” GeoJSON loading moved from import-time I/O to lazy
  `__getattr__` with module-level cache.
- **`pyproject.toml`** â€” classifier updated to
  `Development Status :: 5 - Production/Stable`.
- **CHANGELOG.md** â€” corrected dates and added comparison link references.
- **README.md** â€” codebase structure table updated for the 8-module split.
- **docs/api_reference.md** â€” bumped to v1.0.0; added Extension Helpers,
  Cluster Layers, Cooperative Gestures, Controller, and Style-Diff sections;
  updated `MapWidget` constructor docs with all v0.7â€“1.0 parameters.

---

## [1.0.0] â€” 2026-06-14

### Added

- **Module split** â€” The 3 000-line `components.py` monolith has been split
  into 8 focused modules: `colors`, `_data_utils`, `views`, `widgets`,
  `controls`, `_transitions`, `layers`, `map_widget`.  A backward-compatible
  re-export shim keeps all existing imports working.
- **Extension helpers** â€” New `extensions` module with convenience functions
  for deck.gl layer extensions: `brushing_extension()`,
  `collision_filter_extension()`, `data_filter_extension()`,
  `mask_extension()`, `clip_extension()`, `terrain_extension()`,
  `fill_style_extension()`, `path_style_extension()`.
- **Cluster layers** â€” `MapWidget.add_cluster_layer()` and
  `remove_cluster_layer()` create MapLibre GeoJSON clustered point
  visualisations with click-to-zoom, size-stepped circles, and count labels.
- **Cooperative gestures** â€” `MapWidget(cooperative_gestures=True)` and
  `set_cooperative_gestures()` require Ctrl+scroll to zoom and two-finger
  drag on touch devices, useful for maps embedded in scrollable pages.
- **Style diff** â€” `set_style(session, url, diff=True)` uses MapLibre's
  diff algorithm to preserve existing sources/layers across style changes.
- **Demo Tab 9** â€” Showcases v1.0.0 features: BrushingExtension,
  DataFilterExtension, MapLibre clustering, cooperative gestures.
- **33 new tests** (524 total).

### Changed

- `Development Status` classifier moved from `4 - Beta` to
  `5 - Production/Stable`.

---

## [0.9.0] â€” 2026-06-13

### Added

- **TripsLayer** â€” `trips_layer()` helper for animated vehicle/vessel tracks
  with `path`, `timestamps`, `trailLength`, and `currentTime` properties.
  Includes a client-side `_tripsAnimation` config (`loopLength`, `speed`) that
  drives a `requestAnimationFrame` loop in JavaScript for smooth animation
  without server-side polling.
- **GreatCircleLayer** â€” `great_circle_layer()` helper for geodesic arcs
  (shortest path on sphere), unlike `ArcLayer` parabolic arcs.
- **ContourLayer** â€” `contour_layer()` helper for isoline/isoband
  visualisations from point data with configurable thresholds.
- **GridLayer** â€” `grid_layer()` helper for rectangular spatial binning with
  elevation extrusion support.
- **ScreenGridLayer** â€” `screen_grid_layer()` helper for screen-space binning
  with configurable pixel cell size and colour range.
- **MVTLayer** â€” `mvt_layer()` helper for Mapbox Vector Tiles.
- **WMSLayer** â€” `wms_layer()` helper for deck.gl 9.x native WMS layer.
- **Interleaved rendering** â€” `MapWidget(interleaved=True)` to enable deck.gl
  interleaved rendering with MapLibre GL (layers interspersed with basemap
  labels).  JS reads `data-interleaved` attribute.
- **TripsLayer animation engine** â€” `startTripsAnimation()` /
  `stopTripsAnimation()` JavaScript functions with `requestAnimationFrame`
  loop.  Automatically started after `deck_update` when a TripsLayer with
  `_tripsAnimation` config is detected.
- **Demo Tab 7: Drawing** â€” showcases MapboxDraw tools (point/line/polygon),
  named markers with popups and drag, spatial query, live interaction log.
- **Demo Tab 8: Animation** â€” animated Baltic shipping tracks (TripsLayer),
  GreatCircleLayer route arcs, port scatterplot, GridLayer observation grid,
  with speed/trail-length controls.
- **Demo data** â€” `make_trips_data()` generator converts Baltic shipping
  routes into TripsLayer format; `SAMPLE_STUDY_AREA` GeoJSON polygon constant.
- **30 new tests** (491 total).

---

## [0.8.0] â€” 2026-06-13

### Added

- **deck.gl Widgets** â€” 12 widget helper functions: `zoom_widget`,
  `compass_widget`, `fullscreen_widget`, `scale_widget`, `gimbal_widget`,
  `reset_view_widget`, `screenshot_widget`, `fps_widget`, `loading_widget`,
  `timeline_widget`, `geocoder_widget`, `theme_widget`.  Each returns a spec
  dict with `@@widgetClass` resolved by the JS client.
- **`set_widgets()`** â€” async method to update widgets without resending layers.
- **`update()` widgets param** â€” optional `widgets` list passed through to
  `overlay.setProps({widgets})`.
- **`transition()` helper** â€” build transition specs for layer property
  animations with named easing functions (`ease-in-cubic`,
  `ease-out-cubic`, `ease-in-out-cubic`, `ease-in-out-sine`).
- **`fly_to()`** â€” smooth fly-to camera transitions via MapLibre `flyTo`.
- **`ease_to()`** â€” smooth ease-to camera transitions via MapLibre `easeTo`.
- **Widgets CDN** â€” `@deck.gl/widgets` JS + CSS added to CDN head fragment
  and standalone `to_html()` exports.
- **32 new tests** (410 total).

---

## [0.7.0] â€” 2026-06-12

### Added

- **Extension constructor options** â€” `layer()` now accepts mixed extension
  specs: plain strings (no-args) and `[name, options]` pairs, e.g.
  `extensions=[["DataFilterExtension", {"filterSize": 2}]]`.  JS
  `resolveExtensions()` handles both forms.
- **Deck-level props** â€” `MapWidget.__init__` accepts `picking_radius`,
  `use_device_pixels`, `animate`, `parameters`, and `controller`.  Passed
  through as `data-*` attributes and read by `initMap()` in JS.
- **`update()` deck props** â€” `update()` accepts `picking_radius`,
  `use_device_pixels`, `animate` overrides, applied via `overlay.setProps()`.
- **`set_controller()`** â€” new async method to dynamically enable/disable or
  fine-tune map controller behaviour.
- **10 new layer helpers** â€” `arc_layer`, `icon_layer`, `path_layer`,
  `line_layer`, `text_layer`, `column_layer`, `polygon_layer`,
  `heatmap_layer`, `hexagon_layer`, `h3_hexagon_layer`.
- **`globe_view()`** â€” convenience helper for `GlobeView` spec dicts.
- **68 new tests** (378 total).

---

## [0.6.1] â€” 2026-06-12

### Added

- **`deck_legend_control()`** â€” custom legend panel for deck.gl overlay layers.
  Five swatch shapes (`circle`, `rect`, `line`, `arc`, `gradient`), optional
  visibility checkboxes that toggle deck.gl layers, collapsible header, and
  fully configurable entries.  Implemented as a MapLibre `IControl` in JS with
  dedicated CSS.
- **`legend_control()`** â€” native MapLibre layer legend powered by
  `@watergis/maplibre-gl-legend`, with checkbox toggles and `targets` filter.
- **`opacity_control()`** â€” layer switcher / opacity slider control powered by
  `maplibre-gl-opacity`.
- **Custom map images** â€” `add_image()`, `remove_image()`, `has_image()` for
  loading icons (PNG, JPEG, WebP, SVG, data-URI) into the map style.  Supports
  SDF (signed-distance-field) recolouring and retina `pixel_ratio`.
- `has_image_input_id` reactive property â€” reports `{imageId, exists}` after
  `has_image()` check.

### Fixed

- **JS: tooltip re-render** â€” `deck_update_tooltip` now rebuilds layers so
  tooltip configuration changes take effect on existing layers.
- **JS: nativeLayers tracking** â€” `instance.nativeLayers` initialised to `{}`
  and tracked in add/remove handlers; `deck_set_style` warning no longer dead
  code.
- **JS: export\_image webp + idle** â€” `deck_export_image` supports webp format
  and waits for `map.idle` event before capture to ensure tiles are loaded.
- **Python: HTML-escape style** â€” `to_html()` escapes `self.style` in the
  `data-style` attribute to prevent malformed HTML from URLs containing `"` or
  `&`.
- **README:** escaped pipe characters in `export_image` table row.

### Changed

- All 35 async `session` parameters annotated as `session: Session` with
  `TYPE_CHECKING` guard import.
- `_serialise_data()` annotated as `(data: Any) -> Any`.
- `pyproject.toml` â€” added `htmltools` as explicit dependency, project URLs,
  classifiers (GIS, Science, Beta), `[tool.pytest.ini_options]`, and optional
  `[geopandas]` / `[dev]` extras.
- README â€” removed hardcoded machine-specific Python path; rewritten for
  portable installation instructions.

---

## [0.6.0] â€” 2026-03-01

### Changed

- Extracted CDN URLs into a shared `_cdn.py` module (single source of truth).
- `ui.py` now reads version from `_version.py` instead of hard-coding it (no
  more triple-sync on version bumps).
- Test file â€” moved `import asyncio` / `import pytest` to module level (71
  redundant in-method imports removed).
- README.md â€” full rewrite with accurate MapLibre v5.3.1 reference, 195 test
  count, and complete Phase 1â€“4 feature tables.
- Demo app (`app.py`) â€” comprehensive accordion sidebar covering all features.

### Fixed

- **Draw event listener leak** â€” repeated `enable_draw()` calls no longer
  accumulate orphaned `draw.create` / `draw.update` / `draw.delete` /
  `draw.modechange` listeners on the MapLibre map.
- `disable_draw()` now also removes map-level draw event listeners.
- `set_style()` emits a `console.warn` when native sources/layers exist,
  alerting that they will be destroyed by the style change.
- `query_at_lnglat()` no longer sends `"layers": null` when no layers are
  specified â€” the key is omitted entirely.
- `export_image()` docstring now documents `"webp"` as a supported format.
- `app.py` â€” removed unused `layer` import; corrected docstring version range.
- `components.py` â€” removed extraneous blank line between imports.
- `conda.recipe/meta.yaml` â€” version updated to 0.6.0; GitHub URL corrected
  from `arturas-baziukas/` to `razinkele/`.

---

## [0.5.0] â€” 2026-03-01

### Added

- **Drawing tools** â€” `enable_draw()`, `disable_draw()`, `get_drawn_features()`,
  `delete_drawn_features()` backed by MapboxDraw v1.4.3.
- **GeoPandas integration** â€” `add_geodataframe()` serialises a GeoDataFrame
  into a native MapLibre source + layer; `update_geodataframe()` replaces data
  in-place.
- **Feature state** â€” `set_feature_state()` and `remove_feature_state()` for
  interactive data-driven styling without redrawing layers.
- **Map export** â€” `export_image(format, quality)` captures a base64-encoded
  screenshot (PNG, JPEG, or WebP).
- Shiny inputs: `drawn_features_input_id`, `draw_mode_input_id`,
  `export_result_input_id`.

---

## [0.4.0] â€” 2026-03-01

### Added

- **Globe projection** â€” `set_projection("globe")` / `set_projection("mercator")`.
- **Terrain** â€” `set_terrain(source, exaggeration)` for 3D DEM rendering;
  `set_sky()` for atmosphere effects.
- **Popups** â€” `add_popup(layer_id, template)` with click-to-open popup on
  native MapLibre layers; `remove_popup()` to detach.
- **Spatial queries** â€” `query_rendered_features()` (pixel point or bounds) and
  `query_at_lnglat()` (geographic coordinates) with optional layer/filter
  restrictions; results delivered through `query_result_input_id`.
- **Multiple markers** â€” `add_marker()`, `remove_marker()`, `clear_markers()`
  with colour, draggable, and popup support.
- Shiny inputs: `marker_click_input_id`, `marker_drag_input_id`,
  `feature_click_input_id`.

---

## [0.3.0] â€” 2026-03-01

### Added

- **Native MapLibre sources** â€” `add_source()`, `remove_source()`,
  `set_source_data()` supporting GeoJSON, vector, raster, raster-dem, image, and
  video source types.
- **Native MapLibre layers** â€” `add_maplibre_layer()`, `remove_maplibre_layer()`
  for fill, line, circle, symbol, heatmap, fill-extrusion, raster, and hillshade
  layer types.
- **Style mutation** â€” `set_paint_property()`, `set_layout_property()`,
  `set_filter()` for runtime layer property changes.
- **Basemap switching** â€” `set_style()` replaces the entire basemap style at
  runtime.

---

## [0.2.0] â€” 2026-03-01

### Added

- **MapLibre GL JS v5.3.1** upgrade (from v3.6.2), with all breaking API changes
  handled in the JS init script.
- **Map controls** â€” `add_control()` and `remove_control()` for
  NavigationControl, ScaleControl, FullscreenControl, GeolocateControl,
  GlobeControl, TerrainControl, and AttributionControl.
- **Fit bounds** â€” `fit_bounds(bounds, padding, max_zoom, duration)` to fly/jump
  the camera to a geographic extent.
- **Map click events** â€” `map_click_input_id` fires on basemap clicks (even on
  empty areas).
- **Right-click events** â€” `map_contextmenu_input_id`.
- **`compute_bounds()`** static method to derive `[[sw, ne]]` from GeoJSON.
- Constants: `CONTROL_TYPES`, `CONTROL_POSITIONS`.

---

## [0.1.0] â€” 2026-02-28

### Added

- Initial release.
- `MapWidget` class with configurable view state, basemap style, tooltips, and
  Mapbox API key support.
- Layer helpers: `scatterplot_layer()`, `geojson_layer()`, `tile_layer()`,
  `bitmap_layer()`, generic `layer()`.
- WMS tile support via `{bbox-epsg-3857}` / `{bbox-epsg-4326}` placeholders
  with automatic CRS projection in the JS client.
- Click, hover, and viewport read-back reactive inputs.
- Draggable marker via `add_drag_marker()`.
- Layer visibility toggling via `set_layer_visibility()`.
- Tooltip configuration with `{field}` template interpolation.
- `update_tooltip()` for dynamic tooltip changes.
- Color utilities: `color_range()`, `color_bins()`, `color_quantiles()` with
  five built-in palettes (Viridis, Plasma, Ocean, Thermal, Chlorophyll).
- Binary data transport: `encode_binary_attribute()` for numpy arrays.
- View helpers: `map_view()`, `orthographic_view()`, `first_person_view()`.
- Lighting & effects support via `update(effects=[...])`.
- HTML export: `to_html()` for standalone browser-viewable maps.
- JSON serialisation: `to_json()` / `from_json()`.
- `@@` accessor syntax: identity (`@@d`), property (`@@d.prop`), expression
  (`@@=expr`).
- DataFrame / GeoDataFrame auto-serialisation in layer data.
- Extensions support: `layer(..., extensions=["DataFilterExtension"])`.
- Basemap constants: `CARTO_POSITRON`, `CARTO_DARK`, `CARTO_VOYAGER`,
  `OSM_LIBERTY`.
- `shiny_deckgl-demo` CLI entry point.
- Conda recipe (`conda.recipe/meta.yaml`).
- CDN-pinned assets: deck.gl 9.1.4, MapLibre GL JS 5.3.1.

[1.6.1]: https://github.com/razinka/shiny_deckgl/compare/v1.6.0...HEAD
[1.6.0]: https://github.com/razinka/shiny_deckgl/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/razinka/shiny_deckgl/compare/70f8a45...v1.5.0
[1.4.0]: https://github.com/razinka/shiny_deckgl/compare/70f8a45...70f8a45
[1.3.0]: https://github.com/razinka/shiny_deckgl/compare/cd57ebf...70f8a45
[1.2.0]: https://github.com/razinka/shiny_deckgl/compare/3980562...cd57ebf
[1.1.0]: https://github.com/razinka/shiny_deckgl/compare/3980562...3980562
[1.0.1]: https://github.com/razinka/shiny_deckgl/compare/f07585e...3980562
[1.0.0]: https://github.com/razinka/shiny_deckgl/compare/fa75ff1...f07585e
[0.9.0]: https://github.com/razinka/shiny_deckgl/compare/f3c7340...fa75ff1
[0.8.0]: https://github.com/razinka/shiny_deckgl/compare/d8a3b2e...f3c7340
[0.7.0]: https://github.com/razinka/shiny_deckgl/compare/b3cc3af...d8a3b2e
[0.6.1]: https://github.com/razinka/shiny_deckgl/compare/b3cc3af...b3cc3af
[0.6.0]: https://github.com/razinka/shiny_deckgl/compare/05bed3c...b3cc3af
[0.5.0]: https://github.com/razinka/shiny_deckgl/compare/a0066d0...05bed3c
[0.4.0]: https://github.com/razinka/shiny_deckgl/compare/9708b7a...a0066d0
[0.3.0]: https://github.com/razinka/shiny_deckgl/compare/49afabb...9708b7a
[0.2.0]: https://github.com/razinka/shiny_deckgl/compare/1d96b2d...49afabb
[0.1.0]: https://github.com/razinka/shiny_deckgl/compare/1d96b2d...1d96b2d
