"""Tests for HexSim Fish demo tab data generators."""
import os
import sys
from pathlib import Path

import pytest
import numpy as np

_hexsim_root = os.environ.get("SHINY_DECKGL_HEXSIM_ROOT")
_hexsim_workspace = os.environ.get("SHINY_DECKGL_HEXSIM_WORKSPACE")

HEXSIM_ROOT = Path(_hexsim_root).expanduser() if _hexsim_root else None
HEXSIM_WORKSPACE = (
    Path(_hexsim_workspace).expanduser()
    if _hexsim_workspace
    else HEXSIM_ROOT / "Columbia [small]" if HEXSIM_ROOT else None
)

if HEXSIM_ROOT is not None:
    sys.path.insert(0, str(HEXSIM_ROOT))

try:
    from heximpy.hxnparser import Workspace  # noqa: F401
except ImportError:
    HEXSIM_AVAILABLE = False
else:
    HEXSIM_AVAILABLE = HEXSIM_WORKSPACE is not None and HEXSIM_WORKSPACE.exists()


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


FISH_COLORS = [
    [192, 128, 96, 220],
    [0, 130, 200, 220],
    [0, 180, 140, 220],
    [200, 160, 50, 220],
    [140, 90, 160, 220],
]


@pytest.mark.skipif(not HEXSIM_AVAILABLE, reason="heximpy not available")
class TestMakeHexsimTrips:

    def test_returns_list_of_dicts(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh, make_hexsim_trips
        _, centroids, neighbors, _ = make_hexsim_mesh()
        trips = make_hexsim_trips(10, centroids, neighbors)
        assert isinstance(trips, list)
        assert len(trips) == 10

    def test_trip_has_path_and_timestamps(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh, make_hexsim_trips
        _, centroids, neighbors, _ = make_hexsim_mesh()
        trips = make_hexsim_trips(5, centroids, neighbors)
        for trip in trips:
            assert "path" in trip
            assert "timestamps" in trip
            assert "species" in trip
            assert "color" in trip
            assert trip["species"] == "Atlantic salmon"

    def test_path_length_matches_timestamps(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh, make_hexsim_trips
        _, centroids, neighbors, _ = make_hexsim_mesh()
        trips = make_hexsim_trips(3, centroids, neighbors, n_steps=50)
        for trip in trips:
            assert len(trip["path"]) == len(trip["timestamps"])
            assert len(trip["path"][0]) == 3

    def test_colors_cycle(self):
        from shiny_deckgl._demo_data import make_hexsim_mesh, make_hexsim_trips
        _, centroids, neighbors, _ = make_hexsim_mesh()
        trips = make_hexsim_trips(10, centroids, neighbors)
        for i, trip in enumerate(trips):
            assert trip["color"] == FISH_COLORS[i % 5]
