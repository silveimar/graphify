from __future__ import annotations

"""Cross-repo concept federation merge engine (Phase 66 CFED, Plan 01).

Pure, deterministic, stdlib-only function that merges concept nodes across
multiple graphify repos using a multi-signal AND-gate (D-66.4):

    1. Label match (case-folded exact)
    2. Neighborhood label Jaccard ≥ 0.5
    3. ≥1 shared source_file basename

Tiebreaker (T-66.4): when two peer candidates compete for the same local
concept, the winner has the higher mean `confidence_score` across its
contributing INFERRED neighborhood edges.

Canonical merged_id (D-66.7): lex-min over namespaced contributing ids.

This module exposes only the merge engine; pipeline wiring (build.py),
manifest persistence, and report rendering live in Plans 02–04.
"""

import json
import os
from pathlib import Path
from typing import Iterable

from graphify.validate import validate_extraction_for_read


__all__ = ["federate", "build_manifest", "write_manifest", "FederationCollisionError"]


# Concept-typed nodes (everything except executable code) participate in merges.
_CONCEPT_FILE_TYPES = frozenset({"document", "paper", "rationale", "image"})

# Jaccard threshold for neighborhood overlap (D-66.4).
_JACCARD_THRESHOLD = 0.5


class FederationCollisionError(ValueError):
    """Raised when two `--federate-with` peers resolve to the same repo basename (D-66.3)."""


# --------------------------------------------------------------------------- #
# Repo-label derivation                                                       #
# --------------------------------------------------------------------------- #


def _repo_label_for_peer(peer_path: Path) -> str:
    """Derive the `{repo}` namespace label for a peer artifact path.

    Per D-66.3: basename of the directory parent of the `--federate-with` argument.
    When `peer_path` points at `<repo>/graphify-out/graph.json` we return the
    repo directory name (`peer_path.parent.parent.name` is the repo when
    `peer_path.parent.name == "graphify-out"`); for other shapes we fall back
    to `peer_path.parent.name`.
    """
    parent = peer_path.parent
    if parent.name == "graphify-out":
        return parent.parent.name
    return parent.name


# --------------------------------------------------------------------------- #
# Per-node helpers                                                            #
# --------------------------------------------------------------------------- #


def _is_concept(node: dict) -> bool:
    return node.get("file_type") in _CONCEPT_FILE_TYPES


def _basename(path: str) -> str:
    """Stdlib-only basename derivation (handles both POSIX and Windows separators)."""
    if not path:
        return ""
    # Normalise both POSIX and Windows separators without importing os.path.
    last = max(path.rfind("/"), path.rfind("\\"))
    return path[last + 1:] if last >= 0 else path


def _neighbor_labels(node_id: str, edges: list[dict], id_to_label: dict[str, str]) -> set[str]:
    """1-hop neighbor labels (case-folded), label-based to avoid id-coupling on iterative merges."""
    neighbors: set[str] = set()
    for e in edges:
        if e.get("source") == node_id:
            other = e.get("target")
        elif e.get("target") == node_id:
            other = e.get("source")
        else:
            continue
        lbl = id_to_label.get(other)
        if isinstance(lbl, str) and lbl:
            neighbors.add(lbl.casefold())
    return neighbors


def _basenames_for_node(node_id: str, node: dict, edges: list[dict]) -> set[str]:
    """Collect source_file basenames associated with a concept (node + incident edges)."""
    out: set[str] = set()
    sf = node.get("source_file")
    if isinstance(sf, str) and sf:
        out.add(_basename(sf))
    for e in edges:
        if e.get("source") == node_id or e.get("target") == node_id:
            esf = e.get("source_file")
            if isinstance(esf, str) and esf:
                out.add(_basename(esf))
    return out


def _mean_inferred_score(node_id: str, edges: list[dict]) -> float:
    """Mean `confidence_score` across INFERRED edges incident to this concept (0.0 if none)."""
    scores: list[float] = []
    for e in edges:
        if e.get("confidence") != "INFERRED":
            continue
        if e.get("source") != node_id and e.get("target") != node_id:
            continue
        cs = e.get("confidence_score")
        if isinstance(cs, (int, float)):
            scores.append(float(cs))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


# --------------------------------------------------------------------------- #
# AND-gate primitives (D-66.4)                                                #
# --------------------------------------------------------------------------- #


def _label_ok(local_label: str, peer_label: str) -> bool:
    return (local_label or "").casefold() == (peer_label or "").casefold()


def _jaccard_ok(local_nbrs: set[str], peer_nbrs: set[str]) -> tuple[bool, float]:
    union = local_nbrs | peer_nbrs
    if not union:
        return False, 0.0
    j = len(local_nbrs & peer_nbrs) / len(union)
    return j >= _JACCARD_THRESHOLD, j


def _basename_ok(local_bn: set[str], peer_bn: set[str]) -> tuple[bool, list[str]]:
    shared = sorted(local_bn & peer_bn)
    return len(shared) >= 1, shared


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #


def federate(
    extraction: dict,
    peers: list[Path] | Iterable[Path],
    local_repo: str,
) -> tuple[dict, list[dict]]:
    """Merge concept nodes across the local extraction and peer graph.json artifacts.

    Args:
        extraction: Local extraction dict ({"nodes": [...], "edges": [...]}).
        peers: List of peer `graph.json` paths (one per `--federate-with`).
        local_repo: Repo label used to namespace local node ids.

    Returns:
        (merged_extraction, merges) where:
          - `merged_extraction` is a NEW dict (input is not mutated) whose node
            ids are all namespaced as `{repo}::{original_id}`. Merged concept
            pairs collapse onto a canonical lex-min `merged_id`.
          - `merges` is a list of per-merge manifest entries matching D-66.5.

    Raises:
        FederationCollisionError: when two peer paths share the same repo basename.
    """
    peer_paths: list[Path] = [Path(p) for p in peers]

    # ---- Collision check (D-66.3) BEFORE any merge work ------------------- #
    repo_to_paths: dict[str, list[Path]] = {}
    for pp in peer_paths:
        label = _repo_label_for_peer(pp)
        repo_to_paths.setdefault(label, []).append(pp)
    # local_repo collision with a peer is also a hard fail.
    if local_repo in repo_to_paths:
        raise FederationCollisionError(
            f"[graphify] error: --federate-with paths share repo basename {local_repo!r}\n"
            f"  hint: rename a peer directory or pass distinct parents"
        )
    for label, paths in repo_to_paths.items():
        if len(paths) >= 2:
            raise FederationCollisionError(
                f"[graphify] error: --federate-with paths share repo basename {label!r}\n"
                f"  hint: rename a peer directory or pass distinct parents"
            )

    # ---- Load + validate peers ------------------------------------------- #
    peer_extractions: list[tuple[str, dict]] = []  # (repo_label, extraction)
    for pp in peer_paths:
        with pp.open("r", encoding="utf-8") as fh:
            peer_data = json.load(fh)
        errs = validate_extraction_for_read(peer_data)
        if errs:
            raise ValueError(
                f"[graphify] error: peer extraction at {pp} failed schema validation\n"
                f"  hint: {errs[0]}"
            )
        peer_extractions.append((_repo_label_for_peer(pp), peer_data))

    # ---- Namespace all nodes/edges --------------------------------------- #
    def _ns(repo: str, node_id: str) -> str:
        return f"{repo}::{node_id}"

    def _namespace_extraction(repo: str, data: dict) -> tuple[list[dict], list[dict]]:
        ns_nodes = []
        for n in data.get("nodes", []):
            nn = dict(n)
            nn["id"] = _ns(repo, n["id"])
            ns_nodes.append(nn)
        ns_edges = []
        for e in data.get("edges", []):
            ne = dict(e)
            ne["source"] = _ns(repo, e["source"])
            ne["target"] = _ns(repo, e["target"])
            ns_edges.append(ne)
        return ns_nodes, ns_edges

    local_nodes_ns, local_edges_ns = _namespace_extraction(local_repo, extraction)
    all_nodes: list[dict] = list(local_nodes_ns)
    all_edges: list[dict] = list(local_edges_ns)
    # Track per-repo (repo, namespaced_nodes, namespaced_edges) for candidate generation.
    contributors: list[tuple[str, list[dict], list[dict]]] = [
        (local_repo, local_nodes_ns, local_edges_ns),
    ]
    for repo, peer_data in peer_extractions:
        pn, pe = _namespace_extraction(repo, peer_data)
        all_nodes.extend(pn)
        all_edges.extend(pe)
        contributors.append((repo, pn, pe))

    # ---- Candidate generation: AND-gate per (local_concept, peer_concept) #
    # Build per-repo lookups.
    repo_id_to_label: dict[str, dict[str, str]] = {}
    for repo, nodes, _edges in contributors:
        repo_id_to_label[repo] = {n["id"]: n.get("label", "") for n in nodes}

    # candidates: dict keyed by local_concept_id → list of (peer_repo, peer_node, signals, mean_score)
    candidates: dict[str, list[dict]] = {}

    local_concepts = [n for n in local_nodes_ns if _is_concept(n)]
    for local_node in local_concepts:
        l_id = local_node["id"]
        l_label = local_node.get("label", "")
        l_nbrs = _neighbor_labels(l_id, local_edges_ns, repo_id_to_label[local_repo])
        l_bn = _basenames_for_node(l_id, local_node, local_edges_ns)

        for repo, p_nodes, p_edges in contributors[1:]:  # skip local
            for peer_node in p_nodes:
                if not _is_concept(peer_node):
                    continue
                p_id = peer_node["id"]
                p_label = peer_node.get("label", "")
                if not _label_ok(l_label, p_label):
                    continue
                p_nbrs = _neighbor_labels(p_id, p_edges, repo_id_to_label[repo])
                jac_ok, jac = _jaccard_ok(l_nbrs, p_nbrs)
                if not jac_ok:
                    continue
                p_bn = _basenames_for_node(p_id, peer_node, p_edges)
                bn_ok, shared_bn = _basename_ok(l_bn, p_bn)
                if not bn_ok:
                    continue
                # All three signals passed — record candidate.
                mean_score = _mean_inferred_score(p_id, p_edges)
                candidates.setdefault(l_id, []).append({
                    "repo": repo,
                    "peer_node": peer_node,
                    "peer_edges": p_edges,
                    "signals": {
                        "label_match": l_label,
                        "neighborhood_jaccard": round(jac, 6),
                        "shared_basenames": shared_bn,
                    },
                    "mean_score": mean_score,
                })

    # ---- Tiebreaker selection + merge construction ----------------------- #
    merges: list[dict] = []
    # Map from old namespaced id → canonical merged_id (for edge rewrite).
    id_remap: dict[str, str] = {}
    # Track which contributing nodes get absorbed (so we can drop them from output).
    absorbed_ids: set[str] = set()

    for local_id in sorted(candidates.keys()):
        cands = candidates[local_id]
        tiebreaker_fired = len(cands) >= 2
        # Deterministic tiebreak: highest mean_score, then lex-min peer node id.
        cands_sorted = sorted(
            cands,
            key=lambda c: (-c["mean_score"], c["peer_node"]["id"]),
        )
        winner = cands_sorted[0]

        # Local concept's own mean_score (for the contributing record's source_files).
        local_node = next(n for n in local_nodes_ns if n["id"] == local_id)
        local_label = local_node.get("label", "")
        local_sf = (
            [local_node["source_file"]]
            if isinstance(local_node.get("source_file"), str) and local_node["source_file"]
            else []
        )
        peer_node = winner["peer_node"]
        peer_sf = (
            [peer_node["source_file"]]
            if isinstance(peer_node.get("source_file"), str) and peer_node["source_file"]
            else []
        )

        contributing = [
            {
                "repo": local_repo,
                "original_id": local_id.split("::", 1)[1],
                "label": local_label,
                "source_files": sorted(local_sf),
            },
            {
                "repo": winner["repo"],
                "original_id": peer_node["id"].split("::", 1)[1],
                "label": peer_node.get("label", ""),
                "source_files": sorted(peer_sf),
            },
        ]
        namespaced_ids = [local_id, peer_node["id"]]
        merged_id = min(namespaced_ids)

        entry: dict = {
            "merged_id": merged_id,
            "contributing": contributing,
            "signals": winner["signals"],
        }
        if tiebreaker_fired:
            entry["tiebreaker_score"] = round(winner["mean_score"], 6)
        merges.append(entry)

        # Remap absorbed ids → merged_id.
        for nid in namespaced_ids:
            if nid != merged_id:
                id_remap[nid] = merged_id
                absorbed_ids.add(nid)

    # Sort merges by merged_id for determinism.
    merges.sort(key=lambda e: e["merged_id"])

    # ---- Apply id_remap to the merged extraction ------------------------- #
    out_nodes: list[dict] = []
    seen_ids: set[str] = set()
    for n in all_nodes:
        nid = n["id"]
        if nid in absorbed_ids:
            continue  # collapsed into canonical merged_id
        if nid in seen_ids:
            continue
        seen_ids.add(nid)
        out_nodes.append(n)

    out_edges: list[dict] = []
    for e in all_edges:
        ne = dict(e)
        ne["source"] = id_remap.get(e["source"], e["source"])
        ne["target"] = id_remap.get(e["target"], e["target"])
        out_edges.append(ne)

    # Deterministic node ordering: sort by id for stable iteration.
    out_nodes.sort(key=lambda n: n["id"])
    out_edges.sort(key=lambda e: (e["source"], e["target"], e.get("relation", "")))

    merged_extraction: dict = {"nodes": out_nodes, "edges": out_edges}
    return merged_extraction, merges


def build_manifest(merges: list[dict]) -> list[dict]:
    """Return manifest entries sorted by `merged_id` (deterministic, D-66.5 schema)."""
    return sorted(merges, key=lambda e: e["merged_id"])


# --------------------------------------------------------------------------- #
# Plan 02: Atomic, vault-aware manifest writer (CFED-04)                      #
# --------------------------------------------------------------------------- #


def write_manifest(
    entries: list[dict],
    target: Path,
    *,
    resolved=None,
) -> Path:
    """Atomically write the federation manifest to the resolved artifacts dir.

    Path resolves through ``graphify.output.default_graphify_artifacts_dir`` so
    that vault-aware (Phase 27/63) routing is honored — never hardcode
    ``graphify-out/``.

    Atomicity (Phase 64 sidecar pattern, mirrored from
    ``export.py::_write_repo_identity_sidecar``): write to ``<final>.tmp``,
    fsync, then ``os.replace``. If ``os.replace`` raises, unlink the tmp file
    so no orphan remains.
    """
    # Lazy import to avoid pulling output.py into federate.py's import set
    # at module load (keeps Plan 01's no-new-deps AST scan green for callers
    # who never invoke write_manifest).
    from graphify.output import default_graphify_artifacts_dir

    artifacts_dir = default_graphify_artifacts_dir(target, resolved=resolved)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    final_path = artifacts_dir / "federation-manifest.json"
    tmp_path = final_path.with_suffix(".json.tmp")
    payload = json.dumps(entries, indent=2, sort_keys=True, separators=(",", ": "))
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, final_path)
    except OSError:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
    return final_path
