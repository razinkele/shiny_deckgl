"""Run individual helper functions from deckgl-init.js under Node.

The bundle is an IIFE with top-level `window`/`Shiny` side effects, so it cannot
be imported wholesale. This harness extracts named top-level declarations by
brace matching and evaluates just those in a bare Node context.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

JS_PATH = Path(__file__).resolve().parents[1] / "src" / "shiny_deckgl" / "resources" / "deckgl-init.js"

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


def js_source() -> str:
    return JS_PATH.read_text(encoding="utf-8")


def extract_function(name: str, src: str | None = None) -> str:
    """Return the source of top-level `function <name>(...) {...}`."""
    src = js_source() if src is None else src
    m = re.search(r"^[ \t]*function\s+" + re.escape(name) + r"\s*\(", src, re.M)
    if m is None:
        raise LookupError(f"function {name}() not found in deckgl-init.js")
    start = m.start()
    brace = src.index("{", m.end() - 1)
    depth, i = 0, brace
    while i < len(src):
        c = src[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    raise ValueError(f"unbalanced braces in {name}()")


def extract_var(name: str, src: str | None = None) -> str:
    """Return the source of a top-level `var <name> = ...;` declaration.

    Handles multi-line object and array literals by bracket matching; falls
    back to a single-line match for simple values.
    """
    src = js_source() if src is None else src
    m = re.search(r"^[ \t]*(?:var|const|let)\s+" + re.escape(name) + r"\s*=", src, re.M)
    if m is None:
        raise LookupError(f"declaration {name} not found in deckgl-init.js")

    rest = src[m.end():]
    stripped = rest.lstrip()
    opener = stripped[:1]
    if opener in "{[":
        closer = "}" if opener == "{" else "]"
        start = m.end() + (len(rest) - len(stripped))
        depth = 0
        for i in range(start, len(src)):
            if src[i] == opener:
                depth += 1
            elif src[i] == closer:
                depth -= 1
                if depth == 0:
                    end = src.find(";", i)
                    return src[m.start():(end + 1 if end != -1 else i + 1)]
        raise ValueError(f"unbalanced literal in declaration {name}")

    line = re.search(r"^[ \t]*(?:var|const|let)\s+" + re.escape(name) + r"\s*=.*?;[ \t]*$",
                     src, re.M)
    if line is None:
        raise LookupError(f"declaration {name} is not a single-line value")
    return line.group(0)


def run_js(prelude: str, expression: str) -> object:
    """Eval `expression` after `prelude`; return the JSON-decoded result."""
    script = prelude + "\n;process.stdout.write(JSON.stringify(" + expression + "));"
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise AssertionError(f"node failed:\n{proc.stderr}")
    return json.loads(proc.stdout)
