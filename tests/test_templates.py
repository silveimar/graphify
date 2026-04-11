"""Unit tests for graphify/templates.py — template engine helpers."""
from __future__ import annotations

import inspect
import string
import typing
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Task 1: KNOWN_VARS and ClassificationContext tests
# ---------------------------------------------------------------------------


def test_known_vars_frozen():
    from graphify.templates import KNOWN_VARS

    assert isinstance(KNOWN_VARS, frozenset)
    assert KNOWN_VARS == {
        "label",
        "frontmatter",
        "wayfinder_callout",
        "connections_callout",
        "members_section",
        "sub_communities_callout",
        "dataview_block",
        "metadata_callout",
        "body",
    }


def test_classification_context_is_typeddict():
    from graphify.templates import ClassificationContext

    assert ClassificationContext.__total__ is False


def test_classification_context_declares_community_name():
    from graphify.templates import ClassificationContext

    assert "community_name" in typing.get_type_hints(ClassificationContext)


# ---------------------------------------------------------------------------
# Task 1: resolve_filename tests
# ---------------------------------------------------------------------------


def test_resolve_filename_title_case_basic():
    from graphify.templates import resolve_filename

    assert resolve_filename("neural network theory", "title_case") == "Neural_Network_Theory"


def test_resolve_filename_title_case_existing_underscores():
    from graphify.templates import resolve_filename

    assert resolve_filename("Neural_Network_Theory", "title_case") == "Neural_Network_Theory"


def test_resolve_filename_title_case_unicode_nfc():
    from graphify.templates import resolve_filename

    assert resolve_filename("Teoría de Redes", "title_case") == "Teoría_De_Redes"


def test_resolve_filename_title_case_with_colon():
    from graphify.templates import resolve_filename

    # Colon stripped by safe_filename; hyphen stays intra-word
    assert resolve_filename("Deep-Learning: Methods", "title_case") == "Deep-learning_Methods"


def test_resolve_filename_title_case_with_hyphen_digit():
    from graphify.templates import resolve_filename

    assert resolve_filename("GPT-4 Turbo", "title_case") == "Gpt-4_Turbo"


def test_resolve_filename_kebab_basic():
    from graphify.templates import resolve_filename

    assert resolve_filename("Neural Network Theory", "kebab-case") == "neural-network-theory"


def test_resolve_filename_kebab_existing_underscores():
    from graphify.templates import resolve_filename

    # GEN-07: underscore labels round-trip cleanly via same regex r"[ \t_]+"
    assert resolve_filename("Neural_Network_Theory", "kebab-case") == "neural-network-theory"


def test_resolve_filename_kebab_unicode():
    from graphify.templates import resolve_filename

    assert resolve_filename("Teoría de Redes", "kebab-case") == "teoría-de-redes"


def test_resolve_filename_preserve_delegates_to_safe_filename():
    from graphify.templates import resolve_filename

    assert resolve_filename("my/weird\\name", "preserve") == "myweirdname"


def test_resolve_filename_empty_label_after_sanitization():
    from graphify.templates import resolve_filename

    assert resolve_filename("???", "preserve") == "unnamed"


def test_resolve_filename_stable_across_calls():
    from graphify.templates import resolve_filename

    label = "Transformer Architecture"
    results = [resolve_filename(label, "title_case") for _ in range(3)]
    assert results[0] == results[1] == results[2]


def test_resolve_filename_length_capped():
    from graphify.templates import resolve_filename

    label = "A" * 300
    result = resolve_filename(label, "preserve")
    assert len(result) <= 200


# ---------------------------------------------------------------------------
# Task 1: template_context fixture tests (ensures fixture module is usable)
# ---------------------------------------------------------------------------


def test_make_classification_context_defaults():
    from tests.fixtures.template_context import make_classification_context

    ctx = make_classification_context()
    assert ctx["note_type"] == "thing"
    assert ctx["folder"] == "Atlas/Dots/Things/"
    assert ctx["parent_moc_label"] == "ML Architecture"
    assert ctx["community_tag"] == "ml-architecture"
    assert ctx["members_by_type"] == {}
    assert ctx["sub_communities"] == []
    assert ctx["sibling_labels"] == []


def test_make_classification_context_overrides():
    from tests.fixtures.template_context import make_classification_context

    ctx = make_classification_context(note_type="moc", folder="Atlas/Maps/")
    assert ctx["note_type"] == "moc"
    assert ctx["folder"] == "Atlas/Maps/"
    assert ctx["parent_moc_label"] == "ML Architecture"  # default preserved


def test_make_min_graph_structure():
    from tests.fixtures.template_context import make_min_graph

    G = make_min_graph()
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2
    assert "n_transformer" in G
    assert G.nodes["n_transformer"]["label"] == "Transformer"
    assert G.nodes["n_paper"]["file_type"] == "paper"
    assert G["n_transformer"]["n_attention"]["confidence"] == "EXTRACTED"
    assert G["n_transformer"]["n_paper"]["confidence_score"] == 0.85


# ---------------------------------------------------------------------------
# Task 2: validate_template tests
# ---------------------------------------------------------------------------


def test_validate_template_accepts_all_known_vars():
    from graphify.templates import validate_template

    text = "${frontmatter}\n# ${label}\n${wayfinder_callout}\n${connections_callout}\n${metadata_callout}"
    errors = validate_template(text, required={"frontmatter", "label"})
    assert errors == []


def test_validate_template_rejects_unknown_var():
    from graphify.templates import validate_template

    errors = validate_template("${frontmatter}\n${unknown_thing}", required=set())
    assert len(errors) > 0
    assert any("unknown_thing" in e for e in errors)


def test_validate_template_reports_missing_required():
    from graphify.templates import validate_template

    errors = validate_template("# ${label}", required={"frontmatter"})
    assert len(errors) > 0
    assert any("frontmatter" in e for e in errors)


def test_validate_template_ignores_dollar_escape():
    from graphify.templates import validate_template

    errors = validate_template("This costs $$5 today", required=set())
    assert errors == []


def test_validate_template_ignores_templater_tokens():
    from graphify.templates import validate_template

    text = "${frontmatter}\n<% tp.date.now() %>\n<% tp.file.title %>\n# ${label}"
    errors = validate_template(text, required={"frontmatter", "label"})
    assert errors == []


def test_validate_template_multiple_unknowns_sorted():
    from graphify.templates import validate_template

    errors = validate_template("${zeta}${alpha}${beta}", required=set())
    # Extract unknown var names from error messages (they appear in order)
    unknown_mentions = [e for e in errors if "unknown" in e or any(v in e for v in ["alpha", "beta", "zeta"])]
    # Check alphabetical order: alpha before beta before zeta
    assert len(unknown_mentions) == 3
    assert "alpha" in unknown_mentions[0]
    assert "beta" in unknown_mentions[1]
    assert "zeta" in unknown_mentions[2]


# ---------------------------------------------------------------------------
# Task 2: load_templates tests
# ---------------------------------------------------------------------------


def test_load_templates_returns_all_builtins_when_no_vault_override(tmp_path):
    from graphify.templates import load_templates

    result = load_templates(tmp_path)
    assert set(result.keys()) == {"moc", "community", "thing", "statement", "person", "source"}
    assert all(isinstance(v, string.Template) for v in result.values())


def test_load_templates_user_override_replaces_builtin(tmp_path):
    from graphify.templates import load_templates

    override_dir = tmp_path / ".graphify" / "templates"
    override_dir.mkdir(parents=True)
    (override_dir / "thing.md").write_text(
        "${frontmatter}\n# Custom Thing: ${label}\n${connections_callout}\n${metadata_callout}",
        encoding="utf-8",
    )
    result = load_templates(tmp_path)
    assert "Custom Thing:" in result["thing"].template


def test_load_templates_invalid_user_template_falls_back_and_warns(tmp_path, capsys):
    from graphify.templates import load_templates

    override_dir = tmp_path / ".graphify" / "templates"
    override_dir.mkdir(parents=True)
    (override_dir / "thing.md").write_text(
        "${frontmatter}\n${not_a_real_var}",
        encoding="utf-8",
    )
    result = load_templates(tmp_path)
    # Falls back to built-in (does not contain the invalid var)
    assert "not_a_real_var" not in result["thing"].template
    # Warns to stderr
    captured = capsys.readouterr()
    assert "[graphify] template error:" in captured.err
    assert "thing" in captured.err


def test_load_templates_path_confinement(tmp_path):
    from graphify.templates import load_templates

    # Structural assertion: load_templates uses validate_vault_path
    source = inspect.getsource(load_templates)
    assert "validate_vault_path" in source


def test_load_templates_partial_override(tmp_path):
    from graphify.templates import load_templates

    override_dir = tmp_path / ".graphify" / "templates"
    override_dir.mkdir(parents=True)
    # Only override moc with a valid template
    (override_dir / "moc.md").write_text(
        "${frontmatter}\n# ${label}\n${members_section}\n${dataview_block}",
        encoding="utf-8",
    )
    result = load_templates(tmp_path)
    # moc is user override, rest are built-ins
    assert set(result.keys()) == {"moc", "community", "thing", "statement", "person", "source"}
    assert isinstance(result["thing"], string.Template)
    assert isinstance(result["moc"], string.Template)


# ---------------------------------------------------------------------------
# Task 3: lazy import tests
# ---------------------------------------------------------------------------


def test_lazy_imports_resolve_filename():
    import graphify

    assert callable(graphify.resolve_filename)
    assert graphify.resolve_filename("hello world", "title_case") == "Hello_World"


def test_lazy_imports_validate_template():
    import graphify

    assert callable(graphify.validate_template)
    assert graphify.validate_template("${frontmatter}", set()) == []


def test_lazy_imports_load_templates():
    import graphify

    assert callable(graphify.load_templates)
