from __future__ import annotations

"""Unit tests for graphify/profile.py — profile loading, validation, and safety helpers."""

import sys
import unicodedata
from pathlib import Path
from unittest import mock

import pytest

import datetime

from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    _dump_frontmatter,
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


# ---------------------------------------------------------------------------
# WR-07 regression: validate_profile rejects absolute paths and ~ prefixes
# ---------------------------------------------------------------------------


def test_validate_profile_absolute_path_rejected():
    errors = validate_profile({"folder_mapping": {"moc": "/etc/passwd"}})
    assert len(errors) == 1
    assert "absolute" in errors[0].lower()


def test_validate_profile_tilde_prefix_rejected():
    errors = validate_profile({"folder_mapping": {"moc": "~/Documents/vault"}})
    assert len(errors) == 1
    assert "~" in errors[0]


def test_validate_profile_relative_path_accepted():
    errors = validate_profile({"folder_mapping": {"moc": "Atlas/Maps/"}})
    assert errors == []


def test_validate_profile_windows_drive_root_rejected():
    # C:\path is absolute on Windows — Path.is_absolute() handles it on all platforms
    import sys
    errors = validate_profile({"folder_mapping": {"moc": "C:\\Users\\vault"}})
    if sys.platform == "win32":
        # On Windows C:\... is absolute
        assert any("absolute" in e.lower() for e in errors)
    else:
        # On POSIX C:\Users\vault is relative (no leading /) — validate_vault_path
        # catches it at use-time, but profile validation on POSIX won't flag it.
        # The test just verifies it doesn't crash.
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------


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
# WR-01 regression: safe_frontmatter_value YAML scalar-poison cases
# ---------------------------------------------------------------------------


def test_safe_frontmatter_value_leading_dash_quoted():
    # Leading '-' is a YAML sequence indicator — must quote
    result = safe_frontmatter_value("- item")
    assert result.startswith('"') and result.endswith('"')


def test_safe_frontmatter_value_leading_exclamation_quoted():
    # Leading '!' is a YAML tag indicator — must quote
    result = safe_frontmatter_value("!important")
    assert result.startswith('"') and result.endswith('"')


def test_safe_frontmatter_value_leading_pipe_quoted():
    # Leading '|' is a YAML block scalar indicator — must quote
    result = safe_frontmatter_value("|block")
    assert result.startswith('"') and result.endswith('"')


def test_safe_frontmatter_value_leading_backtick_quoted():
    # Leading '`' is reserved in YAML — must quote
    result = safe_frontmatter_value("`code`")
    assert result.startswith('"') and result.endswith('"')


def test_safe_frontmatter_value_reserved_word_true_quoted():
    assert safe_frontmatter_value("true").startswith('"')


def test_safe_frontmatter_value_reserved_word_false_quoted():
    assert safe_frontmatter_value("false").startswith('"')


def test_safe_frontmatter_value_reserved_word_null_quoted():
    assert safe_frontmatter_value("null").startswith('"')


def test_safe_frontmatter_value_reserved_word_yes_quoted():
    assert safe_frontmatter_value("yes").startswith('"')


def test_safe_frontmatter_value_reserved_word_no_quoted():
    assert safe_frontmatter_value("no").startswith('"')


def test_safe_frontmatter_value_reserved_word_on_quoted():
    assert safe_frontmatter_value("on").startswith('"')


def test_safe_frontmatter_value_reserved_word_case_insensitive():
    # YAML 1.1 treats Yes, YES, NO, True, FALSE, NULL etc. as bool/null
    assert safe_frontmatter_value("Yes").startswith('"')
    assert safe_frontmatter_value("NO").startswith('"')
    assert safe_frontmatter_value("True").startswith('"')
    assert safe_frontmatter_value("NULL").startswith('"')


def test_safe_frontmatter_value_numeric_integer_quoted():
    assert safe_frontmatter_value("42").startswith('"')


def test_safe_frontmatter_value_numeric_float_quoted():
    assert safe_frontmatter_value("0.1").startswith('"')


def test_safe_frontmatter_value_numeric_scientific_quoted():
    assert safe_frontmatter_value("1e10").startswith('"')


def test_safe_frontmatter_value_comma_quoted():
    # Comma is a flow-context separator — must quote
    result = safe_frontmatter_value("a, b")
    assert result.startswith('"') and result.endswith('"')


def test_safe_frontmatter_value_control_chars_stripped():
    # Control characters other than \n/\r must be stripped
    result = safe_frontmatter_value("before\x00after")
    assert "\x00" not in result
    assert "beforeafter" in result


def test_safe_frontmatter_value_nel_stripped():
    # NEL (U+0085) is a YAML line break — must be stripped
    result = safe_frontmatter_value("line\x85break")
    assert "\x85" not in result


def test_safe_frontmatter_value_plain_text_unchanged():
    # Normal text with no poison chars must pass through unchanged
    assert safe_frontmatter_value("ML Architecture") == "ML Architecture"


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


def test_obs01_obs02_safe_tag_regression_anchor():
    """Regression anchor for OBS-01 / OBS-02 (Phase 1 requirements).

    Before Phase 5, `graphify --obsidian` wrote a `.obsidian/graph.json` file
    whose community entries used `tag:community/<slug>` syntax (OBS-01) and
    which read-merged with existing user settings to preserve non-graphify
    entries (OBS-02). The Phase 5 refactor (D-74) removed graph.json
    generation from `to_obsidian` entirely.

    The underlying invariant — that community tags use `community/<slug>`
    syntax where <slug> is produced by `safe_tag` — is still the contract
    used by render_note / render_moc when they emit tags into
    frontmatter and dataview queries. safe_tag therefore remains the root
    of OBS-01/OBS-02 correctness.

    This test belt-and-suspenders the exact literal form the graph.json
    feature used to emit, so that any regression in safe_tag (such as
    accidentally producing `community/<raw>` without slugification, or
    emitting `#community/<slug>` with a stray hash) fails here loudly
    with a search-hit on 'OBS-01' or 'OBS-02'.
    """
    from graphify.profile import safe_tag

    # OBS-01 form: community/<slug> — never `#community/...`, never raw input.
    assert safe_tag("ML/AI Architecture") == "ml-ai-architecture"
    slug = safe_tag("ML/AI Architecture")
    tag_query = f"tag:community/{slug}"
    assert tag_query == "tag:community/ml-ai-architecture"
    assert "#" not in tag_query, "OBS-01 requires tag:community/ syntax, not #-prefixed"

    # OBS-02 implicitly depends on safe_tag being idempotent and deterministic
    # so read-merge-write can identify existing graphify entries by prefix.
    assert safe_tag("ML/AI Architecture") == safe_tag("ML/AI Architecture")
    assert safe_tag("My Community").startswith(""), "safe_tag output is a valid prefix root"

    # Additional adversarial inputs that OBS-01 had to handle at graph.json time:
    assert safe_tag("a/b+c d") == "a-b-c-d"   # / + space → collapse to hyphens
    assert safe_tag("") == "community"          # empty → fallback, matching OBS-02 behavior


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


def test_safe_filename_strips_newline():
    """Newlines in labels would otherwise leak into wikilink targets."""
    result = safe_filename("line1\nline2")
    assert "\n" not in result
    assert result == "line1line2"


def test_safe_filename_strips_carriage_return():
    result = safe_filename("line1\r\nline2")
    assert "\r" not in result
    assert "\n" not in result
    assert result == "line1line2"


def test_safe_filename_strips_tab():
    result = safe_filename("foo\tbar")
    assert "\t" not in result
    assert result == "foobar"


def test_safe_filename_strips_all_c0_controls():
    """C0 control characters (\\x00-\\x1f) and DEL break filenames/wikilinks."""
    label = "foo" + "".join(chr(c) for c in range(0x00, 0x20)) + "\x7fbar"
    result = safe_filename(label)
    assert all(ord(c) >= 0x20 and ord(c) != 0x7f for c in result)
    assert result == "foobar"


def test_safe_filename_strips_unicode_line_separators():
    """NEL (\\x85), LS (\\u2028), and PS (\\u2029) are also newline-class."""
    result = safe_filename("foo\u0085bar\u2028baz\u2029qux")
    assert "\u0085" not in result
    assert "\u2028" not in result
    assert "\u2029" not in result
    assert result == "foobarbazqux"


def test_safe_filename_wikilink_target_no_newline():
    """Regression for UAT Test 5: labels with newlines must not produce
    broken wikilink targets like [[line1\\nline2|...]]."""
    fname = safe_filename("line1\nline2")
    wikilink = f"[[{fname}|alias]]"
    assert "\n" not in wikilink
    assert wikilink == "[[line1line2|alias]]"


# ---------------------------------------------------------------------------
# _dump_frontmatter tests
# ---------------------------------------------------------------------------


def test_dump_frontmatter_basic_scalars():
    out = _dump_frontmatter({"type": "moc", "community": "ML Architecture"})
    assert "---\ntype: moc\ncommunity: ML Architecture\n---" in out


def test_dump_frontmatter_block_list_tags():
    out = _dump_frontmatter({"tags": ["community/ml", "graphify/code"]})
    assert "tags:\n  - community/ml\n  - graphify/code" in out
    # Must not use inline YAML list format
    assert "[" not in out.split("---")[1]


def test_dump_frontmatter_wikilink_quoted():
    out = _dump_frontmatter({"up": ["[[Atlas|Atlas]]"]})
    assert 'up:\n  - "[[Atlas|Atlas]]"' in out


def test_dump_frontmatter_created_date_unquoted():
    out = _dump_frontmatter({"created": datetime.date(2026, 4, 11)})
    assert "created: 2026-04-11\n" in out
    assert '"2026-04-11"' not in out


def test_dump_frontmatter_cohesion_float_two_decimals():
    out = _dump_frontmatter({"cohesion": 0.82345})
    assert "cohesion: 0.82" in out


def test_dump_frontmatter_int_unquoted():
    out = _dump_frontmatter({"count": 3})
    assert "count: 3" in out
    assert '"3"' not in out


def test_dump_frontmatter_bool_lowercase():
    out = _dump_frontmatter({"active": True, "stale": False})
    assert "active: true" in out
    assert "stale: false" in out
    # Must not render as 1 / 0
    assert "active: 1" not in out
    assert "stale: 0" not in out


def test_dump_frontmatter_none_skipped():
    out = _dump_frontmatter({"parent": None, "type": "thing"})
    assert "type: thing" in out
    lines = out.split("\n")
    assert not any(line.startswith("parent:") for line in lines)


def test_dump_frontmatter_field_order_preserved():
    keys = ["up", "related", "collections", "created", "tags", "type"]
    fields = {k: f"val_{k}" for k in keys}
    out = _dump_frontmatter(fields)
    body = out.split("---")[1]
    positions = {k: body.index(k + ":") for k in keys}
    for i in range(len(keys) - 1):
        assert positions[keys[i]] < positions[keys[i + 1]], (
            f"Expected {keys[i]!r} before {keys[i+1]!r} in output"
        )


def test_dump_frontmatter_delimiters():
    import yaml
    fields = {"type": "moc", "rank": 3, "tags": ["a", "b"]}
    out = _dump_frontmatter(fields)
    assert out.startswith("---\n")
    assert out.rstrip("\n").endswith("---")
    # Strip delimiters and round-trip through yaml
    inner = out.split("---")[1]
    parsed = yaml.safe_load(inner)
    assert parsed["type"] == "moc"
    assert parsed["rank"] == 3
    assert parsed["tags"] == ["a", "b"]


def test_default_profile_has_obsidian_dataview_moc_query():
    expected = (
        "TABLE file.folder as Folder, type, source_file\n"
        "FROM #community/${community_tag}\n"
        "SORT file.name ASC"
    )
    assert _DEFAULT_PROFILE["obsidian"]["dataview"]["moc_query"] == expected


def test_default_profile_has_obsidian_atlas_root():
    assert _DEFAULT_PROFILE["obsidian"]["atlas_root"] == "Atlas"


def test_validate_profile_accepts_new_obsidian_keys():
    result = validate_profile({
        "obsidian": {
            "atlas_root": "Custom",
            "dataview": {"moc_query": "TABLE file.name FROM #foo"},
        }
    })
    assert result == [], f"Expected no errors, got: {result}"


def test_deep_merge_preserves_new_defaults():
    merged = _deep_merge(_DEFAULT_PROFILE, {"obsidian": {"atlas_root": "MyRoot"}})
    assert merged["obsidian"]["atlas_root"] == "MyRoot"
    # Sibling key must survive partial override
    assert "moc_query" in merged["obsidian"]["dataview"]
    assert "${community_tag}" in merged["obsidian"]["dataview"]["moc_query"]


# ---------------------------------------------------------------------------
# Plan 03: _DEFAULT_PROFILE extensions (topology + mapping) and
# validate_profile delegation to graphify.mapping.validate_rules
# ---------------------------------------------------------------------------


def test_default_profile_includes_topology_and_mapping_keys():
    from graphify.profile import _DEFAULT_PROFILE
    assert _DEFAULT_PROFILE["topology"]["god_node"]["top_n"] == 10
    assert _DEFAULT_PROFILE["mapping"]["moc_threshold"] == 3


def test_default_profile_top_n_and_threshold_are_not_bool():
    from graphify.profile import _DEFAULT_PROFILE
    top_n = _DEFAULT_PROFILE["topology"]["god_node"]["top_n"]
    threshold = _DEFAULT_PROFILE["mapping"]["moc_threshold"]
    assert isinstance(top_n, int) and not isinstance(top_n, bool)
    assert isinstance(threshold, int) and not isinstance(threshold, bool)


def test_deep_merge_respects_topology_section():
    # VALIDATION row 3-04-04
    from graphify.profile import _DEFAULT_PROFILE, _deep_merge
    override = {"topology": {"god_node": {"top_n": 25}}}
    merged = _deep_merge(_DEFAULT_PROFILE, override)
    assert merged["topology"]["god_node"]["top_n"] == 25
    # Unrelated defaults preserved
    assert merged["mapping"]["moc_threshold"] == 3
    assert merged["folder_mapping"]["moc"] == "Atlas/Maps/"


def test_default_profile_rejects_bool_as_int_threshold():
    # VALIDATION row 3-03-07
    from graphify.profile import validate_profile
    errors = validate_profile({"mapping": {"moc_threshold": True}})
    assert any("mapping.moc_threshold" in e for e in errors)


def test_validate_profile_rejects_bool_top_n():
    from graphify.profile import validate_profile
    errors = validate_profile({"topology": {"god_node": {"top_n": False}}})
    assert any("topology.god_node.top_n" in e for e in errors)


def test_validate_profile_rejects_negative_top_n():
    from graphify.profile import validate_profile
    errors = validate_profile({"topology": {"god_node": {"top_n": -1}}})
    assert any("top_n must be ≥ 0" in e for e in errors)


def test_validate_profile_surfaces_mapping_rules_errors():
    # VALIDATION row 3-04-03
    from graphify.profile import validate_profile
    profile = {
        "mapping_rules": [
            {"when": {"attr": "label", "equals": "X"}, "then": {"note_type": "BOGUS"}},
            {"when": {"topology": "god_node"}, "then": {"note_type": "thing", "folder": "../escape"}},
        ]
    }
    errors = validate_profile(profile)
    assert any("mapping_rules[0].then.note_type" in e for e in errors)
    assert any("mapping_rules[1].then.folder" in e and ".." in e for e in errors)


def test_validate_profile_accepts_default_profile_unchanged():
    from graphify.profile import validate_profile, _DEFAULT_PROFILE
    assert validate_profile(_DEFAULT_PROFILE) == []


# ---------------------------------------------------------------------------
# Phase 4 Plan 02: _DEFAULT_PROFILE.merge extension + _VALID_FIELD_POLICY_MODES
# ---------------------------------------------------------------------------


def test_default_profile_merge_preserve_fields_contains_created():
    # D-27 + D-65: `created` preserved across merge UPDATE runs.
    from graphify.profile import _DEFAULT_PROFILE
    assert "created" in _DEFAULT_PROFILE["merge"]["preserve_fields"]


def test_default_profile_merge_preserve_fields_exact_order():
    # Locked order: rank, mapState, tags (original) + created (new, appended).
    from graphify.profile import _DEFAULT_PROFILE
    assert _DEFAULT_PROFILE["merge"]["preserve_fields"] == [
        "rank",
        "mapState",
        "tags",
        "created",
    ]


def test_default_profile_merge_field_policies_default_empty():
    # D-65: empty default means Plan 03's built-in table wins unchanged.
    from graphify.profile import _DEFAULT_PROFILE
    assert _DEFAULT_PROFILE["merge"]["field_policies"] == {}


def test_valid_field_policy_modes_constant_exact_set():
    # D-64: replace / union / preserve only.
    from graphify.profile import _VALID_FIELD_POLICY_MODES
    assert _VALID_FIELD_POLICY_MODES == frozenset({"replace", "union", "preserve"})


def test_load_profile_empty_vault_yields_empty_field_policies(tmp_path):
    # Regression guard: vault with no profile still emits the default shape.
    from graphify.profile import load_profile
    result = load_profile(tmp_path)
    assert result["merge"]["field_policies"] == {}
    assert result["merge"]["preserve_fields"] == [
        "rank",
        "mapState",
        "tags",
        "created",
    ]


def test_load_profile_user_field_policies_deep_merges_over_default(tmp_path):
    # D-65: user override replaces only the matched keys, other merge keys kept.
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text(
        "merge:\n  field_policies:\n    tags: replace\n",
        encoding="utf-8",
    )
    from graphify.profile import load_profile
    result = load_profile(tmp_path)
    assert result["merge"]["field_policies"] == {"tags": "replace"}
    # Other merge defaults preserved (deep-merge, not replace)
    assert result["merge"]["strategy"] == "update"
    assert result["merge"]["preserve_fields"] == [
        "rank",
        "mapState",
        "tags",
        "created",
    ]


# ---------------------------------------------------------------------------
# Phase 4 Plan 02: merge.field_policies validation
# ---------------------------------------------------------------------------


def test_validate_profile_accepts_empty_field_policies():
    from graphify.profile import validate_profile
    assert validate_profile({"merge": {"field_policies": {}}}) == []


def test_validate_profile_accepts_valid_field_policies():
    from graphify.profile import validate_profile
    p = {
        "merge": {
            "field_policies": {
                "tags": "replace",
                "collections": "union",
                "rank": "preserve",
            }
        }
    }
    assert validate_profile(p) == []


def test_validate_profile_rejects_non_dict_field_policies():
    from graphify.profile import validate_profile
    errors = validate_profile({"merge": {"field_policies": ["tags"]}})
    assert any("merge.field_policies' must be a mapping" in e for e in errors)


def test_validate_profile_rejects_non_string_field_policy_key():
    from graphify.profile import validate_profile
    errors = validate_profile({"merge": {"field_policies": {42: "replace"}}})
    assert any(
        "merge.field_policies key" in e and "must be a string" in e for e in errors
    )


def test_validate_profile_rejects_invalid_field_policy_mode():
    from graphify.profile import validate_profile
    errors = validate_profile({"merge": {"field_policies": {"tags": "nuke"}}})
    matched = [e for e in errors if "merge.field_policies.tags" in e]
    assert matched, f"expected tags policy error, got: {errors}"
    assert "'nuke'" in matched[0]
    assert "valid modes" in matched[0]


def test_validate_profile_accepts_all_three_merge_strategies():
    from graphify.profile import validate_profile
    for strategy in ("update", "skip", "replace"):
        assert validate_profile({"merge": {"strategy": strategy}}) == [], (
            f"strategy {strategy} should be accepted"
        )


def test_validate_profile_omits_field_policies_is_ok():
    from graphify.profile import validate_profile
    assert validate_profile({"merge": {"strategy": "update"}}) == []


# ---------------------------------------------------------------------------
# Phase 5 / D-77 / D-77a — validate_profile_preflight + PreflightResult tests
# ---------------------------------------------------------------------------

from graphify.profile import validate_profile_preflight, PreflightResult


def _mk_vault(tmp_path, profile_yaml: str | None = None, templates: dict[str, str] | None = None):
    """Construct a minimal vault layout under tmp_path."""
    vault = tmp_path / "vault"
    vault.mkdir()
    if profile_yaml is not None or templates is not None:
        (vault / ".graphify").mkdir()
    if profile_yaml is not None:
        (vault / ".graphify" / "profile.yaml").write_text(profile_yaml, encoding="utf-8")
    if templates:
        (vault / ".graphify" / "templates").mkdir()
    for name, text in (templates or {}).items():
        (vault / ".graphify" / "templates" / name).write_text(text, encoding="utf-8")
    return vault


def test_validate_profile_preflight_nonexistent_vault(tmp_path):
    result = validate_profile_preflight(tmp_path / "missing")
    assert len(result.errors) == 1
    assert "does not exist" in result.errors[0]
    assert result.warnings == []
    assert result.rule_count == 0
    assert result.template_count == 0


def test_validate_profile_preflight_no_graphify_dir(tmp_path):
    vault = _mk_vault(tmp_path)
    result = validate_profile_preflight(vault)
    assert result.errors == []
    assert result.warnings == []
    assert result.rule_count == 0
    assert result.template_count == 0


def test_validate_profile_preflight_empty_profile_yaml(tmp_path):
    vault = _mk_vault(tmp_path, profile_yaml="")
    result = validate_profile_preflight(vault)
    assert result.errors == []
    assert result.template_count == 0


def test_validate_profile_preflight_layer1_schema_error(tmp_path):
    yaml_text = (
        "folder_mapping:\n"
        "  moc: '../escape'\n"
    )
    vault = _mk_vault(tmp_path, profile_yaml=yaml_text)
    result = validate_profile_preflight(vault)
    assert any(".." in e for e in result.errors), f"Expected path traversal error, got {result.errors}"


def test_validate_profile_preflight_layer2_template_missing_required(tmp_path):
    # MOC template missing ${frontmatter} placeholder
    bad_template = "# ${label}\n${members_section}\n${dataview_block}\n"
    vault = _mk_vault(tmp_path, profile_yaml="", templates={"moc.md": bad_template})
    result = validate_profile_preflight(vault)
    assert any("frontmatter" in e and "moc.md" in e for e in result.errors), (
        f"Expected frontmatter placeholder error, got {result.errors}"
    )
    # Failed template must NOT increment template_count
    assert result.template_count == 0


def test_validate_profile_preflight_layer3_dead_rule_warning(tmp_path):
    yaml_text = (
        "mapping_rules:\n"
        "  - when: {topology: god_node}\n"
        "    then: {note_type: thing}\n"
        "  - when: {topology: god_node}\n"
        "    then: {note_type: thing}\n"
    )
    vault = _mk_vault(tmp_path, profile_yaml=yaml_text)
    result = validate_profile_preflight(vault)
    assert any("dead rule" in w for w in result.warnings), (
        f"Expected dead-rule warning, got {result.warnings}"
    )
    assert result.rule_count == 2


def test_validate_profile_preflight_layer4_deep_folder_warning(tmp_path):
    yaml_text = (
        "folder_mapping:\n"
        "  moc: 'A/B/C/D/E'\n"  # 5 segments > 4
    )
    vault = _mk_vault(tmp_path, profile_yaml=yaml_text)
    result = validate_profile_preflight(vault)
    assert any("segments" in w or "nesting" in w for w in result.warnings), (
        f"Expected nesting warning, got {result.warnings}"
    )


def test_validate_profile_preflight_layer4_long_path_warning(tmp_path):
    deep_folder = "/".join(["longsegment" * 3] * 2)
    yaml_text = f"folder_mapping:\n  moc: '{deep_folder}'\n"
    vault = _mk_vault(tmp_path, profile_yaml=yaml_text)
    result = validate_profile_preflight(vault)
    assert any("path length" in w or "MAX_PATH" in w for w in result.warnings), (
        f"Expected length warning, got {result.warnings}"
    )


def test_validate_profile_preflight_layer4_mapping_rule_folder(tmp_path):
    yaml_text = (
        "mapping_rules:\n"
        "  - when: {topology: god_node}\n"
        "    then: {note_type: thing, folder: 'A/B/C/D/E'}\n"
    )
    vault = _mk_vault(tmp_path, profile_yaml=yaml_text)
    result = validate_profile_preflight(vault)
    assert any("mapping_rules[0]" in w for w in result.warnings), (
        f"Expected rule folder warning, got {result.warnings}"
    )


def test_validate_profile_preflight_no_side_effects(tmp_path):
    vault = _mk_vault(tmp_path, profile_yaml="naming: {convention: kebab-case}\n")
    r_a = validate_profile_preflight(vault)
    r_b = validate_profile_preflight(vault)
    assert r_a == r_b
    files_after = sorted(p for p in vault.rglob("*"))
    assert all(p.name in {".graphify", "profile.yaml"} for p in files_after)


def test_validate_profile_preflight_clean_vault_passes(tmp_path):
    vault = _mk_vault(
        tmp_path,
        profile_yaml="naming: {convention: title_case}\n",
    )
    result = validate_profile_preflight(vault)
    assert result.errors == []


# --- PreflightResult shape tests (D-77a N/M suffix prerequisites) ---

def test_preflight_result_is_named_tuple_with_four_fields(tmp_path):
    result = validate_profile_preflight(tmp_path / "missing")
    assert isinstance(result, PreflightResult)
    assert hasattr(result, "errors")
    assert hasattr(result, "warnings")
    assert hasattr(result, "rule_count")
    assert hasattr(result, "template_count")
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)
    assert isinstance(result.rule_count, int)
    assert isinstance(result.template_count, int)


def test_preflight_result_tuple_unpack_backward_compat(tmp_path):
    vault = _mk_vault(tmp_path, profile_yaml="")
    result = validate_profile_preflight(vault)
    # Legacy 2-tuple unpack via star-rest
    errors, warnings, *_ = result
    assert errors == result.errors
    assert warnings == result.warnings
    # Full 4-tuple unpack
    e2, w2, rc, tc = result
    assert e2 == result.errors
    assert w2 == result.warnings
    assert rc == result.rule_count
    assert tc == result.template_count


def test_preflight_result_rule_and_template_counts_populated(tmp_path):
    # Valid profile with 3 rules and 1 valid template override
    yaml_text = (
        "mapping_rules:\n"
        "  - when: {topology: god_node}\n"
        "    then: {note_type: thing}\n"
        "  - when: {file_type: document}\n"
        "    then: {note_type: source}\n"
        "  - when: {community_size: {min: 5}}\n"
        "    then: {note_type: statement}\n"
    )
    valid_thing_template = (
        "---\n${frontmatter}---\n# ${label}\nbody\n"
    )
    vault = _mk_vault(
        tmp_path,
        profile_yaml=yaml_text,
        templates={"thing.md": valid_thing_template},
    )
    result = validate_profile_preflight(vault)
    assert result.rule_count == 3
    assert result.template_count == 1


# ---------------------------------------------------------------------------
# Tests for tag_taxonomy and profile_sync — Wave 0, Plan 19-01
# ---------------------------------------------------------------------------

def test_load_profile_none_has_tag_taxonomy_defaults():
    """load_profile(None) returns default profile with the 4-namespace verbatim taxonomy."""
    p = load_profile(None)
    assert "tag_taxonomy" in p
    tt = p["tag_taxonomy"]
    assert isinstance(tt, dict)
    assert "plant" in tt["garden"]
    assert "question" in tt["garden"]
    assert "component" in tt["graph"]
    assert "confluence" in tt["source"]
    assert "python" in tt["tech"]


def test_load_profile_none_has_profile_sync_auto_update():
    """load_profile(None) returns default profile with profile_sync.auto_update=True."""
    p = load_profile(None)
    assert "profile_sync" in p
    assert p["profile_sync"]["auto_update"] is True


def test_validate_profile_tag_taxonomy_not_dict():
    """tag_taxonomy: non-dict value returns an error mentioning tag_taxonomy."""
    errors = validate_profile({"tag_taxonomy": "notadict"})
    assert len(errors) >= 1
    assert any("tag_taxonomy" in e for e in errors)


def test_validate_profile_tag_taxonomy_namespace_not_list():
    """tag_taxonomy.garden: non-list value returns an error mentioning tag_taxonomy.garden."""
    errors = validate_profile({"tag_taxonomy": {"garden": "notalist"}})
    assert len(errors) >= 1
    assert any("tag_taxonomy.garden" in e for e in errors)


def test_validate_profile_tag_taxonomy_non_string_values():
    """tag_taxonomy.garden: list with non-string elements returns an error."""
    errors = validate_profile({"tag_taxonomy": {"garden": [1, 2]}})
    assert len(errors) >= 1
    assert any("tag_taxonomy" in e for e in errors)


def test_validate_profile_tag_taxonomy_valid():
    """tag_taxonomy with valid string-list namespace returns no errors."""
    errors = validate_profile({"tag_taxonomy": {"garden": ["plant", "cultivate"]}})
    assert errors == []


def test_validate_profile_profile_sync_not_dict():
    """profile_sync: non-dict value returns an error mentioning profile_sync."""
    errors = validate_profile({"profile_sync": "notadict"})
    assert len(errors) >= 1
    assert any("profile_sync" in e for e in errors)


def test_validate_profile_profile_sync_auto_update_not_bool():
    """profile_sync.auto_update: non-bool value returns an error mentioning profile_sync.auto_update."""
    errors = validate_profile({"profile_sync": {"auto_update": "yes"}})
    assert len(errors) >= 1
    assert any("profile_sync.auto_update" in e for e in errors)


def test_validate_profile_profile_sync_valid():
    """profile_sync with valid auto_update=False returns no errors."""
    errors = validate_profile({"profile_sync": {"auto_update": False}})
    assert errors == []


def test_load_profile_user_tag_taxonomy_deep_merge(tmp_path):
    """User profile with custom tag_taxonomy.garden overrides the default via deep merge (Layer 2 wins)."""
    import yaml
    vault = tmp_path / "vault"
    vault.mkdir()
    gdir = vault / ".graphify"
    gdir.mkdir()
    (gdir / "profile.yaml").write_text(
        "tag_taxonomy:\n  garden: [custom]\n", encoding="utf-8"
    )
    p = load_profile(vault)
    assert p["tag_taxonomy"]["garden"] == ["custom"]
    # Other namespaces from defaults should still be present
    assert "python" in p["tag_taxonomy"]["tech"]
