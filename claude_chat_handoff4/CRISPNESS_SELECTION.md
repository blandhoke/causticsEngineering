# CRISPNESS_SELECTION.md
# Written by: Claude Chat (independent visual analysis)
# Date: 2026-03-16
# Note: This analysis was performed INDEPENDENTLY from Claude Code's conclusions.
#       Disagreements are flagged explicitly.

---

## PARAMETER SELECTIONS

### Sigma: σ=0.75 (DISAGREES with Claude Code's σ=0.50)

σ=0.50 introduces micro-contrast noise artifacts in the fur and forehead
that read as graininess. The perceived sharpness gain over σ=0.75 is minimal
at display scale but the noise penalty is real. At 1024px production these
artifacts will be more visible, not less. σ=0.75 has better tonal continuity.

### Gamma: γ=0.70 (DISAGREES with Claude Code's γ=0.65)

γ=0.65 muddies the mid-tone detail in the forehead and ear regions. γ=0.70
produces genuinely darker background with brighter caustic line contrast —
this is closer to what sunlight caustics physically look like. The image
reads as "light ON a surface" rather than a glowing emboss. Validate at
1024px before committing — dynamic range shifts at higher resolution.

### Post-process blur: REMOVE (sigma=0.0) — AGREES with Claude Code

"No blur nearest" is clearly superior to baseline. The post-process
gaussian_filter(0.5) is degrading real caustic detail.

Exception: unsharp mask should NOT be ruled out as an option. The rim-lighting
enhancement on ear/jaw contours in the unsharp panel is physically plausible
for sunlight caustics. Keep as optional parameter --unsharp.

### Passes: 16-pass σ=0.50 — STRONGLY DISAGREES with Claude Code's 8-pass

This is the most significant disagreement. The 16-pass panel has MORE black
background showing than 8-pass — that is the correct physical behavior. Light
concentrating precisely into caustic lines means the background stays dark.
Claude Code interpreted the darker background as "flat/off." It is not — it is
physically correct. The finer σ=0.50 with more passes produces the most
accurate energy distribution. Use 16-pass for NORMAL and above. Use 8-pass
for FAST where time is a constraint.

### Colormap: Keep sunlight — AGREES with Claude Code

Reference target: the sunlight σ=0.75 γ=0.5 panel in T is the closest visual
approximation to what a real physical caustic under sunlight looks like.
That is the benchmark all future renders should be compared against.

---

## CRITICAL FINDING NOT RAISED BY CLAUDE CODE: NIKON BANDING

The Nikon renders (both baseline and best params in S) show horizontal
banding artifacts across the lower face and neck. These are NOT sigma or
post-process artifacts — they are SOR solver residuals, wave patterns left
in the mesh surface from the iterative solver not fully converging.

No amount of ray-trace parameter tuning fixes this. The fix is upstream:
  Option 1: More SOR iterations (currently 6, try 8-10)
  Option 2: Different input image for Nikon that doesn't excite this mode
  Option 3: The analysis pipeline OBJ heightmap will show this directly

This is the most important finding from the entire sweep. It means the
rendering quality ceiling is currently set by the solver, not the ray tracer.
Post-process tuning is polishing the output of a partially-converged solver.

---

## RECOMMENDED NEW DEFAULTS FOR ALL FUTURE RUNS

  --sigma    0.75        (not 0.50 — too noisy at production scale)
  --passes   16          (not 8 — physically correct, worth the time)
  --post-sigma 0.0       (remove gaussian_filter entirely)
  --interp   nearest     (remove bilinear interpolation)
  --gamma    0.70        (not 0.65 — better caustic contrast)
  --unsharp  optional    (not default, but available as --unsharp 1.5)

Expected render time at NORMAL (512px): ~25s (from 7s at 4-pass × 4 = ~28s)
Expected render time at production (1024px): ~160s ray trace

---

## WHAT TO DO NEXT (in priority order)

1. Run analysis pipeline (ANALYSIS_PIPELINE_PROMPT.md) — visualize OBJ
   heightmap to confirm solver banding is upstream of ray tracer. This
   determines whether the quality ceiling is the solver or the renderer.

2. Apply new defaults to simulate_batch.py (update CLI defaults).
   Run one NORMAL pass on inkbrush with new defaults as validation.

3. If OBJ heightmap confirms solver banding: increase SOR iterations
   in create_mesh.jl from 6 to 8. This requires ⚠ SUPER CRITICAL confirm
   and a new Julia run (~45 min). But it may unlock significantly better
   output quality across all 5 treatments.

4. Do NOT commit to production 1024px run until step 1 and 2 are validated.
   The current output quality ceiling may be the solver, not the renderer.
   Milling a lens with solver banding would waste a full acrylic slab.
