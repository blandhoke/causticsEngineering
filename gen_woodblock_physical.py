#!/usr/bin/env python3
"""
gen_woodblock_physical.py — Generate 24" and 8" physical lens OBJs from woodblock/normal mesh.
One-shot script for HANDOFF v001 Task 2. Uses the same logic as make_physical_lens.py.
"""

from pathlib import Path
import numpy as np
import sys

BASE = Path("/Users/admin/Documents/Claude/causticsEngineering_v1")

INPUT_OBJ = BASE / "Final cows/woodblock/normal/mesh.obj"

TARGETS = [
    {
        "name": "24in",
        "target_m": 0.6096,       # 24 inches
        "focal_m": 1.219,         # 48" throw
        "output": BASE / "Final cows/woodblock/24in_standard/physical_lens_24x24.obj",
    },
    {
        "name": "8in",
        "target_m": 0.2032,       # 8 inches
        "focal_m": 0.75,          # 30" throw (standard for 8" pieces)
        "output": BASE / "Final cows/woodblock/8in/physical_lens_8x8.obj",
    },
]

# ── Parse OBJ once ──────────────────────────────────────────────────────────────
print(f"Parsing OBJ: {INPUT_OBJ.name} ...")
raw = INPUT_OBJ.read_bytes()
lines = raw.split(b'\n')
v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
verts_orig = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
print(f"  {len(verts_orig):,} vertices")

native_span_m = max(verts_orig[:,0].max()-verts_orig[:,0].min(),
                    verts_orig[:,1].max()-verts_orig[:,1].min())
print(f"  Native XY span: {native_span_m*1000:.2f} mm")

for cfg in TARGETS:
    print(f"\n{'='*60}")
    print(f"  Generating: {cfg['name']} ({cfg['target_m']*1000:.0f}mm x {cfg['target_m']*1000:.0f}mm)")
    print(f"{'='*60}")

    SCALE = cfg["target_m"] / native_span_m
    verts = verts_orig.copy() * SCALE

    # Axis correction (Y/Z swap)
    y_span = verts[:,1].max() - verts[:,1].min()
    z_span = verts[:,2].max() - verts[:,2].min()

    if z_span > y_span * 5:
        print(f"  Axis correction: Z span={z_span*1000:.1f}mm >> Y span={y_span*1000:.1f}mm → rotating")
        old_y = verts[:,1].copy()
        old_z = verts[:,2].copy()
        verts[:,1] = old_z
        verts[:,2] = -old_y
    else:
        print(f"  Axes already correct (Y={y_span*1000:.1f}mm, Z={z_span*1000:.1f}mm)")

    # Bimodal split: find caustic surface relief
    z = verts[:,2]
    z_mid = (z.min() + z.max()) / 2
    upper_z = z[z >= z_mid]
    z_peak = upper_z.max()
    caustic_relief_mm = (upper_z.max() - upper_z.min()) * 1000

    # Reposition to CNC origin
    verts[:,0] -= verts[:,0].min()
    verts[:,1] -= verts[:,1].min()
    verts[:,2] -= z_peak

    xy_span = max(verts[:,0].max(), verts[:,1].max())
    z_range = verts[:,2].max() - verts[:,2].min()

    print(f"  Scale factor: {SCALE:.4f}x")
    print(f"  XY span: {xy_span*1000:.2f} mm ({xy_span/0.0254:.3f}\")")
    print(f"  Caustic relief: {caustic_relief_mm:.3f} mm ({caustic_relief_mm/25.4:.4f}\")")
    print(f"  Full Z range: {z_range*1000:.2f} mm")
    print(f"  Z: {verts[:,2].min()*1000:.3f} to {verts[:,2].max()*1000:.3f} mm")

    if caustic_relief_mm <= 25.4:
        print(f"  ✓ Fits 1\" stock ({25.4 - caustic_relief_mm:.1f}mm margin)")
    else:
        print(f"  ⚠ Exceeds 1\" stock — needs {caustic_relief_mm/25.4:.2f}\" material")

    # Write OBJ
    print(f"  Writing: {cfg['output'].name} ...")
    out_lines = []
    vi = 0
    for line in lines:
        if line.startswith(b'v '):
            x, y, zv = verts[vi]
            out_lines.append(f"v {x:.8f} {y:.8f} {zv:.8f}".encode())
            vi += 1
        else:
            out_lines.append(line)

    cfg['output'].write_bytes(b'\n'.join(out_lines))
    size_mb = cfg['output'].stat().st_size / 1e6
    print(f"  Written: {size_mb:.1f} MB")

    # Verification
    print(f"\n  ── Verification ──")
    print(f"  File: {cfg['output']}")
    print(f"  Vertices: {len(verts):,}")
    print(f"  XY span: {xy_span/0.0254:.4f}\" (target: {cfg['target_m']/0.0254:.1f}\")")
    print(f"  XY error: {abs(xy_span - cfg['target_m'])*1000:.2f} mm")
    print(f"  Caustic relief: {caustic_relief_mm:.3f} mm = {caustic_relief_mm/25.4:.4f}\"")
    print(f"  Dual-surface correction: NOT APPLIED (not needed — solver uses thin lens formula)")

print(f"\n{'='*60}")
print("Done. Both OBJs generated.")
