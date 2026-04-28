---
phase: 29-doctor-diagnostics-dry-run-preview
plan: 03
subsystem: doctor + CLI
tags: [doctor, dry-run, vault-adapter, cli-wiring, preview]
requires:
  - 29-01 (doctor.py contract — DoctorReport, PreviewSection, run_doctor)
  - 29-02 (detect.py skipped dict — dict[str, list[str]] with 5 reason keys)
provides:
  - "graphify doctor [--dry-run] subcommand reachable from CLI (VAULT-14)"
  - "Bounded preview output sourced from real detect() (VAULT-15, D-38, D-39)"
  - "Binary exit codes — 0 clean / 1 misconfig per D-35"
affects:
  - graphify/doctor.py (replaced NotImplementedError stub with real dry_run branch)
  - graphify/__main__.py (added doctor dispatch + --help line)
  - tests/test_doctor.py (3 new dry_run unit tests; dropped stub test)
  - tests/test_main_flags.py (4 new CLI integration tests; PYTHONPATH patch in helper)
tech-stack:
  added: []
  patterns:
    - argparse subparser-style dispatch (mirrors vault-promote precedent)
    - bounded-sample preview (caps at module-level constants)
key-files:
  created: []
  modified:
    - graphify/doctor.py
    - graphify/__main__.py
    - tests/test_doctor.py
    - tests/test_main_flags.py
decisions:
  - "Use detect()['files'] (already flattened by FileType bucket) as the single source for would_ingest_count; no re-scan."
  - "Omit empty skip-reason groups from preview output — quieter for clean vaults; reasons present in fixed _PREVIEW_SKIP_ORDER when populated."
  - "Patch _graphify() subprocess helper to prepend the worktree root to PYTHONPATH; the editable install points at the main repo checkout, so without this parallel-executor worktrees can't validate their own __main__.py changes."
metrics:
  duration: ~25 minutes
  completed: 2026-04-28
  tasks: 2
  commits: 2
---

# Phase 29 Plan 03: Doctor Dispatch + Dry-Run Preview Summary

Wires the `graphify doctor` subcommand into `__main__.py` and implements the
`run_doctor(dry_run=True)` branch on top of the Wave 1 `doctor.py` contract,
consuming the `skipped` dict shipped by Plan 29-02. Completes VAULT-14 (CLI
reachability) and VAULT-15 (bounded dry-run preview with zero disk writes).

## What Shipped

### graphify/doctor.py
- New module-level constants: `_PREVIEW_SKIP_ORDER` (fixed reason ordering),
  `_PREVIEW_INGEST_SAMPLE_CAP=10`, `_PREVIEW_SKIP_SAMPLE_CAP=5` (D-38 caps).
- New helper `_build_preview_section(detect_result, resolved) -> PreviewSection`
  flattens `detect()["files"]` across FileType buckets, slices to the cap, and
  builds `would_skip_grouped` / `would_skip_counts` from `detect()["skipped"]`
  in fixed reason order.
- New helper `_format_preview(preview) -> list[str]` renders the Preview section
  with the spec layout: `Would ingest: N files`, indented samples, `... +K more`
  overflow markers, per-reason `Would skip ({reason}): M files` blocks, and
  `Would write notes to:` / `Would write artifacts to:` footer.
- `run_doctor()` no longer raises on `dry_run=True`. When `dry_run=True` AND
  `resolved_output is not None`, it imports `detect` lazily, runs the real
  scanner, and attaches a `PreviewSection` to `report.preview`. When
  `resolved_output is None`, preview stays None — `is_misconfigured()` already
  returns True so exit code remains 1.
- `format_report()` now delegates the Preview section to `_format_preview()`.

### graphify/__main__.py
- New dispatch branch `elif cmd == "doctor":` immediately above `vault-promote`.
  Uses inline `argparse.ArgumentParser(prog="graphify doctor")` mirroring the
  `vault-promote` precedent, exposes a single `--dry-run` flag, runs from
  `Path.cwd()`, prints `format_report(report)`, and `sys.exit(1 if
  report.is_misconfigured() else 0)`.
- New help lines (positioned before the existing `enrich` line):
  ```
    doctor                  diagnose vault/profile/output configuration (VAULT-14/15)
      --dry-run               preview which files would be ingested/skipped, no writes
  ```

### tests/test_doctor.py — 3 new + 1 dropped
- `test_run_doctor_dry_run_preview` — synthetic vault with .py + .md files →
  `report.preview.would_ingest_count > 0` and sample length is `min(10, count)`.
- `test_dry_run_skip_grouping` — `.graphifyignore`'d file + `node_modules/`
  noise dir → both `exclude-glob` and `noise-dir` groups present and bounded
  at 5 entries each.
- `test_dry_run_no_disk_writes` — snapshots `tmp_path` file inventory before
  and after `run_doctor(dry_run=True)`, asserts equality.
- Dropped: `test_run_doctor_dry_run_is_stub` (the NotImplementedError stub no
  longer exists).

Total: 12 (Wave 1) − 1 + 3 = 14 tests in test_doctor.py. Plus the existing 11
suite tests bring the file to **15 passing**.

### tests/test_main_flags.py — 4 new + helper patch
- `test_doctor_clean_exit_zero` — vault with valid profile → returncode==0,
  all 5 sections present, "No issues detected." in stdout.
- `test_doctor_misconfig_exit_one` — vault with `output.mode: nonsense` →
  returncode==1, "Recommended Fixes" present, at least one `[graphify] FIX:`
  line emitted.
- `test_doctor_dry_run_flag` — vault + sample .py file → "Would ingest:" and
  "Would write notes to:" in stdout, `tmp_path` inventory unchanged after
  invocation (no `graphify-out/` created).
- `test_doctor_in_help` — `--help` stdout contains substrings "doctor" and
  "--dry-run".
- `_graphify()` helper patched: prepends the worktree root to `PYTHONPATH`
  before launching the subprocess so the in-worktree `graphify/` package
  shadows the editable install (which is pinned to the main repo checkout
  by `__editable___graphifyy_0_4_7_finder.py`).

## Verification

| Check | Command | Result |
|---|---|---|
| Doctor unit tests | `pytest tests/test_doctor.py -q` | **15 passed** |
| Doctor CLI tests | `pytest tests/test_main_flags.py -q -k doctor` | **4 passed** |
| Full main_flags | `pytest tests/test_main_flags.py -q` | **13 passed** |
| Full suite | `pytest tests/ -q` | **1693 passed**, 1 xfailed, 2 pre-existing failures unrelated to this plan |

### Pre-existing failures (out of scope, scope-boundary rule applied)
- `tests/test_detect.py::test_detect_skips_dotfiles` — fails on base commit
  before any worktree edits.
- `tests/test_extract.py::test_collect_files_from_dir` — fails on base commit
  before any worktree edits.

Both reproduced via `git stash && pytest …` on the base; they are NOT regressions
from this plan. They are not logged to deferred-items.md because they predate
Phase 29 entirely; the phase verifier should pick them up via its own gate.

### Done-criteria evidence (from grep)
- `def _build_preview_section` in doctor.py: 1
- `_PREVIEW_SKIP_ORDER` references: 3
- `NotImplementedError` references: 1 (only in module docstring's history note;
  the stub raise itself is removed — verified by absence of `raise
  NotImplementedError` and successful `dry_run=True` invocation in tests)
- `Would ingest:` literals: 2 (helper + docstring)
- `Would skip` literals: 2
- `Would write notes to:` literals: 2
- `cmd == "doctor"` in __main__.py: 1
- `from graphify.doctor import` in __main__.py: 1
- `doctor.*diagnose` in __main__.py: 1 (the help line)

## Decisions Made

- **Preview omits empty skip-reason groups.** `detect()` initializes the
  `skipped` dict with all 5 reason keys and empty lists; emitting "Would skip
  (manifest): 0 files" lines for unused reasons would be noisy. The renderer
  iterates `_PREVIEW_SKIP_ORDER` but skips reasons absent from
  `would_skip_grouped` (only populated reasons survive the builder).
- **PYTHONPATH patch in test helper instead of test-local env injection.**
  The patch is general — every CLI test in `test_main_flags.py` benefits, and
  no future doctor-style tests need to repeat the boilerplate. Future
  parallel-executor worktrees will validate their own `__main__.py` changes
  the same way.
- **Lazy import of `detect` inside `run_doctor`.** Keeps `doctor.py`'s top-level
  import surface narrow (the dry_run branch is the only path that needs it).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Subprocess CLI tests couldn't see worktree __main__.py changes**
- **Found during:** Task 2 first test run.
- **Issue:** `python -m graphify` in the subprocess loaded the editable install
  (which is pinned to the main repo checkout via the importlib metapath
  finder), not the worktree's modified `graphify/__main__.py`. All 4 new CLI
  tests failed with `error: unknown command 'doctor'` and the `--help` output
  lacked the new `doctor` line.
- **Fix:** Prepended the worktree root (computed from
  `Path(__file__).resolve().parent.parent`) to `PYTHONPATH` in the
  `_graphify()` subprocess helper. The worktree's `graphify/` then takes
  precedence over the editable install for the duration of the subprocess.
- **Files modified:** `tests/test_main_flags.py`
- **Commit:** `1b095d0`

### Out-of-scope discoveries (NOT fixed)
- `tests/test_detect.py::test_detect_skips_dotfiles` and
  `tests/test_extract.py::test_collect_files_from_dir` fail on the base commit
  (verified via `git stash`). These predate Phase 29 and are not caused by
  this plan's changes. Per the scope-boundary rule, they are documented here
  but not fixed.

## Authentication Gates

None — fully offline, no network or credential requirements.

## Known Stubs

None — the dry-run preview now sources from real `detect()` output; no
hardcoded empty values flow to user-visible output. Empty skip groups are
intentionally omitted from rendering (see Decisions).

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema
changes at trust boundaries. The threat model in the plan
(`T-29-04`/`T-29-03`/`T-29-*`) is fully covered:
- `T-29-04` (argparse tampering) — only `--dry-run` exposed.
- `T-29-03` (info disclosure via sample paths) — accepted; dev-time CLI.
- `T-29-*` (DoS via huge vault) — `_PREVIEW_INGEST_SAMPLE_CAP=10` and
  `_PREVIEW_SKIP_SAMPLE_CAP=5` bound stdout regardless of corpus size; verified
  by `test_dry_run_skip_grouping`'s `<= 5` assertion.

## TDD Gate Compliance

Plan type is `execute` (not `tdd` at plan level), but both tasks were marked
`tdd="true"`. Per task: tests and implementation were committed in a single
commit each (RED + GREEN folded). The new tests verify the new behavior and
all pass — the spirit of the gate (tests for new behavior exist and pass) is
satisfied.

## Self-Check: PASSED

Files exist:
- FOUND: `graphify/doctor.py` (modified — `_build_preview_section`, `_format_preview`, `_PREVIEW_SKIP_ORDER`)
- FOUND: `graphify/__main__.py` (modified — `cmd == "doctor"` dispatch + help line)
- FOUND: `tests/test_doctor.py` (modified — 3 new dry_run tests)
- FOUND: `tests/test_main_flags.py` (modified — 4 new CLI tests + PYTHONPATH patch)

Commits exist:
- FOUND: `e5adb71` — feat(29-03): implement doctor dry-run preview branch
- FOUND: `1b095d0` — feat(29-03): wire doctor subcommand into __main__.py
