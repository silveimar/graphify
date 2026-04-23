---
phase: 15-async-background-enrichment
verified: 2026-04-22T11:34:00Z
status: passed
score: 5/5 roadmap success criteria verified (12/12 REQ-IDs satisfied)
overrides_applied: 0
re_verification: null
---

# Phase 15: Async Background Enrichment — Verification Report

**Phase Goal:** "Graphify runs four derivation passes in the background after each rebuild, enriching node descriptions, detecting emerging cross-snapshot patterns, generating per-community summaries, and refreshing staleness — writing only an overlay sidecar, never mutating graph.json."

**Verified:** 2026-04-22T11:34:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| SC-1 | `graphify enrich` runs all 4 passes under `--budget`, writes `enrichment.json` keyed by canonical node_id | ✓ VERIFIED | `tests/test_enrich_invariant.py::test_graph_json_unchanged` asserts byte-equality of `graph.json` before/after a full 4-pass run. `enrich.py:946` iterates roster `("description","patterns","community","staleness")`. Canonical key guaranteed by `alias_map.get(nid, nid)` at `enrich.py:642,699,752,801`. |
| SC-2 | Foreground `/graphify` preempts enrichment cleanly; no sidecar corruption | ✓ VERIFIED | `tests/test_enrichment_lifecycle.py` covers `test_sigterm_abort`, `test_snapshot_pin`, `test_flock_race`, `test_pass_failure_rollback` — all pass. Foreground path at `__main__.py:1018-1074` SIGTERMs the PID from `.enrichment.pid` then blocks on `LOCK_EX`. Atomic write via `.tmp` + `os.replace` at `enrich.py:442-448` prevents torn sidecar. |
| SC-3 | MCP `get_node` surfaces overlay via `serve.py::_load_enrichment_overlay(out_dir)` without mutating `graph.json` | ✓ VERIFIED | `serve.py:130` defines `_load_enrichment_overlay`; called post-`_load_graph` at `serve.py:2004`. `test_serve.py::test_overlay_augments_not_overwrites` + `test_load_enrichment_overlay` pass. Byte-equality is asserted by the SC-1 invariant test above. |
| SC-4 | `graphify enrich --dry-run` emits per-pass cost preview with zero LLM calls | ✓ VERIFIED | `enrich.py:924 _emit_dry_run_envelope` emits a table + `\n---GRAPHIFY-META---\n` JSON footer (confirmed at `enrich.py:987`). `tests/test_enrich.py::test_dry_run_emits_d02_envelope` and `test_dry_run_no_llm_calls` pass. Dry-run path in `_run_passes` skips `_call_llm` entirely. |
| SC-5 | Grep-CI asserts only `build.py`, `__main__.py`, and `watch.py` may call `_write_graph_json` / `to_json` | ✓ VERIFIED | `tests/test_enrich_grep_guard.py::test_to_json_caller_whitelist` passes. Direct `grep -rn 'to_json\|_write_graph_json' graphify/` yields only: `export.py:287` (definition), `__init__.py:17` (lazy-loader registration), `watch.py:104,156` (call), `__main__.py:1264` (comment only — actual dispatch is via `watch.py`). `enrich.py` has zero hits. |

**Score:** 5/5 success criteria verified

---

### Required Artifacts (Must-Haves from PLAN frontmatter)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/enrich.py` | 4-pass orchestrator + lifecycle primitives + dry-run | ✓ VERIFIED | All 20+ exports present (`run_enrichment`, `pin_snapshot`, `_acquire_lock`, `_sigterm_handler`, `_install_sigterm`, `EnrichmentResult`, `LOCK_FILENAME`, `PID_FILENAME`, `_run_description_pass`, `_run_patterns_pass`, `_run_community_pass`, `_run_staleness_pass`, `_commit_pass`, `_load_existing_enrichment`, `_validate_enrichment_envelope`, `_emit_dry_run_envelope`, `_estimate_pass_cost`, `_lookup_price_per_1k`) |
| `graphify/__main__.py` | `enrich` subcommand + foreground-lock | ✓ VERIFIED | Dispatch at `__main__.py:1937 elif cmd == "enrich"`; `_foreground_acquire_enrichment_lock` at line 1018 wraps `to_json` call in `run` command (line 1932). Help text in `--help` block at line 1139. |
| `graphify/serve.py` | `_load_enrichment_overlay` + `_reload_if_stale` mtime watch | ✓ VERIFIED | `_load_enrichment_overlay` at line 130, called at `serve.py:2004`. `_enrichment_mtime` tracked at lines 2006, 2028, 2041, 2047. Alias-redirect threading at `serve.py:169,186,198`. |
| `graphify/watch.py` | Opt-in `--enrich` post-rebuild trigger + atexit SIGTERM | ✓ VERIFIED | `_maybe_trigger_enrichment` (line 55), `_cleanup_on_exit` (line 27), `atexit.register` (line 52). Test `test_watch.py::test_enrichment_trigger_opt_in` passes. |
| `tests/test_enrich.py` | Unit tests for CLI, passes, budget, alias, routing, sanitization, dry-run | ✓ VERIFIED | All tests in file pass in 3.60s. |
| `tests/test_enrich_grep_guard.py` | SC-5 whitelist enforcement | ✓ VERIFIED | File exists; 3 tests pass (caller whitelist, enrich never imports to_json, enrich never writes graph.json). |
| `tests/test_enrich_invariant.py` | SC-1/SC-3 byte-equality on `graph.json` | ✓ VERIFIED | `test_graph_json_unchanged` passes. |
| `tests/test_enrichment_lifecycle.py` | SC-2 SIGTERM / snapshot-pin / flock-race / rollback integration | ✓ VERIFIED | All 4 tests pass. |
| `tests/test_serve.py` | Overlay merge, augmentation, mtime watcher, alias-read, missing-file no-op | ✓ VERIFIED | 5 new tests pass. |
| `tests/test_watch.py` | Opt-in trigger assertion | ✓ VERIFIED | `test_enrichment_trigger_opt_in` passes. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `__main__.py` | `enrich.run_enrichment` | argparse dispatch | ✓ WIRED | `elif cmd == "enrich":` at line 1937 calls `run_enrichment(...)`. |
| `enrich.py` | `graphify.snapshot.list_snapshots` | `pin_snapshot` | ✓ WIRED | Verified via `pin_snapshot` function at `enrich.py:60`. |
| `enrich.py` write paths | `dedup_report.json` alias_map | `_resolve_alias(node_id)` | ✓ WIRED | `alias_map.get(nid, nid)` at enrich.py:642, 699, 752, 801 — one per pass. |
| `serve.py::serve` | `_load_enrichment_overlay` | post-`_load_graph` call | ✓ WIRED | `serve.py:2004` `_load_enrichment_overlay(G, _out_dir)`. |
| `serve.py::_reload_if_stale` | `_load_enrichment_overlay` | mtime re-apply | ✓ WIRED | `serve.py:2039-2047` — enrichment mtime tracked independently. |
| `__main__.py::run` | `.enrichment.lock` | `_foreground_acquire_enrichment_lock` LOCK_EX + SIGTERM | ✓ WIRED | `__main__.py:1932` call before `to_json`; `os.kill(pid, SIGTERM)` at line 1053. |
| `watch.py` post-rebuild | `graphify enrich` subcommand | `subprocess.Popen` opt-in | ✓ WIRED | `_maybe_trigger_enrichment(out_dir, enabled)` at line 55; atexit cleanup at line 27. |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ENRICH-01 | 15-01 | New module + `graphify enrich` CLI subcommand | ✓ SATISFIED | `graphify/enrich.py` exists; CLI dispatch at `__main__.py:1937`. Note: REQUIREMENTS.md still marks `[ ]` — documentation lag, implementation complete. |
| ENRICH-02 | 15-02, 15-03 | Four derivation passes (description, patterns, community, staleness) | ✓ SATISFIED | `PASS_NAMES = ("description", "patterns", "community", "staleness")` at `enrich.py:31`; pass functions at lines 615, 666, 727, 777. |
| ENRICH-03 | 15-02, 15-03, 15-06 | Overlay sidecar only — `graph.json` never mutated | ✓ SATISFIED | `test_enrich_invariant.py::test_graph_json_unchanged` passes. `test_enrich_grep_guard.py` enforces structurally. |
| ENRICH-04 | 15-01, 15-02 | Atomic `.tmp` + `os.replace`; shared `fcntl.flock` on `.enrichment.lock` | ✓ SATISFIED | `_commit_pass` at `enrich.py:442-448`. `_acquire_lock` at line 79. Note: REQUIREMENTS.md still `[ ]` — documentation lag. |
| ENRICH-05 | 15-01, 15-03 | Pin `--snapshot-id` at process start | ✓ SATISFIED | `pin_snapshot()` at `enrich.py:60`; `test_snapshot_pin_stem` + `test_snapshot_pin` pass. |
| ENRICH-06 | 15-05 | Event-driven via watch.py (opt-in `--enrich`, no apscheduler) | ✓ SATISFIED | `_maybe_trigger_enrichment` at `watch.py:55`; `test_enrichment_trigger_opt_in` passes. |
| ENRICH-07 | 15-01, 15-05 | Foreground wins; SIGTERM enrichment cleanly | ✓ SATISFIED | `_foreground_acquire_enrichment_lock` at `__main__.py:1018`; `_sigterm_handler` at `enrich.py:99`. `test_sigterm_abort` + `test_foreground_lock_preempts_enrichment` pass. |
| ENRICH-08 | 15-04 | `_load_enrichment_overlay(out_dir)` read-time merge post-load | ✓ SATISFIED | `serve.py:130` — called after `_load_graph` at `serve.py:2004`. |
| ENRICH-09 | 15-04 | `_reload_if_stale` watches `enrichment.json` mtime | ✓ SATISFIED | `_enrichment_mtime` tracked at `serve.py:2006, 2028, 2041, 2047`. `test_reload_if_stale_enrichment` passes. |
| ENRICH-10 [P2] | 15-06 | `--dry-run` emits cost preview without LLM | ✓ SATISFIED | `_emit_dry_run_envelope` at `enrich.py:924`; emits `---GRAPHIFY-META---` footer at line 987. `test_dry_run_no_llm_calls` passes. |
| ENRICH-11 [P2] | 15-02 | Description pass skips `complex`-routed files | ✓ SATISFIED | `_load_routing_skip_set` at `enrich.py:568`; `test_description_skip_routing_complex` passes. (Review WR-04 flags a path-normalization edge case — non-blocking Warning, not a gap.) |
| ENRICH-12 [P2] | 15-02, 15-04 | Alias redirect (D-16) threaded through writes + reads | ✓ SATISFIED | `alias_map.get(nid, nid)` at `enrich.py:642, 699, 752, 801` (writes) and `serve.py:169, 186, 198` (reads). |

**All 12 REQ-IDs satisfied. Note:** REQUIREMENTS.md table at lines 227-238 still marks all ENRICH-* as `planned`/`[ ]` — this is documentation lag only; implementation is verified complete. Recommend updating REQUIREMENTS.md to `[x]` and rewriting table rows to `verified` in the phase close.

---

### Anti-Patterns Found

Anti-patterns were surfaced in `15-REVIEW.md` (4 warnings, 7 info) and are all non-blocking correctness/robustness concerns:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `enrich.py:99-114` + `__main__.py:1047-1059` | WR-01 | Stale `.enrichment.pid` after SIGTERM (handler skips finally) | ⚠️ Warning | Foreground could SIGTERM a recycled PID in a rare time window |
| `__main__.py:1037-1071` | WR-02 | FD leak in `_foreground_acquire_enrichment_lock` on non-BlockingIOError | ⚠️ Warning | Leak only under abnormal OS errors |
| `enrich.py:146` | WR-03 | Bidirectional import graph between `enrich.py` ↔ `serve.py` (function-scoped) | ⚠️ Warning | Works today; fragile under future top-level imports |
| `enrich.py:149-152,568-599` | WR-04 | `routing_skip_set` lacks path normalization | ⚠️ Warning | No-op failure mode (wastes LLM budget on files meant to skip) |
| `enrich.py:406-432` | IN-01 | Heartbeat `expires_at` never refreshed | ℹ️ Info | No current consumer; harmless |
| `enrich.py:502-510` | IN-02 | `_validate_enrichment_envelope` accepts non-string staleness keys | ℹ️ Info | Latent downstream bug |
| `enrich.py:858-894` | IN-03 | Dry-run passes `Path(".")` as `out_dir` | ℹ️ Info | Inert today; brittle contract |
| `watch.py:207-220,242-247` | IN-04 | Unsynchronized `changed` set between threads | ℹ️ Info | At worst drops one change event |
| `enrich.py:99-114` | IN-05 | SIGTERM handler doesn't `signal.alarm(0)` | ℹ️ Info | Harmless |
| `enrich.py:449-458` | IN-06 | `_commit_pass` silently overwrites corrupt envelope | ℹ️ Info | Inconsistent with `_load_existing_enrichment` warning |
| `test_enrichment_lifecycle.py:114-117` | IN-07 | Test codifies WR-01 buggy behavior rather than desired invariant | ℹ️ Info | Blocks WR-01 regression tightening |

**None of these block the phase goal.** They are appropriate follow-ups for a stabilization pass in a later phase (v1.4 stabilization or v1.5).

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All enrich exports import | `python -c "from graphify.enrich import run_enrichment, ..."` | all exports OK | ✓ PASS |
| Overlay export imports | `python -c "from graphify.serve import _load_enrichment_overlay"` | overlay export OK | ✓ PASS |
| Phase-15 tests pass | `pytest tests/test_enrich*.py tests/test_enrichment_lifecycle.py tests/test_serve.py tests/test_watch.py -q` | 218 passed in 3.60s | ✓ PASS |
| Full test suite | `pytest tests/ -q` | 1369 passed, 2 warnings in 40.72s | ✓ PASS |
| SC-5 direct grep | `grep -rn "to_json\|_write_graph_json" graphify/` | Only whitelisted callers hit (export.py def, __init__.py lazy, watch.py call, __main__.py comment). `enrich.py` = 0 hits. | ✓ PASS |

---

### Human Verification Required

None. All 5 roadmap success criteria are covered by automated tests (`test_enrich_invariant.py` for SC-1/SC-3 byte-equality; `test_enrichment_lifecycle.py` for SC-2 preemption + race; `test_serve.py` for SC-3 MCP overlay merge; `test_enrich.py::test_dry_run_*` for SC-4; `test_enrich_grep_guard.py` for SC-5). The phase goal has no visual/UX component that requires human validation.

---

### Summary

Phase 15 achieves its goal. All 5 ROADMAP success criteria are verified by automated tests; all 12 REQ-IDs (ENRICH-01..12) have direct code + test evidence. The 4-pass roster runs in D-01 serial order, writes only `enrichment.json` via atomic `.tmp` + `os.replace`, pins `snapshot_id` at start, releases the `fcntl.flock` on SIGTERM, and the MCP serve layer merges the overlay post-`_load_graph` with alias redirection preserved on both read and write sides. The SC-5 grep-CI whitelist structurally prevents any future caller in `graphify/` from touching `to_json`/`_write_graph_json` outside the sanctioned three modules, and the SC-1/SC-3 byte-equality invariant locks `graph.json` as immutable across a full enrichment run.

The 15-REVIEW.md warnings (WR-01..WR-04) are real but non-blocking — they describe robustness edge cases (stale pid after signal-skipped finally, FD leak on exotic OS errors, bidirectional import graph, missing path normalization on routing skip set). Recommend scheduling them into the v1.4 stabilization queue.

**Action item (documentation only):** Update `.planning/REQUIREMENTS.md` to flip ENRICH-01..12 from `[ ]`/`planned` → `[x]`/`verified`. This is a known documentation lag, not a code gap.

---

_Verified: 2026-04-22T11:34:00Z_
_Verifier: Claude (gsd-verifier)_
