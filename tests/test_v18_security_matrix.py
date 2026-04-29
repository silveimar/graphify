"""Executable v1.8 sanitizer coverage matrix."""
from __future__ import annotations

import pytest


SANITIZER_COVERAGE_MATRIX = [
    {
        "input_class": "vault_relative_note_path",
        "helper": "graphify.profile.validate_vault_path",
        "unsafe_sample": "../escape.md",
        "expected": {"raises": "ValueError", "message": "would escape"},
        "test_name": "test_matrix_vault_relative_note_path_rejects_traversal",
    },
    {
        "input_class": "archive_destination_path",
        "helper": "graphify.migration._archive_destination",
        "unsafe_sample": "../escape.md",
        "expected": {"raises": "ValueError", "message": "archive path would escape"},
        "test_name": "test_matrix_archive_destination_path_rejects_traversal",
    },
    {
        "input_class": "profile_output_path",
        "helper": "graphify.profile.validate_sibling_path",
        "unsafe_sample": "../escape",
        "expected": {"raises": "ValueError", "message": "must not contain '..'"},
        "test_name": "test_matrix_profile_output_path_rejects_parent_segments",
    },
    {
        "input_class": "filename",
        "helper": "graphify.profile.safe_filename",
        "unsafe_sample": "Bad/Name|#\x00\n.md",
        "expected": "BadName.md",
        "test_name": "test_matrix_filename_strips_obisdian_and_control_chars",
    },
    {
        "input_class": "tag",
        "helper": "graphify.profile.safe_tag",
        "unsafe_sample": "9 Bad/Tag + Thing",
        "expected": "x9-bad-tag-thing",
        "test_name": "test_matrix_tag_slugifies_to_obsidian_tag_component",
    },
    {
        "input_class": "frontmatter_value",
        "helper": "graphify.profile.safe_frontmatter_value",
        "unsafe_sample": "yes\nno: [bad]\x00",
        "expected": '"yes no: [bad]"',
        "test_name": "test_matrix_frontmatter_value_strips_controls_and_quotes_yaml",
    },
    {
        "input_class": "wikilink_alias",
        "helper": "graphify.templates._sanitize_wikilink_alias",
        "unsafe_sample": "Array[int]]|Bad\nName\x00",
        "expected": "Array[int] ]-Bad Name ",
        "test_name": "test_matrix_wikilink_alias_neutralizes_alias_breakouts",
    },
    {
        "input_class": "generated_concept_title",
        "helper": "graphify.templates._sanitize_generated_title",
        "unsafe_sample": "]] | bad {{#connections}}: #tag\x00\n../escape",
        "expected": "Bad Connections Tag Escape",
        "test_name": "test_matrix_generated_concept_title_strips_template_path_syntax",
    },
    {
        "input_class": "template_block_syntax",
        "helper": "graphify.templates.validate_template",
        "unsafe_sample": "{{#connections}}${conn.label} {{#connections}}${conn.target}{{/connections}}{{/connections}}",
        "expected": {"errors_contain": "nested blocks"},
        "test_name": "test_matrix_template_block_syntax_rejects_nested_blocks",
    },
    {
        "input_class": "dataview_query",
        "helper": "graphify.templates._build_dataview_block",
        "unsafe_sample": "TABLE `${folder}`\n```danger\nFROM #${community_tag}",
        "expected": {"not_contains": "```danger", "contains": "TABLE folder"},
        "test_name": "test_matrix_dataview_query_strips_fence_breakouts",
    },
    {
        "input_class": "repo_identity",
        "helper": "graphify.naming.normalize_repo_identity",
        "unsafe_sample": "org/../../repo",
        "expected": {"raises": "ValueError", "message": "must not contain path segments"},
        "test_name": "test_matrix_repo_identity_rejects_path_segments",
    },
    {
        "input_class": "code_filename_stem",
        "helper": "graphify.naming.build_code_filename_stems",
        "unsafe_sample": {"node_id": "n_bad", "label": "Bad/Name|#\x00", "source_file": "src/bad.py"},
        "expected": "CODE_graphify_BadName",
        "test_name": "test_matrix_code_filename_stem_strips_label_breakouts",
    },
]


ASSERTIONS_BY_TEST_NAME = {}


@pytest.mark.parametrize(
    "row",
    SANITIZER_COVERAGE_MATRIX,
    ids=[row["test_name"] for row in SANITIZER_COVERAGE_MATRIX],
)
def test_sanitizer_coverage_matrix_executes_helper_assertions(row):
    assertion = ASSERTIONS_BY_TEST_NAME.get(row["test_name"])
    assert assertion is not None, f"missing executable assertion for {row['test_name']}"
    assertion(row)
