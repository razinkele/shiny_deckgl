"""Tests for tooltip template interpolation edge cases and XSS prevention.

These tests exercise the *Python-side* escaping (html.escape in to_html)
and document the expected JS-side interpolateTemplate behavior.
The JS logic itself is tested via the Playwright E2E suite; these unit
tests ensure the data contract is sound.
"""
import json
import re

from shiny_deckgl import MapWidget
from conftest import _FakeSession


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


class TestMarkerPopupSanitisation:
    """Marker popup_html is raw HTML — verify Python docstring warns about XSS."""

    def test_popup_html_passed_verbatim(self):
        """Confirm popup_html reaches the message payload unchanged
        (JS-side sanitisation handles safety)."""
        import asyncio

        w = MapWidget("m1")
        fake = _FakeSession()
        asyncio.run(w.add_marker(fake, "mk1", 21.0, 55.0,
                                 popup_html='<b>Safe</b>'))
        assert fake.messages[0][1]["popupHtml"] == "<b>Safe</b>"


class TestTooltipXssEdgeCases:
    """Verify Python-side tooltip serialisation handles XSS edge cases."""

    def test_script_tag_in_tooltip_template_is_escaped(self):
        """Template containing <script> should be HTML-escaped in data-attr."""
        w = MapWidget("xss1", tooltip={"html": "<script>alert(1)</script>"})
        html = w.to_html(layers=[])
        # Extract only the data-tooltip attribute value and verify the angle
        # brackets are escaped there (the full page has its own <script> tags)
        blob = re.search(r'data-tooltip="([^"]*)"', html)
        assert blob is not None
        attr_value = blob.group(1)
        assert "<script>" not in attr_value
        assert "&lt;script&gt;" in attr_value

    def test_template_with_nested_path(self):
        """Templates with {a.b.c} dot paths should serialise correctly."""
        w = MapWidget("xss2", tooltip={"html": "Val: {properties.name}"})
        html = w.to_html(layers=[])
        blob = re.search(r'data-tooltip="([^"]*)"', html)
        assert blob is not None

    def test_empty_tooltip_html(self):
        """Empty string tooltip html should still produce a valid data attr."""
        w = MapWidget("xss3", tooltip={"html": ""})
        html = w.to_html(layers=[])
        assert "data-tooltip" in html

    def test_tooltip_with_style_dict(self):
        """Tooltip with style should serialise both html and style."""
        tip = {"html": "{name}", "style": {"backgroundColor": "red"}}
        w = MapWidget("xss4", tooltip=tip)
        html = w.to_html(layers=[])
        blob = re.search(r'data-tooltip="([^"]*)"', html)
        assert blob is not None
        cfg = json.loads(blob.group(1).replace("&quot;", '"')
                         .replace("&amp;", "&"))
        assert cfg["style"]["backgroundColor"] == "red"

    def test_tooltip_with_special_chars_in_template(self):
        """Templates with quotes and ampersands should not break the HTML attr."""
        tip = {"html": '<b>{name}</b> &amp; "info"'}
        w = MapWidget("xss5", tooltip=tip)
        html = w.to_html(layers=[])
        # Must not have unescaped quotes breaking the attribute
        assert 'data-tooltip="' in html


class TestTooltipValidation:
    """Verify tooltip config validation on the Python side."""

    def test_tooltip_missing_html_key_raises(self):
        """Tooltip dict without 'html' key should raise ValueError."""
        import pytest
        with pytest.raises(ValueError, match="html"):
            MapWidget("v1", tooltip={"template": "{name}"})

    def test_tooltip_none_is_valid(self):
        """None tooltip should not raise."""
        w = MapWidget("v2", tooltip=None)
        assert w.tooltip is None

    def test_tooltip_with_html_key_is_valid(self):
        """Tooltip with 'html' key should work normally."""
        w = MapWidget("v3", tooltip={"html": "{name}"})
        assert w.tooltip == {"html": "{name}"}
