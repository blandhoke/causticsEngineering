"""
prepare_cow2_inputs.py
Generate Option B (Sobel edge map) and Option C (silhouette) inputs for Cow 2 solver.
Both outputs go to examples/ and claude_chat_handoff4/.
"""
import numpy as np
from pathlib import Path
from PIL import Image
from scipy.ndimage import sobel

BASE = Path("/Users/admin/causticsEngineering")
SRC  = BASE / "examples/befuddled_cow_solver_input.jpg"
OUT  = BASE / "examples"
HO   = BASE / "claude_chat_handoff4"
HO.mkdir(exist_ok=True)

img_pil = Image.open(SRC).convert('L')
img = np.array(img_pil, dtype=float) / 255.0

# ── Option B: Sobel edge map ──────────────────────────────────────────────────
sx = sobel(img, axis=0)
sy = sobel(img, axis=1)
edges = np.hypot(sx, sy)
edges = edges / edges.max()
edges[edges < 0.15] = 0.0

b_arr = (edges * 255).astype(np.uint8)
b_img = Image.fromarray(b_arr)
b_img.save(OUT / "cow2_option_b_edges.png")
print(f"Option B: max={b_arr.max()} nonzero={np.count_nonzero(b_arr):,} px")

# ── Option C: White silhouette on black via threshold ─────────────────────────
threshold = 128
c_arr = np.where(img > (threshold / 255.0), 255, 0).astype(np.uint8)
c_img = Image.fromarray(c_arr)
c_img.save(OUT / "cow2_option_c_silhouette.png")
print(f"Option C: white px={np.sum(c_arr > 0):,} ({100*np.mean(c_arr > 0):.1f}%)")

# ── Resize copies for Claude Chat handoff (< 700px longest edge) ──────────────
def resize_for_handoff(src_path, dst_path, max_px=700):
    im = Image.open(src_path)
    w, h = im.size
    scale = min(max_px / w, max_px / h, 1.0)
    if scale < 1.0:
        im = im.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    im.save(dst_path, quality=85)
    size_kb = dst_path.stat().st_size // 1024
    print(f"  Handoff: {dst_path.name} ({im.size[0]}x{im.size[1]}, {size_kb}KB)")

resize_for_handoff(OUT / "cow2_option_b_edges.png",     HO / "cow2_option_b_edges.jpg")
resize_for_handoff(OUT / "cow2_option_c_silhouette.png", HO / "cow2_option_c_silhouette.jpg")

print("\nDone. Upload to Claude Chat for visual approval before running solver.")
