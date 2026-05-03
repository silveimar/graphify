---
phase: 57
slug: elicitation-harness-increment
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| (filled by planner) | | | ELIC-01 / ELIC-02 / HARN-01 / HARN-02 | | | unit / meta-test / doc | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_elicit.py` — extend with sidecar collision scenarios (ELIC-01)
- [ ] `tests/test_harness_import.py` — extend with off-by-default guard tests (HARN-02)
- [ ] `tests/test_mcp_harness_io.py` — extend with MCP explicit-path-required guard (HARN-02)
- [ ] No new framework install required — pytest already configured

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trust Boundaries doc reads correctly | ELIC-02 | Prose review | Open `docs/ELICITATION.md`; verify `## Trust Boundaries` and `## Milestone Non-Goals (v1.11)` sections are present, accurate, and reference the right code surfaces |
| Canonical mapping prose matches schema | HARN-01 | Doc/code alignment | Cross-read mapping section against `graphify/harness_interchange.py` `INTERCHANGE_SCHEMA_ID` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
