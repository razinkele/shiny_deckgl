"""Regression tests for the 2026-09-06 workflow code review.

Each class maps to one confirmed finding; the docstring states the defect and
the test name states the behaviour that must hold.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from _js_harness import (  # noqa: E402
    extract_function,
    extract_var,
    js_source,
    requires_node,
    run_js,
)

from conftest import _FakeSession  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src" / "shiny_deckgl"


class TestNoUndefinedNames:
    """_app_server.py used `ui` (22x) and `MapWidget` without importing either.

    Both sites live inside reactive.Effect callbacks, so the resulting NameError
    reached Session._unhandled_error, which closes the whole browser session --
    every preset button and the HTML/JSON export killed the demo.
    """

    def test_package_has_no_undefined_names(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "F821",
             "--output-format", "concise", str(SRC)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"undefined names in package:\n{proc.stdout}"


def _uri_prelude() -> str:
    return "\n".join([
        extract_var("SANITIZE_URI_SCHEME"),
        extract_var("SANITIZE_DANGEROUS_SCHEMES"),
        extract_function("isDangerousUri"),
    ])


@requires_node
class TestDangerousUriDetection:
    r"""SANITIZE_DANGEROUS_URI was /^\s*javascript\s*:/i.

    That requires the literal contiguous word, but browsers strip TAB/LF/CR from
    anywhere in a URL and leading C0 controls before parsing the scheme, so
    "java<TAB>script:" survived the filter and executed from a MapLibre popup.
    """

    @pytest.mark.parametrize("value", [
        "javascript:alert(1)",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "java\rscript:alert(1)",
        "\x01javascript:alert(1)",
        "  JaVaScRiPt:alert(1)",
        "JAVA\tSCRIPT:alert(1)",
        "vbscript:msgbox(1)",
    ])
    def test_dangerous_schemes_are_rejected(self, value):
        assert run_js(_uri_prelude(), f"isDangerousUri({json.dumps(value)})") is True

    @pytest.mark.parametrize("value", [
        "https://example.com/x",
        "/relative/path",
        "#anchor",
        "mailto:a@b.c",
        "data:image/png;base64,AAAA",
        "",
    ])
    def test_benign_uris_are_allowed(self, value):
        assert run_js(_uri_prelude(), f"isDangerousUri({json.dumps(value)})") is False

    def test_sanitizer_uses_the_scheme_check(self):
        """The old bypassable regex must no longer be referenced."""
        src = js_source()
        assert "SANITIZE_DANGEROUS_URI" not in src
        assert "isDangerousUri(attr.value)" in src


class TestUpdateSanitisesPayload:
    """update()/partial_update() sent layer payloads straight to the websocket.

    to_json()/to_html() run json_safe(), but the live push did not, so a NaN or
    inf coming out of a DataFrame column produced a NaN token that strict JSON
    parsers (including the browser) reject, breaking the whole update.
    """

    @staticmethod
    def _nan_layer():
        from shiny_deckgl import scatterplot_layer
        return scatterplot_layer(
            "pts",
            [{"position": [float("nan"), 55.0], "value": float("inf")}],
        )

    @pytest.mark.asyncio
    async def test_update_payload_is_strict_json(self):
        from shiny_deckgl import MapWidget
        sess = _FakeSession()
        await MapWidget("m").update(sess, [self._nan_layer()])
        handler, payload = sess.messages[-1]
        assert handler == "deck_update"
        json.dumps(payload, allow_nan=False)
        assert payload["layers"][0]["data"][0]["position"][0] is None

    @pytest.mark.asyncio
    async def test_partial_update_payload_is_strict_json(self):
        from shiny_deckgl import MapWidget
        sess = _FakeSession()
        await MapWidget("m").partial_update(sess, [self._nan_layer()])
        handler, payload = sess.messages[-1]
        assert handler == "deck_partial_update"
        json.dumps(payload, allow_nan=False)

    @pytest.mark.asyncio
    async def test_update_view_state_is_sanitised(self):
        from shiny_deckgl import MapWidget
        sess = _FakeSession()
        await MapWidget("m").update(sess, [], view_state={"longitude": float("nan")})
        json.dumps(sess.messages[-1][1], allow_nan=False)


class TestToHtmlEscapesViewState:
    """to_html() interpolated view_state into HTML attributes unescaped.

    self.id and self.style on the same <div> are escaped with html.escape, but
    every data-initial-* value was not, so a string view_state value could
    close the attribute and inject markup into the exported page.
    """

    def test_view_state_string_cannot_break_out_of_attribute(self):
        from shiny_deckgl import MapWidget
        evil = '1" onload="alert(1)'
        html = MapWidget("m", view_state={"longitude": evil}).to_html([])
        assert 'onload="alert(1)"' not in html
        assert "&quot;" in html

    def test_numeric_view_state_still_renders(self):
        from shiny_deckgl import MapWidget
        html = MapWidget("m", view_state={"longitude": 21.1, "latitude": 55.7}).to_html([])
        assert 'data-initial-longitude="21.1"' in html
        assert 'data-initial-latitude="55.7"' in html


class TestEasingParity:
    """enums.EasingFunction published 13 names; the JS EASINGS table had 4.

    The other 9 fell through `EASINGS[name] || identity` and silently animated
    linearly, so ease_in_expo and friends were accepted and ignored.
    """

    @staticmethod
    def _js_easing_names():
        import re
        src = js_source()
        m = re.search(r"const EASINGS = \{(.*?)\n  \};", src, re.S)
        assert m, "EASINGS table not found"
        return set(re.findall(r"'([a-z-]+)':", m.group(1)))

    def test_every_python_easing_has_a_js_implementation(self):
        from shiny_deckgl.enums import EasingFunction
        missing = {e.value for e in EasingFunction} - self._js_easing_names()
        assert not missing, f"easings with no JS implementation: {sorted(missing)}"

    def test_no_orphan_js_easings(self):
        from shiny_deckgl.enums import EasingFunction
        orphans = self._js_easing_names() - {e.value for e in EasingFunction}
        assert not orphans, f"JS easings not published by the enum: {sorted(orphans)}"

    @requires_node
    @pytest.mark.parametrize("name", [
        "linear", "ease-in-sine", "ease-out-sine", "ease-in-quad",
        "ease-out-quad", "ease-in-out-quad", "ease-in-expo",
        "ease-out-expo", "ease-in-out-expo",
    ])
    def test_added_easings_are_monotonic_unit_curves(self, name):
        """Each easing must map 0->0 and 1->1 and never leave [0, 1]."""
        import re
        src = js_source()
        m = re.search(r"(const EASINGS = \{.*?\n  \};)", src, re.S)
        prelude = m.group(1)
        expr = (
            "(function(){var f=EASINGS[%s];"
            "var xs=[0,0.1,0.25,0.5,0.75,0.9,1];"
            "var ys=xs.map(f);"
            "return {first:ys[0],last:ys[ys.length-1],"
            "inRange:ys.every(function(y){return y>=-1e-9&&y<=1+1e-9;}),"
            "monotonic:ys.every(function(y,i){return i===0||y>=ys[i-1]-1e-9;})};})()"
            % ("'" + name + "'")
        )
        got = run_js(prelude, expr)
        assert got["first"] == pytest.approx(0, abs=1e-9)
        assert got["last"] == pytest.approx(1, abs=1e-9)
        assert got["inRange"] is True
        assert got["monotonic"] is True


class TestColorQuantiles:
    """color_quantiles() binned with `v <= break`.

    Each break is the FIRST element of the upper quantile group, so testing
    `<=` pushed every boundary value one bin down. The consequence is that the
    maximum value can never exceed the last break, leaving the top colour of
    the palette unreachable.
    """

    def test_top_colour_is_reachable(self):
        from shiny_deckgl.colors import color_quantiles, color_range
        values = [0.0, 0.0, 0.0, 1.0]
        out = color_quantiles(values, n_bins=4)
        assert out[-1] == color_range(4)[-1]

    def test_bins_are_balanced_for_uniform_data(self):
        from shiny_deckgl.colors import color_quantiles
        values = [float(i) for i in range(10)]
        out = color_quantiles(values, n_bins=2)
        first, second = out[:5], out[5:]
        assert len(set(map(tuple, first))) == 1
        assert len(set(map(tuple, second))) == 1
        assert first[0] != second[0]

    def test_every_bin_used_for_uniform_data(self):
        from shiny_deckgl.colors import color_quantiles
        values = [float(i) for i in range(100)]
        assert len({tuple(c) for c in color_quantiles(values, n_bins=5)}) == 5

    def test_empty_and_constant_input_still_safe(self):
        from shiny_deckgl.colors import color_quantiles
        assert color_quantiles([], n_bins=4) == []
        out = color_quantiles([3.0, 3.0, 3.0], n_bins=4)
        assert len(out) == 3


class TestNormalizeRowsZeroRow:
    """normalize_rows() claimed to handle zero rows but left them all-zero.

    Replacing the zero denominator with 1.0 keeps the row summing to 0, which
    is not a probability vector; simulate_IHTR feeds those rows straight to
    rng.choice(p=...), which raises ValueError.
    """

    def test_zero_row_becomes_an_absorbing_self_loop(self):
        np = pytest.importorskip("numpy")
        from shiny_deckgl._sealmove import normalize_rows
        out = normalize_rows(np.array([
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 2.0],
            [0.0, 1.0, 1.0],
        ]))
        assert out[0].sum() == pytest.approx(1.0)
        assert out[0].tolist() == pytest.approx([1.0, 0.0, 0.0])

    def test_zero_row_is_usable_as_choice_probabilities(self):
        np = pytest.importorskip("numpy")
        from shiny_deckgl._sealmove import normalize_rows
        out = normalize_rows(np.array([[0.0, 0.0], [0.5, 0.5]]))
        np.random.default_rng(0).choice(2, size=5, p=out[0])

    def test_non_square_zero_row_falls_back_to_uniform(self):
        np = pytest.importorskip("numpy")
        from shiny_deckgl._sealmove import normalize_rows
        out = normalize_rows(np.array([[0.0, 0.0, 0.0, 0.0]]))
        assert out[0].tolist() == pytest.approx([0.25] * 4)

    def test_simulate_ihtr_survives_an_absorbing_state(self):
        """The end-to-end crash: a zero row in cfg.P reached rng.choice(p=...)."""
        pytest.importorskip("numpy")
        pytest.importorskip("pandas")
        import numpy as np
        from shiny_deckgl._sealmove import IHTRConfig, simulate_IHTR

        P = np.array([[0.5, 0.5, 0.0], [0.0, 0.0, 0.0], [0.2, 0.3, 0.5]])
        df = simulate_IHTR(IHTRConfig(P=P, n_agents=5, T=4), random_state=0)
        assert len(df) == 20
        assert set(df["cluster"]).issubset({0, 1, 2})

    def test_nonzero_rows_unchanged(self):
        np = pytest.importorskip("numpy")
        from shiny_deckgl._sealmove import normalize_rows
        out = normalize_rows(np.array([[1.0, 3.0]]))
        assert out[0].tolist() == pytest.approx([0.25, 0.75])


class TestCustomGeometryWithoutNumpy:
    """_maybe_encode() imported numpy unconditionally.

    custom_geometry() documents plain Python lists as supported input and numpy
    is an optional extra, so an install without numpy crashed on the documented
    happy path.
    """

    def test_custom_geometry_works_without_numpy(self, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "numpy", None)
        from shiny_deckgl.layers import custom_geometry
        out = custom_geometry({
            "positions": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            "indices": [0, 1, 2],
            "center": [21.0, 55.0],
        })
        assert out["_meshPositions"] == [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        assert out["_meshIndices"] == [0, 1, 2]

    def test_numpy_arrays_still_encode_to_binary(self):
        pytest.importorskip("numpy")
        import numpy as np
        from shiny_deckgl.layers import custom_geometry
        out = custom_geometry({
            "positions": np.zeros(9, dtype="float32"),
            "indices": np.array([0, 1, 2], dtype="uint32"),
            "center": [21.0, 55.0],
        })
        assert isinstance(out["_meshPositions"], dict)


class TestBathymetryPathHops:
    """make_lithuanian_bathymetry_data() used four .parent hops.

    src/shiny_deckgl/_demo_data.py needs three to reach the repo root
    (_demo_data.py -> shiny_deckgl -> src -> root); four lands one directory
    above it, so the bundled bathy.asc was never found and the function
    silently returned an empty list.
    """

    def test_repo_root_bathy_asc_is_found(self, tmp_path, monkeypatch):
        from shiny_deckgl import _demo_data
        root = Path(_demo_data.__file__).resolve().parents[2]
        assert (root / "bathy.asc").exists(), "fixture missing: repo-root bathy.asc"
        # Run from an unrelated cwd so the Path("bathy.asc") fallback cannot mask
        # a wrong number of hops.
        monkeypatch.chdir(tmp_path)
        out = _demo_data.make_lithuanian_bathymetry_data(sample_step=40)
        assert out, "bathymetry data was empty -- the .asc path did not resolve"


@requires_node
class TestPostProcessEffectConstruction:
    """buildEffects passed the whole spec dict as PostProcessEffect's module.

    deck.gl's signature is `new PostProcessEffect(module, props)`, where module
    is a luma.gl shader module object -- not the name string. The resulting
    throw happened while building the effects array, so one bad effect took
    every other effect down with it.
    """

    @staticmethod
    def _prelude(fake_globals: str) -> str:
        return "\n".join([
            "const deck = { PostProcessEffect: function (module, props) {",
            "  this.module = module; this.props = props; } };",
            fake_globals,
            extract_function("resolvePostProcessModule"),
            extract_function("buildEffects"),
        ])

    def test_module_and_props_are_passed_separately(self):
        prelude = self._prelude(
            "globalThis.luma = { vignette: { name: 'vignette', fs: '' } };"
        )
        got = run_js(prelude, (
            "(function(){var e=buildEffects([{type:'PostProcessEffect',"
            "shaderModule:'vignette',radius:0.5}]);"
            "return {n:e.length, moduleName:e[0].module.name, props:e[0].props};})()"
        ))
        assert got["n"] == 1
        assert got["moduleName"] == "vignette"
        assert got["props"] == {"radius": 0.5}

    def test_missing_module_drops_the_effect_without_throwing(self):
        prelude = self._prelude("globalThis.luma = {};")
        got = run_js(prelude, (
            "(function(){var e=buildEffects([{type:'PostProcessEffect',"
            "shaderModule:'vignette',radius:0.5}]);return e.length;})()"
        ))
        assert got == 0

    def test_a_broken_effect_does_not_kill_the_others(self):
        prelude = self._prelude(
            "globalThis.luma = { vignette: { name: 'vignette', fs: '' } };"
        )
        got = run_js(prelude, (
            "(function(){var e=buildEffects(["
            "{type:'PostProcessEffect',shaderModule:'nosuchmodule'},"
            "{type:'PostProcessEffect',shaderModule:'vignette',amount:1}]);"
            "return {n:e.length, name:e[0].module.name};})()"
        ))
        assert got["n"] == 1
        assert got["name"] == "vignette"


@requires_node
class TestAccessorExpressions:
    """The @@= whitelist only matched bare property/index chains.

    layers.py advertises "@@=d.depth_m * 5" and the demo ships that plus
    "@@=d.weight || 1"; both failed the regex. Worse, the rejection path used
    `continue`, leaving the literal "@@=..." STRING in layerProps, which deck.gl
    coerces to a constant NaN -- the layer renders nothing and only a
    console.warn says why.
    """

    @staticmethod
    def _prelude():
        return "\n".join([
            extract_var("ACCESSOR_DANGEROUS_PROPS_RE"),
            extract_var("ACCESSOR_ALLOWED_IDENTS"),
            extract_function("isSafeAccessorExpr"),
            extract_function("resolveAccessors"),
        ])

    def _resolve(self, expr):
        """Return {kind, value} for a layer prop carrying `expr`."""
        return run_js(self._prelude(), (
            "(function(){var p={getRadius:%s, id:'x'};resolveAccessors(p);"
            "if (typeof p.getRadius === 'function') "
            "  return {kind:'fn', value:p.getRadius({depth_m:3,weight:0,a:{b:7},"
            "    0:'zero',k:'kv',phase:'op'})};"
            "return {kind:typeof p.getRadius, value:p.getRadius===undefined?null:p.getRadius};})()"
            % json.dumps("@@=" + expr)
        ))

    @pytest.mark.parametrize("expr,expected", [
        ("d.depth_m", 3),
        ("d.depth_m * 5", 15),
        ("d.weight || 1", 1),
        ("d.a.b", 7),
        ('d["k"]', "kv"),
        ("d[0]", "zero"),
        ("d.phase === 'op' ? 1 : 0", 1),
        ("(d.depth_m + 1) / 2", 2),
        ("d.depth_m > 2 && d.weight === 0", True),
        ("-d.depth_m", -3),
    ])
    def test_documented_expressions_resolve(self, expr, expected):
        got = self._resolve(expr)
        assert got["kind"] == "fn", f"{expr!r} was not compiled to an accessor"
        assert got["value"] == expected

    @pytest.mark.parametrize("expr", [
        "d.constructor",
        "d.__proto__",
        "d.x.prototype",
        "window",
        "globalThis.fetch",
        "fetch('/x')",
        "d.f()",
        "alert(1)",
        "d = 1",
        "d.x; alert(1)",
        "() => 1",
        "`${d.x}`",
        "eval('1')",
        "d[globalThis]",
        "new Function('return 1')",
    ])
    def test_unsafe_expressions_are_rejected(self, expr):
        got = self._resolve(expr)
        assert got["kind"] != "fn", f"{expr!r} must not compile to an accessor"

    @pytest.mark.parametrize("expr", ["fetch('/x')", "d = 1", "() => 1"])
    def test_rejected_accessor_is_removed_not_left_as_a_string(self, expr):
        """A rejected accessor must not stay in layerProps as a raw string."""
        got = self._resolve(expr)
        assert got["kind"] != "string", (
            "the literal accessor string was handed to deck.gl, which coerces "
            "it to a constant NaN"
        )

    def test_every_accessor_shipped_by_the_package_is_accepted(self):
        """No expression the package itself emits may be silently dropped."""
        import re
        exprs = set()
        for f in SRC.rglob("*.py"):
            exprs.update(re.findall(r'"@@=([^"]*)"', f.read_text(encoding="utf-8")))
        exprs.discard("expr")  # docstring placeholder
        checks = ",".join(json.dumps(e) for e in sorted(exprs))
        bad = run_js(
            self._prelude(),
            "[%s].filter(function(e){return !isSafeAccessorExpr(e);})" % checks,
        )
        assert bad == [], f"package ships accessors its own whitelist rejects: {bad}"


@requires_node
class TestBuildViewsUnderscoreFallback:
    """buildViews resolved view classes with a bare deck[typeName] lookup.

    deck.gl 9.x exports experimental views with a leading underscore
    (deck._GlobeView), so the "GlobeView" string that views.py and enums.py
    emit never resolved and globe_view() silently produced no view at all.
    The LightingEffect branch already knows this -- it uses deck._SunLight.
    """

    @staticmethod
    def _prelude(fake_deck):
        return fake_deck + "\n" + extract_function("buildViews")

    def test_globe_view_resolves_via_the_underscore_export(self):
        prelude = self._prelude(
            "const deck = { _GlobeView: function (p) { this.name='_GlobeView'; this.props=p; } };"
        )
        got = run_js(prelude, (
            "(function(){var v=buildViews([{'@@type':'GlobeView',id:'globe'}]);"
            "return {n:v.length, name:v[0].name, id:v[0].props.id};})()"
        ))
        assert got["n"] == 1
        assert got["name"] == "_GlobeView"
        assert got["id"] == "globe"

    def test_plain_export_still_wins_over_the_underscore_form(self):
        prelude = self._prelude(
            "const deck = { MapView: function (p) { this.name='MapView'; },"
            " _MapView: function (p) { this.name='_MapView'; } };"
        )
        got = run_js(prelude, (
            "(function(){var v=buildViews([{'@@type':'MapView'}]);return v[0].name;})()"
        ))
        assert got == "MapView"

    def test_genuinely_unknown_view_is_still_dropped(self):
        prelude = self._prelude("const deck = {};")
        got = run_js(prelude, (
            "(function(){var v=buildViews([{'@@type':'NoSuchView'}]);return v.length;})()"
        ))
        assert got == 0

    def test_every_view_type_the_package_emits_is_reachable(self):
        """views.py / enums.py must not publish a view the JS cannot resolve."""
        from shiny_deckgl.enums import ViewType
        names = [v.value for v in ViewType]
        assert "GlobeView" in names


@requires_node
class TestPartialViewStateUpdate:
    """deck_update substituted hard defaults for omitted view-state keys.

    `zoom: vs.zoom != null ? vs.zoom : 1` meant update(view_state={"longitude":
    x}) snapped zoom to 1 and pitch/bearing to 0, so nudging one axis reset the
    whole camera. Omitted keys must simply not be sent.
    """

    @staticmethod
    def _prelude():
        return extract_function("buildCameraOptions")

    def test_omitted_keys_are_not_sent(self):
        got = run_js(self._prelude(), "buildCameraOptions({longitude: 21, latitude: 55})")
        assert got == {"center": [21, 55]}

    def test_provided_keys_are_forwarded(self):
        got = run_js(self._prelude(), "buildCameraOptions({zoom: 7, pitch: 30})")
        assert got == {"zoom": 7, "pitch": 30}

    def test_full_view_state_round_trips(self):
        got = run_js(self._prelude(), (
            "buildCameraOptions({longitude:21,latitude:55,zoom:7,pitch:30,bearing:15})"
        ))
        assert got == {"center": [21, 55], "zoom": 7, "pitch": 30, "bearing": 15}

    def test_zero_is_not_treated_as_missing(self):
        got = run_js(self._prelude(), "buildCameraOptions({zoom: 0, pitch: 0, bearing: 0})")
        assert got == {"zoom": 0, "pitch": 0, "bearing": 0}

    def test_lone_longitude_does_not_invent_a_latitude(self):
        got = run_js(self._prelude(), "buildCameraOptions({zoom: 5})")
        assert "center" not in got


class TestTemperatureGridIsPositionSeeded:
    """make_sea_temperature_grid() drew noise from a sequential RNG.

    The `continue` that skips out-of-bounds cells does not consume a draw, so
    which gaussian a cell receives depends on how many cells were filtered out
    before it. The comment says the noise is "seeded by position for
    consistency"; it was seeded by iteration order.
    """

    @staticmethod
    def _by_position(rows):
        return {tuple(r["position"]): r["temperature_c"] for r in rows}

    def test_bounds_do_not_change_a_cells_temperature(self):
        from shiny_deckgl._demo_data import make_sea_temperature_grid
        full = self._by_position(make_sea_temperature_grid(month=5))
        clipped = self._by_position(make_sea_temperature_grid(
            bounds={"sw": [20.0, 55.0], "ne": [22.0, 57.0]}, month=5))
        assert clipped, "the clipped viewport returned no cells"
        for pos, temp in clipped.items():
            assert full[pos] == temp, f"cell {pos} changed temperature when clipped"

    def test_month_still_changes_temperatures(self):
        from shiny_deckgl._demo_data import make_sea_temperature_grid
        jan = self._by_position(make_sea_temperature_grid(month=0))
        aug = self._by_position(make_sea_temperature_grid(month=7))
        assert jan != aug

    def test_repeated_calls_are_deterministic(self):
        from shiny_deckgl._demo_data import make_sea_temperature_grid
        a = self._by_position(make_sea_temperature_grid(month=3))
        b = self._by_position(make_sea_temperature_grid(month=3))
        assert a == b


class TestIbmStepIsMetricallyIsotropic:
    """make_seal_trips_ibm() added an isotropic displacement in degrees.

    One degree of latitude is ~111 km everywhere, but one degree of longitude
    is 111 km * cos(lat) -- about 62 km in the Baltic. Adding the same degree
    step to both axes therefore moves an animal ~1.8x further north-south than
    east-west, while the docstring calibrates SPEED_MAX against a km/h swim
    speed. The sibling make_seal_trips() already applies a 0.6 latitude factor.
    """

    def test_equal_degree_step_becomes_equal_metric_step(self):
        import math
        from shiny_deckgl._demo_data import _isotropic_degree_step
        lat = 56.0
        dlon, dlat = _isotropic_degree_step(1.0, 1.0, lat)
        east_km = dlon * 111.32 * math.cos(math.radians(lat))
        north_km = dlat * 111.32
        assert east_km == pytest.approx(north_km, rel=0.02)

    def test_longitude_component_is_untouched(self):
        from shiny_deckgl._demo_data import _isotropic_degree_step
        dlon, _ = _isotropic_degree_step(0.3, 0.7, 56.0)
        assert dlon == pytest.approx(0.3)

    def test_correction_matches_the_sibling_heuristic_in_the_baltic(self):
        """make_seal_trips() hardcodes 0.6; cos(56 deg) is 0.559."""
        from shiny_deckgl._demo_data import _isotropic_degree_step
        _, dlat = _isotropic_degree_step(0.0, 1.0, 56.0)
        assert dlat == pytest.approx(0.56, abs=0.05)

    def test_ibm_trips_still_generate(self):
        pytest.importorskip("numpy")
        from shiny_deckgl._demo_data import make_seal_trips_ibm
        trips = make_seal_trips_ibm(n_seals=3, sim_hours=48, seed=1)
        assert trips
        for t in trips:
            for lon, lat in [(p[0], p[1]) for p in t["path"]]:
                assert 9.0 <= lon <= 30.0
                assert 53.0 <= lat <= 66.0


class TestReactiveSelfInvalidation:
    """Documents the reactive rule the next two classes depend on.

    An Effect that both reads and writes the same reactive source invalidates
    itself, so it re-runs immediately and any invalidate_later() timer it armed
    is superseded. Isolating the read breaks the cycle.
    """

    @pytest.mark.asyncio
    async def test_reading_and_writing_the_same_value_loops(self):
        from shiny import reactive
        v, runs = reactive.Value(0), []

        @reactive.Effect
        def _e():
            runs.append(v())
            if len(runs) < 8:
                v.set(v.get() + 1)

        await reactive.flush()
        assert len(runs) == 8, "expected the effect to re-trigger itself"

    @pytest.mark.asyncio
    async def test_isolating_the_read_breaks_the_cycle(self):
        from shiny import reactive
        v, gate, runs = reactive.Value(0), reactive.Value(True), []

        @reactive.Effect
        def _e():
            gate()
            with reactive.isolate():
                runs.append(v())
                if len(runs) < 8:
                    v.set(v.get() + 1)

        await reactive.flush()
        assert len(runs) == 1


class TestTimelineAutoAdvanceIsolatesItsRead:
    """_auto_advance read input.step() and then wrote it via update_slider.

    The write invalidated the effect, so it re-ran at once and cancelled the
    invalidate_later timer it had just armed -- interval_ms never governed the
    animation cadence. The read must be isolated.
    """

    @staticmethod
    def _auto_advance_ast():
        import ast
        import inspect
        from shiny_deckgl import _timeline
        tree = ast.parse(inspect.getsource(_timeline))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_auto_advance":
                return node
        raise AssertionError("_auto_advance not found in _timeline.py")

    def test_step_is_read_inside_an_isolate_block(self):
        import ast
        fn = self._auto_advance_ast()

        isolated = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.With):
                src = ast.dump(node.items[0].context_expr)
                if "isolate" in src:
                    for inner in ast.walk(node):
                        isolated.add(id(inner))

        reads = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "step"
        ]
        assert reads, "expected _auto_advance to read input.step()"
        for r in reads:
            assert id(r) in isolated, (
                "input.step() is read without reactive.isolate(); the effect "
                "writes that same input, so it invalidates itself"
            )

    def test_invalidate_later_still_drives_the_cadence(self):
        import inspect
        from shiny_deckgl import _timeline
        src = inspect.getsource(_timeline)
        assert "invalidate_later" in src


class TestViewportFallbackPollIsBounded:
    """on_viewport_change re-armed invalidate_later(1.0) on every fallback run.

    A map the user never pans or zooms never produces the view-state input, so
    the fallback branch re-ran once a second for the whole session, re-invoking
    the loader and re-pushing the entire layer payload each time.
    """

    def test_polling_stops_once_the_viewport_arrives(self):
        from shiny_deckgl._viewport import _should_repoll
        assert _should_repoll(viewport_available=True, attempts=0) is False

    def test_polling_is_bounded_while_the_viewport_is_missing(self):
        from shiny_deckgl._viewport import _should_repoll
        assert _should_repoll(viewport_available=False, attempts=0) is True
        assert _should_repoll(viewport_available=False, attempts=1) is True
        assert _should_repoll(viewport_available=False, attempts=10_000) is False

    def test_the_bound_is_finite(self):
        from shiny_deckgl._viewport import _should_repoll
        attempts = 0
        while _should_repoll(viewport_available=False, attempts=attempts):
            attempts += 1
            assert attempts < 1000, "fallback polling never terminates"
        assert attempts > 0, "fallback must poll at least once"


class TestStyleIsPerSession:
    """Demo MapWidgets are module-level singletons shared by every session.

    set_style() wrote self.style on that shared object, so one visitor
    switching to the dark basemap changed what a different visitor's export
    (and initial render) reported.
    """

    def test_set_style_does_not_mutate_the_shared_default(self):
        from shiny_deckgl import MapWidget
        from shiny_deckgl.colors import CARTO_DARK, CARTO_POSITRON
        import asyncio

        w = MapWidget("m", style=CARTO_POSITRON)
        asyncio.run(w.set_style(_FakeSession(), CARTO_DARK))
        assert w.style == CARTO_POSITRON, (
            "set_style mutated the shared widget default; a second session "
            "would inherit the first session's basemap"
        )

    def test_each_session_sees_its_own_style(self):
        from shiny_deckgl import MapWidget
        from shiny_deckgl.colors import CARTO_DARK, CARTO_POSITRON, CARTO_VOYAGER
        import asyncio

        w = MapWidget("m", style=CARTO_POSITRON)
        a, b = _FakeSession(), _FakeSession()
        asyncio.run(w.set_style(a, CARTO_DARK))
        asyncio.run(w.set_style(b, CARTO_VOYAGER))

        assert w.current_style(a) == CARTO_DARK
        assert w.current_style(b) == CARTO_VOYAGER
        assert w.current_style(None) == CARTO_POSITRON

    def test_set_style_still_sends_the_message(self):
        from shiny_deckgl import MapWidget
        from shiny_deckgl.colors import CARTO_DARK
        import asyncio

        w = MapWidget("m")
        sess = _FakeSession()
        asyncio.run(w.set_style(sess, CARTO_DARK, diff=True))
        handler, payload = sess.messages[0]
        assert handler == "deck_set_style"
        assert payload["style"] == CARTO_DARK
        assert payload["diff"] is True

    def test_export_reflects_the_exporting_session(self):
        from shiny_deckgl import MapWidget
        from shiny_deckgl.colors import CARTO_DARK, CARTO_POSITRON
        import asyncio

        w = MapWidget("m", style=CARTO_POSITRON)
        a, b = _FakeSession(), _FakeSession()
        asyncio.run(w.set_style(a, CARTO_DARK))

        assert CARTO_DARK in w.to_html([], session=a)
        assert CARTO_POSITRON in w.to_html([], session=b)

    def test_export_without_a_session_uses_the_default(self):
        from shiny_deckgl import MapWidget
        from shiny_deckgl.colors import CARTO_POSITRON
        w = MapWidget("m", style=CARTO_POSITRON)
        assert CARTO_POSITRON in w.to_html([])


def _app_server_ast():
    import ast
    return ast.parse((SRC / "_app_server.py").read_text(encoding="utf-8"))


def _calls(node, owner, attr):
    import ast
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == attr and isinstance(n.func.value, ast.Name)
                and n.func.value.id == owner):
            return True
    return False


class TestSingleOwnerForAdvWidgetLayers:
    """Two effect groups drove adv_widget with divergent state.

    Eight effects thread the layer list through the _adv_layers reactive value;
    _v1_layers built its own list and pushed it without recording it. Toggling
    brushing therefore wiped the 3-D layers, and the next lighting change wiped
    the brushing layer back out again.
    """

    def test_every_adv_widget_writer_goes_through_adv_layers(self):
        import ast
        tree = _app_server_ast()
        orphans = []
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if fn.name == "server":
                continue  # the enclosing scope contains every inner function
            if not _calls(fn, "adv_widget", "update"):
                continue
            if not (_calls(fn, "_adv_layers", "set") or _calls(fn, "_adv_layers", "get")):
                orphans.append(f"{fn.name} (line {fn.lineno})")
        assert not orphans, (
            "these effects push layers to adv_widget without recording them in "
            f"_adv_layers, so they silently wipe the others: {orphans}"
        )

    def test_there_is_more_than_one_writer_to_guard(self):
        """Guards the guard: the invariant is meaningless with one writer."""
        import ast
        tree = _app_server_ast()
        writers = [
            fn.name for fn in ast.walk(tree)
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
            and fn.name != "server" and _calls(fn, "adv_widget", "update")
        ]
        assert len(writers) > 1


class TestWidgetGalleryInitRunsOnce:
    """_wg_init was a bare reactive.Effect that read every wg_* input.

    _wg_active_widgets() and _wg_layers() read all twenty toggles, so the
    "init" effect took a dependency on each one and re-ran on every toggle --
    an exact duplicate of _wg_update_map, doubling every full map update.
    """

    @staticmethod
    def _wg_init_node():
        import ast
        for node in ast.walk(_app_server_ast()):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_wg_init":
                return node
        raise AssertionError("_wg_init not found")

    def test_init_isolates_its_input_reads(self):
        import ast
        fn = self._wg_init_node()

        isolated = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.With) and any(
                "isolate" in ast.dump(item.context_expr) for item in node.items
            ):
                for inner in ast.walk(node):
                    isolated.add(id(inner))

        reads = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in {"_wg_active_widgets", "_wg_layers"}
        ]
        assert reads, "expected _wg_init to build the initial widget/layer state"
        for r in reads:
            assert id(r) in isolated, (
                "_wg_init reads the wg_* inputs reactively, so it re-runs on "
                "every toggle and duplicates _wg_update_map"
            )

    def test_the_duplicate_effect_still_exists(self):
        """The per-toggle updates must still be handled by _wg_update_map."""
        import ast
        names = [
            n.name for n in ast.walk(_app_server_ast())
            if isinstance(n, ast.AsyncFunctionDef)
        ]
        assert "_wg_update_map" in names


@requires_node
class TestUpdateGenerationGuard:
    """deck_update awaited the SVG atlas preload with no generation guard.

    Two updates in quick succession race: the second may carry no SVG atlas and
    resolve instantly, while the first is still rasterising. The first then
    resolves last and renders its own captured layersData, so what is on screen
    disagrees with instance.lastLayers.
    """

    @staticmethod
    def _prelude():
        return "\n".join([
            extract_function("claimUpdateGeneration"),
            extract_function("isStaleUpdate"),
        ])

    def test_the_latest_claim_is_not_stale(self):
        got = run_js(self._prelude(), (
            "(function(){var i={};var g=claimUpdateGeneration(i);"
            "return isStaleUpdate(i,g);})()"
        ))
        assert got is False

    def test_an_older_claim_is_stale_once_superseded(self):
        got = run_js(self._prelude(), (
            "(function(){var i={};var a=claimUpdateGeneration(i);"
            "var b=claimUpdateGeneration(i);"
            "return {old:isStaleUpdate(i,a), latest:isStaleUpdate(i,b)};})()"
        ))
        assert got == {"old": True, "latest": False}

    def test_generations_are_per_instance(self):
        got = run_js(self._prelude(), (
            "(function(){var i={},j={};var a=claimUpdateGeneration(i);"
            "claimUpdateGeneration(j);claimUpdateGeneration(j);"
            "return isStaleUpdate(i,a);})()"
        ))
        assert got is False

    def test_deck_update_actually_uses_the_guard(self):
        src = js_source()
        assert "claimUpdateGeneration(instance)" in src
        assert "isStaleUpdate(instance" in src


@requires_node
class TestPausedTripsAnimationStaysPaused:
    """deck_update / deck_partial_update called startTripsAnimation blindly.

    An animation the user had explicitly paused resumed playing on the next
    layer update, because nothing recorded that the pause was deliberate.
    """

    @staticmethod
    def _prelude():
        return extract_function("shouldStartTripsAnimation")

    def test_an_update_does_not_resurrect_a_paused_animation(self):
        got = run_js(self._prelude(),
                     "shouldStartTripsAnimation({_tripsPaused: true}, true)")
        assert got is False

    def test_an_update_starts_an_unpaused_animation(self):
        got = run_js(self._prelude(),
                     "shouldStartTripsAnimation({}, true)")
        assert got is True

    def test_an_explicit_resume_overrides_the_pause(self):
        got = run_js(self._prelude(),
                     "shouldStartTripsAnimation({_tripsPaused: true}, false)")
        assert got is True

    def test_pause_records_the_intent_and_resume_clears_it(self):
        src = js_source()
        assert "instance._tripsPaused = true" in src
        assert "instance._tripsPaused = false" in src

    def test_both_update_paths_pass_the_from_update_flag(self):
        """The guard is useless unless deck_update actually opts into it."""
        import re
        src = js_source()
        calls = re.findall(r"^\s*startTripsAnimation\((.*?)\);", src, re.M)
        assert len(calls) == 4, f"expected 4 call sites, found {len(calls)}"
        flagged = [c for c in calls if c.endswith(", true")]
        assert len(flagged) == 2, (
            "deck_update and deck_partial_update must pass fromUpdate=true; "
            f"call sites: {calls}"
        )


@requires_node
class TestExportCompositesTheDeckCanvas:
    """deck_export_image screenshotted map.getCanvas() only.

    Outside interleaved mode deck.gl renders into its own canvas stacked above
    the MapLibre one, so every deck.gl layer was missing from the export. The
    two canvases have to be composited.
    """

    @staticmethod
    def _prelude():
        fake_doc = (
            "const __calls = [];"
            "const document = { createElement: function () {"
            "  return { width: 0, height: 0, getContext: function () {"
            "    return { drawImage: function (c) { __calls.push(c.tag); } }; } };"
            "} };"
        )
        return fake_doc + "\n" + extract_function("compositeMapCanvases")

    def test_both_canvases_are_drawn(self):
        got = run_js(self._prelude(), (
            "(function(){var b={tag:'base',width:800,height:600};"
            "var o={tag:'deck',width:800,height:600};"
            "var out=compositeMapCanvases(b,o);"
            "return {calls:__calls, w:out.width, h:out.height};})()"
        ))
        assert got["calls"] == ["base", "deck"]
        assert (got["w"], got["h"]) == (800, 600)

    def test_interleaved_mode_needs_no_compositing(self):
        """When deck renders into the MapLibre canvas there is one canvas."""
        got = run_js(self._prelude(), (
            "(function(){var b={tag:'base',width:10,height:10};"
            "var out=compositeMapCanvases(b,b);return out.tag;})()"
        ))
        assert got == "base"

    def test_missing_overlay_canvas_falls_back_to_the_base(self):
        got = run_js(self._prelude(), (
            "(function(){var b={tag:'base',width:10,height:10};"
            "return compositeMapCanvases(b,null).tag;})()"
        ))
        assert got == "base"

    def test_export_handler_composites_before_encoding(self):
        src = js_source()
        assert "compositeMapCanvases(" in src
        assert "toDataURL" in src


class TestPackagingMetadataIsConsistent:
    """The declared Python floor drifted below what Shiny actually requires.

    Every shiny release from 1.6.2 on requires Python >= 3.10, but the package
    advertised >=3.9 in pyproject.toml and in the conda recipe, so on 3.9 the
    package's own `shiny>=1.6.3` constraint was unsatisfiable. The tool targets
    (ruff, mypy) must not drift from the declared floor either.
    """

    MIN_PYTHON = (3, 10)

    @staticmethod
    def _pyproject():
        tomllib = pytest.importorskip("tomllib")
        root = Path(__file__).resolve().parents[1]
        return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    def test_requires_python_covers_the_shiny_floor(self):
        req = self._pyproject()["project"]["requires-python"]
        assert req == ">=%d.%d" % self.MIN_PYTHON, (
            f"requires-python is {req!r}; shiny >= 1.6.2 needs "
            ">=%d.%d" % self.MIN_PYTHON
        )

    def test_ruff_and_mypy_target_the_same_floor(self):
        cfg = self._pyproject()
        major, minor = self.MIN_PYTHON
        assert cfg["tool"]["ruff"]["target-version"] == f"py{major}{minor}"
        assert cfg["tool"]["mypy"]["python_version"] == f"{major}.{minor}"

    def test_conda_recipe_agrees_with_pyproject(self):
        root = Path(__file__).resolve().parents[1]
        recipe = (root / "conda.recipe" / "meta.yaml").read_text(encoding="utf-8")
        floor = "python >=%d.%d" % self.MIN_PYTHON
        pins = [ln.strip(" -") for ln in recipe.splitlines() if "python >=" in ln]
        assert pins, "no python pin found in the conda recipe"
        for pin in pins:
            assert pin == floor, f"conda recipe pins {pin!r}, expected {floor!r}"

    def test_cdn_versions_are_exact_pins(self):
        """CDN assets must stay exactly pinned for deterministic builds."""
        import re
        from shiny_deckgl import _cdn
        for name in dir(_cdn):
            if not name.endswith("_VERSION"):
                continue
            val = getattr(_cdn, name)
            assert re.fullmatch(r"\d+\.\d+\.\d+", val), f"{name}={val!r} is not an exact pin"


class TestCoordinateSystemMatchesDeckGL9:
    """CoordinateSystem still carried deck.gl 8's integer constants.

    deck.gl 9 replaced them with strings -- COORDINATE_SYSTEM.LNGLAT is
    "lnglat", not 1 -- and rejects the integers outright with
    "Invalid coordinateSystem: 1" at draw time. Since scatterplot_layer()
    defaults to LNGLAT, the default layer silently failed to render.

    Found by driving the standalone export in a real browser; the static
    review missed it because both sides look internally consistent.
    """

    # Values read from deck.COORDINATE_SYSTEM in Chromium, deck.gl 9.3.11/9.4.0.
    DECKGL_9 = {
        "DEFAULT": "default",
        "LNGLAT": "lnglat",
        "METER_OFFSETS": "meter-offsets",
        "LNGLAT_OFFSETS": "lnglat-offsets",
        "CARTESIAN": "cartesian",
    }

    def test_enum_values_are_the_deckgl_9_strings(self):
        from shiny_deckgl import COORDINATE_SYSTEM
        for name, expected in self.DECKGL_9.items():
            member = getattr(COORDINATE_SYSTEM, "IDENTITY" if name == "DEFAULT" else name)
            assert member.value == expected, f"{name} is {member.value!r}, deck.gl 9 wants {expected!r}"

    def test_default_layer_emits_a_valid_coordinate_system(self):
        from shiny_deckgl import scatterplot_layer
        lyr = scatterplot_layer("pts", [{"position": [21.0, 55.0]}])
        assert lyr["coordinateSystem"] in self.DECKGL_9.values()

    def test_serialised_layer_carries_a_string_not_an_int(self):
        from shiny_deckgl import MapWidget, scatterplot_layer
        spec = json.loads(MapWidget("m").to_json([
            scatterplot_layer("pts", [{"position": [21.0, 55.0]}])
        ]))
        cs = spec["layers"][0]["coordinateSystem"]
        assert isinstance(cs, str), f"coordinateSystem serialised as {type(cs).__name__}"
        assert cs == "lnglat"

    def test_mesh_helper_uses_meter_offsets_by_name(self):
        pytest.importorskip("numpy")
        from shiny_deckgl.layers import custom_geometry
        out = custom_geometry({
            "positions": [0.0, 0.0, 0.0], "indices": [0], "center": [21.0, 55.0],
        })
        assert out["coordinateSystem"] == "meter-offsets"

    @requires_node
    def test_js_still_accepts_the_legacy_integers(self):
        """Apps that hardcoded deck.gl 8 integers must not start failing."""
        prelude = (extract_var("LEGACY_COORDINATE_SYSTEMS") + "\n"
                   + extract_function("normaliseCoordinateSystem"))
        cases = {"1": "lnglat", "2": "meter-offsets", "3": "lnglat-offsets",
                 "0": "cartesian", "-1": "default"}
        for raw, expected in cases.items():
            got = run_js(prelude, f"normaliseCoordinateSystem({raw})")
            assert got == expected, f"legacy {raw} -> {got!r}, expected {expected!r}"

    @requires_node
    def test_js_passes_through_the_modern_strings(self):
        prelude = (extract_var("LEGACY_COORDINATE_SYSTEMS") + "\n"
                   + extract_function("normaliseCoordinateSystem"))
        for s in ("lnglat", "meter-offsets", "cartesian"):
            assert run_js(prelude, f"normaliseCoordinateSystem({json.dumps(s)})") == s


class TestTextLayerRendersNonAsciiText:
    """TextLayer built an ASCII-only font atlas.

    deck.gl's default characterSet covers ASCII, so any label outside it warns
    `Missing character` and renders a gap. On a Lithuanian project that means
    "Klaipeda" cannot be spelled correctly -- the demo logged
    `deck: Missing character: e (279)` for the e with a dot above.
    """

    def test_character_set_is_derived_from_the_data(self):
        from shiny_deckgl import text_layer
        lyr = text_layer("labels", [{"position": [21.0, 55.0], "text": "Klaip\u0117da"}])
        assert lyr.get("characterSet") == "auto", (
            "TextLayer needs characterSet='auto' so deck.gl builds the atlas "
            "from the actual labels")

    def test_explicit_character_set_still_wins(self):
        from shiny_deckgl import text_layer
        lyr = text_layer("labels", [], characterSet=["a", "b"])
        assert lyr["characterSet"] == ["a", "b"]


class TestGridCellLayerUsesCurrentAccessor:
    """grid_cell_layer defaulted to getColor, deprecated in deck.gl 9.

    deck.gl warns `GridCellLayer: getColor is deprecated ... Use
    getFillColor/getLineColor instead` and will remove it in a later version.
    """

    def test_default_is_get_fill_color(self):
        from shiny_deckgl import grid_cell_layer
        lyr = grid_cell_layer("g", [{"position": [21.0, 55.0], "elevation": 1}])
        assert "getFillColor" in lyr
        assert "getColor" not in lyr

    def test_caller_supplied_get_color_is_preserved(self):
        """Explicit getColor still works -- deck.gl accepts it, with a warning."""
        from shiny_deckgl import grid_cell_layer
        lyr = grid_cell_layer("g", [], getColor=[1, 2, 3])
        assert lyr["getColor"] == [1, 2, 3]


class TestUnavailableWidgetsAreDocumented:
    """fps_widget() and view_selector_widget() resolve to no deck.gl class.

    See tests/test_widgets_resolve.py: deck.gl 9.3.6/9.3.11/9.4.0 all export the
    same widget set, and neither FpsWidget nor ViewSelectorWidget is in it.
    """

    def test_docstrings_warn_that_the_widget_is_unavailable(self):
        from shiny_deckgl.widgets import fps_widget, view_selector_widget
        for fn in (fps_widget, view_selector_widget):
            assert "not available" in (fn.__doc__ or "").lower(), (
                f"{fn.__name__} resolves to nothing; its docstring must say so")


class TestCredentialedLayersAreNotFetchedUnconditionally:
    """The demo always fetched Google's 3D Tiles root, which needs an API key.

    `_add()` sets `visible` from the toggle but still includes the layer, and
    deck.gl loads a layer's `data` regardless of visibility. So every page load
    requested https://tile.googleapis.com/v1/3dtiles/root.json without a key,
    got 403, and raised an unhandled page error -- even with the toggle off.
    """

    @staticmethod
    def _is_tile3d_add(node):
        import ast
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_add" and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "gl_tile_3d")

    def test_the_tileset_is_only_requested_when_enabled(self):
        """Guarded by its own toggle, so a disabled layer costs no request."""
        import ast
        tree = _app_server_ast()   # parse once: node identity must be comparable

        calls = [n for n in ast.walk(tree) if self._is_tile3d_add(n)]
        assert calls, "the gl_tile_3d layer is no longer added"

        guarded_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and "gl_tile_3d" in ast.dump(node.test):
                for inner in ast.walk(node):
                    if self._is_tile3d_add(inner):
                        guarded_calls.add(id(inner))

        assert all(id(c) in guarded_calls for c in calls), (
            "the Google 3D Tiles layer is added unconditionally; deck.gl "
            "fetches its data even when visible=False, so the demo 403s on "
            "every page load")

    def test_the_key_requirement_is_documented_at_the_call_site(self):
        src = (SRC / "_app_server.py").read_text(encoding="utf-8")
        idx = src.find("tile.googleapis.com")
        assert idx != -1
        nearby = src[max(0, idx - 600):idx]
        assert "API key" in nearby, (
            "the call site should say that this endpoint needs an API key")
