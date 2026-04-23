---
phase: 19
plan: 02
subsystem: vault-promote
tags: [vault-promote, classification, render, taxonomy, tdd]
dependency_graph:
  requires:
    - graphify.analyze.knowledge_gaps
    - graphify.profile._dump_frontmatter
    - graphify.profile._DEFAULT_PROFILE
    - graphify/builtin_templates/*.md
  provides:
    - graphify.vault_promote.load_graph_and_communities
    - graphify.vault_promote.classify_nodes
    - graphify.vault_promote.render_note
    - graphify.vault_promote._detect_tech_tags
    - graphify.vault_promote.resolve_taxonomy
    - graphify.vault_promote._build_frontmatter_fields
  affects:
    - tests/test_vault_promote.py
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN for all new functions
    - importlib.resources for builtin template loading
    - string.Template.safe_substitute for no-injection rendering
    - 3-layer deep_merge for taxonomy resolution
    - claimed-set priority dispatch for 7-folder classification
key_files:
  created:
    - graphify/vault_promote.py
  modified:
    - tests/test_vault_promote.py
key_decisions:
  - "safe_tag() is applied only to suffix segments, not full 'ns/tag' strings — namespace slash preserved as literal"
  - "Questions are additive (not blocked by claimed set) — D-09 honored"
  - "Maps and Sources are structure-backed (not node-backed) — no claimed-set interaction"
  - "_build_frontmatter_fields_for_source left as separate helper for Plan 03 to use for source-only records"
requirements-completed: [VAULT-02, VAULT-03, VAULT-04, VAULT-07]
metrics:
  duration: 6 min
  completed: 2026-04-23
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 19 Plan 02: Core vault_promote.py Pipeline Summary

**One-liner:** Implemented pure in-memory `vault_promote.py` with 7-folder classifier (claimed-set priority dispatch, Questions bypass, code filter), full Ideaverse frontmatter renderer with EXTRACTED-only `related:`, and 3-layer taxonomy merge with auto-detected tech tags — 611 lines, 9 tests green, 1458 total suite passing.

---

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 2.1 RED | Failing tests for classify_nodes + render pipeline | 196d42b | tests/test_vault_promote.py |
| 2.1+2.2 GREEN | vault_promote.py — graph loader, classifier, renderer | 24bbe99 | graphify/vault_promote.py |

---

## Verification Results

- `pytest tests/test_vault_promote.py -q` — 9 passed, 6 skipped (write-phase)
- `pytest tests/ -q` — 1458 passed, 6 skipped, 2 warnings — no regressions
- `python -c "from graphify.vault_promote import classify_nodes, load_graph_and_communities; print('OK')"` → OK
- `python -c "from graphify.vault_promote import render_note, resolve_taxonomy, _detect_tech_tags; print('OK')"` → OK
- `grep -nE "^def (load_graph_and_communities|classify_nodes)" graphify/vault_promote.py` → 2 matches
- `grep -c "def _is_person\|def _has_quote_marks\|def _has_defines_edge" graphify/vault_promote.py` → 3
- `grep -nE "^def (render_note|_build_frontmatter_fields|_detect_tech_tags|resolve_taxonomy|_extracted_neighbors|_pick_baseline_tags)" graphify/vault_promote.py` → 6 matches
- `wc -l graphify/vault_promote.py` → 611 lines (≥ 350 required)
- `grep -q 'stateMaps' graphify/vault_promote.py` → PASS
- `grep -q '🟥' graphify/vault_promote.py` → PASS
- `grep -q "EXTRACTED" graphify/vault_promote.py` → PASS

---

## Acceptance Criteria Results

| Criterion | Status |
|-----------|--------|
| `load_graph_and_communities` + `classify_nodes` both present | PASS |
| 3 heuristic helpers (`_is_person`, `_has_quote_marks`, `_has_defines_edge`) | PASS |
| Module importable (classify_nodes, load_graph_and_communities) | PASS |
| 3 dispatch tests green (no skips) | PASS |
| Code-typed god_node absent from `things` bucket | PASS |
| `questions` non-empty at threshold=999 with isolated node | PASS |
| 6 render functions at module level | PASS |
| `stateMaps` and `🟥` literals present | PASS |
| `"EXTRACTED"` confidence filter explicit | PASS |
| render_note + resolve_taxonomy + _detect_tech_tags importable | PASS |
| 5 render tests green | PASS |
| Leftover-token guard: `"${" not in rendered` | PASS |
| Line count ≥ 350 | PASS (611) |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] safe_tag() converts full "garden/plant" string to "garden-plant"**
- **Found during:** Task 2.2 GREEN — `test_vault02_frontmatter_tags_namespaces` failed because `safe_tag("garden/plant")` slugifies the `/` to `-`
- **Issue:** Existing code pattern (templates.py line 631) emits tags as `f"community/{safe_tag(suffix)}"` — the namespace prefix is a literal string, only the suffix goes through `safe_tag`. My initial `_pick_baseline_tags` passed full `"ns/suffix"` strings.
- **Fix:** Changed all `safe_tag("garden/plant")` calls to `"garden/" + safe_tag("plant")` pattern throughout `_pick_baseline_tags` and tech-tag emission
- **Files modified:** graphify/vault_promote.py
- **Commit:** 24bbe99 (inline fix before GREEN commit; no separate commit needed — single implementation commit)

**Total deviations:** 1 auto-fixed (Rule 1 — bug in tag emission). **Impact:** Minimal — caught and fixed during GREEN phase before commit.

---

## Known Stubs

None — all functions are fully implemented. Write-phase tests (6) remain `@pytest.mark.skip` as intended; Plan 03 will implement them.

---

## Threat Surface Scan

No new network endpoints, auth paths, or file I/O introduced. This plan is pure in-memory — all inputs are graph-in-memory (already loaded by `load_graph_and_communities`). Security mitigations per threat register:

- T-19-02-01: YAML injection → all values through `safe_frontmatter_value` in `_dump_frontmatter` ✓
- T-19-02-02: Wikilink injection → stems produced via `safe_filename` ✓
- T-19-02-03: Tech-tag injection → extension lookup is closed map + `safe_tag` applied ✓
- T-19-02-04: INFERRED edge in `related:` → hard filter `d.get("confidence") == "EXTRACTED"` in `_extracted_neighbors` ✓
- T-19-02-05: Template placeholder injection → `string.Template.safe_substitute` used ✓
- T-19-02-06: OOM on huge graph → linear traversal, one note at a time ✓

---

## Self-Check: PASSED

- [x] `graphify/vault_promote.py` exists with 611 lines
- [x] `tests/test_vault_promote.py` updated: 9 active tests, 6 skipped
- [x] Commit 196d42b (RED tests) — present in git log
- [x] Commit 24bbe99 (GREEN implementation) — present in git log
- [x] Full suite: 1458 passed, 6 skipped
- [x] `from graphify.vault_promote import classify_nodes, load_graph_and_communities, render_note, resolve_taxonomy, _detect_tech_tags` — all import cleanly

---

## Next

Ready for Plan 19-03 (vault writes — I/O to vault directory, CLI integration).
