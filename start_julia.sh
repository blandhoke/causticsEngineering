#!/usr/bin/env bash
# start_julia.sh — Safe background launcher for julia run.jl
#
# Safety checks:  uncommitted changes, stale PID, OBJ backup
# Logging:        nohup → logs/julia_TIMESTAMP.log + symlink julia_current.log
# Monitor with:   bash check_julia.sh
# Tail live:      tail -f logs/julia_current.log

set -euo pipefail

PROJECT_DIR="/Users/admin/causticsEngineering"
LOGS_DIR="${PROJECT_DIR}/logs"
PID_FILE="${LOGS_DIR}/julia.pid"
SYMLINK="${LOGS_DIR}/julia_current.log"

cd "${PROJECT_DIR}"

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
echo "Starting julia run.jl in background..."
nohup julia run.jl > "${LOG_FILE}" 2>&1 &
JULIA_PID=$!
echo "${JULIA_PID}" > "${PID_FILE}"

echo "  PID:     ${JULIA_PID}"
echo "  Log:     ${LOG_FILE}"
echo "  Symlink: ${SYMLINK}"
echo ""
echo "Monitor:  bash check_julia.sh"
echo "Tail:     tail -f ${SYMLINK}"
