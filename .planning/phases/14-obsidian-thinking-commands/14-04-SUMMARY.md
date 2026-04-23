---
phase: 14-obsidian-thinking-commands
plan: 04
subsystem: graphify.commands
tags: [obsidian, command, orphan, phase-15-consumer, read-only]
requires:
  - graph.json (community metadata per node)
  - enrichment.json (OPTIONAL, Phase 15 overlay; staleness == GHOST)
provides:
  - /graphify-orphan slash command (parameter-less, read-only dual-section report)
affects:
  - graphify/commands/graphify-orphan.md (NEW)
  - tests/test_commands.py (+2 tests)
tech-stack:
  added: []
  patterns:
    - dual-section render (analog: connect.md "Shortest path" + "Surprising bridges")
    - graceful-degrade banner (enrichment.json absence → banner, not error)
    - defensive-union community-null detection (null | -1 | missing)
key-files:
  created:
    - graphify/commands/graphify-orphan.md
  modified:
    - tests/test_commands.py
decisions:
  - D-05 dual-section render: Isolated before Stale/Ghost (remediation ordering)
  - OBSCMD-08 intentionally N/A — command is strictly read-only, no propose_vault_note
  - Phase 15 enrichment.json treated as OPTIONAL — absence handled via banner, not error
metrics:
  duration_minutes: 5
  completed_date: 2026-04-22
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 2
  baseline_tests: 1426
  final_tests: 1428
---

# Phase 14 Plan 04: /graphify-orphan Command Summary

Shipped the parameter-less `/graphify-orphan` slash command as a read-only dual-section report surfacing isolated nodes (no community) from `graph.json` and stale/ghost nodes (staleness == GHOST) from the optional Phase 15 `enrichment.json` overlay, with graceful-degrade banner when the overlay is absent.

## What Was Built

- `graphify/commands/graphify-orphan.md` (NEW) — parameter-less command with `target: obsidian`, `graphify-` prefix, `disable-model-invocation: true`.
- Body defines Step 1 (load isolated from `graph.json` — defensive union of null/-1/missing per RESEARCH A3), Step 2 (conditionally load GHOST from `enrichment.json`), Step 3 (render two distinct `## Isolated Nodes` + `## Stale/Ghost Nodes` sections in that order).
- When `enrichment.json` is absent, the Stale/Ghost section renders a banner pointing the user at `graphify enrich` rather than erroring — treating Phase 15 as OPTIONAL overlay.
- Two new unit tests in `tests/test_commands.py`:
  - `test_orphan_dual_sections` — asserts file exists, frontmatter `name: graphify-orphan` + `target: obsidian`, both section headers present, Isolated precedes Stale.
  - `test_orphan_graceful_without_enrichment` — asserts body mentions `enrichment.json`, `graphify enrich`, and a banner-phrase (`unavailable` | `not yet` | `no enrichment`).

## Commits

- `54882ed` — test(14-04): add failing /graphify-orphan dual-section + graceful-without-enrichment tests (RED)
- `6834569` — feat(14-04): add /graphify-orphan command (OBSCMD-05) (GREEN)

## Verification

- `pytest tests/test_commands.py::test_orphan_dual_sections tests/test_commands.py::test_orphan_graceful_without_enrichment -q` → 2 passed
- `pytest tests/ -q` → 1428 passed (baseline 1426 + 2 new; no regressions)
- Acceptance greps:
  - `## Isolated Nodes|## Stale/Ghost Nodes|enrichment.json|graphify enrich` → 10 occurrences (≥ 4 required)
  - `propose_vault_note|Path.write_text` → 0 occurrences (read-only contract enforced)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rephrased final line to avoid literal string `propose_vault_note`**
- **Found during:** Task 2 acceptance grep
- **Issue:** The plan's suggested body included `Do NOT call \`propose_vault_note\``, which caused the read-only acceptance grep (`propose_vault_note|Path.write_text` == 0) to fail with count 1 — the literal mention counted despite the clear negative framing.
- **Fix:** Changed the final line to `This command is strictly read-only — no vault-write primitives, no note-proposal tool calls.` — preserves the read-only invariant while satisfying the grep acceptance criterion.
- **Files modified:** `graphify/commands/graphify-orphan.md`
- **Commit:** `6834569`

## Requirements Closed

- **OBSCMD-05** — `/graphify-orphan` dual-section command (complete)

## Threat Flags

None — command is strictly read-only, no new trust boundaries, no new network endpoints.

## TDD Gate Compliance

- RED gate: `54882ed` (`test(14-04): ...`) — both new tests failed
- GREEN gate: `6834569` (`feat(14-04): ...`) — both tests pass, full suite green
- REFACTOR: not required

## Self-Check: PASSED

- FOUND: `graphify/commands/graphify-orphan.md`
- FOUND: tests/test_commands.py (contains `test_orphan_dual_sections` + `test_orphan_graceful_without_enrichment`)
- FOUND commit: `54882ed`
- FOUND commit: `6834569`
