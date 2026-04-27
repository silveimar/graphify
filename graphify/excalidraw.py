"""Excalidraw template stub renderer and writer (Phase 21, TMPL-01..05).

Hard-codes the Excalidraw plugin contract for graphify-generated templates:

- ``excalidraw-plugin: parsed`` so the plugin parses the markdown Drawing
  section instead of treating it as a compressed blob.
- ``compress: false`` — a one-way door. graphify never writes compressed
  Excalidraw scenes. Tests in ``tests/test_denylist.py`` enforce that the
  ``lzstring`` package is not imported anywhere in the codebase.
- A ``## Text Elements`` heading and a ``## Drawing`` heading followed by a
  ``json`` code fence containing a valid Excalidraw scene skeleton.
- Font family 5 (Excalifont) as the ``currentItemFontFamily`` in appState.

Path confinement: every target path is routed through
``graphify.profile.validate_vault_path`` before any write, preventing
``../`` traversal via profile ``template_path`` (T-21-10, T-21-11).

Label injection: ``safe_frontmatter_value`` sanitizes names before they
land in the frontmatter ``tags:`` line (T-21-12).
"""
from __future__ import annotations


import json
import math

from pathlib import Path

from graphify.profile import safe_frontmatter_value, validate_vault_path

# Phase 22 (D-01..D-03, SKILL-06): the six valid layout_type values for the
# pure-Python Excalidraw fallback. layout_for() dispatches on these; an
# unknown value falls back to the radial mind-map layout.
_VALID_LAYOUT_TYPES = {
    "architecture",
    "workflow",
    "mind-map",
    "cuadro-sinoptico",
    "repository-components",
    "glossary-graph",
}

# Element geometry constants — integer-rounded everywhere for byte-determinism.
_NODE_W = 160
_NODE_H = 60
_GRID_X_SPACING = 200
_GRID_Y_SPACING = 150
_HORIZ_X_SPACING = 250
_RADIAL_RADIUS = 250
_STROKE_COLOR = "#1e1e2e"
_BG_COLOR = "transparent"
_FONT_FAMILY = 5  # Excalifont

# Scene JSON skeleton — keep in sync with the Excalidraw plugin schema
# (type=excalidraw, version=2). ``source`` is always "graphify" so
# downstream tools can detect graphify-generated stubs.
SCENE_JSON_SKELETON: dict = {
    "type": "excalidraw",
    "version": 2,
    "source": "graphify",
    "elements": [],
    "appState": {
        "viewBackgroundColor": "#ffffff",
        "gridSize": None,
        "currentItemFontFamily": 5,  # Excalifont
    },
    "files": {},
}


def render_stub(diagram_type: dict) -> str:
    """Render a single ``.excalidraw.md`` stub as a string.

    Args:
        diagram_type: A profile ``diagram_types`` entry — minimally needs
            a ``name`` key. Missing keys default gracefully.

    Returns:
        A UTF-8 string beginning with ``---`` frontmatter and containing
        the ``## Text Elements`` and ``## Drawing`` sections.
    """
    name = safe_frontmatter_value(str(diagram_type.get("name", "diagram")))
    scene_json = json.dumps(SCENE_JSON_SKELETON, indent=2)
    return (
        "---\n"
        "excalidraw-plugin: parsed\n"
        "compress: false\n"
        f"tags: [excalidraw, graphify, {name}]\n"
        "---\n\n"
        "## Text Elements\n\n"
        "## Drawing\n"
        "```json\n"
        f"{scene_json}\n"
        "```\n"
    )


def write_stubs(
    vault_dir: str | Path,
    diagram_types: list[dict],
    force: bool = False,
) -> list[Path]:
    """Write one ``.excalidraw.md`` stub per diagram_type entry.

    Idempotent: when ``force=False`` and a target file already exists, the
    file is skipped (not rewritten). With ``force=True``, every target is
    overwritten.

    Args:
        vault_dir: Root of the Obsidian vault. All targets are confined
            beneath this directory via ``validate_vault_path``.
        diagram_types: List of profile ``diagram_types`` entries (may be
            the full 6-entry default list, or a user-declared subset).
        force: When True, overwrite existing files.

    Returns:
        List of ``Path`` objects actually written (excludes skipped files
        in the idempotent case).
    """
    vault_root = Path(vault_dir)
    written: list[Path] = []
    for dt in diagram_types:
        rel = dt.get("template_path") or f"Excalidraw/Templates/{dt.get('name', 'diagram')}.excalidraw.md"
        # Path confinement — raises ValueError on ``..`` or absolute escape
        target = validate_vault_path(rel, vault_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            continue
        target.write_text(render_stub(dt), encoding="utf-8")
        written.append(target)
    return written


# ---------------------------------------------------------------------------
# Phase 22 (SKILL-06): pure-Python layout fallback + write_diagram
# ---------------------------------------------------------------------------


def _ensure_element_id(node: dict, i: int) -> str:
    """Return a deterministic counter-based element id, never label-derived (D-12)."""
    eid = node.get("element_id")
    if isinstance(eid, str) and eid:
        return eid
    return f"elem-{i:04d}"


def _node_rect(node: dict, i: int, x: int, y: int) -> dict:
    """Build a single Excalidraw rectangle element + paired text label."""
    elem_id = _ensure_element_id(node, i)
    label = safe_frontmatter_value(str(node.get("label", node.get("id", f"node-{i}"))))
    return {
        "id": elem_id,
        "type": "rectangle",
        "x": int(x),
        "y": int(y),
        "width": _NODE_W,
        "height": _NODE_H,
        "strokeColor": _STROKE_COLOR,
        "backgroundColor": _BG_COLOR,
        "fontFamily": _FONT_FAMILY,
        "label": label,
    }


def _text_for(node_elem: dict, i: int) -> dict:
    """Paired text element rendering the node's label inside the rectangle."""
    return {
        "id": f"{node_elem['id']}-text",
        "type": "text",
        "x": int(node_elem["x"]) + 8,
        "y": int(node_elem["y"]) + 20,
        "width": _NODE_W - 16,
        "height": 20,
        "text": node_elem["label"],
        "fontFamily": _FONT_FAMILY,
        "strokeColor": _STROKE_COLOR,
        "backgroundColor": _BG_COLOR,
        "containerId": node_elem["id"],
    }


def _arrow_elements(nodes: list[dict], edges: list[dict], start_idx: int) -> list[dict]:
    """Build arrow elements binding source.element_id → target.element_id."""
    by_id: dict[str, str] = {}
    for i, n in enumerate(nodes):
        by_id[n.get("id", "")] = _ensure_element_id(n, i)
    out: list[dict] = []
    for j, e in enumerate(edges):
        src_eid = by_id.get(e.get("source", ""))
        dst_eid = by_id.get(e.get("target", ""))
        if not src_eid or not dst_eid:
            continue
        out.append({
            "id": f"arrow-{start_idx + j:04d}",
            "type": "arrow",
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "strokeColor": _STROKE_COLOR,
            "backgroundColor": _BG_COLOR,
            "startBinding": {"elementId": src_eid},
            "endBinding": {"elementId": dst_eid},
            "label": safe_frontmatter_value(str(e.get("relation", ""))),
        })
    return out


def _layout_grid(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Square-ish grid: cols=ceil(sqrt(n)), spacing 200x / 150y, top-left (0,0)."""
    n = len(nodes)
    cols = max(1, math.ceil(math.sqrt(n))) if n > 0 else 1
    elements: list[dict] = []
    for i, node in enumerate(nodes):
        col = i % cols
        row = i // cols
        rect = _node_rect(node, i, col * _GRID_X_SPACING, row * _GRID_Y_SPACING)
        elements.append(rect)
        elements.append(_text_for(rect, i))
    elements.extend(_arrow_elements(nodes, edges, start_idx=len(elements)))
    return elements


def _layout_horizontal(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Single row left→right, 250px X spacing, y=0 (workflow / pipeline)."""
    elements: list[dict] = []
    for i, node in enumerate(nodes):
        rect = _node_rect(node, i, i * _HORIZ_X_SPACING, 0)
        elements.append(rect)
        elements.append(_text_for(rect, i))
    elements.extend(_arrow_elements(nodes, edges, start_idx=len(elements)))
    return elements


def _layout_radial(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """First node at origin; remaining placed on a circle of radius 250.

    Coordinates integer-rounded for byte-determinism (D-02).
    """
    elements: list[dict] = []
    if not nodes:
        return elements
    # First (root) node at origin
    root_rect = _node_rect(nodes[0], 0, 0, 0)
    elements.append(root_rect)
    elements.append(_text_for(root_rect, 0))
    others = nodes[1:]
    k = len(others)
    for i, node in enumerate(others, start=1):
        theta = 2 * math.pi * (i - 1) / max(1, k)
        x = round(_RADIAL_RADIUS * math.cos(theta))
        y = round(_RADIAL_RADIUS * math.sin(theta))
        rect = _node_rect(node, i, x, y)
        elements.append(rect)
        elements.append(_text_for(rect, i))
    elements.extend(_arrow_elements(nodes, edges, start_idx=len(elements)))
    return elements


def _layout_tree(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Deterministic 3-column rank stand-in for tree (no networkx in v1.5).

    First node at (0,0); remaining ranked by index → row=i//3, col=i%3.
    """
    elements: list[dict] = []
    for i, node in enumerate(nodes):
        col = i % 3
        row = i // 3
        rect = _node_rect(node, i, col * _GRID_X_SPACING, row * _GRID_Y_SPACING)
        elements.append(rect)
        elements.append(_text_for(rect, i))
    elements.extend(_arrow_elements(nodes, edges, start_idx=len(elements)))
    return elements


def layout_for(
    layout_type: str,
    nodes: list[dict],
    edges: list[dict],
) -> list[dict]:
    """Deterministic dispatch: layout_type → layout helper → elements list.

    Unknown layout_type falls back to ``_layout_radial`` (mind-map). All
    layouts are byte-deterministic: nodes iterated in receive order,
    counter-based element ids, integer-rounded coordinates, no RNG.
    """
    dispatch = {
        "architecture":          _layout_grid,
        "workflow":              _layout_horizontal,
        "mind-map":              _layout_radial,
        "cuadro-sinoptico":      _layout_tree,
        "repository-components": _layout_grid,
        "glossary-graph":        _layout_radial,
    }
    return dispatch.get(layout_type, _layout_radial)(nodes, edges)



def write_diagram(*args, **kwargs) -> Path:  # pragma: no cover — Task 4 stub
    """Stub — full implementation lands in Task 4."""
    raise NotImplementedError("write_diagram lands in Task 4")
