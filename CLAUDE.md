# CLAUDE.md — CausticsEngineering
# Auto-accept all edits unless flagged CONFIRM REQUIRED.
# Last updated: 2026-03-16
# Written by: Claude Chat (Sonnet 4.6) via filesystem MCP + Claude Code sessions

---

## ROLE OF CLAUDE IN THIS PROJECT

The user (Bland Hoke) is an artist and CNC operator, not a programmer.
He does not write or debug code. Claude is the sole engineer on this project.

This means Claude must:

  1. OWN THE CODE — Every script, hook, and config file is Claude's responsibility.
     Do not ask the user to edit files, run debug commands, or interpret errors.
     Diagnose and fix problems autonomously.

  2. SELF-DIAGNOSE AT SESSION START — At the beginning of every session, briefly
     audit the current state. Look for:
       - Parameters out of sync (FOCAL_DIST vs focalLength, SPLAT_SIGMA for mesh size)
       - Stale cache files from wrong physics parameters
       - Scripts referencing old version numbers
       - Hooks or tools that could prevent known bug classes
       - CLAUDE.md sections that have become inaccurate
     Fix anything found before starting the user's requested work.

  3. PROACTIVELY IMPROVE THE WORKFLOW — When a task reveals a fragile pattern,
     fix it immediately. Do not document "future improvements" and leave them.
     If something has burned this project once, implement the safeguard now.
     The hooks in .claude/hooks/ exist because bugs hurt real runs. Add more
     hooks whenever a new class of silent failure is identified.

  4. EXPLAIN IN PHYSICAL TERMS — The user understands CNC machines, acrylic
     stock, throw distances, and visual caustic quality. Frame all decisions
     in those terms. "The dome is 25.2mm, which fits your 1-inch stock with
     0.18mm to spare" is more useful than "the z-range is 0.02482m."

  5. NEVER HAND WORK BACK — Do not ask the user to run commands, check values,
     or verify outputs that Claude can check directly. If a script output needs
     reading, read it. If a parameter needs verifying, grep it.

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
    befuddled_v5_accum.npy          <- ray trace cache for befuddled v5 (f=0.75, sigma=0.75)
    befuddled_v5_meta.npy           <- bounds cache for befuddled v5
    caustic_befuddled_v1.png        <- befuddled f=0.2m render (reference, do not delete)
    caustic_befuddled_v4.png        <- befuddled v4 BROKEN render (FOCAL_DIST mismatch)
    caustic_befuddled_v5.png        <- befuddled v5 FIXED render (current best)
    physical_lens_8x8.obj           <- CNC-ready scaled OBJ (8"x8", dome 25.22mm, throw 30")
  simulate_cow.py                   <- cow v3 ray trace (DO NOT MODIFY -- it's the template)
  simulate_befuddled_v5.py          <- current active befuddled script (f=0.75, sigma=0.75)
  simulate_befuddled.py             <- OUTDATED (FOCAL_DIST=0.2 bug) -- do not use
  simulate_caustic.py               <- water drop reference script (do not modify)
  verify_obj.py                     <- OBJ geometry validator (exits 0 on pass)
  make_physical_lens.py             <- physical CNC scaler (writes physical_lens_8x8.obj)

NOTE: simulate_befuddled.py is OUTDATED (FOCAL_DIST=0.2 bug). Use simulate_befuddled_v5.py.

---

## Key Physical Parameters

  focalLength    = 0.75m        hardcoded in create_mesh.jl engineer_caustics()
                                 EMPIRICALLY DETERMINED for 1" acrylic at 8"x8"
                                 Calibration: f=0.20→34.6mm, f=0.60→26.1mm, f=0.75→25.2mm
  FOCAL_DIST     = 0.75         in simulate_*.py — MUST MATCH focalLength above
                                 WRONG FOCAL_DIST was root cause of v4 washout
  artifactSize   = 0.1m         hardcoded in create_mesh.jl engineer_caustics()
                                 (solver's native lens span; native XY ~0.2m at 1024px)
  IOR            = 1.49         cast acrylic / PMMA -- in solver AND simulate_*.py
  Grid           = 512x512      const grid_definition at top of create_mesh.jl
  CNC machine    = Blue Elephant 1325, NK105 controller
  Target lens    = 8"x8" x 1" cast acrylic
  Physical dome  = 25.22mm      (0.18mm margin under 1" stock — USE 1.125" if available)
  Physical throw = 762mm / 30"  from lens bottom to projection plane
  Total install  = ~787mm       throw + dome ≈ light source to projection surface

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
  SPLAT_SIGMA  = 0.75     <- Gaussian splat width (pixels) FOR 1024px / 2.1M face mesh
                             Formula: sigma = 1.5 / sqrt(face_count / 525000)
                             512px mesh (~525k faces) -> sigma=1.5, radius=3
                             1024px mesh (~2.1M faces) -> sigma=0.75, radius=2
  SPLAT_RADIUS = 2        <- kernel half-width for 1024px mesh (5x5 kernel)
  IMAGE_RES    = 1024     <- output PNG resolution
  IOR          = 1.49
  FOCAL_DIST   = 0.75     <- MUST MATCH focalLength in create_mesh.jl (currently 0.75m)
                             v4 was broken because this was 0.2 while solver used 0.75

Cache behavior:
  - Cache present -> skip simulation, load instantly, replot only
  - Cache absent -> full simulation (8-15 min at 512px mesh, 4-pass; ~40 sec at 1024px)
  - To replot only: run script as-is (reads cache)
  - To force re-simulation: delete *_accum.npy + *_meta.npy
  - Stale caches (wrong FOCAL_DIST or wrong sigma): AUTO-DELETE, no confirm needed
  - Protected forever: cow_accum.npy, cow_meta.npy (v3 baseline — never delete)

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

## Physical Scaling (make_physical_lens.py)

make_physical_lens.py EXISTS and is correct. Run it after julia run.jl.

Scale factor is DYNAMIC — computed from actual OBJ XY span (do not hardcode).
1024px input produces ~0.2m native span; scale = 0.2032 / 0.2001 ≈ 1.016x.
512px input produces ~0.1m native span; scale = 0.2032 / 0.1001 ≈ 2.029x.

NATIVE_FOCAL_M in make_physical_lens.py MUST stay in sync with focalLength
in create_mesh.jl. Both are currently 0.75. Check both if you change either.

Critical: Z must scale with XY. The refraction angles depend on dZ/dXY ratio.
Scaling only XY would change all surface normals and destroy the caustic pattern.

Script no longer exits on dome > material limit — it warns and writes CNC file.
The 0.18mm margin at f=0.75 is intentional. Use 1.125" stock if available.

---

## Running the Julia Solver

CONFIRM REQUIRED before running (slow, overwrites examples/original_image.obj).
Edit only the Images.load() line in run.jl to change the target image.

### Background launch (preferred — non-blocking):

  bash start_julia.sh          # safety checks + nohup launch + OBJ backup
  bash check_julia.sh          # poll status at any time
  tail -f logs/julia_current.log  # live log stream

start_julia.sh performs all safety checks automatically:
  1. Aborts if there are uncommitted tracked-file changes
  2. Aborts if solver is already running
  3. Backs up examples/original_image.obj → original_image_BACKUP.obj
  4. Launches julia run.jl via nohup, logs to logs/julia_TIMESTAMP.log
  5. Symlinks logs/julia_current.log → latest log

check_julia.sh parses the live log and reports:
  - Process status (RUNNING / FINISHED / CRASHED)
  - Phase: Precompiling / it1-it6 / findSurface / solidify / COMPLETE
  - Progress bar and % estimate
  - Last convergence value
  - Iteration tracker from loss_itN.png files (reliable ahead-of-log indicator)
  - Last 5 log lines
  - Error detection (NaN, Exception)
  - Returns exit code 0 while running, 1 when done

### Monitoring cadence for Claude Code:

  Phase                  Check every
  ─────────────────────  ───────────
  Precompile (0-30s)     30 sec
  it1 Building Phi       2 min
  it2-it6                90 sec
  findSurface            90 sec
  solidify/saveObj       30 sec
  After complete         run verify_obj.py immediately

### Completion signal:
  "We've filled up 4194304 triangles" in log = solver done (1024px mesh)
  check_julia.sh exits 1 when PID is gone
  Always run python3 verify_obj.py after completion to verify dome height

### Foreground (legacy, blocks terminal):
  julia run.jl

---

## Blender 4.3.2 API (correct names -- wrong names silently fail)

Import:   bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
Caustics: light.cycles.is_caustics_light    = True
          lens.cycles.is_caustics_caster    = True
          plane.cycles.is_caustics_receiver = True

NOT: use_shadow_caustic, is_caustic_catcher  <- silently wrong in 4.3

---

## Tools, Plugins, and Workflow Aids

When starting a session or evaluating whether to add a tool, check this section
first. Add entries here whenever a new tool, script, MCP, or hook is confirmed
useful or confirmed NOT useful for this project.

### Custom Scripts (in project root)

  start_julia.sh     Background Julia launcher with safety checks and OBJ backup
                     USE THIS instead of running julia run.jl directly
  check_julia.sh     Live progress parser for running solver
                     Parse: phase, %, convergence val, errors, last 5 log lines
  verify_obj.py      Post-solver geometry check — exits 0 on pass
  make_physical_lens.py  CNC scaler — dynamic scale from actual OBJ span
  simulate_befuddled_v5.py  Current active ray tracer (FOCAL_DIST=0.75, sigma=0.75)
  analyze_befuddled_v5.py   9-panel analysis figure + metrics

### MCP Servers

  sequential-thinking  USE for multi-step physics reasoning (focal length
                       bracketing, dome/throw tradeoff calculations)
                       Best invoked via Claude Chat before writing new scripts
  context7             USE for numpy/scipy/matplotlib API lookups when writing
                       new Python. Not needed for routine edits.
  memory               Persistent facts across sessions — see ~/.claude/projects/
                       .../memory/MEMORY.md for index
  github               USE for PR creation and review. Not needed for direct
                       git commit workflow (which is the current pattern).
  filesystem (MCP)     Enables Claude Chat to write CLAUDE.md directly.
                       Critical for cross-session Claude Chat → Claude Code handoff.

### Claude Code Hooks (active — .claude/settings.json + .claude/hooks/)

  IMPLEMENTED:
    PreToolUse  Bash  → .claude/hooks/check_julia_direct.sh
      Blocks any direct "julia run.jl" call. Forces use of start_julia.sh.
      Allows: nohup calls (from start_julia.sh itself), bash start_julia.sh

    PostToolUse Write → .claude/hooks/check_focal_sync.sh
      After any file write, checks FOCAL_DIST / focalLength alignment.
      If create_mesh.jl written: compares its focalLength to all simulate_*.py
      If simulate_*.py written: compares its FOCAL_DIST to create_mesh.jl
      Prints clear warning box if mismatch found. Exit 0 always (warning only).

  HOW TO ADD A NEW HOOK:
    1. Write a shell script to .claude/hooks/your_hook.sh (make it executable)
    2. Add an entry to .claude/settings.json under PreToolUse or PostToolUse
    3. Test: echo '{"tool_input":{"command":"..."}}' | bash .claude/hooks/your_hook.sh
    4. Commit both files

  HOOK WRITING RULE: A hook should prevent a bug class that has already
  occurred, or give live visibility into a slow process. Not convenience.
  Every hook adds latency to every matching tool call — keep them fast (<1s).

### What NOT to Add

  Blender Cycles / LuxCore  caustics don't converge — confirmed waste of time
  Blender Decimate modifier  destroys solver surface normals — never use
  Hardcoded scale factors    always compute from actual OBJ XY span dynamically
  Additional MCP servers     high overhead, low benefit for this workflow

### Evaluating a New Tool

  Before adding any tool, script, or MCP, ask:
  1. Does it prevent a class of bug that has already burned this project?
     (High value — implement)
  2. Does it give live visibility into a long-running process?
     (High value — implement)
  3. Does it save typing for a task done more than twice per session?
     (Medium value — implement if simple)
  4. Does it add a new capability not already in the pipeline?
     (Evaluate carefully — complexity cost)
  5. Does it just make something slightly more convenient?
     (Low value — skip)

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
  - Deleting .npy cache files UNLESS they are confirmed stale (wrong physics params)
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
