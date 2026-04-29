"""Executable v1.8 sanitizer coverage matrix."""
from __future__ import annotations

from pathlib import Path

import pytest

from graphify.migration import _archive_destination
from graphify.naming import build_code_filename_stems, normalize_repo_identity
from graphify.profile import (
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_sibling_path,
    validate_vault_path,
)
from graphify.templates import (
    _build_dataview_block,
    _sanitize_generated_title,
    _sanitize_wikilink_alias,
    validate_template,
)

# Private helper imports above are intentional: these tests lock security
# invariants at the exact Markdown/filesystem sink helpers used by v1.8.


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
        "test_name": "test_matrix_filename_strips_obsidian_and_control_chars",
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
        "expected": {"errors_contain": "nested template blocks"},
        "test_name": "test_matrix_template_block_syntax_rejects_nested_blocks",
    },
    {
        "input_class": "dataview_query",
        "helper": "graphify.templates._build_dataview_block",
        "unsafe_sample": "TABLE ${folder}\n```danger\nFROM #${community_tag}",
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


def _assert_raises(match: str, fn, *args) -> None:
    with pytest.raises(ValueError, match=match):
        fn(*args)


def _assert_vault_relative_note_path(row: dict) -> None:
    assert row["helper"] == "graphify.profile.validate_vault_path"
    _assert_raises(row["expected"]["message"], validate_vault_path, row["unsafe_sample"], Path.cwd())


def _assert_archive_destination_path(row: dict) -> None:
    assert row["helper"] == "graphify.migration._archive_destination"
    _assert_raises(row["expected"]["message"], _archive_destination, Path.cwd() / "archive", row["unsafe_sample"])


def _assert_profile_output_path(row: dict) -> None:
    assert row["helper"] == "graphify.profile.validate_sibling_path"
    _assert_raises(row["expected"]["message"], validate_sibling_path, row["unsafe_sample"], Path.cwd() / "vault")


def _assert_filename(row: dict) -> None:
    assert row["helper"] == "graphify.profile.safe_filename"
    assert safe_filename(row["unsafe_sample"]) == row["expected"]


def _assert_tag(row: dict) -> None:
    assert row["helper"] == "graphify.profile.safe_tag"
    assert safe_tag(row["unsafe_sample"]) == row["expected"]


def _assert_frontmatter_value(row: dict) -> None:
    assert row["helper"] == "graphify.profile.safe_frontmatter_value"
    assert safe_frontmatter_value(row["unsafe_sample"]) == row["expected"]


def _assert_wikilink_alias(row: dict) -> None:
    assert row["helper"] == "graphify.templates._sanitize_wikilink_alias"
    assert _sanitize_wikilink_alias(row["unsafe_sample"]) == row["expected"]


def _assert_generated_concept_title(row: dict) -> None:
    assert row["helper"] == "graphify.templates._sanitize_generated_title"
    assert _sanitize_generated_title(row["unsafe_sample"]) == row["expected"]


def _assert_template_block_syntax(row: dict) -> None:
    assert row["helper"] == "graphify.templates.validate_template"
    errors = validate_template(row["unsafe_sample"], set())
    assert any(row["expected"]["errors_contain"] in error for error in errors)


def _assert_dataview_query(row: dict) -> None:
    assert row["helper"] == "graphify.templates._build_dataview_block"
    profile = {"dataview_queries": {"moc": row["unsafe_sample"]}}
    result = _build_dataview_block(
        profile,
        "bad`\ntag",
        "folder`\n",
        "moc",
    )
    assert row["expected"]["contains"] in result
    assert row["expected"]["not_contains"] not in result
    assert "bad`" not in result
    assert "folder`" not in result


def _assert_repo_identity(row: dict) -> None:
    assert row["helper"] == "graphify.naming.normalize_repo_identity"
    _assert_raises(row["expected"]["message"], normalize_repo_identity, row["unsafe_sample"])


def _assert_code_filename_stem(row: dict) -> None:
    assert row["helper"] == "graphify.naming.build_code_filename_stems"
    result = build_code_filename_stems([row["unsafe_sample"]], "Graphify")
    assert result[row["unsafe_sample"]["node_id"]]["filename_stem"] == row["expected"]


ASSERTIONS_BY_TEST_NAME = {
    "test_matrix_vault_relative_note_path_rejects_traversal": _assert_vault_relative_note_path,
    "test_matrix_archive_destination_path_rejects_traversal": _assert_archive_destination_path,
    "test_matrix_profile_output_path_rejects_parent_segments": _assert_profile_output_path,
    "test_matrix_filename_strips_obsidian_and_control_chars": _assert_filename,
    "test_matrix_tag_slugifies_to_obsidian_tag_component": _assert_tag,
    "test_matrix_frontmatter_value_strips_controls_and_quotes_yaml": _assert_frontmatter_value,
    "test_matrix_wikilink_alias_neutralizes_alias_breakouts": _assert_wikilink_alias,
    "test_matrix_generated_concept_title_strips_template_path_syntax": _assert_generated_concept_title,
    "test_matrix_template_block_syntax_rejects_nested_blocks": _assert_template_block_syntax,
    "test_matrix_dataview_query_strips_fence_breakouts": _assert_dataview_query,
    "test_matrix_repo_identity_rejects_path_segments": _assert_repo_identity,
    "test_matrix_code_filename_stem_strips_label_breakouts": _assert_code_filename_stem,
}


def test_sanitizer_coverage_matrix_lists_locked_input_classes():
    expected = {
        "vault_relative_note_path",
        "archive_destination_path",
        "profile_output_path",
        "filename",
        "tag",
        "frontmatter_value",
        "wikilink_alias",
        "generated_concept_title",
        "template_block_syntax",
        "dataview_query",
        "repo_identity",
        "code_filename_stem",
    }

    assert {row["input_class"] for row in SANITIZER_COVERAGE_MATRIX} == expected
    assert len({row["test_name"] for row in SANITIZER_COVERAGE_MATRIX}) == len(SANITIZER_COVERAGE_MATRIX)
    assert set(ASSERTIONS_BY_TEST_NAME) == {row["test_name"] for row in SANITIZER_COVERAGE_MATRIX}


@pytest.mark.parametrize(
    "row",
    SANITIZER_COVERAGE_MATRIX,
    ids=[row["test_name"] for row in SANITIZER_COVERAGE_MATRIX],
)
def test_sanitizer_coverage_matrix_executes_helper_assertions(row):
    assertion = ASSERTIONS_BY_TEST_NAME.get(row["test_name"])
    assert assertion is not None, f"missing executable assertion for {row['test_name']}"
    assertion(row)
