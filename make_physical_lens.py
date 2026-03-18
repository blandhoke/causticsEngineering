#!/usr/bin/env python3
"""
make_physical_lens.py — Scale solver OBJ to physical 8"x8" CNC dimensions.

Target physical:     8"x8" = 0.2032m x 0.2032m
Scale factor:        computed dynamically from actual native OBJ span
                     (solver output varies: ~0.1m at 512px, ~0.2m at 1024px)

IMPORTANT: Z must scale with XY. Refraction angles depend on dZ/dXY ratio.
           Scaling only XY would change all surface normals and destroy the caustic.

Material limits:
  Max dome: 25.4mm (1" cast acrylic)
  Min dome: 5.0mm  (too flat to mill well)
  Script warns if dome exceeds limit but always writes the CNC file.
"""

from pathlib import Path
import os
import sys
import numpy as np

INPUT_OBJ  = Path("/Users/admin/causticsEngineering/examples/original_image.obj")
_size_in   = round(float(os.environ.get("CAUSTIC_TARGET_SIZE", "0.6096")) / 0.0254)
OUTPUT_OBJ = Path(f"/Users/admin/causticsEngineering/examples/physical_lens_{int(_size_in)}x{int(_size_in)}.obj")

# Match CAUSTIC_ARTIFACT_SIZE and CAUSTIC_FOCAL_LENGTH used in the solver run
TARGET_SIZE_M   = float(os.environ.get("CAUSTIC_TARGET_SIZE",   "0.6096"))  # default 24"
NATIVE_FOCAL_M  = float(os.environ.get("CAUSTIC_FOCAL_LENGTH",  "1.219"))   # default 48" throw
MATERIAL_1IN_MM  = 25.4    # 1" cast acrylic (reference only — not a hard limit)
MATERIAL_2IN_MM  = 50.8    # 2" cast acrylic (reference only)
MATERIAL_MIN_MM  = 5.0     # too flat to mill well

print(f"── Physical Lens Scaler ──────────────────────────────")
print(f"  Input:  {INPUT_OBJ.name}")
print(f"  Output: {OUTPUT_OBJ.name}")
print(f"  Target: {TARGET_SIZE_M*1000:.1f} mm x {TARGET_SIZE_M*1000:.1f} mm  ({TARGET_SIZE_M/0.0254:.0f}\")")

print(f"\nParsing OBJ...")
raw   = INPUT_OBJ.read_bytes()
lines = raw.split(b'\n')
v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)

native_span_m  = max(verts[:,0].max()-verts[:,0].min(),
                     verts[:,1].max()-verts[:,1].min())
native_dome_mm = (verts[:,2].max() - verts[:,2].min()) * 1000
native_span_mm = native_span_m * 1000

# Dynamic scale: computed from actual OBJ span, not assumed constant
SCALE = TARGET_SIZE_M / native_span_m

physical_dome_mm = native_dome_mm * SCALE
physical_span_mm = native_span_mm * SCALE
physical_throw_m = NATIVE_FOCAL_M  # throw is a fixed installation distance, does not scale with lens size

print(f"\n── Native mesh ───────────────────────────────────────")
print(f"  Vertices:    {len(verts):,}")
print(f"  XY span:     {native_span_mm:.2f} mm  ({native_span_m:.5f} m)")
print(f"  Dome height: {native_dome_mm:.2f} mm")

print(f"\n── Scale factor ──────────────────────────────────────")
print(f"  {TARGET_SIZE_M*1000:.1f} mm / {native_span_mm:.2f} mm = {SCALE:.4f}x  (all axes)")

print(f"\n── Scaled (physical) ─────────────────────────────────")
print(f"  XY span:        {physical_span_mm:.2f} mm  ({physical_span_mm/25.4:.3f}\")")
print(f"  Dome height:    {physical_dome_mm:.2f} mm  ({physical_dome_mm/25.4:.3f}\")")
print(f"  Throw distance: {physical_throw_m*1000:.1f} mm  ({physical_throw_m/0.0254:.2f}\")")

# Stock guidance deferred — printed after caustic_relief_mm is computed below

# Scale vertices
scaled_verts = verts * SCALE

# ── Axis correction (Y/Z swap) ─────────────────────────────────────────────
# Solver outputs Z as the 8" axis and Y as the ~2mm relief axis.
# CNC convention: X=width, Y=length, Z=up (relief). Detect and fix.
y_span = scaled_verts[:,1].max() - scaled_verts[:,1].min()
z_span = scaled_verts[:,2].max() - scaled_verts[:,2].min()

if z_span > y_span * 5:
    print(f"\n── Axis correction ───────────────────────────────────")
    print(f"  Detected Y/Z swap (Z span={z_span*1000:.1f}mm >> Y span={y_span*1000:.1f}mm)")
    print(f"  Rotating -90° around X: Y→Z, Z→-Y")
    old_y = scaled_verts[:,1].copy()
    old_z = scaled_verts[:,2].copy()
    scaled_verts[:,1] = old_z     # new Y = old Z (the 8" length axis)
    scaled_verts[:,2] = -old_y    # new Z = -old Y (relief, pointing up)
else:
    print(f"\n── Axis correction ───────────────────────────────────")
    print(f"  Axes already correct (Y span={y_span*1000:.1f}mm, Z span={z_span*1000:.1f}mm)")

# ── Reposition to CNC origin ───────────────────────────────────────────────
# Find upper vertex cluster (caustic surface) via bimodal Z split
z = scaled_verts[:,2]
z_mid = (z.min() + z.max()) / 2
upper_z = z[z >= z_mid]
z_peak = upper_z.max()
caustic_relief_mm = (upper_z.max() - upper_z.min()) * 1000

# Stock guidance (informational only — based on caustic relief, the CNC-relevant depth)
if caustic_relief_mm <= MATERIAL_1IN_MM:
    print(f"\n  ✓ Relief {caustic_relief_mm:.2f}mm fits 1\" stock ({MATERIAL_1IN_MM}mm)")
elif caustic_relief_mm <= MATERIAL_2IN_MM:
    print(f"\n  ⚠  Relief {caustic_relief_mm:.2f}mm exceeds 1\" stock — use 2\" cast acrylic")
else:
    print(f"\n  ⚠  Relief {caustic_relief_mm:.2f}mm exceeds 2\" stock — use custom thickness")
if caustic_relief_mm < MATERIAL_MIN_MM:
    print(f"  ⚠  Relief {caustic_relief_mm:.2f}mm is very shallow (<{MATERIAL_MIN_MM}mm) — may not cut well")

# Shift: XY origin at front-left corner, Z=0 at caustic peak (cuts go negative)
scaled_verts[:,0] -= scaled_verts[:,0].min()
scaled_verts[:,1] -= scaled_verts[:,1].min()
scaled_verts[:,2] -= z_peak

cut_depth_in = (caustic_relief_mm * 1.05) / 25.4

print(f"\n── CAUSTICFORGE-READY ────────────────────────────────")
print(f"  Axis orientation: X=width Y=length Z=up (CNC convention) ✓")
print(f"  XY origin: front-left corner at (0, 0) ✓")
print(f"  Z=0 at caustic peak, cuts go negative ✓")
print(f"  Caustic relief: {caustic_relief_mm:.3f}mm = {caustic_relief_mm/25.4:.4f}\"")
print(f"  Cut depth (relief + 5%): {cut_depth_in:.4f}\"")
print(f"  Ready to import into Blender — no manual rotation needed")

# Write scaled + corrected OBJ
print(f"\nWriting scaled OBJ → {OUTPUT_OBJ.name} ...")
out_lines = []
vi = 0
for line in lines:
    if line.startswith(b'v '):
        x, y, z = scaled_verts[vi]
        out_lines.append(f"v {x:.8f} {y:.8f} {z:.8f}".encode())
        vi += 1
    else:
        out_lines.append(line)

OUTPUT_OBJ.write_bytes(b'\n'.join(out_lines))
size_mb = OUTPUT_OBJ.stat().st_size / 1e6
print(f"  Written: {size_mb:.1f} MB")
print(f"\n── Done ──────────────────────────────────────────────")
print(f"  Physical OBJ: {OUTPUT_OBJ}")
print(f"  XY:    {physical_span_mm:.1f} mm x {physical_span_mm:.1f} mm")
print(f"  Dome:  {physical_dome_mm:.2f} mm")
print(f"  Throw: {physical_throw_m*1000:.0f} mm  ({physical_throw_m/0.0254:.1f}\")")
