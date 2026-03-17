#!/usr/bin/env python3
"""
combine_quads_normal.py — Combine 4 NORMAL (512px) quad OBJ meshes into one 8"x8" block.

Identical to combine_quads.py but intended for NORMAL-resolution meshes (~526k faces each,
~2.1M faces combined). Use this for production CAM blocks after HYPER screening confirms
which preprocessing technique wins.

Each quad is scaled to exactly 4"x4" (0.1016m). Z scales proportionally to preserve
surface normals and refraction angles. Dome < 25.4mm per quad required for 1" stock.

Usage:
  python3 combine_quads_normal.py \\
    --q1 PATH --q2 PATH --q3 PATH --q4 PATH \\
    --out PATH \\
    --label "Block name"

Layout (viewed from above):
  Q1 (top-left)     Q2 (top-right)
  Q3 (bottom-left)  Q4 (bottom-right)
"""

# This script uses identical logic to combine_quads.py.
# All functionality is imported from there.

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from combine_quads import combine, main

if __name__ == '__main__':
    main()
