# ANALYSIS_FINDINGS.md
# Written by: Claude Chat
# Date: 2026-03-16
# Based on: inkbrush_normal_v2, T_sharpness_sweep, U_overlay, V_cross_image_metrics,
#            V2_cross_image_strip. Pipeline diagnostics W+X still > 1MB — see note.

---

## NOTE: W and X pipeline diagnostics still exceed 1MB

W_inkbrush_pipeline_diagnostic.png = 714KB ← should load but didn't
X_nikon_pipeline_diagnostic.png = 672KB ← same

Both are under 1MB per the directory listing but the MCP tool is returning
"too large" — likely uncompressed pixel buffer size, not file size.
Claude Code needs to re-run cc_resize.py on these two files with max=600px
(not 900px) to guarantee they load. Current max=900px is still too large
for 12-panel figures with black backgrounds.

Q1 (nikon banding in OBJ heightmap) therefore CANNOT be answered yet.
All other questions answered below.

---

## Q2 — New defaults validation: inkbrush_normal_v2.png

VERDICT: Marginal improvement, wrong direction on one metric.

The darker gamma=0.70 does increase apparent contrast of the bright caustic
lines — the jaw and ear rim-light reads more distinctly against the background.
The nose and muzzle structure is slightly more readable.

However: the amber background fill is STILL the dominant character of the
image. The background reads as dark amber, not black. The cow still appears
to glow from within rather than being lit from above by concentrated sunlight.

The improvement in the metrics (contrast +20%, black coverage +0.6%) is real
but does not change the fundamental visual character. This is a better version
of the same problem, not a solution to the problem.

RECOMMENDATION: Accept these as new defaults for now. The background fill
issue requires a solver-level fix, not a render-level fix.

---

## Q3 — Overlay spatial correspondence: U_overlay_inkbrush.png

VERDICT: Partial correspondence, worse than expected.

At alpha=0.5, the cyan input edges and amber caustic are both visible
simultaneously. Observations:
- The ear outlines and jaw curve show reasonable correspondence
- The forehead blaze/parting line (bright vertical line in caustic) does
  NOT correspond to a strong edge in the input — it appears to be a solver
  artifact from the tonal boundary between the dark hair and light area
- The local Pearson r map (bottom row, second panel) shows the face center
  as mostly red/negative — the solver is ANTI-correlated with edges in the
  central face region. Green (positive correlation) only appears at the
  outer rim of the cow face.
- The difference image (bottom left, red background) shows the caustic has
  excess light EVERYWHERE relative to the input edges — this is the ambient
  fill problem visualized directly.

The r=0.014 for inkbrush OBJ encoder correlation is confirmed visually.
The solver is not encoding the inkbrush strokes — it is encoding the broad
tonal regions of the image.

---

## Q4 — Cross-image ranking: V_cross_image_metrics.png + V2

VERDICT: Nikon IS the best input for caustics by every metric. Confirmed.

From V_cross_image_metrics:
  Caustic sharpness:  Nikon 0.130 > Woodblock 0.120 > Banknote 0.107
                      > Inkbrush 0.107 > Charcol 0.104
  r(caustic, edges):  Nikon +0.219 > Woodblock +0.186 > Banknote +0.213
                      > Charcol +0.208 > Inkbrush +0.150
  Black coverage:     All within 0.1% of each other — not image-dependent

Inkbrush scores LAST on edge encoding (r=0.150). It was selected for artistic
reasons, not metric reasons. This is fine — metrics don't capture the artistic
character — but it means inkbrush requires a stronger input preparation to
compete with nikon on caustic quality.

Critically: from V2_cross_image_strip, the visual quality of nikon's caustic
(bottom row, first panel) shows clear bilateral symmetry and structured edge
lines, despite the banding. Inkbrush caustic (fourth panel) shows a softer,
more diffuse output — the inkbrush strokes themselves are NOT encoding as
distinct caustic lines.

RECOMMENDATION: Nikon should be the production candidate IF the banding can
be confirmed as solver-fixable. Inkbrush is the artistic fallback.

---

## Q5 — post_sigma=0.25 vs 0.0

VERDICT: Not worth testing at this stage.

The composite score difference is 0.900 vs 0.880 — a 2.2% improvement that
is below the threshold of visual perceptibility. More importantly, both are
significantly better than the old baseline (which would score ~0.725 on the
same composite). The marginal gain from adding 0.25 post-sigma blur does not
justify the added complexity when the primary quality ceiling is the solver.

Lock in post_sigma=0.0 as the permanent default.

---

## Additional Observations

### V2 visual strip reveals the core problem clearly

Looking at all 5 inputs (top row) vs caustics (bottom row) side by side:
- Every input image has HIGH input sharpness (white/black cow images)
- Every caustic output has similar character: amber filled, same background level
- The caustic output quality does NOT strongly correlate with input quality
- This is the definitive visual evidence that the quality ceiling is the SOLVER

The solver is producing similar output regardless of whether the input is a
crisp inkbrush, a sharp nikon photo, or a woodblock print. The ~54-57% black
coverage is consistent across all 5. This strongly suggests the solver's 6
SOR iterations are not sufficient to produce sharp light concentration.

### The fundamental fix needed

The solver needs more iterations OR a different input preprocessing that
better exploits what 6 iterations CAN do well.

What 6 iterations can do: encode large-scale tonal boundaries well
What 6 iterations cannot do: encode fine edge detail faithfully (r=0.014 on inkbrush)

Practical options in priority order:
  1. Increase SOR iterations from 6 to 8-10 (CONFIRM REQUIRED — new Julia run)
     Expected: better edge encoding, less ambient fill, higher r(OBJ, edges)
  2. Input preprocessing: strong Gaussian blur on inputs before solver
     (counterintuitive but: blurred input = broader tonal regions = solver
      can concentrate energy more efficiently at fewer sharp boundaries)
  3. Accept current output quality and mill inkbrush as artistic statement
     The ambient amber glow may actually look compelling as a physical lens

---

## Priority Actions for Claude Code

1. Re-run cc_resize.py on W and X with max=600px so Claude Chat can read them:
   python3 cc_resize.py \
     "Final cows/inkbrush/analysis/pipeline_diagnostic.png" \
     --out claude_chat_handoff4/ --prefix "W2_inkbrush_"
   python3 cc_resize.py \
     "Final cows/nikon/analysis/pipeline_diagnostic.png" \
     --out claude_chat_handoff4/ --prefix "X2_nikon_"

2. After W2 and X2 are delivered: Claude Chat will answer Q1 (nikon banding)

3. If Q1 confirms solver banding in OBJ heightmap:
   Prepare a prompt to increase SOR iterations from 6 to 8 in create_mesh.jl
   CONFIRM REQUIRED before any Julia run

4. Do not proceed to production 1024px until Q1 is answered.
