#!/usr/bin/env bash
# run_quad_pipeline.sh — Run ONE quadrant through the full HYPER pipeline.
#
# Usage: bash run_quad_pipeline.sh LABEL PREPROCESSED_INPUT_PNG QUAD_OUTPUT_DIR
#
# Steps:
#   1. Copy preprocessed PNG to examples/quad_input_${LABEL}.png
#   2. Run Julia solver (run_hyper.jl) via start_julia_quad.sh
#   3. Poll completion every 20s
#   4. Copy examples/original_image.obj → ${QUAD_OUTPUT_DIR}/${LABEL}_hyper.obj
#   5-8. Post-processing steps run in parallel (geometry compare, Mitsuba render,
#        metrics, thumbnail) — all complete before script exits.
#
# Re-entrant: if ${QUAD_OUTPUT_DIR}/${LABEL}_hyper.obj already exists, steps 1-4
# are skipped and only post-processing is re-run.
#
# On Julia crash: writes ${QUAD_OUTPUT_DIR}/${LABEL}_error.txt and exits 1.

set -uo pipefail

LABEL="${1:?Usage: bash run_quad_pipeline.sh LABEL INPUT_PNG OUTPUT_DIR}"
INPUT_PNG="${2:?Missing INPUT_PNG}"
OUTPUT_DIR="${3:?Missing OUTPUT_DIR}"

PROJECT_DIR="/Users/admin/causticsEngineering"
BASELINE_OBJ="${PROJECT_DIR}/Final cows/inkbrush/normal/mesh.obj"
REFERENCE_CAUSTIC="${PROJECT_DIR}/luxcore_test/inkbrush_caustic_normal.png"
HANDOFF_DIR="${PROJECT_DIR}/claude_chat_handoff4"

export DRJIT_LIBLLVM_PATH="/usr/local/Cellar/llvm@16/16.0.6_1/lib/libLLVM-16.dylib"

mkdir -p "${OUTPUT_DIR}" "${HANDOFF_DIR}"

OBJ_DEST="${OUTPUT_DIR}/${LABEL}_hyper.obj"
ERROR_FILE="${OUTPUT_DIR}/${LABEL}_error.txt"

echo ""
echo "════════════════════════════════════════════════"
echo " Quad Pipeline: ${LABEL}"
echo "════════════════════════════════════════════════"
echo " Input:  ${INPUT_PNG}"
echo " Output: ${OUTPUT_DIR}"

# ── Re-entrancy check ─────────────────────────────────────────────────────────
if [[ -f "${OBJ_DEST}" ]]; then
    echo " OBJ exists — skipping Julia, running post-processing only."
else
    # ── Step 1: Copy input ────────────────────────────────────────────────────
    QUAD_INPUT="${PROJECT_DIR}/examples/quad_input_${LABEL}.png"
    cp "${INPUT_PNG}" "${QUAD_INPUT}"
    echo " Step 1: Input copied → ${QUAD_INPUT}"

    # ── Step 2-3: Run Julia solver ────────────────────────────────────────────
    T_START=$(date +%s)
    echo " Step 2: Starting Julia solver (${JL_SCRIPT:-run_hyper.jl})..."

    set +e
    COW2_INPUT="${QUAD_INPUT}" bash "${PROJECT_DIR}/start_julia_quad.sh" "${JL_SCRIPT:-run_hyper.jl}"
    LAUNCH_STATUS=$?
    set -e

    if [[ "${LAUNCH_STATUS}" -ne 0 ]]; then
        echo "ERROR: start_julia_quad.sh failed (exit ${LAUNCH_STATUS})" | tee "${ERROR_FILE}"
        exit 1
    fi

    # Read the PID that was just written
    JULIA_PID=$(cat "${PROJECT_DIR}/logs/julia.pid" 2>/dev/null || echo "")
    if [[ -z "${JULIA_PID}" ]]; then
        echo "ERROR: No Julia PID file found after launch" | tee "${ERROR_FILE}"
        exit 1
    fi

    echo " Step 3: Polling Julia (PID ${JULIA_PID}) every 20s..."
    sleep 5
    while kill -0 "${JULIA_PID}" 2>/dev/null; do
        sleep 20
    done

    T_ELAPSED=$(( $(date +%s) - T_START ))
    echo " Step 3: Julia finished in ${T_ELAPSED}s"

    # ── Step 4: Copy OBJ ─────────────────────────────────────────────────────
    SRC_OBJ="${PROJECT_DIR}/examples/original_image.obj"
    if [[ ! -f "${SRC_OBJ}" ]]; then
        echo "ERROR: ${SRC_OBJ} not found after Julia run" | tee "${ERROR_FILE}"
        exit 1
    fi

    # Verify the OBJ has content (not empty/truncated)
    OBJ_LINES=$(wc -l < "${SRC_OBJ}" 2>/dev/null || echo 0)
    if [[ "${OBJ_LINES}" -lt 1000 ]]; then
        echo "ERROR: ${SRC_OBJ} looks truncated (only ${OBJ_LINES} lines)" | tee "${ERROR_FILE}"
        exit 1
    fi

    cp "${SRC_OBJ}" "${OBJ_DEST}"
    echo " Step 4: OBJ saved → ${OBJ_DEST}  (${OBJ_LINES} lines)"
fi

# ── Steps 5-8: Post-processing (parallel within this block) ──────────────────
echo " Steps 5-8: Starting post-processing..."
T_POST=$(date +%s)

# Step 5: Geometry compare (background)
(
    python3 "${PROJECT_DIR}/compare_obj_geometry.py" \
        --a "${OBJ_DEST}" \
        --b "${BASELINE_OBJ}" \
        --label-a "${LABEL} HYPER" \
        --label-b "inkbrush NORMAL baseline" \
        --out-png "${OUTPUT_DIR}/${LABEL}_geometry.png" \
        --out-txt "${OUTPUT_DIR}/${LABEL}_geometry.txt" \
        2>&1 | tail -20
    echo " [${LABEL}] Geometry compare done"
) &
PID_GEOM=$!

# Step 6: Mitsuba render (background)
(
    python3 "${PROJECT_DIR}/render_any_obj.py" \
        --obj "${OBJ_DEST}" \
        --out "${OUTPUT_DIR}/${LABEL}_render.png" \
        --spp 128 --res 128 \
        2>&1 | tail -10
    echo " [${LABEL}] Mitsuba render done"
) &
PID_RENDER=$!

# Wait for render (metrics and thumbnail need it)
wait "${PID_RENDER}" 2>/dev/null || true

# Step 7: Metrics
if [[ -f "${OUTPUT_DIR}/${LABEL}_render.png" ]]; then
    python3 "${PROJECT_DIR}/compute_metrics.py" \
        --caustic "${OUTPUT_DIR}/${LABEL}_render.png" \
        --reference "${REFERENCE_CAUSTIC}" \
        --label "${LABEL}" \
        --out "${OUTPUT_DIR}/${LABEL}_metrics.json" \
        2>&1 | tail -8 || true
    echo " [${LABEL}] Metrics done"
else
    echo " [${LABEL}] WARNING: render not found, skipping metrics"
fi

# Step 8: Thumbnail
if [[ -f "${OUTPUT_DIR}/${LABEL}_render.png" ]]; then
    python3 "${PROJECT_DIR}/cc_resize.py" \
        "${OUTPUT_DIR}/${LABEL}_render.png" \
        --out "${HANDOFF_DIR}/${LABEL}_thumb.png" \
        2>&1 || true
    echo " [${LABEL}] Thumbnail done"
fi

# Wait for geometry compare to finish
wait "${PID_GEOM}" 2>/dev/null || true

T_POST_ELAPSED=$(( $(date +%s) - T_POST ))
echo " Steps 5-8: Post-processing complete in ${T_POST_ELAPSED}s"
echo "════════════════════════════════════════════════"
