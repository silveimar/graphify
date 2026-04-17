---
phase: 10-cross-file-semantic-extraction
plan: "06"
subsystem: serve
tags: [mcp, alias-resolution, dedup, query-graph, d-16]
dependency_graph:
  requires: [10-03]
  provides: [D-16-alias-redirect]
  affects: [graphify/serve.py, tests/test_serve.py]
tech_stack:
  added: []
  patterns: [sidecar-state-load, alias-redirect-layer, tdd-red-green]
key_files:
  created: []
  modified:
    - graphify/serve.py
    - tests/test_serve.py
decisions:
  - "_resolved_aliases dict (canonical->original) scoped inside _run_query_graph, not module-level, for thread-safety"
  - "alias resolution applied only to explicit seed-node fields (node_id, source, target, seed, start, seed_nodes) not free-text question"
  - "resolved_from_alias omitted from meta entirely when no redirect occurred (strict backward compat)"
metrics:
  duration: "18 minutes"
  completed: "2026-04-16"
  tasks_completed: 1
  files_modified: 2
---

# Phase 10 Plan 06: MCP serve.py Alias Resolution (D-16) Summary

D-16 alias redirect layer added to `graphify/serve.py`. Agents querying merged-away node IDs (e.g. `auth`) automatically receive the canonical node (`authentication_service`) annotated with `resolved_from_alias` provenance, preventing MCP callsite breakage after dedup runs.

## What Was Built

### `_load_dedup_report` helper (graphify/serve.py line 91)

Added immediately after `_load_telemetry` (line 81), mirroring the same "returns default on missing or corrupt" pattern:

```python
def _load_dedup_report(out_dir: Path) -> dict[str, str]:
    """D-16: load {eliminated_id: canonical_id} alias map from dedup_report.json.
    Returns {} if the report is missing, unreadable, malformed, or has no alias_map key.
    Never raises — broken dedup report must not crash MCP serve.
    """
    path = out_dir / "dedup_report.json"
    if not path.exists():
        return {}
    ...
    return {str(k): str(v) for k, v in alias_map.items() if isinstance(k, str) and isinstance(v, str)}
```

Defensive behavior: returns `{}` on missing file, OSError, JSONDecodeError, missing `alias_map` key, non-dict `alias_map`, or non-string values. Logs a warning to stderr only on parse error.

### serve() startup (graphify/serve.py line 1027)

Sidecar state initialized after `_telemetry`:

```python
_alias_map: dict[str, str] = _load_dedup_report(_out_dir)  # Phase 10 D-16
```

### `_run_query_graph` signature change (line 743)

Added `alias_map: dict[str, str] | None = None` as the last keyword argument. Default is `None` (backward compatible — callers without the kwarg produce byte-identical responses).

Alias resolution block inserted at line ~782, **before** scoring/traversal, **after** argument parsing:

```python
_resolved_aliases: dict[str, str] = {}  # {canonical_id: original_alias}
_effective_alias_map: dict[str, str] = alias_map or {}

def _resolve_alias(node_id: str) -> str:
    canonical = _effective_alias_map.get(node_id)
    if canonical and canonical != node_id:
        _resolved_aliases[canonical] = node_id
        return canonical
    return node_id
```

**Eligible fields for alias resolution** (explicit seed-node identifiers only, not free-text):
- `node_id`, `source`, `target`, `seed`, `start` (string fields)
- `seed_nodes` (list of strings)

Free-text `question` is NOT resolved (question text goes through `_score_nodes` label matching, not node ID lookup).

### `resolved_from_alias` meta-JSON field

Injected at line 915, immediately before the final `json.dumps(meta)`:

```python
if _resolved_aliases:
    meta["resolved_from_alias"] = _resolved_aliases
```

**Shape:** `{ canonical_id: original_alias }` — e.g. `{"authentication_service": "auth"}`

Field is **omitted entirely** when no redirect occurred (no `null` or empty dict pollution in the meta).

### `_tool_query_graph` closure (line 1209)

Forwards `_alias_map` from the `serve()` closure into `_run_query_graph`:

```python
response = _run_query_graph(
    ...,
    alias_map=_alias_map,  # Phase 10 D-16
)
```

## Tests Added (tests/test_serve.py)

7 new tests appended:

| Test | Coverage |
|------|---------|
| `test_load_dedup_report_missing_returns_empty` | Missing file → `{}` |
| `test_load_dedup_report_reads_alias_map` | Valid file → alias_map dict |
| `test_load_dedup_report_corrupt_returns_empty` | Invalid JSON → `{}` |
| `test_load_dedup_report_missing_alias_map_key` | No `alias_map` key → `{}` |
| `test_load_dedup_report_rejects_non_string_values` | Non-string values filtered out |
| `test_run_query_graph_resolves_alias` | End-to-end: query with alias_map, well-formed meta |
| `test_run_query_graph_no_alias_map_backward_compat` | No alias_map → identical meta structure, no `resolved_from_alias` field |

## Backward Compatibility Confirmation

When `dedup_report.json` is absent (no dedup run):
- `_load_dedup_report` returns `{}`
- `_alias_map` is `{}`
- `_effective_alias_map` in `_run_query_graph` is `{}`
- `_resolved_aliases` remains `{}`
- `resolved_from_alias` is NOT added to meta
- Response is **byte-identical** to pre-Phase-10 behavior

## TDD Gate Compliance

- RED commit: `e9bf217` — `test(10-06): add failing tests for D-16 alias redirect in MCP serve`
- GREEN commit: `f3096d9` — `feat(10-06): add D-16 alias redirect layer in MCP serve.py`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. The `resolved_from_alias` disclosure is intentional per T-10-06 (STRIDE register in the plan) — node IDs are slugified code entity names, not user data.

## Self-Check: PASSED

- `graphify/serve.py` modified: confirmed (grep returns 1 match for `def _load_dedup_report`)
- `tests/test_serve.py` modified: confirmed (112 lines added)
- RED commit `e9bf217`: confirmed in git log
- GREEN commit `f3096d9`: confirmed in git log
- `pytest tests/test_serve.py -q`: 121 passed
- `pytest tests/ -q`: 1152 passed, 3 pre-existing failures in test_delta.py (unrelated to this plan)
