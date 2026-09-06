"""Every widget helper must resolve to a real deck.gl class.

`buildWidgets` looked up `deck[name] || deck['_' + name]` — it could add a
leading underscore but never strip one. deck.gl has since promoted several
widgets from experimental (`_InfoWidget`) to stable (`InfoWidget`), so the
helpers that still emit the underscored name resolved to nothing and were
dropped with only a console warning. Six of eighteen helpers were dead.

Verified against deck.gl 9.3.6, 9.3.11 and 9.4.0: the exported widget set is
identical in all three, so this is long-standing, not a version regression.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from _js_harness import extract_function, requires_node, run_js

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[1]
WIDGETS_PY = ROOT / "src" / "shiny_deckgl" / "widgets.py"

#: Helpers deck.gl provides no class for, in any supported version.
#: Asserted explicitly so that a future deck.gl release adding them is noticed.
KNOWN_UNAVAILABLE = {"_FpsWidget", "_ViewSelectorWidget"}

#: Resolved by shiny_deckgl itself, not by deck.gl.
CUSTOM = {"_DeckLayerLegendWidget"}


def emitted_widget_classes() -> set[str]:
    src = WIDGETS_PY.read_text(encoding="utf-8")
    return set(re.findall(r'"@@widgetClass":\s*"([^"]+)"', src))


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            b.close()
        return True
    except Exception:
        return False


requires_browser = pytest.mark.skipif(
    not _chromium_available(), reason="Playwright Chromium not available"
)


@requires_node
class TestResolverHandlesBothNamings:
    """The resolver must cope with a widget being experimental or stable."""

    @staticmethod
    def _prelude(available):
        decls = ", ".join(f"{n!r}: function () {{}}" for n in available)
        return (
            f"const deck = {{{decls}}};\n"
            + extract_function("resolveWidgetClass")
        )

    def test_stable_name_resolves_when_helper_asks_for_experimental(self):
        got = run_js(self._prelude(["InfoWidget"]),
                     "typeof resolveWidgetClass(deck, '_InfoWidget')")
        assert got == "function"

    def test_experimental_name_resolves_when_helper_asks_for_stable(self):
        got = run_js(self._prelude(["_ScaleWidget"]),
                     "typeof resolveWidgetClass(deck, 'ScaleWidget')")
        assert got == "function"

    def test_exact_name_still_wins(self):
        got = run_js(self._prelude(["ZoomWidget"]),
                     "typeof resolveWidgetClass(deck, 'ZoomWidget')")
        assert got == "function"

    def test_genuinely_absent_widget_returns_nothing(self):
        got = run_js(self._prelude(["ZoomWidget"]),
                     "resolveWidgetClass(deck, 'NoSuchWidget') || null")
        assert got is None


@requires_browser
class TestEveryHelperResolvesInDeckGL:
    @pytest.fixture(scope="class")
    def resolution(self):
        from playwright.sync_api import sync_playwright
        from shiny_deckgl._cdn import DECKGL_JS, DECKGL_WIDGETS_JS

        js = (ROOT / "src" / "shiny_deckgl" / "resources" / "deckgl-init.js").read_text(
            encoding="utf-8")
        names = sorted(emitted_widget_classes())
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page()
            try:
                page.set_content(
                    f'<script src="{DECKGL_JS}"></script>'
                    f'<script src="{DECKGL_WIDGETS_JS}"></script>'
                    "<script>window.Shiny={setInputValue(){},"
                    "addCustomMessageHandler(){}};</script>"
                    f"<script>{js}</script>")
                page.wait_for_function("typeof deck !== 'undefined'", timeout=60000)
                page.wait_for_timeout(1500)
                return page.evaluate(
                    "(names => Object.fromEntries(names.map(n =>"
                    " [n, typeof window.__deckgl_resolveWidgetClass(deck, n)])))",
                    names,
                )
            finally:
                b.close()

    def test_all_available_helpers_resolve(self, resolution):
        unresolved = {
            n for n, t in resolution.items()
            if t != "function" and n not in KNOWN_UNAVAILABLE | CUSTOM
        }
        assert not unresolved, f"widget helpers that resolve to nothing: {sorted(unresolved)}"

    def test_the_unavailable_list_is_still_accurate(self, resolution):
        """If deck.gl ships these, drop them from KNOWN_UNAVAILABLE."""
        now_available = {n for n in KNOWN_UNAVAILABLE
                         if resolution.get(n) == "function"}
        assert not now_available, (
            f"deck.gl now provides {sorted(now_available)} — remove them from "
            "KNOWN_UNAVAILABLE and update the docstrings")

    def test_the_helper_set_is_what_we_think_it_is(self):
        assert len(emitted_widget_classes()) == 18
