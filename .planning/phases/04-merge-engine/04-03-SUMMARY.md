---
phase: 04-merge-engine
plan: 03
subsystem: merge
tags: [merge, primitives, frontmatter-reader, sentinel-parser, policy-dispatcher, tdd, phase-4]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "profile.py safety helpers + _DEFAULT_PROFILE + validate_profile pattern"
  - phase: 04-02
    provides: "_VALID_FIELD_POLICY_MODES + _DEFAULT_PROFILE.merge.field_policies shape + preserve_fields['created']"
provides:
  - "graphify/merge.py: MergeAction/MergePlan/MergeResult frozen dataclasses (D-71)"
  - "_DEFAULT_FIELD_POLICIES built-in per-key policy table (D-64) — 14 keys"
  - "_parse_frontmatter: hand-rolled strict inverse of _dump_frontmatter (D-23)"
  - "_parse_sentinel_blocks: fail-loud sentinel parser, raises _MalformedSentinel (D-67/D-68/D-69)"
  - "_resolve_field_policy: 4-tier precedence dispatcher (D-65)"
  - "_apply_field_policy: replace/union/preserve mode executor (D-64)"
affects:
  - 04-04-compute-merge-plan  # composes all primitives into compute_merge_plan()
  - 04-05-apply-merge-plan    # consumes MergePlan + MergeResult
  - 05-integration            # CLI --dry-run prints MergePlan; --validate-profile validates profile

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hand-rolled regex YAML reader as strict inverse of _dump_frontmatter — no PyYAML on read path"
    - "Fail-loud sentinel parsing: _MalformedSentinel exception, never self-heal (D-69)"
    - "4-tier policy precedence: preserve_fields > user field_policies > built-in > unknown-default preserve"
    - "Frozen dataclasses for immutable plan/result types (mirrors MappingResult precedent)"
    - "Module isolation: merge.py imports only from graphify.profile + stdlib"

key-files:
  created:
    - graphify/merge.py
    - tests/test_merge.py
  modified: []

key-decisions:
  - "Hand-rolled frontmatter reader, not PyYAML — _parse_frontmatter is a strict inverse of _dump_frontmatter's grammar (7 type branches: list, bool, int, float, date, quoted string, bare string)"
  - "Malformed bare value starting with ':' returns None — _dump_frontmatter always quotes ':' via safe_frontmatter_value, so a bare ':' rhs is unambiguously not graphify-emitted"
  - "_MalformedSentinel is a private exception class (not a sentinel return value) — caller pattern is try/except, not None-check; more Pythonic and prevents accidental swallowing"
  - "All three tasks implemented in one GREEN commit (Tasks 2 + 3 code appended to same file per plan's action blocks) with a single RED commit covering all 46 tests — RED/GREEN boundary is clean"
  - "T-04-09 accepted: sentinel-lookalike user prose is claimed by merge — documented in _MalformedSentinel docstring; Plan 04's dual-signal check (frontmatter + sentinel) is the defense"

patterns-established:
  - "Policy-table-as-module-default: merge owns _DEFAULT_FIELD_POLICIES; profile.merge.field_policies deep-merges overrides via _resolve_field_policy 4-tier lookup"
  - "Round-trip invariant: _dump_frontmatter(d) |> _parse_frontmatter == d for all valid graphify-emitted dicts"
  - "Fail-loud primitive contract: parsers return None (frontmatter) or raise (sentinel) on malformed input; never guess or self-heal"

requirements-completed: [MRG-01, MRG-02, MRG-06]

# Metrics
duration: ~4min
completed: 2026-04-11
---

# Phase 4 Plan 03: Merge Primitives Module Summary

**graphify/merge.py delivers the pure primitive layer: three frozen dataclasses (D-71), a 14-key built-in field-policy table (D-64), a hand-rolled YAML frontmatter reader that is a strict inverse of _dump_frontmatter, a fail-loud sentinel block parser, and a 4-tier policy dispatcher — all stdlib only, no PyYAML.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-11T16:51:41Z
- **Completed:** 2026-04-11T16:55:08Z
- **Tasks:** 3 (all TDD)
- **Files created:** 2 (`graphify/merge.py`, `tests/test_merge.py`)
- **Tests added:** 46 (12 dataclass/policy + 13 frontmatter reader + 6 sentinel parser + 15 dispatcher)
- **Tests passing:** 46 / 46

## Accomplishments

- `graphify/merge.py` created (388 lines) with complete primitive layer:
  - `_VALID_ACTIONS`, `_VALID_CONFLICT_KINDS` vocabulary constants
  - `_DEFAULT_FIELD_POLICIES` — 14-key built-in table (replace: 7 graphify scalars; union: 4 graphify lists; preserve: 3 user-stewarded fields)
  - `MergeAction`, `MergePlan`, `MergeResult` frozen dataclasses matching D-71 locked shape
  - `_unquote_scalar`, `_coerce_scalar` — scalar parsing helpers
  - `_parse_frontmatter` — hand-rolled YAML reader, strict inverse of `_dump_frontmatter`
  - `_MalformedSentinel` — private exception class for sentinel failures
  - `_parse_sentinel_blocks` — fail-loud sentinel extractor per D-67/D-68/D-69
  - `_resolve_field_policy` — 4-tier precedence resolver per D-65
  - `_apply_field_policy` — mode executor (replace/union/preserve) per D-64
- `tests/test_merge.py` created (313 lines) with 46 tests across 4 classes

## _DEFAULT_FIELD_POLICIES Table (full)

| Key | Mode | Rationale |
|-----|------|-----------|
| `type` | replace | graphify identity scalar — must track graph state |
| `file_type` | replace | graphify identity scalar |
| `source_file` | replace | graphify identity scalar |
| `source_location` | replace | graphify identity scalar |
| `community` | replace | graphify identity scalar |
| `cohesion` | replace | graphify identity scalar |
| `graphify_managed` | replace | fingerprint (D-62) — always refreshed |
| `up` | union | graphify list + user contributions preserved |
| `related` | union | graphify list + user contributions preserved |
| `collections` | union | graphify list + user contributions preserved |
| `tags` | union | graphify list + user contributions preserved |
| `rank` | preserve | user-stewarded — never overwritten |
| `mapState` | preserve | user-stewarded — never overwritten |
| `created` | preserve | set once at first CREATE (D-27) — never overwritten |

## Frontmatter Reader Grammar

`_parse_frontmatter` is a strict inverse of `_dump_frontmatter` using 5 compiled regexes:

| Regex | Matches |
|-------|---------|
| `_FM_DELIM_RE` | `^---\s*$` — block open/close delimiter |
| `_FM_SCALAR_RE` | `^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$` — key + rhs |
| `_FM_LIST_ITEM_RE` | `^\s{2}-\s(.*)$` — block-form list item |
| `_FM_ISO_DATE_RE` | `^\d{4}-\d{2}-\d{2}$` — ISO date |
| `_FM_INT_RE` | `^-?\d+$` — integer |
| `_FM_FLOAT_RE` | `^-?\d+\.\d{2}$` — `{:.2f}` float |

Type coercion ladder (mirrors `_dump_frontmatter` isinstance order):
1. Quoted string (`"..."`) → unquote + unescape `\"` → str
2. `true`/`false` → bool
3. Integer pattern → int
4. Float `{:.2f}` pattern → float
5. ISO date pattern → `datetime.date`
6. Bare string → str

Return contract: `{}` = no frontmatter block, `dict` = valid parse, `None` = malformed.

T-04-08 safety: `!!python/object/apply:...` tagged YAML is treated as a literal string — no YAML loader invoked, regex-only parsing.

## Sentinel Parser State Machine

`_parse_sentinel_blocks` walks lines linearly with a single `open_block` slot (one block open at a time):

```
initial: open_block = None
  start_match, no open_block → set open_block = (name, idx)
  start_match, open_block set → raise _MalformedSentinel (nested)
  end_match, no open_block   → raise _MalformedSentinel (unpaired end)
  end_match, wrong name       → raise _MalformedSentinel (mismatched)
  end_match, correct name     → store content, clear open_block
  both on one line, same name → store "" (empty block)
  both on one line, diff names → raise _MalformedSentinel
  end of body, open_block set → raise _MalformedSentinel (unclosed)
```

D-68 compliance: absent blocks are simply not in the returned dict — absence is intentional deletion, not an error.

## Policy Dispatcher Precedence Chain

`_resolve_field_policy(key, profile)` — 4-tier lookup (highest wins):

1. `profile.merge.preserve_fields` list → `"preserve"` (hard lock, no user override possible)
2. `profile.merge.field_policies[key]` → user-specified mode
3. `_DEFAULT_FIELD_POLICIES[key]` → built-in mode
4. Unknown key → `"preserve"` (conservative default)

`_apply_field_policy(key, current, new, mode)`:
- `replace` → return `new` (None = field removal)
- `preserve` → return `current` (None = stay missing)
- `union` → current items first + new items not already present (stable order, deduped); non-list current falls back to replace semantics

## Task Commits

1. **RED (all 3 tasks):** `da5050a` — `test(04-03): add failing tests for merge.py primitives (all 3 tasks RED)` — 46 failing tests
2. **GREEN (all 3 tasks):** `42304a2` — `feat(04-03): create merge.py with dataclasses + _DEFAULT_FIELD_POLICIES (Task 1 GREEN)` — complete merge.py, 46 passing

_Note: Tasks 2 and 3 code was appended to merge.py in the same write as Task 1 (the plan's action blocks all say "append to merge.py"). The GREEN commit captures the complete file. TDD RED/GREEN boundary is maintained via the separate RED commit._

## Files Created

- `graphify/merge.py` (388 lines) — complete primitive layer
- `tests/test_merge.py` (313 lines) — 46 unit tests

## Decisions Made

- **Hand-rolled reader rejects bare `:` rhs values.** `_dump_frontmatter` calls `safe_frontmatter_value` which quotes any string containing `:`, so a bare `:` in rhs position is definitionally not graphify-emitted. `_parse_frontmatter` returns `None` for this case.
- **_MalformedSentinel is an exception, not a return sentinel.** The caller pattern `try: blocks = _parse_sentinel_blocks(body) except _MalformedSentinel` is cleaner than checking a sentinel return value, and prevents accidental swallowing of the error signal in Plan 04's control flow.
- **Combined RED commit for all 3 tasks.** All 46 tests are self-consistent (same test file, all import from the same not-yet-existing module). Splitting RED across 3 commits would leave the test file in artificially partial states. GREEN is a single file write by design (plan action blocks all target merge.py).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Malformed frontmatter test: `"---\nbad: : : :\n---"` was parsed as valid**

- **Found during:** Task 2 GREEN verification
- **Issue:** `_FM_SCALAR_RE` captured `bad` as key and `: : :` as rhs value, which `_coerce_scalar` returned as a bare string — no error raised. Test expected `None`.
- **Fix:** Added a guard in `_parse_frontmatter`: if `rhs.strip()` starts with `:` and is not a quoted string, return `None`. Rationale: `_dump_frontmatter` always quotes values containing `:` via `safe_frontmatter_value`, so a bare `:` in rhs position is definitionally malformed on the read path.
- **Files modified:** `graphify/merge.py` (6-line guard inside `_parse_frontmatter`)
- **Commit:** included in `42304a2`

## Known Stubs

None — no UI rendering, no data flows through empty placeholders. The module is purely algorithmic.

## Threat Model Coverage

Mitigated during this plan:

- **T-04-08 (Tampering — YAML tag injection):** No YAML loader. `!!python/object/apply:...` tags fall through to the string branch of `_coerce_scalar`. Test `test_parse_frontmatter_rejects_yaml_tags_as_literal` asserts round-trip identity.
- **T-04-10 (Tampering — nested sentinels):** `_parse_sentinel_blocks` raises `_MalformedSentinel` on duplicate/nested blocks. Tested in `test_parse_sentinel_blocks_nested_same_name_raises_malformed`.
- **T-04-11 (Information Disclosure — None vs {}):** Return contract documented, None/empty/{} are distinguishable. Plan 04 handles all three branches.

Accepted (documented):

- **T-04-09 (Tampering — sentinel-lookalike user prose):** documented in `_MalformedSentinel` docstring. Plan 04's dual-signal check is the defense layer.
- **T-04-12 (Elevation of Privilege — user freezes graphify_managed):** user-local config == CLI-flag trust level. Documented in `_resolve_field_policy` docstring.
- **T-04-13 (Tampering — wikilinks in union list):** strings are opaque; `safe_frontmatter_value` at emission is the defense. No new attack surface.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. `merge.py` is purely in-memory computation; file I/O is deferred to Plans 04 and 05.

## Next Phase / Plan Readiness

- **Plan 04-04 (compute_merge_plan):** Can now import and compose all primitives. Needs to add file-read I/O and the orchestration logic that calls `_parse_frontmatter`, `_parse_sentinel_blocks`, `_resolve_field_policy`, `_apply_field_policy` in sequence.
- **Plan 04-05 (apply_merge_plan):** Consumes `MergePlan` from Plan 04; `MergeResult` shape is locked.
- **Phase 5 (Integration):** `MergePlan` is JSON-serializable via `dataclasses.asdict` — `--dry-run` can print it directly.

## Self-Check: PASSED
