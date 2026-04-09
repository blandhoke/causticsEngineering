# HANDOFF — Solver Research & Input Optimization
# Date: 2026-03-17
# From: Claude Code session
# To: Claude Chat
# Context: Research complete, ready for image preprocessing strategy discussion

---

## What This Project Is

A Julia-based caustic lens pipeline. A target image is fed to a Julia SOR solver
(Matt Ferraro's CausticsEngineering) which produces a lens OBJ. When sunlight passes
through the CNC-milled acrylic lens it projects the target image as a caustic on the floor.

Physical setup:
- Lens: 8"×8" × 1" cast acrylic
- Throw: 762mm (30") to projection plane
- IOR: 1.49 (cast acrylic / PMMA)
- focalLength: 0.75m (empirically calibrated)
- CNC: Blue Elephant 1325, NK105 controller

---

## Part 1 — Three-Solver Comparison (Mitsuba ptracer renders, today)

The question was: is Matt Ferraro's Julia SOR solver the best available,
or do other OT-based solvers produce better caustic meshes?

Three solvers tested on the same inkbrush target image, same IOR, same throw distance.
Primary metric: Pearson r (edge correlation vs reference caustic).

| Solver | Edge r | SSIM | Physical dome | Runtime |
|--------|--------|------|--------------|---------|
| **Julia SOR (ours)** | **0.204** | 0.206 | 25.2mm ✓ | ~45 min (1024px) |
| fast_caustic_design (C++ OT) | 0.064 | 0.208 | 25.8mm ✓ | 14 min |
| Poisson caustic design (C++) | 0.090 | 0.175 | 50.8mm ✗ | 4 min (128px only) |

**Winner: Julia SOR by a significant margin.**

Key findings from the other solvers:
- `fast_caustic_design`: IOR was hardcoded at 1.55 (required source patch to 1.49).
  Its `focal_l` parameter is dimensionless (f/D ratio), not meters — so its physical
  throw is 153mm, not 762mm. Structurally incompatible with our setup without major
  rework.
- `Schwartzburg 2014 (ma.py)`: Requires NVIDIA GPU + CUDA + PyMongeAmpere (CGAL-based
  C extension). All structurally unavailable on macOS without NVIDIA GPU.
- `Poisson caustic design`: Converges extremely slowly. 512px ran 28+ minutes without
  completing. 128px at loose convergence threshold (0.01) converged in ~4 min but at
  low quality. Dome comes out 50.8mm — requires 2" acrylic stock.

**Conclusion: Matt Ferraro's solver is the right tool. The research question is closed.**

---

## Part 2 — Matt Ferraro's Code: Confirmed Unmodified

Compared local src/ files to GitHub (github.com/mattferraro/causticsEngineering).
- `src/CausticsEngineering.jl`: bit-identical to GitHub
- `src/utilities.jl`: bit-identical to GitHub
- `src/create_mesh.jl`: identical algorithm, one intentional change:
  `focalLength = 0.75m` (GitHub original uses 1.0m as default; ours is empirically
  calibrated for 1" acrylic at 8"×8" at 30" throw)
- `run.jl`: only change is image path (cat → cow)

The solver is verbatim Matt Ferraro. All other scripts (Python ray tracers, physical
scaler, Mitsuba renders, hooks) were built on top.

---

## Part 3 — Three-Agent Optimization Sweep (34 experiments today)

Three subagents ran controlled experiments across the solver pipeline at HYPER (128px)
resolution for fast iteration. Primary metric: edge_r via compute_metrics.py.

### Station 1: Input Preprocessing
Winner at HYPER: **Sobel edge preprocessing (+1250% edge_r, 0.004 → 0.051)**

Full results at HYPER (128px, Mitsuba 128spp):
| Preprocessing | edge_r | delta |
|---|---|---|
| **H6 Sobel edges** | 0.051 | **+0.047** |
| Linearize + invert | 0.014 | +0.011 |
| Invert only | 0.008 | +0.004 |
| Baseline (raw) | 0.004 | — |
| Contrast stretch | 0.004 | ~0 |
| Unsharp mask | 0.003 | **HURTS** |
| Binary threshold | 0.003 | **HURTS** |
| Gamma linearization | 0.002 | **HURTS** |

Physics rationale: The SOR solver encodes gradients. Its output caustic IS an edge map.
Feeding it an explicit edge map removes one level of indirection.

### Station 2: SOR Parameters
- ω = 1.99: already optimal. Tested 1.80–1.99, nothing beats it.
- Iteration count at HYPER (128px): 3 iterations > 6 (solver over-corrects at low res;
  NORMAL/PROD should keep 6 iterations)
- Mesh initialization jitter: HURTS. Regular grid is better.
- findSurface(): confirmed Poisson solve (same SOR engine, converges to 1e-5).
  This is mathematically optimal. No path artifacts possible. Not improvable.

### Station 3: Surface Geometry
- Phi smoothing: within noise at all tested σ. No benefit.
- Solidify thickness: zero optical effect (confirmed by vertex analysis).
- artifactSize = 0.10m: optimal for 1" stock.
  Upgrade path: 0.115 with 1.125" stock → ~50% more edge_r.
- focalLength = 0.80m: +0.8% over Sobel baseline. Small. Needs NORMAL confirmation
  before changing. CONFIRM REQUIRED before any focalLength edit.

### Cross-feed (improvements compound but Sobel dominates)
| Config | edge_r | vs baseline |
|---|---|---|
| Baseline (raw, 6 iter) | 0.004 | 1× |
| Sobel only | 0.051 | 13.4× |
| focal=0.80 + Sobel + 3 iter | 0.053 | 14.0× |

Sobel accounts for ~95% of the improvement. SOR parameters are second-order.

---

## Part 4 — The Sobel Problem: NORMAL-Scale Revelation

After the HYPER experiments, we ran a NORMAL (512px) comparison:
- **Without Sobel**: `Final cows/inkbrush/normal/mesh.obj` (original)
- **With Sobel**: `examples/inkbrush_normal_sobel.obj` (new run today)

Both: 526,338 vertices, 1,052,672 faces. Same resolution.

| Metric | Original (no Sobel) | Sobel-preprocessed |
|---|---|---|
| Dome height | 22.05mm | 21.63mm |
| **Height std (top surface)** | **1.354mm** | **0.102mm** |
| **Curvature RMS** | **12,778,693** | **2,205** |
| Curvature ratio | — | **5,800× LESS** |
| Height field correlation | — | r = −0.02 (uncorrelated) |

**The Sobel lens is essentially flat.** The Sobel input is 93% black (mean=0.064).
The solver has almost no energy to redistribute, so it creates near-flat glass with
tiny precision bumps only at the ink-stroke locations.

Physically: most light passes straight through unchanged. Only at the stroke locations
does the surface focus light into bright hairlines. The caustic will be very dim overall
with precise thin lines — not a photographic projection.

**The +1250% HYPER edge_r improvement is real but misleading for photographic goals.**
The sparse lines DO correlate better with a Sobel-filtered reference. But if the goal
is a full photographic caustic — a recognizable face, portrait, or detailed image —
the Sobel lens is the wrong direction. It nukes the image.

---

## Part 5 — What We Know About Input Images (Confirmed Physics)

From the CLAUDE.md physics documentation and confirmed experiments:

**The SOR solver encodes GRADIENTS, not brightness:**
- Flat bright regions → gentle lens surface → diffuse spread → DIM caustic area
- Brightness edges/boundaries → steep curvature → concentrated light → BRIGHT lines
- Net result: the caustic is an edge/gradient replica of the target, not a brightness copy

**Confirmed input strategy results:**
- Photographic image (befuddled cow, continuous gradients): produces photographic
  emboss/relief — entire lens area filled with gradient features, NOT a caustic
- Sobel edge map: nearly-flat lens with hairline precision bumps — very dim overall
- Binary silhouette (white on black): clean filled shape, good edges
- Bold line art / logos: ideal — concentrated edges, clear dark background

**The challenge:** How do you retain the RECOGNIZABILITY of a photographic subject
(face, cow, portrait) while giving the solver enough gradient structure to make a
compelling caustic? Pure photo → emboss. Pure edges → hairlines, dim.

---

## Part 6 — Open Question for This Session

**Goal: retain photographic image while improving caustic quality**

Techniques to explore (NOT tried yet):

1. **Luminance gradient map** — instead of Sobel (binary edge), use the actual gradient
   magnitude preserving smooth falloff: `|∇I|` not thresholded. Retains the "shape" of
   objects via their luminance gradient envelope.

2. **Clahe (Contrast Limited Adaptive Histogram Equalization)** — boosts local contrast
   in a controlled way without edge detection. Amplifies the gradients the solver sees
   while preserving photographic structure.

3. **Frequency-domain enhancement** — amplify mid-spatial frequencies (the range that
   encodes shape) while attenuating both DC (flat regions) and noise (high freq).
   Bandpass filter in frequency space.

4. **Bilateral filter preprocessing** — edge-preserving smoothing. Kills texture noise
   while keeping object boundaries. Gives the solver clean, strong gradients at the
   right places.

5. **Retinex processing** — separates reflectance from illumination, normalizes global
   brightness while preserving local contrast. Used in medical imaging for exactly this
   purpose.

6. **Gradient domain manipulation** — directly boost the gradient field of the image
   (increase dI/dx, dI/dy amplitude) then reconstruct, rather than doing edge detection.
   This sharpens the solver's input without destroying spatial structure.

7. **Luminosity + edge composite** — blend: α × original_gray + (1-α) × sobel_edges.
   Controls the tradeoff between photographic emboss and hairline caustic. Find the
   α that retains recognizability while sharpening the caustic structure.

The key test for each: does the resulting OBJ surface maintain meaningful curvature
(std > 0.5mm) while correlating with the target image's content?

---

## Files Created This Session

### New tools:
- `prepare_sobel_input.py` — Sobel edge preprocessor (ready to use)
- `render_any_obj.py` — Mitsuba render with dynamic OBJ geometry parsing
- `compute_metrics.py` — SSIM + Pearson r edge correlation metrics
- `compare_obj_geometry.py` — deep geometric comparison of two OBJ meshes

### Key output files:
- `examples/inkbrush_normal_sobel.obj` — Sobel NORMAL mesh (near-flat, for reference)
- `examples/inkbrush_normal_obj_comparison.png` — 4-panel height/curvature comparison
- `examples/agent1_findings.json` / `agent2_findings.json` / `agent3_findings.json`
- `examples/solver_comparison.png` — 4-panel Julia vs OTMap vs Poisson render comparison

### Reference meshes:
- `Final cows/inkbrush/normal/mesh.obj` — NORMAL inkbrush mesh, original (no Sobel)
- `examples/inkbrush_normal_sobel.obj` — NORMAL inkbrush mesh, Sobel-preprocessed

---

## Recommended Next Steps

1. **Test the 7 techniques above** on the inkbrush input at HYPER first (fast iteration)
   Measure: edge_r AND top-surface height std (must stay > 0.5mm to be physically useful)

2. **Cross-check winner at NORMAL** (512px): run the best 2-3 techniques at full resolution
   and compare OBJ geometry (use compare_obj_geometry.py)

3. **If a technique passes both tests**: update CLAUDE.md and add a
   `prepare_[method]_input.py` script similar to prepare_sobel_input.py

4. **Physical threshold to keep in mind:**
   - Top surface height std > 0.5mm: meaningful caustic contrast
   - Top surface height std > 1.0mm: comparable to photographic-input baseline
   - Dome height < 25.4mm: fits 1" acrylic stock

---

## NEVER DO (reminders)
- Never run the Julia solver directly (`julia run.jl`) — use `start_julia.sh`
- Never delete `cow_accum.npy`, `cow_meta.npy`, `caustic_cow_v3.png`
- Never change `focalLength` in `create_mesh.jl` without ⚠ confirmation
- Never use Blender Cycles or LuxCore for caustic verification
- `simulate_cow.py` has FOCAL_DIST=0.2 bug — never use as template
