---
phase: 15-async-background-enrichment
plan: 05
subsystem: cli/watch
tags: [foreground-lock, watch, event-driven, sigterm, fcntl, atexit, enrich-subprocess]
requires:
  - 15-01   # LOCK_FILENAME / PID_FILENAME + SIGTERM handler (enrich.py)
  - 15-02   # atomic-commit primitives (enrichment.json)
  - 15-03   # resume semantics (enrichment.json)
provides:
  - foreground-lock protocol (ENRICH-07)
  - opt-in watch --enrich trigger (ENRICH-06)
  - Pitfall 4 zombie mitigation (atexit + running-child guard)
affects:
  - graphify/__main__.py
  - graphify/watch.py
tech-stack:
  added:
    - Python stdlib: atexit, subprocess, signal (already in-use elsewhere)
  patterns:
    - fcntl.flock(LOCK_EX|LOCK_NB) poll loop + bounded timeout fallback
    - subprocess.Popen with start_new_session=False so atexit SIGTERM propagates
key-files:
  created: []
  modified:
    - graphify/__main__.py         # helpers + run wrap + watch subcommand
    - graphify/watch.py            # _maybe_trigger_enrichment + _cleanup_on_exit + atexit
    - tests/test_enrich.py         # +2 foreground-lock tests
    - tests/test_watch.py          # +2 opt-in trigger / atexit tests
decisions:
  - Foreground always wins — no retry/backoff on the foreground side
  - Watch --enrich is strictly opt-in (no auto-spawn on default path)
  - Running-child guard suppresses duplicate spawns during rebuild bursts
metrics:
  duration_minutes: 15
  tasks_completed: 2
  completed: "2026-04-22"
---

# Phase 15 Plan 05: Foreground-Lock Contention & Watch Event Trigger Summary

Closed the foreground/background lock-coordination loop between `graphify run`
and `graphify enrich`: foreground always wins via SIGTERM-plus-block-on-LOCK_EX,
and `graphify watch` gains an opt-in `--enrich` flag that spawns enrichment
after each rebuild with an `atexit` handler that kills any child on shutdown.

## Foreground-Lock Protocol

```
graphify run                            graphify enrich (Plan 01-03)
     │                                           │
     ▼                                           ▼
 _foreground_acquire_               _acquire_lock() holds
 _enrichment_lock(out_dir)          .enrichment.lock (LOCK_EX)
     │                                   +
     │  try LOCK_EX|LOCK_NB              .enrichment.pid written
     │
     │  BlockingIOError?
     │  ├─ read .enrichment.pid
     │  ├─ os.kill(pid, SIGTERM) ───────► SIGTERM handler (enrich.py):
     │  │                                    - flock(LOCK_UN)
     │  │                                    - purge .enrichment.pid
     │  │                                    - sys.exit(1)
     │  └─ poll LOCK_EX|LOCK_NB (100ms)
     │
     ▼
 fd acquired; run_corpus()
     │
     ▼
 finally: flock(LOCK_UN) + os.close(fd)
```

Lock is held across the full `run_corpus()` body (D-01 single-writer semantics).
Timeout escape: if the enrichment handler stalls past 30s, foreground force-blocks
on `LOCK_EX` (still bounded by outer shell timeout).

## Watch Opt-In Enrichment Trigger (ENRICH-06)

`graphify watch --enrich` is the *only* path that spawns enrichment. Default
`graphify watch` remains byte-identical to its prior behaviour. Per rebuild:

1. `_rebuild_code(watch_path)` succeeds
2. `_maybe_trigger_enrichment(watch_path / "graphify-out", enrich)` is called
3. If `enrich=False` → no-op
4. If `enrich=True` and no prior child is running:
   - `subprocess.Popen([sys.executable, "-m", "graphify", "enrich", "--graph", ...])`
   - `start_new_session=False` keeps the child in the watcher's process group
     so the `atexit` handler can signal it reliably
5. If `enrich=True` and a prior child is still alive (`poll() is None`):
   - Skip — no process cascade (Pitfall 4 guard)

## Pitfall 4 Mitigation Surface

Three layered defences against zombie enrichment processes:

| Layer | Mechanism | Location |
|-------|-----------|----------|
| 1. No auto-spawn | `--enrich` defaults False | argparse in `__main__.py` |
| 2. Running-child guard | `poll() is None` check before Popen | `watch._maybe_trigger_enrichment` |
| 3. Shutdown cleanup | `atexit.register(_cleanup_on_exit)` → SIGTERM (5s grace) then SIGKILL | `watch._cleanup_on_exit` |

`_cleanup_on_exit` fires on normal exit, `KeyboardInterrupt`, and shell-close.

## Files Modified

- `graphify/__main__.py`:
  - `+_foreground_acquire_enrichment_lock(out_dir, timeout_seconds=30.0)` — LOCK_EX-or-SIGTERM acquisition
  - `+_foreground_release_enrichment_lock(fd)` — None-safe unlock+close
  - `cmd == "run"`: wrapped body in `try/finally` around `run_corpus` with lock acquire/release
  - `cmd == "watch"`: new inline-argparse subcommand (`path`, `--debounce`, `--enrich`) delegating to `graphify.watch.watch`
- `graphify/watch.py`:
  - `+_active_enrichment_child` module-level handle
  - `+_cleanup_on_exit()` atexit handler (SIGTERM + 5s grace + SIGKILL)
  - `+atexit.register(_cleanup_on_exit)` at import time
  - `+_maybe_trigger_enrichment(out_dir, enabled)` — opt-in Popen trigger with running-child guard
  - `watch()` signature: new keyword-only `enrich: bool = False`; rebuild loop calls `_maybe_trigger_enrichment` after successful `_rebuild_code`
  - standalone `__main__` argparse: `+--enrich` flag
- `tests/test_enrich.py`:
  - `+test_foreground_acquire_returns_none_when_out_dir_missing`
  - `+test_foreground_lock_preempts_enrichment` — integration: spawns a helper child holding the lock, asserts foreground SIGTERMs it and acquires within 5s
- `tests/test_watch.py`:
  - `+test_enrichment_trigger_opt_in`
  - `+test_watch_atexit_terminates_child`

## Commits

| Task | Commit  | Message |
|------|---------|---------|
| 1 RED | 5863633 | test(15-05): add failing tests for foreground-lock preemption |
| 1 GRN | 4a5326d | feat(15-05): foreground-lock wrap around graphify run (ENRICH-07) |
| 2 RED | 3f8f1e0 | test(15-05): add failing tests for watch opt-in --enrich trigger |
| 2 GRN | 967c269 | feat(15-05): opt-in watch --enrich trigger + atexit cleanup (ENRICH-06) |

## Verification

- `pytest tests/test_enrich.py tests/test_watch.py -q` → 30 passed
- `pytest tests/ -q` → **1356 passed** (0 regressions)
- `python -m graphify watch --help 2>&1 | grep -- "--enrich"` → hits
- Acceptance greps (all exit 0):
  - `fcntl.flock`, `SIGTERM`, `os.kill`, `_foreground_acquire_enrichment_lock(out_dir` in `__main__.py`
  - `p_watch.add_argument("--enrich"` in `__main__.py`
  - `def _maybe_trigger_enrichment`, `def _cleanup_on_exit`, `atexit.register`, `subprocess.Popen`, `"enrich"` in `watch.py`

## TDD Gate Compliance

Both tasks followed RED → GREEN cleanly:
- Task 1: `5863633` (test) precedes `4a5326d` (feat)
- Task 2: `3f8f1e0` (test) precedes `967c269` (feat)

## Deviations from Plan

None — plan executed exactly as written. One minor addition not strictly
specified by the plan text but required by an acceptance-grep (`p_watch.add_argument("--enrich"`):
a `cmd == "watch"` subcommand dispatch block was added to `__main__.py` since
none existed previously (Plan assumed one was there). This is a Rule 2 fix
(missing critical infrastructure required to satisfy plan acceptance greps
and honor the plan's intent that `graphify watch` be the canonical entry point
for the opt-in `--enrich` flag).

## Open Items for Plan 06

- Dry-run envelope + byte-equality invariant test (ENRICH-10)
- Grep-CI whitelist test: `enrichment.json` written only by `enrich.py`
- End-to-end stress test: foreground `run` during active enrichment, confirm
  clean `graph.json` + no `enrichment.json.tmp` orphan (T-15-01 validation)

## Self-Check: PASSED

- File `graphify/__main__.py`: FOUND (contains `_foreground_acquire_enrichment_lock`, `_foreground_release_enrichment_lock`, `cmd == "watch"`, `cmd == "run"` wrap)
- File `graphify/watch.py`: FOUND (contains `_maybe_trigger_enrichment`, `_cleanup_on_exit`, `atexit.register`)
- File `tests/test_enrich.py`: FOUND (2 new tests)
- File `tests/test_watch.py`: FOUND (2 new tests)
- File `.planning/phases/15-async-background-enrichment/15-05-SUMMARY.md`: this file
- Commit `5863633`: FOUND
- Commit `4a5326d`: FOUND
- Commit `3f8f1e0`: FOUND
- Commit `967c269`: FOUND
