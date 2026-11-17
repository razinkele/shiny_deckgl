"""deck.gl widget themes: widget_theme= / dark_widget_theme= / set_widget_theme()."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import _FakeSession  # noqa: E402


def test_names_and_dicts_become_data_attributes():
    from shiny_deckgl import MapWidget
    html = str(MapWidget("m", widget_theme="light-glass",
                         dark_widget_theme={"--button-size": "32px"}).ui())
    assert 'data-widget-theme="&quot;light-glass&quot;"' in html
    assert "data-dark-widget-theme=" in html and "--button-size" in html
    assert "data-widget-theme" not in str(MapWidget("plain").ui())


@pytest.mark.parametrize("bad", ["neon", 3, {"button-size": "32px"}])
def test_unknown_themes_are_rejected(bad):
    from shiny_deckgl import MapWidget
    with pytest.raises(ValueError, match="widget_theme"):
        MapWidget("m", widget_theme=bad)


def test_json_round_trip():
    from shiny_deckgl import MapWidget
    w = MapWidget("m", widget_theme="dark", dark_widget_theme="dark-glass")
    spec = json.loads(w.to_json([]))
    assert spec["widgetTheme"] == "dark" and spec["darkWidgetTheme"] == "dark-glass"
    w2, _ = MapWidget.from_json(w.to_json([]))
    assert (w2.widget_theme, w2.dark_widget_theme) == ("dark", "dark-glass")
    assert "widgetTheme" not in json.loads(MapWidget("d").to_json([]))


def test_set_widget_theme_sends_both_themes():
    from shiny_deckgl import MapWidget
    w, s = MapWidget("m"), _FakeSession()
    asyncio.run(w.set_widget_theme(s, "light-glass", dark_theme="dark-glass"))
    assert s.messages[-1] == ("deck_set_widget_theme",
                              {"id": "m", "theme": "light-glass", "darkTheme": "dark-glass"})
    with pytest.raises(ValueError, match="dark_theme"):
        asyncio.run(w.set_widget_theme(s, None, dark_theme="neon"))
