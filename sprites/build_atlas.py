#!/usr/bin/env python3
"""Build the icon atlas sprite sheet from source icons.

Reads source PNG/SVG icons from sprites/source/, processes them
(background removal, rotation, color tinting), scales to icon_size,
combines into a horizontal strip, and updates ibm.py.

Usage:
    python sprites/build_atlas.py
    python sprites/build_atlas.py --preview   # only generate preview
    python sprites/build_atlas.py --size 128  # 128x128 per icon
"""
from __future__ import annotations

import argparse
import base64
import io
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR = SCRIPT_DIR / "source"
OUTPUT_DIR = SCRIPT_DIR / "output"
IBM_PY = SCRIPT_DIR.parent / "src" / "shiny_deckgl" / "ibm.py"

# Species order in the atlas strip.
# Each entry: (species_label, source_file, rotation, flip, tint_rgb, scale)
# rotation: 0=as-is, -90=rotate CW 90° (dorsal icons facing UP → RIGHT)
# flip: True to mirror horizontally
# tint_rgb: (R,G,B) to colorize the silhouette
# scale: fraction of icon_size to fill (1.0 = full, 0.7 = 70% — for smaller species)
SPECIES_CONFIG = [
    # Seals — dorsal, facing up → rotate 90° CW
    # Grey seal: largest Baltic seal, up to 2.3m, bulky
    ("Grey seal",            "seal.png",    -90, False, (122, 138, 138), 1.0),
    # Ringed seal: smallest, ~1.3m, slender
    ("Ringed seal",          "seal.png",    -90, False, (74, 140, 220),  0.75),
    # Harbour seal: medium, ~1.7m
    ("Harbour seal",         "seal.png",    -90, False, (200, 160, 80),  0.85),
    # Dolphins — dorsal, facing up → rotate 90° CW
    # Harbour porpoise: smallest cetacean in Baltic, ~1.5m
    ("Harbour porpoise",     "dolphin.png", -90, False, (90, 122, 138),  0.75),
    # Bottlenose dolphin: largest, up to 3.8m
    ("Bottlenose dolphin",   "dolphin.png", -90, False, (106, 154, 176), 1.0),
    # White-beaked dolphin: medium-large, ~2.8m
    ("White-beaked dolphin", "dolphin.png", -90, False, (138, 176, 192), 0.9),
    # Fish
    # Atlantic cod: large, robust, up to 1.5m
    ("Atlantic cod",         "salmon.png",  0,   False, (138, 122, 90),  0.65),
    # Baltic herring: small, slender, ~25cm
    ("Baltic herring",       "smelt.png",   0,   False, (122, 138, 170), 0.4),
    # Atlantic salmon: large, up to 1.5m
    ("Atlantic salmon",      "salmon.png",  0,   False, (192, 128, 96),  0.7),
    # European smelt: small, slender, ~20cm
    ("European smelt",       "smelt.png",   0,   False, (160, 180, 140), 0.35),
]


def clean_alpha(img: Image.Image, threshold: int = 30) -> Image.Image:
    """Clean up the image for atlas use.

    If the image already has a useful alpha channel (many transparent
    pixels), use it directly. Otherwise, detect background color from
    corners and make it transparent.
    """
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size

    # Check if alpha channel is already meaningful
    alpha_zeros = sum(1 for y in range(h) for x in range(w) if pixels[x, y][3] == 0)
    total = w * h
    has_alpha = alpha_zeros > total * 0.1  # >10% transparent = has alpha

    if has_alpha:
        # Alpha channel exists — just use it as-is
        return img

    # No alpha — detect background from corners and remove it
    corners = [
        pixels[0, 0], pixels[w - 1, 0],
        pixels[0, h - 1], pixels[w - 1, h - 1],
    ]
    avg_r = sum(c[0] for c in corners) // 4
    avg_g = sum(c[1] for c in corners) // 4
    avg_b = sum(c[2] for c in corners) // 4

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            # Distance from background color
            dist = abs(r - avg_r) + abs(g - avg_g) + abs(b - avg_b)
            if dist < threshold * 3:
                pixels[x, y] = (r, g, b, 0)
            else:
                pixels[x, y] = (0, 0, 0, 255)

    return img


def tint_silhouette(img: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Tint a silhouette image with the given RGB color.

    Preserves alpha channel, replaces RGB with the tint color.
    """
    img = img.convert("RGBA")
    r, g, b = color

    # Create a solid color image and composite using alpha
    tint = Image.new("RGBA", img.size, (r, g, b, 255))
    # Use the original's alpha as mask
    _, _, _, alpha = img.split()
    tint.putalpha(alpha)
    return tint


def process_icon(
    src_path: Path,
    icon_size: int,
    rotation: int,
    flip: bool,
    tint: tuple[int, int, int] | None,
    scale: float = 1.0,
) -> Image.Image:
    """Load, process, and scale a source icon."""
    img = Image.open(src_path).convert("RGBA")

    # Clean up alpha / remove background
    img = clean_alpha(img)

    # Rotate if needed (PIL rotation is counter-clockwise, so -90 = CW 90°)
    if rotation != 0:
        img = img.rotate(rotation, expand=True, resample=Image.BICUBIC)

    # Flip horizontally if needed
    if flip:
        img = ImageOps.mirror(img)

    # Tint the silhouette
    if tint:
        img = tint_silhouette(img, tint)

    # Scale to fit within icon_size * scale (for species-specific sizing)
    target = int(icon_size * scale)
    img.thumbnail((target, target), Image.LANCZOS)

    # Center on a square canvas
    canvas = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
    offset_x = (icon_size - img.width) // 2
    offset_y = (icon_size - img.height) // 2
    canvas.paste(img, (offset_x, offset_y), img)

    return canvas


def build_atlas(icon_size: int = 64) -> Image.Image:
    """Build the combined atlas strip."""
    n = len(SPECIES_CONFIG)
    atlas = Image.new("RGBA", (n * icon_size, icon_size), (0, 0, 0, 0))

    for i, (label, filename, rotation, flip, tint, scale) in enumerate(SPECIES_CONFIG):
        src_path = SOURCE_DIR / filename
        if not src_path.exists():
            print(f"  WARNING: {filename} not found — skipping {label}")
            continue

        icon = process_icon(src_path, icon_size, rotation, flip, tint, scale)
        atlas.paste(icon, (i * icon_size, 0), icon)
        print(f"  [{i}] {label}: {filename} (rot={rotation}, flip={flip}, scale={scale})")

    return atlas


def atlas_to_data_uri(atlas: Image.Image) -> str:
    """Convert atlas PIL Image to base64 PNG data-URI."""
    buf = io.BytesIO()
    atlas.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def format_python_string(data_uri: str) -> str:
    """Format the data-URI as a multi-line Python string."""
    prefix_end = data_uri.index(",") + 1
    prefix = data_uri[:prefix_end]
    b64 = data_uri[prefix_end:]

    chunk_size = 64
    chunks = [b64[i:i + chunk_size] for i in range(0, len(b64), chunk_size)]

    lines = ['ICON_ATLAS: str = (']
    lines.append(f'    "{prefix}"')
    for chunk in chunks:
        lines.append(f'    "{chunk}"')
    lines.append(")")
    return "\n".join(lines)


def update_ibm_py(data_uri: str) -> None:
    """Replace ICON_ATLAS in ibm.py."""
    content = IBM_PY.read_text(encoding="utf-8")

    pattern = r'ICON_ATLAS: str = \(\n(?:    "[^"]*"\n)+\)'
    match = re.search(pattern, content)
    if not match:
        print("  ERROR: Could not find ICON_ATLAS in ibm.py")
        sys.exit(1)

    new_assignment = format_python_string(data_uri)
    content = content[:match.start()] + new_assignment + content[match.end():]

    IBM_PY.write_text(content, encoding="utf-8")
    print(f"  Updated {IBM_PY}")


def write_preview(atlas: Image.Image, icon_size: int) -> None:
    """Write preview files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save atlas PNG
    atlas_path = OUTPUT_DIR / "atlas.png"
    atlas.save(atlas_path, format="PNG")

    # Save individual icons
    for i, (label, *_) in enumerate(SPECIES_CONFIG):
        icon = atlas.crop((i * icon_size, 0, (i + 1) * icon_size, icon_size))
        safe_name = label.lower().replace(" ", "_").replace("-", "_")
        icon.save(OUTPUT_DIR / f"{safe_name}.png", format="PNG")

    # HTML preview
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{ background: #1a1a2e; color: #eee; font-family: sans-serif; padding: 20px; }}
h1 {{ font-size: 18px; }}
.strip {{ background: #0f3460; padding: 10px; border-radius: 6px; display: inline-block; }}
.strip img {{ height: {icon_size * 3}px; image-rendering: auto; }}
.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; max-width: 800px; margin-top: 20px; }}
.card {{ background: #16213e; border-radius: 8px; padding: 16px; text-align: center; }}
.card img {{ width: {icon_size * 3}px; height: {icon_size * 3}px; image-rendering: auto; }}
.card .name {{ font-size: 14px; margin-top: 8px; font-weight: 600; }}
.group {{ grid-column: 1 / -1; color: #e94560; text-transform: uppercase; letter-spacing: 2px;
          font-size: 13px; border-bottom: 1px solid #333; padding: 8px 0 4px; margin-top: 8px; }}
</style>
</head>
<body>
<h1>Sprite Atlas — {len(SPECIES_CONFIG)} species @ {icon_size}x{icon_size}</h1>
<p>Full strip:</p>
<div class="strip"><img src="atlas.png"></div>
<div class="grid">
"""
    groups = ["Seals", "Seals", "Seals", "Dolphins", "Dolphins", "Dolphins",
              "Fish", "Fish", "Fish", "Fish"]
    last_group = ""
    for i, (label, *_) in enumerate(SPECIES_CONFIG):
        g = groups[i]
        if g != last_group:
            last_group = g
            html += f'<div class="group">{g}</div>\n'
        safe = label.lower().replace(" ", "_").replace("-", "_")
        html += f'<div class="card"><img src="{safe}.png"><div class="name">{label}</div></div>\n'

    html += "</div></body></html>"

    preview_path = OUTPUT_DIR / "atlas_preview.html"
    preview_path.write_text(html, encoding="utf-8")
    print(f"  Preview: {preview_path}")
    print(f"  Atlas PNG: {atlas_path}")


def main():
    parser = argparse.ArgumentParser(description="Build icon atlas")
    parser.add_argument("--preview", action="store_true",
                        help="Only generate preview, don't update ibm.py")
    parser.add_argument("--size", type=int, default=64,
                        help="Icon size in pixels (default: 64)")
    args = parser.parse_args()

    print(f"Building atlas ({args.size}x{args.size} per icon)...")

    # Check sources exist
    missing = []
    for label, filename, *_ in SPECIES_CONFIG:
        if not (SOURCE_DIR / filename).exists():
            missing.append(f"  {filename} — {label}")
    if missing:
        print("Missing source files:")
        for m in missing:
            print(m)
        sys.exit(1)

    atlas = build_atlas(args.size)
    write_preview(atlas, args.size)

    if not args.preview:
        data_uri = atlas_to_data_uri(atlas)
        update_ibm_py(data_uri)
        b64_len = len(data_uri)
        print(f"\n  Done! Base64 length: {b64_len} chars")
    else:
        print("\n  Preview only — ibm.py not modified")


if __name__ == "__main__":
    main()
