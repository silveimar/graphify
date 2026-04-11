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
# classify() — D-47 precedence pipeline (per-node half; Plan 02 adds
# community assembly)
# ---------------------------------------------------------------------------

def classify(
    G: nx.Graph,
    communities: dict[int, list[str]],
    profile: dict,
    *,
    cohesion: dict[int, float] | None = None,
) -> MappingResult:
    """Classify every real node into a ClassificationContext.

    Precedence pipeline (D-47):
        1. Explicit mapping_rules — first-match-wins
        2. Built-in topology fallback — god node → thing
        3. Default — statement

    Global filters (D-50, D-51):
        - concept nodes: always skipped
        - file-hub nodes: skipped UNLESS explicit `{topology: is_source_file}`
          rule matches (opt-in)

    Community-level fields (community_tag, members_by_type, sibling_labels,
    parent_moc_label, community_name) are left blank in this plan — Plan 02's
    community assembly pass populates them.
    """
    from graphify.cluster import score_all

    folder_mapping = profile.get("folder_mapping") or {}
    top_n = (
        profile.get("topology", {})
        .get("god_node", {})
        .get("top_n", 10)
    )
    raw_rules = profile.get("mapping_rules") or []
    compiled_rules = compile_rules(raw_rules)

    if cohesion is None:
        cohesion = score_all(G, communities)

    node_to_community = _node_community_map(communities)
    community_sizes = {cid: len(members) for cid, members in communities.items()}
    god_list = god_nodes(G, top_n=top_n)
    god_ids = frozenset(g["id"] for g in god_list)

    ctx = _MatchCtx(
        node_to_community=node_to_community,
        community_sizes=community_sizes,
        cohesion=cohesion,
        god_node_ids=god_ids,
    )

    per_node: dict[str, ClassificationContext] = {}
    skipped: set[str] = set()
    traces: list[RuleTrace] = []

    # Deterministic ordering: by (community_id, node_id). Nodes in G but not
    # in communities get classified too (sentinel community id -1).
    ordered_nodes: list[tuple[int, str]] = sorted(
        (cid, n)
        for cid, members in communities.items()
        for n in members
    )
    uncovered = sorted(n for n in G.nodes if n not in node_to_community)
    ordered_nodes.extend((-1, n) for n in uncovered)

    for _cid, node_id in ordered_nodes:
        # (1) Unconditional concept skip (D-50/D-51).
        if _is_concept_node(G, node_id):
            skipped.add(node_id)
            continue

        is_file_hub = _is_file_node(G, node_id)
        matched_rule: tuple[int, dict, dict] | None = None
        for idx, rule in enumerate(compiled_rules):
            when = rule.get("when") or {}
            then = rule.get("then") or {}
            if _match_when(when, node_id, G, ctx=ctx):
                matched_rule = (idx, when, then)
                break

        # (2) File-hub opt-in: only surfaces when the matching rule was
        #     {topology: is_source_file} (D-51). Otherwise skip the hub.
        if is_file_hub:
            if matched_rule is None or matched_rule[1].get("topology") != "is_source_file":
                skipped.add(node_id)
                continue

        if matched_rule is not None:
            idx, when, then = matched_rule
            note_type = then.get("note_type", "statement")
            if note_type not in _NOTE_TYPES:
                note_type = "statement"
            then_folder = then.get("folder")
            folder = _resolve_folder(note_type, then_folder, folder_mapping)
            traces.append(
                RuleTrace(
                    node_id=node_id,
                    rule_index=idx,
                    when_expr=dict(when),
                    matched_kind=_kind_of(when),
                )
            )
        else:
            # (3) Built-in topology fallback — god node → thing, else statement.
            if node_id in god_ids:
                note_type = "thing"
            else:
                note_type = "statement"
            folder = _resolve_folder(note_type, None, folder_mapping)

        per_node[node_id] = ClassificationContext(
            note_type=note_type,
            folder=folder,
            members_by_type={},
            sub_communities=[],
            sibling_labels=[],
        )

    per_community = _assemble_communities(
        G,
        communities,
        per_node,
        skipped,
        profile,
        cohesion,
        ctx.god_node_ids,
    )

    return MappingResult(
        per_node=per_node,
        per_community=per_community,
        skipped_node_ids=skipped,
        rule_traces=traces,
    )


# ---------------------------------------------------------------------------
# Community-level derivations (Plan 02)
# ---------------------------------------------------------------------------


def _derive_community_label(G: nx.Graph, members: list[str], cid: int) -> str:
    """D-58: community label = top-god-node-in-community label.

    Ranks members by G.degree() descending, skipping file-hub and concept
    nodes. Returns the label of the highest-degree real node. If every
    member is synthetic, falls back to ``f"Community {cid}"``.
    """
    ranked = sorted(
        (m for m in members if not _is_file_node(G, m) and not _is_concept_node(G, m)),
        key=lambda m: (-G.degree(m), m),
    )
    if not ranked:
        return f"Community {cid}"
    top = ranked[0]
    return str(G.nodes[top].get("label", top))


def _build_sibling_labels(
    G: nx.Graph,
    community_members: list[str],
    current_node_id: str,
    god_node_ids: frozenset[str] | set[str],
    *,
    cap: int = 5,
) -> list[str]:
    """D-60: ``sibling_labels`` = up to ``cap`` **god-node** labels in the
    community sorted by ``G.degree()`` descending, excluding the current node.

    ``god_node_ids`` is the set computed once in ``classify()`` from
    ``analyze.god_nodes(G, top_n)``. Only community members that are god
    nodes are eligible — D-60 explicitly states non-god nodes get
    ``sibling_labels: []`` and must never be returned here. File-hub and
    concept (synthetic) nodes are also filtered.
    """
    ranked = sorted(
        (
            m
            for m in community_members
            if m != current_node_id
            and m in god_node_ids
            and not _is_file_node(G, m)
            and not _is_concept_node(G, m)
        ),
        key=lambda m: (-G.degree(m), m),
    )
    return [str(G.nodes[m].get("label", m)) for m in ranked[:cap]]


def _inter_community_edges(
    G: nx.Graph,
    node_to_community: dict[str, int],
) -> dict[tuple[int, int], int]:
    """Single-pass walk producing symmetric inter-community edge counts.

    Keys are ``(min(cid_u, cid_v), max(cid_u, cid_v))``. Intra-community
    edges (``cid_u == cid_v``) are ignored. Nodes not in
    ``node_to_community`` are ignored.
    """
    counts: dict[tuple[int, int], int] = {}
    for u, v in G.edges():
        cu = node_to_community.get(u)
        cv = node_to_community.get(v)
        if cu is None or cv is None or cu == cv:
            continue
        key = (min(cu, cv), max(cu, cv))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _nearest_host(
    below_cid: int,
    above_cids: list[int],
    inter_edges: dict[tuple[int, int], int],
    community_sizes: dict[int, int],
) -> int | None:
    """D-53: return the above-threshold cid with the most inter-community
    edges to ``below_cid``.

    Tie-break order: largest community first (``community_sizes`` desc),
    then lowest cid ascending. Returns ``None`` when zero inter-community
    edges exist to any above cid (caller falls back to bucket MOC).
    """
    best_cid: int | None = None
    best_count = 0
    best_size = -1
    for host_cid in above_cids:
        key = (min(below_cid, host_cid), max(below_cid, host_cid))
        count = inter_edges.get(key, 0)
        if count == 0:
            continue
        size = community_sizes.get(host_cid, 0)
        take = False
        if count > best_count:
            take = True
        elif count == best_count and size > best_size:
            take = True
        elif (
            count == best_count
            and size == best_size
            and (best_cid is None or host_cid < best_cid)
        ):
            take = True
        if take:
            best_count = count
            best_size = size
            best_cid = host_cid
    return best_cid


def _assemble_communities(
    G: nx.Graph,
    communities: dict[int, list[str]],
    per_node: dict[str, ClassificationContext],
    skipped_node_ids: set[str],
    profile: dict,
    cohesion: dict[int, float],
    god_node_ids: frozenset[str],
) -> dict[int, ClassificationContext]:
    """D-52..D-60: derive per-community ClassificationContext entries.

    Builds a per_community dict keyed by community id, and mutates every
    per_node entry to fill community_tag / parent_moc_label /
    community_name / sibling_labels.

    Logic:
      1. Communities with ``len(members) >= moc_threshold`` become MOC
         entries (note_type="moc").
      2. Below-threshold communities are routed to the nearest host via
         ``_nearest_host`` (D-53 arg-max by inter-community edge count).
      3. Below-threshold communities with no host edges collapse into a
         synthetic ``per_community[-1]`` Uncategorized bucket MOC (D-56).
      4. Non-MOC per_node entries receive their host MOC's
         community_name / tag / parent_moc_label. ``sibling_labels`` is
         populated only for god nodes (D-60 BLOCKER fidelity fix) and is
         ``[]`` for every other node.
    """
    from graphify.profile import safe_tag

    folder_mapping = profile.get("folder_mapping") or {}
    moc_folder = folder_mapping.get("moc") or folder_mapping.get(
        "default", "Atlas/Maps/"
    )

    # Defensive threshold parse — belt-and-suspenders with Plan 03's
    # validate_rules. Explicitly reject bool (bool is a subclass of int).
    raw_threshold = profile.get("mapping", {}).get("moc_threshold", 3)
    if isinstance(raw_threshold, bool) or not isinstance(raw_threshold, int):
        threshold = 3
    else:
        threshold = raw_threshold

    node_to_community = _node_community_map(communities)
    community_sizes = {cid: len(members) for cid, members in communities.items()}

    above_cids = sorted(
        cid for cid, members in communities.items() if len(members) >= threshold
    )
    below_cids = sorted(
        cid for cid, members in communities.items() if len(members) < threshold
    )

    labels: dict[int, str] = {
        cid: _derive_community_label(G, communities[cid], cid)
        for cid in communities
    }

    inter_edges = _inter_community_edges(G, node_to_community)

    per_community: dict[int, ClassificationContext] = {}

    # --- Above-threshold: one MOC per community -----------------------------
    for cid in above_cids:
        name = labels[cid]
        tag = safe_tag(name)
        per_community[cid] = ClassificationContext(
            note_type="moc",
            folder=moc_folder,
            community_name=name,
            parent_moc_label=name,  # MOC is its own anchor for Phase 2 fallback
            community_tag=tag,
            members_by_type={"thing": [], "statement": [], "person": [], "source": []},
            sub_communities=[],
            sibling_labels=[],
            # W-2 fix: populate cohesion so templates.py:705-706 renders a
            # real value. Wrap with float() per WR-06 to coerce numpy scalars.
            cohesion=float(cohesion.get(cid, 0.0)) if cohesion else 0.0,
        )

    # Sibling labels across MOCs: top 5 other MOC names by community size desc.
    size_sorted_above = sorted(above_cids, key=lambda c: (-community_sizes[c], c))
    for cid in above_cids:
        siblings = [labels[other] for other in size_sorted_above if other != cid][:5]
        per_community[cid]["sibling_labels"] = siblings

    # --- Below-threshold: resolve hosts or route to bucket ------------------
    hostless_below: list[int] = []
    below_to_host: dict[int, int] = {}
    for below_cid in below_cids:
        host = _nearest_host(below_cid, above_cids, inter_edges, community_sizes)
        if host is None:
            hostless_below.append(below_cid)
        else:
            below_to_host[below_cid] = host

    # --- Synthesize bucket MOC only when needed (D-56) ----------------------
    bucket_needed = bool(hostless_below) or (not above_cids and bool(below_cids))
    if bucket_needed:
        per_community[-1] = ClassificationContext(
            note_type="moc",
            folder=moc_folder,
            community_name="Uncategorized",
            parent_moc_label="Uncategorized",
            community_tag="uncategorized",
            members_by_type={"thing": [], "statement": [], "person": [], "source": []},
            sub_communities=[],
            sibling_labels=[],
            # Bucket MOC has no real community to score — 0.0 sentinel.
            cohesion=0.0,
        )
        if not above_cids:
            # Tiny-corpus edge case: ALL communities are below threshold.
            for cid in below_cids:
                below_to_host[cid] = -1
        else:
            for cid in hostless_below:
                below_to_host[cid] = -1

    # --- Fill sub_communities for host MOCs ---------------------------------
    # Iterate below_to_host in ascending below_cid order so sub_communities
    # is emitted deterministically (RESEARCH Q5 RESOLVED).
    for below_cid in sorted(below_to_host):
        host_cid = below_to_host[below_cid]
        sub_label = labels[below_cid]
        member_dicts: list[dict] = []
        for m in communities[below_cid]:
            if m in skipped_node_ids:
                continue
            ctx_m = per_node.get(m)
            if ctx_m is None:
                continue
            member_dicts.append(
                {
                    "label": G.nodes[m].get("label", m),
                    "note_type": ctx_m.get("note_type", "statement"),
                }
            )
        if member_dicts:
            per_community[host_cid]["sub_communities"].append(
                {
                    "label": sub_label,
                    "members": member_dicts,
                    # Internal key used only for deterministic ordering.
                    # ClassificationContext TypedDict is total=False so Phase 2
                    # consumers reading via .get() ignore unknown keys.
                    "_source_cid": below_cid,
                }
            )

    # --- members_by_type for MOCs (above-threshold only; below members
    #     live in sub_communities) ------------------------------------------
    for cid in above_cids:
        for m in communities[cid]:
            if m in skipped_node_ids:
                continue
            ctx_m = per_node.get(m)
            if ctx_m is None:
                continue
            nt = ctx_m.get("note_type", "statement")
            if nt == "moc":
                continue
            group = per_community[cid]["members_by_type"].setdefault(nt, [])
            group.append({"label": G.nodes[m].get("label", m)})

    # --- Enrich per_node entries with community fields ---------------------
    for node_id, ctx_entry in per_node.items():
        cid = node_to_community.get(node_id)
        if cid is None:
            continue
        if cid in above_cids:
            host_cid: int | None = cid
        else:
            host_cid = below_to_host.get(cid)
        if host_cid is None or host_cid not in per_community:
            continue
        host_entry = per_community[host_cid]
        host_name = host_entry["community_name"]
        host_tag = host_entry["community_tag"]
        ctx_entry["community_name"] = host_name
        ctx_entry["parent_moc_label"] = host_name
        ctx_entry["community_tag"] = host_tag
        # BLOCKER 1 (D-60 fidelity): sibling_labels only for god nodes.
        # Non-god nodes MUST receive [] — D-60 is explicit.
        if node_id in god_node_ids:
            ctx_entry["sibling_labels"] = _build_sibling_labels(
                G, communities[cid], node_id, god_node_ids, cap=5,
            )
        else:
            ctx_entry["sibling_labels"] = []

    return per_community


def _kind_of(when: dict) -> str:
    """Return a short string identifying which matcher kind a `when` clause uses."""
    if "attr" in when:
        for op in ("equals", "in", "contains", "regex"):
            if op in when:
                return f"attr:{op}"
        return "attr:?"
    if "topology" in when:
        return f"topology:{when['topology']}"
    if "source_file_ext" in when:
        return "source_file_ext"
    if "source_file_matches" in when:
        return "source_file_matches"
    return "unknown"


def validate_rules(rules: list) -> list[str]:  # pragma: no cover
    raise NotImplementedError("validate_rules() lands in Plan 03")
