# Caustic Render Analysis: v2 → v3 Improvement
# Terminal 2 (Claude Code) → Claude Chat
# Date: 2026-03-15

---

## What Changed (v2 → v3)

Four improvements were applied to the forward ray trace in `simulate_cow.py`:

| Step | Change | Purpose |
|------|--------|---------|
| 1 | Cosine weighting: `w = areas * cos_i / r²` | Correct irradiance for grazing-angle faces |
| 2 | 4-pass jittered barycentric supersampling | Sample each face at 4 random sub-face points instead of centroid |
| 3 | Gaussian photon splat (σ=1.5, r=3px) | Spread each photon hit across a 7×7 kernel instead of single pixel |
| 4 | Post-process Gaussian smooth (σ=0.5) | Soften residual grain without degrading edges |

The OBJ mesh and Julia solver are UNCHANGED. Same 6-iteration cow lens.
Cache was regenerated: 4 passes × 525,534 faces = **2,097,152 total ray samples**, 99.8% hit rate.

---

## Images (included in this package)

| File | Description |
|------|-------------|
| `cow_render.jpg` | Original target (512×512 B&W photo) |
| `caustic_cow_v2.png` | Previous output — centroid ray, single-pixel splat |
| `caustic_cow_v3.png` | New output — jittered supersampling + Gaussian splat |

---

## Quantitative Metrics

### Structural Similarity (SSIM, range −1 to 1, higher = more similar)

| Comparison | v2 | v3 | Change |
|-----------|----|----|--------|
| vs original image | 0.0301 | **0.0909** | **+3.0×** |
| vs Sobel edge map | — | — | — |
| v2 vs v3 (self) | — | 0.7137 | 71% structural overlap |

### Pearson Correlation

| Comparison | v2 | v3 |
|-----------|----|----|
| r vs original brightness | −0.077 | −0.102 |
| r vs Sobel edge magnitude | +0.245 | **+0.313** |

### Dynamic Range & Brightness Distribution

| Metric | v2 | v3 |
|--------|----|----|
| Mean brightness | 0.060 | **0.111** (+85%) |
| Std deviation | 0.100 | **0.155** (+55%) |
| p75 | 0.116 | **0.245** |
| p90 | 0.208 | **0.316** |
| p99 | 0.369 | **0.613** |

v3 has 85% more mean brightness and dramatically higher contrast in the upper brightness
range. The Gaussian splat filled in the dark gaps between face centroids.

### Quadrant Brightness (original vs caustic)

| Region | Original | v2 | v3 |
|--------|----------|----|----|
| top-left (forehead, light ear) | 0.628 | 0.060 | 0.104 |
| top-right (dark ear, background) | 0.487 | 0.069 | 0.129 |
| bottom-left (dark body) | 0.306 | 0.061 | 0.117 |
| bottom-right (bright background) | 0.786 | 0.052 | 0.097 |

All quadrants improved in absolute brightness. The spatial correlation with the
original is still near-zero — the caustic does not reproduce flat-field brightness —
but the tonal richness is significantly better.

---

## Visual Analysis

### v2 Appearance
- Harsh isolated bright lines on a near-black background
- Large dark gaps between lines (artefact of single centroid ray per face)
- The cow's shape was readable but felt sparse and spidery
- The flat interior regions of the face were dark even though the solver placed
  surface curvature there

### v3 Appearance
- Smooth, continuous tonal gradients across the cow face
- The fur texture is still present as fine bright lines, but now surrounded by a
  warm amber fill rather than black gaps
- The neck/head silhouette is defined by a bright caustic rim — physically correct
  (maximum lens curvature at the boundary between the bright face and dark background)
- The muzzle, eye sockets, and ear structure have clearly differentiated tonal levels
- The overall effect resembles sunlight pooled through a physical glass element —
  warm, continuous, with bright edge accents
- No visible mesh-grid artifact (the 512-grid tessellation that was faintly visible
  in the circle caustic is fully suppressed by the Gaussian splat)

---

## Persistent Issue: Spatial Brightness Mismatch

The caustic still does not reproduce the original brightness distribution:

- **The bright gray background** (bottom-right quadrant, original = 0.786) has
  caustic brightness **0.097** — the dimmest quadrant.
- **The dark body fur** (bottom-left, original = 0.306) has caustic brightness
  **0.117** — one of the brighter quadrants.

This is INVERTED and is not an artifact of the rendering improvements. It is a
fundamental consequence of how the SOR mesh-warp solver works at 6 iterations:

1. The solver redistributes face area proportionally to target brightness.
   Large uniform regions (background) get many large flat faces.
2. Large flat faces → gentle surface normals → rays deflect only slightly →
   light spreads diffusely rather than concentrating.
3. Sharp boundaries (face/body edges) get many compressed faces with steep normals
   → rays concentrate → bright caustic lines.
4. Net result: the caustic is bright at **edges**, dim at **flat bright regions**.

This is confirmed by r(v3, Sobel edges) = +0.313 vs r(v3, original) = −0.102.
The caustic is a gradient/edge image of the target, not a brightness replica.

---

## Questions for Claude Chat

### Q1 — Is v3 quality sufficient for CNC fabrication?

Looking at `caustic_cow_v3.png`: does the rendered caustic represent a physically
plausible output that would justify CNC milling? Or is the spatial brightness
mismatch (background dim, edges bright) a show-stopper that must be fixed first
at the solver level?

Specifically: **in a real physical caustic lens under sunlight, would the output
look like v3** (edges bright, fill continuous but dim) **or would it look like
the original image** (flat regions bright, edges at normal brightness)?

This determines whether the issue is with our simulator or with our expectations.

### Q2 — Target image preprocessing to fix the brightness mismatch

Given that the caustic encodes gradients rather than flat brightness, three
preprocessing strategies have been proposed:

**Option A — Blur the target before the solver:**
Apply a large Gaussian blur (σ~10–20px) to the input before `run.jl`. This
smooths the edges into broad bright halos, which the solver would then encode
as large deflection regions → brighter fill in the output.

**Option B — Use the edge map as the target:**
Pre-compute the Sobel/Laplacian edge magnitude of the cow image and use THAT
as the solver input. Since the caustic naturally produces edges, feeding it
an edge map would produce a caustic that matches the edges well.

**Option C — Use a binary/silhouette image:**
Create a white-filled cow silhouette on black and use that as the target.
The solver would concentrate all light inside the silhouette boundary.

Which of A, B, or C is recommended by the caustic literature (Schwartzburg 2014,
Papas 2011, Weyrich 2009)? Is there a standard preprocessing pipeline?

### Q3 — More solver iterations vs. different solver

The loss amplitude at iteration 6 (±1.45) is barely lower than at iteration 3 (±1.43).
Running more iterations does not seem to help — the solver has stalled at the
resolution limit of the 512-grid.

Would it help to:
- Increase grid resolution to 1024 (requires recompiling or changing `grid_definition`)?
- Use the Schwartzburg 2014 OT solver in `~/Desktop/caustic_tools/ShapeFromCaustics/`
  instead of the SOR solver in `run.jl`? This is the `ma.py` file — what does it
  produce and how does its output compare?

### Q4 — Blender validation of v3

Can you import the cow lens OBJ into Blender and do a quick render?
The OBJ is currently the **cow mesh** at:
  `/Users/admin/causticsEngineering/examples/original_image.obj`

Import with `forward_axis='Y', up_axis='Z'`. Even a Cycles render at low sample
count would tell us whether the Blender renderer produces the same edge-dominant
pattern that the forward ray trace shows, confirming that v3 is physically correct.

### Q5 — Ready for `make_physical_lens.py`?

The pipeline at `~/Desktop/caustic_tools/make_physical_lens.py` scales the OBJ to
physical dimensions (8"×8", 27" throw). Should this be run on the current cow OBJ
to produce a CNC-ready file, or should we wait until the brightness mismatch is
resolved via better target preprocessing?

---

## Current Pipeline State

```
run.jl              → points to "examples/cow render.jpg"
original_image.obj  → COW mesh (26.2mm dome, 100.1mm span)
simulate_cow.py     → outputs caustic_cow_v3.png (4-pass, cosine weight, Gaussian splat)
circle lens         → NOT on disk (overwritten); re-run with circle_target.png if needed
```

Git: commit `2cd0dac` — "add cosine weighting, jittered supersampling, gaussian splat"
