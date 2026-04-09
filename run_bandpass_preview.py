#!/usr/bin/env python3
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

src = "/Users/admin/causticsEngineering/Final cows/ink_split.png"
out = "/Users/admin/causticsEngineering"

img  = np.array(Image.open(src).convert('RGB'), dtype=np.float32) / 255.0
gray = 0.299*img[:,:,0] + 0.587*img[:,:,1] + 0.114*img[:,:,2]
print(f"Loaded: {gray.shape}  mean={gray.mean():.3f}  std={gray.std():.3f}")

def bandpass(g, lo, hi):
    low  = gaussian_filter(g.astype('float64'), sigma=lo)
    high = gaussian_filter(g.astype('float64'), sigma=hi)
    bp   = low - high
    bp  -= bp.min()
    if bp.max() > 0: bp /= bp.max()
    return bp.astype('float32')

def save_png(arr, path):
    Image.fromarray((arr.clip(0,1)*255).astype('uint8')).save(path)

bp_q3   = bandpass(gray, lo=2,  hi=32)
bp_q4   = bandpass(gray, lo=1,  hi=8)
bp_wide = bandpass(gray, lo=3,  hi=64)

save_png(bp_q3,   f"{out}/ink_split_bp_q3_lo2_hi32.png")
save_png(bp_q4,   f"{out}/ink_split_bp_q4_lo1_hi8.png")
save_png(bp_wide, f"{out}/ink_split_bp_wide_lo3_hi64.png")

# 4-panel preview
fig, axes = plt.subplots(2, 2, figsize=(14, 14), facecolor='black')
panels = [
    (gray,    "Original — raw grayscale\n(background split will dominate solver)"),
    (bp_q3,   "Bandpass  lo=2  hi=32  [q3 — broad mid-freq]\nBackground equalised, cow structure retained"),
    (bp_q4,   "Bandpass  lo=1  hi=8   [q4 — narrow mid-freq]\nEdge-emphasis, fine ink detail preserved"),
    (bp_wide, "Bandpass  lo=3  hi=64  [wider band]\nSofter, more tonal gradients retained"),
]
for ax, (data, title) in zip(axes.ravel(), panels):
    ax.imshow(data, cmap='gray', vmin=0, vmax=1, interpolation='lanczos')
    ax.set_title(title, color='white', fontsize=11, pad=6)
    ax.axis('off')
    ax.set_facecolor('black')
plt.suptitle("ink_split.png — Bandpass preprocessing options\n(removes asymmetric background, retains cow detail for solver)",
             color='#eee', fontsize=13, y=0.998)
plt.tight_layout(pad=1.0)
plt.savefig(f"{out}/ink_split_bandpass_preview.png",
            dpi=150, bbox_inches='tight', facecolor='black')
plt.close()

for name, arr in [("original",gray),("bp_q3",bp_q3),("bp_q4",bp_q4),("bp_wide",bp_wide)]:
    print(f"  {name:12s}  mean={arr.mean():.3f}  std={arr.std():.3f}")
print("ALL DONE")
