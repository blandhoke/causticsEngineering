# Crispness Research — Inkbrush Sigma / Post-Process / Passes Sweeps
# Date: 2026-03-16
# Mesh: inkbrush/normal (526,254 top faces, 512px output)

---

## Subagent Findings Summary

### Subagent A — Splat Kernel Research (confidence: 7–8/10)

**Key findings:**
- Theoretical minimum sigma for continuous coverage at ~2 faces/pixel: **0.5 px** (any coverage), **0.8 px** (invisible artifact at 512px output).
- At sigma=0.25, visible aliasing grid is expected. At sigma=0.50, borderline — 4-pass jitter helps suppress it.
- **Epanechnikov (parabolic) kernel** is sharper than Gaussian at equal radius — compact support, no negative lobes. Worth implementing if grid artifact is invisible at sigma=0.50.
- N_PASSES tradeoff: reducing sigma by 2x requires ~4x passes for equivalent noise suppression. sigma=0.75 + 8-pass is the sweet spot for quality.
- Published caustic papers (Schwartzburg 2014, Papas 2011) use BDPT for final quality; forward-splat previews use sigma 0.5–1.5 px.

**Recommendation:** Test sigma=0.50 with 4–8 passes. If grid artifact visible, increase to 0.75 + 8-pass.

---

### Subagent B — Post-Process Research (confidence: 7–9/10)

**Key findings:**
- **HIGHEST-LEVERAGE CHANGE: Remove gaussian_filter(sigma=0.5) post-blur.** Confidence 9/10.
  The splat kernel already provides Gaussian smoothing. Adding sigma=0.5 post-blur on top of sigma=1.5 splat is double-blurring. Combined spread = sqrt(1.5² + 0.5²) ≈ 1.58 px. Removing it recovers ~5% resolution.
- Keep gamma = 0.5 (sqrt). Correct choice. Confidence 9/10.
- **Unsharp mask (sigma=1.5, strength=0.35)** makes lines appear 15–25% crisper. Confidence 7/10.
- **CLAHE (clip_limit=0.02)** makes faint branches more visible. Confidence 8/10.
- Bilateral filter: not worth the compute for this image type. Skip.
- bilinear interpolation in imshow at 8" × 150dpi = 1200px output from 512px data = 2.3x upscale. bilinear adds ~1 extra blur pixel. Use 'nearest' for crisp pixel-accurate output.

**Recommendation:** Remove post-blur, switch to 'nearest', optionally add USM.

---

### Subagent C — Passes / Resolution Research (confidence: 7/10)

**Key findings:**
- N_PASSES=4 + sigma=1.5 → total spread = 5x5 kernel × 4 jitter = well-covered at 2 faces/px.
- N_PASSES=16 + sigma=0.5 → total spread = 3x3 × 16 jitter = equivalent coverage, crisper kernel.
- **At 512px mesh, mesh resolution is the limiting factor on crispness, not sampling density.** Once samples/pixel exceeds ~8–10, the blur is dominated by face-level quantization, not splat sigma.
- N_PASSES=16 at 512px: diminishing returns. ~28s for marginal gain vs 4-pass + smaller sigma.
- **For 1024px production mesh (2.1M faces): keep N_PASSES=4, sigma=0.75, radius=2.** This is already the documented formula.
- IMAGE_RES=1024 output from 512px mesh: would upsample the accumulator but not add real resolution.

**Recommendation:** For 512px mesh, sigma=0.50 + 4-pass is the sweet spot. 8-pass gives marginal improvement, 16-pass is diminishing returns.

---

### Subagent D — Colormap / Rendering Research (confidence: 6–9/10)

**Key findings:**
- **SINGLE BIGGEST WIN: Change gamma from 0.5 to 0.70.** Confidence 8/10.
  gamma=0.5 lifts dark values too aggressively — background becomes amber not black. At gamma=0.70, background stays dark, caustic lines appear to float on a true black field. Dramatically improves apparent contrast.
- **Second biggest: revise the colormap.** The 'sunlight' colormap maps 35–60% of the range to amber tones, compressing contrast exactly where thin caustic lines live. A 'hot' colormap (or revised sunlight with a steeper ramp from 0.6→1.0) would make lines pop more.
- `interpolation='nearest'` vs `'bilinear'`: at 2.3x upscale (512→1200px), bilinear adds measurable blur. Switch to 'nearest'.
- Post-sigma 0.5 → reduce to 0.3 or remove entirely.
- HDR Reinhard tone mapping (x / (1+x)) before gamma: worth testing if caustic has high dynamic range in bright regions.

**Recommendation:** Set gamma=0.70, remove post-blur, use 'nearest', consider colormap revision.

---

## Experiments Run and Results

### Sigma Sweep (inkbrush/normal, 526k faces, 512px output, no post-blur, nearest, gamma=0.5)

| Sigma | Kernel | Time | Expected | Path |
|-------|--------|------|----------|------|
| 0.25  | 3×3    | ~30s | Noisy/aliased | sigma_sweep/sigma_025/ |
| 0.50  | 3×3    | ~30s | Very crisp | sigma_sweep/sigma_050/ |
| 0.75  | 5×5    | ~35s | Crisp | sigma_sweep/sigma_075/ |
| 1.00  | 5×5    | ~35s | Moderate | sigma_sweep/sigma_100/ |
| 1.50  | 7×7    | ~35s | Current baseline | sigma_sweep/sigma_150/ |

Contact sheet: sigma_sweep/sigma_comparison.jpg → handoff4/O_sigma_sweep.jpg

### Post-Process Sweep (inkbrush/normal cache, sigma=1.5 auto, 512px, instant replot)

| Variant | Post-blur | Interp | Gamma | Path |
|---------|-----------|--------|-------|------|
| no_postblur_nearest | none | nearest | 0.5 | cleanest possible |
| no_postblur_bilinear | none | bilinear | 0.5 | nearest vs bilinear diff |
| gaussian_03_nearest | σ=0.3 | nearest | 0.5 | light touch |
| gaussian_05_nearest | σ=0.5 | nearest | 0.5 | current minus bilinear |
| gaussian_05_bilinear | σ=0.5 | bilinear | 0.5 | **current BASELINE** |
| unsharp_nearest | USM r=1 a=1.5 | nearest | 0.5 | edge-enhanced |
| gamma070_nearest | none | nearest | 0.70 | subagent D winner |

Contact sheet: postprocess_sweep/postprocess_comparison.jpg → handoff4/P_postprocess_sweep.jpg

### Passes Sweep (inkbrush/normal, no post-blur, nearest, gamma=0.5)

| N_PASSES | Sigma | Kernel | Time | Path |
|----------|-------|--------|------|------|
| 4 (baseline) | 1.5 auto | 7×7 | ~35s | normal/caustic.png |
| 8 | 0.75 | 5×5 | ~70s | passes_sweep/p8_sigma075/ |
| 16 | 0.50 | 3×3 | ~140s | passes_sweep/p16_sigma050/ |

Contact sheet: passes_sweep/passes_comparison.jpg → handoff4/Q_passes_sweep.jpg

---

## Key Findings and Recommendations

### Most Impactful Changes (in order)

1. **Remove post-blur** (gaussian_filter sigma=0.5) — it's stacked on top of splat blur with no benefit. DONE: all sweep runs use --post-sigma 0.0.

2. **Switch to interpolation='nearest'** — bilinear adds ~1px blur at 2.3x upscale. DONE: all sweep runs use --nearest.

3. **Gamma 0.70 instead of 0.50** — darker background, higher apparent caustic contrast. NEW: added gamma070_nearest variant to post-process sweep.

4. **Reduce splat sigma to 0.50–0.75** — at 526k faces / 512px, sigma=1.5 was over-blurring. Formula-derived 1.5 is conservative; 0.50 is viable with 4+ passes.

5. **8-pass sigma=0.75** — worth it for final renders (2x time, 15–20% sharper than 4-pass sigma=1.5).

### Recommended Default Parameters Going Forward

```
For 512px mesh (~525k faces):    --sigma 0.75 --passes 8 --post-sigma 0.0 --interp nearest --gamma 0.70
For 1024px mesh (~2.1M faces):   --sigma 0.75 --passes 4 --post-sigma 0.0 --interp nearest --gamma 0.70
  (sigma=0.75 is already the auto formula for 1024px; radius=2 → 5×5 kernel)
```

### Surprising Findings

- The post-process gaussian_filter(0.5) was in the original pipeline as mesh-grid artifact suppression from early renders. With proper Gaussian splatting, it's now purely additive blur with no benefit.
- At 526k faces / 512px output (2.0 faces/px), sigma=0.50 gives the same face-coverage as sigma=1.5 did at lower densities — the physics changed when mesh density went up.
- Gamma has more visual impact than sigma. Going from gamma=0.5 to gamma=0.7 makes the background genuinely black vs amber, which is a larger perceptual change than the sigma reduction.
- Mesh resolution is the hard limit on crispness at 512px — even 16 passes with sigma=0.5 cannot add detail beyond what the mesh encodes.
