#!/usr/bin/env python3
"""
sharpness_sweep.py — Re-render accum.npy with post-process parameter sweep,
measure sharpness/contrast/black-coverage at each step.

Usage:
  python3 sharpness_sweep.py --slug inkbrush --speed normal
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from scipy.ndimage import sobel, gaussian_filter

PROJECT = Path(__file__).parent

CMAP = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

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

ACCUM_PATH = COW_DIR / 'accum.npy'
if not ACCUM_PATH.exists():
    print(f"ERROR: {ACCUM_PATH} not found"); exit(1)

accum = np.load(ACCUM_PATH)
base  = np.fliplr(accum.copy())
if base.max() > 0: base /= base.max()

def sharpness(img):
    sx = sobel(img, axis=1); sy = sobel(img, axis=0)
    return float(np.mean(np.sqrt(sx**2 + sy**2)))

def contrast(img):
    v = img.ravel()
    v = v[v > 0] if (v > 0).sum() > 100 else v
    return float((np.percentile(v, 99) - np.percentile(v, 1)) / (np.mean(v) + 1e-9))

def black_frac(img):
    return float((img < 0.05).mean())

def render(img_in, post_sigma, gamma, interp_label='nearest'):
    img = img_in.copy()
    if post_sigma > 0:
        img = gaussian_filter(img, sigma=post_sigma)
    img = np.power(img, gamma)
    return img

# Build sweep grid
sigmas = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5]
gammas = [0.3, 0.4, 0.5, 0.60, 0.65, 0.70]

results = []
for g in gammas:
    for s in sigmas:
        img = render(base, s, g)
        results.append({
            'post_sigma': s,
            'gamma': g,
            'sharpness': sharpness(img),
            'contrast': contrast(img),
            'black_frac': black_frac(img),
            'img': img,
        })

# Score: composite of sharpness + contrast + black_frac (all normalized)
sharp_arr   = np.array([r['sharpness']  for r in results])
contrast_arr= np.array([r['contrast']   for r in results])
black_arr   = np.array([r['black_frac'] for r in results])

def norm01(a): mn, mx = a.min(), a.max(); return (a-mn)/(mx-mn+1e-12)
scores = norm01(sharp_arr) * 0.4 + norm01(contrast_arr) * 0.3 + norm01(black_arr) * 0.3
for i, r in enumerate(results):
    r['score'] = float(scores[i])

results.sort(key=lambda x: x['score'], reverse=True)

# ── Write markdown table ───────────────────────────────────────────────────────
md_path = OUT_DIR / 'sharpness_sweep.md'
with open(md_path, 'w') as f:
    f.write(f"# Sharpness Sweep — {SLUG}/{SPEED}\n\n")
    f.write("Ranked by composite score (0.4×sharpness + 0.3×contrast + 0.3×black_coverage)\n\n")
    f.write("| Rank | post_sigma | gamma | sharpness | contrast | black% | score |\n")
    f.write("|------|-----------|-------|-----------|----------|--------|-------|\n")
    for i, r in enumerate(results[:15]):
        f.write(f"| {i+1:2d}   | {r['post_sigma']:.2f}      | {r['gamma']:.2f}  | "
                f"{r['sharpness']:.4f}   | {r['contrast']:.3f}    | "
                f"{r['black_frac']:.1%}  | {r['score']:.3f} |\n")
    f.write("\n## Baseline (current defaults pre-sweep)\n\n")
    baseline = render(base, 0.5, 0.5)
    f.write(f"post_sigma=0.50  gamma=0.50  "
            f"sharpness={sharpness(baseline):.4f}  "
            f"contrast={contrast(baseline):.3f}  "
            f"black={black_frac(baseline):.1%}\n")
    f.write("\n## New defaults\n\n")
    new_def = render(base, 0.0, 0.70)
    f.write(f"post_sigma=0.00  gamma=0.70  "
            f"sharpness={sharpness(new_def):.4f}  "
            f"contrast={contrast(new_def):.3f}  "
            f"black={black_frac(new_def):.1%}\n")

print(f"[{SLUG}/{SPEED}] Sharpness sweep table: {md_path}")
print("\nTop 5 parameter combinations:")
for r in results[:5]:
    print(f"  σ={r['post_sigma']:.2f}  γ={r['gamma']:.2f}  "
          f"sharp={r['sharpness']:.4f}  contrast={r['contrast']:.3f}  "
          f"black={r['black_frac']:.1%}  score={r['score']:.3f}")

# ── Build grid of top 5 + baseline ────────────────────────────────────────────
baseline_entry = {
    'post_sigma': 0.5, 'gamma': 0.5, 'img': render(base, 0.5, 0.5),
    'sharpness': sharpness(baseline), 'score': 0.0, 'label': 'BASELINE\nσ=0.5 γ=0.5'
}
top5 = results[:5]
panels = [baseline_entry] + top5

fig, axes = plt.subplots(2, 3, figsize=(18, 12), facecolor='#111')
axes = axes.ravel()
for i, r in enumerate(panels):
    label = r.get('label') or f"σ={r['post_sigma']:.2f}  γ={r['gamma']:.2f}\nscore={r['score']:.3f}"
    axes[i].imshow(r['img'], cmap=CMAP, origin='upper', interpolation='nearest')
    axes[i].set_title(label, color='#ddd', fontsize=9)
    axes[i].axis('off')

fig.suptitle(f'Sharpness Sweep — {SLUG}/{SPEED} — Top 5 + Baseline', color='white', fontsize=12)
plt.tight_layout(pad=0.5)
grid_png = OUT_DIR / 'sharpness_sweep_grid.png'
plt.savefig(grid_png, dpi=120, bbox_inches='tight', facecolor='#111')
plt.close()
print(f"[{SLUG}/{SPEED}] Grid: {grid_png}")

# cc_resize to handoff
import subprocess
dst = HANDOFF / f'T_sharpness_sweep_{SLUG}.png'
subprocess.run(['python3', str(PROJECT/'cc_resize.py'), str(grid_png), '--out', str(dst)], check=True)
print(f"[{SLUG}/{SPEED}] Handoff: {dst.name}")
