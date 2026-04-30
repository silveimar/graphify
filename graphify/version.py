"""Installed ``graphifyy`` distribution version (single source of truth)."""

from __future__ import annotations


def package_version() -> str:
    """Return the installed PyPI ``graphifyy`` version string, or ``\"unknown\"``."""
    try:
        from importlib.metadata import version

        return version("graphifyy")
    except Exception:
        return "unknown"
