"""MapWidget.rpc() from a reactive.extended_task: view state, features, image."""
from shiny import App, reactive, render, ui

from shiny_deckgl import MapWidget, head_includes, scatterplot_layer

m = MapWidget("rmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("ask", "Ask the map"),
    ui.input_action_button("shot", "Screenshot"),
    ui.input_action_button("ask_effect", "Ask from an effect"),
    ui.output_text("answer"),
    ui.output_text("shot_size"),
    ui.output_text("effect_out"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [scatterplot_layer(
            "pts", [[21.1, 55.7]], getPosition="@@d", getRadius=20000, getFillColor=[255, 0, 0],
        )])

    @reactive.extended_task
    async def ask_map():
        vs = await m.get_view_state(session)
        feats = await m.get_features(session, lnglat=[vs["longitude"], vs["latitude"]])
        return f"zoom={vs['zoom']:.1f} bounds={'sw' in vs['bounds']} features={len(feats)}"

    @reactive.effect
    @reactive.event(input.ask)
    def _ask():
        ask_map()

    @render.text
    def answer():
        return ask_map.result()

    @reactive.extended_task
    async def screenshot():
        return len(await m.get_image(session))

    @reactive.effect
    @reactive.event(input.shot)
    def _shot():
        screenshot()

    @render.text
    def shot_size():
        return f"bytes={screenshot.result()}"

    # Shiny >= 1.9 only: awaited in a plain effect (refused on < 1.9).
    effect_answer = reactive.Value("")

    @reactive.effect
    @reactive.event(input.ask_effect)
    async def _ask_effect():
        try:
            vs = await m.get_view_state(session)
            effect_answer.set(f"effect zoom={vs['zoom']:.1f}")
        except Exception as e:  # noqa: BLE001 - shown to the test
            effect_answer.set(f"effect error={type(e).__name__}")

    @render.text
    def effect_out():
        return effect_answer()


app = App(app_ui, server)
