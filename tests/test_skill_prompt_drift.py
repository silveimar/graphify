"""Drift gate (Phase 65 / Q4): every shipped skill*.md file must reference
the current PROMPT_VERSION substring from graphify.prompts.

Bumping PROMPT_VERSION in graphify/prompts.py without updating the skill
files is a regression — this test catches that.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from graphify.prompts import PROMPT_VERSION


SKILL_DIR = Path(__file__).resolve().parent.parent / "graphify"


def _skill_files() -> list[Path]:
    return sorted(SKILL_DIR.glob("skill*.md"))


def test_skill_files_present():
    files = _skill_files()
    assert len(files) >= 7, f"expected at least 7 skill files, found {len(files)}: {files}"


@pytest.mark.parametrize("skill_path", _skill_files(), ids=lambda p: p.name)
def test_skill_files_reference_prompt_version(skill_path):
    content = skill_path.read_text(encoding="utf-8")
    assert PROMPT_VERSION in content, (
        f"Skill file {skill_path.name} does not reference PROMPT_VERSION={PROMPT_VERSION!r}. "
        "Update the skill file when bumping graphify/prompts.py:PROMPT_VERSION."
    )
