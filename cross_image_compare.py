#!/usr/bin/env python3
"""
cross_image_compare.py — Compare all 5 Final Cows normal renders on the same metrics.

Usage:
  python3 cross_image_compare.py
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
from scipy.ndimage import sobel, gaussian_filter

PROJECT = Path(__file__).parent
OUT_DIR = PROJECT / 'Final cows'
HANDOFF = PROJECT / 'claude_chat_handoff4'

SLUGS = ['banknote', 'charcol', 'inkbrush', 'nikon', 'woodblock']

def sharpness(img):
    sx = sobel(img.astype(float), axis=1)
    sy = sobel(img.astype(float), axis=0)
    return float(np.mean(np.sqrt(sx**2 + sy**2)))

def contrast(img):
    v = img.ravel().astype(float)
    v = v[v > 0.01] if (v > 0.01).sum() > 100 else v
    return float((np.percentile(v, 99) - np.percentile(v, 1)) / (np.mean(v) + 1e-9))

def black_frac(img):
    return float((img < 0.05).mean())

def high_freq_ratio(img):
    f = np.fft.fftshift(np.fft.fft2(img.astype(float)))
    mag = np.log1p(np.abs(f))
    h, w = mag.shape
    cx, cy = w//2, h//2
    r = min(h,w)//4
    Y, X = np.ogrid[:h, :w]
    mask = (X-cx)**2 + (Y-cy)**2 > r**2
    return float(mag[mask].sum() / (mag.sum() + 1e-12))

def pearson_r(a, b):
    a = a.ravel().astype(float); b = b.ravel().astype(float)
    if a.std() < 1e-10 or b.std() < 1e-10: return 0.0
    return float(np.corrcoef(a, b)[0,1])

SZ = 512

rows = []
for slug in SLUGS:
    print(f"Processing {slug}...")

    # Input image
    candidates = [p for p in (PROJECT / 'Final cows').iterdir()
                  if slug in p.stem.lower() and p.suffix.lower() in ('.png','.jpg','.jpeg')]
    if candidates:
        input_img = np.array(Image.open(candidates[0]).convert('L').resize((SZ,SZ), Image.LANCZOS), dtype=np.float64) / 255.0
    else:
        input_img = np.zeros((SZ,SZ))

    sx = sobel(input_img, axis=1); sy = sobel(input_img, axis=0)
    input_edges = np.sqrt(sx**2 + sy**2)
    if input_edges.max() > 0: input_edges /= input_edges.max()

    # Caustic
    caustic_path = PROJECT / 'Final cows' / slug / 'normal' / 'caustic.png'
    if caustic_path.exists():
        caustic = np.array(Image.open(caustic_path).convert('L').resize((SZ,SZ), Image.LANCZOS), dtype=np.float64) / 255.0
        caustic_rgb = np.array(Image.open(caustic_path).convert('RGB').resize((SZ,SZ), Image.LANCZOS))
    else:
        caustic = np.zeros((SZ,SZ))
        caustic_rgb = np.zeros((SZ,SZ,3), dtype=np.uint8)

    rows.append({
        'slug': slug,
        # Input metrics
        'input_sharp':      sharpness(input_img),
        'input_contrast':   float(input_img.std()),
        'input_edge_dens':  float(input_edges.mean()),
        'input_hf':         high_freq_ratio(input_img),
        # Caustic metrics
        'caustic_sharp':    sharpness(caustic),
        'caustic_contrast': contrast(caustic),
        'caustic_black':    black_frac(caustic),
        # Correlation
        'r_edges':          pearson_r(caustic, input_edges),
        'r_bright':         pearson_r(caustic, input_img),
        # Store images for display
        '_input': input_img,
        '_caustic_rgb': caustic_rgb,
        '_edges': input_edges,
    })

# Sort by caustic sharpness
rows_sorted = sorted(rows, key=lambda r: r['caustic_sharp'], reverse=True)

# ── Write markdown table ───────────────────────────────────────────────────────
md_path = OUT_DIR / 'cross_image_metrics.md'
with open(md_path, 'w') as f:
    f.write("# Cross-Image Metrics — All 5 Final Cows (normal)\n\n")
    f.write("Sorted by caustic sharpness.\n\n")
    f.write("| Rank | Slug | in_sharp | in_contrast | in_edge% | caustic_sharp | caustic_contrast | black% | r(edges) | r(bright) |\n")
    f.write("|------|------|----------|-------------|----------|---------------|-----------------|--------|----------|----------|\n")
    for i, r in enumerate(rows_sorted):
        f.write(f"| {i+1} | {r['slug']:<10} | {r['input_sharp']:.4f} | {r['input_contrast']:.3f} | "
                f"{r['input_edge_dens']:.3f} | {r['caustic_sharp']:.4f} | {r['caustic_contrast']:.3f} | "
                f"{r['caustic_black']:.1%} | {r['r_edges']:+.3f} | {r['r_bright']:+.3f} |\n")
    f.write("\n**Key:** in_sharp=input sharpness, in_edge%=edge density, r(edges)=correlation caustic↔input_edges\n")
    f.write("A good caustic treatment: high caustic_sharp + high black% + positive r(edges)\n")

print(f"\nMetrics written: {md_path}")
print("\nRanked by caustic sharpness:")
for i, r in enumerate(rows_sorted):
    print(f"  {i+1}. {r['slug']:<10}  caustic_sharp={r['caustic_sharp']:.4f}  black={r['caustic_black']:.1%}  r_edges={r['r_edges']:+.3f}")

# ── Bar chart figure ───────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(18, 11), facecolor='#111')
axes = axes.ravel()
slugs_sorted = [r['slug'] for r in rows_sorted]
colors = ['#f0a000', '#d08000', '#b06000', '#905000', '#704000']

def bar(ax, vals, title, fmt='.3f', color='#f0a000'):
    bars = ax.bar(slugs_sorted, vals, color=colors)
    for bar_, v in zip(bars, vals):
        ax.text(bar_.get_x() + bar_.get_width()/2, bar_.get_height() + max(vals)*0.01,
                f'{v:{fmt}}', ha='center', va='bottom', color='#ddd', fontsize=8)
    ax.set_title(title, color='#ddd', fontsize=9)
    ax.set_facecolor('#1a1a1a')
    ax.tick_params(colors='#888', labelsize=8)
    ax.spines[:].set_color('#333')
    ax.set_ylim(0, max(vals) * 1.15)

bar(axes[0], [r['caustic_sharp'] for r in rows_sorted], 'Caustic Sharpness\n(higher = crisper lines)')
bar(axes[1], [r['caustic_black'] for r in rows_sorted], 'Black Coverage\n(higher = better dark background)', fmt='.1%')
bar(axes[2], [r['r_edges'] for r in rows_sorted], 'r(caustic, input_edges)\n(higher = better encoding)', fmt='+.3f')
bar(axes[3], [r['input_sharp'] for r in rows_sorted], 'Input Sharpness\n(input quality metric)')
bar(axes[4], [r['input_edge_dens'] for r in rows_sorted], 'Input Edge Density\n(how much edge content exists)')
bar(axes[5], [r['caustic_contrast'] for r in rows_sorted], 'Caustic Contrast\n(dynamic range)')

fig.suptitle('Cross-Image Metrics — All 5 Final Cows (normal, baseline params)', color='white', fontsize=12)
plt.tight_layout()
out_png = OUT_DIR / 'cross_image_metrics.png'
plt.savefig(out_png, dpi=110, bbox_inches='tight', facecolor='#111')
plt.close()
print(f"\nChart: {out_png}")

# Visual comparison strip (input + caustic for each)
fig2, axes2 = plt.subplots(2, 5, figsize=(25, 10), facecolor='#111')
for i, r in enumerate(rows_sorted):
    axes2[0,i].imshow(r['_input'], cmap='gray', origin='upper', interpolation='nearest')
    axes2[0,i].set_title(f"{r['slug']}\ninput (sharp={r['input_sharp']:.3f})", color='#ddd', fontsize=9)
    axes2[0,i].axis('off')
    axes2[1,i].imshow(r['_caustic_rgb'], origin='upper', interpolation='nearest')
    axes2[1,i].set_title(f"caustic (sharp={r['caustic_sharp']:.3f}\nblack={r['caustic_black']:.1%}  r={r['r_edges']:+.3f})",
                         color='#ddd', fontsize=9)
    axes2[1,i].axis('off')
fig2.suptitle('Visual Comparison: Input vs Caustic — All 5 Treatments', color='white', fontsize=12)
plt.tight_layout()
strip_png = OUT_DIR / 'cross_image_strip.png'
plt.savefig(strip_png, dpi=100, bbox_inches='tight', facecolor='#111')
plt.close()
print(f"Strip: {strip_png}")

import subprocess
dst_chart = HANDOFF / 'V_cross_image_metrics.png'
dst_strip = HANDOFF / 'V2_cross_image_strip.png'
subprocess.run(['python3', str(PROJECT/'cc_resize.py'), str(out_png),   '--out', str(dst_chart)], check=True)
subprocess.run(['python3', str(PROJECT/'cc_resize.py'), str(strip_png), '--out', str(dst_strip)], check=True)
print(f"Handoff: {dst_chart.name}  {dst_strip.name}")
