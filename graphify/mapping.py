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


def _join_taxonomy_folder(root: str, folder: str) -> str:
    """Join taxonomy root/folder into a normalized vault-relative folder."""
    text = "/".join(
        segment.strip("/")
        for segment in (root, folder)
        if segment.strip("/")
    )
    return f"{text}/" if text else ""


def _effective_folder_mapping(profile: dict) -> dict:
    """Return folder mappings with taxonomy taking precedence when present."""
    folder_mapping = dict(profile.get("folder_mapping") or {})
    taxonomy = profile.get("taxonomy")
    if not isinstance(taxonomy, dict):
        return folder_mapping

    root = taxonomy.get("root")
    folders = taxonomy.get("folders")
    if not isinstance(root, str) or not isinstance(folders, dict):
        return folder_mapping

    for key in (
        "moc", "thing", "statement", "person", "source", "default",
        "unclassified",
    ):
        folder = folders.get(key)
        if isinstance(folder, str) and folder:
            folder_mapping[key] = _join_taxonomy_folder(root, folder)
    return folder_mapping


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

    folder_mapping = _effective_folder_mapping(profile)
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
      1. Communities with ``len(members) >= min_community_size`` become MOC
         entries (note_type="moc").
      2. Below-threshold communities are routed to the nearest host via
         ``_nearest_host`` (D-53 arg-max by inter-community edge count).
      3. Below-threshold communities with no host edges collapse into a
         synthetic ``per_community[-1]`` _Unclassified bucket MOC (D-56).
      4. Non-MOC per_node entries receive their host MOC's
         community_name / tag / parent_moc_label. ``sibling_labels`` is
         populated only for god nodes (D-60 BLOCKER fidelity fix) and is
         ``[]`` for every other node.
    """
    from graphify.profile import safe_tag

    folder_mapping = _effective_folder_mapping(profile)
    moc_folder = folder_mapping.get("moc") or folder_mapping.get(
        "default", "Atlas/Maps/"
    )
    unclassified_folder = folder_mapping.get("unclassified") or moc_folder

    # Defensive threshold parse — belt-and-suspenders with profile validation.
    # Explicitly reject bool (bool is a subclass of int).
    raw_threshold = profile.get("mapping", {}).get("min_community_size", 3)
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
        bucket_name = "_Unclassified"
        per_community[-1] = ClassificationContext(
            note_type="moc",
            folder=unclassified_folder,
            community_name=bucket_name,
            parent_moc_label=bucket_name,
            community_tag=safe_tag(bucket_name),
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


# ---------------------------------------------------------------------------
# Rule validation (D-44, D-45, D-47) — Plan 03
# ---------------------------------------------------------------------------


def validate_rules(rules: list) -> list[str]:
    """Validate mapping_rules shape and contents. Returns a list of error
    strings — empty means valid. Never raises.

    Covers:
      - Rule shape: dict with `when` + `then`, both dicts
      - Matcher kinds: exactly one of attr/topology/source_file_ext/source_file_matches
      - attr operators: exactly one of equals/in/contains/regex
      - Regex safety: pattern length ≤ _MAX_PATTERN_LEN, compiles via re.compile
      - then.note_type in _NOTE_TYPES (whitelisted)
      - then.folder path safety: no `..`, no absolute, no leading `~`
      - Topology value type: int (not bool) for size thresholds; int|float for cohesion
      - Unknown `then:` keys rejected (D-46; WARNING 1 fix)
      - Dead-rule detection: appended as warnings after per-rule errors
    """
    errors: list[str] = []
    if rules is None:
        return errors
    if not isinstance(rules, list):
        errors.append("'mapping_rules' must be a list")
        return errors

    for idx, rule in enumerate(rules):
        prefix = f"mapping_rules[{idx}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix}: must be a mapping (dict)")
            continue
        when = rule.get("when")
        then = rule.get("then")
        if not isinstance(when, dict):
            errors.append(f"{prefix}.when: must be a mapping (dict)")
        if not isinstance(then, dict):
            errors.append(f"{prefix}.then: must be a mapping (dict)")
        if not isinstance(when, dict) or not isinstance(then, dict):
            continue

        # --- when: exactly one matcher kind ----------------------------
        matcher_keys = [
            k for k in ("attr", "topology", "source_file_ext", "source_file_matches")
            if k in when
        ]
        if len(matcher_keys) == 0:
            errors.append(
                f"{prefix}.when: must contain exactly one of "
                "'attr', 'topology', 'source_file_ext', 'source_file_matches'"
            )
            # Still validate then fields so users see all problems at once.
        elif len(matcher_keys) > 1:
            errors.append(
                f"{prefix}.when: contains multiple matcher kinds {matcher_keys} — "
                "each rule may use only one matcher kind"
            )
        else:
            kind = matcher_keys[0]
            errors.extend(_validate_when_kind(kind, when, prefix))

        # --- then.note_type (required) ---------------------------------
        note_type = then.get("note_type")
        if note_type is None:
            errors.append(f"{prefix}.then.note_type: required")
        elif note_type not in _NOTE_TYPES:
            errors.append(
                f"{prefix}.then.note_type: {note_type!r} not in {sorted(_NOTE_TYPES)}"
            )

        # --- then.folder (optional, path-safety) -----------------------
        folder = then.get("folder")
        if folder is not None:
            errors.extend(_validate_folder(folder, f"{prefix}.then.folder"))

        # --- then: reject unknown keys (D-46 — WARNING 1 fix) ----------
        # D-46: `then:` supports ONLY `note_type` and `folder`. Any other
        # key is a user error we must surface — silently dropping them
        # would let users believe tags/up/etc. were applied.
        extra_keys = set(then) - {"note_type", "folder"}
        if extra_keys:
            errors.append(
                f"{prefix}.then: unknown keys {sorted(extra_keys)} — "
                "only 'note_type' and 'folder' are supported (D-46)"
            )

    # Append dead-rule warnings only when no per-rule errors blocked them.
    # Shape errors above mean the pairwise heuristic could read nonsense.
    if not errors:
        errors.extend(_detect_dead_rules(rules))
    return errors


def _validate_when_kind(kind: str, when: dict, prefix: str) -> list[str]:
    """Dispatch to kind-specific validator. Returns list of error strings."""
    if kind == "attr":
        return _validate_attr_when(when, prefix)
    if kind == "topology":
        return _validate_topology_when(when, prefix)
    if kind == "source_file_ext":
        return _validate_source_file_ext_when(when, prefix)
    if kind == "source_file_matches":
        return _validate_source_file_matches_when(when, prefix)
    return [f"{prefix}.when: unknown matcher kind {kind!r}"]


def _validate_attr_when(when: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    key = when.get("attr")
    if not isinstance(key, str) or not key:
        errors.append(f"{prefix}.when.attr: must be a non-empty string")
    ops = [op for op in ("equals", "in", "contains", "regex") if op in when]
    if len(ops) == 0:
        errors.append(
            f"{prefix}.when: attr matcher requires one of "
            "'equals', 'in', 'contains', 'regex'"
        )
        return errors
    if len(ops) > 1:
        errors.append(
            f"{prefix}.when: attr matcher may use only one operator, got {ops}"
        )
        return errors
    op = ops[0]
    if op == "in" and not isinstance(when["in"], (list, tuple)):
        errors.append(f"{prefix}.when.in: must be a list")
    if op == "contains" and not isinstance(when["contains"], str):
        errors.append(f"{prefix}.when.contains: must be a string")
    if op == "regex":
        pat = when["regex"]
        if not isinstance(pat, str):
            errors.append(f"{prefix}.when.regex: must be a string")
        elif len(pat) > _MAX_PATTERN_LEN:
            errors.append(
                f"{prefix}.when.regex: pattern length {len(pat)} exceeds cap "
                f"{_MAX_PATTERN_LEN} (ReDoS mitigation)"
            )
        else:
            try:
                re.compile(pat)
            except re.error as exc:
                errors.append(f"{prefix}.when.regex: {exc}")
    return errors


def _validate_topology_when(when: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    kind = when.get("topology")
    if kind not in _VALID_TOPOLOGY_KINDS:
        errors.append(
            f"{prefix}.when.topology: {kind!r} not in {sorted(_VALID_TOPOLOGY_KINDS)}"
        )
        return errors
    if kind in ("community_size_gte", "community_size_lt"):
        value = when.get("value")
        # bool-before-int guard (T-3-03) — bool is a subclass of int in Python.
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(
                f"{prefix}.when.value: must be an integer (got {type(value).__name__})"
            )
    elif kind == "cohesion_gte":
        value = when.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(
                f"{prefix}.when.value: must be a number (got {type(value).__name__})"
            )
        elif not (0.0 <= float(value) <= 1.0):
            errors.append(
                f"{prefix}.when.value: must be in [0.0, 1.0] (got {value})"
            )
    return errors


def _validate_source_file_ext_when(when: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    val = when.get("source_file_ext")
    if isinstance(val, str):
        if not val.startswith("."):
            errors.append(
                f"{prefix}.when.source_file_ext: must start with '.' (got {val!r})"
            )
    elif isinstance(val, list):
        for i, item in enumerate(val):
            if not isinstance(item, str) or not item.startswith("."):
                errors.append(
                    f"{prefix}.when.source_file_ext[{i}]: must be a string starting with '.'"
                )
    else:
        errors.append(
            f"{prefix}.when.source_file_ext: must be a string or list of strings"
        )
    return errors


def _validate_source_file_matches_when(when: dict, prefix: str) -> list[str]:
    errors: list[str] = []
    pat = when.get("source_file_matches")
    if not isinstance(pat, str):
        errors.append(f"{prefix}.when.source_file_matches: must be a string")
        return errors
    if len(pat) > _MAX_PATTERN_LEN:
        errors.append(
            f"{prefix}.when.source_file_matches: pattern length {len(pat)} exceeds cap "
            f"{_MAX_PATTERN_LEN} (ReDoS mitigation)"
        )
        return errors
    try:
        re.compile(pat)
    except re.error as exc:
        errors.append(f"{prefix}.when.source_file_matches: {exc}")
    return errors


def _validate_folder(folder: object, prefix: str) -> list[str]:
    """Path-safety mirror of profile.py:178-195 for then.folder overrides (T-3-02)."""
    errors: list[str] = []
    if not isinstance(folder, str):
        errors.append(f"{prefix}: must be a string")
        return errors
    if ".." in folder:
        errors.append(
            f"{prefix}: contains '..' — path traversal sequences are not allowed"
        )
    elif folder.startswith("/"):
        errors.append(
            f"{prefix}: is an absolute path — only relative paths are allowed"
        )
    elif folder.startswith("~"):
        errors.append(
            f"{prefix}: starts with '~' — home-relative paths are not allowed"
        )
    return errors


def _detect_dead_rules(rules: list) -> list[str]:
    """D-45 dead-rule detection. Conservative structural heuristic.

    A rule i is dead iff an earlier rule j:
      - has the same matcher kind (attr:<op>, topology:<kind>, source_file_ext)
      - has the same then.note_type
      - has a strict structural superset of rule i's when-clause within that kind

    Warnings are prefixed ``mapping_rules[{i}]: warning: dead rule ...``. Cross-kind
    pairs never trigger (no false positives). attr:contains, attr:regex, and
    source_file_matches are skipped (semantic equivalence undecidable).
    """
    warnings: list[str] = []
    for i in range(1, len(rules)):
        ri = rules[i]
        if not isinstance(ri, dict):
            continue
        wi = ri.get("when") or {}
        ti = ri.get("then") or {}
        if not isinstance(wi, dict) or not isinstance(ti, dict):
            continue
        ki = _kind_of(wi)
        nt_i = ti.get("note_type")
        for j in range(i):
            rj = rules[j]
            if not isinstance(rj, dict):
                continue
            wj = rj.get("when") or {}
            tj = rj.get("then") or {}
            if not isinstance(wj, dict) or not isinstance(tj, dict):
                continue
            if _kind_of(wj) != ki:
                continue
            if tj.get("note_type") != nt_i:
                continue
            if _is_shadowed(ki, wj, wi):
                warnings.append(
                    f"mapping_rules[{i}]: warning: dead rule — "
                    f"shadowed by mapping_rules[{j}]"
                )
                break
    return warnings


def _is_shadowed(kind: str, broad_when: dict, narrow_when: dict) -> bool:
    """Return True if `broad_when` matches everything `narrow_when` matches.

    Conservative: source_file_matches and attr:contains / attr:regex return
    False (semantic equivalence of regex/substring is undecidable). No false
    positives is the contract.
    """
    if kind == "attr:equals":
        return (
            broad_when.get("attr") == narrow_when.get("attr")
            and broad_when.get("equals") == narrow_when.get("equals")
        )
    if kind == "attr:in":
        if broad_when.get("attr") != narrow_when.get("attr"):
            return False
        broad_set = set(broad_when.get("in") or [])
        narrow_set = set(narrow_when.get("in") or [])
        return broad_set.issuperset(narrow_set)
    if kind in ("topology:god_node", "topology:is_source_file"):
        return True  # both are parameterless — earlier wins
    if kind == "topology:community_size_gte":
        bv = broad_when.get("value")
        nv = narrow_when.get("value")
        if not isinstance(bv, int) or not isinstance(nv, int):
            return False
        if isinstance(bv, bool) or isinstance(nv, bool):
            return False
        return bv <= nv
    if kind == "topology:community_size_lt":
        bv = broad_when.get("value")
        nv = narrow_when.get("value")
        if not isinstance(bv, int) or not isinstance(nv, int):
            return False
        if isinstance(bv, bool) or isinstance(nv, bool):
            return False
        return bv >= nv
    if kind == "topology:cohesion_gte":
        bv = broad_when.get("value")
        nv = narrow_when.get("value")
        if not isinstance(bv, (int, float)) or not isinstance(nv, (int, float)):
            return False
        if isinstance(bv, bool) or isinstance(nv, bool):
            return False
        return float(bv) <= float(nv)
    if kind == "source_file_ext":
        def _as_set(v: object) -> set[str]:
            if isinstance(v, str):
                return {v.lower()}
            if isinstance(v, (list, tuple)):
                return {x.lower() for x in v if isinstance(x, str)}
            return set()
        broad_set = _as_set(broad_when.get("source_file_ext"))
        narrow_set = _as_set(narrow_when.get("source_file_ext"))
        if not broad_set or not narrow_set:
            return False
        return broad_set.issuperset(narrow_set)
    # attr:contains, attr:regex, source_file_matches → conservative skip
    return False
