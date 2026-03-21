# Sprite Icon Pipeline

Drop source icons into this directory, then run `build_atlas.py` to generate the base64-encoded SVG sprite sheet for `ibm.py`.

## Directory Structure

```
sprites/
  README.md
  build_atlas.py        # Pipeline script
  source/               # Drop your source icons here (SVG or PNG)
    grey_seal.svg        # or .png
    ringed_seal.svg
    harbour_seal.svg
    harbour_porpoise.svg
    bottlenose_dolphin.svg
    white_beaked_dolphin.svg
    atlantic_cod.svg
    baltic_herring.svg
    atlantic_salmon.svg
  output/                # Generated files (gitignored)
    atlas.svg            # Combined sprite sheet
    atlas_preview.html   # Browser preview
```

## Requirements

- Each icon must face RIGHT (head/snout pointing right, tail left)
- Any size — the pipeline scales to 64x64 per icon
- SVG or PNG accepted (PNG converted via embedded `<image>`)
- Transparent background

## Usage

```bash
python sprites/build_atlas.py
```

This will:
1. Read all 9 source icons from `sprites/source/`
2. Scale each to 64x64
3. Combine into a 576x64 strip
4. Generate base64-encoded data-URI
5. Update `src/shiny_deckgl/ibm.py` with the new ICON_ATLAS
6. Write preview HTML to `sprites/output/atlas_preview.html`
