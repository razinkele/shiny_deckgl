"""A map with a dark_style that follows ui.input_dark_mode(), plus one without."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer, zoom_widget
from shiny_deckgl.colors import CARTO_DARK, CARTO_VOYAGER

m = MapWidget("dmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5},
              dark_style=CARTO_DARK)
# No dark_style: a dark-mode switch must leave its basemap alone.
p = MapWidget("pmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5})

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_dark_mode(id="mode", mode="light"),
    ui.input_action_button("voyager", "Voyager"),
    ui.output_text("reported"),
    m.ui(height="300px"),
    p.ui(height="200px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [scatterplot_layer("pts", [[21.1, 55.7]], getPosition="@@d",
                                                   getRadius=20000, getFillColor=[255, 0, 0])],
                       widgets=[zoom_widget()])
        await p.update(session, [])

    @reactive.effect
    @reactive.event(input.voyager)
    async def _voyager():
        await m.set_style(session, CARTO_VOYAGER)
        await p.set_style(session, CARTO_VOYAGER)

    @render.text
    def reported():
        v = input[m.dark_mode_input_id]
        if not v.is_set():
            return "none"
        d = v()
        return f"dark={d['dark']} style={d['style']}"


app = App(app_ui, server)
