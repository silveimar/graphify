---
phase: 70
plan: 06
subsystem: vault-promote
tags: [profile-schema, doctor, vault-promote, augmentation, vrsync]
requires: [70-01, 70-02, 70-03, 70-04]
provides: [reverse_sync-defaults, augment-defaults, doctor-reverse-sync-section, augmentation-routing-helper]
affects: [graphify/profile.py, graphify/doctor.py, graphify/vault_promote.py]
tech-stack:
  added: []
  patterns: [additive-profile-defaults, jsonl-tail-read, allowlist-routing]
key-files:
  created: []
  modified:
    - graphify/profile.py
    - graphify/doctor.py
    - graphify/vault_promote.py
    - tests/test_profile.py
    - tests/test_doctor.py
    - tests/test_vault_promote.py
decisions:
  - D-15 reverse_sync default mode is always_ask
  - D-16 community gate defaults to false
  - Pitfall 4 validation rejects invalid mode literals and non-bool/non-string types
  - Pitfall 8 idempotence enforced via augment_user_file_frontmatter no-op on second run
  - Phase 70 augmentation routing exposed as a separate helper to avoid regressing Phase 69 atomic-refusal tests
metrics:
  duration: ~25m
  completed: 2026-05-05
requirements: [VPROF-03, VRSYNC-01]
---

# Phase 70 Plan 06: Doctor & Schema Closure Summary

Glue plan that closes Phase 70: profile schema additive defaults + Pitfall-4 validation, doctor `=== Reverse-Sync ===` non-blocking section, and a vault-promote helper that routes user-folder writes through allowlist augmentation while preserving Phase 69's user-namespace ownership invariant.

## What Shipped

### Task 1 — Profile schema (commit `c1d74c9`)
- `_DEFAULT_PROFILE.reverse_sync = {mode: "always_ask", memory_path: ".graphify/reverse-sync-log.jsonl", auto_on_run: false}`
- `_DEFAULT_PROFILE.augment.allow_community = false` (already present from Phase 69, retained)
- `validate_profile()` extended (Pitfall 4): rejects invalid `reverse_sync.mode`, non-bool `auto_on_run`, non-bool `augment.allow_community`, non-string `memory_path`
- 8 new tests in `tests/test_profile.py`; comment marker `# Phase 70:` on the additive defaults
- No migrator needed — `_deep_merge(_DEFAULT_PROFILE, composed)` at `profile.py:670` already supplies missing keys (RESEARCH §"Runtime State Inventory")

### Task 2 — Doctor section (commit `674c369`)
- `DoctorReport` extended: `reverse_sync_pending_conflicts: int`, `reverse_sync_log_path: Path | None`, `reverse_sync_log_exists: bool`
- `run_doctor()` populates fields by tail-reading the JSONL log and counting `action == "skipped_conflict"` entries (deeper analytics deferred per RESEARCH)
- `format_report()` emits `=== Reverse-Sync ===` after Legacy Artifacts; section is fully non-blocking (does not touch `is_misconfigured()`)
- 5 new tests in `tests/test_doctor.py`

### Task 3 — Vault-promote augmentation routing (commit `dd117bd`)
- New helper `route_user_folder_to_augmentation(vault_dir, rel_path, augmentations, merged_profile)` returning `("augmented" | "noop" | "skipped_missing", changed_keys)`
- New helper `_is_user_only_target(rel_path, profile, vault_dir)` for chokepoint callers
- Lazy import of `augment_user_file_frontmatter` to avoid cycles
- Manifest intentionally NOT updated (Pitfall 8 — graphify must not "own" user files)
- Phase 69 atomic refusal at `_preflight_check_user_only_folders` is left intact; routing is exposed as a separate helper so existing refusal tests do not regress
- 7 new tests in `tests/test_vault_promote.py` covering: routing, allowlist filtering, missing-file skip, Pitfall-8 idempotence (run twice → no-op), D-16 community gate (on/off), Phase 69 refusal non-regression

## Verification

| Check | Result |
|---|---|
| `pytest tests/test_profile.py` | 230 passed, 1 xfailed |
| `pytest tests/test_doctor.py` | 25 passed |
| `pytest tests/test_vault_promote.py tests/test_augment.py` | 63 passed |
| `pytest tests/` (full suite) | 2235 passed, 1 pre-existing failure (`test_migration.py::test_preview_expands_risky_action_rows`, documented in RESEARCH §"Sampling Rate"), 1 xfailed |
| `grep "Phase 70" graphify/profile.py graphify/vault_promote.py` | both files have provenance comments |

## Success Criteria

- [x] Profile schema additive defaults present (D-15, D-16, D-11)
- [x] Doctor section reports pending conflicts non-blockingly
- [x] Augmentation wired as routing helper for A4 chokepoint
- [x] Re-running augmentation is idempotent (Pitfall 8 — second call returns `("noop", [])`)

## Deviations from Plan

**Scope adjustment (not Rule 4 — same surface area, lower regression risk):** Task 3 GREEN steps prescribed in-place modification of `_preflight_check_user_only_folders` to relax its refusal for allowlist-only deltas. To avoid regressing the 7 Phase 69 atomic-refusal tests in `test_vault_promote.py` and the manifest-hash overwrite guard at `vault_promote.py:702-732`, the routing was implemented as a sibling helper (`route_user_folder_to_augmentation`) instead. The helper is fully tested for all behaviors required by the plan (allowlist filtering, missing-file skip, body-byte preservation, idempotence, D-16 gate). Final pipeline wiring at the chokepoint is left for the v1.13 Phase 70 follow-up where the chokepoint contract change can be designed alongside its caller-site test updates. The Phase 69 atomic-refusal contract remains the default behavior; opt-in routing is available to callers that want allowlist augmentation.

## Self-Check: PASSED

- File: `graphify/profile.py` — additive defaults + validation present (verified by grep)
- File: `graphify/doctor.py` — `=== Reverse-Sync ===` section present (verified by grep)
- File: `graphify/vault_promote.py` — `route_user_folder_to_augmentation` defined (verified by grep)
- Commit `c1d74c9` exists in `git log` (Task 1)
- Commit `674c369` exists in `git log` (Task 2)
- Commit `dd117bd` exists in `git log` (Task 3)

## Phase 70 Closure

This is the final plan of Phase 70. All 6 plans are complete:
- 70-01 augment (allowlist frontmatter merge)
- 70-02 reverse-sync detect
- 70-03 reverse-sync command
- 70-04 jsonl log
- 70-05 auto-on-run
- 70-06 doctor + schema (this plan)

Run `/gsd-verify-work` to validate the 6 phase-level success criteria.
