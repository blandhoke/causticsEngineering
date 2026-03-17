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

# Set Julia script based on speed
case "$SPEED" in
  fast)   JL_SCRIPT="run_fast.jl"   ;;
  normal) JL_SCRIPT="run_normal.jl"  ;;
  prod)   JL_SCRIPT="run_prod.jl"    ;;
  *)      echo "Unknown speed: $SPEED"; exit 1 ;;
esac

cd "$PROJECT"

# Backup production OBJ
cp examples/original_image.obj examples/original_image_PROD_BACKUP.obj

# Run Julia solver
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

# Run ray trace
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
