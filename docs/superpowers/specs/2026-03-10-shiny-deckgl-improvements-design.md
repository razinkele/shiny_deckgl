# shiny-deckgl Improvements — Design Spec

**Date:** 2026-03-10
**Source:** `docs/2026-03-10-shiny-deckgl-improvements.md`
**Approach:** Incremental (A) — each improvement independently testable, shipped in priority order

---

## 1. Document `partial_update` Performance Pattern

**Scope:** Documentation only — zero code changes.

**Changes:**
- `map_widget.py`: Augment existing docstrings on `update()` and `partial_update()` with performance guidance and cross-references. `partial_update()` already documents merge-by-ID behavior — add "when to use" guidance and examples. Also reference `patch_layer()` as the single-layer convenience wrapper.
- `README.md`: Add "Performance Patterns" section with the static/dynamic layer split pattern
- `docs/performance-patterns.md`: Full guide with comparison table (`update()` vs `partial_update()` vs `patch_layer()` vs `set_layer_visibility()`)

**Key message:** For apps with large static datasets and fast-updating dynamic data, `partial_update()` reduces serialization cost by 80-90% because it only serializes the layers you pass and merges by ID on the JS side.

---

## 2. Pre-Built Color Ramp Constants

**Scope:** `colors.py` additions + `__init__.py` exports.

**Existing palettes** (already in `colors.py`, only need aliases):
- `PALETTE_VIRIDIS` — alias: `VIRIDIS`
- `PALETTE_OCEAN` — alias: `OCEAN_DEPTH`

**New palettes** (6-stop `[R, G, B]` triples, inspired by ColorBrewer):

| Constant | RGB Values | Description |
|----------|-----------|-------------|
| `PALETTE_BLUES` | `[198,219,239], [158,202,225], [107,174,214], [66,146,198], [33,113,181], [8,69,148]` | Light blue to dark blue (water, ice) |
| `PALETTE_GREENS` | `[199,233,192], [161,217,155], [116,196,118], [65,171,93], [35,139,69], [0,90,50]` | Light green to dark green (vegetation) |
| `PALETTE_REDS` | `[254,229,217], [252,174,145], [251,106,74], [239,59,44], [203,24,29], [153,0,13]` | Light red to dark red (danger, noise) |
| `PALETTE_YELLOW_RED` | `[255,255,178], [254,204,92], [253,141,60], [240,59,32], [189,0,38], [128,0,38]` | Yellow to red (heat, intensity) |
| `PALETTE_BLUE_WHITE` | `[8,48,107], [33,113,181], [66,146,198], [146,197,222], [209,229,240], [247,251,255]` | Dark blue to white (salinity, temp) |

**Short-name aliases** (backward-compatible, added alongside `PALETTE_*`):

| Alias | Points to |
|-------|-----------|
| `VIRIDIS` | `PALETTE_VIRIDIS` (existing) |
| `OCEAN_DEPTH` | `PALETTE_OCEAN` (existing) |
| `BLUES` | `PALETTE_BLUES` (new) |
| `GREENS` | `PALETTE_GREENS` (new) |
| `REDS` | `PALETTE_REDS` (new) |
| `YELLOW_RED` | `PALETTE_YELLOW_RED` (new) |
| `BLUE_WHITE` | `PALETTE_BLUE_WHITE` (new) |

All new names (both `PALETTE_*` and short aliases) added to `__all__` in `colors.py` AND to the `__all__` list in `__init__.py` (lines 265-413).

**Usage:**
```python
from shiny_deckgl import OCEAN_DEPTH, BLUES
grid_layer("depth", data, colorRange=OCEAN_DEPTH)
```

---

## 3. Categorical Color Guidance

**Scope:** Documentation only — added to `docs/performance-patterns.md` under a "Visualization Patterns" section (separate from the performance section, since this is a data visualization pattern, not a performance optimization).

**Recommendation:** Use `scatterplot_layer` with pre-computed per-point RGBA colors for categorical/discrete data (e.g., sediment types, block IDs).

**Why not `grid_layer`:** Its `colorRange` works with `colorAggregation` for continuous gradients. It aggregates values per cell — no way to assign a fixed color per discrete class.

**Pattern:**
```python
CATEGORY_COLORS = {0: [31,119,180,255], 1: [255,127,14,255], 2: [44,160,44,255]}
points = [{"position": [lon, lat], "color": CATEGORY_COLORS[val]} for ...]

scatterplot_layer("sediment", points,
    getPosition="@@=d.position",
    getFillColor="@@=d.color",
)
```

**Future:** Option A from the improvements doc (`colorMode="categorical"` on `grid_layer`) noted as a possible future enhancement.

---

## 4. `update_legend()` Convenience Method

**Scope:** New Python method + new JS message handler.

### Python — `map_widget.py`

```python
async def update_legend(
    self,
    session: "Session",
    entries: list[dict],
    title: str | None = None,
    show_checkbox: bool = True,
    collapsed: bool = False,
    position: str = "bottom-right",
) -> None:
```

Sends `deck_update_legend` custom message with:
```json
{
  "id": "<widget_id>",
  "entries": [...],
  "title": "...",
  "showCheckbox": true,
  "collapsed": false,
  "position": "bottom-right"
}
```

Follows the established pattern of `update_tooltip()`.

### JavaScript — `deckgl-init.js`

New `Shiny.addCustomMessageHandler("deck_update_legend", ...)`:
1. Find existing `DeckLegendControl` on the map instance (stored as `instance.deckLegendControl`)
2. If found: update `_options`, call `_render()`
3. If not found: create new `DeckLegendControl`, add to map, store reference

**Store reference on init:** When a `deck_legend` control is created in `initMap()`, save it as `instance.deckLegendControl`.

**No prior legend required:** If `update_legend()` is called without a prior `deck_legend_control()` in the initial controls, the JS handler creates a new `DeckLegendControl` and adds it. This is documented in the Python method docstring.

**JS compatibility note:** The existing `DeckLegendControl` class already has `_options` property and `_render()` method (lines 60-222 of `deckgl-init.js`). The `show_checkbox`, `collapsed`, and `position` parameters map directly to existing `DeckLegendControl` constructor options. No control refactoring needed.

**No changes to `controls.py`** — initial setup via `deck_legend_control()` stays the same.

---

## 5. Client-Side Animation API

**Scope:** New Python module + MapWidget method + JS animation system.

### Python — new `_animation.py`

```python
def animate(
    prop: str,
    speed: float = 1.0,
    loop: bool = True,
    range_min: float = 0,
    range_max: float = 360,
) -> dict:
```

Returns: `{"@@animate": True, "prop": prop, "speed": speed, "loop": loop, "range_min": range_min, "range_max": range_max}`

Note: Uses `range_min`/`range_max` instead of `min`/`max` to avoid shadowing Python builtins (consistent with `_transitions.py` style).

### Python — `map_widget.py`

```python
async def set_animation(
    self,
    session: "Session",
    layer_id: str,
    enabled: bool = True,
) -> None:
```

Sends `deck_set_animation` message.

### JavaScript — `deckgl-init.js`

**End-to-end transformation flow:**

1. **Python side:** `animate(prop="rotation", speed=40)` returns marker dict
2. **Serialization:** Marker dict is serialized to JSON as part of the layer spec (e.g., `{"getAngle": {"@@animate": true, "prop": "rotation", ...}}`)
3. **JS detection:** In `buildDeckLayers()`, scan each layer's props for objects with `"@@animate": true`. For each found:
   a. Extract the animation config and store on `instance.animations[layerId][prop]`
   b. **Replace the prop value** with an accessor function: `(d) => window._deckgl_anim_{widgetId}_{prop}` (for uniform props like `getAngle`) or `(d) => d.phase === 'operational' ? window._deckgl_anim_{widgetId}_{prop} : 0` (for per-datum usage via manual `@@=` expressions)
   c. Initialize `window._deckgl_anim_{widgetId}_{prop} = range_min`
4. **RAF loop starts** (if not already running)

**RAF loop — builds on TripsLayer pattern** (`startTripsAnimation()` at line ~954 of `deckgl-init.js`):

A new `startPropertyAnimations(instance, mapId)` function follows the same structure:
- Single batched `requestAnimationFrame` tick function
- Each frame: compute `deltaSeconds` from last frame, then for each animation config:
  - `value += speed * deltaSeconds`
  - If `loop`: `value = range_min + ((value - range_min) % (range_max - range_min))`
  - If not `loop`: `value = Math.min(value, range_max)`
  - Write to `window._deckgl_anim_{widgetId}_{prop}`
- Re-build deck layers via `buildDeckLayers()` and call `overlay.setProps({ layers })`
- Schedule next frame via `instance.propertyAnimation.rafId = requestAnimationFrame(tick)`

**`deck_set_animation` handler:**
- `enabled=true`: Start/resume animation for layer
- `enabled=false`: Freeze at current value, cancel RAF if no more animations active

**Cleanup:** When a layer is removed via `update()`, any animation configs for that layer ID are deleted from `instance.animations`. If no animations remain, the RAF loop is cancelled and `window._deckgl_anim_*` globals for that widget are cleaned up.

**Compatibility:**
- `partial_update()` preserves running animations (does not restart) — the RAF loop checks `instance.animations` which is not cleared by partial updates
- Multiple animations per widget supported (batched into single RAF)
- Stopping freezes value; restarting resumes from frozen value

**Accessor integration:**
```python
# Automatic (animate() generates the accessor — JS replaces with window global reader):
icon_layer("turbines", data,
    getAngle=animate(prop="rotation", speed=40, loop=True),
)

# Manual (reference animated value in @@= expression):
getAngle="@@=d.phase === 'operational' ? window._deckgl_anim_sim_map_rotation : 0"
```

### Exports

`animate` added to `_animation.py.__all__`, `__init__.py` imports, and top-level `__all__`.

---

## Version & Compatibility

**Version bump:** Increment to 1.7.0 (new public API: `update_legend()`, `set_animation()`, `animate()`).

**JS compatibility:** New message handlers (`deck_update_legend`, `deck_set_animation`) are additive — they do not modify existing handler behavior. The `buildDeckLayers()` change for `@@animate` detection only triggers on the new marker dict, so existing layer specs are unaffected.

---

## Files Modified

| File | Changes |
|------|---------|
| `src/shiny_deckgl/colors.py` | New palettes + aliases |
| `src/shiny_deckgl/__init__.py` | Export new colors + `animate` |
| `src/shiny_deckgl/map_widget.py` | Docstrings + `update_legend()` + `set_animation()` |
| `src/shiny_deckgl/_animation.py` | **New file** — `animate()` helper |
| `src/shiny_deckgl/resources/deckgl-init.js` | `deck_update_legend` handler + animation system |
| `README.md` | Performance Patterns section |
| `docs/performance-patterns.md` | **New file** — full guide |
| `tests/test_basic.py` | Tests for new palettes, aliases, `animate()` |
| `tests/test_integration.py` | Tests for `update_legend()`, `set_animation()` |

## Testing Strategy

- **Unit tests** (appended to existing `TestColors` and new `TestAnimation` class in `test_basic.py`):
  - New color constants are valid 6-stop RGB lists with values in 0-255 range
  - Aliases point to the exact same object as their `PALETTE_*` counterpart (`VIRIDIS is PALETTE_VIRIDIS`)
  - `animate()` returns correct marker dict with all fields
  - Existing `__all__` validation test updated to include new exports
- **Integration tests** (new `TestUpdateLegend` and `TestSetAnimation` classes in `test_integration.py`):
  - `update_legend()` sends correct message shape via `session._send_custom_message`
  - `set_animation()` sends correct message shape
  - `update_legend()` without prior legend setup documented as valid
- **E2E tests** (deferred — outlined for future):
  - Verify legend DOM updates after `update_legend()` call
  - Verify `window._deckgl_anim_*` globals are set and incrementing during animation
  - Verify animation stops/resumes via `set_animation(enabled=False/True)`
