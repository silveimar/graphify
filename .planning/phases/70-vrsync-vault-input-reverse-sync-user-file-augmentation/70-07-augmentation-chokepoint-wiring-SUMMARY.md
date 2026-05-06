---
phase: 70-vrsync-vault-input-reverse-sync-user-file-augmentation
plan: 07
subsystem: vault-promote
tags: [vault, augmentation, chokepoint, gap-closure, VPROF-03]
gap_closure: true
requires: [70-06]
provides:
  - "Production call site for route_user_folder_to_augmentation"
  - "_route_user_only_writes partition helper at the promote() chokepoint"
affects:
  - graphify/vault_promote.py
tech-stack:
  added: []
  patterns:
    - "Pre-flight partition: split planned writes into augmentation-routes vs refusal-targets vs normal writes BEFORE any I/O"
key-files:
  created: []
  modified:
    - graphify/vault_promote.py
    - tests/test_vault_promote.py
decisions:
  - "Implemented partition at promote() level via new _route_user_only_writes() helper rather than splitting inside _preflight_check_user_only_folders — preserves existing helper signature so all prior tests pass unchanged."
  - "Refusal preserved for user-only-folder writes when user file does NOT exist (graphify must not create files in user folders) AND when planned frontmatter contains any non-allowlist key — both feed the existing _preflight_check_user_only_folders SystemExit gate (D-09)."
  - "Augmented user files are NOT recorded in the manifest (D-11 / Pitfall 8 — graphify never owns user files); _route_user_only_writes calls manifest.pop(rel_path, None) defensively in case a stale entry exists."
metrics:
  duration_minutes: ~25
  tests_added: 4
  tests_total_after: 2239
  completed: 2026-05-05
---

# Phase 70 Plan 07: Augmentation Chokepoint Wiring Summary

Wired `route_user_folder_to_augmentation` (shipped by 70-06 with zero non-test
callers) into the production `promote()` chokepoint so user_only_folders writes
that consist of allowlist-only frontmatter deltas merge into the existing user
file rather than being atomically refused.

## What Shipped

- New helper **`_route_user_only_writes(planned_with_content, merged_profile, vault_dir, manifest)`**
  in `graphify/vault_promote.py`. Partitions planned `(bucket_key, rel_path, content)`
  triples into three lists:
  - `augmented_paths` — user-folder files with existing content + allowlist-only
    planned frontmatter; routed through `route_user_folder_to_augmentation` in-place.
  - `refusal_targets` — user-folder paths that fail the allowlist gate (missing
    user file, or non-allowlist frontmatter key); fed to the existing
    `_preflight_check_user_only_folders` for atomic SystemExit (D-09).
  - `normal_targets` — graphify-owned paths; pass through to the normal
    `_write_record` loop unchanged.
- Integration in `promote()` between rendering and pre-flight, so this is the
  first production caller of `route_user_folder_to_augmentation`.
- Allowlist union sourced from `graphify.augment._ALLOWLIST_LISTS`,
  `_ALLOWLIST_SCALARS`, plus `"community"` when `profile.augment.allow_community`
  is set (D-16). No keys are hardcoded.

## Tests Added (RED → GREEN)

`tests/test_vault_promote.py`:

1. `test_user_folder_augmentation_chokepoint_merges_allowlist_frontmatter` —
   allowlist-only frontmatter delta on existing user file merges in-place; body
   bytes byte-identical (D-07); manifest unchanged (D-11).
2. `test_user_folder_augmentation_chokepoint_idempotent` — second run produces
   identical bytes (Pitfall 8 idempotence).
3. `test_user_folder_augmentation_chokepoint_refuses_non_allowlist_key` —
   `graphifyProject` (non-allowlist) in planned frontmatter routes to refusal
   bucket; user file untouched (D-09 preserved).
4. `test_user_folder_augmentation_chokepoint_refuses_when_user_file_missing` —
   no existing user file → refusal; graphify will not create files in user
   folders.

All four failed before implementation (ImportError on the helper) and pass
after. Full suite: 2239 passing (was 2235 baseline) + 1 unchanged pre-existing
failure in `test_migration.py::test_preview_expands_risky_action_rows`
(out-of-scope, baseline was already red there).

## Deviations from Plan

**1. [Architectural-correctness] Partition lives in `promote()`, not inside `_preflight_check_user_only_folders`.**

The plan suggested splitting "inside `_preflight_check_user_only_folders` (or
its caller in `promote_records`)". The pre-flight helper takes `(bucket_key,
rel_path)` tuples (no content) and is called from many existing tests. Adding
content-aware splitting inside it would have:

- broken its public test surface (3+ tests pass only `(bucket, rel_path)`),
- forced re-rendering of notes inside a function whose name implies pre-flight only.

I instead added a sibling helper `_route_user_only_writes` ABOVE the pre-flight
gate in `promote()`, kept `_preflight_check_user_only_folders`'s signature
intact, and let it run on the (filtered) refusal-targets list. This preserves
backward compatibility, satisfies all five must_haves, and matches the plan's
explicit fallback ("OR its caller in `promote_records` — that's where you can
split into refuse vs route-to-augmentation per record").

## Must-Haves Verification

| # | Must-have | Status |
|---|-----------|--------|
| 1 | `route_user_folder_to_augmentation` has ≥ 1 non-test caller in `graphify/vault_promote.py` | PASS — `_route_user_only_writes` invokes it at the chokepoint (called from `promote()`). `grep -c` on the symbol now returns 4 (was 1 before this plan). |
| 2 | Allowlist-only delta on user_only_folders → frontmatter merged, body bytes unchanged | PASS — asserted by `test_user_folder_augmentation_chokepoint_merges_allowlist_frontmatter`. |
| 3 | Second run is byte-idempotent | PASS — asserted by `test_user_folder_augmentation_chokepoint_idempotent`. |
| 4 | Non-allowlist key OR body-byte change → atomically refused (D-09/D-11) | PASS — `test_user_folder_augmentation_chokepoint_refuses_non_allowlist_key` confirms non-allowlist routes to refusal. Body-byte protection is structural: `route_user_folder_to_augmentation` never writes body bytes (D-07), enforced by `graphify/augment.py::augment_user_file_frontmatter`. |
| 5 | Augmented user files do NOT appear in the graphify manifest | PASS — asserted in test #1; `_route_user_only_writes` defensively pops the path from the manifest. |

## TDD Gate Compliance

- RED commit: `c3aedc1` — `test(70-07): add RED tests for user-folder augmentation chokepoint` (failing on ImportError).
- GREEN commit: `0270c63` — `feat(70-07): wire route_user_folder_to_augmentation into promote() chokepoint` (4/4 new tests pass; full suite green except baseline failure).
- REFACTOR: not required; helper is ~50 lines including docstring; no extraction needed.

## Self-Check: PASSED

- `graphify/vault_promote.py` — present, contains `_route_user_only_writes` and call to `route_user_folder_to_augmentation`.
- `tests/test_vault_promote.py` — present, 4 new tests with `augmentation_chokepoint` in the name.
- Commits `c3aedc1` (RED) and `0270c63` (GREEN) verified in `git log`.
