# Dorsal Sprite Expansion — Design Spec

## Goal

Replace the 3 side-view seal silhouettes with 9 top-down (dorsal) species-specific directional silhouettes for seals, dolphins, and fish. The body shape itself conveys movement direction (head forward, tail trailing).

## Species & Colors

| # | Group | Species | Fill | Stroke | Atlas X |
|---|-------|---------|------|--------|---------|
| 0 | Seal | Grey seal | #7a8a8a | #5a6a6a | 0 |
| 1 | Seal | Ringed seal | #4a8cdc | #346ab0 | 64 |
| 2 | Seal | Harbour seal | #c8a050 | #9a7a30 | 128 |
| 3 | Dolphin | Harbour porpoise | #5a7a8a | #3a5a6a | 192 |
| 4 | Dolphin | Bottlenose dolphin | #6a9ab0 | #4a7a90 | 256 |
| 5 | Dolphin | White-beaked dolphin | #8ab0c0 | #6a90a0 | 320 |
| 6 | Fish | Atlantic cod | #8a7a5a | #6a5a3a | 384 |
| 7 | Fish | Baltic herring | #7a8aaa | #5a6a8a | 448 |
| 8 | Fish | Atlantic salmon | #c08060 | #a06040 | 512 |

## SVG Atlas Format

- **Dimensions:** 576 x 64 (9 icons at 64x64 each)
- **viewBox:** `0 0 576 64`
- **Orientation:** All facing RIGHT (east) — JS computes rotation from movement heading
- **Encoding:** Base64 data-URI

## Art Style (dorsal/top-down)

Each icon has exactly 2 SVG elements:

1. **Body silhouette** (`<path>`) — species-specific dorsal outline with fill + stroke (0.8px)
2. **Midline/spine** (`<path>` or `<line>`) — darker accent line running head-to-tail along the dorsal ridge, opacity 0.5

No eye dots, no belly patches — pure top-down view.

### Shape Guidelines

**Seals:** Teardrop/oval body. Four short flippers splayed at ~45 degree angles from body. Hind flippers trailing as a V-tail. Head end is rounded/blunt.
- Grey seal: widest body, bulky oval, broad head
- Ringed seal: slender elongated body, narrow head
- Harbour seal: medium build, rounded head

**Dolphins:** Streamlined torpedo. Pectoral fins as small lateral wings angled back. Tail flukes as horizontal V at rear. NO dorsal fin (midline — invisible from above). Head tapers to pointed/beaked snout.
- Harbour porpoise: smallest, rounded snout (no beak), short pectoral fins
- Bottlenose dolphin: larger, pronounced beak extending forward, longer pectoral fins
- White-beaked dolphin: short beak, wider body, lighter dorsal patch (use lighter fill stripe)

**Fish:** Fusiform body widest at pectoral region. Pectoral fins as small lateral wings. Tail fin as V-fork at rear. NO dorsal fin visible from above.
- Atlantic cod: broad head tapering to narrow tail, wide pectoral fins, slightly rounded fork
- Baltic herring: slender streamlined body, small pectoral fins, deeply forked tail
- Atlantic salmon: robust body, medium pectoral fins, slightly forked tail

## Code Changes

### `ibm.py`

1. Replace `ICON_ATLAS` with new 576x64 base64-encoded SVG
2. Replace `ICON_MAPPING` — 9 entries instead of 3
3. Expand `SPECIES_COLORS` — add 6 new species entries
4. Update docstrings to reflect all 9 species
5. Keep `__all__`, `format_trips`, `trips_animation_ui`, `trips_animation_server` unchanged

### Tests

Update `test_basic.py` `TestIconAtlas` and `TestIconMapping`:
- Atlas width 576 (was 192)
- 9 icon mapping entries (was 3)
- All 9 species have colors

## Backward Compatibility

- Existing seal species keys (`"Grey seal"`, `"Ringed seal"`, `"Harbour seal"`) keep the same names and the same atlas positions (0, 64, 128)
- New species are appended at positions 192+
- Existing code using seal icons works unchanged
