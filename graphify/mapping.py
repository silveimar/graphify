"""Mapping engine: pure classification of graph nodes into note types and folders."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

import networkx as nx

from graphify.analyze import (
    _is_concept_node,
    _is_file_node,
    _node_community_map,
    god_nodes,
)
from graphify.templates import ClassificationContext, _NOTE_TYPES


# ---------------------------------------------------------------------------
# Module-level constants (D-44 length caps; mirrors security.py style)
# ---------------------------------------------------------------------------

_MAX_PATTERN_LEN = 512
_MAX_CANDIDATE_LEN = 2048

_VALID_ATTR_OPS = frozenset({"equals", "in", "contains", "regex"})
_VALID_TOPOLOGY_KINDS = frozenset({
    "god_node",
    "community_size_gte",
    "community_size_lt",
    "cohesion_gte",
    "is_source_file",
})
_COMPILED_KEY = "_compiled_pattern"


# ---------------------------------------------------------------------------
# Result / trace shapes (D-47 precedence pipeline output)
# ---------------------------------------------------------------------------


class RuleTrace(TypedDict, total=False):
    node_id: str
    rule_index: int
    when_expr: dict
    matched_kind: str


class MappingResult(TypedDict, total=False):
    per_node: dict[str, ClassificationContext]
    per_community: dict[int, ClassificationContext]
    skipped_node_ids: set[str]
    rule_traces: list[RuleTrace]


@dataclass(frozen=True)
class _MatchCtx:
    """Per-classify() scratch cache passed into _match_when."""
    node_to_community: dict[str, int]
    community_sizes: dict[int, int]
    cohesion: dict[int, float]
    god_node_ids: frozenset[str]


# ---------------------------------------------------------------------------
# Rule compilation (D-44: fail-fast regex compile at profile-load time)
# ---------------------------------------------------------------------------

def compile_rules(rules: list) -> list[dict]:
    """Pre-compile regex patterns in rules. Raises ValueError on re.error.

    Deep-copies each rule so the caller's input is not mutated. Stores the
    compiled re.Pattern under the private key `_compiled_pattern` on the
    when-dict. Called at profile-load time so malformed patterns fail fast.
    Shape errors (missing when/then, bad keys) are validate_rules' job — this
    function is a no-op for non-dict entries and tolerates missing keys.
    """
    out: list[dict] = []
    for idx, rule in enumerate(rules or []):
        if not isinstance(rule, dict):
            out.append(rule)
            continue
        when = rule.get("when")
        then = rule.get("then")
        new_when = dict(when) if isinstance(when, dict) else when
        if isinstance(when, dict):
            # attr+regex compound matcher
            if "attr" in when and "regex" in when:
                pat = when["regex"]
                if isinstance(pat, str) and len(pat) <= _MAX_PATTERN_LEN:
                    try:
                        new_when[_COMPILED_KEY] = re.compile(pat)
                    except re.error as exc:
                        raise ValueError(
                            f"mapping_rules[{idx}].when.regex: {exc}"
                        ) from exc
            # top-level source_file_matches
            if "source_file_matches" in when:
                pat = when["source_file_matches"]
                if isinstance(pat, str) and len(pat) <= _MAX_PATTERN_LEN:
                    try:
                        new_when[_COMPILED_KEY] = re.compile(pat)
                    except re.error as exc:
                        raise ValueError(
                            f"mapping_rules[{idx}].when.source_file_matches: {exc}"
                        ) from exc
        out.append({"when": new_when, "then": then})
    return out


# ---------------------------------------------------------------------------
# Matcher dispatch (D-44: 11 matcher kinds; returns False, never raises)
# ---------------------------------------------------------------------------

def _match_when(when: dict, node_id: str, G: nx.Graph, *, ctx: _MatchCtx) -> bool:
    """Dispatch on the matcher kind present in `when`. Returns True iff matched.

    Non-string attribute values fed to string ops (contains/regex) return
    False, never raise (D-44, threat T-3-04 "non-string attr crash").
    Candidate strings longer than _MAX_CANDIDATE_LEN return False for
    regex matchers (threat T-3-01 "ReDoS via long input").
    """
    if not isinstance(when, dict):
        return False
    attrs = G.nodes[node_id]

    # --- Attribute matchers ---------------------------------------------
    if "attr" in when:
        key = when["attr"]
        if key not in attrs:
            return False
        raw = attrs[key]
        if "equals" in when:
            return raw == when["equals"]
        if "in" in when:
            choices = when["in"]
            return isinstance(choices, (list, tuple, set)) and raw in choices
        if "contains" in when:
            needle = when["contains"]
            if not isinstance(raw, str) or not isinstance(needle, str):
                return False
            return needle in raw
        if "regex" in when:
            if not isinstance(raw, str):
                return False
            if len(raw) > _MAX_CANDIDATE_LEN:
                return False
            pat = when.get(_COMPILED_KEY)
            if pat is None:
                return False
            return pat.fullmatch(raw) is not None
        return False

    # --- Topology matchers ----------------------------------------------
    if "topology" in when:
        kind = when["topology"]
        if kind == "god_node":
            return node_id in ctx.god_node_ids
        if kind == "is_source_file":
            return _is_file_node(G, node_id)
        cid = ctx.node_to_community.get(node_id)
        if cid is None:
            return False
        if kind == "community_size_gte":
            value = when.get("value")
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
                and ctx.community_sizes.get(cid, 0) >= value
            )
        if kind == "community_size_lt":
            value = when.get("value")
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
                and ctx.community_sizes.get(cid, 0) < value
            )
        if kind == "cohesion_gte":
            value = when.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False
            return ctx.cohesion.get(cid, 0.0) >= float(value)
        return False

    # --- source_file_ext ------------------------------------------------
    if "source_file_ext" in when:
        ext_spec = when["source_file_ext"]
        source_file = attrs.get("source_file") or ""
        if not isinstance(source_file, str) or not source_file:
            return False
        node_ext = _norm_ext_from_path(source_file)
        if isinstance(ext_spec, str):
            return node_ext == _norm_ext(ext_spec)
        if isinstance(ext_spec, (list, tuple)):
            return node_ext in {_norm_ext(e) for e in ext_spec if isinstance(e, str)}
        return False

    # --- source_file_matches (regex) ------------------------------------
    if "source_file_matches" in when:
        source_file = attrs.get("source_file") or ""
        if not isinstance(source_file, str) or len(source_file) > _MAX_CANDIDATE_LEN:
            return False
        pat = when.get(_COMPILED_KEY)
        if pat is None:
            return False
        return pat.fullmatch(source_file) is not None

    return False


def _norm_ext(ext: str) -> str:
    """Lowercase and normalize leading dot on an extension spec."""
    ext = ext.lower()
    return ext if ext.startswith(".") else f".{ext}"


def _norm_ext_from_path(path: str) -> str:
    """Extract the lowercase file extension (including leading dot) from a path."""
    base = path.rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    return "." + base.rsplit(".", 1)[-1].lower()


# ---------------------------------------------------------------------------
# Folder resolution (D-46: per-rule override falls back to folder_mapping)
# ---------------------------------------------------------------------------

def _resolve_folder(
    note_type: str,
    then_folder: str | None,
    folder_mapping: dict,
) -> str:
    """Return the per-rule folder override, falling back to folder_mapping."""
    if isinstance(then_folder, str) and then_folder:
        return then_folder
    return folder_mapping.get(note_type) or folder_mapping.get("default", "Atlas/Dots/")


# ---------------------------------------------------------------------------
# classify() — stubbed here; implementation lands in Task 3
# ---------------------------------------------------------------------------

def classify(G, communities, profile, *, cohesion=None):  # pragma: no cover
    raise NotImplementedError("classify() lands in Task 3")


def validate_rules(rules: list) -> list[str]:  # pragma: no cover
    raise NotImplementedError("validate_rules() lands in Plan 03")
