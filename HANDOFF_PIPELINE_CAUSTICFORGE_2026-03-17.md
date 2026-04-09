# HANDOFF — Pipeline Physical Lens → CAUSTICFORGE Integration
# Date: 2026-03-17
# From: Claude Chat (Blender MCP)
# To: Claude Code

---

## Summary

The physical lens pipeline currently outputs an OBJ that requires manual
orientation before CAUSTICFORGE can export G-code. This handoff asks Claude
Code to fix the pipeline end so the OBJ arrives in Blender ready to use,
and documents the CAUSTICFORGE changes Claude Chat is making in parallel.

---

## Current Pipeline End (what Claude Code needs to fix)

### What the pipeline does now:

1. Julia solver writes:  `examples/original_image.obj`
2. `make_physical_lens.py` reads it, scales uniformly to 8"x8", writes:
   `examples/physical_lens_8x8.obj`
3. User imports `physical_lens_8x8.obj` into Blender manually
4. **Problem:** The OBJ arrives with Y and Z axes swapped — the lens stands
   on its edge (Z is the 8" length axis, Y is the ~2mm relief axis) instead
   of lying flat (X=width, Y=length, Z=up/relief)
5. User must manually rotate -90° around X, then reposition Z peak to 0 and
   XY min corner to origin before CAUSTICFORGE can use it

### What Claude Code should add to `make_physical_lens.py`:

Add an axis-correction step at the end of the script that:

1. After scaling, detects if the mesh is Y/Z swapped by comparing Y span vs Z span
   - If Z span >> Y span (current broken state): rotate vertices -90° around X axis
     (swap Y and Z: new_y = old_z, new_z = -old_y)
   - After rotation: X=width (~0.2032m), Y=length (~0.2032m), Z=relief (~0.002m)

2. Separates the two vertex clusters (bimodal mesh):
   - Lower cluster (flat base slab): constant Z, ignore for positioning
   - Upper cluster (caustic surface): find Z_max = peak

3. Repositions so:
   - X_min = 0 (front-left corner at origin)
   - Y_min = 0
   - Z_peak = 0 (stock surface, cuts go negative)

4. Writes the corrected OBJ to `examples/physical_lens_8x8.obj` (same path)

5. Appends a summary block to the output:

```
── CAUSTICFORGE-READY ────────────────────────────────────
  Axis orientation: X=width Y=length Z=up (CNC convention) ✓
  XY origin: front-left corner at (0, 0) ✓
  Z=0 at caustic peak, cuts go negative ✓
  Caustic relief: [VALUE]mm = [VALUE]"
  Cut depth (relief + 5%): [VALUE]"
  Ready to import into Blender — no manual rotation needed
```

### Exact rotation math (for reference):

```python
# Detect Y/Z swap: if Z span > Y span by 5x or more, swap is present
y_span = verts[:,1].max() - verts[:,1].min()
z_span = verts[:,2].max() - verts[:,2].min()
if z_span > y_span * 5:
    # Rotate -90 degrees around X: Y → -Z, Z → Y
    old_y = verts[:,1].copy()
    old_z = verts[:,2].copy()
    verts[:,1] = old_z     # new Y = old Z (the 8" axis)
    verts[:,2] = -old_y    # new Z = -old Y (the ~2mm relief axis, now pointing up)

# Find upper cluster (caustic surface) — Z bimodal split
z = verts[:,2]
z_mid = (z.min() + z.max()) / 2
upper_z = z[z >= z_mid]
z_peak = upper_z.max()

# Shift to CNC origin
verts[:,0] -= verts[:,0].min()
verts[:,1] -= verts[:,1].min()
verts[:,2] -= z_peak   # Z=0 at peak
```

---

## Affected Files

- `make_physical_lens.py` — add axis correction + reposition at end
- `run_pipeline_normal.sh` — no changes needed (calls make_physical_lens.py already)
- `run_pipeline_fast.sh` — no changes needed
- `run_quad_pipeline.sh` — no changes needed

---

## What Claude Chat is Patching in CAUSTICFORGE in Parallel

Claude Chat is updating CAUSTICFORGE v1.2 → v1.3 with these changes:

### 1. Auto-detect corrected vs uncorrected OBJ

CAUSTICFORGE `build_heightfield()` will detect the Y/Z swap condition and
auto-correct in-memory if it encounters it — this is the fallback for any
OBJ that wasn't run through the updated `make_physical_lens.py`.

Detection: if Z span > Y span * 5 after import, swap Y/Z before building heightfield.

### 2. Auto-populate target object

When the N-Panel opens, if `bpy.data.objects` contains a mesh named
`physical_lens_8x8` and no target is set, auto-assign it.

### 3. Smarter default output path

Default output path changes from `//caustic_cut.nc` to:
`/Users/admin/causticsEngineering/inkbrush_finish_v12.nc`

### 4. Auto-detect project directory

On analyse, CAUSTICFORGE checks if the target object was imported from a
known project path and suggests the output path accordingly.

### 5. Post-analysis status display

Analysis result panel shows a clear CNC-READY / NOT-READY status line at top:

```
✓ CNC READY — export when bit confirmed
  Relief: 2.055mm (0.081")  Cut depth: 0.085"  Bit: 1/8" ball nose
  Machine time: ~54min Normal / ~38min Superfast
```

---

## Verification Steps for Claude Code

After patching `make_physical_lens.py`, run:

```bash
cd /Users/admin/causticsEngineering
python3 make_physical_lens.py
```

Then import `examples/physical_lens_8x8.obj` into Blender and verify:
- Dimensions panel shows X≈8", Y≈8", Z≈0.08"
- Object lies flat (not standing on edge)
- Object origin is at front-left corner
- Z=0 at top surface, negative below

Expected values for inkbrush normal mesh:
- X: 0 → 7.999"
- Y: 0 → 8.000"
- Z: -0.081" → 0.000"
- Caustic relief: 2.055mm = 0.0809"
- Cut depth (auto): 0.0850"

---

## Files Claude Code Should NOT Touch

- `/Users/admin/Library/Application Support/Blender/4.3/scripts/addons/causticforge_v1.py`
  (Claude Chat owns this file — edits in progress)
- Any `*.nc` G-code files
- `Final cows/` directory

---

## Current G-code Status

`inkbrush_finish_v12.nc` was successfully exported this session:
- 844,230 lines / 29.6MB
- 1/8" ball nose, 0.01250" stepover, 100 IPM Normal
- Caustic relief: 2.055mm, cut depth: 0.08497"
- NK105 compliant ✓

This file is the current production candidate pending bit selection confirmation.
