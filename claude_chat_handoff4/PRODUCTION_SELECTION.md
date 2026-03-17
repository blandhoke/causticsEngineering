# PRODUCTION_SELECTION.md
# Written by: Claude Chat (visual ranking)
# Date: 2026-03-16
# Based on: N_contact_sheet.jpg — all 10 results reviewed

---

## Visual Ranking (1 = best caustic for CNC production)

### 1. INKBRUSH — TOP PICK FOR PRODUCTION
Both fast and normal show the most compelling caustic in the batch.
The cow is fully recognizable — forward-facing, clean anatomy, ears visible,
muzzle clear. The normal render shows excellent tonal separation: bright
concentrated regions on the face, dark background, strong edge structure
along the jawline and ear contours. The inkbrush artistic treatment has
produced the right kind of high-contrast input — the solver is concentrating
light exactly where the ink strokes are. This will look striking at 30" throw.
Run at 1024px.

### 2. NIKON — STRONG SECOND, RUN AT 1024px
The Nikon render shows the cow clearly facing forward with good bilateral
symmetry. The normal result has strong bright regions across the face with
visible ear and jaw structure. Slightly more photographic than inkbrush —
you can see some mid-tone fill — but the caustic structure is clean and
recognizable. Worth running at production resolution to compare directly
against inkbrush.

### 3. WOODBLOCK — INTERESTING, HOLD
Woodblock shows a recognizable cow but the artistic treatment produces a
blockier, more graphic caustic. The normal render has strong geometric
character — bright flat regions rather than fine edge lines. This could be
compelling at 1024px but it reads differently (more graphic, less organic)
than inkbrush. Hold for a second production run after inkbrush/Nikon are
evaluated physically.

### 4. CHARCOL — CONDITIONAL
Charcoal shows the cow clearly but the fast/normal quality difference is
noticeable — the normal render has better edge definition. The caustic has
a slightly smeared quality consistent with charcoal's soft marks. Not the
sharpest caustic but artistically interesting. Do not prioritize for first
production run.

### 5. BANKNOTE — LOWEST PRIORITY
The banknote treatment is producing the most photographic-looking output of
the five — the caustic has fine-line cross-hatching across the face that
creates a dense, visually busy result. The overall amber fill is higher than
the others (less black showing through), suggesting the banknote engraving
style has too much tonal coverage for the solver to concentrate cleanly.
May be worth testing at production but is the lowest priority of the five.

---

## Fast vs Normal Quality Assessment

All five images show a meaningful quality improvement from fast (256px) to
normal (512px):
- Better edge definition at normal — finer caustic lines
- Slightly less blocky/pixelated cow anatomy
- The difference is worth the extra 10 minutes at normal resolution
- At 1024px the improvement should be proportionally larger and worth the
  full 45-minute Julia run

---

## Physics Check — Any Errors?

No flat/washed outputs detected. All 10 renders show:
- Black background (no flat amber fill like the old befuddled v5)
- Concentrated bright regions corresponding to the cow face
- Dark regions corresponding to background areas
All renders are physically valid caustics. The pipeline fix is confirmed
working across all 5 artistic treatments.

---

## PRODUCTION RECOMMENDATION

Run these two at 1024px, in this order:

  PRIORITY 1: inkbrush
    COW2_INPUT="Final cows/inkbrush.png" — run at 1024px production
    Expected: best caustic quality of the batch, fine ink-stroke lines
    concentrated at ~30" throw

  PRIORITY 2: Nikon
    COW2_INPUT="Final cows/Nikon.png" — run at 1024px production
    Expected: clean photographic-quality caustic, strong bilateral symmetry

Run inkbrush first. Review physical output before committing to Nikon.
If inkbrush mills well and projects cleanly, run Nikon as the second lens.

Do NOT run banknote or charcol at production until inkbrush/Nikon are
physically validated.

---

## Claude Code Next Action

1. Run production pipeline for inkbrush at 1024px:
   COW2_INPUT="Final cows/inkbrush.png" bash run_pipeline_production.sh
   (or use start_julia.sh with run.jl pointing to inkbrush.png)
   Output to: Final cows/inkbrush/production/

2. After inkbrush completes (~80 min), run make_physical_lens.py on the
   production mesh to generate the CNC-ready scaled OBJ.

3. Bring caustic render back to Claude Chat for final visual approval
   before sending to CAM.
