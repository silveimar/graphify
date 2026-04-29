"""Tests for Phase 11 D-16: all skill file variants must expose the slash-command discoverability section.

This test file is intentionally self-contained. It does NOT import tests/test_commands.py
(which is created by plan 11-04 in the same wave). Independence preserves parallel wave
execution — plan-checker WARNING 1 fix.
"""
from __future__ import annotations

import re
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
REQUIRED_V18_OBSIDIAN_PHRASES = (
    "MOC-only community output",
    "Graphify-owned v1.8 subtree",
    "preview-first update-vault",
    "graphify update-vault --input work-vault/raw --vault ls-vault",
    "Back up the target vault before apply",
    "graphify-out/migrations/archive/",
    "no destructive deletion",
)
FORBIDDEN_V18_OBSIDIAN_PHRASES = (
    "generates _COMMUNITY_",
    "generates `_COMMUNITY_",
    "_COMMUNITY_* overview notes are generated",
    "_COMMUNITY_* overview notes are created",
)
FORBIDDEN_V18_OBSIDIAN_PATTERNS = (
    re.compile(r"_COMMUNITY_\*.*overview notes", re.IGNORECASE),
    re.compile(r"_COMMUNITY_\*.*dataview queries", re.IGNORECASE),
    re.compile(r"print\(.*_COMMUNITY_", re.IGNORECASE),
)


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


def test_skill_files_share_v18_obsidian_contract_phrases():
    all_files = (PRIMARY_SKILL,) + PLATFORM_VARIANTS
    for skill_file in all_files:
        text = _read(skill_file)
        missing = [
            phrase for phrase in REQUIRED_V18_OBSIDIAN_PHRASES
            if phrase not in text
        ]
        assert not missing, f"{skill_file} missing v1.8 Obsidian phrases: {missing}"


def test_skill_files_forbid_stale_generated_community_claims():
    all_files = (PRIMARY_SKILL,) + PLATFORM_VARIANTS
    for skill_file in all_files:
        text = _read(skill_file)
        stale_phrases = [
            phrase for phrase in FORBIDDEN_V18_OBSIDIAN_PHRASES
            if phrase in text
        ]
        stale_patterns = [
            pattern.pattern for pattern in FORBIDDEN_V18_OBSIDIAN_PATTERNS
            if pattern.search(text)
        ]
        found = stale_phrases + stale_patterns
        assert not found, f"{skill_file} contains stale v1.8 Obsidian claims: {found}"
