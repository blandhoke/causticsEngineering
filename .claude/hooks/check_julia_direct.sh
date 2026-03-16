#!/usr/bin/env bash
# PreToolUse hook — intercepts direct "julia run.jl" calls.
#
# Blocks execution if the user or Claude tries to run julia run.jl directly
# instead of going through start_julia.sh, which provides:
#   - git safety check (no uncommitted changes)
#   - OBJ backup
#   - background nohup logging
#   - PID file for check_julia.sh monitoring
#
# Claude Code passes tool input as JSON on stdin.
# Exit 2 = block the tool call and show this script's output to Claude.

INPUT=$(cat)

# Extract the bash command from the JSON input
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # tool_input is nested under the input key
    ti = d.get('tool_input', d)
    print(ti.get('command', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# Check if this is a direct julia run.jl invocation
# Allow if it's coming from start_julia.sh itself (nohup call)
if echo "$COMMAND" | grep -qE "julia run\.jl" && \
   ! echo "$COMMAND" | grep -qE "nohup julia run\.jl|start_julia\.sh"; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  BLOCKED: Direct julia run.jl call intercepted       ║"
    echo "╠══════════════════════════════════════════════════════╣"
    echo "║  Use:  bash start_julia.sh                           ║"
    echo "║                                                      ║"
    echo "║  start_julia.sh provides:                            ║"
    echo "║    ✓ Blocks if uncommitted changes exist             ║"
    echo "║    ✓ Blocks if solver already running                ║"
    echo "║    ✓ Backs up original_image.obj automatically       ║"
    echo "║    ✓ Logs to logs/julia_TIMESTAMP.log                ║"
    echo "║    ✓ Enables check_julia.sh progress monitoring      ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    exit 2
fi

exit 0
