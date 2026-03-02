"""Individual-Based Model (IBM) movement-visualisation assets.

This module provides **species-agnostic** visual assets for rendering
animal movement tracks on a deck.gl map: colour look-ups and an SVG
sprite sheet for ``IconLayer``.  The assets ship with seal sprites but
the naming is generic so the module can be extended to other taxa.

Actual coordinate / trajectory generation is the responsibility of the
user's own simulation code (the built-in demo app ships with a
correlated random-walk example in ``_demo_data``).

Public API
----------
* ``SPECIES_COLORS``  – RGBA look-up per species
* ``ICON_ATLAS``      – base64 data-URI of a 192×64 SVG sprite sheet
* ``ICON_MAPPING``    – deck.gl icon-mapping dict keyed by species
"""

from __future__ import annotations

__all__ = [
    "SPECIES_COLORS",
    "ICON_ATLAS",
    "ICON_MAPPING",
]

# ---------------------------------------------------------------------------
# Species colour palette
# ---------------------------------------------------------------------------

#: RGBA colours per species for consistent rendering across layers.
SPECIES_COLORS: dict[str, list[int]] = {
    "Grey seal":    [100, 100, 100, 220],   # slate grey
    "Ringed seal":  [70, 140, 220, 220],    # icy blue
    "Harbour seal": [180, 140, 80, 220],    # sandy brown
}

# ---------------------------------------------------------------------------
# SVG icon atlas (base64-encoded sprite sheet for deck.gl IconLayer)
# ---------------------------------------------------------------------------
# Three 64×64 species-coloured seal silhouettes in a 192×64 strip.
# Each species has its own fill colour, a darker accent stroke for
# definition, a lighter belly patch, and a tiny eye dot.
# Base64 encoding is used for reliable loading across browsers.
# viewBox is 0 0 192 64, aligned with the on-screen sprite dimensions.
# Each species is drawn with SVG <path> elements for a realistic
# swimming-seal silhouette (torpedo body, rounded head, hind flippers).
#
# Grey seal    (x=0):   #7a8a8a slate-grey, bulky body, broad snout
# Ringed seal  (x=64):  #4a8cdc icy blue, slender body, small head
# Harbour seal (x=128): #c8a050 sandy gold, medium build, rounded head

#: Base64-encoded data-URI of the 192×64 SVG sprite-sheet.  Pass this as
#: ``iconAtlas`` to ``icon_layer()`` or the ``_tripsHeadIcons`` dict.
ICON_ATLAS: str = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIx"
    "OTIiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCAxOTIgNjQiPjxnIHRyYW5zZm9y"
    "bT0idHJhbnNsYXRlKDAsMCkiPjxwYXRoIGQ9Ik0gNiwzNCBDIDQsMzAgMywyOCA2"
    "LDI2IEwgOCwyNCBDIDEwLDIyIDEwLDI2IDEyLDI4IEMgMTYsMjIgMjQsMTggMzQs"
    "MTggQyA0MiwxOCA0OCwyMCA1MiwyNCBDIDU2LDI2IDU4LDI4IDU4LDMwIEMgNjAs"
    "MzEgNjAsMzMgNTgsMzQgQyA1NiwzNiA1NCwzOCA1MCwzOCBDIDQ2LDQwIDQwLDQy"
    "IDM0LDQyIEMgMjQsNDIgMTYsNDAgMTIsMzYgQyAxMCwzOCAxMCwzNiA4LDM4IEwg"
    "Niw0MCBDIDMsMzggNCwzNiA2LDM0IFoiIGZpbGw9IiM3YThhOGEiIHN0cm9rZT0i"
    "IzVhNmE2YSIgc3Ryb2tlLXdpZHRoPSIwLjgiLz48cGF0aCBkPSJNIDIwLDMwIEMg"
    "MjYsMjggNDAsMjggNDgsMzAgQyA0OCwzNCA0MCwzOCAzNCwzOCBDIDI2LDM4IDIw"
    "LDM0IDIwLDMwIFoiIGZpbGw9IiM5NWE1YTAiIG9wYWNpdHk9IjAuNCIvPjxlbGxp"
    "cHNlIGN4PSI0MCIgY3k9IjQwIiByeD0iNSIgcnk9IjIiIGZpbGw9IiM1YTZhNmEi"
    "IHRyYW5zZm9ybT0icm90YXRlKC0xNSw0MCw0MCkiLz48Y2lyY2xlIGN4PSIxMCIg"
    "Y3k9IjI2IiByPSIxLjIiIGZpbGw9IiMyMjIiIG9wYWNpdHk9IjAuNyIvPjwvZz48"
    "ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSg2NCwwKSI+PHBhdGggZD0iTSA4LDM0IEMg"
    "NiwzMSA1LDI5IDgsMjcgTCAxMCwyNSBDIDExLDIzIDExLDI3IDE0LDI5IEMgMTgs"
    "MjMgMjYsMjAgMzUsMjAgQyA0MiwyMCA0NywyMiA1MCwyNSBDIDUzLDI3IDU1LDI5"
    "IDU1LDMxIEMgNTcsMzIgNTcsMzQgNTUsMzUgQyA1MywzNyA1MSwzOCA0OCwzOCBD"
    "IDQ0LDQwIDM4LDQxIDM1LDQxIEMgMjYsNDEgMTgsMzkgMTQsMzYgQyAxMSwzNyAx"
    "MSwzNiAxMCwzOCBMIDgsMzkgQyA1LDM4IDYsMzYgOCwzNCBaIiBmaWxsPSIjNGE4"
    "Y2RjIiBzdHJva2U9IiMzNDZhYjAiIHN0cm9rZS13aWR0aD0iMC44Ii8+PHBhdGgg"
    "ZD0iTSAyMiwzMCBDIDI4LDI4IDQwLDI5IDQ3LDMxIEMgNDcsMzQgMzksMzcgMzUs"
    "MzcgQyAyNywzNyAyMiwzNCAyMiwzMCBaIiBmaWxsPSIjNmVhYWYwIiBvcGFjaXR5"
    "PSIwLjQiLz48ZWxsaXBzZSBjeD0iMzgiIGN5PSIzOS41IiByeD0iNCIgcnk9IjEu"
    "NSIgZmlsbD0iIzM0NmFiMCIgdHJhbnNmb3JtPSJyb3RhdGUoLTEyLDM4LDM5LjUp"
    "Ii8+PGNpcmNsZSBjeD0iMTIiIGN5PSIyNyIgcj0iMSIgZmlsbD0iIzIyMiIgb3Bh"
    "Y2l0eT0iMC43Ii8+PC9nPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEyOCwwKSI+"
    "PHBhdGggZD0iTSA3LDM0IEMgNSwzMSA0LDI5IDcsMjcgTCA5LDI1IEMgMTAsMjMg"
    "MTAsMjcgMTMsMjkgQyAxNywyMiAyNSwxOSAzNCwxOSBDIDQyLDE5IDQ3LDIxIDUx"
    "LDI0IEMgNTQsMjYgNTYsMjggNTYsMzEgQyA1OCwzMiA1OCwzNCA1NiwzNSBDIDU0"
    "LDM3IDUyLDM4IDQ5LDM4IEMgNDUsNDAgMzksNDIgMzQsNDIgQyAyNSw0MiAxNyw0"
    "MCAxMywzNiBDIDEwLDM3IDEwLDM2IDksMzggTCA3LDQwIEMgNCwzOCA1LDM2IDcs"
    "MzQgWiIgZmlsbD0iI2M4YTA1MCIgc3Ryb2tlPSIjOWE3YTMwIiBzdHJva2Utd2lk"
    "dGg9IjAuOCIvPjxwYXRoIGQ9Ik0gMjEsMzAgQyAyNywyOCA0MCwyOCA0OCwzMSBD"
    "IDQ4LDM0IDQwLDM4IDM0LDM4IEMgMjYsMzggMjEsMzQgMjEsMzAgWiIgZmlsbD0i"
    "I2UwYzg3OCIgb3BhY2l0eT0iMC40Ii8+PGVsbGlwc2UgY3g9IjM5IiBjeT0iNDAi"
    "IHJ4PSI0LjUiIHJ5PSIxLjgiIGZpbGw9IiM5YTdhMzAiIHRyYW5zZm9ybT0icm90"
    "YXRlKC0xNCwzOSw0MCkiLz48Y2lyY2xlIGN4PSIxMSIgY3k9IjI3IiByPSIxLjEi"
    "IGZpbGw9IiMyMjIiIG9wYWNpdHk9IjAuNyIvPjwvZz48L3N2Zz4="
)

#: deck.gl icon-mapping dict keyed by species name.
#: ``anchorY=32`` centres the icon vertically on the point.
ICON_MAPPING: dict[str, dict] = {
    "Grey seal":    {"x": 0,   "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Ringed seal":  {"x": 64,  "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Harbour seal": {"x": 128, "y": 0, "width": 64, "height": 64, "anchorY": 32},
}
