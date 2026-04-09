# HANDOFF — Blender Production Layout + CAUSTICFORGE G-code Strategy
**Date:** 2026-04-08
**From:** Claude Code
**To:** Claude Chat (Blender MCP)

---

## Goal

Arrange all available production-ready caustic lens meshes in Blender for G-code export via the CAUSTICFORGE v1.3 addon. The user (Bland) wants to strategize which meshes to cut, how to lay them out on stock, and generate G-code for the Blue Elephant 1325 CNC.

---

## Available Meshes — Complete Inventory

### 5 Image Variants (the "Final Cows")

These are the five solver input images that were batch-processed through the pipeline. Each exists at multiple resolutions.

| Image | Description | Caustic Sharpness | Edge Correlation | Rank |
|-------|-------------|-------------------|------------------|------|
| **nikon** | Nikon camera photograph of cow | 0.130 | +0.219 | #1 |
| **woodblock** | Woodblock print style | 0.120 | +0.186 | #2 |
| **banknote** | Banknote engraving style | 0.107 | +0.213 | #3 |
| **inkbrush** | Ink brush painting style | 0.107 | +0.150 | #4 |
| **charcol** | Charcoal drawing style | 0.104 | +0.208 | #5 |

Source images live in `Final cows/` as PNG files (banknote.png, charcol.png, inkbrush.png, Nikon.png, woodblock2.png).
INKFORGE/ directory has alternate processing variants (charcol.png, greyish.png, inversion.png, microcontrast.png, woodblock.png, painterly.png).

### Mesh Files by Resolution Tier

#### NORMAL (512px solver, ~526k faces, ~50MB) — good for 8" pieces
| Image | Path | Faces | Native XY Span | Z Relief |
|-------|------|-------|-----------------|----------|
| nikon | `Final cows/nikon/normal/mesh.obj` | 1,052,672 | 0.1001m | 23.1mm |
| banknote | `Final cows/banknote/normal/mesh.obj` | 1,052,672 | 0.1001m | 22.1mm |
| woodblock | `Final cows/woodblock/normal/mesh.obj` | 4,202,496 | 0.2001m | 22.6mm |
| charcol | `Final cows/charcol/normal/mesh.obj` | 4,202,496 | 0.2001m | 23.2mm |
| inkbrush | `Final cows/inkbrush/normal/mesh.obj` | 1,052,672 | 0.1000m | 22.1mm |

Note: woodblock and charcol "normal" meshes are actually 1024px (2.1M faces, ~0.2m span). The others are true 512px.

#### FAST (256px solver, ~131k faces, ~12MB) — for prototyping
All 5 images exist at `Final cows/{name}/fast/mesh.obj`, each ~12MB.

#### PROD (1024px solver, ~2.1M faces, ~206MB) — for 24" production
| Image | Path | Faces | Native XY Span |
|-------|------|-------|-----------------|
| charcol | `Final cows/charcol/prod/mesh.obj` | 4,202,496 | 0.2001m |

Only charcol has a dedicated prod mesh. The woodblock/charcol "normal" meshes are also 1024px.

### Pre-Scaled Physical Lens OBJs (CNC-ready, axis-corrected)

These have already been run through `make_physical_lens.py` — axis-corrected, Z=0 at dome peak, XY origin at front-left corner.

| File | Size | Physical Dims | Relief | Stock Needed |
|------|------|---------------|--------|-------------|
| `Final cows/charcol/24in_standard/physical_lens_24x24.obj` | 170MB | 24"x24" (0.6096m) | 6.86mm (0.270") | 1" acrylic |
| `Final cows/charcol/24in_deep/physical_lens_24x24_deep.obj` | 170MB | 24"x24" (0.6096m) | 8.50mm (0.335") | 1" acrylic |
| `examples/physical_lens_24x24.obj` | 170MB | 24"x24" (0.6096m) | 6.86mm (0.270") | 1" acrylic |
| `examples/physical_lens_8x8.obj` | 41MB | 8"x8" (0.2032m) | 4.48mm (0.176") | 1" acrylic |

The `examples/physical_lens_24x24.obj` appears to be a copy of the charcol/24in_standard version.

### Block/Quadrant Meshes (experimental — 4"x4" tiles)

These were from a quadrant-tiling experiment. Four quadrants per block, designed to tile into 8"x8".

| Block | Quadrants | Combined File | Resolution |
|-------|-----------|---------------|------------|
| block1 | q1-q4 (each ~2.9MB) | `block1_combined_8x8.obj` (9.7MB) | HYPER (128px) |
| block2 | q1-q4 (each ~2.9MB) | `block2_combined_8x8.obj` (9.7MB) | HYPER (128px) |
| block3 | q1-q4 (each ~2.9MB) | `block3_combined_8x8.obj` (9.7MB) | HYPER (128px) |
| block4 | q1-q4 (each ~2.9MB) | `block4_combined_8x8.obj` (9.7MB) | HYPER (128px) |

block3_normal and block4_normal also exist at NORMAL resolution (~50MB each, only q2/q3 and q3/q4 respectively).

### Other Meshes (research/experimental)

| File | Size | Notes |
|------|------|-------|
| `examples/inkbrush_normal_sobel.obj` | 50MB | Sobel-preprocessed input variant |
| `examples/solver_A_fast_ot_raw.obj` | 37MB | Alternative solver A output |
| `examples/solver_A_fast_ot_physical.obj` | 40MB | Solver A scaled to physical |
| `examples/solver_B_schwartzburg_raw.obj` | 2.2MB | Schwartzburg solver output |
| `examples/solver_B_schwartzburg_physical.obj` | 2.3MB | Schwartzburg scaled |
| `examples/diffrender/optimized_lens.obj` | 169MB | Differentiable rendering optimization |
| `Final cows/inkbrush/normal/mesh_trimmed.obj` | 21MB | Trimmed variant (base slab removed) |

---

## CAUSTICFORGE v1.3 Addon — Current State

**Location:** `/Users/admin/Library/Application Support/Blender/4.3/scripts/addons/causticforge_v1.py`
**Panel:** View3D > N-Panel > CAUSTICFORGE
**Version:** 1.3.0

### What It Does
1. **Analyse Surface** — Reads mesh as numpy heightfield, auto-detects bimodal structure (separates flat base slab from caustic surface), computes curvature, recommends bit, estimates machine time
2. **Export G-code** — Generates roughing + finishing passes as NK105-compatible G-code

### Bit Presets Available
| Bit | Diameter | Stepover | Feed (Normal) | Use Case |
|-----|----------|----------|---------------|----------|
| 1/4" Ball Nose | 0.250" | 60% (rough) / 10% (finish) | 144 IPM | 24" pieces, roughing |
| 1/8" Ball Nose | 0.125" | 10% = 0.0125" | 100 IPM | 8" pieces, medium finish |
| 1/16" Ball Nose | 0.0625" | 8% = 0.005" | 72 IPM | Fine finish |
| 1/32" Ball Nose | 0.03125" | 10% = 0.003125" | 40 IPM | Ultra-fine (rarely needed) |

### Key Features
- Auto-detect Y/Z axis swap from pipeline (corrects in-memory)
- Non-uniform scale guard (blocks export if XYZ scale not equal)
- F code on every G01 line (NK105 requirement)
- No G00 rapids (all G01 moves)
- Edge-entry roughing (no plunges into stock)
- Stay-low finishing (minimizes retracts)

### Current Defaults
- Stock: 24"x24"x1" (updated from 8"x8" for production)
- Finish bit: 1/4" ball nose (appropriate for 24" piece)
- Output: `/Users/admin/causticsEngineering/inkbrush_24in_finish.nc`

---

## Blender Import Procedure

```python
# For pre-scaled physical_lens OBJs (already axis-corrected):
bpy.ops.wm.obj_import(
    filepath="path/to/physical_lens_24x24.obj",
    forward_axis='Y',
    up_axis='Z'
)
# No rotation or scaling needed — ready for CAUSTICFORGE immediately.

# For raw solver meshes (mesh.obj from Final cows):
# Import same way, then scale uniformly to target size.
# CAUSTICFORGE auto-detects and corrects Y/Z swap.
```

---

## Production Decisions Needed (For Claude Chat + Bland to Strategize)

### 1. Which image(s) to cut first?
- **nikon** ranks #1 on sharpness but has known SOR banding in lower face/neck area
- **woodblock** ranks #2, cleanest caustic with no known artifacts
- **charcol** is the only image with a full 24" pre-scaled physical lens OBJ ready to go (two variants: standard 6.9mm dome, deep 8.5mm dome)
- **inkbrush** has the most validated G-code (multiple test cuts exported)
- **banknote** ranks #3, no known issues

### 2. What size(s)?
- **24"x24"** — Production target. Only charcol has pre-scaled OBJ. Others need `make_physical_lens.py` run.
- **8"x8"** — Test cut size. `examples/physical_lens_8x8.obj` exists (image TBD — check which solver input produced it)
- **4"x4" quadrant tiles** — Experimental block meshes exist at HYPER resolution (low quality)

### 3. Bit strategy for 24" piece?
- 1/4" ball nose finish: ~41 min, 0.100" stepover — coarser but fast
- 1/8" ball nose finish: ~54 min at 8", scales to ~3+ hrs at 24" — finer detail
- Current recommendation from prior sessions: 1/4" for 24" (mesh cell size 0.023" is finer than 1/4" stepover)

### 4. Layout strategy for multiple pieces?
If cutting multiple images on separate stock sheets, each gets its own G-code file. If tiling multiple small pieces on one sheet, CAUSTICFORGE doesn't currently support multi-object export — each would need separate export with origin offsets.

### 5. Stock availability?
- 1" cast acrylic is standard (25.4mm)
- 1.125" available? Would allow deeper dome (~24.8mm physical) and ~50% higher edge correlation
- Current 24" charcol dome: 6.9mm standard / 8.5mm deep — both well within 1" stock

---

## Existing G-code Files (already exported)

| File | Image | Size | Bit | Lines | Notes |
|------|-------|------|-----|-------|-------|
| `inkbrush_24in_finish.nc` | inkbrush | 24"x24" | 1/4" | — | CAUSTICFORGE v1.3 |
| `inkbrush_finish_v12.nc` | inkbrush | 8"x8" | 1/8" | 844,230 | Production candidate |
| `inkbrush_8x8_finish.nc` | inkbrush | 8"x8" | — | — | Earlier version |
| `test_caustic_finish.nc` | (test) | — | 1/16" | 646,829 | 0.005" stepover |
| `test_caustic_v12.nc` | (test) | — | — | — | 513x513 grid test |

---

## Machine Reference

| Parameter | Value |
|-----------|-------|
| Machine | Blue Elephant 1325 |
| Controller | NK105 (Weihong) |
| Work area | ~1300mm x 2500mm (51" x 98") |
| G-code dialect | G54, G20 (inches), G17 G90, no G00, F on every G01 |
| Spindle | 18,000 RPM |
| Accuracy | +/- 0.03mm |
| Stock | 1" cast acrylic (PMMA, IOR 1.49) |

---

## What Claude Chat Should Do Next

1. **Open `causticforge_v1.blend`** in Blender — check what's already in the scene
2. **Review which meshes Bland wants to cut** — the 5 image variants are ranked above
3. **Import the chosen physical_lens OBJ(s)** into the Blender scene
4. **Arrange on stock** — position for CNC origin (front-left corner, Z=0 at dome peak)
5. **Run CAUSTICFORGE Analyse** on each mesh to confirm relief, bit recommendation, machine time
6. **Discuss bit strategy** with Bland — 1/4" vs 1/8" vs 1/16" tradeoffs
7. **Export G-code** when layout is confirmed

If new physical_lens OBJs are needed for images other than charcol (e.g., nikon, woodblock, banknote, inkbrush at 24"), ask Claude Code to run `make_physical_lens.py` with the appropriate mesh and target size.

---

## Files Reference (Quick Copy-Paste Paths)

```
# Pre-scaled 24" OBJs (ready for Blender import):
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/charcol/24in_standard/physical_lens_24x24.obj
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/charcol/24in_deep/physical_lens_24x24_deep.obj

# Pre-scaled 8" OBJ:
/Users/admin/Documents/Claude/causticsEngineering_v1/examples/physical_lens_8x8.obj

# Raw solver meshes (need make_physical_lens.py before CNC):
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/nikon/normal/mesh.obj
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/banknote/normal/mesh.obj
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/woodblock/normal/mesh.obj
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/charcol/normal/mesh.obj
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/inkbrush/normal/mesh.obj

# CAUSTICFORGE addon:
/Users/admin/Library/Application Support/Blender/4.3/scripts/addons/causticforge_v1.py

# Blender scene:
/Users/admin/Documents/Claude/causticsEngineering_v1/causticforge_v1.blend

# Source images:
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/banknote.png
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/charcol.png
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/inkbrush.png
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/Nikon.png
/Users/admin/Documents/Claude/causticsEngineering_v1/Final cows/woodblock2.png
```
