# shiny\_deckgl API Reference

> **Version 0.6.0** — A Shiny for Python bridge to deck.gl (v9.1.4) and MapLibre GL JS (v5.3.1).

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
- [Controls & Navigation (v0.2)](#controls--navigation-v02)
  - [add\_control()](#add_control)
  - [remove\_control()](#remove_control)
  - [fit\_bounds()](#fit_bounds)
  - [compute\_bounds()](#compute_bounds)
- [Native Sources & Layers (v0.3)](#native-sources--layers-v03)
  - [add\_source()](#add_source)
  - [remove\_source()](#remove_source)
  - [set\_source\_data()](#set_source_data)
  - [add\_maplibre\_layer()](#add_maplibre_layer)
  - [remove\_maplibre\_layer()](#remove_maplibre_layer)
  - [set\_paint\_property()](#set_paint_property)
  - [set\_layout\_property()](#set_layout_property)
  - [set\_filter()](#set_filter)
  - [set\_style()](#set_style)
- [Projection, Terrain & Popups (v0.4)](#projection-terrain--popups-v04)
  - [set\_projection()](#set_projection)
  - [set\_terrain()](#set_terrain)
  - [set\_sky()](#set_sky)
  - [add\_popup()](#add_popup)
  - [remove\_popup()](#remove_popup)
  - [query\_rendered\_features()](#query_rendered_features)
  - [query\_at\_lnglat()](#query_at_lnglat)
  - [add\_marker()](#add_marker)
  - [remove\_marker()](#remove_marker)
  - [clear\_markers()](#clear_markers)
- [Drawing, GeoPandas & Export (v0.5)](#drawing-geopandas--export-v05)
  - [enable\_draw()](#enable_draw)
  - [disable\_draw()](#disable_draw)
  - [get\_drawn\_features()](#get_drawn_features)
  - [delete\_drawn\_features()](#delete_drawn_features)
  - [add\_geodataframe()](#add_geodataframe)
  - [update\_geodataframe()](#update_geodataframe)
  - [set\_feature\_state()](#set_feature_state)
  - [remove\_feature\_state()](#remove_feature_state)
  - [export\_image()](#export_image)
- [Layer Helpers](#layer-helpers)
  - [layer()](#layer)
  - [scatterplot\_layer()](#scatterplot_layer)
  - [geojson\_layer()](#geojson_layer)
  - [tile\_layer()](#tile_layer)
  - [bitmap\_layer()](#bitmap_layer)
- [Basemap & Control Constants](#basemap--control-constants)
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

Returns an `HTMLDependency` that injects deck.gl v9.1.4, MapLibre GL JS v5.3.1, MapboxDraw v1.4.3, and local shiny\_deckgl assets into the page `<head>`.

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
    controls: list[dict] | None = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | *(required)* | Unique HTML element ID for this map instance. |
| `view_state` | `dict \| None` | `{"longitude": 21.1, "latitude": 55.7, "zoom": 8}` | Initial camera with keys `longitude`, `latitude`, `zoom`, and optionally `pitch`, `bearing`, `minZoom`, `maxZoom`. |
| `style` | `str` | `CARTO_POSITRON` | MapLibre style URL. Use a `CARTO_*` / `OSM_*` constant or any MapLibre-compatible style URL. |
| `tooltip` | `dict \| None` | `None` | Tooltip configuration (see [Tooltip Configuration](#tooltip-configuration)). |
| `mapbox_api_key` | `str \| None` | `None` | If provided, enables `mapbox://` style URLs by injecting an access token. |
| `controls` | `list[dict] \| None` | `[{"type": "navigation", "position": "top-right"}]` | Initial controls to add on map load. Each dict has `type` (see `CONTROL_TYPES`), optional `position` (see `CONTROL_POSITIONS`), and optional `options`. |

**Example:**

```python
from shiny_deckgl import MapWidget, CARTO_DARK

map_widget = MapWidget(
    "mymap",
    view_state={"longitude": -122.4, "latitude": 37.8, "zoom": 11, "pitch": 45},
    style=CARTO_DARK,
    tooltip={"html": "<b>{name}</b><br/>depth: {depth} m"},
    controls=[
        {"type": "navigation", "position": "top-left"},
        {"type": "scale", "position": "bottom-left", "options": {"unit": "metric"}},
    ],
)
```

### Shiny Input Properties

Each `MapWidget` exposes reactive Shiny inputs automatically:

| Property | Shiny Input Name | Fires When | Payload |
|---|---|---|---|
| `click_input_id` | `"{id}_click"` | User clicks a pickable deck.gl feature | `{mapId, layerId, object, coordinate}` |
| `hover_input_id` | `"{id}_hover"` | User hovers over a pickable deck.gl feature | `{mapId, layerId, object, coordinate}` |
| `view_state_input_id` | `"{id}_view_state"` | Camera stops moving (`moveend`) | `{longitude, latitude, zoom, pitch, bearing}` |
| `drag_input_id` | `"{id}_drag"` | User finishes dragging legacy drag marker | `{longitude, latitude}` |
| `map_click_input_id` | `"{id}_map_click"` | User clicks on the basemap (even empty areas) | `{longitude, latitude, point: {x, y}}` |
| `map_contextmenu_input_id` | `"{id}_map_contextmenu"` | User right-clicks on the map | `{longitude, latitude, point: {x, y}}` |
| `feature_click_input_id` | `"{id}_feature_click"` | User clicks a native MapLibre layer feature (with popup) | `{layerId, properties, longitude, latitude}` |
| `query_result_input_id` | `"{id}_query_result"` | Spatial query result arrives | `{requestId, features}` |
| `marker_click_input_id` | `"{id}_marker_click"` | User clicks a named marker | `{markerId, longitude, latitude}` |
| `marker_drag_input_id` | `"{id}_marker_drag"` | User finishes dragging a named marker | `{markerId, longitude, latitude}` |
| `drawn_features_input_id` | `"{id}_drawn_features"` | User creates/updates/deletes drawn geometry | GeoJSON FeatureCollection |
| `draw_mode_input_id` | `"{id}_draw_mode"` | Drawing mode changes | Mode string (e.g. `"draw_polygon"`) |
| `export_result_input_id` | `"{id}_export_result"` | Map screenshot is ready | `{requestId, dataUrl, width, height}` |

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

## Controls & Navigation (v0.2)

### `add_control()`

```python
await widget.add_control(
    session,
    control_type: str,
    position: str = "top-right",
    *,
    options: dict | None = None,
) -> None
```

Add a MapLibre control to the map.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `session` | `Session` | *(required)* | The active Shiny session. |
| `control_type` | `str` | *(required)* | One of `CONTROL_TYPES`: `"navigation"`, `"scale"`, `"fullscreen"`, `"geolocate"`, `"globe"`, `"terrain"`, `"attribution"`. |
| `position` | `str` | `"top-right"` | One of `CONTROL_POSITIONS`: `"top-left"`, `"top-right"`, `"bottom-left"`, `"bottom-right"`. |
| `options` | `dict \| None` | `None` | Control-specific options, e.g. `{"maxWidth": 200, "unit": "metric"}` for ScaleControl. |

```python
await widget.add_control(session, "navigation", "top-left")
await widget.add_control(session, "scale", "bottom-left",
                         options={"maxWidth": 200, "unit": "metric"})
```

### `remove_control()`

```python
await widget.remove_control(session, control_type: str) -> None
```

Remove a previously added MapLibre control by type.

```python
await widget.remove_control(session, "scale")
```

### `fit_bounds()`

```python
await widget.fit_bounds(
    session,
    bounds: list[list[float]],
    *,
    padding: int | dict[str, int] = 50,
    max_zoom: float | None = None,
    duration: int = 0,
) -> None
```

Fly/jump the camera to fit the given geographic bounds.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `session` | `Session` | *(required)* | The active Shiny session. |
| `bounds` | `list` | *(required)* | `[[sw_lng, sw_lat], [ne_lng, ne_lat]]` in WGS 84. |
| `padding` | `int \| dict` | `50` | Pixels of padding. Can be uniform `int` or `{"top": 10, "bottom": 10, "left": 10, "right": 10}`. |
| `max_zoom` | `float \| None` | `None` | Maximum zoom level (prevents over-zooming on small areas). |
| `duration` | `int` | `0` | Animation duration in ms. `0` = instant. |

```python
# Fit to Baltic Sea
await widget.fit_bounds(session, [[10.0, 54.0], [30.0, 66.0]],
                        padding=80, duration=2000)
```

### `compute_bounds()`

```python
MapWidget.compute_bounds(geojson: dict) -> list[list[float]]  # static
```

Compute `[[sw_lng, sw_lat], [ne_lng, ne_lat]]` from a GeoJSON object.  Useful with `fit_bounds()`.

```python
bounds = MapWidget.compute_bounds(my_geojson)
await widget.fit_bounds(session, bounds)
```

---

## Native Sources & Layers (v0.3)

### `add_source()`

```python
await widget.add_source(
    session,
    source_id: str,
    source_spec: dict,
) -> None
```

Add a native MapLibre source.

| Parameter | Type | Description |
| --- | --- | --- |
| `session` | `Session` | The active Shiny session. |
| `source_id` | `str` | Unique source identifier. |
| `source_spec` | `dict` | MapLibre source spec. Must include `"type"` (`"geojson"`, `"raster"`, `"vector"`, `"raster-dem"`, `"image"`, `"video"`). |

```python
await widget.add_source(session, "cities", {
    "type": "geojson",
    "data": {"type": "FeatureCollection", "features": [...]},
})
```

### `remove_source()`

```python
await widget.remove_source(session, source_id: str) -> None
```

Remove a native MapLibre source. All layers using this source must be removed first.

### `set_source_data()`

```python
await widget.set_source_data(session, source_id: str, data: dict | str) -> None
```

Update the data of an existing GeoJSON source without removing/re-adding it.  `data` can be a GeoJSON dict or a URL string.

```python
await widget.set_source_data(session, "cities", updated_geojson)
```

### `add_maplibre_layer()`

```python
await widget.add_maplibre_layer(
    session,
    layer_spec: dict,
    *,
    before_id: str | None = None,
) -> None
```

Add a native MapLibre rendering layer.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `session` | `Session` | *(required)* | The active Shiny session. |
| `layer_spec` | `dict` | *(required)* | MapLibre layer spec with at minimum `"id"`, `"type"`, and `"source"`. |
| `before_id` | `str \| None` | `None` | Insert before this layer ID.  `None` = on top. |

```python
await widget.add_maplibre_layer(session, {
    "id": "cities-circles",
    "type": "circle",
    "source": "cities",
    "paint": {"circle-radius": 6, "circle-color": "#FF0000"},
})
```

### `remove_maplibre_layer()`

```python
await widget.remove_maplibre_layer(session, layer_id: str) -> None
```

Remove a native MapLibre layer by id.

### `set_paint_property()`

```python
await widget.set_paint_property(
    session,
    layer_id: str,
    name: str,
    value,
) -> None
```

Set a paint property on a native MapLibre layer at runtime.

```python
await widget.set_paint_property(session, "cities-circles",
                                "circle-color", "#00FF00")
```

### `set_layout_property()`

```python
await widget.set_layout_property(
    session,
    layer_id: str,
    name: str,
    value,
) -> None
```

Set a layout property on a native MapLibre layer at runtime.

```python
await widget.set_layout_property(session, "cities-circles",
                                 "visibility", "none")
```

### `set_filter()`

```python
await widget.set_filter(
    session,
    layer_id: str,
    filter_expr: list | None = None,
) -> None
```

Set a data-driven filter on a native MapLibre layer.  Pass `None` to clear.

```python
await widget.set_filter(session, "cities-circles",
                        [">=", ["get", "population"], 100000])
```

### `set_style()`

```python
await widget.set_style(session, style: str) -> None
```

Change the entire basemap style dynamically.

> **Warning:** This destroys all native sources and layers.  Re-add them after the style loads.

```python
await widget.set_style(session, CARTO_DARK)
```

---

## Projection, Terrain & Popups (v0.4)

### `set_projection()`

```python
await widget.set_projection(
    session,
    projection: str = "mercator",
) -> None
```

Set the map projection.  Requires MapLibre GL JS v4+.

| Parameter | Values |
| --- | --- |
| `projection` | `"mercator"` (flat map, default) or `"globe"` (3D sphere). |

```python
await widget.set_projection(session, "globe")
```

### `set_terrain()`

```python
await widget.set_terrain(
    session,
    source: str | None = None,
    exaggeration: float = 1.0,
) -> None
```

Enable or disable 3D terrain rendering.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `source` | `str \| None` | *(required)* | ID of a `raster-dem` source (added via `add_source()`). Pass `None` to disable terrain. |
| `exaggeration` | `float` | `1.0` | Vertical exaggeration factor.  Values > 1 amplify relief. |

```python
# Add a DEM source first
await widget.add_source(session, "dem", {
    "type": "raster-dem",
    "url": "https://demotiles.maplibre.org/terrain-tiles/tiles.json",
    "tileSize": 256,
})
await widget.set_terrain(session, "dem", exaggeration=1.5)
```

### `set_sky()`

```python
await widget.set_sky(session, sky: dict | None = None) -> None
```

Set sky/atmosphere properties (works with terrain). Pass `None` to remove.

```python
await widget.set_sky(session, {
    "sky-color": "#199EF3",
    "horizon-color": "#ffffff",
    "fog-color": "#ffffff",
})
```

### `add_popup()`

```python
await widget.add_popup(
    session,
    layer_id: str,
    template: str,
    *,
    close_button: bool = True,
    close_on_click: bool = True,
    max_width: str = "300px",
    anchor: str | None = None,
) -> None
```

Attach a click popup to a native MapLibre layer.  Clicking a feature opens a popup with interpolated HTML.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `layer_id` | `str` | *(required)* | The MapLibre layer to attach popup to. |
| `template` | `str` | *(required)* | HTML template with `{property}` placeholders. |
| `close_button` | `bool` | `True` | Show a close button. |
| `close_on_click` | `bool` | `True` | Close when clicking elsewhere. |
| `max_width` | `str` | `"300px"` | CSS max-width. |
| `anchor` | `str \| None` | `None` | Popup anchor position. |

```python
await widget.add_popup(session, "cities-circles",
                       "<b>{name}</b><br/>Pop: {population}")
```

### `remove_popup()`

```python
await widget.remove_popup(session, layer_id: str) -> None
```

Remove a previously attached popup handler from a native layer.

### `query_rendered_features()`

```python
await widget.query_rendered_features(
    session,
    *,
    point: list[float] | None = None,
    bounds: list[list[float]] | None = None,
    layers: list[str] | None = None,
    filter_expr: list | None = None,
    request_id: str = "default",
) -> None
```

Query visible features at a pixel point or within a pixel bounding box.  The result arrives asynchronously as `input[widget.query_result_input_id]()`.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `point` | `list \| None` | `None` | `[x, y]` pixel coordinates on the canvas. |
| `bounds` | `list \| None` | `None` | `[[x1, y1], [x2, y2]]` pixel bounding box. |
| `layers` | `list \| None` | `None` | Restrict to these layer IDs. |
| `filter_expr` | `list \| None` | `None` | MapLibre filter expression. |
| `request_id` | `str` | `"default"` | Identifier for matching results. |

> Provide either `point` or `bounds`, not both.

### `query_at_lnglat()`

```python
await widget.query_at_lnglat(
    session,
    longitude: float,
    latitude: float,
    *,
    layers: list[str] | None = None,
    request_id: str = "default",
) -> None
```

Query features at a geographic coordinate (WGS 84).  The result arrives as `input[widget.query_result_input_id]()`.

```python
await widget.query_at_lnglat(session, 21.12, 55.71,
                             layers=["cities-circles"],
                             request_id="my-query")
```

### `add_marker()`

```python
await widget.add_marker(
    session,
    marker_id: str,
    longitude: float,
    latitude: float,
    *,
    color: str = "#3FB1CE",
    draggable: bool = False,
    popup_html: str | None = None,
) -> None
```

Add a named marker to the map.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `marker_id` | `str` | *(required)* | Unique marker identifier. |
| `longitude, latitude` | `float` | *(required)* | Marker position (WGS 84). |
| `color` | `str` | `"#3FB1CE"` | CSS color for the default marker pin. |
| `draggable` | `bool` | `False` | Allow the user to drag this marker. |
| `popup_html` | `str \| None` | `None` | HTML popup content shown on click. |

When `draggable=True`, drag-end position is sent to `input[widget.marker_drag_input_id]()`.
Clicks sent to `input[widget.marker_click_input_id]()`.

```python
await widget.add_marker(session, "hq", 21.12, 55.71,
                        color="#FF0000", draggable=True,
                        popup_html="<b>Headquarters</b>")
```

### `remove_marker()`

```python
await widget.remove_marker(session, marker_id: str) -> None
```

Remove a named marker from the map.

### `clear_markers()`

```python
await widget.clear_markers(session) -> None
```

Remove all named markers from the map.

---

## Drawing, GeoPandas & Export (v0.5)

### `enable_draw()`

```python
await widget.enable_draw(
    session,
    *,
    modes: list[str] | None = None,
    controls: dict[str, bool] | None = None,
    default_mode: str = "simple_select",
) -> None
```

Enable MapboxDraw drawing tools on the map.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `modes` | `list \| None` | `["draw_point", "draw_line_string", "draw_polygon"]` | Which drawing modes to enable. |
| `controls` | `dict \| None` | `None` | Override individual control visibility, e.g. `{"point": True, "polygon": False}`. |
| `default_mode` | `str` | `"simple_select"` | Initial mode. |

Drawn features are sent to `input[widget.drawn_features_input_id]()` as a GeoJSON FeatureCollection.
Mode changes sent to `input[widget.draw_mode_input_id]()`.

```python
await widget.enable_draw(session, modes=["draw_polygon"])
```

### `disable_draw()`

```python
await widget.disable_draw(session) -> None
```

Remove drawing tools from the map.  Also cleans up all draw event listeners.

### `get_drawn_features()`

```python
await widget.get_drawn_features(session) -> None
```

Request the current set of drawn features.  Result arrives as `input[widget.drawn_features_input_id]()`.

### `delete_drawn_features()`

```python
await widget.delete_drawn_features(
    session,
    feature_ids: list[str] | None = None,
) -> None
```

Delete drawn features.  If `feature_ids` is `None`, deletes all drawn geometry.

```python
# Delete specific features
await widget.delete_drawn_features(session, ["feature-abc", "feature-xyz"])

# Delete all
await widget.delete_drawn_features(session)
```

### `add_geodataframe()`

```python
await widget.add_geodataframe(
    session,
    source_id: str,
    gdf,
    *,
    layer_type: str = "fill",
    paint: dict | None = None,
    layout: dict | None = None,
    before_id: str | None = None,
    popup_template: str | None = None,
) -> None
```

Add a GeoPandas GeoDataFrame as a native MapLibre source + layer.  Convenience method that serialises the GeoDataFrame, adds source + layer, and optionally attaches a popup.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `source_id` | `str` | *(required)* | Unique source identifier. The layer is created with id `"{source_id}-layer"`. |
| `gdf` | `GeoDataFrame` | *(required)* | A `geopandas.GeoDataFrame`. |
| `layer_type` | `str` | `"fill"` | MapLibre layer type. |
| `paint` | `dict \| None` | `None` | Paint properties.  Defaults by type: `"fill"` → `{"fill-color": "#088", "fill-opacity": 0.5}`, `"line"` → `{"line-color": "#333", "line-width": 2}`, `"circle"` → `{"circle-radius": 5, "circle-color": "#088"}`. |
| `layout` | `dict \| None` | `None` | Layout properties. |
| `before_id` | `str \| None` | `None` | Insert layer before this ID. |
| `popup_template` | `str \| None` | `None` | HTML template for click popup (e.g. `"<b>{name}</b>"`). |

```python
import geopandas as gpd
gdf = gpd.read_file("regions.geojson")
await widget.add_geodataframe(session, "regions", gdf,
                              layer_type="fill",
                              popup_template="<b>{region_name}</b>")
```

### `update_geodataframe()`

```python
await widget.update_geodataframe(
    session,
    source_id: str,
    gdf,
) -> None
```

Update the data of an existing GeoDataFrame source in-place.

```python
updated_gdf = gdf[gdf["population"] > 50000]
await widget.update_geodataframe(session, "regions", updated_gdf)
```

### `set_feature_state()`

```python
await widget.set_feature_state(
    session,
    source_id: str,
    feature_id: str | int,
    state: dict,
    *,
    source_layer: str | None = None,
) -> None
```

Set the state of a feature in a source.  Useful for interactive data-driven styling without redrawing.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `source_id` | `str` | *(required)* | Source containing the feature. |
| `feature_id` | `str \| int` | *(required)* | Feature's unique identifier. |
| `state` | `dict` | *(required)* | State properties, e.g. `{"hover": True, "selected": True}`. |
| `source_layer` | `str \| None` | `None` | Required for vector tile sources. |

```python
await widget.set_feature_state(session, "cities", "feature-123",
                               {"hover": True})
```

### `remove_feature_state()`

```python
await widget.remove_feature_state(
    session,
    source_id: str,
    feature_id: str | int | None = None,
    *,
    key: str | None = None,
    source_layer: str | None = None,
) -> None
```

Remove feature state.  If `feature_id` is `None`, clears all features.  If `key` is `None`, removes all state keys.

```python
# Remove hover state from one feature
await widget.remove_feature_state(session, "cities", "feature-123",
                                  key="hover")

# Clear all state from all features
await widget.remove_feature_state(session, "cities")
```

### `export_image()`

```python
await widget.export_image(
    session,
    *,
    format: str = "png",
    quality: float = 0.92,
    request_id: str = "default",
) -> None
```

Request a screenshot of the map.  The base64-encoded image arrives as `input[widget.export_result_input_id]()`.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `format` | `str` | `"png"` | Image format: `"png"`, `"jpeg"`, or `"webp"`. |
| `quality` | `float` | `0.92` | JPEG/WebP quality (0.0–1.0).  Ignored for PNG. |
| `request_id` | `str` | `"default"` | Identifier for matching results. |

```python
await widget.export_image(session, format="jpeg", quality=0.85,
                          request_id="snapshot-1")
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

## Basemap & Control Constants

### Basemap Styles

Pre-defined MapLibre style URLs:

| Constant | URL | Description |
|---|---|---|
| `CARTO_POSITRON` | `basemaps.cartocdn.com/.../positron-nolabels-gl-style/style.json` | Light, minimal basemap |
| `CARTO_DARK` | `basemaps.cartocdn.com/.../dark-matter-nolabels-gl-style/style.json` | Dark basemap |
| `CARTO_VOYAGER` | `basemaps.cartocdn.com/.../voyager-nolabels-gl-style/style.json` | Colourful general-purpose |
| `OSM_LIBERTY` | `tiles.openfreemap.org/styles/liberty` | OpenStreetMap Liberty style |

Pass any MapLibre-compatible style URL to `MapWidget(style=...)`.

### Control Constants

**`CONTROL_TYPES`** — Valid control type strings for `add_control()` and the constructor's `controls` parameter:

`{"navigation", "scale", "fullscreen", "geolocate", "globe", "terrain", "attribution"}`

**`CONTROL_POSITIONS`** — Valid position strings for controls:

`{"top-left", "top-right", "bottom-left", "bottom-right"}`

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
