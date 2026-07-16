"""Regression tests for the deep-review fix batch.

Covers: to_html() <script> breakout escaping, NaN/inf JSON sanitisation in
to_html()/to_json(), the point_cloud/simple_mesh default accessor, and
encode_binary_attribute() TypeError ordering.
"""
from __future__ import annotations

import json

import pytest

from shiny_deckgl import (
    MapWidget,
    scatterplot_layer,
    point_cloud_layer,
    simple_mesh_layer,
    encode_binary_attribute,
)


class TestToHtmlScriptBreakout:
    def test_closing_script_tag_is_escaped(self):
        # A layer property containing </script> must not break out of the
        # embedding <script> block in the exported HTML.
        lyr = scatterplot_layer(
            "evil", [{"position": [21.0, 55.0], "label": "</script><img src=x onerror=alert(1)>"}],
        )
        html = MapWidget("m").to_html([lyr])
        assert "</script><img" not in html
        assert "\\u003c/script>" in html or "\\u003c/script" in html


class TestJsonNaNSanitisation:
    def test_to_json_nullifies_nan(self):
        lyr = scatterplot_layer("pts", [{"position": [float("nan"), 55.0]}])
        spec = MapWidget("m").to_json([lyr])
        # Must be valid JSON with strict parsing (no NaN/Infinity tokens).
        parsed = json.loads(spec)
        assert parsed["layers"][0]["data"][0]["position"][0] is None

    def test_to_html_has_no_infinity_token(self):
        lyr = scatterplot_layer("pts", [{"position": [float("inf"), 55.0]}])
        html = MapWidget("m").to_html([lyr])
        # json.dumps would emit a bare `Infinity` token for inf; json_safe must
        # nullify it so the embedded layersData is valid JSON. ("NaN" is not
        # checked here because the runtime JS legitimately contains isNaN().)
        assert "Infinity" not in html


class TestDefaultAccessorsResolvable:
    def test_point_cloud_default_getposition(self):
        assert point_cloud_layer("pc")["getPosition"] == "@@d.position"

    def test_simple_mesh_default_getposition(self):
        assert simple_mesh_layer("mesh")["getPosition"] == "@@d.position"


class TestEncodeBinaryTypeError:
    def test_non_ndarray_raises_type_error(self):
        with pytest.raises(TypeError):
            encode_binary_attribute([1, 2, 3])

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            encode_binary_attribute(None)
