---
phase: 25
slug: mandatory-dual-artifact-persistence-in-skill-files
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
last_audited: 2026-04-27
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

The plan contains exactly 3 tasks. Task IDs below match `25-01-NN` 1:1 with PLAN.md tasks.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | SKILLMEM-04 | — | RED unit tests: canary + byte-equality drift lock fail because no skill file yet contains the sentinel; existing suite still green; `IN_SCOPE_PLATFORMS` derived from `_PLATFORM_CONFIG` at runtime | unit (RED) | `pytest tests/test_skill_persistence.py -q; [ $? -ne 0 ] && pytest tests/ --ignore=tests/test_skill_persistence.py -q` | ❌ W0 (created in this task) | ✅ green |
| 25-01-02 | 01 | 1 | SKILLMEM-01 | — | Partial GREEN: master `graphify/skill.md` carries the verbatim contract block; the 2 platforms that consume `skill.md` (`claude`, `antigravity` per `__main__.py:51,132`) now pass the canary; remaining 9 platforms still red | unit (partial GREEN) | `pytest tests/test_skill_persistence.py::test_install_emits_persistence_canary -q -k "claude or antigravity"` | ✅ after 25-01-01 | ✅ green |
| 25-01-03 | 01 | 1 | SKILLMEM-02, SKILLMEM-03 | — | Full GREEN: all 8 remaining in-scope variants carry the byte-identical block; all 11 in-scope `_PLATFORM_CONFIG` entries (claude, codex, opencode, aider, copilot, claw, droid, trae, trae-cn, antigravity, windows) pass the canary; byte-equality drift lock passes; full suite green | unit (full GREEN) + regression | `pytest tests/test_skill_persistence.py -q && pytest tests/ -q` | ✅ after 25-01-02 | ✅ green |

*Status: ✅ green · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_skill_persistence.py` — created in Task 25-01-01 (RED state); both tests deliberately fail until Task 25-01-02 and 25-01-03 land the contract block. The test file's mere existence and import-time `_PLATFORM_CONFIG` derivation satisfy the Wave 0 scaffold requirement: every later task's `<verify>` references a test that already exists at the time it runs.

*Existing `tests/test_install.py:18-23` `_install` helper + `Path.home()` mock pattern is reused — no new fixtures required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Contract block reads naturally for an LLM in each harness | SKILLMEM-02 | Subjective LLM-prompt quality | Spot-read inserted block in 2-3 variants (e.g. `skill-codex.md`, `skill-aider.md`) for tone consistency before commit |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (revised 2026-04-27 to reconcile task IDs 1:1 with PLAN.md and lock canonical 11-key in-scope platform list)
**Validated:** 2026-04-27 by `/gsd-validate-phase 25` — all task statuses promoted from ⬜ pending → ✅ green, frontmatter `status: draft → validated`, `last_audited: 2026-04-27` added.

---

## Validation Audit 2026-04-27

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Live evidence:** `pytest tests/test_install.py tests/test_skill_persistence.py -q` → **79 passed in 0.24s**.

**Bookkeeping-only:** Phase was already fully implemented and verified (see `25-VERIFICATION.md`, status `passed`, score 7/7). VALIDATION.md content already had `nyquist_compliant: true` + `wave_0_complete: true`; only frontmatter `status` and per-task pending markers were stale. No tests added; no impl changes; no escalations.
