---
plan: 15-01
phase: 15
wave: 1
status: complete
completed: 2026-04-22
commits:
  - ad67230  # Task 1: Wave-0 TDD scaffolds
  - 7e11fac  # Task 2: enrich.py lifecycle scaffold
  - 56f897d  # Task 3: CLI wiring + read-only FS fix
req_ids: [ENRICH-04, ENRICH-05, ENRICH-07]
---

# Plan 15-01 — Summary

Bootstrap of the Phase 15 async background enrichment subsystem. Landed the
`graphify/enrich.py` module, the `graphify enrich` CLI subcommand, and the three
safety-critical lifecycle primitives required by every downstream plan in the phase.

## What shipped

**`graphify/enrich.py`** — lifecycle scaffold with:
- `fcntl.flock(LOCK_EX | LOCK_NB)` single-writer coordination → exit 3 on contention (ENRICH-04)
- `snapshot_id` pinning at process start, before lock acquisition (ENRICH-05)
- `SIGTERM` + `signal.alarm(600)` watchdog with guaranteed lock release in `finally` (ENRICH-07)
- `_write_pid_file` atomic heartbeat (Pitfall 4 zombie mitigation)
- Early `graph.json` existence gate — missing graph exits 2 with actionable stderr (ENRICH-01)
- `_run_passes()` placeholder — Plans 02/03 fill in the four passes

**`graphify/__main__.py`** — `enrich` subcommand wired into the existing manual
`sys.argv` dispatch with inline `argparse.ArgumentParser`, matching the convention
used by `run`/`query`/`watch`/`capability`. CLI contract:

```
graphify enrich [--graph PATH] [--budget N] [--pass NAME]... [--dry-run] [--snapshot-id ID]
```

Error mapping:
- `BlockingIOError` (another enrichment running) → exit 3
- `OSError` (FS / permission failure) → exit 2 with actionable stderr
- `SystemExit(2)` from `run_enrichment` guards propagates untouched
- Normal completion → exit 0 (or 1 if `result.aborted`)

**`tests/test_enrich.py`** — 5 Wave-0 scaffold tests covering:
- Snapshot pinning happens before lock acquisition
- Lock is released on SIGTERM (fork + signal harness)
- Watchdog alarm fires at 600s
- CLI `--help` advertises all four pass names
- Missing graph.json exits 2

## Bugs fixed mid-implementation

1. **Unhandled `OSError` on read-only filesystem before `graph.json` check.**
   `out_dir.mkdir(parents=True, exist_ok=True)` ran before the existence gate,
   so unwritable parents leaked `PermissionError`. Reordered so the existence
   check fires first; mkdir is now a guaranteed no-op on the happy path and the
   silent `except OSError: pass` hack was removed.

2. **No top-level FS/permission error channel in the CLI branch.**
   Added `except OSError` around `run_enrichment` → exit 2 with actionable
   stderr. Belt-and-suspenders defense against edge cases (broken symlinks,
   path-too-long, etc.) that bypass `run_enrichment`'s own guards.

## Plan amendment

`15-01-PLAN.md` Task 3 `<acceptance_criteria>` was written assuming a
subparsers-based CLI (`sub.add_parser("enrich")` / `args.cmd`). `__main__.py`
actually uses `cmd = sys.argv[1]` manual dispatch with inline argparse per
complex subcommand. Grep criteria amended to match the codebase convention
(`elif cmd == "enrich"`, `prog="graphify enrich"`); behavioral criteria are
unchanged. Rationale preserved inline in the PLAN.md.

## Acceptance criteria — all green

| # | Check | Status |
|---|-------|--------|
| 1 | `grep -q 'elif cmd == "enrich"' graphify/__main__.py` | PASS |
| 2 | `grep -q 'from graphify.enrich import run_enrichment' graphify/__main__.py` | PASS |
| 3 | `grep -q 'prog="graphify enrich"' graphify/__main__.py` | PASS |
| 4 | `python -m graphify enrich --help` lists all 4 pass names | PASS |
| 5 | `python -m graphify enrich --graph /nonexistent/graph.json` exits 2 | PASS |
| 6 | `pytest tests/test_enrich.py -q` (5 Wave-0 tests) | PASS |
| 7 | `pytest tests/test_main_cli.py -q` (no regression) | PASS |

26 tests, 0 failures.

## Downstream handoff

- `run_enrichment()` signature is frozen for Plans 02/03. The `finally:` lock
  release pattern MUST NOT be modified.
- Plans 02/03 fill `_run_passes()` with the four LLM-driven passes
  (description / patterns / community / staleness) and the `_commit_pass`
  atomic writer. D-01 pass order and D-03 priority-drain budget allocation
  are decided; implementation is Plan 02.
- `SIGTERM` + `SIGALRM` handlers and `.enrichment.pid` heartbeat are load-bearing
  for Plan 05 (foreground/background lock coordination).
