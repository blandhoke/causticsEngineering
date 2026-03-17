#!/usr/bin/env python3
"""build_crispness_sheets.py — Build all crispness comparison contact sheets."""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image

BASE = Path("/Users/admin/causticsEngineering/Final cows/inkbrush")
HANDOFF = Path("/Users/admin/causticsEngineering/claude_chat_handoff4")


def load_img(path):
    return np.array(Image.open(path).convert('RGB'))


def make_sheet(images_labels, ncols, title, out_path, dpi=100):
    """Build a contact sheet. images_labels: list of (path, label) tuples."""
    nrows = (len(images_labels) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 5, nrows * 5 + 0.8),
                             facecolor='#111')
    if nrows == 1 and ncols == 1:
        axes = np.array([[axes]])
    elif nrows == 1:
        axes = axes[np.newaxis, :]
    elif ncols == 1:
        axes = axes[:, np.newaxis]

    for i, (path, label) in enumerate(images_labels):
        row, col = divmod(i, ncols)
        ax = axes[row, col]
        try:
            img = load_img(path)
            ax.imshow(img)
        except Exception as e:
            ax.set_facecolor('#111')
            ax.text(0.5, 0.5, f'MISSING\n{path.name}', color='red',
                    ha='center', va='center', transform=ax.transAxes, fontsize=8)
        ax.set_title(label, color='#ddd', fontsize=9, pad=4)
        ax.axis('off')

    # Hide empty axes
    for i in range(len(images_labels), nrows * ncols):
        row, col = divmod(i, ncols)
        axes[row, col].set_visible(False)

    fig.suptitle(title, color='white', fontsize=12, y=0.98)
    plt.tight_layout(pad=0.5, rect=[0, 0, 1, 0.97])
    plt.savefig(out_path, dpi=dpi, bbox_inches='tight', facecolor='#111')
    plt.close()
    print(f"  Saved: {out_path}")


# ── 3A: Sigma sweep (5 panels) ────────────────────────────────────────────────
print("Building 3A: sigma sweep contact sheet...")
sigma_panels = [
    (BASE / "sigma_sweep/sigma_025/caustic.png", "sigma=0.25\n(ultra-crisp)"),
    (BASE / "sigma_sweep/sigma_050/caustic.png", "sigma=0.50\n(very crisp)"),
    (BASE / "sigma_sweep/sigma_075/caustic.png", "sigma=0.75\n(crisp)"),
    (BASE / "sigma_sweep/sigma_100/caustic.png", "sigma=1.00\n(moderate)"),
    (BASE / "sigma_sweep/sigma_150/caustic.png", "sigma=1.50\n(baseline/auto)"),
]
out_sigma = BASE / "sigma_sweep/sigma_comparison.jpg"
make_sheet(sigma_panels, ncols=5, title="Inkbrush — Sigma Sweep (no post-blur, nearest, gamma=0.5)", out_path=out_sigma)

# ── 3B: Post-process sweep (6 panels) ─────────────────────────────────────────
print("Building 3B: post-process sweep contact sheet...")
pp_panels = [
    (BASE / "postprocess_sweep/no_postblur_nearest/caustic.png",  "no blur\nnearest"),
    (BASE / "postprocess_sweep/no_postblur_bilinear/caustic.png", "no blur\nbilinear"),
    (BASE / "postprocess_sweep/gaussian_03_nearest/caustic.png",  "gauss σ=0.3\nnearest"),
    (BASE / "postprocess_sweep/gaussian_05_nearest/caustic.png",  "gauss σ=0.5\nnearest"),
    (BASE / "postprocess_sweep/gaussian_05_bilinear/caustic.png", "gauss σ=0.5\nbilinear\n(BASELINE)"),
    (BASE / "postprocess_sweep/unsharp_nearest/caustic.png",      "unsharp r=1 a=1.5\nnearest"),
]
out_pp = BASE / "postprocess_sweep/postprocess_comparison.jpg"
make_sheet(pp_panels, ncols=3, title="Inkbrush — Post-Process Sweep (sigma=1.5 auto cache)", out_path=out_pp, dpi=120)

# ── 3C: Passes sweep (3 panels) ───────────────────────────────────────────────
print("Building 3C: passes sweep contact sheet...")
# Use original normal caustic as 4-pass baseline
passes_panels = [
    (BASE / "normal/caustic.png",               "4-pass σ=1.5 auto\n(baseline)"),
    (BASE / "passes_sweep/p8_sigma075/caustic.png",  "8-pass σ=0.75\n(2x passes, half sigma)"),
    (BASE / "passes_sweep/p16_sigma050/caustic.png", "16-pass σ=0.50\n(4x passes, third sigma)"),
]
out_passes = BASE / "passes_sweep/passes_comparison.jpg"
make_sheet(passes_panels, ncols=3, title="Inkbrush — Passes Sweep (no post-blur, nearest)", out_path=out_passes, dpi=120)

# ── 3D: Best-vs-baseline (3 panels) ───────────────────────────────────────────
# Best sigma: sigma=0.50 (crisp, small kernel)
# Best combined: sigma=0.50 + unsharp mask (to be determined; using sigma_050 + pp_unsharp sim)
# For now: baseline / best_sigma / best_passes
print("Building 3D: best-vs-baseline sheet...")
best_panels = [
    (BASE / "postprocess_sweep/gaussian_05_bilinear/caustic.png", "BASELINE\nσ=1.5 post=0.5 bilinear 4-pass"),
    (BASE / "sigma_sweep/sigma_050/caustic.png",                  "BEST SIGMA\nσ=0.50 no-post nearest 4-pass"),
    (BASE / "passes_sweep/p16_sigma050/caustic.png",              "BEST PASSES\nσ=0.50 no-post nearest 16-pass"),
]
out_best = BASE / "best_vs_baseline.jpg"
make_sheet(best_panels, ncols=3, title="Inkbrush — Baseline vs Best Results", out_path=out_best, dpi=130)

# ── Copy < 900KB JPEGs to handoff4 ─────────────────────────────────────────────
print("Writing handoff JPEGs...")
import shutil
from PIL import Image as PILImage

def save_handoff_jpeg(src, dst, max_kb=900):
    img = PILImage.open(src).convert('RGB')
    quality = 90
    while True:
        img.save(dst, 'JPEG', quality=quality)
        size_kb = dst.stat().st_size / 1024
        if size_kb <= max_kb or quality <= 40:
            print(f"  {dst.name}: {size_kb:.0f}KB (quality={quality})")
            break
        quality -= 10

save_handoff_jpeg(out_sigma,  HANDOFF / "O_sigma_sweep.jpg")
save_handoff_jpeg(out_pp,     HANDOFF / "P_postprocess_sweep.jpg")
save_handoff_jpeg(out_passes, HANDOFF / "Q_passes_sweep.jpg")
save_handoff_jpeg(out_best,   HANDOFF / "R_best_vs_baseline.jpg")

print("Done. All contact sheets built.")
