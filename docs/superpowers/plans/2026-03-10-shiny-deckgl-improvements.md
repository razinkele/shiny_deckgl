# shiny-deckgl Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 improvements to the shiny-deckgl package: documentation for partial_update pattern, color ramp constants, categorical color guidance, update_legend() method, and client-side animation API.

**Architecture:** Incremental approach — each improvement is independently testable and committed separately. Documentation-only changes first, then Python additions, then Python+JS features. TDD throughout.

**Tech Stack:** Python 3.9+, JavaScript (deck.gl 9.2.10, MapLibre GL JS 5.3.1), pytest

**Spec:** `docs/superpowers/specs/2026-03-10-shiny-deckgl-improvements-design.md`

**Test command:** `conda run -n shiny python -m pytest tests/ -v`

---

## File Structure

| File | Responsibility | Task |
|------|---------------|------|
| `docs/performance-patterns.md` | **New** — Performance & visualization patterns guide | 1, 3 |
| `README.md` | Add Performance Patterns section | 1 |
| `src/shiny_deckgl/map_widget.py` | Augment docstrings, add `update_legend()`, `set_animation()` | 1, 4, 5 |
| `src/shiny_deckgl/colors.py` | Add 5 new palettes + 7 short-name aliases | 2 |
| `src/shiny_deckgl/__init__.py` | Export new colors + `animate_prop` | 2, 5 |
| `src/shiny_deckgl/_animation.py` | **New** — `animate_prop()` helper | 5 |
| `src/shiny_deckgl/resources/deckgl-init.js` | `deck_update_legend` handler + animation RAF system | 4, 5 |
| `src/shiny_deckgl/_version.py` | Bump to 1.7.0 | 6 |
| `tests/test_basic.py` | Tests for palettes, aliases, `animate_prop()`, updated `__all__` check | 2, 5 |
| `tests/test_integration.py` | Tests for `update_legend()`, `set_animation()` messages | 4, 5 |

---

## Chunk 1: Documentation + Color Ramps (Tasks 1–3)

### Task 1: Document `partial_update` Performance Pattern

**Files:**
- Modify: `src/shiny_deckgl/map_widget.py:291-410` (docstrings on `update()`, `partial_update()`, `patch_layer()`)
- Create: `docs/performance-patterns.md`
- Modify: `README.md` (add section after line ~397, before "Running Tests")

- [ ] **Step 1: Augment `update()` docstring**

In `src/shiny_deckgl/map_widget.py`, add performance note to the `update()` docstring (after the existing Parameters section, before the closing `"""`):

```python
        .. tip::
           ``update()`` serialises **every** layer to JSON on each call.
           For apps that mix infrequently-changing static layers (e.g.
           bathymetry heatmap) with rapidly-updating dynamic layers (e.g.
           agent positions every 100 ms), prefer :meth:`partial_update`
           for the dynamic layers — it only serialises the layers you
           pass and merges by ``id`` on the JS side, reducing
           serialisation cost by 80–90 %.

        See Also
        --------
        partial_update : Sparse layer patches (dynamic layers only).
        patch_layer : Convenience wrapper for patching a single layer.
        set_layer_visibility : Toggle visibility without resending data.
```

- [ ] **Step 2: Augment `partial_update()` docstring**

Add after the existing note block in the `partial_update()` docstring:

```python
        .. tip::
           **When to use:** Call ``partial_update()`` for layers whose
           data changes frequently (e.g. per simulation tick), while
           keeping static layers untouched.  Only the layers you include
           are serialised and sent over the WebSocket.

        See Also
        --------
        update : Full layer-stack replacement (use for initial load or
            when the entire landscape changes).
        patch_layer : Single-layer convenience wrapper.
```

- [ ] **Step 3: Create `docs/performance-patterns.md`**

Create the file with the following content:

```markdown
# Performance & Visualization Patterns

## Performance Patterns

### Static / Dynamic Layer Split

For apps with layers that update at different frequencies, split into
static layers (sent once via `update()`) and dynamic layers (sent per
tick via `partial_update()`):

\```python
# On data load (infrequent) — full layer set
await widget.update(session, layers=[
    static_layer_1,   # e.g., bathymetry heatmap
    static_layer_2,   # e.g., food distribution
    dynamic_layer_1,  # e.g., moving agents
])

# On simulation tick (frequent) — only changed layers
await widget.partial_update(session, layers=[
    dynamic_layer_1,  # matched by layer ID, merged into existing set
])
\```

**Why it matters:**
- `update()` serialises the entire layer list to JSON on every call
- `partial_update()` only serialises the layers you pass, and merges by
  ID on the JS side
- For apps with large static datasets (thousands of heatmap points) and
  fast-updating dynamic data (agent positions every 100 ms), this can
  reduce serialisation cost by 80–90 %

### When to use each method

| Scenario | Method |
|----------|--------|
| Initial load, all layers | `update()` |
| Landscape/data changed, rebuild everything | `update()` |
| Agent positions moved (per tick) | `partial_update()` |
| Single layer property tweak | `patch_layer()` |
| Layer visibility toggle | `set_layer_visibility()` |
| Single layer data refresh | `partial_update()` or `patch_layer()` |

---

## Visualization Patterns

### Categorical / Discrete Data

`grid_layer` uses `colorRange` for continuous gradients with
aggregation. It does not support categorical data where each point has
a discrete class.

For categorical data (e.g., sediment types, land-use classes), use
`scatterplot_layer` with pre-computed RGBA colors:

\```python
CATEGORY_COLORS = {
    0: [31, 119, 180, 255],   # Class A — blue
    1: [255, 127, 14, 255],   # Class B — orange
    2: [44, 160, 44, 255],    # Class C — green
}

points = [
    {"position": [lon, lat], "color": CATEGORY_COLORS[val]}
    for lon, lat, val in data
]

scatterplot_layer("sediment", points,
    getPosition="@@=d.position",
    getFillColor="@@=d.color",
)
\```

> **Future:** A `colorMode="categorical"` option for `grid_layer` may
> be added in a future release.
```

- [ ] **Step 4: Add Performance Patterns section to README.md**

In `README.md`, add before the "Running Tests" section (around line 397):

```markdown
## Performance Patterns

See [docs/performance-patterns.md](docs/performance-patterns.md) for guidance on:

- **Static / Dynamic Layer Split** — use `partial_update()` for frequently-changing layers to reduce serialisation cost by 80–90 %
- **Categorical Data** — use `scatterplot_layer` with pre-computed colors for discrete data classes
```

- [ ] **Step 5: Commit**

```bash
git add docs/performance-patterns.md README.md src/shiny_deckgl/map_widget.py
git commit -m "docs: add performance patterns guide and docstring cross-references"
```

---

### Task 2: Pre-Built Color Ramp Constants

**Files:**
- Modify: `src/shiny_deckgl/colors.py:5-55` (add palettes + aliases + `__all__`)
- Modify: `src/shiny_deckgl/__init__.py:123-137,265-324` (exports)
- Test: `tests/test_basic.py`

- [ ] **Step 1: Write failing tests for new palettes**

Append to `tests/test_basic.py`:

```python
class TestNewPalettes:
    """Tests for new color ramp constants added in v1.7.0."""

    def test_palette_blues_has_6_stops(self):
        from shiny_deckgl import PALETTE_BLUES
        assert len(PALETTE_BLUES) == 6

    def test_palette_greens_has_6_stops(self):
        from shiny_deckgl import PALETTE_GREENS
        assert len(PALETTE_GREENS) == 6

    def test_palette_reds_has_6_stops(self):
        from shiny_deckgl import PALETTE_REDS
        assert len(PALETTE_REDS) == 6

    def test_palette_yellow_red_has_6_stops(self):
        from shiny_deckgl import PALETTE_YELLOW_RED
        assert len(PALETTE_YELLOW_RED) == 6

    def test_palette_blue_white_has_6_stops(self):
        from shiny_deckgl import PALETTE_BLUE_WHITE
        assert len(PALETTE_BLUE_WHITE) == 6

    def test_new_palettes_are_rgb_triples(self):
        from shiny_deckgl import (
            PALETTE_BLUES, PALETTE_GREENS, PALETTE_REDS,
            PALETTE_YELLOW_RED, PALETTE_BLUE_WHITE,
        )
        for pal in (PALETTE_BLUES, PALETTE_GREENS, PALETTE_REDS,
                    PALETTE_YELLOW_RED, PALETTE_BLUE_WHITE):
            for stop in pal:
                assert len(stop) == 3
                assert all(0 <= v <= 255 for v in stop)

    def test_new_palettes_work_with_color_range(self):
        from shiny_deckgl import PALETTE_BLUES, color_range
        result = color_range(4, palette=PALETTE_BLUES)
        assert len(result) == 4


class TestColorAliases:
    """Tests for short-name aliases."""

    def test_viridis_alias(self):
        from shiny_deckgl import VIRIDIS, PALETTE_VIRIDIS
        assert VIRIDIS is PALETTE_VIRIDIS

    def test_ocean_depth_alias(self):
        from shiny_deckgl import OCEAN_DEPTH, PALETTE_OCEAN
        assert OCEAN_DEPTH is PALETTE_OCEAN

    def test_blues_alias(self):
        from shiny_deckgl import BLUES, PALETTE_BLUES
        assert BLUES is PALETTE_BLUES

    def test_greens_alias(self):
        from shiny_deckgl import GREENS, PALETTE_GREENS
        assert GREENS is PALETTE_GREENS

    def test_reds_alias(self):
        from shiny_deckgl import REDS, PALETTE_REDS
        assert REDS is PALETTE_REDS

    def test_yellow_red_alias(self):
        from shiny_deckgl import YELLOW_RED, PALETTE_YELLOW_RED
        assert YELLOW_RED is PALETTE_YELLOW_RED

    def test_blue_white_alias(self):
        from shiny_deckgl import BLUE_WHITE, PALETTE_BLUE_WHITE
        assert BLUE_WHITE is PALETTE_BLUE_WHITE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestNewPalettes -v --no-header 2>&1 | head -20`
Expected: FAIL — `ImportError: cannot import name 'PALETTE_BLUES'`

- [ ] **Step 3: Add new palettes and aliases to `colors.py`**

After `PALETTE_CHLOROPHYLL` (line 55), add:

```python
PALETTE_BLUES: list[list[int]] = [
    [198, 219, 239], [158, 202, 225], [107, 174, 214],
    [66, 146, 198], [33, 113, 181], [8, 69, 148],
]
PALETTE_GREENS: list[list[int]] = [
    [199, 233, 192], [161, 217, 155], [116, 196, 118],
    [65, 171, 93], [35, 139, 69], [0, 90, 50],
]
PALETTE_REDS: list[list[int]] = [
    [254, 229, 217], [252, 174, 145], [251, 106, 74],
    [239, 59, 44], [203, 24, 29], [153, 0, 13],
]
PALETTE_YELLOW_RED: list[list[int]] = [
    [255, 255, 178], [254, 204, 92], [253, 141, 60],
    [240, 59, 32], [189, 0, 38], [128, 0, 38],
]
PALETTE_BLUE_WHITE: list[list[int]] = [
    [8, 48, 107], [33, 113, 181], [66, 146, 198],
    [146, 197, 222], [209, 229, 240], [247, 251, 255],
]

# --- Short-name aliases ---
VIRIDIS = PALETTE_VIRIDIS
OCEAN_DEPTH = PALETTE_OCEAN
BLUES = PALETTE_BLUES
GREENS = PALETTE_GREENS
REDS = PALETTE_REDS
YELLOW_RED = PALETTE_YELLOW_RED
BLUE_WHITE = PALETTE_BLUE_WHITE
```

Update `__all__` at top of `colors.py` to include all new names:

```python
__all__ = [
    "CARTO_POSITRON",
    "CARTO_DARK",
    "CARTO_VOYAGER",
    "OSM_LIBERTY",
    "PALETTE_VIRIDIS",
    "PALETTE_PLASMA",
    "PALETTE_OCEAN",
    "PALETTE_THERMAL",
    "PALETTE_CHLOROPHYLL",
    "PALETTE_BLUES",
    "PALETTE_GREENS",
    "PALETTE_REDS",
    "PALETTE_YELLOW_RED",
    "PALETTE_BLUE_WHITE",
    "VIRIDIS",
    "OCEAN_DEPTH",
    "BLUES",
    "GREENS",
    "REDS",
    "YELLOW_RED",
    "BLUE_WHITE",
    "color_range",
    "color_bins",
    "color_quantiles",
    "depth_color",
]
```

- [ ] **Step 4: Update `__init__.py` imports and `__all__`**

In `src/shiny_deckgl/__init__.py`, update the colors import block (lines 123-137):

```python
# --- colors ---
from .colors import (  # noqa: F401
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    color_range,
    color_bins,
    color_quantiles,
    depth_color,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
    PALETTE_BLUES,
    PALETTE_GREENS,
    PALETTE_REDS,
    PALETTE_YELLOW_RED,
    PALETTE_BLUE_WHITE,
    VIRIDIS,
    OCEAN_DEPTH,
    BLUES,
    GREENS,
    REDS,
    YELLOW_RED,
    BLUE_WHITE,
)
```

Add the new names to the `__all__` list (in the "Colors & basemaps" section around line 317):

```python
    # New palettes (v1.7.0)
    "PALETTE_BLUES",
    "PALETTE_GREENS",
    "PALETTE_REDS",
    "PALETTE_YELLOW_RED",
    "PALETTE_BLUE_WHITE",
    # Short-name aliases (v1.7.0)
    "VIRIDIS",
    "OCEAN_DEPTH",
    "BLUES",
    "GREENS",
    "REDS",
    "YELLOW_RED",
    "BLUE_WHITE",
```

- [ ] **Step 5: Update `test_public_api_exports` in `tests/test_basic.py`**

Add the new names to the `expected` set in `test_public_api_exports()` (around line 122):

```python
        # v1.7.0 color ramps
        "PALETTE_BLUES", "PALETTE_GREENS", "PALETTE_REDS",
        "PALETTE_YELLOW_RED", "PALETTE_BLUE_WHITE",
        "VIRIDIS", "OCEAN_DEPTH", "BLUES", "GREENS", "REDS",
        "YELLOW_RED", "BLUE_WHITE",
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestNewPalettes tests/test_basic.py::TestColorAliases tests/test_basic.py::test_public_api_exports -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/shiny_deckgl/colors.py src/shiny_deckgl/__init__.py tests/test_basic.py
git commit -m "feat: add color ramp constants and short-name aliases"
```

---

### Task 3: Categorical Color Guidance (docs only)

Already included in Task 1's `docs/performance-patterns.md` under "Visualization Patterns". No additional work needed — Task 1 covers this.

---

## Chunk 2: Legend Update API (Task 4)

### Task 4: `update_legend()` Convenience Method

**Files:**
- Modify: `src/shiny_deckgl/map_widget.py` (add method after `update_tooltip`, ~line 691)
- Modify: `src/shiny_deckgl/resources/deckgl-init.js` (add handler + store legend ref)
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write failing test for `update_legend()`**

Append to `tests/test_integration.py` (uses `asyncio.run()` to match existing test patterns — no `pytest-asyncio` dependency):

```python
class TestUpdateLegend:
    """Tests for MapWidget.update_legend() method."""

    def test_update_legend_sends_message(self):
        import asyncio
        from shiny_deckgl import MapWidget
        w = MapWidget("legend-test")
        sent = []
        class FakeSession:
            async def send_custom_message(self, type_, data):
                sent.append((type_, data))
        session = FakeSession()
        asyncio.run(w.update_legend(session, entries=[
            {"layer_id": "pts", "label": "Points", "color": [255, 0, 0]},
        ], title="My Legend"))
        assert len(sent) == 1
        msg_type, payload = sent[0]
        assert msg_type == "deck_update_legend"
        assert payload["id"] == "legend-test"
        assert len(payload["entries"]) == 1
        assert payload["title"] == "My Legend"
        assert payload["showCheckbox"] is True
        assert payload["position"] == "bottom-right"

    def test_update_legend_custom_position(self):
        import asyncio
        from shiny_deckgl import MapWidget
        w = MapWidget("legend-pos")
        sent = []
        class FakeSession:
            async def send_custom_message(self, type_, data):
                sent.append((type_, data))
        session = FakeSession()
        asyncio.run(w.update_legend(session, entries=[], position="top-left"))
        assert sent[0][1]["position"] == "top-left"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n shiny python -m pytest tests/test_integration.py::TestUpdateLegend -v`
Expected: FAIL — `AttributeError: 'MapWidget' object has no attribute 'update_legend'`

- [ ] **Step 3: Add `update_legend()` to `map_widget.py`**

Insert after `update_tooltip()` (after line 691):

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
        """Update or create a deck.gl legend control dynamically.

        Patches the existing :class:`DeckLegendControl` on the JS side,
        or creates one if none exists yet.  This allows switching legend
        entries when the user toggles between layers with different color
        schemes — without resending the full controls list.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        entries
            Legend entry dicts (same format as
            :func:`~shiny_deckgl.controls.deck_legend_control`).
        title
            Optional header text.
        show_checkbox
            Show a checkbox per entry to toggle layer visibility.
        collapsed
            Start the panel in collapsed state.
        position
            Control position (default ``"bottom-right"``).  Only used
            when creating a new legend; ignored if one already exists.
        """
        await session.send_custom_message("deck_update_legend", {
            "id": self.id,
            "entries": list(entries),
            "title": title,
            "showCheckbox": show_checkbox,
            "collapsed": collapsed,
            "position": position,
        })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n shiny python -m pytest tests/test_integration.py::TestUpdateLegend -v`
Expected: All PASS

- [ ] **Step 5: Add JS `deck_update_legend` handler**

In `src/shiny_deckgl/resources/deckgl-init.js`, first modify the `initMap()` function to store legend control references. Find the `controlsConfig.forEach` loop (around line 386) and change:

```javascript
      if (ctrl) {
        const pos = cfg.position || 'top-right';
        map.addControl(ctrl, pos);
        initialControls[cfg.type] = { control: ctrl, position: pos };
      }
```

to:

```javascript
      if (ctrl) {
        const pos = cfg.position || 'top-right';
        map.addControl(ctrl, pos);
        initialControls[cfg.type] = { control: ctrl, position: pos };
        // Store deck_legend reference for dynamic updates
        if (cfg.type === 'deck_legend') {
          // Will be stored on instance after it's created below
          ctrl._deckLegendPosition = pos;
        }
      }
```

Then after the `mapInstances[mapId] = { ... }` object creation, add:

```javascript
    // Store deck_legend control reference if one was created at init
    if (initialControls.deck_legend) {
      mapInstances[mapId].deckLegendControl = initialControls.deck_legend.control;
    }
```

Then add the message handler (near other `Shiny.addCustomMessageHandler` blocks):

```javascript
  // -----------------------------------------------------------------------
  // deck_update_legend — update or create a deck.gl legend control
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_update_legend", function (payload) {
    if (!payload || !payload.id) return;
    const instance = ensureInstance(payload.id);
    if (!instance) return;

    const opts = {
      entries: payload.entries || [],
      showCheckbox: payload.showCheckbox !== false,
      collapsed: payload.collapsed || false,
    };
    if (payload.title != null) opts.title = payload.title;

    if (instance.deckLegendControl) {
      // Update existing legend
      instance.deckLegendControl._options = Object.assign(
        instance.deckLegendControl._options, opts
      );
      instance.deckLegendControl._render();
    } else {
      // Create new legend
      const ctrl = new DeckLegendControl(opts);
      const pos = payload.position || 'bottom-right';
      instance.map.addControl(ctrl, pos);
      instance.deckLegendControl = ctrl;
    }
  });
```

- [ ] **Step 6: Run full test suite**

Run: `conda run -n shiny python -m pytest tests/ -v --no-header 2>&1 | tail -5`
Expected: All tests pass (JS tests are not unit-testable here — E2E deferred)

- [ ] **Step 7: Commit**

```bash
git add src/shiny_deckgl/map_widget.py src/shiny_deckgl/resources/deckgl-init.js tests/test_integration.py
git commit -m "feat: add update_legend() for dynamic legend updates"
```

---

## Chunk 3: Client-Side Animation API (Task 5) + Version Bump (Task 6)

### Task 5: Client-Side Animation API

> **Note:** The function is named `animate_prop` (not `animate`) to avoid
> collision with the existing `animate` parameter on `MapWidget.update()`.

**Files:**
- Create: `src/shiny_deckgl/_animation.py`
- Modify: `src/shiny_deckgl/map_widget.py` (add `set_animation()`)
- Modify: `src/shiny_deckgl/__init__.py` (export `animate_prop`)
- Modify: `src/shiny_deckgl/resources/deckgl-init.js` (animation detection + RAF)
- Test: `tests/test_basic.py`, `tests/test_integration.py`

- [ ] **Step 1: Write failing test for `animate_prop()` helper**

Append to `tests/test_basic.py`:

```python
class TestAnimateProp:
    """Tests for the animate_prop() helper function."""

    def test_animate_prop_returns_marker_dict(self):
        from shiny_deckgl import animate_prop
        result = animate_prop(prop="rotation", speed=40)
        assert result["@@animate"] is True
        assert result["prop"] == "rotation"
        assert result["speed"] == 40
        assert result["loop"] is True
        assert result["range_min"] == 0
        assert result["range_max"] == 360

    def test_animate_prop_custom_range(self):
        from shiny_deckgl import animate_prop
        result = animate_prop(prop="scale", speed=1.0, loop=False,
                             range_min=0.5, range_max=2.0)
        assert result["loop"] is False
        assert result["range_min"] == 0.5
        assert result["range_max"] == 2.0

    def test_animate_prop_defaults(self):
        from shiny_deckgl import animate_prop
        result = animate_prop(prop="angle")
        assert result["speed"] == 1.0
        assert result["loop"] is True
        assert result["range_min"] == 0
        assert result["range_max"] == 360

    def test_animate_prop_is_json_serializable(self):
        import json
        from shiny_deckgl import animate_prop
        result = animate_prop(prop="rotation", speed=40)
        serialized = json.dumps(result)
        assert '"@@animate": true' in serialized
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestAnimateProp -v`
Expected: FAIL — `ImportError: cannot import name 'animate_prop'`

- [ ] **Step 3: Create `src/shiny_deckgl/_animation.py`**

```python
"""Client-side property animation helpers."""

from __future__ import annotations

__all__ = ["animate_prop"]


def animate_prop(
    prop: str,
    speed: float = 1.0,
    loop: bool = True,
    range_min: float = 0,
    range_max: float = 360,
) -> dict:
    """Create a client-side animation marker for a layer property.

    When passed as a layer prop value (e.g.
    ``getAngle=animate_prop(...)``), the JavaScript widget starts a
    ``requestAnimationFrame`` loop that increments the property each
    frame — no server round-trips needed.

    .. note::
       Named ``animate_prop`` (not ``animate``) to avoid collision with
       the ``animate`` parameter on :meth:`MapWidget.update`.

    Parameters
    ----------
    prop
        Name for the animated value (used as a key in the JS animation
        registry and in ``window._deckgl_anim_{widgetId}_{prop}``).
    speed
        Units per second (default 1.0).
    loop
        Whether to wrap the value when it reaches *range_max*
        (default ``True``).  For angles this gives continuous rotation.
    range_min
        Minimum value (default 0).
    range_max
        Maximum / wrap value (default 360).

    Returns
    -------
    dict
        A marker dict recognised by the JS layer builder.  Do not
        modify the returned dict — pass it directly as a layer property.

    Example
    -------
    >>> from shiny_deckgl import icon_layer, animate_prop
    >>> icon_layer("turbines", data,
    ...     getAngle=animate_prop(prop="rotation", speed=40, loop=True),
    ... )
    """
    return {
        "@@animate": True,
        "prop": prop,
        "speed": speed,
        "loop": loop,
        "range_min": range_min,
        "range_max": range_max,
    }
```

- [ ] **Step 4: Export `animate_prop` from `__init__.py`**

Add import:

```python
# --- _animation ---
from ._animation import animate_prop  # noqa: F401
```

Add to `__all__`:

```python
    # Animation (v1.7.0)
    "animate_prop",
```

- [ ] **Step 5: Update `test_public_api_exports` in `tests/test_basic.py`**

Add `"animate_prop"` to the `expected` set.

- [ ] **Step 6: Run test to verify it passes**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestAnimate tests/test_basic.py::test_public_api_exports -v`
Expected: All PASS

- [ ] **Step 7: Write failing test for `set_animation()`**

Append to `tests/test_integration.py` (uses `asyncio.run()` to match existing patterns):

```python
class TestSetAnimation:
    """Tests for MapWidget.set_animation() method."""

    def test_set_animation_sends_message(self):
        import asyncio
        from shiny_deckgl import MapWidget
        w = MapWidget("anim-test")
        sent = []
        class FakeSession:
            async def send_custom_message(self, type_, data):
                sent.append((type_, data))
        session = FakeSession()
        asyncio.run(w.set_animation(session, layer_id="turbines", enabled=True))
        assert len(sent) == 1
        msg_type, payload = sent[0]
        assert msg_type == "deck_set_animation"
        assert payload["id"] == "anim-test"
        assert payload["layerId"] == "turbines"
        assert payload["enabled"] is True

    def test_set_animation_disable(self):
        import asyncio
        from shiny_deckgl import MapWidget
        w = MapWidget("anim-off")
        sent = []
        class FakeSession:
            async def send_custom_message(self, type_, data):
                sent.append((type_, data))
        session = FakeSession()
        asyncio.run(w.set_animation(session, layer_id="turbines", enabled=False))
        assert sent[0][1]["enabled"] is False
```

- [ ] **Step 8: Run test to verify it fails**

Run: `conda run -n shiny python -m pytest tests/test_integration.py::TestSetAnimation -v`
Expected: FAIL — `AttributeError: 'MapWidget' object has no attribute 'set_animation'`

- [ ] **Step 9: Add `set_animation()` to `map_widget.py`**

Insert after `update_legend()`:

```python
    async def set_animation(
        self,
        session: "Session",
        layer_id: str,
        enabled: bool = True,
    ) -> None:
        """Start or stop a client-side property animation.

        Targets a layer whose properties include :func:`animate` markers.
        Stopping freezes the animated value at its current position;
        restarting resumes from where it stopped.

        Parameters
        ----------
        session
            The active Shiny ``Session``.
        layer_id
            The ``id`` of the layer containing animated properties.
        enabled
            ``True`` to start/resume, ``False`` to freeze.
        """
        await session.send_custom_message("deck_set_animation", {
            "id": self.id,
            "layerId": layer_id,
            "enabled": enabled,
        })
```

- [ ] **Step 10: Run test to verify it passes**

Run: `conda run -n shiny python -m pytest tests/test_integration.py::TestSetAnimation -v`
Expected: All PASS

- [ ] **Step 11: Add JS animation system to `deckgl-init.js`**

In `src/shiny_deckgl/resources/deckgl-init.js`, add the animation detection in `buildDeckLayers()`. Find the function (search for `function buildDeckLayers`). Inside the loop that processes each layer's props, add detection for `@@animate` markers:

After the `resolveAccessors(props)` call, add:

```javascript
    // Detect @@animate markers and extract animation configs
    const animConfigs = {};
    for (const key of Object.keys(props)) {
      const val = props[key];
      if (val && typeof val === 'object' && val['@@animate'] === true) {
        animConfigs[key] = {
          prop: val.prop,
          speed: val.speed || 1,
          loop: val.loop !== false,
          rangeMin: val.range_min || 0,
          rangeMax: val.range_max || 360,
        };
        // Replace with accessor that reads the animated global
        const globalKey = '_deckgl_anim_' + mapId + '_' + val.prop;
        if (window[globalKey] === undefined) {
          window[globalKey] = val.range_min || 0;
        }
        // Assign current value as a plain number (not an accessor function).
        // This works because buildDeckLayers() is called every frame by the
        // animation RAF loop, so the value is refreshed each frame.  deck.gl
        // detects the change via numeric shallow comparison.  This is simpler
        // than the spec's accessor-function approach and sufficient for
        // uniform props like getAngle on IconLayer.
        props[key] = window[globalKey];
      }
    }
    if (Object.keys(animConfigs).length > 0) {
      props._animConfigs = animConfigs;
    }
```

Then add the animation RAF system (near `startTripsAnimation`):

```javascript
  // -----------------------------------------------------------------------
  // Property animation loop (v1.7.0)
  // -----------------------------------------------------------------------
  function startPropertyAnimations(instance, mapId) {
    // Collect animation configs from all layers
    const allConfigs = {};
    for (const lp of instance.lastLayers) {
      if (lp._animConfigs) {
        allConfigs[lp.id] = lp._animConfigs;
      }
    }

    if (Object.keys(allConfigs).length === 0) {
      // No animations — cancel any existing loop
      if (instance.propertyAnimation && instance.propertyAnimation.rafId) {
        cancelAnimationFrame(instance.propertyAnimation.rafId);
        instance.propertyAnimation = null;
      }
      return;
    }

    // Don't restart if already running
    if (instance.propertyAnimation && instance.propertyAnimation.rafId) return;

    // Merge into existing animations (don't overwrite in-flight configs)
    instance.animations = Object.assign(instance.animations || {}, allConfigs);
    let lastTime = performance.now();

    function tick(now) {
      const dt = (now - lastTime) / 1000; // seconds
      lastTime = now;

      // Update each animated value
      for (const layerId of Object.keys(instance.animations)) {
        const layerConfigs = instance.animations[layerId];
        for (const propKey of Object.keys(layerConfigs)) {
          const cfg = layerConfigs[propKey];
          const globalKey = '_deckgl_anim_' + mapId + '_' + cfg.prop;
          let val = (window[globalKey] || cfg.rangeMin) + cfg.speed * dt;
          if (cfg.loop) {
            const range = cfg.rangeMax - cfg.rangeMin;
            val = cfg.rangeMin + ((val - cfg.rangeMin) % range);
            if (val < cfg.rangeMin) val += range; // handle negative speed
          } else {
            val = Math.min(Math.max(val, cfg.rangeMin), cfg.rangeMax);
          }
          window[globalKey] = val;
        }
      }

      // Rebuild layers with updated values
      const deckLayers = buildDeckLayers(
        instance.lastLayers.map(function (lp) { return Object.assign({}, lp); }),
        mapId,
        instance.tooltipConfig
      );
      instance.overlay.setProps({ layers: deckLayers });

      instance.propertyAnimation.rafId = requestAnimationFrame(tick);
    }

    instance.propertyAnimation = {};
    instance.propertyAnimation.rafId = requestAnimationFrame(tick);
  }

  function cleanupAnimations(instance, mapId, currentLayerIds) {
    if (!instance.animations) return;
    // Remove configs for layers that no longer exist
    for (const layerId of Object.keys(instance.animations)) {
      if (!currentLayerIds.has(layerId)) {
        // Clean up window globals
        const configs = instance.animations[layerId];
        for (const propKey of Object.keys(configs)) {
          delete window['_deckgl_anim_' + mapId + '_' + configs[propKey].prop];
        }
        delete instance.animations[layerId];
      }
    }
    // If no animations remain, cancel RAF
    if (Object.keys(instance.animations).length === 0) {
      if (instance.propertyAnimation && instance.propertyAnimation.rafId) {
        cancelAnimationFrame(instance.propertyAnimation.rafId);
        instance.propertyAnimation = null;
      }
    }
  }
```

In the `deck_update` handler, after `startTripsAnimation(instance, targetId);` add:

```javascript
    // Start property animations if any layers have @@animate markers
    startPropertyAnimations(instance, targetId);
    // Clean up animations for removed layers
    const currentIds = new Set(instance.lastLayers.map(function (l) { return l.id; }));
    cleanupAnimations(instance, targetId, currentIds);
```

Add the `deck_set_animation` handler:

```javascript
  // -----------------------------------------------------------------------
  // deck_set_animation — start/stop property animations for a layer
  // -----------------------------------------------------------------------
  Shiny.addCustomMessageHandler("deck_set_animation", function (payload) {
    if (!payload || !payload.id) return;
    const instance = ensureInstance(payload.id);
    if (!instance) return;

    const layerId = payload.layerId;
    const enabled = payload.enabled !== false;

    if (!enabled) {
      // Freeze: cancel RAF if this was the last animated layer
      if (instance.animations && instance.animations[layerId]) {
        delete instance.animations[layerId];
      }
      if (!instance.animations || Object.keys(instance.animations).length === 0) {
        if (instance.propertyAnimation && instance.propertyAnimation.rafId) {
          cancelAnimationFrame(instance.propertyAnimation.rafId);
          instance.propertyAnimation = null;
        }
      }
    } else {
      // Resume: re-scan layers for animation configs and restart
      startPropertyAnimations(instance, payload.id);
    }
  });
```

- [ ] **Step 12: Run full test suite**

Run: `conda run -n shiny python -m pytest tests/ -v --no-header 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 13: Commit**

```bash
git add src/shiny_deckgl/_animation.py src/shiny_deckgl/__init__.py src/shiny_deckgl/map_widget.py src/shiny_deckgl/resources/deckgl-init.js tests/test_basic.py tests/test_integration.py
git commit -m "feat: add client-side animation API with animate_prop() and set_animation()"
```

---

### Task 6: Version Bump

**Files:**
- Modify: `src/shiny_deckgl/_version.py`

- [ ] **Step 1: Bump version to 1.7.0**

In `src/shiny_deckgl/_version.py`, change the version string to `"1.7.0"`.

- [ ] **Step 2: Run version test**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestVersionBump -v`
Expected: PASS (or update test if it checks exact version)

- [ ] **Step 3: Run full test suite**

Run: `conda run -n shiny python -m pytest tests/ -v --no-header 2>&1 | tail -5`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/shiny_deckgl/_version.py
git commit -m "chore: bump version to 1.7.0"
```
