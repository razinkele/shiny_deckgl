# Time & Space — Viewport-Aware Loading + Time-Series Animation

**Date:** 2026-03-19
**Status:** Design approved
**Version target:** 1.9.0

## Summary

Add two new library capabilities and a demo tab showcasing them together:

1. **Viewport-aware lazy data loading** — server-side callback that receives current viewport bounds and returns filtered layers
2. **Time-series animation** — generic timeline UI control + server wiring for stepping through temporal data
3. **Demo Tab 11: "Time & Space"** — Baltic Sea surface temperature grid animated across 12 months, loading only visible data

## Feature 1: Viewport-Aware Data Loading

### New module: `_viewport.py`

**`on_viewport_change()` — standalone function (not a MapWidget method):**

```python
from shiny_deckgl import on_viewport_change, in_bounds

on_viewport_change(widget, input, session, debounce_ms=300)(load_data)

# Or as a decorator:
@on_viewport_change(widget, input, session, debounce_ms=300)
async def load_data(bounds, zoom):
    """bounds = {sw: [lng, lat], ne: [lng, lat]}"""
    filtered = [p for p in all_points if in_bounds(p, bounds)]
    return [scatterplot_layer("visible_pts", filtered)]
```

- Standalone function in `_viewport.py` — takes `widget`, `input`, and `session` as arguments
- Does NOT modify `MapWidget` class — no changes to `map_widget.py`
- Listens to existing `view_state_input_id` (already sends `bounds.sw`/`bounds.ne` on MapLibre `moveend`)
- Implemented as a `@reactive.Effect` internally, so any reactive values read inside the callback (e.g., `tl.index()`) automatically become dependencies — this is how timeline changes trigger re-fetches
- **Initial load:** fires once on session start using the widget's `view_state` as initial bounds (before any `moveend` event), so the map is never empty
- **Race conditions:** uses last-write-wins — each invocation stores a generation counter; if a newer call starts before an older one finishes, the older result is discarded
- Calls user function with `(bounds_dict, zoom_level)`
- Automatically calls `widget.update(session, returned_layers)`
- No JavaScript changes needed

**`in_bounds()` helper:**

```python
def in_bounds(point: dict, bounds: dict) -> bool:
    """Check if a point's {lon, lat} or [lon, lat] position falls within viewport bounds.

    Note: checks the point center only, not area. Grid cells whose center is
    outside the viewport but whose area overlaps will be excluded.
    """
```

Exported as public API from the package.

### Design decisions

- **Standalone function, not a method** — avoids modifying `map_widget.py`, keeps the core class stable
- **No JS changes** — the `moveend` handler already sends bounds in the `_view_state` input
- **Reactive.Effect internally** — reading any reactive value inside the callback (like `tl.index()`) creates an automatic dependency, so the callback re-fires when those values change (not just on viewport moves). This is the mechanism that connects the timeline to viewport loading.
- **Initial load** — on first call, if no `_view_state` input exists yet, uses `widget.view_state` to derive initial bounds and fires immediately
- **Returns layers** — the decorator calls `widget.update()` with the returned list, keeping the user's callback pure (data in → layers out)
- **Debounce** — 300ms default prevents excessive server calls during continuous panning
- **Last-write-wins** — generation counter prevents stale async results from overwriting fresh ones
- **Empty results** — returning `[]` calls `widget.update(session, [])` which clears all layers (this is existing `update()` behavior)

## Feature 2: Time-Series Animation

### New module: `_timeline.py`

**`timeline_control()` — sidebar UI widget:**

```python
def timeline_control(
    id: str,
    labels: list[str],          # e.g., ["Jan", "Feb", ..., "Dec"]
    interval_ms: int = 1000,    # ms between frames during playback
) -> ui.Tag:
```

Returns Shiny UI elements:
- Play/Pause toggle button
- Slider mapped to label index (0 to len(labels)-1), displayed with label text
- Current label display

**`timeline_server()` — server wiring:**

```python
def timeline_server(id: str, labels: list[str]) -> SimpleNamespace:
    """Returns .index() and .label() reactive accessors."""
```

- `.index()` — current 0-based step index (slider is 0-based internally; displayed label is 1-indexed for UX)
- `.label()` — current label string (e.g., "March")
- Play button starts a `reactive.Timer` that auto-advances the slider
- Pause stops the timer
- Wraps around at the end

Note: unlike `trips_animation_server(id, *, widget, session)`, `timeline_server` does NOT take `widget` or `session` because it does not directly control a widget — it only exposes reactive values. The caller wires these into their own layer-building logic. This is intentional: the timeline is a generic data selector, not a widget controller.

### Design decisions

- **Follows existing `trips_animation_ui/server` pattern** from `ibm.py` — same Shiny module-based approach
- **Slider indexing** — slider `min=0, max=len(labels)-1`, displayed with label text. `.index()` returns the raw 0-based value. No off-by-one conversion needed.
- **Generic** — works with any list of labels (months, years, hours, etc.)
- **Composes with viewport loading** — timeline reactive change triggers `on_viewport_change` to re-fetch data for new timestep (via Shiny's reactive dependency graph — reading `tl.index()` inside the viewport callback creates the dependency automatically)

## Feature 3: Demo Tab 11 — "Time & Space"

### Demo data: `make_sea_temperature_grid()`

Added to `_demo_data.py`:

```python
def make_sea_temperature_grid(
    bounds: dict | None = None,
    month: int = 0,
) -> list[dict]:
```

- Generates ~500 synthetic grid cells covering the Baltic Sea
- Spatial filtering: returns only cells within `bounds` when provided
- Seasonal model: sinusoidal cycle (2°C Feb → 18°C Aug)
- Latitude gradient: -0.5°C per degree north
- Random noise: ±1.5°C per cell (seeded for consistency)
- Returns dicts with: `position`, `temperature_c`, `name`, `month_label`, `bin_label`

### Tab layout

**Sidebar:**
- `timeline_control("ts_timeline", labels=["Jan", ..., "Dec"])` — month scrubber
- Info card: current month, viewport bounds, visible point count
- Color palette selector
- Toggle: show port reference markers

**Map:**
- `grid_cell_layer` — temperature cells colored by `PALETTE_THERMAL`
- Optional `scatterplot_layer` — Baltic ports for reference
- `layer_legend_widget()` — auto-updating temperature legend

**Widget instance:**

```python
timespace_widget = MapWidget(
    "timespace_map",
    tooltip={
        "html": "<b>{name}</b><br/>Temp: {temperature_c}°C<br/>Month: {month_label}",
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
)
```

### Server logic

```python
tl = timeline_server("ts_timeline", labels=MONTH_LABELS)

@on_viewport_change(timespace_widget, input, session, debounce_ms=300)
async def _ts_layers(bounds, zoom):
    month_idx = tl.index()
    data = make_sea_temperature_grid(bounds=bounds, month=month_idx)
    layers = [grid_cell_layer("temps", data, ...)]
    if input.ts_show_ports():
        layers.append(scatterplot_layer("ts_ports", PORTS, ...))
    return layers
```

Timeline step changes invalidate the reactive (because `tl.index()` is read inside the `@reactive.Effect`), triggering a re-fetch with the same viewport but new month. `PORTS` and `BALTIC_VIEW` are existing constants from `_demo_data.py`.

## Files

### New files
| File | Purpose |
|------|---------|
| `src/shiny_deckgl/_viewport.py` | `on_viewport_change()` decorator, `in_bounds()` helper |
| `src/shiny_deckgl/_timeline.py` | `timeline_control()` UI, `timeline_server()` wiring |

### Modified files
| File | Changes |
|------|---------|
| `src/shiny_deckgl/__init__.py` | Export `on_viewport_change`, `in_bounds`, `timeline_control`, `timeline_server` |
| `src/shiny_deckgl/_demo_data.py` | Add `make_sea_temperature_grid()` |
| `src/shiny_deckgl/_app_widgets.py` | Add `timespace_widget` |
| `src/shiny_deckgl/_app_ui.py` | Add Tab 11 UI |
| `src/shiny_deckgl/_app_server.py` | Add Tab 11 server logic |
| `tests/test_basic.py` | Tests for `_viewport.py` and `_timeline.py` |

### Not modified
- `map_widget.py` — decorator lives externally, wraps existing reactive inputs
- `deckgl-init.js` — no new JS needed, bounds already sent via `moveend`

## Testing strategy

**Unit tests (no Shiny session needed):**
- `in_bounds()` — boundary cases, antimeridian, point formats
- `make_sea_temperature_grid()` — output shape, filtering, month range
- `timeline_control()` — returns valid UI tags with correct IDs
- `on_viewport_change()` — constructor validation (bad debounce values, missing args)

**Integration tests (mock Shiny session):**
- Not attempted in this iteration. The async reactive wiring (`on_viewport_change` with `reactive.Effect`) requires a running Shiny app context. The existing test suite (`test_basic.py`) follows a unit-test-only pattern — we match that.

## Scope boundaries

- No new deck.gl layer types
- No changes to core `MapWidget` class
- No changes to JavaScript frontend
- No external data dependencies (all synthetic)
