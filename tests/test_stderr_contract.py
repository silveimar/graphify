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


def test_no_outlier_stderr_prefixes_in_source() -> None:
    """D-04 grep invariant: every print(..., file=sys.stderr) in graphify/ must use a compliant prefix.

    Allowed literal prefixes in the print argument:
      '[graphify] error: '   (plain or f-string)
      '[graphify] info: '    (plain or f-string)
      '  hint: '             (plain or f-string, two leading spaces)

    The single whitelisted exception is graphify/output.py whose raw
    '[graphify] {msg}' form is wrapped by the emit_* functions tested above.
    """
    import subprocess
    import re as _re
    repo = Path(__file__).resolve().parents[1]
    # AUDIT-02 / D-02: the previous regex used `[^)]*file=sys\.stderr` and stopped
    # at the first `)`, so single-line calls like
    #   print(f"[graphify] Extraction warning ({len(x)} issues): ...", file=sys.stderr)
    # slipped past undetected because the inner `)` of `len(x)` / `(... issues)`
    # terminated the character class. Use a greedy `.*` instead — every print(
    # call we care about is on a single line, and grep matches per-line, so
    # `.*file=sys.stderr` correctly walks across nested parens within the line.
    pattern = r"print\(.*file=sys\.stderr"
    out = subprocess.check_output(
        ["grep", "-rEn", pattern, "graphify/", "--include=*.py"],
        cwd=repo, text=True,
    )
    allowed = _re.compile(r'(f?"\[graphify\] (error|info|hint): |f?"  hint: )')
    offenders = []
    for line in out.splitlines():
        path = line.split(":", 1)[0]
        if path == "graphify/output.py":
            continue
        if not allowed.search(line):
            offenders.append(line)
    assert not offenders, "Non-compliant stderr prefixes found:\n" + "\n".join(offenders)


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


# ============================================================================
# Phase 66 — federation error breadcrumbs (CFED Plan 03)
# Both error paths reuse `_emit_vault_error`, so they conform to D-04 by
# construction. These tests pin the exact wording so reformulation drift is
# caught alongside the vault-routing snapshots.
# ============================================================================

def test_federation_missing_peer_breadcrumb(capsys: pytest.CaptureFixture[str]) -> None:
    """Missing peer breadcrumb: `[graphify] error: peer export not found at <p>` + hint."""
    peer_path = "/tmp/__nonexistent__/graphify-out/graph.json"
    with pytest.raises(SystemExit):
        raise _emit_vault_error(
            f"peer export not found at {peer_path}",
            "run `graphify run` in the peer repo first",
        )
    captured = capsys.readouterr().err.rstrip("\n")
    expected = (
        f"[graphify] error: peer export not found at {peer_path}\n"
        f"  hint: run `graphify run` in the peer repo first"
    )
    assert captured == expected
    # D-04 prefix whitelist applies.
    for line in captured.splitlines():
        assert _PREFIX_RE.match(line), f"federation missing-peer line violates D-04: {line!r}"


def test_federation_collision_breadcrumb(capsys: pytest.CaptureFixture[str]) -> None:
    """Collision breadcrumb: `[graphify] error: duplicate peer repo basename '<n>'` + hint."""
    with pytest.raises(SystemExit):
        raise _emit_vault_error(
            "duplicate peer repo basename 'repo'",
            "rename one peer directory or use distinct paths",
        )
    captured = capsys.readouterr().err.rstrip("\n")
    expected = (
        "[graphify] error: duplicate peer repo basename 'repo'\n"
        "  hint: rename one peer directory or use distinct paths"
    )
    assert captured == expected
    for line in captured.splitlines():
        assert _PREFIX_RE.match(line), f"federation collision line violates D-04: {line!r}"
