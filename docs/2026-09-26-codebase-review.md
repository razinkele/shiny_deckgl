# Codebase review — shiny_deckgl v1.10.1 (2026-09-26)

Read-only review, done after the 2026-09-06 review and its fixes shipped as 1.10.0 and 1.10.1.
Items fixed by that round are not repeated here. The main focus is the **layer legend** code.

This file records results only. Nothing in the source was changed.

**How the findings were checked:**
- I read the legend code myself. I also compared it with the deck.gl 9.4.0 `Widget`/`WidgetManager` source and the
  `@watergis/maplibre-gl-legend@2.0.7` bundle. Both were downloaded from unpkg and read line by line.
- Three sub-reviewers covered the rest of the code: the Python API, the JS runtime and the demo app.
- For the claims they rated most severe, I re-read the code myself, noted as *(re-verified)*.
- Findings marked *(probed)* were also run in the `shiny` env or under Node.
- Findings marked *(needs browser)* were deduced from source and have not been run in a browser.

**Status (branch `fix/legend-l1-l6`, committed, not pushed):**
- **Also fixed:**
  - **J9.** The sanitiser strips SVG animation elements and `<math>`, and its output is re-sanitised until it
    stops changing.
  - **P1.** `json_safe` handles numpy, pandas and date types, and covers the add_source, set_source_data and
    add_cluster_layer payloads.
  - **P2.** GeoDataFrames are reprojected to EPSG:4326. One with no CRS whose coordinates can't be lon/lat
    gets a warning.
  - **J2.** Maps re-rendered by `render.ui` are disposed and re-created.
  - **J3.** Style readiness is based on the parsed style, and the queue drains on `style.load`, `styledata`
    or `idle`. Confirmed in a browser first.
  - **J4.** `diff` is passed explicitly. A timeout runs the queue when the style is usable. The demo's
    start-up `set_style` was removed; it had been wiping the MapLibre tab's layers.
- **Second batch (branch `fix/review-batch-2`, stacked on PR #1, not pushed):**
  - **J5.** Asynchronous renders draw the current layer cache, not a stale copy.
  - **D1–D4.** Demo fixes:
    - the Widget Gallery scenarios draw again;
    - the gallery and Colour Scales legends match what is drawn;
    - the Advanced tab keeps its columns;
    - the seal IBM runs in a worker thread, with lower slider caps and patch-only speed/trail updates.
  - **L7, L8.** Swatches show gradients for aggregation layers and read colours through the layer's own
    accessor path.
  - **M1, M2, M4.**
    - Unchanged controls are kept rather than rebuilt.
    - With no `targets`, the legend lists the app's native layers and redraws once a new layer is drawn.
    - `reverse_order` now defaults to `True`.
  - **M5.** `add_control` now waits for the style.
  - **Also fixed on the same branch:** P3, P4, J8, P9, P6, P7, P10, P12, J6 (restart-on-update, dispose
    collision, work after dispose), J7, P8, D5, D6, P5, L10, and the opacity-control desync introduced by M1.
    L9 was fixed by J5.
  - **J6 remainder, done on branch `feat/shared-frame-loop` (stacked on batch 2):**
    - Resolved layer props are cached per `lastLayers` entry.
    - One frame loop per map.
    - A single `renderLayers()` carries the animation state into every render.
    - Animation frames no longer repaint the basemap: 55 renders/s → 0 on the seal tab.
  - **Still open:**
    - **J10:** `fly_to`/`ease_to` fall back to `[0,0]`. Not reachable from Python, which requires lon/lat.
    - **P11:** delete `_mixins/`? It's documented as a deliberate reference copy, so this needs the owner's
      call.
    - **M3:** the plugin's `queryRenderedFeatures` cost is documented only.
- **Found while verifying:** `test_e2e_playwright.py::TestServedPathRendersRealLayers::test_deck_layers_are_present_on_the_gallery_map`
  fails on `main` too. This was already failing before this work, not a regression.
- **L1–L6 fixed.**
  - L1 was fixed more narrowly than suggested below. Layers the *user* unticks stay listed. Layers the *server*
    hides are still left out, because the demo's "Active Layers" legend relies on that.
  - A new `include_hidden=True` lists every layer.
  - L2 adds `MapWidget.legend_visibility_input_id`. The demo's Layers tab now mirrors legend toggles onto its
    sidebar switches.
- **J1 fixed.** Calls after `.` (the `?.(` form) are rejected. A computed `[...]` key must now be a number, a
  quoted string or a `d.a.b` path.
- Everything else below is still open.

---

## Part 1 — Layer legends

The package has two separate legend systems:

| | deck.gl `layer_legend_widget` | MapLibre `legend_control` |
|---|---|---|
| Code | `deckgl-init.js` 150–511, `widgets.py:184` | `controls.py:69`, `deckgl-init.js:544`, third-party plugin |
| Shows | deck.gl overlay layers | native MapLibre style layers only |
| Where entries come from | manual `entries`, or `auto_introspect` of `instance.lastLayers` | `map.getStyle().layers` + `queryRenderedFeatures()` |
| Checkbox toggles | `lastLayers[i].visible`, **client-only** | `setLayoutProperty(visibility)`, **client-only** |

### 1.1 deck.gl legend widget

**L1 — HIGH: a layer hidden from the legend disappears from it, and can't be turned back on.**
- **Where:** `_introspectLayers` (`deckgl-init.js:341`) skips `lp.visible === false`.
- **Failure:**
  - Uncheck a row in an auto-introspected legend: `_toggleLayer` sets `visible:false` in `lastLayers`.
  - The next re-render drops the row. These keep `visible:false` in `lastLayers` and so trigger it:
    - a `deck_partial_update`;
    - a `deck_layer_visibility`;
    - any widget re-render (`deck_set_widgets`, or `setProps` → `onRenderHTML`).
  - The layer can no longer be shown again from the legend.
  - The same thing happens when the server hides a layer with `set_layer_visibility`.
  - A full `update()` behaves differently: it replaces `lastLayers` with Python's list, so the row and the layer
    come back. That is L2, not L1.
- The demo review hit this independently in the Widget Gallery and the Layers tab.
- **Fix:** keep hidden layers in the list and render them unchecked.
- If "only visible layers" is really wanted, make it an option such as `hide_invisible` and hide the checkbox
  when it's on.

**L2 — HIGH: legend toggles never reach the server, so the next update undoes them.**
- **Where:** `_toggleLayer` (`deckgl-init.js:487`) changes only the client's `lastLayers`. Nothing calls
  `Shiny.setInputValue`.
- **Failure:**
  - Any later `update()` resends `visible` from Python, and the layer the user hid comes back.
  - Sidebar switches and legend checkboxes drift out of sync. This is visible in the demo Layers tab
    (`_app_server.py:2545-2575`).
- **Fix:** emit `Shiny.setInputValue(mapId + '_legend_visibility', {layer_id: visible}, {priority:'event'})`.
- Document it as an input, e.g. `MapWidget.legend_visibility_input_id`, so the app can keep its own state and
  switches in step.

**L3 — MEDIUM: the collapsed/expanded state resets on every layer update.**
- **Where:** `_renderInto` (`deckgl-init.js:233-261`) rebuilds the whole DOM from `opts.collapsed` on each
  `_refresh()`.
- **Failure:** a user expands a legend that starts collapsed. The next update, e.g. a timer-driven
  `partial_update`, collapses it again.
- **Fix:** keep the collapsed state on the instance, e.g. `this._collapsed`, starting from the prop. Only re-read
  the prop when it actually changes.

**L4 — MEDIUM: `collapsed=True` with no `title` hides the legend for good.**
- **Where:** the header, which is the only way to toggle, is only created `if (opts.title)`. The body still gets
  `display:none`.
- **Fix:** always show a header when `collapsed` is set, using a default title such as "Layers". Alternatively,
  raise `ValueError` in `layer_legend_widget` when `collapsed=True` and `title is None`.

**L5 — MEDIUM: props that are dropped from an update keep their old values.**
- **Where:** deck.gl's `WidgetManager._setWidgets` reuses a widget instance with the same `id` and calls
  `oldWidget.setProps(new.props)`. Its `Widget.setProps` does `Object.assign(this.props, props)`, i.e. merges.
- `layer_legend_widget()` only writes `title`, `excludeLayers` and `labelMap` when they're truthy (`widgets.py:249-254`).
- **Failure:** changing from `title="X"` to no title leaves "X" in place. Clearing `exclude_layers` or
  `label_map` also has no effect.
- **Fix:** always emit the keys, e.g. `"title": title`, `"excludeLayers": list(exclude_layers or [])`,
  `"labelMap": dict(label_map or {})`.

**L6 — MEDIUM: a legend widget can't be removed by sending an empty widget list.**
- **Where:** `buildWidgets([])` returns `undefined` (`deckgl-init.js:1375`), so `overlay.setProps` never sees
  `widgets: []`. *(re-verified)*
- **Failure:** in the demo, switching off every widget including the legend leaves the legend and the other
  widgets on screen.
- The same bug affects every widget, and effects and views too (Part 2, J8).
- **Fix:** return `[]` for an explicit empty array.

**L7 — MEDIUM: swatch colours are wrong for aggregation layers.**
- `TYPE_SHAPE` maps `HexagonLayer`, `GridLayer`, `ScreenGridLayer` and the column types to `rect`. Only
  `gradient` shapes read `colorRange`. So a `HexagonLayer` with a custom `colorRange` still shows the fixed teal
  from `LAYER_TYPE_DEFAULT_COLOR`.
- For Hexagon, Grid, Heatmap and ScreenGrid layers *without* `colorRange`, deck.gl draws its default YlOrRd ramp
  `[[255,255,178],[254,217,118],[254,178,76],[253,141,60],[240,59,32],[189,0,38]]`. The legend instead shows a
  solid teal or orange swatch.
- `ContourLayer` ignores the colours in its `contours[].color`.
- **Fix:**
  - Treat any aggregation layer that has `colorRange` as a gradient.
  - Fall back to deck's default ramp rather than one solid colour.
  - For contours, build the gradient from `contours[].color`.

**L8 — LOW-MEDIUM: colours from data only match three hard-coded field names.**
- **Where:** `_sampleDataColor` looks at `d.color`, `d.sourceColor` and `d.fillColor`. It ignores the layer's
  actual accessor string.
- **Failure:**
  - `getFillColor="@@=d.fill_color"`, as in the demo SST grid (`_app_server.py:2670`), gives a grey swatch.
  - GeoJSON `@@=properties.x` gives grey too, because `data` is a FeatureCollection object, not an array.
  - A field called `color` that isn't the one the accessor uses gives the *wrong* colour.
- **Fix:** when the accessor matches `^@@=d\.([\w.]+)$` or `^@@=properties\.…`, read that path from the first row
  or feature. Otherwise skip sampling.
- Consider showing a gradient over the first N rows when their colours differ.

**L9 — LOW: a click on a legend checkbox can be overwritten by an update already in progress.**
- `_toggleLayer` renders synchronously from `lastLayers` without claiming an update generation.
- A `deck_update` that is still rasterising SVG atlases then resolves and paints the `layersData` it captured
  earlier. The toggle disappears from the screen while `lastLayers` still records it.
- This is part of the wider render-generation problem (Part 2, J5), and the same fix covers it.

**L10 — LOW: bookkeeping and code-quality issues.**
- `mapInstances[id]._legendWidget` holds one slot. With two legend widgets, only the one rendered last refreshes.
  Both also share the fixed id `deck-layer-legend`, so deck.gl would merge them anyway. Either accept an `id`
  and keep a set of widgets, or document "one per map".
- `onRemove` doesn't clear `_legendWidget`, so a detached element keeps being re-rendered.
- `_extractEntry` step 4 (`deckgl-init.js:378-380`) is unreachable: `getColor` was already tried in step 3.
- The comment on line 154 refers to a `DeckLegendControl` that no longer exists. The `.deck-legend-*` CSS header
  in `styles.css:21` has the same stale name.
- `GeoJsonLayer` is always given the `circle` shape, which is wrong for polygon and line GeoJSON.
- **No JS-level behavioural tests exist for the legend.** `tests/test_basic.py` only checks the Python dict. L1,
  L3 and L5 would all be caught by one Playwright test that toggles a row and then pushes an update.

### 1.2 MapLibre `legend_control` (watergis 2.0.7)

What the plugin itself does, from reading its source:
- It rebuilds itself on every `moveend` and `styledata`.
- Each rebuild runs `map.queryRenderedFeatures()` with **no arguments**, i.e. every feature of every layer in
  the viewport.
- Its `onRemove` does **not** remove the `moveend`, `styledata` or `idle` listeners. They are anonymous arrow
  functions and can't be removed.

**M1 — MEDIUM: rebuilding the controls leaks listeners.**
- `set_controls` removes and re-adds every control. In the demo that happens on *every* sidebar switch and every
  basemap change (`_app_server.py:335-358`). Each rebuild leaves two map listeners attached for the life of the
  map.
- The leaked handlers do nothing, because `this.map` is undefined after removal, but they build up.
- **Fix:** only replace the control whose options actually changed in `deck_set_controls`, rather than replacing
  all of them.
- Also, the demo's "re-apply controls so the legend picks up the new layers" (`_app_server.py:356`) is
  unnecessary: the plugin already rebuilds on `styledata`.

**M2 — MEDIUM: the defaults are close to useless on a vector basemap.**
- `legend_control()` with `targets=None` lists **every** style layer of the basemap. That is about 100 on CARTO
  Positron, around 40 of them rendered.
- The docstring's own example in `map_widget.set_controls` (`map_widget.py:874`) does exactly this.
- **Fix:** when `targets` is absent, default on the JS side to the layer ids in `instance.nativeLayers`, i.e. the
  ones the app added. Keep an explicit `targets={}` meaning "everything".
- This needs a Python change too. JS currently does `opts.targets || {}`, so it can't tell "no targets" from
  `{}`. Python must send `targets: null` explicitly (or a sentinel) when none were given.

**M3 — LOW-MEDIUM: performance.**
- On every `styledata` event (every `add_maplibre_layer`, `set_paint_property` or `set_layout_property`) and
  every `moveend`, the plugin runs a full `queryRenderedFeatures()`.
- On dense vector tiles that takes tens of milliseconds per event.
- The plugin can't do less, so document the cost. `only_rendered=False` avoids the query entirely, since the
  plugin still collects rendered features but only uses them for filtering.

**M4 — LOW: the defaults and docs don't match the plugin.**
- `reverse_order=False` overrides the plugin's default of `true`. The legend then lists the bottom layer first,
  the opposite of how the layers are stacked.
- `show_default` also makes the panel sticky: when it's False, any click outside the panel closes it. That's
  plugin behaviour, but it isn't documented.
- The plugin's checkbox handling uses `document.getElementsByName(layerId)` across the whole page. Two maps
  whose layer ids overlap will flip each other's checkboxes, though not each other's layers.

**M5 — LOW: `deck_add_control` doesn't wait for the style to finish loading, but `deck_set_controls` does.**
`add_control(session, "legend", …)` sent straight after `add_maplibre_layer` can be built before that layer
exists. The plugin's `styledata` listener mostly recovers from this.

---

## Part 2 — Rest of the codebase

### JS runtime (`deckgl-init.js`)

**J1 — HIGH (security): the check that blocks code in accessor strings can be bypassed.** *(probed under Node, re-verified by tracing `isSafeAccessorExpr`)*
- **Where:** lines 1048 and 1118.
- **How:**
  - The call-detection regex doesn't catch `?.(`.
  - The list of dangerous property names is defeated by string concatenation.
  - `d["con"+"structor"]["con"+"structor"]?.("…")?.()` passed the check and ran code.
- **Failure:** stored XSS in any app whose accessor strings come from users or uploaded JSON, including the
  `to_json`/`from_json` round-trip.
- **Fix:** reject `?.` and computed keys that aren't a single string literal. Better, check a token or AST
  whitelist instead of using regexes.

**J2 — HIGH: after a Shiny re-render, the map stays blank and the old one leaks.** *(re-verified)*
- **Where:** the MutationObserver (line 3710) only disposes a map when `!document.getElementById(rel.id)`.
- **Failure:**
  - When `render.ui` replaces the element in place, the new node with the same id already exists by the time the
    observer runs.
  - So the old map is never disposed, and init is skipped because `mapInstances[id]` still exists.
  - Every later message goes to the old, detached map. The old map's WebGL context and animation loops leak.
- **Fix:** dispose when `mapInstances[id].map.getContainer() === rel`, or when that container is no longer
  `isConnected`.

**J3 — HIGH *(needs browser)*: MapLibre calls can be queued forever.**
- **Where:** `whenStyleReady` (line 571) uses `map.isStyleLoaded()`. That returns false while *any source or tile
  is loading*, and the queue it falls back to only drains on `style.load`.
- **Failure:** after the first style load, an `add_maplibre_layer`, `set_controls`, `add_popup` or
  `set_paint_property` sent while tiles load, e.g. right after `add_source` or during a pan, waits for a
  `style.load` that never comes. Nothing is logged.
- Startup is not affected, because the queue drains on the first `style.load`.
- **Fix:** test whether the style has been parsed (`map.style && map.style._loaded`), or also drain the queue on
  `idle`.

**J4 — MEDIUM: `set_style` can silently abandon queued work.**
- The 30 s fallback throws the queued callbacks away instead of running them.
- MapLibre's `diff` defaults to `true` (line 2582). If a diffed style swap doesn't emit `style.load`, every
  queued native call is lost.
- **Fix:** pass `diff: !!payload.diff` explicitly, and drain the queue on timeout if the style has loaded.

**J5 — MEDIUM: fix #19 from the previous round is incomplete.**
- `deck_update` and `deck_partial_update` use separate update counters. `deck_layer_visibility`, the legend
  toggle and the tab-shown rebuild use none.
- **Failure:** a slow `deck_update` can repaint over a later patch or toggle.
- **Fix:** one render generation per map, claimed by every render path, and always render from `lastLayers`.

**J6 — MEDIUM: animation problems.**
- Every `update()` restarts a *running* trips animation from time 0 (line 1927).
- The trips loop and the property-animation loop each set the whole layer list, so they fight and the map
  flickers.
- Each animation frame re-clones binary data, forcing the GPU to re-upload it at 60 fps.
- Async `.then` code keeps running after the map has been disposed.
- A paused animation loses its paused time and head icons on any re-render.
- Disposing map `"map"` also wipes the animation state of `"map_2"`, because it matches globals by id prefix.

**J7 — MEDIUM: messages can be lost or pile up.**
- A message for a map that `render.ui` hasn't created yet is dropped with a warning.
- The queue for maps in hidden tabs has no size limit. A timer-driven `update()` to a hidden tab queues every
  full payload.
- **Fix:** keep only the newest `deck_update` per map in the queue.

**J8 — MEDIUM: `widgets`, `effects` and `views` can't be cleared once set.**
- `buildWidgets([])` returns `undefined`.
- Python drops empty `effects` and `views` because it tests `if effects:`, and `setProps` merges, so the old
  values stay.

**J9 — MEDIUM (defence in depth): the HTML sanitiser misses SVG `<animate>` and `<set>`.**
- `<animate attributeName="href" values="javascript:…">` gets through the sanitiser.
- It only matters when attacker-influenced HTML reaches a popup or tooltip template.
- **Fix:** strip those elements, or use DOMPurify.

**J10 — LOW:**
- `fly_to` and `ease_to` still default a missing centre to `[0,0]`. The earlier fix only covered
  `buildCameraOptions`.
- The tooltip-dismiss pick ignores `pickingRadius`.
- Globe projection and terrain are lost after `set_style`.

### Python API

**P1 — HIGH: common data types aren't JSON-safe.** *(probed)*
- `json_safe` only handles non-finite floats.
- These still reach Shiny's `json.dumps` and raise `TypeError`, which kills the session inside an Effect:
  - pandas `Timestamp`, `NaT`, `pd.NA`;
  - numpy `int64` and `float32` in layer props;
  - `ndarray`.
- `set_source_data`, `add_cluster_layer` and `add_source` skip `json_safe` altogether.

**P2 — HIGH: GeoDataFrames are never reprojected to lon/lat.** *(probed)*
- There is no `to_crs` anywhere in the package.
- A GeoDataFrame in UTM or LKS94 (EPSG:3346) is sent in metres and draws nowhere, with no warning.
- **Fix:** reproject to EPSG:4326 when `crs` is set, and warn when `crs` is `None`.

**P3 — MEDIUM-HIGH: `terrain_extension()` is silently dropped.** *(re-verified)*
- deck.gl 9.4 only exports `_TerrainExtension`, and `resolveExtensions` (line 1142) has no fallback to the
  underscore name.
- The same kind of bug was fixed earlier for GlobeView and the widgets.

**P4 — MEDIUM: `to_html()` omits h3-js.** *(re-verified)* H3 layers render nothing in exported HTML.

**P5 — MEDIUM: `to_html()`, `to_json()` and `from_json()` drop most widget config.**
- Dropped: `controls`, `controller`, `cooperative_gestures`, `picking_radius`, `use_device_pixels`, `parameters`,
  `animate`, `interleaved`.
- `controls=[]` still gets a NavigationControl in the export.
- `to_json()` has no `session=` argument, so it always embeds the default style.

**P6 — MEDIUM: fix #21 from the previous round is incomplete.** `update_tooltip` and `set_cooperative_gestures`
still write to the shared widget object, so one session's changes leak into another session's export.

**P7 — MEDIUM: the `on_viewport_change` debounce doesn't work.**
- Its `asyncio.sleep(0.3)` runs inside Shiny's global reactive lock, so no second call can ever start and
  replace the first.
- It never debounces. Instead it stalls every session for 300 ms on each camera move.

**P8 — MEDIUM: `controller` is only partly honoured.**
- A controller dict passed at init is ignored.
- After `controller=False`, `set_controller(True)` never turns MapLibre's handlers back on.

**P9 — MEDIUM: the colour helpers fail on real data.**
- `color_bins` crashes when the data contains NaN.
- `color_quantiles` puts NaN in the top bin.
- Both raise "truth value ambiguous" when given a `pd.Series` or `ndarray`.

**P10 — MEDIUM: SHYFEM CRS detection assumes UTM 33N.** It only checks `abs(x) > 100000`. UTM 34N and
LKS94 grids for Klaipėda and the Curonian Lagoon end up about 6° off.

**P11 — MEDIUM: `_mixins/` is stale duplicate code.**
- It still contains the `</script>` XSS and the unescaped view-state attributes fixed earlier. It is still
  importable and still unit-tested.
- Delete it, or regenerate it from `map_widget.py`.

**P12 — LOW:**
- `timeline_control(interval_ms=)` is never used. `timeline_server` accepts `interval_ms=0`, which gives a tight
  loop.
- The docs are stale:
  - `__init__.py` example: refers to `set_layers`, `add_layer` and `@render.effect`, none of which exist, and has
    no `head_includes()`;
  - easing count;
  - `coordinateSystem=2`;
  - `has_image` return type;
  - IBM species count and atlas size.

### Demo app

**D1 — HIGH: 3 of the 6 Widget Gallery scenarios draw nothing.** *(re-verified)*
- `wg-heat` and `wg-hexagons` use `@@=d.position` on `[lon, lat, w]` lists.
- `wg-arcs` uses `d.from` and `d.to`, but the data only has `sourcePosition` and `targetPosition`.
- Their legends still show entries.

**D2 — HIGH: the Advanced tab loses its cargo columns at startup.**
- `_v1_layers` runs at init without `ignore_init` and *replaces* `_adv_layers` instead of merging.
- The columns and every later brushing, filter or transition layer are wiped.

**D3 — HIGH: the seal IBM can freeze the server.** *(measured)*
- At the slider maximums, `make_seal_trips_ibm` takes **179 s**, synchronously on the event loop, and produces
  23 MB of JSON. Every session is blocked for that time.
- Each speed or trail tick resends the full payload.

**D4 — MEDIUM: legend problems in the demo.**
- **Colour Scales tab:** `legend_entries` is built and never used (`_app_server.py:685`). *(re-verified)* Its
  bin labels are also wrong in quantiles mode.
- **Time & Space SST:** the auto legend shows one grey box (L8). Its `color_bins` range comes from the cells in
  view, so a given temperature changes colour as you pan.
- **Widget Gallery manual legend:** the colours don't match the layers.
  - Routes are coloured per datum, but the legend shows one swatch.
  - Hexagons draw deck's yellow-to-red ramp, but the legend is green.
  - Arcs go blue to orange, but the legend has no second colour.
- **Layers tab and Widget Gallery:** legend checkboxes and sidebar switches get out of sync (L1, L2).

**D5 — MEDIUM: other demo bugs.**
- The Tile3D toggle never builds its layer.
- The cluster layer is lost when the basemap changes.
- Every 3-D tab input re-flies the camera, snapping back the user's pan and zoom.
- The "range" colour mode is identical to "bins".
- The CRW "geodesic routes" have zero length.
- The HTML export writes to a fixed temp path shared by all users, and reports a server path.

**D6 — LOW:**
- Three basemap effects reload the style at startup because they lack `ignore_init`.
- The layer and widget counts contradict each other: 24 / 33 / 34, and 17 / 18.
- The "2,500 random points" hint is wrong: the code builds a regular 50×50 grid.
- A missing bathymetry file isn't reported.

---

## Suggested order of work

1. **Security:** J1 (accessor check bypass), then J9.
2. **Legend correctness,** as one release: L1, L2, L3, L4, L5, L6 and J8, plus a Playwright test that toggles a
   row and then pushes an update.
3. **Data correctness:** P1 (JSON types) and P2 (CRS). These matter most for marine GIS users.
4. **Lifecycle:** J2 (re-render), J3 (style queue, confirm in a browser first), J5 (single render generation).
5. **Demo:** D1–D4, since the demo is how the package is judged.
6. **Legend quality:** L7, L8, M1, M2, M4.
7. **The rest.**
