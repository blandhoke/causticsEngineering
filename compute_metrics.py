#!/usr/bin/env python3
"""
compute_metrics.py — Image quality metrics for caustic comparison.

Usage:
  python3 compute_metrics.py \
    --caustic PATH --reference PATH --label STRING --out PATH

Outputs a JSON file with SSIM, Pearson r (edge correlation), pct_black,
max_pixel_raw, and mean_brightness. Both images resized to 512x512 first.
"""

import argparse
import json
import numpy as np
from pathlib import Path
from PIL import Image

try:
    from skimage.metrics import structural_similarity as ssim
    from skimage.filters import sobel
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                           'scikit-image', '--break-system-packages'])
    from skimage.metrics import structural_similarity as ssim
    from skimage.filters import sobel


def load_gray(path: str, size: int = 512) -> np.ndarray:
    """Load image, convert to grayscale float [0,1], resize to size×size."""
    img = Image.open(path).convert('L').resize((size, size), Image.LANCZOS)
    return np.array(img, dtype=np.float32) / 255.0


def pearson_r(a: np.ndarray, b: np.ndarray) -> float:
    a_flat = a.ravel() - a.mean()
    b_flat = b.ravel() - b.mean()
    denom = np.sqrt((a_flat**2).sum() * (b_flat**2).sum())
    if denom == 0:
        return 0.0
    return float(np.dot(a_flat, b_flat) / denom)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--caustic',   required=True)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--label',     required=True)
    parser.add_argument('--out',       required=True)
    args = parser.parse_args()

    caustic = load_gray(args.caustic)
    ref     = load_gray(args.reference)

    # Max raw pixel (before normalization)
    raw = np.array(Image.open(args.caustic).convert('L'), dtype=np.float32)
    max_pixel_raw = float(raw.max())

    # Normalize caustic to [0,1] for consistent metrics
    c_norm = caustic.copy()
    if c_norm.max() > 0:
        c_norm /= c_norm.max()

    # SSIM
    ssim_val = float(ssim(c_norm, ref, data_range=1.0))

    # Edge correlation: Sobel filter both images, then Pearson r
    c_edges = sobel(c_norm)
    r_edges = sobel(ref)
    r_val   = pearson_r(c_edges, r_edges)

    # % black pixels (< 0.05) in normalized caustic
    pct_black = float(100.0 * (c_norm < 0.05).sum() / c_norm.size)

    # Mean brightness of normalized caustic
    mean_brightness = float(c_norm.mean())

    result = {
        'label':           args.label,
        'ssim':            ssim_val,
        'pearson_r_edges': r_val,
        'pct_black':       pct_black,
        'max_pixel_raw':   max_pixel_raw,
        'mean_brightness': mean_brightness,
    }

    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"Metrics [{args.label}]")
    for k, v in result.items():
        if k != 'label':
            print(f"  {k:<22} {v:.4f}")
    print(f"Saved → {args.out}")


if __name__ == '__main__':
    main()
