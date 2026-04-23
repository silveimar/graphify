---
phase: 16
slug: graph-argumentation-mode
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-22
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/test_argue.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_argue.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | ARGUE-01, 02, 03, 05, 06, 08 | T-16-03, T-16-06 | RED: test stubs assert fabrication rejection, round cap, zero-LLM, blind-label harness intact before substrate exists | unit | `pytest tests/test_argue.py -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | ARGUE-01, 02, 03, 05, 06, 08 | T-16-01, T-16-03, T-16-06 | GREEN: `argue.py` substrate with `ROUND_CAP=6`, `MAX_TEMPERATURE=0.4`, `validate_turn` fabrication guard, zero LLM imports | unit | `pytest tests/test_argue.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 16-02-01 | 02 | 2 | ARGUE-04, 07 | T-16-06 | `argue_topic` registered in `mcp_tool_registry.py` and `capability_tool_meta.yaml` with `composable_from: []` recursion guard | unit | `pytest tests/test_capability.py::test_argue_topic_not_composable -q` | ✅ | ⬜ pending |
| 16-02-02 | 02 | 2 | ARGUE-04, 07, 09 | T-16-02, T-16-05, T-16-06 | `_run_argue_topic_core` D-02 envelope with `resolved_from_alias` meta key, hardcoded `output_path: "graphify-out/GRAPH_ARGUMENT.md"`, no `_run_chat_core` invocation | unit | `pytest tests/test_serve.py -q -k argue && pytest tests/test_capability.py -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 16-03-01 | 03 | 2 | ARGUE-09, 10 | T-16-05 | `commands/argue.md` frontmatter mirrors `ask.md` (`disable-model-invocation: true`, no `target:` field); advisory-only language | unit | `pytest tests/test_commands.py::test_argue_md_frontmatter -q && pytest tests/ -q` | ✅ | ⬜ pending |
| 16-03-02 | 03 | 2 | ARGUE-06, 09, 10, 11 [P2], 12 [P2], 13 [P2] | T-16-01, T-16-04, T-16-06 | SPAR-Kit orchestration in `skill.md`: ≤6 rounds, temperature ≤ 0.4, `dissent`/`inconclusive`/`consensus` outcomes, Phase 9 blind-label harness preserved unmodified; no Phase 17 `chat` invocation | unit | `pytest tests/test_argue.py::test_blind_label_harness_intact -q && pytest tests/ -q` | ✅ | ⬜ pending |

*Populated by planner from PLAN.md `<verify><automated>` elements. Status tracked by executor.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_argue.py` — stubs for ARGUE-01..13
- [ ] `tests/fixtures/argue_fabricated.json` — known-fabricated node ID fixture for validator test
- [ ] `tests/fixtures/argue_citations.json` — valid citation packet fixture

*Existing `pytest` infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/graphify-argue <question>` skill command produces advisory-only `GRAPH_ARGUMENT.md` with cited persona claims | ARGUE-08, ARGUE-09 | LLM-driven orchestration in `skill.md`; deterministic substrate is auto-verified but end-to-end debate requires live agent | Run `/graphify-argue "Should we adopt async enrichment?"` against sample graph; verify transcript has cited claims, `dissent`/`inconclusive`/`consensus` outcome, ≤6 rounds, `[FABRICATED]` rejections if any |
| Phase 9 blind-label bias suite replay against Phase 16 debate | ARGUE-10 | Bias regression requires human judge rotation + blind A/B label comparison | Execute blind-label suite from `skill.md` §Phase 9 harness with Phase 16 transcripts — verify stripped persona phrases, rotating judge identity, blind A/B labels all intact |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_argue.py + fixtures, created by 16-01-01)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-22 (plan-checker verified)
