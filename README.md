# shiny_deckgl

## Shiny for Python ➔ deck.gl bridge (Java-free)

A lightweight library for integrating [deck.gl](https://deck.gl/) (v9.1.4) and
[MapLibre GL JS](https://maplibre.org/) (v3.6.2) into
[Shiny for Python](https://shiny.posit.co/py/) applications.
Built for marine science and GIS visualization — WMS layers, EMODnet,
HELCOM, food web modelling — the package handles CDN asset injection, layer
construction, and bi-directional messaging between the Python server and the
browser, all without Java dependencies.

## Features

| Capability | Details |
| --- | --- |
| **Reusable `MapWidget`** | Drop-in widget with configurable initial view state, auto-render on connect, and `update()` to push new layers at any time. |
| **Layer helpers** | `scatterplot_layer()`, `geojson_layer()`, `tile_layer()`, `bitmap_layer()` — typed factory functions with sensible defaults and `**kwargs` pass-through. |
| **Generic `layer()`** | Any deck.gl layer class (HeatmapLayer, PathLayer, …) via `layer("HeatmapLayer", ...)`; the JS client resolves `deck[type]` dynamically. |
| **WMS / TileLayer** | First-class WMS support via `tile_layer()` — render EMODnet, GEBCO, or any `{bbox-epsg-3857}` service. |
| **Click & hover events** | Read click/hover results in Python via `input[widget.click_input_id]()` / `input[widget.hover_input_id]()`. Raster layers automatically excluded. |
| **Tooltips** | Configure `tooltip={"html": "<b>{name}</b>"}` on `MapWidget` for automatic hover tooltips with template interpolation. |
| **Viewport read-back** | `input[widget.view_state_input_id]()` gives lon/lat/zoom/pitch/bearing after every camera move. |
| **Basemap styles** | `CARTO_POSITRON`, `CARTO_DARK`, `CARTO_VOYAGER`, `OSM_LIBERTY` — or any MapLibre/Mapbox style URL. |
| **Mapbox API key** | `MapWidget(..., mapbox_api_key="pk.xxx")` to use `mapbox://` style URLs with automatic token injection. |
| **Color scales** | `color_range()`, `color_bins()`, `color_quantiles()` with 5 built-in palettes (`PALETTE_VIRIDIS`, `PALETTE_PLASMA`, `PALETTE_OCEAN`, `PALETTE_THERMAL`, `PALETTE_CHLOROPHYLL`). |
| **Layer visibility** | `set_layer_visibility(session, {"layer1": False})` toggles layers without resending data. |
| **Draggable markers** | `add_drag_marker(session)` places a marker the user can reposition; result in `input[widget.drag_input_id]()`. |
| **DataFrame support** | Pass pandas DataFrames or GeoDataFrames directly as layer data — auto-converted to records / GeoJSON. |
| **Extensions** | `layer(..., extensions=["DataFilterExtension"])` — resolved to `new deck.<Name>()` on the client. |
| **Binary transport** | `encode_binary_attribute(np_array)` — base64-encodes numpy arrays for high-performance typed-array attributes. |
| **Lighting & effects** | Pass `effects=[{"type": "LightingEffect", ...}]` to `update()` for ambient/point/directional lighting. |
| **Multiple views** | `map_view()`, `orthographic_view()`, `first_person_view()` helpers for multi-view layouts. |
| **HTML export** | `widget.to_html(layers, path="map.html")` — standalone HTML file viewable in any browser. |
| **JSON spec** | `to_json()` / `from_json()` for serialising and restoring map configurations. |
| **`@@` accessor convention** | Python strings like `"@@d"` or `"@@d.position"` are resolved to JS arrow functions on the client. |
| **CDN-pinned assets** | deck.gl 9.1.4, MapLibre GL 3.6.2 — deterministic builds. |
| **Conda recipe** | Bundled `conda.recipe/meta.yaml` for micromamba / conda-build. |

## Environment & Prerequisites

This project targets the shared `shiny` micromamba environment.
**Do not create local virtual environments.**

- **Python:** `C:\Users\arturas.baziukas\micromamba\envs\shiny\python.exe`
- **Activate:** `micromamba activate shiny`

## Installation

```bash
micromamba activate shiny
pip install -e .          # editable install (local package, not on conda-forge)
```

For binary transport support (numpy):

```bash
pip install -e ".[binary]"
```

Or build the conda package:

```bash
micromamba build conda.recipe/
micromamba install -n shiny shiny_deckgl --use-local
```

## Quick Start

```bash
micromamba run -n shiny shiny_deckgl-demo
```

This launches a demo app centred on the Baltic Sea with scatter points, an
EMODnet WMS toggle, click-to-inspect, hover info, drag markers, and HTML export.

## Usage in your own apps

```python
from shiny import App, ui, reactive, Session, render
from shiny_deckgl import MapWidget, scatterplot_layer, head_includes, CARTO_DARK

map_widget = MapWidget(
    "mymap",
    view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 8},
    tooltip={"html": "<b>Point</b><br/>lon: {0}, lat: {1}"},
    style=CARTO_DARK,
)

app_ui = ui.page_fluid(
    head_includes(),
    map_widget.ui(height="80vh"),
    ui.output_text_verbatim("click_info"),
)

def server(input, output, session: Session):
    @reactive.Effect
    async def _push_layers():
        layers = [scatterplot_layer("pts", [[21.12, 55.70], [21.15, 55.72]])]
        await map_widget.update(session, layers)

    @render.text
    def click_info():
        val = input[map_widget.click_input_id]()
        return str(val) if val else "Click a point…"

my_app = App(app_ui, server)
```

```bash
micromamba run -n shiny shiny run my_app.py
```

### Using WMS tile layers

```python
from shiny_deckgl import tile_layer

wms_url = (
    "https://ows.emodnet-bathymetry.eu/wms?"
    "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
    "&FORMAT=image/png&TRANSPARENT=true"
    "&LAYERS=emodnet:mean_atlas_land"
    "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
    "&BBOX={bbox-epsg-3857}"
)
layers.append(tile_layer("emodnet-bathy", wms_url))
```

### Color scales

```python
from shiny_deckgl import color_bins, PALETTE_OCEAN

depths = [10.5, 50.2, 120.0, 300.7, 15.3]
colors = color_bins(depths, n_bins=4, palette=PALETTE_OCEAN)
# colors[i] is [R, G, B, 255] for each depth value
```

### HTML export

```python
layers = [scatterplot_layer("pts", [[21.12, 55.70]])]
map_widget.to_html(layers, path="my_map.html", title="Exported Map")
```

## Codebase Structure

| File | Purpose |
| --- | --- |
| `src/shiny_deckgl/components.py` | `MapWidget` class, layer helpers, color utilities, binary transport, view helpers. |
| `src/shiny_deckgl/app.py` | Demo `app()` factory — sidebar UI, WMS, visibility toggle, drag markers, HTML export. |
| `src/shiny_deckgl/ui.py` | `head_includes()` — injects pinned CDN scripts and local JS/CSS. |
| `src/shiny_deckgl/cli.py` | `shiny_deckgl-demo` CLI entry point with Baltic Sea sample data. |
| `src/shiny_deckgl/resources/deckgl-init.js` | Frontend: MapLibre init, deck.gl overlay, message handlers, accessor/extension/binary resolution. |
| `src/shiny_deckgl/resources/styles.css` | Minimal layout + tooltip styles for `.deckgl-map` containers. |
| `conda.recipe/meta.yaml` | Conda build recipe (version synced with `_version.py`). |
| `tests/test_basic.py` | 95+ unit tests covering all features. |

## Running Tests

```bash
micromamba run -n shiny pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
