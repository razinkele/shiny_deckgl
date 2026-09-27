# shiny_deckgl 1.12.2 — in-depth review (2026-09-28)

Four independent reviewers (demo app, JS runtime, Python API, tests/CI/packaging) read the
code at `21b66d6` (v1.12.2) and returned evidence-backed findings; each blocker/major below was
re-verified against the source before it was fixed. Prior reviews:
`docs/2026-09-26-codebase-review.md`, `docs/2026-09-27-dependency-review.md`.

## Status

**Fixed** (branch `fix/review-2026-09-28`): every blocker and major — A1–A4, D1–D7, J1–J3, T1–T2,
T5–T8. **Deferred** (minor, listed in section 5 with the suggested fix): everything else.

---

## 1. Python API

| # | Sev | Finding | Fix |
|---|---|---|---|
| A1 | major | `resend_last_update()` replayed only the last `update()` call's *delta*: widgets/effects/views sent by an earlier call, later `partial_update()` patches, `set_layer_visibility()` toggles and `set_widgets()` were all lost on a reconnect, and a replayed `viewState` re-ran `flyTo`. | Every state-changing call merges into one per-session snapshot (`_record_full_update/_record_layer_patches/_record_visibility/_record_widgets`); no `viewState`. Tests: `TestResendReplaysSessionState`. |
| A2 | major | `docs/api_reference.md` documented `deck_legend_control()`, which never shipped (TOC, example, note, section). | Replaced with a pointer to `layer_legend_widget()`. |
| A3 | major | `CoordinateSystem.DEFAULT = -1` on a `str` Enum became the string `"-1"`, which deck.gl 9 rejects at draw time — reachable via the documented `COORDINATE_SYSTEM.DEFAULT`. | `DEFAULT = "default"`, a true alias of `IDENTITY`. Test: `TestCoordinateSystemDefaultIsIdentity`. |
| A4 | major | `layer_legend_widget` missing from `shiny_deckgl.__all__`. | Added; test asserts `widgets.__all__ ⊆ shiny_deckgl.__all__`. |
| A5 | minor | Constructor `controls=` not validated (only `add_control`/`set_controls` are). | Deferred: share a `_normalise_controls()`. |
| A6 | minor | `map_options="antialias"` gives an opaque `dict()` error. | Deferred: `isinstance(map_options, dict)` check. |
| A7 | minor | `update()` does not run `_serialise_data` on layer `data` while `partial_update()` does; a raw DataFrame in a layer dict kills the session inside an Effect. | Deferred: same shallow-copy pass in `update()`. |
| A8 | minor | `before_id`, widget `placement`, `scrollbar_widget(orientation)`, `popup_widget(position)` unvalidated. | Deferred: shared `_widget()` builder validating against `WidgetPlacement`. |
| A9–A13 | minor | `api_reference.md` a minor behind: 1.10.0/6.7.0 strings, `MapboxOverlay`, deck.gl-8 integer coordinate values, no `map_options`, no `legend_visibility/widget_event/reconnected_input_id`, `update()` deck-level kwargs, `resend_last_update`, `to_json(session=)`. Stale counts in `components.py` docstring ("22 helpers"). | Deferred (docs pass). |
| A14–A16 | minor | `_types.py` drift (`coordinateSystem: int`, duplicate `ControlPosition`/`WidgetPlacement`), missing annotations (`layer(data)`, `add_geodataframe(gdf)`), `MISSING_COLOR` referenced but not exported. | Deferred. |

## 2. Demo application

| # | Sev | Finding | Fix |
|---|---|---|---|
| D1 | major | Spatial query always logged "0 feature(s)": the client sends `{requestId, features}`, the handler expected a list. | Reads `features`; lists the layer ids. Test: `test_spatial_query_counts_features_from_the_dict_payload`. |
| D2 | major | Seven readback cards (click/hover/viewport/drag ×2, ML drag, Time&Space info) were blank until the first event: reading a never-set input raises `SilentException`, so the `is None` placeholder branch never ran. | `_input_or_none()` checks `Value.is_set()` first. Test: `test_readback_outputs_show_placeholder_before_first_event` (5 outputs). |
| D3 | major | Layers tab flew the camera back to the Baltic overview on every switch flip and every legend tick. | Flies only when the view class changes (`_gl_last_view`). |
| D4 | major | Seal tab: toggling any of five overlays resent the whole trips payload (MBs). | Overlays always built with `visible=`; a `_seal_overlays` effect uses `set_layer_visibility()`. |
| D5 | major | HexSim tab: speed/trail sliders resent the mesh and all trips. | `_hexfish_anim_params` patches the two props with `partial_update()`. |
| D6 | major | Time & Space SST scale was fitted to the cells in view, so a cell changed colour when you panned. | Bins on a fixed 0–20 °C domain (`_TS_TEMP_DOMAIN`). |
| D7 | major | No 1.12 feature was visible in the demo. | Added: "Widget events" card (Widgets tab), `zoom_widget(zoom_step=0.5)`, `session.allow_reconnect()` + `_gl_resync` on the gallery map, `map_options` Baltic fence on the MapLibre tab. Still not shown: `before_id` (needs an interleaved map), the new toggle/selector/icon widgets, `pickable="3d"`. |
| D8–D22 | minor | Export status set inside the download generator; export serialises all 35 layers; LT bathymetry switch dead in an installed wheel; duplicate startup updates (`_wg_init`, `_ml_controls_rebuild`, Advanced ×3); Advanced sliders resend every layer; `v1_ports` drawn with both switches off; "Query at Map Center" queries pixel (400,300); Widgets-tab legend without a `legend_visibility` handler; FPS `StatsWidget` listed as experimental; range-mode tooltip "Bin 37/213"; HexSim controls dead without the mesh; duplicate drag output; stale counts ("33 helpers" vs 35, "5 experimental", `app.py` "10 tabs/24 helpers/16 widgets"); 3-D sliders resend data; context-menu items inert. | Deferred. |

## 3. JS runtime (`deckgl-init.js`, `styles.css`)

The reviewer confirmed from the 9.4.0 sources that `MapLibreOverlay` mounts deck's container inside
`.maplibregl-ctrl-top-left` exactly as `MapboxOverlay` did, so the 1.12.2 legend `pointer-events`
bug was the only pointer-events casualty of the switch and no other runtime element sits in a
control container. `attachWidgetEvents`, `mergeMapOptions`, the reconnect branch, `pickable:'3d'`,
`deferMessage` coalescing, `onViewStateChange` forwarding and the `disposeMap` lifecycle were verified
correct. No `sanitizeHtml` / `isSafeAccessorExpr` bypass was found (do not loosen).

| # | Sev | Finding | Fix |
|---|---|---|---|
| J1 | major | `set_style(diff=True)` fires no `style.load`, so the style guard stayed up for 30 s and every `whenStyleReady()` caller (add_source, add_maplibre_layer, popups, controls…) stalled. | `settleDiffStyle()`: settles synchronously for a style object, on `styledata` for a URL; idempotent. Node tests. |
| J2 | major (latent) | deck.gl 9.4 throws on every render for a MapLibre projection other than `mercator`/`globe` (zoom expression, `vertical-perspective`). | `normaliseProjection()` on every `style.load` maps to the nearest preset with a warning. Node tests. |
| J3 | major (UX, pre-existing) | deck `ZoomWidget`/`CompassWidget` (default `top-right`) sit under our default MapLibre `NavigationControl`, which paints over them and takes their clicks. | `dropImplicitNavigation()`: when the navigation control is only our default and a Zoom/Compass widget is set, the control is removed. Explicit `controls=[navigation_control()]` is untouched. Node tests. |
| J4 | minor | MapLibre markers/popups can paint under the deck canvas (needs browser check). | Deferred: `.maplibregl-marker, .maplibregl-popup { z-index: 3 }`. |
| J5 | minor | Interleaved layer groups are created only once `isStyleLoaded()`; an `update()` during tile load draws on top until the next `styledata`. | Deferred (browser check). |
| J6 | minor | `mousemove` tooltip-dismiss does a second GPU pick per move and throws before deck initialises. | Deferred: use deck `onHover` with `!info.object`. |
| J7 | minor | `disposeMap` leaves the 30 s style timer and the legend refresh timer alive. | Deferred. |
| J8 | minor | `_svgAtlasCache` unbounded and global. | Deferred: cap / per-instance. |
| J9 | minor | `data-map-options` can override `transformRequest`/`preserveDrawingBuffer`. | Deferred: pin those two as well. |
| J10 | minor | `useDevicePixels` silently dropped in interleaved mode. | Deferred: warn. |
| J11 | minor | `TimelineWidget` class field clobbers `widget.id`, so two timelines dedupe into one in deck's `WidgetManager` (events already use `props.id`). | Deferred: `if (props.id != null && w.id !== props.id) w.id = props.id` in `buildWidgets`. |
| J12 | minor | Double `shiny:connected` binding could count a same-tick second dispatch as a reconnect; hidden-tab maps never report `_reconnected`. | Deferred. |
| J13 | minor | `deck_export_image` uses private `overlay._deck`; `overlay.getCanvas()` is public in 9.4. | Deferred. |

## 4. Tests, CI, packaging

| # | Sev | Finding | Fix |
|---|---|---|---|
| T1 | **blocker** | The browser suite (14 files, 94 tests — including the 1.12.2 regression guard) never ran in CI: the `dev` extra had no Playwright and every browser file `importorskip`s it. `pyproject.toml` even claimed "no test is skipped". | `browser` extra; `dev` includes `playwright`; CI `browser` job installs Chromium and runs the modules one file at a time, the full demo last and alone; `unit` job runs `-m "not browser"` on 3.11–3.13 with Node pinned. |
| T2 | major | Browser skip gates swallowed *any* launch failure, so a broken Playwright install would go green. | `SHINY_DECKGL_REQUIRE_BROWSER=1` (set in CI) turns launch failure into a failure (`_browser_unavailable()` in `_e2e_app.py`, `test_sanitizer_browser.py`). |
| T3 | major | All 46 `deck_*` message handlers are anonymous closures the Node harness cannot extract; ~40 have no runtime test. | Deferred (name them `onDeckFlyTo` etc.). The three helpers added for J1–J3 are named and Node-tested. |
| T4 | major | Tooltip template path (`interpolateTemplate`, `escapeHtml`) has no JS test. | Deferred: one `@requires_node` test. |
| T5 | major | `_chromium_available()` launched Chromium at *collection* time in two modules. | Import check only; launch failures surface in the fixture. |
| T6 | major | No browser file carried `pytest.mark.browser`, so a marker split was impossible. | `pytestmark` in all 12 files; `addopts = "-ra --strict-markers"`. |
| T7 | major | Release workflows publish without running tests. | `pypi-publish` runs the unit suite before building; wheel check extended to `styles.css` and `helcom_mpa.geojson`. |
| T8 | major | `test_no_page_errors` passed trivially (3 s after DOMContentLoaded, before init). | Asserts on the errors captured by the shared page fixture, which waits for the first `deck_update`. |
| T9–T25 | minor | Node unpinned (fixed alongside T1); skips invisible (`-ra`, fixed); no offline detection for CDN bundles; fixed sleeps; order-dependent legend test; `tests/_hexsim_*.py` not gitignored; brittle count assertions; triplicated widget tests in `test_basic.py`; PEP 639 license form; 3.10 not in the matrix; conda recipe prose says 6.7.0; README "not on PyPI yet"; CHANGELOG mojibake/dates below 1.0.1. | Deferred. |

## 5. Recommended next steps (deferred items, in value order)

1. Name the `deck_*` handlers so the Node harness can reach them (T3) and add the tooltip-template test (T4).
2. Docs pass on `docs/api_reference.md` (A9–A13) and the demo's stale counts (D20).
3. `_widget()` builder with placement validation (A8) + `_normalise_controls()` (A5) + `map_options` type check (A6) + `_serialise_data` in `update()` (A7).
4. Runtime hygiene: J6, J7, J8, J9, J11 are each a few lines.
5. Demo: show `before_id` (needs an interleaved map), the toggle/selector/icon widgets and `pickable="3d"`; D8–D19 perf/UX items.
6. Packaging: PEP 639 license form, 3.10 in the matrix, CHANGELOG encoding.
