---
phase: 12
slug: 12-heterogeneous-extraction-routing
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
updated: 2026-04-17
---

# Phase 12 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (project default) |
| **Quick run command** | `pytest tests/test_routing.py tests/test_cache.py tests/test_extract_router.py tests/test_routing_sidecar.py tests/test_routing_p2.py tests/test_cli_run.py tests/test_route_requirements_smoke.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30–90 seconds (full suite ~40s) |

## Sampling Rate

- **After every task commit:** Run targeted tests for files touched
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite green

## Requirement → Automated Test Map (ROUTE-01..10)

| Requirement | Primary tests | Status |
|-------------|-----------------|--------|
| ROUTE-01 | `tests/test_routing.py` (classification metrics) | COVERED |
| ROUTE-02 | `tests/test_routing.py` (`load_routing_config`, YAML override) | COVERED |
| ROUTE-03 | `tests/test_extract_router.py` (`extract` with/without router) | COVERED |
| ROUTE-04 | `tests/test_cache.py` (`model_id`, semantic cache) | COVERED |
| ROUTE-05 | `tests/test_routing_sidecar.py` (`RoutingAudit.flush`, atomic JSON) | COVERED |
| ROUTE-06 | `tests/test_routing.py` (code floor trivial→simple) | COVERED |
| ROUTE-07 | `tests/test_extract_router.py` (semaphore, 429 event, `GRAPHIFY_EXTRACT_WORKERS`) | COVERED |
| ROUTE-08 | `tests/test_routing_p2.py` (`emit_canary_warning_if_needed`) | COVERED |
| ROUTE-09 | `tests/test_routing_p2.py` (`CostCeilingError`, `enforce_cost_ceiling`) | COVERED |
| ROUTE-10 | `tests/test_routing_p2.py` (image skip when vision `model_id` empty) | COVERED |

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 12-01-01..03 | 01 | 1 | ROUTE-01,02,06,10 | unit | `pytest tests/test_routing.py -q` | COVERED |
| 12-02-01..02 | 02 | 1 | ROUTE-04 | unit | `pytest tests/test_cache.py -q` | COVERED |
| 12-03-01..03 | 03 | 2 | ROUTE-03,07 | unit | `pytest tests/test_extract_router.py -q` | COVERED |
| 12-04-01..02 | 04 | 3 | ROUTE-05 | unit | `pytest tests/test_routing_sidecar.py -q` | COVERED |
| 12-05-01..03 | 05 | 3 | ROUTE-08–10 | unit | `pytest tests/test_routing_p2.py -q` | COVERED |
| 12-06-01..03 | 06 | 4 | ROUTE-03 CLI, D-04 | integration | `pytest tests/test_cli_run.py tests/test_route_requirements_smoke.py -q` | COVERED |

## Wave 0 Requirements

- Existing `tests/conftest.py` reused; Phase 12 adds dedicated test modules under `tests/test_routing*.py`, `test_extract_router.py`, `test_cli_run.py`, `test_route_requirements_smoke.py`.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end `graphify run <repo> --router` with real corpus | Success criteria / cost | Optional live API keys, time | Run on a sample clone; confirm `graphify-out/routing.json` and no regressions |

## Validation Sign-Off

- [x] All ROUTE-01..10 mapped to automated tests or manual row above
- [x] `nyquist_compliant: true` after validation audit

**Approval:** automated Nyquist audit 2026-04-17

## Validation Audit 2026-04-17

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Notes:** `gsd-sdk` was not available in the validation session; audit performed by cross-referencing `tests/` against PLAN requirements and running the Phase 12 pytest bundle (35 tests) and confirming full `pytest tests/` green. No implementation changes required; VALIDATION.md updated from draft to compliant.

**Chain (`--chain`):** Proceed to milestone audit when ready: `/gsd-audit-milestone` (with your workspace suffix if you use GSD workspaces).
