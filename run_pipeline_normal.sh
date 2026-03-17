#!/bin/bash
# run_pipeline_normal.sh — NORMAL pipeline (512px, ~525k faces, ~13 min total)
# DO NOT run autonomously. Requires ⚠ THIS IS SUPER CRITICAL ⚠ confirmation.
set -e

SPEED=normal
RES=512
INPUT=${COW2_INPUT:-./examples/befuddled_cow_solver_input.jpg}

echo "=== NORMAL PIPELINE | ${RES}px | input: $INPUT ==="
echo "Backing up production OBJ..."
cp examples/original_image.obj examples/original_image_PROD_BACKUP.obj

T1=$(date +%s)
echo "Running Julia solver at ${RES}px..."
COW2_INPUT="$INPUT" julia run_normal.jl
T2=$(date +%s)

echo "Preserving normal mesh..."
mv examples/original_image.obj examples/original_image_normal.obj
echo "Restoring production OBJ..."
cp examples/original_image_PROD_BACKUP.obj examples/original_image.obj

echo "Running ray trace..."
T3=$(date +%s)
python3 simulate_normal.py
T4=$(date +%s)

echo ""
echo "=== NORMAL COMPLETE ==="
echo "Julia: $((T2-T1))s | Ray trace: $((T4-T3))s | Total: $((T4-T1))s"
echo "Output: examples/caustic_normal.png"
echo "Mesh:   examples/original_image_normal.obj"
