---
phase: 10
slug: cross-file-semantic-extraction
status: draft
nyquist_compliant: true
wave_0_complete: false  # flips true after plan 10-01 executes
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

> Filled by gsd-planner during planning. One row per task across all 7 plans.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | GRAPH-02/03 | T-10-02 | validate.py accepts list provenance fields | unit | `pytest tests/test_validate.py -q` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 0 | GRAPH-02 | T-10-03 | [dedup] extra declared in pyproject | unit | `pytest tests/test_pyproject.py -q` | ✅ | ⬜ pending |
| 10-01-03 | 01 | 0 | GRAPH-02/03 | T-10-02 | conftest fixtures + stubs + fixture file | unit | `pytest tests/test_batch.py tests/test_dedup.py tests/test_validate.py -q` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | GRAPH-01 | T-10-02 | cluster_files implementation | unit | `python -c "from graphify.batch import cluster_files; assert cluster_files([], []) == []"` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | GRAPH-01 | T-10-02 | 5-behavior GRAPH-01 test matrix | unit | `pytest tests/test_batch.py -q` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 1 | GRAPH-02/03/04 | T-10-01/T-10-02 | dedup core + atomic+confined writers | unit | `python -c "from graphify.dedup import dedup, write_dedup_reports, corpus_hash; r=dedup({'nodes':[],'edges':[]}); assert r[1]['summary']['merges']==0"` | ❌ W0 | ⬜ pending |
| 10-03-02 | 03 | 1 | GRAPH-02/03/04 | T-10-01/T-10-02 | full GRAPH-02/03/04 test matrix + determinism + security | unit | `pytest tests/test_dedup.py -q` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 2 | GRAPH-02 | T-10-04 | CLI --dedup handler + yaml.safe_load only | unit | `pytest tests/test_main_cli.py -q` | ❌ W0 | ⬜ pending |
| 10-04-02 | 04 | 2 | GRAPH-01/02 | — | skill.md + 8 variants updated to per-cluster dispatch | shell | `for f in graphify/skill*.md; do grep -q "from graphify.batch import cluster_files" $f && grep -q "graphify --dedup" $f || exit 1; done` | ✅ | ⬜ pending |
| 10-05-01 | 05 | 2 | GRAPH-02 | T-10-02 | GRAPH_REPORT.md Entity Dedup section + sanitization | unit | `pytest tests/test_report.py -q` | ✅ | ⬜ pending |
| 10-06-01 | 06 | 2 | GRAPH-03 | T-10-06 | MCP alias redirect + resolved_from_alias meta | unit | `pytest tests/test_serve.py -q` | ✅ | ⬜ pending |
| 10-07-01 | 07 | 3 | GRAPH-03 | T-10-05 | render_note emits aliases: frontmatter | unit | `pytest tests/test_templates.py -q -k "alias or merged_from or aliases"` | ✅ | ⬜ pending |
| 10-07-02 | 07 | 3 | GRAPH-03 | T-10-05 | to_obsidian + --obsidian-dedup hydration | unit | `pytest tests/test_export.py -q -k "obsidian_dedup or hydrate"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*File Exists: ✅ file already in repo · ❌ W0 = created by Wave 0 plan 10-01*

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
