"""Playwright smoke-test for the comprehensive demo.

Usage:
    micromamba run -n shiny python tests/test_demo_playwright.py
"""
from __future__ import annotations

import subprocess
import sys
import time

from playwright.sync_api import sync_playwright


PORT = 18765
URL = f"http://127.0.0.1:{PORT}"


def start_server():
    """Launch the demo as a subprocess and wait for it to be ready."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", "examples/demo.py",
         "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # Give the server time to start
    time.sleep(5)
    return proc


def main():
    proc = start_server()
    errors: list[str] = []
    console_msgs: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Capture console messages and errors
            page.on("console", lambda msg: console_msgs.append(
                f"[{msg.type}] {msg.text}"
            ))
            page.on("pageerror", lambda err: errors.append(str(err)))

            print(f"Navigating to {URL} ...")
            page.goto(URL, wait_until="networkidle", timeout=30000)
            print("Page loaded.")

            # Wait for Shiny to connect
            time.sleep(3)

            # --- Check 1: page title ---
            title = page.title()
            print(f"Page title: {title}")

            # --- Check 2: head scripts loaded ---
            deck_script = page.query_selector('script[src*="deck.gl"]')
            maplibre_script = page.query_selector('script[src*="maplibre-gl"]')
            maplibre_css = page.query_selector('link[href*="maplibre-gl"]')
            print(f"deck.gl script tag:    {'FOUND' if deck_script else 'MISSING'}")
            print(f"maplibre-gl script:    {'FOUND' if maplibre_script else 'MISSING'}")
            print(f"maplibre-gl CSS:       {'FOUND' if maplibre_css else 'MISSING'}")

            # --- Check 3: map container div ---
            map_div = page.query_selector('#demo_map')
            print(f"Map div #demo_map:     {'FOUND' if map_div else 'MISSING'}")
            if map_div:
                bbox = map_div.bounding_box()
                print(f"  bounding box:        {bbox}")
                classes = map_div.get_attribute("class")
                style = map_div.get_attribute("style")
                print(f"  class:               {classes}")
                print(f"  style:               {style}")

            # --- Check 4: MapLibre canvas ---
            canvas = page.query_selector('#demo_map canvas.maplibregl-canvas')
            print(f"MapLibre canvas:       {'FOUND' if canvas else 'MISSING'}")

            # --- Check 5: Check if maplibregl is defined ---
            has_maplibre = page.evaluate("typeof maplibregl !== 'undefined'")
            has_deck = page.evaluate("typeof deck !== 'undefined'")
            has_instances = page.evaluate(
                "typeof window.__deckgl_instances !== 'undefined'"
            )
            instance_keys = page.evaluate(
                "Object.keys(window.__deckgl_instances || {})"
            )
            print(f"window.maplibregl:     {'defined' if has_maplibre else 'UNDEFINED'}")
            print(f"window.deck:           {'defined' if has_deck else 'UNDEFINED'}")
            print(f"__deckgl_instances:    {'defined' if has_instances else 'UNDEFINED'}")
            print(f"  instance keys:       {instance_keys}")

            # --- Check 6: inline JS presence (deckgl-init.js content) ---
            all_scripts = page.query_selector_all("script:not([src])")
            inline_js_present = False
            for s in all_scripts:
                content = s.inner_text()
                if "__deckgl_instances" in content or "initMap" in content:
                    inline_js_present = True
                    break
            print(f"deckgl-init.js inline: {'FOUND' if inline_js_present else 'MISSING'}")

            # --- Check 7: data attributes on map div ---
            if map_div:
                data_lon = map_div.get_attribute("data-initial-longitude")
                data_lat = map_div.get_attribute("data-initial-latitude")
                data_style = map_div.get_attribute("data-style")
                print(f"  data-initial-lon:    {data_lon}")
                print(f"  data-initial-lat:    {data_lat}")
                print(f"  data-style:          {data_style}")

            # --- Check 8: look for Shiny connected ---
            shiny_connected = page.evaluate(
                "document.querySelector('html').classList.contains('shiny-busy') || "
                "document.querySelector('html').classList.contains('shiny-idle')"
            )
            html_classes = page.evaluate(
                "document.querySelector('html').className"
            )
            print(f"Shiny state classes:   {html_classes}")

            # --- Take a screenshot ---
            page.screenshot(path="tests/demo_screenshot.png", full_page=True)
            print("Screenshot saved to tests/demo_screenshot.png")

            # --- Print console messages ---
            print(f"\n--- Console messages ({len(console_msgs)}) ---")
            for msg in console_msgs[:30]:
                print(f"  {msg}")

            print(f"\n--- JS errors ({len(errors)}) ---")
            for err in errors[:10]:
                print(f"  ERROR: {err}")

            # --- Dump relevant HTML ---
            head_html = page.evaluate(
                "document.head.innerHTML.substring(0, 3000)"
            )
            print(f"\n--- <head> (first 3000 chars) ---")
            print(head_html)

            browser.close()

    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # Summary
    print("\n========== SUMMARY ==========")
    if not errors:
        print("No JS errors detected.")
    else:
        print(f"{len(errors)} JS errors!")
    if instance_keys:
        print(f"Map instances: {instance_keys} — map should be rendering")
    else:
        print("NO map instances — map is NOT rendering!")


if __name__ == "__main__":
    main()
