---
phase: 36
slug: migration-guide-skill-alignment-regression-sweep
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 locally; pytest is the project standard |
| **Config file** | none — direct pytest modules under `tests/` |
| **Quick run command** | `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_profile.py tests/test_templates.py tests/test_naming.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~60-90 seconds for full suite based on Phase 35 runs |

---

## Sampling Rate

- **After every task commit:** Run the focused test command for touched surfaces.
- **After every plan wave:** Run `pytest tests/test_migration.py tests/test_main_flags.py tests/test_skill_files.py tests/test_profile.py tests/test_templates.py tests/test_naming.py -q`.
- **Before `/gsd-verify-work`:** Full `pytest tests/ -q` must be green.
- **Max feedback latency:** 90 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 1 | MIG-05, VER-01 | T-36-01 / T-36-02 | Archive only after reviewed apply succeeds; no delete path | unit | `pytest tests/test_migration.py -q` | yes | pending |
| 36-01-02 | 01 | 1 | MIG-05, VER-01 | T-36-03 | Archive source/destination paths are confined and rollback metadata exists | unit | `pytest tests/test_migration.py -q` | yes | pending |
| 36-01-03 | 01 | 1 | MIG-05, VER-01 | T-36-01 / T-36-03 | CLI apply archives legacy notes by default using `tmp_path` | CLI subprocess | `pytest tests/test_main_flags.py -q` | yes | pending |
| 36-02-01 | 02 | 2 | MIG-05, VER-02 | T-36-04 | Guide covers backup, validation, dry-run, apply/archive, rollback, and rerun | docs contract | `pytest tests/test_skill_files.py -q` | yes | pending |
| 36-02-02 | 02 | 2 | VER-02 | T-36-05 | English README and CLI docs use the same v1.8 command semantics | docs/CLI | `pytest tests/test_main_flags.py tests/test_skill_files.py -q` | yes | pending |
| 36-03-01 | 03 | 2 | VER-02 | T-36-05 | Every shipped skill variant includes required v1.8 phrases | docs contract | `pytest tests/test_skill_files.py -q` | yes | pending |
| 36-03-02 | 03 | 2 | VER-02 | T-36-05 | Skill variants omit stale generated `_COMMUNITY_*` overview claims | docs contract | `pytest tests/test_skill_files.py -q` | yes | pending |
| 36-04-01 | 04 | 3 | VER-03 | T-36-03 / T-36-06 | Sanitizer matrix maps every input class to helper plus executable test | unit/security | `pytest tests/test_profile.py tests/test_templates.py tests/test_naming.py tests/test_migration.py -q` | yes | pending |
| 36-04-02 | 04 | 3 | VER-01, VER-03 | — | Full suite is green; known baseline failures fixed only if they block gate | regression | `pytest tests/ -q` | yes | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_migration.py` — archive helper-level tests for apply archive behavior and archive path confinement.
- [ ] `tests/test_main_flags.py` — CLI-level apply archive evidence test for `update-vault --apply --plan-id`.
- [ ] `tests/test_skill_files.py` — required v1.8 phrase and forbidden stale `_COMMUNITY_*` generated-output claim tests.
- [ ] `tests/test_v18_security_matrix.py` or equivalent existing-file rows — sanitizer coverage matrix for VER-03.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All Phase 36 behaviors should be covered by unit/docs/CLI tests using `tmp_path`. | N/A |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands or Wave 0 dependencies.
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] Wave 0 covers all missing references.
- [ ] No watch-mode flags.
- [ ] Feedback latency < 90s.
- [ ] `nyquist_compliant: true` set in frontmatter after execution evidence passes.

**Approval:** pending
