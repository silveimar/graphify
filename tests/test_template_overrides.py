from __future__ import annotations

"""Phase 56 — CFG-01 (override surface) + CFG-02 (collision matrix) tests."""

from pathlib import Path
from textwrap import dedent

import pytest

from graphify.profile import validate_profile, validate_profile_preflight


# ---------------------------------------------------------------------------
# CFG-02 §1 — Duplicate id (pattern) in mapping_rule_templates
# ---------------------------------------------------------------------------

def test_collision_duplicate_rule_id_pattern_in_mapping_rule_templates_detected():
    """Two mapping_rule_templates entries pointing at the same rule_id collide."""
    profile = {
        "mapping_rule_templates": [
            {"match": "rule_id", "pattern": "auth_rule", "template": "templates/a.md"},
            {"match": "rule_id", "pattern": "auth_rule", "template": "templates/b.md"},
        ]
    }
    errors = validate_profile(profile)
    assert any(
        "mapping_rule_templates[1]" in e
        and "duplicate pattern" in e
        and "'auth_rule'" in e
        and "mapping_rule_templates[0]" in e
        for e in errors
    ), errors


def test_collision_distinct_rule_ids_in_mapping_rule_templates_not_detected():
    """Two mapping_rule_templates entries with distinct patterns do not collide."""
    profile = {
        "mapping_rule_templates": [
            {"match": "rule_id", "pattern": "auth_rule", "template": "templates/a.md"},
            {"match": "rule_id", "pattern": "billing_rule", "template": "templates/b.md"},
        ]
    }
    errors = validate_profile(profile)
    assert not any(
        "mapping_rule_templates" in e and "duplicate pattern" in e
        for e in errors
    ), errors


# ---------------------------------------------------------------------------
# CFG-02 §2 — Duplicate exact pattern within community_templates
# ---------------------------------------------------------------------------

def test_collision_duplicate_pattern_in_community_templates_detected():
    """Two community_templates entries with the same pattern collide."""
    profile = {
        "community_templates": [
            {"match": "label", "pattern": "transformer*", "template": "templates/a.md"},
            {"match": "label", "pattern": "transformer*", "template": "templates/b.md"},
        ]
    }
    errors = validate_profile(profile)
    assert any(
        "community_templates[1]" in e
        and "duplicate pattern" in e
        and "'transformer*'" in e
        and "community_templates[0]" in e
        for e in errors
    ), errors


def test_collision_similar_but_distinct_patterns_in_community_templates_not_detected():
    """Similar but textually distinct patterns (transformer* vs transformers*) do not collide."""
    profile = {
        "community_templates": [
            {"match": "label", "pattern": "transformer*", "template": "templates/a.md"},
            {"match": "label", "pattern": "transformers*", "template": "templates/b.md"},
        ]
    }
    errors = validate_profile(profile)
    assert not any(
        "community_templates" in e and "duplicate pattern" in e
        for e in errors
    ), errors


# ---------------------------------------------------------------------------
# CFG-02 §3 — Duplicate note_type in note_type_templates
# ---------------------------------------------------------------------------

def test_collision_duplicate_note_type_in_note_type_templates_detected():
    """Two note_type_templates entries targeting the same note_type collide."""
    profile = {
        "note_type_templates": [
            {"match": "note_type", "pattern": "code", "template": "templates/a.md"},
            {"match": "note_type", "pattern": "code", "template": "templates/b.md"},
        ]
    }
    errors = validate_profile(profile)
    assert any(
        "note_type_templates[1]" in e
        and "duplicate pattern" in e
        and "'code'" in e
        and "note_type_templates[0]" in e
        for e in errors
    ), errors


def test_collision_distinct_note_types_in_note_type_templates_not_detected():
    """Two note_type_templates entries for distinct note_types do not collide."""
    profile = {
        "note_type_templates": [
            {"match": "note_type", "pattern": "code", "template": "templates/a.md"},
            {"match": "note_type", "pattern": "moc", "template": "templates/b.md"},
        ]
    }
    errors = validate_profile(profile)
    assert not any(
        "note_type_templates" in e and "duplicate pattern" in e
        for e in errors
    ), errors


# ---------------------------------------------------------------------------
# CFG-02 §4 — Cross-chain dataview_queries.<note_type> collision
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(body).lstrip("\n"), encoding="utf-8")


def test_collision_dataview_queries_across_extends_chain_detected(tmp_path):
    """When extends-parent and child both write dataview_queries.code, preflight
    surfaces a collision error enumerating BOTH source paths."""
    pytest.importorskip("yaml")

    vault = tmp_path / "vault"
    graphify_dir = vault / ".graphify"

    # Seed: pre-establishes dataview_queries as a dict so per-leaf recursion
    # captures both grandparent and child writes (per Plan 01 SUMMARY recursion
    # caveat).
    _write_yaml(graphify_dir / "seed.yaml", """
        dataview_queries:
          moc: "TABLE seed FROM #t/moc"
    """)
    _write_yaml(graphify_dir / "parent.yaml", """
        includes:
          - seed.yaml
        dataview_queries:
          code: "TABLE parent FROM #t/code"
    """)
    _write_yaml(graphify_dir / "profile.yaml", """
        extends: parent.yaml
        dataview_queries:
          code: "TABLE child FROM #t/code"
    """)

    result = validate_profile_preflight(vault)

    collision_errors = [
        e for e in result.errors
        if "dataview_queries.code" in e and "collision across composition chain" in e
    ]
    assert collision_errors, (
        f"Expected dataview_queries.code collision error; got: {result.errors}"
    )
    assert len(collision_errors) == 1, collision_errors
    msg = collision_errors[0]
    assert "parent.yaml" in msg, msg
    assert "profile.yaml" in msg, msg


def test_collision_dataview_queries_single_source_not_detected(tmp_path):
    """When dataview_queries.code is written by exactly one source in the
    composition chain, no collision error is surfaced."""
    pytest.importorskip("yaml")

    vault = tmp_path / "vault"
    graphify_dir = vault / ".graphify"

    _write_yaml(graphify_dir / "seed.yaml", """
        dataview_queries:
          moc: "TABLE seed FROM #t/moc"
    """)
    _write_yaml(graphify_dir / "parent.yaml", """
        includes:
          - seed.yaml
        dataview_queries:
          code: "TABLE only FROM #t/code"
    """)
    _write_yaml(graphify_dir / "profile.yaml", """
        extends: parent.yaml
        dataview_queries:
          moc: "TABLE child_moc FROM #t/moc"
    """)

    result = validate_profile_preflight(vault)

    assert not any(
        "dataview_queries.code" in e and "collision across composition chain" in e
        for e in result.errors
    ), result.errors
