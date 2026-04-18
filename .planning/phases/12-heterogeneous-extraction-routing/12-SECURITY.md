---
phase: 12
slug: heterogeneous-extraction-routing
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-17
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User YAML → loader | `routing_models.yaml` loaded only via `yaml.safe_load` from package or explicit path; no `eval` | Routing config dict |
| Cache keys | Optional `model_id` participates in semantic cache keys | Model id string (user-influenced via routing) |
| Router concurrency | Shared router limits parallel LLM-shaped work | In-process coordination only |
| Audit / outputs | `routing.json` and cost checks write under project output dirs | JSON metadata, numeric estimates |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-12-01 | Tampering | `graphify/routing.py` — `load_routing_config` | mitigate | `yaml.safe_load` only; non-dict YAML yields safe empty merge | closed |
| T-12-02 | Spoofing / cache poisoning | `graphify/cache.py` — `model_id` in cache keys | mitigate | `_sanitize_model_id` rejects `/`, `\`, `..`, and overlong ids | closed |
| T-12-03 | Denial of Service | `graphify/routing.py` — `Router` | mitigate | `threading.Semaphore` caps concurrency; `threading.Event` backs off on 429 | closed |
| T-12-04 | Path traversal | `graphify/routing_audit.py` — `RoutingAudit.flush` | mitigate | Resolved `out_dir` must be under `cwd` (`relative_to`); atomic write to `routing.json` | closed |
| T-12-05 | Information disclosure | `graphify/routing_cost.py` | mitigate | Cost ceiling errors report estimates and ceiling only (docstring: no file contents) | closed |
| T-12-06 | Injection / unsafe paths | `graphify/__main__.py` — `run`; `graphify/pipeline.py` | mitigate | Target path resolved + existence check; audit output confined as in T-12-04 | closed |

*Status: open · closed*  
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-17 | 6 | 6 | 0 | gsd-secure-phase (manual verification against PLAN threat blocks and code) |

### Evidence (implementation pointers)

- **T-12-01:** `load_routing_config` uses `yaml.safe_load` in `graphify/routing.py`.
- **T-12-02:** `_sanitize_model_id` and `file_hash(..., model_id=...)` in `graphify/cache.py`; covered by `tests/test_cache.py`.
- **T-12-03:** `_semaphore`, `_429_backoff`, `signal_429` / `clear_429` in `graphify/routing.py`.
- **T-12-04:** `RoutingAudit.flush` cwd containment + atomic replace in `graphify/routing_audit.py`; `tests/test_routing_sidecar.py`.
- **T-12-05:** `enforce_cost_ceiling` message shape in `graphify/routing_cost.py`.
- **T-12-06:** `graphify run` path handling in `graphify/__main__.py` (`Path.resolve`, exists check); `run_corpus` in `graphify/pipeline.py`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-17
