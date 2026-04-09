#!/usr/bin/env python3
"""
Mitsuba 3 caustic render for the CausticsEngineering lens OBJ.

Integrator: ptracer (particle tracer — shoots rays from light, ideal for caustics)
Material:   dielectric IOR=1.49 (cast acrylic)
Setup:      point light → glass lens → receiver plane (0.75m focal distance)
Output:     examples/caustic_mitsuba.png
"""

import mitsuba as mi
import drjit as dr
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import time

mi.set_variant('scalar_rgb')  # CPU, reliable, no OpenCL

# ── Scene geometry (from OBJ analysis) ────────────────────────────────────────
OBJ_PATH   = "/Users/admin/causticsEngineering/examples/original_image.obj"

IOR        = 1.49
FOCAL_DIST = 0.75   # metres — must match solver focalLength

cx, cy   = 0.100190, 0.100195
z_min    = -0.019531   # lens bottom
z_max    =  0.005293   # lens top
span     =  0.200011   # lens XY span

light_z  = z_max + FOCAL_DIST          # 0.755293 m
plane_z  = z_min - FOCAL_DIST          # -0.769531 m
pad      = span * 1.5                  # receiver plane half-width

# ── Render settings ────────────────────────────────────────────────────────────
WIDTH      = 512
HEIGHT     = 512
SPP        = 1024  # samples per pixel — ptracer converges fast for caustics
MAX_DEPTH  = 16    # enough for 2 refractions + multiple bounces

OUTPUT_PNG = "/Users/admin/causticsEngineering/examples/caustic_mitsuba_1024spp.png"

# ── Sunlight colormap (matching our Python ray tracer) ─────────────────────────
CMAP = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

print(f"Mitsuba {mi.__version__}  |  variant: scalar_rgb")
print(f"Lens:  Z {z_min:.4f}→{z_max:.4f}m  span {span:.4f}m  centre ({cx:.4f},{cy:.4f})")
print(f"Light: z={light_z:.4f}m  |  Plane: z={plane_z:.4f}m")
print(f"Render: {WIDTH}×{HEIGHT}  {SPP} spp  ptracer  max_depth={MAX_DEPTH}")

# ── Scene definition ───────────────────────────────────────────────────────────
scene_dict = {
    'type': 'scene',

    # ── Integrator: particle tracer (forward light tracing) ────────────────────
    # ptracer shoots particles FROM the light — naturally captures caustics.
    # Requires a perspective sensor (not orthographic). We approximate orthographic
    # by placing the camera 50m above the plane with a very narrow FOV.
    'integrator': {
        'type': 'ptracer',
        'max_depth': MAX_DEPTH,
        'hide_emitters': False,
    },

    # ── Camera: between lens and receiver, looking straight down ───────────────
    # CRITICAL: camera must be BELOW the lens (z < z_min) so the ptracer's
    # receiver→camera visibility ray doesn't pass through the glass.
    # If camera is above the lens, the glass blocks/refracts the shadow ray and
    # receiver contributions are lost → black square artifact.
    # Camera at 5cm below lens bottom: z = z_min - 0.05 = -0.0695m
    # Distance to receiver: 0.700m → FOV ≈ 46° covers pad×pad area.
    'sensor': {
        'type': 'perspective',
        'to_world': mi.ScalarTransform4f.look_at(
            origin=[cx, cy, z_min - 0.05],
            target=[cx, cy, plane_z],
            up=[0, 1, 0],
        ),
        'fov': float(2 * np.degrees(np.arctan(pad / abs(plane_z - (z_min - 0.05))))),
        'fov_axis': 'x',
        'film': {
            'type': 'hdrfilm',
            'width':  WIDTH,
            'height': HEIGHT,
        },
        'sampler': {
            'type': 'independent',
            'sample_count': SPP,
        },
    },

    # ── Point light source above the lens ──────────────────────────────────────
    'emitter': {
        'type': 'point',
        'position': [cx, cy, light_z],
        'intensity': {
            'type': 'spectrum',
            'value': 100000.0,   # high power — we're looking at a small caustic spot
        },
    },

    # ── Glass lens (our OBJ) ───────────────────────────────────────────────────
    'lens': {
        'type': 'obj',
        'filename': OBJ_PATH,
        'bsdf': {
            'type': 'dielectric',
            'int_ior': IOR,
            'ext_ior': 'air',
        },
        # The OBJ is already in metres, no transform needed
    },

    # ── Receiver plane (white diffuse) ─────────────────────────────────────────
    # Mitsuba's rectangle primitive is a 2×2 unit square; scale and position it.
    'receiver': {
        'type': 'rectangle',
        'to_world': mi.ScalarTransform4f.translate([cx, cy, plane_z])
                  @ mi.ScalarTransform4f.scale([pad, pad, 1.0]),
        'bsdf': {
            'type': 'diffuse',
            'reflectance': {'type': 'rgb', 'value': [0.9, 0.9, 0.9]},
        },
    },
}

# ── Load and render ────────────────────────────────────────────────────────────
print("\nLoading scene (BVH build may take 30-60s for 2.1M faces)...", flush=True)
t0 = time.time()
scene = mi.load_dict(scene_dict)
t_load = time.time() - t0
print(f"Scene loaded in {t_load:.1f}s", flush=True)

print(f"Rendering {SPP} spp...", flush=True)
t1 = time.time()
img = mi.render(scene, spp=SPP)
t_render = time.time() - t1
print(f"Render complete in {t_render:.1f}s  (total: {time.time()-t0:.1f}s)", flush=True)

# ── Convert to numpy and apply sunlight colormap ───────────────────────────────
img_np = np.array(img)                  # shape (H, W, 3), float32, linear
print(f"Image array shape: {img_np.shape}  min={img_np.min():.4f}  max={img_np.max():.4f}")

# Take luminance channel (average of RGB — ptracer output is mostly monochrome for this)
lum = img_np.mean(axis=2)
if lum.max() > 0:
    lum /= lum.max()
lum = np.sqrt(lum)   # gamma ≈ 2 (matches Python ray tracer)

# Save with sunlight colormap
fig, ax = plt.subplots(figsize=(10, 10), facecolor='black')
extent = [cx - pad, cx + pad, cy - pad, cy + pad]
ax.imshow(lum, cmap=CMAP, origin='lower', extent=extent, interpolation='bilinear')
ax.set_facecolor('black')
ax.tick_params(colors='#aaa')
ax.xaxis.label.set_color('#aaa'); ax.yaxis.label.set_color('#aaa')
for sp in ax.spines.values(): sp.set_edgecolor('#444')
ax.set_xlabel("X (m)"); ax.set_ylabel("Y (m)")
ax.set_title(f"Mitsuba 3 ptracer caustic  |  IOR {IOR}  |  focal {FOCAL_DIST}m  |  {SPP} spp",
             color='#ddd', fontsize=12)
plt.tight_layout()
plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches='tight', facecolor='black')
plt.close()
print(f"\nDone → {OUTPUT_PNG}")
print(f"Load: {t_load:.1f}s  |  Render: {t_render:.1f}s  |  Total: {time.time()-t0:.1f}s")
