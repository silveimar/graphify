from __future__ import annotations

"""Phase 16 argumentation substrate — zero LLM, pure Python + NetworkX.

Module exports:
    ArgumentPackage, PerspectiveSeed, NodeCitation dataclasses
    populate(G, topic, *, scope, budget, node_ids, community_id, communities)
    validate_turn(turn, G) -> list[str]
    compute_overlap(cite_sets) -> float
    ROUND_CAP = 6
    MAX_TEMPERATURE = 0.4

See .planning/phases/16-graph-argumentation-mode/16-CONTEXT.md D-01..D-10.
ARGUE-03 invariant: this module contains ZERO LLM calls. Enforced by
tests/test_argue.py::test_argue_zero_llm_calls.
"""

from dataclasses import dataclass, field

import networkx as nx


# Phase 16 D-06 / ARGUE-08: hard cap on debate rounds.
ROUND_CAP: int = 6

# Phase 16 D-04: max temperature enforced at skill.md LLM call sites.
MAX_TEMPERATURE: float = 0.4

# Phase 16 D-01: fixed persona roster — reuse of Phase 9 lenses verbatim.
_FIXED_LENSES: list[str] = ["security", "architecture", "complexity", "onboarding"]


@dataclass
class NodeCitation:
    """A single node cited in a persona turn."""

    node_id: str
    label: str
    source_file: str


@dataclass
class PerspectiveSeed:
    """A fixed lens persona for the SPAR-Kit debate."""

    lens: str


@dataclass
class ArgumentPackage:
    """Result of populate() — evidence subgraph + fixed 4-lens perspectives.

    subgraph:    NetworkX subgraph of relevant nodes for the debate topic.
    perspectives: Always 4 PerspectiveSeed items (D-01).
    evidence:    NodeCitation for each node in the subgraph.
    """

    subgraph: nx.Graph
    perspectives: list[PerspectiveSeed] = field(default_factory=list)
    evidence: list[NodeCitation] = field(default_factory=list)


def _default_perspectives() -> list[PerspectiveSeed]:
    """Return the fixed 4-lens PerspectiveSeed roster (D-01)."""
    return [PerspectiveSeed(lens=lens) for lens in _FIXED_LENSES]


def _build_evidence(subG: nx.Graph, G: nx.Graph) -> list[NodeCitation]:
    """Build NodeCitation list from nodes in subG, pulling attrs from G."""
    ev: list[NodeCitation] = []
    for nid in subG.nodes:
        if nid not in G.nodes:
            continue
        attrs = G.nodes[nid]
        ev.append(
            NodeCitation(
                node_id=nid,
                label=attrs.get("label", nid),
                source_file=attrs.get("source_file", ""),
            )
        )
    return ev


def populate(
    G: nx.Graph,
    topic: str,
    *,
    scope: str = "topic",
    budget: int = 2000,
    node_ids: list[str] | None = None,
    community_id: int | None = None,
    communities: dict[int, list[str]] | None = None,
) -> ArgumentPackage:
    """Phase 16 ARGUE-01/02: build evidence subgraph + fixed 4-lens perspectives.

    Silent-ignore on malformed input — returns empty ArgumentPackage, never raises.
    Composes serve.py primitives (_extract_entity_terms, _score_nodes, _bfs);
    no new traversal logic.

    Args:
        G: The full knowledge graph.
        topic: Decision question text (used for scope="topic" seed resolution).
        scope: One of "topic" (default), "subgraph", or "community".
        budget: Max nodes in returned subgraph (clamped to [50, 100000]).
        node_ids: Explicit seed nodes for scope="subgraph".
        community_id: Community integer key for scope="community".
        communities: Dict mapping community_id -> list[node_id]; required for
            scope="community". Passed explicitly to decouple argue.py from
            serve.py internal state (A2 recommendation from 16-RESEARCH.md).

    Returns:
        ArgumentPackage with subgraph, 4 fixed perspectives, and evidence list.
        Empty ArgumentPackage (no nodes, no perspectives) on malformed input.
    """
    # Budget clamp — identical to >=6 MCP tool cores in serve.py.
    budget = max(50, min(int(budget), 100000))

    empty_pkg = ArgumentPackage(
        subgraph=G.__class__(),
        perspectives=[],
        evidence=[],
    )

    # Silent-ignore malformed topic for scope="topic" only; subgraph/community
    # scopes may have empty topic.
    if scope == "topic" and (not isinstance(topic, str) or not topic.strip()):
        return empty_pkg

    # Local import avoids circular module load at import time.
    from graphify.serve import _bfs, _extract_entity_terms, _score_nodes

    seed_ids: list[str] = []
    if scope == "subgraph":
        # Drop unknown IDs silently — no echo (Pitfall 6).
        seed_ids = [nid for nid in (node_ids or []) if nid in G.nodes]
    elif scope == "community":
        members: list[str] = []
        if community_id is not None:
            members = (communities or {}).get(community_id, [])
        seed_ids = [nid for nid in members if nid in G.nodes]
    else:
        # Default scope="topic": tokenize + score + BFS seeds.
        terms = _extract_entity_terms(topic)
        if not terms:
            return empty_pkg
        scored = _score_nodes(G, terms)
        seed_ids = [nid for _, nid in scored[:5] if nid in G.nodes]

    if not seed_ids:
        return empty_pkg

    visited, _edges = _bfs(G, seed_ids, depth=2)
    nodes_list = list(visited)[:budget]
    subG = G.subgraph(nodes_list).copy()

    return ArgumentPackage(
        subgraph=subG,
        perspectives=_default_perspectives(),
        evidence=_build_evidence(subG, G),
    )


def validate_turn(turn: dict, G: nx.Graph) -> list[str]:
    """Phase 16 ARGUE-05 D-08/D-10: return node_ids in turn['cites'] not in G.nodes.

    Empty return = valid turn. Zero LLM calls. Operates on atomic cite list,
    not claim prose (D-10 — no partial stripping of claim text).

    Args:
        turn: Dict with optional 'cites' key containing list of node_id strings.
        G: The knowledge graph to validate against.

    Returns:
        List of unknown node_id strings. Empty list means the turn is valid.
    """
    return [nid for nid in turn.get("cites", []) if nid not in G.nodes]


def compute_overlap(cite_sets: list[set[str]]) -> float:
    """Phase 16 ARGUE-08 D-06: Jaccard overlap across non-abstain persona cite sets.

    Pitfall 6 guard: empty sets (abstentions) are dropped before computation.
    Requires >= 2 non-empty sets to return a non-zero overlap — single persona
    or all-abstain rounds yield 0.0.

    No consensus-forcing: overlap is *detected* from independent cite sets,
    never manufactured (D-07 invariant).

    Args:
        cite_sets: List of node_id sets, one per persona turn per round.

    Returns:
        Jaccard similarity in [0.0, 1.0]. 0.0 when fewer than 2 non-empty sets.
    """
    non_empty = [s for s in cite_sets if s]
    if len(non_empty) < 2:
        return 0.0
    intersection: set[str] = set(non_empty[0])
    union: set[str] = set(non_empty[0])
    for s in non_empty[1:]:
        intersection &= s
        union |= s
    if not union:
        return 0.0
    return len(intersection) / len(union)
