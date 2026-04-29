# Phase 38: with-dormant-seeds-and-pending-quick-task - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** 6
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.planning/ROADMAP.md` | config | transform | `.planning/ROADMAP.md` (Phase 37 and Phase 38 sections) | exact |
| `.planning/STATE.md` | config | transform | `.planning/STATE.md` (`## Deferred Items`, `## Pending Todos`) | exact |
| `.planning/seeds/SEED-001-tacit-knowledge-elicitation-engine.md` | config | event-driven | `.planning/seeds/SEED-vault-root-aware-cli.md` + `.planning/seeds/SEED-bidirectional-concept-code-links.md` | role-match |
| `.planning/seeds/SEED-002-harness-memory-export.md` | config | event-driven | `.planning/seeds/SEED-vault-root-aware-cli.md` + `.planning/seeds/SEED-bidirectional-concept-code-links.md` | role-match |
| `.planning/todos/pending/<new-quick-task>.md` | config | request-response | `.planning/todos/completed/fix-detect-self-ingestion-graphify-out.md` | role-match |
| `.planning/quick/<new-quick-task>/<task-id>-PLAN.md` | config | request-response | `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-PLAN.md` | exact |

## Pattern Assignments

### `.planning/ROADMAP.md` (config, transform)

**Analog:** `.planning/ROADMAP.md`

**Phase block shape** (lines 417-426):
```markdown
### Phase 38: with dormant seeds and pending quick task

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 37
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 38 to break down)
```

**Progress table continuity pattern** (lines 370-416):
```markdown
## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| ... |
| 37. Validation Metadata Ratification | v1.8 | 2/2 | Complete   | 2026-04-29 |
```

**Planner guidance:** Keep the Phase 38 section as the single source of truth for plan count and completion status; mirror wording style used in Phase 37 and prior v1.8 entries.

---

### `.planning/STATE.md` (config, transform)

**Analog:** `.planning/STATE.md`

**Roadmap-evolution + deferred-items pattern** (lines 71-74, 151-160):
```markdown
### Roadmap Evolution

- Phase 38 added: with dormant seeds and pending quick task
...
## Deferred Items

| Category | Item | Status |
|----------|------|--------|
| seed | SEED-001 tacit-to-explicit elicitation | Dormant; revisit when onboarding/discovery is milestone theme |
| seed | SEED-002 multi-harness/inverse import | Deferred pending prompt-injection defenses |
| baseline-test | `test_detect_skips_dotfiles`, `test_collect_files_from_dir` | Separate `/gsd-debug` session |
```

**Pending-todo section pattern** (lines 139-141):
```markdown
### Pending Todos

None.
```

**Current-position header pattern** (lines 26-33):
```markdown
## Current Position

Phase: 37
Plan: 37.2 complete
Status: Complete
Last activity: 2026-04-29 -- Phase 37 execution complete
```

**Planner guidance:** For Phase 38, update state with deterministic, minimal deltas: current phase pointer, deferred seed status wording, and pending quick-task visibility without restating milestone history.

---

### `.planning/seeds/SEED-001-tacit-knowledge-elicitation-engine.md` (config, event-driven)

**Analog:** `.planning/seeds/SEED-vault-root-aware-cli.md`

**Seed frontmatter contract** (from `SEED-vault-root-aware-cli.md`, lines 1-10):
```markdown
---
name: SEED-vault-root-aware-cli
description: graphify CLI should detect when CWD is itself an Obsidian vault ...
trigger_when: After v1.7 ships ...
planted_during: v1.7 pre-scoping ...
planted_date: 2026-04-27
source: /gsd-explore conversation ...
fit: tight
effort: small
---
```

**Dormant-status frontmatter variant** (from `SEED-bidirectional-concept-code-links.md`, lines 1-7):
```markdown
---
seed_id: SEED-bidirectional-concept-code-links
trigger_when: a future milestone treats the graph as a navigable knowledge tool ...
planted_during: /gsd-explore for v1.8 scoping
planted_date: 2026-04-28
status: dormant
---
```

**Trigger-condition section pattern** (from `SEED-001`, lines 40-48):
```markdown
## When to Surface

Bring this back into active scoping when **any** of the following is true:

- A future milestone focuses on onboarding, discovery, or "make agents useful for new domains"
- A real user ... says: "I want to use graphify but I don't have docs/code/artifacts — just my head"
```

**Planner guidance:** If Phase 38 changes SEED-001 state, keep trigger-based activation language and explicit "seed vs phase" rationale sections intact.

---

### `.planning/seeds/SEED-002-harness-memory-export.md` (config, event-driven)

**Analog:** `.planning/seeds/SEED-bidirectional-concept-code-links.md` + existing `SEED-002` structure

**Deferred/dependency framing pattern** (from `SEED-002`, lines 35-40):
```markdown
## Why It's a Seed, Not a Phase

- Too early: ...
- Requires SEED-001 or v1.4 Phase 14 to exist first ...
- v1.3 priorities elsewhere ...
```

**Activation trigger list pattern** (from `SEED-002`, lines 41-49):
```markdown
## When to Surface

Activate when **any** of the following is true:

- Multi-harness support becomes a real user ask ...
- Lock-in friction appears in a UAT ...
- v1.4 Phase 13 (Agent Capability Manifest) is being planned ...
```

**Planner guidance:** Preserve explicit prerequisites and "not now" logic; Phase 38 should only adjust status/trigger conditions if there is new evidence in state or roadmap, not rewrite the seed objective.

---

### `.planning/todos/pending/<new-quick-task>.md` (config, request-response)

**Analog:** `.planning/todos/completed/fix-detect-self-ingestion-graphify-out.md`

**Todo issue template pattern** (lines 1-5, 7-13, 25-34):
```markdown
---
title: "Fix self-ingestion: exclude graphify-out/ from detect.py default ignores"
date: 2026-04-27
priority: high
---

# Fix self-ingestion loop in `detect.py`

## Problem
...
## Fix
...
## Acceptance criteria

- [ ] ...
- [ ] ...
```

**Quick-task handoff hint pattern** (lines 36-39):
```markdown
## Suggested entry point

`/gsd-quick fix-detect-self-ingestion` — small surface, regression test, atomic commit.
```

**Planner guidance:** For a pending quick task in Phase 38, keep acceptance criteria checkboxes and explicit `/gsd-quick ...` entry point to preserve execution routing.

---

### `.planning/quick/<new-quick-task>/<task-id>-PLAN.md` (config, request-response)

**Analog:** `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-PLAN.md`

**Quick-plan frontmatter + must-have contract pattern** (lines 1-32):
```markdown
---
phase: 260427-rc7-fix-detect-self-ingestion
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - graphify/detect.py
  - tests/test_detect.py
autonomous: true
requirements:
  - FIX-DETECT-SELF-INGESTION
must_haves:
  truths:
    - "Running detect() ... does NOT return any files from inside graphify-out/ ..."
...
---
```

**Task decomposition pattern** (lines 126-231):
```markdown
<tasks>
<task type="auto" tdd="true">
  <name>Task 1: Add default graphify-out/ exclusion ...</name>
  <files>graphify/detect.py, tests/test_detect.py</files>
  <behavior> ... </behavior>
  <action> ... STEP 1 ... STEP 2 ... STEP 3 ... STEP 4 ... </action>
  <verify>
    <automated>cd ... && pytest tests/test_detect.py -q</automated>
  </verify>
  <done> ... </done>
</task>
</tasks>
```

**Success/output closure pattern** (lines 247-265):
```markdown
<success_criteria>
- [x] ...
- [x] ...
</success_criteria>

<output>
After completion, create `.planning/quick/.../...-SUMMARY.md`
documenting:
  - ...
</output>
```

**Planner guidance:** If Phase 38 introduces a quick-task execution lane, copy this contract-heavy PLAN shape (truths, tasks, verify, done, success_criteria, output) for deterministic execution.

## Shared Patterns

### Planning Artifact Style
**Source:** `.planning/ROADMAP.md`, `.planning/STATE.md`  
**Apply to:** all Phase 38 planning updates
```markdown
### Phase <n>: <slug>
**Goal:** ...
**Depends on:** ...
**Plans:** ...
```

### Seed Lifecycle Tracking
**Source:** `.planning/seeds/SEED-bidirectional-concept-code-links.md`, `.planning/STATE.md`  
**Apply to:** SEED-001/SEED-002 updates plus state synchronization
```markdown
status: dormant
...
| seed | SEED-001 ... | Dormant; revisit when ... |
```

### Quick Task Routing
**Source:** `.planning/todos/completed/fix-detect-self-ingestion-graphify-out.md`, `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-PLAN.md`  
**Apply to:** pending quick task definition and execution artifacts
```markdown
## Suggested entry point
`/gsd-quick <slug>`
```

### Evidence-First Execution
**Source:** `.planning/quick/260427-rc7-fix-detect-self-ingestion/260427-rc7-PLAN.md`  
**Apply to:** any quick task that may touch code
```markdown
<verify>
  <automated>... pytest ...</automated>
</verify>
```

## No Analog Found

None. Phase 38's likely scope (roadmap/state sync, dormant seeds, pending quick-task wiring) has direct analogs in existing planning artifacts.

## Metadata

**Analog search scope:** `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/seeds/`, `.planning/todos/`, `.planning/quick/260427-rc7-*`, `.planning/phases/37-*`  
**Files scanned:** 11  
**Pattern extraction date:** 2026-04-29
