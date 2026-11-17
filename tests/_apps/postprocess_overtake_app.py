"""An update with a first-use effect, overtaken at once by a layers-only update."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, post_process_effect, scatterplot_layer

m = MapWidget("omap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5})

app_ui = ui.page_fluid(head_includes(), ui.input_action_button("go", "Go"),
                       m.ui(height="300px"))


def _dot(layer_id):
    return scatterplot_layer(layer_id, [[21.1, 55.7]], getPosition="@@d",
                             getRadius=150000, getFillColor=[100, 100, 100])


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [_dot("start")])

    # After start-up, so neither message is deferred (deferred updates are
    # merged before the map exists, which hides the race).
    @reactive.effect
    @reactive.event(input.go)
    async def _go():
        # The vignette module is imported on first use, so this update waits...
        await m.update(session, [_dot("first")], effects=[post_process_effect("vignette")])
        # ...and this one (effects omitted, which keeps them) overtakes it.
        await m.update(session, [_dot("second")])


app = App(app_ui, server)
