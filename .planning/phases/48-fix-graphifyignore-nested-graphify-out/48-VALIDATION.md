---
phase: 48
slug: fix-graphifyignore-nested-graphify-out
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-30
---

# Phase 48 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none |
| **Quick run command** | `pytest tests/test_doctor.py -q -k hyg04 tests/test_output.py -q -k default_graphify_artifacts_dir` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~2–5 minutes (full suite, project size dependent) |

---

## Sampling Rate

- **After every task commit:** Quick command above
- **After plan wave 02:** `pytest tests/test_doctor.py tests/test_output.py tests/test_detect.py tests/test_extract.py -q` (paths touched by Phase 48 plans)
- **Before `/gsd-verify-work`:** `pytest tests/ -q` green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat ref | Secure behavior | Test type | Automated command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 48-01-01 | 01 | 1 | HYG-04 | T hint-suppressed-wrongly | Same glob semantics as detect/collect_files before suppressing WOULD_SELF_INGEST ignore fix | unit | `pytest tests/test_doctor.py -q -k hyg04` | ✅ green |
| 48-02-01 | 02 | 2 | HYG-05 | T break layouts / mkdir sprawl | Default `ResolvedOutput` uses cwd `graphify-out`, not nested under corpus `target` | review + suite | `pytest tests/ -q` after trace review | ✅ green |
| 48-02-02 | 02 | 2 | HYG-05 | — | tmp_path locks canonical root vs legacy `resolved=None` behavior | unit | `pytest tests/test_output.py -q -k default_graphify_artifacts_dir` | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure covers Phase 48: regression tests were added during execution (`test_hyg04_*`, `test_default_graphify_artifacts_dir_*`). No Wave 0 stubs required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why manual | Test instructions |
|----------|-------------|------------|-------------------|
| — | — | — | All phase behaviors have automated verification for HYG-04 / HYG-05 acceptance criteria. |

---

## Validation Audit 2026-04-30

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Nyquist gap audit (`/gsd-validate-phase 48 --auto`): **State B** — no prior `48-VALIDATION.md`; reconstructed from `48-01-PLAN.md`, `48-02-PLAN.md`, summaries, and existing tests. **HYG-04** ↔ `tests/test_doctor.py::test_hyg04_graphifyignore_suppresses_redundant_self_ingest_hint`. **HYG-05** ↔ `tests/test_output.py::test_default_graphify_artifacts_dir_*`.

---

## Validation Sign-Off

- [x] All tasks have automated verify commands mapped
- [x] Focused pytest subset green (`hyg04`, `default_graphify_artifacts_dir`)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-04-30 (`/gsd-validate-phase 48 --chain --auto`)
