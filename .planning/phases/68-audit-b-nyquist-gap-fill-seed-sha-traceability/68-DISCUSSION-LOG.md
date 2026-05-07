# Phase 68 — Discussion Log

**Date:** 2026-05-06
**Phase:** 68 — AUDIT-B — Nyquist Gap-Fill & Seed-SHA Traceability
**Mode:** discuss (default), 3 questions in one batch

## Areas Discussed

### 1. Closure script form
- Options presented:
  1. Python script + pytest marker (`@pytest.mark.audit_v112`) — recommended
  2. Bash wrapper around pytest with explicit node-id list
  3. Make target
- **Selected:** Python + pytest marker
- **Rationale:** Marker set IS the citation list — drift between VALIDATION.md and the script becomes structurally impossible because the script can self-check via `pytest -m audit_v112 --collect-only`. Pure Python keeps the toolchain unchanged.

### 2. VALIDATION.md placement
- Options presented:
  1. One consolidated `.planning/milestones/v1.12-VALIDATION.md` — recommended
  2. Per-phase files in `.planning/milestones/v1.12-validation/`
  3. Resurrect `.planning/phases/59-*` etc. with VALIDATION.md only
- **Selected:** Consolidated single file
- **Rationale:** Sits alongside `v1.12-ROADMAP.md` and `v1.12-MILESTONE-AUDIT.md`; keeps the milestone archive self-contained and avoids resurrecting phase directories that were intentionally archived.

### 3. Seed annotation format
- Options presented:
  1. Keep existing inline parenthetical style — recommended
  2. Add a dedicated `## Seed Traceability` table
  3. Both inline + table
- **Selected:** Inline parenthetical (extend existing PROJECT.md voice)
- **Rationale:** Single source of truth, minimal churn, matches existing PROJECT.md/REQUIREMENTS.md voice. No risk of drift between two views.

## Deferred

- Generalize the `audit_v{milestone}` marker pattern as a reusable retroactive-audit primitive for future milestones.

## Claude's Discretion (no question asked)

- Researcher will identify implementing SHA via `git log` filtered by phase commit prefixes (e.g. `feat(59-`, `feat(60-`) and asserting test paths via `v1.12-MILESTONE-AUDIT.md` references + `grep tests/` for phase requirement IDs. One asserting test per phase (Nyquist sampling, not exhaustive).
- Marker `audit_v112` registered in `pyproject.toml` `[tool.pytest.ini_options].markers` to silence the unknown-marker warning.
- Closure script exit codes: 0 = green, 1 = test failure, 2 = citation/marker drift.
