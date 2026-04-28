---
phase: 28-self-ingestion-hardening
plan: "03"
subsystem: detect
tags: [vault-adapter, manifest, output-manifest, atomic-write, prior-files, FIFO, GC]
dependency_graph:
  requires:
    - 28-02 (detect() accepts resolved kwarg + nesting guard)
    - graphify/merge.py (_write_atomic canonical pattern)
    - graphify/output.py (ResolvedOutput.artifacts_dir anchor)
  provides:
    - _load_output_manifest / _save_output_manifest helpers in graphify/detect.py
    - prior_files prune in detect() when resolved is not None
    - Manifest write after successful export in __main__.py --obsidian branch
    - Manifest write after successful run in __main__.py run branch
  affects:
    - graphify/__main__.py (two lazy-import manifest write wire-points)
    - graphify/pipeline.py (run_corpus now receives resolved kwarg end-to-end)
tech_stack:
  added: []
  patterns:
    - atomic tmp+fsync+os.replace write (mirrors merge.py:_write_atomic)
    - FIFO rolling N=5 cap on output-manifest runs array
    - GC stale file entries on every _save_output_manifest call
    - silent skip (no warning) for prior_files matches in detect()
    - lazy import convention for _save_output_manifest inside __main__.py guards
key_files:
  created: []
  modified:
    - graphify/detect.py (_load_output_manifest, _save_output_manifest, prior_files prune)
    - graphify/__main__.py (two manifest write wire-points)
    - tests/test_detect.py (10 new output-manifest tests)
decisions:
  - "D-29: manifest writes happen ONLY after successful export (not in except blocks); --obsidian write is inside the else block post-sys.exit(1); run branch write is on the try-success path before finally"
  - "D-26: always read from resolved.artifacts_dir (stable anchor); notes_dir rename is transparent"
  - "D-27: prior_files prune is silent (no warning); only D-25 emits a warning on malformed manifest"
  - "D-21: when resolved is None, prior_files stays empty set; manifest is never accessed"
  - "_save_output_manifest in __main__.py uses lazy import convention consistent with the file"
metrics:
  duration: "383 seconds (~6 minutes)"
  completed: "2026-04-28"
  tasks_completed: 3
  files_changed: 3
  tests_added: 10
  tests_total: 1674
---

# Phase 28 Plan 03: output-manifest round-trip (VAULT-13) Summary

**One-liner:** Atomic output-manifest.json with FIFO N=5 / GC / renamed-notes-dir recovery wired post-export in both CLI branches.

## What Was Built

VAULT-13 closes the renamed-output-recovery loop: every successful export writes `<artifacts_dir>/output-manifest.json` recording the exact set of files exported. Subsequent runs read the manifest and prune those files from the input scan — even when `notes_dir` has been renamed between runs, because the stable anchor is `artifacts_dir` (D-26).

### Key components

**`graphify/detect.py` — two new helpers + prior_files prune:**

- `_load_output_manifest(artifacts_dir)`: returns `{"version": 1, "runs": []}` silently on missing file; emits one stderr warning on malformed JSON or wrong shape then returns empty envelope (D-25).
- `_save_output_manifest(artifacts_dir, notes_dir, written_files, run_id=None)`: loads existing manifest → GC stale file entries (D-28) → appends new run entry → FIFO-trims to 5 (D-24) → writes atomically via tmp+fsync+os.replace (D-29, verbatim pattern from merge.py:_write_atomic).
- `detect()`: when `resolved is not None`, builds `prior_files: set[str]` from all prior run entries; silently skips any file whose `str(p.resolve())` is in the set (D-27). Guard: `if resolved is None` → prior_files stays empty, manifest never accessed (D-21).

**`graphify/__main__.py` — two lazy-import wire-points:**

- `--obsidian` branch: manifest write inside the `else` block (real run, not dry-run), after `to_obsidian()` returns successfully and `sys.exit(1)` is unreachable. Uses `result.succeeded` (list[Path]) as written_files source. Guarded by `not isinstance(result, MergePlan) and resolved is not None`.
- `run` branch: manifest write immediately after `run_corpus(...)` succeeds (inside try, before finally). Uses `written_files=[]` (roots only; full file list is an --obsidian concern). Guarded by `resolved is not None`. Also threads `resolved=resolved` into `run_corpus(...)` call.

## TDD Gate Compliance

- RED commit: `4773d74` — `test(28-03)` — 10 failing tests with ImportError on missing helpers
- GREEN commit: `4537bcd` — `feat(28-03)` — all 10 tests pass after helpers added to detect.py
- REFACTOR: not needed; code was clean at GREEN

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all manifest functionality is fully wired end-to-end.

## Threat Flags

No new trust-boundary surfaces beyond those in the plan's threat model (T-28-09 through T-28-14). All mitigations implemented:

- T-28-10 (DoS on malformed manifest): `_load_output_manifest` catches all exceptions → empty envelope (D-25)
- T-28-11 (partial write on crash): tmp+fsync+os.replace; `except OSError` unlinks tmp and re-raises
- T-28-13 (write before export completes): both wire-points are post-success, outside any except block

## Self-Check: PASSED

- FOUND: graphify/detect.py (modified — `_load_output_manifest`, `_save_output_manifest`, `prior_files` prune)
- FOUND: graphify/__main__.py (modified — 2 lazy-import manifest write wire-points)
- FOUND: tests/test_detect.py (modified — 10 new output-manifest tests)
- Commits verified: 4773d74, 4537bcd, c0ec80b
- Full suite: 1674 passed, 1 xfailed, 8 warnings
