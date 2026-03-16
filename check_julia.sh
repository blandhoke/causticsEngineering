#!/usr/bin/env bash
# check_julia.sh — Parse running Julia solver log and report progress
# Usage: bash check_julia.sh
# Call repeatedly to poll status. Returns 0 while running, 1 when done/crashed.

PROJECT_DIR="/Users/admin/causticsEngineering"
LOGS_DIR="${PROJECT_DIR}/logs"
PID_FILE="${LOGS_DIR}/julia.pid"
SYMLINK="${LOGS_DIR}/julia_current.log"

# ── Resolve log file ──────────────────────────────────────────────────────────
if [[ -L "${SYMLINK}" ]] && [[ -f "${SYMLINK}" ]]; then
    LOG_FILE=$(readlink "${SYMLINK}")
else
    echo "No active log at ${SYMLINK}"
    exit 1
fi

# ── Process status ────────────────────────────────────────────────────────────
RUNNING=0
if [[ -f "${PID_FILE}" ]]; then
    PID=$(cat "${PID_FILE}")
    if kill -0 "${PID}" 2>/dev/null; then
        RUNNING=1
        STATUS="RUNNING (PID ${PID})"
    else
        STATUS="FINISHED/CRASHED (PID ${PID})"
    fi
else
    STATUS="NO PID FILE"
fi

# ── Iteration progress via loss PNG files (most reliable) ────────────────────
# loss_itN.png is written at the START of each oneIteration() call, before
# "Building Phi" is printed — making it a reliable ahead-of-log indicator.
LAST_IT=0
for i in 1 2 3 4 5 6; do
    [[ -f "${PROJECT_DIR}/examples/loss_it${i}.png" ]] && LAST_IT=$i || break
done

# ── Phase detection via log markers ──────────────────────────────────────────
PHI_COUNT=$(grep -c "^Building Phi$"           "${LOG_FILE}" 2>/dev/null || echo 0)
MINT_COUNT=$(grep -c "^Overall min_t:"         "${LOG_FILE}" 2>/dev/null || echo 0)
HAS_DIVERG=$(grep -c "^Have all the divergences$" "${LOG_FILE}" 2>/dev/null || echo 0)
CONV_COUNT=$(grep -c "^Convergence reached"    "${LOG_FILE}" 2>/dev/null || echo 0)
HAS_SPECS=$(grep -c  "^Specs:"                 "${LOG_FILE}" 2>/dev/null || echo 0)
HAS_FILLED=$(grep -c "^We've filled up 4194304" "${LOG_FILE}" 2>/dev/null || echo 0)

# ── Determine phase label ─────────────────────────────────────────────────────
if [[ "${HAS_FILLED}" -gt 0 ]]; then
    PHASE="solidify/saveObj COMPLETE"
    PCT=100
elif [[ "${HAS_SPECS}" -gt 0 ]]; then
    PHASE="Writing OBJ mesh"
    PCT=96
elif [[ "${HAS_DIVERG}" -gt 0 ]] && [[ "${CONV_COUNT}" -ge 7 ]]; then
    PHASE="findSurface converged — solidifying"
    PCT=90
elif [[ "${HAS_DIVERG}" -gt 0 ]]; then
    PHASE="findSurface — height field SOR running"
    PCT=$(( 72 + CONV_COUNT ))
elif [[ "${MINT_COUNT}" -ge 6 ]]; then
    PHASE="it6 complete — computing surface"
    PCT=72
elif [[ "${PHI_COUNT}" -gt 0 ]]; then
    # Active iteration: PHI_COUNT = current iter number
    ITER_PCT=$(( (MINT_COUNT * 12) ))
    PCT=$(( ITER_PCT + 6 ))   # +6 for in-progress iter
    if [[ "${MINT_COUNT}" -lt "${PHI_COUNT}" ]]; then
        PHASE="it${PHI_COUNT} — Building Phi (SOR running)"
    else
        PHASE="it${PHI_COUNT} — SOR converged, marching mesh"
    fi
elif grep -q "Activating project\|Precompiling" "${LOG_FILE}" 2>/dev/null; then
    PHASE="Precompiling Julia packages"
    PCT=2
else
    PHASE="Starting"
    PCT=0
fi

# ── Last convergence value ────────────────────────────────────────────────────
# Matches bare float lines: 46.491..., 0.00366..., 9.99e-6, etc.
LAST_CONV=$(grep -E "^-?[0-9]+(\.[0-9]+)?(e[+-]?[0-9]+)?$" \
    "${LOG_FILE}" 2>/dev/null | tail -1 || echo "N/A")

# ── Elapsed time ──────────────────────────────────────────────────────────────
# macOS stat: -f "%m"; Linux stat: -c "%Y"
LOG_MTIME=$(stat -f "%m" "${LOG_FILE}" 2>/dev/null || stat -c "%Y" "${LOG_FILE}" 2>/dev/null || echo 0)
# Use file creation via birth time if available, else fall back to mtime
# For simplicity use log filename timestamp (embedded in path)
FNAME=$(basename "${LOG_FILE}")                        # julia_20260316_143022.log
TS_STR=$(echo "${FNAME}" | grep -oE "[0-9]{8}_[0-9]{6}" || echo "")
if [[ -n "${TS_STR}" ]]; then
    START_SEC=$(date -j -f "%Y%m%d_%H%M%S" "${TS_STR}" "+%s" 2>/dev/null \
             || date -d "${TS_STR:0:8} ${TS_STR:9:2}:${TS_STR:11:2}:${TS_STR:13:2}" "+%s" 2>/dev/null \
             || echo 0)
else
    START_SEC=0
fi
NOW=$(date +%s)
ELAPSED=$(( NOW - START_SEC ))
ELAPSED_HMS=$(printf "%02d:%02d:%02d" $((ELAPSED/3600)) $(( (ELAPSED%3600)/60 )) $((ELAPSED%60)) )

# ── Progress bar ──────────────────────────────────────────────────────────────
BAR_LEN=30
FILLED=$(( PCT * BAR_LEN / 100 ))
BAR=$(printf '%0.s█' $(seq 1 ${FILLED} 2>/dev/null) 2>/dev/null || printf '%.0s#' $(seq 1 ${FILLED}))
EMPTY=$(printf '%0.s░' $(seq 1 $(( BAR_LEN - FILLED )) 2>/dev/null) 2>/dev/null || printf '%.0s-' $(seq 1 $(( BAR_LEN - FILLED ))))

# ── Error check ───────────────────────────────────────────────────────────────
ERRORS=$(grep -i "MAX UPDATE WAS NaN\|ERROR\|Exception\|error in" \
    "${LOG_FILE}" 2>/dev/null | grep -v "^#\|precompil" | head -3 || echo "")

# ── Report ────────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════════════"
echo " Julia Solver — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════"
printf " Status:   %s\n" "${STATUS}"
printf " Elapsed:  %s\n" "${ELAPSED_HMS}"
printf " Progress: [%s%s] %d%%\n" "${BAR}" "${EMPTY}" "${PCT}"
printf " Phase:    %s\n" "${PHASE}"
printf " Last val: %s\n" "${LAST_CONV}"
echo ""
printf " Iterations (loss PNGs): "
for i in 1 2 3 4 5 6; do
    if [[ -f "${PROJECT_DIR}/examples/loss_it${i}.png" ]]; then
        printf "it%d✓ " $i
    else
        printf "it%d… " $i
    fi
done
echo ""
echo ""
echo " ── Last 5 log lines ─────────────────────────"
tail -5 "${LOG_FILE}" 2>/dev/null | sed 's/^/   /'
echo "════════════════════════════════════════════════"

if [[ -n "${ERRORS}" ]]; then
    echo ""
    echo " ⚠  ERRORS DETECTED:"
    echo "${ERRORS}" | sed 's/^/   /'
    echo "════════════════════════════════════════════════"
fi

# Return 0 if still running, 1 if done/crashed
[[ "${RUNNING}" -eq 1 ]] && exit 0 || exit 1
