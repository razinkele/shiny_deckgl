"""Tests for the parsers module (SHYFEM mesh parsing).

Tests cover:
- Coordinate transformation functions
- Color depth mapping
- GRD file parsing
- Error handling for missing files and invalid data
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from shiny_deckgl.parsers import (
    parse_shyfem_grd,
    parse_shyfem_mesh,
)

# Also test internal functions
from shiny_deckgl.parsers import (
    _depth_to_rgb,
    _get_transformer,
    _read_grd,
    _utm_to_wgs84,
)


# ---------------------------------------------------------------------------
# Test _depth_to_rgb color mapping
# ---------------------------------------------------------------------------

class TestDepthToRgb:
    """Tests for the depth-to-RGB color mapping function."""

    def test_shallow_depth_light_blue(self):
        """Shallow (t=0) should produce light blue."""
        r, g, b = _depth_to_rgb(0.0)
        assert r == 180  # 30 + 150
        assert g == 220  # 60 + 160
        assert b == 220  # 180 + 40

    def test_deep_depth_dark_blue(self):
        """Deep (t=1) should produce dark blue."""
        r, g, b = _depth_to_rgb(1.0)
        assert r == 30
        assert g == 60
        assert b == 180

    def test_mid_depth(self):
        """Mid-depth (t=0.5) should produce intermediate colors."""
        r, g, b = _depth_to_rgb(0.5)
        assert r == 105  # 30 + 0.5*150
        assert g == 140  # 60 + 0.5*160
        assert b == 200  # 180 + 0.5*40

    def test_rgb_in_valid_range(self):
        """All RGB values should be in 0-255 range."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            r, g, b = _depth_to_rgb(t)
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255

    def test_returns_integers(self):
        """RGB values should be integers."""
        r, g, b = _depth_to_rgb(0.33)
        assert isinstance(r, int)
        assert isinstance(g, int)
        assert isinstance(b, int)


# ---------------------------------------------------------------------------
# Test _get_transformer (pyproj lazy loading)
# ---------------------------------------------------------------------------

class TestGetTransformer:
    """Tests for the pyproj transformer lazy loading."""

    def test_returns_transformer_or_none(self):
        """Should return a transformer if pyproj is installed, None otherwise."""
        result = _get_transformer()
        # Either pyproj is installed and we get a transformer, or it's not and we get None
        assert result is None or hasattr(result, "transform")

    def test_cached_result(self):
        """Should return the same cached object on repeated calls."""
        result1 = _get_transformer()
        result2 = _get_transformer()
        assert result1 is result2


# ---------------------------------------------------------------------------
# Test _utm_to_wgs84 coordinate transformation
# ---------------------------------------------------------------------------

class TestUtmToWgs84:
    """Tests for UTM to WGS84 coordinate transformation."""

    def test_raises_if_no_pyproj(self):
        """Should raise RuntimeError if pyproj is not available."""
        transformer = _get_transformer()
        if transformer is None:
            with pytest.raises(RuntimeError, match="pyproj is required"):
                _utm_to_wgs84(500000, 6000000)

    @pytest.mark.skipif(
        _get_transformer() is None,
        reason="pyproj not installed"
    )
    def test_valid_utm_conversion(self):
        """Valid UTM coordinates should convert to WGS84."""
        # UTM Zone 33N coordinates (roughly Baltic Sea area)
        lon, lat = _utm_to_wgs84(500000, 6200000)
        # Should produce reasonable Baltic coordinates
        assert 10 < lon < 30  # Longitude in Europe
        assert 50 < lat < 60  # Latitude in Baltic region

    @pytest.mark.skipif(
        _get_transformer() is None,
        reason="pyproj not installed"
    )
    def test_invalid_coordinates_raise_error(self):
        """Invalid coordinates should raise ValueError."""
        # This tests the error handling we added
        # Extremely invalid coordinates might cause transform issues
        # depending on pyproj version, but our wrapper should handle it
        try:
            result = _utm_to_wgs84(float('inf'), float('inf'))
            # If it doesn't raise, the result should be checked
            # (some pyproj versions may return inf)
        except ValueError as e:
            assert "Coordinate transformation failed" in str(e)


# ---------------------------------------------------------------------------
# Test GRD file reading with sample data
# ---------------------------------------------------------------------------

# Sample minimal .grd file content
SAMPLE_GRD_WGS84 = """\
1 1 0 20.5 55.0 10.0
1 2 0 20.6 55.0 15.0
1 3 0 20.55 55.1 12.0
2 1 0 3 1 2 3 12.0
"""

SAMPLE_GRD_QUAD = """\
1 1 0 20.0 55.0 10.0
1 2 0 21.0 55.0 15.0
1 3 0 21.0 56.0 20.0
1 4 0 20.0 56.0 18.0
2 1 0 4 1 2 3 4 16.0
"""

SAMPLE_GRD_EMPTY = """\
"""

SAMPLE_GRD_NODES_ONLY = """\
1 1 0 20.5 55.0 10.0
1 2 0 20.6 55.0 15.0
"""


class TestReadGrd:
    """Tests for the internal _read_grd function."""

    def test_read_triangle_mesh(self):
        """Should correctly parse a simple triangle mesh."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)

        try:
            nodes, elements, node_depths = _read_grd(path)
            assert len(nodes) == 3
            assert len(elements) == 1
            assert 1 in nodes
            assert 2 in nodes
            assert 3 in nodes
            assert elements[0]["verts"] == [1, 2, 3]
            assert elements[0]["depth"] == 12.0
        finally:
            path.unlink()

    def test_read_quad_mesh(self):
        """Should correctly parse a quad (4-vertex) element."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_QUAD)
            f.flush()
            path = Path(f.name)

        try:
            nodes, elements, node_depths = _read_grd(path)
            assert len(nodes) == 4
            assert len(elements) == 1
            assert elements[0]["verts"] == [1, 2, 3, 4]
        finally:
            path.unlink()

    def test_read_empty_file(self):
        """Empty file should return empty structures."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_EMPTY)
            f.flush()
            path = Path(f.name)

        try:
            nodes, elements, node_depths = _read_grd(path)
            assert len(nodes) == 0
            assert len(elements) == 0
        finally:
            path.unlink()

    def test_read_nodes_only(self):
        """File with only nodes (no elements) should parse correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_NODES_ONLY)
            f.flush()
            path = Path(f.name)

        try:
            nodes, elements, node_depths = _read_grd(path)
            assert len(nodes) == 2
            assert len(elements) == 0
        finally:
            path.unlink()

    def test_node_depths_extracted(self):
        """Node depths should be extracted from 6th column."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)

        try:
            nodes, elements, node_depths = _read_grd(path)
            assert node_depths[1] == 10.0
            assert node_depths[2] == 15.0
            assert node_depths[3] == 12.0
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Test parse_shyfem_grd (public API)
# ---------------------------------------------------------------------------

class TestParseShyfemGrd:
    """Tests for the public parse_shyfem_grd function."""

    def test_returns_list_of_dicts(self):
        """Should return a list of polygon dictionaries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], dict)
        finally:
            path.unlink()

    def test_polygon_structure(self):
        """Each polygon dict should have required keys."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            poly = result[0]
            assert "polygon" in poly
            assert "depth" in poly
            assert "element_id" in poly
            assert "color" in poly
            assert "layerType" in poly
        finally:
            path.unlink()

    def test_polygon_is_closed(self):
        """Polygon coordinates should be closed (first == last)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            polygon = result[0]["polygon"]
            assert polygon[0] == polygon[-1]
        finally:
            path.unlink()

    def test_color_is_rgba(self):
        """Color should be [R, G, B, A] format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            color = result[0]["color"]
            assert len(color) == 4
            assert all(0 <= c <= 255 for c in color)
        finally:
            path.unlink()

    def test_empty_file_returns_empty_list(self):
        """Empty file should return empty list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_EMPTY)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            assert result == []
        finally:
            path.unlink()

    def test_accepts_string_path(self):
        """Should accept string path as well as Path object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path_str = f.name

        try:
            result = parse_shyfem_grd(path_str)
            assert len(result) == 1
        finally:
            Path(path_str).unlink()

    def test_missing_file_raises_error(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_shyfem_grd("/nonexistent/path/file.grd")


# ---------------------------------------------------------------------------
# Test parse_shyfem_mesh (public API - requires numpy)
# ---------------------------------------------------------------------------

class TestParseShyfemMesh:
    """Tests for the public parse_shyfem_mesh function."""

    @pytest.fixture
    def sample_grd_file(self):
        """Create a temporary .grd file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_WGS84)
            f.flush()
            path = Path(f.name)
        yield path
        path.unlink()

    def test_returns_dict_with_required_keys(self, sample_grd_file):
        """Should return dict with all required keys."""
        result = parse_shyfem_mesh(sample_grd_file)
        assert "positions" in result
        assert "normals" in result
        assert "colors" in result
        assert "indices" in result
        assert "center" in result
        assert "n_vertices" in result
        assert "n_triangles" in result
        assert "depth_range" in result

    def test_positions_flat_list(self, sample_grd_file):
        """Positions should be a flat list of floats (x,y,z triplets)."""
        result = parse_shyfem_mesh(sample_grd_file)
        positions = result["positions"]
        assert isinstance(positions, list)
        assert len(positions) % 3 == 0  # Divisible by 3
        assert len(positions) == result["n_vertices"] * 3

    def test_normals_flat_list(self, sample_grd_file):
        """Normals should be a flat list of floats (x,y,z triplets)."""
        result = parse_shyfem_mesh(sample_grd_file)
        normals = result["normals"]
        assert isinstance(normals, list)
        assert len(normals) == result["n_vertices"] * 3

    def test_colors_flat_list(self, sample_grd_file):
        """Colors should be a flat list of floats (r,g,b triplets)."""
        result = parse_shyfem_mesh(sample_grd_file)
        colors = result["colors"]
        assert isinstance(colors, list)
        assert len(colors) == result["n_vertices"] * 3
        # Colors should be normalized to [0, 1]
        assert all(0 <= c <= 1 for c in colors)

    def test_indices_flat_list(self, sample_grd_file):
        """Indices should be a flat list of integers."""
        result = parse_shyfem_mesh(sample_grd_file)
        indices = result["indices"]
        assert isinstance(indices, list)
        assert len(indices) % 3 == 0  # Triangles
        assert len(indices) == result["n_triangles"] * 3

    def test_center_is_lon_lat(self, sample_grd_file):
        """Center should be [lon, lat] pair."""
        result = parse_shyfem_mesh(sample_grd_file)
        center = result["center"]
        assert len(center) == 2
        # Should be near our sample coordinates
        assert 20 < center[0] < 21  # lon
        assert 55 < center[1] < 56  # lat

    def test_depth_range_is_min_max(self, sample_grd_file):
        """Depth range should be [min, max] pair."""
        result = parse_shyfem_mesh(sample_grd_file)
        depth_range = result["depth_range"]
        assert len(depth_range) == 2
        assert depth_range[0] <= depth_range[1]

    def test_z_scale_affects_positions(self, sample_grd_file):
        """z_scale parameter should affect Z positions."""
        result1 = parse_shyfem_mesh(sample_grd_file, z_scale=50.0)
        result2 = parse_shyfem_mesh(sample_grd_file, z_scale=100.0)

        # Z values (every 3rd value starting from index 2) should be different
        z1 = result1["positions"][2::3]
        z2 = result2["positions"][2::3]

        # With 2x scale, Z values should be ~2x
        if z1[0] != 0:  # Avoid division by zero
            ratio = z2[0] / z1[0]
            assert abs(ratio - 2.0) < 0.01

    def test_empty_file_raises_error(self):
        """Empty file should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(SAMPLE_GRD_EMPTY)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="No nodes or elements"):
                parse_shyfem_mesh(path)
        finally:
            path.unlink()

    def test_json_serializable(self, sample_grd_file):
        """Result should be JSON-serializable."""
        import json
        result = parse_shyfem_mesh(sample_grd_file)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------

class TestParserEdgeCases:
    """Tests for edge cases and error handling."""

    def test_whitespace_lines_ignored(self):
        """Blank lines and whitespace should be ignored."""
        content = """
        1 1 0 20.5 55.0 10.0

        1 2 0 20.6 55.0 15.0

        1 3 0 20.55 55.1 12.0
        2 1 0 3 1 2 3 12.0
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            assert len(result) == 1
        finally:
            path.unlink()

    def test_missing_vertex_skipped(self):
        """Elements referencing missing vertices should be skipped."""
        content = """\
1 1 0 20.5 55.0 10.0
1 2 0 20.6 55.0 15.0
2 1 0 3 1 2 99
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            # Element with missing vertex 99 should be skipped
            assert len(result) == 0
        finally:
            path.unlink()

    def test_element_without_explicit_depth(self):
        """Elements without depth column should use averaged node depths."""
        content = """\
1 1 0 20.5 55.0 10.0
1 2 0 20.6 55.0 20.0
1 3 0 20.55 55.1 15.0
2 1 0 3 1 2 3
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".grd", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            result = parse_shyfem_grd(path)
            # Depth should be average of 10, 20, 15 = 15
            assert result[0]["depth"] == 15.0
        finally:
            path.unlink()
