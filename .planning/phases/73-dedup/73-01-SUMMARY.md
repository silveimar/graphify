---
phase: 73
plan: 01
subsystem: dedup-spike
tags: [dedup, spike, measurement, sha256, fingerprint]
requires: []
provides:
  - scripts/dedup_spike.py (CLI + pure functions for fingerprint/collision/sem-sim cross-check)
  - tests/test_dedup_spike.py (14 unit tests for normalize/fingerprint/grouping/coverage/end-to-end)
affects: []
tech-stack:
  added: []
  patterns: [pure-function-pipeline-with-thin-cli-shell, stdlib-only]
key-files:
  created:
    - scripts/dedup_spike.py
    - tests/test_dedup_spike.py
  modified: []
decisions:
  - Used CONTEXT-locked normalization recipe verbatim (lower -> [^\w\s] strip -> collapse_ws)
  - Description fallback chain: enriched_description -> description -> "" (per RESEARCH override #1)
  - Concept-node universe: {document, paper, image, rationale}; --include-code flag opt-in
  - Default min_score=0.0 for sem-sim coverage (any edge counts)
metrics:
  duration: ~2m
  completed: 2026-05-08
  tasks: 2
  files: 2
  tests: 14
---

# Phase 73 Plan 01: Dedup Measurement Spike — Script + Tests Summary

Implemented `scripts/dedup_spike.py` (Phase 73 DEDUP measurement-only CLI) and `tests/test_dedup_spike.py` (14 unit tests, all passing) per locked CONTEXT recipe and RESEARCH overrides.

## What was built

**`scripts/dedup_spike.py`** — pure-function pipeline + thin argparse CLI:
- `normalize(s)` — CONTEXT recipe: `lower -> [^\w\s] strip -> collapse_ws`
- `fingerprint(label, description)` — `sha256(norm(label) + "|" + norm(description[:200]))`
- `select_concept_nodes(nodes, include_code=False)` — filters to {document, paper, image, rationale}
- `group_by_fingerprint(nodes)` — collision-only groups (len > 1)
- `semsim_pairs(edges, min_score)` — frozenset pairs of `relation == "semantically_similar_to"` edges
- `collision_is_covered(group, semsim)` — True iff every node in group has at least one sem-sim link to another in group
- `load_graph_json(path)` — accepts either `links` or `edges` key (networkx node_link_data variants)
- `classify_corpus(nodes, edges, include_code, min_score)` — returns total/collision_groups/raw/residual counts and rates
- `emit_markdown(per_corpus, min_score)` — per-corpus + aggregate stats table, decision rule line, 20-row collision-sample appendix
- `main(argv)` — argparse CLI with `name=path` positional syntax, `--min-score`, `--include-code`

**`tests/test_dedup_spike.py`** — 14 pytest tests covering all 14 behaviors enumerated in plan task 2 (normalize basic/empty/None, fingerprint determinism/normalization/truncation, grouping singletons, semsim filtering/min_score, coverage full/partial cliques, JSON loader links/edges, concept-node code filtering with/without flag, end-to-end classify_corpus).

## Verification

- `python3 scripts/dedup_spike.py --help` — exits 0, prints usage
- `pytest tests/test_dedup_spike.py -q` — 14 passed in 0.05s

## Deviations from Plan

None — plan executed exactly as written. All exact code blocks from `<action>` were used verbatim.

## Commits

- `6867169` — feat(73-01): add dedup measurement spike script and tests

## Self-Check: PASSED

- scripts/dedup_spike.py: FOUND
- tests/test_dedup_spike.py: FOUND
- commit 6867169: FOUND
- 14/14 tests passing
