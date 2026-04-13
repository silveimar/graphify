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


def classify_staleness(node_data: dict) -> str:
    """Classify a node as FRESH, STALE, or GHOST based on source file state.

    FRESH  — source_hash matches current file hash (or no provenance to check)
    STALE  — source_hash differs from current file hash
    GHOST  — source_file no longer exists on disk
    """
    source_file = node_data.get("source_file", "")
    stored_hash = node_data.get("source_hash")
    if not source_file or not stored_hash:
        return "FRESH"
    p = Path(source_file)
    if not p.exists():
        return "GHOST"
    # Fast mtime gate: skip SHA256 if mtime unchanged
    try:
        current_mtime = p.stat().st_mtime
        stored_mtime = node_data.get("source_mtime")
        if stored_mtime is not None and current_mtime == stored_mtime:
            return "FRESH"
    except OSError:
        return "GHOST"
    from .cache import file_hash

    try:
        current_hash = file_hash(p)
    except OSError:
        return "GHOST"
    return "FRESH" if current_hash == stored_hash else "STALE"


def _escape_pipe(s: str) -> str:
    """Escape pipe characters in markdown table cells."""
    return str(s).replace("|", "\\|")


def render_delta_md(
    delta: dict,
    G_new: nx.Graph | None = None,
    communities_new: dict[int, list[str]] | None = None,
    first_run: bool = False,
) -> str:
    """Render a GRAPH_DELTA.md report from a delta dict.

    Returns markdown string with Summary + Archive sections.
    If first_run is True, returns a sentinel message.
    """
    if first_run:
        return "# Graph Delta Report\n\nFirst run — no previous snapshot to compare.\n"

    lines: list[str] = ["# Graph Delta Report", ""]

    added_n = delta.get("added_nodes", [])
    removed_n = delta.get("removed_nodes", [])
    added_e = delta.get("added_edges", [])
    removed_e = delta.get("removed_edges", [])
    migrations = delta.get("community_migrations", {})
    connectivity = delta.get("connectivity_changes", {})

    has_changes = any([added_n, removed_n, added_e, removed_e, migrations, connectivity])

    # --- Summary section ---
    lines.append("## Summary")
    lines.append("")

    if not has_changes:
        lines.append("No changes detected between snapshots.")
    else:
        lines.append(
            f"- **Added nodes:** {len(added_n)} | **Removed nodes:** {len(removed_n)} "
            f"| **Added edges:** {len(added_e)} | **Removed edges:** {len(removed_e)}"
        )
        lines.append(f"- **Community migrations:** {len(migrations)} nodes changed communities")
        lines.append(f"- **Connectivity changes:** {len(connectivity)} nodes with degree changes")
        lines.append("")

        # Narrative: top changes
        significant: list[str] = []
        if added_n:
            show = added_n[:5]
            suffix = f" (+{len(added_n) - 5} more)" if len(added_n) > 5 else ""
            significant.append(f"New nodes: {', '.join(show)}{suffix}")
        if removed_n:
            show = removed_n[:5]
            suffix = f" (+{len(removed_n) - 5} more)" if len(removed_n) > 5 else ""
            significant.append(f"Removed nodes: {', '.join(show)}{suffix}")
        # Top connectivity changes by absolute degree_delta
        if connectivity:
            top = sorted(connectivity.items(), key=lambda kv: abs(kv[1]["degree_delta"]), reverse=True)[:5]
            for nid, info in top:
                sign = "+" if info["degree_delta"] > 0 else ""
                significant.append(f"`{nid}` degree {sign}{info['degree_delta']}")
        if migrations:
            top_m = list(migrations.items())[:5]
            for nid, (old_c, new_c) in top_m:
                significant.append(f"`{nid}` migrated community {old_c} -> {new_c}")

        if significant:
            lines.append("**Notable changes:**")
            for s in significant[:10]:
                lines.append(f"- {s}")

    # Staleness subsection
    stale_nodes: list[tuple[str, str, str]] = []  # (node_id, source_file, state)
    fresh_count = stale_count = ghost_count = 0
    if G_new is not None:
        for nid, ndata in G_new.nodes(data=True):
            state = classify_staleness(ndata)
            if state == "FRESH":
                fresh_count += 1
            elif state == "STALE":
                stale_count += 1
                stale_nodes.append((nid, ndata.get("source_file", ""), "STALE"))
            elif state == "GHOST":
                ghost_count += 1
                stale_nodes.append((nid, ndata.get("source_file", ""), "GHOST"))
        lines.append("")
        lines.append(f"- **Staleness:** {fresh_count} FRESH, {stale_count} STALE, {ghost_count} GHOST")

    # --- Archive section ---
    lines += ["", "## Archive", ""]

    # Added Nodes
    lines.append("### Added Nodes")
    lines.append("")
    if added_n:
        lines.append("| Node ID | Label | Source File |")
        lines.append("|---------|-------|-------------|")
        for nid in added_n:
            label = nid
            source = ""
            if G_new is not None and nid in G_new:
                nd = G_new.nodes[nid]
                label = _escape_pipe(nd.get("label", nid))
                source = _escape_pipe(nd.get("source_file", ""))
            lines.append(f"| {_escape_pipe(nid)} | {label} | {source} |")
    else:
        lines.append("None.")
    lines.append("")

    # Removed Nodes
    lines.append("### Removed Nodes")
    lines.append("")
    if removed_n:
        lines.append("| Node ID |")
        lines.append("|---------|")
        for nid in removed_n:
            lines.append(f"| {_escape_pipe(nid)} |")
    else:
        lines.append("None.")
    lines.append("")

    # Community Migrations
    lines.append("### Community Migrations")
    lines.append("")
    if migrations:
        lines.append("| Node ID | From Community | To Community |")
        lines.append("|---------|---------------|-------------|")
        for nid in sorted(migrations):
            old_c, new_c = migrations[nid]
            lines.append(f"| {_escape_pipe(nid)} | {old_c} | {new_c} |")
    else:
        lines.append("None.")
    lines.append("")

    # Connectivity Changes
    lines.append("### Connectivity Changes")
    lines.append("")
    if connectivity:
        lines.append("| Node ID | Degree Delta | Added Edges | Removed Edges |")
        lines.append("|---------|-------------|-------------|---------------|")
        for nid in sorted(connectivity):
            info = connectivity[nid]
            dd = info["degree_delta"]
            sign = "+" if dd > 0 else ""
            added_list = ", ".join(f"{s}->{t}" for s, t in info.get("added_edges", []))
            removed_list = ", ".join(f"{s}->{t}" for s, t in info.get("removed_edges", []))
            lines.append(f"| {_escape_pipe(nid)} | {sign}{dd} | {_escape_pipe(added_list or 'none')} | {_escape_pipe(removed_list or 'none')} |")
    else:
        lines.append("None.")
    lines.append("")

    # Stale Nodes table
    if stale_nodes:
        lines.append("### Stale Nodes")
        lines.append("")
        lines.append("| Node ID | Source File | State |")
        lines.append("|---------|------------|-------|")
        for nid, sf, state in sorted(stale_nodes):
            lines.append(f"| {_escape_pipe(nid)} | {_escape_pipe(sf)} | {state} |")
        lines.append("")

    return "\n".join(lines)
