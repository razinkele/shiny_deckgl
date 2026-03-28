"""Tests for HexSim Fish demo tab data generators."""
import sys
import pytest
import numpy as np

sys.path.insert(0, r"C:\Users\DELL\OneDrive - ku.lt\HORIZON_EUROPE\HexSim")

try:
    from heximpy.hxnparser import Workspace  # noqa: F401
    HEXSIM_AVAILABLE = True
except ImportError:
    HEXSIM_AVAILABLE = False


@pytest.mark.skipif(not HEXSIM_AVAILABLE, reason="heximpy not available")
class TestMakeHexsimMesh:

    def test_returns_four_element_tuple(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        result = make_hexsim_mesh()
        assert isinstance(result, tuple)
        assert len(result) == 4

    def test_mesh_data_has_required_keys(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        mesh_data, centroids, neighbors, origin = make_hexsim_mesh()
        assert "positions" in mesh_data
        assert "colors" in mesh_data
        assert "indices" in mesh_data
        assert "center" in mesh_data

    def test_centroids_and_neighbors_shapes(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        mesh_data, centroids, neighbors, origin = make_hexsim_mesh()
        n = centroids.shape[0]
        assert centroids.shape == (n, 2)
        assert neighbors.shape == (n, 6)

    def test_neighbors_are_valid_indices(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        _, centroids, neighbors, _ = make_hexsim_mesh()
        n = centroids.shape[0]
        valid = neighbors[(neighbors >= 0)]
        assert np.all(valid < n)

    def test_origin_is_lon_lat(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        _, _, _, origin = make_hexsim_mesh()
        assert isinstance(origin, list)
        assert len(origin) == 2
        assert -180 <= origin[0] <= 180
        assert -90 <= origin[1] <= 90

    def test_mesh_positions_are_float32(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        mesh_data, _, _, _ = make_hexsim_mesh()
        assert mesh_data["positions"].dtype == np.float32

    def test_water_cells_count(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh
        _, centroids, _, _ = make_hexsim_mesh()
        assert centroids.shape[0] > 5000
