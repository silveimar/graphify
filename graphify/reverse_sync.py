from __future__ import annotations
"""Vault → Input reverse-sync (Phase 70 / VRSYNC-01).

Detection-only module surface in this file (Plan 02). Mode dispatch + prompt
UX (Plan 03), JSONL audit log (Plan 04), and auto_on_run hook (Plan 05) layer
on top.

NOTE: Do NOT use graphify.cache.file_hash() here — it strips frontmatter for
.md files (cache.py:_body_content), which is the wrong semantic for sync.
Reverse-sync compares raw file bytes so frontmatter-only edits are detected.
"""

import difflib
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
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


# ---------------------------------------------------------------------------
# Plan 03: mode dispatch + prompt UX + apply step.
# ---------------------------------------------------------------------------


def _diff_summary(a: bytes, b: bytes) -> str:
    """Compact stats string for JSONL log (D-03). +N -M lines, +A -B bytes.

    a = old (input-side), b = new (vault-side). Wired by Plan 04; defined here
    so the module surface is complete.
    """
    a_lines = a.decode("utf-8", errors="replace").splitlines()
    b_lines = b.decode("utf-8", errors="replace").splitlines()
    diff = list(difflib.ndiff(a_lines, b_lines))
    plus_lines = sum(1 for d in diff if d.startswith("+ "))
    minus_lines = sum(1 for d in diff if d.startswith("- "))
    plus_bytes = max(0, len(b) - len(a))
    minus_bytes = max(0, len(a) - len(b))
    return f"+{plus_lines} -{minus_lines} lines, +{plus_bytes} -{minus_bytes} bytes"


def _append_jsonl(path: Path, record: dict) -> None:
    """Append a single record as a JSON line to *path* (D-15 append-only).

    Mirrors graphify.serve._append_annotation pattern verbatim.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _make_log_record(
    change: ChangeRecord,
    action: str,
    *,
    vault_text: bytes | None,
    input_text: bytes | None,
) -> dict:
    """Build a 7-key JSONL record for a single reverse-sync event (D-14)."""
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if vault_text is None and input_text is None:
        diff = ""
    else:
        diff = _diff_summary(input_text or b"", vault_text or b"")
    return {
        "ts": ts,
        "vault_path": str(change.vault_path),
        "input_path": str(change.input_path),
        "action": action,
        "diff_summary": diff,
        "hash_before": change.hash_before,
        "hash_after": change.hash_after,
    }


def prompt_per_file(rel: str, vault_text: str, input_text: str | None) -> str:
    """Interactive Y/n/d/A/Q prompt (D-01, D-02). TTY-gated (D-13).

    Returns one of: "yes", "no", "all", "quit", "skip".
    "skip" is returned in non-TTY environments (D-13) — caller must treat as
    skipped_conflict (NOT an auto-accept).
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return "skip"
    while True:
        try:
            ans = input(f"[graphify] reverse-sync {rel} [Y/n/d/A/Q]: ").strip()
        except EOFError:
            return "skip"
        low = ans.lower()
        if low in ("", "y", "yes"):
            return "yes"
        if low in ("n", "no"):
            return "no"
        if low in ("a", "all"):
            return "all"
        if low in ("q", "quit"):
            return "quit"
        if low in ("d", "diff"):
            old = (input_text or "").splitlines(keepends=True)
            new = vault_text.splitlines(keepends=True)
            sys.stdout.writelines(
                difflib.unified_diff(old, new, fromfile=f"input/{rel}", tofile=f"vault/{rel}")
            )
            sys.stdout.write("\n")
            sys.stdout.flush()
            continue
        # unknown → re-prompt


def _atomic_copy(src: Path, dst: Path) -> None:
    """Atomic copy via temp + os.replace. Mirrors merge.py / vault_promote pattern."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_bytes(src.read_bytes())
    os.replace(tmp, dst)


def _validate_input_path(input_dir: Path, target: Path) -> bool:
    """Confine *target* to inside *input_dir* (security V4)."""
    return _is_within(target, input_dir)


def apply_change(
    rec: ChangeRecord,
    *,
    mode: str,
    all_yes: bool,
    input_dir: Path,
) -> tuple[str, bool]:
    """Apply one ChangeRecord according to *mode* and *all_yes*.

    Returns (outcome, new_all_yes) where outcome is one of:
      "copied", "skipped_user", "skipped_conflict", "skipped_never_copy",
      "vault_deleted", "quit", "skip" (kind == "skip" — no-op).
    """
    if rec.kind == "skip":
        return ("skip", all_yes)
    if rec.kind == "vault_deleted":
        # D-10: log only, never silently delete in this layer.
        return ("vault_deleted", all_yes)

    # Path-confinement (security V4) before any write.
    if not _validate_input_path(input_dir, rec.input_path):
        print(
            f"[graphify] reverse-sync: refusing target outside input_path: {rec.rel_path}",
            file=sys.stderr,
        )
        return ("skipped_conflict", all_yes)

    if mode == "never_copy":
        return ("skipped_never_copy", all_yes)
    if mode == "always_copy":
        _atomic_copy(rec.vault_path, rec.input_path)
        return ("copied", all_yes)
    # always_ask
    if all_yes:
        _atomic_copy(rec.vault_path, rec.input_path)
        return ("copied", all_yes)
    vault_text = rec.vault_path.read_text(encoding="utf-8", errors="replace")
    input_text = (
        rec.input_path.read_text(encoding="utf-8", errors="replace")
        if rec.input_path.exists() else None
    )
    resp = prompt_per_file(rec.rel_path, vault_text, input_text)
    if resp == "yes":
        _atomic_copy(rec.vault_path, rec.input_path)
        return ("copied", all_yes)
    if resp == "no":
        return ("skipped_user", all_yes)
    if resp == "all":
        _atomic_copy(rec.vault_path, rec.input_path)
        return ("copied", True)
    if resp == "quit":
        return ("quit", all_yes)
    # "skip" (non-TTY, D-13)
    return ("skipped_conflict", all_yes)


def run_reverse_sync(
    vault_dir: Path,
    *,
    input_dir_override: Path | None = None,
    mode_override: str | None = None,
    yes: bool = False,
    auto_on_run: bool = False,
) -> dict:
    """Top-level reverse-sync entry point. Plan 03 implementation.

    JSONL audit log layered in Plan 04; auto-on-run hook layered in Plan 05.
    """
    from graphify.profile import load_profile

    profile = load_profile(vault_dir)
    # Ensure the resolved profile points at *this* vault and the desired input.
    profile = dict(profile)
    profile["vault_path"] = str(vault_dir)
    if input_dir_override is not None:
        profile["input_path"] = str(input_dir_override)
    rs_cfg = profile.get("reverse_sync") or {}
    mode = mode_override or rs_cfg.get("mode") or "always_ask"
    if mode not in ("always_ask", "always_copy", "never_copy"):
        print(
            f"[graphify] reverse-sync: unknown mode '{mode}', defaulting to always_ask",
            file=sys.stderr,
        )
        mode = "always_ask"

    input_dir = Path(profile["input_path"])
    changes = compute_change_set(profile)

    # Plan 04: resolve JSONL log path (D-15 default + memory_path override).
    memory_rel = rs_cfg.get("memory_path") or ".graphify/reverse-sync-log.jsonl"
    log_path = (vault_dir / memory_rel).resolve()
    # Path-confine log inside vault_dir (security).
    if not _is_within(log_path, vault_dir):
        print(
            f"[graphify] reverse-sync: refusing log path outside vault: {memory_rel}",
            file=sys.stderr,
        )
        log_path = (vault_dir / ".graphify" / "reverse-sync-log.jsonl").resolve()

    counters = {
        "copied": 0,
        "skipped_user": 0,
        "skipped_conflict": 0,
        "skipped_never_copy": 0,
        "vault_deleted": 0,
    }
    # D-12: --yes flips always_ask only.
    all_yes = bool(yes) and mode == "always_ask"

    for rec in changes:
        outcome, all_yes = apply_change(
            rec, mode=mode, all_yes=all_yes, input_dir=input_dir
        )
        if outcome == "skip":
            # D-14: kind=="skip" (unchanged file) is NOT a sync event; do not log.
            continue
        if outcome == "quit":
            break

        # Plan 70-08: per-record stdout summary (operator visibility).
        if outcome in (
            "copied",
            "skipped_user",
            "skipped_conflict",
            "skipped_never_copy",
            "vault_deleted",
        ):
            print(f"[graphify] reverse-sync: {outcome} {rec.rel_path}")

        # Plan 04: log every detected change-set decision.
        try:
            vault_bytes = (
                rec.vault_path.read_bytes()
                if rec.vault_path.exists() and rec.vault_path.is_file()
                else None
            )
        except OSError:
            vault_bytes = None
        try:
            input_bytes = (
                rec.input_path.read_bytes()
                if rec.input_path.exists() and rec.input_path.is_file()
                else None
            )
        except OSError:
            input_bytes = None
        # For "copied" action, input_bytes was just (over)written with vault_bytes;
        # diff_summary should reflect the pre-copy delta. For "copied" via apply_change,
        # the input file equals vault now — pass None for input_text when hash_before
        # is None (new file) so diff is "+N -0".
        log_input = input_bytes
        if outcome == "copied" and rec.hash_before is None:
            log_input = None
        _append_jsonl(
            log_path,
            _make_log_record(rec, outcome, vault_text=vault_bytes, input_text=log_input),
        )

        if outcome in counters:
            counters[outcome] += 1

    # Plan 70-08: final totals line (always emitted).
    print(
        f"[graphify] reverse-sync: totals "
        f"copied={counters['copied']} "
        f"skipped_user={counters['skipped_user']} "
        f"skipped_conflict={counters['skipped_conflict']} "
        f"skipped_never_copy={counters['skipped_never_copy']} "
        f"vault_deleted={counters['vault_deleted']}"
    )

    result = dict(counters)
    result["conflicts_skipped"] = counters["skipped_conflict"]
    result["failed"] = False
    result["log_path"] = str(log_path)
    return result


__all__ = [
    "ChangeRecord",
    "ChangeKind",
    "compute_change_set",
    "run_reverse_sync",
    "prompt_per_file",
    "apply_change",
    "_validate_input_path",
    "_diff_summary",
    "_append_jsonl",
    "_make_log_record",
]
