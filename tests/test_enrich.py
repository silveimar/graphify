"""Wave 0 scaffolds per 15-VALIDATION.md — must fail before Plan 01 Task 2 fills the module.

Unit tests for graphify/enrich.py lifecycle primitives:
  - CLI argparse wiring (enrich subcommand)
  - fcntl.flock single-writer coordination (ENRICH-04)
  - snapshot_id pinning at process start (ENRICH-05)
  - SIGTERM + signal.alarm(600) handlers (ENRICH-07)
"""
from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
from pathlib import Path

import pytest

# Skip all flock / signal tests on Windows — fcntl is POSIX-only.
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="fcntl not available on Windows")


# ---------------------------------------------------------------------------
# Test 1: CLI exits non-zero when graph.json is missing
# ---------------------------------------------------------------------------

def test_cli_missing_graph(tmp_path: Path) -> None:
    """graphify enrich with no existing graph.json exits non-zero with actionable stderr."""
    import subprocess

    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_path = out_dir / "graph.json"
    # graph.json intentionally NOT created

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "enrich", "--graph", str(graph_path)],
        cwd=str(tmp_path),
        timeout=30,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, (
        f"expected non-zero exit but got {result.returncode}; stderr={result.stderr!r}"
    )
    combined = (result.stderr + result.stdout).lower()
    assert "graph" in combined or "not found" in combined, (
        f"expected 'graph' or 'not found' in output; got stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: CLI help lists all 4 pass names
# ---------------------------------------------------------------------------

def test_cli_pass_choices(tmp_path: Path) -> None:
    """`graphify enrich --help` stdout contains all 4 pass names."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "graphify", "enrich", "--help"],
        cwd=str(tmp_path),
        timeout=30,
        capture_output=True,
        text=True,
    )

    combined = result.stdout + result.stderr
    for pass_name in ("description", "patterns", "community", "staleness"):
        assert pass_name in combined, (
            f"expected '{pass_name}' in enrich --help output; got:\n{combined}"
        )


# ---------------------------------------------------------------------------
# Test 3: flock contention — second exclusive acquire raises BlockingIOError
# ---------------------------------------------------------------------------

def test_flock_blocks_second_writer(enrich_out_dir: Path) -> None:
    """Acquiring the lock twice raises BlockingIOError on the second attempt."""
    lock_path = enrich_out_dir / ".enrichment.lock"
    fd1 = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd1, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd2 = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd2)
    finally:
        fcntl.flock(fd1, fcntl.LOCK_UN)
        os.close(fd1)


# ---------------------------------------------------------------------------
# Test 4: pin_snapshot returns the most-recent snapshot by mtime
# ---------------------------------------------------------------------------

def test_snapshot_pin_stem(tmp_path: Path) -> None:
    """pin_snapshot(project_root) returns (stem_of_latest, path_to_latest)."""
    from graphify.enrich import pin_snapshot

    snap_dir = tmp_path / "graphify-out" / "snapshots"
    snap_dir.mkdir(parents=True)

    # Write two snapshots; ensure the second has a later mtime
    older = snap_dir / "2026-04-20T14-30-00.json"
    older.write_text(
        json.dumps({"graph": {"nodes": [], "links": []}, "communities": {}, "meta": {}})
    )
    # Nudge mtime so sort order is deterministic even on fast filesystems
    import time; time.sleep(0.01)
    newer = snap_dir / "2026-04-20T15-00-00_delta.json"
    newer.write_text(
        json.dumps({"graph": {"nodes": [], "links": []}, "communities": {}, "meta": {}})
    )

    snapshot_id, snapshot_path = pin_snapshot(tmp_path)

    assert snapshot_path == newer, f"expected latest={newer}, got {snapshot_path}"
    assert snapshot_id == newer.stem, f"expected stem={newer.stem!r}, got {snapshot_id!r}"


# ---------------------------------------------------------------------------
# Test 5: SIGTERM handler releases flock so a new writer can acquire immediately
# ---------------------------------------------------------------------------

def test_sigterm_handler_releases_lock(enrich_out_dir: Path) -> None:
    """_sigterm_handler releases the flock; a fresh fd can then acquire LOCK_EX."""
    from graphify.enrich import _acquire_lock, _install_sigterm, _sigterm_handler

    lock_fd = _acquire_lock(enrich_out_dir)
    _install_sigterm(lock_fd, max_runtime_seconds=0)  # 0 = don't arm alarm

    with pytest.raises(SystemExit) as exc_info:
        _sigterm_handler(signal.SIGTERM, None)

    assert exc_info.value.code == 1, (
        f"expected sys.exit(1) but got code={exc_info.value.code}"
    )

    # After SIGTERM handler: verify the lock is released (new fd can acquire it)
    lock_path = enrich_out_dir / ".enrichment.lock"
    new_fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        # Should NOT raise — lock was released by handler
        fcntl.flock(new_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(new_fd, fcntl.LOCK_UN)
    finally:
        os.close(new_fd)

    # Verify alarm was cleared (itimer should be at 0 since max_runtime_seconds=0)
    # signal.alarm(0) has no effect with 0, but confirm alarm(0) was called in install
    # by confirming no SIGALRM fires; we just verify the test didn't hang.
