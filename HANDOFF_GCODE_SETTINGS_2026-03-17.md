# G-code Settings Handoff — Caustic CNC Export
**Date:** 2026-03-17  
**Session:** CAUSTICFORGE v1.1 pipeline validation on inkbrush/normal mesh  
**Status:** ✅ PIPELINE VALIDATED — G-code generated and verified

---

## Mesh Facts (inkbrush/normal)

| Property | Value |
|---|---|
| Source | `/Users/admin/causticsEngineering/Final cows/inkbrush/normal/mesh.obj` |
| Grid | 513 × 513 regular heightfield |
| Vertices | 526,338 (263,169 caustic surface + 263,169 flat base slab) |
| Native XY span | 0.10000 m |
| Native Z relief | 0.000964 m (caustic surface only) |
| Scale to 8"×8" | **2.032×** (uniform XYZ — preserves surface normals for caustic optics) |
| Physical XY | 8.000" × 8.000" (203.2mm × 203.2mm) |
| Physical relief | **1.959mm = 0.0771"** (caustic surface only) |
| Full slab Z span | 44.8mm (includes flat base — not relevant for CNC) |

### ⚠ Key Finding: Relief is 1.96mm, not 25mm
The mesh includes a flat base slab. The caustic surface relief is only **1.96mm (0.077")**.  
1" acrylic stock is more than sufficient. Do NOT set cut_depth to 1.75".

---

## Blender Import + Orient Procedure

```python
# 1. Import
bpy.ops.wm.obj_import(
    filepath="/Users/admin/causticsEngineering/Final cows/inkbrush/normal/mesh.obj",
    forward_axis='Y',
    up_axis='Z'
)

# 2. Scale to 8"×8" (0.2032m)
obj = bpy.data.objects['mesh']
SCALE = 0.2032 / 0.10000  # = 2.032
obj.scale = (SCALE, SCALE, SCALE)
bpy.ops.object.transform_apply(scale=True)

# 3. Position: XY origin at front-left corner, Z=0 at dome peak
# (dome peak is Z_max = 0.0, cuts go negative)
# After scale, min X/Y ≈ 0 already — just apply transform
bpy.ops.object.transform_apply(location=True)

# 4. Heightfield extraction (numpy, fast):
vf = np.zeros(len(obj.data.vertices)*3, dtype=np.float64)
obj.data.vertices.foreach_get('co', vf)
v = vf.reshape(-1,3)
top = v[263169:]   # second half = caustic surface
z_grid = top[:,2].reshape(513, 513)  # Z in metres
```

---

## Confirmed G-code Settings

### Finishing Pass (1/16" ball nose)

| Parameter | Value | Notes |
|---|---|---|
| Bit | 1/16" (0.0625") ball nose 2-flute carbide | |
| Stepover | **0.005"** (8% of dia) | Locked — not user-adjustable |
| Feed | **72 IPM** (Normal) / **100.8 IPM** (Superfast) | |
| Plunge feed | **10 IPM** | Used on steep descents (>5 thou drop) |
| Rapid/positioning | **180 IPM** (G01 — no G00 on NK105) | |
| Spindle | **18,000 RPM** | |
| Safe height | **0.200"** | Adequate for 0.077" relief |
| Cut depth | **0.0810"** (= 1.05 × 0.0771" relief) | 5% margin |
| Approach clearance | 0.050" above surface | Before each row descent |
| Retract threshold | 0.010" | Mini-lift only if surface rises > this |
| Stay-low | Yes — skips safe height retract when adjacent rows match | |

### Roughing Pass (1/4" ball nose)

| Parameter | Value |
|---|---|
| Bit | 1/4" (0.25") ball nose 2-flute carbide |
| Stepover | **0.100"** (40% of dia) |
| DOC per level | **0.050"** |
| Feed | **144 IPM** (Normal) / **201.6 IPM** (Superfast) |
| Plunge | **20 IPM** |
| Stock to leave | **0.010"** for finishing |
| Z levels | 2 levels (0.050" + 0.031") for 0.081" total |
| Entry | Edge of stock — no plunges into material |

---

## Machine Time Estimates (8"×8" stock)

| Bit | Stepover | Rows | Normal | Superfast |
|---|---|---|---|---|
| 1/8" ball nose | 0.0125" | 640 | ~54 min | ~38 min |
| **1/16" ball nose** | **0.005"** | **1,601** | **~187 min** | **~133 min** |
| 1/32" ball nose | 0.003125" | 2,560 | ~538 min | ~384 min |

**1/16" is the recommended bit** — analysis confirmed feature radius safely above 1/32nd diameter.

---

## G-code Dialect (NK105 / Weihong / Blue Elephant 1325)

- **No G00** — all moves use G01 (NK105 does not safely handle G00 in this config)
- **F on every G01 line** — controller does not cache modal F between blocks
- **G20** — inch mode
- **G54** — work offset
- **G17 G90** — XY plane, absolute coords
- **IJK arcs only** — R-format causes controller errors (confirmed from FloorForge work)
- **No R-format arcs** in finishing pass (all linear G01 — no arcs needed for raster)

---

## Test Output File

```
/Users/admin/causticsEngineering/test_caustic_finish.nc
```

- **Lines:** 646,829  
- **G01 moves:** 642,001  
- **File size:** ~22MB  
- **Rows:** 1,601 at 0.005" stepover  
- **Verified:** correct G54/G20/G17/G90 header, F on every line, no G00, M05/M30 footer  

---

## Known Issues / Next Steps

1. **CAUSTICFORGE surface analysis unit bug** — analysis reports relief in metres labelled as inches. Fix: multiply `relief_in` by 39.3701 in `analyse_surface()`. Does not affect G-code output.

2. **BVH ray_cast timeout** — Blender 4.x removed `Mesh.ray_cast()`; replaced with BVH tree approach but 526k-face BVH build exceeds MCP timeout. Fix: use numpy heightfield directly from vertex array (implemented in session, should be merged into addon).

3. **Stepover % display bug** — panel shows "0% dia" due to integer formatting of 8%. Fix: use `{BIT_DIA*0.08*100:.0f}` → should be `{0.08*100:.0f}`.

4. **Production meshes** — once 16-quadrant block experiment meshes are complete, use same import/scale procedure. Each 4"×4" quadrant will use same settings with `stock_width=4.0, stock_height=4.0`.

---

## CAUSTICFORGE Addon Location

```
/Users/admin/Library/Application Support/Blender/4.3/scripts/addons/causticforge_v1.py
```

Next version should incorporate the numpy heightfield path (bypassing BVH entirely for regular grid meshes).
