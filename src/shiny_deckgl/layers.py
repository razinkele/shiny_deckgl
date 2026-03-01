"""Deck.gl layer helpers — generic ``layer()`` + typed convenience wrappers."""

from __future__ import annotations

from typing import Any

from ._data_utils import _serialise_data


# ---------------------------------------------------------------------------
# Generic layer helper
# ---------------------------------------------------------------------------

def layer(type: str, id: str, data=None, *, extensions: list | None = None, **kwargs) -> dict:
    """Create an arbitrary deck.gl layer definition.

    Works for *any* deck.gl layer class (e.g. ``"HeatmapLayer"``,
    ``"PathLayer"``, ``"ColumnLayer"``).  The JS client resolves
    ``deck[type]`` dynamically.

    Parameters
    ----------
    type
        deck.gl layer class name (e.g. ``"HeatmapLayer"``).
    id
        Unique layer identifier.
    data
        Layer data – list, dict, URL string, DataFrame, or GeoDataFrame.
    extensions
        Optional list of deck.gl extension specs.  Each element can be:

        - A **string** — extension class name, instantiated with no args::

              extensions=["BrushingExtension", "ClipExtension"]

        - A **[name, options] pair** (list or tuple) — instantiated with
          the given options dict::

              extensions=[["DataFilterExtension", {"filterSize": 2}]]

        Mixed forms are allowed::

              extensions=["ClipExtension",
                          ["DataFilterExtension", {"filterSize": 2}]]
    **kwargs
        Any additional deck.gl properties.  ``visible=False`` hides the
        layer without removing it from the stack.
    """
    lyr: dict = {"type": type, "id": id}
    if data is not None:
        lyr["data"] = _serialise_data(data)
    if extensions:
        resolved: list = []
        for ext in extensions:
            if isinstance(ext, str):
                resolved.append(ext)
            elif isinstance(ext, (list, tuple)) and len(ext) == 2:
                resolved.append({"@@extClass": ext[0], "@@extOpts": ext[1]})
            else:
                raise ValueError(
                    f"Invalid extension spec: {ext!r}. "
                    "Expected a string or a [name, options] pair."
                )
        lyr["@@extensions"] = resolved
    lyr.update(kwargs)
    return lyr


# ---------------------------------------------------------------------------
# Typed layer helpers (convenience wrappers around layer())
# ---------------------------------------------------------------------------

def scatterplot_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ScatterplotLayer`` definition.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points, a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``radiusScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getFillColor": [200, 0, 80, 180],
        "radiusMinPixels": 5,
    }
    defaults.update(kwargs)
    return layer("ScatterplotLayer", id, data, **defaults)


def geojson_layer(id: str, data: dict | list, **kwargs) -> dict:
    """Create a deck.gl ``GeoJsonLayer`` definition.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        A GeoJSON ``FeatureCollection`` or ``Feature`` dict, a URL, or a GeoDataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``lineWidthMinPixels``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getFillColor": [0, 128, 255, 120],
        "getLineColor": [0, 128, 255],
        "lineWidthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("GeoJsonLayer", id, data, **defaults)


def tile_layer(id: str, data: str | list, **kwargs) -> dict:
    """Create a deck.gl ``TileLayer`` for XYZ or WMS raster tiles.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        A URL template.  For XYZ tiles use ``{z}/{x}/{y}`` placeholders.
        For WMS, use a ``{bbox-epsg-3857}`` or ``{bbox-epsg-4326}``
        placeholder in the ``BBOX`` parameter — the JS client automatically
        converts tile bounds to the appropriate projection.  Example::

            "https://ows.emodnet-bathymetry.eu/wms?"
            "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            "&FORMAT=image/png&TRANSPARENT=true"
            "&LAYERS=emodnet:mean_atlas_land"
            "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
            "&BBOX={bbox-epsg-3857}"
    """
    defaults: dict[str, Any] = {
        "minZoom": 0,
        "maxZoom": 19,
        "tileSize": 256,
        "renderSubLayers": "@@BitmapLayer",
    }
    defaults.update(kwargs)
    return layer("TileLayer", id, data, **defaults)


def bitmap_layer(id: str, image: str, bounds: list, **kwargs) -> dict:
    """Create a deck.gl ``BitmapLayer`` for a static image overlay.

    Parameters
    ----------
    id
        Unique layer identifier.
    image
        The URL of the image.
    bounds
        ``[left, bottom, right, top]`` in WGS 84.
    """
    return layer("BitmapLayer", id, **{"image": image, "bounds": bounds, **kwargs})


# ---------------------------------------------------------------------------
# Additional layer helpers (v0.7.0)
# ---------------------------------------------------------------------------

def arc_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ArcLayer`` for drawing arcs between two points.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``sourcePosition`` and ``targetPosition`` keys,
        a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getSourceColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getSourceColor": [0, 128, 200],
        "getTargetColor": [200, 0, 80],
        "getWidth": 2,
    }
    defaults.update(kwargs)
    return layer("ArcLayer", id, data, **defaults)


def icon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``IconLayer`` for rendering icons at locations.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts, a remote data URL,
        or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``iconAtlas``, ``iconMapping``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getSize": 24,
        "sizeScale": 1,
    }
    defaults.update(kwargs)
    return layer("IconLayer", id, data, **defaults)


def path_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``PathLayer`` for rendering polylines.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with a ``path`` key (array of coordinates),
        a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPath": "@@d.path",
        "getColor": [0, 128, 255],
        "getWidth": 3,
        "widthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("PathLayer", id, data, **defaults)


def line_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``LineLayer`` for straight lines between two points.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``sourcePosition`` and ``targetPosition`` keys.
    **kwargs
        Extra deck.gl properties (e.g. ``getColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getColor": [0, 0, 0, 128],
        "getWidth": 1,
    }
    defaults.update(kwargs)
    return layer("LineLayer", id, data, **defaults)


def text_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``TextLayer`` for rendering text labels.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with a ``text`` key, a remote data URL,
        or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``getText``, ``getSize``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getText": "@@d.text",
        "getSize": 16,
        "getColor": [0, 0, 0, 255],
        "getTextAnchor": "middle",
        "getAlignmentBaseline": "center",
    }
    defaults.update(kwargs)
    return layer("TextLayer", id, data, **defaults)


def column_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ColumnLayer`` for 3D columns.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``elevation`` key, coordinates, etc.
    **kwargs
        Extra deck.gl properties (e.g. ``radius``, ``extruded``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getElevation": "@@d.elevation",
        "getFillColor": [255, 140, 0],
        "radius": 100,
        "extruded": True,
    }
    defaults.update(kwargs)
    return layer("ColumnLayer", id, data, **defaults)


def polygon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``PolygonLayer`` for rendering filled polygons.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with a ``polygon`` key (array of coordinates).
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``extruded``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPolygon": "@@d.polygon",
        "getFillColor": [0, 128, 255, 80],
        "getLineColor": [0, 0, 0, 200],
        "getLineWidth": 1,
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("PolygonLayer", id, data, **defaults)


def heatmap_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``HeatmapLayer`` for density visualisation.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts, a remote data URL,
        or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``radiusPixels``, ``intensity``).
    """
    defaults: dict[str, Any] = {
        "getPosition": "@@d",
        "getWeight": 1,
        "radiusPixels": 30,
        "intensity": 1,
        "threshold": 0.05,
    }
    defaults.update(kwargs)
    return layer("HeatmapLayer", id, data, **defaults)


def hexagon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``HexagonLayer`` for hexagonal binning.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts.
    **kwargs
        Extra deck.gl properties (e.g. ``radius``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "radius": 1000,
        "elevationScale": 4,
        "extruded": True,
    }
    defaults.update(kwargs)
    return layer("HexagonLayer", id, data, **defaults)


def h3_hexagon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``H3HexagonLayer`` for H3 index-based hexagons.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``hex`` (H3 index) and ``color`` keys.
    **kwargs
        Extra deck.gl properties (e.g. ``getHexagon``, ``extruded``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getHexagon": "@@d.hex",
        "getFillColor": "@@d.color",
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("H3HexagonLayer", id, data, **defaults)


# ---------------------------------------------------------------------------
# Layer helpers (v0.9.0) — geo-layers & aggregation-layers
# ---------------------------------------------------------------------------


def trips_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``TripsLayer`` for animated vehicle/vessel tracks.

    The TripsLayer renders paths that animate over time.  Each feature
    must have a ``path`` (array of ``[lon, lat, timestamp]`` triplets)
    and optionally a set of timestamps.  The ``currentTime`` property
    drives the animation — use the widget's ``_animate`` flag together
    with a Shiny ``reactive.poll`` or `setInterval` to increment it.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``path`` key (array of [lon, lat, time]),
        a remote data URL, or a DataFrame.
    **kwargs
        Extra deck.gl properties (e.g. ``currentTime``, ``trailLength``,
        ``getColor``, ``widthMinPixels``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPath": "@@d.path",
        "getTimestamps": "@@d.timestamps",
        "getColor": [253, 128, 93],
        "widthMinPixels": 2,
        "trailLength": 200,
        "currentTime": 0,
    }
    defaults.update(kwargs)
    return layer("TripsLayer", id, data, **defaults)


def great_circle_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``GreatCircleLayer`` for geodesic arcs.

    Unlike ``ArcLayer`` which draws parabolic arcs, ``GreatCircleLayer``
    follows the shortest path on the sphere (geodesic), which is more
    accurate for long-distance routes.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``sourcePosition`` and ``targetPosition`` keys.
    **kwargs
        Extra deck.gl properties (e.g. ``getSourceColor``, ``getWidth``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getSourcePosition": "@@d.sourcePosition",
        "getTargetPosition": "@@d.targetPosition",
        "getSourceColor": [64, 255, 0],
        "getTargetColor": [0, 128, 200],
        "getWidth": 2,
    }
    defaults.update(kwargs)
    return layer("GreatCircleLayer", id, data, **defaults)


def contour_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ContourLayer`` for isoline/isoband generation.

    Generates isolines or isobands from point data using GPU-accelerated
    aggregation.  Great for density contours, bathymetric contours, etc.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts with position data.
    **kwargs
        Extra deck.gl properties (e.g. ``contours``, ``cellSize``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "getWeight": 1,
        "cellSize": 200,
        "contours": [
            {"threshold": 1, "color": [255, 0, 0], "strokeWidth": 2},
            {"threshold": 5, "color": [0, 255, 0], "strokeWidth": 3},
            {"threshold": [6, 1000], "color": [0, 0, 255, 128]},
        ],
    }
    defaults.update(kwargs)
    return layer("ContourLayer", id, data, **defaults)


def grid_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``GridLayer`` for rectangular grid binning.

    Points are aggregated into a grid of rectangular cells, similar to
    ``HexagonLayer`` but with square cells.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts.
    **kwargs
        Extra deck.gl properties (e.g. ``cellSize``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "getPosition": "@@d",
        "cellSize": 200,
        "elevationScale": 4,
        "extruded": True,
    }
    defaults.update(kwargs)
    return layer("GridLayer", id, data, **defaults)


def screen_grid_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ScreenGridLayer`` for screen-space grid binning.

    Unlike ``GridLayer`` which bins in world coordinates, this layer bins
    in screen pixels — the grid stays the same size regardless of zoom.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of ``[lon, lat]`` points or dicts.
    **kwargs
        Extra deck.gl properties (e.g. ``cellSizePixels``, ``colorRange``).
    """
    defaults: dict[str, Any] = {
        "getPosition": "@@d",
        "getWeight": 1,
        "cellSizePixels": 20,
        "colorRange": [
            [255, 255, 178, 25],
            [254, 217, 118, 85],
            [254, 178, 76, 127],
            [253, 141, 60, 170],
            [240, 59, 32, 212],
            [189, 0, 38, 255],
        ],
    }
    defaults.update(kwargs)
    return layer("ScreenGridLayer", id, data, **defaults)


def mvt_layer(id: str, data: str, **kwargs) -> dict:
    """Create a deck.gl ``MVTLayer`` (Mapbox Vector Tiles).

    Reads vector tile data from a Mapbox/MapTiler/PMTiles URL template.
    Faster than loading large GeoJSON for big datasets.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Tile URL template with ``{x}/{y}/{z}`` placeholders, e.g.
        ``"https://tiles.example.com/{z}/{x}/{y}.pbf"``.
    **kwargs
        Extra deck.gl properties (e.g. ``getFillColor``, ``getLineColor``,
        ``minZoom``, ``maxZoom``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "minZoom": 0,
        "maxZoom": 14,
        "getFillColor": [140, 170, 180],
        "getLineColor": [0, 0, 0, 60],
        "getLineWidth": 1,
        "lineWidthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("MVTLayer", id, data, **defaults)


def wms_layer(id: str, data: str, **kwargs) -> dict:
    """Create a deck.gl ``WMSLayer`` for WMS/WMTS services.

    This is deck.gl's first-class WMS layer (added in 9.x), as an
    alternative to the ``tile_layer()`` workaround with bbox placeholders.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        WMS service base URL (without query parameters), e.g.
        ``"https://ows.emodnet-bathymetry.eu/wms"``.
    **kwargs
        Extra properties: ``layers`` (required WMS LAYERS parameter),
        ``srs``, ``format``, ``transparent``, etc.
    """
    defaults: dict[str, Any] = {
        "layers": [],
        "srs": "EPSG:4326",
        "format": "image/png",
        "transparent": True,
    }
    defaults.update(kwargs)
    return layer("WMSLayer", id, data, **defaults)
