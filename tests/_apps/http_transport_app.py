"""A ~3 MB layer that update(transport="auto") sends over HTTP, then a patch."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer

m = MapWidget("hmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})
N = 200_000   # ~3.1 MB of JSON -- above the 2 MB auto threshold (120k was 1.87 MB)

app_ui = ui.page_fluid(head_includes(), ui.input_action_button("patch", "Patch"), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        pts = [[21.0 + (i % 400) * 0.002, 55.0 + (i // 400) * 0.002] for i in range(N)]
        await m.update(session, [scatterplot_layer("big", pts, getPosition="@@d", getRadius=200,
                                                   getFillColor=[255, 0, 0])])
        # A layer patch right behind the fetched update must apply after it.
        await m.partial_update(session, [{"id": "big", "getRadius": 999}])

    @reactive.effect
    @reactive.event(input.patch)
    async def _patch():
        await m.partial_update(session, [{"id": "big", "getRadius": 4242}])


app = App(app_ui, server)
