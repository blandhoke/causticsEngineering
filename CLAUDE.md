# CLAUDE.md — CausticsEngineering
# Auto-accept all edits unless flagged CONFIRM REQUIRED.
# Do not ask permission for file writes, script runs, or plot regeneration.
# Ask only before: deleting cached .npy files, modifying Julia source, or
# running the full ray trace simulation from scratch (slow).

## What This Project Is
Julia-based caustic lens design pipeline. The Julia solver takes a target image
and outputs a 3D mesh (OBJ) of a refractive acrylic lens surface. When light
passes through the physical CNC-milled lens, it projects the target image as a
caustic pattern on a surface below.

Collaborator Leslie King runs a separate pipeline (ShapeFromCaustics/ma.py).
Her README, parameters, and black-background rules apply ONLY to her process.
Do not apply her settings to this project.

## Directory Layout
/Users/admin/causticsEngineering/
  run.jl                      <- Julia entry point. Edit target image path here.
  src/
    CausticsEngineering.jl    <- Module definition
    create_mesh.jl            <- Core solver. focalLength=0.2 hardcoded line 878.
    utilities.jl
  examples/
    original_image.obj        <- Water drop lens mesh (first test)
    cow render.jpg            <- Current target image (note: space in filename)
    caustic_simulated.png     <- Water drop forward ray trace (reference, DO NOT OVERWRITE)
    caustic_cow.png           <- Cow caustic v1 (upside down — ignore)
    caustic_cow_v2.png        <- Cow caustic v2 (corrected orientation — current best)
    cow_accum.npy             <- Cached ray hit accumulator for cow (DO NOT DELETE)
    cow_meta.npy              <- Cached bounds metadata for cow (DO NOT DELETE)
  simulate_caustic.py         <- Water drop forward ray trace script
  simulate_cow.py             <- Cow forward ray trace script (use cow_accum.npy cache)
  render_caustics.py          <- Blender/Cycles script (outdated, do not use)
  render_caustics_bdpt.py     <- LuxCore BDPT attempt (incomplete)
  CAUSTICS_CONTEXT.md         <- Full Blender MCP session notes (reference)
  CLAUDE.md                   <- This file

## Key Physical Parameters (Julia solver)
  focalLength = 0.2m          <- hardcoded in create_mesh.jl line 878
  IOR = 1.49                  <- acrylic/PMMA
  Light model: point source at focalLength above lens top face
  Lens size: ~0.1m x 0.1m
  CNC machine: Blue Elephant 1325, NK105 controller

## Confirmed Working: Forward Ray Trace Pipeline
The Python forward ray trace is the ground truth verification method.
DO NOT use Blender Cycles or LuxCore for pattern verification — neither converges.

simulate_cow.py workflow:
  - Loads examples/original_image.obj (or any OBJ)
  - Traces rays through mesh via Snell's law (IOR=1.49, focalLength=0.2)
  - Caches results to cow_accum.npy + cow_meta.npy
  - Replot only: just re-run script, it loads cache automatically
  - Output: caustic_cow_v2.png

To replot without re-simulating: run simulate_cow.py as-is (cache auto-loads).
To force re-simulation: delete cow_accum.npy and cow_meta.npy first (CONFIRM REQUIRED).

## Blender OBJ Import (confirmed fix — do not change)
  bpy.ops.wm.obj_import(filepath=OBJ_PATH, forward_axis='Y', up_axis='Z')
Blender version: 4.3.2
Blender 4.3 caustic API:
  light.cycles.is_caustics_light = True
  lens.cycles.is_caustics_caster = True
  plane.cycles.is_caustics_receiver = True

## LuxCore Status
Installed on disk, pyluxcore binary not downloaded.
To activate: Blender UI -> Edit -> Preferences -> Extensions -> BlendLuxCore -> Enable.
This is a manual one-time click — cannot be scripted. Low priority for now.

## Current Problem: Caustic Geometry Mismatch
caustic_cow_v2.png shows the cow is recognizable but with wrong tonality.
Bright energy concentrates at edges/outlines rather than bright image areas.
The caustic looks like an edge-detected version of the original.

Suspected causes (investigate in this order):
  1. Target image not preprocessed for caustic input — photographic portraits
     have complex mid-tone gradients the solver encodes as surface curvature,
     producing edge-enhancement rather than brightness matching.
  2. Solver encodes gradients not absolute brightness — physically inherent,
     may need high-contrast near-binary input image to get clean output.
  3. Quantitative analysis not yet done — run SSIM comparison, edge map
     overlay, and inverted-original comparison before drawing conclusions.

## Next Tasks (do these in order, no permission needed)
1. Run quantitative comparison between cow_render.jpg and caustic_cow_v2.png:
   - SSIM score after normalizing to same size/grayscale
   - Side-by-side: caustic vs contrast-inverted original
   - Edge map of original overlaid on caustic
   - Save as examples/comparison_analysis.png

2. Test with a simpler high-contrast target image:
   - Bold shape, dark background, bright subject, no photographic gradients
   - Place in examples/ and update run.jl to point to it
   - Run julia run.jl to generate new OBJ
   - Run forward ray trace, save as caustic_simple_test.png

3. If geometry mismatch persists after simple image test:
   - Investigate create_mesh.jl for image preprocessing assumptions
   - Check if solver expects inverted image (dark=bright caustic)
   - Check artifactSize parameter effect on output quality

## Running the Julia Solver
  cd /Users/admin/causticsEngineering
  julia run.jl
  Output: examples/original_image.obj (overwrites — rename first if needed)

## Python Dependencies
  pip install numpy scipy matplotlib torch tqdm scikit-learn pillow trimesh scikit-image

## DO NOT (ever, without explicit user instruction)
- Delete opt_weights.npy (Leslie's pipeline — not even in this directory)
- Overwrite caustic_simulated.png (reference render)
- Overwrite cow_accum.npy or cow_meta.npy without CONFIRM REQUIRED flag
- Modify create_mesh.jl or utilities.jl without flagging it first
- Use Cycles for caustic verification
- Apply Leslie's pipeline parameters to this project

## Claude Chat / Blender MCP
Claude Chat (browser) has live Blender MCP access for scene inspection.
Use Claude Chat for: viewport screenshots, material tweaks, geometry debugging.
Use Claude Code (here) for: everything else.
Handoff file: CAUSTICS_CONTEXT.md
