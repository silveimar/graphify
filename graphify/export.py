# write graph to HTML, JSON, SVG, GraphML, Obsidian vault, and Neo4j Cypher
from __future__ import annotations
import html as _html
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable
import networkx as nx
from networkx.readwrite import json_graph
from graphify.security import sanitize_label
from graphify.analyze import _node_community_map, _fmt_source_file
from graphify.profile import safe_filename, safe_frontmatter_value, safe_tag

COMMUNITY_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
]

MAX_NODES_FOR_VIZ = 5_000


def _write_repo_identity_sidecar(artifacts_dir: Path, resolved_repo_identity) -> None:
    """Write resolved repo identity as a generated artifact sidecar."""
    sidecar_path = artifacts_dir / "repo-identity.json"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = sidecar_path.with_suffix(".json.tmp")
    payload = {
        "identity": resolved_repo_identity.identity,
        "raw_value": resolved_repo_identity.raw_value,
        "source": resolved_repo_identity.source,
        "warnings": list(resolved_repo_identity.warnings),
    }
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2, sort_keys=True))
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, sidecar_path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _html_styles() -> str:
    return """<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f1a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; display: flex; height: 100vh; overflow: hidden; }
  #graph { flex: 1; }
  #sidebar { width: 280px; background: #1a1a2e; border-left: 1px solid #2a2a4e; display: flex; flex-direction: column; overflow: hidden; }
  #search-wrap { padding: 12px; border-bottom: 1px solid #2a2a4e; }
  #search { width: 100%; background: #0f0f1a; border: 1px solid #3a3a5e; color: #e0e0e0; padding: 7px 10px; border-radius: 6px; font-size: 13px; outline: none; }
  #search:focus { border-color: #4E79A7; }
  #search-results { max-height: 140px; overflow-y: auto; padding: 4px 12px; border-bottom: 1px solid #2a2a4e; display: none; }
  .search-item { padding: 4px 6px; cursor: pointer; border-radius: 4px; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .search-item:hover { background: #2a2a4e; }
  #info-panel { padding: 14px; border-bottom: 1px solid #2a2a4e; min-height: 140px; }
  #info-panel h3 { font-size: 13px; color: #aaa; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }
  #info-content { font-size: 13px; color: #ccc; line-height: 1.6; }
  #info-content .field { margin-bottom: 5px; }
  #info-content .field b { color: #e0e0e0; }
  #info-content .empty { color: #555; font-style: italic; }
  .neighbor-link { display: block; padding: 2px 6px; margin: 2px 0; border-radius: 3px; cursor: pointer; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-left: 3px solid #333; }
  .neighbor-link:hover { background: #2a2a4e; }
  #neighbors-list { max-height: 160px; overflow-y: auto; margin-top: 4px; }
  #legend-wrap { flex: 1; overflow-y: auto; padding: 12px; }
  #legend-wrap h3 { font-size: 13px; color: #aaa; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
  .legend-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer; border-radius: 4px; font-size: 12px; }
  .legend-item:hover { background: #2a2a4e; padding-left: 4px; }
  .legend-item.dimmed { opacity: 0.35; }
  .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .legend-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .legend-count { color: #666; font-size: 11px; }
  #stats { padding: 10px 14px; border-top: 1px solid #2a2a4e; font-size: 11px; color: #555; }
</style>"""


def _hyperedge_script(hyperedges_json: str) -> str:
    return f"""<script>
// Render hyperedges as shaded regions
const hyperedges = {hyperedges_json};
function drawHyperedges() {{
    const canvas = network.canvas.frame.canvas;
    const ctx = canvas.getContext('2d');
    hyperedges.forEach(h => {{
        const positions = h.nodes
            .map(nid => network.getPositions([nid])[nid])
            .filter(p => p !== undefined);
        if (positions.length < 2) return;
        // Draw convex hull as filled polygon
        ctx.save();
        ctx.globalAlpha = 0.12;
        ctx.fillStyle = '#6366f1';
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2;
        ctx.beginPath();
        const scale = network.getScale();
        const offset = network.getViewPosition();
        const toCanvas = (p) => ({{
            x: (p.x - offset.x) * scale + canvas.width / 2,
            y: (p.y - offset.y) * scale + canvas.height / 2
        }});
        const pts = positions.map(toCanvas);
        // Expand hull slightly
        const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
        const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length;
        const expanded = pts.map(p => ({{
            x: cx + (p.x - cx) * 1.15,
            y: cy + (p.y - cy) * 1.15
        }}));
        ctx.moveTo(expanded[0].x, expanded[0].y);
        expanded.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 0.4;
        ctx.stroke();
        // Label
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = '#4f46e5';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(h.label, cx, cy - 5);
        ctx.restore();
    }});
}}
network.on('afterDrawing', drawHyperedges);
</script>"""


def _html_script(nodes_json: str, edges_json: str, legend_json: str) -> str:
    return f"""<script>
const RAW_NODES = {nodes_json};
const RAW_EDGES = {edges_json};
const LEGEND = {legend_json};

// HTML-escape helper — prevents XSS when injecting graph data into innerHTML
function esc(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}}

// Build vis datasets
const nodesDS = new vis.DataSet(RAW_NODES.map(n => ({{
  id: n.id, label: n.label, color: n.color, size: n.size,
  font: n.font, title: n.title,
  _community: n.community, _community_name: n.community_name,
  _source_file: n.source_file, _file_type: n.file_type, _degree: n.degree,
}})));

const edgesDS = new vis.DataSet(RAW_EDGES.map((e, i) => ({{
  id: i, from: e.from, to: e.to,
  label: '',
  title: e.title,
  dashes: e.dashes,
  width: e.width,
  color: e.color,
  arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
}})));

const container = document.getElementById('graph');
const network = new vis.Network(container, {{ nodes: nodesDS, edges: edgesDS }}, {{
  physics: {{
    enabled: true,
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{
      gravitationalConstant: -60,
      centralGravity: 0.005,
      springLength: 120,
      springConstant: 0.08,
      damping: 0.4,
      avoidOverlap: 0.8,
    }},
    stabilization: {{ iterations: 200, fit: true }},
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 100,
    hideEdgesOnDrag: true,
    navigationButtons: false,
    keyboard: false,
  }},
  nodes: {{ shape: 'dot', borderWidth: 1.5 }},
  edges: {{ smooth: {{ type: 'continuous', roundness: 0.2 }}, selectionWidth: 3 }},
}});

network.once('stabilizationIterationsDone', () => {{
  network.setOptions({{ physics: {{ enabled: false }} }});
}});

function showInfo(nodeId) {{
  const n = nodesDS.get(nodeId);
  if (!n) return;
  const neighborIds = network.getConnectedNodes(nodeId);
  const neighborItems = neighborIds.map(nid => {{
    const nb = nodesDS.get(nid);
    const color = nb ? nb.color.background : '#555';
    return `<span class="neighbor-link" style="border-left-color:${{esc(color)}}" onclick="focusNode(${{JSON.stringify(nid)}})">${{esc(nb ? nb.label : nid)}}</span>`;
  }}).join('');
  document.getElementById('info-content').innerHTML = `
    <div class="field"><b>${{esc(n.label)}}</b></div>
    <div class="field">Type: ${{esc(n._file_type || 'unknown')}}</div>
    <div class="field">Community: ${{esc(n._community_name)}}</div>
    <div class="field">Source: ${{esc(n._source_file || '-')}}</div>
    <div class="field">Degree: ${{n._degree}}</div>
    ${{neighborIds.length ? `<div class="field" style="margin-top:8px;color:#aaa;font-size:11px">Neighbors (${{neighborIds.length}})</div><div id="neighbors-list">${{neighborItems}}</div>` : ''}}
  `;
}}

function focusNode(nodeId) {{
  network.focus(nodeId, {{ scale: 1.4, animation: true }});
  network.selectNodes([nodeId]);
  showInfo(nodeId);
}}

// Track hovered node — hover detection is more reliable than click params
let hoveredNodeId = null;
network.on('hoverNode', params => {{
  hoveredNodeId = params.node;
  container.style.cursor = 'pointer';
}});
network.on('blurNode', () => {{
  hoveredNodeId = null;
  container.style.cursor = 'default';
}});
container.addEventListener('click', () => {{
  if (hoveredNodeId !== null) {{
    showInfo(hoveredNodeId);
    network.selectNodes([hoveredNodeId]);
  }}
}});
network.on('click', params => {{
  if (params.nodes.length > 0) {{
    showInfo(params.nodes[0]);
  }} else if (hoveredNodeId === null) {{
    document.getElementById('info-content').innerHTML = '<span class="empty">Click a node to inspect it</span>';
  }}
}});

const searchInput = document.getElementById('search');
const searchResults = document.getElementById('search-results');
searchInput.addEventListener('input', () => {{
  const q = searchInput.value.toLowerCase().trim();
  searchResults.innerHTML = '';
  if (!q) {{ searchResults.style.display = 'none'; return; }}
  const matches = RAW_NODES.filter(n => n.label.toLowerCase().includes(q)).slice(0, 20);
  if (!matches.length) {{ searchResults.style.display = 'none'; return; }}
  searchResults.style.display = 'block';
  matches.forEach(n => {{
    const el = document.createElement('div');
    el.className = 'search-item';
    el.textContent = n.label;
    el.style.borderLeft = `3px solid ${{n.color.background}}`;
    el.style.paddingLeft = '8px';
    el.onclick = () => {{
      network.focus(n.id, {{ scale: 1.5, animation: true }});
      network.selectNodes([n.id]);
      showInfo(n.id);
      searchResults.style.display = 'none';
      searchInput.value = '';
    }};
    searchResults.appendChild(el);
  }});
}});
document.addEventListener('click', e => {{
  if (!searchResults.contains(e.target) && e.target !== searchInput)
    searchResults.style.display = 'none';
}});

const hiddenCommunities = new Set();
const legendEl = document.getElementById('legend');
LEGEND.forEach(c => {{
  const item = document.createElement('div');
  item.className = 'legend-item';
  item.innerHTML = `<div class="legend-dot" style="background:${{c.color}}"></div>
    <span class="legend-label">${{c.label}}</span>
    <span class="legend-count">${{c.count}}</span>`;
  item.onclick = () => {{
    if (hiddenCommunities.has(c.cid)) {{
      hiddenCommunities.delete(c.cid);
      item.classList.remove('dimmed');
    }} else {{
      hiddenCommunities.add(c.cid);
      item.classList.add('dimmed');
    }}
    const updates = RAW_NODES
      .filter(n => n.community === c.cid)
      .map(n => ({{ id: n.id, hidden: hiddenCommunities.has(c.cid) }}));
    nodesDS.update(updates);
  }};
  legendEl.appendChild(item);
}});
</script>"""


_CONFIDENCE_SCORE_DEFAULTS = {"EXTRACTED": 1.0, "INFERRED": 0.5, "AMBIGUOUS": 0.2}


def attach_hyperedges(G: nx.Graph, hyperedges: list) -> None:
    """Store hyperedges in the graph's metadata dict."""
    existing = G.graph.get("hyperedges", [])
    seen_ids = {h["id"] for h in existing}
    for h in hyperedges:
        if h.get("id") and h["id"] not in seen_ids:
            existing.append(h)
            seen_ids.add(h["id"])
    G.graph["hyperedges"] = existing


def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str) -> None:
    node_community = _node_community_map(communities)
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)
    for node in data["nodes"]:
        node["community"] = node_community.get(node["id"])
    for link in data["links"]:
        if "confidence_score" not in link:
            conf = link.get("confidence", "EXTRACTED")
            link["confidence_score"] = _CONFIDENCE_SCORE_DEFAULTS.get(conf, 1.0)
    data["hyperedges"] = getattr(G, "graph", {}).get("hyperedges", [])
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    # MANIFEST-02: runtime manifest alongside graph.json (same success path).
    try:
        from graphify.capability import write_runtime_manifest

        write_runtime_manifest(Path(output_path).parent)
    except Exception as exc:
        raise RuntimeError(
            "graphify-out/capability.json could not be written; install graphify with [mcp] extras "
            "(jsonschema, PyYAML) or see prior exception"
        ) from exc


def _cypher_escape(s: str) -> str:
    """Escape a string for safe embedding in a Cypher single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def to_cypher(G: nx.Graph, output_path: str) -> None:
    lines = ["// Neo4j Cypher import - generated by /graphify", ""]
    for node_id, data in G.nodes(data=True):
        label = _cypher_escape(data.get("label", node_id))
        node_id_esc = _cypher_escape(node_id)
        _ft = re.sub(r"[^A-Za-z0-9_]", "", data.get("file_type", "unknown").capitalize())
        ftype = (_ft if _ft and _ft[0].isalpha() else "Entity")
        lines.append(f"MERGE (n:{ftype} {{id: '{node_id_esc}', label: '{label}'}});")
    lines.append("")
    for u, v, data in G.edges(data=True):
        rel = re.sub(r"[^A-Za-z0-9_]", "_", data.get("relation", "RELATES_TO").upper())
        conf = _cypher_escape(data.get("confidence", "EXTRACTED"))
        u_esc = _cypher_escape(u)
        v_esc = _cypher_escape(v)
        lines.append(
            f"MATCH (a {{id: '{u_esc}'}}), (b {{id: '{v_esc}'}}) "
            f"MERGE (a)-[:{rel} {{confidence: '{conf}'}}]->(b);"
        )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def to_html(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
    community_labels: dict[int, str] | None = None,
) -> None:
    """Generate an interactive vis.js HTML visualization of the graph.

    Features: node size by degree, click-to-inspect panel, search box,
    community filter, physics clustering by community, confidence-styled edges.
    Raises ValueError if graph exceeds MAX_NODES_FOR_VIZ.
    """
    if G.number_of_nodes() > MAX_NODES_FOR_VIZ:
        raise ValueError(
            f"Graph has {G.number_of_nodes()} nodes - too large for HTML viz. "
            f"Use --no-viz or reduce input size."
        )

    node_community = _node_community_map(communities)
    degree = dict(G.degree())
    max_deg = max(degree.values(), default=1) or 1

    # Build nodes list for vis.js
    vis_nodes = []
    for node_id, data in G.nodes(data=True):
        cid = node_community.get(node_id, 0)
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        label = sanitize_label(data.get("label", node_id))
        deg = degree.get(node_id, 1)
        size = 10 + 30 * (deg / max_deg)
        # Only show label for high-degree nodes by default; others show on hover
        font_size = 12 if deg >= max_deg * 0.15 else 0
        vis_nodes.append({
            "id": node_id,
            "label": label,
            "color": {"background": color, "border": color, "highlight": {"background": "#ffffff", "border": color}},
            "size": round(size, 1),
            "font": {"size": font_size, "color": "#ffffff"},
            "title": _html.escape(label),
            "community": cid,
            "community_name": sanitize_label((community_labels or {}).get(cid, f"Community {cid}")),
            "source_file": sanitize_label(_fmt_source_file(data.get("source_file", ""))),
            "file_type": data.get("file_type", ""),
            "degree": deg,
        })

    # Build edges list
    vis_edges = []
    for u, v, data in G.edges(data=True):
        confidence = data.get("confidence", "EXTRACTED")
        relation = data.get("relation", "")
        vis_edges.append({
            "from": u,
            "to": v,
            "label": relation,
            "title": _html.escape(f"{relation} [{confidence}]"),
            "dashes": confidence != "EXTRACTED",
            "width": 2 if confidence == "EXTRACTED" else 1,
            "color": {"opacity": 0.7 if confidence == "EXTRACTED" else 0.35},
            "confidence": confidence,
        })

    # Build community legend data
    legend_data = []
    for cid in sorted((community_labels or {}).keys()):
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        lbl = _html.escape(sanitize_label((community_labels or {}).get(cid, f"Community {cid}")))
        n = len(communities.get(cid, []))
        legend_data.append({"cid": cid, "color": color, "label": lbl, "count": n})

    # Escape </script> sequences so embedded JSON cannot break out of the script tag
    def _js_safe(obj) -> str:
        return json.dumps(obj).replace("</", "<\\/")

    nodes_json = _js_safe(vis_nodes)
    edges_json = _js_safe(vis_edges)
    legend_json = _js_safe(legend_data)
    hyperedges_json = _js_safe(getattr(G, "graph", {}).get("hyperedges", []))
    title = _html.escape(sanitize_label(str(output_path)))
    stats = f"{G.number_of_nodes()} nodes &middot; {G.number_of_edges()} edges &middot; {len(communities)} communities"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>graphify - {title}</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
{_html_styles()}
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search nodes..." autocomplete="off">
    <div id="search-results"></div>
  </div>
  <div id="info-panel">
    <h3>Node Info</h3>
    <div id="info-content"><span class="empty">Click a node to inspect it</span></div>
  </div>
  <div id="legend-wrap">
    <h3>Communities</h3>
    <div id="legend"></div>
  </div>
  <div id="stats">{stats}</div>
</div>
{_html_script(nodes_json, edges_json, legend_json)}
{_hyperedge_script(hyperedges_json)}
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")


# Keep backward-compatible alias - skill.md calls generate_html
generate_html = to_html


# ---------------------------------------------------------------------------
# Phase 10 D-15: hydrate merged_from from dedup_report.json (--obsidian-dedup)
# ---------------------------------------------------------------------------

def _hydrate_merged_from(G: nx.Graph, output_dir: Path) -> None:
    """Populate G.nodes[canonical_id]['merged_from'] from dedup_report.json.

    Called by to_obsidian when obsidian_dedup=True. Mutates G in place.

    Search order for dedup_report.json:
    1. output_dir.parent (typical graphify-out/obsidian layout — preferred)
    2. graphify-out/ relative to cwd (fallback for unusual layouts)

    Silently returns when the report is missing. Never raises.
    """
    # Note: an earlier implementation also searched `output_dir / ".." /` but
    # that resolves to the same path as candidate 1 after `.resolve()` and was
    # removed as redundant.
    candidates = [
        output_dir.parent / "dedup_report.json",
        Path("graphify-out") / "dedup_report.json",
    ]
    report_path = None
    for c in candidates:
        try:
            if c.resolve().exists():
                report_path = c.resolve()
                break
        except OSError:
            continue
    if report_path is None:
        print(
            "[graphify] warning: --obsidian-dedup set but no dedup_report.json found",
            file=sys.stderr,
        )
        return
    try:
        data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[graphify] warning: could not read {report_path}: {e}",
              file=sys.stderr)
        return
    # Build {canonical_id: [eliminated_ids]} from merges[]
    merges = data.get("merges", []) if isinstance(data, dict) else []
    for merge in merges:
        canonical_id = merge.get("canonical_id")
        if not canonical_id or canonical_id not in G:
            continue
        eliminated_ids = [
            e.get("id") for e in merge.get("eliminated", [])
            if isinstance(e, dict) and isinstance(e.get("id"), str)
        ]
        # Merge into existing merged_from (if dedup already ran into G.nodes)
        existing = G.nodes[canonical_id].get("merged_from") or []
        combined = sorted(set(existing) | set(e for e in eliminated_ids if e))
        if combined:
            G.nodes[canonical_id]["merged_from"] = combined


def to_obsidian(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str,
    *,
    profile: dict | None = None,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    repo_identity: str | None = None,
    concept_namer: Callable | None = None,
    dry_run: bool = False,
    force: bool = False,
    obsidian_dedup: bool = False,
) -> "MergeResult | MergePlan":
    """Export graph as an Obsidian vault using the profile-driven pipeline.

    Runs: load_profile → classify → render_all → compute_merge_plan → apply_merge_plan.
    When `profile` is None, discovers `.graphify/profile.yaml` inside `output_dir`
    or falls back to `_DEFAULT_PROFILE` (Ideaverse ACE-shaped Atlas layout).
    When `dry_run=True`, returns a MergePlan without writing any files.
    Otherwise returns a MergeResult recording per-path write outcomes.

    `community_labels` feeds per-community display names into the classification
    pipeline via profile-independent merge into classify()'s per_community ctx.
    `cohesion` is passed through to classify() for per-community cohesion scores.
    `force` bypasses user-modified detection (D-10): user-modified notes are
    updated/replaced as if unmodified. User sentinel blocks (D-08) still preserved.
    """
    # Function-local imports so `graphify install` (which touches export.py through
    # __init__.py's lazy map) doesn't force heavy deps at CLI entry time.
    from graphify.profile import load_profile
    from graphify.mapping import classify
    from graphify.templates import render_note, render_moc
    from graphify.merge import (
        compute_merge_plan,
        apply_merge_plan,
        RenderedNote,
        split_rendered_note,
        _load_manifest,
    )

    out = Path(output_dir)
    # Upfront guard: fail loudly with an actionable message when output_dir
    # collides with a non-directory (regular file, symlink, device, etc.).
    # Without this, `out.mkdir(exist_ok=True)` below raises FileExistsError
    # with a confusing "File exists" message, and downstream render_note calls
    # can raise FileNotFoundError from load_templates(vault_dir=out).
    if out.exists() and not out.is_dir():
        raise ValueError(
            f"to_obsidian: output_dir {out} exists but is not a directory"
        )
    out.mkdir(parents=True, exist_ok=True)

    # Phase 10 D-15: hydrate merged_from from dedup_report.json when flag set.
    # This mutates G.nodes in place before rendering so render_note can emit aliases:.
    if obsidian_dedup:
        _hydrate_merged_from(G, out)

    # Manifest lives in the parent of the vault dir (typically graphify-out/).
    # vault-manifest.json is a graphify sidecar alongside graph.json.
    # _load_manifest gracefully returns {} when the file is absent (first run).
    _vault_dir = out.resolve()
    manifest_path = _vault_dir.parent / "vault-manifest.json"
    manifest = _load_manifest(manifest_path)

    # D-74: always run the new pipeline. No `if profile is None` branching.
    if profile is None:
        profile = load_profile(out)
    artifacts_dir = out.resolve().parent
    from graphify.naming import (
        build_code_filename_stems,
        resolve_concept_names,
        resolve_repo_identity,
    )
    resolved_repo_identity = resolve_repo_identity(
        Path.cwd(),
        cli_identity=repo_identity,
        profile=profile,
    )
    if not dry_run:
        _write_repo_identity_sidecar(artifacts_dir, resolved_repo_identity)
    concept_names = resolve_concept_names(
        G,
        communities,
        profile,
        artifacts_dir,
        llm_namer=concept_namer,
        dry_run=dry_run,
    )
    resolved_labels = {
        cid: concept.title
        for cid, concept in concept_names.items()
    }

    mapping_result = classify(G, communities, profile, cohesion=cohesion)
    per_node = mapping_result.get("per_node", {}) or {}
    per_community = mapping_result.get("per_community", {}) or {}
    skipped = mapping_result.get("skipped_node_ids", set()) or set()

    # Explicit caller labels win, then Phase 33 concept names, then mapping's
    # topology-derived labels. render_moc applies final sink sanitization.
    merged_labels = dict(resolved_labels)
    if community_labels:
        merged_labels.update(community_labels)
    original_labels = {
        cid: (
            ctx.get("community_name")
            or ctx.get("parent_moc_label")
            or f"Community {cid}"
        )
        for cid, ctx in per_community.items()
    }
    for cid, label in merged_labels.items():
        if cid in per_community:
            ctx = dict(per_community[cid])
            ctx["community_name"] = label
            ctx["community_tag"] = safe_tag(label)
            per_community[cid] = ctx
    final_labels = {
        cid: (
            ctx.get("community_name")
            or ctx.get("parent_moc_label")
            or f"Community {cid}"
        )
        for cid, ctx in per_community.items()
    }
    original_to_final_label = {
        str(original): str(final_labels[cid])
        for cid, original in original_labels.items()
        if cid in final_labels
    }
    node_to_community = _node_community_map(communities)
    for node_id, ctx in list(per_node.items()):
        if not isinstance(ctx, dict):
            continue
        parent_label = None
        cid = node_to_community.get(node_id)
        if cid in final_labels:
            parent_label = str(final_labels[cid])
        else:
            current_parent = ctx.get("parent_moc_label")
            if current_parent:
                parent_label = original_to_final_label.get(str(current_parent))
        if not parent_label:
            continue
        updated_ctx = dict(ctx)
        updated_ctx["parent_moc_label"] = parent_label
        updated_ctx["community_name"] = parent_label
        updated_ctx["community_tag"] = safe_tag(parent_label)
        per_node[node_id] = updated_ctx

    code_candidates: list[dict] = []
    for node_id, ctx in per_node.items():
        if ctx.get("note_type") != "code" or node_id not in G:
            continue
        node = G.nodes[node_id]
        code_candidates.append(
            {
                "node_id": node_id,
                "label": node.get("label", node_id),
                "source_file": node.get("source_file", ""),
            }
        )
    code_filename_stems = build_code_filename_stems(
        code_candidates,
        resolved_repo_identity.identity,
    )
    for node_id, stem_info in code_filename_stems.items():
        if node_id not in per_node:
            continue
        ctx = dict(per_node[node_id])
        ctx.update(stem_info)
        ctx["repo_identity"] = resolved_repo_identity.identity
        per_node[node_id] = ctx
    for cid, ctx in list(per_community.items()):
        enriched_members: list[dict] = []
        changed = False
        for member in ctx.get("code_members", []) or []:
            if not isinstance(member, dict):
                continue
            enriched = dict(member)
            stem_info = code_filename_stems.get(str(member.get("id") or ""))
            if stem_info:
                enriched.update(stem_info)
                changed = True
            enriched_members.append(enriched)
        if not changed:
            continue
        updated_ctx = dict(ctx)
        updated_ctx["code_members"] = enriched_members
        updated_ctx["code_member_labels"] = [
            member.get("filename_stem") or member.get("label")
            for member in enriched_members
            if member.get("filename_stem") or member.get("label")
        ]
        per_community[cid] = updated_ctx

    rendered_notes: dict[str, RenderedNote] = {}

    # ---- Per-node notes (thing / statement / person / source) ----
    for node_id, ctx in per_node.items():
        if node_id in skipped:
            continue
        note_type = ctx.get("note_type", "statement")
        if note_type in ("moc", "community"):
            # MOC-shaped classification belongs in per_community, not per_node —
            # defensive skip to avoid double-rendering.
            continue
        try:
            filename, rendered_text = render_note(
                node_id, G, profile, note_type, ctx, vault_dir=out,
            )
        except (ValueError, FileNotFoundError) as exc:
            # render_note raises ValueError on unknown note_type or missing
            # node, and FileNotFoundError from load_templates() if a user
            # template file vanished mid-run. Broader OSError (permission
            # denied, disk full, etc.) still propagates — "validate, report,
            # don't crash" stops at truly unrecoverable errors.
            print(
                f"[graphify] to_obsidian: skipping node {node_id!r} "
                f"({note_type}): {exc}",
                file=sys.stderr,
            )
            continue
        folder = ctx.get("folder") or profile.get("folder_mapping", {}).get("default", "Atlas/Dots/")
        target_path = out / folder / filename
        # Plan 01 public helper — stable contract for frontmatter splitting.
        # No private merge.py internal helpers imported across the module boundary.
        fm_fields, body = split_rendered_note(rendered_text)
        rendered_notes[node_id] = RenderedNote(
            node_id=node_id,
            target_path=target_path,
            frontmatter_fields=fm_fields,
            body=body,
        )

    # ---- Per-community MOC notes ----
    for cid, ctx in per_community.items():
        note_type = ctx.get("note_type", "moc")
        if note_type == "community":
            print(
                "[graphify] warning: note_type 'community' is deprecated; "
                "rendering as MOC-only output",
                file=sys.stderr,
            )
            note_type = "moc"
        if note_type != "moc":
            print(
                f"[graphify] to_obsidian: skipping community {cid} "
                f"({note_type}): unsupported community note type",
                file=sys.stderr,
            )
            continue
        try:
            filename, rendered_text = render_moc(
                cid, G, communities, profile, ctx, vault_dir=out,
            )
        except (ValueError, FileNotFoundError) as exc:
            # Same diagnostic discipline as the per-node loop above: surface
            # silently-skipped MOC/overview renders so CI logs catch regressions.
            # Mirrors the per-node except clause — ValueError from render_moc
            # (unknown shape, missing community) plus FileNotFoundError from
            # load_templates() if a template file vanished mid-run.
            print(
                f"[graphify] to_obsidian: skipping community {cid} "
                f"({note_type}): {exc}",
                file=sys.stderr,
            )
            continue
        folder = ctx.get("folder") or profile.get("folder_mapping", {}).get("moc", "Atlas/Maps/")
        target_path = out / folder / filename
        fm_fields, body = split_rendered_note(rendered_text)
        synthetic_id = f"_moc_{cid}"
        rendered_notes[synthetic_id] = RenderedNote(
            node_id=synthetic_id,
            target_path=target_path,
            frontmatter_fields=fm_fields,
            body=body,
        )

    plan = compute_merge_plan(
        out, rendered_notes, profile,
        skipped_node_ids=skipped,
        manifest=manifest,
        force=force,
    )
    if dry_run:
        return plan
    return apply_merge_plan(
        plan, out, rendered_notes, profile,
        manifest_path=manifest_path,
        old_manifest=manifest,
    )


def to_canvas(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
    community_labels: dict[int, str] | None = None,
    node_filenames: dict[str, str] | None = None,
) -> None:
    """Export graph as an Obsidian Canvas file - communities as groups, nodes as cards.

    Generates a structured layout: communities arranged in a grid, nodes within
    each community arranged in rows. Edges shown between connected nodes.
    Opens in Obsidian as an infinite canvas with community groupings visible.
    """
    # Obsidian canvas color codes (cycle through for communities)
    CANVAS_COLORS = ["1", "2", "3", "4", "5", "6"]  # red, orange, yellow, green, cyan, purple

    def safe_name(label: str) -> str:
        cleaned = re.sub(r'[\\/*?:"<>|#^[\]]', "", label.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")).strip()
        cleaned = re.sub(r"\.(md|mdx|markdown)$", "", cleaned, flags=re.IGNORECASE)
        return cleaned or "unnamed"

    # Build node_filenames if not provided (same dedup logic as to_obsidian)
    # FIX-02: Sort nodes for deterministic dedup across re-runs.
    if node_filenames is None:
        node_filenames = {}
        seen_names: dict[str, int] = {}
        for node_id, data in sorted(
            G.nodes(data=True),
            key=lambda nd: (_fmt_source_file(nd[1].get("source_file", "")), nd[1].get("label", nd[0]))
        ):
            base = safe_filename(data.get("label", node_id))
            if base in seen_names:
                seen_names[base] += 1
                node_filenames[node_id] = f"{base}_{seen_names[base]}"
            else:
                seen_names[base] = 0
                node_filenames[node_id] = base

    num_communities = len(communities)
    cols = math.ceil(math.sqrt(num_communities)) if num_communities > 0 else 1
    rows = math.ceil(num_communities / cols) if num_communities > 0 else 1

    canvas_nodes: list[dict] = []
    canvas_edges: list[dict] = []

    # Lay out communities in a grid
    gap = 80
    group_x_offsets: list[int] = []
    group_y_offsets: list[int] = []

    # Precompute group sizes so we can calculate offsets
    sorted_cids = sorted(communities.keys())
    group_sizes: dict[int, tuple[int, int]] = {}
    for cid in sorted_cids:
        members = communities[cid]
        n = len(members)
        w = max(600, 220 * math.ceil(math.sqrt(n)) if n > 0 else 600)
        h = max(400, 100 * math.ceil(n / 3) + 120 if n > 0 else 400)
        group_sizes[cid] = (w, h)

    # Compute cumulative row heights and col widths for grid placement
    # Each grid cell uses the max width/height in its col/row
    col_widths: list[int] = []
    row_heights: list[int] = []
    for col_idx in range(cols):
        max_w = 0
        for row_idx in range(rows):
            linear = row_idx * cols + col_idx
            if linear < len(sorted_cids):
                cid = sorted_cids[linear]
                w, _ = group_sizes[cid]
                max_w = max(max_w, w)
        col_widths.append(max_w)

    for row_idx in range(rows):
        max_h = 0
        for col_idx in range(cols):
            linear = row_idx * cols + col_idx
            if linear < len(sorted_cids):
                cid = sorted_cids[linear]
                _, h = group_sizes[cid]
                max_h = max(max_h, h)
        row_heights.append(max_h)

    # Map from cid → (group_x, group_y, group_w, group_h)
    group_layout: dict[int, tuple[int, int, int, int]] = {}
    for idx, cid in enumerate(sorted_cids):
        col_idx = idx % cols
        row_idx = idx // cols
        gx = sum(col_widths[:col_idx]) + col_idx * gap
        gy = sum(row_heights[:row_idx]) + row_idx * gap
        gw, gh = group_sizes[cid]
        group_layout[cid] = (gx, gy, gw, gh)

    # Build set of all node_ids in canvas for edge filtering
    all_canvas_nodes: set[str] = set()
    for members in communities.values():
        all_canvas_nodes.update(members)

    # Generate group and node canvas entries
    for idx, cid in enumerate(sorted_cids):
        members = communities[cid]
        community_name = (
            community_labels.get(cid, f"Community {cid}")
            if community_labels and cid is not None
            else f"Community {cid}"
        )
        gx, gy, gw, gh = group_layout[cid]
        canvas_color = CANVAS_COLORS[idx % len(CANVAS_COLORS)]

        # Group node
        canvas_nodes.append({
            "id": f"g{cid}",
            "type": "group",
            "label": community_name,
            "x": gx,
            "y": gy,
            "width": gw,
            "height": gh,
            "color": canvas_color,
        })

        # Node cards inside the group - rows of 3
        sorted_members = sorted(members, key=lambda n: G.nodes[n].get("label", n))
        for m_idx, node_id in enumerate(sorted_members):
            col = m_idx % 3
            row = m_idx // 3
            nx_x = gx + 20 + col * (180 + 20)
            nx_y = gy + 80 + row * (60 + 20)
            fname = node_filenames.get(node_id, safe_filename(G.nodes[node_id].get("label", node_id)))
            canvas_nodes.append({
                "id": f"n_{node_id}",
                "type": "file",
                "file": f"{fname}.md",
                "x": nx_x,
                "y": nx_y,
                "width": 180,
                "height": 60,
            })

    # Generate edges - only between nodes both in canvas, cap at 200 highest-weight
    all_edges_weighted: list[tuple[float, str, str, str]] = []
    for u, v, edata in G.edges(data=True):
        if u in all_canvas_nodes and v in all_canvas_nodes:
            weight = edata.get("weight", 1.0)
            relation = edata.get("relation", "")
            conf = edata.get("confidence", "EXTRACTED")
            label = f"{relation} [{conf}]" if relation else f"[{conf}]"
            all_edges_weighted.append((weight, u, v, label))

    all_edges_weighted.sort(key=lambda x: -x[0])
    for weight, u, v, label in all_edges_weighted[:200]:
        canvas_edges.append({
            "id": f"e_{u}_{v}",
            "fromNode": f"n_{u}",
            "toNode": f"n_{v}",
            "label": label,
        })

    canvas_data = {"nodes": canvas_nodes, "edges": canvas_edges}
    Path(output_path).write_text(json.dumps(canvas_data, indent=2), encoding="utf-8")


def push_to_neo4j(
    G: nx.Graph,
    uri: str,
    user: str,
    password: str,
    communities: dict[int, list[str]] | None = None,
) -> dict[str, int]:
    """Push graph directly to a running Neo4j instance via the Python driver.

    Requires: pip install neo4j

    Uses MERGE so re-running is safe - nodes and edges are upserted, not duplicated.
    Returns a dict with counts of nodes and edges pushed.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError as e:
        raise ImportError(
            "neo4j driver not installed. Run: pip install neo4j"
        ) from e

    node_community = _node_community_map(communities) if communities else {}

    def _safe_rel(relation: str) -> str:
        return re.sub(r"[^A-Z0-9_]", "_", relation.upper().replace(" ", "_").replace("-", "_")) or "RELATED_TO"

    def _safe_label(label: str) -> str:
        """Sanitize a Neo4j node label to prevent Cypher injection."""
        sanitized = re.sub(r"[^A-Za-z0-9_]", "", label)
        return sanitized if sanitized else "Entity"

    driver = GraphDatabase.driver(uri, auth=(user, password))
    nodes_pushed = 0
    edges_pushed = 0

    with driver.session() as session:
        for node_id, data in G.nodes(data=True):
            props = {k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))}
            props["id"] = node_id
            cid = node_community.get(node_id)
            if cid is not None:
                props["community"] = cid
            ftype = _safe_label(data.get("file_type", "Entity").capitalize())
            session.run(
                f"MERGE (n:{ftype} {{id: $id}}) SET n += $props",
                id=node_id,
                props=props,
            )
            nodes_pushed += 1

        for u, v, data in G.edges(data=True):
            rel = _safe_rel(data.get("relation", "RELATED_TO"))
            props = {k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))}
            session.run(
                f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
                f"MERGE (a)-[r:{rel}]->(b) SET r += $props",
                src=u,
                tgt=v,
                props=props,
            )
            edges_pushed += 1

    driver.close()
    return {"nodes": nodes_pushed, "edges": edges_pushed}


def to_graphml(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
) -> None:
    """Export graph as GraphML - opens in Gephi, yEd, and any GraphML-compatible tool.

    Community IDs are written as a node attribute so Gephi can colour by community.
    Edge confidence (EXTRACTED/INFERRED/AMBIGUOUS) is preserved as an edge attribute.
    """
    H = G.copy()
    node_community = _node_community_map(communities)
    for node_id in H.nodes():
        H.nodes[node_id]["community"] = node_community.get(node_id, -1)
    nx.write_graphml(H, output_path)


def to_svg(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
    community_labels: dict[int, str] | None = None,
    figsize: tuple[int, int] = (20, 14),
) -> None:
    """Export graph as an SVG file using matplotlib + spring layout.

    Lightweight and embeddable - works in Obsidian notes, Notion, GitHub READMEs,
    and any markdown renderer. No JavaScript required.

    Node size scales with degree. Community colors match the HTML output.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError as e:
        raise ImportError("matplotlib not installed. Run: pip install matplotlib") from e

    node_community = _node_community_map(communities)

    fig, ax = plt.subplots(figsize=figsize, facecolor="#1a1a2e")
    ax.set_facecolor("#1a1a2e")
    ax.axis("off")

    pos = nx.spring_layout(G, seed=42, k=2.0 / (G.number_of_nodes() ** 0.5 + 1))

    degree = dict(G.degree())
    max_deg = max(degree.values(), default=1) or 1

    node_colors = [COMMUNITY_COLORS[node_community.get(n, 0) % len(COMMUNITY_COLORS)] for n in G.nodes()]
    node_sizes = [300 + 1200 * (degree.get(n, 1) / max_deg) for n in G.nodes()]

    # Draw edges - dashed for non-EXTRACTED
    for u, v, data in G.edges(data=True):
        conf = data.get("confidence", "EXTRACTED")
        style = "solid" if conf == "EXTRACTED" else "dashed"
        alpha = 0.6 if conf == "EXTRACTED" else 0.3
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ax.plot([x0, x1], [y0, y1], color="#aaaaaa", linewidth=0.8,
                linestyle=style, alpha=alpha, zorder=1)

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=node_sizes, alpha=0.9)
    nx.draw_networkx_labels(G, pos, ax=ax,
                            labels={n: G.nodes[n].get("label", n) for n in G.nodes()},
                            font_size=7, font_color="white")

    # Legend
    if community_labels:
        patches = [
            mpatches.Patch(
                color=COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)],
                label=f"{label} ({len(communities.get(cid, []))})",
            )
            for cid, label in sorted(community_labels.items())
        ]
        ax.legend(handles=patches, loc="upper left", framealpha=0.7,
                  facecolor="#2a2a4e", labelcolor="white", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, format="svg", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
