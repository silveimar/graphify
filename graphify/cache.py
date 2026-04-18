# per-file extraction cache - skip unchanged files on re-run
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _body_content(content: bytes) -> bytes:
    """Strip YAML frontmatter from Markdown content, returning only the body."""
    text = content.decode(errors="replace")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].encode()
    return content


def _inner_hash(path: Path) -> str:
    """SHA256 of file contents + resolved path (legacy cache key body)."""
    p = Path(path)
    raw = p.read_bytes()
    content = _body_content(raw) if p.suffix.lower() == ".md" else raw
    h = hashlib.sha256()
    h.update(content)
    h.update(b"\x00")
    h.update(str(p.resolve()).encode())
    return h.hexdigest()


def _sanitize_model_id(model_id: str) -> str:
    """Reject path-like model_id values (cache poisoning / traversal)."""
    if ".." in model_id or "/" in model_id or "\\" in model_id:
        raise ValueError("model_id must not contain path segments or '..'")
    if not model_id:
        return ""
    # Reasonable length cap
    if len(model_id) > 512:
        raise ValueError("model_id too long")
    return model_id


def _cache_key_string(inner: str, model_id: str) -> str:
    """ROUTE-04: returned file_hash string; empty model_id preserves legacy 64-char hex."""
    if not model_id:
        return inner
    return f"{inner}:{model_id}"


def _cache_json_filename(key: str) -> str:
    """Map logical cache key to a filesystem-safe .json basename (no ':' on Windows)."""
    if ":" not in key:
        return f"{key}.json"
    return f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"


def file_hash(path: Path, model_id: str = "") -> str:
    """SHA256 of file contents + resolved path, optional ROUTE-04 model_id suffix.

    When ``model_id`` is empty, returns the legacy 64-char hex digest only.
    When non-empty, returns ``hexdigest + ':' + model_id`` and uses a hashed
    filename under ``graphify-out/cache/`` so paths stay portable.
    """
    _sanitize_model_id(model_id)
    inner = _inner_hash(path)
    return _cache_key_string(inner, model_id)


def cache_dir(root: Path = Path(".")) -> Path:
    """Returns graphify-out/cache/ - creates it if needed."""
    d = Path(root) / "graphify-out" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_cached(path: Path, root: Path = Path("."), *, model_id: str = "") -> dict | None:
    """Return cached extraction for this file if hash matches, else None."""
    try:
        key = file_hash(path, model_id=model_id)
    except ValueError:
        return None
    except OSError:
        return None
    entry = cache_dir(root) / _cache_json_filename(key)
    if not entry.exists():
        return None
    try:
        return json.loads(entry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_cached(
    path: Path,
    result: dict,
    root: Path = Path("."),
    *,
    model_id: str = "",
) -> None:
    """Save extraction result for this file under a key that includes optional ``model_id``."""
    key = file_hash(path, model_id=model_id)
    entry = cache_dir(root) / _cache_json_filename(key)
    tmp = entry.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(result), encoding="utf-8")
        os.replace(tmp, entry)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def cached_files(root: Path = Path(".")) -> set[str]:
    """Return set of cache key stems present (legacy hex or hashed names)."""
    d = cache_dir(root)
    out: set[str] = set()
    for p in d.glob("*.json"):
        out.add(p.stem)
    return out


def clear_cache(root: Path = Path(".")) -> None:
    """Delete all graphify-out/cache/*.json files."""
    d = cache_dir(root)
    for f in d.glob("*.json"):
        f.unlink()


def check_semantic_cache(
    files: list[str],
    root: Path = Path("."),
    *,
    model_id: str = "",
) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Check semantic extraction cache for a list of absolute file paths."""
    cached_nodes: list[dict] = []
    cached_edges: list[dict] = []
    cached_hyperedges: list[dict] = []
    uncached: list[str] = []

    for fpath in files:
        result = load_cached(Path(fpath), root, model_id=model_id)
        if result is not None:
            cached_nodes.extend(result.get("nodes", []))
            cached_edges.extend(result.get("edges", []))
            cached_hyperedges.extend(result.get("hyperedges", []))
        else:
            uncached.append(fpath)

    return cached_nodes, cached_edges, cached_hyperedges, uncached


def save_semantic_cache(
    nodes: list[dict],
    edges: list[dict],
    hyperedges: list[dict] | None = None,
    root: Path = Path("."),
    *,
    model_id: str = "",
) -> int:
    """Save semantic extraction results to cache, keyed by source_file."""
    from collections import defaultdict

    by_file: dict[str, dict] = defaultdict(lambda: {"nodes": [], "edges": [], "hyperedges": []})
    for n in nodes:
        src = n.get("source_file", "")
        if src:
            by_file[src]["nodes"].append(n)
    for e in edges:
        src = e.get("source_file", "")
        if src:
            by_file[src]["edges"].append(e)
    for h in (hyperedges or []):
        src = h.get("source_file", "")
        if src:
            by_file[src]["hyperedges"].append(h)

    saved = 0
    for fpath, result in by_file.items():
        p = Path(fpath)
        if not p.is_absolute():
            p = Path(root) / p
        if p.exists():
            save_cached(p, result, root, model_id=model_id)
            saved += 1
    return saved
