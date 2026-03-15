# Geometry Mismatch Analysis
# Prepared by: Terminal 2 (Claude Code)
# Date: 2026-03-15

---

## Summary

The forward ray trace produces a recognizable but geometrically distorted cow caustic.
The distortion is NOT a random rendering artifact — it is a deterministic coordinate
transform error somewhere in the Julia → OBJ → Python pipeline.

---

## Evidence

### 1. Loss images are correctly oriented; OBJ is not

`quantifyLoss!` in `create_mesh.jl` saves with:
```julia
rgbImg = RGB.(red, green, blue)'
save("./examples/loss_$(suffix).png", ...)
```
The trailing `'` is a Julia matrix transpose. Since the solver operates on
`permutedims(img)` (also a transpose), the two transposes cancel in the loss images,
making them display correctly oriented relative to the original photo.

The OBJ export does NOT apply this correction. `saveObj!` writes node coordinates
directly as (X=node.x, Y=node.y, Z=node.z) without any axis correction.

**Implication:** If the loss images look correct, but the caustic is wrong,
the error is in the OBJ coordinate space, not in the solver itself.

### 2. Row-origin Y-flip is confirmed

Julia `Images.load` returns arrays with row=1 at top. The mesh y-axis goes 1→512
in the same direction (row 1 = mesh y=1). In the OBJ, Y=1 is at the physical
bottom of the 3D coordinate system (math convention, Y increases upward).

This means OBJ Y = image row number, but large row = bottom of image = small Y
in physical space. The image is vertically flipped in 3D.

**Fix applied:** `origin='upper'` in matplotlib → **correct**.

### 3. Horizontal mirror: uncertain

`np.fliplr` was applied to correct a suspected horizontal mirror. The physical
optics of this lens (collimated light, flat-back refraction) do NOT inherently
introduce a left-right mirror. The question is whether `permutedims` introduces one.

For a square image:
- `permutedims` swaps [row, col] → [col, row]
- This is a reflection across the main diagonal (not a left-right or up-down flip)
- Combined with the Y-flip already present, the net transform is:
  diagonal mirror + Y-flip = 90° rotation

**If the caustic is rotated 90°, `np.fliplr` is the wrong fix.**
The correct fix would be either:
- Remove `permutedims` in Julia (no re-solve needed if image is square, but would
  require a re-run to rebuild the OBJ)
- Or in Python: replace `np.fliplr` with `np.rot90(accum, k=?)` — direction TBD

### 4. Solver convergence is real but fine-detail limited

Loss amplitude across iterations:

| Iter | Min    | Max   | Phi conv. step |
|------|--------|-------|----------------|
| 1    | -0.811 | 0.991 | 3546           |
| 2    | -1.275 | 1.182 | 3452           |
| 3    | -1.425 | 1.299 | 3321           |
| 4    | -1.346 | 1.250 | 3210           |
| 5    | -1.401 | 1.274 | 3101           |
| 6    | -1.448 | 1.259 | 2970           |

The loss amplitude is NOT decreasing monotonically — it oscillates around ~1.3 from
iterations 3–6. This is typical of SOR-based mesh optimization that has reached its
effective resolution limit. The coarse 512-grid cannot represent the fine fur texture
in the cow photo. The solver has converged in the sense that the Poisson solve
reaches `max_update < 1e-5` each iteration, but the mesh warp itself oscillates.

**The cow is a hard target.** CLAUDE.md explicitly warns: "Test pipeline with a
high-contrast simple target image (bold shape, no thin lines)."

---

## Suspected Fix Priority

1. **(Highest impact, requires re-run):** Determine correct permutedims handling.
   If a 90° rotation is confirmed, remove `permutedims` from `engineer_caustics`,
   re-run `julia run.jl`, re-run `simulate_cow.py` (delete `cow_accum.npy` first).

2. **(No re-run needed):** If the error is only the Y-flip (origin='upper' already
   applied) and the horizontal mirror (`np.fliplr` already applied), then the
   caustic may be geometrically correct and the remaining distortion is solver-quality
   limited, not a coordinate bug.

3. **(Independent improvement):** Test with a simple high-contrast target (filled
   circle, bold letter, solid triangle) to isolate coordinate errors from image-quality
   limitations. Any rotation/mirror would be immediately obvious on a simple shape.

---

## What Claude Chat Should Check in Blender

Import `examples/original_image.obj` with `forward_axis='Y', up_axis='Z'`.
Apply an emission material with the Z-height mapped to emission strength.
Render a top-down orthographic view.

Expected if coordinate chain is correct:
- Bright emission regions should correspond to bright regions of `cow render.jpg`
  (the background, forehead, muzzle area)
- Dark regions should match the dark regions (ear fur, body shadow)
- Orientation should match the original image (dark ear = upper right from above)

If the emission map is rotated, mirrored, or transposed relative to the original:
the exact transform seen tells us precisely which correction to apply.

---

## Code Locations

| Issue | File | Line |
|-------|------|------|
| permutedims | `src/create_mesh.jl` | ~855 in `engineer_caustics` |
| Loss transpose-save | `src/create_mesh.jl` | ~379 in `quantifyLoss!` |
| saveObj! (no axis flip) | `src/create_mesh.jl` | ~109 |
| np.fliplr + origin | `simulate_cow.py` | ~149–152 |
