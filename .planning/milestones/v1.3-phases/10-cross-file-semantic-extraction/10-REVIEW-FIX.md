---
phase: 10-cross-file-semantic-extraction
fixed_at: 2026-04-16T20:55:00Z
review_path: .planning/phases/10-cross-file-semantic-extraction/10-REVIEW.md
iteration: 2
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-04-16T20:55:00Z
**Source review:** `.planning/phases/10-cross-file-semantic-extraction/10-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 10 (all severities, per `--all`)
- Fixed: 10 (3 in iteration 1, 7 in iteration 2)
- Skipped: 0

## Previously fixed (iteration 1)

The three Warning findings were fixed in the first pass — see `.planning/phases/10-cross-file-semantic-extraction/10-REVIEW-FIX.md` history at commit `b2280a9` for the full applied-fix detail. Summary preserved here for traceability:

### WR-01: `graphify --dedup --graph graph.json` hard-rejects node-link format

**Files modified:** `graphify/__main__.py`, `tests/test_main_cli.py`
**Commit:** `7562073`
**Applied fix:** Mirrored `graphify/validate.py`'s `"links"` -> `"edges"` fallback in the `--dedup` shape-check so NetworkX node-link format is accepted. Added `test_dedup_accepts_node_link_graph_json` regression test.

### WR-02: `_resolved_aliases[canonical] = node_id` loses original alias when multiple aliases redirect to the same canonical

**Files modified:** `graphify/serve.py`, `tests/test_serve.py`
**Commit:** `a4452fe`
**Applied fix:** Changed `_resolved_aliases` from `dict[str, str]` to `dict[str, list[str]]` and switched the recorder to `setdefault(canonical, []).append(node_id)` (idempotent). Added `test_run_query_graph_records_all_aliases_for_same_canonical` regression test.

### WR-03: `_run_query_graph` mutates the caller's `arguments` dict in place

**Files modified:** `graphify/serve.py`, `tests/test_serve.py`
**Commit:** `7819bb9`
**Applied fix:** Inserted `arguments = dict(arguments)` at the head of `_run_query_graph` so all subsequent rewrites operate on a local shallow copy. Added `test_run_query_graph_does_not_mutate_caller_arguments` regression test.

## Fixed Issues

### IN-01: Dead/redundant assignment in `_split_by_top_dir`

**Files modified:** `graphify/batch.py`
**Commit:** `9c21361`
**Applied fix:** Removed the dead `common = Path(*[p.parent for p in paths]) if len(paths) == 1 else paths[0].parent` line. The `if len(paths) == 1` branch is unreachable because `_split_by_top_dir` early-returns at `if len(component) <= 1` higher up. Replaced the dead assignment with an inline comment documenting the `len(paths) > 1` invariant, leaving the unconditional `common = Path(os.path.commonpath(...))` line that already produces the correct value. All 9 tests in `test_batch.py` pass.

### IN-02: Inline `import os` in `_split_by_top_dir`

**Files modified:** `graphify/batch.py`
**Commit:** `3addd44`
**Applied fix:** Hoisted `import os` from the function body to the module top, alphabetically between `from __future__ import annotations` and `import sys`. Removed the inline `import os` inside `_split_by_top_dir`. Brings `batch.py` into line with the rest of the package's PEP 8 / project import-organization style. All 9 tests in `test_batch.py` pass.

### IN-03: `_load_dedup_report` silently swallows OS errors (no warning)

**Files modified:** `graphify/serve.py`
**Commit:** `38792d9`
**Applied fix:** Split the combined `except (json.JSONDecodeError, OSError)` clause in `_load_dedup_report` into two distinct `except` branches. `json.JSONDecodeError` keeps the existing parse-error warning. `OSError as e` now also prints a warning to stderr (`could not read dedup_report.json ({e}); alias map disabled`) so unreadable reports surface a diagnostic instead of silently disabling alias redirection. All 123 tests in `test_serve.py` pass.

### IN-04: Inconsistent label sanitization between `dedup_report.md` and `GRAPH_REPORT.md`

**Files modified:** `graphify/security.py`, `graphify/dedup.py`
**Commit:** `ae83a2c`
**Applied fix:** Added a shared `sanitize_label_md` helper to `graphify/security.py` (replaces backticks with apostrophes and HTML-escapes angle brackets — same protections as the private `_sanitize_md` in `report.py`). Updated `_render_dedup_md` to use `sanitize_label_md(sanitize_label(...))` instead of `html.escape(sanitize_label(...))`, so dedup_report.md now strips backticks identically to `GRAPH_REPORT.md`. Removed the now-unused `import html` from `dedup.py`. Centralizing the helper in `security.py` matches the project convention (CLAUDE.md: "All external input sanitization is centralized in `graphify/security.py`"). 43 tests in `test_security.py` + `test_dedup.py` pass; 45 tests in `test_report.py` still pass (no regression).

### IN-05: `<-` arrow in `dedup_report.md` becomes `&lt;-` after `html.escape`

**Files modified:** `graphify/dedup.py`
**Commit:** `127e1cd`
**Applied fix:** Replaced the literal `<-` arrow in the `_render_dedup_md` line template with `←` (U+2190), matching `report.py:272`. Both `GRAPH_REPORT.md` and `dedup_report.md` now use the same arrow glyph. All 22 tests in `test_dedup.py` pass; no test asserted on the literal `<-`.

### IN-06: `_merge_extraction` uses O(n²) `not in` check when folding `source_file`

**Files modified:** `graphify/dedup.py`
**Commit:** `9435394`
**Applied fix:** Refactored the per-eliminated `source_file` accumulation loop from O(n²) list `not in` checks to an O(1) set with `update`/`add`. Output normalization is unchanged: `sorted(sf_set)` for ≥2 entries, single string for 1, empty string for 0 — the canonical `sorted` output makes set-based folding behaviorally identical to the previous list-based implementation regardless of insertion order. Annotated with a comment noting the equivalence. All 22 tests in `test_dedup.py` pass.

### IN-07: Docstring for `_load_dedup_report` lists three fallback candidate paths, but `_hydrate_merged_from` uses a different search order

**Files modified:** `graphify/export.py`
**Commit:** `97ce533`
**Applied fix:** Removed the redundant `output_dir / ".." / "dedup_report.json"` candidate from `_hydrate_merged_from` (equivalent to candidate 1 after `.resolve()`). Updated the docstring to document the two-candidate precedence (preferred: `output_dir.parent`, fallback: `Path("graphify-out")` cwd-relative). Added an inline comment noting the dropped redundant path so future readers don't reintroduce it. All 15 tests in `test_export.py` pass.

---

_Fixed: 2026-04-16T20:55:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
