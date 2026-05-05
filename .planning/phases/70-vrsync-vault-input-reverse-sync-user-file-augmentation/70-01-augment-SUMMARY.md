---
phase: 70
plan: 01
subsystem: vault-augmentation
tags: [vrsync, augment, frontmatter, vprof-03, tdd]
requires:
  - graphify.merge._parse_frontmatter
  - graphify.merge._find_body_start
  - graphify.profile._dump_frontmatter
provides:
  - graphify.augment.augment_user_file_frontmatter
affects:
  - User-authored vault notes (frontmatter augmentation only; body byte-identical)
tech_stack:
  added: []
  patterns:
    - Allowlist merge (lists union / scalars only-if-absent)
    - Atomic write via tmp + os.replace
    - Byte-level read/write to preserve CRLF and BOM
key_files:
  created:
    - graphify/augment.py
    - tests/test_augment.py
  modified: []
decisions:
  - D-04 list union with user order preserved (tags, related_to, up, references)
  - D-05 scalar only-if-absent (comments, analysis, type)
  - D-06 stateless re-add of user-deleted keys
  - D-07 body bytes byte-identical pre/post augmentation
  - D-16 community key gated by profile.augment.allow_community
metrics:
  duration_min: ~12
  completed: 2026-05-05
  tasks: 3 (1 RED, 1 GREEN, 1 REFACTOR no-op)
  tests_added: 12
---

# Phase 70 Plan 01: Allowlist Frontmatter Augmentation — Summary

Implements the augmentation half of VPROF-03: graphify can ADD allowlist frontmatter keys to user-authored vault files, never touching the body, never overwriting existing scalar values, and producing zero diff on idempotent re-runs.

## What Was Built

**`graphify/augment.py`** — `augment_user_file_frontmatter(target, augmentations, profile) -> (Path, list[str])`.

Behavior:
- Reads target as bytes → decodes UTF-8 → strips BOM if present.
- Captures body slice via `_find_body_start` BEFORE any mutation.
- Parses existing frontmatter via `_parse_frontmatter`.
- For each incoming key:
  - If in `_ALLOWLIST_LISTS` (`tags`, `related_to`, `up`, `references`) → union with existing, preserving user order, appending novel items at end (D-04).
  - If in `_ALLOWLIST_SCALARS` (`comments`, `analysis`, `type`, plus `community` when D-16 gate enabled) → write only when key absent (D-05).
  - Otherwise → ignored.
- Re-emits frontmatter via `_dump_frontmatter` and concatenates with the captured body using a single `\n` separator (the parser strips that delimiter newline on read, giving body-byte-identity).
- Atomic write: `target.suffix + ".tmp"` → `os.replace`.
- Returns `(target, sorted(changed_keys))`. Empty list when nothing changed (no rewrite occurs).

## Tests Added (12)

`tests/test_augment.py`:

1. `test_list_keys_union_preserve_order` — D-04 happy path
2. `test_list_keys_create_when_absent` — list created from scratch
3. `test_scalar_keys_only_if_absent` — D-05 protection
4. `test_scalar_added_when_absent` — D-05 fill-in
5. `test_community_gate_default_false` — D-16 default
6. `test_community_gate_enabled` — D-16 opt-in
7. `test_non_allowlist_keys_ignored` — allowlist enforcement
8. `test_body_byte_identical_property` — D-07, 50 randomized iterations covering LF/CRLF/BOM/embedded `---`/empty bodies
9. `test_idempotent_reaugment` — second call returns `[]`
10. `test_d06_stateless_readd` — user deletion is re-added
11. `test_returns_changed_keys_list` — return contract + sorted determinism
12. `test_atomic_write` — simulated `os.replace` failure leaves original intact

All 12 pass. Full suite: 2174 pass / 1 pre-existing unrelated failure (`test_migration::test_preview_expands_risky_action_rows`, confirmed pre-existing via `git stash`).

## Deviations

**[Rule 1 — Bug] Byte-mode I/O instead of `Path.write_text`**

- **Found during:** Task 2 GREEN (property test iter 2).
- **Issue:** `Path.write_text` round-tripped CRLF as LF on POSIX (text-mode universal-newline translation), violating D-07.
- **Fix:** Switched to `read_bytes`/`write_bytes` with explicit UTF-8 codec on the boundary.
- **Files modified:** `graphify/augment.py`.
- **Commit:** `e2effc4` (folded into the GREEN commit; pre-commit attempt was the catalyst).

**[Rule 1 — Bug] Body-leading-newline absorption**

- **Found during:** Task 2 GREEN (property test iter 8).
- **Issue:** When body started with `\n`, the original conditional emitter (`new_fm + body` vs `new_fm + "\n" + body`) absorbed the body's leading newline into the closing `---` delimiter, dropping a byte from the body.
- **Fix:** Always emit exactly one `\n` between closing `---` and body — the parser unconditionally strips that newline on read, restoring byte-identity.
- **Files modified:** `graphify/augment.py`.
- **Commit:** `e2effc4`.

No architectural deviations. No CLAUDE.md violations. No new dependencies.

## Decisions Confirmed

- **D-04** Lists union, user order preserved. Verified by `test_list_keys_union_preserve_order`.
- **D-05** Scalars only-if-absent. Verified by `test_scalar_keys_only_if_absent` + `test_scalar_added_when_absent`.
- **D-06** Stateless re-add. Verified by `test_d06_stateless_readd`.
- **D-07** Body byte-identical. Verified by 50-iter property test with LF/CRLF/BOM/embedded `---`.
- **D-16** `community` gated by `profile.augment.allow_community`. Verified by both gate tests.

## Verification

- `pytest tests/test_augment.py -q` → 12 passed
- `pytest tests/ -q` → 2174 passed, 1 pre-existing failure (unrelated)
- `grep -c "PyYAML\|yaml.safe_load" graphify/augment.py` → 0 (anti-pattern check clean)
- `python3 -c "from graphify.augment import augment_user_file_frontmatter; print('ok')"` → ok

## Commits

- `6f9c665` test(70-01): add failing tests for augment_user_file_frontmatter (RED)
- `e2effc4` feat(70-01): implement augment_user_file_frontmatter (GREEN)
- (REFACTOR no-op — module already conformant; no commit per TDD-only-on-change rule)

## Self-Check: PASSED

- FOUND: graphify/augment.py
- FOUND: tests/test_augment.py
- FOUND: 6f9c665
- FOUND: e2effc4
