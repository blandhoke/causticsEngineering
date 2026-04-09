# HANDOFF — 24" Square Production Settings
# Date: 2026-03-17
# From: Claude Chat
# To: Claude Code

---

## Decision: Refactor pipeline for 24"×24" production piece

Previous testing was at 8"×8". The production piece is 24"×24".
All solver and G-code settings below are optimized for this size.

---

## Optimal Configuration

### Physical dimensions
  Lens size:      24"×24" = 0.6096m×0.6096m
  artifactSize:   0.6096 (update in engineer_caustics — currently hardcoded 0.1)
  Stock:          1" cast acrylic (standard — dome fits with headroom)

### Focal length (throw distance)
  focalLength:    1.219m = 48" throw  ← OPTIMAL
  
  Rationale:
    - Dome depth:  ~9.2mm  (9× deeper than 8" piece at same focalLength — rich geometry)
    - Solar blur:  12mm at 48" throw  (natural light quality, not over-sharp)
    - Projected image: ~18-24" readable cow portrait at floor/table level
    - 1" stock fits comfortably — no special material order

  Alternative throws for reference:
    36" throw (f=0.914m) → 12.3mm dome, 9mm blur — sharper, slightly deeper stock use
    60" throw (f=1.524m) →  7.4mm dome, 15mm blur — softer, shallower dome
    48" is the sweet spot between dome depth and solar blur quality.

### Solver resolution
  Resolution:     1024px  (correct ceiling for 24"×24")
  
  At 24"×1024px:  grid cell = 0.023" (0.59mm)
  1/4" bit stepover = 0.100" — mesh is finer than stepover, 1024px fully adequate.
  2048px gives 0.012" cells — still finer than the 1/4" bit. No gain at 24".
  2048px is only justified at 24" if using a 1/8" finish bit (0.013" stepover).

### Finish pass — 1/4" ball nose
  Bit:            1/4" ball nose 2-flute
  RPM:            18,000
  Stepover:       0.100" (40% of diameter — locked)
  Feed Normal:    144 IPM
  Feed Superfast: 202 IPM  (1.4×)
  Plunge:         20 IPM

  Machine time:
    Normal:     ~41 minutes  ← use this first
    Superfast:  ~29 minutes

  Rows:           240  (24" / 0.100" stepover)
  Total path:     ~5,856"

### Roughing pass — not a concern per Bland
  Use standard 1/4" roughing settings.
  Fast at any reasonable DOC given shallow dome (~9mm max).
  DOC 0.050", stock-to-leave 0.010" — same as current settings.

---

## Changes Required in Pipeline

### 1. make_physical_lens.py
  Change TARGET_SIZE_M from 0.2032 to 0.6096:
  ```python
  TARGET_SIZE_M = 0.6096  # 24 inches
  ```

### 2. engineer_caustics() in src/create_mesh.jl
  Change artifactSize from 0.1 to 0.6096:
  ```julia
  artifactSize = 0.6096  # 24 inches in metres
  focalLength  = parse(Float64, get(ENV, "CAUSTIC_FOCAL_LENGTH", "1.219"))
  ```
  Note: artifactSize should also be env-configurable for future size changes:
  ```julia
  artifactSize = parse(Float64, get(ENV, "CAUSTIC_ARTIFACT_SIZE", "0.6096"))
  ```

### 3. CAUSTICFORGE addon — update defaults
  stock_width default:   8.0  →  24.0
  stock_height default:  8.0  →  24.0
  finish_bit default:    0625_BALL  →  025_BALL  (1/4" for 24" piece)
  output path default:   update to inkbrush_24in_finish.nc

### 4. G-code output filename
  inkbrush_24in_finish.nc

---

## Expected Output at These Settings

  Solver grid:       1025×1025  (same as current — resolution independent of size)
  Mesh verts:        2,101,250  (same as current)
  Caustic relief:    ~9.2mm = ~0.362"
  Cut depth:         ~0.380"  (relief + 5%)
  Stock required:    1" cast acrylic  (0.380" cut depth well within 1")
  
  G-code lines:      ~211,000  (240 rows × ~880 lines/row)
  File size:         ~7.5MB
  Machine time:      ~41 min Normal  /  ~29 min Superfast

---

## Scaling Reference (do not delete — useful for future sizes)

  Dome depth formula: dome_8in × (new_size / 8)² × (0.75 / new_focalLength)
  
  | Size | focalLength | Dome   | Solar blur | Machine time (1/4") |
  |------|-------------|--------|------------|---------------------|
  | 8"   | 0.75m       | 2mm    | 7mm@30"    | 54 min              |
  | 24"  | 1.219m      | 9.2mm  | 12mm@48"   | 41 min  ← PRODUCTION|
  | 36"  | 1.829m      | 9.2mm  | 16mm@72"   | 94 min              |
  | 48"  | 3.048m      | 7.5mm  | 27mm@120"  | 167 min             |

  Solar blur = throw_distance_metres × 0.009 × 1000  (mm)
  Machine constraint: NK105 accuracy ±0.03mm — never the limiting factor.
  Solar blur is always the resolution floor at practical throw distances.

---

## Files Claude Code Should NOT Touch
  - /Users/admin/Library/Application Support/Blender/4.3/scripts/addons/causticforge_v1.py
    (Claude Chat owns this — will update defaults separately)
  - Any existing *.nc G-code files
  - Final cows/ directory
