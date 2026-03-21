"""Tests for tooltip template interpolation edge cases and XSS prevention.

These tests exercise the *Python-side* escaping (html.escape in to_html)
and document the expected JS-side interpolateTemplate behavior.
The JS logic itself is tested via the Playwright E2E suite; these unit
tests ensure the data contract is sound.
"""
import json
import re

from shiny_deckgl import MapWidget


class TestInterpolateTemplateContract:
    """Verify the Python side correctly passes templates that JS will parse."""

    def test_hyphenated_field_in_template(self):
        """Templates with {hyphen-field} should survive Python serialisation."""
        w = MapWidget("t1", tooltip={"html": "Code: {iso-a3}"})
        html = w.to_html(layers=[])
        blob = re.search(r'data-tooltip="([^"]*)"', html)
        assert blob is not None
        cfg = json.loads(blob.group(1).replace("&quot;", '"')
                         .replace("&amp;", "&")
                         .replace("&lt;", "<")
                         .replace("&gt;", ">"))
        assert cfg["html"] == "Code: {iso-a3}"
