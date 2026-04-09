from __future__ import annotations

"""Unit tests for graphify/profile.py — profile loading, validation, and safety helpers."""

import sys
import unicodedata
from pathlib import Path
from unittest import mock

import pytest

from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    load_profile,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_profile,
    validate_vault_path,
)


# ---------------------------------------------------------------------------
# _deep_merge tests
# ---------------------------------------------------------------------------


def test_deep_merge_nested_override():
    base = {"a": {"b": 1, "c": 2}}
    override = {"a": {"b": 99}}
    assert _deep_merge(base, override) == {"a": {"b": 99, "c": 2}}


def test_deep_merge_non_overlapping():
    assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_deep_merge_override_replaces_non_dict():
    assert _deep_merge({"a": {"b": 1}}, {"a": "string"}) == {"a": "string"}


def test_deep_merge_does_not_mutate_base():
    base = {"a": {"b": 1}}
    _deep_merge(base, {"a": {"b": 99}})
    assert base == {"a": {"b": 1}}


# ---------------------------------------------------------------------------
# load_profile tests
# ---------------------------------------------------------------------------


def test_load_profile_no_profile_returns_defaults(tmp_path):
    result = load_profile(tmp_path)
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
    assert result["folder_mapping"]["moc"] == "Atlas/Maps/"


def test_load_profile_with_yaml(tmp_path):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text(
        'folder_mapping:\n  moc: "Custom/Maps/"\n', encoding="utf-8"
    )
    result = load_profile(tmp_path)
    assert result["folder_mapping"]["moc"] == "Custom/Maps/"
    # Other defaults preserved (D-02)
    assert result["folder_mapping"]["thing"] == "Atlas/Dots/Things/"


def test_load_profile_empty_yaml_returns_defaults(tmp_path):
    """Empty YAML returns None from safe_load — guarded by `or {}` (Pitfall 1)."""
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text("", encoding="utf-8")
    result = load_profile(tmp_path)
    assert result == _deep_merge(_DEFAULT_PROFILE, {})


def test_load_profile_invalid_yaml_prints_errors(tmp_path, capsys):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text("unknown_key: 1\n", encoding="utf-8")
    result = load_profile(tmp_path)
    captured = capsys.readouterr()
    assert "[graphify] profile error:" in captured.err
    assert "Unknown profile key 'unknown_key'" in captured.err
    # Falls back to defaults
    assert result == _deep_merge(_DEFAULT_PROFILE, {})


def test_load_profile_pyyaml_not_installed(tmp_path, capsys):
    """When PyYAML is not available, fall back to defaults with stderr message (D-04)."""
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text("folder_mapping:\n  moc: Custom/\n", encoding="utf-8")

    with mock.patch.dict(sys.modules, {"yaml": None}):
        result = load_profile(tmp_path)

    captured = capsys.readouterr()
    assert "PyYAML not installed" in captured.err
    assert "pip install graphifyy[obsidian]" in captured.err
    assert result == _deep_merge(_DEFAULT_PROFILE, {})


# ---------------------------------------------------------------------------
# validate_profile tests
# ---------------------------------------------------------------------------


def test_validate_profile_valid_empty_dict():
    assert validate_profile({}) == []


def test_validate_profile_valid_full():
    profile = {
        "folder_mapping": {"moc": "Maps/", "default": "Notes/"},
        "naming": {"convention": "kebab-case"},
        "merge": {"strategy": "skip", "preserve_fields": ["tags"]},
        "mapping_rules": [],
        "obsidian": {},
    }
    assert validate_profile(profile) == []


def test_validate_profile_not_dict():
    errors = validate_profile("string")
    assert len(errors) == 1
    assert "YAML mapping" in errors[0]


def test_validate_profile_unknown_key():
    errors = validate_profile({"bad_key": 1})
    assert len(errors) == 1
    assert "Unknown profile key 'bad_key'" in errors[0]


def test_validate_profile_invalid_naming_convention():
    errors = validate_profile({"naming": {"convention": "bad"}})
    assert len(errors) == 1
    assert "Invalid naming convention" in errors[0]


def test_validate_profile_invalid_merge_strategy():
    errors = validate_profile({"merge": {"strategy": "bad"}})
    assert len(errors) == 1
    assert "Invalid merge strategy" in errors[0]


def test_validate_profile_traversal_in_folder_mapping():
    errors = validate_profile({"folder_mapping": {"moc": "../escape"}})
    assert len(errors) == 1
    assert ".." in errors[0]


def test_validate_profile_collects_multiple_errors():
    """D-03: collect all errors, not fail-on-first."""
    profile = {"key1": 1, "key2": 2, "key3": 3}
    errors = validate_profile(profile)
    assert len(errors) == 3


def test_validate_profile_mapping_rules_not_list():
    errors = validate_profile({"mapping_rules": "not a list"})
    assert len(errors) == 1
    assert "mapping_rules" in errors[0]


def test_validate_profile_preserve_fields_not_list():
    errors = validate_profile({"merge": {"preserve_fields": "not a list"}})
    assert len(errors) == 1
    assert "preserve_fields" in errors[0]


# ---------------------------------------------------------------------------
# validate_vault_path tests
# ---------------------------------------------------------------------------


def test_validate_vault_path_safe(tmp_path):
    result = validate_vault_path("Atlas/Maps/", tmp_path)
    assert result == (tmp_path / "Atlas" / "Maps").resolve()


def test_validate_vault_path_traversal_raises(tmp_path):
    with pytest.raises(ValueError, match="would escape"):
        validate_vault_path("../escape", tmp_path)


def test_validate_vault_path_absolute_outside_raises(tmp_path):
    with pytest.raises(ValueError, match="would escape"):
        validate_vault_path("/etc/passwd", tmp_path)


# ---------------------------------------------------------------------------
# safe_frontmatter_value tests
# ---------------------------------------------------------------------------


def test_safe_frontmatter_value_clean():
    assert safe_frontmatter_value("clean text") == "clean text"


def test_safe_frontmatter_value_colon():
    assert safe_frontmatter_value("has: colon") == '"has: colon"'


def test_safe_frontmatter_value_hash():
    assert safe_frontmatter_value("has #tag") == '"has #tag"'


def test_safe_frontmatter_value_quotes_and_colon():
    result = safe_frontmatter_value('has "quotes" and: colon')
    assert result == '"has \\"quotes\\" and: colon"'


def test_safe_frontmatter_value_newline():
    result = safe_frontmatter_value("line\nbreak")
    assert "\n" not in result
    assert "line break" in result


def test_safe_frontmatter_value_carriage_return():
    result = safe_frontmatter_value("line\rbreak")
    assert "\r" not in result


# ---------------------------------------------------------------------------
# safe_tag tests
# ---------------------------------------------------------------------------


def test_safe_tag_normal():
    assert safe_tag("My Community") == "my-community"


def test_safe_tag_leading_digit():
    assert safe_tag("123 Numbers") == "x123-numbers"


def test_safe_tag_special_chars():
    assert safe_tag("a/b+c") == "a-b-c"


def test_safe_tag_empty():
    assert safe_tag("") == "community"


def test_safe_tag_slashes_and_plus():
    assert safe_tag("slashes/and+plus") == "slashes-and-plus"


# ---------------------------------------------------------------------------
# safe_filename tests
# ---------------------------------------------------------------------------


def test_safe_filename_normal():
    assert safe_filename("Normal Name") == "Normal Name"


def test_safe_filename_illegal_chars():
    result = safe_filename('file: "bad"')
    assert ":" not in result
    assert '"' not in result


def test_safe_filename_length_cap():
    long_name = "a" * 250
    result = safe_filename(long_name)
    assert len(result) <= 201
    # Ends with 8 hex chars after underscore
    assert result[-9] == "_"
    assert all(c in "0123456789abcdef" for c in result[-8:])


def test_safe_filename_nfc_normalization():
    """e + combining acute accent should become single NFC codepoint."""
    decomposed = "e\u0301"
    result = safe_filename(decomposed)
    assert result == unicodedata.normalize("NFC", decomposed)


def test_safe_filename_empty_label():
    assert safe_filename("") == "unnamed"


def test_safe_filename_preserves_case():
    assert safe_filename("MyClass") == "MyClass"
