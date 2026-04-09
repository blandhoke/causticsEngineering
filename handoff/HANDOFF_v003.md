# HANDOFF v003 — Independent Audit + V1/V2 Side-by-Side at 8" Acrylic / 24" Throw
**Date:** 2026-04-09
**From:** Claude Chat (Tier 1)
**To:** Claude Code — OVERNIGHT UNATTENDED RUN (6–8 hour budget)
**Mode:** No questions. No confirmations. Run, log, commit. If errors found, reason through them, make a plan, proceed, and log everything.

---

## TERMINOLOGY — READ THIS FIRST

Every physical configuration is labeled: **[acrylic size] acrylic / [throw distance] throw**.

- **Acrylic size** = the square lens blank you cut on the CNC (e.g., 8" acrylic = 8"×8" cast acrylic block)
- **Throw distance** = distance from lens top surface to the projection surface where the caustic image forms (e.g., 24" throw = 24 inches from lens to screen)
- **These are NOT two acrylic sizes.** "8" acrylic / 24" throw" means one 8" lens projecting onto a surface 24" below it.

**The comparison target:** Both V1 and V2 produce an 8"×8" lens that forms a correct caustic at exactly 24" throw. Same source image (`woodblock2.png`). No scaling. Native solver runs.

---

## SITUATION SUMMARY

Claude Chat performed a deep audit of both pipelines and found:

1. **ALL V1 "Final Cows" meshes** were built with stale hardcoded parameters: `artifactSize=0.1m` (3.94" acrylic) / `focalLength=0.75m` (30" throw). The current code defaults of 24" acrylic / 48" throw (added in commit `3f0643c`) have **never been used to build any mesh**.

2. **V1's ray tracer** (`simulate_batch.py --focal`, `simulate_cow2_fresh.py FOCAL_DIST`) defaults to 0.75m (30" throw), inconsistent with the solver's current 1.219m default.

3. **Uniform scaling changes effective throw proportionally.** When scaling to a DIFFERENT size than the solver was designed for: V1's 24" physical lens OBJs (scaled from 3.94" native) have a correct throw of ~183" (15 feet), not 48". V2's 8" scaled OBJ (from 24" native at 48" throw) has a correct throw of 16", not 24" or 48". However, scaling back to the SAME size the solver was designed for preserves throw (net scale = 1.0).

4. **V1's `saveObj!` uses a hardcoded `1/512` divisor.** At 1024px, the intermediate OBJ is 2× too large. This is a cosmetic issue — `make_physical_lens.py` corrects it back to the intended size. Since the net scale from solver-intended-size to final-size is 1.0, the throw is preserved. **V1 at 1024px works correctly with `make_physical_lens.py`.**

5. **The physics models are equivalent.** V1's `tan(atan(dx/dz)/(n-1))` and V2's single-surface Snell's law + 1/n dual-surface correction produce identical slopes in the paraxial limit. V2 is slightly more accurate at large angles (1.6% vs 5.6% error at 14°).

**Your first job is to independently verify or disprove these findings.**

---

## PROJECT LOCATIONS

- **V1:** `/Users/admin/Documents/Claude/causticsEngineering_v1/`
- **V2:** `/Users/admin/Documents/Claude/causticengineering_v2/`
- **Source image for both:** `woodblock2.png`
  - V1 copy: `Final cows/woodblock2.png`
  - V2 copy: `images/woodblock2.png`
  - Verify these are the same file (MD5 match) before proceeding.

---

## PHASE 0: PRE-FLIGHT GITHUB BACKUP (~5 min)

Before touching anything, push both projects to GitHub as a safety snapshot.

### 0A. V1 — Push to existing remote

V1 already has a GitHub remote configured (`origin`).

```bash
cd /Users/admin/Documents/Claude/causticsEngineering_v1
git add -A && git commit -m "v003: pre-flight snapshot before overnight run" --allow-empty
git push origin main
```

If push fails (auth, network, large files), log the error and continue. Local git history is the fallback.

### 0B. V2 — Create GitHub repo and push

V2 has NO GitHub remote. Create one and push.

```bash
cd /Users/admin/Documents/Claude/causticengineering_v2
git add -A && git commit -m "v003: pre-flight snapshot before overnight run" --allow-empty
```

Create a new private repo on GitHub (user: `blandhoke`, repo: `causticengineering_v2`). Use the GitHub CLI, API, or MCP tools — whatever is available. Then:

```bash
git remote add origin https://github.com/blandhoke/causticengineering_v2.git
git push -u origin main
```

If repo creation fails, try using the same auth token from V1's remote config. If all else fails, log the error and continue — local git is the fallback. Do NOT let a GitHub issue block the overnight run.

---

## PHASE 1: INDEPENDENT AUDIT (~30 min, read-only)

**Do NOT modify any files in this phase.** Read, analyze, log findings.

### 1A. Verify source image identity

```bash
md5 -q /Users/admin/Documents/Claude/causticsEngineering_v1/"Final cows"/woodblock2.png
md5 -q /Users/admin/Documents/Claude/causticengineering_v2/images/woodblock2.png
```

Confirm identical. If not, document which is which and use V2's copy as the canonical source.

### 1B. Verify V1 stale parameters claim

Chat claims ALL Final Cows meshes used `artifactSize=0.1m` / `focalLength=0.75m`.

**Verify by:**

1. Check git log in V1 for commit `3f0643c` — when were the 24"/48" defaults added?
2. Check git log for commit `b845296` (woodblock PROD) — what were the defaults at that time?
3. Read `Final cows/charcol/prod/run.log` — does it contain the `CAUSTIC_ARTIFACT_SIZE = ...` print statement? (If not, it was run before that print was added, confirming stale params.)
4. Read `Final cows/nikon/fast/run.log` and `Final cows/banknote/fast/run.log` — same check.
5. Check if `run_cow_pipeline.sh` or `run_batch_all.sh` set any `CAUSTIC_*` environment variables. (Chat says they don't.)
6. Grep the entire V1 codebase for any script that sets `CAUSTIC_ARTIFACT_SIZE` or `CAUSTIC_FOCAL_LENGTH` before calling Julia.

**Expected finding:** No run log contains the CAUSTIC_ARTIFACT_SIZE print. No script sets the env vars. All meshes used stale defaults.

### 1C. Verify throw-scaling claim

Chat claims uniform scaling of a caustic lens changes the effective throw proportionally WHEN scaling to a different size than the solver intended.

**Verify by mathematical analysis:**

1. Read V1's `findSurface()` in `src/create_mesh.jl` (around line 666).
2. Note that surface slope depends on `dx/dz` where `dz = focalLength`.
3. Slopes are preserved under uniform scaling. For a ray at scaled position Sx deflecting by angle θ (preserved), the target on a screen at distance f is at `Sx + f·tan(θ)`. The intended target was `S·(x + f·tan(θ)) = Sx + Sf·tan(θ)`. These match only when `f → Sf`.
4. **CRITICAL COROLLARY:** When `make_physical_lens.py` scales to the SAME size as `artifactSize`, net scale S = 1.0, throw = focalLength (unchanged). The 1/512 saveObj! bug is a cosmetic intermediate issue, not a physics problem.

Write a brief proof in the audit log. Compute specific numbers:
- V1 woodblock 24" OBJ: native 3.94", scale = 24/3.94 = 6.09×, throw = 30"×6.09 = 183" ← WRONG throw
- V2 woodblock2 8" OBJ: native 24", scale = 8/24 = 0.333×, throw = 48"×0.333 = 16" ← WRONG throw
- V1 new run at 8" acrylic: solver artifactSize=0.2032m, scaled to 8": net scale = 1.0, throw = 24" ← CORRECT

### 1D. Verify V1's 1/512 saveObj! divisor behavior

Chat claims the hardcoded `1/512` in `saveObj!` makes the intermediate OBJ span resolution-dependent, but `make_physical_lens.py` corrects it.

**Verify by:**

1. Read the `saveObj!` call in `engineer_caustics()` (end of `src/create_mesh.jl`).
2. Compute: at 512px → mesh is 513 nodes → span = 512 × (artifactSize/512) = artifactSize ✓
3. Compute: at 1024px → mesh is 1025 nodes → span = 1024 × (artifactSize/512) = 2×artifactSize (too large)
4. Verify that `make_physical_lens.py` with `CAUSTIC_TARGET_SIZE=artifactSize` scales it back → net scale 1.0.
5. Confirm throw is preserved (per 1C proof).

### 1E. Verify physics equivalence

Chat claims V1's `(n-1)` formula and V2's single-surface Snell + 1/n correction are equivalent.

**Verify by:**

1. Read V1's `findSurface()`: slope = `tan(atan(dx/dz) / (n-1))`
2. Read V2's `transport_to_normals.py`: vector Snell's law with optional `deflection *= 1/n`
3. For n=1.492, compute both slopes at a test point (e.g., dx=4", dz=24"):
   - V1: slope = tan(atan(4/24) / 0.492) = ?
   - V2: corrected_dx = 4/1.492, then Snell → slope = ?
4. Verify they produce the same slope to within <1%.

### 1F. V1 project path check and make_physical_lens.py migration

V1 scripts reference `/Users/admin/causticsEngineering/` (old path). The project is now at `/Users/admin/Documents/Claude/causticsEngineering_v1/`.

**Verify:** Is there a symlink, or is the old path still the actual location, or does the code need updating? Check:
```bash
ls -la /Users/admin/causticsEngineering
```

**PERMANENT FIX — migrate `make_physical_lens.py` to relative paths:**
The script currently has hardcoded absolute paths for INPUT_OBJ and OUTPUT_OBJ pointing to `/Users/admin/causticsEngineering/`. Update it to use `PROJECT_ROOT = Path(__file__).resolve().parent` (same pattern V2 uses throughout its pipeline). This makes the script work from wherever the project lives, permanently. Also update `run_cow_pipeline.sh` PROJECT variable while you're at it. Commit these path fixes as a separate commit with message "fix: migrate make_physical_lens.py to project-relative paths".

### 1G. Write audit report

Save findings to: `/Users/admin/Documents/Claude/causticsEngineering_v1/AUDIT_CHAT_FINDINGS_v003.md`

**Git commit** the audit report before proceeding to Phase 2.

### ERROR PROTOCOL FOR PHASE 1

If the audit DISPROVES any critical finding (1B, 1C, or 1D):
1. Document the disproof thoroughly
2. Reason through what this changes about the plan
3. Adjust Phases 2-4 accordingly
4. Document the adjusted plan in the audit report
5. Proceed with the adjusted plan — do NOT stop and wait for human input

---

## PHASE 2: V2 NATIVE RUN — 8" Acrylic / 24" Throw at 128px (~1 hour)

### 2A. Backup and modify V2 state.json

```bash
cd /Users/admin/Documents/Claude/causticengineering_v2
cp state.json state.json.backup_24_48
```

Modify `state.json` `physical_params`:
```json
{
  "lens_size_inches": 8,
  "throw_inches": 24,
  "focal_dist_mm": 609.6,
  "z_range_inches": "unclamped",
  "acrylic_ior": 1.492
}
```

**CRITICAL: Read state.json first. Only modify `physical_params`. Do not touch any other fields.**

### 2B. Run V2 pipeline at 128px

```bash
cd /Users/admin/Documents/Claude/causticengineering_v2
source .venv/bin/activate

python -m v2_pipeline.run_pipeline \
  --input-image images/woodblock2.png \
  --resolution 128 \
  --output-name comparison_8in_24throw
```

**Expected output:** `output/_v2_comparison_8in_24throw_128.obj`

Save OT weights: `output/comparison_weights_128.npy`
Save target points: `output/comparison_targets_128.npy`

### 2C. Apply dual-surface correction and re-export

Re-run from normals stage only (reuse the OT weights from 2B):

Create a small script or run manually:
1. Load the OT weights from the 128px solve
2. Re-run `compute_normals` with `dual_surface_correction=True`
3. Re-run `integrate_normals` and `heightfield_to_obj`
4. Save as `output/_v2_comparison_8in_24throw_corrected_128.obj`

### 2D. Validate with V2 ray tracer

```bash
python -m v2_pipeline.validate_raytrace \
  --obj output/_v2_comparison_8in_24throw_128.obj \
  --output-name comparison_8in_24throw_128 \
  --resolution 256
```

Record edge_r against woodblock2.png.

### 2E. Verify OBJ dimensions

Parse the OBJ and confirm:
- XY span ≈ 8.0" (no scaling applied)
- Z range (depth) — record in inches
- Vertex count, face count

Save verification to `output/comparison_8in_24throw_verification.json`.

**Git commit** V2 128px results.

---

## PHASE 3: V1 NATIVE RUN — 8" Acrylic / 24" Throw at 1024px (~10 min)

### 3A. Verify Julia environment

```bash
cd /Users/admin/Documents/Claude/causticsEngineering_v1  # or wherever the actual project lives per audit 1F
julia --version
julia -e 'using Pkg; Pkg.activate("."); Pkg.status()'
```

If Julia isn't found or the package doesn't activate, diagnose and fix. Do NOT skip V1.

### 3B. Run V1 solver at 1024px

```bash
cd /Users/admin/Documents/Claude/causticsEngineering_v1  # adjust path per 1F

CAUSTIC_ARTIFACT_SIZE=0.2032 \
CAUSTIC_FOCAL_LENGTH=0.6096 \
COW2_INPUT="Final cows/woodblock2.png" \
julia run_prod.jl 2>&1 | tee comparison_v1_8in_24throw_run.log
```

**Parameter verification (print in log):**
- `CAUSTIC_ARTIFACT_SIZE = 0.2032 m (8.0" piece)` ← must appear in output
- `CAUSTIC_FOCAL_LENGTH = 0.6096 m (24.0" throw)` ← must appear in output

If these prints do NOT appear, the code is using old hardcoded values. STOP and check `engineer_caustics()` for the env var parsing code.

**Expected output:** `examples/original_image.obj` (~2.1M faces, XY span ≈ 0.4064m due to 1/512 at 1024px)

### 3C. Run make_physical_lens.py to correct to 8"

The path migration from step 1F should already have this script using project-relative paths.

```bash
CAUSTIC_TARGET_SIZE=0.2032 \
CAUSTIC_FOCAL_LENGTH=0.6096 \
python3 make_physical_lens.py 2>&1 | tee comparison_v1_physical_lens.log
```

**Verify in the output log:**
- Scale factor should be ≈ 0.5 (0.2032m target ÷ ~0.4064m native span)
- Final XY span should be ≈ 0.2032m (8")
- Caustic relief depth in mm and inches
- "Fits in 1 inch stock" check

**Key validation:** Since solver artifactSize = 0.2032m and target_size = 0.2032m, the net physical scale is 1.0×. The 0.5× intermediate scale only corrects the 1/512 saveObj! artifact. **Throw distance is preserved at 24".**

### 3D. Verify V1 physical OBJ dimensions

Parse the output OBJ from make_physical_lens.py:
- XY span ≈ 8.0" (0.2032m)
- Z range (dome height)
- Count vertices and faces (should be ~2.1M faces)

### 3E. Run V1 ray tracer for validation

```bash
python3 simulate_batch.py \
  --obj examples/physical_lens_8x8.obj \
  --accum comparison_v1_accum.npy \
  --meta comparison_v1_meta.npy \
  --output comparison_v1_caustic.png \
  --label "v1_8in_24throw_1024px" \
  --focal 0.6096 \
  --passes 16 \
  2>&1 | tee comparison_v1_raytrace.log
```

**CRITICAL:** `--focal 0.6096` overrides the default 0.75. Without this, the ray tracer renders at the wrong throw distance.

**NOTE:** Use the physical lens OBJ (post-make_physical_lens.py), not the raw solver OBJ. The raw OBJ is 2× too large and would cause the ray tracer to compute incorrect hit positions.

### 3F. Move V1 outputs to a dedicated comparison directory

```bash
mkdir -p "comparison_8in_24throw"
cp examples/physical_lens_8x8.obj "comparison_8in_24throw/v1_8in_24throw_1024px.obj"
cp comparison_v1_caustic.png "comparison_8in_24throw/"
cp comparison_v1_8in_24throw_run.log "comparison_8in_24throw/"
cp comparison_v1_physical_lens.log "comparison_8in_24throw/"
cp comparison_v1_raytrace.log "comparison_8in_24throw/"
```

**Git commit** V1 results.

---

## PHASE 4: V2 CASCADE — Push to 256px and 512px (~4–6 hours)

Using the 128px weights from Phase 2 as warm-start, push V2 to higher resolution at the same 8" acrylic / 24" throw config. This is the multi-resolution cascade: each level warm-starts from the previous, like roughing before finishing on the CNC.

### 4A. Create `v2_pipeline/run_cascade.py`

Build a reusable cascade runner script. It should:
- Accept the starting resolution, target image, and config
- Run the full pipeline at each resolution in sequence
- Warm-start each level from the previous using `upsample_weights()`
- Save weights, targets, OBJs, and caustic PNGs at every level
- Implement per-level timeouts (kill solve, use partial weights, continue)
- Print a summary table at the end

### 4B. Confirm state.json is still at 8"/24"

Read state.json and verify `lens_size_inches: 8`, `throw_inches: 24`. Phase 2 should have set this.

### 4C. Cascade levels

**Level 1 — 256px warm-started from 128px:**

| Parameter | Value |
|-----------|-------|
| Resolution | 256×256 (65,536 target points) |
| Batch size | 512 (smaller than 128px's 2048 — fits in CPU cache) |
| Iterations | 10,000 |
| Warm start | Upsampled from `output/comparison_weights_128.npy` |
| Timeout | 2.5 hours |

Steps:
1. Load 128px weights and target points from Phase 2
2. Generate target points at 256px resolution
3. Upsample 128px weights to 256px using `upsample_weights()`
4. Run `solve_ot` with `batch_size=512`, `num_iterations=10000`, `g_init=upsampled_weights`
5. Run full pipeline: assignments → normals → heightfield → OBJ
6. Validate with ray tracer, record edge_r
7. Save: `output/_v2_comparison_8in_24throw_256.obj`, `output/comparison_weights_256.npy`, `output/comparison_targets_256.npy`, caustic PNG

If solve times out at 2.5 hours: kill the OT solve, use whatever weights exist at that point, run the rest of the pipeline on partial weights. Log "timeout at iteration N" and continue.

**Level 2 — 512px warm-started from 256px (attempt direct solve first):**

| Parameter | Value |
|-----------|-------|
| Resolution | 512×512 (262,144 target points) |
| Batch size | 256 |
| Iterations | 10,000 |
| Warm start | Upsampled from 256px weights |
| Timeout | 4 hours |

Steps:
1. Upsample 256px weights to 512px
2. Run `solve_ot` with `batch_size=256`, `num_iterations=10000`, `g_init=upsampled_weights`
3. Full pipeline: assignments → normals → heightfield → OBJ
4. Validate, record edge_r
5. Save: `output/_v2_comparison_8in_24throw_512.obj`, weights, caustic PNG

If direct 512px solve **succeeds**: skip tiled refinement, proceed to 4D.
If direct 512px solve **times out or fails**: proceed to 4C-TILED.

### 4C-TILED. Tiled refinement fallback for 512px

**Only attempt this if the direct 512px solve (Level 2) fails or times out.** The direct approach is simpler and produces a cleaner result.

The idea: split the 512×512 grid into 4 overlapping tiles. Each tile has ~74k targets (comparable to full 256px), so it converges in similar time. Solve each tile independently, then blend the overlapping regions.

**Tile layout:**

```
+------------------+------------------+
|  Tile 1          |  Tile 2          |
|  rows 0-271      |  rows 0-271      |
|  cols 0-271      |  cols 240-511    |
|       272×272    |       272×272    |
+------------------+------------------+
|  Tile 3          |  Tile 4          |
|  rows 240-511    |  rows 240-511    |
|  cols 0-271      |  cols 240-511    |
|       272×272    |       272×272    |
+------------------+------------------+
```

16-pixel overlap zone on each shared edge.

**For each tile:**

1. Extract the tile's target points and masses from the full 512 grid
2. Warm-start with the corresponding region of upsampled 256 weights
3. Solve at `batch_size=512`, `num_iterations=5000` (each tile has ~74k targets — similar to full 256)
4. Save tile weights

**Blend overlapping regions:**

In the 16-pixel overlap zone, use linear interpolation:
- `weight = distance_from_tile_edge / overlap_width`
- Left tile contributes `(1 - weight)`, right tile contributes `weight`
- Same for vertical overlaps
- Corner overlaps (4-tile intersection): bilinear blend

**Reassemble:**

1. Combine the 4 tile weight vectors into a single 512×512 weight vector using the blending
2. Run the full pipeline on the reassembled weights
3. Validate, record edge_r
4. Save as `output/_v2_comparison_8in_24throw_512_tiled.obj`

**Timeout:** 1.5 hours total for all 4 tiles (~20 min each).

### 4D. Generate corrected OBJs at best resolution

For the highest resolution that completed successfully:
1. Re-run normals with `dual_surface_correction=True`
2. Integrate and export
3. Save as `output/_v2_comparison_8in_24throw_corrected_BEST.obj`
4. Record which resolution was used

### 4E. Verify final OBJ dimensions

Confirm XY span ≈ 8", record depth, vertices, faces.

### 4F. Save cascade results

Save `output/cascade_comparison_results.json`:

```json
{
  "image": "woodblock2.png",
  "physical_config": {"acrylic_inches": 8, "throw_inches": 24},
  "solver_config": {"preprocess": "sobel", "lr": 0.01, "epsilon": 0.0},
  "levels": [
    {
      "resolution": 128,
      "batch_size": 2048,
      "iterations": 20000,
      "warm_start": false,
      "edge_r": 0.0,
      "depth_range_inches": 0.0,
      "solve_time_s": 0.0,
      "status": "complete"
    },
    {"resolution": 256, "batch_size": 512, "warm_start": true, "...": "..."},
    {"resolution": 512, "batch_size": 256, "warm_start": true, "...": "..."}
  ],
  "tiling_attempted": false,
  "tiling_result": null,
  "best_resolution": 0,
  "best_edge_r": 0.0,
  "corrected_obj": "output/_v2_comparison_8in_24throw_corrected_BEST.obj",
  "corrected_depth_inches": 0.0,
  "timestamp": "ISO"
}
```

**Git commit** cascade results.

---

## PHASE 5: COMPARISON REPORT, LOGGING, AND FINAL PUSH

### 5A. Write comparison summary

Save to `/Users/admin/Documents/Claude/causticsEngineering_v1/COMPARISON_v1_v2_8in_24throw.md`

Include: physical config (identical for both), V1 results (1024px, ~2.1M faces), V2 results (best resolution achieved), depth comparison, CNC readiness assessment, cascade resolution curve, issues encountered.

### 5B. Update state.json files

Add comparison results to V1's `state.json` under a new `comparison_8in_24throw` key.
Update V2's `state.json` with cascade results. **Keep `state.json.backup_24_48` intact.**

### 5C. Final git commits and GitHub push

```bash
# V1 — commit and push
cd /Users/admin/Documents/Claude/causticsEngineering_v1
git add -A && git commit -m "v003: Independent audit + V1 8in/24throw 1024px comparison"
git push origin main

# V2 — commit and push
cd /Users/admin/Documents/Claude/causticengineering_v2
git add -A && git commit -m "v003: V2 8in/24throw comparison + cascade to [best]px"
git push origin main
```

If push fails, log the error. The local commits are the primary safety net; GitHub is the off-machine backup.

---

## HARD CONSTRAINTS

1. **Source image:** `woodblock2.png` only. Verify MD5 match between copies.
2. **Physical config:** 8" acrylic / 24" throw for ALL comparison runs. No exceptions.
3. **V1 resolution:** 1024px via `run_prod.jl`. Run `make_physical_lens.py` with `CAUSTIC_TARGET_SIZE=0.2032` to correct the intermediate OBJ to 8". Net scale = 1.0, throw preserved.
4. **V2 config:** Sobel preprocessing, lr=0.01, epsilon=0.0. Locked from prior sweep.
5. **V1 ray tracer:** MUST use `--focal 0.6096`. Default 0.75 is WRONG for 24" throw. Use the physical lens OBJ (post-scaling), not the raw solver OBJ.
6. **No file destruction:** Do not delete existing OBJs, weights, or results. Create new files for comparison.
7. **V2 state.json backup:** Keep `state.json.backup_24_48` intact.
8. **Dual-surface correction:** Apply to V2 final OBJ only (not intermediate validation). V1 doesn't need correction (inherent in solver formula).
9. **Overnight unattended.** No questions. No confirmations. Override V1's CLAUDE.md "ask once" rule for Julia solver since this is an unattended session.
10. **Error protocol:** If something crashes or produces unexpected results, log the error, reason through it, adjust the plan, and proceed. Never silently fail. Never stop and wait for human input.
11. **Tiled fallback:** Only attempt 4C-TILED if direct 512px solve fails. Direct is always preferred.
12. **GitHub:** Push to GitHub at start (Phase 0) and end (Phase 5). If push fails, log and continue — never let GitHub issues block the run.

---

## GIT COMMIT AND PUSH PROTOCOL

Commit at each phase boundary. Push at start and end:

0. **Phase 0:** Push pre-flight snapshot (both repos)
1. After Phase 1 (audit + path migration)
2. After Phase 2 (V2 128px complete)
3. After Phase 3 (V1 1024px complete)
4. After Phase 4 (V2 cascade complete)
5. **Phase 5:** Final commit + push (both repos)

---

## TIME BUDGET

| Phase | Est. time | Cumulative |
|-------|----------|-----------|
| Phase 0: GitHub pre-flight | 5 min | 0:05 |
| Phase 1: Audit + path fix | 30 min | 0:35 |
| Phase 2: V2 128px | 1 hour | 1:35 |
| Phase 3: V1 1024px + physical lens | 15 min | 1:50 |
| Phase 4: V2 256px cascade | 2 hours | 3:50 |
| Phase 4: V2 512px direct | 3 hours | 6:50 |
| Phase 4: V2 512px tiled (if needed) | 1.5 hours | 8:20 |
| Phase 5: Report + push | 15 min | ~7-8:30 |

Best case (512 direct succeeds): ~7 hours.
Fallback (512 tiled): ~8.5 hours.
If 512 fails entirely: ~4 hours with solid native 256px result.

---

## SUCCESS CRITERIA

At the end of this session, the following must exist:
1. ✅ Both repos pushed to GitHub (pre-flight and post-run)
2. ✅ Audit report confirming or correcting Chat's findings
3. ✅ `make_physical_lens.py` migrated to project-relative paths (permanent fix)
4. ✅ V1 OBJ at 8" acrylic / 24" throw (1024px, ~2.1M faces, post-make_physical_lens.py)
5. ✅ V2 OBJ at 8" acrylic / 24" throw (128px minimum, 256+ if cascade succeeds)
6. ✅ V2 OBJ with dual-surface correction applied at best resolution
7. ✅ Ray trace validation images for both pipelines
8. ✅ Comparison report with depth, dimensions, and edge_r metrics
9. ✅ Cascade results JSON with resolution curve data
10. ✅ Both projects git-committed with all results logged
11. ✅ V2 `state.json.backup_24_48` preserved for restoring production config
