# Review fixes — 2026-09-06

Resolution of the 25 findings in [`2026-09-06-codebase-review.md`](2026-09-06-codebase-review.md).
All fixed test-first: a failing test written and observed RED before each change.

**Suite: 1737 → 1900 passing, 12 skipped, 0 failures.** New tests in
`tests/test_review_2026_09.py`, `tests/test_maplibre_v6.py` and
`tests/test_widgets_resolve.py`; JS harness in `tests/_js_harness.py`.
Released as **1.10.0**.

## Prerequisite: the suite was testing the wrong code

`pytest` imported `site-packages/shiny_deckgl` **1.9.2**, not `src/` (1.9.4), so
11 tests "failed" that were really passing against stale code. Fixed with
`pythonpath = ["src"]` in `[tool.pytest.ini_options]`.

> The `shiny_deckgl-demo` CLI and the conda package are still **1.9.2**.
> **None of these fixes reach the demo until you rebuild and reinstall the
> conda package** — see the release notes in `CHANGELOG.md` for 1.10.0.

## Fixed

| # | Site | Fix |
|---|---|---|
| 1 | `_app_server.py` | `ui` (22 uses) and `MapWidget` were never imported — every preset button, HTML export and JSON round-trip raised `NameError` inside a `reactive.Effect`, closing the whole session. Imports added. |
| 2 | `deckgl-init.js:82` | `javascript:` filter was a substring regex; `java<TAB>script:` executed. Replaced with `isDangerousUri()` — strips TAB/LF/CR and leading C0 controls as the URL parser does, then compares the scheme exactly. Also blocks `vbscript:`. |
| 3 | `map_widget.py` | `update()`/`partial_update()` bypassed `json_safe()`; NaN/inf reached the websocket as invalid JSON. |
| 4 | `map_widget.py` | `to_html()` interpolated `view_state` into HTML attributes unescaped while neighbouring attributes were escaped. |
| 5 | `deckgl-init.js` | `deck_export_image` captured only the MapLibre canvas, dropping every deck.gl layer outside interleaved mode. Now composites both canvases. |
| 6 | `_timeline.py` | `_auto_advance` read `input.step()` reactively and also wrote it, so it invalidated itself and cancelled its own `invalidate_later` — `interval_ms` never governed cadence. Read is now isolated. |
| 7 | `_viewport.py` | The fallback branch re-armed `invalidate_later(1.0)` unconditionally: an untouched map re-pushed every layer once a second, forever. Now bounded (`_should_repoll`, 10 attempts). |
| 8 | `_app_server.py` | `_v1_layers` was the only one of 9 `adv_widget` writers not threading through `_adv_layers`, so it and the 3-D effects wiped each other. |
| 9 | `_demo_data.py` | `make_sea_temperature_grid` drew noise from a sequential RNG *after* the `continue` that skips filtered cells, so a cell's temperature depended on the viewport. Now seeded by position, matching the comment's claim. |
| 10 | `effects.py` / `deckgl-init.js` | `new PostProcessEffect(spec)` — deck.gl expects `(module, props)`. The throw killed the entire effects array. Now resolves the module and drops the single effect with a warning if absent. |
| 11 | `deckgl-init.js` | `@@=` whitelist rejected every non-trivial expression **and left the raw string in `layerProps`**, which deck.gl coerces to a constant NaN. 3 of the package's own 31 accessors were dead, including the documented `d.depth_m * 5`. |
| 12 | `deckgl-init.js` | `buildViews` used a bare `deck[typeName]`; deck.gl 9.x exports `_GlobeView`. Underscore fallback added. |
| 13 | `enums.py` / `deckgl-init.js` | 13 easings published, 4 implemented; the other 9 silently animated linearly. All 13 implemented, with a parity test in both directions. |
| 14 | `colors.py` | `color_quantiles` binned with `v <= break` against upper-group first values, pushing every boundary value down a bin and making the top colour unreachable. |
| 15 | `_sealmove.py` | `normalize_rows` left zero rows all-zero, so `rng.choice(p=...)` raised. Now an absorbing self-loop. |
| 16 | `layers.py` | `_maybe_encode` imported numpy unconditionally, crashing `custom_geometry()` on numpy-less installs despite lists being documented input. |
| 17 | `_demo_data.py` | `make_lithuanian_bathymetry_data` used four `.parent` hops, landing above the repo root; `bathy.asc` was never found. |
| 18 | `_demo_data.py` | The IBM added an isotropic **degree** step to both axes, moving seals ~1.8× further north-south than east-west. Latitude component now scaled by `cos(lat)`. |
| 19 | `deckgl-init.js` | `deck_update` awaited the SVG-atlas preload with no generation guard; a slower earlier update could resolve last and paint stale layers. |
| 20 | `deckgl-init.js` | Layer updates resurrected an explicitly paused trips animation. |
| 21 | `_app_widgets.py` / `map_widget.py` | Demo widgets are module singletons; `set_style` mutated the shared `style`, leaking one visitor's basemap into every other session. Style is now per-session (`current_style(session)`, `to_html(session=)`). |
| 22 | `_app_server.py` | `_wg_init` read all 20 `wg_*` inputs reactively, so the "init" effect duplicated `_wg_update_map` on every toggle. |
| — | **bonus** | `np` and `Session` were undefined in string annotations (not in the review). Fixed via `TYPE_CHECKING` imports; a `ruff --select F821` test now guards the whole package. |

## Found afterwards, by putting a browser on it

Neither of these is in the 25 findings. Both were invisible to static review —
each side of the contract looked internally consistent, and only a running
browser rejects the value. Both were found within minutes of the first
Playwright run.

### `coordinateSystem` used deck.gl 8's integers

deck.gl 9 identifies coordinate systems by string (`"lnglat"`,
`"meter-offsets"`, …) and rejects the old integers at draw time with
`Invalid coordinateSystem: 1`. `CoordinateSystem` still emitted integers, and
`scatterplot_layer()` defaults to `LNGLAT` — so **the default layer silently
failed to render**, along with ~60 other emission sites.

The enum now carries deck.gl 9's strings; the JS client maps the legacy
integers across, so apps that hardcoded `1` keep working at runtime. Verified in
Chromium on both delivery paths: six layer types (including `meter-offsets`)
in a standalone export, and the full demo over a live Shiny websocket.

**API note:** the enum changed from `int`-valued to `str`-valued, so Python-side
comparisons such as `cs == 1` no longer hold.

### Maps never initialised on the first tab

`deckgl-init.js` waited for readiness with
`document.addEventListener('shiny:connected', …)`. Shiny dispatches that event
through jQuery — `$(document).trigger({type: "shiny:connected"})` — and a
jQuery-triggered event **never reaches a native listener**. Demonstrated
directly: after `jQuery(document).trigger(...)` the jQuery handler count is 1
and the native handler count is 0.

So the initial-load gate never ran. Maps came up only when their tab was
switched to, because `shown.bs.tab` is a genuine DOM event. The handler is now
registered through jQuery when it is present, keeping the native listener for
standalone hosts, guarded against firing twice.

This is long-standing, not a recent regression: the oldest Shiny available
locally (1.4.0) already dispatched through jQuery, as does 1.7.0.

### Six of eighteen widget helpers rendered nothing

`buildWidgets` resolved a class as `deck[name] || deck['_' + name]`: it could
*add* a leading underscore but never *strip* one. deck.gl has since promoted
several widgets from experimental to stable (`_InfoWidget` → `InfoWidget`), so
every helper still emitting the underscored name silently resolved to nothing
and was dropped with a console warning.

Restored: `context_menu_widget`, `info_widget`, `loading_widget`,
`theme_widget`. Still unavailable, because deck.gl ships no such class in any
9.x release: `fps_widget` and `view_selector_widget` — their docstrings now say
so, and `tests/test_widgets_resolve.py` pins that list so a future deck.gl
release adding them is noticed.

Checked against deck.gl 9.3.6, 9.3.11 and 9.4.0, which export an identical
widget set: long-standing, not a version regression.

### Text labels could not render non-ASCII characters

`TextLayer` used deck.gl's default ASCII font atlas, so "Klaipėda" logged
`Missing character: ė` and rendered a gap — a visible defect on a Lithuanian
project. `characterSet="auto"` now builds the atlas from the labels actually
supplied, so any language works. The standalone-export test renders that label,
and the existing no-console-errors assertion catches a regression.

### The demo raised an unhandled error on every page load

It always built a `Tile3DLayer` pointing at Google's 3D Tiles endpoint, which
answers 403 without an API key. deck.gl fetches a layer's `data` even when
`visible=False`, so the toggle defaulting to off did not help. The layer is now
built only while its toggle is on, and the call site documents the key
requirement.

Also fixed: `grid_cell_layer()` defaulted to `getColor`, deprecated on
`GridCellLayer` in deck.gl 9 and slated for removal; the default is now
`getFillColor`, with an explicit `getColor` still passed through.

### What the demo console looks like now

One benign warning remains — `luma.gl: Binding weightsTexture not set` — which
is luma.gl complaining about deck.gl's own `HeatmapLayer` shader module, not
about anything this package emits. No errors, no unhandled page errors.

## Decisions you should confirm

- **`normalize_rows`: zero row → absorbing self-loop, not uniform.** The only
  caller is `simulate_IHTR`'s Markov transition matrix, where uniform would
  teleport agents to arbitrary haulout clusters. Non-square matrices still fall
  back to uniform. **Confirm the absorbing-state reading is what you want.**
- **`color_quantiles` binning changed for every caller** — demo colours shift
  slightly. Correct, but visible.
- **The `@@=` language widened** from property chains to arithmetic /
  comparison / ternary over `d`. This is a security surface (`new Function`).
  15 attack strings are tested and rejected — calls, assignment, arrows,
  template literals, and any identifier other than `d`.
- **Three existing tests were updated** because they encoded the buggy
  behaviour: `test_sealmove.py` and `test_error_handling.py` (zero row stays
  zero) and `test_basic.py` ×2 (`set_style` mutates the shared attribute).
- **CI now installs `.[dev]`** — which pulls in `geopandas`. Split into a
  lighter `test` extra if that's too heavy.

## Known limits

- **`sanitizeHtml` itself is not run under Node** (it needs `DOMParser`).
  `isDangerousUri` is behaviour-tested; its wiring into `sanitizeHtml` is
  asserted by source inspection only.
- **`data:` URIs are still allowed** in `href`. `data:text/html` is a real
  vector; left in scope-check territory rather than changed silently.
- **Post-processing effects still do not render** — `@luma.gl/effects` is not
  shipped. The fix stops one bad effect destroying the whole effects array;
  actually rendering them is a feature, not a bug fix.
- **`deck_export_image` compositing is tested with fake canvases**, not a real
  browser: exercising it needs a `deck_export_image` round trip, which the
  browser tests do not drive. Everything else here *is* browser-verified — the
  Playwright MCP server was unavailable, but the Playwright Python library and
  Chromium are installed locally and were used throughout. The deck canvas is
  located via `overlay._deck || overlay.deck`, an internal property.
- **The end-to-end suite is memory-bound on a 16 GB machine.** Running the whole
  file at once gets killed; per-class runs pass. 18 of 20 passed on the one
  complete run, and both failures were test bugs, since fixed.
