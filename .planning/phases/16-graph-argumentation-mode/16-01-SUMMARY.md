---
phase: 16
plan: "01"
subsystem: argue
tags: [argue, substrate, dataclass, zero-llm, validator, jaccard, tdd]
dependency_graph:
  requires: []
  provides:
    - graphify/argue.py::ArgumentPackage
    - graphify/argue.py::PerspectiveSeed
    - graphify/argue.py::NodeCitation
    - graphify/argue.py::populate
    - graphify/argue.py::validate_turn
    - graphify/argue.py::compute_overlap
    - graphify/argue.py::ROUND_CAP
    - graphify/argue.py::MAX_TEMPERATURE
  affects:
    - graphify/serve.py (Plan 02 will register argue_topic MCP tool)
    - graphify/skill.md (Plan 03 will add SPAR-Kit orchestration)
tech_stack:
  added: []
  patterns:
    - "@dataclass with field(default_factory=list) — mirrors enrich.py EnrichmentResult"
    - "local import inside function body to avoid circular import at module load"
    - "budget = max(50, min(int(budget), 100000)) clamp — matches >=6 serve.py tool cores"
    - "pure error-list return pattern — mirrors validate.py::validate_extraction"
    - "silent-ignore on malformed input — mirrors serve.py _run_chat_core lines 1210-1224"
key_files:
  created:
    - graphify/argue.py
    - tests/test_argue.py
    - tests/fixtures/argue_citations.json
    - tests/fixtures/argue_fabricated.json
  modified: []
decisions:
  - "A2 from 16-RESEARCH.md: pass communities dict as kwarg to populate() rather than importing _communities_from_graph from serve — keeps argue.py decoupled from serve.py internal state"
  - "Local import of _extract_entity_terms, _score_nodes, _bfs inside populate() body to avoid circular import at module load"
  - "19 tests written (plan said 18+) — added extra validate_turn_missing_cites_key test covering the .get default path"
metrics:
  duration: "3m 18s"
  completed: "2026-04-22"
  tasks_completed: 2
  files_created: 4
  tests_added: 19
---

# Phase 16 Plan 01: argue.py Zero-LLM Substrate Summary

**One-liner:** Zero-LLM Python substrate for graph argumentation — ArgumentPackage/PerspectiveSeed/NodeCitation dataclasses plus populate(), validate_turn(), compute_overlap() composing existing serve.py BFS primitives, with ROUND_CAP=6 and MAX_TEMPERATURE=0.4 constants.

## What Was Built

`graphify/argue.py` — the pure Python substrate for Phase 16 graph argumentation mode. No LLM calls anywhere in the module. All graph traversal composes existing `serve.py` primitives via a local import inside `populate()`.

### Dataclasses

- `NodeCitation(node_id, label, source_file)` — a single cited graph node in a persona turn
- `PerspectiveSeed(lens)` — one of 4 fixed lens personas (security/architecture/complexity/onboarding)
- `ArgumentPackage(subgraph, perspectives, evidence)` — the packaged result of `populate()`

### Functions

- `populate(G, topic, *, scope, budget, node_ids, community_id, communities)` — builds an evidence subgraph from the full knowledge graph via topic resolution, explicit node_ids, or community membership; always returns 4 fixed perspectives; budget-clamped
- `validate_turn(turn, G)` — pure fabrication guard; returns list of `node_id`s in `turn["cites"]` not present in `G.nodes`; empty list = valid turn
- `compute_overlap(cite_sets)` — Jaccard similarity across non-abstain cite sets; drops empty sets before computation; requires >=2 non-empty sets

### Constants

- `ROUND_CAP = 6` — hard cap on debate rounds (D-06/ARGUE-08)
- `MAX_TEMPERATURE = 0.4` — enforced at skill.md LLM call sites (D-04)

## Tests

`tests/test_argue.py` — 19 unit tests covering:

| Test | Requirement |
|------|-------------|
| test_argument_package_fields | ARGUE-02 |
| test_four_perspectives | ARGUE-02 D-01 |
| test_populate_returns_argument_package | ARGUE-01 |
| test_populate_scope_subgraph | ARGUE-01 D-03 |
| test_populate_scope_community | ARGUE-01 D-03 |
| test_populate_empty_topic | ARGUE-01 silent-ignore |
| test_populate_budget_clamp | ARGUE-01 D-02 |
| test_validate_turn_valid | ARGUE-05 D-08 |
| test_validate_turn_fabricated | ARGUE-05 D-08 (fixture-driven) |
| test_validate_turn_empty_cites | ARGUE-05 D-08 |
| test_validate_turn_missing_cites_key | ARGUE-05 D-10 |
| test_compute_overlap_jaccard | ARGUE-08 D-06 |
| test_compute_overlap_drops_abstentions | ARGUE-08 D-06 Pitfall 6 |
| test_compute_overlap_all_empty | ARGUE-08 D-06 |
| test_compute_overlap_single_nonempty | ARGUE-08 D-06 |
| test_round_cap_constant | ARGUE-08 D-06 |
| test_max_temperature_constant | ARGUE-08 D-04 |
| test_argue_zero_llm_calls | ARGUE-03 (grep-based) |
| test_blind_label_harness_intact | ARGUE-06 SC4 (grep-based) |

## TDD Gate Compliance

- RED commit: `6fcc612` — `test(16-01): add failing tests for argue.py substrate` — all 19 tests failed with `ModuleNotFoundError: No module named 'graphify.argue'`
- GREEN commit: `48e8577` — `feat(16-01): implement argue.py zero-LLM substrate (ARGUE-01/02/03/05/08)` — all 19 tests pass, full suite 1403 passed

## Deviations from Plan

### Minor Adjustments

**1. [Rule 1 - Enhancement] 19 tests instead of 18**
- **Found during:** Task 1 authoring
- **Issue:** The `test_validate_turn_missing_cites_key` test was listed in the plan's behavior block but the count said "18+". Added it as the 19th test because it covers the `.get("cites", [])` default path — a correctness case.
- **Impact:** None — plan said "12+ cases" and "18+"; 19 satisfies both.
- **Commit:** 6fcc612

None — plan executed as written. All constraints (D-01..D-10, ROUND_CAP=6, MAX_TEMPERATURE=0.4, zero-LLM invariant, Phase 9 harness anchor) honored exactly.

## Requirements Addressed

- ARGUE-01: populate() function with topic/subgraph/community scopes
- ARGUE-02: ArgumentPackage, PerspectiveSeed, NodeCitation dataclasses with correct field types
- ARGUE-03: Zero-LLM invariant enforced and grep-tested
- ARGUE-05: validate_turn() fabrication guard with fixture-driven negative test
- ARGUE-06: Phase 9 blind-label harness at skill.md:1512 verified unmodified
- ARGUE-08: ROUND_CAP=6, MAX_TEMPERATURE=0.4, compute_overlap() with abstention drop

## Known Stubs

None — all functions are fully implemented. `populate()` wires to real serve.py primitives (`_extract_entity_terms`, `_score_nodes`, `_bfs`). No placeholder data.

## Threat Flags

None — argue.py introduces no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All threat mitigations from the plan's threat register are implemented (T-16-01 through T-16-04, T-16-06, Zero-LLM invariant, Phase 9 harness deletion guard).

## Self-Check: PASSED

- `graphify/argue.py` — FOUND
- `tests/test_argue.py` — FOUND
- `tests/fixtures/argue_citations.json` — FOUND
- `tests/fixtures/argue_fabricated.json` — FOUND
- Task 1 commit `6fcc612` — FOUND
- Task 2 commit `48e8577` — FOUND
- `pytest tests/test_argue.py -q` — 19 passed
- `pytest tests/ -q` — 1403 passed, 0 failures
