# Phase 65: CCONF — Discussion Log

**Date:** 2026-05-06
**Mode:** default (4 areas selected, multi-question batched per area)

## Areas Selected
User chose all four offered:
1. Scoring source & integration point
2. Confidence cache shape & key
3. schema_version + legacy fixture
4. Calibration check + evidence shape

---

## Area 1 — Scoring source & integration point

| Question | Options presented | Selection |
|----------|-------------------|-----------|
| Where does the per-edge score come from? | Real LLM call (rec) / Heuristic-then-LLM-later / Hybrid heuristic+LLM gate | **Real LLM call** |
| Where in the pipeline does scoring run? | Inside extract.py at concept emission (rec) / Post-build sweep in new score.py / Inside build.py before normalize | **Inside extract.py at concept emission** |
| Per-edge or batched LLM calls? | Batched per source file (rec) / One call per edge / Batched per concept node | **Batched per source file** |

**Notes:** No follow-ups raised. Decisions captured as D-65.01–03.

---

## Area 2 — Confidence cache shape & key

| Question | Options presented | Selection |
|----------|-------------------|-----------|
| Where does the confidence cache live? | `graphify-out/cache/confidence/<sha>.json` (rec) / Same dir prefixed / Separate top-level dir | **`graphify-out/cache/confidence/<sha>.json`** |
| Cache key composition? | sha256(prompt_version‖model‖file_hash) (rec) / Per-edge edge_signature / + concept_set_hash | **sha256(prompt_version‖model‖file_hash)** |
| Where is `prompt_version` defined? | New `graphify/prompts.py` (rec) / Constant in extract.py / Read from pyproject | **New `graphify/prompts.py`** |

**Notes:** Decisions captured as D-65.04–06. `prompts.py` also houses the scoring prompt template.

---

## Area 3 — schema_version + legacy fixture

| Question | Options presented | Selection |
|----------|-------------------|-----------|
| Where does schema_version live? | Top-level JSON + nx.Graph.graph attr (rec) / JSON only / Per-node meta | **Top-level JSON + nx.Graph.graph attr** |
| Value format? | Semver string '1.13' (rec) / Integer / ISO date | **Semver string '1.13'** |
| Legacy fixture source? | Frozen real v1.12 graph.json (rec) / Hand-crafted minimal / Both | **Frozen real v1.12 graph.json** |

**Notes:** Decisions captured as D-65.07–09. Read-vs-write enforcement implemented in validate.py.

---

## Area 4 — Calibration check + evidence shape

| Question | Options presented | Selection |
|----------|-------------------|-----------|
| Calibration granularity? | Histogram + multi-rule flags (rec) / Single roadmap rule / Configurable via profile | **Histogram + multi-rule flags** |
| Threshold configurability? | Hardcoded constants in report.py (rec) / Env vars / profile.yaml | **Hardcoded constants in report.py** |
| Evidence field shape? | Free-text excerpt char-capped + sanitized (rec) / Structured {quote, file, location} / Free-text + optional location | **Free-text excerpt, char-capped + sanitized** |
| Skewed corpus test? | Hand-built fixture + stubbed scorer (rec) / Property-based seeded RNG / Capture from real biased prompt run | **Hand-built fixture + stubbed scorer** |

**Notes:** Decisions captured as D-65.10–13. Three flag rules locked: mode-collapse (>70% in any single bin), refusal-to-decide (>50% at exactly 0.5), no-negatives (<5% below 0.5).

---

## Deferred Ideas
None surfaced. Federation/drift/parameterized-query consumers of `confidence_score` are already scoped to Phases 66–67 by the roadmap.

## Claude's Discretion (planner-owned)
- Exact scoring-prompt wording (research deliverable).
- One-vs-two `validate.py` entry points for read/write modes.
- Choice of fixture corpus that produces the frozen v1.12 graph.json.
- Histogram rendering style in GRAPH_REPORT.md (ASCII / table / both).
- Concurrency/retry behavior (inherits existing semantic-extraction patterns).
- Exact JSON shape inside `graphify-out/cache/confidence/<sha>.json`.
