#!/usr/bin/env python3
"""
analyze_pipeline.py — Diagnostic: visualize every stage of the caustic pipeline.

Usage:
  python3 analyze_pipeline.py --slug inkbrush --speed normal
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from PIL import Image
from scipy.ndimage import sobel, gaussian_filter

PROJECT = Path(__file__).parent

parser = argparse.ArgumentParser()
parser.add_argument('--slug',  required=True)
parser.add_argument('--speed', default='normal')
args = parser.parse_args()

SLUG  = args.slug
SPEED = args.speed

COW_DIR  = PROJECT / 'Final cows' / SLUG / SPEED
OUT_DIR  = PROJECT / 'Final cows' / SLUG / 'analysis'
HANDOFF  = PROJECT / 'claude_chat_handoff4'
OUT_DIR.mkdir(parents=True, exist_ok=True)

OBJ_PATH    = COW_DIR / 'mesh.obj'
ACCUM_PATH  = COW_DIR / 'accum.npy'
CAUSTIC_PNG = COW_DIR / 'caustic.png'

# ── Input image ───────────────────────────────────────────────────────────────
# Find source input image
INPUT_PATHS = list((PROJECT / 'Final cows').glob(f'{SLUG}.*'))
INPUT_PATHS += list((PROJECT / 'Final cows').glob(f' {SLUG}.*'))
INPUT_PATHS += list((PROJECT / 'Final cows').glob(f'*{SLUG}*'))
input_candidates = [p for p in (PROJECT / 'Final cows').iterdir()
                    if SLUG in p.stem.lower() and p.suffix.lower() in ('.png','.jpg','.jpeg')]
if not input_candidates:
    # Try project root
    input_candidates = list(PROJECT.glob(f'*{SLUG}*'))
    input_candidates = [p for p in input_candidates if p.suffix.lower() in ('.png','.jpg','.jpeg')]

if input_candidates:
    input_img_raw = np.array(Image.open(input_candidates[0]).convert('L').resize((512,512), Image.LANCZOS), dtype=np.float64)
    input_img = input_img_raw / 255.0
    input_source = input_candidates[0].name
else:
    input_img = np.zeros((512,512))
    input_source = 'NOT FOUND'

print(f"[{SLUG}/{SPEED}] Input: {input_source}")

# ── Helper: FFT spectrum ───────────────────────────────────────────────────────
def fft_spectrum(img):
    f = np.fft.fftshift(np.fft.fft2(img))
    mag = np.log1p(np.abs(f))
    return mag / mag.max() if mag.max() > 0 else mag

def high_freq_ratio(img):
    f = np.fft.fftshift(np.fft.fft2(img))
    mag = np.log1p(np.abs(f))
    h, w = mag.shape
    cx, cy = w//2, h//2
    r = min(h,w)//4
    Y, X = np.ogrid[:h, :w]
    mask = (X-cx)**2 + (Y-cy)**2 > r**2
    return mag[mask].sum() / mag.sum() if mag.sum() > 0 else 0

def sharpness(img):
    sx = sobel(img, axis=1)
    sy = sobel(img, axis=0)
    return np.mean(np.sqrt(sx**2 + sy**2))

def dynamic_range(img):
    v = img[img > 0] if img.max() > 0 else img.ravel()
    if len(v) < 10: return 0
    return (np.percentile(v, 99) - np.percentile(v, 1)) / (np.mean(v) + 1e-9)

def pearson_r(a, b):
    a = a.ravel().astype(float); b = b.ravel().astype(float)
    if a.std() < 1e-10 or b.std() < 1e-10: return 0.0
    return float(np.corrcoef(a, b)[0,1])

# ── Sobel edges of input ───────────────────────────────────────────────────────
sx = sobel(input_img, axis=1); sy = sobel(input_img, axis=0)
input_edges = np.sqrt(sx**2 + sy**2)
input_edges /= input_edges.max() if input_edges.max() > 0 else 1

# ── OBJ heightmap ─────────────────────────────────────────────────────────────
print(f"[{SLUG}/{SPEED}] Parsing OBJ...")
heightmap = np.zeros((512, 512))
heightmap_counts = np.zeros((512, 512))

if OBJ_PATH.exists():
    raw = OBJ_PATH.read_bytes()
    lines = raw.split(b'\n')
    verts = np.fromstring(
        b'\n'.join(l[2:] for l in lines if l.startswith(b'v ')).decode(),
        dtype=np.float64, sep=' '
    ).reshape(-1, 3)

    xmin, xmax = verts[:,0].min(), verts[:,0].max()
    ymin, ymax = verts[:,1].min(), verts[:,1].max()
    zmin, zmax = verts[:,2].min(), verts[:,2].max()

    # Only top surface vertices (z > median)
    zmid = (zmin + zmax) / 2
    top_verts = verts[verts[:,2] > zmid]

    px = ((top_verts[:,0] - xmin) / (xmax - xmin + 1e-12) * 511).astype(int).clip(0,511)
    py = ((top_verts[:,1] - ymin) / (ymax - ymin + 1e-12) * 511).astype(int).clip(0,511)
    np.add.at(heightmap, (py, px), top_verts[:,2])
    np.add.at(heightmap_counts, (py, px), 1)
    mask = heightmap_counts > 0
    heightmap[mask] /= heightmap_counts[mask]
    heightmap[~mask] = zmin
    heightmap = np.fliplr(heightmap)
    heightmap = (heightmap - heightmap.min()) / (heightmap.max() - heightmap.min() + 1e-12)

    face_lines = [l for l in lines if l.startswith(b'f ')]
    n_faces = len(face_lines)
    dome_mm = (zmax - zmin) * 1000
    print(f"[{SLUG}/{SPEED}] OBJ: {len(verts):,} verts  {n_faces:,} faces  dome={dome_mm:.2f}mm")
else:
    print(f"[{SLUG}/{SPEED}] WARNING: OBJ not found at {OBJ_PATH}")
    n_faces = 0; dome_mm = 0

# OBJ gradient magnitude
hsx = sobel(heightmap, axis=1); hsy = sobel(heightmap, axis=0)
obj_gradient = np.sqrt(hsx**2 + hsy**2)
obj_gradient /= obj_gradient.max() if obj_gradient.max() > 0 else 1

r_solver = pearson_r(obj_gradient, input_edges)
print(f"[{SLUG}/{SPEED}] r(OBJ_gradient, input_edges) = {r_solver:.4f}")

# ── Raw accumulator ────────────────────────────────────────────────────────────
if ACCUM_PATH.exists():
    accum = np.load(ACCUM_PATH)
    raw_accum = np.fliplr(accum.copy())
    if raw_accum.max() > 0: raw_accum /= raw_accum.max()
    raw_accum_display = np.sqrt(raw_accum)  # sqrt gamma for display only
    print(f"[{SLUG}/{SPEED}] Accum: min={accum.min():.6g}  max={accum.max():.6g}  "
          f"mean={accum.mean():.6g}  DR={dynamic_range(raw_accum):.2f}")
else:
    print(f"[{SLUG}/{SPEED}] WARNING: accum.npy not found")
    raw_accum = np.zeros((512,512))
    raw_accum_display = raw_accum

r_raytrace = pearson_r(raw_accum, input_edges)
print(f"[{SLUG}/{SPEED}] r(raw_accum, input_edges)    = {r_raytrace:.4f}")

# ── Caustic PNG ────────────────────────────────────────────────────────────────
SZ = 512
if CAUSTIC_PNG.exists():
    caustic = np.array(Image.open(CAUSTIC_PNG).convert('L').resize((SZ,SZ), Image.LANCZOS), dtype=np.float64) / 255.0
    caustic_rgb = np.array(Image.open(CAUSTIC_PNG).convert('RGB').resize((SZ,SZ), Image.LANCZOS))
else:
    caustic = np.zeros((SZ,SZ))
    caustic_rgb = np.zeros((SZ,SZ,3), dtype=np.uint8)

r_final = pearson_r(caustic, input_edges)
print(f"[{SLUG}/{SPEED}] r(final_output, input_edges)  = {r_final:.4f}")

# ── Sharpness scores ──────────────────────────────────────────────────────────
sharp_input  = sharpness(input_img)
sharp_obj    = sharpness(heightmap)
sharp_accum  = sharpness(raw_accum)
sharp_final  = sharpness(caustic)
print(f"[{SLUG}/{SPEED}] Sharpness: input={sharp_input:.4f}  obj={sharp_obj:.4f}  "
      f"accum={sharp_accum:.4f}  final={sharp_final:.4f}")

hf_input = high_freq_ratio(input_img)
hf_obj   = high_freq_ratio(heightmap)
hf_accum = high_freq_ratio(raw_accum)

# ── Build figure (3 rows × 4 cols) ────────────────────────────────────────────
fig, axes = plt.subplots(3, 4, figsize=(20, 16), facecolor='#0a0a0a')
fig.suptitle(f'Pipeline Diagnostic: {SLUG}/{SPEED}', color='white', fontsize=14)

def show(ax, img, title, cmap='gray', vmin=None, vmax=None):
    ax.imshow(img, cmap=cmap, vmin=vmin, vmax=vmax, origin='upper', interpolation='nearest')
    ax.set_title(title, color='#ddd', fontsize=8, pad=3)
    ax.axis('off')
    ax.set_facecolor('#0a0a0a')

# Row 1 — Input
show(axes[0,0], input_img, f'Input image\n{input_source}\nnon-zero={100*(input_img>0).mean():.0f}%  sharp={sharp_input:.3f}')
show(axes[0,1], fft_spectrum(input_img), f'Input FFT spectrum\nhigh-freq energy: {hf_input:.1%}', cmap='inferno')
show(axes[0,2], input_edges, f'Input Sobel edges\nmean edge mag: {input_edges.mean():.4f}')
axes[0,3].hist(input_img.ravel(), bins=100, color='#f0a000', edgecolor='none')
axes[0,3].set_facecolor('#111'); axes[0,3].set_title(f'Input histogram\ncontrast: {input_img.std():.3f}', color='#ddd', fontsize=8)
axes[0,3].tick_params(colors='#888', labelsize=7); axes[0,3].spines[:].set_color('#333')

# Row 2 — OBJ heightmap
show(axes[1,0], heightmap, f'OBJ heightmap (Z values)\n{n_faces:,} faces  dome={dome_mm:.1f}mm\nsharp={sharp_obj:.3f}')
show(axes[1,1], obj_gradient, f'OBJ gradient magnitude\n(surface slope = light concentration)\nsharp={sharp_obj:.3f}')
# Overlay: cyan edges on gradient
overlay = np.stack([obj_gradient, obj_gradient, obj_gradient], axis=2)
overlay[:,:,0] = np.clip(obj_gradient - input_edges * 0.5, 0, 1)  # subtract cyan from red
overlay[:,:,1] = np.clip(obj_gradient + input_edges * 0.5, 0, 1)  # add to green
overlay[:,:,2] = np.clip(obj_gradient + input_edges * 0.5, 0, 1)  # add to blue
show(axes[1,2], overlay.clip(0,1), f'OBJ gradient + input edges (cyan)\nr(gradient, edges) = {r_solver:.3f}')
show(axes[1,3], fft_spectrum(heightmap), f'OBJ FFT spectrum\nhigh-freq: {hf_obj:.1%}', cmap='inferno')

# Row 3 — Ray trace
show(axes[2,0], raw_accum_display, f'Raw accumulator (sqrt gamma, no colormap)\nDR={dynamic_range(raw_accum):.2f}  sharp={sharp_accum:.3f}', cmap='gray')
show(axes[2,1], fft_spectrum(raw_accum), f'Accum FFT spectrum\nhigh-freq: {hf_accum:.1%}', cmap='inferno')
show(axes[2,2], caustic_rgb, f'Final caustic.png\nr(final, edges)={r_final:.3f}  sharp={sharp_final:.3f}')
# Overlay: cyan input edges on amber accum
acc_rgb = np.zeros((512,512,3))
if caustic.max() > 0:
    caustic_r = np.array(Image.open(CAUSTIC_PNG).convert('RGB').resize((512,512), Image.LANCZOS)).astype(float)/255 if CAUSTIC_PNG.exists() else acc_rgb
    acc_norm = caustic_r[:,:,0]  # use red channel as proxy
else:
    acc_norm = raw_accum_display
acc_for_overlay = caustic_rgb.astype(float)/255.0 if CAUSTIC_PNG.exists() else np.zeros((SZ,SZ,3))
overlay2 = np.stack([acc_for_overlay[:,:,0], acc_for_overlay[:,:,0]*0.6, np.zeros((SZ,SZ))], axis=2)
edge_boost = (input_edges * 0.8)[:,:,None] * np.array([0, 1, 1])
overlay2 = np.clip(overlay2 + edge_boost, 0, 1)
show(axes[2,3], overlay2, f'Accum (amber) + input edges (cyan)\nr(accum, edges)={r_raytrace:.3f}')

# Summary text box
summary = (f"SHARPNESS: input={sharp_input:.3f} → OBJ={sharp_obj:.3f} → "
           f"accum={sharp_accum:.3f} → final={sharp_final:.3f}\n"
           f"CORRELATION: OBJ/edges={r_solver:.3f}  accum/edges={r_raytrace:.3f}  final/edges={r_final:.3f}\n"
           f"HIGH-FREQ: input={hf_input:.1%}  OBJ={hf_obj:.1%}  accum={hf_accum:.1%}")
fig.text(0.5, 0.01, summary, color='#aaa', fontsize=8, ha='center',
         bbox=dict(boxstyle='round', facecolor='#111', edgecolor='#333'))

plt.tight_layout(rect=[0, 0.04, 1, 0.97])
out_png = OUT_DIR / 'pipeline_diagnostic.png'
plt.savefig(out_png, dpi=120, bbox_inches='tight', facecolor='#0a0a0a')
plt.close()
print(f"[{SLUG}/{SPEED}] Saved: {out_png}")

# cc_resize to handoff
import subprocess
prefix = f'W_' if SLUG == 'inkbrush' else f'X_'
dst = HANDOFF / f'{prefix}{SLUG}_pipeline_diagnostic.png'
subprocess.run(['python3', str(PROJECT/'cc_resize.py'), str(out_png), '--out', str(dst)], check=True)
print(f"[{SLUG}/{SPEED}] Handoff: {dst.name}")
