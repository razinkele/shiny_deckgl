"""Dark mode (v1.13.0): dark_style=, follow_dark_mode, set_dark_mode(), dark_mode_input_id."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import _FakeSession  # noqa: E402

DARK = "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json"


def test_dark_style_attribute_and_default_following():
    from shiny_deckgl import MapWidget
    html = str(MapWidget("m", dark_style=DARK).ui())
    assert f'data-dark-style="{DARK}"' in html
    assert "data-follow-dark-mode" not in html            # True is the default: no attribute
    html2 = str(MapWidget("m2", dark_style=DARK, follow_dark_mode=False).ui())
    assert 'data-follow-dark-mode="false"' in html2
    assert "data-dark-style" not in str(MapWidget("m3").ui())


def test_json_round_trip():
    from shiny_deckgl import MapWidget
    w = MapWidget("m", dark_style=DARK, follow_dark_mode=False)
    spec = json.loads(w.to_json([]))
    assert spec["darkStyle"] == DARK and spec["followDarkMode"] is False
    w2, _ = MapWidget.from_json(w.to_json([]))
    assert w2.dark_style == DARK and w2.follow_dark_mode is False
    assert "darkStyle" not in json.loads(MapWidget("d").to_json([]))


def test_set_dark_mode_sends_and_records_the_style_per_session():
    from shiny_deckgl import MapWidget
    from shiny_deckgl.colors import CARTO_POSITRON
    w, s1, s2 = MapWidget("m", dark_style=DARK), _FakeSession(), _FakeSession()
    asyncio.run(w.set_dark_mode(s1, True))
    assert s1.messages[-1] == ("deck_set_dark_mode", {"id": "m", "dark": True})
    assert w.current_style(s1) == DARK
    assert w.current_style(s2) == CARTO_POSITRON
    asyncio.run(w.set_dark_mode(s1, False))
    assert w.current_style(s1) == CARTO_POSITRON


def test_set_dark_mode_without_a_dark_style_only_toggles_widgets():
    from shiny_deckgl import MapWidget
    from shiny_deckgl.colors import CARTO_POSITRON
    w, s = MapWidget("m"), _FakeSession()
    asyncio.run(w.set_dark_mode(s, True))
    assert s.messages[-1] == ("deck_set_dark_mode", {"id": "m", "dark": True})
    assert w.current_style(s) == CARTO_POSITRON


def test_input_id():
    from shiny_deckgl import MapWidget
    assert MapWidget("m").dark_mode_input_id == "m_dark_mode"


def test_dark_style_must_be_a_string():
    from shiny_deckgl import MapWidget
    with pytest.raises(TypeError, match="dark_style"):
        MapWidget("m", dark_style=["x"])
