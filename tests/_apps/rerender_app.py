"""Minimal app whose map lives inside render.ui, for test_e2e_rerender.py."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer

m = MapWidget("rmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("rerender", "Re-render"),
    ui.output_ui("holder"),
)


def server(input, output, session):
    @render.ui
    def holder():
        input.rerender()
        return m.ui(height="300px")

    @reactive.effect
    @reactive.event(input.rerender, ignore_none=False)
    async def _push():
        await m.update(session, [scatterplot_layer(
            "pts", [[21.1, 55.7]], getPosition="@@d",
            getRadius=5000, getFillColor=[255, 0, 0],
        )])


app = App(app_ui, server)
