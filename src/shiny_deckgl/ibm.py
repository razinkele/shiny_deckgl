"""Individual-Based Model (IBM) movement-visualisation assets.

This module provides visual assets and helpers for rendering animal
movement tracks on a deck.gl map.  Nine Baltic Sea species are included:
seals (3), dolphins (3), and fish (3).

Visual Assets
-------------
* ``SPECIES_COLORS``  – RGBA look-up per species
* ``ICON_ATLAS``      – base64 data-URI of a 192×64 SVG sprite sheet
* ``ICON_MAPPING``    – deck.gl icon-mapping dict keyed by species

Data Helpers
------------
* ``format_trips()``  – convert raw coordinate lists into the dict
  format that ``trips_layer()`` expects

Shiny Modules
-------------
* ``trips_animation_ui()``     – Play/Pause/Reset buttons + speed &
  trail sliders (drop into any Shiny sidebar)
* ``trips_animation_server()`` – wires the buttons to
  ``MapWidget.trips_control()`` and exposes ``speed`` / ``trail``
  reactive inputs back to the caller
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shiny import Session
    from .map_widget import MapWidget

__all__ = [
    "SPECIES_COLORS",
    "ICON_ATLAS",
    "ICON_MAPPING",
    "format_trips",
    "trips_animation_ui",
    "trips_animation_server",
]

# ---------------------------------------------------------------------------
# Species colour palette
# ---------------------------------------------------------------------------

#: RGBA colours per species for consistent rendering across layers.
SPECIES_COLORS: dict[str, list[int]] = {
    # Seals
    "Grey seal":            [100, 100, 100, 220],  # slate grey
    "Ringed seal":          [70, 140, 220, 220],   # icy blue
    "Harbour seal":         [180, 140, 80, 220],   # sandy brown
    # Dolphins
    "Harbour porpoise":     [90, 122, 138, 220],   # steel blue-grey
    "Bottlenose dolphin":   [106, 154, 176, 220],  # ocean blue
    "White-beaked dolphin": [138, 176, 192, 220],  # pale blue
    # Fish
    "Atlantic cod":         [138, 122, 90, 220],   # olive brown
    "Baltic herring":       [122, 138, 170, 220],  # steel blue
    "Atlantic salmon":      [192, 128, 96, 220],   # copper
}

# ---------------------------------------------------------------------------
# SVG icon atlas (base64-encoded sprite sheet for deck.gl IconLayer)
# ---------------------------------------------------------------------------
# Nine 64×64 species-coloured dorsal (top-down) silhouettes in a 576×64 strip.
# Each species has its own fill colour, a darker stroke for definition, and a
# midline spine accent.  All face RIGHT so the JS rotation logic (atan2) works.
# Base64 encoding is used for reliable loading across browsers.
#
# Seals (teardrop body, 4 splayed flippers, V-tail):
#   Grey seal         (x=0):   #7a8a8a — widest, bulky oval
#   Ringed seal       (x=64):  #4a8cdc — slender, elongated
#   Harbour seal      (x=128): #c8a050 — medium build
#
# Dolphins (streamlined torpedo, pectoral fin wings, horizontal tail flukes):
#   Harbour porpoise  (x=192): #5a7a8a — smallest, rounded snout
#   Bottlenose dolphin(x=256): #6a9ab0 — larger, pronounced beak
#   White-beaked dolphin(x=320):#8ab0c0 — short beak, wider body
#
# Fish (fusiform body, pectoral fin wings, forked tail):
#   Atlantic cod      (x=384): #8a7a5a — broad head, tapering
#   Baltic herring    (x=448): #7a8aaa — slender, deeply forked
#   Atlantic salmon   (x=512): #c08060 — robust, slightly forked

#: Base64-encoded data-URI of the 576×64 SVG sprite-sheet.  Pass this as
#: ``iconAtlas`` to ``icon_layer()`` or the ``_tripsHeadIcons`` dict.
ICON_ATLAS: str = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI1"
    "NzYiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA1NzYgNjQiPgo8IS0tIEdyZXkg"
    "c2VhbDogYnVsa3kgb3ZhbCwgYnJvYWQgaGVhZCwgNCBmbGlwcGVycywgVi10YWls"
    "IC0tPgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgwLDApIj4KPHBhdGggZD0iTSAx"
    "MCwzMiBDIDEwLDI2IDE0LDIwIDIwLDE4IEMgMjYsMTYgMzQsMTYgNDAsMTcgQyA0"
    "NiwxOCA1MiwyMSA1NiwyNiBDIDU4LDI4IDU4LDM2IDU2LDM4IEMgNTIsNDMgNDYs"
    "NDYgNDAsNDcgQyAzNCw0OCAyNiw0OCAyMCw0NiBDIDE0LDQ0IDEwLDM4IDEwLDMy"
    "IFogTSA4LDI0IEwgNCwxOCBNIDgsNDAgTCA0LDQ2IE0gNTIsMjQgTCA1NiwyMCBN"
    "IDUyLDQwIEwgNTYsNDQgTSA1NiwzMCBMIDYyLDI4IEMgNjIsMzIgNjIsMzIgNjIs"
    "MzYgTCA1NiwzNCIgZmlsbD0iIzdhOGE4YSIgc3Ryb2tlPSIjNWE2YTZhIiBzdHJv"
    "a2Utd2lkdGg9IjAuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CjxsaW5lIHgx"
    "PSIxMiIgeTE9IjMyIiB4Mj0iNTYiIHkyPSIzMiIgc3Ryb2tlPSIjNWE2YTZhIiBz"
    "dHJva2Utd2lkdGg9IjEiIG9wYWNpdHk9IjAuNSIgc3Ryb2tlLWxpbmVjYXA9InJv"
    "dW5kIi8+CjwvZz4KPCEtLSBSaW5nZWQgc2VhbDogc2xlbmRlciwgZWxvbmdhdGVk"
    "LCBuYXJyb3cgaGVhZCAtLT4KPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoNjQsMCki"
    "Pgo8cGF0aCBkPSJNIDgsMzIgQyA4LDI3IDEyLDIyIDE4LDIwIEMgMjQsMTggMzIs"
    "MTcgMzgsMTggQyA0NCwxOSA1MCwyMiA1NCwyNyBDIDU2LDI5IDU2LDM1IDU0LDM3"
    "IEMgNTAsNDIgNDQsNDUgMzgsNDYgQyAzMiw0NyAyNCw0NiAxOCw0NCBDIDEyLDQy"
    "IDgsMzcgOCwzMiBaIE0gNywyNSBMIDMsMjAgTSA3LDM5IEwgMyw0NCBNIDUwLDI1"
    "IEwgNTQsMjEgTSA1MCwzOSBMIDU0LDQzIE0gNTQsMzAgTCA2MCwyOCBDIDYxLDMy"
    "IDYxLDMyIDYwLDM2IEwgNTQsMzQiIGZpbGw9IiM0YThjZGMiIHN0cm9rZT0iIzM0"
    "NmFiMCIgc3Ryb2tlLXdpZHRoPSIwLjgiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIv"
    "Pgo8bGluZSB4MT0iMTAiIHkxPSIzMiIgeDI9IjU0IiB5Mj0iMzIiIHN0cm9rZT0i"
    "IzM0NmFiMCIgc3Ryb2tlLXdpZHRoPSIwLjgiIG9wYWNpdHk9IjAuNSIgc3Ryb2tl"
    "LWxpbmVjYXA9InJvdW5kIi8+CjwvZz4KPCEtLSBIYXJib3VyIHNlYWw6IG1lZGl1"
    "bSBidWlsZCwgcm91bmRlZCBoZWFkIC0tPgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0"
    "ZSgxMjgsMCkiPgo8cGF0aCBkPSJNIDksMzIgQyA5LDI2IDEzLDIxIDE5LDE5IEMg"
    "MjUsMTcgMzMsMTYgMzksMTcgQyA0NSwxOCA1MSwyMiA1NSwyNyBDIDU3LDI5IDU3"
    "LDM1IDU1LDM3IEMgNTEsNDIgNDUsNDYgMzksNDcgQyAzMyw0OCAyNSw0NyAxOSw0"
    "NSBDIDEzLDQzIDksMzggOSwzMiBaIE0gNywyNCBMIDMsMTkgTSA3LDQwIEwgMyw0"
    "NSBNIDUxLDI0IEwgNTUsMjAgTSA1MSw0MCBMIDU1LDQ0IE0gNTUsMzAgTCA2MSwy"
    "OCBDIDYyLDMyIDYyLDMyIDYxLDM2IEwgNTUsMzQiIGZpbGw9IiNjOGEwNTAiIHN0"
    "cm9rZT0iIzlhN2EzMCIgc3Ryb2tlLXdpZHRoPSIwLjgiIHN0cm9rZS1saW5lY2Fw"
    "PSJyb3VuZCIvPgo8bGluZSB4MT0iMTEiIHkxPSIzMiIgeDI9IjU1IiB5Mj0iMzIi"
    "IHN0cm9rZT0iIzlhN2EzMCIgc3Ryb2tlLXdpZHRoPSIwLjgiIG9wYWNpdHk9IjAu"
    "NSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CjwvZz4KPCEtLSBIYXJib3VyIHBv"
    "cnBvaXNlOiBzbWFsbCB0b3JwZWRvLCByb3VuZGVkIHNub3V0LCBzbWFsbCBwZWN0"
    "b3JhbCBmaW5zLCBob3Jpem9udGFsIGZsdWtlcyAtLT4KPGcgdHJhbnNmb3JtPSJ0"
    "cmFuc2xhdGUoMTkyLDApIj4KPHBhdGggZD0iTSA2LDMyIEMgNiwyOCAxMCwyNCAx"
    "NiwyMiBDIDIyLDIwIDMwLDIwIDM4LDIyIEMgNDQsMjQgNTAsMjggNTQsMzIgQyA1"
    "MCwzNiA0NCw0MCAzOCw0MiBDIDMwLDQ0IDIyLDQ0IDE2LDQyIEMgMTAsNDAgNiwz"
    "NiA2LDMyIFoiIGZpbGw9IiM1YTdhOGEiIHN0cm9rZT0iIzNhNWE2YSIgc3Ryb2tl"
    "LXdpZHRoPSIwLjgiLz4KPHBhdGggZD0iTSAyMCwyMiBMIDE2LDE2IE0gMjAsNDIg"
    "TCAxNiw0OCIgc3Ryb2tlPSIjM2E1YTZhIiBzdHJva2Utd2lkdGg9IjEuMiIgc3Ry"
    "b2tlLWxpbmVjYXA9InJvdW5kIi8+CjxwYXRoIGQ9Ik0gNTQsMzIgTCA2MiwyNiBN"
    "IDU0LDMyIEwgNjIsMzgiIHN0cm9rZT0iIzNhNWE2YSIgc3Ryb2tlLXdpZHRoPSIx"
    "LjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8bGluZSB4MT0iOCIgeTE9IjMy"
    "IiB4Mj0iNTQiIHkyPSIzMiIgc3Ryb2tlPSIjM2E1YTZhIiBzdHJva2Utd2lkdGg9"
    "IjAuOCIgb3BhY2l0eT0iMC41IiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9n"
    "Pgo8IS0tIEJvdHRsZW5vc2UgZG9scGhpbjogbGFyZ2VyLCBwcm9ub3VuY2VkIGJl"
    "YWssIGxvbmdlciBwZWN0b3JhbCBmaW5zIC0tPgo8ZyB0cmFuc2Zvcm09InRyYW5z"
    "bGF0ZSgyNTYsMCkiPgo8cGF0aCBkPSJNIDQsMzIgQyA0LDI3IDgsMjIgMTQsMjAg"
    "QyAyMCwxOCAyOCwxOCAzNiwyMCBDIDQyLDIyIDQ4LDI2IDUyLDMyIEMgNDgsMzgg"
    "NDIsNDIgMzYsNDQgQyAyOCw0NiAyMCw0NiAxNCw0NCBDIDgsNDIgNCwzNyA0LDMy"
    "IFoiIGZpbGw9IiM2YTlhYjAiIHN0cm9rZT0iIzRhN2E5MCIgc3Ryb2tlLXdpZHRo"
    "PSIwLjgiLz4KPHBhdGggZD0iTSA1MiwzMiBMIDU4LDMyIiBzdHJva2U9IiM0YTdh"
    "OTAiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjxw"
    "YXRoIGQ9Ik0gMTgsMjAgTCAxMiwxMiBNIDE4LDQ0IEwgMTIsNTIiIHN0cm9rZT0i"
    "IzRhN2E5MCIgc3Ryb2tlLXdpZHRoPSIxLjIiIHN0cm9rZS1saW5lY2FwPSJyb3Vu"
    "ZCIvPgo8cGF0aCBkPSJNIDUyLDMyIEwgNjIsMjQgTSA1MiwzMiBMIDYyLDQwIiBz"
    "dHJva2U9IiM0YTdhOTAiIHN0cm9rZS13aWR0aD0iMS41IiBzdHJva2UtbGluZWNh"
    "cD0icm91bmQiLz4KPGxpbmUgeDE9IjYiIHkxPSIzMiIgeDI9IjU4IiB5Mj0iMzIi"
    "IHN0cm9rZT0iIzRhN2E5MCIgc3Ryb2tlLXdpZHRoPSIwLjgiIG9wYWNpdHk9IjAu"
    "NSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CjwvZz4KPCEtLSBXaGl0ZS1iZWFr"
    "ZWQgZG9scGhpbjogc2hvcnQgYmVhaywgd2lkZXIgYm9keSAtLT4KPGcgdHJhbnNm"
    "b3JtPSJ0cmFuc2xhdGUoMzIwLDApIj4KPHBhdGggZD0iTSA1LDMyIEMgNSwyNiAx"
    "MCwyMSAxNiwxOSBDIDIyLDE3IDMwLDE3IDM4LDE5IEMgNDQsMjEgNTAsMjYgNTQs"
    "MzIgQyA1MCwzOCA0NCw0MyAzOCw0NSBDIDMwLDQ3IDIyLDQ3IDE2LDQ1IEMgMTAs"
    "NDMgNSwzOCA1LDMyIFoiIGZpbGw9IiM4YWIwYzAiIHN0cm9rZT0iIzZhOTBhMCIg"
    "c3Ryb2tlLXdpZHRoPSIwLjgiLz4KPHBhdGggZD0iTSA1NCwzMiBMIDU4LDMyIiBz"
    "dHJva2U9IiM2YTkwYTAiIHN0cm9rZS13aWR0aD0iMS44IiBzdHJva2UtbGluZWNh"
    "cD0icm91bmQiLz4KPHBhdGggZD0iTSAyMCwxOSBMIDE1LDEzIE0gMjAsNDUgTCAx"
    "NSw1MSIgc3Ryb2tlPSIjNmE5MGEwIiBzdHJva2Utd2lkdGg9IjEuMiIgc3Ryb2tl"
    "LWxpbmVjYXA9InJvdW5kIi8+CjxwYXRoIGQ9Ik0gNTQsMzIgTCA2MiwyNSBNIDU0"
    "LDMyIEwgNjIsMzkiIHN0cm9rZT0iIzZhOTBhMCIgc3Ryb2tlLXdpZHRoPSIxLjUi"
    "IHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8bGluZSB4MT0iNyIgeTE9IjMyIiB4"
    "Mj0iNTgiIHkyPSIzMiIgc3Ryb2tlPSIjNmE5MGEwIiBzdHJva2Utd2lkdGg9IjAu"
    "OCIgb3BhY2l0eT0iMC41IiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9nPgo8"
    "IS0tIEF0bGFudGljIGNvZDogYnJvYWQgaGVhZCwgdGFwZXJpbmcgYm9keSwgcm91"
    "bmRlZCB0YWlsIGZvcmsgLS0+CjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDM4NCww"
    "KSI+CjxwYXRoIGQ9Ik0gNiwzMiBDIDYsMjYgMTIsMjAgMjAsMTggQyAyOCwxNiAz"
    "NiwxOCA0MiwyMiBDIDQ4LDI2IDUyLDMwIDU0LDMyIEMgNTIsMzQgNDgsMzggNDIs"
    "NDIgQyAzNiw0NiAyOCw0OCAyMCw0NiBDIDEyLDQ0IDYsMzggNiwzMiBaIiBmaWxs"
    "PSIjOGE3YTVhIiBzdHJva2U9IiM2YTVhM2EiIHN0cm9rZS13aWR0aD0iMC44Ii8+"
    "CjxwYXRoIGQ9Ik0gMTQsMTggTCAxMCwxMiBNIDE0LDQ2IEwgMTAsNTIiIHN0cm9r"
    "ZT0iIzZhNWEzYSIgc3Ryb2tlLXdpZHRoPSIxIiBzdHJva2UtbGluZWNhcD0icm91"
    "bmQiLz4KPHBhdGggZD0iTSA1NCwzMiBMIDYyLDI2IEMgNjAsMzIgNjAsMzIgNjIs"
    "MzggTCA1NCwzMiBaIiBmaWxsPSIjNmE1YTNhIiBzdHJva2U9IiM2YTVhM2EiIHN0"
    "cm9rZS13aWR0aD0iMC41Ii8+CjxsaW5lIHgxPSI4IiB5MT0iMzIiIHgyPSI1NCIg"
    "eTI9IjMyIiBzdHJva2U9IiM2YTVhM2EiIHN0cm9rZS13aWR0aD0iMC44IiBvcGFj"
    "aXR5PSIwLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L2c+CjwhLS0gQmFs"
    "dGljIGhlcnJpbmc6IHNsZW5kZXIsIGRlZXBseSBmb3JrZWQgdGFpbCAtLT4KPGcg"
    "dHJhbnNmb3JtPSJ0cmFuc2xhdGUoNDQ4LDApIj4KPHBhdGggZD0iTSA4LDMyIEMg"
    "OCwyOCAxNCwyMyAyMiwyMSBDIDI4LDIwIDM0LDIwIDQwLDIyIEMgNDYsMjQgNTAs"
    "MjggNTQsMzIgQyA1MCwzNiA0Niw0MCA0MCw0MiBDIDM0LDQ0IDI4LDQ0IDIyLDQz"
    "IEMgMTQsNDEgOCwzNiA4LDMyIFoiIGZpbGw9IiM3YThhYWEiIHN0cm9rZT0iIzVh"
    "NmE4YSIgc3Ryb2tlLXdpZHRoPSIwLjgiLz4KPHBhdGggZD0iTSAxOCwyMSBMIDE1"
    "LDE2IE0gMTgsNDMgTCAxNSw0OCIgc3Ryb2tlPSIjNWE2YThhIiBzdHJva2Utd2lk"
    "dGg9IjAuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CjxwYXRoIGQ9Ik0gNTQs"
    "MzIgTCA2MywyNCBNIDU0LDMyIEwgNjMsNDAiIHN0cm9rZT0iIzVhNmE4YSIgc3Ry"
    "b2tlLXdpZHRoPSIxLjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8bGluZSB4"
    "MT0iMTAiIHkxPSIzMiIgeDI9IjU0IiB5Mj0iMzIiIHN0cm9rZT0iIzVhNmE4YSIg"
    "c3Ryb2tlLXdpZHRoPSIwLjYiIG9wYWNpdHk9IjAuNSIgc3Ryb2tlLWxpbmVjYXA9"
    "InJvdW5kIi8+CjwvZz4KPCEtLSBBdGxhbnRpYyBzYWxtb246IHJvYnVzdCBib2R5"
    "LCBzbGlnaHRseSBmb3JrZWQgdGFpbCAtLT4KPGcgdHJhbnNmb3JtPSJ0cmFuc2xh"
    "dGUoNTEyLDApIj4KPHBhdGggZD0iTSA2LDMyIEMgNiwyNiAxMiwyMSAyMCwxOSBD"
    "IDI2LDE3IDM0LDE3IDQwLDE5IEMgNDYsMjEgNTIsMjYgNTYsMzIgQyA1MiwzOCA0"
    "Niw0MyA0MCw0NSBDIDM0LDQ3IDI2LDQ3IDIwLDQ1IEMgMTIsNDMgNiwzOCA2LDMy"
    "IFoiIGZpbGw9IiNjMDgwNjAiIHN0cm9rZT0iI2EwNjA0MCIgc3Ryb2tlLXdpZHRo"
    "PSIwLjgiLz4KPHBhdGggZD0iTSAxNiwxOSBMIDEyLDEzIE0gMTYsNDUgTCAxMiw1"
    "MSIgc3Ryb2tlPSIjYTA2MDQwIiBzdHJva2Utd2lkdGg9IjEiIHN0cm9rZS1saW5l"
    "Y2FwPSJyb3VuZCIvPgo8cGF0aCBkPSJNIDU2LDMyIEwgNjMsMjYgQyA2MSwzMiA2"
    "MSwzMiA2MywzOCBMIDU2LDMyIFoiIGZpbGw9IiNhMDYwNDAiIHN0cm9rZT0iI2Ew"
    "NjA0MCIgc3Ryb2tlLXdpZHRoPSIwLjUiLz4KPGxpbmUgeDE9IjgiIHkxPSIzMiIg"
    "eDI9IjU2IiB5Mj0iMzIiIHN0cm9rZT0iI2EwNjA0MCIgc3Ryb2tlLXdpZHRoPSIw"
    "LjgiIG9wYWNpdHk9IjAuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+CjwvZz4K"
    "PC9zdmc+"
)

#: deck.gl icon-mapping dict keyed by species name.
#: ``anchorY=32`` centres the icon vertically on the point.
ICON_MAPPING: dict[str, dict] = {
    # Seals
    "Grey seal":            {"x": 0,   "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Ringed seal":          {"x": 64,  "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Harbour seal":         {"x": 128, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    # Dolphins
    "Harbour porpoise":     {"x": 192, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Bottlenose dolphin":   {"x": 256, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "White-beaked dolphin": {"x": 320, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    # Fish
    "Atlantic cod":         {"x": 384, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Baltic herring":       {"x": 448, "y": 0, "width": 64, "height": 64, "anchorY": 32},
    "Atlantic salmon":      {"x": 512, "y": 0, "width": 64, "height": 64, "anchorY": 32},
}


# ---------------------------------------------------------------------------
# Data helper — format_trips
# ---------------------------------------------------------------------------

def format_trips(
    paths: list[list[list[float]]],
    *,
    loop_length: int = 600,
    timestamps: list[list[int | float]] | None = None,
    properties: list[dict] | None = None,
) -> list[dict]:
    """Convert raw coordinate lists into the dict format ``trips_layer()`` expects.

    This bridges the gap between *"I have paths"* and *"trips_layer needs
    this exact dict structure"*.  You supply a list of 2-D paths (each a
    list of ``[lon, lat]`` pairs) and ``format_trips`` adds evenly-spaced
    timestamps, builds the 3-D ``[lon, lat, time]`` arrays, and merges in
    any per-trip metadata you provide.

    Parameters
    ----------
    paths
        One entry per trip.  Each entry is a list of coordinate pairs
        ``[[lon, lat], ...]``.  If a coordinate already has three
        elements ``[lon, lat, time]``, the third element is kept as the
        timestamp and the *timestamps* parameter is ignored for that
        trip.
    loop_length
        Total animation loop duration (arbitrary time units).  Used to
        auto-generate evenly-spaced timestamps when the path has only
        2-D coordinates and no explicit *timestamps* are supplied.
    timestamps
        Optional explicit per-trip timestamp arrays.  Must be the same
        length as *paths* and each inner list must match the
        corresponding path length.  If ``None``, timestamps are
        generated automatically from *loop_length*.
    properties
        Optional list of dicts (one per trip) with arbitrary extra keys
        (e.g. ``name``, ``species``, ``color``).  These are merged into
        the output dicts so that ``trips_layer`` accessors such as
        ``getColor="@@d.color"`` work.

    Returns
    -------
    list[dict]
        Each dict has at least:

        * ``path`` – list of ``[lon, lat, time]`` triplets
        * ``timestamps`` – flat list of time values

        Plus any keys supplied via *properties*.

    Examples
    --------
    >>> from shiny_deckgl.ibm import format_trips
    >>> trips = format_trips(
    ...     paths=[[[20.0, 57.0], [20.5, 57.2], [20.0, 57.0]]],
    ...     loop_length=100,
    ...     properties=[{"name": "Trip 1", "color": [255, 0, 0]}],
    ... )
    >>> trips[0]["path"][0]
    [20.0, 57.0, 0]
    """
    if properties is not None and len(properties) != len(paths):
        raise ValueError(
            f"properties length ({len(properties)}) must match "
            f"paths length ({len(paths)})"
        )
    if timestamps is not None and len(timestamps) != len(paths):
        raise ValueError(
            f"timestamps length ({len(timestamps)}) must match "
            f"paths length ({len(paths)})"
        )

    result: list[dict] = []

    for idx, path in enumerate(paths):
        n_pts = len(path)
        if n_pts == 0:
            continue

        # Determine timestamps for this trip
        has_3d = len(path[0]) >= 3
        if has_3d:
            ts = [pt[2] for pt in path]
            path_3d = [[pt[0], pt[1], pt[2]] for pt in path]
        elif timestamps is not None:
            ts = list(timestamps[idx])
            if len(ts) != n_pts:
                raise ValueError(
                    f"timestamps[{idx}] length ({len(ts)}) != "
                    f"path length ({n_pts})"
                )
            path_3d = [[pt[0], pt[1], t] for pt, t in zip(path, ts)]
        else:
            # Auto-generate evenly spaced
            if n_pts == 1:
                ts = [0]
            else:
                ts = [int(i * loop_length / (n_pts - 1)) for i in range(n_pts)]
            path_3d = [[pt[0], pt[1], t] for pt, t in zip(path, ts)]

        trip: dict[str, Any] = {
            "path": path_3d,
            "timestamps": ts,
        }

        # Merge user-supplied properties
        if properties is not None:
            trip.update(properties[idx])

        result.append(trip)

    return result


# ---------------------------------------------------------------------------
# Shiny module — trips animation controls
# ---------------------------------------------------------------------------

def trips_animation_ui(
    id: str,
    *,
    speed_default: float = 8.0,
    speed_min: float = 0.5,
    speed_max: float = 100.0,
    speed_step: float = 0.5,
    trail_default: int = 180,
    trail_min: int = 20,
    trail_max: int = 400,
    trail_step: int = 10,
):
    """UI fragment for TripsLayer animation controls.

    Drop this into a sidebar or card to get Play / Pause / Reset
    buttons plus speed and trail-length sliders.  Wire it up on the
    server side with :func:`trips_animation_server`.

    Parameters
    ----------
    id
        Shiny module namespace ID (e.g. ``"seal_anim"``).
    speed_default / speed_min / speed_max / speed_step
        Initial value and range for the animation speed slider.
    trail_default / trail_min / trail_max / trail_step
        Initial value and range for the trail length slider.

    Returns
    -------
    shiny.ui.TagList
        Ready to embed in a sidebar or layout.
    """
    from shiny import module, ui as _ui  # deferred to avoid import at load

    @module.ui
    def _inner_ui():
        return _ui.TagList(
            _ui.layout_columns(
                _ui.input_action_button(
                    "play", "\u25B6 Play", class_="btn-sm btn-success",
                ),
                _ui.input_action_button(
                    "pause", "\u23F8 Pause", class_="btn-sm btn-warning",
                ),
                _ui.input_action_button(
                    "reset", "\u23F9 Reset", class_="btn-sm btn-danger",
                ),
                col_widths=(4, 4, 4),
            ),
            _ui.input_slider(
                "speed", "Animation speed",
                min=speed_min, max=speed_max, value=speed_default,
                step=speed_step,
            ),
            _ui.input_slider(
                "trail", "Trail length",
                min=trail_min, max=trail_max, value=trail_default,
                step=trail_step,
            ),
        )

    return _inner_ui(id)


def trips_animation_server(
    id: str,
    *,
    widget: "MapWidget",
    session: "Session",
):
    """Server logic for TripsLayer animation controls.

    Wires the Play / Pause / Reset buttons produced by
    :func:`trips_animation_ui` to the widget's ``trips_control``
    method.  Returns a namespace object whose ``.speed()`` and
    ``.trail()`` reactive accessors mirror the slider values so
    the caller can feed them into ``trips_layer()``.

    Parameters
    ----------
    id
        Must match the *id* passed to :func:`trips_animation_ui`.
    widget
        The :class:`~shiny_deckgl.MapWidget` that hosts the TripsLayer.
    session
        The active Shiny ``Session``.

    Returns
    -------
    types.SimpleNamespace
        ``.speed`` and ``.trail`` — callable reactive values
        (``input.speed`` and ``input.trail`` from the module).

    Example
    -------
    ::

        anim = trips_animation_server("seal_anim", widget=my_widget, session=session)
        # Later, inside a reactive effect:
        speed = anim.speed()
        trail = anim.trail()
    """
    import types
    from shiny import module, reactive

    result_holder: list = []

    @module.server
    def _inner_server(input, output, inner_session):
        @reactive.Effect
        @reactive.event(input.play)
        async def _play():
            await widget.trips_control(session, "resume")

        @reactive.Effect
        @reactive.event(input.pause)
        async def _pause():
            await widget.trips_control(session, "pause")

        @reactive.Effect
        @reactive.event(input.reset)
        async def _reset():
            await widget.trips_control(session, "reset")

        result_holder.append(
            types.SimpleNamespace(speed=input.speed, trail=input.trail)
        )

    _inner_server(id)
    return result_holder[0]
