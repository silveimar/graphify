"""Documentation contract tests for v1.8 migration guidance."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MIGRATION_GUIDE = ROOT / "docs" / "MIGRATION_V1_8.md"
README = ROOT / "README.md"
DOC_CONTRACT_FILES = (MIGRATION_GUIDE, README)
LOCALIZED_READMES = {
    "README.ja-JP.md",
    "README.ko-KR.md",
    "README.zh-CN.md",
}

GUIDE_REQUIRED_PHRASES = (
    "graphify update-vault --input work-vault/raw --vault ls-vault",
    "Back up the target vault before apply",
    "Review the migration plan before apply",
    "graphify-out/migrations/archive/",
    "Rollback immediately after apply/archive if needed",
    "Rerun graphify after reviewing the archive",
)

README_REQUIRED_PHRASES = (
    "MIGRATION_V1_8.md",
    "graphify update-vault --input <raw-corpus> --vault <target-vault>",
    "preview is the default",
    "--apply --plan-id <id>",
    "graphify-out/migrations/archive/",
    "does not destructively delete legacy notes",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v18_migration_guide_contains_required_phrases():
    text = _read(MIGRATION_GUIDE)

    for phrase in GUIDE_REQUIRED_PHRASES:
        assert phrase in text


def test_v18_migration_guide_orders_backup_and_rollback():
    text = _read(MIGRATION_GUIDE)

    backup = text.index("Back up the target vault before apply")
    apply_command = text.index("--apply --plan-id")
    apply_section = text.index("Apply and archive")
    rollback = text.index("Rollback immediately after apply/archive if needed")
    rerun = text.index("Rerun graphify after reviewing the archive")

    assert backup < apply_command
    assert apply_section < rollback < rerun


def test_v18_docs_contract_is_english_only():
    contract_names = {path.name for path in DOC_CONTRACT_FILES}

    assert not contract_names & LOCALIZED_READMES


def test_readme_links_v18_migration_guide_and_update_vault_contract():
    text = _read(README)

    for phrase in README_REQUIRED_PHRASES:
        assert phrase in text
