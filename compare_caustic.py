#!/usr/bin/env python3
"""
compare_caustic.py — Quantitative comparison between target image and caustic render.

Outputs examples/comparison_analysis.png with 6 panels:
  1. Original (grayscale)
  2. Caustic v2 (normalised grayscale)
  3. Inverted original  (caustics may encode inverse brightness)
  4. SSIM map: caustic vs original
  5. SSIM map: caustic vs inverted original
  6. Edge overlay: Canny edges of original drawn on caustic
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
from pathlib import Path
from skimage.metrics import structural_similarity as ssim
from skimage.filters import sobel
from skimage.feature import canny

BASE        = Path("/Users/admin/causticsEngineering/examples")
ORIG_PATH   = BASE.parent / "examples" / "cow render.jpg"
CAUS_PATH   = BASE / "caustic_cow_v2.png"
OUT_PATH    = BASE / "comparison_analysis.png"

# ── Load and normalise both images to float32 [0,1] at the same size ──────────
orig_pil = Image.open(ORIG_PATH).convert('L')   # grayscale
caus_pil = Image.open(CAUS_PATH).convert('L')

# Resize caustic to match original (original is 512×512)
target_size = orig_pil.size   # (W, H)
caus_pil_r  = caus_pil.resize(target_size, Image.LANCZOS)

orig = np.array(orig_pil,   dtype=np.float32) / 255.0
caus = np.array(caus_pil_r, dtype=np.float32) / 255.0

# Normalise caustic to [0,1] (it may have a compressed range after the render)
if caus.max() > caus.min():
    caus = (caus - caus.min()) / (caus.max() - caus.min())
if orig.max() > orig.min():
    orig = (orig - orig.min()) / (orig.max() - orig.min())

orig_inv = 1.0 - orig   # inverted original

# ── SSIM ──────────────────────────────────────────────────────────────────────
ssim_val,  ssim_map  = ssim(caus, orig,     data_range=1.0, full=True)
ssim_inv_val, ssim_inv_map = ssim(caus, orig_inv, data_range=1.0, full=True)

# ── Edge map of original (Canny) ───────────────────────────────────────────────
edges = canny(orig, sigma=2.0)   # bool edge mask

# Edge overlay: caustic as background, edges in bright cyan
caus_rgb   = np.stack([caus, caus * 0.6, caus * 0.0], axis=-1)   # amber tint
edge_overlay = caus_rgb.copy()
edge_overlay[edges, 0] = 0.0
edge_overlay[edges, 1] = 1.0
edge_overlay[edges, 2] = 0.9   # cyan edges

# Also compute Sobel gradient magnitude for a softer edge map
sobel_orig = sobel(orig)
if sobel_orig.max() > 0:
    sobel_orig = sobel_orig / sobel_orig.max()

# ── Correlation at each rotation/flip to detect geometric transform ────────────
def masked_corr(a, b):
    """Pearson correlation between two same-size float arrays."""
    a_flat = a.ravel() - a.mean()
    b_flat = b.ravel() - b.mean()
    denom  = np.std(a) * np.std(b)
    return float(np.dot(a_flat, b_flat) / (len(a_flat) * denom)) if denom > 1e-9 else 0.0

transforms = {
    'Identity':         caus,
    'FlipLR':           np.fliplr(caus),
    'FlipUD':           np.flipud(caus),
    'Flip both':        np.flipud(np.fliplr(caus)),
    'Rot90 CCW':        np.rot90(caus, k=1),
    'Rot90 CW':         np.rot90(caus, k=3),
    'Rot180':           np.rot90(caus, k=2),
}

print("\n── Pearson correlation: caustic vs original ─────────────────────────────")
print(f"  {'Transform':<16}  vs orig    vs inv")
best_k, best_v = None, -9
for name, tc in transforms.items():
    # Resize if rot90 changed shape (shouldn't for square, but be safe)
    if tc.shape != orig.shape:
        tc = np.array(Image.fromarray((tc*255).astype(np.uint8)).resize(target_size, Image.LANCZOS), dtype=np.float32)/255.0
    r_orig = masked_corr(tc, orig)
    r_inv  = masked_corr(tc, orig_inv)
    flag = " ◄ best" if r_orig > best_v else ""
    if r_orig > best_v:
        best_v, best_k = r_orig, name
    print(f"  {name:<16}  {r_orig:+.4f}   {r_inv:+.4f}{flag}")

print(f"\n  SSIM (caustic vs original):          {ssim_val:.4f}")
print(f"  SSIM (caustic vs inverted original): {ssim_inv_val:.4f}")
print(f"\n  Best geometric match: '{best_k}' (r={best_v:.4f})")

# ── Plot ───────────────────────────────────────────────────────────────────────
CMAP_SUN = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

fig, axes = plt.subplots(2, 3, figsize=(18, 12), facecolor='#111')
fig.suptitle(
    f"Caustic vs Target Analysis  |  SSIM(orig)={ssim_val:.4f}   SSIM(inv)={ssim_inv_val:.4f}"
    f"\nBest geometric match: {best_k}  (r={best_v:.4f})",
    color='white', fontsize=13, y=0.98
)

def styled(ax, title):
    ax.set_title(title, color='#ddd', fontsize=10, pad=6)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_facecolor('#111')
    for sp in ax.spines.values(): sp.set_visible(False)

# Panel 1: original
axes[0,0].imshow(orig,     cmap='gray',  vmin=0, vmax=1)
styled(axes[0,0], "Original (grayscale, normalised)")

# Panel 2: caustic
axes[0,1].imshow(caus,     cmap=CMAP_SUN, vmin=0, vmax=1)
styled(axes[0,1], "Caustic v2 (normalised)")

# Panel 3: inverted original
axes[0,2].imshow(orig_inv, cmap='gray',  vmin=0, vmax=1)
styled(axes[0,2], "Inverted original  (1 − orig)")

# Panel 4: SSIM map caustic vs original
sm1 = axes[1,0].imshow(ssim_map, cmap='RdYlGn', vmin=-1, vmax=1)
styled(axes[1,0], f"SSIM map: caustic vs original  (mean={ssim_val:.4f})")
plt.colorbar(sm1, ax=axes[1,0], fraction=0.046, pad=0.04)

# Panel 5: SSIM map caustic vs inverted
sm2 = axes[1,1].imshow(ssim_inv_map, cmap='RdYlGn', vmin=-1, vmax=1)
styled(axes[1,1], f"SSIM map: caustic vs inverted  (mean={ssim_inv_val:.4f})")
plt.colorbar(sm2, ax=axes[1,1], fraction=0.046, pad=0.04)

# Panel 6: edge overlay
axes[1,2].imshow(edge_overlay, vmin=0, vmax=1)
styled(axes[1,2], "Edge overlay: Canny edges (cyan) on caustic")

plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig(OUT_PATH, dpi=150, bbox_inches='tight', facecolor='#111')
plt.close()
print(f"\nSaved → {OUT_PATH}")
