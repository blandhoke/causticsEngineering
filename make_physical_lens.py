#!/usr/bin/env python3
"""
make_physical_lens.py — Scale solver OBJ to physical 8"x8" CNC dimensions.

Solver native size:  0.1m x 0.1m  (artifactSize in create_mesh.jl)
Target physical:     8"x8" = 0.2032m x 0.2032m
Scale factor:        2.032  (applied uniformly to ALL axes: X, Y, Z)

Physical throw distance:
  solver focal = 0.2m at native 0.1m size
  scaled throw = 0.2 x (0.2032 / 0.1) = 0.4064m ≈ 16"

IMPORTANT: Z must scale with XY. Refraction angles depend on dZ/dXY ratio.
           Scaling only XY would change all surface normals and destroy the caustic.
"""

from pathlib import Path
import sys

INPUT_OBJ  = Path("/Users/admin/causticsEngineering/examples/original_image.obj")
OUTPUT_OBJ = Path("/Users/admin/causticsEngineering/examples/physical_lens_8x8.obj")

NATIVE_SIZE_M  = 0.1          # solver artifactSize (metres)
TARGET_SIZE_M  = 0.2032       # 8 inches in metres
SCALE          = TARGET_SIZE_M / NATIVE_SIZE_M   # = 2.032
NATIVE_FOCAL_M = 0.2          # solver focalLength (metres)
MATERIAL_MAX_MM = 25.4        # 1" cast acrylic
MATERIAL_MIN_MM = 5.0         # too flat to mill well

print(f"── Physical Lens Scaler ──────────────────────────────")
print(f"  Input:          {INPUT_OBJ.name}")
print(f"  Output:         {OUTPUT_OBJ.name}")
print(f"  Scale factor:   {SCALE:.4f}x  (all axes)")
print(f"  Physical throw: {NATIVE_FOCAL_M * SCALE * 1000:.1f} mm  "
      f"({NATIVE_FOCAL_M * SCALE / 0.0254:.1f}\")")

print(f"\nParsing OBJ...")
raw   = INPUT_OBJ.read_bytes()
lines = raw.split(b'\n')

import numpy as np
v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)

native_dome_mm    = (verts[:,2].max() - verts[:,2].min()) * 1000
native_span_mm    = max(verts[:,0].max()-verts[:,0].min(),
                        verts[:,1].max()-verts[:,1].min()) * 1000
physical_dome_mm  = native_dome_mm  * SCALE
physical_span_mm  = native_span_mm  * SCALE

print(f"\n── Native mesh ───────────────────────────────────────")
print(f"  Vertices:       {len(verts):,}")
print(f"  XY span:        {native_span_mm:.2f} mm")
print(f"  Dome height:    {native_dome_mm:.2f} mm")

print(f"\n── Scaled (physical) ─────────────────────────────────")
print(f"  XY span:        {physical_span_mm:.2f} mm  "
      f"({physical_span_mm/25.4:.3f}\")")
print(f"  Dome height:    {physical_dome_mm:.2f} mm  "
      f"({physical_dome_mm/25.4:.3f}\")")
print(f"  Throw distance: {NATIVE_FOCAL_M * SCALE * 1000:.1f} mm  "
      f"({NATIVE_FOCAL_M * SCALE / 0.0254:.2f}\")")

# Warnings
warnings = []
if physical_dome_mm > MATERIAL_MAX_MM:
    warnings.append(f"⚠  DOME {physical_dome_mm:.1f}mm EXCEEDS 1\" MATERIAL ({MATERIAL_MAX_MM}mm) — cannot mill")
if physical_dome_mm < MATERIAL_MIN_MM:
    warnings.append(f"⚠  DOME {physical_dome_mm:.1f}mm is very shallow (<{MATERIAL_MIN_MM}mm) — may not cut well")
if warnings:
    print("\n── WARNINGS ──────────────────────────────────────────")
    for w in warnings: print(f"  {w}")
    if physical_dome_mm > MATERIAL_MAX_MM:
        sys.exit(1)
else:
    print(f"\n  ✓ Dome height fits within 1\" material")

# Write scaled OBJ
print(f"\nWriting scaled OBJ → {OUTPUT_OBJ.name} ...")
scaled_verts = verts * SCALE

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
print(f"  XY:    {physical_span_mm:.1f} mm × {physical_span_mm:.1f} mm")
print(f"  Dome:  {physical_dome_mm:.2f} mm")
print(f"  Throw: {NATIVE_FOCAL_M * SCALE * 1000:.0f} mm  "
      f"({NATIVE_FOCAL_M * SCALE / 0.0254:.1f}\")")
