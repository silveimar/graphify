---
phase: 56
slug: dataview-templates-profile-overrides
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.10/3.12 — CI matrix) |
| **Config file** | `pyproject.toml` (tool.pytest.ini_options if present, else default) |
| **Quick run command** | `pytest tests/test_profile.py tests/test_mapping.py tests/test_template_overrides.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | quick ~20s · full ~90s |

---

## Sampling Rate

- **After every task commit:** Run quick command (subset of impacted files)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (quick) / 120 seconds (full)

---

## Per-Task Verification Map

> Populated by planner during PLAN.md generation. Each PLAN task gets a row mapping to its automated verify command. Wave 0 dependencies marked ❌ W0 until the new test file (`tests/test_template_overrides.py`) is created.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 56-XX-XX | XX | N | TMPL-03 / CFG-01 / CFG-02 | — | path-confined override loads | unit | `pytest tests/test_template_overrides.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_template_overrides.py` — new module covering CFG-01 ladder + CFG-02 collision matrix (parametric tests per D-56.07)
- [ ] Existing `tests/test_profile.py` — additions for `mapping_rule_templates:` / `note_type_templates:` validators + dataview_queries dead-rule classes (no new file needed)
- [ ] Existing `tests/test_mapping.py` — additions for `mapping_rules.id:` slug validation + uniqueness
- [ ] No new framework install — pytest already in `pyproject.toml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docs/PROFILE-CONFIGURATION.md` worked example renders cleanly in Markdown viewers | D-56.10 | Doc rendering quality is subjective | Open in Obsidian + GitHub preview — verify code-fences, ladder list ordering, and cross-references resolve |
| `docs/TEMPLATES.md` forward-pointer reads naturally in context of the surrounding section | D-56.11 | Prose quality | Read the full TEMPLATES.md section containing the new pointer; confirm flow is not jarring |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_template_overrides.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick) / 120s (full)
- [ ] `nyquist_compliant: true` set in frontmatter (after planner populates per-task map)

**Approval:** pending
