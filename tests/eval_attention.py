"""
Graphify evaluation script — Transformer/Attention paper corpus.
Runs the full pipeline with a simulated Claude extraction JSON.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path

# Make sure we can import graphify from src/
sys.path.insert(0, str(Path(__file__).parent / "src"))

from graphify import detector, ast_extractor, graph_builder, clusterer, analyzer, reporter

# ── 1. Detection ──────────────────────────────────────────────────────────────
RAW = Path("/home/safi/graphify_test/raw")
detection = detector.detect(RAW)
print("=== Detection ===")
print(json.dumps(detection, indent=2))

# ── 2. AST extraction from .py files ─────────────────────────────────────────
py_files = [Path(f) for f in detection["files"].get("code", [])]
ast_result = ast_extractor.extract(py_files) if py_files else {"nodes": [], "edges": []}
print(f"\n=== AST extraction: {len(ast_result['nodes'])} nodes, {len(ast_result['edges'])} edges ===")

# ── 3. Simulated Claude extraction (realistic paper knowledge graph) ──────────
SOURCE_MD = str(RAW / "attention_notes.md")
SOURCE_CFG = str(RAW / "config.md")

simulated_extraction = {
    "nodes": [
        # Core architecture concepts
        {"id": "transformer",           "label": "Transformer",               "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3"},
        {"id": "encoder_layer",         "label": "EncoderLayer",              "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.1"},
        {"id": "decoder_layer",         "label": "DecoderLayer",              "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.1"},
        # Attention mechanism
        {"id": "multi_head_attention",  "label": "MultiHeadAttention",        "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.2"},
        {"id": "scaled_dot_product",    "label": "ScaledDotProductAttention", "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.2.1"},
        # Sub-components
        {"id": "feed_forward",          "label": "FeedForward",               "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.3"},
        {"id": "layer_norm",            "label": "LayerNorm",                 "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.1"},
        {"id": "positional_encoding",   "label": "PositionalEncoding",        "file_type": "paper", "source_file": SOURCE_MD, "source_location": "Sec 3.5"},
        # Hyperparameters — from config.md
        {"id": "d_model",               "label": "d_model",                   "file_type": "document", "source_file": SOURCE_CFG, "source_location": "L3"},
        {"id": "num_heads",             "label": "num_heads",                 "file_type": "document", "source_file": SOURCE_CFG, "source_location": "L4"},
        {"id": "dropout",               "label": "dropout",                   "file_type": "document", "source_file": SOURCE_CFG, "source_location": "L7"},
    ],
    "edges": [
        # Transformer contains encoder and decoder stacks
        {"source": "transformer",          "target": "encoder_layer",        "relation": "contains",          "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        {"source": "transformer",          "target": "decoder_layer",        "relation": "contains",          "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        # EncoderLayer uses multi-head attention and feed-forward
        {"source": "encoder_layer",        "target": "multi_head_attention", "relation": "uses",              "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        {"source": "encoder_layer",        "target": "feed_forward",         "relation": "uses",              "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        {"source": "encoder_layer",        "target": "layer_norm",           "relation": "applies",           "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        # DecoderLayer uses multi-head attention (self + cross) and feed-forward
        {"source": "decoder_layer",        "target": "multi_head_attention", "relation": "uses",              "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        {"source": "decoder_layer",        "target": "feed_forward",         "relation": "uses",              "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        {"source": "decoder_layer",        "target": "layer_norm",           "relation": "applies",           "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        # MultiHeadAttention implements ScaledDotProduct internally
        {"source": "multi_head_attention", "target": "scaled_dot_product",   "relation": "implements",        "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        # Hyperparameter relationships — from config.md to architecture nodes
        {"source": "multi_head_attention", "target": "d_model",              "relation": "parameterized_by",  "confidence": "EXTRACTED", "source_file": SOURCE_CFG, "weight": 1.0},
        {"source": "multi_head_attention", "target": "num_heads",            "relation": "parameterized_by",  "confidence": "EXTRACTED", "source_file": SOURCE_CFG, "weight": 1.0},
        {"source": "scaled_dot_product",   "target": "d_model",              "relation": "scales_by",         "confidence": "INFERRED",  "source_file": SOURCE_MD,  "weight": 0.8},
        {"source": "feed_forward",         "target": "d_model",              "relation": "parameterized_by",  "confidence": "EXTRACTED", "source_file": SOURCE_CFG, "weight": 1.0},
        # Positional encoding connects to transformer input (cross-community link)
        {"source": "positional_encoding",  "target": "transformer",          "relation": "feeds_into",        "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
        {"source": "positional_encoding",  "target": "d_model",              "relation": "dimensioned_by",    "confidence": "INFERRED",  "source_file": SOURCE_MD,  "weight": 0.8},
        # Dropout applied across sub-layers — ambiguous which specific sublayer
        {"source": "dropout",              "target": "multi_head_attention",  "relation": "regularizes",      "confidence": "AMBIGUOUS", "source_file": SOURCE_CFG, "weight": 0.6},
        {"source": "dropout",              "target": "feed_forward",          "relation": "regularizes",      "confidence": "AMBIGUOUS", "source_file": SOURCE_CFG, "weight": 0.6},
        # Cross-community bridge: LayerNorm and PositionalEncoding both affect d_model scale
        {"source": "layer_norm",           "target": "positional_encoding",  "relation": "operates_at_same_scale_as", "confidence": "INFERRED", "source_file": SOURCE_MD, "weight": 0.7},
        # Encoder-Decoder cross-attention: DecoderLayer attends to encoder output
        {"source": "decoder_layer",        "target": "encoder_layer",        "relation": "cross_attends_to",  "confidence": "EXTRACTED", "source_file": SOURCE_MD, "weight": 1.0},
    ],
    "input_tokens": 3200,
    "output_tokens": 820,
}

# ── 4. Merge AST + simulated Claude extraction ────────────────────────────────
all_extractions = [simulated_extraction]
if ast_result["nodes"]:
    all_extractions.append(ast_result)

G = graph_builder.build(all_extractions)
print(f"\n=== Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges ===")

# ── 5. Community detection ────────────────────────────────────────────────────
communities = clusterer.cluster(G)
cohesion = clusterer.score_all(G, communities)
print(f"\n=== Communities: {len(communities)} detected ===")
for cid, nodes in communities.items():
    node_labels = [G.nodes[n].get("label", n) for n in nodes]
    print(f"  Community {cid} ({len(nodes)} nodes): {node_labels}")
    print(f"    Cohesion: {cohesion[cid]}")

# ── 6. Analysis ───────────────────────────────────────────────────────────────
god_node_list = analyzer.god_nodes(G, top_n=10)
print(f"\n=== God Nodes ===")
for g in god_node_list:
    print(f"  {g['label']}: {g['edges']} edges")

surprise_list = analyzer.surprising_connections(G, communities=communities, top_n=5)
print(f"\n=== Surprising Connections: {len(surprise_list)} found ===")
for s in surprise_list:
    print(f"  {s['source']} <-> {s['target']} [{s['confidence']}]: {s['relation']}")
    print(f"    Note: {s.get('note', 'cross-file')}")

# ── 7. Community labels (hand-crafted for accuracy) ───────────────────────────
# We label based on which nodes ended up in which community
community_labels = {}
for cid, nodes in communities.items():
    node_labels_set = {G.nodes[n].get("label", n) for n in nodes}
    if "MultiHeadAttention" in node_labels_set or "ScaledDotProductAttention" in node_labels_set:
        community_labels[cid] = "Attention Mechanism"
    elif "Transformer" in node_labels_set or "EncoderLayer" in node_labels_set:
        community_labels[cid] = "Encoder-Decoder Architecture"
    elif "d_model" in node_labels_set or "num_heads" in node_labels_set or "dropout" in node_labels_set:
        community_labels[cid] = "Hyperparameters & Configuration"
    elif "PositionalEncoding" in node_labels_set:
        community_labels[cid] = "Positional Encoding & Embedding"
    elif any(label.endswith(".py") or "()" in label for label in node_labels_set):
        community_labels[cid] = "Code Implementation"
    else:
        community_labels[cid] = f"Cluster {cid}"

token_cost = {"input": simulated_extraction["input_tokens"], "output": simulated_extraction["output_tokens"]}

# ── 8. Report ─────────────────────────────────────────────────────────────────
report = reporter.generate(
    G=G,
    communities=communities,
    cohesion_scores=cohesion,
    community_labels=community_labels,
    god_node_list=god_node_list,
    surprise_list=surprise_list,
    detection_result=detection,
    token_cost=token_cost,
    root=str(RAW),
)

out_path = Path("/tmp/GRAPH_REPORT_attention.md")
out_path.write_text(report)
print(f"\n=== Report written to {out_path} ===")
print(report)
