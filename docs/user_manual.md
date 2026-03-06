# shiny_deckgl User Manual

> **Version 1.6.1** — A comprehensive guide to building interactive geospatial visualizations with Shiny for Python and deck.gl.

---

## Table of Contents

1. [Introduction](#introduction)
2. [How shiny_deckgl Compares to Other Tools](#how-shiny_deckgl-compares-to-other-tools)
   - [vs. deck.gl (JavaScript)](#vs-deckgl-javascript)
   - [vs. Kepler.gl](#vs-keplergl)
   - [vs. PyDeck](#vs-pydeck)
   - [vs. Folium / Leaflet](#vs-folium--leaflet)
   - [vs. Plotly / Mapbox](#vs-plotly--mapbox)
   - [When to Choose shiny_deckgl](#when-to-choose-shiny_deckgl)
3. [Core Concepts](#core-concepts)
   - [MapWidget](#mapwidget)
   - [Layers](#layers)
   - [Views](#views)
   - [Controls and Widgets](#controls-and-widgets)
4. [Representing Map Features](#representing-map-features)
   - [Point Data](#point-data)
   - [Line and Path Data](#line-and-path-data)
   - [Polygon and Area Data](#polygon-and-area-data)
   - [Raster and Tile Data](#raster-and-tile-data)
   - [3D Features](#3d-features)
   - [Text and Labels](#text-and-labels)
5. [Visualizing Model Results](#visualizing-model-results)
   - [Hydrodynamic Model Output](#hydrodynamic-model-output)
   - [Species Distribution Models](#species-distribution-models)
   - [Trajectory and Particle Tracking](#trajectory-and-particle-tracking)
   - [Aggregated Statistics](#aggregated-statistics)
   - [Time Series Animation](#time-series-animation)
6. [Layer Selection Guide](#layer-selection-guide)
7. [Color Scales and Styling](#color-scales-and-styling)
8. [Interactivity](#interactivity)
9. [Performance Optimization](#performance-optimization)
10. [Complete Examples](#complete-examples)

---

## Introduction

**shiny_deckgl** is a Python library that bridges [Shiny for Python](https://shiny.posit.co/py/) with [deck.gl](https://deck.gl/), enabling scientists and developers to create high-performance, interactive geospatial visualizations directly from Python. It was designed with marine science and GIS applications in mind, but is suitable for any domain requiring map-based data visualization.

### Key Features

- **33 layer types** covering points, lines, polygons, heatmaps, 3D meshes, and more
- **Reactive updates** — layers respond to user inputs in real-time
- **No JavaScript required** — configure everything from Python
- **High performance** — WebGL-accelerated rendering handles millions of points
- **WMS/WMTS support** — integrate with EMODnet, GEBCO, HELCOM, and other OGC services
- **Binary transport** — efficient numpy array serialization for large datasets
- **HTML export** — generate standalone maps for reports and sharing

---

## How shiny_deckgl Compares to Other Tools

### vs. deck.gl (JavaScript)

| Aspect | deck.gl (JS) | shiny_deckgl |
|--------|--------------|--------------|
| **Language** | JavaScript/TypeScript | Python |
| **Learning curve** | Requires JS ecosystem knowledge | Python-only, familiar to data scientists |
| **Reactivity** | Manual state management | Built-in Shiny reactivity |
| **Server integration** | Requires custom backend | Native Python server with Shiny |
| **Feature parity** | Full deck.gl API | 33 layer types, all major features |
| **Use case** | Production web apps | Data analysis, dashboards, prototypes |

**shiny_deckgl** wraps deck.gl's JavaScript library, providing Python bindings for the most commonly used features. You get ~90% of deck.gl's power without writing JavaScript.

### vs. Kepler.gl

| Aspect | Kepler.gl | shiny_deckgl |
|--------|-----------|--------------|
| **Interface** | GUI-driven, drag-and-drop | Code-driven, programmatic |
| **Customization** | Limited to GUI options | Full programmatic control |
| **Reproducibility** | Export/import JSON configs | Version-controlled Python code |
| **Server-side logic** | None (client-only) | Full Python backend |
| **Data size** | Limited by browser memory | Stream from server, binary transport |
| **Integration** | Standalone or Jupyter | Embeds in Shiny apps |

**Choose Kepler.gl** for quick exploratory visualization without coding.
**Choose shiny_deckgl** when you need programmatic control, reproducibility, or server-side data processing.

### vs. PyDeck

| Aspect | PyDeck | shiny_deckgl |
|--------|--------|--------------|
| **Framework** | Jupyter-focused | Shiny-focused |
| **Reactivity** | Limited (Jupyter widgets) | Full Shiny reactive system |
| **UI components** | Minimal | Rich Shiny UI components |
| **Production deployment** | Requires additional setup | Native Shiny deployment |
| **MapLibre integration** | deck.gl only | deck.gl + MapLibre controls |
| **WMS support** | Basic | First-class with bbox templates |

**Choose PyDeck** for Jupyter notebook exploration.
**Choose shiny_deckgl** for building interactive applications with controls, forms, and server logic.

### vs. Folium / Leaflet

| Aspect | Folium/Leaflet | shiny_deckgl |
|--------|----------------|--------------|
| **Rendering** | SVG/Canvas (Leaflet) | WebGL (deck.gl) |
| **Performance** | ~10,000 points | Millions of points |
| **3D support** | Limited | Full 3D (terrain, meshes, extrusion) |
| **Layer types** | Basic (markers, polygons) | 33 specialized layer types |
| **Styling** | CSS-based | GPU-accelerated, data-driven |

**Choose Folium** for simple maps with few features.
**Choose shiny_deckgl** when you need performance, 3D, or specialized visualizations.

### vs. Plotly / Mapbox

| Aspect | Plotly Mapbox | shiny_deckgl |
|--------|---------------|--------------|
| **Backend** | Mapbox GL JS | MapLibre GL JS (open source) |
| **API key required** | Yes (for most styles) | No (uses open basemaps) |
| **Layer types** | Plotly trace types | 33 deck.gl layer types |
| **Aggregation layers** | Limited | HexagonLayer, GridLayer, HeatmapLayer, etc. |
| **Scientific viz** | General purpose | Designed for scientific data |

**Choose Plotly** for general-purpose dashboards with Dash.
**Choose shiny_deckgl** for scientific visualization without API key requirements.

### When to Choose shiny_deckgl

shiny_deckgl is the right choice when you need:

1. **High-performance rendering** of large geospatial datasets
2. **Server-side data processing** with reactive updates
3. **Scientific visualization** (model output, trajectories, meshes)
4. **WMS/OGC service integration** (EMODnet, GEBCO, national SDIs)
5. **3D visualization** (terrain, bathymetry, extruded features)
6. **No vendor lock-in** (open-source stack, no API keys)
7. **Python-native workflow** integrated with pandas, numpy, geopandas

---

## Core Concepts

### MapWidget

The `MapWidget` is the central component — it manages the map view, layers, and user interactions.

```python
from shiny_deckgl import MapWidget, head_includes

# Create a map widget
map_widget = MapWidget(
    "mymap",                                    # Unique ID
    view_state={                                # Initial camera position
        "longitude": 20.0,
        "latitude": 56.0,
        "zoom": 6,
        "pitch": 0,
        "bearing": 0,
    },
    style=CARTO_POSITRON,                       # Basemap style
    tooltip={"html": "<b>{name}</b>"},          # Hover tooltip template
)

# In your UI
app_ui = ui.page_fluid(
    head_includes(),                            # Required CSS/JS
    map_widget.ui(height="600px"),              # Render the map
)

# In your server
async def update_map():
    layers = [scatterplot_layer("points", data)]
    await map_widget.update(session, layers)
```

### Layers

Layers are the visual elements on the map. shiny_deckgl provides 33 typed layer helpers:

| Category | Layers |
|----------|--------|
| **Core** | `scatterplot_layer`, `geojson_layer`, `arc_layer`, `line_layer`, `path_layer`, `icon_layer`, `text_layer`, `column_layer`, `polygon_layer`, `bitmap_layer`, `grid_cell_layer`, `solid_polygon_layer` |
| **Aggregation** | `heatmap_layer`, `hexagon_layer`, `grid_layer`, `screen_grid_layer`, `contour_layer` |
| **Geo-spatial** | `h3_hexagon_layer`, `h3_cluster_layer`, `a5_layer`, `geohash_layer`, `quadkey_layer`, `s2_layer`, `great_circle_layer`, `trips_layer` |
| **Tile/Raster** | `tile_layer`, `mvt_layer`, `wms_layer`, `terrain_layer`, `tile_3d_layer` |
| **3D/Mesh** | `point_cloud_layer`, `simple_mesh_layer`, `scenegraph_layer` |

### Views

Views control how the map is projected and rendered:

```python
from shiny_deckgl import map_view, globe_view, orthographic_view

# Standard 2D map
views = [map_view()]

# 3D globe
views = [globe_view()]

# Orthographic (flat, no perspective)
views = [orthographic_view()]
```

### Controls and Widgets

**MapLibre Controls** — UI elements on the map:
- Navigation (zoom buttons, compass)
- Scale bar
- Fullscreen toggle
- Geolocate (GPS position)
- Globe/Terrain toggles

**deck.gl Widgets** — Overlay widgets:
- Zoom, Compass, Gimbal
- Screenshot, FPS counter
- Loading indicator
- Timeline (for animations)

```python
from shiny_deckgl import zoom_widget, compass_widget, scale_widget

await map_widget.set_widgets(session, [
    zoom_widget(),
    compass_widget(),
    scale_widget(),
])
```

---

## Representing Map Features

### Point Data

**Use cases:** Sampling stations, port locations, species observations, sensor positions.

#### ScatterplotLayer — Variable-sized circles

Best for: Quantitative point data with size/color encoding.

```python
from shiny_deckgl import scatterplot_layer

# Data: list of dicts or DataFrame
stations = [
    {"position": [20.5, 55.7], "temperature": 12.5, "name": "Station A"},
    {"position": [21.1, 56.2], "temperature": 14.2, "name": "Station B"},
]

layer = scatterplot_layer(
    "stations",
    stations,
    getPosition="@@=d.position",
    getRadius="@@=d.temperature * 100",     # Size by temperature
    getFillColor=[65, 182, 196, 200],
    radiusMinPixels=5,
    radiusMaxPixels=50,
    pickable=True,                          # Enable hover/click
)
```

#### IconLayer — Custom markers

Best for: Categorical point data with distinct symbols.

```python
from shiny_deckgl import icon_layer

ports = [
    {"position": [18.68, 54.37], "type": "cargo", "name": "Gdansk"},
    {"position": [21.00, 55.72], "type": "ferry", "name": "Klaipeda"},
]

layer = icon_layer(
    "ports",
    ports,
    getPosition="@@=d.position",
    iconAtlas="https://example.com/icons.png",
    iconMapping={
        "cargo": {"x": 0, "y": 0, "width": 64, "height": 64},
        "ferry": {"x": 64, "y": 0, "width": 64, "height": 64},
    },
    getIcon="@@=d.type",
    getSize=32,
    pickable=True,
)
```

#### ColumnLayer — 3D bars at points

Best for: Magnitude data requiring height encoding.

```python
from shiny_deckgl import column_layer

catches = [
    {"position": [20.5, 55.7], "tonnes": 1500},
    {"position": [21.1, 56.2], "tonnes": 2300},
]

layer = column_layer(
    "catches",
    catches,
    getPosition="@@=d.position",
    getElevation="@@=d.tonnes",
    elevationScale=10,
    radius=5000,
    getFillColor=[255, 140, 0, 200],
    extruded=True,
    pickable=True,
)
```

### Line and Path Data

**Use cases:** Ship tracks, migration routes, cables, pipelines, transects.

#### LineLayer — Simple straight lines

Best for: Point-to-point connections.

```python
from shiny_deckgl import line_layer

connections = [
    {"sourcePosition": [18.68, 54.37], "targetPosition": [21.00, 55.72]},
]

layer = line_layer(
    "connections",
    connections,
    getSourcePosition="@@=d.sourcePosition",
    getTargetPosition="@@=d.targetPosition",
    getColor=[100, 100, 200],
    getWidth=2,
    pickable=True,
)
```

#### ArcLayer — Curved arcs

Best for: Origin-destination flows, showing direction.

```python
from shiny_deckgl import arc_layer

flows = [
    {
        "source": [18.68, 54.37],
        "target": [21.00, 55.72],
        "volume": 500,
    },
]

layer = arc_layer(
    "flows",
    flows,
    getSourcePosition="@@=d.source",
    getTargetPosition="@@=d.target",
    getSourceColor=[0, 128, 255],
    getTargetColor=[255, 0, 128],
    getWidth="@@=d.volume / 100",
    pickable=True,
)
```

#### GreatCircleLayer — Geodesic arcs

Best for: Long-distance routes following Earth's curvature.

```python
from shiny_deckgl import great_circle_layer

routes = [
    {"source": [18.68, 54.37], "target": [-74.0, 40.7], "name": "Baltic-NYC"},
]

layer = great_circle_layer(
    "routes",
    routes,
    getSourcePosition="@@=d.source",
    getTargetPosition="@@=d.target",
    getSourceColor=[0, 200, 80],
    getTargetColor=[200, 0, 80],
    getWidth=2,
    pickable=True,
)
```

#### PathLayer — Multi-segment paths

Best for: GPS tracks, survey transects, complex routes.

```python
from shiny_deckgl import path_layer

tracks = [
    {
        "path": [[20.0, 55.0], [20.5, 55.5], [21.0, 55.3], [21.5, 55.8]],
        "vessel": "RV Baltica",
        "color": [255, 100, 50],
    },
]

layer = path_layer(
    "tracks",
    tracks,
    getPath="@@=d.path",
    getColor="@@=d.color",
    widthMinPixels=2,
    pickable=True,
)
```

#### TripsLayer — Animated paths

Best for: Temporal trajectories, AIS playback, drifter tracks.

```python
from shiny_deckgl import trips_layer

trips = [
    {
        "path": [[20.0, 55.0], [20.5, 55.5], [21.0, 55.3]],
        "timestamps": [0, 300, 600],  # seconds
        "vessel": "Ferry Alpha",
    },
]

layer = trips_layer(
    "trips",
    trips,
    getPath="@@=d.path",
    getTimestamps="@@=d.timestamps",
    getColor=[253, 128, 93],
    widthMinPixels=3,
    trailLength=200,
    currentTime=300,
)
```

### Polygon and Area Data

**Use cases:** Marine protected areas, EEZ boundaries, habitat zones, model grid cells.

#### GeoJsonLayer — GeoJSON features

Best for: Standard GIS data (polygons, multipolygons, mixed geometries).

```python
from shiny_deckgl import geojson_layer

# GeoJSON FeatureCollection
mpa_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Curonian Spit", "area_km2": 264},
            "geometry": {"type": "Polygon", "coordinates": [...]},
        },
    ],
}

layer = geojson_layer(
    "mpas",
    mpa_geojson,
    getFillColor=[0, 180, 120, 100],
    getLineColor=[0, 180, 120, 255],
    lineWidthMinPixels=2,
    pickable=True,
)
```

#### PolygonLayer — Polygon arrays

Best for: Dynamic polygon data from arrays (not GeoJSON).

```python
from shiny_deckgl import polygon_layer

zones = [
    {
        "polygon": [[20.0, 55.0], [20.5, 55.0], [20.5, 55.5], [20.0, 55.5]],
        "name": "Zone A",
        "color": [100, 150, 200, 150],
    },
]

layer = polygon_layer(
    "zones",
    zones,
    getPolygon="@@=d.polygon",
    getFillColor="@@=d.color",
    getLineColor=[0, 0, 0, 100],
    pickable=True,
)
```

#### H3HexagonLayer — H3 hexagonal cells

Best for: Hexagonal binning with H3 indices.

```python
from shiny_deckgl import h3_hexagon_layer

h3_cells = [
    {"hex": "8928308280fffff", "value": 42, "color": [255, 140, 0, 180]},
    {"hex": "8928308281fffff", "value": 67, "color": [255, 100, 0, 180]},
]

layer = h3_hexagon_layer(
    "h3",
    h3_cells,
    getHexagon="@@=d.hex",
    getFillColor="@@=d.color",
    extruded=False,
    pickable=True,
)
```

### Raster and Tile Data

**Use cases:** Bathymetry, satellite imagery, WMS services, basemap overlays.

#### TileLayer — XYZ/TMS tiles

Best for: Pre-rendered tile services.

```python
from shiny_deckgl import tile_layer

layer = tile_layer(
    "osm",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    minZoom=0,
    maxZoom=19,
    tileSize=256,
    opacity=0.7,
)
```

#### WMSLayer — OGC WMS services

Best for: EMODnet, GEBCO, national mapping agencies.

```python
from shiny_deckgl import wms_layer

layer = wms_layer(
    "bathymetry",
    "https://ows.emodnet-bathymetry.eu/wms",
    layers=["emodnet:mean_atlas_land"],
    transparent=True,
    opacity=0.8,
)
```

#### BitmapLayer — Georeferenced images

Best for: Single images with known bounds.

```python
from shiny_deckgl import bitmap_layer

layer = bitmap_layer(
    "satellite",
    image="https://example.com/satellite.png",
    bounds=[18.0, 54.0, 22.0, 57.0],  # [west, south, east, north]
    opacity=0.9,
)
```

### 3D Features

**Use cases:** Terrain visualization, bathymetry, 3D city models, mesh output.

#### TerrainLayer — Elevation mesh from tiles

Best for: Terrain/bathymetry from DEM tiles.

```python
from shiny_deckgl import terrain_layer

layer = terrain_layer(
    "terrain",
    elevationData="https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
    texture="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    elevationDecoder={
        "rScaler": 256, "gScaler": 1, "bScaler": 1/256, "offset": -32768
    },
    meshMaxError=4.0,
)
```

#### PointCloudLayer — 3D point clouds

Best for: LiDAR data, sonar point clouds.

```python
from shiny_deckgl import point_cloud_layer

points = [
    {"position": [20.0, 55.0, 100], "color": [255, 100, 50]},
    {"position": [20.1, 55.1, 150], "color": [255, 150, 50]},
]

layer = point_cloud_layer(
    "lidar",
    points,
    getPosition="@@=d.position",
    getColor="@@=d.color",
    pointSize=3,
    pickable=True,
)
```

#### SimpleMeshLayer — 3D model instances

Best for: Placing 3D objects (ships, buoys) on the map.

```python
from shiny_deckgl import simple_mesh_layer

objects = [
    {"position": [20.5, 55.5, 0], "name": "Buoy A"},
]

layer = simple_mesh_layer(
    "buoys",
    objects,
    getPosition="@@=d.position",
    mesh="@@SphereGeometry",  # Built-in geometry
    sizeScale=1000,
    getColor=[255, 200, 0],
    pickable=True,
)
```

### Text and Labels

#### TextLayer — Map labels

```python
from shiny_deckgl import text_layer

labels = [
    {"position": [20.5, 55.7], "text": "Klaipeda", "size": 14},
]

layer = text_layer(
    "labels",
    labels,
    getPosition="@@=d.position",
    getText="@@=d.text",
    getSize="@@=d.size",
    getColor=[0, 0, 0, 255],
    getTextAnchor="middle",
    getAlignmentBaseline="center",
    fontWeight="bold",
    pickable=True,
)
```

---

## Visualizing Model Results

### Hydrodynamic Model Output

**SHYFEM, ROMS, NEMO, Delft3D** — Finite element/difference model output.

#### Mesh visualization with SimpleMeshLayer

```python
from shiny_deckgl import simple_mesh_layer, custom_geometry
from shiny_deckgl.parsers import parse_shyfem_mesh

# Parse SHYFEM .grd file
mesh_data = parse_shyfem_mesh("model_output.grd", z_scale=500)

layer = simple_mesh_layer(
    "mesh",
    **custom_geometry(mesh_data),
    pickable=True,
    wireframe=False,
)
```

#### Scalar field on polygons

```python
from shiny_deckgl import polygon_layer, color_range, PALETTE_THERMAL

# Model output: temperature per cell
cells = [
    {"polygon": [...], "temperature": 12.5},
    {"polygon": [...], "temperature": 14.2},
]

# Color by temperature
temps = [c["temperature"] for c in cells]
colors = color_range(len(cells), palette=PALETTE_THERMAL)

for i, cell in enumerate(cells):
    cell["color"] = colors[i]

layer = polygon_layer(
    "temperature",
    cells,
    getPolygon="@@=d.polygon",
    getFillColor="@@=d.color",
    pickable=True,
)
```

#### Velocity vectors with IconLayer

```python
from shiny_deckgl import icon_layer
import math

# Model output: velocity at grid points
velocities = [
    {"position": [20.0, 55.0], "u": 0.5, "v": 0.3},  # m/s
]

# Calculate arrow rotation
for v in velocities:
    v["angle"] = math.degrees(math.atan2(v["v"], v["u"]))
    v["magnitude"] = math.sqrt(v["u"]**2 + v["v"]**2)

layer = icon_layer(
    "currents",
    velocities,
    getPosition="@@=d.position",
    getAngle="@@=d.angle",
    getSize="@@=d.magnitude * 50",
    iconAtlas="arrow_atlas.png",
    iconMapping={"arrow": {"x": 0, "y": 0, "width": 64, "height": 64}},
    getIcon="arrow",
)
```

### Species Distribution Models

**MaxEnt, SDMs, habitat suitability** — Probability/suitability surfaces.

#### HexagonLayer for occurrence aggregation

```python
from shiny_deckgl import hexagon_layer

# Species occurrences
occurrences = [
    {"position": [20.1, 55.2]},
    {"position": [20.3, 55.4]},
    # ... thousands of points
]

layer = hexagon_layer(
    "occurrences",
    occurrences,
    getPosition="@@=d.position",
    radius=10000,          # 10 km hexagons
    elevationScale=100,
    extruded=True,
    colorRange=[
        [255, 255, 178], [254, 204, 92], [253, 141, 60],
        [240, 59, 32], [189, 0, 38]
    ],
    pickable=True,
)
```

#### GridLayer for model output

```python
from shiny_deckgl import grid_layer

# Predicted probability grid
predictions = [
    {"position": [20.0, 55.0], "probability": 0.8},
    {"position": [20.1, 55.0], "probability": 0.6},
]

layer = grid_layer(
    "sdm",
    predictions,
    getPosition="@@=d.position",
    cellSize=5000,
    elevationScale=1000,
    getElevationWeight="@@=d.probability",
    extruded=True,
    pickable=True,
)
```

#### ContourLayer for probability contours

```python
from shiny_deckgl import contour_layer

layer = contour_layer(
    "habitat",
    predictions,
    getPosition="@@=d.position",
    getWeight="@@=d.probability",
    cellSize=5000,
    contours=[
        {"threshold": 0.3, "color": [255, 255, 0], "strokeWidth": 1},
        {"threshold": 0.5, "color": [255, 165, 0], "strokeWidth": 2},
        {"threshold": 0.7, "color": [255, 0, 0], "strokeWidth": 3},
        {"threshold": [0.8, 1.0], "color": [128, 0, 128, 100]},  # Filled band
    ],
)
```

### Trajectory and Particle Tracking

**Lagrangian models, drifters, animal tracking** — Moving objects over time.

#### TripsLayer for animated trajectories

```python
from shiny_deckgl import trips_layer, format_trips

# Raw particle positions over time
particles = [
    {
        "id": "particle_1",
        "path": [[20.0, 55.0], [20.1, 55.1], [20.2, 55.0], [20.3, 55.2]],
        "timestamps": [0, 3600, 7200, 10800],  # seconds
    },
    # ... more particles
]

layer = trips_layer(
    "particles",
    particles,
    getPath="@@=d.path",
    getTimestamps="@@=d.timestamps",
    getColor=[253, 128, 93],
    widthMinPixels=2,
    trailLength=3600,     # 1 hour trail
    currentTime=5000,     # Animation time
)
```

#### PathLayer with color gradient for time

```python
from shiny_deckgl import path_layer, color_range

# Color path segments by time
track = {
    "path": [[20.0, 55.0], [20.1, 55.1], [20.2, 55.0]],
}

# Create multiple path segments with different colors
segments = []
colors = color_range(len(track["path"]) - 1, palette=PALETTE_VIRIDIS)

for i in range(len(track["path"]) - 1):
    segments.append({
        "path": [track["path"][i], track["path"][i + 1]],
        "color": colors[i],
    })

layer = path_layer(
    "track",
    segments,
    getPath="@@=d.path",
    getColor="@@=d.color",
    widthMinPixels=3,
)
```

### Aggregated Statistics

**Catch statistics, monitoring data, survey results** — Summarized by area.

#### H3HexagonLayer for hexagonal summaries

```python
from shiny_deckgl import h3_hexagon_layer, color_bins
import h3

# Aggregate catches to H3 cells
catches_by_cell = {}
for catch in catches:
    cell = h3.latlng_to_cell(catch["lat"], catch["lon"], resolution=5)
    catches_by_cell[cell] = catches_by_cell.get(cell, 0) + catch["kg"]

# Create layer data with colors
values = list(catches_by_cell.values())
colors = color_bins(values, n_bins=5, palette=PALETTE_OCEAN)

h3_data = [
    {"hex": cell, "value": val, "color": colors[i]}
    for i, (cell, val) in enumerate(catches_by_cell.items())
]

layer = h3_hexagon_layer(
    "catches",
    h3_data,
    getHexagon="@@=d.hex",
    getFillColor="@@=d.color",
    getElevation="@@=d.value",
    elevationScale=0.1,
    extruded=True,
    pickable=True,
)
```

### Time Series Animation

For time-varying model output, use reactive updates:

```python
from shiny import reactive

# Time slider in UI
ui.input_slider("time_step", "Time", min=0, max=100, value=0)

# Update layers when time changes
@reactive.Effect
@reactive.event(input.time_step)
async def update_timestep():
    t = input.time_step()

    # Get data for this timestep
    data = model_output[t]

    # Update layer
    layers = [polygon_layer("model", data, ...)]
    await map_widget.update(session, layers)
```

---

## Layer Selection Guide

| Data Type | Recommended Layer | Alternatives |
|-----------|-------------------|--------------|
| **Points (few)** | `scatterplot_layer` | `icon_layer`, `text_layer` |
| **Points (many)** | `heatmap_layer`, `hexagon_layer` | `screen_grid_layer`, `grid_layer` |
| **Points (3D)** | `column_layer`, `point_cloud_layer` | `scatterplot_layer` with elevation |
| **Lines (simple)** | `line_layer` | `arc_layer` |
| **Lines (complex)** | `path_layer` | `geojson_layer` |
| **Lines (animated)** | `trips_layer` | — |
| **Polygons (GeoJSON)** | `geojson_layer` | `polygon_layer` |
| **Polygons (arrays)** | `polygon_layer` | `solid_polygon_layer` |
| **Polygons (H3)** | `h3_hexagon_layer` | `h3_cluster_layer` |
| **Raster (tiles)** | `tile_layer` | `wms_layer`, `bitmap_layer` |
| **Raster (WMS)** | `wms_layer` | `tile_layer` with WMS URL |
| **3D terrain** | `terrain_layer` | — |
| **3D mesh** | `simple_mesh_layer` | `scenegraph_layer` |
| **3D models** | `scenegraph_layer` | `simple_mesh_layer` |
| **Contours** | `contour_layer` | `geojson_layer` with pre-computed contours |
| **Flow/OD** | `arc_layer` | `great_circle_layer`, `line_layer` |

---

## Color Scales and Styling

### Built-in Palettes

```python
from shiny_deckgl import (
    color_range,
    color_bins,
    color_quantiles,
    PALETTE_VIRIDIS,
    PALETTE_PLASMA,
    PALETTE_OCEAN,
    PALETTE_THERMAL,
    PALETTE_CHLOROPHYLL,
)

# Generate n colors from a palette
colors = color_range(10, palette=PALETTE_OCEAN)

# Classify values into bins
values = [10, 25, 30, 45, 80]
colors = color_bins(values, n_bins=5, palette=PALETTE_THERMAL)

# Quantile-based classification
colors = color_quantiles(values, n_quantiles=4, palette=PALETTE_VIRIDIS)
```

### Bathymetric colors

```python
from shiny_deckgl import depth_color

# Blue gradient for depth
for cell in cells:
    cell["color"] = depth_color(cell["depth"], max_depth=200, alpha=200)
```

### Data-driven styling

Use `@@=` expressions for dynamic styling:

```python
layer = scatterplot_layer(
    "points",
    data,
    # Size by value
    getRadius="@@=d.value * 10",

    # Color by category (ternary expression)
    getFillColor="@@=d.type === 'A' ? [255, 0, 0] : [0, 0, 255]",
)
```

---

## Interactivity

### Tooltips

```python
map_widget = MapWidget(
    "map",
    tooltip={
        "html": """
            <b>{name}</b><br/>
            Value: {value}<br/>
            Category: {category}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
            "fontSize": "12px",
        },
    },
)
```

### Click events

```python
@reactive.Effect
def handle_click():
    click = input[map_widget.click_input_id]()
    if click:
        print(f"Clicked: {click['object']}")
```

### Drawing tools

```python
# Enable drawing
await map_widget.enable_draw(session, modes=["draw_polygon", "draw_point"])

# Get drawn features
features = await map_widget.get_drawn_features(session)
```

### Camera control

```python
# Fly to location
await map_widget.fly_to(session, longitude=20.0, latitude=55.0, zoom=10)

# Fit to bounds
await map_widget.fit_bounds(session, [[18, 54], [22, 57]])
```

---

## Performance Optimization

### Use binary transport for large arrays

```python
from shiny_deckgl import encode_binary_attribute
import numpy as np

positions = np.array([[20.0, 55.0], [20.1, 55.1], ...], dtype=np.float32)

layer = scatterplot_layer(
    "points",
    {"length": len(positions)},
    getPosition=encode_binary_attribute(positions),
)
```

### Use aggregation layers

Instead of rendering 100,000 points individually, aggregate:

```python
# DON'T: 100k scatter points
layer = scatterplot_layer("points", huge_dataset)

# DO: Aggregate to hexagons
layer = hexagon_layer("hex", huge_dataset, radius=1000)
```

### Use partial updates

```python
# Update only changed properties
await map_widget.patch_layer(session, "my_layer", opacity=0.5)
```

### Limit visible layers

Toggle layers off when not needed:

```python
await map_widget.set_layer_visibility(session, {"heavy_layer": False})
```

---

## Complete Examples

### Marine Protected Areas Map

```python
from shiny import App, ui, reactive
from shiny_deckgl import (
    MapWidget, head_includes, geojson_layer, scatterplot_layer,
    CARTO_POSITRON, deck_legend_control,
)

map_widget = MapWidget(
    "mpa_map",
    view_state={"longitude": 20, "latitude": 56, "zoom": 5},
    style=CARTO_POSITRON,
    tooltip={"html": "<b>{name}</b><br/>Area: {area_km2} km²"},
)

app_ui = ui.page_fluid(
    head_includes(),
    ui.h2("Baltic Sea Marine Protected Areas"),
    map_widget.ui(height="600px"),
)

def server(input, output, session):
    @reactive.Effect
    async def init():
        layers = [
            geojson_layer(
                "mpas",
                MPA_GEOJSON,
                getFillColor=[0, 180, 120, 100],
                getLineColor=[0, 180, 120, 255],
                lineWidthMinPixels=2,
                pickable=True,
            ),
            scatterplot_layer(
                "ports",
                PORTS,
                getPosition="@@=d.position",
                getFillColor=[65, 182, 196],
                radiusMinPixels=5,
                pickable=True,
            ),
        ]

        await map_widget.update(session, layers)
        await map_widget.set_controls(session, [
            {"type": "navigation", "position": "top-right"},
            deck_legend_control(
                entries=[
                    {"label": "Protected Areas", "color": [0, 180, 120], "shape": "rect"},
                    {"label": "Ports", "color": [65, 182, 196], "shape": "circle"},
                ],
                position="bottom-right",
            ),
        ])

app = App(app_ui, server)
```

### Animated Ship Tracks

```python
from shiny import App, ui, reactive
from shiny_deckgl import (
    MapWidget, head_includes, trips_layer, trips_animation_ui, trips_animation_server,
)

map_widget = MapWidget("ships", view_state={...})

app_ui = ui.page_sidebar(
    ui.sidebar(
        trips_animation_ui("anim"),
    ),
    head_includes(),
    map_widget.ui(height="100%"),
)

def server(input, output, session):
    trips_animation_server("anim", map_widget, session)

    @reactive.Effect
    async def init():
        layers = [
            trips_layer(
                "ships",
                SHIP_TRACKS,
                getPath="@@=d.path",
                getTimestamps="@@=d.timestamps",
                getColor=[253, 128, 93],
                trailLength=300,
            ),
        ]
        await map_widget.update(session, layers)

app = App(app_ui, server)
```

---

## Getting Help

- **API Reference:** [docs/api_reference.md](api_reference.md)
- **Demo App:** Run `shiny_deckgl-demo` to explore all features
- **GitHub Issues:** [github.com/razinkele/shiny_deckgl/issues](https://github.com/razinkele/shiny_deckgl/issues)
- **deck.gl Documentation:** [deck.gl/docs](https://deck.gl/docs) (for layer properties)

---

*shiny_deckgl v1.6.1 — Built for marine science and GIS visualization*
