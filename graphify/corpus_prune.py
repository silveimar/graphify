"""Shared corpus directory pruning and output-manifest loading (Phase 45).

Used by ``detect()`` and ``extract.collect_files()`` so eligibility rules stay in sync.
The ``graphify-out/memory/`` second-root allow-list remains in ``detect`` only.

Keep pruning helpers aligned with ``detect.py`` — duplicate intentionally to avoid import cycles.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from graphify.output import ResolvedOutput

_OUTPUT_MANIFEST_NAME = "output-manifest.json"
_OUTPUT_MANIFEST_VERSION = 1

# Mirror detect.py — keep in sync.
_SKIP_DIRS = {
    "venv", ".venv", "env", ".env",
    "node_modules", "__pycache__", ".git",
    "dist", "build", "target", "out",
    "site-packages", "lib64",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".eggs", "*.egg-info",
}
_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}

DirPruneReason = Literal["noise-dir", "exclude-glob", "nesting"]


def _is_nested_output(part: str, resolved_basenames: frozenset[str]) -> bool:
    if part in _SELF_OUTPUT_DIRS:
        return True
    if part in resolved_basenames:
        return True
    return False


def _is_noise_dir(part: str) -> bool:
    if part in _SKIP_DIRS:
        return True
    if part in _SELF_OUTPUT_DIRS:
        return True
    if part.endswith("_venv") or part.endswith("_env"):
        return True
    if part.endswith(".egg-info"):
        return True
    return False


def _is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    if not patterns:
        return False
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return False
    rel = rel.replace(os.sep, "/")
    parts = rel.split("/")
    for pattern in patterns:
        p = pattern.strip("/")
        if not p:
            continue
        if fnmatch.fnmatch(rel, p):
            return True
        if fnmatch.fnmatch(path.name, p):
            return True
        for i, part in enumerate(parts):
            if fnmatch.fnmatch(part, p):
                return True
            if fnmatch.fnmatch("/".join(parts[: i + 1]), p):
                return True
    return False


def _load_output_manifest(artifacts_dir: Path) -> dict:
    manifest_path = artifacts_dir / _OUTPUT_MANIFEST_NAME
    if not manifest_path.exists():
        return {"version": _OUTPUT_MANIFEST_VERSION, "runs": []}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "runs" not in data:
            raise ValueError("unexpected shape")
        return data
    except Exception:
        print(
            "[graphify] WARNING: output-manifest.json unreadable, ignoring history",
            file=sys.stderr,
        )
        return {"version": _OUTPUT_MANIFEST_VERSION, "runs": []}


def build_prior_files(root: Path, resolved: ResolvedOutput | None) -> set[str]:
    """Union manifest file paths from resolved artifacts_dir and/or default graphify-out."""
    prior: set[str] = set()
    dirs: list[Path] = []
    if resolved is not None:
        dirs.append(resolved.artifacts_dir)
    default_go = root / "graphify-out"
    if resolved is None and default_go.is_dir():
        dirs.append(default_go)
    for ad in dirs:
        manifest_data = _load_output_manifest(ad)
        for run in manifest_data.get("runs", []):
            for f in run.get("files", []):
                try:
                    prior.add(str(Path(f).resolve()))
                except OSError:
                    prior.add(str(f))
    return prior


def nested_output_dirname(part: str, resolved_basenames: frozenset[str]) -> bool:
    """True if dirname *part* is nested graphify output (D-18); public API for doctor."""
    return _is_nested_output(part, resolved_basenames)


def dir_prune_reason(
    d: str,
    dp: Path,
    root: Path,
    *,
    resolved_basenames: frozenset[str],
    patterns: list[str],
) -> DirPruneReason | None:
    """Return skip reason if directory *d* under *dp* should not be descended into."""
    if (d.startswith(".") and d != ".graphify") or _is_noise_dir(d):
        return "noise-dir"
    if _is_ignored(dp / d, root, patterns):
        return "exclude-glob"
    if _is_nested_output(d, resolved_basenames):
        return "nesting"
    return None


def should_prune_dirname(
    d: str,
    dp: Path,
    root: Path,
    *,
    resolved_basenames: frozenset[str],
    patterns: list[str],
) -> bool:
    """True if *d* should be pruned from ``os.walk`` (same outcome as ``detect`` loop)."""
    return dir_prune_reason(d, dp, root, resolved_basenames=resolved_basenames, patterns=patterns) is not None
