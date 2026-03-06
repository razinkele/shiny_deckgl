"""Deep Playwright diagnostic — check layers, Shiny connection, and deck overlay.

Note: This is a diagnostic script, not a pytest test suite.
      For pytest-compatible E2E tests, see test_e2e_playwright.py.
"""
from __future__ import annotations

import subprocess
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore


PORT = 18766
URL = f"http://127.0.0.1:{PORT}"


def start_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", "examples/demo.py",
         "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(6)
    return proc


def main():
    if sync_playwright is None:
        print("ERROR: playwright not installed. Run: pip install playwright")
        return

    proc = start_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            errors = []
            console_msgs = []
            page.on("console", lambda msg: console_msgs.append(
                f"[{msg.type}] {msg.text}"
            ))
            page.on("pageerror", lambda err: errors.append(str(err)))

            print(f"Navigating to {URL} ...")
            page.goto(URL, wait_until="networkidle", timeout=30000)
            print("Page loaded. Waiting 5s for Shiny to connect and push layers...")
            time.sleep(5)

            # 1. Check Shiny connection state
            html_classes = page.evaluate("document.documentElement.className")
            print(f"\n=== Shiny State ===")
            print(f"  HTML classes: '{html_classes}'")
            shiny_connected = "shiny-idle" in html_classes or "shiny-busy" in html_classes
            print(f"  Shiny connected: {shiny_connected}")

            # 2. Check if Shiny object exists and is functional
            shiny_info = page.evaluate("""(() => {
                if (typeof Shiny === 'undefined') return 'Shiny undefined';
                if (!Shiny.setInputValue) return 'Shiny.setInputValue missing';
                if (!Shiny.addCustomMessageHandler) return 'Shiny.addCustomMessageHandler missing';
                return 'Shiny OK';
            })()""")
            print(f"  Shiny object: {shiny_info}")

            # 3. Check deck.gl instances
            print(f"\n=== deck.gl Instances ===")
            instances_info = page.evaluate("""(() => {
                const inst = window.__deckgl_instances;
                if (!inst) return {exists: false};
                const keys = Object.keys(inst);
                const result = {exists: true, keys: keys, details: {}};
                keys.forEach(k => {
                    const i = inst[k];
                    result.details[k] = {
                        hasMap: !!i.map,
                        hasOverlay: !!i.overlay,
                        hasTooltipConfig: !!i.tooltipConfig,
                        lastLayersCount: i.lastLayers ? i.lastLayers.length : 0,
                        mapLoaded: i.map ? i.map.loaded() : false,
                        mapStyle: i.map ? i.map.getStyle().name : 'unknown',
                    };
                    // Check overlay layers
                    try {
                        const overlayProps = i.overlay._props || i.overlay.props || {};
                        result.details[k].overlayLayerCount = overlayProps.layers ? overlayProps.layers.length : -1;
                    } catch(e) {
                        result.details[k].overlayError = e.message;
                    }
                });
                return result;
            })()""")
            print(f"  Exists: {instances_info.get('exists')}")
            print(f"  Keys: {instances_info.get('keys')}")
            for k, v in instances_info.get('details', {}).items():
                print(f"  [{k}]:")
                for prop, val in v.items():
                    print(f"    {prop}: {val}")

            # 4. Check custom message handlers registered
            print(f"\n=== Custom Message Handlers ===")
            handlers = page.evaluate("""(() => {
                // Shiny stores handlers internally
                const result = {};
                const names = ['deck_update', 'deck_layer_visibility', 'deck_add_drag_marker'];
                names.forEach(n => {
                    try {
                        // Check if handler was registered by trying to find it
                        result[n] = typeof Shiny !== 'undefined' ? 'Shiny exists' : 'no Shiny';
                    } catch(e) {
                        result[n] = 'error: ' + e.message;
                    }
                });
                return result;
            })()""")
            for name, status in handlers.items():
                print(f"  {name}: {status}")

            # 5. Try to manually check if shiny:connected event has fired
            print(f"\n=== Init Check ===")
            init_check = page.evaluate("""(() => {
                const maps = document.querySelectorAll('.deckgl-map');
                const result = {mapDivCount: maps.length, mapDivIds: []};
                maps.forEach(m => {
                    result.mapDivIds.push(m.id);
                });
                // Check if maplibregl canvas exists inside the map div
                const mapEl = document.getElementById('demo_map');
                if (mapEl) {
                    result.hasCanvas = !!mapEl.querySelector('canvas');
                    result.childCount = mapEl.children.length;
                    result.childTags = Array.from(mapEl.children).map(c => c.tagName + '.' + c.className).slice(0, 10);
                }
                return result;
            })()""")
            for k, v in init_check.items():
                print(f"  {k}: {v}")

            # 6. Check WebSocket / Shiny session
            print(f"\n=== WebSocket ===")
            ws_info = page.evaluate("""(() => {
                try {
                    if (typeof Shiny !== 'undefined' && Shiny.shinyapp) {
                        const ws = Shiny.shinyapp.$socket;
                        return {
                            exists: !!ws,
                            readyState: ws ? ws.readyState : -1,
                            // 0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED
                        };
                    }
                    return {exists: false, note: 'Shiny.shinyapp not found'};
                } catch(e) {
                    return {error: e.message};
                }
            })()""")
            for k, v in ws_info.items():
                print(f"  {k}: {v}")

            # 7. Try sending a manual deck_update to see what happens
            print(f"\n=== Manual Layer Push Test ===")
            manual_test = page.evaluate("""(() => {
                try {
                    const inst = window.__deckgl_instances;
                    if (!inst || !inst['demo_map']) return 'No instance';
                    const i = inst['demo_map'];
                    
                    // Check overlay internal state
                    const overlay = i.overlay;
                    const result = {
                        overlayType: overlay.constructor.name,
                    };
                    
                    // Try to get current layers from overlay
                    if (overlay._deck) {
                        result.hasDeck = true;
                        const deckProps = overlay._deck.props;
                        result.deckLayerCount = deckProps.layers ? deckProps.layers.length : 0;
                    } else {
                        result.hasDeck = false;
                    }
                    
                    // Check if the overlay has setProps
                    result.hasSetProps = typeof overlay.setProps === 'function';
                    
                    return result;
                } catch(e) {
                    return {error: e.message, stack: e.stack ? e.stack.substring(0, 300) : ''};
                }
            })()""")
            for k, v in manual_test.items():
                print(f"  {k}: {v}")

            # 8. Wait a bit more and check again
            print(f"\n=== Waiting 5 more seconds... ===")
            time.sleep(5)

            final_check = page.evaluate("""(() => {
                const inst = window.__deckgl_instances;
                if (!inst || !inst['demo_map']) return {error: 'no instance'};
                const i = inst['demo_map'];
                return {
                    lastLayersCount: i.lastLayers ? i.lastLayers.length : 0,
                    lastLayerIds: i.lastLayers ? i.lastLayers.map(l => l.id) : [],
                };
            })()""")
            print(f"  lastLayersCount: {final_check.get('lastLayersCount')}")
            print(f"  lastLayerIds: {final_check.get('lastLayerIds')}")

            # 9. Console messages
            print(f"\n=== Console ({len(console_msgs)} msgs) ===")
            for msg in console_msgs:
                print(f"  {msg}")

            print(f"\n=== JS Errors ({len(errors)}) ===")
            for err in errors:
                print(f"  {err}")

            # Screenshot
            page.screenshot(path="tests/demo_screenshot_deep.png", full_page=True)
            print(f"\nScreenshot: tests/demo_screenshot_deep.png")

            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
