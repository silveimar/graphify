---
phase: 56
slug: dataview-templates-profile-overrides
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
updated: 2026-05-02
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 56-01-T1 | 01 | 1 | CFG-02 | — | provenance shape change (no security surface) | unit (RED) | `pytest tests/test_profile.py::test_provenance_accumulates_across_extends_chain -x` (expect non-zero) | ✅ | ⬜ pending |
| 56-01-T2 | 01 | 1 | CFG-02 | — | provenance accumulates all writers (no last-writer info loss) | unit (GREEN) | `pytest tests/test_profile.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 56-02-T1 | 02 | 2 | CFG-02 | — | preflight collision detection (defense-in-depth at validation layer) | unit (RED) | `pytest tests/test_template_overrides.py 2>&1 \| grep -E "failed"` | ✅ W0 | ⬜ pending |
| 56-02-T2 | 02 | 2 | CFG-02 | — | deterministic error wording for 4 collision classes | unit (GREEN) | `pytest tests/test_template_overrides.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 56-03-T1 | 03 | 3 | CFG-01 | — | path-confined override loads (`..`, abs, `~` rejected) | unit (RED) | `pytest tests/test_profile.py tests/test_mapping.py 2>&1 \| grep -E "failed"` | ✅ | ⬜ pending |
| 56-03-T2 | 03 | 3 | CFG-01 | T-30-V12 | path-confinement validators ported verbatim from community_templates: | unit (GREEN) | `pytest tests/test_profile.py -q` | ✅ | ⬜ pending |
| 56-03-T3 | 03 | 3 | CFG-01 | — | mapping_rules.id slug pattern + uniqueness validated | unit (GREEN) | `pytest tests/test_mapping.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 56-04-T1 | 04 | 4 | TMPL-03 | — | dataview_queries dead-rule preflight | unit (RED) | `pytest tests/test_profile.py 2>&1 \| grep -E "failed"` | ✅ | ⬜ pending |
| 56-04-T2 | 04 | 4 | TMPL-03 | — | unknown ${var} rejected (allowlist {community_tag, folder}); unreachable note_type rejected; empty-after-substitution rejected | unit (GREEN) | `pytest tests/test_profile.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 56-05-T1 | 05 | 5 | CFG-01 | — | ladder + warn-fallback + classify integration | unit (RED) | `pytest tests/test_template_overrides.py 2>&1 \| grep -E "failed"` | ✅ | ⬜ pending |
| 56-05-T2 | 05 | 5 | CFG-01 | T-55-D55.14 | warn-and-fall-back per list (no abort on missing override) | unit (GREEN) | `pytest tests/test_template_overrides.py::test_classify_populates_rule_id_when_matched_rule_has_id tests/test_template_overrides.py::test_community_template_missing_file_still_warns_with_correct_list_name -x && pytest tests/ -q` | ✅ | ⬜ pending |
| 56-05-T3 | 05 | 5 | CFG-01 | — | D-56.05 ladder order: mapping_rule > community > note_type > base | unit (GREEN) | `pytest tests/test_template_overrides.py -q && pytest tests/test_profile_composition.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 56-06-T1 | 06 | 5 | TMPL-03, CFG-01, CFG-02 | — | docs (no code) | manual + grep | `grep -c "mapping_rule_templates" docs/PROFILE-CONFIGURATION.md` returns >= 3 | ✅ | ⬜ pending |
| 56-06-T2 | 06 | 5 | CFG-01 | — | docs (no code) | manual + grep | `grep -c "PROFILE-CONFIGURATION.md" docs/TEMPLATES.md` returns >= 1 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_template_overrides.py` — CREATED in Plan 02 Task 1 (wave 2 RED), extended in Plan 05 Task 1 (wave 3 RED). Wave 0 dependency satisfied as part of the CFG-02 RED step before any GREEN consumer task lands.
- [x] Existing `tests/test_profile.py` — additions for `mapping_rule_templates:` / `note_type_templates:` validators (Plan 03) + dataview_queries dead-rule classes (Plan 04) + provenance shape (Plan 01). No new file needed.
- [x] Existing `tests/test_mapping.py` — additions for `mapping_rules.id:` slug validation + uniqueness (Plan 03 Task 1).
- [x] No new framework install — pytest already in `pyproject.toml`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `docs/PROFILE-CONFIGURATION.md` worked example renders cleanly in Markdown viewers | D-56.10 | Doc rendering quality is subjective | Open in Obsidian + GitHub preview — verify code-fences, ladder list ordering, and cross-references resolve |
| `docs/TEMPLATES.md` forward-pointer reads naturally in context of the surrounding section | D-56.11 | Prose quality | Read the full TEMPLATES.md section containing the new pointer; confirm flow is not jarring |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task has its own command)
- [x] Wave 0 covers all MISSING references (`tests/test_template_overrides.py` created in Plan 02 Task 1)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (quick) / 120s (full)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for execution
