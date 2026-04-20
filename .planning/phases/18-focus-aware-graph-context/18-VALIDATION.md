---
phase: 18
slug: focus-aware-graph-context
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project-pinned; no version lock in `pyproject.toml` — CI uses latest) |
| **Config file** | none — pytest auto-discovers via `tests/test_*.py` |
| **Quick run command** | `pytest tests/test_serve.py tests/test_snapshot.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30s quick · ~90s full (~1315 tests = 1295 existing + 20 new) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_serve.py tests/test_snapshot.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | FOCUS-02 | — | N/A | unit | `pytest tests/test_serve.py::test_focus_resolver_str_source_file -x` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | FOCUS-02 | — | N/A | unit | `pytest tests/test_serve.py::test_focus_resolver_list_source_file_multi_seed -x` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | FOCUS-06 | — | N/A | unit | `pytest tests/test_serve.py::test_multi_seed_compose_all_matches_expected -x` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | FOCUS-01 | — | N/A | unit | `pytest tests/test_serve.py::test_get_focus_context_registered -x` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 2 | FOCUS-03 | — | N/A | unit | `pytest tests/test_serve.py::test_get_focus_context_envelope_ok -x` | ❌ W0 | ⬜ pending |
| 18-02-03 | 02 | 2 | FOCUS-03 | — | N/A | unit | `pytest tests/test_serve.py::test_get_focus_context_community_summary -x` | ❌ W0 | ⬜ pending |
| 18-02-04 | 02 | 2 | FOCUS-04 | T-18-A / spoofed-path-leak | silent `no_context`, no echoed path, no traceback | unit | `pytest tests/test_serve.py::test_get_focus_context_spoofed_path_silent -x` | ❌ W0 | ⬜ pending |
| 18-02-05 | 02 | 2 | FOCUS-04 | T-18-B / missing-file-leak | silent `no_context` on FileNotFoundError | unit | `pytest tests/test_serve.py::test_get_focus_context_missing_file_silent -x` | ❌ W0 | ⬜ pending |
| 18-02-06 | 02 | 2 | FOCUS-05 | — | N/A | static | `pytest tests/test_serve.py::test_no_watchdog_import_in_focus_path -x` | ❌ W0 | ⬜ pending |
| 18-02-07 | 02 | 2 | FOCUS-07 | T-18-C / CR-01-regression | construction fails fast when path.name == "graphify-out" | unit | `pytest tests/test_snapshot.py::test_project_root_sentinel_rejects_graphify_out -x` | ❌ W0 | ⬜ pending |
| 18-02-08 | 02 | 2 | FOCUS-07 | — | N/A | integration | `pytest tests/test_snapshot.py::test_nested_dir_fixture_list_snapshots -x` | ❌ W0 | ⬜ pending |
| 18-02-09 | 02 | 2 | FOCUS-07 | — | N/A | smoke | `pytest tests/test_serve.py::test_snapshot_callsites_use_project_root -x` | ❌ W0 | ⬜ pending |
| 18-02-10 | 02 | 2 | D-03 (cross) | T-18-A/B/C | binary envelope shape across spoof / unindexed / missing | property | `pytest tests/test_serve.py::test_binary_status_invariant -x` | ❌ W0 | ⬜ pending |
| 18-02-11 | 02 | 2 | D-08 (cross) | — | N/A | unit | `pytest tests/test_serve.py::test_budget_drop_outer_hop_first -x` | ❌ W0 | ⬜ pending |
| 18-02-12 | 02 | 2 | D-12 (cross) | T-18-A | no-context envelope does not echo focus_hint | unit | `pytest tests/test_serve.py::test_no_context_does_not_echo_focus_hint -x` | ❌ W0 | ⬜ pending |
| 18-03-01 | 03 | 3 | FOCUS-08 P2 | — | N/A | unit | `pytest tests/test_serve.py::test_focus_debounce_suppresses_duplicate -x` | ❌ W0 | ⬜ pending |
| 18-03-02 | 03 | 3 | FOCUS-08 P2 | — | N/A | unit | `pytest tests/test_serve.py::test_focus_debounce_expires -x` | ❌ W0 | ⬜ pending |
| 18-03-03 | 03 | 3 | FOCUS-09 P2 | — | N/A | unit | `pytest tests/test_serve.py::test_focus_stale_reported_at_rejected -x` | ❌ W0 | ⬜ pending |
| 18-03-04 | 03 | 3 | FOCUS-09 P2 | — | Py 3.10 Z-suffix compat shim prevents freshness parse failure | unit | `pytest tests/test_serve.py::test_focus_reported_at_z_suffix_parses -x` | ❌ W0 | ⬜ pending |
| 18-03-05 | 03 | 3 | FOCUS-09 P2 | — | malformed input returns `no_context` (no traceback) | unit | `pytest tests/test_serve.py::test_focus_malformed_reported_at -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Extend `tests/test_serve.py` with focus-resolver, envelope, binary-status, budget-drop, debounce, freshness cases (~15 tests)
- [ ] Extend `tests/test_snapshot.py` with `ProjectRoot` sentinel + nested-dir fixture (~5 tests)
- [ ] Add `nested_project_root(tmp_path)` fixture to `tests/conftest.py` — lays out `tmp_path/project/graphify-out/snapshots/` and returns `tmp_path/project` as project_root; shared by both test files.
- [ ] No framework install needed — pytest already in dev env.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*None — all phase behaviors have automated verification. The D-03/D-11 binary-status invariant is a property test, not a manual check.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
