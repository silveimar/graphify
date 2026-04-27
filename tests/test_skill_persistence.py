"""Tests for the mandatory dual-artifact persistence contract block (Phase 25).

Two enforcement guards:

1. ``test_install_emits_persistence_canary`` — parametrized over every
   in-scope ``_PLATFORM_CONFIG`` entry. Mocks ``Path.home()`` to ``tmp_path``,
   runs ``graphify install <platform>``, then byte-asserts the sentinel
   ``<!-- graphify:persistence-contract:v1 -->`` is present in the emitted
   ``skill_dst``. This is the "is the contract reaching the install
   destination?" canary.

2. ``test_persistence_block_byte_equal_across_variants`` — reads each of
   the 9 in-scope source ``skill*.md`` files from the package directory,
   slices each from the sentinel up to (but not including) the next
   ``## `` heading, and asserts every slice is byte-identical to the slice
   from ``skill.md``. This is the "are all variants in lockstep?" drift
   lock that fails loudly on any future per-platform paraphrase.

The list of in-scope platforms is derived AT RUNTIME from
``graphify.__main__._PLATFORM_CONFIG`` (excluding ``excalidraw``, which is
a separate skill surface per Phase 25 CONTEXT.md decision D-04). This
ensures the test cannot drift if a new platform is added or renamed in
production without explicitly opting it in or out.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from graphify.__main__ import _PLATFORM_CONFIG


SENTINEL = "<!-- graphify:persistence-contract:v1 -->"

# IN_SCOPE_PLATFORMS is derived at runtime from graphify._PLATFORM_CONFIG
# so the test cannot drift if a new platform is added or renamed.
IN_SCOPE_PLATFORMS = sorted(k for k in _PLATFORM_CONFIG if k != "excalidraw")

IN_SCOPE_SKILL_FILES = [
    "skill.md",
    "skill-aider.md",
    "skill-claw.md",
    "skill-codex.md",
    "skill-copilot.md",
    "skill-droid.md",
    "skill-opencode.md",
    "skill-trae.md",
    "skill-windows.md",
]


# Sanity check at collection time: _PLATFORM_CONFIG must still contain the
# 12 expected keys (11 in-scope + excalidraw). If this fails, somebody added
# or removed a platform and the test author needs to make a deliberate
# inclusion/exclusion decision rather than silently under-covering.
assert len(IN_SCOPE_PLATFORMS) == 11, (
    f"Expected 11 in-scope platforms (12 _PLATFORM_CONFIG entries minus "
    f"'excalidraw'); got {len(IN_SCOPE_PLATFORMS)}: {IN_SCOPE_PLATFORMS}. "
    f"_PLATFORM_CONFIG keys: {sorted(_PLATFORM_CONFIG)}"
)


def _pkg_dir() -> Path:
    """Return the on-disk path of the installed graphify package."""
    import graphify

    return Path(graphify.__file__).parent


def _extract_block(text: str) -> str:
    """Return the persistence contract block from ``text``.

    The block is the byte slice starting at ``SENTINEL`` (inclusive) and
    ending immediately before the next line that starts with ``## ``.
    Returns an empty string if the sentinel is absent — this is the failure
    signal the canary tests rely on.
    """
    start = text.find(SENTINEL)
    if start == -1:
        return ""
    # Find next "## " heading after the sentinel. Anchor on a leading
    # newline so we don't match the heading the sentinel itself precedes
    # being part of the slice.
    match = re.search(r"\n## ", text[start + len(SENTINEL) :])
    if match is None:
        # No subsequent heading — return everything after the sentinel.
        return text[start:]
    end = start + len(SENTINEL) + match.start()
    return text[start:end]


def _install(tmp_path: Path, platform: str) -> None:
    """Mirror the ``_install`` helper from ``tests/test_install.py``."""
    from graphify.__main__ import install

    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)


@pytest.mark.parametrize("platform", IN_SCOPE_PLATFORMS)
def test_install_emits_persistence_canary(tmp_path: Path, platform: str) -> None:
    """SKILLMEM-04: every emitted skill carries the persistence canary."""
    _install(tmp_path, platform)
    cfg = _PLATFORM_CONFIG[platform]
    emitted = tmp_path / cfg["skill_dst"]
    assert emitted.exists(), f"{platform}: skill not emitted at {emitted}"
    installed_bytes = emitted.read_bytes()
    assert SENTINEL.encode("utf-8") in installed_bytes, (
        f"{platform}: persistence canary {SENTINEL!r} missing from {emitted}"
    )


def test_persistence_block_byte_equal_across_variants() -> None:
    """SKILLMEM-02: contract block must be byte-identical across all 9 variants."""
    pkg = _pkg_dir()
    blocks: dict[str, str] = {}
    for name in IN_SCOPE_SKILL_FILES:
        path = pkg / name
        assert path.exists(), f"in-scope skill source missing from package: {path}"
        text = path.read_text(encoding="utf-8")
        blocks[name] = _extract_block(text)

    # Every block must be non-empty (sentinel present + body present).
    empty = [name for name, block in blocks.items() if block == ""]
    assert not empty, (
        f"persistence sentinel {SENTINEL!r} not found in: {empty}"
    )

    # All blocks must equal the master skill.md slice.
    reference = blocks["skill.md"]
    divergent = [
        name for name, block in blocks.items() if block != reference
    ]
    assert not divergent, (
        f"persistence block drift detected — these variants do not match "
        f"graphify/skill.md byte-for-byte: {divergent}"
    )
