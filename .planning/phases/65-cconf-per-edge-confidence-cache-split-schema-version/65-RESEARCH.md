# Phase 65: CCONF — Per-Edge Confidence + Cache Split + schema_version - Research

**Researched:** 2026-05-06
**Domain:** graphify extraction schema, persistence (cache), validation, calibration reporting
**Confidence:** HIGH (codebase verified end-to-end; one design assumption flagged for planner — see Open Questions Q1)

## Summary

This is an internal-architecture phase for graphify v1.13. All five CCONF requirements modify Python modules already in the codebase — no new frameworks, no new dependencies, no new external services. The phase has three load-bearing surfaces:

1. **`extract.py`** — three sites today bake in `confidence_score: 1.0` (lines ~596, 1211–1231, 2252). Three more INFERRED-emitting sites (lines 2252 and the "uses" cross-class edge at 2252) emit no `confidence_score` at all. These must be replaced with per-edge LLM-derived scores plus an `evidence` string.
2. **New `graphify/cache.py` sibling module (or new functions in same module) + `graphify/prompts.py`** — second cache namespace at `graphify-out/cache/confidence/<sha>.json` keyed on `sha256(prompt_version || model || file_hash)`. The existing extract cache (`graphify-out/cache/<sha>.json`) is untouched. `prompts.py` houses the new `PROMPT_VERSION` constant and the scoring prompt template.
3. **`validate.py` + `report.py`** — `schema_version` enforced as optional-on-read / required-on-write; calibration histogram + flag rules in `GRAPH_REPORT.md`.

**Primary recommendation:** Land in three independent waves matching CONTEXT load-order (schema_version + legacy fixture FIRST → confidence cache + scoring SECOND → calibration self-check THIRD). The Phase 53 invariant `_normalize_concept_code_edges` in `build.py` (line 116) already merges duplicate edges with `max(confidence_score)` — Phase 65 adds upstream score variance; merge logic stays untouched. Validate.py already enforces `confidence_score ∈ [0.0, 1.0]` for INFERRED edges on the four new concept↔code relations (Phase 53 D-53.07-09) — Phase 65 just makes the values non-uniform. [VERIFIED: graphify/validate.py:178-210, graphify/build.py:34-114]

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scoring source & integration point**
- **D-65.01** — Real Claude LLM scoring; no heuristic floor, no deferred-LLM stub. Reuses existing semantic-extraction Claude integration.
- **D-65.02** — Score at concept emission inside `extract.py`. `_normalize_concept_code_edges` in `build.py` stays untouched (Phase 53 D-53.02/06 invariants preserved).
- **D-65.03** — Batched per source file. All concept↔code edges from one source file scored in a single LLM call. Matches the cache key (file-hash already pins source content).

**Confidence cache shape & key**
- **D-65.04** — Layout: `graphify-out/cache/confidence/<sha>.json`. Sibling subdirectory next to existing flat extract cache.
- **D-65.05** — Cache key = `sha256(prompt_version || model || file_hash)`. Bumping `prompt_version` invalidates only confidence entries; bumping `model` invalidates only confidence entries; existing extract cache remains valid.
- **D-65.06** — `prompt_version` lives in a new `graphify/prompts.py`. Module-level constant; bumped by code change in same commit as any prompt edit. Same module is home for the scoring prompt template.

**schema_version + legacy fixture**
- **D-65.07** — Storage: top-level JSON key in `graph.json` AND `nx.Graph.graph` attr.
- **D-65.08** — Value format: semver-shaped string `"1.13"`. Read accepts missing/absent (pre-1.13); write requires it. Implemented as two `validate.py` entry points OR one entry point with a `mode` parameter (planner's call).
- **D-65.09** — Legacy fixture: frozen real `graph.json` from a v1.12 sample run, captured verbatim from a known-good v1.12 commit, checked in under `tests/fixtures/`.

**Calibration self-check**
- **D-65.10** — 10-bin histogram of `confidence_score` across all INFERRED concept↔code edges. Three flag rules:
  1. Mode-collapse: any single bin holds >70% of total mass.
  2. Refusal-to-decide: >50% of scores at exactly 0.5.
  3. No-negatives: <5% of edges score below 0.5.
  Histogram rendered regardless; fired rules reported with observed value + threshold.
- **D-65.11** — Thresholds hardcoded as named constants in `report.py` (e.g. `_CALIBRATION_MODE_COLLAPSE_THRESHOLD = 0.70`).

**Evidence field shape**
- **D-65.12** — Free-text excerpt, `edge["evidence"]: str`, hard cap 280 chars, sanitization via existing `security.py` patterns (control-char strip, HTML-escape).
- **D-65.13** — Skewed corpus test = hand-built fixture + stubbed scorer. Tiny `graph.json` where every concept↔code edge has `confidence_score` in 0.85±0.05; scorer monkeypatched. Test asserts mode-collapse flag fires. **No LLM calls in tests.**

**Stderr contract conformance**
- **D-65.14** — Any new warnings/errors emitted by scoring path or schema_version validation MUST conform to locked `[graphify] {error|info}: …` + `  hint: …` two-line contract from Phase 64. Snapshot test at `tests/fixtures/stderr_contract.txt` is the gate.

### Claude's Discretion

- Exact prompt template wording for the scoring call.
- Whether `validate.py` exposes one entry point with `mode={"read","write"}` parameter or two separate functions.
- The small fixture corpus used to generate the frozen v1.12 `graph.json` (prefer something already in `tests/fixtures/`).
- Whether the calibration histogram is rendered as ASCII bars, a markdown table, or both.
- Concurrency/retry behavior for LLM scoring call (inherits whatever is already in `extract.py`).
- Cache file format details inside `graphify-out/cache/confidence/<sha>.json` (likely mirror existing extract cache JSON shape).

### Deferred Ideas (OUT OF SCOPE)

- Federation tiebreakers using `confidence_score` → Phase 66.
- Drift edge filters using `confidence_score` → Phase 67.
- Parameterized concept queries (`concept_code_hops` with `min_confidence`) → Phase 67 (CQUERY).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CCONF-01 | Concept↔code edges emit per-edge `confidence_score ∈ [0.0, 1.0]` from LLM scoring (replaces uniform `1.0`) | Three current sites at `extract.py:596, 1211-1231, 2252` carry the baked-in `1.0`; replace with scored emission. `validate.py:189-210` already bounds-checks INFERRED. [VERIFIED] |
| CCONF-02 | INFERRED edges include an `evidence` field carrying the textual basis for the score | `validate.py:65-71 KNOWN_EVIDENCE_VALUES` already exists for EXTRACTED edges (annotation/jsdoc/docstring/...); CCONF-02 introduces a separate free-text `evidence: str` for INFERRED edges. **Schema choice:** treat INFERRED-evidence as a separate string field path (not the EXTRACTED enum), or expand the validator. Planner decision. [VERIFIED] |
| CCONF-03 | Confidence cache lives in a separate namespace keyed on `prompt_version + model + edge_signature`; `prompt_version` bump invalidates only confidence entries | `cache.py` patterns at `_sanitize_model_id` (line 32), `_cache_key_string` (line 44), `_cache_json_filename` (line 50) directly reusable for sibling module/functions. Existing extract cache untouched. [VERIFIED] |
| CCONF-04 | `GRAPH_REPORT.md` gains a calibration self-check section that flags suspicious score distributions | `report.py:86-95` already computes `inf_avg` and pulls `confidence_score` per INFERRED edge; histogram + flag rules slot in next to "Summary" or as a new H2 section. [VERIFIED] |
| CCONF-05 | `validate.py` enforces "optional on read, required on write" with a new `schema_version` field; frozen v1.10–v1.12 legacy fixture passes read | `validate.py:117` `validate_extraction(data: dict) -> list[str]` is the single read-validation entry today; D-65.08 adds either a `mode` param or a sibling `validate_extraction_for_write`. [VERIFIED] |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM scoring call | Skill orchestrator (`graphify/skill*.md`) | `graphify/extract.py` (Python helper that drives request/response shape) | The Python library does NOT call Anthropic API directly; the skill (Claude Code agent) is the LLM client and writes scored nodes/edges into `save_semantic_cache`. See Open Question Q1. [VERIFIED: grep -rn "anthropic" graphify/*.py shows no client] |
| Score persistence | `graphify/cache.py` (extended) or new `graphify/confidence_cache.py` | `graphify/prompts.py` (constants supplier) | Mirrors existing extract cache module boundaries. |
| Per-edge attribute storage | NetworkX graph (`build.py` consumes; export.py persists) | `graph.json` round-trip via `json_graph.node_link_data` | Edge dict already carries `confidence_score`; `evidence` is one new key. |
| schema_version write-validation | `graphify/validate.py` | `graphify/export.py:to_json` (must inject `schema_version` at write) | Single source of truth on read; export wires the value at serialization. |
| Calibration histogram | `graphify/report.py` | — | Pure read over `G.edges(data=True)`. |
| Evidence sanitization | `graphify/security.py:sanitize_label` (existing) | — | D-65.12 explicitly reuses; cap at 280 chars (vs. label cap 256). |

## Standard Stack

### Core (already present — no installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `hashlib` | 3.10+ | sha256 for confidence cache key composition | Already used by `cache.py:_inner_hash` [VERIFIED] |
| Python stdlib `json` | 3.10+ | Cache file I/O + `graph.json` schema_version round-trip | Already used [VERIFIED] |
| Python stdlib `pathlib` | 3.10+ | Path construction (`graphify-out/cache/confidence/<sha>.json`) | Already used [VERIFIED] |
| `networkx` | unpinned (latest 3.x) | Graph + `G.graph` attr storage for `schema_version` | Already core dependency [VERIFIED: pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | already CI baseline | Pure unit tests, fixtures via `tmp_path` | All Phase 65 tests [VERIFIED] |
| Existing `graphify/security.py:sanitize_label` | n/a | Evidence string sanitization | D-65.12 [VERIFIED] |

**Installation:** None required. Phase 65 introduces zero new dependencies. [VERIFIED via pyproject.toml inspection — no LLM client library is a hard dep; all LLM work happens in the skill/orchestrator layer]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sibling subdirectory `cache/confidence/<sha>.json` | Suffixed filename in same dir (e.g. `<sha>.confidence.json`) | Subdirectory wins for `rm -rf` reset semantics (D-65.04 rationale). |
| Two `validate.py` entry points | Single entry point with `mode={"read","write"}` parameter | Discretion item; both are explicitly allowed by D-65.08. |
| ASCII histogram bars | Markdown table | Discretion item; both rendered if planner chooses. |

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Skill orchestrator (graphify/skill*.md, runs in Claude Code agent) │
│                                                                     │
│   1. detect() ──► uncached files                                    │
│   2. SEMANTIC EXTRACTION (Claude API call by the skill)             │
│      • Emit concept↔code edges with relation/source/target          │
│      • NEW: also score each edge → confidence_score + evidence      │
│      • Batched per source file (D-65.03)                            │
│   3. save_semantic_cache(...)                  ─┐                   │
│      NEW: save_confidence_cache(...)            │                   │
└─────────────────────────────────────────────────┼───────────────────┘
                                                  │
                              ┌───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Python library                                                     │
│                                                                     │
│   cache.py (UNCHANGED)        confidence_cache.py / cache.py-ext    │
│   ┌─────────────────────┐     ┌────────────────────────────────┐    │
│   │ graphify-out/       │     │ graphify-out/cache/confidence/ │    │
│   │   cache/<sha>.json  │     │   <sha2>.json                  │    │
│   │ key=file_hash+model │     │ key=sha256(prompt_version ||   │    │
│   └─────────────────────┘     │     model || file_hash)        │    │
│                               └────────────────────────────────┘    │
│                                                                     │
│   prompts.py (NEW)                                                  │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ PROMPT_VERSION = "1.13.0"                                   │   │
│   │ SCORING_PROMPT_TEMPLATE = "..."                             │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   validate.py (EXTENDED)                                            │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ validate_for_read(data)  → schema_version optional          │   │
│   │ validate_for_write(data) → schema_version REQUIRED          │   │
│   │   (or single entry with mode= param — discretion D-65.08)   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   build.py:_normalize_concept_code_edges (UNCHANGED — Phase 53)     │
│   • Already merges duplicate edges with max(confidence_score)       │
│                                                                     │
│   export.py:to_json (EXTENDED)                                      │
│   • Injects schema_version="1.13" at top level                      │
│   • Round-trips G.graph["schema_version"]                           │
│                                                                     │
│   report.py (EXTENDED)                                              │
│   • Existing: avg INFERRED confidence (line 94)                     │
│   • NEW: 10-bin histogram + 3 flag rules                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Touch List
```
graphify/
├── extract.py            # MODIFIED: replace baked-in 1.0 at lines ~596, 1211-1231, 2252;
│                         # introduce per-edge scored emission with evidence
├── prompts.py            # NEW: PROMPT_VERSION + SCORING_PROMPT_TEMPLATE
├── cache.py              # MODIFIED: add confidence-cache helpers (or extracted to new module)
│                         # OR
├── confidence_cache.py   # NEW: load_confidence/save_confidence; mirrors cache.py structure
├── validate.py           # MODIFIED: schema_version semantics (read vs write)
├── export.py             # MODIFIED: emit schema_version in to_json + G.graph attr
├── report.py             # MODIFIED: calibration histogram + flag-rule constants
├── security.py           # UNCHANGED (sanitize_label reused for evidence)
├── build.py              # UNCHANGED (Phase 53 invariant preserved)
└── skill.md (+ 7 platform variants)
                          # MODIFIED: orchestrate scoring call alongside semantic extraction;
                          # consume save_confidence_cache; respect prompt_version
tests/
├── fixtures/
│   ├── legacy_v1_12_graph.json    # NEW (D-65.09): frozen real v1.12 graph.json
│   └── skewed_distribution.json   # NEW (D-65.13): hand-built mode-collapse fixture
├── test_validate.py               # MODIFIED: schema_version read/write split tests
├── test_confidence_cache.py       # NEW: prompt_version invalidation, model invalidation, file_hash isolation
├── test_extract_confidence.py     # NEW (or extend test_extract.py): scored-edge emission via stubbed scorer
├── test_report_calibration.py     # NEW: histogram + 3 flag rules
└── test_extract.py                # UNCHANGED (file-hash cache regression check stays green)
```

### Pattern 1: Sibling Cache Module (mirrors `cache.py`)
**What:** Replicate the proven `cache.py` shape — `_sanitize_*`, `_cache_key_string`, `_cache_json_filename`, `load_*`, `save_*` — for the confidence namespace.
**When to use:** New cache namespace requested in this phase (D-65.04/05).
**Example:**
```python
# Source: graphify/cache.py:50 (existing pattern to mirror)
def _cache_json_filename(key: str) -> str:
    if ":" not in key:
        return f"{key}.json"
    return f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

# Phase 65 new pattern:
def _confidence_cache_key(prompt_version: str, model_id: str, file_hash: str) -> str:
    blob = f"{prompt_version}\x00{model_id}\x00{file_hash}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def confidence_cache_dir(root: Path = Path(".")) -> Path:
    d = Path(root) / "graphify-out" / "cache" / "confidence"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

### Pattern 2: Atomic Write (already used)
**What:** `tmp = entry.with_suffix(".tmp"); tmp.write_text(...); os.replace(tmp, entry)` — atomic on POSIX and Windows.
**When to use:** Confidence cache writes (mirrors `cache.py:save_cached`).
**Example:** see `cache.py:96-101` [VERIFIED].

### Pattern 3: Two-Line Stderr (Phase 64 contract)
**What:** Any new warning/error MUST be `[graphify] {error|info}: <msg>\n  hint: <hint>`.
**When to use:** Anywhere Phase 65 emits stderr — e.g. "schema_version missing — read-validating as legacy", "confidence scoring fell back due to LLM error".
**Example:**
```python
# Source: graphify/output.py:emit_option_b_breadcrumb pattern (Phase 64 verified emitter)
print("[graphify] info: schema_version missing — read-validating as legacy v1.12", file=sys.stderr)
print("  hint: writes will require schema_version='1.13' once this graph is regenerated", file=sys.stderr)
```

### Anti-Patterns to Avoid
- **Don't introduce a new LLM client in Python.** All Anthropic calls today happen at the skill layer (`graphify/skill.md`). Adding an `anthropic` import to `extract.py` would change the deployment contract (graphify currently runs offline if the skill isn't dispatched). The scorer call sits in the skill's "Step 3B" (semantic extraction) alongside the existing concept↔code emission. See Open Question Q1.
- **Don't unify the two cache namespaces.** D-65.04/05 are explicit: `graphify-out/cache/<sha>.json` (extract) and `graphify-out/cache/confidence/<sha>.json` (confidence) must remain independent so `prompt_version` bumps don't invalidate AST cache hits.
- **Don't rewrite `_normalize_concept_code_edges`.** Phase 53 D-53.02/05/06 invariants are locked. The function's existing `max(confidence_score)` merge already handles non-uniform scores — Phase 65 doesn't need to change it.
- **Don't extend `KNOWN_EVIDENCE_VALUES` enum to include free text.** That set is for EXTRACTED-edge evidence (annotation/jsdoc/docstring/...). The new INFERRED `evidence` field is free text — wire it as a separate validation path, not by expanding the enum.
- **Don't conflate the four new concept↔code relations with all INFERRED edges.** The validator at `validate.py:185` only enforces `confidence_score` for `documents/tests/realizes/instantiates` — but CCONF-01 says "Every concept↔code INFERRED edge". Planner must decide: is `implements` (Phase 53 D-53.10 backward-compat skip) included? **Recommendation:** include `implements` for forward INFERRED edges only; preserve EXTRACTED `implements` baseline for backward compat. Surface as Open Question Q2.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cache key derivation | New hash mixer | Mirror `cache.py:_cache_key_string` + sha256-named file via `_cache_json_filename` | Proven pattern; Windows-safe (no `:` in filenames); `model_id` sanitization already handles traversal |
| Atomic file write | `open()` + `write()` | `tmp.write_text(...)` + `os.replace(tmp, entry)` | Already in `cache.py:96-101`; survives crashes |
| Evidence sanitization | New escape function | `graphify/security.py:sanitize_label` (with 280-char cap) | D-65.12 explicit; HTML-safe + control-char strip |
| Stderr formatting | New print pattern | Two-line `[graphify] error:` + `  hint:` (Phase 64 contract) | Snapshot test `tests/fixtures/stderr_contract.txt` will fail otherwise |
| Schema-version detection | Bespoke regex | Read top-level JSON `schema_version` key with `dict.get()`; absent ⇒ legacy | Round-trips through `node_link_data`/`node_link_graph` cleanly via `G.graph` attr |
| Histogram bucketing | Hand-rolled bin math | `int(score * 10)` clamped to `[0,9]` for 10-bin floor mapping | Stdlib `bisect`/`statistics` are overkill; this is a 5-line operation |

**Key insight:** Every architectural primitive Phase 65 needs already exists. The phase is composition, not novelty. Avoid temptation to "improve" the cache module structure while you're touching it.

## Common Pitfalls

### Pitfall 1: Confidence cache invalidates AST cache
**What goes wrong:** Bumping `prompt_version` accidentally re-runs structural extraction, blowing past CCONF-03 success criterion 2.
**Why it happens:** If the planner threads `prompt_version` into `cache.file_hash(model_id=...)`, it pollutes the model_id channel.
**How to avoid:** Keep the two key spaces strictly separate. `cache.file_hash` continues to take `model_id` only; the new confidence-cache helper takes `prompt_version` as a *third* dimension and never composes it into the AST cache key.
**Warning signs:** Test `test_extract.py` cache hits start failing after `prompt_version` bump.
**Test:** `test_confidence_cache_isolation` — bump `prompt_version`, assert AST cache hit count unchanged on a fixture corpus.

### Pitfall 2: schema_version absence treated as a write error
**What goes wrong:** Loading a v1.12 graph triggers a validation error.
**Why it happens:** Naive implementation puts `schema_version` in `REQUIRED_FIELDS` for both read and write.
**How to avoid:** Two paths or `mode=` parameter (D-65.08). Read mode treats missing `schema_version` as "pre-1.13" and proceeds silently (or with a Phase 64-conformant `[graphify] info:` breadcrumb — discretion).
**Warning signs:** `tests/fixtures/legacy_v1_12_graph.json` fails validation on read.

### Pitfall 3: Evidence string blows the 280-char cap
**What goes wrong:** LLM returns 500-char justification; serialization corrupts wiki/HTML.
**Why it happens:** Sanitization happens at render-time, not at-cache-time.
**How to avoid:** Truncate + sanitize at the moment the score is written into the edge dict (in `extract.py`/scorer wrapper), not at report-time.
**Warning signs:** Vault notes contain unescaped `<`, `>`, or control chars.

### Pitfall 4: Mode-collapse rule fires on tiny graphs
**What goes wrong:** A corpus with 3 INFERRED edges all at 0.85 fires "mode-collapse" — false positive.
**Why it happens:** Percentages on tiny denominators are noisy.
**How to avoid:** Add a minimum-edge-count gate before any rule fires. Recommendation: skip calibration section entirely when `len(inf_edges) < 10`. Surface as Open Question Q3 — planner discretion.
**Warning signs:** First-run user reports false alarms on small corpora.

### Pitfall 5: Score variance from `_normalize_concept_code_edges` merge
**What goes wrong:** Same edge extracted twice (different files) with scores 0.4 and 0.9 — `build.py` merge takes `max(0.4, 0.9) = 0.9`, masking the low-confidence signal.
**Why it happens:** Phase 53 D-53.05 chose `max()` to prefer higher confidence.
**How to avoid:** This is a known intentional invariant (Phase 53 D-53.05). Don't fight it — but **document it in the report**: the calibration histogram is over post-merge scores. Add a one-sentence note in the calibration section.
**Warning signs:** Calibration looks suspiciously high-confidence on multi-file corpora.

### Pitfall 6: Skill orchestrator not synchronized with `prompt_version`
**What goes wrong:** Python `prompts.py` bumps `PROMPT_VERSION` but the seven `skill*.md` variants still use the old prompt text.
**Why it happens:** Two sources of truth — Python module and Markdown skill files.
**How to avoid:** Either (a) skill files load the prompt from `graphify/prompts.py` at runtime via a quick `python -c "from graphify.prompts import SCORING_PROMPT_TEMPLATE; print(...)"` shell-out (matches existing skill patterns); OR (b) a unit test asserts skill files contain the canonical prompt-version string. Option (b) is cheaper. Surface as Open Question Q4.
**Warning signs:** Cache hits return scores that don't match the prompt the skill is actually using.

## Code Examples

### Adding schema_version on write (extending `to_json`)
```python
# Source: graphify/export.py:316-330 (current to_json)
def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str) -> None:
    node_community = _node_community_map(communities)
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)
    # NEW Phase 65: emit schema_version at top level
    data["schema_version"] = G.graph.get("schema_version", "1.13")
    for node in data["nodes"]:
        node["community"] = node_community.get(node["id"])
    for link in data["links"]:
        if "confidence_score" not in link:
            conf = link.get("confidence", "EXTRACTED")
            link["confidence_score"] = _CONFIDENCE_SCORE_DEFAULTS.get(conf, 1.0)
    # ... rest unchanged
```

### Confidence cache key derivation
```python
# Phase 65 new in graphify/confidence_cache.py (or graphify/cache.py extension)
import hashlib

def _confidence_cache_key(prompt_version: str, model_id: str, file_hash: str) -> str:
    """Composes the three-dimensional confidence cache key per D-65.05."""
    if "/" in prompt_version or ".." in prompt_version:
        raise ValueError("prompt_version must not contain path segments")
    blob = f"{prompt_version}\x00{model_id}\x00{file_hash}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
```

### Calibration flag-rule shape
```python
# Phase 65 new in graphify/report.py
_CALIBRATION_MIN_EDGES = 10
_CALIBRATION_MODE_COLLAPSE_THRESHOLD = 0.70   # any single bin
_CALIBRATION_REFUSAL_THRESHOLD = 0.50         # exact 0.5 share
_CALIBRATION_NEGATIVE_FLOOR = 0.05            # share with score < 0.5

def _calibration_histogram(inf_scores: list[float]) -> list[int]:
    bins = [0] * 10
    for s in inf_scores:
        idx = min(9, max(0, int(s * 10)))
        bins[idx] += 1
    return bins
```

### Evidence sanitization at emission time
```python
# Phase 65 in graphify/extract.py (scorer wrapper, conceptual)
from .security import sanitize_label

_MAX_EVIDENCE_LEN = 280

def _finalize_evidence(raw: str) -> str:
    truncated = raw[:_MAX_EVIDENCE_LEN]
    return sanitize_label(truncated)  # control-char strip + (callers HTML-escape at render)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Uniform `confidence_score: 1.0` baseline | Per-edge LLM-derived `confidence_score ∈ [0,1]` | Phase 65 (this) | Replaces v1.10–v1.12 stub baseline; downstream Phase 66/67 features become meaningful |
| Single cache namespace `graphify-out/cache/<sha>.json` | Two namespaces; confidence at `cache/confidence/<sha>.json` | Phase 65 (this) | `prompt_version` bumps no longer invalidate AST cache |
| No `schema_version` on graph.json | `schema_version: "1.13"` required-on-write, optional-on-read | Phase 65 (this) | First explicit forward-compat contract for graph serialization |
| `validate.py` enforces `confidence_score` only on 4 new concept↔code relations (Phase 53 D-53.07-09) | Same enforcement, but real-world INFERRED scores will be non-uniform | Phase 65 produces input for existing validator | Validator already correct — no change needed |

**Deprecated/outdated:** Nothing removed. Phase 65 is purely additive at the schema level (new `evidence` field, new `schema_version` field, new cache namespace).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed; CI matrix Python 3.10 + 3.12) [VERIFIED: pyproject.toml] |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_validate.py tests/test_confidence_cache.py tests/test_report_calibration.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CCONF-01 | extract.py emits `confidence_score ∈ [0,1]` per concept↔code INFERRED edge (no uniform 1.0) | unit | `pytest tests/test_extract_confidence.py::test_no_uniform_one -x` | ❌ Wave 0 |
| CCONF-01 | uniform-1.0 baseline absent on a stubbed-scorer fixture | unit | `pytest tests/test_extract_confidence.py::test_score_variance_present -x` | ❌ Wave 0 |
| CCONF-02 | INFERRED edges include non-empty `evidence` field, ≤280 chars, sanitized | unit | `pytest tests/test_extract_confidence.py::test_evidence_field_present_and_capped -x` | ❌ Wave 0 |
| CCONF-03 | Bumping `prompt_version` invalidates only confidence-cache entries | unit | `pytest tests/test_confidence_cache.py::test_prompt_version_invalidation -x` | ❌ Wave 0 |
| CCONF-03 | Bumping `model` invalidates only confidence-cache entries; AST cache untouched | unit | `pytest tests/test_confidence_cache.py::test_model_invalidation_isolated -x` | ❌ Wave 0 |
| CCONF-03 | Unchanged file_hash → confidence cache hit (no re-extraction) | unit | `pytest tests/test_confidence_cache.py::test_file_hash_unchanged_skips -x` | ❌ Wave 0 |
| CCONF-04 | Mode-collapse flag fires on `tests/fixtures/skewed_distribution.json` (per D-65.13) | unit | `pytest tests/test_report_calibration.py::test_mode_collapse_flag_fires -x` | ❌ Wave 0 |
| CCONF-04 | Refusal-to-decide flag fires when >50% scores at 0.5 | unit | `pytest tests/test_report_calibration.py::test_refusal_flag_fires -x` | ❌ Wave 0 |
| CCONF-04 | No-negatives flag fires when <5% scores below 0.5 | unit | `pytest tests/test_report_calibration.py::test_no_negatives_flag_fires -x` | ❌ Wave 0 |
| CCONF-04 | Histogram rendered regardless of flags (well-distributed corpus) | unit | `pytest tests/test_report_calibration.py::test_histogram_always_rendered -x` | ❌ Wave 0 |
| CCONF-05 | Frozen `tests/fixtures/legacy_v1_12_graph.json` passes read validation | unit | `pytest tests/test_validate.py::test_legacy_v1_12_passes_read -x` | ❌ Wave 0 (fixture + test) |
| CCONF-05 | Write validation fails when `schema_version` is absent | unit | `pytest tests/test_validate.py::test_write_requires_schema_version -x` | ❌ Wave 0 |
| CCONF-05 | `to_json` emits `schema_version: "1.13"` at top level | unit | `pytest tests/test_export.py::test_to_json_emits_schema_version -x` | ❌ Wave 0 |
| Phase 64 carry | New stderr emissions conform to two-line contract | unit | `pytest tests/test_stderr_contract.py -x` | ✅ EXISTS (Phase 64) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_validate.py tests/test_confidence_cache.py tests/test_report_calibration.py tests/test_extract_confidence.py -x -q` (~targeted; <30s)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green + `tests/fixtures/stderr_contract.txt` snapshot unchanged (or knowingly updated)

### Wave 0 Gaps
- [ ] `tests/test_confidence_cache.py` — covers CCONF-03
- [ ] `tests/test_extract_confidence.py` — covers CCONF-01, CCONF-02 (or extend `tests/test_extract.py`)
- [ ] `tests/test_report_calibration.py` — covers CCONF-04
- [ ] `tests/fixtures/legacy_v1_12_graph.json` — frozen real v1.12 graph.json (D-65.09 procurement step)
- [ ] `tests/fixtures/skewed_distribution.json` — hand-built mode-collapse fixture (D-65.13)
- [ ] Extend `tests/test_validate.py` with read-vs-write `schema_version` cases (CCONF-05)
- [ ] Extend `tests/test_export.py` with `to_json` schema_version emission (CCONF-05)

**Skewed corpus fixture shape (D-65.13):**
```json
{
  "schema_version": "1.13",
  "nodes": [
    {"id": "code_a", "label": "ModuleA", "file_type": "code", "source_file": "a.py"},
    {"id": "code_b", "label": "ModuleB", "file_type": "code", "source_file": "b.py"},
    {"id": "concept_x", "label": "Concept X", "file_type": "rationale", "source_file": ""},
    {"id": "concept_y", "label": "Concept Y", "file_type": "rationale", "source_file": ""}
  ],
  "edges": [
    {"source": "code_a", "target": "concept_x", "relation": "documents",
     "confidence": "INFERRED", "confidence_score": 0.84, "evidence": "...",
     "source_file": "a.py", "weight": 1.0},
    {"source": "code_b", "target": "concept_x", "relation": "documents",
     "confidence": "INFERRED", "confidence_score": 0.86, "evidence": "...",
     "source_file": "b.py", "weight": 1.0},
    "...8 more edges all in 0.85±0.05 to push >70% into the [0.8, 0.9) bin..."
  ]
}
```

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not applicable — no user-facing auth surface in this phase |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | LLM-returned `evidence` strings; cap 280 chars; sanitize via `security.py:sanitize_label` (control-char strip + length cap); HTML-escape at render time |
| V6 Cryptography | partial | sha256 used as cache key composition (collision-resistance not security-critical; using stdlib `hashlib` — never hand-roll) |

### Known Threat Patterns for graphify Python pipeline

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection via source code or comments influencing `evidence` field content | Tampering | Treat all `evidence` text as untrusted: truncate, control-char strip, HTML-escape at render. Already encoded in D-65.12 + `security.py:sanitize_label` reuse. |
| Cache poisoning via crafted `prompt_version` or `model_id` (path traversal) | Tampering | `cache.py:_sanitize_model_id` rejects `..`, `/`, `\`; mirror this for `prompt_version` in the new helper. |
| Confidence cache filename collisions on Windows (`:` not allowed in filenames) | DoS | Mirror `cache.py:_cache_json_filename` — sha256 the composite key for the on-disk filename. [VERIFIED pattern] |
| Schema_version downgrade attack (someone hand-edits `graph.json` to absent → old reader silently treats as legacy) | Tampering | Acceptable in v1.13 — read-validation is intentionally permissive (D-65.08). Future hardening (Phase 66+) can promote to required when v1.10–v1.12 graphs age out. |
| LLM returns adversarial control characters in `evidence` | Tampering / DoS-render | `sanitize_label` already strips control chars [VERIFIED graphify/security.py:190]. |

## Runtime State Inventory

> Phase 65 is greenfield-additive within the codebase (new fields, new cache namespace, new fixture). It is NOT a rename/refactor/migration. The Runtime State Inventory check is **N/A — no rename, no string replacement, no relocation of existing data**. Existing AST cache files (`graphify-out/cache/<sha>.json`) on user disks remain valid and untouched. New confidence-cache directory is created on demand. Existing v1.10–v1.12 user graphs (`graph.json` without `schema_version`) read cleanly by design (CCONF-05).

## Environment Availability

> Phase 65 is pure code/config — no new tools, runtimes, services, or CLI utilities required. **Skipping.** All work happens inside the existing Python package + skill orchestrator surface that's already running.

## Project Constraints (from CLAUDE.md)

The following directives MUST be honored by the planner:

- **Python 3.10+** (CI runs 3.10 and 3.12) — type hints use `dict[K,V]`, `str | None`, `from __future__ import annotations`. [VERIFIED]
- **No new required dependencies** — confidence cache and prompts module use stdlib only. [VERIFIED feasible — no LLM client needed in Python; skill is the LLM tier]
- **Pure unit tests** — no network, no fs side effects outside `tmp_path`. The skewed corpus + legacy v1.12 fixture are static JSON files; the scorer is monkeypatched per D-65.13. [VERIFIED constraint]
- **No linter or formatter** — match existing 4-space indentation, module docstring as first line after `from __future__ import annotations`, stderr prefix `[graphify]`.
- **Security: all external input through `security.py`** — `evidence` field is LLM output (external input) and MUST flow through `sanitize_label` per D-65.12. [VERIFIED surface exists]
- **Skill files: 7 platforms** — `skill.md`, `skill-codex.md`, `skill-opencode.md`, `skill-openclaw.md`, `skill-droid.md`, `skill-trae.md`, `skill-trae-cn.md` — any prompt-version coordination must touch all variants OR centralize via runtime read of `prompts.py`. [VERIFIED 7 platforms]
- **No commits without user request** — research deliverable is RESEARCH.md only.
- **`commit_docs: true`** in `.planning/config.json` — research artifact will be committed by orchestrator after acceptance. [VERIFIED]
- **`workflow.tdd_mode: true`** — Wave 0 RED tests precede GREEN implementation; respect TDD ordering in plan structure.
- **`workflow.nyquist_validation: true`** — Validation Architecture section above is required (and provided).
- **`graphify.enabled: true`** — graph-aware planning; the planner SHOULD query `graphify-out/` for affected file relationships (e.g. `extract.py` ↔ `cache.py` ↔ `validate.py` cluster).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "LLM scoring happens at the skill orchestrator layer, not via a Python-side Anthropic client" | Architectural Responsibility Map, Open Question Q1 | If the planner actually wants a Python-side `anthropic` client, this changes pyproject.toml, deployment, and offline guarantees — `[ASSUMED]` based on grep showing no client in `graphify/*.py` and skill.md owning Step 3B semantic extraction. **Confirm with user via discuss-phase before plans land.** |
| A2 | "Including `implements` (the legacy concept↔code relation) in CCONF-01 scoring is forward-only; existing EXTRACTED `implements` edges keep their baseline" | Anti-Patterns / Open Question Q2 | If the user wants ALL `implements` edges (including EXTRACTED) scored, scope expands; `[ASSUMED]` based on Phase 53 D-53.10 backward-compat carve-out. |
| A3 | "10-bin histogram with `int(score * 10)` floor mapping is the canonical bucketing" | Code Examples, Pitfall 4 | Trivial; `[ASSUMED]`. |
| A4 | "Calibration section gates on `len(inf_edges) >= 10` to avoid false positives on tiny corpora" | Pitfall 4, Open Question Q3 | If gate is wrong, false alarms or false silence; `[ASSUMED]` — reasonable default, planner discretion. |
| A5 | "Skill files load `PROMPT_VERSION` at runtime via Python shell-out OR a unit test asserts skill-file substring matches" | Pitfall 6, Open Question Q4 | Drift risk between skill prompts and Python `prompt_version`; `[ASSUMED]` — needs planner pick. |

## Open Questions

1. **LLM scoring tier ownership.**
   - What we know: graphify Python has no Anthropic client (`grep -rn "anthropic" graphify/*.py` returns only enrich.py price-lookup string and routing.py endpoint URL); semantic extraction is documented as "Step 3B" in `graphify/skill.md` lines 269+ and dispatched by Claude Code subagents.
   - What's unclear: D-65.01 says "actual Claude API call" — is this (a) a new Python-side client added to `extract.py` or (b) a skill-orchestrated call whose result is written into `save_confidence_cache(...)` by the skill?
   - Recommendation: **(b) skill-orchestrated**, matching every existing semantic-extraction call in graphify. The Python helper exposes `score_concept_code_edges_for_file(path, edges) -> [(score, evidence), ...]` that the skill drives. This preserves the "no new required deps" CLAUDE.md constraint and the offline guarantee. Confirm with user before plan-01 lands.

2. **Does `implements` count as an in-scope concept↔code relation for CCONF-01?**
   - What we know: `validate.py:NEW_CONCEPT_CODE_RELATIONS` is `{documents, tests, realizes, instantiates}` — `implements` is intentionally excluded (Phase 53 D-53.10 backward compat).
   - What's unclear: CCONF-01 says "every concept↔code INFERRED edge" — `build.py:CONCEPT_CODE_RELATIONS` includes `implements`. Should new INFERRED `implements` edges also carry per-edge `confidence_score`?
   - Recommendation: **Yes, for forward-emitted INFERRED `implements` only.** Existing EXTRACTED `implements` baseline (the v1.10/v1.11 shipped behavior) keeps `confidence_score: 1.0` per Phase 53 D-53.10. Phase 65 surfaces variance only on newly-INFERRED edges. Confirm.

3. **Calibration section minimum-edge gate.**
   - What we know: D-65.10 doesn't specify a minimum corpus size before flag rules fire.
   - What's unclear: Should rules fire on a 3-edge graph?
   - Recommendation: Skip calibration entirely when `len(inf_edges) < 10`; render a one-line "calibration skipped — insufficient INFERRED edges (n=X, need ≥10)" note instead. Planner discretion.

4. **`prompt_version` synchronization across 7 skill files.**
   - What we know: Bumping `PROMPT_VERSION` in `prompts.py` invalidates the confidence cache, but the skill-side prompt text lives in `skill*.md`.
   - What's unclear: How is drift prevented?
   - Recommendation: Add `tests/test_skill_files.py::test_skill_prompts_match_python_constants` that greps each `skill*.md` for the literal `SCORING_PROMPT_TEMPLATE` substring or for `PROMPT_VERSION = "..."` reference. This mirrors the existing Phase 36 "skill drift" test pattern. Planner picks the exact assertion shape.

5. **Choice between two `validate.py` entry points vs. single `mode=` parameter.**
   - What we know: D-65.08 explicitly leaves this to the planner.
   - Recommendation: Two entry points — `validate_extraction_for_read` and `validate_extraction_for_write`. Cleaner call-sites, better IDE help, and `validate_extraction` (current) becomes an alias for `validate_extraction_for_read` for backward compat.

6. **Confidence cache module placement.**
   - What we know: D-65.04/05 don't mandate file location.
   - Recommendation: Extend `graphify/cache.py` with `confidence_*` helpers rather than a new `confidence_cache.py`. Keeps the cache surface in one module (matches user mental model — "the cache"), and the new helpers naturally call `cache._sanitize_model_id` / `cache._inner_hash`.

## Sources

### Primary (HIGH confidence)
- `graphify/cache.py` (full read) — confidence cache pattern source [VERIFIED]
- `graphify/validate.py` (full read) — schema validation entry point + existing `confidence_score ∈ [0,1]` enforcement on the four Phase 53 relations [VERIFIED]
- `graphify/build.py:1-150` — Phase 53 invariants, `_normalize_concept_code_edges`, `_merge_edge_fields` already-handles-non-uniform-scores [VERIFIED]
- `graphify/extract.py` — INFERRED emission sites at 596, 1211, 1221, 1231, 2252; baked-in `confidence_score: 1.0` [VERIFIED via grep]
- `graphify/report.py:1-180` — current `inf_avg` calculation; integration point for histogram [VERIFIED]
- `graphify/export.py:316-330` — `to_json` integration point for `schema_version` [VERIFIED]
- `graphify/security.py:183-202` — `_MAX_LABEL_LEN`, `sanitize_label` reuse for evidence [VERIFIED]
- `pyproject.toml` — current version `1.0.0`; no LLM client dependency [VERIFIED]
- `tests/test_cache.py` (head) and `tests/test_validate.py` (head) — existing pure-unit-test patterns [VERIFIED]
- `.planning/phases/65-cconf-…/65-CONTEXT.md` — locked decisions [VERIFIED via cat]
- `.planning/REQUIREMENTS.md` §CCONF — definitive requirement text [VERIFIED via cat]
- `.planning/ROADMAP.md` §"Phase 65" — depends-on Phase 64, 4 success criteria [VERIFIED via cat]
- `tests/fixtures/stderr_contract.txt` — Phase 64 locked snapshot (referenced; existence confirmed via memory 6105 / 6162)

### Secondary (MEDIUM confidence)
- Memory observation 6166 — confirms current INFERRED edges emit no confidence_score in some sites [CITED]
- Memory observation 6169 — confirms 14 architectural decisions locked [CITED]
- Memory observation 5631 — `cache.file_hash` strips frontmatter before hashing (relevant to deciding whether confidence cache should match this) [CITED]

### Tertiary (LOW confidence)
- None — every claim is backed by direct file inspection or upstream context.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primitive verified in source.
- Architecture: HIGH — module boundaries and integration anchors confirmed by reading.
- Pitfalls: HIGH — pitfalls 1, 2, 5 are direct consequences of verified code; pitfalls 3, 4, 6 are best-practice prudence.
- Validation architecture: HIGH — Wave 0 gaps fully enumerated; existing test patterns (`test_cache.py`, `test_validate.py`) provide direct templates.

**Research date:** 2026-05-06
**Valid until:** 2026-06-05 (stable internal-architecture domain; refresh only if upstream Phase 64 fixtures change or pyproject deps shift)
