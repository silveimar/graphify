"""Tests for profile composition (extends/includes, cycle detection, provenance) — Phase 30 / CFG-02."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    load_profile,
    validate_profile,
    validate_profile_preflight,
)

# Phase 30 / CFG-02: these symbols are added by Plan 30-01 Task 2. During the
# RED phase of TDD they are not yet defined; lazy-import so collection still
# succeeds and individual tests fail with a clear AttributeError instead of a
# blanket import error preventing all collection.
def _resolve_profile_chain(*args, **kwargs):  # pragma: no cover (replaced at import)
    from graphify.profile import _resolve_profile_chain as _impl
    return _impl(*args, **kwargs)


def _deep_merge_with_provenance(*args, **kwargs):  # pragma: no cover
    from graphify.profile import _deep_merge_with_provenance as _impl
    return _impl(*args, **kwargs)

FIXTURES = Path(__file__).parent / "fixtures" / "profiles"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_fixture(name: str, tmp_path: Path) -> Path:
    """Copy a fixture vault into tmp_path/vault and return the vault path."""
    dest = tmp_path / "vault"
    shutil.copytree(FIXTURES / name, dest)
    return dest


def _make_chain(tmp_path: Path, depth: int) -> Path:
    """Build an extends-chain of *depth* hops inside tmp_path/vault/.graphify/.

    Returns the entry-point Path (lvl0.yaml). depth=0 is a single file with no
    extends; depth=8 means 8 extends links (9 files total: lvl0..lvl8).
    """
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    for i in range(depth + 1):
        nxt = f"lvl{i+1}.yaml" if i < depth else None
        body = "folder_mapping:\n  thing: 01-Things\n"
        if nxt:
            body = f"extends: {nxt}\n" + body
        (g / f"lvl{i}.yaml").write_text(body, encoding="utf-8")
    return g / "lvl0.yaml"


# ---------------------------------------------------------------------------
# Resolver: extends single-parent chain (CFG-02 SC#1)
# ---------------------------------------------------------------------------


def test_extends_single_parent_merges(tmp_path):
    vault = _copy_fixture("linear_chain", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors == [], f"unexpected errors: {result.errors}"
    fm = result.composed["folder_mapping"]
    # thing was overridden by fusion.yaml (root core overridden)
    assert fm["thing"] == "from-fusion/Things"
    # statement was added by profile.yaml itself (last-wins on top of fusion's
    # inherited core statement)
    assert fm["statement"] == "from-profile/Statements"
    # naming.convention follows fusion (overrode core's kebab-case)
    assert result.composed["naming"]["convention"] == "snake_case"


def test_includes_ordered_last_wins(tmp_path):
    vault = _copy_fixture("includes_only", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors == [], f"unexpected errors: {result.errors}"
    fm = result.composed["folder_mapping"]
    # tags.yaml is last in includes list → wins on `thing`
    assert fm["thing"] == "from-tags/Things"
    assert fm["statement"] == "from-tags/Statements"


def test_extends_then_includes_then_own_fields_order(tmp_path):
    vault = _copy_fixture("extends_and_includes", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors == [], f"unexpected errors: {result.errors}"
    fm = result.composed["folder_mapping"]
    # own fields override the extends-chain
    assert fm["thing"] == "from-profile/Things"
    # statement comes from the extended fusion (no override in includes/own)
    assert fm["statement"] == "from-fusion/Statements"
    # naming was overridden by includes (after extends, before own — but own
    # has no naming key so the include layer wins)
    assert result.composed["naming"]["convention"] == "snake_case"


def test_neither_extends_nor_includes_unchanged_behavior(tmp_path):
    """Back-compat: a profile.yaml with no extends/includes loads identically
    to pre-Phase-30 behavior."""
    vault = _copy_fixture("single_file", tmp_path)
    result = load_profile(vault)
    assert result["folder_mapping"]["thing"] == "01-Things"
    assert result["folder_mapping"]["statement"] == "02-Statements"
    assert result["naming"]["convention"] == "kebab-case"
    # Defaults still merged in
    assert result["folder_mapping"]["moc"] == "Atlas/Maps/"


# ---------------------------------------------------------------------------
# Schema typing of new keys
# ---------------------------------------------------------------------------


def test_extends_must_be_string_not_list(tmp_path):
    """D-03: extends accepts ONLY a single string (single-parent chain)."""
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("extends:\n  - a.yaml\n  - b.yaml\n", encoding="utf-8")
    errors = validate_profile({"extends": ["a.yaml", "b.yaml"]})
    assert any("extends" in e for e in errors)


def test_includes_must_be_list_not_string():
    errors = validate_profile({"includes": "mixin.yaml"})
    assert any("includes" in e and "list" in e for e in errors)


# ---------------------------------------------------------------------------
# Cycle detection (direct + indirect + via includes)
# ---------------------------------------------------------------------------


def test_cycle_self_reference_detected(tmp_path):
    vault = _copy_fixture("cycle_self", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert any("cycle detected" in e for e in result.errors), result.errors
    assert any("→" in e for e in result.errors), result.errors


def test_cycle_indirect_chain_detected(tmp_path):
    """a → b → c → a — entry a.yaml; chain rendered root-first."""
    vault = _copy_fixture("cycle_indirect", tmp_path)
    entry = vault / ".graphify" / "a.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors, "expected cycle error"
    err = next(e for e in result.errors if "cycle detected" in e)
    # Must include all three filenames AND end in the duplicate (a.yaml again)
    assert "a.yaml" in err
    assert "b.yaml" in err
    assert "c.yaml" in err
    assert "→" in err
    # Format: "extends/includes cycle detected: a.yaml → b.yaml → c.yaml → a.yaml"
    assert err.startswith("extends/includes cycle detected: ")
    # Last token after final arrow should be a.yaml (the duplicate)
    assert err.rstrip().endswith("a.yaml")


def test_cycle_via_includes_detected(tmp_path):
    """A cycle introduced via includes: must also be caught."""
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("includes:\n  - mix.yaml\n", encoding="utf-8")
    (g / "mix.yaml").write_text("includes:\n  - profile.yaml\n", encoding="utf-8")
    result = _resolve_profile_chain(g / "profile.yaml", tmp_path / "vault")
    assert any("cycle detected" in e for e in result.errors), result.errors


def test_diamond_inheritance_not_cycle(tmp_path):
    """A extends B; A includes C; C extends B → NOT a cycle (D-04)."""
    vault = _copy_fixture("diamond", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors == [], f"diamond should not be a cycle: {result.errors}"
    assert result.composed["folder_mapping"]["thing"] == "core/Things"
    assert result.composed["naming"]["convention"] == "kebab-case"


# ---------------------------------------------------------------------------
# Depth cap (D-05)
# ---------------------------------------------------------------------------


def test_depth_cap_8_allowed(tmp_path):
    entry = _make_chain(tmp_path, 8)
    result = _resolve_profile_chain(entry, tmp_path / "vault")
    assert result.errors == [], f"depth==8 should succeed: {result.errors}"
    assert result.composed["folder_mapping"]["thing"] == "01-Things"


def test_depth_cap_9_rejected(tmp_path):
    entry = _make_chain(tmp_path, 9)
    result = _resolve_profile_chain(entry, tmp_path / "vault")
    assert any("recursion depth exceeded 8" in e for e in result.errors), result.errors


# ---------------------------------------------------------------------------
# Partial fragments (D-08)
# ---------------------------------------------------------------------------


def test_partial_fragment_validates_when_composed(tmp_path):
    """A fragment without folder_mapping is fine — only the COMPOSED profile
    must validate."""
    vault = _copy_fixture("partial_fragment", tmp_path)
    result = load_profile(vault)
    # Composition succeeded → folder_mapping comes from profile.yaml
    assert result["folder_mapping"]["thing"] == "01-Things"
    assert result["folder_mapping"]["statement"] == "02-Statements"
    assert result["naming"]["convention"] == "kebab-case"


def test_partial_fragment_alone_is_not_validated(tmp_path):
    """The resolver does NOT call validate_profile per-fragment. Loading the
    fragment alone via _resolve_profile_chain returns no errors even though
    the fragment is intentionally incomplete."""
    vault = _copy_fixture("partial_fragment", tmp_path)
    fragment_entry = vault / ".graphify" / "bases" / "partial.yaml"
    result = _resolve_profile_chain(fragment_entry, vault)
    assert result.errors == []


# ---------------------------------------------------------------------------
# Path security (T-30-01) — D-07
# ---------------------------------------------------------------------------


def test_absolute_extends_path_rejected(tmp_path):
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("extends: /tmp/evil.yaml\n", encoding="utf-8")
    result = _resolve_profile_chain(g / "profile.yaml", tmp_path / "vault")
    assert any("escapes .graphify/" in e for e in result.errors), result.errors


def test_extends_traversal_rejected(tmp_path):
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("extends: ../../etc/passwd\n", encoding="utf-8")
    result = _resolve_profile_chain(g / "profile.yaml", tmp_path / "vault")
    assert any("escapes .graphify/" in e for e in result.errors), result.errors


@pytest.mark.skipif(sys.platform == "win32", reason="symlink privilege")
def test_extends_symlink_escape_rejected(tmp_path):
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text("folder_mapping:\n  thing: leaked\n", encoding="utf-8")
    (g / "link.yaml").symlink_to(outside)
    (g / "profile.yaml").write_text("extends: link.yaml\n", encoding="utf-8")
    result = _resolve_profile_chain(g / "profile.yaml", tmp_path / "vault")
    assert any("escapes .graphify/" in e for e in result.errors), result.errors


def test_sibling_relative_path_resolution(tmp_path):
    """D-06: extends paths are resolved relative to the file that declares
    them (sibling-relative), NOT relative to vault root."""
    vault = _copy_fixture("linear_chain", tmp_path)
    # bases/fusion.yaml has `extends: core.yaml` — must resolve as
    # bases/core.yaml (sibling), not <vault>/.graphify/core.yaml.
    entry = vault / ".graphify" / "bases" / "fusion.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors == [], result.errors
    assert result.composed["folder_mapping"]["statement"] == "from-core/Statements"


def test_malformed_yaml_in_fragment(tmp_path):
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("extends: broken.yaml\n", encoding="utf-8")
    (g / "broken.yaml").write_text("folder_mapping: : :\n", encoding="utf-8")
    result = _resolve_profile_chain(g / "profile.yaml", tmp_path / "vault")
    assert any("YAML parse error" in e for e in result.errors), result.errors


# ---------------------------------------------------------------------------
# Graceful fallback through load_profile() (CFG-02 / D-01)
# ---------------------------------------------------------------------------


def test_load_profile_cycle_returns_default(tmp_path, capsys):
    vault = _copy_fixture("cycle_self", tmp_path)
    result = load_profile(vault)
    # Returns the bare _DEFAULT_PROFILE
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
    captured = capsys.readouterr()
    assert "[graphify] profile error:" in captured.err


def test_load_profile_path_escape_returns_default(tmp_path, capsys):
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("extends: /etc/passwd\n", encoding="utf-8")
    result = load_profile(tmp_path / "vault")
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
    captured = capsys.readouterr()
    assert "[graphify] profile error:" in captured.err


def test_load_profile_missing_fragment_returns_default(tmp_path, capsys):
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text("extends: nope.yaml\n", encoding="utf-8")
    result = load_profile(tmp_path / "vault")
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
    captured = capsys.readouterr()
    assert "[graphify] profile error:" in captured.err


# ---------------------------------------------------------------------------
# ResolvedProfile shape + provenance + deep_merge contract
# ---------------------------------------------------------------------------


def test_resolved_profile_namedtuple_shape(tmp_path):
    vault = _copy_fixture("single_file", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    # Must have all five named fields
    assert hasattr(result, "composed")
    assert hasattr(result, "chain")
    assert hasattr(result, "provenance")
    assert hasattr(result, "errors")
    assert hasattr(result, "community_template_rules")
    assert isinstance(result.chain, list)
    assert isinstance(result.provenance, dict)
    assert isinstance(result.errors, list)
    assert isinstance(result.community_template_rules, list)


def test_deep_merge_with_provenance_does_not_mutate_base():
    base = {"a": {"b": 1}}
    snapshot = {"a": {"b": 1}}
    _deep_merge_with_provenance(base, {"a": {"b": 99}}, Path("x.yaml"), {})
    assert base == snapshot, "_deep_merge_with_provenance must not mutate base"


def test_provenance_records_dotted_keys(tmp_path):
    vault = _copy_fixture("linear_chain", tmp_path)
    entry = vault / ".graphify" / "profile.yaml"
    result = _resolve_profile_chain(entry, vault)
    assert result.errors == []
    # thing was last touched by fusion.yaml (profile.yaml does not set it)
    src_thing = result.provenance.get("folder_mapping.thing")
    assert src_thing is not None
    assert str(src_thing).endswith("bases/fusion.yaml")
    # statement was last touched by profile.yaml itself
    src_stmt = result.provenance.get("folder_mapping.statement")
    assert src_stmt is not None
    assert str(src_stmt).endswith("profile.yaml")


def test_provenance_list_typed_leaves_record_at_list_level(tmp_path):
    """R7: list-typed values are recorded under the list key itself, not with
    a [index] suffix."""
    g = tmp_path / "vault" / ".graphify"
    g.mkdir(parents=True)
    (g / "profile.yaml").write_text(
        "mapping_rules:\n"
        "  - if:\n"
        "      file_type: code\n"
        "    then:\n"
        "      folder: Code/\n",
        encoding="utf-8",
    )
    result = _resolve_profile_chain(g / "profile.yaml", tmp_path / "vault")
    assert result.errors == []
    assert "mapping_rules" in result.provenance
    # No indexed sub-keys allowed
    assert not any(k.startswith("mapping_rules[") for k in result.provenance)


# ---------------------------------------------------------------------------
# Plan 30-02 / CFG-03: community_templates runtime dispatch tests
# ---------------------------------------------------------------------------


def _ct_vault(tmp_path: Path) -> Path:
    """Copy the community_templates fixture vault into tmp_path/vault."""
    return _copy_fixture("community_templates", tmp_path)


def _moc_ctx(community_name: str) -> dict:
    """Minimal classification_context for MOC rendering."""
    return {
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


def _render_moc_with_profile(vault: Path, profile_overrides: dict, community_id: int, community_name: str):
    """Helper: load profile from vault and call _render_moc_like with overrides applied.

    profile_overrides is merged into the loaded profile dict shallow-style; we
    use this for the case-sensitivity and first-match-wins tests where we want
    custom rules without touching the shared fixture.
    """
    import networkx as nx
    from graphify.profile import load_profile
    from graphify.templates import _render_moc_like

    profile = load_profile(vault)
    profile = dict(profile)
    profile.update(profile_overrides)
    G = nx.Graph()
    G.add_node("n_a", label="A", file_type="code", source_file="x.py")
    communities = {community_id: ["n_a"]}
    return _render_moc_like(
        community_id=community_id,
        G=G,
        communities=communities,
        profile=profile,
        classification_context=_moc_ctx(community_name),
        template_key="moc",
        vault_dir=vault,
    )


def test_community_templates_label_glob_match(tmp_path):
    """`transformer*` rule matches 'transformer-stack' → renders override."""
    vault = _ct_vault(tmp_path)
    _, text = _render_moc_with_profile(vault, {}, community_id=5, community_name="transformer-stack")
    assert "OVERRIDE_TEMPLATE_MARKER" in text
    assert "BIG_OVERRIDE_MARKER" not in text


def test_community_templates_id_exact_match(tmp_path):
    """match=id pattern=0 matches community_id=0 → renders big-community override."""
    vault = _ct_vault(tmp_path)
    # Use a name that does NOT match transformer* so the id rule wins
    _, text = _render_moc_with_profile(vault, {}, community_id=0, community_name="auth-flow")
    assert "BIG_OVERRIDE_MARKER" in text
    assert "OVERRIDE_TEMPLATE_MARKER" not in text


def test_community_templates_first_match_wins(tmp_path):
    """When two rules both match, the first listed wins (D-13)."""
    vault = _ct_vault(tmp_path)
    overrides = {
        "community_templates": [
            {"match": "label", "pattern": "transformer*", "template": "templates/transformer-moc.md"},
            {"match": "label", "pattern": "*", "template": "templates/big-community-moc.md"},
        ]
    }
    _, text = _render_moc_with_profile(vault, overrides, community_id=7, community_name="transformer-stack")
    assert "OVERRIDE_TEMPLATE_MARKER" in text
    assert "BIG_OVERRIDE_MARKER" not in text


def test_community_templates_no_match_falls_back_to_default(tmp_path):
    """No rule matches → default MOC template used (no override marker)."""
    vault = _ct_vault(tmp_path)
    _, text = _render_moc_with_profile(vault, {}, community_id=42, community_name="unrelated-thing")
    assert "OVERRIDE_TEMPLATE_MARKER" not in text
    assert "BIG_OVERRIDE_MARKER" not in text
    # Default MOC has frontmatter delimiters
    assert text.startswith("---\n")


def test_community_templates_fnmatch_case_sensitive(tmp_path):
    """`Transformer*` does NOT match `transformer-stack` (case-sensitive)."""
    vault = _ct_vault(tmp_path)
    overrides = {
        "community_templates": [
            {"match": "label", "pattern": "Transformer*", "template": "templates/transformer-moc.md"},
        ]
    }
    _, text = _render_moc_with_profile(vault, overrides, community_id=3, community_name="transformer-stack")
    assert "OVERRIDE_TEMPLATE_MARKER" not in text


def test_community_templates_question_mark_glob(tmp_path):
    """`auth-?` matches `auth-1`, NOT `auth-12`."""
    vault = _ct_vault(tmp_path)
    overrides = {
        "community_templates": [
            {"match": "label", "pattern": "auth-?", "template": "templates/transformer-moc.md"},
        ]
    }
    _, text1 = _render_moc_with_profile(vault, overrides, community_id=11, community_name="auth-1")
    assert "OVERRIDE_TEMPLATE_MARKER" in text1
    _, text2 = _render_moc_with_profile(vault, overrides, community_id=12, community_name="auth-12")
    assert "OVERRIDE_TEMPLATE_MARKER" not in text2


def test_community_templates_id_pattern_bool_rejected():
    """validate_profile rejects bool pattern under match='id'."""
    profile = {
        "community_templates": [
            {"match": "id", "pattern": True, "template": "templates/x.md"}
        ]
    }
    errors = validate_profile(profile)
    assert any("pattern must be an integer" in e for e in errors)


def test_community_templates_label_pattern_int_rejected():
    """validate_profile rejects int pattern under match='label'."""
    profile = {
        "community_templates": [
            {"match": "label", "pattern": 7, "template": "templates/x.md"}
        ]
    }
    errors = validate_profile(profile)
    assert any("pattern must be a string" in e for e in errors)


def test_community_templates_unknown_keys_rejected():
    """Extra keys in a rule → validate_profile error."""
    profile = {
        "community_templates": [
            {"match": "label", "pattern": "x*", "template": "templates/x.md", "extra": 1}
        ]
    }
    errors = validate_profile(profile)
    assert any("unknown keys" in e for e in errors)


def test_override_template_path_escape_falls_back(tmp_path, capsys):
    """A template path with `..` segments falls back to default + emits stderr."""
    vault = _ct_vault(tmp_path)
    # Bypass validate_profile (which would catch the `..`) by injecting at runtime
    overrides = {
        "community_templates": [
            {"match": "label", "pattern": "transformer*", "template": "../escape.md"},
        ]
    }
    _, text = _render_moc_with_profile(vault, overrides, community_id=1, community_name="transformer-stack")
    assert "OVERRIDE_TEMPLATE_MARKER" not in text
    captured = capsys.readouterr()
    assert "[graphify] community_templates override" in captured.err


def test_override_template_missing_file_falls_back(tmp_path, capsys):
    """Referenced override file does not exist → default used + stderr warning."""
    vault = _ct_vault(tmp_path)
    overrides = {
        "community_templates": [
            {"match": "label", "pattern": "transformer*", "template": "templates/missing-moc.md"},
        ]
    }
    _, text = _render_moc_with_profile(vault, overrides, community_id=1, community_name="transformer-stack")
    assert "OVERRIDE_TEMPLATE_MARKER" not in text
    captured = capsys.readouterr()
    assert "[graphify] community_templates override" in captured.err
    assert "missing" in captured.err.lower()


def test_override_template_invalid_placeholder_falls_back(tmp_path, capsys):
    """Override template missing required placeholder ${label} → falls back."""
    vault = _ct_vault(tmp_path)
    overrides = {
        "community_templates": [
            {"match": "label", "pattern": "transformer*", "template": "templates/invalid-moc.md"},
        ]
    }
    _, text = _render_moc_with_profile(vault, overrides, community_id=1, community_name="transformer-stack")
    assert "OVERRIDE_TEMPLATE_MARKER" not in text
    captured = capsys.readouterr()
    assert "[graphify] community_templates override" in captured.err
    assert "missing required placeholder" in captured.err
    assert "${label}" in captured.err


def test_override_scope_moc_only(tmp_path):
    """Member nodes (rendered via render_note) use type-based templates,
    regardless of community_templates rules (D-12 — MOC-only scope)."""
    import networkx as nx
    from graphify.profile import load_profile
    from graphify.templates import render_note

    vault = _ct_vault(tmp_path)
    profile = load_profile(vault)
    G = nx.Graph()
    G.add_node(
        "n_transformer",
        label="Transformer",
        file_type="code",
        source_file="src/model.py",
        source_location="L42",
    )
    ctx = {
        "note_type": "thing",
        "folder": "01-Things/",
        "parent_moc_label": "transformer-stack",
        "community_name": "transformer-stack",
        "community_tag": "transformer-stack",
        "members_by_type": {},
        "sub_communities": [],
        "sibling_labels": [],
    }
    fname, text = render_note(
        "n_transformer", G, profile, "thing", ctx, vault_dir=vault
    )
    # The override marker must NEVER appear on a non-MOC node, even when the
    # node belongs to a community that matches a community_templates rule.
    assert "OVERRIDE_TEMPLATE_MARKER" not in text
    assert "BIG_OVERRIDE_MARKER" not in text
    # Standard thing render: frontmatter present + label heading
    assert text.startswith("---\n")
    assert "type: thing" in text


# ----------------------------------------------------------------------------
# Phase 30 / Plan 03: --validate-profile output extension tests (RED)
# ----------------------------------------------------------------------------
import subprocess


def _run_validate(vault_path: Path) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify --validate-profile <vault_path>` as a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "graphify", "--validate-profile", str(vault_path)],
        capture_output=True,
        text=True,
    )


def test_validate_profile_prints_merge_chain(tmp_path):
    """Output to stdout contains 'Merge chain (root ancestor first):' followed
    by chain files in resolution order: core.yaml -> fusion.yaml -> profile.yaml."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "linear_chain", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 0, proc.stderr
    assert "Merge chain (root ancestor first):" in proc.stdout
    chain_section = proc.stdout.split("Merge chain")[1]
    assert (
        chain_section.index("core.yaml")
        < chain_section.index("fusion.yaml")
        < chain_section.index("profile.yaml")
    )


def test_validate_profile_prints_field_provenance(tmp_path):
    """Output contains 'Field provenance (' header and dotted-key ← source-file lines."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "linear_chain", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 0, proc.stderr
    assert "Field provenance (" in proc.stdout
    assert "leaf fields):" in proc.stdout
    assert "←" in proc.stdout  # ← arrow
    assert "folder_mapping.thing" in proc.stdout


def test_validate_profile_prints_resolved_community_templates(tmp_path):
    """For community_templates fixture: prints 2-rule section with as-written rules."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "community_templates", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 0, proc.stderr
    assert "Resolved community templates (2 rules):" in proc.stdout
    assert "match=label" in proc.stdout
    assert 'pattern="transformer*"' in proc.stdout
    assert "template=templates/transformer-moc.md" in proc.stdout
    assert "match=id" in proc.stdout
    assert "pattern=0" in proc.stdout
    # Graph-blind disclaimer (D-17):
    assert "actual community-to-template assignments require a graph" in proc.stdout


def test_validate_profile_single_file_shows_no_rules(tmp_path):
    """Single-file profile (no extends/includes) shows one-element chain and
    'Resolved community templates: (none)'."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "single_file", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 0, proc.stderr
    assert "Resolved community templates: (none)" in proc.stdout
    chain_section = proc.stdout.split("Merge chain")[1].split("Field provenance")[0]
    # Exactly one filename in chain section: profile.yaml
    assert chain_section.count("profile.yaml") == 1
    assert "core.yaml" not in chain_section


def test_validate_profile_exits_zero_on_valid_composed(tmp_path):
    """Valid composed profile exits 0 even when the new sections print."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "linear_chain", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 0, proc.stderr


def test_validate_profile_exits_nonzero_on_cycle(tmp_path):
    """Cycle in fragments → exit code 1 + cycle error on stderr."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "cycle_via_profile_yaml", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 1
    assert "error:" in proc.stderr
    assert "cycle detected" in proc.stderr


def test_validate_profile_exits_nonzero_on_path_escape(tmp_path):
    """Path-escape in fragments → exit code 1 + escape error on stderr."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "path_escape", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 1
    assert "error:" in proc.stderr
    assert "escapes .graphify/" in proc.stderr


def test_validate_profile_lost_fields_after_extends_removal(tmp_path):
    """D-15 / SC#4: removing an extends: reference makes parent-sourced fields
    disappear from the provenance section, AND the post-removal run still exits 0."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "lost_fields_demo", vault)
    profile_yaml = vault / ".graphify" / "profile.yaml"

    proc_before = _run_validate(vault)
    assert proc_before.returncode == 0, proc_before.stderr
    provenance_before = proc_before.stdout.split("Field provenance")[1].split(
        "Resolved community templates"
    )[0]
    # Sanity: provenance includes naming.convention sourced from the parent.
    assert "naming.convention" in provenance_before
    assert "parent.yaml" in provenance_before

    # Rewrite profile.yaml WITHOUT the extends line — schema-self-sufficient:
    profile_yaml.write_text(
        "folder_mapping:\n"
        "  thing: from-child/Things\n"
        "  statement: from-child/Statements\n"
    )

    proc_after = _run_validate(vault)
    assert proc_after.returncode == 0, (
        f"after extends removal, validate-profile must still exit 0; "
        f"stderr={proc_after.stderr!r}"
    )
    provenance_after = proc_after.stdout.split("Field provenance")[1].split(
        "Resolved community templates"
    )[0]
    # parent-sourced fields are gone:
    assert "parent.yaml" not in provenance_after
    assert "naming.convention" not in provenance_after
    # Remaining keys are now sourced from profile.yaml only:
    assert "folder_mapping.thing" in provenance_after
    assert "← profile.yaml" in provenance_after


def test_validate_profile_graph_blind_note(tmp_path):
    """Output contains literal disclaimer about graph-blind community-template assignments."""
    vault = tmp_path / "vault"
    shutil.copytree(FIXTURES / "community_templates", vault)
    proc = _run_validate(vault)
    assert proc.returncode == 0, proc.stderr
    assert "actual community-to-template assignments require a graph" in proc.stdout
