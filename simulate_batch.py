#!/usr/bin/env python3
"""
simulate_batch.py — Parameterized ray tracer for Final Cows batch pipeline.
All paths passed as CLI arguments. No hardcoded paths. Auto-sigma from face count.

Usage:
  python3 simulate_batch.py --obj path/to/mesh.obj --accum path/accum.npy \
      --meta path/meta.npy --output path/caustic.png --label "slug (speed)"

Crispness controls (all optional):
  --sigma       override auto-sigma (float; default: auto from face count)
  --post-sigma  gaussian_filter sigma after render (float; 0.0 = disabled; default: 0.5)
  --interp      matplotlib interpolation: 'bilinear' or 'nearest' (default: 'nearest')
  --gamma       gamma power applied to normalized accumulator (float; default: 0.5)
  --passes      N_PASSES (int; default: 4)

Cache invalidation:
  Cache is physics-dependent (sigma, passes, focal, ior, res).
  Post-process params (post-sigma, interp, gamma) never require cache regeneration.
  Delete accum.npy + meta.npy to force re-simulation.
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--obj',        required=True)
parser.add_argument('--accum',      required=True)
parser.add_argument('--meta',       required=True)
parser.add_argument('--output',     required=True)
parser.add_argument('--label',      default='caustic')
parser.add_argument('--passes',     type=int,   default=16)
parser.add_argument('--focal',      type=float, default=0.75)
parser.add_argument('--ior',        type=float, default=1.49)
parser.add_argument('--res',        type=int,   default=512)
parser.add_argument('--sigma',      type=float, default=None,
                    help='Override auto-sigma. Default: 1.5*sqrt(525000/top_faces)')
parser.add_argument('--post-sigma', type=float, default=0.0, dest='post_sigma',
                    help='Post-process gaussian_filter sigma. 0.0 to disable.')
parser.add_argument('--interp',     default='nearest',
                    choices=['bilinear', 'nearest'],
                    help='matplotlib imshow interpolation (default: nearest)')
parser.add_argument('--gamma',      type=float, default=0.70,
                    help='Gamma power applied to normalized accumulator (default: 0.70)')
parser.add_argument('--unsharp',    type=float, default=0.0,
                    help='Unsharp mask amount (0.0=disabled). Applied before gamma on linear accum.')
args = parser.parse_args()

OBJ_PATH    = Path(args.obj)
ACCUM_PATH  = Path(args.accum)
META_PATH   = Path(args.meta)
OUTPUT_PATH = Path(args.output)
LABEL       = args.label
N_PASSES    = args.passes
FOCAL_DIST  = args.focal
IOR         = args.ior
IMAGE_RES   = args.res
SIGMA_OVR   = args.sigma
POST_SIGMA  = args.post_sigma
INTERP      = args.interp
GAMMA       = args.gamma
UNSHARP     = args.unsharp   # float; 0.0 = disabled
BATCH_SIZE  = 100_000

CMAP = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

def refract_batch(d, n_hat, n_ratio):
    cos_i  = np.einsum('ij,ij->i', -d, n_hat).clip(0.0, 1.0)
    sin2_t = n_ratio**2 * (1.0 - cos_i**2)
    valid  = sin2_t <= 1.0
    cos_t  = np.sqrt(np.maximum(0.0, 1.0 - sin2_t))
    d_out  = n_ratio * d + (n_ratio * cos_i - cos_t)[:, None] * n_hat
    mag    = np.linalg.norm(d_out, axis=1, keepdims=True)
    d_out /= np.where(mag > 0, mag, 1.0)
    return d_out, valid

if ACCUM_PATH.exists() and META_PATH.exists():
    print(f"[{LABEL}] Loading cache: {ACCUM_PATH.name}")
    accum = np.load(ACCUM_PATH)
    meta  = np.load(META_PATH)
    xmin, xmax, ymin, ymax = meta
else:
    print(f"[{LABEL}] Parsing OBJ: {OBJ_PATH.name} ...")
    raw   = OBJ_PATH.read_bytes()
    lines = raw.split(b'\n')
    v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
    f_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'f '))
    verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
    faces = np.fromstring(f_buf.decode(), dtype=np.int32,   sep=' ').reshape(-1, 3) - 1
    print(f"[{LABEL}]   {len(verts):,} vertices | {len(faces):,} faces")

    v0r = verts[faces[:, 0]]; v1r = verts[faces[:, 1]]; v2r = verts[faces[:, 2]]
    raw_n_all = np.cross(v1r - v0r, v2r - v0r)
    top_idx   = np.where(raw_n_all[:, 2] > 0)[0]
    n_top     = len(top_idx)

    if SIGMA_OVR is not None:
        splat_sigma  = SIGMA_OVR
        splat_radius = max(1, int(round(splat_sigma * 2)))
        print(f"[{LABEL}]   top_faces={n_top:,}  sigma={splat_sigma:.3f} (override)  radius={splat_radius}")
    else:
        splat_sigma  = 1.5 * np.sqrt(525_000 / max(n_top, 1))
        splat_radius = max(2, int(round(splat_sigma * 1.5)))
        print(f"[{LABEL}]   top_faces={n_top:,}  sigma={splat_sigma:.3f} (auto)  radius={splat_radius}")

    z_min, z_max = verts[:, 2].min(), verts[:, 2].max()
    cx = (verts[:, 0].min() + verts[:, 0].max()) / 2
    cy = (verts[:, 1].min() + verts[:, 1].max()) / 2
    lens_span = max(verts[:,0].max()-verts[:,0].min(), verts[:,1].max()-verts[:,1].min())
    light_pos = np.array([cx, cy, z_max + FOCAL_DIST])
    plane_z   = z_min - FOCAL_DIST
    print(f"[{LABEL}]   dome={(z_max-z_min)*1000:.2f}mm  light_z={light_pos[2]:.4f}  plane_z={plane_z:.4f}")

    pad  = lens_span * 1.5
    xmin, xmax = cx - pad, cx + pad
    ymin, ymax = cy - pad, cy + pad
    accum = np.zeros((IMAGE_RES, IMAGE_RES), dtype=np.float64)

    ks     = range(-splat_radius, splat_radius + 1)
    kernel = {(dy, dx): np.exp(-(dx**2 + dy**2) / (2 * splat_sigma**2))
              for dy in ks for dx in ks}

    print(f"[{LABEL}] Tracing {N_PASSES} passes (sigma={splat_sigma:.3f} radius={splat_radius}) ...")
    n_hit_total = 0
    total = n_top
    np.random.seed(42)

    for start in range(0, total, BATCH_SIZE):
        batch = top_idx[start : start + BATCH_SIZE]
        b0 = verts[faces[batch, 0]]
        b1 = verts[faces[batch, 1]]
        b2 = verts[faces[batch, 2]]
        raw_n = np.cross(b1 - b0, b2 - b0)
        mag_n = np.linalg.norm(raw_n, axis=1, keepdims=True)
        ns    = raw_n / np.where(mag_n > 0, mag_n, 1.0)
        areas = mag_n[:, 0] * 0.5

        for _ in range(N_PASSES):
            ra = np.random.rand(len(batch))
            rb = np.random.rand(len(batch))
            fold = ra + rb > 1; ra[fold] = 1 - ra[fold]; rb[fold] = 1 - rb[fold]
            cents = ra[:,None]*b0 + rb[:,None]*b1 + (1-ra-rb)[:,None]*b2

            d_in = cents - light_pos[None, :]
            r2   = np.sum(d_in**2, axis=1)
            d_in /= np.linalg.norm(d_in, axis=1, keepdims=True)

            d_glass, valid = refract_batch(d_in, ns, n_ratio=1.0 / IOR)
            cos_i = np.einsum('ij,ij->i', -d_in, ns).clip(0, 1)

            dz_g  = d_glass[:, 2]
            t_bot = np.where(dz_g < -1e-12, (z_min - cents[:, 2]) / dz_g, -1.0)
            valid &= t_bot > 0
            exit_p = cents + t_bot[:, None] * d_glass

            n_bot = np.zeros_like(exit_p); n_bot[:, 2] = 1.0
            d_exit, valid2 = refract_batch(d_glass, n_bot, n_ratio=IOR)
            valid &= valid2

            dz_e  = d_exit[:, 2]
            t_pln = np.where(np.abs(dz_e) > 1e-12, (plane_z - exit_p[:, 2]) / dz_e, -1.0)
            valid &= t_pln > 0
            hits  = exit_p + t_pln[:, None] * d_exit

            hx = hits[valid, 0]; hy = hits[valid, 1]
            w  = areas[valid] * cos_i[valid] / np.where(r2[valid] > 0, r2[valid], 1.0)
            px = ((hx - xmin) / (xmax - xmin) * IMAGE_RES).astype(np.int32)
            py = ((hy - ymin) / (ymax - ymin) * IMAGE_RES).astype(np.int32)
            ok = (px >= 0) & (px < IMAGE_RES) & (py >= 0) & (py < IMAGE_RES)

            for dy in range(-splat_radius, splat_radius + 1):
                for dx in range(-splat_radius, splat_radius + 1):
                    g   = kernel[(dy, dx)]
                    pxc = (px[ok] + dx).clip(0, IMAGE_RES - 1)
                    pyc = (py[ok] + dy).clip(0, IMAGE_RES - 1)
                    np.add.at(accum, (pyc, pxc), w[ok] * g)
            n_hit_total += int(ok.sum())

        pct = 100 * min(start + BATCH_SIZE, total) / total
        print(f"[{LABEL}]   {min(start+BATCH_SIZE,total):>7,}/{total:,} ({pct:.0f}%)", end='\r')

    accum /= N_PASSES
    hit_rate = 100 * n_hit_total / (total * N_PASSES) if total > 0 else 0
    print(f"\n[{LABEL}]   hit_rate={hit_rate:.1f}%  sigma={splat_sigma:.3f}  faces={n_top:,}")
    np.save(ACCUM_PATH, accum)
    np.save(META_PATH,  np.array([xmin, xmax, ymin, ymax]))

# ── Render ─────────────────────────────────────────────────────────────────────
sigma_label = f"{SIGMA_OVR:.3f} (manual)" if SIGMA_OVR is not None else "auto"
print(f"[{LABEL}] Parameters: sigma={sigma_label}  passes={N_PASSES}  gamma={GAMMA}"
      f"  post-sigma={POST_SIGMA}  interp={INTERP}  unsharp={UNSHARP}")

img = np.fliplr(accum.copy())
if img.max() > 0: img /= img.max()

# Unsharp mask — applied BEFORE gamma on linear normalized accumulator
if UNSHARP > 0.0:
    try:
        from scipy.ndimage import gaussian_filter as _gf
        _blurred = _gf(img, sigma=3.0)
        img = np.clip(img + UNSHARP * (img - _blurred), 0.0, 1.0)
        print(f"[{LABEL}] Unsharp mask: sigma=3.0, amount={UNSHARP} (pre-gamma)")
    except ImportError:
        pass

# Gamma
img = np.power(img, GAMMA)

# Post-process blur (0.0 = disabled; default is now 0.0)
if POST_SIGMA > 0.0:
    try:
        from scipy.ndimage import gaussian_filter
        img = gaussian_filter(img, sigma=POST_SIGMA)
        print(f"[{LABEL}] Post-blur: sigma={POST_SIGMA}")
    except ImportError:
        pass

fig, ax = plt.subplots(figsize=(8, 8), facecolor='black')
ax.imshow(img, cmap=CMAP, origin='upper', interpolation=INTERP)
ax.set_facecolor('black')
for spine in ax.spines.values(): spine.set_edgecolor('#444')
ax.set_title(LABEL, color='#ddd', fontsize=11)
ax.axis('off')
plt.tight_layout(pad=0.3)
plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight', facecolor='black')
plt.close()
print(f"[{LABEL}] Done -> {OUTPUT_PATH}")
