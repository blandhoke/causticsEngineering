#!/usr/bin/env python3
"""
optimize_caustic.py — Mitsuba 3 differentiable caustic lens optimizer.

Optimizes lens vertex Z-positions so that the rendered caustic matches a
target image. Replacement / refinement path for the Julia SOR solver.

Variant:     llvm_ad_rgb  (16-thread CPU + drjit autodiff)
Integrator:  prb          (Path Replay Backpropagation — supports backward())
Optimizer:   Adam         (mi.ad.Adam, per-vertex learning rate)

Usage:
  python3 optimize_caustic.py                         # inkbrush target, defaults
  python3 optimize_caustic.py --target path/to/target.png
  python3 optimize_caustic.py --iter 200 --lr 2e-6 --spp 128 --res 256
  python3 optimize_caustic.py --obj examples/original_image_fast.obj

Outputs (all under examples/diffrender/):
  iter_NNNN.png        — render at each save checkpoint
  loss.png             — loss curve
  optimized_lens.obj   — final vertex-optimized lens mesh

Notes:
  - prb is a camera-side path tracer; caustic convergence requires ~128 spp
    per iteration. Use --spp 64 for speed, --spp 256 for stable gradients.
  - Vertex updates are constrained to Z only (surface height). XY stays fixed
    so the lens footprint and boundary do not move.
  - Start from the existing Julia-solver OBJ for fast convergence. Starting
    from a flat dome is possible but requires ~500+ iterations.
  - BVH rebuild cost: ~0.5s at 131k faces (fast OBJ), ~2s at 525k (normal OBJ).
    Use --obj examples/original_image_fast.obj for fastest iteration.
"""

import os
os.environ.setdefault(
    'DRJIT_LIBLLVM_PATH',
    '/usr/local/Cellar/llvm@16/16.0.6_1/lib/libLLVM-16.dylib',
)

import mitsuba as mi
import drjit as dr
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image as PILImage
import argparse, time

mi.set_variant('llvm_ad_rgb')

# ── CLI ────────────────────────────────────────────────────────────────────────
PROJECT = Path(__file__).parent

parser = argparse.ArgumentParser(description='Differentiable caustic lens optimizer')
parser.add_argument('--obj',        default='examples/original_image.obj',
                    help='Starting lens OBJ (default: original_image.obj)')
parser.add_argument('--target',     default='luxcore_test/inkbrush_caustic_normal.png',
                    help='Target caustic PNG (default: inkbrush reference)')
parser.add_argument('--iter',       type=int,   default=100,
                    help='Optimization iterations (default: 100)')
parser.add_argument('--lr',         type=float, default=1e-6,
                    help='Adam learning rate for vertex Z (default: 1e-6)')
parser.add_argument('--spp',        type=int,   default=64,
                    help='Samples per pixel per iteration (default: 64)')
parser.add_argument('--res',        type=int,   default=128,
                    help='Render resolution per side (default: 128)')
parser.add_argument('--save-every', type=int,   default=10, dest='save_every',
                    help='Save render + OBJ every N iterations (default: 10)')
parser.add_argument('--out-dir',    default='examples/diffrender', dest='out_dir',
                    help='Output directory (default: examples/diffrender)')
args = parser.parse_args()

OBJ_PATH   = PROJECT / args.obj
TARGET_PNG = PROJECT / args.target
OUT_DIR    = PROJECT / args.out_dir
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Scene parameters — must stay in sync with render_mitsuba.py ───────────────
IOR        = 1.49
FOCAL_DIST = 0.75
cx, cy     = 0.100190, 0.100195
z_min      = -0.019531
z_max      =  0.005293
span       =  0.200011
light_z    = z_max + FOCAL_DIST
plane_z    = z_min - FOCAL_DIST
pad        = span * 1.5
RES        = args.res

print(f"Mitsuba {mi.__version__}  |  variant: llvm_ad_rgb")
print(f"OBJ:    {OBJ_PATH}")
print(f"Target: {TARGET_PNG}")
print(f"Iter={args.iter}  LR={args.lr}  SPP={args.spp}  Res={RES}x{RES}")
print(f"Output: {OUT_DIR}")

# ── Load and preprocess target image ──────────────────────────────────────────
# Target is the desired caustic pattern. Resize to match render resolution.
# The target PNG is gamma-encoded [0,1]; we use it as-is for a perceptual loss.
target_pil = (
    PILImage.open(TARGET_PNG)
    .convert('RGB')
    .resize((RES, RES), PILImage.LANCZOS)
)
target_np = np.array(target_pil).astype(np.float32) / 255.0  # (H,W,3) [0,1]
target_mi = mi.TensorXf(target_np)
print(f"\nTarget range: {target_np.min():.3f}–{target_np.max():.3f}  "
      f"mean={target_np.mean():.3f}")

# ── Scene definition ───────────────────────────────────────────────────────────
# prb (Path Replay Backpropagation) is used instead of ptracer because it
# supports dr.backward() for parameter gradients. It is a camera-side path
# tracer, so it finds caustic paths via specular refraction through the lens.
scene_dict = {
    'type': 'scene',

    'integrator': {
        'type': 'ptracer',   # particle tracer: shoots from light → lens → receiver
        'max_depth': 16,     # caustic paths are sampled directly (forward direction)
        'hide_emitters': False,
    },

    # Camera below the lens, looking down at receiver — same geometry as
    # render_mitsuba.py. No glass between camera and receiver on this side.
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
            'width':  RES,
            'height': RES,
        },
        'sampler': {
            'type': 'independent',
            'sample_count': args.spp,
        },
    },

    'emitter': {
        'type': 'point',
        'position': [cx, cy, light_z],
        'intensity': {'type': 'spectrum', 'value': 100000.0},
    },

    'lens': {
        'type': 'obj',
        'filename': str(OBJ_PATH),
        'bsdf': {
            'type': 'dielectric',
            'int_ior': IOR,
            'ext_ior': 'air',
        },
    },

    'receiver': {
        'type': 'rectangle',
        'to_world': (
            mi.ScalarTransform4f.translate([cx, cy, plane_z])
            @ mi.ScalarTransform4f.scale([pad, pad, 1.0])
        ),
        'bsdf': {
            'type': 'diffuse',
            'reflectance': {'type': 'rgb', 'value': [0.9, 0.9, 0.9]},
        },
    },
}

# ── Load scene ─────────────────────────────────────────────────────────────────
print('\nLoading scene...')
t0 = time.time()
scene  = mi.load_dict(scene_dict)
params = mi.traverse(scene)
print(f'Scene loaded in {time.time()-t0:.1f}s')

# ── Inspect available parameters ───────────────────────────────────────────────
print('\nDifferentiable parameters:')
for k in params.keys():
    v = params[k]
    shape_info = getattr(v, 'shape', '?')
    print(f'  {k}: {type(v).__name__}  {shape_info}')

VP_KEY = 'lens.vertex_positions'
if VP_KEY not in params:
    # Mitsuba sometimes uses a different key format — search for it
    matches = [k for k in params.keys() if 'vertex' in k.lower()]
    if matches:
        VP_KEY = matches[0]
        print(f'\nUsing vertex key: {VP_KEY}')
    else:
        raise RuntimeError(
            f"Could not find vertex_positions in params. "
            f"Keys: {list(params.keys())}"
        )

# ── Set up optimizer — Z-only vertex updates ───────────────────────────────────
# Strategy: keep a frozen copy of initial XY positions; optimizer only changes Z.
# After each Adam step we restore XY from the frozen copy to prevent the lens
# from drifting laterally (which would break the physical geometry).

vp_init = dr.detach(params[VP_KEY])           # frozen reference  (Float, len=N*3)
vp_np   = np.array(vp_init).reshape(-1, 3)   # (N, 3) for OBJ export
n_verts = vp_np.shape[0]

# Identify top-surface vertices: those with Z above the median
# (flat bottom has Z ≈ z_min; top surface has variable Z up to z_max)
z_median = np.median(vp_np[:, 2])
top_mask_np = (vp_np[:, 2] > z_median).astype(np.float32)  # (N,) binary
top_mask_flat = np.repeat(top_mask_np, 3).reshape(-1)        # (N*3,) — blocks XY+Z for non-top
# Only allow Z updates: mask out X and Y indices (indices 0,1 of each triplet)
xyz_z_mask = np.zeros(n_verts * 3, dtype=np.float32)
xyz_z_mask[2::3] = top_mask_np  # Z index (every 3rd element, offset 2)
z_update_mask = mi.Float(xyz_z_mask)

print(f'\nVertices: {n_verts:,}  top-surface: {int(top_mask_np.sum()):,}')

opt = mi.ad.Adam(lr=args.lr)
opt[VP_KEY] = params[VP_KEY]

# ── Helper: normalize HDR render to [0,1] for loss ────────────────────────────
# norm_scale is set from the initial (pre-optimization) render so that the
# normalization is a constant — not a function of the current render.
# A dynamic peak breaks gradient flow (drjit can't backprop through dr.max).
_norm_scale = 1.0  # set after initial render below

def normalize_render(img_tensor):
    """Tone-map HDR render to [0,1] using sqrt (matches render_mitsuba.py)."""
    img = dr.maximum(img_tensor, 0.0) / _norm_scale
    return dr.sqrt(img)

# ── Save helper ────────────────────────────────────────────────────────────────
def save_render(img_np_norm, step, loss_val):
    """Save a normalized (H,W,3) float32 render as PNG."""
    rgb = (np.clip(img_np_norm, 0, 1) * 255).astype(np.uint8)
    path = OUT_DIR / f'iter_{step:04d}.png'
    PILImage.fromarray(rgb).save(path)
    print(f'  saved {path.name}  loss={loss_val:.6f}')

def save_obj(vp_current_np, step):
    """Write optimized vertex positions into a copy of the original OBJ."""
    out_path = OUT_DIR / f'lens_iter_{step:04d}.obj'
    with open(OBJ_PATH) as f:
        lines = f.readlines()
    v_idx = 0
    with open(out_path, 'w') as f:
        for line in lines:
            if line.startswith('v ') and v_idx < len(vp_current_np):
                x, y, z = vp_current_np[v_idx]
                f.write(f'v {x:.8f} {y:.8f} {z:.8f}\n')
                v_idx += 1
            else:
                f.write(line)
    print(f'  saved {out_path.name}  ({v_idx} vertices written)')
    return out_path

# ── Initial render (before optimization) ──────────────────────────────────────
print('\nInitial render (before optimization)...')
with dr.suspend_grad():
    img0 = mi.render(scene, spp=args.spp * 2, seed=9999)
img0_np = np.array(img0)
_norm_scale = float(img0_np.max()) or 1.0   # fix normalization constant
print(f'Normalization scale: {_norm_scale:.1f}')
img0_norm = np.array(normalize_render(img0))
save_render(img0_norm, 0, float('nan'))

# ── Optimization loop ─────────────────────────────────────────────────────────
losses = []
t_loop = time.time()

print(f'\nStarting {args.iter} iterations...')
print(f'{"Iter":>5}  {"Loss":>10}  {"GradMax":>10}  {"dZ_max":>10}  {"Time":>5}')
print('-' * 50)

for i in range(1, args.iter + 1):
    t_iter = time.time()

    # 1. Apply current optimizer state to scene params
    #    Z-only constraint: restore XY from frozen initial positions so the
    #    lens footprint never drifts; only surface heights (Z) are updated.
    vp_current = opt[VP_KEY]
    xy_restore_mask = mi.Float(1.0) - z_update_mask
    vp_constrained = vp_current * z_update_mask + vp_init * xy_restore_mask
    params[VP_KEY] = vp_constrained
    params.update()

    # 2. Render — seed_grad separates primal and gradient samples (PRB requirement)
    img = mi.render(scene, params, spp=args.spp, seed=i, seed_grad=i + 100000)

    # 3. Normalize to [0,1] and compute L2 loss vs target
    img_norm = normalize_render(img)
    loss = dr.mean(dr.square(img_norm - target_mi))

    # 4. Backpropagate through the rendering
    dr.backward(loss)

    # 5. Log gradient magnitude before step (sanity check)
    grad_vp = dr.grad(opt[VP_KEY])
    grad_max = float(np.array(dr.max(dr.abs(grad_vp))).flat[0])

    # 6. Optimizer step
    opt.step()

    # 7. Log
    loss_val = float(np.array(loss).flat[0])
    losses.append(loss_val)

    # Measure max Z displacement from initial
    vp_np_now = np.array(dr.detach(opt[VP_KEY])).reshape(-1, 3)
    dz = vp_np_now[:, 2] - vp_np[:, 2]
    dz_max = float(np.abs(dz).max())

    t_elapsed = time.time() - t_iter
    print(f'{i:5d}  {loss_val:10.6f}  {grad_max:10.2e}  {dz_max:10.6f}m  {t_elapsed:5.1f}s')

    # 7. Save checkpoint
    if i % args.save_every == 0 or i == args.iter:
        with dr.suspend_grad():
            img_check = mi.render(scene, spp=args.spp * 4, seed=i + 10000)
        img_check_norm = np.array(normalize_render(img_check))
        save_render(img_check_norm, i, loss_val)
        save_obj(vp_np_now, i)

t_total = time.time() - t_loop
print(f'\nOptimization complete in {t_total:.0f}s  ({t_total/args.iter:.1f}s/iter)')

# ── Save final OBJ ─────────────────────────────────────────────────────────────
vp_final_np = np.array(dr.detach(params[VP_KEY])).reshape(-1, 3)
final_obj = save_obj(vp_final_np, args.iter)
# Also save as the canonical optimized name
import shutil
shutil.copy(final_obj, OUT_DIR / 'optimized_lens.obj')
print(f'\nFinal OBJ: {OUT_DIR}/optimized_lens.obj')

# ── Loss curve ─────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 4), facecolor='black')
ax.plot(range(1, len(losses) + 1), losses, color='#f90', linewidth=1.5)
ax.set_facecolor('black')
ax.tick_params(colors='#aaa')
ax.set_xlabel('Iteration', color='#aaa')
ax.set_ylabel('L2 Loss', color='#aaa')
ax.set_title('Differentiable caustic optimization — loss curve', color='#ddd')
for sp in ax.spines.values():
    sp.set_edgecolor('#444')
plt.tight_layout()
plt.savefig(OUT_DIR / 'loss.png', dpi=120, bbox_inches='tight', facecolor='black')
plt.close()
print(f'Loss curve: {OUT_DIR}/loss.png')

# ── Side-by-side comparison ────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor='black')
titles = ['Before optimization', 'After optimization', 'Target']
imgs   = [img0_norm, np.array(normalize_render(img)), target_np]
for ax, title, im in zip(axes, titles, imgs):
    ax.imshow(np.clip(im, 0, 1), origin='lower')
    ax.set_title(title, color='#ddd', fontsize=11)
    ax.set_facecolor('black')
    ax.axis('off')
plt.tight_layout()
plt.savefig(OUT_DIR / 'comparison.png', dpi=120, bbox_inches='tight', facecolor='black')
plt.close()
print(f'Comparison: {OUT_DIR}/comparison.png')
