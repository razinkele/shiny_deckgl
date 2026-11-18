"""A map whose deck.gl widgets use built-in themes in light and dark mode."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, zoom_widget

m = MapWidget("tmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 5},
              widget_theme="light-glass", dark_widget_theme="dark")

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("plain", "Plain"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [], widgets=[zoom_widget()])

    @reactive.effect
    @reactive.event(input.plain)
    async def _plain():
        await m.set_widget_theme(session, None)


app = App(app_ui, server)
