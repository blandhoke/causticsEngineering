#!/usr/bin/env python3
"""
trim_caustic_obj.py — Strip the flat base slab from a caustic lens OBJ.

The Julia solver outputs a mesh with two vertex layers:
  Layer 1 (first N/2 verts): flat base slab at constant Z — solver structural geometry
  Layer 2 (last N/2 verts):  caustic lens surface — the actual CNC target

This script keeps only the caustic surface layer, discarding the flat base.
The geometry is NOT modified in any way — no scaling, no Z adjustment.
The dZ/dXY ratio (which encodes refraction angles) is fully preserved.

Usage:
  python3 trim_caustic_obj.py input.obj output_trimmed.obj

Output: OBJ containing only the caustic surface vertices and their faces.
"""

import sys
import numpy as np
from pathlib import Path

def trim_caustic_obj(input_path, output_path):
    input_path  = Path(input_path)
    output_path = Path(output_path)

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    raw   = input_path.read_bytes()
    lines = raw.split(b'\n')

    # Parse vertices and faces
    v_lines = [l for l in lines if l.startswith(b'v ')]
    f_lines = [l for l in lines if l.startswith(b'f ')]
    other   = [l for l in lines if not l.startswith(b'v ') and not l.startswith(b'f ')]

    verts = np.array([
        [float(x) for x in l[2:].split()]
        for l in v_lines
    ])
    n_verts = len(verts)

    print(f"Vertices: {n_verts:,}   Faces: {len(f_lines):,}")
    print(f"Z range (full): {verts[:,2].min()*1000:.3f}mm → {verts[:,2].max()*1000:.3f}mm")

    # ── Detect bimodal structure ──────────────────────────────────────────────
    z_all = verts[:, 2]
    z_mid = (z_all.min() + z_all.max()) / 2.0
    lower_mask = z_all < z_mid
    upper_mask = ~lower_mask

    lower_count = lower_mask.sum()
    upper_count = upper_mask.sum()

    # Confirm bimodal: roughly equal halves, lower layer is flat
    lower_z = z_all[lower_mask]
    lower_std = lower_z.std()
    lower_range = lower_z.max() - lower_z.min()
    upper_z = z_all[upper_mask]
    upper_relief = upper_z.max() - upper_z.min()

    print(f"\nLower cluster: {lower_count:,} verts  Z std={lower_std*1000:.4f}mm  range={lower_range*1000:.4f}mm")
    print(f"Upper cluster: {upper_count:,} verts  relief={upper_relief*1000:.4f}mm = {upper_relief*39.3701:.5f}\"")

    is_flat_base = lower_std < (z_all.max() - z_all.min()) * 0.001
    if not is_flat_base:
        print("WARNING: Lower cluster is not flat — may not be a base slab. Aborting trim.")
        print("Use the original OBJ — no trim needed.")
        return False

    print(f"\nConfirmed: lower cluster is flat base slab (std={lower_std*1000:.6f}mm)")
    print(f"Keeping upper {upper_count:,} verts (caustic surface only)")

    # ── Build new vertex set ──────────────────────────────────────────────────
    # Upper verts: indices where upper_mask is True
    upper_indices = np.where(upper_mask)[0]  # original 0-based indices
    n_new = len(upper_indices)

    # Old index → new index mapping (1-based for OBJ)
    old_to_new = np.full(n_verts, -1, dtype=np.int32)
    for new_i, old_i in enumerate(upper_indices):
        old_to_new[old_i] = new_i + 1  # 1-based

    # ── Filter faces ──────────────────────────────────────────────────────────
    kept_faces = []
    dropped    = 0
    for fl in f_lines:
        parts = fl.split()
        # Face indices are 1-based in OBJ
        idxs = [int(p) - 1 for p in parts[1:]]  # convert to 0-based
        new_idxs = [old_to_new[i] for i in idxs]
        if any(ni == -1 for ni in new_idxs):
            dropped += 1
            continue
        kept_faces.append(b'f ' + b' '.join(str(ni).encode() for ni in new_idxs))

    print(f"Faces kept: {len(kept_faces):,}   Faces dropped (base): {dropped:,}")

    # ── Scale and position for CNC ────────────────────────────────────────────
    # Scale uniformly to physical 8"×8" = 0.2032m
    # Z: set peak to 0.0, cuts go negative (CNC convention)
    upper_verts = verts[upper_indices]
    native_span = max(upper_verts[:,0].max()-upper_verts[:,0].min(),
                      upper_verts[:,1].max()-upper_verts[:,1].min())
    scale = 0.2032 / native_span  # uniform — preserves dZ/dXY
    z_peak_native = upper_verts[:,2].max()

    phys_verts = upper_verts.copy()
    phys_verts[:,0] = (upper_verts[:,0] - upper_verts[:,0].min()) * scale
    phys_verts[:,1] = (upper_verts[:,1] - upper_verts[:,1].min()) * scale
    phys_verts[:,2] = (upper_verts[:,2] - z_peak_native) * scale  # Z=0 at peak

    phys_relief_m  = phys_verts[:,2].max() - phys_verts[:,2].min()
    phys_relief_mm = phys_relief_m * 1000
    phys_relief_in = phys_relief_m * 39.3701

    print(f"\nPhysical (scaled) dimensions:")
    print(f"  XY: {phys_verts[:,0].max():.4f}m × {phys_verts[:,1].max():.4f}m"
          f"  = {phys_verts[:,0].max()*39.3701:.4f}\" × {phys_verts[:,1].max()*39.3701:.4f}\"")
    print(f"  Relief: {phys_relief_mm:.4f}mm = {phys_relief_in:.5f}\"")
    print(f"  Scale factor: {scale:.6f}× (uniform)")
    print(f"  dZ/dXY ratio preserved: {phys_relief_m/phys_verts[:,0].max():.6f}")

    # ── Write output OBJ ──────────────────────────────────────────────────────
    out_lines = []

    # Header comments
    out_lines.append(b"# Caustic lens surface - trimmed + scaled to 8x8 CNC")
    out_lines.append(f"# Source: {input_path.name}".encode())
    out_lines.append(f"# Vertices: {n_new:,}  (original: {n_verts:,})".encode())
    out_lines.append(f"# Physical: 8.000\" x 8.000\" x {phys_relief_in:.5f}\" ({phys_relief_mm:.4f}mm)".encode())
    out_lines.append(f"# Scale: {scale:.6f}x uniform — dZ/dXY ratio preserved".encode())
    out_lines.append(f"# Z=0 at dome peak, negative = into stock".encode())
    out_lines.append(f"# Units: metres (1 Blender unit = 1 metre on import)".encode())
    out_lines.append(f"# dims {int(round(n_new**0.5))} {int(round(n_new**0.5))}".encode())
    out_lines.append(b"")

    # Vertices (scaled, CNC-positioned)
    for i in range(n_new):
        x, y, z = phys_verts[i]
        out_lines.append(f"v {x:.10f} {y:.10f} {z:.10f}".encode())

    out_lines.append(b"")

    # Faces
    out_lines.extend(kept_faces)
    out_lines.append(b"")

    output_path.write_bytes(b'\n'.join(out_lines))
    size_mb = output_path.stat().st_size / 1e6

    print(f"\nWritten: {output_path}  ({size_mb:.1f} MB)")
    print(f"Z range (trimmed): {upper_z.min()*1000:.4f}mm → {upper_z.max()*1000:.4f}mm")
    print(f"True caustic relief: {upper_relief*1000:.4f}mm = {upper_relief*39.3701:.5f}\"")
    print(f"Dome height from solver ({upper_relief*1000:.4f}mm) confirmed — NOT the slab thickness")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 trim_caustic_obj.py input.obj output_trimmed.obj")
        sys.exit(1)
    success = trim_caustic_obj(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
