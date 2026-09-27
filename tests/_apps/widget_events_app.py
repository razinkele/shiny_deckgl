"""Real deck.gl widgets whose state changes should arrive as a Shiny input."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, timeline_widget, toggle_widget

m = MapWidget("wmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

app_ui = ui.page_fluid(head_includes(), ui.output_text("last"), m.ui(height="300px"))


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [], widgets=[
            timeline_widget(id="tl", timeRange=[0, 100], initialTime=10, placement="bottom-left"),
            # top-left: top-right is under MapLibre's navigation control
            toggle_widget("layers", id="tg", placement="top-left"),
        ])

    @render.text
    def last():
        ev = input[m.widget_event_input_id]()
        return f"{ev['id']}:{ev['event']}:{ev['value']}" if ev else "none"


app = App(app_ui, server)
