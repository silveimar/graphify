---
phase: 21
slug: profile-extension-template-bootstrap
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_profile.py tests/test_seed.py tests/test_main.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_profile.py tests/test_seed.py tests/test_main.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD by planner | — | — | PROF-01..04, TMPL-01..06 | — | — | unit | `pytest -q` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profile.py` — extend with `diagram_types` validation cases (PROF-01..04)
- [ ] `tests/test_main.py` — extend with `--init-diagram-templates` CLI cases (TMPL-01..05)
- [ ] `tests/test_vault_write_denylist.py` — new grep-denylist test (TMPL-06)

*Existing pytest infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Excalidraw plugin renders stub | TMPL-02, TMPL-03 | Requires real Obsidian + Excalidraw plugin | Open a stub in Obsidian vault; confirm canvas loads with `compress: false` intact and scene JSON renders |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
