"""A map with a SplitterWidget and a widget whose props deck.gl rejects."""
from shiny import App, reactive, ui

from shiny_deckgl import (MapWidget, head_includes, scatterplot_layer, splitter_widget,
                          zoom_widget)

m = MapWidget("smap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5})

app_ui = ui.page_fluid(head_includes(), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(
            session,
            [scatterplot_layer("pts", [[21.1, 55.7]], getPosition="@@d",
                               getRadius=20000, getFillColor=[255, 0, 0])],
            widgets=[
                splitter_widget(orientation="vertical"),
                # The deck.gl 9.3 shape: no viewLayout, so the 9.4 constructor throws.
                {"@@widgetClass": "_SplitterWidget", "id": "broken", "orientation": "vertical"},
                zoom_widget(),
            ],
        )


app = App(app_ui, server)
