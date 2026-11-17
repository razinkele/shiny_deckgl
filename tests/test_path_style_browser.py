"""path_style_extension() options work in the pinned deck.gl.

deck.gl 9.4 deprecated ``highPrecisionDash`` (for ``dashMode``) and only
honours ``getOffset`` when the extension is built with ``offset: true`` --
the helper used to send the former and never the latter, so ``getOffset``
was silently inert. This draws a horizontal path in real deck.gl and checks
where its pixels land.
"""

from __future__ import annotations

import io

import pytest

pytestmark = pytest.mark.browser


def _chromium_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("playwright") is not None


requires_browser = pytest.mark.skipif(
    not _chromium_available(), reason="Playwright Chromium not available"
)

# A 10 px wide red horizontal line through the centre of a 200x200 canvas.
_PAGE = """
<div id="c" style="position:absolute;left:0;top:0;width:200px;height:200px"></div>
<script>
window.renderPath = (extOpts, layerProps) => new Promise(resolve => {
  const el = document.getElementById('c');
  if (window._deck) window._deck.finalize();
  let frames = 0;
  window._deck = new deck.Deck({
    parent: el, width: 200, height: 200,
    views: new deck.OrthographicView(),
    initialViewState: {target: [0, 0, 0], zoom: 0},
    controller: false,
    layers: [new deck.PathLayer({
      id: 'p', data: [{path: [[-80, 0], [80, 0]]}],
      getPath: d => d.path, getColor: [255, 0, 0], getWidth: 10,
      widthUnits: 'pixels', billboard: false,
      extensions: [new deck.PathStyleExtension(extOpts)],
      ...layerProps,
    })],
    onAfterRender: () => { if (++frames === 2) resolve(true); },
  });
});
</script>
"""


def _red_rows(png: bytes) -> list[int]:
    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = img.size
    px = img.load()
    return [y for y in range(h)
            if any(px[x, y][0] > 200 and px[x, y][1] < 80 for x in range(w))]


@requires_browser
class TestPathStyleInDeckGL:
    @pytest.fixture(scope="class")
    def render(self):
        from playwright.sync_api import sync_playwright
        from shiny_deckgl._cdn import DECKGL_JS

        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page(viewport={"width": 200, "height": 200})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.set_content(f'<script src="{DECKGL_JS}"></script>{_PAGE}')
            page.wait_for_function("typeof deck !== 'undefined'", timeout=60000)

            def _render(ext: list, layer_props: dict) -> list[int]:
                assert ext[0] == "PathStyleExtension"
                page.evaluate("([o, p]) => window.renderPath(o, p)", [ext[1], layer_props])
                rows = _red_rows(page.locator("#c").screenshot())
                assert not errors, errors
                return rows

            try:
                yield _render
            finally:
                b.close()

    def test_offset_true_shifts_the_line(self, render):
        from shiny_deckgl import path_style_extension

        centred = render(path_style_extension(offset=True), {"getOffset": 0})
        shifted = render(path_style_extension(offset=True), {"getOffset": 3})
        assert centred and shifted
        # 3 stroke widths of a 10 px line: ~30 px sideways.
        moved = abs(sum(shifted) / len(shifted) - sum(centred) / len(centred))
        assert 20 < moved < 40, (centred, shifted)

    def test_without_offset_get_offset_is_ignored(self, render):
        """Documents why the helper must send offset: deck.gl drops getOffset."""
        from shiny_deckgl import path_style_extension

        centred = render(path_style_extension(), {"getOffset": 0})
        ignored = render(path_style_extension(), {"getOffset": 3})
        assert centred == ignored

    @pytest.mark.parametrize("mode", ["segment", "path"])
    def test_dash_modes_render_without_errors(self, render, mode):
        from shiny_deckgl import path_style_extension

        rows = render(path_style_extension(dash_mode=mode), {"getDashArray": [4, 4]})
        assert rows
