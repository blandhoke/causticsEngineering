#!/usr/bin/env python3
"""
overlay_compare.py — Overlay source input edges with caustic output at multiple
blend levels to show spatial correspondence.

Usage:
  python3 overlay_compare.py --slug inkbrush --speed normal
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
from scipy.ndimage import sobel, uniform_filter

PROJECT = Path(__file__).parent

parser = argparse.ArgumentParser()
parser.add_argument('--slug',  required=True)
parser.add_argument('--speed', default='normal')
args = parser.parse_args()

SLUG  = args.slug
SPEED = args.speed

COW_DIR = PROJECT / 'Final cows' / SLUG / SPEED
OUT_DIR = PROJECT / 'Final cows' / SLUG / 'analysis'
HANDOFF = PROJECT / 'claude_chat_handoff4'
OUT_DIR.mkdir(parents=True, exist_ok=True)

CAUSTIC_PNG = COW_DIR / 'caustic.png'
ACCUM_PATH  = COW_DIR / 'accum.npy'

# Load input image
input_candidates = [p for p in (PROJECT / 'Final cows').iterdir()
                    if SLUG in p.stem.lower() and p.suffix.lower() in ('.png','.jpg','.jpeg')]
if input_candidates:
    input_img = np.array(Image.open(input_candidates[0]).convert('L').resize((512,512), Image.LANCZOS), dtype=np.float64) / 255.0
else:
    input_img = np.zeros((512,512))

# Sobel edges of input
sx = sobel(input_img, axis=1); sy = sobel(input_img, axis=0)
input_edges = np.sqrt(sx**2 + sy**2)
if input_edges.max() > 0: input_edges /= input_edges.max()

# Load caustic
if CAUSTIC_PNG.exists():
    caustic_rgb = np.array(Image.open(CAUSTIC_PNG).convert('RGB').resize((512,512), Image.LANCZOS)).astype(float) / 255.0
    caustic_gray = caustic_rgb.mean(axis=2)
else:
    caustic_rgb = np.zeros((512,512,3)); caustic_gray = np.zeros((512,512))

# ── Build 5-alpha blend panels ────────────────────────────────────────────────
alphas = [0.0, 0.25, 0.5, 0.75, 1.0]

def make_blend(alpha):
    # Caustic: amber tones (from RGB)
    caustic_layer = caustic_rgb.copy()
    # Input edges: cyan (0, 1, 1)
    edge_layer = np.stack([np.zeros_like(input_edges),
                           input_edges,
                           input_edges], axis=2)
    blend = alpha * caustic_layer + (1 - alpha) * edge_layer
    return np.clip(blend, 0, 1)

# Difference image: caustic - input_edges (normalized)
diff = caustic_gray - input_edges
diff_norm = (diff - diff.min()) / (diff.max() - diff.min() + 1e-12)
# Red = caustic has extra light (caustic > edge), Blue = missing (caustic < edge)
diff_rgb = np.zeros((512,512,3))
diff_rgb[:,:,0] = np.clip(diff_norm * 2, 0, 1)          # red channel
diff_rgb[:,:,2] = np.clip((1 - diff_norm) * 2 - 1, 0, 1) # blue channel

# Local Pearson r in 32x32 sliding window
def local_pearson(a, b, radius=16):
    corr_map = np.zeros_like(a)
    from scipy.ndimage import uniform_filter
    sz = 2 * radius + 1
    a_mean = uniform_filter(a, sz)
    b_mean = uniform_filter(b, sz)
    a2 = uniform_filter(a**2, sz) - a_mean**2
    b2 = uniform_filter(b**2, sz) - b_mean**2
    ab = uniform_filter(a*b, sz) - a_mean*b_mean
    denom = np.sqrt(np.maximum(a2, 0) * np.maximum(b2, 0)) + 1e-12
    corr_map = ab / denom
    return corr_map.clip(-1, 1)

print(f"[{SLUG}/{SPEED}] Computing local correlation map...")
lcorr = local_pearson(caustic_gray, input_edges, radius=16)
lcorr_display = (lcorr + 1) / 2  # map [-1,1] to [0,1]

# ── Build figure ──────────────────────────────────────────────────────────────
# 2 rows: row1 = 5 blend panels; row2 = diff + correlation + two reference panels
fig = plt.figure(figsize=(25, 10), facecolor='#111')
fig.suptitle(f'Overlay Comparison: {SLUG}/{SPEED}  |  cyan=input edges  amber=caustic',
             color='white', fontsize=12)

# Row 1: 5 blend panels
for i, alpha in enumerate(alphas):
    ax = fig.add_subplot(2, 5, i+1)
    ax.imshow(make_blend(alpha))
    ax.set_title(f'α={alpha:.2f}\n{"pure edges" if alpha==0 else "pure caustic" if alpha==1 else "blend"}',
                 color='#ddd', fontsize=8)
    ax.axis('off')

# Row 2
ax6 = fig.add_subplot(2, 5, 6)
ax6.imshow(diff_rgb)
ax6.set_title('Difference\nred=caustic>edges  blue=edges>caustic', color='#ddd', fontsize=8)
ax6.axis('off')

ax7 = fig.add_subplot(2, 5, 7)
ax7.imshow(lcorr_display, cmap='RdYlGn', vmin=0, vmax=1)
ax7.set_title('Local Pearson r (32px window)\ngreen=good corr  red=anti-corr', color='#ddd', fontsize=8)
ax7.axis('off')

ax8 = fig.add_subplot(2, 5, 8)
ax8.imshow(input_img, cmap='gray')
ax8.set_title(f'Input image (reference)\nsharp edges={input_edges.mean():.4f}', color='#ddd', fontsize=8)
ax8.axis('off')

ax9 = fig.add_subplot(2, 5, 9)
ax9.imshow(caustic_rgb)
ax9.set_title(f'Final caustic (reference)\nglobal r={np.corrcoef(caustic_gray.ravel(), input_edges.ravel())[0,1]:.3f}',
              color='#ddd', fontsize=8)
ax9.axis('off')

ax10 = fig.add_subplot(2, 5, 10)
ax10.imshow(input_edges, cmap='gray')
ax10.set_title('Input Sobel edges\n(what solver should encode)', color='#ddd', fontsize=8)
ax10.axis('off')

plt.tight_layout(rect=[0, 0, 1, 0.95])
out_png = OUT_DIR / 'overlay_compare.png'
plt.savefig(out_png, dpi=110, bbox_inches='tight', facecolor='#111')
plt.close()
print(f"[{SLUG}/{SPEED}] Saved: {out_png}")

import subprocess
dst = HANDOFF / f'U_overlay_{SLUG}.png'
subprocess.run(['python3', str(PROJECT/'cc_resize.py'), str(out_png), '--out', str(dst)], check=True)
print(f"[{SLUG}/{SPEED}] Handoff: {dst.name}")
