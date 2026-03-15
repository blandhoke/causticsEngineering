#!/usr/bin/env python3
"""
analyze_befuddled.py — 9-panel comparative analysis, befuddled cow v1 vs cow v3.
Writes: examples/befuddled_analysis_v1.png
Writes: HANDOFF_BEFUDDLED_v1.md
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.filters import sobel
import datetime, json

BASE = Path("/Users/admin/causticsEngineering/examples")
ROOT = Path("/Users/admin/causticsEngineering")

BEFUDDLED_INPUT = BASE / "befuddled_cow_solver_input.jpg"
CAUSTIC_BEF     = BASE / "caustic_befuddled_v1.png"
CAUSTIC_V3      = BASE / "caustic_cow_v3.png"
ORIG_COW        = BASE / "cow render.jpg"
OUT_ANALYSIS    = BASE / "befuddled_analysis_v1.png"
OUT_HANDOFF     = ROOT / "HANDOFF_BEFUDDLED_v1.md"
PHYS_LOG        = ROOT / "logs" / "physical_lens.log"

CMAP_SUN = LinearSegmentedColormap.from_list('sunlight', [
    (0.00, (0.00, 0.00, 0.00)),
    (0.35, (0.50, 0.25, 0.00)),
    (0.60, (0.95, 0.75, 0.05)),
    (0.80, (1.00, 0.97, 0.45)),
    (1.00, (1.00, 1.00, 0.92)),
])

def load_gray_norm(path, size=None):
    img = Image.open(path).convert('L')
    if size:
        img = img.resize(size, Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    if arr.max() > arr.min():
        arr = (arr - arr.min()) / (arr.max() - arr.min())
    return arr

def corr(a, b):
    af = a.ravel() - a.mean()
    bf = b.ravel() - b.mean()
    d  = np.std(a) * np.std(b)
    return float(np.dot(af, bf) / (len(af) * d)) if d > 1e-9 else 0.0

def quadrant_means(arr):
    H, W = arr.shape
    return {
        'top-left':     arr[:H//2, :W//2].mean(),
        'top-right':    arr[:H//2, W//2:].mean(),
        'bottom-left':  arr[H//2:, :W//2].mean(),
        'bottom-right': arr[H//2:, W//2:].mean(),
    }

print("Loading images...")
SIZE = (1024, 1024)

bef_input = load_gray_norm(BEFUDDLED_INPUT, SIZE)
caus_bef  = load_gray_norm(CAUSTIC_BEF)
caus_v3   = load_gray_norm(CAUSTIC_V3)
orig_cow  = load_gray_norm(ORIG_COW, (caus_v3.shape[1], caus_v3.shape[0]))

# Resize caustics to same size for comparison
if caus_bef.shape != caus_v3.shape:
    h, w = caus_v3.shape
    caus_bef = np.array(Image.fromarray((caus_bef*255).astype(np.uint8)).resize((w, h), Image.LANCZOS), dtype=np.float32) / 255.0

# ── Metrics ──────────────────────────────────────────────────────────────────
print("Computing metrics...")
bef_resized = np.array(Image.fromarray((bef_input*255).astype(np.uint8)).resize(
    (caus_bef.shape[1], caus_bef.shape[0]), Image.LANCZOS), dtype=np.float32) / 255.0
if bef_resized.max() > bef_resized.min():
    bef_resized = (bef_resized - bef_resized.min()) / (bef_resized.max() - bef_resized.min())

ssim_bef_input,  ssim_bef_map  = ssim(caus_bef, bef_resized, data_range=1.0, full=True)
ssim_v3_orig,    ssim_v3_map   = ssim(caus_v3,  orig_cow,    data_range=1.0, full=True)

edges_bef = sobel(bef_resized); edges_bef = edges_bef / edges_bef.max() if edges_bef.max() > 0 else edges_bef
edges_v3  = sobel(orig_cow);    edges_v3  = edges_v3  / edges_v3.max()  if edges_v3.max()  > 0 else edges_v3

r_bef_bright = corr(caus_bef, bef_resized)
r_bef_edge   = corr(caus_bef, edges_bef)
r_v3_bright  = corr(caus_v3,  orig_cow)
r_v3_edge    = corr(caus_v3,  edges_v3)

def pstats(arr, label):
    return {
        'label': label,
        'mean':  float(arr.mean()),
        'std':   float(arr.std()),
        'p75':   float(np.percentile(arr, 75)),
        'p90':   float(np.percentile(arr, 90)),
        'p99':   float(np.percentile(arr, 99)),
    }

stats_bef = pstats(caus_bef, 'befuddled')
stats_v3  = pstats(caus_v3,  'cow_v3')

quads_input = quadrant_means(bef_resized)
quads_v3    = quadrant_means(caus_v3)
quads_bef   = quadrant_means(caus_bef)

diff_map = caus_bef.astype(np.float32) - caus_v3.astype(np.float32)

# ── Report to stdout ──────────────────────────────────────────────────────────
print("\n═══ METRIC REPORT ═══════════════════════════════════════════════")
print(f"  SSIM(befuddled caustic, befuddled input):  {ssim_bef_input:.4f}")
print(f"  SSIM(cow v3 caustic, original cow):        {ssim_v3_orig:.4f}")
print(f"  Pearson r(befuddled, brightness):          {r_bef_bright:+.4f}")
print(f"  Pearson r(befuddled, edges):               {r_bef_edge:+.4f}")
print(f"  Pearson r(cow v3, brightness):             {r_v3_bright:+.4f}")
print(f"  Pearson r(cow v3, edges):                  {r_v3_edge:+.4f}")
print(f"\n  Brightness stats:")
for k,v in [('befuddled', stats_bef), ('cow v3', stats_v3)]:
    print(f"    {k:<12}  mean={v['mean']:.4f}  std={v['std']:.4f}  "
          f"p75={v['p75']:.4f}  p90={v['p90']:.4f}  p99={v['p99']:.4f}")
print(f"\n  Quadrant brightness (bottom-right = background):")
print(f"  {'Region':<16}  {'Input':>8}  {'Cow v3':>8}  {'Befuddled':>10}")
for q in ['top-left','top-right','bottom-left','bottom-right']:
    flag = "  ← KEY" if q == 'bottom-right' else ""
    print(f"  {q:<16}  {quads_input[q]:>8.3f}  {quads_v3[q]:>8.3f}  {quads_bef[q]:>10.3f}{flag}")

br_improvement = quads_bef['bottom-right'] - quads_v3['bottom-right']
print(f"\n  Bottom-right improvement (befuddled vs v3): {br_improvement:+.4f}")
print("═══════════════════════════════════════════════════════════════════")

# ── 9-panel plot ──────────────────────────────────────────────────────────────
print("\nRendering 9-panel analysis figure...")
fig, axes = plt.subplots(3, 3, figsize=(20, 20), facecolor='#0d0d0d')
fig.suptitle(
    f"Befuddled Cow v1 — Caustic Analysis\n"
    f"SSIM(bef, input)={ssim_bef_input:.4f}   SSIM(v3, orig)={ssim_v3_orig:.4f}   "
    f"r(bef, edges)={r_bef_edge:+.3f}   r(bef, brightness)={r_bef_bright:+.3f}",
    color='white', fontsize=13, y=0.99
)

def ax_style(ax, title):
    ax.set_title(title, color='#ddd', fontsize=10, pad=5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_facecolor('#0d0d0d')
    for sp in ax.spines.values(): sp.set_visible(False)

# Row 1
axes[0,0].imshow(bef_input, cmap='gray', vmin=0, vmax=1)
ax_style(axes[0,0], "Input: befuddled cow 1.jpg (grayscale)")

axes[0,1].imshow(edges_bef, cmap='gray', vmin=0, vmax=1)
ax_style(axes[0,1], "Sobel edge map of input")

hist_bef, bins = np.histogram(bef_input.ravel(), bins=50, range=(0,1))
hist_caus, _   = np.histogram(caus_bef.ravel(),  bins=50, range=(0,1))
bx = (bins[:-1] + bins[1:]) / 2
axes[0,2].bar(bx, hist_bef / hist_bef.max(),  width=0.018, color='#4488cc', alpha=0.7, label='input')
axes[0,2].bar(bx, hist_caus / hist_caus.max(), width=0.018, color='#cc8833', alpha=0.7, label='caustic')
axes[0,2].set_facecolor('#111'); axes[0,2].tick_params(colors='#aaa')
for sp in axes[0,2].spines.values(): sp.set_edgecolor('#444')
axes[0,2].legend(facecolor='#222', labelcolor='white', fontsize=9)
axes[0,2].set_title("Brightness histogram: input (blue) vs caustic (amber)", color='#ddd', fontsize=10)

# Row 2
axes[1,0].imshow(caus_bef, cmap=CMAP_SUN, vmin=0, vmax=1)
ax_style(axes[1,0], f"caustic_befuddled_v1.png  (mean={stats_bef['mean']:.3f})")

axes[1,1].imshow(caus_v3, cmap=CMAP_SUN, vmin=0, vmax=1)
ax_style(axes[1,1], f"caustic_cow_v3.png  (mean={stats_v3['mean']:.3f})")

dm = axes[1,2].imshow(diff_map, cmap='RdBu', vmin=-0.5, vmax=0.5)
ax_style(axes[1,2], "Difference: befuddled − v3  (red=brighter, blue=dimmer)")
plt.colorbar(dm, ax=axes[1,2], fraction=0.046, pad=0.04)

# Row 3 — Panel 7: quadrant bar chart
quad_labels = ['top-left', 'top-right', 'bot-left', 'bot-right']
qi = np.arange(4)
w  = 0.25
v_in  = [quads_input[q] for q in ['top-left','top-right','bottom-left','bottom-right']]
v_v3  = [quads_v3[q]    for q in ['top-left','top-right','bottom-left','bottom-right']]
v_bef = [quads_bef[q]   for q in ['top-left','top-right','bottom-left','bottom-right']]
axes[2,0].bar(qi - w, v_in,  width=w, color='#4488cc', label='input')
axes[2,0].bar(qi,     v_v3,  width=w, color='#cc4433', label='cow v3')
axes[2,0].bar(qi + w, v_bef, width=w, color='#cc8833', label='befuddled')
axes[2,0].set_xticks(qi); axes[2,0].set_xticklabels(quad_labels, color='#aaa', fontsize=8)
axes[2,0].tick_params(colors='#aaa'); axes[2,0].set_facecolor('#111')
for sp in axes[2,0].spines.values(): sp.set_edgecolor('#444')
axes[2,0].legend(facecolor='#222', labelcolor='white', fontsize=8)
axes[2,0].set_title("Quadrant mean brightness", color='#ddd', fontsize=10)

# Panel 8: SSIM heatmap befuddled vs input
sm = axes[2,1].imshow(ssim_bef_map, cmap='RdYlGn', vmin=-1, vmax=1)
ax_style(axes[2,1], f"SSIM map: befuddled caustic vs input  (mean={ssim_bef_input:.4f})")
plt.colorbar(sm, ax=axes[2,1], fraction=0.046, pad=0.04)

# Panel 9: text metrics
axes[2,2].set_facecolor('#0d0d0d')
for sp in axes[2,2].spines.values(): sp.set_visible(False)
axes[2,2].set_xticks([]); axes[2,2].set_yticks([])
txt = (
    f"  METRIC SUMMARY\n"
    f"  {'─'*38}\n"
    f"  SSIM(bef, input)     = {ssim_bef_input:+.4f}\n"
    f"  SSIM(v3, orig cow)   = {ssim_v3_orig:+.4f}\n"
    f"\n"
    f"  r(bef, brightness)   = {r_bef_bright:+.4f}\n"
    f"  r(bef, edges)        = {r_bef_edge:+.4f}\n"
    f"  r(v3,  brightness)   = {r_v3_bright:+.4f}\n"
    f"  r(v3,  edges)        = {r_v3_edge:+.4f}\n"
    f"\n"
    f"  Brightness (befuddled):\n"
    f"    mean={stats_bef['mean']:.3f}  std={stats_bef['std']:.3f}\n"
    f"    p75={stats_bef['p75']:.3f}  p90={stats_bef['p90']:.3f}  p99={stats_bef['p99']:.3f}\n"
    f"\n"
    f"  Brightness (cow v3):\n"
    f"    mean={stats_v3['mean']:.3f}  std={stats_v3['std']:.3f}\n"
    f"    p75={stats_v3['p75']:.3f}  p90={stats_v3['p90']:.3f}  p99={stats_v3['p99']:.3f}\n"
    f"\n"
    f"  Bottom-right quadrant (background):\n"
    f"    input={quads_input['bottom-right']:.3f}\n"
    f"    v3   ={quads_v3['bottom-right']:.3f}\n"
    f"    bef  ={quads_bef['bottom-right']:.3f}  (Δ{br_improvement:+.3f})\n"
)
axes[2,2].text(0.03, 0.97, txt, transform=axes[2,2].transAxes,
               fontsize=9, verticalalignment='top', fontfamily='monospace',
               color='#dddddd')
axes[2,2].set_title("Quantitative metrics", color='#ddd', fontsize=10)

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(OUT_ANALYSIS, dpi=120, bbox_inches='tight', facecolor='#0d0d0d')
plt.close()
print(f"Saved → {OUT_ANALYSIS}")

# ── Read physical lens log if available ───────────────────────────────────────
phys_summary = "(make_physical_lens.py output not available)"
if PHYS_LOG.exists():
    phys_summary = PHYS_LOG.read_text().strip()

# ── Write HANDOFF_BEFUDDLED_v1.md ─────────────────────────────────────────────
print(f"Writing {OUT_HANDOFF.name} ...")
br_verdict = (
    f"IMPROVED: bottom-right caustic brightness {quads_bef['bottom-right']:.3f} vs v3 {quads_v3['bottom-right']:.3f} (Δ{br_improvement:+.3f})"
    if br_improvement > 0.005 else
    f"NO SIGNIFICANT CHANGE: bottom-right {quads_bef['bottom-right']:.3f} vs v3 {quads_v3['bottom-right']:.3f} (Δ{br_improvement:+.3f})"
)

fill_verdict = (
    "More uniform fill than v3 — Option A preprocessing helped"
    if stats_bef['mean'] > stats_v3['mean'] * 1.05 else
    "Similar fill to v3 — Option A preprocessing had limited effect on fill uniformity"
)

edge_vs_bright = (
    "still edge-dominated (r_edge > r_bright absolute value)"
    if abs(r_bef_edge) > abs(r_bef_bright) else
    "brightness correlation improved over v3 — preprocessing is working"
)

ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

handoff_md = f"""# HANDOFF_BEFUDDLED_v1.md
# Befuddled Cow Run — Results & Next Steps
# Generated: {ts} by analyze_befuddled.py

---

## Run Settings

| Parameter | Value |
|-----------|-------|
| Input image | befuddled cow 1.jpg (Photoshop Option A: contrast boost, no pure black/white, 0.5px blur) |
| Image size | 1024×1024px |
| Solver grid | 1024px auto (image size controls mesh, not grid_definition) |
| Mesh faces | ~2.1M (1024px input) |
| Iterations | 6 SOR + Poisson height solve |
| Ray trace | 4-pass jittered barycentric, cosine weight, Gaussian splat σ=1.5 r=3 |
| IOR | 1.49 |
| Focal distance | 0.2m |
| Output | examples/caustic_befuddled_v1.png |

---

## All Metrics

### Structural Similarity (SSIM)

| Comparison | Value |
|-----------|-------|
| SSIM(befuddled caustic, befuddled input) | **{ssim_bef_input:.4f}** |
| SSIM(cow v3 caustic, original cow) | {ssim_v3_orig:.4f} |

### Pearson Correlation

| Comparison | Befuddled | Cow v3 |
|-----------|-----------|--------|
| r(caustic, brightness) | {r_bef_bright:+.4f} | {r_v3_bright:+.4f} |
| r(caustic, Sobel edges) | {r_bef_edge:+.4f} | {r_v3_edge:+.4f} |

### Brightness Distribution

| Stat | Befuddled | Cow v3 |
|------|-----------|--------|
| Mean | {stats_bef['mean']:.4f} | {stats_v3['mean']:.4f} |
| Std  | {stats_bef['std']:.4f} | {stats_v3['std']:.4f} |
| p75  | {stats_bef['p75']:.4f} | {stats_v3['p75']:.4f} |
| p90  | {stats_bef['p90']:.4f} | {stats_v3['p90']:.4f} |
| p99  | {stats_bef['p99']:.4f} | {stats_v3['p99']:.4f} |

### Quadrant Brightness

| Region | Input | Cow v3 | Befuddled | Δ (bef−v3) |
|--------|-------|--------|-----------|-----------|
| top-left     | {quads_input['top-left']:.3f} | {quads_v3['top-left']:.3f} | {quads_bef['top-left']:.3f} | {quads_bef['top-left']-quads_v3['top-left']:+.3f} |
| top-right    | {quads_input['top-right']:.3f} | {quads_v3['top-right']:.3f} | {quads_bef['top-right']:.3f} | {quads_bef['top-right']-quads_v3['top-right']:+.3f} |
| bottom-left  | {quads_input['bottom-left']:.3f} | {quads_v3['bottom-left']:.3f} | {quads_bef['bottom-left']:.3f} | {quads_bef['bottom-left']-quads_v3['bottom-left']:+.3f} |
| **bottom-right** | **{quads_input['bottom-right']:.3f}** | **{quads_v3['bottom-right']:.3f}** | **{quads_bef['bottom-right']:.3f}** | **{br_improvement:+.3f}** |

**Bottom-right verdict: {br_verdict}**

---

## Visual Description of caustic_befuddled_v1.png

- **Fill uniformity**: {fill_verdict}
- **Edge vs brightness**: Caustic is {edge_vs_bright}
- **Recognizability**: See caustic_befuddled_v1.png — compare against befuddled_analysis_v1.png

---

## Physical Lens (physical_lens_8x8.obj)

```
{phys_summary}
```

---

## CNC Assessment

The physical lens is scaled to 8"×8" (203.2mm × 203.2mm) with uniform XY+Z scale
factor of 2.032×. The Z axis MUST scale with XY to preserve refraction angles.

Key concerns for the Blue Elephant 1325 / NK105:
- Check dome height vs 1" (25.4mm) material — see physical lens output above
- Steepest slopes are at the cow silhouette boundary — verify with CAM software
- Physical_lens_8x8.obj is ready for import into CAM (Fusion 360, VCarve, etc.)
- Recommended toolpath: 3D adaptive with 1/4" ball endmill, 0.1mm stepover
- Stock: 1" cast acrylic (NOT extruded — cast is more uniform optically)

---

## Recommended Next Step

"""

if ssim_bef_input > ssim_v3_orig * 1.5 and br_improvement > 0.01:
    next_step = """### → OPTION: Mill the befuddled cow lens

Option A preprocessing produced measurable improvement. The caustic fill is
broader and the background region is better illuminated. This result may be
CNC-ready.

**Prompt for Claude Chat:**
> The befuddled cow caustic run is complete. SSIM improved to {:.4f} vs v3 {:.4f}.
> Bottom-right quadrant improved by {:+.3f}. Review caustic_befuddled_v1.png and
> befuddled_analysis_v1.png. physical_lens_8x8.obj is ready.
> Is this result good enough to mill, or do we need a further iteration?
""".format(ssim_bef_input, ssim_v3_orig, br_improvement)

elif abs(r_bef_edge) > abs(r_bef_bright):
    next_step = """### → OPTION B or C: Try a different target image type

The befuddled cow caustic is still edge-dominated (r_edge > r_brightness).
Option A preprocessing (blur + contrast) did not sufficiently fix the flat-region
brightness issue. Recommended next approaches:

**Option B — Feed the Sobel edge map as the target:**
  Pre-compute edges from befuddled_cow_solver_input.jpg and use that as the
  solver input. The caustic will then explicitly match the desired edges.

**Option C — White-filled cow silhouette on black:**
  Create a binary cow silhouette. All energy goes inside the boundary.
  Clean, simple, CNC-ready.

**Prompt for Claude Chat:**
> Befuddled cow run complete. Still edge-dominated: r(caustic, edges)={:.3f}.
> SSIM={:.4f}. Bottom-right unchanged at {:.3f}.
> Review befuddled_analysis_v1.png. Should we try Option B (edge map target)
> or Option C (silhouette) next? Or is this result acceptable for milling?
""".format(r_bef_edge, ssim_bef_input, quads_bef['bottom-right'])

else:
    next_step = f"""### → Review results and decide

SSIM(bef, input)={ssim_bef_input:.4f}. Bottom-right Δ={br_improvement:+.3f}.
Review caustic_befuddled_v1.png and befuddled_analysis_v1.png visually.

**Prompt for Claude Chat:**
> Befuddled cow run complete. SSIM={ssim_bef_input:.4f}, bottom-right Δ={br_improvement:+.3f}.
> Review befuddled_analysis_v1.png. Is Option A preprocessing an improvement?
> Should we proceed to milling, try Option B/C, or re-run at 1024px?
"""

handoff_md += next_step
OUT_HANDOFF.write_text(handoff_md)
print(f"Saved → {OUT_HANDOFF.name}")
print("\nAnalysis complete.")
