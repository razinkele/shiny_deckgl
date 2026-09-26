"""An animated TripsLayer patched while it plays, for test_e2e_trips.py."""
from shiny import App, reactive, ui

from shiny_deckgl import MapWidget, head_includes, trips_layer

m = MapWidget("tmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 7})

TRIPS = [{
    "path": [[21.0 + i * 0.01, 55.7] for i in range(100)],
    "timestamps": list(range(0, 1000, 10)),
}]

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("trail", "Change trail"),
    ui.input_action_button("speed", "Double speed"),
    ui.input_action_button("reset", "Reset"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [trips_layer(
            "trips", TRIPS, trailLength=50,
            _tripsAnimation={"loopLength": 1000, "speed": 10},
        )])

    @reactive.effect
    @reactive.event(input.trail)
    async def _trail():
        await m.partial_update(session, [{"id": "trips", "trailLength": 80}])

    @reactive.effect
    @reactive.event(input.speed)
    async def _speed():
        await m.partial_update(session, [{
            "id": "trips", "_tripsAnimation": {"loopLength": 1000, "speed": 20},
        }])

    @reactive.effect
    @reactive.event(input.reset)
    async def _reset():
        await m.trips_control(session, "reset")


app = App(app_ui, server)
