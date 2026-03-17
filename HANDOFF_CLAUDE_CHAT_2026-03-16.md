# CausticsEngineering — Handoff to Claude Chat
# Date: 2026-03-16
# From: Claude Code (terminal session)
# To: Claude Chat (desktop/browser)
# Topic: Session wrap-up + pipeline ready to run + project infrastructure complete

---

## What Just Happened (This Session)

This was a pure infrastructure and tuning session — no Julia runs, no ray traces.
Everything is committed and clean. The pipeline is staged and ready to execute.

### What Was Built or Fixed

1. **Global Claude Code config** — `~/.claude/CLAUDE.md` created with universal rules:
   subagent strategy, scratchpad planning, proactive compaction, idea signals,
   autonomous commits, hooks-first approach. Applies to every project on this machine.

2. **Permission system consolidated** — `.claude/settings.local.json` is now the
   single source of truth. `.claude/settings.json` is hooks-only. No more conflicting
   rules causing permission prompts.

3. **simulate_befuddled.py hardened** — raises RuntimeError immediately if run.
   Prevents accidental use of the broken FOCAL_DIST=0.2 script that caused v4 failure.

4. **run_befuddled_pipeline.sh fixed** — now uses `start_julia.sh` (hook-compliant)
   and `simulate_befuddled_v5.py` (correct physics). Was referencing both wrong.

5. **CLAUDE.md fully documented** — every file in `examples/` is now listed and
   explained. Input image strategy section retitled "Active Research."

6. **CLAUDE_CODE_FIELD_GUIDE.md** — shareable best-practices document written for
   Leslie King. Lives in project root. Safe to share (won't collide with her CLAUDE.md).

7. **Memory system updated** — 6 memory files covering user profile, focal calibration,
   pipeline workflow, known pitfalls, confirmation format, and global rules.

---

## Current Pipeline State

**Git:** 3 commits ahead of origin/main. Clean working tree.
**Active solver input:** `examples/befuddled_cow_solver_input.jpg` (Option A — Gaussian blur)
**Active script:** `simulate_befuddled_v5.py` (FOCAL_DIST=0.75, sigma=0.75)
**Last good render:** `caustic_befuddled_v5.png` (current best)
**Physical output:** `physical_lens_8x8.obj` (dome 25.22mm, 8"x8", throw 30")

**Nothing has been run this session.** The pipeline is idle and ready.

---

## What Comes Next (Pipeline Run)

The next Claude Code session should execute this sequence — in order, no skipping:

```
1. bash start_julia.sh
   ⚠ THIS IS SUPER CRITICAL ⚠ — overwrites original_image.obj, takes ~45 min
   Confirm before running. Check no other terminal is active.

2. bash check_julia.sh     ← poll every 30s; exits 1 when done

3. python3 verify_obj.py   ← validate dome height, face count, geometry

4. python3 simulate_befuddled_v5.py
   First run: full ray trace (~40 min, 4-pass, 1024px)
   Subsequent runs: loads cache, instant

5. python3 make_physical_lens.py
   Writes physical_lens_8x8.obj (CNC-ready, 8"x8" scaled)

6. Analysis + git commit + git push
```

---

## Active Research Question

The v5 render used **Option A** (Gaussian blur preprocessing). The physical CNC
test will determine whether Option A produces a better result than v3 (cow).

The three strategies being evaluated:
- **Option A** (current) — Gaussian blur softens edges, broader energy spread
- **Option B** (untested) — Sobel edge map as input, explicit edge encoding
- **Option C** (untested) — Pure white silhouette, all energy inside cow shape

The physical test result should inform which option to run next.

---

## Key Parameters (Do Not Change Without Confirming)

| Parameter | Value | Location |
|-----------|-------|----------|
| focalLength | 0.75m | src/create_mesh.jl |
| FOCAL_DIST | 0.75 | simulate_befuddled_v5.py |
| SPLAT_SIGMA | 0.75 | simulate_befuddled_v5.py |
| IOR | 1.49 | both files |
| Grid | 1024px input → ~2.1M face mesh | run.jl |
| Physical dome | 25.22mm | verify_obj.py output |
| Physical throw | 762mm / 30" | make_physical_lens.py |

FOCAL_DIST and focalLength **must always match.** Mismatch was the root cause
of the entire v4 failure. A PostToolUse hook now checks this automatically.

---

## Infrastructure Notes for Claude Chat

- **Two-terminal workflow is unchanged:** Claude Chat = research + Blender MCP.
  Claude Code = all execution, file writes, git.
- **CLAUDE_CODE_FIELD_GUIDE.md** is ready to send to Leslie King as a PDF or
  paste. Do not send the project CLAUDE.md — that's internal.
- **No Blender Cycles for caustic verification** — neither Cycles nor LuxCore
  converges on caustics. The Python ray tracer is the only reliable verification.
- **New global rules are live** — future Claude Code sessions will auto-commit,
  plan before acting, and use subagents for parallel work without being asked.

---

## Files Claude Chat Should Know About

```
CLAUDE.md                          ← full project reference (519 lines)
~/.claude/CLAUDE.md                ← global behavioral rules (new this session)
CLAUDE_CODE_FIELD_GUIDE.md         ← shareable protips document for Leslie
examples/caustic_befuddled_v5.png  ← current best render
examples/physical_lens_8x8.obj     ← current CNC file
src/create_mesh.jl                 ← CONFIRM REQUIRED before any edit
simulate_befuddled_v5.py           ← active ray trace script
```

---

## One Open Question for Claude Chat

The dome height at f=0.75 is 25.22mm with only 0.18mm margin in 1" acrylic.
If the physical test shows the lens needs refinement (dome too deep or too shallow),
the next round should consider whether to:
- Adjust focalLength (changes dome AND throw distance)
- Source 1.125" acrylic stock (eliminates the margin problem entirely)

This is a physical test decision — Claude Chat can help reason about it once
the CNC results come back.

---
*Handoff written by Claude Code — 2026-03-16*
*Next action: /compact this session, then start pipeline in fresh Claude Code session*
