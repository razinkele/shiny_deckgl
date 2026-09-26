"""update() with an SVG icon atlas, then an immediate visibility change.

deck_update preloads SVG atlases asynchronously before it renders. For
test_e2e_render_race.py (J5, 2026-09-26 review).
"""
import urllib.parse

from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, icon_layer, scatterplot_layer

m = MapWidget("race", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<circle cx="32" cy="32" r="28" fill="red"/></svg>')
ATLAS = "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(_SVG)
MAPPING = {"dot": {"x": 0, "y": 0, "width": 64, "height": 64, "mask": False}}

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("go", "Update, then hide 'pts'"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [])

    @reactive.effect
    @reactive.event(input.go)
    async def _go():
        await m.update(session, [
            scatterplot_layer("pts", [[21.1, 55.7]], getPosition="@@d", getRadius=5000),
            icon_layer("icons", [{"p": [21.2, 55.8]}], getPosition="@@=d.p",
                       getIcon="@@='dot'", getSize=32,
                       iconAtlas=ATLAS, iconMapping=MAPPING),
        ])
        # Arrives while the atlas above is still being rasterised.
        await m.set_layer_visibility(session, {"pts": False})


app = App(app_ui, server)
