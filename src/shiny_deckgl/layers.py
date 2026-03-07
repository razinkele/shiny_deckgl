"""Deck.gl layer helpers — generic ``layer()`` + typed convenience wrappers.

Accessor String Conventions
---------------------------
Layer definitions use special ``@@`` prefixed strings that the deck.gl JSON
converter resolves at runtime:

- ``"@@d"`` — Direct data accessor, references the entire data item.
  Used when the full object is the value (e.g., ``getPosition: "@@d"``
  when data items are ``[lon, lat]`` arrays).

- ``"@@d.property"`` — Property accessor, references a specific property
  of the data item (e.g., ``getPosition: "@@d.position"`` when data items
  are dicts like ``{"position": [lon, lat], ...}``).

- ``"@@=property"`` — Binary accessor, used for binary-encoded attributes
  passed via ``encode_binary_attribute()``. The ``=`` signals that the
  attribute is a typed array, not JSON data.

- ``"@@ClassName"`` — Class reference, instantiates a deck.gl/luma.gl class
  (e.g., ``"@@BitmapLayer"`` for sub-layers, ``"@@CubeGeometry"`` for mesh
  geometry types).

See `deck.gl JSON configuration docs <https://deck.gl/docs/api-reference/json/conversion-reference>`_
for the full specification.
"""

from __future__ import annotations

from typing import Any

from ._data_utils import _serialise_data
from .enums import CoordinateSystem

__all__ = [
    "layer",
    # Core layers
    "scatterplot_layer",
    "geojson_layer",
    "arc_layer",
    "bitmap_layer",
    "column_layer",
    "grid_cell_layer",
    "icon_layer",
    "line_layer",
    "path_layer",
    "point_cloud_layer",
    "polygon_layer",
    "solid_polygon_layer",
    "text_layer",
    # Aggregation layers
    "contour_layer",
    "grid_layer",
    "heatmap_layer",
    "hexagon_layer",
    "screen_grid_layer",
    # Geo layers
    "a5_layer",
    "geohash_layer",
    "great_circle_layer",
    "h3_cluster_layer",
    "h3_hexagon_layer",
    "mvt_layer",
    "quadkey_layer",
    "s2_layer",
    "terrain_layer",
    "tile_layer",
    "tile_3d_layer",
    "trips_layer",
    "wms_layer",
    # Mesh layers
    "scenegraph_layer",
    "simple_mesh_layer",
    # Utilities
    "custom_geometry",
    "COORDINATE_SYSTEM",
]


# ---------------------------------------------------------------------------
# Generic layer helper
# ---------------------------------------------------------------------------

def layer(type: str, id: str, data=None, *, extensions: list[str | list] | None = None, **kwargs) -> dict:
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
    # Build from kwargs first, then forcibly set type/id so that
    # stray type= or id= in **kwargs can never silently clobber the
    # positional arguments.
    lyr: dict = {**kwargs, "type": type, "id": id}
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "getPosition": "@@d",
        "getFillColor": [200, 0, 80, 180],
        "radiusMinPixels": 5,
    }
    defaults.update(kwargs)
    return layer("ScatterplotLayer", id, data, **defaults)


def geojson_layer(id: str, data: list | dict, **kwargs) -> dict:
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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


def bitmap_layer(id: str, image: str, bounds: list[float], **kwargs) -> dict:
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
        "coordinateSystem": CoordinateSystem.LNGLAT,
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
    if "layers" not in kwargs:
        raise ValueError(
            "wms_layer() requires a 'layers' keyword argument "
            "specifying the WMS LAYERS to request, e.g. "
            "layers=['emodnet:mean_atlas_land']"
        )
    layers_val = kwargs["layers"]
    if not isinstance(layers_val, list) or len(layers_val) == 0:
        raise ValueError(
            "wms_layer() 'layers' must be a non-empty list of layer names, "
            f"got {type(layers_val).__name__}: {layers_val!r}"
        )
    defaults: dict[str, Any] = {
        "srs": "EPSG:4326",
        "format": "image/png",
        "transparent": True,
    }
    defaults.update(kwargs)
    return layer("WMSLayer", id, data, **defaults)


def point_cloud_layer(id: str, data: Any | None = None, **kwargs) -> dict:
    """Create a deck.gl ``PointCloudLayer``.

    Renders a cloud of 3-D points.  Each point is positioned at
    ``[longitude, latitude, altitude]`` and drawn as a circle in
    screen space.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Point-cloud data (list of dicts, URL, etc.).
    **kwargs
        Extra properties (``getPosition``, ``getColor``, ``getNormal``,
        ``pointSize``, ``sizeUnits``, etc.).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "pointSize": 2,
        "sizeUnits": "pixels",
        "getPosition": "@@=position",
        "getColor": [255, 140, 0],
        "getNormal": [0, 0, 1],
    }
    defaults.update(kwargs)
    return layer("PointCloudLayer", id, data, **defaults)


def simple_mesh_layer(id: str, data: Any | None = None, **kwargs) -> dict:
    """Create a deck.gl ``SimpleMeshLayer``.

    Renders a 3-D mesh (OBJ, PLY, or programmatic geometry) at each
    data point.  Useful for placing 3-D models on a map.

    Built-in mesh shorthands (resolved by the JS runtime):

    - ``"@@CubeGeometry"`` — luma.gl cube
    - ``"@@SphereGeometry"`` — luma.gl sphere
    - ``"@@CustomGeometry"`` — inline vertex arrays (use with
      :func:`custom_geometry`)

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Data source providing anchor positions.
    **kwargs
        Extra properties (``mesh`` URL or geometry, ``getPosition``,
        ``getColor``, ``getOrientation``, ``getScale``, ``sizeScale``,
        ``texture``, etc.).

    Example
    -------
    Render a parsed SHYFEM finite-element mesh::

        from shiny_deckgl.parsers import parse_shyfem_mesh
        mesh = parse_shyfem_mesh("mesh.grd")
        lyr = simple_mesh_layer("fem-mesh", **custom_geometry(mesh),
                                pickable=True)
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "getPosition": "@@=position",
        "getColor": [140, 170, 200],
        "sizeScale": 1,
    }
    defaults.update(kwargs)
    return layer("SimpleMeshLayer", id, data, **defaults)


def terrain_layer(id: str, data: Any | None = None, **kwargs) -> dict:
    """Create a deck.gl ``TerrainLayer``.

    Reconstructs mesh surfaces from height-map images (e.g. Mapzen
    Terrain Tiles).  The resulting 3-D terrain can be textured with a
    satellite or map-style raster.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Terrain-RGB tile URL template (``{x}/{y}/{z}`` placeholders),
        or ``None`` if ``elevationData`` is supplied via kwargs.
    **kwargs
        Extra properties:

        - ``elevationData`` — URL template for elevation tiles
        - ``texture`` — URL template for color/satellite tiles
        - ``elevationDecoder`` — dict describing RGB→elevation mapping
        - ``meshMaxError`` — max LOD simplification error in metres
        - ``bounds`` — ``[west, south, east, north]``
    """
    defaults: dict[str, Any] = {
        "meshMaxError": 4.0,
    }
    # Allow either `data` or `elevationData` for the height-map URL.
    # When elevationData is set (either from data or kwargs), pass
    # data=None to layer() to avoid sending the URL twice.
    if data is not None and "elevationData" not in kwargs:
        defaults["elevationData"] = data
    defaults.update(kwargs)
    return layer("TerrainLayer", id, None, **defaults)


# ---------------------------------------------------------------------------
# Additional Core layers (v1.6.0)
# ---------------------------------------------------------------------------


def grid_cell_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``GridCellLayer``.

    Renders grid cells as columns.  This is the primitive layer used by
    :func:`grid_layer` after aggregation, but can be used directly when
    you have pre-aggregated cell data.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of cell data with position and optional elevation/color.
    **kwargs
        Extra properties (``cellSize``, ``coverage``, ``extruded``,
        ``elevationScale``, ``getPosition``, ``getColor``, ``getElevation``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "cellSize": 1000,
        "coverage": 1,
        "extruded": True,
        "elevationScale": 1,
        "getPosition": "@@d.position",
        "getColor": [255, 140, 0, 180],
        "getElevation": "@@d.elevation",
    }
    defaults.update(kwargs)
    return layer("GridCellLayer", id, data, **defaults)


def solid_polygon_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``SolidPolygonLayer``.

    Renders filled and/or extruded polygons.  This is the primitive layer
    used internally by :func:`polygon_layer` and :func:`geojson_layer`,
    but can be used directly for more control.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of polygon data with ``polygon`` key containing coordinates.
    **kwargs
        Extra properties (``getPolygon``, ``getFillColor``, ``getLineColor``,
        ``getElevation``, ``extruded``, ``wireframe``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "filled": True,
        "extruded": False,
        "wireframe": False,
        "getPolygon": "@@d.polygon",
        "getFillColor": [140, 170, 180, 200],
        "getLineColor": [80, 80, 80],
        "getElevation": 0,
    }
    defaults.update(kwargs)
    return layer("SolidPolygonLayer", id, data, **defaults)


# ---------------------------------------------------------------------------
# Spatial index layers (v1.6.0) — Geo layers for various indexing systems
# ---------------------------------------------------------------------------


def a5_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``A5Layer`` for A5 pentagon cells.

    Renders filled polygons based on the A5 geospatial indexing system,
    which uses pentagons to tile the globe.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``pentagon`` (A5 index as BigInt or hex string).
    **kwargs
        Extra properties (``getPentagon``, ``getFillColor``, ``getElevation``,
        ``extruded``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "getPentagon": "@@d.pentagon",
        "getFillColor": [255, 140, 0, 180],
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("A5Layer", id, data, **defaults)


def geohash_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``GeohashLayer`` for Geohash cells.

    Renders filled polygons based on the Geohash geospatial indexing
    system.  Each cell is identified by a string like ``"9q8yy"``.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``geohash`` key containing geohash strings.
    **kwargs
        Extra properties (``getGeohash``, ``getFillColor``, ``getElevation``,
        ``extruded``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "getGeohash": "@@d.geohash",
        "getFillColor": [255, 140, 0, 180],
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("GeohashLayer", id, data, **defaults)


def h3_cluster_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``H3ClusterLayer`` for H3 hexagon clusters.

    Renders the outline of clusters of H3 hexagons as polygons.  Unlike
    :func:`h3_hexagon_layer` which renders individual hexagons, this
    layer groups multiple hexagons into unified cluster polygons.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``hexIds`` (array of H3 indices per cluster).
    **kwargs
        Extra properties (``getHexagons``, ``getFillColor``, ``getLineColor``,
        ``stroked``, ``lineWidthMinPixels``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "stroked": True,
        "filled": True,
        "getHexagons": "@@d.hexIds",
        "getFillColor": [255, 140, 0, 180],
        "getLineColor": [0, 0, 0],
        "lineWidthMinPixels": 1,
    }
    defaults.update(kwargs)
    return layer("H3ClusterLayer", id, data, **defaults)


def quadkey_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``QuadkeyLayer`` for Bing Maps quadkey tiles.

    Renders filled polygons based on the Quadkey geospatial indexing
    system used by Bing Maps.  Each cell is identified by a string of
    digits (0-3) like ``"0123"``.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``quadkey`` key containing quadkey strings.
    **kwargs
        Extra properties (``getQuadkey``, ``getFillColor``, ``getElevation``,
        ``extruded``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "getQuadkey": "@@d.quadkey",
        "getFillColor": [255, 140, 0, 180],
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("QuadkeyLayer", id, data, **defaults)


def s2_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``S2Layer`` for Google S2 cells.

    Renders filled polygons based on the S2 geospatial indexing system
    developed by Google.  Each cell is identified by a token (hex string
    or Hilbert quad key).

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Array of dicts with ``token`` key containing S2 cell tokens.
    **kwargs
        Extra properties (``getS2Token``, ``getFillColor``, ``getElevation``,
        ``extruded``, ``elevationScale``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "getS2Token": "@@d.token",
        "getFillColor": [255, 140, 0, 180],
        "extruded": False,
    }
    defaults.update(kwargs)
    return layer("S2Layer", id, data, **defaults)


def tile_3d_layer(id: str, data: str, **kwargs) -> dict:
    """Create a deck.gl ``Tile3DLayer`` for 3D Tiles / I3S data.

    Renders 3D tilesets in the OGC 3D Tiles specification (used by
    Cesium) or Esri I3S format.  Supports point clouds, batched 3D
    models, and instanced models.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        URL to a 3D Tiles tileset.json or I3S layer endpoint.
    **kwargs
        Extra properties (``pointSize``, ``opacity``, ``getPointColor``,
        ``onTilesetLoad``, ``onTileLoad``, ``loadOptions``).
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "pointSize": 1.0,
        "opacity": 1.0,
    }
    defaults.update(kwargs)
    return layer("Tile3DLayer", id, data, **defaults)


# ---------------------------------------------------------------------------
# Additional Mesh layers (v1.6.0)
# ---------------------------------------------------------------------------


def scenegraph_layer(id: str, data: list | dict, **kwargs) -> dict:
    """Create a deck.gl ``ScenegraphLayer`` for glTF 3D models.

    Renders 3D models in the glTF format at each data point.  Supports
    PBR materials, animations, and complex scene hierarchies.

    Parameters
    ----------
    id
        Unique layer identifier.
    data
        Data source providing anchor positions for model instances.
    **kwargs
        Extra properties:

        - ``scenegraph`` — URL to a glTF/GLB file
        - ``getPosition`` — position accessor (default: ``"@@d.position"``)
        - ``getOrientation`` — ``[pitch, yaw, roll]`` in degrees
        - ``getScale`` — scale factors ``[x, y, z]``
        - ``sizeScale`` — global size multiplier
        - ``_animations`` — animation playback config
        - ``_lighting`` — ``"flat"`` or ``"pbr"``
    """
    defaults: dict[str, Any] = {
        "pickable": True,
        "coordinateSystem": CoordinateSystem.LNGLAT,
        "sizeScale": 1,
        "getPosition": "@@d.position",
        "getOrientation": [0, 0, 0],
        "getScale": [1, 1, 1],
        "getColor": [255, 255, 255, 255],
        "_lighting": "pbr",
    }
    defaults.update(kwargs)
    return layer("ScenegraphLayer", id, data, **defaults)


# ---------------------------------------------------------------------------
# Coordinate system constants (imported from enums for single source of truth)
# ---------------------------------------------------------------------------

# Backwards-compatible alias: COORDINATE_SYSTEM.LNGLAT etc.
# The enum values work the same way as the old class attributes.
COORDINATE_SYSTEM = CoordinateSystem


# ---------------------------------------------------------------------------
# Custom mesh geometry helper
# ---------------------------------------------------------------------------

def custom_geometry(
    mesh_data: dict,
    *,
    position: list[float] | None = None,
) -> dict:
    """Build SimpleMeshLayer kwargs from parsed mesh geometry.

    This helper converts the output of
    :func:`~shiny_deckgl.parsers.parse_shyfem_mesh` (or any dict with
    ``positions``, ``normals``, ``colors``, ``indices``, ``center``)
    into the keyword arguments expected by :func:`simple_mesh_layer`.

    The JS runtime detects the ``"@@CustomGeometry"`` mesh marker and
    constructs a ``luma.Geometry`` from the inline vertex arrays.

    Parameters
    ----------
    mesh_data
        Dict with keys ``positions``, ``normals``, ``colors``,
        ``indices``, and ``center`` (as returned by
        :func:`~shiny_deckgl.parsers.parse_shyfem_mesh`).
    position
        Override the coordinate origin ``[lon, lat]``.  Defaults to
        ``mesh_data["center"]``.  The single data instance is placed at
        ``[0, 0, 0]`` metres offset from this origin.

    Returns
    -------
    dict
        Keyword arguments for :func:`simple_mesh_layer`: ``data``,
        ``mesh``, ``_meshPositions``, ``_meshNormals``, ``_meshColors``,
        ``_meshIndices``, ``coordinateSystem``, ``coordinateOrigin``,
        ``sizeScale``, ``getPosition``, ``getColor``.

    Example
    -------
    >>> from shiny_deckgl.parsers import parse_shyfem_mesh
    >>> from shiny_deckgl import simple_mesh_layer, custom_geometry
    >>> mesh = parse_shyfem_mesh("mesh.grd")
    >>> lyr = simple_mesh_layer("my-mesh", **custom_geometry(mesh))
    """
    for key in ("positions", "indices"):
        if key not in mesh_data:
            raise ValueError(f"mesh_data must contain '{key}'")

    ctr = mesh_data.get("center", [0, 0])
    origin = position if position is not None else [ctr[0], ctr[1]]

    return {
        # Single instance at the origin (0 m offset)
        "data": [{"position": [0, 0, 0], "layerType": "Custom Mesh"}],
        "getPosition": "@@=d.position",
        "getColor": [255, 255, 255, 255],
        "mesh": "@@CustomGeometry",
        "_meshPositions": mesh_data["positions"],
        "_meshNormals": mesh_data.get("normals", []),
        "_meshColors": mesh_data.get("colors", []),
        "_meshIndices": mesh_data["indices"],
        "sizeScale": 1,
        "coordinateSystem": COORDINATE_SYSTEM.METER_OFFSETS,
        "coordinateOrigin": origin,
    }
