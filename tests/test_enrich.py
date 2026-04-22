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


# ===========================================================================
# Plan 15-02 tests — description/patterns/community passes + atomic commit
# ===========================================================================

def _write_min_graph_json(out_dir: Path) -> None:
    """Write a minimal graph.json so run_enrichment's existence guard passes."""
    (out_dir / "graph.json").write_text(
        json.dumps({"graph": {"nodes": [], "links": []}, "communities": {}})
    )


def _make_graph(nodes: list[tuple[str, dict]], edges: list[tuple[str, str, dict]] | None = None):
    """Build a small nx.Graph from (id, attrs) tuples."""
    import networkx as nx
    G = nx.Graph()
    for nid, attrs in nodes:
        G.add_node(nid, **attrs)
    for u, v, attrs in edges or []:
        G.add_edge(u, v, **attrs)
    return G


# ---------------------------------------------------------------------------
# Test: description pass respects budget (D-03 priority drain)
# ---------------------------------------------------------------------------

def test_description_pass_respects_budget(enrich_out_dir: Path, monkeypatch) -> None:
    """_run_description_pass stops once budget_remaining is exhausted."""
    from graphify.enrich import _run_description_pass

    G = _make_graph([
        (f"n{i}", {"label": f"N{i}", "source_file": f"f{i}.py", "file_type": "code"})
        for i in range(10)
    ])

    def fake_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        return ("enriched description", 30)
    monkeypatch.setattr("graphify.enrich._call_llm", fake_llm)

    result, tokens_used, llm_calls = _run_description_pass(
        G, enrich_out_dir, "snap-x",
        budget_remaining=100, dry_run=False,
        alias_map={}, routing_skip=set(),
    )
    # 100 tokens / 30 per call -> at most 4 calls before budget exhausts
    assert llm_calls <= 4, f"expected ≤4 calls on budget=100, got {llm_calls}"
    assert len(result) <= 4
    assert tokens_used <= 100 + 30  # allow one overshoot (call happens before next check)
    assert all(v == "enriched description" for v in result.values())


# ---------------------------------------------------------------------------
# Test: passes run serially in D-01 order
# ---------------------------------------------------------------------------

def test_patterns_pass_serial_after_description(enrich_out_dir: Path, monkeypatch) -> None:
    """_run_passes invokes description → patterns → community in that exact order."""
    import graphify.enrich as enrich_mod
    from graphify.enrich import EnrichmentResult

    _write_min_graph_json(enrich_out_dir)

    calls: list[str] = []

    def fake_desc(*a, **kw):
        calls.append("description")
        return {}, 0, 0
    def fake_patterns(*a, **kw):
        calls.append("patterns")
        return [], 0, 0
    def fake_community(*a, **kw):
        calls.append("community")
        return {}, 0, 0

    monkeypatch.setattr(enrich_mod, "_run_description_pass", fake_desc)
    monkeypatch.setattr(enrich_mod, "_run_patterns_pass", fake_patterns)
    monkeypatch.setattr(enrich_mod, "_run_community_pass", fake_community)

    # Patch load_snapshot + _load_dedup_report + _commit_pass (tested separately)
    import networkx as nx
    monkeypatch.setattr("graphify.snapshot.load_snapshot",
                        lambda p: (nx.Graph(), {}, {}))
    monkeypatch.setattr("graphify.serve._load_dedup_report", lambda od: {})
    monkeypatch.setattr(enrich_mod, "_commit_pass", lambda *a, **kw: None)

    result = EnrichmentResult(snapshot_id="snap-x")
    enrich_mod._run_passes(
        enrich_out_dir, "snap-x", enrich_out_dir / "snapshots" / "2026-04-20T14-30-00.json",
        ["description", "patterns", "community"],
        budget=None, dry_run=False, resume=False, result=result,
    )
    assert calls == ["description", "patterns", "community"], (
        f"expected D-01 serial order, got {calls}"
    )


# ---------------------------------------------------------------------------
# Test: community pass keys by str(community_id)
# ---------------------------------------------------------------------------

def test_community_pass_per_community_summary(enrich_out_dir: Path, monkeypatch) -> None:
    """_run_community_pass returns dict with string community_id keys."""
    from graphify.enrich import _run_community_pass

    G = _make_graph([
        ("n0", {"label": "N0", "source_file": "f0.py", "file_type": "code"}),
        ("n1", {"label": "N1", "source_file": "f1.py", "file_type": "code"}),
        ("n2", {"label": "N2", "source_file": "f2.py", "file_type": "code"}),
        ("n3", {"label": "N3", "source_file": "f3.py", "file_type": "code"}),
    ])
    communities = {0: ["n0", "n1"], 1: ["n2", "n3"]}

    def fake_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        return ("community summary", 20)
    monkeypatch.setattr("graphify.enrich._call_llm", fake_llm)

    result, tokens, calls = _run_community_pass(
        G, communities, enrich_out_dir, "snap-x",
        budget_remaining=1000, dry_run=False, alias_map={},
    )
    assert set(result.keys()) == {"0", "1"}, (
        f"expected string community_id keys, got {list(result.keys())}"
    )
    for v in result.values():
        assert isinstance(v, str) and len(v) > 0


# ---------------------------------------------------------------------------
# Test: alias redirect (D-16) — writes keyed by canonical node_id only
# ---------------------------------------------------------------------------

def test_enrichment_key_alias_canonical(enrich_out_dir: Path, monkeypatch) -> None:
    """Description pass emits keys resolved through alias_map → only canonical ids."""
    from graphify.enrich import _run_description_pass

    G = _make_graph([
        ("alias_old_id", {"label": "Old", "source_file": "a.py", "file_type": "code"}),
        ("other_id", {"label": "Other", "source_file": "b.py", "file_type": "code"}),
    ])
    alias_map = {"alias_old_id": "canonical_new_id"}

    def fake_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        return ("text", 10)
    monkeypatch.setattr("graphify.enrich._call_llm", fake_llm)

    result, _, _ = _run_description_pass(
        G, enrich_out_dir, "snap-x",
        budget_remaining=1000, dry_run=False,
        alias_map=alias_map, routing_skip=set(),
    )
    assert "canonical_new_id" in result, f"missing canonical id in {list(result.keys())}"
    assert "alias_old_id" not in result, (
        f"eliminated alias_old_id must NOT appear in result, got {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test: ENRICH-11 P2 routing skip — complex-tier files skipped
# ---------------------------------------------------------------------------

def test_description_skip_routing_complex(enrich_out_dir: Path, monkeypatch) -> None:
    """Nodes whose source_file is routed 'complex' are skipped."""
    from graphify.enrich import _run_description_pass, _load_routing_skip_set

    # Write routing.json tagging fileA.py as complex
    (enrich_out_dir / "routing.json").write_text(json.dumps({
        "version": 1,
        "files": {
            "fileA.py": {"class": "complex", "info": {"class": "complex"}},
            "fileB.py": {"class": "simple", "info": {"class": "simple"}},
        },
    }))

    G = _make_graph([
        ("A1", {"label": "A1", "source_file": "fileA.py", "file_type": "code"}),
        ("A2", {"label": "A2", "source_file": "fileA.py", "file_type": "code"}),
        ("B1", {"label": "B1", "source_file": "fileB.py", "file_type": "code"}),
    ])
    skip_files = _load_routing_skip_set(enrich_out_dir)
    assert "fileA.py" in skip_files
    routing_skip_nids = {nid for nid, d in G.nodes(data=True)
                          if d.get("source_file") in skip_files}
    assert routing_skip_nids == {"A1", "A2"}

    def fake_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        return ("ok", 10)
    monkeypatch.setattr("graphify.enrich._call_llm", fake_llm)

    result, _, _ = _run_description_pass(
        G, enrich_out_dir, "snap-x",
        budget_remaining=1000, dry_run=False,
        alias_map={}, routing_skip=routing_skip_nids,
    )
    assert list(result.keys()) == ["B1"], (
        f"only B1 should be enriched (A1, A2 skipped); got {list(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test: per-pass atomic commit with rollback-on-failure
# ---------------------------------------------------------------------------

def test_per_pass_atomic_commit(enrich_out_dir: Path, monkeypatch) -> None:
    """_commit_pass merges atomically; mid-write failure preserves prior passes."""
    from graphify.enrich import _commit_pass

    _commit_pass(enrich_out_dir, "snap-x", "description", {"n0": "desc0"})
    data = json.loads((enrich_out_dir / "enrichment.json").read_text())
    assert list(data["passes"].keys()) == ["description"]
    assert data["passes"]["description"] == {"n0": "desc0"}
    assert data["version"] == 1
    assert data["snapshot_id"] == "snap-x"

    _commit_pass(enrich_out_dir, "snap-x", "patterns", [{"pattern_id": "p1"}])
    data = json.loads((enrich_out_dir / "enrichment.json").read_text())
    assert set(data["passes"].keys()) == {"description", "patterns"}

    # Simulate write failure on third commit
    import graphify.enrich as enrich_mod
    real_replace = os.replace
    calls = {"n": 0}
    def flaky_replace(src, dst):
        calls["n"] += 1
        raise OSError("disk full")
    monkeypatch.setattr(enrich_mod.os, "replace", flaky_replace)

    with pytest.raises(OSError):
        _commit_pass(enrich_out_dir, "snap-x", "community", {"0": "summary"})

    # Restore and verify prior state untouched
    monkeypatch.setattr(enrich_mod.os, "replace", real_replace)
    data = json.loads((enrich_out_dir / "enrichment.json").read_text())
    assert set(data["passes"].keys()) == {"description", "patterns"}, (
        "failed commit must not corrupt prior passes"
    )
    assert not (enrich_out_dir / "enrichment.json.tmp").exists(), (
        ".tmp file must be cleaned up after failed write"
    )


# ---------------------------------------------------------------------------
# Test: LLM output sanitized (T-15-03)
# ---------------------------------------------------------------------------

def test_pass_output_sanitized(enrich_out_dir: Path, monkeypatch) -> None:
    """Raw LLM output with HTML/markdown tokens is piped through sanitize_label_md."""
    from graphify.enrich import _run_description_pass, _sanitize_pass_output

    # Sanity: the sanitizer itself escapes angle brackets
    assert "<script>" not in _sanitize_pass_output("<script>alert(1)</script>")

    G = _make_graph([
        ("n0", {"label": "N0", "source_file": "f0.py", "file_type": "code"}),
    ])

    def fake_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        return ("<script>alert(1)</script>", 10)
    monkeypatch.setattr("graphify.enrich._call_llm", fake_llm)

    result, _, _ = _run_description_pass(
        G, enrich_out_dir, "snap-x",
        budget_remaining=1000, dry_run=False,
        alias_map={}, routing_skip=set(),
    )
    assert "n0" in result
    assert "<script>" not in result["n0"], (
        f"raw HTML must be sanitized, got: {result['n0']!r}"
    )
