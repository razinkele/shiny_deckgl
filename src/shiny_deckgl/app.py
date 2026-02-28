import os
import tempfile

from shiny import App, ui, reactive, Session, render
from .ui import head_includes
from .components import (
    MapWidget,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    CARTO_POSITRON,
    CARTO_DARK,
    color_range,
    PALETTE_OCEAN,
)


_BASEMAP_CHOICES = {
    "Positron (light)": CARTO_POSITRON,
    "Dark Matter": CARTO_DARK,
}


def app(data_provider=None) -> App:
    """Create the shiny_deckgl demo application.

    Showcases tooltips, hover/click events, viewport read-back, basemap
    switching, WMS overlay toggling, layer visibility, draggable markers,
    and color-scale utilities.

    Parameters
    ----------
    data_provider
        Optional callable returning ``{"data": [[lon, lat], ...]}`` or a
        GeoJSON dict.  Falls back to a single ``[[0, 0]]`` point.
    """
    map_widget = MapWidget(
        "map1",
        tooltip={"html": "<b>Point</b><br/>lon: {0}, lat: {1}"},
        view_state={"longitude": 21.1, "latitude": 55.7, "zoom": 8, "minZoom": 2, "maxZoom": 18},
    )

    app_ui = ui.page_fluid(
        head_includes(),
        ui.h2("shiny_deckgl Demo"),
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_action_button("refresh", "Refresh Data"),
                ui.hr(),
                ui.input_select(
                    "basemap",
                    "Basemap",
                    choices=list(_BASEMAP_CHOICES.keys()),
                ),
                ui.hr(),
                ui.input_switch("show_wms", "Show EMODnet Bathymetry (WMS)", value=False),
                ui.input_switch("show_points", "Show points layer", value=True),
                ui.hr(),
                ui.input_action_button("place_marker", "Place drag marker"),
                ui.input_action_button("export_html", "Export HTML"),
                ui.h4("Drag marker position"),
                ui.output_text_verbatim("drag_info"),
                ui.hr(),
                ui.h4("Clicked Item"),
                ui.output_text_verbatim("click_info"),
                ui.hr(),
                ui.h4("Hover"),
                ui.output_text_verbatim("hover_info"),
                ui.hr(),
                ui.h4("Current Viewport"),
                ui.output_text_verbatim("viewport_info"),
                width=300,
            ),
            map_widget.ui(height="80vh"),
        ),
    )

    def server(input, output, session: Session):
        _last_layers: reactive.Value[list[dict]] = reactive.Value([])

        @render.text
        def click_info():
            click_data = input[map_widget.click_input_id]()
            if click_data is None:
                return "Click a point to see info..."
            return (
                f"Layer: {click_data.get('layerId')}\n"
                f"Coords: {click_data.get('coordinate')}\n"
                f"Object: {click_data.get('object')}"
            )

        @render.text
        def hover_info():
            hover_data = input[map_widget.hover_input_id]()
            if hover_data is None:
                return "Hover a point..."
            return (
                f"Layer: {hover_data.get('layerId')}\n"
                f"Coords: {hover_data.get('coordinate')}"
            )

        @render.text
        def viewport_info():
            vs = input[map_widget.view_state_input_id]()
            if vs is None:
                return "Pan / zoom to update..."
            return (
                f"lon: {vs.get('longitude', 0):.4f}\n"
                f"lat: {vs.get('latitude', 0):.4f}\n"
                f"zoom: {vs.get('zoom', 0):.2f}\n"
                f"pitch: {vs.get('pitch', 0):.1f}\n"
                f"bearing: {vs.get('bearing', 0):.1f}"
            )

        @render.text
        def drag_info():
            pos = input[map_widget.drag_input_id]()
            if pos is None:
                return "Place a marker first..."
            return (
                f"lon: {pos.get('longitude', 0):.6f}\n"
                f"lat: {pos.get('latitude', 0):.6f}"
            )

        # Trigger an initial render as soon as the session connects
        @reactive.Effect
        async def _initial_push():
            await _build_and_push()

        @reactive.Effect
        @reactive.event(input.refresh, input.show_wms)
        async def _on_control_change():
            await _build_and_push()

        # Layer visibility toggle (points layer)
        @reactive.Effect
        @reactive.event(input.show_points)
        async def _toggle_points():
            await map_widget.set_layer_visibility(
                session, {"layer1": input.show_points()}
            )

        # Drag marker placement
        @reactive.Effect
        @reactive.event(input.place_marker)
        async def _place_drag_marker():
            await map_widget.add_drag_marker(session)

        # HTML export
        @reactive.Effect
        @reactive.event(input.export_html)
        async def _export_html():
            path = os.path.join(tempfile.gettempdir(), "shiny_deckgl_export.html")
            map_widget.to_html(_last_layers.get(), path=path)
            # Use ui.notification to inform the user
            ui.notification_show(f"Exported to {path}", type="message")

        async def _build_and_push():
            payload = data_provider() if data_provider else {"data": [[0, 0]]}

            # Convert legacy payload format into module payload
            data = payload.get("data", [])
            is_geojson = isinstance(data, dict) and data.get("type") in [
                "FeatureCollection",
                "Feature",
            ]

            layers = []

            # Add WMS layer if switched on
            if input.show_wms():
                wms_url = (
                    "https://ows.emodnet-bathymetry.eu/wms?"
                    "SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
                    "&FORMAT=image/png&TRANSPARENT=true"
                    "&LAYERS=emodnet:mean_atlas_land"
                    "&CRS=EPSG:3857&WIDTH=256&HEIGHT=256"
                    "&BBOX={bbox-epsg-3857}"
                )
                layers.append(tile_layer("emodnet-bathy", wms_url))

            # Use ocean color palette for scatter points
            ocean_colors = color_range(1, PALETTE_OCEAN)
            fill_color = list(ocean_colors[0])

            if is_geojson:
                layers.append(geojson_layer("layer1", data))
            else:
                layers.append(
                    scatterplot_layer("layer1", data, getFillColor=fill_color)
                )

            view_state = None
            if isinstance(data, list) and len(data) > 0:
                try:
                    lon, lat = data[0]
                    view_state = {"longitude": lon, "latitude": lat, "zoom": 5}
                except (TypeError, ValueError):
                    pass

            await map_widget.update(session, layers, view_state)
            _last_layers.set(layers)

    return App(app_ui, server)
