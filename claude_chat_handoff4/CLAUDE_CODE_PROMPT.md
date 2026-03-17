# Claude Code Prompt — Pipeline Rebuild + Three-Speed Iteration
# Date: 2026-03-16
# From: Claude Chat (visual analysis complete)
# Priority: PARALLEL execution via subagents where possible

---

## READ FIRST

Read `/Users/admin/causticsEngineering/CLAUDE.md` and `~/.claude/CLAUDE.md`.
All hooks, autonomy rules, and confirmation formats are live.

---

## VISUAL DIAGNOSIS FROM CLAUDE CHAT

Claude Chat has seen the renders. Here is what was found:

### What v5 actually looks like (caustic_befuddled_v5.png)
The v5 output is NOT a caustic. It is a photographic emboss/relief map rendered
in amber. The entire lens area is filled with continuous amber tones showing full
fur texture, hair detail, chain links — essentially the source photograph rendered
as a normal map. Almost no black background is visible. This is the opposite of a
correct caustic (which should be bright concentrated lines on near-black).

### Root cause (confirmed)
The solver input `befuddled_cow_solver_input.jpg` is a continuous-gradient
photographic grayscale image. The SOR solver with a photographic input produces
a photographic emboss, not a caustic. The Gaussian blur preprocessing made the
problem WORSE — it spread the gradients further, causing the solver to distribute
energy even more uniformly across the lens surface.

For a caustic lens, the solver needs a NEAR-BINARY or HIGH-CONTRAST input where
bright = "concentrate light here" and dark = "no light here." A photograph fails
this requirement completely.

### The cow v1 contamination (your observation — confirmed)
The analysis panel upper-center shows "v3 baseline: f=0.2m, 512px, σ=1.5" — this
is the original cow render (Cow 1). It is embedded in the analysis figure as the
reference. This is correct for comparison purposes, but it means the analysis
script is explicitly pulling from the old cow run. This is NOT causing the visual
output to be wrong — the wrong INPUT IMAGE is causing the wrong output.

### Y-axis flip (confirmed)
The caustic render needs `np.flipud(accum)` not just `np.fliplr(accum)`.
Currently only horizontal flip is applied. The cow appears inverted vertically.
Fix in all simulate_*.py scripts.

### What Cow 2 needs to be
For v5 to produce a real caustic, the solver input must be one of:
  Option C (best): White silhouette of cow on pure black background
  Option B (good): Sobel edge map of the cow — dark background, bright edges only
  Option A (current, wrong): Photographic grayscale — produces emboss, not caustic

---

## STRATEGIC DIRECTION

Three parallel pipelines. Three input strategies. All running simultaneously.
Do not run them sequentially. Use subagents.

### Pipeline Speeds
  HYPER  = 128px input → ~33k faces  → Julia ~10s  → ray trace ~30s  → total ~1 min
  FAST   = 256px input → ~131k faces → Julia ~45s  → ray trace ~2min → total ~3 min
  NORMAL = 512px input → ~525k faces → Julia ~5min → ray trace ~8min → total ~13 min

### Input Strategies for Cow 2
  Option B = Sobel edge map (generate from befuddled_cow_solver_input.jpg in Python)
  Option C = White-filled silhouette on black (generate programmatically or near-binary threshold)

Production (1024px) only runs AFTER we confirm a promising result at 512px NORMAL.

---

## TASK 0 — Immediate Fixes (auto-accept, do these first)

### 0A — Fix Y-axis flip in ALL simulate_*.py scripts
Change:
  img = np.fliplr(accum.copy())
To:
  img = np.flipud(np.fliplr(accum.copy()))

Apply to: simulate_cow.py, simulate_befuddled_v5.py, simulate_caustic.py,
simulate_circle.py, and any new simulate_*.py files created in this session.
This is a visual correction only — does not affect physics, does not invalidate caches.

### 0B — Regenerate befuddled v5 render with flip fix
Delete befuddled_v5_accum.npy cache is NOT needed — just replot:
  python3 simulate_befuddled_v5.py
(Cache exists, will skip simulation, will replot with new flip. ~5 seconds.)
Save output as caustic_befuddled_v5_flipfix.png (do not overwrite v5 reference).

### 0C — Generate the two correct input images for Cow 2

Write `prepare_cow2_inputs.py` and run it:

  from PIL import Image, ImageFilter
  import numpy as np
  from scipy.ndimage import sobel, gaussian_filter
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt

  src = "examples/befuddled_cow_solver_input.jpg"
  img = np.array(Image.open(src).convert('L'), dtype=float) / 255.0

  # Option B: Sobel edge map
  sx = sobel(img, axis=0); sy = sobel(img, axis=1)
  edges = np.hypot(sx, sy)
  edges = edges / edges.max()
  # Threshold to keep only strong edges, set rest to black
  edges[edges < 0.15] = 0
  Image.fromarray((edges * 255).astype(np.uint8)).save(
      "examples/cow2_option_b_edges.png")

  # Option C: White silhouette on black via Otsu threshold
  from PIL import Image as PILImage
  import PIL.ImageOps
  pil = PILImage.open(src).convert('L')
  threshold = 128  # adjust if silhouette looks wrong
  binary = pil.point(lambda x: 255 if x > threshold else 0)
  binary.save("examples/cow2_option_c_silhouette.png")

  print("Wrote cow2_option_b_edges.png and cow2_option_c_silhouette.png")

After running, resize both to < 1MB and write to claude_chat_handoff4/:
  cow2_option_b_edges.png
  cow2_option_c_silhouette.png

Claude Chat needs to approve these before they go into the solver.
Write to READY_FOR_CLAUDE_CHAT.md: "Option B and C inputs generated — upload
to Claude Chat for visual approval before running solver."

---

## TASK 1 — Build Three-Speed Pipeline Scripts

Use subagents to build all three pipelines in parallel.

### Subagent A — HYPER pipeline (128px)
Files to create:
  run_hyper.jl          — resize to 128px, calls engineer_caustics()
  simulate_hyper.py     — auto-sigma, separate caches (hyper_accum.npy)
  run_pipeline_hyper.sh — full pipeline with backup/restore, timing

### Subagent B — FAST pipeline (256px)
Files to create:
  run_fast.jl           — resize to 256px, calls engineer_caustics()
  simulate_fast.py      — auto-sigma, separate caches (fast_accum.npy)
  run_pipeline_fast.sh  — full pipeline with backup/restore, timing

### Subagent C — NORMAL pipeline (512px)
Files to create:
  run_normal.jl         — resize to 512px, calls engineer_caustics()
  simulate_normal.py    — sigma=1.5 (512px baseline, confirmed working), separate caches
  run_pipeline_normal.sh — full pipeline with backup/restore, timing

### Common spec for all three:

run_*.jl pattern:
  using Pkg; Pkg.activate(".")
  using Images, CausticsEngineering
  TARGET_IMAGE = get(ENV, "COW2_INPUT", "./examples/befuddled_cow_solver_input.jpg")
  image = Images.load(TARGET_IMAGE)
  image = imresize(image, (RES, RES))   # RES = 128, 256, or 512
  engineer_caustics(image)

  The ENV var COW2_INPUT allows swapping input without editing the file:
    COW2_INPUT=./examples/cow2_option_c_silhouette.png julia run_fast.jl

simulate_*.py pattern:
  OBJ_PATH    = BASE / "original_image_{speed}.obj"   # hyper/fast/normal
  ACCUM_PATH  = BASE / "{speed}_accum.npy"
  META_PATH   = BASE / "{speed}_meta.npy"
  OUTPUT_PATH = BASE / "caustic_{speed}.png"
  IMAGE_RES   = 512    # output resolution (same for all speeds)

  # Auto-sigma from face count
  face_count = len(faces)
  SPLAT_SIGMA  = 1.5 * (525000 / face_count) ** 0.5
  SPLAT_RADIUS = max(2, int(round(SPLAT_SIGMA * 1.5)))
  print(f"[{speed}] sigma={SPLAT_SIGMA:.3f} radius={SPLAT_RADIUS} faces={face_count:,}")

  # Apply BOTH flips
  img = np.flipud(np.fliplr(accum.copy()))

  N_PASSES = 4, FOCAL_DIST = 0.75, IOR = 1.49

run_pipeline_*.sh pattern:
  #!/bin/bash
  set -e
  SPEED=hyper   # or fast / normal
  RES=128       # or 256 / 512
  INPUT=${COW2_INPUT:-./examples/befuddled_cow_solver_input.jpg}

  echo "=== ${SPEED} PIPELINE | ${RES}px | input: $INPUT ==="
  cp examples/original_image.obj examples/original_image_PROD_BACKUP.obj

  T1=$(date +%s)
  COW2_INPUT="$INPUT" julia run_${SPEED}.jl
  T2=$(date +%s)
  mv examples/original_image.obj examples/original_image_${SPEED}.obj
  cp examples/original_image_PROD_BACKUP.obj examples/original_image.obj

  T3=$(date +%s)
  python3 simulate_${SPEED}.py
  T4=$(date +%s)

  echo "Julia: $((T2-T1))s | Ray trace: $((T4-T3))s | Total: $((T4-T1))s"
  echo "Output: examples/caustic_${SPEED}.png"

### IMPORTANT: Do NOT run any of the pipeline scripts autonomously.
Build them, commit them, report them as ready. The ⚠ SUPER CRITICAL confirm
is required before any Julia run because it overwrites original_image.obj
(even with backup/restore, this is a destructive operation on production).

---

## TASK 2 — Rebuild Option: Fresh Pipeline Subagent

In parallel with Task 1, spawn a subagent to evaluate whether a clean-slate
rebuild is worthwhile.

### Subagent D — Pipeline Rebuild Assessment

Subagent D should answer these questions (text analysis only, no file writes):

1. What are the accumulated patches in simulate_befuddled_v5.py vs simulate_cow.py?
   List every parameter that differs. Are any of these differences suspicious?

2. What is the state of original_image.obj? (run verify_obj.py and report)
   Is it definitely the befuddled 1024px mesh or could it be a cow mesh?

3. Does the current engineer_caustics() pipeline have any state that persists
   between runs that could contaminate a new run? (check for global variables,
   module-level state, or anything that wouldn't reset if julia run.jl is called twice)

4. Is there any reason NOT to start from simulate_cow.py as the clean template
   for a new simulate_cow2.py that only uses Option B or C input?

5. If building from scratch: what is the minimum viable simulate script that:
   - reads original_image.obj
   - applies correct sigma for its face count
   - applies both flips
   - outputs a named file
   - has NO legacy parameters from previous versions

Subagent D returns: rebuild recommendation (yes/no), confidence, and if yes —
the exact minimal script content for a new simulate_cow2_fresh.py.

Main Claude synthesizes D's findings. If D recommends rebuild:
  Write simulate_cow2_fresh.py based on D's spec.
  This script is a candidate to replace simulate_befuddled_v5.py for new runs.

---

## TASK 3 — Update CLAUDE.md

After all tasks complete, update CLAUDE.md to reflect:

1. Rename convention: befuddled cow = Cow 2 throughout
2. Add to Target Image Strategy section:
   - Option B and C input files are in examples/cow2_option_b_edges.png
     and examples/cow2_option_c_silhouette.png
   - CONFIRMED: photographic input (Option A / befuddled_cow_solver_input.jpg)
     produces a photographic emboss, NOT a caustic — do not use as solver input
3. Add Y-flip note to Forward Ray Trace section:
   - Correct orientation requires BOTH np.flipud AND np.fliplr
   - np.fliplr alone was confirmed wrong (y-axis inverted in all renders before this fix)
4. Add three-speed pipeline section referencing run_hyper/fast/normal.jl
5. Rename: "Active Research: Input Image Strategy" → "Cow 2 Input Strategy"

---

## TASK 4 — Visual Handoff Package (parallel with Tasks 1–3)

Spawn Subagent E to build the handoff images while main Claude handles Tasks 1–3.

Subagent E writes and runs `prepare_visual_handoff.py`:
  - Resize all existing renders to < 700px longest edge → claude_chat_handoff4/
  - Include: A_ref_cow_v3, B_v1, C_v4, D_v5, D2_v5_flipfix (once 0B runs)
  - Include: E_loss_it1, F_loss_it3, G_loss_it6
  - Include: H_analysis_v5, I_solver_input, J_original_source
  - Include: K_option_b_edges, L_option_c_silhouette (once 0C runs)
  - Build comparison_grid.png (2×6 panels, JPEG quality=85, < 1MB)
  - Verify all files < 900KB

Subagent E also writes `claude_chat_handoff4/VISUAL_ANALYSIS_REQUEST.md`:

  Section 1 — Context for Claude Chat:
    - v5 confirmed: photographic emboss, not caustic (Claude Chat saw this)
    - Y-flip fixed in v5_flipfix
    - Two new solver inputs generated (Option B edges, Option C silhouette)

  Section 2 — Visual approval task for Claude Chat:
    Claude Chat must look at K_option_b_edges.png and L_option_c_silhouette.png
    and answer:

    Q1: Does Option B (edge map) look like it has clear bright edges on dark background?
        Is it clean or noisy? Would it produce a recognizable caustic? [describe]

    Q2: Does Option C (silhouette) look like a clean white cow shape on black?
        Is the silhouette complete (no holes in the body), or are there artifacts?
        Would it produce a clean glowing cow shape? [describe]

    Q3: Does the flipfix render (D2) look correctly oriented now?
        Is the cow right-side up? [yes/no]

    Q4 (optional): Does either Option B or C look CLEARLY superior as a solver input?
        Or should we run both? [both / B / C]

    Write answers to: claude_chat_handoff4/CLAUDE_CHAT_FINDINGS.md
    Claude Code reads it and picks which input(s) to run.

---

## EXECUTION ORDER (PARALLEL)

Main Claude orchestrates. All subagents fire simultaneously after Task 0.

  SEQUENCE:
  1. Task 0A — fix Y-flip in all scripts (main Claude, 5 min)
  2. Task 0B — replot v5 with flip fix (main Claude, auto-accept)
  3. Task 0C — generate Option B and C inputs (main Claude, auto-accept)

  PARALLEL AFTER TASK 0:
  4a. Subagent A — build HYPER pipeline scripts
  4b. Subagent B — build FAST pipeline scripts
  4c. Subagent C — build NORMAL pipeline scripts
  4d. Subagent D — pipeline rebuild assessment
  4e. Subagent E — visual handoff package + VISUAL_ANALYSIS_REQUEST.md

  AFTER ALL SUBAGENTS COMPLETE:
  5. Main Claude synthesizes D's rebuild recommendation
  6. If rebuild: write simulate_cow2_fresh.py
  7. Task 3: update CLAUDE.md
  8. git add -A && git commit -m "three-speed pipelines + cow2 inputs + y-flip fix"
  9. Report to user:
     - What was built
     - Diagnostic summary (especially: what is original_image.obj right now?)
     - Paste prompt for Claude Chat (visual approval of Option B and C inputs)
     - Which pipeline to run first and with which input

---

## HARD CONSTRAINTS

  NEVER run autonomously:
    - run_pipeline_hyper.sh / fast.sh / normal.sh (build only)
    - Any julia run directly

  AUTO-ACCEPT (no confirmation):
    - All script writes and edits
    - Running Task 0B (simulate_befuddled_v5.py replot)
    - Running prepare_visual_handoff.py
    - Running prepare_cow2_inputs.py
    - Running verify_obj.py
    - Git commit

  CONFIRM REQUIRED (⚠ SUPER CRITICAL format):
    - Any Julia solver run
    - Editing create_mesh.jl
