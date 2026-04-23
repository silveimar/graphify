---
phase: 06-graph-delta-analysis-staleness
fixed_at: 2026-04-12T00:00:00Z
review_path: .planning/phases/06-graph-delta-analysis-staleness/06-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-04-12
**Source review:** .planning/phases/06-graph-delta-analysis-staleness/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: --from without --to (or vice versa) silently ignored

**Files modified:** `graphify/__main__.py`
**Commit:** 634180a
**Applied fix:** Added validation after arg-parsing loop that checks `bool(from_path) != bool(to_path)` and exits with an error message if only one of `--from`/`--to` is provided.

### WR-02: --cap accepts zero or negative values, which deletes all snapshots

**Files modified:** `graphify/__main__.py`, `graphify/snapshot.py`
**Commit:** fc430e3
**Applied fix:** Added `cap < 1` validation in both `--cap` and `--cap=` arg parsing branches in `__main__.py`, printing an error and exiting with code 2. Also added a defensive guard in `snapshot.py`'s `save_snapshot` function that clamps `cap` to 1 if it somehow reaches the FIFO prune logic with an invalid value.

### WR-03: --delta output path relative to cwd not graph root

**Files modified:** `graphify/__main__.py`
**Commit:** 34ea1c5
**Applied fix:** In the `--from/--to` block, derived `graph_root` from the resolved graph path's parent-parent (`graph_path -> graphify-out/graph.json -> project root`) and used it for the output path. In the `--delta` block, derived `graph_root` from the already-resolved `gp` variable and passed it to `list_snapshots(graph_root)` and used it for the delta output path.

### WR-04: Floating-point mtime comparison may produce false FRESH results

**Files modified:** `graphify/delta.py`
**Commit:** e78ba14
**Applied fix:** Added `isinstance(stored_mtime, float)` type guard to the mtime equality check. This ensures the fast mtime gate is only used when the stored value is the same type as `stat().st_mtime`, preventing false FRESH results from JSON round-trip precision loss (e.g., when a float is deserialized as an int).

## Skipped Issues

None -- all in-scope findings were fixed.

---

_Fixed: 2026-04-12_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
