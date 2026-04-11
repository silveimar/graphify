"""Unit tests for graphify.merge — primitives: dataclasses, frontmatter reader,
sentinel parser, and policy dispatcher."""
from __future__ import annotations

import dataclasses
import datetime
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Task 1 — Dataclasses + _DEFAULT_FIELD_POLICIES (RED tests)
# ---------------------------------------------------------------------------

class TestDataclassesAndPolicies:

    def test_imports_succeed(self):
        from graphify.merge import (
            MergeAction, MergePlan, MergeResult, _DEFAULT_FIELD_POLICIES,
        )
        assert MergeAction is not None
        assert MergePlan is not None
        assert MergeResult is not None
        assert _DEFAULT_FIELD_POLICIES is not None

    def test_merge_action_constructs_with_defaults(self):
        from graphify.merge import MergeAction
        a = MergeAction(path=Path("x.md"), action="CREATE", reason="new")
        assert a.changed_fields == []
        assert a.changed_blocks == []
        assert a.conflict_kind is None

    def test_merge_action_is_frozen(self):
        from graphify.merge import MergeAction
        a = MergeAction(path=Path("x.md"), action="CREATE", reason="new")
        with pytest.raises(dataclasses.FrozenInstanceError):
            a.path = Path("y.md")  # type: ignore[misc]

    def test_valid_actions_set_contains_exact_vocabulary(self):
        from graphify.merge import _VALID_ACTIONS
        assert _VALID_ACTIONS == frozenset({
            "CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"
        })

    def test_default_field_policies_type_is_replace(self):
        from graphify.merge import _DEFAULT_FIELD_POLICIES
        assert _DEFAULT_FIELD_POLICIES["type"] == "replace"

    def test_default_field_policies_tags_is_union(self):
        from graphify.merge import _DEFAULT_FIELD_POLICIES
        assert _DEFAULT_FIELD_POLICIES["tags"] == "union"

    def test_default_field_policies_rank_is_preserve(self):
        from graphify.merge import _DEFAULT_FIELD_POLICIES
        assert _DEFAULT_FIELD_POLICIES["rank"] == "preserve"

    def test_default_field_policies_created_is_preserve(self):
        from graphify.merge import _DEFAULT_FIELD_POLICIES
        assert _DEFAULT_FIELD_POLICIES["created"] == "preserve"

    def test_default_field_policies_graphify_managed_is_replace(self):
        from graphify.merge import _DEFAULT_FIELD_POLICIES
        assert _DEFAULT_FIELD_POLICIES["graphify_managed"] == "replace"

    def test_default_field_policies_all_values_valid(self):
        from graphify.merge import _DEFAULT_FIELD_POLICIES
        from graphify.profile import _VALID_FIELD_POLICY_MODES
        for key, mode in _DEFAULT_FIELD_POLICIES.items():
            assert mode in _VALID_FIELD_POLICY_MODES, f"{key!r} has invalid mode {mode!r}"

    def test_merge_plan_constructs_and_is_frozen(self):
        from graphify.merge import MergePlan
        p = MergePlan(actions=[], orphans=[], summary={})
        assert p.summary == {}
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.orphans = []  # type: ignore[misc]

    def test_merge_result_shape(self):
        from graphify.merge import MergeAction, MergePlan, MergeResult
        plan = MergePlan(actions=[], orphans=[], summary={})
        r = MergeResult(plan=plan, succeeded=[], failed=[], skipped_identical=[])
        assert r.succeeded == []
        assert r.failed == []
        assert r.skipped_identical == []


# ---------------------------------------------------------------------------
# Task 2 — Frontmatter reader round-trip tests (RED tests)
# ---------------------------------------------------------------------------

def _round_trip(fields: dict) -> dict:
    from graphify.profile import _dump_frontmatter
    from graphify.merge import _parse_frontmatter
    dumped = _dump_frontmatter(fields)
    parsed = _parse_frontmatter(dumped)
    assert parsed is not None, f"parse returned None for dumped: {dumped!r}"
    return parsed


class TestParseFrontmatter:

    def test_parse_frontmatter_round_trip_scalar(self):
        result = _round_trip({"type": "thing", "community": "Transformer"})
        assert result == {"type": "thing", "community": "Transformer"}

    def test_parse_frontmatter_round_trip_block_list(self):
        result = _round_trip({"tags": ["community/transformer", "graphify/thing"]})
        assert result == {"tags": ["community/transformer", "graphify/thing"]}

    def test_parse_frontmatter_round_trip_bool(self):
        result = _round_trip({"graphify_managed": True})
        assert result == {"graphify_managed": True}
        assert isinstance(result["graphify_managed"], bool)

    def test_parse_frontmatter_round_trip_int(self):
        result = _round_trip({"rank": 5})
        assert result == {"rank": 5}
        assert isinstance(result["rank"], int)

    def test_parse_frontmatter_round_trip_float(self):
        result = _round_trip({"cohesion": 0.82})
        assert result == {"cohesion": 0.82}
        assert isinstance(result["cohesion"], float)

    def test_parse_frontmatter_round_trip_date(self):
        result = _round_trip({"created": datetime.date(2026, 4, 11)})
        assert result == {"created": datetime.date(2026, 4, 11)}
        assert isinstance(result["created"], datetime.date)

    def test_parse_frontmatter_quoted_scalar(self):
        result = _round_trip({"source_file": "foo: bar"})
        assert result == {"source_file": "foo: bar"}

    def test_parse_frontmatter_escaped_quote(self):
        result = _round_trip({"label": 'say "hi"'})
        assert result == {"label": 'say "hi"'}

    def test_parse_frontmatter_wikilink_inside_list(self):
        result = _round_trip({"up": ["[[Parent|Parent]]"]})
        assert result == {"up": ["[[Parent|Parent]]"]}

    def test_parse_frontmatter_preserves_insertion_order(self):
        from graphify.profile import _dump_frontmatter
        from graphify.merge import _parse_frontmatter
        fields = {"a": "1", "b": "2", "c": "3"}
        dumped = _dump_frontmatter(fields)
        parsed = _parse_frontmatter(dumped)
        assert parsed is not None
        assert list(parsed.keys()) == ["a", "b", "c"]

    def test_parse_frontmatter_malformed_returns_none(self):
        from graphify.merge import _parse_frontmatter
        result = _parse_frontmatter("---\nbad: : : :\n---")
        assert result is None

    def test_parse_frontmatter_no_frontmatter_block_returns_empty(self):
        from graphify.merge import _parse_frontmatter
        result = _parse_frontmatter("Just a body with no frontmatter delimiters.")
        assert result == {}

    def test_parse_frontmatter_rejects_yaml_tags_as_literal(self):
        """T-04-08: crafted !!python tags must round-trip as literal strings, not execute."""
        from graphify.profile import _dump_frontmatter
        from graphify.merge import _parse_frontmatter
        # safe_frontmatter_value will quote the ! leading indicator
        fields = {"key": "!!python/object/apply:os.system"}
        dumped = _dump_frontmatter(fields)
        parsed = _parse_frontmatter(dumped)
        assert parsed is not None
        assert parsed["key"] == "!!python/object/apply:os.system"


# ---------------------------------------------------------------------------
# Task 2 — Sentinel block parser tests (RED tests)
# ---------------------------------------------------------------------------

class TestParseSentinelBlocks:

    def test_parse_sentinel_blocks_extracts_single_block(self):
        from graphify.merge import _parse_sentinel_blocks
        body = "<!-- graphify:wayfinder:start -->\nCONTENT\n<!-- graphify:wayfinder:end -->"
        result = _parse_sentinel_blocks(body)
        assert "wayfinder" in result
        assert result["wayfinder"] == "CONTENT"

    def test_parse_sentinel_blocks_extracts_multiple_blocks(self):
        from graphify.merge import _parse_sentinel_blocks
        body = (
            "<!-- graphify:wayfinder:start -->\nWF\n<!-- graphify:wayfinder:end -->\n"
            "some user text\n"
            "<!-- graphify:connections:start -->\nCONN\n<!-- graphify:connections:end -->\n"
            "<!-- graphify:metadata:start -->\nMETA\n<!-- graphify:metadata:end -->"
        )
        result = _parse_sentinel_blocks(body)
        assert result == {"wayfinder": "WF", "connections": "CONN", "metadata": "META"}

    def test_parse_sentinel_blocks_unpaired_start_raises_malformed(self):
        from graphify.merge import _parse_sentinel_blocks, _MalformedSentinel
        body = "<!-- graphify:wayfinder:start -->\nno end marker"
        with pytest.raises(_MalformedSentinel):
            _parse_sentinel_blocks(body)

    def test_parse_sentinel_blocks_unpaired_end_raises_malformed(self):
        from graphify.merge import _parse_sentinel_blocks, _MalformedSentinel
        body = "<!-- graphify:wayfinder:end -->\nno start marker above"
        with pytest.raises(_MalformedSentinel):
            _parse_sentinel_blocks(body)

    def test_parse_sentinel_blocks_nested_same_name_raises_malformed(self):
        from graphify.merge import _parse_sentinel_blocks, _MalformedSentinel
        body = (
            "<!-- graphify:wayfinder:start -->\n"
            "<!-- graphify:wayfinder:start -->\n"
            "content\n"
            "<!-- graphify:wayfinder:end -->\n"
            "<!-- graphify:wayfinder:end -->"
        )
        with pytest.raises(_MalformedSentinel):
            _parse_sentinel_blocks(body)

    def test_parse_sentinel_blocks_missing_block_is_empty_not_error(self):
        from graphify.merge import _parse_sentinel_blocks
        body = "<!-- graphify:wayfinder:start -->\nWF\n<!-- graphify:wayfinder:end -->"
        result = _parse_sentinel_blocks(body)
        # Only wayfinder is present; connections absence is D-68 "respected"
        assert "wayfinder" in result
        assert "connections" not in result


# ---------------------------------------------------------------------------
# Task 3 — Policy dispatcher tests (RED tests)
# ---------------------------------------------------------------------------

class TestPolicyDispatcher:

    def test_resolve_field_policy_uses_builtin_for_known_key(self):
        from graphify.merge import _resolve_field_policy
        assert _resolve_field_policy("tags", profile={}) == "union"

    def test_resolve_field_policy_uses_builtin_for_replace_key(self):
        from graphify.merge import _resolve_field_policy
        assert _resolve_field_policy("type", profile={}) == "replace"

    def test_resolve_field_policy_unknown_key_defaults_to_preserve(self):
        from graphify.merge import _resolve_field_policy
        assert _resolve_field_policy("priority", profile={}) == "preserve"

    def test_resolve_field_policy_user_override_wins_for_known_key(self):
        from graphify.merge import _resolve_field_policy
        profile = {"merge": {"field_policies": {"tags": "replace"}}}
        assert _resolve_field_policy("tags", profile=profile) == "replace"

    def test_resolve_field_policy_user_override_wins_for_unknown_key(self):
        from graphify.merge import _resolve_field_policy
        profile = {"merge": {"field_policies": {"priority": "replace"}}}
        assert _resolve_field_policy("priority", profile=profile) == "replace"

    def test_resolve_field_policy_preserves_other_builtins_when_overriding_one(self):
        from graphify.merge import _resolve_field_policy
        # Override only tags — type should still come from built-in
        override_profile = {"merge": {"field_policies": {"tags": "replace"}}}
        assert _resolve_field_policy("type", profile=override_profile) == "replace"

    def test_resolve_field_policy_preserve_fields_list_forces_preserve(self):
        from graphify.merge import _resolve_field_policy
        profile = {"merge": {
            "preserve_fields": ["tags"],
            "field_policies": {"tags": "replace"},  # would normally win over built-in
        }}
        assert _resolve_field_policy("tags", profile) == "preserve", \
            "preserve_fields list must override field_policies"

    def test_apply_field_policy_replace_overwrites(self):
        from graphify.merge import _apply_field_policy
        assert _apply_field_policy("type", current="statement", new="thing", mode="replace") == "thing"

    def test_apply_field_policy_preserve_keeps_current(self):
        from graphify.merge import _apply_field_policy
        assert _apply_field_policy("rank", current=5, new=10, mode="preserve") == 5

    def test_apply_field_policy_preserve_keeps_missing_current(self):
        from graphify.merge import _apply_field_policy
        assert _apply_field_policy("rank", current=None, new=10, mode="preserve") is None

    def test_apply_field_policy_union_merges_lists_stable_order(self):
        from graphify.merge import _apply_field_policy
        result = _apply_field_policy(
            "tags",
            current=["user/x", "community/t"],
            new=["community/t", "graphify/thing"],
            mode="union",
        )
        assert result == ["user/x", "community/t", "graphify/thing"]

    def test_apply_field_policy_union_with_empty_current(self):
        from graphify.merge import _apply_field_policy
        result = _apply_field_policy("up", current=[], new=["[[Parent|Parent]]"], mode="union")
        assert result == ["[[Parent|Parent]]"]

    def test_apply_field_policy_union_with_none_current(self):
        from graphify.merge import _apply_field_policy
        result = _apply_field_policy("up", current=None, new=["[[Parent|Parent]]"], mode="union")
        assert result == ["[[Parent|Parent]]"]

    def test_apply_field_policy_replace_with_none_new_removes(self):
        from graphify.merge import _apply_field_policy
        assert _apply_field_policy("cohesion", current=0.82, new=None, mode="replace") is None

    def test_apply_field_policy_union_on_non_list_falls_back_to_replace(self):
        from graphify.merge import _apply_field_policy
        result = _apply_field_policy("tags", current="not-a-list", new=["a"], mode="union")
        assert result == ["a"]


# ---------------------------------------------------------------------------
# Phase 4 Task 3: compute_merge_plan integration tests (RED first)
# ---------------------------------------------------------------------------

import shutil


def _copy_vault_fixture(name: str, tmp_path) -> Path:
    """Copy a checked-in vault fixture into tmp_path and return its root."""
    src = Path(__file__).parent / "fixtures" / "vaults" / name
    dst = tmp_path / name
    shutil.copytree(src, dst)
    return dst


def _rendered_note_matching_pristine(vault_root: Path) -> dict:
    """Build a RenderedNote whose frontmatter_fields and body match the
    pristine fixture's file exactly (for idempotent-update tests).
    """
    from graphify.merge import _parse_frontmatter
    target = Path("Atlas/Dots/Things/Transformer.md")
    text = (vault_root / target).read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    body_start = text.index("---", 4) + 3
    body = text[body_start:]
    return {
        "node_id": "transformer",
        "target_path": target,
        "frontmatter_fields": fm,
        "body": body,
    }


def test_compute_empty_vault_empty_render(tmp_path):
    from graphify.merge import compute_merge_plan, MergePlan
    vault = _copy_vault_fixture("empty", tmp_path)
    plan = compute_merge_plan(vault, {}, {})
    assert isinstance(plan, MergePlan)
    assert plan.actions == []
    assert plan.summary == {}


def test_compute_create_action_for_new_path(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("empty", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "CREATE"
    assert plan.actions[0].path.is_absolute()
    assert str(vault) in str(plan.actions[0].path)


def test_compute_update_idempotent_pristine(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    rn = _rendered_note_matching_pristine(vault)
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.action == "UPDATE"
    assert action.changed_fields == []
    assert action.changed_blocks == []
    assert "idempotent" in action.reason


def test_compute_update_changed_source_file(tmp_path):
    from graphify.merge import compute_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = Path("Atlas/Dots/Things/Transformer.md")
    text = (vault / target).read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    new_fields = dict(fm)
    new_fields["source_file"] = "src/transformer_v2.py"
    body_start = text.index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": target,
        "frontmatter_fields": new_fields,
        "body": text[body_start:],
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.action == "UPDATE"
    assert "source_file" in action.changed_fields


def test_compute_update_unions_user_extended_tags(tmp_path):
    from graphify.merge import compute_merge_plan, _parse_frontmatter, _apply_field_policy
    vault = _copy_vault_fixture("user_extended", tmp_path)
    # Render as if graphify only knows about the original two tags (no user/research)
    target = Path("Atlas/Dots/Things/Transformer.md")
    text = (vault / target).read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    # Build a render that doesn't include user/research — simulates fresh graphify output
    new_fields = dict(fm)
    new_fields["tags"] = ["community/transformer-family", "graphify/thing"]
    body_start = text.index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": target,
        "frontmatter_fields": new_fields,
        "body": text[body_start:],
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "UPDATE"
    # Verify union semantics: both user/research (from existing) and graphify/thing (new) survive
    merged_tags = _apply_field_policy(
        "tags",
        current=fm["tags"],
        new=new_fields["tags"],
        mode="union",
    )
    assert "user/research" in merged_tags
    assert "graphify/thing" in merged_tags


def test_compute_skip_conflict_fingerprint_stripped(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("fingerprint_stripped", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "SKIP_CONFLICT"
    assert plan.actions[0].conflict_kind == "unmanaged_file"


def test_compute_skip_conflict_malformed_sentinel(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("malformed_sentinel", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "SKIP_CONFLICT"
    assert plan.actions[0].conflict_kind == "malformed_sentinel"


def test_compute_skip_conflict_unmanaged_collision(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("unmanaged_collision", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "SKIP_CONFLICT"
    assert plan.actions[0].conflict_kind == "unmanaged_file"


def test_compute_preserve_rank_survives_update(tmp_path):
    from graphify.merge import compute_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("preserve_fields_edited", tmp_path)
    # Render matches except we DON'T know about rank/mapState (graphify didn't emit them)
    target = Path("Atlas/Dots/Things/Transformer.md")
    existing = _parse_frontmatter((vault / target).read_text())
    new_fields = {k: v for k, v in existing.items() if k not in ("rank", "mapState")}
    rn = {
        "node_id": "transformer",
        "target_path": target,
        "frontmatter_fields": new_fields,
        "body": (vault / target).read_text().split("---", 2)[2],
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.action == "UPDATE"
    assert "rank" not in action.changed_fields
    assert "mapState" not in action.changed_fields


def test_compute_strategy_skip_is_noop_for_existing(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    rn = _rendered_note_matching_pristine(vault)
    profile = {"merge": {"strategy": "skip"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "SKIP_PRESERVE"


def test_compute_strategy_replace_overwrites_fingerprinted(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    rn = _rendered_note_matching_pristine(vault)
    profile = {"merge": {"strategy": "replace"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "REPLACE"


def test_compute_strategy_replace_still_skips_unmanaged(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("unmanaged_collision", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    profile = {"merge": {"strategy": "replace"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "SKIP_CONFLICT"


def test_compute_orphan_detection_via_previously_managed_paths(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    orphan_path = vault / "Atlas/Dots/Things/Transformer.md"
    plan = compute_merge_plan(
        vault,
        {},  # no rendered notes — everything is an orphan candidate
        {},
        previously_managed_paths={orphan_path},
    )
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "ORPHAN"
    assert len(plan.orphans) == 1


def test_compute_skipped_node_id_produces_no_action(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("empty", tmp_path)
    rn = {
        "node_id": "foo",
        "target_path": Path("Atlas/Dots/Things/Foo.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Foo\n",
    }
    plan = compute_merge_plan(vault, {"foo": rn}, {}, skipped_node_ids={"foo"})
    assert plan.actions == []


def test_compute_is_pure_no_mtime_change(tmp_path):
    from graphify.merge import compute_merge_plan
    import os
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target_file = vault / "Atlas/Dots/Things/Transformer.md"
    mtime_before = os.path.getmtime(target_file)
    rn = _rendered_note_matching_pristine(vault)
    compute_merge_plan(vault, {"transformer": rn}, {})
    mtime_after = os.path.getmtime(target_file)
    assert mtime_before == mtime_after, "compute_merge_plan must not modify any file (purity violation)"


def test_compute_field_order_preserved_after_merge(tmp_path):
    from graphify.merge import _merge_frontmatter, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    existing = _parse_frontmatter(target.read_text())
    new = dict(existing)
    new["cohesion"] = 0.8
    merged, changed = _merge_frontmatter(existing, new, profile={})
    assert "cohesion" in merged
    assert "cohesion" in changed
    keys = list(merged.keys())
    # cohesion must be positioned after its canonical neighbor "community"
    assert keys.index("cohesion") > keys.index("community")
    # Pre-existing keys keep their relative order
    original_keys = [k for k in existing.keys() if k in merged]
    for a, b in zip(original_keys, original_keys[1:]):
        assert keys.index(a) < keys.index(b), f"{a} must precede {b}"


def test_compute_action_paths_are_absolute_and_inside_vault(tmp_path):
    from graphify.merge import compute_merge_plan
    vault = _copy_vault_fixture("empty", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert len(plan.actions) == 1
    action_path = plan.actions[0].path
    assert action_path.is_absolute()
    assert str(vault.resolve()) in str(action_path)
