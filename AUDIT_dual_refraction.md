# AUDIT — Dual Surface Refraction
**Date:** 2026-04-08
**Session:** v001
**Blocker ID:** DUAL_REFRACTION (state.json)

---

## VERDICT: ✅ NO MISMATCH — BLOCKER RESOLVED

The solver **already accounts for dual refraction** via the thin plano-convex lens formula.
The ray tracer **already models both surfaces** with two explicit Snell's law applications.
`make_physical_lens.py` correctly applies **no refraction correction** — none is needed.

**No code changes required. No existing physical lens OBJs are wrong.**

---

## Evidence

### 1. Solver (`src/create_mesh.jl`, `findSurface()` lines 666-730)

The critical physics is at lines 676-691:

```julia
n₁ = 1.49           # acrylic IOR
inv_n1m1 = 1.0 / (n₁ - 1)   # = 1/0.49 = 2.0408

# For each mesh node:
dx = (node.ix - node.x) * metersPerPixel   # required lateral displacement
dz = H                                      # = focalLength (node.z=0 at this stage)

Nx[i, j] = tan(atan(dx / dz) * inv_n1m1)   # surface slope for this deflection
```

The formula computes: `surface_slope = tan(deflection_angle / (n - 1))`

This inverts the **thin plano-convex lens equation**: `deflection = surface_slope × (n - 1)`.

#### Why (n-1) IS the dual-surface formula:

For a vertical ray hitting a surface tilted at angle α from horizontal:

**Surface 1 (air → acrylic, curved top):**
- Angle of incidence = α
- Snell: sin(α) = n sin(θ_r) → paraxial: θ_r ≈ α/n
- Ray deflection inside glass = α - α/n = α(n-1)/n

**Surface 2 (acrylic → air, flat bottom):**
- Ray hits flat surface at angle β₁ = α(n-1)/n from normal
- Snell: n sin(β₁) = sin(β₂) → paraxial: β₂ = n × β₁ = n × α(n-1)/n = α(n-1)

**Total exit deflection = α(n-1)** ← this is what the solver uses. ✓

For comparison, a **single-surface** model (air→acrylic only, no exit) gives deflection = α(n-1)/n = α×0.329, which is a factor of n=1.49 smaller. The solver uses α(n-1)=α×0.49, which is the LARGER (correct) value.

The (n-1) factor is the standard thin lens power formula for a plano-convex lens:
  P = (n-1) × (1/R_curved - 1/R_flat) = (n-1)/R_curved

#### Thin lens approximation error:

The solver assumes zero lens thickness (all nodes at Z=0 when computing slopes).
Actual relief vs throw:
- 24" lens: relief ~6.9mm, throw 1219mm → thickness/focal ≈ 0.006 (0.6%)
- 8" lens: relief ~2mm, throw 750mm → thickness/focal ≈ 0.003 (0.3%)

Thick lens correction would change effective power by O(thickness/focal)² < 0.004%.
This is far below the solar blur disk (~12mm at 48" throw). **Negligible.**

### 2. Ray Tracer (`simulate_cow2_fresh.py`, lines 136-151)

The ray tracer applies Snell's law **TWICE per ray**:

```python
# Refraction 1: air → acrylic at curved top surface (line 136)
d_glass, valid = refract_batch(d_in, ns, n_ratio=1.0 / IOR)   # n_ratio = 1/1.49

# Propagate through glass to flat bottom (lines 140-141)
t_bot = (z_min - cents[:, 2]) / dz_g
exit_p = cents + t_bot[:, None] * d_glass

# Refraction 2: acrylic → air at flat bottom surface (lines 144-145)
n_bot[:, 2] = 1.0   # upward normal
d_exit, valid2 = refract_batch(d_glass, n_bot, n_ratio=IOR / 1.0)  # n_ratio = 1.49

# Propagate to receiver plane (lines 148-151)
hits = exit_p + t_pln[:, None] * d_exit
```

The ray tracer explicitly models:
1. Refraction at curved entry surface (Snell's law, air→acrylic)
2. Propagation through acrylic medium (finite thickness)
3. Refraction at flat exit surface (Snell's law, acrylic→air)
4. Propagation to receiver plane

This is physically complete. It even handles the finite lens thickness that the solver's thin-lens formula approximates away (though the effect is negligible as shown above).

**All simulate_*.py scripts use this same dual-refraction pattern** — confirmed by grep across the entire codebase.

### 3. `make_physical_lens.py` (lines 1-146)

Searched for: `ior`, `1.49`, `shrink`, `correction`, `compensat`, `refraction`, `dual`, `two_surface`, `snell`, `n_acrylic`, `plano`.

**Found:** Zero refraction correction code. Only mentions are:
- Line 9: docstring "Refraction angles depend on dZ/dXY ratio" (about uniform scaling)

This is **correct behavior**. The physical scaler should NOT apply any refraction correction because:
- The solver already computed the surface shape that produces the correct dual-refraction deflections
- The uniform XYZ scaling preserves the dZ/dXY ratio, so refraction angles are maintained
- Any XY shrink/expand would break the solver's carefully computed surface

### 4. Codebase-wide search

Searched all `.py` and `.jl` files for refraction-related terms. Every occurrence falls into one of:
- Solver: uses `(n-1)` formula (correct for dual surface, as proven above)
- Ray tracers: apply `refract_batch()` twice per ray (correct)
- Docstrings/comments: reference IOR=1.49 as a constant
- Scale scripts: warn about preserving dZ/dXY ratio (correct guidance)

**No file contains any "dual surface correction", "shrink factor", or "compensation" code.**
**No file needs any such correction.** The physics is correct end-to-end.

---

## Why the Blocker Was Wrong

The blocker claimed: "Solver uses single-surface refraction (air→acrylic). Features appear at ~1.49x predicted radius."

This misidentifies `(n-1)` as the single-surface Snell's law, when in fact:
- Single surface: deflection = α(n-1)/n = α × 0.329
- Dual surface (thin plano-convex lens): deflection = α(n-1) = α × 0.49 ← **what the solver uses**

The factor of 1.49 difference between these is real — but it's the dual-surface formula that's larger, and the solver uses the larger (dual-surface) value. If anything, a "single surface only" solver would produce features at *smaller* radius than predicted, not larger.

---

## Impact on Existing Physical Lens OBJs

All existing physical lens OBJs are **correct**:
- charcol/24in_standard/physical_lens_24x24.obj ✓
- charcol/24in_deep/physical_lens_24x24_deep.obj ✓
- examples/physical_lens_8x8.obj ✓

No re-generation needed. No correction factor applies.

---

## Recommendation

1. Update state.json: `blockers[DUAL_REFRACTION].status = "resolved_false_alarm"`
2. Do NOT add any correction to `make_physical_lens.py`
3. Proceed with physical lens generation and CNC production
