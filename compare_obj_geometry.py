#!/usr/bin/env python3
"""
compare_obj_geometry.py — Deep geometric comparison of two lens OBJ meshes.

Usage:
  python3 compare_obj_geometry.py --a PATH --b PATH [--label-a STR] [--label-b STR]

Compares: vertex counts, dome geometry, height field statistics, surface curvature,
vertex displacement map between the two meshes, and cross-correlation of height fields.
"""

import argparse
import numpy as np
from pathlib import Path
from scipy.ndimage import gaussian_filter
from scipy.stats import pearsonr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_obj(path):
    raw   = Path(path).read_bytes()
    lines = raw.split(b'\n')
    v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
    f_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'f '))
    verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
    faces = np.fromstring(f_buf.decode(), dtype=np.int32,   sep=' ').reshape(-1, 3) - 1
    return verts, faces


def top_surface_verts(verts, faces):
    """Return only vertices belonging to top-facing faces."""
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    top_mask = normals[:, 2] > 0
    top_idx  = np.unique(faces[top_mask].ravel())
    return verts[top_idx], top_idx


def height_field_grid(verts, n=256):
    """Interpolate scattered top-surface vertices onto a regular n×n grid."""
    from scipy.interpolate import griddata
    x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
    xi = np.linspace(x.min(), x.max(), n)
    yi = np.linspace(y.min(), y.max(), n)
    XX, YY = np.meshgrid(xi, yi)
    ZZ = griddata((x, y), z, (XX, YY), method='linear')
    return ZZ, xi, yi


def surface_curvature(Z, dx):
    """Approximate mean curvature from height field via Laplacian."""
    from scipy.ndimage import laplace
    return laplace(np.nan_to_num(Z)) / (dx ** 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--a',       required=True)
    parser.add_argument('--b',       required=True)
    parser.add_argument('--label-a', default='Mesh A')
    parser.add_argument('--label-b', default='Mesh B')
    parser.add_argument('--out-png', default=None)
    parser.add_argument('--out-txt', default=None)
    args = parser.parse_args()

    print(f"\nComparing OBJ meshes:")
    print(f"  A: {args.a}")
    print(f"  B: {args.b}\n")

    vA, fA = load_obj(args.a)
    vB, fB = load_obj(args.b)

    lines = []
    def p(s=''):
        print(s)
        lines.append(s)

    p("=" * 60)
    p(f"  {args.label_a}  vs  {args.label_b}")
    p("=" * 60)

    # ── Basic geometry ─────────────────────────────────────────────
    p("\n── Vertex / Face counts ──────────────────────────────────")
    p(f"  Vertices:  {len(vA):>10,}   {len(vB):>10,}   {'MATCH' if len(vA)==len(vB) else 'DIFFER'}")
    p(f"  Faces:     {len(fA):>10,}   {len(fB):>10,}   {'MATCH' if len(fA)==len(fB) else 'DIFFER'}")

    # ── Bounding box ───────────────────────────────────────────────
    p("\n── Bounding Box ──────────────────────────────────────────")
    for label, v in [(args.label_a, vA), (args.label_b, vB)]:
        span = max(v[:,0].max()-v[:,0].min(), v[:,1].max()-v[:,1].min())
        dome = (v[:,2].max() - v[:,2].min()) * 1000
        cx   = (v[:,0].max()+v[:,0].min()) / 2
        cy   = (v[:,1].max()+v[:,1].min()) / 2
        p(f"  {label}:")
        p(f"    XY span:     {span*1000:.3f} mm")
        p(f"    Dome height: {dome:.3f} mm   (z {v[:,2].min()*1000:.3f} → {v[:,2].max()*1000:.3f} mm)")
        p(f"    Centroid:    ({cx*1000:.3f}, {cy*1000:.3f}) mm")

    # ── Top-surface height statistics ──────────────────────────────
    p("\n── Top-Surface Height Field Statistics ───────────────────")
    tvA, _ = top_surface_verts(vA, fA)
    tvB, _ = top_surface_verts(vB, fB)
    for label, tv in [(args.label_a, tvA), (args.label_b, tvB)]:
        z = tv[:, 2]
        p(f"  {label}  (top verts: {len(tv):,})")
        p(f"    z mean:    {z.mean()*1000:.4f} mm")
        p(f"    z std:     {z.std()*1000:.4f} mm")
        p(f"    z p5:      {np.percentile(z,5)*1000:.4f} mm")
        p(f"    z p50:     {np.percentile(z,50)*1000:.4f} mm")
        p(f"    z p95:     {np.percentile(z,95)*1000:.4f} mm")
        p(f"    z range:   {(z.max()-z.min())*1000:.4f} mm")

    # ── Height field grid comparison (requires matching resolution) ─
    p("\n── Height Field Cross-Comparison (256×256 grid) ──────────")
    N = 256
    try:
        # Align both to same XY extent for fair comparison
        x_min = max(tvA[:,0].min(), tvB[:,0].min())
        x_max = min(tvA[:,0].max(), tvB[:,0].max())
        y_min = max(tvA[:,1].min(), tvB[:,1].min())
        y_max = min(tvA[:,1].max(), tvB[:,1].max())

        from scipy.interpolate import griddata
        xi = np.linspace(x_min, x_max, N)
        yi = np.linspace(y_min, y_max, N)
        XX, YY = np.meshgrid(xi, yi)

        ZA = griddata((tvA[:,0], tvA[:,1]), tvA[:,2], (XX, YY), method='linear')
        ZB = griddata((tvB[:,0], tvB[:,1]), tvB[:,2], (XX, YY), method='linear')

        # Mask NaN (outside convex hull)
        mask = ~(np.isnan(ZA) | np.isnan(ZB))
        ZA_v, ZB_v = ZA[mask], ZB[mask]

        diff = ZA_v - ZB_v
        p(f"  Valid comparison pixels: {mask.sum():,} / {N*N:,} ({100*mask.mean():.1f}%)")
        p(f"  Height difference (A - B):")
        p(f"    Mean:    {diff.mean()*1000:+.4f} mm  ({'A higher' if diff.mean()>0 else 'B higher'})")
        p(f"    Std:     {diff.std()*1000:.4f} mm")
        p(f"    Max abs: {np.abs(diff).max()*1000:.4f} mm")
        p(f"    RMS:     {np.sqrt((diff**2).mean())*1000:.4f} mm")

        r, pval = pearsonr(ZA_v, ZB_v)
        p(f"  Pearson r (height correlation): {r:.6f}")
        p(f"  Height fields are {'NEARLY IDENTICAL (r>0.999)' if r > 0.999 else 'SIMILAR (r>0.99)' if r > 0.99 else 'MODERATELY CORRELATED' if r > 0.9 else 'SIGNIFICANTLY DIFFERENT'}")

        # Curvature comparison
        dx = (x_max - x_min) / N
        CA = surface_curvature(ZA, dx)
        CB = surface_curvature(ZB, dx)
        CA_v = CA[mask]
        CB_v = CB[mask]
        p(f"\n  Surface curvature (Laplacian, mm⁻¹):")
        p(f"    {args.label_a}: mean={CA_v.mean()*1000:+.4f}  std={CA_v.std()*1000:.4f}  rms={np.sqrt((CA_v**2).mean())*1000:.4f}")
        p(f"    {args.label_b}: mean={CB_v.mean()*1000:+.4f}  std={CB_v.std()*1000:.4f}  rms={np.sqrt((CB_v**2).mean())*1000:.4f}")
        p(f"    RMS curvature ratio (B/A): {CB_v.std() / max(CA_v.std(), 1e-12):.4f}")
        p(f"    {'B has HIGHER curvature (sharper features)' if CB_v.std() > CA_v.std() else 'A has HIGHER curvature'}")

        # ── Comparison figure ──────────────────────────────────────
        out_png = args.out_png or str(Path(args.a).parent / 'obj_comparison.png')
        fig, axes = plt.subplots(1, 4, figsize=(20, 5), facecolor='black')

        ZA_full = ZA.copy(); ZA_full[~mask] = np.nan
        ZB_full = ZB.copy(); ZB_full[~mask] = np.nan
        diff_full = np.full((N, N), np.nan)
        diff_full[mask] = diff

        vmin = min(np.nanmin(ZA_full), np.nanmin(ZB_full))
        vmax = max(np.nanmax(ZA_full), np.nanmax(ZB_full))

        axes[0].imshow(ZA_full, origin='lower', cmap='viridis', vmin=vmin, vmax=vmax)
        axes[0].set_title(f'{args.label_a}\nHeight field', color='white', fontsize=9)

        axes[1].imshow(ZB_full, origin='lower', cmap='viridis', vmin=vmin, vmax=vmax)
        axes[1].set_title(f'{args.label_b}\nHeight field', color='white', fontsize=9)

        lim = np.nanpercentile(np.abs(diff_full), 95)
        im = axes[2].imshow(diff_full * 1000, origin='lower', cmap='RdBu_r',
                            vmin=-lim*1000, vmax=lim*1000)
        axes[2].set_title(f'Difference (A - B)\nmm, 95th pct = ±{lim*1000:.3f}mm', color='white', fontsize=9)
        plt.colorbar(im, ax=axes[2], label='mm')

        curv_diff = CA - CB
        curv_diff[~mask] = np.nan
        lim_c = np.nanpercentile(np.abs(curv_diff), 95)
        axes[3].imshow(curv_diff, origin='lower', cmap='RdBu_r',
                       vmin=-lim_c, vmax=lim_c)
        axes[3].set_title(f'Curvature diff (A - B)\nRed=A sharper, Blue=B sharper', color='white', fontsize=9)

        for ax in axes:
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_facecolor('black')
        fig.suptitle(f'OBJ Geometry Comparison\n{Path(args.a).name}  vs  {Path(args.b).name}',
                     color='#ddd', fontsize=10)
        plt.tight_layout()
        plt.savefig(out_png, dpi=150, bbox_inches='tight', facecolor='black')
        plt.close()
        p(f"\nComparison figure → {out_png}")

    except Exception as e:
        p(f"  Grid comparison failed: {e}")

    p("\n" + "=" * 60)

    if args.out_txt:
        Path(args.out_txt).write_text('\n'.join(lines))
        print(f"\nReport → {args.out_txt}")


if __name__ == '__main__':
    main()
