---
phase: 19
slug: vault-promotion-script-layer-b
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `pytest tests/test_vault_promote.py tests/test_profile.py tests/test_analyze.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds (quick) / ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_vault_promote.py tests/test_profile.py tests/test_analyze.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds for the quick loop

---

## Per-Task Verification Map

Populated by the planner as tasks are authored. Every task row must map to a REQ-ID and include an automated command from the quick or full suite, or declare a Wave 0 dependency.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 0 | VAULT-01..07 | — | N/A (scaffold) | unit | `pytest tests/test_vault_promote.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_vault_promote.py` — stubs for VAULT-01..07 (uses `tmp_path` fixture, no network, no FS outside tmp)
- [ ] `tests/test_analyze.py` — new stub or extension covering `knowledge_gaps()` extraction (see RESEARCH.md finding #1)
- [ ] `tests/test_profile.py` — additions for `tag_taxonomy` and `profile_sync` keys (both validation and deep-merge layering)
- [ ] `graphify/analyze.py::knowledge_gaps()` — extract the isolated/thin-community/high-ambiguity logic out of `report.py::generate()` (lines 194–217) into a named, testable function BEFORE any vault_promote.py code lands
- [ ] `graphify/profile.py` — add `tag_taxonomy` and `profile_sync` to `_VALID_TOP_LEVEL_KEYS` and `_DEFAULT_PROFILE` with validators following the existing `topology` pattern
- [ ] `graphify/builtin_templates/question.md` and `graphify/builtin_templates/quote.md` — new templates matching the `${frontmatter}/${label}/${body}/${metadata_callout}` substitution pattern

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Actual Obsidian rendering of promoted notes (wikilinks resolve, Dataview if present, frontmatter parsed by plugins) | VAULT-02, VAULT-03 | Plugin-dependent; pytest cannot simulate Obsidian's parser | Open a test vault after a `graphify vault-promote` run. Confirm: (1) frontmatter properties panel shows all required keys; (2) `related:` wikilinks resolve in preview; (3) Map MOC shows `stateMaps: 🟥` as an emoji; (4) tag pane shows `garden/*`, `source/*`, `graph/*`, `tech/*` namespaces |
| Re-run drift across many graph deltas (multi-run sequence) | VAULT-01, VAULT-05 | Emergent drift behavior across many runs is noisy to simulate in a single pytest; spot-check with real graphs | Run `graphify` + `graphify vault-promote` 3× over a churning repo; confirm `import-log.md` accumulates 3 blocks, overwrite-self works, and no foreign file is touched |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`knowledge_gaps()`, `tag_taxonomy`, `profile_sync`, `question.md`, `quote.md`, `test_vault_promote.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
