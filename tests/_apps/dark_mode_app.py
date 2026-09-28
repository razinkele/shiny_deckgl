"""A map with a dark_style that follows ui.input_dark_mode()."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer, zoom_widget
from shiny_deckgl.colors import CARTO_DARK

m = MapWidget("dmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5},
              dark_style=CARTO_DARK)

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_dark_mode(id="mode", mode="light"),
    ui.output_text("reported"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [scatterplot_layer("pts", [[21.1, 55.7]], getPosition="@@d",
                                                   getRadius=20000, getFillColor=[255, 0, 0])],
                       widgets=[zoom_widget()])

    @render.text
    def reported():
        v = input[m.dark_mode_input_id]
        if not v.is_set():
            return "none"
        d = v()
        return f"dark={d['dark']} style={d['style']}"


app = App(app_ui, server)
