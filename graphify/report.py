# generate GRAPH_REPORT.md - the human-readable audit trail
from __future__ import annotations
import re
import statistics
from datetime import date
import networkx as nx
from graphify.security import sanitize_label


def _fmt_source(value) -> str:
    """Render a source_file value as a display string.

    Defends against list[str] values reaching the renderer even if
    analyze.py already flattened them — defense-in-depth per T-10-08-02.

    list[str] -> comma-joined string
    str       -> unchanged
    other     -> str(value) or ""
    """
    if isinstance(value, list):
        return ", ".join(v for v in value if v) if value else ""
    return str(value or "")


def _safe_community_name(label: str) -> str:
    """Mirrors export.safe_name so community hub filenames and report wikilinks always agree."""
    cleaned = re.sub(r'[\\/*?:"<>|#^[\]]', "", label.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")).strip()
    cleaned = re.sub(r"\.(md|mdx|markdown)$", "", cleaned, flags=re.IGNORECASE)
    return cleaned or "unnamed"


def _compute_hot_cold(
    G: nx.Graph,
    counters: dict[str, int],
    hot_percentile: float = 0.90,
    cold_percentile: float = 0.10,
) -> dict:
    """Return hot paths and cold edges for Usage Patterns section. Per D-10."""
    if not counters:
        never = list(G.edges())
        return {"hot": [], "cold": [], "never_traversed": len(never), "total_queries": 0}

    all_counts = list(counters.values())
    total = sum(all_counts)

    if len(all_counts) >= 10:
        thresholds = statistics.quantiles(all_counts, n=10)
        hot_floor = thresholds[8]   # 90th percentile
        cold_ceil = thresholds[0]   # 10th percentile
    else:
        hot_floor = max(all_counts)
        cold_ceil = min(all_counts)

    hot = [(k, v) for k, v in counters.items() if v >= hot_floor]
    cold = [(k, v) for k, v in counters.items() if v <= cold_ceil and v > 0]
    never = [
        (u, v) for u, v, _ in G.edges(data=True)
        if f"{min(u, v)}:{max(u, v)}" not in counters
    ]
    hot.sort(key=lambda x: -x[1])
    cold.sort(key=lambda x: x[1])
    return {
        "hot": hot[:10],
        "cold": cold[:10],
        "never_traversed": len(never),
        "total_queries": total,
    }


def generate(
    G: nx.Graph,
    communities: dict[int, list[str]],
    cohesion_scores: dict[int, float],
    community_labels: dict[int, str],
    god_node_list: list[dict],
    surprise_list: list[dict],
    detection_result: dict,
    token_cost: dict,
    root: str,
    suggested_questions: list[dict] | None = None,
    usage_data: dict | None = None,
    dedup_report: dict | None = None,  # Phase 10, D-04
) -> str:
    today = date.today().isoformat()

    confidences = [d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True)]
    total = len(confidences) or 1
    ext_pct = round(confidences.count("EXTRACTED") / total * 100)
    inf_pct = round(confidences.count("INFERRED") / total * 100)
    amb_pct = round(confidences.count("AMBIGUOUS") / total * 100)

    inf_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("confidence") == "INFERRED"]
    inf_scores = [d.get("confidence_score", 0.5) for _, _, d in inf_edges]
    inf_avg = round(sum(inf_scores) / len(inf_scores), 2) if inf_scores else None

    lines = [
        f"# Graph Report - {root}  ({today})",
        "",
        "## Corpus Check",
    ]
    if detection_result.get("warning"):
        lines.append(f"- {detection_result['warning']}")
    else:
        lines += [
            f"- {detection_result['total_files']} files · ~{detection_result['total_words']:,} words",
            "- Verdict: corpus is large enough that graph structure adds value.",
        ]

    lines += [
        "",
        "## Summary",
        f"- {G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities detected",
        f"- Extraction: {ext_pct}% EXTRACTED · {inf_pct}% INFERRED · {amb_pct}% AMBIGUOUS"
        + (f" · INFERRED: {len(inf_edges)} edges (avg confidence: {inf_avg})" if inf_avg is not None else ""),
        f"- Token cost: {token_cost.get('input', 0):,} input · {token_cost.get('output', 0):,} output",
    ]

    # Community hub navigation - links to _COMMUNITY_*.md files in the Obsidian vault.
    # Without these, GRAPH_REPORT.md is a dead-end and the vault splits into disconnected components.
    if communities:
        lines += ["", "## Community Hubs (Navigation)"]
        for cid in communities:
            label = community_labels.get(cid, f"Community {cid}")
            safe = _safe_community_name(label)
            lines.append(f"- [[_COMMUNITY_{safe}|{label}]]")

    lines += [
        "",
        "## God Nodes (most connected - your core abstractions)",
    ]
    for i, node in enumerate(god_node_list, 1):
        lines.append(f"{i}. `{node['label']}` - {node['edges']} edges")

    lines += ["", "## Surprising Connections (you probably didn't know these)"]
    if surprise_list:
        for s in surprise_list:
            relation = s.get("relation", "related_to")
            note = s.get("note", "")
            files = s.get("source_files", ["", ""])
            conf = s.get("confidence", "EXTRACTED")
            cscore = s.get("confidence_score")
            if conf == "INFERRED" and cscore is not None:
                conf_tag = f"INFERRED {cscore:.2f}"
            else:
                conf_tag = conf
            sem_tag = " [semantically similar]" if relation == "semantically_similar_to" else ""
            lines += [
                f"- `{s['source']}` --{relation}--> `{s['target']}`  [{conf_tag}]{sem_tag}",
                f"  {_fmt_source(files[0])} → {_fmt_source(files[1])}" + (f"  _{note}_" if note else ""),
            ]
    else:
        lines.append("- None detected - all connections are within the same source files.")

    hyperedges = G.graph.get("hyperedges", [])
    if hyperedges:
        lines += ["", "## Hyperedges (group relationships)"]
        for h in hyperedges:
            node_labels = ", ".join(h.get("nodes", []))
            conf = h.get("confidence", "INFERRED")
            cscore = h.get("confidence_score")
            conf_tag = f"{conf} {cscore:.2f}" if cscore is not None else conf
            lines.append(f"- **{h.get('label', h.get('id', ''))}** — {node_labels} [{conf_tag}]")

    lines += ["", "## Communities"]
    from .analyze import _is_file_node as _ifn
    for cid, nodes in communities.items():
        label = community_labels.get(cid, f"Community {cid}")
        score = cohesion_scores.get(cid, 0.0)
        # Filter method/function stubs from display - they're structural noise
        real_nodes = [n for n in nodes if not _ifn(G, n)]
        display = [G.nodes[n].get("label", n) for n in real_nodes[:8]]
        suffix = f" (+{len(real_nodes)-8} more)" if len(real_nodes) > 8 else ""
        lines += [
            "",
            f"### Community {cid} - \"{label}\"",
            f"Cohesion: {score}",
            f"Nodes ({len(real_nodes)}): {', '.join(display)}{suffix}",
        ]

    ambiguous = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("confidence") == "AMBIGUOUS"]
    if ambiguous:
        lines += ["", "## Ambiguous Edges - Review These"]
        for u, v, d in ambiguous:
            ul = G.nodes[u].get("label", u)
            vl = G.nodes[v].get("label", v)
            lines += [
                f"- `{ul}` → `{vl}`  [AMBIGUOUS]",
                f"  {d.get('source_file', '')} · relation: {d.get('relation', 'unknown')}",
            ]

    # --- Gaps section ---
    from .analyze import _is_file_node, _is_concept_node

    isolated = [
        n for n in G.nodes()
        if G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n)
    ]
    thin_communities = {
        cid: nodes for cid, nodes in communities.items() if len(nodes) < 3
    }
    gap_count = len(isolated) + len(thin_communities)

    if gap_count > 0 or amb_pct > 20:
        lines += ["", "## Knowledge Gaps"]
        if isolated:
            isolated_labels = [G.nodes[n].get("label", n) for n in isolated[:5]]
            suffix = f" (+{len(isolated)-5} more)" if len(isolated) > 5 else ""
            lines.append(f"- **{len(isolated)} isolated node(s):** {', '.join(f'`{l}`' for l in isolated_labels)}{suffix}")
            lines.append("  These have ≤1 connection - possible missing edges or undocumented components.")
        if thin_communities:
            for cid, nodes in thin_communities.items():
                label = community_labels.get(cid, f"Community {cid}")
                node_labels = [G.nodes[n].get("label", n) for n in nodes]
                lines.append(f"- **Thin community `{label}`** ({len(nodes)} nodes): {', '.join(f'`{l}`' for l in node_labels)}")
                lines.append("  Too small to be a meaningful cluster - may be noise or needs more connections extracted.")
        if amb_pct > 20:
            lines.append(f"- **High ambiguity: {amb_pct}% of edges are AMBIGUOUS.** Review the Ambiguous Edges section above.")

    if suggested_questions:
        lines += ["", "## Suggested Questions"]
        no_signal = len(suggested_questions) == 1 and suggested_questions[0].get("type") == "no_signal"
        if no_signal:
            lines.append(f"_{suggested_questions[0]['why']}_")
        else:
            lines.append("_Questions this graph is uniquely positioned to answer:_")
            lines.append("")
            for q in suggested_questions:
                if q.get("question"):
                    lines.append(f"- **{q['question']}**")
                    lines.append(f"  _{q['why']}_")

    if usage_data:
        counters = usage_data.get("counters", {})
        if counters:
            hc = _compute_hot_cold(G, counters)
            lines += ["", "## Usage Patterns", ""]
            lines.append(f"Total edge traversals recorded: **{hc['total_queries']}**")
            lines.append(f"Never-traversed edges: **{hc['never_traversed']}**")
            lines.append("")
            if hc["hot"]:
                lines.append("### Hot Paths (top 10%)")
                lines.append("")
                lines.append("| Edge | Traversals |")
                lines.append("|------|------------|")
                for edge_key, count in hc["hot"]:
                    parts = edge_key.split(":", 1)
                    a_label = G.nodes[parts[0]].get("label", parts[0]) if parts[0] in G else parts[0]
                    b_label = G.nodes[parts[1]].get("label", parts[1]) if parts[1] in G else parts[1]
                    lines.append(f"| {_sanitize_md(a_label)} -> {_sanitize_md(b_label)} | {count} |")
                lines.append("")
            if hc["cold"]:
                lines.append("### Cold Zones (bottom 10%)")
                lines.append("")
                lines.append("| Edge | Traversals |")
                lines.append("|------|------------|")
                for edge_key, count in hc["cold"]:
                    parts = edge_key.split(":", 1)
                    a_label = G.nodes[parts[0]].get("label", parts[0]) if parts[0] in G else parts[0]
                    b_label = G.nodes[parts[1]].get("label", parts[1]) if parts[1] in G else parts[1]
                    lines.append(f"| {_sanitize_md(a_label)} -> {_sanitize_md(b_label)} | {count} |")
                lines.append("")

    # Phase 10 / D-04: Entity Dedup section (optional; only rendered when dedup ran)
    if dedup_report and dedup_report.get("merges"):
        summary = dedup_report.get("summary", {}) or {}
        merges = dedup_report["merges"]
        lines += [
            "",
            "## Entity Dedup",
            (
                f"- {summary.get('merges', len(merges))} entities merged · "
                f"{summary.get('total_nodes_before', '?')} nodes → "
                f"{summary.get('total_nodes_after', '?')} nodes"
            ),
            "",
        ]
        # Render up to first 10 merges; defense-in-depth sanitization on all labels
        for merge in merges[:10]:
            canon_label = _sanitize_md(sanitize_label(str(merge.get("canonical_label", ""))))
            elim_labels = ", ".join(
                _sanitize_md(sanitize_label(str(e.get("label", e.get("id", "")))))
                for e in merge.get("eliminated", [])
            )
            fuzzy = float(merge.get("fuzzy_score", 0.0) or 0.0)
            cos = float(merge.get("cosine_score", 0.0) or 0.0)
            lines.append(
                f"- `{canon_label}` ← {elim_labels}  "
                f"[fuzzy={fuzzy:.3f}, cos={cos:.3f}]"
            )
        if len(merges) > 10:
            lines.append(f"  (+{len(merges) - 10} more — see dedup_report.json)")

    return "\n".join(lines)


def _sanitize_md(text: str) -> str:
    """Strip characters that could inject markdown structure from untrusted LLM output."""
    # Remove backtick sequences and angle brackets that could break markdown embedding
    text = text.replace("`", "'").replace("<", "&lt;").replace(">", "&gt;")
    return text


def render_analysis(
    lens_results: list[dict],
    root: str,
    lenses_run: list[str],
) -> str:
    """Render GRAPH_ANALYSIS.md from per-lens tournament result dicts."""
    today = date.today().isoformat()

    lines = [
        f"# Graph Analysis - {root}  ({today})",
        "",
        "> Multi-perspective analysis using autoreason tournament protocol.",
        f"> Lenses run: {', '.join(lenses_run)}",
    ]

    # Overall Verdict section
    findings = [r for r in lens_results if r.get("verdict") == "Finding"]
    clean = [r for r in lens_results if r.get("verdict") == "Clean"]
    total = len(lens_results)

    lines += ["", "## Overall Verdict", ""]
    if not findings:
        lines.append("All lenses report clean — no actionable findings.")
    else:
        top_findings = [r.get("top_finding", "") for r in findings if r.get("top_finding", "")]
        key_str = "; ".join(top_findings) if top_findings else "see per-lens sections below"
        lines.append(
            f"{len(findings)} of {total} lenses found issues. Key findings: {_sanitize_md(key_str)}"
        )

    # Per-lens sections — every lens always appears (D-83)
    for r in lens_results:
        lens = r.get("lens", "unknown")
        verdict = r.get("verdict", "")
        confidence = r.get("confidence", 0.0)
        confidence_label = r.get("confidence_label", "")
        findings_text = _sanitize_md(r.get("findings_text", ""))
        voting_rationale = _sanitize_md(r.get("voting_rationale", ""))
        top_finding = _sanitize_md(r.get("top_finding", ""))
        incumbent_summary = _sanitize_md(r.get("incumbent_summary", ""))
        adversary_summary = _sanitize_md(r.get("adversary_summary", ""))
        synthesis_summary = _sanitize_md(r.get("synthesis_summary", ""))
        scores = r.get("scores", {"A": 0, "B": 0, "AB": 0})

        # Determine winner label for Tournament Rationale
        score_a = scores.get("A", 0)
        score_b = scores.get("B", 0)
        score_ab = scores.get("AB", 0)
        if score_a >= score_b and score_a >= score_ab:
            verdict_source = "Incumbent (A)"
        elif score_b >= score_a and score_b >= score_ab:
            verdict_source = "Adversary (B)"
        else:
            verdict_source = "Synthesis (AB)"

        lines += [
            "",
            "---",
            "",
            f"## {lens.title()}",
            "",
            f"**Verdict:** {verdict}",
            f"**Confidence:** {confidence_label} (score: {confidence:.2f})",
            "",
            "### Top Finding",
            top_finding if top_finding else "No issues found.",
            "",
            "### Full Analysis",
            findings_text,
            "",
            "### Tournament Rationale",
            f"- Incumbent (A): {incumbent_summary}",
            f"- Adversary (B): {adversary_summary}",
            f"- Synthesis (AB): {synthesis_summary}",
            f"- Judges voted: A={score_a}, B={score_b}, AB={score_ab}",
            f"- Winner: {verdict_source} — {voting_rationale}",
        ]

    # Cross-Lens Synthesis section
    lines += ["", "## Cross-Lens Synthesis", ""]

    # Convergences: multiple lenses agree
    lines.append("### Convergences")
    if lens_results and len(clean) == len(lens_results):
        lines.append("- All lenses agree: no issues detected.")
    elif len(clean) >= 3:
        lens_names = ", ".join(r.get("lens", "") for r in clean)
        lines.append(f"- {len(clean)} lenses agree: no issues ({lens_names})")
    else:
        lines.append("- No strong convergence detected across lenses.")

    # Tensions: opposing verdicts between lens pairs
    lines += ["", "### Tensions"]
    tension_pairs = []
    for i, r1 in enumerate(lens_results):
        for r2 in lens_results[i + 1:]:
            if r1.get("verdict") != r2.get("verdict"):
                tension_pairs.append((r1.get("lens", ""), r2.get("verdict", ""), r2.get("lens", ""), r1.get("verdict", "")))
    if tension_pairs:
        for lens_a, verdict_b, lens_b, verdict_a in tension_pairs:
            lines.append(
                f"- {lens_a.title()} ({verdict_a}) vs {lens_b.title()} ({verdict_b}): opposing verdicts"
            )
    else:
        lines.append("- No tensions detected — all lenses agree.")

    return "\n".join(lines)
