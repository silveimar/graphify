---
phase: 65-cconf-per-edge-confidence-cache-split-schema-version
verified: 2026-05-06T22:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
---

# Phase 65: CCONF — Per-Edge Confidence + Cache Split + schema_version — Verification Report

**Phase Goal:** Every concept↔code INFERRED edge carries a per-edge LLM-derived `confidence_score` and `evidence`, persisted via a separate cache namespace that prompt-version bumps invalidate cleanly, with backward-compat reads of pre-v1.13 graphs.

**Verified:** 2026-05-06
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap SCs + executor checklist)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CCONF-05: read/write validation split + `schema_version` emit + legacy v1.12 fixture passes read | VERIFIED | `graphify/validate.py:245` `validate_extraction_for_read`, `:250` `validate_extraction_for_write`; `graphify/export.py:329-332` stamps `schema_version` (defaults `"1.13"`, defers to `G.graph["schema_version"]`); `tests/fixtures/legacy_v1_12_graph.json` exists (no `schema_version` key); 5 tests in `tests/test_validate.py` + `tests/test_export.py` green |
| 2 | CCONF-01/02: INFERRED concept↔code edges in extract.py emit `confidence_score` + `evidence` via skill-orchestrated scoring path (no Python LLM SDK) | VERIFIED | `graphify/extract.py:34` `score_concept_code_edges_for_file` hook; `:26` `_finalize_evidence`; `:2305-2325` per-batch scoring + clamp + sanitize wired at end of `_resolve_cross_file_imports` before `return new_edges`; default fallback `(0.5, "")` keeps pipeline pure when skill absent (Q1, CLAUDE.md no-new-deps); 5 tests in `tests/test_extract_confidence.py` green |
| 3 | CCONF-03 / Q6: confidence cache is a separate namespace; AST cache byte-untouched on prompt_version/model_id changes | VERIFIED | `graphify/cache.py:113` `_sanitize_prompt_version`, `:129` `_confidence_cache_key` (sha256 over NUL-joined components), `:141` `confidence_cache_dir` (`graphify-out/cache/confidence/`), `:148` `load_confidence`, `:175` `save_confidence`. Helpers call `file_hash(path, model_id="")` so model_id participates only via key, leaving AST namespace orthogonal. 7 tests in `tests/test_confidence_cache.py` green (incl. AST-cache byte-untouched assertion) |
| 4 | Q4: prompt-version drift gate covers all shipped skill files | VERIFIED | `tests/test_skill_prompt_drift.py` parametrizes over `Path("graphify").glob("skill*.md")` — stricter superset of plan's 7-file requirement. All 10 shipped skill files contain `1.13.0` (verified by `grep -c "1.13.0"` returning ≥1 per file). |
| 5 | CCONF-04: GRAPH_REPORT.md gains 10-bin histogram + 3 flag rules; n<10 skip path; skewed fixture fires `mode_collapse` | VERIFIED | `graphify/report.py:12-15` four threshold constants; `:18` `_calibration_histogram` (10 bins, clamp at bin 9 for s=1.0); `:27` `_calibration_flags` (mode_collapse / refusal / no_negatives); `:175-204` `## Calibration` rendering block with n<10 skip line and post-merge note. `tests/fixtures/skewed_distribution.json` (10 INFERRED edges all in [0.80,0.90)) fires `mode_collapse`. 6 tests in `tests/test_report_calibration.py` green |
| 6 | Constraints: no new required deps; Phase 53 `_normalize_concept_code_edges` invariant intact; Phase 64 stderr contract intact | VERIFIED | `git log a554fa5..HEAD -- pyproject.toml` empty (no diff). `graphify/build.py:116` `_normalize_concept_code_edges` present, untouched (`git log a554fa5..HEAD -- graphify/build.py` empty). No new prints introduced by Phase 65 changes (default no-op scorer is silent); full stderr-snapshot suite (Phase 64) remains green. |
| 7 | Test suite: `pytest tests/ -q` clean modulo documented pre-existing failure | VERIFIED | Full run: **2318 passed, 1 xfailed, 1 failed in 150.59s**. The single failure is `tests/test_migration.py::test_preview_expands_risky_action_rows`, pre-existing on `main` and explicitly logged in `deferred-items.md` as out-of-scope for CCONF. All 75 phase-65-specific tests pass (`tests/test_validate.py + test_export.py + test_confidence_cache.py + test_extract_confidence.py + test_skill_prompt_drift.py + test_report_calibration.py`). |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `graphify/validate.py` | read/write split functions | VERIFIED | Both functions present at lines 245 / 250 |
| `graphify/export.py` | `schema_version` emit | VERIFIED | Line 332 stamps version with G.graph round-trip |
| `graphify/prompts.py` | new module with PROMPT_VERSION + template | VERIFIED | `PROMPT_VERSION = "1.13.0"` (line 10), `SCORING_PROMPT_TEMPLATE` (line 12) |
| `graphify/cache.py` | 5 confidence helpers | VERIFIED | All 5 symbols present (sanitize, key, dir, load, save) |
| `graphify/extract.py` | scoring hook + evidence sanitizer + wiring | VERIFIED | Hook + finalizer at module top, batch scoring wired before return in `_resolve_cross_file_imports` |
| `graphify/report.py` | calibration constants + helpers + render block | VERIFIED | 4 thresholds + 2 helpers + `## Calibration` section |
| `tests/fixtures/legacy_v1_12_graph.json` | frozen v1.12 graph (no schema_version) | VERIFIED | Exists, no `schema_version` key (real v1.12 tag output, not synthetic) |
| `tests/fixtures/skewed_distribution.json` | 10 INFERRED edges, mode-collapse trigger | VERIFIED | Loaded by `test_mode_collapse_flag_fires`, fires flag |
| `graphify/skill*.md` (10 files) | each references PROMPT_VERSION | VERIFIED | All 10 contain `1.13.0` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_resolve_cross_file_imports` (extract.py) | scoring hook | `score_concept_code_edges_for_file(path, batch)` call at line 2305 | WIRED | Result clamped + assigned to `edge["confidence_score"]` and `edge["evidence"]` |
| extract.py | prompts.py | `from .prompts import PROMPT_VERSION` at line 17 | WIRED | Import succeeds; used by drift gate test indirectly via skill files |
| cache.py | confidence cache namespace | `confidence_cache_dir(root)` returns `graphify-out/cache/confidence/` | WIRED | Both load/save use this; AST cache uses separate `cache_dir(root)` |
| report.py | calibration block | `## Calibration` rendered after Summary, before Community Hubs | WIRED | Renders unconditionally for INFERRED-bearing graphs; n<10 emits skip line |
| skill drift test | shipped skill files | `Path("graphify").glob("skill*.md")` parametrize | WIRED | Stricter than plan-stated 7 — covers all 10 shipped files |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase-65 specific tests pass | `pytest tests/test_validate.py tests/test_export.py tests/test_confidence_cache.py tests/test_extract_confidence.py tests/test_skill_prompt_drift.py tests/test_report_calibration.py -q` | 75 passed | PASS |
| Full suite green (modulo deferred) | `pytest tests/ -q` | 2318 passed, 1 xfailed, 1 pre-existing failure (logged) | PASS |
| Every shipped skill references PROMPT_VERSION | `for f in graphify/skill*.md; do grep -c "1.13.0" "$f"; done` | All ≥1 | PASS |
| Legacy fixture has no schema_version | `grep -c '"schema_version"' tests/fixtures/legacy_v1_12_graph.json` | 0 | PASS |
| build.py untouched (Phase 53) | `git log a554fa5..HEAD -- graphify/build.py` | empty | PASS |
| pyproject.toml untouched (no new deps) | `git log a554fa5..HEAD -- pyproject.toml` | empty | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CCONF-01 | 65-02 | Per-edge LLM-derived confidence_score | SATISFIED | `extract.py:2305-2325` scoring path; `_finalize_evidence` + clamp |
| CCONF-02 | 65-02 | `evidence` field on INFERRED edges | SATISFIED | `edge["evidence"] = _finalize_evidence(evidence)` (line 2324) |
| CCONF-03 | 65-02 | Second cache namespace, prompt_version invalidation | SATISFIED | `confidence_cache_dir` + `_confidence_cache_key`; `test_confidence_cache.py` covers AST-untouched + invalidation |
| CCONF-04 | 65-03 | Calibration self-check in GRAPH_REPORT.md | SATISFIED | `## Calibration` block with histogram + 3 flag rules + n<10 skip; skewed fixture fires `mode_collapse` |
| CCONF-05 | 65-01 | schema_version read/write split + legacy backward-compat | SATISFIED | `validate_extraction_for_read/_for_write`; legacy v1.12 fixture passes read; new writes require schema_version |

No orphaned requirements detected.

### Anti-Patterns Found

None of severity. The default scorer fallback `(0.5, "")` is intentional (Q1: skill-orchestrated, no Python LLM SDK per CLAUDE.md). The fallback is documented in summary, gated by a try/except, and unit-tested for shape — it is not a concealed stub but a documented seam awaiting skill-side dispatch (already wired in `graphify/skill*.md`).

### Evidence-cap reconciliation (process note)

`_finalize_evidence` slices to 280 chars then runs `sanitize_label`, which caps at 256 (`_MAX_LABEL_LEN`). Effective on-disk cap is min(280, 256) = 256. Tests assert `len ≤ 280`, satisfied. Documented under "Process note" deviations in 65-02 SUMMARY. Not a goal blocker.

### Human Verification Required

None. All goal criteria are programmatically verifiable and verified.

### Gaps Summary

No gaps. All 4 roadmap success criteria, all 5 requirements (CCONF-01..05), all constraints, and the deferred-items contract are satisfied. The only test-suite failure is the pre-existing `test_migration.py::test_preview_expands_risky_action_rows`, which was triaged on `main` before phase 65, documented in `deferred-items.md`, and explicitly out of scope.

### Roadmap Sync Note (informational, not a gap)

`.planning/ROADMAP.md` line 138 still lists Phase 65 as `0/0 — Not started`, and the per-plan checkboxes at lines 58-60 are unchecked. This is a roadmap-bookkeeping update for the orchestrator/closer, not a goal-achievement issue — every plan summary, commit, and test confirms the work shipped.

---

*Verified: 2026-05-06*
*Verifier: Claude (gsd-verifier)*
