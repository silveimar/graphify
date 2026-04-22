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


# ===========================================================================
# Plan 15-03 tests — staleness pass + D-07 resume + D-05 schema guard
# ===========================================================================

def _pre_write_envelope(out_dir: Path, snapshot_id: str, passes: dict) -> None:
    """Helper: seed an enrichment.json envelope for resume tests."""
    envelope = {
        "version": 1,
        "snapshot_id": snapshot_id,
        "generated_at": "2026-04-20T16:00:00Z",
        "passes": passes,
    }
    (out_dir / "enrichment.json").write_text(json.dumps(envelope, indent=2))


# ---------------------------------------------------------------------------
# Test: staleness pass performs zero LLM calls (D-03 compute-only)
# ---------------------------------------------------------------------------

def test_staleness_pass_no_llm_calls(enrich_out_dir: Path, monkeypatch) -> None:
    """_run_staleness_pass must never call _call_llm; tokens_used == 0; llm_calls == 0."""
    from graphify.enrich import _run_staleness_pass

    G = _make_graph([
        ("n0", {"label": "N0", "source_file": "", "file_type": "code"}),
        ("n1", {"label": "N1", "source_file": "", "file_type": "code"}),
    ])

    llm_calls = {"n": 0}

    def boom_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        llm_calls["n"] += 1
        raise AssertionError("_call_llm must NOT be invoked by staleness pass (D-03)")
    monkeypatch.setattr("graphify.enrich._call_llm", boom_llm)

    result, tokens, calls = _run_staleness_pass(
        G, enrich_out_dir, "snap-x", alias_map={}, dry_run=False,
    )
    assert tokens == 0, f"tokens must be 0 (compute-only), got {tokens}"
    assert calls == 0, f"llm_calls must be 0 (compute-only), got {calls}"
    assert llm_calls["n"] == 0, "_call_llm was invoked — D-03 violation"
    # Every node should be classified (no source_file ⇒ FRESH per delta.classify_staleness)
    assert set(result.keys()) == {"n0", "n1"}


# ---------------------------------------------------------------------------
# Test: staleness pass correctly labels FRESH / STALE / GHOST
# ---------------------------------------------------------------------------

def test_staleness_pass_classifies_fresh_stale_ghost(
    tmp_path: Path, enrich_out_dir: Path,
) -> None:
    """Staleness pass wraps delta.classify_staleness — labels match file state."""
    import networkx as nx
    from graphify.cache import file_hash
    from graphify.enrich import _run_staleness_pass

    src_fresh = tmp_path / "fresh.py"
    src_fresh.write_text("x = 1\n")
    src_stale = tmp_path / "stale.py"
    src_stale.write_text("y = 2\n")
    # classify_staleness uses graphify.cache.file_hash (which includes resolved path)
    fresh_hash = file_hash(src_fresh)

    G = nx.Graph()
    G.add_node(
        "N1", label="n1", file_type="code",
        source_file=str(src_fresh), source_hash=fresh_hash,
        source_mtime=src_fresh.stat().st_mtime,
    )
    G.add_node(
        "N2", label="n2", file_type="code",
        source_file=str(src_stale),
        source_hash="deadbeef" * 8,  # wrong hash → STALE
        source_mtime=src_stale.stat().st_mtime - 10,  # mtime differs too
    )
    G.add_node(
        "N3", label="n3", file_type="code",
        source_file=str(tmp_path / "missing.py"),
        source_hash="x", source_mtime=0.0,
    )

    result, tokens, calls = _run_staleness_pass(
        G, enrich_out_dir, "snap-x", alias_map={}, dry_run=False,
    )
    assert tokens == 0 and calls == 0
    assert result["N1"] == "FRESH", f"N1 expected FRESH, got {result.get('N1')!r}"
    assert result["N2"] == "STALE", f"N2 expected STALE, got {result.get('N2')!r}"
    assert result["N3"] == "GHOST", f"N3 expected GHOST, got {result.get('N3')!r}"


# ---------------------------------------------------------------------------
# Test: D-07 resume — matching snapshot_id skips completed passes
# ---------------------------------------------------------------------------

def test_resume_same_snapshot_skips_completed_passes(
    enrich_out_dir: Path, monkeypatch,
) -> None:
    """Re-running with matching snapshot_id must skip passes already in enrichment.json."""
    import graphify.enrich as enrich_mod
    from graphify.enrich import EnrichmentResult

    _write_min_graph_json(enrich_out_dir)
    # Pre-seed envelope: description already complete
    _pre_write_envelope(enrich_out_dir, "snap-x", {"description": {"N1": "done"}})

    # Stub all three LLM pass runners — track which got called
    calls: list[str] = []

    def fake_desc(*a, **kw):
        calls.append("description")
        return {"N_new": "newdesc"}, 0, 0

    def fake_patterns(*a, **kw):
        calls.append("patterns")
        return [], 0, 0

    def fake_community(*a, **kw):
        calls.append("community")
        return {}, 0, 0

    def fake_staleness(*a, **kw):
        calls.append("staleness")
        return {}, 0, 0

    monkeypatch.setattr(enrich_mod, "_run_description_pass", fake_desc)
    monkeypatch.setattr(enrich_mod, "_run_patterns_pass", fake_patterns)
    monkeypatch.setattr(enrich_mod, "_run_community_pass", fake_community)
    monkeypatch.setattr(enrich_mod, "_run_staleness_pass", fake_staleness)

    import networkx as nx
    monkeypatch.setattr(
        "graphify.snapshot.load_snapshot",
        lambda p: (nx.Graph(), {}, {}),
    )
    monkeypatch.setattr("graphify.serve._load_dedup_report", lambda od: {})

    result = EnrichmentResult(snapshot_id="snap-x")
    enrich_mod._run_passes(
        enrich_out_dir, "snap-x",
        enrich_out_dir / "snapshots" / "2026-04-20T14-30-00.json",
        ["description", "patterns", "community", "staleness"],
        budget=None, dry_run=False, resume=True, result=result,
    )

    assert "description" not in calls, (
        f"description should be skipped on resume, but got calls={calls}"
    )
    assert result.passes_skipped == ["description"], (
        f"expected passes_skipped=['description'], got {result.passes_skipped}"
    )
    assert set(result.passes_run) == {"patterns", "community", "staleness"}, (
        f"expected remaining 3 passes to run, got {result.passes_run}"
    )

    # The pre-written description value must survive (not overwritten)
    data = json.loads((enrich_out_dir / "enrichment.json").read_text())
    assert data["passes"]["description"] == {"N1": "done"}, (
        f"resume must preserve prior description; got {data['passes']['description']!r}"
    )


# ---------------------------------------------------------------------------
# Test: D-07 different snapshot_id → fresh run (envelope discarded)
# ---------------------------------------------------------------------------

def test_resume_diff_snapshot_fresh(enrich_out_dir: Path, monkeypatch) -> None:
    """Pre-existing envelope with a different snapshot_id must be discarded → all 4 passes run."""
    import graphify.enrich as enrich_mod
    from graphify.enrich import (
        EnrichmentResult,
        _load_existing_enrichment,
    )

    _write_min_graph_json(enrich_out_dir)
    _pre_write_envelope(enrich_out_dir, "s_old", {"description": {"Nold": "x"}})

    # _load_existing_enrichment must return {} for mismatched snapshot_id
    assert _load_existing_enrichment(enrich_out_dir, "s_new") == {}

    def fake_desc(*a, **kw):
        return {"Nnew": "d"}, 0, 0

    def fake_patterns(*a, **kw):
        return [{"pattern_id": "p1", "nodes": ["Nnew"], "summary": "s"}], 0, 0

    def fake_community(*a, **kw):
        return {"0": "c"}, 0, 0

    def fake_staleness(*a, **kw):
        return {"Nnew": "FRESH"}, 0, 0

    monkeypatch.setattr(enrich_mod, "_run_description_pass", fake_desc)
    monkeypatch.setattr(enrich_mod, "_run_patterns_pass", fake_patterns)
    monkeypatch.setattr(enrich_mod, "_run_community_pass", fake_community)
    monkeypatch.setattr(enrich_mod, "_run_staleness_pass", fake_staleness)

    import networkx as nx
    monkeypatch.setattr(
        "graphify.snapshot.load_snapshot",
        lambda p: (nx.Graph(), {}, {}),
    )
    monkeypatch.setattr("graphify.serve._load_dedup_report", lambda od: {})

    result = EnrichmentResult(snapshot_id="s_new")
    enrich_mod._run_passes(
        enrich_out_dir, "s_new",
        enrich_out_dir / "snapshots" / "2026-04-20T14-30-00.json",
        ["description", "patterns", "community", "staleness"],
        budget=None, dry_run=False, resume=True, result=result,
    )

    assert result.passes_skipped == [], (
        f"expected empty passes_skipped on fresh snapshot, got {result.passes_skipped}"
    )
    assert len(result.passes_run) == 4, (
        f"expected all 4 passes to run, got {result.passes_run}"
    )

    data = json.loads((enrich_out_dir / "enrichment.json").read_text())
    assert data["snapshot_id"] == "s_new", (
        f"envelope snapshot_id must be overwritten with new id; got {data['snapshot_id']!r}"
    )
    # Prior description value must be gone (discarded because snapshot mismatched)
    assert "Nold" not in data["passes"].get("description", {}), (
        "prior snapshot's description entries must be discarded"
    )


# ---------------------------------------------------------------------------
# Test: envelope schema v1 + _validate_enrichment_envelope
# ---------------------------------------------------------------------------

def test_enrichment_envelope_version_one(enrich_out_dir: Path, monkeypatch) -> None:
    """After a full 4-pass run, enrichment.json has version=1 and all 4 pass keys."""
    import graphify.enrich as enrich_mod
    from graphify.enrich import (
        EnrichmentResult,
        _validate_enrichment_envelope,
    )

    _write_min_graph_json(enrich_out_dir)

    def fake_desc(*a, **kw):
        return {"N1": "d"}, 0, 0

    def fake_patterns(*a, **kw):
        return [{"pattern_id": "p1", "nodes": ["N1"], "summary": "s"}], 0, 0

    def fake_community(*a, **kw):
        return {"0": "summary"}, 0, 0

    def fake_staleness(*a, **kw):
        return {"N1": "FRESH"}, 0, 0

    monkeypatch.setattr(enrich_mod, "_run_description_pass", fake_desc)
    monkeypatch.setattr(enrich_mod, "_run_patterns_pass", fake_patterns)
    monkeypatch.setattr(enrich_mod, "_run_community_pass", fake_community)
    monkeypatch.setattr(enrich_mod, "_run_staleness_pass", fake_staleness)

    import networkx as nx
    monkeypatch.setattr(
        "graphify.snapshot.load_snapshot",
        lambda p: (nx.Graph(), {}, {}),
    )
    monkeypatch.setattr("graphify.serve._load_dedup_report", lambda od: {})

    result = EnrichmentResult(snapshot_id="snap-x")
    enrich_mod._run_passes(
        enrich_out_dir, "snap-x",
        enrich_out_dir / "snapshots" / "2026-04-20T14-30-00.json",
        ["description", "patterns", "community", "staleness"],
        budget=None, dry_run=False, resume=False, result=result,
    )

    data = json.loads((enrich_out_dir / "enrichment.json").read_text())
    assert data["version"] == 1
    assert set(data["passes"].keys()) == {
        "description", "patterns", "community", "staleness",
    }
    assert isinstance(data.get("snapshot_id"), str) and data["snapshot_id"]
    assert "generated_at" in data
    assert _validate_enrichment_envelope(data) is True


# ---------------------------------------------------------------------------
# Test: malformed / wrong-version envelope is discarded on load
# ---------------------------------------------------------------------------

def test_malformed_envelope_discarded(
    enrich_out_dir: Path, capsys,
) -> None:
    """Wrong version or wrong shape → _load_existing_enrichment returns {}."""
    from graphify.enrich import (
        _load_existing_enrichment,
        _validate_enrichment_envelope,
    )

    # Case 1: wrong version
    (enrich_out_dir / "enrichment.json").write_text(
        json.dumps({"version": 2, "snapshot_id": "s1", "passes": {}})
    )
    assert _load_existing_enrichment(enrich_out_dir, "s1") == {}
    captured = capsys.readouterr()
    assert "[graphify]" in captured.err, (
        f"expected stderr warning starting with [graphify]; got {captured.err!r}"
    )

    # Case 2: completely wrong shape
    (enrich_out_dir / "enrichment.json").write_text(
        json.dumps({"completely": "wrong-shape"})
    )
    assert _validate_enrichment_envelope({"completely": "wrong-shape"}) is False
    assert _load_existing_enrichment(enrich_out_dir, "s1") == {}

    # Case 3: not even JSON
    (enrich_out_dir / "enrichment.json").write_text("{{{ not json")
    assert _load_existing_enrichment(enrich_out_dir, "s1") == {}

    # Case 4: valid v1 envelope with mismatched snapshot_id still returns {}
    (enrich_out_dir / "enrichment.json").write_text(
        json.dumps({
            "version": 1,
            "snapshot_id": "s_other",
            "generated_at": "2026-04-20T16:00:00Z",
            "passes": {},
        })
    )
    assert _load_existing_enrichment(enrich_out_dir, "s1") == {}

    # Positive control: a valid matching envelope returns the full dict
    (enrich_out_dir / "enrichment.json").write_text(
        json.dumps({
            "version": 1,
            "snapshot_id": "s1",
            "generated_at": "2026-04-20T16:00:00Z",
            "passes": {"description": {"n0": "desc"}},
        })
    )
    loaded = _load_existing_enrichment(enrich_out_dir, "s1")
    assert loaded.get("snapshot_id") == "s1"
    assert loaded.get("passes", {}).get("description") == {"n0": "desc"}


# ---------------------------------------------------------------------------
# Plan 15-05 Task 1: foreground-lock contention (ENRICH-07)
# ---------------------------------------------------------------------------

def test_foreground_acquire_returns_none_when_out_dir_missing(tmp_path: Path) -> None:
    """_foreground_acquire_enrichment_lock on a non-existent out_dir returns None (no lock needed)."""
    from graphify.__main__ import _foreground_acquire_enrichment_lock
    result = _foreground_acquire_enrichment_lock(tmp_path / "nonexistent_out_dir")
    assert result is None


def test_foreground_lock_preempts_enrichment(tmp_path: Path, enrich_out_dir: Path) -> None:
    """ENRICH-07: foreground rebuild SIGTERMs running enrichment and wins the lock.

    Spawns a helper child process that:
      - acquires .enrichment.lock (LOCK_EX)
      - writes .enrichment.pid
      - installs a SIGTERM handler that unlocks + removes pid + exits(1)
      - sleeps indefinitely

    Then foreground calls _foreground_acquire_enrichment_lock; it must
    SIGTERM the child, block briefly on LOCK_EX, and return a valid fd.
    """
    import subprocess
    import time

    from graphify.enrich import LOCK_FILENAME, PID_FILENAME

    enrich_script = tmp_path / "fake_enrich.py"
    enrich_script.write_text(
        "import fcntl, os, time, json, signal, sys\n"
        f"out_dir = {str(enrich_out_dir)!r}\n"
        f"lock_path = os.path.join(out_dir, {LOCK_FILENAME!r})\n"
        f"pid_path = os.path.join(out_dir, {PID_FILENAME!r})\n"
        "fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)\n"
        "fcntl.flock(fd, fcntl.LOCK_EX)\n"
        "with open(pid_path, 'w') as f:\n"
        "    json.dump({'pid': os.getpid(), 'started_at': 'now', 'expires_at': 'later'}, f)\n"
        "def handler(s, fr):\n"
        "    try: fcntl.flock(fd, fcntl.LOCK_UN)\n"
        "    except Exception: pass\n"
        "    try: os.unlink(pid_path)\n"
        "    except Exception: pass\n"
        "    sys.exit(1)\n"
        "signal.signal(signal.SIGTERM, handler)\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    proc = subprocess.Popen([sys.executable, str(enrich_script)])
    try:
        pid_file = enrich_out_dir / PID_FILENAME
        deadline = time.time() + 5.0
        while not pid_file.exists() and time.time() < deadline:
            time.sleep(0.05)
        assert pid_file.exists(), "fake enrichment failed to write .enrichment.pid"

        from graphify.__main__ import (
            _foreground_acquire_enrichment_lock,
            _foreground_release_enrichment_lock,
        )
        t0 = time.time()
        lock_fd = _foreground_acquire_enrichment_lock(enrich_out_dir, timeout_seconds=10.0)
        elapsed = time.time() - t0
        assert lock_fd is not None, "foreground failed to acquire lock"
        assert elapsed < 5.0, (
            f"foreground took {elapsed:.2f}s (should be ~instant after SIGTERM)"
        )
        proc.wait(timeout=5.0)
        assert proc.returncode == 1, (
            f"child should have SIGTERM-exited with 1 (got {proc.returncode})"
        )
        _foreground_release_enrichment_lock(lock_fd)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2.0)


# ===========================================================================
# Plan 15-06 tests — dry-run D-02 envelope (ENRICH-10 P2, SC-4)
# ===========================================================================

def _write_fixture_for_dry_run(out_dir: Path) -> None:
    """Seed graph.json + a matching snapshot so run_enrichment can pin."""
    graph_payload = {
        "directed": False, "multigraph": False, "graph": {},
        "nodes": [
            {"id": "N1", "label": "n1", "description": "",
             "source_file": "x.py", "source_hash": "h1",
             "source_mtime": 0.0, "file_type": "code"},
            {"id": "N2", "label": "n2", "description": "",
             "source_file": "y.py", "source_hash": "h2",
             "source_mtime": 0.0, "file_type": "code"},
        ],
        "links": [],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "graph.json").write_text(json.dumps(graph_payload))
    snap_payload = {
        "graph": graph_payload,
        "communities": {"0": ["N1", "N2"]},
        "metadata": {},
    }
    (out_dir / "snapshots").mkdir(exist_ok=True)
    (out_dir / "snapshots" / "2026-04-20T14-30-00.json").write_text(
        json.dumps(snap_payload)
    )


def test_dry_run_emits_d02_envelope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENRICH-10 P2: --dry-run emits a D-02 envelope (table + separator + JSON)."""
    out_dir = tmp_path / "graphify-out"
    _write_fixture_for_dry_run(out_dir)

    # Any LLM invocation during dry-run is a hard failure.
    def forbidden_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        raise AssertionError("LLM called during dry-run")
    monkeypatch.setattr("graphify.enrich._call_llm", forbidden_llm)

    from graphify.enrich import run_enrichment
    result = run_enrichment(
        out_dir,
        budget=10000,
        passes=None,
        dry_run=True,
        project_root=tmp_path,
    )
    assert result.dry_run is True

    out = capsys.readouterr().out
    # Human-readable table header
    assert "graphify enrich --dry-run preview" in out
    assert "snapshot_id:" in out
    assert "budget cap:" in out
    for pass_name in ("description", "patterns", "community", "staleness"):
        assert pass_name in out, f"pass {pass_name!r} missing from table"
    # D-02 separator marker (exact literal)
    assert "---GRAPHIFY-META---" in out, "D-02 separator missing"

    # Everything AFTER the separator must be valid JSON with expected shape.
    _, _, meta_blob = out.partition("---GRAPHIFY-META---")
    meta = json.loads(meta_blob.strip())
    assert meta["dry_run"] is True
    assert meta["status"] == "preview"
    assert meta["snapshot_id"] == "2026-04-20T14-30-00"
    assert set(meta["passes"].keys()) >= {
        "description", "patterns", "community", "staleness",
    }
    for pname, info in meta["passes"].items():
        assert "tokens_estimate" in info
        assert "llm_calls_estimate" in info
    assert "totals" in meta
    assert "tokens_estimate" in meta["totals"]
    assert "llm_calls_estimate" in meta["totals"]
    assert meta["budget_cap"] == 10000
    assert "within_budget" in meta


def test_dry_run_no_llm_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ENRICH-10 P2 / SC-4: dry-run guarantees zero LLM invocations and no disk writes."""
    out_dir = tmp_path / "graphify-out"
    _write_fixture_for_dry_run(out_dir)

    call_counter = {"n": 0}

    def forbidden_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        call_counter["n"] += 1
        raise AssertionError("LLM called during dry-run")

    monkeypatch.setattr("graphify.enrich._call_llm", forbidden_llm)

    from graphify.enrich import run_enrichment
    run_enrichment(
        out_dir,
        budget=10000,
        passes=None,
        dry_run=True,
        project_root=tmp_path,
    )
    assert call_counter["n"] == 0, (
        f"dry-run invoked LLM {call_counter['n']} time(s)"
    )
    # Dry-run never touches disk — no enrichment.json should appear.
    assert not (out_dir / "enrichment.json").exists(), (
        "dry-run must not produce enrichment.json"
    )


def test_dry_run_envelope_within_budget_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dry-run envelope flips within_budget=False when totals exceed cap."""
    out_dir = tmp_path / "graphify-out"
    _write_fixture_for_dry_run(out_dir)

    def forbidden_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
        raise AssertionError("LLM called during dry-run")
    monkeypatch.setattr("graphify.enrich._call_llm", forbidden_llm)

    from graphify.enrich import run_enrichment
    # Tiny budget: each pass's dry-run estimate is 300 tokens per item, so
    # a budget of 100 must produce within_budget=False in the meta.
    run_enrichment(
        out_dir,
        budget=100,
        passes=None,
        dry_run=True,
        project_root=tmp_path,
    )
    out = capsys.readouterr().out
    _, _, meta_blob = out.partition("---GRAPHIFY-META---")
    meta = json.loads(meta_blob.strip())
    assert meta["budget_cap"] == 100
    assert meta["within_budget"] is False
