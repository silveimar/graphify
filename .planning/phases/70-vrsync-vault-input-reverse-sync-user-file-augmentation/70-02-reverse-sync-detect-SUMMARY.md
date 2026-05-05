---
phase: 70
plan: 02
subsystem: reverse-sync
tags: [vrsync, detection, tdd]
requires:
  - phase-69-profile-shape (vault_path, input_path, user_only_folders)
provides:
  - compute_change_set
  - ChangeRecord
  - _raw_sha256
affects:
  - graphify/reverse_sync.py (new)
tech_stack:
  added: []
  patterns:
    - raw-bytes SHA256 (mirrors vault_promote._hash_bytes / merge._content_hash)
    - frozen dataclass for immutable change records
    - forward+reverse two-pass classification
key_files:
  created:
    - graphify/reverse_sync.py
    - tests/test_reverse_sync.py
    - tests/fixtures/vault_with_user_folders/.gitkeep
  modified: []
decisions:
  - "Use hashlib.sha256(read_bytes()) directly — explicitly NOT graphify.cache.file_hash, which strips Markdown frontmatter and would silently misclassify frontmatter-only edits as 'skip' (Pitfall 1)."
  - "Two-pass scan (forward vault→input, then reverse input→vault) keeps classifier a pure function and isolates D-10 (vault_deleted is log-only, never silent deletion)."
  - "Sort records by rel_path for deterministic ordering — downstream JSONL log (Plan 04) and prompt UX (Plan 03) depend on stable iteration."
metrics:
  duration: "~10 min"
  tasks_completed: 2
  files_created: 3
  tests_added: 9
  completed: 2026-05-05
---

# Phase 70 Plan 02: Reverse-Sync Detection Summary

One-liner: pure-function `compute_change_set(profile)` walks `user_only_folders`, classifies *.md files as new/update/skip/vault_deleted via raw-bytes SHA256, returning a sorted list of `ChangeRecord` for downstream prompt UX and JSONL audit.

## Tasks Executed

| # | Task                                              | Type  | Commit  |
| - | ------------------------------------------------- | ----- | ------- |
| 1 | RED: failing detection tests for compute_change_set | tdd | 9e00eec |
| 2 | GREEN: implement compute_change_set in reverse_sync.py | tdd | 47fd3d6 |

## What Was Built

`graphify/reverse_sync.py` (new, 151 LOC):

- `ChangeKind = Literal["new", "update", "skip", "vault_deleted"]`
- `ChangeRecord` (frozen dataclass): `rel_path`, `vault_path`, `input_path`, `kind`, `hash_before`, `hash_after`
- `_raw_sha256(path)` — raw-bytes hash (frontmatter-preserving)
- `_iter_md_files(root)` — recursive *.md collector
- `_is_within(child, parent)` — symlink-safe path-confinement check
- `compute_change_set(profile)` — two-pass classifier

Tests (`tests/test_reverse_sync.py`, 9 cases):
new / updated / skip-unchanged / vault_deleted / scope-restriction (D-08) /
markdown-only (D-09) / recursive-subdirs (D-09) / frontmatter-only-update
(Pitfall 1 regression guard) / empty-vault.

## Verification

- `pytest tests/test_reverse_sync.py -q` → 9 passed
- `grep -E '^\s*from graphify\.cache|^\s*import graphify\.cache' graphify/reverse_sync.py` → 0 hits (Pitfall 1 guard satisfied; the only mentions of `cache.file_hash` are in the module docstring as a do-not-do warning)
- `grep 'hashlib.sha256' graphify/reverse_sync.py` → present (raw-bytes idiom confirmed)

## TDD Gate Compliance

- RED gate: commit 9e00eec — `test(70-02): add failing detection tests` (collection error / module not found)
- GREEN gate: commit 47fd3d6 — `feat(70-02): implement compute_change_set` (9/9 passing)
- REFACTOR gate: none required; implementation is minimal and clean.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. `compute_change_set` is a complete, fully-wired pure function. Downstream
plans (03 mode dispatch, 04 JSONL log, 05 auto-on-run) consume `ChangeRecord`
without further detection-layer changes.

## Self-Check: PASSED

- FOUND: graphify/reverse_sync.py
- FOUND: tests/test_reverse_sync.py
- FOUND: tests/fixtures/vault_with_user_folders/.gitkeep
- FOUND: 9e00eec (RED commit)
- FOUND: 47fd3d6 (GREEN commit)
