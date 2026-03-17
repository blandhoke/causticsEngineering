"""
generate_corrected_inputs.py
Fix Option C (invert + morphological fill) and Option B (stronger threshold + blur).
"""
import numpy as np
from pathlib import Path
from PIL import Image
from scipy.ndimage import binary_fill_holes, gaussian_filter

BASE = Path("/Users/admin/causticsEngineering/examples")
HO   = Path("/Users/admin/causticsEngineering/claude_chat_handoff4")

# ── Option C corrected: invert + fill ────────────────────────────────────────
c_src = BASE / "cow2_option_c_silhouette.png"
c_arr = np.array(Image.open(c_src).convert('L'))

# Current state: white background, black cow — INVERTED from what solver needs
# Step 1: Invert → black background, white cow (but fragmented interior)
c_inv = 255 - c_arr

# Step 2: Binary fill — fill holes in the white cow shape
# Work in binary domain
c_bin = c_inv > 128
c_filled = binary_fill_holes(c_bin)

# Step 3: Small morphological dilation to close remaining gaps (3-pixel radius)
from scipy.ndimage import binary_dilation, generate_binary_structure
struct = generate_binary_structure(2, 1)
# dilate 3 times to bridge small gaps, then fill again
c_dilated = binary_dilation(c_filled, structure=struct, iterations=3)
c_filled2  = binary_fill_holes(c_dilated)

c_out = (c_filled2 * 255).astype(np.uint8)
Image.fromarray(c_out).save(BASE / "cow2_option_c_corrected.png")

white_pct = 100 * np.mean(c_filled2)
print(f"Option C corrected: white={white_pct:.1f}%  (was inverted+fragmented)")
print(f"  Saved: cow2_option_c_corrected.png")

# Handoff copy
ho_img = Image.fromarray(c_out)
w, h = ho_img.size
scale = min(700/w, 700/h, 1.0)
if scale < 1.0:
    ho_img = ho_img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
ho_img.save(HO / "L2_option_c_corrected.jpg", quality=85)
sz = (HO / "L2_option_c_corrected.jpg").stat().st_size // 1024
print(f"  Handoff: L2_option_c_corrected.jpg ({ho_img.size[0]}x{ho_img.size[1]}, {sz}KB)")

# ── Option B corrected: stronger threshold + blur ─────────────────────────────
b_src = BASE / "cow2_option_b_edges.png"
b_arr = np.array(Image.open(b_src).convert('L'), dtype=float) / 255.0

# Keep only top 25% strongest edges
threshold = 0.25
b_thresh = np.where(b_arr >= threshold, b_arr, 0.0)

# 1.5px Gaussian blur to merge micro-edges
b_blurred = gaussian_filter(b_thresh, sigma=1.5)

# Re-normalize
if b_blurred.max() > 0:
    b_blurred /= b_blurred.max()

b_out = (b_blurred * 255).astype(np.uint8)
Image.fromarray(b_out).save(BASE / "cow2_option_b_corrected.png")

nonzero_pct = 100 * np.mean(b_out > 0)
print(f"\nOption B corrected: nonzero={nonzero_pct:.1f}%  (threshold=25%, blur=1.5px)")
print(f"  Saved: cow2_option_b_corrected.png")

# Handoff copy
ho_b = Image.fromarray(b_out)
w, h = ho_b.size
scale = min(700/w, 700/h, 1.0)
if scale < 1.0:
    ho_b = ho_b.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
ho_b.save(HO / "K2_option_b_corrected.jpg", quality=85)
sz = (HO / "K2_option_b_corrected.jpg").stat().st_size // 1024
print(f"  Handoff: K2_option_b_corrected.jpg ({ho_b.size[0]}x{ho_b.size[1]}, {sz}KB)")

print("\nDone.")
