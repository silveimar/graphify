---
phase: 04-merge-engine
plan: 05
subsystem: merge
tags: [merge, apply, atomic-writes, content-hash, lazy-exports, phase-4]

# Dependency graph
requires:
  - phase: 04-04
    provides: "compute_merge_plan + MergePlan output — apply_merge_plan consumes this"
  - phase: 04-03
    provides: "MergeAction/MergePlan/MergeResult dataclasses + _parse_frontmatter + _parse_sentinel_blocks + _merge_frontmatter + _merge_body_blocks"
  - phase: 01-foundation
    provides: "profile.py _dump_frontmatter + validate_vault_path"
provides:
  - "graphify/merge.py: apply_merge_plan public function (D-70 side-effectful half)"
  - "graphify/merge.py: _write_atomic — crash-safe .tmp + fsync + os.replace protocol"
  - "graphify/merge.py: _cleanup_stale_tmp — defensive stale .tmp removal at run start"
  - "graphify/merge.py: _synthesize_file_text — final text synthesis for CREATE/REPLACE/UPDATE"
  - "graphify/merge.py: _hash_bytes — SHA-256 content-hash for identical-skip comparison"
  - "graphify/__init__.py: lazy imports for compute_merge_plan, apply_merge_plan, MergePlan, MergeAction, MergeResult, RenderedNote"
affects:
  - 04-06-dry-run       # dry-run calls compute_merge_plan and reads MergePlan; apply is the write counterpart
  - 05-integration      # Phase 5 CLI wires to_obsidian -> compute_merge_plan -> apply_merge_plan

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic write: .tmp + os.fsync + os.replace — crash-safe on POSIX and Windows"
    - "Content-hash skip: SHA-256 comparison before any write; idempotent re-runs produce zero FS churn"
    - "D-72 ORPHAN contract: ORPHAN/SKIP_PRESERVE/SKIP_CONFLICT produce zero writes — no arbitrary file deletion"
    - "Stale .tmp cleanup: rglob('*.md.tmp') at apply start as defensive pass"
    - "Lazy __init__.py map: 6 new Phase 4 symbols added without eager imports"

key-files:
  created: []
  modified:
    - graphify/merge.py
    - graphify/__init__.py
    - tests/test_merge.py

key-decisions:
  - "apply_merge_plan re-synthesizes file text from MergeAction + RenderedNote + profile rather than baking text into MergeAction at compute time — avoids O(vault_size) MergePlan inflation and enables Phase 5 --dry-run to skip text synthesis"
  - "_synthesize_file_text raises ValueError for SKIP_*/ORPHAN actions — caller (apply_merge_plan) guards against those before calling synthesis, so the raise is a programming-error sentinel, not a user-facing error"
  - "Content-hash skip fires for ALL write actions (CREATE included) — if a CREATE target already exists with identical bytes, it is treated as skipped_identical; this covers the edge case of a file created outside apply's CREATE path"
  - "imports hashlib and os at module level inside the apply-layer section (not at top of file) to keep section locality readable; Python de-duplicates the import at runtime"

patterns-established:
  - "apply_merge_plan is the mirror of compute_merge_plan: compute reads/decides, apply writes/reports"
  - "MergeResult.skipped_identical is the idempotence audit trail — callers can assert zero writes on unchanged vaults"
  - "test_apply_atomic_no_partial_file_on_error uses monkeypatch on os.replace to simulate disk failure — verifies .tmp cleanup and original file integrity"

requirements-completed: [MRG-01, MRG-07]

# Metrics
duration: ~5min
completed: 2026-04-11
---

# Phase 4 Plan 05: apply_merge_plan Summary

**apply_merge_plan delivers the side-effectful write half of Phase 4: atomic `.tmp + fsync + os.replace` writes for CREATE/UPDATE/REPLACE actions, SHA-256 content-hash skip for idempotent re-runs, strict ORPHAN/SKIP_* no-op contract, defensive stale-tmp cleanup, and full lazy export wiring of all six Phase 4 public symbols into `graphify/__init__.py`.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-11T17:03:40Z
- **Completed:** 2026-04-11T17:08:02Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 3 (`graphify/merge.py`, `graphify/__init__.py`, `tests/test_merge.py`)
- **Lines added to merge.py:** 181 (730 → 911 total)
- **Tests added:** 11 (63 from Plans 03+04 + 11 new = 74 total passing)

## Accomplishments

### Atomic Write Protocol

`_write_atomic(target, content)` implements the crash-safe write sequence:

1. Compute `.tmp` path as `target.with_suffix(target.suffix + ".tmp")`
2. `target.parent.mkdir(parents=True, exist_ok=True)` — creates intermediate dirs (inside vault_dir after `_validate_target`)
3. Open `.tmp` for writing, call `fh.flush()` + `os.fsync(fh.fileno())` — data durable before replace
4. `os.replace(tmp, target)` — atomic on POSIX and Windows
5. On `OSError`: best-effort `tmp.unlink()` — no partial `.tmp` remains

### Content-Hash Skip

Before writing any action, `apply_merge_plan` computes `_hash_bytes(new_bytes)` and compares to `_hash_bytes(existing_bytes)`. If identical, the path is added to `MergeResult.skipped_identical` and no write is performed. This makes re-running graphify on an unchanged vault produce **zero filesystem writes**.

### ORPHAN / SKIP_* No-Op Contract (D-72)

`apply_merge_plan` skips the `SKIP_PRESERVE`, `SKIP_CONFLICT`, and `ORPHAN` action types entirely — they do not appear in `succeeded`, `failed`, or `skipped_identical`. No file is ever deleted. Tested by `test_apply_orphan_never_deleted` (the orphan file remains on disk after apply) and `test_apply_skip_preserve_noop` (mtime unchanged).

### Stale .tmp Cleanup

`_cleanup_stale_tmp(vault_dir)` runs at the top of every `apply_merge_plan` call. It uses `vault_dir.rglob("*.md.tmp")` to find leftover `.tmp` files from previous aborted runs and unlinks them (unlinks the symlink itself if the `.tmp` is a symlink, per T-04-22). Tested by `test_apply_cleanup_stale_tmp`.

### Phase 4 Public API Surface (graphify/__init__.py)

Six new entries in the lazy `_map` dict:

| Symbol | Module | Type |
|--------|--------|------|
| `compute_merge_plan` | `graphify.merge` | function |
| `apply_merge_plan` | `graphify.merge` | function |
| `MergeAction` | `graphify.merge` | dataclass |
| `MergePlan` | `graphify.merge` | dataclass |
| `MergeResult` | `graphify.merge` | dataclass |
| `RenderedNote` | `graphify.merge` | TypedDict |

`__init__.py` stays at 45 lines (≤50 limit respected).

### Integration Tests — 11 tests covering all must_haves

| Test | Coverage |
|------|----------|
| `test_apply_empty_plan_returns_empty_result` | Empty plan baseline |
| `test_apply_create_writes_new_file` | CREATE path, no .tmp remains |
| `test_apply_update_idempotent_skips_write` | Content-hash skip, mtime unchanged |
| `test_apply_update_changed_source_file_writes` | Changed UPDATE writes, succeeded list |
| `test_apply_replace_overwrites_preserve_fields` | REPLACE drops rank/mapState (M3) |
| `test_apply_skip_preserve_noop` | SKIP_PRESERVE zero writes (M2 end-to-end) |
| `test_apply_orphan_never_deleted` | ORPHAN file remains on disk (D-72/M8) |
| `test_apply_skip_conflict_no_write` | SKIP_CONFLICT leaves content unchanged |
| `test_apply_cleanup_stale_tmp` | Stale .tmp removal at apply start |
| `test_apply_atomic_no_partial_file_on_error` | Disk-error leaves original intact, no .tmp remains |
| `test_apply_path_escape_recorded_as_failed` | Path-escape lands in failed, no write |

## Task Commits

1. **RED:** `2960806` — `test(04-05): add failing tests for apply_merge_plan (RED — 11 tests)`
2. **Task 1 GREEN:** `1201c43` — `feat(04-05): implement apply_merge_plan + atomic write helpers (Task 1 GREEN)`
3. **Task 2 GREEN:** `a83e43f` — `feat(04-05): wire Phase 4 lazy exports + apply_merge_plan tests (Task 2 GREEN)`

## Files Modified

- `graphify/merge.py` (911 lines, +181 from Plan 04's 730)
- `graphify/__init__.py` (45 lines, +6 entries)
- `tests/test_merge.py` (845 lines, +232 from Plan 04's 613)

## Decisions Made

- **Text synthesis deferred to apply time, not baked into MergeAction.** compute_merge_plan records action type + changed keys only. apply_merge_plan re-runs the merge logic using the plan action as a dispatch key. This keeps MergePlan memory O(action_count), not O(vault_size), and lets Phase 5's `--dry-run` skip text synthesis entirely.
- **Content-hash skip covers CREATE as well as UPDATE/REPLACE.** If a CREATE target already exists on disk with identical bytes (e.g., two apply runs with no vault changes in between), the write is skipped. This is strictly more conservative than necessary but costs nothing.
- **`hashlib` and `os` imported inline at the apply-layer section boundary.** Python caches the import so runtime cost is zero. This keeps the section visually self-contained without changing the module's import surface.

## Deviations from Plan

None — plan executed exactly as written. All code blocks in the `<action>` sections were implemented verbatim; test function names match the `<behavior>` spec exactly.

## Known Stubs

None — apply_merge_plan writes real content to disk; all data flows are wired. No placeholder text or empty-collection pass-throughs affecting output.

## Threat Model Coverage

| Threat ID | Status | Notes |
|-----------|--------|-------|
| T-04-20 | Accepted | TOCTOU between compute and apply is documented. Atomic `.tmp + os.replace` makes the write itself atomic; the race window is between plan computation and apply execution, accepted as batch-tool limitation. |
| T-04-21 | Mitigated | `_validate_target` is called on every action path before any write. Symlink-escaped paths raise ValueError → recorded in `MergeResult.failed`, no write. Tested in `test_apply_path_escape_recorded_as_failed`. |
| T-04-22 | Mitigated | `_cleanup_stale_tmp` calls `tmp.unlink()` — unlinks the symlink itself (Python semantics), not the symlink target. A malicious `.tmp` symlink pointing outside vault_dir is unlinked safely. |
| T-04-23 | Accepted | Single-pass `rglob` walk is O(n). No cap in v1 — Phase 5 can scope with a path argument if needed. |
| T-04-24 | Mitigated | `_validate_target` is called BEFORE `target.parent.mkdir`. Paths whose parents would escape vault_dir never reach `mkdir`. |
| T-04-25 | Accepted | `MergeResult.failed` error strings are diagnostic. Phase 5 CLI will sanitize for display. Not a credentials leak. |
| T-04-26 | Accepted | `MergeResult.succeeded` is the write audit trail. Phase 5 `GRAPH_REPORT.md` will surface it. |

## Threat Flags

None — no new network endpoints, auth paths, file access patterns outside the declared vault_dir write scope, or schema changes. `apply_merge_plan` is a pure filesystem writer bounded by `_validate_target`.

## Self-Check: PASSED
