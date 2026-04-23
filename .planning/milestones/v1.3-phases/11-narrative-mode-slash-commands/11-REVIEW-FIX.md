---
phase: 11-narrative-mode-slash-commands
fixed_at: 2026-04-17T12:20:00Z
review_path: .planning/phases/11-narrative-mode-slash-commands/11-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-04-17T12:20:00Z
**Source review:** .planning/phases/11-narrative-mode-slash-commands/11-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, CR-02, WR-01, WR-02)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Snapshot path double-nesting — Phase 11 tools always return `insufficient_history` in production

**Files modified:** `graphify/serve.py`, `tests/test_serve.py`
**Commit:** 8c66ea0
**Applied fix:** Changed all four closure call sites in `serve()` from `_run_graph_summary(G, communities, _out_dir, ...)`, `_run_entity_trace(G, _out_dir, ...)`, `_run_drift_nodes(G, _out_dir, ...)`, and `_run_newly_formed_clusters(G, communities, _out_dir, ...)` to pass `_out_dir.parent` instead of `_out_dir`. Since `list_snapshots(root)` in `snapshot.py` appends `graphify-out/snapshots/` to `root`, passing `_out_dir` (which is already `graphify-out/`) caused it to scan `graphify-out/graphify-out/snapshots/` — a path that never exists. Passing `_out_dir.parent` (the project root) resolves correctly to `graphify-out/snapshots/`. Added regression test `test_graph_summary_snapshot_root_not_double_nested` that simulates the production layout (`graph_path = tmp_path/graphify-out/graph.json`) and asserts `snapshot_count >= 1` after saving a snapshot, which would be 0 if the double-nesting bug were present.

### CR-02: `_cursor_install()` called without required `project_dir` argument

**Files modified:** `graphify/__main__.py`, `tests/test_install.py`
**Commit:** 60ba3d7
**Applied fix:** Added the missing `Path(".")` argument at line 181 in `install()`: `_cursor_install(Path("."))`. This matches the correct pattern already used at the direct CLI path at line 1618. Added regression test `test_install_cursor_via_install_helper` that calls `install(platform="cursor")` via the public helper (not `_cursor_install` directly) using a monkeypatched stub, verifying the stub is called with a `Path` argument and no `TypeError` is raised.

### WR-01: `_run_graph_summary` — `comms_prev` from snapshot not explicitly deleted

**Files modified:** `graphify/serve.py`
**Commit:** 455f5f8
**Applied fix:** Added `del comms_prev` immediately after `del G_prev` in `_run_graph_summary`, after the scalar extraction into `delta_block` is complete. This matches the memory-discipline pattern used in all other snapshot-chain walkers (`_run_entity_trace`, `_run_drift_nodes`, `_run_newly_formed_clusters`).

### WR-02: `ghost.md` instructs parsing `meta.status` on tools that return plain text — dead guard

**Files modified:** `graphify/commands/ghost.md`, `tests/test_commands.py`
**Commit:** 60022fd
**Applied fix:** Replaced the dead `Parse meta.status on both responses` / `If either response has status == no_graph` instruction in `ghost.md` with correct response-shape descriptions: `get_annotations returns a JSON array (not a meta envelope)` and `god_nodes returns plain text (not a meta envelope)`, plus actionable guards for empty-array and empty-list cases. Split `test_stretch_command_files_have_no_graph_guard` to exclude `ghost` (which legitimately has no meta envelope) and added `test_ghost_md_guard_wording` that asserts ghost.md describes a JSON array response, guards on empty array/list, and contains no reference to `meta.status`.

---

_Fixed: 2026-04-17T12:20:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
