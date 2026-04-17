---
phase: 10-cross-file-semantic-extraction
fixed_at: 2026-04-16T20:35:00Z
review_path: .planning/phases/10-cross-file-semantic-extraction/10-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 7
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-04-16T20:35:00Z
**Source review:** `.planning/phases/10-cross-file-semantic-extraction/10-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (Critical + Warning, per `--scope critical_warning`)
- Fixed: 3
- Skipped: 7 (Info — out of scope unless `--all` specified)

## Fixed Issues

### WR-01: `graphify --dedup --graph graph.json` hard-rejects node-link format

**Files modified:** `graphify/__main__.py`, `tests/test_main_cli.py`
**Commit:** `7562073`
**Applied fix:** Mirrored `graphify/validate.py`'s `"links"` -> `"edges"` fallback in the `--dedup` shape-check. Before the existing `if "nodes" not in extraction or "edges" not in extraction` guard, the CLI now normalizes NetworkX node-link format by promoting `extraction["links"]` to `extraction["edges"]` when only `links` is present. Added `test_dedup_accepts_node_link_graph_json` regression test feeding `{"nodes": [], "links": []}` through `--dedup --graph graph.json` and asserting a 0-merge dedup report is produced.

### WR-02: `_resolved_aliases[canonical] = node_id` loses original alias when multiple aliases redirect to the same canonical

**Files modified:** `graphify/serve.py`, `tests/test_serve.py`
**Commit:** `a4452fe`
**Applied fix:** Changed `_resolved_aliases` from `dict[str, str]` to `dict[str, list[str]]` and switched the recorder to `setdefault(canonical, []).append(node_id)` (with idempotency guard `if node_id not in aliases`). Updated the `_run_query_graph` docstring describing the `resolved_from_alias` meta shape to document the list-of-aliases per canonical contract (D-16 schema). Added `test_run_query_graph_records_all_aliases_for_same_canonical` which feeds two distinct aliases (`auth`, `auth_svc`) collapsing to one canonical (`authentication_service`) via `seed_nodes` and asserts both aliases appear in `meta["resolved_from_alias"]["authentication_service"]`.

### WR-03: `_run_query_graph` mutates the caller's `arguments` dict in place

**Files modified:** `graphify/serve.py`, `tests/test_serve.py`
**Commit:** `7819bb9`
**Applied fix:** Inserted `arguments = dict(arguments)` immediately before the alias-resolution loop in `_run_query_graph`, so all subsequent rewrites of `arguments[_alias_field]` and `arguments["seed_nodes"]` operate on a local shallow copy instead of the caller's dict. Added `test_run_query_graph_does_not_mutate_caller_arguments` which snapshots `node_id` and `seed_nodes`, runs the dispatch with two aliases, and asserts the caller's `arguments` dict still holds the original (pre-resolution) IDs.

## Skipped Issues

### IN-01: Dead/redundant assignment in `_split_by_top_dir`

**File:** `graphify/batch.py:117-120`
**Reason:** out of scope (`--all` not specified)
**Original issue:** First assignment to `common` is dead code — the `if len(paths) == 1 else ...` branch is unreachable due to early return at line 114; the next line unconditionally overwrites `common` via `os.path.commonpath`.

### IN-02: Inline `import os` in `_split_by_top_dir`

**File:** `graphify/batch.py:119`
**Reason:** out of scope (`--all` not specified)
**Original issue:** `import os` is placed inline in the function body instead of at the top of the module — minor PEP 8 / project import-organization style inconsistency.

### IN-03: `_load_dedup_report` silently swallows OS errors (no warning)

**File:** `graphify/serve.py:99-103`
**Reason:** out of scope (`--all` not specified)
**Original issue:** Combined `except (json.JSONDecodeError, OSError)` clause prints a warning only for the JSON parse case; OSError silently returns `{}`, hiding permission/device errors that disable alias redirection.

### IN-04: Inconsistent label sanitization between `dedup_report.md` and `GRAPH_REPORT.md`

**File:** `graphify/dedup.py:579-581` vs `graphify/report.py:264-267`
**Reason:** out of scope (`--all` not specified)
**Original issue:** `_render_dedup_md` uses `html.escape(sanitize_label(...))` which leaves backticks untouched, breaking the surrounding inline-code markdown when canonical labels contain backticks. `report.py:_sanitize_md` already replaces backticks with apostrophes.

### IN-05: `<-` arrow in `dedup_report.md` becomes `&lt;-` after `html.escape`

**File:** `graphify/dedup.py:584`
**Reason:** out of scope (`--all` not specified)
**Original issue:** `dedup_report.md` uses literal `<-` while `report.py:272` uses `←` (U+2190); minor aesthetic inconsistency between the two report surfaces.

### IN-06: `_merge_extraction` uses O(n^2) `not in` check when folding `source_file`

**File:** `graphify/dedup.py:466-471`
**Reason:** out of scope (`--all` not specified)
**Original issue:** Per-eliminated `if s and s not in sf_list:` is O(n) on a list — O(n*m^2) across n merges with m source files each. Negligible for typical merge groups; flagged for awareness on large-merge cases.

### IN-07: Docstring for `_load_dedup_report` lists three fallback candidate paths, but `_hydrate_merged_from` uses a different search order

**File:** `graphify/export.py:454-462`
**Reason:** out of scope (`--all` not specified)
**Original issue:** Three search candidates for `dedup_report.json` — candidates 1 and 2 are equivalent after `.resolve()` (redundant), candidate 3 is cwd-relative (surprises users invoking from a parent directory). Clarity / maintainability concern; not a bug.

---

_Fixed: 2026-04-16T20:35:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
