---
phase: 35-templates-export-plumbing-dry-run-migration-visibility
verified: 2026-04-29T06:13:23Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 35: Templates, Export Plumbing & Dry-Run/Migration Visibility Verification Report

**Phase Goal:** Users can preview and run the new export/migration path without silent overwrites, hidden legacy artifacts, or repo identity drift.  
**Verified:** 2026-04-29T06:13:23Z  
**Status:** passed  
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Resolved repo identity is recorded consistently in CODE note filenames, frontmatter, tags, and output manifests. | VERIFIED | `graphify/export.py` injects `resolved_repo_identity.identity` into CODE contexts; `graphify/templates.py` emits CODE-only `repo` frontmatter and `repo/<identity>` tags; `graphify/merge.py` stores per-note `repo_identity` and `__graphify_run__`; focused test passed. |
| 2 | `graphify update-vault --input work-vault/raw --vault ls-vault` is an origin raw-corpus input feeding a fixed vault destination, not a vault-to-vault move. | VERIFIED | `graphify/__main__.py` exposes the exact command shape; `run_update_vault()` resolves `input_dir` as `raw`, requires target `vault_dir/.obsidian`, resolves output from the target vault, and runs `run_corpus(raw, ...)`. |
| 3 | Preview is the default and runs before any vault note writes. | VERIFIED | CLI only applies when `--apply` is set; `run_update_vault()` calls `to_obsidian(..., dry_run=True, return_render_context=True)` before writing migration artifacts. `test_update_vault_preview_default_runs_pipeline` confirmed no vault Markdown notes were written. |
| 4 | Option A dry-run/apply is preview-then-apply, not a fresh full rebuild/write bypass. | VERIFIED | Apply loads a reviewed artifact, reruns a current dry-run preview only for validation, checks plan IDs match, reconstructs a classified `MergePlan` from applicable rows, then calls `apply_merge_plan()`; no `dry_run=False` path is used in `graphify/migration.py`. |
| 5 | Apply requires both `--apply` and `--plan-id <id>` from a preview artifact. | VERIFIED | `graphify/__main__.py` exits 2 with `error: --apply requires --plan-id from a preview artifact`; focused CLI test passed. |
| 6 | Apply rejects stale, tampered, or mismatched plan artifacts before vault writes. | VERIFIED | `load_migration_plan()` validates plan ID shape and recomputed digest; `validate_plan_matches_request()` checks resolved input, vault, repo identity, digest, and current preview plan ID; stale-plan test preserved vault files. |
| 7 | Preview writes JSON and Markdown migration plan artifacts without writing vault notes or mutating the vault manifest. | VERIFIED | `write_migration_artifacts()` writes `migration-plan-<id>.json` and `.md` under `migrations/` via `.tmp` + `fsync()` + `os.replace()`; tests assert vault files and `vault-manifest.json` remain unchanged during preview. |
| 8 | Legacy `_COMMUNITY_*` files are surfaced as ORPHAN review-only rows when unmatched. | VERIFIED | `scan_legacy_notes()` finds legacy/fingerprinted Markdown under the target vault and `build_migration_preview()` appends review-only `ORPHAN` rows; `test_legacy_community_files_surface_as_orphans` passed. |
| 9 | Matched old managed paths are reported beside canonical v1.8 Graphify-owned target paths. | VERIFIED | Manifest/frontmatter/filename identity matching populates `legacy_mappings` with `old_path`, `new_path`, `identity_source`, `legacy_action`, and `canonical_action`; mapping test confirms JSON and Markdown include both paths. |
| 10 | CREATE, UPDATE, SKIP_PRESERVE, SKIP_CONFLICT, REPLACE, and ORPHAN outcomes are reviewable before apply. | VERIFIED | `ACTION_ORDER` includes all six outcomes; `format_migration_preview()` prints all counts, expands risky actions, and summarizes low-risk rows; focused risky-row test passed. |
| 11 | Existing managed notes with concrete different repo identity are classified as `SKIP_CONFLICT`. | VERIFIED | `_classify_repo_drift()` converts mismatched concrete repo identities to `SKIP_CONFLICT` with `conflict_kind: repo_identity_drift`; focused drift test passed. |
| 12 | Legacy notes and ORPHAN rows are never deleted, moved, updated, or promoted to writes by migration apply helpers. | VERIFIED | `filter_applicable_actions()` returns only CREATE, UPDATE, and REPLACE; `apply_merge_plan()` skips SKIP_PRESERVE, SKIP_CONFLICT, and ORPHAN; non-deletion tests passed. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/migration.py` | Migration preview, legacy scan, artifact persistence, plan validation, update-vault orchestration, repo drift classification | VERIFIED | Exists and substantive; `gsd-sdk verify.artifacts` passed; wired from CLI and export/merge helpers. |
| `graphify/__main__.py` | `update-vault` command with preview-first and apply-by-plan-id semantics | VERIFIED | Exists and substantive; command branch parses `--input`, `--vault`, `--apply`, `--plan-id`, delegates to `run_update_vault()`. |
| `graphify/export.py` | CODE render context repo identity and dry-run render context for migration apply | VERIFIED | Exists and substantive; CODE contexts get `repo_identity`; dry-run can return plan/render context for validated apply. |
| `graphify/templates.py` | CODE `repo` frontmatter and `repo/<identity>` tag rendering | VERIFIED | Exists and substantive; CODE-only repo frontmatter/tag use existing sanitizers. |
| `graphify/merge.py` | Repo merge policy, manifest repo metadata, safe apply path | VERIFIED | Exists and substantive; `repo` is graphify-owned, manifests store repo identity, apply skips non-write actions. |
| `tests/test_migration.py` | Migration helper tests for legacy surfacing, artifacts, stale plans, repo drift, non-deletion | VERIFIED | Exists and substantive; focused migration tests passed. |
| `tests/test_main_flags.py` | CLI tests for update-vault command shape, preview default, apply gate | VERIFIED | Exists and substantive; focused CLI tests passed. |
| `tests/test_export.py` | REPO-04 export assertions | VERIFIED | Exists and substantive; focused export test passed. |
| `tests/test_merge.py` | Manifest compatibility and repo field policy assertions | VERIFIED | Exists and substantive; artifact verification passed. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `graphify/__main__.py` | `graphify.migration.run_update_vault` | `update-vault` branch | VERIFIED | `gsd-sdk verify.key-links` found the command wiring. |
| `graphify/migration.py` | `graphify.output.resolve_output` | Target vault profile/output resolution | VERIFIED | `run_update_vault()` resolves output from `vault_dir`, preserving fixed target semantics and profile-routed notes. |
| `graphify/migration.py` | `graphify.pipeline.run_corpus` | Raw `--input` pipeline execution | VERIFIED | `run_update_vault()` calls `run_corpus(raw, ...)` before build/cluster/export dry-run. |
| `graphify/migration.py` | `graphify.export.to_obsidian` | Dry-run render feeding preview/apply validation | VERIFIED | `to_obsidian(..., dry_run=True, return_render_context=True)` is used; no migration `dry_run=False` bypass found. |
| `graphify/migration.py` | `graphify.merge.apply_merge_plan` | Validated classified apply | VERIFIED | Apply reconstructs a `MergePlan` from filtered reviewed rows and calls `apply_merge_plan()`. |
| `graphify/migration.py` | `graphify.profile.validate_vault_path` | Legacy scan and action reconstruction confinement | VERIFIED | Legacy candidates and preview action reconstruction pass through vault path validation. |
| `graphify/migration.py` | `graphify.naming.resolve_repo_identity` | Banner, CODE rows, drift comparison | VERIFIED | `run_update_vault()` resolves identity once from input/profile/CLI and reuses it in preview/export. |
| `graphify/export.py` | `graphify.naming.resolve_repo_identity` | Resolved identity injected into CODE contexts | VERIFIED | `resolved_repo_identity.identity` is threaded into CODE render contexts. |
| `graphify/templates.py` | `graphify.profile.safe_tag` / `safe_frontmatter_value` | Repo tag/frontmatter sanitization | VERIFIED | CODE repo tags and frontmatter use existing sanitizers. |
| `graphify/merge.py` | `_build_manifest_from_result` | Manifest repo metadata | VERIFIED | Manifest entries and reserved run metadata record repo identity. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `graphify/migration.py` | `preview` | `run_corpus(input_dir)` -> `build()` -> `cluster()` -> `to_obsidian(..., dry_run=True)` -> `build_migration_preview()` | Yes | FLOWING |
| `graphify/migration.py` | `loaded` plan artifact | `load_migration_plan(resolved.artifacts_dir, plan_id)` plus digest recomputation | Yes | FLOWING |
| `graphify/migration.py` | `applicable_plan` | `filter_applicable_actions(loaded)` -> `_merge_plan_from_preview()` | Yes, filtered to CREATE/UPDATE/REPLACE only | FLOWING |
| `graphify/export.py` / `graphify/templates.py` | `repo_identity` | `resolve_repo_identity()` -> CODE classification context -> `render_note()` | Yes | FLOWING |
| `graphify/merge.py` | Manifest `repo_identity` | Rendered CODE frontmatter `repo` -> `_build_manifest_from_result()` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI preview/apply gate/repo drift/repo metadata focused behavior | `pytest tests/test_migration.py::test_update_vault_rejects_stale_plan_id tests/test_migration.py::test_repo_identity_drift_becomes_skip_conflict tests/test_migration.py::test_update_vault_profile_output_outside_vault_previews_and_applies tests/test_main_flags.py::test_update_vault_preview_default_runs_pipeline tests/test_main_flags.py::test_update_vault_apply_without_plan_id_exits_two tests/test_main_flags.py::test_update_vault_help_lists_command_shape tests/test_export.py::test_code_notes_record_repo_identity_in_frontmatter_tags_and_manifest -q` | `7 passed, 2 warnings` | PASS |
| Phase-level regression gate | `pytest tests/ -q` | Orchestrator reported `1871 passed, 1 xfailed, 8 warnings` | PASS |
| Artifact declarations | `gsd-sdk query verify.artifacts` for all three plans | `11/11` artifacts passed | PASS |
| Key link declarations | `gsd-sdk query verify.key-links` for all three plans | `10/10` links verified | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| COMM-02 | 35-01, 35-03 | User sees legacy `_COMMUNITY_*` files surfaced as migration candidates or orphans instead of silently ignored. | SATISFIED | `scan_legacy_notes()` plus `build_migration_preview()` surface unmatched legacy notes as review-only ORPHAN rows; legacy surfacing tests passed. |
| REPO-04 | 35-02, 35-03 | User sees resolved repo identity recorded consistently in CODE note filenames, frontmatter, tags, and output manifests. | SATISFIED | CODE filename stems, CODE `repo` frontmatter, `repo/<identity>` tags, per-note manifest entries, and `__graphify_run__` are verified by focused export test. |
| MIG-01 | 35-03 | User can run an automated migration command for the real `work-vault` to `ls-vault` update path. | SATISFIED | CLI help and branch expose `graphify update-vault --input work-vault/raw --vault ls-vault`; preview CLI test passed. |
| MIG-02 | 35-01, 35-03 | User can preview migration effects in dry-run mode before any vault writes occur. | SATISFIED | Preview path uses `to_obsidian(..., dry_run=True)` and writes migration artifacts only; no vault Markdown notes in CLI preview test. |
| MIG-03 | 35-01 | User sees old managed paths mapped to new Graphify-owned paths when note identity can be matched. | SATISFIED | `legacy_mappings` records old and new paths with identity source and canonical action; JSON/Markdown mapping test passed. |
| MIG-04 | 35-01, 35-03 | User can review CREATE, UPDATE, SKIP_PRESERVE, SKIP_CONFLICT, REPLACE, and ORPHAN outcomes before committing. | SATISFIED | Formatter prints all six counts and expands risky rows; apply requires reviewed plan id; focused tests passed. |
| MIG-06 | 35-01, 35-03 | User never has legacy vault notes automatically deleted during migration. | SATISFIED | ORPHAN/SKIP rows are excluded from applicable actions and `apply_merge_plan()` never deletes ORPHAN rows; non-deletion test passed. |

No orphaned Phase 35 requirements were found in `REQUIREMENTS.md`. Later Phase 36 owns MIG-05 and VER-01..03, which are not Phase 35 gaps.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | No blocker or warning anti-patterns found in the verified Phase 35 surface. | - | Review gate is clean after commit `260f09d`; focused tests cover the prior routed-output blocker. |

### Human Verification Required

None. Phase 35 is CLI/filesystem behavior with deterministic unit and subprocess coverage; no visual, external-service, or real-time behavior remains for human-only verification.

### Gaps Summary

No gaps found. The phase goal is achieved: the new migration path previews first, persists review artifacts, requires an exact reviewed plan for apply, preserves legacy/community artifacts as review-only, surfaces repo drift as `SKIP_CONFLICT`, and keeps repo identity consistent across CODE output surfaces and manifests.

---

_Verified: 2026-04-29T06:13:23Z_  
_Verifier: Claude (gsd-verifier)_
