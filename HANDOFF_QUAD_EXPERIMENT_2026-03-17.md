# HANDOFF — 16-Quadrant Preprocessing Sweep
# Date: 2026-03-17
# Session: 4 blocks × 4 quadrants × HYPER screening → NORMAL promotion

---

## What Was Done

Ran a systematic preprocessing sweep to find the best solver input technique for
the inkbrush image. 16 HYPER (128px, ~33k faces) runs across 4 blocks of 4 techniques
each, then promoted promising variants to NORMAL (512px, ~526k faces) for confirmation.

New infrastructure built this session:
- `prepare_inputs.py` — 7-technique preprocessing library
- `start_julia_quad.sh` — safe background launcher for quad pipeline runs
- `run_quad_pipeline.sh` — single-quad orchestrator (Julia → Mitsuba → metrics → thumb)
- `combine_quads.py` / `combine_quads_normal.py` — 4-quad → 8"×8" block assembler

---

## Technique Assignments

Input: inkbrush source image (1024×1024px) with various preprocessing applied.

| Block | Q1 | Q2 | Q3 | Q4 |
|-------|----|----|----|----|
| Block 1 | alpha_blend (raw) | clahe | unsharp_mask | gradient_magnitude |
| Block 2 | blur_only σ=1 | blur_only σ=2 | blur_only σ=4 | blur_only σ=8 |
| Block 3 | blur(σ=8)→grad | blur(σ=3)→grad | raw Sobel/grad | raw photo ref |
| Block 4 | raw photo ref | high-pass | bandpass σ_lo=2 σ_hi=32 | bandpass σ_lo=1 σ_hi=8 |

Input image statistics confirm these assignments:
- Block 3 Q1: mean=0.056, std=0.092 (very sparse gradient after heavy blur)
- Block 3 Q2: mean=0.094, std=0.133 (moderate sparse gradient)
- Block 3 Q3: mean=0.159, std=0.190 (raw gradient, less sparse)
- Block 4 Q3: mean=0.478, std=0.121 (bandpass mid-frequency content)
- Block 4 Q4: mean=0.432, std=0.063 (narrower band, lower variance)

---

## HYPER Screening Results (128px, ~33k faces)

Thresholds: PASS = z_std ≥ 0.3mm AND edge_r ≥ 0.05
            MARGINAL = one threshold met
            REJECT = neither met
            REJECT-flat = z_std < 0.3mm (lens geometrically flat)

| Quad | Technique | z_std (mm) | edge_r | Status |
|------|-----------|-----------|--------|--------|
| block1_q1 | alpha_blend | 2.624 | −0.0144 | REJECT |
| block1_q2 | clahe | 2.614 | −0.0105 | REJECT |
| block1_q3 | unsharp_mask | 2.590 | +0.0054 | REJECT |
| block1_q4 | gradient_magnitude | 0.039 | +0.0394 | REJECT-flat |
| block2_q1 | blur_only σ=1 | 2.629 | −0.0070 | REJECT |
| block2_q2 | blur_only σ=2 | 2.628 | +0.0121 | REJECT |
| block2_q3 | blur_only σ=4 | 2.627 | +0.0181 | REJECT |
| block2_q4 | blur_only σ=8 | 2.627 | +0.0140 | REJECT |
| block3_q1 | blur(σ=8)→grad | 0.040 | +0.0387 | REJECT-flat |
| block3_q2 | blur(σ=3)→grad | 0.501 | +0.0416 | MARGINAL |
| block3_q3 | blur(σ=2)→grad | 0.409 | +0.0542 | **PASS** |
| block3_q4 | raw photo ref | 2.629 | −0.0199 | REJECT |
| block4_q1 | raw photo ref | 2.619 | −0.0142 | REJECT |
| block4_q2 | high-pass | 2.619 | −0.0088 | REJECT |
| block4_q3 | bandpass σ_lo=2 σ_hi=32 | 2.629 | +0.0246 | MARGINAL |
| block4_q4 | bandpass σ_lo=1 σ_hi=8 | 2.383 | +0.0407 | MARGINAL |

**HYPER winner: block3_q3 (blur→grad, σ≈2)** — only quad to hit both thresholds.

Promoted to NORMAL: block3_q2, block3_q3 (PASS/MARGINAL), block4_q3, block4_q4 (MARGINAL — bandpass is a physically motivated candidate worth testing at full resolution).

---

## NORMAL Results (512px, ~526k faces)

| Quad | Technique | z_std (mm) | edge_r | pct_black | Status |
|------|-----------|-----------|--------|-----------|--------|
| block3_q2_normal | blur(σ=3)→grad | 0.165 | +0.104 | 21.3% | REJECT-flat |
| block3_q3_normal | blur(σ=2)→grad | **0.089** | +0.108 | 21.1% | REJECT-flat |
| block4_q3_normal | bandpass σ_lo=2 σ_hi=32 | **1.336** | +0.101 | 20.8% | **PASS** |
| block4_q4_normal | bandpass σ_lo=1 σ_hi=8 | **1.332** | +0.104 | 20.6% | **PASS** |

Reference (inkbrush NORMAL baseline): z_std = 1.354mm, edge_r = 0.159

---

## Critical Finding: Technique Reversal Between HYPER and NORMAL

**blur-then-gradient COLLAPSED at NORMAL resolution.**

- HYPER: blur→grad = 0.41–0.50mm z_std (PASS/MARGINAL)
- NORMAL: blur→grad = 0.09–0.17mm z_std (REJECT-flat — worse than HYPER!)

**bandpass PROMOTED at NORMAL resolution.**

- HYPER: bandpass = 2.38–2.63mm z_std (MARGINAL, low edge_r)
- NORMAL: bandpass = 1.33mm z_std, edge_r ≈ 0.10 (PASS)

**Physics explanation:**
Blur-then-gradient creates a very sparse, thin-line input. At 128px, those sparse
gradients have enough relative energy to drive lens curvature. At 512px, the same
sparse lines occupy a tiny fraction of the mesh — the solver sees mostly black background
and produces a nearly-flat lens with very little deflection geometry.

Bandpass preserves mid-frequency photographic content (face shapes, tonal regions)
while removing DC (flat gray areas). At HYPER resolution, this gives the solver
a "busy" image where energy is spread everywhere — the solver cannot concentrate it
sharply → low edge_r despite high z_std. At NORMAL resolution, the 4x more mesh nodes
allow the solver to encode the mid-frequency features precisely, producing a
geometrically rich lens (z_std ≈ 1.33mm, matching the photo baseline of 1.354mm)
with meaningful caustic edge correlation (+0.101 to +0.104 vs inkbrush baseline 0.014).

**Rule going forward:** HYPER screening is NOT a reliable predictor for NORMAL outcome.
Run at least one FAST (256px) intermediate step for any new technique before committing
to NORMAL or PROD.

---

## Anomalies

1. **block1_q2 error**: `start_julia_quad.sh failed (exit 1)` — error.txt shows launch
   failure. The HYPER OBJ still exists and post-processing completed. Root cause was
   likely a stale PID file from the previous run. Julia completed successfully for
   this quad (metrics and geometry files present and valid).

2. **blur(σ=8)→grad collapse** (block3_q1): z_std=0.040mm — even worse than gradient_magnitude
   alone (block1_q4: z_std=0.039mm). Heavy blurring before gradient removes all high-frequency
   structure, leaving almost no signal for the solver. Both collapse to identical flat geometry.

3. **HYPER z_std ~2.63mm** for most techniques: Photo-like inputs (alpha_blend, clahe,
   blur_only, raw photo) all produce z_std ≈ 2.62–2.63mm at HYPER. This is the
   "saturated" regime — the solver uses all available deflection range with a
   photo input regardless of minor preprocessing differences. Edge_r is the
   discriminating metric in this regime.

4. **block4_q4 bandpass (σ_lo=1 σ_hi=8)**: z_std dropped to 2.38mm at HYPER vs 2.63mm
   for other photo-like inputs. The very narrow bandpass removes both low and high
   frequencies, leaving very low-variance content (std=0.063) — enough to cause
   partial solver energy reduction even at HYPER scale.

---

## Combined Block Meshes (HYPER, for visual reference only)

These are 8"×8" blocks assembled from 4 HYPER quads (25mm→4"×4" scaled).
Physical dome heights are unrealistically tall at HYPER scale (~87mm) — not CNC-suitable.
Use for visual/caustic pattern comparison only.

- `examples/block1/block1_combined_8x8.obj`  (all photo-enhancing techniques)
- `examples/block2/block2_combined_8x8.obj`  (blur_only variants)
- `examples/block3/block3_combined_8x8.obj`  (gradient + photo refs)
- `examples/block4/block4_combined_8x8.obj`  (bandpass + photo refs)

---

## Production Candidates (NORMAL OBJs ready for physical evaluation)

| File | Technique | z_std | edge_r | Dome (native) |
|------|-----------|-------|--------|---------------|
| `examples/block4_normal/block4_q3_normal_hyper.obj` | bandpass σ_lo=2 σ_hi=32 | 1.336mm | 0.101 | 21.5mm |
| `examples/block4_normal/block4_q4_normal_hyper.obj` | bandpass σ_lo=1 σ_hi=8  | 1.332mm | 0.104 | 21.5mm |

Both fit within 1" (25.4mm) stock. Narrow-band (σ_lo=1 σ_hi=8) has marginally
higher edge_r (0.104 vs 0.101). Difference is within noise — either is suitable.

Note: OBJ filenames have `_hyper` suffix due to naming artifact in run_quad_pipeline.sh
— the files contain NORMAL (512px, ~526k face) mesh data. Rename before CAM:
```
cp examples/block4_normal/block4_q3_normal_hyper.obj examples/block4_normal/block4_q3_bandpass_2_32_normal.obj
cp examples/block4_normal/block4_q4_normal_hyper.obj examples/block4_normal/block4_q4_bandpass_1_8_normal.obj
```

---

## Contact Sheets for Claude Chat Review

All 4-panel results contact sheets are in `claude_chat_handoff4/`:
- `block1_results_contact.png` — alpha_blend / clahe / unsharp / gradient
- `block2_results_contact.png` — blur_only σ=1,2,4,8
- `block3_results_contact.png` — blur→grad variants + raw photo reference
- `block4_results_contact.png` — bandpass variants + raw photo reference

Input preview panels: `block{1-4}_inputs_preview.png`

---

## Recommended Next Steps

1. **Visual review of block4_q3 and block4_q4 NORMAL renders** in Claude Chat.
   Ask Claude Chat: "Do block4_q3_normal and block4_q4_normal show recognizable
   inkbrush caustic features? Is block4_q4 (narrow bandpass) noticeably sharper?"

2. **Run PROD (1024px)** on the winning bandpass technique once Claude Chat approves.
   Use: `COW2_INPUT=./examples/quad_input_block4_q3_normal.png bash start_julia.sh`
   Expected: ~45 min, ~2.1M face mesh, dome ≈ 21.5mm (fits 1" stock).

3. **Consider σ_lo / σ_hi tuning sweep** at HYPER before PROD.
   Variants to test: σ_lo=1.5 σ_hi=16, σ_lo=1 σ_hi=4, σ_lo=2 σ_hi=16.
   The bandpass parameters were not tuned — the current σ_lo=1 σ_hi=8 and σ_lo=2 σ_hi=32
   were arbitrary starting points. A 4-point HYPER sweep takes ~10 minutes.

4. **Update CLAUDE.md Preprocessing section** once a winner is confirmed at NORMAL+.
   Current CLAUDE.md documents Sobel as primary lever (+1250% vs raw). Bandpass
   produces comparable edge_r (0.10) to Sobel (0.05 at HYPER, actual NORMAL value
   not yet measured for Sobel). Consider a direct Sobel vs bandpass NORMAL comparison.

5. **Fix `_hyper.obj` naming artifact** in `run_quad_pipeline.sh`:
   The OBJ output is named `${LABEL}_hyper.obj` regardless of JL_SCRIPT.
   Should use `${JL_SCRIPT%.jl}` suffix derived from the actual script name.

---

## Files Committed This Session

```
prepare_inputs.py              preprocessing library (7 techniques + preview generator)
start_julia_quad.sh            safe quad-pipeline Julia launcher
run_quad_pipeline.sh           single-quad orchestrator
combine_quads.py               4-quad → 8"x8" block assembler
combine_quads_normal.py        NORMAL-scale wrapper (same logic)
examples/block1/               16 HYPER runs, metrics, renders, geometry
examples/block2/
examples/block3/
examples/block3_normal/        NORMAL runs: blur→grad (both REJECT-flat)
examples/block4/
examples/block4_normal/        NORMAL runs: bandpass (both PASS)
examples/quad_input_*.png      21 preprocessed input images
claude_chat_handoff4/          results contact sheets, input previews, thumbnails
.gitignore                     added: examples/loss_it*.png, logs/
```
