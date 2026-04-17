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
