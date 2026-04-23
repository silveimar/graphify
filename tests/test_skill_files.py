"""Tests for Phase 11 D-16: all skill file variants must expose the slash-command discoverability section.

This test file is intentionally self-contained. It does NOT import tests/test_commands.py
(which is created by plan 11-04 in the same wave). Independence preserves parallel wave
execution — plan-checker WARNING 1 fix.
"""
from __future__ import annotations
from pathlib import Path

import graphify


PRIMARY_SKILL = "skill.md"
PLATFORM_VARIANTS = (
    "skill-codex.md",
    "skill-opencode.md",
    "skill-aider.md",
    "skill-copilot.md",
    "skill-claw.md",
    "skill-droid.md",
    "skill-trae.md",
    "skill-windows.md",
)
CORE_COMMANDS = ("/context", "/trace", "/connect", "/drift", "/emerge")
HEADING = "## Available slash commands"


def _read(name: str) -> str:
    return (Path(graphify.__file__).parent / name).read_text(encoding="utf-8")


def test_primary_skill_file_lists_available_commands():
    text = _read(PRIMARY_SKILL)
    assert HEADING in text, f"{PRIMARY_SKILL} missing '{HEADING}' heading"
    for cmd in CORE_COMMANDS:
        assert cmd in text, f"{PRIMARY_SKILL} missing reference to {cmd}"


def test_platform_variant_skill_files_list_available_commands():
    for variant in PLATFORM_VARIANTS:
        text = _read(variant)
        assert HEADING in text, f"{variant} missing '{HEADING}' heading"
        for cmd in CORE_COMMANDS:
            assert cmd in text, f"{variant} missing reference to {cmd}"


def test_skill_files_discoverability_section_is_consistent():
    # All 9 files must use the exact same heading text — detect drift early
    all_files = (PRIMARY_SKILL,) + PLATFORM_VARIANTS
    headings = {f: (HEADING in _read(f)) for f in all_files}
    missing = [f for f, present in headings.items() if not present]
    assert not missing, f"Heading '{HEADING}' missing from: {missing}"
