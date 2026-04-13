"""graph delta computation — diff, staleness, and GRAPH_DELTA.md rendering."""
from __future__ import annotations

from pathlib import Path

import networkx as nx


def compute_delta(
    G_old: nx.Graph,
    communities_old: dict[int, list[str]],
    G_new: nx.Graph,
    communities_new: dict[int, list[str]],
) -> dict:
    """Compare two graph snapshots and return a structured diff dict.

    Returns dict with keys: added_nodes, removed_nodes, added_edges,
    removed_edges, community_migrations, connectivity_changes.
    """
    old_nodes = set(G_old.nodes())
    new_nodes = set(G_new.nodes())
    old_edges = set(G_old.edges())
    new_edges = set(G_new.edges())

    added_nodes = sorted(new_nodes - old_nodes)
    removed_nodes = sorted(old_nodes - new_nodes)
    common_nodes = old_nodes & new_nodes

    # Community membership: node_id -> community_id
    old_membership: dict[str, int | None] = {
        n: cid for cid, ns in communities_old.items() for n in ns
    }
    new_membership: dict[str, int | None] = {
        n: cid for cid, ns in communities_new.items() for n in ns
    }

    migrations: dict[str, tuple[int | None, int | None]] = {}
    for n in common_nodes:
        old_cid = old_membership.get(n)
        new_cid = new_membership.get(n)
        if old_cid != new_cid:
            migrations[n] = (old_cid, new_cid)

    # Per-node connectivity delta
    connectivity: dict[str, dict] = {}
    for n in common_nodes:
        old_deg = G_old.degree(n)
        new_deg = G_new.degree(n)
        if old_deg != new_deg:
            old_edges_n = set(G_old.edges(n))
            new_edges_n = set(G_new.edges(n))
            connectivity[n] = {
                "degree_delta": new_deg - old_deg,
                "added_edges": sorted(new_edges_n - old_edges_n),
                "removed_edges": sorted(old_edges_n - new_edges_n),
            }

    return {
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "added_edges": sorted(new_edges - old_edges),
        "removed_edges": sorted(old_edges - new_edges),
        "community_migrations": migrations,
        "connectivity_changes": connectivity,
    }
