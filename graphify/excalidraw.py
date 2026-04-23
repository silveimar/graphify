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
from pathlib import Path

from graphify.profile import safe_frontmatter_value, validate_vault_path

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
