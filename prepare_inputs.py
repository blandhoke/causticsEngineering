#!/usr/bin/env python3
"""
prepare_inputs.py — Image preprocessing library for caustic lens solver experiments.

Each function accepts (input_path, output_path, **params) and returns the output path.
All inputs converted to grayscale float [0,1]. All outputs saved as uint8 PNG.

Usage:
  python3 prepare_inputs.py --technique NAME --in PATH --out PATH [--param VAL ...]
  python3 prepare_inputs.py --make-preview --inputs P1 P2 P3 P4 \\
                            --labels "L1" "L2" "L3" "L4" --out preview.png

Techniques:
  alpha_blend             --alpha FLOAT (0.0=pure Sobel, 1.0=pure photo)
  clahe                   --clip-limit FLOAT  --tile-size INT
  gradient_magnitude      --power FLOAT
  gaussian_blur_gradient  --blur-sigma FLOAT  --power FLOAT
  bandpass                --low-sigma FLOAT  --high-sigma FLOAT
  unsharp_mask            --sigma FLOAT  --amount FLOAT
  blur_only               --sigma FLOAT
"""

import argparse
import numpy as np
from pathlib import Path
from PIL import Image
from scipy.ndimage import gaussian_filter
from skimage.filters import sobel
from skimage.color import rgb2gray


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_gray(input_path: str) -> np.ndarray:
    """Load image as grayscale float32 [0,1]."""
    img = np.array(Image.open(input_path).convert('RGB'), dtype=np.float32) / 255.0
    return rgb2gray(img)


def _save(arr: np.ndarray, output_path: str, technique: str, gray_in: np.ndarray) -> str:
    """Clip to [0,1], save as uint8 PNG, print stats."""
    arr = np.clip(arr.astype(np.float32), 0.0, 1.0)
    out_img = Image.fromarray((arr * 255).astype(np.uint8))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out_img.save(output_path)
    print(f"{technique}")
    print(f"  Input:  mean={gray_in.mean():.3f}  std={gray_in.std():.3f}")
    print(f"  Output: mean={arr.mean():.3f}  std={arr.std():.3f}")
    print(f"  Saved → {output_path}")
    return output_path


# ── Preprocessing techniques ──────────────────────────────────────────────────

def alpha_blend(input_path: str, output_path: str, alpha: float = 0.5) -> str:
    """Blend: alpha × original_gray + (1-alpha) × sobel_edges.
    alpha=1.0 = pure photo, alpha=0.0 = pure Sobel edge map.
    Both components normalized to [0,1] before blending.
    """
    gray = _load_gray(input_path)
    edges = sobel(gray)
    if edges.max() > 0:
        edges = edges / edges.max()
    result = np.clip(alpha * gray + (1.0 - alpha) * edges, 0.0, 1.0)
    return _save(result, output_path, f"alpha_blend(alpha={alpha:.2f})", gray)


def clahe(input_path: str, output_path: str,
          clip_limit: float = 0.02, tile_size: int = 8) -> str:
    """CLAHE: Contrast Limited Adaptive Histogram Equalization.
    Boosts local contrast in a controlled way, preserving photographic structure.
    clip_limit: 0.01–0.08 typical. tile_size: kernel size in pixels.
    """
    from skimage.exposure import equalize_adapthist
    gray = _load_gray(input_path)
    result = equalize_adapthist(gray, kernel_size=tile_size, clip_limit=clip_limit)
    return _save(result.astype(np.float32), output_path,
                 f"clahe(clip={clip_limit}, tile={tile_size})", gray)


def gradient_magnitude(input_path: str, output_path: str, power: float = 1.0) -> str:
    """Raw gradient magnitude |∇I|^power.
    power=1.0 = linear, power=2.0 = emphasize strong gradients, power=0.5 = boost weak.
    Preserves spatial structure of gradient field, normalized to [0,1].
    """
    gray = _load_gray(input_path)
    dy, dx = np.gradient(gray)
    mag = np.sqrt(dx**2 + dy**2)
    if power != 1.0:
        mag = np.power(np.maximum(mag, 0.0), power)
    if mag.max() > 0:
        mag = mag / mag.max()
    return _save(mag, output_path, f"gradient_magnitude(power={power})", gray)


def gaussian_blur_gradient(input_path: str, output_path: str,
                           blur_sigma: float = 3.0, power: float = 1.0) -> str:
    """Gaussian blur then gradient magnitude.
    Broadens sharp edge transitions into softer ramps the solver can sample better.
    blur_sigma controls the pre-blur radius; power adjusts gradient emphasis.
    """
    gray = _load_gray(input_path)
    blurred = gaussian_filter(gray, sigma=blur_sigma)
    dy, dx = np.gradient(blurred)
    mag = np.sqrt(dx**2 + dy**2)
    if power != 1.0:
        mag = np.power(np.maximum(mag, 0.0), power)
    if mag.max() > 0:
        mag = mag / mag.max()
    return _save(mag, output_path,
                 f"gaussian_blur_gradient(blur_sigma={blur_sigma}, power={power})", gray)


def bandpass(input_path: str, output_path: str,
             low_sigma: float = 2.0, high_sigma: float = 32.0) -> str:
    """Bandpass filter: isolates mid-spatial frequencies encoding object shape.
    Formula: gaussian(img, low_sigma) - gaussian(img, high_sigma)
    low_sigma: slightly blurred (retains shape edges)
    high_sigma: strongly blurred (DC/broad strokes only)
    Difference = shape features at scales between low_sigma and high_sigma.
    Result shifted and normalized to [0,1].
    """
    gray = _load_gray(input_path)
    low_pass = gaussian_filter(gray, sigma=low_sigma)   # retains mid+high freq
    high_pass = gaussian_filter(gray, sigma=high_sigma) # retains only low freq
    result = low_pass - high_pass  # isolates mid-frequency content
    result = result - result.min()
    if result.max() > 0:
        result = result / result.max()
    return _save(result, output_path,
                 f"bandpass(low_sigma={low_sigma}, high_sigma={high_sigma})", gray)


def unsharp_mask(input_path: str, output_path: str,
                 sigma: float = 2.0, amount: float = 0.5) -> str:
    """Unsharp mask: preserves photographic structure while boosting gradient energy.
    result = clip(original + amount × (original - gaussian(original, sigma)), 0, 1)
    Amplifies existing gradients without destroying spatial structure.
    """
    gray = _load_gray(input_path)
    blurred = gaussian_filter(gray, sigma=sigma)
    result = np.clip(gray + amount * (gray - blurred), 0.0, 1.0)
    return _save(result, output_path, f"unsharp_mask(sigma={sigma}, amount={amount})", gray)


def blur_only(input_path: str, output_path: str, sigma: float = 3.0) -> str:
    """Gaussian blur only — no gradient computation.
    Tests whether a softened photographic input produces better solver geometry
    by removing competing fine-texture gradients while keeping object boundaries.
    """
    gray = _load_gray(input_path)
    result = np.clip(gaussian_filter(gray, sigma=sigma), 0.0, 1.0)
    return _save(result, output_path, f"blur_only(sigma={sigma})", gray)


# ── Technique registry ────────────────────────────────────────────────────────

TECHNIQUES = {
    'alpha_blend':            alpha_blend,
    'clahe':                  clahe,
    'gradient_magnitude':     gradient_magnitude,
    'gaussian_blur_gradient': gaussian_blur_gradient,
    'bandpass':               bandpass,
    'unsharp_mask':           unsharp_mask,
    'blur_only':              blur_only,
}


# ── 4-panel preview ───────────────────────────────────────────────────────────

def make_block_preview(image_paths: list, labels: list, output_path: str) -> str:
    """Generate a 2×2 panel preview of preprocessed images.
    image_paths: list of 4 PNG paths
    labels: list of 4 label strings
    output_path: destination PNG
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(10, 10), facecolor='black')
    fig.patch.set_facecolor('black')

    for ax, path, label in zip(axes.ravel(), image_paths, labels):
        if Path(path).exists():
            img = np.array(Image.open(path).convert('L'))
            ax.imshow(img, cmap='gray', vmin=0, vmax=255)
        else:
            ax.text(0.5, 0.5, f'MISSING:\n{path}',
                    ha='center', va='center', color='red', transform=ax.transAxes)
        ax.set_title(label, color='white', fontsize=10, pad=4)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor('black')
        for sp in ax.spines.values():
            sp.set_edgecolor('#444')

    plt.tight_layout(pad=0.5)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='black')
    plt.close()
    print(f"Preview saved → {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Image preprocessing for caustic lens solver experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--technique', choices=list(TECHNIQUES.keys()),
                        help='Preprocessing technique name')
    parser.add_argument('--in',  dest='input',  help='Input image path')
    parser.add_argument('--out', dest='output', required=True,
                        help='Output PNG path (or preview PNG for --make-preview)')
    parser.add_argument('--make-preview', action='store_true',
                        help='Generate 4-panel preview instead of preprocessing')
    parser.add_argument('--inputs',  nargs='+', help='--make-preview: 4 input PNG paths')
    parser.add_argument('--labels',  nargs='+', help='--make-preview: 4 panel labels')

    # alpha_blend
    parser.add_argument('--alpha',      type=float, default=0.5,
                        help='alpha_blend: blend ratio (0.0=pure Sobel, 1.0=pure photo)')
    # clahe
    parser.add_argument('--clip-limit', type=float, default=0.02,
                        help='clahe: clip limit (0.01–0.08 typical)')
    parser.add_argument('--tile-size',  type=int,   default=8,
                        help='clahe: grid tile size in pixels')
    # gradient_magnitude / gaussian_blur_gradient
    parser.add_argument('--power',      type=float, default=1.0,
                        help='gradient_magnitude / gaussian_blur_gradient: power exponent')
    parser.add_argument('--blur-sigma', type=float, default=3.0,
                        help='gaussian_blur_gradient: Gaussian sigma before gradient')
    # bandpass
    parser.add_argument('--low-sigma',  type=float, default=2.0,
                        help='bandpass: low-pass sigma (shape features)')
    parser.add_argument('--high-sigma', type=float, default=32.0,
                        help='bandpass: high-pass sigma (DC removal)')
    # unsharp_mask / blur_only
    parser.add_argument('--sigma',      type=float, default=2.0,
                        help='unsharp_mask: Gaussian sigma  |  blur_only: Gaussian sigma')
    parser.add_argument('--amount',     type=float, default=0.5,
                        help='unsharp_mask: sharpening amount')

    args = parser.parse_args()

    if args.make_preview:
        if not args.inputs or not args.labels:
            parser.error('--make-preview requires --inputs and --labels')
        make_block_preview(args.inputs, args.labels, args.output)
        return

    if not args.technique:
        parser.error('--technique is required unless --make-preview is set')
    if not args.input:
        parser.error('--in is required unless --make-preview is set')

    fn = TECHNIQUES[args.technique]

    if args.technique == 'alpha_blend':
        fn(args.input, args.output, alpha=args.alpha)
    elif args.technique == 'clahe':
        fn(args.input, args.output, clip_limit=args.clip_limit, tile_size=args.tile_size)
    elif args.technique == 'gradient_magnitude':
        fn(args.input, args.output, power=args.power)
    elif args.technique == 'gaussian_blur_gradient':
        fn(args.input, args.output, blur_sigma=args.blur_sigma, power=args.power)
    elif args.technique == 'bandpass':
        fn(args.input, args.output, low_sigma=args.low_sigma, high_sigma=args.high_sigma)
    elif args.technique == 'unsharp_mask':
        fn(args.input, args.output, sigma=args.sigma, amount=args.amount)
    elif args.technique == 'blur_only':
        fn(args.input, args.output, sigma=args.sigma)


if __name__ == '__main__':
    main()
