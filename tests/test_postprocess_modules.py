"""post_process_effect() modules: documented list, client table and CDN config agree."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "src" / "shiny_deckgl" / "resources" / "deckgl-init.js").read_text(encoding="utf-8")


def _client_modules() -> set[str]:
    table = re.search(r"var LUMA_EFFECT_FILES = \{(.*?)\};", JS, re.S).group(1)
    return set(re.findall(r"^\s*(\w+):", table, re.M))


def _documented_modules() -> set[str]:
    from shiny_deckgl.effects import post_process_effect
    doc = post_process_effect.__doc__
    supported = doc.split("Supported:")[1].split("are not available")[0]
    listed = set(re.findall(r'- ``"(\w+)"``', supported))
    return listed


def test_documented_modules_are_the_ones_the_client_loads():
    assert _documented_modules() == _client_modules()


def test_client_paths_are_under_the_postprocessing_dist():
    table = re.search(r"var LUMA_EFFECT_FILES = \{(.*?)\};", JS, re.S).group(1)
    paths = re.findall(r":\s*'([^']+)'", table)
    assert paths and all(re.fullmatch(r"(image-[a-z]+-filters|fxaa)/[a-z]+", p) for p in paths), paths


UNAVAILABLE = {"edgeWork", "tiltShift", "triangleBlur", "zoomBlur"}


def test_enum_members_are_loadable_or_documented_unavailable():
    from shiny_deckgl.enums import PostProcessShader
    values = {m.value for m in PostProcessShader}
    assert values - UNAVAILABLE == _client_modules()
    doc = PostProcessShader.__doc__
    assert all(m.name in doc for m in PostProcessShader if m.value in UNAVAILABLE)


def test_cdn_config_publishes_the_pinned_effects_base():
    from shiny_deckgl._cdn import CDN_CONFIG_JSON, LUMA_EFFECTS_VERSION
    body = re.search(r">(.*)</script>", CDN_CONFIG_JSON).group(1)
    base = json.loads(body)["lumaEffects"]
    assert f"@luma.gl/effects@{LUMA_EFFECTS_VERSION}/" in base
    assert base.endswith("/dist/passes/postprocessing/")


def test_standalone_export_carries_the_cdn_config(tmp_path):
    from shiny_deckgl import MapWidget, post_process_effect
    html = MapWidget("x").to_html([], effects=[post_process_effect("vignette")])
    assert 'id="shiny-deckgl-cdn"' in html
    assert "__deckgl_preloadEffects" in html
