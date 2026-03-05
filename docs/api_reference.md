# shiny\_deckgl API Reference

> **Version 1.4.0** — A Shiny for Python bridge to deck.gl (v9.2.10) and MapLibre GL JS (v5.3.1).

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
  - [add\_image()](#add_image)
  - [remove\_image()](#remove_image)
  - [has\_image()](#has_image)
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
- [Control Helpers (v0.6)](#control-helpers-v06)
  - [set\_controls()](#set_controls)
  - [geolocate\_control()](#geolocate_control)
  - [globe\_control()](#globe_control)
  - [terrain\_control()](#terrain_control)
  - [legend\_control()](#legend_control)
  - [opacity\_control()](#opacity_control)
  - [deck\_legend\_control()](#deck_legend_control)
- [Layer Helpers (v0.7)](#layer-helpers-v07)
  - [layer()](#layer)
  - [scatterplot\_layer()](#scatterplot_layer)
  - [geojson\_layer()](#geojson_layer)
  - [tile\_layer()](#tile_layer)
  - [bitmap\_layer()](#bitmap_layer)
  - [arc\_layer()](#arc_layer)
  - [icon\_layer()](#icon_layer)
  - [path\_layer()](#path_layer)
  - [line\_layer()](#line_layer)
  - [text\_layer()](#text_layer)
  - [column\_layer()](#column_layer)
  - [polygon\_layer()](#polygon_layer)
  - [heatmap\_layer()](#heatmap_layer)
  - [hexagon\_layer()](#hexagon_layer)
  - [h3\_hexagon\_layer()](#h3_hexagon_layer)
- [Widgets (v0.8)](#widgets-v08)
  - [set\_widgets()](#set_widgets)
  - [Widget Helper Functions](#widget-helper-functions)
- [Camera Transitions (v0.8)](#camera-transitions-v08)
  - [fly\_to()](#fly_to)
  - [ease\_to()](#ease_to)
- [Transition Helper (v0.8)](#transition-helper-v08)
- [Layer Helpers (v0.9)](#layer-helpers-v09)
  - [trips\_layer()](#trips_layer)
  - [great\_circle\_layer()](#great_circle_layer)
  - [contour\_layer()](#contour_layer)
  - [grid\_layer()](#grid_layer)
  - [screen\_grid\_layer()](#screen_grid_layer)
  - [mvt\_layer()](#mvt_layer)
  - [wms\_layer() (deck.gl)](#wms_layer-deckgl)
- [Interleaved Rendering (v0.9)](#interleaved-rendering-v09)
- [TripsLayer Animation (v0.9)](#tripslayer-animation-v09)
- [Extension Helpers (v1.0)](#extension-helpers-v10)
  - [brushing\_extension()](#brushing_extension)
  - [collision\_filter\_extension()](#collision_filter_extension)
  - [data\_filter\_extension()](#data_filter_extension)
  - [mask\_extension()](#mask_extension)
  - [clip\_extension()](#clip_extension)
  - [terrain\_extension()](#terrain_extension)
  - [fill\_style\_extension()](#fill_style_extension)
  - [path\_style\_extension()](#path_style_extension)
  - [fp64\_extension()](#fp64_extension)
- [Cluster Layers (v1.0)](#cluster-layers-v10)
  - [add\_cluster\_layer()](#add_cluster_layer)
  - [remove\_cluster\_layer()](#remove_cluster_layer)
- [Cooperative Gestures (v1.0)](#cooperative-gestures-v10)
  - [set\_cooperative\_gestures()](#set_cooperative_gestures)
- [Controller (v1.0)](#controller-v10)
  - [set\_controller()](#set_controller)
- [IBM Helpers (v1.1)](#ibm-helpers-v11)
  - [format\_trips()](#format_trips)
  - [trips\_animation\_ui()](#trips_animation_ui)
  - [trips\_animation\_server()](#trips_animation_server)
  - [Extension Type Alias](#extension-type-alias)
- [Effects Helpers (v1.2)](#effects-helpers-v12)
  - [ambient\_light()](#ambient_light)
  - [point\_light()](#point_light)
  - [directional\_light()](#directional_light)
  - [sun\_light()](#sun_light)
  - [lighting\_effect()](#lighting_effect)
  - [post\_process\_effect()](#post_process_effect)
- [Layer Helpers (v1.2)](#layer-helpers-v12)
  - [point\_cloud\_layer()](#point_cloud_layer)
  - [simple\_mesh\_layer()](#simple_mesh_layer)
  - [terrain\_layer()](#terrain_layer)
- [Mesh Geometry Helpers (v1.3)](#mesh-geometry-helpers-v13)
  - [custom\_geometry()](#custom_geometry)
  - [COORDINATE\_SYSTEM](#coordinate_system)
- [SHYFEM Parsers (v1.3)](#shyfem-parsers-v13)
  - [parse\_shyfem\_grd()](#parse_shyfem_grd)
  - [parse\_shyfem\_mesh()](#parse_shyfem_mesh)
- [Demo Data Factories (v1.3)](#demo-data-factories-v13)
- [Partial Updates (v1.4)](#partial-updates-v14)
  - [partial\_update()](#partial_update)
  - [patch\_layer()](#patch_layer)
- [IBM Visual Assets (v1.1)](#ibm-visual-assets-v11)
- [Basemap & Control Constants](#basemap--control-constants)
- [Color Utilities](#color-utilities)
  - [Palette Constants](#palette-constants)
  - [color\_range()](#color_range)
  - [color\_bins()](#color_bins)
  - [color\_quantiles()](#color_quantiles)
  - [depth\_color()](#depth_color)
- [Binary Data Transport](#binary-data-transport)
  - [encode\_binary\_attribute()](#encode_binary_attribute)
- [View Helpers](#view-helpers)
  - [map\_view()](#map_view)
  - [orthographic\_view()](#orthographic_view)
  - [first\_person\_view()](#first_person_view)
  - [globe\_view()](#globe_view)
  - [orbit\_view()](#orbit_view)
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
    picking_radius: int = 0,
    use_device_pixels: bool | int = True,
    animate: bool = False,
    parameters: dict | None = None,
    controller: bool | dict = True,
    interleaved: bool = False,
    cooperative_gestures: bool = False,
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
| `picking_radius` | `int` | `0` | Extra pixels around the pointer for pick detection. |
| `use_device_pixels` | `bool \| int` | `True` | Whether to use retina resolution; set `False` for performance. |
| `animate` | `bool` | `False` | Enable continuous rendering (needed for TripsLayer animation). |
| `parameters` | `dict \| None` | `None` | WebGL parameters passed to the deck.gl `Deck` instance. |
| `controller` | `bool \| dict` | `True` | Map controller config. `True` for default, `False` to disable, dict for fine-tuning. |
| `interleaved` | `bool` | `False` | Enable deck.gl interleaved rendering (layers interspersed with basemap labels). |
| `cooperative_gestures` | `bool` | `False` | Require Ctrl+scroll to zoom and two-finger drag on touch. |

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
| `has_image_input_id` | `"{id}_has_image"` | `has_image()` check completes | `{imageId, exists}` |

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

### `add_image()`

```python
await widget.add_image(
    session,
    image_id: str,
    url: str,
    *,
    pixel_ratio: float = 1,
    sdf: bool = False,
) -> None
```

Load an image from a URL (or data-URI) into the map style so it can be
referenced by a symbol layer's `icon-image` layout property.  If an image
with the same *image_id* already exists it is replaced.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `session` | `Session` | *(required)* | The active Shiny session. |
| `image_id` | `str` | *(required)* | Unique name for the image. |
| `url` | `str` | *(required)* | HTTP(S) URL or `data:` URI of the image. |
| `pixel_ratio` | `float` | `1` | Device pixel ratio for retina displays. |
| `sdf` | `bool` | `False` | Treat the image as a signed-distance-field icon (recolourable with `icon-color`). |

```python
await widget.add_image(session, "buoy", "https://example.com/buoy.png", pixel_ratio=2)
await widget.add_maplibre_layer(session, {
    "id": "stations",
    "type": "symbol",
    "source": "station-src",
    "layout": {"icon-image": "buoy", "icon-size": 0.5},
})
```

### `remove_image()`

```python
await widget.remove_image(session, image_id: str) -> None
```

Remove a previously loaded image from the map style.

### `has_image()`

```python
await widget.has_image(session, image_id: str) -> None
```

Check whether *image_id* is loaded.  The result arrives asynchronously as
`input.<map_id>_has_image` containing `{"imageId": str, "exists": bool}`.

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
await widget.set_style(
    session,
    style: str,
    *,
    diff: bool = False,
) -> None
```

Change the entire basemap style dynamically.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `style` | `str` | *(required)* | URL of the new map style JSON. |
| `diff` | `bool` | `False` | When `True`, MapLibre computes a diff and only applies changes, preserving existing sources/layers. |

> **Warning:** With `diff=False` (default), this destroys all native sources and layers.  Re-add them after the style loads.  Use `diff=True` to preserve them.

```python
await widget.set_style(session, CARTO_DARK)

# Preserve existing sources/layers:
await widget.set_style(session, CARTO_VOYAGER, diff=True)
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

## Control Helpers (v0.6)

### `set_controls()`

```python
await widget.set_controls(
    session: Session,
    controls: list[dict],
) -> None
```

Replace **all** MapLibre controls on the map at once. Existing controls are removed before the new set is applied. Each control dict has `type` (one of `CONTROL_TYPES`), `position` (default `"top-right"`), and `options` (default `{}`).

Use the `*_control()` helper functions to build control specs, or construct dicts manually.

```python
await widget.set_controls(session, [
    {"type": "navigation", "position": "top-right", "options": {}},
    geolocate_control(position="top-right", trackUserLocation=True),
    globe_control(position="top-right"),
    legend_control(targets={"water": "Water"}, position="bottom-left"),
    deck_legend_control(
        entries=[{"layer_id": "ports", "label": "Ports", "color": [0, 200, 100]}],
        position="bottom-right", title="Deck.gl Layers",
    ),
])
```

### `geolocate_control()`

```python
geolocate_control(position: str = "top-right", **options) -> dict
```

Create a MapLibre `GeolocateControl` spec. Adds a button that uses the browser Geolocation API to locate the user.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `position` | `str` | `"top-right"` | Control position. |
| `**options` | | | Passed to `GeolocateControl`: `trackUserLocation`, `showAccuracyCircle`, `positionOptions`, etc. |

```python
geolocate_control(position="top-right", trackUserLocation=True)
```

### `globe_control()`

```python
globe_control(position: str = "top-right", **options) -> dict
```

Create a MapLibre `GlobeControl` spec (flat ↔ globe toggle). Requires MapLibre GL JS ≥ 5.0.

```python
globe_control(position="top-right")
```

### `terrain_control()`

```python
terrain_control(position: str = "top-right", **options) -> dict
```

Create a MapLibre `TerrainControl` spec (3D terrain toggle). Requires MapLibre GL JS ≥ 5.0 and a terrain source in the style.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `position` | `str` | `"top-right"` | Control position. |
| `**options` | | | Passed to `TerrainControl`: `source` (terrain source id), `exaggeration` (height multiplier). |

```python
terrain_control(position="top-right", source="terrain-dem", exaggeration=1.5)
```

### `legend_control()`

```python
legend_control(
    targets: dict[str, str] | None = None,
    position: str = "bottom-left",
    *,
    show_default: bool = False,
    show_checkbox: bool = True,
    only_rendered: bool = True,
    reverse_order: bool = False,
    title: str | None = None,
) -> dict
```

Create a legend control for **native MapLibre style layers** (powered by `@watergis/maplibre-gl-legend`). Displays a collapsible legend panel generated from the MapLibre style. Layer visibility can be toggled with checkboxes.

> **Note:** This control only sees native MapLibre layers added via `add_maplibre_layer()`. For deck.gl overlay layers, use [`deck_legend_control()`](#deck_legend_control) instead.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `targets` | `dict \| None` | `None` | Map of layer id → display label. `None` shows all layers. |
| `position` | `str` | `"bottom-left"` | Control position. |
| `show_default` | `bool` | `False` | Whether the panel starts expanded. |
| `show_checkbox` | `bool` | `True` | Show visibility toggle checkboxes. |
| `only_rendered` | `bool` | `True` | Only show currently rendered layers. |
| `reverse_order` | `bool` | `False` | Reverse layer order in the legend. |
| `title` | `str \| None` | `None` | Panel title text. |

```python
legend_control(
    targets={"mpa-fill": "Marine Protected Areas", "ports-circle": "Ports"},
    position="bottom-left",
    show_default=True,
    only_rendered=False,
)
```

### `opacity_control()`

```python
opacity_control(
    position: str = "top-left",
    *,
    base_layers: dict[str, str] | None = None,
    over_layers: dict[str, str] | None = None,
    opacity_control_enabled: bool = True,
) -> dict
```

Create an opacity / layer-switcher control (powered by `maplibre-gl-opacity`). Displays radio buttons for base layers and checkboxes with opacity sliders for overlay layers.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `position` | `str` | `"top-left"` | Control position. |
| `base_layers` | `dict \| None` | `None` | Layer id → label for mutually exclusive base layers (radio buttons). |
| `over_layers` | `dict \| None` | `None` | Layer id → label for overlay layers (checkboxes + opacity sliders). |
| `opacity_control_enabled` | `bool` | `True` | Show the opacity slider for overlays. |

```python
opacity_control(
    over_layers={"mpa-fill": "Marine Protected Areas", "ports-circle": "Ports"},
)
```

### `deck_legend_control()`

```python
deck_legend_control(
    entries: list[dict],
    position: str = "bottom-right",
    *,
    show_checkbox: bool = True,
    collapsed: bool = False,
    title: str | None = None,
) -> dict
```

Create a legend control for **deck.gl overlay layers**. Unlike `legend_control()` (which wraps the `@watergis/maplibre-gl-legend` plugin and can only see native MapLibre style layers), this control displays user-defined entries with colour swatches and optional visibility checkboxes that toggle deck.gl layers on and off.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `entries` | `list[dict]` | *(required)* | Legend entries (see table below). |
| `position` | `str` | `"bottom-right"` | Control position. |
| `show_checkbox` | `bool` | `True` | Show checkboxes to toggle deck.gl layer visibility. |
| `collapsed` | `bool` | `False` | Start the panel in collapsed state. |
| `title` | `str \| None` | `None` | Header text. When set, the panel is collapsible. |

**Entry dict keys:**

| Key | Type | Description |
| --- | --- | --- |
| `layer_id` | `str` | deck.gl layer id (used by the visibility checkbox). |
| `label` | `str` | Human-readable display label. |
| `color` | `list \| str` | `[r, g, b]`, `[r, g, b, a]`, or CSS colour string. |
| `shape` | `str` | Swatch shape: `"circle"` (default), `"rect"`, `"line"`, `"arc"`, `"gradient"`. |
| `color2` | `list \| str` | Second colour for `"arc"` shape (gradient end). |
| `colors` | `list` | List of colours for `"gradient"` shape (e.g. HeatmapLayer `colorRange`). |

**Swatch shapes and typical use:**

| Shape | CSS Class | Best For |
| --- | --- | --- |
| `circle` | 12 × 12 px circle | `ScatterplotLayer` |
| `rect` | 16 × 12 px rectangle | `GeoJsonLayer` fill, `ColumnLayer` |
| `line` | 20 × 3 px bar | `PathLayer`, `LineLayer` |
| `arc` | 24 × 4 px gradient bar | `ArcLayer` (source → target colour) |
| `gradient` | 40 × 10 px multi-stop gradient | `HeatmapLayer`, `HexagonLayer` |

```python
deck_legend_control(
    entries=[
        {"layer_id": "ports", "label": "Baltic Ports",
         "color": [65, 182, 196], "shape": "circle"},
        {"layer_id": "mpa-zones", "label": "Marine Protected Areas",
         "color": [0, 128, 0, 100], "shape": "rect"},
        {"layer_id": "port-arcs", "label": "Shipping Routes",
         "color": [255, 140, 0], "color2": [200, 0, 80], "shape": "arc"},
        {"layer_id": "observation-heat", "label": "Observation Heatmap",
         "colors": [[0, 25, 0], [0, 209, 0], [255, 255, 0], [255, 0, 0]],
         "shape": "gradient"},
        {"layer_id": "route-paths", "label": "Route Paths",
         "color": [100, 100, 200], "shape": "line"},
    ],
    position="bottom-right",
    title="Deck.gl Layers",
    show_checkbox=True,
)
```

---

## Layer Helpers (v0.7)

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

### `arc_layer()`

```python
arc_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create an `ArcLayer` for drawing arcs between two points.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts, remote URL, or DataFrame. |
| `getSourcePosition` | `"@@d.sourcePosition"` | Source coordinate accessor. |
| `getTargetPosition` | `"@@d.targetPosition"` | Target coordinate accessor. |
| `getSourceColor` | `[0, 128, 200]` | Source end colour. |
| `getTargetColor` | `[200, 0, 80]` | Target end colour. |
| `getWidth` | `2` | Arc width in pixels. |

```python
arc_layer("routes", data, getSourceColor=[0, 200, 0], getWidth=3)
```

### `icon_layer()`

```python
icon_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create an `IconLayer` for rendering icons at locations.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of `[lon, lat]` points / dicts / URL / DataFrame. |
| `getPosition` | `"@@d"` | Position accessor. |
| `getSize` | `24` | Icon size. |
| `sizeScale` | `1` | Global size multiplier. |

```python
icon_layer("markers", data, iconAtlas="atlas.png",
           iconMapping={"marker": {"x": 0, "y": 0, "width": 128, "height": 128}},
           getIcon="marker")
```

### `path_layer()`

```python
path_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `PathLayer` for rendering polylines.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts with `path` key / URL / DataFrame. |
| `getPath` | `"@@d.path"` | Path accessor. |
| `getColor` | `[0, 128, 255]` | Line colour. |
| `getWidth` | `3` | Line width. |
| `widthMinPixels` | `1` | Minimum width in pixels. |

```python
path_layer("trails", data, getColor=[255, 0, 0], getWidth=5)
```

### `line_layer()`

```python
line_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `LineLayer` for straight lines between two points. Unlike `ArcLayer`, lines are drawn as straight segments (no curve).

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts with `sourcePosition`/`targetPosition`. |
| `getSourcePosition` | `"@@d.sourcePosition"` | Source coordinate accessor. |
| `getTargetPosition` | `"@@d.targetPosition"` | Target coordinate accessor. |
| `getColor` | `[0, 0, 0, 128]` | Line colour. |
| `getWidth` | `1` | Line width. |

```python
line_layer("connections", data, getColor=[80, 80, 200])
```

### `text_layer()`

```python
text_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `TextLayer` for rendering text labels at locations.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts with `text` key / URL / DataFrame. |
| `getPosition` | `"@@d"` | Position accessor. |
| `getText` | `"@@d.text"` | Text content accessor. |
| `getSize` | `16` | Font size. |
| `getColor` | `[0, 0, 0, 255]` | Text colour. |
| `getTextAnchor` | `"middle"` | Horizontal alignment. |
| `getAlignmentBaseline` | `"center"` | Vertical alignment. |

```python
text_layer("labels", data, getSize=12, getColor=[255, 255, 255])
```

### `column_layer()`

```python
column_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `ColumnLayer` for 3D extruded columns.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts / URL / DataFrame. |
| `getPosition` | `"@@d"` | Position accessor. |
| `getElevation` | `"@@d.elevation"` | Column height accessor. |
| `getFillColor` | `[255, 140, 0]` | Fill colour. |
| `radius` | `100` | Column radius in meters. |
| `extruded` | `True` | Enable 3D extrusion. |

```python
column_layer("towers", data, radius=500, getFillColor=[65, 182, 196])
```

### `polygon_layer()`

```python
polygon_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `PolygonLayer` for rendering filled polygons.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts with `polygon` key. |
| `getPolygon` | `"@@d.polygon"` | Polygon accessor. |
| `getFillColor` | `[0, 128, 255, 80]` | Fill colour (RGBA). |
| `getLineColor` | `[0, 0, 0, 200]` | Outline colour. |
| `getLineWidth` | `1` | Outline width. |
| `extruded` | `False` | Enable 3D extrusion. |

```python
polygon_layer("zones", data, getFillColor=[0, 200, 0, 60], extruded=True,
              getElevation="@@d.height")
```

### `heatmap_layer()`

```python
heatmap_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `HeatmapLayer` for density visualisation.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of `[lon, lat]` points / dicts / URL / DataFrame. |
| `getPosition` | `"@@d"` | Position accessor. |
| `getWeight` | `1` | Weight accessor or constant. |
| `radiusPixels` | `30` | Kernel radius in pixels. |
| `intensity` | `1` | Intensity multiplier. |
| `threshold` | `0.05` | Minimum density threshold. |

```python
heatmap_layer("density", data, radiusPixels=50, intensity=2)
```

### `hexagon_layer()`

```python
hexagon_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create a `HexagonLayer` for hexagonal binning. Points are aggregated into hexagonal bins.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of `[lon, lat]` points / dicts. |
| `getPosition` | `"@@d"` | Position accessor. |
| `radius` | `1000` | Hex radius in meters. |
| `elevationScale` | `4` | Elevation multiplier. |
| `extruded` | `True` | Enable 3D extrusion. |

```python
hexagon_layer("hex-bins", data, radius=500, extruded=True,
              elevationScale=10)
```

### `h3_hexagon_layer()`

```python
h3_hexagon_layer(id: str, data: list | dict, **kwargs) -> dict
```

Create an `H3HexagonLayer` for H3 index-based hexagons. Renders pre-computed H3 spatial indices.

| Parameter | Default | Description |
| --- | --- | --- |
| `id` | *(required)* | Unique layer identifier. |
| `data` | *(required)* | Array of dicts with `hex` (H3 index) and `color`. |
| `getHexagon` | `"@@d.hex"` | H3 index accessor. |
| `getFillColor` | `"@@d.color"` | Fill colour accessor. |
| `extruded` | `False` | Enable 3D extrusion. |

```python
h3_hexagon_layer("h3-grid", data, extruded=True,
                 getElevation="@@d.count", elevationScale=100)
```

---

## IBM Helpers (v1.1)

Individual-Based Model helpers for animal movement visualisation.

Importable from the top-level package or directly from `shiny_deckgl.ibm`.

```python
from shiny_deckgl import format_trips, trips_animation_ui, trips_animation_server
# or
from shiny_deckgl.ibm import format_trips, trips_animation_ui, trips_animation_server
```

### `format_trips()`

```python
shiny_deckgl.ibm.format_trips(
    paths: list[list[list[float]]],
    *,
    loop_length: int = 600,
    timestamps: list[list[int | float]] | None = None,
    properties: list[dict] | None = None,
) -> list[dict]
```

Convert raw coordinate lists into the dict format `trips_layer()` expects.

| Parameter | Default | Description |
| --- | --- | --- |
| `paths` | *(required)* | List of trips, each a list of `[lon, lat]` or `[lon, lat, time]` pairs. |
| `loop_length` | `600` | Total animation loop duration for auto-generated timestamps. |
| `timestamps` | `None` | Explicit per-trip timestamp arrays (overrides `loop_length`). |
| `properties` | `None` | Per-trip metadata dicts merged into the output (e.g. `name`, `species`, `color`). |

**Returns** a list of dicts, each with `path` (`[lon, lat, time]` triplets), `timestamps`, and any merged properties.

```python
trips = format_trips(
    paths=[[[20.0, 57.0], [20.5, 57.2], [20.0, 57.0]]],
    loop_length=100,
    properties=[{"name": "Trip 1", "color": [255, 0, 0]}],
)
# trips[0]["path"][0] == [20.0, 57.0, 0]
```

### `trips_animation_ui()`

```python
shiny_deckgl.ibm.trips_animation_ui(
    id: str,
    *,
    speed_default: float = 8.0,
    speed_min: float = 0.5,
    speed_max: float = 100.0,
    speed_step: float = 0.5,
    trail_default: int = 180,
    trail_min: int = 20,
    trail_max: int = 400,
    trail_step: int = 10,
) -> TagList
```

Drop-in Shiny module UI fragment with Play / Pause / Reset buttons (in a 4-4-4 column layout) plus speed and trail-length sliders.

```python
ui.accordion_panel(
    "Animation Controls",
    trips_animation_ui("seal_anim"),
)
```

### `trips_animation_server()`

```python
shiny_deckgl.ibm.trips_animation_server(
    id: str,
    *,
    widget: MapWidget,
    session: Session,
) -> SimpleNamespace
```

Companion server logic. Wires the Play / Pause / Reset buttons to `widget.trips_control(session, action)` and returns a `SimpleNamespace` with `.speed()` and `.trail()` reactive accessors.

```python
anim = trips_animation_server("seal_anim", widget=seal_widget, session=session)

# inside reactive effects:
speed = anim.speed()
trail = anim.trail()
```

### Extension Type Alias

```python
from shiny_deckgl.extensions import Extension
# Extension = str | list[str | dict]
```

All 8 extension helpers (`brushing_extension`, `data_filter_extension`, etc.) now return `Extension` instead of the previous mixed `str` / `list` annotations. This provides consistent typing for the `extensions` parameter of `layer()`.

---

## Effects Helpers (v1.2)

Typed helpers for deck.gl lighting and post-processing effects.  These replace
the raw dict approach described in the [Lighting & Effects](#lighting--effects)
section with convenience functions.

```python
from shiny_deckgl import (
    lighting_effect, ambient_light, point_light,
    directional_light, sun_light, post_process_effect,
)

effects = [
    lighting_effect(
        ambient_light(intensity=0.8),
        point_light([20.0, 55.0, 80000], intensity=2.0),
        directional_light([-1, -3, -1], intensity=0.6),
    ),
    post_process_effect("brightnessContrast", brightness=0.1, contrast=0.2),
]

await widget.update(session, layers=[...], effects=effects)
```

### `ambient_light()`

```python
shiny_deckgl.ambient_light(
    color: list[int] | tuple[int, ...] = (255, 255, 255),
    intensity: float = 1.0,
) -> dict
```

Ambient light — illuminates all objects equally regardless of direction.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `color` | `list[int]` | `[255, 255, 255]` | RGB colour. |
| `intensity` | `float` | `1.0` | Brightness multiplier. |

### `point_light()`

```python
shiny_deckgl.point_light(
    position: list[float],
    color: list[int] | tuple[int, ...] = (255, 255, 255),
    intensity: float = 1.0,
    **kwargs,
) -> dict
```

Point light — emits from a single position in all directions.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `position` | `list[float]` | *(required)* | `[longitude, latitude, altitude_metres]`. |
| `color` | `list[int]` | `[255, 255, 255]` | RGB colour. |
| `intensity` | `float` | `1.0` | Brightness multiplier. |

### `directional_light()`

```python
shiny_deckgl.directional_light(
    direction: list[float] = (-1, -3, -1),
    color: list[int] | tuple[int, ...] = (255, 255, 255),
    intensity: float = 1.0,
    _shadow: bool = False,
    **kwargs,
) -> dict
```

Directional light — parallel rays from a distant source (like the sun).

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `direction` | `list[float]` | `[-1, -3, -1]` | `[x, y, z]` direction vector. |
| `color` | `list[int]` | `[255, 255, 255]` | RGB colour. |
| `intensity` | `float` | `1.0` | Brightness multiplier. |
| `_shadow` | `bool` | `False` | Enable experimental shadow rendering. |

### `sun_light()`

```python
shiny_deckgl.sun_light(
    timestamp: int | float,
    color: list[int] | tuple[int, ...] = (255, 255, 255),
    intensity: float = 1.0,
    _shadow: bool = False,
    **kwargs,
) -> dict
```

Sun light — directional light whose direction is computed from the sun's position at a given time.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `timestamp` | `int \| float` | *(required)* | Unix timestamp in milliseconds. |
| `color` | `list[int]` | `[255, 255, 255]` | RGB colour. |
| `intensity` | `float` | `1.0` | Brightness multiplier. |
| `_shadow` | `bool` | `False` | Enable experimental shadow rendering. |

### `lighting_effect()`

```python
shiny_deckgl.lighting_effect(
    ambient: dict | None = None,
    *lights: dict,
    **kwargs,
) -> dict
```

Combine an optional ambient light with any number of point/directional/sun lights into a single `LightingEffect` spec.

```python
lighting_effect(
    ambient_light(intensity=0.5),
    point_light([20, 55, 80000], intensity=2.0),
    directional_light([-1, -3, -1], intensity=0.8),
)
```

### `post_process_effect()`

```python
shiny_deckgl.post_process_effect(
    shader_module: str,
    **kwargs,
) -> dict
```

Screen-space pixel manipulation via a luma.gl shader module.

| Parameter | Type | Description |
| --- | --- | --- |
| `shader_module` | `str` | Shader name: `"brightnessContrast"`, `"hueSaturation"`, `"noise"`, `"sepia"`, `"vibrance"`, `"vignette"`, `"tiltShift"`, `"triangleBlur"`, `"zoomBlur"`, etc. |
| `**kwargs` | | Shader-specific parameters (e.g. `brightness=0.5`). |

```python
post_process_effect("brightnessContrast", brightness=0.1, contrast=0.3)
post_process_effect("vignette", radius=0.5, amount=0.5)
```

---

## Layer Helpers (v1.2)

New typed layer helpers for 3-D content and terrain.

### `point_cloud_layer()`

```python
shiny_deckgl.point_cloud_layer(id: str, data=None, **kwargs) -> dict
```

Render a cloud of 3-D points.  Each point is drawn as a circle in screen space.

| Property | Default | Description |
| --- | --- | --- |
| `pickable` | `True` | Enable hover/click. |
| `pointSize` | `2` | Point size. |
| `sizeUnits` | `"pixels"` | Size units. |
| `getPosition` | `"@@=position"` | Position accessor. |
| `getColor` | `[255, 140, 0]` | Point colour. |
| `getNormal` | `[0, 0, 1]` | Normal vector accessor. |

### `simple_mesh_layer()`

```python
shiny_deckgl.simple_mesh_layer(id: str, data=None, **kwargs) -> dict
```

Place a 3-D mesh (OBJ, PLY, or programmatic geometry) at each data point.

| Property | Default | Description |
| --- | --- | --- |
| `pickable` | `True` | Enable hover/click. |
| `getPosition` | `"@@=position"` | Anchor-point accessor. |
| `getColor` | `[140, 170, 200]` | Mesh colour. |
| `sizeScale` | `1` | Scale multiplier. |

Pass `mesh="https://example.com/model.obj"` for the 3-D model URL.

### `terrain_layer()`

```python
shiny_deckgl.terrain_layer(id: str, data=None, **kwargs) -> dict
```

Reconstruct mesh surfaces from height-map images (e.g. Mapzen Terrain Tiles).

| Property | Default | Description |
| --- | --- | --- |
| `meshMaxError` | `4.0` | Max LOD simplification error in metres. |

Key kwargs: `elevationData` (URL template), `texture` (satellite/map tile URL), `elevationDecoder` (RGB→elevation mapping), `bounds` (`[west, south, east, north]`).

---

## Mesh Geometry Helpers (v1.3)

Helpers for building inline 3-D mesh geometry for `SimpleMeshLayer`.

Importable from the top-level package or from `shiny_deckgl.layers`:

```python
from shiny_deckgl import custom_geometry, COORDINATE_SYSTEM
```

### `custom_geometry()`

```python
custom_geometry(
    mesh_data: dict,
    *,
    position: list[float] | None = None,
) -> dict
```

Build `simple_mesh_layer()` keyword arguments from parsed mesh geometry.

Converts the output of `parse_shyfem_mesh()` (or any dict with `positions`, `normals`, `colors`, `indices`, `center`) into the kwargs expected by `simple_mesh_layer()`.  The JS runtime detects the `"@@CustomGeometry"` mesh marker and constructs a `luma.Geometry` from the inline vertex arrays.

| Parameter | Default | Description |
| --- | --- | --- |
| `mesh_data` | *(required)* | Dict with keys `positions`, `normals`, `colors`, `indices`, `center` (as returned by `parse_shyfem_mesh()`). |
| `position` | `None` | Override the coordinate origin `[lon, lat]`.  Defaults to `mesh_data["center"]`. |

**Returns** a `dict` of kwargs: `data`, `mesh`, `_meshPositions`, `_meshNormals`, `_meshColors`, `_meshIndices`, `coordinateSystem`, `coordinateOrigin`, `sizeScale`, `getPosition`, `getColor`.

```python
from shiny_deckgl.parsers import parse_shyfem_mesh
from shiny_deckgl import simple_mesh_layer, custom_geometry

mesh = parse_shyfem_mesh("mesh.grd")
lyr = simple_mesh_layer("my-mesh", **custom_geometry(mesh), pickable=True)
```

### `COORDINATE_SYSTEM`

```python
class COORDINATE_SYSTEM
```

deck.gl coordinate system constants.  Use with the `coordinateSystem` property on any layer.

| Attribute | Value | Description |
| --- | --- | --- |
| `DEFAULT` | `-1` | Auto-detect based on data. |
| `LNGLAT` | `1` | Positions as `[longitude, latitude]` (default for most layers). |
| `METER_OFFSETS` | `2` | Positions in **metres** relative to a `coordinateOrigin`. |
| `LNGLAT_OFFSETS` | `3` | Positions as `[longitude_offset, latitude_offset]`. |
| `CARTESIAN` | `0` | Non-geographic pixel/unit coordinates. |

```python
simple_mesh_layer("mesh", data,
                  coordinateSystem=COORDINATE_SYSTEM.METER_OFFSETS,
                  coordinateOrigin=[21.07, 55.31])
```

---

## SHYFEM Parsers (v1.3)

Finite-element mesh parsers for SHYFEM `.grd` grid files.

Importable from the top-level package or from `shiny_deckgl.parsers`:

```python
from shiny_deckgl import parse_shyfem_grd, parse_shyfem_mesh
# or
from shiny_deckgl.parsers import parse_shyfem_grd, parse_shyfem_mesh
```

> **Note:** If node X values exceed 100 000, coordinates are assumed to be in UTM Zone 33N (EPSG:32633) and `pyproj` is used for WGS84 conversion.  Install with: `micromamba install -n shiny pyproj`.

### `parse_shyfem_grd()`

```python
parse_shyfem_grd(path: str | Path) -> list[dict]
```

Parse a SHYFEM `.grd` file and return **PolygonLayer-ready** data.

Each element (triangle or quad) is converted to a closed polygon with a depth-mapped blue colour ramp.

| Parameter | Description |
| --- | --- |
| `path` | Path to the `.grd` file. |

**Returns** a list of dicts, each with keys:

| Key | Type | Description |
| --- | --- | --- |
| `polygon` | `list[list[float]]` | Closed polygon coordinates `[[lon, lat], ...]`. |
| `depth` | `float` | Element depth (metres). |
| `element_id` | `int` | Mesh element identifier. |
| `color` | `list[int]` | `[R, G, B, A]` depth-mapped colour. |
| `layerType` | `str` | Always `"SHYFEM Mesh"`. |

```python
from shiny_deckgl import parse_shyfem_grd, layer
data = parse_shyfem_grd("curonian.grd")
lyr = layer("PolygonLayer", "mesh", data,
            getFillColor="@@=color",
            getPolygon="@@=polygon",
            pickable=True)
```

### `parse_shyfem_mesh()`

```python
parse_shyfem_mesh(path: str | Path, z_scale: float = 50.0) -> dict
```

Parse a SHYFEM `.grd` file into **SimpleMeshLayer** geometry arrays.

Vertex positions are in **metres** relative to the mesh centre, suitable for `COORDINATE_SYSTEM.METER_OFFSETS`.

| Parameter | Default | Description |
| --- | --- | --- |
| `path` | *(required)* | Path to the `.grd` file. |
| `z_scale` | `50.0` | Vertical exaggeration factor for depth. |

**Returns** a dict with keys:

| Key | Type | Description |
| --- | --- | --- |
| `positions` | `list[float]` | Flat vertex positions `[x, y, z, ...]`. |
| `normals` | `list[float]` | Flat per-vertex normals. |
| `colors` | `list[float]` | Flat per-vertex colours (0–1 range). |
| `indices` | `list[int]` | Flat triangle indices. |
| `center` | `list[float]` | `[lon, lat]` mesh centre in WGS84. |
| `n_vertices` | `int` | Total vertex count. |
| `n_triangles` | `int` | Total triangle count. |
| `depth_range` | `list[float]` | `[min_depth, max_depth]`. |

```python
from shiny_deckgl import parse_shyfem_mesh, simple_mesh_layer, custom_geometry
mesh = parse_shyfem_mesh("curonian.grd", z_scale=100)
lyr = simple_mesh_layer("fem", **custom_geometry(mesh))
```

---

## Demo Data Factories (v1.3)

Pre-built data generators for the demo app and quick prototyping.

Importable from the top-level package:

```python
from shiny_deckgl import (
    SHYFEM_VIEW,
    make_h3_data, make_point_cloud_data,
    make_shyfem_polygon_data, make_shyfem_mesh_data,
)
```

### `SHYFEM_VIEW`

```python
SHYFEM_VIEW: dict
```

Default view state centred on the Curonian Lagoon (Lithuania):

```python
{"longitude": 21.07, "latitude": 55.31, "zoom": 9, "pitch": 0, "bearing": 0}
```

### `make_h3_data()`

```python
make_h3_data() -> list[dict]
```

Generate H3 hexagon demo data — 7 resolution-3 cells in the central Baltic.  Each dict has keys `hex`, `count`, `color`, `name`, `layerType`.

### `make_point_cloud_data()`

```python
make_point_cloud_data() -> list[dict]
```

Generate synthetic 3-D point cloud around Baltic ports.  Each dict has keys `position` (`[lon, lat, z]`), `color`, `name`, `layerType`.

### `make_shyfem_polygon_data()`

```python
make_shyfem_polygon_data(grd_path: str | None = None) -> list[dict]
```

Load a SHYFEM `.grd` as PolygonLayer data.  Falls back to simple bounding-box polygons around Baltic ports when `grd_path` is `None` or the file doesn't exist.

| Parameter | Default | Description |
| --- | --- | --- |
| `grd_path` | `None` | Path to the `.grd` file. |

### `make_shyfem_mesh_data()`

```python
make_shyfem_mesh_data(grd_path: str | None = None, z_scale: float = 50.0) -> dict | None
```

Load a SHYFEM `.grd` as SimpleMeshLayer geometry arrays.  Returns `None` when `grd_path` is `None` or the file doesn't exist.

| Parameter | Default | Description |
| --- | --- | --- |
| `grd_path` | `None` | Path to the `.grd` file. |
| `z_scale` | `50.0` | Vertical exaggeration factor. |

---

## Partial Updates (v1.4)

Methods for efficiently patching layer properties without resending the entire
layer stack.

### `partial_update()`

```python
await widget.partial_update(
    session,
    layers: list[dict],
) -> None
```

Push **sparse layer patches** — only changed properties are sent.  Each dict
in `layers` must contain an `"id"` key matching an existing layer; the
remaining keys are shallow-merged into that layer's current props on the
client.

DataFrames / GeoDataFrames in `data` fields are auto-serialised.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `session` | `Session` | *(required)* | The active Shiny session. |
| `layers` | `list[dict]` | *(required)* | Sparse dicts with `id` + changed props. |

> **Note:** This method patches **layer** properties only.  Deck-level props
> (`effects`, `views`, `widgets`, `picking_radius`, etc.) are not affected —
> use `update()` for those.

**Example:**

```python
# Change only the opacity and radius of an existing layer
await map_widget.partial_update(session, [
    {"id": "scatter-ports", "opacity": 0.5, "radiusMinPixels": 12},
])
```

### `patch_layer()`

```python
await widget.patch_layer(
    session,
    layer_id: str,
    **props: Any,
) -> None
```

Convenience wrapper around `partial_update()` for the common case of tweaking
**one layer** at a time.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `session` | `Session` | *(required)* | The active Shiny session. |
| `layer_id` | `str` | *(required)* | ID of the layer to patch. |
| `**props` | `Any` | — | Layer properties to update. |

**Example:**

```python
await map_widget.patch_layer(session, "scatter-ports", opacity=0.5)
```

---

## IBM Visual Assets (v1.1)

Colour palette, sprite-sheet atlas, and icon mapping for individual-based model (IBM) visualisations.

Importable from the top-level package or from `shiny_deckgl.ibm`:

```python
from shiny_deckgl import SPECIES_COLORS, ICON_ATLAS, ICON_MAPPING
```

### `SPECIES_COLORS`

```python
SPECIES_COLORS: dict[str, list[int]]
```

RGBA colours per species for consistent rendering across layers.

| Key | Colour | RGBA |
| --- | --- | --- |
| `"Grey seal"` | Slate grey | `[100, 100, 100, 220]` |
| `"Ringed seal"` | Icy blue | `[70, 140, 220, 220]` |
| `"Harbour seal"` | Sandy brown | `[180, 140, 80, 220]` |

### `ICON_ATLAS`

```python
ICON_ATLAS: str
```

Base64-encoded data-URI of a 192×64 SVG sprite sheet containing three seal silhouettes (Grey, Ringed, Harbour).  Pass as `iconAtlas` to `icon_layer()` or the `_tripsHeadIcons` option.

### `ICON_MAPPING`

```python
ICON_MAPPING: dict[str, dict]
```

deck.gl icon-mapping dict keyed by species name.  Each value specifies `x`, `y`, `width`, `height`, and `anchorY` within the `ICON_ATLAS` sprite sheet.

| Key | x | y | width | height | anchorY |
| --- | --- | --- | --- | --- | --- |
| `"Grey seal"` | 0 | 0 | 64 | 64 | 32 |
| `"Ringed seal"` | 64 | 0 | 64 | 64 | 32 |
| `"Harbour seal"` | 128 | 0 | 64 | 64 | 32 |

```python
from shiny_deckgl import icon_layer, ICON_ATLAS, ICON_MAPPING
lyr = icon_layer("seals", data,
                 iconAtlas=ICON_ATLAS,
                 iconMapping=ICON_MAPPING,
                 getIcon="@@=species")
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

**`CONTROL_TYPES`** — Valid control type strings for `add_control()`, `set_controls()`, and the constructor's `controls` parameter:

`{"navigation", "scale", "fullscreen", "geolocate", "globe", "terrain", "attribution", "legend", "opacity", "deck_legend"}`

**`CONTROL_POSITIONS`** — Valid position strings for controls:

`{"top-left", "top-right", "bottom-left", "bottom-right"}`

---

## Widgets (v0.8)

deck.gl ships with its own widget system, independent of MapLibre controls. Widgets are rendered in the WebGL overlay and provide UI affordances such as zoom buttons, compass, fullscreen toggle, etc.

### `set_widgets()`

```python
await widget.set_widgets(
    session: Session,
    widgets: list[dict],
) -> None
```

Replace **all** deck.gl widgets at once (without resending layers). Each dict in `widgets` is built with a `*_widget()` helper.

```python
await widget.set_widgets(session, [
    zoom_widget(placement="top-right"),
    compass_widget(placement="top-right"),
    fullscreen_widget(),
    scale_widget(placement="bottom-left"),
])
```

### Widget Helper Functions

All helpers return a plain `dict` with a `"@@widgetClass"` key consumed by the JS client.

| Helper | Class | Default Placement | Description |
| --- | --- | --- | --- |
| `zoom_widget()` | `ZoomWidget` | `"top-right"` | Zoom-in / zoom-out buttons |
| `compass_widget()` | `CompassWidget` | `"top-right"` | Bearing indicator / reset |
| `fullscreen_widget()` | `FullscreenWidget` | `"top-right"` | Toggle fullscreen |
| `scale_widget()` | `ScaleWidget` | `"bottom-left"` | Distance scale bar |
| `gimbal_widget()` | `GimbalWidget` | `"top-right"` | 3D camera gimbal control |
| `reset_view_widget()` | `ResetViewWidget` | `"top-right"` | Reset camera to initial state |
| `screenshot_widget()` | `ScreenshotWidget` | `"top-right"` | Take a screenshot |
| `fps_widget()` | `FpsWidget` | `"top-left"` | Frames-per-second counter |
| `loading_widget()` | `LoadingWidget` | — | Spinner during layer loading |
| `timeline_widget()` | `TimelineWidget` | `"bottom-left"` | Time scrubber for animated layers |
| `geocoder_widget()` | `GeocoderWidget` | `"top-left"` | Address search |
| `theme_widget()` | `ThemeWidget` | — | Light/dark theme toggle |

**Experimental widgets** (deck.gl ≥ 9.2):

| Helper | Class | Default Placement | Description |
| --- | --- | --- | --- |
| `context_menu_widget()` | `ContextMenuWidget` | — | Right-click context menu |
| `info_widget()` | `InfoWidget` | `"top-left"` | Layer hover/pick information |
| `splitter_widget()` | `SplitterWidget` | — | Split-screen view divider |
| `stats_widget()` | `StatsWidget` | `"top-left"` | GPU/CPU performance statistics |
| `view_selector_widget()` | `ViewSelectorWidget` | `"top-left"` | Switch between view modes |

Every helper accepts `placement` (where supported) and `**kwargs` passed directly as widget properties.

```python
from shiny_deckgl import (
    zoom_widget, compass_widget, fullscreen_widget,
    scale_widget, fps_widget, loading_widget,
)

await widget.set_widgets(session, [
    zoom_widget(),
    compass_widget(),
    fullscreen_widget(),
    scale_widget(placement="bottom-left"),
    fps_widget(placement="top-left"),
    loading_widget(),
])
```

---

## Camera Transitions (v0.8)

Smooth camera movements powered by MapLibre's built-in `flyTo` and `easeTo` methods.

### `fly_to()`

```python
await widget.fly_to(
    session: Session,
    longitude: float,
    latitude: float,
    zoom: float | None = None,
    pitch: float | None = None,
    bearing: float | None = None,
    speed: float = 1.2,
    duration: int | str = "auto",
) -> None
```

Smooth fly-to camera transition using MapLibre `flyTo`. The camera departs the current view, zooms out to show both origin and destination, then zooms in to the target.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `longitude` | `float` | *(required)* | Target longitude. |
| `latitude` | `float` | *(required)* | Target latitude. |
| `zoom` | `float \| None` | `None` | Target zoom (unchanged if `None`). |
| `pitch` | `float \| None` | `None` | Target pitch in degrees. |
| `bearing` | `float \| None` | `None` | Target bearing in degrees. |
| `speed` | `float` | `1.2` | Fly speed multiplier. |
| `duration` | `int \| str` | `"auto"` | Duration in ms, or `"auto"` for MapLibre-calculated. |

```python
await widget.fly_to(session, longitude=20.0, latitude=55.5,
                    zoom=8, pitch=45, speed=0.8)
```

### `ease_to()`

```python
await widget.ease_to(
    session: Session,
    longitude: float,
    latitude: float,
    zoom: float | None = None,
    pitch: float | None = None,
    bearing: float | None = None,
    duration: int = 1000,
) -> None
```

Smooth ease-to camera transition using MapLibre `easeTo`. Unlike `fly_to`, this is a simple linear interpolation without the zoom-out/zoom-in arc.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `longitude` | `float` | *(required)* | Target longitude. |
| `latitude` | `float` | *(required)* | Target latitude. |
| `zoom` | `float \| None` | `None` | Target zoom (unchanged if `None`). |
| `pitch` | `float \| None` | `None` | Target pitch in degrees. |
| `bearing` | `float \| None` | `None` | Target bearing in degrees. |
| `duration` | `int` | `1000` | Duration in milliseconds. |

```python
await widget.ease_to(session, longitude=21.0, latitude=56.0,
                     zoom=10, duration=2000)
```

---

## Transition Helper (v0.8)

### `transition()`

```python
transition(
    duration: int = 1000,
    easing: str | None = None,
    type: str = "interpolation",
    **kwargs,
) -> dict
```

Build a transition spec for a layer property. When assigned to a layer's `transitions` dict, the property will smoothly animate between values on data update.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `duration` | `int` | `1000` | Duration in ms (for `"interpolation"` type). |
| `easing` | `str \| None` | `None` | Named easing: `"ease-in-cubic"`, `"ease-out-cubic"`, `"ease-in-out-cubic"`, `"ease-in-out-sine"`. |
| `type` | `str` | `"interpolation"` | `"interpolation"` or `"spring"`. |
| `**kwargs` | | | Additional props, e.g. `stiffness`, `damping` for spring. |

```python
scatterplot_layer("pts", data,
    getRadius=10,
    transitions={
        "getRadius": transition(800, easing="ease-in-out-cubic"),
        "getFillColor": transition(500),
    },
)
```

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

### `depth_color()`

```python
depth_color(
    elevation: float,
    max_depth: float = 459.0,
    alpha: int = 210,
) -> list[int]
```

Map an elevation / depth value to a blue-gradient RGBA colour.

Produces a smooth dark-blue-to-teal ramp suitable for bathymetric visualisations.  At `elevation=0` the colour is a pale teal `[50, 180, 120, α]`; at `max_depth` it is a deep navy `[10, 60, 255, α]`.

| Parameter | Default | Description |
| --- | --- | --- |
| `elevation` | *(required)* | The depth or elevation value (0 = shallowest). |
| `max_depth` | `459.0` | Reference maximum depth for normalisation (roughly the Baltic Sea's Landsort Deep). |
| `alpha` | `210` | Alpha channel (0–255). |

**Returns** `[R, G, B, A]`.

```python
from shiny_deckgl import depth_color
shallow = depth_color(10)   # pale teal
deep    = depth_color(400)  # deep navy
```

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

### `globe_view()`

```python
globe_view(**kwargs) -> dict
```

Create a `GlobeView` spec for a 3D globe projection. Renders the earth as a globe rather than a flat Mercator projection. Useful for visualising global datasets.

```python
await widget.update(session, layers=my_layers,
                    views=[globe_view(controller=True)])
```

### `orbit_view()`

```python
orbit_view(**kwargs) -> dict
```

Create an `OrbitView` spec for orbiting around a 3-D target (meshes, point clouds).  The camera orbits around a `target` point rather than a geographic location.

| Parameter | Type | Description |
| --- | --- | --- |
| `target` | `list[float]` | `[x, y, z]` point to orbit around. |
| `rotationX` | `float` | Rotation around the X axis (pitch). |
| `rotationOrbit` | `float` | Rotation around the orbit axis (yaw). |
| `zoom` | `float` | Zoom level. |
| `controller` | `bool` | Enable user interaction (default `True`). |

```python
await widget.update(session, layers=my_layers,
                    views=[orbit_view(target=[0, 0, 0], zoom=4, controller=True)])
```

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

Pass an `effects` list to `widget.update()` for ambient/point lighting.

**Recommended (v1.2+):** use the typed [Effects Helpers](#effects-helpers-v12):

```python
from shiny_deckgl import lighting_effect, ambient_light, point_light

effects = [
    lighting_effect(
        ambient_light(intensity=1.0),
        point_light([21.1, 55.7, 8000], color=[255, 200, 150], intensity=2.0),
    ),
]

await widget.update(session, layers=my_layers, effects=effects)
```

**Raw dict approach (still supported):**

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

The JS client resolves `LightingEffect` specs into `deck.LightingEffect` instances with `deck.AmbientLight`, `deck.PointLight`, `deck.DirectionalLight`, and `deck._SunLight` sub-objects.

---

## Layer Helpers (v0.9)

New layer helpers for geo-spatial analysis, animation, and tiled data sources.
All return plain `dict` objects for use with `widget.update()`.

### `trips_layer()`

Animated vehicle/vessel tracks using deck.gl's `TripsLayer`.

```python
shiny_deckgl.trips_layer(
    id: str,
    data: list | dict,
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `pickable` | `True` | Enable hover/click |
| `getPath` | `"@@d.path"` | Accessor for `[lon, lat, timestamp]` arrays |
| `getTimestamps` | `"@@d.timestamps"` | Accessor for timestamp arrays |
| `getColor` | `[253, 128, 93]` | Trail colour |
| `widthMinPixels` | `2` | Minimum trail width |
| `trailLength` | `200` | Trail length in time units |
| `currentTime` | `0` | Current animation time |

**Animation config:** Pass `_tripsAnimation={"loopLength": 1800, "speed": 1}` to enable
automatic client-side animation via `requestAnimationFrame`.

```python
trips_layer("ships", trips_data,
            trailLength=300,
            _tripsAnimation={"loopLength": 1800, "speed": 1.5})
```

### `great_circle_layer()`

Geodesic arcs (shortest path on sphere) — unlike `arc_layer()` parabolic arcs.

```python
shiny_deckgl.great_circle_layer(
    id: str,
    data: list | dict,
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `pickable` | `True` | Enable hover/click |
| `getSourcePosition` | `"@@d.sourcePosition"` | Source point accessor |
| `getTargetPosition` | `"@@d.targetPosition"` | Target point accessor |
| `getSourceColor` | `[64, 255, 0]` | Colour at source |
| `getTargetColor` | `[0, 128, 200]` | Colour at target |
| `getWidth` | `2` | Arc width |

### `contour_layer()`

Isoline/isoband visualisation from point data.

```python
shiny_deckgl.contour_layer(
    id: str,
    data: list | dict,
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `getPosition` | `"@@d"` | Point position accessor |
| `cellSize` | `200` | Grid cell size in metres |
| `contours` | *(3 default thresholds)* | Array of `{threshold, color, strokeWidth}` |

### `grid_layer()`

Rectangular spatial binning with optional 3-D extrusion.

```python
shiny_deckgl.grid_layer(
    id: str,
    data: list | dict,
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `getPosition` | `"@@d"` | Point position accessor |
| `cellSize` | `200` | Cell size in metres |
| `elevationScale` | `4` | Elevation multiplier |
| `extruded` | `True` | Enable 3-D columns |

### `screen_grid_layer()`

Screen-space binning — fast density grid in pixel coordinates.

```python
shiny_deckgl.screen_grid_layer(
    id: str,
    data: list | dict,
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `getPosition` | `"@@d"` | Point position accessor |
| `cellSizePixels` | `20` | Cell size in pixels |
| `colorRange` | *(6-stop warm palette)* | Colour ramp array |

### `mvt_layer()`

Mapbox Vector Tiles for rendering large tilesets.

```python
shiny_deckgl.mvt_layer(
    id: str,
    data: str,          # tile URL template
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `minZoom` | `0` | Minimum zoom level |
| `maxZoom` | `14` | Maximum zoom level |
| `getFillColor` | `[200, 200, 200]` | Fill colour |
| `getLineColor` | `[100, 100, 100]` | Stroke colour |
| `lineWidthMinPixels` | `1` | Minimum stroke width |

### `wms_layer()` (deck.gl)

deck.gl 9.x native WMS layer for OGC Web Map Services.

```python
shiny_deckgl.wms_layer(
    id: str,
    data: str,          # WMS service URL
    **kwargs,
) -> dict
```

**Default properties:**

| Property | Default | Description |
| --- | --- | --- |
| `srs` | `"EPSG:4326"` | Spatial reference system |
| `format` | `"image/png"` | Image format |

---

## Interleaved Rendering (v0.9)

Enable interleaved rendering to allow deck.gl layers to be interspersed with
MapLibre basemap labels, buildings, and other layers:

```python
widget = MapWidget("map", interleaved=True)
```

When `interleaved=True`, the `MapboxOverlay` is created with
`interleaved: true`, allowing deck.gl layers to appear between basemap
layers rather than always on top.

**Note:** Interleaved rendering may have performance implications with many
layers.  Test with your specific layer combination.

---

## TripsLayer Animation (v0.9)

The TripsLayer includes a built-in client-side animation engine.  Pass a
`_tripsAnimation` config dict to any `trips_layer()` call:

```python
trips_layer("ships", data,
            trailLength=200,
            _tripsAnimation={"loopLength": 1800, "speed": 1.0})
```

| Config Key | Type | Description |
| --- | --- | --- |
| `loopLength` | `int` | Total animation duration (time units) |
| `speed` | `float` | Animation speed multiplier |

The JavaScript engine uses `requestAnimationFrame` to increment `currentTime`
each frame.  When `currentTime` reaches `loopLength`, it wraps back to `0`.
The animation starts automatically when the TripsLayer is detected after
`widget.update()`.

---

## Extension Helpers (v1.0)

Extension helpers create specs for deck.gl layer extensions.  Pass them in the
`extensions` list of any `layer()` call.  No-argument extensions return a plain
string; extensions with options return a `[name, options]` pair.

```python
from shiny_deckgl import layer, brushing_extension, data_filter_extension

layer(
    "ScatterplotLayer", "pts", data=points,
    extensions=[brushing_extension(), data_filter_extension(filter_size=1)],
    brushingRadius=50000,
    brushingEnabled=True,
    getFilterValue="@@d.year",
    filterRange=[2010, 2020],
)
```

### `brushing_extension()`

```python
shiny_deckgl.brushing_extension() -> str
```

Highlight features near the cursor.

**Layer props enabled:** `brushingRadius`, `brushingEnabled`, `brushingTarget`.

### `collision_filter_extension()`

```python
shiny_deckgl.collision_filter_extension() -> str
```

Hide overlapping labels/icons.

**Layer props enabled:** `collisionEnabled`, `collisionGroup`, `collisionTestProps`, `getCollisionPriority`.

### `data_filter_extension()`

```python
shiny_deckgl.data_filter_extension(filter_size: int = 1) -> list
```

GPU-accelerated data filtering.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `filter_size` | `int` | `1` | Number of filter dimensions (1–4). |

**Layer props enabled:** `getFilterValue`, `filterRange`, `filterSoftRange`, `filterEnabled`, `filterTransformSize`, `filterTransformColor`.

### `mask_extension()`

```python
shiny_deckgl.mask_extension() -> str
```

Clip layer rendering to a GeoJSON mask.

**Layer props enabled:** `maskId`, `maskByInstance`, `maskInverted`.

### `clip_extension()`

```python
shiny_deckgl.clip_extension() -> str
```

Clip layer rendering to the current view bounds for performance.

### `terrain_extension()`

```python
shiny_deckgl.terrain_extension() -> str
```

Drape layers onto a 3D terrain surface.

**Layer props enabled:** `terrainDrawMode`.

### `fill_style_extension()`

```python
shiny_deckgl.fill_style_extension(pattern: bool = True) -> list
```

Apply fill patterns to polygon layers.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `pattern` | `bool` | `True` | Enable pattern fills. |

**Layer props enabled:** `fillPatternAtlas`, `fillPatternMapping`, `fillPatternMask`, `getFillPattern`, `getFillPatternScale`, `getFillPatternOffset`.

### `path_style_extension()`

```python
shiny_deckgl.path_style_extension(dash: bool = False, high_precision: bool = False) -> list
```

Dashed/offset path rendering.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `dash` | `bool` | `False` | Enable dash patterns. |
| `high_precision` | `bool` | `False` | Use pixel-perfect dash rendering (slower). |

**Layer props enabled:** `getDashArray`, `dashJustified`, `getOffset`.

### `fp64_extension()`

```python
shiny_deckgl.fp64_extension() -> str
```

`Fp64Extension` — enable 64-bit floating-point rendering on the GPU for layers that need extremely precise positioning. Useful when visualising data at very high zoom levels or with coordinates that span a wide range.

**Layer props enabled:** `fp64` — set to `True` to activate.

```python
layer("ScatterplotLayer", "pts", data,
      extensions=[fp64_extension()],
      fp64=True)
```

---

## Cluster Layers (v1.0)

### `add_cluster_layer()`

```python
await widget.add_cluster_layer(
    session,
    source_id: str,
    data: dict | str | list,
    *,
    cluster_radius: int = 50,
    cluster_max_zoom: int = 14,
    cluster_color: str = "#51bbd6",
    cluster_stroke_color: str = "#ffffff",
    cluster_stroke_width: int = 1,
    cluster_text_color: str = "#ffffff",
    cluster_text_size: int = 12,
    point_color: str = "#11b4da",
    point_radius: int = 5,
    point_stroke_color: str = "#ffffff",
    point_stroke_width: int = 1,
    size_steps: list | None = None,
    cluster_properties: dict | None = None,
) -> None
```

Add clustered GeoJSON points with click-to-zoom.  Creates a GeoJSON source
with `cluster: true` plus three MapLibre layers: cluster circles, count labels,
and unclustered points.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `source_id` | `str` | *(required)* | Unique source identifier.  Layers created: `{source_id}-clusters`, `{source_id}-count`, `{source_id}-unclustered`. |
| `data` | `dict \| str \| list` | *(required)* | GeoJSON FeatureCollection (dict), URL string, or list of `[lon, lat]` pairs. |
| `cluster_radius` | `int` | `50` | Pixel radius for merging points. |
| `cluster_max_zoom` | `int` | `14` | Max zoom at which clusters are generated. |
| `cluster_color` | `str` | `"#51bbd6"` | Fill colour for cluster circles. |
| `cluster_stroke_color` | `str` | `"#ffffff"` | Stroke colour for cluster circles. |
| `cluster_stroke_width` | `int` | `1` | Stroke width for cluster circles. |
| `cluster_text_color` | `str` | `"#ffffff"` | Colour for count labels. |
| `cluster_text_size` | `int` | `12` | Font size for count labels. |
| `point_color` | `str` | `"#11b4da"` | Fill colour for unclustered points. |
| `point_radius` | `int` | `5` | Radius for unclustered points. |
| `point_stroke_color` | `str` | `"#ffffff"` | Stroke colour for unclustered points. |
| `point_stroke_width` | `int` | `1` | Stroke width for unclustered points. |
| `size_steps` | `list \| None` | `[[0,18],[100,24],[750,32]]` | `[count, radius]` pairs for cluster circle size interpolation. |
| `cluster_properties` | `dict \| None` | `None` | MapLibre `clusterProperties` for aggregate computations. |

```python
await widget.add_cluster_layer(session, "ports", port_geojson,
                                cluster_radius=60,
                                cluster_color="#ff6b6b",
                                point_color="#ffd93d")
```

### `remove_cluster_layer()`

```python
await widget.remove_cluster_layer(session, source_id: str) -> None
```

Remove a cluster layer group and its underlying GeoJSON source.

```python
await widget.remove_cluster_layer(session, "ports")
```

---

## Cooperative Gestures (v1.0)

### `set_cooperative_gestures()`

```python
await widget.set_cooperative_gestures(
    session,
    enabled: bool,
) -> None
```

Toggle cooperative gestures on the map.  When enabled, the user must hold
**Ctrl** (or **⌘** on macOS) while scrolling to zoom, and two-finger drag is
required on touch devices.

```python
# Enable (e.g. for maps embedded in scrollable pages)
await widget.set_cooperative_gestures(session, True)

# Also configurable at construction time:
widget = MapWidget("map", cooperative_gestures=True)
```

---

## Controller (v1.0)

### `set_controller()`

```python
await widget.set_controller(
    session,
    options: bool | dict,
) -> None
```

Configure map controller behaviour at runtime.

| Parameter | Type | Description |
| --- | --- | --- |
| `options` | `bool \| dict` | `True` enables default controller.  `False` disables all interaction.  A dict fine-tunes specific behaviours. |

```python
# Disable double-click zoom, enable touch rotate
await widget.set_controller(session, {
    "touchRotate": True,
    "doubleClickZoom": False,
})

# Disable all interaction
await widget.set_controller(session, False)
```

---

## CLI

The package installs a `shiny_deckgl-demo` console script:

```bash
shiny_deckgl-demo
```

This launches the built-in demo app centred on the Baltic Sea with 10 tabs
showcasing all features: scatter layers, WMS, controls, drawing tools,
markers, popups, terrain, extensions, clustering, lighting, effects,
IBM trips animation, and a Layer Gallery of all 24 layer helpers.

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
