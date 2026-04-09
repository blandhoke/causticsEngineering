# Claude Code Prompt — Apply Crispness Findings + Resize Tool + Analysis Pipeline
# Date: 2026-03-16
# From: Claude Chat (independent analysis complete)
# Source: CRISPNESS_SELECTION.md — read it first for full reasoning

---

## READ FIRST

Read `/Users/admin/causticsEngineering/CLAUDE.md` and `~/.claude/CLAUDE.md`.
Read `/Users/admin/causticsEngineering/claude_chat_handoff4/CRISPNESS_SELECTION.md`
for Claude Chat's independent visual analysis and reasoning behind every decision.
No Julia runs. No confirmation needed for anything unless flagged explicitly.

---

## IMPORTANT CONTEXT: TWO DISAGREEMENTS WITH CLAUDE CODE'S PRIOR CONCLUSIONS

Claude Chat reviewed all 6 images independently and reached different conclusions
on two key parameters. The reasoning is in CRISPNESS_SELECTION.md. Implement
Claude Chat's selections, not Claude Code's prior recommendations:

  sigma:  USE 0.75  (not 0.50 — micro-noise at production scale)
  passes: USE 16    (not 8 — 16-pass is physically correct, darker background
                     is correct behavior, not a defect)
  gamma:  USE 0.70  (not 0.65 — better caustic contrast, validate at 1024px)
  post-sigma: 0.0   (agreed — remove gaussian_filter)
  interp: nearest   (agreed)

---

## TASK 1 — Write cc_resize.py (permanent Claude Chat image prep tool)

Save to: /Users/admin/causticsEngineering/cc_resize.py

Rules that must be followed in this script:
  - ALWAYS save as PNG. Never JPEG. JPEG introduces DCT artifacts on caustics.
  - Max dimension: 900px (caustic PNGs at 900px = 200-500KB, always under 1MB MCP limit)
  - Use LANCZOS resampling
  - Print filename, output dimensions, and file size in KB for each file
  - Warn if any output exceeds 900KB

Modes:
  # Single file with explicit output path
  python3 cc_resize.py path/to/caustic.png --out handoff4/name.png

  # Multiple files, auto-named, to a directory
  python3 cc_resize.py file1.png file2.png --out handoff4/ --prefix tag_

  # All caustic.png files recursively under a directory
  python3 cc_resize.py --dir "Final cows/inkbrush/" --out handoff4/ --prefix inkbrush_

  # Slug + speed shorthand (grabs Final cows/<slug>/<speed>/caustic.png)
  python3 cc_resize.py --slug inkbrush --speed normal --out handoff4/

After any pipeline run, cc_resize.py should be called automatically.
Add this call to the end of run_cow_pipeline.sh so every run auto-deposits
a Claude Chat-readable PNG in claude_chat_handoff4/.

---

## TASK 2 — Update simulate_batch.py with new defaults and parameters

Add/update these CLI arguments and their defaults:

  --sigma      float  default=AUTO  (auto from face count formula if not set)
  --passes     int    default=16    (was 4 — Claude Chat confirmed 16-pass winner)
  --post-sigma float  default=0.0   (was 0.5 — remove gaussian_filter by default)
  --interp     str    default='nearest'  (was 'bilinear')
  --gamma      float  default=0.70  (was 0.5 — new validated default)
  --unsharp    float  default=0.0   (new — if > 0, apply unsharp mask with this amount)

When --sigma is not set: use auto formula (1.5 * sqrt(525000 / face_count)).
When --sigma IS set: use that value directly, skip auto formula.

Print a clear parameter summary at the start of every run:
  [label] Parameters: sigma=X.XX (auto/manual) passes=N gamma=X.XX
          post-sigma=X.XX interp=nearest unsharp=X.XX

Update the PostToolUse focal sync hook — after any write to simulate_batch.py,
verify that FOCAL_DIST still matches focalLength in create_mesh.jl.

---

## TASK 3 — Validation run with new defaults

After updating simulate_batch.py, run a validation on inkbrush/normal
using the new defaults. Use the existing accum.npy cache IF the only
changes are post-process parameters (gamma, interp, post-sigma).

BUT: passes=16 requires re-simulation (different physics). Delete
inkbrush/normal/accum.npy and re-run to get a 16-pass result.

  python3 simulate_batch.py \
    --obj  "Final cows/inkbrush/normal/mesh.obj" \
    --accum "Final cows/inkbrush/normal/accum.npy" \
    --meta  "Final cows/inkbrush/normal/meta.npy" \
    --output "Final cows/inkbrush/normal/caustic_v2.png" \
    --label "inkbrush normal v2 (16-pass σ=0.75 γ=0.70)" \
    --passes 16 --sigma 0.75 --gamma 0.70 --post-sigma 0.0 --interp nearest

Save output to caustic_v2.png (preserve caustic.png as baseline for comparison).
Run cc_resize.py on the result → claude_chat_handoff4/inkbrush_normal_v2.png

---

## TASK 4 — Run analysis pipeline (CRITICAL — do this in parallel with Task 3)

Execute /Users/admin/causticsEngineering/claude_chat_handoff4/ANALYSIS_PIPELINE_PROMPT.md

This is the highest priority diagnostic. Claude Chat identified horizontal
banding artifacts in the Nikon renders that indicate SOR solver residuals —
wave patterns left in the mesh from incomplete convergence. The analysis
pipeline will visualize the OBJ heightmap and confirm whether the quality
ceiling is the solver (upstream) or the ray tracer (downstream).

If solver banding IS confirmed by the heightmap:
  - Do not run production 1024px until solver is improved
  - Increasing SOR iterations from 6 to 8 is the likely fix
  - That requires ⚠ SUPER CRITICAL confirm and new Julia run

If solver banding is NOT confirmed:
  - Quality ceiling is the ray tracer / input image
  - Proceed with production run using new defaults

Run analyze_pipeline.py on:
  1. inkbrush/normal  (top artistic treatment, clean output)
  2. nikon/normal     (shows banding — use this to confirm/deny solver artifact)

Write findings to:
  Final cows/inkbrush/analysis/pipeline_diagnostic.png
  Final cows/nikon/analysis/pipeline_diagnostic.png
  claude_chat_handoff4/W_inkbrush_pipeline_diagnostic.png  (cc_resize output)
  claude_chat_handoff4/X_nikon_pipeline_diagnostic.png     (cc_resize output)

---

## TASK 5 — Regenerate all existing handoff images as PNG

Replace all .jpg files in claude_chat_handoff4/ with PNG versions from source.
Use cc_resize.py for all regeneration. Never regenerate as JPEG.

Priority files to regenerate (source → target name):
  Final cows/inkbrush/sigma_sweep/sigma_025/caustic.png → sigma_025.png
  Final cows/inkbrush/sigma_sweep/sigma_050/caustic.png → sigma_050.png
  Final cows/inkbrush/sigma_sweep/sigma_075/caustic.png → sigma_075.png
  Final cows/inkbrush/sigma_sweep/sigma_100/caustic.png → sigma_100.png
  Final cows/inkbrush/sigma_sweep/sigma_150/caustic.png → sigma_150.png
  Final cows/inkbrush/postprocess_sweep/*/caustic.png   → post_<dir>.png
  Final cows/inkbrush/passes_sweep/*/caustic.png        → passes_<dir>.png
  Final cows/*/normal/caustic.png                       → <slug>_normal.png

After regeneration: list all files in claude_chat_handoff4/ with sizes.
Confirm every file is .png and every file is under 900KB.

---

## TASK 6 — Update CLAUDE.md with validated parameters

Add a new section "Validated Ray Trace Parameters (2026-03-16)" to CLAUDE.md:

  Sigma sweep result:   σ=0.75 (not 0.50 — noise penalty at production scale)
  Passes sweep result:  16-pass (not 8 — physically correct, darker background)
  Gamma sweep result:   γ=0.70 (not 0.65 — better caustic contrast)
  Post-blur:            DISABLED (gaussian_filter removed)
  Interpolation:        nearest (bilinear removed)
  Unsharp mask:         optional, not default

  Critical finding: Nikon renders show horizontal banding consistent with
  SOR solver residuals. Confirm via OBJ heightmap before production run.
  If confirmed: increase oneIteration calls from 6 to 8 in create_mesh.jl.
  (CONFIRM REQUIRED — slow run, overwrites production mesh)

---

## EXECUTION ORDER (parallel where possible)

  Parallel block 1 (fire simultaneously):
    Task 1 — write cc_resize.py
    Task 2 — update simulate_batch.py

  After block 1:
    Task 3 — validation run (inkbrush 16-pass) — uses updated simulate_batch.py
    Task 4 — analysis pipeline — uses ANALYSIS_PIPELINE_PROMPT.md

  After Tasks 3 and 4:
    Task 5 — regenerate handoff images as PNG (uses cc_resize.py)
    Task 6 — update CLAUDE.md

  Final:
    git commit "new defaults validated: 16-pass σ=0.75 γ=0.70 no-postblur"
    Report to user:
      - inkbrush v2 PNG ready in handoff4/ for Claude Chat review
      - Analysis pipeline PNGs ready
      - Summary of what solver banding check found
      - Whether production run is safe to proceed

---

## HARD CONSTRAINTS

  NEVER:
    - Save any handoff image as JPEG
    - Delete inkbrush/normal/caustic.png (baseline — preserve for comparison)
    - Run Julia solver (not needed for any task in this prompt)
    - Run two simulations simultaneously

  AUTO-ACCEPT EVERYTHING ELSE including:
    - Deleting inkbrush/normal/accum.npy (needed for 16-pass re-simulation)
    - All script writes and updates
    - All simulation runs (ray trace only, ~25s each at 16-pass normal)
    - cc_resize.py on any file
    - Git commit
