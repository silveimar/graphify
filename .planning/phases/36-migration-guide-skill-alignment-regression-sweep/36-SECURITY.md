# Phase 36 Security Evidence

Phase 36 closes the v1.8 migration/docs/security sweep with executable evidence for preview-first vault updates, archive-by-default rollback metadata, docs and skill drift protection, and sanitizer coverage across every locked VER-03 input class.

## Threat Mitigations

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-36-01 | mitigated | `graphify/migration.py` keeps `load_migration_plan()` digest validation and `validate_plan_matches_request()` before apply/archive; `tests/test_migration.py::test_update_vault_rejects_stale_plan_id` proves stale plans fail before side effects. |
| T-36-02 | mitigated | `graphify/migration.py` archives only when `apply_merge_plan()` has no failures; `tests/test_migration.py::test_apply_failure_does_not_archive_legacy_notes` covers the failure gate. |
| T-36-03 | mitigated | `archive_legacy_notes()` validates sources through `validate_vault_path()` and destinations through `_archive_destination()`; `tests/test_migration.py` plus `tests/test_v18_security_matrix.py` cover traversal, duplicate destinations, and archive-root confinement. |
| T-36-04 | mitigated | `format_migration_preview()` prints `Archived legacy notes` and `graphify-out/migrations/archive/`; `tests/test_main_flags.py::test_update_vault_apply_archives_legacy_notes_by_default` verifies CLI rollback evidence. |
| T-36-05 | mitigated | `MIGRATION_V1_8.md` puts backup before apply and rollback immediately after apply/archive; `tests/test_docs.py::test_v18_migration_guide_orders_backup_and_rollback` enforces ordering. |
| T-36-06 | mitigated | `README.md` and `graphify update-vault --help` describe preview-first `--apply --plan-id`, archive paths, and no destructive deletion; `tests/test_docs.py` and `tests/test_main_flags.py` enforce the wording. |
| T-36-07 | mitigated | `tests/test_docs.py` locks exact guide/README phrases for backup, review, rollback, archive, and rerun. |
| T-36-08 | accepted | Localized README sync is explicitly out of scope per D-08; `tests/test_docs.py::test_v18_docs_contract_is_english_only` prevents accidental localized scope expansion. |
| T-36-09 | mitigated | All packaged `graphify/skill*.md` variants include the v1.8 Obsidian behavior block; `tests/test_skill_files.py::test_skill_files_share_v18_obsidian_contract_phrases` loops every variant. |
| T-36-10 | mitigated | Required skill phrases cover preview-first update-vault, backup before apply, archive location, and no destructive deletion; enforced by `REQUIRED_V18_OBSIDIAN_PHRASES`. |
| T-36-11 | mitigated | `FORBIDDEN_V18_OBSIDIAN_PHRASES` rejects stale generated `_COMMUNITY_*` claims while preserving legitimate legacy archive language. |
| T-36-12 | mitigated | Skill drift failure messages name the exact variant missing required phrases or containing forbidden claims. |
| T-36-13 | mitigated | `SANITIZER_COVERAGE_MATRIX` rows execute helper behavior through `test_sanitizer_coverage_matrix_executes_helper_assertions`, not passive documentation. |
| T-36-14 | mitigated | This artifact maps every matrix input class to helper and executable test name, including archive destination confinement. |
| T-36-15 | mitigated | `36-VALIDATION.md` records focused and full pytest evidence after execution. |
| T-36-16 | mitigated | `pytest tests/ -q` passed with `1896 passed, 1 xfailed, 8 warnings`; known baseline failures did not reproduce and required no scope expansion. |

## Sanitizer Coverage Matrix

| Input class | Helper | Executable test |
|-------------|--------|-----------------|
| vault_relative_note_path | `graphify.profile.validate_vault_path` | `test_matrix_vault_relative_note_path_rejects_traversal` |
| archive_destination_path | `graphify.migration._archive_destination` | `test_matrix_archive_destination_path_rejects_traversal` |
| profile_output_path | `graphify.profile.validate_sibling_path` | `test_matrix_profile_output_path_rejects_parent_segments` |
| filename | `graphify.profile.safe_filename` | `test_matrix_filename_strips_obsidian_and_control_chars` |
| tag | `graphify.profile.safe_tag` | `test_matrix_tag_slugifies_to_obsidian_tag_component` |
| frontmatter_value | `graphify.profile.safe_frontmatter_value` | `test_matrix_frontmatter_value_strips_controls_and_quotes_yaml` |
| wikilink_alias | `graphify.templates._sanitize_wikilink_alias` | `test_matrix_wikilink_alias_neutralizes_alias_breakouts` |
| generated_concept_title | `graphify.templates._sanitize_generated_title` | `test_matrix_generated_concept_title_strips_template_path_syntax` |
| template_block_syntax | `graphify.templates.validate_template` | `test_matrix_template_block_syntax_rejects_nested_blocks` |
| dataview_query | `graphify.templates._build_dataview_block` | `test_matrix_dataview_query_strips_fence_breakouts` |
| repo_identity | `graphify.naming.normalize_repo_identity` | `test_matrix_repo_identity_rejects_path_segments` |
| code_filename_stem | `graphify.naming.build_code_filename_stems` | `test_matrix_code_filename_stem_strips_label_breakouts` |

## Regression Evidence

| Gate | Command | Result |
|------|---------|--------|
| Matrix/helper gate | `pytest tests/test_v18_security_matrix.py tests/test_profile.py tests/test_templates.py tests/test_naming.py tests/test_migration.py -q` | 435 passed, 1 xfailed, 2 warnings |
| Focused Phase 36 gate | `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_docs.py tests/test_v18_security_matrix.py tests/test_profile.py tests/test_templates.py tests/test_naming.py -q` | 467 passed, 1 xfailed, 2 warnings |
| Full suite gate | `pytest tests/ -q` | 1896 passed, 1 xfailed, 8 warnings |

No network calls or non-`tmp_path` filesystem side effects were introduced by the new sanitizer matrix tests.
