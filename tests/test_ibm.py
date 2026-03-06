"""Tests for the IBM (Individual-Based Model) module.

Tests cover:
- Species colors and icon mappings
- format_trips() data helper
- Error handling for invalid inputs
"""
from __future__ import annotations

import json

import pytest

from shiny_deckgl.ibm import (
    ICON_ATLAS,
    ICON_MAPPING,
    SPECIES_COLORS,
    format_trips,
)


# ---------------------------------------------------------------------------
# Test SPECIES_COLORS constant
# ---------------------------------------------------------------------------

class TestSpeciesColors:
    """Tests for the SPECIES_COLORS dictionary."""

    def test_has_three_species(self):
        """Should have exactly three seal species."""
        assert len(SPECIES_COLORS) == 3

    def test_expected_species(self):
        """Should have the expected species keys."""
        assert "Grey seal" in SPECIES_COLORS
        assert "Ringed seal" in SPECIES_COLORS
        assert "Harbour seal" in SPECIES_COLORS

    def test_colors_are_rgba(self):
        """Each color should be [R, G, B, A] format."""
        for species, color in SPECIES_COLORS.items():
            assert len(color) == 4, f"{species} should have 4 color components"
            assert all(0 <= c <= 255 for c in color), f"{species} colors out of range"

    def test_colors_are_lists(self):
        """Colors should be lists (not tuples) for JSON compatibility."""
        for species, color in SPECIES_COLORS.items():
            assert isinstance(color, list), f"{species} color should be a list"

    def test_json_serializable(self):
        """SPECIES_COLORS should be JSON-serializable."""
        serialized = json.dumps(SPECIES_COLORS)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed == SPECIES_COLORS


# ---------------------------------------------------------------------------
# Test ICON_ATLAS constant
# ---------------------------------------------------------------------------

class TestIconAtlas:
    """Tests for the ICON_ATLAS base64 SVG string."""

    def test_is_data_uri(self):
        """Should be a valid data URI."""
        assert ICON_ATLAS.startswith("data:image/svg+xml;base64,")

    def test_base64_decodable(self):
        """Base64 portion should be decodable."""
        import base64
        b64_part = ICON_ATLAS.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert len(decoded) > 0

    def test_contains_svg(self):
        """Decoded content should be valid SVG."""
        import base64
        b64_part = ICON_ATLAS.split(",", 1)[1]
        decoded = base64.b64decode(b64_part).decode("utf-8")
        assert "<svg" in decoded
        assert "</svg>" in decoded

    def test_svg_dimensions(self):
        """SVG should have expected 192x64 dimensions."""
        import base64
        b64_part = ICON_ATLAS.split(",", 1)[1]
        decoded = base64.b64decode(b64_part).decode("utf-8")
        assert 'width="192"' in decoded
        assert 'height="64"' in decoded


# ---------------------------------------------------------------------------
# Test ICON_MAPPING constant
# ---------------------------------------------------------------------------

class TestIconMapping:
    """Tests for the ICON_MAPPING deck.gl configuration."""

    def test_has_three_species(self):
        """Should have mappings for all three species."""
        assert len(ICON_MAPPING) == 3

    def test_same_species_as_colors(self):
        """Should have same species keys as SPECIES_COLORS."""
        assert set(ICON_MAPPING.keys()) == set(SPECIES_COLORS.keys())

    def test_mapping_structure(self):
        """Each mapping should have x, y, width, height, anchorY."""
        for species, mapping in ICON_MAPPING.items():
            assert "x" in mapping, f"{species} missing x"
            assert "y" in mapping, f"{species} missing y"
            assert "width" in mapping, f"{species} missing width"
            assert "height" in mapping, f"{species} missing height"
            assert "anchorY" in mapping, f"{species} missing anchorY"

    def test_icon_dimensions(self):
        """All icons should be 64x64."""
        for species, mapping in ICON_MAPPING.items():
            assert mapping["width"] == 64
            assert mapping["height"] == 64

    def test_icon_positions(self):
        """Icons should be at expected x positions in sprite sheet."""
        assert ICON_MAPPING["Grey seal"]["x"] == 0
        assert ICON_MAPPING["Ringed seal"]["x"] == 64
        assert ICON_MAPPING["Harbour seal"]["x"] == 128

    def test_anchor_centered(self):
        """anchorY should be 32 (centered vertically)."""
        for species, mapping in ICON_MAPPING.items():
            assert mapping["anchorY"] == 32

    def test_json_serializable(self):
        """ICON_MAPPING should be JSON-serializable."""
        serialized = json.dumps(ICON_MAPPING)
        assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# Test format_trips() function
# ---------------------------------------------------------------------------

class TestFormatTrips:
    """Tests for the format_trips data helper function."""

    def test_basic_single_trip(self):
        """Should format a single 2D path into trip dict."""
        paths = [[[20.0, 57.0], [20.5, 57.2], [21.0, 57.0]]]
        result = format_trips(paths)

        assert len(result) == 1
        trip = result[0]
        assert "path" in trip
        assert "timestamps" in trip

    def test_path_becomes_3d(self):
        """2D coordinates should become 3D with timestamps."""
        paths = [[[20.0, 57.0], [20.5, 57.2]]]
        result = format_trips(paths)

        path_3d = result[0]["path"]
        assert len(path_3d[0]) == 3  # [lon, lat, time]
        assert len(path_3d[1]) == 3

    def test_timestamps_generated(self):
        """Timestamps should be auto-generated from loop_length."""
        paths = [[[20.0, 57.0], [20.5, 57.2], [21.0, 57.0]]]
        result = format_trips(paths, loop_length=100)

        timestamps = result[0]["timestamps"]
        assert timestamps == [0, 50, 100]

    def test_custom_loop_length(self):
        """loop_length parameter should affect timestamps."""
        paths = [[[0, 0], [1, 1], [2, 2]]]
        result = format_trips(paths, loop_length=200)

        timestamps = result[0]["timestamps"]
        assert timestamps == [0, 100, 200]

    def test_single_point_path(self):
        """Single point path should have timestamp 0."""
        paths = [[[20.0, 57.0]]]
        result = format_trips(paths)

        assert result[0]["timestamps"] == [0]
        assert result[0]["path"] == [[20.0, 57.0, 0]]

    def test_empty_path_skipped(self):
        """Empty paths should be skipped."""
        paths = [[], [[20.0, 57.0]], []]
        result = format_trips(paths)

        assert len(result) == 1  # Only the non-empty path

    def test_multiple_trips(self):
        """Should handle multiple trips."""
        paths = [
            [[20.0, 57.0], [20.5, 57.2]],
            [[21.0, 58.0], [21.5, 58.2], [22.0, 58.0]],
        ]
        result = format_trips(paths)

        assert len(result) == 2

    def test_3d_coordinates_preserved(self):
        """Pre-existing timestamps in 3D coords should be preserved."""
        paths = [[[20.0, 57.0, 10], [20.5, 57.2, 20], [21.0, 57.0, 30]]]
        result = format_trips(paths)

        timestamps = result[0]["timestamps"]
        assert timestamps == [10, 20, 30]

    def test_explicit_timestamps(self):
        """Explicit timestamps parameter should override generation."""
        paths = [[[20.0, 57.0], [20.5, 57.2], [21.0, 57.0]]]
        timestamps = [[0, 25, 100]]
        result = format_trips(paths, timestamps=timestamps)

        assert result[0]["timestamps"] == [0, 25, 100]

    def test_properties_merged(self):
        """Properties should be merged into trip dicts."""
        paths = [[[20.0, 57.0], [20.5, 57.2]]]
        properties = [{"name": "Trip 1", "color": [255, 0, 0], "species": "Grey seal"}]
        result = format_trips(paths, properties=properties)

        trip = result[0]
        assert trip["name"] == "Trip 1"
        assert trip["color"] == [255, 0, 0]
        assert trip["species"] == "Grey seal"

    def test_properties_length_mismatch_raises(self):
        """Mismatched properties length should raise ValueError."""
        paths = [[[20.0, 57.0]], [[21.0, 58.0]]]
        properties = [{"name": "Trip 1"}]  # Only one, but two paths

        with pytest.raises(ValueError, match="properties length"):
            format_trips(paths, properties=properties)

    def test_timestamps_length_mismatch_raises(self):
        """Mismatched timestamps length should raise ValueError."""
        paths = [[[20.0, 57.0]], [[21.0, 58.0]]]
        timestamps = [[0, 100]]  # Only one, but two paths

        with pytest.raises(ValueError, match="timestamps length"):
            format_trips(paths, timestamps=timestamps)

    def test_inner_timestamps_length_mismatch_raises(self):
        """Mismatched inner timestamps length should raise ValueError."""
        paths = [[[20.0, 57.0], [20.5, 57.2], [21.0, 57.0]]]
        timestamps = [[0, 100]]  # Only 2 timestamps but 3 points

        with pytest.raises(ValueError, match="timestamps.*length"):
            format_trips(paths, timestamps=timestamps)

    def test_json_serializable(self):
        """Output should be JSON-serializable."""
        paths = [[[20.0, 57.0], [20.5, 57.2]]]
        properties = [{"name": "Trip 1", "color": [255, 0, 0]}]
        result = format_trips(paths, properties=properties)

        serialized = json.dumps(result)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed[0]["name"] == "Trip 1"

    def test_deck_gl_compatible_output(self):
        """Output should be compatible with trips_layer accessor conventions."""
        paths = [[[20.0, 57.0], [20.5, 57.2]]]
        properties = [{"color": [255, 0, 0]}]
        result = format_trips(paths, properties=properties)

        trip = result[0]
        # trips_layer expects: getPath="@@d.path", getTimestamps="@@d.timestamps"
        assert "path" in trip
        assert "timestamps" in trip
        # And custom properties for getColor="@@d.color"
        assert "color" in trip


# ---------------------------------------------------------------------------
# Test trips_animation_ui (structure only, not Shiny behavior)
# ---------------------------------------------------------------------------

class TestTripsAnimationUi:
    """Tests for trips_animation_ui function."""

    def test_import_available(self):
        """Should be importable from ibm module."""
        from shiny_deckgl.ibm import trips_animation_ui
        assert callable(trips_animation_ui)

    def test_returns_tag_list(self):
        """Should return a Shiny TagList when called."""
        from shiny_deckgl.ibm import trips_animation_ui
        result = trips_animation_ui("test_anim")
        # Should be a Shiny Tag or TagList
        assert result is not None
        assert hasattr(result, "tagify") or hasattr(result, "children")


# ---------------------------------------------------------------------------
# Test trips_animation_server (signature only)
# ---------------------------------------------------------------------------

class TestTripsAnimationServer:
    """Tests for trips_animation_server function."""

    def test_import_available(self):
        """Should be importable from ibm module."""
        from shiny_deckgl.ibm import trips_animation_server
        assert callable(trips_animation_server)

    def test_function_signature(self):
        """Should have expected parameters."""
        import inspect
        from shiny_deckgl.ibm import trips_animation_server
        sig = inspect.signature(trips_animation_server)
        params = list(sig.parameters.keys())
        assert "id" in params
        assert "widget" in params
        assert "session" in params
