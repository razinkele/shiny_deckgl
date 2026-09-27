"""Two layers and a layer legend with checkboxes, for a real click on a checkbox."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, layer_legend_widget, scatterplot_layer

m = MapWidget("lmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

app_ui = ui.page_fluid(head_includes(), ui.output_text("last"), m.ui(height="400px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [
            scatterplot_layer("ports", [[21.1, 55.7]], getPosition="@@d", getRadius=20000,
                              getFillColor=[255, 0, 0]),
            scatterplot_layer("buoys", [[21.3, 55.9]], getPosition="@@d", getRadius=20000,
                              getFillColor=[0, 0, 255]),
        ], widgets=[layer_legend_widget(
            placement="bottom-right", title="Active Layers",
            show_checkbox=True, auto_introspect=True,
        )])

    @render.text
    def last():
        ev = input[m.legend_visibility_input_id]()
        return f"{ev['layer_id']}:{ev['visible']}" if ev else "none"


app = App(app_ui, server)
