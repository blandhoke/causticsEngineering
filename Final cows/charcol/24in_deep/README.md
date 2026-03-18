# Charcol 24" — Deep Dome Variant
Generated: 2026-03-17

## Settings
- CAUSTIC_ARTIFACT_SIZE = 0.6096 (24" native mesh)
- CAUSTIC_FOCAL_LENGTH  = 1.219m (48" throw)
- Source: INKFORGE/charcol.png

## Results
- Caustic relief: 37.3mm = 1.469"
- Cut depth:      1.542"
- Stock required: ~2–3" cast acrylic
- Native mesh span: 1220mm (2× target — scaled 0.5× to reach 24")

## Note
artifactSize=0.6096 produces a native mesh that is 2× the physical target
(native span = 2 × artifactSize). Scaling to 24" halves everything BUT the
h-values from findSurface at this focalLength still produce deep geometry.
The f-ratio (artifactSize/focalLength = 0.6096/1.219 = 0.5) is 4× "faster"
than the 8" design (0.1/0.762 = 0.131) — this drives the deeper relief.

## Use case
If 2"+ stock is available, this variant offers richer lens geometry.
Compare against charcol/24in_standard (artifactSize=0.1) for visual diff.
