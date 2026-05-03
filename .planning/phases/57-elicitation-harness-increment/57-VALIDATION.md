---
phase: 57
slug: elicitation-harness-increment
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-03
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml + tests/conftest.py |
| **Quick run command** | `pytest tests/test_elicit.py tests/test_harness_import.py tests/test_mcp_harness_io.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick subset for the touched test module
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 57-01-T1 | 57-01 | 1 | ELIC-01 | T-57-01 | Sidecar merge precedence (elicitation wins) | unit | `pytest tests/test_elicit.py::test_sidecar_node_id_collision_elicitation_wins tests/test_elicit.py::test_sidecar_edge_conflicting_relation_last_wins tests/test_elicit.py::test_sidecar_preserves_confidence_across_merge -x -q` | ✅ | ⬜ pending |
| 57-01-T2 | 57-01 | 1 | ELIC-01 | T-57-02, T-57-03, T-57-04 | Malformed JSON swallow-and-warn; schema rejection; dangling edge accepted | unit | `pytest tests/test_elicit.py::test_malformed_sidecar_loader_returns_none tests/test_elicit.py::test_sidecar_missing_required_fields_rejected tests/test_elicit.py::test_sidecar_edge_referencing_absent_node -x -q` | ✅ | ⬜ pending |
| 57-02-T1 | 57-02 | 2 | ELIC-02, HARN-01 | T-57-06 | Trust-boundary doc surfaces vault-write refusal contract | doc | `grep -c "^## Trust Boundaries$" docs/ELICITATION.md && grep -c "^## Canonical Harness Interchange (v1) Mapping$" docs/ELICITATION.md && grep -c "^## Milestone Non-Goals (v1.11)$" docs/ELICITATION.md && grep -c "graphify.harness.interchange/v1" docs/ELICITATION.md` | ✅ | ⬜ pending |
| 57-02-T2 | 57-02 | 2 | ELIC-02, HARN-01 | T-57-05, T-57-07 | Schema-id constant ↔ doc parity; H2 heading lock | unit | `pytest tests/test_elicit.py::test_doc_has_trust_boundaries_section tests/test_elicit.py::test_doc_has_milestone_non_goals_section tests/test_elicit.py::test_doc_has_canonical_mapping tests/test_harness_interchange.py::test_interchange_schema_id_locked -x -q` | ✅ | ⬜ pending |
| 57-03-T1 | 57-03 | 1 | HARN-02 | T-57-08 | Vault-output refusal unless `--allow-vault-write` | unit (subprocess) | `pytest tests/test_harness_import.py::test_import_refuses_vault_rooted_output tests/test_harness_import.py::test_import_accepts_vault_with_explicit_flag -x -q` | ✅ | ⬜ pending |
| 57-03-T2 | 57-03 | 1 | HARN-02 | T-57-09 | No auto-invocation: AST allowlist guard | meta-test | `pytest tests/test_harness_import.py::test_no_auto_invocation_of_import_harness -x -q` | ✅ | ⬜ pending |
| 57-03-T3 | 57-03 | 1 | HARN-02 | T-57-10 | MCP `import_harness` requires explicit `path` arg | unit | `pytest tests/test_mcp_harness_io.py::test_mcp_import_harness_refuses_empty_path -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_elicit.py` — extend with sidecar collision scenarios (ELIC-01)
- [x] `tests/test_harness_import.py` — extend with off-by-default guard tests (HARN-02)
- [x] `tests/test_mcp_harness_io.py` — extend with MCP explicit-path-required guard (HARN-02)
- [x] No new framework install required — pytest already configured

All target test modules exist in the repo; new tests are appended in-place. No file creation required for Wave 0.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trust Boundaries doc reads correctly | ELIC-02 | Prose review | Open `docs/ELICITATION.md`; verify `## Trust Boundaries` and `## Milestone Non-Goals (v1.11)` sections are present, accurate, and reference the right code surfaces |
| Canonical mapping prose matches schema | HARN-01 | Doc/code alignment | Cross-read mapping section against `graphify/harness_interchange.py` `INTERCHANGE_SCHEMA_ID` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-03
