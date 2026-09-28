"""Two maps in two tabs, to force and recover from WebGL context loss."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer, zoom_widget

a = MapWidget("amap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})
b = MapWidget("bmap", view_state={"longitude": 24.9, "latitude": 60.2, "zoom": 5})

app_ui = ui.page_fluid(
    head_includes(),
    ui.output_text("events"),
    ui.navset_tab(
        ui.nav_panel("A", a.ui(height="300px"), value="tab_a"),
        ui.nav_panel("B", b.ui(height="300px"), value="tab_b"),
        id="tabs",
    ),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await a.update(session, [scatterplot_layer("pts", [[21.1, 55.7]], getPosition="@@d", getRadius=20000,
                                                   getFillColor=[255, 0, 0])], widgets=[zoom_widget()])
        await b.update(session, [scatterplot_layer("pts_b", [[24.9, 60.2]], getPosition="@@d", getRadius=20000,
                                                   getFillColor=[0, 0, 255])])

    _log = reactive.Value([])

    for w in (a, b):
        def _make(widget):
            @reactive.effect
            @reactive.event(input[widget.reconnected_input_id])
            def _():
                ev = input[widget.reconnected_input_id]()
                _log.set(_log.get() + [f"{widget.id}:{ev.get('reason', 'reconnect')}"])
        _make(w)

    @render.text
    def events():
        return " ".join(_log.get()) or "none"


app = App(app_ui, server)
