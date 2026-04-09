# Claude Code Prompt — Auto-Resize Tool for Claude Chat
# Date: 2026-03-16
# From: Claude Chat
# Purpose: Build a reusable tool that prepares any render for Claude Chat
#          to read via MCP — PNG only, no JPEG, no quality loss.

---

## CRITICAL FINDING FROM CLAUDE CHAT

The current prepare_visual_handoff.py saves handoff images as JPEG quality=85.
This introduces compression artifacts on top of the existing caustic blur,
making it impossible for Claude Chat to assess true render quality.

RULE GOING FORWARD: All handoff images for Claude Chat must be saved as PNG.
At 700px max dimension, caustic PNGs are 150-400KB — well under the 1MB MCP limit.
JPEG is never needed and always degrades caustic analysis.

---

## TASK 1 — Write cc_resize.py (the permanent Claude Chat prep tool)

A general-purpose utility that takes any image or directory of images and
produces MCP-readable PNGs. This replaces ad-hoc resize logic in all
handoff scripts.

Save to: /Users/admin/causticsEngineering/cc_resize.py

```python
#!/usr/bin/env python3
"""
cc_resize.py — Prepare images for Claude Chat MCP reading.

Resizes to max 900px longest edge, saves as PNG (never JPEG).
At 900px, caustic PNGs are 200-500KB — always under the 1MB MCP limit.
JPEG is explicitly refused — it introduces compression artifacts on caustics.

Usage:
  # Single file:
  python3 cc_resize.py path/to/caustic.png --out claude_chat_handoff4/name.png

  # Directory — all PNGs/JPGs in a folder:
  python3 cc_resize.py Final\ cows/inkbrush/sigma_sweep/ --out claude_chat_handoff4/ --prefix sigma_

  # Specific files with auto-naming:
  python3 cc_resize.py file1.png file2.png --out claude_chat_handoff4/

  # After any pipeline run — grab all caustic.png files from a slug:
  python3 cc_resize.py --slug inkbrush --speed normal --out claude_chat_handoff4/
"""

import argparse
import sys
from pathlib import Path
from PIL import Image

MAX_PX   = 900   # longest edge — always under 1MB as PNG
OUT_DIR  = Path("/Users/admin/causticsEngineering/claude_chat_handoff4")
PROJECT  = Path("/Users/admin/causticsEngineering")

def resize_for_cc(src: Path, dst: Path):
    """Resize src image to MAX_PX longest edge, save as PNG. Never JPEG."""
    dst = dst.with_suffix('.png')   # force PNG regardless of input extension
    img = Image.open(src)
    img.thumbnail((MAX_PX, MAX_PX), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, 'PNG', optimize=True)
    size_kb = dst.stat().st_size // 1024
    print(f"  {src.name} → {dst.name}  ({img.size[0]}×{img.size[1]}px, {size_kb}KB)")
    if size_kb > 900:
        print(f"  WARNING: {dst.name} is {size_kb}KB — may exceed MCP 1MB limit")
    return dst

parser = argparse.ArgumentParser()
parser.add_argument('sources', nargs='*', help='Image files or directories')
parser.add_argument('--out',    default=str(OUT_DIR), help='Output directory or file path')
parser.add_argument('--prefix', default='',           help='Prefix for auto-named outputs')
parser.add_argument('--slug',   default='',           help='Final cows slug (e.g. inkbrush)')
parser.add_argument('--speed',  default='normal',     help='Pipeline speed (fast/normal)')
parser.add_argument('--all-sweeps', action='store_true',
                    help='Grab all caustic.png from all sweep subdirs for a slug')
args = parser.parse_args()

out_path = Path(args.out)
sources  = [Path(s) for s in args.sources]

# --slug mode: grab caustic.png from slug/speed/ and all sweep subdirs
if args.slug:
    base = PROJECT / 'Final cows' / args.slug
    # Main speed result
    main = base / args.speed / 'caustic.png'
    if main.exists():
        sources.append(main)
    # All sweep subdirs if --all-sweeps
    if args.all_sweeps:
        for sweep_dir in sorted(base.glob('*/*/caustic.png')):
            sources.append(sweep_dir)

# Expand directories to their image files
expanded = []
for s in sources:
    if s.is_dir():
        for ext in ('*.png', '*.jpg', '*.jpeg'):
            expanded.extend(sorted(s.glob(ext)))
    else:
        expanded.append(s)

if not expanded:
    print("No images found. Check paths.")
    sys.exit(1)

print(f"Resizing {len(expanded)} image(s) → {out_path}/")
out_path.mkdir(parents=True, exist_ok=True)

results = []
for src in expanded:
    # Auto-name: prefix + parent_dir + filename stem
    if out_path.is_dir():
        stem = f"{args.prefix}{src.parent.name}_{src.stem}" if args.prefix else src.stem
        dst  = out_path / f"{stem}.png"
    else:
        dst = out_path  # explicit output path

    result = resize_for_cc(src, dst)
    results.append(result)

print(f"\nDone. {len(results)} files in {out_path}/")
print("All PNG, no JPEG. Safe for Claude Chat MCP reading.")
```

---

## TASK 2 — Update prepare_visual_handoff.py

Change all JPEG saves to PNG. Find every line like:
  img.save(out, 'JPEG', quality=85)
  or
  plt.savefig(out, ...) where out ends in .jpg

Replace with PNG equivalents. Update all output filenames from .jpg to .png
in that script. This is a simple find-and-replace — auto-accept.

---

## TASK 3 — Add cc_resize as a post-run hook in run_cow_pipeline.sh

After simulate_batch.py completes, automatically resize the caustic.png
for Claude Chat:

  # At end of run_cow_pipeline.sh, after "=== DONE ===" line:
  python3 "${PROJECT}/cc_resize.py" \
    "${OUT_DIR}/caustic.png" \
    --out "${PROJECT}/claude_chat_handoff4/" \
    --prefix "${SLUG}_${SPEED}_"
  echo "  Claude Chat copy: claude_chat_handoff4/${SLUG}_${SPEED}_caustic.png"

This means every pipeline run auto-deposits a Claude Chat-readable PNG
in the handoff folder. No manual step needed.

---

## TASK 4 — Regenerate all existing handoff images as PNG

Run cc_resize.py to replace all existing .jpg files in claude_chat_handoff4/
with proper PNG versions:

  cd /Users/admin/causticsEngineering
  # Regenerate sweep results from source PNGs
  python3 cc_resize.py \
    "Final cows/inkbrush/sigma_sweep/sigma_025/caustic.png" \
    "Final cows/inkbrush/sigma_sweep/sigma_050/caustic.png" \
    "Final cows/inkbrush/sigma_sweep/sigma_075/caustic.png" \
    "Final cows/inkbrush/sigma_sweep/sigma_100/caustic.png" \
    "Final cows/inkbrush/sigma_sweep/sigma_150/caustic.png" \
    --out claude_chat_handoff4/ --prefix "sigma_"

  python3 cc_resize.py \
    "Final cows/inkbrush/postprocess_sweep/no_postblur_nearest/caustic.png" \
    "Final cows/inkbrush/postprocess_sweep/gaussian_03_nearest/caustic.png" \
    "Final cows/inkbrush/postprocess_sweep/gaussian_05_nearest/caustic.png" \
    "Final cows/inkbrush/postprocess_sweep/gaussian_05_bilinear/caustic.png" \
    "Final cows/inkbrush/postprocess_sweep/unsharp_nearest/caustic.png" \
    "Final cows/inkbrush/postprocess_sweep/gamma070_nearest/caustic.png" \
    --out claude_chat_handoff4/ --prefix "post_"

  python3 cc_resize.py \
    "Final cows/inkbrush/passes_sweep/passes_8_sigma_075/caustic.png" \
    "Final cows/inkbrush/passes_sweep/passes_16_sigma_050/caustic.png" \
    --out claude_chat_handoff4/ --prefix "passes_"

  # Also regenerate the 5 normal results
  for slug in banknote charcol inkbrush nikon woodblock; do
    python3 cc_resize.py \
      "Final cows/${slug}/normal/caustic.png" \
      --out claude_chat_handoff4/ --prefix "${slug}_normal_"
  done

After running, list all files in claude_chat_handoff4/ with sizes and
confirm all are PNG and all are under 900KB.

---

## EXECUTION ORDER

  1. Write cc_resize.py (Task 1)
  2. Update prepare_visual_handoff.py (Task 2)
  3. Update run_cow_pipeline.sh (Task 3)
  4. Run Task 4 regeneration (auto-accept)
  5. Report: list of new PNG files in handoff4/ with sizes
  6. git commit "cc_resize tool: PNG-only handoff, no JPEG degradation"

## NO CONFIRMATION NEEDED FOR ANYTHING IN THIS PROMPT.
