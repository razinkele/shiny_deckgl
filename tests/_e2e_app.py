"""Start a small Shiny app from tests/_apps for a browser test."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def running_app(module: str, port: int):
    """Serve ``tests/_apps/<module>.py`` on *port* against the working tree."""
    with socket.socket() as s:
        s.settimeout(1.0)
        if s.connect_ex(("127.0.0.1", port)) == 0:
            pytest.fail(f"port {port} already in use (stale server?)")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT / "tests" / "_apps"), env.get("PYTHONPATH", "")])
    proc = subprocess.Popen(
        [sys.executable, "-m", "shiny", "run", f"{module}:app", "--port", str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=str(ROOT),
    )
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if proc.poll() is not None:
                pytest.fail(f"{module} exited early:\n" + (proc.stdout.read() if proc.stdout else ""))
            with socket.socket() as s:
                s.settimeout(1.0)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.5)
        else:
            pytest.fail(f"{module} did not start on port {port}")
        yield proc
    finally:
        # `shiny run` spawns uvicorn as a child; on Windows kill the tree.
        if proc.poll() is None:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, check=False)
            else:
                proc.terminate()
            proc.wait(timeout=15)


@contextmanager
def browser_page(url: str, ready_selector: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"chromium unavailable: {exc}")
        pg = browser.new_page()
        pg.console_log = []
        pg.on("console", lambda msg: pg.console_log.append(msg.text))
        pg.goto(url)
        pg.wait_for_selector(ready_selector, timeout=30000)
        try:
            yield pg
        finally:
            browser.close()
