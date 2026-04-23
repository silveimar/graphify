---
phase: 9
slug: multi-perspective-analysis-autoreason-tournament
status: audited
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-14
audited: 2026-04-14
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_analyze.py tests/test_report.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_analyze.py tests/test_report.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | render_analysis_context() prompt serializer | T-09-03 | .get() defensive access on all node attrs | unit | `pytest tests/test_analyze.py -k render_analysis_context -v` | ✅ | ✅ green |
| 09-01-02 | 01 | 1 | render_analysis() markdown renderer (D-80,D-81,D-82,D-83) | T-09-01 | _sanitize_md() strips backticks/angle brackets from LLM strings | unit | `pytest tests/test_report.py -k render_analysis -v` | ✅ | ✅ green |
| 09-02-01 | 02 | 2 | Tournament orchestration in skill.md (D-75,D-76,D-77,D-78) | T-09-04,T-09-05 | Round isolation, judge format validation | manual | N/A (skill.md = LLM prompt) | — | ✅ manual-only |
| 09-03-01 | 03 | 3 | Human quality verification checkpoint | — | N/A | manual | N/A (human review) | — | ✅ manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Test counts:** 9 tests (render_analysis_context) + 14 tests (render_analysis) + 11 tests (_sanitize_md security) = **34 automated tests**

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tournament produces meaningful GRAPH_ANALYSIS.md | D-80, D-81 | LLM output quality requires human review | Run graphify on a test corpus, review GRAPH_ANALYSIS.md for coherent per-lens findings |
| Clean verdict appears when no issues found | D-82, D-83 | Requires clean graph input | Run tournament on a well-structured codebase, verify "Clean" verdicts with rationale |
| Tournament orchestration runs 4 rounds per lens | D-76 | skill.md is an LLM prompt, not testable Python code | Run `/graphify analyze` and verify 4 rounds execute per lens in console output |
| Lens selection from user prompt works | D-78 | Prompt parsing happens in skill.md agent context | Run `/graphify analyze for security` and verify only security lens runs |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Manual-Only justification
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-14

---

## Validation Audit 2026-04-14

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

**Gap resolved:** `_sanitize_md()` (T-09-01 security mitigation) — 11 tests added covering all 6 LLM-sourced string fields for backtick stripping and angle-bracket escaping.

**Full suite after audit:** 1034 tests passing (up from 1023 before Phase 9).
