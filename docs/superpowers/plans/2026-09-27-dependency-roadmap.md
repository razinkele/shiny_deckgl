# Dependency Roadmap (1.12.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring shiny_deckgl up to the current MapLibre, deck.gl 9.4 and Shiny 1.8 feature set: MapLibre 6.11.2, the `MapLibreOverlay` integration, current widgets with events reported as Shiny inputs, 3-D picking, MapLibre map options, reconnect resync, and a headless demo test — released as 1.12.0.

**Architecture:** The package is a Python `MapWidget` that sends custom messages to one browser runtime, `src/shiny_deckgl/resources/deckgl-init.js`, which builds deck.gl layers/widgets on a MapLibre map. Every task changes the Python spec builders (`widgets.py`, `layers.py`, `map_widget.py`), the runtime, or both, and is verified by (a) Python unit tests with the `_FakeSession` double in `tests/conftest.py`, (b) Node tests that extract single runtime functions with `tests/_js_harness.py` (it extracts only top-level `function name(` and single-line or bracketed top-level `var/const/let name =` declarations; the code runs under `node --input-type=module`, i.e. strict mode, so every global a function touches must be extracted or stubbed), and (c) Playwright browser tests using the small apps in `tests/_apps/` via `tests/_e2e_app.py`.

**Tech Stack:** Python ≥ 3.10, Shiny for Python (runtime floor 1.6.3; 1.8.0 installed in the `shiny` env and required by the `test`/`dev` extras), deck.gl 9.4.0 + `@deck.gl/widgets` 9.4.0 (CDN), MapLibre GL JS 6.x (CDN, ESM), pytest, Node 22 for JS unit tests, Playwright + Chromium for browser tests. Python runs through `micromamba run -n shiny python`; never pip, never a venv.

**Spec:** `docs/2026-09-27-dependency-review.md` (sections 2.1–2.7, order in section 3).

**Review:** this plan was reviewed by a four-lens workflow (codebase fit, upstream APIs, test soundness, spec coverage) with per-finding adversarial verification; 30 findings were confirmed and folded in. The material changes from the first draft: Task 3 seeds inputs (the test server seeds none) and uses `is_ok`/`error` as properties; Task 4's rationale is corrected (`MapboxOverlay` 9.4 already handles MapLibre's globe); Task 5 keeps `extensions=`; Tasks 6–7 update the existing widget tests and use the real `PopupWidget`/`SelectorWidget` props; Task 8 reads the widget's real `id`; Task 9 grew a `map_options` pass-through; the WebGPU task was dropped (see "Deferred").

## Global Constraints

- Runtime dependency floor stays `shiny>=1.6.3`; only the `test` and `dev` extras add `shiny>=1.8.0`.
- deck.gl and `@deck.gl/widgets` stay pinned to exactly the same version (`DECKGL_VERSION = "9.4.0"`).
- The `to_html()` export keeps MapLibre `MAPLIBRE_EXPORT_VERSION = "5.24.0"` (v6's module worker dies on `file://`).
- CDN versions are single-sourced in `src/shiny_deckgl/_cdn.py`; README and `.github/copilot-instructions.md` must state the same numbers. Historical release notes (README "v1.10.0" row, CHANGELOG) keep their original numbers.
- The `@@=` accessor whitelist in `isSafeAccessorExpr` is not loosened by any task.
- Every Shiny input the runtime emits has a `MapWidget.<name>_input_id` property returning `f"{self._bare_id}_<suffix>"`.
- Run the unit suite as `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main([...]); sys.stdout.flush(); os._exit(0)"` (the `micromamba run` wrapper hangs on a non-zero child exit). Exclude `tests/test_e2e_playwright.py` and `tests/test_benchmarks.py` from full runs; run browser modules one file at a time (16 GB machine). Ports used by existing `tests/_apps`: 18766–18775; new apps take 18776+.
- Public defaults do not change silently: `zoom_widget()` keeps `placement="top-right"`; deprecations warn for at least one minor release before removal.
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Deferred (from spec 2.4 and 2.6), with reasons

- **WebGPU opt-in (spec 2.6):** the pinned umbrella bundle `deck.gl@9.4.0/dist.min.js` ships no WebGPU adapter, so `deviceProps: {type: 'webgpu'}` makes `Deck` throw "No matching device found" instead of rendering. Supporting it means loading `@luma.gl/webgpu`'s browser bundle and passing its adapter, which is a new CDN dependency for an experimental backend. Not in 1.12.0; noted in the changelog.
- **Demo `antialiasing` toggle (spec 2.4):** demo-only; the library part (`antialiasing` passes through) is documented in Task 9.

## Review Focus

1. **Widget events for a widget whose `id` the app did not set.** deck.gl gives each class its own default id (`"timeline"`, `"toggle"`, …), so two of a kind still report the same id. Test (Task 8): a spec without `id` reports the class's default id, taken from the constructed widget, and the docs tell authors to set `id=` when they add two of a kind.
2. **`pickable='3d'` on a raster layer.** `TileLayer`/`BitmapLayer` are skipped by the pick-handler setup; `'3d'` must not crash them and must not attach pick handlers. Test (Task 9): a `TileLayer` with `pickable='3d'` keeps `pickable === '3d'` and gets no `onClick`.
3. **A reconnect before the first `update()`.** `resend_last_update()` with nothing recorded must be a no-op returning `False`, not an error. Test (Task 10).
4. **A later `set_widgets()` must not silently detach the event shim.** deck.gl's `Widget.setProps` merges with `Object.assign(this.props, props)`; the shim lives on the instance's `props`, so it survives unless the new spec carries the same callback key. Test (Task 8): after a merge that does not mention `onChange`, firing the event still reports.
5. **`before_id` on a layer while not interleaved.** deck.gl ignores `beforeId` in overlaid mode; the prop must still pass through unchanged so the same layer spec works in both modes. Test (Task 5).

---

### Task 1: MapLibre 6.7.0 → 6.11.2 (edits already applied in the working tree; verify and commit)

**Files (already modified, uncommitted):**
- `src/shiny_deckgl/_cdn.py` (`MAPLIBRE_VERSION = "6.11.2"`)
- `tests/test_basic.py` (the two former `maplibre-gl@6.7.0` assertions now derive from `MAPLIBRE_VERSION`)
- `README.md` lines 6, 39, 316, 318 and `.github/copilot-instructions.md` line 5 say 6.11.2; README line 168 (the v1.10.0 history row) deliberately still says 6.7.0

**Interfaces:**
- Produces: `MAPLIBRE_VERSION == "6.11.2"`; everything else unchanged.

- [ ] **Step 1: Confirm the tree state**

Run: `git status --short | grep -v "^??"` → exactly `_cdn.py`, `tests/test_basic.py`, `README.md`, `.github/copilot-instructions.md`, plus Task 2's `_app_ui.py`/`test_app_modules.py` (also already applied). `grep -n "6\.7\.0" README.md .github/copilot-instructions.md src tests` must show only README line 168.

- [ ] **Step 2: Unit check (already run once: 43 passed)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_basic.py','tests/test_maplibre_v6.py','-k','maplibre or cdn or head or MapLibre']); sys.stdout.flush(); os._exit(0)"`
Expected: pass.

- [ ] **Step 3: Browser modules one at a time (already run once, all green: 18 / 7 / 1 / 3 / 1 passed)**

`tests/test_maplibre_v6.py`, `tests/test_e2e_style_queue.py`, `tests/test_e2e_startup_style.py`, `tests/test_e2e_rerender.py`, `tests/test_e2e_playwright.py::TestNoJavaScriptErrors`. `test_e2e_style_queue.py` exercises `whenStyleReady`, which reads MapLibre's `style._loaded` (still present in 6.11.2's `src/style/style.ts`).

- [ ] **Step 4: Commit only Task 1's files**

```bash
git add src/shiny_deckgl/_cdn.py tests/test_basic.py README.md .github/copilot-instructions.md
git commit -m "deps: MapLibre GL JS 6.7.0 -> 6.11.2 (worker-tile leak, setStyle terrain crash, Map#once fix)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: Replace the deprecated `ui.output_text_verbatim()` in the demo (edits already applied; commit)

**Files (already modified, uncommitted):**
- `src/shiny_deckgl/_app_ui.py` (15 sites → `ui.output_code(`)
- `tests/test_app_modules.py` (`test_demo_ui_uses_no_deprecated_output_text_verbatim`, added at the end)

**Interfaces:**
- Produces: the demo UI uses `ui.output_code()`; server-side `@render.text` functions are unchanged (`output_code` renders text outputs verbatim in a `<pre>`; checked in the browser: `#gl_status` is a `PRE` with `white-space: pre`).

- [ ] **Step 1: Confirm the guard test passes and the app-module tests pass (already run: 34 passed)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_app_modules.py']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 2: Commit**

```bash
git add src/shiny_deckgl/_app_ui.py tests/test_app_modules.py
git commit -m "demo: ui.output_code() replaces the deprecated ui.output_text_verbatim()

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Headless demo test with `shiny.testserver`

Scheduled before the widget tasks (spec section 3 lists it fourth) on purpose: it is cheap insurance that later demo edits (Task 6) are run against.

**Files:**
- Modify: `pyproject.toml` (`test` and `dev` extras: add `"shiny>=1.8.0"`)
- Create: `tests/test_demo_headless.py`

**Interfaces:**
- Consumes: `shiny_deckgl.app.app`; `shiny.testserver.test_server(app, timeout_secs=)` → context-managed `TestServerSession` with `set_inputs(**kw)`, properties `is_ok: bool` and `error: str | None`, and `get_output(name)` → value object with `.status` (`"ok"`, `"silent"`, `"never-rendered"`, …) and `.value`.
- Facts established by probing the demo under the test server: it seeds **no** inputs (`get_input("pal_mode")` → `KeyError … Available: none`), so any effect that reads an input before it is set stops at `SilentException` and `is_ok` stays `True`; outputs whose effects never ran report `status == "never-rendered"`/`"silent"`. Custom messages (the map payloads) are discarded by the mock connection. Therefore: seed every input an effect reads, then assert on outputs; and the Layers tab cannot be driven this way, because its `_gl_init` reads its switches inside `reactive.isolate()` and never re-runs after seeding.
- Produces: a test module that proves the Colour Scales and Advanced tabs' reactive graph runs without errors under seeded inputs.

- [ ] **Step 1: Add the extra**

In `pyproject.toml`, in both the `test` and `dev` lists, add:

```toml
    "shiny>=1.8.0",      # shiny.testserver for tests/test_demo_headless.py
```

- [ ] **Step 2: Write the test**

`tests/test_demo_headless.py`:

```python
"""Run parts of the demo's server function in memory (Shiny >= 1.8.0).

shiny.testserver.test_server() runs the real reactive graph against a mock
connection: no browser, no websocket. It seeds no inputs and discards custom
messages (the map payloads), so each test seeds the inputs its effects read
and asserts on text outputs and on the absence of errors. The Layers tab is
not covered: its init effect reads its switches inside reactive.isolate() and
never re-runs once inputs exist -- that tab stays with the Playwright suite.
"""
from __future__ import annotations

import pytest

pytest.importorskip("shiny.testserver")
from shiny.testserver import test_server  # noqa: E402

from shiny_deckgl.app import app  # noqa: E402

COLOUR_INPUTS = {"pal_name": "Viridis", "pal_mode": "bins", "pal_nbins": 6, "pal_layer": "scatter"}
ADVANCED_INPUTS = {
    "enable_lighting": False, "ambient": 1.0, "point_intensity": 1.0,
    "v1_brushing": False, "v1_brush_radius": 50000,
    "v1_data_filter": False, "v1_filter_range": (0, 100),
}


def test_demo_starts_without_errors():
    with test_server(app, timeout_secs=60) as s:
        assert s.is_ok, s.error


@pytest.mark.parametrize("mode", ["bins", "quantiles", "range"])
def test_colour_scales_mode(mode):
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**{**COLOUR_INPUTS, "pal_mode": mode})
        assert s.is_ok, s.error
        out = s.get_output("pal_stats")
        assert out.status == "ok"
        assert "Palette:    Viridis" in out.value
        for n in (3, 9):
            s.set_inputs(pal_nbins=n)
            assert s.is_ok, s.error
            assert f"Bins/stops: {n}" in s.get_output("pal_stats").value


@pytest.mark.parametrize("layer", ["columns", "scatter", "heatmap"])
def test_colour_scales_layer_types(layer):
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**{**COLOUR_INPUTS, "pal_layer": layer})
        assert s.is_ok, s.error
        assert s.get_output("pal_stats").status == "ok"


def test_advanced_tab_effects_survive_their_inputs():
    # The 2026-09-26 review's D2: an effect here once wiped the shared layer list.
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**ADVANCED_INPUTS)
        assert s.is_ok, s.error
        s.set_inputs(enable_lighting=True, ambient=0.5, point_intensity=2.0)
        assert s.is_ok, s.error
        assert "Lighting ON" in s.get_output("advanced_log").value
        s.set_inputs(v1_brushing=True, v1_brush_radius=80000)
        s.set_inputs(v1_data_filter=True, v1_filter_range=(10, 60))
        s.set_inputs(enable_lighting=False)
        assert s.is_ok, s.error
        assert "Lighting OFF" in s.get_output("advanced_log").value
```

If an output id above does not match the demo (`advanced_log`), read `_app_server.py` for the `@render.text` that renders `_advanced_log` and use its function name; do not drop the assertion.

- [ ] **Step 3: Run it; expect PASS (Shiny 1.8.0 is installed in the env)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','-rs','tests/test_demo_headless.py']); sys.stdout.flush(); os._exit(0)"`
Expected: all pass. A failing assertion here is a real demo bug: fix it in `_app_server.py` in this task and note it in the commit.

- [ ] **Step 4: Full unit suite on 1.8.0**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','--ignore=tests/test_e2e_playwright.py','--ignore=tests/test_benchmarks.py','tests']); sys.stdout.flush(); os._exit(0)"`
Expected: pass; watch for new `ShinyDeprecationWarning` lines and fix their sources.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_demo_headless.py src/shiny_deckgl/_app_server.py
git commit -m "test: run the demo's Colour Scales and Advanced tabs headlessly with shiny.testserver

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `MapboxOverlay` → `MapLibreOverlay`

**Files:**
- Modify: `src/shiny_deckgl/resources/deckgl-init.js` (the `new deck.MapboxOverlay({` call; the comment near line 617 that names MapboxOverlay)
- Create: `tests/_apps/globe_app.py`, `tests/test_e2e_globe.py`

**Interfaces:**
- Consumes: `deck.MapLibreOverlay` from the umbrella bundle `deck.gl@9.4.0/dist.min.js` (exported from its `index.d.ts`; props type `Omit<DeckProps, …> & {interleaved?: boolean}`, identical to `MapboxOverlay`'s).
- What actually changes (from deck.gl `modules/mapbox/src` vs `modules/maplibre/src`): `MapboxOverlay` 9.4 already reads MapLibre's `projection.type`, switches to `GlobeView` and centres the camera on terrain, so globe rendering is **not** the delta. `MapLibreOverlay` is the MapLibre-typed overlay deck.gl now recommends, with a native elevation / render-parameter path (`compatibility.ts`), a one-overlay-per-map guard, and interleaved layer groups by `beforeId` (`layer-group.ts`). The switch is a maintenance move onto the supported integration; the globe test below is a regression guard, expected to pass before and after.
- Produces: `mapInstances[id].overlay` is a `MapLibreOverlay`; `overlay._deck` is still where tests and the export read the `Deck` (internal in both classes).

- [ ] **Step 1: Write the browser test**

`tests/_apps/globe_app.py`:

```python
"""A deck.gl layer on a map that switches to globe projection."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer

m = MapWidget("gmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 3})

app_ui = ui.page_fluid(head_includes(), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [scatterplot_layer(
            "pts", [[21.1, 55.7]], getPosition="@@d", getRadius=200000,
            getFillColor=[255, 0, 0], pickable=True,
        )])


app = App(app_ui, server)
```

`tests/test_e2e_globe.py`:

```python
"""The overlay is deck.gl's MapLibre integration, and layers follow globe projection.

MapLibreOverlay is the integration deck.gl 9.4 recommends for MapLibre. The
globe test is a regression guard (MapboxOverlay 9.4 already handled it); the
instanceof test is what changes with the switch.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18776

_LAYER_PRESENT = """() => {
  const i = window.__deckgl_instances && window.__deckgl_instances.gmap;
  return !!(i && i.overlay._deck.props.layers.some(l => l.id === 'pts'));
}"""


@pytest.fixture(scope="module")
def page():
    with running_app("globe_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#gmap .maplibregl-canvas") as pg:
            pg.wait_for_function(_LAYER_PRESENT, timeout=30000)
            yield pg


def test_overlay_is_the_maplibre_integration(page):
    assert page.evaluate("() => typeof deck.MapLibreOverlay === 'function'")
    assert page.evaluate("() => window.__deckgl_instances.gmap.overlay instanceof deck.MapLibreOverlay")


def test_point_stays_on_its_location_in_globe_projection(page):
    page.evaluate("() => window.__deckgl_instances.gmap.map.setProjection({type: 'globe'})")
    page.wait_for_timeout(1500)
    got = page.evaluate("""() => {
      const i = window.__deckgl_instances.gmap;
      const dk = i.overlay._deck;
      const view = dk.getViewports()[0];
      const p = view.project([21.1, 55.7]);
      const info = dk.pickObject({x: p[0], y: p[1], radius: 8});
      return { projection: i.map.getProjection().type, picked: info ? info.layer.id : null };
    }""")
    assert got == {"projection": "globe", "picked": "pts"}
```

- [ ] **Step 2: Run it; expect `test_overlay_is_the_maplibre_integration` to FAIL and the globe test to PASS**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','--tb=short','tests/test_e2e_globe.py']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 3: Switch the class and the comment**

In `deckgl-init.js`:

```js
    const overlay = new deck.MapLibreOverlay({
```

and change the comment near line 617 from "Under MapboxOverlay, MapLibre does the panning and zooming" to "Under MapLibreOverlay, MapLibre does the panning and zooming".

- [ ] **Step 4: Run the globe test and the overlay-dependent browser tests, one file at a time; expect PASS**

`tests/test_e2e_globe.py`, `tests/test_e2e_frame_loop.py`, `tests/test_e2e_render_race.py`, `tests/test_e2e_trips.py`, `tests/test_maplibre_v6.py`, `tests/test_e2e_playwright.py::TestServedPathRendersRealLayers`.
If `overlay._deck` is undefined under `MapLibreOverlay`, replace every `overlay._deck` read in `deckgl-init.js` and the tests with `(overlay._deck || overlay.deck)`.

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/resources/deckgl-init.js tests/_apps/globe_app.py tests/test_e2e_globe.py
git commit -m "feat: integrate through deck.gl's MapLibreOverlay, the supported MapLibre integration

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `before_id` on deck.gl layers (interleaved mode)

**Files:**
- Modify: `src/shiny_deckgl/layers.py:94` (`layer()` signature, docstring, one `if`; module docstring)
- Test: `tests/test_basic.py` (new class), `tests/test_render_cache_js.py` (one Node test)

**Interfaces:**
- Consumes: deck.gl reads `layer.props.beforeId` in interleaved mode (`@deck.gl/maplibre` `layer-group.ts`).
- Produces: `layer(type, id, data=None, *, extensions=None, before_id: str | None = None, **kwargs) -> dict` emitting `"beforeId": before_id` when given. The existing `extensions` parameter and its body (`if extensions: … lyr["@@extensions"] = resolved`, lines ~135–147) stay exactly as they are. Every typed helper forwards `**kwargs` to `layer()`, so they all accept `before_id=`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_basic.py`:

```python
class TestLayerBeforeId:
    """before_id places a deck.gl layer under a MapLibre style layer (interleaved)."""

    def test_before_id_is_emitted_as_beforeId(self):
        from shiny_deckgl import scatterplot_layer
        lyr = scatterplot_layer("pts", [], before_id="waterway-label")
        assert lyr["beforeId"] == "waterway-label"
        assert "before_id" not in lyr

    def test_absent_before_id_emits_nothing(self):
        from shiny_deckgl import scatterplot_layer
        assert "beforeId" not in scatterplot_layer("pts", [])

    def test_extensions_still_work_alongside_before_id(self):
        from shiny_deckgl import brushing_extension, scatterplot_layer
        lyr = scatterplot_layer("pts", [], extensions=[brushing_extension()], before_id="x")
        assert lyr["beforeId"] == "x" and "@@extensions" in lyr
```

Append to `tests/test_render_cache_js.py` (Review Focus 5):

```python
@requires_node
def test_beforeId_reaches_the_deck_layer_props():
    got = run_js(_prelude(), """(function(){
        var src = [{ type: 'ScatterplotLayer', id: 'p', data: [], beforeId: 'waterway-label' }];
        return buildDeckLayers(src, 'm')[0].props.beforeId;
    })()""")
    assert got == "waterway-label"
```

- [ ] **Step 2: Run; expect the first Python test to FAIL (`before_id` emitted verbatim, no `beforeId`)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_basic.py','tests/test_render_cache_js.py','-k','BeforeId or beforeId']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 3: Implement**

In `src/shiny_deckgl/layers.py`, change only the `def` line (line 94) and add one `if` after `lyr` is built:

```python
def layer(
    type: str,
    id: str,
    data=None,
    *,
    extensions: list[str | list] | None = None,
    before_id: str | None = None,
    **kwargs,
) -> dict:
```

docstring addition (in the Parameters list, after `extensions`):

```
    before_id
        In interleaved mode (``MapWidget(interleaved=True)``), the id of the
        MapLibre style layer to draw this layer *beneath*, e.g. a label layer.
        Ignored in overlaid mode. Emitted as deck.gl's ``beforeId`` prop.
```

and immediately after the existing `lyr: dict = {**kwargs, "type": type, "id": id}`:

```python
    if before_id is not None:
        lyr["beforeId"] = before_id
```

Everything else in the function, including the `extensions` handling, is untouched.

- [ ] **Step 4: Run; expect PASS. Then `tests/test_basic.py` and `tests/test_extensions.py` in full.**

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/layers.py tests/test_basic.py tests/test_render_cache_js.py
git commit -m "feat: before_id= on deck.gl layers for interleaved ordering under basemap layers

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Deprecate `fps_widget()` and `view_selector_widget()`

**Files:**
- Modify: `src/shiny_deckgl/widgets.py` (`fps_widget`, `view_selector_widget`; add `import warnings`)
- Modify: `tests/test_widgets.py` (lines ~97, ~159–164, ~233–237, ~394–398, ~448–467 assert the old behaviour)
- Modify: `tests/test_widgets_resolve.py` (`KNOWN_UNAVAILABLE`; the `== 18` count at line 137)
- Modify: `src/shiny_deckgl/_app_server.py` (`_wg_active_widgets`: the `wg_fps` and `wg_view_selector` branches; the `@reactive.event` list and name lists in `_wg_update_map`), `src/shiny_deckgl/_app_ui.py` (remove the `wg_view_selector` switch; "17 deck.gl Widgets" labels → 16)

**Interfaces:**
- Produces: `fps_widget(placement="top-left", **kwargs)` warns `DeprecationWarning` and returns `stats_widget(placement=placement, **kwargs)`, i.e. `{"@@widgetClass": "_StatsWidget", ...}` — the same string the real helper emits, so the emitted-class set does not grow. `view_selector_widget()` warns `DeprecationWarning` and returns `{}`; `buildWidgets()` already drops a spec with no `@@widgetClass`. Emitted distinct `@@widgetClass` strings go from 18 to 16 (`_FpsWidget` and `_ViewSelectorWidget` gone).

- [ ] **Step 1: Rewrite the existing tests and add the new ones**

In `tests/test_widgets.py`:

- the fps structure test (~line 95–97): wrap the call in `with pytest.warns(DeprecationWarning):` and assert `w["@@widgetClass"] == "_StatsWidget"`;
- the view-selector structure (~159–164), default-placement (~233–237) and kwargs (~394–398) tests: replace all three with one test:

```python
    def test_view_selector_widget_is_deprecated_and_empty(self):
        with pytest.warns(DeprecationWarning, match="no ViewSelectorWidget"):
            assert view_selector_widget() == {}
```

- the all-widgets collection (~448–467): remove `fps_widget()` and `view_selector_widget()` from the list, change `assert len(widgets) == 17` to `== 15`.

Append:

```python
import warnings


class TestDeprecatedWidgetHelpers:
    def test_fps_widget_warns_and_becomes_a_stats_widget(self):
        from shiny_deckgl import fps_widget, stats_widget
        with pytest.warns(DeprecationWarning, match="StatsWidget"):
            spec = fps_widget(placement="bottom-left")
        assert spec == stats_widget(placement="bottom-left")

    def test_other_helpers_do_not_warn(self):
        from shiny_deckgl import zoom_widget
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            zoom_widget()
```

In `tests/test_widgets_resolve.py`: `KNOWN_UNAVAILABLE: set[str] = set()` (keep the comment, reworded: "fps_widget/view_selector_widget are deprecated and no longer emit `_FpsWidget`/`_ViewSelectorWidget`") and `assert len(emitted_widget_classes()) == 16`.

- [ ] **Step 2: Run; expect the new/rewritten tests to FAIL (no warning; old class names)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_widgets.py','tests/test_widgets_resolve.py::test_the_helper_set_is_what_we_think_it_is']); sys.stdout.flush(); os._exit(0)"`
(If the resolve test has a different name, run the whole file; its browser-gated class skips without Chromium.)

- [ ] **Step 3: Implement**

`widgets.py`: add `import warnings` at the top and replace the two helpers:

```python
def fps_widget(placement: str = "top-left", **kwargs) -> dict:
    """Deprecated: deck.gl 9.3 merged ``FpsWidget`` into ``StatsWidget``.

    Returns :func:`stats_widget` with the same arguments and warns. Removed in 2.0.
    """
    warnings.warn(
        "fps_widget() is deprecated: deck.gl 9.3 merged FpsWidget into "
        "StatsWidget. Use stats_widget() instead.",
        DeprecationWarning, stacklevel=2,
    )
    return stats_widget(placement=placement, **kwargs)


def view_selector_widget(placement: str = "top-left", **kwargs) -> dict:
    """Deprecated: deck.gl 9.x exports no ``ViewSelectorWidget``.

    Returns an empty spec, which the client drops, and warns. Removed in 2.0.
    """
    warnings.warn(
        "view_selector_widget() is deprecated: deck.gl 9.4 exports no "
        "ViewSelectorWidget, so it never rendered. It will be removed in 2.0.",
        DeprecationWarning, stacklevel=2,
    )
    return {}
```

Demo: in `_app_server.py` `_wg_active_widgets`, replace `fps_widget(...)` with `stats_widget(placement="bottom-left", framesPerUpdate=60)` under `wg_fps` and delete the `wg_view_selector` branch; remove `input.wg_view_selector` from `_wg_update_map`'s `@reactive.event(...)` list and `"_ViewSelectorWidget"` from its name lists; in `_app_ui.py` delete the `wg_view_selector` switch and change the "All 17 deck.gl Widgets" / "17 deck.gl Widgets + Layer Legend" labels to 16. In `_wg_update_map` the status line `f"Active widgets: {len(widgets)} / 18"` becomes `/ 17`.

- [ ] **Step 4: Run; expect PASS, with deprecation warnings treated as errors outside the two deprecation tests**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','-W','error::DeprecationWarning:shiny_deckgl','tests/test_widgets.py','tests/test_widgets_resolve.py','tests/test_app_modules.py','tests/test_demo_headless.py','tests/test_basic.py']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/widgets.py src/shiny_deckgl/_app_server.py src/shiny_deckgl/_app_ui.py tests/test_widgets.py tests/test_widgets_resolve.py
git commit -m "feat: deprecate fps_widget() (now StatsWidget) and view_selector_widget() (no such class)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: New widget helpers from deck.gl 9.3/9.4

**Files:**
- Modify: `src/shiny_deckgl/widgets.py` (`__all__`, five new helpers, `zoom_widget` gains `zoom_step`)
- Modify: `src/shiny_deckgl/__init__.py` (import + `__all__`)
- Modify: `tests/test_widgets_resolve.py` (count 16 → 21)
- Test: `tests/test_widgets.py`

**Interfaces:**
- Consumes (exact `@deck.gl/widgets@9.4.0` typings): `PopupWidget` (`position: number[]`, `content: string | {text?: string} | {html?: string}`, `placement?: PopoverProps['placement']` — a popover placement such as `'top'`/`'bottom-start'`, **not** a widget corner; `defaultIsOpen?`, `closeButton?`, `onOpenChange?`); `IconWidget` (`icon: string`, `label?`, `onClick?`); `ToggleWidget` (`icon`, `initialChecked?`, `onIcon?`, `label?`, `onLabel?`, `onColor?`, `onChange?`); `SelectorWidget` (`options: {value, icon, label?}[]` — each option needs an `icon`; `initialValue?`, `tooltip?`, `placement?`, `onChange?`; no top-level `icon`/`label`); `ScrollbarWidget` (`orientation?`, `contentBoundsPadding?`); `ZoomWidget` (`zoomStep?`).
- Produces:

```python
def zoom_widget(placement: str = "top-right", *, zoom_step: float | None = None, **kwargs) -> dict  # default unchanged
def popup_widget(position: list[float], content: str | dict, *, placement: str | None = None, **kwargs) -> dict
def icon_widget(icon: str, label: str | None = None, *, placement: str = "top-left", **kwargs) -> dict
def toggle_widget(icon: str, *, initial_checked: bool = False, on_icon: str | None = None,
                  label: str | None = None, on_label: str | None = None, on_color: str | None = None,
                  placement: str = "top-left", **kwargs) -> dict
def selector_widget(options: list[dict], *, initial_value=None, tooltip: str | None = None,
                    placement: str = "top-left", **kwargs) -> dict
def scrollbar_widget(orientation: str = "vertical", *, placement: str = "bottom-right", **kwargs) -> dict
```

All emit the un-prefixed class name; `resolveWidgetClass` also tries the `_` form.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_widgets.py`:

```python
class TestNewWidgetHelpers:
    def test_popup_widget(self):
        from shiny_deckgl import popup_widget
        spec = popup_widget([21.1, 55.7], "Klaipėda")
        assert spec == {"@@widgetClass": "PopupWidget", "position": [21.1, 55.7], "content": "Klaipėda"}
        rich = popup_widget([0, 0], {"html": "<b>x</b>"}, placement="bottom-start")
        assert rich["content"] == {"html": "<b>x</b>"} and rich["placement"] == "bottom-start"

    def test_icon_widget(self):
        from shiny_deckgl import icon_widget
        spec = icon_widget("info", "About")
        assert spec["@@widgetClass"] == "IconWidget" and spec["icon"] == "info" and spec["label"] == "About"

    def test_toggle_widget_snake_case_maps_to_deck_props(self):
        from shiny_deckgl import toggle_widget
        spec = toggle_widget("layers", initial_checked=True, on_icon="layers_clear", label="Layers",
                             on_label="Hide", on_color="#0a0")
        assert spec["@@widgetClass"] == "ToggleWidget"
        assert spec["initialChecked"] is True and spec["onIcon"] == "layers_clear"
        assert spec["onLabel"] == "Hide" and spec["onColor"] == "#0a0"
        assert "initial_checked" not in spec

    def test_selector_widget(self):
        from shiny_deckgl import selector_widget
        opts = [{"value": "a", "icon": "palette", "label": "A"}, {"value": "b", "icon": "brush"}]
        spec = selector_widget(opts, initial_value="a", tooltip="Palette")
        assert spec["@@widgetClass"] == "SelectorWidget"
        assert spec["options"] == opts and spec["initialValue"] == "a" and spec["tooltip"] == "Palette"

    def test_selector_widget_requires_an_icon_per_option(self):
        from shiny_deckgl import selector_widget
        with pytest.raises(ValueError, match="icon"):
            selector_widget([{"value": "a"}])

    def test_scrollbar_widget(self):
        from shiny_deckgl import scrollbar_widget
        assert scrollbar_widget("horizontal")["orientation"] == "horizontal"
        assert scrollbar_widget()["@@widgetClass"] == "ScrollbarWidget"

    def test_zoom_step_and_unchanged_default(self):
        from shiny_deckgl import zoom_widget
        assert zoom_widget(zoom_step=0.5)["zoomStep"] == 0.5
        assert "zoomStep" not in zoom_widget()
        assert zoom_widget()["placement"] == "top-right"

    def test_all_new_helpers_are_exported(self):
        import shiny_deckgl as m
        for name in ("popup_widget", "icon_widget", "toggle_widget", "selector_widget", "scrollbar_widget"):
            assert name in m.__all__ and callable(getattr(m, name))
```

In `tests/test_widgets_resolve.py` change the count to `== 21`.

- [ ] **Step 2: Run; expect FAIL (ImportError)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_widgets.py','-k','NewWidgetHelpers or zoom_step']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 3: Implement in `widgets.py`**

Replace `zoom_widget` (keep its default):

```python
def zoom_widget(placement: str = "top-right", *, zoom_step: float | None = None, **kwargs) -> dict:
    """Create a ``ZoomWidget`` spec (zoom-in / zoom-out buttons).

    zoom_step
        Zoom levels per click (deck.gl 9.4, default 1).
    """
    spec = {"@@widgetClass": "ZoomWidget", "placement": placement, **kwargs}
    if zoom_step is not None:
        spec["zoomStep"] = zoom_step
    return spec
```

Add after `screenshot_widget`:

```python
def popup_widget(
    position: list[float],
    content: str | dict,
    *,
    placement: str | None = None,
    **kwargs,
) -> dict:
    """Create a ``PopupWidget`` spec: a popup anchored at a map coordinate.

    position
        ``[longitude, latitude]`` (or ``[x, y]`` in a non-geospatial view).
    content
        Text, or ``{"text": ...}`` / ``{"html": ...}``.
    placement
        Where the popup sits relative to the anchor: a popover placement such
        as ``"top"``, ``"bottom-start"`` (not a widget corner).

    Open/close changes are reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    spec = {"@@widgetClass": "PopupWidget", "position": list(position), "content": content, **kwargs}
    if placement is not None:
        spec["placement"] = placement
    return spec


def icon_widget(icon: str, label: str | None = None, *, placement: str = "top-left", **kwargs) -> dict:
    """Create an ``IconWidget`` spec: a single button with a Material Symbols icon.

    Clicks are reported through :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    spec = {"@@widgetClass": "IconWidget", "placement": placement, "icon": icon, **kwargs}
    if label is not None:
        spec["label"] = label
    return spec


def toggle_widget(
    icon: str,
    *,
    initial_checked: bool = False,
    on_icon: str | None = None,
    label: str | None = None,
    on_label: str | None = None,
    on_color: str | None = None,
    placement: str = "top-left",
    **kwargs,
) -> dict:
    """Create a ``ToggleWidget`` spec: an on/off button.

    The checked state is reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    spec = {"@@widgetClass": "ToggleWidget", "placement": placement, "icon": icon,
            "initialChecked": initial_checked, **kwargs}
    for key, value in (("onIcon", on_icon), ("label", label), ("onLabel", on_label), ("onColor", on_color)):
        if value is not None:
            spec[key] = value
    return spec


def selector_widget(
    options: list[dict],
    *,
    initial_value=None,
    tooltip: str | None = None,
    placement: str = "top-left",
    **kwargs,
) -> dict:
    """Create a ``SelectorWidget`` spec: a dropdown of options.

    options
        Each ``{"value": ..., "icon": "<Material Symbols name>", "label": ...}``;
        ``icon`` is required by deck.gl.

    The chosen value is reported through
    :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`.
    """
    for opt in options:
        if not isinstance(opt, dict) or "value" not in opt or "icon" not in opt:
            raise ValueError("each selector option needs 'value' and 'icon' keys")
    spec = {"@@widgetClass": "SelectorWidget", "placement": placement, "options": list(options), **kwargs}
    if initial_value is not None:
        spec["initialValue"] = initial_value
    if tooltip is not None:
        spec["tooltip"] = tooltip
    return spec


def scrollbar_widget(orientation: str = "vertical", *, placement: str = "bottom-right", **kwargs) -> dict:
    """Create a ``ScrollbarWidget`` spec for large orthographic canvases."""
    return {"@@widgetClass": "ScrollbarWidget", "placement": placement, "orientation": orientation, **kwargs}
```

Add the five names to `widgets.__all__`, and in `src/shiny_deckgl/__init__.py` to the `from .widgets import (...)` block and `__all__`, next to `zoom_widget`.

- [ ] **Step 4: Run; expect PASS; then `tests/test_widgets_resolve.py` (its browser-gated class checks every emitted class resolves in the real bundle).**

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/widgets.py src/shiny_deckgl/__init__.py tests/test_widgets.py tests/test_widgets_resolve.py
git commit -m "feat: popup/icon/toggle/selector/scrollbar widget helpers; zoom_step on zoom_widget

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: Widget events reported as a Shiny input

**Files:**
- Modify: `src/shiny_deckgl/resources/deckgl-init.js` (`buildWidgets`; new `WIDGET_EVENTS` table and `attachWidgetEvents()`)
- Modify: `src/shiny_deckgl/map_widget.py` (new `widget_event_input_id` property next to `legend_visibility_input_id`)
- Modify: `src/shiny_deckgl/widgets.py` (docstrings of `timeline_widget`, `geocoder_widget`, `theme_widget`, `stats_widget`, `fullscreen_widget`, `loading_widget`, `reset_view_widget`)
- Test: `tests/test_widgets.py` (Python), `tests/test_widget_events_js.py` (Node, new), `tests/_apps/widget_events_app.py` + `tests/test_e2e_widget_events.py` (browser, new)

**Interfaces:**
- Consumes: the deck.gl 9.3+ callback props (from `@deck.gl/widgets@9.4.0` typings): `TimelineWidget.onTimeChange(value)`, `.onPlayingChange(playing)`; `ToggleWidget.onChange(checked)`; `SelectorWidget.onChange(value)`; `IconWidget.onClick()` (no argument); `PopupWidget.onOpenChange(isOpen)`; `StatsWidget.onExpandedChange(expanded)`; `ThemeWidget.onThemeModeChange(mode)`; `GeocoderWidget.onGeocode(params)`; `ZoomWidget.onZoom(params)`; `FullscreenWidget.onFullscreenChange(fullscreen)`; `LoadingWidget.onLoadingChange(loading)`; `ResetViewWidget.onReset(params)` (an object, `{viewId, viewState}`). Widgets read callbacks from `this.props` at event time, and each class has its own default `id` in `defaultProps` (`"timeline"`, `"toggle"`, …) which the constructed instance exposes as `widget.id`. `Widget.setProps(props)` merges with `Object.assign(this.props, props)`.
- Produces: one Shiny input per map, `f"{bare_id}_widget_event"`, set with `{priority: "event"}` to `{"id": <widget.id>, "widget": <class name without "_">, "event": <prop name without "on", lower-camel>, "value": <callback argument, or null when there is none>}`. Property `MapWidget.widget_event_input_id`. The shim is attached to the constructed instance's `props`, after `new Cls(props)`, so it reads the real id and survives later `setProps` merges (Review Focus 4). A pre-existing JS callback on the props is still called first.

- [ ] **Step 1: Python test for the property**

Append to `tests/test_widgets.py`:

```python
def test_widget_event_input_id():
    from shiny_deckgl import MapWidget
    assert MapWidget("m1").widget_event_input_id == "m1_widget_event"
```

- [ ] **Step 2: Node test for the shim (fails: `attachWidgetEvents` undefined)**

`tests/test_widget_events_js.py`:

```python
"""buildWidgets() reports deck.gl widget state changes to Shiny (roadmap 2.3)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

# Fake widget classes with deck.gl's shape: props merged over defaultProps,
# `id` taken from them, and setProps() merging like Widget.setProps.
_FAKES = r"""
var sent = [];
var Shiny = { setInputValue: function (n, v, o) { sent.push({name: n, value: v, opts: o}); } };
var document = { getElementById: function () { return null; } };
function makeClass(defaultId) {
  function W(props) { this.props = Object.assign({ id: defaultId }, props); this.id = this.props.id; }
  W.defaultProps = { id: defaultId };
  W.prototype.setProps = function (p) { Object.assign(this.props, p); };
  return W;
}
var deck = { TimelineWidget: makeClass('timeline'), ToggleWidget: makeClass('toggle'),
             IconWidget: makeClass('icon'), ZoomWidget: makeClass('zoom'), _GeocoderWidget: makeClass('geocoder') };
function createDeckLayerLegendWidget(p) { return new (makeClass('deck-layer-legend'))(p); }
"""


def _prelude():
    return "\n".join([
        _FAKES,
        extract_var("WIDGET_EVENTS"),
        extract_function("resolveWidgetClass"),
        extract_function("attachWidgetEvents"),
        extract_function("buildWidgets"),
    ])


def _js(body):
    return run_js(_prelude(), "(function(){" + body + "})()")


@requires_node
class TestWidgetEvents:
    def test_timeline_changes_reach_shiny(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': '_TimelineWidget', id: 'tl', timeRange: [0, 10] }], 'm')[0];
            w.props.onTimeChange(4); w.props.onPlayingChange(true);
            return sent;
        """)
        assert got == [
            {"name": "m_widget_event", "value": {"id": "tl", "widget": "TimelineWidget", "event": "timeChange", "value": 4}, "opts": {"priority": "event"}},
            {"name": "m_widget_event", "value": {"id": "tl", "widget": "TimelineWidget", "event": "playingChange", "value": True}, "opts": {"priority": "event"}},
        ]

    def test_unset_id_reports_the_classes_default_id(self):
        # Review Focus 1: deck.gl's default id is per class ("toggle"), not "widget".
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'ToggleWidget', icon: 'x' }], 'm')[0];
            w.props.onChange(true);
            return sent[0].value;
        """)
        assert got == {"id": "toggle", "widget": "ToggleWidget", "event": "change", "value": True}

    def test_callback_without_argument_sends_null(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'IconWidget', id: 'i', icon: 'info' }], 'm')[0];
            w.props.onClick();
            return sent[0].value;
        """)
        assert got == {"id": "i", "widget": "IconWidget", "event": "click", "value": None}

    def test_object_payloads_pass_through(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'ZoomWidget', id: 'z' }], 'm')[0];
            w.props.onZoom({ zoom: 5, direction: 'in' });
            return sent[0].value.value;
        """)
        assert got == {"zoom": 5, "direction": "in"}

    def test_existing_js_callback_is_still_called(self):
        got = _js("""
            var calls = 0;
            var w = buildWidgets([{ '@@widgetClass': 'ToggleWidget', id: 't', icon: 'x', onChange: function () { calls++; } }], 'm')[0];
            w.props.onChange(false);
            return { calls: calls, sent: sent.length };
        """)
        assert got == {"calls": 1, "sent": 1}

    def test_shim_survives_a_setProps_merge(self):
        # Review Focus 4: set_widgets() later merges new props into the instance.
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': 'ToggleWidget', id: 't', icon: 'x' }], 'm')[0];
            w.setProps({ icon: 'y', label: 'L' });
            w.props.onChange(true);
            return sent.length;
        """)
        assert got == 1

    def test_widgets_without_events_are_untouched(self):
        got = _js("""
            var w = buildWidgets([{ '@@widgetClass': '_DeckLayerLegendWidget', id: 'l' }], 'm')[0];
            return Object.keys(w.props).filter(function (k) { return k.indexOf('on') === 0; });
        """)
        assert got == []
```

- [ ] **Step 3: Run both; expect FAIL**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_widgets.py','tests/test_widget_events_js.py','-k','widget_event or WidgetEvents']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 4: Implement**

`map_widget.py`, after `legend_visibility_input_id`:

```python
    @property
    def widget_event_input_id(self) -> str:
        """Shiny input for state changes made in deck.gl widgets.

        Set (with event priority) each time a widget fires one of its
        callbacks, as ``{"id", "widget", "event", "value"}``: the widget's
        ``id`` (deck.gl's default is the class's own id, e.g. ``"timeline"``,
        so set ``id=`` when you add two of a kind), its class name
        (``"TimelineWidget"``), the event (``"timeChange"``,
        ``"playingChange"``, ``"change"``, ``"click"``, ``"openChange"``,
        ``"expandedChange"``, ``"themeModeChange"``, ``"geocode"``,
        ``"zoom"``, ``"fullscreenChange"``, ``"loadingChange"``, ``"reset"``)
        and the callback's argument: a value, an object for ``geocode``,
        ``zoom`` and ``reset``, or ``None`` for ``click``.
        """
        return f"{self._bare_id}_widget_event"
```

`deckgl-init.js`, immediately before `function buildWidgets`:

```js
  // Widget callbacks (deck.gl >= 9.3) forwarded to Shiny as one input per
  // map: <mapId>_widget_event = {id, widget, event, value}. Keyed by the
  // class name without the experimental "_" prefix.
  var WIDGET_EVENTS = {
    TimelineWidget: ['onTimeChange', 'onPlayingChange'],
    ToggleWidget: ['onChange'],
    SelectorWidget: ['onChange'],
    IconWidget: ['onClick'],
    PopupWidget: ['onOpenChange'],
    StatsWidget: ['onExpandedChange'],
    ThemeWidget: ['onThemeModeChange'],
    GeocoderWidget: ['onGeocode'],
    ZoomWidget: ['onZoom'],
    FullscreenWidget: ['onFullscreenChange'],
    LoadingWidget: ['onLoadingChange'],
    ResetViewWidget: ['onReset'],
  };

  // Patches the constructed widget's props: widgets read callbacks from
  // this.props at event time, the instance carries the real id (its class
  // default when the spec set none), and Widget.setProps merges, so the
  // shim survives later set_widgets() calls.
  function attachWidgetEvents(widget, className, targetId) {
    var name = className.replace(/^_/, '');
    var events = WIDGET_EVENTS[name];
    if (!events || !widget || !widget.props) return widget;
    events.forEach(function (prop) {
      var own = typeof widget.props[prop] === 'function' ? widget.props[prop] : null;
      var event = prop.charAt(2).toLowerCase() + prop.slice(3);   // onTimeChange -> timeChange
      widget.props[prop] = function (value) {
        if (own) own.apply(this, arguments);
        Shiny.setInputValue(targetId + '_widget_event', {
          id: widget.id != null ? widget.id : name, widget: name, event: event,
          value: arguments.length ? value : null,
        }, { priority: 'event' });
      };
    });
    return widget;
  }
```

and in `buildWidgets`, replace `return new Cls(props);` with:

```js
      return attachWidgetEvents(new Cls(props), className, targetId);
```

`widgets.py`: add to the docstrings of `timeline_widget`, `geocoder_widget`, `theme_widget`, `stats_widget`, `fullscreen_widget`, `loading_widget`, `reset_view_widget`: "State changes are reported through :attr:`~shiny_deckgl.MapWidget.widget_event_input_id`." and to `timeline_widget` also: "Pass ``initialTime`` for an uncontrolled timeline; passing ``time``/``playing`` makes it controlled, i.e. it only moves when the server sends new values with :meth:`~shiny_deckgl.MapWidget.set_widgets`."

- [ ] **Step 5: Run the Step 3 command; expect PASS**

- [ ] **Step 6: Browser test with the real widgets**

`tests/_apps/widget_events_app.py`:

```python
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, timeline_widget, toggle_widget

m = MapWidget("wmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

app_ui = ui.page_fluid(head_includes(), ui.output_text("last"), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [], widgets=[
            timeline_widget(id="tl", timeRange=[0, 100], initialTime=10, placement="bottom-left"),
            toggle_widget("layers", id="tg", placement="top-right"),
        ])

    @render.text
    def last():
        ev = input[m.widget_event_input_id]()
        return f"{ev['id']}:{ev['event']}:{ev['value']}" if ev else "none"


app = App(app_ui, server)
```

`tests/test_e2e_widget_events.py`:

```python
"""Real deck.gl widgets report their state changes as a Shiny input."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _e2e_app import browser_page, running_app  # noqa: E402

PORT = 18777


@pytest.fixture(scope="module")
def page():
    with running_app("widget_events_app", PORT):
        with browser_page(f"http://127.0.0.1:{PORT}/", "#wmap .maplibregl-canvas") as pg:
            pg.wait_for_selector("#wmap .deck-widget-timeline", timeout=30000)
            yield pg


def test_toggle_click_reaches_the_server(page):
    page.click("#wmap .deck-widget-toggle button")
    page.wait_for_function("() => document.getElementById('last').innerText === 'tg:change:True'", timeout=5000)


def test_timeline_play_reaches_the_server(page):
    page.click("#wmap .deck-widget-timeline button")  # play/pause button
    page.wait_for_function("() => /^tl:(playingChange|timeChange):/.test(document.getElementById('last').innerText)", timeout=5000)
```

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','--tb=short','tests/test_e2e_widget_events.py']); sys.stdout.flush(); os._exit(0)"`
Expected: PASS. If a selector does not match, read the widget DOM with Playwright (`page.evaluate("() => document.querySelector('#wmap .deck-widget-container').innerHTML")`) and adjust the two `.deck-widget-*` selectors; do not weaken the assertions.

- [ ] **Step 7: Commit**

```bash
git add src/shiny_deckgl/resources/deckgl-init.js src/shiny_deckgl/map_widget.py src/shiny_deckgl/widgets.py tests/test_widgets.py tests/test_widget_events_js.py tests/_apps/widget_events_app.py tests/test_e2e_widget_events.py
git commit -m "feat: deck.gl widget state changes reported as input[widget_event_input_id]

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: `pickable='3d'`, MapLibre `map_options`, and 9.4 prop documentation

**Files:**
- Modify: `src/shiny_deckgl/resources/deckgl-init.js` (`resolveLayerProps`: the `layerProps.pickable = true` line; the `mapOpts` literal in `initMap`; new `mergeMapOptions()`)
- Modify: `src/shiny_deckgl/map_widget.py` (`__init__` gains `map_options`; `_map_data_attrs`; `_JSON_WIDGET_SETTINGS`)
- Modify: `src/shiny_deckgl/layers.py` (module docstring: a "deck.gl 9.4 props" paragraph; `tile_layer`/`wms_layer` docstrings mention `visibleMinZoom`/`visibleMaxZoom`)
- Modify: `src/shiny_deckgl/extensions.py` (`path_style_extension` docstring: `dashMode`, `dashUnits`; `fill_style_extension` docstring: `fillPatternSizeUnits`, `getFillPatternBackgroundColor`)
- Test: `tests/test_render_cache_js.py`, `tests/test_review_2026_09.py`

**Interfaces:**
- Consumes: deck.gl 9.3+ `pickable?: boolean | '3d'`; `PickingInfo.coordinate` then carries `[lon, lat, z]` (the click input already forwards `info.coordinate`). MapLibre `Map` options `maxBounds`, `maxPitch`, `renderWorldCopies`, `antialias`, etc.
- Produces: `pickable="3d"` reaches deck.gl unchanged; raster layers keep skipping pick handlers. `MapWidget(map_options: dict | None = None)` → `data-map-options` (JSON) → merged into the MapLibre constructor options, `map_options` winning over the view-state-derived keys except `container` and `style`, which stay pinned; exported in JSON as `mapOptions`.

- [ ] **Step 1: Failing tests**

Append to `tests/test_render_cache_js.py`:

```python
@requires_node
class TestPickable3d:
    def test_3d_is_kept_and_handlers_attached(self):
        got = run_js(_prelude(), """(function(){
            var l = buildDeckLayers([{ type: 'ScatterplotLayer', id: 'p', data: [], pickable: '3d' }], 'm')[0];
            return { pickable: l.props.pickable, click: typeof l.props.onClick, hover: typeof l.props.onHover };
        })()""")
        assert got == {"pickable": "3d", "click": "function", "hover": "function"}

    def test_raster_layer_with_3d_gets_no_handlers(self):
        # Review Focus 2
        got = run_js(_prelude() + "\ndeck.TileLayer = FakeLayer;", """(function(){
            var l = buildDeckLayers([{ type: 'TileLayer', id: 't', data: 'https://x/{z}/{x}/{y}.png', pickable: '3d' }], 'm')[0];
            return { pickable: l.props.pickable, click: typeof l.props.onClick };
        })()""")
        assert got == {"pickable": "3d", "click": "undefined"}


@requires_node
def test_map_options_merge_keeps_container_and_style():
    got = run_js(extract_function("mergeMapOptions"), """(function(){
        var base = { container: 'm', style: 'S', zoom: 3, maxZoom: 24 };
        return [
          mergeMapOptions(base, { dataset: {} }),
          mergeMapOptions(base, { dataset: { mapOptions: JSON.stringify({ maxZoom: 12, maxBounds: [[20,54],[23,57]], container: 'evil', style: 'evil' }) } }),
          mergeMapOptions(base, { dataset: { mapOptions: '{not json' } }),
        ];
    })()""")
    assert got[0] == {"container": "m", "style": "S", "zoom": 3, "maxZoom": 24}
    assert got[1] == {"container": "m", "style": "S", "zoom": 3, "maxZoom": 12, "maxBounds": [[20, 54], [23, 57]]}
    assert got[2] == got[0]
```

Append to `tests/test_review_2026_09.py`:

```python
class TestMapOptions:
    def test_attribute_and_json_round_trip(self):
        import json as _json
        from shiny_deckgl import MapWidget
        w = MapWidget("m", map_options={"maxPitch": 60, "renderWorldCopies": False})
        assert 'data-map-options="' in str(w.ui())
        assert _json.loads(w.to_json([]))["mapOptions"] == {"maxPitch": 60, "renderWorldCopies": False}
        w2, _ = MapWidget.from_json(w.to_json([]))
        assert w2.map_options == {"maxPitch": 60, "renderWorldCopies": False}
        assert "data-map-options" not in str(MapWidget("d").ui())

    def test_pinned_keys_are_rejected(self):
        from shiny_deckgl import MapWidget
        with pytest.raises(ValueError, match="container"):
            MapWidget("m", map_options={"container": "x"})
```

- [ ] **Step 2: Run; expect FAIL**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_render_cache_js.py','tests/test_review_2026_09.py','-k','Pickable3d or map_options or MapOptions']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 3: Implement**

`deckgl-init.js`, in `resolveLayerProps` (the block `if (!RASTER_TYPES.has(layerProps.type) && layerProps.pickable !== false) {`), replace `layerProps.pickable = true;` with:

```js
        // Keep '3d' (depth picking, deck.gl >= 9.3); only fill in the default.
        if (layerProps.pickable !== '3d') layerProps.pickable = true;
```

Next to `applyController`, add:

```js
  // data-map-options: extra MapLibre Map constructor options (maxBounds,
  // maxPitch, renderWorldCopies, antialias, ...). They win over the
  // view-state-derived defaults; container and style stay pinned.
  function mergeMapOptions(base, el) {
    var raw = el && el.dataset ? el.dataset.mapOptions : undefined;
    if (!raw) return Object.assign({}, base);
    var extra;
    try { extra = JSON.parse(raw); } catch (e) {
      console.warn('[shiny_deckgl] Ignoring malformed data-map-options:', e.message);
      return Object.assign({}, base);
    }
    var out = Object.assign({}, base, extra);
    out.container = base.container;
    out.style = base.style;
    return out;
  }
```

and in `initMap`, after the `const mapOpts = {...};` literal, before `new maplibregl.Map(mapOpts)`, change the construction to `const map = new maplibregl.Map(mergeMapOptions(mapOpts, el));`.

`map_widget.py` `__init__`: add after `interleaved: bool = False,`:

```python
        map_options: dict | None = None,
```

docstring entry:

```
    map_options
        Extra MapLibre ``Map`` constructor options, e.g.
        ``{"maxBounds": [[20, 54], [23, 57]], "maxPitch": 60,
        "renderWorldCopies": False, "antialias": True}``. They override the
        view-state-derived defaults; ``container`` and ``style`` cannot be set
        here.
```

body, next to `self.interleaved = interleaved`:

```python
        if map_options and ({"container", "style"} & set(map_options)):
            raise ValueError("map_options cannot set 'container' or 'style'; use style=")
        self.map_options = dict(map_options) if map_options else None
```

In `_map_data_attrs`, after the `interleaved` line:

```python
        if self.map_options:
            attrs["data_map_options"] = json.dumps(self.map_options)
```

In `_JSON_WIDGET_SETTINGS` add `("mapOptions", "map_options", None),`.

Docstrings: in `layers.py`'s module docstring add:

```
deck.gl 9.4 props worth knowing (all pass through ``**kwargs``):
  ``pickable="3d"`` (depth picking: the click/hover ``coordinate`` gains z),
  ``antialiasing=True`` on Path/Line/Arc/PointCloud layers,
  ``visibleMinZoom``/``visibleMaxZoom`` on ``TileLayer`` (draw range,
  separate from the load range), ``getPixelOffset`` on ``ScatterplotLayer``.
```

and one sentence on `visibleMinZoom`/`visibleMaxZoom` in the `tile_layer` and `wms_layer` docstrings. In `extensions.py`, add to `path_style_extension`'s docstring: "deck.gl 9.4 adds ``dashMode`` (``\"restart\"`` per segment or ``\"continuous\"``) and ``dashUnits`` (``\"strokeWidth\"``, ``\"pixels\"``, ``\"meters\"``, ``\"common\"``), passed as layer props." and to `fill_style_extension`'s: "deck.gl 9.4 generates hatch, cross-hatch and dot patterns in the shader and adds ``fillPatternSizeUnits`` and ``getFillPatternBackgroundColor`` layer props."

- [ ] **Step 4: Run; expect PASS. Then `tests/test_render_cache_js.py`, `tests/test_review_2026_09.py` in full, and one browser module (`tests/test_e2e_rerender.py`) to confirm maps still construct.**

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/resources/deckgl-init.js src/shiny_deckgl/map_widget.py src/shiny_deckgl/layers.py src/shiny_deckgl/extensions.py tests/test_render_cache_js.py tests/test_review_2026_09.py
git commit -m "feat: pickable='3d' reaches deck.gl; MapWidget(map_options=) for MapLibre map options; 9.4 prop docs

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: Reconnect resync

**Files:**
- Modify: `src/shiny_deckgl/resources/deckgl-init.js` (`onShinyConnected`; a new top-level `var _reconnectCount = 0;` next to `var _shinyConnectedHandled = false;` at ~line 1213)
- Modify: `src/shiny_deckgl/map_widget.py` (`__init__`: `self.last_update = None`; `update()`; new `reconnected_input_id`; new `resend_last_update()`)
- Test: `tests/test_review_2026_09.py` (Python), `tests/test_reconnect_js.py` (Node, new)

**Interfaces:**
- Consumes: Shiny's client fires `shiny:connected` on every socket open, including after a reconnect (`session.allow_reconnect()`, Shiny ≥ 1.8.0); the package's `onShinyConnected` runs its startup once thanks to `_shinyConnectedHandled`.
- Produces: on the second and later `shiny:connected`, the client sets `f"{bare_id}_reconnected"` (event priority, value `{"count": n}`) for every live map. `MapWidget.update()` records its payload per session (`self._remember(session, "last_update", payload)`); `await MapWidget.resend_last_update(session)` sends it again as `deck_update` and returns `True`, or does nothing and returns `False` when nothing was recorded (Review Focus 3).

- [ ] **Step 1: Python tests**

Append to `tests/test_review_2026_09.py`:

```python
class TestReconnectResync:
    def test_input_id(self):
        from shiny_deckgl import MapWidget
        assert MapWidget("m").reconnected_input_id == "m_reconnected"

    def test_resend_repeats_the_last_update_for_that_session(self):
        import asyncio
        from conftest import _FakeSession
        from shiny_deckgl import MapWidget, scatterplot_layer
        w, s1, s2 = MapWidget("m"), _FakeSession(), _FakeSession()
        asyncio.run(w.update(s1, [scatterplot_layer("a", [[1, 2]])], picking_radius=5))
        first = s1.messages[-1]
        assert asyncio.run(w.resend_last_update(s1)) is True
        assert s1.messages[-1] == first
        assert asyncio.run(w.resend_last_update(s2)) is False   # Review Focus 3
        assert s2.messages == []
```

- [ ] **Step 2: Node test**

`tests/test_reconnect_js.py`:

```python
"""A repeated shiny:connected (a reconnect) tells the server which maps are live."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _js_harness import extract_function, extract_var, requires_node, run_js  # noqa: E402

# Every global onShinyConnected touches must exist: the harness runs in
# strict mode. _reconnectCount is extracted from the runtime itself.
_FAKES = r"""
var sent = [];
var Shiny = { setInputValue: function (n, v, o) { sent.push({name: n, value: v, opts: o}); } };
var mapInstances = { a: {}, b: {} };
var _shinyConnectedHandled = false;
function loadMapLibre() { return Promise.resolve(); }
var maplibregl = undefined, deck = undefined;   // tryInit polls and gives up; not under test
var document = { querySelectorAll: function () { return []; } };
function setTimeout() {}
"""


@requires_node
def test_second_connected_reports_a_reconnect_for_every_map():
    prelude = "\n".join([_FAKES, extract_var("_reconnectCount"), extract_function("onShinyConnected")])
    got = run_js(prelude, """(function(){
        onShinyConnected();            // first connect: no report
        var afterFirst = sent.length;
        onShinyConnected(); onShinyConnected();
        return { afterFirst: afterFirst, sent: sent };
    })()""")
    assert got["afterFirst"] == 0
    assert got["sent"] == [
        {"name": "a_reconnected", "value": {"count": 1}, "opts": {"priority": "event"}},
        {"name": "b_reconnected", "value": {"count": 1}, "opts": {"priority": "event"}},
        {"name": "a_reconnected", "value": {"count": 2}, "opts": {"priority": "event"}},
        {"name": "b_reconnected", "value": {"count": 2}, "opts": {"priority": "event"}},
    ]
```

- [ ] **Step 3: Run both; expect FAIL (`_reconnectCount` not found by `extract_var`; no `resend_last_update`)**

Run: `micromamba run -n shiny python -c "import pytest,os,sys; rc=pytest.main(['-q','-p','no:cacheprovider','tests/test_review_2026_09.py','tests/test_reconnect_js.py','-k','Reconnect or reconnect']); sys.stdout.flush(); os._exit(0)"`

- [ ] **Step 4: Implement**

`deckgl-init.js`: next to `var _shinyConnectedHandled = false;` add `var _reconnectCount = 0;`, and in `onShinyConnected` replace

```js
    if (_shinyConnectedHandled) return;
    _shinyConnectedHandled = true;
```

with

```js
    if (_shinyConnectedHandled) {
      // A later shiny:connected is a reconnect (session.allow_reconnect()).
      // Shiny resends inputs and recalculates outputs, but the maps are fed
      // by custom messages, which are not replayed: tell the server which
      // maps are still live so it can resend_last_update().
      _reconnectCount++;
      Object.keys(mapInstances).forEach(function (id) {
        Shiny.setInputValue(id + '_reconnected', { count: _reconnectCount }, { priority: 'event' });
      });
      return;
    }
    _shinyConnectedHandled = true;
```

`map_widget.py`: in `__init__`, next to `self._session_state = WeakKeyDictionary()`:

```python
        self.last_update: dict | None = None   # fallback for _recall("last_update")
```

In `update()`, just before `await session.send_custom_message("deck_update", json_safe(payload))`:

```python
        # Kept per session so resend_last_update() can replay it after a reconnect.
        self._remember(session, "last_update", payload)
```

After `legend_visibility_input_id`:

```python
    @property
    def reconnected_input_id(self) -> str:
        """Shiny input set when the browser reconnects to its session.

        Requires ``session.allow_reconnect(True)`` (Shiny >= 1.8.0) and a host
        that keeps sessions alive. Value: ``{"count": n}``. Typical use::

            @reactive.effect
            @reactive.event(input[widget.reconnected_input_id])
            async def _resync():
                await widget.resend_last_update(session)
        """
        return f"{self._bare_id}_reconnected"
```

After `update()`:

```python
    async def resend_last_update(self, session: "Session") -> bool:
        """Send this session's most recent :meth:`update` payload again.

        Custom messages sent while the websocket was down are lost; after a
        reconnect (:attr:`reconnected_input_id`) this restores the layers,
        widgets and view state of the last update. Native MapLibre layers and
        controls are not replayed. Returns ``False`` when nothing was recorded.
        """
        payload = self._recall(session, "last_update")
        if payload is None:
            return False
        await session.send_custom_message("deck_update", json_safe(payload))
        return True
```

- [ ] **Step 5: Run; expect PASS. Then `tests/test_review_2026_09.py` in full.**

- [ ] **Step 6: Commit**

```bash
git add src/shiny_deckgl/resources/deckgl-init.js src/shiny_deckgl/map_widget.py tests/test_review_2026_09.py tests/test_reconnect_js.py
git commit -m "feat: reconnected_input_id and resend_last_update() for session.allow_reconnect()

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: Release 1.12.0

**Files:**
- Modify: `src/shiny_deckgl/_version.py`, `CHANGELOG.md`, `README.md`, `.github/copilot-instructions.md`

- [ ] **Step 1: Bump**

```python
__version__ = "1.12.0"
```

- [ ] **Step 2: CHANGELOG entry (above `## [1.11.1]`; the file is CRLF with a BOM — write it the way the 1.11.x entries were written)**

```markdown
## [1.12.0] — <date>

From `docs/2026-09-27-dependency-review.md`; plan in `docs/superpowers/plans/2026-09-27-dependency-roadmap.md`.

### Added
- `before_id=` on every layer helper: interleaved ordering under a basemap layer.
- `popup_widget()`, `icon_widget()`, `toggle_widget()`, `selector_widget()`,
  `scrollbar_widget()`; `zoom_widget(zoom_step=)`.
- `MapWidget.widget_event_input_id`: widget state changes (timeline, toggles,
  selectors, geocoder, theme, ...) arrive as `{"id", "widget", "event", "value"}`.
- `MapWidget(map_options=)`: extra MapLibre map options (`maxBounds`, `maxPitch`,
  `renderWorldCopies`, `antialias`, ...).
- `MapWidget.reconnected_input_id` and `resend_last_update()` for
  `session.allow_reconnect()` (Shiny >= 1.8.0).
- `pickable="3d"` (depth picking) is passed through to deck.gl.
- `tests/test_demo_headless.py`: parts of the demo's reactive graph under `shiny.testserver`.

### Changed
- MapLibre GL JS 6.7.0 → 6.11.2 (served); exports stay on 5.24.0.
- deck.gl integration is now `MapLibreOverlay`, the integration deck.gl recommends for MapLibre.
- Demo uses `ui.output_code()` (Shiny 1.8.0 deprecates `output_text_verbatim`).
- Demo Widget Gallery: the View selector switch is gone (no such deck.gl class), the
  FPS switch adds a `StatsWidget`, 16 widgets.

### Deprecated
- `fps_widget()` (returns a `StatsWidget`) and `view_selector_widget()` (renders nothing); removed in 2.0.

### Not done
- WebGPU opt-in: the CDN umbrella bundle ships no WebGPU adapter, so it cannot be
  enabled without an extra `@luma.gl/webgpu` bundle. Deferred.
```

- [ ] **Step 3: README** — a `### v1.12.0` table in the version history, following the 1.11.x sections' style; update the pinned-version sentence in `.github/copilot-instructions.md` if Task 1 left anything.

- [ ] **Step 4: Full unit suite + browser modules one at a time; then commit**

```bash
git add src/shiny_deckgl/_version.py CHANGELOG.md README.md .github/copilot-instructions.md
git commit -m "release: v1.12.0 -- MapLibre 6.11.2, MapLibreOverlay, widget events, map options, reconnect resync

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Push the branch and open a PR against `main`; after merge, tag `v1.12.0` and run the `conda-build-upload` workflow (it skips versions already on the channel).

---

## Self-review notes

- Spec coverage: 2.1 → Task 1; 2.2 → Task 4 (+5 for `before_id`); 2.3 → Tasks 6–8; 2.4 → Task 9 (`pickable='3d'`, `map_options`, prop docs; demo antialias toggle deferred); 2.5 → Tasks 2, 3, 10; 2.6 → deferred with reason; 2.7 → no code; release → Task 11.
- Names used across tasks: `widget_event_input_id` / `attachWidgetEvents` / `WIDGET_EVENTS` (8), `reconnected_input_id` / `resend_last_update` / `_reconnectCount` (10), `map_options` / `data-map-options` / `mergeMapOptions` (9), `before_id` → `beforeId` (5), `stats_widget` reuse in `fps_widget` (6). Consistent.
- Emitted `@@widgetClass` count: 18 today → 16 after Task 6 → 21 after Task 7; both tasks update `tests/test_widgets_resolve.py`.
- Review Focus 1–5 have tests in Tasks 8, 9, 10, 8, 5 respectively.
