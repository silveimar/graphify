# MCP stdio server - exposes graph query tools to Claude and other agents
from __future__ import annotations
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


def _record_traversal(telemetry: dict, edges: list[tuple]) -> None:
    """Increment traversal counters for each edge. Keys normalized as min:max. Per D-02."""
    counters = telemetry.setdefault("counters", {})
    for u, v in edges:
        key = f"{min(u, v)}:{max(u, v)}"
        counters[key] = counters.get(key, 0) + 1


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


def _subgraph_to_text(G: nx.Graph, nodes: set[str], edges: list[tuple], token_budget: int = 2000) -> str:
    """Render subgraph as text, cutting at token_budget (approx 3 chars/token)."""
    char_budget = token_budget * 3
    lines = []
    for nid in sorted(nodes, key=lambda n: G.degree(n), reverse=True):
        d = G.nodes[nid]
        line = f"NODE {sanitize_label(d.get('label', nid))} [src={d.get('source_file', '')} loc={d.get('source_location', '')} community={d.get('community', '')}]"
        lines.append(line)
    for u, v in edges:
        if u in nodes and v in nodes:
            d = G.edges[u, v]
            line = f"EDGE {sanitize_label(G.nodes[u].get('label', u))} --{d.get('relation', '')} [{d.get('confidence', '')}]--> {sanitize_label(G.nodes[v].get('label', v))}"
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
    _out_dir = Path(graph_path).parent
    _annotations: list[dict] = _compact_annotations(_out_dir / "annotations.jsonl")
    _agent_edges: list[dict] = _load_agent_edges(_out_dir / "agent-edges.json")
    _telemetry: dict = _load_telemetry(_out_dir / "telemetry.json")
    _session_id = str(uuid.uuid4())

    server = Server("graphify")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="query_graph",
                description="Search the knowledge graph using BFS or DFS. Returns relevant nodes and edges as text context.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Natural language question or keyword search"},
                        "mode": {"type": "string", "enum": ["bfs", "dfs"], "default": "bfs",
                                 "description": "bfs=broad context, dfs=trace a specific path"},
                        "depth": {"type": "integer", "default": 3, "description": "Traversal depth (1-6)"},
                        "token_budget": {"type": "integer", "default": 2000, "description": "Max output tokens"},
                    },
                    "required": ["question"],
                },
            ),
            types.Tool(
                name="get_node",
                description="Get full details for a specific node by label or ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"label": {"type": "string", "description": "Node label or ID to look up"}},
                    "required": ["label"],
                },
            ),
            types.Tool(
                name="get_neighbors",
                description="Get all direct neighbors of a node with edge details.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "relation_filter": {"type": "string", "description": "Optional: filter by relation type"},
                    },
                    "required": ["label"],
                },
            ),
            types.Tool(
                name="get_community",
                description="Get all nodes in a community by community ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"community_id": {"type": "integer", "description": "Community ID (0-indexed by size)"}},
                    "required": ["community_id"],
                },
            ),
            types.Tool(
                name="god_nodes",
                description="Return the most connected nodes - the core abstractions of the knowledge graph.",
                inputSchema={"type": "object", "properties": {"top_n": {"type": "integer", "default": 10}}},
            ),
            types.Tool(
                name="graph_stats",
                description="Return summary statistics: node count, edge count, communities, confidence breakdown.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="shortest_path",
                description="Find the shortest path between two concepts in the knowledge graph.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source concept label or keyword"},
                        "target": {"type": "string", "description": "Target concept label or keyword"},
                        "max_hops": {"type": "integer", "default": 8, "description": "Maximum hops to consider"},
                    },
                    "required": ["source", "target"],
                },
            ),
            types.Tool(
                name="annotate_node",
                description="Add a free-text annotation to a node. Persisted across server restarts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string", "description": "ID of the node to annotate"},
                        "text": {"type": "string", "description": "Annotation text"},
                        "peer_id": {"type": "string", "description": "Peer identifier (default: anonymous)"},
                    },
                    "required": ["node_id", "text"],
                },
            ),
            types.Tool(
                name="flag_node",
                description="Flag a node's importance level. Persisted across server restarts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string", "description": "ID of the node to flag"},
                        "importance": {"type": "string", "enum": ["high", "medium", "low"], "description": "Importance level"},
                        "peer_id": {"type": "string", "description": "Peer identifier (default: anonymous)"},
                    },
                    "required": ["node_id", "importance"],
                },
            ),
            types.Tool(
                name="add_edge",
                description="Add an agent-inferred edge between two nodes. Stored in agent-edges.json sidecar; never modifies graph.json.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "Source node ID"},
                        "target": {"type": "string", "description": "Target node ID"},
                        "relation": {"type": "string", "description": "Edge relation type"},
                        "peer_id": {"type": "string", "description": "Peer identifier (default: anonymous)"},
                    },
                    "required": ["source", "target", "relation"],
                },
            ),
            types.Tool(
                name="propose_vault_note",
                description="Stage a proposed vault note for human approval. Does NOT write to the vault — only to graphify-out/proposals/.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Note title"},
                        "note_type": {"type": "string", "default": "note", "description": "Note type (e.g., note, person, source)"},
                        "body_markdown": {"type": "string", "description": "Full markdown content for the note body"},
                        "suggested_folder": {"type": "string", "description": "Suggested vault folder path"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the note"},
                        "rationale": {"type": "string", "description": "Why the agent proposes this note"},
                        "peer_id": {"type": "string", "default": "anonymous"},
                    },
                    "required": ["title", "body_markdown"],
                },
            ),
            types.Tool(
                name="get_annotations",
                description="Query stored annotations, optionally filtered by peer, session, or time range.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "peer_id": {"type": "string", "description": "Filter by peer identifier"},
                        "session_id": {"type": "string", "description": "Filter by session ID"},
                        "time_from": {"type": "string", "description": "ISO-8601 lower bound (inclusive)"},
                        "time_to": {"type": "string", "description": "ISO-8601 upper bound (inclusive)"},
                    },
                },
            ),
            types.Tool(
                name="get_agent_edges",
                description=(
                    "Query agent-inferred edges from agent-edges.json, optionally filtered "
                    "by peer_id, session_id, or node_id (matches source or target)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "peer_id": {"type": "string", "description": "Filter by peer identifier"},
                        "session_id": {"type": "string", "description": "Filter by session ID"},
                        "node_id": {"type": "string", "description": "Filter edges involving a specific node (source or target)"},
                    },
                },
            ),
        ]

    def _reload_if_stale() -> None:
        """Reload G and communities if graph.json mtime has changed (D-13)."""
        nonlocal G, communities, _graph_mtime
        try:
            mtime = os.stat(graph_path).st_mtime
        except OSError:
            return
        if mtime != _graph_mtime:
            G = _load_graph(graph_path)
            communities = _communities_from_graph(G)
            _graph_mtime = mtime

    def _tool_query_graph(arguments: dict) -> str:
        _reload_if_stale()
        question = arguments["question"]
        mode = arguments.get("mode", "bfs")
        depth = min(int(arguments.get("depth", 3)), 6)
        budget = int(arguments.get("token_budget", 2000))
        terms = [t.lower() for t in question.split() if len(t) > 2]
        scored = _score_nodes(G, terms)
        start_nodes = [nid for _, nid in scored[:3]]
        if not start_nodes:
            return "No matching nodes found."
        nodes, edges = _dfs(G, start_nodes, depth) if mode == "dfs" else _bfs(G, start_nodes, depth)
        _record_traversal(_telemetry, edges)
        _save_telemetry(_out_dir, _telemetry)
        header = f"Traversal: {mode.upper()} depth={depth} | Start: {[G.nodes[n].get('label', n) for n in start_nodes]} | {len(nodes)} nodes found\n\n"
        return header + _subgraph_to_text(G, nodes, edges, budget)

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
    }

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        handler = _handlers.get(name)
        if not handler:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            return [types.TextContent(type="text", text=handler(arguments))]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"Error executing {name}: {exc}")]

    import asyncio

    async def main() -> None:
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    _filter_blank_stdin()
    asyncio.run(main())


if __name__ == "__main__":
    graph_path = sys.argv[1] if len(sys.argv) > 1 else "graphify-out/graph.json"
    serve(graph_path)
