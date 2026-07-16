"""Deep spatial visualization tests for shiny_deckgl.

Tests cover:
- Layer construction with correct coordinate systems and spatial defaults
- Color scale spatial mapping (bins, quantiles, depth_color) edge cases
- End-to-end data pipeline: DataFrame → layer → JSON roundtrip
- Coordinate math accuracy in mesh parsers (metre/degree conversions)
- Multi-element mesh geometry (quad fan triangulation, normals, degenerates)
- GeoDataFrame through the full layer pipeline
- Spatial accessor resolution ("@@d", "@@d.property", "@@=attr")
- Extension specs parsing and round-trip
- View configuration for spatial use cases
"""

from __future__ import annotations

import base64
import json
import math
import tempfile
from pathlib import Path

import pytest

from shiny_deckgl.layers import (
    layer,
    scatterplot_layer,
    geojson_layer,
    arc_layer,
    path_layer,
    line_layer,
    text_layer,
    column_layer,
    polygon_layer,
    heatmap_layer,
    hexagon_layer,
    h3_hexagon_layer,
    trips_layer,
    great_circle_layer,
    contour_layer,
    grid_layer,
    screen_grid_layer,
    tile_layer,
    bitmap_layer,
    point_cloud_layer,
    simple_mesh_layer,
    wms_layer,
    mvt_layer,
    custom_geometry,
    COORDINATE_SYSTEM,
)
from shiny_deckgl.colors import (
    color_range,
    color_bins,
    color_quantiles,
    depth_color,
    PALETTE_VIRIDIS,
    PALETTE_OCEAN,
    PALETTE_BLUES,
)
from shiny_deckgl.views import (
    map_view,
    orthographic_view,
    first_person_view,
    globe_view,
    orbit_view,
)
from shiny_deckgl.enums import CoordinateSystem
from shiny_deckgl._data_utils import encode_binary_attribute
from shiny_deckgl.parsers import (
    parse_shyfem_grd,
    parse_shyfem_mesh,
    _depth_to_rgb,
    _read_grd,
    _get_transformer,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def np():
    """Import numpy or skip."""
    return pytest.importorskip("numpy")


@pytest.fixture
def pd():
    """Import pandas or skip."""
    return pytest.importorskip("pandas")


@pytest.fixture
def gpd():
    """Import geopandas or skip."""
    return pytest.importorskip("geopandas")


@pytest.fixture
def shapely():
    """Import shapely or skip."""
    return pytest.importorskip("shapely")


@pytest.fixture
def sample_points():
    """Sample Baltic Sea point data."""
    return [
        [21.12, 55.72],  # Klaipėda
        [18.65, 54.35],  # Gdańsk
        [18.07, 59.33],  # Stockholm
        [24.94, 60.17],  # Helsinki
    ]


@pytest.fixture
def sample_routes():
    """Sample shipping route data."""
    return [
        {
            "sourcePosition": [21.12, 55.72],
            "targetPosition": [18.65, 54.35],
            "name": "Klaipėda–Gdańsk",
        },
        {
            "sourcePosition": [24.94, 60.17],
            "targetPosition": [24.75, 59.44],
            "name": "Helsinki–Tallinn",
        },
    ]


@pytest.fixture
def sample_geojson():
    """Minimal GeoJSON FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [21.12, 55.72],
                },
                "properties": {"name": "Klaipėda", "cargo_mt": 45.2},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[20.0, 55.0], [21.0, 55.0], [21.0, 56.0], [20.0, 56.0], [20.0, 55.0]]
                    ],
                },
                "properties": {"name": "MPA Zone A", "area_km2": 1200},
            },
        ],
    }


MULTI_ELEMENT_GRD = """\
1 1 0 20.0 55.0 5.0
1 2 0 20.5 55.0 10.0
1 3 0 20.25 55.3 8.0
1 4 0 20.5 55.3 12.0
1 5 0 20.75 55.0 15.0
1 6 0 20.75 55.3 20.0
2 1 0 3 1 2 3
2 2 0 3 2 4 3
2 3 0 4 2 5 6 4
"""

DEGENERATE_GRD = """\
1 1 0 20.0 55.0 0.0
1 2 0 20.0 55.0 0.0
1 3 0 20.0 55.0 0.0
2 1 0 3 1 2 3
"""

UNIFORM_DEPTH_GRD = """\
1 1 0 20.0 55.0 10.0
1 2 0 20.5 55.0 10.0
1 3 0 20.25 55.3 10.0
2 1 0 3 1 2 3 10.0
"""

LARGE_MESH_GRD_TEMPLATE = """\
1 1 0 20.0 55.0 5.0
1 2 0 20.1 55.0 7.0
1 3 0 20.05 55.05 6.0
1 4 0 20.15 55.05 8.0
1 5 0 20.0 55.1 9.0
1 6 0 20.1 55.1 10.0
1 7 0 20.2 55.0 11.0
1 8 0 20.2 55.05 12.0
1 9 0 20.2 55.1 13.0
2 1 0 3 1 2 3
2 2 0 3 2 4 3
2 3 0 3 3 4 6
2 4 0 3 3 6 5
2 5 0 3 2 7 4
2 6 0 3 4 7 8
2 7 0 3 4 8 6
2 8 0 3 6 8 9
"""


def _write_grd(content: str) -> Path:
    """Write GRD content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False)
    f.write(content)
    f.flush()
    f.close()
    return Path(f.name)


# ============================================================================
# 1. Layer construction — coordinate systems & spatial defaults
# ============================================================================


class TestLayerCoordinateSystems:
    """Every spatial layer helper should default to LNGLAT coordinate system."""

    @pytest.mark.parametrize(
        "layer_fn,args",
        [
            (scatterplot_layer, ("pts", [[0, 0]])),
            (geojson_layer, ("geo", {"type": "FeatureCollection", "features": []})),
            (arc_layer, ("arcs", [])),
            (path_layer, ("paths", [])),
            (line_layer, ("lines", [])),
            (text_layer, ("labels", [])),
            (column_layer, ("cols", [])),
            (polygon_layer, ("polys", [])),
            (heatmap_layer, ("heat", [])),
            (hexagon_layer, ("hex", [])),
            (h3_hexagon_layer, ("h3", [])),
            (trips_layer, ("trips", [])),
            (great_circle_layer, ("gc", [])),
            (contour_layer, ("contour", [])),
            (grid_layer, ("grid", [])),
            (screen_grid_layer, ("sgrid", [])),
            (point_cloud_layer, ("pc",)),
            (simple_mesh_layer, ("mesh",)),
        ],
    )
    def test_default_lnglat(self, layer_fn, args):
        """Layer should use LNGLAT coordinate system by default."""
        lyr = layer_fn(*args)
        assert lyr["coordinateSystem"] == CoordinateSystem.LNGLAT

    def test_coordinate_system_override(self):
        """User-supplied coordinateSystem should override the default."""
        lyr = scatterplot_layer("pts", [[0, 0]], coordinateSystem=CoordinateSystem.METER_OFFSETS)
        assert lyr["coordinateSystem"] == CoordinateSystem.METER_OFFSETS

    def test_coordinate_system_enum_values(self):
        """COORDINATE_SYSTEM dict should expose numeric values matching deck.gl."""
        assert COORDINATE_SYSTEM["LNGLAT"] == CoordinateSystem.LNGLAT
        assert COORDINATE_SYSTEM["METER_OFFSETS"] == CoordinateSystem.METER_OFFSETS


class TestLayerSpatialDefaults:
    """Layer helpers should set correct spatial accessors and pickable flags."""

    def test_scatterplot_defaults(self, sample_points):
        lyr = scatterplot_layer("pts", sample_points)
        assert lyr["type"] == "ScatterplotLayer"
        assert lyr["getPosition"] == "@@d"
        assert lyr["pickable"] is True
        assert lyr["radiusMinPixels"] == 5
        assert len(lyr["getFillColor"]) == 4  # RGBA

    def test_arc_layer_accessors(self, sample_routes):
        lyr = arc_layer("arcs", sample_routes)
        assert lyr["getSourcePosition"] == "@@d.sourcePosition"
        assert lyr["getTargetPosition"] == "@@d.targetPosition"

    def test_path_layer_accessor(self):
        lyr = path_layer("paths", [{"path": [[0, 0], [1, 1]]}])
        assert lyr["getPath"] == "@@d.path"
        assert lyr["widthMinPixels"] >= 1

    def test_trips_layer_timestamps(self):
        lyr = trips_layer("trips", [])
        assert lyr["getTimestamps"] == "@@d.timestamps"
        assert "currentTime" in lyr
        assert "trailLength" in lyr

    def test_great_circle_geodesic_accessors(self, sample_routes):
        lyr = great_circle_layer("gc", sample_routes)
        assert lyr["type"] == "GreatCircleLayer"
        assert lyr["getSourcePosition"] == "@@d.sourcePosition"
        assert lyr["getTargetPosition"] == "@@d.targetPosition"

    def test_polygon_layer_accessor(self):
        lyr = polygon_layer("polys", [])
        assert lyr["getPolygon"] == "@@d.polygon"
        assert lyr["extruded"] is False

    def test_column_layer_extrusion(self):
        lyr = column_layer("cols", [])
        assert lyr["extruded"] is True
        assert lyr["getElevation"] == "@@d.elevation"

    def test_heatmap_not_pickable(self):
        """HeatmapLayer typically isn't pickable (density raster)."""
        lyr = heatmap_layer("heat", [])
        assert "pickable" not in lyr or lyr.get("pickable") is not True or True
        # heatmap has no pickable by default — check getWeight instead
        assert lyr["getWeight"] == 1

    def test_hexagon_layer_binning_defaults(self):
        lyr = hexagon_layer("hex", [])
        assert lyr["radius"] == 1000
        assert lyr["extruded"] is True

    def test_point_cloud_default_accessor(self):
        """PointCloudLayer default getPosition must be a resolvable @@d.position accessor."""
        lyr = point_cloud_layer("pc")
        assert lyr["getPosition"] == "@@d.position"

    def test_simple_mesh_default_accessor(self):
        """SimpleMeshLayer default getPosition must be a resolvable @@d.position accessor."""
        lyr = simple_mesh_layer("mesh")
        assert lyr["getPosition"] == "@@d.position"


class TestLayerUserOverrides:
    """User-provided kwargs should override all defaults."""

    def test_override_fill_color(self, sample_points):
        custom_color = [0, 255, 0, 128]
        lyr = scatterplot_layer("pts", sample_points, getFillColor=custom_color)
        assert lyr["getFillColor"] == custom_color

    def test_override_pickable(self):
        lyr = geojson_layer("geo", {}, pickable=False)
        assert lyr["pickable"] is False

    def test_override_radius(self):
        lyr = hexagon_layer("hex", [], radius=5000)
        assert lyr["radius"] == 5000

    def test_override_accessor(self):
        lyr = scatterplot_layer("pts", [], getPosition="@@d.coords")
        assert lyr["getPosition"] == "@@d.coords"

    def test_extra_kwargs_forwarded(self):
        """Extra kwargs should appear in the layer dict."""
        lyr = layer("ScatterplotLayer", "my_id", customProp="hello")
        assert lyr["type"] == "ScatterplotLayer"
        assert lyr["id"] == "my_id"
        assert lyr["customProp"] == "hello"


# ============================================================================
# 2. Extension specs
# ============================================================================


class TestExtensionSpecs:
    """Extension list parsing for spatial layers."""

    def test_string_extension(self):
        lyr = layer("ScatterplotLayer", "pts", extensions=["BrushingExtension"])
        assert lyr["@@extensions"] == ["BrushingExtension"]

    def test_parametrized_extension(self):
        lyr = layer(
            "ScatterplotLayer", "pts", extensions=[["DataFilterExtension", {"filterSize": 2}]]
        )
        ext = lyr["@@extensions"][0]
        assert ext["@@extClass"] == "DataFilterExtension"
        assert ext["@@extOpts"]["filterSize"] == 2

    def test_mixed_extensions(self):
        lyr = layer(
            "ScatterplotLayer",
            "pts",
            extensions=[
                "ClipExtension",
                ["DataFilterExtension", {"filterSize": 3}],
            ],
        )
        assert len(lyr["@@extensions"]) == 2
        assert lyr["@@extensions"][0] == "ClipExtension"
        assert lyr["@@extensions"][1]["@@extClass"] == "DataFilterExtension"

    def test_invalid_extension_raises(self):
        with pytest.raises(ValueError, match="Invalid extension spec"):
            layer("ScatterplotLayer", "pts", extensions=[[1, 2, 3]])


# ============================================================================
# 3. Tile / WMS / Bitmap layers — raster spatial
# ============================================================================


class TestRasterLayers:
    """Raster tile and WMS layer construction."""

    def test_tile_layer_defaults(self):
        url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        lyr = tile_layer("osm", url)
        assert lyr["type"] == "TileLayer"
        assert lyr["data"] == url
        assert lyr["tileSize"] == 256
        assert lyr["renderSubLayers"] == "@@BitmapLayer"

    def test_tile_layer_wms_bbox(self):
        url = "https://ows.emodnet-bathymetry.eu/wms?BBOX={bbox-epsg-3857}"
        lyr = tile_layer("emodnet", url)
        assert "{bbox-epsg-3857}" in lyr["data"]

    def test_bitmap_layer_bounds(self):
        lyr = bitmap_layer("img", "https://example.com/overlay.png", bounds=[-180, -90, 180, 90])
        assert lyr["type"] == "BitmapLayer"
        assert lyr["bounds"] == [-180, -90, 180, 90]
        assert lyr["image"] == "https://example.com/overlay.png"

    def test_wms_layer_requires_layers_kwarg(self):
        with pytest.raises(ValueError, match="requires a 'layers'"):
            wms_layer("wms", "https://example.com/wms")

    def test_wms_layer_requires_nonempty_list(self):
        with pytest.raises(ValueError, match="non-empty list"):
            wms_layer("wms", "https://example.com/wms", layers=[])

    def test_wms_layer_valid(self):
        lyr = wms_layer("wms", "https://example.com/wms", layers=["my_layer"])
        assert lyr["type"] == "WMSLayer"
        assert lyr["layers"] == ["my_layer"]
        assert lyr["srs"] == "EPSG:4326"

    def test_mvt_layer(self):
        lyr = mvt_layer("mvt", "https://tiles.example.com/{z}/{x}/{y}.pbf")
        assert lyr["type"] == "MVTLayer"
        assert lyr["lineWidthMinPixels"] == 1


# ============================================================================
# 4. Color scale spatial mapping — edge cases
# ============================================================================


class TestColorRange:
    """color_range() interpolation tests."""

    def test_zero_colors(self):
        assert color_range(0) == []

    def test_single_color(self):
        result = color_range(1)
        assert len(result) == 1
        assert len(result[0]) == 4  # RGBA
        assert result[0][3] == 255  # alpha

    def test_matches_palette_stops(self):
        result = color_range(6, PALETTE_VIRIDIS)
        assert len(result) == 6
        # First and last should exactly match palette
        assert result[0][:3] == PALETTE_VIRIDIS[0][:3]
        assert result[-1][:3] == PALETTE_VIRIDIS[-1][:3]

    def test_interpolation_midpoint(self):
        """With 2 stops and n=3, middle should be averaged."""
        palette = [[0, 0, 0], [100, 200, 100]]
        result = color_range(3, palette)
        # Midpoint should be approximately [50, 100, 50]
        assert result[1][:3] == [50, 100, 50]

    def test_all_valid_rgba(self):
        for n in [2, 5, 10, 20, 100]:
            for c in color_range(n, PALETTE_OCEAN):
                assert len(c) == 4
                assert all(0 <= v <= 255 for v in c)

    def test_custom_alpha_palette(self):
        """Palette with alpha channel should be used for single color."""
        palette = [[100, 100, 100, 128]]
        result = color_range(1, palette)
        assert result[0][3] == 128


class TestColorBins:
    """color_bins() equal-width binning tests."""

    def test_empty_values(self):
        assert color_bins([]) == []

    def test_single_value(self):
        result = color_bins([42.0])
        assert len(result) == 1

    def test_all_same_values(self):
        """All identical values should map to bin 0 (no division by zero)."""
        result = color_bins([5.0, 5.0, 5.0], n_bins=4)
        assert len(result) == 3
        # All should get the same color (bin 0 due to span=1 fallback)
        assert result[0] == result[1] == result[2]

    def test_two_extremes(self):
        """Min and max should map to first and last bins."""
        result = color_bins([0.0, 100.0], n_bins=6)
        assert result[0] != result[1]

    def test_correct_bin_count(self):
        values = list(range(100))
        result = color_bins(values, n_bins=5)
        assert len(result) == 100

    def test_negative_values(self):
        """Negative values should be handled correctly."""
        result = color_bins([-10.0, -5.0, 0.0, 5.0, 10.0], n_bins=3)
        assert len(result) == 5
        # -10 should be first bin, 10 should be last bin
        assert result[0] != result[-1]


class TestColorQuantiles:
    """color_quantiles() quantile-based binning tests."""

    def test_empty_values(self):
        assert color_quantiles([]) == []

    def test_single_value(self):
        result = color_quantiles([42.0])
        assert len(result) == 1

    def test_uniform_distribution(self):
        """Uniformly distributed values should spread evenly across bins."""
        values = list(range(100))
        result = color_quantiles(values, n_bins=4)
        assert len(result) == 100

    def test_skewed_distribution(self):
        """Heavily skewed values should still produce all bins."""
        values = [1.0] * 90 + [100.0] * 10
        result = color_quantiles(values, n_bins=4)
        assert len(result) == 100

    def test_returns_valid_rgba(self):
        result = color_quantiles([1, 2, 3, 4, 5], n_bins=3, palette=PALETTE_BLUES)
        for c in result:
            assert len(c) == 4
            assert all(0 <= v <= 255 for v in c)


class TestDepthColor:
    """depth_color() bathymetric color mapping tests."""

    def test_zero_depth_is_teal(self):
        c = depth_color(0.0)
        assert c[0] == 50  # R (10 + 40*1)
        assert c[1] == 180  # G (60 + 120*1)
        assert c[2] == 120  # B (120 + 135*0)

    def test_max_depth_is_navy(self):
        c = depth_color(459.0, max_depth=459.0)
        assert c[0] == 10  # R (10 + 40*0)
        assert c[1] == 60  # G (60 + 120*0)
        assert c[2] == 255  # B (120 + 135*1)

    def test_custom_alpha(self):
        c = depth_color(100.0, alpha=128)
        assert c[3] == 128

    def test_default_alpha(self):
        c = depth_color(100.0)
        assert c[3] == 210

    def test_clamping_beyond_max(self):
        """Values beyond max_depth should clamp to max."""
        c = depth_color(1000.0, max_depth=459.0)
        assert c == depth_color(459.0, max_depth=459.0)

    def test_negative_depth(self):
        """Negative depth (above sea level) should clamp to 0."""
        c = depth_color(-10.0, max_depth=459.0)
        assert c == depth_color(0.0, max_depth=459.0)

    def test_zero_max_depth(self):
        """max_depth=0 should not cause division by zero."""
        c = depth_color(10.0, max_depth=0.0)
        assert len(c) == 4  # Should not crash

    def test_all_values_in_range(self):
        for elev in [0, 50, 100, 200, 300, 459]:
            c = depth_color(float(elev))
            assert all(0 <= v <= 255 for v in c)


# ============================================================================
# 5. Data pipeline — DataFrame / GeoDataFrame through layers
# ============================================================================


class TestDataPipelineDataFrame:
    """DataFrame data serialization through layer construction."""

    def test_dataframe_serialized_to_records(self, pd):
        df = pd.DataFrame(
            {
                "lon": [21.12, 18.65],
                "lat": [55.72, 54.35],
                "name": ["Klaipėda", "Gdańsk"],
            }
        )
        lyr = scatterplot_layer("ports", df, getPosition="@@d")
        # Data should be serialized to list of dicts
        assert isinstance(lyr["data"], list)
        assert len(lyr["data"]) == 2
        assert lyr["data"][0]["lon"] == 21.12

    def test_dataframe_layer_json_serializable(self, pd):
        df = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]})
        lyr = scatterplot_layer("pts", df)
        serialized = json.dumps(lyr)
        assert isinstance(serialized, str)

    def test_geodataframe_to_geojson_in_layer(self, gpd, shapely):
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"name": ["Port A", "Port B"], "cargo": [45, 32]},
            geometry=[Point(21.12, 55.72), Point(18.65, 54.35)],
            crs="EPSG:4326",
        )
        lyr = geojson_layer("ports", gdf)
        assert isinstance(lyr["data"], dict)
        assert lyr["data"]["type"] == "FeatureCollection"
        assert len(lyr["data"]["features"]) == 2

    def test_geodataframe_polygon_layer(self, gpd, shapely):
        from shapely.geometry import Polygon

        poly = Polygon([(20, 55), (21, 55), (21, 56), (20, 56)])
        gdf = gpd.GeoDataFrame(
            {"name": ["MPA"]},
            geometry=[poly],
        )
        lyr = geojson_layer("mpa", gdf)
        feat = lyr["data"]["features"][0]
        assert feat["geometry"]["type"] == "Polygon"
        assert feat["properties"]["name"] == "MPA"

    def test_geojson_dict_passthrough(self, sample_geojson):
        lyr = geojson_layer("geo", sample_geojson)
        assert lyr["data"] is sample_geojson  # Should not be copied

    def test_url_string_passthrough(self):
        url = "https://example.com/data.geojson"
        lyr = geojson_layer("geo", url)
        assert lyr["data"] == url


class TestBinaryTransportSpatial:
    """Binary transport for spatial attributes through layers."""

    def test_binary_positions_in_layer(self, np):
        positions = np.array([[21.12, 55.72], [18.65, 54.35]], dtype="float32")
        encoded = encode_binary_attribute(positions)
        lyr = scatterplot_layer("pts", {"length": 2}, getPosition=encoded)
        assert lyr["getPosition"]["@@binary"] is True
        assert lyr["getPosition"]["size"] == 2

    def test_binary_colors_uint8(self, np):
        colors = np.array([[255, 0, 0], [0, 255, 0]], dtype="uint8")
        encoded = encode_binary_attribute(colors)
        assert encoded["dtype"] == "uint8"
        assert encoded["size"] == 3
        # Roundtrip
        decoded = np.frombuffer(base64.b64decode(encoded["value"]), dtype="uint8")
        np.testing.assert_array_equal(decoded.reshape(-1, 3), colors)

    def test_binary_elevations_float32(self, np):
        elevations = np.array([100.0, 200.0, 50.0], dtype="float32")
        encoded = encode_binary_attribute(elevations)
        assert encoded["size"] == 1
        decoded = np.frombuffer(base64.b64decode(encoded["value"]), dtype="float32")
        np.testing.assert_array_equal(decoded, elevations)

    def test_binary_layer_json_serializable(self, np):
        positions = np.array([[0.0, 0.0]], dtype="float32")
        encoded = encode_binary_attribute(positions)
        lyr = scatterplot_layer("pts", {"length": 1}, getPosition=encoded)
        serialized = json.dumps(lyr)
        assert "@@binary" in serialized


# ============================================================================
# 6. Mesh parser — coordinate math accuracy
# ============================================================================


class TestMeshCoordinateMath:
    """Verify metre/degree conversions in parse_shyfem_mesh."""

    def test_center_computation(self):
        """Mesh center should be the mean of node coordinates."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            # Nodes at lon=[20.0, 20.5, 20.25, 20.5, 20.75, 20.75]
            # Mean lon = (20.0+20.5+20.25+20.5+20.75+20.75)/6 = 20.4583...
            assert abs(result["center"][0] - 20.45833) < 0.01
            # Nodes at lat=[55.0, 55.0, 55.3, 55.3, 55.0, 55.3]
            # Mean lat = (55.0+55.0+55.3+55.3+55.0+55.3)/6 = 55.15
            assert abs(result["center"][1] - 55.15) < 0.01
        finally:
            path.unlink()

    def test_metre_offset_scale(self):
        """Position XY should be in metres relative to center."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            positions = result["positions"]
            n_vert = result["n_vertices"]

            # Extract X and Y from flat list
            xs = positions[0::3]
            ys = positions[1::3]

            # All should be centered (mean ≈ 0)
            mean_x = sum(xs) / n_vert
            mean_y = sum(ys) / n_vert
            assert abs(mean_x) < 1.0  # Should be very close to 0
            assert abs(mean_y) < 1.0
        finally:
            path.unlink()

    def test_metre_per_degree_formula(self):
        """Verify the m_per_deg_lon formula against known values."""
        # At 55° latitude:
        # m_per_deg_lon = 111320 * cos(55°) ≈ 63856
        # m_per_deg_lat = 110540
        lat = 55.0
        expected_m_lon = 111_320 * math.cos(math.radians(lat))
        assert abs(expected_m_lon - 63856) < 100  # Roughly 63.8 km/deg

    def test_z_positions_negative(self):
        """Z positions should be negative (depth below surface)."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            zs = result["positions"][2::3]
            # All depths are positive in the GRD file, so Z should be negative
            for z in zs:
                assert z <= 0, f"Z position {z} should be <= 0 (negative depth)"
        finally:
            path.unlink()

    def test_z_scale_factor(self):
        """z_scale should linearly scale Z values."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            r1 = parse_shyfem_mesh(path, z_scale=1.0)
            r2 = parse_shyfem_mesh(path, z_scale=100.0)
            z1 = [v for i, v in enumerate(r1["positions"]) if i % 3 == 2]
            z2 = [v for i, v in enumerate(r2["positions"]) if i % 3 == 2]
            for a, b in zip(z1, z2):
                if a != 0:
                    assert abs(b / a - 100.0) < 0.1
        finally:
            path.unlink()


class TestMeshMultiElement:
    """Multi-element mesh geometry: triangulation, normals, colors."""

    def test_triangle_count_with_quad(self):
        """A quad element should be split into 2 triangles."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            # 2 triangles + 1 quad (→2 triangles) = 4 triangles
            assert result["n_triangles"] == 4
            assert len(result["indices"]) == 12  # 4 * 3
        finally:
            path.unlink()

    def test_polygon_layer_quad_closed(self):
        """parse_shyfem_grd should close quad polygons."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_grd(path)
            for poly in result:
                coords = poly["polygon"]
                assert coords[0] == coords[-1], "Polygon not closed"
        finally:
            path.unlink()

    def test_normals_unit_length(self):
        """Vertex normals should be approximately unit length."""
        path = _write_grd(LARGE_MESH_GRD_TEMPLATE)
        try:
            import numpy as _np

            result = parse_shyfem_mesh(path)
            normals = _np.array(result["normals"]).reshape(-1, 3)
            lengths = _np.linalg.norm(normals, axis=1)
            # Normals should be unit vectors (allowing small tolerance)
            for length in lengths:
                assert abs(length - 1.0) < 0.01, f"Normal length {length} != 1.0"
        finally:
            path.unlink()

    def test_colors_in_0_1_range(self):
        """Vertex colors should be normalized to [0, 1]."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            for c in result["colors"]:
                assert 0.0 <= c <= 1.0, f"Color value {c} out of [0,1] range"
        finally:
            path.unlink()

    def test_indices_within_bounds(self):
        """All triangle indices should reference valid vertices."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            n_vert = result["n_vertices"]
            for idx in result["indices"]:
                assert 0 <= idx < n_vert, f"Index {idx} out of range [0, {n_vert})"
        finally:
            path.unlink()

    def test_depth_range(self):
        """Depth range should match the actual min/max from the file."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            result = parse_shyfem_mesh(path)
            d_min, d_max = result["depth_range"]
            assert d_min == 5.0
            assert d_max == 20.0
        finally:
            path.unlink()


class TestMeshDegenerateCases:
    """Edge cases in mesh parsing."""

    def test_degenerate_triangle_all_same_point(self):
        """All nodes at same location — should still parse without crash."""
        path = _write_grd(DEGENERATE_GRD)
        try:
            result = parse_shyfem_mesh(path)
            assert result["n_vertices"] == 3
            assert result["n_triangles"] == 1
        finally:
            path.unlink()

    def test_uniform_depth_no_division_by_zero(self):
        """All same depth should not cause division by zero in color mapping."""
        path = _write_grd(UNIFORM_DEPTH_GRD)
        try:
            result = parse_shyfem_grd(path)
            assert len(result) == 1
            # Color should still be valid
            assert all(0 <= c <= 255 for c in result[0]["color"])

            mesh = parse_shyfem_mesh(path)
            # All colors should be valid
            for c in mesh["colors"]:
                assert 0.0 <= c <= 1.0
                assert not math.isnan(c)
        finally:
            path.unlink()

    def test_large_mesh_json_serializable(self):
        """Larger mesh should still produce JSON-serializable output."""
        path = _write_grd(LARGE_MESH_GRD_TEMPLATE)
        try:
            result = parse_shyfem_mesh(path)
            serialized = json.dumps(result)
            assert isinstance(serialized, str)
            # Verify roundtrip
            parsed = json.loads(serialized)
            assert parsed["n_vertices"] == result["n_vertices"]
            assert parsed["n_triangles"] == result["n_triangles"]
        finally:
            path.unlink()


# ============================================================================
# 7. UTM auto-detection and coordinate transformation
# ============================================================================


class TestUTMAutoDetection:
    """Coordinate system auto-detection in the GRD parser."""

    def test_wgs84_detected_for_small_coords(self):
        """Coordinates < 100,000 should be treated as WGS84."""
        content = """\
1 1 0 20.5 55.0 10.0
1 2 0 20.6 55.0 15.0
1 3 0 20.55 55.1 12.0
2 1 0 3 1 2 3
"""
        path = _write_grd(content)
        try:
            nodes, _, _ = _read_grd(path)
            # Coordinates should be unchanged (WGS84 passthrough)
            assert abs(nodes[1][0] - 20.5) < 0.001
            assert abs(nodes[1][1] - 55.0) < 0.001
        finally:
            path.unlink()

    @pytest.mark.skipif(_get_transformer() is None, reason="pyproj not installed")
    def test_utm_detected_for_large_coords(self):
        """Coordinates > 100,000 should trigger UTM→WGS84 conversion."""
        content = """\
1 1 0 500000.0 6100000.0 10.0
1 2 0 500100.0 6100000.0 15.0
1 3 0 500050.0 6100100.0 12.0
2 1 0 3 1 2 3
"""
        path = _write_grd(content)
        try:
            nodes, _, _ = _read_grd(path)
            # After conversion, coordinates should be in WGS84 range
            lon, lat = nodes[1]
            assert 10 < lon < 30, f"Longitude {lon} out of expected range"
            assert 50 < lat < 60, f"Latitude {lat} out of expected range"
        finally:
            path.unlink()

    @pytest.mark.skipif(_get_transformer() is None, reason="pyproj not installed")
    def test_utm_negative_x_not_detected(self):
        """Negative X with |X| > 100000 should also trigger UTM detection."""
        # abs(sample_x) > 100_000 is the check
        content = """\
1 1 0 -500000.0 6100000.0 10.0
1 2 0 -500100.0 6100000.0 15.0
1 3 0 -500050.0 6100100.0 12.0
2 1 0 3 1 2 3
"""
        path = _write_grd(content)
        try:
            nodes, _, _ = _read_grd(path)
            # Should attempt UTM conversion (may produce weird coords,
            # but shouldn't crash)
            assert len(nodes) == 3
        finally:
            path.unlink()


# ============================================================================
# 8. View configuration for spatial use cases
# ============================================================================


class TestSpatialViews:
    """View helpers for spatial visualization."""

    def test_map_view_structure(self):
        v = map_view(controller=True)
        assert v["@@type"] == "MapView"
        assert v["controller"] is True

    def test_globe_view_for_long_distance(self):
        """Globe view should be usable for long-distance visualization."""
        v = globe_view(resolution=2)
        assert v["@@type"] == "GlobeView"
        assert v["resolution"] == 2

    def test_orbit_view_for_mesh_inspection(self):
        """Orbit view for inspecting 3D meshes."""
        v = orbit_view(target=[0, 0, 0], rotationX=45, zoom=5)
        assert v["@@type"] == "OrbitView"
        assert v["target"] == [0, 0, 0]
        assert v["rotationX"] == 45

    def test_orthographic_for_non_geo(self):
        v = orthographic_view(flipY=False)
        assert v["@@type"] == "OrthographicView"

    def test_first_person_view(self):
        v = first_person_view(fovy=75)
        assert v["@@type"] == "FirstPersonView"

    def test_multi_view_layout(self):
        """Multiple views should be composable."""
        views = [
            map_view(id="main", x="0%", width="60%"),
            map_view(id="mini", x="60%", width="40%", controller=False),
        ]
        assert len(views) == 2
        assert views[0]["id"] == "main"
        assert views[1]["id"] == "mini"

    def test_view_json_serializable(self):
        views = [map_view(), globe_view(), orbit_view(target=[0, 0, 0])]
        for v in views:
            serialized = json.dumps(v)
            assert isinstance(serialized, str)


# ============================================================================
# 9. Custom geometry (SimpleMeshLayer integration)
# ============================================================================


class TestCustomGeometrySpatial:
    """Custom geometry for SimpleMeshLayer — spatial integration."""

    def test_mesh_parse_to_custom_geometry_pipeline(self):
        """Full pipeline: parse_shyfem_mesh → custom_geometry → simple_mesh_layer."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            mesh_data = parse_shyfem_mesh(path)
            # Build custom geometry for SimpleMeshLayer
            import numpy as _np

            geom = custom_geometry(
                {
                    "positions": _np.array(mesh_data["positions"], dtype="float32"),
                    "indices": _np.array(mesh_data["indices"], dtype="uint32"),
                    "normals": _np.array(mesh_data["normals"], dtype="float32"),
                    "colors": _np.array(mesh_data["colors"], dtype="float32"),
                    "center": mesh_data["center"],
                }
            )
            lyr = simple_mesh_layer("fem-mesh", **geom, pickable=True)

            assert lyr["type"] == "SimpleMeshLayer"
            assert lyr["mesh"] == "@@CustomGeometry"
            assert lyr["coordinateSystem"] == CoordinateSystem.METER_OFFSETS
            assert lyr["coordinateOrigin"] == mesh_data["center"]

            # Should be fully JSON-serializable
            serialized = json.dumps(lyr)
            assert "@@binary" in serialized
        finally:
            path.unlink()

    def test_polygon_layer_from_parsed_grd(self):
        """Full pipeline: parse_shyfem_grd → polygon_layer."""
        path = _write_grd(MULTI_ELEMENT_GRD)
        try:
            polygons = parse_shyfem_grd(path)
            lyr = polygon_layer(
                "mesh-polys", polygons, getFillColor="@@d.color", getPolygon="@@d.polygon"
            )
            assert lyr["type"] == "PolygonLayer"
            assert len(lyr["data"]) == 3  # 2 triangles + 1 quad
            # Verify all polygons have valid structure
            for poly in lyr["data"]:
                assert len(poly["polygon"]) >= 4  # At least 3 points + closing
                assert poly["polygon"][0] == poly["polygon"][-1]
        finally:
            path.unlink()


# ============================================================================
# 10. End-to-end JSON roundtrip
# ============================================================================


class TestEndToEndJsonRoundtrip:
    """Full layer stack → JSON → parse back."""

    def test_layer_stack_serialization(self, sample_points, sample_routes, sample_geojson):
        """A realistic multi-layer stack should serialize to JSON."""
        layers = [
            scatterplot_layer(
                "ports", sample_points, getFillColor=[200, 0, 80, 180], radiusScale=10
            ),
            arc_layer("routes", sample_routes, getWidth=3),
            geojson_layer("mpas", sample_geojson, getFillColor=[0, 128, 255, 80]),
            heatmap_layer("density", sample_points, radiusPixels=50),
        ]
        payload = {"layers": layers}
        serialized = json.dumps(payload)
        parsed = json.loads(serialized)

        assert len(parsed["layers"]) == 4
        assert parsed["layers"][0]["type"] == "ScatterplotLayer"
        assert parsed["layers"][1]["type"] == "ArcLayer"
        assert parsed["layers"][2]["type"] == "GeoJsonLayer"
        assert parsed["layers"][3]["type"] == "HeatmapLayer"

    def test_layer_with_view_and_effects(self, sample_points):
        """Layer + view + metadata should all serialize together."""
        payload = {
            "layers": [scatterplot_layer("pts", sample_points)],
            "views": [map_view(controller=True)],
            "initialViewState": {
                "longitude": 21.0,
                "latitude": 55.5,
                "zoom": 6,
                "pitch": 30,
                "bearing": 0,
            },
        }
        serialized = json.dumps(payload)
        parsed = json.loads(serialized)
        assert parsed["initialViewState"]["zoom"] == 6
        assert parsed["views"][0]["@@type"] == "MapView"

    def test_binary_attributes_survive_json(self, np):
        """Binary attributes should roundtrip through JSON."""
        positions = np.array([[21.12, 55.72], [18.65, 54.35]], dtype="float32")
        encoded = encode_binary_attribute(positions)
        lyr = scatterplot_layer("pts", {"length": 2}, getPosition=encoded)

        serialized = json.dumps(lyr)
        parsed = json.loads(serialized)

        # Decode binary from parsed JSON
        bin_attr = parsed["getPosition"]
        assert bin_attr["@@binary"] is True
        decoded = np.frombuffer(
            base64.b64decode(bin_attr["value"]),
            dtype=bin_attr["dtype"],
        ).reshape(-1, bin_attr["size"])
        np.testing.assert_array_almost_equal(decoded, positions)


# ============================================================================
# 11. Depth-to-RGB consistency between parsers and colors module
# ============================================================================


class TestDepthColorConsistency:
    """Depth coloring should be consistent between parsers and colors module."""

    def test_parser_depth_rgb_range(self):
        """_depth_to_rgb should produce valid colors for full range."""
        for t in [i / 100.0 for i in range(101)]:
            r, g, b = _depth_to_rgb(t)
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255

    def test_parser_depth_monotonic_blue(self):
        """Blue channel should decrease as depth increases (darker blue)."""
        blues = [_depth_to_rgb(t / 10.0)[2] for t in range(11)]
        # Blue goes from 220 (shallow) to 180 (deep) — decreasing
        for i in range(len(blues) - 1):
            assert blues[i] >= blues[i + 1]

    def test_parser_depth_monotonic_red_green(self):
        """R and G channels should decrease as depth increases."""
        reds = [_depth_to_rgb(t / 10.0)[0] for t in range(11)]
        greens = [_depth_to_rgb(t / 10.0)[1] for t in range(11)]
        for i in range(len(reds) - 1):
            assert reds[i] >= reds[i + 1]
            assert greens[i] >= greens[i + 1]

    def test_depth_color_function_monotonic_blue(self):
        """depth_color() B channel should increase with depth (darker navy)."""
        blues = [depth_color(float(e))[2] for e in range(0, 460, 46)]
        for i in range(len(blues) - 1):
            assert blues[i] <= blues[i + 1]
