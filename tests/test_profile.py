from __future__ import annotations

"""Minimal failing tests for profile.py TDD RED phase."""

from graphify.profile import (
    load_profile,
    validate_profile,
    validate_vault_path,
    safe_frontmatter_value,
    safe_tag,
    safe_filename,
    _DEFAULT_PROFILE,
    _deep_merge,
)


def test_safe_tag_normal():
    assert safe_tag("My Community") == "my-community"


def test_safe_filename_normal():
    assert safe_filename("Normal Name") == "Normal Name"


def test_load_profile_no_profile_returns_defaults(tmp_path):
    result = load_profile(tmp_path)
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
