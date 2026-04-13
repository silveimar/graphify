---
phase: 06-graph-delta-analysis-staleness
verified: 2026-04-12T23:45:00Z
status: passed
score: 5/5
overrides_applied: 0
---

# Phase 6: Graph Delta Analysis & Staleness Verification Report

**Phase Goal:** Users can see how their knowledge graph changed between runs and know how fresh each node is
**Verified:** 2026-04-12T23:45:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After two pipeline runs, user can open GRAPH_DELTA.md and see exactly which nodes were added, removed, or changed communities since the previous run | VERIFIED | `render_delta_md` produces Summary + Archive sections with Added Nodes, Removed Nodes, Community Migrations tables. `auto_snapshot_and_delta` chains save + delta in one call. CLI `--from`/`--to` also produces GRAPH_DELTA.md. Tests `test_render_delta_md_with_changes`, `test_auto_snapshot_and_delta_second_run`, `test_cli_snapshot_from_to` all pass. |
| 2 | User can read a concise delta summary (agent-context-sized) and separately reference a full machine-readable archive without the summary being bloated | VERIFIED | `render_delta_md` renders `## Summary` (counts + narrative of top 5 changes, ~20-40 lines) and `## Archive` (full markdown tables for Added Nodes, Removed Nodes, Community Migrations, Connectivity Changes, Stale Nodes). Empty deltas produce "No changes detected". |
| 3 | Every graph node carries extracted_at, source_hash, and a staleness state (FRESH / STALE / GHOST) so user or agent can judge data freshness without re-running extraction | VERIFIED | `_extract_generic` in extract.py injects `extracted_at` (ISO UTC), `source_hash` (SHA256 via `file_hash`), `source_mtime` on every node (lines 678-698). `classify_staleness` in delta.py returns FRESH/STALE/GHOST with mtime fast-gate + SHA256 authoritative check. Tests `test_extract_python_provenance_fields`, `test_provenance_source_hash_matches_file_hash`, `test_classify_staleness_fresh/stale/ghost` all pass. |
| 4 | Running graphify snapshot saves a named snapshot without requiring a full pipeline re-run, and graphify-out/snapshots/ never exceeds the configured retention limit | VERIFIED | `graphify snapshot` CLI command loads existing graph.json (no pipeline re-run), saves via `save_snapshot`. `--name` flag adds sanitized label to filename. `--cap N` enforces FIFO pruning. Tests `test_cli_snapshot_saves_file`, `test_cli_snapshot_with_name`, `test_fifo_prune_removes_oldest` all pass. CLI help output confirms snapshot command with all flags. |
| 5 | Per-node connectivity delta (degree change, new/lost edge counts) is visible in the delta output, not just node-level presence/absence | VERIFIED | `compute_delta` computes `connectivity_changes` dict with `degree_delta`, `added_edges`, `removed_edges` per node. `render_delta_md` renders `### Connectivity Changes` table with degree delta and specific edge lists. Tests `test_connectivity_change`, `test_render_delta_md_connectivity` pass. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/snapshot.py` | save_snapshot, load_snapshot, snapshots_dir, list_snapshots, auto_snapshot_and_delta | VERIFIED | 149 lines, all 5 functions present, atomic write via os.replace, FIFO prune, name sanitization |
| `graphify/delta.py` | compute_delta, classify_staleness, render_delta_md | VERIFIED | 261 lines, all 3 public functions plus _escape_pipe helper, mtime fast-gate, Summary+Archive pattern |
| `tests/test_snapshot.py` | Unit tests for snapshot + provenance | VERIFIED | 286 lines, 19 test functions (snapshot save/load/prune/list + provenance + auto_snapshot_and_delta) |
| `tests/test_delta.py` | Unit tests for delta + CLI | VERIFIED | 304 lines, 21 test functions (compute_delta + classify_staleness + render_delta_md + CLI integration) |
| `graphify/__init__.py` | Lazy-load entries for all new functions | VERIFIED | Contains entries for save_snapshot, load_snapshot, list_snapshots, snapshots_dir, auto_snapshot_and_delta, compute_delta, classify_staleness, render_delta_md |
| `graphify/__main__.py` | snapshot CLI subcommand | VERIFIED | `if cmd == "snapshot":` at line 907, full --name/--cap/--graph/--from/--to/--delta parsing, help text at lines 752-758 |
| `graphify/extract.py` | Provenance injection in _extract_generic | VERIFIED | extracted_at, source_hash, source_mtime injected at lines 696-698, file_hash imported from .cache at line 12 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| graphify/snapshot.py | networkx.readwrite.json_graph | node_link_data/node_link_graph | WIRED | Lines 11, 53-55, 141-143 |
| graphify/extract.py | graphify/cache.py | file_hash() for source_hash | WIRED | Import at line 12: `from .cache import load_cached, save_cached, file_hash`; used at line 681 |
| graphify/delta.py | graphify/cache.py | file_hash() for staleness | WIRED | Lazy import at line 90: `from .cache import file_hash`; used at line 93 |
| graphify/delta.py | graphify/snapshot.py | load_snapshot for comparison | WIRED | Used via snapshot.py's auto_snapshot_and_delta (line 102-105) |
| graphify/__main__.py | graphify/snapshot.py | import save_snapshot, load_snapshot, list_snapshots | WIRED | Lines 945, 990, 995 |
| graphify/__main__.py | graphify/delta.py | import compute_delta, render_delta_md | WIRED | Lines 946, 996 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All lazy imports resolve | `python -c "from graphify import save_snapshot, load_snapshot, compute_delta, classify_staleness, render_delta_md, auto_snapshot_and_delta"` | "All lazy imports OK" | PASS |
| CLI help shows snapshot command | `python -m graphify --help \| grep snapshot` | 6 lines of snapshot help text | PASS |
| Snapshot + delta tests pass | `pytest tests/test_snapshot.py tests/test_delta.py -q` | 40 passed in 0.88s | PASS |
| Full test suite passes | `pytest tests/ -q` | 912 passed, 2 warnings in 11.13s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| DELTA-01 | 02, 03 | User can compare current graph run against previous run and see added/removed/changed nodes and edges in GRAPH_DELTA.md | SATISFIED | compute_delta + render_delta_md produce full diff; auto_snapshot_and_delta and CLI --from/--to wire it to user |
| DELTA-02 | 01, 03 | Graph snapshots persist to graphify-out/snapshots/ with automatic retention (default: keep last 10) | SATISFIED | save_snapshot writes to graphify-out/snapshots/, FIFO prune enforced on every save (cap=10 default) |
| DELTA-03 | 01 | Every extracted node carries extracted_at and source_hash metadata | SATISFIED | _extract_generic injects extracted_at (ISO), source_hash (SHA256), source_mtime on every code node |
| DELTA-04 | 02 | Nodes have three-state staleness: FRESH/STALE/GHOST | SATISFIED | classify_staleness returns FRESH/STALE/GHOST with mtime fast-gate and SHA256 authoritative check |
| DELTA-05 | 02 | GRAPH_DELTA.md uses summary+archive pattern | SATISFIED | render_delta_md produces ## Summary (counts + narrative) + ## Archive (full tables) |
| DELTA-06 | 02 | Community migration tracked: which nodes moved between communities | SATISFIED | compute_delta tracks community_migrations dict; render_delta_md renders Community Migrations table |
| DELTA-07 | 03 | graphify snapshot CLI saves named snapshot without full pipeline re-run | SATISFIED | `graphify snapshot --name <label>` loads graph.json directly, no extraction/build/cluster pipeline |
| DELTA-08 | 02 | Connectivity change metrics per node (degree delta, new/lost edges) in delta output | SATISFIED | compute_delta produces connectivity_changes with degree_delta + specific edges; rendered in Archive table |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No anti-patterns detected in snapshot.py, delta.py, or related test files |

### Human Verification Required

None. All phase deliverables are verifiable through automated checks. The phase produces data files (JSON snapshots, markdown reports) and CLI commands that can be fully tested programmatically.

### Gaps Summary

No gaps found. All 5 roadmap success criteria verified. All 8 DELTA requirements (DELTA-01 through DELTA-08) satisfied with implementation evidence. Full test suite (912 tests) passes with no regressions. All artifacts exist, are substantive, and are properly wired.

---

_Verified: 2026-04-12T23:45:00Z_
_Verifier: Claude (gsd-verifier)_
