---
phase: 16
slug: graph-argumentation-mode
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/test_argue.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_argue.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | ARGUE-01..07 | — | `argue.py` substrate contains zero LLM calls | unit | `pytest tests/test_argue.py -q` | ❌ W0 | ⬜ pending |

*Populated by planner; status tracked by executor. Template row above — planner fills real tasks.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_argue.py` — stubs for ARGUE-01..13
- [ ] `tests/fixtures/argue_fabricated.json` — known-fabricated node ID fixture for validator test
- [ ] `tests/fixtures/argue_citations.json` — valid citation packet fixture

*Existing `pytest` infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/graphify-argue <question>` skill command produces advisory-only `GRAPH_ARGUMENT.md` with cited persona claims | ARGUE-08, ARGUE-09 | LLM-driven orchestration in `skill.md`; deterministic substrate is auto-verified but end-to-end debate requires live agent | Run `/graphify-argue "Should we adopt async enrichment?"` against sample graph; verify transcript has cited claims, `dissent`/`inconclusive`/`consensus` outcome, ≤6 rounds, `[FABRICATED]` rejections if any |
| Phase 9 blind-label bias suite replay against Phase 16 debate | ARGUE-10 | Bias regression requires human judge rotation + blind A/B label comparison | Execute blind-label suite from `skill.md` §Phase 9 harness with Phase 16 transcripts — verify stripped persona phrases, rotating judge identity, blind A/B labels all intact |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_argue.py + fixtures)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
