"""sanitizeHtml() in a real browser (J9, docs/2026-09-26-codebase-review.md).

The sanitiser depends on DOMParser, which Node lacks, so these tests load the
real function from deckgl-init.js into headless Chromium, insert its output
with innerHTML the way the tooltip and popup code do, and check that nothing
scriptable survives.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _js_harness import extract_function, extract_var  # noqa: E402

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402


_SANITIZER = "\n".join([
    extract_var("SANITIZE_STRIP_TAGS"),
    extract_var("SANITIZE_STRIP_ATTRS"),
    extract_var("SANITIZE_URI_SCHEME"),
    extract_var("SANITIZE_DANGEROUS_SCHEMES"),
    extract_var("SANITIZE_DATA_URI_SAFE"),
    extract_function("isDangerousUri"),
    extract_var("SANITIZE_URI_ATTRS"),
    extract_function("sanitizeHtmlOnce"),
    extract_function("sanitizeHtml"),
])

# Inserts the sanitised markup, gives any handlers/animations a moment to
# fire, then reports what is left in the DOM that could run script.
_PROBE = r"""
async (html) => {
  window.__pwned = false;
  const host = document.createElement('div');
  document.body.appendChild(host);
  const out = sanitizeHtml(html);
  host.innerHTML = out;
  await new Promise(r => setTimeout(r, 300));
  const bad = [];
  for (const el of host.querySelectorAll('*')) {
    const tag = el.localName.toLowerCase();
    if (['script', 'animate', 'set', 'animatemotion', 'animatetransform', 'math'].includes(tag)) bad.push(tag);
    for (const a of el.attributes) {
      if (/^on/i.test(a.name)) bad.push(tag + '@' + a.name);
      if (/href$|^src$/i.test(a.name) && /^\s*(javascript|vbscript)\s*:/i.test(a.value.replace(/[\t\n\r]/g, ''))) bad.push(tag + '@' + a.name);
    }
  }
  // Clicking every link must not run script either.
  for (const a of host.querySelectorAll('a')) { try { a.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); } catch (e) {} }
  await new Promise(r => setTimeout(r, 100));
  host.remove();
  return { out, bad, pwned: window.__pwned === true };
}
"""


@pytest.fixture(scope="module")
def page():
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch()
    except Exception as exc:  # browser not installed
        pytest.skip(f"chromium unavailable: {exc}")
    pg = browser.new_page()
    pg.set_content("<!doctype html><html><body></body></html>")
    pg.add_script_tag(content=_SANITIZER + "\nwindow.sanitizeHtml = sanitizeHtml;")
    # Block real navigation so a javascript: href that slipped through is
    # observed as __pwned rather than tearing the page down.
    yield pg
    browser.close()
    pw.stop()


PAYLOAD = "window.__pwned=true"

MALICIOUS = [
    # SMIL animation rewriting href to javascript: after sanitising (J9).
    f'<svg><a><animate attributeName="href" values="javascript:{PAYLOAD}"/>'
    f'<text x="20" y="20">x</text></a></svg>',
    f'<svg><a><set attributeName="href" to="javascript:{PAYLOAD}"/><text>x</text></a></svg>',
    f'<svg><animate onbegin="{PAYLOAD}" attributeName="x" dur="1s"/></svg>',
    f'<svg><set onbegin="{PAYLOAD}" attributeName="x" to="1"/></svg>',
    f'<svg><animateTransform onbegin="{PAYLOAD}" attributeName="transform" type="scale" dur="1s"/></svg>',
    # Classic handlers and schemes (regression guard).
    f'<img src=x onerror="{PAYLOAD}">',
    f'<a href="javascript:{PAYLOAD}">x</a>',
    f'<svg><a xlink:href="javascript:{PAYLOAD}"><text>x</text></a></svg>',
    f'<iframe srcdoc="<script>parent.__pwned=true</script>"></iframe>',
    # Mutation-XSS shapes: markup that changes meaning when the sanitised
    # output is parsed a second time by innerHTML.
    f'<math><mtext><table><mglyph><style><!--</style>'
    f'<img title="--&gt;&lt;img src=1 onerror={PAYLOAD}&gt;"></mglyph></table></mtext></math>',
    f'<math><mi><table><mi><style><img src=x onerror={PAYLOAD}></style></mi></table></mi></math>',
    f'<svg></p><style><a id="</style><img src=1 onerror={PAYLOAD}>">',
    f'<form><math><mtext></form><form><mglyph><style></math><img src onerror={PAYLOAD}>',
    f'<noscript><p title="</noscript><img src=x onerror={PAYLOAD}>">',
]


@pytest.mark.parametrize("html", MALICIOUS)
def test_nothing_scriptable_survives(page, html):
    got = page.evaluate(_PROBE, html)
    assert got["bad"] == [], f"left in DOM: {got['bad']}\nout={got['out']!r}"
    assert got["pwned"] is False, f"payload ran; out={got['out']!r}"


@pytest.mark.parametrize("html,must_contain", [
    ("<b>Port</b>: Klaipėda<br><i>depth 14 m</i>", "<b>Port</b>"),
    ('<a href="https://example.com" target="_blank">link</a>', 'href="https://example.com"'),
    ('<img src="data:image/png;base64,AAAA" width="10">', "data:image/png"),
    ('<table><tr><td>a</td><td>1</td></tr></table>', "<td>a</td>"),
    ('<svg width="10" height="10"><circle cx="5" cy="5" r="4" fill="red"></circle></svg>', "<circle"),
    ('<span style="color:red">red</span>', 'style="color:red"'),
])
def test_benign_markup_is_kept(page, html, must_contain):
    got = page.evaluate(_PROBE, html)
    assert must_contain in got["out"]
    assert got["bad"] == []


def test_output_is_stable(page):
    """What is inserted must itself survive another pass unchanged."""
    for html in MALICIOUS:
        once = page.evaluate("h => sanitizeHtml(h)", html)
        twice = page.evaluate("h => sanitizeHtml(h)", once)
        assert once == twice, f"not stable for {html!r}"
