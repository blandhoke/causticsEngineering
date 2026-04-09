# LuxCore Test / Debug Directory

Isolated environment for LuxCore experimentation. Nothing here affects the main pipeline.

## Known Root Cause (as of 2026-03-16)

Every `pyluxcore.RenderSession()` call hangs on macOS because:

```
RenderSession() → Context::Context() → OpenCLDeviceDescription::AddDeviceDescs()
  → clGetDeviceIDs() → com.apple.opencl → pthread_once → dispatch_mach_send... HANGS
```

Apple deprecated OpenCL (macOS 10.14, 2018). The GPU XPC service hangs on
first call from headless/background processes. Affects ALL engines: BIDIR, PATHCPU, etc.

The one successful BIDIR run in the prior session was non-deterministic luck.

## Files

- `render_caustics_bdpt.py` — Main render script (two-pass Blender approach)
- `lux_dump_bidir_props.py` — Dumps BlendLuxCore BIDIR export properties
- `lux_bidircpu_direct.py` — Direct pyluxcore BIDIRCPU test (hangs)
- `lux_pyluxcore_direct.py` — Direct pyluxcore PATHCPU test (hangs)
- `lux_pathcpu_props.py` — PATHCPU with BIDIR-equivalent props (still hangs)
- `original_image.obj` — Lens mesh (befuddled cow, f=0.75m) for render tests
- `*.png` — Reference caustic outputs from the Python forward ray tracer

## Potential Next Debug Steps (if pursuing)

1. **Check if clGetPlatformIDs can be called from main thread** (not via Blender `--background`):
   Write a minimal C test or use Python ctypes to call OpenCL directly and see if
   it hangs only from background processes or always.

2. **Try DYLD_LIBRARY_PATH workaround**: Override the OpenCL framework with a stub
   that returns no platforms. LuxCore would then proceed with CPU-only native threads.

3. **Try newer pyluxcore**: LuxCore 2.10.1 is installed. Check if 2.10.2 or 2.11
   added any no-OpenCL build option or macOS fix.

4. **OCLGRIND or fake OpenCL**: Install a fake OpenCL ICD loader (e.g., via Homebrew
   `ocl-icd`) that returns quickly with 0 platforms. This would let Context::Context()
   complete and fall back to native CPU threads.

## Why It Doesn't Matter for the Main Pipeline

The Python forward ray tracer (`simulate_*.py`) is:
- Faster for verification (loads cache in <1s)
- Physically correct (Snell's law, confirmed 99.8% hit rate)
- Already producing publication-quality caustic renders

LuxCore BIDIR would be prettier (Monte Carlo noise vs triangle-grid artifact) but
at 13+ min/1000spp on CPU it's impractical. The forward tracer is the right tool.
