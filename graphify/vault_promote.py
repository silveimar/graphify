"""Vault promotion pipeline: graph loading, 7-folder classification, and per-note rendering.

This module is a pure in-memory pipeline — it produces classification records and
rendered markdown strings but performs NO I/O to the vault or to graphify-out/.
Writes are handled by Plan 03 (vault_write.py).

Dispatch priority (first-match wins; a node claimed by an earlier bucket is NOT
re-processed by later buckets — except Questions which are additive):

    1. Things    — god_nodes() filtered to file_type != "code"; threshold gated
    2. Questions — knowledge_gaps(); ALWAYS promoted, threshold bypassed (D-09)
    3. Maps      — one MOC record per community_id (not node-backed)
    4. People    — label matches ^[A-Z][a-z]+ [A-Z][a-z]+$; threshold gated
    5. Quotes    — file_type=="document" AND label has quote marks; threshold gated
    6. Statements— any adjacent edge has relation="defines"; threshold gated
    7. Sources   — one record per unique source_file path (not node-backed)

Maps and Sources are not node-backed (they don't consume from `claimed`).
Questions are additive: a node in Things can ALSO appear in Questions.
"""
from __future__ import annotations

import datetime
import importlib.resources as ilr
import json
import re
import string
from copy import deepcopy
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from graphify.analyze import god_nodes, knowledge_gaps, _iter_sources
from graphify.profile import (
    _DEFAULT_PROFILE,
    _deep_merge,
    _dump_frontmatter,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
)


# ---------------------------------------------------------------------------
# Extension → tech-tag map (RESEARCH.md Open Question 3 / D-07-like)
# ---------------------------------------------------------------------------

_TECH_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".sql": "sql",
    ".graphql": "graphql",
    ".kt": "kotlin",
    ".kts": "kotlin",
}

# Folder type → builtin template filename stem mapping
_FOLDER_TO_TEMPLATE: dict[str, str] = {
    "Things": "thing",
    "Questions": "question",
    "Maps": "moc",
    "Sources": "source",
    "People": "person",
    "Quotes": "quote",
    "Statements": "statement",
}

# All placeholder keys expected by every builtin template
_ALL_PLACEHOLDER_KEYS: tuple[str, ...] = (
    "frontmatter",
    "label",
    "wayfinder_callout",
    "body",
    "connections_callout",
    "metadata_callout",
    "members_section",
    "sub_communities_callout",
    "dataview_block",
)


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_graph_and_communities(graph_path: Path) -> tuple[nx.Graph, dict[int, list[str]]]:
    """Load a graphify-out/graph.json and reconstruct in-memory G + communities dict.

    Uses the json_graph.node_link_graph round-trip with a TypeError fallback for
    NetworkX version compatibility (RESEARCH.md Pattern 1).

    Returns (G, communities) where communities maps community_id -> list[node_id].
    Nodes with a None or non-integer community attribute are skipped.
    """
    gp = Path(graph_path).resolve()
    raw = json.loads(gp.read_text(encoding="utf-8"))
    try:
        G = json_graph.node_link_graph(raw, edges="links")
    except TypeError:
        G = json_graph.node_link_graph(raw)

    communities: dict[int, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        cid = data.get("community")
        if cid is None:
            continue
        try:
            cid_int = int(cid)
        except (TypeError, ValueError):
            continue
        communities.setdefault(cid_int, []).append(node_id)

    return G, communities


# ---------------------------------------------------------------------------
# Heuristic helpers for People / Quotes / Statements
# ---------------------------------------------------------------------------

def _is_person(label: str) -> bool:
    """Return True if label looks like a human name (First Last pattern)."""
    return re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+$", label) is not None


def _has_quote_marks(label: str) -> bool:
    """Return True if label contains any common quotation mark character."""
    return any(c in label for c in ('"', '“', '”', '«', '»'))


def _has_defines_edge(G: nx.Graph, node_id: str) -> bool:
    """Return True if the node has any adjacent edge with relation='defines'."""
    return any(
        d.get("relation") == "defines"
        for _, _, d in G.edges(node_id, data=True)
    )


# ---------------------------------------------------------------------------
# 7-folder classifier
# ---------------------------------------------------------------------------

def classify_nodes(
    G: nx.Graph,
    communities: dict[int, list[str]],
    profile: dict,
    threshold: int,
) -> dict[str, list[dict]]:
    """Classify graph nodes into 7 Ideaverse folders.

    Returns a dict with keys:
        things, questions, maps, sources, people, quotes, statements

    Each value is a list of classification records. Node-backed records include:
        node_id, label, folder, score

    Map records include: community_id, label, folder, score, members
    Source records include: source_path, label, folder, score

    Questions are additive: a node already claimed by another bucket can still
    appear in Questions if knowledge_gaps() returns it. (D-09)

    Maps and Sources are computed from community/source_file structure, not from
    node identity — they do not interact with the `claimed` set.
    """
    result: dict[str, list[dict]] = {
        "things": [],
        "questions": [],
        "maps": [],
        "sources": [],
        "people": [],
        "quotes": [],
        "statements": [],
    }

    # Set of node_ids already assigned to a bucket (Things/People/Quotes/Statements only)
    claimed: set[str] = set()

    # ------------------------------------------------------------------
    # 1. Things — god_nodes with file_type != "code", degree >= threshold
    # ------------------------------------------------------------------
    god_list = god_nodes(G)
    for gn in god_list:
        nid = gn["id"]
        node_data = G.nodes[nid]
        file_type = node_data.get("file_type", "")
        if file_type == "code":
            continue  # D-10: never promote code-typed nodes as Things
        degree = G.degree(nid)
        if degree < threshold:
            continue
        claimed.add(nid)
        result["things"].append({
            "node_id": nid,
            "label": gn["label"],
            "folder": "Atlas/Dots/Things/",
            "score": degree,
        })

    # ------------------------------------------------------------------
    # 2. Questions — knowledge_gaps(), ALWAYS promoted (threshold bypassed)
    # ------------------------------------------------------------------
    gaps = knowledge_gaps(G, communities)
    for gap in gaps:
        nid = gap["id"]
        result["questions"].append({
            "node_id": nid,
            "label": gap["label"],
            "folder": "Atlas/",
            "score": G.degree(nid),
            "reason": gap.get("reason", ""),
        })

    # ------------------------------------------------------------------
    # 3. Maps — one MOC per community_id
    # ------------------------------------------------------------------
    for cid, member_ids in communities.items():
        result["maps"].append({
            "community_id": cid,
            "label": f"Community {cid}",
            "folder": "Atlas/Maps/",
            "score": 0,
            "members": list(member_ids),
        })

    # ------------------------------------------------------------------
    # 4. People — label matches First Last AND degree >= threshold AND unclaimed
    # ------------------------------------------------------------------
    for node_id, data in G.nodes(data=True):
        if node_id in claimed:
            continue
        label = data.get("label", "")
        degree = G.degree(node_id)
        if _is_person(label) and degree >= threshold:
            claimed.add(node_id)
            result["people"].append({
                "node_id": node_id,
                "label": label,
                "folder": "Atlas/Dots/People/",
                "score": degree,
            })

    # ------------------------------------------------------------------
    # 5. Quotes — file_type=="document" AND quote marks AND degree >= threshold AND unclaimed
    # ------------------------------------------------------------------
    for node_id, data in G.nodes(data=True):
        if node_id in claimed:
            continue
        label = data.get("label", "")
        file_type = data.get("file_type", "")
        degree = G.degree(node_id)
        if file_type == "document" and _has_quote_marks(label) and degree >= threshold:
            claimed.add(node_id)
            result["quotes"].append({
                "node_id": node_id,
                "label": label,
                "folder": "Atlas/Quotes/",
                "score": degree,
            })

    # ------------------------------------------------------------------
    # 6. Statements — outgoing "defines" edge AND degree >= threshold AND unclaimed
    # ------------------------------------------------------------------
    for node_id, data in G.nodes(data=True):
        if node_id in claimed:
            continue
        degree = G.degree(node_id)
        if _has_defines_edge(G, node_id) and degree >= threshold:
            claimed.add(node_id)
            result["statements"].append({
                "node_id": node_id,
                "label": data.get("label", node_id),
                "folder": "Atlas/Dots/Statements/",
                "score": degree,
            })

    # ------------------------------------------------------------------
    # 7. Sources — one record per unique source_file path (deduplicated)
    # ------------------------------------------------------------------
    seen_sources: set[str] = set()
    for node_id, data in G.nodes(data=True):
        for src_path in _iter_sources(data.get("source_file")):
            if src_path and src_path not in seen_sources:
                seen_sources.add(src_path)
                stem = Path(src_path).stem
                result["sources"].append({
                    "source_path": src_path,
                    "label": stem,
                    "folder": "Atlas/Sources/",
                    "score": 0,
                })

    return result


# ---------------------------------------------------------------------------
# Layer-3 tech-tag detection
# ---------------------------------------------------------------------------

def _detect_tech_tags(G: nx.Graph) -> dict[str, list[str]]:
    """Scan all node source_file values and return detected tech tags.

    Returns {"tech": [sorted_unique_tags]} where tags are values from _TECH_EXT_MAP.
    Unknown extensions produce nothing. Output tags are passed through safe_tag.
    """
    detected: set[str] = set()
    for _, data in G.nodes(data=True):
        for src_path in _iter_sources(data.get("source_file")):
            ext = Path(src_path).suffix.lower()
            if ext in _TECH_EXT_MAP:
                detected.add(safe_tag(_TECH_EXT_MAP[ext]))
    return {"tech": sorted(detected)}


# ---------------------------------------------------------------------------
# Tag taxonomy resolution (3-layer merge)
# ---------------------------------------------------------------------------

def resolve_taxonomy(G: nx.Graph, user_profile: dict) -> dict:
    """Resolve the 3-layer tag taxonomy merge.

    Layer 1: _DEFAULT_PROFILE["tag_taxonomy"] (built-in baseline)
    Layer 2: user_profile["tag_taxonomy"] (vault profile.yaml override)
    Layer 3: _detect_tech_tags(G) (auto-detected from graph extensions)

    Returns the merged taxonomy dict (namespace -> list[str]).
    """
    # Layer 1: baseline
    taxonomy = deepcopy(_DEFAULT_PROFILE.get("tag_taxonomy", {}))

    # Layer 2: user override
    user_taxonomy = user_profile.get("tag_taxonomy", {})
    if user_taxonomy:
        taxonomy = _deep_merge(taxonomy, user_taxonomy)

    # Layer 3: auto-detected tech tags
    layer3 = _detect_tech_tags(G)
    if layer3.get("tech"):
        taxonomy = _deep_merge(taxonomy, layer3)

    return taxonomy


# ---------------------------------------------------------------------------
# EXTRACTED-only neighbor resolution (D-21 / VAULT-04)
# ---------------------------------------------------------------------------

def _extracted_neighbors(G: nx.Graph, node_id: str) -> list[str]:
    """Return node IDs of neighbors connected via EXTRACTED-confidence edges only."""
    result = []
    for u, v, d in G.edges(node_id, data=True):
        if d.get("confidence") == "EXTRACTED":
            neighbor = v if u == node_id else u
            result.append(neighbor)
    return result


# ---------------------------------------------------------------------------
# Baseline tag selection (VAULT-02 — every note gets garden/source/graph tags)
# ---------------------------------------------------------------------------

def _pick_baseline_tags(
    record: dict,
    folder_type: str,
    taxonomy: dict,
) -> list[str]:
    """Return one tag from each of garden/, source/, graph/ namespaces.

    Rules are deterministic (no randomness):
      garden: garden/question for Questions; garden/plant for everything else
      source: derived from record's source_file extension or file_type
      graph:  derived from folder_type or file_type
    """
    tags: list[str] = []

    # garden/ namespace — emit as "garden/" + safe_tag(suffix) to preserve the slash
    if folder_type == "Questions":
        tags.append("garden/" + safe_tag("question"))
    else:
        tags.append("garden/" + safe_tag("plant"))

    # source/ namespace
    file_type: str = record.get("file_type", "")
    src_path: str = record.get("source_path", record.get("source_file", ""))
    if not src_path and record.get("_source_file"):
        src_path = record["_source_file"]

    if src_path:
        ext = Path(src_path).suffix.lower()
        if ext in _TECH_EXT_MAP:
            tags.append("source/" + safe_tag("code"))
        elif file_type == "paper":
            tags.append("source/" + safe_tag("paper"))
        elif file_type == "image":
            tags.append("source/" + safe_tag("doc"))
        else:
            tags.append("source/" + safe_tag("doc"))
    elif file_type == "code":
        tags.append("source/" + safe_tag("code"))
    elif file_type == "paper":
        tags.append("source/" + safe_tag("paper"))
    else:
        tags.append("source/" + safe_tag("doc"))

    # graph/ namespace
    if file_type == "rationale":
        tags.append("graph/" + safe_tag("concept"))
    elif folder_type == "Maps":
        tags.append("graph/" + safe_tag("domain"))
    elif folder_type == "Sources":
        tags.append("graph/" + safe_tag("integration"))
    elif folder_type == "Statements":
        tags.append("graph/" + safe_tag("component"))
    else:
        tags.append("graph/" + safe_tag("component"))

    return tags


# ---------------------------------------------------------------------------
# Frontmatter field builder
# ---------------------------------------------------------------------------

def _build_frontmatter_fields(
    record: dict,
    folder_type: str,
    G: nx.Graph,
    merged_taxonomy: dict,
    run_meta: dict,
) -> dict:
    """Build the frontmatter fields dict for a given classification record.

    Returns a dict suitable for passing to profile._dump_frontmatter().
    Maps omit 'related:' and add 'stateMaps' + 'collections'.
    """
    is_map = folder_type == "Maps"
    node_id: str | None = record.get("node_id")
    community_id: int | None = record.get("community_id")

    # Determine graphifyScore
    if node_id is not None and node_id in G.nodes:
        score = G.degree(node_id)
    else:
        score = record.get("score", 0)

    # Enrich record with source_file for tag selection
    if node_id is not None and node_id in G.nodes:
        node_data = G.nodes[node_id]
        src_paths = _iter_sources(node_data.get("source_file"))
        file_type = node_data.get("file_type", "")
        record = dict(record)
        record["file_type"] = file_type
        record["_source_file"] = src_paths[0] if src_paths else ""

    # Base tags
    tags = _pick_baseline_tags(record, folder_type, merged_taxonomy)

    # Add tech/* tags from Layer 3 for this node's source_file(s)
    if node_id is not None and node_id in G.nodes:
        node_data = G.nodes[node_id]
        for src_path in _iter_sources(node_data.get("source_file")):
            ext = Path(src_path).suffix.lower()
            if ext in _TECH_EXT_MAP:
                tech_tag = "tech/" + safe_tag(_TECH_EXT_MAP[ext])
                if tech_tag not in tags:
                    tags.append(tech_tag)

    # Build fields dict (insertion-order matters for _dump_frontmatter)
    fields: dict = {}

    if is_map:
        fields["stateMaps"] = "🟥"

    fields["up"] = "[[Atlas]]"

    # related: — EXTRACTED edges only; OMIT entirely for Maps
    if not is_map and node_id is not None:
        neighbor_ids = _extracted_neighbors(G, node_id)
        related_links = []
        for n in neighbor_ids:
            neighbor_label = G.nodes[n].get("label", n) if n in G.nodes else n
            stem = safe_filename(neighbor_label)
            related_links.append(f"[[{stem}]]")
        fields["related"] = related_links

    # collections
    if is_map:
        members = record.get("members", [])
        member_links = []
        for mid in members:
            member_label = G.nodes[mid].get("label", mid) if mid in G.nodes else mid
            stem = safe_filename(member_label)
            member_links.append(f"[[{stem}]]")
        fields["collections"] = member_links
    else:
        fields["collections"] = []

    fields["created"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    fields["graphifyProject"] = safe_frontmatter_value(str(run_meta.get("project", "")))
    fields["graphifyRun"] = safe_frontmatter_value(str(run_meta.get("run_id", "")))
    fields["graphifyScore"] = score
    fields["graphifyThreshold"] = run_meta.get("threshold", 0)
    fields["tags"] = tags

    return fields


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def _load_builtin_template(note_type: str) -> string.Template:
    """Load a builtin template from graphify/builtin_templates/ via importlib.resources."""
    ref = ilr.files("graphify").joinpath("builtin_templates").joinpath(f"{note_type}.md")
    text = ref.read_text(encoding="utf-8")
    return string.Template(text)


# ---------------------------------------------------------------------------
# Note renderer — public API
# ---------------------------------------------------------------------------

def render_note(
    record: dict,
    folder_type: str,
    G: nx.Graph,
    merged_profile: dict,
    run_meta: dict,
) -> tuple[str, str]:
    """Render a single promoted note to (filename_stem, markdown_string).

    Parameters
    ----------
    record       : classification record from classify_nodes()
    folder_type  : one of Things|Questions|Maps|Sources|People|Quotes|Statements
    G            : the loaded NetworkX graph
    merged_profile: fully merged profile (Layers 1+2); Layer 3 is computed here
    run_meta     : {"project": str, "run_id": str, "threshold": int}

    Returns (safe_filename(record["label"]), rendered_markdown)
    """
    taxonomy = resolve_taxonomy(G, merged_profile)

    # Build frontmatter
    fields = _build_frontmatter_fields(record, folder_type, G, taxonomy, run_meta)
    frontmatter_str = _dump_frontmatter(fields)

    # Determine label
    label = record.get("label", "Untitled")

    # Build members_section for Maps
    members_section = ""
    if folder_type == "Maps":
        member_ids = record.get("members", [])
        lines = []
        for mid in member_ids:
            member_label = G.nodes[mid].get("label", mid) if mid in G.nodes else mid
            stem = safe_filename(member_label)
            lines.append(f"- [[{stem}|{member_label}]]")
        members_section = "\n".join(lines)

    # Build substitution dict — ALL known placeholders; unused ones get ""
    subs: dict[str, str] = {key: "" for key in _ALL_PLACEHOLDER_KEYS}
    subs["frontmatter"] = frontmatter_str
    subs["label"] = label
    subs["members_section"] = members_section

    # Load and render template
    template_name = _FOLDER_TO_TEMPLATE.get(folder_type, "thing")
    tmpl = _load_builtin_template(template_name)
    rendered = tmpl.safe_substitute(subs)

    # Filename stem
    filename_stem = safe_filename(label)

    return filename_stem, rendered


def _build_frontmatter_fields_for_source(
    record: dict,
    G: nx.Graph,
    merged_taxonomy: dict,
    run_meta: dict,
) -> dict:
    """Build frontmatter fields for a Source record (not node-backed)."""
    tags = _pick_baseline_tags(record, "Sources", merged_taxonomy)
    src_path = record.get("source_path", "")
    ext = Path(src_path).suffix.lower() if src_path else ""
    if ext in _TECH_EXT_MAP:
        tech_tag = "tech/" + safe_tag(_TECH_EXT_MAP[ext])
        if tech_tag not in tags:
            tags.append(tech_tag)

    fields: dict = {
        "up": "[[Atlas]]",
        "related": [],
        "collections": [],
        "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "graphifyProject": safe_frontmatter_value(str(run_meta.get("project", ""))),
        "graphifyRun": safe_frontmatter_value(str(run_meta.get("run_id", ""))),
        "graphifyScore": 0,
        "graphifyThreshold": run_meta.get("threshold", 0),
        "tags": tags,
    }
    return fields
