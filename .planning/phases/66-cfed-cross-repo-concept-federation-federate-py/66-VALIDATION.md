---
phase: 66
slug: cfed-cross-repo-concept-federation-federate-py
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-06
---

# Phase 66 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sourced from RESEARCH.md ## Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured via `pyproject.toml` + `tests/conftest.py`) |
| **Config file** | `pyproject.toml` (no separate `pytest.ini`) |
| **Quick run command** | `pytest tests/test_federate.py tests/test_build.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5s quick, ~60s full |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_federate.py tests/test_build.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 66-XX-01 | TBD | 1 | CFED-01 | — | Default off; absent flag = no-op | unit | `pytest tests/test_build.py -x` | ✅ | ⬜ pending |
| 66-XX-02 | TBD | 1 | CFED-01 | — | `--federate-with` repeatable | unit | `pytest tests/test_federate.py::test_cli_repeatable -x` | ❌ W0 | ⬜ pending |
| 66-XX-03 | TBD | 1 | CFED-02 | — | Two runs → byte-identical manifest | unit | `pytest tests/test_federate.py::test_manifest_deterministic -x` | ❌ W0 | ⬜ pending |
| 66-XX-04 | TBD | 1 | CFED-02 | — | No new deps (AST-scan federate.py) | unit | `pytest tests/test_federate.py::test_no_new_deps -x` | ❌ W0 | ⬜ pending |
| 66-XX-05 | TBD | 2 | CFED-03 | — | Namespacing rewrites all ids + edges | unit | `pytest tests/test_federate.py::test_namespace -x` | ❌ W0 | ⬜ pending |
| 66-XX-06 | TBD | 2 | CFED-03 | — | AND-gate all-pass → merge | unit | `pytest tests/test_federate.py::test_gate_all_pass -x` | ❌ W0 | ⬜ pending |
| 66-XX-07 | TBD | 2 | CFED-03 | — | AND-gate any-fail → no merge (3 cases) | unit | `pytest tests/test_federate.py::test_gate_label_fail tests/test_federate.py::test_gate_jaccard_fail tests/test_federate.py::test_gate_basename_fail -x` | ❌ W0 | ⬜ pending |
| 66-XX-08 | TBD | 2 | CFED-03 | — | Tiebreaker: mean INFERRED confidence_score | unit | `pytest tests/test_federate.py::test_tiebreaker -x` | ❌ W0 | ⬜ pending |
| 66-XX-09 | TBD | 2 | CFED-03 | — | Canonical merged_id = lex-min | unit | `pytest tests/test_federate.py::test_canonical_id -x` | ❌ W0 | ⬜ pending |
| 66-XX-10 | TBD | 2 | CFED-03 | T-66-01 | Repo basename collision → two-line stderr error | unit | `pytest tests/test_federate.py::test_collision_error -x` | ❌ W0 | ⬜ pending |
| 66-XX-11 | TBD | 2 | CFED-04 | — | Manifest path via `default_graphify_artifacts_dir` | unit | `pytest tests/test_federate.py::test_manifest_vault_aware -x` | ❌ W0 | ⬜ pending |
| 66-XX-12 | TBD | 2 | CFED-04 | — | Manifest schema matches D-66.5 | unit | `pytest tests/test_federate.py::test_manifest_schema -x` | ❌ W0 | ⬜ pending |
| 66-XX-13 | TBD | 2 | CFED-04 | — | Atomic manifest write | unit | `pytest tests/test_federate.py::test_manifest_atomic -x` | ❌ W0 | ⬜ pending |
| 66-XX-14 | TBD | 3 | CFED-05 | — | Federation section renders on merges | unit | `pytest tests/test_federate.py::test_report_renders_section -x` | ❌ W0 | ⬜ pending |
| 66-XX-15 | TBD | 3 | CFED-05 | — | Federation section omitted on zero merges | unit | `pytest tests/test_federate.py::test_report_omits_on_zero -x` | ❌ W0 | ⬜ pending |
| 66-XX-16 | TBD | 3 | CFED-05 | T-66-02 | Missing peer artifact → Phase 64 two-line stderr | unit | `pytest tests/test_stderr_contract.py -x` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Plan column = TBD; planner fills in `66-01-PLAN.md` etc.*

---

## Wave 0 Requirements

- [ ] `tests/test_federate.py` — main module covering all CFED-01..05 cases above
- [ ] `tests/fixtures/peer_match/graph.json` — peer artifact achieving all three gate signals (full merge)
- [ ] `tests/fixtures/peer_nomerge/graph.json` — peer with label match but neighborhood Jaccard < 0.5 (zero-merge case)
- [ ] `tests/fixtures/peer_collision_a/graph.json` and `peer_collision_b/graph.json` — same basename, for collision test
- [ ] Extend `tests/test_stderr_contract.py` snapshot with federation error breadcrumb
- [ ] (Optional) Extract Federation-section assertion helpers from `tests/test_report_calibration.py` style

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end CLI run with two real graphify-out/ trees | CFED-01..05 | Cross-repo orchestration is awkward to fully fixture | Run `graphify federate --federate-with ../graphify-other-repo/graphify-out` from a third repo; confirm `graphify-out/federation-manifest.json` exists, `GRAPH_REPORT.md` has Federation section, and a known concept appears merged. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
