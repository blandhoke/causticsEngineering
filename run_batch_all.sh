#!/bin/bash
# run_batch_all.sh — Run all Final Cows through FAST then NORMAL (interleaved)
# 5 images x 2 speeds = 10 runs (~80 min total)
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
echo "5 images x 2 speeds = 10 runs"
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
