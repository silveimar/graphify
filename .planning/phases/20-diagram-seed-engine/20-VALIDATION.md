---
phase: 20
slug: diagram-seed-engine
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-23
audited_at: 2026-04-23T13:45:00Z
asvs_level: L1
requirements_total: 11
requirements_covered: 11
requirements_partial: 0
requirements_missing: 0
---

# Phase 20 — Validation Strategy

Per-phase validation contract for the Diagram Seed Engine (SEED-01..SEED-11). Reconstructed from PLAN + SUMMARY artifacts (State B) after phase execution completed and the SEED-10 gap was closed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (via `pip install -e ".[all]"`) |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `pytest tests/test_analyze.py tests/test_seed.py tests/test_serve.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | quick: ~9s · full: ~42s |
| **Phase test files** | `tests/test_analyze.py` (47 tests, 8 new), `tests/test_seed.py` (27 tests, new file), `tests/test_serve.py` (1013 tests, 13 new incl. SEED-10 regression) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_{module}.py -q` for the task's target module (~1s)
- **After every plan wave:** Quick run command above (~9s)
- **Before `/gsd-verify-work`:** Full suite must be green (~42s)
- **Max feedback latency:** 9 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | SEED-02 | T-20-01-01..05 | `god_nodes` + `_cross_community_surprises` tag `possible_diagram_seed=True` on candidates only | unit | `pytest tests/test_analyze.py::test_god_nodes_tags_possible_diagram_seed tests/test_analyze.py::test_cross_community_surprises_tags_endpoints tests/test_analyze.py::test_god_nodes_returns_shape_unchanged -q` | ✅ | ✅ green |
| 20-01-02 | 01 | 1 | SEED-02, SEED-03 | T-20-01-01..03 | `detect_user_seeds` reads `gen-diagram-seed[/<type>]` tags with malformed-tag tolerance; tag write-back routed only through `compute_merge_plan` | unit + grep | `pytest tests/test_analyze.py::test_detect_user_seeds_reads_tags tests/test_analyze.py::test_detect_user_seeds_auto_seeds_from_attribute tests/test_analyze.py::test_detect_user_seeds_tolerates_malformed_tags tests/test_analyze.py::test_detect_user_seeds_slash_hint_empty_suffix tests/test_analyze.py::test_tag_writeback_routed_only_through_compute_merge_plan -q` | ✅ | ✅ green |
| 20-02-01 | 02 | 2 | SEED-04, SEED-05, SEED-07, SEED-08 | T-20-02-01..08 | `build_seed` ego-graph + layout heuristic + dedup + hashing invariants | unit | `pytest tests/test_seed.py -q -k "build_seed or dedup or layout_heuristic or element_id or version_nonce"` | ✅ | ✅ green |
| 20-02-02 | 02 | 2 | SEED-01, SEED-06, D-01, D-02, D-07, D-08 | T-20-02-03..08 | `build_all_seeds` orchestrator: atomic write, manifest-last, cap-before-IO, orphan cleanup, vault opt-in, CLI flag | integration | `pytest tests/test_seed.py::test_build_all_seeds_writes_manifest_and_seed_files tests/test_seed.py::test_manifest_is_written_last tests/test_seed.py::test_rerun_deletes_orphaned_seed_files tests/test_seed.py::test_cap_enforced_before_file_io_and_warn_emitted tests/test_seed.py::test_cli_diagram_seeds_flag_smoke -q` | ✅ | ✅ green |
| 20-03-01 | 03 | 3 | SEED-09, SEED-11 | T-20-03-01..07 | `list_diagram_seeds` MCP tool: registry entry + envelope + alias resolution + corrupt-manifest resilience | unit | `pytest tests/test_serve.py -q -k "list_diagram_seeds"` | ✅ | ✅ green |
| 20-03-02 | 03 | 3 | SEED-10, SEED-11 | T-20-03-01..07 | `get_diagram_seed` MCP tool: registry entry + SeedDict round-trip + path-traversal rejection + corrupt-file fallback + alias resolution | unit | `pytest tests/test_serve.py -q -k "get_diagram_seed or test_build_all_seeds_merged_seed_list_then_get_round_trip"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → Test Rollup

| REQ-ID | Status | Evidence |
|--------|--------|----------|
| SEED-01 (`build_all_seeds`) | COVERED | `test_build_all_seeds_writes_manifest_and_seed_files`, `test_cli_diagram_seeds_flag_smoke` |
| SEED-02 (tag selection + reader) | COVERED | Tests A–G in `test_analyze.py` (8 tests total with denylist) |
| SEED-03 (write-back denylist) | COVERED | `test_tag_writeback_routed_only_through_compute_merge_plan` |
| SEED-04 (SeedDict schema) | COVERED | 4 `test_build_seed_*` tests in `test_seed.py` |
| SEED-05 (dedup > 60%) | COVERED | `test_dedup_merges_when_overlap_above_60_percent`, `test_dedup_preserves_user_layout_hint_on_merge` |
| SEED-06 (cap + D-07 warn) | COVERED | `test_cap_enforced_before_file_io_and_warn_emitted`, `test_user_seeds_never_counted_toward_cap`, `test_overlap_user_frees_auto_slot` |
| SEED-07 (layout heuristic D-05) | COVERED | 5 `test_layout_heuristic_*` tests |
| SEED-08 (deterministic hashing) | COVERED | `test_element_id_is_sha256_truncated_16`, `test_version_nonce_is_deterministic`, `test_element_id_never_uses_label` |
| SEED-09 (`list_diagram_seeds`) | COVERED | 6 `test_list_diagram_seeds_*` tests |
| SEED-10 (`get_diagram_seed`) | COVERED | 5 `test_get_diagram_seed_*` tests **+** `test_build_all_seeds_merged_seed_list_then_get_round_trip` (post-verification regression for merged-seed round-trip, commits `9bf0777` RED / `7e9f880` GREEN) |
| SEED-11 (MCP registry) | COVERED | `test_list_diagram_seeds_tool_registered`, `test_get_diagram_seed_tool_registered` |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 stubs needed:
- pytest already installed and configured via `pyproject.toml`
- `tests/test_analyze.py` pre-existed (extended in Plan 20-01)
- `tests/test_seed.py` created fresh in Plan 20-02 (27 tests, RED first)
- `tests/test_serve.py` pre-existed (12 new MCP tests in Plan 20-03 + 1 regression test post-verification)

---

## Manual-Only Verifications

All phase behaviors have automated verification. No manual-only checks.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: every task in every plan has an automated command; no gap > 1 commit
- [x] Wave 0 covers all MISSING references (N/A — no missing refs)
- [x] No watch-mode flags
- [x] Feedback latency < 9s (quick) / 42s (full)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-23

---

## Validation Audit 2026-04-23

| Metric | Count |
|--------|-------|
| Requirements audited | 11 |
| COVERED | 11 |
| PARTIAL | 0 |
| MISSING | 0 |
| Resolved in this audit | 0 (no gaps) |
| Escalated to manual-only | 0 |

*Notes:* The SEED-10 merged-seed round-trip was initially flagged as an integration gap in `20-VERIFICATION.md` (status `gaps_found`). It was closed inline during phase execution by commits `9bf0777` (RED end-to-end regression) and `7e9f880` (GREEN fix: write seed files as `{seed_id}-seed.json`). The regression test drives the real `build_all_seeds` pipeline — not the `_make_seed_tree` fixture that papered over the bug.
