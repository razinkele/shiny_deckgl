"""on_viewport_change with a counting loader, for test_e2e_viewport.py."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, on_viewport_change

m = MapWidget("vmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("ping", "Ping"),
    ui.output_text("pong"),
    ui.output_text("calls"),
    ui.input_numeric("dep", "Dependency", 0),
    m.ui(height="300px"),
)


def server(input, output, session):
    n_calls = reactive.Value(0)
    last_dep = reactive.Value(None)

    @on_viewport_change(m, input, session, debounce_ms=500)
    async def _load(bounds, zoom):
        # Reading an input inside the loader makes it a dependency.
        dep = input.dep()
        with reactive.isolate():
            n_calls.set(n_calls.get() + 1)
            last_dep.set(dep)
        return []

    @render.text
    def pong():
        return f"pong {input.ping()}"

    @render.text
    def calls():
        return f"calls={n_calls.get()} dep={last_dep.get()}"


app = App(app_ui, server)
