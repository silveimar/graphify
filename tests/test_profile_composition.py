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
