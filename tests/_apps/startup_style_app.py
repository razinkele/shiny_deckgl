"""Map in a hidden tab gets set_style + native layers at start-up.

Mirrors the demo's MapLibre tab: the messages are deferred while the tab is
hidden and replayed when the map is created, so set_style() arrives while the
initial style is still loading. For test_e2e_style_queue.py.
"""
from shiny import App, reactive, ui

from shiny_deckgl import CARTO_POSITRON as POSITRON
from shiny_deckgl import MapWidget, head_includes

m = MapWidget("tmap", view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 6})

POINTS = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {},
     "geometry": {"type": "Point", "coordinates": [21.1, 55.7]}},
]}

app_ui = ui.page_fluid(
    head_includes(),
    ui.navset_tab(
        ui.nav_panel("First", ui.p("nothing here")),
        ui.nav_panel("Map", m.ui(height="300px")),
    ),
)


def server(input, output, session):
    @reactive.effect
    async def _startup():
        await m.update(session, [])
        await m.add_source(session, "pts", {"type": "geojson", "data": POINTS})
        await m.add_maplibre_layer(session, {
            "id": "pts-circle", "type": "circle", "source": "pts",
            "paint": {"circle-radius": 8, "circle-color": "#e00"},
        })
        # A basemap effect without ignore_init re-applies the same style and
        # then re-adds the layers, as the demo did.
        await m.set_style(session, POSITRON)
        await m.add_source(session, "pts2", {"type": "geojson", "data": POINTS})
        await m.add_maplibre_layer(session, {
            "id": "pts2-circle", "type": "circle", "source": "pts2",
            "paint": {"circle-radius": 5, "circle-color": "#00e"},
        })


app = App(app_ui, server)
