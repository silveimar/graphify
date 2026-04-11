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
