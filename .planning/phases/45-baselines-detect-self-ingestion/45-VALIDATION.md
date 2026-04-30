---
phase: 45
slug: baselines-detect-self-ingestion
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-30
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (stdlib assertions) |
| **Config file** | none |
| **Quick run command** | `pytest tests/test_detect.py tests/test_extract.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~60–180s full suite (project size dependent) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_detect.py tests/test_extract.py -q`
- **After every plan wave:** `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** target < 3 min quick slice

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 1 | HYG-01 | T-path | Resolved paths confined to corpus root | unit | `pytest tests/test_detect.py -q` | ✅ | ⬜ pending |
| 45-01-02 | 01 | 1 | HYG-01 | T-manifest | Manifest paths compared resolved-only | unit | `pytest tests/test_detect.py::test_*manifest* -q` | ❌ W0 add | ⬜ pending |
| 45-02-01 | 02 | 2 | HYG-01 | T-yaml | Profile YAML never ingested as document | unit | `pytest tests/test_detect.py -q` | ✅ | ⬜ pending |
| 45-03-01 | 03 | 3 | HYG-02 | — | Dot-path assertions pathlib + string | unit | `pytest tests/test_detect.py::test_detect_skips_dotfiles -q` | ✅ | ⬜ pending |
| 45-03-02 | 03 | 3 | HYG-03 | — | collect_files parity | unit | `pytest tests/test_extract.py -q` | ✅ | ⬜ pending |

---

## Wave 0 Requirements

- [x] Existing `tests/test_detect.py`, `tests/test_extract.py` — baseline
- [ ] New tests from Plan 03 tasks — stubs acceptable after Plan 01 lands

*Wave 0 = existing infrastructure covers baseline gates until new tests land.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operator clears stale manifest | D-45.03 | File editing | Delete `graphify-out/output-manifest.json`, re-run detect, confirm files reappear |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands
- [ ] Sampling continuity maintained across waves
- [ ] `nyquist_compliant: true` after execution sign-off

**Approval:** pending
