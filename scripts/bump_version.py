#!/usr/bin/env python3
"""Bump the published package version in pyproject.toml (project name: graphifyy).

The CLI reads the version via importlib.metadata in graphify/__main__.py.

Typical workflow after shipping a GSD milestone and tagging:

  python scripts/bump_version.py 1.1.0
  pip install -e ".[mcp,pdf,watch]"
  python scripts/sync_mcp_server_json.py
  pytest tests/ -q

Use minor bumps (1.0.0 -> 1.1.0) for milestone-sized releases; patch for fixes only.

Usage:
  python scripts/bump_version.py <semver>
  python scripts/bump_version.py <semver> --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"

# Strict X.Y.Z (bump pre-release tags by editing pyproject.toml by hand if needed)
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_LINE_RE = re.compile(r'^version\s*=\s*"([^"]*)"\s*$', re.MULTILINE)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("version", help='New version, e.g. "1.1.0"')
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print old -> new and exit without writing",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    new_v = args.version.strip()
    if not _VERSION_RE.match(new_v):
        print(f"error: version must look like 1.2.3 (got {new_v!r})", file=sys.stderr)
        return 2

    text = _PYPROJECT.read_text(encoding="utf-8")
    m = _LINE_RE.search(text)
    if not m:
        print(f"error: no version = line found in {_PYPROJECT}", file=sys.stderr)
        return 2
    old_v = m.group(1)
    if old_v == new_v:
        print(f"already at {new_v}")
        return 0

    new_text = _LINE_RE.sub(f'version = "{new_v}"', text, count=1)
    print(f"{_PYPROJECT.relative_to(_REPO_ROOT)}: {old_v} -> {new_v}")
    if args.dry_run:
        return 0
    _PYPROJECT.write_text(new_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
