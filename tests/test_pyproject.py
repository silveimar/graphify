"""Regression guard for pyproject.toml packaging metadata.

Ensures Phase 1 Foundation's obsidian extras group survives future merges —
merge commit 15b97be silently dropped `obsidian = ["PyYAML"]` and the PyYAML
entry from `all` when reconciling v3's video/audio additions. This test
fails loudly if that recurs.
"""
from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python 3.10 via pytest's transitive dep


def _load_pyproject() -> dict:
    root = Path(__file__).resolve().parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def test_obsidian_extras_group_exists():
    data = _load_pyproject()
    extras = data["project"]["optional-dependencies"]
    assert "obsidian" in extras, (
        "pyproject.toml is missing the 'obsidian' optional-dependencies group. "
        "Phase 1 Foundation requires `obsidian = [\"PyYAML\"]` for profile.yaml "
        "loading. If you hit this after a merge, restore the line under "
        "[project.optional-dependencies]."
    )
    assert "PyYAML" in extras["obsidian"], (
        "'obsidian' extras group exists but does not declare PyYAML. "
        "profile.py's fallback path prints `pip install graphifyy[obsidian]` "
        "as its install hint — that command must install PyYAML."
    )


def test_all_extras_includes_pyyaml():
    data = _load_pyproject()
    all_extras = data["project"]["optional-dependencies"]["all"]
    assert "PyYAML" in all_extras, (
        "'all' extras group is missing PyYAML. `pip install graphifyy[all]` "
        "must include every optional dep — if obsidian is in extras, its "
        "package must be in 'all' too."
    )
