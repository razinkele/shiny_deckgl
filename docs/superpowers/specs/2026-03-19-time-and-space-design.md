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

**`on_viewport_change()` decorator:**

```python
@widget.on_viewport_change(session, debounce_ms=300)
async def load_data(bounds, zoom):
    """bounds = {sw: [lng, lat], ne: [lng, lat]}"""
    filtered = [p for p in all_points if in_bounds(p, bounds)]
    return [scatterplot_layer("visible_pts", filtered)]
```

- Listens to existing `view_state_input_id` (already sends `bounds.sw`/`bounds.ne` on MapLibre `moveend`)
- Debounces via Shiny reactive patterns
- Calls user function with `(bounds_dict, zoom_level)`
- Automatically calls `widget.update(session, returned_layers)`
- No JavaScript changes needed

**`in_bounds()` helper:**

```python
def in_bounds(point: dict, bounds: dict) -> bool:
    """Check if a {lon, lat} point falls within viewport bounds."""
```

Exported as public API from the package.

### Design decisions

- **No JS changes** — the `moveend` handler already sends bounds in the `_view_state` input
- **Decorator pattern** — matches Shiny's `@reactive.Effect` style, feels native
- **Returns layers** — the decorator calls `widget.update()` with the returned list, keeping the user's callback pure (data in → layers out)
- **Debounce** — 300ms default prevents excessive server calls during continuous panning

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
- Slider mapped to label index (1 to len(labels))
- Current label display

**`timeline_server()` — server wiring:**

```python
def timeline_server(id: str) -> SimpleNamespace:
    """Returns .index() and .label() reactive accessors."""
```

- `.index()` — current 0-based step index
- `.label()` — current label string (e.g., "March")
- Play button starts a `reactive.Timer` that auto-advances the slider
- Pause stops the timer
- Wraps around at the end

### Design decisions

- **Follows existing `trips_animation_ui/server` pattern** from `ibm.py` — same module-based approach
- **Generic** — works with any list of labels (months, years, hours, etc.)
- **Composes with viewport loading** — timeline reactive change triggers `on_viewport_change` to re-fetch data for new timestep

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
tl = timeline_server("ts_timeline")

@timespace_widget.on_viewport_change(session, debounce_ms=300)
async def _ts_layers(bounds, zoom):
    month_idx = tl.index()
    data = make_sea_temperature_grid(bounds=bounds, month=month_idx)
    layers = [grid_cell_layer("temps", data, ...)]
    if input.ts_show_ports():
        layers.append(scatterplot_layer("ts_ports", PORTS, ...))
    return layers
```

Timeline step changes invalidate the reactive, triggering a re-fetch with the same viewport but new month.

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

## Scope boundaries

- No new deck.gl layer types
- No changes to core `MapWidget` class
- No changes to JavaScript frontend
- No external data dependencies (all synthetic)
