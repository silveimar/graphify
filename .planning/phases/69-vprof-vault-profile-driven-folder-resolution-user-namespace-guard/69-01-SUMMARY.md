---
phase: 69
plan: "01"
subsystem: profile
tags: [schema-migration, profile, tdd]
dependency_graph:
  requires: []
  provides: [migrate_profile_v1_to_v2, graphify_folder_mapping schema v2]
  affects: [graphify/profile.py, tests/test_profile.py]
tech_stack:
  added: []
  patterns: [atomic YAML write via .tmp + os.replace, idempotent migrator returning sentinel strings]
key_files:
  modified:
    - graphify/profile.py
    - tests/test_profile.py
decisions:
  - "D-06: .bak overwrite only on actual migration — idempotent re-invocation leaves .bak mtime unchanged"
  - "D-16: user_only_folders defaults to [] (opt-in, not opt-out)"
  - "Migrator placed as a standalone function before load_profile; load_profile wires it via a pre-resolution peek at the raw YAML"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-05"
requirements: [VPROF-01]
---

# Phase 69 Plan 01: Profile Schema v2 + Silent v1→v2 Migrator Summary

Profile schema extended to v2 with 4 new top-level keys and a silent in-place migrator that renames `folder_mapping` to `graphify_folder_mapping` on first read.

## What Was Built

### Schema v2 keys added to `_DEFAULT_PROFILE`

| Key | Value / Type |
|-----|--------------|
| `graphify_folder_mapping` | dict of 7 singular-noun bucket keys (thing, question, map, person, quote, statement, source) → Ideaverse ACE paths |
| `user_only_folders` | `[]` (empty opt-in list, per D-16) |
| `augment` | `{"allow_community": False}` |
| `reverse_sync` | `{}` (Phase 70 placeholder) |

All 4 keys added to `_VALID_TOP_LEVEL_KEYS`.

### `migrate_profile_v1_to_v2(profile_path: Path, vault_dir: Path) -> str`

Signature and return values:
- `"migrated"` — legacy `folder_mapping` key detected and renamed; `.bak` written.
- `"already_v2"` — `graphify_folder_mapping` already present, OR neither key found; no-op.
- `"skipped_no_yaml"` — profile_path does not exist or PyYAML not installed.

**.bak semantics (D-05/D-06):** Written ONLY when an actual migration occurs (the `folder_mapping` branch). Re-invocation on a v2 profile returns `"already_v2"` and does not touch `.bak` — mtime invariant verified by `test_migrator_idempotent`. If `.bak` already exists from a prior migration run, it is overwritten (single overwriting `.bak`, no `.bak.bak` accumulation).

**Atomic write:** `.yaml.tmp` + `os.replace` per existing profile.py pattern.

**Stderr breadcrumb:** single `[graphify] profile: migrated folder_mapping → graphify_folder_mapping (backup at .graphify/profile.yaml.bak)` line.

### `load_profile()` wiring

Before calling `_resolve_profile_chain`, `load_profile` now does a lightweight peek at the raw YAML. If the loaded dict contains `folder_mapping` but not `graphify_folder_mapping`, it calls `migrate_profile_v1_to_v2` in-place so the chain resolver sees the already-migrated file.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | e1699bf | test(69-01): add failing migrator tests — all 3 failed with ImportError |
| GREEN (feat) | 386d563 | feat(69-01): implement profile schema v2 + silent v1→v2 migrator — all 3 pass |

## Test Count

- 3 new tests in `tests/test_profile.py`: `test_migrator_renames_key`, `test_migrator_idempotent`, `test_migrator_writes_bak`
- Full suite: 222 passed, 1 xfailed (no regressions)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `graphify/profile.py` — modified and committed at 386d563
- `tests/test_profile.py` — modified and committed at e1699bf (RED), 386d563 (no additional change needed)
- All 3 migrator tests pass
- Full `pytest tests/test_profile.py -q` passes (222 passed, 1 xfailed)
