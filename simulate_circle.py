#!/usr/bin/env python3
"""
simulate_circle.py — Forward ray trace for the circle_target test.

First run: traces rays through examples/original_image.obj, saves to circle_accum.npy.
Subsequent runs: loads cached accumulator instantly.
Output: examples/caustic_circle.png  (never overwrites caustic_simulated.png)
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE        = Path("/Users/admin/causticsEngineering/examples")
OBJ_PATH    = BASE / "original_image.obj"
OUTPUT_PATH = BASE / "caustic_circle.png"
ACCUM_PATH  = BASE / "circle_accum.npy"
META_PATH   = BASE / "circle_meta.npy"

assert OUTPUT_PATH.name != "caustic_simulated.png", "Refusing to overwrite reference render"

IOR        = 1.49
FOCAL_DIST = 0.2
IMAGE_RES  = 1024
BATCH_SIZE = 100_000

# ── Warm sunlight colormap ─────────────────────────────────────────────────────
CMAP = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

# ── Vectorised Snell's law ─────────────────────────────────────────────────────
def refract_batch(d, n_hat, n_ratio):
    cos_i  = np.einsum('ij,ij->i', -d, n_hat).clip(0.0, 1.0)
    sin2_t = n_ratio**2 * (1.0 - cos_i**2)
    valid  = sin2_t <= 1.0
    cos_t  = np.sqrt(np.maximum(0.0, 1.0 - sin2_t))
    d_out  = n_ratio * d + (n_ratio * cos_i - cos_t)[:, None] * n_hat
    mag    = np.linalg.norm(d_out, axis=1, keepdims=True)
    d_out /= np.where(mag > 0, mag, 1.0)
    return d_out, valid

# ── Load cache or run simulation ───────────────────────────────────────────────
if ACCUM_PATH.exists() and META_PATH.exists():
    print(f"Loading cached data from {ACCUM_PATH.name} ...")
    accum = np.load(ACCUM_PATH)
    meta  = np.load(META_PATH)
    xmin, xmax, ymin, ymax = meta

else:
    print("Parsing OBJ...")
    raw   = OBJ_PATH.read_bytes()
    lines = raw.split(b'\n')
    v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
    f_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'f '))
    verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)
    faces = np.fromstring(f_buf.decode(), dtype=np.int32,   sep=' ').reshape(-1, 3) - 1
    print(f"  {len(verts):,} vertices  |  {len(faces):,} faces")

    z_min, z_max  = verts[:, 2].min(), verts[:, 2].max()
    cx = (verts[:, 0].min() + verts[:, 0].max()) / 2
    cy = (verts[:, 1].min() + verts[:, 1].max()) / 2
    lens_span     = max(verts[:,0].max()-verts[:,0].min(), verts[:,1].max()-verts[:,1].min())
    lens_top_z    = z_max
    lens_bottom_z = z_min
    print(f"  Lens Z: {lens_bottom_z:.5f} → {lens_top_z:.5f}  "
          f"|  span {lens_span:.4f} m  |  dome height {z_max - z_min:.5f} m")

    light_pos = np.array([cx, cy, lens_top_z + FOCAL_DIST])
    plane_z   = lens_bottom_z - FOCAL_DIST
    print(f"  Light: {light_pos}  |  Plane z: {plane_z:.5f}")

    v0 = verts[faces[:, 0]]; v1 = verts[faces[:, 1]]; v2 = verts[faces[:, 2]]
    raw_normals = np.cross(v1 - v0, v2 - v0)
    top_idx     = np.where(raw_normals[:, 2] > 0)[0]
    print(f"  Top-surface faces: {len(top_idx):,}")

    pad  = lens_span * 1.5
    xmin, xmax = cx - pad, cx + pad
    ymin, ymax = cy - pad, cy + pad
    accum = np.zeros((IMAGE_RES, IMAGE_RES), dtype=np.float64)

    print("\nTracing rays...")
    n_hit_total = 0
    total = len(top_idx)

    for start in range(0, total, BATCH_SIZE):
        batch = top_idx[start : start + BATCH_SIZE]
        b0 = verts[faces[batch, 0]]
        b1 = verts[faces[batch, 1]]
        b2 = verts[faces[batch, 2]]

        cents = (b0 + b1 + b2) / 3.0
        raw_n = np.cross(b1 - b0, b2 - b0)
        mag_n = np.linalg.norm(raw_n, axis=1, keepdims=True)
        ns    = raw_n / np.where(mag_n > 0, mag_n, 1.0)
        areas = mag_n[:, 0] * 0.5

        d_in  = cents - light_pos[None, :]
        r2    = np.sum(d_in**2, axis=1)
        d_in /= np.linalg.norm(d_in, axis=1, keepdims=True)

        d_glass, valid = refract_batch(d_in, ns, n_ratio=1.0 / IOR)

        dz_g   = d_glass[:, 2]
        t_bot  = np.where(dz_g < -1e-12, (lens_bottom_z - cents[:, 2]) / dz_g, -1.0)
        valid &= t_bot > 0
        exit_p = cents + t_bot[:, None] * d_glass

        n_bot          = np.zeros_like(exit_p); n_bot[:, 2] = 1.0
        d_exit, valid2 = refract_batch(d_glass, n_bot, n_ratio=IOR / 1.0)
        valid &= valid2

        dz_e   = d_exit[:, 2]
        t_pln  = np.where(np.abs(dz_e) > 1e-12, (plane_z - exit_p[:, 2]) / dz_e, -1.0)
        valid &= t_pln > 0
        hits   = exit_p + t_pln[:, None] * d_exit

        hx = hits[valid, 0];  hy = hits[valid, 1]
        w  = areas[valid] / np.where(r2[valid] > 0, r2[valid], 1.0)
        px = ((hx - xmin) / (xmax - xmin) * IMAGE_RES).astype(np.int32)
        py = ((hy - ymin) / (ymax - ymin) * IMAGE_RES).astype(np.int32)
        ok = (px >= 0) & (px < IMAGE_RES) & (py >= 0) & (py < IMAGE_RES)
        np.add.at(accum, (py[ok], px[ok]), w[ok])
        n_hit_total += int(ok.sum())

        print(f"  {min(start+BATCH_SIZE, total):>7,} / {total:,}  "
              f"({100*(start+BATCH_SIZE)/total:.0f}%)", end='\r')

    hit_rate = 100 * n_hit_total / total if total > 0 else 0
    print(f"\n  Hits on plane: {n_hit_total:,}  ({hit_rate:.1f}% hit rate)")

    np.save(ACCUM_PATH, accum)
    np.save(META_PATH,  np.array([xmin, xmax, ymin, ymax]))
    print(f"Saved cache → {ACCUM_PATH.name}")

# ── Plot ───────────────────────────────────────────────────────────────────────
print("Rendering image...")
img = np.fliplr(accum.copy())
if img.max() > 0:
    img /= img.max()
img = np.sqrt(img)   # gamma ≈ 2

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
ax.set_title("Predicted caustic (circle)  —  IOR 1.49  |  focal 0.2 m",
             color='#ddd', fontsize=12)
plt.tight_layout()
plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight', facecolor='black')
plt.close()
print(f"Done → {OUTPUT_PATH}")
