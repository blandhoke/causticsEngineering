# Crispness Research — Ready for Claude Chat Review
# Date: 2026-03-16
# Status: ALL SWEEPS COMPLETE

---

## Images Ready for Upload (in handoff4/)

| File | Contents | Size |
|------|----------|------|
| O_sigma_sweep.jpg | Sigma: 0.25 / 0.50 / 0.75 / 1.00 / 1.50 (5 panels) | ~173KB |
| P_postprocess_sweep.jpg | 7 post-process variants: baseline/no-blur/gaussian-03/gaussian-05/unsharp/gamma-065/gamma-070 | ~236KB |
| Q_passes_sweep.jpg | 4-pass baseline / 8-pass σ=0.75 / 16-pass σ=0.50 (3 panels) | ~137KB |
| R_best_vs_baseline.jpg | Baseline vs gamma=0.65 vs gamma=0.70 (4 panels) | ~162KB |
| S_nikon_best_params.jpg | Nikon: baseline vs σ=0.50 16-pass (2 panels) | ~116KB |
| T_cmap_sigma_comparison.jpg | sunlight vs 'hot' colormap + σ=0.50 vs σ=0.75 (4 panels) | ~170KB |

---

## Key Finding Per Sweep (one sentence each)

**O — Sigma Sweep:**
Smaller sigma (0.25–0.50) gives sharper caustic lines but at the cost of visible grid
artifact; sigma=0.75 is the predicted sweet spot where artifact becomes invisible at 526k faces.

**P — Post-Process Sweep:**
Removing the gaussian_filter(0.5) post-blur and switching gamma from 0.5 to 0.70 produces
the darkest background and crispest lines; bilinear interpolation adds measurable upscale blur.

**Q — Passes Sweep:**
16-pass sigma=0.50 is theoretically the crispest but diminishing returns vs the baseline;
the mesh resolution (512px) is the hard limit on detail, not sampling density.

**R — Best vs Baseline:**
Side-by-side shows that sigma=0.50 + gamma=0.70 + no-post-blur + nearest is meaningfully
sharper and higher-contrast than the current baseline.

**S — Nikon:**
Nikon shows similar improvements with the best params; worth confirming that sigma=0.50
doesn't expose grid artifact in the denser-line Nikon image.

---

## Questions for Claude Chat

**Q1 — Sigma Sweep (O_sigma_sweep.jpg):**
Which sigma panel looks sharpest WITHOUT visible mesh-grid artifact?
Options: 0.25 (ultra), 0.50 (very crisp), 0.75 (crisp), 1.00 (moderate), 1.50 (current).
Grid artifact looks like a regular dot or stripe pattern in the background of the caustic.

**Q2 — Gamma (R_best_vs_baseline.jpg):**
Compare 4 panels: baseline (γ=0.5, post-blur, bilinear) / no-blur nearest γ=0.5 / γ=0.65 / γ=0.70.
Subagents predict γ=0.70 makes the background genuinely black vs amber, increasing apparent contrast.
Does this look better, or does it lose too much shadow detail in the caustic halos?
Preferred gamma: 0.50 / 0.65 / 0.70 ?

**Q3 — Passes (Q_passes_sweep.jpg):**
Is there a visible sharpness improvement between 4-pass baseline and 16-pass sigma=0.50?
Is the improvement worth 4x the simulation time?

**Q4 — Best vs Baseline (R_best_vs_baseline.jpg):**
Does the right panel (best render: sigma=1.5, gamma=0.70, no-blur, nearest) look
meaningfully better than the baseline? Which of the three panels would you choose
for the final production run?

**Q5 — Nikon (S_nikon_best_params.jpg):**
Does sigma=0.50 + 16-pass look good on the nikon image, or is there visible grid artifact
that wasn't present in the inkbrush?

**Q6 — Colormap (T_cmap_sigma_comparison.jpg):**
Two colormaps: 'sunlight' (current amber) and 'hot' (black→red→orange→yellow→white, used in published caustic papers).
Plus sigma=0.50 vs sigma=0.75 variants.
Which colormap + sigma combination looks best?

---

## Recommended Default Parameters (pending Claude Chat visual confirmation)

Based on 4 parallel research subagents + sweep results:

```
# For 512px normal mesh (~525k faces):
python3 simulate_batch.py \
  --sigma 0.75 --passes 8 --post-sigma 0.0 --interp nearest --gamma 0.70

# For 1024px production mesh (~2.1M faces):
python3 simulate_batch.py \
  --sigma 0.75 --passes 4 --post-sigma 0.0 --interp nearest --gamma 0.70
```

---

## Prompt for Claude Chat Response

Please write your visual assessment to:
  `/Users/admin/causticsEngineering/claude_chat_handoff4/CRISPNESS_SELECTION.md`

Format:
  Q1: sigma=X.XX (reason: ...)
  Q2: gamma=0.70 better/worse (reason: ...)
  Q3: passes worth it: yes/no (reason: ...)
  Q4: recommended panel: baseline/best-sigma/best-render (reason: ...)
  Q5: nikon grid artifact: yes/no (reason: ...)
  Q6: preferred colormap: sunlight / hot (reason: ...)
  RECOMMENDED DEFAULTS: (your call on sigma, gamma, passes, post-sigma, interp, colormap)
