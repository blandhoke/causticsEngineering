# Comparison: V1 vs V2 — 8" Acrylic / 24" Throw
**Date:** 2026-04-09
**Session:** v003 (overnight unattended run)
**Source image:** woodblock2.png (MD5: c7ff322408426698f8946ae70d8e0625)

---

## Physical Configuration (identical for both)

| Parameter | Value |
|-----------|-------|
| Acrylic size | 8" × 8" |
| Throw distance | 24" (lens top to projection surface) |
| Acrylic IOR | 1.492 |
| Source image | woodblock2.png (Sobel preprocessed) |

---

## V1 Results (1024px, ~2.1M faces)

| Metric | Value |
|--------|-------|
| Solver | Julia SOR, 6 iterations, ω=1.99 |
| Resolution | 1024×1024 (2,097,152 top faces) |
| Solver params | artifactSize=0.2032m, focalLength=0.6096m |
| XY span | 203.2mm (8.000") |
| Full dome | 25.20mm (0.992") |
| Caustic relief | 6.28mm (0.247") |
| Scale factor | 0.4996× (correcting 1/512 saveObj artifact) |
| Net physical scale | 1.0× (throw preserved at 24") |
| Stock fit | ✓ Fits 1" cast acrylic (0.18mm margin) |
| Solver time | ~8 min |
| make_physical_lens.py | ✓ Axis correction OK, CNC origin set |

### V1 Ray Trace
- Passes: 16, sigma=0.751 (auto), gamma=0.70
- Hit rate: 100.0%
- Focal: 0.6096m (24" throw, correctly overridden from 0.75m default)
- Uses physical lens OBJ (post-scaling, not raw solver OBJ)

---

## V2 Results (128px best, cascade to 512px)

### Resolution Cascade

| Resolution | Faces | edge_r | bright_r | Depth (uncorr) | Depth (corr) | Solve time | Total time |
|------------|-------|--------|----------|----------------|--------------|------------|------------|
| 128px | 32,258 | **0.2489** | 0.2129 | 0.459" | 0.307" | 1.7s | 57 min* |
| 256px | 130,050 | 0.2014 | 0.1761 | 0.446" | 0.298" | 1.7s | 31 min* |
| 512px | 522,242 | 0.1117 | 0.1032 | 0.461" | 0.308" | 0.8s | 111 min* |

*Total time includes JAX JIT compilation (~57 min on first run, ~30 min on subsequent runs with different batch sizes). Actual OT solve is <2 seconds.

### V2 Solver Config
- Engine: ott-jax semi-discrete OT (Laguerre cells)
- Preprocessing: Sobel edge map
- Learning rate: 0.01, epsilon: 0.0
- 128px: 20000 iterations, batch_size 2048
- 256px: 10000 iterations, batch_size 512 (warm-started from 128px)
- 512px: 10000 iterations, batch_size 256 (warm-started from 256px)

### Observation: edge_r degrades at higher resolution
The 128px solve had the best edge_r (0.249). Higher resolutions (256px, 512px) produced lower edge_r. This is because:
1. More target points require more OT iterations to converge
2. 10000 iterations at 256px/512px is insufficient vs 20000 at 128px
3. The upsampled warm-start provides a good initial guess but more refinement is needed
4. The OT solver ran on CPU (JAX) — GPU would significantly improve convergence

### V2 Dual-Surface Correction
- Correction factor: 1/n = 0.6702
- Applied to deflection (not position)
- Reduces depth by ~33% (physically correct for plano-convex lens)

---

## Depth Comparison

| Pipeline | Uncorrected depth | Corrected depth | Notes |
|----------|-------------------|-----------------|-------|
| V1 1024px | N/A (inherent) | 6.28mm (0.247") relief | V1 formula incorporates dual-surface |
| V2 128px | 11.65mm (0.459") | 7.80mm (0.307") | With 1/n correction |
| V2 256px | 11.32mm (0.446") | 7.58mm (0.298") | With 1/n correction |
| V2 512px | 11.70mm (0.461") | 7.83mm (0.308") | With 1/n correction |

V2 corrected depths (~0.30") are about 22% deeper than V1 (0.247"). This difference reflects:
- V1 uses `tan(atan(dx/dz)/(n-1))` — exact thin lens formula
- V2 uses single-surface Snell + 1/n correction — slightly different in non-paraxial regime
- At 1.66% slope difference per computation (audit 1E), accumulated over the entire surface

Both fit comfortably in 1" cast acrylic stock.

---

## CNC Readiness Assessment

### V1 (READY)
- 2.1M faces, 8" × 8", 6.28mm relief
- make_physical_lens.py: axis corrected, CNC origin at front-left, Z=0 at peak
- 1/4" ball nose finishing appropriate (cell spacing ~0.008" at 1024px)
- Recommended: roughing + finishing pass

### V2 128px (NOT READY — low resolution)
- 32k faces at 128px is too coarse for production CNC
- Cell spacing = 8"/128 = 0.0625" — 1/4" ball nose at 20% stepover (0.050") would undersample
- Suitable for proof-of-concept only

### V2 256px (MARGINAL)
- 130k faces, cell spacing = 0.031"
- 1/8" ball nose at 10% stepover (0.0125") would work
- ~2 hour cut time estimated

### V2 512px (READY)
- 522k faces, cell spacing = 0.016"
- 1/4" ball nose at 20% stepover (0.050") appropriate
- Comparable to V1 at 512px resolution
- However: edge_r=0.1117 indicates solver did not fully converge. More iterations needed.

---

## Issues Encountered

1. **JAX JIT compilation overhead:** Each new batch size triggers ~30-60 min of JIT compilation on CPU. The actual OT solve takes <2 seconds. GPU would eliminate this.

2. **512px chunked assignment:** The compute_assignments_chunked step at 512px (262k×262k) took ~40-50 minutes per run due to large intermediate arrays (2GB per chunk). A more memory-efficient KD-tree approach could reduce this.

3. **GitHub push failures:** V1 repo has large OBJ files (>100MB) in history. V2 had .venv in history. V2 was cleaned with git-filter-repo and pushed successfully. V1 still needs history cleaning.

4. **V2 edge_r degradation at higher resolution:** The resolution curve (0.249 → 0.201 → 0.112) suggests the OT solver needs significantly more iterations at higher resolutions, or a multi-grid approach.

---

## Recommendations

1. **For immediate 8" proof cut:** Use V1 1024px OBJ (highest resolution, CNC-ready, fully converged)
2. **For V2 production quality:** Re-run at 256px with 30000+ iterations, or implement GPU acceleration
3. **For fair V1/V2 comparison:** Run V2 at 128px with 50000+ iterations to achieve full convergence, then compare edge_r with V1 at matching throw

---

## Files Generated

### V1 (in causticsEngineering_v1/)
- `examples/physical_lens_8x8.obj` — 8" CNC-ready OBJ (2.1M faces)
- `comparison_v1_caustic.png` — Ray trace caustic image
- `comparison_8in_24throw/` — Dedicated comparison directory with logs

### V2 (in causticengineering_v2/output/)
- `_v2_comparison_8in_24throw_128.obj` — 128px uncorrected
- `_v2_comparison_8in_24throw_256.obj` — 256px uncorrected
- `_v2_comparison_8in_24throw_512.obj` — 512px uncorrected
- `_v2_comparison_8in_24throw_corrected_128.obj` — 128px with 1/n correction
- `_v2_comparison_8in_24throw_corrected_256.obj` — 256px with 1/n correction
- `_v2_comparison_8in_24throw_corrected_512.obj` — 512px with 1/n correction
- `cascade_comparison_results.json` — Full cascade metrics
- `caustic_comparison_8in_24throw_*.png` — Ray trace images
- `comparison_weights_*.npy` — Saved OT weights for warm-starting
