"""Run parts of the demo's server function in memory (Shiny >= 1.8.0).

shiny.testserver.test_server() runs the real reactive graph against a mock
connection: no browser, no websocket. It seeds no inputs and discards custom
messages (the map payloads), so each test seeds the inputs its effects read
and asserts on text outputs and on the absence of errors. The Layers tab is
not covered: its init effect reads its switches inside reactive.isolate() and
never re-runs once inputs exist -- that tab stays with the Playwright suite.
"""
from __future__ import annotations

import pytest

pytest.importorskip("shiny.testserver")
from shiny.testserver import test_server  # noqa: E402

from shiny_deckgl.app import app  # noqa: E402

COLOUR_INPUTS = {"pal_name": "Viridis", "pal_mode": "bins", "pal_nbins": 6, "pal_layer": "scatter"}
ADVANCED_INPUTS = {
    "enable_lighting": False, "ambient": 1.0, "point_intensity": 1.0,
    "v1_brushing": False, "v1_brush_radius": 50000,
    "v1_data_filter": False, "v1_filter_range": (0, 100),
}


def test_demo_starts_without_errors():
    with test_server(app, timeout_secs=60) as s:
        assert s.is_ok, s.error


@pytest.mark.parametrize("mode", ["bins", "quantiles", "range"])
def test_colour_scales_mode(mode):
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**{**COLOUR_INPUTS, "pal_mode": mode})
        assert s.is_ok, s.error
        out = s.get_output("pal_stats")
        assert out.status == "ok"
        assert "Palette:    Viridis" in out.value
        for n in (3, 9):
            s.set_inputs(pal_nbins=n)
            assert s.is_ok, s.error
            assert f"Bins/stops: {n}" in s.get_output("pal_stats").value


@pytest.mark.parametrize("layer", ["columns", "scatter", "heatmap"])
def test_colour_scales_layer_types(layer):
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**{**COLOUR_INPUTS, "pal_layer": layer})
        assert s.is_ok, s.error
        assert s.get_output("pal_stats").status == "ok"


def test_advanced_tab_effects_survive_their_inputs():
    # The 2026-09-26 review's D2: an effect here once wiped the shared layer list.
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**ADVANCED_INPUTS)
        assert s.is_ok, s.error
        s.set_inputs(enable_lighting=True, ambient=0.5, point_intensity=2.0)
        assert s.is_ok, s.error
        assert "Lighting ON" in s.get_output("advanced_status").value
        s.set_inputs(v1_brushing=True, v1_brush_radius=80000)
        s.set_inputs(v1_data_filter=True, v1_filter_range=(10, 60))
        s.set_inputs(enable_lighting=False)
        assert s.is_ok, s.error
        assert "Lighting OFF" in s.get_output("advanced_status").value


# ---------------------------------------------------------------------------
# 2026-09-28 review: outputs before the first browser event, spatial query
# ---------------------------------------------------------------------------

READBACK_PLACEHOLDERS = {
    "click_info": "Click a port or arc",
    "hover_info": "Hover over a feature",
    "viewport_info": "Pan or zoom the map",
    "events_drag": "Place a marker",
    "ml_drag_info": "Place a marker first",
}


@pytest.mark.parametrize("output_id,placeholder", sorted(READBACK_PLACEHOLDERS.items()))
def test_readback_outputs_show_placeholder_before_first_event(output_id, placeholder):
    # Reading a never-set input raises SilentException, which left these
    # cards blank; the demo now checks is_set() first.
    with test_server(app, timeout_secs=60) as s:
        out = s.get_output(output_id)
        assert out.status == "ok", (output_id, out.status)
        assert placeholder in out.value


def test_spatial_query_counts_features_from_the_dict_payload():
    with test_server(app, timeout_secs=60) as s:
        s.set_inputs(**{"draw_map_query_result": {
            "requestId": 1,
            "features": [{"layer": {"id": "ports-circle"}}, {"layer": {"id": "mpa-fill"}}],
        }})
        assert s.is_ok, s.error
        log = s.get_output("draw_log").value
        assert "Query returned 2 feature(s): mpa-fill, ports-circle" in log
