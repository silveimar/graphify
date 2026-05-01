---
phase: 54-mcp-trace-obsidian-parity
plan: 5
subsystem: docs/manifest/verification
tags: [docs, manifest, verification, close-out, cgraph-03, cgraph-04]
requires: [54-02, 54-03, 54-04]
provides:
  - "docs/RELATIONS.md §'MCP traversal' (Phase 54)"
  - ".planning/phases/54-mcp-trace-obsidian-parity/54-VERIFICATION.md (CGRAPH-03/04 mapping tables)"
  - "A1 carve-out resolution (ADOPTED, with Plan 04 dev. #4 honest note)"
  - "Phase 54 close-out gate (1995 passed, 1 xfailed, 0 failed)"
affects:
  - docs/RELATIONS.md
  - server.json
  - .planning/phases/54-mcp-trace-obsidian-parity/54-VERIFICATION.md
key-files:
  created:
    - .planning/phases/54-mcp-trace-obsidian-parity/54-VERIFICATION.md
  modified:
    - docs/RELATIONS.md
decisions:
  - "A1 carve-out (moc.md \\${body} slot) ADOPTED — additive edit, not a NEW template (D-54.10 intent preserved)"
  - "Plan 04 dev. #4 honestly documented in VERIFICATION.md: inverse sections render on rationale notes, NOT on community MOCs (preserves 1:1 count parity per D-54.12)"
  - "server.json regen via sync_mcp_server_json.py is a no-op when manifest schemas are already in sync (Plans 02/03 triggered prior regen)"
  - "Plan 05 acceptance criteria for grep-in-server.json deviated from reality: server.json is the slim hash-only form; tool schemas live in capability.py and are bound via manifest_content_hash"
metrics:
  duration: "~25min"
  tasks: 3
  completed: "2026-05-01"
---

# Phase 54 Plan 05: Wave 5 close-out — RELATIONS.md, server.json, VERIFICATION.md

CGRAPH-03 and CGRAPH-04 documented and verified. Phase 54 ready to close.

## What was added to docs/RELATIONS.md

New top-level `## MCP traversal (Phase 54)` section appended (121 net inserts) covering:

- `concept_code_hops` parameters (incl. NEW `relations: list[string]` default `["implements"]`, allowed values, error semantics).
- Payload meta keys: `relations` (sorted echo), `traversal_steps`, `steps_by_relation`, `reachable_node_ids`, `depth_by_id`, `truncated`, plus the conditional `implements_traversal_steps` shim (set-equality on `relations == ["implements"]`).
- `entity_trace.include_concept_code` (default `false`, byte-identical to Phase 11; `true` adds `concept_code_reachable` + `concept_code_steps_by_relation`).
- `_IMPL_EDGE_BUDGET = 500` global cap and truncation semantics.
- Backward-compat table for Phase 47 + Phase 11 callers.
- Three example invocations (default, widened-relations, entity_trace merge).
- Implementation references (file:line callouts to serve.py / mcp_tool_registry.py).

Existing RELATIONS.md sections untouched (`git diff` shows additive only — zero `-` lines).

## VERIFICATION.md mapping table summary

`.planning/phases/54-mcp-trace-obsidian-parity/54-VERIFICATION.md` (147 lines) contains:

- **CGRAPH-03 mapping table** (10 rows) — sub-requirement → MCP tool/parameter → `serve.py` / `mcp_tool_registry.py` source line → test name. Tests: 6 from `test_concept_code_mcp.py`, 2 from `test_serve.py`, 1 from `test_capability.py`.
- **CGRAPH-04 mapping table** (9 rows) — sub-requirement → vault location (`${body}` slot) → `templates.py` builder → test name. Tests: 7 from `test_concept_code_obsidian.py`.
- **A1 carve-out resolution** (ADOPTED) with honest Plan 04 dev. #4 note.
- **Plan 04 deviations summary** (4 rows: Rule 1×2, Rule 2, Rule 4 architectural).
- **Must-haves status** reconciled across Plans 01-05 (every truth `[x]`).
- **Full-suite gate**: `1995 passed, 1 xfailed, 0 failed`. Phase 53 baseline was 1979 passed, so +16 (matches Plan 01's 16 RED tests now GREEN).
- **server.json shape deviation** documented honestly (slim hash-only form vs Plan's grep criteria).
- **Outstanding/deferred**: PyPI version bump, `concept_code_layout` profile knob (CFG-01 / Phase 56), `/trace` slash widening (D-54.05).

## Plan 04 deviations honestly captured

| # | Rule | Issue | Fix | Commit |
|---|------|-------|-----|--------|
| 1 | Rule 1 | `_find_md_for_label` non-deterministic across filesystems | Two-pass H1-title preferred lookup | `90c9178` |
| 2 | Rule 1 | `test_backward_parity_wikilinks_to_edges` total off by 2× | `expected_total = 2 * edge_count` | `371c2ee` |
| 3 | Rule 2 | Connections callout double-rendered typed concept↔code edges | Filter 5 typed relations out of `_build_connections_callout` | `90c9178` |
| 4 | Rule 4 | Original plan emitted inverse sections on community MOC; broke deterministic H1 lookup AND inflated count parity | Route inverse sections to per-rationale notes via `render_note` rationale dispatch; keep `${body}` in moc.md for future use | `371c2ee` |

All four are listed in VERIFICATION.md §"Plan 04 Deviations Summary" — no paper-over.

## Final pytest stats

```
$ pytest tests/ -q
1995 passed, 1 xfailed, 8 warnings in 69.63s
```

| Metric | Phase 53 baseline | Phase 54 close | Delta |
|--------|-------------------|----------------|-------|
| passed | 1979 | 1995 | **+16** |
| xfailed | 1 | 1 | 0 |
| failed | 0 | 0 | 0 |

`tests/test_capability.py`: 26 passed (manifest hash binding intact).

## server.json regen

`python scripts/sync_mcp_server_json.py` was run (Task 2) — exit 0, hash unchanged at `ac31ce60c04bee38…` because Plans 02/03 already triggered regen during their schema edits. The slim form (`name`, `version`, `packages`, `_meta.manifest_content_hash`, `_meta.tool_count: 27`) is the actual on-disk shape; tool schemas live in `graphify/capability.py::build_manifest_dict()` and are bound via the hash. The `tests/test_capability.py` 26-test suite (all green) provides the schema-drift guarantee.

This is documented as a deviation from Plan 05's grep-in-server.json acceptance criteria.

## Files changed

| File | Change |
|------|--------|
| `docs/RELATIONS.md` | +121 lines: new `## MCP traversal (Phase 54)` section. Existing content untouched. |
| `.planning/phases/54-mcp-trace-obsidian-parity/54-VERIFICATION.md` | NEW (147 lines): CGRAPH-03/04 mapping + A1 ADOPTED + Plan 04 dev. summary + full-suite gate |
| `server.json` | unchanged (sync produced no diff — manifest hash already in sync from Plans 02/03) |

## Commits

| Commit | Subject |
|--------|---------|
| `1f6d22b` | docs(54-05): add MCP traversal section to docs/RELATIONS.md |
| `b9a2e95` | docs(54-05): create 54-VERIFICATION.md (CGRAPH-03/04 mapping + A1 ADOPTED + 1995/0) |

(Task 2 produced no commit — `git status` showed no diff on server.json after the sync run.)

## Deviations from plan

### Rule 1 — Plan 05 acceptance criteria mismatch reality

**1. server.json grep criteria (Task 2)**
- **Found during:** Task 2 verification.
- **Issue:** Plan 05 expected `grep -c "concept_code_hops" server.json ≥ 1` and similar greps for `relations` / `include_concept_code` directly inside `server.json`. The actual on-disk `server.json` is the slim hash-only form (29 lines: `name`, `version`, `packages`, `_meta`); tool schemas live in `graphify/capability.py::build_manifest_dict()` and are bound to the manifest via `_meta.manifest_content_hash`. The `scripts/sync_mcp_server_json.py` script writes only version + hash + tool_count.
- **Fix:** Ran `python scripts/sync_mcp_server_json.py` (exit 0, no-op since Plans 02/03 already triggered regen). Confirmed `pytest tests/test_capability.py -x` green (26 tests, hash binding verified). Documented the deviation in VERIFICATION.md §"server.json regeneration note" and in this Summary.
- **Why this is correct:** The hash binding (`tests/test_capability.py` 26 tests, all green) provides the equivalent guarantee — schema drift flips the hash. This is the codebase's actual MCP capability invariant; the Plan author appears to have misremembered the on-disk shape.

### No other deviations

Tasks 1 and 3 met all acceptance criteria as specified.

## Self-Check: PASSED

- `docs/RELATIONS.md` `## MCP traversal` section — FOUND (`grep -c "^## MCP traversal" docs/RELATIONS.md` = 1)
- `.planning/phases/54-mcp-trace-obsidian-parity/54-VERIFICATION.md` — FOUND (147 lines)
- `server.json` `_meta.manifest_content_hash` — present and stable (sync exit 0; capability tests 26/26 green)
- Commit `1f6d22b` (RELATIONS.md) — FOUND in `git log`
- Commit `b9a2e95` (VERIFICATION.md) — FOUND in `git log`
- Full pytest suite: 1995 passed, 1 xfailed, 0 failed — verified
- Acceptance criteria for Tasks 1 + 3: all greps ≥ required threshold (Task 1: 1/6/5/5/3/3 vs ≥1/≥2/≥1/≥1/≥1/≥1; Task 3: file exists/1/1/5/5/24 vs ≥1/1/1/≥1/≥1/≥8)
- Phase 53 baseline preserved (1979 → 1995, monotonic increase)

## EXECUTION COMPLETE
