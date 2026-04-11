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


# ---------------------------------------------------------------------------
# Plan 03 Task 1: _emit_wikilink tests
# ---------------------------------------------------------------------------


def test_emit_wikilink_auto_aliases():
    from graphify.templates import _emit_wikilink

    assert _emit_wikilink("Neural Network Theory", "title_case") == "[[Neural_Network_Theory|Neural Network Theory]]"


def test_emit_wikilink_kebab():
    from graphify.templates import _emit_wikilink

    assert _emit_wikilink("Neural Network Theory", "kebab-case") == "[[neural-network-theory|Neural Network Theory]]"


def test_emit_wikilink_unicode_preserved_in_alias():
    from graphify.templates import _emit_wikilink

    assert _emit_wikilink("Teoría de Redes", "title_case") == "[[Teoría_De_Redes|Teoría de Redes]]"


# ---------------------------------------------------------------------------
# CR-01 regression: _sanitize_wikilink_alias / _emit_wikilink escaping
# ---------------------------------------------------------------------------


def test_sanitize_wikilink_alias_escapes_closing_brackets():
    from graphify.templates import _sanitize_wikilink_alias

    # ]] must not appear in alias — it would close the wikilink early
    assert "]]" not in _sanitize_wikilink_alias("Array[int]]")


def test_sanitize_wikilink_alias_escapes_pipe():
    from graphify.templates import _sanitize_wikilink_alias

    # | in alias creates a malformed second alias segment
    result = _sanitize_wikilink_alias("Label|Injection")
    assert "|" not in result


def test_sanitize_wikilink_alias_escapes_newlines():
    from graphify.templates import _sanitize_wikilink_alias

    result = _sanitize_wikilink_alias("Line1\nLine2\rLine3")
    assert "\n" not in result
    assert "\r" not in result


def test_emit_wikilink_label_with_closing_brackets():
    from graphify.templates import _emit_wikilink, _sanitize_wikilink_alias

    # "Array[int]]" raw alias would contain "]]" which closes the wikilink early.
    # After sanitization "]]" is replaced with "] ]" so no premature close.
    alias = _sanitize_wikilink_alias("Array[int]]")
    assert "]]" not in alias


def test_emit_wikilink_label_with_pipe():
    from graphify.templates import _emit_wikilink

    result = _emit_wikilink("A|B", "title_case")
    # Only one | separator (between fname and alias) — no extra | in alias
    assert result.count("|") == 1


def test_emit_wikilink_label_with_newline():
    from graphify.templates import _emit_wikilink, _sanitize_wikilink_alias

    # resolve_filename may preserve \n in the filename stem (safe_filename handles it),
    # but the alias must not contain newlines so the containing callout line stays intact.
    alias = _sanitize_wikilink_alias("Label\nWith\rNewlines")
    assert "\n" not in alias
    assert "\r" not in alias


# ---------------------------------------------------------------------------
# Plan 03 Task 1: _build_frontmatter_fields tests
# ---------------------------------------------------------------------------


def test_build_frontmatter_fields_non_moc_order():
    import datetime
    from graphify.templates import _build_frontmatter_fields

    result = _build_frontmatter_fields(
        up=["[[ML_Architecture|ML Architecture]]"],
        related=[],
        collections=[],
        tags=["community/ml-architecture", "graphify/code"],
        note_type="thing",
        file_type="code",
        source_file="src/model.py",
        source_location="L42",
        community="ML Architecture",
        created=datetime.date(2026, 4, 11),
    )
    keys = list(result.keys())
    # D-24 field order
    expected_order = ["up", "created", "tags", "type", "file_type", "source_file", "source_location", "community"]
    # Check order: each expected key appears in correct relative order
    key_positions = {k: keys.index(k) for k in expected_order if k in keys}
    ordered_keys = [k for k in expected_order if k in key_positions]
    positions = [key_positions[k] for k in ordered_keys]
    assert positions == sorted(positions), f"Keys not in expected order: {keys}"


def test_build_frontmatter_fields_empty_lists_still_emit():
    import datetime
    from graphify.templates import _build_frontmatter_fields

    result = _build_frontmatter_fields(
        up=["[[Atlas|Atlas]]"],
        related=[],
        collections=[],
        tags=["graphify/code"],
        note_type="thing",
        file_type="code",
        source_file="src/model.py",
        source_location=None,
        community=None,
        created=datetime.date(2026, 4, 11),
    )
    # LOCKED POLICY: empty lists are SKIPPED
    assert "related" not in result
    assert "collections" not in result


def test_build_frontmatter_fields_up_is_always_list():
    import datetime
    from graphify.templates import _build_frontmatter_fields

    result = _build_frontmatter_fields(
        up=["[[ML_Architecture|ML Architecture]]"],
        related=[],
        collections=[],
        tags=["community/ml-architecture"],
        note_type="thing",
        file_type="code",
        source_file="src/model.py",
        source_location=None,
        community=None,
        created=datetime.date(2026, 4, 11),
    )
    assert isinstance(result["up"], list)
    assert len(result["up"]) == 1


def test_build_frontmatter_fields_cohesion_only_for_moc():
    import datetime
    from graphify.templates import _build_frontmatter_fields

    result = _build_frontmatter_fields(
        up=[],
        related=[],
        collections=[],
        tags=["graphify/code"],
        note_type="thing",
        file_type="code",
        source_file="src/model.py",
        source_location=None,
        community=None,
        created=datetime.date(2026, 4, 11),
        cohesion=0.75,
    )
    assert "cohesion" not in result


# ---------------------------------------------------------------------------
# Plan 03 Task 1: _build_wayfinder_callout tests
# ---------------------------------------------------------------------------


def test_build_wayfinder_callout_thing_links_to_parent_moc_and_atlas():
    from graphify.templates import _build_wayfinder_callout, resolve_filename

    profile = {"obsidian": {"atlas_root": "Atlas"}}
    parent_label = "ML Architecture"
    result = _build_wayfinder_callout(
        note_type="thing",
        parent_moc_label=parent_label,
        profile=profile,
        convention="title_case",
    )
    # Use resolve_filename to derive expected filename (locked behavior: .capitalize())
    parent_fname = resolve_filename(parent_label, "title_case")
    expected = (
        "> [!note] Wayfinder\n"
        f"> Up: [[{parent_fname}|{parent_label}]]\n"
        "> Map: [[Atlas|Atlas]]"
    )
    assert result == expected


def test_build_wayfinder_callout_custom_atlas_root():
    from graphify.templates import _build_wayfinder_callout

    profile = {"obsidian": {"atlas_root": "Vault"}}
    result = _build_wayfinder_callout(
        note_type="thing",
        parent_moc_label="ML Architecture",
        profile=profile,
        convention="title_case",
    )
    assert "> Map: [[Vault|Vault]]" in result


def test_build_wayfinder_callout_moc_up_is_atlas():
    from graphify.templates import _build_wayfinder_callout

    profile = {"obsidian": {"atlas_root": "Atlas"}}
    result = _build_wayfinder_callout(
        note_type="moc",
        parent_moc_label="Some Parent",
        profile=profile,
        convention="title_case",
    )
    # For MOC type, both Up and Map point to Atlas (D-35)
    assert "> Up: [[Atlas|Atlas]]" in result
    assert "> Map: [[Atlas|Atlas]]" in result


# ---------------------------------------------------------------------------
# Plan 03 Task 1: _build_connections_callout tests
# ---------------------------------------------------------------------------


def test_build_connections_callout_lists_outgoing_edges():
    from tests.fixtures.template_context import make_min_graph
    from graphify.templates import _build_connections_callout

    G = make_min_graph()
    result = _build_connections_callout(G, "n_transformer", "title_case")
    assert result.startswith("> [!info] Connections")
    assert "> - [[Attention_Mechanism|Attention Mechanism]] — contains [EXTRACTED]" in result
    assert "> - [[Attention_Is_All_You_Need|Attention Is All You Need]] — references [INFERRED]" in result


def test_build_connections_callout_empty_when_no_edges():
    from tests.fixtures.template_context import make_min_graph
    from graphify.templates import _build_connections_callout

    G = make_min_graph()
    G.add_node("n_isolated", label="Isolated Node", file_type="code", source_file="src/x.py")
    result = _build_connections_callout(G, "n_isolated", "title_case")
    assert result == ""


def test_build_connections_callout_confidence_uppercase():
    from tests.fixtures.template_context import make_min_graph
    from graphify.templates import _build_connections_callout

    G = make_min_graph()
    result = _build_connections_callout(G, "n_transformer", "title_case")
    assert "[EXTRACTED]" in result
    assert "[INFERRED]" in result


# ---------------------------------------------------------------------------
# Plan 03 Task 1: _build_metadata_callout tests
# ---------------------------------------------------------------------------


def test_build_metadata_callout_fields_present():
    from graphify.templates import _build_metadata_callout

    result = _build_metadata_callout(
        source_file="src/model.py",
        source_location="L42",
        community="ML Architecture",
    )
    assert "> [!abstract] Metadata" in result
    assert "> source_file: src/model.py" in result
    assert "> source_location: L42" in result
    assert "> community: ML Architecture" in result


def test_build_metadata_callout_skips_missing_source_location():
    from graphify.templates import _build_metadata_callout

    result = _build_metadata_callout(
        source_file="src/model.py",
        source_location=None,
        community="ML Architecture",
    )
    assert "source_location" not in result
    assert "> source_file: src/model.py" in result


# ---------------------------------------------------------------------------
# Plan 03 Task 2: render_note tests
# ---------------------------------------------------------------------------


def test_render_note_returns_tuple_filename_and_text():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    fname, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert isinstance(fname, str)
    assert fname.endswith(".md")
    assert isinstance(text, str)
    assert len(text) > 0


def test_render_note_filename_uses_convention():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile_title = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    fname, _ = render_note("n_transformer", G, profile_title, "thing", ctx)
    assert fname == "Transformer.md"

    profile_kebab = {"naming": {"convention": "kebab-case"}, "obsidian": {"atlas_root": "Atlas"}}
    fname2, _ = render_note("n_transformer", G, profile_kebab, "thing", ctx)
    assert fname2 == "transformer.md"


def test_render_note_thing_has_frontmatter_delimiters():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert text.startswith("---\n")
    # Second --- exists (frontmatter end delimiter)
    lines = text.split("\n")
    dashes = [i for i, l in enumerate(lines) if l.strip() == "---"]
    assert len(dashes) >= 2


def test_render_note_frontmatter_field_order():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    # Extract frontmatter block
    lines = text.split("\n")
    fm_start = 0  # first ---
    fm_end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    fm_lines = lines[fm_start + 1:fm_end]
    fm_keys = [l.split(":")[0].strip() for l in fm_lines if ":" in l and not l.startswith("  ")]
    # D-24 order check: up before created before tags before type
    for earlier, later in [("up", "created"), ("created", "tags"), ("tags", "type")]:
        if earlier in fm_keys and later in fm_keys:
            assert fm_keys.index(earlier) < fm_keys.index(later), (
                f"Expected '{earlier}' before '{later}' but got order: {fm_keys}"
            )


def test_render_note_frontmatter_up_is_list_with_parent_moc():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note, resolve_filename

    G = make_min_graph()
    parent_label = "ML Architecture"
    ctx = make_classification_context(parent_moc_label=parent_label)
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    parent_fname = resolve_filename(parent_label, "title_case")
    wikilink = f"[[{parent_fname}|{parent_label}]]"
    assert "up:" in text
    # wikilink may be quoted by safe_frontmatter_value (contains [)
    assert wikilink in text or f'"{wikilink}"' in text


def test_render_note_frontmatter_tags_include_community_tag():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context(community_tag="ml-architecture")
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert "community/ml-architecture" in text


def test_render_note_frontmatter_created_is_today_iso():
    import datetime
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    today = datetime.date.today().isoformat()
    assert today in text


def test_render_note_contains_heading():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert "# Transformer" in text


def test_render_note_contains_wayfinder_callout():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note, resolve_filename

    G = make_min_graph()
    parent_label = "ML Architecture"
    ctx = make_classification_context(parent_moc_label=parent_label)
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    parent_fname = resolve_filename(parent_label, "title_case")
    assert "> [!note] Wayfinder" in text
    assert f"> Up: [[{parent_fname}|{parent_label}]]" in text
    assert "> Map: [[Atlas|Atlas]]" in text


def test_render_note_contains_connections_callout():
    import re
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert "> [!info] Connections" in text
    assert re.search(r"> - \[\[.*\]\] — .* \[EXTRACTED|INFERRED|AMBIGUOUS\]", text)


def test_render_note_contains_metadata_callout():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert "> [!abstract] Metadata" in text
    assert "> source_file: src/model.py" in text
    assert "> source_location: L42" in text
    assert "> community: ML Architecture" in text


def test_render_note_section_order_d32():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    # D-32: frontmatter end → heading → wayfinder → connections → metadata
    idx_fm_end = text.index("---\n", 3)  # second --- (after frontmatter content)
    idx_heading = text.index("# Transformer")
    idx_wayfinder = text.index("> [!note] Wayfinder")
    idx_connections = text.index("> [!info] Connections")
    idx_metadata = text.index("> [!abstract] Metadata")
    assert idx_fm_end < idx_heading < idx_wayfinder < idx_connections < idx_metadata


def test_render_note_all_four_non_moc_types_work():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    for note_type in ("thing", "statement", "person", "source"):
        fname, text = render_note("n_transformer", G, profile, note_type, ctx)
        assert fname.endswith(".md"), f"{note_type}: fname missing .md"
        assert len(text) > 0, f"{note_type}: text is empty"
        assert f"type: {note_type}" in text, f"{note_type}: type not in frontmatter"


def test_render_note_wikilink_alias_human_label():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    _, text = render_note("n_transformer", G, profile, "thing", ctx)
    # Display alias must use human label (with spaces), not slugified name
    assert "[[Attention_Mechanism|Attention Mechanism]]" in text
    assert "[[Attention_Mechanism|Attention_Mechanism]]" not in text


def test_render_note_unknown_node_raises_valueerror():
    import pytest
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    with pytest.raises(ValueError, match=r"node_id .* not in graph"):
        render_note("nope", G, profile, "thing", ctx)


def test_render_note_uses_user_template_override(tmp_path):
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    # Create custom user template override
    tpl_dir = tmp_path / ".graphify" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "thing.md").write_text(
        "${frontmatter}\n# Custom: ${label}\n\n${connections_callout}\n${metadata_callout}",
        encoding="utf-8",
    )
    _, text = render_note("n_transformer", G, profile, "thing", ctx, vault_dir=tmp_path)
    assert "# Custom: Transformer" in text


def test_render_note_lazy_import(tmp_path):
    import graphify
    from tests.fixtures.template_context import make_min_graph, make_classification_context

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    fname, text = graphify.render_note("n_transformer", G, profile, "thing", ctx, vault_dir=tmp_path)
    assert fname == "Transformer.md"
    assert text.startswith("---")


def test_render_note_without_vault_dir_uses_builtins_only():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    # vault_dir omitted — must use built-in templates, no exception
    fname, text = render_note("n_transformer", G, profile, "thing", ctx)
    assert "---" in text
    assert "# Transformer" in text


def test_render_note_raises_valueerror_for_unknown_node():
    import pytest
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    with pytest.raises(ValueError, match=r"node_id .* not in graph"):
        render_note("nope", G, profile, "thing", ctx)


def test_render_note_raises_valueerror_for_invalid_note_type():
    import pytest
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    with pytest.raises(ValueError, match=r"note_type .* not in"):
        render_note("n_transformer", G, profile, "whatever", ctx)


# ---------------------------------------------------------------------------
# Plan 04 Task 1: _build_members_section tests
# ---------------------------------------------------------------------------


def test_build_members_section_groups_by_type():
    from graphify.templates import _build_members_section

    members_by_type = {
        "thing": [{"id": "n1", "label": "Transformer"}, {"id": "n2", "label": "Attention"}],
        "statement": [],
        "person": [],
        "source": [{"id": "n3", "label": "Attention Is All You Need"}],
    }
    result = _build_members_section(members_by_type, "title_case")
    # Things group present with correct wikilinks
    assert "> [!info] Things" in result
    assert "[[Transformer|Transformer]]" in result
    assert "[[Attention|Attention]]" in result
    # Sources group present
    assert "> [!info] Sources" in result
    assert "[[Attention_Is_All_You_Need|Attention Is All You Need]]" in result
    # Empty groups omitted (D-30)
    assert "> [!info] Statements" not in result
    assert "> [!info] People" not in result


def test_build_members_section_group_order():
    from graphify.templates import _build_members_section

    members_by_type = {
        "thing": [{"id": "n1", "label": "Thing One"}],
        "statement": [{"id": "n2", "label": "Statement One"}],
        "person": [{"id": "n3", "label": "Person One"}],
        "source": [{"id": "n4", "label": "Source One"}],
    }
    result = _build_members_section(members_by_type, "title_case")
    idx_things = result.index("> [!info] Things")
    idx_statements = result.index("> [!info] Statements")
    idx_people = result.index("> [!info] People")
    idx_sources = result.index("> [!info] Sources")
    assert idx_things < idx_statements < idx_people < idx_sources


def test_build_members_section_empty_returns_empty_string():
    from graphify.templates import _build_members_section

    members_by_type = {"thing": [], "statement": [], "person": [], "source": []}
    result = _build_members_section(members_by_type, "title_case")
    assert result == ""


def test_build_members_section_wikilinks_auto_aliased():
    from graphify.templates import _build_members_section

    members_by_type = {
        "thing": [{"id": "n1", "label": "Attention Mechanism"}],
        "statement": [],
        "person": [],
        "source": [],
    }
    result = _build_members_section(members_by_type, "title_case")
    assert "[[Attention_Mechanism|Attention Mechanism]]" in result


# ---------------------------------------------------------------------------
# Plan 04 Task 1: _build_sub_communities_callout tests
# ---------------------------------------------------------------------------


def test_build_sub_communities_callout_renders_nested_bullets():
    from graphify.templates import _build_sub_communities_callout

    sub_communities = [
        {"label": "Tiny Cluster", "members": [{"id": "n1", "label": "Node A"}, {"id": "n2", "label": "Node B"}]}
    ]
    result = _build_sub_communities_callout(sub_communities, "title_case")
    assert result == "> [!abstract] Sub-communities\n> - **Tiny Cluster:** [[Node_A|Node A]], [[Node_B|Node B]]"


def test_build_sub_communities_callout_multiple_sub_communities():
    from graphify.templates import _build_sub_communities_callout

    sub_communities = [
        {"label": "Cluster One", "members": [{"id": "n1", "label": "Node A"}]},
        {"label": "Cluster Two", "members": [{"id": "n2", "label": "Node B"}]},
    ]
    result = _build_sub_communities_callout(sub_communities, "title_case")
    lines = result.split("\n")
    bullet_lines = [l for l in lines if l.startswith("> - **")]
    assert len(bullet_lines) == 2


def test_build_sub_communities_callout_empty_returns_empty_string():
    from graphify.templates import _build_sub_communities_callout

    result = _build_sub_communities_callout([], "title_case")
    assert result == ""


def test_build_sub_communities_callout_single_member():
    from graphify.templates import _build_sub_communities_callout

    sub_communities = [{"label": "Solo Cluster", "members": [{"id": "n1", "label": "Solo Node"}]}]
    result = _build_sub_communities_callout(sub_communities, "title_case")
    assert "[[Solo_Node|Solo Node]]" in result
    assert "> - **Solo Cluster:**" in result


# ---------------------------------------------------------------------------
# Plan 04 Task 1: _build_dataview_block tests
# ---------------------------------------------------------------------------


def test_build_dataview_block_substitutes_community_tag():
    from graphify.profile import _DEFAULT_PROFILE
    from graphify.templates import _build_dataview_block

    profile = {
        "obsidian": {
            "dataview": {
                "moc_query": _DEFAULT_PROFILE["obsidian"]["dataview"]["moc_query"],
            }
        }
    }
    result = _build_dataview_block(profile, "ml-architecture", "Atlas/Maps/")
    assert result.startswith("```dataview\n")
    assert result.endswith("\n```")
    assert "FROM #community/ml-architecture" in result
    assert "SORT file.name ASC" in result


def test_build_dataview_block_honors_custom_moc_query():
    from graphify.templates import _build_dataview_block

    custom_query = 'TABLE file.name, type\nFROM #community/${community_tag}\nWHERE type = "thing"\nLIMIT 20'
    profile = {"obsidian": {"dataview": {"moc_query": custom_query}}}
    result = _build_dataview_block(profile, "ml-architecture", "Atlas/Maps/")
    assert "LIMIT 20" in result
    assert '#community/ml-architecture' in result
    assert 'WHERE type = "thing"' in result
    assert "SORT file.name ASC" not in result


def test_build_dataview_block_two_phase_isolation():
    from graphify.templates import _build_dataview_block

    # User's moc_query contains a literal ${label} token (made-up variable)
    profile = {"obsidian": {"dataview": {"moc_query": "TABLE ${label} FROM #community/${community_tag}"}}}
    result = _build_dataview_block(profile, "foo", "Atlas/Maps/")
    # safe_substitute must leave ${label} unchanged (not in {community_tag, folder})
    assert "${label}" in result
    assert "#community/foo" in result
    assert result.startswith("```dataview")


def test_build_dataview_block_missing_moc_query_uses_default():
    from graphify.templates import _build_dataview_block

    # profile has obsidian: {} (no dataview key)
    profile = {"obsidian": {}}
    result = _build_dataview_block(profile, "ml-architecture", "Atlas/Maps/")
    # Fallback must produce a non-empty dataview block
    assert result.startswith("```dataview")
    assert len(result) > 20


# ---------------------------------------------------------------------------
# Plan 04 Task 2: render_moc + render_community_overview tests
# ---------------------------------------------------------------------------


def test_render_moc_returns_tuple():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    fname, text = render_moc(0, G, communities, profile, ctx)
    assert isinstance(fname, str)
    assert fname.endswith(".md")
    assert isinstance(text, str)
    assert len(text) > 0


def test_render_moc_filename_from_community_name():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(community_name="ML Architecture")
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    fname, _ = render_moc(0, G, communities, profile, ctx)
    assert fname == "Ml_Architecture.md"


def test_render_moc_frontmatter_type_moc():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "type: moc" in text


def test_render_moc_frontmatter_fields():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    # Extract frontmatter block
    lines = text.split("\n")
    fm_end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    fm_lines = lines[1:fm_end]
    fm_keys = [l.split(":")[0].strip() for l in fm_lines if ":" in l and not l.startswith("  ")]
    # D-24 order: up < created < tags < type, community before cohesion
    for earlier, later in [("up", "created"), ("created", "tags"), ("tags", "type")]:
        if earlier in fm_keys and later in fm_keys:
            assert fm_keys.index(earlier) < fm_keys.index(later), (
                f"Expected '{earlier}' before '{later}' but got order: {fm_keys}"
            )
    if "community" in fm_keys and "cohesion" in fm_keys:
        assert fm_keys.index("community") < fm_keys.index("cohesion")


def test_render_moc_frontmatter_tags_include_community_slug():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(community_tag="ml-architecture")
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "tags:" in text
    assert "community/ml-architecture" in text


def test_render_moc_contains_members_section():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "> [!info] Things" in text
    assert "[[Transformer|Transformer]]" in text


def test_render_moc_contains_dataview_fence():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "```dataview" in text
    assert "FROM #community/ml-architecture" in text
    assert "SORT file.name ASC" in text


def test_render_moc_custom_moc_query_respected():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {
        "naming": {"convention": "title_case"},
        "obsidian": {
            "atlas_root": "Atlas",
            "dataview": {"moc_query": "TABLE file.name FROM #community/${community_tag} LIMIT 5"},
        },
    }
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "LIMIT 5" in text
    assert "#community/ml-architecture" in text
    assert "SORT file.name ASC" not in text


def test_render_moc_wayfinder_links_to_atlas():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "> [!note] Wayfinder" in text
    assert "> Up: [[Atlas|Atlas]]" in text
    assert "> Map: [[Atlas|Atlas]]" in text


def test_render_moc_section_order_d31():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(sub_communities=[{"label": "Tiny", "members": [{"id": "n_x", "label": "X"}]}])
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    # D-31: frontmatter closing --- < heading < wayfinder < members < sub_communities < dataview < metadata
    idx_fm_end = text.index("---\n", 3)
    idx_heading = text.index("# ML Architecture")
    idx_wayfinder = text.index("> [!note] Wayfinder")
    idx_members = text.index("> [!info]")
    idx_sub = text.index("> [!abstract] Sub-communities")
    idx_dataview = text.index("```dataview")
    idx_metadata = text.index("> [!abstract] Metadata")
    assert idx_fm_end < idx_heading < idx_wayfinder < idx_members < idx_sub < idx_dataview < idx_metadata


def test_render_moc_sub_communities_rendered_when_present():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(sub_communities=[{"label": "Tiny", "members": [{"id": "n_x", "label": "X"}]}])
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "> [!abstract] Sub-communities" in text
    assert "[[X|X]]" in text


def test_render_moc_sub_communities_absent_when_empty():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(sub_communities=[])
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "> [!abstract] Sub-communities" not in text


def test_render_moc_cohesion_included_in_frontmatter():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(cohesion=0.82)
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "cohesion: 0.82" in text


def test_render_community_overview_uses_community_template(tmp_path):
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_community_overview

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    # With custom community.md override
    tpl_dir = tmp_path / ".graphify" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "community.md").write_text(
        "${frontmatter}\n# Custom Community: ${label}\n${members_section}\n${dataview_block}",
        encoding="utf-8",
    )
    fname, text = render_community_overview(0, G, communities, profile, ctx, vault_dir=tmp_path)
    assert fname.endswith(".md")
    assert "# Custom Community: ML Architecture" in text


def test_render_moc_lazy_import():
    import graphify

    assert callable(graphify.render_moc)
    assert callable(graphify.render_community_overview)


def test_render_moc_without_vault_dir_uses_builtins_only():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    # vault_dir omitted — must not raise and must use built-in moc.md
    fname, text = render_moc(0, G, communities, profile, ctx)
    assert "# ML Architecture" in text
    assert not fname == ""


# ---------------------------------------------------------------------------
# Plan 04 Task 2: regression tests
# ---------------------------------------------------------------------------


def test_moc_section_order_end_to_end_matches_d31():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(sub_communities=[{"label": "Mini", "members": [{"id": "n_x", "label": "X"}]}])
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    idx_fm_end = text.index("---\n", 3)
    idx_heading = text.index("# ML Architecture")
    idx_wayfinder = text.index("> [!note] Wayfinder")
    idx_members = text.index("> [!info]")
    idx_sub = text.index("> [!abstract] Sub-communities")
    idx_dataview = text.index("```dataview")
    idx_metadata = text.index("> [!abstract] Metadata")
    assert idx_fm_end < idx_heading < idx_wayfinder < idx_members < idx_sub < idx_dataview < idx_metadata


def test_frontmatter_field_order_d24_moc():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    lines = text.split("\n")
    fm_end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    fm_keys = [l.split(":")[0].strip() for l in lines[1:fm_end] if ":" in l and not l.startswith("  ")]
    for earlier, later in [("up", "created"), ("created", "tags"), ("tags", "type")]:
        if earlier in fm_keys and later in fm_keys:
            assert fm_keys.index(earlier) < fm_keys.index(later)


def test_templater_token_passthrough_in_user_moc_template(tmp_path):
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_community_overview

    G = make_min_graph()
    ctx = make_moc_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    tpl_dir = tmp_path / ".graphify" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "community.md").write_text(
        "${frontmatter}\n# ${label}\n<% tp.file.title %>\n${members_section}\n${dataview_block}",
        encoding="utf-8",
    )
    _, text = render_community_overview(0, G, communities, profile, ctx, vault_dir=tmp_path)
    assert "<% tp.file.title %>" in text


def test_render_moc_does_not_consult_graph():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    # Add extra nodes NOT in classification_context members_by_type
    G.add_node("n_ghost_1", label="GhostNodeOne", file_type="code", source_file="src/ghost.py")
    G.add_node("n_ghost_2", label="GhostNodeTwo", file_type="code", source_file="src/ghost.py")
    G.add_edge("n_ghost_1", "n_ghost_2", relation="calls", confidence="EXTRACTED")
    G.add_edge("n_transformer", "n_ghost_1", relation="imports", confidence="EXTRACTED")

    # ctx members_by_type contains ONLY n_transformer
    ctx = make_moc_context(members_by_type={
        "thing": [{"id": "n_transformer", "label": "Transformer"}],
        "statement": [], "person": [], "source": [],
    })
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "GhostNodeOne" not in text
    assert "GhostNodeTwo" not in text


def test_build_sub_communities_callout_renders_abstract_callout():
    from graphify.templates import _build_sub_communities_callout

    sub_communities = [
        {"label": "Tiny Cluster", "members": [{"id": "n1", "label": "Node A"}, {"id": "n2", "label": "Node B"}]}
    ]
    result = _build_sub_communities_callout(sub_communities, "title_case")
    assert result.startswith("> [!abstract] Sub-communities")


def test_render_moc_includes_sub_communities_when_present():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    ctx = make_moc_context(sub_communities=[
        {"label": "Below Threshold Cluster", "members": [{"id": "n_x", "label": "X"}, {"id": "n_y", "label": "Y"}]}
    ])
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    communities = {0: ["n_transformer", "n_paper"]}
    _, text = render_moc(0, G, communities, profile, ctx)
    # Below-threshold sub-community must appear as inline callout inside MOC (no separate file)
    assert "> [!abstract] Sub-communities" in text
