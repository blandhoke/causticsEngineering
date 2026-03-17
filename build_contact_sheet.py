"""
build_contact_sheet.py
5 rows (images) x 2 columns (fast | normal), black bg, white labels, amber accents.
Reads timing from run.log TIMING: line.
"""
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from PIL import Image

PROJECT = Path("/Users/admin/causticsEngineering")
SLUGS   = ["banknote", "charcol", "inkbrush", "nikon", "woodblock"]
SPEEDS  = ["fast", "normal"]
AMBER   = "#FFC040"

def read_timing(log_path):
    try:
        for line in log_path.read_text().splitlines():
            if line.startswith("TIMING:"):
                m = re.search(r"Total=(\d+)s", line)
                if m: return int(m.group(1))
    except Exception:
        pass
    return None

def read_sigma(log_path):
    try:
        for line in log_path.read_text().splitlines():
            m = re.search(r"sigma=([\d.]+)", line)
            if m: return float(m.group(1))
    except Exception:
        pass
    return None

def read_faces(log_path):
    try:
        for line in log_path.read_text().splitlines():
            m = re.search(r"top_faces=([\d,]+)", line)
            if m: return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return None

# Build figure: 5 rows x 2 cols
fig = plt.figure(figsize=(14, 18), facecolor='black')
gs  = gridspec.GridSpec(5, 2, figure=fig, hspace=0.06, wspace=0.04,
                        left=0.02, right=0.98, top=0.95, bottom=0.02)

for row, slug in enumerate(SLUGS):
    for col, speed in enumerate(SPEEDS):
        ax = fig.add_subplot(gs[row, col])
        ax.set_facecolor('black')
        for spine in ax.spines.values():
            spine.set_edgecolor('#333')

        img_path = PROJECT / "Final cows" / slug / speed / "caustic.png"
        log_path = PROJECT / "Final cows" / slug / speed / "run.log"

        if img_path.exists():
            img = np.array(Image.open(img_path).convert('RGB'))
            ax.imshow(img, aspect='equal')
        else:
            ax.text(0.5, 0.5, 'MISSING', color='red',
                    ha='center', va='center', transform=ax.transAxes)

        total = read_timing(log_path)
        sigma = read_sigma(log_path)
        faces = read_faces(log_path)
        time_str  = f"{total}s" if total else "?"
        sigma_str = f"σ={sigma:.2f}" if sigma else ""
        faces_str = f"{faces//1000}k faces" if faces else ""

        title = f"{slug}  [{speed}]  {time_str}"
        sub   = "  ".join(filter(None, [sigma_str, faces_str]))
        ax.set_title(title, color=AMBER, fontsize=9, fontweight='bold', pad=3)
        if sub:
            ax.text(0.5, -0.02, sub, color='#888', fontsize=7,
                    ha='center', va='top', transform=ax.transAxes)
        ax.axis('off')

fig.suptitle("Final Cows — Caustic Batch Results  |  FAST (256px) vs NORMAL (512px)",
             color='white', fontsize=13, fontweight='bold', y=0.975)

out_full = PROJECT / "Final cows" / "comparison_contact_sheet.png"
fig.savefig(out_full, dpi=150, bbox_inches='tight', facecolor='black')
plt.close()
print(f"Full-res contact sheet: {out_full}")

# Handoff JPEG < 900KB
from PIL import Image as PILImage
sheet = PILImage.open(out_full).convert('RGB')
w, h = sheet.size
# try quality 85, reduce if > 900KB
for q in [85, 75, 65]:
    out_ho = PROJECT / "claude_chat_handoff4" / "N_contact_sheet.jpg"
    sheet.save(out_ho, quality=q)
    sz = out_ho.stat().st_size // 1024
    if sz <= 900:
        print(f"Handoff JPEG (q={q}): {w}x{h} → {sz}KB")
        break
    print(f"  q={q}: {sz}KB, reducing...")
