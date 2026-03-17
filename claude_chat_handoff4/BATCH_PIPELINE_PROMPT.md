# Claude Code Prompt — Final Cows Batch Run
# Date: 2026-03-16
# From: Claude Chat
# Goal: Run all 5 Final Cows images through FAST and NORMAL pipelines in parallel.
#       All outputs self-contained in Final cows/<n>/ subfolders.
#       Original images untouched.

---

## READ FIRST

Read `/Users/admin/causticsEngineering/CLAUDE.md` and `~/.claude/CLAUDE.md`.
All hooks, autonomy rules, and confirmation formats are live.

---

## CONTEXT

The HYPER pipeline confirmed the solver is working correctly with near-binary
artistic inputs. We now have 5 curated cow images ready for a full comparative
run. The goal is to see which artistic treatment produces the most compelling
caustic output — these results will directly inform the CNC production decision.

Input images (do not modify):
  /Users/admin/causticsEngineering/Final cows/ banknote.png
  /Users/admin/causticsEngineering/Final cows/charcol.png
  /Users/admin/causticsEngineering/Final cows/inkbrush.png
  /Users/admin/causticsEngineering/Final cows/Nikon.png
  /Users/admin/causticsEngineering/Final cows/woodblock.png

Note: banknote.png has a leading space in the filename. Handle this carefully
in all scripts — quote all paths, never glob without quoting.

---

## JULIA AUTO-APPROVAL

User has confirmed this is the only terminal open. There is no OBJ collision
risk. ALL Julia solver runs in this batch are pre-approved. Do not ask for
confirmation before running any Julia job. Run the full batch autonomously
from start to finish.

---

## FILE MANAGEMENT STRATEGY

Every image gets its own subfolder under "Final cows/". All outputs for that
image live there forever — mesh, cache, renders, log. Nothing crosses between
image subfolders. The examples/ directory is used only as a transit area during
the Julia run (because engineer_caustics() hardcodes its output path there);
all files are moved to the image subfolder immediately after each step.

Structure:
  Final cows/
    banknote/
      fast/
        mesh.obj             ← 256px solver output
        accum.npy            ← ray trace cache
        meta.npy
        caustic.png          ← final render
        run.log              ← timing + sigma + hit rate
      normal/
        mesh.obj             ← 512px solver output
        accum.npy
        meta.npy
        caustic.png
        run.log
    charcol/
      [same structure]
    inkbrush/
      [same structure]
    Nikon/
      [same structure]
    woodblock/
      [same structure]
  comparison_contact_sheet.png  ← all 10 results in one grid

---

## TASK 1 — Build the Batch Infrastructure

### 1A — Write run_cow_pipeline.sh

A parameterized single-image pipeline runner. Takes two arguments: image path
and speed (fast or normal). Handles all file management.

```bash
#!/bin/bash
# run_cow_pipeline.sh — Run one image through one pipeline speed
# Usage: bash run_cow_pipeline.sh "<image_path>" <speed>
# Example: bash run_cow_pipeline.sh "Final cows/ banknote.png" fast
set -e

IMAGE_PATH="$1"
SPEED="$2"
PROJECT="/Users/admin/causticsEngineering"

# Derive slug from filename (strip path, extension, spaces, leading space)
BASENAME=$(basename "$IMAGE_PATH")
SLUG=$(echo "$BASENAME" | sed 's/\.[^.]*$//' | sed 's/^[[:space:]]*//' | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

# Output directory for this image + speed
OUT_DIR="${PROJECT}/Final cows/${SLUG}/${SPEED}"
mkdir -p "$OUT_DIR"

echo "=== ${SLUG} | ${SPEED} | $(date) ==="
echo "Input:  $IMAGE_PATH"
echo "Output: $OUT_DIR"

# Set resolution based on speed
case "$SPEED" in
  fast)   JL_SCRIPT="run_fast.jl"   ;;
  normal) JL_SCRIPT="run_normal.jl"  ;;
  *)      echo "Unknown speed: $SPEED"; exit 1 ;;
esac

cd "$PROJECT"

# Backup production OBJ
cp examples/original_image.obj examples/original_image_PROD_BACKUP.obj

# Run Julia solver with this image as input
echo "Step 1: Julia solver (${SPEED})..."
T1=$(date +%s)
COW2_INPUT="$IMAGE_PATH" julia "$JL_SCRIPT" > "$OUT_DIR/run.log" 2>&1
T2=$(date +%s)
JULIA_TIME=$((T2-T1))
echo "  Julia: ${JULIA_TIME}s"

# Move solver output to subfolder, restore production OBJ
mv examples/original_image.obj "${OUT_DIR}/mesh.obj"
cp examples/original_image_PROD_BACKUP.obj examples/original_image.obj
echo "  Production OBJ restored."

# Run ray trace pointing at this subfolder's mesh
echo "Step 2: Ray trace..."
T3=$(date +%s)
python3 simulate_batch.py \
  --obj    "${OUT_DIR}/mesh.obj" \
  --accum  "${OUT_DIR}/accum.npy" \
  --meta   "${OUT_DIR}/meta.npy" \
  --output "${OUT_DIR}/caustic.png" \
  --label  "${SLUG} (${SPEED})" \
  >> "$OUT_DIR/run.log" 2>&1
T4=$(date +%s)
TRACE_TIME=$((T4-T3))
echo "  Ray trace: ${TRACE_TIME}s"

TOTAL=$((T4-T1))
echo "=== DONE: ${SLUG}/${SPEED} in ${TOTAL}s ==="
echo "TIMING: Julia=${JULIA_TIME}s RayTrace=${TRACE_TIME}s Total=${TOTAL}s" >> "$OUT_DIR/run.log"
```

### 1B — Write simulate_batch.py

A fully parameterized version of simulate_fast.py accepting CLI arguments.
This is the single ray trace script used for all 10 batch runs.
No hardcoded paths.

Arguments:
  --obj      path to mesh OBJ
  --accum    path for accum cache (.npy)
  --meta     path for meta cache (.npy)
  --output   path for output PNG
  --label    plot title string (e.g. "banknote (fast)")
  --passes   N_PASSES (default: 4)
  --focal    FOCAL_DIST (default: 0.75)
  --ior      IOR (default: 1.49)
  --res      IMAGE_RES output resolution (default: 512)

Physics:
  - Auto-sigma computed from actual face count after OBJ parse:
      sigma = 1.5 * sqrt(525000 / face_count)
      radius = max(2, int(round(sigma * 1.5)))
  - Print: face_count, sigma, radius, hit_rate to stdout (goes to run.log)
  - np.fliplr only for orientation (confirmed correct, no flipud)
  - Same sunlight colormap as all other simulate scripts
  - Cache logic: if accum+meta exist, skip simulation and replot only

### 1C — Write run_batch_all.sh

Interleaved execution: FAST then NORMAL per image, one image at a time.
This way results trickle in every ~3 min rather than waiting 65 min for
the first NORMAL output.

```bash
#!/bin/bash
# run_batch_all.sh — Run all Final Cows through FAST then NORMAL (interleaved)
set -e
PROJECT="/Users/admin/causticsEngineering"
cd "$PROJECT"

IMAGES=(
  "Final cows/ banknote.png"
  "Final cows/charcol.png"
  "Final cows/inkbrush.png"
  "Final cows/Nikon.png"
  "Final cows/woodblock.png"
)

TOTAL_START=$(date +%s)
echo "=== BATCH START: $(date) ==="
echo "5 images x 2 speeds = 10 runs (~80 min total)"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

for IMAGE in "${IMAGES[@]}"; do
  BASENAME=$(basename "$IMAGE")
  SLUG=$(echo "$BASENAME" | sed 's/\.[^.]*$//' | sed 's/^[[:space:]]*//' | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

  echo "══════════════════════════════════════════"
  echo " $SLUG"
  echo "══════════════════════════════════════════"

  for SPEED in fast normal; do
    if bash run_cow_pipeline.sh "$IMAGE" "$SPEED"; then
      PASS_COUNT=$((PASS_COUNT + 1))
      echo "  ✓ ${SLUG}/${SPEED}"
    else
      FAIL_COUNT=$((FAIL_COUNT + 1))
      echo "  ✗ ${SLUG}/${SPEED} FAILED — check Final cows/${SLUG}/${SPEED}/run.log"
    fi
    echo ""
  done
done

TOTAL_END=$(date +%s)
ELAPSED=$((TOTAL_END - TOTAL_START))

echo "══════════════════════════════════════════"
echo " BATCH COMPLETE: $(date)"
echo " Elapsed: ${ELAPSED}s ($(( ELAPSED/60 ))min)"
echo " Passed: ${PASS_COUNT}/10  Failed: ${FAIL_COUNT}/10"
echo "══════════════════════════════════════════"
echo ""
echo "Results: Final cows/<slug>/<speed>/caustic.png"
```

---

## TASK 2 — Create Output Subfolders

Create all 10 output directories before any run:
  Final cows/banknote/fast/
  Final cows/banknote/normal/
  Final cows/charcol/fast/
  Final cows/charcol/normal/
  Final cows/inkbrush/fast/
  Final cows/inkbrush/normal/
  Final cows/nikon/fast/
  Final cows/nikon/normal/
  Final cows/woodblock/fast/
  Final cows/woodblock/normal/

---

## TASK 3 — Verify Inputs

Run verify_final_cows.py before any Julia job fires. Check:
  - Readable
  - nonzero pixel % (flag if < 5% or > 95% — would produce flat output)
  - Dimensions (note if not square — run_*.jl will resize anyway)
  - Mode (RGB vs grayscale — Julia converts to grayscale internally)

Do not modify any image. Report findings only.
Proceed with the batch regardless of findings unless an image is unreadable.

---

## TASK 4 — After All Runs Complete

### 4A — Build comparison contact sheet

Write and run build_contact_sheet.py:
  - 5 rows (one per image) × 2 columns (fast | normal)
  - Label each panel: slug, speed, total time from run.log
  - Black background, white labels, amber accent (#FFC040)
  - Save full-res as: Final cows/comparison_contact_sheet.png
  - Save < 900KB JPEG as: claude_chat_handoff4/N_contact_sheet.jpg
    (this is what Claude Chat will review)

### 4B — Timing summary table

Print to terminal and append to a new file Final cows/BATCH_SUMMARY.md:
  Image     | FAST time | FAST faces | FAST sigma | NORMAL time | NORMAL faces | NORMAL sigma
  banknote  | ...       | ...        | ...        | ...         | ...          | ...
  ...

Extract from run.log files (TIMING: line and sigma printed by simulate_batch.py).

### 4C — Write claude_chat_handoff4/BATCH_READY_FOR_REVIEW.md

Include:
  - Pass/fail summary
  - Timing table
  - Instruction: "Upload N_contact_sheet.jpg to Claude Chat for visual ranking"
  - Ask Claude Chat to:
      1. Rank all 5 treatments from most to least compelling caustic
      2. Identify which speed (fast vs normal) shows meaningful quality difference
      3. Flag any render that looks like it has a physics error (flat, washed, doubled)
      4. Recommend top 1-2 treatments to run at production (1024px)

---

## EXECUTION ORDER — FULLY AUTONOMOUS

Run all of this without stopping for confirmation:

  1. Task 2 — mkdir all output dirs
  2. Task 3 — verify_final_cows.py (run it, report results, continue regardless)
  3. Task 1A — write run_cow_pipeline.sh
  4. Task 1B — write simulate_batch.py
  5. Task 1C — write run_batch_all.sh
  6. git commit "batch pipeline infrastructure + Final cows ready"
  7. Run run_batch_all.sh — all 10 jobs, fully autonomous, ~80 min
  8. Task 4A — build_contact_sheet.py (run after batch completes)
  9. Task 4B — BATCH_SUMMARY.md
  10. Task 4C — BATCH_READY_FOR_REVIEW.md
  11. git commit "Final cows batch complete — all 10 renders"
  12. Report to user: timing summary + paste prompt for Claude Chat

---

## HARD CONSTRAINTS (unchanged)

  NEVER:
    - Modify any file in "Final cows/" (the 5 input PNGs)
    - Run two Julia jobs simultaneously
    - Delete examples/original_image.obj without backup/restore

  AUTO-ACCEPT EVERYTHING ELSE including:
    - All Julia solver runs (pre-approved for this batch)
    - run_batch_all.sh
    - All 10 run_cow_pipeline.sh calls
    - All script writes, directory creation, git commits

  CONFIRM REQUIRED (⚠ SUPER CRITICAL) — only:
    - Editing create_mesh.jl focalLength or artifactSize
    - Any operation outside /Users/admin/causticsEngineering/
