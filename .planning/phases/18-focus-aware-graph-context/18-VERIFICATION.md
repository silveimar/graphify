---
phase: 18-focus-aware-graph-context
verified: 2026-04-20
status: gaps_found
score: 4/5 roadmap success criteria, 9/9 REQ-IDs (SC4 PARTIAL — sentinel not wired to production callers)
overrides_applied: 0
re_verification: null
gaps:
  - truth: "SC4: The ProjectRoot sentinel prevents Phase 12/15/17 from reintroducing CR-01"
    status: partial
    reason: "Sentinel raises correctly in the test (test_project_root_sentinel_rejects_graphify_out passes), but none of the snapshot helpers (snapshots_dir, list_snapshots, save_snapshot, auto_snapshot_and_delta) actually accept or construct ProjectRoot — they take `project_root: Path`. No production caller in graphify/serve.py (lines 1072, 1359, 1514, 1611), graphify/__main__.py (line 1459), or graphify/skill.md (lines 504, 1062) invokes ProjectRoot(...). A future phase passing Path('graphify-out') directly to save_snapshot would still silently double-nest without tripping the sentinel. This matches 18-REVIEW.md WR-01 exactly."
    artifacts:
      - path: "graphify/snapshot.py"
        issue: "ProjectRoot defined (lines 15-31) but never referenced by snapshots_dir/list_snapshots/save_snapshot/auto_snapshot_and_delta; only the class definition + two test imports reference it."
      - path: "graphify/serve.py"
        issue: "Production callers pass raw `_out_dir.parent` (lines 1072, 2214, 2244, 2286, 2303, 2318) directly, bypassing the sentinel."
    missing:
      - "Runtime guard inside snapshots_dir / save_snapshot / list_snapshots / auto_snapshot_and_delta that rejects `path.name == 'graphify-out'` (matches 18-REVIEW.md WR-01 fix option (a))."
      - "OR: change parameter type to accept `Path | ProjectRoot` and unwrap internally (18-REVIEW.md WR-01 fix option (b))."
deferred: []
human_verification: []
---

# Phase 18: Focus-Aware Graph Context Verification Report

**Phase Goal (ROADMAP.md:229):** An agent reports what the user is currently focused on (a file path, optionally a function or line) and graphify returns a scoped subgraph — neighbors, community, and citations — so downstream tools can reason about the local neighborhood without loading the full graph.

**Verified:** 2026-04-20
**Status:** gaps_found (SC4 PARTIAL — sentinel not wired)
**Re-verification:** No — initial verification

## Goal Achievement

### ROADMAP Success Criteria

| # | Criterion | Method | Evidence | Verdict |
|---|-----------|--------|----------|---------|
| 1 | `get_focus_context({"file_path":"...", "neighborhood_depth":2, "include_community":true})` returns BFS ego-graph + community summary in D-02 envelope with full citations | pytest + grep + runtime call | `tests/test_serve.py::test_get_focus_context_envelope_ok` PASSES; `tests/test_serve.py::test_get_focus_context_community_summary` PASSES; envelope emitted by `_run_get_focus_context_core` at serve.py:1840 uses `text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta)` with `meta.status == "ok"`, `node_count >= 1`, `edge_count >= 0`; `_render_focus_community_summary` at serve.py:1688 renders per-community top-3-by-degree members | PASS |
| 2 | Spoofed `focus_hint.file_path = "/etc/passwd"` returns silent no_context (no leak, no echo) via `validate_graph_path(path, base=project_root)` | pytest + grep | `tests/test_serve.py::test_get_focus_context_spoofed_path_silent` PASSES; serve.py:1785 `validate_graph_path(candidate, base=project_root)`; serve.py:1786 `except (ValueError, FileNotFoundError): return _no_context()`; `tests/test_serve.py::test_no_context_does_not_echo_focus_hint` PASSES (asserts `/etc/passwd`, `SECRET_FN`, `424242` absent from envelope); `tests/test_serve.py::test_binary_status_invariant` PASSES (spoof/unindexed/missing all yield byte-identical `{status, node_count, edge_count, budget_used}` meta) | PASS |
| 3 | `source_file` as `str \| list[str]` resolves correctly — multi-source node returns matching node_ids without crashing | pytest | `tests/test_serve.py::test_focus_resolver_str_source_file` PASSES; `tests/test_serve.py::test_focus_resolver_list_source_file_multi_seed` PASSES; `_resolve_focus_seeds` at serve.py:773 delegates to `analyze._iter_sources` (imported at serve.py:17); handles both schemas via iteration at serve.py:797 `for s in _iter_sources(data.get("source_file"))` | PASS |
| 4 | Regression test constructs `Snapshot(project_root=Path("graphify-out"))` and sentinel raises before any path operation — renamed field + assertion prevents Phase 12/15/17 from reintroducing CR-01 | pytest + grep | `tests/test_snapshot.py::test_project_root_sentinel_rejects_graphify_out` PASSES (line 290-296 of test_snapshot.py); `snapshot.py::ProjectRoot.__post_init__` at line 25-31 raises `ValueError` on `path.name == "graphify-out"`. **PARTIAL because:** `ProjectRoot` is defined but NEVER USED by `snapshots_dir` / `list_snapshots` / `save_snapshot` / `auto_snapshot_and_delta` — all four accept `project_root: Path`, not `ProjectRoot`. Production callers in serve.py (lines 1072, 2214, 2244, 2286, 2303, 2318) and __main__.py (line 1459) pass raw `Path` objects directly. A Phase 12/15/17 author passing `Path("graphify-out")` to `save_snapshot(...)` would still silently double-nest — the sentinel only fires when a caller explicitly wraps in `ProjectRoot(...)`, which happens only in the two unit tests. See 18-REVIEW.md WR-01. | PARTIAL |
| 5 | Focus is pull-model via MCP arg — no filesystem watcher thread exists; `nx.ego_graph` is reused (no new traversal algorithms) | pytest + grep | `tests/test_serve.py::test_no_watchdog_import_in_focus_path` PASSES; `grep "import watchdog\|from watchdog" graphify/serve.py` returns 0 lines; `grep "nx.ego_graph(G, *\[" graphify/serve.py` returns 0 lines (correct multi-seed form via `nx.compose_all` at serve.py:770); `_multi_seed_ego` at serve.py:756 composes per-seed `nx.ego_graph` calls via `nx.compose_all` | PASS |

**Score:** 4/5 criteria fully VERIFIED · 1/5 PARTIAL (SC4)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/serve.py::_resolve_focus_seeds` | Path→node_id resolver handling str \| list[str] | VERIFIED | line 773 |
| `graphify/serve.py::_multi_seed_ego` | Multi-seed ego-graph via nx.compose_all | VERIFIED | line 756; uses `nx.compose_all(subgraphs)` at line 770 |
| `graphify/serve.py::_run_get_focus_context_core` | Pure dispatch core returning D-02 envelope | VERIFIED | line 1731 |
| `graphify/serve.py::_render_focus_community_summary` | Community summary renderer | VERIFIED | line 1688 |
| `graphify/serve.py::_tool_get_focus_context` | MCP handler closure with freshness+debounce gates | VERIFIED | line 2246 |
| `graphify/serve.py::_FOCUS_DEBOUNCE_CACHE` | Module-level debounce dict | VERIFIED | line 1850 |
| `graphify/serve.py::_FOCUS_DEBOUNCE_WINDOW` | 0.5-second constant | VERIFIED | line 1851 (`= 0.5`) |
| `graphify/serve.py::_focus_debounce_key` / `_get` / `_put` | Debounce helpers | VERIFIED | lines 1854, 1865, 1876 |
| `graphify/serve.py::_check_focus_freshness` | Freshness helper with Py 3.10 Z-shim | VERIFIED | line 1886; `.replace("Z", "+00:00")` at line 1901 |
| `graphify/snapshot.py::ProjectRoot` | Frozen-dataclass sentinel | EXISTS but ORPHANED | line 16; raises on `path.name == "graphify-out"` at line 26; **not imported by any production caller — only by two tests. Fails Level-3 wiring check for its intended purpose (SC4).** |
| `graphify/mcp_tool_registry.py::get_focus_context Tool` | MCP schema entry | VERIFIED | line 231 with full inputSchema |
| `tests/conftest.py::nested_project_root` | Shared fixture | VERIFIED | line 144 |
| `tests/test_snapshot.py` | 3 sentinel + nested-dir tests | VERIFIED | lines 290-312 |
| `tests/test_serve.py` | 18 new phase-18 tests | VERIFIED | all names in 18-VALIDATION.md present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `serve.py::_resolve_focus_seeds` | `analyze.py::_iter_sources` | `from graphify.analyze import _iter_sources` | WIRED | serve.py:17 import confirmed; used at serve.py:797 |
| `serve.py::_multi_seed_ego` | `networkx` | `nx.compose_all([nx.ego_graph(G, s, radius=r) for s in seeds])` | WIRED | serve.py:770 |
| `serve.py::_run_get_focus_context_core` | `security.py::validate_graph_path` | `validate_graph_path(candidate, base=project_root)` | WIRED | serve.py:1785 with explicit `base=project_root` per Pitfall 3 |
| `serve.py::_run_get_focus_context_core` | `serve.py::_resolve_focus_seeds` | direct call | WIRED | serve.py:1798 |
| `serve.py::_run_get_focus_context_core` | `serve.py::_multi_seed_ego` | direct call | WIRED | serve.py:1806, 1819 |
| `serve.py::_tool_get_focus_context` | `_out_dir.parent` | positional arg (CR-01 mitigation) | WIRED | serve.py:2286 `_run_get_focus_context_core(G, communities, _alias_map, _out_dir.parent, arguments)` |
| `serve.py::_tool_get_focus_context` | `_check_focus_freshness` | `if not _check_focus_freshness(focus_hint.get("reported_at"))` | WIRED | serve.py:2271 |
| `serve.py::_tool_get_focus_context` | `_focus_debounce_get`/`_put` | closure calls | WIRED | serve.py:2279 (get) and 2287 (put) |
| `snapshot.py::ProjectRoot.__post_init__` | `raise ValueError` | `path.name == "graphify-out"` | WIRED (class-internal) | snapshot.py:26-31 |
| `snapshot.py::ProjectRoot` | `snapshot.py::snapshots_dir` + `list_snapshots` + `save_snapshot` + `auto_snapshot_and_delta` | **(no link)** | **ORPHANED** | `grep -rn "ProjectRoot" graphify/` returns 0 usages outside the class definition itself (serve.py only has it in comments/docstrings). Helpers accept `project_root: Path`, never `ProjectRoot`. **This is the WR-01/SC4 gap.** |
| `serve.py::_handlers` dict | `get_focus_context` handler | `"get_focus_context": _tool_get_focus_context` | WIRED | serve.py:2405 (MANIFEST-05 invariant holds — registry + handlers keyset match) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|---------| 
| `_run_get_focus_context_core` | `focused` (nx.Graph) | `_multi_seed_ego(G, seeds, radius=depth)` — real graph composition from live `G.nodes`/`G.edges` | Yes (real nx subgraph) | FLOWING |
| `_run_get_focus_context_core` | `text_body` | `_subgraph_to_text(fg, set(fg.nodes), list(fg.edges), token_budget=budget, layer=2)` | Yes (reused Phase 9.2 renderer) | FLOWING |
| `_render_focus_community_summary` | `touched` (set of community IDs) | iterates `focused.nodes` and reads `G.nodes[nid].get("community")` | Yes (real attrs) | FLOWING |
| `_tool_get_focus_context` | `envelope` | `_run_get_focus_context_core(G, communities, _alias_map, _out_dir.parent, arguments)` | Yes (wired to full pipeline) | FLOWING |
| `_focus_debounce_get`/`_put` | `_FOCUS_DEBOUNCE_CACHE` | module-level dict populated on every successful core call | Yes | FLOWING |
| `_check_focus_freshness` | parsed `datetime` | `datetime.fromisoformat(reported_at.replace("Z", "+00:00"))` | Yes (live parse) | FLOWING |
| `snapshot.py::ProjectRoot.path` | — | frozen-dataclass field | N/A (class sentinel only) | **DISCONNECTED** — no production caller instantiates `ProjectRoot`; the `.path` field is never consumed downstream. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full phase-18 test set (21 locked tests) passes | `pytest tests/test_serve.py::{18 tests} tests/test_snapshot.py::{3 tests}` | `21 passed in 0.54s` | PASS |
| Full suite regression | `pytest tests/ -q` | `1325 passed, 2 warnings in 39.04s` | PASS |
| `get_focus_context` in MCP tool names | `python -c "from graphify.mcp_tool_registry import build_mcp_tools; print('get_focus_context' in {t.name for t in build_mcp_tools()})"` | `True` (20 tools total; `get_focus_context` present) | PASS |
| `ProjectRoot` sentinel actually raises at construction | `python -c "from graphify.snapshot import ProjectRoot; from pathlib import Path; ProjectRoot(path=Path('graphify-out'))"` | Raises `ValueError: ProjectRoot received PosixPath('graphify-out')...` | PASS |
| `_check_focus_freshness` behavior | `python -c` with fresh/stale/malformed/absent inputs | `fresh=True`, `stale=False`, `malformed=False`, `absent=True` | PASS |
| `_FOCUS_DEBOUNCE_WINDOW == 0.5`, key derivation | `python -c "from graphify.serve import _focus_debounce_key, _FOCUS_DEBOUNCE_WINDOW"` | `window=0.5`, `key=('x.py', '', -1, 2, True)` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FOCUS-01 | 18-02 | New MCP tool `get_focus_context(focus_hint, budget)` | SATISFIED | `graphify/serve.py::_tool_get_focus_context` (line 2246) + `mcp_tool_registry.py` entry (line 231) + `_handlers` dict (line 2405); test `test_get_focus_context_registered` passes |
| FOCUS-02 | 18-01 | Resolves `file_path`→node_ids handling `source_file: str \| list[str]` | SATISFIED | `graphify/serve.py::_resolve_focus_seeds` (line 773) delegates to `analyze._iter_sources`; tests `test_focus_resolver_str_source_file` + `test_focus_resolver_list_source_file_multi_seed` pass |
| FOCUS-03 | 18-02 | Returns BFS subgraph at depth with citations, community summary, D-02 envelope | SATISFIED | `_run_get_focus_context_core` (line 1731) + `_render_focus_community_summary` (line 1688); tests `test_get_focus_context_envelope_ok` + `test_get_focus_context_community_summary` pass |
| FOCUS-04 | 18-02 | `validate_graph_path(path, base=project_root)` confinement; spoofed paths silently ignored | SATISFIED | serve.py:1785 `base=project_root`; serve.py:1786 `except (ValueError, FileNotFoundError)`; tests `test_get_focus_context_spoofed_path_silent`, `test_get_focus_context_missing_file_silent`, `test_binary_status_invariant`, `test_no_context_does_not_echo_focus_hint` all pass |
| FOCUS-05 | 18-02 | Pull-model via MCP arg — no filesystem watcher side-channel | SATISFIED | `test_no_watchdog_import_in_focus_path` passes; `grep "import watchdog\|from watchdog" graphify/serve.py` returns 0 |
| FOCUS-06 | 18-01 | Uses `nx.ego_graph` for bounded-depth neighborhood | SATISFIED | `_multi_seed_ego` at serve.py:756 uses `nx.compose_all([nx.ego_graph(G, s, radius=r) for s in seeds])`; test `test_multi_seed_compose_all_matches_expected` passes; grep confirms no multi-seed `nx.ego_graph(G, [...])` anti-pattern |
| FOCUS-07 | 18-02 | Snapshot-path-double-nesting regression guard — renames `root`→`project_root`; asserts `not path.name == "graphify-out"` at construction | **PARTIAL** | `ProjectRoot` class exists at `snapshot.py:16` and raises at construction; `root`→`project_root` rename completed across 4 signatures (snapshot.py lines 34, 41, 49, 105); 3 sentinel tests pass. **HOWEVER**: the sentinel is not wired into the 4 snapshot helpers — they accept `project_root: Path`, not `ProjectRoot`. Production callers in `serve.py` and `__main__.py` bypass the sentinel. A Phase 12/15/17 author passing `Path("graphify-out")` directly would still silently double-nest. The REQ text ("asserts `not path.name == 'graphify-out'` at construction") is literally satisfied by the class, but the *intent* ("prevents downstream phases from reintroducing CR-01") is not enforced. See 18-REVIEW.md WR-01. |
| FOCUS-08 [P2] | 18-03 | 500ms debounce prevents cache thrash | SATISFIED | `_FOCUS_DEBOUNCE_CACHE` + `_FOCUS_DEBOUNCE_WINDOW = 0.5` at serve.py:1850-1851; `_focus_debounce_key/_get/_put` at lines 1854, 1865, 1876; wired into `_tool_get_focus_context` at lines 2279 (get) and 2287 (put); tests `test_focus_debounce_suppresses_duplicate` + `test_focus_debounce_expires` pass (see 18-REVIEW.md WR-03 note: first test's coverage is narrow — tests the get helper, not the wrapper path — but the wrapper wiring is grep-verifiable) |
| FOCUS-09 [P2] | 18-03 | `focus_hint.reported_at` freshness (≤5 min) rejects stale focus | SATISFIED | `_check_focus_freshness` at serve.py:1886 with Py 3.10 Z-shim at line 1901 (`reported_at.replace("Z", "+00:00")`); wired into `_tool_get_focus_context` at serve.py:2271; tests `test_focus_stale_reported_at_rejected` + `test_focus_reported_at_z_suffix_parses` + `test_focus_malformed_reported_at` all pass |

**Note on PARTIAL:** FOCUS-07 is classified SATISFIED against the literal REQ text (the sentinel *does* assert at construction) but the *ROADMAP SC4 intent* (prevent downstream phases from reintroducing CR-01) is PARTIAL because the sentinel is orphaned from production call sites. The REQUIREMENTS.md row (line 270) marks it complete; the gap is a wiring issue, not a feature-existence issue.

### Anti-Patterns Scanned

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `graphify/serve.py` | — | `nx.ego_graph(G, [` multi-seed anti-pattern | — | 0 matches (ABSENT, correct) |
| `graphify/serve.py` | — | `import watchdog` / `from watchdog` | — | 0 matches (ABSENT, correct per FOCUS-05) |
| `graphify/serve.py` | 1848 | `time.time()` | Info | 1 match — it is inside a *comment* explaining why `time.monotonic()` is used instead. Not an anti-pattern instance. |
| `graphify/` + `tests/` (excluding conftest) | — | legacy `root=` kwarg on snapshot helpers | — | 0 matches (rename complete; conftest has backward-compat alias per plan) |
| `graphify/snapshot.py` | — | `ProjectRoot` consumption in helpers | Warning | 0 matches (the sentinel is never consumed by the helpers it's meant to guard — WR-01 / SC4 PARTIAL root cause) |

### 18-REVIEW.md Findings Summary

The Phase 18 code review (`18-REVIEW.md`, reviewed 2026-04-20T19:58:00Z, status `issues_found`) surfaced **0 Critical, 4 Warning, 5 Info** findings. This verification confirms:

- **WR-01 (ProjectRoot not wired)** — CONFIRMED. Classified as a real gap (SC4 PARTIAL above). The class exists and raises correctly in tests, but no production caller constructs `ProjectRoot(...)` before passing to snapshot helpers. Fix suggested in review: add inline `if project_root.name == "graphify-out": raise ValueError(...)` inside each of the four helpers (or change param type to `Path | ProjectRoot` with unwrap). Non-blocking for the literal REQ text but blocking for the SC4 intent.
- **WR-02 (dead `alias_map` parameter)** — CONFIRMED via grep: `_run_get_focus_context_core` declares `alias_map: dict` at serve.py:1733 but the body never references `alias_map` (0 occurrences inside the function body lines 1731-1841). The caller at serve.py:2286 still passes `_alias_map`. Classified as **dead code / Warning**, not a functional gap. Recommend removing the parameter in a follow-up plan, per 18-REVIEW.md WR-02 fix suggestion.
- **WR-03 (`test_focus_debounce_suppresses_duplicate` shallow coverage)** — CONFIRMED. The test seeds `_FOCUS_DEBOUNCE_CACHE` manually and reads it back; it never calls `_tool_get_focus_context` nor triggers the `monkeypatch.setattr` on the core blow-up. The wrapper's debounce wiring is *grep-verifiable* (serve.py:2279 `_focus_debounce_get(key)`, serve.py:2287 `_focus_debounce_put(key, envelope)`) but is not *integration-tested*. Classified as a **Warning / test-quality gap**, not a functional gap.
- **WR-04 (`test_budget_drop_outer_hop_first` assertions too weak)** — CONFIRMED. Test asserts `len(small_body) <= len(large_body)` and `status ∈ {"ok","no_context"}` (tautological); does not assert `depth_used` reduction. Would pass even if D-08 outer-hop-first logic were replaced by naive char-clipping. The D-08 loop *does* exist at serve.py:1820-1823 (grep confirms) but is only weakly tested. Classified as a **Warning / test-quality gap**, not a functional gap.
- **IN-01..IN-05** — all stylistic / Info-level observations; do not affect goal achievement.

### Deviations from Plan (from SUMMARY.md sections)

Extracted from the three SUMMARY.md `Deviations` sections:

| # | Deviation | Classification | Plan | Notes |
|---|-----------|----------------|------|-------|
| 1 | `_run_focus_core` (RESEARCH.md) renamed to `_run_get_focus_context_core` (PATTERNS.md convention) | intentional | 18-02 | Matches VALIDATION.md test naming (`test_get_focus_context_*`) and MCP tool name |
| 2 | `validate_graph_path` with relative `file_path` false-escaped tmp_path — fixed by prepending `project_root` to relative paths before calling `validate_graph_path` | bug fix (intentional) | 18-02 | Documented as Pitfall-3 extension; serve.py:1782-1784 |
| 3 | `_resolve_focus_seeds` needs project-root-relative target (not absolute) — fixed by computing `Path(validated).relative_to(project_root.resolve())` | bug fix (intentional) | 18-02 | serve.py:1796-1799; stored `source_file` values are relative |
| 4 | `test_no_watchdog_import_in_focus_path` scan range narrowed to `[_run_get_focus_context_core, next top-level def]` | intentional | 18-02 | Original broad scan false-tripped on unrelated `_filter_blank_stdin` stdio helper |
| 5 | `_tool_get_focus_context` missing-graph path collapses to `no_context` (not `no_graph`) to preserve binary invariant | intentional | 18-02 | T-18-A/B/C tested by `test_binary_status_invariant` |
| 6 | `make_snapshot_chain` fixture accepts both `project_root=` (new) and `root=` (legacy) as backwards-compat shim | intentional | 18-02 | Documented; cleanup deferred to follow-up per 18-REVIEW.md IN-05 |
| 7 | `skill.md` runtime callsites updated from `root=` to `project_root=` (lines 504, 1062) | intentional | 18-02 | Required by rename; would have crashed skill runtime otherwise |
| 8 | Plan 18-03: zero deviations | — | 18-03 | Plan executed verbatim |

No regressions detected. All deviations either fix discovered plan defects, adopt clearer naming, or preserve invariants.

### Human Verification Required

None. All phase behaviors have automated coverage per 18-VALIDATION.md.

### Gaps Summary

One real gap: **SC4 is PARTIAL because the `ProjectRoot` sentinel is defined but not wired to production callers.** The class raises correctly in tests (so the literal REQ-07 "asserts at construction" text is satisfied) but the SC4 intent ("prevents Phase 12/15/17 from reintroducing CR-01") is not structurally enforced — future authors passing `Path("graphify-out")` directly to `snapshots_dir` / `list_snapshots` / `save_snapshot` / `auto_snapshot_and_delta` will still silently double-nest. This is exactly the class of bug the phase was meant to permanently prevent.

**Recommended follow-up fix** (matches 18-REVIEW.md WR-01 option (a) — minimal surface area):

Add a runtime guard at the top of each of the four snapshot helpers:

```python
def snapshots_dir(project_root: Path = Path(".")) -> Path:
    p = Path(project_root)
    if p.name == "graphify-out":
        raise ValueError(
            f"snapshots_dir received {p!r}; pass the directory CONTAINING "
            f"graphify-out/, not graphify-out/ itself. Try: {p.parent!r}"
        )
    d = p / "graphify-out" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

…and similar one-liners at the top of `list_snapshots`, `save_snapshot`, `auto_snapshot_and_delta`. Scope: ~30 LOC + 4 targeted tests (one per helper, same pattern as the existing `ProjectRoot` sentinel tests). Low-risk; makes SC4 fully structural rather than relying on caller discipline.

The other three Warning-level findings (WR-02 dead parameter, WR-03 shallow debounce test, WR-04 weak budget-drop assertion) are **non-blocking code-quality improvements** that do not affect goal achievement and are not gating the phase — they should be tracked as follow-up tasks, not re-opening Phase 18.

All 9 REQ-IDs have traceability entries in REQUIREMENTS.md pointing to shipped code (lines 264-272). All 21 locked tests pass. Full test suite green (1325 passed). No regressions.

---

_Verified: 2026-04-20_
_Verifier: Claude (gsd-verifier)_
