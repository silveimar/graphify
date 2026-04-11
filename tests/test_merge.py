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
