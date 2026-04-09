# COMPARISON — V1 vs V2 Woodblock 8" Physical Lens (Forensic)
**Date:** 2026-04-09
**Session:** v002
**Source:** HANDOFF_v002 Tasks 2 + 3

---

## EXECUTIVE SUMMARY

V1 and V2 are **not directly comparable** for this woodblock cut. They differ in:
1. **Source image** (INKFORGE/woodblock.png vs woodblock2.png — different files, r=0.907)
2. **Solver resolution** (1024px / 2.1M faces vs 128px / 32k faces)
3. **Native lens size** (0.1m / 3.94" vs 24")
4. **Throw distance** (30" vs 48")
5. **Refraction model** (thin plano-convex formula vs corrected single-surface Snell)

The refraction models ARE mathematically equivalent in the paraxial limit (both produce slope = delta / (f*(n-1))). The 4.7x depth difference is **not a physics error** — it's primarily driven by the different native sizes and throw distances. A controlled comparison requires running both pipelines on the same image at the same resolution with the same physical parameters.

**Recommendation for first cut:** V2's 8" lens at 48" throw, because it was purpose-designed for the 48" throw that both pipelines now target, and has G-code ready. V1's 8" woodblock lens was computed for a 30" throw (stale config) — its physical accuracy at 48" is undefined.

---

## 2A: THROW DISTANCES

| Parameter | V1 (at time of PROD woodblock run) | V2 |
|-----------|-------------------------------------|-----|
| Throw distance | 0.75m = 29.5" (hardcoded) | 48" = 1.219m |
| Native lens size | 0.1m = 3.94" | 24" |
| artifactSize / lens_size | 0.1m | 24 inches |
| Source commit | `b845296` (Mar 17, 2026) | state.json `2026-04-08T22:00:00Z` |

**Evidence:**
- V1: `git show b845296^:src/create_mesh.jl` shows `artifactSize = 0.1` and `focalLength = 0.75` — both hardcoded, no env var support yet. The 24" / 48" defaults were added in commit `3f0643c` AFTER the woodblock run.
- V2: `state.json` → `physical_params.throw_inches = 48`, `lens_size_inches = 24`.

**Impact:** V1's woodblock mesh was designed for a 30" throw installation (8"x8" piece, 30" from lens to floor). V2's was designed for a 48" throw. If Bland installs at 48", only V2 is physically correct. V1 would need to be re-run with updated parameters.

---

## 2B: V1 SCALE CHAIN

```
Julia solver (PROD run, commit b845296):
  artifactSize = 0.1m,  focalLength = 0.75m
  Input: INKFORGE/woodblock.png (1024x1024, grayscale)
  Grid: 1025x1025 nodes → 2,101,250 vertices → 4,202,496 faces
  OBJ scale: 1/512 * 0.1 = 0.000195 m/node
  
Raw solver mesh (Final cows/woodblock/normal/mesh.obj):
  XY span: 0.200069m x 0.200100m (native ≈ 7.88")
  Z range: -0.019531 to +0.003097 (total dome 22.63mm)
  Top surface relief: 2.024mm (just the caustic variation)
  Bottom slab: flat at Z = -0.019531m

gen_woodblock_physical.py (v001 session):
  Target: 8" = 0.2032m
  SCALE = 0.2032 / 0.2001 = 1.016x (barely any change!)
  → XY: 0.2032m (8.000")
  → Caustic relief: 2.055mm (scaled from 2.024mm)
  → Total Z: 22.979mm (includes slab offset)
  → Units: METERS
  → Z=0 at caustic peak, cuts go negative
```

**Key insight:** The V1 woodblock mesh was computed for a ~4" native lens, so scaling to 8" is only a 1.016x factor. The total Z range (22.98mm) is mostly slab offset — only 2.055mm is actual caustic surface variation. The 2.055mm is the CNC-relevant cut depth.

---

## 2C: V2 SCALE CHAIN

```
ott-jax solver + transport_to_normals.py + Frankot-Chellappa:
  Input: woodblock2.png (1024x1024 RGB, resized to 128x128)
  Grid: 128x128 = 16,384 vertices
  lens_size = 24",  throw = 48",  IOR = 1.492
  Dual-surface correction: deflection *= 1/n (0.670)
  
Raw solver mesh (_v2_woodblock2_corrected_128.obj):
  XY span: 23.8125" x 23.8125" (native at 24" scale)
  Z range: 0.0 to 1.1235" (28.54mm)
  Units: INCHES
  
Uncorrected mesh for comparison:
  Z range: 0.0 to 1.6790" (42.65mm)
  Ratio corrected/uncorrected: 0.669 ≈ 1/n = 0.670 ✓
  
scale_obj.py:
  Target: 8"
  SCALE = 8.0 / 23.8125 = 0.3360x
  → XY: 8.000" x 8.000"
  → Z range: 0.3775" (9.59mm) — this is the CNC cut depth
  → Solidified: bottom at z=0, top surface 0..0.3775"
  → Units: INCHES
  → Z=0 at stock bottom, cuts go positive (inverted from V1)
```

**Key insight:** V2 starts at 24" native scale and shrinks 3x to get to 8". The dual-surface correction (1/n) reduces depth by exactly the expected factor. The Z orientation is inverted from V1 (V1 cuts negative from peak, V2 builds positive from bottom).

---

## 2D: DIRECT MESH COMPARISON

| Metric | V1 (8" woodblock) | V2 (8" woodblock) |
|--------|-------------------|-------------------|
| Source image | INKFORGE/woodblock.png | woodblock2.png |
| Solver resolution | 1024px | 128px |
| Vertices (total/solidified) | 2,101,250 | 32,768 |
| Top surface vertices | 1,050,625 | 16,384 |
| XY span | 7.999" | 8.000" |
| Total Z range | 22.98mm (0.905") | 9.59mm (0.378") |
| Caustic relief (CNC cut depth) | 2.055mm (0.081") | 9.59mm (0.378") |
| V2/V1 CNC depth ratio | — | 4.66x |
| Center-line RMS slope | 0.0134 | 0.0519 |
| Center-line max slope angle | 1.72 deg | 6.57 deg |
| Center-line mean slope angle | 0.67 deg | 2.58 deg |
| OBJ units | meters | inches |
| Z orientation | peak=0, cuts negative | base=0, surface positive |
| Throw distance used | 30" | 48" |
| Native lens size | 3.94" | 24" |

### Center-line Z profiles

See `comparison_v1v2_centerline.png` for:
- Individual center-line profiles (V1: 1025 sample points, V2: 128 sample points)
- Normalized shape overlay (0-1 range)
- Surface slope angle distribution

The V1 profile shows very fine detail (1024px resolution) but extremely shallow relief (2mm).
The V2 profile shows coarser features (128px) but significantly deeper relief (9.6mm).

### Volume and slope

V2 slopes are ~4x steeper than V1 on average (2.58 deg vs 0.67 deg). Both are gentle enough for any ball nose end mill. Neither lens has concavities small enough to be problematic — all curvature radii are far above 1/4" ball radius.

---

## 2E: REFRACTION MODEL ANALYSIS

### 1. Do both pipelines account for dual-surface refraction?

**YES, but differently.**

| Aspect | V1 | V2 |
|--------|-----|-----|
| Approach | Thin plano-convex formula: `slope = tan(atan(d/f) / (n-1))` | Pre-shrink deflection by 1/n, then single-surface Snell |
| Where dual-surface enters | The `(n-1)` term IS the dual-surface thin lens equation | The `1/n` correction compensates for single-surface model |
| Ray tracer | Full two-surface Snell (entry + exit) | Single-surface only |

### 2. Are they mathematically equivalent in the paraxial limit?

**YES.**

V1 paraxial: slope ≈ delta / (f * (n-1))

V2 paraxial derivation:
```
  delta_corrected = delta / n
  refracted direction d_t ≈ (delta/(n*f), 0, -1)  [for small angles]
  raw_normal = n1*d_i - n2*d_t = (0,0,-1) - n*(delta/(n*f), 0, -1) = (-delta/f, 0, n-1)
  slope = -nx/nz = delta / (f*(n-1))
```

Both give `slope = delta / (f * (n-1))`. QED.

### 3. If equivalent, why do the depths differ?

The depths differ because V1 and V2 are **not solving the same physical problem:**

| Factor | V1 | V2 | Effect on depth |
|--------|-----|-----|-----------------|
| Throw distance | 30" | 48" | ~1.6x |
| Native lens size | 3.94" | 24" | ~6x larger deflection angles |
| Source image | INKFORGE/woodblock.png (brighter) | woodblock2.png (darker, more contrast) | Unknown |
| Solver resolution | 1024px | 128px | V2 less converged |
| Scale to 8" | 1.016x (barely changes) | 0.336x (significant shrink) | Built into depth |

The combination of these factors produces a 4.66x depth ratio. No single factor explains it — it's the compound effect of solving genuinely different physical problems.

### 4. Which one is correct for the target installation?

If the physical installation is **48" throw:** V2 is correct. V1 was computed for 30" throw.

If the physical installation is **30" throw:** V1 is correct (but only for the INKFORGE/woodblock source).

Neither is "wrong" — they're designed for different installations. But V1's CLAUDE.md now says `focalLength = 1.219` (48"), and the 24" config was added after the woodblock run. The V1 woodblock mesh is essentially orphaned — it uses stale parameters that no longer match the project's target configuration.

### 5. Testable predictions

- **V1 at 30" throw:** Should project an ~8" caustic image. Caustic quality depends on INKFORGE/woodblock.png content.
- **V2 at 48" throw:** Should project an ~8" caustic image. Caustic quality depends on woodblock2.png content.
- **V1 at 48" throw:** Caustic will be ~1.6x too large (projected image ~13" instead of 8") because the surface was designed for 30" throw.
- **V2 at 30" throw:** Caustic will be ~0.6x too small (projected image ~5" instead of 8").

Cut one and measure the projected image size at the intended throw distance. If it matches the lens size (±10%), the physics is correct.

---

## 2F: FINDINGS FOR V2 TO IMPROVE

### 1. Documentation: "Single-surface" is misleading

V2's CLAUDE.md says "Single-surface thin-lens model" but the actual code applies a dual-surface correction (`1/n = 0.670`). The documentation should say: **"Corrected single-surface model (pre-shrink deflection by 1/n to account for dual-surface amplification)."** The current phrasing makes it sound like dual-surface refraction is ignored, when it's actually handled.

### 2. Ray tracer validation mismatch

V2's ray tracer (`validate_raytrace.py`) uses single-surface Snell with **no correction**. But the mesh encodes pre-shrunk deflections (1/n factor baked in). When the ray tracer traces through this mesh, it applies single-surface Snell to a surface designed for dual-surface physics. The ray tracer output represents **what the model predicts** for a single-surface lens, NOT what the physical dual-surface lens will do.

For validation purposes: this is fine (it validates the solver → mesh → ray trace consistency). But it does NOT predict the actual physical caustic. The physical lens will amplify deflections by ~n, producing a caustic that's ~1.49x larger than the ray tracer shows.

**Recommendation:** Add a `--physical` flag to the ray tracer that applies Snell's law twice (entry + exit surface) to predict actual physical output. This is what V1's ray tracer does, and it's essential for predicting whether the cut lens will actually work.

### 3. Resolution gap

V2's production mesh is only 128px (16,384 surface vertices). V1's is 1024px (1,050,625 surface vertices). At 8", V2's mesh cell spacing is `8" / 128 = 0.0625"` (1.59mm). V1's is `8" / 1024 = 0.0078"` (0.20mm). The V1 mesh has **64x more surface detail**.

A 1/4" ball nose at 20% stepover (V2's G-code config) has 0.050" stepover — finer than V2's 0.0625" cells. The CNC toolpath has higher resolution than the mesh it's cutting. At minimum, V2 should run at 256px before production. V2's state.json shows `best_edge_r_256 = 0.2413` which is significantly better than 128px (0.2248).

### 4. Convergence

V2's state.json: `"ot_converged": false`. The OT solver did not fully converge at 128px. Non-convergence means the transport map is suboptimal — some light may land in wrong locations. This could manifest as blurry or misplaced features in the physical caustic.

### 5. Frankot-Chellappa vs Poisson/SOR

Both V1 (SOR Poisson) and V2 (Frankot-Chellappa FFT) are valid surface integrators. FC is faster (FFT = O(n log n) vs SOR = O(n * iterations)). Both enforce integrability. For a well-posed normal field, they produce identical results. No action needed — this is a valid design choice.

---

## TASK 3: V2 G-CODE STATUS REPORT

### Files

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `woodblock2_8x8_roughing.nc` | 50,363 | 1.77 MB | Roughing pass |
| `woodblock2_8x8_finishing.nc` | 64,035 | 2.25 MB | Spiral finishing |
| `woodblock2_8x8_squarecut.nc` | 4,537 | 161 KB | Perimeter cut with tabs |

### Roughing

- **Tool:** 1/4" Ball Nose 2-Flute
- **Strategy:** Y-raster
- **DOC:** 0.100"
- **Stepover:** 0.150" (60% dia)
- **Feed:** 144 IPM, Plunge: 20 IPM, RPM: 18000
- **Skin left:** 0.015" (for finish pass)
- **Rough floor:** -0.380"
- **Z levels:** 4, Y rows/level: 54
- **Entry:** Edge-entry only — no plunges into stock
- **Setup:** G54, G20 (inches), G17 G90

### Finishing

- **Tool:** 1/4" Ball Nose 2-Flute
- **Strategy:** Archimedean spiral, outside-in, CW climb
- **Stepover:** 0.050" (20% dia)
- **Feed:** 144 IPM, Plunge: 20 IPM, RPM: 18000
- **Revolutions:** ~114, R from 5.707" to 0.025"
- **Scallop guide:** 20% stepover ≈ 2.6 mil scallop height
- **Points:** 64,002

### Square Cut

- **Tool:** 0.500" O-flute
- **RPM:** 20,000
- **Feed:** 120 IPM, Plunge: 36 IPM
- **DOC:** 0.150", Passes: 7
- **Total depth:** 1.010"
- **Tabs:** 4 x 0.500" wide x 0.100" tall

### Bit Selection vs V1 Recommendation

V1's bit analysis recommended **1/8" ball nose at 10% stepover** for 8" pieces. V2's G-code uses **1/4" ball nose at 20% stepover** for both roughing and finishing.

At V2's mesh resolution (128px), the 1/4" ball at 20% (0.050" stepover) is actually appropriate — it's finer than the mesh cell spacing (0.0625"). Using a 1/8" ball would gain no additional detail from a 128px mesh.

If V2 scales to 256px or higher, the 1/8" recommendation from V1's analysis would apply.

---

## COMPARISON PLOTS

- `comparison_v1v2_centerline.png` — Four-panel figure:
  - V1 center-line Z profile (1025 points)
  - V2 center-line Z profile (128 points)
  - Normalized shape overlay
  - Surface slope angle distribution

---

## SOURCE FILES READ (for reproducibility)

V1:
- `src/create_mesh.jl` (lines 666-730: findSurface, lines 853-903: engineer_caustics)
- `make_physical_lens.py` (full)
- `gen_woodblock_physical.py` (full, v001 one-shot script)
- `logs/julia_20260317_201430.log` (PROD run log)
- `Final cows/woodblock/normal/mesh.obj` (raw solver mesh, measured)
- `Final cows/woodblock/8in/physical_lens_8x8.obj` (physical lens, measured)

V2 (READ-ONLY):
- `v2_pipeline/transport_to_normals.py` (full)
- `v2_pipeline/normals_to_heightfield.py` (full)
- `v2_pipeline/heightfield_to_obj.py` (full)
- `v2_pipeline/scale_obj.py` (full)
- `v2_pipeline/validate_raytrace.py` (full)
- `state.json` (full)
- `CLAUDE.md` (full, via system reminder)
- `output/_v2_woodblock2_corrected_128.obj` (measured)
- `output/_v2_woodblock2_128.obj` (measured, uncorrected for comparison)
- `output/physical_lens_8x8_woodblock2.obj` (measured)
- `output/woodblock2_8x8_roughing.nc` (header + footer)
- `output/woodblock2_8x8_finishing.nc` (header + footer)
- `output/woodblock2_8x8_squarecut.nc` (header + footer)
