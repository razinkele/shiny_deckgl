# Performance & Visualization Patterns

## Performance Patterns

### Static / Dynamic Layer Split

For apps with layers that update at different frequencies, split into
static layers (sent once via `update()`) and dynamic layers (sent per
tick via `partial_update()`):

```python
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
```

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

```python
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
```

> **Future:** A `colorMode="categorical"` option for `grid_layer` may
> be added in a future release.
