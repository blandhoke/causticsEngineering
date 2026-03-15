# CLAUDE.md — CausticsEngineering
# Auto-accept all edits unless flagged CONFIRM REQUIRED.
# Last updated: 2026-03-15 — synthesized from full multi-session history
# Written by: Claude Chat (Sonnet 4.6) via filesystem MCP

---

## What This Project Is

A Julia-based caustic lens design pipeline. A target image is fed to a
Successive Over-Relaxation (SOR) Optimal Transport solver which warps a mesh
to design a refractive acrylic lens surface (OBJ). When sunlight passes
through the CNC-milled lens, it projects the target image as a caustic
pattern on the floor below.

Physical output: CNC-milled cast acrylic on a Blue Elephant 1325 / NK105.

Collaborator Leslie King runs a SEPARATE pipeline (ShapeFromCaustics/ma.py).
Her README, parameters, and black-background rules apply ONLY to her process.
NEVER apply her settings to this project.

---

## Directory Layout

/Users/admin/causticsEngineering/
  CLAUDE.md                         <- this file (update after major runs)
  HANDOFF_NEW_CHAT.md               <- session handoff for new Claude Chat instances
  CAUSTICS_CONTEXT.md               <- Blender MCP session notes (reference)
  run.jl                            <- Julia entry point — edit image path here
  src/
    CausticsEngineering.jl          <- module definition
    create_mesh.jl                  <- core SOR solver (see KEY INTERNALS below)
    utilities.jl                    <- do not modify without flagging
  examples/
    original_image.obj              <- CURRENT active lens mesh (solver overwrites this)
    original_image_cow_v3.obj       <- preserved cow mesh backup (do not delete)
    befuddled_cow_solver_input.jpg  <- current active solver input
    "befuddled cow 1.jpg"           <- user's Photoshop-curated input (DO NOT MODIFY)
    "cow render.jpg"                <- original cow photo (do not delete)
    caustic_simulated.png           <- water drop reference (DO NOT OVERWRITE -- ever)
    caustic_cow_v2.png              <- cow v2, centroid ray (reference)
    caustic_cow_v3.png              <- cow v3, 4-pass Gaussian splat (DO NOT OVERWRITE)
    cow_accum.npy                   <- ray trace cache for cow v3 (DO NOT DELETE)
    cow_meta.npy                    <- bounds cache for cow v3 (DO NOT DELETE)
    befuddled_accum.npy             <- ray trace cache for befuddled run
    befuddled_meta.npy              <- bounds cache for befuddled run
  simulate_cow.py                   <- cow v3 ray trace (DO NOT MODIFY -- it's the template)
  simulate_befuddled.py             <- befuddled run script (copy of simulate_cow.py)
  simulate_caustic.py               <- water drop reference script (do not modify)

NOTE: make_physical_lens.py does NOT exist yet. It must be written from scratch.
      See PHYSICAL SCALING section below for the required math.

---

## Key Physical Parameters

  focalLength    = 0.2m         hardcoded in create_mesh.jl engineer_caustics()
  artifactSize   = 0.1m         hardcoded in create_mesh.jl engineer_caustics()
                                 (this is the solver's native lens span)
  IOR            = 1.49         cast acrylic / PMMA -- in solver AND simulate_*.py
  Grid           = 512x512      const grid_definition at top of create_mesh.jl
  CNC machine    = Blue Elephant 1325, NK105 controller
  Target lens    = 8"x8" x 1" cast acrylic

---

## Solver Key Internals (read before touching create_mesh.jl)

The solver pipeline in engineer_caustics():
  1. Converts image to grayscale, permutedims (benign for square images -- do not remove)
  2. Creates a squareMesh of size (width+1) x (height+1)
     -> Input image dimensions directly determine mesh node count
     -> 512px input -> 513x513 mesh nodes -> ~525k faces
     -> 1024px input with grid_definition=512 -> Julia uses full 1024px image size
        (grid_definition constant is DECLARED but not used in engineer_caustics;
         mesh size = image size. A 1024px image produces a 1025x1025 mesh.)
  3. Normalizes image energy to match mesh area (boost_ratio)
  4. Runs 6 SOR iterations (oneIteration x 6) -- loss stalls after ~it3 at 512px
  5. findSurface() computes height field via Snell's law refraction geometry
  6. solidify() closes the mesh (adds flat bottom, edge walls)
  7. saveObj!() writes examples/original_image.obj
     scale = 1/512 * artifactSize = 1/512 * 0.1 = ~0.000195 m/node
     -> All vertex coords in meters (0.0 to ~0.1m range)
     -> Z range typically -0.02m to +0.007m (dome ~26mm at 512px input)

IMPORTANT: grid_definition = 512 is declared but NOT used by engineer_caustics().
The mesh resolution is set by the input IMAGE dimensions in run.jl.
A 1024px input image will produce a ~2.1M face mesh automatically.
To use 512 grid with a 1024px image: resize image to 512px in run.jl before loading.
CONFIRM REQUIRED before modifying create_mesh.jl.

---

## Forward Ray Trace Pipeline (simulate_*.py)

Current version: simulate_cow.py (v3 -- all improvements applied, use as template)

Algorithm:
  1. Parse OBJ -> vertices, faces
  2. Identify top-surface faces (cross product Z > 0)
  3. For N_PASSES iterations:
     a. Jittered barycentric sampling (random point within each triangle)
     b. Ray from point source -> face centroid via Snell's law (IOR 1.49)
     c. Refract at flat bottom surface (back to air)
     d. Intersect with receiver plane at focal distance below lens
     e. Weight: area x cos(theta) / r^2
     f. Gaussian splat onto accumulator (sigma=1.5px, radius=3px kernel)
  4. Divide by N_PASSES (energy conservation)
  5. Normalize, sqrt gamma, plot with sunlight colormap
  6. Optional: scipy gaussian_filter(sigma=0.5) post-process smooth

Parameters (confirmed working):
  N_PASSES     = 4        <- do not reduce; 4x jitter is minimum for clean output
  SPLAT_SIGMA  = 1.5      <- Gaussian splat width (pixels)
  SPLAT_RADIUS = 3        <- kernel half-width (7x7 total kernel)
  IMAGE_RES    = 1024     <- output PNG resolution
  IOR          = 1.49
  FOCAL_DIST   = 0.2

Cache behavior:
  - Cache present -> skip simulation, load instantly, replot only
  - Cache absent -> full simulation (8-15 min at 512px mesh, 4-pass)
  - To replot only: run script as-is (reads cache)
  - To force re-simulation: delete *_accum.npy + *_meta.npy (CONFIRM REQUIRED)

DO NOT use Blender Cycles or LuxCore for caustic verification -- neither converges.

---

## Caustic Physics -- Critical Understanding

The SOR solver encodes GRADIENTS not flat-field brightness:
  - Flat bright regions -> gentle lens surface -> diffuse spread -> DIM caustic
  - Brightness edges/boundaries -> steep curvature -> concentration -> BRIGHT caustic
  - Net result: caustic is an edge/gradient image of the target, not a brightness replica

Confirmed metrics (cow v3, 4-pass Gaussian splat):
  SSIM(caustic, original image)   = 0.0909   (3x better than v2 = 0.030)
  Pearson r(caustic, edges)       = +0.313   (3x stronger than brightness)
  Pearson r(caustic, brightness)  = -0.102
  Mean brightness                 = 0.111    (85% brighter than v2)

Confirmed: the caustic is physically correct. The brightness mismatch is NOT
a simulator bug -- it is correct physics from an unsuitable input image.

---

## Target Image Strategy

BEST:   High-contrast near-binary images (white subject, black background)
GOOD:   Silhouettes, bold line art, logos
POOR:   Photographic images with gradients (produces edge-dominated output)

Option A -- Heavy Gaussian blur preprocessing (CURRENT EXPERIMENT):
  Smooth edges into broad halos before the solver.
  "befuddled cow 1.jpg": contrast-boosted in Photoshop, pure black/white
  removed, 0.5px Gaussian blur applied by user. This is the Option A test.
  Expected: broader fill regions, less edge-dominated output.

Option B -- Feed edge map as target:
  Pre-compute Sobel edge magnitude -> feed to Julia.
  Expected: caustic matches edges explicitly, sharp, won't read as animal.

Option C -- Silhouette / binary:
  White-filled cow on black. All energy inside silhouette boundary.
  Expected: glowing cow shape, clean edges, no interior detail.

---

## Grid Resolution Strategy

  512px input  -> ~525k faces   -> Julia ~5 min   -> ray trace ~8-15 min  -> ITERATION
  1024px input -> ~2.1M faces   -> Julia ~45 min  -> ray trace ~30-40 min -> PRODUCTION

DO NOT decimate the Blender mesh to reduce face count.
  Decimation destroys solver precision. Each vertex encodes a specific
  refractive deflection angle. Blender's decimate merges vertices in ways
  that corrupt the surface normals the physics depends on.

To use 512-equivalent mesh with 1024px image:
  Resize image to 512x512 in run.jl before passing to engineer_caustics().
  This is the correct way to control resolution, not grid_definition.

Current status: using 1024px input image for befuddled cow run.
  -> This will produce a ~2.1M face mesh automatically.
  -> Julia will take ~45 min. Ray trace will take ~30-40 min.
  -> If user wants a quick test: resize image to 512px in run.jl first.

---

## Physical Scaling (make_physical_lens.py -- TO BE WRITTEN)

make_physical_lens.py does NOT exist. When writing it, use this math:

Solver output: native size = artifactSize = 0.1m x 0.1m
  scale in saveObj! = 1/512 * 0.1 = ~0.000195 m/vertex-step

Target physical: 8"x8" = 0.2032m x 0.2032m
Scale factor: 0.2032 / 0.1 = 2.032x (apply to ALL axes: X, Y, and Z)

Physical throw distance:
  solver focalLength = 0.2m at native 0.1m size
  scaled throw = 0.2 x (0.2032 / 0.1) = 0.4064m = ~16"

Script logic:
  1. Read examples/original_image.obj (parse v lines)
  2. Multiply ALL vertex coords (X, Y, Z) by 2.032
  3. Write to examples/physical_lens_8x8.obj
  4. Report: physical XY span, dome height mm, throw distance
  5. WARN if dome height > 25.4mm (exceeds 1" material thickness)

Critical: Z must scale with XY. The refraction angles depend on dZ/dXY ratio.
Scaling only XY would change all surface normals and destroy the caustic pattern.

---

## Running the Julia Solver

  cd /Users/admin/causticsEngineering
  julia run.jl

CONFIRM REQUIRED before running (slow, overwrites examples/original_image.obj).
Always backup first: cp examples/original_image.obj examples/original_image_BACKUP.obj
Edit only the Images.load() line in run.jl to change the target image.

---

## Blender 4.3.2 API (correct names -- wrong names silently fail)

Import:   bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
Caustics: light.cycles.is_caustics_light    = True
          lens.cycles.is_caustics_caster    = True
          plane.cycles.is_caustics_receiver = True

NOT: use_shadow_caustic, is_caustic_catcher  <- silently wrong in 4.3

---

## Permissions Model

Auto-accept (no confirmation needed):
  - Any Python script edits or new script creation
  - Running simulate_*.py (including full re-simulation if cache absent)
  - All analysis scripts and matplotlib output
  - Editing run.jl image path only
  - Writing make_physical_lens.py from scratch
  - Git add + commit

CONFIRM REQUIRED -- ask once, then proceed on yes:
  - Deleting any .npy cache file
  - Any edit to create_mesh.jl or utilities.jl
  - Running julia run.jl (slow, destructive to current OBJ)
  - Running make_physical_lens.py (produces CNC output file)

NEVER -- hard constraints, no exceptions:
  - Delete cow_accum.npy or cow_meta.npy
  - Overwrite caustic_simulated.png
  - Overwrite caustic_cow_v3.png
  - Modify utilities.jl without flagging
  - Apply Leslie King's pipeline parameters to this project
  - Use Blender Cycles for caustic verification
  - Run julia run.jl a second time without explicit re-confirmation

---

## Git Workflow

Before major runs:   git add -A && git commit -m "message"
Revert single file:  git checkout -- <filename>
Revert all:          git checkout -- .

Key commits:
  pre-improvement baseline  -> working state before v3
  2cd0dac                   -> cow v3 (cosine weight, 4-pass, Gaussian splat)

---

## Claude Chat / Blender MCP

Claude Chat (browser) = Blender MCP + research + analysis + prompts for Claude Code
Claude Code (terminal) = simulation, file management, git, Python/Julia execution

Handoff files:
  HANDOFF_NEW_CHAT.md       <- read first in any new Claude Chat session
  HANDOFF_BEFUDDLED_v1.md   <- generated after befuddled cow run completes
