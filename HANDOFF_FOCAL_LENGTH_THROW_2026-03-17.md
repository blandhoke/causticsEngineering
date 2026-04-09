# HANDOFF — Focal Length, Throw Distance, and Dome Budget
# Date: 2026-03-17
# From: Claude Chat
# To: Claude Code

---

## Key Findings

### 1. Dome height is a function of focal length — not material thickness

The 23mm dome warning in `make_physical_lens.py` was calibrated for the original
befuddled cow pipeline at 16"×16". For the current 8"×8" inkbrush lens at
focalLength=0.75m, the actual caustic surface relief is only **2.055mm** — 8% of
available 1" stock depth. There is no material constraint issue at current settings.

Dome depth scales as:
  dome ∝ image_displacement / (focalLength × (n-1))
  where n = 1.49 (cast acrylic IOR), so (n-1) = 0.49

Shorter focal length → deeper dome from the same image content.

Approximate dome depths for inkbrush at 8"×8":
  focalLength = 0.30m → ~5mm dome
  focalLength = 0.50m → ~3mm dome
  focalLength = 0.75m → ~2mm dome (current)
  focalLength = 1.50m → ~1mm dome

At 16"x16" (artifactSize=0.2032m), dome scales ~4x deeper than 8":
  focalLength = 0.75m → ~8mm dome  (fits 1" stock comfortably)
  focalLength = 0.50m → ~12mm dome (fits 1" stock)
  focalLength = 0.30m → ~20mm dome (approaching 1" limit, use 1.5" stock)
  Solver time is identical to 8" — artifactSize is a post-solve scale factor only.
  G-code at 16" x 1/8": ~216 min Normal. At 16" x 1/16": ~748 min — not recommended.

### 2. focalLength is not a free parameter — it must match installation geometry

focalLength in the Julia solver sets the throw distance: the physical distance from
the bottom face of the lens to the projection surface (floor, table, wall).

If focalLength=0.75m but the lens is installed 400mm above the floor, the caustic
image will be distorted. They must match.

**focalLength = actual physical throw distance in the installation.**

### 3. Machine tolerance does not constrain throw distance

Blue Elephant 1325 / NK105 working accuracy: ±0.03mm (confirmed from spec sheet).
Real-world with acrylic and workholding: ~±0.05mm conservative estimate.

At any practical throw distance, the sun's angular diameter (0.5° = 9 mrad) produces
more blur than the machine's positional error. The machine is not the limiting factor.

Caustic sharpness is limited by:
  - Solar blur = throw_distance × 0.009 (grows with throw)
  - Feature scale = lens_size / grid_resolution = 8" / 1025 ≈ 0.008" per grid cell

Sweet spot for readable cow portrait at 8"×8" lens: **0.5m to 1.0m throw**
  - 0.5m → projected image ~20" across, sharp, crisp lines
  - 1.0m → projected image ~40" across, readable but softer
  - 1.5m+ → solar blur starts washing fine fur/eye detail

### 4. Recommended action for Claude Code

Make focalLength configurable via environment variable before next solver run:

```julia
focalLength = parse(Float64, get(ENV, "CAUSTIC_FOCAL_LENGTH", "0.75"))
```

This lets us sweep focal lengths without editing source. The sweep to run:
  CAUSTIC_FOCAL_LENGTH=0.30  → deepest dome, shortest throw (12")
  CAUSTIC_FOCAL_LENGTH=0.50  → medium dome, 20" throw
  CAUSTIC_FOCAL_LENGTH=0.75  → current baseline, 30" throw
  CAUSTIC_FOCAL_LENGTH=1.00  → shallow dome, 39" throw

Lock the production value once installation geometry is confirmed.

### 5. Do NOT add a dome ceiling clamp

Remove or disable the 25.4mm dome warning/clamp in `make_physical_lens.py` for
test runs. Let the solver produce whatever height the image+focalLength naturally
generates. Report the dome depth and let Bland decide if it fits the stock.

For reference: even at focalLength=0.30m the expected dome is ~5mm — well within
1" stock. The 25.4mm ceiling would only be hit at extremely short focal lengths
(<0.1m) which are not physically meaningful for this installation.

---

## Resolution — 1024px is the production ceiling, 2048px has no optical gain

Grid cell size vs finish bit stepover:
  512px  → 0.016" cell — toolpath (0.005" so) finer than mesh, interpolating
  1024px → 0.008" cell — mesh finer than toolpath, full solver resolution captured ✓
  2048px → 0.004" cell — finer than any practical stepover, solver time ~4x longer

Solar blur at 0.5m throw = 4.5mm. Sub-0.1mm surface features are washed out optically.
1024px is the correct ceiling for 8"x8". At 16"x16", 2048px becomes justified:
  - Solar blur does not scale with lens size — same absolute blur circle at projection plane
  - 16" x 2048px gives 0.008" cells, matching 8" x 1024px feature resolution
  - Solver time at 2048px is ~4x longer but artifactSize does not affect solver time
  - G-code at 16" x 1/8" x 1024px: ~216 min. At 2048px: ~480 min.
  Do not propose 2048px for 8"x8". It is appropriate for 16"x16" final production only.

---

## Current Production Values (do not change without confirmation)

- focalLength: 0.75m
- artifactSize: 0.1m (native solver size — scaled to 8"×8" by make_physical_lens.py)
- IOR: 1.49 (cast acrylic)
- Grid: 512px → 1025×1025 mesh (2.1M verts after solidify)
- Caustic relief: 2.055mm = 0.0809"
- G-code: inkbrush_finish_v12.nc (844k lines, 1/8" ball nose, 100 IPM Normal)
