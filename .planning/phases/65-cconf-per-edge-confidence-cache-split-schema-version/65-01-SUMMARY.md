---
phase: 65
plan: 01
subsystem: validation, export, fixtures
tags: [schema, validation, backward-compat, cconf-05]
requires: []
provides:
  - graphify.validate.validate_extraction_for_read
  - graphify.validate.validate_extraction_for_write
  - graphify.export.to_json emits schema_version
  - tests/fixtures/legacy_v1_12_graph.json (frozen v1.12 graph)
affects:
  - all future writers (must round-trip schema_version)
  - all future readers (use validate_extraction_for_read for legacy compat)
tech-stack:
  added: []
  patterns:
    - read/write validation split (D-65.08 / Q5)
    - schema_version round-trip via G.graph dict
key-files:
  created:
    - tests/fixtures/legacy_v1_12_graph.json
  modified:
    - graphify/validate.py
    - graphify/export.py
    - tests/test_validate.py
    - tests/test_export.py
decisions:
  - "Legacy fixture procured by running v1.12 tag against tests/fixtures/extraction.json (no synthetic data per D-65.09)"
  - "Read mode is implemented as a thin alias of validate_extraction (zero behavioral drift for existing callers)"
  - "to_json defaults to schema_version='1.13' but always defers to G.graph['schema_version'] when set, enabling lossless round-trip"
metrics:
  duration: ~10m
  completed: 2026-05-06
---

# Phase 65 Plan 01: schema_version read/write split + frozen v1.12 fixture — Summary

One-liner: Split validation into read (legacy-tolerant) and write (schema_version-required) entry points, stamp every new `to_json` output with `schema_version="1.13"`, and freeze a real v1.12 graph.json as the regression anchor for backward compatibility.

## What shipped

1. `graphify/validate.py`
   - New: `validate_extraction_for_read(data) -> list[str]` — alias of `validate_extraction` (schema_version absent is OK for v1.10–v1.12 graphs).
   - New: `validate_extraction_for_write(data) -> list[str]` — requires non-empty `schema_version` string; appends `"Missing required key 'schema_version' (write-mode)"` when absent/empty/non-string.
   - `validate_extraction` itself is unchanged (D-65.08 backward compat for all current callers).

2. `graphify/export.py:to_json`
   - One-line addition mirroring the existing `data["hyperedges"] = ...` pattern:
     `data["schema_version"] = getattr(G, "graph", {}).get("schema_version", "1.13")`
   - Fresh writes stamp `"1.13"`; if a caller has set `G.graph["schema_version"]` (e.g. round-tripping a loaded graph), the explicit value wins.

3. `tests/fixtures/legacy_v1_12_graph.json`
   - Real graph.json produced by running `to_json` at the `v1.12` tag against `tests/fixtures/extraction.json` (D-65.09). No `schema_version` key. 85 lines, valid JSON, contains `nodes`, `links`, `hyperedges` keys.

4. Tests (5 new, all green):
   - `tests/test_validate.py::test_legacy_v1_12_passes_read`
   - `tests/test_validate.py::test_write_requires_schema_version`
   - `tests/test_validate.py::test_write_accepts_with_schema_version`
   - `tests/test_export.py::test_to_json_emits_schema_version`
   - `tests/test_export.py::test_to_json_round_trips_g_graph_attr`

## Commits

- `712a780` test(65-01): add failing tests for schema_version read/write split + legacy v1.12 fixture (RED)
- `6aacf87` feat(65-01): implement schema_version read/write split + emit in to_json (GREEN)

## Verification

- `pytest tests/test_validate.py tests/test_export.py -q` — 46 passed.
- `pytest tests/ -q` — 2289 passed, 1 xfailed, 1 unrelated pre-existing failure (`tests/test_migration.py::test_preview_expands_risky_action_rows`, present on `main` before Plan 65-01; logged in `deferred-items.md`, out of scope for CCONF phase).
- Fixture sanity:
  - `grep -c '"schema_version"' tests/fixtures/legacy_v1_12_graph.json` → 0 (no version key, as required)
  - `grep -c '"nodes"' tests/fixtures/legacy_v1_12_graph.json` → 1
- All Plan 65-01 acceptance criteria met (see plan `<acceptance_criteria>` blocks).

## Deviations from Plan

None of substance. Notes:

- The plan's `<verify>` for Task 1 included a complex `! pytest …` exit-code check; in practice the tests fail at collection time with `ImportError` (the strongest possible RED signal), which still satisfies the RED gate. Confirmed visually before committing.
- A pre-existing failure in `tests/test_migration.py::test_preview_expands_risky_action_rows` was discovered while running the full suite. Confirmed unrelated by stashing 65-01 changes and re-running on `main`. Logged in `deferred-items.md` per scope-boundary rule.

## Known Stubs

None. The two new entry points are fully implemented. No placeholder data flows.

## Threat Flags

None — change introduces no new network surface, file-access patterns, or auth paths. Schema is widened by one optional-on-read / required-on-write top-level string key.

## Self-Check: PASSED

- `tests/fixtures/legacy_v1_12_graph.json` exists.
- Commits `712a780` and `6aacf87` exist on `main`.
- All 5 new tests pass and full suite shows no new failures attributable to this plan.
