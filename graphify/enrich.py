"""Async background graph enrichment — 4 passes (description, patterns, community, staleness).

Writes overlay sidecar only (``graphify-out/enrichment.json``); ``graph.json`` is NEVER mutated.
See .planning/phases/15-async-background-enrichment/15-CONTEXT.md §<decisions> for D-01..D-07.

ENRICH-04: single-writer fcntl.flock coordination
ENRICH-05: snapshot_id pinned at process start, never followed mid-run
ENRICH-07: SIGTERM + signal.alarm(600) handlers for clean abort
"""
from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graphify.security import validate_graph_path
from graphify.snapshot import list_snapshots

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

LOCK_FILENAME = ".enrichment.lock"
PID_FILENAME = ".enrichment.pid"
PASS_NAMES: tuple[str, ...] = ("description", "patterns", "community", "staleness")
DEFAULT_MAX_RUNTIME_SECONDS = 600  # Pitfall 4 mitigation — SIGALRM after 10 min

# Module-level fd used by the SIGTERM handler (set inside run_enrichment; read in handler).
_lock_fd: int | None = None


# ---------------------------------------------------------------------------
# Public result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentResult:
    """Aggregated outcome of one enrichment run (all passes)."""

    snapshot_id: str
    passes_run: list[str] = field(default_factory=list)
    passes_skipped: list[str] = field(default_factory=list)
    passes_failed: list[str] = field(default_factory=list)
    tokens_used: int = 0
    llm_calls: int = 0
    dry_run: bool = False
    aborted: bool = False  # True if SIGTERM received mid-run


# ---------------------------------------------------------------------------
# Snapshot pinning (ENRICH-05)
# ---------------------------------------------------------------------------

def pin_snapshot(project_root: Path) -> tuple[str, Path]:
    """Return (snapshot_id, snapshot_path) for the most recent snapshot.

    snapshot_id = snapshot_path.stem (e.g. '2026-04-20T14-30-00').
    Raises FileNotFoundError if no snapshots exist yet.
    """
    snapshots = list_snapshots(project_root)
    if not snapshots:
        raise FileNotFoundError(
            "no snapshots found under graphify-out/snapshots/; run `graphify run` first"
        )
    latest = snapshots[-1]  # list_snapshots returns oldest → newest (mtime sort)
    return latest.stem, latest


# ---------------------------------------------------------------------------
# Lock acquisition (ENRICH-04)
# ---------------------------------------------------------------------------

def _acquire_lock(out_dir: Path) -> int:
    """Acquire exclusive flock on .enrichment.lock. Returns fd.

    Raises BlockingIOError if another enrichment process is active.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    lock_path = out_dir / LOCK_FILENAME
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise
    return fd


# ---------------------------------------------------------------------------
# SIGTERM / SIGALRM handler (ENRICH-07)
# ---------------------------------------------------------------------------

def _sigterm_handler(signum: int, frame: object) -> None:
    """SIGTERM / SIGALRM handler: release flock, print notice, sys.exit(1).

    Pitfall 2 guard: release the lock with LOCK_UN but do NOT close the fd
    inside the signal handler — closing inside a handler can cause double-close
    races. The OS cleans up the fd on process exit.
    """
    global _lock_fd
    if _lock_fd is not None:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
    print(
        "[graphify] enrichment: SIGTERM received; releasing lock and exiting cleanly",
        file=sys.stderr,
    )
    sys.exit(1)


def _install_sigterm(
    lock_fd: int,
    max_runtime_seconds: int = DEFAULT_MAX_RUNTIME_SECONDS,
) -> None:
    """Register SIGTERM (and SIGALRM) handlers and arm signal.alarm(max_runtime_seconds).

    Stores lock_fd in the module-level _lock_fd so the handler can release it.
    SIGALRM also triggers _sigterm_handler for Pitfall 4 zombie mitigation.
    max_runtime_seconds=0 skips arming the alarm (used in tests).
    """
    global _lock_fd
    _lock_fd = lock_fd
    signal.signal(signal.SIGTERM, _sigterm_handler)
    signal.signal(signal.SIGALRM, _sigterm_handler)  # alarm also triggers clean abort
    if max_runtime_seconds > 0:
        signal.alarm(max_runtime_seconds)


# ---------------------------------------------------------------------------
# Pass orchestrator stub (Plans 02/03 will populate)
# ---------------------------------------------------------------------------

def _run_passes(
    out_dir: Path,
    snapshot_id: str,
    snapshot_path: Path,
    passes: list[str],
    *,
    budget: int | None,
    dry_run: bool,
    resume: bool,
    result: EnrichmentResult,
) -> None:
    """Placeholder pass dispatcher — Plans 02 and 03 will replace this body.

    Plan 01 implementation: log the no-op and append all requested passes to
    result.passes_skipped. No LLM calls, no file writes (other than heartbeat).
    This function is the single extension point for downstream plans.
    """
    print(
        "[graphify] enrichment: placeholder _run_passes — Plans 02/03 will populate",
        file=sys.stderr,
    )
    result.passes_skipped.extend(passes)


# ---------------------------------------------------------------------------
# Public orchestrator (ENRICH-01, ENRICH-04, ENRICH-05, ENRICH-07)
# ---------------------------------------------------------------------------

def run_enrichment(
    out_dir: Path,
    *,
    budget: int | None = None,
    passes: list[str] | None = None,
    dry_run: bool = False,
    resume: bool = True,
    snapshot_id_override: str | None = None,
    project_root: Path | None = None,
) -> EnrichmentResult:
    """Acquire lock, pin snapshot, install SIGTERM handler, then run the pass orchestrator.

    Plan 01 skeleton: calls an internal _run_passes() placeholder that returns an empty
    EnrichmentResult. Plans 02 and 03 will fill in the four passes. The lock / snapshot /
    signal plumbing in this function is frozen after Plan 01 — later plans MUST NOT modify
    the finally: block release pattern.

    Args:
        out_dir: graphify-out/ directory (contains graph.json + enrichment.json sidecar).
        budget: token cap applied in D-03 priority-drain order (description → patterns → community).
        passes: list of pass names to run; None → all 4 in PASS_NAMES order.
        dry_run: if True, preview tokens/calls without LLM invocations (ENRICH-10 P2).
        resume: if True, skip already-complete passes from prior runs (Plans 02/03 fill this).
        snapshot_id_override: pin to a specific snapshot_id instead of latest.
        project_root: root containing graphify-out/; inferred from out_dir.parent if None.
    """
    global _lock_fd

    project_root = project_root or out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Guard: graph.json must exist (ENRICH-01)
    graph_path = out_dir / "graph.json"
    if not graph_path.exists():
        print(
            f"[graphify] enrichment: {graph_path} not found — run `graphify run` first",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # Pin snapshot (ENRICH-05) — done BEFORE acquiring the lock so failures are fast
    if snapshot_id_override:
        snapshot_id = snapshot_id_override
        snapshot_path = next(
            (p for p in list_snapshots(project_root) if p.stem == snapshot_id),
            None,
        )
        if snapshot_path is None:
            raise SystemExit(
                f"snapshot_id {snapshot_id!r} not found under "
                f"{project_root}/graphify-out/snapshots/"
            )
    else:
        snapshot_id, snapshot_path = pin_snapshot(project_root)

    # Acquire exclusive lock (ENRICH-04)
    lock_fd = _acquire_lock(out_dir)

    # Store fd so SIGTERM handler can release it
    _lock_fd = lock_fd

    # Install SIGTERM + SIGALRM handlers and arm watchdog alarm (ENRICH-07 / Pitfall 4)
    _install_sigterm(lock_fd, DEFAULT_MAX_RUNTIME_SECONDS)

    # Write heartbeat .pid file atomically (Pitfall 4 zombie mitigation)
    _write_pid_file(out_dir, snapshot_id)

    result = EnrichmentResult(snapshot_id=snapshot_id, dry_run=dry_run)

    try:
        _run_passes(
            out_dir,
            snapshot_id,
            snapshot_path,
            passes or list(PASS_NAMES),
            budget=budget,
            dry_run=dry_run,
            resume=resume,
            result=result,
        )
    finally:
        # Always cancel the watchdog alarm on normal exit (Pitfall 4)
        signal.alarm(0)
        # Release and close the lock
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
            _lock_fd = None
        # Remove heartbeat .pid file (Pitfall 4 cleanup)
        try:
            (out_dir / PID_FILENAME).unlink(missing_ok=True)
        except OSError:
            pass

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_pid_file(out_dir: Path, snapshot_id: str) -> None:
    """Write .enrichment.pid heartbeat atomically (Pitfall 4 mitigation).

    Uses the routing_audit.py atomic pattern: write to .tmp then os.replace.
    Validates out_dir base confinement only (the pid file doesn't exist yet,
    so validate_graph_path on the exact path would raise FileNotFoundError).
    """
    # Validate the base directory (not the file — it doesn't exist yet)
    validate_graph_path(out_dir, base=out_dir.parent)

    now = datetime.now(timezone.utc)
    from datetime import timedelta
    expires = now + timedelta(seconds=DEFAULT_MAX_RUNTIME_SECONDS)

    payload: dict[str, Any] = {
        "pid": os.getpid(),
        "started_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "snapshot_id": snapshot_id,
    }

    dest = out_dir / PID_FILENAME
    tmp = dest.with_suffix(".pid.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
