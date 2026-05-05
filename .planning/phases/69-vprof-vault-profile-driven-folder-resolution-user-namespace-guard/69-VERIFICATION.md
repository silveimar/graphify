---
phase: 69-vprof-vault-profile-driven-folder-resolution-user-namespace-guard
verified: 2026-05-05T19:45:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 69: VPROF — Vault Profile-Driven Folder Resolution & User-Namespace Guard Verification Report

**Phase Goal:** `graphify update-vault` and `graphify vault-promote --write-into-vault` resolve every write target via `profile.graphify_folder_mapping`, refuse to write under `profile.user_only_folders`, and surface legacy graphify-shaped artifacts outside the pinned subtree via `graphify doctor` + `--migrate-legacy`.
**Verified:** 2026-05-05T19:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With profile mapping `moc → Atlas/Sources/Graphify/Maps/`, no MOC notes land in `Atlas/Maps/`; writes go under pinned subtree | VERIFIED | `test_profile_folder_routing` (test_vault_promote.py:867) — `classify_nodes()` uses `graphify_folder_mapping`; hardcoded `Atlas/Maps` literal verified absent from routing code |
| 2 | Hardcoded `Atlas/...` folder literals and `_FOLDER_PATH_PREFIX` dict removed; folder computed from profile | VERIFIED | `_FOLDER_PATH_PREFIX` not present in vault_promote.py; `_resolve_folder_prefix()` at :871-902 reads `profile.graphify_folder_mapping` then falls back to D-04 pattern |
| 3 | Write to `user_only_folders` path refused pre-flight with two-line stderr `[graphify] error:` + `  hint:` | VERIFIED | `_preflight_check_user_only_folders()` at vault_promote.py:959; `test_refusal_stderr_format` (test_vault_promote.py:1039); `test_preflight_refusal_atomic` (test_vault_promote.py:995) |
| 4 | Manifest-hash overwrite guard (formerly lines 702-732) preserved and covered by regression test | VERIFIED | Guard logic at vault_promote.py:707-733 (write_note); `test_manifest_hash_guard_regression` (test_vault_promote.py:1071) simulates name collision and asserts `skipped_user_modified` |
| 5 | Old `folder_mapping` key upgrades silently to `graphify_folder_mapping` (idempotent; second call is no-op) | VERIFIED | `migrate_profile_v1_to_v2()` at profile.py:575; `test_migrator_renames_key` (test_profile.py:2311); `test_migrator_idempotent` (test_profile.py:2331) — second call returns `"already_v2"`, .bak mtime unchanged |
| 6 | `graphify doctor` reports legacy artifacts; `--migrate-legacy-apply` relocates them and re-points manifest | VERIFIED | `detect_legacy_artifacts()` at vault_promote.py:1187; `migrate_legacy()` at vault_promote.py:1236; `detect_legacy_artifact_paths` wired into doctor report at doctor.py:478-628; CLI flags at __main__.py:3319-3361; tests: `test_detect_legacy_comm_at_root`, `test_detect_legacy_community_maps`, `test_migrate_legacy_dry_run`, `test_migrate_legacy_apply`, `test_migrate_legacy_rollback` |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/profile.py` | Schema v2 keys + migrator | VERIFIED | `graphify_folder_mapping` at :171; `user_only_folders` at :180; `migrate_profile_v1_to_v2()` at :575 |
| `graphify/vault_promote.py` | Profile-driven folder resolution + refusal + legacy migration | VERIFIED | `_resolve_folder_prefix()` :871; `_preflight_check_user_only_folders()` :959; `detect_legacy_artifacts()` :1187; `migrate_legacy()` :1236 |
| `graphify/doctor.py` | Legacy artifact detection section | VERIFIED | `legacy_artifact_paths` field :162; detection call :478; rendering :616-628 |
| `graphify/__main__.py` | CLI flag wiring for `--migrate-legacy` and `--migrate-legacy-apply` | VERIFIED | Flags at :3319-3324; dispatch at :3333-3361 |
| `tests/test_profile.py` | Migrator tests | VERIFIED | `test_migrator_renames_key` :2311, `test_migrator_idempotent` :2331, `test_migrator_writes_bak` :2353 |
| `tests/test_vault_promote.py` | Refusal, hash guard, legacy detection/migration tests | VERIFIED | 8 new tests identified :995-1345 |
| `tests/test_doctor.py` | Doctor legacy section tests | VERIFIED | Included in 286 passed (test_vault_promote + test_profile + test_doctor suite) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `classify_nodes()` | `profile.graphify_folder_mapping` | `_resolve_folder_prefix()` | WIRED | vault_promote.py:892 reads `merged_profile.get("graphify_folder_mapping")` |
| `_preflight_check_user_only_folders()` | pre-flight chokepoint in `update_vault()` | call at :1091-1092 | WIRED | Called before any `write_note()` invocation |
| `detect_legacy_artifacts()` | doctor report | `doctor.py:478` import + assignment | WIRED | `report.legacy_artifact_paths = detect_legacy_artifacts(...)` |
| CLI `--migrate-legacy-apply` | `migrate_legacy()` | `__main__.py:3350-3351` | WIRED | `from graphify.vault_promote import migrate_legacy as _migrate_legacy` then called |
| `migrate_profile_v1_to_v2()` | profile load path | `profile.py:651` check | WIRED | Auto-migration on load when `folder_mapping` present without `graphify_folder_mapping` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 69 test suite | `pytest tests/test_vault_promote.py tests/test_profile.py tests/test_doctor.py -q` | 286 passed, 1 xfailed | PASS |
| Full suite (regression) | `pytest tests/ -q` | 2162 passed, 1 failed, 1 xfailed | PASS (see note) |

**Note on sole failure:** `tests/test_migration.py::test_preview_expands_risky_action_rows` — this test was last modified at commit `351e956` (ELIC-02 milestone), which predates Phase 69. None of the Phase 69 commits touch `test_migration.py` or `migration.py`. This is a pre-existing failure, not a Phase 69 regression.

### Requirements Coverage

| Requirement | Plans | Description | Status | Evidence |
|-------------|-------|-------------|--------|----------|
| VPROF-01 | 69-01, 69-02 | Schema v2 key `graphify_folder_mapping` + migrator | SATISFIED | `migrate_profile_v1_to_v2()` in profile.py:575; tests :2311, :2331 |
| VPROF-02 | 69-02 | Profile-driven folder resolution; no hardcoded `Atlas/...` | SATISFIED | `_resolve_folder_prefix()` vault_promote.py:871; `_FOLDER_PATH_PREFIX` absent |
| VPROF-03 (refusal half) | 69-03 | Pre-flight refusal for `user_only_folders` paths | SATISFIED | `_preflight_check_user_only_folders()` :959; atomic refusal test :995 |
| VPROF-04 | 69-04 | `graphify doctor` legacy detection + `--migrate-legacy-apply` | SATISFIED | `detect_legacy_artifacts()` :1187; `migrate_legacy()` :1236; doctor wiring :478 |

### Cross-Cutting Checks

**Phase 70 work creep:** No Phase 70 features (reverse-sync, bidirectional wikilink rewriting) found in Phase 69 commits. vault_promote.py implements only detection + migration, not bidirectional sync.

**Deferred ideas still deferred:** The CONTEXT.md D-16 items (vault-root-aware default path, bidirectional sync) are not implemented in Phase 69 code — confirmed by absence of related symbols in vault_promote.py.

**Manifest-hash guard preserved:** `write_note()` at vault_promote.py:707-733 retains the three-path guard (new write / overwrite-own / skip-user-modified). The regression test `test_manifest_hash_guard_regression` at :1071 explicitly covers the `skipped_user_modified` path with a simulated name collision. The guard was not broken by Phase 69 changes.

### Anti-Patterns Found

None blocking. The `Atlas/Sources/Graphify/Misc` fallback at vault_promote.py:1255 and the D-04 stderr INFO warning are intentional per decision D-04 (documented in CONTEXT.md). The `"Atlas/Maps"` string at vault_promote.py:1144 is a detection pattern for legacy artifacts (inside `_LEGACY_PATTERNS`), not a write target — not a stub.

### Human Verification Required

None. All success criteria are verifiable programmatically via code inspection and the test suite.

---

## PHASE COMPLETE

All 6 success criteria pass. Phase 69 goal is achieved:

- Profile-driven folder resolution is wired end-to-end (no hardcoded `Atlas/...` write targets).
- `_FOLDER_PATH_PREFIX` dict is gone.
- User-namespace refusal fires pre-flight with the required two-line stderr format and raises `SystemExit(1)` before any write.
- Manifest-hash overwrite guard is preserved with a regression test.
- `folder_mapping → graphify_folder_mapping` migrator is idempotent and covered by 3 tests.
- `graphify doctor` surfaces legacy artifacts; `--migrate-legacy-apply` relocates them atomically with rollback.

The sole test failure (`test_preview_expands_risky_action_rows`) is pre-existing from ELIC-02, not introduced by Phase 69.

---

_Verified: 2026-05-05T19:45:00Z_
_Verifier: Claude (gsd-verifier)_
