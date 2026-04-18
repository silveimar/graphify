# MCP tool definitions — single source for serve.list_tools and capability manifest (Phase 13).
from __future__ import annotations


def query_graph_input_schema() -> dict:
    """JSON Schema for the `query_graph` MCP tool input.

    Module-level so tests can assert shape without starting MCP. Phase 9.2 D-01.
    """
    return {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Natural language question or keyword search",
            },
            "mode": {
                "type": "string",
                "enum": ["bfs", "dfs"],
                "default": "bfs",
                "description": "bfs=broad context, dfs=trace a specific path (depth < 3 only)",
            },
            "depth": {
                "type": "integer",
                "default": 3,
                "minimum": 1,
                "maximum": 6,
                "description": "Traversal depth (1-6). At depth >= 3 bidirectional BFS auto-activates.",
            },
            "budget": {
                "type": "integer",
                "default": 2000,
                "minimum": 50,
                "maximum": 100000,
                "description": "Total token ceiling for the response",
            },
            "layer": {
                "type": "integer",
                "default": 1,
                "enum": [1, 2, 3],
                "description": "1=compact summary, 2=edges+neighbors, 3=full",
            },
            "continuation_token": {
                "type": "string",
                "description": "Opaque drill-down token from a prior Layer 1 or 2 response",
            },
            "token_budget": {
                "type": "integer",
                "default": 2000,
                "description": "DEPRECATED - alias for `budget`. Kept for backward compatibility.",
            },
        },
        "required": ["question"],
    }


def build_mcp_tools():
    """Return MCP Tool list — must match serve._handlers keys (MANIFEST-05)."""
    from mcp import types

    return [
        types.Tool(
            name="query_graph",
            description="Search the knowledge graph using BFS or DFS. Returns relevant nodes and edges as text context.",
            inputSchema=query_graph_input_schema(),
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
                    "note_type": {"type": "string", "default": "note", "description": "Note type (e.g. note, person, source)"},
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
        types.Tool(
            name="graph_summary",
            description="Return a full graph-backed summary: god nodes, top communities, and delta from the most recent snapshot. Used by the /context slash command.",
            inputSchema={"type": "object", "properties": {
                "top_n": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "budget": {"type": "integer", "default": 500, "minimum": 50, "maximum": 100000},
            }},
        ),
        types.Tool(
            name="connect_topics",
            description="Return the shortest path between two topics PLUS a separate block of globally surprising cross-community bridges (NOT filtered to the A-B path). Used by the /connect slash command.",
            inputSchema={"type": "object", "properties": {
                "topic_a": {"type": "string"},
                "topic_b": {"type": "string"},
                "budget": {"type": "integer", "default": 500},
            }, "required": ["topic_a", "topic_b"]},
        ),
        types.Tool(
            name="entity_trace",
            description="Return the evolution of a named entity across graph snapshots: first-seen, per-snapshot community and degree, current status. Used by the /trace slash command.",
            inputSchema={"type": "object", "properties": {
                "entity": {"type": "string"},
                "budget": {"type": "integer", "default": 500},
            }, "required": ["entity"]},
        ),
        types.Tool(
            name="drift_nodes",
            description="Return nodes whose community or centrality has trended consistently across recent snapshots. Used by the /drift slash command.",
            inputSchema={"type": "object", "properties": {
                "top_n": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
                "max_snapshots": {"type": "integer", "default": 10, "minimum": 2, "maximum": 50},
                "budget": {"type": "integer", "default": 500},
            }},
        ),
        types.Tool(
            name="newly_formed_clusters",
            description="Return communities that are new in the current graph compared to the most recent prior snapshot. Used by the /emerge slash command.",
            inputSchema={"type": "object", "properties": {
                "budget": {"type": "integer", "default": 500},
            }},
        ),
        types.Tool(
            name="capability_describe",
            description=(
                "Describe graphify MCP capability: static manifest summary merged with live graph "
                "and sidecar freshness (non-secret aggregates only)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


def tool_names_ordered() -> list[str]:
    """Stable ordered tool names for manifest and assertions."""
    return [t.name for t in build_mcp_tools()]
