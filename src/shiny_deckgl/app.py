"""Comprehensive shiny_deckgl demo — showcases all v0.1–v0.6 features."""

from __future__ import annotations

import json
import os
import tempfile

from shiny import App, reactive, render, Session, ui

from .ui import head_includes
from .components import (
    MapWidget,
    scatterplot_layer,
    geojson_layer,
    tile_layer,
    layer,
    CARTO_POSITRON,
    CARTO_DARK,
    CARTO_VOYAGER,
    OSM_LIBERTY,
    color_range,
    PALETTE_OCEAN,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASEMAP_CHOICES = {
    "Positron (light)": CARTO_POSITRON,
    "Dark Matter": CARTO_DARK,
    "Voyager": CARTO_VOYAGER,
    "OSM Liberty": OSM_LIBERTY,
}

_PROJECTION_CHOICES = ["mercator", "globe"]

# Sample GeoJSON for native source/layer demos
_SAMPLE_GEOJSON: dict = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Klaipeda", "population": 150000, "type": "city"},
            "geometry": {"type": "Point", "coordinates": [21.14, 55.71]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Palanga", "population": 16000, "type": "resort"},
            "geometry": {"type": "Point", "coordinates": [20.95, 55.92]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Nida", "population": 1500, "type": "resort"},
            "geometry": {"type": "Point", "coordinates": [20.86, 55.30]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Šilutė", "population": 20000, "type": "city"},
            "geometry": {"type": "Point", "coordinates": [21.48, 55.35]},
        },
    ],
}


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def app(data_provider=None) -> App:
    """Create the shiny_deckgl demo application.

    Showcases every feature introduced in Phases 1–4:

    * **Phase 1** – MapLibre v5, controls, fit_bounds, map click events
    * **Phase 2** – Native sources/layers, style mutation (paint/layout/filter)
    * **Phase 3** – Projection, terrain, popups, spatial queries, markers
    * **Phase 4** – Drawing tools, feature state, map export

    Parameters
    ----------
    data_provider
        Optional callable returning ``{"data": [[lon, lat], ...]}`` or a
        GeoJSON dict.  Falls back to sample Baltic Sea points.
    """

    map_widget = MapWidget(
        "map1",
        tooltip={"html": "<b>Point</b><br/>lon: {0}, lat: {1}"},
        view_state={
            "longitude": 21.1,
            "latitude": 55.7,
            "zoom": 8,
            "pitch": 0,
            "bearing": 0,
            "minZoom": 2,
            "maxZoom": 18,
        },
        controls=[
            {"type": "navigation", "position": "top-right"},
        ],
    )

    # -----------------------------------------------------------------------
    # UI
    # -----------------------------------------------------------------------

    app_ui = ui.page_fluid(
        head_includes(),
        ui.h2("shiny_deckgl Demo"),
        ui.layout_sidebar(
            ui.sidebar(
                # ---- Basemap & Projection ---------------------------------
                ui.accordion(
                    ui.accordion_panel(
                        "Basemap & View",
                        ui.input_select("basemap", "Basemap",
                                        choices=list(_BASEMAP_CHOICES.keys())),
                        ui.input_select("projection", "Projection",
                                        choices=_PROJECTION_CHOICES,
                                        selected="mercator"),
                        ui.input_action_button("fit_baltic",
                                               "Fit to Baltic Sea"),
                        ui.output_text_verbatim("viewport_info"),
                    ),
                    # ---- Controls -----------------------------------------
                    ui.accordion_panel(
                        "Controls",
                        ui.input_switch("ctl_scale", "Scale bar", value=False),
                        ui.input_switch("ctl_fullscreen", "Fullscreen",
                                        value=False),
                    ),
                    # ---- Layers -------------------------------------------
                    ui.accordion_panel(
                        "Layers",
                        ui.input_action_button("refresh", "Refresh Data"),
                        ui.input_switch("show_wms",
                                        "EMODnet Bathymetry (WMS)",
                                        value=False),
                        ui.input_switch("show_points",
                                        "deck.gl Scatter Points",
                                        value=True),
                        ui.hr(),
                        ui.p("Native MapLibre layer"),
                        ui.input_switch("show_native",
                                        "Show cities layer", value=False),
                        ui.input_slider("circle_radius",
                                        "Circle radius", 4, 20, 8),
                        ui.input_select("filter_type", "Filter by type",
                                        choices=["all", "city", "resort"],
                                        selected="all"),
                        ui.input_slider("paint_opacity",
                                        "Fill opacity", 0.1, 1.0, 0.7,
                                        step=0.1),
                    ),
                    # ---- Markers & Popups ---------------------------------
                    ui.accordion_panel(
                        "Markers & Popups",
                        ui.input_action_button("add_klaipeda_marker",
                                               "Add Klaipėda marker"),
                        ui.input_action_button("add_palanga_marker",
                                               "Add Palanga marker"),
                        ui.input_action_button("clear_all_markers",
                                               "Clear all markers"),
                        ui.hr(),
                        ui.input_action_button("place_drag_marker",
                                               "Place legacy drag marker"),
                        ui.h6("Marker click"),
                        ui.output_text_verbatim("marker_click_info"),
                        ui.h6("Marker drag"),
                        ui.output_text_verbatim("marker_drag_info"),
                    ),
                    # ---- Drawing ------------------------------------------
                    ui.accordion_panel(
                        "Drawing Tools",
                        ui.input_action_button("enable_draw",
                                               "Enable drawing"),
                        ui.input_action_button("disable_draw",
                                               "Disable drawing"),
                        ui.input_action_button("get_drawn",
                                               "Get drawn features"),
                        ui.input_action_button("delete_drawn",
                                               "Delete all drawn"),
                        ui.h6("Draw mode"),
                        ui.output_text_verbatim("draw_mode_info"),
                        ui.h6("Drawn features"),
                        ui.output_text_verbatim("drawn_features_info"),
                    ),
                    # ---- Interaction & Queries ----------------------------
                    ui.accordion_panel(
                        "Interaction",
                        ui.h6("deck.gl click"),
                        ui.output_text_verbatim("click_info"),
                        ui.h6("Map click (anywhere)"),
                        ui.output_text_verbatim("map_click_info"),
                        ui.h6("Feature click (native layer)"),
                        ui.output_text_verbatim("feature_click_info"),
                        ui.h6("Hover"),
                        ui.output_text_verbatim("hover_info"),
                        ui.h6("Spatial query result"),
                        ui.output_text_verbatim("query_result_info"),
                    ),
                    # ---- Export -------------------------------------------
                    ui.accordion_panel(
                        "Export",
                        ui.input_action_button("export_png",
                                               "Export PNG screenshot"),
                        ui.input_action_button("export_html",
                                               "Export HTML"),
                        ui.h6("Export status"),
                        ui.output_text_verbatim("export_info"),
                    ),
                    open=["Basemap & View"],
                ),
                width=340,
            ),
            map_widget.ui(height="85vh"),
        ),
    )

    # -----------------------------------------------------------------------
    # Server
    # -----------------------------------------------------------------------

    def server(input, output, session: Session):
        _last_layers: reactive.Value[list[dict]] = reactive.Value([])
        _native_added: reactive.Value[bool] = reactive.Value(False)

        # ---- Outputs ------------------------------------------------------

        @render.text
        def viewport_info():
            vs = input[map_widget.view_state_input_id]()
            if vs is None:
                return "Pan / zoom to update…"
            return (
                f"lon: {vs.get('longitude', 0):.4f}\n"
                f"lat: {vs.get('latitude', 0):.4f}\n"
                f"zoom: {vs.get('zoom', 0):.2f}\n"
                f"pitch: {vs.get('pitch', 0):.1f}\n"
                f"bearing: {vs.get('bearing', 0):.1f}"
            )

        @render.text
        def click_info():
            d = input[map_widget.click_input_id]()
            if d is None:
                return "Click a deck.gl point…"
            return (
                f"Layer: {d.get('layerId')}\n"
                f"Coords: {d.get('coordinate')}\n"
                f"Object: {d.get('object')}"
            )

        @render.text
        def map_click_info():
            d = input[map_widget.map_click_input_id]()
            if d is None:
                return "Click anywhere on the map…"
            return (
                f"lon: {d.get('longitude', 0):.5f}\n"
                f"lat: {d.get('latitude', 0):.5f}"
            )

        @render.text
        def feature_click_info():
            d = input[map_widget.feature_click_input_id]()
            if d is None:
                return "Click a native layer feature…"
            props = d.get("properties", {})
            return (
                f"Layer: {d.get('layerId')}\n"
                f"Name: {props.get('name')}\n"
                f"Pop: {props.get('population')}"
            )

        @render.text
        def hover_info():
            d = input[map_widget.hover_input_id]()
            if d is None:
                return "Hover a deck.gl point…"
            return (
                f"Layer: {d.get('layerId')}\n"
                f"Coords: {d.get('coordinate')}"
            )

        @render.text
        def marker_click_info():
            d = input[map_widget.marker_click_input_id]()
            if d is None:
                return "Click a marker…"
            return (
                f"Marker: {d.get('markerId')}\n"
                f"lon: {d.get('longitude', 0):.5f}\n"
                f"lat: {d.get('latitude', 0):.5f}"
            )

        @render.text
        def marker_drag_info():
            d = input[map_widget.marker_drag_input_id]()
            if d is None:
                return "Drag a marker…"
            return (
                f"Marker: {d.get('markerId')}\n"
                f"lon: {d.get('longitude', 0):.6f}\n"
                f"lat: {d.get('latitude', 0):.6f}"
            )

        @render.text
        def draw_mode_info():
            d = input[map_widget.draw_mode_input_id]()
            return d or "(drawing not active)"

        @render.text
        def drawn_features_info():
            d = input[map_widget.drawn_features_input_id]()
            if d is None:
                return "(none)"
            feats = d.get("features", []) if isinstance(d, dict) else []
            return f"{len(feats)} feature(s)\n{json.dumps(d, indent=2)[:500]}"

        @render.text
        def query_result_info():
            d = input[map_widget.query_result_input_id]()
            if d is None:
                return "Run a spatial query…"
            feats = d.get("features", [])
            return (
                f"Request: {d.get('requestId')}\n"
                f"Found: {len(feats)} feature(s)\n"
                f"{json.dumps(feats[:3], indent=2)[:400]}"
            )

        @render.text
        def export_info():
            d = input[map_widget.export_result_input_id]()
            if d is None:
                return "Click 'Export PNG'…"
            url = d.get("dataUrl", "")
            return (
                f"Request: {d.get('requestId')}\n"
                f"Size: {d.get('width')}×{d.get('height')}\n"
                f"Data URL: {url[:80]}…"
            )

        # ---- Initial setup ------------------------------------------------

        @reactive.Effect
        async def _initial_push():
            await _build_and_push()

        # ---- Basemap switching --------------------------------------------

        @reactive.Effect
        @reactive.event(input.basemap)
        async def _on_basemap():
            style = _BASEMAP_CHOICES[input.basemap()]
            await map_widget.set_style(session, style)

        # ---- Projection ---------------------------------------------------

        @reactive.Effect
        @reactive.event(input.projection)
        async def _on_projection():
            await map_widget.set_projection(session, input.projection())

        # ---- Controls -----------------------------------------------------

        @reactive.Effect
        @reactive.event(input.ctl_scale)
        async def _toggle_scale():
            if input.ctl_scale():
                await map_widget.add_control(
                    session, "scale", "bottom-left",
                    options={"unit": "metric"})
            else:
                await map_widget.remove_control(session, "scale")

        @reactive.Effect
        @reactive.event(input.ctl_fullscreen)
        async def _toggle_fullscreen():
            if input.ctl_fullscreen():
                await map_widget.add_control(
                    session, "fullscreen", "top-left")
            else:
                await map_widget.remove_control(session, "fullscreen")

        # ---- Fit bounds ---------------------------------------------------

        @reactive.Effect
        @reactive.event(input.fit_baltic)
        async def _fit_baltic():
            await map_widget.fit_bounds(
                session,
                [[9, 53], [31, 66]],
                padding=40,
                duration=1500,
            )

        # ---- deck.gl layers -----------------------------------------------

        @reactive.Effect
        @reactive.event(input.refresh, input.show_wms)
        async def _on_control_change():
            await _build_and_push()

        @reactive.Effect
        @reactive.event(input.show_points)
        async def _toggle_points():
            await map_widget.set_layer_visibility(
                session, {"layer1": input.show_points()})

        # ---- Native MapLibre source & layer -------------------------------

        @reactive.Effect
        @reactive.event(input.show_native)
        async def _toggle_native():
            if input.show_native():
                await map_widget.add_source(session, "cities", {
                    "type": "geojson",
                    "data": _SAMPLE_GEOJSON,
                })
                await map_widget.add_maplibre_layer(session, {
                    "id": "cities-circle",
                    "type": "circle",
                    "source": "cities",
                    "paint": {
                        "circle-radius": input.circle_radius(),
                        "circle-color": "#0088cc",
                        "circle-opacity": input.paint_opacity(),
                        "circle-stroke-color": "#fff",
                        "circle-stroke-width": 2,
                    },
                })
                await map_widget.add_popup(
                    session, "cities-circle",
                    "<b>{name}</b><br/>Population: {population}<br/>Type: {type}",
                )
                _native_added.set(True)
            else:
                await map_widget.remove_popup(session, "cities-circle")
                await map_widget.remove_maplibre_layer(session, "cities-circle")
                await map_widget.remove_source(session, "cities")
                _native_added.set(False)

        # ---- Style mutation (paint / filter) on native layer ---------------

        @reactive.Effect
        @reactive.event(input.circle_radius)
        async def _on_radius():
            if _native_added.get():
                await map_widget.set_paint_property(
                    session, "cities-circle",
                    "circle-radius", input.circle_radius())

        @reactive.Effect
        @reactive.event(input.paint_opacity)
        async def _on_opacity():
            if _native_added.get():
                await map_widget.set_paint_property(
                    session, "cities-circle",
                    "circle-opacity", input.paint_opacity())

        @reactive.Effect
        @reactive.event(input.filter_type)
        async def _on_filter():
            if _native_added.get():
                val = input.filter_type()
                if val == "all":
                    await map_widget.set_filter(session, "cities-circle", None)
                else:
                    await map_widget.set_filter(
                        session, "cities-circle",
                        ["==", ["get", "type"], val])

        # ---- Markers (named, Phase 3) ------------------------------------

        @reactive.Effect
        @reactive.event(input.add_klaipeda_marker)
        async def _add_klaipeda():
            await map_widget.add_marker(
                session, "klaipeda", 21.14, 55.71,
                color="#e63946", draggable=True,
                popup_html="<b>Klaipėda</b><br/>Port city")

        @reactive.Effect
        @reactive.event(input.add_palanga_marker)
        async def _add_palanga():
            await map_widget.add_marker(
                session, "palanga", 20.95, 55.92,
                color="#457b9d", draggable=False,
                popup_html="<b>Palanga</b><br/>Beach resort")

        @reactive.Effect
        @reactive.event(input.clear_all_markers)
        async def _clear_markers():
            await map_widget.clear_markers(session)

        @reactive.Effect
        @reactive.event(input.place_drag_marker)
        async def _place_drag_marker():
            await map_widget.add_drag_marker(session)

        # ---- Spatial queries on map click ---------------------------------

        @reactive.Effect
        @reactive.event(input[map_widget.map_click_input_id])
        async def _on_map_click_query():
            d = input[map_widget.map_click_input_id]()
            if d is None or not _native_added.get():
                return
            await map_widget.query_at_lnglat(
                session,
                d["longitude"], d["latitude"],
                layers=["cities-circle"],
                request_id="click-query",
            )

        # ---- Drawing tools (Phase 4) -------------------------------------

        @reactive.Effect
        @reactive.event(input.enable_draw)
        async def _enable_draw():
            await map_widget.enable_draw(
                session,
                controls={
                    "point": True,
                    "line_string": True,
                    "polygon": True,
                    "trash": True,
                },
            )

        @reactive.Effect
        @reactive.event(input.disable_draw)
        async def _disable_draw():
            await map_widget.disable_draw(session)

        @reactive.Effect
        @reactive.event(input.get_drawn)
        async def _get_drawn():
            await map_widget.get_drawn_features(session)

        @reactive.Effect
        @reactive.event(input.delete_drawn)
        async def _delete_drawn():
            await map_widget.delete_drawn_features(session)

        # ---- Export (Phase 4) --------------------------------------------

        @reactive.Effect
        @reactive.event(input.export_png)
        async def _export_png():
            await map_widget.export_image(
                session, format="png", request_id="demo-screenshot")

        @reactive.Effect
        @reactive.event(input.export_html)
        async def _export_html():
            path = os.path.join(
                tempfile.gettempdir(), "shiny_deckgl_export.html")
            map_widget.to_html(_last_layers.get(), path=path)
            ui.notification_show(f"Exported to {path}", type="message")

        # ---- Build & push deck.gl layers ----------------------------------

        async def _build_and_push():
            payload = (data_provider() if data_provider
                       else {"data": [[21.12, 55.70], [21.15, 55.72]]})

            data = payload.get("data", [])
            is_geojson = isinstance(data, dict) and data.get("type") in [
                "FeatureCollection", "Feature",
            ]

            layers = []

            # WMS tile layer
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

            # Scatter / GeoJSON layer
            ocean_colors = color_range(1, PALETTE_OCEAN)
            fill_color = list(ocean_colors[0])

            if is_geojson:
                layers.append(geojson_layer("layer1", data))
            else:
                layers.append(
                    scatterplot_layer(
                        "layer1", data,
                        getFillColor=fill_color,
                        radiusMinPixels=6,
                    )
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
