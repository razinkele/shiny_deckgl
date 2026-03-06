"""Tests for the views module — deck.gl view helpers.

Tests verify that:
- All view functions return proper dict structure
- View type markers (@@type) are correct
- kwargs are forwarded correctly
- Common view configurations work as expected
"""

from __future__ import annotations

import pytest

from shiny_deckgl import (
    map_view,
    orthographic_view,
    first_person_view,
    globe_view,
    orbit_view,
)


# ---------------------------------------------------------------------------
# Test view structure and type markers
# ---------------------------------------------------------------------------

class TestViewStructure:
    """Tests that all views return proper dict structure."""

    def test_map_view_structure(self):
        """map_view should return dict with @@type."""
        v = map_view()
        assert isinstance(v, dict)
        assert "@@type" in v
        assert v["@@type"] == "MapView"

    def test_orthographic_view_structure(self):
        """orthographic_view should return dict with @@type."""
        v = orthographic_view()
        assert isinstance(v, dict)
        assert "@@type" in v
        assert v["@@type"] == "OrthographicView"

    def test_first_person_view_structure(self):
        """first_person_view should return dict with @@type."""
        v = first_person_view()
        assert isinstance(v, dict)
        assert "@@type" in v
        assert v["@@type"] == "FirstPersonView"

    def test_globe_view_structure(self):
        """globe_view should return dict with @@type."""
        v = globe_view()
        assert isinstance(v, dict)
        assert "@@type" in v
        assert v["@@type"] == "GlobeView"

    def test_orbit_view_structure(self):
        """orbit_view should return dict with @@type."""
        v = orbit_view()
        assert isinstance(v, dict)
        assert "@@type" in v
        assert v["@@type"] == "OrbitView"


# ---------------------------------------------------------------------------
# Test kwargs forwarding
# ---------------------------------------------------------------------------

class TestViewKwargs:
    """Tests that kwargs are properly forwarded to view dicts."""

    def test_map_view_kwargs(self):
        """map_view should forward kwargs."""
        v = map_view(
            id="main-view",
            controller=True,
            x=0,
            y=0,
            width="100%",
            height="100%",
        )
        assert v["id"] == "main-view"
        assert v["controller"] is True
        assert v["x"] == 0
        assert v["y"] == 0
        assert v["width"] == "100%"
        assert v["height"] == "100%"

    def test_orthographic_view_kwargs(self):
        """orthographic_view should forward kwargs."""
        v = orthographic_view(
            id="ortho-view",
            controller=True,
            flipY=False,
        )
        assert v["id"] == "ortho-view"
        assert v["controller"] is True
        assert v["flipY"] is False

    def test_first_person_view_kwargs(self):
        """first_person_view should forward kwargs."""
        v = first_person_view(
            id="fps-view",
            controller=True,
            fovy=75,
        )
        assert v["id"] == "fps-view"
        assert v["controller"] is True
        assert v["fovy"] == 75

    def test_globe_view_kwargs(self):
        """globe_view should forward kwargs."""
        v = globe_view(
            id="globe-view",
            controller=True,
            resolution=2,
        )
        assert v["id"] == "globe-view"
        assert v["controller"] is True
        assert v["resolution"] == 2

    def test_orbit_view_kwargs(self):
        """orbit_view should forward kwargs."""
        v = orbit_view(
            id="orbit-view",
            target=[0, 0, 0],
            rotationX=30,
            rotationOrbit=45,
            zoom=2,
            minZoom=0,
            maxZoom=10,
            controller=True,
        )
        assert v["id"] == "orbit-view"
        assert v["target"] == [0, 0, 0]
        assert v["rotationX"] == 30
        assert v["rotationOrbit"] == 45
        assert v["zoom"] == 2
        assert v["minZoom"] == 0
        assert v["maxZoom"] == 10
        assert v["controller"] is True


# ---------------------------------------------------------------------------
# Test view state configuration
# ---------------------------------------------------------------------------

class TestViewStateConfiguration:
    """Tests for view state configuration patterns."""

    def test_map_view_with_view_state(self):
        """map_view should accept viewState."""
        v = map_view(
            viewState={
                "longitude": -122.4,
                "latitude": 37.8,
                "zoom": 10,
                "pitch": 45,
                "bearing": 0,
            }
        )
        assert v["viewState"]["longitude"] == -122.4
        assert v["viewState"]["latitude"] == 37.8
        assert v["viewState"]["zoom"] == 10
        assert v["viewState"]["pitch"] == 45

    def test_globe_view_with_view_state(self):
        """globe_view should accept viewState."""
        v = globe_view(
            viewState={
                "longitude": 0,
                "latitude": 0,
                "zoom": 1,
            }
        )
        assert v["viewState"]["longitude"] == 0
        assert v["viewState"]["latitude"] == 0
        assert v["viewState"]["zoom"] == 1

    def test_orbit_view_with_view_state(self):
        """orbit_view should accept viewState."""
        v = orbit_view(
            viewState={
                "target": [0, 0, 0],
                "rotationX": 0,
                "rotationOrbit": 0,
                "zoom": 1,
            }
        )
        assert v["viewState"]["target"] == [0, 0, 0]
        assert v["viewState"]["rotationX"] == 0


# ---------------------------------------------------------------------------
# Test controller configuration
# ---------------------------------------------------------------------------

class TestControllerConfiguration:
    """Tests for controller configuration options."""

    def test_map_view_controller_boolean(self):
        """map_view should accept boolean controller."""
        v = map_view(controller=True)
        assert v["controller"] is True

        v = map_view(controller=False)
        assert v["controller"] is False

    def test_map_view_controller_dict(self):
        """map_view should accept dict controller with options."""
        v = map_view(
            controller={
                "scrollZoom": True,
                "dragPan": True,
                "dragRotate": False,
                "doubleClickZoom": True,
                "touchZoom": True,
                "touchRotate": True,
                "keyboard": True,
            }
        )
        assert v["controller"]["scrollZoom"] is True
        assert v["controller"]["dragRotate"] is False

    def test_orbit_view_controller_options(self):
        """orbit_view should accept controller options."""
        v = orbit_view(
            controller={
                "dragMode": "rotate",
                "scrollZoom": True,
            }
        )
        assert v["controller"]["dragMode"] == "rotate"


# ---------------------------------------------------------------------------
# Test multi-view layouts
# ---------------------------------------------------------------------------

class TestMultiViewLayouts:
    """Tests for multi-view layout configurations."""

    def test_split_view_layout(self):
        """Multiple views can be configured for split layout."""
        views = [
            map_view(id="left", x=0, y=0, width="50%", height="100%"),
            map_view(id="right", x="50%", y=0, width="50%", height="100%"),
        ]
        assert len(views) == 2
        assert views[0]["x"] == 0
        assert views[1]["x"] == "50%"

    def test_minimap_layout(self):
        """Main map with minimap overlay."""
        views = [
            map_view(id="main", controller=True),
            map_view(
                id="minimap",
                x=10,
                y=10,
                width=200,
                height=150,
                controller=False,
            ),
        ]
        assert views[0]["controller"] is True
        assert views[1]["controller"] is False
        assert views[1]["width"] == 200

    def test_map_and_orbit_combo(self):
        """Map view with orbit view for 3D inspection."""
        views = [
            map_view(id="map", width="70%"),
            orbit_view(id="3d", x="70%", width="30%"),
        ]
        assert views[0]["@@type"] == "MapView"
        assert views[1]["@@type"] == "OrbitView"


# ---------------------------------------------------------------------------
# Test view-specific properties
# ---------------------------------------------------------------------------

class TestViewSpecificProperties:
    """Tests for view-specific properties."""

    def test_first_person_view_fovy(self):
        """first_person_view should accept fovy (field of view)."""
        v = first_person_view(fovy=90)
        assert v["fovy"] == 90

    def test_first_person_view_near_far(self):
        """first_person_view should accept near/far clipping planes."""
        v = first_person_view(near=0.1, far=1000)
        assert v["near"] == 0.1
        assert v["far"] == 1000

    def test_orbit_view_orbit_axis(self):
        """orbit_view should accept orbitAxis."""
        v = orbit_view(orbitAxis="Y")
        assert v["orbitAxis"] == "Y"

        v = orbit_view(orbitAxis="Z")
        assert v["orbitAxis"] == "Z"

    def test_orthographic_view_flip_y(self):
        """orthographic_view should accept flipY."""
        v = orthographic_view(flipY=True)
        assert v["flipY"] is True


# ---------------------------------------------------------------------------
# Test edge cases
# ---------------------------------------------------------------------------

class TestViewEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_view_with_no_kwargs(self):
        """Views should work with no kwargs."""
        v = map_view()
        assert len(v) == 1  # Only @@type

    def test_view_with_none_values(self):
        """Views should pass through None values."""
        v = map_view(controller=None)
        assert v["controller"] is None

    def test_view_with_complex_view_state(self):
        """Views should handle complex nested viewState."""
        v = map_view(
            viewState={
                "longitude": -122.4,
                "latitude": 37.8,
                "zoom": 10,
                "transitionDuration": 1000,
                "transitionInterpolator": "FlyToInterpolator",
            }
        )
        assert v["viewState"]["transitionInterpolator"] == "FlyToInterpolator"

    def test_view_clear_property(self):
        """Views should accept clear property."""
        v = map_view(clear=True)
        assert v["clear"] is True

    def test_view_repeat_property(self):
        """Views should accept repeat property."""
        v = map_view(repeat=True)
        assert v["repeat"] is True

    def test_all_views_instantiate(self):
        """All view types should instantiate without error."""
        views = [
            map_view(),
            orthographic_view(),
            first_person_view(),
            globe_view(),
            orbit_view(),
        ]
        assert len(views) == 5
        for v in views:
            assert "@@type" in v


# ---------------------------------------------------------------------------
# Test view type markers consistency
# ---------------------------------------------------------------------------

class TestViewTypeMarkers:
    """Tests for consistent view type markers."""

    @pytest.mark.parametrize("view_fn,expected_type", [
        (map_view, "MapView"),
        (orthographic_view, "OrthographicView"),
        (first_person_view, "FirstPersonView"),
        (globe_view, "GlobeView"),
        (orbit_view, "OrbitView"),
    ])
    def test_view_type_marker(self, view_fn, expected_type):
        """Each view should have correct @@type marker."""
        v = view_fn()
        assert v["@@type"] == expected_type

    def test_view_type_is_string(self):
        """@@type should always be a string."""
        for view_fn in [map_view, orthographic_view, first_person_view, globe_view, orbit_view]:
            v = view_fn()
            assert isinstance(v["@@type"], str)
