---
phase: 10
slug: cross-file-semantic-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Filled from 10-RESEARCH.md `## Validation Architecture` section. Refined during planning.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `pytest tests/test_batch.py tests/test_dedup.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5s quick / ~30s full (mocked encoder; real model is opt-in) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_<module>.py -q` for the module the task touched
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green AND `pytest tests/test_dedup.py::test_determinism_golden_report -q` passes
- **Max feedback latency:** ≤30 seconds for full suite

---

## Per-Task Verification Map

> Filled by gsd-planner during step 8. Stub structure shown — planner appends one row per task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | GRAPH-02 | T-10-01 | path-confined dedup_report write | unit | `pytest tests/test_dedup.py::test_report_path_confined -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_batch.py` — stubs for GRAPH-01 (cluster_files, token-budget split, topo order, cycle fallback)
- [ ] `tests/test_dedup.py` — stubs for GRAPH-02/03/04 (fuzzy gate, embedding gate, blocking, edge re-routing, cross-type guard, golden report determinism)
- [ ] `tests/conftest.py` — shared fixtures: `fake_encoder` (deterministic numpy from `hash(label)`), `tmp_corpus` factory, `dedup_config` factory
- [ ] No new framework install required — pytest already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real `sentence-transformers/all-MiniLM-L6-v2` produces sane merge decisions on a 100-node mixed corpus | GRAPH-02 | Real model is 80MB; downloading on every CI run wasteful — only run locally before release | `pip install -e '.[dedup]'` then `pytest tests/test_dedup_real_model.py -m real_model -q` |
| Obsidian wikilink forward-mapping after `--obsidian-dedup` | GRAPH-03 (D-15) | Requires a real Obsidian vault to validate human-readable wikilink rendering | Run `graphify --obsidian-dedup --obsidian-dir /tmp/test-vault` against the fixture vault, open in Obsidian, confirm aliased links resolve to canonical notes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_batch.py + test_dedup.py + conftest fixtures)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
