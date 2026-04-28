---
phase: 28
slug: self-ingestion-hardening
status: ratified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
audited: 2026-04-28
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed, all 1647 tests passing) |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3s quick / ~25s full |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3s (quick run)

---

## Per-Task Verification Map

> Task IDs and Wave numbers are placeholders pending PLAN.md authoring. Planner backfills `Task ID` / `Plan` / `Wave` columns; the `Requirement → Test` mapping below is locked.

| Requirement | Secure Behavior | Test Type | Automated Command | Status |
|-------------|-----------------|-----------|-------------------|--------|
| VAULT-11 | `output.exclude` accepted in profile schema | unit | `pytest tests/test_profile.py::test_validate_profile_output_exclude_valid_glob_list -x` | ✅ green (test_profile.py:1344) |
| VAULT-11 | Traversal/empty/non-string/non-list/absolute exclude entries rejected | unit | `pytest tests/test_profile.py -k "output_exclude" -x` | ✅ green (test_profile.py:1352–1391; 5 rejection-class tests) |
| VAULT-11 | `exclude_globs` populated in `ResolvedOutput` from profile | unit | `pytest tests/test_output.py::test_resolve_output_exclude_globs_populated_from_profile -x` | ✅ green (test_output.py:283) |
| VAULT-11 | `exclude_globs` defaults to `()` for default & cli-flag sources | unit | `pytest tests/test_output.py -k "exclude_globs" -x` | ✅ green (test_output.py:278, 294, 299) |
| VAULT-11 | `detect()` prunes files matching `exclude_globs` | unit | `pytest tests/test_detect.py::test_detect_exclude_globs_prunes_files -x` | ✅ green (test_detect.py:379) |
| VAULT-11 | `exclude_globs` applied even when `--output` overrides destination | unit | `pytest tests/test_detect.py::test_detect_exclude_globs_with_cli_flag -x` | ✅ green (test_detect.py:395) |
| VAULT-11 | Empty `exclude_globs` tuple is a no-op | unit | `pytest tests/test_detect.py::test_detect_exclude_globs_empty_tuple_no_op -x` | ✅ green (test_detect.py:409) |
| VAULT-12 | Paths matching `resolved.notes_dir.name` pruned from scan | unit | `pytest tests/test_detect.py::test_detect_nesting_guard_resolved_notes_dir_basename -x` | ✅ green (test_detect.py:310) |
| VAULT-12 | Paths matching `resolved.artifacts_dir.name` pruned from scan | unit | `pytest tests/test_detect.py::test_detect_nesting_guard_resolved_artifacts_dir_basename -x` | ✅ green (test_detect.py:325) |
| VAULT-12 | Single summary warning emitted (not per-file) | unit | `pytest tests/test_detect.py::test_detect_nesting_guard_summary_emits_once -x` | ✅ green (test_detect.py:340) |
| VAULT-12 | No warning when no nesting present | unit | `pytest tests/test_detect.py::test_detect_nesting_guard_no_warning_when_no_nesting -x` | ✅ green (test_detect.py:364) |
| VAULT-12 | Guard applies with `resolved=None` (no-vault case) | unit | `pytest tests/test_detect.py -k "test_detect_skips_graphify_out" -x` | ✅ green (test_detect.py:241, 256, 288) |
| VAULT-13 | Manifest round-trip (atomic write + read back) | unit | `pytest tests/test_detect.py::test_save_and_load_output_manifest_round_trip -x` | ✅ green (test_detect.py:426) |
| VAULT-13 | Missing manifest → silent empty (no crash) | unit | `pytest tests/test_detect.py::test_load_output_manifest_missing_returns_silent_empty -x` | ✅ green (test_detect.py:450) |
| VAULT-13 | Malformed manifest → warn-once + empty | unit | `pytest tests/test_detect.py::test_load_output_manifest_malformed_warns_once -x` | ✅ green (test_detect.py:464) |
| VAULT-13 | Wrong-shape manifest → warn-once + empty | unit | `pytest tests/test_detect.py::test_load_output_manifest_wrong_shape_warns_once -x` | ✅ green (test_detect.py:480) |
| VAULT-13 | Rolling N=5 FIFO cap enforced on write | unit | `pytest tests/test_detect.py::test_save_output_manifest_fifo_caps_at_5 -x` | ✅ green (test_detect.py:496) |
| VAULT-13 | GC of stale file entries on write | unit | `pytest tests/test_detect.py::test_save_output_manifest_gc_removes_missing_files -x` | ✅ green (test_detect.py:517) |
| VAULT-13 | Atomic write — no partial file on OSError | unit | `pytest tests/test_detect.py::test_save_output_manifest_atomic_no_partial_on_oserror -x` | ✅ green (test_detect.py:544) |
| VAULT-13 | Prior-run files excluded from scan (renamed notes_dir recovery) | unit | `pytest tests/test_detect.py::test_detect_renamed_notes_dir_no_re_ingest -x` | ✅ green (test_detect.py:591) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_detect.py` — VAULT-11/12/13 tests appended (rows 304–630): 17 dedicated tests covering nesting guard, exclude_globs, and output-manifest behaviors
- [x] `tests/test_profile.py` — VAULT-11 `output.exclude` validation tests appended (rows 1344–1391): 6 tests covering valid glob list + 5 rejection classes
- [x] `tests/test_output.py` — `ResolvedOutput.exclude_globs` 6th field landed; `test_resolve_output_exclude_globs_populated_from_profile` added (test_output.py:283); defaults & cli-flag cases at 278/294/299
- [x] No new framework or fixture install required — existing `tmp_path` fixtures from Phase 27 reused

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end self-ingestion regression repro | VAULT-11/12/13 (composite) | Multi-step user-flow scenario; covered by integration test but worth one manual pass | `cd /tmp/repro-vault && touch .obsidian/.empty && cat > .graphify/profile.yaml <<EOF\noutput:\n  mode: vault-relative\n  path: knowledge-graph\n  exclude:\n    - "**/cache/**"\nEOF` then run `graphify --obsidian` twice; second run must NOT nest `knowledge-graph/.../knowledge-graph/...` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s — `pytest tests/test_detect.py tests/test_profile.py tests/test_output.py -q` runs in ~0.42s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ratified 2026-04-28

---

## Validation Audit 2026-04-28

| Metric | Count |
|--------|-------|
| Requirements audited | 3 (VAULT-11, VAULT-12, VAULT-13) |
| Behavior rows | 20 |
| Gaps found (MISSING) | 0 |
| Resolved (existing tests mapped) | 20/20 |
| Escalated to manual-only | 0 |
| Targeted suite | 238 passed, 1 xfailed (pre-existing baseline) in 0.42s |
| Full suite | 1674 passed (per 28-VERIFICATION.md) |

**Outcome:** Phase 28 is Nyquist-compliant. The 20 behavior rows authored as Wave-0 contract before execution all map to existing tests in `tests/test_detect.py` (rows 304–630), `tests/test_profile.py` (rows 1344–1391), and `tests/test_output.py` (rows 278–299). No test generation required — this audit was a pure documentation reconciliation flipping `nyquist_compliant: false` → `true` and Wave-0 rows ❌ → ✅ to reflect post-execution reality.
