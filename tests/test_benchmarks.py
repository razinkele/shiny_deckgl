"""Performance benchmarks for shiny_deckgl.

Run with: pytest tests/test_benchmarks.py --benchmark-only -v

These benchmarks measure the performance of key operations to ensure
they remain fast as the codebase evolves.
"""
from __future__ import annotations

import json

import pytest

from shiny_deckgl import (
    MapWidget,
    scatterplot_layer,
    geojson_layer,
    line_layer,
    arc_layer,
    path_layer,
    polygon_layer,
    layer,
    color_range,
    color_bins,
    color_quantiles,
    transition,
    PALETTE_VIRIDIS,
)
from shiny_deckgl._mixins import NavigationMixin
from shiny_deckgl._data_utils import _serialise_data


# ---------------------------------------------------------------------------
# Fixtures for benchmark data
# ---------------------------------------------------------------------------

@pytest.fixture
def small_point_data():
    """100 data points."""
    return [{"position": [i * 0.1, i * 0.1], "value": i} for i in range(100)]


@pytest.fixture
def medium_point_data():
    """1,000 data points."""
    return [{"position": [i * 0.01, i * 0.01], "value": i} for i in range(1000)]


@pytest.fixture
def large_point_data():
    """10,000 data points."""
    return [{"position": [i * 0.001, i * 0.001], "value": i} for i in range(10000)]


@pytest.fixture
def small_geojson():
    """GeoJSON with 100 features."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [i * 0.1, i * 0.1]},
                "properties": {"id": i, "value": i * 10},
            }
            for i in range(100)
        ],
    }


@pytest.fixture
def medium_geojson():
    """GeoJSON with 1,000 features."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [i * 0.01, i * 0.01]},
                "properties": {"id": i, "value": i * 10},
            }
            for i in range(1000)
        ],
    }


@pytest.fixture
def large_geojson():
    """GeoJSON with 10,000 features."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [i * 0.001, i * 0.001]},
                "properties": {"id": i, "value": i * 10},
            }
            for i in range(10000)
        ],
    }


@pytest.fixture
def numeric_values_small():
    """100 numeric values for color functions."""
    return [i * 1.5 for i in range(100)]


@pytest.fixture
def numeric_values_large():
    """10,000 numeric values for color functions."""
    return [i * 0.01 for i in range(10000)]


# ---------------------------------------------------------------------------
# MapWidget benchmarks
# ---------------------------------------------------------------------------

class TestMapWidgetBenchmarks:
    """Benchmarks for MapWidget creation and operations."""

    def test_widget_creation(self, benchmark):
        """Benchmark MapWidget instantiation."""
        benchmark(
            MapWidget,
            "benchmark_widget",
            view_state={"longitude": 0, "latitude": 0, "zoom": 5},
        )

    def test_widget_ui_generation(self, benchmark):
        """Benchmark UI tag generation."""
        widget = MapWidget("benchmark_widget")
        benchmark(widget.ui)

    def test_to_json_small(self, benchmark, small_point_data):
        """Benchmark JSON serialization with 100 data points."""
        widget = MapWidget("benchmark_widget")
        layers = [scatterplot_layer("points", data=small_point_data)]
        benchmark(widget.to_json, layers)

    def test_to_json_medium(self, benchmark, medium_point_data):
        """Benchmark JSON serialization with 1,000 data points."""
        widget = MapWidget("benchmark_widget")
        layers = [scatterplot_layer("points", data=medium_point_data)]
        benchmark(widget.to_json, layers)

    def test_to_json_large(self, benchmark, large_point_data):
        """Benchmark JSON serialization with 10,000 data points."""
        widget = MapWidget("benchmark_widget")
        layers = [scatterplot_layer("points", data=large_point_data)]
        benchmark(widget.to_json, layers)

    def test_from_json(self, benchmark):
        """Benchmark JSON deserialization."""
        widget = MapWidget("benchmark_widget")
        layers = [scatterplot_layer("points", data=[{"position": [0, 0]}])]
        json_str = widget.to_json(layers)
        benchmark(MapWidget.from_json, json_str)


# ---------------------------------------------------------------------------
# Layer creation benchmarks
# ---------------------------------------------------------------------------

class TestLayerBenchmarks:
    """Benchmarks for layer creation functions."""

    def test_scatterplot_layer_creation(self, benchmark, small_point_data):
        """Benchmark scatterplot layer creation."""
        benchmark(scatterplot_layer, "benchmark", data=small_point_data)

    def test_geojson_layer_creation(self, benchmark, small_geojson):
        """Benchmark GeoJSON layer creation."""
        benchmark(geojson_layer, "benchmark", data=small_geojson)

    def test_line_layer_creation(self, benchmark):
        """Benchmark line layer creation."""
        data = [
            {"sourcePosition": [0, 0], "targetPosition": [1, 1]}
            for _ in range(100)
        ]
        benchmark(line_layer, "benchmark", data=data)

    def test_arc_layer_creation(self, benchmark):
        """Benchmark arc layer creation."""
        data = [
            {"sourcePosition": [0, 0], "targetPosition": [1, 1]}
            for _ in range(100)
        ]
        benchmark(arc_layer, "benchmark", data=data)

    def test_generic_layer_creation(self, benchmark, small_point_data):
        """Benchmark generic layer() function."""
        benchmark(layer, "ScatterplotLayer", "benchmark", data=small_point_data)

    def test_multiple_layers_creation(self, benchmark, small_point_data):
        """Benchmark creating multiple layers."""
        def create_multiple():
            return [
                scatterplot_layer(f"layer_{i}", data=small_point_data)
                for i in range(10)
            ]
        benchmark(create_multiple)


# ---------------------------------------------------------------------------
# Color function benchmarks
# ---------------------------------------------------------------------------

class TestColorBenchmarks:
    """Benchmarks for color functions."""

    def test_color_range_small(self, benchmark):
        """Benchmark color_range with 10 colors."""
        benchmark(color_range, 10, PALETTE_VIRIDIS)

    def test_color_range_large(self, benchmark):
        """Benchmark color_range with 100 colors."""
        benchmark(color_range, 100, PALETTE_VIRIDIS)

    def test_color_bins_small(self, benchmark, numeric_values_small):
        """Benchmark color_bins with 100 values."""
        benchmark(color_bins, numeric_values_small, 6, PALETTE_VIRIDIS)

    def test_color_bins_large(self, benchmark, numeric_values_large):
        """Benchmark color_bins with 10,000 values."""
        benchmark(color_bins, numeric_values_large, 6, PALETTE_VIRIDIS)

    def test_color_quantiles_small(self, benchmark, numeric_values_small):
        """Benchmark color_quantiles with 100 values."""
        benchmark(color_quantiles, numeric_values_small, 6, PALETTE_VIRIDIS)

    def test_color_quantiles_large(self, benchmark, numeric_values_large):
        """Benchmark color_quantiles with 10,000 values."""
        benchmark(color_quantiles, numeric_values_large, 6, PALETTE_VIRIDIS)


# ---------------------------------------------------------------------------
# Bounds computation benchmarks
# ---------------------------------------------------------------------------

class TestBoundsComputationBenchmarks:
    """Benchmarks for bounds computation."""

    def test_compute_bounds_small(self, benchmark, small_geojson):
        """Benchmark compute_bounds with 100 features."""
        benchmark(NavigationMixin.compute_bounds, small_geojson)

    def test_compute_bounds_medium(self, benchmark, medium_geojson):
        """Benchmark compute_bounds with 1,000 features."""
        benchmark(NavigationMixin.compute_bounds, medium_geojson)

    def test_compute_bounds_large(self, benchmark, large_geojson):
        """Benchmark compute_bounds with 10,000 features."""
        benchmark(NavigationMixin.compute_bounds, large_geojson)


# ---------------------------------------------------------------------------
# Data serialization benchmarks
# ---------------------------------------------------------------------------

class TestDataSerializationBenchmarks:
    """Benchmarks for data serialization."""

    def test_serialise_list_small(self, benchmark, small_point_data):
        """Benchmark _serialise_data with 100 items."""
        benchmark(_serialise_data, small_point_data)

    def test_serialise_list_large(self, benchmark, large_point_data):
        """Benchmark _serialise_data with 10,000 items."""
        benchmark(_serialise_data, large_point_data)

    def test_serialise_geojson_small(self, benchmark, small_geojson):
        """Benchmark _serialise_data with small GeoJSON."""
        benchmark(_serialise_data, small_geojson)

    def test_serialise_geojson_large(self, benchmark, large_geojson):
        """Benchmark _serialise_data with large GeoJSON."""
        benchmark(_serialise_data, large_geojson)


# ---------------------------------------------------------------------------
# JSON operations benchmarks
# ---------------------------------------------------------------------------

class TestJsonBenchmarks:
    """Benchmarks for JSON serialization operations."""

    def test_json_dumps_small(self, benchmark, small_point_data):
        """Benchmark json.dumps with 100 items."""
        benchmark(json.dumps, small_point_data)

    def test_json_dumps_large(self, benchmark, large_point_data):
        """Benchmark json.dumps with 10,000 items."""
        benchmark(json.dumps, large_point_data)

    def test_json_loads(self, benchmark, large_point_data):
        """Benchmark json.loads with 10,000 items."""
        json_str = json.dumps(large_point_data)
        benchmark(json.loads, json_str)


# ---------------------------------------------------------------------------
# Transition benchmarks
# ---------------------------------------------------------------------------

class TestTransitionBenchmarks:
    """Benchmarks for transition creation."""

    def test_transition_simple(self, benchmark):
        """Benchmark simple transition creation."""
        benchmark(transition, duration=500)

    def test_transition_with_easing(self, benchmark):
        """Benchmark transition with easing."""
        benchmark(transition, duration=500, easing="ease-in-out-cubic")

    def test_transition_spring(self, benchmark):
        """Benchmark spring transition."""
        benchmark(transition, type="spring", stiffness=120, damping=20)


# ---------------------------------------------------------------------------
# HTML export benchmarks
# ---------------------------------------------------------------------------

class TestHtmlExportBenchmarks:
    """Benchmarks for HTML export."""

    def test_to_html_small(self, benchmark, small_point_data):
        """Benchmark to_html with 100 data points."""
        widget = MapWidget("benchmark_widget")
        layers = [scatterplot_layer("points", data=small_point_data)]
        benchmark(widget.to_html, layers)

    def test_to_html_medium(self, benchmark, medium_point_data):
        """Benchmark to_html with 1,000 data points."""
        widget = MapWidget("benchmark_widget")
        layers = [scatterplot_layer("points", data=medium_point_data)]
        benchmark(widget.to_html, layers)


# ---------------------------------------------------------------------------
# Numpy binary encoding benchmarks (if numpy available)
# ---------------------------------------------------------------------------

class TestNumpyBenchmarks:
    """Benchmarks for numpy operations (skipped if numpy not available)."""

    @pytest.fixture
    def numpy(self):
        """Import numpy or skip test."""
        return pytest.importorskip("numpy")

    def test_encode_binary_small(self, benchmark, numpy):
        """Benchmark binary encoding with 1,000 floats."""
        from shiny_deckgl._data_utils import encode_binary_attribute
        arr = numpy.random.rand(1000, 3).astype("float32")
        benchmark(encode_binary_attribute, arr)

    def test_encode_binary_large(self, benchmark, numpy):
        """Benchmark binary encoding with 100,000 floats."""
        from shiny_deckgl._data_utils import encode_binary_attribute
        arr = numpy.random.rand(100000, 3).astype("float32")
        benchmark(encode_binary_attribute, arr)

    def test_encode_binary_positions(self, benchmark, numpy):
        """Benchmark binary encoding for position data."""
        from shiny_deckgl._data_utils import encode_binary_attribute
        # Simulate 50,000 3D positions (common use case)
        arr = numpy.random.rand(50000, 3).astype("float32")
        benchmark(encode_binary_attribute, arr)
