---
phase: 10-cross-file-semantic-extraction
verified: 2026-04-17T13:15:00Z
status: passed
score: 4/4
overrides_applied: 0
re_verification: true
previous_status: passed
previous_score: 4/4
gaps_closed:
  - "dedup → build → analyze pipeline crashes with TypeError when source_file is list[str] (UAT test 6)"
  - "graphify --dedup on zero-byte --graph file surfaces JSONDecodeError instead of empty report (UAT test 2)"
  - "Missing [dedup] extra and path-escape --out-dir both leak Python tracebacks instead of clean error messages (UAT test 3)"
  - "MCP no_seed_nodes short-circuit path omits resolved_from_alias even when alias was resolved (UAT test 8)"
gaps_remaining: []
regressions: []
---

# Phase 10: Cross-File Semantic Extraction — Re-Verification Report

**Phase Goal:** Deliver production-quality graphs on multi-source corpora via (A) cluster-based batch extraction (one LLM call per import-connected cluster, not per file) AND (B) post-extraction entity deduplication merging fuzzy + embedding-similar nodes into canonical entities with re-routed edges, aggregated weights, and deterministic canonical label selection.

**Verified:** 2026-04-17T13:15:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure plans 10-08 and 10-09

---

## Re-Verification Context

The initial verification (2026-04-17T02:20:00Z) returned `passed` for the 4 ROADMAP success criteria. However, UAT testing subsequently identified 4 gaps in the pipeline's error handling and composed flow behavior. Gap closure plans 10-08 (UAT test 6 — source_file list crash) and 10-09 (UAT tests 2, 3, 8 — CLI UX + MCP alias visibility) were executed and this re-verification confirms all 4 gaps are now closed.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Extractor processes import-connected file clusters as one LLM call per cluster | VERIFIED | Unchanged from initial verification — `batch.py::cluster_files()` confirmed substantive (213 lines); all 9 skill variants retain cluster_files dispatch. |
| 2 | `graphify/dedup.py` produces a structured `dedup_report` listing merged pairs with canonical labels | VERIFIED | Unchanged from initial verification — `dedup.py` (590 lines), all 22 dedup tests pass, `write_dedup_reports()` confirmed. |
| 3 | After dedup, edges are re-routed to canonical nodes with no dangling edges; composed pipeline dedup → build → analyze runs without crash | VERIFIED | **Newly verified:** `_iter_sources` helper added to `analyze.py` (line 11). All 7 call sites in `analyze.py` that read `source_file` now tolerate `str | list[str] | None`. `_fmt_source_file` normalizes list values to comma-joined strings at emit sites. `export.py` line 372 and 708 also fixed. Integration tests `test_dedup_pipeline.py` (3 tests) pass. |
| 4 | (Stretch GRAPH-04) Cross-source mixed corpus collapses to one canonical node via `--dedup-cross-type` | VERIFIED | Unchanged from initial verification — `test_cross_source_graph04_acceptance` passes. |

**Score:** 4/4 truths verified

---

## UAT Gap Closure Verification

### Gap 1 — UAT Test 6: dedup → build → analyze TypeError (CLOSED)

**Root cause:** `_is_file_node` in `analyze.py` called `Path(source_file).name` where `source_file` was `list[str]` after Phase 10 D-12 schema extension.

**Fix verified:**
- `_iter_sources(source_file)` helper at `graphify/analyze.py:11` — normalizes `str | list[str] | None` → `list[str]`
- `_fmt_source_file(source_file)` helper at `graphify/analyze.py:32` — flattens to comma-joined string for emit/sort
- `_fmt_source(value)` helper at `graphify/report.py:10` — defense-in-depth for report renderer
- 7 call sites in `analyze.py` audited and updated (confirmed via grep)
- 2 call sites in `export.py` fixed: `sanitize_label(_fmt_source_file(...))` at line 372; sort key at line 708
- `report.py` surprising-connections renderer updated at line 149
- **Tests:** 7 new unit tests in `test_analyze.py::test_*list_source*` (all pass), 3 integration tests in `test_dedup_pipeline.py` (all pass)
- Commits: 45ae309 (RED), 06a66cf (GREEN), a1b7582 (REFACTOR)

### Gap 2 — UAT Test 2: Zero-byte graph file surfaces JSONDecodeError (CLOSED)

**Root cause:** `--dedup` handler passed zero-byte file directly to `json.loads()`, producing confusing error instead of empty-extraction no-op.

**Fix verified:**
- `graphify/__main__.py` line 1196: `if source_path.exists() and source_path.stat().st_size == 0: extraction = {"nodes": [], "edges": []}` before `json.loads()` call
- **Test:** `test_dedup_zero_byte_graph_exits_clean` in `test_main_cli.py:326` — PASSES

### Gap 3 — UAT Test 3: Missing extra and path-escape leak Python tracebacks (CLOSED)

**Root cause:** `_dedup()` and `write_dedup_reports()` calls in `--dedup` handler were unguarded — cleanly-worded `RuntimeError` and `ValueError` propagated to `sys.excepthook` instead of being caught and formatted.

**Fix verified:**
- `graphify/__main__.py` line 1231: `except (RuntimeError, ValueError) as e: print(f"error: {e}", file=sys.stderr); sys.exit(1)` wraps both `_dedup()` and `write_dedup_reports()` calls
- **Tests:** `test_dedup_missing_extra_clean_error` at line 369 and `test_dedup_path_escape_clean_error` at line 349 — both PASS

### Gap 4 — UAT Test 8: resolved_from_alias missing on no_seed_nodes path (CLOSED)

**Root cause:** `_run_query_graph` no_seed_nodes early-return (serve.py ~line 847) did not include the `if _resolved_aliases: meta["resolved_from_alias"] = _resolved_aliases` guard that the happy-path branch had.

**Fix verified:**
- `graphify/serve.py` lines 858-859: `if _resolved_aliases: meta["resolved_from_alias"] = _resolved_aliases` added inside the `if not start_nodes:` block
- Confirmed via grep: `resolved_from_alias` appears at both line 859 (no_seed_nodes) and line 934 (happy-path)
- **Test:** `test_no_seed_nodes_surfaces_resolved_from_alias` in `test_serve.py:1514` — PASSES

---

### Required Artifacts (regression check)

| Artifact | Status | Regression check |
|----------|--------|-----------------|
| `graphify/batch.py` | VERIFIED | Unchanged; 9 batch tests still pass |
| `graphify/dedup.py` | VERIFIED | Unchanged core logic; docstring added at write site (a1b7582) |
| `graphify/analyze.py` | VERIFIED | `_iter_sources` + `_fmt_source_file` helpers added; all 35 analyze tests pass |
| `graphify/report.py` | VERIFIED | `_fmt_source` helper added; renderer updated; report tests pass |
| `graphify/export.py` | VERIFIED | 2 source_file call sites fixed (a1b7582); export tests pass |
| `graphify/__main__.py` | VERIFIED | Zero-byte guard + clean error wrapping added; CLI tests pass |
| `graphify/serve.py` | VERIFIED | resolved_from_alias guard added to no_seed_nodes branch; serve tests pass |
| `graphify/validate.py` | VERIFIED | Unchanged |
| All 9 skill file variants | VERIFIED | Unchanged |
| `tests/test_batch.py` | VERIFIED | 9 tests pass (unchanged) |
| `tests/test_dedup.py` | VERIFIED | 22 tests pass (unchanged) |
| `tests/test_dedup_pipeline.py` | VERIFIED | New — 3 integration tests pass |
| `tests/fixtures/dedup_composed_extraction.json` | VERIFIED | New — multi-source fixture with near-dup pair |

---

### Key Link Verification (regression check)

| From | To | Via | Status |
|------|----|-----|--------|
| `graphify/analyze.py` source_file call sites | `_iter_sources()` / `_fmt_source_file()` | Direct call at all 7 sites | WIRED |
| `graphify/export.py` source_file call sites | `_fmt_source_file` via import from analyze | `from graphify.analyze import _node_community_map, _fmt_source_file` | WIRED |
| `graphify/__main__.py --dedup` handler | zero-byte short-circuit | `stat().st_size == 0` check before `json.loads()` | WIRED |
| `graphify/__main__.py --dedup` handler | clean error boundary | `except (RuntimeError, ValueError)` wraps `_dedup()` + `write_dedup_reports()` | WIRED |
| `graphify/serve.py _run_query_graph` no_seed_nodes | `resolved_from_alias` metadata | `if _resolved_aliases:` guard inside `if not start_nodes:` block | WIRED |

All other key links from initial verification unchanged and passing.

---

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| Full test suite | 1178 passed, 0 failed, 2 warnings (deprecations in graspologic/numba) | PASS |
| 7 new analyze list-source tests | All pass in isolation (`-k "list_source"`) | PASS |
| 3 new dedup_pipeline integration tests | All pass in isolation | PASS |
| 4 new CLI + serve tests (UAT gaps 2, 3, 8) | All pass in isolation | PASS |
| Commit SHAs from summaries (45ae309, 06a66cf, a1b7582, 57b5468, be7a391) | All 5 found in git log | PASS |

---

### Anti-Patterns Found

No blockers found. The only "placeholder" match in grep is an HTML `<input placeholder="Search nodes...">` attribute in `export.py`'s vis.js template — this is a UI label, not a code stub.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None in modified gap-closure files | — | — | — | — |

---

### Test Count Delta

| Plan | Before | After | Delta |
|------|--------|-------|-------|
| After 10-08 | 1161 | 1174 | +13 (7 test_analyze + 3 test_dedup_pipeline + 3 fixture-driven) |
| After 10-09 | 1174 | 1178 | +4 (3 test_main_cli + 1 test_serve) |
| **Total** | **1161** | **1178** | **+17** |

---

### Human Verification Required

None. All 4 UAT gaps are verifiable programmatically and all new tests pass.

---

### Gaps Summary

No gaps remaining. All 4 UAT-identified gaps from the initial test run are closed:

1. **UAT Test 6 (major):** `dedup → analyze` TypeError on `source_file: list[str]` — fixed via `_iter_sources` helper across all 7 call sites in `analyze.py`, 2 sites in `export.py`, and `_fmt_source` in `report.py`. Integration test proves composed pipeline runs end-to-end.

2. **UAT Test 2 (minor):** Zero-byte `--graph` file now treated as empty extraction (exit 0, empty dedup_report) rather than surfacing `JSONDecodeError`.

3. **UAT Test 3 (minor):** Missing `[dedup]` extra and path-escape `--out-dir` now produce single-line `error: <message>` with exit 1, no Python traceback.

4. **UAT Test 8 (minor):** MCP `no_seed_nodes` short-circuit now includes `resolved_from_alias` metadata when alias resolution occurred, consistent with the happy-path behavior.

All 4 ROADMAP success criteria (GRAPH-01 through GRAPH-04 stretch) remain satisfied. No regressions introduced.

---

_Verified: 2026-04-17T13:15:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after gap closure plans 10-08 and 10-09_
