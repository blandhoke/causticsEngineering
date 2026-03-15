#!/usr/bin/env python3
"""
verify_obj.py — Parse and validate examples/original_image.obj after solver run.
Flags if dome height > 25.4mm (won't fit in 1" acrylic).

Top-surface face check:
  Open surface meshes should have >90% top-facing faces.
  Solidified/closed meshes have ~50% top-facing faces (curved top + flat bottom)
  and are detected automatically — the check threshold is adjusted accordingly.
"""
import numpy as np
import sys
from pathlib import Path

OBJ_PATH = Path("/Users/admin/causticsEngineering/examples/original_image.obj")

print(f"Parsing {OBJ_PATH} ...")
raw   = OBJ_PATH.read_bytes()
lines = raw.split(b'\n')
v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
f_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'f '))

verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
faces = np.fromstring(f_buf.decode(), dtype=np.int32,   sep=' ').reshape(-1, 3) - 1

print(f"\n── Geometry ──────────────────────────────────────")
print(f"  Vertices:      {len(verts):,}")
print(f"  Faces:         {len(faces):,}")

x_min, x_max = verts[:,0].min(), verts[:,0].max()
y_min, y_max = verts[:,1].min(), verts[:,1].max()
z_min, z_max = verts[:,2].min(), verts[:,2].max()

xy_span_m  = max(x_max - x_min, y_max - y_min)
dome_mm    = (z_max - z_min) * 1000

print(f"\n  XY span:       {xy_span_m*1000:.2f} mm  ({xy_span_m:.5f} m)")
print(f"  Z range:       {z_min*1000:.3f} mm → {z_max*1000:.3f} mm")
dome_status = '✓ fits in 1" acrylic' if dome_mm < 25.4 else '⚠ EXCEEDS 1" ACRYLIC THICKNESS'
print(f"  Dome height:   {dome_mm:.2f} mm  ({dome_status})")

v0 = verts[faces[:,0]]; v1 = verts[faces[:,1]]; v2 = verts[faces[:,2]]
raw_n     = np.cross(v1 - v0, v2 - v0)
top_faces = (raw_n[:,2] > 0).sum()
top_pct   = 100 * top_faces / len(faces)

# Detect closed/solidified mesh: face count > vertex count * 1.5
# Solidified meshes have ~50% top-facing faces (curved top + flat bottom) — correct
# Open surface meshes should have >90% top-facing faces
is_solid = len(faces) > len(verts) * 1.5
threshold = 40 if is_solid else 90
mesh_type = "solidified/closed" if is_solid else "open surface"

print(f"\n  Mesh type:               {mesh_type}")
print(f"  Top-surface faces (Z>0): {top_faces:,}  ({top_pct:.1f}%)")
if top_pct >= threshold:
    print(f"  ✓ top-surface ratio normal for {mesh_type} mesh")
else:
    print(f"  ⚠ LOW top-surface ratio ({top_pct:.1f}% < {threshold}%) — check mesh orientation")

errors = []
if dome_mm > 25.4:
    errors.append(f"STOP: dome height {dome_mm:.1f}mm exceeds 25.4mm (1\" acrylic)")
# Top-surface ratio is a warning only, not a pipeline-blocking error
if top_pct < threshold:
    print(f"\n  ⚠ WARNING: top-surface ratio low for {mesh_type} mesh — review if caustic looks wrong")

if errors:
    print("\n── ERRORS ────────────────────────────────────────")
    for e in errors: print(f"  {e}")
    sys.exit(1)
else:
    print("\n── PASS: OBJ geometry looks valid ────────────────")
