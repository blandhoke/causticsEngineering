# Handoff: Focal Length Optimization — Befuddled Cow v4
**Date:** 2026-03-15
**Terminal 2 (Python ray trace pipeline) → Claude Chat**

---

## What We Were Trying to Do

Scale the befuddled cow caustic lens to physical 8"×8" CNC dimensions using 1" cast acrylic stock (25.4mm). The solver had been run previously with `focalLength = 0.2m` and the resulting lens was too deep to mill.

---

## Key Findings

### Dome Height vs Focal Length (empirical, same image/resolution)

| focalLength | Native dome | Physical dome | Physical throw | Status |
|-------------|------------|---------------|----------------|--------|
| 0.20m       | 34.04mm    | 34.6mm        | 8"             | ✗ exceeds 1" |
| 0.30m       | 29.84mm    | 30.3mm        | 12"            | ✗ exceeds 1" |
| 0.60m       | 25.66mm    | 26.1mm        | 24"            | ✗ exceeds by 0.7mm |
| **0.75m**   | **24.82mm**| **25.22mm**   | **30"**        | ✓ fits |

### Critical discovery: dome does NOT scale as 1/f

Initial assumption was `dome ∝ 1/focalLength`. Reality:
- Z_min of the OBJ is **fixed at -19.531mm** across all focal lengths — it's set by the solidifier base, not the optics
- Only Z_max changes with focalLength
- Actual rate: ~4.2mm reduction per +0.1m at low f, slowing to ~1.4mm per +0.1m at higher f
- This means you cannot analytically predict the required focal length — it must be empirically bracketed

### Dome margin at f=0.75m is tight
- Physical dome = 25.22mm vs 25.4mm limit → **0.18mm margin**
- For CNC: Z-zero precision matters. Recommend 1.125" stock or careful zero verification.

---

## What Was Built / Fixed

### `src/create_mesh.jl`
- Changed `focalLength = 0.2` → `focalLength = 0.75`

### `make_physical_lens.py` (rewritten)
- Was: hardcoded `NATIVE_SIZE_M = 0.1`, broke at 1024px (native is 0.2m, not 0.1m)
- Now: reads actual XY span from OBJ, computes `SCALE = TARGET_SIZE_M / native_span_m` dynamically
- Also hardcoded `NATIVE_FOCAL_M` which must be kept in sync with `create_mesh.jl` — this is a manual maintenance burden (see issues below)

### `verify_obj.py`
- Fixed SyntaxError: f-string with backslash inside expression doesn't work in Python <3.12
- Script now runs cleanly

---

## Current Output Files

| File | Description |
|------|-------------|
| `examples/original_image.obj` | Solver output, native 200mm×200mm, dome 24.82mm, f=0.75m |
| `examples/physical_lens_8x8.obj` | Scaled 8"×8", dome 25.22mm, throw 30", CNC-ready (177MB) |
| `examples/caustic_befuddled_v1.png` | Ray trace at f=0.20m (reference) |
| `examples/caustic_befuddled_v4.png` | Ray trace at f=0.75m (current) |

---

## Open Issues / Things to Work Through

### Issue 1: verify_obj.py false positive on "50% top-surface faces"
The script flags meshes where <90% of faces have Z-pointing normals. At 1024px, the solidified mesh has ~50% top-facing faces (closed solid with both top curved surface and flat bottom). The 90% threshold was written for an open surface mesh. Script exits with error code 1 even when the dome check passes.
- **Impact:** Pipeline halts at verify step unless this is fixed or the check is removed/corrected for closed meshes

### Issue 2: NATIVE_FOCAL_M in make_physical_lens.py is manually maintained
The throw distance calculation requires `NATIVE_FOCAL_M` to match `focalLength` in `create_mesh.jl`. These are in two separate files with no enforcement. If someone changes one and not the other, the reported throw distance will be wrong (the OBJ geometry is still correct, only the metadata printout is affected).
- **Proposed fix:** Read focalLength from the OBJ filename or a sidecar `.json` written by the solver

### Issue 3: Physical throw shown in make_physical_lens.py doesn't match intuition
At f=0.75m the throw distance reported is 762mm (30"). But `make_physical_lens.py` computes throw as `NATIVE_FOCAL_M × SCALE`. This is the distance from the **lens bottom** to the projection plane, not the total installation height. The light source sits above the lens top, so total installation depth = throw + dome height ≈ 762mm + 25mm = 787mm from source to plane. Small but worth being explicit about.

### Issue 4: simulate_befuddled.py accumulates version-locked filenames
Each new version adds another hardcoded exclusion to the assert guard and hardcoded path constants. This is fragile — if we run v5, v6, etc. the file needs manual edits. Better approach: pass version as argument or auto-detect from git tag.

### Issue 5: caustic_befuddled_v4.png not yet compared to v1
We have both renders but haven't done a side-by-side quality analysis. A longer focal length flattens the surface and should produce a slightly different caustic character (less concentrated, potentially more uniform coverage). Worth comparing SSIM and brightness before committing to CNC.

---

## Questions for Claude Chat

1. **Does the caustic quality change meaningfully with focalLength?** The v1 (f=0.2m) and v4 (f=0.75m) renders exist. Are there physics-based reasons the longer throw would produce a better or worse caustic pattern on the wall?

2. **Is 0.18mm dome margin acceptable for the Blue Elephant 1325?** NK105 controller Z resolution and material flatness tolerance determine whether this is safe.

3. **Should we add a sidecar JSON from the Julia solver** to pass physical parameters (focalLength, artifactSize) to downstream Python scripts automatically?

---

## Focal Length Calibration Data (for future reference)

All runs used: befuddled cow 1024px input, 1024×1024 solver grid, artifactSize=0.1m, IOR=1.49

```
f=0.20m: Z_min=-19.531mm  Z_max=14.508mm  dome=34.04mm
f=0.30m: Z_min=-19.531mm  Z_max=10.313mm  dome=29.84mm
f=0.60m: Z_min=-19.531mm  Z_max= 6.129mm  dome=25.66mm
f=0.75m: Z_min=-19.531mm  Z_max= 5.293mm  dome=24.82mm
```

Z_min is constant — set by solidifier, not focalLength.
Z_max decreases with focalLength at diminishing rate.
Rule of thumb: need f ≥ 0.75m to fit 1" acrylic at 1024px with befuddled cow image.
