#!/usr/bin/env python3
"""
combine_quads.py — Combine 4 quad OBJ meshes into one 8"x8" block OBJ.

Each quad mesh is scaled to exactly 4"x4" (0.1016m) — Z scales proportionally
to preserve surface normals and refraction angles. The 4 quads are arranged:

  Q1 (top-left)     Q2 (top-right)
  Q3 (bottom-left)  Q4 (bottom-right)

Usage:
  python3 combine_quads.py \\
    --q1 PATH --q2 PATH --q3 PATH --q4 PATH \\
    --out PATH \\
    --label "Block name"

Output is a single OBJ with all vertices then all faces (renumbered).
Run verify_obj.py on the combined mesh before use.
"""

import argparse
import numpy as np
from pathlib import Path


QUAD_SIZE_M = 0.1016   # 4 inches in metres


def load_obj(path: str):
    """Parse OBJ file, return (verts [N,3], faces [M,3])."""
    raw = Path(path).read_bytes()
    lines = raw.split(b'\n')
    v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
    f_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'f '))
    if not v_buf.strip():
        raise ValueError(f"No vertices in {path}")
    verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
    faces = np.fromstring(f_buf.decode(), dtype=np.int32,   sep=' ').reshape(-1, 3)
    return verts, faces


def normalize_and_scale(verts: np.ndarray, quad_size: float = QUAD_SIZE_M) -> np.ndarray:
    """Normalize mesh XY to start at (0,0) and scale to quad_size × quad_size.
    Z scales proportionally to preserve surface normals.
    """
    verts = verts.copy()

    # Normalize to start at (0, 0)
    verts[:, 0] -= verts[:, 0].min()
    verts[:, 1] -= verts[:, 1].min()

    xy_span = max(verts[:, 0].max(), verts[:, 1].max())
    if xy_span < 1e-9:
        raise ValueError("Degenerate mesh: zero XY span")

    scale = quad_size / xy_span
    verts[:, 0] *= scale
    verts[:, 1] *= scale
    verts[:, 2] *= scale   # Z must scale with XY to preserve refraction angles

    return verts


def offset_quad(verts: np.ndarray, x_offset: float, y_offset: float) -> np.ndarray:
    """Translate a normalized quad to its position in the 8"x8" block."""
    verts = verts.copy()
    verts[:, 0] += x_offset
    verts[:, 1] += y_offset
    return verts


def combine(quad_paths: list, out_path: str, label: str = "Combined block"):
    """Combine 4 quad OBJs into one 8"x8" block.

    Quadrant layout (viewed from above):
      Q1 offset (0,       QUAD_SIZE)   top-left
      Q2 offset (QUAD_SIZE, QUAD_SIZE) top-right
      Q3 offset (0,       0)           bottom-left
      Q4 offset (QUAD_SIZE, 0)         bottom-right
    """
    offsets = [
        (0.0,       QUAD_SIZE_M),   # Q1 top-left
        (QUAD_SIZE_M, QUAD_SIZE_M), # Q2 top-right
        (0.0,       0.0),           # Q3 bottom-left
        (QUAD_SIZE_M, 0.0),         # Q4 bottom-right
    ]

    all_verts = []
    all_faces = []
    vert_offset = 0
    stats = []

    for i, (path, (xoff, yoff)) in enumerate(zip(quad_paths, offsets), start=1):
        if not Path(path).exists():
            print(f"  WARNING: Q{i} missing: {path} — substituting empty quad")
            stats.append({'q': i, 'path': path, 'status': 'MISSING'})
            continue

        print(f"\nQ{i}: {Path(path).name}")
        verts, faces = load_obj(path)

        # Stats before scaling
        x_span = verts[:, 0].max() - verts[:, 0].min()
        y_span = verts[:, 1].max() - verts[:, 1].min()
        dome   = (verts[:, 2].max() - verts[:, 2].min()) * 1000
        print(f"  Native: XY span {x_span*1000:.1f}×{y_span*1000:.1f}mm  dome {dome:.2f}mm")
        print(f"  Vertices: {len(verts):,}  Faces: {len(faces):,}")

        verts = normalize_and_scale(verts)
        verts = offset_quad(verts, xoff, yoff)

        # Stats after scaling
        dome_scaled = (verts[:, 2].max() - verts[:, 2].min()) * 1000
        scale_factor = QUAD_SIZE_M / max(x_span, y_span)
        print(f"  Scaled:  {QUAD_SIZE_M*1000:.1f}×{QUAD_SIZE_M*1000:.1f}mm  dome {dome_scaled:.2f}mm  (scale {scale_factor:.4f}×)")
        print(f"  Offset:  ({xoff*1000:.0f}, {yoff*1000:.0f}) mm")

        if dome_scaled > 25.4:
            print(f"  *** WARNING: dome {dome_scaled:.2f}mm exceeds 1\" stock (25.4mm) ***")

        all_faces.append(faces + vert_offset + 1)  # OBJ faces are 1-indexed
        all_verts.append(verts)
        vert_offset += len(verts)
        stats.append({
            'q': i, 'path': path, 'status': 'OK',
            'native_dome_mm': dome, 'scaled_dome_mm': dome_scaled,
            'scale_factor': scale_factor,
            'verts': len(verts), 'faces': len(faces),
        })

    if not all_verts:
        raise ValueError("No valid quad meshes found — cannot combine")

    combined_verts = np.vstack(all_verts)
    combined_faces = np.vstack(all_faces)

    # Write OBJ
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(f"# {label}\n")
        f.write(f"# Combined 8\"x8\" block: {len(combined_verts):,} verts  {len(combined_faces):,} faces\n")
        f.write(f"# Quads: {' | '.join(Path(p).name for p in quad_paths)}\n")
        f.write("o combined_block\n")
        for v in combined_verts:
            f.write(f"v {v[0]:.8f} {v[1]:.8f} {v[2]:.8f}\n")
        for face in combined_faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Combined block: {label}")
    print(f"{'='*60}")
    print(f"  Total vertices:   {len(combined_verts):>10,}")
    print(f"  Total faces:      {len(combined_faces):>10,}")
    x_range = combined_verts[:, 0].max() - combined_verts[:, 0].min()
    y_range = combined_verts[:, 1].max() - combined_verts[:, 1].min()
    z_range = (combined_verts[:, 2].max() - combined_verts[:, 2].min()) * 1000
    print(f"  Block XY span:   {x_range*1000:.1f}×{y_range*1000:.1f}mm  (target 203.2×203.2mm)")
    print(f"  Z range (total): {z_range:.2f}mm")
    for s in stats:
        if s['status'] == 'OK':
            flag = " *** OVER 25.4mm ***" if s['scaled_dome_mm'] > 25.4 else ""
            print(f"  Q{s['q']}: dome {s['scaled_dome_mm']:.2f}mm{flag}")
        else:
            print(f"  Q{s['q']}: MISSING")
    print(f"  Saved → {out_path}")

    # Quick geometry validation
    print("\nGeometry validation:")
    x_min = combined_verts[:, 0].min()
    y_min = combined_verts[:, 1].min()
    if abs(x_min) > 0.001 or abs(y_min) > 0.001:
        print(f"  WARNING: Combined mesh origin ({x_min:.4f}, {y_min:.4f}) — expected near (0,0)")
    else:
        print(f"  Origin: OK ({x_min:.6f}, {y_min:.6f})")
    if x_range < 0.19 or x_range > 0.21:
        print(f"  WARNING: X span {x_range*1000:.1f}mm — expected ~203.2mm")
    else:
        print(f"  X span: OK ({x_range*1000:.1f}mm)")
    if y_range < 0.19 or y_range > 0.21:
        print(f"  WARNING: Y span {y_range*1000:.1f}mm — expected ~203.2mm")
    else:
        print(f"  Y span: OK ({y_range*1000:.1f}mm)")
    print("  Combined OBJ written successfully.")


def main():
    parser = argparse.ArgumentParser(
        description='Combine 4 quad OBJ meshes into one 8"x8" block OBJ')
    parser.add_argument('--q1',    required=True, help='Top-left quad OBJ')
    parser.add_argument('--q2',    required=True, help='Top-right quad OBJ')
    parser.add_argument('--q3',    required=True, help='Bottom-left quad OBJ')
    parser.add_argument('--q4',    required=True, help='Bottom-right quad OBJ')
    parser.add_argument('--out',   required=True, help='Output combined OBJ path')
    parser.add_argument('--label', default='Combined block', help='Block label')
    args = parser.parse_args()

    combine([args.q1, args.q2, args.q3, args.q4], args.out, label=args.label)


if __name__ == '__main__':
    main()
