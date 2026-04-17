---
phase: 11
slug: narrative-mode-slash-commands
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (per CLAUDE.md project testing convention — Python 3.10 / 3.12 CI) |
| **Config file** | none (pyproject.toml has no `[tool.pytest]` section; pytest runs with defaults) |
| **Quick run command** | `pytest tests/test_serve.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds quick (test_serve.py alone); ~45 seconds full suite (reference: Phase 10 test_serve.py runtime benchmark) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_serve.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | SLASH-01 | T-11-01-01 / T-11-01-03 | budget clamp, sanitize_label on labels | unit | `pytest tests/test_serve.py::test_graph_summary_envelope_ok -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | SLASH-03 | T-11-01-01 / T-11-01-05 | two-section non-conflation, alias redirect | unit | `pytest tests/test_serve.py::test_connect_topics_envelope_ok -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | SLASH-01, SLASH-03 | T-11-01-01..05 | envelope structure, status enum | unit | `pytest tests/test_serve.py -q -k "graph_summary or connect_topics"` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | SLASH-02 | — | shared fixture, n0..n{i} id scheme | unit | `pytest tests/ --collect-only -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 2 | SLASH-02 | T-11-02-01..03 | memory discipline (del G_snap), alias redirect | unit | `pytest tests/test_serve.py::test_entity_trace_envelope_structure -q` | ❌ W0 | ⬜ pending |
| 11-02-03 | 02 | 2 | SLASH-02 | T-11-02-02 | weakref-verified G_snap release | unit | `pytest tests/test_serve.py::test_entity_trace_memory_discipline -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 3 | SLASH-04 | T-11-03-01..04 | clamps, memory discipline | unit | `pytest tests/test_serve.py::test_drift_nodes_trend_vectors -q` | ❌ W0 | ⬜ pending |
| 11-03-02 | 03 | 3 | SLASH-05 | T-11-03-03..05 | set-based novelty rule, no_change status | unit | `pytest tests/test_serve.py::test_newly_formed_clusters_new_cluster_detected -q` | ❌ W0 | ⬜ pending |
| 11-03-03 | 03 | 3 | SLASH-04, SLASH-05 | T-11-03-01..05 | envelope structure, status enum | unit | `pytest tests/test_serve.py -q -k "drift_nodes or newly_formed"` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 4 | SLASH-01, SLASH-04 | T-11-04-01..04 | frontmatter, no_graph guard | unit | `pytest tests/test_commands.py -q -k "context or drift"` | ❌ W0 | ⬜ pending |
| 11-04-02 | 04 | 4 | SLASH-02, SLASH-03, SLASH-05 | T-11-04-01..04 | $ARGUMENTS, distinct sections, status guards | unit | `pytest tests/test_commands.py -q -k "trace or connect or emerge"` | ❌ W0 | ⬜ pending |
| 11-04-03 | 04 | 4 | SLASH-01..05 | T-11-04-01..04 | MCP tool drift detector (WARNING 3) | unit | `pytest tests/test_commands.py::test_command_files_reference_registered_tools -q` | ❌ W0 | ⬜ pending |
| 11-05-01 | 05 | 4 | SLASH-01..05 (discoverability) | T-11-05-01..02 | section injection (no rewrite) | unit | `grep -q '## Available slash commands' graphify/skill.md` | ✅ (file exists) | ⬜ pending |
| 11-05-02 | 05 | 4 | SLASH-01..05 (discoverability) | T-11-05-01..02 | 8 variants carry identical appendix | unit | `pytest tests/test_skill_files.py -q` | ❌ W0 | ⬜ pending |
| 11-05-03 | 05 | 4 | SLASH-01..05 (discoverability) | T-11-05-02 | consistency across 9 files | unit | `pytest tests/test_skill_files.py::test_skill_files_discoverability_section_is_consistent -q` | ❌ W0 | ⬜ pending |
| 11-06-01 | 06 | 5 | SLASH-01..05 (install) | T-11-06-01..04 | windows parity, opt-out flag | unit | `pytest tests/test_install.py -q -k "command_files or no_commands or uninstall_removes or non_claude"` | ✅ (file exists) | ⬜ pending |
| 11-06-02 | 06 | 5 | SLASH-01..05 (install) | T-11-06-04 | package-data glob correctness | unit | `pytest tests/test_pyproject.py::test_package_data_includes_commands -q` | ✅ (file exists) | ⬜ pending |
| 11-06-03 | 06 | 5 | SLASH-01..05 (install) | T-11-06-01..04 | windows vs codex behavior (BLOCKER 3) | unit | `pytest tests/test_install.py::test_install_command_files_windows -q` | ✅ (file exists) | ⬜ pending |
| 11-07-00 | 07 | 6 | SLASH-06, SLASH-07 | — | gate decision recorded | manual/grep | `grep -q '^GATE:' .planning/phases/11-narrative-mode-slash-commands/11-07-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 11-07-01 | 07 | 6 | SLASH-06 | T-11-07-01..03 | /ghost frontmatter, get_annotations ref | unit (conditional) | `grep -q '^GATE: defer' .../11-07-SUMMARY.md && exit 0 || pytest tests/test_commands.py::test_ghost_md_references_get_annotations -q` | ❌ W0 | ⬜ pending |
| 11-07-02 | 07 | 6 | SLASH-07 | T-11-07-01, T-11-07-04 | evidence sections, anti-fabrication guard | unit (conditional) | `grep -q '^GATE: defer' .../11-07-SUMMARY.md && exit 0 || pytest tests/test_commands.py::test_challenge_md_has_evidence_sections -q` | ❌ W0 | ⬜ pending |
| 11-07-03 | 07 | 6 | SLASH-06, SLASH-07 | T-11-07-01..04 | stretch-command suite | unit (conditional) | `grep -q '^GATE: defer' .../11-07-SUMMARY.md && exit 0 || pytest tests/test_commands.py -q -k "stretch or ghost or challenge"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*"File Exists" column: ✅ = pre-existing file being extended; ❌ W0 = Wave 0 (the plan's own Task 3) creates the test file.*

---

## Wave 0 Requirements

Every Phase 11 plan that produces code also produces its own tests in Task 3 of the same plan (one test wave per code wave). This is acceptable under Nyquist because:
- Tasks 1-2 verify via grep/AST (structural checks — ensure implementation exists)
- Task 3 verify via pytest (behavior check — ensure implementation works)
- Wave-level gate before the next wave requires the full pytest run to be green

Files created at Wave 0 (within their own plans, not upstream):
- [x] `tests/test_serve.py` — EXTENDED across plans 11-01, 11-02, 11-03 (pre-existing file; 25+ new test functions across 3 plans)
- [x] `tests/conftest.py` — EXTENDED by plan 11-02 Task 1 (new `make_snapshot_chain` fixture with n0..n{i} id scheme — BLOCKER 2 fix)
- [x] `tests/test_commands.py` — NEW FILE created by plan 11-04 Task 3 (10 tests including drift detector WARNING 3)
- [x] `tests/test_skill_files.py` — NEW FILE created by plan 11-05 Task 3 (3 tests, self-contained per WARNING 1)
- [x] `tests/test_install.py` — EXTENDED by plan 11-06 Task 3 (6 new tests including windows parity BLOCKER 3)
- [x] `tests/test_pyproject.py` — EXTENDED by plan 11-06 Task 3 (1 new test)

Framework install: not required — pytest 7.x already in `[project.optional-dependencies] dev` per pyproject.toml; CI runs it on Python 3.10 and 3.12.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| /ghost voice fidelity (rendered in Claude Code) | SLASH-06 | Requires human judgment of voice match | After `graphify install`, type `/ghost <question>` in Claude Code with an annotated graph; evaluate whether the answer sounds like the user's own notes |
| /challenge narrative tone (rendered in Claude Code) | SLASH-07 | Requires human judgment of tone and section clarity | After `graphify install`, type `/challenge <belief>` in Claude Code; evaluate whether the two sections are clearly labelled and the anti-fabrication guard is respected |
| Thinking-partner tone across all 5 core commands | SLASH-01..05 | Subjective rendering quality | Post-install, invoke each of `/context`, `/trace`, `/connect`, `/drift`, `/emerge` in Claude Code against a real graph; evaluate whether responses read as a thinking partner rather than a report |

*Automated verification covers structure, status codes, and tool registration. Tone and voice fidelity require human judgment.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (Wave 0 = same-plan Task 3 — acknowledged in Nyquist note)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every implementation task has grep/AST + pytest verify per plan-checker BLOCKER 5 pragmatic Option B)
- [x] Wave 0 covers all MISSING references (each plan's Task 3 creates/extends the pytest surface referenced by its own Tasks 1-2)
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending /gsd-plan-checker re-review (plan-checker BLOCKER 5 fix — VALIDATION.md populated with real values, frontmatter flipped to true)
