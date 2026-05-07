---
phase: 72-reas
plan: 01
subsystem: validate
tags: [reasoning-relations, schema, validation]
requires: []
provides: [REASONING_RELATIONS, reasoning-edge-validation, relations-doc-section]
affects: [graphify/validate.py, docs/RELATIONS.md, tests/test_validate.py, tests/fixtures/extraction_with_reasoning.json]
tech_stack_added: []
key_patterns: [frozenset-vocab, per-edge-rule-block, read-write-split]
files_created:
  - tests/fixtures/extraction_with_reasoning.json
files_modified:
  - graphify/validate.py
  - docs/RELATIONS.md
  - tests/test_validate.py
decisions:
  - "REASONING_RELATIONS frozenset registered alongside KNOWN_EDGE_RELATIONS, mirroring Phase 53 NEW_CONCEPT_CODE_RELATIONS precedent."
  - "Code-endpoint rejection rule fires only inside validate_extraction (write/read shared path); validate_extraction_for_read remains permissive for legacy graphs (D-72.05)."
  - "INFERRED reasoning edges enforce confidence_score in [0.0, 1.0] using same try/except float pattern as Phase 53 (D-72.03/06)."
  - "supersedes oriented newer -> older; evolved_into is older -> newer (opposite). Documented to prevent downstream auto-stamp inversion in Plan 03."
metrics:
  duration_minutes: 5
  tasks_completed: 2
  files_changed: 4
  completed_date: 2026-05-07
---

# Phase 72 Plan 01: Reasoning-relation vocabulary registered in validate.py

**One-liner:** Registered the 5 REASONING_RELATIONS in validate.py with code-endpoint rejection (D-72.05) and INFERRED confidence_score enforcement (D-72.03/06) per CCONF v1.13, plus docs/RELATIONS.md taxonomy with supersedes newer->older orientation.

## What shipped

- `graphify/validate.py`: new `REASONING_RELATIONS` frozenset (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`); same 5 names appended to `KNOWN_EDGE_RELATIONS` (warn-once vocabulary). Per-edge loop now builds a `node_types: dict[str, str]` alongside `node_ids` and uses it to reject reasoning edges with `file_type='code'` on either endpoint. INFERRED reasoning edges require `confidence_score ∈ [0.0, 1.0]` (parsed via float() try/except, mirroring Phase 53 precedent at validate.py:194-198).
- `tests/fixtures/extraction_with_reasoning.json`: 3 doc nodes (`adr_0028`, `adr_0042`, `concept_x`), 2 edges (supersedes EXTRACTED + supports INFERRED 0.8), `schema_version: "2.0"`. Used by 72-01 fixture-loads test and reserved for downstream plans.
- `tests/test_validate.py`: 5 new tests — `test_reasoning_relations_accepted`, `test_reasoning_rejects_code_endpoint`, `test_reasoning_inferred_score`, `test_legacy_no_reasoning_loads`, `test_reasoning_fixture_loads`.
- `docs/RELATIONS.md`: new top-level section `## Reasoning relations (Phase 72)` with 5-row relation table (definition / direction / confidence), explicit **`supersedes` newer -> older** call-out, `evolved_into` older->newer counter-note, Phase 71 auto-stamp interaction subsection, and ADR-0042 supersedes ADR-0028 worked example.

## Commits

| Task | Description                                                                                  | Commit  |
| ---- | -------------------------------------------------------------------------------------------- | ------- |
| 1    | Register REASONING_RELATIONS + endpoint/score rules + tests + fixture                        | 4dd52b1 |
| 2    | Document 5 reasoning relations in docs/RELATIONS.md with supersedes orientation              | 27a01b8 |

## Verification

- `pytest tests/test_validate.py -x -q` — **31 passed** (26 existing + 5 new).
- `grep -c "REASONING_RELATIONS" graphify/validate.py` → 4 (definition + 1 usage + 2 doc-comment refs).
- `grep -c "supports\|contradicts\|supersedes\|evolved_into\|depends_on" graphify/validate.py` → 10 (registration in 2 frozensets).
- All 5 docs/RELATIONS.md grep checks pass: `Reasoning relations (Phase 72)`, `newer -> older`, `Auto-stamping`, `ADR-0042 supersedes ADR-0028`, all 5 relation names.

## Deviations from Plan

None — plan executed as written.

The TDD task (Task 1) bundled test creation, fixture creation, and implementation into a single commit because the plan structured it as one `<task type="auto" tdd="true">` block with a shared `<files>` list. Each test is independently executable and the implementation appears in the same commit as its test.

## Deferred Issues

47 pre-existing test failures observed during the full regression run, all in `tests/test_vault_cwd.py` and `tests/test_vault_parity.py`. **Out of Phase 72 scope** (no vault-discovery code touched). Logged in `.planning/phases/72-reas/deferred-items.md`. `pytest tests/test_validate.py` passes cleanly (31/31).

## Threat Flags

None — all changes are validation-layer-only (read-only enforcement appended to existing per-edge loop). No new network endpoints, file access, or trust boundaries introduced.

## Self-Check: PASSED

- [x] graphify/validate.py contains REASONING_RELATIONS (verified via grep — 4 occurrences)
- [x] tests/fixtures/extraction_with_reasoning.json exists (verified via Write success + fixture-loads test)
- [x] docs/RELATIONS.md contains Phase 72 section with newer->older orientation (verified via 5 grep checks)
- [x] Commit 4dd52b1 (feat 72-01) present in `git log`
- [x] Commit 27a01b8 (docs 72-01) present in `git log`
- [x] All 31 tests in tests/test_validate.py pass
