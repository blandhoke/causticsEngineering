# HANDOFF v001 — Dual Refraction Audit + Woodblock Lens + Bit Resolution
**Date:** 2026-04-08
**From:** Claude Chat
**To:** Claude Code
**Blocker addressed:** DUAL_REFRACTION (state.json)

---

## ⚠ CPU RESOURCE WARNING — READ FIRST ⚠

**A separate Claude Code instance is currently running the v2 solver** in `/Users/admin/Documents/Claude/causticsEngineering_v2/`. This is a 10+ hour Julia solver run that is CPU-intensive.

**Before running any CPU-heavy operation in this session:**
1. Check system load: `top -l 1 | head -5` or `sysctl -n vm.loadavg`
2. If load average is already high (>6 on an 8-core machine, or >75% of core count), **STOP and report to the operator.** Do not stack heavy compute on top of the v2 solver.
3. The v2 solver takes priority. If this session's work would cause the v2 run to take 2-3× longer, **abort and wait.**

**What counts as CPU-heavy in this session:**
- Task 2 (generating physical lens OBJs from 4.2M face mesh) — `make_physical_lens.py` parses and transforms a ~200MB OBJ. This will spike CPU for a few minutes.
- Task 3 (curvature analysis on 4.2M face mesh) — numpy vertex/face processing on millions of elements. Could be significant.
- Task 1 (audit) — just reading files + grep. Negligible CPU. Safe to run anytime.

**If load is too high:** Complete Task 1 (the audit — it's all file reads), write findings, update state.json with partial results, and stop. Report to operator that Tasks 2-3 are deferred pending v2 solver completion. This is the correct behavior — do not try to power through.

---

## SESSION PROTOCOL

**Read order:** CLAUDE.md → state.json → this file.
**Thinking mode:** Hard. No ultrathink. Skeleton-first on any new code.
**Git:** Commit at session start (snapshot) and session end (results). Commit message format: `v001: <summary>`.
**State update:** Update `state.json` at session end with results from all three tasks.

---

## PRIOR SESSION LOG

No prior versioned sessions. This is the first handoff under the new architecture.

Relevant prior work:
- All 5 Final Cow images batch-processed through solver at multiple resolutions
- `make_physical_lens.py` exists and is functional — generates axis-corrected, scaled OBJs
- Charcol has pre-scaled 24" physical lens OBJs (standard + deep dome)
- CAUSTICFORGE v1.3 addon ready in Blender for G-code export
- No other images have physical lens OBJs yet

---

## TASK 1 — Dual Refraction Mismatch Audit (CRITICAL BLOCKER)

### Context

The solver uses Snell's law at a SINGLE refractive surface (air→acrylic, IOR 1.49). The physical lens is a plano-convex slab: light enters the curved top (air→acrylic), propagates through the medium, then exits the flat bottom (acrylic→air). Two refractions, not one.

The net effect: the physical lens deflects light approximately 49% more than the solver predicts. A caustic feature the solver places at radius `r` from center will appear at ~1.49r on the real projection surface.

This means every physical lens OBJ generated so far may produce a caustic image that is **spatially stretched** relative to what the ray tracer validated. The image will still look like the cow — but it will be bigger than the lens, with edges potentially clipped.

### Audit scope

1. **Read `make_physical_lens.py`** end to end. Search for any refraction correction, IOR compensation, shrink factor, or dual-surface logic. Look for: `ior`, `1.49`, `shrink`, `correction`, `compensat`, `refraction`, `dual`, `two_surface`, `snell`, `n_acrylic`. Report what you find with file + line numbers.

2. **Read the solver source** (`src/create_mesh.jl`, specifically `findSurface()` and `engineer_caustics()`). How does it compute surface height from the transport map? Does it apply Snell's law once (paraxial single-surface) or model both interfaces? Report with line numbers.

3. **Read `simulate_cow2_fresh.py`** (the active ray tracer). Count how many times it applies Snell's law per ray. If only once, the validation has the same blind spot and wouldn't detect the mismatch.

4. **Search ALL Python and Julia files** in the project for: `1.49`, `ior`, `refraction`, `snell`, `dual`, `two_surface`, `compensat`, `shrink_factor`, `correction_factor`, `n_acrylic`, `plano`. Command: `grep -rn "1\.49\|ior\|refraction\|snell\|dual.*surface\|shrink.*factor\|correction.*factor\|compensat\|n_acrylic\|plano" --include="*.py" --include="*.jl" .`

5. **Deliverable:** Write findings to `AUDIT_dual_refraction.md` in project root. Clear YES/NO/PARTIALLY answer with evidence.

### If NOT accounted for — implement the fix

**Approach: Post-scale in `make_physical_lens.py` (option C)**

Why this approach: The solver and ray tracer stay untouched. Their internal metrics (edge_r, sharpness, black_pct) remain valid and comparable across runs. The correction only applies when mapping solver output to physical CNC coordinates — which is exactly what `make_physical_lens.py` does.

**Before implementing, derive the correction factor from first principles:**

For a plano-convex lens (curved top, flat bottom) with refractive index n:
- Entry surface (air→acrylic): ray refracts at the curved surface
- Exit surface (acrylic→air): ray refracts at the flat bottom
- For small angles (paraxial), the thin lens power is: P = (n-1) × (1/R_top - 1/R_bottom)
- Flat bottom means 1/R_bottom = 0, so: P = (n-1)/R_top
- But the solver computes deflection as if the single surface has power: P_solver = (n-1)/R_top (air→acrylic only)
- The actual EXIT deflection through flat bottom adds another factor

Work through the full Snell's law geometry for a ray hitting a surface with local slope θ:
1. Single-surface deflection angle δ₁ (what the solver computes)
2. Additional deflection at flat exit surface δ₂
3. Total lateral displacement at throw distance D
4. Ratio: total_displacement / solver_predicted_displacement

Write the derivation in comments in the code. If the ratio is NOT ~1.49, use the correct value.

**Implementation:**
- Add CLI flag: `--dual-surface-correction` (default: enabled)
- Add CLI flag: `--ior` (default: 1.49)
- When enabled: scale XY vertex positions toward mesh center by the correction factor
- Z coordinates unchanged (relief depth is physical)
- Print the correction factor applied to stdout
- **Back up `make_physical_lens.py` to `make_physical_lens.py.bak` before any edit**

---

## TASK 2 — Generate Woodblock Physical Lens OBJs

**Depends on:** Task 1 complete (correction integrated or confirmed unnecessary)
**⚠ CPU check required before starting** — see CPU RESOURCE WARNING above.

### 2A: Woodblock 24" lens

```
Input:  Final cows/woodblock/normal/mesh.obj
        (NOTE: this is actually 1024px / 4.2M faces / ~0.2m native span)
Target: 24" × 24" (0.6096m)
Output: Final cows/woodblock/24in_standard/physical_lens_24x24.obj
```

Create the output directory if it doesn't exist.

### 2B: Woodblock 8" lens (for Task 3 analysis)

```
Input:  Final cows/woodblock/normal/mesh.obj
Target: 8" × 8" (0.2032m)
Output: Final cows/woodblock/8in/physical_lens_8x8.obj
```

### Verification

After generating each OBJ, report:
- File size
- Vertex count
- XY span (confirm matches target ± 0.1mm)
- Z relief (min Z to max Z)
- Whether dual-surface correction was applied (and what factor)

---

## TASK 3 — Bit Resolution Analysis for 8" Woodblock

**⚠ CPU check required before starting** — see CPU RESOURCE WARNING above.

### Question

Can a 1/4" ball nose end mill resolve the fine caustic detail in the 8" woodblock lens, or does it smear features — requiring 1/8"?

### Analysis steps

**3A: Mesh cell size**
- The woodblock normal mesh is 1024px → 1025×1025 nodes → 1024 cells per axis
- At 8" physical: cell_size = 8.0 / 1024 ≈ 0.00781" per cell
- CONFIRM by reading actual vertex positions from the generated 8" OBJ. Compute minimum and mean vertex-to-neighbor spacing in X and Y.

**3B: Bit geometry vs mesh resolution**

| Bit | Diameter | Tip Radius | Stepover (10%) | Stepover (8%) |
|-----|----------|------------|----------------|---------------|
| 1/4" ball | 0.250" | 0.125" | 0.025" | 0.020" |
| 1/8" ball | 0.125" | 0.0625" | 0.0125" | 0.010" |
| 1/16" ball | 0.0625" | 0.03125" | 0.005" | 0.004" |

Mesh cell size (~0.0078") is smaller than 1/8" stepover (0.0125") and much smaller than 1/4" stepover (0.025"). But stepover determines pass spacing — the tip radius determines what features the bit can physically enter.

**3C: Surface curvature analysis (the real question)**
- Load the 8" woodblock OBJ with numpy (parse vertices + faces)
- For each face: compute the surface normal
- For each vertex: compute local mean curvature from surrounding face normals
- Convert curvature to minimum radius of concavity: R_min = 1 / |curvature|
- Build a histogram of concavity radii across all vertices
- Report: what % of surface area has concavity radius < 0.125" (1/4" limit)?
- Report: what % of surface area has concavity radius < 0.0625" (1/8" limit)?

**3D: Scallop height**
- Formula: h = R - sqrt(R² - (stepover/2)²) where R = ball radius
- Compute for each bit at its default stepover
- Compare scallop height to the Z relief range of the 8" lens
- Scallop height should be <5% of total relief for acceptable finish

**3E: Cut time estimate**
- Passes = ceil(8.0 / stepover)
- Pass length = 8.0"
- Lines = passes × 2 (bidirectional raster)
- Time = (total_travel / feed_rate) + retract_overhead
- Feed rates from CAUSTICFORGE: 1/4"=144 IPM, 1/8"=100 IPM, 1/16"=72 IPM

### Deliverable

Write to: `ANALYSIS_woodblock_8in_bit_resolution.md` in project root.

Include:
- Mesh cell size (measured, not computed from formula)
- Curvature distribution summary (mean, median, 5th percentile concavity radius)
- % of features below each bit threshold
- Scallop height table
- Cut time estimates for roughing + finishing at each bit size
- **Clear recommendation:** which finishing bit, which stepover, whether roughing 1/4" + finishing 1/8" is the right combo
- If 1/4" is viable for 8": say so with the numbers. If 1/8" is needed: say so with the numbers. Hoping for 1/8" but let the data decide.

---

## HARD CONSTRAINTS

- **⚠ V2 SOLVER IS RUNNING** — A 10+ hour Julia solver is active in a separate Claude Code instance. Check CPU load before any compute-heavy task. If load is high, complete Task 1 only and stop. The v2 solver takes absolute priority over v1 work.
- Do NOT modify `src/create_mesh.jl` or any solver source
- Do NOT run the Julia solver
- Do NOT delete any existing physical lens OBJs
- Do NOT modify CAUSTICFORGE addon
- Do NOT touch anything in `/Users/admin/Documents/Claude/causticsEngineering_v2/`
- Back up any file before modifying it
- Git commit at start and end of session

## EXPECTED OUTCOMES

1. `AUDIT_dual_refraction.md` — clear answer on whether the mismatch is handled
2. If needed: updated `make_physical_lens.py` with dual-surface XY correction
3. Two new woodblock physical lens OBJs (24" and 8") — *if CPU allows*
4. `ANALYSIS_woodblock_8in_bit_resolution.md` — bit resolution recommendation with data — *if CPU allows*
5. Updated `state.json` reflecting all results (including partial completion if CPU-gated)

---

## STATE.JSON UPDATES AT SESSION END

Update these fields:
- `session_last`: "v001"
- `session_last_date`: today's date
- `physical_lens_pipeline.dual_surface_refraction_corrected`: true/false with correction factor
- `blockers[DUAL_REFRACTION].status`: "resolved" or "unresolved" with notes
- Add woodblock entries to `physical_lens_pipeline.existing_physical_objs`
- `next_session_task`: "HANDOFF_v002" (Claude Chat will decide scope)
- `next_session_scope`: brief description of what's next (likely: Blender import + CAUSTICFORGE G-code export)
- If Tasks 2-3 deferred: set `next_session_scope` to include deferred work
