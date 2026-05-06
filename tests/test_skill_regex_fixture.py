"""Tests for skill_stderr_regexes.yaml — validates each platform's stderr contract regex."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

FIXTURE_DIR = Path(__file__).parent / "fixtures"
YAML_FIXTURE = FIXTURE_DIR / "skill_stderr_regexes.yaml"
CONTRACT_FIXTURE = FIXTURE_DIR / "stderr_contract.txt"

EXPECTED_PLATFORMS = {
    "claude-code",
    "codex",
    "opencode",
    "openclaw",
    "factory-droid",
    "trae",
    "trae-cn",
}


def _load_fixture() -> dict:
    with YAML_FIXTURE.open() as fh:
        return yaml.safe_load(fh)


def _contract_lines() -> list[str]:
    return CONTRACT_FIXTURE.read_text().splitlines()


def test_all_seven_platforms_present() -> None:
    """Fixture must contain exactly 7 platform keys — no more, no less."""
    data = _load_fixture()
    assert set(data.keys()) == EXPECTED_PLATFORMS, (
        f"Platform key mismatch.\n"
        f"  Expected: {sorted(EXPECTED_PLATFORMS)}\n"
        f"  Got:      {sorted(data.keys())}"
    )


def test_each_regex_compiles() -> None:
    """Each platform's regex value must be a non-empty, compilable Python pattern."""
    data = _load_fixture()
    errors: list[str] = []
    for platform, pattern in data.items():
        if not isinstance(pattern, str) or len(pattern) == 0:
            errors.append(f"{platform}: empty or non-string regex")
            continue
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(f"{platform}: invalid regex — {exc}")
    if errors:
        pytest.fail("Regex compilation failures:\n" + "\n".join(f"  - {e}" for e in errors))


def test_each_regex_matches_locked_contract() -> None:
    """Each platform's regex must match at least one line of the locked stderr_contract.txt."""
    data = _load_fixture()
    lines = _contract_lines()
    mismatches: list[str] = []
    for platform, pattern in data.items():
        if not isinstance(pattern, str) or len(pattern) == 0:
            mismatches.append(f"{platform}: empty regex — cannot match any line")
            continue
        try:
            compiled = re.compile(pattern)
        except re.error:
            mismatches.append(f"{platform}: invalid regex (see test_each_regex_compiles)")
            continue
        if not any(compiled.search(line) for line in lines):
            mismatches.append(
                f"{platform}: regex {pattern!r} matched 0 lines in stderr_contract.txt"
            )
    if mismatches:
        pytest.fail(
            "Regexes that match no lines in the locked contract:\n"
            + "\n".join(f"  - {m}" for m in mismatches)
        )
