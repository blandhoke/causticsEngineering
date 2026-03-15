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
  Script exits non-zero if dome exceeds material thickness.
"""

from pathlib import Path
import sys
import numpy as np

INPUT_OBJ  = Path("/Users/admin/causticsEngineering/examples/original_image.obj")
OUTPUT_OBJ = Path("/Users/admin/causticsEngineering/examples/physical_lens_8x8.obj")

TARGET_SIZE_M   = 0.2032   # 8 inches in metres
NATIVE_FOCAL_M  = 0.75     # solver focalLength (metres) — must match focalLength in create_mesh.jl
MATERIAL_MAX_MM = 25.4     # 1" cast acrylic
MATERIAL_MIN_MM = 5.0      # too flat to mill well

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
physical_throw_m = NATIVE_FOCAL_M * SCALE

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

# Warnings
warnings = []
if physical_dome_mm > MATERIAL_MAX_MM:
    warnings.append(
        f"DOME {physical_dome_mm:.1f}mm EXCEEDS 1\" MATERIAL ({MATERIAL_MAX_MM}mm) — cannot mill\n"
        f"  Options:\n"
        f"    (a) Use 1.5\" (38.1mm) or 2\" (50.8mm) cast acrylic stock\n"
        f"    (b) Reduce physical size: max span for 1\" = {native_dome_mm * 25.4 / native_dome_mm:.0f}mm "
        f"→ need MATERIAL_MAX_MM >= {physical_dome_mm:.0f}mm\n"
        f"    (c) Reduce solver focalLength in create_mesh.jl to produce shallower dome"
    )
if physical_dome_mm < MATERIAL_MIN_MM:
    warnings.append(f"DOME {physical_dome_mm:.1f}mm is very shallow (<{MATERIAL_MIN_MM}mm) — may not cut well")

if warnings:
    print("\n── WARNINGS ──────────────────────────────────────────")
    for w in warnings:
        print(f"  ⚠  {w}")
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
print(f"  XY:    {physical_span_mm:.1f} mm x {physical_span_mm:.1f} mm")
print(f"  Dome:  {physical_dome_mm:.2f} mm")
print(f"  Throw: {physical_throw_m*1000:.0f} mm  ({physical_throw_m/0.0254:.1f}\")")
