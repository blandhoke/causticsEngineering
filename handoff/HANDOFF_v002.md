# HANDOFF v002 — Forensic Cross-Pipeline Comparison: V1 vs V2 Woodblock 8"
**Date:** 2026-04-08
**From:** Claude Chat
**To:** Claude Code
**Prior session:** v001 (dual refraction audit, woodblock lens gen, bit analysis)

---

## ⚠ CPU RESOURCE WARNING — STILL APPLIES ⚠

V2 solver still running. This session is READ-ONLY analysis — CPU impact should be negligible. Check load at session start anyway.

**Do NOT modify anything in `/Users/admin/Documents/Claude/causticengineering_v2/`.** Read-only access for comparison. This is a cross-team collaboration, not an intervention.

---

## SESSION PROTOCOL

**Read order:** CLAUDE.md → state.json → this file.
**Thinking mode:** Hard. No ultrathink.
**Git:** Commit at session start and end (v1 repo only). Format: `v002: <summary>`.
**State update:** Update `state.json` at session end.

---

## CONTEXT — WHY THIS COMPARISON MATTERS

V1 and V2 are deliberately different pipelines competing to produce the best caustic lens:
- **V1:** Julia SOR optimal transport → Poisson surface reconstruction → `(n-1)` thin lens formula
- **V2:** ott-jax semi-discrete OT → vector Snell's law normals → Frankot-Chellappa integration

Both target the same physical output: a CNC-milled acrylic lens on the Blue Elephant 1325.

Bland is about to cut an 8" proof piece. Both pipelines have an 8" woodblock physical lens OBJ. The question is which one to cut — and whether either has a physics error that would waste acrylic.

**This is a team exercise.** If you spot something that could help V2 improve, document it. V2's Claude Code will do the same review of V1. We all win when the best lens gets cut.

---

## TASK 1 — Source Image Verification

### Problem

V1 woodblock run.log says `Loading: Final cows/woodblock.png` but that file no longer exists. Only `Final cows/woodblock2.png` (1.39MB) exists. A separate `INKFORGE/woodblock.png` (447KB) also exists — different file.

V2 explicitly uses `images/woodblock2.png` (1.39MB, confirmed in v2's state.json).

### Steps

1. `md5 "Final cows/woodblock2.png"` and `md5 /Users/admin/Documents/Claude/causticengineering_v2/images/woodblock2.png` — confirm same file
2. `git log --all --diff-filter=D -- "Final cows/woodblock.png"` — check if this file was deleted from git
3. `git log --follow --oneline -- "Final cows/woodblock/normal/mesh.obj"` — when was the mesh last written?
4. Check if the mesh vertex count matches a 512px run (1,052,672 faces) or 1024px run (4,202,496 faces) — the run.log describes a 512px run but the file is 205MB which suggests 1024px
5. If the mesh file postdates the run.log, the run.log is stale and a later run may have used a different source image

### Deliverable

Write to `VERIFICATION_woodblock_source.md`. Answer: are v1 and v2 8" lenses built from the same source image? YES / NO / UNCERTAIN.

---

## TASK 2 — Physics Model Forensic Comparison

This is the big one. V1 and V2 reach DIFFERENT conclusions about dual-surface refraction. Both cannot be right in the same way. Your job is to understand what each pipeline ACTUALLY does (not what docs say), compare them, and determine whether the difference matters for the physical lens.

### What V1 does (from actual code)

**Solver** (`src/create_mesh.jl`, `findSurface()` ~line 676):
```julia
Nx[i,j] = tan(atan(dx/dz) * inv_n1m1)   # inv_n1m1 = 1/(n-1)
```
Surface slope = tan(deflection_angle / (n-1))

V1's audit claims this IS the dual-surface plano-convex thin lens formula because total exit deflection for a thin plano-convex lens = α(n-1).

**Ray tracer** (`simulate_cow2_fresh.py`): Applies Snell's law TWICE — once at curved entry surface (air→acrylic), once at flat exit (acrylic→air). This is a full dual-surface physical model.

**Physical scaling** (`make_physical_lens.py`): Uniform XYZ scale. No refraction correction. None needed per v1's logic.

### What V2 does (from actual code)

**Solver** (ott-jax): Computes optimal transport map (source positions → target positions)

**Normals** (`transport_to_normals.py`):
```python
raw_normal = n1 * d_i - n2 * d_t   # Vector Snell's law, SINGLE surface
```
Then optionally applies:
```python
if dual_surface_correction:
    correction = 1.0 / ior  # = 0.670
    deflection = assigned_targets - grid_points
    assigned_targets = grid_points + deflection * correction
```
This SHRINKS target positions before computing normals. Logic: "physical dual-surface lens amplifies deflection by ~n, so pre-shrink by 1/n."

**Ray tracer** (`validate_raytrace.py`): Applies Snell's law ONCE — single surface only. Matches the solver's model (no exit surface).

**Physical scaling** (`scale_obj.py`): Uniform XYZ scale. No additional refraction correction.

### The fundamental question

Both pipelines aim for the same physical result: the dual-surface lens sends light to the correct target positions. But they get there differently:

- **V1:** Solver directly uses (n-1) deflection formula → mesh surface slopes ARE the physical slopes → ray tracer confirms with two-surface tracing → no post-correction
- **V2:** Solver uses single-surface OT → pre-shrinks targets by 1/n → computes normals from shrunk targets using single-surface Snell → ray tracer validates with single-surface only → mesh encodes smaller deflections that the physical dual-surface lens will amplify back to correct size

If both are mathematically correct, the resulting mesh geometries should differ by exactly a factor related to n. Specifically:
- V1 mesh slopes should encode the FULL dual-surface deflection
- V2 mesh slopes should encode 1/n times the full deflection
- V2 mesh should therefore have SHALLOWER relief than V1 for the same target/throw

**BUT** v2 state.json shows 0.378" depth at 8" while v1 shows 2.055mm (0.081") — v2 is DEEPER, not shallower. This is backwards from what the refraction model difference predicts.

### Your analysis tasks

**2A: Trace actual throw distance used by each pipeline**

⚠ CRITICAL DISCOVERY: V1's `engineer_caustics()` defaults are:
```julia
artifactSize = get(ENV, "CAUSTIC_ARTIFACT_SIZE", "0.6096")  # 24"
focalLength  = get(ENV, "CAUSTIC_FOCAL_LENGTH",  "1.219")   # 48"
```
But V1's CLAUDE.md says `focalLength = 0.75m` (29.5"). The CLAUDE.md may be stale. The actual solver may have used 1.219m (48") throw.

V2 uses `throw_inches = 48` (1.219m).

If both used 48" throw, one explanation for depth differences vanishes. Check:
- V1: what env vars were set when the woodblock mesh was generated? Check run logs, pipeline scripts, and git history. The run.log in `Final cows/woodblock/normal/` might show this.
- V2: confirmed 48" from state.json.
- Also check: when `make_physical_lens.py` generated the v1 8" OBJ, what NATIVE_FOCAL_M did it use?

**2B: Read `make_physical_lens.py` and trace the full scale chain**

The 2.055mm depth for v1's 8" lens seems very shallow. Read `make_physical_lens.py` end to end and trace:
- What input mesh does it read?
- How does it compute the scale factor?
- Does it apply a focal-length-dependent dome scaling?
- Is the Z relief being scaled differently than XY?
- What is the actual Z range of the raw solver mesh (before scaling)?
- And what's the Z range of the v1 8" physical lens OBJ you just generated in v001?

**2C: Read `scale_obj.py` from v2 and trace the same chain**

Same questions for v2. The 0.378" depth (9.6mm) at 8" — where does that come from? Read the input mesh, trace the scale, verify the output.

**2D: Direct mesh comparison**

Load both 8" physical lens OBJs with numpy:

```
V1: Final cows/woodblock/8in/physical_lens_8x8.obj
V2: /Users/admin/Documents/Claude/causticengineering_v2/output/physical_lens_8x8_woodblock2.obj
```

Compare:
- Vertex count, face count
- XY span (should both be ~8")
- Z range (max - min vertex Z)
- Z profile: extract center-line (Y = 4.0" ± tolerance) Z values, plot both on same axes
- Total volume under the surface (proxy for "how much acrylic gets carved away")
- RMS surface slope (proxy for how aggressive the lens refraction is)

**2E: The refraction model agreement/disagreement summary**

Write a clear summary:
1. Do both pipelines account for dual-surface refraction? (YES, but differently)
2. Are the approaches mathematically equivalent in the paraxial limit?
3. If equivalent, why do the depths differ?
4. If NOT equivalent, which one is correct for a plano-convex acrylic lens?
5. What testable prediction differs between them? (e.g., "V1 predicts caustic image size X, V2 predicts Y — whichever matches the physical cut is correct")

**2F: Findings for V2 to improve (collaborative)**

If you spot anything that could help v2 — a simplification, a potential error, a missed optimization — write it up. Examples of things to look for:
- V2's CLAUDE.md says "Single-surface thin-lens model" but the correction makes it effectively dual-surface. Is the documentation misleading?
- V2's ray tracer validates with single-surface only. If the mesh encodes pre-shrunk targets, is the ray tracer actually validating the correct physical prediction?
- V2's correction factor is 1/n = 0.670. V1's audit derives that the ratio of dual-to-single is n/(n-1) × (n-1)/n = 1... wait, that's 1. Actually, single gives α(n-1)/n, dual gives α(n-1). Ratio = n. So correction should be 1/n = 0.670 — this matches. But verify the derivation.
- Does V2's Frankot-Chellappa integrator match V1's Poisson/SOR integrator in accuracy?

---

## TASK 3 — V2 G-code Status Report

V2 already has G-code in `causticengineering_v2/output/`:
- `woodblock2_8x8_roughing.nc`
- `woodblock2_8x8_finishing.nc`
- `woodblock2_8x8_squarecut.nc`

**Read-only.** Report:
- File sizes and line counts
- First 10 and last 5 lines of each (G20/G54 setup, feed rates, spindle commands)
- Any header comments about toolpath parameters (bit, stepover, DOC)
- Which bit was used for finishing? Does it match the 1/8" recommendation from v001?

---

## HARD CONSTRAINTS

- **READ-ONLY on `/Users/admin/Documents/Claude/causticengineering_v2/`** — absolutely no writes
- Do NOT modify v1 solver source, ray tracers, or existing OBJs
- Do NOT run any solvers or ray tracers
- Do NOT attempt to "fix" either pipeline's physics — document findings only
- Git commit at start and end of session (v1 repo only)
- CPU-light tasks only

## DELIVERABLES

1. `VERIFICATION_woodblock_source.md` — source image confirmation
2. `COMPARISON_v1_v2_woodblock_8in.md` — comprehensive forensic comparison including:
   - Actual throw distances used by each pipeline
   - Full scale chain traced for both
   - Direct mesh geometry comparison with plots
   - Refraction model analysis
   - Findings for V2 team
   - V2 G-code status
3. Comparison plots as PNGs (prefix: `comparison_v1v2_`)
4. Updated `state.json`

---

## STATE.JSON UPDATES AT SESSION END

- `session_last`: "v002"
- `session_last_date`: today's date
- Add `v1_v2_comparison` key with:
  - `source_image_match`: true/false
  - `throw_distance_match`: true/false and what each used
  - `depth_v1_inches`: measured from OBJ
  - `depth_v2_inches`: measured from OBJ
  - `refraction_model_equivalent`: true/false with explanation
  - `recommended_cut`: which pipeline's 8" OBJ to cut first and why
- Update `blockers[SOURCE_IMAGE_UNCERTAINTY]` status
- `next_session_task`: "HANDOFF_v003"
- `next_session_scope`: TBD by Claude Chat after reviewing comparison
