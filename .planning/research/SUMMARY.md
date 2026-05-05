# Project Research Summary

**Project:** graphify v1.13 — Concept Intelligence & Audit Closure
**Domain:** Knowledge-graph CLI / refinement milestone on mature concept↔code system (v1.10–v1.12)
**Researched:** 2026-05-05
**Confidence:** HIGH

## Executive Summary

graphify v1.13 is a **refinement milestone**, not a greenfield build. The concept↔code edge system shipped across v1.10–v1.12 already covers the hard architectural lifting (LLM-driven concept extraction, vault adapter, routing audit, Nyquist sampling). v1.13 layers five focused improvements: per-edge LLM confidence scores, deterministic cross-repo federation, drift detection, parametrized vault queries, and audit closure (Nyquist gap-fill, stderr sweep, seed traceability). All four research dimensions converge: this is best built **with zero new dependencies**, leveraging the existing stdlib + heuristics + cache + validate stack.

The recommended approach follows a strict 5-phase build order — **S1 (parametrized vault queries) → V1 (vault Option B layout) → E1 (per-edge confidence + cache namespace split) → B1 (federation, blocked on E1) → D1 (drift, blocked on E1+B1)** — with two new modules (`federate.py`, `drift.py`) added to the pipeline. Audit closure runs in parallel as an independent track but blocks SHIP. All four research dimensions agree that **per-edge LLM confidence is simultaneously the load-bearing primitive AND the highest-risk surface**: federation cross-repo merging, drift scoring, and calibration self-check all anchor on it, while its cache invalidation, schema migration, and prompt-version coupling are where regressions hide.

Key risks center on schema compatibility ("optional on read, required on write" + `schema_version` field + legacy fixture), cache namespace separation (a SECOND cache keyed on `prompt_version + model` to prevent stale confidence scores poisoning re-runs), federation determinism (namespace-by-default, multi-signal evidence before any cross-repo merge — no embeddings), drift anchoring on community membership Jaccard (not unstable community names/IDs), and the stderr sweep audit (7 platform skill files regex-parse stderr — any reformatting silently breaks downstream agents).

## Key Findings

### Recommended Stack

Zero new runtime dependencies. v1.13 fits cleanly inside the existing stack: stdlib (`json`, `hashlib`, `pathlib`), NetworkX, optional PyYAML (already present for routing), tree-sitter (unchanged), and the existing Claude API path for LLM confidence. No `sentence-transformers`, no embeddings, no vector store. See `STACK.md`.

**Core technologies:**
- **stdlib only for federation/drift** — `federate.py` and `drift.py` are pure Python; deterministic merging via id-namespacing + multi-signal evidence
- **Existing cache (`graphify/cache.py`)** — split into a SECOND namespace keyed on `prompt_version + model`
- **Existing validate.py + schema_version field** — schema-compat strategy is "optional on read, required on write" with a frozen legacy fixture in tests
- **Existing security.py path confinement** — federation manifests stay inside `graphify-out/`

### Expected Features

7 table stakes, 6 differentiators, 6 explicit anti-features. See `FEATURES.md`.

**Must have (table stakes):**
- Per-edge LLM `confidence_score` written by extractors (E1)
- Cache namespace split keyed on `prompt_version + model` (E1)
- Parametrized vault Dataview queries (S1)
- Vault Option B layout migration with backward-compat reads (V1)
- Schema-compat: `schema_version` field + legacy fixture + "optional on read, required on write" (E1)
- Nyquist audit gap-fill + stderr sweep + seed traceability (Audit closure)
- Calibration self-check harness (D-4) wired as test for C-2

**Should have (competitive):**
- Deterministic cross-repo federation (B1) — namespace-by-default, multi-signal evidence merge
- Drift detection anchored on community membership Jaccard (D1)
- Federation manifest format suitable for future agent consumption
- Drift report surfacing in GRAPH_REPORT.md
- Per-edge confidence visible in HTML viz tooltip
- Audit traceability: every shipped artifact links to seed SHA

**Defer / anti-features (explicitly out of scope):**
- Embedding-based similarity (anti-feature — violates "deterministic, no embeddings")
- Auto-merging across repos without multi-signal evidence
- Drift remediation / auto-fix (read-only signal only in v1.13)
- LLM-based federation arbitration (deterministic only)
- Cross-vault profile inheritance
- Real-time drift watcher (offline batch only)

### Architecture Approach

5-phase build order with strict dependencies. Two new modules slot into the existing pipeline between `analyze.py` and `report.py`. See `ARCHITECTURE.md`.

**Major components:**
1. **S1 — Parametrized vault queries** (`vault/profile.py` extension) — Dataview thresholds become profile params
2. **V1 — Vault Option B layout** (vault adapter migration) — backward-compat read of legacy paths; new writes use Option B
3. **E1 — Per-edge confidence + cache split** (`extract.py` + `cache.py` + `validate.py`) — load-bearing; blocks B1 and D1
4. **B1 — Federation** (NEW `federate.py`) — deterministic id-namespacing, multi-signal merge evidence, manifest output
5. **D1 — Drift detection** (NEW `drift.py`) — community-membership Jaccard between snapshots; surfaces in `report.py`

Plus parallel **Audit Closure track**: Nyquist gap-fill, stderr format sweep across 7 platform skills, seed-SHA traceability. Independent of engineering, blocks SHIP.

### Critical Pitfalls

1. **Stale per-edge confidence from prompt drift** — Mitigation: SECOND cache namespace keyed on `prompt_version + model`; bumping prompt_version forces re-score.
2. **Schema-break on read of pre-v1.13 graphs** — Mitigation: "optional on read, required on write" + `schema_version` field + frozen legacy fixture.
3. **Federation false-merges across repos** — Mitigation: namespace-by-default (`{repo}::{id}`), require multi-signal evidence (label + neighborhood + source path); no embeddings.
4. **Drift anchored on volatile community names** — Mitigation: anchor drift on **membership Jaccard between snapshots**, not on community-id equality.
5. **stderr sweep silently breaking 7 platform skills** — Mitigation: freeze stderr format as contract; add stderr-format snapshot test before any reformatting.

## Implications for Roadmap

### Phase S1: Parametrized Vault Queries
**Rationale:** Lowest-risk, no dependencies, unblocks vault-side validation in parallel.
**Delivers:** Profile schema extension, parametrized templates, backward-compat for unset params
**Addresses:** Table-stakes parametrized queries
**Avoids:** Layout churn while query thresholds are also moving

### Phase V1: Vault Option B Layout Migration
**Rationale:** Independent of E1/B1/D1; best done before federation introduces multi-repo manifests.
**Delivers:** Vault adapter writes Option B; reads still tolerate legacy layout
**Implements:** V1 component

### Phase E1: Per-Edge Confidence + Cache Namespace Split
**Rationale:** Load-bearing. Blocks B1 and D1. Schema-compat must land here.
**Delivers:** `confidence_score` on every LLM-inferred edge, cache keyed on `prompt_version + model`, `schema_version` field, legacy fixture, calibration self-check (D-4)
**Avoids:** Pitfalls #1 (stale confidence) and #2 (schema break)

### Phase B1: Cross-Repo Federation
**Rationale:** Blocked on E1 (needs reliable per-edge confidence to weight merge evidence). Deterministic, no embeddings.
**Delivers:** `federate.py`, namespaced manifest format, multi-signal merge logic, federation report section
**Avoids:** Pitfall #3 (false-merges across repos)

### Phase D1: Drift Detection
**Rationale:** Blocked on E1+B1. Most useful once confidence is per-edge and federation provides cross-repo baseline.
**Delivers:** `drift.py`, community-membership Jaccard, drift section in GRAPH_REPORT.md
**Avoids:** Pitfall #4 (volatile community names)

### Phase A1: Audit Closure (parallel track)
**Rationale:** Independent of engineering work but blocks SHIP.
**Delivers:** Nyquist gap-fill, stderr format snapshot test + sweep, seed-SHA traceability
**Avoids:** Pitfall #5 (stderr regression breaking 7 platform skills)

### Phase Ordering Rationale

- **S1 → V1 → E1 → B1 → D1** is enforced by data dependencies: federation and drift both require per-edge confidence (E1); B1 outputs become a baseline drift candidate for D1.
- **Audit closure runs in parallel** because it touches docs, tests, and stderr format — orthogonal to pipeline modules.
- **Two new modules only** (`federate.py`, `drift.py`) keeps the architectural footprint small and aligned with graphify's "single function per stage" pattern.
- **Convergence across all 4 dimensions:** Stack ("no embeddings"), Features ("deterministic federation"), Architecture ("E1 blocks B1+D1"), and Pitfalls ("namespace-by-default, multi-signal merge") all point to the same implementation shape.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase B1 (Federation):** Manifest format and multi-signal evidence threshold — no in-repo precedent.
- **Phase D1 (Drift):** Jaccard threshold tuning + report rendering; reuse D-4 calibration harness.
- **Phase A1 (stderr sweep):** Audit all 7 platform skill files to enumerate the regex contract before format changes.

Phases with standard patterns (skip research-phase):
- **Phase S1:** Profile param extension follows established `profile.py` patterns.
- **Phase V1:** Vault adapter migration follows v1.7 layout-change playbook.
- **Phase E1:** Schema-compat + cache namespace split are well-known mechanical patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps; everything fits existing stack verified across v1.10–v1.12 |
| Features | HIGH | 7/6/6 explicitly mapped; D-4 already provides test harness for C-2 |
| Architecture | HIGH | 5-phase DAG with clear dependencies; only 2 new modules |
| Pitfalls | HIGH | Each top-5 pitfall has a concrete mitigation endorsed independently by all 4 dimensions |

**Overall confidence:** HIGH

### Gaps to Address

- **Federation manifest schema** — needs a concrete spec during B1 planning; flag for research-phase before B1.
- **Drift Jaccard threshold** — needs empirical tuning against existing v1.10–v1.12 graph snapshots; flag during D1 planning.
- **stderr contract enumeration** — exact regex patterns parsed by each of the 7 platform skill files must be enumerated before A1 sweep.
- **Calibration self-check (D-4) wiring** — confirmed as test harness for C-2; mechanical hookup point in `tests/` to be picked during E1 planning.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md`
- `.planning/research/FEATURES.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`
- `.planning/PROJECT.md` (v1.13 milestone block + Seed Status)
- v1.10–v1.12 shipped milestones — concept↔code edge baseline, routing audit, Nyquist sampling

### Secondary (MEDIUM confidence)
- v1.7 vault adapter migration playbook — pattern for V1 layout change
- Existing `graphify/cache.py` design — pattern for second namespace keyed on `prompt_version + model`
- Existing `graphify/validate.py` schema enforcement — extension point for `schema_version` field

### Tertiary (LOW confidence)
- Federation manifest format — no in-repo precedent; needs research-phase before B1
- Drift Jaccard threshold — needs empirical tuning against historical snapshots

---
*Research completed: 2026-05-05*
*Ready for roadmap: yes*
