---
phase: 15
slug: async-background-enrichment
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
audited: 2026-04-22
audit_ref: "18.2-02 — frontmatter refresh after 15-VERIFICATION PASSED (5/5 SCs, 12/12 REQ-IDs); test suites test_enrich*.py + test_enrichment_lifecycle.py 33/33 green"
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `pytest tests/test_enrich.py tests/test_enrichment_lifecycle.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30-60 seconds (full suite); ~5 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_enrich.py tests/test_enrichment_lifecycle.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Task IDs will be filled by the planner. This is the expected coverage matrix derived from 15-RESEARCH.md §Validation Architecture.

| Area | Requirement | Secure Behavior | Test Type | Test File (expected) |
|------|-------------|-----------------|-----------|----------------------|
| Module + CLI scaffold | ENRICH-01 | `graphify enrich` exits non-zero with actionable error when `graph.json` missing | unit | `tests/test_enrich.py::test_cli_missing_graph` |
| Four passes shipped | ENRICH-02 | All 4 passes enumerable via `--pass X` argparse choices | unit | `tests/test_enrich.py::test_cli_pass_choices` |
| `graph.json` read-only invariant | ENRICH-03 | Byte-equality of `graph.json` pre/post enrichment run | integration | `tests/test_enrich_invariant.py::test_graph_json_unchanged` |
| Grep-CI whitelist | SC-5 | Only `build.py` + `__main__.py` call `_write_graph_json` | grep-CI | `tests/test_enrich_grep_guard.py::test_write_graph_json_callers` |
| Atomic write + flock | ENRICH-04 | Concurrent foreground + enrichment: foreground wins, no `.tmp` orphan, no partial JSON | integration | `tests/test_enrichment_lifecycle.py::test_flock_race` |
| Snapshot pinning | ENRICH-05 | Mid-run rebuild does NOT switch enrichment to new snapshot | integration | `tests/test_enrichment_lifecycle.py::test_snapshot_pin` |
| Event-driven trigger | ENRICH-06 | `watch.py` post-rebuild hook fires enrichment only under `--enrich` flag | unit | `tests/test_watch.py::test_enrichment_trigger_opt_in` |
| SIGTERM clean-abort | ENRICH-07 | SIGTERM during pass: partial-pass `.tmp` removed, prior passes persisted, lock released | integration | `tests/test_enrichment_lifecycle.py::test_sigterm_abort` |
| Overlay merge | ENRICH-08 | `get_node` on enriched node returns `enriched_description`; base `description` unchanged | unit | `tests/test_serve.py::test_load_enrichment_overlay` |
| mtime watcher | ENRICH-09 | `_reload_if_stale` picks up `enrichment.json` updates | unit | `tests/test_serve.py::test_reload_enrichment_mtime` |
| Dry-run preview | ENRICH-10 P2 | `--dry-run` returns D-02 envelope with per-pass tokens/calls; zero LLM invocations | unit | `tests/test_enrich.py::test_dry_run_no_llm_calls` |
| Routing skip-list | ENRICH-11 P2 | Description pass skips files with `routing.json:info.class == "complex"` | unit | `tests/test_enrich.py::test_description_skip_routing_complex` |
| Alias redirect | ENRICH-12 P2 | Enrichment writes key by canonical node_id after `_resolve_alias` | unit | `tests/test_enrich.py::test_enrichment_key_alias_canonical` |
| Resumability | D-07 | Second run with same snapshot_id skips completed passes; different snapshot_id discards | unit | `tests/test_enrich.py::test_resume_same_snapshot` + `test_resume_diff_snapshot_fresh` |
| Per-pass atomic commit | D-02 | Failed pass rolls back; prior passes remain in `enrichment.json` | integration | `tests/test_enrichment_lifecycle.py::test_pass_failure_rollback` |

---

## Wave 0 Requirements

- [ ] `tests/test_enrich.py` — unit tests for CLI, overlay, resumability, dry-run, routing skip-list, alias redirect
- [ ] `tests/test_enrichment_lifecycle.py` — integration tests for flock race, SIGTERM abort, snapshot pinning, pass-failure rollback
- [ ] `tests/test_enrich_invariant.py` — graph.json byte-equality invariant test
- [ ] `tests/test_enrich_grep_guard.py` — grep-CI test for `_write_graph_json` caller whitelist
- [ ] `tests/conftest.py` extension — shared fixtures for `.enrichment.lock` teardown, snapshot pinning, subprocess SIGTERM helpers

*pytest 7.x is already installed as a dev dependency; no framework bootstrapping required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zombie process lifecycle under shell-close | Pitfall 4 mitigation | Requires a real terminal session to exercise SIGHUP/shell-disown path; not portable in CI | 1. Start `graphify enrich` in terminal. 2. Close terminal window. 3. After ~30s verify no `graphify enrich` processes remain via `ps aux \| grep graphify`. |
| Real-world LLM call coverage | ENRICH-02 (description/patterns/community quality) | Requires live API key + real graph; deterministic tests use mocked responses | 1. Populate a test graph with `graphify run` on the repo. 2. Run `graphify enrich --budget 10000`. 3. Inspect `enrichment.json` passes for semantic quality. |
| Cross-snapshot patterns signal quality | ENRICH-02 patterns | Requires ≥3 historical snapshots + multi-day commit history to evaluate | Build snapshot history over ≥1 week, then run enrich and inspect `passes.patterns[].summary`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_enrich.py, test_enrichment_lifecycle.py, test_enrich_invariant.py, test_enrich_grep_guard.py)
- [ ] No watch-mode flags (pytest runs once per sample, not `--watch`)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter after planner assigns task IDs

**Approval:** pending
