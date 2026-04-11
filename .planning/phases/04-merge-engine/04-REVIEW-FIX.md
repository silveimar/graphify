---
phase: 04-merge-engine
fixed_at: 2026-04-11T00:00:00Z
review_path: .planning/phases/04-merge-engine/04-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-04-11T00:00:00Z
**Source review:** .planning/phases/04-merge-engine/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR: 0, WR: 4)
- Fixed: 4
- Skipped: 0

Info-severity findings (IN-01..IN-06) were out of scope for this
iteration (`fix_scope: critical_warning`) and are not addressed here.

All fixes verified by `pytest tests/test_merge.py -q` after each commit
(85 → 87 → 89 → 91 → 95 passing tests). Broader regression check across
`tests/test_merge.py tests/test_profile.py tests/test_templates.py`
passes 349/349 after the final commit.

## Fixed Issues

### WR-01: `_merge_body_blocks` silently fails when sentinel lines carry prefix/suffix text

**Files modified:** `graphify/merge.py`, `tests/test_merge.py`
**Commit:** `5dcfb8f`
**Applied fix:** Replaced the literal-string `result.replace(old, replacement, 1)`
approach in `_merge_body_blocks` with line-index-based splicing. Added a
new private helper `_locate_sentinel_block_ranges` that walks the body
once and returns `{block_name: (start_line_idx, end_line_idx)}` using
the same `_SENTINEL_START_RE` / `_SENTINEL_END_RE` that
`_parse_sentinel_blocks` already uses, guaranteeing parser/rewriter
symmetry. `_merge_body_blocks` now rebuilds the body line-by-line,
preserving the user's original marker-line formatting verbatim while
swapping the content between them. If a block that `_parse_sentinel_blocks`
accepted has no locatable line range (defensive fail-loud invariant),
`_MalformedSentinel` is raised instead of silently reporting a fake
refresh. Added two regression tests:
`test_merge_body_blocks_handles_marker_inner_whitespace` pins the
previously-broken case where `<!--  graphify:wayfinder:start  -->`
(extra inner whitespace accepted by the regex) now rewrites correctly,
and `test_merge_body_blocks_reports_nothing_when_content_identical`
sanity-checks the identical-body fast path.

### WR-02: `_insert_with_canonical_neighbor` docstring/implementation mismatch on empty-neighbor fallback

**Files modified:** `graphify/merge.py`, `tests/test_merge.py`
**Commit:** `824937f`
**Applied fix:** Per the guidance note, the prepend behavior when no
preceding canonical neighbor is found is intentional — canonical keys
belong at the front. Updated two docstrings to match:
(1) `_merge_frontmatter`'s D-66 ordering comment now explicitly states
that canonical-key prepending happens when no preceding canonical
neighbor exists in `existing`, and that non-canonical new-only keys are
appended at end. (2) `_insert_with_canonical_neighbor` gained a
three-case docstring spelling out the non-canonical append, the
neighbor-found insert, and the no-preceding-neighbor prepend branches
with a concrete example (`{"rank": 5}` + new `source_file` →
`{"source_file": ..., "rank": 5}`). Added two regression tests:
`test_insert_canonical_key_prepended_when_no_preceding_neighbor` pins
the prepend branch (previously only the neighbor-found branch was
covered), and `test_insert_non_canonical_key_appended_at_end` pins the
non-canonical append branch.

### WR-03: `_validate_target` trusts `relative_to` without resolving absolute candidates

**Files modified:** `graphify/merge.py`, `tests/test_merge.py`
**Commit:** `3bfe084`
**Applied fix:** In `_validate_target`, when `candidate.is_absolute()`,
the function now calls `.resolve()` on BOTH `vault_dir` and `candidate`
before invoking `Path.relative_to`. If the resolved candidate escapes
the resolved vault, a `ValueError` is raised with a clear message
mentioning the original (unresolved) candidate for caller logging.
Relative candidates skip the resolve dance since they're rooted off
`vault_dir` by `validate_vault_path` downstream. Added two regression
tests: `test_validate_target_handles_symlinked_tmpdir` creates a real
vault dir and a sibling symlink pointing at it, then asserts that
`_validate_target` works in both directions (symlink vault + real
candidate, and real vault + symlink candidate) — this pins the macOS
`/tmp` ↔ `/private/tmp` parity case. `test_validate_target_rejects_absolute_path_outside_vault`
pins the companion invariant that a genuinely-escaping absolute path
still raises ValueError after resolution.

### WR-04: `_parse_frontmatter` float regex is too narrow — loses precision on user-hand-edited scalars

**Files modified:** `graphify/merge.py`, `tests/test_merge.py`
**Commit:** `5b5f20e`
**Applied fix:** Broadened `_FM_FLOAT_RE` from `^-?\d+\.\d{2}$` (exactly
two decimals) to `^-?\d+\.\d+$` (any decimal precision). The int check
in `_coerce_scalar` runs before the float check, so integers are still
caught first. Added a comment explaining the rationale (user-edited
files emit arbitrary precision; graphify-authored files always emit
`{:.2f}`, but the reader must round-trip either). Added four regression
tests: `test_parse_frontmatter_user_edited_float_one_decimal` pins
`cohesion: 0.5` → `float(0.5)` (was previously the bare string `"0.5"`);
`test_parse_frontmatter_user_edited_float_three_decimals` pins
`cohesion: 0.123` → `float(0.123)` (the exact example from the review);
`test_parse_frontmatter_user_edited_float_merge_is_idempotent` pins the
end-to-end idempotency invariant — a user-edited `0.5` value merged
against a new render of `0.5` reports `changed == []` (previously would
report `cohesion` as changed on every run); and
`test_parse_frontmatter_negative_float_one_decimal` pins the
negative-float path.

---

_Fixed: 2026-04-11T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
