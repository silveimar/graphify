"""Post-extraction entity deduplication (Phase 10, GRAPH-02/03/04).

Merges fuzzy-matched and embedding-similar nodes into canonical entities
with aggregated edges. Pure function: takes an extraction dict, returns
(dedup'd_extraction, report_dict). Never mutates inputs; never touches
NetworkX graphs (per RESEARCH.md Pitfall 1).

Run as a pipeline stage: detect -> extract -> dedup -> build_graph (D-03).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import networkx as nx

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    _HAS_SENTENCE_TRANSFORMERS = False

from graphify.security import sanitize_label, sanitize_label_md

# ---------- Constants ----------

_MODEL: "SentenceTransformer | None" = None
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_DEFAULT_FUZZY_THRESHOLD = 0.90   # D-02
_DEFAULT_EMBED_THRESHOLD = 0.85   # D-02
_LENGTH_RATIO_GUARD = 0.7         # RESEARCH Pattern 3
_PREFIX_LEN = 4                   # RESEARCH Pattern 3
_COSINE_DECIMALS = 3              # RESEARCH determinism note

CONFIDENCE_ORDER = {"EXTRACTED": 2, "INFERRED": 1, "AMBIGUOUS": 0}  # D-10


# ---------- Public API ----------

def dedup(
    extraction: dict,
    *,
    fuzzy_threshold: float = _DEFAULT_FUZZY_THRESHOLD,
    embed_threshold: float = _DEFAULT_EMBED_THRESHOLD,
    cross_type: bool = False,
    encoder: Callable[[list[str]], Any] | None = None,
) -> tuple[dict, dict]:
    """Merge fuzzy+embedding-similar nodes. Returns (dedup'd extraction, report).

    Parameters
    ----------
    extraction : dict
        Must contain "nodes" (list[dict]) and "edges" (list[dict]) keyed
        by the graphify schema (see validate.py).
    fuzzy_threshold : float
        Minimum difflib.SequenceMatcher.ratio() for same-type merges (D-02).
    embed_threshold : float
        Minimum cosine similarity for ALL merges (D-02). Always applied
        even when cross_type=True.
    cross_type : bool
        D-13. If False (default), pairs with differing file_type never merge.
        If True, cross-type pairs bypass the fuzzy gate entirely and use
        cosine alone (RESEARCH Pitfall 4).
    encoder : callable | None
        Inject a mock encoder for testing. Must accept list[str] and return
        an array-like of shape (N, 384) with L2-normalized rows. When None,
        the real sentence-transformers model is loaded lazily on first call.

    Returns
    -------
    (dedup'd_extraction, report_dict)
        dedup'd_extraction has the same schema as the input but with
        eliminated nodes removed, canonical nodes annotated with
        merged_from/source_file-as-list, and edges re-routed + aggregated.
        report_dict matches the schema in the plan interfaces spec.
    """
    nodes = list(extraction.get("nodes", []))
    edges = list(extraction.get("edges", []))
    total_before = len(nodes)

    if total_before == 0:
        return extraction, _empty_report(total_before, 0)

    # Step 1: pre-dedup undirected graph degree (D-09 tie-break)
    pre_degree = _compute_pre_degree(nodes, edges)

    # Step 2: blocking + candidate pairs
    blocks = _build_prefix_blocks(nodes)
    candidates = _candidate_pairs(
        nodes, blocks,
        fuzzy_threshold=fuzzy_threshold,
        cross_type=cross_type,
    )

    # Step 3: embedding gate (only for candidates that passed fuzzy or cross-type)
    passing = _apply_embedding_gate(
        nodes, candidates, encoder=encoder,
        embed_threshold=embed_threshold,
        cross_type=cross_type,
    )

    # Step 4: union-find to group transitively-merging nodes
    groups = _union_groups(passing, n_nodes=len(nodes))

    # Step 5: canonical selection + merge map + provenance
    nodes_by_id = {n["id"]: n for n in nodes}
    merge_map: dict[str, str] = {}
    provenance: dict[str, list[str]] = defaultdict(list)
    scores_by_canonical: dict[str, dict] = {}

    for group_indices in groups:
        if len(group_indices) < 2:
            continue
        group_ids = [nodes[i]["id"] for i in group_indices]
        canonical = _select_canonical(group_ids, nodes_by_id, pre_degree)
        eliminated = [nid for nid in group_ids if nid != canonical]
        for elim in eliminated:
            merge_map[elim] = canonical
            provenance[canonical].append(elim)
        # Track best fuzzy + cosine scores for the merge report
        group_set = set(group_indices)
        group_scores = [
            (fuzzy, cos) for (a, b, fuzzy, cos) in passing
            if a in group_set and b in group_set
        ]
        if group_scores:
            scores_by_canonical[canonical] = {
                "fuzzy_score": round(max(f for f, _ in group_scores), 3),
                "cosine_score": round(max(c for _, c in group_scores), 3),
            }

    # Step 6: apply merge to extraction dict (edges + nodes)
    new_extraction = _merge_extraction(extraction, merge_map, provenance)

    # Step 7: build report
    report = _build_report(
        total_before=total_before,
        total_after=len(new_extraction["nodes"]),
        merge_map=merge_map,
        provenance=provenance,
        nodes_by_id=nodes_by_id,
        scores=scores_by_canonical,
    )
    return new_extraction, report


def write_dedup_reports(report: dict, out_dir: Path) -> None:
    """Atomically write dedup_report.json and dedup_report.md inside out_dir.

    T-10-01 mitigation: `out_dir` is resolved and must be a subdirectory of
    the current working directory (or the graphify-out/ conventional root).
    T-10-02 mitigation: all canonical labels pass through sanitize_label()
    before embedding in the .md output.
    """
    out_dir = Path(out_dir).resolve()
    cwd = Path.cwd().resolve()
    # Path confinement: out_dir must live under cwd (standard graphify-out/ pattern)
    try:
        out_dir.relative_to(cwd)
    except ValueError as e:
        raise ValueError(
            f"dedup_report output path {out_dir!s} escapes working directory {cwd!s}"
        ) from e
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "dedup_report.json"
    md_path = out_dir / "dedup_report.md"

    # Atomic JSON write (cache.py pattern)
    tmp_json = json_path.with_suffix(".json.tmp")
    try:
        tmp_json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp_json, json_path)
    except Exception:
        tmp_json.unlink(missing_ok=True)
        raise

    # Atomic MD write with sanitized labels (T-10-02)
    md_body = _render_dedup_md(report)
    tmp_md = md_path.with_suffix(".md.tmp")
    try:
        tmp_md.write_text(md_body, encoding="utf-8")
        os.replace(tmp_md, md_path)
    except Exception:
        tmp_md.unlink(missing_ok=True)
        raise


def corpus_hash(file_paths: list[str]) -> str:
    """SHA256 over sorted per-file hashes (RESEARCH Pattern 9).

    Exposed for the skill / CLI to key the dedup cache. Adding one file
    changes the corpus hash, invalidating any cached dedup result.
    """
    from graphify.cache import file_hash
    sorted_hashes = sorted(file_hash(Path(p)) for p in file_paths)
    return hashlib.sha256(json.dumps(sorted_hashes).encode()).hexdigest()


# ---------- Private helpers ----------

def _get_model() -> "SentenceTransformer":
    """Lazy-load all-MiniLM-L6-v2. Raises if optional [dedup] extra not installed."""
    global _MODEL
    if not _HAS_SENTENCE_TRANSFORMERS:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Run: pip install 'graphifyy[dedup]'"
        )
    if _MODEL is None:
        print(f"[graphify] Loading embedding model {_MODEL_NAME} ...", file=sys.stderr)
        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


def _encode_labels(labels: list[str], encoder: Callable | None) -> Any:
    """Encode labels using injected callable or lazy-loaded real model."""
    if encoder is not None:
        return encoder(labels)
    model = _get_model()
    return model.encode(
        labels, normalize_embeddings=True,
        batch_size=64, show_progress_bar=False,
    )


def _fuzzy_ratio(a: str, b: str) -> float:
    """Case-insensitive difflib ratio (RESEARCH Pattern 2)."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _build_prefix_blocks(nodes: list[dict]) -> dict[str, list[int]]:
    """Group node indices by lowercased 4-char label prefix (RESEARCH Pattern 3)."""
    blocks: dict[str, list[int]] = {}
    for i, node in enumerate(nodes):
        label = node.get("label", "")
        key = label.lower()[:_PREFIX_LEN]
        blocks.setdefault(key, []).append(i)
    return blocks


def _candidate_pairs(
    nodes: list[dict],
    blocks: dict[str, list[int]],
    *,
    fuzzy_threshold: float,
    cross_type: bool,
) -> list[tuple[int, int, float]]:
    """Return (i, j, fuzzy_ratio) tuples for pairs passing:

    - same prefix block
    - length ratio >= 0.7 (cheap guard)
    - fuzzy ratio >= threshold IF same file_type
    - when cross_type=True: cross-type pairs pass with fuzzy_ratio = 0.0
      (they still need cosine gate later; see _apply_embedding_gate)

    Same-type candidates always satisfy the fuzzy gate here. Cross-type
    candidates are emitted with fuzzy=0.0 as a sentinel so the embedding
    gate can treat them separately (Pitfall 4).
    """
    candidates: list[tuple[int, int, float]] = []
    for block in blocks.values():
        for ki in range(len(block)):
            i = block[ki]
            for j in block[ki + 1:]:
                li = len(nodes[i].get("label", ""))
                lj = len(nodes[j].get("label", ""))
                if li == 0 or lj == 0:
                    continue
                length_ratio = min(li, lj) / max(li, lj)
                same_type = nodes[i].get("file_type") == nodes[j].get("file_type")

                if same_type:
                    if length_ratio < _LENGTH_RATIO_GUARD:
                        continue
                    fuzzy = _fuzzy_ratio(
                        nodes[i].get("label", ""), nodes[j].get("label", ""),
                    )
                    if fuzzy >= fuzzy_threshold:
                        candidates.append((i, j, fuzzy))
                else:
                    # Cross-type pair (D-13)
                    if not cross_type:
                        continue
                    # Bypass fuzzy gate; emit with sentinel 0.0
                    candidates.append((i, j, 0.0))
    return candidates


def _apply_embedding_gate(
    nodes: list[dict],
    candidates: list[tuple[int, int, float]],
    *,
    encoder: Callable | None,
    embed_threshold: float,
    cross_type: bool,
) -> list[tuple[int, int, float, float]]:
    """Run embedding cosine gate (D-02).

    Returns list of (i, j, fuzzy_ratio, cosine) tuples that passed the gate.
    If candidates is empty, skip encoding entirely (avoids loading model).
    """
    if not candidates:
        return []

    # Encode ALL candidate node labels (dedup set for reuse)
    indices = sorted({i for pair in candidates for i in pair[:2]})
    labels_to_encode = [nodes[i].get("label", "") for i in indices]
    embeddings = _encode_labels(labels_to_encode, encoder)
    idx_to_row = {idx: row for row, idx in enumerate(indices)}

    passing: list[tuple[int, int, float, float]] = []
    for i, j, fuzzy in candidates:
        vec_i = embeddings[idx_to_row[i]]
        vec_j = embeddings[idx_to_row[j]]
        cosine = _cosine(vec_i, vec_j)
        if cosine >= embed_threshold:
            passing.append((i, j, fuzzy, cosine))
    return passing


def _cosine(a: Any, b: Any) -> float:
    """Cosine similarity on L2-normalized vectors == dot product. Rounded 3 decimals."""
    if np is None:
        raise RuntimeError("numpy is required for dedup; install '[dedup]' extra")
    return round(float(np.dot(a, b)), _COSINE_DECIMALS)


def _union_groups(
    passing: list[tuple[int, int, float, float]],
    n_nodes: int,
) -> list[list[int]]:
    """Union-find over passing pairs. Returns list of groups (each a list of node indices).

    Nodes not in any pair are omitted from the result (no-op groups).
    """
    parent = list(range(n_nodes))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i, j, _, _ in passing:
        union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    seen = {i for pair in passing for i in pair[:2]}
    for idx in sorted(seen):
        groups[find(idx)].append(idx)
    return [sorted(g) for g in groups.values()]


def _compute_pre_degree(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """D-09 tie-break source: degree on the pre-dedup undirected graph.

    Built from the extraction dict directly (no build_from_json dependency).
    """
    G = nx.Graph()
    for node in nodes:
        G.add_node(node["id"])
    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src in G and tgt in G:
            G.add_edge(src, tgt)
    return dict(G.degree())


def _select_canonical(
    candidate_ids: list[str],
    nodes_by_id: dict[str, dict],
    pre_degree: dict[str, int],
) -> str:
    """D-09: longest label -> most-connected (pre-dedup degree) -> alphabetical."""
    def sort_key(nid: str) -> tuple:
        label = nodes_by_id.get(nid, {}).get("label", "")
        degree = pre_degree.get(nid, 0)
        return (-len(label), -degree, label)
    return sorted(candidate_ids, key=sort_key)[0]


def _merge_extraction(
    extraction: dict,
    merge_map: dict[str, str],
    provenance: dict[str, list[str]],
) -> dict:
    """Apply merge_map to extraction dict (RESEARCH Pattern 4). Pure function.

    Operates on dicts only — never on NetworkX graphs (Pitfall 1 compliance). Handles:
    - eliminated nodes removed, canonical nodes updated in place (on a copy)
    - merged_from list populated with eliminated IDs (deduped, sorted)
    - source_file becomes sorted list[str] for canonicals with >1 contributing file
    - edges re-routed; parallel edges grouped by (new_src, new_tgt, relation)
    - self-loops (new_src == new_tgt) dropped (Pitfall 6)
    - parallel edges aggregated: weight=sum, confidence_score=max,
      confidence enum = max by CONFIDENCE_ORDER, source_file union sorted
    """
    if not merge_map:
        # No merges — return shallow-copied dict so callers can safely mutate
        return {**extraction}

    # Build canonical node dict
    nodes_by_id: dict[str, dict] = {}
    eliminated_ids = set(merge_map.keys())

    # First pass: canonicals as-is, skip eliminated for now
    for node in extraction.get("nodes", []):
        nid = node["id"]
        if nid in eliminated_ids:
            continue
        nodes_by_id[nid] = dict(node)

    # Second pass: fold eliminated into their canonicals (provenance + source_file union)
    for node in extraction.get("nodes", []):
        nid = node["id"]
        if nid not in eliminated_ids:
            continue
        canonical_id = merge_map[nid]
        canon = nodes_by_id.get(canonical_id)
        if canon is None:
            # Safety guard: canonical not found (should not happen)
            continue
        # Merge source_file (str -> list[str])
        existing = canon.get("source_file", "")
        sf_list = list(existing) if isinstance(existing, list) else ([existing] if existing else [])
        incoming = node.get("source_file", "")
        if isinstance(incoming, list):
            for s in incoming:
                if s and s not in sf_list:
                    sf_list.append(s)
        elif incoming and incoming not in sf_list:
            sf_list.append(incoming)
        # Normalize: single string if only one entry, else sorted list
        canon["source_file"] = sorted(sf_list) if len(sf_list) > 1 else (sf_list[0] if sf_list else "")

    # merged_from: attach to each canonical
    for canonical_id, eliminated_list in provenance.items():
        if canonical_id in nodes_by_id:
            nodes_by_id[canonical_id]["merged_from"] = sorted(set(eliminated_list))

    # Re-route + aggregate edges
    edge_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for edge in extraction.get("edges", []):
        new_src = merge_map.get(edge["source"], edge["source"])
        new_tgt = merge_map.get(edge["target"], edge["target"])
        if new_src == new_tgt:
            continue  # Pitfall 6: drop self-loops from merges
        key = (new_src, new_tgt, edge.get("relation", ""))
        e = dict(edge)
        e["source"] = new_src
        e["target"] = new_tgt
        edge_groups[key].append(e)

    merged_edges: list[dict] = []
    for _, group in edge_groups.items():
        if len(group) == 1:
            merged_edges.append(group[0])
            continue
        merged = dict(group[0])
        merged["weight"] = sum(e.get("weight", 1.0) for e in group)
        merged["confidence_score"] = max(
            (e.get("confidence_score", 0.0) for e in group), default=0.0
        )
        merged["confidence"] = max(
            group,
            key=lambda e: CONFIDENCE_ORDER.get(e.get("confidence", "AMBIGUOUS"), 0),
        )["confidence"]
        sf_set = {e["source_file"] for e in group if e.get("source_file")}
        if len(sf_set) > 1:
            merged["source_file"] = sorted(sf_set)
        elif sf_set:
            merged["source_file"] = next(iter(sf_set))
        merged_edges.append(merged)

    return {
        **extraction,
        "nodes": list(nodes_by_id.values()),
        "edges": merged_edges,
    }


def _build_report(
    *,
    total_before: int,
    total_after: int,
    merge_map: dict[str, str],
    provenance: dict[str, list[str]],
    nodes_by_id: dict[str, dict],
    scores: dict[str, dict],
) -> dict:
    """Build the dedup_report dict (see plan interfaces schema)."""
    merges_list: list[dict] = []
    for canonical_id, eliminated_ids in sorted(provenance.items()):
        canon = nodes_by_id.get(canonical_id, {})
        eliminated_records = []
        for elim in sorted(set(eliminated_ids)):
            n = nodes_by_id.get(elim, {})
            eliminated_records.append({
                "id": elim,
                "label": n.get("label", ""),
                "source_file": n.get("source_file", ""),
            })
        score = scores.get(canonical_id, {"fuzzy_score": 0.0, "cosine_score": 0.0})
        merges_list.append({
            "canonical_id": canonical_id,
            "canonical_label": canon.get("label", ""),
            "eliminated": eliminated_records,
            "fuzzy_score": score["fuzzy_score"],
            "cosine_score": score["cosine_score"],
        })
    return {
        "version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "total_nodes_before": total_before,
            "total_nodes_after": total_after,
            "merges": len(merges_list),
        },
        "alias_map": {k: v for k, v in sorted(merge_map.items())},
        "merges": merges_list,
    }


def _empty_report(total_before: int, total_after: int) -> dict:
    """Build an empty dedup report with zero merges."""
    return {
        "version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "total_nodes_before": total_before,
            "total_nodes_after": total_after,
            "merges": 0,
        },
        "alias_map": {},
        "merges": [],
    }


def _render_dedup_md(report: dict) -> str:
    """Render dedup_report.md with sanitized labels (T-10-02)."""
    summary = report.get("summary", {})
    lines: list[str] = [
        "# Entity Dedup Report",
        "",
        f"- Version: {report.get('version', '1')}",
        f"- Generated: {report.get('generated_at', '')}",
        f"- Nodes before: {summary.get('total_nodes_before', 0)}",
        f"- Nodes after: {summary.get('total_nodes_after', 0)}",
        f"- Merges: {summary.get('merges', 0)}",
        "",
        "## Merges",
        "",
    ]
    for merge in report.get("merges", []):
        # T-10-02: strip control chars + cap length (sanitize_label), then strip
        # markdown structural chars incl. backticks (sanitize_label_md). Mirrors
        # report.py:_sanitize_md so both reports render canonical labels identically.
        canon_label = sanitize_label_md(sanitize_label(merge.get("canonical_label", "")))
        eliminated_labels = ", ".join(
            sanitize_label_md(sanitize_label(e.get("label", e.get("id", ""))))
            for e in merge.get("eliminated", [])
        )
        lines.append(
            f"- `{canon_label}` ← {eliminated_labels}  "
            f"[fuzzy={merge.get('fuzzy_score', 0):.3f}, cos={merge.get('cosine_score', 0):.3f}]"
        )
    if not report.get("merges"):
        lines.append("_No merges._")
    return "\n".join(lines) + "\n"
