# VERIFICATION — Woodblock Source Image
**Date:** 2026-04-09
**Session:** v002

---

## VERDICT: NO — V1 and V2 use DIFFERENT source images

The v1 and v2 8" woodblock physical lenses were built from **different source images**.
This means any geometry comparison (depth, curvature, slopes) reflects BOTH pipeline
differences AND input differences. The comparison is NOT apples-to-apples.

---

## Evidence

### V1 source image
- **File:** `INKFORGE/woodblock.png`
- **MD5:** `a08bb8049c5d605406a494935f1402fa`
- **Size:** 457,734 bytes (457 KB)
- **Dimensions:** 1024x1024, grayscale (mode L)
- **Pixel stats:** range 41–255, mean 73.4
- **Confirmed by:** PROD run log `logs/julia_20260317_201430.log` line 2: `Loading: ./INKFORGE/woodblock.png`

### V2 source image
- **File:** `images/woodblock2.png` (identical to v1's `Final cows/woodblock2.png`)
- **MD5:** `c7ff322408426698f8946ae70d8e0625`
- **Size:** 1,461,215 bytes (1.39 MB)
- **Dimensions:** 1024x1024, RGB
- **Pixel stats:** range 0–255, mean 59.3
- **Confirmed by:** v2 state.json

### Pixel comparison (both converted to grayscale)
- **Identical pixels:** NO
- **Max pixel difference:** 182
- **Mean pixel difference:** 48.45
- **Pearson correlation:** 0.907 (same subject, different rendering)

### How the confusion arose

1. **Mar 16:** A 512px NORMAL run loaded `Final cows/woodblock.png` (= woodblock2.png, MD5 c7ff...). This run produced a 512px mesh and wrote `run.log` to `Final cows/woodblock/normal/`.
2. **Mar 17:** A 1024px PROD run loaded `INKFORGE/woodblock.png` (different image, MD5 a08b...). This overwrote `Final cows/woodblock/normal/mesh.obj` with the 2.1M-face mesh but did NOT update the `run.log` in that directory.
3. The stale `run.log` (Mar 16, 512px) remained, making it appear the mesh was built from `Final cows/woodblock.png` when it was actually built from `INKFORGE/woodblock.png`.
4. `Final cows/woodblock.png` was subsequently deleted in commit `46bb206` (v001 session start), making provenance verification harder.
5. `run.jl` at the time of the PROD commit still pointed to `befuddled_cow_solver_input.jpg` — the PROD run used a different entry point or env var override.

### Impact on v001 physical OBJs

The v001 session's `gen_woodblock_physical.py` script read `Final cows/woodblock/normal/mesh.obj` — which is the 1024px PROD mesh built from **INKFORGE/woodblock.png**. Therefore:
- `Final cows/woodblock/24in_standard/physical_lens_24x24.obj` → from INKFORGE/woodblock.png
- `Final cows/woodblock/8in/physical_lens_8x8.obj` → from INKFORGE/woodblock.png

Both v1 physical OBJs are derived from a different source image than v2.

### Recommendation

Any v1-vs-v2 geometry comparison must account for this. Depth, curvature, and slope differences may be partially or entirely explained by input image differences rather than pipeline differences. A controlled comparison would require running v1 on woodblock2.png (or v2 on INKFORGE/woodblock.png) — same image through both pipelines.
