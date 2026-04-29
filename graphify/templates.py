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

import dataclasses
import datetime
import fnmatch
import importlib.resources as ilr
import re
import string
import sys
from pathlib import Path
from typing import Callable, TypedDict

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
    "moc", "community", "thing", "statement", "person", "source", "code",
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
    filename_stem: str
    filename_collision: bool
    filename_collision_hash: str
    parent_moc_label: str
    community_tag: str
    members_by_type: dict
    code_members: list
    code_member_labels: list
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
# Phase 31: Block-template machinery (TMPL-01 / TMPL-02)
# ---------------------------------------------------------------------------
#
# Block syntax (locked verbatim by ROADMAP success criteria 1 & 2):
#   {{#if_<name>}}…{{/if}}            — conditional section (TMPL-01)
#   {{#if_attr_<name>}}…{{/if}}       — raw-attribute escape hatch (D-01/D-03)
#   {{#connections}}…{{/connections}} — per-edge iteration loop (TMPL-02)
#
# Ordering invariant (D-16): block expansion runs BEFORE `safe_substitute`
# so node labels containing `{{`, `}}`, `#`, `${`, backticks, or newlines
# cannot smuggle conditional logic, fake loops, or break Dataview fences.
#
# Validation invariant (D-09/D-10): all block syntax errors surface from
# `validate_template` at preflight; render path never re-validates.
# ---------------------------------------------------------------------------


class _BlockTemplate(string.Template):
    """string.Template subclass with one-segment dot-extended idpattern.

    Per CPython, ``string.Template.__init_subclass__`` recompiles ``pattern``
    when a subclass overrides ``idpattern``. Do NOT override ``pattern``.

    The extended idpattern allows ``${conn.label}`` style identifiers used
    by the TMPL-02 connection loop (D-04/D-05) while remaining a strict
    superset of the stock identifier — block-free templates still render
    byte-identical (D-16 / ROADMAP criterion 4).
    """
    idpattern = r"(?a:[_a-z][_a-z0-9]*(?:\.[_a-z][_a-z0-9]*)?)"


_CONN_FIELDS: frozenset[str] = frozenset(
    {"label", "relation", "target", "confidence", "community", "source_file"}
)

_IF_ATTR_RE = re.compile(r"^if_attr_([a-z_][a-z0-9_]*)$")

# Block parser regexes — single-pass FSM, no recursion (T-31-03 mitigation)
_BLOCK_OPEN_RE = re.compile(r"\{\{#([a-z_][a-z0-9_]*)\}\}")
_BLOCK_CLOSE_RE = re.compile(r"\{\{/(if|connections)\}\}")

# Recognize ${conn.<field>} and ${conn_<field>} during validation/scrubbing
_CONN_FIELD_RE = re.compile(r"\$\{conn\.([a-z_][a-z0-9_]*)\}")
_CONN_FLAT_FIELD_RE = re.compile(r"\$\{conn_([a-z_][a-z0-9_]*)\}")


@dataclasses.dataclass(frozen=True)
class BlockContext:
    """Render-time context consumed by `_expand_blocks`.

    Carries the graph + node id (for predicate evaluation), the pre-built
    sorted+sanitized edge records (for `{{#connections}}` iteration), and
    a precomputed boolean for `{{#if_has_dataview}}` so the predicate need
    not re-render the dataview block.

    `graph` is annotated as `Any` because templates.py is pure stdlib
    (IN-10 — no networkx import) but the runtime value is always an
    `nx.Graph` passed in by the caller.
    """
    graph: "object"  # nx.Graph at runtime; templates.py is stdlib-only (IN-10)
    node_id: str
    edges: list[dict]
    dataview_nonempty: bool


def _pred_god_node(ctx: BlockContext) -> bool:
    node = ctx.graph.nodes.get(ctx.node_id, {})
    if node.get("is_god_node"):
        return True
    return ctx.node_id in (ctx.graph.graph.get("god_nodes") or [])


def _pred_isolated(ctx: BlockContext) -> bool:
    return (
        ctx.graph.degree(ctx.node_id) == 0
        if ctx.node_id in ctx.graph
        else False
    )


def _pred_has_connections(ctx: BlockContext) -> bool:
    return (
        ctx.graph.degree(ctx.node_id) > 0
        if ctx.node_id in ctx.graph
        else False
    )


def _pred_has_dataview(ctx: BlockContext) -> bool:
    return ctx.dataview_nonempty


_PREDICATE_CATALOG: dict[str, Callable[[BlockContext], bool]] = {
    "if_god_node": _pred_god_node,
    "if_isolated": _pred_isolated,
    "if_has_connections": _pred_has_connections,
    "if_has_dataview": _pred_has_dataview,
}


def _eval_predicate(name: str, ctx: BlockContext) -> bool:
    """Dispatch a predicate name to its catalog handler or attr escape hatch.

    Raises KeyError on unknown names — render path treats this defensively
    (D-09/D-10): preflight should have caught it via `validate_template`.
    """
    if name in _PREDICATE_CATALOG:
        return _PREDICATE_CATALOG[name](ctx)
    m = _IF_ATTR_RE.match(name)
    if m:
        attr = m.group(1)
        node = ctx.graph.nodes.get(ctx.node_id, {})
        return bool(node.get(attr))
    raise KeyError(name)


def _build_edge_records(graph, node_id) -> list[dict]:
    """Build deterministic, sanitized edge records for {{#connections}} loops.

    Field provenance (D-04/D-06) — NetworkX edge data does NOT carry
    label/community/source_file reliably; those must be sourced from the
    target node's attributes:

      - label:        target node attr 'label' (sanitized via
                      `_sanitize_wikilink_alias`) — falls back to target id
      - relation:     edge data 'relation' (default '')
      - target:       D-06 — target node 'label' (sanitized), NOT raw node id
      - confidence:   edge data 'confidence' (default '')
      - community:    target node attr 'community' (str-coerced, default '')
      - source_file:  edge data 'source_file' (default '')

    Sort: (relation ASC, label ASC) — RESEARCH OQ3 / VALIDATION ordering
    invariant. This sort is the single point that locks deterministic loop
    output across NetworkX edge-iteration order changes.
    """
    records: list[dict] = []
    if node_id not in graph:
        return records
    for u, v, data in graph.edges(node_id, data=True):
        target = v if u == node_id else u
        target_node = graph.nodes[target]
        label = _sanitize_wikilink_alias(str(target_node.get("label", target)))
        relation = _sanitize_wikilink_alias(str(data.get("relation", "")))
        confidence = _sanitize_wikilink_alias(str(data.get("confidence", "")))
        community = _sanitize_wikilink_alias(str(target_node.get("community", "")))
        source_file = _sanitize_wikilink_alias(str(data.get("source_file", "")))
        records.append({
            "label": label,
            "relation": relation,
            "target": label,
            "confidence": confidence,
            "community": community,
            "source_file": source_file,
        })
    return sorted(records, key=lambda e: (e["relation"], e["label"]))


def _expand_blocks(text: str, ctx: BlockContext) -> str:
    """Single-pass FSM expansion of `{{#…}}…{{/…}}` blocks (D-16, D-09/D-10).

    Pre-condition: `text` has already passed `validate_template` — this
    function is preflight-only-trusting and does NOT re-validate. It will
    raise `ValueError` only as a defensive invariant if it observes an
    impossible state (nested opener) on input that should have been
    rejected at preflight.

    Each `{{#connections}}` block emits BOTH `${conn.<field>}` and
    `${conn_<field>}` substituted forms (D-05) so stock `string.Template`
    AND `_BlockTemplate` both render the resulting text correctly.
    Per-iteration values are pre-sanitized inside `_build_edge_records`
    (D-15).
    """
    out_parts: list[str] = []
    pos = 0
    while pos < len(text):
        m_open = _BLOCK_OPEN_RE.search(text, pos)
        if not m_open:
            out_parts.append(text[pos:])
            break
        # Append literal text before the opener
        out_parts.append(text[pos:m_open.start()])
        opener = m_open.group(1)
        # Find the matching closer
        m_close_if = _BLOCK_CLOSE_RE.search(text, m_open.end())
        if m_close_if is None:
            # Should be unreachable on validated input
            raise ValueError(
                f"_expand_blocks: unclosed block '{{{{#{opener}}}}}' "
                "(should have been caught by validate_template)"
            )
        # Defensive: detect nested opener inside the body
        m_inner_open = _BLOCK_OPEN_RE.search(text, m_open.end(), m_close_if.start())
        if m_inner_open is not None:
            raise ValueError(
                "_expand_blocks: nested blocks not supported "
                "(should have been caught by validate_template)"
            )
        body = text[m_open.end():m_close_if.start()]
        closer = m_close_if.group(1)
        if opener == "connections":
            if closer != "connections":
                raise ValueError(
                    "_expand_blocks: block mismatch "
                    "(should have been caught by validate_template)"
                )
            # Iterate ctx.edges (already sorted via _build_edge_records)
            iterations: list[str] = []
            for record in ctx.edges:
                rendered = body
                for field in _CONN_FIELDS:
                    value = record.get(field, "")
                    rendered = rendered.replace(f"${{conn.{field}}}", value)
                    rendered = rendered.replace(f"${{conn_{field}}}", value)
                iterations.append(rendered)
            out_parts.append("".join(iterations))
        else:
            if closer != "if":
                raise ValueError(
                    "_expand_blocks: block mismatch "
                    "(should have been caught by validate_template)"
                )
            try:
                cond = _eval_predicate(opener, ctx)
            except KeyError:
                # Defensive only: preflight should have rejected this.
                cond = False
            if cond:
                out_parts.append(body)
            # else: omit the body entirely (D-19 clean elision)
        pos = m_close_if.end()
    return "".join(out_parts)


# ---------------------------------------------------------------------------
# Template validation (D-22) — follows validate.py pattern: return error list
# ---------------------------------------------------------------------------

def validate_template(text: str, required: set[str]) -> list[str]:
    """Validate a template string.

    Returns a list of error strings — empty means valid. Distinguishes:
      - `${var}` → must be in KNOWN_VARS (or `conn.<field>` / `conn_<field>`
        inside a `{{#connections}}` block — Phase 31 TMPL-02)
      - `$$` (escaped dollar) → correctly ignored (Template.pattern.escaped group)
      - `<% ... %>` Templater tokens → never matched (no `$` prefix), ignored
      - Missing placeholders from `required` → reported as errors
      - Malformed placeholders like `${bad name}` or a bare `$` → surfaced
        as errors (IN-08), not silently swallowed.
      - Phase 31 TMPL-01/TMPL-02 block syntax `{{#name}}…{{/closer}}` →
        rejected for nesting (D-07/D-08), unclosed openers, mismatched
        closers, unknown predicate names, and unknown `conn.<field>`
        references. All block validation happens at preflight (D-09/D-10).
    """
    errors: list[str] = []

    # ------------------------------------------------------------------
    # Phase 31: Block syntax validation (TMPL-01/TMPL-02)
    #
    # Block grammar (locked by ROADMAP success criteria 1 & 2):
    #   {{#if_<name>}}…{{/if}}
    #   {{#if_attr_<name>}}…{{/if}}
    #   {{#connections}}…{{/connections}}
    #
    # Validation invariants (D-07..D-10):
    #   - At most one block depth — nested openers are an error (D-07/D-08)
    #   - Every `{{#X}}` must have a matching closer
    #   - `{{#if_*}}` closes with `{{/if}}`; `{{#connections}}` with `{{/connections}}`
    #   - Predicate names must be in `_PREDICATE_CATALOG` or match `_IF_ATTR_RE`
    #   - `${conn.<field>}` references inside `{{#connections}}` must use a
    #     known field from `_CONN_FIELDS`
    # ------------------------------------------------------------------
    block_errors: list[str] = []
    body_segments: list[tuple[str, str | None]] = []  # (segment_text, opener_name_or_None)
    pos = 0
    open_name: str | None = None
    open_kind: str | None = None  # "if" | "connections"
    cursor_text_start = 0
    while pos < len(text):
        m_open = _BLOCK_OPEN_RE.search(text, pos)
        m_close = _BLOCK_CLOSE_RE.search(text, pos)
        if not m_open and not m_close:
            break
        # Pick whichever match comes first
        if m_open and (not m_close or m_open.start() < m_close.start()):
            opener = m_open.group(1)
            if open_name is not None:
                # D-08 verbatim message (with captured names)
                block_errors.append(
                    "validate_template: nested template blocks are not supported "
                    f"(found '{{{{#{opener}}}}}' inside '{{{{#{open_name}}}}}'). "
                    "Flatten the template or pre-compute the predicate."
                )
                # Fall through: skip this opener and keep searching to surface
                # additional issues consistently. We do NOT change open_name.
                pos = m_open.end()
                continue
            # capture text before the opener as a free segment
            body_segments.append((text[cursor_text_start:m_open.start()], None))
            open_name = opener
            open_kind = "connections" if opener == "connections" else "if"
            cursor_text_start = m_open.end()
            pos = m_open.end()
        else:
            assert m_close is not None
            closer = m_close.group(1)
            if open_name is None:
                block_errors.append(
                    f"validate_template: unexpected closer '{{{{/{closer}}}}}' "
                    "with no matching opener"
                )
                pos = m_close.end()
                continue
            if (open_kind == "if" and closer != "if") or (
                open_kind == "connections" and closer != "connections"
            ):
                block_errors.append(
                    f"validate_template: block mismatch — "
                    f"'{{{{#{open_name}}}}}' closed by '{{{{/{closer}}}}}'"
                )
                # Reset state defensively
                open_name = None
                open_kind = None
                cursor_text_start = m_close.end()
                pos = m_close.end()
                continue
            # Successful close: capture the body
            body_segments.append((text[cursor_text_start:m_close.start()], open_name))
            open_name = None
            open_kind = None
            cursor_text_start = m_close.end()
            pos = m_close.end()

    if open_name is not None:
        block_errors.append(
            f"validate_template: unclosed block '{{{{#{open_name}}}}}'"
        )
    # tail
    body_segments.append((text[cursor_text_start:], None))

    # Validate predicate names + connection field references per segment
    for body, opener in body_segments:
        if opener is None:
            continue
        if opener == "connections":
            for fm in _CONN_FIELD_RE.finditer(body):
                field = fm.group(1)
                if field not in _CONN_FIELDS:
                    block_errors.append(
                        f"validate_template: unknown connection field "
                        f"'conn.{field}' — valid: {sorted(_CONN_FIELDS)}"
                    )
        else:
            # Predicate name validation
            if opener in _PREDICATE_CATALOG:
                pass
            elif _IF_ATTR_RE.match(opener):
                pass
            else:
                block_errors.append(
                    f"validate_template: unknown predicate '{{{{#{opener}}}}}' "
                    f"— known: {sorted(_PREDICATE_CATALOG)} "
                    "(or use {{#if_attr_<name>}} for raw node attributes)"
                )

    errors.extend(block_errors)

    # ------------------------------------------------------------------
    # Stock $-placeholder validation. Strip block syntax + dotted
    # `${conn.<field>}` references first so they don't surface as
    # "unknown placeholder" errors.
    # ------------------------------------------------------------------
    scrubbed = _BLOCK_OPEN_RE.sub("", text)
    scrubbed = _BLOCK_CLOSE_RE.sub("", scrubbed)
    # Strip ${conn.<field>} dotted forms (validated above when inside a block)
    scrubbed = _CONN_FIELD_RE.sub("", scrubbed)
    # Strip parallel ${conn_<field>} flat forms — accept them as known
    scrubbed = _CONN_FLAT_FIELD_RE.sub("", scrubbed)

    found: set[str] = set()
    for m in string.Template.pattern.finditer(scrubbed):
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
    "code": {"frontmatter", "label"},
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
    return _BlockTemplate(text)


def load_templates(vault_dir: Path) -> dict[str, string.Template]:
    """Discover and load templates for all supported note types.

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
                templates[note_type] = _BlockTemplate(user_text)
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


def _sanitize_generated_title(label: str) -> str:
    """Normalize unsafe generated community titles before they reach sinks."""
    text = str(label)
    if not re.search(
        r'[\\/:*?"<>|#^[\]{}\x00-\x1f\x7f\u0085\u2028\u2029]|\.\.',
        text,
    ):
        return text
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not words:
        return "Community"
    return " ".join(word.capitalize() for word in words)


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


def _code_member_display_labels(
    code_members: list,
    code_member_labels: list,
) -> list[str]:
    """Return CODE member labels from structured context, preserving order."""
    labels: list[str] = []
    for member in code_members:
        if not isinstance(member, dict):
            continue
        label = member.get("filename_stem") or member.get("label")
        if label:
            labels.append(str(label))
    if not labels:
        labels = [str(label) for label in code_member_labels if label]
    return labels


def _build_code_member_links(
    code_members: list,
    code_member_labels: list,
    convention: str,
) -> list[str]:
    """Return wikilinks for CODE members, preserving exact generated targets."""
    links: list[str] = []
    for member in code_members:
        if not isinstance(member, dict):
            continue
        filename_stem = member.get("filename_stem")
        if not isinstance(filename_stem, str) or not filename_stem.strip():
            continue
        target = safe_filename(filename_stem)
        alias_source = member.get("label") or filename_stem
        alias = _sanitize_wikilink_alias(str(alias_source))
        if not alias.strip():
            alias = target
        links.append(f"[[{target}|{alias}]]")
    if links:
        return links
    return [
        _emit_wikilink(str(label), convention)
        for label in code_member_labels
        if label
    ]


def _build_code_members_section(
    code_members: list,
    code_member_labels: list,
    convention: str,
) -> str:
    """Build a MOC section linking to important CODE notes from context."""
    links = _build_code_member_links(code_members, code_member_labels, convention)
    if not links:
        return ""
    lines = ["> [!info] Important CODE Notes"]
    for link in links:
        lines.append(f"> - {link}")
    return "\n\n" + "\n".join(lines)


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


def _build_dataview_block(
    profile: dict,
    community_tag: str,
    folder: str,
    note_type: str,
) -> str:
    """Render a ```dataview fence using the profile's per-note-type query.

    Lookup order (Phase 31, TMPL-03, D-13):
      1. profile["dataview_queries"][note_type]   — Phase 31 per-note-type override
      2. profile["obsidian"]["dataview"]["moc_query"]  — legacy single-query
      3. _FALLBACK_MOC_QUERY                       — built-in default

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

    Empty-query empty-output (Phase 31, TMPL-03, Warning 7): when the resolved
    query string is empty or whitespace-only after two-phase substitution, this
    function returns the empty string `""` (no fence emitted). The downstream
    `${dataview_block}` substitution slot is therefore empty, and Plan 01's
    `BlockContext.dataview_nonempty` evaluates to False — `{{#if_has_dataview}}`
    blocks omit cleanly.
    """
    # Phase 31 (D-13) per-note-type override wins over legacy moc_query.
    per_type = (profile.get("dataview_queries") or {}).get(note_type)
    if isinstance(per_type, str) and per_type.strip():
        moc_query = per_type
    else:
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

    # Phase 31 (TMPL-03 / Warning 7): empty-query empty-output. When the
    # resolved query strips to empty, emit no fence at all so the outer
    # template's ${dataview_block} slot stays empty and {{#if_has_dataview}}
    # blocks omit cleanly via BlockContext.dataview_nonempty=False.
    if not query.strip():
        return ""

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
    """Render a non-MOC note (thing/statement/person/source/code).

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
    _KNOWN_NOTE_TYPES = ("thing", "statement", "person", "source", "code")
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
    if isinstance(ctx, dict) and ctx.get("filename_collision"):
        frontmatter_fields["filename_collision"] = True
        collision_hash = ctx.get("filename_collision_hash")
        if collision_hash:
            frontmatter_fields["filename_collision_hash"] = str(collision_hash)

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

    # Phase 31 (TMPL-03): consult per-note-type Dataview query for non-MOC
    # notes. Built-in `thing/statement/person/source/code.md` templates do not
    # currently expose a `${dataview_block}` slot, so the resolved value is
    # only surfaced if a vault override template adds the slot — but the
    # lookup itself runs unconditionally so all six note types participate
    # in the dataview_queries.<note_type> resolution chain (D-13).
    note_dataview_block = _build_dataview_block(
        profile,
        community_tag or "",
        ctx.get("folder", "") if isinstance(ctx, dict) else "",
        note_type,
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
        # Phase 31 (TMPL-03): per-note-type Dataview block. Empty when the
        # built-in template lacks `${dataview_block}` (today's thing/statement/
        # person/source/code.md), populated when a vault override adds the slot.
        "dataview_block": note_dataview_block,
    }

    if vault_dir is not None:
        templates = load_templates(vault_dir)
    else:
        templates = {
            nt: _load_builtin_template(nt)
            for nt in ("thing", "statement", "person", "source", "code", "moc", "community")
        }
    template = templates[note_type]
    # Phase 31 (D-16): expand `{{#…}}…{{/…}}` blocks BEFORE safe_substitute so
    # node labels containing `{{`, `}}`, `#`, `${`, etc. cannot inject syntax.
    block_ctx = BlockContext(
        graph=G,
        node_id=node_id,
        edges=_build_edge_records(G, node_id),
        # Phase 31 (TMPL-03): non-empty when the per-note-type query resolves
        # to a non-empty fence; empty otherwise (D-31 baseline preserved when
        # no dataview_queries.<note_type> override is configured).
        dataview_nonempty=bool(note_dataview_block.strip()),
    )
    expanded_source = _expand_blocks(template.template, block_ctx)
    text = _BlockTemplate(expanded_source).safe_substitute(substitution_ctx)

    filename_stem = ctx.get("filename_stem") if isinstance(ctx, dict) else None
    if isinstance(filename_stem, str) and filename_stem.strip():
        filename = safe_filename(filename_stem) + ".md"
    else:
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
    return _BlockTemplate(text)


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
    *,
    note_type: str | None = None,
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
    community_name = _sanitize_generated_title(community_name)
    community_tag = ctx.get("community_tag") or safe_tag(community_name)
    folder = ctx.get("folder", "Atlas/Maps/")
    members_by_type = ctx.get("members_by_type", {})
    sub_communities = ctx.get("sub_communities", [])
    sibling_labels = ctx.get("sibling_labels", [])
    code_members = ctx.get("code_members", [])
    code_member_labels = ctx.get("code_member_labels", [])
    code_links = _build_code_member_links(code_members, code_member_labels, convention)
    # Cast to plain float so numpy.float64 (not a Python float subclass) renders
    # correctly as "0.82" rather than "numpy.float64(0.82)" (WR-06).
    _raw_cohesion = ctx.get("cohesion")
    cohesion: float | None = float(_raw_cohesion) if _raw_cohesion is not None else None

    # Frontmatter
    up_list: list[str] = [_emit_wikilink(
        profile.get("obsidian", {}).get("atlas_root", "Atlas"),
        convention,
    )]
    related_labels = list(sibling_labels or [])
    related_list = [_emit_wikilink(lab, convention) for lab in related_labels if lab]
    related_list.extend(link for link in code_links if link not in related_list)
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
    members_section += _build_code_members_section(
        code_members,
        code_member_labels,
        convention,
    )
    sub_communities_callout = _build_sub_communities_callout(sub_communities, convention)
    # Phase 31 (TMPL-03): note_type drives per-note-type Dataview query lookup.
    # When the caller did not supply note_type, fall back to template_key
    # (which is already "moc" or "community" — semantically equivalent here).
    effective_note_type = note_type if note_type is not None else template_key
    dataview_block = _build_dataview_block(
        profile, community_tag, folder, effective_note_type,
    )
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
            for nt in ("thing", "statement", "person", "source", "code", "moc", "community")
        }
    )
    default_template = templates[template_key]
    template = _pick_community_template(
        community_id, community_name, profile, vault_dir, default_template
    )
    # Phase 31 (D-16): expand blocks BEFORE safe_substitute. MOCs and
    # Community Overviews operate on a community context — the synthetic
    # node_id is the community label and `{{#connections}}` blocks
    # iterate an empty edge set (loop blocks in MOC templates are out of
    # scope for these entry points; the wrapper still runs so any
    # `{{#if_*}}` blocks evaluate correctly and block-free templates
    # render unchanged).
    block_ctx = BlockContext(
        graph=G,
        node_id=community_name,
        edges=[],
        dataview_nonempty=bool(dataview_block.strip()),
    )
    expanded_source = _expand_blocks(template.template, block_ctx)
    text = _BlockTemplate(expanded_source).safe_substitute(substitution_ctx)
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

    Block expansion (Phase 31): `_render_moc_like` invokes `_expand_blocks`
    before `safe_substitute` (D-16 ordering invariant). Edge iteration data
    flows through `_build_edge_records` for deterministic ordering.
    """
    return _render_moc_like(
        community_id, G, communities, profile, classification_context,
        template_key="moc", vault_dir=vault_dir, created=created,
        note_type="moc",
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

    Block expansion (Phase 31): `_render_moc_like` invokes `_expand_blocks`
    before `safe_substitute` (D-16 ordering invariant). Edge iteration data
    flows through `_build_edge_records` for deterministic ordering.
    """
    return _render_moc_like(
        community_id, G, communities, profile, classification_context,
        template_key="community", vault_dir=vault_dir, created=created,
        note_type="community",
    )
