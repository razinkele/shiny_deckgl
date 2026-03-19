# Time & Space Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add viewport-aware lazy data loading, time-series animation controls, and a demo Tab 11 ("Time & Space") showcasing Baltic Sea temperature data animated across 12 months.

**Architecture:** Two new modules (`_viewport.py`, `_timeline.py`) provide reusable building blocks. The demo tab wires them together — the viewport callback loads spatially filtered temperature data for the current timeline step. All reactive composition happens through Shiny's dependency graph.

**Tech Stack:** Python 3.9+, Shiny for Python, shiny_deckgl (existing package)

**Spec:** `docs/superpowers/specs/2026-03-19-time-and-space-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/shiny_deckgl/_viewport.py` (NEW) | `on_viewport_change()` decorator, `in_bounds()` helper |
| `src/shiny_deckgl/_timeline.py` (NEW) | `timeline_control()` UI, `timeline_server()` wiring |
| `src/shiny_deckgl/__init__.py` (MODIFY) | Export new public API |
| `src/shiny_deckgl/_demo_data.py` (MODIFY) | Add `make_sea_temperature_grid()`, `MONTH_LABELS` |
| `src/shiny_deckgl/_app_widgets.py` (MODIFY) | Add `timespace_widget` |
| `src/shiny_deckgl/_app_ui.py` (MODIFY) | Add Tab 11 UI |
| `src/shiny_deckgl/_app_server.py` (MODIFY) | Add Tab 11 server logic |
| `tests/test_basic.py` (MODIFY) | Tests for new modules |

---

### Task 1: `in_bounds()` helper

**Files:**
- Create: `src/shiny_deckgl/_viewport.py`
- Test: `tests/test_basic.py`

- [ ] **Step 1: Write failing tests for `in_bounds`**

Add to `tests/test_basic.py` at the end of the file:

```python
# ---------------------------------------------------------------------------
# _viewport module tests
# ---------------------------------------------------------------------------

from shiny_deckgl._viewport import in_bounds


class TestInBounds:
    """Tests for the in_bounds() spatial filter helper."""

    def test_point_inside(self):
        bounds = {"sw": [10.0, 54.0], "ne": [25.0, 60.0]}
        assert in_bounds({"lon": 20.0, "lat": 57.0}, bounds) is True

    def test_point_outside_east(self):
        bounds = {"sw": [10.0, 54.0], "ne": [25.0, 60.0]}
        assert in_bounds({"lon": 30.0, "lat": 57.0}, bounds) is False

    def test_point_outside_north(self):
        bounds = {"sw": [10.0, 54.0], "ne": [25.0, 60.0]}
        assert in_bounds({"lon": 20.0, "lat": 65.0}, bounds) is False

    def test_point_on_boundary_is_inside(self):
        bounds = {"sw": [10.0, 54.0], "ne": [25.0, 60.0]}
        assert in_bounds({"lon": 10.0, "lat": 54.0}, bounds) is True
        assert in_bounds({"lon": 25.0, "lat": 60.0}, bounds) is True

    def test_position_list_format(self):
        """in_bounds also accepts a dict with 'position': [lon, lat]."""
        bounds = {"sw": [10.0, 54.0], "ne": [25.0, 60.0]}
        assert in_bounds({"position": [20.0, 57.0]}, bounds) is True
        assert in_bounds({"position": [30.0, 57.0]}, bounds) is False

    def test_none_bounds_returns_true(self):
        """When bounds is None, everything is 'in bounds' (no filtering)."""
        assert in_bounds({"lon": 20.0, "lat": 57.0}, None) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestInBounds -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shiny_deckgl._viewport'`

- [ ] **Step 3: Implement `in_bounds` in `_viewport.py`**

Create `src/shiny_deckgl/_viewport.py`:

```python
"""Viewport-aware data loading helpers."""

from __future__ import annotations

from typing import Any

__all__ = ["in_bounds", "on_viewport_change"]


def in_bounds(point: dict[str, Any], bounds: dict[str, list[float]] | None) -> bool:
    """Check if a point falls within viewport bounds.

    Parameters
    ----------
    point
        Dict with either ``lon``/``lat`` keys or a ``position`` key
        containing ``[lon, lat, ...]``.
    bounds
        Dict with ``sw`` and ``ne`` keys, each ``[lon, lat]``.
        If ``None``, returns ``True`` (no filtering).

    Returns
    -------
    bool
        ``True`` if the point center is within bounds (inclusive).

    Note
    ----
    Checks the point center only, not area. Grid cells whose center
    is outside the viewport but whose area overlaps will be excluded.
    """
    if bounds is None:
        return True

    if "position" in point:
        lon, lat = point["position"][0], point["position"][1]
    else:
        lon, lat = point["lon"], point["lat"]

    sw = bounds["sw"]
    ne = bounds["ne"]
    return sw[0] <= lon <= ne[0] and sw[1] <= lat <= ne[1]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestInBounds -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/_viewport.py tests/test_basic.py
git commit -m "feat: add in_bounds() viewport filtering helper"
```

---

### Task 2: `on_viewport_change()` decorator

**Files:**
- Modify: `src/shiny_deckgl/_viewport.py`
- Test: `tests/test_basic.py`

- [ ] **Step 1: Write failing tests for `on_viewport_change`**

Add to `tests/test_basic.py`:

```python
from shiny_deckgl._viewport import on_viewport_change


class TestOnViewportChange:
    """Tests for on_viewport_change() argument validation."""

    def test_rejects_negative_debounce(self):
        with pytest.raises(ValueError, match="debounce_ms"):
            on_viewport_change(None, None, None, debounce_ms=-1)

    def test_rejects_non_widget(self):
        with pytest.raises(TypeError, match="MapWidget"):
            on_viewport_change("not_a_widget", None, None)

    def test_returns_callable_decorator(self):
        """With a real MapWidget, returns a decorator (callable)."""
        from shiny_deckgl import MapWidget
        widget = MapWidget("test_vp")
        # Cannot fully wire without a Shiny session, but the outer
        # function should return a decorator without error
        decorator = on_viewport_change(widget, None, None)
        assert callable(decorator)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestOnViewportChange -v`
Expected: FAIL — `ImportError: cannot import name 'on_viewport_change'`

- [ ] **Step 3: Implement `on_viewport_change`**

Add to `src/shiny_deckgl/_viewport.py` after the `in_bounds` function:

```python
def on_viewport_change(
    widget: Any,
    input: Any,
    session: Any,
    *,
    debounce_ms: int = 300,
):
    """Decorator that calls a function when the map viewport changes.

    The decorated async function receives ``(bounds, zoom)`` and should
    return a list of layer dicts.  The decorator calls
    ``widget.update(session, layers)`` with the returned layers.

    Inside the decorated function, any Shiny reactive value that is read
    (e.g. ``tl.index()``) automatically becomes a dependency — the
    function re-fires when that value changes, not only on viewport moves.

    On first call (before any ``moveend`` event), the decorator fires
    once using ``widget.view_state`` to derive initial bounds.

    Parameters
    ----------
    widget
        A :class:`~shiny_deckgl.MapWidget` instance.
    input
        The Shiny ``input`` object from the server function.
    session
        The active Shiny ``Session``.
    debounce_ms
        Milliseconds to debounce viewport changes (default 300).

    Returns
    -------
    callable
        A decorator.  Use as ``@on_viewport_change(widget, input, session)``.

    Example
    -------
    >>> @on_viewport_change(my_widget, input, session)
    ... async def load_data(bounds, zoom):
    ...     data = get_points(bounds)
    ...     return [scatterplot_layer("pts", data)]
    """
    from .map_widget import MapWidget

    if not isinstance(widget, MapWidget):
        raise TypeError(
            f"widget must be a MapWidget instance, got {type(widget).__name__}"
        )
    if debounce_ms < 0:
        raise ValueError(f"debounce_ms must be >= 0, got {debounce_ms}")

    def decorator(fn):
        if input is None or session is None:
            # Allow construction without session for testing
            return fn

        from shiny import reactive

        _generation = [0]

        @reactive.Effect
        async def _viewport_watcher():
            # Read the view state input (creates reactive dependency)
            vs = input[widget.view_state_input_id]()

            if vs is not None and "bounds" in vs:
                bounds = vs["bounds"]
                zoom = vs.get("zoom", 0)
            else:
                # Initial load — use widget's configured view_state
                vs0 = widget.view_state
                lon = vs0.get("longitude", 0)
                lat = vs0.get("latitude", 0)
                z = vs0.get("zoom", 5)
                # Approximate bounds from center + zoom
                span = 180 / (2 ** z)
                bounds = {
                    "sw": [lon - span, lat - span / 2],
                    "ne": [lon + span, lat + span / 2],
                }
                zoom = z

            _generation[0] += 1
            my_gen = _generation[0]

            # Debounce: wait briefly, skip if superseded
            if debounce_ms > 0:
                import asyncio
                await asyncio.sleep(debounce_ms / 1000.0)

            layers = await fn(bounds, zoom)

            # Last-write-wins: skip if a newer call started
            if my_gen != _generation[0]:
                return

            if layers is not None:
                await widget.update(session, layers)

        return fn

    return decorator
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestOnViewportChange -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/_viewport.py tests/test_basic.py
git commit -m "feat: add on_viewport_change() reactive decorator"
```

---

### Task 3: `timeline_control()` UI

**Files:**
- Create: `src/shiny_deckgl/_timeline.py`
- Test: `tests/test_basic.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_basic.py`:

```python
from shiny_deckgl._timeline import timeline_control, timeline_server


class TestTimelineControl:
    """Tests for timeline_control() UI builder."""

    def test_returns_tag(self):
        ui_tag = timeline_control("tl", labels=["Jan", "Feb", "Mar"])
        # Should return a Shiny TagList (has render method or children)
        assert ui_tag is not None

    def test_requires_labels(self):
        with pytest.raises(ValueError, match="labels"):
            timeline_control("tl", labels=[])

    def test_requires_positive_interval(self):
        with pytest.raises(ValueError, match="interval_ms"):
            timeline_control("tl", labels=["A", "B"], interval_ms=0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestTimelineControl -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shiny_deckgl._timeline'`

- [ ] **Step 3: Implement `timeline_control`**

Create `src/shiny_deckgl/_timeline.py`:

```python
"""Time-series animation controls for Shiny."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

__all__ = ["timeline_control", "timeline_server"]


def timeline_control(
    id: str,
    labels: list[str],
    *,
    interval_ms: int = 1000,
) -> Any:
    """UI fragment for time-series animation controls.

    Returns Play/Pause button, a slider scrubber mapped to label indices,
    and a text display of the current label.

    Parameters
    ----------
    id
        Shiny module namespace ID.
    labels
        List of step labels (e.g. month names). Length determines slider range.
    interval_ms
        Milliseconds between frames during auto-play (default 1000).

    Returns
    -------
    shiny.ui.TagList
        Ready to embed in a sidebar.
    """
    if not labels:
        raise ValueError("labels must be a non-empty list")
    if interval_ms <= 0:
        raise ValueError(f"interval_ms must be > 0, got {interval_ms}")

    from shiny import module, ui

    @module.ui
    def _inner_ui():
        choices = {str(i): lbl for i, lbl in enumerate(labels)}
        return ui.TagList(
            ui.layout_columns(
                ui.input_action_button(
                    "play", "\u25B6 Play",
                    class_="btn-sm btn-success",
                ),
                ui.input_action_button(
                    "pause", "\u23F8 Pause",
                    class_="btn-sm btn-warning",
                ),
                col_widths=(6, 6),
            ),
            ui.input_slider(
                "step", "Time step",
                min=0, max=len(labels) - 1, value=0, step=1,
                ticks=False,
            ),
            ui.output_text("current_label"),
        )

    return _inner_ui(id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestTimelineControl -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/_timeline.py tests/test_basic.py
git commit -m "feat: add timeline_control() UI for time-series animation"
```

---

### Task 4: `timeline_server()` wiring

**Files:**
- Modify: `src/shiny_deckgl/_timeline.py`
- Test: `tests/test_basic.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_basic.py`:

```python
class TestTimelineServer:
    """Tests for timeline_server() argument validation."""

    def test_requires_labels(self):
        with pytest.raises(ValueError, match="labels"):
            timeline_server("tl", labels=[])

    def test_accepts_valid_labels(self):
        """Should not raise with valid labels (actual wiring needs a session)."""
        # timeline_server returns a SimpleNamespace with .index and .label
        # but wiring requires a Shiny session; just test it doesn't crash
        result = timeline_server("tl", labels=["A", "B", "C"])
        assert hasattr(result, "index")
        assert hasattr(result, "label")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestTimelineServer -v`
Expected: FAIL — `timeline_server` not yet implemented

- [ ] **Step 3: Implement `timeline_server`**

Add to `src/shiny_deckgl/_timeline.py` after `timeline_control`:

```python
def timeline_server(
    id: str,
    labels: list[str],
    *,
    interval_ms: int = 1000,
) -> Any:
    """Server logic for time-series animation controls.

    Wires the Play/Pause buttons and step slider produced by
    :func:`timeline_control`. Returns a namespace with reactive
    accessors for the current step.

    Unlike ``trips_animation_server``, this does NOT take ``widget``
    or ``session`` because it doesn't directly control a widget —
    it only exposes reactive values that the caller wires into
    their own layer-building logic.

    Parameters
    ----------
    id
        Must match the *id* passed to :func:`timeline_control`.
    labels
        Same label list passed to :func:`timeline_control`.
    interval_ms
        Milliseconds between auto-play frames (default 1000).

    Returns
    -------
    types.SimpleNamespace
        ``.index`` — callable returning current 0-based step index.
        ``.label`` — callable returning current label string.
    """
    import types

    if not labels:
        raise ValueError("labels must be a non-empty list")

    try:
        from shiny import module, reactive
    except ImportError:
        # No Shiny available (testing) — return stubs
        return types.SimpleNamespace(
            index=lambda: 0,
            label=lambda: labels[0] if labels else "",
        )

    result_holder: list = []

    @module.server
    def _inner_server(input, output, inner_session):
        _playing = reactive.Value(False)

        @reactive.Effect
        @reactive.event(input.play)
        def _on_play():
            _playing.set(True)

        @reactive.Effect
        @reactive.event(input.pause)
        def _on_pause():
            _playing.set(False)

        @reactive.Effect
        async def _auto_advance():
            """Polling loop: advances the slider when playing."""
            if not _playing():
                return
            reactive.invalidate_later(interval_ms / 1000.0)
            current = input.step()
            next_val = (current + 1) % len(labels)
            from shiny import ui as _ui
            _ui.update_slider("step", value=next_val, session=inner_session)

        @output
        @reactive.event(input.step)
        def current_label():
            idx = input.step()
            return f"{labels[idx]}"

        result_holder.append(types.SimpleNamespace(
            index=input.step,
            label=lambda: labels[input.step()],
        ))

    _inner_server(id)

    if result_holder:
        return result_holder[0]

    # Fallback for environments without active Shiny session
    return types.SimpleNamespace(
        index=lambda: 0,
        label=lambda: labels[0] if labels else "",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestTimelineServer -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/_timeline.py tests/test_basic.py
git commit -m "feat: add timeline_server() reactive wiring"
```

---

### Task 5: Export new public API from `__init__.py`

**Files:**
- Modify: `src/shiny_deckgl/__init__.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_basic.py`:

```python
class TestTimeSpaceExports:
    """Verify new public API is exported from the package."""

    def test_in_bounds_exported(self):
        assert hasattr(m, "in_bounds")

    def test_on_viewport_change_exported(self):
        assert hasattr(m, "on_viewport_change")

    def test_timeline_control_exported(self):
        assert hasattr(m, "timeline_control")

    def test_timeline_server_exported(self):
        assert hasattr(m, "timeline_server")

    def test_month_labels_exported(self):
        assert hasattr(m, "MONTH_LABELS")
        assert len(m.MONTH_LABELS) == 12
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestTimeSpaceExports -v`
Expected: FAIL — `AssertionError` (attributes not found)

- [ ] **Step 3: Add imports and exports to `__init__.py`**

Add after the `from ._animation import animate_prop` line (line 200):

```python
# --- _viewport ---
from ._viewport import on_viewport_change, in_bounds  # noqa: F401

# --- _timeline ---
from ._timeline import timeline_control, timeline_server  # noqa: F401

# --- demo data (new in v1.9.0) ---
from ._demo_data import MONTH_LABELS  # noqa: F401
```

Add to the `__all__` list, after `"animate_prop"` (line 440):

```python
    # Viewport-aware loading (v1.9.0)
    "on_viewport_change",
    "in_bounds",
    # Timeline animation (v1.9.0)
    "timeline_control",
    "timeline_server",
    "MONTH_LABELS",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestTimeSpaceExports -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/__init__.py tests/test_basic.py
git commit -m "feat: export viewport and timeline API from package"
```

---

### Task 6: `make_sea_temperature_grid()` demo data

**Files:**
- Modify: `src/shiny_deckgl/_demo_data.py`
- Test: `tests/test_basic.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_basic.py`:

```python
from shiny_deckgl._demo_data import make_sea_temperature_grid


class TestSeaTemperatureGrid:
    """Tests for the synthetic Baltic Sea temperature data generator."""

    def test_returns_list_of_dicts(self):
        data = make_sea_temperature_grid()
        assert isinstance(data, list)
        assert len(data) > 0
        assert isinstance(data[0], dict)

    def test_required_keys(self):
        data = make_sea_temperature_grid()
        required = {"position", "temperature_c", "name", "month_label", "bin_label", "elevation"}
        for row in data[:5]:
            assert required.issubset(row.keys()), f"Missing keys in {row.keys()}"

    def test_month_affects_temperature(self):
        winter = make_sea_temperature_grid(month=1)  # Feb
        summer = make_sea_temperature_grid(month=7)  # Aug
        avg_winter = sum(d["temperature_c"] for d in winter) / len(winter)
        avg_summer = sum(d["temperature_c"] for d in summer) / len(summer)
        assert avg_summer > avg_winter, "Summer should be warmer than winter"

    def test_bounds_filtering(self):
        all_data = make_sea_temperature_grid()
        bounds = {"sw": [18.0, 56.0], "ne": [22.0, 58.0]}
        filtered = make_sea_temperature_grid(bounds=bounds)
        assert len(filtered) < len(all_data), "Bounds should reduce point count"
        for row in filtered:
            lon, lat = row["position"]
            assert 18.0 <= lon <= 22.0
            assert 56.0 <= lat <= 58.0

    def test_none_bounds_returns_all(self):
        all_data = make_sea_temperature_grid(bounds=None)
        assert len(all_data) > 100, "Should return many points with no bounds"

    def test_month_range(self):
        """All 12 months should work without error."""
        for m in range(12):
            data = make_sea_temperature_grid(month=m)
            assert len(data) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestSeaTemperatureGrid -v`
Expected: FAIL — `ImportError: cannot import name 'make_sea_temperature_grid'`

- [ ] **Step 3: Implement `make_sea_temperature_grid`**

Add to `src/shiny_deckgl/_demo_data.py` before the `__all__` or at the end of the data generator section. Find the appropriate location near other `make_*` functions:

```python
# ---------------------------------------------------------------------------
# Baltic Sea surface temperature grid (synthetic, seasonal)
# ---------------------------------------------------------------------------

MONTH_LABELS: list[str] = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Pre-compute the grid once (immutable base positions)
_TEMP_GRID_LON_RANGE = (10.0, 30.0)   # Baltic Sea longitude extent
_TEMP_GRID_LAT_RANGE = (54.0, 66.0)   # Baltic Sea latitude extent
_TEMP_GRID_STEP = 0.5                  # ~55 km at 60°N


@functools.lru_cache(maxsize=1)
def _temperature_grid_positions() -> list[tuple[float, float]]:
    """Generate the fixed grid of positions covering the Baltic Sea."""
    positions = []
    lon = _TEMP_GRID_LON_RANGE[0]
    while lon <= _TEMP_GRID_LON_RANGE[1]:
        lat = _TEMP_GRID_LAT_RANGE[0]
        while lat <= _TEMP_GRID_LAT_RANGE[1]:
            positions.append((round(lon, 2), round(lat, 2)))
            lat += _TEMP_GRID_STEP
        lon += _TEMP_GRID_STEP
    return positions


def make_sea_temperature_grid(
    bounds: dict | None = None,
    month: int = 0,
) -> list[dict]:
    """Generate synthetic Baltic Sea surface temperature data.

    Parameters
    ----------
    bounds
        Optional viewport bounds ``{sw: [lon, lat], ne: [lon, lat]}``.
        When provided, only grid cells within bounds are returned.
    month
        Month index (0=Jan, 11=Dec). Affects the temperature via a
        sinusoidal seasonal cycle.

    Returns
    -------
    list[dict]
        Each dict has: ``position``, ``temperature_c``, ``name``,
        ``month_label``, ``elevation`` (for grid_cell_layer height).
    """
    positions = _temperature_grid_positions()

    # Seasonal model: sinusoidal, coldest in Feb (month=1), warmest in Aug (month=7)
    # T_base = 10 + 8 * sin((month - 1) * pi / 6 - pi/2)
    # => Feb: 10 - 8 = 2°C,  Aug: 10 + 8 = 18°C
    import math
    seasonal = 10.0 + 8.0 * math.sin((month - 1) * math.pi / 6.0 - math.pi / 2.0)

    month_label = MONTH_LABELS[month % 12]
    rng = random.Random(42 + month)  # Deterministic per month

    result: list[dict] = []
    for lon, lat in positions:
        # Spatial filter
        if bounds is not None:
            sw, ne = bounds["sw"], bounds["ne"]
            if not (sw[0] <= lon <= ne[0] and sw[1] <= lat <= ne[1]):
                continue

        # Latitude gradient: colder further north
        lat_offset = -0.5 * (lat - 57.0)
        # Random noise (seeded by position for consistency)
        noise = rng.gauss(0, 1.5)
        temp = round(seasonal + lat_offset + noise, 1)

        # Elevation for 3D extrusion (proportional to temperature)
        elevation = max(0, temp) * 500

        # Bin label for legend (5°C bins)
        bin_lo = int(temp // 5) * 5
        bin_label = f"{bin_lo}–{bin_lo + 5}°C"

        result.append({
            "position": [lon, lat],
            "temperature_c": temp,
            "name": f"{lat:.1f}°N {lon:.1f}°E",
            "month_label": month_label,
            "bin_label": bin_label,
            "elevation": elevation,
        })

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n shiny python -m pytest tests/test_basic.py::TestSeaTemperatureGrid -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/_demo_data.py tests/test_basic.py
git commit -m "feat: add make_sea_temperature_grid() synthetic data generator"
```

---

### Task 7: `timespace_widget` MapWidget instance

**Files:**
- Modify: `src/shiny_deckgl/_app_widgets.py`

- [ ] **Step 1: Add the widget instance**

Add after the `widgets_gallery_widget` definition (before `__all__`):

```python
# Tab 11 — Time & Space (viewport-aware + timeline)
timespace_widget = MapWidget(
    "timespace_map",
    tooltip={
        "html": (
            "<b>{name}</b><br/>"
            "Temp: {temperature_c}°C<br/>"
            "Month: {month_label}"
        ),
        "style": TOOLTIP_STYLE,
    },
    view_state=BALTIC_VIEW,
)
```

Add `"timespace_widget"` to the `__all__` list.

- [ ] **Step 2: Run existing tests to verify nothing is broken**

Run: `conda run -n shiny python -m pytest tests/test_basic.py -x -q`
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/shiny_deckgl/_app_widgets.py
git commit -m "feat: add timespace_widget for Tab 11"
```

---

### Task 8: Tab 11 UI

**Files:**
- Modify: `src/shiny_deckgl/_app_ui.py`

- [ ] **Step 1: Add imports for `timespace_widget` and `timeline_control`**

Add `timespace_widget` to the import from `._app_widgets` (around line 38):

```python
from ._app_widgets import (
    gallery_widget,
    maplibre_widget,
    events_widget,
    palette_widget,
    adv_widget,
    draw_widget,
    three_d_widget,
    seal_widget,
    widgets_gallery_widget,
    timespace_widget,
)
```

Add import for `timeline_control` and `MONTH_LABELS` near the top of the file:

```python
from ._timeline import timeline_control
from ._demo_data import MONTH_LABELS
```

- [ ] **Step 2: Add Tab 11 UI**

Insert before the `# -- About (right-aligned)` section (before line 1395), after the Widgets tab closing `),`.

Note: The `timeline_control("ts_timeline", labels=MONTH_LABELS)` call uses the reusable module from Task 3. It generates Play/Pause buttons, a slider, and a label output — all namespaced under `"ts_timeline"`.

```python
    # -- Tab 11: Time & Space (viewport-aware loading + timeline) ----------
    ui.nav_panel(
        "\U0001F321\uFE0F Time & Space",
        ui.layout_sidebar(
            ui.sidebar(
                ui.tags.small(
                    "v1.9.0", class_="badge text-bg-info mb-2",
                ),
                sidebar_hint(
                    "Viewport-aware lazy loading + time-series animation. "
                    "Only data within the visible map area is loaded from "
                    "the server. Pan/zoom to load new data. Use the "
                    "timeline to animate Baltic Sea surface temperature "
                    "across 12 months."
                ),
                ui.accordion(
                    ui.accordion_panel(
                        "\U0001F4C5 Timeline",
                        timeline_control("ts_timeline", labels=MONTH_LABELS),
                    ),
                    ui.accordion_panel(
                        "\u2699 Options",
                        ui.input_switch(
                            "ts_show_ports", "Show port markers",
                            value=True,
                        ),
                        ui.input_switch(
                            "ts_3d", "3D extrusion",
                            value=False,
                        ),
                        ui.input_slider(
                            "ts_cell_size", "Cell size (m)",
                            min=10000, max=80000, value=40000,
                            step=5000,
                        ),
                    ),
                    ui.accordion_panel(
                        "\U0001F4CA Info",
                        ui.output_text_verbatim("ts_info"),
                    ),
                    id="tab11_accordion",
                    open=["\U0001F4C5 Timeline"],
                    multiple=True,
                ),
                width=280,
            ),
            timespace_widget.ui(height="60vh"),
            ui.card(
                ui.card_header("\U0001F321\uFE0F Temperature Status"),
                ui.output_text_verbatim("ts_status"),
            ),
        ),
    ),
```

- [ ] **Step 3: Run the app import test**

Run: `conda run -n shiny python -c "from shiny_deckgl._app_ui import build_ui; print('UI OK')"`
Expected: `UI OK`

- [ ] **Step 4: Commit**

```bash
git add src/shiny_deckgl/_app_ui.py
git commit -m "feat: add Tab 11 'Time & Space' UI layout"
```

---

### Task 9: Tab 11 server logic

**Files:**
- Modify: `src/shiny_deckgl/_app_server.py`

- [ ] **Step 1: Add imports**

Add to the imports at the top of `_app_server.py`:

After the `from .ibm import ...` line (around line 109), add:

```python
from ._viewport import on_viewport_change
from ._timeline import timeline_server
from ._demo_data import make_sea_temperature_grid, MONTH_LABELS
```

Add `timespace_widget` to the widget imports (around line 126):

```python
from ._app_widgets import (
    ...
    timespace_widget,
)
```

- [ ] **Step 2: Add Tab 11 server logic**

Insert inside the `server()` function, after the Widgets Gallery section (after line ~1690), before the function ends.

**Key:** This uses `timeline_server()` from Task 4 and `on_viewport_change()` from Task 2 — the reusable components. Reading `tl.index()` inside the viewport callback auto-creates a reactive dependency, so month changes trigger re-fetch without explicit wiring.

```python
    # ===================================================================
    # Tab 11: Time & Space (viewport-aware loading + timeline)
    # ===================================================================

    # Wire the timeline_control() UI using the reusable timeline_server()
    tl = timeline_server("ts_timeline", labels=MONTH_LABELS)

    @output
    @render.text
    def ts_info():
        vs = input[timespace_widget.view_state_input_id]()
        if vs and "bounds" in vs:
            b = vs["bounds"]
            return (
                f"Month: {tl.label()}\n"
                f"Zoom: {vs.get('zoom', 0):.1f}\n"
                f"Bounds: [{b['sw'][0]:.1f}, {b['sw'][1]:.1f}] "
                f"to [{b['ne'][0]:.1f}, {b['ne'][1]:.1f}]"
            )
        return "Pan or zoom the map to load data"

    # Viewport-aware data loading — uses on_viewport_change() decorator.
    # Reading tl.index() and input.ts_* inside the callback creates
    # reactive dependencies, so the callback re-fires on month change,
    # option toggles, AND viewport pans — all automatically.
    @on_viewport_change(timespace_widget, input, session, debounce_ms=300)
    async def _ts_load_data(bounds, zoom):
        month_idx = tl.index()
        data = make_sea_temperature_grid(bounds=bounds, month=month_idx)

        layers: list[dict] = []

        if data:
            # Color by temperature: blue (cold) -> red (warm)
            # color_bins() maps values to colors using equal-width bins
            from .colors import color_bins, PALETTE_THERMAL
            colors = color_bins(
                [d["temperature_c"] for d in data],
                n_bins=6,
                palette=PALETTE_THERMAL,
            )
            for d, c in zip(data, colors):
                d["fill_color"] = c

            layers.append(
                grid_cell_layer(
                    "ts_temp_grid",
                    data,
                    getPosition="@@=d.position",
                    getFillColor="@@=d.fill_color",
                    cellSize=input.ts_cell_size(),
                    extruded=input.ts_3d(),
                    getElevation="@@=d.elevation" if input.ts_3d() else 0,
                    elevationScale=1,
                    pickable=True,
                    opacity=0.8,
                )
            )

        if input.ts_show_ports():
            layers.append(
                scatterplot_layer(
                    "ts_ports",
                    PORTS,
                    getPosition="@@=[d.lon, d.lat]",
                    getRadius=8000,
                    getFillColor=[255, 140, 0, 200],
                    getLineColor=[255, 255, 255, 200],
                    lineWidthMinPixels=2,
                    stroked=True,
                    pickable=True,
                )
            )

        # Return layers — on_viewport_change calls widget.update() for us
        # But we also want widgets, so call update directly
        await timespace_widget.update(
            session, layers,
            widgets=[
                loading_widget(),
                layer_legend_widget(
                    title=f"SST — {MONTH_LABELS[month_idx]}",
                    auto_introspect=True,
                    placement="top-left",
                ),
            ],
        )
        return None  # Return None to skip the decorator's auto-update

    @output
    @render.text
    def ts_status():
        month_label = tl.label()
        return f"Month: {month_label}"
```

- [ ] **Step 3: Verify layer function imports**

The `grid_cell_layer` and `scatterplot_layer` functions are used in the server code. Check that they are already imported in `_app_server.py` (they are used in other tabs). The existing imports use them from `.layers` — they should already be available. If not, add:

```python
from .layers import grid_cell_layer, scatterplot_layer
```

Note: `PORTS` is already imported at line 63 of `_app_server.py` from `._demo_data`.

- [ ] **Step 4: Verify the app loads**

Run: `conda run -n shiny python -c "from shiny_deckgl.app import app; print('App OK')"`
Expected: `App OK`

- [ ] **Step 5: Commit**

```bash
git add src/shiny_deckgl/_app_server.py
git commit -m "feat: add Tab 11 server logic with viewport-aware temperature loading"
```

---

### Task 10: Run full test suite and fix

**Files:** All modified files

- [ ] **Step 1: Run the full test suite**

Run: `conda run -n shiny python -m pytest tests/ -v --tb=short 2>&1 | tail -50`
Expected: All tests pass. If any fail, fix them.

- [ ] **Step 2: Run the demo app import check**

Run: `conda run -n shiny python -c "from shiny_deckgl import app; print(type(app))"`
Expected: `<class 'shiny.app.App'>`

- [ ] **Step 3: Verify new exports**

Run:
```bash
conda run -n shiny python -c "
from shiny_deckgl import (
    on_viewport_change, in_bounds,
    timeline_control, timeline_server, MONTH_LABELS,
)
print('All exports OK')
print(f'MONTH_LABELS: {MONTH_LABELS}')
"
```
Expected: `All exports OK` and 12 month labels printed

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "fix: address test failures from Time & Space integration"
```

(Skip if no fixes were needed.)
