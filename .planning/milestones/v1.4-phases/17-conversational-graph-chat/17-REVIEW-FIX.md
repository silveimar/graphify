---
phase: 17-conversational-graph-chat
fixed_at: 2026-04-22T17:05:00Z
review_path: .planning/phases/17-conversational-graph-chat/17-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 17: Code Review Fix Report

**Fixed at:** 2026-04-22T17:05:00Z
**Source review:** .planning/phases/17-conversational-graph-chat/17-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (all Warnings; Info findings out of scope for this run)
- Fixed: 4
- Skipped: 0

All in-scope findings were fixed, verified against the full `tests/test_serve.py`
suite (188 passed), and committed atomically. Info-severity findings (IN-01
through IN-05) were intentionally out of scope per `fix_scope: critical_warning`.

## Fixed Issues

### WR-01: TTL eviction uses wall clock; jumps backwards silently evict healthy sessions

**Files modified:** `graphify/serve.py`, `tests/test_serve.py`
**Commit:** 163bbe0
**Applied fix:** Replaced `now = time.time()` with `now = time.monotonic()` in
`_run_chat_core` so TTL eviction and session-turn `ts` stamps use a monotonic
clock immune to NTP slew / suspend-resume wall-clock jumps. Updated
`test_chat_ttl_eviction` seed-timestamp to use `time.monotonic() - 2000` for
symmetry; the rest of the test is unchanged. Full `tests/test_serve.py` suite
passes (188 tests).

### WR-02: `_truncate_to_token_cap` can mid-sentence-truncate even when sentence-split would work

**Files modified:** `graphify/serve.py`
**Commit:** 41baa0d
**Applied fix:** When the `out == []` fallback triggers (first sentence alone
exceeds char_cap), replaced the raw character slice with a word-boundary
`rsplit(" ", 1)[0]` on the first sentence, stripped trailing punctuation, and
appended the ellipsis. Updated the docstring to mention the word-boundary
fallback. All 14 cap/token-related tests pass.

### WR-03: `_resolved_aliases` keyed by canonical can double-resolve when canonical is itself a key in alias_map

**Files modified:** `graphify/serve.py`
**Commit:** 4ec0d2c
**Applied fix:** Rewrote `_resolve_alias` inside `_run_chat_core` to walk the
alias map transitively with a `seen` set as a cycle guard, terminating on
self-reference, cycle, or missing key. This defensively handles
`dedup_report.json` entries that may not be transitively closed (e.g. chained
pairs from concatenated dedup runs). The `_resolved_aliases` attribution still
records the original input id under the final canonical. Full serve test suite
passes (188 tests).

### WR-04: Citations list can contain nodes absent from `G.nodes`; validator silently ignores them

**Files modified:** `graphify/serve.py`
**Commit:** 3613b76
**Applied fix:** Replaced the list-comprehension citation builder (which fell
through to synthetic `label=nid`, `source_file=""` entries when the resolved
canonical was missing from `G.nodes`) with an explicit loop that skips
unresolved canonicals. If the filtered citation list is empty while `status`
is still `"ok"`, status is downgraded to `"no_results"` so the `/graphify-ask`
fuzzy-fallback template renders instead of emitting a broken citation
envelope. Label/source_file lookups now always use the post-resolution
canonical id. Full serve test suite passes (188 tests).

---

_Fixed: 2026-04-22T17:05:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
