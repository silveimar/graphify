---
phase: 57-elicitation-harness-increment
plan: 02
subsystem: docs + tests
tags: [docs, elicitation, harness, interchange, regression-lock]
requires:
  - 57-01 (ELIC-01 sidecar merge tests — referenced as canonical record per D-12)
  - 57-03 (HARN-02 --allow-vault-write flag — referenced in trust-boundary doc)
provides:
  - docs/ELICITATION.md (3 new H2s: Trust Boundaries, Canonical Harness Interchange (v1) Mapping, Milestone Non-Goals (v1.11))
  - tests/test_elicit.py (3 doc-content regression tests)
  - tests/test_harness_interchange.py (1 schema-id constant + drift lock)
affects: []
tech-stack:
  added: []
  patterns:
    - "Doc-content regression-lock test (Path(__file__).resolve().parents[1] / 'docs' / ...)"
    - "Pitfall 5: code constant ↔ user-facing prose drift lock via verbatim substring assertion"
key-files:
  created: []
  modified:
    - docs/ELICITATION.md
    - tests/test_elicit.py
    - tests/test_harness_interchange.py
decisions:
  - "ELIC-02 trust-boundary doc edits land in-place (D-10) as sibling H2s to existing sections (Open Question #3 resolution)"
  - "Sidecar merge precedence is NOT separately re-documented (D-12); doc references tests/test_elicit.py as canonical record"
  - "INTERCHANGE_SCHEMA_ID constant value is locked at 'graphify.harness.interchange/v1' with both a code-side equality assertion and a doc-text substring assertion (drift lock)"
metrics:
  duration: ~3min
  tasks: 2
  files: 3
  completed: 2026-05-03
---

# Phase 57 Plan 02: ELIC-02 Doc Edits + HARN-01 Schema Lock Summary

In-place documentation expansion (`docs/ELICITATION.md`) adding three milestone-scoped H2 sections (Trust Boundaries, Canonical Harness Interchange v1 Mapping, Milestone Non-Goals v1.11), locked by four regression tests that pin both the doc structure and the canonical schema-id constant.

## What Shipped

### Documentation (`docs/ELICITATION.md`)

Three new sibling H2 sections inserted between the existing `## Where sidecar merge runs` section and the renamed Non-Goals section:

1. **`## Trust Boundaries`** — three subsections covering (a) where elicitation reads/writes via `resolve_output()`, with a pointer to `tests/test_elicit.py` as the canonical record of sidecar merge precedence; (b) what `import-harness` will and will not do, including the `--allow-vault-write` refusal contract and MCP `validate_graph_path` empty-path rejection; (c) LLM trust posture during elicit (sanitize, label-escape, Phase 40 caps unchanged).

2. **`## Canonical Harness Interchange (v1) Mapping`** — schema id `graphify.harness.interchange/v1` plus a four-row field-mapping table mirroring `graph_data_to_extraction()` (`schema`, `graph.nodes[]`, `graph.edges[]`, `provenance`) and an explicit doc-pointer to the schema-id lock test.

3. **`## Milestone Non-Goals (v1.11)`** — heading renamed in place from `## Non-goals (other phases)` (no duplicate heading); existing Phase 40 / Phase 41 bullets preserved; three new v1.11-scoped bullets appended (real inverse round-trip deferred, no new harness target formats, Phase 40 size caps not re-tested).

### Tests

- `tests/test_elicit.py::test_doc_has_trust_boundaries_section` — substring assertions for `## Trust Boundaries`, `resolve_output`, `<artifacts_dir>/elicitation.json`, `sanitize_harness_text`.
- `tests/test_elicit.py::test_doc_has_milestone_non_goals_section` — asserts new heading present, old heading absent, new bullet substring present.
- `tests/test_elicit.py::test_doc_has_canonical_mapping` — asserts canonical mapping H2, schema id, and `graph_data_to_extraction` are all present.
- `tests/test_harness_interchange.py::test_interchange_schema_id_locked` — asserts `INTERCHANGE_SCHEMA_ID == "graphify.harness.interchange/v1"` AND that the same string appears verbatim in `docs/ELICITATION.md` (Pitfall 5 drift lock).

## Verification

- All four new tests pass individually and together.
- Full pytest suite: **2094 passed, 1 xfailed** in 75s — no regressions.
- All Task 1 acceptance grep checks confirmed:
  - `## Trust Boundaries`: 1
  - `## Canonical Harness Interchange (v1) Mapping`: 1
  - `## Milestone Non-Goals (v1.11)`: 1
  - `## Non-goals (other phases)`: 0 (renamed in place)
  - `graphify.harness.interchange/v1`: 2
  - `resolve_output`: 2
  - `tests/test_elicit.py`: 1
  - `allow-vault-write`: 1

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | 907b022 | docs(57-02): add Trust Boundaries, Canonical Interchange Mapping, Milestone Non-Goals (ELIC-02 + HARN-01) |
| 2 | 2005baa | test(57-02): lock doc content + INTERCHANGE_SCHEMA_ID constant (ELIC-02 + HARN-01) |

## Requirements Closed

- **ELIC-02** — `docs/ELICITATION.md` now states trust boundaries, artifact locations, and milestone-scoped non-goals.
- **HARN-01** — Documented canonical mapping for the harness interchange envelope, with code↔doc parity locked by `test_interchange_schema_id_locked`.

## Deviations from Plan

None — plan executed exactly as written. All three D-10/D-11/D-12 constraints honored:
- D-10 (in-place edit, two new H2 sections plus canonical-mapping per D-07): satisfied.
- D-11 (Trust Boundaries covers three surfaces): satisfied.
- D-12 (sidecar merge precedence not separately re-documented; references test module): satisfied.

## Self-Check: PASSED

- `docs/ELICITATION.md` modified — FOUND
- `tests/test_elicit.py` modified — FOUND
- `tests/test_harness_interchange.py` modified — FOUND
- Commit `907b022` — FOUND
- Commit `2005baa` — FOUND
- Four new tests pass — VERIFIED
- Full suite green — VERIFIED
