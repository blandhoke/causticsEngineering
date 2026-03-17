#!/bin/bash
# run_pipeline_fast.sh — FAST pipeline (256px, ~131k faces, ~3 min total)
# DO NOT run autonomously. Requires ⚠ THIS IS SUPER CRITICAL ⚠ confirmation.
set -e

SPEED=fast
RES=256
INPUT=${COW2_INPUT:-./examples/befuddled_cow_solver_input.jpg}

echo "=== FAST PIPELINE | ${RES}px | input: $INPUT ==="
echo "Backing up production OBJ..."
cp examples/original_image.obj examples/original_image_PROD_BACKUP.obj

T1=$(date +%s)
echo "Running Julia solver at ${RES}px..."
COW2_INPUT="$INPUT" julia run_fast.jl
T2=$(date +%s)

echo "Preserving fast mesh..."
mv examples/original_image.obj examples/original_image_fast.obj
echo "Restoring production OBJ..."
cp examples/original_image_PROD_BACKUP.obj examples/original_image.obj

echo "Running ray trace..."
T3=$(date +%s)
python3 simulate_fast.py
T4=$(date +%s)

echo ""
echo "=== FAST COMPLETE ==="
echo "Julia: $((T2-T1))s | Ray trace: $((T4-T3))s | Total: $((T4-T1))s"
echo "Output: examples/caustic_fast.png"
echo "Mesh:   examples/original_image_fast.obj"
