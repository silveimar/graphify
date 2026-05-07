---
phase: 71
slug: temp
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-07
---

# Phase 71 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 71-RESEARCH.md "Validation Architecture" section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — see `pyproject.toml`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_temporal.py tests/test_validate.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds full / ~3 seconds quick |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite command above
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Populated by gsd-planner during planning. Each task gets one row mapping it to its automated verify command. Wave 0 fixtures (legacy graph.json without temporal columns; modern graph.json with temporal columns) gate Wave 1+.*

---

## Wave 0 Requirements

- [ ] `tests/test_temporal.py` — new test module for valid_from / valid_until field semantics, schema_version 2.0 round-trip
- [ ] `tests/fixtures/graph_legacy_v113.json` — frozen pre-temporal graph for backward-compat read tests
- [ ] `tests/fixtures/graph_temporal_v20.json` — temporal-stamped graph for write/read round-trip
- [ ] `tests/conftest.py` — add `freeze_run_ts` fixture (env-var `GRAPHIFY_RUN_TS` override) for deterministic temporal stamping
- [ ] Extend `tests/test_validate.py` — assert `validate_extraction_for_read` accepts legacy edges and `validate_extraction_for_write` requires `valid_from`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Obsidian vault temporal frontmatter renders correctly | TEMP-03 | Visual rendering in Obsidian | Open vault, inspect any edge note, confirm `valid_from` / `valid_until` keys present and parseable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
