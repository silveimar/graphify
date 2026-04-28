"""Template engine: pure rendering functions for Obsidian notes.

Optional-dependency note (IN-10): this module is **pure stdlib** — it does
not import PyYAML, networkx, or any other third-party package. Profile
loading (`graphify.profile`) is the only consumer of PyYAML, and it does so
via a guarded `try: import yaml` so installs without the `[obsidian]` extras
group still work against the built-in default profile. The `obsidian`
extras group in `pyproject.toml` declares PyYAML for `profile.yaml` parsing
only — installing graphify without that group still gives you a fully
functional template engine running against `_DEFAULT_PROFILE`.
"""
from __future__ import annotations

import datetime
import fnmatch
import importlib.resources as ilr
import re
import string
import sys
from pathlib import Path
from typing import TypedDict

from graphify.profile import (
    _DEFAULT_PROFILE,
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
# Sentinel grammar (D-67) — body-signal half of the dual fingerprint (D-62)
# ---------------------------------------------------------------------------
# Any change to these literals MUST be mirrored in merge.py's sentinel parser:
# these strings are the source of truth for the body-signal half of the dual
# fingerprint (D-62). Plan 03/04 of Phase 4 parse them to detect graphify-owned
# body regions, refresh them on update (D-67), and respect their deletion
# (D-68). Empty sections never emit stray markers — the empty-string contract
# (D-18) is preserved by _wrap_sentinel's short-circuit on empty content.

_SENTINEL_START_FMT: str = "<!-- graphify:{name}:start -->"
_SENTINEL_END_FMT: str = "<!-- graphify:{name}:end -->"


def _wrap_sentinel(name: str, content: str) -> str:
    """Wrap a non-empty section in paired HTML-comment sentinel markers.

    Returns the original (empty) string when *content* is empty — empty
    sections never emit stray markers per the empty-string contract (D-18)
    and the D-68 deleted-block-respect rule.
    """
    if not content:
        return ""
    start = _SENTINEL_START_FMT.format(name=name)
    end = _SENTINEL_END_FMT.format(name=name)
    return f"{start}\n{content}\n{end}"

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
      - Malformed placeholders like `${bad name}` or a bare `$` → surfaced
        as errors (IN-08), not silently swallowed.
    """
    errors: list[str] = []
    found: set[str] = set()
    for m in string.Template.pattern.finditer(text):
        name = m.group("named") or m.group("braced")
        if name:
            found.add(name)
            continue
        # m.group("escaped") == "$$" → not a substitution site
        if m.group("escaped"):
            continue
        # m.group("invalid") → malformed `$` not followed by an identifier
        # (e.g. `${bad name}`, `$ `, trailing `$`). Surface a clear error
        # rather than silently ignoring it (IN-08).
        if m.group("invalid") is not None:
            snippet = m.group(0)
            errors.append(
                f"malformed placeholder near {snippet!r} — "
                "expected ${name} where name is a Python identifier"
            )
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


# IN-03: Cache the Traversable handle for the built-in templates root so we
# don't re-resolve `ilr.files("graphify")` on every template load. The handle
# itself is cheap, but ilr.files() does a package walk on each call which adds
# noticeable overhead when rendering many notes. The import lives at the top
# of the module (instead of inside _load_builtin_template) for the same reason.
_BUILTIN_TEMPLATES_ROOT = ilr.files("graphify").joinpath("builtin_templates")


def _load_builtin_template(note_type: str) -> string.Template:
    """Load a built-in template from graphify/builtin_templates/ via importlib.resources.

    Uses the cached Traversable root (Python 3.9+) — works under editable,
    wheel, and zip-archive installs. Never cast to Path() directly
    (Pattern 1 pitfall).
    """
    ref = _BUILTIN_TEMPLATES_ROOT.joinpath(f"{note_type}.md")
    text = ref.read_text(encoding="utf-8")
    return string.Template(text)


def load_templates(vault_dir: Path) -> dict[str, string.Template]:
    """Discover and load templates for all 6 note types.

    For each type, prefers a user override at
    `<vault_dir>/.graphify/templates/<type>.md` if it exists, validates, and
    falls back to the built-in on error (logging to stderr per D-22).

    Raises FileNotFoundError if `vault_dir` does not exist or is not a
    directory (IN-09). A non-existent vault_dir was previously silently
    masked because every per-type lookup just fell back to the built-in
    template — callers had no way to tell that their override directory
    was being ignored.
    """
    vault_path = Path(vault_dir)
    if not vault_path.exists():
        raise FileNotFoundError(
            f"vault_dir does not exist: {vault_path} — "
            "templates cannot be discovered. Pass a valid Obsidian vault path "
            "or omit vault_dir to use the built-in defaults."
        )
    if not vault_path.is_dir():
        raise FileNotFoundError(
            f"vault_dir is not a directory: {vault_path} — "
            "templates cannot be discovered."
        )
    templates: dict[str, string.Template] = {}
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

# Characters that break wikilink syntax when present in the display alias.
# `]]` closes the wikilink early; `|` creates a malformed alias; newlines
# break the containing callout/list/frontmatter block.
_WIKILINK_ALIAS_FORBIDDEN: dict[str, str] = {
    "]]": "] ]",
    "|": "-",
    "\n": " ",
    "\r": " ",
}

# Control characters beyond \n/\r that must be replaced with a space in
# aliases — tab, vertical tab, form feed, NEL, line/paragraph separators,
# plus the rest of the C0/DEL range — all embed invisibly inside `[[...]]`
# and break callout rendering.
_WIKILINK_ALIAS_CONTROL_RE = re.compile(
    r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f\u0085\u2028\u2029]"
)


def _sanitize_wikilink_alias(label: str) -> str:
    """Replace characters that would break wikilink alias syntax."""
    out = label
    for bad, repl in _WIKILINK_ALIAS_FORBIDDEN.items():
        out = out.replace(bad, repl)
    out = _WIKILINK_ALIAS_CONTROL_RE.sub(" ", out)
    return out


def _emit_wikilink(label: str, convention: str) -> str:
    """Return `[[filename|label]]` auto-aliased to display label.

    The filename is sanitized by resolve_filename/safe_filename.
    The display alias is sanitized by _sanitize_wikilink_alias to prevent
    injection via `]]`, `|`, or newlines in node labels (CR-01).
    """
    fname = resolve_filename(label, convention)
    alias = _sanitize_wikilink_alias(label)
    return f"[[{fname}|{alias}]]"


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
    body = (
        "> [!note] Wayfinder\n"
        f"> Up: {up_link}\n"
        f"> Map: {atlas_link}"
    )
    return _wrap_sentinel("wayfinder", body)


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
        # Strip chars that break callout bullet syntax (WR-02):
        # \n/\r split the callout line; ] closes the confidence bracket early.
        relation = str(relation).replace("\n", " ").replace("\r", " ").replace("]", "")
        confidence = str(confidence).replace("\n", " ").replace("\r", " ").replace("]", "")
        link = _emit_wikilink(target_label, convention)
        lines.append(f"> - {link} — {relation} [{confidence}]")
    if not lines:
        return ""
    body = "> [!info] Connections\n" + "\n".join(lines)
    return _wrap_sentinel("connections", body)


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
    body = "\n".join(lines)
    return _wrap_sentinel("metadata", body)


# ---------------------------------------------------------------------------
# MOC member section (D-30, D-39) — grouped by note type, empty groups omitted
# ---------------------------------------------------------------------------

_MEMBER_GROUP_ORDER: list[tuple[str, str]] = [
    # (note_type key in members_by_type, display name in callout header)
    ("thing", "Things"),
    ("statement", "Statements"),
    ("person", "People"),
    ("source", "Sources"),
]


def _build_members_section(members_by_type: dict, convention: str) -> str:
    """Build grouped `> [!info] <Group>` callouts listing community members.

    Empty groups are omitted. Each member is a bullet with an auto-aliased
    wikilink. Group order is locked: Things → Statements → People → Sources.

    IN-06: only properly structured member dicts with a non-empty `label`
    are rendered. Non-dict entries and dicts missing `label` are silently
    dropped, matching `_build_sub_communities_callout`'s policy. This avoids
    accidentally emitting `[[Filename|<repr-of-stub>]]` from raw node-id
    strings if a Phase 3 caller passes a malformed members_by_type payload.
    """
    blocks: list[str] = []
    for type_key, display_name in _MEMBER_GROUP_ORDER:
        members = members_by_type.get(type_key) or []
        if not members:
            continue
        lines = [f"> [!info] {display_name}"]
        for m in members:
            if not isinstance(m, dict):
                continue
            label = m.get("label")
            if not label:
                continue
            lines.append(f"> - {_emit_wikilink(label, convention)}")
        # Skip the group entirely if every member was dropped — otherwise we'd
        # emit a lone `> [!info] <Group>` header with no bullets.
        if len(lines) == 1:
            continue
        blocks.append("\n".join(lines))
    body = "\n\n".join(blocks)
    return _wrap_sentinel("members", body)


# ---------------------------------------------------------------------------
# Sub-communities callout (D-29) — below-threshold communities inline
# ---------------------------------------------------------------------------

def _build_sub_communities_callout(sub_communities: list, convention: str) -> str:
    """Render a `> [!abstract] Sub-communities` callout with nested bullets.

    Each sub-community becomes a bullet of the form:
    `> - **<group name>:** [[wikilink1]], [[wikilink2]], ...`
    Returns empty string when the input list is empty.
    """
    if not sub_communities:
        return ""
    lines: list[str] = ["> [!abstract] Sub-communities"]
    for sub in sub_communities:
        sub_label = sub.get("label", "Subcommunity") if isinstance(sub, dict) else str(sub)
        members = sub.get("members", []) if isinstance(sub, dict) else []
        member_links = ", ".join(
            _emit_wikilink(m.get("label", ""), convention)
            for m in members
            if isinstance(m, dict) and m.get("label")
        )
        lines.append(f"> - **{sub_label}:** {member_links}")
    body = "\n".join(lines)
    return _wrap_sentinel("sub_communities", body)


# ---------------------------------------------------------------------------
# Dataview block (D-28, Pattern 5) — two-phase substitution
# ---------------------------------------------------------------------------

# IN-01: Single source of truth — pull the default moc_query from
# _DEFAULT_PROFILE in profile.py instead of duplicating the string here.
# Updating the default in one place must not require touching the other.
_FALLBACK_MOC_QUERY: str = (
    _DEFAULT_PROFILE["obsidian"]["dataview"]["moc_query"]
)


def _build_dataview_block(profile: dict, community_tag: str, folder: str) -> str:
    """Render a ```dataview fence using the profile's moc_query template.

    Uses two-phase `string.Template` substitution (Pattern 5 in 02-RESEARCH.md):
      1. Substitute `${community_tag}` and `${folder}` INTO the user's
         query template FIRST using safe_substitute.
      2. Wrap the resulting query in a dataview fence.
      3. Pass the fence as the `${dataview_block}` value to the OUTER
         template — because `string.Template` is single-pass, any literal
         `${...}` remaining in the query text is preserved as-is.

    Inputs are sanitized before substitution (WR-05): backticks and newlines
    in `folder` or `community_tag` would break the outer dataview fence.
    Post-substitution the query is also guarded against fence-breaking chars.
    """
    moc_query = (
        profile.get("obsidian", {})
        .get("dataview", {})
        .get("moc_query")
    )
    if not moc_query:
        moc_query = _FALLBACK_MOC_QUERY

    # Strip backticks and newlines from substitution values so they cannot
    # break the ``` fence or inject new lines into the query block (WR-05).
    safe_community_tag = community_tag.replace("`", "").replace("\n", "").replace("\r", "")
    safe_folder = folder.replace("`", "").replace("\n", "").replace("\r", "")

    query = string.Template(moc_query).safe_substitute(
        community_tag=safe_community_tag,
        folder=safe_folder,
    )

    # Guard post-substitution query: ``` anywhere in the query would prematurely
    # close the dataview fence in the rendered markdown.
    query = query.replace("```", "")

    body = f"```dataview\n{query}\n```"
    return _wrap_sentinel("dataview", body)


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
    created: "datetime.date | None" = None,
) -> tuple[str, str]:
    """Render a non-MOC note (thing/statement/person/source).

    Returns (filename, rendered_text). Filename includes `.md` extension.

    The `vault_dir` keyword arg is an extension of D-41: when supplied,
    user template overrides from `<vault_dir>/.graphify/templates/` are
    honored. When omitted, only built-in templates are loaded.
    Phase 5 will pass this through from the refactored `to_obsidian()`.

    The `created` kwarg (IN-05) lets callers (and tests) pin the
    `created:` frontmatter date for reproducible/deterministic output.
    Defaults to `datetime.date.today()` for backward compatibility.
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
    # Prefer ctx["community_name"] (Phase 3-populated) over parent_moc_label
    # fallback — mirrors the preference order in _render_moc_like (WR-03).
    community_name = (
        ctx.get("community_name") or ctx.get("parent_moc_label")
    ) if isinstance(ctx, dict) else None
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
        # safe_tag ensures no spaces, uppercase, or special chars in the tag
        # component (WR-04). community_tag from ctx may not be pre-slugified.
        tag_list.append(f"community/{safe_tag(community_tag)}")
    tag_list.append(f"graphify/{safe_tag(file_type or 'note')}")

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
        # IN-05: caller-supplied date wins; default to today for back-compat.
        created=created if created is not None else datetime.date.today(),
    )

    # Phase 10 D-15: forward-map wikilinks from eliminated IDs via Obsidian aliases.
    # Only emitted when merged_from is non-empty; absent = byte-identical to pre-Phase-10.
    merged_from_ids = node.get("merged_from") or []
    if merged_from_ids:
        # Sort + dedupe; sanitize each alias for wikilink safety (T-10-05)
        aliases_list = sorted({
            _sanitize_wikilink_alias(str(mid))
            for mid in merged_from_ids
            if isinstance(mid, str) and mid
        })
        # Filter any sanitized-to-empty results (T-10-05 defense: | → space, etc.)
        aliases_list = [a for a in aliases_list if a.strip()]
        if aliases_list:
            frontmatter_fields["aliases"] = aliases_list

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


# ---------------------------------------------------------------------------
# Public: render_moc + render_community_overview (D-31, D-41)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Phase 30 / CFG-03: community_templates runtime dispatch (D-11..D-13)
# ---------------------------------------------------------------------------

def _load_override_template(rel_path: str, vault_dir, default_template):
    """Load an override template from <vault_dir>/.graphify/<rel_path>.

    On any failure (path escape, missing file, unreadable, invalid placeholders)
    emit a stderr warning and return *default_template* (graceful fallback per
    D-22 / T-30-01 mitigation).
    """
    # Function-local import to dodge potential circular import with profile.py
    from graphify.profile import validate_vault_path

    if vault_dir is None:
        # Built-in defaults context — overrides require a real vault.
        return default_template
    try:
        graphify_dir = Path(vault_dir) / ".graphify"
        canonical = validate_vault_path(rel_path, graphify_dir)
    except (ValueError, OSError) as exc:
        print(
            f"[graphify] community_templates override path rejected ({rel_path}): {exc} — using default",
            file=sys.stderr,
        )
        return default_template
    if not canonical.exists():
        print(
            f"[graphify] community_templates override missing ({rel_path}) — using default",
            file=sys.stderr,
        )
        return default_template
    try:
        text = canonical.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"[graphify] community_templates override unreadable ({rel_path}): {exc} — using default",
            file=sys.stderr,
        )
        return default_template
    errors = validate_template(text, _REQUIRED_PER_TYPE["moc"])
    if errors:
        for err in errors:
            print(
                f"[graphify] community_templates override invalid ({rel_path}): {err} — using default",
                file=sys.stderr,
            )
        return default_template
    return string.Template(text)


def _pick_community_template(
    community_id: int,
    community_name: str,
    profile: dict,
    vault_dir,
    default_template: "string.Template",
) -> "string.Template":
    """Return an override template if community_templates matches; else default.

    Rule evaluation: first-match-wins (D-13). label-match uses fnmatchcase
    (portable, case-sensitive — D-11). id-match uses exact int compare and
    rejects bool (R5).
    """
    rules = profile.get("community_templates") or []
    if not isinstance(rules, list):
        return default_template
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        match = rule.get("match")
        pattern = rule.get("pattern")
        template_path = rule.get("template")
        if not isinstance(template_path, str) or not template_path:
            continue
        if match == "label":
            if not isinstance(pattern, str) or not isinstance(community_name, str):
                continue
            if fnmatch.fnmatchcase(community_name, pattern):
                return _load_override_template(template_path, vault_dir, default_template)
        elif match == "id":
            if isinstance(pattern, bool) or not isinstance(pattern, int):
                continue
            if pattern == community_id:
                return _load_override_template(template_path, vault_dir, default_template)
    return default_template


def _render_moc_like(
    community_id: int,
    G,
    communities: dict,
    profile: dict,
    classification_context,
    template_key: str,  # "moc" or "community"
    vault_dir,
    created: "datetime.date | None" = None,
) -> tuple[str, str]:
    """Shared rendering body for MOC and Community Overview notes.

    G and `communities` are part of the D-41 public surface but are intentionally
    unused in Phase 2 MOC rendering. MOCs derive members from classification_context
    (populated by Phase 3), not by walking the graph directly. They are reserved
    for future use (IN-02):
    - Phase 3 may consult G to compute cohesion scores before populating the ctx
    - Future TMPL-xx work may emit bridge-node tables from G
    - `communities` may be needed when MOCs gain cross-community link sections
    If you find yourself reaching for G here, the right answer is almost always
    "add the derived data to ClassificationContext in Phase 3 and consume it here."
    """
    # IN-02: silence unused-argument warnings; the parameters are part of the
    # locked D-41 signature and reserved for future use per the docstring above.
    _ = G
    _ = communities
    ctx = classification_context if isinstance(classification_context, dict) else {}
    convention = profile.get("naming", {}).get("convention", "title_case")

    # Derive community display name. Preference order:
    #   1. ctx["community_name"]  (explicit; Phase 3 populates for MOC/Community Overview)
    #   2. ctx["parent_moc_label"] (fallback — Phase 3 may put MOC self-label here)
    #   3. "Community {id}"
    community_name: str = (
        ctx.get("community_name")
        or ctx.get("parent_moc_label")
        or f"Community {community_id}"
    )
    community_tag = ctx.get("community_tag") or safe_tag(community_name)
    folder = ctx.get("folder", "Atlas/Maps/")
    members_by_type = ctx.get("members_by_type", {})
    sub_communities = ctx.get("sub_communities", [])
    sibling_labels = ctx.get("sibling_labels", [])
    # Cast to plain float so numpy.float64 (not a Python float subclass) renders
    # correctly as "0.82" rather than "numpy.float64(0.82)" (WR-06).
    _raw_cohesion = ctx.get("cohesion")
    cohesion: float | None = float(_raw_cohesion) if _raw_cohesion is not None else None

    # Frontmatter
    up_list: list[str] = [_emit_wikilink(
        profile.get("obsidian", {}).get("atlas_root", "Atlas"),
        convention,
    )]
    related_list = [_emit_wikilink(lab, convention) for lab in sibling_labels if lab]
    tags = [f"community/{community_tag}", "graphify/moc"]
    fm_fields = _build_frontmatter_fields(
        up=up_list,
        related=related_list,
        collections=[],
        tags=tags,
        note_type="moc" if template_key == "moc" else "community",
        file_type=None,
        source_file=None,
        source_location=None,
        community=community_name,
        # IN-05: caller-supplied date wins; default to today for back-compat.
        created=created if created is not None else datetime.date.today(),
        cohesion=cohesion,
    )
    frontmatter = _dump_frontmatter(fm_fields)

    # Sections
    # IN-07: pass `template_key` rather than hardcoding "moc" so that the
    # wayfinder callout reflects the actual note type being rendered
    # (community overviews used to be tagged as MOCs in this code path).
    wayfinder = _build_wayfinder_callout(
        note_type=template_key,
        parent_moc_label=None,
        profile=profile,
        convention=convention,
    )
    members_section = _build_members_section(members_by_type, convention)
    sub_communities_callout = _build_sub_communities_callout(sub_communities, convention)
    dataview_block = _build_dataview_block(profile, community_tag, folder)
    metadata = _build_metadata_callout(
        source_file=None,
        source_location=None,
        community=community_name,
    )

    substitution_ctx = {
        "label": community_name,
        "frontmatter": frontmatter,
        "wayfinder_callout": wayfinder,
        "connections_callout": "",  # not used in MOCs per D-31
        "members_section": members_section,
        "sub_communities_callout": sub_communities_callout,
        "dataview_block": dataview_block,
        "metadata_callout": metadata,
        "body": "",
    }

    templates = (
        load_templates(vault_dir)
        if vault_dir is not None
        else {
            nt: _load_builtin_template(nt)
            for nt in ("thing", "statement", "person", "source", "moc", "community")
        }
    )
    default_template = templates[template_key]
    template = _pick_community_template(
        community_id, community_name, profile, vault_dir, default_template
    )
    text = template.safe_substitute(substitution_ctx)
    filename = resolve_filename(community_name, convention) + ".md"
    return filename, text


def render_moc(
    community_id: int,
    G,
    communities: dict,
    profile: dict,
    classification_context,
    *,
    vault_dir=None,
    created: "datetime.date | None" = None,
) -> tuple[str, str]:
    """Render a MOC note for a community. Returns (filename, rendered_text).

    The `created` kwarg (IN-05) lets callers pin the `created:` frontmatter
    date for reproducible/deterministic output. Defaults to today.
    """
    return _render_moc_like(
        community_id, G, communities, profile, classification_context,
        template_key="moc", vault_dir=vault_dir, created=created,
    )


def render_community_overview(
    community_id: int,
    G,
    communities: dict,
    profile: dict,
    classification_context,
    *,
    vault_dir=None,
    created: "datetime.date | None" = None,
) -> tuple[str, str]:
    """Render a Community Overview note. Same signature as render_moc but
    uses the `community.md` built-in template by default.

    The `created` kwarg (IN-05) lets callers pin the `created:` frontmatter
    date for reproducible/deterministic output. Defaults to today.
    """
    return _render_moc_like(
        community_id, G, communities, profile, classification_context,
        template_key="community", vault_dir=vault_dir, created=created,
    )
