# Dependency review and improvement roadmap — shiny_deckgl 1.11.1 (2026-09-27)

What the newest Shiny for Python, deck.gl and MapLibre GL JS releases offer this package, and what
is worth doing about it. Written after the 2026-09-26 codebase review was released as 1.11.0/1.11.1.

**How this was checked.** Versions come from the npm and PyPI registries. Release contents come from
the upstream changelogs (deck.gl `docs/whats-new.md`, MapLibre `CHANGELOG.md`, py-shiny
`CHANGELOG.md`) and, where the changelogs were vague, from the upstream source at the tagged
version (py-shiny 1.8.0 `testserver`, `_connection.py`, `_session.py`, the bundled `shiny.js`;
deck.gl `modules/maplibre/src`). Claims about this package come from its source. Nothing here was
tried in a browser yet; the "risk" column is an estimate.

---

## 1. Where things stand

| Dependency | Pinned | Latest | Gap |
|---|---|---|---|
| Shiny for Python | floor `>=1.6.3`; 1.7.0 installed | **1.8.0** (2026-09-13) | one minor release |
| deck.gl + `@deck.gl/widgets` | 9.4.0 | **9.4.0** (2026-09-05) | current; declared the final v9 |
| MapLibre GL JS, served (`MAPLIBRE_VERSION`) | 6.7.0 | **6.11.2** (2026-09-24) | four minor releases |
| MapLibre GL JS, `to_html()` export | 5.24.0 | 5.24.0 (latest 5.x, 2026-04-23) | none |
| `@mapbox/mapbox-gl-draw` | 1.5.1 | 1.5.2 (2026-09-14) | patch |
| `@watergis/maplibre-gl-legend` | 2.0.7 | 2.0.7 | none |
| `maplibre-gl-opacity` | 1.8.0 | 1.8.0 (2025-01-19) | none; project is quiet |
| `h3-js` | 4.5.0 | 4.5.0 | none |

deck.gl publishes no v10 prerelease (`dist-tags`: `latest` 9.4.0, `beta` 9.4.0-beta.4). v9.4's notes
say v10 "is expected to introduce larger architectural changes, including luma.gl v10, loaders.gl v5,
and support for more advanced binary data pipelines".

---

## 2. Roadmap

Ordered by value for this package. Effort: S = an hour or two, M = a day, L = several days.

| # | Item | Effort | Risk |
|---|---|---|---|
| 2.1 | MapLibre 6.7.0 → 6.11.2 | S | low |
| 2.2 | `MapboxOverlay` → `MapLibreOverlay` | S–M | low–medium |
| 2.3 | Widget refresh: new helpers, drop dead ones, events → Shiny inputs | M | low |
| 2.4 | Expose 9.4 layer/extension props; `pickable: '3d'` | S–M | low |
| 2.5 | Shiny 1.8.0: reconnect resync, headless demo test, deprecations | M | low |
| 2.6 | WebGPU opt-in flag | S | n/a (experimental) |
| 2.7 | deck.gl v10 readiness | — | — |

### 2.1 Upgrade MapLibre to 6.11.2

**Why.** Since 6.7.0 (all from the MapLibre changelog):

- 6.11.1: worker-tile memory leak fixed. The demo runs eleven maps and the e2e suite is already
  memory-bound on a 16 GB machine.
- 6.9.0: `setStyle()` no longer crashes with terrain. The demo swaps basemaps with terrain available.
- 6.11.2: `Map#once()` layer filtering fixed. The style-ready queue (`whenStyleReady`) uses `once`.
- 6.8.0: `map.getStyleUrl()`. The client could report which style it actually has, so
  `MapWidget.current_style()` stops being an assumption.
- 6.9.0–6.11.2: per-frame performance work (projection data uploaded once per frame, faster
  triangulation, symbol placement).
- 6.4.1: a DOM-sanitisation fix in MapLibre's own code. Not load-bearing here (popups and tooltips go
  through the package's sanitiser), but one less thing to reason about.

**Compatibility.** 6.9.0 lists one breaking change: the RTL text plugin is no longer needed. The
package never loaded it. The J3 fix reads MapLibre's `style._loaded` internal; it is still present in
6.11.2's `src/style/style.ts`.

**How.** Bump `MAPLIBRE_VERSION` in `_cdn.py`, then run `tests/test_maplibre_v6.py`, the
`test_e2e_*` modules and the demo e2e classes one at a time. Leave the export pin at 5.24.0: v6's
module worker still dies on `file://`.

### 2.2 Switch to `MapLibreOverlay`

**Why.** deck.gl 9.4 added `@deck.gl/maplibre`, "the recommended deck.gl integration for MapLibre GL
JS", supporting MapLibre v4.5.1, v5 and v6. The umbrella bundle the package already loads exports it
(`deck.MapLibreOverlay`), so no new script tag is needed. Its props type is identical to
`MapboxOverlay`'s (`Omit<DeckProps, …> & { interleaved?: boolean }`).

What it does that matters here, from `modules/maplibre/src`:

- `compatibility.ts` reads MapLibre's projection (`mercator` | `globe`) and terrain elevation and
  feeds them to deck.gl. Today the demo's MapLibre tab uses native layers because deck.gl overlays
  were not globe-safe; with this overlay, deck.gl layers should render correctly under the Globe
  control, and the camera target elevation is synchronised over terrain.
- `layer-group.ts`: in interleaved mode, deck.gl layers are grouped by `beforeId`, so a deck.gl layer
  can be placed under basemap labels. The package supports `before_id` only for native layers.

**Caveats (documented upstream).** On the globe, `TextLayer` and non-billboard `IconLayer` have
rendering limitations; deck.gl layers are not draped over MapLibre terrain.

**How.** One line in `deckgl-init.js` (`new deck.MapboxOverlay(` → `new deck.MapLibreOverlay(`),
then a `before_id`/`beforeId` option on deck.gl layers in interleaved mode, plus tests: the existing
e2e modules, the demo's Globe control with a deck.gl layer visible, and terrain. Keep the
`overlay._deck` access (used by the export and tests) under review: it is internal in both overlays.

### 2.3 Refresh the widget layer

**Dead helpers.** `fps_widget()` and `view_selector_widget()` still ship but resolve to nothing:
`@deck.gl/widgets@9.4.0` exports neither `FpsWidget` (merged into `StatsWidget` in 9.3) nor
`ViewSelectorWidget`. Deprecate both with a warning, and have `fps_widget()` return a `StatsWidget`
spec.

**Missing helpers.** 9.3/9.4 export `PopupWidget`, `IconWidget`, `ToggleWidget`, `SelectorWidget`
and `ScrollbarWidget`, and `ZoomWidget` gained `zoomStep`. Add helpers in `widgets.py` following the
existing pattern.

**Widget events as Shiny inputs.** 9.3 gave widgets state callbacks — `onTimeChange`,
`onPlayingChange`, `onExpandedChange`, `onThemeModeChange`, `onFullscreenChange`, `onLoadingChange`,
`onReset`, `onZoom`, `onGeocode`, `onChange` — and controlled props (`time`, `playing`, `expanded`,
`themeMode`) alongside `initial*` defaults. `buildWidgets()` could attach these callbacks and forward
them with `Shiny.setInputValue`, the way the layer legend now reports toggles via
`legend_visibility_input_id`. Then:

- the timeline becomes a real Shiny input (`input[widget.timeline_input_id]()` → `{time, playing}`),
  and the server can drive it through `set_widgets()` with the controlled `time`/`playing` props,
  which would let `_timeline.py`'s polling go;
- geocoder results, theme changes and toggle/selector values reach the server.

### 2.4 Expose what deck.gl 9.4 already provides

Layer kwargs pass straight through, so most of this is documentation, typing and demo coverage:

- `antialiasing` on `PathLayer`, `LineLayer`, `ArcLayer`, `PointCloudLayer` (analytic, no MSAA;
  composite layers forward it). Worth a demo toggle: MapLibre's canvas defaults to `antialias: false`.
- `PathStyleExtension`: `dashMode`, `dashUnits`. `FillStyleExtension`: hatch/cross-hatch/dot
  patterns, `fillPatternSizeUnits`, `getFillPatternBackgroundColor`. Add to the extension helpers.
- `TileLayer` `visibleMinZoom`/`visibleMaxZoom` (draw range separate from load range), for the
  WMS/tile helpers.
- `ScatterplotLayer` `getPixelOffset` (transition-enabled screen-space offset).
- `TextLayer` per-object clipping boxes and sticky text (9.3).

One item needs code: **`pickable: '3d'`** (9.3) returns true 3-D coordinates on picked geometry.
For the bathymetry columns, the SHYFEM mesh and 3-D tiles, the click input could carry an elevation.

**Controller options do not apply.** 9.4's `maxBounds`, `maxBoundsPadding`, `trackpadGesture`,
`doubleClickDragZoom`, `zoomAround`, `rubberBand` and `rotationPivot` belong to deck.gl's
controllers. Under either overlay MapLibre does the interaction (`controller` is mapped onto
MapLibre's handlers since 1.11.0), so the equivalents to expose are MapLibre map options:
`maxBounds`, `maxPitch`, `renderWorldCopies`, `antialias`.

### 2.5 Shiny for Python 1.8.0

**`session.allow_reconnect()`.** On a successful reconnect "the browser sends all of its current
input values to the session on the server, and the server recalculates any outputs and sends them
back". Checked against the client: `shiny:connected` fires on every socket open, so it fires again on
reconnect, and the package's one-shot guard (`_shinyConnectedHandled`) correctly leaves the existing
maps alone. But the maps are driven by custom messages, not outputs: any `update()` sent while the
socket was down is lost and the map stays stale.

*Suggestion:* keep each session's last `update()` payload (and native-layer calls) on the Python side
and re-send them when the client reports a reconnect (a second `shiny:connected` → an
`input[<id>_reconnected]` event). Only useful under hosting that keeps sessions alive (Posit
Connect, Shiny Server); on plain `shiny run` a reconnect starts a new session, as the docstring says.

**`shiny.testserver.test_server()` and the `local_server` fixture.** An in-memory server that runs
the real reactive graph without a browser. Checked: `MockConnection.send()` is `pass`, so custom
messages are discarded and it cannot assert on `deck_update` payloads. `tests/conftest.py`'s
`_FakeSession` stays the tool for that. It is still valuable: a test that runs the demo `server()`
under `test_server()`, flips every switch and asserts `is_ok()` (plus the status text outputs)
would catch effect exceptions — the Advanced-tab bug from the 2026-09-26 review was one — without
the Playwright suite's memory cost. Requires `shiny>=1.8.0` in the `test` extra only.

**Deprecations.** `@render.download` is already replaced (1.11.0). `ui.output_text_verbatim()` is
deprecated in 1.8.0 in favour of `ui.output_code()` / `ui.output_text()`; the demo UI uses it 15
times. Mechanical.

**`ui.page_html()`** (own `index.html` with Shiny dependencies injected) does not change anything for
this package.

**Not available:** py-shiny has no `reactive.debounce`/`throttle`, so the reschedule-based debounce
in `on_viewport_change` stays the right design.

### 2.6 WebGPU: opt-in only

9.4 ships WebGPU support for every official layer, but its notes keep it experimental and not for
production. It can only apply in overlaid mode (interleaved shares MapLibre's WebGL2 context). The
package has no WebGPU references. A `MapWidget(device_type="webgpu")` flag passed through to the
overlay's `deviceProps` is cheap to add for experiments; it should not be the default, and a
machine without a discrete GPU will not show a benefit. The `visgl:webgl-only` export condition is a
bundler feature and does not apply to CDN loading.

### 2.7 deck.gl v10 readiness

Nothing to do until a prerelease exists. The announced changes (luma.gl v10, loaders.gl v5, binary
data pipelines) touch two places in the client: `resolveBinaryAttributes` / `decodeBinaryValue`
(the `@@binary` transport) and the resolution cache added in 1.11.0. Both are self-contained. Keep
`@deck.gl/widgets` pinned to exactly the deck.gl version, as now, and keep the `_`-prefixed class
fallback (`resolveWidgetClass`): v10 will likely move more classes in or out of "experimental".

---

## 3. Suggested order

1. **2.1 and 2.5's deprecations** — small, safe, and 2.1 fixes a memory leak that the e2e suite feels.
2. **2.2** — one-line switch plus a globe/terrain check in the browser; unlocks deck.gl layers on the
   globe and `before_id` for deck.gl layers.
3. **2.3** — the widget event plumbing is the biggest usability gain for app authors.
4. **2.5's headless demo test** — cheap insurance for the demo.
5. **2.4**, then **2.6** as time allows.
