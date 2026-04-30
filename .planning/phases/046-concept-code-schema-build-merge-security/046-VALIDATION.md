---
phase: 46
slug: concept-code-schema-build-merge-security
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 46 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Quick run command** | `pytest tests/test_concept_code_edges.py tests/test_validate.py -q` |
| **Full suite command** | `pytest tests/ -q` |

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command |
|---------|------|------|-------------|-----------|-------------------|
| 46-01-01 | 01 | 1 | CCODE-01 | unit | `pytest tests/test_validate.py tests/test_concept_code_edges.py::test_unknown_edge_relation_warns_stderr -q` |
| 46-02-01 | 02 | 1 | CCODE-02 | unit | `pytest tests/test_concept_code_edges.py -q` |
| 46-03-01 | 03 | 2 | CCODE-05 | unit | `pytest tests/test_report.py -q` (if touched) / full suite |

## Validation Sign-Off

- [x] Automated coverage for normalize + warn-unknown + graph.json round-trip
- [x] Full `pytest tests/` green after implementation

**Approval:** 2026-04-30 (inline execution with `/gsd-plan-phase 46 --chain`)
