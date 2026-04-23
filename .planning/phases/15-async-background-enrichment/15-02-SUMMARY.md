---
phase: 15-async-background-enrichment
plan: 02
subsystem: enrichment
tags: [llm, passes, description, patterns, community, priority-drain, alias, atomic-commit]
one_liner: "Three serial LLM passes (description→patterns→community) + atomic _commit_pass for enrichment.json, all D-16 alias-gated and T-15-03 sanitized."
requires:
  - graphify.snapshot.load_snapshot
  - graphify.serve._load_dedup_report
  - graphify.security.sanitize_label_md
  - graphify.security.validate_graph_path
  - graphify.analyze.god_nodes
provides:
  - graphify.enrich._commit_pass
  - graphify.enrich._run_description_pass
  - graphify.enrich._run_patterns_pass
  - graphify.enrich._run_community_pass
  - graphify.enrich._sanitize_pass_output
  - graphify.enrich._budget_remaining
  - graphify.enrich._load_routing_skip_set
  - graphify.enrich._load_existing_enrichment
  - graphify.enrich._call_llm
  - graphify.enrich._run_passes (D-01 serial dispatcher)
affects:
  - graphify-out/enrichment.json (new sidecar; atomic-write only)
tech-stack:
  added: []
  patterns:
    - atomic write via .tmp + os.replace (copied from routing_audit.py:47-53)
    - D-16 alias_map.get(nid, nid) at every write site
    - D-03 priority-drain budget accounting
    - T-15-03 sanitize_label_md on all LLM output
key-files:
  created: []
  modified:
    - graphify/enrich.py (306 → 666 LOC; appended passes + atomic commit + real dispatcher)
    - tests/test_enrich.py (157 → 427 LOC; +7 tests)
decisions:
  - "Pattern candidate surface uses analyze.god_nodes(G, top_n=5) on the tip graph; cross-snapshot correlation deferred to Plan 06. Deterministic + no chain fixture required for Wave-2 tests."
  - "_load_routing_skip_set accepts both top-level `class` (Phase 12 RoutingAudit) and nested `info.class` (RESEARCH.md spec) for forward compatibility."
  - "_call_llm is a single private hook that raises NotImplementedError by design — production wiring deferred so tests monkeypatch cleanly and dry_run never touches it."
  - "_commit_pass rebuilds the envelope if version≠1 or snapshot_id mismatches; keeps enrichment.json tightly pinned to the snapshot_id it represents."
  - "_run_passes appends successful passes to result.passes_run (non-dry-run) or result.passes_skipped (dry-run); skipped-due-to-resume passes are simply filtered out of `requested` before execution."
metrics:
  duration: ~15m
  completed: 2026-04-22
  tasks: 2
  files_modified: 2
  commits:
    - 31dbfea (test RED)
    - a5d54cf (feat GREEN)
---

# Phase 15 Plan 02: Description / Patterns / Community Passes + Atomic Commit — Summary

## One-liner
Three serial LLM passes — `description`, `patterns`, `community` — running in D-01 order with D-03 priority-drain budget allocation, every write keyed through the D-16 alias map, and each pass committed atomically to `enrichment.json` via the `.tmp` + `os.replace` pattern copied verbatim from `routing_audit.py`.

## Locked Public API (for Plans 03/04/05/06)

```python
# graphify/enrich.py — frozen signatures

def _run_description_pass(G, out_dir, snapshot_id, *,
    budget_remaining: int, dry_run: bool,
    alias_map: dict[str, str], routing_skip: set[str],
) -> tuple[dict[str, str], int, int]:
    """(descriptions_by_canonical_id, tokens_used, llm_calls)"""

def _run_patterns_pass(G, out_dir, snapshot_id, *,
    budget_remaining: int, dry_run: bool,
    alias_map: dict[str, str], history_depth: int = 5,
) -> tuple[list[dict], int, int]:
    """(patterns_list[{pattern_id, nodes:[canonical], summary}], tokens_used, llm_calls)"""

def _run_community_pass(G, communities, out_dir, snapshot_id, *,
    budget_remaining: int, dry_run: bool,
    alias_map: dict[str, str],
) -> tuple[dict[str, str], int, int]:
    """(summary_by_str_community_id, tokens_used, llm_calls)"""

def _commit_pass(out_dir, snapshot_id, pass_name, result_data) -> None:
    """Atomic merge into enrichment.json; .tmp unlinked on failure."""

def _sanitize_pass_output(text: str) -> str      # sanitize_label_md wrapper
def _budget_remaining(budget, spent) -> int      # None → sys.maxsize
def _load_routing_skip_set(out_dir) -> set[str]  # source_file paths routed 'complex'
def _load_existing_enrichment(out_dir, snapshot_id) -> dict  # resume check
def _call_llm(prompt, max_tokens) -> tuple[str, int]  # test mock point
```

**Dispatcher contract:** `_run_passes` iterates `("description", "patterns", "community")` in that D-01 order, skipping any already present in `enrichment.json["passes"]` when `resume=True`. Staleness is untouched here — Plan 03 appends it as the 4th dispatch branch.

## D-03 Priority-Drain Behavior
- `budget=100`, per-call cost 30 → description consumes 4 calls (120 total, overshoots by one call per D-03 "check-before-not-after" semantics — documented in `test_description_pass_respects_budget`).
- Remaining budget is computed fresh per pass via `_budget_remaining(budget, result.tokens_used)`; patterns gets whatever description left, community gets whatever patterns left.
- When remaining ≤ 0 a pass still runs but its inner loop exits on the first iteration (returns empty result).
- `budget=None` → `sys.maxsize` (unlimited).

## Verification Results
- `pytest tests/test_enrich.py -q` → 12 passed (5 Plan-01 + 7 Plan-02).
- `pytest tests/ -q` → 1341 passed.
- `grep -c "alias_map.get" graphify/enrich.py` = 4 (≥3 required; applied in description, patterns, community, and internal top-members resolution).
- `grep -c "sanitize_label_md" graphify/enrich.py` = 1 (T-15-03 applied in `_sanitize_pass_output` wrapper).
- `grep -cE "to_json|_write_graph_json" graphify/enrich.py` = 0 (T-15-02 enforced — graph.json never touched).
- `graphify/enrich.py` LOC = 666 (envelope ~600 allowed one-off for detailed docstrings).

## Deviations from Plan
None. Task 1 + Task 2 executed exactly as spec'd. Note: `_run_patterns_pass` uses a simpler candidate surface than "nodes in ≥3 of last 5 snapshots" — the PLAN explicitly marked that heuristic as *Claude's Discretion* and listed cross-snapshot correlation as a Plan-06 integration concern. We picked the smaller god-node surface so Wave-2 tests don't need a snapshot-chain fixture; the pattern-assembly envelope (pattern_id / nodes / summary) is unchanged.

## Threat Mitigations Applied
| ID | Where | How |
|----|-------|-----|
| T-15-01 | `_commit_pass` | `.tmp` write → `os.replace`; except-path unlinks `.tmp`. |
| T-15-02 | entire module | zero `to_json` / `_write_graph_json` references (grep-enforced). |
| T-15-03 | all pass outputs | `_sanitize_pass_output` → `sanitize_label_md` before every write. |
| T-15-04 | `_budget_remaining` + pass loops | priority-drain; loop exits when `tokens_used >= budget_remaining`. |
| T-15-05 | all pass outputs | `alias_map.get(nid, nid)` on every emitted key (D-16). |

## Open Items for Plan 03 (staleness)
- Append `"staleness"` branch in `_run_passes` (pure compute, no budget deduction).
- Use `_load_existing_enrichment` for proper resume-from-partial-envelope logic (Plan 02 only uses it to detect snapshot_id mismatch — Plan 03 should formalize per-pass resume tests).
- Add schema version migration test (what happens when version=0 envelopes exist? Plan 02 rebuilds; Plan 03 should lock that into a regression test).
- Plan 03 should add a `test_run_passes_resume_skips_committed` sibling of Plan 02's serial-order test, exercising `resume=True` + pre-populated `enrichment.json`.

## Self-Check: PASSED
- FOUND: graphify/enrich.py (_commit_pass, _run_description_pass, _run_patterns_pass, _run_community_pass, _sanitize_pass_output, _load_routing_skip_set, _budget_remaining, _load_existing_enrichment, _call_llm)
- FOUND: tests/test_enrich.py (+7 tests; 12 total passing)
- FOUND: commit 31dbfea (RED)
- FOUND: commit a5d54cf (GREEN)
