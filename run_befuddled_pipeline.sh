#!/bin/bash
# run_befuddled_pipeline.sh
# Full autonomous pipeline: Julia solver → OBJ verify → ray trace →
# physical scaling → analysis → git commit
# All output is tee'd to logs/ so nothing is lost.
#
# NOTE: Step 6 (Julia solver) uses start_julia.sh for background launch + logging.
#       After launching, wait for it to finish before continuing.
set -e   # exit on any error

cd /Users/admin/causticsEngineering
LOGS=./logs
mkdir -p "$LOGS"

echo_ts() { echo "[$(date '+%H:%M:%S')] $*"; }

echo_ts "═══ BEFUDDLED COW PIPELINE START ═══"

# ── Step 6: Julia solver ──────────────────────────────────────────────────────
echo_ts "Step 6: Launching Julia solver via start_julia.sh (background, ~45 min for 1024px)..."
bash start_julia.sh
echo_ts "Waiting for Julia solver to complete..."
while bash check_julia.sh; do sleep 30; done
echo_ts "Step 6 complete."

# ── Step 7: Verify OBJ ───────────────────────────────────────────────────────
echo_ts "Step 7: Verifying OBJ geometry..."
python3 verify_obj.py 2>&1 | tee "$LOGS/verify_obj.log"
echo_ts "Step 7 complete."

# ── Step 9: Forward ray trace ────────────────────────────────────────────────
echo_ts "Step 9: Running forward ray trace (4-pass, ~35 min)..."
python3 simulate_befuddled_v5.py 2>&1 | tee "$LOGS/raytrace_befuddled.log"
echo_ts "Step 9 complete."

# ── Step 10: Physical lens scaling ───────────────────────────────────────────
echo_ts "Step 10: Running make_physical_lens.py..."
python3 make_physical_lens.py 2>&1 | tee "$LOGS/physical_lens.log"
echo_ts "Step 10 complete."

# ── Step 11: Analysis ────────────────────────────────────────────────────────
echo_ts "Step 11: Running comparative analysis..."
python3 analyze_befuddled.py 2>&1 | tee "$LOGS/analysis_befuddled.log"
echo_ts "Step 11 complete."

# ── Step 12: Git commit ───────────────────────────────────────────────────────
echo_ts "Step 12: Committing results..."
git add -A
git commit -m "befuddled cow v1: option-A input, 4-pass splat, 8x8 physical"
echo_ts "Step 12 complete."

echo_ts "═══ PIPELINE COMPLETE ═══"
echo_ts "Outputs:"
echo_ts "  examples/caustic_befuddled_v1.png"
echo_ts "  examples/befuddled_analysis_v1.png"
echo_ts "  examples/physical_lens_8x8.obj"
echo_ts "  HANDOFF_BEFUDDLED_v1.md"
echo_ts "  logs/*.log"
