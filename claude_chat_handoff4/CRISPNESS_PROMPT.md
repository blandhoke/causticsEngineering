# Claude Code Prompt — Crispness Research + Sigma Sweep
# Date: 2026-03-16
# From: Claude Chat
# Goal: Identify and fix the blur sources in simulate_batch.py, run a sigma sweep
#       on existing normal meshes (no new Julia runs needed), and package all
#       results for Claude Chat visual review.

---

## READ FIRST

Read `/Users/admin/causticsEngineering/CLAUDE.md` and `~/.claude/CLAUDE.md`.

---

## DIAGNOSIS FROM CLAUDE CHAT

Three blur sources are stacked in the current pipeline:

  BLUR 1 — Gaussian splat kernel: sigma=1.5, radius=2 (5×5 kernel)
    At 512px output resolution on a ~525k face mesh, sigma=1.5 is the
    formula-correct value BUT it is tuned for energy conservation, not crispness.
    Each photon hit bleeds into a 5×5 neighborhood. For fine caustic lines
    (ink strokes, woodblock edges) this smears detail significantly.

  BLUR 2 — Post-process gaussian_filter(sigma=0.5) applied to the rendered image
    This is an ADDITIONAL blur applied AFTER the splat, inherited from the
    original simulate_cow.py. It was originally added to suppress mesh-grid
    artifacts in early renders. With proper Gaussian splatting it may no
    longer be needed and is simply degrading sharpness.

  BLUR 3 — matplotlib interpolation='bilinear' in imshow()
    A third, lighter blur applied at the display stage. Can be eliminated.

The research question: what is the minimum blur needed to avoid
visible mesh-grid artifacts while maximizing caustic crispness?

---

## IMPORTANT: NO NEW JULIA RUNS NEEDED

The existing normal meshes in Final cows/<slug>/normal/mesh.obj are valid.
The accum.npy caches can be DELETED to force re-simulation with new sigma,
or we can REPLOT from cache with different post-processing.

Strategy:
  - Sigma sweep: delete cache, re-simulate with new sigma values (~7s each)
  - Post-process sweep: keep cache, replot with different gaussian_filter values
    (instant — just re-renders the PNG from existing accum.npy)
  - Both sweeps run on inkbrush/normal and nikon/normal (top 2 treatments)

---

## TASK 1 — Deploy Research Subagents (parallel)

Spawn 4 subagents simultaneously. Each researches a different approach to
caustic sharpness. Each returns: method, expected result, recommended parameters,
confidence score. Main Claude synthesizes and selects experiments to run.

### Subagent A — Splat Kernel Research
Research question: what sigma minimizes mesh-grid artifact while maximizing
edge sharpness in forward ray-traced caustic simulations?

Investigate:
  1. What does sigma=0 (single-pixel accumulation) look like — pure grid artifact?
  2. At what sigma does the grid artifact become invisible vs sigma=1.5?
  3. Is there a non-Gaussian kernel (tent, box, Mitchell-Netravali) that gives
     sharper edges with less energy spread than Gaussian?
  4. Does increasing N_PASSES (from 4 to 8 or 16) allow a smaller sigma while
     maintaining smooth coverage? (more samples = less reliance on splat width)
  5. What sigma values are used in published caustic papers (Schwartzburg 2014,
     Papas 2011) for similar mesh densities?

Return: recommended sigma range to test, optimal kernel type, N_PASSES tradeoff.

### Subagent B — Post-Process Research
Research question: what post-processing maximizes perceived sharpness while
suppressing noise in a sparse photon accumulation map?

Investigate:
  1. Is scipy gaussian_filter(sigma=0.5) helping or hurting at this mesh density?
  2. What does unsharp masking do to a caustic render — does it enhance edges
     without amplifying grid artifacts?
  3. Bilateral filter — preserves edges better than Gaussian, could suppress
     grid artifact while keeping caustic lines sharp. Viable?
  4. Adaptive histogram equalization (CLAHE) — enhances local contrast without
     blurring. Effect on caustic visibility?
  5. Gamma correction: current pipeline uses sqrt(img) (gamma≈2). Is a different
     gamma (e.g. 0.4, 0.6) better for caustic contrast?

Return: recommended post-process pipeline, specific parameters, before/after
description of expected effect.

### Subagent C — Resolution / Sampling Research
Research question: does increasing N_PASSES reduce the need for Gaussian
splatting, and what is the crispness vs time tradeoff?

Investigate:
  1. At N_PASSES=8 with sigma=0.75 vs N_PASSES=4 with sigma=1.5 — same total
     samples, different distribution. Which is crisper?
  2. At N_PASSES=16 with sigma=0.5 — is the grid artifact suppressed?
  3. What is the theoretical minimum sigma for a ~525k face mesh at 512px output
     such that the average inter-face gap is covered?
     (Face density: 525k faces / (512×512 px) ≈ 2.0 faces/px at IMAGE_RES=512.
      If faces average 1px², sigma=0.5 might be sufficient with enough passes.)
  4. Is IMAGE_RES=1024 output (upsampled from 512px mesh) worth trying?
     More output pixels = each caustic line occupies more pixels = appears sharper.

Return: recommended N_PASSES + sigma combinations, expected time per run.

### Subagent D — Colormap / Rendering Research
Research question: does the sunlight colormap obscure sharpness, and are there
rendering improvements that make caustics look more physically real?

Investigate:
  1. Does the amber colormap compress contrast in the bright regions where
     caustic lines are? A higher-contrast colormap might make lines look sharper
     even with the same underlying data.
  2. Does `interpolation='bilinear'` in matplotlib imshow add visible blur?
     Test: 'nearest' or 'none' for pixel-accurate output.
  3. Is the sqrt gamma (power=0.5) the right choice? Too much gamma lift can
     make the background amber rather than black, which reduces apparent contrast
     of the caustic lines. Try power=0.3 or 0.4.
  4. HDR tone mapping: applying a simple Reinhard or filmic tone map to the
     raw accumulator before gamma — could reveal more dynamic range in bright
     caustic lines vs dark background.

Return: recommended colormap/gamma/interpolation settings.

---

## TASK 2 — Implement Experiments Based on Subagent Findings

After all 4 subagents report, main Claude selects the most promising parameter
combinations and runs them. Target: 8-12 experiments total.

### Mandatory sweep — run regardless of subagent findings:
These are the highest-confidence improvements based on Claude Chat's analysis:

  Experiment set A — Sigma sweep (re-simulate, ~7s each):
    Delete accum.npy for inkbrush/normal only (not the other 4 — preserve them)
    Run simulate_batch.py with:
      sigma_override=0.25  radius=1   (ultra-crisp, likely noisy)
      sigma_override=0.50  radius=1   (very crisp)
      sigma_override=0.75  radius=1   (crisp)
      sigma_override=1.00  radius=2   (moderate)
      sigma_override=1.50  radius=2   (current baseline)
    Save each to: Final cows/inkbrush/sigma_sweep/sigma_XXX/caustic.png

  Experiment set B — Post-process sweep (replot from cache, instant):
    Replot inkbrush/normal accum.npy with:
      no_postblur + nearest interpolation + sqrt gamma  (cleanest possible)
      no_postblur + bilinear + sqrt gamma               (current minus postblur)
      gaussian_filter(0.3) + nearest + sqrt gamma
      gaussian_filter(0.5) + nearest + sqrt gamma       (current minus bilinear)
      gaussian_filter(0.5) + bilinear + sqrt gamma      (current baseline)
      unsharp_mask(radius=1, amount=1.5) + nearest
    Save each to: Final cows/inkbrush/postprocess_sweep/<name>/caustic.png

  Experiment set C — Passes sweep (re-simulate):
    N_PASSES=8  sigma=0.75  (double passes, half sigma)
    N_PASSES=16 sigma=0.50  (quad passes, third sigma)
    Save to: Final cows/inkbrush/passes_sweep/<name>/caustic.png

### Add --sigma and --post-sigma CLI args to simulate_batch.py:
  --sigma       override auto-sigma (float, default: auto from face count)
  --post-sigma  gaussian_filter sigma applied after render (float, default: 0.5,
                set to 0.0 to disable)
  --interp      matplotlib interpolation ('bilinear' or 'nearest', default: 'nearest')
  --gamma       power for gamma correction (float, default: 0.5)
  --passes      already exists, now also used in sweep

This makes simulate_batch.py the universal tool for all experiments.
All sweeps run by calling simulate_batch.py with different CLI args.
Cache is only regenerated when --sigma or --passes changes (physics changes).
Post-process params never require cache regeneration.

---

## TASK 3 — Build Comparison Packages for Claude Chat

After all experiments complete, build visual packages.

### 3A — Sigma sweep contact sheet
  Final cows/inkbrush/sigma_sweep/sigma_comparison.jpg
  5 panels side by side: sigma 0.25 / 0.50 / 0.75 / 1.00 / 1.50
  Label each: sigma value + "grid visible?" annotation if applicable
  Save < 900KB version to claude_chat_handoff4/O_sigma_sweep.jpg

### 3B — Post-process sweep contact sheet
  Final cows/inkbrush/postprocess_sweep/postprocess_comparison.jpg
  6 panels: all post-process variants
  Save < 900KB to claude_chat_handoff4/P_postprocess_sweep.jpg

### 3C — Passes sweep contact sheet
  Final cows/inkbrush/passes_sweep/passes_comparison.jpg
  3 panels: 4-pass baseline / 8-pass / 16-pass
  Save < 900KB to claude_chat_handoff4/Q_passes_sweep.jpg

### 3D — Best-of comparison
After all sweeps, identify the single best result from each sweep category.
Build a 3-panel "before vs after" sheet:
  Panel 1: current baseline (sigma=1.5, post=0.5, bilinear, 4-pass)
  Panel 2: best from sigma sweep
  Panel 3: best from combined (best sigma + best post-process)
  Save to claude_chat_handoff4/R_best_vs_baseline.jpg

### 3E — If time permits: run best params on nikon/normal
Once the best parameter set is identified from the inkbrush sweeps,
run the same params on nikon/normal (the second-ranked treatment).
Save to claude_chat_handoff4/S_nikon_best_params.jpg

---

## TASK 4 — Write Subagent Research Summary

Write Final cows/CRISPNESS_RESEARCH.md with:
  - Summary of each subagent's findings
  - Parameters tested and why
  - Which experiments showed the most improvement
  - Recommended default parameters for future runs
  - Any surprising findings

Write claude_chat_handoff4/CRISPNESS_READY_FOR_REVIEW.md:
  - List of all images in handoff4/ for this sweep (O, P, Q, R, S)
  - Key finding in one sentence per sweep
  - Question for Claude Chat: "Which panel in O_sigma_sweep looks sharpest
    without visible grid artifact?"
  - Paste prompt for Claude Chat to use

---

## EXECUTION ORDER

  1. Spawn Subagents A, B, C, D simultaneously (parallel research)
  2. Main Claude waits for all 4 to report
  3. Add --sigma, --post-sigma, --interp, --gamma, --passes CLI args to simulate_batch.py
  4. Run sigma sweep experiments (inkbrush/normal only, delete its accum.npy first)
  5. Run post-process sweep (replot from cache — no simulation needed)
  6. Run passes sweep (re-simulate with new N_PASSES values)
  7. Build all contact sheets (Tasks 3A-3D)
  8. If sweeps done and time permits, run best params on nikon (Task 3E)
  9. Write CRISPNESS_RESEARCH.md and CRISPNESS_READY_FOR_REVIEW.md
  10. git commit "crispness research: sigma/postprocess/passes sweep complete"

---

## HARD CONSTRAINTS

  NEVER:
    - Delete accum.npy for any image EXCEPT inkbrush/normal (that's the test bed)
    - Modify the 5 original input PNGs in Final cows/
    - Run any Julia solver (all work is ray-trace only — fast, no confirms needed)

  AUTO-ACCEPT EVERYTHING:
    - All script edits (simulate_batch.py CLI args)
    - All simulation runs (no Julia, ray trace only, ~7-60s each)
    - All directory creation
    - All contact sheet builds
    - Git commit

  No confirmation needed for anything in this prompt.
