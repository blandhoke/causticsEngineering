#!/usr/bin/env python3
"""
simulate_cow2_fresh.py — Generic forward ray tracer for CausticsEngineering solver output.
Cow 2 production script (Option B or C input). Zero legacy parameters.

Usage:
  python3 simulate_cow2_fresh.py

Configure PREFIX and OBJ_PATH at the top to select the run target.
Sigma and radius are computed automatically from face count — no manual tuning needed.

  512px mesh  (~525k top faces)  -> sigma≈1.5, radius≈3
  256px mesh  (~131k top faces)  -> sigma≈3.0, radius≈5
  128px mesh  (~33k top faces)   -> sigma≈6.0, radius≈9
  1024px mesh (~2.1M top faces)  -> sigma≈0.75, radius≈2
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
PREFIX    = "cow2"          # output and cache file prefix — change per run
OBJ_PATH  = Path("/Users/admin/causticsEngineering/examples/original_image_normal.obj")
OUT_DIR   = Path("/Users/admin/causticsEngineering/examples")

IOR        = 1.49           # cast acrylic / PMMA — do not change
FOCAL_DIST = 0.75           # MUST match focalLength in src/create_mesh.jl (currently 0.75)
IMAGE_RES  = 512            # output PNG resolution (square)
BATCH_SIZE = 100_000
N_PASSES   = 4              # minimum for clean output; do not reduce

# ── Derived paths ─────────────────────────────────────────────────────────────
OUTPUT_PATH = OUT_DIR / f"caustic_{PREFIX}.png"
ACCUM_PATH  = OUT_DIR / f"{PREFIX}_accum.npy"
META_PATH   = OUT_DIR / f"{PREFIX}_meta.npy"

# ── Warm sunlight colormap ─────────────────────────────────────────────────────
CMAP = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

# ── Snell's law ────────────────────────────────────────────────────────────────
def refract_batch(d, n_hat, n_ratio):
    cos_i  = np.einsum('ij,ij->i', -d, n_hat).clip(0.0, 1.0)
    sin2_t = n_ratio**2 * (1.0 - cos_i**2)
    valid  = sin2_t <= 1.0
    cos_t  = np.sqrt(np.maximum(0.0, 1.0 - sin2_t))
    d_out  = n_ratio * d + (n_ratio * cos_i - cos_t)[:, None] * n_hat
    mag    = np.linalg.norm(d_out, axis=1, keepdims=True)
    d_out /= np.where(mag > 0, mag, 1.0)
    return d_out, valid

# ── Simulation or cache load ───────────────────────────────────────────────────
if ACCUM_PATH.exists() and META_PATH.exists():
    print(f"Loading cache: {ACCUM_PATH.name}")
    accum = np.load(ACCUM_PATH)
    meta  = np.load(META_PATH)
    xmin, xmax, ymin, ymax = meta

else:
    print(f"Parsing OBJ: {OBJ_PATH.name} ...")
    raw   = OBJ_PATH.read_bytes()
    lines = raw.split(b'\n')
    v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
    f_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'f '))
    verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
    faces = np.fromstring(f_buf.decode(), dtype=np.int32,   sep=' ').reshape(-1, 3) - 1
    print(f"  {len(verts):,} vertices  |  {len(faces):,} faces")

    # Auto-compute splat sigma from top-surface face count
    # Reference: 512px mesh (~525k top faces) -> sigma=1.5 (empirically confirmed)
    # Formula: sigma = 1.5 / sqrt(top_face_count / 525_000)
    v0r = verts[faces[:, 0]]; v1r = verts[faces[:, 1]]; v2r = verts[faces[:, 2]]
    raw_n_all = np.cross(v1r - v0r, v2r - v0r)
    top_idx   = np.where(raw_n_all[:, 2] > 0)[0]
    n_top     = len(top_idx)
    splat_sigma  = 1.5 / np.sqrt(max(n_top, 525_000) / 525_000)
    splat_radius = max(1, round(splat_sigma * 2))
    print(f"  [{PREFIX}] top faces={n_top:,}  sigma={splat_sigma:.3f}  radius={splat_radius}")

    z_min, z_max = verts[:, 2].min(), verts[:, 2].max()
    cx = (verts[:, 0].min() + verts[:, 0].max()) / 2
    cy = (verts[:, 1].min() + verts[:, 1].max()) / 2
    lens_span    = max(verts[:,0].max()-verts[:,0].min(), verts[:,1].max()-verts[:,1].min())
    light_pos    = np.array([cx, cy, z_max + FOCAL_DIST])
    plane_z      = z_min - FOCAL_DIST
    print(f"  Lens Z: {z_min*1000:.2f} mm → {z_max*1000:.2f} mm  |  dome {(z_max-z_min)*1000:.2f} mm")
    print(f"  Light: z={light_pos[2]:.4f}  |  Plane z: {plane_z:.5f}")

    pad  = lens_span * 1.5
    xmin, xmax = cx - pad, cx + pad
    ymin, ymax = cy - pad, cy + pad
    accum = np.zeros((IMAGE_RES, IMAGE_RES), dtype=np.float64)

    # Precompute Gaussian splat kernel
    ks     = range(-splat_radius, splat_radius + 1)
    kernel = {(dy, dx): np.exp(-(dx**2 + dy**2) / (2 * splat_sigma**2))
              for dy in ks for dx in ks}

    print(f"Tracing rays  ({N_PASSES} passes, sigma={splat_sigma:.3f}, radius={splat_radius}) ...")
    n_hit_total = 0
    total       = n_top
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
            fold = ra + rb > 1
            ra[fold] = 1 - ra[fold]
            rb[fold] = 1 - rb[fold]
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

            n_bot          = np.zeros_like(exit_p); n_bot[:, 2] = 1.0
            d_exit, valid2 = refract_batch(d_glass, n_bot, n_ratio=IOR / 1.0)
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

        print(f"  {min(start+BATCH_SIZE, total):>7,} / {total:,}  "
              f"({100*min(start+BATCH_SIZE, total)/total:.0f}%)", end='\r')

    accum /= N_PASSES
    hit_rate = 100 * n_hit_total / (total * N_PASSES) if total > 0 else 0
    print(f"\n  Hits: {n_hit_total:,}  ({hit_rate:.1f}% across {N_PASSES} passes)")

    np.save(ACCUM_PATH, accum)
    np.save(META_PATH,  np.array([xmin, xmax, ymin, ymax]))
    print(f"Saved cache -> {ACCUM_PATH.name}")

# ── Render ─────────────────────────────────────────────────────────────────────
print("Rendering ...")
img = np.flipud(np.fliplr(accum.copy()))
if img.max() > 0:
    img /= img.max()
img = np.sqrt(img)

try:
    from scipy.ndimage import gaussian_filter
    img = gaussian_filter(img, sigma=0.5)
except ImportError:
    pass

fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')
ax.imshow(img, cmap=CMAP, origin='upper',
          extent=[xmin, xmax, ymin, ymax],
          interpolation='bilinear')
ax.set_facecolor('black')
ax.tick_params(colors='#aaa')
ax.xaxis.label.set_color('#aaa')
ax.yaxis.label.set_color('#aaa')
for spine in ax.spines.values():
    spine.set_edgecolor('#444')
ax.set_xlabel("X (m)")
ax.set_ylabel("Y (m)")
ax.set_title(f"Predicted caustic ({PREFIX})  —  IOR {IOR}  |  f={FOCAL_DIST}m  |  {N_PASSES}-pass",
             color='#ddd', fontsize=12)
plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight', facecolor='black')
plt.close()
print(f"Done -> {OUTPUT_PATH}")
