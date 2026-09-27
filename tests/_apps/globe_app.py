"""A deck.gl layer on a map that switches to globe projection."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer

m = MapWidget("gmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 3})

app_ui = ui.page_fluid(head_includes(), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [scatterplot_layer(
            "pts", [[21.1, 55.7]], getPosition="@@d", getRadius=200000,
            getFillColor=[255, 0, 0], pickable=True,
        )])


app = App(app_ui, server)
