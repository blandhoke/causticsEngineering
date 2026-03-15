#!/usr/bin/env python3
"""
analyze_befuddled_v5.py — 9-panel comparative analysis for befuddled cow v5.

Row 1: context  — input grayscale / v3 baseline / brightness histogram
Row 2: caustics — v4 broken / v5 fixed / difference map
Row 3: quant    — quadrant bars / SSIM heatmap / metrics text
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path

try:
    from skimage.metrics import structural_similarity as ssim
    from skimage.filters import sobel
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("skimage not available — SSIM and edge metrics will be skipped")

try:
    from scipy.stats import pearsonr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

BASE = Path("/Users/admin/causticsEngineering/examples")

# ── Load images ────────────────────────────────────────────────────────────────
def load_gray(path, size=1024):
    from PIL import Image
    img = Image.open(path).convert('L').resize((size, size))
    return np.array(img, dtype=np.float32) / 255.0

input_img = load_gray(BASE.parent / "examples/befuddled_cow_solver_input.jpg")
v3_img    = load_gray(BASE / "caustic_cow_v3.png")
v4_img    = load_gray(BASE / "caustic_befuddled_v4.png")
v5_img    = load_gray(BASE / "caustic_befuddled_v5.png")

print(f"Input stats:  min={input_img.min():.3f}  max={input_img.max():.3f}  mean={input_img.mean():.3f}")
print(f"v3 stats:     min={v3_img.min():.3f}  max={v3_img.max():.3f}  mean={v3_img.mean():.3f}")
print(f"v4 stats:     min={v4_img.min():.3f}  max={v4_img.max():.3f}  mean={v4_img.mean():.3f}")
print(f"v5 stats:     min={v5_img.min():.3f}  max={v5_img.max():.3f}  mean={v5_img.mean():.3f}")

# ── Metrics ────────────────────────────────────────────────────────────────────
ssim_v5 = ssim(v5_img, input_img, data_range=1.0) if HAS_SKIMAGE else float('nan')
ssim_v3 = ssim(v3_img, input_img[:v3_img.shape[0], :v3_img.shape[1]], data_range=1.0) if HAS_SKIMAGE else float('nan')
ssim_v4 = ssim(v4_img, input_img, data_range=1.0) if HAS_SKIMAGE else float('nan')

r_bright = pearsonr(v5_img.ravel(), input_img.ravel())[0] if HAS_SCIPY else float('nan')

if HAS_SKIMAGE:
    edges = sobel(input_img)
    edges_norm = edges / (edges.max() + 1e-9)
    r_edges = pearsonr(v5_img.ravel(), edges_norm.ravel())[0] if HAS_SCIPY else float('nan')
    ssim_map_v5, _ = ssim(v5_img, input_img, data_range=1.0, full=True)
    ssim_map_v5 = _
else:
    r_edges = float('nan')
    ssim_map_v5 = np.zeros_like(v5_img)

p75  = np.percentile(v5_img, 75)
p90  = np.percentile(v5_img, 90)
p99  = np.percentile(v5_img, 99)

# Physical lens params
native_dome_mm  = 24.825
phys_dome_mm    = 25.22
throw_mm        = 762.0
throw_in        = 30.0
margin_mm       = 25.4 - phys_dome_mm

# Quadrant brightness
h, w = v5_img.shape
def quad_mean(img, q):
    hh, hw = img.shape[0]//2, img.shape[1]//2
    regions = {
        'TL': img[:hh, :hw], 'TR': img[:hh, hw:],
        'BL': img[hh:, :hw], 'BR': img[hh:, hw:]
    }
    return regions[q].mean()

quads = ['TL', 'TR', 'BL', 'BR']
input_q = [quad_mean(input_img, q) for q in quads]
v3_q    = [quad_mean(v3_img,    q) for q in quads]
v5_q    = [quad_mean(v5_img,    q) for q in quads]

print(f"\nSSIM(v5, input):  {ssim_v5:.4f}")
print(f"SSIM(v4, input):  {ssim_v4:.4f}")
print(f"SSIM(v3, input):  {ssim_v3:.4f}")
print(f"r(v5, brightness): {r_bright:.4f}")
print(f"r(v5, edges):      {r_edges:.4f}")
print(f"v5 mean/std/p75/p90/p99: {v5_img.mean():.4f} / {v5_img.std():.4f} / {p75:.4f} / {p90:.4f} / {p99:.4f}")

# ── Plot ───────────────────────────────────────────────────────────────────────
CMAP_SUN = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

fig = plt.figure(figsize=(18, 18), facecolor='#0a0a0a')
gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.38, wspace=0.25)

title_kw  = dict(color='#dddddd', fontsize=11, pad=6)
label_kw  = dict(color='#aaaaaa', fontsize=9)

# ── Row 1 ──────────────────────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0]); ax1.set_facecolor('black')
ax1.imshow(input_img, cmap='gray', vmin=0, vmax=1)
ax1.set_title("Input: befuddled cow (solver input)", **title_kw)
ax1.text(0.02, 0.98,
         f"min={input_img.min():.3f}  max={input_img.max():.3f}  mean={input_img.mean():.3f}",
         transform=ax1.transAxes, color='#aaa', fontsize=8, va='top',
         bbox=dict(facecolor='black', alpha=0.6, pad=2))
ax1.axis('off')

ax2 = fig.add_subplot(gs[0, 1]); ax2.set_facecolor('black')
ax2.imshow(v3_img, cmap=CMAP_SUN, vmin=0, vmax=1)
ax2.set_title("v3 baseline: f=0.2m, 512px, \u03c3=1.5", **title_kw)
ax2.axis('off')

ax3 = fig.add_subplot(gs[0, 2]); ax3.set_facecolor('#111')
bins = np.linspace(0, 1, 64)
ax3.hist(input_img.ravel(), bins=bins, color='#4488cc', alpha=0.7, label='input', density=True)
ax3.hist(v5_img.ravel(),    bins=bins, color='#cc8833', alpha=0.7, label='v5 caustic', density=True)
ax3.set_title("Brightness histogram", **title_kw)
ax3.set_xlabel("Pixel value", **label_kw)
ax3.set_ylabel("Density", **label_kw)
ax3.legend(fontsize=9, labelcolor='#ccc', facecolor='#222', edgecolor='#444')
ax3.set_facecolor('#111')
ax3.tick_params(colors='#888')
for spine in ax3.spines.values(): spine.set_edgecolor('#444')

# ── Row 2 ──────────────────────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0]); ax4.set_facecolor('black')
ax4.imshow(v4_img, cmap=CMAP_SUN, vmin=0, vmax=1)
ax4.set_title(f"v4 BROKEN: f-mismatch + \u03c3 too large\nSSIM={ssim_v4:.4f}", **title_kw)
ax4.axis('off')

ax5 = fig.add_subplot(gs[1, 1]); ax5.set_facecolor('black')
ax5.imshow(v5_img, cmap=CMAP_SUN, vmin=0, vmax=1)
ax5.set_title(f"v5 FIXED: f=0.75, \u03c3=0.75\nSSIM={ssim_v5:.4f}", **title_kw)
ax5.axis('off')

ax6 = fig.add_subplot(gs[1, 2]); ax6.set_facecolor('black')
diff = v5_img.astype(np.float32) - v4_img.astype(np.float32)
vabs = np.abs(diff).max()
im6 = ax6.imshow(diff, cmap='RdBu_r', vmin=-vabs, vmax=vabs)
ax6.set_title("v5 \u2212 v4\n(red=brighter in v5, blue=dimmer)", **title_kw)
ax6.axis('off')
plt.colorbar(im6, ax=ax6, fraction=0.046, pad=0.04).ax.tick_params(colors='#aaa')

# ── Row 3 ──────────────────────────────────────────────────────────────────────
ax7 = fig.add_subplot(gs[2, 0]); ax7.set_facecolor('#111')
x   = np.arange(len(quads))
w_  = 0.25
ax7.bar(x - w_,    input_q, w_, color='#4488cc', label='input')
ax7.bar(x,         v3_q,    w_, color='#888888', label='v3 baseline')
ax7.bar(x + w_,    v5_q,    w_, color='#cc8833', label='v5 fixed')
ax7.set_xticks(x); ax7.set_xticklabels(quads, color='#ccc')
ax7.set_title("Quadrant brightness", **title_kw)
ax7.set_ylabel("Mean brightness", **label_kw)
ax7.legend(fontsize=8, labelcolor='#ccc', facecolor='#222', edgecolor='#444')
ax7.set_facecolor('#111')
ax7.tick_params(colors='#888')
for spine in ax7.spines.values(): spine.set_edgecolor('#444')

ax8 = fig.add_subplot(gs[2, 1]); ax8.set_facecolor('black')
if HAS_SKIMAGE:
    im8 = ax8.imshow(ssim_map_v5, cmap='hot', vmin=0, vmax=1)
    plt.colorbar(im8, ax=ax8, fraction=0.046, pad=0.04).ax.tick_params(colors='#aaa')
else:
    ax8.text(0.5, 0.5, 'skimage not available', transform=ax8.transAxes,
             ha='center', va='center', color='#aaa')
ax8.set_title("SSIM heatmap: v5 vs input", **title_kw)
ax8.axis('off')

ax9 = fig.add_subplot(gs[2, 2]); ax9.set_facecolor('#0d0d0d')
ax9.axis('off')
metrics_text = (
    f"{'─'*38}\n"
    f"  CAUSTIC QUALITY\n"
    f"{'─'*38}\n"
    f"  SSIM(v5, input)     {ssim_v5:>8.4f}\n"
    f"  SSIM(v4, input)     {ssim_v4:>8.4f}  [broken]\n"
    f"  SSIM(v3, baseline)  {ssim_v3:>8.4f}\n"
    f"  r(v5, brightness)   {r_bright:>8.4f}\n"
    f"  r(v5, Sobel edges)  {r_edges:>8.4f}\n"
    f"\n"
    f"  v5 brightness\n"
    f"    mean  {v5_img.mean():>8.4f}\n"
    f"    std   {v5_img.std():>8.4f}\n"
    f"    p75   {p75:>8.4f}\n"
    f"    p90   {p90:>8.4f}\n"
    f"    p99   {p99:>8.4f}\n"
    f"\n"
    f"{'─'*38}\n"
    f"  PHYSICAL LENS\n"
    f"{'─'*38}\n"
    f"  Native dome   {native_dome_mm:>6.2f} mm\n"
    f"  Physical dome {phys_dome_mm:>6.2f} mm  / 25.4mm limit\n"
    f"  Margin        {margin_mm:>6.3f} mm\n"
    f"  Throw         {throw_in:>6.1f}\"  ({throw_mm:.0f} mm)\n"
    f"  Fits 1\" stock  {'YES' if phys_dome_mm < 25.4 else 'NO'}  ({margin_mm:.3f}mm margin)\n"
    f"  Scale factor  1.0159x\n"
    f"{'─'*38}\n"
)
ax9.text(0.04, 0.97, metrics_text, transform=ax9.transAxes,
         fontfamily='monospace', fontsize=8.5, color='#cccccc',
         va='top', linespacing=1.4)
ax9.set_title("Metrics", **title_kw)

fig.suptitle(
    "Befuddled Cow v5 — Bug-Fixed Render  |  f=0.75m  |  IOR 1.49  |  \u03c3=0.75px  |  4-pass",
    color='white', fontsize=14, y=0.98)

out = BASE / "befuddled_analysis_v5.png"
plt.savefig(out, dpi=120, bbox_inches='tight', facecolor='#0a0a0a')
plt.close()
print(f"\nSaved → {out}")
