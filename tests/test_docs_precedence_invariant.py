"""Invariant test: canonical output destination precedence string (D-08, VFIX-02).

This test guards against drift between docs and runtime precedence. The runtime
source of truth lives in ``graphify/__main__.py`` (around line 2021) and reads:

    --output > profile > option-b (vault) > --obsidian-dir > legacy default

Every doc surface that mentions output precedence MUST contain this exact
substring verbatim. If this test fails, update the docs (not the test) — unless
the runtime precedence itself changed, in which case update both this test and
all 9 doc sites in lockstep.
"""

from __future__ import annotations

from pathlib import Path

CANONICAL = "--output > profile > option-b (vault) > --obsidian-dir > legacy default"

REPO_ROOT = Path(__file__).resolve().parents[1]

SITES = [
    "README.md",
    "graphify/__main__.py",
    "graphify/skill.md",
    "graphify/skill-codex.md",
    "graphify/skill-opencode.md",
    "graphify/skill-claw.md",
    "graphify/skill-droid.md",
    "graphify/skill-trae.md",
    "graphify/skill-windows.md",
]


def test_canonical_precedence_string_present_in_all_doc_sites() -> None:
    missing: list[str] = []
    for rel in SITES:
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8")
        if CANONICAL not in text:
            missing.append(rel)
    assert not missing, (
        "Canonical precedence string missing from doc site(s):\n  - "
        + "\n  - ".join(missing)
        + f"\n\nExpected verbatim substring:\n  {CANONICAL}\n"
        "Source of truth: graphify/__main__.py (D-08 comment near ResolvedOutput precedence)."
    )


def test_main_help_contains_canonical_string_at_least_twice() -> None:
    """Both --help blocks (around lines 1746 and 1767) must carry the canonical string."""
    text = (REPO_ROOT / "graphify/__main__.py").read_text(encoding="utf-8")
    count = text.count(CANONICAL)
    assert count >= 2, (
        f"Expected canonical precedence string to appear >= 2 times in "
        f"graphify/__main__.py (both --help blocks), found {count}."
    )
