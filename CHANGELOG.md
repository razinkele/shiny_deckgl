# Changelog

All notable changes to **shiny\_deckgl** are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and version numbers use [Semantic Versioning](https://semver.org/).

---

## [0.6.0] — 2026-03-01

### Changed

- Extracted CDN URLs into a shared `_cdn.py` module (single source of truth).
- `ui.py` now reads version from `_version.py` instead of hard-coding it (no
  more triple-sync on version bumps).
- Test file — moved `import asyncio` / `import pytest` to module level (71
  redundant in-method imports removed).
- README.md — full rewrite with accurate MapLibre v5.3.1 reference, 195 test
  count, and complete Phase 1–4 feature tables.
- Demo app (`app.py`) — comprehensive accordion sidebar covering all features.

### Fixed

- **Draw event listener leak** — repeated `enable_draw()` calls no longer
  accumulate orphaned `draw.create` / `draw.update` / `draw.delete` /
  `draw.modechange` listeners on the MapLibre map.
- `disable_draw()` now also removes map-level draw event listeners.
- `set_style()` emits a `console.warn` when native sources/layers exist,
  alerting that they will be destroyed by the style change.
- `query_at_lnglat()` no longer sends `"layers": null` when no layers are
  specified — the key is omitted entirely.
- `export_image()` docstring now documents `"webp"` as a supported format.
- `app.py` — removed unused `layer` import; corrected docstring version range.
- `components.py` — removed extraneous blank line between imports.
- `conda.recipe/meta.yaml` — version updated to 0.6.0; GitHub URL corrected
  from `arturas-baziukas/` to `razinkele/`.

---

## [0.5.0] — 2026-03-01

### Added

- **Drawing tools** — `enable_draw()`, `disable_draw()`, `get_drawn_features()`,
  `delete_drawn_features()` backed by MapboxDraw v1.4.3.
- **GeoPandas integration** — `add_geodataframe()` serialises a GeoDataFrame
  into a native MapLibre source + layer; `update_geodataframe()` replaces data
  in-place.
- **Feature state** — `set_feature_state()` and `remove_feature_state()` for
  interactive data-driven styling without redrawing layers.
- **Map export** — `export_image(format, quality)` captures a base64-encoded
  screenshot (PNG, JPEG, or WebP).
- Shiny inputs: `drawn_features_input_id`, `draw_mode_input_id`,
  `export_result_input_id`.

---

## [0.4.0] — 2026-03-01

### Added

- **Globe projection** — `set_projection("globe")` / `set_projection("mercator")`.
- **Terrain** — `set_terrain(source, exaggeration)` for 3D DEM rendering;
  `set_sky()` for atmosphere effects.
- **Popups** — `add_popup(layer_id, template)` with click-to-open popup on
  native MapLibre layers; `remove_popup()` to detach.
- **Spatial queries** — `query_rendered_features()` (pixel point or bounds) and
  `query_at_lnglat()` (geographic coordinates) with optional layer/filter
  restrictions; results delivered through `query_result_input_id`.
- **Multiple markers** — `add_marker()`, `remove_marker()`, `clear_markers()`
  with colour, draggable, and popup support.
- Shiny inputs: `marker_click_input_id`, `marker_drag_input_id`,
  `feature_click_input_id`.

---

## [0.3.0] — 2026-03-01

### Added

- **Native MapLibre sources** — `add_source()`, `remove_source()`,
  `set_source_data()` supporting GeoJSON, vector, raster, raster-dem, image, and
  video source types.
- **Native MapLibre layers** — `add_maplibre_layer()`, `remove_maplibre_layer()`
  for fill, line, circle, symbol, heatmap, fill-extrusion, raster, and hillshade
  layer types.
- **Style mutation** — `set_paint_property()`, `set_layout_property()`,
  `set_filter()` for runtime layer property changes.
- **Basemap switching** — `set_style()` replaces the entire basemap style at
  runtime.

---

## [0.2.0] — 2026-03-01

### Added

- **MapLibre GL JS v5.3.1** upgrade (from v3.6.2), with all breaking API changes
  handled in the JS init script.
- **Map controls** — `add_control()` and `remove_control()` for
  NavigationControl, ScaleControl, FullscreenControl, GeolocateControl,
  GlobeControl, TerrainControl, and AttributionControl.
- **Fit bounds** — `fit_bounds(bounds, padding, max_zoom, duration)` to fly/jump
  the camera to a geographic extent.
- **Map click events** — `map_click_input_id` fires on basemap clicks (even on
  empty areas).
- **Right-click events** — `map_contextmenu_input_id`.
- **`compute_bounds()`** static method to derive `[[sw, ne]]` from GeoJSON.
- Constants: `CONTROL_TYPES`, `CONTROL_POSITIONS`.

---

## [0.1.0] — 2026-02-28

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

[0.6.0]: https://github.com/razinkele/shiny_deckgl/compare/05bed3c...b3cc3af
[0.5.0]: https://github.com/razinkele/shiny_deckgl/compare/a0066d0...05bed3c
[0.4.0]: https://github.com/razinkele/shiny_deckgl/compare/9708b7a...a0066d0
[0.3.0]: https://github.com/razinkele/shiny_deckgl/compare/49afabb...9708b7a
[0.2.0]: https://github.com/razinkele/shiny_deckgl/compare/1d96b2d...49afabb
[0.1.0]: https://github.com/razinkele/shiny_deckgl/compare/1d96b2d...1d96b2d
