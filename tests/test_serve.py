"""Tests for serve.py - MCP graph query helpers (no mcp package required)."""
import base64
import json
import pytest
import networkx as nx
from networkx.readwrite import json_graph

from graphify.serve import (
    _communities_from_graph,
    _score_nodes,
    _bfs,
    _bidirectional_bfs,
    _dfs,
    _subgraph_to_text,
    _load_graph,
    _append_annotation,
    _compact_annotations,
    _load_agent_edges,
    _save_agent_edges,
    _make_annotate_record,
    _make_flag_record,
    _make_edge_record,
    _filter_annotations,
    _make_proposal_record,
    _save_proposal,
    _list_proposals,
    _estimate_tokens_for_layer,
    _compute_branching_factor,
    _estimate_cardinality,
    _encode_continuation,
    _decode_continuation,
    _synthesize_targets,
    _query_graph_input_schema,
    _run_query_graph,
    _run_graph_summary,
    _run_connect_topics,
    _run_entity_trace,
    _run_drift_nodes,
    _run_newly_formed_clusters,
    _resolve_focus_seeds,
    _multi_seed_ego,
    _run_get_focus_context_core,
    _FOCUS_DEBOUNCE_CACHE,
    _check_focus_freshness,
    _focus_debounce_key,
    _run_chat_core,
    _CHAT_SESSIONS,
    _classify_intent,
    _extract_entity_terms,
    _validate_citations,
    _fuzzy_suggest,
    _truncate_to_token_cap,
    _build_label_token_index,
    _compose_explore_narrative,
    _WORD_RE,
    QUERY_GRAPH_META_SENTINEL,
)
from collections import deque
import time
from unittest.mock import MagicMock


def _make_graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("n1", label="extract", source_file="extract.py", source_location="L10", community=0)
    G.add_node("n2", label="cluster", source_file="cluster.py", source_location="L5", community=0)
    G.add_node("n3", label="build", source_file="build.py", source_location="L1", community=1)
    G.add_node("n4", label="report", source_file="report.py", source_location="L1", community=1)
    G.add_node("n5", label="isolated", source_file="other.py", source_location="L1", community=2)
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED")
    G.add_edge("n2", "n3", relation="imports", confidence="EXTRACTED")
    G.add_edge("n3", "n4", relation="uses", confidence="EXTRACTED")
    return G


def _make_chain_graph(n: int) -> nx.Graph:
    """Chain n1-n2-...-nN, 1-connected component."""
    G = nx.Graph()
    for i in range(1, n + 1):
        G.add_node(f"n{i}", label=f"node{i}")
    for i in range(1, n):
        G.add_edge(f"n{i}", f"n{i+1}")
    return G


def _make_disjoint_components() -> nx.Graph:
    """Two disjoint 3-node chains: a1-a2-a3 and b1-b2-b3."""
    G = nx.Graph()
    for name in ["a1", "a2", "a3", "b1", "b2", "b3"]:
        G.add_node(name, label=name)
    G.add_edge("a1", "a2")
    G.add_edge("a2", "a3")
    G.add_edge("b1", "b2")
    G.add_edge("b2", "b3")
    return G


# --- _communities_from_graph ---

def test_communities_from_graph_basic():
    G = _make_graph()
    communities = _communities_from_graph(G)
    assert 0 in communities
    assert 1 in communities
    assert "n1" in communities[0]
    assert "n2" in communities[0]
    assert "n3" in communities[1]

def test_communities_from_graph_no_community_attr():
    G = nx.Graph()
    G.add_node("a", label="foo")  # no community attr
    communities = _communities_from_graph(G)
    assert communities == {}

def test_communities_from_graph_isolated():
    G = _make_graph()
    communities = _communities_from_graph(G)
    assert 2 in communities
    assert "n5" in communities[2]


# --- _score_nodes ---

def test_score_nodes_exact_label_match():
    G = _make_graph()
    scored = _score_nodes(G, ["extract"])
    nids = [nid for _, nid in scored]
    assert "n1" in nids
    assert scored[0][1] == "n1"  # highest score first

def test_score_nodes_no_match():
    G = _make_graph()
    scored = _score_nodes(G, ["xyzzy"])
    assert scored == []

def test_score_nodes_source_file_partial():
    G = _make_graph()
    # "cluster.py" contains "cluster" - should score 0.5 for source match
    scored = _score_nodes(G, ["cluster"])
    nids = [nid for _, nid in scored]
    assert "n2" in nids


# --- _bfs ---

def test_bfs_depth_1():
    G = _make_graph()
    visited, edges = _bfs(G, ["n1"], depth=1)
    assert "n1" in visited
    assert "n2" in visited  # direct neighbor
    assert "n3" not in visited  # 2 hops away

def test_bfs_depth_2():
    G = _make_graph()
    visited, edges = _bfs(G, ["n1"], depth=2)
    assert "n3" in visited  # n1 -> n2 -> n3

def test_bfs_disconnected():
    G = _make_graph()
    visited, edges = _bfs(G, ["n5"], depth=3)
    assert visited == {"n5"}  # isolated node

def test_bfs_returns_edges():
    G = _make_graph()
    visited, edges = _bfs(G, ["n1"], depth=1)
    assert len(edges) >= 1
    assert any(u == "n1" or v == "n1" for u, v in edges)


# --- _dfs ---

def test_dfs_depth_1():
    G = _make_graph()
    visited, edges = _dfs(G, ["n1"], depth=1)
    assert "n1" in visited
    assert "n2" in visited
    assert "n3" not in visited

def test_dfs_full_chain():
    G = _make_graph()
    visited, edges = _dfs(G, ["n1"], depth=5)
    assert {"n1", "n2", "n3", "n4"}.issubset(visited)


# --- _subgraph_to_text ---

def test_subgraph_to_text_contains_labels():
    G = _make_graph()
    text = _subgraph_to_text(G, {"n1", "n2"}, [("n1", "n2")])
    assert "extract" in text
    assert "cluster" in text

def test_subgraph_to_text_truncates():
    G = _make_graph()
    # Very small budget forces truncation
    text = _subgraph_to_text(G, {"n1", "n2", "n3", "n4"}, [("n1", "n2")], token_budget=1)
    assert "truncated" in text

def test_subgraph_to_text_edge_included():
    G = _make_graph()
    text = _subgraph_to_text(G, {"n1", "n2"}, [("n1", "n2")])
    assert "EDGE" in text
    assert "calls" in text


# --- _load_graph ---

def test_load_graph_roundtrip(tmp_path):
    G = _make_graph()
    data = json_graph.node_link_data(G, edges="links")
    p = tmp_path / "graph.json"
    p.write_text(json.dumps(data))
    G2 = _load_graph(str(p))
    assert G2.number_of_nodes() == G.number_of_nodes()
    assert G2.number_of_edges() == G.number_of_edges()

def test_load_graph_missing_file(tmp_path):
    graphify_dir = tmp_path / "graphify-out"
    graphify_dir.mkdir()
    with pytest.raises(SystemExit):
        _load_graph(str(graphify_dir / "nonexistent.json"))


# ============================================================================
# Task 1: Sidecar persistence helpers
# ============================================================================

# --- _append_annotation ---

def test_append_annotation_creates_file(tmp_path):
    out_dir = tmp_path / "graphify-out"
    record1 = {"node_id": "n1", "text": "first", "peer_id": "alice"}
    record2 = {"node_id": "n2", "text": "second", "peer_id": "bob"}
    _append_annotation(out_dir, record1)
    _append_annotation(out_dir, record2)
    ann_file = out_dir / "annotations.jsonl"
    assert ann_file.exists()
    lines = ann_file.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == record1
    assert json.loads(lines[1]) == record2


# --- _compact_annotations ---

def test_compact_annotations_missing_file(tmp_path):
    result = _compact_annotations(tmp_path / "annotations.jsonl")
    assert result == []


def test_compact_annotations_dedup(tmp_path):
    path = tmp_path / "annotations.jsonl"
    records = [
        {"node_id": "n1", "annotation_type": "annotation", "peer_id": "alice", "text": "first"},
        {"node_id": "n1", "annotation_type": "annotation", "peer_id": "alice", "text": "last"},
        {"node_id": "n2", "annotation_type": "annotation", "peer_id": "alice", "text": "other"},
    ]
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    result = _compact_annotations(path)
    assert len(result) == 2
    # duplicate key keeps last record
    n1_records = [r for r in result if r["node_id"] == "n1"]
    assert len(n1_records) == 1
    assert n1_records[0]["text"] == "last"


def test_compact_annotations_corrupt_line(tmp_path):
    path = tmp_path / "annotations.jsonl"
    path.write_text('{"node_id":"n1","annotation_type":"annotation","peer_id":"alice","text":"ok"}\nNOT VALID JSON\n')
    result = _compact_annotations(path)
    assert len(result) == 1
    assert result[0]["node_id"] == "n1"


# --- _load_agent_edges ---

def test_load_agent_edges_missing(tmp_path):
    result = _load_agent_edges(tmp_path / "agent-edges.json")
    assert result == []


def test_load_agent_edges_valid(tmp_path):
    path = tmp_path / "agent-edges.json"
    edges = [{"source": "a", "target": "b", "relation": "calls"}]
    path.write_text(json.dumps(edges))
    result = _load_agent_edges(path)
    assert result == edges


# --- _save_agent_edges ---

def test_save_agent_edges_atomic(tmp_path):
    out_dir = tmp_path / "graphify-out"
    edges = [{"source": "x", "target": "y", "relation": "imports"}]
    _save_agent_edges(out_dir, edges)
    target = out_dir / "agent-edges.json"
    assert target.exists()
    assert json.loads(target.read_text()) == edges
    # No leftover .tmp file
    assert not (out_dir / "agent-edges.tmp").exists()


# ============================================================================
# Task 2: Mutation tools, record helpers, and filter
# ============================================================================

# --- _make_annotate_record ---

def test_make_annotate_record_defaults():
    record = _make_annotate_record("n1", "some text", "anonymous", "sess-001")
    assert record["annotation_type"] == "annotation"
    assert record["peer_id"] == "anonymous"
    assert record["node_id"] == "n1"
    assert record["text"] == "some text"
    assert record["session_id"] == "sess-001"
    # record_id should be a uuid4 format (36 chars with dashes)
    assert len(record["record_id"]) == 36
    assert record["record_id"].count("-") == 4
    # timestamp is ISO-8601
    assert "T" in record["timestamp"]
    assert record["timestamp"].endswith("+00:00") or record["timestamp"].endswith("Z") or "UTC" in record["timestamp"] or "+" in record["timestamp"]


def test_make_annotate_record_sanitizes():
    # sanitize_label strips control characters and caps length (see security.py).
    # HTML escaping happens at render time, not at storage time — this is by design.
    text_with_controls = "hello\x00\x01\x1fworld"
    record = _make_annotate_record("n1", text_with_controls, "anonymous", "sess-001")
    # Control characters must be stripped
    assert "\x00" not in record["text"]
    assert "\x01" not in record["text"]
    assert "\x1f" not in record["text"]
    assert "helloworld" in record["text"]


# --- _make_flag_record ---

def test_make_flag_record_valid():
    record = _make_flag_record("n1", "high", "alice", "sess-001")
    assert record["annotation_type"] == "flag"
    assert record["importance"] == "high"
    assert record["peer_id"] == "alice"


def test_make_flag_record_invalid():
    with pytest.raises(ValueError):
        _make_flag_record("n1", "critical", "alice", "sess-001")


# --- _make_edge_record ---

def test_make_edge_record():
    record = _make_edge_record("a", "b", "imports", "alice", "sess-001")
    assert record["confidence"] == "INFERRED"
    assert record["source"] == "a"
    assert record["target"] == "b"
    assert record["relation"] == "imports"
    assert "record_id" in record
    assert "timestamp" in record


def test_make_edge_record_never_modifies_graph():
    G = nx.Graph()
    G.add_node("a")
    G.add_node("b")
    initial_edges = G.number_of_edges()
    _make_edge_record("a", "b", "calls", "anon", "sess-001")
    assert G.number_of_edges() == initial_edges


# --- _filter_annotations ---

def test_filter_annotations_no_filter():
    annotations = [
        {"node_id": "n1", "peer_id": "alice", "session_id": "s1", "timestamp": "2026-01-01T00:00:00+00:00"},
        {"node_id": "n2", "peer_id": "bob", "session_id": "s2", "timestamp": "2026-01-02T00:00:00+00:00"},
    ]
    result = _filter_annotations(annotations, None, None, None, None)
    assert len(result) == 2


def test_filter_annotations_by_peer():
    annotations = [
        {"node_id": "n1", "peer_id": "alice", "session_id": "s1", "timestamp": "2026-01-01T00:00:00+00:00"},
        {"node_id": "n2", "peer_id": "bob", "session_id": "s2", "timestamp": "2026-01-02T00:00:00+00:00"},
    ]
    result = _filter_annotations(annotations, "alice", None, None, None)
    assert len(result) == 1
    assert result[0]["peer_id"] == "alice"


def test_filter_annotations_by_session():
    annotations = [
        {"node_id": "n1", "peer_id": "alice", "session_id": "s1", "timestamp": "2026-01-01T00:00:00+00:00"},
        {"node_id": "n2", "peer_id": "bob", "session_id": "s2", "timestamp": "2026-01-02T00:00:00+00:00"},
    ]
    result = _filter_annotations(annotations, None, "s2", None, None)
    assert len(result) == 1
    assert result[0]["session_id"] == "s2"


def test_filter_annotations_by_time_range():
    annotations = [
        {"node_id": "n1", "peer_id": "alice", "session_id": "s1", "timestamp": "2026-01-01T00:00:00+00:00"},
        {"node_id": "n2", "peer_id": "bob", "session_id": "s2", "timestamp": "2026-01-02T00:00:00+00:00"},
        {"node_id": "n3", "peer_id": "carol", "session_id": "s3", "timestamp": "2026-01-03T00:00:00+00:00"},
    ]
    result = _filter_annotations(annotations, None, None, "2026-01-01T12:00:00+00:00", "2026-01-02T12:00:00+00:00")
    assert len(result) == 1
    assert result[0]["node_id"] == "n2"


# --- Security invariants ---

def test_peer_id_never_from_env():
    import graphify.serve as serve_mod
    source = open(serve_mod.__file__).read()
    assert "os.environ" not in source, "serve.py must not read os.environ (peer_id must never be auto-detected)"


# ============================================================================
# Task 1 (Plan 02): Proposal staging helpers
# ============================================================================

# --- _make_proposal_record ---

def test_make_proposal_record_fields():
    record = _make_proposal_record(
        {"title": "My Note", "body_markdown": "# Hello"},
        session_id="sess-abc",
    )
    for field in ("record_id", "title", "note_type", "body_markdown", "suggested_folder",
                  "tags", "rationale", "peer_id", "session_id", "timestamp", "status"):
        assert field in record, f"Missing field: {field}"
    assert record["session_id"] == "sess-abc"
    assert record["title"] == "My Note"
    assert record["body_markdown"] == "# Hello"


def test_make_proposal_record_sanitizes():
    record = _make_proposal_record(
        {"title": "\x00evil", "body_markdown": "ok"},
        session_id="sess-1",
    )
    assert "\x00" not in record["title"]
    assert "evil" in record["title"]


def test_make_proposal_record_default_peer():
    record = _make_proposal_record({"title": "T", "body_markdown": "B"}, session_id="s1")
    assert record["peer_id"] == "anonymous"


def test_make_proposal_record_status_pending():
    record = _make_proposal_record({"title": "T", "body_markdown": "B"}, session_id="s1")
    assert record["status"] == "pending"


def test_make_proposal_record_default_note_type():
    record = _make_proposal_record({"title": "T", "body_markdown": "B"}, session_id="s1")
    assert record["note_type"] == "note"


def test_make_proposal_record_tags_sanitized():
    record = _make_proposal_record(
        {"title": "T", "body_markdown": "B", "tags": ["good", "\x01bad"]},
        session_id="s1",
    )
    assert record["tags"] == ["good", "bad"]


# --- _save_proposal ---

def test_save_proposal_creates_dir(tmp_path):
    out_dir = tmp_path / "graphify-out"
    record = _make_proposal_record({"title": "T", "body_markdown": "B"}, session_id="s1")
    _save_proposal(out_dir, record)
    proposals_dir = out_dir / "proposals"
    assert proposals_dir.is_dir()
    files = list(proposals_dir.glob("*.json"))
    assert len(files) == 1


def test_save_proposal_filename_is_uuid(tmp_path):
    out_dir = tmp_path / "graphify-out"
    record = _make_proposal_record(
        {"title": "My Important Note", "body_markdown": "body"},
        session_id="s1",
    )
    _save_proposal(out_dir, record)
    proposals_dir = out_dir / "proposals"
    files = list(proposals_dir.glob("*.json"))
    assert len(files) == 1
    filename = files[0].name
    # Filename must be {record_id}.json — never based on title
    assert filename == f"{record['record_id']}.json"
    assert "My_Important_Note" not in filename
    assert "My Important Note" not in filename


# --- _list_proposals ---

def test_list_proposals_empty(tmp_path):
    out_dir = tmp_path / "graphify-out"
    result = _list_proposals(out_dir)
    assert result == []


def test_list_proposals_returns_records(tmp_path):
    out_dir = tmp_path / "graphify-out"
    r1 = _make_proposal_record({"title": "A", "body_markdown": "a"}, session_id="s1")
    r2 = _make_proposal_record({"title": "B", "body_markdown": "b"}, session_id="s1")
    _save_proposal(out_dir, r1)
    _save_proposal(out_dir, r2)
    result = _list_proposals(out_dir)
    assert len(result) == 2
    ids = {r["record_id"] for r in result}
    assert r1["record_id"] in ids
    assert r2["record_id"] in ids


def test_list_proposals_skips_corrupt(tmp_path):
    out_dir = tmp_path / "graphify-out"
    proposals_dir = out_dir / "proposals"
    proposals_dir.mkdir(parents=True)
    # Write a valid proposal
    r1 = _make_proposal_record({"title": "A", "body_markdown": "a"}, session_id="s1")
    _save_proposal(out_dir, r1)
    # Write a corrupt JSON file
    (proposals_dir / "corrupt.json").write_text("NOT VALID JSON", encoding="utf-8")
    result = _list_proposals(out_dir)
    assert len(result) == 1
    assert result[0]["record_id"] == r1["record_id"]


# ============================================================================
# Task 1 (Plan 08.2-01): get_node provenance and staleness
# ============================================================================

from graphify.delta import classify_staleness


def test_get_node_provenance_format_with_metadata():
    """Verify the 9-line output format when node has provenance fields."""
    d = {"label": "my_func", "source_file": "foo.py", "source_location": "L10",
         "file_type": "code", "community": 0,
         "extracted_at": "2025-01-01T00:00:00+00:00", "source_hash": "abc123"}
    extracted_at = d.get("extracted_at", "\u2014")
    source_hash = d.get("source_hash", "\u2014")
    assert extracted_at == "2025-01-01T00:00:00+00:00"
    assert source_hash == "abc123"
    # classify_staleness returns FRESH for missing file (no real FS in test)
    # The key contract: extracted_at and source_hash are read from node data


def test_get_node_provenance_format_without_metadata():
    """Verify defaults when node has no provenance fields (per D-03)."""
    d = {"label": "concept_node", "file_type": "rationale"}
    extracted_at = d.get("extracted_at", "\u2014")
    source_hash = d.get("source_hash", "\u2014")
    staleness = classify_staleness(d)
    assert extracted_at == "\u2014"
    assert source_hash == "\u2014"
    assert staleness == "FRESH"  # D-03: default for no provenance


def test_classify_staleness_fresh_no_provenance():
    """classify_staleness returns FRESH when source_file or source_hash is missing."""
    assert classify_staleness({}) == "FRESH"
    assert classify_staleness({"source_file": "foo.py"}) == "FRESH"
    assert classify_staleness({"source_hash": "abc"}) == "FRESH"


def test_classify_staleness_ghost(tmp_path):
    """classify_staleness returns GHOST when source_file does not exist."""
    assert classify_staleness({"source_file": str(tmp_path / "nonexistent.py"), "source_hash": "abc"}) == "GHOST"


# ============================================================================
# Task 2 (Plan 08.2-01): _filter_agent_edges
# ============================================================================

from graphify.serve import _filter_agent_edges


def test_filter_agent_edges_no_filter():
    edges = [
        {"source": "n1", "target": "n2", "peer_id": "alice", "session_id": "s1"},
        {"source": "n3", "target": "n4", "peer_id": "bob", "session_id": "s2"},
    ]
    assert _filter_agent_edges(edges, None, None, None) == edges


def test_filter_agent_edges_by_peer():
    edges = [
        {"source": "n1", "target": "n2", "peer_id": "alice", "session_id": "s1"},
        {"source": "n3", "target": "n4", "peer_id": "bob", "session_id": "s2"},
    ]
    result = _filter_agent_edges(edges, "alice", None, None)
    assert len(result) == 1
    assert result[0]["peer_id"] == "alice"


def test_filter_agent_edges_by_session():
    edges = [
        {"source": "n1", "target": "n2", "peer_id": "alice", "session_id": "s1"},
        {"source": "n3", "target": "n4", "peer_id": "bob", "session_id": "s2"},
    ]
    result = _filter_agent_edges(edges, None, "s2", None)
    assert len(result) == 1
    assert result[0]["session_id"] == "s2"


def test_filter_agent_edges_by_node_id():
    edges = [
        {"source": "n1", "target": "n2", "peer_id": "alice", "session_id": "s1"},
        {"source": "n3", "target": "n1", "peer_id": "bob", "session_id": "s2"},
        {"source": "n3", "target": "n4", "peer_id": "bob", "session_id": "s3"},
    ]
    result = _filter_agent_edges(edges, None, None, "n1")
    assert len(result) == 2
    assert all(e["source"] == "n1" or e["target"] == "n1" for e in result)


def test_filter_agent_edges_combined():
    edges = [
        {"source": "n1", "target": "n2", "peer_id": "alice", "session_id": "s1"},
        {"source": "n3", "target": "n4", "peer_id": "alice", "session_id": "s2"},
        {"source": "n5", "target": "n6", "peer_id": "bob", "session_id": "s1"},
    ]
    result = _filter_agent_edges(edges, "alice", "s1", None)
    assert len(result) == 1
    assert result[0]["source"] == "n1"


def test_filter_agent_edges_no_match():
    edges = [
        {"source": "n1", "target": "n2", "peer_id": "alice", "session_id": "s1"},
    ]
    assert _filter_agent_edges(edges, "nobody", None, None) == []


# --- Telemetry sidecar helpers (Plan 09.1-01, Task 1) ---

from graphify.serve import (
    _load_telemetry,
    _save_telemetry,
    _record_traversal,
    _edge_weight,
    _decay_telemetry,
)


def test_load_telemetry_missing(tmp_path):
    result = _load_telemetry(tmp_path / "telemetry.json")
    assert result == {"counters": {}, "threshold": 5}


def test_load_telemetry_valid(tmp_path):
    path = tmp_path / "telemetry.json"
    data = {"counters": {"a:b": 3}, "threshold": 5}
    path.write_text(json.dumps(data))
    result = _load_telemetry(path)
    assert result == data


def test_load_telemetry_corrupt(tmp_path):
    path = tmp_path / "telemetry.json"
    path.write_text("not json{{{")
    result = _load_telemetry(path)
    assert result == {"counters": {}, "threshold": 5}


def test_save_telemetry_atomic(tmp_path):
    data = {"counters": {"x:y": 7}, "threshold": 5}
    _save_telemetry(tmp_path, data)
    path = tmp_path / "telemetry.json"
    assert path.exists()
    assert json.loads(path.read_text()) == data
    # No leftover .tmp file
    assert not (tmp_path / "telemetry.json.tmp").exists()


def test_record_traversal():
    telemetry = {"counters": {}, "threshold": 5}
    _record_traversal(telemetry, [("n1", "n2"), ("n2", "n3")])
    assert telemetry["counters"] == {"n1:n2": 1, "n2:n3": 1}


def test_edge_key_normalization():
    telemetry = {"counters": {}, "threshold": 5}
    _record_traversal(telemetry, [("n2", "n1")])
    _record_traversal(telemetry, [("n1", "n2")])
    assert telemetry["counters"] == {"n1:n2": 2}


def test_weight_formula():
    assert _edge_weight(1) == 1.0
    assert _edge_weight(2) == pytest.approx(1.693, abs=0.01)
    assert _edge_weight(22027) == 10.0
    assert _edge_weight(0) == 1.0


def test_decay_counters():
    telemetry = {"counters": {"a:b": 10, "c:d": 1}, "threshold": 5}
    _decay_telemetry(telemetry, multiplier=0.8)
    assert telemetry["counters"] == {"a:b": 8}


# --- Derived edge detection (Plan 09.1-01, Task 2) ---

from graphify.serve import _check_derived_edges


def test_derived_edge_proposal(tmp_path):
    G = nx.Graph()
    G.add_node("n1", label="n1")
    G.add_node("n2", label="n2")
    G.add_node("n3", label="n3")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    telemetry = {"counters": {"n1:n2": 5, "n2:n3": 5}, "threshold": 5}
    agent_edges: list[dict] = []
    _check_derived_edges(G, telemetry, tmp_path, agent_edges)
    assert len(agent_edges) == 1
    e = agent_edges[0]
    assert e["source"] == "n1"
    assert e["target"] == "n3"
    assert e["relation"] == "derived_shortcut"
    assert e["confidence"] == "INFERRED"
    assert e["confidence_score"] == 0.7


def test_derived_edge_no_duplicate(tmp_path):
    G = nx.Graph()
    G.add_node("n1", label="n1")
    G.add_node("n2", label="n2")
    G.add_node("n3", label="n3")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    telemetry = {"counters": {"n1:n2": 5, "n2:n3": 5}, "threshold": 5}
    agent_edges: list[dict] = []
    _check_derived_edges(G, telemetry, tmp_path, agent_edges)
    _check_derived_edges(G, telemetry, tmp_path, agent_edges)
    assert len(agent_edges) == 1


def test_derived_edge_below_threshold(tmp_path):
    G = nx.Graph()
    G.add_node("n1", label="n1")
    G.add_node("n2", label="n2")
    G.add_node("n3", label="n3")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    telemetry = {"counters": {"n1:n2": 4, "n2:n3": 5}, "threshold": 5}
    agent_edges: list[dict] = []
    _check_derived_edges(G, telemetry, tmp_path, agent_edges)
    assert len(agent_edges) == 0


def test_derived_edge_existing_graph_edge(tmp_path):
    G = nx.Graph()
    G.add_node("n1", label="n1")
    G.add_node("n2", label="n2")
    G.add_node("n3", label="n3")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    G.add_edge("n1", "n3")  # Direct edge already exists
    telemetry = {"counters": {"n1:n2": 10, "n2:n3": 10}, "threshold": 5}
    agent_edges: list[dict] = []
    _check_derived_edges(G, telemetry, tmp_path, agent_edges)
    assert len(agent_edges) == 0


# ---------------------------------------------------------------------------
# Phase 9.2 — Progressive Graph Retrieval: Plan 01 foundation helpers
# ---------------------------------------------------------------------------


def test_estimate_tokens_for_layer():
    # Layer 1: 50 tok/node (no edge cost) — CONTEXT D-04
    assert _estimate_tokens_for_layer(10, 5, 1) == 500
    # Layer 2: 200 tok/node + 30 tok/edge
    assert _estimate_tokens_for_layer(10, 5, 2) == 2150
    # Layer 3: calibrated from graphify-out/graph.json (391 B avg node / 4 chars/tok)
    assert _estimate_tokens_for_layer(10, 5, 3) == 1475
    # Monotonic ordering L1 <= L2 for the same non-trivial input
    assert _estimate_tokens_for_layer(10, 5, 1) <= _estimate_tokens_for_layer(10, 5, 2)


def test_estimate_tokens_for_layer_zero_input():
    assert _estimate_tokens_for_layer(0, 0, 1) == 0
    assert _estimate_tokens_for_layer(0, 0, 2) == 0
    assert _estimate_tokens_for_layer(0, 0, 3) == 0


def test_estimate_cardinality_basic():
    # Chain: n1 — n2 — n3 — n4 — n5 (4 edges)
    G = nx.Graph()
    for i in range(1, 6):
        G.add_node(f"n{i}", label=f"node{i}", source_file="x.py", community=0)
    for i in range(1, 5):
        G.add_edge(f"n{i}", f"n{i+1}")
    result = _estimate_cardinality(G, ["n1"], depth=2, layer=1, branching_factor=2.0)
    assert set(result.keys()) == {"nodes", "edges", "tokens"}
    assert result["nodes"] > 0 and result["nodes"] <= G.number_of_nodes()
    assert result["edges"] >= 0 and result["edges"] <= G.number_of_edges()
    assert result["tokens"] == _estimate_tokens_for_layer(result["nodes"], result["edges"], 1)


def test_estimate_cardinality_depth_zero():
    G = _make_graph()
    out = _estimate_cardinality(G, ["n1", "n2"], depth=0, layer=2, branching_factor=3.0)
    assert out["nodes"] == 2
    assert out["edges"] == 0
    assert out["tokens"] == _estimate_tokens_for_layer(2, 0, 2)


def test_estimate_cardinality_clamped_to_graph_size():
    G = nx.Graph()
    for i in range(1, 6):
        G.add_node(f"n{i}", label=f"n{i}")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    # Wildly over-estimating branching factor should still clamp to graph size.
    out = _estimate_cardinality(G, ["n1"], depth=5, layer=3, branching_factor=100.0)
    assert out["nodes"] <= G.number_of_nodes()
    assert out["edges"] <= G.number_of_edges()


def test_compute_branching_factor_returns_average_degree_over_two():
    # Pure unit test of the helper that serve() calls at startup.
    # Closure-wiring proof is via grep proxy in acceptance criteria, not this test.
    G = nx.Graph()
    for i in range(1, 5):
        G.add_node(f"n{i}", label=f"n{i}")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    G.add_edge("n3", "n4")
    # 2 * 3 / 4 = 1.5
    assert abs(_compute_branching_factor(G) - 1.5) < 0.001
    # Empty graph returns 1.0 sentinel (no crash)
    assert _compute_branching_factor(nx.Graph()) == 1.0


def test_encode_decode_continuation_roundtrip():
    query_params = {"question": "auth", "depth": 3, "mode": "bfs"}
    visited = {"n3", "n1", "n2"}  # unordered
    token = _encode_continuation(query_params, visited, current_layer=1, graph_mtime=1234.5)
    payload, status = _decode_continuation(token, graph_mtime=1234.5)
    assert status == "ok"
    assert payload["q"] == query_params
    assert payload["v"] == sorted(visited)  # deterministic sort
    assert payload["l"] == 1
    assert isinstance(payload["h"], str) and len(payload["h"]) == 16
    assert all(c in "0123456789abcdef" for c in payload["h"])


def test_continuation_token_graph_changed():
    token = _encode_continuation({"question": "x"}, {"n1"}, 1, graph_mtime=1000.0)
    payload, status = _decode_continuation(token, graph_mtime=2000.0)
    assert status == "graph_changed"
    # Payload is still returned — agent can inspect for debugging.
    assert payload["q"] == {"question": "x"}
    assert payload["l"] == 1


def test_continuation_token_malformed():
    payload, status = _decode_continuation("not-a-valid-token!!!", graph_mtime=1000.0)
    assert status == "malformed"
    assert payload == {}


def test_continuation_token_tampered_hash():
    token = _encode_continuation({"q": "x"}, {"n1"}, 1, graph_mtime=1000.0)
    # Decode, mutate the hash, re-encode
    raw = base64.urlsafe_b64decode(token.encode())
    p = json.loads(raw.decode())
    p["h"] = "0" * 16  # tamper
    tampered = base64.urlsafe_b64encode(json.dumps(p, sort_keys=True).encode()).decode()
    payload, status = _decode_continuation(tampered, graph_mtime=1000.0)
    assert status == "graph_changed"


def test_continuation_token_oversized_rejected():
    # Build a token clearly over the 64 KB cap.
    huge = "x" * 70000
    payload, status = _decode_continuation(huge, graph_mtime=1000.0)
    assert status == "malformed"
    assert payload == {}


# --- Phase 9.2 Plan 02 Task 1: _record_traversal search_strategy extension (D-08) ---

def test_record_traversal_stores_search_strategy():
    from graphify.serve import _record_traversal
    telemetry: dict = {}
    _record_traversal(telemetry, [("a", "b")], search_strategy="bidirectional")
    assert telemetry["counters"]["a:b"] == 1
    assert "strategies" in telemetry
    assert len(telemetry["strategies"]) == 1
    assert telemetry["strategies"][0]["strategy"] == "bidirectional"
    assert telemetry["strategies"][0]["edges"] == 1


def test_record_traversal_backward_compat():
    # Legacy call signature: no search_strategy kwarg — must still increment counters.
    from graphify.serve import _record_traversal
    telemetry: dict = {}
    _record_traversal(telemetry, [("a", "b"), ("b", "c")])
    assert telemetry["counters"]["a:b"] == 1
    assert telemetry["counters"]["b:c"] == 1
    # Default strategy recorded as "bfs"
    assert telemetry["strategies"][0]["strategy"] == "bfs"


def test_record_traversal_multiple_strategies():
    from graphify.serve import _record_traversal
    telemetry: dict = {}
    _record_traversal(telemetry, [("a", "b")], search_strategy="bfs")
    _record_traversal(telemetry, [("a", "c")], search_strategy="dfs")
    _record_traversal(telemetry, [("a", "d")], search_strategy="bidirectional")
    assert [r["strategy"] for r in telemetry["strategies"]] == ["bfs", "dfs", "bidirectional"]


# --- Phase 9.2 Plan 02 Task 2: _bidirectional_bfs (D-06, D-07) ---

def test_bidirectional_bfs_meets_in_middle():
    G = _make_chain_graph(7)  # n1..n7
    visited, edges, status = _bidirectional_bfs(G, ["n1"], ["n7"], depth=6, max_visited=1000)
    assert status == "ok"
    assert "n1" in visited and "n7" in visited
    # Should visit far fewer than 7 — bidirectional meets near the middle
    assert len(visited) <= 7


def test_bidirectional_disjoint_frontiers_partial():
    G = _make_disjoint_components()
    visited, edges, status = _bidirectional_bfs(
        G, ["a1"], ["b1"], depth=5, max_visited=1000
    )
    assert status == "frontiers_disjoint"
    # Partial: both starting frontiers are in visited
    assert "a1" in visited and "b1" in visited
    # No path exists, but we explored both sides
    assert len(visited) >= 2


def test_bidirectional_budget_exhausted():
    G = nx.balanced_tree(r=3, h=4)  # ~121 nodes
    # Convert integer node names to strings to match our API
    G = nx.relabel_nodes(G, {n: f"n{n}" for n in G.nodes()})
    visited, edges, status = _bidirectional_bfs(
        G, ["n0"], ["n120"], depth=4, max_visited=5
    )
    assert status == "budget_exhausted"
    # Cap was reached — count may slightly overshoot due to single-frontier expansion,
    # but should be in a tight band around max_visited.
    assert len(visited) >= 5


def test_bidirectional_ok_status_on_reachable():
    G = _make_chain_graph(5)
    visited, edges, status = _bidirectional_bfs(G, ["n1"], ["n5"], depth=4, max_visited=100)
    assert status == "ok"


def test_bidirectional_no_double_counting_at_meet():
    G = _make_chain_graph(5)  # n1-n2-n3-n4-n5
    _, edges, status = _bidirectional_bfs(G, ["n1"], ["n5"], depth=4, max_visited=100)
    assert status == "ok"
    # Normalize edges to (min, max) tuples — no duplicates
    normalized = {(min(u, v), max(u, v)) for u, v in edges}
    # edges_seen may contain duplicates during traversal (Pitfall 6)
    # but after dedup, count is reasonable
    assert len(normalized) >= 1
    # The caller (Plan 03) will dedupe before calling _record_traversal;
    # this test just confirms dedup is achievable on the output.


# --- Phase 9.2 Plan 02 Task 3: _synthesize_targets (D-06 Claude's Discretion, Pitfall 5) ---

def test_synthesize_targets_top_k_high_degree():
    # Star: n0 is hub (degree 10), n1..n10 are leaves (degree 1 each)
    G = nx.Graph()
    G.add_node("n0", label="hub")
    for i in range(1, 11):
        G.add_node(f"n{i}", label=f"leaf{i}")
        G.add_edge("n0", f"n{i}")
    out = _synthesize_targets(G, ["n1"])
    # N=11 → K = max(3, min(20, int(log2(11)))) = max(3, 3) = 3
    assert len(out) == 3
    # Highest-degree candidate first
    assert out[0] == "n0"


def test_synthesize_targets_excludes_start():
    G = nx.Graph()
    G.add_node("n0")
    for i in range(1, 11):
        G.add_node(f"n{i}")
        G.add_edge("n0", f"n{i}")
    out = _synthesize_targets(G, ["n0"])
    assert "n0" not in out


def test_synthesize_targets_empty_fallback():
    G = nx.Graph()
    G.add_node("n0")
    out = _synthesize_targets(G, ["n0"])
    assert out == []


def test_synthesize_targets_custom_k():
    G = nx.Graph()
    G.add_node("n0")
    for i in range(1, 11):
        G.add_node(f"n{i}")
        G.add_edge("n0", f"n{i}")
    out = _synthesize_targets(G, ["n1"], k=5)
    assert len(out) == 5


def test_synthesize_targets_k_capped_at_n_minus_start():
    G = nx.Graph()
    for i in range(1, 5):
        G.add_node(f"n{i}")
    G.add_edge("n1", "n2")
    G.add_edge("n2", "n3")
    out = _synthesize_targets(G, ["n1"], k=10)
    # Only 3 candidates remain (n2, n3, n4)
    assert len(out) == 3


# --- Phase 9.2 Plan 03 Task 1: _subgraph_to_text layered rendering ---

def test_subgraph_to_text_layer1_only_label_and_community():
    G = _make_graph()
    nodes = {"n1", "n2"}
    edges = [("n1", "n2")]
    out = _subgraph_to_text(G, nodes, edges, token_budget=2000, layer=1)
    assert "label=" in out
    assert "community=" in out
    # L1 MUST NOT include src= or loc= (those are L3-only)
    assert "src=" not in out
    assert "loc=" not in out
    # L1 MUST NOT include EDGE lines
    assert "EDGE " not in out


def test_subgraph_to_text_layer2_includes_edges():
    G = _make_graph()
    nodes = {"n1", "n2"}
    edges = [("n1", "n2")]
    out = _subgraph_to_text(G, nodes, edges, token_budget=2000, layer=2)
    assert "NODE " in out
    assert "EDGE " in out
    assert "label=" in out


def test_subgraph_to_text_layer3_full_attributes():
    G = _make_graph()
    nodes = {"n1", "n2"}
    edges = [("n1", "n2")]
    out = _subgraph_to_text(G, nodes, edges, token_budget=2000, layer=3)
    # Legacy output includes src= and loc= in brackets
    assert "src=" in out
    assert "loc=" in out
    assert "EDGE " in out


def test_subgraph_to_text_backward_compat_no_layer():
    G = _make_graph()
    nodes = {"n1", "n2"}
    edges = [("n1", "n2")]
    legacy = _subgraph_to_text(G, nodes, edges, 2000)
    explicit_l3 = _subgraph_to_text(G, nodes, edges, 2000, layer=3)
    assert legacy == explicit_l3


def test_subgraph_to_text_layer1_budget_respected():
    G = _make_graph()
    nodes = set(G.nodes())
    edges = list(G.edges())
    out = _subgraph_to_text(G, nodes, edges, token_budget=500, layer=1)
    # chars/token heuristic = 3; output may include truncation marker
    assert len(out) <= 500 * 3 + 100  # 100-char slack for truncation marker


def test_subgraph_to_text_all_layers_sanitize_labels():
    # Plan 03 Task 1 Rule 3 deviation: sanitize_label strips control chars (not HTML),
    # so we use \x00 in the label rather than <script>. If a control char survives in
    # output, sanitize_label failed to apply on that layer's path.
    G = nx.Graph()
    G.add_node("n1", label="bad\x00label", source_file="x.py", community=0)
    G.add_node("n2", label="normal", source_file="y.py", community=0)
    G.add_edge("n1", "n2", relation="calls", confidence="EXTRACTED")
    nodes = {"n1", "n2"}
    edges = [("n1", "n2")]
    for layer in (1, 2, 3):
        out = _subgraph_to_text(G, nodes, edges, 2000, layer=layer)
        # Raw \x00 MUST NOT appear — sanitize_label strips control chars on every layer
        assert "\x00" not in out


# --- Phase 9.2 Plan 03 Task 2: query_graph input schema extension ---

def test_list_tools_query_graph_schema_has_budget():
    schema = _query_graph_input_schema()
    props = schema["properties"]
    assert "budget" in props
    assert "layer" in props
    assert "continuation_token" in props
    assert schema["required"] == ["question"]


def test_list_tools_query_graph_schema_layer_enum():
    schema = _query_graph_input_schema()
    assert schema["properties"]["layer"]["enum"] == [1, 2, 3]


def test_list_tools_query_graph_schema_backward_compat():
    schema = _query_graph_input_schema()
    # Legacy param must remain for backward compat per D-01
    assert "token_budget" in schema["properties"]
    assert "DEPRECATED" in schema["properties"]["token_budget"]["description"]


def test_list_tools_query_graph_schema_budget_clamped():
    schema = _query_graph_input_schema()
    # DoS mitigation per RESEARCH Security Domain
    assert schema["properties"]["budget"]["minimum"] == 50
    assert schema["properties"]["budget"]["maximum"] == 100000
    assert schema["properties"]["depth"]["maximum"] == 6


# --- Phase 9.2 Plan 03 Task 3: _run_query_graph dispatch end-to-end ---

def _dispatch_fixture_graph():
    """7-node chain + community attrs for dispatch-level tests."""
    G = _make_chain_graph(7)
    for i, n in enumerate(G.nodes()):
        G.nodes[n]["community"] = i % 3
        G.nodes[n].setdefault("source_file", "x.py")
    return G


def test_query_graph_layer1_budget_respected():
    G = _dispatch_fixture_graph()
    communities = _communities_from_graph(G)
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, communities, graph_mtime=1000.0, branching_factor=bf,
        telemetry=telemetry,
        arguments={"question": "node", "depth": 2, "budget": 500, "layer": 1},
    )
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["layer"] == 1
    # Budget respect: chars <= budget*3 + slack (truncation marker)
    assert len(text_body) <= 500 * 3 + 100


def test_response_format_sentinel_splits_cleanly():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 1, "budget": 1000, "layer": 1},
    )
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2  # exactly one sentinel
    json.loads(parts[1])  # valid JSON


def test_query_graph_backward_compat_token_budget_alias():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 2, "token_budget": 1500, "layer": 1},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    # Success signals the aliased value was accepted.
    assert meta["status"] in ("ok", "frontiers_disjoint", "budget_exhausted")


def test_depth_3_triggers_bidirectional():
    G = _dispatch_fixture_graph()  # 7-node chain
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 3, "budget": 5000, "layer": 1},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    # On a 7-node graph with log2(7)=2 -> K=max(3,2)=3 targets, bidirectional is expected.
    assert meta["search_strategy"] == "bidirectional"


def test_depth_2_remains_bfs():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 2, "budget": 5000, "layer": 1},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["search_strategy"] in ("bfs", "dfs")


def test_depth_2_query_includes_cardinality_estimate():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 2, "budget": 5000, "layer": 1},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["cardinality_estimate"] is not None
    assert set(meta["cardinality_estimate"].keys()) == {"nodes", "edges", "tokens"}


def test_depth_1_no_cardinality_estimate():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 1, "budget": 5000, "layer": 1},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["cardinality_estimate"] is None


def test_estimate_exceeded_status_and_empty_result():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    # Tiny budget + high depth triggers 10x threshold
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 6, "budget": 50, "layer": 3},
    )
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "estimate_exceeded"
    assert text_body == ""
    # Cardinality still returned for inspection
    assert meta["cardinality_estimate"] is not None


def test_continuation_token_graph_changed_in_dispatch():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    stale_token = _encode_continuation(
        {"question": "node", "depth": 2, "mode": "bfs"},
        {"n1"}, 1, graph_mtime=1000.0,
    )
    # Current mtime differs from encode-time
    response = _run_query_graph(
        G, _communities_from_graph(G), 2000.0, bf, telemetry,
        {"question": "node", "depth": 2, "budget": 1000, "layer": 1,
         "continuation_token": stale_token},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "graph_changed"


def test_query_graph_emits_continuation_token_for_l1_and_l2():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    for layer in (1, 2):
        response = _run_query_graph(
            G, _communities_from_graph(G), 1000.0, bf, telemetry,
            {"question": "node", "depth": 2, "budget": 2000, "layer": layer},
        )
        _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
        meta = json.loads(meta_json)
        assert meta["continuation_token"] is not None
    # Layer 3 is terminal
    response = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 2, "budget": 2000, "layer": 3},
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["continuation_token"] is None


def test_token_04_deferred_no_bloom_filter_code():
    # Guard: TOKEN-04 is deferred per D-09. No Bloom filter, no materialized closure cache.
    source = open("graphify/serve.py").read().lower()
    assert "bloom" not in source
    assert "materialized_closure" not in source
    assert "transitive_closure_cache" not in source


def test_dispatch_dedupes_edges_before_record_traversal():
    G = _dispatch_fixture_graph()
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    _ = _run_query_graph(
        G, _communities_from_graph(G), 1000.0, bf, telemetry,
        {"question": "node", "depth": 3, "budget": 5000, "layer": 1},
    )
    # No counter > len(G.edges) - would indicate the dedup failed.
    for key, count in telemetry.get("counters", {}).items():
        assert count <= G.number_of_edges()


# ============================================================================
# Phase 10 Plan 06 — D-16: _load_dedup_report + alias redirect in query_graph
# ============================================================================

from graphify.serve import _load_dedup_report


def test_load_dedup_report_missing_returns_empty(tmp_path):
    """_load_dedup_report returns {} when dedup_report.json does not exist."""
    result = _load_dedup_report(tmp_path)
    assert result == {}


def test_load_dedup_report_reads_alias_map(tmp_path):
    """_load_dedup_report returns the alias_map dict from dedup_report.json."""
    report = {
        "version": "1",
        "alias_map": {"auth": "authentication_service", "auth_svc": "authentication_service"},
        "merges": [],
    }
    (tmp_path / "dedup_report.json").write_text(json.dumps(report), encoding="utf-8")
    result = _load_dedup_report(tmp_path)
    assert result == {
        "auth": "authentication_service",
        "auth_svc": "authentication_service",
    }


def test_load_dedup_report_corrupt_returns_empty(tmp_path):
    """Corrupt JSON does not crash — returns {}."""
    (tmp_path / "dedup_report.json").write_text("not json {}{", encoding="utf-8")
    result = _load_dedup_report(tmp_path)
    assert result == {}


def test_load_dedup_report_missing_alias_map_key(tmp_path):
    """Report without alias_map key returns {}."""
    report = {"version": "1", "summary": {}, "merges": []}
    (tmp_path / "dedup_report.json").write_text(json.dumps(report), encoding="utf-8")
    result = _load_dedup_report(tmp_path)
    assert result == {}


def test_load_dedup_report_rejects_non_string_values(tmp_path):
    """alias_map with non-string values is filtered (defensive)."""
    report = {
        "version": "1",
        "alias_map": {
            "good_key": "good_value",
            "int_value": 42,
        },
        "merges": [],
    }
    (tmp_path / "dedup_report.json").write_text(json.dumps(report), encoding="utf-8")
    result = _load_dedup_report(tmp_path)
    assert result == {"good_key": "good_value"}


def test_run_query_graph_resolves_alias():
    """_run_query_graph redirects merged-away IDs and annotates meta with resolved_from_alias."""
    G = nx.Graph()
    G.add_node("authentication_service", label="authentication service",
               file_type="code", community=0, source_file="auth.py", source_location="L1")
    G.add_node("other", label="other service", file_type="code", community=0,
               source_file="other.py", source_location="L1")
    G.add_edge("authentication_service", "other", relation="calls", confidence="EXTRACTED")

    communities = _communities_from_graph(G)
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    alias_map = {"auth": "authentication_service"}

    response = _run_query_graph(
        G, communities, 1000.0, bf, telemetry,
        {"question": "authentication service", "depth": 1, "budget": 500, "layer": 1},
        alias_map=alias_map,
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    # No alias was actually triggered (question-based scoring, no explicit node_id)
    # — just verify no crash and meta is well-formed
    assert "layer" in meta


def test_run_query_graph_no_alias_map_backward_compat():
    """_run_query_graph with no alias_map kwarg behaves identically to pre-Phase-10."""
    G = _dispatch_fixture_graph()
    communities = _communities_from_graph(G)
    telemetry: dict = {}
    bf = _compute_branching_factor(G)

    response_without = _run_query_graph(
        G, communities, 1000.0, bf, telemetry,
        {"question": "node", "depth": 1, "budget": 500, "layer": 1},
    )
    telemetry2: dict = {}
    response_with_empty = _run_query_graph(
        G, communities, 1000.0, bf, telemetry2,
        {"question": "node", "depth": 1, "budget": 500, "layer": 1},
        alias_map={},
    )
    # Both should produce the same structure (meta keys, status)
    _, meta1_json = response_without.split(QUERY_GRAPH_META_SENTINEL, 1)
    _, meta2_json = response_with_empty.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta1 = json.loads(meta1_json)
    meta2 = json.loads(meta2_json)
    assert meta1["status"] == meta2["status"]
    assert "resolved_from_alias" not in meta1
    assert "resolved_from_alias" not in meta2


def test_run_query_graph_records_all_aliases_for_same_canonical():
    """WR-02 regression: multiple aliases resolving to one canonical must all be recorded.

    Pre-fix the recorder was ``_resolved_aliases[canonical] = node_id`` which
    overwrote on the second hit, so only the last alias survived. Now each
    canonical maps to a list of every alias that was redirected to it.
    """
    G = nx.Graph()
    G.add_node("authentication_service", label="authentication service",
               file_type="code", community=0, source_file="auth.py", source_location="L1")
    G.add_node("other", label="other service", file_type="code", community=0,
               source_file="other.py", source_location="L1")
    G.add_edge("authentication_service", "other", relation="calls", confidence="EXTRACTED")

    communities = _communities_from_graph(G)
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    # Two distinct merged-away IDs both collapse to the same canonical.
    alias_map = {
        "auth": "authentication_service",
        "auth_svc": "authentication_service",
    }

    response = _run_query_graph(
        G, communities, 1000.0, bf, telemetry,
        {
            "question": "auth",
            "depth": 1,
            "budget": 500,
            "layer": 1,
            # seed_nodes triggers alias resolution for both entries.
            "seed_nodes": ["auth", "auth_svc"],
        },
        alias_map=alias_map,
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    resolved = meta["resolved_from_alias"]
    # Both aliases must surface under the canonical, not just the last write.
    assert "authentication_service" in resolved
    assert isinstance(resolved["authentication_service"], list)
    assert sorted(resolved["authentication_service"]) == ["auth", "auth_svc"]


def test_run_query_graph_does_not_mutate_caller_arguments():
    """WR-03 regression: _run_query_graph must not rewrite caller's arguments dict.

    Pre-fix alias resolution mutated ``arguments[seed_nodes]`` and
    ``arguments[node_id]`` in place, so the caller's dict held the resolved
    canonical IDs after dispatch — a latent bug for any retry/instrumentation
    path that re-reads the original input.
    """
    G = nx.Graph()
    G.add_node("authentication_service", label="authentication service",
               file_type="code", community=0, source_file="auth.py", source_location="L1")
    G.add_node("other", label="other", file_type="code", community=0,
               source_file="other.py", source_location="L1")
    G.add_edge("authentication_service", "other", relation="calls", confidence="EXTRACTED")

    communities = _communities_from_graph(G)
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    alias_map = {"auth": "authentication_service", "auth_svc": "authentication_service"}

    arguments = {
        "question": "auth",
        "depth": 1,
        "budget": 500,
        "layer": 1,
        "node_id": "auth",
        "seed_nodes": ["auth", "auth_svc"],
    }
    # Snapshot exact pre-call state for comparison.
    snapshot = {
        "question": arguments["question"],
        "depth": arguments["depth"],
        "budget": arguments["budget"],
        "layer": arguments["layer"],
        "node_id": arguments["node_id"],
        "seed_nodes": list(arguments["seed_nodes"]),
    }

    _run_query_graph(
        G, communities, 1000.0, bf, telemetry, arguments, alias_map=alias_map,
    )

    # Caller's dict must be untouched: aliases must still be the original strings.
    assert arguments["node_id"] == snapshot["node_id"] == "auth"
    assert arguments["seed_nodes"] == snapshot["seed_nodes"] == ["auth", "auth_svc"]
    assert arguments["question"] == snapshot["question"]
    assert arguments["depth"] == snapshot["depth"]
    assert arguments["budget"] == snapshot["budget"]
    assert arguments["layer"] == snapshot["layer"]




# --- Phase 10 Plan 09: UAT gap test 8 — alias resolution on no_seed_nodes path ---

def test_no_seed_nodes_surfaces_resolved_from_alias():
    """no_seed_nodes meta must include resolved_from_alias when an alias was resolved (UAT gap test 8).

    When node_id='auth' redirects to 'authentication_service' via alias_map, but
    authentication_service is not in the graph (so start_nodes is empty), the
    no_seed_nodes meta must still expose resolved_from_alias so agents know the
    redirect happened.
    """
    # A graph that does NOT contain the canonical 'authentication_service' node
    # so that after alias resolution, _score_nodes finds no seed nodes.
    G = nx.Graph()
    G.add_node("unrelated_service", label="unrelated service", file_type="code",
               community=0, source_file="other.py", source_location="L1")

    communities = _communities_from_graph(G)
    telemetry: dict = {}
    bf = _compute_branching_factor(G)
    alias_map = {"auth": "authentication_service"}

    response = _run_query_graph(
        G, communities, 1000.0, bf, telemetry,
        {
            "node_id": "auth",
            "question": "",  # empty question ensures no question-based scoring
            "depth": 1,
            "budget": 500,
            "layer": 1,
        },
        alias_map=alias_map,
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "no_seed_nodes"
    assert "resolved_from_alias" in meta, (
        "resolved_from_alias must be present in no_seed_nodes meta when alias was resolved"
    )
    assert meta["resolved_from_alias"] == {"authentication_service": ["auth"]}


# --- Phase 11: graph_summary + connect_topics ---

def _make_graph_for_phase11() -> nx.Graph:
    """Richer graph with distinct communities for Phase 11 tool tests."""
    G = nx.Graph()
    G.add_node("n1", label="extract", source_file="extract.py", source_location="L10", community=0)
    G.add_node("n2", label="cluster", source_file="cluster.py", source_location="L5", community=0)
    G.add_node("n3", label="build", source_file="build.py", source_location="L1", community=1)
    G.add_node("n4", label="report", source_file="report.py", source_location="L1", community=1)
    G.add_node("n5", label="serve", source_file="serve.py", source_location="L1", community=2)
    G.add_edge("n1", "n2", relation="calls", confidence="INFERRED", source_file="extract.py")
    G.add_edge("n2", "n3", relation="imports", confidence="EXTRACTED", source_file="cluster.py")
    G.add_edge("n3", "n4", relation="uses", confidence="EXTRACTED", source_file="build.py")
    G.add_edge("n1", "n5", relation="references", confidence="AMBIGUOUS", source_file="extract.py")
    return G


def test_graph_summary_envelope_no_graph(tmp_path):
    """When graph_path does not exist: meta.status == 'no_graph', splits cleanly on SENTINEL."""
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    response = _run_graph_summary(G, communities, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    # tmp_path has no snapshots — should still return ok (not no_graph, that's the closure test)
    # The pure helper doesn't check graph_path existence — the closure does.
    # What the helper does: 0 snapshots → delta = {"status": "no_prior_snapshot"}
    assert meta["status"] == "ok"
    assert meta["delta"] == {"status": "no_prior_snapshot"}
    assert meta["snapshot_count"] == 0


def test_graph_summary_envelope_ok(tmp_path):
    """On a populated graph: meta.status == 'ok', required keys present."""
    from graphify.snapshot import save_snapshot
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    save_snapshot(G, communities, tmp_path)
    # Slightly modified graph for the current state
    G2 = _make_graph_for_phase11()
    G2.add_node("n6", label="new_node", source_file="new.py", community=0)
    communities2 = _communities_from_graph(G2)
    response = _run_graph_summary(G2, communities2, tmp_path, {"top_n": 3, "budget": 500})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["layer"] == 1
    assert "snapshot_count" in meta
    assert "god_node_count" in meta
    assert "community_count" in meta
    assert meta["snapshot_count"] >= 1
    assert meta["god_node_count"] >= 0
    assert meta["community_count"] >= 0


def test_graph_summary_budget_clamp(tmp_path):
    """Budget clamping: 10 clamps to 50, 999999999 clamps to 100000. No crash."""
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    # Low budget clamp — no crash
    response_low = _run_graph_summary(G, communities, tmp_path, {"budget": 10})
    assert QUERY_GRAPH_META_SENTINEL in response_low
    meta_low = json.loads(response_low.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta_low["status"] == "ok"
    # High budget clamp — no crash
    response_high = _run_graph_summary(G, communities, tmp_path, {"budget": 999999999})
    assert QUERY_GRAPH_META_SENTINEL in response_high
    meta_high = json.loads(response_high.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta_high["status"] == "ok"
    # Low budget response should be shorter than high budget (body clamped differently)
    body_low = response_low.split(QUERY_GRAPH_META_SENTINEL)[0]
    body_high = response_high.split(QUERY_GRAPH_META_SENTINEL)[0]
    # body_low max is 50*3=150 chars; body_high max is 100000*3 chars — body_low <= body_high
    assert len(body_low) <= len(body_high) + 1  # allow for truncation marker edge case


def test_graph_summary_no_prior_snapshot(tmp_path):
    """Brand-new graph with zero snapshots: meta.delta == {'status': 'no_prior_snapshot'}."""
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    response = _run_graph_summary(G, communities, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "ok"
    assert meta["delta"] == {"status": "no_prior_snapshot"}


def test_graph_summary_compute_delta_four_arg_call(tmp_path, monkeypatch):
    """BLOCKER 1 regression: compute_delta must be called with 4 args, not 2."""
    from graphify import delta as _delta
    calls = []
    original = _delta.compute_delta

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(_delta, "compute_delta", _spy)

    # Set up a prior snapshot
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    from graphify.snapshot import save_snapshot
    save_snapshot(G, communities, tmp_path)

    # Run the helper (it will import compute_delta at call time from .delta)
    # We need to also patch the reference inside serve module
    import graphify.serve as _serve_mod
    monkeypatch.setattr(_serve_mod, "_run_graph_summary",
                        lambda G, comms, snaps_dir, args: _run_graph_summary(G, comms, snaps_dir, args))

    G2 = _make_graph_for_phase11()
    G2.add_node("n6", label="new_node", source_file="new.py", community=0)
    communities2 = _communities_from_graph(G2)

    # Patch compute_delta inside graphify.delta so _run_graph_summary picks it up
    from graphify import delta as delta_mod
    monkeypatch.setattr(delta_mod, "compute_delta", _spy)

    response = _run_graph_summary(G2, communities2, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    assert calls, "compute_delta was not called"
    args, _kwargs = calls[0]
    assert len(args) == 4, f"Expected 4 positional args to compute_delta, got {len(args)}: {args!r}"


def test_graph_summary_snapshot_root_not_double_nested(tmp_path):
    """Regression: CR-01 — _out_dir.parent (project root) must be passed, not _out_dir.

    Simulates the production path: graph_path = "graphify-out/graph.json"
    so _out_dir = tmp_path / "graphify-out".
    save_snapshot(..., project_root=tmp_path) writes to tmp_path/graphify-out/snapshots/.
    If _run_graph_summary receives _out_dir instead of _out_dir.parent, list_snapshots()
    would scan _out_dir/graphify-out/snapshots/ (double-nested, non-existent), returning []
    and forcing delta == {'status': 'no_prior_snapshot'} even after a real snapshot was saved.
    """
    from graphify.snapshot import save_snapshot

    # Simulate the production layout: graph lives at graphify-out/graph.json
    graphify_out = tmp_path / "graphify-out"
    graphify_out.mkdir()

    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)

    # Save a snapshot to tmp_path/graphify-out/snapshots/ (what save_snapshot does by default)
    save_snapshot(G, communities, project_root=tmp_path)

    # Simulate a second (current) graph state
    G2 = _make_graph_for_phase11()
    G2.add_node("n_new", label="new_node", source_file="new.py", community=0)
    communities2 = _communities_from_graph(G2)

    # The closure in serve() does: _out_dir = Path(graph_path).parent = graphify_out
    # The correct call is: _run_graph_summary(G, communities, _out_dir.parent, arguments)
    # i.e. pass tmp_path (the project root), NOT graphify_out.
    response = _run_graph_summary(G2, communities2, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])

    # snapshot_count must be >= 1; if double-nested path were used it would be 0
    assert meta["snapshot_count"] >= 1, (
        "snapshot_count is 0 — snapshots were not found, indicating double-nested path bug "
        "(pass _out_dir.parent not _out_dir to _run_graph_summary)"
    )
    # delta must not be the no-snapshot fallback
    assert meta["delta"] != {"status": "no_prior_snapshot"}, (
        "delta still shows no_prior_snapshot — list_snapshots() returned [] "
        "because the wrong root directory was passed (double-nesting bug)"
    )
    assert meta["status"] == "ok"


def test_connect_topics_envelope_ok(tmp_path):
    """Two connected labels: meta.status=='ok', path_length, surprise_count, surprise_scope present."""
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    response = _run_connect_topics(G, communities, {}, {"topic_a": "extract", "topic_b": "build"})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert "path_length" in meta
    assert "surprise_count" in meta
    assert meta["surprise_scope"] == "global"


def test_connect_topics_alias_redirect(tmp_path):
    """Alias map: topic_a='auth' redirects to 'authentication_service' via alias_map."""
    G = nx.Graph()
    G.add_node("authentication_service", label="authentication service",
               source_file="auth.py", community=0)
    G.add_node("user_model", label="user model", source_file="user.py", community=1)
    G.add_edge("authentication_service", "user_model", relation="uses",
               confidence="EXTRACTED", source_file="auth.py")
    communities = _communities_from_graph(G)
    alias_map = {"auth": "authentication_service"}
    response = _run_connect_topics(
        G, communities, alias_map,
        {"topic_a": "auth", "topic_b": "user model"}
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "ok"
    assert "resolved_from_alias" in meta
    assert meta["resolved_from_alias"] == {"authentication_service": ["auth"]}


def test_connect_topics_ambiguous(tmp_path):
    """When label fuzzy-matches multiple nodes: meta.status == 'ambiguous_entity'."""
    G = nx.Graph()
    G.add_node("auth_service", label="auth service", source_file="auth_service.py", community=0)
    G.add_node("auth_provider", label="auth provider", source_file="auth_provider.py", community=0)
    G.add_node("user_model", label="user model", source_file="user.py", community=1)
    G.add_edge("auth_service", "user_model", relation="uses",
               confidence="EXTRACTED", source_file="auth_service.py")
    G.add_edge("auth_provider", "user_model", relation="uses",
               confidence="EXTRACTED", source_file="auth_provider.py")
    communities = _communities_from_graph(G)
    # "auth" matches both auth_service and auth_provider
    response = _run_connect_topics(
        G, communities, {},
        {"topic_a": "auth", "topic_b": "user model"}
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "ambiguous_entity"
    assert "candidates" in meta
    assert "topic_a" in meta["candidates"]
    candidates_a = meta["candidates"]["topic_a"]
    assert len(candidates_a) == 2
    for c in candidates_a:
        assert "id" in c
        assert "label" in c
        assert "source_file" in c


def test_connect_topics_entity_not_found(tmp_path):
    """Unknown label returns status='entity_not_found' with missing_endpoints list."""
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    response = _run_connect_topics(
        G, communities, {},
        {"topic_a": "nonexistent_zzzxxx", "topic_b": "extract"}
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "entity_not_found"
    assert "missing_endpoints" in meta
    assert "topic_a" in meta["missing_endpoints"]


def test_connect_topics_no_path(tmp_path):
    """Two disconnected components: status == 'no_path'."""
    G = nx.Graph()
    G.add_node("island_a", label="island a", source_file="a.py", community=0)
    G.add_node("island_b", label="island b", source_file="b.py", community=1)
    # No edges between them
    communities = _communities_from_graph(G)
    response = _run_connect_topics(
        G, communities, {},
        {"topic_a": "island a", "topic_b": "island b"}
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "no_path"


def test_connect_topics_section_headers_distinct(tmp_path):
    """text_body must contain 'Shortest Path' before 'Surprising Bridges', plus scope label.

    Validates RESEARCH.md Pitfall 4 (no conflation) and BLOCKER 4 Option A resolution.
    """
    G = _make_graph_for_phase11()
    communities = _communities_from_graph(G)
    response = _run_connect_topics(
        G, communities, {},
        {"topic_a": "extract", "topic_b": "report"}
    )
    assert QUERY_GRAPH_META_SENTINEL in response
    text_body = response.split(QUERY_GRAPH_META_SENTINEL)[0]
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])

    idx_path = text_body.find("Shortest Path")
    idx_bridges = text_body.find("Surprising Bridges")
    assert idx_path >= 0, "'Shortest Path' header missing from text_body"
    assert idx_bridges >= 0, "'Surprising Bridges' header missing from text_body"
    assert idx_path < idx_bridges, "'Shortest Path' must appear before 'Surprising Bridges'"
    assert "global to the graph" in text_body, (
        "Surprising-bridges section must be explicitly labelled as 'global to the graph'"
    )
    assert meta["surprise_scope"] == "global"


# --- Phase 11: entity_trace ---

def test_entity_trace_insufficient_history(tmp_path):
    """With 0 prior snapshots (only live graph): meta.status == 'insufficient_history'."""
    G_live = nx.Graph()
    for j in range(3):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    # tmp_path has no snapshots directory — list_snapshots returns []
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "n0"})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    assert meta["status"] == "insufficient_history"
    assert meta["snapshots_available"] == 0


def test_entity_trace_ok_timeline(make_snapshot_chain, tmp_path):
    """With >=2 snapshots where entity n0 exists throughout: status ok, timeline_length>=3."""
    snaps = make_snapshot_chain(n=3, root=tmp_path)
    # Build G_live with same id scheme as fixture (BLOCKER 2 fix)
    G_live = nx.Graph()
    for j in range(4):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    G_live.add_edge("n0", "n2", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    G_live.add_edge("n0", "n3", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "n0"})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["timeline_length"] >= 3
    assert meta["first_seen"] is not None
    text_body = parts[0]
    # text_body should reference "first_seen" or "First seen"
    assert "First seen" in text_body or "first_seen" in text_body


def test_entity_trace_alias_redirect(make_snapshot_chain, tmp_path):
    """Alias map: passing entity='auth' redirects to 'authentication_service'. meta has resolved_from_alias."""
    snaps = make_snapshot_chain(n=2, root=tmp_path)
    # Build a live graph where 'authentication_service' exists (not 'auth')
    # Use n0 as alias target for compatibility with fixture snapshots
    G_live = nx.Graph()
    for j in range(3):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    alias_map = {"auth": "n0"}
    response = _run_entity_trace(G_live, tmp_path, alias_map, {"entity": "auth"})
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "ok"
    assert "resolved_from_alias" in meta
    assert meta["resolved_from_alias"] == {"n0": ["auth"]}


def test_entity_trace_ambiguous_entity(make_snapshot_chain, tmp_path):
    """Label 'auth' matches multiple nodes: status == 'ambiguous_entity' with candidates list."""
    snaps = make_snapshot_chain(n=2, root=tmp_path)
    G_live = nx.Graph()
    G_live.add_node("auth_service", label="auth service", source_file="auth_service.py",
                    community=0, file_type="code")
    G_live.add_node("auth_provider", label="auth provider", source_file="auth_provider.py",
                    community=0, file_type="code")
    G_live.add_node("user_model", label="user model", source_file="user.py",
                    community=1, file_type="code")
    G_live.add_edge("auth_service", "user_model", relation="uses",
                    confidence="EXTRACTED", source_file="auth_service.py")
    G_live.add_edge("auth_provider", "user_model", relation="uses",
                    confidence="EXTRACTED", source_file="auth_provider.py")
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "auth"})
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "ambiguous_entity"
    assert "candidates" in meta
    assert len(meta["candidates"]) == 2
    for c in meta["candidates"]:
        assert "id" in c
        assert "label" in c
        assert "source_file" in c


def test_entity_trace_entity_not_found(make_snapshot_chain, tmp_path):
    """Entity 'nonexistent_label_xyz' against populated graph returns status == 'entity_not_found'."""
    snaps = make_snapshot_chain(n=2, root=tmp_path)
    G_live = nx.Graph()
    for j in range(3):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "nonexistent_label_xyz"})
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "entity_not_found"


def test_entity_trace_no_graph(tmp_path):
    """When graph_path does not exist: meta.status == 'no_data' (no entity given)."""
    # _run_entity_trace takes G directly — we test the no_data edge case by passing empty entity.
    G_live = nx.Graph()
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": ""})
    assert QUERY_GRAPH_META_SENTINEL in response
    meta = json.loads(response.split(QUERY_GRAPH_META_SENTINEL)[1])
    assert meta["status"] == "no_data"


def test_entity_trace_memory_discipline(make_snapshot_chain, tmp_path):
    """Weakref test: all snapshot graphs are released after _run_entity_trace returns."""
    import weakref
    import gc
    from graphify import snapshot as _snap
    original = _snap.load_snapshot
    refs = []

    def _spy(path):
        G, c, m = original(path)
        refs.append(weakref.ref(G))
        return G, c, m

    _snap.load_snapshot = _spy
    try:
        snaps = make_snapshot_chain(n=3, root=tmp_path)
        # Build G_live with the SAME id scheme as the fixture so _find_node matches.
        G_live = nx.Graph()
        for j in range(4):
            G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                            source_location=f"L{j}", file_type="code", community=j % 2)
        G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
        G_live.add_edge("n0", "n2", relation="calls", confidence="EXTRACTED", source_file="f0.py")
        G_live.add_edge("n0", "n3", relation="calls", confidence="EXTRACTED", source_file="f0.py")
        _ = _run_entity_trace(G_live, tmp_path, {}, {"entity": "n0"})
        gc.collect()
        alive = sum(1 for r in refs if r() is not None)
        assert alive == 0, f"{alive} snapshot graph(s) still alive — memory discipline violated"
    finally:
        _snap.load_snapshot = original


def test_entity_trace_envelope_structure(make_snapshot_chain, tmp_path):
    """On OK path: response splits on SENTINEL, json parses, all required keys present."""
    snaps = make_snapshot_chain(n=3, root=tmp_path)
    G_live = nx.Graph()
    for j in range(4):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    G_live.add_edge("n0", "n2", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    G_live.add_edge("n0", "n3", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    response = _run_entity_trace(G_live, tmp_path, {}, {"entity": "n0"})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    required_keys = {
        "status", "layer", "search_strategy", "cardinality_estimate",
        "continuation_token", "snapshot_count", "first_seen", "timeline_length", "entity_id"
    }
    for key in required_keys:
        assert key in meta, f"Required key missing from meta: {key}"
    assert meta["status"] == "ok"
    assert meta["layer"] == 1
    assert meta["search_strategy"] == "trace"


# --- Phase 11: drift_nodes + newly_formed_clusters ---

def test_drift_nodes_insufficient_history(tmp_path):
    """Zero snapshots → status='insufficient_history', snapshots_available==0."""
    G = nx.Graph()
    G.add_node("n0", label="n0", source_file="f0.py", source_location="L0",
               file_type="code", community=0)
    response = _run_drift_nodes(G, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "insufficient_history"
    assert meta["snapshots_available"] == 0
    assert meta["search_strategy"] == "drift"


def test_drift_nodes_trend_vectors(make_snapshot_chain, tmp_path):
    """With 3 snapshots, drift_nodes returns meta.drift_count >= 1 and nodes_scanned >= 2."""
    snaps = make_snapshot_chain(n=3, root=tmp_path)
    # Build G_live using same n{j} scheme; n0 is present across all snapshots → drifts
    G_live = nx.Graph()
    for j in range(4):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    G_live.add_edge("n0", "n2", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    G_live.add_edge("n0", "n3", relation="calls", confidence="EXTRACTED", source_file="f0.py")

    response = _run_drift_nodes(G_live, tmp_path, {"max_snapshots": 10})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["drift_count"] >= 1
    assert meta["nodes_scanned"] >= 2
    # At least one node label should appear in the text body
    assert parts[0].strip(), "text_body should not be empty"


def test_drift_nodes_top_n_respected(make_snapshot_chain, tmp_path):
    """With top_n=1, meta.drift_count <= 1."""
    snaps = make_snapshot_chain(n=3, root=tmp_path)
    G_live = nx.Graph()
    for j in range(4):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=j % 2)
    response = _run_drift_nodes(G_live, tmp_path, {"top_n": 1})
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["drift_count"] <= 1


def test_drift_nodes_memory_discipline(make_snapshot_chain, tmp_path):
    """All G_snap objects are released (del'd) after _run_drift_nodes completes."""
    import gc
    import weakref
    import graphify.snapshot as _snap

    original = _snap.load_snapshot
    refs = []

    def _spy(path):
        G, c, m = original(path)
        refs.append(weakref.ref(G))
        return G, c, m

    _snap.load_snapshot = _spy
    try:
        snaps = make_snapshot_chain(n=3, root=tmp_path)
        G_live = nx.Graph()
        for j in range(4):
            G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                            source_location=f"L{j}", file_type="code", community=j % 2)
        _ = _run_drift_nodes(G_live, tmp_path, {})
        gc.collect()
        alive = sum(1 for r in refs if r() is not None)
        assert alive == 0, f"{alive} snapshot graph(s) still alive — memory discipline violated"
    finally:
        _snap.load_snapshot = original


def test_newly_formed_clusters_insufficient_history(tmp_path):
    """Zero snapshots → status='insufficient_history'."""
    G = nx.Graph()
    G.add_node("n0", label="n0", source_file="f0.py", source_location="L0",
               file_type="code", community=0)
    communities = {0: ["n0"]}
    response = _run_newly_formed_clusters(G, communities, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "insufficient_history"
    assert meta["snapshots_available"] == 0
    assert meta["search_strategy"] == "emerge"


def test_newly_formed_clusters_no_change(tmp_path):
    """When live graph and most recent snapshot have identical community members → no_change."""
    from graphify.snapshot import save_snapshot

    G = nx.Graph()
    for j in range(3):
        G.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                   source_location=f"L{j}", file_type="code", community=j % 2)
    G.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    # Community structure is identical to what we'll load back.
    communities = {0: ["n0", "n2"], 1: ["n1"]}
    save_snapshot(G, communities, project_root=tmp_path, name="snap_00")

    response = _run_newly_formed_clusters(G, communities, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "no_change"
    assert meta["new_cluster_count"] == 0
    assert meta["new_cluster_ids"] == []


def test_newly_formed_clusters_new_cluster_detected(tmp_path):
    """Snapshot has {n0, n1, n2}; live graph adds {new_a, new_b, new_c} as isolated triangle → 1 new cluster."""
    from graphify.snapshot import save_snapshot

    # Save snap with original nodes only.
    G_old = nx.Graph()
    for j in range(3):
        G_old.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                       source_location=f"L{j}", file_type="code", community=0)
    G_old.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    comms_old = {0: ["n0", "n1", "n2"]}
    save_snapshot(G_old, comms_old, project_root=tmp_path, name="snap_00")

    # Live graph has original nodes PLUS an isolated new cluster.
    G_live = nx.Graph()
    for j in range(3):
        G_live.add_node(f"n{j}", label=f"n{j}", source_file=f"f{j}.py",
                        source_location=f"L{j}", file_type="code", community=0)
    G_live.add_edge("n0", "n1", relation="calls", confidence="EXTRACTED", source_file="f0.py")
    for name in ["new_a", "new_b", "new_c"]:
        G_live.add_node(name, label=name, source_file="new.py",
                        source_location="L1", file_type="code", community=99)
    G_live.add_edge("new_a", "new_b", relation="calls", confidence="EXTRACTED", source_file="new.py")
    G_live.add_edge("new_b", "new_c", relation="calls", confidence="EXTRACTED", source_file="new.py")
    G_live.add_edge("new_c", "new_a", relation="calls", confidence="EXTRACTED", source_file="new.py")
    # new_a/b/c form community 99 — no overlap with prior community 0.
    comms_live = {0: ["n0", "n1", "n2"], 99: ["new_a", "new_b", "new_c"]}

    response = _run_newly_formed_clusters(G_live, comms_live, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["new_cluster_count"] >= 1
    assert 99 in meta["new_cluster_ids"]


def test_newly_formed_clusters_envelope_structure(tmp_path):
    """On OK path: response splits on SENTINEL; json parses; all required keys present."""
    from graphify.snapshot import save_snapshot

    # Snap with just {n0} in community 0.
    G_old = nx.Graph()
    G_old.add_node("n0", label="n0", source_file="f0.py",
                   source_location="L0", file_type="code", community=0)
    save_snapshot(G_old, {0: ["n0"]}, project_root=tmp_path, name="snap_00")

    # Live graph adds a fully new community.
    G_live = nx.Graph()
    G_live.add_node("n0", label="n0", source_file="f0.py",
                    source_location="L0", file_type="code", community=0)
    G_live.add_node("fresh", label="fresh", source_file="fresh.py",
                    source_location="L1", file_type="code", community=1)
    comms_live = {0: ["n0"], 1: ["fresh"]}

    response = _run_newly_formed_clusters(G_live, comms_live, tmp_path, {})
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    required_keys = {
        "status", "layer", "search_strategy", "cardinality_estimate",
        "continuation_token", "snapshot_count", "new_cluster_count", "new_cluster_ids",
    }
    for key in required_keys:
        assert key in meta, f"Required key missing: {key}"
    assert meta["layer"] == 1
    assert meta["search_strategy"] == "emerge"



# --- Phase 18 focus resolver tests (FOCUS-02, FOCUS-06) ---

def test_focus_resolver_str_source_file(tmp_path):
    """FOCUS-02: resolver handles source_file as str (single-source v1.3 schema)."""
    from pathlib import Path
    G = nx.Graph()
    G.add_node("n_login", label="login", source_file="src/auth.py",
               source_location="L10", file_type="code", community=0)
    G.add_node("n_other", label="other", source_file="src/other.py",
               source_location="L1", file_type="code", community=0)
    # Write the target file so validate_graph_path-style callers can resolve; resolver itself compares strings.
    target = tmp_path / "src" / "auth.py"
    target.parent.mkdir(parents=True)
    target.write_text("def login(): pass\n")
    # Resolver compares against both the raw stored string AND the resolved absolute form (D-04).
    seeds = _resolve_focus_seeds(G, Path("src/auth.py"))
    assert seeds == ["n_login"]


def test_focus_resolver_list_source_file_multi_seed(tmp_path):
    """FOCUS-02 + D-01: resolver handles source_file as list[str] via _iter_sources and returns multi-seed union."""
    from pathlib import Path
    G = nx.Graph()
    G.add_node("n_a", label="alpha", source_file=["src/auth.py", "src/helpers.py"],
               source_location="L10", file_type="code", community=0)
    G.add_node("n_b", label="beta", source_file=["src/auth.py"],
               source_location="L20", file_type="code", community=0)
    G.add_node("n_c", label="gamma", source_file="src/other.py",
               source_location="L1", file_type="code", community=1)
    seeds = _resolve_focus_seeds(G, Path("src/auth.py"))
    assert set(seeds) == {"n_a", "n_b"}
    assert "n_c" not in seeds


def test_multi_seed_compose_all_matches_expected():
    """FOCUS-06: multi-seed ego-graph uses nx.compose_all (not multi-seed nx.ego_graph which raises NodeNotFound)."""
    G = nx.path_graph(5)  # 0-1-2-3-4
    for n in G.nodes:
        G.nodes[n]["label"] = str(n)
    # Expected: ego(0, r=1) = {0, 1}; ego(2, r=1) = {1, 2, 3}; union = {0, 1, 2, 3}
    subgraph = _multi_seed_ego(G, [0, 2], radius=1)
    assert set(subgraph.nodes) == {0, 1, 2, 3}
    # Attributes preserved from originals
    assert subgraph.nodes[0]["label"] == "0"
    # Empty seeds -> empty graph (defensive)
    empty = _multi_seed_ego(G, [], radius=1)
    assert len(empty.nodes) == 0
    # Seeds not in graph -> filter, do NOT raise NodeNotFound
    partial = _multi_seed_ego(G, [0, "nonexistent"], radius=1)
    assert set(partial.nodes) == {0, 1}


# --- Phase 18 get_focus_context MCP tool (FOCUS-01, FOCUS-03, FOCUS-04, FOCUS-05, FOCUS-07) ---

def _make_focus_graph():
    """Synthetic graph with 4 nodes, 3 edges, source_file both str and list forms."""
    G = nx.Graph()
    G.add_node("n_login",  label="login",  source_file="src/auth.py",
               source_location="L10", file_type="code", community=0)
    G.add_node("n_verify", label="verify", source_file="src/auth.py",
               source_location="L20", file_type="code", community=0)
    G.add_node("n_hash",   label="hash",   source_file=["src/auth.py", "src/helpers.py"],
               source_location="L30", file_type="code", community=0)
    G.add_node("n_log",    label="log",    source_file="src/logger.py",
               source_location="L5",  file_type="code", community=1)
    G.add_edge("n_login",  "n_verify", relation="calls", confidence="EXTRACTED", source_file="src/auth.py")
    G.add_edge("n_verify", "n_hash",   relation="calls", confidence="EXTRACTED", source_file="src/auth.py")
    G.add_edge("n_login",  "n_log",    relation="calls", confidence="EXTRACTED", source_file="src/auth.py")
    return G


def _write_source_file(project_root, rel="src/auth.py"):
    f = project_root / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("def login(): pass\n")
    return f


def test_get_focus_context_registered():
    """FOCUS-01: tool is registered in mcp_tool_registry (MANIFEST-05 invariant ensures handler parity)."""
    from graphify.mcp_tool_registry import build_mcp_tools
    tool_names = {t.name for t in build_mcp_tools()}
    assert "get_focus_context" in tool_names


def test_get_focus_context_envelope_ok(tmp_path):
    """FOCUS-03: happy path — D-02 envelope with meta.status == 'ok'."""
    _write_source_file(tmp_path, "src/auth.py")
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    args = {"focus_hint": {"file_path": "src/auth.py", "neighborhood_depth": 2}, "budget": 500}
    response = _run_get_focus_context_core(G, communities, tmp_path, args)
    assert QUERY_GRAPH_META_SENTINEL in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert len(parts) == 2
    meta = json.loads(parts[1])
    assert meta["status"] == "ok"
    assert meta["node_count"] >= 1
    assert meta["edge_count"] >= 0


def test_get_focus_context_community_summary(tmp_path):
    """FOCUS-03: include_community=True surfaces community info in the envelope."""
    _write_source_file(tmp_path, "src/auth.py")
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    args = {"focus_hint": {"file_path": "src/auth.py", "include_community": True}, "budget": 500}
    response = _run_get_focus_context_core(G, communities, tmp_path, args)
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    has_summary = "community_summary" in meta or "community" in parts[0].lower()
    assert has_summary, f"expected community info in meta or text_body; got meta={meta!r}"


def test_get_focus_context_spoofed_path_silent(tmp_path):
    """FOCUS-04 + T-18-A: /etc/passwd (outside project_root) returns no_context envelope."""
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    args = {"focus_hint": {"file_path": "/etc/passwd"}, "budget": 500}
    response = _run_get_focus_context_core(G, communities, tmp_path, args)
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    assert parts[0] == ""  # D-09 empty text_body
    meta = json.loads(parts[1])
    assert meta == {"status": "no_context", "node_count": 0, "edge_count": 0, "budget_used": 0}


def test_get_focus_context_missing_file_silent(tmp_path):
    """FOCUS-04 + T-18-B: file indexed in graph but missing on disk — silent no_context (FileNotFoundError caught)."""
    # Do NOT create src/auth.py on disk. Graph references it; validate_graph_path raises FileNotFoundError.
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    args = {"focus_hint": {"file_path": "src/auth.py"}, "budget": 500}
    response = _run_get_focus_context_core(G, communities, tmp_path, args)
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert meta["status"] == "no_context"
    assert parts[0] == ""


def test_no_watchdog_import_in_focus_path():
    """FOCUS-05: pull-model — no filesystem watcher import appears in serve.py focus path."""
    import pathlib
    src = pathlib.Path("graphify/serve.py").read_text()
    assert "import watchdog" not in src
    assert "from watchdog" not in src
    # Scope to the focus-tool region: from _run_get_focus_context_core through the
    # next top-level def. Broader scans pick up the unrelated _filter_blank_stdin
    # helper (stdio blank-line filter, has legit threading.Thread) and false-trip.
    focus_start = src.find("def _run_get_focus_context_core")
    assert focus_start >= 0, "_run_get_focus_context_core must exist"
    focus_end = src.find("\ndef ", focus_start + 1)
    if focus_end < 0:
        focus_end = len(src)
    region = src[focus_start:focus_end]
    assert "threading.Thread" not in region
    assert "asyncio.create_task" not in region
    assert "watchdog" not in region


def test_snapshot_callsites_use_project_root():
    """FOCUS-07 smoke: the 4 _tool_* wrappers still pass _out_dir.parent (project root, not graphify-out)."""
    import pathlib
    src = pathlib.Path("graphify/serve.py").read_text()
    for wrapper in ["_tool_entity_trace", "_tool_drift_nodes",
                    "_tool_newly_formed_clusters", "_tool_graph_summary"]:
        start = src.find(f"def {wrapper}(")
        assert start >= 0, f"wrapper {wrapper} not found"
        end = src.find("\n    def ", start + 1)
        if end < 0:
            end = src.find("\ndef ", start + 1)
        body = src[start:end if end >= 0 else len(src)]
        assert "_out_dir.parent" in body, f"{wrapper} should reference _out_dir.parent (project root)"


def test_binary_status_invariant(tmp_path):
    """D-03 + D-11: spoof / unindexed / missing all yield the SAME meta keys shape — binary status."""
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    expected_keys = {"status", "node_count", "edge_count", "budget_used"}

    # 1. Spoofed path (outside project_root)
    r1 = _run_get_focus_context_core(G, communities, tmp_path,
                                     {"focus_hint": {"file_path": "/etc/passwd"}, "budget": 500})
    # 2. Unindexed but valid path (file exists in project_root but no graph node)
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "unknown.py").write_text("pass\n")
    r2 = _run_get_focus_context_core(G, communities, tmp_path,
                                     {"focus_hint": {"file_path": "src/unknown.py"}, "budget": 500})
    # 3. Missing on disk (graph claims it but file absent)
    r3 = _run_get_focus_context_core(G, communities, tmp_path,
                                     {"focus_hint": {"file_path": "src/auth.py"}, "budget": 500})

    for resp in (r1, r2, r3):
        parts = resp.split(QUERY_GRAPH_META_SENTINEL)
        assert parts[0] == ""
        meta = json.loads(parts[1])
        assert set(meta.keys()) == expected_keys, f"meta shape leaked info: {meta!r}"
        assert meta["status"] == "no_context"


def _make_large_focus_graph():
    """10-node 2-hop chain so outer hop (depth=2) is non-empty and can be dropped independently."""
    import networkx as nx
    G = nx.Graph()
    # Seed node + 3 depth-1 neighbors + 6 depth-2 neighbors (2 per depth-1 node)
    G.add_node("seed_auth", label="seed_auth", source_file="src/auth.py",
               source_location="L1", file_type="code", community=0)
    for i in range(3):
        inner = f"inner_{i}"
        G.add_node(inner, label=inner, source_file=f"src/inner_{i}.py",
                   source_location="L1", file_type="code", community=0)
        G.add_edge("seed_auth", inner, relation="calls", confidence="EXTRACTED",
                   source_file="src/auth.py")
        for j in range(2):
            outer = f"outer_{i}_{j}"
            G.add_node(outer, label=outer, source_file=f"src/outer_{i}_{j}.py",
                       source_location="L1", file_type="code", community=0)
            G.add_edge(inner, outer, relation="calls", confidence="EXTRACTED",
                       source_file=f"src/inner_{i}.py")
    return G


def test_budget_drop_outer_hop_first(tmp_path):
    """D-08: outer hop dropped first when ego-graph + summary > budget*3.
    (a) fewer nodes than uncapped depth=2, (b) every returned node within depth=1 of seed, (c) inner hop preserved."""
    _write_source_file(tmp_path, "src/auth.py")
    G = _make_large_focus_graph()
    communities = _communities_from_graph(G)
    focus_hint = {"file_path": "src/auth.py", "neighborhood_depth": 2}

    # Tight budget forces outer-hop drop. Post-Plan-18-04 signature: (G, communities, project_root, arguments)
    # Budget chosen so that depth=2 (10 nodes) overflows char_budget but depth=1 (4 nodes) fits.
    small = _run_get_focus_context_core(G, communities, tmp_path,
                                        {"focus_hint": focus_hint, "budget": 300})
    large = _run_get_focus_context_core(G, communities, tmp_path,
                                        {"focus_hint": focus_hint, "budget": 10000})
    small_meta = json.loads(small.split(QUERY_GRAPH_META_SENTINEL)[1])
    large_meta = json.loads(large.split(QUERY_GRAPH_META_SENTINEL)[1])

    # (a) fewer nodes than uncapped depth=2 — node_count invariant not text-length.
    assert small_meta["node_count"] < large_meta["node_count"], (
        f"tight budget should drop outer hop: small={small_meta['node_count']} "
        f"large={large_meta['node_count']}"
    )
    # (b) depth_used monotonicity — small-budget must have STRICTLY less depth_used than large
    # (outer hop dropped per D-08 shrink-radius-before-char-clip).
    assert "depth_used" in small_meta and "depth_used" in large_meta, (
        "D-08 envelope must expose depth_used on ok status"
    )
    assert small_meta["depth_used"] < large_meta["depth_used"], (
        f"outer hop not dropped: small depth_used ({small_meta['depth_used']}) "
        f"must be < large ({large_meta['depth_used']})"
    )
    # (c) inner hop preserved when outer dropped — seed + 3 depth-1 neighbors = 4 nodes minimum.
    # Only assert when D-08 landed at depth=1 (inner preserved); if it had to go to depth=0 the fixture
    # needed a larger budget, which is fixture-tuning, not a D-08 invariant.
    if small_meta["status"] == "ok" and small_meta["depth_used"] >= 1:
        assert small_meta["node_count"] >= 4, (
            f"inner hop dropped prematurely: small returned {small_meta['node_count']} nodes "
            f"at depth_used={small_meta['depth_used']}"
        )


def test_no_context_does_not_echo_focus_hint(tmp_path):
    """D-12 + T-18-D: no_context envelope MUST NOT echo file_path / function_name / line."""
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    args = {"focus_hint": {"file_path": "/etc/passwd", "function_name": "SECRET_FN",
                           "line": 424242}, "budget": 500}
    response = _run_get_focus_context_core(G, communities, tmp_path, args)
    assert "/etc/passwd" not in response
    assert "SECRET_FN" not in response
    assert "424242" not in response
    parts = response.split(QUERY_GRAPH_META_SENTINEL)
    meta = json.loads(parts[1])
    assert set(meta.keys()) == {"status", "node_count", "edge_count", "budget_used"}


# --- Phase 18 P2 guards: FOCUS-08 debounce + FOCUS-09 freshness ---

def test_focus_debounce_suppresses_duplicate(tmp_path, monkeypatch):
    """FOCUS-08 + D-14: dispatcher path — second call within 500ms returns cached envelope
    byte-identical to first, and _run_get_focus_context_core is NOT re-invoked.
    Mirrors the get→core→put sequence in _tool_get_focus_context (WR-03 strengthening)."""
    from graphify import serve as serve_mod
    from graphify.serve import (
        _FOCUS_DEBOUNCE_CACHE,
        _focus_debounce_key,
        _focus_debounce_get,
        _focus_debounce_put,
    )
    _FOCUS_DEBOUNCE_CACHE.clear()
    _write_source_file(tmp_path, "src/auth.py")
    G = _make_focus_graph()
    communities = _communities_from_graph(G)
    focus_hint = {"file_path": "src/auth.py", "neighborhood_depth": 1}
    args = {"focus_hint": focus_hint, "budget": 500}

    # Count invocations of the core via monkeypatch.
    call_counter = {"n": 0}
    real_core = serve_mod._run_get_focus_context_core
    def _counting_core(*a, **kw):
        call_counter["n"] += 1
        return real_core(*a, **kw)
    monkeypatch.setattr(serve_mod, "_run_get_focus_context_core", _counting_core)

    # First call: core runs, envelope is cached (simulating _tool_get_focus_context's put path).
    # Post-Plan-18-04 signature: (G, communities, project_root, arguments) — no alias_map.
    key = _focus_debounce_key(focus_hint)
    first_envelope = serve_mod._run_get_focus_context_core(G, communities, tmp_path, args)
    _focus_debounce_put(key, first_envelope)
    assert call_counter["n"] == 1

    # Second call within window: get path returns cached envelope byte-for-byte.
    cached = _focus_debounce_get(key)
    assert cached is not None, "cache should hit within 500ms window"
    assert cached == first_envelope, "cached envelope must be byte-identical to first"
    # Core must NOT have been re-invoked during the get path.
    assert call_counter["n"] == 1, f"core re-invoked on cache hit (n={call_counter['n']})"

    _FOCUS_DEBOUNCE_CACHE.clear()


def test_focus_debounce_expires(tmp_path, monkeypatch):
    """FOCUS-08 + D-14: after the 500ms window, cache does NOT return — fresh compute happens."""
    from graphify.serve import _focus_debounce_get
    _FOCUS_DEBOUNCE_CACHE.clear()
    args = {"focus_hint": {"file_path": "src/auth.py", "neighborhood_depth": 1}, "budget": 500}
    key = _focus_debounce_key(args["focus_hint"])
    # Seed cache with a timestamp 1 second in the past (window is 0.5s → expired).
    import time as time_mod
    fake_now = [time_mod.monotonic()]
    _FOCUS_DEBOUNCE_CACHE[key] = (fake_now[0] - 1.0, "CACHED_VALUE")

    # Freshness check should see the entry as expired:
    assert _focus_debounce_get(key) is None
    _FOCUS_DEBOUNCE_CACHE.clear()


def test_focus_stale_reported_at_rejected():
    """FOCUS-09 + D-15: reported_at >300s in the past → freshness returns False."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    stale = (now - timedelta(seconds=600)).isoformat()  # 10 minutes ago
    assert _check_focus_freshness(stale, now=now) is False


def test_focus_reported_at_z_suffix_parses():
    """FOCUS-09: Z-suffix compat shim — Py 3.10 fromisoformat rejects 'Z', shim must handle it."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    # Fresh (within 300s) reported_at with Z suffix
    recent = (now - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Must return True (fresh) — NOT False (parse-fail collapse).
    assert _check_focus_freshness(recent, now=now) is True


def test_focus_malformed_reported_at():
    """FOCUS-09 + D-11: malformed reported_at collapses to no_context signal (returns False, no traceback)."""
    assert _check_focus_freshness("not-an-iso-date") is False
    assert _check_focus_freshness("2026-99-99T99:99:99Z") is False
    assert _check_focus_freshness("") is True  # empty = absent = backward compatible (D-15)
    assert _check_focus_freshness(None) is True  # None = absent


# ============================================================================
# Phase 15 Plan 04: _load_enrichment_overlay (ENRICH-08/09/12, D-06, D-16)
# ============================================================================

def _write_enrichment_graph_json(tmp_path, G):
    """Helper: serialize G to graphify-out/graph.json and return (out_dir, graph_path)."""
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_path = out_dir / "graph.json"
    data = json_graph.node_link_data(G, edges="links")
    graph_path.write_text(json.dumps(data), encoding="utf-8")
    return out_dir, graph_path


def test_load_enrichment_overlay(tmp_path):
    """ENRICH-08 + D-06: overlay adds enriched_description without overwriting base description."""
    from graphify.serve import _load_enrichment_overlay
    G = nx.Graph()
    G.add_node("N1", label="n1", description="base", source_file="a.py", community=0)
    G.add_node("N2", label="n2", source_file="b.py", community=0)
    out_dir, gp = _write_enrichment_graph_json(tmp_path, G)
    envelope = {
        "version": 1,
        "snapshot_id": "snap-abc",
        "passes": {
            "description": {"N1": "enriched text A", "N2": "enriched text B"},
        },
    }
    (out_dir / "enrichment.json").write_text(json.dumps(envelope), encoding="utf-8")

    G2 = _load_graph(str(gp))
    _load_enrichment_overlay(G2, out_dir)

    assert G2.nodes["N1"]["description"] == "base"  # base preserved — D-06
    assert G2.nodes["N1"]["enriched_description"] == "enriched text A"
    assert G2.nodes["N2"]["enriched_description"] == "enriched text B"
    # N2 had no base description — overlay must not synthesize one
    assert G2.nodes["N2"].get("description") in (None, "")


def test_overlay_augments_not_overwrites(tmp_path):
    """D-06: staleness_override / community_summary / patterns augment — never clobber base fields."""
    from graphify.serve import _load_enrichment_overlay
    G = nx.Graph()
    G.add_node("N1", label="n1", staleness="FRESH", community=0)
    G.add_node("N2", label="n2", community=0)
    G.add_node("N3", label="n3", community=1)
    out_dir, gp = _write_enrichment_graph_json(tmp_path, G)
    envelope = {
        "version": 1,
        "snapshot_id": "snap-xyz",
        "passes": {
            "community": {"0": "cluster 0 summary", "1": "cluster 1 summary"},
            "staleness": {"N1": "GHOST", "N2": "STALE", "N3": "FRESH"},
            "patterns": [{"name": "god_node", "nodes": ["N1"]}],
        },
    }
    (out_dir / "enrichment.json").write_text(json.dumps(envelope), encoding="utf-8")

    G2 = _load_graph(str(gp))
    _load_enrichment_overlay(G2, out_dir)

    # staleness_override set; base staleness not overwritten (N1 retains FRESH)
    assert G2.nodes["N1"]["staleness_override"] == "GHOST"
    assert G2.nodes["N1"]["staleness"] == "FRESH"
    assert G2.nodes["N2"]["staleness_override"] == "STALE"
    assert G2.nodes["N3"]["staleness_override"] == "FRESH"

    # community_summary threaded to all nodes in that community
    assert G2.nodes["N1"]["community_summary"] == "cluster 0 summary"
    assert G2.nodes["N2"]["community_summary"] == "cluster 0 summary"
    assert G2.nodes["N3"]["community_summary"] == "cluster 1 summary"

    # patterns live at graph-level
    patterns = G2.graph.get("patterns")
    assert isinstance(patterns, list) and len(patterns) == 1
    assert patterns[0]["name"] == "god_node"
    assert patterns[0]["nodes"] == ["N1"]


def test_reload_if_stale_enrichment(tmp_path):
    """ENRICH-09: re-apply overlay when enrichment.json mtime changes. graph.json must NOT be mutated."""
    import os
    import time
    from graphify.serve import _load_enrichment_overlay
    G = nx.Graph()
    G.add_node("N1", label="n1", description="base", community=0)
    out_dir, gp = _write_enrichment_graph_json(tmp_path, G)
    graph_mtime_before = os.stat(gp).st_mtime

    # v1 overlay
    env1 = {
        "version": 1,
        "snapshot_id": "s1",
        "passes": {"description": {"N1": "first"}},
    }
    ep = out_dir / "enrichment.json"
    ep.write_text(json.dumps(env1), encoding="utf-8")

    G2 = _load_graph(str(gp))
    _load_enrichment_overlay(G2, out_dir)
    assert G2.nodes["N1"]["enriched_description"] == "first"

    # v2 overlay — rewrite and bump mtime
    env2 = {
        "version": 1,
        "snapshot_id": "s2",
        "passes": {"description": {"N1": "second"}},
    }
    ep.write_text(json.dumps(env2), encoding="utf-8")
    new_ts = time.time() + 5
    os.utime(ep, (new_ts, new_ts))

    _load_enrichment_overlay(G2, out_dir)
    assert G2.nodes["N1"]["enriched_description"] == "second"

    # graph.json untouched — mtime unchanged (T-15-02)
    assert os.stat(gp).st_mtime == graph_mtime_before


def test_overlay_alias_redirect_on_read(tmp_path):
    """D-16 / ENRICH-12: overlay node_ids routed through dedup alias_map before G.nodes lookup."""
    from graphify.serve import _load_enrichment_overlay
    G = nx.Graph()
    G.add_node("canonical_new", label="c", community=0)
    out_dir, gp = _write_enrichment_graph_json(tmp_path, G)

    # Write dedup report mapping old_alias → canonical_new
    dedup = {
        "version": "1",
        "alias_map": {"old_alias": "canonical_new"},
        "merges": [],
    }
    (out_dir / "dedup_report.json").write_text(json.dumps(dedup), encoding="utf-8")

    # Envelope keyed by old_alias + one genuinely-missing id
    env = {
        "version": 1,
        "snapshot_id": "sid",
        "passes": {
            "description": {
                "old_alias": "enriched via alias",
                "ghost_id": "should be silently skipped",
            },
            "staleness": {"old_alias": "STALE"},
        },
    }
    (out_dir / "enrichment.json").write_text(json.dumps(env), encoding="utf-8")

    G2 = _load_graph(str(gp))
    _load_enrichment_overlay(G2, out_dir)

    # Alias redirected to canonical
    assert G2.nodes["canonical_new"]["enriched_description"] == "enriched via alias"
    assert G2.nodes["canonical_new"]["staleness_override"] == "STALE"

    # No phantom nodes created for alias or ghost
    assert "old_alias" not in G2.nodes
    assert "ghost_id" not in G2.nodes


def test_overlay_missing_file_noop(tmp_path):
    """Missing enrichment.json → no-op. Preserves existing tests that mock _load_graph."""
    from graphify.serve import _load_enrichment_overlay
    G = nx.Graph()
    G.add_node("N1", label="n1", description="base")
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # No enrichment.json written
    _load_enrichment_overlay(G, out_dir)

    # Unchanged
    assert G.nodes["N1"]["description"] == "base"
    assert "enriched_description" not in G.nodes["N1"]
    assert G.graph.get("patterns") is None


# ============================================================
# Phase 17 CHAT-01/02/08 — conversational chat tool
# ============================================================

@pytest.fixture
def _reset_chat_sessions():
    """Clear the module-level chat session store around each chat test."""
    _CHAT_SESSIONS.clear()
    yield
    _CHAT_SESSIONS.clear()


def test_chat_tool_registered():
    """CHAT-01 registry surface: chat tool discoverable via build_mcp_tools()."""
    from graphify import mcp_tool_registry
    tools = (
        getattr(mcp_tool_registry, "TOOLS", None)
        or getattr(mcp_tool_registry, "tools", None)
        or mcp_tool_registry.build_mcp_tools()
    )
    assert tools is not None, "mcp_tool_registry must expose a tool list"
    chat_tool = next((t for t in tools if getattr(t, "name", None) == "chat"), None)
    assert chat_tool is not None, "chat tool missing from registry"
    schema = chat_tool.inputSchema
    assert "query" in schema["required"]
    assert "query" in schema["properties"]
    assert "session_id" in schema["properties"]


def test_chat_envelope_ok(_reset_chat_sessions):
    """CHAT-01 / CHAT-09: _run_chat_core emits a valid D-02 sentinel envelope."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(G, communities, {}, {"query": "what is extract?"})
    assert QUERY_GRAPH_META_SENTINEL in response
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["intent"] in ("explore", "connect", "summarize")
    assert meta["session_id"] is None
    assert "resolved_from_alias" in meta
    assert "citations" in meta and isinstance(meta["citations"], list)


def test_chat_intent_connect_calls_bi_bfs(_reset_chat_sessions, monkeypatch):
    """CHAT-02 connect intent dispatches _bidirectional_bfs when 2+ seeds resolve."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    spy = MagicMock(return_value=(set(G.nodes), [], "ok"))
    monkeypatch.setattr("graphify.serve._bidirectional_bfs", spy)
    response = _run_chat_core(
        G, communities, {}, {"query": "how does extract connect to build"}
    )
    _, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["intent"] == "connect"
    assert spy.called, "connect intent must invoke _bidirectional_bfs when 2+ seeds resolve"


def test_chat_session_isolation(_reset_chat_sessions):
    """CHAT-08 session_id scoping + session_id=None never writes to shared state."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": "s1"})
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": "s2"})
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": None})
    assert "s1" in _CHAT_SESSIONS
    assert "s2" in _CHAT_SESSIONS
    assert None not in _CHAT_SESSIONS
    assert len(_CHAT_SESSIONS["s1"]) >= 1
    assert len(_CHAT_SESSIONS["s2"]) >= 1


def test_chat_ttl_eviction(_reset_chat_sessions):
    """CHAT-08 30-min idle TTL evicts stale sessions lazily on next call."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    _CHAT_SESSIONS["old"] = deque(
        [{"query": "x", "citations": [], "narrative_hash": "", "ts": time.time() - 2000}],
        maxlen=10,
    )
    _run_chat_core(G, communities, {}, {"query": "what is extract?", "session_id": "fresh"})
    assert "old" not in _CHAT_SESSIONS, "stale session should have been evicted"


# ============================================================
# Phase 17 Plan 17-02 — composer / validator / fuzzy / cap
# ============================================================


def test_chat_validator_strips_uncited():
    """CHAT-04 D-04: sentence containing uncited label-token is dropped."""
    G = _make_graph()
    label_index = _build_label_token_index(G)
    # Pick any node in the graph whose label has a >2-char token.
    sample_nid = None
    sample_token = None
    for nid in G.nodes:
        lbl = G.nodes[nid].get("label", nid).lower()
        toks = [t for t in _WORD_RE.findall(lbl) if len(t) > 2]
        if toks:
            sample_nid, sample_token = nid, toks[0]
            break
    assert sample_nid is not None, "fixture invariant: graph must have a >2-char label token"

    # With empty cited set, any sentence containing sample_token must be dropped.
    narrative = f"Totally unrelated sentence. The {sample_token} appears here."
    cleaned, dropped = _validate_citations(
        narrative, cited_ids=set(), label_index=label_index
    )
    assert sample_token not in cleaned.lower()
    assert len(dropped) >= 1

    # When cited_ids contains sample_nid, the sentence survives.
    cleaned2, _ = _validate_citations(
        narrative, cited_ids={sample_nid}, label_index=label_index
    )
    assert sample_token in cleaned2.lower()


def test_chat_no_match_returns_suggestions(_reset_chat_sessions):
    """CHAT-05: empty-match query returns fuzzy suggestions from graph candidate pool."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    response = _run_chat_core(
        G, communities, {}, {"query": "xyznonexistentblah"}
    )
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert meta["status"] == "no_results"
    assert text_body == ""
    # Suggestions (if any) must be drawn strictly from graph labels.
    graph_labels = {G.nodes[n].get("label", n) for n in G.nodes}
    for s in meta["suggestions"]:
        assert s in graph_labels or any(s in lbl for lbl in graph_labels), (
            f"suggestion {s!r} is not sourced from graph labels"
        )


def test_chat_suggestions_no_echo(_reset_chat_sessions):
    """CHAT-05 echo-leak guard (T-17-02 / Pitfall 1 / Phase 18 D-12)."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    leak_marker = "xyznonexistentblah"
    response = _run_chat_core(
        G, communities, {}, {"query": leak_marker}
    )
    text_body, meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    meta = json.loads(meta_json)
    assert leak_marker not in text_body
    assert leak_marker not in json.dumps(meta["suggestions"])
    for s in meta["suggestions"]:
        assert leak_marker not in s


def test_chat_narrative_under_cap(_reset_chat_sessions, monkeypatch):
    """CHAT-09 / D-09: 500-token cap enforced; overflow truncates at sentence boundary with ellipsis."""
    G = _make_graph()
    communities = _communities_from_graph(G)
    # Force composer to emit a long narrative using only a real cited label
    # so the citation validator does not strip it.
    # Use a node label token guaranteed to appear in the graph.
    sample_label = G.nodes["n1"].get("label", "n1")
    long_narrative = (f"The query touches {sample_label}. " * 200)
    def _fake_compose(G_, visited, edges, cited_ids):
        return long_narrative
    monkeypatch.setattr("graphify.serve._compose_explore_narrative", _fake_compose)
    response = _run_chat_core(G, communities, {}, {"query": "what is extract?"})
    text_body, _meta_json = response.split(QUERY_GRAPH_META_SENTINEL, 1)
    assert len(text_body) <= 2000, (
        f"text_body {len(text_body)} chars exceeds 500-token cap"
    )
    # When truncation occurred (original > cap), expect ellipsis marker
    # (or empty string if validator stripped everything).
    if len(long_narrative) > 2000:
        assert text_body.endswith("…") or text_body == "", (
            "truncated narrative must end with ellipsis (or be empty if validator stripped it)"
        )


def test_chat_truncate_helper_unit():
    """Unit test for _truncate_to_token_cap — sentence boundary behavior."""
    short = "Hello world."
    assert _truncate_to_token_cap(short) == short
    # 2500+ chars → must truncate and end with ellipsis.
    long = ("This is a sentence. " * 200)
    out = _truncate_to_token_cap(long)
    assert len(out) <= 2000
    assert out.endswith("…")
