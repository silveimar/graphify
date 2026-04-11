---
phase: 04-merge-engine
plan: 03
type: execute
wave: 2
depends_on:
  - 02
files_modified:
  - graphify/merge.py
  - tests/test_merge.py
autonomous: true
requirements:
  - MRG-01
  - MRG-02
  - MRG-06
tags:
  - merge
  - primitives
  - frontmatter-reader
  - sentinel-parser

must_haves:
  truths:
    - "graphify/merge.py module file exists with `from __future__ import annotations` and a single-line module docstring"
    - "MergeAction, MergePlan, MergeResult frozen dataclasses are defined with the exact field shape locked in D-71"
    - "_DEFAULT_FIELD_POLICIES dict maps every key graphify emits to a locked mode per D-64"
    - "Hand-rolled frontmatter reader _parse_frontmatter parses every shape _dump_frontmatter can emit: scalars, block-form lists, bools, ints, floats, ISO dates, quoted strings with escaped quotes"
    - "_parse_frontmatter returns the same dict shape back when fed the output of _dump_frontmatter (round-trip identity)"
    - "_parse_frontmatter reports malformed YAML by returning None (or raising a private sentinel) so compute_merge_plan can emit conflict_kind='malformed_frontmatter'"
    - "_parse_sentinel_blocks extracts {block_name: (start_line, end_line, content)} from a body string and distinguishes paired/unpaired/nested-malformed cases"
    - "_resolve_field_policy merges user's profile.merge.field_policies over _DEFAULT_FIELD_POLICIES and returns 'preserve' for unknown keys"
    - "_apply_field_policy dispatches a single key's merge decision given current_value, new_value, and mode"
  artifacts:
    - path: "graphify/merge.py"
      provides: "MergePlan/MergeAction/MergeResult dataclasses + hand-rolled YAML reader + sentinel parser + policy dispatcher"
      min_lines: 250
    - path: "tests/test_merge.py"
      provides: "Unit tests for every primitive: reader round-trip, sentinel parsing, policy dispatcher"
  key_links:
    - from: "graphify/merge.py::_parse_frontmatter"
      to: "graphify/profile.py::_dump_frontmatter"
      via: "symmetric inverse grammar (strict round-trip per CONTEXT Claude's Discretion)"
      pattern: "dump_frontmatter"
    - from: "graphify/merge.py::_resolve_field_policy"
      to: "graphify/profile.py::_deep_merge"
      via: "user field_policies override deep-merged over built-in table"
      pattern: "_deep_merge"
    - from: "graphify/merge.py::_DEFAULT_FIELD_POLICIES"
      to: "Phase 2 frontmatter emission (D-24, D-25)"
      via: "every key _build_frontmatter_fields can emit has an entry"
      pattern: "_DEFAULT_FIELD_POLICIES"
---

<objective>
Create `graphify/merge.py` with the primitive building blocks Plan 04 will compose into `compute_merge_plan`. This plan delivers: the public dataclasses (`MergeAction`, `MergePlan`, `MergeResult`) per D-71; the built-in field-policy table `_DEFAULT_FIELD_POLICIES` per D-64; a hand-rolled frontmatter reader that is a strict inverse of `profile.py::_dump_frontmatter` per D-23/Claude's Discretion; a sentinel-block parser per D-67; and a policy dispatcher per D-64/D-65.

Purpose: Merge's correctness depends on these primitives being independently proven. `_parse_frontmatter` and `_dump_frontmatter` must round-trip. `_parse_sentinel_blocks` must never self-heal (D-69). `_apply_field_policy` must match D-64 exactly per mode.

Output: A `merge.py` module with public dataclasses + 5 private primitives + 20+ unit tests, all importing only stdlib + `graphify.profile`. No file I/O in this plan — `compute_merge_plan` (Plan 04) and `apply_merge_plan` (Plan 05) add orchestration.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-merge-engine/04-CONTEXT.md
@.planning/phases/02-template-engine/02-CONTEXT.md
@graphify/profile.py
@graphify/templates.py
@graphify/mapping.py
@graphify/validate.py

<interfaces>
<!-- Canonical writer: merge's reader must be a strict inverse of this function -->

From graphify/profile.py L359-394 (_dump_frontmatter — emission grammar):
```python
def _dump_frontmatter(fields: dict) -> str:
    lines: list[str] = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {safe_frontmatter_value(str(item))}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        elif isinstance(value, float):
            lines.append(f"{key}: {value:.2f}")
        elif isinstance(value, datetime.date):
            lines.append(f"{key}: {value.isoformat()}")
        else:
            lines.append(f"{key}: {safe_frontmatter_value(str(value))}")
    lines.append("---")
    return "\n".join(lines)
```

From graphify/profile.py L286-322 (safe_frontmatter_value — how scalars get quoted):
- Wraps in double quotes when value has `:#[]{},`, a leading `-?!&*|>%@\``, is in {yes/no/true/false/null/on/off/~}, or matches numeric regex
- Escapes internal `"` as `\"`
- Strips newlines and control chars BEFORE the quoting decision
- Non-quoting-required values are returned bare

From graphify/templates.py (section builder constants — Plan 01 added these):
```python
_SENTINEL_START_FMT: str = "<!-- graphify:{name}:start -->"
_SENTINEL_END_FMT: str = "<!-- graphify:{name}:end -->"
```

<!-- Phase 2 D-24 frontmatter field order (the exhaustive list of keys graphify emits) -->
Field order from _build_frontmatter_fields: up, related, collections, created, tags, type, file_type, source_file, source_location, community, cohesion.

Plan 04 will ADD: graphify_managed (the frontmatter half of D-62 fingerprint). Declare its policy here.

<!-- Locked MergeAction dataclass shape from D-71 -->
```python
@dataclass(frozen=True)
class MergeAction:
    path: Path
    action: Literal["CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"]
    reason: str
    changed_fields: list[str] = field(default_factory=list)
    changed_blocks: list[str] = field(default_factory=list)
    conflict_kind: str | None = None  # "unmanaged_file" | "malformed_sentinel" | "malformed_frontmatter"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create merge.py skeleton with dataclasses + _DEFAULT_FIELD_POLICIES</name>
  <files>graphify/merge.py</files>
  <read_first>
    - graphify/profile.py (entire file — you will import `_DEFAULT_PROFILE`, `_VALID_MERGE_STRATEGIES`, `_VALID_FIELD_POLICY_MODES`, `_deep_merge`, `safe_frontmatter_value`, `_dump_frontmatter`)
    - graphify/mapping.py L1-60 (pattern for frozen dataclass module header with `from __future__ import annotations`)
    - graphify/templates.py L12-30 (module docstring + import style)
    - .planning/phases/04-merge-engine/04-CONTEXT.md D-64, D-65, D-71, D-72 (dataclass shape + policy contract)
  </read_first>
  <behavior>
    - Test 1: `from graphify.merge import MergeAction, MergePlan, MergeResult, _DEFAULT_FIELD_POLICIES` succeeds.
    - Test 2: `MergeAction(path=Path("x.md"), action="CREATE", reason="new")` constructs. `mergeaction.changed_fields == []` default.
    - Test 3: `MergeAction` is frozen — `action.path = Path("y.md")` raises `dataclasses.FrozenInstanceError`.
    - Test 4: `MergeAction(path=Path("x.md"), action="INVALID", reason="")` does NOT raise at construction time (Literal is not runtime-enforced in dataclasses), BUT `_VALID_ACTIONS` set contains exactly `{"CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"}` so downstream callers can validate.
    - Test 5: `_DEFAULT_FIELD_POLICIES["type"] == "replace"` and `["tags"] == "union"` and `["rank"] == "preserve"` and `["created"] == "preserve"` and `["graphify_managed"] == "replace"`.
    - Test 6: Every field key in `_DEFAULT_FIELD_POLICIES` is covered by `_VALID_FIELD_POLICY_MODES` (values are exclusively in `{"replace", "union", "preserve"}`).
    - Test 7: `MergePlan(actions=[], orphans=[], summary={}).summary == {}`; `MergePlan` is frozen.
  </behavior>
  <action>
Create a new file `graphify/merge.py` with exactly the following skeleton (no file I/O, no reader, no parser — those come in Task 2 and Task 3). Keep the module below 120 lines at this point.

```python
"""Merge engine: pure reconciliation of rendered notes against an existing vault."""
from __future__ import annotations

import dataclasses
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
```

DO NOT:
- Import from `graphify.export`, `graphify.templates`, `graphify.mapping` (Area-A module isolation — CONTEXT.md "Claude's Discretion: Module-level imports")
- Add any file-I/O functions yet
- Define `_parse_frontmatter` / `_parse_sentinel_blocks` / `_resolve_field_policy` / `_apply_field_policy` / `compute_merge_plan` / `apply_merge_plan` in this task — they arrive in Tasks 2-3 and Plan 04/05
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && python -c "from graphify.merge import MergeAction, MergePlan, MergeResult, _DEFAULT_FIELD_POLICIES, _VALID_ACTIONS, _VALID_CONFLICT_KINDS; from pathlib import Path; a = MergeAction(path=Path('x.md'), action='CREATE', reason='new'); assert a.changed_fields == []; assert _DEFAULT_FIELD_POLICIES['type'] == 'replace'; assert _DEFAULT_FIELD_POLICIES['tags'] == 'union'; assert _DEFAULT_FIELD_POLICIES['created'] == 'preserve'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f graphify/merge.py` — file exists
    - `head -1 graphify/merge.py` == `"""Merge engine: pure reconciliation of rendered notes against an existing vault."""`
    - `grep -q "from __future__ import annotations" graphify/merge.py` succeeds
    - `grep -q "from graphify.profile import" graphify/merge.py` succeeds AND the import block includes `_VALID_FIELD_POLICY_MODES`, `_deep_merge`, `_dump_frontmatter`, `safe_frontmatter_value`
    - `grep -q "from graphify.export" graphify/merge.py` FAILS (module isolation — merge does NOT import from export)
    - `grep -q "from graphify.templates" graphify/merge.py` FAILS
    - `grep -q "from graphify.mapping" graphify/merge.py` FAILS
    - `grep -c "@dataclass(frozen=True)" graphify/merge.py` >= 3 (MergeAction, MergePlan, MergeResult)
    - `grep -q "_DEFAULT_FIELD_POLICIES" graphify/merge.py` succeeds
    - `python -c "from graphify.merge import _DEFAULT_FIELD_POLICIES, _VALID_FIELD_POLICY_MODES; assert all(v in _VALID_FIELD_POLICY_MODES for v in _DEFAULT_FIELD_POLICIES.values())"` exits 0
    - `python -c "import dataclasses; from graphify.merge import MergeAction; from pathlib import Path; a = MergeAction(path=Path('x'), action='CREATE', reason=''); import pytest; pytest.raises(dataclasses.FrozenInstanceError, lambda: setattr(a, 'reason', 'y'))"` exits 0 (frozen enforced)
  </acceptance_criteria>
  <done>merge.py module exists with strict import hygiene; three frozen dataclasses with the locked D-71 shape; _DEFAULT_FIELD_POLICIES table covers all 14 graphify-owned frontmatter keys with correct modes; _VALID_ACTIONS and _VALID_CONFLICT_KINDS constants declared.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Hand-rolled frontmatter reader + sentinel-block parser</name>
  <files>graphify/merge.py, tests/test_merge.py</files>
  <read_first>
    - graphify/profile.py L359-394 (_dump_frontmatter — the grammar your reader MUST be the strict inverse of)
    - graphify/profile.py L286-322 (safe_frontmatter_value — understand what quoting rules produced the strings you're reading)
    - graphify/templates.py (_SENTINEL_START_FMT / _SENTINEL_END_FMT constants — the exact grammar you parse)
    - .planning/phases/04-merge-engine/04-CONTEXT.md D-67, D-68, D-69 (sentinel contract, deleted-block rule, malformed-fail-loud rule)
    - .planning/phases/02-template-engine/02-CONTEXT.md D-23, D-24, D-25, D-26 (frontmatter model — what you're parsing)
  </read_first>
  <behavior>
    - Test `test_parse_frontmatter_round_trip_scalar`: dump + parse a dict `{"type": "thing", "community": "Transformer"}` returns the same dict.
    - Test `test_parse_frontmatter_round_trip_block_list`: dump + parse `{"tags": ["community/transformer", "graphify/thing"]}` returns the same dict.
    - Test `test_parse_frontmatter_round_trip_bool`: dump + parse `{"graphify_managed": True}` returns `{"graphify_managed": True}` (bool, not the string "true").
    - Test `test_parse_frontmatter_round_trip_int`: dump + parse `{"rank": 5}` returns `{"rank": 5}` (int).
    - Test `test_parse_frontmatter_round_trip_float`: dump + parse `{"cohesion": 0.82}` returns `{"cohesion": 0.82}` (float, tolerant of `{:.2f}` rounding).
    - Test `test_parse_frontmatter_round_trip_date`: dump + parse `{"created": datetime.date(2026, 4, 11)}` returns `{"created": datetime.date(2026, 4, 11)}`.
    - Test `test_parse_frontmatter_quoted_scalar`: dump + parse `{"source_file": "foo: bar"}` (colon forces quoting) returns the original.
    - Test `test_parse_frontmatter_escaped_quote`: dump + parse `{"label": 'say "hi"'}` returns the original (internal `\"` escape inside quotes).
    - Test `test_parse_frontmatter_wikilink_inside_list`: dump + parse `{"up": ["[[Parent|Parent]]"]}` returns the original (wikilinks force quoting because of `[`).
    - Test `test_parse_frontmatter_preserves_insertion_order`: parse returns an ordered dict where `list(parsed.keys()) == ["a", "b", "c"]` when the YAML emitted them in that order.
    - Test `test_parse_frontmatter_malformed_returns_none`: a string `"---\nbad: : : :\n---"` (unparseable) returns `None`.
    - Test `test_parse_frontmatter_no_frontmatter_block_returns_empty`: a body with no `---` delimiters returns `{}` (empty dict, not None — absence of frontmatter is NOT the same as malformed).
    - Test `test_parse_sentinel_blocks_extracts_single_block`: a body `"<!-- graphify:wayfinder:start -->\nCONTENT\n<!-- graphify:wayfinder:end -->"` returns `{"wayfinder": {"content": "CONTENT", ...}}`.
    - Test `test_parse_sentinel_blocks_extracts_multiple_blocks`: body with wayfinder + connections + metadata returns three entries.
    - Test `test_parse_sentinel_blocks_unpaired_start_raises_malformed`: a body with `start -->` but no matching `end -->` returns the special `MalformedSentinel` signal (or raises a private exception — Claude's choice, documented in docstring).
    - Test `test_parse_sentinel_blocks_unpaired_end_raises_malformed`: similar — `end -->` with no matching `start -->`.
    - Test `test_parse_sentinel_blocks_nested_same_name_raises_malformed`: `start --> ... start --> ... end --> ... end -->` for the same block name fails-loud.
    - Test `test_parse_sentinel_blocks_missing_block_is_empty_not_error`: a body with ONLY a wayfinder block (no connections) returns `{"wayfinder": {...}}` — absence of a block is D-68 "deleted block, respected", NOT an error.
  </behavior>
  <action>
**Append to `graphify/merge.py`** (below the dataclasses, above any future compute_merge_plan).

Two private helpers: `_parse_frontmatter` and `_parse_sentinel_blocks`. Plus a small sentinel for malformed results.

### `_parse_frontmatter`

```python
# ---------------------------------------------------------------------------
# Hand-rolled frontmatter reader (D-23 Claude's Discretion: symmetric inverse
# of profile.py::_dump_frontmatter — DO NOT introduce PyYAML on the read path)
# ---------------------------------------------------------------------------

import datetime
import re

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
_FM_FLOAT_RE = re.compile(r"^-?\d+\.\d{2}$")  # _dump_frontmatter always uses {:.2f}

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
            result[key] = _coerce_scalar(rhs)
            current_list_key = None
        i += 1
    # fell off the end without a closing "---"
    return None
```

### `_parse_sentinel_blocks`

```python
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
    MergeAction(action='SKIP_CONFLICT', conflict_kind='malformed_sentinel')."""


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
```

### Create `tests/test_merge.py`

A new file with the test class `TestParseFrontmatter` (12 tests from the behavior list for the reader) and `TestParseSentinelBlocks` (5 tests for the parser). Use `datetime.date(2026, 4, 11)` literals, not `datetime.date.today()`, so tests are deterministic. Import via `from graphify.merge import _parse_frontmatter, _parse_sentinel_blocks, _MalformedSentinel`.

Round-trip tests follow this pattern (write once, use everywhere):

```python
def _round_trip(fields: dict) -> dict:
    from graphify.profile import _dump_frontmatter
    from graphify.merge import _parse_frontmatter
    dumped = _dump_frontmatter(fields)
    parsed = _parse_frontmatter(dumped)
    assert parsed is not None, f"parse returned None for dumped: {dumped!r}"
    return parsed
```

**DO NOT:**
- Import PyYAML anywhere in merge.py or the tests
- Attempt to handle YAML flow-style lists `[a, b, c]` — `_dump_frontmatter` only emits block-form lists, so the reader only needs to accept block-form
- Self-heal any malformed input (D-69 is absolute)
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && pytest tests/test_merge.py -k "parse_frontmatter or parse_sentinel" -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def _parse_frontmatter" graphify/merge.py` succeeds
    - `grep -q "def _parse_sentinel_blocks" graphify/merge.py` succeeds
    - `grep -q "class _MalformedSentinel" graphify/merge.py` succeeds
    - `grep -q "import yaml" graphify/merge.py` FAILS (no PyYAML on read path)
    - `test -f tests/test_merge.py` — file exists
    - `grep -c "def test_parse_frontmatter_round_trip" tests/test_merge.py` >= 8
    - `grep -c "def test_parse_sentinel_blocks" tests/test_merge.py` >= 5
    - `pytest tests/test_merge.py -k "parse_frontmatter" -q` exits 0 with at least 10 tests passing
    - `pytest tests/test_merge.py -k "parse_sentinel" -q` exits 0 with at least 5 tests passing
    - `python -c "from graphify.merge import _parse_frontmatter; assert _parse_frontmatter('---\ntype: thing\ntags:\n  - a\n  - b\n---') == {'type': 'thing', 'tags': ['a', 'b']}"` exits 0
    - `python -c "from graphify.merge import _parse_sentinel_blocks; r = _parse_sentinel_blocks('before\n<!-- graphify:foo:start -->\nX\n<!-- graphify:foo:end -->\nafter'); assert r == {'foo': 'X'}"` exits 0
  </acceptance_criteria>
  <done>Hand-rolled frontmatter reader is a strict inverse of _dump_frontmatter for all 7 type branches; sentinel parser extracts paired blocks and raises _MalformedSentinel on every malformed case; 15+ unit tests cover round-trip, type coercion, unpaired, nested, and deleted-block scenarios; merge.py has zero PyYAML dependency.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Policy dispatcher — _resolve_field_policy + _apply_field_policy</name>
  <files>graphify/merge.py, tests/test_merge.py</files>
  <read_first>
    - graphify/merge.py (the file you've built so far — dataclasses and _DEFAULT_FIELD_POLICIES are already in place)
    - graphify/profile.py L82-90 (_deep_merge — reuse for overlay semantics)
    - .planning/phases/04-merge-engine/04-CONTEXT.md D-64, D-65 (policy modes and override semantics)
    - tests/test_merge.py (the file you started in Task 2 — append to it, don't recreate)
  </read_first>
  <behavior>
    - Test `test_resolve_field_policy_uses_builtin_for_known_key`: `_resolve_field_policy("tags", profile={})` returns `"union"`.
    - Test `test_resolve_field_policy_uses_builtin_for_replace_key`: `_resolve_field_policy("type", profile={})` returns `"replace"`.
    - Test `test_resolve_field_policy_unknown_key_defaults_to_preserve`: `_resolve_field_policy("priority", profile={})` returns `"preserve"`.
    - Test `test_resolve_field_policy_user_override_wins_for_known_key`: `_resolve_field_policy("tags", profile={"merge": {"field_policies": {"tags": "replace"}}})` returns `"replace"`.
    - Test `test_resolve_field_policy_user_override_wins_for_unknown_key`: `_resolve_field_policy("priority", profile={"merge": {"field_policies": {"priority": "replace"}}})` returns `"replace"`.
    - Test `test_resolve_field_policy_preserves_other_builtins_when_overriding_one`: after override, `_resolve_field_policy("type", profile=override_profile_for_tags)` still returns `"replace"` from built-in.
    - Test `test_resolve_field_policy_preserve_fields_list_forces_preserve`: a field listed in `profile.merge.preserve_fields` returns `"preserve"` EVEN IF field_policies would say otherwise. Precedence: preserve_fields > field_policies > _DEFAULT_FIELD_POLICIES > unknown-default `preserve`.
    - Test `test_apply_field_policy_replace_overwrites`: `_apply_field_policy("type", current="statement", new="thing", mode="replace")` returns `"thing"`.
    - Test `test_apply_field_policy_preserve_keeps_current`: `_apply_field_policy("rank", current=5, new=10, mode="preserve")` returns `5`.
    - Test `test_apply_field_policy_preserve_keeps_missing_current`: `_apply_field_policy("rank", current=None, new=10, mode="preserve")` returns `None` (user hasn't set it → graphify doesn't either under preserve).
    - Test `test_apply_field_policy_union_merges_lists_stable_order`: `_apply_field_policy("tags", current=["user/x", "community/t"], new=["community/t", "graphify/thing"], mode="union")` returns `["user/x", "community/t", "graphify/thing"]` (current items first, then new items not already in current — stable order, deduped).
    - Test `test_apply_field_policy_union_with_empty_current`: `_apply_field_policy("up", current=[], new=["[[Parent|Parent]]"], mode="union")` returns `["[[Parent|Parent]]"]`.
    - Test `test_apply_field_policy_union_with_none_current`: `_apply_field_policy("up", current=None, new=["[[Parent|Parent]]"], mode="union")` returns `["[[Parent|Parent]]"]`.
    - Test `test_apply_field_policy_replace_with_none_new_removes`: `_apply_field_policy("cohesion", current=0.82, new=None, mode="replace")` returns `None` (graphify is no longer emitting this field — honor the removal).
    - Test `test_apply_field_policy_union_on_non_list_falls_back_to_replace`: `_apply_field_policy("tags", current="not-a-list", new=["a"], mode="union")` returns `["a"]` (malformed current → overwrite, matches D-64 union semantics on degraded input).
  </behavior>
  <action>
**Append to `graphify/merge.py`** (below the sentinel parser).

### `_resolve_field_policy`

```python
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
```

### Extend `tests/test_merge.py`

Append a `TestPolicyDispatcher` class (or flat test functions) covering the 15 behavior cases above. Every test is a single-line assertion (`assert _resolve_field_policy(...)` or `assert _apply_field_policy(...)`), no fixtures required. Use `_DEFAULT_FIELD_POLICIES` imported constants to express the built-in expectations without duplicating values.

Example:

```python
def test_resolve_field_policy_preserve_fields_list_forces_preserve():
    profile = {"merge": {
        "preserve_fields": ["tags"],
        "field_policies": {"tags": "replace"},  # would normally win over built-in
    }}
    assert _resolve_field_policy("tags", profile) == "preserve", \
        "preserve_fields list must override field_policies"

def test_apply_field_policy_union_merges_lists_stable_order():
    result = _apply_field_policy(
        "tags",
        current=["user/x", "community/t"],
        new=["community/t", "graphify/thing"],
        mode="union",
    )
    assert result == ["user/x", "community/t", "graphify/thing"]
```

**DO NOT:**
- Mutate `current` in place — return a new list so callers can trust immutability
- Try to do a set-union (order would be lost — D-64 "union, deduped, order-stable" requires list-based dedup)
- Add any I/O or filesystem calls
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && pytest tests/test_merge.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def _resolve_field_policy" graphify/merge.py` succeeds
    - `grep -q "def _apply_field_policy" graphify/merge.py` succeeds
    - `grep -c "def test_resolve_field_policy" tests/test_merge.py` >= 7
    - `grep -c "def test_apply_field_policy" tests/test_merge.py` >= 8
    - `grep -q "preserve_fields list must override" tests/test_merge.py` succeeds (precedence comment present in the locked test)
    - `pytest tests/test_merge.py -k "field_policy" -q` exits 0 with at least 15 tests passing
    - `pytest tests/test_merge.py -q` exits 0 (Task 2's tests still green alongside Task 3's)
    - `python -c "from graphify.merge import _resolve_field_policy, _apply_field_policy; assert _resolve_field_policy('tags', {}) == 'union'; assert _resolve_field_policy('priority', {}) == 'preserve'; assert _apply_field_policy('tags', ['a'], ['a', 'b'], 'union') == ['a', 'b']"` exits 0
  </acceptance_criteria>
  <done>_resolve_field_policy implements the 4-tier precedence (preserve_fields > user field_policies > built-in > unknown-default); _apply_field_policy implements all three modes per D-64 semantics; 15+ dispatcher unit tests pass; full test_merge.py suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| note-file-on-disk → `_parse_frontmatter` | User-edited file with potentially-adversarial YAML content |
| note-file-on-disk → `_parse_sentinel_blocks` | User-edited body that may contain comment-like strings inside wikilinks or callouts |
| profile.yaml → `_resolve_field_policy` | User-supplied field_policies overlay (already validated by Plan 02, but defense-in-depth matters) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-08 | Tampering | Crafted frontmatter with `key: !!python/object/apply:os.system` trying to exploit a YAML loader | mitigate | No YAML loader is invoked. `_parse_frontmatter` walks lines with regex only; `!!python/...` tokens are treated as literal strings by `_coerce_scalar` and fall through to the string branch. Test in Task 2: add `test_parse_frontmatter_rejects_yaml_tags_as_literal` asserting `key: "!!python/object/apply:os.system"` round-trips as the literal string. |
| T-04-09 | Tampering | Crafted body with sentinel-like comments in user prose (e.g., a user writes `<!-- graphify:fake:start -->` inside a ${body} region) | mitigate | `_parse_sentinel_blocks` extracts ANY matched pair. A user writing sentinel-lookalike prose accidentally claims that block as graphify-owned. This is an accepted tradeoff per D-62 (dual-signal ownership): if a user strips the frontmatter signal, their fake sentinel still needs the frontmatter `graphify_managed: true` to trigger merge. Plan 04's compute_merge_plan checks both signals. Document in _parse_sentinel_blocks docstring as a known behavior, not a bug. |
| T-04-10 | Tampering | Nested sentinel blocks (same name opened twice before closing) designed to smuggle content | mitigate | `_parse_sentinel_blocks` raises `_MalformedSentinel` on duplicate or nested blocks. The file becomes SKIP_CONFLICT with `conflict_kind="malformed_sentinel"` in Plan 04 — fail loud, never self-heal. Tested in Task 2. |
| T-04-11 | Information Disclosure | `_parse_frontmatter` returning None silently when the caller expects `{}` | mitigate | Return contract is documented: `{}` = no frontmatter, dict = valid, None = malformed. Type checker enforces None handling. Plan 04 raises SKIP_CONFLICT on None. |
| T-04-12 | Elevation of Privilege | Malicious profile.merge.field_policies setting `{"graphify_managed": "preserve"}` to freeze the fingerprint | accept | As noted in Plan 02 T-04-04: user-local config is equivalent trust to CLI flags. A user who edits their own profile to stop fingerprint refresh is exercising local authority. Documented in `_resolve_field_policy` docstring. |
| T-04-13 | Tampering | `_apply_field_policy` union on user's list containing a `[[malicious|href]]` wikilink that survives into graphify's rewritten frontmatter | accept | Wikilinks are strings; union treats them as opaque. Emission back to disk goes through `safe_frontmatter_value`, which is the line of defense. No new attack surface vs Phase 1. |
</threat_model>

<verification>
- `pytest tests/test_merge.py -q` passes with 30+ tests
- Round-trip property: for every dict fed to _dump_frontmatter + _parse_frontmatter, the result equals the input (modulo float {:.2f} rounding)
- Sentinel parser: every malformed case raises _MalformedSentinel; every well-formed case returns the expected dict
- No PyYAML import in merge.py: `grep -q "import yaml" graphify/merge.py` fails
</verification>

<success_criteria>
- `graphify/merge.py` module exists with public dataclasses + 5 private primitives (_parse_frontmatter, _parse_sentinel_blocks, _unquote_scalar, _coerce_scalar, _resolve_field_policy, _apply_field_policy)
- Hand-rolled reader is a strict inverse of _dump_frontmatter for all 7 type branches
- Sentinel parser handles paired, unpaired, nested, deleted-block cases per D-67/D-68/D-69
- Policy dispatcher implements 4-tier precedence: preserve_fields > user field_policies > built-in table > unknown-default preserve
- 30+ unit tests in tests/test_merge.py, all green
- No imports from `graphify.export`, `graphify.templates`, `graphify.mapping` — merge is standalone
- No PyYAML on the read path
</success_criteria>

<output>
After completion, create `.planning/phases/04-merge-engine/04-03-SUMMARY.md` documenting: the dataclass shapes, the _DEFAULT_FIELD_POLICIES table (full dump), the reader's regex grammar, the sentinel parser's state machine, and the policy dispatcher's precedence chain.
</output>
