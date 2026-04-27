---
phase: 21
slug: profile-extension-template-bootstrap
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-23
audited_at: 2026-04-27T17:18:00Z
asvs_level: L1
requirements_total: 10
requirements_covered: 10
requirements_partial: 0
requirements_missing: 0
---

# Phase 21 — Validation Strategy

Per-phase validation contract for the Profile Extension & Template Bootstrap phase (PROF-01..04 + TMPL-01..06). Reconstructed from PLAN + SUMMARY artifacts (State A audit) after phase execution completed and all 1554 tests passed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_profile.py tests/test_seed.py tests/test_init_templates.py tests/test_denylist.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Quick run measured** | 0.88s (187 passed, 1 xfailed) |
| **Estimated full runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick subset (above) — < 1s feedback.
- **After every plan wave:** Run `pytest tests/ -q`.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 60 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement(s) | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|----------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-T1 | 21-01 | 1 | PROF-01, PROF-02, PROF-03 | T-21-01 (unknown-key bypass) | `diagram_types` accepted in `_VALID_TOP_LEVEL_KEYS`; default has 6 entries; validator agrees with parser in same atomic commit | unit | `pytest tests/test_profile.py::test_profile_diagram_types_atomicity_guard tests/test_profile.py::test_profile_missing_diagram_types_section_ok tests/test_profile.py::test_profile_diagram_types_missing_fields_graceful -q` | ✓ tests/test_profile.py:1112,1141,1146 | ✅ green |
| 21-01-T1 | 21-01 | 1 | PROF-04 | T-21-02 (recommender bypass) | `build_seed` matches profile `diagram_types` first via D-06 gate (`min_main_nodes`) and D-07 tiebreak (highest gate wins, then declaration order); falls back to `_TEMPLATE_MAP[layout_type]` | unit | `pytest tests/test_seed.py::test_seed_recommender_profile_match tests/test_seed.py::test_seed_recommender_fallback_to_layout tests/test_seed.py::test_seed_recommender_gates_on_min_main_nodes tests/test_seed.py::test_seed_recommender_tiebreak_highest_min_main_nodes_wins tests/test_seed.py::test_seed_recommender_tiebreak_declaration_order_on_equal_min -q` | ✓ tests/test_seed.py:664,674,685,696,725 | ✅ green |
| 21-01-T2 | 21-01 | 1 | PROF-02 (atomicity) | T-21-01 | All 4 hunks (keys list + default + validator + seed reader) in ONE git commit | static | `git show --stat 0f4acf2` (single-commit invariant verified at audit time; preserved by GSD atomic-commit policy) | ✓ commit `0f4acf2` | ✅ green |
| 21-02-T1 | 21-02 | 2 | TMPL-02, TMPL-03 | T-21-03 (compress drift) | `render_stub` emits `excalidraw-plugin: parsed` + `compress: false` + `## Text Elements` + `## Drawing` + valid scene JSON (type:excalidraw, version:2, source:graphify) | unit | `pytest tests/test_init_templates.py::test_render_stub_contains_compress_false tests/test_init_templates.py::test_render_stub_has_required_sections tests/test_init_templates.py::test_render_stub_scene_json_parses tests/test_init_templates.py::test_render_stub_sanitizes_label -q` | ✓ tests/test_init_templates.py:35,41,47,58 | ✅ green |
| 21-02-T1 | 21-02 | 2 | TMPL-02, TMPL-04, TMPL-05 | T-21-04 (path traversal) | `write_stubs` writes 6 stubs (or profile subset) via `validate_vault_path`; idempotent without `--force`; `--force` overwrites; path traversal blocked | unit | `pytest tests/test_init_templates.py::test_write_stubs_writes_6_files tests/test_init_templates.py::test_write_stubs_idempotent_without_force tests/test_init_templates.py::test_write_stubs_force_overwrites tests/test_init_templates.py::test_write_stubs_profile_subset tests/test_init_templates.py::test_write_stubs_path_traversal_blocked -q` | ✓ tests/test_init_templates.py:75,82,95,107,115 | ✅ green |
| 21-02-T2 | 21-02 | 2 | TMPL-01, TMPL-04, TMPL-05 | T-21-04 | `graphify --init-diagram-templates [--force]` CLI dispatches; idempotent; force overwrites; missing vault errors; unknown option errors | integration (subprocess) | `pytest tests/test_init_templates.py::test_cli_init_writes_six_stubs_tmp_path tests/test_init_templates.py::test_cli_init_idempotent_second_run_zero tests/test_init_templates.py::test_cli_init_force_overwrites_six tests/test_init_templates.py::test_cli_init_missing_vault_errors tests/test_init_templates.py::test_cli_init_unknown_option_errors -q` | ✓ tests/test_init_templates.py:141,149,157,166,172 | ✅ green |
| 21-02-T2 | 21-02 | 2 | TMPL-06 | T-21-05 (vault-write expansion) | Denylist: no direct vault `.md` writes in `seed.py` / `export.py` / `__main__.py`; only `merge.compute_merge_plan` writes vault `.md`; no `lzstring` import anywhere in `graphify/` | static (grep) | `pytest tests/test_denylist.py::test_no_direct_md_writes_in_seed_export_main tests/test_denylist.py::test_no_lzstring_import_anywhere tests/test_denylist.py::test_only_merge_exposes_compute_merge_plan -q` | ✓ tests/test_denylist.py:29,83,96 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_profile.py` — `diagram_types` validation cases (PROF-01..03) — 3 tests added
- [x] `tests/test_seed.py` — recommender cases (PROF-04, D-06, D-07) — 5 tests added
- [x] `tests/test_init_templates.py` — stub renderer + CLI (TMPL-01..05) — 14 tests added
- [x] `tests/test_denylist.py` — vault-write denylist + lzstring guard (TMPL-06) — 3 tests added

*Existing pytest infrastructure covers all phase requirements — no framework install needed. Verified by quick-run subset: 187 passed, 1 xfailed, 0.88s.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Excalidraw plugin renders stub | TMPL-02, TMPL-03 | Requires real Obsidian + Excalidraw plugin | Open a stub in Obsidian vault; confirm canvas loads with `compress: false` intact and scene JSON renders |

This is the only manual-only item; it is intentionally deferred because programmatic rendering would require a headless Obsidian instance, which is out of scope for graphify's CI. The contract (frontmatter + scene JSON shape) is fully validated by `test_render_stub_*`.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (zero MISSING at audit time)
- [x] No watch-mode flags
- [x] Feedback latency < 60s (measured: 0.88s for quick subset)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ✓ approved 2026-04-27

---

## Validation Audit 2026-04-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Pre-existing tests confirmed | 28 across 4 files |

**Findings:** All 10 phase requirements (PROF-01..04 + TMPL-01..06) had complete automated coverage at execution time — the original draft VALIDATION.md was never updated post-execution to reflect committed test files. This audit reconciles the per-task map against actual test files and flips the frontmatter from draft to approved. No new tests were generated; the auditor agent was not spawned (no gaps to fill).
