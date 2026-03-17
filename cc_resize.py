#!/usr/bin/env python3
"""
cc_resize.py — Resize caustic PNGs for Claude Chat upload (always PNG, max 900px).

Usage:
  # Single file with explicit output path
  python3 cc_resize.py path/to/caustic.png --out handoff4/name.png

  # Multiple files, auto-named, to a directory
  python3 cc_resize.py file1.png file2.png --out handoff4/ --prefix tag_

  # All caustic.png files recursively under a directory
  python3 cc_resize.py --dir "Final cows/inkbrush/" --out handoff4/ --prefix inkbrush_

  # Slug + speed shorthand (grabs Final cows/<slug>/<speed>/caustic.png)
  python3 cc_resize.py --slug inkbrush --speed normal --out handoff4/
"""

import argparse
import sys
from pathlib import Path
from PIL import Image

MAX_PX  = 900
MAX_KB  = 900
PROJECT = Path(__file__).parent


def resize_one(src: Path, dst: Path):
    img = Image.open(src).convert('RGB')
    w, h = img.size
    if w > MAX_PX or h > MAX_PX:
        scale = MAX_PX / max(w, h)
        nw, nh = int(w * scale), int(h * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
    else:
        nw, nh = w, h
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, 'PNG')
    kb = dst.stat().st_size / 1024
    flag = ' *** OVER 900KB ***' if kb > MAX_KB else ''
    print(f"  {dst.name}: {nw}×{nh}px  {kb:.0f}KB{flag}")
    return dst


def auto_name(src: Path, out_dir: Path, prefix: str) -> Path:
    return out_dir / f"{prefix}{src.stem}.png"


def main():
    parser = argparse.ArgumentParser(description='Resize caustic PNGs for Claude Chat.')
    parser.add_argument('files',      nargs='*', help='Input PNG file(s)')
    parser.add_argument('--out',      required=True, help='Output file or directory')
    parser.add_argument('--prefix',   default='',    help='Prefix for auto-named output files')
    parser.add_argument('--dir',      default=None,  help='Recursively find caustic.png under this dir')
    parser.add_argument('--slug',     default=None,  help='Slug shorthand (Final cows/<slug>/<speed>/caustic.png)')
    parser.add_argument('--speed',    default='normal', help='Speed tier: fast/normal/prod')
    args = parser.parse_args()

    out_path = Path(args.out)
    sources = []

    # Collect sources
    if args.slug:
        src = PROJECT / 'Final cows' / args.slug / args.speed / 'caustic.png'
        if not src.exists():
            print(f"ERROR: {src} not found", file=sys.stderr)
            sys.exit(1)
        sources.append(src)

    if args.dir:
        base = Path(args.dir)
        found = sorted(base.rglob('caustic.png'))
        if not found:
            print(f"ERROR: no caustic.png found under {base}", file=sys.stderr)
            sys.exit(1)
        sources.extend(found)

    for f in args.files:
        p = Path(f)
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            sys.exit(1)
        sources.append(p)

    if not sources:
        parser.print_help()
        sys.exit(1)

    # Determine output mode
    single_explicit = (len(sources) == 1 and not out_path.is_dir()
                       and not str(args.out).endswith('/'))

    print(f"cc_resize: {len(sources)} file(s) → {out_path}  (max {MAX_PX}px, PNG)")
    for src in sources:
        if single_explicit:
            dst = out_path
            dst.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_path.mkdir(parents=True, exist_ok=True)
            # Build a descriptive name from path components
            parts = src.parts
            # e.g. Final cows/inkbrush/sigma_sweep/sigma_025/caustic.png
            # → prefix + slug_speed_sigma_025.png
            try:
                fc_idx = next(i for i, p in enumerate(parts) if 'Final cows' in p or 'final cows' in p.lower())
                rel_parts = parts[fc_idx+1:]  # e.g. inkbrush/sigma_sweep/sigma_025/caustic.png
                name_parts = [p for p in rel_parts[:-1]]  # drop 'caustic.png'
                stem = '_'.join(name_parts)
            except StopIteration:
                stem = '_'.join(src.parts[-3:-1])
            dst = out_path / f"{args.prefix}{stem}.png"
        resize_one(src, dst)


if __name__ == '__main__':
    main()
