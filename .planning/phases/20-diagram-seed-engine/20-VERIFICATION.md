---
phase: 20-diagram-seed-engine
verified: 2026-04-23T13:25:00Z
status: gaps_found
score: 10/11 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "Agent calls list_diagram_seeds, picks a seed_id from the response, and successfully fetches the full SeedDict via get_diagram_seed(seed_id) — the documented v1.5 consumer round-trip (ROADMAP Success Criterion #5, SEED-10)."
    status: partial
    reason: "For auto-detected seeds that pass dedup-merge (SEED-05), list_diagram_seeds returns seed_id='merged-<sha12>' (pulled from the SeedDict body), but get_diagram_seed looks up the file as '{seed_id}-seed.json' — and seed.py writes files as '{main_node_id}-seed.json'. Consequence: the documented list→get round-trip succeeds only for singleton seeds; for merged seeds it always returns status=not_found. End-to-end integration run reproduces the failure: list returned seed_id 'merged-6a5d18d32535', get('merged-6a5d18d32535') returned not_found even though the file 'hub-seed.json' exists on disk."
    artifacts:
      - path: "graphify/seed.py"
        issue: "File naming uses main_node_id ('{_safe_filename_stem(seed['main_node_id'])}-seed.json', line 524) while the seed dict carries seed_id='merged-<sha12>' for merged seeds (line 371). The two identifiers diverge exactly when SEED-05 fires."
      - path: "graphify/serve.py"
        issue: "_run_list_diagram_seeds_core (line 2642) emits seed.get('seed_id') as the row's canonical id; _run_get_diagram_seed_core (line 2713) resolves 'seeds_dir / f\"{canonical_id}-seed.json\"'. For merged seeds the row id is not the file stem."
      - path: "tests/test_serve.py"
        issue: "_sample_seed / _manifest_entry fixtures always set seed_id == main_node_id == seed_file-stem, so no test exercises a merged seed's list→get round-trip. The 12 new tests pass despite the mismatch."
    missing:
      - "Either (a) write seeds as '{seed_id}-seed.json' so list and get share the same id, or (b) make list emit an id that matches the filename stem (main_node_id), or (c) persist a seed_id→seed_file mapping in the manifest and have get_diagram_seed read the manifest instead of deriving the path from seed_id."
      - "Add a regression test in tests/test_serve.py: create a dedup-merged seed on disk (seed_id='merged-abc', file='hub-seed.json'), call list to capture the returned id, call get with that id, assert status='ok'."
deferred: []
---

# Phase 20: Diagram Seed Engine — Verification Report

**Phase Goal:** graphify auto-detects diagram-worthy nodes from the analyzed graph and exposes structured seeds — both via the filesystem and as MCP tools — so agents can select and consume them in the Excalidraw pipeline.

**Verified:** 2026-04-23T13:25:00Z
**Status:** gaps_found (1 partial — list→get round-trip for merged seeds)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `graphify --diagram-seeds` populates `graphify-out/seeds/` with per-seed JSON + manifest; auto cap enforced before I/O | VERIFIED | End-to-end run wrote `hub-seed.json` + `seeds-manifest.json`; `_MAX_AUTO_SEEDS=20` enforced at `seed.py:460-461` before any write; `graphify/__main__.py:1379` wires `--diagram-seeds` |
| 2 | Seed JSON contains `main_nodes` (r=1), `supporting_nodes` (r=2\\r=1), `relations`, `suggested_layout_type`, `suggested_template`, `trigger` | VERIFIED | Integration dump of `hub-seed.json` shows exactly these 6 required keys plus seed_id/main_node_id/version_nonce_seed/dedup_merged_from |
| 3 | >60% overlap seeds union-merged single-pass degree-sorted; element IDs = `sha256(node_id)[:16]`; never label-derived | VERIFIED | `seed.py:33 _OVERLAP_THRESHOLD=0.60`; `seed.py:330 jaccard > _OVERLAP_THRESHOLD`; `seed.py:59` element_id uses `sha256(node_id.encode())[:16]`; tests C/I/J pass |
| 4 | `list_diagram_seeds` returns D-02 envelope with 5-field rows, alias-resolved | VERIFIED | Integration call returned tab-separated row + `---GRAPHIFY-META---` + JSON meta; 5 fields confirmed; `_resolve_alias` closure at `serve.py:2589-2597` |
| 5 | `get_diagram_seed(seed_id)` returns full SeedDict in D-02 envelope; unknown id returns error status without crashing | PARTIAL | Unknown id → `status=not_found` (verified); path traversal → `not_found` (verified); **BUT** the seed_id returned by `list_diagram_seeds` for dedup-merged seeds cannot be fetched via `get_diagram_seed` — file naming mismatch. See Gap #1. |
| 6 | Detection boundary D-18: `seed.py` only calls `god_nodes()` + `detect_user_seeds()` from `analyze.py`, never reimplements | VERIFIED | `grep "from graphify.analyze import" seed.py` → 1 hit; `grep "_find_surprises\|extract_god_nodes\|_parse_gen_diagram_seed" seed.py` → 0 hits |
| 7 | Tag write-back via `compute_merge_plan` only — no direct frontmatter writes | VERIFIED | `seed.py:558` lazy import of `compute_merge_plan` inside `vault is not None` branch; denylist test `test_tag_writeback_routed_only_through_compute_merge_plan` green |
| 8 | MANIFEST-05 atomic pair: registry + serve ship in one commit | VERIFIED | `git show --stat 1a924cc` touches both `graphify/mcp_tool_registry.py` and `graphify/serve.py` in the same commit |
| 9 | MANIFEST-06: `capability_tool_meta.yaml` has explicit entries for both new tools | VERIFIED | `capability_tool_meta.yaml:112 list_diagram_seeds` and `:117 get_diagram_seed` with `composable_from: [list_diagram_seeds]` |
| 10 | Atomic-write parity: tempfile + rename per seed; manifest written last; corrupt manifest tolerated | VERIFIED | `seed.py:73 _write_atomic`, `seed.py:114 _save_seeds_manifest`; `test_manifest_is_written_last`, `test_partial_write_failure_leaves_no_visible_state` pass |
| 11 | Full suite green — no regressions introduced by Phase 20 | VERIFIED | `pytest tests/ -q` → **1524 passed, 8 warnings in 40.55s** (matches claim in 20-03-SUMMARY) |

**Score:** 10/11 truths verified (1 partial).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/analyze.py` | `god_nodes()` + `_cross_community_surprises()` tag `possible_diagram_seed=True`; new `detect_user_seeds(G)` | VERIFIED | Line 91 / 387-388 / 687 present; 3 attribute assignments confirmed |
| `graphify/seed.py` | `build_seed`, `build_all_seeds`, 6-predicate layout heuristic, dedup, cap, atomic write, hashing | VERIFIED | 583 lines; all required defs present (`build_seed:217`, `build_all_seeds:401`, `_select_layout_type:139`, `_dedup_overlapping_seeds:295`, `_write_atomic:73`, `_save_seeds_manifest:114`, `_element_id:55`) |
| `graphify/__main__.py` | `--diagram-seeds` flag handler | VERIFIED | Handler at `:1379`; help at `:1184`; 6 occurrences |
| `graphify/mcp_tool_registry.py` | Tool declarations for `list_diagram_seeds` + `get_diagram_seed` | VERIFIED | Lines 349 (list) and 364 (get) with required `seed_id` arg on get |
| `graphify/serve.py` | 2 module-level cores + 2 wrappers + handler registration | VERIFIED | `_run_list_diagram_seeds_core:2562`, `_run_get_diagram_seed_core:2667`, `_tool_list_diagram_seeds:3316`, `_tool_get_diagram_seed:3323`, handlers at `:3353-3354` |
| `graphify/capability_tool_meta.yaml` | MANIFEST-06 entries for both tools | VERIFIED | Lines 112 + 117 |
| `tests/test_seed.py` | Unit tests covering atomic write, dedup, cap, heuristic, hashing | VERIFIED | 640 lines, 27 tests, all pass |
| `tests/test_serve.py` | 12 new MCP tool tests | VERIFIED | All 12 `test_*_diagram_seed*` tests pass |
| `tests/test_analyze.py` | Auto-tag tests + denylist | VERIFIED | 8 new tests, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `seed.py::build_all_seeds` | `analyze.py::god_nodes` + `detect_user_seeds` | top-level import | WIRED | `from graphify.analyze import god_nodes, detect_user_seeds` confirmed |
| `seed.py::build_all_seeds` (vault branch) | `merge.py::compute_merge_plan` | lazy import inside `if vault is not None` | WIRED | Integration-verified; denylist guard ensures no bypass path |
| `serve.py::_run_list_diagram_seeds_core` | `graphify-out/seeds/seeds-manifest.json` | read+parse | WIRED | Integration: manifest read, 1 row emitted for the sample graph |
| `serve.py::_run_get_diagram_seed_core` | `{seeds_dir}/{seed_id}-seed.json` | file read | PARTIAL | Works for singleton seeds; **fails for dedup-merged seeds** because file is named by `main_node_id` but request uses `seed_id='merged-<sha12>'` |
| `__main__.py --diagram-seeds` | `seed.py::build_all_seeds` | function call | WIRED | CLI entry at `:1379`; smoke test `test_cli_diagram_seeds_flag_smoke` passes |
| `mcp_tool_registry.py` | `serve.py::_handlers` | name-keyed dispatch | WIRED | MANIFEST-05 startup invariant: 24 registry tools == 24 handler keys |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `seeds-manifest.json` | manifest_entries | `build_all_seeds` writes per-candidate entry with `written_at` timestamp | Yes — 1 real entry from integration run | FLOWING |
| `{node_id}-seed.json` | `main_nodes`, `supporting_nodes`, `relations` | networkx `ego_graph(radius=1|2)` + subgraph edge iteration | Yes — 6 real nodes emitted from test graph | FLOWING |
| `list_diagram_seeds` text_body | tab rows | re-reads seed JSON files, emits `seed_id/main_node_label/layout/trigger/node_count` | Yes — but seed_id diverges from file stem for merged seeds (see gap) | FLOWING (with gap) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `pytest tests/ -q` | 1524 passed, 8 warnings, 40.55s | PASS |
| `--diagram-seeds` appears in help | `grep -c '--diagram-seeds' graphify/__main__.py` | 6 | PASS |
| `build_all_seeds` end-to-end run writes manifest + seed | `python -c "from graphify.seed import build_all_seeds; ..."` | summary dict + 1 seed + 1 manifest entry on disk | PASS |
| `list_diagram_seeds` round-trip | integration call → D-02 envelope | 1 row, `status=ok`, `seed_count=1` | PASS |
| `get_diagram_seed('hub')` for singleton | integration call with main_node_id | Full SeedDict + `status=ok` | PASS |
| `get_diagram_seed('merged-<sha12>')` using id from list | integration call with seed_id returned by list | `status=not_found` despite file existing on disk | **FAIL — Gap #1** |
| Path traversal rejected | `get_diagram_seed('../../etc/passwd')` | `status=not_found` without filesystem access | PASS |
| MANIFEST-05 atomic pair | `git show --stat 1a924cc` | Both `mcp_tool_registry.py` and `serve.py` in same commit | PASS |
| MANIFEST-06 meta entries | `grep -E "^(list|get)_diagram_seed" capability_tool_meta.yaml` | 2 entries present | PASS |

### Requirements Coverage (SEED-01..SEED-11)

| REQ-ID | Plan | Description | Status | Evidence |
|--------|------|-------------|--------|----------|
| SEED-01 | 20-02 | `--diagram-seeds` CLI triggers seed generation, writes to `graphify-out/seeds/` | PASS | `__main__.py:1379`; integration run wrote the files |
| SEED-02 | 20-01 | Auto-tag `possible_diagram_seed` + `detect_user_seeds(G)` reading `gen-diagram-seed[/type]` | PASS | `analyze.py:91,387-388,687`; 8 tests green |
| SEED-03 | 20-01 | Tag write-back only via `compute_merge_plan` with `tags:'union'`; direct writes forbidden | PASS | `seed.py:558` single lazy import; denylist test green; contract deferred-applied in v1.5 (plan computed, not applied — matches D-08 in 20-02 summary) |
| SEED-04 | 20-02 | `build_seed()` produces SeedDict with required keys; one file per seed | PASS | Schema verified via integration dump; `seed.py:217`; 4 schema tests green |
| SEED-05 | 20-02 | `build_all_seeds()` merges >60% overlap, degree-desc single pass, no recursive re-merge | PASS | `seed.py:295, 330`; 2 dedup tests green; integration merged 6 source ids into 1 seed |
| SEED-06 | 20-02 | auto seeds capped at 20 before file I/O; user seeds uncapped | PASS | `seed.py:460-461` cap happens before any write; `test_cap_enforced_before_file_io_and_warn_emitted` + `test_user_seeds_never_counted_toward_cap` green |
| SEED-07 | 20-02 | 6-predicate layout heuristic; `/type` hint overrides | PASS | `_select_layout_type:139`; 5 heuristic tests green; integration picked `glossary-graph` for concept graph |
| SEED-08 | 20-02 | element_id = `sha256(node_id)[:16]`; version_nonce = `int(sha256(node_id+x+y)[:8],16)`; label-derived forbidden | PASS | `seed.py:59,64`; 3 hashing tests green; element_id `ca978112ca1bbdca` confirmed in integration dump |
| SEED-09 | 20-03 | `list_diagram_seeds` returns per-seed summary via D-02 envelope; alias-threaded | PASS | Envelope format verified; 7 list tests green |
| SEED-10 | 20-03 | `get_diagram_seed(seed_id)` returns full SeedDict via D-02 envelope | PARTIAL | Works for singleton seeds. **Fails for merged seeds**: the seed_id returned by list cannot be used as the get argument because `{seed_id}-seed.json` path-derivation mismatches `{main_node_id}-seed.json` file naming. Tests don't cover this path. |
| SEED-11 | 20-03 | registry + serve extensions in same plan/commit (MANIFEST-05) | PASS | Commit `1a924cc` touches both; handler-set/registry-set equality invariant holds |

**Orphaned REQ-IDs check:** `grep -E "Phase 20" .planning/REQUIREMENTS.md` confirms only SEED-01..SEED-11 are assigned to Phase 20; no plan missed a REQ-ID. All 11 IDs are claimed by plans 20-01/02/03 as mapped in REQUIREMENTS.md lines 119-129.

### MANIFEST Invariants

| Invariant | Description | Status | Evidence |
|-----------|-------------|--------|----------|
| MANIFEST-05 | registry + serve extensions land atomically | PASS | `git show --stat 1a924cc` includes both files; startup invariant `{t.name for t in build_mcp_tools()} == set(_handlers.keys())` holds (24 == 24) |
| MANIFEST-06 | `capability_tool_meta.yaml` has explicit entries for every registered tool | PASS | Both new tools present at YAML lines 112/117 with `cost_class: cheap`, `deterministic: true`, `cacheable_until: graph_mtime`; composability declared on `get_diagram_seed` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `graphify/serve.py` | 2713 | `seeds_dir / f"{canonical_id}-seed.json"` derives file path from `seed_id`, but seed files are named by `main_node_id` | Blocker | Breaks list→get round-trip for merged seeds — documented in Gap #1 |
| — | — | No TODO / FIXME / placeholder markers found in phase artifacts | Info | — |
| — | — | No empty `return []` / `return {}` in production code for this phase | Info | — |

### Human Verification Required

None. All verification steps are automatable and were executed.

### Gaps Summary

Phase 20 delivers the diagram-seed engine and MCP exposure almost entirely as specified: every REQ-ID has an artifact, every key link is wired, 1524 tests pass, D-18 / MANIFEST-05 / MANIFEST-06 invariants hold, and the analyze→seed→MCP pipeline works end-to-end for singleton seeds.

**One real gap remains:** the list→get round-trip (ROADMAP Success Criterion #5, SEED-10) fails for any seed that was produced by SEED-05 dedup merging. `list_diagram_seeds` returns `seed_id='merged-<sha12>'` (drawn from the SeedDict body), but `get_diagram_seed` constructs the file path as `{seed_id}-seed.json` while `seed.py` actually writes files as `{main_node_id}-seed.json`. The two identifiers only coincide for singletons. Because test fixtures synthesize seeds with `seed_id == main_node_id`, the 12 MCP tests never exercise the merged path, so the suite is green despite the bug.

The fix is a ~10-line change in one of three places (see `missing` in frontmatter). A single regression test asserting the full list→get round-trip on a merged seed would prevent recurrence.

All other Phase 20 deliverables are VERIFIED.

## Verdict

**CONDITIONAL** — Phase 20 is structurally complete and the suite is green, but SEED-10 / Success Criterion #5 is only partially satisfied: the list→get round-trip breaks for dedup-merged seeds. This is an observable, test-missing bug that Phase 22's Excalidraw skill will hit the moment it encounters a merged seed. Recommend closing the gap (Option A/B/C in frontmatter `missing`) and adding the regression test before starting Phase 22.

---

*Verified: 2026-04-23T13:25:00Z*
*Verifier: Claude (gsd-verifier)*
