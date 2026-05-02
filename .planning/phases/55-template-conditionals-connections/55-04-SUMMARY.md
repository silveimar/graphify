---
phase: 55
plan: "04"
subsystem: templates
tags: [tdd, red-gate, doc-fixtures, templates-doc]
dependency_graph:
  requires: [55-01]
  provides: [red-gate-docs-templates-examples, fence-loader]
  affects: [tests/test_docs_templates_examples.py]
tech_stack:
  added: []
  patterns: [doc-fence-as-fixture, tdd-red-gate, parametrize-from-markdown]
key_files:
  created:
    - tests/test_docs_templates_examples.py
  modified: []
decisions:
  - "Two parametrize axes: fence runner (test_docs_template_fence) + section coverage gate (test_docs_templates_section_id_present) — ensures both fence execution and section completeness are verified when docs/TEMPLATES.md lands"
  - "Stub entries per section ID (not zero tests) when doc is missing — gives pytest 16 clearly-failing tests in RED state, one per section per axis"
  - "_FENCE_RE uses re.DOTALL so multi-line fence bodies are captured correctly"
metrics:
  duration: "125s"
  completed: "2026-05-02"
  tasks: 1
  files: 1
---

# Phase 55 Plan 04: Doc-Fence Fixture Loader for docs/TEMPLATES.md — RED Gate

New `tests/test_docs_templates_examples.py` lifts `<!-- test:<id> -->` annotated fences from `docs/TEMPLATES.md` and runs each through `_expand_blocks`. RED gate: all 16 tests fail with "docs/TEMPLATES.md does not yet exist — Plan 55-05 will create it."

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create doc-fence fixture loader (RED gate) | bab5aaf | tests/test_docs_templates_examples.py |

## Acceptance Gate Results

| Gate | Result | Details |
|------|--------|---------|
| File imports without error | PASSED | `python -c "import tests.test_docs_templates_examples"` OK |
| pytest collects 16 tests | PASSED | 8 fence + 8 section-coverage tests |
| All 16 fail RED with expected message | PASSED | "docs/TEMPLATES.md does not yet exist — Plan 55-05 will create it" |
| All 8 D-55.11 section IDs covered | PASSED | conditional-blocks, connection-loops, ordering-invariant, sanitization, predicate-catalog, predicate-flags, validation, backward-compat |

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | bab5aaf | PRESENT |
| GREEN | Deferred to 55-05 (creates docs/TEMPLATES.md) | N/A — this plan is the RED gate |

This plan intentionally establishes RED state only. GREEN landing is Plan 55-05 which creates `docs/TEMPLATES.md` with `<!-- test:<id> -->` annotated fences for all 8 required sections.

## Known Stubs

None. No rendered output — this is a pure test file.

## Threat Flags

None. No new network endpoints, auth paths, file access beyond read-only `docs/TEMPLATES.md`, or schema changes.

## Self-Check: PASSED

- `tests/test_docs_templates_examples.py` created: FOUND
- Commit bab5aaf: FOUND
- 16 tests collected: VERIFIED
- 16 tests fail RED: VERIFIED
