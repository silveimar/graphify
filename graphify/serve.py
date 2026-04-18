# MCP stdio server - exposes graph query tools to Claude and other agents
from __future__ import annotations
import base64
import hashlib
import json
import os
import sys
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph
from graphify.security import sanitize_label
from graphify.delta import classify_staleness
from graphify.mcp_tool_registry import build_mcp_tools, query_graph_input_schema as _query_graph_input_schema


def _append_annotation(out_dir: Path, record: dict) -> None:
    """Append a single annotation record as a JSON line to annotations.jsonl."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "annotations.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _compact_annotations(path: Path) -> list[dict]:
    """Read annotations.jsonl, deduplicate by (node_id, annotation_type, peer_id), rewrite atomically.

    Deduplication keeps the LAST record per key. Corrupt lines are skipped.
    Returns the deduplicated list, or [] if the file does not exist.
    """
    if not path.exists():
        return []
    records: dict[tuple, dict] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                key = (record.get("node_id"), record.get("annotation_type"), record.get("peer_id"))
                records[key] = record
            except json.JSONDecodeError:
                # Skip corrupt lines — data loss limited to at most one record (T-07-06)
                continue
    deduped = list(records.values())
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in deduped), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return deduped


def _load_agent_edges(path: Path) -> list[dict]:
    """Load agent-edges.json as a list of dicts. Returns [] if missing or corrupt."""
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_agent_edges(out_dir: Path, edges: list[dict]) -> None:
    """Atomically write agent-edges.json to out_dir using os.replace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "agent-edges.json"
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(edges, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _load_telemetry(path: Path) -> dict:
    """Load telemetry.json as a dict. Returns default on missing or corrupt."""
    if not path.exists():
        return {"counters": {}, "threshold": 5}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"counters": {}, "threshold": 5}


def _load_dedup_report(out_dir: Path) -> dict[str, str]:
    """D-16: load {eliminated_id: canonical_id} alias map from dedup_report.json.

    Returns {} if the report is missing, unreadable, malformed, or has no
    alias_map key. Never raises — broken dedup report must not crash MCP serve.
    """
    path = out_dir / "dedup_report.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("[graphify] warning: dedup_report.json could not be parsed; alias map disabled", file=sys.stderr)
        return {}
    except OSError as e:
        print(f"[graphify] warning: could not read dedup_report.json ({e}); alias map disabled", file=sys.stderr)
        return {}
    alias_map = data.get("alias_map", {}) if isinstance(data, dict) else {}
    # Defensive: ensure all keys/values are strings (reject anything else)
    if not isinstance(alias_map, dict):
        return {}
    return {str(k): str(v) for k, v in alias_map.items() if isinstance(k, str) and isinstance(v, str)}


def _save_telemetry(out_dir: Path, data: dict) -> None:
    """Atomically write telemetry.json to out_dir using os.replace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "telemetry.json"
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _compute_branching_factor(G: nx.Graph) -> float:
    """Graph-average branching factor = 2*E/N. Used for depth-extrapolation in cardinality estimates.

    Returns 1.0 for the empty graph (degenerate case — estimator still produces a finite number).
    Cached at graph-load in serve() and refreshed by _reload_if_stale(). Per CONTEXT D-04.
    """
    if G.number_of_nodes() == 0:
        return 1.0
    return (2.0 * G.number_of_edges()) / G.number_of_nodes()


def _record_traversal(
    telemetry: dict,
    edges: list[tuple],
    search_strategy: str = "bfs",
) -> None:
    """Increment traversal counters for each edge. Keys normalized as min:max. Per D-02.

    Phase 9.2 D-08: records `search_strategy` per call in `telemetry["strategies"]`.
    Valid values: "bfs", "dfs", "bidirectional". Legacy callers without the kwarg
    default to "bfs", matching the pre-9.2 implicit behavior.
    """
    counters = telemetry.setdefault("counters", {})
    for u, v in edges:
        key = f"{min(u, v)}:{max(u, v)}"
        counters[key] = counters.get(key, 0) + 1
    # Phase 9.2 D-08: per-call strategy record. Phase 9.1's _compute_hot_cold() reads
    # `counters` not this list — backward compatible extension.
    telemetry.setdefault("strategies", []).append({
        "strategy": search_strategy,
        "edges": len(edges),
    })


# Continuation-token codec — stateless drill-down for Phase 9.2 progressive retrieval.
# Payload shape: {"q": dict, "v": list[str], "l": int, "h": str}. Per CONTEXT D-03.

_CONTINUATION_TOKEN_MAX_BYTES = 65536  # 64 KB hard cap (DoS mitigation, RESEARCH §Security)


def _encode_continuation(
    query_params: dict,
    visited: set[str],
    current_layer: int,
    graph_mtime: float,
) -> str:
    """Encode an opaque drill-down token. Base64(JSON) with SHA-256 mtime-integrity hash.

    Opaque to agents; debug-transparent to server-side logs. Per CONTEXT D-03.
    Deterministic: `visited` is sorted so two encodes with identical input produce identical output.
    """
    mtime_hash = hashlib.sha256(
        f"{graph_mtime}:{json.dumps(query_params, sort_keys=True)}".encode()
    ).hexdigest()[:16]
    payload = {
        "q": query_params,
        "v": sorted(visited),
        "l": current_layer,
        "h": mtime_hash,
    }
    return base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True).encode()
    ).decode()


def _decode_continuation(token: str, graph_mtime: float) -> tuple[dict, str]:
    """Decode + validate a continuation token.

    Returns (payload_dict, status) where status is one of:
      "ok"             — payload intact, mtime hash matches current graph
      "graph_changed"  — hash mismatch (graph was rebuilt or touched since encode)
      "malformed"      — base64 decode failed, JSON parse failed, or token exceeded size cap
    """
    if not token or len(token.encode()) > _CONTINUATION_TOKEN_MAX_BYTES:
        return {}, "malformed"
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        payload = json.loads(raw.decode())
        if not isinstance(payload, dict):
            return {}, "malformed"
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {}, "malformed"
    expected = hashlib.sha256(
        f"{graph_mtime}:{json.dumps(payload.get('q', {}), sort_keys=True)}".encode()
    ).hexdigest()[:16]
    if payload.get("h") != expected:
        return payload, "graph_changed"
    return payload, "ok"


def _edge_weight(traversals: int) -> float:
    """Logarithmic weight: 1.0 + log(t), clamped [1.0, 10.0]. Per D-03/D-05."""
    return max(1.0, min(10.0, 1.0 + math.log(max(1, traversals))))


def _decay_telemetry(telemetry: dict, multiplier: float = 0.8) -> None:
    """Multiply all counters by multiplier, remove zero entries. Per D-04/D-05."""
    counters = telemetry.get("counters", {})
    to_remove = []
    for key, count in counters.items():
        new_val = int(count * multiplier)
        if new_val <= 0:
            to_remove.append(key)
        else:
            counters[key] = new_val
    for key in to_remove:
        del counters[key]


def _check_derived_edges(
    G: nx.Graph,
    telemetry: dict,
    out_dir: Path,
    agent_edges: list[dict],
) -> None:
    """Propose 2-hop shortcut edges when traversal threshold met. Per D-06/D-07/D-08."""
    threshold = telemetry.get("threshold", 5)
    counters = telemetry.get("counters", {})
    existing = {(e["source"], e["target"]) for e in agent_edges}
    existing |= {(e["target"], e["source"]) for e in agent_edges}
    added = False
    for key_ab, count_ab in list(counters.items()):
        if count_ab < threshold:
            continue
        a, b = key_ab.split(":", 1)
        if b not in G:
            continue
        for neighbor in G.neighbors(b):
            if neighbor == a:
                continue
            key_bc = f"{min(b, neighbor)}:{max(b, neighbor)}"
            if counters.get(key_bc, 0) < threshold:
                continue
            pair = (a, neighbor)
            rpair = (neighbor, a)
            if pair in existing or rpair in existing:
                continue
            if G.has_edge(a, neighbor):
                continue
            record = {
                "source": a,
                "target": neighbor,
                "relation": "derived_shortcut",
                "confidence": "INFERRED",
                "confidence_score": 0.7,
                "source_file": "",
                "via": b,
                "traversal_count": min(count_ab, counters[key_bc]),
            }
            agent_edges.append(record)
            existing.add(pair)
            added = True
    if added:
        _save_agent_edges(out_dir, agent_edges)


def _make_annotate_record(node_id: str, text: str, peer_id: str, session_id: str) -> dict:
    """Create a validated annotation record. All string inputs are sanitized."""
    return {
        "record_id": str(uuid.uuid4()),
        "annotation_type": "annotation",
        "node_id": sanitize_label(node_id),
        "text": sanitize_label(text),
        "peer_id": sanitize_label(peer_id),
        "session_id": sanitize_label(session_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_flag_record(node_id: str, importance: str, peer_id: str, session_id: str) -> dict:
    """Create a validated flag record. Raises ValueError for invalid importance values."""
    if importance not in {"high", "medium", "low"}:
        raise ValueError(f"Invalid importance: must be high, medium, or low. Got: {importance!r}")
    return {
        "record_id": str(uuid.uuid4()),
        "annotation_type": "flag",
        "node_id": sanitize_label(node_id),
        "importance": importance,
        "peer_id": sanitize_label(peer_id),
        "session_id": sanitize_label(session_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_edge_record(source: str, target: str, relation: str, peer_id: str, session_id: str) -> dict:
    """Create a validated agent edge record. Never modifies the in-memory graph (T-07-03)."""
    return {
        "record_id": str(uuid.uuid4()),
        "source": sanitize_label(source),
        "target": sanitize_label(target),
        "relation": sanitize_label(relation),
        "confidence": "INFERRED",
        "peer_id": sanitize_label(peer_id),
        "session_id": sanitize_label(session_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_proposal_record(arguments: dict, session_id: str) -> dict:
    """Create a validated proposal record. All string inputs are sanitized."""
    title = sanitize_label(arguments.get("title", ""))
    note_type = sanitize_label(arguments.get("note_type", "note"))
    body_markdown = sanitize_label(arguments.get("body_markdown", ""))
    suggested_folder = sanitize_label(arguments.get("suggested_folder", ""))
    rationale = sanitize_label(arguments.get("rationale", ""))
    tags = [sanitize_label(t) for t in arguments.get("tags", [])]
    peer_id = sanitize_label(arguments.get("peer_id", "anonymous"))
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "record_id": record_id,
        "title": title,
        "note_type": note_type,
        "body_markdown": body_markdown,
        "suggested_folder": suggested_folder,
        "tags": tags,
        "rationale": rationale,
        "peer_id": peer_id,
        "session_id": sanitize_label(session_id),
        "timestamp": timestamp,
        "status": "pending",
    }


def _save_proposal(out_dir: Path, record: dict) -> None:
    """Write a proposal record as JSON to graphify-out/proposals/{record_id}.json."""
    proposals_dir = out_dir / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    (proposals_dir / f"{record['record_id']}.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )


def _list_proposals(out_dir: Path) -> list[dict]:
    """Return all proposal dicts from graphify-out/proposals/, sorted by timestamp ascending.

    Returns empty list if proposals dir does not exist. Skips corrupt JSON files.
    """
    proposals_dir = out_dir / "proposals"
    if not proposals_dir.exists():
        return []
    proposals = []
    for path in proposals_dir.glob("*.json"):
        try:
            proposals.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    proposals.sort(key=lambda r: r.get("timestamp", ""))
    return proposals


def _filter_annotations(
    annotations: list[dict],
    peer_id: str | None,
    session_id: str | None,
    time_from: str | None,
    time_to: str | None,
) -> list[dict]:
    """Filter annotation list by optional peer_id, session_id, and ISO-8601 time range."""
    result = list(annotations)
    if peer_id is not None:
        result = [r for r in result if r.get("peer_id") == peer_id]
    if session_id is not None:
        result = [r for r in result if r.get("session_id") == session_id]
    if time_from is not None:
        result = [r for r in result if r.get("timestamp", "") >= time_from]
    if time_to is not None:
        result = [r for r in result if r.get("timestamp", "") <= time_to]
    return result


def _filter_agent_edges(
    edges: list[dict],
    peer_id: str | None,
    session_id: str | None,
    node_id: str | None,
) -> list[dict]:
    """Filter agent-edge list by optional peer_id, session_id, or node_id (source or target)."""
    result = list(edges)
    if peer_id is not None:
        result = [e for e in result if e.get("peer_id") == peer_id]
    if session_id is not None:
        result = [e for e in result if e.get("session_id") == session_id]
    if node_id is not None:
        result = [e for e in result if e.get("source") == node_id or e.get("target") == node_id]
    return result


def _load_graph(graph_path: str) -> nx.Graph:
    try:
        resolved = Path(graph_path).resolve()
        if resolved.suffix != ".json":
            raise ValueError(f"Graph path must be a .json file, got: {graph_path!r}")
        if not resolved.exists():
            raise FileNotFoundError(f"Graph file not found: {resolved}")
        safe = resolved
        data = json.loads(safe.read_text(encoding="utf-8"))
        try:
            return json_graph.node_link_graph(data, edges="links")
        except TypeError:
            return json_graph.node_link_graph(data)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"error: graph.json is corrupted ({exc}). Re-run /graphify to rebuild.", file=sys.stderr)
        sys.exit(1)


def _communities_from_graph(G: nx.Graph) -> dict[int, list[str]]:
    """Reconstruct community dict from community property stored on nodes."""
    communities: dict[int, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        cid = data.get("community")
        if cid is not None:
            communities.setdefault(int(cid), []).append(node_id)
    return communities


def _score_nodes(G: nx.Graph, terms: list[str]) -> list[tuple[float, str]]:
    scored = []
    for nid, data in G.nodes(data=True):
        label = data.get("label", "").lower()
        source = data.get("source_file", "").lower()
        score = sum(1 for t in terms if t in label) + sum(0.5 for t in terms if t in source)
        if score > 0:
            scored.append((score, nid))
    return sorted(scored, reverse=True)


def _bfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:
    visited: set[str] = set(start_nodes)
    frontier = set(start_nodes)
    edges_seen: list[tuple] = []
    for _ in range(depth):
        next_frontier: set[str] = set()
        for n in frontier:
            for neighbor in G.neighbors(n):
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    edges_seen.append((n, neighbor))
        visited.update(next_frontier)
        frontier = next_frontier
    return visited, edges_seen


def _bidirectional_bfs(
    G: nx.Graph,
    start_nodes: list[str],
    target_nodes: list[str],
    depth: int,
    max_visited: int,
) -> tuple[set[str], list[tuple], str]:
    """Meet-in-the-middle BFS. `depth` is the combined hop budget (forward + reverse).

    Returns (visited, edges_seen, status) where status is one of:
      "ok"                 — frontiers met, traversal complete (reachable endpoints)
      "frontiers_disjoint" — exhausted depth budget without meeting (disjoint components)
      "budget_exhausted"   — hit max_visited cap before meet

    Per CONTEXT D-06/D-07. Implementation is hand-rolled rather than wrapping
    networkx._bidirectional_pred_succ because:
      (a) NetworkX's helper is a private API (leading underscore)
      (b) it returns pred/succ dicts for path reconstruction, not a visited set
      (c) it cannot produce partial results on disjoint frontiers
    Mirrors the (visited, edges_seen) contract of _bfs() above so _subgraph_to_text
    and _record_traversal consume it uniformly.
    """
    forward_visited: set[str] = set(start_nodes)
    reverse_visited: set[str] = set(target_nodes)
    forward_frontier: set[str] = set(start_nodes)
    reverse_frontier: set[str] = set(target_nodes)
    edges_seen: list[tuple] = []

    # Immediate meet check (start and target overlap)
    if forward_visited & reverse_visited:
        return forward_visited | reverse_visited, edges_seen, "ok"

    hops_forward = 0
    hops_reverse = 0
    max_forward = (depth + 1) // 2
    max_reverse = depth // 2

    while forward_frontier or reverse_frontier:
        # Budget check (D-07 — "budget_exhausted")
        if len(forward_visited) + len(reverse_visited) >= max_visited:
            return forward_visited | reverse_visited, edges_seen, "budget_exhausted"

        # Pick smaller frontier to expand (same heuristic NetworkX uses)
        expand_forward = (
            forward_frontier
            and hops_forward < max_forward
            and (
                not reverse_frontier
                or len(forward_frontier) <= len(reverse_frontier)
                or hops_reverse >= max_reverse
            )
        )

        if expand_forward:
            next_f: set[str] = set()
            for n in forward_frontier:
                for neighbor in G.neighbors(n):
                    if neighbor not in forward_visited:
                        next_f.add(neighbor)
                        edges_seen.append((n, neighbor))
                        if neighbor in reverse_visited:
                            forward_visited |= next_f
                            return (
                                forward_visited | reverse_visited,
                                edges_seen,
                                "ok",
                            )
            forward_visited |= next_f
            forward_frontier = next_f
            hops_forward += 1
        elif reverse_frontier and hops_reverse < max_reverse:
            next_r: set[str] = set()
            for n in reverse_frontier:
                for neighbor in G.neighbors(n):
                    if neighbor not in reverse_visited:
                        next_r.add(neighbor)
                        edges_seen.append((neighbor, n))  # reversed direction marker
                        if neighbor in forward_visited:
                            reverse_visited |= next_r
                            return (
                                forward_visited | reverse_visited,
                                edges_seen,
                                "ok",
                            )
            reverse_visited |= next_r
            reverse_frontier = next_r
            hops_reverse += 1
        else:
            # Neither frontier can expand further under the depth budget
            break

    return forward_visited | reverse_visited, edges_seen, "frontiers_disjoint"


def _synthesize_targets(
    G: nx.Graph,
    start_nodes: list[str],
    k: int | None = None,
) -> list[str]:
    """Top-K high-degree nodes excluding the start set. For bi-BFS when no explicit target.

    K heuristic per CONTEXT D-06 Claude's Discretion + RESEARCH Open Question #1:
      K = max(3, min(20, int(log2(N)))) when k is None.

    Returns `[]` only if G minus start_nodes is empty — the caller uses this as the
    sentinel to fall back to unidirectional BFS (Pitfall 5: never silently claim
    bidirectional when there is no target pair).
    """
    import math
    start_set = set(start_nodes)
    candidates = [n for n in G.nodes() if n not in start_set]
    if not candidates:
        return []
    if k is None:
        n = G.number_of_nodes()
        if n <= 1:
            return []
        k = max(3, min(20, int(math.log2(n))))
    # Sort by degree descending, tie-break by node id for determinism
    candidates.sort(key=lambda nid: (-G.degree(nid), nid))
    return candidates[:k]


def _dfs(G: nx.Graph, start_nodes: list[str], depth: int) -> tuple[set[str], list[tuple]]:
    visited: set[str] = set()
    edges_seen: list[tuple] = []
    stack = [(n, 0) for n in reversed(start_nodes)]
    while stack:
        node, d = stack.pop()
        if node in visited or d > depth:
            continue
        visited.add(node)
        for neighbor in G.neighbors(node):
            if neighbor not in visited:
                stack.append((neighbor, d + 1))
                edges_seen.append((node, neighbor))
    return visited, edges_seen


def _estimate_tokens_for_layer(n_nodes: int, n_edges: int, layer: int) -> int:
    """Deterministic token estimate for a layered subgraph — no tokenizer dep.

    Layer 1: id + label + community only                -> ~50 tok/node       (CONTEXT D-04)
    Layer 2: L1 + edges + 1-hop neighbor labels         -> ~200 tok/node + ~30 tok/edge
    Layer 3: full attribute serialization               -> ~100 tok/node + ~95 tok/edge
             (calibrated from graphify-out/graph.json: avg 391 B/node / 4 chars/tok)
    """
    if layer == 1:
        return 50 * n_nodes
    if layer == 2:
        return 200 * n_nodes + 30 * n_edges
    # layer == 3 (or any other value) — full attribute dump
    return 100 * n_nodes + 95 * n_edges


def _estimate_cardinality(
    G: nx.Graph,
    start_nodes: list[str],
    depth: int,
    layer: int,
    branching_factor: float,
) -> dict:
    """1-hop BFS probe + geometric extrapolation. Returns {"nodes","edges","tokens"}.

    Accuracy degrades on power-law topologies (hubs vs leaves); D-05 keeps this advisory only.
    Per CONTEXT D-04.
    """
    if depth <= 0:
        return {
            "nodes": len(start_nodes),
            "edges": 0,
            "tokens": _estimate_tokens_for_layer(len(start_nodes), 0, layer),
        }
    one_hop_visited, _one_hop_edges = _bfs(G, start_nodes, 1)
    one_hop_count = len(one_hop_visited)
    if depth == 1:
        est_nodes = one_hop_count
    else:
        est_nodes = min(
            int(len(start_nodes) * (branching_factor ** depth)),
            G.number_of_nodes(),
        )
    est_edges = min(int(est_nodes * branching_factor / 2), G.number_of_edges())
    return {
        "nodes": est_nodes,
        "edges": est_edges,
        "tokens": _estimate_tokens_for_layer(est_nodes, est_edges, layer),
    }


def _subgraph_to_text(
    G: nx.Graph,
    nodes: set[str],
    edges: list[tuple],
    token_budget: int = 2000,
    layer: int = 3,
) -> str:
    """Render subgraph as text, cutting at token_budget (approx 3 chars/token).

    Phase 9.2 D-02/D-04 — `layer` controls output density:
      layer=1 : id + sanitized label + community only         (~50 tok/node, no edges)
      layer=2 : L1 fields + edges + neighbor labels           (~200 tok/node + ~30 tok/edge)
      layer=3 : full attribute serialization (legacy default) (~100 tok/node + ~95 tok/edge)

    Every emitted label goes through sanitize_label(). Degree-descending sort preserved.
    """
    char_budget = token_budget * 3
    lines: list[str] = []
    sorted_nodes = sorted(nodes, key=lambda n: G.degree(n), reverse=True)

    if layer == 1:
        # Compact summary: id, sanitized label, community membership
        for nid in sorted_nodes:
            d = G.nodes[nid]
            label = sanitize_label(d.get("label", nid))
            community = d.get("community", "")
            lines.append(f"NODE {nid} label={label} community={community}")
        # L1: no edges emitted
    elif layer == 2:
        # L1 fields + edges with relation + confidence + neighbor labels
        for nid in sorted_nodes:
            d = G.nodes[nid]
            label = sanitize_label(d.get("label", nid))
            community = d.get("community", "")
            lines.append(f"NODE {nid} label={label} community={community}")
        for u, v in edges:
            if u in nodes and v in nodes:
                ed = G.edges[u, v]
                u_label = sanitize_label(G.nodes[u].get("label", u))
                v_label = sanitize_label(G.nodes[v].get("label", v))
                lines.append(
                    f"EDGE {u_label} --{ed.get('relation', '')} "
                    f"[{ed.get('confidence', '')}]--> {v_label}"
                )
    else:
        # layer == 3 — full attribute dump (LEGACY — exact current behavior preserved)
        for nid in sorted_nodes:
            d = G.nodes[nid]
            line = (
                f"NODE {sanitize_label(d.get('label', nid))} "
                f"[src={d.get('source_file', '')} loc={d.get('source_location', '')} "
                f"community={d.get('community', '')}]"
            )
            lines.append(line)
        for u, v in edges:
            if u in nodes and v in nodes:
                ed = G.edges[u, v]
                line = (
                    f"EDGE {sanitize_label(G.nodes[u].get('label', u))} "
                    f"--{ed.get('relation', '')} [{ed.get('confidence', '')}]--> "
                    f"{sanitize_label(G.nodes[v].get('label', v))}"
                )
                lines.append(line)

    output = "\n".join(lines)
    if len(output) > char_budget:
        output = output[:char_budget] + f"\n... (truncated to ~{token_budget} token budget)"
    return output


def _find_node(G: nx.Graph, label: str) -> list[str]:
    """Return node IDs whose label or ID matches the search term (case-insensitive)."""
    term = label.lower()
    return [nid for nid, d in G.nodes(data=True)
            if term in d.get("label", "").lower() or term == nid.lower()]


# Sentinel for Phase 9.2 D-02 hybrid response format.
# Appears on its own line (preceded + followed by \n) so naive clients see it
# as visually-separated text rather than a parse error (Pitfall 4).
QUERY_GRAPH_META_SENTINEL = "\n---GRAPHIFY-META---\n"


def _run_query_graph(
    G: nx.Graph,
    communities: dict,
    graph_mtime: float,
    branching_factor: float,
    telemetry: dict,
    arguments: dict,
    alias_map: dict[str, str] | None = None,
) -> str:
    """Pure dispatch core for query_graph - no MCP runtime. Returns the full D-02 response string.

    Separated from `_tool_query_graph` so unit tests can exercise the full pipeline
    (cardinality, bi-BFS, layer rendering, continuation-token encode/decode) without
    standing up an MCP stdio server.

    alias_map (Phase 10 D-16): when provided, resolve merged-away node IDs to their
    canonical equivalents before scoring / traversal. The response meta JSON includes
    `resolved_from_alias: {canonical_id: [original_alias, ...]}` listing every alias
    that was redirected to each canonical (multiple aliases may collapse to one
    canonical, so the value is always a list).

    Phase 9.2 dispatch pipeline:
      1. Decode continuation_token if present; short-circuit on graph_changed / malformed.
      2. Score + select start nodes (existing _score_nodes).
      3. If depth >= 2: compute cardinality_estimate; short-circuit on estimate_exceeded.
      4. If depth >= 3: bidirectional BFS (synthesize targets if none); else single-endpoint.
      5. Normalize edges (Pitfall 6 dedup), record telemetry with search_strategy.
      6. Render via _subgraph_to_text(..., layer=layer).
      7. Encode outbound continuation_token for layer < 3.
      8. Emit text_body + SENTINEL + json.dumps(meta).
    """
    question = str(arguments.get("question", ""))
    mode = str(arguments.get("mode", "bfs"))
    depth = max(1, min(int(arguments.get("depth", 3)), 6))
    # D-01: `budget` is preferred; `token_budget` is deprecated alias. Prefer explicit budget.
    budget = int(arguments.get("budget", arguments.get("token_budget", 2000)))
    budget = max(50, min(budget, 100000))
    layer = int(arguments.get("layer", 1))
    if layer not in (1, 2, 3):
        layer = 1
    continuation_token = arguments.get("continuation_token")
    explicit_targets = arguments.get("target_nodes")  # optional; synthesize at depth >=3 if absent

    # Phase 10 D-16: resolve alias-redirects before scoring / traversal.
    # If alias_map is provided (loaded from dedup_report.json at serve() startup),
    # any merged-away node ID in the query is transparently redirected to the canonical.
    # WR-02: keep a list per canonical so multiple aliases collapsing to the same
    # canonical (e.g. ``auth`` and ``auth_svc`` both -> ``authentication_service``)
    # all surface in meta.resolved_from_alias instead of the last-write winning.
    _resolved_aliases: dict[str, list[str]] = {}  # {canonical_id: [original_alias, ...]}
    _effective_alias_map: dict[str, str] = alias_map or {}

    def _resolve_alias(node_id: str) -> str:
        """Return canonical ID for node_id; record redirect if it occurred."""
        canonical = _effective_alias_map.get(node_id)
        if canonical and canonical != node_id:
            aliases = _resolved_aliases.setdefault(canonical, [])
            if node_id not in aliases:
                aliases.append(node_id)
            return canonical
        return node_id

    # Apply alias resolution to explicit seed-node fields passed in arguments.
    # These fields carry specific node IDs (not free-text questions).
    # WR-03: shallow-copy arguments before rewriting so the caller's dict (passed
    # in by _tool_query_graph) is never mutated. Retry / instrumentation that
    # re-reads arguments after dispatch must see the original input.
    arguments = dict(arguments)
    for _alias_field in ("node_id", "source", "target", "seed", "start"):
        if _alias_field in arguments and isinstance(arguments[_alias_field], str):
            arguments[_alias_field] = _resolve_alias(arguments[_alias_field])
    if "seed_nodes" in arguments and isinstance(arguments["seed_nodes"], list):
        arguments["seed_nodes"] = [
            _resolve_alias(n) if isinstance(n, str) else n
            for n in arguments["seed_nodes"]
        ]

    # Phase 9.2 D-03: continuation_token validation at dispatch head.
    prior_visited: set[str] = set()
    if continuation_token:
        decoded, status = _decode_continuation(continuation_token, graph_mtime)
        if status in ("graph_changed", "malformed"):
            meta = {
                "layer": layer,
                "search_strategy": None,
                "status": status if status != "malformed" else "malformed_token",
                "cardinality_estimate": None,
                "continuation_token": None,
            }
            return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        # Restore visited-so-far from prior layer for drill-down; use decoded query.
        prior_visited = set(decoded.get("v", []))
        # Reuse original question from token if not explicitly re-supplied.
        if not question:
            question = str(decoded.get("q", {}).get("question", ""))

    # Existing start-node scoring. _score_nodes returns (score, nid) tuples.
    terms = [t.lower() for t in question.split() if len(t) > 2]
    scored = _score_nodes(G, terms)
    start_nodes = [nid for _, nid in scored[:3]]
    if not start_nodes:
        meta = {
            "layer": layer,
            "search_strategy": None,
            "status": "no_seed_nodes",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        # UAT gap 8: surface alias resolution metadata even on the short-circuit
        # path so agents know which canonical the alias was redirected to.
        # Mirrors the same guard at the happy-path meta construction below.
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Phase 9.2 D-04/D-05: cardinality pre-flight (only for depth >= 2).
    cardinality_estimate: dict | None = None
    if depth >= 2:
        cardinality_estimate = _estimate_cardinality(
            G, start_nodes, depth, layer, branching_factor
        )
        # D-05: abort when estimate > 10x budget. Return estimate + empty result.
        if cardinality_estimate["tokens"] > 10 * budget:
            meta = {
                "layer": layer,
                "search_strategy": None,
                "status": "estimate_exceeded",
                "cardinality_estimate": cardinality_estimate,
                "continuation_token": None,
            }
            return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Phase 9.2 D-06/D-07: bidirectional BFS at depth >= 3 (unconditional).
    status = "ok"
    if depth >= 3:
        if explicit_targets:
            targets = list(explicit_targets)
        else:
            targets = _synthesize_targets(G, start_nodes)
        if targets:
            max_visited = max(10, int(budget / 50))  # L1 density ~50 tok/node as budget proxy
            visited, edges_seen, bi_status = _bidirectional_bfs(
                G, start_nodes, targets, depth=depth, max_visited=max_visited
            )
            search_strategy = "bidirectional"
            status = bi_status
        else:
            # Pitfall 5: no targets -> honest fallback to unidirectional BFS.
            visited, edges_seen = _bfs(G, start_nodes, depth)
            search_strategy = "bfs"
    elif mode == "dfs":
        visited, edges_seen = _dfs(G, start_nodes, depth)
        search_strategy = "dfs"
    else:
        visited, edges_seen = _bfs(G, start_nodes, depth)
        search_strategy = "bfs"

    # Merge prior visited from continuation_token (drill-down case).
    visited = visited | prior_visited

    # Pitfall 6: dedupe edges before recording (normalize to min/max tuples).
    deduped_edges = list({(min(u, v), max(u, v)) for u, v in edges_seen})
    _record_traversal(telemetry, deduped_edges, search_strategy=search_strategy)

    # Render
    text_body = _subgraph_to_text(G, visited, edges_seen, token_budget=budget, layer=layer)

    # Encode outbound continuation_token for layer < 3 (L3 is terminal).
    if layer < 3:
        out_token = _encode_continuation(
            query_params={"question": question, "depth": depth, "mode": mode},
            visited=visited,
            current_layer=layer,
            graph_mtime=graph_mtime,
        )
    else:
        out_token = None

    meta = {
        "layer": layer,
        "search_strategy": search_strategy,
        "status": status,
        "cardinality_estimate": cardinality_estimate,
        "continuation_token": out_token,
    }
    # Phase 10 D-16: include alias redirect provenance when any redirect occurred.
    if _resolved_aliases:
        meta["resolved_from_alias"] = _resolved_aliases
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)


def _filter_blank_stdin() -> None:
    """Filter blank lines from stdin before MCP reads it.

    Some MCP clients (Claude Desktop, etc.) send blank lines between JSON
    messages. The MCP stdio transport tries to parse every line as a
    JSONRPCMessage, so a bare newline triggers a Pydantic ValidationError.
    This installs an OS-level pipe that relays stdin while dropping blanks.
    """
    import os
    import threading

    r_fd, w_fd = os.pipe()
    saved_fd = os.dup(sys.stdin.fileno())

    def _relay() -> None:
        try:
            with open(saved_fd, "rb") as src, open(w_fd, "wb") as dst:
                for line in src:
                    if line.strip():
                        dst.write(line)
                        dst.flush()
        except Exception:
            pass

    threading.Thread(target=_relay, daemon=True).start()
    os.dup2(r_fd, sys.stdin.fileno())
    os.close(r_fd)
    sys.stdin = open(0, "r", closefd=False)


def _run_graph_summary(
    G: nx.Graph,
    communities: dict[int, list[str]],
    snaps_dir: Path,
    arguments: dict,
) -> str:
    """Pure helper for graph_summary MCP tool (Phase 11 SLASH-01).

    Testable without MCP runtime. Returns the full hybrid envelope string.
    """
    budget = int(arguments.get("budget", 500))
    budget = max(50, min(budget, 100000))
    top_n = int(arguments.get("top_n", 10))
    top_n = max(1, min(top_n, 50))

    from .analyze import god_nodes as _god_nodes
    from .snapshot import list_snapshots, load_snapshot
    from .delta import compute_delta

    gods = _god_nodes(G, top_n=top_n)
    snaps = list_snapshots(snaps_dir)

    # Build top communities list (top 5 by size)
    top_communities = []
    sorted_comms = sorted(communities.items(), key=lambda x: len(x[1]), reverse=True)
    for cid, node_ids in sorted_comms[:5]:
        sample_labels = []
        for nid in node_ids[:3]:
            sample_labels.append(G.nodes[nid].get("label", nid) if nid in G.nodes else nid)
        top_communities.append({"id": cid, "size": len(node_ids), "sample": sample_labels})

    # Compute delta from most recent snapshot
    delta_block: dict | None = None
    if len(snaps) >= 1:
        G_prev, comms_prev, _meta_prev = load_snapshot(snaps[-1])
        delta = compute_delta(G_prev, comms_prev, G, communities)
        delta_block = {
            "added_nodes": len(delta["added_nodes"]),
            "removed_nodes": len(delta["removed_nodes"]),
            "added_edges": len(delta["added_edges"]),
            "removed_edges": len(delta["removed_edges"]),
        }
        del G_prev
        del comms_prev
    else:
        delta_block = {"status": "no_prior_snapshot"}

    # Build text_body
    lines = ["## Graph Summary", ""]
    lines.append(f"**Nodes:** {G.number_of_nodes()}  |  **Edges:** {G.number_of_edges()}  |  **Communities:** {len(communities)}")
    lines.append("")
    lines.append("### God Nodes (most connected)")
    for i, n in enumerate(gods, 1):
        lines.append(f"  {i}. {n['label']} — {n['edges']} edges")
    lines.append("")
    lines.append("### Top Communities")
    for c in top_communities:
        sample_str = ", ".join(c["sample"])
        lines.append(f"  Community {c['id']}: {c['size']} nodes — e.g. {sample_str}")
    lines.append("")
    if delta_block and "status" not in delta_block:
        lines.append("### Recent Delta (vs. last snapshot)")
        lines.append(f"  +{delta_block['added_nodes']} nodes  -{delta_block['removed_nodes']} nodes  "
                     f"+{delta_block['added_edges']} edges  -{delta_block['removed_edges']} edges")
    elif delta_block and delta_block.get("status") == "no_prior_snapshot":
        lines.append("### Recent Delta")
        lines.append("  No prior snapshot — this is the first graph build.")

    text_body = "\n".join(lines)
    max_chars = budget * 3
    if len(text_body) > max_chars:
        text_body = text_body[:max_chars] + f"\n... (truncated to ~{budget} token budget)"

    meta: dict = {
        "status": "ok",
        "layer": 1,
        "search_strategy": None,
        "cardinality_estimate": None,
        "continuation_token": None,
        "snapshot_count": len(snaps),
        "god_node_count": len(gods),
        "community_count": len(communities),
        "delta": delta_block,
    }
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)


def _run_connect_topics(
    G: nx.Graph,
    communities: dict[int, list[str]],
    alias_map: dict[str, str],
    arguments: dict,
) -> str:
    """Pure helper for connect_topics MCP tool (Phase 11 SLASH-03).

    Testable without MCP runtime. Returns the full hybrid envelope string.
    Emits two DISTINCT sections: shortest path AND globally surprising bridges.
    The surprising-bridges block is NOT filtered to the A-B path — it is global.
    """
    budget = int(arguments.get("budget", 500))
    budget = max(50, min(budget, 100000))

    # Sanitize inputs (T-11-01-01)
    topic_a_raw = sanitize_label(arguments.get("topic_a", ""))
    topic_b_raw = sanitize_label(arguments.get("topic_b", ""))

    if not topic_a_raw or not topic_b_raw:
        meta: dict = {
            "status": "no_data",
            "layer": 1,
            "search_strategy": "connect",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Alias resolution (Phase 10 D-16)
    _resolved_aliases: dict[str, list[str]] = {}
    _effective_alias_map: dict[str, str] = alias_map or {}

    def _resolve_alias(node_id: str) -> str:
        canonical = _effective_alias_map.get(node_id)
        if canonical and canonical != node_id:
            aliases = _resolved_aliases.setdefault(canonical, [])
            if node_id not in aliases:
                aliases.append(node_id)
            return canonical
        return node_id

    topic_a_id = _resolve_alias(topic_a_raw)
    topic_b_id = _resolve_alias(topic_b_raw)

    # Label resolution
    matches_a = _find_node(G, topic_a_id)
    matches_b = _find_node(G, topic_b_id)

    missing = []
    if not matches_a:
        missing.append("topic_a")
    if not matches_b:
        missing.append("topic_b")
    if missing:
        meta = {
            "status": "entity_not_found",
            "layer": 1,
            "search_strategy": "connect",
            "cardinality_estimate": None,
            "continuation_token": None,
            "missing_endpoints": missing,
        }
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    if len(matches_a) > 1 or len(matches_b) > 1:
        candidates: dict[str, list[dict]] = {}
        if len(matches_a) > 1:
            candidates["topic_a"] = [
                {"id": m, "label": G.nodes[m].get("label", m), "source_file": G.nodes[m].get("source_file", "")}
                for m in matches_a
            ]
        if len(matches_b) > 1:
            candidates["topic_b"] = [
                {"id": m, "label": G.nodes[m].get("label", m), "source_file": G.nodes[m].get("source_file", "")}
                for m in matches_b
            ]
        meta = {
            "status": "ambiguous_entity",
            "layer": 1,
            "search_strategy": "connect",
            "cardinality_estimate": None,
            "continuation_token": None,
            "candidates": candidates,
        }
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    src_id = matches_a[0]
    dst_id = matches_b[0]

    # Compute shortest path
    try:
        path_nodes = nx.shortest_path(G, src_id, dst_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        meta = {
            "status": "no_path",
            "layer": 1,
            "search_strategy": "connect",
            "cardinality_estimate": None,
            "continuation_token": None,
            "topic_a_id": src_id,
            "topic_b_id": dst_id,
        }
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    hops = len(path_nodes) - 1

    # Build path text
    path_segments = []
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        edata = G.edges[u, v]
        rel = edata.get("relation", "")
        conf = edata.get("confidence", "")
        conf_str = f" [{conf}]" if conf else ""
        if i == 0:
            path_segments.append(G.nodes[u].get("label", u))
        path_segments.append(f"--{rel}{conf_str}--> {G.nodes[v].get('label', v)}")

    # Compute globally surprising bridges (NOT filtered to A-B path — global to the graph)
    from .analyze import surprising_connections as _sc
    bridges = _sc(G, communities, top_n=5)

    # Build text_body with two DISTINCT labelled sections (RESEARCH.md Pitfall 4 — do NOT conflate)
    lines = [
        f"## Shortest Path ({hops} hops)",
        "  " + " ".join(path_segments),
        "",
        "## Surprising Bridges (global to the graph, not filtered to the A-B path)",
    ]
    if bridges:
        for b in bridges:
            src_label = G.nodes[b["source"]].get("label", b["source"]) if b["source"] in G.nodes else b["source"]
            tgt_label = G.nodes[b["target"]].get("label", b["target"]) if b["target"] in G.nodes else b["target"]
            rel = b.get("relation", "")
            conf = b.get("confidence", "")
            conf_str = f" [{conf}]" if conf else ""
            lines.append(f"  {src_label} --{rel}{conf_str}--> {tgt_label}")
    else:
        lines.append("  (no surprising bridges detected)")

    text_body = "\n".join(lines)
    max_chars = budget * 3
    if len(text_body) > max_chars:
        text_body = text_body[:max_chars] + f"\n... (truncated to ~{budget} token budget)"

    meta = {
        "status": "ok",
        "layer": 1,
        "search_strategy": "connect",
        "cardinality_estimate": None,
        "continuation_token": None,
        "path_length": hops,
        "surprise_count": len(bridges),
        "surprise_scope": "global",
        "topic_a_id": src_id,
        "topic_b_id": dst_id,
    }
    if _resolved_aliases:
        meta["resolved_from_alias"] = _resolved_aliases
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)



def _run_entity_trace(
    G: "nx.Graph",
    snaps_dir: "Path",
    alias_map: "dict[str, str]",
    arguments: dict,
) -> str:
    """Pure helper for entity_trace MCP tool (Phase 11 SLASH-02).

    Testable without MCP runtime. Returns the full hybrid envelope string.

    Walk graphify-out/snapshots/*.json via list_snapshots(snaps_dir) + load_snapshot()
    with strict memory discipline (only one nx.Graph deserialized at a time — del G_snap
    after extracting scalars). Honours Phase 10 alias-redirect contract (D-16).

    Node-id scheme in tests: nodes are named n0, n1, ..., n{i} with label=f"n{j}".
    Any test that constructs a live G_live tip graph must use the same scheme so
    _find_node can bridge fixture-built snapshots and the live tip.
    """
    from .snapshot import list_snapshots, load_snapshot

    budget = int(arguments.get("budget", 500))
    budget = max(50, min(budget, 100000))

    entity_raw = sanitize_label(str(arguments.get("entity", "")))
    if not entity_raw:
        meta: dict = {
            "status": "no_data",
            "layer": 1,
            "search_strategy": "trace",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Phase 10 D-16: alias resolution — scoped per-call for thread safety.
    _resolved_aliases: dict[str, list[str]] = {}
    _effective_alias_map: dict[str, str] = alias_map or {}

    def _resolve_alias(node_id: str) -> str:
        canonical = _effective_alias_map.get(node_id)
        if canonical and canonical != node_id:
            aliases = _resolved_aliases.setdefault(canonical, [])
            if node_id not in aliases:
                aliases.append(node_id)
            return canonical
        return node_id

    entity_resolved = _resolve_alias(entity_raw)

    # List prior snapshots from snaps_dir.
    snaps = list_snapshots(snaps_dir)

    # Insufficient-history: need at least 1 prior snapshot for a meaningful trace
    # (live G counts as second data point, so threshold is len(snaps) < 1).
    if len(snaps) < 1:
        meta = {
            "status": "insufficient_history",
            "layer": 1,
            "search_strategy": "trace",
            "cardinality_estimate": None,
            "continuation_token": None,
            "snapshots_available": len(snaps),
        }
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Initial resolution on the live graph — check for ambiguity first.
    live_matches = _find_node(G, entity_resolved)
    if len(live_matches) > 1:
        candidates = [
            {
                "id": m,
                "label": G.nodes[m].get("label", m),
                "source_file": G.nodes[m].get("source_file", ""),
            }
            for m in live_matches
        ]
        meta = {
            "status": "ambiguous_entity",
            "layer": 1,
            "search_strategy": "trace",
            "cardinality_estimate": None,
            "continuation_token": None,
            "candidates": candidates,
        }
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Walk snapshot chain with memory discipline: extract scalars then del G_snap.
    timeline: list[dict] = []
    first_seen_ts: "str | None" = None

    for path in snaps:
        G_snap, _comms_snap, meta_snap = load_snapshot(path)
        ts = meta_snap.get("timestamp", path.stem)
        snap_matches = _find_node(G_snap, entity_resolved)
        if snap_matches:
            node_id_snap = snap_matches[0]
            if first_seen_ts is None:
                first_seen_ts = ts
            comm_id_snap = G_snap.nodes[node_id_snap].get("community", -1)
            degree_snap = G_snap.degree(node_id_snap)
            timeline.append({
                "timestamp": ts,
                "community": comm_id_snap,
                "degree": degree_snap,
                "present": True,
            })
        else:
            timeline.append({"timestamp": ts, "present": False})
        del G_snap  # CRITICAL memory discipline: only one graph in memory at a time

    # Check entity existence across all sources (snapshots + live) for entity_not_found.
    if not live_matches and first_seen_ts is None:
        # Entity not found anywhere — no matches in any snapshot and not in live graph.
        meta = {
            "status": "entity_not_found",
            "layer": 1,
            "search_strategy": "trace",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        if _resolved_aliases:
            meta["resolved_from_alias"] = _resolved_aliases
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Append live graph as "tip" data point.
    if live_matches:
        tip_id = live_matches[0]
        if first_seen_ts is None:
            first_seen_ts = "current"
        timeline.append({
            "timestamp": "current",
            "community": G.nodes[tip_id].get("community", -1),
            "degree": G.degree(tip_id),
            "present": True,
        })
    else:
        timeline.append({"timestamp": "current", "present": False})

    # Build text_body: Layer-1 compact timeline.
    entity_label = entity_resolved
    if live_matches:
        entity_label = G.nodes[live_matches[0]].get("label", entity_resolved)

    lines = [f"## Entity Trace: {sanitize_label(entity_label)}", ""]
    lines.append(f"**First seen:** {first_seen_ts}")
    lines.append(f"**Timeline ({len(timeline)} data points):**")
    lines.append("")
    for entry in timeline:
        ts_str = entry["timestamp"]
        if entry.get("present"):
            comm_val = entry["community"]
            deg_val = entry["degree"]
            lines.append(f"  {ts_str}: community={comm_val}, degree={deg_val}")
        else:
            lines.append(f"  {ts_str}: (not present)")

    text_body = "\n".join(lines)
    max_chars = budget * 3
    if len(text_body) > max_chars:
        text_body = text_body[:max_chars] + f"\n... (truncated to ~{budget} token budget)"

    entity_id_out = live_matches[0] if live_matches else entity_resolved
    meta = {
        "status": "ok",
        "layer": 1,
        "search_strategy": "trace",
        "cardinality_estimate": None,
        "continuation_token": None,
        "snapshot_count": len(snaps),
        "first_seen": first_seen_ts,
        "timeline_length": len(timeline),
        "entity_id": entity_id_out,
    }
    if _resolved_aliases:
        meta["resolved_from_alias"] = _resolved_aliases
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)


def _run_drift_nodes(
    G: "nx.Graph",
    snaps_dir: "Path",
    arguments: dict,
) -> str:
    """Pure helper for drift_nodes MCP tool (Phase 11 SLASH-04).

    Testable without MCP runtime. Returns the full hybrid envelope string.

    Walks graphify-out/snapshots/*.json via list_snapshots(snaps_dir) + load_snapshot()
    with strict memory discipline (del G_snap after extracting scalars — Pattern E).
    Computes a trend score per node from community-change count and degree delta,
    returns the top-N drifters as a Layer-1 narrative + meta envelope.
    """
    from .snapshot import list_snapshots, load_snapshot

    budget = int(arguments.get("budget", 500))
    budget = max(50, min(budget, 100000))
    max_snapshots = int(arguments.get("max_snapshots", 10))
    max_snapshots = max(2, min(max_snapshots, 50))
    top_n = int(arguments.get("top_n", 10))
    top_n = max(1, min(top_n, 100))

    snaps = list_snapshots(snaps_dir)

    # Insufficient-history: need at least 1 prior snapshot (live G is the second data point).
    if len(snaps) < 1:
        meta: dict = {
            "status": "insufficient_history",
            "layer": 1,
            "search_strategy": "drift",
            "cardinality_estimate": None,
            "continuation_token": None,
            "snapshots_available": len(snaps),
        }
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Walk the last max_snapshots snapshots with memory discipline (Pattern E).
    # history: {node_id: [(timestamp, community, degree), ...]}
    history: dict[str, list[tuple]] = {}
    for path in snaps[-max_snapshots:]:
        G_snap, _, meta_snap = load_snapshot(path)
        ts = meta_snap.get("timestamp", path.stem)
        for nid, d in G_snap.nodes(data=True):
            history.setdefault(nid, []).append((ts, d.get("community", -1), G_snap.degree(nid)))
        del G_snap  # CRITICAL memory discipline: only one graph in memory at a time

    # Add current live G as the tip data point.
    for nid, d in G.nodes(data=True):
        history.setdefault(nid, []).append(("current", d.get("community", -1), G.degree(nid)))

    # Compute per-node trend score.
    # Only include nodes present in at least 2 data points (ignore noise/transient nodes).
    scored: list[tuple[float, str]] = []
    for nid, entries in history.items():
        if len(entries) < 2:
            continue
        # community_changes: how many distinct communities the node visited (0 = stable, >0 = drifted)
        community_changes = len({c for _, c, _ in entries}) - 1
        # degree_delta: signed centrality change from first to last data point
        degree_delta = entries[-1][2] - entries[0][2]
        # trend_score: simple weighted composition — no new algorithm (D-18)
        trend_score = community_changes * 2 + abs(degree_delta)
        scored.append((trend_score, nid))

    # Sort by trend_score descending; take top_n.
    scored.sort(key=lambda x: x[0], reverse=True)
    top_drifters = scored[:top_n]

    # Build text_body: Layer-1 narrative of top drifting nodes.
    lines = ["## Drifting Nodes", ""]
    for score, nid in top_drifters:
        entries = history[nid]
        label = G.nodes[nid].get("label", nid) if nid in G.nodes else nid
        community_set = {c for _, c, _ in entries}
        community_changes = len(community_set) - 1
        degree_delta = entries[-1][2] - entries[0][2]
        degree_sign = "+" if degree_delta >= 0 else ""
        lines.append(
            f"  {sanitize_label(label)}: community_changes={community_changes}, "
            f"degree_delta={degree_sign}{degree_delta}, score={score:.1f}"
        )
    text_body = "\n".join(lines)
    max_chars = budget * 3
    if len(text_body) > max_chars:
        text_body = text_body[:max_chars] + f"\n... (truncated to ~{budget} token budget)"

    actual_snap_count = min(len(snaps), max_snapshots)
    meta = {
        "status": "ok",
        "layer": 1,
        "search_strategy": "drift",
        "cardinality_estimate": None,
        "continuation_token": None,
        "snapshot_count": actual_snap_count,
        "drift_count": len(top_drifters),
        "nodes_scanned": len(history),
    }
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)


def _run_newly_formed_clusters(
    G: "nx.Graph",
    communities: "dict[int, list[str]]",
    snaps_dir: "Path",
    arguments: dict,
) -> str:
    """Pure helper for newly_formed_clusters MCP tool (Phase 11 SLASH-05).

    Testable without MCP runtime. Returns the full hybrid envelope string.

    Loads the most recent prior snapshot and applies a set-based novelty rule:
    a current community is "new" if NONE of its members appeared in ANY prior community.
    This avoids compute_delta's 4-arg complexity (per D-18 no-new-algorithms constraint).
    """
    from .snapshot import list_snapshots, load_snapshot

    budget = int(arguments.get("budget", 500))
    budget = max(50, min(budget, 100000))

    snaps = list_snapshots(snaps_dir)

    # Insufficient-history: need at least 1 prior snapshot to compute diff against.
    if len(snaps) < 1:
        meta: dict = {
            "status": "insufficient_history",
            "layer": 1,
            "search_strategy": "emerge",
            "cardinality_estimate": None,
            "continuation_token": None,
            "snapshots_available": len(snaps),
        }
        return "" + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    # Load most recent prior snapshot — extract community dict then release graph.
    G_prev, comms_prev, _meta_prev = load_snapshot(snaps[-1])
    del G_prev  # CRITICAL memory discipline: only one graph in memory at a time

    # "New cluster" rule: members have zero overlap with any prior community.
    # A current community is "new" if none of its members appeared in any prior community.
    new_clusters: list[tuple[int, list[str]]] = []
    for c, members in communities.items():
        M_c = set(members)
        overlaps_any_prior = any(bool(M_c & set(P_p)) for P_p in comms_prev.values())
        if not overlaps_any_prior:
            new_clusters.append((c, sorted(members)))

    if len(new_clusters) == 0:
        meta = {
            "status": "no_change",
            "layer": 1,
            "search_strategy": "emerge",
            "cardinality_estimate": None,
            "continuation_token": None,
            "snapshot_count": len(snaps),
            "new_cluster_count": 0,
            "new_cluster_ids": [],
        }
        return (
            "No new clusters formed since the last run. The graph structure is stable."
            + QUERY_GRAPH_META_SENTINEL
            + json.dumps(meta, ensure_ascii=False)
        )

    # Build text_body: one line per new cluster with id, size, representative labels.
    lines = ["## Newly Formed Clusters", ""]
    for c, members in new_clusters:
        # Pick up to 3 representative nodes by degree (highest degree first).
        member_degrees = [(G.degree(m) if m in G.nodes else 0, m) for m in members]
        member_degrees.sort(key=lambda x: x[0], reverse=True)
        reps = [
            G.nodes[m].get("label", m) if m in G.nodes else m
            for _, m in member_degrees[:3]
        ]
        rep_str = ", ".join(sanitize_label(r) for r in reps)
        lines.append(
            f"  Community {c}: {len(members)} members (e.g. {rep_str})"
        )

    text_body = "\n".join(lines)
    max_chars = budget * 3
    if len(text_body) > max_chars:
        text_body = text_body[:max_chars] + f"\n... (truncated to ~{budget} token budget)"

    meta = {
        "status": "ok",
        "layer": 1,
        "search_strategy": "emerge",
        "cardinality_estimate": None,
        "continuation_token": None,
        "snapshot_count": len(snaps),
        "new_cluster_count": len(new_clusters),
        "new_cluster_ids": [c for c, _ in new_clusters],
    }
    return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)


def serve(graph_path: str = "graphify-out/graph.json") -> None:
    """Start the MCP server. Requires pip install mcp."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError as e:
        raise ImportError("mcp not installed. Run: pip install mcp") from e

    G = _load_graph(graph_path)
    communities = _communities_from_graph(G)

    # Sidecar state initialised at server startup (D-03: compaction at startup only)
    _graph_mtime = Path(graph_path).stat().st_mtime if Path(graph_path).exists() else 0.0
    # Phase 9.2 D-04: average branching factor cached at load for cardinality estimation.
    _branching_factor = _compute_branching_factor(G)
    _out_dir = Path(graph_path).parent
    _annotations: list[dict] = _compact_annotations(_out_dir / "annotations.jsonl")
    _agent_edges: list[dict] = _load_agent_edges(_out_dir / "agent-edges.json")
    _telemetry: dict = _load_telemetry(_out_dir / "telemetry.json")
    _alias_map: dict[str, str] = _load_dedup_report(_out_dir)  # Phase 10 D-16
    _session_id = str(uuid.uuid4())
    _dedup_mtime: float = -1.0
    _manifest_sig: tuple[float, ...] | None = None
    _manifest_hash_val: str | None = None

    server = Server("graphify")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return build_mcp_tools()

    def _reload_if_stale() -> None:
        """Reload G and communities if graph.json mtime has changed (D-13).

        Also refreshes the Phase 9.2 branching-factor cache so the cardinality
        estimator reflects the post-rebuild graph topology.
        """
        nonlocal G, communities, _graph_mtime, _branching_factor
        try:
            mtime = os.stat(graph_path).st_mtime
        except OSError:
            return
        if mtime != _graph_mtime:
            G = _load_graph(graph_path)
            communities = _communities_from_graph(G)
            _branching_factor = _compute_branching_factor(G)
            _graph_mtime = mtime

    def _maybe_reload_dedup() -> None:
        nonlocal _alias_map, _dedup_mtime
        p = _out_dir / "dedup_report.json"
        try:
            mt = p.stat().st_mtime if p.exists() else 0.0
        except OSError:
            mt = 0.0
        if mt != _dedup_mtime:
            _alias_map = _load_dedup_report(_out_dir)
            _dedup_mtime = mt

    def _manifest_source_paths() -> list[Path]:
        pkg = Path(__file__).resolve().parent
        return [
            pkg / "mcp_tool_registry.py",
            pkg / "capability.py",
            pkg / "capability_tool_meta.yaml",
        ]

    def _sidecar_paths_for_manifest() -> list[Path]:
        return [
            Path(graph_path),
            _out_dir / "dedup_report.json",
            _out_dir / "telemetry.json",
            _out_dir / "annotations.jsonl",
            _out_dir / "agent-edges.json",
            _out_dir / "enrichment.json",
        ]

    def _manifest_invalidation_tuple() -> tuple[float, ...]:
        t: list[float] = []
        for p in _manifest_source_paths() + _sidecar_paths_for_manifest():
            try:
                t.append(p.stat().st_mtime)
            except OSError:
                t.append(0.0)
        return tuple(t)

    def _get_manifest_hash() -> str:
        nonlocal _manifest_sig, _manifest_hash_val
        sig = _manifest_invalidation_tuple()
        if _manifest_hash_val is not None and _manifest_sig == sig:
            return _manifest_hash_val
        from graphify.capability import build_manifest_dict, canonical_manifest_hash

        h = canonical_manifest_hash(build_manifest_dict())
        _manifest_hash_val = h
        _manifest_sig = sig
        return h

    def _merge_manifest_meta(text: str, manifest_hash: str) -> str:
        if QUERY_GRAPH_META_SENTINEL in text:
            body, rest = text.split(QUERY_GRAPH_META_SENTINEL, 1)
            try:
                meta = json.loads(rest.strip())
            except json.JSONDecodeError:
                meta = {"status": "ok", "meta_parse_error": True}
            if not isinstance(meta, dict):
                meta = {"status": "ok", "meta_shape_error": True}
            meta["manifest_content_hash"] = manifest_hash
            return body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        meta = {"status": "ok", "manifest_content_hash": manifest_hash}
        return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    def _tool_query_graph(arguments: dict) -> str:
        # Phase 9.2 D-02: synchronous dispatch returning str. The hybrid response format
        # (text_body + SENTINEL + json(meta)) is emitted by _run_query_graph. The MCP
        # stdio dispatch table at serve.py:~1073 wraps sync-str returns in TextContent.
        _reload_if_stale()  # NO arguments - reads graph_path from serve() closure
        response = _run_query_graph(
            G=G,
            communities=communities,
            graph_mtime=_graph_mtime,
            branching_factor=_branching_factor,
            telemetry=_telemetry,
            arguments=arguments,
            alias_map=_alias_map,  # Phase 10 D-16
        )
        # _save_telemetry(out_dir, data) - out_dir FIRST, data SECOND. Appends 'telemetry.json'.
        _save_telemetry(_out_dir, _telemetry)
        _check_derived_edges(G, _telemetry, _out_dir, _agent_edges)  # Phase 9.1 scaffolding, unchanged
        return response

    def _tool_get_node(arguments: dict) -> str:
        _reload_if_stale()
        label = arguments["label"].lower()
        matches = [(nid, d) for nid, d in G.nodes(data=True)
                   if label in d.get("label", "").lower() or label == nid.lower()]
        if not matches:
            return f"No node matching '{label}' found."
        nid, d = matches[0]
        staleness = classify_staleness(d)
        extracted_at = d.get("extracted_at", "\u2014")
        source_hash = d.get("source_hash", "\u2014")
        return "\n".join([
            f"Node: {d.get('label', nid)}",
            f"  ID: {nid}",
            f"  Source: {d.get('source_file', '')} {d.get('source_location', '')}",
            f"  Type: {d.get('file_type', '')}",
            f"  Community: {d.get('community', '')}",
            f"  Degree: {G.degree(nid)}",
            f"  Extracted At: {extracted_at}",
            f"  Source Hash: {source_hash}",
            f"  Staleness: {staleness}",
        ])

    def _tool_get_neighbors(arguments: dict) -> str:
        _reload_if_stale()
        label = arguments["label"].lower()
        rel_filter = arguments.get("relation_filter", "").lower()
        matches = _find_node(G, label)
        if not matches:
            return f"No node matching '{label}' found."
        nid = matches[0]
        lines = [f"Neighbors of {G.nodes[nid].get('label', nid)}:"]
        for neighbor in G.neighbors(nid):
            d = G.edges[nid, neighbor]
            rel = d.get("relation", "")
            if rel_filter and rel_filter not in rel.lower():
                continue
            lines.append(f"  --> {G.nodes[neighbor].get('label', neighbor)} [{rel}] [{d.get('confidence', '')}]")
        return "\n".join(lines)

    def _tool_get_community(arguments: dict) -> str:
        _reload_if_stale()
        cid = int(arguments["community_id"])
        nodes = communities.get(cid, [])
        if not nodes:
            return f"Community {cid} not found."
        lines = [f"Community {cid} ({len(nodes)} nodes):"]
        for n in nodes:
            d = G.nodes[n]
            lines.append(f"  {d.get('label', n)} [{d.get('source_file', '')}]")
        return "\n".join(lines)

    def _tool_god_nodes(arguments: dict) -> str:
        _reload_if_stale()
        from .analyze import god_nodes as _god_nodes
        nodes = _god_nodes(G, top_n=int(arguments.get("top_n", 10)))
        lines = ["God nodes (most connected):"]
        lines += [f"  {i}. {n['label']} - {n['edges']} edges" for i, n in enumerate(nodes, 1)]
        return "\n".join(lines)

    def _tool_graph_stats(_: dict) -> str:
        _reload_if_stale()
        confs = [d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True)]
        total = len(confs) or 1
        return (
            f"Nodes: {G.number_of_nodes()}\n"
            f"Edges: {G.number_of_edges()}\n"
            f"Communities: {len(communities)}\n"
            f"EXTRACTED: {round(confs.count('EXTRACTED')/total*100)}%\n"
            f"INFERRED: {round(confs.count('INFERRED')/total*100)}%\n"
            f"AMBIGUOUS: {round(confs.count('AMBIGUOUS')/total*100)}%\n"
        )

    def _tool_shortest_path(arguments: dict) -> str:
        _reload_if_stale()
        src_scored = _score_nodes(G, [t.lower() for t in arguments["source"].split()])
        tgt_scored = _score_nodes(G, [t.lower() for t in arguments["target"].split()])
        if not src_scored:
            return f"No node matching source '{arguments['source']}' found."
        if not tgt_scored:
            return f"No node matching target '{arguments['target']}' found."
        src_nid, tgt_nid = src_scored[0][1], tgt_scored[0][1]
        max_hops = int(arguments.get("max_hops", 8))
        try:
            path_nodes = nx.shortest_path(G, src_nid, tgt_nid)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return f"No path found between '{G.nodes[src_nid].get('label', src_nid)}' and '{G.nodes[tgt_nid].get('label', tgt_nid)}'."
        hops = len(path_nodes) - 1
        if hops > max_hops:
            return f"Path exceeds max_hops={max_hops} ({hops} hops found)."
        segments = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edata = G.edges[u, v]
            rel = edata.get("relation", "")
            conf = edata.get("confidence", "")
            conf_str = f" [{conf}]" if conf else ""
            if i == 0:
                segments.append(G.nodes[u].get("label", u))
            segments.append(f"--{rel}{conf_str}--> {G.nodes[v].get('label', v)}")
        return f"Shortest path ({hops} hops):\n  " + " ".join(segments)

    def _tool_annotate_node(arguments: dict) -> str:
        """Add a free-text annotation to a node. Persisted to annotations.jsonl (T-07-01)."""
        node_id = arguments.get("node_id", "")
        text = arguments.get("text", "")
        peer_id = arguments.get("peer_id", "anonymous")
        record = _make_annotate_record(node_id, text, peer_id, _session_id)
        _append_annotation(_out_dir, record)
        _annotations.append(record)
        return json.dumps(record)

    def _tool_flag_node(arguments: dict) -> str:
        """Flag a node's importance (high/medium/low). Persisted to annotations.jsonl."""
        node_id = arguments.get("node_id", "")
        importance = arguments.get("importance", "")
        peer_id = arguments.get("peer_id", "anonymous")
        try:
            record = _make_flag_record(node_id, importance, peer_id, _session_id)
        except ValueError as exc:
            return str(exc)
        _append_annotation(_out_dir, record)
        _annotations.append(record)
        return json.dumps(record)

    def _tool_add_edge(arguments: dict) -> str:
        """Add an agent-inferred edge. Saved to agent-edges.json; never mutates G (T-07-03)."""
        source = arguments.get("source", "")
        target = arguments.get("target", "")
        relation = arguments.get("relation", "")
        peer_id = arguments.get("peer_id", "anonymous")
        record = _make_edge_record(source, target, relation, peer_id, _session_id)
        _agent_edges.append(record)
        _save_agent_edges(_out_dir, _agent_edges)
        return json.dumps(record)

    def _tool_propose_vault_note(arguments: dict) -> str:
        """Stage a proposed vault note for human review. Writes to graphify-out/proposals/ only (T-07-09)."""
        record = _make_proposal_record(arguments, _session_id)
        _save_proposal(_out_dir, record)
        return json.dumps({"record_id": record["record_id"], "status": "pending"})

    def _tool_get_annotations(arguments: dict) -> str:
        """Return annotations, optionally filtered by peer_id, session_id, or time range."""
        peer_id = arguments.get("peer_id") or None
        session_id = arguments.get("session_id") or None
        time_from = arguments.get("time_from") or None
        time_to = arguments.get("time_to") or None
        results = _filter_annotations(_annotations, peer_id, session_id, time_from, time_to)
        return json.dumps(results)

    def _tool_get_agent_edges(arguments: dict) -> str:
        """Return agent-inferred edges, optionally filtered by peer_id, session_id, or node_id."""
        peer_id = arguments.get("peer_id") or None
        session_id = arguments.get("session_id") or None
        node_id = arguments.get("node_id") or None
        results = _filter_agent_edges(_agent_edges, peer_id, session_id, node_id)
        return json.dumps(results)

    def _tool_graph_summary(arguments: dict) -> str:
        """Phase 11 SLASH-01: full graph-backed summary (god nodes + communities + delta)."""
        _reload_if_stale()
        if not Path(graph_path).exists():
            meta: dict = {
                "status": "no_graph",
                "layer": 1,
                "search_strategy": None,
                "cardinality_estimate": None,
                "continuation_token": None,
            }
            text = "No graph found at graphify-out/graph.json. Run /graphify to build one."
            return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        return _run_graph_summary(G, communities, _out_dir.parent, arguments)

    def _tool_connect_topics(arguments: dict) -> str:
        """Phase 11 SLASH-03: shortest path + globally surprising bridges between two topics."""
        _reload_if_stale()
        if not Path(graph_path).exists():
            meta: dict = {
                "status": "no_graph",
                "layer": 1,
                "search_strategy": "connect",
                "cardinality_estimate": None,
                "continuation_token": None,
            }
            text = "No graph found at graphify-out/graph.json. Run /graphify to build one."
            return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        return _run_connect_topics(G, communities, _alias_map, arguments)

    def _tool_entity_trace(arguments: dict) -> str:
        """Phase 11 SLASH-02: entity evolution timeline across graph snapshots."""
        _reload_if_stale()
        if not Path(graph_path).exists():
            meta: dict = {
                "status": "no_graph",
                "layer": 1,
                "search_strategy": "trace",
                "cardinality_estimate": None,
                "continuation_token": None,
            }
            text = "No graph found at graphify-out/graph.json. Run /graphify to build one."
            return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        return _run_entity_trace(G, _out_dir.parent, _alias_map, arguments)

    def _tool_drift_nodes(arguments: dict) -> str:
        """Phase 11 SLASH-04: per-node trend vectors across snapshot chain."""
        _reload_if_stale()
        if not Path(graph_path).exists():
            meta: dict = {
                "status": "no_graph",
                "layer": 1,
                "search_strategy": "drift",
                "cardinality_estimate": None,
                "continuation_token": None,
            }
            text = "No graph found at graphify-out/graph.json. Run /graphify to build one."
            return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        return _run_drift_nodes(G, _out_dir.parent, arguments)

    def _tool_newly_formed_clusters(arguments: dict) -> str:
        """Phase 11 SLASH-05: communities new in current graph vs. most recent snapshot."""
        _reload_if_stale()
        if not Path(graph_path).exists():
            meta: dict = {
                "status": "no_graph",
                "layer": 1,
                "search_strategy": "emerge",
                "cardinality_estimate": None,
                "continuation_token": None,
            }
            text = "No graph found at graphify-out/graph.json. Run /graphify to build one."
            return text + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)
        return _run_newly_formed_clusters(G, communities, _out_dir.parent, arguments)

    def _file_mtime_or_zero(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    def _enrichment_snapshot_id() -> str | None:
        p = _out_dir / "enrichment.json"
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        sid = data.get("snapshot_id", data.get("version"))
        return str(sid) if sid is not None else None

    def _tool_capability_describe(arguments: dict) -> str:
        """MANIFEST-03: static manifest + live non-secret scalars (T-13-01)."""
        del arguments  # reserved
        _reload_if_stale()
        _maybe_reload_dedup()
        from graphify.capability import build_manifest_dict

        md = build_manifest_dict()
        lines = [
            "## Capability",
            "",
            f"**Tools (manifest):** {len(md.get('CAPABILITY_TOOLS', []))}",
            f"**graphify version:** {md.get('graphify_version', '')}",
            "",
            "## Live graph",
            "",
        ]
        gp = Path(graph_path)
        if gp.exists():
            lines += [
                f"- nodes: {G.number_of_nodes()}",
                f"- edges: {G.number_of_edges()}",
                f"- communities: {len(communities)}",
            ]
        else:
            lines.append("- (no graph loaded)")
        lines += ["", "## Sidecars", ""]
        lines.append(f"- alias_map entries: {len(_alias_map)}")
        lines.append(f"- enrichment snapshot_id: {json.dumps(_enrichment_snapshot_id())}")
        for label, rel in [
            ("graph.json", None),
            ("dedup_report.json", "dedup_report.json"),
            ("telemetry.json", "telemetry.json"),
            ("annotations.jsonl", "annotations.jsonl"),
            ("agent-edges.json", "agent-edges.json"),
            ("enrichment.json", "enrichment.json"),
        ]:
            p = gp if rel is None else _out_dir / rel
            lines.append(f"- {label} mtime: {_file_mtime_or_zero(p)}")
        text_body = "\n".join(lines)
        meta = {
            "status": "ok",
            "layer": 0,
            "search_strategy": "capability_describe",
            "cardinality_estimate": None,
            "continuation_token": None,
        }
        return text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta, ensure_ascii=False)

    _handlers = {
        "query_graph": _tool_query_graph,
        "get_node": _tool_get_node,
        "get_neighbors": _tool_get_neighbors,
        "get_community": _tool_get_community,
        "god_nodes": _tool_god_nodes,
        "graph_stats": _tool_graph_stats,
        "shortest_path": _tool_shortest_path,
        "annotate_node": _tool_annotate_node,
        "flag_node": _tool_flag_node,
        "add_edge": _tool_add_edge,
        "propose_vault_note": _tool_propose_vault_note,
        "get_annotations": _tool_get_annotations,
        "get_agent_edges": _tool_get_agent_edges,
        "graph_summary": _tool_graph_summary,
        "connect_topics": _tool_connect_topics,
        "entity_trace": _tool_entity_trace,
        "drift_nodes": _tool_drift_nodes,
        "newly_formed_clusters": _tool_newly_formed_clusters,
        "capability_describe": _tool_capability_describe,
    }

    _reg_tools = build_mcp_tools()
    if {t.name for t in _reg_tools} != set(_handlers.keys()):
        raise RuntimeError("MCP tool registry and _handlers keys must match (MANIFEST-05)")

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        _maybe_reload_dedup()
        mh = _get_manifest_hash()
        handler = _handlers.get(name)
        if not handler:
            return [types.TextContent(type="text", text=_merge_manifest_meta(f"Unknown tool: {name}", mh))]
        try:
            raw = handler(arguments)
            return [types.TextContent(type="text", text=_merge_manifest_meta(raw, mh))]
        except Exception as exc:
            return [types.TextContent(type="text", text=_merge_manifest_meta(f"Error executing {name}: {exc}", mh))]

    import asyncio

    async def main() -> None:
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    _filter_blank_stdin()
    asyncio.run(main())


if __name__ == "__main__":
    graph_path = sys.argv[1] if len(sys.argv) > 1 else "graphify-out/graph.json"
    serve(graph_path)
