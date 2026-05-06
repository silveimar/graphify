"""Snapshot test: locks the [graphify] error:/info:/hint: two-line stderr contract (AUDIT-02).

Golden fixture: tests/fixtures/stderr_contract.txt
Three sections (blank-line separated):
  section[0] -- error block (_emit_vault_error)
  section[1] -- info block (_emit_vault_info)
  section[2] -- option_b block (emit_option_b_breadcrumb)

D-04: strict prefix whitelist -- every non-empty line must match
  ^(\\[graphify\\] (error|info|hint): |  hint: )
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from graphify.output import (
    _emit_vault_error,
    _emit_vault_info,
    _reset_option_b_breadcrumb_for_tests,
    emit_option_b_breadcrumb,
)

# Load fixture once at module level — empty fixture causes immediate failure in tests.
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "stderr_contract.txt"
FIXTURE = FIXTURE_PATH.read_text(encoding="utf-8")

# Split into sections on blank lines (each section is one emitter's output).
_raw_sections = FIXTURE.split("\n\n")
SECTIONS = [s.strip("\n") for s in _raw_sections]

# Expecting exactly 3 sections: error, info, option_b.
SECTION_ERROR = SECTIONS[0] if len(SECTIONS) > 0 else ""
SECTION_INFO = SECTIONS[1] if len(SECTIONS) > 1 else ""
SECTION_OPTION_B = SECTIONS[2] if len(SECTIONS) > 2 else ""

# D-04 strict prefix whitelist regex.
_PREFIX_RE = re.compile(r"^(\[graphify\] (error|info|hint): |  hint: )")


def test_emit_vault_error_matches_snapshot(capsys: pytest.CaptureFixture[str]) -> None:
    """_emit_vault_error output must match section[0] of the golden fixture byte-exactly."""
    with pytest.raises(SystemExit):
        raise _emit_vault_error("vault refused: profile invalid", "fix profile.yaml")
    captured = capsys.readouterr().err.rstrip("\n")
    assert captured == SECTION_ERROR, (
        f"_emit_vault_error stderr mismatch.\n"
        f"Got:\n{captured!r}\n"
        f"Expected (from fixture section[0]):\n{SECTION_ERROR!r}"
    )


def test_emit_vault_info_matches_snapshot(capsys: pytest.CaptureFixture[str]) -> None:
    """_emit_vault_info output must match section[1] of the golden fixture byte-exactly."""
    _emit_vault_info("vault routing", "see docs")
    captured = capsys.readouterr().err.rstrip("\n")
    assert captured == SECTION_INFO, (
        f"_emit_vault_info stderr mismatch.\n"
        f"Got:\n{captured!r}\n"
        f"Expected (from fixture section[1]):\n{SECTION_INFO!r}"
    )


def test_emit_option_b_breadcrumb_matches_snapshot(capsys: pytest.CaptureFixture[str]) -> None:
    """emit_option_b_breadcrumb output lines must match section[2] of the golden fixture."""
    _reset_option_b_breadcrumb_for_tests()
    emit_option_b_breadcrumb(Path("/tmp/vault"))
    captured = capsys.readouterr().err.rstrip("\n")
    lines = [ln for ln in captured.splitlines() if ln]
    # All lines must start with [graphify] info: or   hint:
    for line in lines:
        assert line.startswith("[graphify] info:") or line.startswith("  hint:"), (
            f"Unexpected line prefix in Option B breadcrumb: {line!r}"
        )
    # First line must equal the first line of fixture section[2].
    fixture_first_line = SECTION_OPTION_B.splitlines()[0] if SECTION_OPTION_B else ""
    assert lines[0] == fixture_first_line if lines else True, (
        f"Option B first line mismatch.\n"
        f"Got: {lines[0]!r}\n"
        f"Expected (fixture section[2] line 1): {fixture_first_line!r}"
    )
    # Full output must match section[2] exactly.
    assert captured == SECTION_OPTION_B, (
        f"Option B breadcrumb stderr mismatch.\n"
        f"Got:\n{captured!r}\n"
        f"Expected (from fixture section[2]):\n{SECTION_OPTION_B!r}"
    )


def test_strict_prefix_whitelist(capsys: pytest.CaptureFixture[str]) -> None:
    """D-04: every non-empty line in all fixture sections must match the strict prefix whitelist.

    Allowed: '[graphify] error: ', '[graphify] info: ', '[graphify] hint: ', '  hint: '
    """
    all_lines = "\n".join([SECTION_ERROR, SECTION_INFO, SECTION_OPTION_B]).splitlines()
    non_empty = [ln for ln in all_lines if ln]
    assert non_empty, "Fixture is empty — populate tests/fixtures/stderr_contract.txt (GREEN task)"
    for line in non_empty:
        assert _PREFIX_RE.match(line), (
            f"Line violates D-04 strict prefix whitelist: {line!r}\n"
            f"Allowed prefixes: '[graphify] error: ', '[graphify] info: ', "
            f"'[graphify] hint: ', '  hint: '"
        )
