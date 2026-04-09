# Handoff: Mitsuba 3 Caustic Rendering — First Successful Render
# Date: 2026-03-17
# From: Claude Code (Terminal)
# To: Claude Chat
# Status: MITSUBA 3 IS WORKING — first render produced in 5.8 seconds

---

## WHAT JUST HAPPENED

We have a working caustic renderer. After exhaustive LuxCore debugging (see below),
we pivoted to Mitsuba 3. It installed in one command, loaded the 2.1M face lens
mesh in 4.4 seconds, and rendered 256 spp in 1.4 seconds total.

**The output:** `examples/caustic_mitsuba.png` — open it to evaluate.

---

## MITSUBA 3 STATUS

### What Is Working
```
mitsuba 3.7.1 installed at: /Users/admin/Library/Python/3.9/lib/python/site-packages/mitsuba/
variant: scalar_rgb (CPU, single-thread, reliable)
integrator: ptracer (particle tracer — forward light tracing, ideal for caustics)
sensor: perspective (50m altitude, ~0.34° FOV → near-orthographic approximation)
BVH build: 4.4s for 2.1M face mesh
Render: 1.4s for 256 spp at 512×512
Max pixel value: 79,770 (signal present — caustic is hitting the plane)
```

### Render Script
`/Users/admin/causticsEngineering/render_mitsuba.py`

Scene parameters baked in:
```python
OBJ_PATH   = "examples/original_image.obj"   # befuddled cow lens, f=0.75m
IOR        = 1.49                              # cast acrylic
FOCAL_DIST = 0.75                              # must match Julia solver
cx, cy     = 0.100190, 0.100195               # lens centre
z_min      = -0.019531  z_max = 0.005293      # lens Z range
light_z    = z_max + 0.75 = 0.755293          # point source above lens
plane_z    = z_min - 0.75 = -0.769531         # receiver below lens
pad        = span * 1.5 = 0.300017            # receiver half-width
```

### Known Issues / What Claude Chat Needs to Assess Visually
1. **Is the caustic pattern visible and cow-shaped?** Compare with
   `luxcore_test/inkbrush_caustic_normal.png` — our Python ray tracer reference.
2. **Is the image black / flat?** The light intensity (100,000W) may need tuning.
   `max=79,770` suggests signal exists, but the sqrt gamma may compress it.
3. **Is the orientation correct?** Caustic should match the fliplr orientation
   confirmed in our Python ray tracer (horizontal mirror of input image).
4. **Noise level at 256 spp?** ptracer with a point light source should converge
   quickly. If noisy, increase SPP to 1024 or 4096 — still fast (scales linearly).

---

## LUXCORE DEAD END — FINAL DIAGNOSIS

### Root Cause (Confirmed)
```
clGetPlatformIDs()  → CL_SUCCESS, 1 platform   ← WORKS
clGetDeviceIDs()    → hangs forever             ← BROKEN (system-wide)
```

`clGetDeviceIDs` deadlocks in `pthread_once → dispatch_mach IPC` from:
- Blender `--background` mode ✗
- Blender GUI mode (untested but expected ✗ based on standalone Python result)
- Standalone Blender Python 3.11 (outside Blender process) ✗
- System Python 3.9 main thread ✗

This is a **macOS 15.7.2 Sequoia + AMD Radeon Pro 560X driver issue**.
The GPU compute XPC service fails to respond to `clGetDeviceIDs` calls.
LuxCore always calls this in `Context::Context()` for every engine type.

### What Was Tried (11 approaches, all failed)
See `luxcore_test/LUXCORE_DIAGNOSIS_AND_STRATEGY.md` for full table.

### SIP Status
SIP is **enabled** — blocks DYLD_INSERT_LIBRARIES on hardened Blender binary.
The stub approach (fake libOpenCL.dylib) may still work against Blender's embedded
Python binary which may not be hardened. This is a research task for agents.

---

## SYSTEM PROFILE SUMMARY

```
Hardware: MacBook Pro 15,1 (2019)
CPU:      Intel i9, 8-core, 2.4 GHz (16 threads with HT)
RAM:      32 GB
GPU:      AMD Radeon Pro 560X — 4 GB VRAM, Metal 2 (1024 SPs, ~2.4 TFLOPS FP32)
          Intel UHD Graphics 630 — display only
OS:       macOS 15.7.2 Sequoia (Darwin 24.6.0)
SIP:      ENABLED
Python:   3.9.6 (system), 3.11 (Blender embedded)
Mitsuba:  3.7.1 installed on Python 3.9
```

---

## WHAT CLAUDE CHAT NEEDS TO DO

### Priority 1 — Evaluate the render output
Open `examples/caustic_mitsuba.png` and determine:
- Is the caustic visible and shaped correctly?
- Does it match the Python ray tracer reference images in `luxcore_test/`?
- What adjustments are needed? (light intensity, SPP, camera angle)

If the render looks good → we can proceed to production renders for inkbrush/Nikon
at 1024px and 1024+ spp before committing to CNC.

If the render is black/flat → light intensity needs tuning. The adjustment is one
parameter change in `render_mitsuba.py` line ~57: `'value': 100000.0`.

### Priority 2 — Spawn parallel agents for Mitsuba optimization
Based on the strategic document `luxcore_test/GAMEPLAN_2026-03-17.md`, the
8-agent parallel research plan is ready to execute. Key questions still open:

**Mitsuba-specific (most important):**
- **Agent M3: Differentiable rendering for lens design** — can Mitsuba 3's drjit
  backend optimize vertex positions directly from a target image? This could
  replace or validate the Julia SOR solver. Research papers: "Differentiable
  Caustics" SIGGRAPH 2023, Mitsuba 3 inverse rendering examples.

- **Agent M5: Metal GPU on AMD Radeon 560X** — `scalar_rgb` is single-threaded.
  The `llvm_ad_rgb` variant uses all 16 CPU threads. Does a Metal variant exist
  for AMD on macOS? At 1.4s/render with scalar_rgb, llvm might bring this to
  milliseconds.

- **Agent M2: llvm_ad_rgb variant** — the LLVM warning ("LLVM API initialization
  failed") currently appears at startup. This may mean `llvm_ad_rgb` can't run
  yet. Is there a missing LLVM installation? `brew install llvm@16` may fix it.
  If llvm_ad_rgb works: 16-thread CPU acceleration + autodiff for the optimizer.

**LuxCore (secondary, pursue in parallel):**
- **Agent L1:** Is Blender's embedded Python 3.11 NOT hardened? If so, the
  DYLD_INSERT_LIBRARIES stub for `clGetDeviceIDs` would work.
  Test: `codesign -d --entitlements - /Applications/Blender.app/Contents/Resources/4.3/python/bin/python3.11`

- **System Agent:** Is there a macOS system setting to re-enable AMD OpenCL compute?
  Search: "macOS Sequoia AMD OpenCL clGetDeviceIDs disabled"
  Possible fix: Security & Privacy settings, or `sudo systemextensionsctl` command.

### Priority 3 — Production render pipeline
Once render quality is confirmed, update `render_mitsuba.py` for:
- `inkbrush.png` target (production pick #1)
- 1024×1024 output, 1024+ spp
- Save to `Final cows/inkbrush/production/caustic_mitsuba.png`
Then compare with Python ray tracer SSIM metric to confirm equivalence.

---

## MITSUBA OBJ GENERATION — THE STRATEGIC PIVOT

The user raised the question of generating `.obj` files directly from Mitsuba.
This refers to Mitsuba 3's **differentiable rendering** capability:

**Current pipeline:**
```
Target image → Julia SOR solver (OT) → OBJ → Python ray trace → verify
```

**Mitsuba differentiable pipeline (proposed):**
```
Target image → Mitsuba 3 drjit optimizer → OBJ (directly)
```

This works by:
1. Start with the current flat/domed mesh as initial geometry
2. Define loss: |mi.render(scene, params) - target_caustic|²
3. Compute gradient: dr.grad(loss) w.r.t. vertex positions
4. Adam optimizer step on vertex positions
5. Repeat until convergence (100-500 iterations)
6. Export optimized vertex positions as OBJ

The Julia solver uses Optimal Transport (Monge-Ampère PDE) which is mathematically
elegant but requires careful tuning (focalLength bracketing, SOR iterations, 45+ min).
Mitsuba's differentiable approach would be faster to iterate and potentially produce
higher quality caustics by directly optimizing for pixel-accurate output.

**Key constraint to research:** Does drjit autodiff work for mesh vertex positions
in Mitsuba 3? The `mi.traverse(scene)` API exposes mesh parameters including
`vertex_positions`. Whether gradients flow through the BVH traversal is the
critical question.

---

## FILES SUMMARY

```
luxcore_test/
  LUXCORE_DIAGNOSIS_AND_STRATEGY.md  ← Full LuxCore failure history
  GAMEPLAN_2026-03-16.md              ← 8-agent parallel strategy (updated: GAMEPLAN_2026-03-17.md)
  original_image.obj                  ← Copy of lens mesh for isolated testing
  *.png                               ← Reference caustic images + target images

examples/
  caustic_mitsuba.png                 ← NEW: first Mitsuba render (evaluate this)
  original_image.obj                  ← Lens mesh (befuddled cow, f=0.75m, 2.1M faces)

render_mitsuba.py                     ← NEW: working Mitsuba render script
```

---

## QUICK PARAMETER REFERENCE

To change render quality, edit these lines in `render_mitsuba.py`:
```python
WIDTH  = 512    # → 1024 for production
HEIGHT = 512    # → 1024 for production
SPP    = 256    # → 1024 or 4096 for cleaner output (still fast)
MAX_DEPTH = 16  # fine as-is (2 refractions need ~4 bounces)
```

To change the light intensity (if output is too dim or too bright):
```python
'value': 100000.0   # line ~57 — increase for brighter caustic
```

To render a different lens mesh (e.g., inkbrush production):
```python
OBJ_PATH = "/Users/admin/causticsEngineering/Final cows/inkbrush/normal/mesh.obj"
OUTPUT_PNG = "/Users/admin/causticsEngineering/Final cows/inkbrush/production/caustic_mitsuba.png"
```

---

## NEXT ACTIONS FOR CLAUDE CODE (waiting on Claude Chat visual review)

1. If render looks correct → bump to 1024×1024 / 1024 spp, run production render
2. If render is black → increase light intensity to 1e7 or 1e8 and rerun
3. If render shows wrong orientation → add `np.fliplr(lum)` before imshow
4. Implement llvm_ad_rgb variant after checking LLVM install status
5. Pursue inkbrush 1024px production Julia run (independent of rendering)

---

*Handoff written by Claude Code — 2026-03-17*
*Mitsuba 3.7.1 working. First render: 5.8s total. caustic_mitsuba.png is ready to review.*
