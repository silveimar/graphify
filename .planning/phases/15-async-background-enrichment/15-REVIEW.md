---
phase: 15-async-background-enrichment
reviewed: 2026-04-22T11:30:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - graphify/enrich.py
  - graphify/serve.py
  - graphify/__main__.py
  - graphify/watch.py
  - tests/test_enrich.py
  - tests/test_enrich_grep_guard.py
  - tests/test_enrich_invariant.py
  - tests/test_enrichment_lifecycle.py
  - tests/test_serve.py
  - tests/test_watch.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2026-04-22T11:30:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 15 introduces a non-trivial set of concurrency primitives (fcntl.flock, SIGTERM/SIGALRM handlers, subprocess.Popen with atexit cleanup, atomic tmp+rename, pid heartbeat) and a schema-versioned overlay merge path. On the whole the implementation is careful and closely tracks the design truths in the 15-0X-PLAN documents.

Key strengths:
- The SC-5 grep-CI guard enforces the structural invariant (only `build.py`, `__main__.py`, `watch.py` may call `to_json` / `_write_graph_json`) at test time.
- Alias redirection (D-16) is threaded through every write-side pass and every read-side overlay merge — I found no regression.
- Subprocess invocation in `watch.py` is argv-based (no shell), with controlled paths — no command-injection surface.
- Atomic writes (`.tmp` + `os.replace`) are used consistently, with `.tmp` unlink on exception.
- `yaml.safe_load` is used (T-10-04 compliance) in `_lookup_price_per_1k`.

The findings below are all correctness / robustness concerns; none are critical security vulnerabilities. The highest-severity concerns cluster around (a) stale `.enrichment.pid` files after SIGTERM, (b) a blind `os.kill(pid, SIGTERM)` in the foreground-rebuild path whose PID might be recycled, and (c) a file-descriptor leak window in `_foreground_acquire_enrichment_lock` under unexpected exceptions.

## Warnings

### WR-01: Stale `.enrichment.pid` after SIGTERM can cause foreground rebuild to SIGTERM an unrelated PID

**File:** `graphify/enrich.py:99-114` (handler), `graphify/__main__.py:1047-1059` (foreground SIGTERM)
**Issue:** The SIGTERM handler (`_sigterm_handler`) intentionally does **not** delete `.enrichment.pid` — the `run_enrichment` `finally` block handles pid cleanup, but `sys.exit(1)` inside the handler skips the `finally` of `run_enrichment` (confirmed by the test comment at `tests/test_enrichment_lifecycle.py:115-117` — "PID heartbeat should have been cleaned up ... NOTE: signal-handler sys.exit skips the try/finally cleanup"). The result is that `.enrichment.pid` persists after SIGTERM.

On the next foreground rebuild, `_foreground_acquire_enrichment_lock` (`__main__.py:1047-1059`) reads the stale pid and calls `_os.kill(pid, _signal.SIGTERM)`. On a long-running system, PIDs are recycled — that pid may now belong to an unrelated user/system process. While the foreground path only *reaches* the `os.kill` branch when `flock(LOCK_EX|LOCK_NB)` raises `BlockingIOError` (i.e., *some* process holds the lock), there is a time window where the lock has just been released by a dying enrichment process but the pid file has not yet been removed.

**Fix:** Clean up `.enrichment.pid` inside `_sigterm_handler` before `sys.exit` (async-signal safety is still OK for `os.unlink` in CPython), and/or validate the recorded pid before SIGTERM-ing by cross-checking `started_at` and process-start-time via `psutil` — or at minimum check `expires_at` in the heartbeat and refuse to SIGTERM when the heartbeat is already expired:

```python
def _sigterm_handler(signum: int, frame: object) -> None:
    global _lock_fd, _pid_file_path  # also set by _write_pid_file
    if _lock_fd is not None:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
    # Pitfall-4 extension: remove pid heartbeat so foreground rebuild does
    # not SIGTERM a recycled PID.
    if _pid_file_path is not None:
        try:
            os.unlink(_pid_file_path)
        except OSError:
            pass
    print("[graphify] enrichment: SIGTERM received ...", file=sys.stderr)
    sys.exit(1)
```

And in `_foreground_acquire_enrichment_lock`, before calling `os.kill`, validate the heartbeat is fresh (`expires_at` > now).

### WR-02: File-descriptor leak in `_foreground_acquire_enrichment_lock` on unexpected exceptions

**File:** `graphify/__main__.py:1037-1071`
**Issue:** `fd = _os.open(str(lock_path), ...)` is opened on line 1038. The immediately-following `_fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)` is wrapped in `try/except BlockingIOError`, but ONLY `BlockingIOError` is caught. Any other `OSError` (e.g., EINTR, permission error on a networked FS) bypasses the handler and propagates up with `fd` leaked. Likewise, if the subsequent `_json.loads` / `_os.kill` / polling loop raises anything unexpected, the fd leaks.

**Fix:** Wrap the acquire+polling logic in a `try/except` that closes `fd` on any failure, or use a helper that guarantees cleanup:

```python
fd = _os.open(str(lock_path), _os.O_RDWR | _os.O_CREAT, 0o644)
try:
    try:
        _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        pass
    # ... SIGTERM + polling ...
    _fcntl.flock(fd, _fcntl.LOCK_EX)
    return fd
except BaseException:
    try:
        _os.close(fd)
    finally:
        raise
```

### WR-03: `_run_passes` reaches outside `graphify/` internals by importing `graphify.serve._load_dedup_report`

**File:** `graphify/enrich.py:146` (and `tests/test_enrich.py:244`)
**Issue:** `_run_passes` performs `from graphify.serve import _load_dedup_report` at call time. This creates a reverse dependency: `serve.py` already imports from `enrich.py` (`_load_enrichment_overlay` calls `from graphify.enrich import _validate_enrichment_envelope` at `serve.py:150`). The two modules therefore have a bidirectional import graph mediated by function-scoped imports. This works today but is fragile: a future top-level import on either side will cause a circular-import failure.

**Fix:** Move `_load_dedup_report` to a neutral location (e.g., a new `graphify/dedup.py` or into `graphify/security.py` if it is treated as a small loader). Both `serve.py` and `enrich.py` then import from the neutral module, and the circular risk disappears.

### WR-04: Routing-skip set matches raw `source_file` strings with no normalization

**File:** `graphify/enrich.py:149-152`, `_load_routing_skip_set` at line 569-599
**Issue:** `_load_routing_skip_set` returns a `set[str]` of path strings read verbatim from `routing.json`. The caller then builds `routing_skip_nids = {nid for nid, d in G.nodes(data=True) if d.get("source_file") in routing_skip_files}`. If `routing.json` writes absolute paths while the graph stores relative paths (or vice versa), the intersection will be silently empty and no nodes get skipped. Because the failure mode is "no skip," this bug wastes LLM budget on files that were supposed to be excluded — not catastrophic, but invalidates the ENRICH-11 P2 guarantee without any warning.

**Fix:** Normalize both sides (e.g., `str(Path(p).resolve())` or relative-to-project-root) before intersection, or add an assert-level warning to stderr when `routing.json` is present but intersection is empty. At minimum, document the expected path form in `_load_routing_skip_set`'s docstring.

## Info

### IN-01: Heartbeat `expires_at` is written once and never refreshed

**File:** `graphify/enrich.py:406-432`
**Issue:** `_write_pid_file` sets `expires_at = now + 600s` at process start. For a run that exits normally well before 600s, the heartbeat is deleted in the finally block — fine. But the field is never refreshed mid-run; a pass that takes 400s followed by one that takes 250s will have `expires_at` already in the past when the second pass starts. Any external consumer reading the heartbeat (e.g., a future monitoring tool) would mistakenly mark the process as "expired." Currently nothing reads `expires_at`, but per CLAUDE.md conventions (schema fields should mean what they say), either drop the field or arrange for it to be updated at pass boundaries.

**Fix:** Either remove the `expires_at` field (not consumed anywhere) or call `_write_pid_file` again at each `_commit_pass` boundary.

### IN-02: `_validate_enrichment_envelope` does not validate that `staleness` keys are strings

**File:** `graphify/enrich.py:502-510`
**Issue:** Iterates `stal.items()` and checks `label` against the enum, but accepts non-string keys silently. An envelope with `{42: "FRESH"}` would pass validation and later break on `G.nodes[canonical]` lookup where `canonical` is an int.

**Fix:** Add `isinstance(_nid, str)` to the iteration check:
```python
for _nid, label in stal.items():
    if not isinstance(_nid, str) or label not in valid_labels:
        return False
```

### IN-03: `_estimate_pass_cost` passes `Path(".")` as out_dir during dry-run

**File:** `graphify/enrich.py:858-894`
**Issue:** The dry-run cost estimator calls the production pass functions with `out_dir = Path(".")`. Today none of the passes read from `out_dir` when `dry_run=True`, so this is inert. But if a future pass reads e.g. a cache file during dry-run, it will silently read from CWD instead of the real graphify-out directory — a brittle contract.

**Fix:** Pass the real `out_dir` through from the caller (`run_enrichment`):
```python
# in run_enrichment, before _emit_dry_run_envelope:
per_pass[pass_name] = _estimate_pass_cost(
    pass_name, G_loaded, communities_loaded,
    budget_cap=budget,
    out_dir=out_dir,  # propagate
)
```

### IN-04: Possible data race on `changed` set between watchdog thread and main loop

**File:** `graphify/watch.py:207-220, 242-247`
**Issue:** `Handler.on_any_event` runs on the watchdog observer thread and mutates the outer `changed: set[Path]`, `pending: bool`, and `last_trigger: float` captured via closure. The main loop reads them without synchronization. In CPython, `set.add`, attribute assignment, and reading are atomic at the bytecode level thanks to the GIL, but `list(changed); changed.clear()` is a two-step sequence that can drop paths added between the two calls. Worst case: one file-change event is missed and deferred to the next rebuild — low severity, but worth flagging.

**Fix:** Protect the set with a `threading.Lock()` or use a `queue.Queue()` instead:
```python
with _lock:
    batch = list(changed)
    changed.clear()
```

### IN-05: `_sigterm_handler` does not call `signal.alarm(0)` before `sys.exit`

**File:** `graphify/enrich.py:99-114`
**Issue:** If SIGTERM arrives while SIGALRM is armed, the handler exits without cancelling the alarm. Python's interpreter shutdown will unwind anyway so this is harmless in practice, but explicit `signal.alarm(0)` at handler entry is idiomatic defensive code.

**Fix:** Add `signal.alarm(0)` as the first statement in `_sigterm_handler`.

### IN-06: `_commit_pass` discards an unreadable existing envelope silently

**File:** `graphify/enrich.py:449-458`
**Issue:** If `enrichment.json` exists but fails to parse (`OSError` or `JSONDecodeError`), `_commit_pass` silently replaces it with a fresh envelope. The prior (corrupt) envelope is not backed up and there is no stderr warning. Compare with `_load_existing_enrichment` (line 531-535), which *does* print a stderr warning in the same situation — the two code paths should be consistent.

**Fix:** Emit the same stderr warning from `_commit_pass`:
```python
except (OSError, json.JSONDecodeError) as exc:
    print(
        f"[graphify] enrichment: existing enrichment.json unreadable ({exc}); "
        f"overwriting with fresh envelope",
        file=sys.stderr,
    )
    existing = None
```

### IN-07: Tests accept vagueness about `.enrichment.pid` lifecycle

**File:** `tests/test_enrichment_lifecycle.py:114-117`
**Issue:** The `test_sigterm_abort` test explicitly documents in a comment that pid cleanup after SIGTERM is not verified ("signal-handler sys.exit skips the try/finally cleanup in run_enrichment — so .enrichment.pid may persist after SIGTERM"). This is the symptom of the WR-01 bug and the test codifies the buggy behavior rather than asserting the desired invariant. Once WR-01 is fixed, this test should be tightened to assert `not (out_dir / ".enrichment.pid").exists()` after SIGTERM.

**Fix:** After WR-01's fix, change the NOTE comment block into a positive assertion:
```python
assert not (out_dir / ".enrichment.pid").exists(), (
    "SIGTERM handler must clean up pid heartbeat (see WR-01)"
)
```

---

_Reviewed: 2026-04-22T11:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
