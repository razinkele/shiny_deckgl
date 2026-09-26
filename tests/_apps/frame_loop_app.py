"""Trips (with head icons) + @@animate + a binary layer on one map.

For test_e2e_frame_loop.py.
"""
import numpy as np
from shiny import App, reactive, ui

from shiny_deckgl import (
    MapWidget, animate_prop, encode_binary_attribute, head_includes,
    scatterplot_layer, trips_layer,
)
from shiny_deckgl.ibm import ICON_ATLAS, ICON_MAPPING

m = MapWidget("fmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 7})

TRIPS = [{
    "path": [[21.0 + i * 0.01, 55.7] for i in range(100)],
    "timestamps": list(range(0, 10000, 100)),
    "species": "Grey seal",
}]
POS = np.array([[21.0, 55.6], [21.2, 55.8]], dtype="float32")

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("pause", "Pause"),
    ui.input_action_button("trail", "Patch trail"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [
            trips_layer(
                "trips", TRIPS, trailLength=200,
                _tripsAnimation={"loopLength": 10000, "speed": 50},
                _tripsHeadIcons={"iconAtlas": ICON_ATLAS, "iconMapping": ICON_MAPPING,
                                 "iconField": "species"},
            ),
            scatterplot_layer("spin", [[21.1, 55.7]], getPosition="@@d", getRadius=3000,
                              radiusScale=animate_prop("r", speed=20, range_min=1, range_max=1e6)),
            scatterplot_layer("bin", {"length": 2}, getPosition=encode_binary_attribute(POS),
                              getRadius=2000),
        ])

    @reactive.effect
    @reactive.event(input.pause)
    async def _pause():
        await m.trips_control(session, "pause")

    @reactive.effect
    @reactive.event(input.trail)
    async def _trail():
        await m.partial_update(session, [{"id": "trips", "trailLength": 300}])


app = App(app_ui, server)
