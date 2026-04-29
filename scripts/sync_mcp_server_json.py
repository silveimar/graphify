#!/usr/bin/env python3
"""Update repo-root server.json PyPI version fields and _meta.manifest_content_hash.

Run after `pip install -e .` so importlib.metadata matches pyproject.toml.

  python scripts/sync_mcp_server_json.py

Exits non-zero if the installed graphifyy version does not match pyproject.toml.
"""
from __future__ import annotations

import json
import re
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_SERVER_JSON = _REPO_ROOT / "server.json"
_LINE_RE = re.compile(r'^version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def _pyproject_version() -> str:
    text = _PYPROJECT.read_text(encoding="utf-8")
    m = _LINE_RE.search(text)
    if not m:
        raise SystemExit(f"no version = line in {_PYPROJECT}")
    return m.group(1)


def main() -> int:
    declared = _pyproject_version()
    installed = pkg_version("graphifyy")
    if installed != declared:
        print(
            f"error: installed graphifyy ({installed}) != pyproject ({declared}). "
            f"Run: pip install -e .",
            file=sys.stderr,
        )
        return 2

    from graphify.capability import build_manifest_dict, canonical_manifest_hash

    built = build_manifest_dict()
    digest = canonical_manifest_hash(built)
    tool_count = len(built.get("CAPABILITY_TOOLS", []) or [])

    raw = json.loads(_SERVER_JSON.read_text(encoding="utf-8"))
    raw["version"] = declared
    pkgs = raw.get("packages")
    if isinstance(pkgs, list) and pkgs and isinstance(pkgs[0], dict):
        pkgs[0]["version"] = declared
    meta = raw.setdefault("_meta", {})
    if isinstance(meta, dict):
        meta["manifest_content_hash"] = digest
        meta["tool_count"] = tool_count

    _SERVER_JSON.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{_SERVER_JSON.relative_to(_REPO_ROOT)}: synced to {declared}, hash={digest[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
