"""verify_final_cows.py — Check all 5 Final Cows inputs before batch run."""
import numpy as np
from pathlib import Path
from PIL import Image

PROJECT = Path("/Users/admin/causticsEngineering")
IMAGES = [
    PROJECT / "Final cows/ banknote.png",
    PROJECT / "Final cows/charcol.png",
    PROJECT / "Final cows/inkbrush.png",
    PROJECT / "Final cows/Nikon.png",
    PROJECT / "Final cows/woodblock.png",
]

print("=== Final Cows Input Verification ===\n")
all_ok = True
for path in IMAGES:
    slug = path.name.strip().rsplit('.', 1)[0].replace(' ', '_').lower()
    try:
        im = Image.open(path)
        arr = np.array(im.convert('L'), dtype=float) / 255.0
        nonzero_pct = 100 * np.mean(arr > 0.05)
        bright_pct  = 100 * np.mean(arr > 0.5)
        w, h = im.size
        flags = []
        if nonzero_pct < 5:  flags.append("WARN: nearly all black")
        if bright_pct > 95:  flags.append("WARN: nearly all white")
        flag_str = "  ← " + ", ".join(flags) if flags else ""
        print(f"  {slug:12s}  {w}x{h}  {im.mode}  nonzero={nonzero_pct:.1f}%  bright={bright_pct:.1f}%{flag_str}")
    except Exception as e:
        print(f"  {slug:12s}  ERROR: {e}")
        all_ok = False

print(f"\nAll readable: {'YES' if all_ok else 'NO — fix before running'}")
