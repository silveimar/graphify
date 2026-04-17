---
phase: 10-cross-file-semantic-extraction
plan: "08"
subsystem: analyze
tags: [gap-closure, uat-test-6, source_file, list-tolerance, pipeline-composition]
dependency_graph:
  requires: [10-01, 10-03]
  provides: [list-safe-source_file-reads, dedup-analyze-pipeline-e2e]
  affects: [analyze.py, report.py, export.py, dedup.py]
tech_stack:
  added: []
  patterns:
    - _iter_sources() normalizer helper for str|list[str]|None -> list[str]
    - _fmt_source_file() flattener for display/sort contexts
    - _fmt_source() defense-in-depth in report.py renderer
key_files:
  created:
    - tests/test_dedup_pipeline.py
    - tests/fixtures/dedup_composed_extraction.json
  modified:
    - graphify/analyze.py
    - graphify/report.py
    - graphify/export.py
    - graphify/dedup.py
    - tests/test_analyze.py
decisions:
  - _iter_sources placed in analyze.py (not a shared _schema.py) to avoid circular imports; re-exported to export.py via direct import
  - _fmt_source_file used at emit sites in analyze.py so source_files list values are always str by the time they reach report.py / callers
  - _fmt_source added to report.py as defense-in-depth (handles any residual list values from external callers)
  - export.py sort key and sanitize_label call site both fixed in Task 3 (out-of-plan discovery, Rule 1 auto-fix)
metrics:
  duration: ~18 minutes
  completed: "2026-04-17"
  tasks: 3
  files_changed: 6
---

# Phase 10 Plan 08: source_file list[str] Gap Closure (UAT Test 6) Summary

**One-liner:** `_iter_sources`/`_fmt_source_file` helpers make every analyze.py + report.py + export.py `source_file` read site tolerate `str | list[str]`, closing the `TypeError: expected str, bytes or os.PathLike object, not list` crash in the composed `dedup -> build -> analyze` pipeline.

## Commits

| SHA | Type | Description |
|-----|------|-------------|
| 45ae309 | RED | test(10-08): add RED regression tests for source_file: list[str] composed pipeline |
| 06a66cf | GREEN | fix(10-08): handle source_file: list[str] in analyze.py + report.py (closes UAT gap, test 6) |
| a1b7582 | REFACTOR | refactor(10-08): fix export.py source_file list[str] crash sites + annotate dedup write site |

## Call Sites Fixed in analyze.py

| Site | Line (before) | Function | Issue | Fix |
|------|---------------|----------|-------|-----|
| `_is_file_node` | ~27 | `_is_file_node` | `Path(list)` TypeError | `any(label == _Path(s).name for s in _iter_sources(source_file))` |
| `surprising_connections` set | ~84 | `surprising_connections` | set comprehension included raw list values | Flattened via `_iter_sources` in nested comprehension |
| `_is_concept_node` | ~103-111 | `_is_concept_node` | `source.split("/")` AttributeError on list | `_iter_sources` → `any("." in s.split("/")[-1] for s in sources)` |
| `_cross_file_surprises` equality | ~213 | `_cross_file_surprises` | `u_source == v_source` unreliable on list | Normalize to `tuple(sorted(_iter_sources(...)))` then compare tuples |
| `_cross_file_surprises` emit | ~255-263 | `_cross_file_surprises` | Raw list in `source_files[0/1]` → Python list repr in report | `_fmt_source_file()` at all three emit sites |
| `_cross_community_surprises` betweenness emit | ~299-310 | `_cross_community_surprises` | Same raw list issue | `_fmt_source_file()` |
| `_cross_community_surprises` community emit | ~338 | `_cross_community_surprises` | Same | `_fmt_source_file()` |

## Call Sites Fixed in export.py (Task 3 auto-fix, Rule 1)

| Site | Line | Issue | Fix |
|------|------|-------|-----|
| `sanitize_label(data.get("source_file",""))` | ~372 | `sanitize_label` expects str; list crashes `_CONTROL_CHAR_RE.sub` | `sanitize_label(_fmt_source_file(...))` |
| `sort key: nd[1].get("source_file","")` | ~708 | Python 3 raises `TypeError` comparing list vs str in tuple sort | `_fmt_source_file(nd[1].get("source_file",""))` |

## New Helpers

### `graphify/analyze.py`

```python
def _iter_sources(source_file: str | list[str] | None) -> list[str]:
    """Normalize source_file to a flat list of non-empty strings."""

def _fmt_source_file(source_file: str | list[str] | None) -> str:
    """Flatten source_file to comma-joined display string for output dicts / sort keys."""
```

### `graphify/report.py`

```python
def _fmt_source(value) -> str:
    """Defense-in-depth renderer: list[str] -> comma-joined, str -> unchanged."""
```

## Test Delta

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| Total passing | 1161 | 1174 | +13 |
| test_analyze.py | 28 | 35 | +7 |
| test_dedup_pipeline.py | 0 | 3 | +3 |
| New fixture | — | dedup_composed_extraction.json | created |

## UAT Test 6 Closure

Manual reproduction confirmed:

```python
data = json.loads(Path('tests/fixtures/multi_file_extraction.json').read_text())
deduped, _ = dedup(data, encoder=fake_enc)
G = build_from_json(deduped)
result = god_nodes(G, top_n=5)
# Result: [{'id': 'auth_service_code_b', 'label': 'auth_service', ...}, ...]  — no TypeError
```

**UAT gap status: CLOSED.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed export.py source_file list[str] crash sites (Task 3)**

- **Found during:** Task 3 audit
- **Issue:** `export.py` line ~372 passed raw `source_file` to `sanitize_label()` which calls `_CONTROL_CHAR_RE.sub()` — crashes with `TypeError` when `source_file` is a list. Line ~708 used raw `source_file` as sort key tuple element — crashes with `TypeError` comparing `list < str` in Python 3.
- **Fix:** Import `_fmt_source_file` from `graphify.analyze` and wrap both call sites.
- **Files modified:** `graphify/export.py`
- **Commit:** a1b7582

## Known Stubs

None — all data flows through real helpers with no placeholder values.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The `_iter_sources` and `_fmt_source_file` helpers are pure internal normalizers. T-10-08-01 (nested list filtering) and T-10-08-02 (display-path information disclosure) are both mitigated as specified in the plan threat model.

## Self-Check: PASSED

- tests/test_dedup_pipeline.py: FOUND
- tests/fixtures/dedup_composed_extraction.json: FOUND
- graphify/analyze.py: FOUND (contains `_iter_sources`, `_fmt_source_file`)
- graphify/report.py: FOUND (contains `_fmt_source`)
- Commits 45ae309, 06a66cf, a1b7582: FOUND in git log
