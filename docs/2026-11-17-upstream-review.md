# Upstream status review — 2026-11-17

shiny_deckgl 1.14.0 against upstream py-shiny, deck.gl and MapLibre GL JS.
Primary sources: PyPI/npm registries, upstream changelogs and upgrade guides, the GitHub security advisory.

## Versions

| Dependency | Pinned | Latest upstream |
|---|---|---|
| shiny (runtime floor) | `>=1.6.3` | 1.9.0 (2026-10-29); main is unreleased: drops Py 3.10, adds `reactive.debounce`/`throttle`, renames `invalidate_later(delay=)` → `delay_secs` |
| deck.gl + widgets | 9.4.1 (uncommitted, was 9.4.0) | 9.4.1; 10.0.0-alpha.1 (2026-11-12) |
| maplibre-gl, served | 6.18.0 (uncommitted, was 6.11.2) | 6.19.0 (2026-11-17) |
| maplibre-gl, export | 5.24.0 | 5.24.1 (security fix) |
| @mapbox/mapbox-gl-draw | 1.5.1 | 1.5.2 |
| @watergis/maplibre-gl-legend | 2.0.7 | 4.1.0 (3.0 dropped the UMD build and v5 support) |
| maplibre-gl-opacity / h3-js | 1.8.0 / 4.5.0 | current |

## Pending CDN bump (9.4.1 / 6.18.0)

Changelogs show no breaking changes for the APIs we use. `style._loaded` still exists, and deck's MapLibre module uses only public map API.
Worker start-up changed in 6.13 and 6.17, so run the browser suite before committing (`test_maplibre_v6`, `test_e2e_context_loss`, `test_e2e_globe`, plus a strict-CSP check).
Problems in the diff itself:
- `README.md:361`: the blank line after the heading was lost, and "no UMD" became `noUMD`.
- Stale pins the bump missed: `conda.recipe/meta.yaml:54-55` (9.4.0 / 6.7.0) and `.github/copilot-instructions.md:4-5`.

## Findings

### P1
1. **The export pin MapLibre 5.24.0 has a critical XSS advisory.** GHSA-jrc7-96c5-q579 / CVE-2026-85061 (`DOM.sanitize()` bypass) affects `< 5.24.1`. Bump `MAPLIBRE_EXPORT_VERSION` in `_cdn.py:11`, the tests (`tests/test_basic.py:615,1034`) and `README.md:377`.
2. **The demo breaks on the declared Shiny floor.** `_app_server.py:1095` uses `render.download_button` (added in 1.7.0) without a guard.
3. **The `shiny>=1.6.3` floor is untested and admits a Shiny with the bookmark path-traversal fixed in 1.6.4.** Our own `enable_bookmarking()` is already gated at 1.6.4 (`map_widget.py:834`), so this is a reason to raise the floor, not a hole in shiny_deckgl. On <1.6.4, `tests/test_bookmarking.py` fails with no skip. CI only runs latest + 1.8.0, although its comment says the floor is covered.
   → Raise the floor to `shiny>=1.7.0` in pyproject, `conda.recipe/meta.yaml` and README, and add a CI job pinned to the floor.

### P2
1. **Python 3.10.** Upstream main requires 3.11+, but we declare 3.10 and CI tests only 3.11–3.13. Either bump `requires-python` or add a 3.10 job, and add 3.14 to CI.
2. **The local `shiny` env is stale:** Shiny 1.6.0 (confirmed 2026-11-17, though the 2026-11-03 notes said 1.8), no pytest-asyncio, editable metadata says 1.9.1. Rebuild it on 1.9, then move the dev/test extras to `shiny>=1.9.0`.
3. **deck.gl 9.4.1 draws `cartesian` z taller below zoom 12** (deck.gl #10790: upstream gives ~1.4x at 46° and 2x at 60°; ~1.8x at Klaipėda is derived from that, not stated upstream). Check the demo `gl_terrain` exaggeration (`_app_server.py:2581-2590`) and add a CHANGELOG note.
4. **`path_style_extension()` lags 9.4** (`extensions.py:154-174`):
   - it emits the deprecated `highPrecisionDash`;
   - it never emits `offset`, so `getOffset` has no effect;
   - the docstring gives the wrong `dashMode`/`dashUnits` values.
   → Add `offset=` and `dash_mode=`, and map `high_precision` to `dashMode: 'path'` with a deprecation warning.
5. **Private Shiny import with a silent fallback:** `map_widget.py:91` imports `shiny._namespaces.resolve_id`. Switch to the public `shiny.module.resolve_id`.
6. **The legend plugin is frozen at 2.0.7:** 3.x+ ships no UMD build. Move it to ESM together with P3-1.

### P3
1. **The v5 export pin may now be removable:** MapLibre 6.17 fixed `file://` loading (#8912). Spike an ESM export template and a `file://` browser test.
2. **deck.gl v10 alpha touchpoints.** Add an opt-in CI job against the alpha.
   - `COORDINATE_SYSTEM` becomes CRS strings: `enums.py:115-138`, `deckgl-init.js:1503-1520`.
   - A5 v1 changes cell indexes.
   - GlobeView `resolution` defaults to 0.
   - Experimental `_`-prefixed classes may be renamed.
3. **Small bumps:** mapbox-gl-draw 1.5.2 now. MapLibre 6.19.0 after a patch release; it adds `setTrustedTypesPolicy`, which matters for CSP.
4. **Coverage gaps:** widget themes (`LightTheme`/`DarkTheme`/glass), `_CameraLight`, 9.4 `ViewLayout`, widget tooltips. Every other 9.4.1 layer, extension and widget is wrapped.
5. **Adopt `reactive.debounce`/`throttle` once released;** it would replace the hand-rolled debounce in `_viewport.py:163-180`.
6. **Still open from earlier reviews:**
   - sidebar `role=`/`aria_label` (1.9 doc, item 6);
   - `ui.page_html` export, demo toast/offcanvas/toolbar and `shiny.otel` (1.8 doc, items 8–10).
   - `testing.py:36` imports the private `UiBase` and falls back to a stub on failure. Add a test that the real base is used.

No upstream deprecations are hit apart from `highPrecisionDash`. The JS's Shiny API use (`setInputValue`, `addCustomMessageHandler`, `makeRequest`) is unchanged in 1.9.
