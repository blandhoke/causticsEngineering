# Claude Code Prompt — Caustic Analysis Pipeline
# Date: 2026-03-16
# From: Claude Chat
# Goal: Build a diagnostic tool that makes caustic quality measurable and
#       comparable, identifies exactly which pipeline stage is destroying
#       sharpness, and produces output Claude Chat can read at < 1MB.

---

## READ FIRST

Read `/Users/admin/causticsEngineering/CLAUDE.md` and `~/.claude/CLAUDE.md`.
No Julia runs. No confirmation needed for anything in this prompt.

---

## THE CORE QUESTION

The renders look blurry. Before tuning any parameters, we need to know:
  WHICH STAGE is losing sharpness?

  Stage 1 — Input image itself: is it high-contrast enough for the solver?
  Stage 2 — Julia solver output (OBJ): did the mesh actually encode the image?
             (We can visualize the OBJ surface as a heightmap — if the
              heightmap looks like the input, the solver worked.)
  Stage 3 — Splat accumulator (accum.npy): before any post-processing,
             what does the raw photon map look like?
  Stage 4 — Post-processing: does gaussian_filter + gamma + colormap
             add or remove perceptible detail?
  Stage 5 — Output PNG: final result

If Stage 2 (OBJ heightmap) looks sharp but Stage 3 (raw accum) looks blurry,
the problem is the splat sigma.
If Stage 2 already looks soft, the problem is the solver or the input.
If Stage 3 looks sharp but Stage 4 looks blurry, the problem is post-processing.

---

## TASK 1 — Write analyze_pipeline.py

A diagnostic script that takes ONE image slug and produces a multi-panel
analysis figure showing every stage of the pipeline.

Usage:
  python3 analyze_pipeline.py --slug inkbrush --speed normal

Output:
  Final cows/<slug>/analysis/pipeline_diagnostic.png
  Final cows/<slug>/analysis/pipeline_diagnostic_small.jpg  ← < 900KB for Claude Chat

### Panel layout (3 rows × 4 cols):

ROW 1 — Source material
  [1,1] Input image (grayscale, normalized, full detail)
        Label: filename, size, nonzero%, min/max/mean/std
  [1,2] Input image — frequency spectrum (2D FFT magnitude, log scale)
        Shows: how much high-frequency detail exists in the input
        Annotation: "high freq energy = potential for sharp caustic"
  [1,3] Input image — Sobel edge magnitude
        Shows: where the edges are that the solver should encode
  [1,4] Input histogram with contrast metrics
        Show: if the image is truly high-contrast or has mid-gray content

ROW 2 — Solver output (OBJ as heightmap)
  [2,1] OBJ heightmap — Z values of top-surface vertices rendered as image
        This is the actual surface the solver produced.
        Brighter = higher dome, darker = lower. Reconstructed by binning
        vertex Z values back onto a grid matching the input resolution.
        Label: face count, dome height, XY span, sigma used
  [2,2] OBJ heightmap — gradient magnitude (dZ/dX, dZ/dY)
        Shows: where the steep surface slopes are. These are where light
        concentrates. Should spatially match the edges in [1,3].
  [2,3] Overlay: Sobel edges of input (cyan) over OBJ gradient magnitude
        This is the KEY diagnostic — if edges align with gradients, the
        solver correctly encoded the input. If misaligned, the solver failed
        or the input was wrong.
        Show Pearson r(gradient, edges) as annotation.
  [2,4] OBJ heightmap — frequency spectrum
        How much high-frequency detail made it into the mesh surface?
        Compare directly to [1,2].

ROW 3 — Ray trace stages
  [3,1] Raw accumulator (accum.npy) — NO post-processing
        Load accum.npy directly. Apply ONLY sqrt gamma and fliplr.
        No gaussian_filter. No colormap — show as grayscale.
        Label: raw min/max/mean, dynamic range
  [3,2] Raw accumulator — frequency spectrum
        How much high-freq detail survived the ray trace + splat?
  [3,3] Current rendered output (caustic.png as-is)
        For direct visual comparison with raw accum.
  [3,4] Overlay: Sobel edges of INPUT (cyan) on raw accum (amber)
        Does the raw accumulator spatially match the input edges?
        Annotation: Pearson r(accum, input_edges), Pearson r(accum, input_brightness)

### Key metrics to print on the figure:
  - r(OBJ_gradient, input_edges):  how well solver encoded the image
  - r(raw_accum, input_edges):     how well ray trace captured solver intent
  - r(final_output, input_edges):  end-to-end fidelity
  - Sharpness score: mean gradient magnitude of each stage
    (higher = sharper; tracks sharpness loss through pipeline)
  - Dynamic range at each stage: (p99 - p1) / mean
    (higher = more contrast; tracks contrast compression through pipeline)

### Frequency spectrum method:
  import numpy as np
  fft = np.fft.fftshift(np.fft.fft2(img))
  magnitude = np.log1p(np.abs(fft))
  # Normalize and display — bright center = low freq, bright edges = high freq
  # Quantify: ratio of energy in outer 25% of spectrum vs total
  h, w = magnitude.shape
  mask = np.zeros_like(magnitude, dtype=bool)
  cx, cy = w//2, h//2
  r_inner = min(h, w) // 4
  Y, X = np.ogrid[:h, :w]
  mask[(X-cx)**2 + (Y-cy)**2 > r_inner**2] = True
  high_freq_ratio = magnitude[mask].sum() / magnitude.sum()
  # Report as "high-freq energy: X.X%" — higher = more detail = sharper

### OBJ heightmap reconstruction:
  Parse mesh.obj. For top-surface vertices only, bin Z values onto a
  (512×512) grid by X,Y position (normalize X,Y to grid coords, use
  numpy histogram2d for mean Z per cell). Apply fliplr to match
  caustic orientation. Normalize to [0,1].
  This is a direct visualization of the physical lens surface.

---

## TASK 2 — Write sharpness_sweep.py

Re-render the existing accum.npy cache with different post-processing
parameters and measure sharpness at each step. No re-simulation needed.

For a given slug/speed, sweep:
  sigma:     [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]
  gamma:     [0.3, 0.4, 0.5, 0.6]  (sqrt = 0.5, current)
  interp:    ['nearest', 'bilinear']

For each combination, compute:
  - Sharpness score: mean(|gradient(img)|)  — higher = sharper
  - Contrast score: (p99 - p1) / mean       — higher = more dynamic range
  - Black coverage: fraction of pixels < 0.05  — higher = more black background
    (important: a good caustic has lots of black)

Output a ranked table: top 10 parameter combinations by sharpness score.
Also generate PNGs for the top 5 combinations and the current baseline.

Save results to:
  Final cows/<slug>/analysis/sharpness_sweep.md   (ranked table)
  Final cows/<slug>/analysis/sharpness_sweep_grid.png  (top 5 + baseline)
  claude_chat_handoff4/T_sharpness_sweep_inkbrush.jpg  (< 900KB)

Usage:
  python3 sharpness_sweep.py --slug inkbrush --speed normal

---

## TASK 3 — Write overlay_compare.py

Overlay the source input image with the caustic output at multiple blend levels
so spatial correspondence (or lack of it) is immediately visible.

For each blend alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
  - Blend: alpha * caustic + (1-alpha) * input_edges_colorized
  - Input edges in cyan, caustic in amber
  - At alpha=0.0: pure edge map of input
  - At alpha=1.0: pure caustic
  - At alpha=0.5: both visible simultaneously

Also generate:
  - Difference image: caustic - input_edges (normalized)
    Shows where caustic has extra light (red) vs missing light (blue)
  - Spatial correlation map: local Pearson r in 32×32 sliding window
    Shows WHICH REGIONS of the image are well-encoded vs poorly-encoded

Save to:
  Final cows/<slug>/analysis/overlay_compare.png
  claude_chat_handoff4/U_overlay_inkbrush.jpg  (< 900KB)

Usage:
  python3 overlay_compare.py --slug inkbrush --speed normal

---

## TASK 4 — Write cross_image_compare.py

Compare all 5 Final Cows normal renders on the same metrics side by side.
This answers: "which treatment is intrinsically best-suited to caustic encoding?"

For each of the 5 images:
  - Load input image and normal/caustic.png
  - Compute: sharpness score, contrast score, black coverage,
    r(caustic, input_edges), r(caustic, input_brightness)
  - Also compute input image quality metrics:
    input_high_freq_ratio, input_contrast, input_edge_density

Output a ranked comparison table + bar chart:
  Final cows/cross_image_metrics.md
  Final cows/cross_image_metrics.png
  claude_chat_handoff4/V_cross_image_metrics.jpg  (< 900KB)

This will show definitively whether inkbrush/nikon are better because
of the artistic treatment OR in spite of it.

---

## TASK 5 — Run Everything on inkbrush/normal First

After all scripts are written:

1. python3 analyze_pipeline.py --slug inkbrush --speed normal
2. python3 sharpness_sweep.py --slug inkbrush --speed normal
3. python3 overlay_compare.py --slug inkbrush --speed normal
4. python3 cross_image_compare.py   (all 5 images)

All outputs go to Final cows/inkbrush/analysis/ and claude_chat_handoff4/.

---

## TASK 6 — Write claude_chat_handoff4/ANALYSIS_READY.md

Tell Claude Chat:
  - What each output image shows
  - What question each one answers
  - Specific things to look for in each panel
  - The ranked sharpness parameter table (text — Claude Chat can read md files)

Include the sharpness_sweep.md table directly in ANALYSIS_READY.md so
Claude Chat can read the numbers without needing to see an image.

Key question for Claude Chat after reviewing T, U, V:
  1. In T_sharpness_sweep: which panel looks most like a physical caustic
     under sunlight? (not just "sharp" — physically plausible)
  2. In U_overlay: at alpha=0.5, do the caustic bright regions spatially
     correspond to the ink brush strokes in the input?
  3. In V_cross_image_metrics: does the bar chart confirm inkbrush as
     the best treatment, or does a different image score better on metrics?

---

## EXECUTION ORDER

All auto-accept, no confirmation needed:

  1. Write analyze_pipeline.py
  2. Write sharpness_sweep.py
  3. Write overlay_compare.py
  4. Write cross_image_compare.py
  5. Run all four scripts on inkbrush/normal
  6. Write ANALYSIS_READY.md
  7. git commit "caustic analysis pipeline: pipeline diagnostic + sharpness sweep"
  8. Report: paste prompt for Claude Chat + key numeric findings

## HARD CONSTRAINTS

  NEVER modify Final cows/ input images or any accum.npy cache files.
  These scripts are READ-ONLY on existing data. They only write to
  Final cows/<slug>/analysis/ and claude_chat_handoff4/.
