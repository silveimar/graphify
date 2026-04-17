---
phase: 10-cross-file-semantic-extraction
plan: "05"
subsystem: report
tags: [report, dedup, audit-trail, security, sanitization]
dependency_graph:
  requires:
    - 10-03  # graphify/dedup.py write_dedup_reports (dedup_report dict schema)
  provides:
    - GRAPH_REPORT.md Entity Dedup section (D-04 audit trail third leg)
  affects:
    - graphify/report.py generate() signature
    - tests/test_report.py (5 new tests)
tech_stack:
  added: []
  patterns:
    - defense-in-depth label sanitization: sanitize_label (security.py) + _sanitize_md (report.py)
key_files:
  modified:
    - graphify/report.py
    - tests/test_report.py
decisions:
  - "dedup_report param placed last in generate() signature to preserve backward compatibility for all existing callers"
  - "truncate at 10 merges with overflow reference to dedup_report.json to keep GRAPH_REPORT.md scannable"
  - "defense-in-depth: both sanitize_label (HTML escape + length cap from security.py) and _sanitize_md (backtick/angle-bracket strip from report.py) applied to every canonical and eliminated label"
metrics:
  duration_minutes: 8
  completed: "2026-04-16"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 2
requirements:
  - GRAPH-02
---

# Phase 10 Plan 05: Entity Dedup section in GRAPH_REPORT.md Summary

**One-liner:** Optional `dedup_report` parameter added to `generate()` appending a sanitized "Entity Dedup" section when entity merges occurred, completing the D-04 three-leg audit trail.

## What Was Built

`graphify/report.py::generate()` now accepts an optional `dedup_report: dict | None = None` parameter (last in the signature, backward compatible). When the dict contains a non-empty `merges` list, the function appends an `## Entity Dedup` section to GRAPH_REPORT.md with:

- A summary line: `N entities merged · X nodes → Y nodes`
- Up to 10 merge entries in the form: `` `canonical_label` ← elim1, elim2  [fuzzy=0.957, cos=0.912] ``
- An overflow line when merges > 10: `(+N more — see dedup_report.json)`

When `dedup_report` is `None` or has an empty merges list, output is byte-identical to pre-Phase-10 behavior.

## Final `generate()` Parameter List

```python
def generate(
    G: nx.Graph,
    communities: dict[int, list[str]],
    cohesion_scores: dict[int, float],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    detection_result: dict,
    token_cost: dict,
    root: str,
    suggested_questions: list[dict] | None = None,
    usage_data: dict | None = None,
    dedup_report: dict | None = None,  # Phase 10, D-04
) -> str:
```

## Insertion Point

The Entity Dedup block is inserted immediately before `return "\n".join(lines)`, after the `## Usage Patterns` section (the last previously-rendered section). Section order in GRAPH_REPORT.md is now:

1. Corpus Check
2. Summary
3. Community Hubs
4. God Nodes
5. Surprising Connections
6. Hyperedges (if any)
7. Communities
8. Ambiguous Edges (if any)
9. Knowledge Gaps (if any)
10. Suggested Questions (if any)
11. Usage Patterns (if any)
12. **Entity Dedup** (if any — new in Phase 10)

## Defense-in-Depth Sanitization Chain (T-10-02)

All `canonical_label` and eliminated-node labels pass through two layers:

1. `sanitize_label(str(...))` — from `graphify/security.py`: HTML-escapes `<>`, strips control chars, caps at 256 chars
2. `_sanitize_md(...)` — from `report.py` itself: replaces backticks with `'`, converts `<`/`>` to `&lt;`/`&gt;`

This mirrors the pattern used by `dedup.py` for `dedup_report.md`.

## Test Coverage Matrix (5 new tests)

| Test | Scenario | Assertion |
|------|----------|-----------|
| `test_generate_no_dedup_section_when_none` | `dedup_report` omitted (default None) | `## Entity Dedup` absent |
| `test_generate_no_dedup_section_when_empty` | `dedup_report` with `merges: []` | `## Entity Dedup` absent |
| `test_generate_renders_dedup_section_with_merges` | 1 merge with labels + scores | section present, labels + scores in output |
| `test_generate_dedup_section_sanitizes_labels` | `<script>alert(1)</script>` as canonical_label | raw `<script>` absent from section; `alert` still present (escaped) |
| `test_generate_dedup_section_truncates_above_10` | 15 merges | first 10 present, Label14 absent, `+5 more` present |

`pytest tests/test_report.py -q`: 45 passed (40 pre-existing + 5 new).
`pytest tests/ -q`: 1145 passed, 3 pre-existing failures in `test_delta.py::test_cli_snapshot_*` (unrelated to this plan — snapshot CLI command not yet implemented).

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Description |
|------|-------------|
| 12e388c | feat(10-05): add Entity Dedup section to GRAPH_REPORT.md (D-04) |

## Self-Check: PASSED

- [x] `graphify/report.py` modified — confirmed at commit 12e388c
- [x] `tests/test_report.py` modified — confirmed at commit 12e388c
- [x] `grep -n 'dedup_report: dict | None = None' graphify/report.py` — 1 match (line 67)
- [x] `grep -n '## Entity Dedup' graphify/report.py` — 1 match (line 254)
- [x] `grep -n 'sanitize_label' graphify/report.py` — 3 matches (import + 2 call sites)
- [x] 5 new tests pass, 0 regressions introduced
