---
phase: 15-async-background-enrichment
plan: 03
subsystem: enrichment
tags: [staleness, resume, schema, compute-only, enrichment]
requires:
  - graphify.delta.classify_staleness
  - graphify.enrich._commit_pass
  - graphify.enrich.PASS_NAMES
provides:
  - graphify.enrich._run_staleness_pass
  - graphify.enrich._load_existing_enrichment
  - graphify.enrich._validate_enrichment_envelope
affects:
  - graphify/enrich.py
  - tests/test_enrich.py
tech-stack:
  added: []
  patterns:
    - "D-05 envelope schema: version=1, strict key-subset + per-pass container shape"
    - "D-07 resume-by-default: snapshot_id match → per-pass skip; mismatch or malformed → fresh"
    - "D-03 budget-exempt compute-only pass (staleness)"
key-files:
  created: []
  modified:
    - graphify/enrich.py (+149 / −15 LOC; 800 total)
    - tests/test_enrich.py (+344 LOC)
decisions:
  - "Staleness pass is a thin wrapper around delta.classify_staleness — no reimplementation"
  - "_validate_enrichment_envelope logs version-mismatch warnings (user-diagnosable) but returns False silently for other shape deviations"
  - "_load_existing_enrichment returns the FULL envelope dict; caller reads the passes sub-dict for the per-pass skip gate"
  - "Staleness pass tolerates dry_run without changing its behavior (cheap anyway) so Plan 06's --dry-run preview still shows an accurate staleness snapshot"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-22"
  tasks: 2
  tests_added: 6
  tests_total_enrich: 18
  tests_full_suite: 1347
requirements:
  - ENRICH-02
  - ENRICH-03
  - ENRICH-05
---

# Phase 15 Plan 03: Staleness Pass + Resume + Schema Guard Summary

**One-liner:** Add D-01 pass 4 (`staleness`, compute-only wrapping `delta.classify_staleness`) plus D-07 per-pass resume gate and D-05 strict schema guard, closing out the 4-pass enrichment roster.

## Public API

| Symbol | Signature | Role |
|--------|-----------|------|
| `_run_staleness_pass` | `(G, out_dir, snapshot_id, *, alias_map, dry_run=False) -> tuple[dict[str, str], int, int]` | Pass 4 — always returns `(labels, 0, 0)`. Labels ∈ `{FRESH, STALE, GHOST}`. D-03 budget-exempt. D-16 alias-threaded keys. |
| `_load_existing_enrichment` | `(out_dir: Path, snapshot_id: str) -> dict` | D-07 gate — returns the full v1 envelope iff file exists, parses, passes `_validate_enrichment_envelope`, AND matches `snapshot_id`; else `{}`. |
| `_validate_enrichment_envelope` | `(data: object) -> bool` | D-05 strict schema guard. Returns `False` on any deviation; logs version-mismatch warnings to stderr. |

Plan 04's `_load_enrichment_overlay` can compose against this locked v1 shape.

## D-07 Resume Behavior Table

| Condition | `_load_existing_enrichment` return | `_run_passes` outcome |
|-----------|-----------------------------------|----------------------|
| File absent | `{}` | All 4 passes run fresh |
| File unreadable / JSON decode error | `{}` + stderr warning | Fresh run; next `_commit_pass` writes new envelope |
| Version ≠ 1 | `{}` + `"envelope version != 1; discarding"` stderr warning | Fresh run; envelope overwritten on first commit |
| Unknown pass key (e.g. from future phase) in v1 envelope | `{}` + `"unexpected pass key"` stderr warning | Fresh run; overwritten on commit |
| Wrong container shape (e.g. patterns is dict not list) | `{}` | Fresh run |
| Staleness label ∉ `{FRESH,STALE,GHOST}` | `{}` | Fresh run |
| v1-valid but `snapshot_id` mismatch | `{}` | Fresh run; envelope overwritten with new `snapshot_id` on first commit |
| v1-valid + matching `snapshot_id` | full envelope dict | Per-pass skip gate — only missing passes run; previously written pass values preserved |

## D-01 Pass Order (Locked After Plan 03)

```
description  →  patterns  →  community  →  staleness
  (budget)     (budget)     (budget)     (compute-only, D-03 exempt)
```

Each LLM pass goes through the resume-skip gate (`if pass_name in existing_passes: skipped`); staleness follows the same gate pattern but runs with zero tokens, zero LLM calls, and no budget check.

## Deviations from Plan

None — plan executed exactly as written. Minor clarifications applied:

- Plan 02 had a version of `_load_existing_enrichment` that only did `version == 1 AND snapshot_id ==`; Plan 03 replaces it with the full schema-guarded version as specified in the plan's `<interfaces>`.
- Used `graphify.cache.file_hash` in the FRESH fixture of `test_staleness_pass_classifies_fresh_stale_ghost` (the staleness hash includes the resolved path, per `cache.file_hash`), so a naïve `hashlib.sha256(bytes).hexdigest()` would falsely report STALE. Correct hash source surfaced from reading `graphify/cache.py`.

## Tests Added (6 new, 18 total in test_enrich.py)

1. `test_staleness_pass_no_llm_calls` — monkeypatches `_call_llm` to raise; asserts zero invocations and `(tokens, calls) == (0, 0)`.
2. `test_staleness_pass_classifies_fresh_stale_ghost` — constructs three on-disk fixture files (FRESH hash match, STALE hash mismatch, GHOST file missing) and asserts exact label mapping.
3. `test_resume_same_snapshot_skips_completed_passes` — pre-writes envelope with `description` complete; asserts only `patterns/community/staleness` ran and the pre-written `description` value survives unmodified.
4. `test_resume_diff_snapshot_fresh` — pre-writes envelope with `snapshot_id="s_old"`; pins `"s_new"`; asserts `_load_existing_enrichment` returns `{}`, all 4 passes run, and envelope `snapshot_id` is overwritten.
5. `test_enrichment_envelope_version_one` — full 4-pass run; asserts envelope keys are `{version=1, snapshot_id, generated_at, passes: {description, patterns, community, staleness}}` and round-trips through `_validate_enrichment_envelope`.
6. `test_malformed_envelope_discarded` — version 2, wrong-shape, not-even-JSON, mismatched snapshot_id all return `{}`; positive control confirms matching envelope returns full dict; stderr warning captured for version mismatch.

## Threat Mitigations Applied (from PLAN threat register)

- **T-15-01 (tampered envelope):** `_validate_enrichment_envelope` rejects malformed shapes → `_load_existing_enrichment` returns `{}` → caller runs fresh; prior (possibly tampered) envelope is overwritten on first successful commit.
- **T-15-05 (spoofed staleness label):** `_run_staleness_pass` enum-filters to `{FRESH, STALE, GHOST}` at produce time; `_validate_enrichment_envelope` re-enforces at load time. Labels outside this set are dropped with a stderr warning.
- **T-15-02 (graph.json mutation):** Acceptance grep proves no `to_json` / `_write_graph_json` references in `graphify/enrich.py`; the pass returns a dict and the orchestrator writes via `_commit_pass` → `enrichment.json` only.

## Open Items Handed Forward

- **Plan 04 (`graphify/serve.py` overlay merge):** Implement `_load_enrichment_overlay(out_dir) -> dict` that calls `_load_existing_enrichment` (or equivalent), pins the current on-disk `graph.json`'s active snapshot, and merges enrichment values into the subgraph/BFS results exposed over MCP. Consume the locked v1 shape documented above — do not re-validate, just trust `_validate_enrichment_envelope`'s gate.
- **Plan 06 (integration / `--dry-run`):** Add a schema regression test that loads a pinned v1 envelope fixture from `tests/fixtures/enrichment_v1.json` and asserts `_validate_enrichment_envelope(data) is True`. Also add the `--dry-run` top-level summary (tokens / calls / per-pass count) that reads the envelope but does not trigger LLM paths.

## Self-Check: PASSED

- [x] `graphify/enrich.py` exists, 800 lines (≤ ~800 LOC budget met at boundary)
- [x] `grep -q "def _run_staleness_pass" graphify/enrich.py` ✓
- [x] `grep -q "def _load_existing_enrichment" graphify/enrich.py` ✓
- [x] `grep -q "def _validate_enrichment_envelope" graphify/enrich.py` ✓
- [x] `grep -q "from graphify.delta import classify_staleness" graphify/enrich.py` ✓
- [x] `grep -q "return results, 0, 0" graphify/enrich.py` ✓ (D-03 compute-only literal)
- [x] `grep -qE "to_json|_write_graph_json" graphify/enrich.py` returns non-zero ✓ (SC-5)
- [x] `pytest tests/test_enrich.py -q` → 18/18 pass ✓
- [x] `pytest tests/ -q` → 1347 pass, 0 fail ✓
- [x] Commits exist: RED `c6bcdb9`, GREEN `5b9ae91` ✓
