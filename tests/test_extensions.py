"""Tests for the extensions module — deck.gl layer extensions.

Tests verify that:
- All extension functions return proper structure (string or [name, options])
- Extension names match deck.gl class names
- Parameters are properly forwarded
- Extension type alias works correctly
"""

from __future__ import annotations

import pytest

from shiny_deckgl import (
    brushing_extension,
    collision_filter_extension,
    data_filter_extension,
    mask_extension,
    clip_extension,
    terrain_extension,
    fill_style_extension,
    path_style_extension,
    fp64_extension,
)
from shiny_deckgl.extensions import Extension


# ---------------------------------------------------------------------------
# Test extension return types
# ---------------------------------------------------------------------------

class TestExtensionReturnTypes:
    """Tests that extensions return proper types (string or list)."""

    def test_brushing_extension_returns_string(self):
        """brushing_extension should return string."""
        ext = brushing_extension()
        assert isinstance(ext, str)
        assert ext == "BrushingExtension"

    def test_collision_filter_extension_returns_string(self):
        """collision_filter_extension should return string."""
        ext = collision_filter_extension()
        assert isinstance(ext, str)
        assert ext == "CollisionFilterExtension"

    def test_data_filter_extension_returns_list(self):
        """data_filter_extension should return [name, options] list."""
        ext = data_filter_extension()
        assert isinstance(ext, list)
        assert len(ext) == 2
        assert ext[0] == "DataFilterExtension"
        assert isinstance(ext[1], dict)

    def test_mask_extension_returns_string(self):
        """mask_extension should return string."""
        ext = mask_extension()
        assert isinstance(ext, str)
        assert ext == "MaskExtension"

    def test_clip_extension_returns_string(self):
        """clip_extension should return string."""
        ext = clip_extension()
        assert isinstance(ext, str)
        assert ext == "ClipExtension"

    def test_terrain_extension_returns_string(self):
        """terrain_extension should return string."""
        ext = terrain_extension()
        assert isinstance(ext, str)
        assert ext == "TerrainExtension"

    def test_fill_style_extension_returns_list(self):
        """fill_style_extension should return [name, options] list."""
        ext = fill_style_extension()
        assert isinstance(ext, list)
        assert len(ext) == 2
        assert ext[0] == "FillStyleExtension"
        assert isinstance(ext[1], dict)

    def test_path_style_extension_returns_list(self):
        """path_style_extension should return [name, options] list."""
        ext = path_style_extension()
        assert isinstance(ext, list)
        assert len(ext) == 2
        assert ext[0] == "PathStyleExtension"
        assert isinstance(ext[1], dict)

    def test_fp64_extension_returns_string(self):
        """fp64_extension should return string."""
        ext = fp64_extension()
        assert isinstance(ext, str)
        assert ext == "Fp64Extension"


# ---------------------------------------------------------------------------
# Test extension parameters
# ---------------------------------------------------------------------------

class TestExtensionParameters:
    """Tests for extension parameter handling."""

    def test_data_filter_extension_default_filter_size(self):
        """data_filter_extension should default to filter_size=1."""
        ext = data_filter_extension()
        assert ext[1]["filterSize"] == 1

    @pytest.mark.parametrize("filter_size", [1, 2, 3, 4])
    def test_data_filter_extension_custom_filter_size(self, filter_size):
        """data_filter_extension should accept filter_size 1-4."""
        ext = data_filter_extension(filter_size=filter_size)
        assert ext[1]["filterSize"] == filter_size

    def test_fill_style_extension_default_pattern(self):
        """fill_style_extension should default to pattern=True."""
        ext = fill_style_extension()
        assert ext[1]["pattern"] is True

    def test_fill_style_extension_pattern_false(self):
        """fill_style_extension should accept pattern=False."""
        ext = fill_style_extension(pattern=False)
        assert ext[1]["pattern"] is False

    def test_path_style_extension_defaults(self):
        """path_style_extension should default to dash=False, high_precision=False."""
        ext = path_style_extension()
        assert ext[1]["dash"] is False
        assert ext[1]["highPrecisionDash"] is False

    def test_path_style_extension_dash_enabled(self):
        """path_style_extension should accept dash=True."""
        ext = path_style_extension(dash=True)
        assert ext[1]["dash"] is True

    def test_path_style_extension_high_precision(self):
        """path_style_extension should accept high_precision=True."""
        ext = path_style_extension(high_precision=True)
        assert ext[1]["highPrecisionDash"] is True

    def test_path_style_extension_all_options(self):
        """path_style_extension should accept all options together."""
        ext = path_style_extension(dash=True, high_precision=True)
        assert ext[1]["dash"] is True
        assert ext[1]["highPrecisionDash"] is True


# ---------------------------------------------------------------------------
# Test Extension type alias
# ---------------------------------------------------------------------------

class TestExtensionTypeAlias:
    """Tests for the Extension type alias."""

    def test_extension_type_accepts_string(self):
        """Extension type should accept string."""
        ext: Extension = "BrushingExtension"
        assert isinstance(ext, str)

    def test_extension_type_accepts_list(self):
        """Extension type should accept list."""
        ext: Extension = ["DataFilterExtension", {"filterSize": 2}]
        assert isinstance(ext, list)

    def test_all_extensions_match_type(self):
        """All extension functions should return Extension type."""
        extensions = [
            brushing_extension(),
            collision_filter_extension(),
            data_filter_extension(),
            mask_extension(),
            clip_extension(),
            terrain_extension(),
            fill_style_extension(),
            path_style_extension(),
            fp64_extension(),
        ]
        for ext in extensions:
            # Extension is Union[str, list]
            assert isinstance(ext, (str, list))


# ---------------------------------------------------------------------------
# Test extension names match deck.gl
# ---------------------------------------------------------------------------

class TestExtensionNames:
    """Tests that extension names match deck.gl class names."""

    @pytest.mark.parametrize("ext_fn,expected_name", [
        (brushing_extension, "BrushingExtension"),
        (collision_filter_extension, "CollisionFilterExtension"),
        (mask_extension, "MaskExtension"),
        (clip_extension, "ClipExtension"),
        (terrain_extension, "TerrainExtension"),
        (fp64_extension, "Fp64Extension"),
    ])
    def test_string_extension_name(self, ext_fn, expected_name):
        """String extensions should have correct class name."""
        ext = ext_fn()
        assert ext == expected_name

    @pytest.mark.parametrize("ext_fn,expected_name", [
        (data_filter_extension, "DataFilterExtension"),
        (fill_style_extension, "FillStyleExtension"),
        (path_style_extension, "PathStyleExtension"),
    ])
    def test_list_extension_name(self, ext_fn, expected_name):
        """List extensions should have correct class name as first element."""
        ext = ext_fn()
        assert ext[0] == expected_name


# ---------------------------------------------------------------------------
# Test extension combinations
# ---------------------------------------------------------------------------

class TestExtensionCombinations:
    """Tests for combining multiple extensions."""

    def test_multiple_string_extensions(self):
        """Multiple string extensions should work in a list."""
        extensions = [
            brushing_extension(),
            collision_filter_extension(),
            mask_extension(),
        ]
        assert len(extensions) == 3
        assert all(isinstance(e, str) for e in extensions)

    def test_mixed_extensions(self):
        """Mixed string and list extensions should work together."""
        extensions = [
            brushing_extension(),
            data_filter_extension(filter_size=2),
            mask_extension(),
            fill_style_extension(pattern=True),
        ]
        assert len(extensions) == 4
        assert isinstance(extensions[0], str)
        assert isinstance(extensions[1], list)
        assert isinstance(extensions[2], str)
        assert isinstance(extensions[3], list)

    def test_common_scatterplot_extensions(self):
        """Common extensions for ScatterplotLayer."""
        extensions = [
            brushing_extension(),
            data_filter_extension(filter_size=1),
        ]
        assert extensions[0] == "BrushingExtension"
        assert extensions[1][0] == "DataFilterExtension"

    def test_common_path_extensions(self):
        """Common extensions for PathLayer."""
        extensions = [
            path_style_extension(dash=True),
            terrain_extension(),
        ]
        assert extensions[0][0] == "PathStyleExtension"
        assert extensions[1] == "TerrainExtension"

    def test_common_polygon_extensions(self):
        """Common extensions for PolygonLayer."""
        extensions = [
            fill_style_extension(pattern=True),
            mask_extension(),
            clip_extension(),
        ]
        assert len(extensions) == 3


# ---------------------------------------------------------------------------
# Test extension with layer integration
# ---------------------------------------------------------------------------

class TestExtensionLayerIntegration:
    """Tests for extensions used with layer functions."""

    def test_extensions_in_layer_format(self):
        """Extensions should be usable in layer extensions parameter."""
        from shiny_deckgl import scatterplot_layer

        layer = scatterplot_layer(
            "points",
            data=[],
            extensions=[
                brushing_extension(),
                data_filter_extension(filter_size=1),
            ],
            brushingRadius=50000,
            brushingEnabled=True,
        )

        # Layer function uses @@extensions key
        assert "@@extensions" in layer
        assert len(layer["@@extensions"]) == 2
        assert layer["brushingRadius"] == 50000

    def test_all_extensions_in_layer(self):
        """All extensions should be usable in a layer."""
        from shiny_deckgl import layer

        l = layer(
            "ScatterplotLayer",
            "test",
            data=[],
            extensions=[
                brushing_extension(),
                collision_filter_extension(),
                data_filter_extension(),
                mask_extension(),
                clip_extension(),
                terrain_extension(),
                fill_style_extension(),
                path_style_extension(),
                fp64_extension(),
            ],
        )
        # Layer function uses @@extensions key
        assert len(l["@@extensions"]) == 9


# ---------------------------------------------------------------------------
# Test edge cases
# ---------------------------------------------------------------------------

class TestExtensionEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_data_filter_extension_zero_filter_size(self):
        """data_filter_extension with filter_size=0 (unusual but allowed)."""
        ext = data_filter_extension(filter_size=0)
        assert ext[1]["filterSize"] == 0

    def test_extension_options_are_independent(self):
        """Each extension call should return independent options dict."""
        ext1 = data_filter_extension(filter_size=1)
        ext2 = data_filter_extension(filter_size=2)

        # Modify ext1's options
        ext1[1]["extra"] = "value"

        # ext2 should not be affected
        assert "extra" not in ext2[1]
        assert ext1[1]["filterSize"] == 1
        assert ext2[1]["filterSize"] == 2

    def test_fill_style_extension_with_pattern_true(self):
        """fill_style_extension with explicit pattern=True."""
        ext = fill_style_extension(pattern=True)
        assert ext[1]["pattern"] is True

    def test_all_extensions_instantiate(self):
        """All extension functions should instantiate without error."""
        extensions = [
            brushing_extension(),
            collision_filter_extension(),
            data_filter_extension(),
            mask_extension(),
            clip_extension(),
            terrain_extension(),
            fill_style_extension(),
            path_style_extension(),
            fp64_extension(),
        ]
        assert len(extensions) == 9
        for ext in extensions:
            assert ext is not None
