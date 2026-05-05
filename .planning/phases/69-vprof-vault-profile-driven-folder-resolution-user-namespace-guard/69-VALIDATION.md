---
phase: 69
slug: vprof-vault-profile-driven-folder-resolution-user-namespace-guard
status: draft
nyquist_compliant: true
wave_0_complete: true
wave_0_rationale: "TDD RED tasks in Plans 01–04 satisfy the Wave 0 stub contract — each plan's first task writes failing tests for the requirement before any implementation. No separate Wave 0 plan is required."
created: 2026-05-05
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 69-RESEARCH.md "Validation Architecture" section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `pytest tests/test_vault_promote.py tests/test_profile.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_vault_promote.py tests/test_profile.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 69-01-W0 | 01 | 0 | VPROF-01 | — | Test stubs scaffold | unit | `pytest tests/test_profile.py -q --collect-only` | ❌ W0 | ⬜ pending |
| 69-01-01 | 01 | 1 | VPROF-01 | T-69-V5 / YAML safe_load only | Migrator renames `folder_mapping` → `graphify_folder_mapping` | unit | `pytest tests/test_profile.py::test_migrator_renames_key -x` | ❌ W0 | ⬜ pending |
| 69-01-02 | 01 | 1 | VPROF-01 | — | Migrator is idempotent (second run is no-op) | unit | `pytest tests/test_profile.py::test_migrator_idempotent -x` | ❌ W0 | ⬜ pending |
| 69-01-03 | 01 | 1 | VPROF-01 | — | Migrator writes single `.bak` (overwrites on subsequent runs) | unit | `pytest tests/test_profile.py::test_migrator_writes_bak -x` | ❌ W0 | ⬜ pending |
| 69-02-01 | 02 | 2 | VPROF-02 | T-69-V4 / path-confinement | `promote()` routes records via `profile.graphify_folder_mapping` | unit | `pytest tests/test_vault_promote.py::test_profile_folder_routing -x` | ❌ W0 | ⬜ pending |
| 69-02-02 | 02 | 2 | VPROF-02 | — | Unknown record type falls back to `Atlas/Sources/Graphify/<Type>/` | unit | `pytest tests/test_vault_promote.py::test_unknown_type_fallback -x` | ❌ W0 | ⬜ pending |
| 69-02-03 | 02 | 2 | VPROF-02 | — | `test_end_to_end_all_seven_folders` updated to assert `Atlas/Sources/Graphify/...` paths (regression for SC#1) | unit | `pytest tests/test_vault_promote.py::test_end_to_end_all_seven_folders -x` | ✅ (update) | ⬜ pending |
| 69-02-04 | 02 | 2 | VPROF-02 | — | `_FOLDER_PATH_PREFIX` dict + `classify_nodes()` `folder` literals removed (negative test: grep returns no matches) | unit | `pytest tests/test_vault_promote.py::test_no_hardcoded_atlas_literals -x` | ❌ W0 | ⬜ pending |
| 69-03-01 | 03 | 3 | VPROF-03 | T-69-V4 / pre-flight refusal | Pre-flight refuses write targeting `user_only_folders` (zero partial writes) | unit | `pytest tests/test_vault_promote.py::test_preflight_refusal_atomic -x` | ❌ W0 | ⬜ pending |
| 69-03-02 | 03 | 3 | VPROF-03 | T-69-V4 / chokepoint guard | `_write_record()` chokepoint refuses bypass attempt (synthetic test calling write helper directly with bad target) | unit | `pytest tests/test_vault_promote.py::test_write_record_chokepoint_guard -x` | ❌ W0 | ⬜ pending |
| 69-03-03 | 03 | 3 | VPROF-03 | — | Refusal stderr matches two-line `[graphify] error:` + `  hint:` format | unit | `pytest tests/test_vault_promote.py::test_refusal_stderr_format -x` | ❌ W0 | ⬜ pending |
| 69-03-04 | 03 | 3 | VPROF-03 | — | Manifest-hash overwrite guard regression — name collision within pinned subtree still triggers guard (SC#4) | unit | `pytest tests/test_vault_promote.py::test_manifest_hash_guard_regression -x` | ❌ W0 | ⬜ pending |
| 69-03-05 | 03 | 3 | VPROF-03 | — | Pre-flight runs BEFORE manifest-hash check (ordering invariant; D-11) | unit | `pytest tests/test_vault_promote.py::test_preflight_before_manifest_guard -x` | ❌ W0 | ⬜ pending |
| 69-03-06 | 03 | 3 | VPROF-03 | T-69-V4 / symlink resolve | Path.resolve() before user_only_folders check (symlink bypass mitigation) | unit | `pytest tests/test_vault_promote.py::test_user_only_symlink_resolved -x` | ❌ W0 | ⬜ pending |
| 69-04-01 | 04 | 4 | VPROF-04 | — | doctor detects `_COMM*.md` at vault root | unit | `pytest tests/test_vault_promote.py::test_detect_legacy_comm_at_root -x` | ❌ W0 | ⬜ pending |
| 69-04-02 | 04 | 4 | VPROF-04 | — | doctor detects `Community*.md` under `Atlas/Maps/` | unit | `pytest tests/test_vault_promote.py::test_detect_legacy_community_maps -x` | ❌ W0 | ⬜ pending |
| 69-04-03 | 04 | 4 | VPROF-04 | — | doctor detects manifest-tagged frontmatter outside pinned subtree (uses `graphifyProject` per RESEARCH A2) | unit | `pytest tests/test_vault_promote.py::test_detect_manifest_outside_pinned -x` | ❌ W0 | ⬜ pending |
| 69-04-04 | 04 | 4 | VPROF-04 | — | `--migrate-legacy` (or `--migrate-legacy-apply` per planner choice) dry-run prints plan, performs zero moves | unit | `pytest tests/test_vault_promote.py::test_migrate_legacy_dry_run -x` | ❌ W0 | ⬜ pending |
| 69-04-05 | 04 | 4 | VPROF-04 | — | `--migrate-legacy --apply` (or alt flag) moves files AND updates manifest atomically (SC#6) | unit | `pytest tests/test_vault_promote.py::test_migrate_legacy_apply -x` | ❌ W0 | ⬜ pending |
| 69-04-06 | 04 | 4 | VPROF-04 | — | Atomic rollback: if manifest write fails after move, file is moved back | unit | `pytest tests/test_vault_promote.py::test_migrate_legacy_rollback -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vault_promote.py` — add stub functions for VPROF-02/03/04 tests (mark `pytest.skip` initially; implementations land in Wave 1+)
- [ ] `tests/test_profile.py` — add stub functions for VPROF-01 migrator tests
- [ ] `tests/conftest.py` — confirm shared fixtures (vault_dir tmp_path, sample profile YAML) cover Phase 69 needs; extend if missing
- [ ] No new framework install — pytest 7.x already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Ideaverse vault end-to-end check | SC#1 | User's actual vault is the regression-bug epicenter; smoke test against the real vault confirms the fix lands in production conditions | After Phase 69 ships: run `graphify update-vault` against the user's Ideaverse vault. Verify all community MOC notes land under `Atlas/Sources/Graphify/Maps/`. Verify zero new files appear under `Atlas/Maps/` or vault root. |
| YAML round-trip preserves user comments/key order in `profile.yaml` | VPROF-01 | PyYAML's `safe_dump` does not preserve comments by default; visual inspection of a real user-edited profile confirms acceptable round-trip | Hand-edit a `profile.yaml` with comments and custom key order. Run any command that triggers the migrator. Inspect rewritten file: comments preserved? Key order acceptable? |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick run)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
