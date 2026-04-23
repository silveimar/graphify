---
phase: 20-diagram-seed-engine
plan: 01
subsystem: analyze
tags: [analyze, auto-tag, user-seed, tag-writeback, diagram-seed, detection-only]
requirements: [SEED-02, SEED-03]
dependency_graph:
  requires:
    - graphify/analyze.py (god_nodes, _cross_community_surprises)
    - graphify/merge.py (_DEFAULT_FIELD_POLICY tags='union', compute_merge_plan)
  provides:
    - graphify.analyze.detect_user_seeds
    - possible_diagram_seed node attribute contract
    - tag-writeback denylist enforcement
  affects:
    - Plan 20-02 (seed.py) — will import god_nodes + detect_user_seeds
tech_stack:
  added: []
  patterns:
    - Node-attribute side-effect from selection functions
    - Grep denylist test for architecture invariant enforcement
    - Tolerant tag parser (isinstance gates before match)
key_files:
  created: []
  modified:
    - graphify/analyze.py
    - tests/test_analyze.py
decisions:
  - D-18 detection boundary enforced — analyze.py is the sole diagram-seed detector
  - Tag write-back remains routed exclusively through graphify.merge.compute_merge_plan (merge.py:70)
  - layout_hint normalizes empty slash-suffix ("gen-diagram-seed/") to None, not ""
metrics:
  duration_seconds: 282
  commits: 3
  tasks_completed: 2
  files_modified: 2
  completed: 2026-04-23
---

# Phase 20 Plan 01: analyze.py Diagram Seed Extension Summary

**One-liner:** Added `possible_diagram_seed` auto-tagging to `god_nodes()` and `_cross_community_surprises()`, introduced `detect_user_seeds()` reader for the `gen-diagram-seed[/type]` tag contract, and locked tag write-back to `graphify.merge.compute_merge_plan` via a grep denylist test.

## Scope Delivered

### 1. Auto-tag on selection functions (SEED-02)
- **`graphify/analyze.py:91`** — inside `god_nodes()` selection loop, added:
  ```python
  G.nodes[node_id]["possible_diagram_seed"] = True
  ```
  Only fires on nodes that pass the file-hub / concept-node filter AND land in the returned top-N list.
- **`graphify/analyze.py:387-388`** — inside `_cross_community_surprises()` dedup-emission loop, both endpoints of every emitted surprise are tagged. Resolved `_src_id`/`_tgt_id` are threaded through the sort and popped during dedup so the tag lands on the actual emitted-bridge nodes, not on pre-dedup candidates that get dropped.

### 2. `detect_user_seeds(G)` reader (SEED-02)
- **`graphify/analyze.py:687`** — new function with signature `(G: nx.Graph) -> dict[str, list[dict]]`.
- Reads `possible_diagram_seed` attribute → `auto_seeds`.
- Reads `tags` attribute:
  - `"gen-diagram-seed"` → `user_seeds` entry with `layout_hint=None`.
  - `"gen-diagram-seed/<type>"` → `user_seeds` entry with `layout_hint=<type>`.
  - `"gen-diagram-seed/"` (empty suffix) normalized to `layout_hint=None`.
- Tolerates malformed input: `tags=None`, `tags="string-not-list"`, or list entries that aren't strings — all silently skipped, no raise.

### 3. Tag write-back denylist (SEED-03)
- Grep denylist test (`test_tag_writeback_routed_only_through_compute_merge_plan`) scans `graphify/analyze.py` and (if present) `graphify/seed.py` for forbidden patterns:
  - `.write_text(`
  - `open(..., "w")` / `open(..., 'w')`
  - `write_note_directly`
- All three must be absent. The only legal write path is `graphify.merge.compute_merge_plan` (merge.py line 863) using the `tags: "union"` policy at line 70.
- Test gracefully skips the `seed.py` branch while that file does not yet exist (Plan 20-02 will create it).

## Tests Added

| # | Test | Guards |
|---|------|--------|
| A | `test_god_nodes_tags_possible_diagram_seed` | Selection loop side-effect on G + non-selected nodes stay untagged |
| B | `test_cross_community_surprises_tags_endpoints` | Both endpoints of every emitted bridge tagged |
| C | `test_god_nodes_returns_shape_unchanged` | Public return schema regression guard |
| D | `test_detect_user_seeds_reads_tags` | `gen-diagram-seed` + `gen-diagram-seed/workflow` parsed |
| E | `test_detect_user_seeds_auto_seeds_from_attribute` | `possible_diagram_seed=True` → `auto_seeds` entries |
| F | `test_detect_user_seeds_tolerates_malformed_tags` | None / non-list / non-string elements handled |
| G | `test_detect_user_seeds_slash_hint_empty_suffix` | Trailing-slash tag normalizes hint to None |
| H | `test_tag_writeback_routed_only_through_compute_merge_plan` | Grep denylist enforces D-08 / SEED-03 |

Final suite: `pytest tests/ -q` → **1485 passed, 2 warnings** (all pre-existing third-party deprecation warnings, unrelated).

## Commits

| Hash | Gate | Message |
|------|------|---------|
| `4597890` | RED | `test(20-01): add failing tests for possible_diagram_seed auto-tagging` |
| `6387230` | GREEN — Task 1 | `feat(20-01): auto-tag possible_diagram_seed on god nodes and cross-community bridges` |
| `48cae54` | GREEN — Task 2 | `feat(20-01): add detect_user_seeds() reader and tag-writeback denylist test` |

## CONTEXT.md Correction

CONTEXT.md D-08 refers to `vault_adapter.py::compute_merge_plan`. That module does not exist. The canonical location is **`graphify.merge.compute_merge_plan`** (confirmed in PATTERNS.md and verified at `graphify/merge.py:863`). Plan 20-02 should import from `graphify.merge`, not a non-existent `vault_adapter`.

## Handoff to Plan 20-02

Plan 20-02 (`graphify/seed.py`) must:

```python
from graphify.analyze import god_nodes, detect_user_seeds
```

and **must not** reimplement either routine. Its responsibilities:

1. Compose `god_nodes(G)` + `detect_user_seeds(G)` to produce the seed set.
2. Add the `--vault` flag that drives tag write-back via `graphify.merge.compute_merge_plan` — any other write path is blocked by Test H.
3. Validate the `layout_hint` string against the 6-entry allowlist (T-20-01-02 carry-forward): `cuadro-sinoptico`, `workflow`, `architecture`, `mind-map`, `repository-components`, `glossary-graph`.

## Deviations from Plan

None — plan executed exactly as written. The Task 2 tests were committed together with the Task 1 RED commit (test H passed trivially on pre-Task-2 code, tests D–G failed as expected). This consolidates test authorship into one RED commit, still respecting RED→GREEN ordering per gate.

## TDD Gate Compliance

- RED commit exists: `4597890` (`test(20-01): ...`)
- GREEN commit exists: `6387230` (`feat(20-01): auto-tag ...`) and `48cae54` (`feat(20-01): add detect_user_seeds ...`)
- REFACTOR gate: not needed — implementation landed clean on first GREEN pass.

## Self-Check: PASSED

- Commit `4597890` found in `git log`
- Commit `6387230` found in `git log`
- Commit `48cae54` found in `git log`
- `graphify/analyze.py` modified (detect_user_seeds at line 687, auto-tags at 91/387/388)
- `tests/test_analyze.py` modified (47 tests total, 8 new)
- `pytest tests/ -q` exits 0 (1485 passed)
