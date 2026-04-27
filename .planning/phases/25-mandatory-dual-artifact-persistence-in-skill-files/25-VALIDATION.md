---
phase: 25
slug: mandatory-dual-artifact-persistence-in-skill-files
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_install.py tests/test_skill_persistence.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | quick ~3s · full ~25s |

---

## Sampling Rate

- **After every task commit:** Run quick command (`pytest tests/test_install.py tests/test_skill_persistence.py -q`)
- **After every plan wave:** Run full suite (`pytest tests/ -q`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds (quick), ~30 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | SKILLMEM-04 | — | Regression test asserts canary in every emitted skill | unit (RED) | `pytest tests/test_skill_persistence.py::test_install_emits_persistence_canary -q` | ❌ W0 | ⬜ pending |
| 25-01-02 | 01 | 1 | SKILLMEM-04 | — | Byte-equality drift lock across 9 source files | unit (RED) | `pytest tests/test_skill_persistence.py::test_persistence_block_byte_equal_across_variants -q` | ❌ W0 | ⬜ pending |
| 25-01-03 | 01 | 2 | SKILLMEM-01 | — | Master `graphify/skill.md` carries the contract block | unit (GREEN) | `pytest tests/test_skill_persistence.py -q -k canary` | ❌ W0 | ⬜ pending |
| 25-01-04 | 01 | 2 | SKILLMEM-02 | — | All 8 remaining in-scope variants carry the verbatim block | unit (GREEN) | `pytest tests/test_skill_persistence.py -q` | ❌ W0 | ⬜ pending |
| 25-01-05 | 01 | 3 | SKILLMEM-03 | — | `graphify install <platform>` re-emits the block on fresh install for every `_PLATFORM_CONFIG` entry | unit (GREEN, subsumed by 01) | `pytest tests/test_skill_persistence.py::test_install_emits_persistence_canary -q` | ❌ W0 | ⬜ pending |
| 25-01-06 | 01 | 3 | SKILLMEM-01..04 | — | Full pytest suite green | regression | `pytest tests/ -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_skill_persistence.py` — new file; both tests RED before any contract block lands

*Existing `tests/test_install.py:18-23` `_install` helper + `Path.home()` mock pattern is reused — no new fixtures required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Contract block reads naturally for an LLM in each harness | SKILLMEM-02 | Subjective LLM-prompt quality | Spot-read inserted block in 2-3 variants (e.g. `skill-codex.md`, `skill-aider.md`) for tone consistency before commit |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
