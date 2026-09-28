"""Bookmarking: the camera and a hidden layer survive a bookmark URL."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer

m = MapWidget("bmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5})


def app_ui(request):
    return ui.page_fluid(
        head_includes(),
        ui.input_action_button("hide", "Hide buoys"),
        ui.input_action_button("save", "Bookmark"),
        ui.output_text("url"),
        m.ui(height="300px"),
    )


def server(input, output, session):
    m.enable_bookmarking(session)

    @reactive.effect
    async def _init():
        await m.update(session, [
            scatterplot_layer("ports", [[21.1, 55.7]], getPosition="@@d", getRadius=20000, getFillColor=[255, 0, 0]),
            scatterplot_layer("buoys", [[21.3, 55.9]], getPosition="@@d", getRadius=20000, getFillColor=[0, 0, 255]),
        ])

    @reactive.effect
    @reactive.event(input.hide)
    async def _hide():
        await m.set_layer_visibility(session, {"buoys": False})

    _url = reactive.Value("")

    @reactive.effect
    @reactive.event(input.save)
    async def _save():
        _url.set(await session.bookmark.get_bookmark_url() or "")

    @render.text
    def url():
        return _url.get()


app = App(app_ui, server, bookmark_store="url")
