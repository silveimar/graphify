# Milestone v2.0 — Project Summary

**Generated:** 2026-05-12
**Milestone:** v2.0 "Graph Schema Deepening"
**Status:** Shipped (Archived 2026-05-12)
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**graphify** is a Claude Code skill backed by a Python CLI library that turns any input (code, docs, papers, images) into a clustered knowledge graph with HTML + JSON + audit-report outputs and an optional Obsidian-vault adapter. The pipeline is `detect() → extract() → build_graph() → cluster() → analyze() → report() → export()`, with deterministic tree-sitter AST extraction for code and LLM-based semantic extraction for docs.

**v2.0 in one sentence:** A major-version graph schema upgrade that adds **temporal edge validity** and **typed reasoning relations** to the graph data model, measures (but defers) content-fingerprint dedup, fixes the carryover vault-CWD argparse defect, and ships the coordinated `graphifyy 2.0.0` PyPI bump — all while preserving backward-compatible read of legacy `graph.json`.

**Cycle:** 2026-05-07 → 2026-05-12 (5 days, 5 phases, 15 plans).

**Hard non-goals (decisions, not omissions):**
- No embeddings — Leiden topology-only clustering remains the design.
- No Postgres / Supabase backend — filesystem JSON + optional Neo4j export stays.
- No OB1 integration — deferred to `SEED-ob1-recipe-repo-graphify`.

## 2. Architecture & Technical Decisions

- **Two distinct version strings, by design.**
  - **Why:** Schema-version follows MAJOR.MINOR (`SCHEMA_VERSION = "2.0"` in `build.py:113`); PyPI package follows full semver (`graphifyy 2.0.0`). The split was set as precedent in v1.13 CCONF and re-confirmed here.
  - **Phase:** 75-PKG + integration check 4.

- **INFERRED-only supersession stamping.**
  - **Why:** Only LLM-derived edges decay and get historical stamps. EXTRACTED structural edges (AST-found) are treated as ground truth with `decay_weight = 1.0` and no `valid_until` churn — preventing legitimate `imports`/`calls` from being marked stale across cache runs.
  - **Phase:** 71-TEMP (`temporal.py::stamp_supersessions`, wired in `build.py:31`).

- **4-site analyze filter for superseded edges — but `contradictions_and_chains` deliberately doesn't filter.**
  - **Why:** God-node, surprising-connection, cross-community, and suggested-question scoring (4 sites) skip `valid_until is not None` so historical edges don't inflate scores. The 5th analysis site — `contradictions_and_chains` — *intentionally* surfaces superseded relations because its contract IS the supersession chain history (REAS-03).
  - **Phase:** 71-04 (filter), 72-04 (intentional exemption).

- **Reasoning relations are a typed-relation extension, not a separate edge collection.**
  - **Why:** Five new relations (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`) live in the same edge schema, validated by a `REASONING_RELATIONS` frozenset in `validate.py:72-77`. Rejected on `file_type == "code"` endpoints so code-graph semantics stay structural-only.
  - **Phase:** 72-01.

- **Prompt versioning as cache key.**
  - **Why:** `PROMPT_VERSION` in `graphify/prompts.py:10` bumped to `1.14.0` to invalidate cached extractions across all 10 platform skill markdown files when the reasoning-relation taxonomy was added. A drift-gate test (`tests/test_skill_prompt_drift.py`) keeps the 10 skill variants in lockstep.
  - **Phase:** 72-02.

- **Measurement-only spike for dedup (gated implementation).**
  - **Why:** Avoid building speculative dedup machinery. Phase 73 ran a SHA-256 fingerprint spike across a code repo + doc-heavy corpus, measured **18.78%** aggregate near-duplicate concept-node rate, and issued a *ship recommendation*; actual dedup implementation is deferred to a future milestone activated by this signal.
  - **Phase:** 73-DEDUP.

- **Two-atomic-commit topology for the version bump (D6).**
  - **Why:** A version bump touches code (`pyproject.toml`, `server.json`) and docs (release-stamp records) — separating them into `chore(75):` then `docs(75):` keeps blame clean and lets the docs commit be redone without re-bumping.
  - **Phase:** 75-02.

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 71 | TEMP — Temporal edge validity | Complete | `valid_from`/`valid_until`/`decay_weight` on every edge + 4-site analyze filter + Temporal Health report section |
| 72 | REAS — Reasoning-relation edge types | Complete | Five typed relations on doc/concept nodes + ADR-aware extraction prompts + contradiction/supersession analysis |
| 73 | DEDUP — Measurement-only dedup spike | Complete | 18.78% near-dup rate measured; ship recommendation issued; implementation deferred |
| 74 | VBUG — Vault-CWD argparse fix | Complete | `update-vault`/`vault-promote` no longer exit-2 when run from vault CWD without `--vault`; 14-branch regression suite |
| 75 | PKG — graphifyy 2.0.0 PyPI bump | Complete | Coordinated version stamp across `pyproject.toml`, `server.json` (hash `1bc87657…`), and 12 platform skill stamps |

## 4. Requirements Coverage

Audit verdict: **`passed`** — 13/13 requirements SATISFIED, 5/5 cross-phase integration checks WIRED (see `.planning/milestones/v2.0-MILESTONE-AUDIT.md`).

- ✅ **TEMP-01..04** — Temporal columns, decay weights, supersession stamping, Temporal Health rendering (Phase 71)
- ✅ **REAS-01..04** — Validator taxonomy, skill-prompt extension, contradictions/chains analysis, typed Obsidian frontmatter (Phase 72)
- ✅ **DEDUP-01** — Spike measured (18.78%), ship recommendation issued, `Q-2026-05-07-01` resolved (Phase 73)
- ✅ **VBUG-01/02** — Argparse fix uniform across gated commands, 14-branch regression suite, debug session flipped to `resolved` (Phase 74)
- ✅ **PKG-01/02** — `graphifyy 2.0.0`, `server.json` manifest hash synced, `.graphify_version` stamps refreshed, CI matrix gate via D3 CI-as-contract (Phase 75)

## 5. Key Decisions Log

| ID | Decision | Phase |
|----|----------|-------|
| D-71.x | Run-now ISO timestamp as single clock per build | 71-02 |
| D-71.x | `setdefault` preserves prior `valid_from` across re-runs | 71-02 |
| D-71.x | `edge_subgraph` view with degree fallback for isolates | 71-03 |
| D-72.03/06 | INFERRED reasoning edges require `confidence_score ∈ [0,1]` | 72-01 |
| D-72.05 | Code-endpoint rejection only in `validate_extraction` (write path); read path stays permissive for legacy graphs | 72-01 |
| D-04 | Substring fallback uses lex-sorted candidates for determinism | 72-03 |
| D-07 | `supersedes` edge target is the SUPERSEDED node (newer→older orientation) | 72-03 |
| D-09 | Idempotent supersession stamp via `if e.get("valid_until") is None` guard | 72-03 |
| D-13 | `knowledge_gaps` exempts nodes with reasoning edges from "isolated" classification | 72-04 |
| D-15 | Obsidian frontmatter renders reasoning relations as typed YAML list (distinguishable from structural) | 72-04 |
| D-02 | Dedup spike methodology recipe locked (SHA-256 fingerprint of normalized labels) | 73-CONTEXT |
| 74-VBUG | Chose `required=False` + tightened post-parse guard over the alternative "inject `--vault <cwd>` before parse" approach | 74-01 |
| D6 | Two-atomic-commit topology for version bump (`chore:` then `docs:`) | 75-02 |

## 6. Tech Debt & Deferred Items

Active follow-ups (from `v2.0-MILESTONE-AUDIT.md` and ROADMAP "Deferred"):

1. **Git tag `v2.0.0`** + PyPI publish via twine — D7, human-supervised post-archive (not yet tagged).
2. **CI matrix gate** — Local pytest had an env-leak red signal; relied on D3 CI-as-contract for Python 3.10/3.12 acceptance. A dedicated "test-triage" phase is owed.
3. **REAS-02 prompt content** — Drift-gate test (`tests/test_skill_prompt_drift.py`) is the contract; not re-executed in the audit.
4. **REAS-03 superseded-edge inclusion** — Intentional today; if future intent shifts to "current-only contradictions", add a 5th-site `valid_until is None` filter.
5. **CLAUDE.md doc fix** — Carryover doc-debt: `mcp/server.json` → `server.json` reference. Future docs phase.
6. **`test_vault_cwd_gate` env leak** — Subprocesses auto-adopt the real vault during tests; future test-hygiene phase.

Deferred to future milestones (per ROADMAP):

- **OB1-RECIPE-01..04** — Ship graphify as `recipes/repo-graphify` for OB1 (seed).
- **MCP-ALIGN-01..02** — Align `serve.py` with ob-graph's 10-tool surface.
- **DEDUP-02..N** — Implement node-level dedup (activated by 73's positive spike).

## 7. Getting Started

- **Install:** `pip install -e ".[all]"` (or `.[mcp,pdf,watch]` to match CI).
- **Verify CLI:** `graphify --help` and `graphify --version` (should report `2.0.0`).
- **Run tests:** `pytest tests/ -q` (CI runs on Python 3.10 and 3.12).
- **Run the pipeline on a corpus:** `graphify run <path>` then inspect `graphify-out/GRAPH_REPORT.md`.
- **Key directories:**
  - `graphify/` — pipeline modules, one per stage (`detect.py`, `extract.py`, `build.py`, `cluster.py`, `analyze.py`, `report.py`, `export.py`).
  - `graphify/temporal.py` — **new in v2.0**: decay-weight + supersession stamping.
  - `graphify/prompts.py` — `PROMPT_VERSION` (cache-invalidation lever).
  - `graphify/validate.py` — schema enforcement; `REASONING_RELATIONS` lives here.
  - `tests/` — one test file per module + `tests/fixtures/graph_legacy_v113.json` (legacy back-compat fixture) + `tests/fixtures/graph_temporal_v20.json`.
  - `docs/RELATIONS.md` — relation taxonomy (now includes reasoning relations).
  - `.planning/milestones/v2.0-*` — ROADMAP, REQUIREMENTS, MILESTONE-AUDIT for this cycle.
- **Where to look first if extending the schema:** `validate.py` (taxonomy & write/read split) → `build.py` (edge stamping) → `analyze.py` (consumption sites) → `report.py`/`wiki.py`/`export.py` (rendering).

---

## Stats

- **Timeline:** 2026-05-07 → 2026-05-12 (5 days)
- **Phases:** 5 / 5 complete (Phases 71–75)
- **Plans:** 15 / 15 complete
- **Commits (milestone window):** ~67–72 (ROADMAP records 72; `git log --since=2026-05-07` reports 67)
- **Files changed:** 224 (+10,241 / −21,650 — deletions inflated by v1.13 archive cleanup during the cycle)
- **Contributors:** silveimar
- **Audit:** `passed` (13/13 requirements, 5/5 integration)
