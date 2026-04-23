---
phase: 19
plan: "04"
subsystem: vault_promote
tags: [testing, integration, documentation, requirements]
dependency_graph:
  requires: [19-02, 19-03]
  provides: [VAULT-integration-coverage, vault-promote-docs, REQUIREMENTS-closure]
  affects: [tests/test_vault_promote.py, tests/fixtures/vault_promote_graph.json, README.md, graphify/skill.md, .planning/REQUIREMENTS.md]
tech_stack:
  added: []
  patterns: [synthetic-fixture-with-list-source-file, threshold-sensitive-dispatch-testing, TDD-RED-GREEN]
key_files:
  created:
    - tests/fixtures/vault_promote_graph.json
    - .planning/phases/19-vault-promotion-script-layer-b/19-04-SUMMARY.md
  modified:
    - tests/test_vault_promote.py
    - README.md
    - graphify/skill.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/19-vault-promotion-script-layer-b/19-VALIDATION.md
decisions:
  - "Threshold=1 used in end-to-end fixture tests so degree-1 People/Quotes/Statements nodes qualify (D-fixture-threshold)"
  - "21-node fixture with 10 backbone fillers ensures god_nodes top-10 is filled by high-degree nodes, leaving People/Quotes/Statements out of Things bucket"
  - "Foreign file test uses pre-existing vault file (no first promote() run) to guarantee clean manifest state"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-23"
  tasks_completed: 2
  files_changed: 6
---

# Phase 19 Plan 04: Integration Tests, Heuristics, Docs, Traceability Summary

Integration fixture and end-to-end tests prove all 7 vault folders populate correctly; heuristic unit tests cover People/Quotes/Statements dispatchers; README + skill.md document the vault-promote subcommand; REQUIREMENTS.md traceability fully closed for VAULT-01..07.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 4.1 | Integration fixture + end-to-end tests + heuristic unit coverage | d25d032 |
| 4.2 | Documentation (README + skill.md) + REQUIREMENTS.md traceability closure | b8818fe |

## What Was Built

### Task 4.1 — Integration Fixture + Tests

Created `tests/fixtures/vault_promote_graph.json` — a 21-node synthetic graph with:
- 4 communities (0–3) exercising Maps dispatch
- `n_code_hub` with `source_file: list[str]` (`["src/core.py", "src/utils.ts"]`) — exercises `_iter_sources` and Layer-3 tech detection for both python and typescript
- 10 backbone filler nodes ensuring god_nodes top-10 is filled, keeping People/Quotes/Statements nodes unclaimed by Things
- Confidence mix: 16 EXTRACTED, 1 INFERRED, 1 AMBIGUOUS
- Isolated node `n_isolated` (degree=0) — triggers Questions via knowledge_gaps
- `n_alice` (`Alice Smith`) → People; `n_quote` (curly-quote label) → Quotes; `n_stmt` (defines edge) → Statements

Added 8 new tests to `tests/test_vault_promote.py` (total: 28 tests, 0 skipped):
- `test_end_to_end_all_seven_folders` — asserts ≥1 .md in each of 7 target folders
- `test_multi_run_drift_overwrite_self` — 2nd run has 0 foreign skips, import-log has 2 Run blocks
- `test_multi_run_preserves_foreign_file` — pre-placed Community 0.md survives promote()
- `test_multi_run_preserves_user_edit` — user-mutated promoted file skipped as user_modified
- `test_heuristic_people_regex` — _is_person True/False boundary cases
- `test_heuristic_quote_marks` — _has_quote_marks True/False including guillemets
- `test_heuristic_defines_edge` — _has_defines_edge True/False via undirected graph
- `test_tech_layer3_detection_persists_via_writeback` — python + typescript in profile.yaml after promote()

### Task 4.2 — Documentation + Traceability

**README.md** — Added `### Vault Promotion — graphify vault-promote` subsection (3 occurrences of "vault-promote") covering CLI usage, write semantics (never overwrites foreign, idempotent via manifest), and coexists-with-approve note.

**graphify/skill.md** — Added `## For vault-promote` section covering usage, dispatch summary, import-log behaviour, tech-tag auto-detection, and when-to-use guidance (vault-promote vs approve).

**.planning/REQUIREMENTS.md** — Replaced all 7 TBD plan values with authoritative plan references:
- VAULT-01: 19-03 (promote() orchestrator + CLI)
- VAULT-02: 19-02 (frontmatter + tag taxonomy)
- VAULT-03: 19-02 (7-folder classify_nodes)
- VAULT-04: 19-02 (EXTRACTED-only related: filter)
- VAULT-05: 19-03 (import-log)
- VAULT-06: 19-03 (profile write-back)
- VAULT-07: 19-01, 19-02 (3-layer tag taxonomy)

**19-VALIDATION.md** — Set `nyquist_compliant: true`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixture dispatch collision: People/Quotes/Statements claimed by Things**
- **Found during:** Task 4.1 RED phase — `test_end_to_end_all_seven_folders` failed because `god_nodes()` top-10 returned Alice/Quote/Stmt in a small graph
- **Issue:** In a graph with < 11 non-file nodes, `god_nodes()` returns ALL nodes including the special-purpose People/Quotes/Statements nodes; classify_nodes() claims them for Things before the People/Quotes/Statements buckets can process them
- **Fix:** Redesigned fixture to include 10 backbone filler nodes (each degree=1 to n_doc_hub), ensuring god_nodes top-10 is filled by backbone nodes; special nodes (Alice/Quote/Stmt) have degree=1 and fall outside top-10. Used threshold=1 in integration tests.
- **Files modified:** `tests/fixtures/vault_promote_graph.json`, `tests/test_vault_promote.py`
- **Commit:** d25d032

**2. [Rule 1 - Bug] Foreign file test used non-promoted path**
- **Found during:** Task 4.1 test debugging — `test_multi_run_preserves_foreign_file` placed `Handmade.md` at `Atlas/Dots/Things/Handmade.md` but promote() never tries to write that path
- **Fix:** Rewrote test to pre-place `Community 0.md` at `Atlas/Maps/Community 0.md` — a path promote() always attempts to write for community 0's Map MOC. Removed the intermediate first promote() run; used empty manifest to guarantee foreign detection.
- **Files modified:** `tests/test_vault_promote.py`
- **Commit:** d25d032

## Test Results

```
pytest tests/test_vault_promote.py -q
28 passed, 5 warnings in 0.50s

pytest tests/ -q
1477 passed, 7 warnings in 38.04s
```

## Acceptance Criteria Verification

- `test -f tests/fixtures/vault_promote_graph.json` — PASS
- `python -c "... assert len(d['nodes']) >= 11 and len(d['links']) >= 6 ..."` — PASS (21 nodes, 18 links)
- `grep -cE "^def test_" tests/test_vault_promote.py` — 28 (≥ 21)
- `grep -c "pytest.mark.skip" tests/test_vault_promote.py` — 0
- `pytest tests/test_vault_promote.py -q` — 28 passed, 0 skipped
- `pytest tests/ -q` — 1477 passed, 0 failures
- `grep -c "vault_promote_graph.json" tests/test_vault_promote.py` — 1 (fixture referenced)
- `grep -c "vault-promote" README.md` — 3
- `grep -q "Write semantics" README.md` — PASS
- `grep -q "vault-promote" graphify/skill.md` — PASS
- `grep -cE "^\| VAULT-0[1-7] \| 19 \| TBD \|" .planning/REQUIREMENTS.md` — 0
- `grep -cE "^\| VAULT-0[1-7] \| 19 \| 19-0" .planning/REQUIREMENTS.md` — 7

## Known Stubs

None — all promoted note content is rendered from real fixture data via the full pipeline.

## Threat Flags

None — this plan adds only test fixtures (controlled input in tmp_path sandbox) and static documentation. No new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- `tests/fixtures/vault_promote_graph.json` — EXISTS
- `tests/test_vault_promote.py` — EXISTS (28 tests)
- Commit d25d032 — EXISTS (`git log --oneline | grep d25d032`)
- Commit b8818fe — EXISTS (`git log --oneline | grep b8818fe`)
