"""Adds a native source + layer on demand, for test_e2e_style_queue.py."""
from shiny import App, reactive, ui

from shiny_deckgl import CARTO_DARK as DARK
from shiny_deckgl import CARTO_POSITRON as POSITRON
from shiny_deckgl import MapWidget, head_includes, legend_control

m = MapWidget(
    "smap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6},
    controls=[legend_control(show_default=True)],
)

POINTS = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {},
     "geometry": {"type": "Point", "coordinates": [21.1, 55.7]}},
]}

app_ui = ui.page_fluid(
    head_includes(),
    ui.input_action_button("add", "Add layer"),
    ui.input_action_button("restyle", "Swap basemap, re-add layer"),
    ui.input_action_button("same", "Re-apply current basemap, re-add layer"),
    m.ui(height="300px"),
)


def server(input, output, session):
    @reactive.effect
    async def _init():
        await m.update(session, [])

    @reactive.effect
    @reactive.event(input.add)
    async def _add():
        n = input.add()
        await m.add_source(session, f"pts-{n}", {"type": "geojson", "data": POINTS})
        await m.add_maplibre_layer(session, {
            "id": f"pts-circle-{n}", "type": "circle", "source": f"pts-{n}",
            "paint": {"circle-radius": 8, "circle-color": "#e00"},
        })

    @reactive.effect
    @reactive.event(input.same)
    async def _same():
        # The map starts on Positron; setting it again must still settle.
        n = input.same()
        await m.set_style(session, POSITRON)
        await m.add_source(session, f"same-{n}", {"type": "geojson", "data": POINTS})
        await m.add_maplibre_layer(session, {
            "id": f"same-circle-{n}", "type": "circle", "source": f"same-{n}",
            "paint": {"circle-radius": 8, "circle-color": "#0a0"},
        })

    @reactive.effect
    @reactive.event(input.restyle)
    async def _restyle():
        n = input.restyle()
        style = DARK if n % 2 else POSITRON
        await m.set_style(session, style)
        await m.add_source(session, f"re-{n}", {"type": "geojson", "data": POINTS})
        await m.add_maplibre_layer(session, {
            "id": f"re-circle-{n}", "type": "circle", "source": f"re-{n}",
            "paint": {"circle-radius": 8, "circle-color": "#00e"},
        })


app = App(app_ui, server)
