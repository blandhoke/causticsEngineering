#!/usr/bin/env python3
"""
prepare_visual_handoff.py
Resize caustic renders to max 700px longest edge, save as JPEG quality=85
to claude_chat_handoff4/. Prints name, dimensions, and file size for each.
"""

import os
from pathlib import Path
from PIL import Image

PROJECT = Path("/Users/admin/causticsEngineering")
OUT_DIR = PROJECT / "claude_chat_handoff4"
OUT_DIR.mkdir(exist_ok=True)

MAX_PX = 700
JPEG_QUALITY = 85
SIZE_WARN_KB = 900

SOURCES = [
    ("examples/caustic_cow_v3.png",              "A_ref_cow_v3.jpg",       True),
    ("examples/caustic_befuddled_v1.png",         "B_v1.jpg",               False),
    ("examples/caustic_befuddled_v4.png",         "C_v4.jpg",               False),
    ("examples/caustic_befuddled_v5.png",         "D_v5.jpg",               True),
    ("examples/caustic_befuddled_v5_flipfix.png", "D2_v5_flipfix.jpg",      False),
    ("examples/loss_it1.png",                     "E_loss_it1.jpg",         False),
    ("examples/loss_it3.png",                     "F_loss_it3.jpg",         False),
    ("examples/loss_it6.png",                     "G_loss_it6.jpg",         False),
    ("examples/befuddled_cow_solver_input.jpg",   "I_solver_input.jpg",     True),
    ("examples/cow2_option_b_edges.png",          "K_option_b_edges.jpg",   False),
    ("examples/cow2_option_c_silhouette.png",     "L_option_c_silhouette.jpg", False),
]

print(f"Output directory: {OUT_DIR}\n")
print(f"{'File':<30} {'Source dims':>14} {'Output dims':>14} {'Size KB':>9}")
print("-" * 72)

missing = []
written = []

for rel_src, out_name, required in SOURCES:
    src = PROJECT / rel_src
    if not src.exists():
        tag = "REQUIRED — missing" if required else "optional — skipped"
        print(f"  {'SKIP':<28} {tag:>14}  {rel_src}")
        missing.append(rel_src)
        continue

    img = Image.open(src)
    orig_w, orig_h = img.size
    src_dims = f"{orig_w}x{orig_h}"

    # Resize to max 700px longest edge
    scale = min(MAX_PX / orig_w, MAX_PX / orig_h, 1.0)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    if scale < 1.0:
        img = img.resize((new_w, new_h), Image.LANCZOS)
    out_dims = f"{new_w}x{new_h}"

    # Convert to RGB (handles RGBA/palette PNGs)
    if img.mode != "RGB":
        img = img.convert("RGB")

    out_path = OUT_DIR / out_name
    img.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    size_kb = out_path.stat().st_size / 1024
    flag = "  <-- OVERSIZED" if size_kb > SIZE_WARN_KB else ""
    print(f"  {out_name:<28} {src_dims:>14}  {out_dims:>14}  {size_kb:>7.1f} KB{flag}")
    written.append(out_name)

print()
print(f"Written: {len(written)}  |  Skipped/missing: {len(missing)}")
if missing:
    print("Missing sources:")
    for m in missing:
        print(f"  {m}")
