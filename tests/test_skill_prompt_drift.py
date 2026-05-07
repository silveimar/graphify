"""Drift gate (Phase 65 / Q4): every shipped skill*.md file must reference
the current PROMPT_VERSION substring from graphify.prompts.

Bumping PROMPT_VERSION in graphify/prompts.py without updating the skill
files is a regression — this test catches that.

Phase 72-02 extension: every skill*.md file must contain a byte-identical
reasoning-relations block (BEGIN/END-bounded), the ADR-0042 supersession
exemplar, the ADR contradiction exemplar, and PROMPT_VERSION must be
"1.14.0".
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from graphify.prompts import PROMPT_VERSION


SKILL_DIR = Path(__file__).resolve().parent.parent / "graphify"

REASONING_BLOCK_BEGIN = "<!-- BEGIN: phase-72-reas reasoning-relations block -->"
REASONING_BLOCK_END = "<!-- END: phase-72-reas reasoning-relations block -->"
_BLOCK_RE = re.compile(
    re.escape(REASONING_BLOCK_BEGIN) + r"(.*?)" + re.escape(REASONING_BLOCK_END),
    re.DOTALL,
)


def _skill_files() -> list[Path]:
    return sorted(SKILL_DIR.glob("skill*.md"))


def _extract_reasoning_block(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    m = _BLOCK_RE.search(text)
    return m.group(1) if m else None


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


def test_prompt_version_bumped():
    """Phase 72-02: PROMPT_VERSION must be 1.14.0 to invalidate the
    confidence cache after the reasoning-relation prompt extension shipped."""
    assert PROMPT_VERSION == "1.14.0", (
        f"PROMPT_VERSION expected '1.14.0' (Phase 72-02 cache invalidation), got {PROMPT_VERSION!r}"
    )


def test_reasoning_relations_block_parity():
    """Phase 72-02: every skill*.md file must contain a byte-identical
    reasoning-relations block bounded by phase-72-reas BEGIN/END markers."""
    files = _skill_files()
    blocks: dict[str, str | None] = {f.name: _extract_reasoning_block(f) for f in files}

    missing = [n for n, b in blocks.items() if b is None]
    assert not missing, (
        f"Skill files missing the phase-72-reas reasoning-relations block: {missing}"
    )

    reference_name = "skill.md"
    assert reference_name in blocks, "skill.md must be present as the canonical reference"
    reference = blocks[reference_name]
    drift = [n for n, b in blocks.items() if b != reference]
    assert not drift, (
        "Reasoning-relations block content drifted from skill.md in: "
        f"{drift}. The block must be byte-identical across all skill*.md files."
    )


def test_adr_supersession_exemplar_present():
    """Phase 72-02: every skill*.md must include the ADR-0042 supersession
    and ADR contradiction worked examples inside the BEGIN/END block."""
    for f in _skill_files():
        block = _extract_reasoning_block(f)
        assert block is not None, f"{f.name} missing reasoning-relations block"
        # Supersession exemplar (Worked example 1)
        assert "ADR-0042" in block, f"{f.name} block missing 'ADR-0042'"
        assert "ADR-0028" in block, f"{f.name} block missing 'ADR-0028'"
        assert "supersedes" in block, f"{f.name} block missing 'supersedes' relation"
        # Contradiction exemplar (Worked example 2)
        assert "adr_0050" in block, f"{f.name} block missing 'adr_0050' contradiction emit"
        assert "0050-revisit" in block, f"{f.name} block missing contradiction fragment"
        assert "contradicts" in block, f"{f.name} block missing 'contradicts' relation"
        # Orientation note
        assert "newer -> older" in block, f"{f.name} block missing supersedes orientation note"
        # All 5 relations present
        for rel in ("supports", "contradicts", "supersedes", "evolved_into", "depends_on"):
            assert rel in block, f"{f.name} block missing relation '{rel}'"
