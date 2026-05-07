"""Edge-level drift between graph snapshots (CDRIFT, Phase 67 Plan 01).

Pure functional core:

- ``match_communities_by_jaccard`` — Jaccard@0.7 community membership matching.
- ``classify_edges`` — labels every implements|documents|tests edge in the new
  graph as ``"stable"``, ``"community-renamed"``, ``"community-resharded"``, or
  ``"orphaned"``.
- ``write_drift_snapshot`` — thin wrapper around ``snapshot.save_snapshot``
  (D-01 path = ``graphify-out/snapshots/``, D-02 cap=10) plus an explicit
  ``fsync`` for D-03 durability parity with ``federate.write_manifest``.
- ``compute_edge_drift`` — load the most recent snapshot, classify against the
  current graph, and return a summary dict. Returns ``None`` when no prior
  snapshot exists (D-09).

Per CONTEXT D-04/D-05, the threshold is a single hardcoded module-level
constant. No env var, no CLI flag.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import networkx as nx

from .snapshot import list_snapshots, load_snapshot, save_snapshot

# D-04, D-05 — single hardcoded constant. Communities matching ≥ this Jaccard
# similarity on membership are treated as "renamed"; below threshold the old
# community is considered "resharded".
JACCARD_THRESHOLD = 0.7  # type: float

# D-07 — drift only classifies these three edge classes (in addition to nodes
# remaining in matched communities).
_DRIFT_RELATIONS: frozenset[str] = frozenset({"implements", "documents", "tests"})


# ---------------------------------------------------------------------------
# Jaccard community matching (CDRIFT-01)
# ---------------------------------------------------------------------------

def match_communities_by_jaccard(
    old: dict[int, list[str]],
    new: dict[int, list[str]],
    threshold: float = JACCARD_THRESHOLD,
) -> dict[int, int]:
    """Return ``{old_cid: new_cid}`` for community pairs whose membership
    Jaccard similarity is ≥ ``threshold``.

    Greedy best-match: iterate old communities in stable order, and for each
    pick the highest-similarity unclaimed new community. Each new community is
    claimed at most once.
    """
    old_sets: dict[int, frozenset[str]] = {
        cid: frozenset(members) for cid, members in old.items()
    }
    new_sets: dict[int, frozenset[str]] = {
        cid: frozenset(members) for cid, members in new.items()
    }

    matches: dict[int, int] = {}
    claimed: set[int] = set()

    for old_cid in sorted(old_sets.keys()):
        old_members = old_sets[old_cid]
        if not old_members:
            continue
        best_cid: int | None = None
        best_sim: float = 0.0
        for new_cid, new_members in new_sets.items():
            if new_cid in claimed:
                continue
            if not new_members:
                continue
            inter = len(old_members & new_members)
            if inter == 0:
                continue
            union = len(old_members | new_members)
            sim = inter / union if union else 0.0
            if sim >= threshold and sim > best_sim:
                best_sim = sim
                best_cid = new_cid
        if best_cid is not None:
            matches[old_cid] = best_cid
            claimed.add(best_cid)

    return matches


# ---------------------------------------------------------------------------
# Edge classification (CDRIFT-02)
# ---------------------------------------------------------------------------

def _node_to_cid(communities: dict[int, list[str]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for cid, members in communities.items():
        for n in members:
            out[n] = cid
    return out


def classify_edges(
    G_old: nx.Graph,
    communities_old: dict[int, list[str]],
    G_new: nx.Graph,
    communities_new: dict[int, list[str]],
) -> list[dict]:
    """Classify every implements|documents|tests edge in ``G_new``.

    Returns a list of records ``{source, target, relation, source_file,
    classification}`` where ``classification`` is one of ``"stable"``,
    ``"community-renamed"``, ``"community-resharded"``, ``"orphaned"`` (D-07).
    """
    matches = match_communities_by_jaccard(communities_old, communities_new)
    old_node_to_cid = _node_to_cid(communities_old)
    new_node_to_cid = _node_to_cid(communities_new)
    matched_old_cids = set(matches.keys())

    out: list[dict] = []
    # Iterate edges; supports both Graph and MultiGraph.
    for u, v, data in G_new.edges(data=True):
        relation = data.get("relation")
        if relation not in _DRIFT_RELATIONS:
            continue
        source_file = data.get("source_file", "")

        # Orphaned: at least one endpoint missing in old graph entirely OR
        # missing from any old community membership.
        if (
            u not in G_old.nodes
            or v not in G_old.nodes
            or u not in old_node_to_cid
            or v not in old_node_to_cid
        ):
            classification = "orphaned"
        else:
            old_cid_u = old_node_to_cid[u]
            old_cid_v = old_node_to_cid[v]
            new_cid_u = new_node_to_cid.get(u)
            new_cid_v = new_node_to_cid.get(v)

            if new_cid_u is None or new_cid_v is None:
                classification = "orphaned"
            else:
                # Endpoints present in both partitions. Are their old
                # communities each matched (Jaccard ≥ 0.7) in the new
                # partition? If yes → stable or community-renamed; if no for
                # at least one → community-resharded.
                if (
                    old_cid_u in matched_old_cids
                    and old_cid_v in matched_old_cids
                ):
                    # Endpoints' old communities had a renamed counterpart.
                    # If those counterparts equal the actual new cids of the
                    # endpoints, they're truly stable; otherwise the old
                    # communities matched something else (rare with greedy
                    # best-match, but possible) → still community-renamed.
                    expected_new_u = matches[old_cid_u]
                    expected_new_v = matches[old_cid_v]
                    same_u = expected_new_u == new_cid_u and old_cid_u == new_cid_u
                    same_v = expected_new_v == new_cid_v and old_cid_v == new_cid_v
                    if same_u and same_v:
                        classification = "stable"
                    else:
                        classification = "community-renamed"
                else:
                    classification = "community-resharded"

        out.append(
            {
                "source": u,
                "target": v,
                "relation": relation,
                "source_file": source_file,
                "classification": classification,
            }
        )

    return out


# ---------------------------------------------------------------------------
# Snapshot persistence (CDRIFT-04)
# ---------------------------------------------------------------------------

def write_drift_snapshot(
    G: nx.Graph,
    communities: dict[int, list[str]],
    project_root: Path = Path("."),
    cap: int = 10,
) -> Path:
    """Persist a graph snapshot under ``graphify-out/snapshots/`` (D-01).

    Delegates atomic write + FIFO retention to :func:`snapshot.save_snapshot`
    (D-02 cap=10). Adds an explicit ``fsync`` of the resulting file descriptor
    for Phase-66-equivalent durability (D-03).
    """
    try:
        path = save_snapshot(G, communities, project_root=project_root, cap=cap)
    except Exception as exc:
        print(
            f"[graphify] error: failed to write drift snapshot: {exc}\n"
            f"  hint: ensure {Path(project_root)!s}/graphify-out/snapshots/ is writable",
            file=sys.stderr,
        )
        raise

    # D-03: explicit fsync for durability parity with federate.write_manifest.
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # fsync failure is non-fatal (file is already on disk via os.replace);
        # warn but don't raise.
        pass

    return path


def compute_edge_drift(
    G_new: nx.Graph,
    communities_new: dict[int, list[str]],
    project_root: Path = Path("."),
) -> dict | None:
    """Compute edge drift against the most recent prior snapshot.

    Returns ``None`` when no prior snapshot exists (D-09 — caller omits the
    Drift section). Otherwise returns a summary dict with shape::

        {
          "counts": {"stable": int, "community-renamed": int,
                     "community-resharded": int, "orphaned": int},
          "edges":  list[dict],   # one per implements|documents|tests edge
        }
    """
    snaps = list_snapshots(project_root)
    if not snaps:
        return None

    prev = snaps[-1]  # mtime-sorted, oldest first → last is newest
    try:
        G_old, communities_old, _meta = load_snapshot(prev)
    except ValueError as exc:
        print(
            f"[graphify] error: corrupt drift snapshot: {exc}\n"
            f"  hint: delete {prev!s} and re-run to regenerate",
            file=sys.stderr,
        )
        return None

    edges = classify_edges(G_old, communities_old, G_new, communities_new)
    counts = {
        "stable": 0,
        "community-renamed": 0,
        "community-resharded": 0,
        "orphaned": 0,
    }
    for e in edges:
        cls = e["classification"]
        if cls in counts:
            counts[cls] += 1
    return {"counts": counts, "edges": edges}
