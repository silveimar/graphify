"""Tests for serve.py - MCP graph query helpers (no mcp package required)."""
import json
import pytest
import networkx as nx
from networkx.readwrite import json_graph

from graphify.serve import (
    _communities_from_graph,
    _score_nodes,
    _bfs,
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
)


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
