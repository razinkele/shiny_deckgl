# shiny\_deckgl API Reference

> **Version 0.1.0** — A Shiny for Python bridge to deck.gl and MapLibre GL JS.

```python
import shiny_deckgl as sdgl
```

---

## Table of Contents

- [Head Dependency](#head-dependency)
- [MapWidget](#mapwidget)
  - [Constructor](#constructor)
  - [Shiny Input Properties](#shiny-input-properties)
  - [ui()](#ui)
  - [update()](#update)
  - [set\_layer\_visibility()](#set_layer_visibility)
  - [add\_drag\_marker()](#add_drag_marker)
  - [update\_tooltip()](#update_tooltip)
  - [to\_json() / from\_json()](#to_json--from_json)
  - [to\_html()](#to_html)
- [Layer Helpers](#layer-helpers)
  - [layer()](#layer)
  - [scatterplot\_layer()](#scatterplot_layer)
  - [geojson\_layer()](#geojson_layer)
  - [tile\_layer()](#tile_layer)
  - [bitmap\_layer()](#bitmap_layer)
- [Basemap Constants](#basemap-constants)
- [Color Utilities](#color-utilities)
  - [Palette Constants](#palette-constants)
  - [color\_range()](#color_range)
  - [color\_bins()](#color_bins)
  - [color\_quantiles()](#color_quantiles)
- [Binary Data Transport](#binary-data-transport)
  - [encode\_binary\_attribute()](#encode_binary_attribute)
- [View Helpers](#view-helpers)
  - [map\_view()](#map_view)
  - [orthographic\_view()](#orthographic_view)
  - [first\_person\_view()](#first_person_view)
- [Accessor Syntax](#accessor-syntax)
- [WMS Tile Layers](#wms-tile-layers)
- [Tooltip Configuration](#tooltip-configuration)
- [Lighting & Effects](#lighting--effects)
- [CLI](#cli)

---

## Head Dependency

### `head_includes()`

```python
shiny_deckgl.head_includes() -> HTMLDependency
```

Returns an `HTMLDependency` that injects deck.gl v9.1.4, MapLibre GL JS v3.6.2, and local shiny\_deckgl assets into the page `<head>`.

Place as a **direct child** of any `ui.page_*()` layout:

```python
from shiny import ui
from shiny_deckgl import head_includes

app_ui = ui.page_fluid(
    head_includes(),
    # ... rest of UI
)
```

> **Warning:** Do **not** wrap the return value in `ui.head_content()` — the
> `HTMLDependency` object already handles `<head>` injection.  Wrapping it
> would silently drop all scripts.

---

## MapWidget

The central class that binds a deck.gl/MapLibre map to a Shiny session.

### Constructor

```python
MapWidget(
    id: str,
    view_state: dict | None = None,
    style: str = CARTO_POSITRON,
    tooltip: dict | None = None,
    mapbox_api_key: str | None = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | *(required)* | Unique HTML element ID for this map instance. |
| `view_state` | `dict \| None` | `{"longitude": 21.1, "latitude": 55.7, "zoom": 8}` | Initial camera with keys `longitude`, `latitude`, `zoom`, and optionally `pitch`, `bearing`, `minZoom`, `maxZoom`. |
| `style` | `str` | `CARTO_POSITRON` | MapLibre style URL. Use a `CARTO_*` / `OSM_*` constant or any MapLibre-compatible style URL. |
| `tooltip` | `dict \| None` | `None` | Tooltip configuration (see [Tooltip Configuration](#tooltip-configuration)). |
| `mapbox_api_key` | `str \| None` | `None` | If provided, enables `mapbox://` style URLs by injecting an access token. |

**Example:**

```python
from shiny_deckgl import MapWidget, CARTO_DARK

map_widget = MapWidget(
    "mymap",
    view_state={"longitude": -122.4, "latitude": 37.8, "zoom": 11, "pitch": 45},
    style=CARTO_DARK,
    tooltip={"html": "<b>{name}</b><br/>depth: {depth} m"},
)
```

### Shiny Input Properties

Each `MapWidget` exposes reactive Shiny inputs automatically:

| Property | Shiny Input Name | Fires When |
|---|---|---|
| `widget.click_input_id` | `"{id}_click"` | User clicks a pickable feature |
| `widget.hover_input_id` | `"{id}_hover"` | User hovers over a pickable feature |
| `widget.view_state_input_id` | `"{id}_view_state"` | Camera stops moving (`moveend`) |
| `widget.drag_input_id` | `"{id}_drag"` | User finishes dragging a marker |

**Click / Hover payload:**

```python
{
    "mapId": "mymap",
    "layerId": "scatter",
    "object": { ... },        # the picked feature's properties
    "coordinate": [lng, lat]
}
```

**View state payload:**

```python
{
    "longitude": -122.4,
    "latitude": 37.8,
    "zoom": 11.5,
    "pitch": 45,
    "bearing": 0
}
```

**Drag payload:**

```python
{"longitude": -122.41, "latitude": 37.79}
```

### `ui()`

```python
widget.ui(width: str = "100%", height: str = "400px") -> ui.Tag
```

Returns a Shiny `ui.Tag` `<div>` configured for this map.  Place it in your layout:

```python
app_ui = ui.page_fluid(
    head_includes(),
    map_widget.ui(height="600px"),
)
```

### `update()`

```python
await widget.update(
    session,
    layers: list[dict],
    view_state: dict | None = None,
    transition_duration: int = 0,
    effects: list[dict] | None = None,
    views: list[dict] | None = None,
) -> None
```

Push a new set of deck.gl layers (and optionally a new camera, effects, or views) to the map.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `session` | `Session` | *(required)* | The active Shiny session. |
| `layers` | `list[dict]` | *(required)* | Layer dicts from `*_layer()` helpers or `layer()`. |
| `view_state` | `dict \| None` | `None` | New camera position to animate/jump to. |
| `transition_duration` | `int` | `0` | Milliseconds for `flyTo` animation.  `0` = instant `jumpTo`. |
| `effects` | `list[dict] \| None` | `None` | Lighting / post-processing effects (see [Lighting & Effects](#lighting--effects)). |
| `views` | `list[dict] \| None` | `None` | View specs from `map_view()`, `orthographic_view()`, etc. |

**Example:**

```python
@reactive.effect
@reactive.event(input.go)
async def _():
    await map_widget.update(
        session,
        layers=[scatterplot_layer("pts", my_data)],
        view_state={"longitude": 10, "latitude": 50, "zoom": 6},
        transition_duration=2000,
    )
```

### `set_layer_visibility()`

```python
await widget.set_layer_visibility(
    session,
    visibility: dict[str, bool],
) -> None
```

Toggle layer visibility **without resending data** — the JS client patches the existing layer stack.

```python
await map_widget.set_layer_visibility(session, {
    "heatmap": False,
    "scatter": True,
})
```

### `add_drag_marker()`

```python
await widget.add_drag_marker(
    session,
    longitude: float | None = None,
    latitude: float | None = None,
) -> None
```

Place a draggable MapLibre marker on the map.  When the user finishes dragging, the new position is sent to `input[widget.drag_input_id]()`.

| Parameter | Default | Description |
|---|---|---|
| `longitude` | Centre of current view | Initial marker longitude. |
| `latitude` | Centre of current view | Initial marker latitude. |

### `update_tooltip()`

```python
await widget.update_tooltip(
    session,
    tooltip: dict | None = None,
) -> None
```

Update the tooltip configuration **dynamically** without re-rendering the map.  Pass a new tooltip dict (same format as the constructor's `tooltip` parameter), or `None` to disable tooltips.

```python
await widget.update_tooltip(session, {
    "html": "<b>{species}</b><br/>Depth: {depth} m",
    "style": {"backgroundColor": "#0a2a4a", "color": "#ddf"},
})

# Disable tooltips
await widget.update_tooltip(session, None)
```

### `to_json()` / `from_json()`

```python
json_str = widget.to_json(layers, effects=None)       # -> str
widget2, layers2 = MapWidget.from_json(json_str)       # -> (MapWidget, list[dict])
```

Serialise/deserialise the full map specification (view state, style, tooltip, layers, effects) to/from a JSON string.  Useful for saving map snapshots or transferring specs between sessions.

### `to_html()`

```python
html_str = widget.to_html(
    layers: list[dict],
    path: str | Path | None = None,
    effects: list[dict] | None = None,
    title: str = "shiny_deckgl Map",
) -> str
```

Export the map as a **standalone HTML file** that works without Shiny.  The file embeds CDN links for deck.gl and MapLibre, inlines all layer data, and can be opened in any browser.

| Parameter | Default | Description |
|---|---|---|
| `layers` | *(required)* | Layer dicts to embed. |
| `path` | `None` | File path to write.  If `None`, returns the HTML string without writing. |
| `effects` | `None` | Optional effects to embed. |
| `title` | `"shiny_deckgl Map"` | HTML `<title>`. |

```python
html = map_widget.to_html(
    layers=[scatterplot_layer("pts", data)],
    path="export/mymap.html",
)
```

---

## Layer Helpers

All layer helpers return plain `dict` objects that are passed to `widget.update()`.

### `layer()`

```python
layer(
    type: str,
    id: str,
    data=None,
    *,
    extensions: list[str] | None = None,
    **kwargs,
) -> dict
```

Create an **arbitrary** deck.gl layer.  Works for any layer class — the JS client resolves `deck[type]` dynamically.

| Parameter | Description |
|---|---|
| `type` | deck.gl layer class name, e.g. `"HeatmapLayer"`, `"PathLayer"`, `"ColumnLayer"`. |
| `id` | Unique layer identifier. |
| `data` | Layer data — `list`, `dict`, URL `str`, `DataFrame`, or `GeoDataFrame`. |
| `extensions` | deck.gl extension class names, e.g. `["DataFilterExtension"]`. |
| `**kwargs` | Any deck.gl layer properties. Use `visible=False` to hide without removing. |

**Data serialisation:** `GeoDataFrame` → GeoJSON `FeatureCollection`;  `DataFrame` → list of row-dicts;  everything else passed through.

```python
layer("HeatmapLayer", "heat", data, intensity=1, radiusPixels=60)
layer("PathLayer", "routes", paths, getColor=[255, 0, 0], widthMinPixels=2)
```

### `scatterplot_layer()`

```python
scatterplot_layer(id: str, data: list | dict, **kwargs) -> dict
```

Convenience wrapper for `ScatterplotLayer`.

**Defaults applied:**

| Property | Default |
|---|---|
| `pickable` | `True` |
| `getPosition` | `"@@d"` (identity accessor) |
| `getFillColor` | `[200, 0, 80, 180]` |
| `radiusMinPixels` | `5` |

```python
scatterplot_layer("pts", [[21.1, 55.7], [21.2, 55.8]],
                  getFillColor=[0, 200, 100], radiusMinPixels=8)
```

### `geojson_layer()`

```python
geojson_layer(id: str, data: dict | list, **kwargs) -> dict
```

Convenience wrapper for `GeoJsonLayer`.

**Defaults applied:**

| Property | Default |
|---|---|
| `pickable` | `True` |
| `getFillColor` | `[0, 128, 255, 120]` |
| `getLineColor` | `[0, 128, 255]` |
| `lineWidthMinPixels` | `1` |

```python
geojson_layer("regions", geojson_fc, getFillColor="@@=d.properties.color")
```

### `tile_layer()`

```python
tile_layer(id: str, data: str | list, **kwargs) -> dict
```

Create a `TileLayer` for **XYZ raster tiles** or **WMS GetMap** requests.

**Defaults applied:**

| Property | Default |
|---|---|
| `minZoom` | `0` |
| `maxZoom` | `19` |
| `tileSize` | `256` |
| `renderSubLayers` | `"@@BitmapLayer"` |

For XYZ tiles, use `{x}`, `{y}`, `{z}` placeholders:

```python
tile_layer("osm", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
```

For WMS, use a `{bbox-epsg-3857}` or `{bbox-epsg-4326}` placeholder — see [WMS Tile Layers](#wms-tile-layers).

### `bitmap_layer()`

```python
bitmap_layer(id: str, image: str, bounds: list, **kwargs) -> dict
```

Create a `BitmapLayer` for a static image overlay.

| Parameter | Description |
|---|---|
| `image` | URL of the image. |
| `bounds` | `[left, bottom, right, top]` in WGS 84. |

```python
bitmap_layer("overlay", "https://example.com/chart.png",
             bounds=[-10, 35, 40, 70])
```

---

## Basemap Constants

Pre-defined MapLibre style URLs:

| Constant | URL | Description |
|---|---|---|
| `CARTO_POSITRON` | `basemaps.cartocdn.com/.../positron-nolabels-gl-style/style.json` | Light, minimal basemap |
| `CARTO_DARK` | `basemaps.cartocdn.com/.../dark-matter-nolabels-gl-style/style.json` | Dark basemap |
| `CARTO_VOYAGER` | `basemaps.cartocdn.com/.../voyager-nolabels-gl-style/style.json` | Colourful general-purpose |
| `OSM_LIBERTY` | `tiles.openfreemap.org/styles/liberty` | OpenStreetMap Liberty style |

Pass any MapLibre-compatible style URL to `MapWidget(style=...)`.

---

## Color Utilities

### Palette Constants

Six-stop `[R, G, B]` palettes for use with the color functions:

| Constant | Description |
|---|---|
| `PALETTE_VIRIDIS` | Perceptually uniform purple → yellow |
| `PALETTE_PLASMA` | Purple → orange → yellow |
| `PALETTE_OCEAN` | Dark navy → teal → light aqua |
| `PALETTE_THERMAL` | Dark blue → green → red |
| `PALETTE_CHLOROPHYLL` | Light yellow → dark green |

### `color_range()`

```python
color_range(n: int = 6, palette: list[list[int]] | None = None) -> list[list[int]]
```

Generate `n` evenly-spaced `[R, G, B, 255]` colours by linearly interpolating a palette.

```python
colors = color_range(10, PALETTE_OCEAN)
# → 10 RGBA colours from dark navy to light aqua
```

### `color_bins()`

```python
color_bins(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]
```

Map each value to a colour using **equal-width** bins across the value range.

Returns one `[R, G, B, A]` per input value.

```python
depths = [10, 45, 120, 200, 500]
fill_colors = color_bins(depths, n_bins=5, palette=PALETTE_OCEAN)
```

### `color_quantiles()`

```python
color_quantiles(
    values: list[float],
    n_bins: int = 6,
    palette: list[list[int]] | None = None,
) -> list[list[int]]
```

Map each value to a colour using **quantile-based** bins (each bin contains approximately the same number of values).

Returns one `[R, G, B, A]` per input value.

---

## Binary Data Transport

### `encode_binary_attribute()`

```python
encode_binary_attribute(array) -> dict
```

Encode a numpy array as a base64 binary transport dict for deck.gl [binary attributes](https://deck.gl/docs/developer-guide/performance#supply-attributes-directly).  This avoids JSON-serialising large numeric arrays.

| Parameter | Description |
|---|---|
| `array` | A `numpy.ndarray` (`float32`, `float64`, `uint8`, or `int32`). Other dtypes are cast to `float32`. |

**Returns:** `{"@@binary": True, "dtype": "float32", "size": <n_components>, "value": "<base64>"}`

The JS client decodes this back into a `TypedArray` attribute.

```python
import numpy as np

positions = np.array([[21.1, 55.7], [21.2, 55.8]], dtype="float32")
layer("ScatterplotLayer", "pts",
      data={"length": len(positions)},
      getPosition=encode_binary_attribute(positions))
```

> **Note:** `numpy` is an optional dependency — it is only imported when `encode_binary_attribute()` is called.

---

## View Helpers

Override the default `MapView` or use multiple views for split-screen / non-geo layouts.

### `map_view()`

```python
map_view(**kwargs) -> dict
```

Create a `MapView` spec.  Accepts any [MapView properties](https://deck.gl/docs/api-reference/core/map-view) such as `controller`, `x`, `y`, `width`, `height`.

### `orthographic_view()`

```python
orthographic_view(**kwargs) -> dict
```

Create an `OrthographicView` spec for non-geographic flat-plane visualisations (e.g. graph plots).

### `first_person_view()`

```python
first_person_view(**kwargs) -> dict
```

Create a `FirstPersonView` spec for immersive 3D walkthroughs.

**Multi-view example:**

```python
await widget.update(session, layers=my_layers, views=[
    map_view(id="main", controller=True, width="50%"),
    map_view(id="minimap", x="50%", width="50%", controller=False),
])
```

---

## Accessor Syntax

String-based accessor conventions that the JS client resolves into JavaScript functions:

| Syntax | Resolves To | Use Case |
|---|---|---|
| `"@@d"` | `d => d` | Identity — pass the whole datum (e.g. `[lon, lat]` arrays). |
| `"@@d.prop"` | `d => d["prop"]` | Simple property access. |
| `"@@=<expr>"` | `new Function('d', 'return ' + expr)` | Arbitrary JS expression. |

### Expression Accessor Examples

```python
# Access a nested property
scatterplot_layer("pts", data, getRadius="@@=d.properties.radius * 10")

# Conditional colour
geojson_layer("zones", fc,
    getFillColor="@@=d.properties.value > 50 ? [255,0,0] : [0,255,0]")

# Array indexing
layer("ScatterplotLayer", "pts", data, getPosition="@@=d.coordinates")
```

> **Security note:** Expression accessors use `new Function()`, which is equivalent to `eval()`. Only use with trusted data.

---

## WMS Tile Layers

The `tile_layer()` helper supports OGC **WMS GetMap** requests via special bbox placeholders.  The JS client detects these placeholders and automatically projects tile bounds into the requested CRS.

### Supported Placeholders

| Placeholder | CRS | Projection |
|---|---|---|
| `{bbox-epsg-3857}` | EPSG:3857 (Web Mercator) | Lon/lat → Mercator metres |
| `{bbox-epsg-4326}` | EPSG:4326 (WGS 84) | Lon/lat passed directly |

### How It Works

1. The JS client detects `{bbox-epsg-NNNN}` in the URL template.
2. For each tile, it computes the bounding box in the target CRS.
3. It replaces the placeholder with `minX,minY,maxX,maxY`.
4. It fetches the image via `fetch()` with error handling:
   - Non-200 responses → `null` (empty tile)
   - XML/text content-type → `null` (WMS error document)
   - Empty blob → `null`
   - Decode failure → `null` (silently ignored)
5. Valid images are rendered via `createImageBitmap()`.

### Example: EMODnet Bathymetry WMS

```python
wms_url = (
    "https://ows.emodnet-bathymetry.eu/wms?"
    "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
    "&FORMAT=image/png&TRANSPARENT=true"
    "&LAYERS=emodnet:mean_atlas_land"
    "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
    "&BBOX={bbox-epsg-3857}"
)

tile_layer("wms-bathy", wms_url, opacity=0.6)
```

### Dynamic WMS Discovery with OWSLib

Use [OWSLib](https://owslib.readthedocs.io/) to query WMS capabilities at runtime and let users pick layers:

```python
from owslib.wms import WebMapService

wms = WebMapService("https://ows.emodnet-bathymetry.eu/wms?", version="1.3.0")

# Build a choices dict for ui.input_select:  {layer_id: display_label}
choices = {name: meta.title or name for name, meta in wms.contents.items()}

# In the UI
ui.input_select("wms_layer", "WMS Layer:", choices=choices)

# In the server — rebuild tile_layer when selection changes
@reactive.effect
@reactive.event(input.wms_layer)
async def _rebuild():
    layer_name = input.wms_layer()
    safe_id = layer_name.replace(":", "_")
    url = (
        "https://ows.emodnet-bathymetry.eu/wms?"
        "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
        "&FORMAT=image/png&TRANSPARENT=true"
        f"&LAYERS={layer_name}"
        "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
        "&BBOX={bbox-epsg-3857}"
    )
    await widget.update(session, layers=[
        tile_layer(f"wms-{safe_id}", url, opacity=0.7),
    ])
```

> **Important:** Give each WMS layer selection a **unique layer ID** (e.g. `f"wms-{safe_id}"`).  deck.gl caches tiles by layer ID, so reusing the same ID when switching layers will show stale tiles.

---

## Tooltip Configuration

Pass a `tooltip` dict to `MapWidget` to enable hover tooltips on pickable layers.

```python
tooltip = {
    "html": "<b>{name}</b><br/>Depth: {depth} m<br/>Species: {species}",
    "style": {
        "backgroundColor": "#222",
        "color": "#fff",
        "fontSize": "13px",
        "padding": "6px 10px",
        "borderRadius": "4px",
    },
}

widget = MapWidget("mymap", tooltip=tooltip)
```

### Template Placeholders

Use `{field}` in the `html` template to interpolate feature properties. Nested access is supported: `{properties.name}`.

For GeoJSON features, properties are accessed from the `properties` object automatically.

---

## Lighting & Effects

Pass an `effects` list to `widget.update()` for ambient/point lighting:

```python
effects = [{
    "type": "LightingEffect",
    "ambientLight": {
        "color": [255, 255, 255],
        "intensity": 1.0,
    },
    "pointLights": [{
        "color": [255, 200, 150],
        "intensity": 2.0,
        "position": [21.1, 55.7, 8000],
    }],
}]

await widget.update(session, layers=my_layers, effects=effects)
```

The JS client resolves `LightingEffect` specs into `deck.LightingEffect` instances with `deck.AmbientLight` and `deck.PointLight` sub-objects.

---

## CLI

The package installs a `shiny_deckgl-demo` console script:

```bash
shiny_deckgl-demo
```

This launches the built-in demo app with sample data (two points near Klaipeda, Lithuania).

---

## Quick Start

```python
from shiny import App, reactive, ui
from shiny_deckgl import (
    MapWidget, head_includes, scatterplot_layer, CARTO_POSITRON
)

widget = MapWidget("map", style=CARTO_POSITRON,
                   tooltip={"html": "<b>{name}</b>"})

app_ui = ui.page_fluid(
    head_includes(),
    widget.ui(height="500px"),
)

def server(input, output, session):
    @reactive.effect
    async def _():
        data = [
            {"name": "Klaipeda", "coordinates": [21.12, 55.71]},
            {"name": "Nida", "coordinates": [20.97, 55.30]},
        ]
        await widget.update(session, layers=[
            scatterplot_layer("cities", data,
                              getPosition="@@=d.coordinates",
                              radiusMinPixels=8),
        ])

app = App(app_ui, server)
```
