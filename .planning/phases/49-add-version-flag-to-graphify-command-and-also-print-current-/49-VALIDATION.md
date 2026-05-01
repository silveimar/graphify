---
phase: 49
slug: add-version-flag-to-graphify-command-and-also-print-current
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none |
| **Quick run command** | `pytest tests/test_main_cli.py tests/test_main_flags.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~2–5 minutes (full suite) |

---

## Sampling Rate

- **After every task commit:** Quick run command
- **After every plan wave:** `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 1 | CLI-VER-01 | — | N/A | unit | `pytest tests/test_main_flags.py -q -k version` | ✅ | ✅ green |
| 49-01-02 | 01 | 1 | CLI-VER-02 | — | N/A | unit | `pytest tests/test_main_cli.py -q -k validate_profile` | ✅ | ✅ green |

---

## Wave 0 Requirements

- Existing `tests/test_main_cli.py` subprocess harness covers CLI integration.

---

## Manual-Only Verifications

*None — all phase behaviors target automated CLI tests.*

---

## Validation Sign-Off

- [x] `nyquist_compliant: true` after tasks green
- [x] Full `pytest tests/` green after execution (1965 passed, 2026-05-01)

**Approval:** 2026-05-01 (`/gsd-execute-phase 49 --auto --chain`)
