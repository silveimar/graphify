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


# ---------------------------------------------------------------------------
# CFG-01 §5 — D-56.05 render-time ladder + D-56.13 warn-and-fall-back
# ---------------------------------------------------------------------------

# Distinct markers so tests can assert WHICH tier won.
_BASE_MOC = """${frontmatter}
# Base MOC: ${label}

BASE_MOC_MARKER

${members_section}

${dataview_block}
"""

_OVERRIDE_MR = """${frontmatter}
# Mapping Rule Override: ${label}

OVERRIDE_MR_MARKER

${dataview_block}
"""

_OVERRIDE_CT = """${frontmatter}
# Community Template Override: ${label}

OVERRIDE_CT_MARKER

${members_section}

${dataview_block}
"""

_OVERRIDE_NT = """${frontmatter}
# Note-Type Override: ${label}

OVERRIDE_NT_MARKER

${dataview_block}
"""

_BASE_THING = """${frontmatter}
# Base Thing: ${label}

BASE_THING_MARKER

${connections_callout}
"""


def _ladder_vault(
    tmp_path: Path,
    *,
    write_mr_template: bool = True,
    write_ct_template: bool = True,
    write_nt_template: bool = True,
    profile_extras: str = "",
) -> Path:
    """Build a fully self-contained vault for ladder/warn-fallback tests.

    Three override template files share distinct markers; the profile lists
    point to each via mapping_rule_templates / community_templates / note_type_templates.
    Per-template booleans suppress writing the file (drives missing-file warns).
    """
    vault = tmp_path / "vault"
    g = vault / ".graphify"
    tmpl_dir = g / "templates"
    tmpl_dir.mkdir(parents=True)

    # Base MOC and base Thing templates (always present — base tier fallback)
    (tmpl_dir / "moc.md").write_text(_BASE_MOC, encoding="utf-8")
    (tmpl_dir / "thing.md").write_text(_BASE_THING, encoding="utf-8")
    # Built-ins also need to exist in load_templates() — copy minimal stubs.
    for nt in ("statement", "person", "source", "code", "community"):
        (tmpl_dir / f"{nt}.md").write_text(
            "${frontmatter}\n# ${label}\n\n${dataview_block}\n",
            encoding="utf-8",
        )

    if write_mr_template:
        (tmpl_dir / "override_mr.md").write_text(_OVERRIDE_MR, encoding="utf-8")
    if write_ct_template:
        (tmpl_dir / "override_ct.md").write_text(_OVERRIDE_CT, encoding="utf-8")
    if write_nt_template:
        (tmpl_dir / "override_nt.md").write_text(_OVERRIDE_NT, encoding="utf-8")

    # Profile registers all three lists; tests pass profile_extras to drop
    # tiers when they want to test fall-through.
    profile_yaml = dedent(
        """
        folder_mapping:
          thing: 01-Things
          statement: 02-Statements
          moc: 06-MOCs
          community: 07-Communities
        naming:
          convention: kebab-case
        taxonomy:
          version: v1.8
          root: .
          folders:
            moc: 06-MOCs
            thing: 01-Things
            statement: 02-Statements
            person: People
            source: Sources
            default: 01-Things
            unclassified: 06-MOCs
        """
    ).lstrip()
    profile_yaml += profile_extras
    (g / "profile.yaml").write_text(profile_yaml, encoding="utf-8")
    return vault


def _moc_ctx_with(community_name: str, **overrides) -> dict:
    base = {
        "note_type": "moc",
        "folder": "06-MOCs/",
        "community_name": community_name,
        "community_tag": "test-tag",
        "members_by_type": {
            "thing": [{"id": "n_a", "label": "A"}],
            "statement": [],
            "person": [],
            "source": [],
        },
        "sub_communities": [],
        "sibling_labels": [],
        "cohesion": 0.5,
    }
    base.update(overrides)
    return base


def _render_moc_via_resolve(vault: Path, community_id: int, community_name: str):
    import networkx as nx
    from graphify.profile import load_profile
    from graphify.templates import _render_moc_like

    profile = load_profile(vault)
    G = nx.Graph()
    G.add_node("n_a", label="A", file_type="code", source_file="x.py")
    communities = {community_id: ["n_a"]}
    return _render_moc_like(
        community_id=community_id,
        G=G,
        communities=communities,
        profile=profile,
        classification_context=_moc_ctx_with(community_name),
        template_key="moc",
        vault_dir=vault,
    )


# ---- Ladder precedence tests ---------------------------------------------

_ALL_THREE_LISTS = dedent(
    """
    mapping_rule_templates:
      - match: rule_id
        pattern: foo
        template: templates/override_mr.md
    community_templates:
      - match: label
        pattern: "transformer*"
        template: templates/override_ct.md
    note_type_templates:
      - match: note_type
        pattern: moc
        template: templates/override_nt.md
    """
)


def test_ladder_mapping_rule_template_wins_over_community_and_note_type(tmp_path):
    """Tier 1 (mapping_rule_templates) beats tiers 2 (community) + 3 (note_type)."""
    vault = _ladder_vault(tmp_path, profile_extras=_ALL_THREE_LISTS)
    # Render with ctx carrying rule_id="foo" — triggers tier 1.
    import networkx as nx
    from graphify.profile import load_profile
    from graphify.templates import _render_moc_like

    profile = load_profile(vault)
    G = nx.Graph()
    G.add_node("n_a", label="A", file_type="code", source_file="x.py")
    communities = {5: ["n_a"]}
    ctx = _moc_ctx_with("transformer-stack", rule_id="foo")
    _, text = _render_moc_like(
        community_id=5,
        G=G,
        communities=communities,
        profile=profile,
        classification_context=ctx,
        template_key="moc",
        vault_dir=vault,
    )
    assert "OVERRIDE_MR_MARKER" in text, text
    assert "OVERRIDE_CT_MARKER" not in text
    assert "OVERRIDE_NT_MARKER" not in text
    assert "BASE_MOC_MARKER" not in text


def test_ladder_community_template_wins_when_no_mapping_rule_match(tmp_path):
    """Tier 2 (community_templates) wins when no rule_id is set in ctx."""
    vault = _ladder_vault(tmp_path, profile_extras=_ALL_THREE_LISTS)
    _, text = _render_moc_via_resolve(vault, community_id=5, community_name="transformer-stack")
    assert "OVERRIDE_CT_MARKER" in text, text
    assert "OVERRIDE_MR_MARKER" not in text
    assert "OVERRIDE_NT_MARKER" not in text
    assert "BASE_MOC_MARKER" not in text


def test_ladder_note_type_template_wins_when_no_mapping_or_community_match(tmp_path):
    """Tier 3 (note_type_templates) wins when no mapping_rule and no community match."""
    vault = _ladder_vault(tmp_path, profile_extras=_ALL_THREE_LISTS)
    # community_name="other" does NOT match transformer* glob → tier 2 misses;
    # no rule_id in ctx → tier 1 misses; tier 3 (note_type=moc) matches.
    _, text = _render_moc_via_resolve(vault, community_id=5, community_name="other")
    assert "OVERRIDE_NT_MARKER" in text, text
    assert "OVERRIDE_MR_MARKER" not in text
    assert "OVERRIDE_CT_MARKER" not in text
    assert "BASE_MOC_MARKER" not in text


def test_ladder_base_default_when_no_overrides_match(tmp_path):
    """Tier 4 (base) falls through when nothing matches."""
    # Empty profile_extras → no override lists registered.
    vault = _ladder_vault(tmp_path, profile_extras="")
    _, text = _render_moc_via_resolve(vault, community_id=5, community_name="other")
    assert "BASE_MOC_MARKER" in text, text
    assert "OVERRIDE_MR_MARKER" not in text
    assert "OVERRIDE_CT_MARKER" not in text
    assert "OVERRIDE_NT_MARKER" not in text


# ---- Warn-fallback tests (D-56.13 / Phase 55 D-55.14) --------------------


def test_mapping_rule_template_missing_file_warns_and_falls_back(tmp_path, capsys):
    """Missing mapping_rule_templates override file → stderr warn + base renders."""
    extras = dedent(
        """
        mapping_rule_templates:
          - match: rule_id
            pattern: foo
            template: templates/override_mr.md
        """
    )
    vault = _ladder_vault(tmp_path, write_mr_template=False, profile_extras=extras)

    import networkx as nx
    from graphify.profile import load_profile
    from graphify.templates import _render_moc_like

    profile = load_profile(vault)
    G = nx.Graph()
    G.add_node("n_a", label="A", file_type="code", source_file="x.py")
    communities = {5: ["n_a"]}
    ctx = _moc_ctx_with("anything", rule_id="foo")
    _, text = _render_moc_like(
        community_id=5,
        G=G,
        communities=communities,
        profile=profile,
        classification_context=ctx,
        template_key="moc",
        vault_dir=vault,
    )

    err = capsys.readouterr().err
    assert "[graphify] mapping_rule_templates override missing" in err, err
    # Falls through all the way to base because no other tier matches.
    assert "BASE_MOC_MARKER" in text


def test_note_type_template_missing_file_warns_and_falls_back(tmp_path, capsys):
    """Missing note_type_templates override file → stderr warn + base renders."""
    extras = dedent(
        """
        note_type_templates:
          - match: note_type
            pattern: moc
            template: templates/override_nt.md
        """
    )
    vault = _ladder_vault(tmp_path, write_nt_template=False, profile_extras=extras)
    _, text = _render_moc_via_resolve(vault, community_id=5, community_name="other")

    err = capsys.readouterr().err
    assert "[graphify] note_type_templates override missing" in err, err
    assert "BASE_MOC_MARKER" in text


def test_community_template_missing_file_still_warns_with_correct_list_name(tmp_path, capsys):
    """Phase 30 regression: missing community_templates override → existing
    `community_templates override missing` warn unchanged after refactor."""
    extras = dedent(
        """
        community_templates:
          - match: label
            pattern: "transformer*"
            template: templates/override_ct.md
        """
    )
    vault = _ladder_vault(tmp_path, write_ct_template=False, profile_extras=extras)
    _, text = _render_moc_via_resolve(vault, community_id=5, community_name="transformer-stack")

    err = capsys.readouterr().err
    assert "[graphify] community_templates override missing" in err, err
    assert "BASE_MOC_MARKER" in text


# ---- Integration: classify() → ctx.rule_id + render_note end-to-end ------


def test_classify_populates_rule_id_when_matched_rule_has_id():
    """classify() copies matched rule's `id:` field into ctx['rule_id']."""
    import networkx as nx
    from graphify.mapping import classify

    G = nx.Graph()
    # File-hub with topology=is_source_file rule (D-51 opt-in pattern keeps
    # mapping logic simple); two nodes — one matches a rule with id, one falls
    # through to topology default and has no rule_id.
    G.add_node("n_thing", label="T", file_type="concept_dummy", source_file="x.py")
    # Make n_thing NOT a concept (avoid skip): use file_type that isn't concept/file.
    G.nodes["n_thing"]["file_type"] = "method"
    G.add_node("n_other", label="O", file_type="method", source_file="y.py")
    communities = {0: ["n_thing", "n_other"]}

    profile = {
        "mapping_rules": [
            {
                "id": "thing_rule",
                "when": {"attr": "label", "equals": "T"},
                "then": {"note_type": "thing"},
            },
        ],
    }
    result = classify(G, communities, profile)
    assert result.per_node["n_thing"].get("rule_id") == "thing_rule"
    # Rule with no id: → no rule_id key in ctx.
    assert "rule_id" not in result.per_node["n_other"]


def test_render_note_with_rule_id_picks_mapping_rule_template(tmp_path, capsys):
    """End-to-end: profile with mapping_rules[0].id=foo + mapping_rule_templates
    pointing at foo → render_note uses override marker."""
    extras = dedent(
        """
        mapping_rule_templates:
          - match: rule_id
            pattern: foo
            template: templates/override_mr.md
        """
    )
    # Build a vault but override_mr.md needs to render a thing (not moc) — the
    # render_note path uses ${connections_callout}, not ${members_section}.
    vault = _ladder_vault(tmp_path, write_mr_template=False, profile_extras=extras)
    # Write an override_mr.md with thing-friendly slots.
    (vault / ".graphify" / "templates" / "override_mr.md").write_text(
        "${frontmatter}\n# MR Override Thing: ${label}\n\nOVERRIDE_MR_MARKER\n\n${connections_callout}\n",
        encoding="utf-8",
    )

    import networkx as nx
    from graphify.profile import load_profile
    from graphify.templates import render_note

    profile = load_profile(vault)
    G = nx.Graph()
    G.add_node("n_a", label="A", file_type="code", source_file="x.py")
    ctx = {
        "note_type": "thing",
        "folder": "01-Things/",
        "community_name": "anything",
        "community_tag": "test-tag",
        "sibling_labels": [],
        "rule_id": "foo",
    }
    _, text = render_note(
        node_id="n_a",
        G=G,
        profile=profile,
        note_type="thing",
        classification_context=ctx,
        vault_dir=vault,
    )
    assert "OVERRIDE_MR_MARKER" in text, text
    assert "BASE_THING_MARKER" not in text
