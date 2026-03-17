#!/usr/bin/env python3
"""
render_any_obj.py — Mitsuba 3 caustic render for any lens OBJ.

Dynamically reads OBJ geometry (cx, cy, z_min, z_max, span) from the file.
Identical scene setup to render_mitsuba.py (IOR=1.49, FOCAL_DIST=0.75,
ptracer, sunlight colormap, camera below lens).

Usage:
  python3 render_any_obj.py \
    --obj PATH --out PATH [--spp INT] [--res INT]
"""

import argparse
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

import mitsuba as mi
import drjit as dr

mi.set_variant('scalar_rgb')

# Physical constants — MUST match solver
IOR        = 1.49
FOCAL_DIST = 0.75   # metres

# Sunlight colormap (identical to render_mitsuba.py and simulate_*.py)
CMAP = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])


def parse_obj_geometry(obj_path: str):
    """Parse OBJ vertices and return (cx, cy, z_min, z_max, span)."""
    raw   = Path(obj_path).read_bytes()
    lines = raw.split(b'\n')
    v_buf = b'\n'.join(l[2:] for l in lines if l.startswith(b'v '))
    if not v_buf.strip():
        raise ValueError(f"No vertices found in {obj_path}")
    verts = np.fromstring(v_buf.decode(), dtype=np.float64, sep=' ').reshape(-1, 3)

    x_min, x_max = verts[:, 0].min(), verts[:, 0].max()
    y_min, y_max = verts[:, 1].min(), verts[:, 1].max()
    z_min, z_max = verts[:, 2].min(), verts[:, 2].max()

    cx   = float((x_min + x_max) / 2)
    cy   = float((y_min + y_max) / 2)
    span = float(max(x_max - x_min, y_max - y_min))

    return cx, cy, float(z_min), float(z_max), span


def render(obj_path: str, out_path: str, spp: int = 1024, res: int = 512):
    t0 = time.time()

    print(f"Parsing OBJ geometry: {obj_path}")
    cx, cy, z_min, z_max, span = parse_obj_geometry(obj_path)

    light_z = z_max + FOCAL_DIST
    plane_z = z_min - FOCAL_DIST
    pad     = span * 1.5

    print(f"  Lens:  Z {z_min:.4f}→{z_max:.4f}m  span {span:.4f}m  centre ({cx:.4f},{cy:.4f})")
    print(f"  Light: z={light_z:.4f}m  |  Plane: z={plane_z:.4f}m  |  Pad: {pad:.4f}m")
    print(f"Mitsuba {mi.__version__}  |  variant: scalar_rgb")
    print(f"Render: {res}×{res}  {spp} spp  ptracer  IOR={IOR}  focal={FOCAL_DIST}m")

    # Camera: 5cm below lens bottom, looking straight down at receiver plane
    # (must be below lens so glass doesn't block the shadow ray)
    cam_z    = z_min - 0.05
    cam_fov  = float(2 * np.degrees(np.arctan(pad / abs(plane_z - cam_z))))

    scene_dict = {
        'type': 'scene',

        'integrator': {
            'type': 'ptracer',
            'max_depth': 16,
            'hide_emitters': False,
        },

        'sensor': {
            'type': 'perspective',
            'to_world': mi.ScalarTransform4f.look_at(
                origin=[cx, cy, cam_z],
                target=[cx, cy, plane_z],
                up=[0, 1, 0],
            ),
            'fov':      cam_fov,
            'fov_axis': 'x',
            'film': {
                'type':   'hdrfilm',
                'width':  res,
                'height': res,
            },
            'sampler': {
                'type':         'independent',
                'sample_count': spp,
            },
        },

        'emitter': {
            'type': 'point',
            'position': [cx, cy, light_z],
            'intensity': {
                'type':  'spectrum',
                'value': 100000.0,
            },
        },

        'lens': {
            'type':     'obj',
            'filename': str(Path(obj_path).resolve()),
            'bsdf': {
                'type':    'dielectric',
                'int_ior': IOR,
                'ext_ior': 'air',
            },
        },

        'receiver': {
            'type': 'rectangle',
            'to_world': mi.ScalarTransform4f.translate([cx, cy, plane_z])
                      @ mi.ScalarTransform4f.scale([pad, pad, 1.0]),
            'bsdf': {
                'type':        'diffuse',
                'reflectance': {'type': 'rgb', 'value': [0.9, 0.9, 0.9]},
            },
        },
    }

    print(f"\nLoading scene (BVH build may take 30-60s for large meshes)...", flush=True)
    t_load0 = time.time()
    scene   = mi.load_dict(scene_dict)
    t_load  = time.time() - t_load0
    print(f"Scene loaded in {t_load:.1f}s", flush=True)

    print(f"Rendering {spp} spp...", flush=True)
    t_render0 = time.time()
    img       = mi.render(scene, spp=spp)
    t_render  = time.time() - t_render0
    print(f"Render complete in {t_render:.1f}s  (total: {time.time()-t0:.1f}s)", flush=True)

    img_np = np.array(img)
    print(f"Image: shape={img_np.shape}  min={img_np.min():.4f}  max={img_np.max():.4f}")

    lum = img_np.mean(axis=2)
    if lum.max() > 0:
        lum /= lum.max()
    lum = np.sqrt(lum)   # gamma ~2, matches Python ray tracer

    extent = [cx - pad, cx + pad, cy - pad, cy + pad]
    fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')
    ax.imshow(lum, cmap=CMAP, origin='lower', extent=extent, interpolation='bilinear')
    ax.set_facecolor('black')
    ax.tick_params(colors='#aaa')
    ax.xaxis.label.set_color('#aaa')
    ax.yaxis.label.set_color('#aaa')
    for sp in ax.spines.values():
        sp.set_edgecolor('#444')
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(
        f"Mitsuba 3 ptracer  |  IOR {IOR}  |  focal {FOCAL_DIST}m  |  {spp} spp\n{Path(obj_path).name}",
        color='#ddd', fontsize=11
    )
    plt.tight_layout()

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='black')
    plt.close()

    total = time.time() - t0
    print(f"\nDone → {out_path}")
    print(f"Load: {t_load:.1f}s  |  Render: {t_render:.1f}s  |  Total: {total:.1f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--obj', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--spp', type=int, default=1024)
    parser.add_argument('--res', type=int, default=512)
    args = parser.parse_args()
    render(args.obj, args.out, spp=args.spp, res=args.res)


if __name__ == '__main__':
    main()
