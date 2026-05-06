"""Tests for confidence cache helpers (Phase 65 / CCONF-03).

Covers prompt_version invalidation, model invalidation, file_hash isolation,
and namespace orthogonality with the AST cache.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from graphify.cache import (
    _sanitize_prompt_version,
    _confidence_cache_key,
    confidence_cache_dir,
    load_confidence,
    save_confidence,
    file_hash,
    load_cached,
    save_cached,
    cache_dir,
    _cache_json_filename,
)


@pytest.fixture
def tmp_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def foo():\n    return 1\n")
    return f


def test_prompt_version_invalidation(tmp_file, tmp_path):
    payload = {"edges": [{"src": "a", "tgt": "b", "score": 0.7, "evidence": "uses bar"}]}
    save_confidence(tmp_file, payload, tmp_path, prompt_version="1.13.0", model_id="claude-3-7-sonnet")

    hit = load_confidence(tmp_file, tmp_path, prompt_version="1.13.0", model_id="claude-3-7-sonnet")
    assert hit == payload

    miss = load_confidence(tmp_file, tmp_path, prompt_version="1.13.1", model_id="claude-3-7-sonnet")
    assert miss is None


def test_model_invalidation_isolated(tmp_file, tmp_path):
    payload = {"edges": [{"src": "x", "tgt": "y", "score": 0.5, "evidence": "ev"}]}
    save_confidence(tmp_file, payload, tmp_path, prompt_version="1.13.0", model_id="claude-3-7-sonnet")

    # Save AST cache with same model
    save_cached(tmp_file, {"nodes": [{"id": "a"}], "edges": []}, tmp_path, model_id="claude-3-7-sonnet")

    # Confidence cache miss with different model
    miss = load_confidence(tmp_file, tmp_path, prompt_version="1.13.0", model_id="claude-3-5-haiku")
    assert miss is None

    # AST cache for same file + same model still hits — namespace untouched
    ast_hit = load_cached(tmp_file, tmp_path, model_id="claude-3-7-sonnet")
    assert ast_hit is not None
    assert ast_hit.get("nodes") == [{"id": "a"}]


def test_file_hash_unchanged_skips(tmp_file, tmp_path):
    payload = {"edges": [{"score": 0.42}]}
    save_confidence(tmp_file, payload, tmp_path, prompt_version="1.13.0", model_id="m1")
    hit1 = load_confidence(tmp_file, tmp_path, prompt_version="1.13.0", model_id="m1")
    hit2 = load_confidence(tmp_file, tmp_path, prompt_version="1.13.0", model_id="m1")
    assert hit1 == hit2 == payload


def test_confidence_cache_isolation_from_extract_cache(tmp_file, tmp_path):
    """Bumping prompt_version must not mutate any AST cache file on disk."""
    save_cached(tmp_file, {"nodes": [], "edges": []}, tmp_path, model_id="m1")
    ast_files_before = {p.name: p.read_bytes() for p in cache_dir(tmp_path).glob("*.json")}
    assert ast_files_before, "expected AST cache to have at least one entry"

    save_confidence(tmp_file, {"edges": []}, tmp_path, prompt_version="1.13.0", model_id="m1")
    save_confidence(tmp_file, {"edges": []}, tmp_path, prompt_version="1.13.1", model_id="m1")
    save_confidence(tmp_file, {"edges": []}, tmp_path, prompt_version="2.0.0", model_id="m1")

    ast_files_after = {p.name: p.read_bytes() for p in cache_dir(tmp_path).glob("*.json")}
    assert ast_files_before == ast_files_after, "AST cache files must be byte-identical after confidence cache mutations"


def test_confidence_dir_layout(tmp_path):
    d = confidence_cache_dir(tmp_path)
    assert d == tmp_path / "graphify-out" / "cache" / "confidence"
    assert d.is_dir()


def test_sanitize_prompt_version_rejects_traversal():
    with pytest.raises(ValueError):
        _sanitize_prompt_version("../etc")
    with pytest.raises(ValueError):
        _sanitize_prompt_version("/abs")
    with pytest.raises(ValueError):
        _sanitize_prompt_version("a\\b")
    with pytest.raises(ValueError):
        _sanitize_prompt_version("")
    assert _sanitize_prompt_version("1.13.0") == "1.13.0"


def test_filename_safe_for_windows(tmp_file, tmp_path):
    """Cache filename for any composite key must never contain ':'."""
    key = _confidence_cache_key("1.13.0", "claude-3-7-sonnet", "abc123")
    fname = _cache_json_filename(key)
    assert ":" not in fname
    assert fname.endswith(".json")

    save_confidence(tmp_file, {"x": 1}, tmp_path, prompt_version="1.13.0", model_id="claude-3-7-sonnet")
    for p in confidence_cache_dir(tmp_path).glob("*.json"):
        assert ":" not in p.name
