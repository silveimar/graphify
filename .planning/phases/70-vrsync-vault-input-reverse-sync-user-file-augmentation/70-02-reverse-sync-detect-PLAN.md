---
phase: 70
plan: 02
type: tdd
wave: 1
depends_on: []
files_modified:
  - graphify/reverse_sync.py
  - tests/test_reverse_sync.py
  - tests/fixtures/vault_with_user_folders/.gitkeep
autonomous: true
requirements: [VRSYNC-01]
must_haves:
  truths:
    - "Reverse-sync detects new/changed/skip/vault_deleted classes via raw-bytes SHA256 (Success Criterion 1)"
    - "Scan scope is exactly profile.user_only_folders, recursive, *.md only (D-08, D-09)"
    - "Subdirectory structure is mirrored when copying vault → input (D-09)"
    - "cache.file_hash() is NOT used for change detection (Pitfall 1)"
  artifacts:
    - path: "graphify/reverse_sync.py"
      provides: "compute_change_set(), _raw_sha256(), ChangeRecord dataclass"
      exports: ["compute_change_set", "ChangeRecord"]
    - path: "tests/test_reverse_sync.py"
      provides: "Detection unit tests covering D-08..D-10"
  key_links:
    - from: "graphify/reverse_sync.py"
      to: "filesystem"
      via: "hashlib.sha256(path.read_bytes()).hexdigest()"
      pattern: "hashlib\\.sha256\\(.*read_bytes"
    - from: "graphify/reverse_sync.py"
      to: "graphify/profile.py"
      via: "load_profile import for user_only_folders, vault_path, input_path"
      pattern: "from graphify.profile import"
---

<objective>
Build the change-detection core of `graphify reverse-sync`: walk profile.user_only_folders recursively, hash markdown files raw-bytes, classify each pair as new/update/skip/vault_deleted, and return a structured change set. No I/O writes yet; no prompt; no JSONL — those land in plans 03 and 04.

Purpose: Pure-function classifier so the prompt UX, mode dispatch, and JSONL log can be tested independently against a known change set.
Output: `graphify/reverse_sync.py` (partial — detection only) + `tests/test_reverse_sync.py` covering D-08..D-10.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md
@.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md
@graphify/cache.py
@graphify/vault_promote.py

<interfaces>
- profile shape (Phase 69): `profile.user_only_folders: list[str]`, `profile.vault_path: str`, `profile.input_path: str`.
- Reuse: raw-bytes SHA256 idiom from `vault_promote.py:641` — `hashlib.sha256(path.read_bytes()).hexdigest()`.
- DO NOT import `cache.file_hash` (strips frontmatter — Pitfall 1).
- ChangeRecord (new): dataclass with `vault_path: Path`, `input_path: Path`, `rel_path: str`, `kind: Literal["new","update","skip","vault_deleted"]`, `hash_before: str | None`, `hash_after: str | None`.
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1 (RED): Failing tests for compute_change_set</name>
  <files>tests/test_reverse_sync.py, tests/fixtures/vault_with_user_folders/.gitkeep</files>
  <read_first>
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md (D-08, D-09, D-10)
    - .planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-RESEARCH.md (Pitfall 1, Architecture diagram)
    - graphify/cache.py:11-72
    - graphify/vault_promote.py:641 (raw-bytes SHA256 idiom)
  </read_first>
  <behavior>
    - test_detect_new_file: vault has Atlas/foo.md, input has nothing → ChangeRecord(kind="new", hash_after=H, hash_before=None)
    - test_detect_updated_file: both exist, contents differ → kind="update", hash_before≠hash_after
    - test_detect_skip_unchanged: identical bytes → kind="skip"
    - test_detect_vault_deleted: input has Atlas/old.md, vault does not → kind="vault_deleted" (D-10)
    - test_scope_user_only_folders: file outside user_only_folders is ignored entirely (D-08)
    - test_markdown_only: .txt, .pdf, .png in user folder are skipped (D-09)
    - test_recursive_subdirs: vault has Atlas/sub/deep/note.md → rel_path == "Atlas/sub/deep/note.md", input target preserves this path (D-09)
    - test_frontmatter_only_change_detected: file with body unchanged but frontmatter edited still flagged "update" (Pitfall 1 regression guard — proves cache.file_hash NOT used)
    - test_empty_vault: no user folders or no files → empty change set
    - Use tmp_path to construct dual-tree fixture (vault_dir/Atlas/, input_dir/Atlas/) inline.
  </behavior>
  <action>
    Create tests/test_reverse_sync.py with the 9 test functions above. Each builds a profile dict inline: `profile = {"vault_path": str(vault_dir), "input_path": str(input_dir), "user_only_folders": ["Atlas"], "reverse_sync": {}, "augment": {}}`. Import: `from graphify.reverse_sync import compute_change_set, ChangeRecord`. Create empty fixture dir tests/fixtures/vault_with_user_folders/.gitkeep so future end-to-end tests can use it. Run pytest — all must FAIL (ModuleNotFoundError).
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -q 2>&1 | grep -E "(error|failed)"</automated>
  </verify>
  <done>tests/test_reverse_sync.py has 9 detection tests; all fail with import error or assertion error.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2 (GREEN): Implement compute_change_set in graphify/reverse_sync.py</name>
  <files>graphify/reverse_sync.py</files>
  <read_first>
    - tests/test_reverse_sync.py (just written)
    - graphify/vault_promote.py:641 (raw-bytes SHA256)
    - graphify/security.py (path confinement helpers if any apply)
  </read_first>
  <action>
    Create graphify/reverse_sync.py:
    ```python
    from __future__ import annotations
    """Vault → Input reverse-sync (Phase 70 / VRSYNC-01).

    Detection-only module surface in this file (Plan 02). Mode dispatch + prompt
    UX (Plan 03), JSONL audit log (Plan 04), and auto_on_run hook (Plan 05) layer
    on top.

    NOTE: Do NOT use graphify.cache.file_hash() here — it strips frontmatter for
    .md files (cache.py:11-17), which is the wrong semantic for sync.
    """
    import hashlib
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
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def compute_change_set(profile: dict) -> list[ChangeRecord]:
        ...
    ```
    Algorithm:
    1. Resolve `vault_dir = Path(profile["vault_path"])`, `input_dir = Path(profile["input_path"])`.
    2. For each folder in `profile.get("user_only_folders", [])`:
       - Walk `vault_dir / folder` recursively, collect *.md files (D-09).
       - For each `vault_md`, compute `rel = vault_md.relative_to(vault_dir)`, `input_target = input_dir / rel`.
       - Compute hash_after = _raw_sha256(vault_md). hash_before = _raw_sha256(input_target) if input_target.exists() else None.
       - Classify: kind = "new" if hash_before is None else ("skip" if hash_before == hash_after else "update").
    3. For each folder, also walk `input_dir / folder` recursively for *.md files; for any file present in input but absent in vault, emit kind="vault_deleted" with hash_before=existing input hash, hash_after=None (D-10).
    4. Skip non-existent folders gracefully (warn-and-continue is plan 05's job; here just skip).
    5. Return sorted list by rel_path for deterministic ordering.
    Path-safety: resolve both vault_md and input_target; ensure input_target.resolve() stays under input_dir.resolve() (Pitfall: path traversal via symlink). Skip with stderr `[graphify] reverse-sync: refusing path outside input root: {rel}` if violation detected.
  </action>
  <verify>
    <automated>pytest tests/test_reverse_sync.py -q</automated>
  </verify>
  <done>All 9 detection tests pass; grep -c 'cache.file_hash\|from graphify.cache' graphify/reverse_sync.py == 0 (Pitfall 1 guard); grep 'hashlib.sha256' graphify/reverse_sync.py shows raw-bytes idiom.</done>
</task>

</tasks>

<verification>
- `pytest tests/test_reverse_sync.py -q` green
- `grep -v '^#' graphify/reverse_sync.py | grep -c 'from graphify.cache'` == 0
- ChangeRecord dataclass exposes all required fields for downstream plans 03/04
</verification>

<success_criteria>
- compute_change_set returns ChangeRecord list with correct kind classification
- D-08 (scope), D-09 (markdown only + recursive mirror), D-10 (vault_deleted log only) covered by tests
- Frontmatter-only edits are correctly detected (regression guard for Pitfall 1)
</success_criteria>

<output>
Create `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-02-reverse-sync-detect-SUMMARY.md` after completion.
</output>
