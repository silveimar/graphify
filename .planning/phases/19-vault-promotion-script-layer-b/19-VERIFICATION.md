---
phase: 19-vault-promotion-script-layer-b
verified: 2026-04-23T06:45:04Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 19: Vault Promotion Script (Layer B) Verification Report

**Phase Goal:** `graphify/vault_promote.py` reads `graph.json` + `GRAPH_REPORT.md`, classifies/scores nodes, writes promoted Obsidian markdown notes directly to the user's vault at correct Ideaverse Pro 2.5 destination folders with full frontmatter, wikilinks, and tag taxonomy.
**Verified:** 2026-04-23T06:45:04Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `graphify vault-promote --vault /path/to/vault --threshold 3` reads graphify-out/graph.json and writes notes to correct Ideaverse folders without touching any existing vault file it did not create | ✓ VERIFIED | `promote()` in `vault_promote.py:L891–L975` orchestrates load → classify → render → write via D-13 decision table; foreign-file guard confirmed by `test_vault01_cli_does_not_overwrite_foreign` and `test_multi_run_preserves_foreign_file` |
| 2 | Every promoted note has valid Ideaverse frontmatter (`up`, `related`, `created`, `collections`, `graphifyProject`, `graphifyRun`, `graphifyScore`, `graphifyThreshold`) + ≥1 tag from each of `garden/*`, `source/*`, `graph/*` | ✓ VERIFIED | All 8 fields set in `_build_frontmatter_fields()` (lines 482–513); `_pick_baseline_tags()` emits exactly one tag per namespace; confirmed by `test_vault02_frontmatter_fields`, `test_vault02_tags_garden_source_graph` |
| 3 | Node-type dispatch: god-node → `Atlas/Dots/Things/`; knowledge gap → `Atlas/Dots/Questions/`; cluster → `Atlas/Maps/<slug>.md` with `stateMaps: 🟥` | ✓ VERIFIED | `_FOLDER_PATH_PREFIX` maps `things`→`Atlas/Dots/Things`, `questions`→`Atlas/Dots/Questions`, `maps`→`Atlas/Maps`; `stateMaps: 🟥` set at line 482; `promote()` uses prefix not record["folder"]; `test_end_to_end_all_seven_folders` asserts all 7 folders populated |
| 4 | `related:` links populated ONLY from EXTRACTED-confidence edges; INFERRED and AMBIGUOUS omitted | ✓ VERIFIED | `_extracted_neighbors()` at line 358–364 filters strictly to `confidence == "EXTRACTED"`; called in `_build_frontmatter_fields` at line 488; Maps omit `related:` entirely; confirmed by `test_vault04_related_extracted_only` |
| 5 | `graphify-out/import-log.md` written after each run with vault path, run timestamp, promoted-count by type, threshold, skipped-count | ✓ VERIFIED | `_format_run_block()` at line 755 emits `vault`, `threshold`, `promoted`, `skipped` fields; `_append_import_log()` prepends latest-first; called from `promote()` step 8; confirmed by `test_vault05_import_log_written`, `test_vault05_import_log_append_latest_first`, `test_promote_smoke` |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/vault_promote.py` | Full pipeline: load, classify, render, write, import-log, profile writeback | ✓ VERIFIED | 977 lines; all 7 buckets, `promote()` orchestrator, atomic write, manifest, import-log, VAULT-06 writeback |
| `graphify/profile.py` | `_DEFAULT_PROFILE`, `_deep_merge`, `_dump_frontmatter`, `safe_filename`, `safe_tag`, `validate_vault_path`, `load_profile`, `safe_frontmatter_value` | ✓ VERIFIED | All 8 functions present at lines 36, 121, 136, 355, 376, 415, 429, 449 |
| `graphify/analyze.py` | `knowledge_gaps()`, `_iter_sources()` | ✓ VERIFIED | `knowledge_gaps` at line 628; `_iter_sources` at line 11; imported by `vault_promote.py` |
| `graphify/builtin_templates/question.md` | Question note template | ✓ VERIFIED | Exists; all 7 templates present: `thing.md`, `question.md`, `moc.md`, `source.md`, `person.md`, `quote.md`, `statement.md` |
| `graphify/builtin_templates/quote.md` | Quote note template | ✓ VERIFIED | Exists |
| `tests/test_vault_promote.py` | 28 passing tests covering all 7 VAULT REQ-IDs | ✓ VERIFIED | 28 passed, 0 skipped, 0 failures confirmed by `pytest tests/test_vault_promote.py -q` |
| `tests/fixtures/vault_promote_graph.json` | 21-node synthetic fixture with all 7 bucket types | ✓ VERIFIED | File exists; 21 nodes, 18 links per SUMMARY |
| `graphify/__main__.py` | `vault-promote` CLI subcommand registered | ✓ VERIFIED | Command registered at line 2111; `--vault`, `--threshold`, `--graph` args; calls `promote()` |
| `README.md` | `vault-promote` usage documented | ✓ VERIFIED | `### Vault Promotion — graphify vault-promote` section at line 378; 3 occurrences of "vault-promote"; "Write semantics" present |
| `graphify/skill.md` | `vault-promote` agent guidance documented | ✓ VERIFIED | `## For vault-promote` section at line 1778 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `vault_promote.py` | `analyze.knowledge_gaps()` | `from graphify.analyze import god_nodes, knowledge_gaps, _iter_sources` | ✓ WIRED | Line 37; gaps flow into Questions bucket |
| `vault_promote.py` | `profile._DEFAULT_PROFILE` | `from graphify.profile import _DEFAULT_PROFILE, _deep_merge, ...` | ✓ WIRED | Lines 39–46; Layer 1 taxonomy baseline |
| `vault_promote.py` | `builtin_templates/*.md` | `ilr.files("graphify").joinpath("builtin_templates").joinpath(f"{note_type}.md")` | ✓ WIRED | `_load_builtin_template()` line 519–524; all 7 templates loaded by key |
| `promote()` | `write_note()` | Direct call in bucket loop (line 944) | ✓ WIRED | Uses `_FOLDER_PATH_PREFIX[bucket_key]` — not stale `record["folder"]` |
| `promote()` | `_writeback_profile()` | Conditional call at line 966–968 gated on `profile_sync.auto_update` | ✓ WIRED | VAULT-06 write-back correctly gated |
| `__main__.py` | `promote()` | `from graphify.vault_promote import promote` at line 2132 | ✓ WIRED | CLI handler calls promote with parsed args |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `vault_promote.py` → `promote()` | `G, communities` | `load_graph_and_communities(graph_path)` reads `graph.json` via `json_graph.node_link_graph` | Yes — real graph from disk | ✓ FLOWING |
| `vault_promote.py` → `classify_nodes()` | `god_list` | `god_nodes(G)` from `analyze.py` — real degree-ranked traversal | Yes | ✓ FLOWING |
| `vault_promote.py` → `classify_nodes()` | `gaps` | `knowledge_gaps(G, communities)` — isolated/thin/ambiguity detection | Yes | ✓ FLOWING |
| `vault_promote.py` → `_build_frontmatter_fields()` | `related_links` | `_extracted_neighbors(G, node_id)` — edge iteration with confidence filter | Yes — EXTRACTED edges only | ✓ FLOWING |
| `vault_promote.py` → `_append_import_log()` | run block | `_format_run_block(run_meta, promoted_counts, skipped_entries)` — live counts from write loop | Yes | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 28 vault-promote tests pass | `pytest tests/test_vault_promote.py -q` | `28 passed, 5 warnings in 0.49s` | ✓ PASS |
| Full suite passes (no regression) | `pytest tests/ -q` | `1477 passed, 7 warnings in 41.15s` | ✓ PASS |
| CLI help works | `python -m graphify vault-promote --help` | Exits 0 with `--vault`, `--threshold` in output (confirmed by `test_cli_subcommand_help_works`) | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| VAULT-01 | 19-03 | CLI reads graph.json, writes to Ideaverse folders, no foreign overwrites | ✓ SATISFIED | `promote()` orchestrator; `write_note()` D-13 table; `test_vault01_write_decision_table`, `test_vault01_cli_does_not_overwrite_foreign` |
| VAULT-02 | 19-02 | All 8 frontmatter fields + 3-namespace tag baseline | ✓ SATISFIED | `_build_frontmatter_fields()` lines 478–513; `_pick_baseline_tags()`; `test_vault02_frontmatter_fields`, `test_vault02_tags_garden_source_graph` |
| VAULT-03 | 19-02 | 7-folder dispatch: Things/Questions/Maps/Sources/People/Quotes/Statements | ✓ SATISFIED | `classify_nodes()` 7 buckets; `_FOLDER_PATH_PREFIX`; `test_end_to_end_all_seven_folders` |
| VAULT-04 | 19-02 | `related:` EXTRACTED-only | ✓ SATISFIED | `_extracted_neighbors()` line 358; `test_vault04_related_extracted_only` |
| VAULT-05 | 19-03 | `import-log.md` with vault, timestamp, counts, threshold, skips | ✓ SATISFIED | `_format_run_block()` + `_append_import_log()`; `test_vault05_import_log_written`, `test_vault05_import_log_append_latest_first` |
| VAULT-06 | 19-03 | Profile write-back: union-merge Layer-3 tags into `.graphify/profile.yaml`, atomic, gated by `auto_update` | ✓ SATISFIED | `_writeback_profile()` line 799; `test_vault06_profile_writeback_union_merge`, `test_vault06_profile_writeback_opt_out` |
| VAULT-07 | 19-01, 19-02 | 3-layer tag taxonomy: `_DEFAULT_PROFILE` → user `profile.yaml` → auto-detected extensions | ✓ SATISFIED | `resolve_taxonomy()` line 328; Layer 1/2/3 merge; `test_vault07_tag_taxonomy_layer_merge`, `test_tech_layer3_detection_persists_via_writeback` |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `vault_promote.py` | 219 | `"folder": "Atlas/"` in Questions record | ℹ️ Info | Dead field — `promote()` uses `_FOLDER_PATH_PREFIX["questions"]` = `"Atlas/Dots/Questions"` for actual writes, not `record["folder"]`. Integration test confirms correct path. No behavior impact. |

No blockers. No stubs. No placeholder implementations.

---

### Human Verification Required

None. All success criteria are verifiable programmatically and confirmed by passing tests.

---

### Gaps Summary

No gaps. All 5 success criteria verified, all 7 VAULT REQ-IDs satisfied, 28 tests pass, full suite (1477 tests) passes without regression.

The one notable observation (Questions `record["folder"]` being `"Atlas/"` vs the actual write path `"Atlas/Dots/Questions"`) is a dead/stale field — the write path is controlled exclusively by `_FOLDER_PATH_PREFIX` which is correct. The end-to-end test confirms files land in `Atlas/Dots/Questions`.

---

_Verified: 2026-04-23T06:45:04Z_
_Verifier: Claude (gsd-verifier)_
