---
phase: 54-mcp-trace-obsidian-parity
plan: 1
subsystem: mcp+obsidian-tests
tags: [mcp, obsidian, parity, tdd, red, wave-1]
requires: [Phase 53 — round_trip.json fixture, build_from_json orientation contract]
provides: [16 named RED tests across 4 test files, 5 vault_parity expected-section fixtures]
affects:
  - tests/test_concept_code_mcp.py
  - tests/test_serve.py
  - tests/test_capability.py
  - tests/test_concept_code_obsidian.py
  - tests/fixtures/concept_code/vault_parity/
tech-stack:
  added: []
  patterns:
    - "QUERY_GRAPH_META_SENTINEL string-partition idiom for parsing helper return values"
    - "_wrap_sentinel('concept_code_relations', ...) boundary markers for round-trip parity"
key-files:
  created:
    - tests/test_concept_code_obsidian.py
    - tests/fixtures/concept_code/vault_parity/code_klass.md
    - tests/fixtures/concept_code/vault_parity/code_subklass.md
    - tests/fixtures/concept_code/vault_parity/code_test_klass.md
    - tests/fixtures/concept_code/vault_parity/moc_authservice.md
    - tests/fixtures/concept_code/vault_parity/moc_tokenstore.md
  modified:
    - tests/test_concept_code_mcp.py
    - tests/test_serve.py
    - tests/test_capability.py
decisions:
  - "Parse helper return via QUERY_GRAPH_META_SENTINEL string partition (not dict-direct)"
  - "MCP arg key is 'entity' for both concept_code_hops and entity_trace"
  - "Reuse Phase 53 round_trip.json fixture untouched (T-54-01 mitigation)"
  - "Backward-compat guard test_entity_trace_default_excludes_concept_code passes by design — must stay green through Wave 2"
metrics:
  completed_date: 2026-04-30
  duration_minutes: 18
  red_tests_landed: 16
  fixture_files_landed: 5
  commits: 2
---

# Phase 54 Plan 1: TDD RED — failing tests + vault-parity fixtures Summary

Wave 1 (TDD RED) of Phase 54 lands 16 named RED tests + 5 expected-section fixtures across 4 test files. Every CGRAPH-03 / CGRAPH-04 truth from `54-RESEARCH.md §"Phase Requirements → Test Map"` now has an executable assertion. Production code is untouched on disk; Waves 2–4 (Plans 02/03/04) will flip the assertions GREEN.

## New Tests by File

### `tests/test_concept_code_mcp.py` (6 RED — CGRAPH-03)

| # | Test | Decision | Behavior under test |
|---|------|----------|---------------------|
| 1 | `test_concept_code_hops_default_relations` | D-54.01 / D-54.03 | Omitting `relations` defaults to `["implements"]`; payload echoes `relations`, `traversal_steps`, `steps_by_relation`, AND `implements_traversal_steps` shim. |
| 2 | `test_concept_code_hops_unknown_relation_errors` | D-54.02 | `relations=["bogus"]` returns structured error envelope listing all 5 allowed values. |
| 3 | `test_concept_code_hops_empty_relations_errors` | D-54.02 | `relations=[]` returns `status=error` with "must not be empty" diagnostic. |
| 4 | `test_concept_code_hops_multi_relation_traversal` | D-54.01 / D-54.03 | `relations=["documents","tests"]` from `c_concept`; `steps_by_relation` carries both keys with positive counts; shim NOT active for non-implements-only set. |
| 5 | `test_concept_code_hops_payload_steps_by_relation` | D-54.03 | All-5-relation request: `set(steps_by_relation.keys()) == {5 relations}` and `traversal_steps == sum(values)`. |
| 6 | `test_concept_code_hops_backward_compat_implements_steps_key` | D-54.03 | Explicit `relations=["implements"]` (not omitted) still activates the shim — set-equality, not None-vs-list. |

### `tests/test_serve.py` (2 — CGRAPH-03)

| # | Test | Decision | Behavior under test |
|---|------|----------|---------------------|
| 7 | `test_entity_trace_default_excludes_concept_code` | D-54.04 | (Backward-compat seal) Default omitting `include_concept_code` MUST NOT add `concept_code_reachable` / `concept_code_steps_by_relation` keys. **Note:** passes today by design; must stay GREEN through Wave 2. |
| 8 | `test_entity_trace_includes_concept_code_when_requested` | D-54.04 | `include_concept_code=True` adds `concept_code_reachable: list[str]` and `concept_code_steps_by_relation: dict` (subset of 5 allowed relations). |

### `tests/test_capability.py` (1 — CGRAPH-03)

| # | Test | Decision | Behavior under test |
|---|------|----------|---------------------|
| 9 | `test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code` | D-54.01 / D-54.04 | `concept_code_hops.inputSchema.properties.relations` is `array<string>` default `["implements"]`; `entity_trace.inputSchema.properties.include_concept_code` is `boolean` default `false`. |

### `tests/test_concept_code_obsidian.py` (7 NEW — CGRAPH-04)

| # | Test | Decision | Behavior under test |
|---|------|----------|---------------------|
| 10 | `test_code_note_per_relation_sections_canonical_order` | D-54.07 | k_klass CODE note H2 headers form a subsequence of `[Implements, Documents, Tests, Realizes, Instantiates]`. |
| 11 | `test_concept_moc_inverse_sections_canonical_order` | D-54.08 | c_concept MOC H2 headers form a subsequence of `[Implemented by, Documented by, Tested by, Realized by, Instantiated by]`. |
| 12 | `test_empty_relation_section_suppressed` | D-54.07 | k_subklass note has only `## Instantiates`; the other 4 forward headers are absent. |
| 13 | `test_forward_parity_edges_to_wikilinks` | D-54.12 | Every concept↔code edge (when `_src` is code/test/document) appears as a wikilink under the matching forward H2 in src's note. |
| 14 | `test_backward_parity_wikilinks_to_edges` | D-54.12 | Every wikilink under any of the 10 Phase 54 H2 sections corresponds to a graph edge with the matching relation; total link count must equal graph edge count (no vacuous pass). |
| 15 | `test_per_relation_count_parity` | D-54.12 | For each of 5 relations: `forward_count == inverse_count == graph_edge_count`. |
| 16 | `test_round_trip_per_relation_sections_idempotent` | D-54.11 | Two `to_obsidian` runs produce byte-identical content within `<!-- graphify:concept_code_relations:start -->`/`...:end -->` markers; ≥1 sentinel block must exist (no vacuous pass). |

## Fixture Files

| File | Forward / Inverse | Relations covered |
|------|-------------------|-------------------|
| `vault_parity/code_klass.md` | forward | `## Implements` (AuthService), `## Realizes` (TokenStore) |
| `vault_parity/code_subklass.md` | forward | `## Instantiates` (AuthService) — empty-suppression of other 4 |
| `vault_parity/code_test_klass.md` | forward | `## Tests` (AuthService) |
| `vault_parity/moc_authservice.md` | inverse | `## Implemented by`, `## Documented by`, `## Tested by`, `## Instantiated by` |
| `vault_parity/moc_tokenstore.md` | inverse | `## Realized by` (Klass) |

## RED Confirmation

Command:
```
pytest tests/test_concept_code_mcp.py tests/test_serve.py tests/test_capability.py tests/test_concept_code_obsidian.py
```
Result on `main` after Wave 1 lands:
```
15 failed, 233 passed in 1.06s
```

**RED breakdown (15/16 fail; 1 backward-compat seal passes by design):**
- All 6 new `test_concept_code_mcp.py` tests fail (missing `relations` arg, missing `traversal_steps`/`steps_by_relation`/`implements_traversal_steps` shim, no error envelope for bogus values).
- `test_serve.py::test_entity_trace_default_excludes_concept_code` PASSES — it is a Phase 11 backward-compat seal: today's `_run_entity_trace` already omits concept_code keys, and Wave 2 must preserve that behavior. The "RED" validation table entry guards regression *after* Wave 2, not before.
- `test_serve.py::test_entity_trace_includes_concept_code_when_requested` fails (no `concept_code_reachable` / `concept_code_steps_by_relation` in meta).
- `test_capability.py::test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code` fails (`relations` and `include_concept_code` properties not yet declared in inputSchema).
- All 7 `test_concept_code_obsidian.py` tests fail (no per-relation section emission yet; no sentinel block; counts mismatch).

Sample failure output:
```
FAILED tests/test_concept_code_mcp.py::test_concept_code_hops_default_relations
  AssertionError: meta.get("relations") == ["implements"], got None

FAILED tests/test_concept_code_obsidian.py::test_per_relation_count_parity
  AssertionError: forward parity broken for implements: vault=0 graph=1
```

All failures are **semantic assertion errors** — no `ImportError`, no `SyntaxError`, no `KeyError` outside of the controlled `meta.get(...)` paths. RED for the right reasons.

## Phase 47 + Phase 53 Backward-Compat (still GREEN)

Command:
```
pytest tests/test_concept_code_mcp.py::test_concept_code_hops_golden_path \
       tests/test_serve.py::test_entity_trace_default_excludes_concept_code \
       tests/test_serve.py::test_entity_trace_insufficient_history \
       tests/test_serve.py::test_entity_trace_ok_timeline \
       tests/test_serve.py::test_entity_trace_alias_redirect \
       tests/test_capability.py::test_manifest_tool_names_match_registry \
       tests/test_export.py
```
Result:
```
31 passed, 2 warnings in 7.25s
```

Phase 47 `concept_code_hops` golden-path test still passes (helper signature unchanged on disk). Phase 11 `entity_trace` regression suite passes. `test_export.py` round-trip / dedup / naming tests pass. `round_trip.json` fixture is untouched (verified — only test files and new fixtures added in this plan).

## Files Changed

```
tests/test_concept_code_mcp.py    (+196 lines: helper + 6 RED tests)
tests/test_serve.py               (+47 lines: 2 RED tests)
tests/test_capability.py          (+34 lines: 1 RED test)
tests/test_concept_code_obsidian.py  (NEW, 348 lines: helpers + 7 RED tests)
tests/fixtures/concept_code/vault_parity/code_klass.md       (NEW)
tests/fixtures/concept_code/vault_parity/code_subklass.md    (NEW)
tests/fixtures/concept_code/vault_parity/code_test_klass.md  (NEW)
tests/fixtures/concept_code/vault_parity/moc_authservice.md  (NEW)
tests/fixtures/concept_code/vault_parity/moc_tokenstore.md   (NEW)
```

No production code modified. `tests/fixtures/concept_code/round_trip.json` untouched.

## Commits

| Hash | Task | Description |
|------|------|-------------|
| `ab9ec93` | Task 1 | Add 9 RED MCP tests for concept_code_hops widening + entity_trace + capability schema |
| `14fad1d` | Task 2 | Add 7 RED Obsidian per-relation parity tests + 5 vault_parity fixtures |

## Deviations from Plan

**None inline.** One contract-clarity note carried through into the SUMMARY:

- `test_entity_trace_default_excludes_concept_code` is a backward-compat seal that passes on `main` by design (Phase 11 envelope already excludes the new keys). The plan groups it with the 16 RED tests because the validation table sees it as the no-op-default truth for D-54.04. Holding to the orchestrator's "halt and report" rule: it is reported here rather than treated as a halt — Wave 2 must keep this test green, and any regression in Wave 2 will be caught immediately.

## Self-Check

Files exist:
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/test_concept_code_obsidian.py` — FOUND
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/fixtures/concept_code/vault_parity/code_klass.md` — FOUND
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/fixtures/concept_code/vault_parity/code_subklass.md` — FOUND
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/fixtures/concept_code/vault_parity/code_test_klass.md` — FOUND
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/fixtures/concept_code/vault_parity/moc_authservice.md` — FOUND
- `/Users/silveimar/Documents/silogia-repos/graphify/tests/fixtures/concept_code/vault_parity/moc_tokenstore.md` — FOUND

Commits exist:
- `ab9ec93` — FOUND (`tests(54-01): add 9 RED MCP tests for concept_code_hops widening + entity_trace + capability schema`)
- `14fad1d` — FOUND (`tests(54-01): add 7 RED Obsidian per-relation parity tests + 5 vault_parity fixtures`)

## Self-Check: PASSED

## EXECUTION COMPLETE
