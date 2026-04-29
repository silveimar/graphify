---
phase: 32-profile-contract-defaults
verified: 2026-04-29T00:40:08Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 32: Profile Contract & Defaults Verification Report

**Phase Goal:** Users get a stable v1.8 default vault taxonomy and actionable profile validation before downstream export behavior changes.
**Verified:** 2026-04-29T00:40:08Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | No-profile Obsidian note defaults route generated notes into a Graphify-owned subtree, including concept MOCs under `Atlas/Sources/Graphify/MOCs/`. | VERIFIED | `_DEFAULT_PROFILE.folder_mapping` uses `Atlas/Sources/Graphify/...`; `to_obsidian()` loads defaults when no profile is supplied; `tests/test_export.py::test_to_obsidian_no_profile_dry_run_uses_graphify_default_paths` asserts every dry-run CREATE path starts with `Atlas/Sources/Graphify/` and at least one MOC path starts with `Atlas/Sources/Graphify/MOCs/`. |
| 2 | `_DEFAULT_PROFILE` exposes the top-level v1.8 `taxonomy:` contract. | VERIFIED | `graphify/profile.py` defines `taxonomy.version == "v1.8"`, `root == "Atlas/Sources/Graphify"`, and stable folders for `moc`, `thing`, `statement`, `person`, `source`, `default`, and `unclassified`. `_VALID_TOP_LEVEL_KEYS` includes `taxonomy`; `validate_profile(_DEFAULT_PROFILE) == []` is covered by tests. |
| 3 | Valid v1.8 user profiles override folder placement through `taxonomy:`, while missing required v1.8 keys fail validation. | VERIFIED | `validate_profile_preflight()` requires user-authored profiles to include `taxonomy` and `mapping.min_community_size`; CLI tests assert non-zero `--validate-profile` for missing keys. `load_profile()` applies taxonomy-derived folder mapping for valid user profiles. |
| 4 | Unsupported taxonomy keys and unsafe taxonomy folder paths are validation errors. | VERIFIED | `validate_profile()` rejects unknown taxonomy keys, unknown folder keys, absolute paths, `~`, empty strings, non-strings, and traversal; tests cover invalid keys and `taxonomy.folders.moc: ../escape`. |
| 5 | Legacy `mapping.moc_threshold` is invalid immediately, including when `mapping.min_community_size` is present. | VERIFIED | `validate_profile()` emits `mapping.moc_threshold is no longer supported; use mapping.min_community_size`; CLI spot-check returned exit code 1 and contained that error. No runtime alias remains in `graphify/mapping.py`. |
| 6 | Canonical `mapping.min_community_size` controls standalone MOC generation. | VERIFIED | `graphify/mapping.py::_assemble_communities()` reads only `profile["mapping"]["min_community_size"]` with a defensive fallback; `tests/test_mapping.py::test_mapping_min_community_size_controls_standalone_moc_floor` proves threshold 2 vs 3 changes standalone MOC behavior. |
| 7 | Taxonomy folder semantics take precedence over explicit `folder_mapping`. | VERIFIED | `graphify/mapping.py::_effective_folder_mapping()` overlays taxonomy folders after reading `folder_mapping`; `tests/test_mapping.py::test_taxonomy_moc_folder_wins_over_conflicting_folder_mapping` verifies taxonomy MOC folder wins over `Old/Maps/`. |
| 8 | The `_Unclassified` fallback is deterministic and routed under the Graphify MOC subtree. | VERIFIED | `graphify/mapping.py` creates `per_community[-1]` with `community_name == "_Unclassified"`, safe tag `unclassified`, and `folder=unclassified_folder`; tests verify the bucket and folder `Atlas/Sources/Graphify/MOCs/`. |
| 9 | No-root vault note guarantee holds for default Obsidian output paths. | VERIFIED | Default `folder_mapping` has no empty/root note folders; export dry-run test confirms all planned note paths are nested under `Atlas/Sources/Graphify/`. |
| 10 | `graphify --validate-profile` and `graphify doctor` share the same preflight diagnostic source. | VERIFIED | `graphify/__main__.py --validate-profile` and `graphify/doctor.py::run_doctor()` both call `validate_profile_preflight()`. Doctor stores `result.errors` and `result.warnings`; tests cover drift-sensitive taxonomy, legacy-key, and community-template findings. |
| 11 | Doctor treats validation errors as misconfiguration and warning-only community overview guidance as nonfatal. | VERIFIED | `DoctorReport.is_misconfigured()` depends on errors, unresolved output, or self-ingestion, not warnings. CLI spot-check for `community.md` returned code 0 and printed `MOC-only output`; `mapping.moc_threshold` doctor tests assert misconfiguration and fix hints. |
| 12 | Roadmap and requirements wording use the locked v1.8 contract. | VERIFIED | `ROADMAP.md` Phase 32 success criteria name `taxonomy:`, `mapping.min_community_size`, and immediate `mapping.moc_threshold` invalidation. `REQUIREMENTS.md` marks TAX-01..04, COMM-03, CLUST-01, and CLUST-04 complete and contains no `clustering.min_community_size`. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/profile.py` | Source of truth for v1.8 taxonomy defaults, validation, and preflight warnings | VERIFIED | Contains top-level `taxonomy`, canonical `mapping.min_community_size`, hard error for `mapping.moc_threshold`, required user-profile key checks, taxonomy path validation, and community overview warnings. |
| `graphify/mapping.py` | Taxonomy-aware folder resolution and community threshold routing | VERIFIED | Computes effective folder mapping from taxonomy, reads `min_community_size`, emits `_Unclassified`, and has no `moc_threshold` runtime fallback. |
| `graphify/doctor.py` | Doctor integration with shared profile preflight | VERIFIED | Imports `validate_profile_preflight`, stores warnings separately, renders `[graphify] warning:`, and builds targeted fixes for taxonomy, `mapping.min_community_size`, `mapping.moc_threshold`, and MOC-only output. |
| `graphify/export.py` | Export consumes `ClassificationContext.folder` instead of owning taxonomy decisions | VERIFIED | `to_obsidian()` calls `classify()`, then uses `ctx.get("folder")` for node and community target paths. |
| `tests/test_profile.py` | Profile contract coverage | VERIFIED | Covers default taxonomy, taxonomy atomicity, invalid taxonomy keys/folders, required v1.8 keys, legacy-key invalidation, and community template warnings. |
| `tests/test_mapping.py` | Mapping contract coverage | VERIFIED | Covers taxonomy precedence, `min_community_size`, and `_Unclassified`. |
| `tests/test_export.py` | No-profile dry-run path guarantee | VERIFIED | Covers default dry-run paths under `Atlas/Sources/Graphify/`. |
| `tests/test_doctor.py` | Doctor/preflight drift coverage | VERIFIED | Covers taxonomy errors, `mapping.moc_threshold`, warning-only community overview output, and fix hints. |
| `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` | Updated planning contract | VERIFIED | Phase 32 and requirement wording match the locked contract. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `graphify/profile.py` | `graphify/__main__.py` | `validate_profile_preflight()` for `--validate-profile` | WIRED | CLI validation command calls shared preflight and exits non-zero when `result.errors` is non-empty. |
| `graphify/profile.py` | `graphify/doctor.py` | `validate_profile_preflight()` | WIRED | Doctor imports and calls shared preflight when profile or templates exist. |
| `graphify/profile.py` | `graphify/mapping.py` | Resolved profile carries `taxonomy` and `mapping.min_community_size` | WIRED | `to_obsidian()` loads profile, then passes it to `classify()`; mapping resolves taxonomy and threshold from the profile. |
| `graphify/mapping.py` | `graphify/export.py` | `ClassificationContext.folder` | WIRED | Export target paths are built from mapping-owned `ctx.get("folder")` values. |
| `.planning/REQUIREMENTS.md` | `.planning/ROADMAP.md` | Matching v1.8 contract wording | WIRED | Both documents use `mapping.min_community_size`, immediate `mapping.moc_threshold` invalidation, and taxonomy precedence language. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `to_obsidian()` path planning | `ctx["folder"]` | `classify()` from `graphify/mapping.py` using loaded profile | Yes | FLOWING |
| `classify()` MOC threshold | `threshold` | `profile["mapping"]["min_community_size"]` | Yes | FLOWING |
| `doctor` profile diagnostics | `profile_validation_errors`, `profile_validation_warnings` | `validate_profile_preflight()` | Yes | FLOWING |
| `--validate-profile` CLI diagnostics | `result.errors`, `result.warnings` | `validate_profile_preflight()` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Focused Phase 32 test suite | `pytest tests/test_profile.py tests/test_mapping.py tests/test_doctor.py tests/test_export.py -q` | `261 passed, 1 xfailed, 2 warnings` | PASS |
| `mapping.moc_threshold` fails direct profile validation | Temporary vault + `python -m graphify --validate-profile <vault>` | Exit code 1; stderr contains `mapping.moc_threshold is no longer supported` | PASS |
| Doctor community overview warning is nonfatal | Temporary vault with `.graphify/templates/community.md` + `python -m graphify doctor` | Exit code 0; stdout contains `MOC-only output` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TAX-01 | 32-01, 32-02, 32-03 | No-profile generated notes under Graphify-owned default subtree | SATISFIED | Default folders and export dry-run test. |
| TAX-02 | 32-01, 32-02, 32-03 | Default concept MOCs under `Atlas/Sources/Graphify/MOCs/` | SATISFIED | `_DEFAULT_PROFILE.folder_mapping.moc`, mapping MOC folder, export dry-run test. |
| TAX-03 | 32-01, 32-02, 32-03 | User-authored profiles override through `taxonomy:`; missing keys fail validation | SATISFIED | Required-key preflight and taxonomy precedence tests. |
| TAX-04 | 32-01, 32-02, 32-04 | Actionable errors for unsupported taxonomy keys and invalid folder mappings | SATISFIED | Validator and doctor tests plus fix hints. |
| COMM-03 | 32-01, 32-02, 32-04 | Guidance for deprecated community overview output | SATISFIED | Preflight/doctor warnings name `community.md`/community template rules and `MOC-only output`. |
| CLUST-01 | 32-01, 32-02, 32-03 | `mapping.min_community_size` controls standalone MOC generation | SATISFIED | Mapping implementation and threshold tests. |
| CLUST-04 | 32-01, 32-02, 32-04 | `mapping.moc_threshold` causes deterministic validation failure | SATISFIED | Validator, CLI, and doctor evidence. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `graphify/profile.py` | n/a | `mapping.moc_threshold` string remains only in validation error branch | Info | Expected and required for deterministic invalidation. |
| `graphify/doctor.py` | n/a | `mapping.moc_threshold` string remains only in fix-hint branch | Info | Expected and required for actionable diagnostics. |
| `tests/test_profile.py` | n/a | Existing xfail placeholder comment in diagram-types test | Info | Pre-existing test placeholder unrelated to Phase 32 runtime behavior; focused suite passes with expected `1 xfailed`. |

### Human Verification Required

None. Phase 32 produces profile/schema/diagnostic behavior with automated verification paths; no visual, realtime, or external-service behavior is required.

### Gaps Summary

No blocking gaps found. The phase achieved the contract layer it promised: default taxonomy, validation, preflight/doctor surfacing, canonical community-size keying, legacy-key invalidation, taxonomy precedence, `_Unclassified` fallback, and planning-document alignment.

Residual risk: `load_profile()` still falls back to defaults after printing errors for invalid user profiles. This preserves existing library behavior while `--validate-profile` and `doctor` fail deterministically; later export/migration phases should decide whether runtime export should hard-stop on invalid profiles.

---

_Verified: 2026-04-29T00:40:08Z_
_Verifier: Claude (gsd-verifier)_
