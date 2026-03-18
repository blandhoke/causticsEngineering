# Charcol 24" — Standard Variant (GCODE READY)
Generated: 2026-03-17

## Settings
- CAUSTIC_ARTIFACT_SIZE = 0.1 (standard 8" mesh, scaled to 24")
- CAUSTIC_FOCAL_LENGTH  = 1.219m (48" throw)
- CAUSTIC_TARGET_SIZE   = 0.6096 (24" physical output)
- Source: INKFORGE/charcol.png (black background)

## Results
- Caustic relief: 6.109mm = 0.2405"
- Cut depth:      0.2525"  (relief + 5%)
- Stock required: 1" cast acrylic  ✓ (6.1mm << 25.4mm limit)
- Physical size:  609.6mm × 609.6mm (24" × 24")
- Throw distance: 1219mm (48")
- Scale factor:   3.0457×

## Files
- mesh.obj              — native solver output (200mm span, pre-scale)
- physical_lens_24x24.obj — CNC-ready (24"×24", Z=0 at peak, cuts go negative)

## Orientation (CNC convention)
- X = width, Y = length, Z = up
- Z=0 at caustic peak — all cuts are negative Z
- XY origin at front-left corner (0, 0)
- Import directly into Blender or CAM software — no rotation needed

## vs Deep Variant (24in_deep)
- Deep variant: artifactSize=0.6096, f-ratio=0.5 → 37.3mm relief (needs 2"+ stock)
- Standard variant: artifactSize=0.1, f-ratio=0.131 → 6.1mm relief (fits 1" stock)
- Recommendation: use standard for 1" acrylic stock
