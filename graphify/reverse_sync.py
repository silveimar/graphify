from __future__ import annotations
"""Vault → Input reverse-sync (Phase 70 / VRSYNC-01).

Detection-only module surface in this file (Plan 02). Mode dispatch + prompt
UX (Plan 03), JSONL audit log (Plan 04), and auto_on_run hook (Plan 05) layer
on top.

NOTE: Do NOT use graphify.cache.file_hash() here — it strips frontmatter for
.md files (cache.py:_body_content), which is the wrong semantic for sync.
Reverse-sync compares raw file bytes so frontmatter-only edits are detected.
"""

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ChangeKind = Literal["new", "update", "skip", "vault_deleted"]


@dataclass(frozen=True)
class ChangeRecord:
    rel_path: str
    vault_path: Path
    input_path: Path
    kind: ChangeKind
    hash_before: str | None
    hash_after: str | None


def _raw_sha256(path: Path) -> str:
    """SHA-256 of raw file bytes (mirrors vault_promote._hash_bytes / merge._content_hash).

    Intentionally distinct from graphify.cache.file_hash, which strips Markdown
    frontmatter and would misclassify frontmatter-only edits as 'skip'.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_within(child: Path, parent: Path) -> bool:
    """Return True if resolved *child* is under resolved *parent* (symlink-safe)."""
    try:
        child_r = child.resolve()
        parent_r = parent.resolve()
    except OSError:
        return False
    try:
        child_r.relative_to(parent_r)
        return True
    except ValueError:
        return False


def _iter_md_files(root: Path) -> list[Path]:
    """Recursively collect *.md files under *root* (D-09). Empty list if missing."""
    if not root.exists() or not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def compute_change_set(profile: dict) -> list[ChangeRecord]:
    """Classify markdown files in profile.user_only_folders as new/update/skip/vault_deleted.

    D-08: scope is exactly profile.user_only_folders (recursive).
    D-09: only *.md files; subdir structure mirrored to input tree.
    D-10: input-side files absent from vault are emitted as 'vault_deleted'
          (logged only — deletion mirroring happens later, never silently here).

    Returns a list sorted by rel_path for deterministic ordering. Side-effect-free.
    """
    vault_dir = Path(profile["vault_path"])
    input_dir = Path(profile["input_path"])
    folders: list[str] = list(profile.get("user_only_folders", []) or [])

    records: list[ChangeRecord] = []
    seen_rel: set[str] = set()

    for folder in folders:
        vault_root = vault_dir / folder
        input_root = input_dir / folder

        # Forward pass: vault → input classification (new / update / skip).
        for vault_md in _iter_md_files(vault_root):
            try:
                rel = vault_md.relative_to(vault_dir)
            except ValueError:
                continue
            rel_str = rel.as_posix()
            input_target = input_dir / rel

            # Path-safety: refuse traversal outside input_dir.
            if not _is_within(input_target, input_dir):
                print(
                    f"[graphify] reverse-sync: refusing path outside input root: {rel_str}",
                    file=sys.stderr,
                )
                continue

            hash_after = _raw_sha256(vault_md)
            if input_target.exists() and input_target.is_file():
                hash_before: str | None = _raw_sha256(input_target)
                kind: ChangeKind = "skip" if hash_before == hash_after else "update"
            else:
                hash_before = None
                kind = "new"

            records.append(
                ChangeRecord(
                    rel_path=rel_str,
                    vault_path=vault_md,
                    input_path=input_target,
                    kind=kind,
                    hash_before=hash_before,
                    hash_after=hash_after,
                )
            )
            seen_rel.add(rel_str)

        # Reverse pass: input-side files with no vault counterpart → vault_deleted (D-10).
        for input_md in _iter_md_files(input_root):
            try:
                rel = input_md.relative_to(input_dir)
            except ValueError:
                continue
            rel_str = rel.as_posix()
            if rel_str in seen_rel:
                continue
            vault_target = vault_dir / rel
            if vault_target.exists() and vault_target.is_file():
                # Should already have been picked up in forward pass; defensive skip.
                continue
            if not _is_within(input_md, input_dir):
                continue
            records.append(
                ChangeRecord(
                    rel_path=rel_str,
                    vault_path=vault_target,
                    input_path=input_md,
                    kind="vault_deleted",
                    hash_before=_raw_sha256(input_md),
                    hash_after=None,
                )
            )
            seen_rel.add(rel_str)

    records.sort(key=lambda r: r.rel_path)
    return records


__all__ = ["ChangeRecord", "ChangeKind", "compute_change_set"]
