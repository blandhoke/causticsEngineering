#!/usr/bin/env bash
# PostToolUse hook — checks FOCAL_DIST / focalLength sync after file writes.
#
# This is the #1 source of silent bugs in this project:
#   create_mesh.jl  focalLength = X
#   simulate_*.py   FOCAL_DIST  = X  ← MUST MATCH or caustic is washed out
#
# Triggered after any Write tool call. Checks:
#   - If create_mesh.jl was written: compare its focalLength to all simulate_*.py
#   - If simulate_*.py was written:  compare its FOCAL_DIST to create_mesh.jl
#
# Prints a warning (does NOT block — this is PostToolUse). Exit 0 always.

PROJECT="/Users/admin/causticsEngineering"
MESH="$PROJECT/src/create_mesh.jl"

INPUT=$(cat)

# Extract the file path that was just written
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

[[ -z "$FILE_PATH" ]] && exit 0

# ── Helper: extract focalLength from create_mesh.jl ──────────────────────────
get_focal_length() {
    grep -E '^\s*focalLength\s*=' "$MESH" 2>/dev/null \
        | grep -v '^\s*#' \
        | head -1 \
        | grep -oE '[0-9]+(\.[0-9]+)?' \
        | head -1
}

# ── Helper: extract FOCAL_DIST from a simulate_*.py file ─────────────────────
get_focal_dist() {
    local pyfile="$1"
    grep -E '^\s*FOCAL_DIST\s*=' "$pyfile" 2>/dev/null \
        | grep -v '^\s*#' \
        | head -1 \
        | grep -oE '[0-9]+(\.[0-9]+)?' \
        | head -1
}

# ── Case 1: create_mesh.jl was written ───────────────────────────────────────
if echo "$FILE_PATH" | grep -q "create_mesh\.jl"; then
    FL=$(get_focal_length)
    [[ -z "$FL" ]] && exit 0

    MISMATCHES=()
    for pyfile in "$PROJECT"/simulate_*.py; do
        [[ -f "$pyfile" ]] || continue
        FD=$(get_focal_dist "$pyfile")
        [[ -z "$FD" ]] && continue
        if [[ "$FD" != "$FL" ]]; then
            MISMATCHES+=("$(basename $pyfile): FOCAL_DIST=$FD")
        fi
    done

    if [[ ${#MISMATCHES[@]} -gt 0 ]]; then
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  ⚠  FOCAL_DIST MISMATCH DETECTED                        ║"
        echo "╠══════════════════════════════════════════════════════════╣"
        echo "║  create_mesh.jl  focalLength = $FL"
        echo "║                                                          ║"
        echo "║  Mismatched simulate scripts:                            ║"
        for m in "${MISMATCHES[@]}"; do
            printf "║    ✗  %-50s║\n" "$m"
        done
        echo "║                                                          ║"
        echo "║  ACTION: Update FOCAL_DIST in the above script(s)       ║"
        echo "║  A mismatch causes washed-out flat caustic output.      ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        echo ""
    else
        echo ""
        echo "  ✓ FOCAL_DIST sync check: all simulate_*.py match focalLength=$FL"
        echo ""
    fi
fi

# ── Case 2: a simulate_*.py was written ──────────────────────────────────────
if echo "$FILE_PATH" | grep -qE "simulate_.*\.py"; then
    [[ -f "$MESH" ]] || exit 0
    FL=$(get_focal_length)
    FD=$(get_focal_dist "$FILE_PATH")

    [[ -z "$FL" || -z "$FD" ]] && exit 0

    if [[ "$FD" != "$FL" ]]; then
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  ⚠  FOCAL_DIST MISMATCH DETECTED                        ║"
        echo "╠══════════════════════════════════════════════════════════╣"
        printf "║  %-56s║\n" "$(basename $FILE_PATH)  FOCAL_DIST = $FD"
        printf "║  %-56s║\n" "create_mesh.jl          focalLength = $FL"
        echo "║                                                          ║"
        echo "║  These MUST match or the caustic will be washed out.    ║"
        echo "║  Root cause of v4 failure — do not repeat this bug.     ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        echo ""
    else
        echo ""
        echo "  ✓ FOCAL_DIST sync check: FOCAL_DIST=$FD matches focalLength=$FL"
        echo ""
    fi
fi

exit 0
