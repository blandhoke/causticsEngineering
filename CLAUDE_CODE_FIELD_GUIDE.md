# Claude Code Field Guide
### A Proposal for Getting Maximum Performance Out of Claude Code
*Prepared by Bland Hoke — based on real multi-session production experience*

---

## What This Is

This document is a distillation of hard-won lessons from running Claude Code as the
sole engineer on a physics-based caustic lens design pipeline. The project involves
Julia solvers, Python ray tracers, CNC output, and iterative physical testing — a
genuinely complex, multi-domain workflow where Claude Code handles all code, all
debugging, and all pipeline execution autonomously.

Everything here is field-tested. None of it is theoretical.

The goal is to help you configure Claude Code so it works *with* your thinking
rather than interrupting it — maximally autonomous, maximally exploratory, with
hard stops only where they genuinely matter.

---

## Part 1 — The Foundation: CLAUDE.md

### What It Is

`CLAUDE.md` is a plain text file that Claude Code reads at the start of every
session. It is your persistent instruction set — everything you would otherwise
have to re-explain every time. Claude treats it as binding.

### Two Levels

**Global** (`~/.claude/CLAUDE.md`) — applies to every project on your machine.
Put universal behavioral rules here: how you want Claude to communicate, when to
ask vs. act, commit message format, tool preferences.

**Project** (`/your/project/CLAUDE.md`) — applies only to that project.
Put domain knowledge here: physical parameters, file ownership rules, pipeline
sequence, what must never be overwritten.

Project rules override global rules where they conflict.

### What to Put In a Project CLAUDE.md

The best CLAUDE.md files are *discovered*, not written upfront. Start with:
- What the project does (one paragraph)
- Directory layout with annotations
- The 3-5 parameters that, if wrong, break everything
- What files must never be overwritten
- The pipeline sequence (step by step)
- What Claude should never do (hard limits)

Add to it whenever a bug surprises you. The CLAUDE.md becomes a living record
of every lesson the project has taught you.

---

## Part 2 — Autonomy Model

### The Core Principle

Asking a non-programmer to make technical decisions they cannot evaluate is not
caution — it is just friction. Configure Claude to default to action.

Divide all operations into three categories:

**JUST DO IT** — no confirmation, ever:
- File writes, edits, new scripts
- Running Python/analysis scripts
- Git add and commit
- Installing packages
- Reading anything

**ASK ONCE** — one confirmation, then proceed immediately:
- Operations that are slow AND destructive (e.g., a solver that takes 45 min
  and overwrites your only output file)
- Operations that touch files outside the project
- Changing a physical parameter that affects real-world output

**NEVER** — hard limits, no exceptions:
- Overwriting reference/baseline files
- Force-pushing to git
- Running destructive OS commands

### The Critical Confirmation Format

When an ASK ONCE situation arises, require Claude to signal it unmistakably.
The prompt must begin with:

```
⚠ THIS IS SUPER CRITICAL ⚠
[One sentence: what gets destroyed and why it cannot be undone.]
OK to proceed?
```

This matters because you may be running multiple terminals, multiple sessions,
or have background processes running. A buried question in a paragraph is easy
to misread. This format is impossible to miss.

Add this to your global CLAUDE.md as a universal rule.

---

## Part 3 — The Subagent Strategy (This Is the Big One)

### What Subagents Are

Claude Code can spawn sub-instances of itself — subagents — that work in
parallel on independent tasks. Each subagent gets its own context window and
runs simultaneously with the others. The main Claude orchestrates, collects
results, and acts on the synthesis.

From your perspective: you give Claude a goal, it disappears into parallel
exploration, and surfaces with a consolidated answer and recommended action.

### Depth and Width

Think of it as a tree, not a chain:

```
Depth 1 — Main Claude (1 instance)
  └── Depth 2 — Parallel subagents (as many as useful)
        └── Depth 3 — Sub-subagents (as many as each D2 agent needs)
```

- **Width is unlimited** at every level. Spawn as many as the problem needs.
- **Depth is capped at 3.** Beyond that, errors compound and results become
  unverifiable without a human checkpoint.
- **Only Depth 1 writes files, runs git, or executes destructive operations.**
  Depth 2 and 3 are research and analysis only.

### The Feedback Loop

Subagents don't automatically report back — the orchestration pattern must be
explicit. The rule:

1. Main Claude spawns all depth-2 agents simultaneously
2. Each agent returns: **findings**, **confidence level**, **recommended action**
3. Depth-2 agents collect their depth-3 results before reporting up
4. Main Claude synthesizes everything, then acts *once* with full information

### What to Use Subagents For

**Parallelizing routine work:**
- Reading 5 files simultaneously instead of sequentially
- Running multiple analysis scripts at once
- Searching the codebase from multiple angles in parallel

**Exploration and innovation:**
- Assign each depth-2 agent a different approach to the same problem
- Let depth-3 agents drill into physics, math, or algorithm details
- One agent explores the conservative solution; another explores the novel one
- Synthesize at depth-1 and choose the best-informed path

**Custom script development:**
- Subagent A: research the algorithm
- Subagent B: find existing implementations / prior art
- Subagent C: draft the script structure
- Main Claude: integrates findings, writes the final script

This is particularly powerful for developing custom Python tools for a new
analysis task you've never done before. Instead of one Claude thinking
sequentially, you get a research team thinking in parallel.

### Example Prompt Pattern

```
Explore three approaches to [problem]:
  Agent A: [approach 1]
  Agent B: [approach 2]
  Agent C: [approach 3]
Each agent returns: findings, limitations, recommended next step.
Synthesize and recommend the best path.
```

---

## Part 4 — Planning: Scratchpad First

Before executing any multi-step or irreversible task, require Claude to write
a visible plan first. This gives you a window to redirect before any work happens.

### Format

```
PLAN: [task name]
─────────────────
Goal: [one sentence]
Steps:
  1. ...
  2. ...
Risks: [what could go wrong]
Subagents: yes/no
Proceeding in 10 seconds unless redirected.
```

Short plans (≤4 steps): inline in the response.
Complex plans: temporary `PLAN_[task].md` file, deleted after completion.

The "proceeding unless redirected" pattern is key — it preserves autonomy
while giving you a chance to catch a wrong assumption before it propagates.

---

## Part 5 — Idea Signal Levels

Claude has no way to know whether you can evaluate a suggestion independently.
Require it to signal the significance of its proposals:

| Signal | Meaning |
|--------|---------|
| `straightforward fix` | Routine, expected — just do it |
| `worth noting` | Non-obvious but not surprising |
| `this is a better approach` | Meaningfully superior to what exists |
| `this is genuinely novel` | Creative, unexpected, high upside — pay attention |

This prevents every suggestion from feeling equally weighted and helps you
allocate your attention to the ideas that actually deserve it.

---

## Part 6 — Hooks: Structural Bug Prevention

Hooks are shell scripts that Claude Code runs automatically before or after
tool calls. They are the most underused feature in Claude Code.

**PreToolUse hooks** — run before a tool executes, can block it:
- Block a dangerous direct command and force users through a safer wrapper
- Intercept parameter-changing edits and warn before they apply
- Enforce "commit before running" rules

**PostToolUse hooks** — run after a tool executes, warning only:
- After writing a config file, check that dependent files are still in sync
- After a file write, verify a parameter that must match across multiple files
- After a git commit, check that no protected file was modified

### The Philosophy

Implement hooks *before* the bug happens, not after. The best hooks encode
lessons from real incidents — "this parameter was wrong in three files and we
didn't catch it until the output was completely broken."

Add a rule to your CLAUDE.md: at the start of any new project, Claude should
scan for hook opportunities and propose them before any pipeline runs.

### Hook Configuration

Hooks live in `.claude/settings.json` in your project:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "bash .claude/hooks/my_check.sh"}]
    }],
    "PostToolUse": [{
      "matcher": "Write",
      "hooks": [{"type": "command", "command": "bash .claude/hooks/sync_check.sh"}]
    }]
  }
}
```

Hook scripts receive tool input as JSON on stdin. Exit code 2 blocks the
operation and shows the script output. Exit code 0 allows it.

---

## Part 7 — Memory System

Claude Code has a persistent memory system at `~/.claude/projects/[project]/memory/`.
Memories are markdown files with frontmatter that load into future sessions.

### Memory Types

| Type | What it stores |
|------|---------------|
| `user` | Your role, expertise, preferences — how Claude should calibrate explanations |
| `feedback` | Corrections and guidance — rules that should survive session resets |
| `project` | Ongoing goals, deadlines, decisions not in the code |
| `reference` | Where things live in external systems |

### The Index

`MEMORY.md` in the memory directory is an index table. Claude reads it first
and loads relevant files. Keep it concise (under 200 lines).

### What to Memorize

- Feedback you've given that corrects a default behavior
- Parameters that have already caused production failures
- Your physical constraints (machine dimensions, material limits, etc.)
- Pipeline lessons that can't be derived from reading the code

### What NOT to Memorize

- Code patterns (read the code)
- Git history (use git log)
- Debugging solutions (the fix is in the code)
- Anything already in CLAUDE.md

---

## Part 8 — Version Control Discipline

### Commit Before Destruction

Any time Claude is about to run something that overwrites an important file,
it should commit first — automatically, without being asked. Add this to your
CLAUDE.md as a rule.

### Commit Message Format

The diff shows *what* changed. The commit message should explain *why*.

```
Bad:  "update focal length parameter"
Good: "set focalLength=0.75 — empirically optimal for 1\" acrylic at 30\" throw"
```

For non-trivial changes: subject line + blank line + body explaining the
decision, the context, and any breaking changes.

### GitHub CLI

Install `gh` and configure Claude to use it for all GitHub operations
(PRs, issues, checking CI). More reliable than constructing URLs manually.

```bash
brew install gh
gh auth login
```

---

## Part 9 — Proactive Compaction

Claude Code sessions have a context limit. When it fills, auto-compact fires
and the session history is summarized — potentially at an inconvenient moment
mid-pipeline.

Instead, require Claude to proactively suggest compacting at natural breakpoints:

```
Context checkpoint — good time to /compact before [next task]. Compact now?
```

Trigger conditions:
1. All current work is committed to git (clean stopping point)
2. The next task is large enough that a mid-task compaction would be disruptive
3. The session has been long (many tool calls, heavy file reads)

This is a soft suggestion, not a critical ask. It just prevents the auto-compact
from firing in the middle of a 45-minute solver run.

---

## Part 10 — Session Handoff

Before compacting or ending a session, require Claude to write a handoff file
summarizing the current state. This ensures the next session (or a second
Claude Chat instance) has everything it needs to continue without re-discovery.

**Handoff file format:**
```markdown
# HANDOFF_[context].md
## Current State
## What Was Just Completed
## What Comes Next
## Open Decisions / Deferred Questions
## Parameters in Play
```

These files are particularly valuable when you run Claude Code in one terminal
and Claude Chat (browser) in another — the handoff file is the bridge.

---

## Quick Reference: Global CLAUDE.md Template

```markdown
# CLAUDE.md — Global Defaults

## Response Style
- Terse and direct. Lead with the answer.
- No trailing summaries. No emoji unless asked.
- Reference code as file_path:line_number.

## Autonomy Default
Prefer action. Only stop for irreversible + high-blast-radius operations.

## Confirmation Format
Any irreversible operation prompt must begin with:
  ⚠ THIS IS SUPER CRITICAL ⚠
  [What gets destroyed and why it can't be undone.]
  OK to proceed?

## Version Control
- Commit before destructive operations.
- Never force-push without explicit instruction.
- Use gh for GitHub operations.
- Commit messages explain WHY, not what.

## Subagents
- Use for all parallelizable work.
- Depth limit: 3. Width: unlimited.
- Only Depth 1 writes files or runs git.
- Each agent returns: findings, confidence, recommended action.

## Planning
Write a scratchpad plan before any 3+ step or irreversible task.
Format: Goal / Steps / Risks / Subagents / Proceeding in 10s.

## Idea Signals
Rate proposals: "straightforward fix" / "worth noting" /
"this is a better approach" / "this is genuinely novel"

## Hooks
At project start, proactively identify PreToolUse and PostToolUse
hook opportunities. Implement before the first pipeline run.

## Self-Diagnosis at Session Start
Read CLAUDE.md + memory, check git status, report anomalies.
Own the code. Never hand a problem back to the user.
```

---

## A Note on Starting Small

You don't need all of this on day one. The highest-leverage items in order:

1. **Write a project CLAUDE.md** — even a rough one. It compounds immediately.
2. **Add the ⚠ THIS IS SUPER CRITICAL ⚠ rule** — prevents the worst accidents.
3. **Start using subagents for parallel file reads** — smallest win, immediate payoff.
4. **Add one hook** for the parameter or file that has already burned you once.
5. **Set up the memory system** — becomes valuable after the second session.

Everything else follows naturally once those five are in place.

---

*This document was assembled from production experience on a caustic lens
design pipeline — Julia SOR solver, Python ray tracer, CNC output — running
over multiple multi-hour sessions with full autonomous pipeline execution.*

*The lessons here came from real bugs, real data loss, and real wasted compute.
The protections here exist because they were needed.*
