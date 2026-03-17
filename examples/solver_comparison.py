#!/usr/bin/env python3
"""
solver_comparison.py — 4-panel caustic comparison figure.

Panels: [Reference (Python ray tracer) | Julia SOR | Solver A OTMap | Solver B Poisson]
Each 512×512, labeled with solver name and SSIM + edge-r scores.
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).parent.parent

panels = [
    {
        'path': ROOT / 'luxcore_test/inkbrush_caustic_normal.png',
        'label': 'Reference\n(Python ray tracer)',
        'metrics_path': None,
    },
    {
        'path': ROOT / 'examples/baseline_julia_caustic.png',
        'label': 'Julia SOR\n(our solver)',
        'metrics_path': ROOT / 'examples/metrics_baseline.json',
    },
    {
        'path': ROOT / 'examples/solver_A_fast_ot_caustic.png',
        'label': 'Solver A\nfast_caustic_design OTMap\n(focal 153mm, not 762mm)',
        'metrics_path': ROOT / 'examples/metrics_solver_A.json',
    },
    {
        'path': ROOT / 'examples/solver_B_schwartzburg_caustic.png',
        'label': 'Solver B\nPoisson caustic design\n(128px fallback)',
        'metrics_path': ROOT / 'examples/metrics_solver_B.json',
    },
]

fig, axes = plt.subplots(1, 4, figsize=(20, 6), facecolor='black')
fig.patch.set_facecolor('black')

for ax, panel in zip(axes, panels):
    img = Image.open(panel['path']).convert('RGB').resize((512, 512), Image.LANCZOS)
    ax.imshow(np.array(img))
    ax.set_facecolor('black')
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor('#555')

    # Build subtitle
    if panel['metrics_path'] and Path(panel['metrics_path']).exists():
        m = json.loads(Path(panel['metrics_path']).read_text())
        sub = f"SSIM={m['ssim']:.3f}  r={m['pearson_r_edges']:.3f}"
    else:
        sub = ""

    title = panel['label']
    if sub:
        title += f"\n{sub}"

    ax.set_title(title, color='#ddd', fontsize=9, pad=6)

fig.suptitle(
    'Three-Solver Caustic Comparison — inkbrush target  |  Mitsuba ptracer 1024spp\n'
    'Primary metric: Pearson r (edge correlation vs reference)',
    color='#ccc', fontsize=11, y=1.01
)

plt.tight_layout(pad=0.5)
out = ROOT / 'examples/solver_comparison.png'
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='black')
plt.close()
print(f"Saved → {out}")
