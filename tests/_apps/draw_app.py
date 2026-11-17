"""A map with MapboxDraw enabled at start-up."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes

m = MapWidget("dmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5})

app_ui = ui.page_fluid(head_includes(), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [])
        await m.enable_draw(session)


app = App(app_ui, server)
