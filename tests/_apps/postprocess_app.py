"""A grey circle drawn with a brightnessContrast PostProcessEffect."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, post_process_effect, scatterplot_layer

m = MapWidget("pmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5})

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_numeric("brightness", "Brightness", 0.0),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _draw():
        await m.update(
            session,
            [scatterplot_layer("dot", [[21.1, 55.7]], getPosition="@@d",
                               getRadius=150000, getFillColor=[100, 100, 100])],
            effects=[post_process_effect("brightnessContrast",
                                         brightness=input.brightness(), contrast=0)],
        )


app = App(app_ui, server)
