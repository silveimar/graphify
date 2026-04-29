---
phase: 35
slug: templates-export-plumbing-dry-run-migration-visibility
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
completed: 2026-04-29
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | none — tests run directly via pytest |
| **Quick run command** | `pytest tests/test_migration.py tests/test_export.py tests/test_merge.py tests/test_main_flags.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | < 60 seconds for focused tests |

---

## Sampling Rate

- **After every task commit:** Run the narrow test file touched by the task.
- **After every plan wave:** Run `pytest tests/test_migration.py tests/test_export.py tests/test_merge.py tests/test_main_flags.py -q`
- **Before `/gsd-verify-work`:** Run `pytest tests/ -q`; account only for documented pre-existing baseline failures if they remain unrelated.
- **Max feedback latency:** 60 seconds for focused feedback.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 01 | 0 | COMM-02 | T-35-01 | Legacy `_COMMUNITY_*` files surface as matched candidates or ORPHAN review-only rows, never silently ignored. | unit | `pytest tests/test_migration.py::test_legacy_community_files_surface_as_orphans -q` | yes | green |
| 35-01-02 | 01 | 0 | MIG-02 | T-35-02 | Preview writes migration artifacts but no vault Markdown notes or vault manifest changes. | unit/CLI | `pytest tests/test_migration.py::test_preview_writes_artifacts_but_no_vault_notes -q` | yes | green |
| 35-01-03 | 01 | 0 | MIG-03 | T-35-03 | Manifest identity maps old managed paths to new Graphify-owned paths in JSON and Markdown artifacts. | unit | `pytest tests/test_migration.py::test_legacy_manifest_identity_maps_old_path_to_new_path -q` | yes | green |
| 35-01-04 | 01 | 0 | MIG-04 | T-35-04 | Preview shows all six action classes and expands risky classes. | unit | `pytest tests/test_migration.py::test_preview_expands_risky_action_rows -q` | yes | green |
| 35-01-05 | 01 | 0 | MIG-06 | T-35-05 | Apply never deletes or moves legacy `_COMMUNITY_*` notes or ORPHAN rows. | unit | `pytest tests/test_migration.py::test_apply_never_deletes_legacy_orphan_files -q` | yes | green |
| 35-02-01 | 02 | 0 | REPO-04 | T-35-06 | CODE notes record repo identity in frontmatter, tags, and manifest metadata. | unit/integration | `pytest tests/test_export.py::test_code_notes_record_repo_identity_in_frontmatter_tags_and_manifest -q` | yes | green |
| 35-03-01 | 03 | 0 | MIG-01 | T-35-07 | `graphify update-vault --input work-vault/raw --vault ls-vault` runs preview-first and requires `--apply --plan-id` for writes. | CLI integration | `pytest tests/test_main_flags.py::test_update_vault_preview_default_runs_pipeline -q` | yes | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `tests/test_migration.py` — covers COMM-02, MIG-02, MIG-03, MIG-04, and MIG-06.
- [x] `tests/test_main_flags.py` — covers MIG-01 CLI parsing, preview default, and apply gate.
- [x] `tests/test_export.py` — covers REPO-04 frontmatter, tags, and manifest propagation.
- [x] `tests/test_merge.py` — covers any MergeAction metadata, repo drift conflict classification, or formatter changes.

---

## Manual-Only Verifications

All phase behaviors have automated verification paths.

---

## Validation Sign-Off

- [x] All tasks have automated verify commands or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency < 60s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** Nyquist-compliant after 12/12 verification truths passed.
