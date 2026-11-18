"""Demo sidebars are ARIA landmarks on Shiny >= 1.9 and still build on older Shiny."""
from __future__ import annotations

import re

import pytest


def test_every_demo_sidebar_is_a_labelled_landmark_where_supported():
    import inspect

    from shiny import ui
    if "role" not in inspect.signature(ui.sidebar).parameters:
        pytest.skip("ui.sidebar(role=) needs Shiny >= 1.9")
    from shiny_deckgl._app_ui import build_ui
    html = str(build_ui())
    labels = re.findall(r'<aside[^>]*aria-label="([^"]+)"', html)
    assert len(labels) == 12, labels
    assert all(label.endswith(" settings") for label in labels)
    assert len(set(labels)) == 12   # one name per tab


def test_sidebars_build_without_role_on_older_shiny(monkeypatch):
    """Shiny < 1.9 has no `role` (or `aria_label` landmark check): pass neither."""
    import shiny.ui

    from shiny_deckgl import _app_ui
    seen: list[dict] = []
    real = shiny.ui.sidebar

    def old_sidebar(*children, position="left", open=None, width=250, id=None,
                    title=None, bg=None, fg=None, class_=None, **kwargs):
        seen.append(kwargs)
        return real(*children, position=position, open=open, width=width, id=id,
                    title=title, bg=bg, fg=fg, class_=class_, **kwargs)

    monkeypatch.setattr(shiny.ui, "sidebar", old_sidebar)
    _app_ui._sidebar("Layers", "x")
    assert seen == [{}]
