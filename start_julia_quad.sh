#!/usr/bin/env bash
# start_julia_quad.sh — Safe background launcher for quad-pipeline Julia runs.
#
# Usage: COW2_INPUT=./path/to/input.png bash start_julia_quad.sh run_hyper.jl
#
# Same safety checks as start_julia.sh but accepts:
#   $1 = Julia script to run (run_hyper.jl, run_fast.jl, run_normal.jl)
#   COW2_INPUT env var = input image path
#
# After completion, examples/original_image.obj contains the new mesh.
# The caller is responsible for copying it to the final destination.
#
# Monitor progress: bash check_julia.sh
# Tail live log:    tail -f logs/julia_current.log

set -euo pipefail

JL_SCRIPT="${1:-run_hyper.jl}"
PROJECT_DIR="/Users/admin/causticsEngineering"
LOGS_DIR="${PROJECT_DIR}/logs"
PID_FILE="${LOGS_DIR}/julia.pid"
SYMLINK="${LOGS_DIR}/julia_current.log"

cd "${PROJECT_DIR}"

# ── Validate COW2_INPUT ───────────────────────────────────────────────────────
if [[ -z "${COW2_INPUT:-}" ]]; then
    echo "ERROR: COW2_INPUT env var not set."
    echo "Usage: COW2_INPUT=./path/to/input.png bash start_julia_quad.sh run_hyper.jl"
    exit 1
fi

if [[ ! -f "${COW2_INPUT}" ]]; then
    echo "ERROR: COW2_INPUT file not found: ${COW2_INPUT}"
    exit 1
fi

if [[ ! -f "${PROJECT_DIR}/${JL_SCRIPT}" ]]; then
    echo "ERROR: Julia script not found: ${PROJECT_DIR}/${JL_SCRIPT}"
    exit 1
fi

# ── Safety 1: uncommitted tracked-file changes ────────────────────────────────
DIRTY=$(git status --porcelain | grep -v '^??' || true)
if [[ -n "${DIRTY}" ]]; then
    echo "ERROR: Uncommitted changes detected. Commit before running solver."
    echo ""
    echo "${DIRTY}"
    echo ""
    echo "Run:  git add -A && git commit -m 'pre-solver backup'"
    exit 1
fi

# ── Safety 2: solver already running ─────────────────────────────────────────
if [[ -f "${PID_FILE}" ]]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "ERROR: Julia solver already running (PID ${OLD_PID})."
        echo "Check:  bash check_julia.sh"
        exit 1
    else
        echo "Stale PID file (PID ${OLD_PID} not running) — cleaning up."
        rm -f "${PID_FILE}"
    fi
fi

# ── Safety 3: backup current OBJ ─────────────────────────────────────────────
OBJ="${PROJECT_DIR}/examples/original_image.obj"
BACKUP="${PROJECT_DIR}/examples/original_image_BACKUP.obj"
if [[ -f "${OBJ}" ]]; then
    cp "${OBJ}" "${BACKUP}"
    echo "OBJ backup → examples/original_image_BACKUP.obj"
fi

# ── Set up log ────────────────────────────────────────────────────────────────
mkdir -p "${LOGS_DIR}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="${LOGS_DIR}/julia_${TIMESTAMP}.log"
ln -sf "${LOG_FILE}" "${SYMLINK}"

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
echo "Starting ${JL_SCRIPT} in background..."
echo "  COW2_INPUT: ${COW2_INPUT}"
export COW2_INPUT
nohup julia "${JL_SCRIPT}" > "${LOG_FILE}" 2>&1 &
JULIA_PID=$!
echo "${JULIA_PID}" > "${PID_FILE}"

echo "  PID:     ${JULIA_PID}"
echo "  Log:     ${LOG_FILE}"
echo "  Symlink: ${SYMLINK}"
echo ""
echo "Monitor:  bash check_julia.sh"
echo "Tail:     tail -f ${SYMLINK}"
