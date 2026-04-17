---
phase: 10-cross-file-semantic-extraction
plan: "03"
subsystem: dedup
tags: [dedup, graph, extraction, entity-resolution, security]
dependency_graph:
  requires:
    - 10-cross-file-semantic-extraction/01  # schema extension + fake_encoder fixture
    - graphify/security.py                  # sanitize_label
    - graphify/cache.py                     # file_hash for corpus_hash
  provides:
    - graphify/dedup.py                     # dedup(), write_dedup_reports(), corpus_hash()
  affects:
    - graphify pipeline (detect -> extract -> dedup -> build_graph)
    - tests/test_dedup.py
tech_stack:
  added:
    - html (stdlib) — HTML-escape for T-10-02 label sanitization in _render_dedup_md
  patterns:
    - Union-find for transitive merge grouping
    - 4-char prefix blocking + length-ratio guard (O(N log N) candidate reduction)
    - Atomic write via tmp file + os.replace (cache.py pattern)
    - Optional-dep guard: sentence-transformers lazy-loaded, RuntimeError on missing
key_files:
  created:
    - graphify/dedup.py
  modified:
    - tests/test_dedup.py  # replaced Wave 0 stub with full GRAPH-02/03/04 test matrix
decisions:
  - "Used html.escape(sanitize_label(label)) in _render_dedup_md — security.py docstring explicitly states html.escape() is needed for HTML injection contexts (T-10-02 deviation auto-fixed Rule 2)"
  - "Removed 'relabel_nodes' from docstring comment to satisfy 0-matches acceptance criterion"
metrics:
  duration_minutes: 6
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_passing: 22
  completed_date: "2026-04-16"
---

# Phase 10 Plan 03: Entity Deduplication (graphify/dedup.py) Summary

**One-liner:** Fuzzy+cosine AND-gate deduplication with union-find grouping, dict-only edge re-routing, D-09 canonical tie-break, and T-10-01/T-10-02 security hardening.

## What Was Built

`graphify/dedup.py` — a 590-line pure-function module that slots between `extract()` and `build_graph()` in the pipeline (D-03). Takes an extraction dict, returns `(dedup'd_extraction, report_dict)`.

### Public API

```python
def dedup(
    extraction: dict,
    *,
    fuzzy_threshold: float = 0.90,   # D-02
    embed_threshold: float = 0.85,   # D-02
    cross_type: bool = False,         # D-13
    encoder=None,                     # callable(list[str]) -> ndarray | None
) -> tuple[dict, dict]:
    """Returns (dedup'd_extraction, report_dict)."""

def write_dedup_reports(report: dict, out_dir: Path) -> None:
    """Atomically write dedup_report.json + dedup_report.md inside out_dir.
    Raises ValueError if out_dir escapes cwd (T-10-01).
    """

def corpus_hash(file_paths: list[str]) -> str:
    """SHA256 over sorted per-file hashes for dedup cache keying."""
```

### Private Helpers (14)

| Helper | Purpose |
|--------|---------|
| `_get_model()` | Lazy-load sentence-transformers; RuntimeError if not installed |
| `_encode_labels(labels, encoder)` | Delegate to injected encoder or lazy model |
| `_fuzzy_ratio(a, b)` | Case-insensitive difflib.SequenceMatcher.ratio() |
| `_build_prefix_blocks(nodes)` | Group node indices by 4-char label prefix |
| `_candidate_pairs(nodes, blocks, *, fuzzy_threshold, cross_type)` | O(N log N) blocking + length-ratio guard + fuzzy gate |
| `_apply_embedding_gate(nodes, candidates, *, encoder, embed_threshold, cross_type)` | Cosine gate over candidate pairs |
| `_cosine(a, b)` | Dot product on normalized vectors, rounded to 3 decimals |
| `_union_groups(passing, n_nodes)` | Union-find: transitive merge groups from passing pairs |
| `_compute_pre_degree(nodes, edges)` | Pre-dedup undirected graph degree for D-09 tie-break |
| `_select_canonical(candidate_ids, nodes_by_id, pre_degree)` | D-09: longest label -> degree -> alphabetical |
| `_merge_extraction(extraction, merge_map, provenance)` | Dict-only edge re-routing + weight/confidence aggregation |
| `_build_report(...)` | Construct dedup_report dict with alias_map + merges list |
| `_empty_report(total_before, total_after)` | Zero-merge report for empty inputs |
| `_render_dedup_md(report)` | HTML-escaped markdown rendering (T-10-02) |

## Test Results

**22 tests, 22 passed.** Full matrix covered:

| Test | Requirement |
|------|-------------|
| `test_empty_extraction_returns_empty_report` | Baseline |
| `test_dedup_produces_report` | Report schema |
| `test_fuzzy_threshold_respected` | GRAPH-02 fuzzy gate |
| `test_cosine_threshold_respected` | GRAPH-02 cosine gate |
| `test_both_gates_pass_triggers_merge` | GRAPH-02 AND semantics |
| `test_cross_type_blocked_by_default` | D-13 |
| `test_cross_type_allowed_with_flag` | D-13 cosine-only path |
| `test_no_dangling_edges_after_merge` | GRAPH-03 edge re-routing |
| `test_edge_weight_summed` | D-10 weight=sum |
| `test_confidence_promotion` | D-10 confidence enum |
| `test_self_loops_dropped` | Pitfall 6 |
| `test_canonical_label_selection` | D-09 longest label |
| `test_canonical_tie_break_by_degree` | D-09 degree tie-break |
| `test_canonical_tie_break_alphabetical` | D-09 alphabetical tie-break |
| `test_provenance_fields` | D-11 merged_from + source_file list |
| `test_cross_source_graph04_acceptance` | GRAPH-04 stretch |
| `test_report_path_confined` | T-10-01 |
| `test_canonical_label_sanitized` | T-10-02 |
| `test_determinism_golden_report` | Byte-identical repeated runs |
| `test_write_reports_creates_both_files` | Atomic write |
| `test_corpus_hash_deterministic` | Order-independent hash |
| `test_corpus_hash_changes_on_added_file` | Cache invalidation |

GRAPH-04 acceptance test passes: with `cross_type=True` and `_forced_merge_encoder`, the multi_file_extraction fixture (auth.py AuthService + api.py auth_service + tests/test_auth.py AuthService + docs/auth.md Authentication Service) merges into one canonical with 3+ contributing source_files.

## Commits

| Hash | Description |
|------|-------------|
| `db9a14f` | `test(10-03)`: RED phase — failing test file with full matrix |
| `165737f` | `feat(10-03)`: GREEN phase — graphify/dedup.py implementation |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Security] html.escape() required for T-10-02 MD label output**
- **Found during:** Task 1 GREEN phase (test_canonical_label_sanitized failed)
- **Issue:** `security.sanitize_label()` strips control chars and caps length but does NOT HTML-escape. Its own docstring states "For direct HTML injection, wrap the result with html.escape()." The plan spec said to use `sanitize_label()` but did not mention the additional `html.escape()` wrap needed.
- **Fix:** Changed `_render_dedup_md` to apply `html.escape(sanitize_label(label))` for every label embedding in the MD output. Added `import html` to module imports.
- **Files modified:** `graphify/dedup.py`
- **Commit:** `165737f`

**2. [Rule 1 - Bug] Comment reference to `relabel_nodes` in docstring**
- **Found during:** Acceptance criteria check (`grep -n 'relabel_nodes' graphify/dedup.py` returned 1 match)
- **Issue:** Docstring said "Never calls nx.relabel_nodes (Pitfall 1)." — the word appeared in a comment, triggering the grep check.
- **Fix:** Rewrote docstring to "Operates on dicts only — never on NetworkX graphs (Pitfall 1 compliance)" — preserves intent, eliminates the literal string match.
- **Files modified:** `graphify/dedup.py`
- **Commit:** `165737f` (in-place before commit)

## Security Hardening

- **T-10-01** (path confinement): `write_dedup_reports` resolves `out_dir` and calls `.relative_to(cwd)`, raising `ValueError` with "escapes" in message if path escapes cwd.
- **T-10-02** (label sanitization): `_render_dedup_md` applies `html.escape(sanitize_label(label))` to every canonical and eliminated label before embedding in the `.md` output. `dedup_report.json` stores raw labels (JSON serialization handles escaping safely).

## Determinism Strategy

- `alias_map` built via `sorted(merge_map.items())`
- `provenance` iteration via `sorted(provenance.items())`
- `eliminated` records sorted by ID within each merge entry
- `json.dumps(report, ..., sort_keys=True)` in atomic write
- Union-find iterates over `sorted(seen)` for deterministic group formation
- Cosine similarity rounded to 3 decimals before threshold comparison (cross-platform float stability)

## Known Stubs

None — all public functions fully wired. No placeholder data or hardcoded empty returns in the main code path.

## Threat Flags

None. No new network endpoints, auth paths, or trust-boundary schema changes beyond what was planned in the threat model.

## Self-Check: PASSED

- `graphify/dedup.py` exists: FOUND
- `tests/test_dedup.py` exists: FOUND
- Commits `db9a14f`, `165737f` exist in git log: CONFIRMED
- `grep -n 'relabel_nodes' graphify/dedup.py`: 0 matches
- 17 public+private functions: CONFIRMED
- 22 tests passing: CONFIRMED
- No regressions: 3 pre-existing test_delta.py failures unchanged
