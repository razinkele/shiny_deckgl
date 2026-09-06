# Codebase review — src/shiny_deckgl (2026-09-06)

Workflow review: 6 subsystem finders + per-cluster adversarial verification (12 agents).
27 candidates raised, 25 confirmed.

| cluster | raised | confirmed |
|---|---|---|
| js-runtime | 4 | 4 |
| widget-core | 4 | 3 |
| demo-app | 5 | 5 |
| data-sim | 5 | 5 |
| support | 5 | 4 |
| py-js-contract | 4 | 4 |

## CRITICAL (2)

### `_app_server.py:1923` — correctness

`ui` is never imported or bound in _app_server.py, so every reference to it raises NameError; in a reactive.Effect this closes the whole Shiny session.

**Failure scenario.** Click any Widgets Gallery preset button (wg_preset_nav / _debug / _presentation / _all / _none). `_wg_apply_preset` executes `ui.update_switch("wg_zoom", value=zoom)` at line 1923 -> NameError: name 'ui' is not defined. The exception propagates out of the reactive.Effect into Session._unhandled_error (shiny/session/_session.py:1569-1571), which prints the error and calls `await self.close()` -- the entire browser session (all 12 tabs) is terminated, not just that control. Same crash from Tab 6 'Export HTML' at line 1057 (`ui.notification_show(...)`, after the file has already been written and the log set). The `@render.ui` output `pal_swatch` (lines 554/563/564/568) hits the same NameError but degrades to an error box instead of closing the session. Verified: `symtable` reports 'ui' is not an identifier at module scope nor bound anywhere in the file; the only imports are json/os/random/tempfile/typing plus package-local names (lines 9-137), and the deferred import at line 141 is `from shiny import reactive, render` -- no `ui`.

```
line 141: `    from shiny import reactive, render  # imported here to keep top-level light`
line 1057: `        ui.notification_show(f"Exported to {path}", type="message")`
line 1923: `        ui.update_switch("wg_zoom", value=zoom)`
line 554: `                ui.tags.div(`
shiny/session/_session.py:1569-1571: `async def _unhandled_error(self, e: Exception) -> None:` / `print("Unhandled error: " + str(e), file=sys.stderr)` / `await self.close()`
```

*Verifier:* Verified: _app_server.py has no binding of `ui` anywhere — imports at lines 9-13 (json/os/random/tempfile/typing), 16-137 package-local names, and the deferred `from shiny import reactive, render` at line 141. Grep for `ui =`, `import ui`, `as ui` returns nothing, yet there are 20+ `ui.` references. Line 1923 is exactly `ui.update_switch("wg_zoom", value=zoom)` inside `_wg_apply_preset`, reached from the five preset effects (1880-1918); `wg_preset_all` etc. exist in _app_ui.py (line 1353), and `export_html` (856) reaches `ui.notification_show` at 1057. No test in tests/test_review_fixes.py or tests/test_tooltip_xss.py covers it; working tree is post-08bdf4f. Real NameError on every preset click and on HTML export.

### `_app_server.py:1074` — correctness

`MapWidget` is used in _do_roundtrip but never imported into _app_server.py, so the JSON round-trip button raises NameError and closes the session.

**Failure scenario.** Open Tab 6 (Export & Serialisation) and click the 'JSON round-trip' button (input.roundtrip_json). `_do_roundtrip` builds the layers and the spec successfully, then line 1074 evaluates `MapWidget.from_json(spec_json)` -> NameError: name 'MapWidget' is not defined. Being inside a `reactive.Effect`, this reaches `Session._unhandled_error`, which calls `await self.close()` and kills the whole demo session. `_app_server.py` imports MapWidget nowhere (module symbol table has no 'MapWidget'); only `_app_widgets.py` imports it. The demo therefore has no working round-trip feature at all.

```
line 1071-1074: `    async def _do_roundtrip():` / `        layers = _gl_build_all_layers()` / `        spec_json = gallery_widget.to_json(layers)` / `        w2, layers2 = MapWidget.from_json(spec_json)`
(module import block lines 9-137 contains no `MapWidget`; symtable confirms `module has MapWidget: False`)
```

*Verifier:* Verified: line 1074 is `w2, layers2 = MapWidget.from_json(spec_json)` and it is the ONLY occurrence of `MapWidget` in _app_server.py — the name is never imported (MapWidget is imported only in _app_widgets.py, which _app_server.py imports selectively at lines 125-137, not including MapWidget). The `roundtrip_json` button exists in _app_ui.py:862, so `_do_roundtrip` is reachable and raises NameError after to_json succeeds. Not covered by the cited tests.

## HIGH (10)

### `resources/deckgl-init.js:82` — security

sanitizeHtml's javascript:-URI check is bypassable with embedded whitespace/control characters, so attacker-controlled feature properties can produce clickable javascript: links in MapLibre popups.

**Failure scenario.** An app author registers a normal popup template via deck_add_popup, e.g. template = '<a href="{website}">Visit</a>' (used at line 2702). The native MapLibre layer is fed from an external GeoJSON / vector-tile source, so feature properties are attacker-controlled. A feature carries website = "java\tscript:alert(document.cookie)" (a literal TAB inside the scheme). escapeHtml (lines 66-74) only replaces & < > " ' so the tab survives; DOMParser preserves it in the href attribute value; the guard /^\s*javascript\s*:/i at line 82 fails to match because the whitespace is *inside* the word, not leading; doc.body.innerHTML re-serialises the tab verbatim and the string reaches maplibregl.Popup.setHTML() at line 2713. Per the URL spec browsers strip TAB/LF/CR from URLs before parsing, so clicking the link executes the JavaScript in the Shiny app's origin. A leading C0 control ("\x01javascript:...") is a second variant: browsers strip leading C0 controls but JS \s does not match \x01. The tooltip path (line 1266) is not exploitable because .deckgl-tooltip has pointer-events:none (styles.css line 8), but the popup paths at lines 2702 and 2864 are. Fix direction: normalise with new URL(attr.value, location.href).protocol instead of a regex.

```
var SANITIZE_DANGEROUS_URI = /^\s*javascript\s*:/i;   // line 82
} else if (SANITIZE_URI_ATTRS.has(attr.name.toLowerCase()) &&
           SANITIZE_DANGEROUS_URI.test(attr.value)) {   // lines 103-104
const html = sanitizeHtml(interpolateTemplate(template, props));  // line 2702
.setHTML(html)   // line 2713
```

*Verifier:* Verified at deckgl-init.js:82: SANITIZE_DANGEROUS_URI = /^\s*javascript\s*:/i requires the literal contiguous word 'javascript', so 'java\tscript:' (or a leading \x01 C0 control) does not match. escapeHtml (66-74) only replaces & < > " ' so the TAB survives interpolation; DOMParser preserves it inside the quoted href value and doc.body.innerHTML re-serialises it. The URL spec has browsers strip TAB/LF/CR before scheme parsing, so the link executes. Reachable: sanitizeHtml(interpolateTemplate(template, props)) feeds maplibregl.Popup.setHTML at ~2713 (deck_add_popup, feature props from an external source) and setHTML(sanitizeHtml(payload.popupHtml)) at ~2864. tests/test_tooltip_xss.py only covers Python-side escaping and has no URI-scheme test; commit 08bdf4f's security fixes were </script> escaping and Mapbox token host matching, not this regex.

### `resources/deckgl-init.js:3092` — correctness

deck_export_image screenshots only the MapLibre basemap canvas, silently dropping every deck.gl layer in the default (non-interleaved) mode.

**Failure scenario.** The widget is created without interleaved=True, so line 746 sets interleavedMode = false and deck.MapboxOverlay renders into its own separate canvas layered above the MapLibre canvas. deck_export_image then calls map.getCanvas() (line 3092) and canvas.toDataURL(...) (line 3099), which reads only the MapLibre GL canvas. Repro: render a ScatterplotLayer with 1000 points, send deck_export_image, and the returned dataUrl is a picture of the basemap with zero points on it — no error, no warning, just a silently wrong export. Only interleaved=True happens to work, because in that mode deck.gl draws into MapLibre's own WebGL context. The exported width/height reported back at lines 3103-3104 also come from the basemap canvas, so a caller cannot even detect the mismatch.

```
const interleavedMode = el.dataset.interleaved === 'true';   // line 746
const canvas = map.getCanvas();                              // line 3092
const dataUrl = canvas.toDataURL(format, quality);           // line 3099
```

*Verifier:* Verified: line 3092 is 'const canvas = map.getCanvas();' and 3099 'canvas.toDataURL(format, quality)', both on the MapLibre GL canvas. interleavedMode comes from el.dataset.interleaved (line 746) and map_widget.py:186 defaults interleaved=False, so the default path constructs deck.MapboxOverlay({interleaved:false}), which renders into its own separate canvas above the basemap; that canvas is never read. preserveDrawingBuffer:true at line 634 only makes the basemap capture non-blank, it does not merge deck layers. width/height at 3103-3104 also come from the basemap canvas. export_image (map_widget.py:1933) documents no such limitation, so the silently-wrong export is a real, undisclosed defect.

### `map_widget.py:390` — silently-wrong-data

update() and partial_update() send layer payloads over the websocket without json_safe() sanitisation, so NaN/inf (and pandas Timestamps) in DataFrame-derived layer data produce invalid JSON or crash the send.

**Failure scenario.** df = pd.DataFrame({'lon':[21.1,21.2],'lat':[55.7,55.8],'depth':[10.0,float('nan')]}); await widget.update(session, [scatterplot_layer('pts', df, getPosition='@@d.lon')]). _serialise_data() turns the frame into row-dicts containing NaN; I ran this and json.dumps emits the bare token: ..."depth": NaN}]}. Shiny writes that string to the socket and the browser's JSON.parse throws SyntaxError, so the whole deck_update message (and anything batched with it) is dropped — the map silently never updates, with no server-side error. A missing value in a survey/bathymetry column is the normal case, not an edge case. Same root cause with a different symptom for a datetime column: pd.to_datetime(...) rows yield Timestamp objects and json.dumps raises 'TypeError: Object of type Timestamp is not JSON serializable' inside _send_message, killing the session.

```
map_widget.py:368-390  payload: dict = {"id": self.id, "layers": layers} ... await session.send_custom_message("deck_update", payload)   — no json_safe(), unlike to_json() (line 2011) and to_html() (lines 2083-2084) which both call json_safe(). partial_update() at line 430 has the same gap: it calls _serialise_data() but never json_safe(). Shiny's transport is plain stdlib json: site-packages/shiny/session/_session.py:1458  message_str = json.dumps(message)  (allow_nan=True by default).
```

*Verifier:* Verified. map_widget.py:390 (update) and :430 (partial_update) call session.send_custom_message() with the raw layer payload; grep shows json_safe() is applied only in to_json() (:2011) and to_html() (:2083-2084), never on the websocket path. layer() -> _data_utils._serialise_data() converts a DataFrame via to_dict(orient='records'), preserving NaN floats and pandas Timestamp objects verbatim. Shiny's SessionImpl._send_message (site-packages/shiny/session/_session.py:1458) is a bare `json.dumps(message)` with no encoder and no allow_nan=False, so NaN emits the non-standard bare token (client-side JSON.parse rejects the frame) and a Timestamp raises TypeError inside the send. Not covered by 08bdf4f / test_review_fixes.py (which only tests to_json/to_html NaN+inf) or test_tooltip_xss.py.

### `map_widget.py:2108` — security-xss

to_html() interpolates view_state values into HTML attributes with no escaping, while every neighbouring attribute on the same div is escaped — allowing attribute break-out and script injection.

**Failure scenario.** MapWidget('m', view_state={'longitude': '0"><script>alert(1)</script><div x="', 'latitude': 55.7, 'zoom': 8}).to_html([]) — I ran it and the output contains literally: data-initial-longitude="0"><script>alert(1)</script><div x="". The injected script executes for anyone opening the exported file. Reachable whenever view_state is not developer-authored, e.g. MapWidget.from_json(spec) (line 2013) on a user-supplied/round-tripped spec, or a view_state built from input.<map>_view_state()/a query string before export. ui() is unaffected because htmltools escapes attributes; only to_html() is vulnerable, and test_review_fixes.py only covers </script> inside layer data, not view_state.

```
map_widget.py:2106-2116:
<div id="{_html_mod.escape(self.id)}" class="deckgl-map"
     style="width:100%;height:100vh;"
     data-initial-longitude="{vs.get('longitude', 0)}"
     data-initial-latitude="{vs.get('latitude', 0)}"
     ...
     data-style="{_html_mod.escape(self.style)}"
id, style, tooltip (line 2073) and mapbox_api_key (line 2078) all go through _html_mod.escape(..., quote=True); the seven data-initial-* values do not.
```

*Verifier:* Verified. map_widget.py:2108-2114 interpolate vs.get('longitude'|'latitude'|'zoom'|...) straight into double-quoted HTML attributes, while the id (:2106), style (:2115), tooltip (:2073) and mapbox key (:2078) on the same div all go through _html_mod.escape(..., quote=True) - the inconsistency is on adjacent lines. __init__ (:195) stores `view_state or {...}` with no type coercion or validation, so a string value survives to the f-string; from_json (:2013-2034) feeds an arbitrary parsed spec through that same __init__, giving a concrete untrusted path. test_review_fixes.py covers only </script> inside layer data and test_tooltip_xss.py only the data-tooltip attribute; neither touches view_state.

### `_app_server.py:1285` — correctness

Two independent effects own the same adv_widget layer list with divergent state, so each one silently wipes the other's layers.

**Failure scenario.** `_adv_init` (line 736) pushes the cargo-column layers and records them in `_adv_layers`. `_v1_layers` (line 1255) writes to the SAME `adv_widget` via a full-replace `update()` with only `["v1_ports"]`, and never touches `_adv_layers`. Both fire at session start (`@reactive.event` defaults to ignore_init=False), and `_v1_layers` is registered later (1255 > 736/743), so it runs last: the Advanced tab opens showing only v1_ports -- the 3-D cargo columns the tab is built around are never visible. Conversely, nudging the Ambient slider makes `_apply_lighting` (line 750) re-push `_adv_layers.get()`, which still contains cargo-columns/binary-scatter/animated-ports but NOT v1_ports, so the brushing/data-filter layer silently disappears while its sidebar switches still read 'enabled'. Every subsequent toggle flip-flops the map between the two disjoint layer sets.

```
line 736-739: `    async def _adv_init():` / `        layers = _adv_base_layers()` / `        _adv_layers.set(layers)` / `        await adv_widget.update(session, layers)`
line 1271-1285: `        layers = [` / `            scatterplot_layer(` / `                "v1_ports",` ... / `        await adv_widget.update(session, layers)`
line 750: `        layers = _adv_layers.get()`
```

*Verifier:* Verified: `_adv_init` (def at 736) sets `_adv_layers` and pushes the cargo-column layers; `_v1_layers` (def at 1255) ends at line 1285 with `await adv_widget.update(session, layers)` where layers == [v1_ports] only, and never reads or updates `_adv_layers`. MapWidget.update (map_widget.py:307) builds `payload["layers"] = layers` and sends `deck_update` — a full replace, not a merge (partial_update is the merging variant). Inputs v1_brushing/v1_filter_range exist (_app_ui.py:780/824) and are non-None switches/sliders, so the @reactive.event effect fires at init (ignore_init defaults False) after _adv_init. _apply_lighting (750-766) re-pushes _adv_layers.get(), which never contains v1_ports. Divergent ownership of the same widget's layer list is real and reachable.

### `_demo_data.py:2152` — silently-wrong-data

make_sea_temperature_grid() draws its noise term from a sequential RNG inside a loop that `continue`s past viewport-filtered cells, so the temperature reported for a fixed grid cell changes depending on the `bounds` argument — despite the comment claiming the noise is "seeded by position for consistency".

**Failure scenario.** Verified empirically. `make_sea_temperature_grid(month=5)` returns cell [20.0, 57.0] with temperature_c=15.0. `make_sea_temperature_grid(bounds={"sw":[20.0,57.0],"ne":[24.0,60.0]}, month=5)` returns the same cell with temperature_c=13.1. All 63/63 cells in the bounded result differ from their unbounded values, and `bin_label` and `elevation` (line 2156/2159) shift with them. In the Shiny demo, panning/zooming the map (which changes `bounds`) makes every cell's temperature and legend bin jump, so the same location shows different data on every viewport change.

```
2139: rng = random.Random(42 + month)  # Deterministic per month
2144:        if bounds is not None:
2145:            sw, ne = bounds["sw"], bounds["ne"]
2146:            if not (sw[0] <= lon <= ne[0] and sw[1] <= lat <= ne[1]):
2147:                continue
2151:        # Random noise (seeded by position for consistency)
2152:        noise = rng.gauss(0, 1.5)
```

*Verifier:* Reproduced empirically. _demo_data.py:2139 creates rng=random.Random(42+month) and line 2152 draws rng.gauss(0,1.5) inside the loop AFTER the `continue` at line 2147 that skips out-of-bounds cells, so the noise stream is consumed in filtered order. make_sea_temperature_grid(month=5) vs. the same call with bounds sw=[20,57]/ne=[24,60] gives 63/63 differing temperatures for identical positions (e.g. cell (20.0,57.0): 15.0 vs 13.1), and elevation (2156) and bin_label (2159-2160) shift with them, contradicting the line-2151 comment 'seeded by position for consistency'. Not covered by 08bdf4f (whose 'local seeded RNG in cached factories' fix produced exactly this per-month seed) nor by test_review_fixes.py / test_tooltip_xss.py.

### `_timeline.py:138` — correctness

The `_auto_advance` reactive effect reads `input.step()` (line 138), creating a reactive dependency on the very input it writes via `update_slider` (line 141); the write re-invalidates the effect, which cancels the pending `invalidate_later` timer, so `interval_ms` never governs the animation cadence.

**Failure scenario.** Call `timeline_control("tl", MONTH_LABELS, interval_ms=1000)` + `timeline_server("tl", MONTH_LABELS, interval_ms=1000)` and press Play. The effect reads step=0, schedules a 1 s timer, then sets the slider to 1. The client echoes input.step=1 back, which invalidates the effect's context; py-shiny's `cancel_task` handler (registered at reactive/_core.py:397) cancels the 1 s timer and the effect immediately re-runs and advances again. The documented `interval_ms` parameter therefore has no effect on the frame cadence — the loop period is whatever the client slider round-trip/rate-policy produces. Additionally, a user dragging the scrubber while playing invalidates the same effect and triggers an immediate extra advance.

```
133:        async def _auto_advance():
136:            if not _playing():
137:                return
138:            reactive.invalidate_later(interval_ms / 1000.0)
139:            current = input.step()
140:            next_val = (current + 1) % len(labels)
142:            _ui.update_slider("step", value=next_val, session=inner_session)

shiny/reactive/_core.py:397 ctx.on_invalidate(cancel_task)  -> the invalidate_later timer is cancelled whenever the context is invalidated by another dependency
```

*Verifier:* Confirmed by code plus py-shiny internals. _timeline.py:132-141: the _auto_advance Effect calls reactive.invalidate_later(interval_ms/1000) at line 137, then takes a reactive dependency on input.step() at line 138 and writes that same input via _ui.update_slider('step', ...) at line 141. In the installed py-shiny, reactive/_core.py registers ctx.on_invalidate(cancel_task) for invalidate_later, so when the client echoes the updated slider value back as an input.step change the effect's context invalidates, the pending timer is cancelled, and the effect re-runs and advances again. The cadence is therefore the client round-trip/rate-policy, not interval_ms; dragging the scrubber while playing likewise triggers an immediate extra advance. No guard elsewhere (the _playing() early return at 135-136 only stops the loop when paused), and no timeline test or 08bdf4f change addresses it.

### `_viewport.py:126` — resource-leak

on_viewport_change re-arms reactive.invalidate_later(1.0) on every fallback run, so an app whose map is never panned/zoomed re-runs the loader and re-pushes the whole layer payload to the browser once per second for the entire session.

**Failure scenario.** App does `@on_viewport_change(widget, input, session)` over a query that returns layers, and the user opens the page and never drags or zooms the map (common for a static overview map, or a tab that is opened and left alone). `input[widget.view_state_input_id]()` keeps raising, the else branch runs every time, calls `reactive.invalidate_later(1.0)` again, and one second later the effect re-runs: `fn(bounds, zoom)` re-executes the (possibly expensive) data query and `await widget.update(session, layers)` serialises and pushes the full layer payload over the websocket. This repeats at 1 Hz indefinitely -- unbounded CPU/DB/bandwidth per idle session, and layer state is re-sent (resetting client-side transitions) forever.

```
_viewport.py:392-409:
            if vs is not None and "bounds" in vs:
                bounds = vs["bounds"]
                zoom = vs.get("zoom", 0)
            else:
                # Initial load - use widget's configured view_state
                ...
                zoom = z
                # Re-run when the input becomes available
                reactive.invalidate_later(1.0)

resources/deckgl-init.js:711-726 - the only writer of `<mapId>_view_state`:
    // Send view state back to Shiny on every meaningful camera move
    map.on('moveend', function () { ... Shiny.setInputValue(mapId + '_view_state', {...}); });
The handler is attached after the map is constructed and there is no initial/`load`-time emission, so the input never exists until the user actually moves the camera.
```

*Verifier:* Real and reachable. src/shiny_deckgl/_viewport.py is only 158 lines (cited 409 does not exist); the code is at line 126, inside the else branch of the reactive Effect: `reactive.invalidate_later(1.0)` is re-armed on every fallback run, and `input[widget.view_state_input_id]()` keeps raising until a moveend arrives. Verified the client only ever sets `<id>_view_state` from `map.on('moveend', ...)` (resources/deckgl-init.js:712), registered AFTER the Map constructor, so the constructor's internal jumpTo/resize cannot satisfy it. Checked maplibre-gl 5.24.0 (the pinned MAPLIBRE_VERSION) directly: `_setupResizeObserver` explicitly swallows the initial ResizeObserver callback (`this._resizeObserver = new o((e)=>{ t ? i(e) : t = true; })`), so no resize-driven moveend fires on load. The only other resize path is the `shown.bs.tab` handler (line ~3336), which requires a tab switch. Therefore a map that is never panned/zoomed/resized re-runs fn(bounds, zoom) and re-pushes layers at 1 Hz for the whole session. Not touched by 08bdf4f and not covered by tests/test_review_fixes.py or tests/test_tooltip_xss.py.

### `effects.py:288` — api-contract

post_process_effect() emits a `shaderModule` string that the JS client never resolves; the whole spec dict is passed as deck.gl PostProcessEffect's `module` argument, so post-processing effects never render (and throw in deck.gl).

**Failure scenario.** `await map_widget.update(session, layers=[...], effects=[post_process_effect("vignette", radius=0.5, amount=0.5)])`. The client builds `new deck.PostProcessEffect({type:'PostProcessEffect', shaderModule:'vignette', radius:0.5, amount:0.5})`; deck.gl reads `module.name`/`module.uniforms` off that plain object, gets undefined, and the effect either throws during `setProps`/render or is a silent no-op -- the documented `post_process_effect` API (all 15 shader modules listed at effects.py:254-270) never works. Related sub-defect: even once resolution is added, `PostProcessShader.HEX_PIXELATE = "hexPixelate"` (enums.py:709) does not match the luma.gl module name `hexagonalPixelate` that effects.py:266 itself documents.

```
effects.py:288:
    return {"type": "PostProcessEffect", "shaderModule": shader_module, **kwargs}

resources/deckgl-init.js:1093-1095 (the only consumer; `grep -n shaderModule deckgl-init.js` returns no hits):
      // PostProcessEffect
      if (spec.type === 'PostProcessEffect' && deck.PostProcessEffect) {
        return new deck.PostProcessEffect(spec);
      }
deck.gl 9's signature is `new PostProcessEffect(module: ShaderPass, props?)` -- here the plain spec object `{type, shaderModule, ...params}` is handed in as `module`, and the actual luma.gl shader module named by `shaderModule` is never looked up.
```

*Verifier:* Confirmed at the cited line. effects.py:288 returns {'type':'PostProcessEffect','shaderModule':shader_module, **kwargs}, and the only client handling is deckgl-init.js:1094-1095 `new deck.PostProcessEffect(spec)` — the whole spec dict is passed as deck.gl's `module` argument, with no lookup of `shaderModule` anywhere in the JS (grep for shaderModule/luma effects returns only that spot). deck.gl reads module.name/module.uniforms off the plain object and gets undefined, so the documented 15-module API cannot render. The sub-defect is also real but mis-anchored: PostProcessShader.HEX_PIXELATE = 'hexPixelate' is at enums.py:237 (enums.py has 247 lines, not 709), versus the 'hexagonalPixelate' name the docstring itself lists. Neither is addressed by 08bdf4f or the two named test files.

### `resources/deckgl-init.js:953` — api-contract-violation

The `@@=` accessor whitelist rejects every expression that is not a bare property/index chain, and on rejection leaves the raw `@@=...` string in layerProps, so deck.gl receives a string where it expects an accessor. layers.py documents arithmetic expressions as supported.

**Failure scenario.** `scatterplot_layer("pts", data, getRadius="@@=d.depth_m * 5")` — the exact form advertised in layers.py:18 — fails the regex (the ` * 5` is not matched). The `continue` on line 957 leaves `layerProps.getRadius === "@@=d.depth_m * 5"`, which is then handed to `new deck.ScatterplotLayer(layerProps)` at line 1430. deck.gl treats a non-function accessor as a constant, coerces the string to a number, gets NaN, and the layer renders nothing. The only signal is a console.warn — the Python side reports success. The same applies to `"@@=d.weight || 1"` (used at _app_server.py:1747) and any ternary/arithmetic accessor.

```
deckgl-init.js:951-958
        // Whitelist: only allow safe accessor patterns (property access, array indexing)
        // Matches: d, d.prop, d.a.b.c, d[0], d["key"], d['key'], or combinations
        const SAFE_ACCESSOR_RE = /^d(?:\.[a-zA-Z_$][a-zA-Z0-9_$]*|\[\d+\]|\["[^"]*"\]|\['[^']*'\])*$/;
        if (!SAFE_ACCESSOR_RE.test(expr)) {
          console.warn('[shiny_deckgl] Invalid accessor expression "' + val + '": ' +
            'must match pattern d.prop, d[0], d["key"], etc.');
          continue;
        }

layers.py:16-19
- ``"@@=expr"`` — Expression accessor.  ``expr`` is a **safe** JavaScript
  property/index expression that **must start with ``d``** (the datum),
  e.g. ``"@@=d.position"``, ``"@@=d.color"``, ``"@@=d.depth_m * 5"``.
  The client validates it against a whitelist before evaluating.
```

*Verifier:* Verified at deckgl-init.js:953: SAFE_ACCESSOR_RE is /^d(?:\.[a-zA-Z_$][a-zA-Z0-9_$]*|\[\d+\]|\["[^"]*"\]|\['[^']*'\])*$/, which matches only bare property/index chains; ' * 5' and ' || 1' fail it. On failure line 957 `continue`s, so layerProps[key] keeps the literal '@@=...' string and is passed straight to the deck.gl layer constructor in buildDeckLayers — deck.gl treats a non-function accessor as a constant, giving NaN. Not a hypothetical: the shipped demo at _app_server.py:1747 uses getWeight="@@=d.weight || 1" on a HeatmapLayer, and layers.py:18 documents "@@=d.depth_m * 5" as supported. Commit 08bdf4f touched only the point_cloud/simple_mesh default accessor (@@=position), not this whitelist, and neither tests/test_review_fixes.py nor tests/test_tooltip_xss.py exercises @@= expressions. The rejection itself may be intended security policy, but the doc/demo contract mismatch plus the silent raw-string passthrough is a real defect.

## MEDIUM (11)

### `resources/deckgl-init.js:1959` — race-condition

deck_update has no generation guard around its async SVG-atlas preload, so an older update can resolve last and render stale layers that disagree with instance.lastLayers.

**Failure scenario.** deck_update A arrives carrying a layer with an uncached data:image/svg+xml iconAtlas; rasteriseIconAtlas (line 1522) resolves only after Image.onload, which takes a network/decode tick. 10 ms later deck_update B arrives with no SVG atlas, so its Promise.all([]) at line 1959 resolves on the very next microtask: B builds and calls overlay.setProps first. A's promise then resolves and calls overlay.setProps with its own stale, closed-over layersData, overwriting B. Meanwhile instance.lastLayers was set synchronously at line 1945 and holds B's layers, so the rendered overlay, the legend widget (_refresh at 1946) and the animation scans (1987/1990) all disagree with what the user sees, and nothing corrects it until the next update. deck_partial_update guards exactly this case with instance._partialUpdateGen (lines 2045 and 2058); deck_update simply lacks the equivalent check.

```
instance.lastLayers = layersData;                     // line 1945
Promise.all(svgAtlasPreloads).then(function () {      // line 1959  (no gen check)
  const deckLayers = buildDeckLayers(cloneLayersData(layersData), targetId);
...compare deck_partial_update:
instance._partialUpdateGen = (instance._partialUpdateGen || 0) + 1;  // line 2045
if (partialUpdateGen !== instance._partialUpdateGen) return;         // line 2058
```

*Verifier:* Verified: deck_update sets instance.lastLayers synchronously at 1945 and refreshes the legend at 1946, then defers all rendering into Promise.all(svgAtlasPreloads).then(...) at 1959 with no generation token; the callback closes over layersData and calls overlay.setProps unconditionally. deck_partial_update does exactly the guard the claim describes (instance._partialUpdateGen bumped at 2045, checked with 'if (partialUpdateGen !== instance._partialUpdateGen) return;' at 2058), so the asymmetry is real. Reachable when update A carries an uncached data:image/svg+xml iconAtlas (rasteriseIconAtlas resolves after Image.onload) and a closely following update B has none, so B's Promise.all([]) resolves first; A then overwrites B's render while lastLayers/legend/animation scans hold B.

### `resources/deckgl-init.js:1657` — correctness

Every deck_update / deck_partial_update unconditionally restarts the TripsLayer animation from t=0 and resurrects an explicitly paused animation.

**Failure scenario.** savedPausedAt is read only from instance.tripsAnimation.pausedAt, which pauseTripsAnimation (line 1811) is the only writer of. (a) While an animation is running normally, pausedAt is undefined, so savedPausedAt = 0; startTripsAnimation is called unconditionally at line 1987 (deck_update) and line 2067 (deck_partial_update), so an app that pushes a reactive data refresh once per second pins the trip animation to elapsed ~0-1 s forever — the trails never advance past the first second of the loop, with no error. (b) After the user sends deck_trips_control {action:'pause'}, the next deck_update or deck_partial_update calls startTripsAnimation again, which claims a new generation and schedules a fresh RAF at line 1793 — the animation silently resumes despite the pause, contradicting the deck_trips_control contract. The comment at line 1986 ('Start/stop TripsLayer animation if needed') shows the call was meant to be conditional.

```
var savedPausedAt = (instance.tripsAnimation && instance.tripsAnimation.pausedAt != null)
                    ? instance.tripsAnimation.pausedAt : 0;   // line 1657-1658
var timeOffset = savedPausedAt;                               // line 1713
var startedAt = performance.now();                            // line 1714
// Start/stop TripsLayer animation if needed (v0.9.0)
startTripsAnimation(instance, targetId);                      // lines 1986-1987
startTripsAnimation(instance, targetId);                      // line 2067
```

*Verifier:* Verified: startTripsAnimation (1655) reads savedPausedAt only from instance.tripsAnimation.pausedAt (1657), and pauseTripsAnimation (1801-1812) is its only writer, so during normal running pausedAt is undefined and savedPausedAt = 0 — every deck_update (unconditional call at 1987) and deck_partial_update (2067) restarts the loop at t=0, pinning trails near the loop start under periodic reactive refreshes. Part (b) is the stronger half: pause leaves instance.tripsAnimation alive with pausedAt set (only stopTripsAnimation nulls it), so the next deck_update calls startTripsAnimation, claims a new _tripsAnimGen (so the 1710 gen check passes) and schedules a fresh RAF with timeOffset = pausedAt — the animation silently resumes with no user action, contradicting the deck_trips_control pause contract. No test in tests/test_review_fixes.py touches trips/pause, and 08bdf4f's 'Guard TripsLayer RAF against resurrection via generation token' addresses async-atlas resurrection after a stop/pause, not the unconditional restart from deck_update.

### `layers.py:1127` — correctness

_maybe_encode() imports numpy unconditionally, so custom_geometry() crashes on installs without numpy even when the mesh arrays are plain Python lists (the documented supported input).

**Failure scenario.** On a base install (pip install shiny-deckgl, no [binary] extra), custom_geometry({'positions': [[0.0,0.0,0.0], ...], 'indices': [0,1,2], 'center': [21.1,55.7]}) — plain lists, which the docstring at lines 1152-1161 explicitly says are supported and 'passed through as JSON for backward compatibility' — raises ModuleNotFoundError: No module named 'numpy' on the first _maybe_encode call at line 1195, before any type check. The list path never needs numpy at all; the import should be guarded (try/except ImportError -> return arr, or the module-name check used in _data_utils).

```
layers.py:1125-1132:
def _maybe_encode(arr: Any, dtype: str) -> Any:
    """Encode numpy arrays as binary; pass lists through unchanged."""
    import numpy as np  # noqa: local import — numpy is optional
    if isinstance(arr, np.ndarray):
        ...
    return arr
numpy is only an extra: pyproject.toml:29-32  [project.optional-dependencies] binary = ["numpy"]. The sibling helper deliberately avoids this — _data_utils.py:96-101 type-checks via type(array).__module__ *before* importing numpy, precisely "so a bad input raises the documented TypeError even when numpy is not installed".
```

*Verifier:* Verified. layers.py:1127 does an unconditional `import numpy as np` at the top of _maybe_encode(), before any type check, and custom_geometry() calls it unconditionally at :1195-1198 for positions/normals/colors/indices. pyproject.toml lists only shiny>=1.6.3 and htmltools as dependencies - numpy is in the optional `binary` extra - so a base install has no numpy (nothing else pulls it in; _data_utils.py deliberately avoids importing numpy/pandas at runtime, using an MRO class-name check and a TYPE_CHECKING-only numpy import, which is the guarded pattern this function should follow). The docstring at :1150-1161 states plain lists are supported and passed through as JSON, yet that path raises ModuleNotFoundError before reaching the isinstance check.

### `_app_widgets.py:22` — cross-session-state-leak

MapWidget instances are module-level singletons whose mutable `style` is written by one session's basemap switch and read by another session's HTML/JSON export.

**Failure scenario.** Two users connect concurrently. User A changes Tab 1's basemap select -> `_switch_basemap` (_app_server.py:205) calls `gallery_widget.set_style(...)`, which mutates the shared instance attribute `self.style` (map_widget.py:711). User B then clicks 'Export HTML' (_app_server.py:1049) or 'Export JSON' (1063); `to_html` embeds `self.style` at map_widget.py:2115 (`data-style="{_html_mod.escape(self.style)}"`) and `to_json` at 2002 (`"style": self.style`). B's exported file therefore carries A's basemap even though B's own dropdown and on-screen map show a different one -- silently wrong output with no error. The same singleton pattern applies to all 11 widgets (lines 22-135) and to `update_tooltip`/`set_cooperative_gestures`, which mutate `self.tooltip` (map_widget.py:734) and `self.cooperative_gestures` (547) globally.

```
_app_widgets.py:22-33: `gallery_widget = MapWidget(` / `    "gallery_map",` ... `    view_state=BALTIC_VIEW,` / `    controls=[],` / `)`  (module scope, evaluated once at import)
_app_server.py:204-205: `        style_url = BASEMAP_CHOICES.get(input.basemap(), CARTO_POSITRON)` / `        await gallery_widget.set_style(session, style_url)`
map_widget.py:711: `        self.style = style`
map_widget.py:2115: `     data-style="{_html_mod.escape(self.style)}"`
map_widget.py:2002: `            "style": self.style,`
```

*Verifier:* Verified: _app_widgets.py defines all 11 MapWidget instances at module scope (gallery_widget at line 22), imported by both _app_ui.py and _app_server.py, so they are process-wide singletons shared by every session. set_style (map_widget.py, `self.style = style` at 711) mutates instance state, and to_json (`"style": self.style`, ~2002) and to_html (`data-style="{...self.style}"`, ~2115) read it; _switch_basemap (_app_server.py:205) calls it per-session. update_tooltip (734) and cooperative-gesture state are likewise mutated globally. Manifests only with concurrent sessions, which is why MEDIUM is the right severity, but the module docstring only justifies sharing between UI and server within a process — not cross-session mutation. Not fixed or tested.

### `_sealmove.py:40` — correctness

normalize_rows() claims to handle zero rows but replaces the zero denominator with 1.0, leaving the row as all zeros; simulate_IHTR then passes that row to rng.choice(p=...) and crashes.

**Failure scenario.** Verified empirically. `simulate_IHTR(IHTRConfig(P=np.array([[0.,0.,0.],[0.1,0.8,0.1],[0.05,0.15,0.8]]), n_agents=10, T=5), random_state=1)` raises `ValueError: Probabilities do not sum to 1.` at line 133, because `normalize_rows` returns `[0., 0., 0.]` (sum 0.0) for row 0 and the uniform initial distribution places agents in state 0. A transition matrix with an unreachable/absorbing-free cluster row (a realistic output of estimating I-HTR rates from telemetry where one cluster has no observed departures) crashes the simulator instead of being handled.

```
36: def normalize_rows(M: np.ndarray) -> np.ndarray:
37:     """Normalize rows to sum to 1 (handling zero rows)."""
39:     rowsums = M.sum(axis=1, keepdims=True)
40:     rowsums[rowsums == 0] = 1.0
41:     return np.asarray(M / rowsums)
133:                new_states[mask] = rng.choice(K, size=count, p=P[k])
```

*Verifier:* Confirmed empirically. _sealmove.py:38-41 sets rowsums[rowsums==0]=1.0, so an all-zero row is returned as all zeros despite the line-37 docstring claiming it handles zero rows; simulate_IHTR normalizes at line 103 and feeds P[k] to rng.choice at line 133. Running simulate_IHTR(IHTRConfig(P=[[0,0,0],[.1,.8,.1],[.05,.15,.8]], n_agents=10, T=5), random_state=1) raises ValueError: Probabilities do not sum to 1. IHTRConfig performs no validation, so any caller-supplied matrix with an unobserved row reaches the crash. Weakest point is that only tests currently call it with valid matrices, but the docstring contract is plainly violated.

### `_demo_data.py:1892` — correctness

make_lithuanian_bathymetry_data() uses four `.parent` hops from `src/shiny_deckgl/_demo_data.py`, resolving to the directory ABOVE the repo root instead of the repo root, so the bundled `bathy.asc` is never found and the function silently returns an empty list.

**Failure scenario.** `bathy.asc` exists at the repo root (confirmed by glob). From `src/shiny_deckgl/_demo_data.py`, `.parent`x4 = `<repo root>/..`, so the first `exists()` check fails. The fallback `Path("bathy.asc")` is cwd-relative, so whenever the app is launched from anywhere other than the repo root (e.g. `python examples/app.py` run from a parent directory, or any installed-package deployment), the function returns `[]` and the Lithuanian bathymetry GridCellLayer renders nothing — with no error or warning. Because it is `@lru_cache(maxsize=8)`, the empty result is then cached for the process lifetime.

```
1891:    # Look for bathy.asc in project root
1892:    asc_path = Path(__file__).parent.parent.parent.parent / "bathy.asc"
1895:        asc_path = Path("bathy.asc")
1898:        return []  # Return empty if file not found

(compare line 1419, which correctly reaches the repo root with three hops:)
1419: _EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
```

*Verifier:* Confirmed by path arithmetic. The file is src/shiny_deckgl/_demo_data.py, so Path(__file__).parent.parent.parent.parent at line 1892 resolves to the directory ABOVE the repo root (parent=shiny_deckgl, x2=src, x3=repo root, x4=above), and bathy.asc exists only at the repo root (verified: no bathy.asc one level up). The comment on line 1891 says 'Look for bathy.asc in project root', so the intent is clear and the hop count is off by one. My successful run (15426 cells) only worked via the cwd-relative fallback Path('bathy.asc') at line 1895 because cwd happened to be the repo root; from any other cwd the function returns [] silently and, being @lru_cache'd (line 1881), caches the empty result. Not touched by 08bdf4f or the regression tests.

### `_demo_data.py:1290` — numerical-correctness

make_seal_trips_ibm() adds an isotropic displacement in degrees to both lon and lat, mixing degree and metric units: the docstring calibrates SPEED_MAX against a km/h swim speed, but equal degree steps mean ~1.9x more real distance north-south than east-west at Baltic latitudes. The sibling make_seal_trips() applies a 0.6 latitude factor at line 891; the IBM does not.

**Failure scenario.** A Harbour seal (speed_scale=1.0) at 58°N moving due east is capped at 0.06° lon/h = 0.06 x 111.32 x cos(58°) ≈ 3.5 km/h, while the same seal moving due north gets 0.06 x 111.32 ≈ 6.7 km/h — half vs. the full documented 5–7 km/h. The diffusive component at line 1290 is likewise anisotropic, so simulated tracks are systematically stretched north-south, and derived foraging-trip extents and haul-out choice distances (line 1329, computed as a plain Euclidean norm over mixed lon/lat degrees) inherit the same distortion.

```
1198:    # Typical seal swim speed: 5–7 km/h ≈ 0.05° lat/h
1199:    SPEED_MAX = 0.06          # max displacement per step (degrees)
1200:    DIFFUSIVE_SIGMA = 0.018   # random movement component
1290:                    rng.normal(0, DIFFUSIVE_SIGMA * a.speed_scale, size=2)
1293:                speed_lim = SPEED_MAX * a.speed_scale
1296:                    step = step / L * speed_lim

(sibling function applies the correction:)
891:            new_lat = lat + step_size * math.sin(heading) * 0.6 * rng.uniform(0.7, 1.3)
```

*Verifier:* Confirmed. The docstring at 1115-1126 explicitly presents this as a mechanistic McConnell-style IBM, and the comment at line 1198 calibrates 'Typical seal swim speed: 5-7 km/h ~ 0.05 deg lat/h' before SPEED_MAX=0.06 (line 1199) is applied isotropically: the diffusive draw at line 1290 is rng.normal(0, DIFFUSIVE_SIGMA*speed_scale, size=2) over both lon and lat, and the cap at 1293-1296 uses a plain Euclidean norm over mixed degree axes. At 58N one degree of longitude is ~0.53 of a degree of latitude in km, so eastward motion tops out near 3.5 km/h against ~6.7 km/h northward, stretching tracks north-south; the haul-out distance computation at 1329-1330 inherits the same mixed-unit norm. The sibling make_seal_trips applies an explicit 0.6 latitude factor at lines 891 and 901, showing the correction was applied elsewhere and simply omitted here, so this is a modelling inconsistency rather than a style opinion.

### `enums.py:62` — enum-mismatch

9 of the 13 EasingFunction values have no counterpart in the JS EASINGS table and silently degrade to linear instead of erroring.

**Failure scenario.** `transitions={"getRadius": transition(800, easing=EasingFunction.EASE_IN_OUT_QUAD)}` serialises `@@easing: "ease-in-out-quad"`; the JS lookup misses, falls through to the `|| function(t){return t}` identity, and the animation plays perfectly linearly with no warning. The developer sees a working transition and cannot tell that their chosen easing was discarded. Same for LINEAR, both SINE-in/out values, both remaining QUAD values, and all three EXPO values.

```
enums.py:539-551 defines LINEAR="linear", EASE_IN_SINE="ease-in-sine", EASE_OUT_SINE="ease-out-sine", EASE_IN_QUAD/EASE_OUT_QUAD/EASE_IN_OUT_QUAD, EASE_IN_EXPO/EASE_OUT_EXPO/EASE_IN_OUT_EXPO, ...

resources/deckgl-init.js:1152-1157 -- the complete table:
  const EASINGS = {
    'ease-in-cubic': ..., 'ease-out-cubic': ...,
    'ease-in-out-cubic': ..., 'ease-in-out-sine': ...
  };
resources/deckgl-init.js:1220:
    tSpec.easing = EASINGS[tSpec['@@easing']] || function(t) { return t; };
A Python-wide grep for `easing` shows `_transitions.transition()` is the only producer of `@@easing`, so nothing else (no camera/fly-to path) consumes these names either -- contradicting the enum docstring "Easing functions for camera transitions".
```

*Verifier:* Real mismatch, wrong line: EasingFunction is at enums.py:62-79 (file is 247 lines; 539 does not exist). It defines 13 values; the JS EASINGS table (deckgl-init.js:1152-1157) has only 4 (ease-in-cubic, ease-out-cubic, ease-in-out-cubic, ease-in-out-sine), and the resolver at line 1220 falls back to the identity function with no warning. Verified there is no Python-side whitelist: _transitions.py:40-41 writes `@@easing` verbatim with no validation (its docstring even documents only the same 4 names), so `transition(800, easing=EasingFunction.EASE_IN_OUT_QUAD)` does serialise and silently degrade. One nuance: LINEAR degrading to the identity is harmless, so the count of harmful silent misses is 8 of 13, not 9. Not fixed in 08bdf4f.

### `colors.py:211` — correctness

color_quantiles uses `v <= break` against breakpoints that are the first element of each upper quantile, so every bin boundary value is pushed one bin down and the top color is never emitted.

**Failure scenario.** `color_quantiles([1,2,3,4,5,6], n_bins=6)` -> breaks = [2,3,4,5,6]; values 1 and 2 both map to bin 0, 3->1, 4->2, 5->3, 6->4, and bin 5 (the darkest/brightest palette stop) is never used. With 6 equally-spaced values in 6 quantile bins the map is off by one everywhere and one sixth of the palette is dead, so a legend built from `color_range(6, palette)` does not match the colors actually drawn -- silently wrong data-to-color mapping.

```
colors.py:204-215:
    breaks = [
        sorted_vals[min(int(i / n_bins * n), n - 1)]
        for i in range(1, n_bins)
    ]

    def _bin(v: float) -> int:
        for i, br in enumerate(breaks):
            if v <= br:
                return i
        return n_bins - 1

    return [colors[_bin(v)] for v in values]
`sorted_vals[int(i/n_bins*n)]` is the *lowest* member of quantile i, so `v <= br` classifies it into bin i-1. The correct test for this breakpoint definition is `v < br`.
```

*Verifier:* Confirmed at colors.py:211 (`if v <= br`). Breaks are built at line 204-207 as sorted_vals[int(i/n_bins*n)], i.e. the FIRST element of each upper quantile, and comparing with <= claims that boundary value for the lower bin. Traced the stated example: color_quantiles([1,2,3,4,5,6], n_bins=6) -> breaks [2,3,4,5,6]; 1 and 2 -> bin 0, 3->1, 4->2, 5->3, 6->4, bin 5 never emitted, so a legend built from color_range(6, palette) disagrees with the drawn colors. Precision note on the claim's generality: the boundary-off-by-one holds for all n, but the top bin is dropped only when the last break equals max (small n relative to n_bins); for e.g. n=100/n_bins=4 the top bin is still reached. No test pins the current behaviour (tests/test_basic.py:536-551 and 2078-2105 only assert counts/tuple shape/uniform-value equality), so it is not intended behaviour, and 08bdf4f did not touch colors.py.

### `resources/deckgl-init.js:1111` — api-contract-violation

buildViews resolves view classes with a bare `deck[typeName]` lookup and no underscore fallback, but deck.gl 9.x exports GlobeView as `deck._GlobeView`, so the `"GlobeView"` string that views.py/enums.py emit never resolves.

**Failure scenario.** `await widget.update(session, layers, views=[globe_view()])` sends `{"@@type": "GlobeView"}`. At line 1111 `deck["GlobeView"]` is `undefined` (the UMD bundle exposes `deck._GlobeView`), so the view is dropped by the `.filter(v => v !== null)` on line 1117, `buildViews` returns an empty array, `overlayProps.views` is never set (line 1971-1972), and the map silently keeps the default MapView. Only a console warning is emitted. The same lookup works for MapView/OrbitView/OrthographicView/FirstPersonView, so the failure is specific to the one view type that deck.gl marks experimental.

```
deckgl-init.js:1108-1116
      const typeName = spec['@@type'] || 'MapView';
      ...
      const ViewClass = deck[typeName];
      if (!ViewClass) {
        console.warn('[shiny_deckgl] Unknown view type: ' + typeName);
        return null;
      }

enums.py:211
    GLOBE = "GlobeView"

Compare the sibling resolvers, which DO have the fallback:
deckgl-init.js:1140  const Cls = deck[className] || deck['_' + className];
deckgl-init.js:1282  const LayerClass = deck[layerProps.type] || deck['_' + layerProps.type];

deck.gl 9.x public API (confirmed via deck.gl docs, api-reference/core/globe-view.md):
  import {_GlobeView as GlobeView} from '@deck.gl/core';
  new deck._GlobeView()
```

*Verifier:* Verified at deckgl-init.js:1111: `const ViewClass = deck[typeName];` with no underscore fallback (contrast buildWidgets line 1140, which does `deck[className] || deck['_' + className]`). views.py:44 and enums.py:211 both emit the string "GlobeView". The pinned bundle is deck.gl@9.3.6 UMD (_cdn.py:10); deck.gl's own scripting example for that bundle uses `new deck._GlobeView()`, i.e. the UMD global exposes _GlobeView, not GlobeView. So the lookup yields undefined, the view is dropped by .filter(v => v !== null) at 1117, buildViews returns [] which is falsy-length-wise only via `if (views)` — an empty array is truthy, so overlayProps.views = [] is set; either way the GlobeView never reaches deck.gl and only a console.warn is emitted. Not covered by 08bdf4f or the two test files.

### `resources/deckgl-init.js:1152` — enum-mismatch

The JS EASINGS table implements only 4 of the 13 easing names published by the public `EasingFunction` enum; the other 9 silently fall back to an identity (linear) function with no warning.

**Failure scenario.** `transitions={"getRadius": transition(800, easing=EasingFunction.EASE_IN_EXPO)}` sends `{"@@easing": "ease-in-expo"}`. `EASINGS["ease-in-expo"]` is undefined, so line 1220 installs `function(t){return t;}` and the property animates linearly. Nine of the thirteen enum members (ease-in-sine, ease-out-sine, ease-in-quad, ease-out-quad, ease-in-out-quad, ease-in-expo, ease-out-expo, ease-in-out-expo, and linear-by-accident) behave identically to each other with no console warning, so a typo like "ease-in-cubick" is equally invisible. The enum docstring at enums.py:65 claims 'These map to d3-ease functions in the JavaScript client', but no d3-ease is loaded.

```
deckgl-init.js:1152-1157
  const EASINGS = {
    'ease-in-cubic': function(t) { return t * t * t; },
    'ease-out-cubic': function(t) { return 1 - Math.pow(1 - t, 3); },
    'ease-in-out-cubic': function(t) { return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; },
    'ease-in-out-sine': function(t) { return -(Math.cos(Math.PI * t) - 1) / 2; }
  };

deckgl-init.js:1219-1221
          if (tSpec && tSpec['@@easing']) {
            tSpec.easing = EASINGS[tSpec['@@easing']] || function(t) { return t; };
            delete tSpec['@@easing'];

enums.py:67-79 (all exported via __init__.py:262/436)
    LINEAR = "linear"
    EASE_IN_CUBIC = "ease-in-cubic"
    EASE_OUT_CUBIC = "ease-out-cubic"
    EASE_IN_OUT_CUBIC = "ease-in-out-cubic"
    EASE_IN_SINE = "ease-in-sine"
    EASE_OUT_SINE = "ease-out-sine"
    EASE_IN_OUT_SINE = "ease-in-out-sine"
    EASE_IN_QUAD = "ease-in-quad"
    EASE_OUT_QUAD = "ease-out-quad"
    EASE_IN_OUT_QUAD = "ease-in-out-quad"
    EASE_IN_EXPO = "ease-in-expo"
    EASE_OUT_EXPO = "ease-out-expo"
    EASE_IN_OUT_EXPO = "ease-in-out-expo"
```

*Verifier:* Verified: EASINGS at deckgl-init.js:1152 defines exactly 4 entries (ease-in-cubic, ease-out-cubic, ease-in-out-cubic, ease-in-out-sine), while EasingFunction in enums.py:62-77 publishes 13 names; _transitions.py:41 emits the raw enum string as '@@easing'. Line 1220 does `tSpec.easing = EASINGS[tSpec['@@easing']] || function(t){return t;}` — unknown names (including typos) silently become identity with no warning. No d3-ease is loaded anywhere (only deck.gl/maplibre/h3 in _cdn.py), so the enum docstring claim is also false. Note the claim slightly overstates one item: 'linear' mapping to identity is coincidentally correct behaviour, so 8 of 9 are actually wrong — the defect stands.

## LOW (2)

### `_app_server.py:1810` — reactivity

`_wg_init` reads inputs without reactive.isolate(), so it becomes a duplicate of _wg_update_map and every widget toggle sends two identical full map updates.

**Failure scenario.** `_wg_init` is a bare `@reactive.Effect` that calls `_wg_active_widgets()` and `_wg_layers()`, both of which read ~20 `input.wg_*` values (lines 1631-1699, 1704-1780). Those reads register `_wg_init` as a dependent of every one of them, so flipping e.g. `wg_fps` re-runs BOTH `_wg_init` and `_wg_update_map` (line 1832), sending two full `deck_update` payloads for the same state change and doubling the layer-rebuild cost on every toggle; the ordering of the two pushes is not guaranteed. This is the exact pattern the file explicitly guards against elsewhere -- `_ml_init` (line 287) and `_gl_init` (line 2453) wrap their input reads in `with reactive.isolate():` with comments saying the effect must not re-fire on toggles. `_wg_init` is also fully redundant, since `_wg_update_map` uses the default `ignore_init=False` and already fires once at session start.

```
line 1808-1816: `    @reactive.Effect` / `    async def _wg_init():` / `        """Send initial widget + layer state on session start."""` / `        widgets = _wg_active_widgets()` / `        layers = _wg_layers()` / `        await widgets_gallery_widget.update(` / `            session, layers, widgets=widgets,` / `        )`
line 285-288 (the guarded pattern): `        # Isolate the control-toggle reads so this init effect does NOT become` / `        # reactive on every ml_* switch ...` / `        with reactive.isolate():` / `            controls = _build_ml_controls()`
```

*Verifier:* Verified: `_wg_init` is a bare `@reactive.Effect` at line 1810 (decorator at 1809) whose body calls `_wg_active_widgets()` (a @reactive.Calc at 1644 that reads all input.wg_* switches) and `_wg_layers()` (@reactive.Calc at 1728), with no reactive.isolate() — the only two isolate() uses in the file are at 287 (_ml_init) and 2462 (_gl_init), both with comments explaining that an init effect must not re-fire on toggles. Dependencies propagate through reactive.Calc, so _wg_init re-runs on every wg_* change alongside _wg_update_map (1831), which has @reactive.event over the same inputs and ignore_init=False, making _wg_init redundant even at startup. Duplicate full deck_update payloads with unspecified ordering; real, though LOW impact.

### `resources/deckgl-init.js:1931` — silently-wrong-data

deck_update substitutes hard-coded defaults (zoom 1, pitch 0, bearing 0) for view-state keys the Python side omitted, so a partial `view_state` passed to `update()` resets the camera instead of leaving those axes alone.

**Failure scenario.** The user has panned/zoomed to zoom 12 and calls `await widget.update(session, layers, view_state={"pitch": 45})` to tilt the camera. Because `vs.longitude`/`vs.latitude`/`vs.zoom` are absent, line 1930-1931 builds `{center: [0, 0], zoom: 1, pitch: 45, bearing: 0}` and `map.jumpTo` teleports the map to null island at world zoom. The same call shape through `fly_to()` behaves correctly, so the two code paths disagree on the meaning of a partial view state.

```
deckgl-init.js:1927-1940
    if (payload.viewState) {
      const vs = payload.viewState;
      const opts = {
        center: [vs.longitude != null ? vs.longitude : 0, vs.latitude != null ? vs.latitude : 0],
        zoom: vs.zoom != null ? vs.zoom : 1,
        pitch: vs.pitch != null ? vs.pitch : 0,
        bearing: vs.bearing != null ? vs.bearing : 0
      };
      ...
        map.jumpTo(opts);

Contrast deck_fly_to, which omits absent keys so MapLibre keeps the current value:
deckgl-init.js:2129-2131
    if (vs.zoom != null) opts.zoom = vs.zoom;
    if (vs.pitch != null) opts.pitch = vs.pitch;
    if (vs.bearing != null) opts.bearing = vs.bearing;

_types.py:52-62 declares ViewState as `TypedDict, total=False` — every key optional.
```

*Verifier:* Verified at deckgl-init.js:1928-1934 (the cited 1930-1931 is inside this block): deck_update builds `{center: [vs.longitude ?? 0, vs.latitude ?? 0], zoom: vs.zoom ?? 1, pitch: vs.pitch ?? 0, bearing: vs.bearing ?? 0}` and calls map.jumpTo/flyTo with it, so a partial view_state resets omitted axes and recenters on [0,0]. MapLibre's CameraOptions accept partial input, and the sibling handlers deck_fly_to (2129-2131) and deck_ease_to (2148-2150) only set zoom/pitch/bearing when present — the author's own intended semantics for absent keys — so the two paths genuinely disagree. map_widget.update() passes view_state through verbatim with no merge or completion. Low impact (a complete view_state is the normal usage) but a real, reachable inconsistency, untouched by 08bdf4f and untested.
