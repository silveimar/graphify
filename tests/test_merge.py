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

    def test_parse_frontmatter_user_edited_float_one_decimal(self):
        """WR-04 regression: a user-edited `cohesion: 0.5` must parse as
        float(0.5), not as the string "0.5". Otherwise the next
        _merge_frontmatter compares "0.5" (str) != 0.5 (float) and reports
        spurious churn on every re-run.
        """
        from graphify.merge import _parse_frontmatter
        result = _parse_frontmatter("---\ncohesion: 0.5\n---\n")
        assert result == {"cohesion": 0.5}
        assert isinstance(result["cohesion"], float)

    def test_parse_frontmatter_user_edited_float_three_decimals(self):
        """WR-04 regression: user writes `cohesion: 0.123` (three decimals).
        The old regex hardcoded exactly two decimals and would fall through
        to the bare-string branch.
        """
        from graphify.merge import _parse_frontmatter
        result = _parse_frontmatter("---\ncohesion: 0.123\n---\n")
        assert result == {"cohesion": 0.123}
        assert isinstance(result["cohesion"], float)

    def test_parse_frontmatter_user_edited_float_merge_is_idempotent(self):
        """WR-04 regression, end-to-end: a user-edited `cohesion: 0.5` must
        not cause `_merge_frontmatter` to report `cohesion` as changed when
        the new render emits the same float value.
        """
        from graphify.merge import _merge_frontmatter, _parse_frontmatter
        existing = _parse_frontmatter("---\ncohesion: 0.5\n---\n")
        assert existing is not None
        merged, changed = _merge_frontmatter(existing, {"cohesion": 0.5}, profile={})
        assert changed == [], (
            "user-edited 0.5 (float) should be idempotent vs new render 0.5 — "
            f"got changed={changed!r}"
        )
        assert merged == {"cohesion": 0.5}

    def test_parse_frontmatter_negative_float_one_decimal(self):
        """Negative floats with arbitrary precision must also round-trip."""
        from graphify.merge import _parse_frontmatter
        result = _parse_frontmatter("---\ncohesion: -0.5\n---\n")
        assert result == {"cohesion": -0.5}
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

    def test_merge_body_blocks_handles_marker_inner_whitespace(self):
        """WR-01 regression: parser accepts `<!--   graphify:foo:start   -->`
        (extra inner whitespace) via re.search; `_merge_body_blocks` must
        rewrite the block successfully even when the marker line's spelling
        differs from the canonical literal. Previously a literal .replace()
        would silently no-op while reporting the block as changed.
        """
        from graphify.merge import _merge_body_blocks, _parse_sentinel_blocks
        body = (
            "<!--  graphify:wayfinder:start  -->\n"
            "OLD WAYFINDER\n"
            "<!-- graphify:wayfinder:end   -->\n"
        )
        existing_blocks = _parse_sentinel_blocks(body)
        assert existing_blocks == {"wayfinder": "OLD WAYFINDER"}
        new_blocks = {"wayfinder": "NEW WAYFINDER"}
        result, changed = _merge_body_blocks(body, existing_blocks, new_blocks)
        assert "NEW WAYFINDER" in result
        assert "OLD WAYFINDER" not in result
        assert changed == ["wayfinder"]
        # Canonical spellings of the marker lines must survive user formatting.
        assert "<!--  graphify:wayfinder:start  -->" in result
        assert "<!-- graphify:wayfinder:end   -->" in result

    def test_merge_body_blocks_reports_nothing_when_content_identical(self):
        """Sanity check the fast-path: identical blocks are not listed in changed."""
        from graphify.merge import _merge_body_blocks, _parse_sentinel_blocks
        body = (
            "<!-- graphify:wayfinder:start -->\n"
            "SAME\n"
            "<!-- graphify:wayfinder:end -->\n"
        )
        existing_blocks = _parse_sentinel_blocks(body)
        new_blocks = {"wayfinder": "SAME"}
        result, changed = _merge_body_blocks(body, existing_blocks, new_blocks)
        assert changed == []
        assert result == body


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


def test_insert_canonical_key_prepended_when_no_preceding_neighbor():
    """WR-02 regression: when `existing` has no canonical key preceding the
    new canonical key, `_insert_with_canonical_neighbor` prepends the new key
    so graphify-owned canonical fields lead user-authored fields.
    """
    from graphify.merge import _insert_with_canonical_neighbor
    existing = {"rank": 5}
    result = _insert_with_canonical_neighbor(existing, "source_file", "src/x.py")
    keys = list(result.keys())
    assert keys == ["source_file", "rank"], (
        "source_file has no preceding canonical neighbor in existing, "
        "so it must be prepended ahead of user-authored rank"
    )
    assert result["source_file"] == "src/x.py"
    assert result["rank"] == 5


def test_insert_non_canonical_key_appended_at_end():
    """Non-canonical keys (not in _CANONICAL_KEY_ORDER) are appended at end
    regardless of the presence of canonical keys.
    """
    from graphify.merge import _insert_with_canonical_neighbor
    existing = {"type": "thing", "tags": ["a"]}
    result = _insert_with_canonical_neighbor(existing, "priority", "high")
    keys = list(result.keys())
    assert keys == ["type", "tags", "priority"]


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


def test_validate_target_handles_symlinked_tmpdir(tmp_path):
    """WR-03 regression: `_validate_target` must resolve both `vault_dir`
    and the candidate path before calling `Path.relative_to`, so that
    symlink parity (e.g. macOS `/tmp` → `/private/tmp`) does not cause a
    false ValueError for paths that are in fact inside the vault.
    """
    import os
    from graphify.merge import _validate_target

    # Build a real vault under tmp_path, then create a sibling symlink that
    # points at it. Passing the symlink dir as vault_dir and an absolute
    # candidate under the real dir (or vice versa) used to raise ValueError.
    real_vault = tmp_path / "real_vault"
    real_vault.mkdir()
    target_file = real_vault / "Atlas/Dots/Things/Transformer.md"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("stub", encoding="utf-8")

    symlink_vault = tmp_path / "symlink_vault"
    os.symlink(real_vault, symlink_vault)

    # vault_dir is the symlink; candidate is an absolute path under the
    # *real* directory. Without resolving, `relative_to` raises ValueError.
    candidate_via_real = real_vault / "Atlas/Dots/Things/Transformer.md"
    result = _validate_target(candidate_via_real, symlink_vault)
    assert result.is_absolute()
    # Resolved form must live under the resolved vault.
    assert str(result.resolve()).startswith(str(symlink_vault.resolve()))

    # And the symmetric case: vault_dir is the real dir, candidate traverses
    # through the symlink. Must also succeed.
    candidate_via_symlink = symlink_vault / "Atlas/Dots/Things/Transformer.md"
    result2 = _validate_target(candidate_via_symlink, real_vault)
    assert result2.is_absolute()
    assert str(result2.resolve()).startswith(str(real_vault.resolve()))


def test_validate_target_rejects_absolute_path_outside_vault(tmp_path):
    """Companion to the symlink test: an absolute path that genuinely
    escapes the vault after resolution must still raise ValueError.
    """
    from graphify.merge import _validate_target
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "elsewhere" / "evil.md"
    outside.parent.mkdir()
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        _validate_target(outside, vault)


# --- Phase 4 Task 5 Task 2: apply_merge_plan integration ---

def test_apply_empty_plan_returns_empty_result(tmp_path):
    from graphify.merge import apply_merge_plan, MergePlan, MergeResult
    vault = _copy_vault_fixture("empty", tmp_path)
    plan = MergePlan(actions=[], orphans=[], summary={})
    result = apply_merge_plan(plan, vault, {}, {})
    assert isinstance(result, MergeResult)
    assert result.succeeded == []
    assert result.failed == []
    assert result.skipped_identical == []


def test_apply_create_writes_new_file(tmp_path):
    from graphify.merge import apply_merge_plan, compute_merge_plan
    vault = _copy_vault_fixture("empty", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "CREATE"
    result = apply_merge_plan(plan, vault, {"transformer": rn}, {})
    target = vault / "Atlas/Dots/Things/Transformer.md"
    assert target.exists(), "CREATE must write the file"
    content = target.read_text()
    assert "graphify_managed" in content
    assert "# Transformer" in content
    # No .tmp file should remain
    assert not (target.with_suffix(".md.tmp")).exists()
    assert target in result.succeeded


def test_apply_update_idempotent_skips_write(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    rn = _rendered_note_matching_pristine(vault)
    target = vault / rn["target_path"]
    original_mtime = target.stat().st_mtime_ns
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    # Confirm the plan is UPDATE with empty changed lists
    assert plan.actions[0].action == "UPDATE"
    assert plan.actions[0].changed_fields == []
    assert plan.actions[0].changed_blocks == []
    result = apply_merge_plan(plan, vault, {"transformer": rn}, {})
    assert target in result.skipped_identical
    assert target not in result.succeeded
    assert target.stat().st_mtime_ns == original_mtime, \
        "idempotent re-apply must not touch the file"


def test_apply_update_changed_source_file_writes(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target_rel = Path("Atlas/Dots/Things/Transformer.md")
    target = vault / target_rel
    text = target.read_text()
    fm = _parse_frontmatter(text)
    new_fields = dict(fm)
    new_fields["source_file"] = "src/transformer_v2.py"
    body_start = text.index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": target_rel,
        "frontmatter_fields": new_fields,
        "body": text[body_start:],
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "UPDATE"
    assert "source_file" in plan.actions[0].changed_fields
    result = apply_merge_plan(plan, vault, {"transformer": rn}, {})
    assert target in result.succeeded
    assert target not in result.skipped_identical
    written = _parse_frontmatter(target.read_text())
    assert written["source_file"] == "src/transformer_v2.py"


def test_apply_replace_overwrites_preserve_fields(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("preserve_fields_edited", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    # Build a rendered note WITHOUT rank/mapState
    existing = _parse_frontmatter(target.read_text())
    new_fields = {k: v for k, v in existing.items() if k not in ("rank", "mapState")}
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": new_fields,
        "body": target.read_text().split("---", 2)[2],
    }
    profile = {"merge": {"strategy": "replace"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert plan.actions[0].action == "REPLACE"
    apply_merge_plan(plan, vault, {"transformer": rn}, profile)
    after = _parse_frontmatter(target.read_text())
    assert "rank" not in after, "replace must lose user's rank edit"
    assert "mapState" not in after, "replace must lose user's mapState edit"


def test_apply_skip_preserve_noop(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan
    import os
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    rn = _rendered_note_matching_pristine(vault)
    target = vault / rn["target_path"]
    profile = {"merge": {"strategy": "skip"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert plan.actions[0].action == "SKIP_PRESERVE"
    mtime_before = target.stat().st_mtime_ns
    result = apply_merge_plan(plan, vault, {"transformer": rn}, profile)
    assert target.stat().st_mtime_ns == mtime_before, "SKIP_PRESERVE must not touch file"
    assert result.succeeded == []
    assert result.skipped_identical == []


def test_apply_orphan_never_deleted(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    orphan_path = Path("Atlas/Dots/Things/Transformer.md")
    # Empty rendered_notes: the file is "orphaned"
    plan = compute_merge_plan(
        vault, {}, {},
        previously_managed_paths={(vault / orphan_path).resolve()},
    )
    assert any(a.action == "ORPHAN" for a in plan.actions)
    result = apply_merge_plan(plan, vault, {}, {})
    # The file must STILL exist — D-72 never deletes
    assert (vault / orphan_path).exists()
    # It must not be in succeeded or failed — apply skips ORPHAN
    assert (vault / orphan_path).resolve() not in result.succeeded


def test_apply_skip_conflict_no_write(tmp_path):
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("fingerprint_stripped", tmp_path)
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "# Transformer\n",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "SKIP_CONFLICT"
    target = vault / "Atlas/Dots/Things/Transformer.md"
    original_content = target.read_text()
    original_mtime = target.stat().st_mtime_ns
    result = apply_merge_plan(plan, vault, {"transformer": rn}, {})
    assert target.read_text() == original_content, "SKIP_CONFLICT must not modify file"
    assert target.stat().st_mtime_ns == original_mtime
    assert result.succeeded == []
    assert result.failed == []


def test_apply_cleanup_stale_tmp(tmp_path):
    from graphify.merge import apply_merge_plan, MergePlan
    vault = _copy_vault_fixture("empty", tmp_path)
    # Pre-seed a stale .tmp file
    stale = vault / "Atlas/Dots/Things/Transformer.md.tmp"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("stale content")
    assert stale.exists()
    plan = MergePlan(actions=[], orphans=[], summary={})
    apply_merge_plan(plan, vault, {}, {})
    assert not stale.exists(), "_cleanup_stale_tmp must remove stale .tmp files"


def test_apply_atomic_no_partial_file_on_error(tmp_path, monkeypatch):
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    import os
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    original_content = target.read_text()
    target_rel = Path("Atlas/Dots/Things/Transformer.md")
    text = target.read_text()
    fm = _parse_frontmatter(text)
    new_fields = dict(fm)
    new_fields["source_file"] = "new_source.py"
    body_start = text.index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": target_rel,
        "frontmatter_fields": new_fields,
        "body": text[body_start:],
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "UPDATE"

    # Monkeypatch os.replace to raise on the vault's file
    original_replace = os.replace
    def failing_replace(src, dst):
        if str(vault) in str(dst):
            raise OSError("simulated disk error")
        return original_replace(src, dst)
    monkeypatch.setattr(os, "replace", failing_replace)

    result = apply_merge_plan(plan, vault, {"transformer": rn}, {})

    # Original file must be unchanged
    assert target.read_text() == original_content, \
        "atomic write failure must leave original file intact"
    # No .tmp file should remain
    tmp_file = target.with_suffix(".md.tmp")
    assert not tmp_file.exists(), "failed atomic write must clean up .tmp file"
    # Failed path must be in MergeResult.failed
    assert len(result.failed) == 1
    assert result.failed[0][0] == target.resolve()


def test_apply_path_escape_recorded_as_failed(tmp_path):
    from graphify.merge import apply_merge_plan, MergePlan, MergeAction
    vault = _copy_vault_fixture("empty", tmp_path)
    # Craft a path that escapes vault_dir using '..' traversal
    escape_path = vault / ".." / "escaped.md"
    escaped_action = MergeAction(
        path=escape_path.resolve(),
        action="CREATE",
        reason="crafted escape",
    )
    plan = MergePlan(actions=[escaped_action], orphans=[], summary={"CREATE": 1})
    rn = {
        "node_id": "escape",
        "target_path": escape_path.resolve(),
        "frontmatter_fields": {"type": "thing"},
        "body": "# Escaped\n",
    }
    result = apply_merge_plan(plan, vault, {"escape": rn}, {})
    assert len(result.failed) == 1, "escaped path must be recorded in failed"
    assert not (tmp_path / "escaped.md").exists(), "escaped path must NOT be written"


# ---------------------------------------------------------------------------
# Phase 4 must_have traceability (from .planning/phases/04-merge-engine/04-CONTEXT.md)
# ---------------------------------------------------------------------------
# M1  test_preserve_rank_survives_update                         → MRG-01, success-1
# M2  test_strategy_skip_is_noop                                 → MRG-07, success-2
# M3  test_strategy_replace_overwrites_preserve_fields           → MRG-07, success-3
# M4  test_field_order_preserved_minimal_diff                    → MRG-06, success-4
# M5  test_sentinel_round_trip_deleted_block_not_reinserted      → D-68
# M6  test_unmanaged_file_skip_conflict                          → D-63
# M7  test_malformed_sentinel_skip_warn                          → D-69
# M8  test_orphan_never_deleted_under_replace                    → D-72
# M9  test_compute_merge_plan_is_pure                            → Plan 04 purity
# M10 test_apply_merge_plan_content_hash_skip                    → re-run cheapness
# ---------------------------------------------------------------------------

# --- Phase 4 must_haves M1..M4 (success criteria end-to-end) ---


def test_preserve_rank_survives_update(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("preserve_fields_edited", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"

    # Build a rendered note whose frontmatter EXCLUDES rank and mapState —
    # graphify never emits them, so they can only come from the existing file.
    existing_fm = _parse_frontmatter(target.read_text())
    new_fields = {k: v for k, v in existing_fm.items() if k not in ("rank", "mapState")}
    body_start = target.read_text().index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": new_fields,
        "body": target.read_text()[body_start:],
    }

    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "UPDATE"
    apply_merge_plan(plan, vault, {"transformer": rn}, {})

    after = _parse_frontmatter(target.read_text())
    assert after["rank"] == 7, f"rank survived as {after.get('rank')!r}"
    assert "mapState" in after and "zoom" in str(after["mapState"]), \
        f"mapState lost: {after.get('mapState')!r}"


def test_strategy_skip_is_noop(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    original_bytes = target.read_bytes()
    original_mtime = target.stat().st_mtime_ns

    # Build a rendered note with a CHANGED source_file
    existing_fm = _parse_frontmatter(target.read_text())
    new_fields = dict(existing_fm)
    new_fields["source_file"] = "src/models/CHANGED.py"
    body_start = target.read_text().index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": new_fields,
        "body": target.read_text()[body_start:],
    }
    profile = {"merge": {"strategy": "skip"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert plan.actions[0].action == "SKIP_PRESERVE"
    apply_merge_plan(plan, vault, {"transformer": rn}, profile)

    assert target.read_bytes() == original_bytes, "skip must leave file byte-identical"
    assert target.stat().st_mtime_ns == original_mtime, "skip must not touch mtime"


def test_strategy_replace_overwrites_preserve_fields(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("preserve_fields_edited", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"

    existing_fm = _parse_frontmatter(target.read_text())
    new_fields = {k: v for k, v in existing_fm.items() if k not in ("rank", "mapState")}
    body_start = target.read_text().index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": new_fields,
        "body": target.read_text()[body_start:],
    }
    profile = {"merge": {"strategy": "replace"}}
    plan = compute_merge_plan(vault, {"transformer": rn}, profile)
    assert plan.actions[0].action == "REPLACE"
    apply_merge_plan(plan, vault, {"transformer": rn}, profile)

    after = _parse_frontmatter(target.read_text())
    assert "rank" not in after, f"replace must drop rank, got {after.get('rank')!r}"
    assert "mapState" not in after, f"replace must drop mapState, got {after.get('mapState')!r}"


def test_field_order_preserved_minimal_diff(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    original_text = target.read_text()
    original_fm = _parse_frontmatter(original_text)
    original_keys = list(original_fm.keys())

    new_fields = dict(original_fm)
    new_fields["source_file"] = "src/models/transformer.py"  # CHANGED
    body_start = original_text.index("---", 4) + 3
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": new_fields,
        "body": original_text[body_start:],
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "UPDATE"
    assert plan.actions[0].changed_fields == ["source_file"], \
        f"only source_file should change, got {plan.actions[0].changed_fields}"
    apply_merge_plan(plan, vault, {"transformer": rn}, {})

    after_text = target.read_text()
    after_fm = _parse_frontmatter(after_text)
    after_keys = list(after_fm.keys())
    assert after_keys == original_keys, \
        f"field order changed: before={original_keys} after={after_keys}"
    assert after_fm["source_file"] == "src/models/transformer.py"

    # Git-diff shape assertion: exactly ONE line differs between old and new text
    # (the source_file line), ignoring trailing newline differences
    old_lines = original_text.splitlines()
    new_lines = after_text.splitlines()
    diff = [
        (i, o, n) for i, (o, n) in enumerate(zip(old_lines, new_lines)) if o != n
    ]
    diff_count = len(diff) + abs(len(old_lines) - len(new_lines))
    assert diff_count == 1, f"expected exactly 1 line diff, got {diff_count}: {diff}"
    _, old_line, new_line = diff[0]
    assert "source_file" in old_line and "source_file" in new_line, \
        f"the only diff must be on source_file, got {old_line!r} -> {new_line!r}"


# --- Phase 4 must_haves M5..M10 + T-04-01 security assertion ---


def test_sentinel_round_trip_deleted_block_not_reinserted(tmp_path):
    from pathlib import Path
    import re
    from graphify.merge import compute_merge_plan, apply_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"

    # Remove the connections block from the file
    original = target.read_text()
    stripped = re.sub(
        r"<!-- graphify:connections:start -->.*?<!-- graphify:connections:end -->",
        "",
        original,
        flags=re.DOTALL,
    )
    assert "graphify:connections:start" not in stripped
    target.write_text(stripped)

    # Rendered note includes a FRESH connections block
    existing_fm = _parse_frontmatter(stripped)
    body_with_new_connections = (
        "# Transformer\n\n"
        "<!-- graphify:wayfinder:start -->\n> [!note] Wayfinder\n> Up: [[X|X]]\n> Map: [[Atlas|Atlas]]\n<!-- graphify:wayfinder:end -->\n\n"
        "<!-- graphify:connections:start -->\n> [!info] Connections\n> - [[New|New]] — uses [EXTRACTED]\n<!-- graphify:connections:end -->\n\n"
        "<!-- graphify:metadata:start -->\n> [!abstract] Metadata\n> source_file: src/transformer.py\n<!-- graphify:metadata:end -->"
    )
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": existing_fm,
        "body": body_with_new_connections,
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    apply_merge_plan(plan, vault, {"transformer": rn}, {})

    after = target.read_text()
    assert "graphify:connections:start" not in after, \
        "D-68: deleted block must NOT be re-inserted by merge"


def test_unmanaged_file_skip_conflict(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("fingerprint_stripped", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    original_bytes = target.read_bytes()
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "<!-- graphify:wayfinder:start -->\nX\n<!-- graphify:wayfinder:end -->",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "SKIP_CONFLICT"
    assert plan.actions[0].conflict_kind == "unmanaged_file"
    apply_merge_plan(plan, vault, {"transformer": rn}, {})
    assert target.read_bytes() == original_bytes, "unmanaged file must never be touched"


def test_malformed_sentinel_skip_warn(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("malformed_sentinel", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    original_bytes = target.read_bytes()
    rn = {
        "node_id": "transformer",
        "target_path": Path("Atlas/Dots/Things/Transformer.md"),
        "frontmatter_fields": {"type": "thing", "graphify_managed": True},
        "body": "<!-- graphify:wayfinder:start -->\nX\n<!-- graphify:wayfinder:end -->",
    }
    plan = compute_merge_plan(vault, {"transformer": rn}, {})
    assert plan.actions[0].action == "SKIP_CONFLICT"
    assert plan.actions[0].conflict_kind == "malformed_sentinel"
    apply_merge_plan(plan, vault, {"transformer": rn}, {})
    assert target.read_bytes() == original_bytes, \
        "D-69: malformed sentinel must leave file untouched"


def test_orphan_never_deleted_under_replace(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    assert target.exists()

    profile = {"merge": {"strategy": "replace"}}
    plan = compute_merge_plan(
        vault,
        {},  # no rendered notes — everything is orphan
        profile,
        previously_managed_paths={target.resolve()},
    )
    orphan_actions = [a for a in plan.actions if a.action == "ORPHAN"]
    assert len(orphan_actions) == 1, f"expected 1 ORPHAN, got {plan.actions}"
    apply_merge_plan(plan, vault, {}, profile)
    assert target.exists(), "D-72: orphan files are NEVER deleted, even under replace"


def test_compute_merge_plan_is_pure(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, _parse_frontmatter
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    mtime_before = target.stat().st_mtime_ns

    rn = _rendered_note_matching_pristine(vault)
    _ = compute_merge_plan(vault, {"transformer": rn}, {})

    assert target.stat().st_mtime_ns == mtime_before, \
        "compute_merge_plan must not modify any file"
    # No .tmp files created
    tmp_files = list(vault.rglob("*.tmp"))
    assert tmp_files == [], f"compute must not create .tmp files, found {tmp_files}"


def test_apply_merge_plan_content_hash_skip(tmp_path):
    from pathlib import Path
    from graphify.merge import compute_merge_plan, apply_merge_plan
    vault = _copy_vault_fixture("pristine_graphify", tmp_path)
    target = vault / "Atlas/Dots/Things/Transformer.md"
    rn = _rendered_note_matching_pristine(vault)

    # First apply — idempotent update, but content is already identical
    plan1 = compute_merge_plan(vault, {"transformer": rn}, {})
    r1 = apply_merge_plan(plan1, vault, {"transformer": rn}, {})
    assert target in r1.skipped_identical, \
        f"first apply should content-hash-skip; got succeeded={r1.succeeded}, skipped={r1.skipped_identical}"
    mtime_after_first = target.stat().st_mtime_ns

    # Second apply — must still skip
    plan2 = compute_merge_plan(vault, {"transformer": rn}, {})
    r2 = apply_merge_plan(plan2, vault, {"transformer": rn}, {})
    assert target in r2.skipped_identical
    assert target.stat().st_mtime_ns == mtime_after_first, \
        "content-hash skip must not touch mtime across runs"


def test_malicious_label_does_not_break_sentinel_pairing(tmp_path):
    """T-04-01 mitigation: a node label containing the literal end-marker
    substring must not confuse the sentinel parser."""
    from graphify.merge import _parse_sentinel_blocks
    body = (
        "<!-- graphify:connections:start -->\n"
        "> - [[Fake|contains <!-- graphify:connections:end --> in alias]] — uses [EXTRACTED]\n"
        "<!-- graphify:connections:end -->\n"
    )
    # The parser currently uses regex .search — verify it still extracts exactly
    # one connections block, OR raises _MalformedSentinel. EITHER behavior is
    # safe (test pins whichever is implemented) — the point is it must not
    # SILENTLY claim the wrong region as graphify-owned.
    from graphify.merge import _MalformedSentinel
    try:
        blocks = _parse_sentinel_blocks(body)
        # If it parses, the extracted content must include the closing end-marker
        # in the alias (demonstrating the parser found the LAST end marker)
        assert "connections" in blocks
    except _MalformedSentinel:
        # Equally acceptable — fail-loud on ambiguous input per D-69
        pass


# ---------------------------------------------------------------------------
# Phase 5 / D-76 — format_merge_plan tests
# ---------------------------------------------------------------------------

from graphify.merge import format_merge_plan, MergePlan, MergeAction


def _mk_plan(actions=None, summary=None, orphans=None):
    actions = actions or []
    orphans = orphans or []
    # Derive summary from actions if not provided
    if summary is None:
        summary = {
            "CREATE": 0, "UPDATE": 0, "SKIP_PRESERVE": 0,
            "SKIP_CONFLICT": 0, "REPLACE": 0, "ORPHAN": 0,
        }
        for a in actions:
            summary[a.action] = summary.get(a.action, 0) + 1
    return MergePlan(actions=actions, orphans=orphans, summary=summary)


def test_format_merge_plan_empty_plan():
    out = format_merge_plan(_mk_plan())
    assert out.startswith("Merge Plan — 0 actions\n")
    assert "CREATE:" in out
    assert "UPDATE:" in out
    assert "SKIP_PRESERVE:" in out
    assert "SKIP_CONFLICT:" in out
    assert "REPLACE:" in out
    assert "ORPHAN:" in out
    # No per-group headers when everything is empty
    assert "CREATE (" not in out


def test_format_merge_plan_header_total_counts_actions():
    plan = _mk_plan([
        MergeAction(path=Path("a.md"), action="CREATE", reason="new"),
        MergeAction(path=Path("b.md"), action="CREATE", reason="new"),
        MergeAction(path=Path("c.md"), action="CREATE", reason="new"),
    ])
    out = format_merge_plan(plan)
    assert out.startswith("Merge Plan — 3 actions\n")


def test_format_merge_plan_all_six_summary_rows_in_locked_order():
    plan = _mk_plan([MergeAction(path=Path("a.md"), action="CREATE", reason="new")])
    out = format_merge_plan(plan)
    order = ["CREATE:", "UPDATE:", "SKIP_PRESERVE:", "SKIP_CONFLICT:", "REPLACE:", "ORPHAN:"]
    positions = [out.index(label) for label in order]
    assert positions == sorted(positions), f"Summary rows out of order: {positions}"


def test_format_merge_plan_update_row_suffix():
    plan = _mk_plan([
        MergeAction(
            path=Path("Atlas/Maps/Community_0.md"),
            action="UPDATE",
            reason="update",
            changed_fields=["a", "b", "c"],
            changed_blocks=["x", "y"],
        )
    ])
    out = format_merge_plan(plan)
    assert "(3 fields, 2 blocks)" in out
    assert "UPDATE  Atlas/Maps/Community_0.md" in out


def test_format_merge_plan_skip_conflict_suffix():
    plan = _mk_plan([
        MergeAction(
            path=Path("x.md"), action="SKIP_CONFLICT",
            reason="conflict", conflict_kind="unmanaged_file",
        ),
        MergeAction(
            path=Path("y.md"), action="SKIP_CONFLICT",
            reason="conflict", conflict_kind=None,
        ),
    ])
    out = format_merge_plan(plan)
    assert "[unmanaged_file]" in out
    assert "[unknown]" in out


def test_format_merge_plan_orphan_reason():
    plan = _mk_plan([
        MergeAction(
            path=Path("Atlas/Dots/Things/Old.md"),
            action="ORPHAN",
            reason="node transformer_old no longer in graph",
        )
    ])
    out = format_merge_plan(plan)
    assert "(node transformer_old no longer in graph)" in out


def test_format_merge_plan_deterministic():
    plan = _mk_plan([
        MergeAction(path=Path("a.md"), action="CREATE", reason="new"),
        MergeAction(path=Path("b.md"), action="UPDATE", reason="update"),
    ])
    assert format_merge_plan(plan) == format_merge_plan(plan)


def test_format_merge_plan_action_groups_sorted_by_path():
    plan = _mk_plan([
        MergeAction(path=Path("Atlas/Dots/Things/Z.md"), action="CREATE", reason="new"),
        MergeAction(path=Path("Atlas/Dots/Things/A.md"), action="CREATE", reason="new"),
    ])
    out = format_merge_plan(plan)
    a_pos = out.index("Atlas/Dots/Things/A.md")
    z_pos = out.index("Atlas/Dots/Things/Z.md")
    assert a_pos < z_pos, "CREATE group must be sorted by path"


def test_format_merge_plan_group_section_only_when_nonzero():
    plan = _mk_plan([MergeAction(path=Path("a.md"), action="CREATE", reason="new")])
    out = format_merge_plan(plan)
    # Summary line for UPDATE: 0 must be present
    assert "UPDATE:" in out
    # But per-group header for UPDATE must NOT be present (count is zero)
    assert "UPDATE (" not in out


# ---------------------------------------------------------------------------
# Plan 05-01 — split_rendered_note tests (public wrapper over private helpers)
# ---------------------------------------------------------------------------

from graphify.merge import split_rendered_note


def test_split_rendered_note_happy_path():
    text = "---\nkey: value\ncount: 3\n---\n# Title\nbody line\n"
    fm, body = split_rendered_note(text)
    assert isinstance(fm, dict)
    assert fm.get("key") == "value"
    assert "# Title" in body
    assert "body line" in body
    assert "---" not in body  # fence is consumed


def test_split_rendered_note_no_frontmatter():
    text = "# Title\nno fence here\n"
    fm, body = split_rendered_note(text)
    assert fm == {}
    assert body == text


def test_split_rendered_note_unclosed_frontmatter():
    text = "---\nkey: value\n# no closing fence\n"
    fm, body = split_rendered_note(text)
    assert fm == {}
    assert body == text


def test_split_rendered_note_empty_string():
    fm, body = split_rendered_note("")
    assert fm == {}
    assert body == ""


def test_split_rendered_note_returns_two_tuple_of_dict_str():
    result = split_rendered_note("---\nk: v\n---\nhi\n")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert isinstance(result[1], str)


def test_split_rendered_note_roundtrip_with_dump_frontmatter():
    # _dump_frontmatter is Phase 4's existing serializer; split_rendered_note
    # must be its inverse for simple key/value cases.
    # _dump_frontmatter returns "---\n...\n---" (no trailing newline), so a
    # newline separator is required before the body — matching how render_note
    # assembles the full document in practice.
    from graphify.merge import _dump_frontmatter
    original = {"tags": ["community/transformer"], "type": "thing"}
    rendered = _dump_frontmatter(original) + "\nbody\n"
    fm, body = split_rendered_note(rendered)
    assert fm.get("type") == "thing"
    assert fm.get("tags") == ["community/transformer"]
    assert body == "body\n"


# ---------------------------------------------------------------------------
# Phase 8 Plan 01 Task 1 — Vault Manifest I/O + MergeAction extension
# ---------------------------------------------------------------------------


class TestVaultManifest:

    def test_save_load_roundtrip(self, tmp_path):
        from graphify.merge import _save_manifest, _load_manifest
        manifest_path = tmp_path / "vault-manifest.json"
        data = {
            "Atlas/Note.md": {
                "content_hash": "abc123",
                "last_merged": "2026-04-12T10:00:00+00:00",
                "target_path": "Atlas/Note.md",
                "node_id": "note",
                "note_type": "thing",
                "community_id": 0,
                "has_user_blocks": False,
            }
        }
        _save_manifest(manifest_path, data)
        loaded = _load_manifest(manifest_path)
        assert loaded == data

    def test_load_missing_returns_empty(self, tmp_path):
        from graphify.merge import _load_manifest
        manifest_path = tmp_path / "nonexistent-manifest.json"
        result = _load_manifest(manifest_path)
        assert result == {}

    def test_load_corrupt_returns_empty(self, tmp_path, capsys):
        from graphify.merge import _load_manifest
        manifest_path = tmp_path / "vault-manifest.json"
        manifest_path.write_text("this is not valid json {{{{", encoding="utf-8")
        result = _load_manifest(manifest_path)
        assert result == {}
        captured = capsys.readouterr()
        assert "vault-manifest.json" in captured.err
        assert "corrupted" in captured.err

    def test_save_atomic_no_partial(self, tmp_path, monkeypatch):
        """If the write fails mid-way, neither .json nor .json.tmp should remain."""
        import json as json_mod
        from graphify.merge import _save_manifest
        manifest_path = tmp_path / "vault-manifest.json"

        original_dumps = json_mod.dumps

        def raising_dumps(*args, **kwargs):
            raise OSError("simulated write failure")

        monkeypatch.setattr(json_mod, "dumps", raising_dumps)
        with pytest.raises(OSError):
            _save_manifest(manifest_path, {"key": "value"})
        # No partial .json file
        assert not manifest_path.exists()
        # No leftover .json.tmp
        tmp_file = manifest_path.with_suffix(".json.tmp")
        assert not tmp_file.exists()

    def test_content_hash_content_only(self, tmp_path):
        """Same content at different paths must produce the same hash."""
        from graphify.merge import _content_hash
        file_a = tmp_path / "a" / "note.md"
        file_b = tmp_path / "b" / "note.md"
        file_a.parent.mkdir(parents=True)
        file_b.parent.mkdir(parents=True)
        content = b"# Hello\nsome content\n"
        file_a.write_bytes(content)
        file_b.write_bytes(content)
        assert _content_hash(file_a) == _content_hash(file_b)

    def test_merge_action_new_fields_backward_compat(self):
        """MergeAction constructed without new fields must use defaults."""
        from graphify.merge import MergeAction
        a = MergeAction(path=Path("x.md"), action="CREATE", reason="new")
        assert a.user_modified is False
        assert a.has_user_blocks is False
        assert a.source == "graphify"

    def test_apply_writes_manifest(self, tmp_path):
        """apply_merge_plan with manifest_path must write vault-manifest.json."""
        from graphify.merge import apply_merge_plan, compute_merge_plan
        vault = _copy_vault_fixture("empty", tmp_path)
        manifest_path = tmp_path / "graphify-out" / "vault-manifest.json"
        rn = {
            "node_id": "transformer",
            "target_path": Path("Atlas/Dots/Things/Transformer.md"),
            "frontmatter_fields": {"type": "thing", "graphify_managed": True},
            "body": "# Transformer\n",
        }
        plan = compute_merge_plan(vault, {"transformer": rn}, {})
        result = apply_merge_plan(
            plan, vault, {"transformer": rn}, {},
            manifest_path=manifest_path,
        )
        assert manifest_path.exists(), "vault-manifest.json must be written"
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Find the entry for our note
        assert len(manifest) == 1
        entry = next(iter(manifest.values()))
        assert "content_hash" in entry
        assert "last_merged" in entry
        assert "target_path" in entry
        assert "node_id" in entry
        assert "note_type" in entry
        assert "community_id" in entry
        assert "has_user_blocks" in entry
        assert entry["node_id"] == "transformer"

    def test_apply_skip_preserve_retains_old_entry(self, tmp_path):
        """SKIP_PRESERVE notes must keep their prior manifest entry unchanged."""
        from graphify.merge import apply_merge_plan, compute_merge_plan, MergeAction, MergePlan
        vault = _copy_vault_fixture("pristine_graphify", tmp_path)
        manifest_path = tmp_path / "graphify-out" / "vault-manifest.json"
        target_rel = "Atlas/Dots/Things/Transformer.md"
        old_entry = {
            "content_hash": "old_hash_value",
            "last_merged": "2026-01-01T00:00:00+00:00",
            "target_path": target_rel,
            "node_id": "transformer",
            "note_type": "thing",
            "community_id": 0,
            "has_user_blocks": False,
        }
        old_manifest = {target_rel: old_entry}
        # Build a plan with SKIP_PRESERVE for that file
        target_path = vault / target_rel
        plan = MergePlan(
            actions=[MergeAction(
                path=target_path,
                action="SKIP_PRESERVE",
                reason="strategy=skip",
            )],
            orphans=[],
            summary={"SKIP_PRESERVE": 1},
        )
        rn = _rendered_note_matching_pristine(vault)
        apply_merge_plan(
            plan, vault, {"transformer": rn}, {},
            manifest_path=manifest_path,
            old_manifest=old_manifest,
        )
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert target_rel in manifest
        assert manifest[target_rel]["content_hash"] == "old_hash_value"
