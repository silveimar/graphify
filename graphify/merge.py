"""Merge engine: pure reconciliation of rendered notes against an existing vault."""
from __future__ import annotations

import dataclasses
import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from graphify.profile import (
    _DEFAULT_PROFILE,
    _VALID_FIELD_POLICY_MODES,
    _VALID_MERGE_STRATEGIES,
    _deep_merge,
    _dump_frontmatter,
    safe_frontmatter_value,
)


# ---------------------------------------------------------------------------
# Action vocabulary (D-71) — valid values for MergeAction.action
# ---------------------------------------------------------------------------

_VALID_ACTIONS: frozenset[str] = frozenset({
    "CREATE",
    "UPDATE",
    "SKIP_PRESERVE",
    "SKIP_CONFLICT",
    "REPLACE",
    "ORPHAN",
})

_VALID_CONFLICT_KINDS: frozenset[str] = frozenset({
    "unmanaged_file",
    "malformed_sentinel",
    "malformed_frontmatter",
})


# ---------------------------------------------------------------------------
# Built-in per-key field policy table (D-64)
# ---------------------------------------------------------------------------

# Policy rationale:
# - `replace`  — identity-bearing graphify scalars that MUST track the new graph state
# - `union`    — graphify-owned lists that users legitimately extend
# - `preserve` — user-authored or once-only fields that must survive UPDATE
#
# Unknown frontmatter keys (user-added, not emitted by graphify) default to
# `preserve` at dispatch time — see _resolve_field_policy's fallback.
_DEFAULT_FIELD_POLICIES: dict[str, str] = {
    # Graphify-owned scalars (D-64 replace list)
    "type": "replace",
    "file_type": "replace",
    "source_file": "replace",
    "source_location": "replace",
    "community": "replace",
    "cohesion": "replace",
    "graphify_managed": "replace",  # Fingerprint scalar (D-62) — always refreshed on UPDATE
    # Graphify-owned lists (D-64 union list)
    "up": "union",
    "related": "union",
    "collections": "union",
    "tags": "union",
    # User-stewarded fields (D-64 preserve list) — defaults also in profile.merge.preserve_fields
    "rank": "preserve",
    "mapState": "preserve",
    "created": "preserve",
}


# ---------------------------------------------------------------------------
# Public dataclasses (D-71)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MergeAction:
    """One row in a MergePlan — decision for a single file path.

    See D-71 for field semantics. `action` is a Literal for type-checker
    benefit only — runtime validation uses the _VALID_ACTIONS set.
    """
    path: Path
    action: Literal["CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"]
    reason: str
    changed_fields: list[str] = field(default_factory=list)
    changed_blocks: list[str] = field(default_factory=list)
    conflict_kind: str | None = None


@dataclass(frozen=True)
class MergePlan:
    """Pure data structure produced by compute_merge_plan (Plan 04).

    Consumed by apply_merge_plan (Plan 05) or printed by Phase 5 --dry-run.
    JSON-serializable via dataclasses.asdict.
    """
    actions: list[MergeAction]
    orphans: list[Path]
    summary: dict[str, int]


@dataclass(frozen=True)
class MergeResult:
    """Mirror of MergePlan recording write outcomes after apply_merge_plan.

    success/failed are per-path partitions; skipped_identical captures files
    where content-hash comparison avoided a write (Claude's Discretion in
    CONTEXT.md — content-hash skip).
    """
    plan: MergePlan
    succeeded: list[Path]
    failed: list[tuple[Path, str]]   # (path, error_message)
    skipped_identical: list[Path]


# ---------------------------------------------------------------------------
# Hand-rolled frontmatter reader (D-23 Claude's Discretion: symmetric inverse
# of profile.py::_dump_frontmatter — DO NOT introduce PyYAML on the read path)
# ---------------------------------------------------------------------------

# Grammar notes (inverse of _dump_frontmatter):
# - A frontmatter block starts with a line exactly "---" and ends with "---".
# - Each in-block line is either a scalar "key: value" or a list header "key:"
#   followed by block-form items "  - value".
# - Scalars may be bare, double-quoted (with escaped \"), or typed:
#   true/false, integers, {:.2f} floats, ISO dates YYYY-MM-DD.
# - Unknown shapes fall through to string (mirrors the `else` branch in dumper).

_FM_DELIM_RE = re.compile(r"^---\s*$")
_FM_SCALAR_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
_FM_LIST_ITEM_RE = re.compile(r"^\s{2}-\s(.*)$")
_FM_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FM_INT_RE = re.compile(r"^-?\d+$")
# _dump_frontmatter emits floats via `f"{v:.2f}"`, but users may hand-edit a
# fingerprinted file and write `cohesion: 0.5` or `cohesion: 0.123`. The
# reader must round-trip any well-formed decimal to float so the next
# compute_merge_plan doesn't report churn purely because "0.5" (string) !=
# 0.5 (float). Intentionally stricter than YAML: no bare keywords, no
# scientific notation (mirrors `_dump_frontmatter`'s isinstance ladder —
# scientific notation is a degenerate case rejected at emission time).
_FM_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")  # WR-04: any decimal precision


def _unquote_scalar(raw: str) -> str:
    """Inverse of safe_frontmatter_value quoting.

    Removes surrounding double-quotes if present and unescapes internal
    \\" → ". Bare values are returned as-is.
    """
    raw = raw.strip()
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('\\"', '"')
    return raw


def _coerce_scalar(raw: str):
    """Apply type coercion inverse to _dump_frontmatter's type-dispatch ladder.

    Order matters: check typed forms BEFORE falling back to string, mirroring
    the isinstance ladder in _dump_frontmatter (bool → int → float → date → str).
    """
    # quoted string short-circuits — quoting forces string type
    stripped = raw.strip()
    if len(stripped) >= 2 and stripped.startswith('"') and stripped.endswith('"'):
        return _unquote_scalar(stripped)
    if stripped == "true":
        return True
    if stripped == "false":
        return False
    if _FM_INT_RE.match(stripped):
        return int(stripped)
    if _FM_FLOAT_RE.match(stripped):
        return float(stripped)
    if _FM_ISO_DATE_RE.match(stripped):
        try:
            return datetime.date.fromisoformat(stripped)
        except ValueError:
            return stripped
    return stripped  # bare string


def _parse_frontmatter(body: str) -> dict | None:
    """Parse a graphify-authored frontmatter block into an ordered dict.

    Returns:
      - {}   when there is no `---` block at the top of body
      - dict when the block parses cleanly
      - None when the block is malformed (unclosed delimiter, unknown line shape)

    Malformed → None is how compute_merge_plan detects the
    conflict_kind="malformed_frontmatter" case in Plan 04.
    """
    lines = body.split("\n")
    if not lines or not _FM_DELIM_RE.match(lines[0]):
        return {}
    result: dict = {}
    current_list_key: str | None = None
    i = 1
    while i < len(lines):
        line = lines[i]
        if _FM_DELIM_RE.match(line):
            return result
        # list item line?
        list_match = _FM_LIST_ITEM_RE.match(line)
        if list_match:
            if current_list_key is None:
                return None  # orphan list item
            result[current_list_key].append(_unquote_scalar(list_match.group(1)))
            i += 1
            continue
        # scalar or list-header line?
        scalar_match = _FM_SCALAR_RE.match(line)
        if not scalar_match:
            # unknown line shape — bail (CONTEXT: never self-heal, fail loud)
            return None
        key, rhs = scalar_match.group(1), scalar_match.group(2)
        if rhs == "":
            # list header — next lines must be list items
            result[key] = []
            current_list_key = key
        else:
            # A bare rhs starting with ':' means _dump_frontmatter would have
            # quoted it (safe_frontmatter_value quotes ':' anywhere). A line
            # like `key: : : :` is unambiguously malformed on the read path.
            rhs_stripped = rhs.strip()
            if rhs_stripped and rhs_stripped[0] == ":" and not (
                rhs_stripped.startswith('"') or rhs_stripped.startswith("'")
            ):
                return None
            result[key] = _coerce_scalar(rhs)
            current_list_key = None
        i += 1
    # fell off the end without a closing "---"
    return None


# ---------------------------------------------------------------------------
# Sentinel block parser (D-67, D-68, D-69)
# ---------------------------------------------------------------------------

# Mirror graphify.templates._SENTINEL_START_FMT / _SENTINEL_END_FMT exactly.
# Duplicated here (not imported) because CONTEXT.md Claude's Discretion says
# merge.py has NO dependency on templates.py — module isolation.
_SENTINEL_START_RE = re.compile(r"<!--\s*graphify:([A-Za-z_][A-Za-z0-9_]*):start\s*-->")
_SENTINEL_END_RE = re.compile(r"<!--\s*graphify:([A-Za-z_][A-Za-z0-9_]*):end\s*-->")


class _MalformedSentinel(Exception):
    """Private signal — compute_merge_plan catches this and emits
    MergeAction(action='SKIP_CONFLICT', conflict_kind='malformed_sentinel').

    T-04-09 note: a user writing sentinel-lookalike prose accidentally claims
    that block as graphify-owned. This is an accepted tradeoff per D-62
    (dual-signal ownership): if a user strips the frontmatter signal, their
    fake sentinel still needs the frontmatter `graphify_managed: true` to
    trigger merge. Plan 04's compute_merge_plan checks both signals.
    """


def _parse_sentinel_blocks(body: str) -> dict[str, str]:
    """Extract {block_name: content_between_markers} from a note body.

    Returns a mapping only for blocks whose start AND end markers are both
    present, in order, and not nested for the same name. Blocks that don't
    appear in the body are simply absent from the returned dict — this is
    D-68 "deleted blocks are respected" behavior.

    Raises `_MalformedSentinel` when:
      - a start marker has no matching end marker
      - an end marker appears with no prior start marker
      - the same block name is opened twice before being closed

    D-69 rule: NEVER self-heal. The caller (compute_merge_plan) catches the
    exception and records SKIP_CONFLICT with conflict_kind="malformed_sentinel".
    """
    # Walk the body linearly. Maintain a stack of currently-open block names.
    # Any deviation from the paired-in-order contract raises _MalformedSentinel.
    lines = body.split("\n")
    blocks: dict[str, str] = {}
    open_block: tuple[str, int] | None = None  # (name, start_line_idx)
    for idx, line in enumerate(lines):
        start_match = _SENTINEL_START_RE.search(line)
        end_match = _SENTINEL_END_RE.search(line)
        if start_match and end_match:
            # Both on one line — only legal if same block with empty content
            if start_match.group(1) != end_match.group(1):
                raise _MalformedSentinel(f"mixed start/end on line {idx}")
            if open_block is not None:
                raise _MalformedSentinel(
                    f"nested same-line block while {open_block[0]!r} still open"
                )
            blocks[start_match.group(1)] = ""
            continue
        if start_match:
            if open_block is not None:
                raise _MalformedSentinel(
                    f"nested start {start_match.group(1)!r} while "
                    f"{open_block[0]!r} still open at line {idx}"
                )
            open_block = (start_match.group(1), idx)
            continue
        if end_match:
            if open_block is None:
                raise _MalformedSentinel(
                    f"end marker {end_match.group(1)!r} with no open block at line {idx}"
                )
            if open_block[0] != end_match.group(1):
                raise _MalformedSentinel(
                    f"end marker {end_match.group(1)!r} does not match "
                    f"open block {open_block[0]!r} at line {idx}"
                )
            content = "\n".join(lines[open_block[1] + 1 : idx])
            if open_block[0] in blocks:
                raise _MalformedSentinel(
                    f"duplicate block {open_block[0]!r} at line {idx}"
                )
            blocks[open_block[0]] = content
            open_block = None
    if open_block is not None:
        raise _MalformedSentinel(f"unclosed block {open_block[0]!r}")
    return blocks


# ---------------------------------------------------------------------------
# Policy dispatcher (D-64, D-65)
# ---------------------------------------------------------------------------

def _resolve_field_policy(key: str, profile: dict) -> str:
    """Resolve the merge mode for a single frontmatter key.

    Precedence (highest first):
      1. `profile.merge.preserve_fields` list — hard preserve, no override possible.
         (This is the user-facing "don't touch" list from Phase 1 MRG-02.)
      2. `profile.merge.field_policies.<key>` — user's per-key override.
      3. `_DEFAULT_FIELD_POLICIES.<key>` — graphify's built-in policy table.
      4. Unknown keys → `"preserve"` (conservative — never clobber user fields
         graphify has never seen).

    T-04-12 note: a malicious profile could set `{"graphify_managed": "preserve"}`
    to freeze the fingerprint. This is accepted — user-local config is equivalent
    trust to CLI flags. A user who edits their own profile to stop fingerprint
    refresh is exercising local authority.
    """
    merge_cfg = profile.get("merge", {}) if isinstance(profile, dict) else {}
    preserve_list = merge_cfg.get("preserve_fields") or []
    if key in preserve_list:
        return "preserve"
    user_policies = merge_cfg.get("field_policies") or {}
    if key in user_policies:
        return user_policies[key]
    if key in _DEFAULT_FIELD_POLICIES:
        return _DEFAULT_FIELD_POLICIES[key]
    return "preserve"


def _apply_field_policy(
    key: str,
    current,
    new,
    mode: str,
):
    """Apply a single-key merge decision.

    Modes:
      - `replace`  — return `new` (including None, which means "graphify is
                     no longer emitting this key, remove it").
      - `preserve` — return `current` (including None, which means "user
                     hasn't set it either, stay missing").
      - `union`    — list-wise union: current items first (preserving user's
                     stable order), then new items not already present.
                     Non-list current → fall through to replace semantics.

    T-04-13 note: union on a user's list containing wikilinks treats them as
    opaque strings. The defense is at emission time via safe_frontmatter_value.
    """
    if mode == "replace":
        return new
    if mode == "preserve":
        return current
    if mode == "union":
        if not isinstance(current, list):
            return new if new is not None else current
        if new is None:
            return list(current)
        if not isinstance(new, list):
            return new  # degraded new shape — replace
        merged = list(current)
        for item in new:
            if item not in merged:
                merged.append(item)
        return merged
    # Unknown mode — treat as preserve (conservative)
    return current


# ---------------------------------------------------------------------------
# Canonical frontmatter key order (D-24) — source of truth for
# slot-near-neighbor insertion when adding new keys to existing files.
# This list MUST match graphify.templates._build_frontmatter_fields order.
# ---------------------------------------------------------------------------

_CANONICAL_KEY_ORDER: list[str] = [
    "up",
    "related",
    "collections",
    "created",
    "tags",
    "type",
    "file_type",
    "source_file",
    "source_location",
    "community",
    "cohesion",
    "graphify_managed",
]


# ---------------------------------------------------------------------------
# RenderedNote TypedDict — input shape for compute_merge_plan
# ---------------------------------------------------------------------------

from typing import TypedDict


class RenderedNote(TypedDict):
    """Input shape for compute_merge_plan's rendered_notes parameter.

    Phase 5's to_obsidian() builds this dict by calling render_note / render_moc
    from templates.py and adding the target_path from mapping.py's MappingResult.
    """
    node_id: str
    target_path: Path
    frontmatter_fields: dict
    body: str


# ---------------------------------------------------------------------------
# Fingerprint check (D-62)
# ---------------------------------------------------------------------------

def _has_fingerprint(parsed_fm: dict | None, blocks: dict[str, str]) -> bool:
    """True iff EITHER fingerprint signal (D-62) is present."""
    if parsed_fm and parsed_fm.get("graphify_managed"):
        return True
    return bool(blocks)


# ---------------------------------------------------------------------------
# Body-start locator + path confinement gate
# ---------------------------------------------------------------------------

def _find_body_start(text: str) -> int:
    """Byte index of the first char after the closing `---` delimiter of a
    frontmatter block. Returns 0 when no frontmatter is present.
    """
    if not text.startswith("---"):
        return 0
    second = text.find("\n---", 3)
    if second == -1:
        return 0
    end = text.find("\n", second + 1)
    if end == -1:
        return len(text)
    return end + 1


def _validate_target(candidate: Path, vault_dir: Path) -> Path:
    """Gate every candidate path through profile.validate_vault_path.

    Raises ValueError if the path escapes vault_dir.

    WR-03: Absolute candidates are resolved via `.resolve()` before being
    made relative to `vault_dir`. `vault_dir` is likewise resolved. This
    ensures symlink parity on platforms like macOS, where `/tmp` is a
    symlink to `/private/tmp`: without resolving, an absolute candidate
    passed in as `/private/tmp/...` against a `vault_dir` of `/tmp/...`
    (or vice versa) would raise ValueError from `Path.relative_to` even
    though both paths point at the same vault.
    """
    from graphify.profile import validate_vault_path
    if candidate.is_absolute():
        resolved_vault = vault_dir.resolve()
        resolved_candidate = candidate.resolve()
        try:
            rel = resolved_candidate.relative_to(resolved_vault)
        except ValueError as exc:
            raise ValueError(
                f"{candidate!r} escapes vault directory {vault_dir}"
            ) from exc
    else:
        rel = candidate
    return validate_vault_path(rel, vault_dir)


# ---------------------------------------------------------------------------
# Frontmatter merge helpers (D-66)
# ---------------------------------------------------------------------------

def _insert_with_canonical_neighbor(target: dict, key: str, value) -> dict:
    """Insert `key: value` into `target` using canonical-neighbor ordering.

    Behavior (WR-02 — kept as-is, matches callers' expectations):
      - If `key` is NOT in `_CANONICAL_KEY_ORDER`, append at end.
      - If `key` IS canonical and `target` contains a preceding canonical
        key (anything listed before `key` in `_CANONICAL_KEY_ORDER`), insert
        immediately after the nearest such neighbor.
      - If `key` IS canonical but NO preceding canonical neighbor exists in
        `target`, *prepend* `key` at the start of the dict. This ensures
        graphify-owned canonical keys lead user-authored content — e.g.
        `{"rank": 5}` + new `source_file` becomes
        `{"source_file": ..., "rank": 5}`, not the reverse.
    """
    if key not in _CANONICAL_KEY_ORDER:
        new_dict = dict(target)
        new_dict[key] = value
        return new_dict

    canonical_idx = _CANONICAL_KEY_ORDER.index(key)
    preceding = _CANONICAL_KEY_ORDER[:canonical_idx]
    neighbor: str | None = None
    for candidate in reversed(preceding):
        if candidate in target:
            neighbor = candidate
            break

    new_dict: dict = {}
    if neighbor is None:
        new_dict[key] = value
        for k, v in target.items():
            new_dict[k] = v
        return new_dict

    for k, v in target.items():
        new_dict[k] = v
        if k == neighbor:
            new_dict[key] = value
    return new_dict


def _merge_frontmatter(
    existing: dict,
    new: dict,
    profile: dict,
) -> tuple[dict, list[str]]:
    """Merge new frontmatter into existing, preserving order + per-key policy.

    D-66 ordering rule: keys already in `existing` keep their position;
    keys in `new` but not in `existing` are slotted after their nearest
    preceding canonical neighbor from _CANONICAL_KEY_ORDER. If no preceding
    canonical neighbor is present in `existing`, the new key is *prepended*
    so graphify-owned canonical keys always lead user-authored content
    (see `_insert_with_canonical_neighbor`). Non-canonical `new`-only keys
    are appended at end.

    Returns (merged_dict, changed_keys_list).
    """
    merged: dict = {}
    changed: list[str] = []
    new_consumed: set[str] = set()

    for key, current_value in existing.items():
        mode = _resolve_field_policy(key, profile)
        if key in new:
            updated = _apply_field_policy(key, current_value, new[key], mode)
            new_consumed.add(key)
        else:
            # Not in new render
            if mode == "preserve":
                updated = current_value
            else:
                updated = None  # graphify removed — drop from output
        if updated is None:
            if current_value is not None:
                changed.append(key)
            continue
        if updated != current_value:
            changed.append(key)
        merged[key] = updated

    new_only = [k for k in new if k not in new_consumed]
    for key in new_only:
        mode = _resolve_field_policy(key, profile)
        if mode == "preserve":
            continue
        value = _apply_field_policy(key, None, new[key], mode)
        if value is None:
            continue
        merged = _insert_with_canonical_neighbor(merged, key, value)
        changed.append(key)

    return merged, changed


# ---------------------------------------------------------------------------
# Body block merge helper (D-68)
# ---------------------------------------------------------------------------

def _locate_sentinel_block_ranges(body: str) -> dict[str, tuple[int, int]]:
    """Return {block_name: (start_line_idx, end_line_idx)} for each paired block.

    Line indices are the positions of the start and end marker lines in
    `body.split("\n")`. Used by `_merge_body_blocks` to splice refreshed
    content by line range, avoiding the regex-vs-literal asymmetry that
    plagues string-replace-based body rewrites (WR-01).

    Assumes `body` has already been validated by `_parse_sentinel_blocks`;
    callers must guard against `_MalformedSentinel` before calling this.
    """
    lines = body.split("\n")
    ranges: dict[str, tuple[int, int]] = {}
    open_name: str | None = None
    open_idx: int = -1
    for idx, line in enumerate(lines):
        start_match = _SENTINEL_START_RE.search(line)
        end_match = _SENTINEL_END_RE.search(line)
        if start_match and end_match and start_match.group(1) == end_match.group(1):
            ranges[start_match.group(1)] = (idx, idx)
            continue
        if start_match:
            open_name = start_match.group(1)
            open_idx = idx
            continue
        if end_match and open_name == end_match.group(1):
            ranges[open_name] = (open_idx, idx)
            open_name = None
            open_idx = -1
    return ranges


def _merge_body_blocks(
    existing_body: str,
    existing_blocks: dict[str, str],
    new_blocks: dict[str, str],
) -> tuple[str, list[str]]:
    """Refresh existing body blocks in place; never re-insert deleted ones (D-68).

    Walks existing_blocks (what's currently in the file) and replaces each
    with its counterpart from new_blocks. Blocks in new_blocks not present
    in existing_blocks are D-68 "deleted, respected" and NOT re-inserted.
    Blocks in existing_blocks not in new_blocks are left unchanged.

    Splicing is done by line index (from `_locate_sentinel_block_ranges`),
    NOT by literal-string `.replace()`. This guarantees symmetry with the
    regex-based `_parse_sentinel_blocks` parser: any marker line accepted by
    the parser will be correctly rewritten here, regardless of surrounding
    whitespace variations the regex tolerates (WR-01).
    """
    changed: list[str] = []
    if not existing_blocks:
        return existing_body, changed

    # Build list of (name, start_idx, end_idx) for blocks that need refresh,
    # sorted by start_idx so the splice indices stay stable as we rebuild.
    ranges = _locate_sentinel_block_ranges(existing_body)
    to_refresh: list[tuple[str, int, int]] = []
    for name, existing_content in existing_blocks.items():
        if name not in new_blocks:
            continue
        if new_blocks[name] == existing_content:
            continue
        if name not in ranges:
            # Parser accepted it but locator couldn't find a line range —
            # shouldn't happen in practice, but fail loud rather than silently
            # reporting a fake refresh.
            raise _MalformedSentinel(
                f"block {name!r} parsed but has no locatable line range"
            )
        start_idx, end_idx = ranges[name]
        to_refresh.append((name, start_idx, end_idx))

    if not to_refresh:
        return existing_body, changed

    # Sort by start_idx ascending, then rebuild line-by-line so that earlier
    # splices don't invalidate later indices.
    to_refresh.sort(key=lambda x: x[1])
    lines = existing_body.split("\n")
    out_lines: list[str] = []
    cursor = 0
    for name, start_idx, end_idx in to_refresh:
        # Copy unchanged lines up to (but not including) the start marker line.
        out_lines.extend(lines[cursor:start_idx])
        # Preserve the original start-marker line verbatim (user formatting survives).
        out_lines.append(lines[start_idx])
        # Insert the refreshed content.
        new_content = new_blocks[name]
        if new_content:
            out_lines.extend(new_content.split("\n"))
        # Preserve the original end-marker line verbatim (or, for single-line
        # blocks where start_idx == end_idx, skip — the single line acts as both).
        if end_idx != start_idx:
            out_lines.append(lines[end_idx])
        cursor = end_idx + 1
        changed.append(name)
    out_lines.extend(lines[cursor:])
    return "\n".join(out_lines), changed


# ---------------------------------------------------------------------------
# compute_merge_plan — pure read-only orchestration (D-70, D-71, D-72)
# ---------------------------------------------------------------------------

def compute_merge_plan(
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],
    profile: dict,
    *,
    skipped_node_ids: set[str] | None = None,
    previously_managed_paths: set[Path] | None = None,
) -> MergePlan:
    """Pure reconciliation of rendered notes against a vault on disk.

    Produces a MergePlan listing per-file MergeAction decisions. Never writes.
    Phase 5's --dry-run calls this directly.
    """
    vault_dir = Path(vault_dir).resolve()
    skipped_node_ids = skipped_node_ids or set()
    strategy = profile.get("merge", {}).get("strategy", "update")
    if strategy not in _VALID_MERGE_STRATEGIES:
        strategy = "update"

    actions: list[MergeAction] = []
    orphan_paths: list[Path] = []
    rendered_path_set: set[Path] = set()

    for node_id, rn in rendered_notes.items():
        if node_id in skipped_node_ids:
            continue
        raw_target = Path(rn["target_path"])
        try:
            target_path = _validate_target(raw_target, vault_dir)
        except ValueError as exc:
            actions.append(MergeAction(
                path=raw_target,
                action="SKIP_CONFLICT",
                reason=f"path escape: {exc}",
                conflict_kind="unmanaged_file",
            ))
            continue
        rendered_path_set.add(target_path)

        if not target_path.exists():
            actions.append(MergeAction(
                path=target_path,
                action="CREATE",
                reason="new file",
            ))
            continue

        # File exists — read and parse
        existing_text = target_path.read_text(encoding="utf-8")
        parsed_fm = _parse_frontmatter(existing_text)
        body_start = _find_body_start(existing_text)
        existing_body = existing_text[body_start:]

        if parsed_fm is None:
            actions.append(MergeAction(
                path=target_path,
                action="SKIP_CONFLICT",
                reason="malformed frontmatter — file left untouched",
                conflict_kind="malformed_frontmatter",
            ))
            continue

        try:
            existing_blocks = _parse_sentinel_blocks(existing_body)
        except _MalformedSentinel as exc:
            actions.append(MergeAction(
                path=target_path,
                action="SKIP_CONFLICT",
                reason=f"malformed sentinel: {exc}",
                conflict_kind="malformed_sentinel",
            ))
            continue

        if not _has_fingerprint(parsed_fm, existing_blocks):
            actions.append(MergeAction(
                path=target_path,
                action="SKIP_CONFLICT",
                reason="no fingerprint — refusing to overwrite unmanaged file",
                conflict_kind="unmanaged_file",
            ))
            continue

        # Fingerprinted existing file — strategy dispatch
        if strategy == "skip":
            actions.append(MergeAction(
                path=target_path,
                action="SKIP_PRESERVE",
                reason="strategy=skip leaves existing files untouched",
            ))
            continue
        if strategy == "replace":
            actions.append(MergeAction(
                path=target_path,
                action="REPLACE",
                reason="strategy=replace overwrites fingerprinted file",
            ))
            continue

        # strategy == "update" — per-field + per-block diff
        _, changed_fields = _merge_frontmatter(parsed_fm, rn["frontmatter_fields"], profile)
        try:
            new_blocks = _parse_sentinel_blocks(rn["body"])
        except _MalformedSentinel:
            # Shouldn't happen — graphify-emitted bodies are always well-formed
            new_blocks = {}
        _, changed_blocks = _merge_body_blocks(existing_body, existing_blocks, new_blocks)

        reason = "idempotent re-render" if not changed_fields and not changed_blocks else "update"
        actions.append(MergeAction(
            path=target_path,
            action="UPDATE",
            reason=reason,
            changed_fields=changed_fields,
            changed_blocks=changed_blocks,
        ))

    # Orphan detection (D-72)
    if previously_managed_paths:
        for prior in previously_managed_paths:
            try:
                prior_resolved = _validate_target(Path(prior), vault_dir)
            except ValueError:
                continue
            if prior_resolved in rendered_path_set:
                continue
            if not prior_resolved.exists():
                continue
            orphan_paths.append(prior_resolved)
            actions.append(MergeAction(
                path=prior_resolved,
                action="ORPHAN",
                reason="node no longer in graph — reported, never deleted",
            ))

    summary: dict[str, int] = {}
    for a in actions:
        summary[a.action] = summary.get(a.action, 0) + 1

    return MergePlan(actions=actions, orphans=orphan_paths, summary=summary)


# ---------------------------------------------------------------------------
# Apply layer (D-70 side-effectful half) — atomic writes, content-hash skip
# ---------------------------------------------------------------------------

import hashlib
import os


def _hash_bytes(data: bytes) -> str:
    """SHA-256 hash of bytes — used for content-identical skip comparison."""
    return hashlib.sha256(data).hexdigest()


def _write_atomic(target: Path, content: str) -> None:
    """Write *content* to *target* atomically via .tmp + os.replace.

    Raises OSError on write / replace failure. Best-effort unlinks the .tmp
    file if the sequence aborts mid-flight.
    """
    tmp = target.with_suffix(target.suffix + ".tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _cleanup_stale_tmp(vault_dir: Path) -> None:
    """Unlink any .md.tmp files left over from a previous aborted apply run.

    Called once at the top of apply_merge_plan as a defensive pass (CONTEXT
    Claude's Discretion: "Clean up stale .tmp files at the top of
    apply_merge_plan as a defensive pass.")
    """
    for tmp in vault_dir.rglob("*.md.tmp"):
        try:
            tmp.unlink()
        except OSError:
            continue


def _synthesize_file_text(
    action: MergeAction,
    rendered_note: RenderedNote,
    existing_text: str | None,
    profile: dict,
) -> str:
    """Produce the final file text for a given MergeAction.

    CREATE / REPLACE: emit _dump_frontmatter(rendered.frontmatter_fields) + rendered.body
    UPDATE: re-merge frontmatter against existing, refresh body blocks in place

    Raises ValueError for actions this function cannot handle (SKIP_*, ORPHAN).
    """
    if action.action in ("CREATE", "REPLACE"):
        fm_text = _dump_frontmatter(rendered_note["frontmatter_fields"])
        body = rendered_note["body"]
        # Ensure exactly one newline between frontmatter block and body
        if body.startswith("\n"):
            return fm_text + body
        return fm_text + "\n" + body

    if action.action == "UPDATE":
        assert existing_text is not None
        parsed_fm = _parse_frontmatter(existing_text)
        if parsed_fm is None:
            raise ValueError("UPDATE action on file with unparseable frontmatter")
        body_start = _find_body_start(existing_text)
        existing_body = existing_text[body_start:]
        merged_fm, _ = _merge_frontmatter(parsed_fm, rendered_note["frontmatter_fields"], profile)
        existing_blocks = _parse_sentinel_blocks(existing_body)
        new_blocks = _parse_sentinel_blocks(rendered_note["body"])
        merged_body, _ = _merge_body_blocks(existing_body, existing_blocks, new_blocks)
        fm_text = _dump_frontmatter(merged_fm)
        if merged_body.startswith("\n"):
            return fm_text + merged_body
        return fm_text + "\n" + merged_body

    raise ValueError(f"_synthesize_file_text cannot handle action {action.action!r}")


def apply_merge_plan(
    plan: MergePlan,
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],
    profile: dict,
) -> MergeResult:
    """Consume a MergePlan and apply writes to disk.

    Writes ONLY CREATE, UPDATE, REPLACE actions. Skips SKIP_PRESERVE,
    SKIP_CONFLICT, and ORPHAN (D-72: orphans reported, never deleted).

    Content-hash compare: before writing UPDATE or REPLACE, compute SHA-256
    of new vs existing content and skip the write entirely if identical.
    Skipped paths go into MergeResult.skipped_identical.

    Atomic writes: `.tmp + fsync + os.replace` (Claude's Discretion).

    Re-validates every target path via _validate_target before writing
    (defense in depth; compute already did this).
    """
    vault_dir = Path(vault_dir).resolve()
    _cleanup_stale_tmp(vault_dir)

    succeeded: list[Path] = []
    failed: list[tuple[Path, str]] = []
    skipped_identical: list[Path] = []

    # Index rendered_notes by target_path for O(1) lookup per action.
    # compute_merge_plan already resolved target_paths to absolute; but the
    # plan's action.path is the validated absolute path, so match on that.
    notes_by_path: dict[Path, RenderedNote] = {}
    for rn in rendered_notes.values():
        try:
            resolved = _validate_target(Path(rn["target_path"]), vault_dir)
        except ValueError:
            continue
        notes_by_path[resolved] = rn

    for action in plan.actions:
        if action.action in ("SKIP_PRESERVE", "SKIP_CONFLICT", "ORPHAN"):
            continue
        try:
            target = _validate_target(action.path, vault_dir)
        except ValueError as exc:
            failed.append((action.path, f"path escape on apply: {exc}"))
            continue

        rendered = notes_by_path.get(target)
        if rendered is None:
            failed.append((target, "no rendered note matches action path"))
            continue

        existing_text: str | None = None
        if action.action == "UPDATE":
            try:
                existing_text = target.read_text(encoding="utf-8")
            except OSError as exc:
                failed.append((target, f"read existing failed: {exc}"))
                continue

        try:
            new_text = _synthesize_file_text(action, rendered, existing_text, profile)
        except (ValueError, _MalformedSentinel) as exc:
            failed.append((target, f"synthesis failed: {exc}"))
            continue

        # Content-hash skip: compare bytes
        new_bytes = new_text.encode("utf-8")
        if target.exists():
            try:
                existing_bytes = target.read_bytes()
            except OSError:
                existing_bytes = b""
            if _hash_bytes(new_bytes) == _hash_bytes(existing_bytes):
                skipped_identical.append(target)
                continue

        try:
            _write_atomic(target, new_text)
            succeeded.append(target)
        except OSError as exc:
            failed.append((target, f"write failed: {exc}"))

    return MergeResult(
        plan=plan,
        succeeded=succeeded,
        failed=failed,
        skipped_identical=skipped_identical,
    )
