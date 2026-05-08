"""Phase 73 DEDUP measurement-only spike.

Computes near-duplicate concept-node rate over one or more graph.json files,
cross-checks against semantically_similar_to edges, and emits markdown stats.

No graphify production code changes. See .planning/phases/73-dedup/73-CONTEXT.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

CONCEPT_FILE_TYPES = {"document", "paper", "image", "rationale"}


def normalize(s: str | None) -> str:
    """CONTEXT recipe: lower -> strip [^\\w\\s] -> collapse whitespace."""
    if not s:
        return ""
    stripped = _PUNCT_RE.sub("", s.lower())
    return " ".join(stripped.split())


def _description_for(node: dict) -> str:
    """Per research: enriched_description preferred, falls back to description, then ''."""
    return node.get("enriched_description") or node.get("description") or ""


def fingerprint(label: str, description: str | None) -> str:
    """sha256(norm(label) + '|' + norm(description[:200]))."""
    desc = (description or "")[:200]
    payload = normalize(label) + "|" + normalize(desc)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_concept_nodes(nodes: list[dict], include_code: bool = False) -> list[dict]:
    allowed = set(CONCEPT_FILE_TYPES)
    if include_code:
        allowed.add("code")
    return [n for n in nodes if n.get("file_type") in allowed]


def group_by_fingerprint(nodes: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for n in nodes:
        fp = fingerprint(n.get("label", ""), _description_for(n))
        groups[fp].append(n)
    return {fp: ns for fp, ns in groups.items() if len(ns) > 1}


def semsim_pairs(edges: list[dict], min_score: float = 0.0) -> set[frozenset]:
    pairs: set[frozenset] = set()
    for e in edges:
        if e.get("relation") != "semantically_similar_to":
            continue
        score = e.get("confidence_score", 1.0)
        if score is not None and score < min_score:
            continue
        pairs.add(frozenset((e["source"], e["target"])))
    return pairs


def collision_is_covered(group: list[dict], semsim: set[frozenset]) -> bool:
    ids = [n["id"] for n in group]
    for nid in ids:
        if not any(frozenset((nid, other)) in semsim for other in ids if other != nid):
            return False
    return True


def load_graph_json(path: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    edges = data.get("links") or data.get("edges") or []
    return nodes, edges


def classify_corpus(
    nodes: list[dict],
    edges: list[dict],
    include_code: bool,
    min_score: float,
) -> dict:
    concepts = select_concept_nodes(nodes, include_code=include_code)
    total = len(concepts)
    groups = group_by_fingerprint(concepts)
    pairs = semsim_pairs(edges, min_score=min_score)

    raw_collision_node_ids: set[str] = set()
    residual_collision_node_ids: set[str] = set()
    for fp, group in groups.items():
        for n in group:
            raw_collision_node_ids.add(n["id"])
        if not collision_is_covered(group, pairs):
            for n in group:
                residual_collision_node_ids.add(n["id"])

    return {
        "total_concept_nodes": total,
        "collision_groups": len(groups),
        "raw_collision_nodes": len(raw_collision_node_ids),
        "residual_collision_nodes": len(residual_collision_node_ids),
        "raw_rate": (len(raw_collision_node_ids) / total) if total else 0.0,
        "residual_rate": (len(residual_collision_node_ids) / total) if total else 0.0,
        "groups": groups,
    }


def emit_markdown(per_corpus: dict[str, dict], min_score: float) -> str:
    lines: list[str] = []
    lines.append("## Results\n")
    lines.append(f"_sem-sim min_score threshold: {min_score}_\n")
    lines.append("| Corpus | Concept Nodes | Collision Groups | Raw Nodes | Residual Nodes | Raw % | Residual % |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    agg_total = 0
    agg_raw = 0
    agg_residual = 0
    agg_groups = 0
    for name, stats in per_corpus.items():
        lines.append(
            f"| {name} | {stats['total_concept_nodes']} | {stats['collision_groups']} | "
            f"{stats['raw_collision_nodes']} | {stats['residual_collision_nodes']} | "
            f"{stats['raw_rate'] * 100:.2f}% | {stats['residual_rate'] * 100:.2f}% |"
        )
        agg_total += stats["total_concept_nodes"]
        agg_raw += stats["raw_collision_nodes"]
        agg_residual += stats["residual_collision_nodes"]
        agg_groups += stats["collision_groups"]
    agg_raw_rate = (agg_raw / agg_total) if agg_total else 0.0
    agg_residual_rate = (agg_residual / agg_total) if agg_total else 0.0
    lines.append(
        f"| **AGGREGATE** | {agg_total} | {agg_groups} | {agg_raw} | {agg_residual} | "
        f"{agg_raw_rate * 100:.2f}% | {agg_residual_rate * 100:.2f}% |"
    )
    lines.append("")

    decision = "Ship" if (agg_raw_rate > 0.05 and agg_residual_rate > 0.05) else "Defer"
    lines.append(f"**Aggregate decision (raw>5% AND residual>5%): {decision}**\n")

    lines.append("## Appendix: Collision Sample (first 20 groups across corpora)\n")
    lines.append("| Corpus | Fingerprint (8) | Group Size | Labels (truncated) | Source Files |")
    lines.append("|---|---|---:|---|---|")
    shown = 0
    for name, stats in per_corpus.items():
        for fp, group in stats["groups"].items():
            if shown >= 20:
                break
            labels = " // ".join(sorted({(n.get("label") or "")[:60] for n in group}))
            sources = " // ".join(sorted({(n.get("source_file") or "")[:60] for n in group}))
            lines.append(f"| {name} | `{fp[:8]}` | {len(group)} | {labels} | {sources} |")
            shown += 1
        if shown >= 20:
            break
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Phase 73 dedup measurement spike")
    p.add_argument("graphs", nargs="+", help="One or more graph.json paths (label them with name=path)")
    p.add_argument("--min-score", type=float, default=0.0, help="sem-sim confidence_score threshold (default 0.0 = any edge counts)")
    p.add_argument("--include-code", action="store_true", help="Also fingerprint file_type=code nodes")
    args = p.parse_args(argv)

    per_corpus: dict[str, dict] = {}
    for entry in args.graphs:
        if "=" in entry:
            name, raw_path = entry.split("=", 1)
        else:
            raw_path = entry
            name = Path(raw_path).parent.parent.name or raw_path
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            print(f"[dedup_spike] missing: {path}", file=sys.stderr)
            return 2
        nodes, edges = load_graph_json(path)
        per_corpus[name] = classify_corpus(
            nodes, edges, include_code=args.include_code, min_score=args.min_score
        )

    sys.stdout.write(emit_markdown(per_corpus, args.min_score))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
