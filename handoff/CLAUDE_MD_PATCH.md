
---

## Session Handoff Architecture (added 2026-04-08)

Three-layer system for cross-session continuity. Strict separation of concerns.

### 1. state.json — Machine-readable project state (single source of truth)

Lives in project root. Every session reads it first, updates it last.
Contains: solver status, physical parameters, pipeline status, blockers,
`next_session_task` (tells the next session what to do).
No prose, no ambiguity — just data.

### 2. CLAUDE.md — Project rules for Claude Code (this file)

Read at session start. Contains: what the project is, pipeline architecture,
physics model, autonomy rules, file conventions, guardrails.
This is the instruction manual for the executor.

### 3. handoff/HANDOFF_vNNN.md — Scoped session prompts (versioned)

One file per Claude Code session, numbered sequentially (v001, v002, ...).
Each contains: prior session log, what changed, specific tasks for this session,
hard constraints, and expected outcomes.
Claude Code reads the latest one after CLAUDE.md and state.json.

### The loop

1. Claude Chat reads state.json → decides what to do next
2. Claude Chat writes handoff/HANDOFF_vNNN.md with scoped tasks
3. Operator pastes prompt into Claude Code
4. Claude Code reads: CLAUDE.md → state.json → latest handoff → executes
5. Claude Code git commits at start and end of every session
6. Claude Code updates state.json with results
7. Operator reports results to Claude Chat
8. Claude Chat reads updated state.json → loop repeats

### Key rules

- Claude Chat = strategist (decides direction, never writes code)
- Claude Code = executor (writes code, never makes strategic decisions)
- state.json is the only thing that crosses session boundaries reliably
- Handoffs are versioned so you can trace full history
- Git commit at start and end of every CC session (rollback = one git revert)
- Physical parameters live in state.json, never hardcoded
- One track per session — don't combine unrelated tasks
- Read order at session start: CLAUDE.md → state.json → handoff/HANDOFF_vNNN.md (latest)

### Legacy handoff files (pre-architecture)

The loose HANDOFF_*.md files in the project root predate this system.
They are historical reference only. All new handoffs go in handoff/.
Do not create new handoff files in the project root.
