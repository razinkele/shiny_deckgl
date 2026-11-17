"""Exploratory deep sweep of the shiny_deckgl demo.

Usage: python tools/demo_sweep.py <repo_root> <out_dir> [port]

Starts the demo (working tree, via demo_serve.py, which also logs websocket send
failures Shiny normally swallows), then in Chromium visits every tab and
exercises every input: switches/checkboxes/radios clicked, buttons clicked,
sliders moved to max/min and back, every select option chosen, text inputs
filled. After each action it records new console errors, page errors, failed
requests, server tracebacks, Shiny disconnects, visible output errors and
blank maps. Writes report.json + shots/.
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve()
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 8790
SHOTS = OUT / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
LOG = OUT / "server.log"
SETTLE = 1.2

IGNORE_CONSOLE = (
    "GPU stall", "DEPRECATED: This", "language code", "GL Driver Message",
    "[.WebGL", "favicon",
)


def start_server():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    logf = open(LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(pathlib.Path(__file__).with_name("demo_serve.py")), str(PORT)],
        stdout=logf, stderr=subprocess.STDOUT, env=env, cwd=str(ROOT),
    )
    for _ in range(180):
        if proc.poll() is not None:
            raise SystemExit("server exited early:\n" + LOG.read_text(encoding="utf-8")[-3000:])
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", PORT)) == 0:
                return proc
        time.sleep(0.5)
    stop_server(proc)
    raise SystemExit("server did not start")


def stop_server(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


class Log:
    def __init__(self):
        self.pos = 0

    def new(self) -> str:
        txt = LOG.read_text(encoding="utf-8", errors="replace")
        chunk, self.pos = txt[self.pos:], len(txt)
        return chunk


def server_problems(chunk: str) -> list[str]:
    out, lines = [], chunk.splitlines()
    for i, ln in enumerate(lines):
        if ("Traceback" in ln or "SEND FAILED" in ln or "ERROR" in ln
                or "Error:" in ln or "Exception" in ln or "Warning:" in ln):
            out.append("\n".join(lines[i:i + 25]))
    return out


REVEAL_JS = """el => {
  const panes = [];
  for (let n = el; n; n = n.parentElement) {
    if (n.classList && n.classList.contains('accordion-collapse') && !n.classList.contains('show')) panes.push(n);
  }
  panes.reverse().forEach(c => {
    const item = c.closest('.accordion-item');
    const btn = item && item.querySelector('.accordion-button');
    if (btn) btn.click();
  });
  return panes.length;
}"""


def reveal(page, loc) -> bool:
    """Open any collapsed accordion panels around loc; True if it is then visible."""
    try:
        if loc.is_visible():
            return True
        if loc.evaluate(REVEAL_JS):
            page.wait_for_timeout(700)
        loc.scroll_into_view_if_needed(timeout=3000)
        return loc.is_visible()
    except Exception:  # noqa: BLE001
        return False


def blank_score(png: bytes) -> dict:
    from PIL import Image, ImageStat
    img = Image.open(io.BytesIO(png)).convert("L")
    st = ImageStat.Stat(img)
    hist = img.histogram()
    top = max(hist) / max(1, sum(hist))
    return {"std": round(st.stddev[0], 2), "dominant": round(top, 3)}


def main():
    proc = start_server()
    slog = Log()
    report = {"tabs": [], "events": [], "global": {}, "hidden": []}
    pending = {"console": [], "pageerror": [], "requests": []}

    def ev(tab, target, action, extra=None):
        chunk = slog.new()
        probs = server_problems(chunk)
        state = page.evaluate(
            "() => ({connected: !!(window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()),"
            " outErr: [...document.querySelectorAll('.tab-pane.active .shiny-output-error')]"
            "   .filter(e => e.offsetParent && !e.classList.contains('shiny-output-error-silent'))"
            "   .map(e => (e.id || '') + ': ' + e.textContent.trim().slice(0, 200)),"
            " notif: [...document.querySelectorAll('.shiny-notification-error, #shiny-disconnected-overlay')]"
            "   .map(e => e.textContent.trim().slice(0, 200))})")
        rec = {
            "tab": tab, "target": target, "action": action,
            "console": pending["console"][:], "pageerror": pending["pageerror"][:],
            "requests": pending["requests"][:], "server": probs,
            "connected": state["connected"], "output_errors": state["outErr"],
            "notifications": state["notif"],
        }
        if extra:
            rec.update(extra)
        for k in pending:
            pending[k].clear()
        bad = (rec["console"] or rec["pageerror"] or rec["requests"] or rec["server"]
               or not rec["connected"] or rec["output_errors"] or rec["notifications"]
               or rec.get("error") or rec.get("xss_fired"))
        rec["bad"] = bool(bad)
        report["events"].append(rec)
        flag = "!!" if bad else "ok"
        print(f"[{flag}] {tab[:22]:22} {target[:40]:40} {action}", flush=True)
        return rec

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1600, "height": 1000}, accept_downloads=True)
            page = ctx.new_page()
            page.on("console", lambda m: m.type in ("error", "warning") and not any(
                s in m.text for s in IGNORE_CONSOLE) and pending["console"].append(
                f"{m.type}: {m.text[:400]}"))
            page.on("pageerror", lambda e: pending["pageerror"].append(str(e)[:400]))
            page.on("requestfailed", lambda r: pending["requests"].append(
                f"FAILED {r.url[:200]} {r.failure}"))
            page.on("response", lambda r: r.status >= 400 and pending["requests"].append(
                f"HTTP {r.status} {r.url[:200]}"))

            t0 = time.time()
            page.goto(f"http://127.0.0.1:{PORT}/", wait_until="domcontentloaded")
            page.wait_for_function(
                "() => window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()", timeout=60000)
            page.wait_for_timeout(6000)
            report["global"]["load_seconds"] = round(time.time() - t0, 1)
            ev("(startup)", "page", "load")

            tabs = page.locator(".navbar .nav-link[data-bs-toggle='tab'], .navbar a.nav-link[role='tab']")
            n = tabs.count()
            titles = [tabs.nth(i).inner_text().strip() for i in range(n)]
            print("tabs:", titles, flush=True)

            for ti, title in enumerate(titles):
                tabs.nth(ti).click()
                page.wait_for_timeout(3500)
                tinfo = {"title": title, "maps": [], "inputs": 0}
                maps = page.locator(".tab-pane.active .deckgl-map")
                for mi in range(maps.count()):
                    m = maps.nth(mi)
                    try:
                        m.scroll_into_view_if_needed(timeout=3000)
                        box = m.bounding_box()
                        sc = blank_score(m.screenshot(timeout=10000))
                        canv = m.evaluate("e => [...e.querySelectorAll('canvas')].map(c => [c.width, c.height])")
                        tinfo["maps"].append({"id": m.get_attribute("id"), "box": box, "canvases": canv, **sc})
                    except Exception as e:  # noqa: BLE001
                        tinfo["maps"].append({"id": m.get_attribute("id"), "error": str(e)[:300]})
                page.screenshot(path=str(SHOTS / f"tab{ti:02d}.png"))
                ev(title, "(tab)", "activate", {"maps": tinfo["maps"]})

                pane = page.locator(".tab-pane.active").first
                # --- checkbox-like inputs (switches, checkbox groups, radios) ---
                boxes = pane.locator("input[type=checkbox], input[type=radio]")
                ids = []
                for i in range(boxes.count()):
                    b = boxes.nth(i)
                    ids.append((b.get_attribute("id") or b.get_attribute("name") or f"box{i}",
                                b.get_attribute("type"), b.get_attribute("value")))
                for i, (bid, typ, val) in enumerate(ids):
                    b = boxes.nth(i)
                    try:
                        target = f"{bid}={val}" if typ == "radio" else bid
                        if not reveal(page, b):
                            report["hidden"].append(f"{title} | {target}")
                            continue
                        b.click(timeout=3000, force=True)
                        page.wait_for_timeout(int(SETTLE * 1000))
                        ev(title, target, "click#1")
                        if typ == "checkbox":
                            b.click(timeout=3000, force=True)
                            page.wait_for_timeout(int(SETTLE * 1000))
                            ev(title, target, "click#2 (restore)")
                        tinfo["inputs"] += 1
                    except Exception as e:  # noqa: BLE001
                        ev(title, bid, "click FAILED", {"error": str(e)[:300]})

                # --- sliders ---
                sliders = pane.locator("input.js-range-slider")
                for i in range(sliders.count()):
                    sid = sliders.nth(i).get_attribute("id")
                    try:
                        info = page.evaluate(
                            "id => { const d = $('#' + CSS.escape(id)).data('ionRangeSlider');"
                            " return {min: d.options.min, max: d.options.max, from: d.result.from,"
                            " to: d.result.to, type: d.options.type}; }", sid)
                        for label, val in (("max", info["max"]), ("min", info["min"]),
                                           ("restore", info["from"])):
                            page.evaluate(
                                "([id, v, t]) => { const d = $('#' + CSS.escape(id)).data('ionRangeSlider');"
                                " d.update(t === 'double' ? {from: v} : {from: v}); }",
                                [sid, val, info["type"]])
                            page.wait_for_timeout(int(SETTLE * 1000))
                            ev(title, sid, f"slider {label}={val}")
                        tinfo["inputs"] += 1
                    except Exception as e:  # noqa: BLE001
                        ev(title, sid, "slider FAILED", {"error": str(e)[:300]})

                # --- selects (native or selectize) ---
                selects = pane.locator("select")
                for i in range(selects.count()):
                    s = selects.nth(i)
                    sid = s.get_attribute("id")
                    try:
                        opts = s.evaluate("e => [...e.options].map(o => o.value)")
                        orig = s.evaluate("e => e.value")
                        for v in opts + [orig]:
                            s.evaluate(
                                "(e, v) => { if (e.selectize) e.selectize.setValue(v);"
                                " else { e.value = v; $(e).trigger('change'); } }", v)
                            page.wait_for_timeout(int(SETTLE * 1000))
                            ev(title, sid, f"select {v}")
                        tinfo["inputs"] += 1
                    except Exception as e:  # noqa: BLE001
                        ev(title, sid, "select FAILED", {"error": str(e)[:300]})

                # --- text inputs ---
                texts = pane.locator("input[type=text]:not(.js-range-slider):not(.selectize-input input), textarea")
                for i in range(texts.count()):
                    t = texts.nth(i)
                    tid = t.get_attribute("id") or f"text{i}"
                    if not tid or tid.endswith("-selectized"):
                        continue
                    try:
                        orig = t.input_value()
                        for v in ("test value", '<img src=x onerror="window.__xss=1">', orig):
                            t.fill(v, timeout=3000)
                            t.press("Tab")
                            page.wait_for_timeout(int(SETTLE * 1000))
                            xss = page.evaluate("() => !!window.__xss")
                            ev(title, tid, f"text {v[:30]!r}", {"xss_fired": xss})
                        tinfo["inputs"] += 1
                    except Exception as e:  # noqa: BLE001
                        ev(title, tid, "text FAILED", {"error": str(e)[:300]})

                # --- buttons last (they may start long-running things) ---
                btns = pane.locator("button.action-button, a.action-button, a.shiny-download-link, button.shiny-download-link")
                bids = [btns.nth(i).get_attribute("id") or f"btn{i}" for i in range(btns.count())]
                for i, bid in enumerate(bids):
                    b = btns.nth(i)
                    try:
                        if not reveal(page, b):
                            report["hidden"].append(f"{title} | {bid}")
                            continue
                        cls = b.get_attribute("class") or ""
                        if "shiny-download-link" in cls:
                            with page.expect_download(timeout=30000) as dl:
                                b.click(timeout=3000)
                            d = dl.value
                            path = OUT / "downloads" / d.suggested_filename
                            path.parent.mkdir(exist_ok=True)
                            d.save_as(path)
                            page.wait_for_timeout(500)
                            ev(title, bid, "download", {"file": str(path), "size": path.stat().st_size})
                        else:
                            b.click(timeout=3000)
                            page.wait_for_timeout(int(SETTLE * 1500))
                            ev(title, bid, "click")
                        tinfo["inputs"] += 1
                    except Exception as e:  # noqa: BLE001
                        ev(title, bid, "button FAILED", {"error": str(e)[:300]})

                page.screenshot(path=str(SHOTS / f"tab{ti:02d}_after.png"))
                report["tabs"].append(tinfo)

            # --- dark mode, resize, reload ---
            dm = page.locator("bslib-input-dark-mode")
            if dm.count():
                dm.first.click()
                page.wait_for_timeout(2500)
                ev("(global)", "dark_mode", "toggle on")
                page.screenshot(path=str(SHOTS / "dark.png"))
                dm.first.click()
                page.wait_for_timeout(1500)
                ev("(global)", "dark_mode", "toggle off")

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(2500)
            sizes = page.evaluate(
                "() => [...document.querySelectorAll('.tab-pane.active .deckgl-map')].map(e => {"
                " const c = e.querySelector('canvas'); const r = e.getBoundingClientRect();"
                " return {id: e.id, w: Math.round(r.width), cw: c ? Math.round(c.getBoundingClientRect().width) : null}; })")
            page.screenshot(path=str(SHOTS / "mobile.png"))
            ev("(global)", "viewport 390x844", "resize", {"sizes": sizes})
            page.set_viewport_size({"width": 1600, "height": 1000})

            page.reload(wait_until="domcontentloaded")
            page.wait_for_function(
                "() => window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()", timeout=60000)
            page.wait_for_timeout(5000)
            ev("(global)", "page", "reload")
            browser.close()
    except BaseException as exc:
        report["global"]["aborted"] = repr(exc)
        raise
    finally:
        # Keep what was collected and never leave the server running.
        stop_server(proc)
        report["global"]["server_tail"] = LOG.read_text(encoding="utf-8", errors="replace")[-4000:]
        (OUT / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        bad = [e for e in report["events"] if e["bad"]]
        print(f"\nDONE: {len(report['events'])} actions, {len(bad)} with problems")


if __name__ == "__main__":
    main()
