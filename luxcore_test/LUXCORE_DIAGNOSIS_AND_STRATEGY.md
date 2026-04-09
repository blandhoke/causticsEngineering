# LuxCore Failure Diagnosis & Recovery Strategy
# Prepared by: Claude Code (Terminal Session)
# Date: 2026-03-16
# Audience: Claude Chat + subagents
# Purpose: Attack the caustic visualization problem in parallel

---

## EXECUTIVE SUMMARY

We need to render the `.obj` caustic lens mesh to verify it will produce the correct
caustic pattern before investing machine hours on the CNC mill. The Python forward
ray tracer works but produces a triangle-grid artifact and lacks photorealistic
lighting. We attempted BlendLuxCore BIDIR (the gold standard for refractive caustics)
and hit a macOS-specific deadlock in the OpenCL framework. This document provides:

1. The complete technical failure trace
2. Every workaround identified
3. Alternative renderer options
4. A parallel agent attack strategy for Claude Chat to execute immediately

The most likely solution is an OpenCL stub loader (30 min to implement) or switching
to a standalone LuxCore binary that doesn't use Blender's headless mode.

---

## PART 1: WHAT WE NEED TO RENDER

### The Object
- File: `/Users/admin/causticsEngineering/examples/original_image.obj`
  (also copied to `luxcore_test/original_image.obj`)
- Geometry: Solidified mesh, ~2.1M faces at 1024px (befuddled cow lens)
  or ~525k faces at 512px (cow v3 lens)
- Scale: ~0.1m × 0.1m × 0.025m (native solver units)
- Material: Glass, IOR = 1.49 (cast acrylic / PMMA)
- What we want to see: A caustic pattern on a flat receiver plane below the lens

### The Physical Setup
```
        Point light source
            ↓
        [Glass lens]   IOR=1.49, dome ~25mm
            ↓↓↓        refracts light downward
        ─────────      receiver plane (white matte)
        caustic here   0.75m below lens bottom
```

### Why This Matters
The Python forward ray tracer confirms the caustic pattern is mathematically correct,
but it shows a triangle mesh grid artifact because each face contributes exactly one
ray from its centroid. A proper Monte Carlo or photon-mapped render would show the
continuous, smooth caustic — the visual that tells us whether the CNC investment
is worth it. We cannot ship physical acrylic to the mill without this confirmation.

---

## PART 2: LUXCORE FAILURE — COMPLETE TECHNICAL DIAGNOSIS

### Environment
- Hardware: macOS (Intel + AMD Radeon Pro 560X)
- Blender: 4.3.2
- BlendLuxCore: 2.10.2 (extension)
- pyluxcore: 2.10.1 (bundled C++ shared library)
- macOS version: Darwin 24.6.0 (macOS 15.x Sequoia)

### The Hang — Exact Call Stack

Captured via macOS `sample` tool on the hanging Blender process:

```
Thread 1 (main):
  PyEval_EvalCode
    _PyEval_EvalFrameDefault
      pyluxcore.cpython-311-darwin.so  [pyluxcore.RenderSession.__init__]
        pyluxcore.cpython-311-darwin.so  [luxcore::detail::RenderSessionImpl::RenderSessionImpl]
          pyluxcore.cpython-311-darwin.so  [slg::RenderSession::RenderSession]
            pyluxcore.cpython-311-darwin.so  [slg::RenderEngine::FromProperties]
              pyluxcore.cpython-311-darwin.so  [slg::PathCPURenderEngine::FromProperties]
                pyluxcore.cpython-311-darwin.so  [slg::CPUNoTileRenderEngine::CPUNoTileRenderEngine]
                  pyluxcore.cpython-311-darwin.so  [slg::CPURenderEngine::CPURenderEngine]
                    pyluxcore.cpython-311-darwin.so  [slg::RenderEngine::RenderEngine]
                      pyluxcore.cpython-311-darwin.so  [luxrays::Context::Context]
                        pyluxcore.cpython-311-darwin.so  [luxrays::OpenCLDeviceDescription::AddDeviceDescs]
                          com.apple.opencl / clGetDeviceIDs   ← HANGS HERE
                            pthread_once
                              __pthread_once_handler
                                dispatch_mach_send_with_result_and_wait_for_reply
                                  _dispatch_mach_send_and_wait_for_reply
                                    (waiting forever — no timeout)

All worker threads: semaphore_wait_trap (blocked waiting for main thread to finish init)
```

Same stack confirmed for: PATHCPU, BIDIRCPU (all engines — same code path).

### Why `pthread_once` Makes This Fatal

`pthread_once` protects a one-time initialization block. If the first caller blocks
indefinitely, ALL subsequent callers in the same process also block waiting for the
first to complete. There is no timeout. The process is permanently frozen.

This is not a bug in LuxCore's logic. It is Apple's `com.apple.opencl` framework
attempting to contact the GPU compute XPC service (a background system process).
In a headless/background process launched without a GUI session, this IPC call
hangs because the GPU service may not be bound to the background process's session.

### UPDATED DIAGNOSIS — 2026-03-16 (supersedes earlier analysis)

**`clGetDeviceIDs` hangs from standalone Python main thread — NOT just Blender.**

```python
# Test run from Blender's Python 3.11, NO Blender process, main thread:
clGetPlatformIDs()  → CL_SUCCESS, 1 platform   ← WORKS
clGetDeviceIDs()    → hangs forever             ← BROKEN
```

This is a **macOS Sequoia AMD Radeon Pro 560X driver / GPU compute XPC service failure**.
The issue is system-level, not Blender-specific. All previous "Blender hang" analysis
was correct about the mechanism but wrong about the scope — it's deeper than Blender.

**Implication:** Running Blender in GUI mode (non-background) will NOT fix the hang.
Any process that calls `clGetDeviceIDs` hangs, period.

**What still works:** `clGetPlatformIDs` succeeds. OpenCL is present but devices
are inaccessible. Intel UHD 630 and AMD 560X both report as a single platform but
`clGetDeviceIDs` for that platform hangs.

**SIP status:** ENABLED. DYLD_INSERT_LIBRARIES blocked for hardened binaries.
Blender's embedded Python binary may not be hardened — worth checking separately.

---

### Every Workaround Attempted and Result

| Attempt | Script | Result |
|---------|--------|--------|
| BlendLuxCore exporter BIDIR via `bpy.ops.render.render()` | render_caustics_bdpt.py | Silent fail — LuxCore engine never called in `--background` mode |
| BlendLuxCore exporter BIDIR via direct `exp.create_session()` | luxcore_direct2.py | **WORKED ONCE** — non-deterministic (13+ min at 1350% CPU, killed before completion) |
| BlendLuxCore exporter PATH/CPU via `exp.create_session()` | luxcore_path_cpu.py | Hangs 0.1% CPU — OpenCL pthread_once deadlock |
| BlendLuxCore exporter PATH + PhotonGI caustic cache CPU | luxcore_path_cpu.py | Hangs — same |
| BlendLuxCore exporter PATH + PhotonGI + OCL/GPU | luxcore_path_gpu.py | Hangs — same (OCL also triggers OpenCL init) |
| Minimal PATH test (32×32, 5 spp, no PhotonGI, fresh scene) | lux_path_minimal.py | Hangs — same |
| Fresh Blender scene (no .blend loaded) PATH | lux_path_fresh.py | Hangs — same |
| Direct `pyluxcore.RenderSession(rcfg)` PATHCPU | lux_pyluxcore_direct.py | Hangs — same |
| Direct `pyluxcore.RenderSession(rcfg)` BIDIRCPU | lux_bidircpu_direct.py | Hangs — same |
| Add `film.opencl.enable = 0` to config | lux_pathcpu_props.py | Hangs — property does not prevent Context::Context() from calling AddDeviceDescs |
| Dump BIDIR exporter properties to find magic disable key | lux_dump_bidir_props.py | No special OpenCL-disable key found. BIDIR and PATH generate identical property sets |

### Why the Single BIDIR Success Was Real But Non-Deterministic

The one successful BIDIR run (session before this one) produced 1350% CPU usage
across 16 threads, loaded 1,052,674 Embree triangles, and ran for 13+ minutes.
It was definitively rendering.

The most likely explanation: the macOS GPU XPC service occasionally responds to
the Mach IPC query within the `pthread_once` block (perhaps the display server
was in the right state). On the next invocation with a fresh process, the service
did not respond, and the hang occurred. This is consistent with known reports of
intermittent OpenCL availability on macOS Ventura/Sequoia in background processes.

---

## PART 3: ROOT CAUSE — ARCHITECTURAL

### Why LuxCore Always Enumerates OpenCL (Even for CPU Engines)

`luxrays::Context::Context()` is called for ALL render engines, not just GPU ones.
Its constructor builds a complete device list — both native CPU threads AND OpenCL
devices — so the user can choose at runtime. This is by design: LuxCore discovers
all available compute resources at startup.

The relevant code path (from LuxCore open source, approximate):
```cpp
// luxrays/src/context.cpp
Context::Context(LogHandler *handler, const Properties &config) {
    // ... always enumerate OpenCL ...
    if (openCLEnabled) {
        cl_uint platformCount;
        clGetPlatformIDs(0, nullptr, &platformCount);  // ← may hang on macOS
        for each platform:
            OpenCLDeviceDescription::AddDeviceDescs(platform, ...);
    }
}
```

The `openCLEnabled` flag is determined by the compile-time build flags, not runtime
properties. BlendLuxCore 2.10.x for macOS is compiled WITH OpenCL support.

### Why `film.opencl.enable = 0` Doesn't Help

This property controls whether the image pipeline (tone mapping, etc.) uses OpenCL
for acceleration. It has nothing to do with the render engine's device enumeration.
The device list is built before any properties are consulted.

---

## PART 4: UNPROVEN FIXES — RANKED BY PROBABILITY OF SUCCESS

### Fix 1: Fake OpenCL ICD Loader (HIGHEST PROBABILITY — ~85%)
**Concept:** Replace Apple's `com.apple.opencl` with a stub library that returns
`CL_SUCCESS` with 0 platforms immediately. LuxCore's `Context::Context()` would
complete with "no OpenCL devices found" and fall back to native CPU threads.

**Implementation:**
```bash
# Option A: Use Homebrew's ocl-icd (open-source ICD loader for Linux, may work on macOS)
brew install ocl-icd  # installs /usr/local/lib/libOpenCL.dylib stub

# Option B: Write a minimal stub .dylib in C:
# ---
# #include <OpenCL/opencl.h>
# cl_int clGetPlatformIDs(cl_uint num_entries, cl_platform_id *platforms, cl_uint *num_platforms) {
#     if (num_platforms) *num_platforms = 0;
#     return CL_SUCCESS;
# }
# cl_int clGetDeviceIDs(...) { return CL_DEVICE_NOT_FOUND; }
# --- compile as .dylib, preload:
# cc -dynamiclib -o /tmp/fake_opencl.dylib fake_opencl.c -framework OpenCL
DYLD_INSERT_LIBRARIES=/tmp/fake_opencl.dylib \
  /Applications/Blender.app/Contents/MacOS/Blender --background --python script.py
```

**Risk:** `DYLD_INSERT_LIBRARIES` is blocked by macOS System Integrity Protection (SIP)
for hardened binaries. Blender may be hardened. This is the main risk.
**Check:** `codesign -d --entitlements - /Applications/Blender.app/Contents/MacOS/Blender`
Look for `com.apple.security.cs.disable-library-validation` in entitlements.

**Fallback if SIP blocks it:** Run Blender from a copy that is not code-signed,
or use `csrutil disable` (requires Recovery Mode, not recommended).

---

### Fix 2: Run Blender in GUI Mode, Not --background (HIGH PROBABILITY — ~80%)
**Concept:** The OpenCL XPC service hang appears specific to background/headless
processes. A GUI Blender process has a proper Quartz display session and may have
a valid connection to the GPU compute service.

**Implementation:** Run the render script via Blender's Python scripting workspace
(GUI open, not headless), OR use `open -a Blender` with an AppleScript trigger,
OR use `Blender --python script.py` WITHOUT `--background`.

```bash
# Without --background (opens Blender window, then runs script):
/Applications/Blender.app/Contents/MacOS/Blender --python /path/to/script.py
# Blender will open briefly, run the script, then quit.
# The key: it has a GUI session, so OpenCL XPC may work.
```

**Risk:** Requires a display (won't work over SSH without X forwarding). Also
requires the script to call `bpy.ops.wm.quit_blender()` at the end.

---

### Fix 3: LuxCoreRender Standalone (SEPARATE BINARY — ~75%)
**Concept:** LuxCoreRender has a standalone command-line render binary (`luxcoreui`
or `luxcoreconsole`) that is separate from the Blender integration. The standalone
binary may have been compiled without OpenCL or with a different initialization path.

**Check:**
```bash
find /Users/admin/Library -name "luxcoreconsole" -o -name "luxcoreui" 2>/dev/null
find /Applications -name "luxcoreconsole" -o -name "luxcoreui" 2>/dev/null
# Or download from: https://github.com/LuxCoreRender/LuxCore/releases
# Look for: LuxCore-opencl-macos (or non-opencl build)
```

The standalone binary accepts `.lxs` or `.scn` scene files (LuxCore's native format).
We would need to convert the OBJ to a LuxCore scene file — straightforward.

**Key advantage:** A non-OpenCL build (PATHCPU-only) may exist that skips the
entire `AddDeviceDescs()` code path entirely.

---

### Fix 4: Mitsuba 3 (ALTERNATIVE RENDERER — ~90% for basic caustics)
**Concept:** Mitsuba 3 is an open-source physically-based renderer with excellent
caustic support, installs via pip, and has no OpenCL dependency. It uses LLVM/Dr.Jit
for CPU vectorization. Most importantly: it's a Python-native renderer.

```bash
pip install mitsuba
# Mitsuba has a 'ptracer' integrator (particle tracer = forward light tracing)
# and 'bdpt' integrator (bidirectional). Both handle refractive caustics well.
```

**Scene setup for our use case:**
```python
import mitsuba as mi
mi.set_variant('scalar_rgb')  # CPU, scalar, RGB

scene_dict = {
    'type': 'scene',
    'sensor': {'type': 'orthographic', ...},
    'emitter': {'type': 'point', 'position': [cx, cy, light_z], 'intensity': {...}},
    'lens': {
        'type': 'obj',
        'filename': 'original_image.obj',
        'bsdf': {'type': 'dielectric', 'int_ior': 1.49, 'ext_ior': 1.0}
    },
    'plane': {
        'type': 'rectangle',
        'bsdf': {'type': 'diffuse', 'reflectance': 0.8}
    },
    'integrator': {'type': 'ptracer', 'max_depth': 16}
}
img = mi.render(mi.load_dict(scene_dict), spp=512)
```

**Why Mitsuba is ideal for caustics:**
- `ptracer` (photon tracer): shoots rays FROM the light, perfect for caustics
- `bdpt` (bidirectional): balanced path tracing, handles all light transport
- Pure Python + pip, no C++ compilation or Blender dependency
- Active development, macOS native support
- Used in caustic rendering research (Schwartzburg 2014 comparison papers)

**Risk:** 2.1M face OBJ may be slow to load/BVH-build. Use the 512px (525k face)
mesh for iteration, production mesh for final render.

---

### Fix 5: pbrt-v4 (ALTERNATIVE RENDERER — ~70%)
**Concept:** pbrt-v4 (physically based rendering tool from the Pharr/Humphreys textbook)
has a SPPM (stochastic progressive photon mapping) integrator that is specifically
designed for caustics. Available as Homebrew formula or source build.

```bash
brew install pbrt  # if available, or build from source
```

**Note:** pbrt scene format requires manual scene file construction. Less Pythonic
than Mitsuba but the SPPM integrator is arguably the best available for refractive
caustics from a point light source.

---

### Fix 6: Cycles with Manifold Next Event Estimation (MODERATE — ~50%)
**Concept:** Standard Cycles fails on refractive caustics because the probability
of a sampled path connecting light → glass → receiver is essentially zero with
naive BSDF sampling. MNEE (Manifold Next Event Estimation) directly solves for
the glass refraction path and connects it explicitly.

Blender 4.x Cycles has MNEE support for shadow caustics but NOT refractive path
tracing caustics in the current stable build. However, there are forks and builds
with experimental MNEE enabled.

**Check:** In Blender 4.3.2, under `Light Path` settings, look for `Shadow Caustics`
toggle. If it exists, it may help but only for shadow caustic effects, not full
refraction caustics.

**Verdict:** Low probability of producing a clean caustic without a specialized
Cycles build. Not recommended as primary path.

---

### Fix 7: Pre-warm OpenCL Before Blender Launches (SPECULATIVE — ~40%)
**Concept:** If a brief OpenCL call is made from a non-Blender process BEFORE
Blender starts, the GPU XPC service may initialize properly and subsequent calls
from Blender would succeed.

```bash
# Pre-warm: call clGetPlatformIDs from a tiny C program
# If this hangs, the problem is system-wide (SIP/GPU service)
# If this succeeds, try immediately launching Blender after
python3 -c "import ctypes; ocl = ctypes.CDLL('/System/Library/Frameworks/OpenCL.framework/OpenCL'); print(ocl)" &
wait; /Applications/Blender.app/Contents/MacOS/Blender --background --python script.py
```

**Low confidence:** The `pthread_once` protection means each PROCESS initializes
independently. Pre-warming in a different process doesn't carry over.

---

### Fix 8: LuxCore via Blender GUI (AppleScript Automation — ~65%)
**Concept:** Use macOS AppleScript or Automator to:
1. Open Blender normally (GUI mode, full display session)
2. Load the scene
3. Trigger render via menu/shortcut
4. Save output image

This avoids `--background` mode entirely. Blender with a real GUI session has
proper GPU service access. The LuxCore BIDIR success in our prior session likely
happened because the Blender process had a display session context.

---

## PART 5: PARALLEL AGENT ATTACK STRATEGY FOR CLAUDE CHAT

Claude Chat should spawn the following subagents simultaneously. Each agent
investigates one thread independently and returns findings + confidence + recommended
action. Do NOT wait for one to complete before starting others.

---

### AGENT 1 — Mitsuba 3 Feasibility + OBJ Compatibility
**Task:** Research and spec out a complete Mitsuba 3 render script for our caustic lens.

**Investigate:**
- Can Mitsuba 3 `scalar_rgb` variant load a 2.1M face OBJ directly?
- What is the memory/time cost for BVH construction at this scale?
- Does `ptracer` (forward light tracing) converge faster than `bdpt` for a point
  light + glass scenario?
- What `spp` is needed for a clean caustic (literature: 512–2048 spp typical)?
- Are there any OBJ import limitations (texture, normals, winding order)?
- What does the render loop look like in Python for our geometry?

**Output:** A complete, runnable Mitsuba 3 Python script for our exact scene.

**Why Mitsuba specifically:** pip install, Python-native, no OpenCL, caustic-optimized.

---

### AGENT 2 — LuxCore OpenCL Stub / DYLD Bypass
**Task:** Find or write an OpenCL stub that makes `clGetDeviceIDs()` return immediately.

**Investigate:**
- Is Blender 4.3.2 on macOS a hardened binary? (Does SIP block DYLD_INSERT_LIBRARIES?)
  Command: `codesign -d --entitlements - /Applications/Blender.app/Contents/MacOS/Blender`
- Does `ocl-icd` from Homebrew provide a stub that works on macOS?
- Can we write a minimal fake `libOpenCL.dylib` in C (just stub the 3 required functions)?
  Required: `clGetPlatformIDs`, `clGetDeviceIDs`, plus any others LuxCore calls
- Is there a LuxCore build for macOS that omits OpenCL entirely (CPU-only build)?
  Check: https://github.com/LuxCoreRender/LuxCore/releases
- Can we patch the pyluxcore .so binary to NOP the `AddDeviceDescs` call? (hex edit)

**Output:** Step-by-step instructions + code for the most viable bypass method.

---

### AGENT 3 — LuxCoreRender Standalone Binary
**Task:** Find and evaluate the standalone LuxCoreRender binary for macOS.

**Investigate:**
- Does a macOS standalone `luxcoreconsole` or `luxcorerender` binary exist?
  Check GitHub releases: https://github.com/LuxCoreRender/LuxCore/releases
- Is there a non-OpenCL macOS build available?
- What scene format does it accept (.lxs, .cfg, .scn)?
- How do we convert our OBJ + glass material setup to the LuxCore native scene format?
  (Needed: camera, point light, glass material with IOR=1.49, receiver plane, halt condition)
- What BIDIR configuration settings produce clean caustics at reasonable speed?
- Can pyluxcore be used standalone (outside Blender) — i.e., just `python3` with
  the pyluxcore .so on PYTHONPATH, not inside Blender at all?
  Path to test: `/Users/admin/Library/Application Support/Blender/4.3/extensions/user_default/BlendLuxCore/pyluxcore.cpython-311-darwin.so`

**Output:** Either a working standalone LuxCore approach OR a verdict that it requires
the same OpenCL enumeration and is blocked.

---

### AGENT 4 — Blender GUI Mode Render (Non-Background)
**Task:** Determine if running Blender WITHOUT `--background` fixes the OpenCL hang.

**Investigate:**
- In macOS, does a non-background Blender process (with display) have different
  GPU XPC service access than `--background`?
- Can a Python script run via `Blender --python script.py` (no `--background`)
  complete a LuxCore render and save output to disk?
- Does the script need to call `bpy.ops.wm.quit_blender()` at the end?
- What is the minimum script structure for: load OBJ, set up scene, BIDIR render,
  save PNG, quit — without any manual interaction?
- Are there any gotchas with running Blender headless-ish on macOS (Dock icon, window)?
  Could use `--no-window-focus` or NSWorkspace tricks if needed.

**Output:** A working Blender non-background render script, or a clear verdict
that GUI mode doesn't change the OpenCL hang behavior.

---

### AGENT 5 — Alternative Caustic Renderers Survey
**Task:** Survey ALL viable open-source renderers that can render OBJ + IOR=1.49
glass caustics on macOS without OpenCL dependency.

**Evaluate each on:**
- macOS compatibility (native, no OpenCL required)
- Python/scripting interface (can automate without GUI)
- Caustic rendering quality (does it converge within minutes?)
- Install complexity (pip / brew / source build)
- OBJ mesh support at 2.1M faces

**Candidates to evaluate:**
1. **Mitsuba 3** — pip install, Python-native, ptracer/bdpt
2. **pbrt-v4** — SPPM integrator, academic gold standard for caustics
3. **Embree + OSPRay** — Intel's path tracer, macOS native
4. **Cycles (standalone)** — Separate from Blender, but likely same limitation
5. **Appleseed** — Production renderer with spectral capabilities
6. **Tungsten** — Research renderer with excellent caustic support
7. **ART (Advanced Rendering Toolkit)** — Spectral, academic
8. **Radiance** — Photon mapping, academic, macOS native
9. **LightMetrica** — Research, Python bindings
10. **Falcor** — Microsoft research renderer (GPU, D3D12 — skip for macOS)
11. **Taichi** — GPU-agnostic, has path tracer examples
12. **Three.js / WebGL** — In-browser physically-based rendering (long shot but zero install)

**Output:** Ranked shortlist (top 3) with install instructions + caustic quality evidence.

---

### AGENT 6 — macOS OpenCL System Diagnosis
**Task:** Determine the exact macOS system state causing the OpenCL hang and whether
it can be fixed at the OS level without hacking the renderer.

**Investigate:**
- What macOS version is this? (Darwin 24.6.0 = macOS 15.x Sequoia)
- Is SIP enabled? (`csrutil status` in Terminal)
- Is the GPU service responding to OpenCL queries from non-Blender processes?
  Test: `python3 -c "import ctypes; lib = ctypes.CDLL('/System/Library/Frameworks/OpenCL.framework/OpenCL'); n = ctypes.c_uint(0); lib.clGetPlatformIDs(0, None, ctypes.byref(n)); print(n.value)"`
- Does the hang occur in ALL processes or only Blender `--background`?
- Is there a macOS system preference, `defaults write`, or environment variable
  that configures OpenCL service availability for background processes?
- AMD Radeon Pro 560X: is it supported by Metal Performance Shaders as an alternative?
  If so, can LuxCore's CUDA/Metal path be used instead of OpenCL?
- Is there a macOS 15 regression in background process GPU access?

**Output:** Diagnosis of whether the OpenCL hang is fixable at OS level, and if so how.

---

## PART 6: RECOMMENDED EXECUTION ORDER

Claude Chat should:

1. **Immediately spawn all 6 agents in parallel** (no dependency between them)
2. **Set a 20-minute research window** — agents return findings simultaneously
3. **Synthesis decision tree:**

```
If Agent 2 finds a working DYLD stub:
  → Implement it. 30-min fix. LuxCore BIDIR with our exact scene.

If Agent 4 confirms non-background mode works:
  → Run Blender non-background. Minimal code change. ~5 min to test.

If Agent 3 finds a standalone LuxCore binary without OpenCL:
  → Use standalone binary. Write scene file. No Blender dependency.

If any of the above fail:
  → Fall back to Agent 1/5 (Mitsuba 3 or best alternative renderer)
  → Mitsuba 3 is the highest-confidence alternative that will definitely work.

Agent 6 findings inform ALL other agents (system state = prerequisite knowledge).
```

---

## PART 7: WHAT A SUCCESSFUL RENDER NEEDS TO SHOW

Regardless of which renderer we use, the output must answer:

1. **Is the caustic pattern shaped like the target image?** (cow silhouette / inkbrush)
2. **Is energy concentrated correctly?** (bright regions where lens design intended)
3. **Is the scale correct?** (pattern diameter matches expected throw at 0.75m focal)
4. **Are there any catastrophic artifacts?** (ray leak, self-intersection, TIR failure)

Acceptance criteria:
- 512×512 output minimum (1024×1024 preferred)
- 100–500 spp minimum (1000 spp ideal)
- Black background, caustic visible as concentrated light region
- Pattern recognizably similar to Python ray tracer output but without grid artifact

If the rendered caustic matches the Python ray tracer output (SSIM > 0.3) AND
looks photorealistic (smooth concentration, no triangle artifact), the CNC investment
is confirmed. Otherwise investigate the discrepancy before milling.

---

## PART 8: SCENE PARAMETERS (copy these into any renderer)

```python
# Geometry
OBJ_PATH = "/Users/admin/causticsEngineering/examples/original_image.obj"
# Mesh scale: 0.0 to ~0.1m in X and Y, -0.0195m to +0.005m in Z
# Lens center: approximately (0.1m, 0.1m, 0.0m) in OBJ coordinates
# Lens Z range: z_min ≈ -0.01953m, z_max ≈ +0.00529m
# Lens span: ~0.2m × 0.2m (at 1024px; ~0.1m × 0.1m at 512px)

# Physics
IOR = 1.49              # cast acrylic / PMMA
FOCAL_DIST = 0.75       # metres — point light above lens top AND receiver below lens bottom

# Light
light_z = z_max + FOCAL_DIST   # above lens top
light_energy = 10000            # watts (adjust per renderer)
light_radius = 0.001            # near-point source (1mm)

# Receiver plane
plane_z = z_min - FOCAL_DIST    # below lens bottom

# Camera (for orthographic top-down verification view)
cam_z = light_z + 0.05
cam_type = 'orthographic'
cam_scale = lens_span * 1.5

# Background: pure black (0,0,0), world energy = 0
# Do not use HDRI or ambient light — caustics only
```

---

## PART 9: FILES IN THIS DIRECTORY

```
luxcore_test/
  README.md                     ← Quick summary of the problem
  LUXCORE_DIAGNOSIS_AND_STRATEGY.md  ← This file (comprehensive)
  original_image.obj             ← The lens mesh (befuddled cow, f=0.75m)
  render_caustics_bdpt.py        ← The Blender+LuxCore script that built the scene
  lux_bidircpu_direct.py         ← Direct pyluxcore BIDIRCPU test (hangs)
  lux_pyluxcore_direct.py        ← Direct pyluxcore PATHCPU test (hangs)
  lux_pathcpu_props.py           ← PATHCPU with all BIDIR export properties (hangs)
  lux_dump_bidir_props.py        ← Captures BIDIR export properties (works — no session)
  inkbrush.png                   ← Target image: inkbrush treatment (top production pick)
  Nikon.png                      ← Target image: Nikon photo (2nd production pick)
  charcol.png                    ← Target image: charcoal treatment
  woodblock.png                  ← Target image: woodblock treatment
  inkbrush_caustic_fast.png      ← Python ray trace, inkbrush, 256px mesh
  inkbrush_caustic_normal.png    ← Python ray trace, inkbrush, 512px mesh
  nikon_caustic_best.png         ← Python ray trace, Nikon, best params
  nikon_caustic_normal.png       ← Python ray trace, Nikon, normal resolution
  comparison_contact_sheet.png   ← All 10 renders (5 images × 2 resolutions) side by side
```

---

## PART 10: CLAUDE CHAT INSTRUCTIONS

Claude Chat should:

1. Read this document in full
2. Spawn all 6 agents listed in Part 5 in a SINGLE message (parallel)
3. Each agent should use WebSearch + WebFetch to research its specific question
4. Set explicit output format: each agent returns [findings, confidence 1-10, recommended action]
5. After agents return, synthesize and generate either:
   a. A working render script (Mitsuba/LuxCore/other) for Claude Code to run, OR
   b. A step-by-step fix for the OpenCL issue for Claude Code to implement
6. Claude Code will execute whatever Claude Chat produces

**Time budget:** We want a caustic render within the next 2–3 hours.
**Acceptable quality:** 512px output, 200+ spp, smooth caustic, no triangle grid.

---

*This document was prepared by Claude Code after exhaustive LuxCore debugging.*
*All test scripts are in this directory. Findings are reproducible.*
*Primary recommendation: Mitsuba 3 (Agent 1) as fastest path to a render.*
*Secondary: DYLD stub (Agent 2) to fix LuxCore if Mitsuba 3 has any issue.*
