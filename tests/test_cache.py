"""Tests for graphify/cache.py."""
import pytest
from pathlib import Path
from graphify.cache import (
    file_hash,
    cache_dir,
    load_cached,
    save_cached,
    save_semantic_cache,
    cached_files,
    clear_cache,
    _body_content,
)


@pytest.fixture
def tmp_file(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("hello world")
    return f


@pytest.fixture
def cache_root(tmp_path):
    return tmp_path


def test_file_hash_consistent(tmp_file):
    """Same file gives same hash on repeated calls."""
    h1 = file_hash(tmp_file)
    h2 = file_hash(tmp_file)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) == 64  # SHA256 hex digest length


def test_file_hash_changes(tmp_path):
    """Different file contents give different hashes."""
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("content one")
    f2.write_text("content two")
    assert file_hash(f1) != file_hash(f2)


def test_cache_roundtrip(tmp_file, cache_root):
    """Save then load returns the same result dict."""
    result = {"nodes": [{"id": "n1", "label": "Node1"}], "edges": []}
    save_cached(tmp_file, result, root=cache_root)
    loaded = load_cached(tmp_file, root=cache_root)
    assert loaded == result


def test_cache_miss_on_change(tmp_file, cache_root):
    """After file content changes, load_cached returns None."""
    result = {"nodes": [], "edges": [{"source": "a", "target": "b"}]}
    save_cached(tmp_file, result, root=cache_root)
    # Modify the file
    tmp_file.write_text("completely different content")
    assert load_cached(tmp_file, root=cache_root) is None


def test_cached_files(tmp_path, cache_root):
    """cached_files returns the set of cached hashes."""
    f1 = tmp_path / "file1.py"
    f2 = tmp_path / "file2.py"
    f1.write_text("alpha")
    f2.write_text("beta")

    save_cached(f1, {"nodes": [], "edges": []}, root=cache_root)
    save_cached(f2, {"nodes": [], "edges": []}, root=cache_root)

    hashes = cached_files(cache_root)
    assert file_hash(f1) in hashes
    assert file_hash(f2) in hashes


def test_clear_cache(tmp_file, cache_root):
    """clear_cache removes all .json files from graphify-out/cache/."""
    save_cached(tmp_file, {"nodes": [], "edges": []}, root=cache_root)
    assert len(list((cache_root / "graphify-out" / "cache").glob("*.json"))) > 0
    clear_cache(cache_root)
    assert len(list((cache_root / "graphify-out" / "cache").glob("*.json"))) == 0


def test_md_frontmatter_only_change_same_hash(tmp_path):
    """Changing only frontmatter fields in a .md file does not change the hash."""
    f = tmp_path / "doc.md"
    f.write_text("---\nreviewed: 2026-01-01\n---\n\n# Title\n\nBody text.")
    h1 = file_hash(f)
    f.write_text("---\nreviewed: 2026-04-09\n---\n\n# Title\n\nBody text.")
    h2 = file_hash(f)
    assert h1 == h2


def test_md_body_change_different_hash(tmp_path):
    """Changing the body of a .md file produces a different hash."""
    f = tmp_path / "doc.md"
    f.write_text("---\nreviewed: 2026-01-01\n---\n\n# Title\n\nOriginal body.")
    h1 = file_hash(f)
    f.write_text("---\nreviewed: 2026-01-01\n---\n\n# Title\n\nChanged body.")
    h2 = file_hash(f)
    assert h1 != h2


def test_md_no_frontmatter_hashed_normally(tmp_path):
    """A .md file with no frontmatter is hashed by its full content."""
    f = tmp_path / "doc.md"
    f.write_text("# Just a heading\n\nNo frontmatter here.")
    h1 = file_hash(f)
    f.write_text("# Just a heading\n\nDifferent content.")
    h2 = file_hash(f)
    assert h1 != h2


def test_non_md_file_hashed_fully(tmp_path):
    """Non-.md files are still hashed by their full content."""
    f = tmp_path / "script.py"
    f.write_text("# comment\nx = 1")
    h1 = file_hash(f)
    f.write_text("# changed comment\nx = 1")
    h2 = file_hash(f)
    assert h1 != h2


def test_model_id_splits_cache(tmp_path, cache_root):
    """ROUTE-04: different model_id → different cache paths; empty matches legacy key."""
    f = tmp_path / "a.py"
    f.write_text("print(1)", encoding="utf-8")
    h0 = file_hash(f)
    h1 = file_hash(f, model_id="m-a")
    h2 = file_hash(f, model_id="m-b")
    assert h0 != h1
    assert h1 != h2
    assert ":" not in h0
    assert ":m-a" in h1
    save_cached(f, {"nodes": [], "edges": []}, root=cache_root, model_id="m-a")
    save_cached(f, {"nodes": [{"id": "x"}], "edges": []}, root=cache_root, model_id="m-b")
    assert load_cached(f, root=cache_root, model_id="m-a") == {"nodes": [], "edges": []}
    assert load_cached(f, root=cache_root, model_id="m-b")["nodes"][0]["id"] == "x"


def test_model_id_path_rejected(tmp_path):
    import pytest

    f = tmp_path / "x.py"
    f.write_text("a = 1")
    with pytest.raises(ValueError):
        file_hash(f, model_id="../evil")


def test_semantic_cache_model_id(tmp_path, cache_root):
    """save_semantic_cache passes model_id into per-file save_cached."""
    f = tmp_path / "s.py"
    f.write_text("a = 1", encoding="utf-8")
    absf = str(f.resolve())
    save_semantic_cache(
        [{"id": "n1", "source_file": absf, "label": "a"}],
        [],
        root=cache_root,
        model_id="tier1",
    )
    assert load_cached(f, root=cache_root, model_id="tier1") is not None


def test_body_content_strips_frontmatter():
    """_body_content correctly strips YAML frontmatter."""
    content = b"---\ntitle: Test\n---\n\nActual body."
    assert _body_content(content) == b"\n\nActual body."


def test_body_content_no_frontmatter():
    """_body_content returns content unchanged when no frontmatter present."""
    content = b"No frontmatter here."
    assert _body_content(content) == content
