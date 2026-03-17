"""
generate_option_c_v2.py
Option C v2: threshold=0.38 on dark pixels, flood-fill from cow face center,
8px dilation + binary_fill_holes to close internal bright patches (blaze, nose).

The strategy:
  1. Dark mask: pixels < 0.38 = cow body candidates (dark fur)
  2. Flood-fill from seed (col=512, row=400) = cow face center
     → gets the connected dark region = cow body outline
  3. Dilate 8px → bridges thin gaps in the outline
  4. binary_fill_holes → fills interior bright patches (blaze, nose, etc.)
  5. Result: solid white cow on black background
"""
import numpy as np
from pathlib import Path
from PIL import Image
from scipy.ndimage import label, binary_dilation, binary_fill_holes, generate_binary_structure

BASE = Path("/Users/admin/causticsEngineering/examples")
HO   = Path("/Users/admin/causticsEngineering/claude_chat_handoff4")

SRC  = BASE / "befuddled_cow_solver_input.jpg"
OUT  = BASE / "cow2_option_c_v2.png"

img_pil = Image.open(SRC).convert('L')
img = np.array(img_pil, dtype=float) / 255.0
print(f"Image: {img.shape[1]}x{img.shape[0]}  min={img.min():.3f}  max={img.max():.3f}")
print(f"Note: cow body rows ~179-1023 (bright background rows 0-179 excluded from mask)")

# Strategy: restrict to rows 150+ to exclude bright background, use threshold=0.75
# to capture cow body + all bright interior patches (blaze, nose, chain).
# This works because the background at rows 150+ is part of the image with the cow,
# not the pure bright sky at the top — but the key is we're looking at the LARGEST
# connected component in this zone which is the cow body.
THRESHOLD   = 0.75
ROW_CUTOFF  = 150   # rows above this are bright sky background, excluded

# Step 1: Restricted mask
mask = np.zeros_like(img, dtype=bool)
mask[ROW_CUTOFF:, :] = img[ROW_CUTOFF:, :] < THRESHOLD
mask_pct = 100 * np.mean(mask)
print(f"Candidate pixels (rows {ROW_CUTOFF}+, value < {THRESHOLD}): {mask_pct:.1f}%")

# Step 2: Label connected components, take the LARGEST (= cow body + interior)
labeled, n_components = label(mask)
print(f"Connected components: {n_components}")

component_sizes = [(np.sum(labeled == i), i) for i in range(1, n_components + 1)]
component_sizes.sort(reverse=True)
cow_label = component_sizes[0][1]
cow_size  = component_sizes[0][0]
rows_c, cols_c = np.where(labeled == cow_label)
print(f"Largest component (cow): {cow_size:,} px ({100*cow_size/(img.shape[0]*img.shape[1]):.1f}%)  "
      f"centroid=({int(cols_c.mean())}, {int(rows_c.mean())})")

cow_component = labeled == cow_label

# Step 3: Dilate 8px to bridge remaining small gaps
struct = generate_binary_structure(2, 1)
cow_dilated = binary_dilation(cow_component, structure=struct, iterations=8)
dilated_pct = 100 * np.mean(cow_dilated)
print(f"After 8px dilation: {dilated_pct:.1f}%")

# Step 4: Fill any remaining enclosed holes
cow_filled = binary_fill_holes(cow_dilated)
filled_pct = 100 * np.mean(cow_filled)
print(f"After fill_holes: {filled_pct:.1f}%  (target: 70-75%)")

# Save
out_arr = (cow_filled * 255).astype(np.uint8)
Image.fromarray(out_arr).save(OUT)
print(f"\nSaved: {OUT.name}")

# Handoff resize
ho_img = Image.fromarray(out_arr).convert('RGB')
w, h = ho_img.size
scale = min(700/w, 700/h, 1.0)
if scale < 1.0:
    ho_img = ho_img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
ho_path = HO / "L3_option_c_v2.jpg"
ho_img.save(ho_path, quality=85)
sz = ho_path.stat().st_size // 1024
print(f"Handoff: {ho_path.name} ({ho_img.size[0]}x{ho_img.size[1]}, {sz}KB)")
