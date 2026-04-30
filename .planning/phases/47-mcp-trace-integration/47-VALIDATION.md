---
phase: 47
slug: mcp-trace-integration
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-30
---

# Phase 47 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none |
| **Quick run command** | `pytest tests/test_concept_code_edges.py tests/test_concept_code_mcp.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~120s |

## Sampling Rate

- After every task commit: quick command on touched tests
- After wave 2: `pytest tests/ -q`

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|---------------------|--------|
| 47-01-01 | 01 | 1 | CCODE-03 | unit | `pytest tests/test_concept_code_mcp.py -q` | pending |
| 47-01-02 | 01 | 1 | CCODE-04 | unit | `pytest tests/test_concept_code_mcp.py::test_concept_code_hops_golden_path -q` | pending |
| 47-02-01 | 02 | 2 | CCODE-03 docs | grep | `grep -q concept_code_hops docs/RELATIONS.md` | pending |

## Wave 0 Requirements

- Existing infrastructure covers requirements; new file `tests/test_concept_code_mcp.py` introduced in Plan 01.

## Manual-Only Verifications

| Behavior | Why manual |
|----------|------------|
| MCP stdio round-trip in Claude Desktop | Optional smoke; not required for CI |

## Validation Sign-Off

- [ ] `nyquist_compliant: true` after execution

**Approval:** pending
