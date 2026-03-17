# Analysis Pipeline — Ready for Claude Chat Review
# Date: 2026-03-16
# Status: ALL ANALYSIS COMPLETE

---

## Images Ready for Upload

| File | What it shows | Size |
|------|--------------|------|
| inkbrush_normal_v2.png | inkbrush 16-pass σ=0.75 γ=0.70 (NEW defaults) | ~323KB |
| W_inkbrush_pipeline_diagnostic.png | Full pipeline breakdown: input → OBJ → accum → output | ~714KB |
| X_nikon_pipeline_diagnostic.png | Same diagnostic for nikon (shows banding) | ~672KB |
| T_sharpness_sweep_inkbrush.png | Top 5 param combos vs baseline (grid) | ~333KB |
| U_overlay_inkbrush.png | Input edges (cyan) blended with caustic at 5 alpha levels | ~285KB |
| V_cross_image_metrics.png | Bar charts: all 5 treatments compared | ~70KB |
| V2_cross_image_strip.png | Visual strip: input + caustic side by side for all 5 | ~294KB |

---

## What Each Image Answers

**inkbrush_normal_v2.png** — The new production default render.
16 passes, sigma=0.75, gamma=0.70, no post-blur, nearest interpolation.
Compare to inkbrush_normal.png (old baseline) — is this visually better?

**W_inkbrush_pipeline_diagnostic.png** — 3×4 diagnostic grid.
Row 1: input image / FFT spectrum / Sobel edges / histogram
Row 2: OBJ heightmap / gradient magnitude / edges+gradient overlay / OBJ FFT
Row 3: raw accumulator / accum FFT / final caustic / edges+caustic overlay
KEY PANEL: [2,3] overlay of Sobel edges on OBJ gradient. r=0.014 — very low.
This means the solver barely encoded the inkbrush edge structure.

**X_nikon_pipeline_diagnostic.png** — Same grid for nikon.
r(OBJ_gradient, edges)=0.171 — much better than inkbrush.
LOOK FOR: horizontal banding in the OBJ heightmap [2,1] and gradient [2,2].
If banding is visible there, it IS solver residuals (not a ray-trace artifact).

**T_sharpness_sweep_inkbrush.png** — Top 5 post-process combinations measured.
Baseline (σ=0.5, γ=0.5): sharp=0.088, contrast=1.80, black=53.8%
New default (σ=0.0, γ=0.70): sharp=0.087, contrast=2.17, black=54.4%
The new defaults WIN on contrast (+20%) and black coverage — confirmed by metrics.

**U_overlay_inkbrush.png** — Spatial correspondence check.
At alpha=0.5 (blend), do the BRIGHT caustic regions correspond to ink brush strokes?
Or do they appear in unexpected locations?

**V_cross_image_metrics.png + V2_cross_image_strip.png** — All 5 treatments ranked.
Nikon scores HIGHEST on caustic sharpness (0.130) despite the banding artifact.
Inkbrush scores 4th on sharpness but was selected for artistic quality.

---

## Sharpness Sweep Table (top 15)

| Rank | post_sigma | gamma | sharpness | contrast | black% | score |
|------|-----------|-------|-----------|----------|--------|-------|
|  1   | 0.25      | 0.70  | 0.0867   | 2.244    | 54.4%  | 0.900 |
|  2   | 0.00      | 0.70  | 0.0868   | 2.170    | 54.4%  | 0.880 |
|  3   | 0.25      | 0.65  | 0.0897   | 2.131    | 54.2%  | 0.872 |
|  4   | 0.25      | 0.60  | 0.0924   | 2.022    | 54.1%  | 0.849 |
|  5   | 0.00      | 0.65  | 0.0897   | 2.045    | 54.2%  | 0.849 |
|  6   | 0.00      | 0.60  | 0.0924   | 1.922    | 54.1%  | 0.822 |
|  7   | 0.25      | 0.50  | 0.0967   | 1.815    | 54.0%  | 0.817 |
|  8   | 0.50      | 0.70  | 0.0788   | 2.219    | 54.3%  | 0.811 |
| 10   | 0.00      | 0.50  | 0.0967   | 1.676    | 54.0%  | 0.779 |
| **BASELINE** | 0.50 | 0.50 | 0.0882 | 1.804 | 53.8% | — |
| **NEW DEF**  | 0.00 | 0.70 | 0.0868 | 2.170 | 54.4% | 0.880 |

Note: Mathematically, post_sigma=0.25 (very light blur) slightly beats post_sigma=0.0
on composite score at gamma=0.70 (rank 1 vs rank 2). Consider testing this in production.

---

## Pipeline Diagnostic Numbers

| Metric | inkbrush | nikon |
|--------|----------|-------|
| r(OBJ_gradient, edges) | 0.014 | **0.171** |
| r(raw_accum, edges)    | 0.159 | **0.233** |
| r(final, edges)        | 0.150 | **0.219** |
| Sharpness input        | 0.308 | 0.267 |
| Sharpness OBJ          | 1.226 | 1.116 |
| Sharpness accum        | 0.067 | **0.084** |
| Sharpness final        | 0.107 | **0.130** |

The low r(OBJ_gradient, edges)=0.014 for inkbrush means the solver encoded
brightness gradients, not edge structure. The inkbrush input image may have
too much smooth tonal content relative to sharp edges for the solver.

---

## Questions for Claude Chat

**Q1 — Nikon banding (W + X diagnostic):**
In X_nikon_pipeline_diagnostic.png, row 2 (OBJ panels): is horizontal banding
visible in the heightmap [2,1] and gradient [2,2]?
If yes: this confirms solver residuals. Fixing requires more SOR iterations.
If no: the banding in the render is a ray-trace or post-process artifact.

**Q2 — New defaults validation (inkbrush_normal_v2.png):**
Does the 16-pass σ=0.75 γ=0.70 render look better than the old baseline?
Is the darker background an improvement or does it look underexposed?

**Q3 — Overlay check (U_overlay_inkbrush.png):**
At the alpha=0.5 blend panel: do the bright caustic regions correspond to the
ink brush strokes in the input image? Or are they spatially shifted?

**Q4 — Cross-image ranking (V_cross_image_metrics.png):**
Nikon scores highest on every metric. Does the bar chart confirm nikon as the
intrinsically best input for caustics, independent of the banding defect?

**Q5 — Post_sigma=0.25 vs 0.0:**
The sharpness sweep shows post_sigma=0.25 + gamma=0.70 scores slightly higher
than 0.0 + 0.70 on the composite metric (0.900 vs 0.880). Worth testing this
tiny blur vs fully removing it? Or is the difference imperceptible?

---

## Write Answers To

`claude_chat_handoff4/ANALYSIS_FINDINGS.md`

Include:
  - Q1: banding visible in OBJ heightmap? yes/no
  - Q2: v2 render better/worse/same as baseline?
  - Q3: overlay correspondence good/partial/none?
  - Q4: nikon confirmed as best input for caustics?
  - Q5: post_sigma=0.25 worth testing?
  - Any other observations from the diagnostic figures
