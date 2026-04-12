---
phase: 04
slug: merge-engine
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-11
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Reconstructed retroactively from PLAN/SUMMARY artifacts after all 6 plans completed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (≥7) |
| **Config file** | `pyproject.toml` (no `pytest.ini`; pytest auto-discovers) |
| **Quick run command** | `pytest tests/test_merge.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Phase-04 scoped command** | `pytest tests/test_merge.py tests/test_profile.py tests/test_templates.py -q` |
| **Estimated runtime** | ~0.4 s (phase-scoped, 349 tests) / ~5 s (full suite, 818 tests) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_merge.py -q`
- **After every plan wave:** `pytest tests/test_merge.py tests/test_profile.py tests/test_templates.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** < 1 second for phase-scoped run; < 5 seconds for full suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | MRG-01 | T-04-01 | All 6 section builders wrap output in paired `<!-- graphify:*:start/end -->` sentinels; adversarial labels cannot break pairing | unit | `pytest tests/test_templates.py -k sentinel -q` | ✅ | ✅ green |
| 04-02-01 | 02 | 1 | MRG-02, MRG-07 | T-04-05, T-04-06 | `validate_profile` rejects invalid field_policies modes and non-string keys; `_DEFAULT_PROFILE.merge.preserve_fields` includes `rank`, `mapState`, `tags`, `created` | unit | `pytest tests/test_profile.py -k "merge or field_policies or validate_profile" -q` | ✅ | ✅ green |
| 04-03-01 | 03 | 1 | MRG-01, MRG-02, MRG-06 | T-04-08, T-04-10, T-04-11 | `_parse_frontmatter` regex-only; `_parse_sentinel_blocks` raises `_MalformedSentinel` on nested/duplicate blocks; `_resolve_field_policy` 4-tier precedence; `_merge_frontmatter` preserves key order | unit | `pytest tests/test_merge.py -q` | ✅ | ✅ green |
| 04-04-01 | 04 | 2 | MRG-01, MRG-06, MRG-07 | T-04-14..T-04-19 | `compute_merge_plan` is pure; classifies NEW/UPDATE/SKIP_IDENTICAL/SKIP_PRESERVE/SKIP_CONFLICT/ORPHAN correctly; path escape → SKIP_CONFLICT | unit | `pytest tests/test_merge.py -k "compute or action" -q` | ✅ | ✅ green |
| 04-05-01 | 05 | 2 | MRG-01, MRG-07 | T-04-20..T-04-26 | `apply_merge_plan` uses `.tmp + fsync + os.replace`; stale `.tmp` cleanup unlinks symlinks without following; path-escape recorded in `MergeResult.failed` | unit | `pytest tests/test_merge.py -k "apply or atomic or cleanup" -q` | ✅ | ✅ green |
| 04-06-01 | 06 | 3 | MRG-01, MRG-02, MRG-06, MRG-07 | T-04-01, T-04-27, T-04-29 | `TestPhase4MustHaves` suite: 11 named tests M1..M10 + T-04-01 cover every ROADMAP success criterion end-to-end | unit (e2e) | `pytest tests/test_merge.py -k "preserve_rank or strategy_skip or strategy_replace or field_order or sentinel_round_trip or unmanaged_file or malformed_sentinel or orphan_never or compute_merge_plan_is_pure or content_hash_skip or malicious_label" -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Must-Have → Test Traceability Matrix

This matrix maps the Plan 06 `TestPhase4MustHaves` suite to ROADMAP requirements and design decisions. Every must-have has exactly one named test; the test name is greppable.

| Must-Have | Test | Requirement | Design Decision | File:Line |
|-----------|------|-------------|-----------------|-----------|
| M1 | `test_preserve_rank_survives_update` | MRG-01 / success-1 | — | `tests/test_merge.py:1026` |
| M2 | `test_strategy_skip_is_noop` | MRG-07 / success-2 | — | `tests/test_merge.py:1054` |
| M3 | `test_strategy_replace_overwrites_preserve_fields` | MRG-07 / success-3 | — | `tests/test_merge.py:1082` |
| M4 | `test_field_order_preserved_minimal_diff` | MRG-06 / success-4 | — | `tests/test_merge.py:1107` |
| M5 | `test_sentinel_round_trip_deleted_block_not_reinserted` | MRG-01 | D-68 (deletion contract) | `tests/test_merge.py:1155` |
| M6 | `test_unmanaged_file_skip_conflict` | MRG-01 | D-63 (unmanaged files) | `tests/test_merge.py:1195` |
| M7 | `test_malformed_sentinel_skip_warn` | MRG-01 | D-69 (malformed sentinel) | `tests/test_merge.py:1214` |
| M8 | `test_orphan_never_deleted_under_replace` | MRG-07 | D-72 (orphan never deleted) | `tests/test_merge.py:1234` |
| M9 | `test_compute_merge_plan_is_pure` | MRG-01 | Plan 04 purity | `tests/test_merge.py:1254` |
| M10 | `test_apply_merge_plan_content_hash_skip` | MRG-01 | Re-run cheapness | `tests/test_merge.py:1271` |
| T-04-01 | `test_malicious_label_does_not_break_sentinel_pairing` | MRG-01 | Adversarial label security | `tests/test_merge.py:1293` |

### Requirement Coverage Summary

| Phase-04 Requirement | Test Count | Status |
|----------------------|-----------|--------|
| MRG-01 (update preserves user edits) | 7+ (M1, M5, M6, M7, M9, M10, T-04-01) | ✅ COVERED |
| MRG-02 (`preserve_fields` in profile) | 4+ (profile validation + M1/M3) | ✅ COVERED |
| MRG-06 (frontmatter ordering preserved) | 1 (M4 with `diff_count == 1` lock) | ✅ COVERED |
| MRG-07 (strategy: update/skip/replace) | 3 (M2, M3, M8) | ✅ COVERED |

Out-of-scope requirements (deliberately deferred, not a Phase 04 gap):

- **MRG-03** (`--dry-run` preview) — mapped to Phase 5 in `REQUIREMENTS.md:114`.
- **MRG-05** (backward-compatible fallback) — mapped to Phase 5 in `REQUIREMENTS.md:116`.

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

`tests/test_merge.py`, `tests/test_profile.py`, and `tests/test_templates.py` existed before Phase 04 and were extended in-place. No new test files created. No conftest changes required. No framework installation needed.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

Plan 04 explicitly forbids watch-mode flags and manual checks — every must-have has an `end-to-end` test over a real vault fixture copy in `tmp_path`. The regression sweep (Plan 06) ran `pytest tests/ -q` and recorded 818/818 green.

---

## Deferred Items (Pre-Existing, Not Phase-04 Scope)

Two pre-existing test failures were discovered during Phase 04 execution and deferred because they reproduce on `HEAD` before any Phase 04 changes:

- `tests/test_detect.py::test_detect_skips_dotfiles`
- `tests/test_extract.py::test_collect_files_from_dir`

See `.planning/phases/04-merge-engine/deferred-items.md`. These are environment/fixture-related issues in detect + extract suites, unrelated to `graphify/merge.py`, `graphify/profile.py`, or `graphify/templates.py`. Phase 04's own test surface (`test_merge.py` + `test_profile.py` + `test_templates.py`) is fully green at 349/349.

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

- State B (reconstructed from artifacts; no prior VALIDATION.md).
- Plan 06 pre-ships a complete must-have traceability matrix — every M1..M10 + T-04-01 is a named test at a known line number.
- No gaps surfaced; auditor spawn skipped per workflow (Step 6 direct path when gap count is zero).
- Infrastructure detected via `pyproject.toml`; no Wave 0 needed.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (no Wave 0 needed — existing infra sufficient)
- [x] No watch-mode flags
- [x] Feedback latency < 5 s (phase-scoped: ~0.4 s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-11
