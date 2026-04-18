# Phase 12 — Technical Research

**Phase:** 12 — Heterogeneous Extraction Routing  
**Question:** What do we need to know to plan this phase well?

## RESEARCH COMPLETE

### Current architecture (verified)

- **`graphify/extract.py::extract(paths)`** — AST-only structural extraction; uses `load_cached` / `save_cached` from `cache.py` with keys derived from `file_hash()` (content + resolved path). No LLM calls in Python today.
- **Semantic extraction** — Orchestrated entirely in **`graphify/skill.md`** (Step 3B): subagents per `batch.cluster_files()` cluster; **`check_semantic_cache`** / **`save_semantic_cache`** use the same cache filenames as AST cache (`file_hash` only) today — **model_id isolation (ROUTE-04) requires extending both AST and semantic cache paths**.
- **`graphify/batch.py::cluster_files`** — Returns clusters with `files` lists; Phase 12 CONTEXT D-01: **single batch LLM call uses max tier** across member files; **routing.json** still records **per-file** classification + model choice.
- **`graphify/dedup.py::write_dedup_reports`** — Template for atomic JSON + markdown sidecars under `graphify-out/`.
- **CLI** — No `graphify run` subcommand yet (`__main__.py` ends with `unknown command` for unlisted verbs). Success criteria and CONTEXT require **`graphify run --router`** (opt-in).

### Architectural gap (ROUTE-03 vs today)

ROUTE-03 requires `extract(..., router=...)`, **ThreadPoolExecutor** for LLM fan-out, and **semaphore + 429 Event** (ROUTE-07). The repo has **no** first-party HTTP LLM client in library code; semantic work runs via **agent subagents** in the skill.

**Planning stance:** Phase 12 delivers **router types, YAML config, cache keying, routing.json, rate-limit primitives, and programmatic hooks**. Implement **either** (a) a minimal **`LLMBackend` protocol** + default **no-op/test stub** so `ThreadPoolExecutor` runs real parallelism in tests with injectable backends, **or** (b) thin HTTP client behind optional extra — **executor chooses** based on `pyproject.toml` constraints. **Skill.md** must be updated so Step 3B **respects router classification** (max-tier cluster rule, `model_id` in cache checks, `routing.json` emission) even when LLM remains agent-driven.

### Dependencies

- **`radon`** — ROUTE-01 names cyclomatic complexity for Python; add as optional extra or soft-import with documented fallback (tree-sitter metrics always available).
- **`yaml.safe_load`** — Already required by project invariants for user config; **`routing_models.yaml`** follows harness_schemas pattern.

### Cache backward compatibility (ROUTE-04)

- **`file_hash(path, model_id="")`** → `hexdigest + ":" + model_id` (REQ verbatim). Callers omitting `model_id` get legacy `":''"` suffix **or** preserve exact legacy string for empty model_id — **planner locks one rule** in Plan 02 to avoid double-invalidating all caches.

### Validation Architecture (Nyquist)

- **Dimension 8 — extraction correctness:** Router must not downgrade code files below mid-tier (ROUTE-06); **unit tests** with synthetic metrics YAML.
- **Dimension 7 — resilience:** ROUTE-07 **threading.Semaphore** + **threading.Event** for 429 — **integration-style test** with mock provider raising 429.
- **Dimension 6 — observability:** `routing.json` schema version field + atomic write — **grep/JSON parse tests**.

---

## Recommendations for planner

1. **Six plans** in four waves: foundation (routing + yaml) → cache → extract integration + parallelism → sidecars → P2 (canary + cost) → CLI + skill + tests.
2. **Threat model:** Path writes only via `validate_graph_path` for outputs; YAML from repo root only `yaml.safe_load`; no secrets in `routing_models.yaml` (endpoints are references, not API keys).

## Open items for execution (not blockers for planning)

- Exact **`routing.json` JSON Schema** version string (CONTEXT defers to implementation).
- Canary failure: **stderr warning vs non-zero exit** — default **warning** per CONTEXT unless REQ tightened.
