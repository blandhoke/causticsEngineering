# Claude Chat Handoff Package
# Caustic Lens Pipeline — Geometry Mismatch Investigation
# Prepared: 2026-03-15 by Terminal 2 (Claude Code)

---

## Purpose

This package gives Claude Chat everything needed to diagnose and fix a geometric
mismatch between the target cow image and the forward ray trace caustic output.

## Start Here

Read `HANDOFF_PROMPT.md` first — it contains the exact questions to answer and
the specific visual comparisons to make.

`GEOMETRY_ANALYSIS.md` is the detailed technical background prepared by Terminal 2.
Read it for context but treat it as a hypothesis, not a conclusion.

---

## Package Contents

```
README.md                 ← this file
HANDOFF_PROMPT.md         ← the prompt: questions to answer, what to do
GEOMETRY_ANALYSIS.md      ← technical analysis from Terminal 2

images/
  cow_render.jpg          ← original target image (512×512 B&W photograph)
  caustic_cow_v2.png      ← current caustic output (after orientation fixes)
  caustic_cow.png         ← v1 caustic — RAW, no orientation fix (upside-down)
  caustic_simulated.png   ← water-drop caustic (known-good reference render)
  loss_it1.png            ← solver residual map, iteration 1
  loss_it6.png            ← solver residual map, iteration 6
                            (blue=mesh area > target, red=mesh area < target)

code/
  run.jl                  ← Julia entry point (loads image, calls engineer_caustics)
  create_mesh.jl          ← full solver source (permutedims is on ~line 855)
  simulate_cow.py         ← Python forward ray trace (current, with np.fliplr fix)
  simulate_caustic.py     ← Python forward ray trace (original, water-drop version)
```

---

## Quick Visual Guide

| Image | What to look for |
|-------|-----------------|
| `cow_render.jpg` | DARK ear = upper-RIGHT. LIGHT ear = upper-LEFT. Muzzle = lower-center. Large BRIGHT background = upper-right quadrant. |
| `loss_it1.png` | Red regions = not enough light (dark in target). Blue = too much light (bright in target). Cow should be recognizable and correctly oriented. |
| `loss_it6.png` | Same encoding. Compare structure to it1 — has the solver reduced the residual? |
| `caustic_cow.png` | V1: no orientation fix. Should appear upside-down and/or mirrored. |
| `caustic_cow_v2.png` | V2: origin='upper' + np.fliplr applied. Question is: is this now correct, or still wrong axis? |
| `caustic_simulated.png` | Water-drop caustic. Shows the pipeline works for that target. Reference for what a good caustic looks like. |

---

## The Central Question

Does `permutedims(img)` in `engineer_caustics` (create_mesh.jl ~line 855) cause
a 90° rotation in the final caustic output?

The evidence suggests yes, but only visual confirmation — specifically comparing
the loss images (which undo the transpose for display) against the caustic output
(which does not) — will give a definitive answer.

---

## Constraints

- DO NOT re-run `julia run.jl` unless explicitly instructed to do so
- DO NOT delete `cow_accum.npy` or `cow_meta.npy` — cached ray trace data
- DO NOT modify `ma.py` or `opt_weights.npy` — unrelated OT solver cache
- DO NOT change OBJ import axes (`forward_axis='Y', up_axis='Z'` is confirmed correct)
- Physical parameters (IOR=1.49, focal=0.2m) are correct — do not adjust
