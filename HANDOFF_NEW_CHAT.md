# CausticsEngineering — Full Session Handoff
# Claude Chat Session: March 15, 2026
# Prepared for: New Claude Chat instance
# Topic: Evaluate external Cycles caustic plugin for techniques applicable to our pipeline

---

## Project in One Paragraph

A Julia program designs a refractive acrylic lens surface (OBJ mesh) that projects
a target image as a caustic pattern under sunlight. The pipeline: target image →
Julia OT solver → OBJ mesh → Python forward ray trace → caustic verification image.
The physical output is a CNC-milled acrylic lens (8"x8", 1" thick, 27" throw).
IOR=1.49, focal=0.2m. Collaborator: Leslie King (separate pipeline, ignore her params).

---

## What Is Confirmed Working

### Forward Ray Trace (ground truth verification)
- Script: `/Users/admin/causticsEngineering/simulate_cow.py`
- Traces ~525k rays through OBJ via Snell's law, 99.8% hit rate
- Caches to `cow_accum.npy` / `cow_meta.npy` — do not delete
- Output colormap: warm sunlight (black→amber→gold→white)
- Current output: `examples/caustic_cow_v2.png`

### OBJ Import (Blender)
- `forward_axis='Y', up_axis='Z'` — confirmed correct, do not change
- Lens Z range: -0.01953 → +0.00664m (dome height ~26mm)
- Mesh: 526k verts, 1.05M faces, CLOSED (manifold), normals 97.9% in Z

### Blender 4.3.2 Caustic API
- `light.cycles.is_caustics_light = True`
- `lens.cycles.is_caustics_caster = True`
- `plane.cycles.is_caustics_receiver = True`
- Old names (use_shadow_caustic, is_caustic_catcher) silently fail in 4.3

### Orientation Fixes (confirmed correct, do not revert)
- `origin='upper'` in matplotlib imshow
- `np.fliplr(accum)` before plotting
- permutedims in Julia is benign for square images — do not remove

---

## Completed Analysis: Why Cow Caustic Looks Wrong

Full quantitative analysis by Terminal 2 (Claude Code). Summary:

| Root Cause | Verdict | Evidence |
|---|---|---|
| Geometric transform error | NOT the cause | Edge overlay confirms correct placement |
| Simple brightness inversion | NOT the cause | SSIM(inv) only 19% better, both near zero |
| Wrong simulation parameters | NOT the cause | 99.8% hit rate, correct edge structure |
| Wrong input image type | PRIMARY cause | Background (41.9%) gets less light than dark fur |
| Caustic physics = edge detector | Expected physics | r(caustic,edges)=+0.28 vs r(caustic,brightness)=-0.09 |
| Solver stall at 512 grid | Secondary | Loss oscillates it3→it6, fur unrepresented |

Key insight: caustics are physically edge detectors. r(caustic, Sobel edges) = +0.28,
which is 3x stronger than brightness correlation. SSIM(caustic vs edge map) = 0.252,
vs SSIM(caustic vs original) = 0.038. The solver is working correctly — the cow
photograph was the wrong input type.

---

## What Claude Code (Terminal 2) Is Currently Running

Three preprocessing experiments (started, may be complete):
1. `examples/circle_target.png` → `examples/caustic_circle.png`
   White circle on black — pipeline geometry validation
2. `examples/cow_silhouette.png` → `examples/caustic_cow_silhouette.png`
   Background-removed cow, white on black
3. `examples/cow_edges.png` → `examples/caustic_cow_edges.png`
   Sobel edge map of cow as target

Results not yet seen. Upload images to Claude Chat when ready.

---

## LuxCore Status

BlendLuxCore installed on disk, pyluxcore binary NOT downloaded.
Activation: Blender UI → Edit → Preferences → Extensions → BlendLuxCore → Enable
(one manual click, cannot be scripted).
LuxCore BIDIR attempted via headless script — ran for 60+ min, inconclusive.
Low priority. Forward ray trace is sufficient for pattern verification.

---

## Key File Locations

/Users/admin/causticsEngineering/
  CLAUDE.md                     ← auto-accept instructions, Claude Code reads this
  CAUSTICS_CONTEXT.md           ← earlier Blender MCP session notes
  run.jl                        ← Julia entry (edit target image path here)
  src/create_mesh.jl            ← solver, focalLength=0.2 at line 878
  simulate_cow.py               ← forward ray trace (use cache, do not re-run)
  simulate_caustic.py           ← water drop version (reference)
  examples/
    original_image.obj          ← cow lens mesh (current)
    cow_accum.npy               ← DO NOT DELETE (ray trace cache)
    cow_meta.npy                ← DO NOT DELETE
    caustic_cow_v2.png          ← current best output
    caustic_simulated.png       ← water drop reference (DO NOT OVERWRITE)
    circle_target.png           ← (may exist, Terminal 2 generating)
    caustic_circle.png          ← (may exist, Terminal 2 generating)

---

## The Curveball: New Task for This Chat

A Cycles-based Blender plugin specifically designed for caustic rendering exists
and reportedly works well. The new Claude Chat instance should:

1. Evaluate the plugin — understand its approach to caustic rendering in Cycles
2. Extract specific techniques, math, or methods it uses to overcome Cycles'
   known caustic convergence limitations
3. Identify anything applicable to our pipeline:
   - Does it use a different light path strategy?
   - Does it use MNEE (Manifold Next Event Estimation)?
   - Does it use photon mapping or progressive photon mapping?
   - Does it preprocess the scene geometry in any way?
   - Does it use custom OSL shaders?
   - Does it apply any post-processing to reduce fireflies?
4. Determine if any of its techniques could improve our Python forward ray trace
   output quality (sharper edges, better contrast, less mesh-grid artifact)
5. Determine if any techniques could make a Cycles render viable as an alternative
   to or complement of the forward ray trace

The goal is not to switch to the plugin — it is to learn from it.

---

## Strategic Context

The forward ray trace produces a correct but visually noisy output due to the
triangulated mesh grid pattern visible in the caustic. The mesh grid artifact
is because we're splatting one ray per face centroid — any technique that
smooths this (supersampling, Gaussian splatting, importance sampling) would
improve output quality significantly.

The Python ray trace gives physics-correct results but looks like a triangle mesh.
The ideal output looks like the SIGGRAPH 2014 paper figures — smooth, clean caustic
patterns. Understanding how the Cycles plugin achieves this would directly inform
how to post-process our ray trace output.

---

## DO NOT (carry forward from CLAUDE.md)

- Do not delete cow_accum.npy or cow_meta.npy
- Do not overwrite caustic_simulated.png
- Do not change OBJ import axes
- Do not apply Leslie King's pipeline parameters to this project
- Do not use standard Cycles for caustic verification (fireflies, no convergence)
- Do not re-run julia run.jl unless explicitly instructed
