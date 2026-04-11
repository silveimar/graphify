"""Template engine: pure rendering functions for Obsidian notes."""
from __future__ import annotations

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
