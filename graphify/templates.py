"""Template engine: pure rendering functions for Obsidian notes."""
from __future__ import annotations

import datetime
import re
import string
import sys
from pathlib import Path
from typing import TypedDict

from graphify.profile import (
    _dump_frontmatter,
    safe_filename,
    safe_frontmatter_value,
    safe_tag,
    validate_vault_path,
)

# ---------------------------------------------------------------------------
# Locked placeholder vocabulary (D-18, D-31, D-32)
# ---------------------------------------------------------------------------

KNOWN_VARS: frozenset[str] = frozenset({
    "label",
    "frontmatter",
    "wayfinder_callout",
    "connections_callout",
    "members_section",
    # sub_communities_callout: Claude's Discretion per D-29 (not in D-18 vocabulary)
    "sub_communities_callout",
    "dataview_block",
    "metadata_callout",
    "body",
})

_NOTE_TYPES: frozenset[str] = frozenset({
    "moc", "community", "thing", "statement", "person", "source",
})

# ---------------------------------------------------------------------------
# Classification context shape (D-42) — Phase 3 populates, Phase 2 consumes
# ---------------------------------------------------------------------------


class ClassificationContext(TypedDict, total=False):
    note_type: str
    folder: str
    parent_moc_label: str
    community_tag: str
    members_by_type: dict
    sub_communities: list
    sibling_labels: list
    # community_name: Phase 3-populated display name for the community
    # (MOCs/Community Overviews only). Falls back to parent_moc_label when absent.
    community_name: str


# ---------------------------------------------------------------------------
# Filename resolution (D-36, D-37, D-38)
# ---------------------------------------------------------------------------

def resolve_filename(label: str, convention: str) -> str:
    """Convert a node label to a filename stem (no .md extension).

    Used for BOTH disk filenames and wikilink targets — see D-19 for the
    engine-owned coupling rationale. Always pair the return value with the
    original label when emitting wikilinks: `[[{fname}|{label}]]`.
    """
    if convention == "title_case":
        # D-36: split on BOTH spaces and underscores so existing underscored
        # labels (e.g. "Neural_Network_Theory") don't collapse to a single
        # lower-cased word. Verified in 02-RESEARCH.md Pattern 4.
        #
        # LOCKED BEHAVIOR: Both title_case AND kebab-case split on the SAME
        # regex r"[ \t_]+" so that "Neural_Network_Theory" round-trips cleanly
        # in either direction (title -> kebab -> title). This is a deliberate
        # choice; research Pattern 4's space-only split was for illustrative
        # context, not a locked rule.
        words = re.split(r"[ \t_]+", label)
        result = "_".join(w.capitalize() for w in words if w)
    elif convention == "kebab-case":
        # See LOCKED BEHAVIOR note above: same r"[ \t_]+" as title_case.
        words = re.split(r"[ \t_]+", label.lower())
        result = "-".join(w for w in words if w)
    else:  # "preserve" or unknown → fall through to safe_filename
        result = label
    return safe_filename(result)


# ---------------------------------------------------------------------------
# Template validation (D-22) — follows validate.py pattern: return error list
# ---------------------------------------------------------------------------

def validate_template(text: str, required: set[str]) -> list[str]:
    """Validate a template string.

    Returns a list of error strings — empty means valid. Distinguishes:
      - `${var}` → must be in KNOWN_VARS
      - `$$` (escaped dollar) → correctly ignored (Template.pattern.escaped group)
      - `<% ... %>` Templater tokens → never matched (no `$` prefix), ignored
      - Missing placeholders from `required` → reported as errors
    """
    errors: list[str] = []
    found: set[str] = set()
    for m in string.Template.pattern.finditer(text):
        name = m.group("named") or m.group("braced")
        if name:
            found.add(name)
        # m.group("escaped") == "$$" → not a substitution site
        # m.group("invalid") → malformed, surfaced as unknown via `named`/`braced` None
    unknown = found - KNOWN_VARS
    for var in sorted(unknown):
        errors.append(f"unknown placeholder ${{{var}}} — not a graphify section var")
    for req in sorted(required):
        if req not in found:
            errors.append(f"missing required placeholder ${{{req}}}")
    return errors


# ---------------------------------------------------------------------------
# Template discovery and loading (D-20, D-21)
# ---------------------------------------------------------------------------

_REQUIRED_PER_TYPE: dict[str, set[str]] = {
    "moc": {"frontmatter", "label", "members_section", "dataview_block"},
    "community": {"frontmatter", "label", "members_section", "dataview_block"},
    "thing": {"frontmatter", "label"},
    "statement": {"frontmatter", "label"},
    "person": {"frontmatter", "label"},
    "source": {"frontmatter", "label"},
}


def _load_builtin_template(note_type: str) -> string.Template:
    """Load a built-in template from graphify/builtin_templates/ via importlib.resources.

    Uses the Traversable API (Python 3.9+) — works under editable, wheel, and
    zip-archive installs. Never cast to Path() directly (Pattern 1 pitfall).
    """
    import importlib.resources as ilr
    ref = ilr.files("graphify").joinpath("builtin_templates").joinpath(f"{note_type}.md")
    text = ref.read_text(encoding="utf-8")
    return string.Template(text)


def load_templates(vault_dir: Path) -> dict[str, string.Template]:
    """Discover and load templates for all 6 note types.

    For each type, prefers a user override at
    `<vault_dir>/.graphify/templates/<type>.md` if it exists, validates, and
    falls back to the built-in on error (logging to stderr per D-22).
    """
    templates: dict[str, string.Template] = {}
    vault_path = Path(vault_dir)
    templates_dir_rel = Path(".graphify") / "templates"
    for note_type in sorted(_NOTE_TYPES):
        required = _REQUIRED_PER_TYPE[note_type]
        user_file_rel = templates_dir_rel / f"{note_type}.md"
        user_text: str | None = None
        try:
            user_path = validate_vault_path(user_file_rel, vault_path)
            if user_path.is_file():
                user_text = user_path.read_text(encoding="utf-8")
        except (ValueError, OSError):
            user_text = None

        if user_text is not None:
            errors = validate_template(user_text, required)
            if errors:
                for err in errors:
                    print(
                        f"[graphify] template error: {note_type}.md — {err}",
                        file=sys.stderr,
                    )
                templates[note_type] = _load_builtin_template(note_type)
            else:
                templates[note_type] = string.Template(user_text)
        else:
            templates[note_type] = _load_builtin_template(note_type)
    return templates


# ---------------------------------------------------------------------------
# Wikilink emission (D-37, D-38) — single source of truth
# ---------------------------------------------------------------------------

def _emit_wikilink(label: str, convention: str) -> str:
    """Return `[[filename|label]]` auto-aliased to display label."""
    fname = resolve_filename(label, convention)
    return f"[[{fname}|{label}]]"


# ---------------------------------------------------------------------------
# Frontmatter field dict builder (D-23, D-24, D-25, D-26, D-27)
# ---------------------------------------------------------------------------

def _build_frontmatter_fields(
    *,
    up: list[str],
    related: list[str],
    collections: list[str],
    tags: list[str],
    note_type: str,
    file_type: str | None,
    source_file: str | None,
    source_location: str | None,
    community: str | None,
    created: datetime.date,
    cohesion: float | None = None,
) -> dict:
    """Build the ordered dict of frontmatter fields.

    Order (D-24): up → related → collections → created → tags → type → file_type
                 → source_file → source_location → community → cohesion

    Empty lists are SKIPPED (locked policy).
    None scalars are SKIPPED.
    `up` is always a list even when single-item (D-26).
    `cohesion` only included when note_type in {moc, community}.
    """
    fields: dict = {}
    if up:
        fields["up"] = up
    if related:
        fields["related"] = related
    if collections:
        fields["collections"] = collections
    fields["created"] = created
    if tags:
        fields["tags"] = tags
    fields["type"] = note_type
    if file_type:
        fields["file_type"] = file_type
    if source_file:
        fields["source_file"] = source_file
    if source_location:
        fields["source_location"] = source_location
    if community:
        fields["community"] = community
    if cohesion is not None and note_type in ("moc", "community"):
        fields["cohesion"] = cohesion
    return fields


# ---------------------------------------------------------------------------
# Wayfinder callout (D-35, D-39)
# ---------------------------------------------------------------------------

def _build_wayfinder_callout(
    note_type: str,
    parent_moc_label: str | None,
    profile: dict,
    convention: str,
) -> str:
    """Build a `> [!note] Wayfinder` callout with Up: and Map: rows."""
    atlas_root = profile.get("obsidian", {}).get("atlas_root", "Atlas")
    atlas_link = _emit_wikilink(atlas_root, convention)
    if note_type in ("moc", "community"):
        up_link = atlas_link
    elif parent_moc_label:
        up_link = _emit_wikilink(parent_moc_label, convention)
    else:
        up_link = atlas_link  # fallback: orphan → link directly to Atlas
    return (
        "> [!note] Wayfinder\n"
        f"> Up: {up_link}\n"
        f"> Map: {atlas_link}"
    )


# ---------------------------------------------------------------------------
# Connections callout (D-33) — iterates outgoing edges, auto-aliases
# ---------------------------------------------------------------------------

def _build_connections_callout(G, node_id: str, convention: str) -> str:
    """Build a `> [!info] Connections` callout listing outgoing edges.

    Format: `> - [[target_fname|target_label]] — relation [CONFIDENCE]`
    Returns empty string when the node has no edges.
    """
    if node_id not in G:
        return ""
    lines: list[str] = []
    # networkx Graph.edges(node, data=True) → iterable of (u, v, data)
    for u, v, data in G.edges(node_id, data=True):
        target = v if u == node_id else u
        target_label = G.nodes[target].get("label", target)
        relation = data.get("relation", "related")
        confidence = data.get("confidence", "AMBIGUOUS")
        link = _emit_wikilink(target_label, convention)
        lines.append(f"> - {link} — {relation} [{confidence}]")
    if not lines:
        return ""
    return "> [!info] Connections\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Metadata callout (D-34)
# ---------------------------------------------------------------------------

def _build_metadata_callout(
    *,
    source_file: str | None,
    source_location: str | None,
    community: str | None,
) -> str:
    """Build a `> [!abstract] Metadata` callout duplicating key fields."""
    lines: list[str] = ["> [!abstract] Metadata"]
    if source_file:
        lines.append(f"> source_file: {source_file}")
    if source_location:
        lines.append(f"> source_location: {source_location}")
    if community:
        lines.append(f"> community: {community}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public: render_note (D-32, D-41)
# ---------------------------------------------------------------------------

def render_note(
    node_id: str,
    G,
    profile: dict,
    note_type: str,
    classification_context: "ClassificationContext | dict",
    *,
    vault_dir: "Path | None" = None,
) -> tuple[str, str]:
    """Render a non-MOC note (thing/statement/person/source).

    Returns (filename, rendered_text). Filename includes `.md` extension.

    The `vault_dir` keyword arg is an extension of D-41: when supplied,
    user template overrides from `<vault_dir>/.graphify/templates/` are
    honored. When omitted, only built-in templates are loaded.
    Phase 5 will pass this through from the refactored `to_obsidian()`.
    """
    # WARNING 1: both input-validation failures raise ValueError for consistency.
    _KNOWN_NOTE_TYPES = ("thing", "statement", "person", "source")
    if note_type not in _KNOWN_NOTE_TYPES:
        raise ValueError(
            f"render_note: note_type {note_type!r} not in {sorted(_KNOWN_NOTE_TYPES)}"
        )
    if node_id not in G:
        raise ValueError(f"render_note: node_id {node_id!r} not in graph")

    convention = profile.get("naming", {}).get("convention", "title_case")
    node = G.nodes[node_id]
    label = node.get("label", node_id)
    file_type = node.get("file_type")
    source_file = node.get("source_file")
    source_location = node.get("source_location")

    ctx = classification_context
    parent_moc_label = ctx.get("parent_moc_label") if isinstance(ctx, dict) else None
    community_tag = ctx.get("community_tag") if isinstance(ctx, dict) else None
    community_name = ctx.get("parent_moc_label") if isinstance(ctx, dict) else None
    sibling_labels = ctx.get("sibling_labels", []) if isinstance(ctx, dict) else []

    # Build each section as a pre-rendered scalar (D-18)
    up_list: list[str] = []
    if parent_moc_label:
        up_list.append(_emit_wikilink(parent_moc_label, convention))

    related_list: list[str] = [
        _emit_wikilink(lab, convention) for lab in sibling_labels if lab
    ]

    tag_list: list[str] = []
    if community_tag:
        tag_list.append(f"community/{community_tag}")
    tag_list.append(f"graphify/{file_type or 'note'}")

    frontmatter_fields = _build_frontmatter_fields(
        up=up_list,
        related=related_list,
        collections=[],
        tags=tag_list,
        note_type=note_type,
        file_type=file_type,
        source_file=source_file,
        source_location=source_location,
        community=community_name,
        created=datetime.date.today(),
    )
    frontmatter = _dump_frontmatter(frontmatter_fields)

    wayfinder = _build_wayfinder_callout(
        note_type=note_type,
        parent_moc_label=parent_moc_label,
        profile=profile,
        convention=convention,
    )
    connections = _build_connections_callout(G, node_id, convention)
    metadata = _build_metadata_callout(
        source_file=source_file,
        source_location=source_location,
        community=community_name,
    )

    substitution_ctx = {
        "label": label,
        "frontmatter": frontmatter,
        "wayfinder_callout": wayfinder,
        "connections_callout": connections,
        "metadata_callout": metadata,
        "body": "",  # D-18: absent section → empty string
        # MOC-only vars provided as empty for safe_substitute idempotence
        "members_section": "",
        "sub_communities_callout": "",
        "dataview_block": "",
    }

    if vault_dir is not None:
        templates = load_templates(vault_dir)
    else:
        templates = {
            nt: _load_builtin_template(nt)
            for nt in ("thing", "statement", "person", "source", "moc", "community")
        }
    template = templates[note_type]
    text = template.safe_substitute(substitution_ctx)

    filename = resolve_filename(label, convention) + ".md"
    return filename, text
