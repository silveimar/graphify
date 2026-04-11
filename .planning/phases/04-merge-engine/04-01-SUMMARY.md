---
phase: 04-merge-engine
plan: 01
subsystem: templates
tags: [templates, sentinels, body-refresh, phase-4]

# Dependency graph
requires:
  - phase: 02-template-engine
    provides: "Six section builders (_build_wayfinder_callout, _build_connections_callout, _build_metadata_callout, _build_members_section, _build_sub_communities_callout, _build_dataview_block) returning empty-string when their inputs are empty (D-18)"
provides:
  - "_SENTINEL_START_FMT and _SENTINEL_END_FMT module constants in graphify/templates.py"
  - "_wrap_sentinel(name, content) helper that short-circuits on empty content"
  - "Paired HTML-comment sentinels around every graphify-owned section: wayfinder, connections, metadata, members, sub_communities, dataview"
  - "Sentinel grammar regex _collect_sentinels(text) helper colocated in tests/test_templates.py"
affects:
  - 04-03-merge-primitives  # merge.py sentinel parser consumes real sentinel output from templates
  - 04-04-compute-merge-plan # compute_merge_plan detects graphify-owned body regions via sentinels
  - 04-05-apply-merge-plan   # body-block round-trip (D-67/D-68) refreshes content between sentinels
  - D-62 fingerprint match   # unblocks fingerprint detection tied to sentinel-wrapped body regions

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level format-string constants with {name} placeholder — single source of truth for sentinel grammar"
    - "Short-circuit helper: empty content in → empty content out, preserving D-18 conditional omission"
    - "Test helper _collect_sentinels using re.compile for symmetric start/end token collection"

key-files:
  created: []
  modified:
    - graphify/templates.py
    - tests/test_templates.py

key-decisions:
  - "Sentinel grammar is <!-- graphify:{name}:start --> / <!-- graphify:{name}:end --> — HTML comment so Obsidian renders it as whitespace"
  - "Empty section content short-circuits inside _wrap_sentinel, so missing connections/members blocks emit no sentinel at all (preserves D-18)"
  - "_wrap_sentinel is private (leading underscore) and not exported — merge.py uses its own parser keyed off the same grammar constants"
  - "Updated 8 existing tests that asserted exact equality or .startswith on raw section output; each now asserts both the sentinel markers AND the inner body content. No assertions weakened."

commits:
  - "40f2083 feat(04-01): wrap template section builders in D-67 sentinel markers"
  - "d242127 test(04-01): add D-67 sentinel round-trip assertions for template renders"

tests-added:
  - "test_render_note_emits_matched_wayfinder_sentinels"
  - "test_render_note_emits_matched_connections_sentinels"
  - "test_render_note_omits_connections_sentinel_when_no_edges"
  - "test_render_note_emits_matched_metadata_sentinels"
  - "test_render_moc_emits_all_moc_sentinels"
  - "test_render_moc_omits_members_sentinel_when_empty"
  - "test_render_moc_omits_sub_communities_sentinel_when_empty"
  - "test_sentinel_start_end_are_paired_in_render_output"
  - "test_sentinel_pairing_survives_adversarial_connections_label  # T-04-01 regression guard"

test-results:
  - "tests/test_templates.py: 152 passed (143 baseline + 9 new sentinel assertions)"
  - "tests/test_templates.py -k sentinel: 9 passed"

deviations:
  - "Rule 1 auto-fix: Task 1 altered section-builder return shape by design, so 8 existing tests with exact-equality assertions on raw output were updated in the same commit to match the sentinel-wrapped contract. Inner-body content assertions preserved; no assertions weakened."
  - "Task 2 commit (d242127) and this SUMMARY.md were finalized by the orchestrator after the executor hit a sandbox permission denial on write-side tools. All tests were passing on disk at the time of handoff; the orchestrator committed the pending work unchanged and verified pytest."

requirements-addressed:
  - "MRG-01: wrap all graphify-owned body regions in sentinel markers so merge.py can detect and refresh them in-place on re-run"
  - "T-04-01: adversarial node labels containing sentinel-lookalike substrings cannot break sentinel pairing"
---

## Overview

Back-patched `graphify/templates.py` to wrap every section builder's output in paired HTML-comment sentinel markers (`<!-- graphify:{name}:start -->` / `<!-- graphify:{name}:end -->`). This unblocks Phase 4 merge: the sentinel parser in Plan 04-03 (`merge.py`) now has real sentinel output to test against, and the body-block round-trip decisions in D-67/D-68 become mechanically feasible.

## What Was Built

**Task 1 (commit 40f2083) — Wrap section builders:**
- Added `_SENTINEL_START_FMT = "<!-- graphify:{name}:start -->"` and `_SENTINEL_END_FMT = "<!-- graphify:{name}:end -->"` as module-level constants in `graphify/templates.py`.
- Added `_wrap_sentinel(name, content) -> str` helper. Empty `content` short-circuits to `""` to preserve D-18 (sections with no content emit nothing, not an empty sentinel pair).
- Wrapped all six graphify-owned section builders: `_build_wayfinder_callout` (`wayfinder`), `_build_connections_callout` (`connections`), `_build_metadata_callout` (`metadata`), `_build_members_section` (`members`), `_build_sub_communities_callout` (`sub_communities`), `_build_dataview_block` (`dataview`).
- Rewrote 8 existing tests that had exact-equality/startswith assertions on raw builder output so they assert both sentinel markers and inner body content.

**Task 2 (commit d242127) — Round-trip tests:**
- 9 new end-to-end render tests exercising the sentinel pairing invariants across `render_note` and `render_moc`, including:
  - All positive-pairing cases for the six sections
  - Omission cases (empty connections, empty members, empty sub_communities)
  - A global pairing-equality assertion that counts start and end sentinels across full render output
  - T-04-01 regression: an adversarial node label containing `<!-- graphify:connections:end -->` does not terminate the connections block early (label escape preserves pairing)
- Shared helper `_collect_sentinels(text) -> (starts, ends)` using `re.compile(r"<!-- graphify:(\w+):start -->")` / `end`, colocated at the top of the sentinel test group.

## Deferred

- Pre-existing test failures on baseline (`tests/test_detect.py::test_detect_skips_dotfiles`, `tests/test_extract.py::test_collect_files_from_dir`) — reproducible on `418883e` before any 04-01 changes. Logged to `.planning/phases/04-merge-engine/deferred-items.md` by Plan 04-02. Out of scope for this plan.

## Self-Check

- [x] Task 1 committed with passing tests (40f2083)
- [x] Task 2 committed with passing tests (d242127)
- [x] 152/152 tests passing in `tests/test_templates.py`
- [x] Sentinel grammar documented in plan + summary for merge.py consumers
- [x] T-04-01 adversarial-label regression guarded
- [x] No regressions in unrelated test files (the two deferred failures reproduce on baseline)
