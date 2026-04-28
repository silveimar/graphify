"""Shared test fixtures for graphify template engine tests (Plans 02-03, 02-04)."""
from __future__ import annotations

import networkx as nx


def make_classification_context(**overrides) -> dict:
    """Return a dict conforming to ClassificationContext shape with reasonable defaults.

    Any kwarg overrides the default value. Designed for reuse by Plans 03 and 04.
    """
    defaults: dict = {
        "note_type": "thing",
        "folder": "Atlas/Dots/Things/",
        "parent_moc_label": "ML Architecture",
        "community_tag": "ml-architecture",
        "members_by_type": {},
        "sub_communities": [],
        "sibling_labels": [],
    }
    defaults.update(overrides)
    return defaults


def make_moc_context(**overrides) -> dict:
    """Return a ClassificationContext-shaped dict for MOC rendering tests.

    Defaults represent an ML Architecture community with two members,
    a cohesion score, and empty sub_communities.
    Any kwarg overrides the default value.
    """
    defaults: dict = {
        "note_type": "moc",
        "folder": "Atlas/Maps/",
        "community_name": "ML Architecture",
        "community_tag": "ml-architecture",
        "members_by_type": {
            "thing": [{"id": "n_transformer", "label": "Transformer"}],
            "statement": [],
            "person": [],
            "source": [{"id": "n_paper", "label": "Attention Is All You Need"}],
        },
        "sub_communities": [],
        "sibling_labels": [],
        "cohesion": 0.82,
    }
    defaults.update(overrides)
    return defaults


def make_min_graph() -> nx.Graph:
    """Return a minimal NetworkX graph with 3 nodes and 2 edges for testing.

    Nodes:
      - n_transformer: label="Transformer", code node
      - n_attention: label="Attention Mechanism", code node
      - n_paper: label="Attention Is All You Need", paper node

    Edges:
      - n_transformer -- n_attention (contains, EXTRACTED)
      - n_transformer -- n_paper (references, INFERRED, confidence_score=0.85)
    """
    G = nx.Graph()
    G.add_node(
        "n_transformer",
        label="Transformer",
        file_type="code",
        source_file="src/model.py",
        source_location="L42",
    )
    G.add_node(
        "n_attention",
        label="Attention Mechanism",
        file_type="code",
        source_file="src/model.py",
        source_location="L101",
    )
    G.add_node(
        "n_paper",
        label="Attention Is All You Need",
        file_type="paper",
        source_file="papers/attn.pdf",
    )
    G.add_edge(
        "n_transformer",
        "n_attention",
        relation="contains",
        confidence="EXTRACTED",
    )
    G.add_edge(
        "n_transformer",
        "n_paper",
        relation="references",
        confidence="INFERRED",
        confidence_score=0.85,
    )
    return G


def make_classification_fixture() -> tuple[nx.Graph, dict[int, list[str]]]:
    """Multi-community fixture for Phase 3 classify() tests.

    Returns (G, communities) where:
      - cid 0 = 4 real + 1 file-hub + 1 concept (above-threshold)
      - cid 1 = 2 real (below-threshold, hosts attribute-rule tests)
      - cid 2 = 1 isolate (size-1 below-threshold, no neighbors)

    Degrees are engineered so n_transformer is the unique top god node
    in cid 0 and n_auth is the unique top god node in cid 1.
    """
    G = nx.Graph()
    # --- Community 0: above-threshold, 4 real + 2 synthetic ---
    G.add_node(
        "n_transformer",
        label="Transformer",
        file_type="code",
        source_file="src/model.py",
        source_location="L42",
    )
    G.add_node(
        "n_attention",
        label="Attention",
        file_type="code",
        source_file="src/model.py",
        source_location="L101",
    )
    G.add_node(
        "n_layernorm",
        label="LayerNorm",
        file_type="code",
        source_file="src/model.py",
        source_location="L150",
    )
    G.add_node(
        "n_softmax",
        label="Softmax",
        file_type="code",
        source_file="src/model.py",
        source_location="L200",
    )
    # File hub: label == basename(source_file) → _is_file_node True
    G.add_node(
        "n_file_model",
        label="model.py",
        file_type="code",
        source_file="src/model.py",
    )
    # Concept: empty source_file → _is_concept_node True
    G.add_node(
        "n_concept_attn",
        label="AttentionConcept",
        file_type="code",
        source_file="",
    )
    # --- Community 1: below-threshold (size 2), person attribute ---
    G.add_node(
        "n_auth",
        label="AuthService",
        file_type="person",
        source_file="src/auth.py",
        source_location="L10",
    )
    G.add_node(
        "n_token",
        label="TokenValidator",
        file_type="code",
        source_file="src/auth.py",
        source_location="L88",
    )
    # --- Community 2: size-1 isolate ---
    G.add_node(
        "n_isolate",
        label="Orphan",
        file_type="code",
        source_file="src/orphan.py",
    )

    # Edges engineered so n_transformer has degree 5, n_attention 3,
    # n_layernorm 2, n_softmax 1 (within cid 0 + 1 inter-community edge),
    # n_auth has degree 2, n_token has degree 1.
    G.add_edge("n_transformer", "n_attention", relation="contains", confidence="EXTRACTED")
    G.add_edge("n_transformer", "n_layernorm", relation="contains", confidence="EXTRACTED")
    G.add_edge("n_transformer", "n_softmax", relation="contains", confidence="EXTRACTED")
    G.add_edge("n_transformer", "n_file_model", relation="contains", confidence="EXTRACTED")
    G.add_edge("n_attention", "n_layernorm", relation="references", confidence="EXTRACTED")
    G.add_edge("n_attention", "n_concept_attn", relation="references", confidence="INFERRED")
    # Inter-community edge (cid 0 → cid 1): exactly 1 — n_transformer -- n_auth
    G.add_edge("n_transformer", "n_auth", relation="calls", confidence="EXTRACTED")
    # cid 1 internal
    G.add_edge("n_auth", "n_token", relation="contains", confidence="EXTRACTED")

    communities: dict[int, list[str]] = {
        0: [
            "n_transformer",
            "n_attention",
            "n_layernorm",
            "n_softmax",
            "n_file_model",
            "n_concept_attn",
        ],
        1: ["n_auth", "n_token"],
        2: ["n_isolate"],
    }
    return G, communities


# ---------------------------------------------------------------------------
# Phase 31: Block context fixture helpers (TMPL-01 / TMPL-02)
# ---------------------------------------------------------------------------


def make_block_context(graph, node_id, *, dataview_nonempty: bool = False):
    """Build a `BlockContext` from a graph + node id, calling `_build_edge_records`.

    Used by `_expand_blocks` unit tests so the fixture matches what the
    production render path constructs.
    """
    from graphify.templates import BlockContext, _build_edge_records

    return BlockContext(
        graph=graph,
        node_id=node_id,
        edges=_build_edge_records(graph, node_id),
        dataview_nonempty=dataview_nonempty,
    )


def make_graph_with_god_node(node_id: str = "god1") -> nx.Graph:
    """Tiny graph where the node is flagged as a god node via attribute.

    Includes one peer node + edge so degree > 0 (so `if_god_node` and
    `if_has_connections` are both True; `if_isolated` is False).
    """
    G = nx.Graph()
    G.add_node(node_id, label="God Node", file_type="code", is_god_node=True)
    G.add_node("peer1", label="Peer", file_type="code")
    G.add_edge(node_id, "peer1", relation="contains", confidence="EXTRACTED")
    return G


def make_graph_with_isolated(node_id: str = "iso1") -> nx.Graph:
    """Graph with an isolated (degree-0) node — `if_isolated` True."""
    G = nx.Graph()
    G.add_node(node_id, label="Isolated", file_type="code")
    # Add unrelated nodes so the graph is not empty
    G.add_node("other", label="Other", file_type="code")
    return G


def make_graph_with_edges(node_id: str, edge_specs: list[dict]) -> nx.Graph:
    """Build a graph with a center node connected to N peers per edge_specs.

    Each `edge_spec` is a dict with keys matching the six conn fields:
      - label (target node label)
      - relation (edge data)
      - target (ignored — populated from target node's label per D-06)
      - confidence (edge data)
      - community (target node attr)
      - source_file (edge data)

    The target node id is derived from the spec's label, slugified.
    """
    G = nx.Graph()
    G.add_node(node_id, label=node_id, file_type="code")
    for i, spec in enumerate(edge_specs):
        peer_label = spec.get("label", f"peer{i}")
        peer_id = f"peer_{i}_{peer_label.lower().replace(' ', '_')}"
        G.add_node(
            peer_id,
            label=peer_label,
            file_type="code",
            community=spec.get("community", ""),
        )
        G.add_edge(
            node_id,
            peer_id,
            relation=spec.get("relation", "related"),
            confidence=spec.get("confidence", "EXTRACTED"),
            source_file=spec.get("source_file", ""),
        )
    return G
