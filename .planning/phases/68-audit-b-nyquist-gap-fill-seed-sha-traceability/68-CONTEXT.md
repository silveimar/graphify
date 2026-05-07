---
phase: 68
name: AUDIT-B — Nyquist Gap-Fill & Seed-SHA Traceability
date: 2026-05-06
requirements: [AUDIT-01, AUDIT-03]
status: context_gathered
---

# Phase 68 — AUDIT-B Context

## Domain

Retroactive audit-closure phase. No new product features. Three deliverables:

1. **Nyquist gap-fill** — 5 retroactive VALIDATION.md entries for v1.12 phases (59, 59.1, 60, 60.1, 61), each citing the implementing SHA and the asserting test path.
2. **Closure script** — runnable from a clean checkout; re-executes every cited test and reports green.
3. **Seed-SHA traceability** — REQUIREMENTS.md and PROJECT.md annotated so each SEED is mapped to its consuming milestone(s).

The phase succeeds when no v1.12-deferred audit item remains open in `MILESTONES.md`.

## Canonical Refs

- `.planning/ROADMAP.md` (Phase 68 success criteria, lines defining AUDIT-B)
- `.planning/REQUIREMENTS.md` (AUDIT-01, AUDIT-03; SEED bullets to be annotated)
- `.planning/PROJECT.md` (existing inline SEED → milestone parentheticals — preserve voice)
- `.planning/MILESTONES.md` (v1.12-deferred audit items to close)
- `.planning/milestones/v1.12-ROADMAP.md` (Phase 59, 59.1, 60, 60.1, 61 goals)
- `.planning/milestones/v1.12-MILESTONE-AUDIT.md` (existing audit; closure path documented at end of file)
- `.planning/milestones/v1.12-REQUIREMENTS.md` (v1.12 requirement IDs that the cited tests assert)

## Decisions

### D-01 Closure script form — Python + pytest marker

`scripts/audit_b_closure.py` drives pytest by collecting tests tagged with a new `@pytest.mark.audit_v112` marker, then runs them and exits non-zero on any failure. Tests cited in `v1.12-VALIDATION.md` MUST carry this marker. Script also performs a `pytest -m audit_v112 --collect-only` cross-check to guarantee that the marker set matches the citation list (no drift).

**Implementation notes for planner:**
- Register the marker in `pyproject.toml` `[tool.pytest.ini_options].markers` to silence the unknown-marker warning.
- Script is self-contained Python — no shell, no Make.
- Exit codes: 0 = all green, 1 = test failure, 2 = citation/marker drift.

### D-02 VALIDATION.md placement — single consolidated file

All 5 retroactive entries live in `.planning/milestones/v1.12-VALIDATION.md` with one `## Phase {N}` section per phase. Sits alongside `v1.12-ROADMAP.md` and `v1.12-MILESTONE-AUDIT.md` so the milestone archive is self-contained. Do **not** resurrect the per-phase directories under `.planning/phases/`.

**Per-phase section schema (locked):**
```
## Phase {N}: {name}
- **Implementing SHA:** {sha}
- **Asserting test:** {path}::{node_id}
- **Marker:** @pytest.mark.audit_v112
- **Re-run command:** `python scripts/audit_b_closure.py`
- **Status:** PASS @ {date} on {sha}
```

### D-03 Seed annotation format — inline parenthetical (extend existing pattern)

Extend the current PROJECT.md style. Each of the 4 SEED bullets is patched to include all consuming milestones plus closure SHAs where known:

- `SEED-001` → v1.9
- `SEED-002` → v1.4
- `SEED-vault-root-aware-cli` → v1.12 + v1.13 (Option B closes the remaining 20% in Phase 63)
- `SEED-bidirectional-concept-code-links` → v1.10 / v1.11 / v1.13 (CCONF, CFED, CDRIFT, CQUERY close the remaining 35% in phases 65–67)

Mirror the same annotations in `REQUIREMENTS.md` where SEEDs are referenced. No new traceability table — single source of truth, minimal churn.

### D-04 Identifying implementing SHA + asserting test path

Researcher will use `git log --oneline --all` filtered by phase commit prefixes (e.g. `feat(59-`, `feat(60-`) to locate the canonical implementing SHA. The asserting test path is the test file/node that exercises the phase's success criteria — typically already named in `v1.12-MILESTONE-AUDIT.md` or discoverable via `grep -r` in `tests/` for phase requirement IDs (VCWD-*, E2E-*, etc.).

If a phase has multiple candidate tests, cite the one that most directly asserts the phase's headline success criterion. One asserting test per phase is sufficient — Nyquist sampling, not exhaustive coverage.

### D-05 Closure on v1.12 audit items

After the 5 VALIDATION.md sections land and the closure script runs green, edit `.planning/MILESTONES.md` to mark every v1.12-deferred audit item resolved. The MILESTONE-AUDIT.md file's "Proceed to /gsd-complete-milestone v1.12" closure path becomes runnable.

## Boundaries (NOT in this phase)

- No new graphify source code in `graphify/`. Only `scripts/audit_b_closure.py`, the marker registration in `pyproject.toml`, and documentation edits.
- No re-running of v1.12 phase logic itself — only re-running the cited tests.
- No new tests written. The marker is added to existing tests in place.
- No reformatting of existing audit files beyond surgical edits to add SHAs/markers.

## Success Criteria (from ROADMAP)

1. v1.12 phases 59, 59.1, 60, 60.1, 61 each have a retroactive VALIDATION.md entry citing the implementing SHA and the asserting test path. → consolidated in `v1.12-VALIDATION.md` per D-02.
2. A closure script re-executes every cited test and reports green; checked in and runnable from a clean checkout. → `scripts/audit_b_closure.py` per D-01.
3. REQUIREMENTS.md and PROJECT.md annotate each seed with its consuming milestone (SEED-001 → v1.9, SEED-002 → v1.4, SEED-vault-root-aware-cli → v1.12 + v1.13, SEED-bidirectional-concept-code-links → v1.10 / v1.11 / v1.13). → per D-03.
4. The audit closure leaves no v1.12-deferred audit item open in MILESTONES.md. → per D-05.

## Deferred Ideas

- Generalizing the `audit_v{milestone}` marker pattern as a reusable retroactive-audit primitive for future milestones — note for after AUDIT-B ships.
