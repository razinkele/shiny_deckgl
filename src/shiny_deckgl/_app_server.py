"""Server function for the demo application.

This module contains the server() function that handles all server-side logic
for the comprehensive shiny_deckgl demo application.
"""

from __future__ import annotations

import json
import os
import random
import tempfile
from typing import Any

# Module-level imports needed by server function
from ._data_utils import encode_binary_attribute
from .widgets import (
    zoom_widget,
    compass_widget,
    fullscreen_widget,
    scale_widget,
    gimbal_widget,
    reset_view_widget,
    screenshot_widget,
    fps_widget,
    loading_widget,
    theme_widget,
    timeline_widget,
    geocoder_widget,
    context_menu_widget,
    info_widget,
    splitter_widget,
    stats_widget,
    view_selector_widget,
    layer_legend_widget,
)
from ._transitions import transition
from .controls import (
    geolocate_control,
    globe_control,
    terrain_control,
    legend_control,
    opacity_control,
    deck_legend_control,
)

from .effects import (
    ambient_light,
    point_light,
    directional_light,
    lighting_effect,
    post_process_effect,
)

from .colors import (
    CARTO_POSITRON,
    color_range,
    color_bins,
    color_quantiles,
    PALETTE_VIRIDIS,
)

from ._demo_data import (
    PORTS,
    ROUTES,
    MPA_GEOJSON,
    EMODNET_WMS_URL,
    BASEMAP_CHOICES,
    PALETTE_CHOICES,
    BALTIC_VIEW,
    make_arc_data,
    make_heatmap_points,
    make_path_data,
    make_port_data_simple,
    make_port_geojson,
    make_trips_data,
    make_bathymetry_grid,
    make_fish_observations,
    make_3d_arc_data,
    SHYFEM_VIEW,
    make_h3_data,
    make_point_cloud_data,
    make_shyfem_polygon_data,
    make_shyfem_mesh_data,
    CURONIAN_GRD_PATH as _CURONIAN_GRD_STR,
    POLYGON_GRD_PATH as _POLYGON_GRD_STR,
    fish_species_color as _species_color,
    make_gallery_port_data,
    make_gallery_arc_data,
    make_gallery_line_data,
    make_gallery_path_data,
    make_gallery_text_data,
    make_gallery_icon_data,
    make_gallery_column_data,
    make_seal_trips,
    make_seal_trips_ibm,
    make_seal_haulout_data,
    make_seal_foraging_areas,
    # New layer data generators (v1.6.0)
    make_grid_cell_data,
    make_lithuanian_bathymetry_data,
    make_solid_polygon_data,
    make_a5_data,
    make_geohash_data,
    make_h3_cluster_data,
    make_quadkey_data,
    make_s2_data,
    make_scenegraph_data,
)
from .ibm import ICON_ATLAS, ICON_MAPPING, trips_animation_server
from .colors import depth_color as _bathy_color

from .extensions import (
    brushing_extension,
    data_filter_extension,
)

# Widget instances
from ._app_widgets import (
    gallery_widget,
    maplibre_widget,
    events_widget,
    palette_widget,
    adv_widget,
    draw_widget,
    three_d_widget,
    seal_widget,
    widgets_gallery_widget,
)

def server(input: Any, output: Any, session: "Session"):  # type: ignore[name-defined]
    # local imports deferred until app startup
    from shiny import reactive, render  # imported here to keep top-level light
    from .layers import (
        layer,
        scatterplot_layer,
        geojson_layer,
        tile_layer,
        bitmap_layer,
        arc_layer,
        icon_layer,
        path_layer,
        line_layer,
        text_layer,
        column_layer,
        polygon_layer,
        heatmap_layer,
        hexagon_layer,
        h3_hexagon_layer,
        trips_layer,
        great_circle_layer,
        contour_layer,
        grid_layer,
        screen_grid_layer,
        mvt_layer,
        wms_layer,
        point_cloud_layer,
        simple_mesh_layer,
        terrain_layer,
        custom_geometry,
        # New layers (v1.6.0)
        grid_cell_layer,
        solid_polygon_layer,
        a5_layer,
        geohash_layer,
        h3_cluster_layer,
        quadkey_layer,
        s2_layer,
        tile_3d_layer,
        scenegraph_layer,
        COORDINATE_SYSTEM,
    )

    # Shared reactive stores
    _adv_layers: reactive.Value[list[dict]] = reactive.Value([])
    _export_log: reactive.Value[str] = reactive.Value("")
    _advanced_log: reactive.Value[str] = reactive.Value("")

    # -- Pre-computed static data (generated once per session) ----------
    _arc_data = make_arc_data()
    _heatmap_points = make_heatmap_points(300)
    _path_data = make_path_data()
    _port_data_simple = make_port_data_simple()
    _cargo_values = [float(p["cargo_mt"]) for p in PORTS]

    # -- Shared helpers ---------------------------------------------------

    # =================================================================
    # Tab 1 — deck.gl Layers  (gallery — basemap + navigation)
    # =================================================================

    # Basemap switching (gallery widget on Tab 1)
    @reactive.Effect
    @reactive.event(input.basemap)
    async def _switch_basemap():
        style_url = BASEMAP_CHOICES.get(input.basemap(), CARTO_POSITRON)
        await gallery_widget.set_style(session, style_url)

    # Fly-to / ease-to transitions (gallery widget on Tab 1)
    @reactive.Effect
    @reactive.event(input.fly_klaipeda)
    async def _fly_klaipeda():
        await gallery_widget.fly_to(session, 21.13, 55.71, zoom=10, speed=1.5)

    @reactive.Effect
    @reactive.event(input.ease_stockholm)
    async def _ease_stockholm():
        await gallery_widget.ease_to(
            session, 18.07, 59.33, zoom=10, duration=2000,
        )

    @reactive.Effect
    @reactive.event(input.fly_baltic)
    async def _fly_baltic():
        await gallery_widget.fly_to(
            session, 19.5, 57.0, zoom=5, pitch=0, bearing=0,
        )

    # =================================================================
    # Tab 2 — MapLibre Controls
    # =================================================================

    async def _ml_add_native_layers():
        """Add native MapLibre sources + layers for MPAs and ports.

        Native layers render correctly in globe projection and are
        visible to the legend / opacity plugins (unlike deck.gl overlays).
        """
        # --- MPA polygons (GeoJSON source + fill + line layers) ---
        await maplibre_widget.add_source(session, "mpa-source", {
            "type": "geojson",
            "data": MPA_GEOJSON,
        })
        await maplibre_widget.add_maplibre_layer(session, {
            "id": "mpa-fill",
            "type": "fill",
            "source": "mpa-source",
            "paint": {
                "fill-color": "rgba(0, 180, 120, 0.25)",
                "fill-outline-color": "rgba(0, 180, 120, 0.8)",
            },
        })
        await maplibre_widget.add_maplibre_layer(session, {
            "id": "mpa-line",
            "type": "line",
            "source": "mpa-source",
            "paint": {
                "line-color": "rgba(0, 180, 120, 0.8)",
                "line-width": 2,
            },
        })
        # --- Port circles (GeoJSON source + circle layer) ---
        await maplibre_widget.add_source(session, "ports-source", {
            "type": "geojson",
            "data": make_port_geojson(),
        })
        await maplibre_widget.add_maplibre_layer(session, {
            "id": "ports-circle",
            "type": "circle",
            "source": "ports-source",
            "paint": {
                "circle-radius": 7,
                "circle-color": "rgba(0, 140, 200, 0.8)",
                "circle-stroke-color": "#fff",
                "circle-stroke-width": 1,
            },
        })

    @reactive.Effect
    async def _ml_init():
        """Push initial native layers + controls to the MapLibre tab."""
        # Send an empty deck.gl update so the overlay is initialised
        await maplibre_widget.update(session, [])
        # Add native MapLibre layers (globe-safe, legend/opacity visible)
        await _ml_add_native_layers()
        controls = _build_ml_controls()
        await maplibre_widget.set_controls(session, controls)

    def _build_ml_controls() -> list[dict]:
        """Build the list of MapLibre controls from sidebar switches."""
        ctrls: list[dict] = []
        if input.ml_navigation():
            ctrls.append({
                "type": "navigation",
                "position": "top-right",
                "options": {},
            })
        if input.ml_geolocate():
            ctrls.append(geolocate_control(
                position="top-right",
                trackUserLocation=True,
            ))
        if input.ml_globe():
            ctrls.append(globe_control(position="top-right"))
        if input.ml_terrain():
            ctrls.append(terrain_control(position="top-right"))
        if input.ml_legend():
            ctrls.append(legend_control(
                targets={
                    "mpa-fill": "Marine Protected Areas",
                    "ports-circle": "Baltic Ports",
                },
                position="bottom-left",
                show_default=input.ml_legend_default(),
                show_checkbox=input.ml_legend_checkbox(),
                only_rendered=False,
            ))
        if input.ml_opacity():
            ctrls.append(opacity_control(
                position="top-left",
                over_layers={
                    "mpa-fill": "Marine Protected Areas",
                    "ports-circle": "Baltic Ports",
                },
            ))
        return ctrls

    # Re-build controls when any toggle changes
    @reactive.Effect
    @reactive.event(
        input.ml_navigation, input.ml_geolocate,
        input.ml_globe, input.ml_terrain,
        input.ml_legend, input.ml_legend_checkbox,
        input.ml_legend_default, input.ml_opacity,
    )
    async def _ml_controls_rebuild():
        controls = _build_ml_controls()
        await maplibre_widget.set_controls(session, controls)

    # Basemap switching — re-add native layers after style swap
    @reactive.Effect
    @reactive.event(input.ml_basemap)
    async def _ml_switch_basemap():
        style_url = BASEMAP_CHOICES.get(
            input.ml_basemap(), CARTO_POSITRON,
        )
        await maplibre_widget.set_style(session, style_url)
        # set_style removes all sources/layers; re-add ours
        await _ml_add_native_layers()
        # Re-apply controls so legend picks up the fresh layers
        controls = _build_ml_controls()
        await maplibre_widget.set_controls(session, controls)

    # Drag marker (MapLibre tab)
    @reactive.Effect
    @reactive.event(input.ml_place_marker)
    async def _ml_place_drag():
        await maplibre_widget.add_drag_marker(session)

    @render.text
    def ml_drag_info():
        pos = input[maplibre_widget.drag_input_id]()
        if pos is None:
            return "Place a marker first\u2026"
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    # Clusters (merged from former Tab 10)
    @reactive.Effect
    @reactive.event(input.v1_show_clusters, input.v1_cluster_radius)
    async def _v1_clusters():
        if input.v1_show_clusters():
            await maplibre_widget.add_cluster_layer(
                session,
                "v1-clusters",
                make_port_geojson(),
                cluster_radius=input.v1_cluster_radius(),
                cluster_color="#14919b",
                point_color="#e65100",
                point_radius=6,
            )
        else:
            await maplibre_widget.remove_cluster_layer(session, "v1-clusters")

    @reactive.Effect
    @reactive.event(input.v1_cooperative)
    async def _v1_cooperative():
        await maplibre_widget.set_cooperative_gestures(
            session, input.v1_cooperative()
        )

    # =================================================================
    # Tab 3 — Events & Tooltips
    # =================================================================

    @reactive.Effect
    async def _events_init():
        """Push interactive layers to the events map."""
        layers = [
            geojson_layer(
                "ev-mpa", MPA_GEOJSON,
                getFillColor=[0, 180, 120, 60],
                getLineColor=[0, 180, 120, 200],
                lineWidthMinPixels=2,
                pickable=True,
            ),
            layer(
                "ArcLayer", "ev-arcs",
                data=_arc_data,
                getSourcePosition="@@=d.sourcePosition",
                getTargetPosition="@@=d.targetPosition",
                getSourceColor="@@=d.sourceColor",
                getTargetColor="@@=d.targetColor",
                getWidth=2, pickable=True,
            ),
            scatterplot_layer(
                "ev-ports", _port_data_simple,
                getPosition="@@=d.position",
                getFillColor=[200, 0, 80, 180],
                radiusMinPixels=8, pickable=True,
            ),
        ]
        await events_widget.update(session, layers)
        await events_widget.set_controls(session, [
            deck_legend_control(
                entries=[
                    {"layer_id": "ev-mpa", "label": "Marine Protected Areas",
                     "color": [0, 180, 120, 60], "shape": "rect"},
                    {"layer_id": "ev-arcs", "label": "Port connections",
                     "color": [255, 140, 0], "color2": [200, 0, 80],
                     "shape": "arc"},
                    {"layer_id": "ev-ports", "label": "Baltic Ports",
                     "color": [200, 0, 80, 180], "shape": "circle"},
                ],
                title="Events Layers",
            ),
        ])

    # Dynamic tooltip customisation
    @reactive.Effect
    @reactive.event(
        input.tooltip_template, input.tooltip_bg, input.tooltip_fg,
        ignore_init=True,
    )
    async def _update_tooltip():
        template = input.tooltip_template()
        if not template.strip():
            await events_widget.update_tooltip(session, None)
            return
        await events_widget.update_tooltip(session, {
            "html": template,
            "style": {
                "backgroundColor": input.tooltip_bg(),
                "color": input.tooltip_fg(),
                "fontSize": "13px",
            },
        })

    # Drag marker (events map)
    @reactive.Effect
    @reactive.event(input.events_marker)
    async def _events_place_marker():
        await events_widget.add_drag_marker(session)

    @render.text
    def events_drag():
        pos = input[events_widget.drag_input_id]()
        if pos is None:
            return "Place a marker to see position\u2026"
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    @render.text
    def events_drag2():
        pos = input[events_widget.drag_input_id]()
        if pos is None:
            return "No drag marker placed."
        return (
            f"lon: {pos.get('longitude', 0):.6f}\n"
            f"lat: {pos.get('latitude', 0):.6f}"
        )

    # Event readback outputs
    @render.text
    def click_info():
        data = input[events_widget.click_input_id]()
        if data is None:
            return "Click a port or arc on the map\u2026"
        obj_str = json.dumps(data.get("object"), indent=2, default=str)
        return (
            f"Layer:  {data.get('layerId')}\n"
            f"Coords: {data.get('coordinate')}\n"
            f"Object: {obj_str}"
        )

    @render.text
    def hover_info():
        data = input[events_widget.hover_input_id]()
        if data is None:
            return "Hover over a feature\u2026"
        return (
            f"Layer: {data.get('layerId')}\n"
            f"Coords: [{data.get('coordinate', [0, 0])[0]:.4f}, "
            f"{data.get('coordinate', [0, 0])[1]:.4f}]"
        )

    @render.text
    def viewport_info():
        vs = input[events_widget.view_state_input_id]()
        if vs is None:
            return "Pan or zoom the map\u2026"
        return (
            f"Longitude: {vs.get('longitude', 0):.4f}\n"
            f"Latitude:  {vs.get('latitude', 0):.4f}\n"
            f"Zoom:      {vs.get('zoom', 0):.2f}\n"
            f"Pitch:     {vs.get('pitch', 0):.1f}\u00b0\n"
            f"Bearing:   {vs.get('bearing', 0):.1f}\u00b0"
        )

    # =================================================================
    # Tab 4 — Colour Scales
    # =================================================================

    # Pre-compute bathymetry grid once per session
    _pal_bathy = make_bathymetry_grid(cols=25, rows=15)
    _pal_depths = [pt["depth_m"] for pt in _pal_bathy]

    # Basemap switching for palette tab
    @reactive.Effect
    @reactive.event(input.pal_basemap)
    async def _pal_switch_basemap():
        style_url = BASEMAP_CHOICES.get(input.pal_basemap(), CARTO_POSITRON)
        await palette_widget.set_style(session, style_url)

    @reactive.Calc
    def _pal_colors() -> list[list[int]]:
        """Compute per-point colours from current palette settings."""
        pal = PALETTE_CHOICES.get(input.pal_name(), PALETTE_VIRIDIS)
        n = input.pal_nbins()
        mode = input.pal_mode()
        if mode == "bins":
            return color_bins(_pal_depths, n_bins=n, palette=pal)
        elif mode == "quantiles":
            return color_quantiles(_pal_depths, n_bins=n, palette=pal)
        else:  # "range" — assign N-colour linear ramp via bins
            return color_bins(_pal_depths, n_bins=n, palette=pal)

    @reactive.Calc
    def _pal_range_colors() -> list[list[int]]:
        """Compute the swatch colours (N evenly-spaced stops)."""
        pal = PALETTE_CHOICES.get(input.pal_name(), PALETTE_VIRIDIS)
        return color_range(input.pal_nbins(), palette=pal)

    # Swatch preview
    @render.ui
    def pal_swatch():
        colours = _pal_range_colors()
        cells = []
        for i, c in enumerate(colours):
            hex_col = f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
            cells.append(
                ui.tags.div(
                    style=(
                        f"display:inline-block;width:32px;height:24px;"
                        f"background:{hex_col};border:1px solid #666;"
                        f"border-radius:3px;margin:1px;"
                    ),
                    title=f"Stop {i+1}: rgb({c[0]}, {c[1]}, {c[2]})",
                )
            )
        return ui.div(
            ui.tags.div(
                *cells,
                style="display:flex;flex-wrap:wrap;gap:2px;margin-bottom:6px;",
            ),
            ui.tags.small(
                f"{len(colours)} stops from {input.pal_name()} palette",
                style="color:#888;",
            ),
        )

    # Stats output
    @render.text
    def pal_stats():
        colours = _pal_colors()
        n = input.pal_nbins()
        mode_label = {
            "bins": "color_bins (equal-width)",
            "quantiles": "color_quantiles (equal-count)",
            "range": "color_range (linear interpolation)",
        }.get(input.pal_mode(), input.pal_mode())

        lo, hi = min(_pal_depths), max(_pal_depths)
        unique_cols = len(set(tuple(c) for c in colours))
        return (
            f"Palette:    {input.pal_name()}\n"
            f"Mode:       {mode_label}\n"
            f"Bins/stops: {n}\n"
            f"Data range: {lo:.1f} \u2013 {hi:.1f} m\n"
            f"Points:     {len(_pal_bathy)}\n"
            f"Unique colours assigned: {unique_cols}"
        )

    # Code example output
    @render.text
    def pal_code():
        mode = input.pal_mode()
        pal_name = input.pal_name().upper()
        pal_const = f"PALETTE_{pal_name}" if pal_name != "CHLOROPHYLL" else "PALETTE_CHLOROPHYLL"
        n = input.pal_nbins()
        if mode == "bins":
            return (
                f"from shiny_deckgl import color_bins, {pal_const}\n\n"
                f"depths = [10.5, 45.2, 120.0, 250.3, \u2026]\n"
                f"colors = color_bins(depths, n_bins={n}, palette={pal_const})\n"
                f"# \u2192 one [R, G, B, A] per depth value"
            )
        elif mode == "quantiles":
            return (
                f"from shiny_deckgl import color_quantiles, {pal_const}\n\n"
                f"depths = [10.5, 45.2, 120.0, 250.3, \u2026]\n"
                f"colors = color_quantiles(depths, n_bins={n}, palette={pal_const})\n"
                f"# \u2192 one [R, G, B, A] per value (equal-count bins)"
            )
        else:
            return (
                f"from shiny_deckgl import color_range, {pal_const}\n\n"
                f"colors = color_range(n={n}, palette={pal_const})\n"
                f"# \u2192 {n} evenly-spaced [R, G, B, A] colours"
            )

    # Push palette-coloured layers to the palette map
    @reactive.Effect
    @reactive.event(
        input.pal_name, input.pal_mode, input.pal_nbins,
        input.pal_layer,
    )
    async def _pal_update_map():
        colours = _pal_colors()
        lo, hi = min(_pal_depths), max(_pal_depths)
        layer_type = input.pal_layer()

        # Build coloured data
        coloured_data = []
        for pt, c in zip(_pal_bathy, colours):
            bin_idx = int((pt["depth_m"] - lo) / max(hi - lo, 1) * (input.pal_nbins() - 1))
            bin_idx = max(0, min(bin_idx, input.pal_nbins() - 1))
            coloured_data.append({
                **pt,
                "color": c,
                "bin_label": f"Bin {bin_idx + 1}/{input.pal_nbins()}",
            })

        layers: list[dict] = []

        if layer_type == "columns":
            layers.append(column_layer(
                "pal-columns", coloured_data,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor="@@=d.color",
                radius=20000,
                elevationScale=1,
                extruded=True,
                pickable=True,
            ))
        elif layer_type == "scatter":
            layers.append(scatterplot_layer(
                "pal-scatter", coloured_data,
                getPosition="@@=d.position",
                getFillColor="@@=d.color",
                getRadius="@@=d.depth_m * 5",
                radiusMinPixels=4,
                radiusMaxPixels=25,
                pickable=True,
            ))
        else:  # heatmap (ignores palette — uses its own gradient)
            layers.append(layer(
                "HeatmapLayer", "pal-heat",
                data=coloured_data,
                getPosition="@@=d.position",
                getWeight="@@=d.depth_m",
                radiusPixels=40,
                intensity=1,
                threshold=0.05,
                pickable=False,
            ))

        # Build legend entries from swatch colours
        swatch = _pal_range_colors()
        legend_entries = []
        for i, c in enumerate(swatch):
            # Compute approximate depth range for label
            bin_lo = lo + (hi - lo) * i / len(swatch)
            bin_hi = lo + (hi - lo) * (i + 1) / len(swatch)
            legend_entries.append({
                "layer_id": f"pal-bin-{i}",
                "label": f"{bin_lo:.0f}\u2013{bin_hi:.0f} m",
                "color": c[:3],
                "shape": "rect",
            })

        widgets = [
            zoom_widget(), compass_widget(),
            fullscreen_widget(), scale_widget(),
        ]

        await palette_widget.update(
            session, layers, widgets=widgets,
            transition_duration=600,
        )
        await palette_widget.set_controls(
            session,
            [deck_legend_control(
                entries=legend_entries,
                position="bottom-right",
                title=f"{input.pal_name()} \u2014 {input.pal_mode()}",
                show_checkbox=False,
                collapsed=False,
            )],
        )

    # =================================================================
    # Tab 5 — Advanced
    # =================================================================

    def _adv_base_layers() -> list[dict]:
        """3-D cargo columns — good for demonstrating lighting effects."""
        column_data = [
            {
                "position": [float(p["lon"]), float(p["lat"])],
                "elevation": float(p["cargo_mt"]) * 200,
                "name": p["name"],
                "cargo_mt": float(p["cargo_mt"]),
                "color": [0, 160, 230, 200],
            }
            for p in PORTS
        ]
        return [
            column_layer(
                "cargo-columns",
                data=column_data,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor="@@=d.color",
                diskResolution=12,
                radius=15000,
                extruded=True,
                pickable=True,
            ),
        ]

    @reactive.Effect
    async def _adv_init():
        layers = _adv_base_layers()
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        await adv_widget.set_controls(session, [
            deck_legend_control(
                entries=[
                    {"layer_id": "cargo-columns", "label": "Cargo (3D columns)",
                     "color": [0, 160, 230, 200], "shape": "rect"},
                ],
                title="Advanced Layers",
            ),
        ])

    # Lighting
    @reactive.Effect
    @reactive.event(
        input.enable_lighting, input.ambient, input.point_intensity,
    )
    async def _apply_lighting():
        layers = _adv_layers.get()
        effects = None
        if input.enable_lighting():
            amb = ambient_light(intensity=input.ambient())
            pl = point_light(
                position=[19.5, 57.0, 80000],
                color=(255, 255, 220),
                intensity=input.point_intensity(),
            )
            le = lighting_effect(amb, pl)
            effects = [le]
            _advanced_log.set(
                f"Lighting ON\n"
                f"  Ambient intensity: {input.ambient()}\n"
                f"  Point light intensity: {input.point_intensity()}\n"
                f"  Point light position: [19.5, 57.0, 80000]"
            )
        else:
            _advanced_log.set("Lighting OFF")
        await adv_widget.update(session, layers, effects=effects)

    # Binary transport (numpy)
    @reactive.Effect
    @reactive.event(input.push_binary)
    async def _push_binary():
        try:
            import numpy as np

            lons = np.linspace(10.0, 30.0, 50, dtype="float32")
            lats = np.linspace(53.0, 62.0, 50, dtype="float32")
            grid_lon, grid_lat = np.meshgrid(lons, lats)
            positions = np.column_stack([
                grid_lon.ravel(), grid_lat.ravel(),
            ]).astype("float32")
            binary_pos = encode_binary_attribute(positions)

            binary_lyr = layer(
                "ScatterplotLayer", "binary-scatter",
                data={"length": len(positions)},
                getPosition=binary_pos,
                getFillColor=[255, 100, 50, 200],
                radiusMinPixels=3, radiusMaxPixels=8, pickable=False,
            )

            layers = [
                lyr for lyr in _adv_layers.get()
                if lyr.get("id") != "binary-scatter"
            ] + [binary_lyr]
            _adv_layers.set(layers)
            await adv_widget.update(session, layers)
            _advanced_log.set(
                f"Binary transport layer pushed!\n"
                f"  Points: {len(positions):,}\n"
                f"  Array dtype: {positions.dtype}\n"
                f"  Array shape: {positions.shape}\n"
                f"  Base64 payload: {len(binary_pos['value']):,} chars"
            )
        except ImportError:
            _advanced_log.set(
                "numpy is not installed.\n"
                "Install with: micromamba install -n shiny numpy"
            )

    # Extensions (DataFilterExtension)

    # Pre-compute filter data (static; only filterRange changes)
    _filtered_port_data = [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "cargo_mt": p["cargo_mt"],
            "filterValue": p["cargo_mt"],
        }
        for p in PORTS
    ]

    def _make_filtered_layer(max_cargo: float) -> dict:
        """Build a DataFilterExtension scatterplot layer."""
        return layer(
            "ScatterplotLayer", "filtered-ports",
            data=_filtered_port_data,
            getPosition="@@=d.position",
            getFillColor=[255, 200, 0, 220],
            getRadius=8, radiusScale=1000, radiusMinPixels=20,
            pickable=True,
            extensions=["DataFilterExtension"],
            getFilterValue="@@=d.filterValue",
            filterRange=[0, max_cargo],
            parameters={"depthCompare": "always"},
        )

    @reactive.Effect
    @reactive.event(input.push_filtered)
    async def _push_filtered():
        max_cargo = input.filter_value()
        filtered_lyr = _make_filtered_layer(max_cargo)
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") != "filtered-ports"
        ] + [filtered_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        visible = sum(1 for p in PORTS if p["cargo_mt"] <= max_cargo)
        _advanced_log.set(
            f"DataFilterExtension layer pushed!\n"
            f"  Filter range: [0, {max_cargo}] Mt\n"
            f"  Ports visible: {visible}/{len(PORTS)}\n"
            f"  Extension: DataFilterExtension"
        )

    @reactive.Effect
    @reactive.event(input.filter_value)
    async def _update_filter():
        """Re-push the filtered layer when the slider changes."""
        layers = _adv_layers.get()
        if not any(lyr.get("id") == "filtered-ports" for lyr in layers):
            return
        max_cargo = input.filter_value()
        filtered_lyr = _make_filtered_layer(max_cargo)
        new_layers = [
            lyr for lyr in layers if lyr.get("id") != "filtered-ports"
        ] + [filtered_lyr]
        _adv_layers.set(new_layers)
        await adv_widget.update(session, new_layers)

    @render.text
    def advanced_status():
        return (
            _advanced_log.get()
            or "Use the controls to test advanced features\u2026"
        )

    # Transition demo (v0.8.0)
    @reactive.Effect
    @reactive.event(input.push_transitions)
    async def _push_transitions():
        """Push a scatterplot layer with animated transitions."""
        port_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "radius": max(5, p["cargo_mt"] / 2) * (1 + random.random()),
                "color": [
                    random.randint(50, 255),
                    random.randint(50, 255),
                    random.randint(50, 200),
                    200,
                ],
            }
            for p in PORTS
        ]
        animated_lyr = scatterplot_layer(
            "animated-ports",
            data=port_data,
            getPosition="@@=d.position",
            getFillColor="@@=d.color",
            getRadius="@@=d.radius",
            radiusScale=1000,
            radiusMinPixels=6,
            radiusMaxPixels=40,
            pickable=True,
            transitions={
                "getRadius": transition(800, easing="ease-in-out-cubic"),
                "getFillColor": transition(600, easing="ease-out-cubic"),
            },
        )
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") != "animated-ports"
        ] + [animated_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        _advanced_log.set(
            "Transition layer pushed!\n"
            "  Layer: animated-ports (ScatterplotLayer)\n"
            "  getRadius transition: 800ms ease-in-out-cubic\n"
            "  getFillColor transition: 600ms ease-out-cubic\n"
            "\nClick again to see transitions animate with new values."
        )

    # Property animation demos (v1.7.0) ---------------------------------
    from ._animation import animate_prop

    @reactive.Effect
    @reactive.event(input.push_anim_rotate)
    async def _push_anim_rotate():
        """Push an IconLayer with continuously rotating icons."""
        icon_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "layerType": "Animated Icon",
            }
            for p in PORTS
        ]
        animated_lyr = icon_layer(
            "anim-icons",
            data=icon_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPosition="@@=d.position",
            iconAtlas="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
            iconMapping={
                "marker": {"x": 0, "y": 0, "width": 128,
                           "height": 128, "anchorY": 64},
            },
            getIcon="marker",
            getSize=36,
            getAngle=animate_prop(prop="rotation", speed=90, loop=True),
            pickable=True,
        )
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") not in ("anim-icons", "anim-pulse")
        ] + [animated_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        _advanced_log.set(
            "Rotating icons pushed!\n"
            "  Layer: anim-icons (IconLayer)\n"
            "  getAngle: animate_prop(speed=90) \u2014 90\u00b0/sec\n"
            "  Animation runs client-side at 60 fps.\n"
            "\n\u23F8 Use Pause/Resume to control."
        )

    @reactive.Effect
    @reactive.event(input.push_anim_pulse)
    async def _push_anim_pulse():
        """Push a ScatterplotLayer with pulsing radius."""
        pulse_data = [
            {
                "position": [p["lon"], p["lat"]],
                "name": p["name"],
                "cargo_mt": p["cargo_mt"],
                "layerType": "Pulsing Circle",
            }
            for p in PORTS
        ]
        animated_lyr = scatterplot_layer(
            "anim-pulse",
            data=pulse_data,
            getPosition="@@=d.position",
            getFillColor=[65, 182, 196, 140],
            getLineColor=[0, 100, 120, 200],
            stroked=True,
            lineWidthMinPixels=2,
            getRadius=animate_prop(
                prop="pulse", speed=8000, loop=True,
                range_min=3000, range_max=15000,
            ),
            radiusMinPixels=4,
            radiusMaxPixels=50,
            pickable=True,
        )
        layers = [
            lyr for lyr in _adv_layers.get()
            if lyr.get("id") not in ("anim-icons", "anim-pulse")
        ] + [animated_lyr]
        _adv_layers.set(layers)
        await adv_widget.update(session, layers)
        _advanced_log.set(
            "Pulsing circles pushed!\n"
            "  Layer: anim-pulse (ScatterplotLayer)\n"
            "  getRadius: animate_prop(speed=8000, range 3k\u201315k)\n"
            "  Animation runs client-side at 60 fps.\n"
            "\n\u23F8 Use Pause/Resume to control."
        )

    @reactive.Effect
    @reactive.event(input.stop_anim)
    async def _stop_anim():
        """Pause all property animations."""
        for lid in ("anim-icons", "anim-pulse"):
            try:
                await adv_widget.set_animation(session, layer_id=lid, enabled=False)
            except Exception:
                pass
        _advanced_log.set("Animation paused.\n\u25B6 Click Resume to restart.")

    @reactive.Effect
    @reactive.event(input.resume_anim)
    async def _resume_anim():
        """Resume all property animations."""
        for lid in ("anim-icons", "anim-pulse"):
            try:
                await adv_widget.set_animation(session, layer_id=lid, enabled=True)
            except Exception:
                pass
        _advanced_log.set("Animation resumed!")

    # =================================================================
    # Tab 6 — Export & Serialisation
    # =================================================================

    @reactive.Effect
    @reactive.event(input.export_html)
    async def _do_export_html():
        layers, _names = _gl_layers()
        path = os.path.join(
            tempfile.gettempdir(), "shiny_deckgl_demo_export.html",
        )
        gallery_widget.to_html(layers, path=path, title="shiny_deckgl Export")
        fsize = os.path.getsize(path)
        _export_log.set(
            f"HTML exported successfully!\n"
            f"Path: {path}\n"
            f"Size: {fsize:,} bytes\n"
            f"Layers: {len(layers)}"
        )
        ui.notification_show(f"Exported to {path}", type="message")

    @reactive.Effect
    @reactive.event(input.export_json)
    async def _do_export_json():
        layers, _names = _gl_layers()
        spec = gallery_widget.to_json(layers)
        ellip = "\u2026" if len(spec) > 2000 else ""
        _export_log.set(
            f"JSON spec ({len(spec):,} chars):\n\n{spec[:2000]}{ellip}"
        )

    @reactive.Effect
    @reactive.event(input.roundtrip_json)
    async def _do_roundtrip():
        layers, _names = _gl_layers()
        spec_json = gallery_widget.to_json(layers)
        w2, layers2 = MapWidget.from_json(spec_json)
        checks = [
            f"Original widget id:     {gallery_widget.id}",
            f"Restored widget id:     {w2.id}",
            f"IDs match:              {gallery_widget.id == w2.id}",
            f"Style match:            {gallery_widget.style == w2.style}",
            f"View state match:       "
            f"{gallery_widget.view_state == w2.view_state}",
            f"Tooltip match:          "
            f"{gallery_widget.tooltip == w2.tooltip}",
            f"Layer count match:      "
            f"{len(layers)} == {len(layers2)}",
            f"Layer IDs (original):   "
            f"{[lyr.get('id') for lyr in layers]}",
            f"Layer IDs (restored):   "
            f"{[lyr.get('id') for lyr in layers2]}",
            "\n\u2713 JSON round-trip successful!",
        ]
        _export_log.set("\n".join(checks))

    @render.text
    def export_output():
        return _export_log.get() or "Click an export button\u2026"

    # =================================================================
    # Tab 7 — Drawing Tools & Interaction
    # =================================================================

    _draw_log = reactive.Value("")

    @reactive.Effect
    @reactive.event(input.draw_enable)
    async def _draw_enable():
        await draw_widget.enable_draw(session)
        _draw_log.set(
            _draw_log.get()
            + "\n✏️  Drawing enabled — use the toolbar on the map."
        )

    @reactive.Effect
    @reactive.event(input.draw_disable)
    async def _draw_disable():
        await draw_widget.disable_draw(session)
        _draw_log.set(_draw_log.get() + "\n❌  Drawing disabled.")

    @reactive.Effect
    @reactive.event(input.draw_get)
    async def _draw_get():
        await draw_widget.get_drawn_features(session)
        _draw_log.set(
            _draw_log.get() + "\n📋  Requesting drawn features…"
        )

    @reactive.Effect
    @reactive.event(input.draw_clear)
    async def _draw_clear():
        await draw_widget.delete_drawn_features(session)
        _draw_log.set(
            _draw_log.get() + "\n🗑️  All drawn features deleted."
        )

    # Show drawn features when they arrive
    @reactive.Effect
    @reactive.event(
        input[draw_widget.drawn_features_input_id],
    )
    def _draw_feat_arrived():
        data = input[draw_widget.drawn_features_input_id]()
        n = len(data.get("features", [])) if isinstance(data, dict) else 0
        pretty = json.dumps(data, indent=2)
        _draw_log.set(
            _draw_log.get()
            + f"\n📋  Drawn features updated — {n} feature(s):"
            + f"\n{pretty}"
        )

    # Draw mode change
    @reactive.Effect
    @reactive.event(input[draw_widget.draw_mode_input_id])
    def _draw_mode_changed():
        mode = input[draw_widget.draw_mode_input_id]()
        _draw_log.set(
            _draw_log.get()
            + f"\n🔧  Draw mode changed → {mode}"
        )

    # -- Markers & Popups -------------------------------------------------

    @reactive.Effect
    @reactive.event(input.add_port_markers)
    async def _add_port_markers():
        for p in PORTS[:5]:
            await draw_widget.add_marker(
                session,
                marker_id=p["name"],
                longitude=p["lon"],
                latitude=p["lat"],
                color="#14919b",
                draggable=True,
                popup_html=(
                    f"<b>{p['name']}</b> ({p['country']})"
                    f"<br/>Cargo: {p['cargo_mt']} Mt"
                ),
            )
        _draw_log.set(
            _draw_log.get()
            + "\n📍  Added 5 port markers (draggable, with popups)."
        )

    @reactive.Effect
    @reactive.event(input.clear_all_markers)
    async def _clear_markers():
        await draw_widget.clear_markers(session)
        _draw_log.set(_draw_log.get() + "\n🗑️  All markers cleared.")

    @reactive.Effect
    @reactive.event(input[draw_widget.marker_click_input_id])
    def _marker_clicked():
        data = input[draw_widget.marker_click_input_id]()
        _draw_log.set(
            _draw_log.get()
            + f"\n🖱️  Marker click: {data.get('markerId')} "
            + f"({data.get('longitude'):.4f}, {data.get('latitude'):.4f})"
        )

    @reactive.Effect
    @reactive.event(input[draw_widget.marker_drag_input_id])
    def _marker_dragged():
        data = input[draw_widget.marker_drag_input_id]()
        _draw_log.set(
            _draw_log.get()
            + f"\n🔄  Marker drag: {data.get('markerId')} → "
            + f"({data.get('longitude'):.4f}, {data.get('latitude'):.4f})"
        )

    # -- Spatial Query ----------------------------------------------------

    @reactive.Effect
    @reactive.event(input.query_center)
    async def _query_center():
        await draw_widget.query_rendered_features(
            session,
            point=[400, 300],
        )
        _draw_log.set(
            _draw_log.get()
            + "\n🔍  Querying features at map center…"
        )

    @reactive.Effect
    @reactive.event(input[draw_widget.query_result_input_id])
    def _query_result():
        data = input[draw_widget.query_result_input_id]()
        n = len(data) if isinstance(data, list) else 0
        _draw_log.set(
            _draw_log.get()
            + f"\n🔍  Query returned {n} feature(s)."
        )

    @render.text
    def draw_log():
        return _draw_log.get() or "Interaction log will appear here…"

    # Brushing & DataFilter extensions (merged from former Tab 9)

    _v1_port_data = [
        {
            "position": [p["lon"], p["lat"]],
            "name": p["name"],
            "cargo_mt": p["cargo_mt"],
        }
        for p in PORTS
    ]

    @reactive.Effect
    @reactive.event(
        input.v1_brushing,
        input.v1_brush_radius,
        input.v1_data_filter,
        input.v1_filter_range,
    )
    async def _v1_layers():
        exts: list = []
        extra: dict = {}

        if input.v1_brushing():
            exts.append(brushing_extension())
            extra["brushingRadius"] = input.v1_brush_radius()
            extra["brushingEnabled"] = True

        if input.v1_data_filter():
            exts.append(data_filter_extension(filter_size=1))
            fmin, fmax = input.v1_filter_range()
            extra["getFilterValue"] = "@@d.cargo_mt"
            extra["filterRange"] = [fmin, fmax]
            extra["filterEnabled"] = True

        layers = [
            scatterplot_layer(
                "v1_ports",
                _v1_port_data,
                getPosition="@@=d.position",
                getRadius=8000,
                getFillColor=[20, 145, 155, 200],
                getLineColor=[255, 255, 255],
                lineWidthMinPixels=1,
                stroked=True,
                extensions=exts if exts else None,
                **extra,
            ),
        ]
        await adv_widget.update(session, layers)

    # =================================================================
    # Tab 7: 3-D Visualisation
    # =================================================================

    # Pre-generate data (constant for the session)
    _bathy_grid = make_bathymetry_grid()
    _fish_obs = make_fish_observations()
    _arc_3d = make_3d_arc_data()

    @reactive.Effect
    @reactive.event(
        input.td_bathy, input.td_bathy_elev, input.td_bathy_wireframe,
        input.td_fish, input.td_fish_mode, input.td_fish_elev,
        input.td_arcs, input.td_arc_width,
        input.td_lighting, input.td_ambient, input.td_point_light,
        input.td_directional, input.td_dir_intensity,
        input.td_pp_brightness, input.td_brightness, input.td_contrast,
        input.td_pitch, input.td_bearing,
    )
    async def _td_rebuild():
        layers: list[dict] = []

        # --- Bathymetry columns ---
        if input.td_bathy():
            bathy_data = [
                {
                    **pt,
                    "color": _bathy_color(pt["elevation"]),
                }
                for pt in _bathy_grid
            ]
            layers.append(
                column_layer(
                    "td-bathy",
                    data=bathy_data,
                    getPosition="@@=d.position",
                    getElevation="@@=d.elevation",
                    getFillColor="@@=d.color",
                    elevationScale=input.td_bathy_elev(),
                    diskResolution=6,
                    radius=12000,
                    extruded=True,
                    wireframe=input.td_bathy_wireframe(),
                    pickable=True,
                    opacity=0.85,
                ),
            )

        # --- Fish observations ---
        if input.td_fish():
            mode = input.td_fish_mode()
            if mode == "hexagon":
                fish_positions = [
                    pt["position"] for pt in _fish_obs
                ]
                layers.append(
                    hexagon_layer(
                        "td-fish-hex",
                        data=fish_positions,
                        getPosition="@@=d",
                        elevationScale=input.td_fish_elev() * 100,
                        radius=25000,
                        extruded=True,
                        pickable=True,
                        colorRange=[
                            [255, 255, 178],
                            [254, 204, 92],
                            [253, 141, 60],
                            [240, 59, 32],
                            [189, 0, 38],
                        ],
                        opacity=0.7,
                    ),
                )
            else:
                fish_data = [
                    {
                        **pt,
                        "color": _species_color(pt["species"]),
                    }
                    for pt in _fish_obs
                ]
                layers.append(
                    column_layer(
                        "td-fish-col",
                        data=fish_data,
                        getPosition="@@=d.position",
                        getElevation="@@=d.elevation",
                        getFillColor="@@=d.color",
                        elevationScale=input.td_fish_elev() * 100,
                        diskResolution=8,
                        radius=8000,
                        extruded=True,
                        pickable=True,
                        opacity=0.8,
                    ),
                )

        # --- 3-D arcs ---
        if input.td_arcs():
            layers.append(
                arc_layer(
                    "td-arcs",
                    data=_arc_3d,
                    getSourcePosition="@@=d.sourcePosition",
                    getTargetPosition="@@=d.targetPosition",
                    getSourceColor="@@=d.sourceColor",
                    getTargetColor="@@=d.targetColor",
                    getHeight="@@=d.height",
                    getWidth=input.td_arc_width(),
                    pickable=True,
                ),
            )

        # --- Lighting ---
        effects = None
        if input.td_lighting():
            amb = ambient_light(intensity=input.td_ambient())
            pl = point_light(
                position=[19.5, 57.0, 80000],
                color=(255, 255, 220),
                intensity=input.td_point_light(),
            )
            lights = [pl]
            if input.td_directional():
                dl = directional_light(
                    direction=[-1, -3, -1],
                    intensity=input.td_dir_intensity(),
                )
                lights.append(dl)
            le = lighting_effect(amb, *lights)
            effects = [le]
        if input.td_pp_brightness():
            pp = post_process_effect(
                "brightnessContrast",
                brightness=input.td_brightness(),
                contrast=input.td_contrast(),
            )
            effects = effects or []
            effects.append(pp)

        await three_d_widget.update(session, layers, effects=effects)

        # Fly to the current pitch / bearing
        await three_d_widget.fly_to(
            session,
            longitude=19.5,
            latitude=57.0,
            zoom=5,
            pitch=input.td_pitch(),
            bearing=input.td_bearing(),
        )

    # =================================================================
    # Tab 8 — Seal IBM (Individual-Based Model)
    # =================================================================

    _SEAL_LOOP = 600
    _seal_haulout_data = make_seal_haulout_data()
    _seal_foraging_geojson = make_seal_foraging_areas()

    # Play / Pause / Reset + speed & trail via reusable module
    seal_anim = trips_animation_server(
        "seal_anim", widget=seal_widget, session=session,
    )

    @reactive.Calc
    def _seal_trips():
        """Regenerate trips when model type or parameters change."""
        model = input.seal_model_type()
        n = input.seal_n_individuals()
        if model == "mcconnell":
            sim_h = input.seal_sim_hours()
            return make_seal_trips_ibm(
                n_seals=n,
                sim_hours=sim_h,
                loop_length=_SEAL_LOOP,
            )
        return make_seal_trips(
            n_seals=n,
            loop_length=_SEAL_LOOP,
        )

    @reactive.Effect
    @reactive.event(
        input.seal_model_type,
        input.seal_n_individuals,
        input.seal_sim_hours,
        input.seal_species,
        seal_anim.speed,
        seal_anim.trail,
        input.seal_bathymetry,
        input.seal_haulouts,
        input.seal_foraging,
        input.seal_routes,
        input.seal_grid,
    )
    async def _seal_layers():
        selected = set(input.seal_species())
        trips = _seal_trips()
        layers: list[dict] = []

        # EMODnet bathymetry WMS underlay (deck.gl native WMSLayer)
        if input.seal_bathymetry():
            layers.append(wms_layer(
                "seal-bathymetry-wms",
                EMODNET_WMS_URL,
                layers=["emodnet:mean_atlas_land"],
            ))

        # Foraging area ellipses (below tracks)
        if input.seal_foraging():
            filtered_features = [
                f for f in _seal_foraging_geojson["features"]
                if f["properties"]["species"] in selected
            ]
            if filtered_features:
                foraging_geojson = {
                    "type": "FeatureCollection",
                    "features": filtered_features,
                }
                layers.append(
                    geojson_layer(
                        "seal_foraging_areas",
                        foraging_geojson,
                        getFillColor=[100, 180, 220, 40],
                        getLineColor=[80, 140, 200, 100],
                        lineWidthMinPixels=1,
                        stroked=True,
                        filled=True,
                    )
                )

        # Animated seal tracks (TripsLayer) with head icons
        filtered_trips = [t for t in trips if t["species"] in selected]
        if filtered_trips:
            layers.append(
                trips_layer(
                    "seal_trips",
                    filtered_trips,
                    trailLength=seal_anim.trail(),
                    getColor="@@d.color",
                    widthMinPixels=3,
                    _tripsAnimation={
                        "loopLength": _SEAL_LOOP,
                        "speed": seal_anim.speed(),
                    },
                    _tripsHeadIcons={
                        "iconAtlas": ICON_ATLAS,
                        "iconMapping": ICON_MAPPING,
                        "iconField": "species",
                        "getSize": 24,
                        "sizeScale": 1,
                        "sizeMinPixels": 10,
                        "sizeMaxPixels": 64,
                    },
                )
            )

        # Haul-out colony markers
        if input.seal_haulouts():
            filtered_haulouts = [
                h for h in _seal_haulout_data
                if h["species"] in selected
            ]
            if filtered_haulouts:
                layers.append(
                    scatterplot_layer(
                        "seal_haulouts",
                        filtered_haulouts,
                        getPosition="@@=d.position",
                        getRadius="@@=d.radius * 800",
                        getFillColor="@@d.color",
                        getLineColor=[255, 255, 255, 200],
                        lineWidthMinPixels=2,
                        stroked=True,
                        pickable=True,
                    )
                )

        # GreatCircleLayer — geodesic arcs between haulout colonies
        if input.seal_routes():
            gc_data = []
            for t in filtered_trips:
                wps = [p[:2] for p in t["path"]]
                if len(wps) >= 2:
                    gc_data.append({
                        "sourcePosition": wps[0],
                        "targetPosition": wps[-1],
                        "name": t.get("name", ""),
                    })
            if gc_data:
                layers.append(
                    great_circle_layer(
                        "seal_gc_routes",
                        gc_data,
                        getSourceColor=[100, 180, 220, 120],
                        getTargetColor=[100, 180, 220, 120],
                        getWidth=1,
                    )
                )

        # GridLayer — 3-D extruded density grid from haulout positions
        if input.seal_grid():
            grid_pts = [
                h["position"]
                for h in _seal_haulout_data
                if h["species"] in selected
                for _ in range(int(h.get("radius", 5)))
            ]
            if grid_pts:
                layers.append(
                    grid_layer(
                        "seal_density_grid",
                        grid_pts,
                        cellSize=30000,
                        elevationScale=200,
                        extruded=True,
                        pickable=False,
                        opacity=0.4,
                    )
                )

        await seal_widget.update(
            session, layers,
            widgets=[loading_widget()],
        )

    # ===================================================================
    # Tab 9: Widgets Gallery
    # ===================================================================

    _wg_log: reactive.Value[str] = reactive.Value("")

    # -- Reactive: build widget list from toggles -----------------------

    @reactive.Calc
    def _wg_active_widgets() -> list[dict]:
        """Assemble the active widget list from all toggle switches."""
        widgets: list[dict] = []
        # Standard widgets (v0.8.0)
        if input.wg_zoom():
            widgets.append(zoom_widget())
        if input.wg_compass():
            widgets.append(compass_widget())
        if input.wg_gimbal():
            widgets.append(gimbal_widget())
        if input.wg_reset_view():
            widgets.append(reset_view_widget())
        if input.wg_fullscreen():
            widgets.append(fullscreen_widget())
        if input.wg_scale():
            widgets.append(scale_widget())
        if input.wg_screenshot():
            widgets.append(screenshot_widget(filename="shiny-deckgl-capture"))
        if input.wg_fps():
            widgets.append(fps_widget())
        if input.wg_loading():
            widgets.append(loading_widget(label="Loading layers\u2026"))
        if input.wg_theme():
            widgets.append(theme_widget())
        if input.wg_timeline():
            widgets.append(timeline_widget(min=0, max=1000, step=10))
        if input.wg_geocoder():
            widgets.append(geocoder_widget(placeholder="Search location\u2026"))
        # Experimental widgets (v9.2+)
        if input.wg_context_menu():
            widgets.append(context_menu_widget(items=[
                {"label": "Copy coordinates"},
                {"label": "Zoom to 100%"},
                {"label": "Reset view"},
            ]))
        if input.wg_info():
            widgets.append(info_widget(
                placement="top-left",
                text="Hover over features for details",
            ))
        if input.wg_splitter():
            widgets.append(splitter_widget(orientation="vertical"))
        if input.wg_stats():
            widgets.append(stats_widget(
                placement="bottom-left",
                framesPerUpdate=60,
            ))
        if input.wg_view_selector():
            widgets.append(view_selector_widget(initialViewMode="map"))
        # Layer legend widget
        if input.wg_layer_legend():
            if input.wg_auto_legend():
                # Auto-introspect mode: no manual entries needed
                widgets.append(layer_legend_widget(
                    placement="top-left",
                    title="Layers (auto)",
                    show_checkbox=True,
                    auto_introspect=True,
                    label_map={
                        "wg-ports": "Ports",
                        "wg-heat": "Heatmap",
                        "wg-arcs": "Arcs",
                        "wg-routes": "Routes",
                        "wg-columns": "3-D Columns",
                        "wg-hexagons": "Hexagons",
                    },
                ))
            else:
                meta = _WG_LAYER_META.get(input.wg_layer_combo())
                if meta:
                    layer_id, label, color, shape = meta
                    widgets.append(layer_legend_widget(
                        entries=[{"layer_id": layer_id, "label": label,
                                  "color": color, "shape": shape}],
                        placement="top-left",
                        title="Active Layer",
                        show_checkbox=True,
                        collapsed=False,
                    ))
        return widgets

    # -- Reactive: build layer list from dropdown -----------------------

    @reactive.Calc
    def _wg_layers() -> list[dict]:
        """Build layer for the selected scenario."""
        choice = input.wg_layer_combo()
        if choice == "ports":
            return [scatterplot_layer(
                "wg-ports",
                _port_data_simple,
                getPosition="@@=d.position",
                getRadius="@@=d.radius",
                getFillColor=[20, 130, 180, 180],
                radiusMinPixels=4,
                radiusMaxPixels=30,
                pickable=True,
            )]
        elif choice == "heatmap":
            return [heatmap_layer(
                "wg-heat",
                _heatmap_points,
                getPosition="@@=d.position",
                getWeight="@@=d.weight || 1",
                radiusPixels=40,
                intensity=1.2,
                threshold=0.05,
            )]
        elif choice == "arcs":
            return [arc_layer(
                "wg-arcs",
                _arc_data,
                getSourcePosition="@@=d.from",
                getTargetPosition="@@=d.to",
                getSourceColor=[0, 128, 255],
                getTargetColor=[255, 100, 0],
                getWidth=2,
                pickable=True,
            )]
        elif choice == "routes":
            return [path_layer(
                "wg-routes",
                _path_data,
                getPath="@@=d.path",
                getColor="@@=d.color",
                widthMinPixels=2,
                pickable=True,
            )]
        elif choice == "3d_columns":
            return [column_layer(
                "wg-columns",
                _port_data_simple,
                getPosition="@@=d.position",
                getElevation="@@=d.elevation",
                getFillColor=[14, 145, 155, 200],
                radius=8000,
                elevationScale=1,
                extruded=True,
                pickable=True,
            )]
        elif choice == "hexagons":
            return [hexagon_layer(
                "wg-hexagons",
                _heatmap_points,
                getPosition="@@=d.position",
                radius=20000,
                elevationScale=50,
                extruded=True,
                pickable=True,
            )]
        return []

    # -- Legend for active layer scenario ---------------------------------

    _WG_LAYER_META: dict[str, tuple[str, str, list[int], str]] = {
        "ports": ("wg-ports", "Ports (ScatterplotLayer)", [20, 130, 180], "circle"),
        "heatmap": ("wg-heat", "Heatmap (HeatmapLayer)", [255, 80, 0], "gradient"),
        "arcs": ("wg-arcs", "Arcs (ArcLayer)", [0, 128, 255], "arc"),
        "routes": ("wg-routes", "Routes (PathLayer)", [180, 100, 60], "line"),
        "3d_columns": ("wg-columns", "3-D Columns (ColumnLayer)", [14, 145, 155], "rect"),
        "hexagons": ("wg-hexagons", "Hexagons (HexagonLayer)", [80, 160, 80], "rect"),
    }

    # -- Init: send default widgets + layers on first load ----------------

    @reactive.Effect
    async def _wg_init():
        """Send initial widget + layer state on session start."""
        widgets = _wg_active_widgets()
        layers = _wg_layers()
        await widgets_gallery_widget.update(
            session, layers, widgets=widgets,
        )

    # -- Push widgets + layers to the map --------------------------------

    @reactive.Effect
    @reactive.event(
        input.wg_zoom, input.wg_compass, input.wg_gimbal,
        input.wg_reset_view, input.wg_fullscreen, input.wg_scale,
        input.wg_screenshot, input.wg_fps, input.wg_loading,
        input.wg_theme, input.wg_timeline, input.wg_geocoder,
        input.wg_context_menu, input.wg_info, input.wg_splitter,
        input.wg_stats, input.wg_view_selector,
        input.wg_layer_combo, input.wg_layer_legend,
        input.wg_auto_legend,
    )
    async def _wg_update_map():
        widgets = _wg_active_widgets()
        layers = _wg_layers()
        await widgets_gallery_widget.update(
            session, layers, widgets=widgets,
        )
        # Update status console
        names = [w["@@widgetClass"] for w in widgets]
        standard = [n for n in names if not n.startswith("_") or n in (
            "_ScaleWidget", "_FpsWidget", "_LoadingWidget",
            "_TimelineWidget", "_GeocoderWidget", "_ThemeWidget",
            "_DeckLayerLegendWidget",
        )]
        experimental = [n for n in names if n in (
            "_ContextMenuWidget", "_InfoWidget", "_SplitterWidget",
            "_StatsWidget", "_ViewSelectorWidget",
        )]
        status_lines = [
            f"Active widgets: {len(widgets)} / 18",
            f"Layer: {input.wg_layer_combo()}",
            "",
        ]
        if standard:
            status_lines.append("Standard:")
            status_lines.extend(f"  \u2022 {n}" for n in standard)
        if experimental:
            status_lines.append("Experimental (v9.2+):")
            status_lines.extend(f"  \u2022 {n}" for n in experimental)
        if not names:
            status_lines.append("  (no widgets active)")
        _wg_log.set("\n".join(status_lines))

    @render.text
    def wg_status():
        return (
            _wg_log.get()
            or "Toggle widgets in the sidebar to see them on the map."
        )

    # -- Preset buttons --------------------------------------------------

    @reactive.Effect
    @reactive.event(input.wg_preset_nav)
    async def _wg_preset_nav():
        """Navigation preset: zoom, compass, scale, fullscreen, reset."""
        await _wg_apply_preset(
            zoom=True, compass=True, scale=True,
            fullscreen=True, reset_view=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_debug)
    async def _wg_preset_debug():
        """Debug preset: FPS, stats, info, loading."""
        await _wg_apply_preset(
            fps=True, stats=True, info=True, loading=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_presentation)
    async def _wg_preset_presentation():
        """Presentation: fullscreen, screenshot, theme, scale."""
        await _wg_apply_preset(
            fullscreen=True, screenshot=True, theme=True, scale=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_all)
    async def _wg_preset_all():
        """Turn on every widget."""
        await _wg_apply_preset(
            zoom=True, compass=True, gimbal=True, reset_view=True,
            fullscreen=True, scale=True, screenshot=True, fps=True,
            loading=True, theme=True, timeline=True, geocoder=True,
            context_menu=True, info=True, splitter=True, stats=True,
            view_selector=True,
        )

    @reactive.Effect
    @reactive.event(input.wg_preset_none)
    async def _wg_preset_none():
        """Turn off all widgets."""
        await _wg_apply_preset()

    async def _wg_apply_preset(
        zoom=False, compass=False, gimbal=False, reset_view=False,
        fullscreen=False, scale=False, screenshot=False, fps=False,
        loading=False, theme=False, timeline=False, geocoder=False,
        context_menu=False, info=False, splitter=False, stats=False,
        view_selector=False,
    ):
        """Set all widget toggles to the given preset values."""
        ui.update_switch("wg_zoom", value=zoom)
        ui.update_switch("wg_compass", value=compass)
        ui.update_switch("wg_gimbal", value=gimbal)
        ui.update_switch("wg_reset_view", value=reset_view)
        ui.update_switch("wg_fullscreen", value=fullscreen)
        ui.update_switch("wg_scale", value=scale)
        ui.update_switch("wg_screenshot", value=screenshot)
        ui.update_switch("wg_fps", value=fps)
        ui.update_switch("wg_loading", value=loading)
        ui.update_switch("wg_theme", value=theme)
        ui.update_switch("wg_timeline", value=timeline)
        ui.update_switch("wg_geocoder", value=geocoder)
        ui.update_switch("wg_context_menu", value=context_menu)
        ui.update_switch("wg_info", value=info)
        ui.update_switch("wg_splitter", value=splitter)
        ui.update_switch("wg_stats", value=stats)
        ui.update_switch("wg_view_selector", value=view_selector)

    # ===================================================================
    # Tab 1: Layer Gallery — all 33 layer helpers
    # ===================================================================

    # -- Pre-computed gallery data (generated once per session) ----------
    _gl_port_data = make_gallery_port_data()
    _gl_arc_data = make_gallery_arc_data()
    _gl_line_data = make_gallery_line_data()
    _gl_path_data = make_gallery_path_data()
    _gl_text_data = make_gallery_text_data()
    _gl_icon_data = make_gallery_icon_data()
    _gl_column_data = make_gallery_column_data()

    # New layer data (v1.6.0)
    _gl_grid_cell_data = make_grid_cell_data()
    _gl_lithuanian_bathy = make_lithuanian_bathymetry_data(sample_step=3)
    _gl_solid_polygon_data = make_solid_polygon_data()
    _gl_a5_data = make_a5_data()
    _gl_geohash_data = make_geohash_data()
    _gl_h3_cluster_data = make_h3_cluster_data()
    _gl_quadkey_data = make_quadkey_data()
    _gl_s2_data = make_s2_data()
    _gl_scenegraph_data = make_scenegraph_data()

    _gl_polygon_data = make_shyfem_polygon_data(_POLYGON_GRD_STR)
    _gl_shyfem_mesh = make_shyfem_mesh_data(_CURONIAN_GRD_STR, z_scale=500.0)

    # Pre-compute mesh node points for the "Show mesh nodes" overlay
    _gl_mesh_node_data: list[dict] | None = None
    if _gl_shyfem_mesh is not None:
        _pos = _gl_shyfem_mesh["positions"]
        _col = _gl_shyfem_mesh.get("colors", [])
        _n = _gl_shyfem_mesh["n_vertices"]
        _gl_mesh_node_data = []
        for _i in range(_n):
            _r = round(_col[_i * 3] * 255) if _col else 120
            _g = round(_col[_i * 3 + 1] * 255) if _col else 170
            _b = round(_col[_i * 3 + 2] * 255) if _col else 210
            _gl_mesh_node_data.append({
                "position": [
                    _pos[_i * 3],
                    _pos[_i * 3 + 1],
                    _pos[_i * 3 + 2],
                ],
                "color": [_r, _g, _b, 220],
                "name": f"Node {_i}",
                "layerType": "MeshNode",
            })
        del _pos, _col, _n, _i, _r, _g, _b

    _gl_great_circle_data = [
        {
            "sourcePosition": r["waypoints"][0],
            "targetPosition": r["waypoints"][-1],
            "name": f"{r['from']} \u2192 {r['to']} (geodesic)",
            "layerType": "GreatCircleLayer",
        }
        for r in ROUTES
    ]

    _gl_heatmap_pts = make_heatmap_points(400)
    _gl_trips_data = make_trips_data(1800)

    _gl_h3_data = make_h3_data()

    _gl_point_cloud = make_point_cloud_data()

    # GeoJSON for gallery — HELCOM Marine Protected Areas
    _gl_geojson = MPA_GEOJSON

    # -- Build all 33 gallery layers once (data sent at session init) ----
    # Toggle-switch ID -> (layer_id(s), display_name(s))
    _GL_TOGGLE_MAP: dict[str, list[tuple[str, str]]] = {
        "gl_scatterplot":   [("gl-scatter", "ScatterplotLayer")],
        "gl_geojson":       [("gl-geojson", "GeoJsonLayer")],
        "gl_arc":           [("gl-arcs", "ArcLayer")],
        "gl_line":          [("gl-lines", "LineLayer")],
        "gl_path":          [("gl-paths", "PathLayer")],
        "gl_icon":          [("gl-icons", "IconLayer")],
        "gl_text":          [("gl-text", "TextLayer")],
        "gl_column":        [("gl-columns", "ColumnLayer")],
        "gl_polygon":       [("gl-polygons", "PolygonLayer")],
        "gl_great_circle":  [("gl-gc", "GreatCircleLayer")],
        "gl_grid_cell":     [("gl-grid-cell", "GridCellLayer")],
        "gl_lt_bathy":      [("gl-lt-bathy", "LT Bathymetry")],
        "gl_solid_polygon": [("gl-solid-polygon", "SolidPolygonLayer")],
        "gl_heatmap":       [("gl-heatmap", "HeatmapLayer")],
        "gl_hexagon":       [("gl-hexagons", "HexagonLayer")],
        "gl_grid":          [("gl-grid", "GridLayer")],
        "gl_screen_grid":   [("gl-screen-grid", "ScreenGridLayer")],
        "gl_contour":       [("gl-contour", "ContourLayer")],
        "gl_h3_hexagon":    [("gl-h3", "H3HexagonLayer")],
        "gl_trips":         [("gl-trips", "TripsLayer")],
        "gl_a5":            [("gl-a5", "A5Layer")],
        "gl_geohash":       [("gl-geohash", "GeohashLayer")],
        "gl_h3_cluster":    [("gl-h3-cluster", "H3ClusterLayer")],
        "gl_quadkey":       [("gl-quadkey", "QuadkeyLayer")],
        "gl_s2":            [("gl-s2", "S2Layer")],
        "gl_tile":          [("gl-tiles", "TileLayer")],
        "gl_bitmap":        [("gl-bitmap", "BitmapLayer")],
        "gl_mvt":           [("gl-mvt", "MVTLayer")],
        "gl_wms":           [("gl-wms", "WMSLayer")],
        "gl_tile_3d":       [("gl-tile-3d", "Tile3DLayer")],
        "gl_point_cloud":   [("gl-pointcloud", "PointCloudLayer")],
        "gl_simple_mesh":   [("gl-mesh", "SimpleMeshLayer")]
                             + ([("gl-mesh-nodes", "MeshNodes")]
                                if _gl_mesh_node_data is not None else []),
        "gl_terrain":       [("gl-terrain", "TerrainLayer")],
        "gl_scenegraph":    [("gl-scenegraph", "ScenegraphLayer")],
    }

    # 3-D layer names that need pitched view
    _GL_3D_NAMES = {
        "TerrainLayer", "PointCloudLayer", "SimpleMeshLayer",
        "ColumnLayer", "HexagonLayer", "GridLayer",
        "GridCellLayer", "Tile3DLayer", "ScenegraphLayer",
    }

    def _gl_build_all_layers() -> list[dict]:
        """Build all 33 gallery layers with initial visibility from switches."""
        layers: list[dict] = []

        def _add(switch_id: str, layer_spec: dict) -> None:
            layer_spec["visible"] = getattr(input, switch_id)()
            layers.append(layer_spec)

        # -- Core layers ---
        _add("gl_scatterplot", scatterplot_layer(
            "gl-scatter", _gl_port_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPosition="@@=d.position",
            getRadius="@@=d.radius",
            getFillColor=[20, 130, 180, 200],
            radiusMinPixels=4,
            radiusMaxPixels=30,
            pickable=True,
        ))
        _add("gl_geojson", geojson_layer(
            "gl-geojson", _gl_geojson,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getFillColor=[0, 180, 120, 60],
            getLineColor=[0, 180, 120, 200],
            lineWidthMinPixels=2,
            pickable=True,
        ))
        _add("gl_arc", arc_layer(
            "gl-arcs", _gl_arc_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getSourceColor=[0, 128, 255],
            getTargetColor=[255, 80, 80],
            getWidth=2,
            pickable=True,
        ))
        _add("gl_line", line_layer(
            "gl-lines", _gl_line_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getColor=[80, 80, 80, 180],
            getWidth=2,
            pickable=True,
        ))
        _add("gl_path", path_layer(
            "gl-paths", _gl_path_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPath="@@=d.path",
            getColor="@@=d.color",
            widthMinPixels=2,
            pickable=True,
        ))
        _add("gl_icon", icon_layer(
            "gl-icons", _gl_icon_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPosition="@@=d.position",
            iconAtlas="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
            iconMapping={
                "marker": {"x": 0, "y": 0, "width": 128,
                           "height": 128, "anchorY": 128},
            },
            getIcon="marker",
            getSize=32,
            pickable=True,
        ))
        _add("gl_text", text_layer(
            "gl-text", _gl_text_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPosition="@@=d.position",
            getText="@@=d.text",
            getSize=14,
            getColor=[0, 0, 0, 255],
            getTextAnchor="middle",
            getAlignmentBaseline="center",
            fontWeight="bold",
            pickable=True,
        ))
        _add("gl_column", column_layer(
            "gl-columns", _gl_column_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPosition="@@=d.position",
            getElevation="@@=d.elevation",
            getFillColor=[14, 145, 155, 200],
            radius=8000,
            elevationScale=1,
            extruded=True,
            pickable=True,
        ))
        _add("gl_polygon", polygon_layer(
            "gl-polygons", _gl_polygon_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPolygon="@@=d.polygon",
            getFillColor="@@=d.color",
            getLineColor=[40, 80, 120, 200],
            getLineWidth=1,
            lineWidthMinPixels=1,
            pickable=True,
        ))
        _add("gl_great_circle", great_circle_layer(
            "gl-gc", _gl_great_circle_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getSourceColor=[0, 200, 80],
            getTargetColor=[200, 0, 180],
            getWidth=2,
            pickable=True,
        ))
        # GridCellLayer with real Baltic Sea bathymetry from EMODnet
        _add("gl_grid_cell", grid_cell_layer(
            "gl-grid-cell", _gl_grid_cell_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPosition="@@=d.position",
            getElevation="@@=d.elevation",
            getFillColor="@@=d.color",
            cellSize=45000,  # ~0.5° at Baltic latitudes
            coverage=0.9,
            elevationScale=1,
            extruded=True,
            pickable=True,
        ))
        # Lithuanian coastal bathymetry from bathy.asc (1km resolution, sampled every 3rd)
        if _gl_lithuanian_bathy:
            _add("gl_lt_bathy", grid_cell_layer(
                "gl-lt-bathy", _gl_lithuanian_bathy,
                coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
                getPosition="@@=d.position",
                getElevation="@@=d.depth",
                getFillColor="@@=d.color",
                cellSize=3500,  # ~3km to match sampling step (covers gaps)
                coverage=1.0,   # Full coverage, no gaps between cells
                elevationScale=0,  # Flat display (2D colored grid)
                extruded=False,    # No 3D extrusion
                pickable=True,
            ))
        _add("gl_solid_polygon", solid_polygon_layer(
            "gl-solid-polygon", _gl_solid_polygon_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPolygon="@@=d.polygon",
            getFillColor="@@=d.color",
            extruded=False,
            pickable=True,
        ))

        # -- Aggregation layers ---
        _add("gl_heatmap", heatmap_layer(
            "gl-heatmap", _gl_heatmap_pts,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            radiusPixels=40,
            intensity=1.2,
            threshold=0.05,
        ))
        _add("gl_hexagon", hexagon_layer(
            "gl-hexagons", _gl_heatmap_pts,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            radius=20000,
            elevationScale=50,
            extruded=True,
            pickable=True,
        ))
        _add("gl_grid", grid_layer(
            "gl-grid", _gl_heatmap_pts,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            cellSize=20000,
            elevationScale=50,
            extruded=True,
            pickable=True,
        ))
        _add("gl_screen_grid", screen_grid_layer(
            "gl-screen-grid", _gl_heatmap_pts,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            cellSizePixels=20,
        ))
        _add("gl_contour", contour_layer(
            "gl-contour", _gl_heatmap_pts,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            cellSize=20000,
            contours=[
                {"threshold": 1, "color": [255, 0, 0],
                 "strokeWidth": 2},
                {"threshold": 5, "color": [0, 200, 0],
                 "strokeWidth": 3},
                {"threshold": [6, 100], "color": [0, 100, 255, 128]},
            ],
        ))

        # -- Geo-spatial layers ---
        _add("gl_h3_hexagon", h3_hexagon_layer(
            "gl-h3", _gl_h3_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getHexagon="@@=d.hex",
            getFillColor="@@=d.color",
            extruded=False,
            pickable=True,
        ))
        _add("gl_trips", trips_layer(
            "gl-trips", _gl_trips_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPath="@@=d.path",
            getTimestamps="@@=d.timestamps",
            getColor=[253, 128, 93],
            widthMinPixels=3,
            trailLength=300,
            currentTime=500,
        ))
        _add("gl_a5", a5_layer(
            "gl-a5", _gl_a5_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getPentagon="@@=d.pentagon",
            getFillColor=[255, 140, 0, 180],
            getElevation="@@=d.count",
            elevationScale=50,
            extruded=True,
            pickable=True,
        ))
        _add("gl_geohash", geohash_layer(
            "gl-geohash", _gl_geohash_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getGeohash="@@=d.geohash",
            getFillColor="@@=d.color",
            extruded=False,
            pickable=True,
        ))
        _add("gl_h3_cluster", h3_cluster_layer(
            "gl-h3-cluster", _gl_h3_cluster_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getHexagons="@@=d.hexIds",
            getFillColor="@@=d.color",
            stroked=True,
            filled=True,
            pickable=True,
        ))
        _add("gl_quadkey", quadkey_layer(
            "gl-quadkey", _gl_quadkey_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getQuadkey="@@=d.quadkey",
            getFillColor="@@=d.color",
            extruded=False,
            pickable=True,
        ))
        _add("gl_s2", s2_layer(
            "gl-s2", _gl_s2_data,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
            getS2Token="@@=d.token",
            getFillColor="@@=d.color",
            extruded=False,
            pickable=True,
        ))

        # -- Tile / raster layers ---
        _add("gl_tile", tile_layer(
            "gl-tiles",
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            minZoom=0,
            maxZoom=19,
            tileSize=256,
            opacity=0.6,
        ))
        _add("gl_bitmap", bitmap_layer(
            "gl-bitmap",
            image=(
                "https://ows.emodnet-bathymetry.eu/wms"
                "?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1"
                "&LAYERS=emodnet:mean_atlas_land"
                "&STYLES=&SRS=EPSG:4326"
                "&BBOX=9.0,53.0,30.5,66.0"
                "&WIDTH=1024&HEIGHT=768"
                "&FORMAT=image/png&TRANSPARENT=true"
            ),
            bounds=[9.0, 53.0, 30.5, 66.0],
            opacity=0.7,
        ))
        _add("gl_mvt", mvt_layer(
            "gl-mvt",
            "https://tiles.stadiamaps.com/data/openmaptiles/{z}/{x}/{y}.pbf",
            minZoom=0,
            maxZoom=14,
            getFillColor=[140, 170, 200, 100],
            getLineColor=[0, 0, 0, 80],
            lineWidthMinPixels=1,
            pickable=True,
        ))
        _add("gl_wms", wms_layer(
            "gl-wms",
            EMODNET_WMS_URL,
            layers=["emodnet:mean_atlas_land"],
            transparent=True,
            opacity=0.6,
        ))
        _add("gl_tile_3d", tile_3d_layer(
            "gl-tile-3d",
            # Sample 3D Tiles dataset (NYC buildings)
            "https://tile.googleapis.com/v1/3dtiles/root.json",
            pickable=True,
            opacity=0.8,
        ))

        # -- 3-D / mesh layers ---
        _add("gl_point_cloud", point_cloud_layer(
            "gl-pointcloud", _gl_point_cloud,
            getPosition="@@=d.position",
            getColor="@@=d.color",
            pointSize=4,
            pickable=True,
        ))

        if _gl_shyfem_mesh is not None:
            _add("gl_simple_mesh", simple_mesh_layer(
                "gl-mesh",
                **custom_geometry(_gl_shyfem_mesh),
                pickable=True,
                wireframe=False,
            ))
        else:
            _mesh_data = [
                {
                    "position": [p["lon"], p["lat"], 500],
                    "name": p["name"],
                    "layerType": "SimpleMeshLayer",
                }
                for p in PORTS
            ]
            _add("gl_simple_mesh", simple_mesh_layer(
                "gl-mesh", _mesh_data,
                getPosition="@@=d.position",
                getColor=[255, 180, 60, 220],
                mesh="@@CubeGeometry",
                sizeScale=20000,
                pickable=True,
            ))
        if _gl_mesh_node_data is not None:
            assert _gl_shyfem_mesh is not None
            ctr = _gl_shyfem_mesh["center"]
            _add("gl_simple_mesh", scatterplot_layer(
                "gl-mesh-nodes",
                _gl_mesh_node_data,
                getPosition="@@=d.position",
                getFillColor="@@=d.color",
                getRadius=30,
                radiusMinPixels=1,
                radiusMaxPixels=4,
                coordinateSystem=2,
                coordinateOrigin=[ctr[0], ctr[1]],
                pickable=True,
            ))

        # TerrainLayer with AWS elevation + Esri Ocean Base texture
        # AWS Terrarium tiles include bathymetry data
        # Esri World Ocean Base shows ocean depth coloring
        # Elevation exaggeration: 20x to make terrain differences visible
        _add("gl_terrain", terrain_layer(
            "gl-terrain",
            elevationData="https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
            # Esri World Ocean Base - shows bathymetry coloring (tile-based)
            texture="https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
            elevationDecoder={
                # Terrarium format with 20x exaggeration for visibility
                # Base formula: elevation = (R * 256 + G + B / 256) - 32768
                "rScaler": 256 * 20, "gScaler": 1 * 20,
                "bScaler": (1 / 256) * 20, "offset": -32768 * 20,
            },
            # Baltic Sea bounds (focus area)
            bounds=[9.0, 53.0, 30.5, 66.0],
            meshMaxError=4.0,
            wireframe=False,
            coordinateSystem=COORDINATE_SYSTEM.LNGLAT,
        ))
        _add("gl_scenegraph", scenegraph_layer(
            "gl-scenegraph", _gl_scenegraph_data,
            getPosition="@@=d.position",
            getOrientation="@@=d.orientation",
            # Sample glTF model (a simple box)
            scenegraph="https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/Box/glTF/Box.gltf",
            sizeScale=5000,
            pickable=True,
        ))

        return layers

    # -- Compute view state from active layer names ----------------------

    _SF_VIEW: dict = {
        "longitude": -122.42, "latitude": 37.78, "zoom": 12,
        "pitch": 45, "bearing": 0,
    }

    def _gl_view_state(active_names: set[str]) -> dict:
        # A5Layer uses SF bike-parking data — fly there
        if "A5Layer" in active_names:
            return _SF_VIEW
        needs_3d = bool(_GL_3D_NAMES & active_names)
        if "SimpleMeshLayer" in active_names and _CURONIAN_GRD_STR:
            return {**SHYFEM_VIEW, "pitch": 50, "bearing": -15} if needs_3d else SHYFEM_VIEW
        elif needs_3d:
            return {**BALTIC_VIEW, "pitch": 50, "bearing": -15, "zoom": 6}
        return BALTIC_VIEW

    # -- Send all layers once at session init ----------------------------

    _gl_initialized: reactive.Value[bool] = reactive.Value(False)

    @reactive.Effect
    async def _gl_init():
        """Send all 33 layers once (heavy payload, one-time cost)."""
        all_layers = _gl_build_all_layers()

        widgets = [
            zoom_widget(), compass_widget(),
            fullscreen_widget(), scale_widget(),
            loading_widget(label="Loading layers…"),
            layer_legend_widget(
                placement="bottom-right",
                title="Active Layers",
                show_checkbox=True,
                auto_introspect=True,
            ),
        ]

        active_names: set[str] = set()
        for sw, pairs in _GL_TOGGLE_MAP.items():
            if getattr(input, sw)():
                active_names.update(name for _, name in pairs)

        vs = _gl_view_state(active_names)

        await gallery_widget.update(
            session, all_layers, widgets=widgets,
            view_state=vs, transition_duration=800,
        )

        # Initial status
        _gl_update_status(active_names)
        _gl_initialized.set(True)

    # -- Status helper (lightweight, no layer data) ----------------------

    def _gl_update_status(active_names: set[str]) -> None:
        lines = [f"Active layers: {len(active_names)} / 24", ""]
        if active_names:
            for n in sorted(active_names):
                lines.append(f"  • {n}")
        else:
            lines.append("  (no layers active)")
        _gl_log.set("\n".join(lines))

    # -- Toggle: visibility only (tiny payload ~200 bytes) ---------------

    @reactive.Effect
    @reactive.event(
        input.gl_scatterplot, input.gl_geojson, input.gl_arc,
        input.gl_line, input.gl_path, input.gl_icon, input.gl_text,
        input.gl_column, input.gl_polygon, input.gl_great_circle,
        input.gl_heatmap, input.gl_hexagon, input.gl_grid,
        input.gl_screen_grid, input.gl_contour,
        input.gl_h3_hexagon, input.gl_trips,
        input.gl_tile, input.gl_bitmap, input.gl_mvt, input.gl_wms,
        input.gl_point_cloud, input.gl_simple_mesh, input.gl_terrain,
        # v1.6.0 layers
        input.gl_grid_cell, input.gl_lt_bathy, input.gl_solid_polygon,
        input.gl_a5, input.gl_geohash, input.gl_h3_cluster,
        input.gl_quadkey, input.gl_s2, input.gl_tile_3d,
        input.gl_scenegraph,
    )
    async def _gl_toggle():
        # Skip toggles until initial data has been sent
        if not _gl_initialized.get():
            return

        visibility: dict[str, bool] = {}
        active_names: set[str] = set()

        for sw, pairs in _GL_TOGGLE_MAP.items():
            val = getattr(input, sw)()
            for layer_id, name in pairs:
                visibility[layer_id] = val
                if val:
                    active_names.add(name)

        # Send only visibility dict (~200 bytes vs ~30 MB)
        await gallery_widget.set_layer_visibility(session, visibility)

        # Update view state for 3-D layers (lightweight fly_to)
        vs = _gl_view_state(active_names)
        await gallery_widget.fly_to(
            session,
            longitude=vs["longitude"],
            latitude=vs["latitude"],
            zoom=vs.get("zoom"),
            pitch=vs.get("pitch"),
            bearing=vs.get("bearing"),
        )

        # Update status (legend auto-refreshes via introspection)
        _gl_update_status(active_names)


    _gl_log: reactive.Value[str] = reactive.Value("")

    @render.text
    def gl_status():
        return (
            _gl_log.get()
            or "Toggle layers in the sidebar to see them on the map."
        )


__all__ = ["server"]
