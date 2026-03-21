#!/usr/bin/env python3
"""Build the icon atlas sprite sheet from source icons.

Reads individual icon files (SVG or PNG) from sprites/source/,
scales each to 64x64, combines into a horizontal strip, encodes
as a base64 data-URI, and updates ibm.py with the new ICON_ATLAS.

Usage:
    python sprites/build_atlas.py
    python sprites/build_atlas.py --preview   # only generate preview, don't update ibm.py
    python sprites/build_atlas.py --size 128   # use 128x128 per icon instead of 64
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import sys
from pathlib import Path

# Species in atlas order — filenames must match (underscored, lowercase)
SPECIES_ORDER = [
    ("grey_seal",            "Grey seal"),
    ("ringed_seal",          "Ringed seal"),
    ("harbour_seal",         "Harbour seal"),
    ("harbour_porpoise",     "Harbour porpoise"),
    ("bottlenose_dolphin",   "Bottlenose dolphin"),
    ("white_beaked_dolphin", "White-beaked dolphin"),
    ("atlantic_cod",         "Atlantic cod"),
    ("baltic_herring",       "Baltic herring"),
    ("atlantic_salmon",      "Atlantic salmon"),
]

SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR = SCRIPT_DIR / "source"
OUTPUT_DIR = SCRIPT_DIR / "output"
IBM_PY = SCRIPT_DIR.parent / "src" / "shiny_deckgl" / "ibm.py"


def find_source_icon(filename_stem: str) -> Path | None:
    """Find a source icon file by stem name (SVG preferred over PNG)."""
    for ext in (".svg", ".png", ".PNG", ".SVG"):
        p = SOURCE_DIR / (filename_stem + ext)
        if p.exists():
            return p
    return None


def build_svg_atlas(icon_size: int = 64) -> str:
    """Build a combined SVG atlas from source icons.

    Returns the SVG string.
    """
    n = len(SPECIES_ORDER)
    width = n * icon_size
    height = icon_size

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    ]

    for i, (stem, label) in enumerate(SPECIES_ORDER):
        src = find_source_icon(stem)
        if src is None:
            print(f"  WARNING: No source icon for '{stem}' — using placeholder")
            x = i * icon_size
            parts.append(
                f'<rect x="{x}" y="0" width="{icon_size}" height="{icon_size}" '
                f'fill="#333" stroke="#666" stroke-width="1"/>'
                f'<text x="{x + icon_size // 2}" y="{icon_size // 2 + 4}" '
                f'text-anchor="middle" fill="#999" font-size="8">{stem}</text>'
            )
            continue

        x = i * icon_size
        ext = src.suffix.lower()

        if ext == ".svg":
            # Read SVG content, strip outer <svg> tag, wrap in positioned <g>
            svg_content = src.read_text(encoding="utf-8")

            # Extract viewBox or width/height from source SVG
            vb_match = re.search(r'viewBox="([^"]+)"', svg_content)
            w_match = re.search(r'width="([^"]+)"', svg_content)
            h_match = re.search(r'height="([^"]+)"', svg_content)

            if vb_match:
                vb = vb_match.group(1)
                vb_parts = vb.split()
                src_w = float(vb_parts[2]) - float(vb_parts[0])
                src_h = float(vb_parts[3]) - float(vb_parts[1])
            elif w_match and h_match:
                src_w = float(re.sub(r'[^0-9.]', '', w_match.group(1)))
                src_h = float(re.sub(r'[^0-9.]', '', h_match.group(1)))
                vb = f"0 0 {src_w} {src_h}"
            else:
                src_w = src_h = icon_size
                vb = f"0 0 {icon_size} {icon_size}"

            # Scale to fit icon_size x icon_size
            scale = min(icon_size / src_w, icon_size / src_h)
            scaled_w = src_w * scale
            scaled_h = src_h * scale
            offset_x = x + (icon_size - scaled_w) / 2
            offset_y = (icon_size - scaled_h) / 2

            # Use nested <svg> to handle viewBox scaling cleanly
            parts.append(
                f'<svg x="{offset_x:.1f}" y="{offset_y:.1f}" '
                f'width="{scaled_w:.1f}" height="{scaled_h:.1f}" '
                f'viewBox="{vb}">'
            )
            # Strip the outer <svg...> and </svg> tags, keep inner content
            inner = re.sub(r'<\?xml[^>]*\?>\s*', '', svg_content)
            inner = re.sub(r'<svg[^>]*>', '', inner, count=1)
            inner = re.sub(r'</svg>\s*$', '', inner)
            parts.append(inner)
            parts.append('</svg>')

        elif ext == ".png":
            # Embed PNG as base64 <image> element
            png_data = base64.b64encode(src.read_bytes()).decode()
            parts.append(
                f'<image x="{x}" y="0" width="{icon_size}" height="{icon_size}" '
                f'href="data:image/png;base64,{png_data}"/>'
            )

        print(f"  [{i}] {label}: {src.name} ({ext})")

    parts.append("</svg>")
    return "\n".join(parts)


def encode_data_uri(svg: str) -> str:
    """Encode SVG string as base64 data-URI."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def format_python_string(data_uri: str, var_name: str = "ICON_ATLAS") -> str:
    """Format the data-URI as a multi-line Python string assignment."""
    prefix = "data:image/svg+xml;base64,"
    b64 = data_uri[len(prefix):]

    chunk_size = 64
    chunks = [b64[i:i + chunk_size] for i in range(0, len(b64), chunk_size)]

    lines = [f'{var_name}: str = (']
    lines.append(f'    "{prefix}"')
    for chunk in chunks:
        lines.append(f'    "{chunk}"')
    lines.append(")")
    return "\n".join(lines)


def update_ibm_py(data_uri: str) -> None:
    """Replace ICON_ATLAS in ibm.py with the new data-URI."""
    if not IBM_PY.exists():
        print(f"  ERROR: {IBM_PY} not found")
        sys.exit(1)

    content = IBM_PY.read_text(encoding="utf-8")

    # Find the ICON_ATLAS assignment block
    pattern = r'ICON_ATLAS: str = \(\n(?:    "[^"]*"\n)+\)'
    match = re.search(pattern, content)
    if not match:
        print("  ERROR: Could not find ICON_ATLAS assignment in ibm.py")
        print("  Looking for pattern: ICON_ATLAS: str = (\\n    \"...\"\\n)")
        sys.exit(1)

    new_assignment = format_python_string(data_uri)
    content = content[:match.start()] + new_assignment + content[match.end():]

    IBM_PY.write_text(content, encoding="utf-8")
    print(f"  Updated {IBM_PY}")


def write_preview(svg: str, icon_size: int) -> None:
    """Write an HTML preview page."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save raw SVG
    svg_path = OUTPUT_DIR / "atlas.svg"
    svg_path.write_text(svg, encoding="utf-8")

    # Build preview HTML
    labels = [label for _, label in SPECIES_ORDER]
    preview = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{ background: #1a1a2e; color: #eee; font-family: sans-serif; padding: 20px; }}
h1 {{ font-size: 18px; }}
.strip {{ background: #0f3460; padding: 10px; border-radius: 6px; display: inline-block; }}
.strip img {{ height: {icon_size * 2}px; image-rendering: pixelated; }}
.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; max-width: 800px; margin-top: 20px; }}
.card {{ background: #16213e; border-radius: 8px; padding: 12px; text-align: center; }}
.card img {{ width: {icon_size * 2}px; height: {icon_size * 2}px; }}
.card .name {{ font-size: 13px; margin-top: 6px; }}
</style>
</head>
<body>
<h1>Sprite Atlas Preview — {len(labels)} species @ {icon_size}x{icon_size}</h1>
<div class="strip"><img src="atlas.svg" alt="Full atlas strip"></div>
<div class="grid">
"""
    for i, (stem, label) in enumerate(SPECIES_ORDER):
        x = i * icon_size
        preview += f"""<div class="card">
<svg width="{icon_size * 2}" height="{icon_size * 2}" viewBox="{x} 0 {icon_size} {icon_size}">
<image href="atlas.svg" width="{icon_size * len(labels)}" height="{icon_size}"/>
</svg>
<div class="name">{label}</div>
</div>
"""
    preview += "</div></body></html>"

    preview_path = OUTPUT_DIR / "atlas_preview.html"
    preview_path.write_text(preview, encoding="utf-8")
    print(f"  Preview: {preview_path}")


def main():
    parser = argparse.ArgumentParser(description="Build icon atlas sprite sheet")
    parser.add_argument("--preview", action="store_true",
                        help="Only generate preview, don't update ibm.py")
    parser.add_argument("--size", type=int, default=64,
                        help="Icon size in pixels (default: 64)")
    args = parser.parse_args()

    print(f"Building atlas ({args.size}x{args.size} per icon)...")
    print(f"Source dir: {SOURCE_DIR}")

    # Check what's available
    found = 0
    for stem, label in SPECIES_ORDER:
        src = find_source_icon(stem)
        if src:
            found += 1

    if found == 0:
        print(f"\n  No source icons found in {SOURCE_DIR}/")
        print("  Drop SVG or PNG files named:")
        for stem, label in SPECIES_ORDER:
            print(f"    {stem}.svg  (or .png)  — {label}")
        print("\n  Then re-run this script.")
        sys.exit(1)

    print(f"  Found {found}/{len(SPECIES_ORDER)} source icons\n")

    svg = build_svg_atlas(args.size)
    write_preview(svg, args.size)

    if not args.preview:
        data_uri = encode_data_uri(svg)
        update_ibm_py(data_uri)
        print(f"\n  Done! ICON_ATLAS updated in ibm.py")
        print(f"  Base64 length: {len(data_uri)} chars")
    else:
        print(f"\n  Preview only — ibm.py not modified")


if __name__ == "__main__":
    main()
