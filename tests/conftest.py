"""Shared pytest fixtures for Phase 10 dedup + batch tests."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_encoder():
    """Deterministic mock encoder — same label always produces the same L2-normalized vector.

    Used in place of sentence-transformers so CI does not download the 90MB model.
    Returns a callable taking list[str] -> np.ndarray of shape (N, 384) dtype float32.
    """
    def _encode(labels: list[str]) -> np.ndarray:
        result = []
        for label in labels:
            rng = np.random.default_rng(abs(hash(label)) % (2**32))
            vec = rng.standard_normal(384).astype(np.float32)
            vec /= np.linalg.norm(vec)
            result.append(vec)
        return np.array(result)
    return _encode


@pytest.fixture
def tmp_corpus(tmp_path):
    """Factory: create a temp corpus with a dict of {relative_path: content}.

    Returns a callable `make(files: dict[str, str]) -> list[Path]`.
    Each call writes all files under tmp_path and returns absolute Path objects
    in the same order as the input dict.
    """
    def _make(files: dict[str, str]) -> list[Path]:
        paths = []
        for rel, content in files.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            paths.append(p)
        return paths
    return _make


@pytest.fixture
def dedup_config():
    """Factory: return a dict of dedup kwargs with sane defaults (D-02).

    Usage: `dedup(ext, **dedup_config())` or override individual fields.
    """
    def _make(**overrides) -> dict:
        base = {
            "fuzzy_threshold": 0.90,
            "embed_threshold": 0.85,
            "cross_type": False,
        }
        base.update(overrides)
        return base
    return _make


@pytest.fixture
def multi_file_extraction():
    """Load tests/fixtures/multi_file_extraction.json — the Phase 10 canonical test corpus.

    Contains duplicate-candidate nodes across multiple files with import edges,
    designed to exercise GRAPH-01 (clustering) and GRAPH-02/03 (dedup).
    """
    return json.loads((FIXTURES / "multi_file_extraction.json").read_text(encoding="utf-8"))


@pytest.fixture
def make_snapshot_chain(tmp_path):
    """Factory fixture: create a chain of N synthetic snapshots under `root`.

    Usage::

        def test_something(make_snapshot_chain, tmp_path):
            snaps = make_snapshot_chain(n=3, root=tmp_path)
            # snaps is a list[Path] sorted oldest-first (matching list_snapshots order)

    Node-id scheme (CRITICAL — downstream tests that construct a live tip graph G_live
    MUST use the same scheme so _find_node can match across chain and tip):

        - Snapshot i (0-indexed) contains nodes n0 .. n{i+1}
        - Each node j has: label=f"n{j}", source_file=f"f{j}.py",
          source_location=f"L{j}", file_type="code", community=j % 2
        - Each snapshot i>0 also adds edge (n0, n{i}, relation="calls",
          confidence="EXTRACTED", source_file="f0.py")
        - Nodes are named n0, n1, ..., n{i+1} with label matching the id string.

    This means a 3-snapshot chain yields:
        snap_00: nodes {n0, n1}
        snap_01: nodes {n0, n1, n2}, edge n0->n1
        snap_02: nodes {n0, n1, n2, n3}, edges n0->n1, n0->n2

    Each snapshot is saved with name=f"snap_{i:02d}" so mtime ordering matches
    insertion order (list_snapshots sorts by mtime oldest-first).
    """
    import networkx as nx
    from graphify.snapshot import save_snapshot

    def _make(n: int = 3, root: "Path | None" = None) -> "list[Path]":
        base = Path(root) if root is not None else tmp_path
        paths = []
        for i in range(n):
            G = nx.Graph()
            # Snapshot i contains nodes n0 .. n{i+1}
            for j in range(i + 2):
                G.add_node(
                    f"n{j}",
                    label=f"n{j}",
                    source_file=f"f{j}.py",
                    source_location=f"L{j}",
                    file_type="code",
                    community=j % 2,
                )
            # From snapshot 1 onward, add edge n0 -> n{i}
            if i > 0:
                G.add_edge(
                    "n0",
                    f"n{i}",
                    relation="calls",
                    confidence="EXTRACTED",
                    source_file="f0.py",
                )
            communities = {j % 2: [f"n{k}" for k in range(i + 2) if k % 2 == j % 2] for j in range(i + 2)}
            p = save_snapshot(G, communities, project_root=base, name=f"snap_{i:02d}")
            paths.append(p)
        # Return sorted oldest-first (matching list_snapshots output ordering)
        paths.sort(key=lambda p: p.stat().st_mtime)
        return paths

    return _make


@pytest.fixture
def nested_project_root(tmp_path):
    """Lay out tmp_path/project/graphify-out/snapshots/ + tmp_path/project/src/auth.py.

    Returns the project root (tmp_path/project) — NOT graphify-out/ — so path-confinement
    semantics match production. Used by both test_serve.py (focus resolver integration)
    and test_snapshot.py (CR-01 regression). Reproduces the nested-dir layout that would
    have caught v1.3 CR-01 (Pitfall 20) had it existed.
    """
    project = tmp_path / "project"
    (project / "graphify-out" / "snapshots").mkdir(parents=True)
    (project / "src").mkdir()
    (project / "src" / "auth.py").write_text("def login(): pass\n")
    return project
