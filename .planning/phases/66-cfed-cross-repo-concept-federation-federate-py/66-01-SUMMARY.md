---
phase: 66-cfed-cross-repo-concept-federation-federate-py
plan: 01
subsystem: federate
tags: [federation, merge-engine, tdd, cfed]
requires:
  - graphify/validate.py::validate_extraction_for_read
provides:
  - graphify/federate.py::federate
  - graphify/federate.py::build_manifest
  - graphify/federate.py::FederationCollisionError
affects: []
tech_stack:
  added: []
  patterns: [pure-function, deterministic-stdlib, AND-gate, lex-min-canonical-id]
key_files:
  created:
    - graphify/federate.py
    - tests/test_federate.py
    - tests/fixtures/peer_match/graph.json
    - tests/fixtures/peer_nomerge/graph.json
    - tests/fixtures/peer_collision_a/repo/graph.json
    - tests/fixtures/peer_collision_b/repo/graph.json
  modified: []
decisions: [D-66.3, D-66.4, D-66.5, D-66.7]
metrics:
  duration: ~10m
  tasks: 2
  files_created: 6
  tests_added: 11
  date: 2026-05-06
---

# Phase 66 Plan 01: federate.py merge engine (TDD) — Summary

Deterministic, stdlib-only federation merge engine that namespaces nodes
across repos and merges concept pairs via a multi-signal AND-gate (label +
neighborhood Jaccard ≥ 0.5 + shared source-file basename) with a
confidence_score-mean tiebreaker and lex-min canonical merged_id.

## Tasks Completed

| Task | Name                                            | Commit  |
| ---- | ----------------------------------------------- | ------- |
| 1    | RED — peer fixtures + failing federation tests  | b7f2b5e |
| 2    | GREEN — implement federate.py merge engine     | 3469826 |

## Behaviors Locked by Tests (CFED-02, CFED-03)

- **Namespacing (D-66.3 / D-66.7):** every node id rewritten as
  `{repo}::{original_id}`; all edge endpoints rewritten in lockstep.
- **AND-gate (D-66.4):** merge fires iff label-equality (case-folded) AND
  1-hop neighborhood-label Jaccard ≥ 0.5 AND ≥1 shared source_file basename.
  Each leg is independently exercised by `test_gate_label_fail`,
  `test_gate_jaccard_fail`, `test_gate_basename_fail`.
- **Tiebreaker (T-66.4):** when ≥2 peers compete for the same local target,
  winner = highest mean `confidence_score` across the peer's INFERRED
  neighborhood edges; `tiebreaker_score` recorded in manifest entry only
  when tiebreaker fired.
- **Canonical merged_id (D-66.7):** `min(contributing_namespaced_ids)` —
  lex-min, deterministic.
- **Collision (D-66.3):** `FederationCollisionError` raised when two
  `--federate-with` paths' `parent.name` collide; message format follows
  Phase 64 two-line stderr contract.
- **Determinism:** sorted-key JSON of two `build_manifest` calls is
  byte-identical; output node/edge lists are sorted.
- **No new deps:** AST scan asserts imports are a subset of
  `{__future__, json, pathlib, hashlib, os, tempfile, typing,
  graphify.validate, graphify.security}` — pure stdlib + existing graphify
  modules.

## Public API

```python
from graphify.federate import federate, build_manifest, FederationCollisionError

merged_extraction, merges = federate(
    extraction,        # local {"nodes": [...], "edges": [...]}
    peers,             # list[Path] of peer graph.json files
    local_repo="myrepo",
)
manifest = build_manifest(merges)  # sorted by merged_id, D-66.5 schema
```

The `merges` list entries match D-66.5 verbatim — Plan 02's manifest writer
can consume them with no transformation.

## Verification

- `pytest tests/test_federate.py -q` → **11 passed**
- `pytest tests/ -q` → 2329 passed, 1 xfailed, 1 pre-existing failure
  (`tests/test_migration.py::test_preview_expands_risky_action_rows` —
  documented in Phase 65 `deferred-items.md`, explicitly out of scope)
- AST allow-list scan: `OK` (no new dependencies)
- `grep -c "from __future__ import annotations" graphify/federate.py` → 1
- `grep -c "def federate" graphify/federate.py` → 1

## Deviations from Plan

None — plan executed exactly as written.

## Cross-Plan Handoff

Plan 02 (`build.py` wiring + manifest writer) consumes:
- `federate(extraction, peers, local_repo)` for the pipeline call
- `build_manifest(merges)` directly into `write_manifest()`
- `FederationCollisionError` propagated via the CLI two-line stderr handler

Plan 03 (report rendering) reads the manifest produced by Plan 02; no direct
dependency on `federate.py`.

## Self-Check: PASSED

- `graphify/federate.py` — FOUND
- `tests/test_federate.py` — FOUND
- `tests/fixtures/peer_match/graph.json` — FOUND
- `tests/fixtures/peer_nomerge/graph.json` — FOUND
- `tests/fixtures/peer_collision_a/repo/graph.json` — FOUND
- `tests/fixtures/peer_collision_b/repo/graph.json` — FOUND
- Commit b7f2b5e — FOUND
- Commit 3469826 — FOUND

## TDD Gate Compliance

- **RED gate:** `test(66-01): add failing federation engine tests + peer fixtures` (b7f2b5e) — confirmed RED via `ModuleNotFoundError: graphify.federate` before implementation
- **GREEN gate:** `feat(66-01): implement deterministic federation merge engine` (3469826) — all 11 tests pass
- **REFACTOR gate:** not needed; implementation landed clean on first iteration
