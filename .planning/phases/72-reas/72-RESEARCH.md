# Phase 72: REAS — Research

**Researched:** 2026-05-07
**Domain:** Graph schema extension (validation + extraction + build + analyze + render) — reasoning-relation edge types layered on top of the Phase 71 temporal validity schema
**Confidence:** HIGH (all claims verified by codebase grep; no external library research required)

---

## Summary

Phase 72 extends graphify's edge schema with five new relation types (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`) intended for document/concept nodes only. Mechanically, this is a layered repeat of the Phase 53 concept↔code precedent (frozenset registration + per-relation validation rule + canonical relation-vocabulary doc) with two genuinely novel pieces:

1. **Two-pass build resolution** for cross-document references that cannot be resolved when an extractor sees a single file.
2. **`supersedes` auto-stamping** of `valid_until` on outbound edges of the superseded node, sitting *on top of* Phase 71's existing temporal stamping in `build_from_json` (lines 293–320).

The single most important non-obvious finding is that the **semantic-extraction prompt for documents/papers/rationales does not live in `graphify/extract.py`** — it lives in `graphify/skill.md` (Step 3 Part B, lines ~265–435) and its 8 platform variants (`skill-codex.md`, `skill-aider.md`, `skill-claw.md`, `skill-codex.md`, `skill-copilot.md`, `skill-droid.md`, `skill-excalidraw.md`, `skill-opencode.md`, `skill-trae.md`, `skill-windows.md`). Every prompt change must be replicated across all 10 files, and the Phase 65 skill-prompt-drift gate (`tests/test_skill_prompt_drift.py`) enforces parity. `extract.py` itself is tree-sitter code-only — `from .prompts import PROMPT_VERSION` at line 17 is the cache key, not the prompt body.

**Primary recommendation:** Land Phase 72 in 4 plans:
1. `validate.py` + `docs/RELATIONS.md` — `REASONING_RELATIONS` frozenset, KNOWN_EDGE_RELATIONS extension, both-endpoints-doc/concept rule, RELATIONS.md taxonomy section.
2. Skill prompts (all 10 `skill*.md` files) + `prompts.py` `PROMPT_VERSION` bump — ADR exemplars for supersession & contradiction; one-line definitions for the other 3 relations.
3. `build.py` — two-pass target resolution helper + `_stamp_supersession_outbound` integrated into `build_from_json` between current temporal-stamp block (lines 293–310) and existing `stamp_supersessions(...)` call (lines 316–320).
4. `analyze.py` (knowledge_gaps fix + new contradictions/chains producer) + `report.py` section + `wiki.py` `## Reasoning Relations` subsection + `export.py` Obsidian frontmatter `reasoning_relations:` list.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**1. Extraction trigger & prompt shape (REAS-02)**
- **D-01:** Extend the EXISTING semantic-extraction prompt for documents (md/txt/rst), papers (PDF), and rationales — single LLM pass per doc, no second classifier prompt and no signal-gating.
- **D-02:** Prompt exemplars are FOCUSED: two worked examples — ADR supersession chain (ADR-0042 supersedes ADR-0028) and an ADR contradiction. The other three relations (`supports`, `evolved_into`, `depends_on`) get a one-line definition only.
- **D-03:** Reasoning edges emit `confidence` (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`) and `confidence_score` per the CCONF v1.13 contract. INFERRED requires `confidence_score ∈ [0.0, 1.0]`. (Researcher-evaluated: see "Open Questions" — recommend NOT adding an `evidence` field for reasoning relations.)

**2. Cross-document edges & dangling targets**
- **D-04:** Two-pass build resolution. Pass 1 extracts reasoning edges with raw target strings (id or label); pass 2 resolves them after every doc has been extracted. Unresolved targets are dropped with a stderr warning. No stub-node creation.
- **D-05:** Both endpoints must be document-typed or concept-typed. Reject if EITHER source OR target is a code-typed node.
- **D-06:** Validation pattern follows `validate.py` shape: return error strings, do not raise.

**3. Interaction with Phase 71 temporal layer**
- **D-07:** `supersedes` auto-stamps `valid_until` on outbound edges of the superseded node.
- **D-08:** Stamp scope is **all outbound edges** of B — both reasoning and structural relations.
- **D-09:** Stamp is one-shot at supersession-edge insertion time; idempotent.
- **D-10:** Stamping mutates `valid_until` on existing edges; does NOT create new edges.

**4. Contradictions & supersession-chain rendering (REAS-03 + REAS-04)**
- **D-11:** `analyze.py` Contradictions/Chains section is confidence-gated at `confidence_score >= 0.5`; EXTRACTED edges (no score) always included.
- **D-12:** Sorting: longest chains first; pairs by `confidence_score` desc; no top-N cap initially.
- **D-13:** `analyze.py` knowledge_gaps must NOT misclassify isolated reasoning-edge endpoints as gaps.
- **D-14:** `wiki.py` gets a separate `## Reasoning Relations` subsection above `## Relationships` and above `## Historical relations`. Omit when empty.
- **D-15:** Obsidian frontmatter `reasoning_relations: [{type, target, confidence_score}]` YAML list.
- **D-16:** `report.py` GRAPH_REPORT.md gets a top-level "Contradictions and Supersession Chains" section.

### Claude's Discretion
- Exact placement of two-pass resolution logic in `build.py` (new helper vs inline).
- Whether to share resolution code with the existing `dangling stdlib import` warning pattern.
- Whether the prompt-extension lives inline in existing prompts or as a new appended block (coordinate with `PROMPT_VERSION` bump).
- Concrete YAML key naming in Obsidian frontmatter beyond `reasoning_relations`.

### Deferred Ideas (OUT OF SCOPE)
- Top-N caps on report sections.
- Stub-node creation for unresolved reasoning targets.
- Second-pass dedicated reasoning classifier prompt.
- Signal-triggered (gated) extraction.
- `evidence` field for reasoning relations (researcher recommends staying deferred — see Open Questions).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REAS-01 | `validate.py` accepts the 5 reasoning relations on doc/concept nodes; rejects on code nodes | `validate.py` Phase 53 `NEW_CONCEPT_CODE_RELATIONS` precedent (lines 52–69); per-edge loop at lines 178–214 already inspects `relation`, `confidence`, `confidence_score`. Node-type lookup needs new helper because today's loop does not consult node `file_type`. See "Architecture Patterns" §1. |
| REAS-02 | Extraction prompts emit reasoning edges with `confidence` + `confidence_score`; ADR supersession + contradiction examples | Prompt body lives in **`graphify/skill.md` Step 3 Part B**, NOT `extract.py`. 10 platform variants must be updated in lockstep; skill-prompt-drift gate (`tests/test_skill_prompt_drift.py`) enforces parity. `prompts.py::PROMPT_VERSION` (currently `"1.13.0"`) bump invalidates the confidence cache (`sha256(PROMPT_VERSION || model_id || file_hash)`). |
| REAS-03 | Contradictions & Supersession Chains analysis section; isolated reasoning-edge nodes not gaps | `analyze.py::knowledge_gaps` lines 661–685 has the isolated filter at lines 681–684 (`G.degree(n) <= 1 and not _is_file_node and not _is_concept_node`). Add reasoning-edge predicate. New chain-building producer needed; uses NetworkX DiGraph view filtered to `relation == "supersedes"`. |
| REAS-04 | GRAPH_REPORT.md + wiki.py + Obsidian render reasoning relations distinctly from structural | Phase 71-05 `## Historical relations` precedent in `wiki.py` lines 89–110 — second filtered pass over neighbors; same shape for `## Reasoning Relations`. `report.py::generate` Temporal Health section at lines 434–447 is the precedent for a top-level new section. Obsidian export uses profile-driven note rendering; frontmatter keys reach the YAML via `split_rendered_note` and rendered templates — see "Architecture Patterns" §5. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reasoning-relation vocabulary registration | Validation layer (`validate.py`) | docs (`RELATIONS.md`) | Single source of truth pattern set by Phase 53 |
| Reasoning-relation extraction | Skill orchestration layer (`skill*.md`) | `prompts.py` PROMPT_VERSION | Doc/paper/rationale extraction is LLM-driven; lives in skill prompt, not Python |
| Two-pass target resolution | Build layer (`build.py`) | — | Cross-file resolution requires the full corpus node set; only `build_from_json` sees that |
| Supersession auto-stamp on outbound edges | Build layer (`build.py`) | Phase 71 temporal layer (`temporal.py::stamp_supersessions`) | Mutates existing edge `valid_until`; sits between temporal stamp and supersession-diff stamp |
| Contradictions/Chains detection | Analysis layer (`analyze.py`) | — | Pure graph computation, no I/O |
| GRAPH_REPORT.md section | Render layer (`report.py`) | — | Existing section-conventions module |
| Wiki per-community rendering | Render layer (`wiki.py`) | — | Mirrors Historical relations subsection from Phase 71-05 |
| Obsidian frontmatter `reasoning_relations:` | Export/profile layer (`export.py` + templates) | profile/template files | Profile-driven; YAML list shape must round-trip through `split_rendered_note` |
| Knowledge-gaps reasoning-edge filter | Analysis layer (`analyze.py`) | — | Predicate fix at lines 681–684 |

---

## Standard Stack

### Core (already shipped, no new deps required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | unpinned | Graph data structure; DiGraph filtered views via `edge_subgraph` | Already the project's core abstraction (Phase 71 uses `edge_subgraph` precedent at `analyze.py:88-92`) |
| pyyaml | optional | YAML frontmatter for Obsidian export | Already used by `temporal_config.yaml`; `yaml.safe_load` is mandatory (T-71-01) |
| stdlib `html` | — | `html.escape` for any rendered LLM-derived strings | Phase 71-05 precedent at `wiki.py:112`; defense in depth against label-injection |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `pathlib` | — | Prior-graph path resolution | Already used in `build.py::_prior_graph_path` |

### Alternatives Considered (rejected)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `confidence_score` only | Add `evidence` field (Phase 53 style) | DEFERRED. Phase 53 evidence values (`annotation`, `jsdoc`, `docstring`, `test_docstring`, `inheritance`) are AST-derived markers — they do not naturally map to LLM-extracted reasoning text. Forcing one would either expand `KNOWN_EVIDENCE_VALUES` with semantic categories (`adr_block`, `header_phrase`, etc.) or accept free-text evidence (open-ended sanitization burden). Recommendation: defer per CONTEXT.md "Deferred Ideas". |
| Separate classifier prompt pass | Single semantic-prompt extension | Locked by D-01 |

**No new packages to install.**

**Version verification:** No new dependencies, so no `npm view` / `pip` registry check needed. PyYAML stays at the existing optional pin in `pyproject.toml`.

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌────────────────────────────────────────────┐
                    │  Phase 72 data flow overlay (additive only)│
                    └────────────────────────────────────────────┘

(corpus files: ADRs, md, PDFs)
        │
        ▼
[skill.md Step 3 Part B prompt] ──── extended with 5-relation taxonomy + ADR exemplars
        │  emits per-doc nodes/edges JSON (raw target string still allowed)
        ▼
graphify-out/.graphify_chunk_NN.json  (existing chunk artifacts)
        │
        ▼
[skill Step 3 Part C merge → in-memory extraction dict]
        │
        ▼
build_from_json(extraction):
        │  ┌──────────────────────────────────────────────┐
        │  │ EXISTING: _normalize_concept_code_edges       │
        │  │ EXISTING: per-edge temporal stamp (L293–310)  │
        │  │ ⊕ NEW: two-pass reasoning-target resolution   │  ← Plan 03
        │  │ EXISTING: stamp_supersessions diff (L316–320) │
        │  │ ⊕ NEW: supersedes-outbound auto-stamp         │  ← Plan 03 (after diff)
        │  │ EXISTING: validate_extraction (now 5 new rels)│  ← Plan 01
        │  │ EXISTING: federation (no-op for our path)     │
        │  │ EXISTING: G.add_node / G.add_edge            │
        │  └──────────────────────────────────────────────┘
        ▼
nx.Graph G (with reasoning edges + valid_until backstamps)
        │
        ├──▶ analyze.py:
        │     • knowledge_gaps (filter fix — D-13) ── Plan 04
        │     • NEW contradictions_and_chains()    ── Plan 04
        │
        ├──▶ report.py:
        │     • EXISTING Temporal Health section
        │     • NEW "Contradictions and Supersession Chains" section ── Plan 04
        │
        ├──▶ wiki.py:
        │     • NEW "## Reasoning Relations" subsection ── Plan 04
        │     • EXISTING "## Historical relations" subsection
        │
        └──▶ export.py (Obsidian path):
              • NEW frontmatter key reasoning_relations: [...] ── Plan 04
```

### Recommended Project Structure (no new files; all extensions in-place)

```
graphify/
├── validate.py          # +REASONING_RELATIONS frozenset, +endpoint type rule
├── prompts.py           # PROMPT_VERSION bump 1.13.0 → 1.14.0
├── skill.md             # +5-relation taxonomy, +ADR exemplars (Step 3 Part B)
├── skill-{aider,claw,codex,copilot,droid,excalidraw,opencode,trae,windows}.md   # parity
├── build.py             # +_resolve_reasoning_targets(), +_stamp_supersession_outbound()
├── analyze.py           # +contradictions_and_chains(), knowledge_gaps reasoning-edge filter
├── report.py            # +new top-level section
├── wiki.py              # +"## Reasoning Relations" subsection in _community_article
├── export.py            # +reasoning_relations frontmatter shape (via profile/template)
docs/
└── RELATIONS.md         # +"Reasoning relations (Phase 72)" section
tests/
├── test_validate.py     # +endpoint type rule tests
├── test_build.py        # +two-pass resolve, +supersedes-outbound stamp tests
├── test_analyze.py      # +knowledge_gaps reasoning fix, +chain producer
├── test_report.py       # +new section render
├── test_wiki.py         # +subsection render
├── test_export.py       # +Obsidian frontmatter
└── fixtures/
    ├── adr_supersession.md   # NEW (ADR-0028 / ADR-0042 corpus)
    └── adr_contradiction.md  # NEW
```

### Pattern 1: Frozenset Registration of New Relations (Phase 53 precedent)

**What:** Add a sibling frozenset to `validate.py` for the 5 reasoning relations and extend `KNOWN_EDGE_RELATIONS` so `warn_unknown_relations` does not stderr-spam on every emit.

**When to use:** Every time graphify accepts a new edge `relation` value.

**Example:**
```python
# graphify/validate.py — Phase 53 precedent at lines 52–69
NEW_CONCEPT_CODE_RELATIONS: frozenset[str] = frozenset({
    "documents", "tests", "realizes", "instantiates",
})

# Phase 72 extension — sibling frozenset
REASONING_RELATIONS: frozenset[str] = frozenset({
    "supports", "contradicts", "supersedes", "evolved_into", "depends_on",
})
# Also add all 5 names to KNOWN_EDGE_RELATIONS at lines 14–43
```

### Pattern 2: Per-Relation Endpoint Type Rule (NEW pattern; no exact precedent)

**What:** Phase 53's per-edge validation loop (lines 178–214) currently does not look at node `file_type`. D-05 requires both endpoints to be document- or concept-typed. The loop already builds `node_ids = {n["id"] for n in data.get("nodes", []) ...}` at line 156 — that comprehension needs to grow into a `node_types: dict[str, str]` lookup.

**When to use:** REAS-01 endpoint enforcement.

**Example:**
```python
# In validate_extraction(), expand the comprehension at line 156:
node_types: dict[str, str] = {
    n["id"]: str(n.get("file_type", ""))
    for n in data.get("nodes", []) if isinstance(n, dict) and "id" in n
}
node_ids = set(node_types)

# Inside the per-edge loop after the existing concept↔code block (~line 214):
if rel in REASONING_RELATIONS:
    src_t = node_types.get(edge.get("source", ""), "")
    tgt_t = node_types.get(edge.get("target", ""), "")
    # D-05: BOTH endpoints must be doc- or concept-typed.
    # `concept` is not a file_type in VALID_FILE_TYPES — concept-ness is detected
    # in analyze.py via _is_concept_node (no source extension). For validate.py
    # at write time, we approximate: reject only when EITHER endpoint is "code".
    if src_t == "code" or tgt_t == "code":
        errors.append(
            f"Edge {i} relation={rel!r} requires non-code endpoints; "
            f"got source.file_type={src_t!r}, target.file_type={tgt_t!r}"
        )
    # confidence_score rule (CCONF v1.13)
    if conf == "INFERRED":
        raw = edge.get("confidence_score")
        try:
            score = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            score = None
        if score is None or not (0.0 <= score <= 1.0):
            errors.append(
                f"Edge {i} relation={rel!r} confidence=INFERRED requires "
                f"'confidence_score' in [0.0, 1.0]"
            )
```

**Subtlety on "concept-typed":** `VALID_FILE_TYPES = {"code", "document", "paper", "image", "rationale"}` does NOT include `"concept"`. `analyze.py::_is_concept_node` (lines 146–164) detects concept nodes heuristically by the absence of a real file extension. In `validate.py` at write-time we cannot run that heuristic (the concept may legitimately have empty `source_file`). Recommendation: validate by **negation** — reject when EITHER endpoint has `file_type == "code"`. This satisfies D-05 ("reject if either source or target is code-typed") without requiring a new node type.

### Pattern 3: Two-Pass Build Resolution (NOVEL — no precedent)

**What:** Today, `build_from_json` is single-pass: it calls `_normalize_concept_code_edges`, stamps temporal fields, runs `stamp_supersessions`, validates, builds the graph. Edge `target` is expected to be a node `id` already.

For reasoning relations, the LLM extractor sees one document at a time (per chunk in Step 3 Part B) and may emit `target: "ADR-0028"` (a label or partial id) without knowing whether `ADR-0028` exists as a node yet. The skill Step 3 Part C merge collects all chunks before calling `build_from_json` — so by the time `build_from_json` runs, the full node set IS available. The two-pass resolution is therefore a **build-time pass over the merged extraction dict**, not a corpus-wide re-extraction.

**Where pass-1 stores raw target strings:** in the edge dict's existing `target` field. Convention: if `target` does not match any `node["id"]`, treat it as a **label-or-partial-id reference** to be resolved.

**Where pass-2 runs:** in `build_from_json`, **before** `_normalize_concept_code_edges` (which sorts and merges by `(source, target, relation)` — must run on resolved targets) and **before** the temporal stamp block (so unresolved drops don't waste a stamp).

**When extract.py is the producer:** it isn't, for reasoning relations. AST extractors do not emit doc/concept edges. The semantic skill prompt is the producer, and it operates per-chunk but writes to disk, with merge happening in skill Step 3 Part C. The merged dict reaches `build_from_json` with all docs visible.

**Example:**
```python
# graphify/build.py — new helper, called near the top of build_from_json
def _resolve_reasoning_targets(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve raw target strings on reasoning edges. Drop unresolved with stderr warning.

    Returns a NEW edges list (filtered). Pass-1 trusts whatever the extractor emitted.
    Pass-2 walks reasoning edges and tries:
      a) target already matches a node["id"] → no-op
      b) target matches a node["label"] (case-insensitive) → rewrite to that node["id"]
      c) target appears as a substring of any node["id"] → rewrite (deterministic by sort)
      d) otherwise drop with a stderr warning (D-04)
    """
    from .validate import REASONING_RELATIONS
    by_id = {n["id"]: n for n in nodes if isinstance(n, dict) and "id" in n}
    label_to_id: dict[str, str] = {}
    for n in nodes:
        lbl = n.get("label")
        if isinstance(lbl, str) and lbl:
            label_to_id.setdefault(lbl.lower(), n["id"])
    out: list[dict[str, Any]] = []
    for e in edges:
        if e.get("relation") not in REASONING_RELATIONS:
            out.append(e); continue
        tgt = e.get("target", "")
        if tgt in by_id:
            out.append(e); continue
        resolved = label_to_id.get(str(tgt).lower())
        if resolved is None:
            # deterministic fallback: lex-sorted substring match
            cands = sorted(nid for nid in by_id if str(tgt).lower() in nid.lower())
            resolved = cands[0] if cands else None
        if resolved is None:
            print(
                f"[graphify] dangling reasoning edge {e.get('source','?')} "
                f"-{e.get('relation')}-> {tgt!r}: no matching node, dropping",
                file=sys.stderr,
            )
            continue
        e2 = dict(e); e2["target"] = resolved
        out.append(e2)
    return out
```

Call site (insert in `build_from_json` immediately after the `extraction["edges"] = [dict(e) for e in extraction.get("edges", [])]` copy on line ~268, BEFORE `_normalize_concept_code_edges`):

```python
extraction["edges"] = _resolve_reasoning_targets(extraction["nodes"], extraction["edges"])
```

### Pattern 4: Supersedes Auto-Stamp on Outbound Edges (NEW; sits ON TOP of Phase 71)

**What:** When `A supersedes B` is present in the edge list, every other outbound edge of `B` (in the SAME edge list) gets `valid_until = run_now`. Idempotent because we use `if e.get("valid_until") is None` before stamping (D-09, D-10).

**Where it runs:** `build_from_json`, AFTER the temporal-stamp block at lines 293–310 (which sets `valid_from` and default `valid_until=None`), and AFTER `stamp_supersessions(...)` at lines 316–320 (Phase 71's INFERRED-disappearance diff). Reasoning supersession is a write-time concept emerging from the new edges; Phase 71's `stamp_supersessions` is a diff against the prior on-disk graph for INFERRED edges that no longer appear. The two stamping mechanisms operate on disjoint trigger conditions and write to the same `valid_until` field — they do NOT conflict because:

1. Phase 71's `stamp_supersessions` stamps `valid_until` ONLY on edges from the prior graph that disappeared in this run AND were INFERRED. It does NOT touch new edges.
2. Phase 72's outbound stamp acts on currently-present outbound edges of `B`, the superseded node. These are exactly the edges Phase 71 left at `valid_until=None` because they DID still appear this run.

Therefore: no double-stamp, no stomp. Edges that fall under both rules (rare: an outbound edge of `B` that also disappeared this run AND was INFERRED) would be stamped by Phase 71 first; Phase 72's `if e.get("valid_until") is None` check makes the second pass a no-op.

**Risk:** If a supersedes edge is itself superseded in a later run (`A2 supersedes B` after `A supersedes B` already shipped), Phase 71's normal stamping rules apply to the supersedes edge itself. The outbound edges of `B` were stamped on the first run; rerunning is a no-op (idempotent per D-10).

**Example:**
```python
# graphify/build.py — new helper, called AFTER stamp_supersessions(...) at line ~320
def _stamp_supersession_outbound(
    edges: list[dict[str, Any]],
    run_now: str,
) -> None:
    """D-07/D-08/D-09/D-10: For every `A supersedes B`, stamp valid_until=run_now
    on every other outbound edge of B that is still currently-valid.
    Mutates `edges` in place. Idempotent: skips edges whose valid_until is already set.
    """
    superseded_ids = {
        str(e["source"])  # NOTE: orientation — see "Direction" below
        for e in edges
        if e.get("relation") == "supersedes" and "source" in e and "target" in e
    }
    # Wait — orientation: "A supersedes B" should mean A → B (A is canonical, B is superseded).
    # The SUPERSEDED node is the TARGET, not the source. Re-do:
    superseded_ids = {
        str(e["target"])
        for e in edges
        if e.get("relation") == "supersedes"
    }
    if not superseded_ids:
        return
    for e in edges:
        if e.get("relation") == "supersedes":
            continue
        if str(e.get("source", "")) not in superseded_ids:
            continue
        if e.get("valid_until") is None:  # D-09 idempotent
            e["valid_until"] = run_now
```

**Direction note (CRITICAL for plan):** The skill prompt and exemplars must be unambiguous: `supersedes` is oriented **newer → older** (A supersedes B means A replaces B; B is superseded). Therefore the SUPERSEDED node is the edge `target`, not `source`. The auto-stamp iterates outbound edges of `target`. Document this in `docs/RELATIONS.md`.

### Pattern 5: Obsidian Frontmatter `reasoning_relations:` (profile-template-driven)

**What:** Obsidian export at `export.py::to_obsidian` (lines 571+) goes through a profile pipeline: `load_profile → classify → render_all → split_rendered_note → apply_merge_plan`. Frontmatter is part of the rendered note text; `split_rendered_note` (line 821) splits it from the body before merge. New frontmatter keys reach the YAML by appearing in the **template files** the profile loads.

**Discretionary call:** D-15 says `reasoning_relations: [{type, target, confidence_score}]`. Two implementation paths:
1. **Template-side:** Edit `graphify/builtin_templates/` to render the YAML list when the rendering context contains a `reasoning_relations` key.
2. **classify-side:** `classify(G, communities, profile, cohesion=cohesion)` builds `per_node` and `per_community` ctx dicts. Inject `reasoning_relations: [...]` into `per_node[ctx]` for each doc/concept node that has outbound reasoning edges.

**Recommendation:** Both. classify must populate the ctx; the default template must render it (omit when empty per Phase 71-05 precedent). Verify the Phase 71 vault profile templates do not already use the `reasoning_relations` key — grep returns 0 hits, so no collision.

**Round-trip safety:** `split_rendered_note` (existing public helper) handles arbitrary YAML keys via `frontmatter_fields` dict — it does NOT enumerate known keys. Adding a new key requires no changes to the splitter. The merge layer (`compute_merge_plan` / `apply_merge_plan`) treats frontmatter as opaque dict; new keys ride through.

### Anti-Patterns to Avoid

- **Hand-editing one `skill*.md` and forgetting the other 9.** The drift gate (`tests/test_skill_prompt_drift.py`) will fail CI. Use a shared content block sourced from a single source of truth or copy carefully.
- **Re-inventing per-edge validation outside `validate.py`.** REAS-01 enforcement belongs in `validate_extraction`, not `build.py`. `build.py` already prints the first error and continues — keep that behavior.
- **Stamping `valid_until` inside the same loop that adds reasoning edges.** Run the two-pass resolution and the outbound-stamp as separate, narrow helpers — this matches Phase 71's discipline of one-helper-per-concern (cf. `temporal.py::stamp_supersessions` is its own function).
- **Adding `evidence` field for reasoning relations.** No extractor signal naturally maps to the existing `KNOWN_EVIDENCE_VALUES` set. Stay deferred.
- **Top-N caps.** D-12 says "no top-N cap initially." Don't slip one in.
- **Treating `concept` as a `file_type`.** It is NOT in `VALID_FILE_TYPES`. Concept-ness is heuristic at analyze time. Validate by rejecting `code` endpoints, not by requiring `concept` endpoints.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reasoning-relation taxonomy validation | Custom inline guards in extractors | `validate.py` frozenset + per-edge loop (Phase 53 pattern) | Single source of truth; existing module-wide convention |
| Cross-document target resolution | Stub-node creation | Two-pass resolve + drop (D-04) | Stub nodes pollute communities/clustering and hide real corpus gaps |
| Supersession-chain detection | Recursive Python on raw edge list | NetworkX `DiGraph.edge_subgraph(filter_edges)` + `nx.dag_longest_path` | networkx already in deps; correct DAG handling for free |
| YAML frontmatter splitting in Obsidian export | Re-implement parser | `export.py::split_rendered_note` (Plan 01 public helper, line 821) | Stable contract |
| HTML-escape on rendered LLM strings | Custom regex | `html.escape(...)[:64]` (Phase 71-05 precedent at `wiki.py:112`) | T-71-15 / T-71-19 mitigation already audited |
| Test clock injection | Mocking `datetime` | `monkeypatch.setenv("GRAPHIFY_RUN_TS", "2026-...")` (already supported by `temporal.py::run_now_iso`) | Phase 71 test pattern at `tests/test_temporal.py:35-37` |

**Key insight:** Phase 72 is 80% layered repetition of established patterns (Phase 53 vocabulary registration, Phase 71 temporal stamp ordering, Phase 71-05 wiki subsection rendering) and 20% genuinely new (two-pass resolution, supersedes-outbound stamp). Lean on the precedents — they have already been audited and threat-modeled.

---

## Common Pitfalls

### Pitfall 1: Forgetting one of the 10 skill prompt files
**What goes wrong:** Prompt drift gate fails CI, or worse — drift gate doesn't cover the prompt body line, and the affected platform silently emits no reasoning edges.
**Why it happens:** Multi-platform skill packaging is a graphify quirk; new contributors don't know about it.
**How to avoid:** Always grep for any prompt-resident phrase across `graphify/skill*.md` before committing. Run `pytest tests/test_skill_prompt_drift.py -q` locally.
**Warning signs:** Test failure naming a specific platform skill file; one ADR exemplar appearing in 9 of 10 files.

### Pitfall 2: PROMPT_VERSION not bumped → stale cache, no re-extraction
**What goes wrong:** Existing graphs run on prior corpora won't re-extract reasoning relations because `sha256(PROMPT_VERSION || model_id || file_hash)` is unchanged.
**Why it happens:** Prompt edits ship without touching `graphify/prompts.py::PROMPT_VERSION`.
**How to avoid:** Bump `PROMPT_VERSION` from `"1.13.0"` → `"1.14.0"` (or `"2.0.0"` to align with milestone) in the SAME commit as the prompt body change.
**Warning signs:** No new reasoning edges appear on a re-run of a previously-extracted corpus.

### Pitfall 3: supersedes orientation flipped
**What goes wrong:** Auto-stamp lands on outbound edges of the WRONG node — the canonical replacement, not the deprecated original. Phase 71's `## Historical relations` then shows the canonical doc as historical and the obsolete one as current.
**Why it happens:** The English idiom "A supersedes B" → A is newer; but the implementer codes target=newer.
**How to avoid:** Document orientation explicitly in `docs/RELATIONS.md` AND in the skill prompt exemplar. Add a unit test where ADR-0042 supersedes ADR-0028 and assert that ADR-0028's outbound edges get `valid_until` stamped.
**Warning signs:** Wiki community articles list ADR-0042 (the newer doc) under `## Historical relations`.

### Pitfall 4: Two-pass resolution drops legitimate edges
**What goes wrong:** Label-based resolution fails because the LLM returned `"ADR-0028"` and the actual node id is `adr_0028` (lowercase, underscore). All edges drop silently with stderr warnings.
**Why it happens:** `_make_id` (extract.py) lowercases and underscore-joins; LLM emits human label.
**How to avoid:** Resolution must try (a) exact id, (b) case-insensitive label, (c) deterministic substring match on id. The example helper in Pattern 3 covers all three.
**Warning signs:** Many `[graphify] dangling reasoning edge` warnings on a corpus the user knows has resolvable references.

### Pitfall 5: knowledge_gaps filter too narrow
**What goes wrong:** A doc node with EXACTLY one reasoning edge (degree=1) and no structural edges still appears as "isolated" because the predicate `_is_file_node OR _is_concept_node` returns False for documents.
**Why it happens:** `_is_concept_node` checks for missing file extension; a `.md` doc has an extension, so it's "concrete," but it's still legitimately tagged with a reasoning edge.
**How to avoid:** Add a third disjunct: `OR has_reasoning_edge(G, n)`. Implementation:
```python
def _has_reasoning_edge(G, n) -> bool:
    from .validate import REASONING_RELATIONS
    return any(
        G.edges[n, m].get("relation") in REASONING_RELATIONS
        for m in G.neighbors(n)
    )
```
**Warning signs:** ADR documents with a single `supersedes` edge appearing in the gaps list of GRAPH_REPORT.md.

### Pitfall 6: Confidence gate at 0.5 silently hides EXTRACTED edges
**What goes wrong:** `confidence_score >= 0.5` is gated, but EXTRACTED edges may not have `confidence_score` at all (per the existing CCONF v1.13 contract — EXTRACTED implies confidence_score=1.0 by convention but is not always emitted).
**Why it happens:** Naive `edge.get("confidence_score", 0.0) >= 0.5` excludes EXTRACTED edges that omit the field.
**How to avoid:** Gate is `confidence == "EXTRACTED" OR (confidence_score is not None AND confidence_score >= 0.5)`. D-11 says: "EXTRACTED edges (no score) are always included."
**Warning signs:** Report section is empty even though an EXTRACTED `supersedes` edge exists.

### Pitfall 7: Supersession chain detection misses cycles
**What goes wrong:** If a corpus contains `A supersedes B` and `B supersedes A` (extraction error), `nx.dag_longest_path` raises on cycle.
**Why it happens:** LLM extraction can hallucinate symmetric edges.
**How to avoid:** Wrap in `try/except nx.NetworkXUnfeasible:`; on cycle, fall back to listing the cycle members and emit a stderr warning.
**Warning signs:** GRAPH_REPORT.md generation crashes on a corpus with conflicting supersession edges.

---

## Code Examples

### Two-pass resolution + outbound stamp wiring in `build_from_json`

```python
# graphify/build.py — INSIDE build_from_json, modifications shown with ⊕ markers
extraction = dict(extraction)
extraction["nodes"] = list(extraction.get("nodes", []))
extraction["edges"] = [dict(e) for e in extraction.get("edges", [])]
hyper_in = extraction.get("hyperedges")
if hyper_in is not None:
    extraction["hyperedges"] = [dict(h) for h in hyper_in]

# ⊕ Phase 72 (REAS, D-04): two-pass reasoning-target resolution.
# Runs BEFORE _normalize_concept_code_edges so the canonical sort sees resolved targets.
extraction["edges"] = _resolve_reasoning_targets(extraction["nodes"], extraction["edges"])

nodes_for_norm = [n for n in extraction["nodes"] if isinstance(n, dict)]
_normalize_concept_code_edges(nodes_for_norm, extraction["edges"])

# Phase 71 temporal stamp (existing, lines 293–310) — unchanged
run_now = run_now_iso()
decay_cfg = load_decay_config()
for e in extraction["edges"]:
    e.setdefault("valid_from", run_now)
    e.setdefault("valid_until", None)
    if "decay_weight" not in e:
        if e.get("confidence") == "EXTRACTED":
            e["decay_weight"] = 1.0
        else:
            e["decay_weight"] = compute_decay_weight(
                relation=e.get("relation", ""),
                valid_from=e["valid_from"],
                run_now=run_now,
                config=decay_cfg,
            )

# Phase 71 supersession diff against prior graph.json (existing)
extraction["edges"] = stamp_supersessions(
    new_edges=extraction["edges"],
    prior_graph_path=_prior_graph_path(target_dir, resolved_output=resolved_output),
    run_now=run_now,
)

# ⊕ Phase 72 (REAS, D-07/D-08/D-09/D-10): supersedes auto-stamp on outbound edges.
# Runs AFTER stamp_supersessions (Phase 71) so the temporal stamp values are stable.
_stamp_supersession_outbound(extraction["edges"], run_now)
```

### Contradictions and Chains producer

```python
# graphify/analyze.py — new function
import networkx as nx
from .validate import REASONING_RELATIONS  # noqa: I001

def contradictions_and_chains(G: "nx.Graph") -> dict:
    """D-11/D-12: Return contradiction pairs and supersession chains.

    Output shape:
        {
          "contradictions": [
              {"a": str, "b": str, "confidence_score": float, "source_file": str},
              ...
          ],
          "supersession_chains": [
              {"path": [str, ...], "length": int, "confidence_scores": [float, ...]},
              ...
          ],
        }
    """
    # Filter helper: D-11 confidence gate.
    def _gated(d: dict) -> bool:
        if d.get("confidence") == "EXTRACTED":
            return True
        s = d.get("confidence_score")
        try:
            return s is not None and float(s) >= 0.5
        except (TypeError, ValueError):
            return False

    # Build a directed view restricted to supersedes edges only.
    DG = nx.DiGraph()
    contradictions: list[dict] = []
    for u, v, d in G.edges(data=True):
        rel = d.get("relation")
        if rel not in REASONING_RELATIONS or not _gated(d):
            continue
        # Honor original direction even on undirected G (Phase 53 _src/_tgt convention)
        s = d.get("_src", u); t = d.get("_tgt", v)
        if rel == "supersedes":
            DG.add_edge(s, t, **d)
        elif rel == "contradicts":
            score = float(d.get("confidence_score", 1.0))
            contradictions.append({
                "a": s, "b": t,
                "confidence_score": score,
                "source_file": d.get("source_file", ""),
            })

    # D-12: contradictions sorted by score desc.
    contradictions.sort(key=lambda x: -x["confidence_score"])

    # Chains: find all maximal directed paths in DG.
    chains: list[dict] = []
    if DG.number_of_edges() > 0:
        try:
            # Heads = nodes with no incoming supersedes; iterate longest path from each.
            heads = [n for n in DG.nodes if DG.in_degree(n) == 0]
            for h in heads:
                # DFS lexicographically; collect deepest path.
                stack: list[tuple[str, list[str]]] = [(h, [h])]
                while stack:
                    cur, path = stack.pop()
                    succs = sorted(DG.successors(cur))
                    if not succs:
                        if len(path) >= 2:
                            scores = [float(DG.edges[a, b].get("confidence_score", 1.0))
                                      for a, b in zip(path, path[1:])]
                            chains.append({
                                "path": path,
                                "length": len(path),
                                "confidence_scores": scores,
                            })
                    for s in succs:
                        if s in path:  # cycle guard
                            continue
                        stack.append((s, path + [s]))
        except nx.NetworkXUnfeasible:
            print("[graphify] supersession cycle detected — chain output truncated",
                  file=__import__("sys").stderr)

    # D-12: longest chains first.
    chains.sort(key=lambda c: -c["length"])
    return {"contradictions": contradictions, "supersession_chains": chains}
```

### Wiki subsection (mirrors Phase 71-05 Historical relations at `wiki.py:89–110`)

```python
# graphify/wiki.py — INSIDE _community_article, INSERT BEFORE the existing
# "## Relationships" section at line 70.
# (Note: D-14 says above ## Relationships AND above ## Historical relations.)
import html  # already imported
from graphify.validate import REASONING_RELATIONS

reasoning: list[tuple[str, str, str | None]] = []  # (neighbor_label, rel, score_str_or_none)
seen_r: set[tuple[str, str, str]] = set()
for nid in nodes:
    for neighbor in G.neighbors(nid):
        ed = G.edges[nid, neighbor]
        rel = ed.get("relation")
        if rel not in REASONING_RELATIONS:
            continue
        s = ed.get("_src", nid); t = ed.get("_tgt", neighbor)
        key = (s, t, str(rel))
        if key in seen_r:
            continue
        seen_r.add(key)
        neighbor_label = G.nodes[t if s == nid else s].get("label", neighbor)
        score = ed.get("confidence_score")
        score_s = f"{float(score):.2f}" if isinstance(score, (int, float)) else None
        reasoning.append((neighbor_label, str(rel), score_s))

if reasoning:
    lines += ["## Reasoning Relations", ""]
    for neighbor_label, rel, score_s in reasoning:
        safe_label = html.escape(neighbor_label)[:64]
        suffix = f" (confidence {score_s})" if score_s else ""
        lines.append(f"- {rel}: [[{safe_label}]]{suffix}")
    lines.append("")
```

### GRAPH_REPORT.md section (mirrors Temporal Health at `report.py:434-447`)

```python
# graphify/report.py — INSIDE generate(), INSERT before or after "## Temporal Health" block
from .analyze import contradictions_and_chains
_cc = contradictions_and_chains(G)
if _cc["contradictions"] or _cc["supersession_chains"]:
    lines += ["", "## Contradictions and Supersession Chains", ""]
    if _cc["supersession_chains"]:
        lines += ["### Supersession Chains (longest first)", ""]
        for chain in _cc["supersession_chains"]:
            path_str = " → ".join(
                _sanitize_md(G.nodes[n].get("label", n)) for n in chain["path"]
            )
            scores_avg = (
                sum(chain["confidence_scores"]) / len(chain["confidence_scores"])
                if chain["confidence_scores"] else 1.0
            )
            lines.append(f"- {path_str}  (length {chain['length']}, avg confidence {scores_avg:.2f})")
        lines.append("")
    if _cc["contradictions"]:
        lines += ["### Contradiction Pairs (highest confidence first)", ""]
        for c in _cc["contradictions"]:
            la = _sanitize_md(G.nodes[c["a"]].get("label", c["a"]))
            lb = _sanitize_md(G.nodes[c["b"]].get("label", c["b"]))
            src = c["source_file"] or "—"
            lines.append(
                f"- `{la}` ⟂ `{lb}`  (confidence {c['confidence_score']:.2f}, source `{src}`)"
            )
        lines.append("")
```

### Test fixture pattern (clock injection, ADR supersession)

```python
# tests/test_build.py — supersession outbound stamp test
def test_supersedes_outbound_stamp(monkeypatch):
    monkeypatch.setenv("GRAPHIFY_RUN_TS", "2026-05-07T12:00:00+00:00")
    extraction = {
        "schema_version": "2.0",
        "nodes": [
            {"id": "adr_0028", "label": "ADR-0028", "file_type": "document",
             "source_file": "docs/adr/0028.md"},
            {"id": "adr_0042", "label": "ADR-0042", "file_type": "document",
             "source_file": "docs/adr/0042.md"},
            {"id": "concept_x", "label": "Concept X", "file_type": "document",
             "source_file": "docs/concepts/x.md"},
        ],
        "edges": [
            # ADR-0042 supersedes ADR-0028  (newer → older, target = superseded)
            {"source": "adr_0042", "target": "adr_0028", "relation": "supersedes",
             "confidence": "EXTRACTED", "source_file": "docs/adr/0042.md"},
            # Outbound edge of the superseded node — should get valid_until stamped
            {"source": "adr_0028", "target": "concept_x", "relation": "supports",
             "confidence": "INFERRED", "confidence_score": 0.8,
             "source_file": "docs/adr/0028.md"},
        ],
    }
    G = build_from_json(extraction)
    # The outbound edge of adr_0028 must now carry valid_until = the run timestamp.
    ed = G.edges["adr_0028", "concept_x"]
    assert ed["valid_until"] == "2026-05-07T12:00:00+00:00"
    # The supersedes edge itself remains currently-valid (valid_until = None).
    sup = G.edges["adr_0042", "adr_0028"]
    assert sup.get("valid_until") is None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-pass build (target must already be a known id) | Two-pass build (resolve raw target strings, drop unresolved) | Phase 72 | New pattern — first multi-pass build helper |
| Temporal stamping ONLY on edge disappearance (Phase 71) | + Auto-stamp on `supersedes` insertion (Phase 72) | Phase 72 | Two stamping triggers; disjoint write conditions; idempotent |
| `KNOWN_EDGE_RELATIONS` covers ~30 structural/semantic relations | + 5 reasoning relations (`supports`, `contradicts`, `supersedes`, `evolved_into`, `depends_on`) | Phase 72 | Frozenset extension |
| `wiki.py` per-community renders Relationships + (Phase 71-05) Historical relations | + Reasoning Relations subsection | Phase 72 | Additive section; omit when empty |

**Deprecated/outdated:** None. Phase 72 is purely additive; legacy graphs without reasoning relations load unchanged via `validate_extraction_for_read` (the read-mode is permissive about absent fields).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The skill Step 3 Part C merge is the single point where all per-doc chunks are combined before `build_from_json` runs, so the two-pass resolver sees the full node set. | Pattern 3 | If a re-extraction path bypasses skill merge (e.g., direct CLI call `graphify run` with a pre-shipped extraction.json), some reasoning targets will be unresolvable at first run. **Verification:** the existing `extraction.json` test fixture (`tests/fixtures/extraction.json`) confirms the dict-shape contract; verify by running the chosen 2-pass on any fixture and asserting no spurious drops. [VERIFIED: code grep confirms `build_from_json` is the single corpus-wide assembly point in this codebase] |
| A2 | `confidence_score` on EXTRACTED reasoning edges is omitted by convention rather than required. | Pitfall 6 | If extractor emits `confidence_score=1.0` on EXTRACTED edges, the gate `confidence == "EXTRACTED" OR score >= 0.5` is over-permissive but never under-permissive. Safe direction. [CITED: docs/RELATIONS.md Phase 53 confidence rules — EXTRACTED requires `evidence` not `confidence_score`] |
| A3 | NetworkX `edge_subgraph` view + `DiGraph` works on graphify's undirected `Graph` because `_src`/`_tgt` attrs are preserved on every edge (Phase 53 W2 invariant). | Code Examples §contradictions_and_chains | If `_src`/`_tgt` not present on reasoning edges, direction is lost. **Mitigation:** the build.py edge-add loop at lines ~395 sets `attrs["_src"]`/`attrs["_tgt"]` on EVERY edge — verified. [VERIFIED: `graphify/build.py:395-396`] |
| A4 | The 10-skill-file drift gate (`tests/test_skill_prompt_drift.py`) covers prompt-body changes, not just header metadata. | Pitfall 1 | If gate is metadata-only, prompt drift can ship undetected. **Mitigation:** plan should include a proof-of-coverage assertion (induce a prompt diff in skill.md only, run the test, confirm fail). [ASSUMED — gate file not read in this research session] |

---

## Open Questions

1. **Should reasoning relations carry an `evidence` field analogous to Phase 53?**
   - What we know: D-03 says "researcher to decide." The Phase 53 evidence values (`annotation`, `jsdoc`, `docstring`, `test_docstring`, `inheritance`) are AST-derived signals; reasoning relations are LLM-extracted from prose. No natural mapping exists.
   - What's unclear: Whether a future audit will demand a citation-trail field for reasoning edges (e.g., the exact ADR section that triggered the extraction).
   - Recommendation: **Defer.** `confidence_score` plus the existing `source_file` and `source_location` fields already provide auditability. If audit demands more, add a `citation: {section: str, snippet: str}` field in a future phase rather than overloading the structural `evidence` enum.

2. **Concrete YAML key naming for Obsidian frontmatter beyond `reasoning_relations`.**
   - What we know: D-15 fixes the outer key as `reasoning_relations` and the per-item shape as `{type, target, confidence_score}`.
   - What's unclear: Whether `target` should be a wikilink-encoded string (`"[[ADR-0028]]"`) for Obsidian Dataview convenience, or a bare label (`"ADR-0028"`).
   - Recommendation: Bare label. Dataview can wikilink-format on render via `link()` function; bare labels keep the YAML query-friendly without wrapping characters.

3. **Should `analyze.py::contradictions_and_chains` deduplicate symmetric `contradicts` edges?**
   - What we know: `contradicts` is naturally symmetric. The LLM may emit both `A contradicts B` and `B contradicts A`.
   - What's unclear: Whether the report section should show one row or two.
   - Recommendation: Deduplicate by `frozenset({source, target})` keyed pair, keep the higher `confidence_score`. Document this in the implementation comment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.10+ | Whole project | ✓ | 3.10 / 3.12 (CI) | — |
| networkx | Graph algorithms | ✓ | unpinned | — |
| pyyaml | Optional YAML loading; Obsidian frontmatter | ✓ (optional install) | unpinned | Defaults already in code (cf. `temporal.py::load_decay_config` ImportError handler) |
| pytest | Tests | ✓ | — | — |

**No external service dependencies.** All Phase 72 work is pure code/config; no need to probe Docker, databases, network services, etc.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `pytest tests/test_validate.py tests/test_build.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REAS-01 | `validate.py` accepts 5 reasoning relations on doc/concept; rejects on code | unit | `pytest tests/test_validate.py::test_reasoning_relations_accepted -x` | ❌ Wave 0 |
| REAS-01 | INFERRED reasoning edge requires `confidence_score ∈ [0.0, 1.0]` | unit | `pytest tests/test_validate.py::test_reasoning_inferred_score -x` | ❌ Wave 0 |
| REAS-01 | Code-typed endpoint on reasoning edge produces validation error | unit | `pytest tests/test_validate.py::test_reasoning_rejects_code_endpoint -x` | ❌ Wave 0 |
| REAS-01 | Legacy graph.json without reasoning relations loads via `validate_extraction_for_read` | unit | `pytest tests/test_validate.py::test_legacy_no_reasoning_loads -x` | ❌ Wave 0 |
| REAS-02 | All 10 `skill*.md` files contain ADR supersession exemplar (drift gate) | unit | `pytest tests/test_skill_prompt_drift.py -q` | ✅ exists; needs new assertion |
| REAS-02 | `prompts.py::PROMPT_VERSION` bumped from "1.13.0" | unit | `pytest tests/test_skill_prompt_drift.py::test_prompt_version_bumped -x` | ❌ Wave 0 |
| REAS-03 | `analyze.py::contradictions_and_chains` returns expected shape on ADR fixture | unit | `pytest tests/test_analyze.py::test_contradictions_and_chains -x` | ❌ Wave 0 |
| REAS-03 | Isolated reasoning-edge node NOT in `knowledge_gaps` | unit | `pytest tests/test_analyze.py::test_knowledge_gaps_excludes_reasoning_endpoints -x` | ❌ Wave 0 |
| REAS-03 / D-12 | Longest supersession chain rendered first | unit | `pytest tests/test_analyze.py::test_chain_sort_longest_first -x` | ❌ Wave 0 |
| REAS-04 | GRAPH_REPORT.md contains "Contradictions and Supersession Chains" section | unit | `pytest tests/test_report.py::test_contradictions_section -x` | ❌ Wave 0 |
| REAS-04 | wiki community article contains "## Reasoning Relations" subsection | unit | `pytest tests/test_wiki.py::test_reasoning_relations_subsection -x` | ❌ Wave 0 |
| REAS-04 | wiki subsection omitted when no reasoning edges (Phase 71-05 mirror) | unit | `pytest tests/test_wiki.py::test_reasoning_relations_omit_when_empty -x` | ❌ Wave 0 |
| REAS-04 | Obsidian export note frontmatter contains `reasoning_relations:` YAML list | unit | `pytest tests/test_export.py::test_obsidian_reasoning_relations_frontmatter -x` | ❌ Wave 0 |
| D-04 | Two-pass resolution drops unresolved targets with stderr warning | unit | `pytest tests/test_build.py::test_resolve_drops_unresolved -x` | ❌ Wave 0 |
| D-04 | Two-pass resolution rewrites label-based target to id | unit | `pytest tests/test_build.py::test_resolve_label_to_id -x` | ❌ Wave 0 |
| D-07/D-08 | `supersedes` edge auto-stamps `valid_until` on outbound edges of target | unit | `pytest tests/test_build.py::test_supersedes_outbound_stamp -x` | ❌ Wave 0 |
| D-09 | Auto-stamp is idempotent across re-runs | unit | `pytest tests/test_build.py::test_supersedes_stamp_idempotent -x` | ❌ Wave 0 |
| D-10 | Auto-stamp does NOT create new edges | unit | `pytest tests/test_build.py::test_supersedes_no_new_edges -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_validate.py tests/test_build.py tests/test_analyze.py -x -q`
- **Per wave merge:** `pytest tests/test_validate.py tests/test_build.py tests/test_analyze.py tests/test_report.py tests/test_wiki.py tests/test_export.py tests/test_skill_prompt_drift.py -q`
- **Phase gate:** `pytest tests/ -q` green on Python 3.10 AND 3.12 before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/fixtures/adr_supersession.md` — ADR-0028/ADR-0042 markdown corpus for end-to-end test
- [ ] `tests/fixtures/adr_contradiction.md` — ADR contradiction corpus
- [ ] `tests/fixtures/extraction_with_reasoning.json` — pre-built extraction dict for build.py tests (so they don't depend on skill prompt being correctly extended)
- [ ] `tests/test_validate.py` — 4 new tests for REAS-01
- [ ] `tests/test_build.py` — 5 new tests for D-04 + D-07..D-10
- [ ] `tests/test_analyze.py` — 3 new tests for REAS-03
- [ ] `tests/test_report.py` — 1 new test for REAS-04
- [ ] `tests/test_wiki.py` — 2 new tests for REAS-04
- [ ] `tests/test_export.py` — 1 new test for REAS-04
- [ ] `tests/test_skill_prompt_drift.py` — extend with ADR-exemplar parity assertion

---

## Security Domain

> Default-enabled. Project security model is defined by `graphify/security.py` + `SECURITY.md`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `validate.py::validate_extraction` returns error list; new `REASONING_RELATIONS` rule layered into existing per-edge loop |
| V5 Input Validation | yes | `html.escape(...)[:64]` on any LLM-derived neighbor label rendered into wiki/report (Phase 71-05 precedent at `wiki.py:112`) |
| V6 Cryptography | no | — |

### Known Threat Patterns for graphify Phase 72

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM-injected reasoning target with shell metacharacters | Tampering | Two-pass resolver only matches against id/label literals; non-matches drop. No `eval`/subprocess use. |
| LLM-injected markdown in `confidence_score` field | Tampering | `confidence_score` cast to `float()` with try/except; non-float drops the edge silently (existing pattern at `validate.py:194-198`). |
| LLM-injected wikilink/HTML in neighbor labels rendered to wiki | Tampering | `html.escape(neighbor_label)[:64]` (T-71-15 / T-71-19 precedent). |
| Supersedes orientation flip → false historical labeling | Information disclosure (incorrect) | Direction documented in `docs/RELATIONS.md`; unit test asserts target = superseded node. |
| Cycle in supersession chain → DoS via infinite path enumeration | DoS | DFS with `if s in path: continue` cycle guard; `try/except nx.NetworkXUnfeasible`. |
| Unbounded chain enumeration on adversarial corpus | DoS | Mitigated by inherent corpus size + Phase 71's edge budget pattern; D-12 explicitly defers top-N caps but plan can include a defensive `len(chains) > 10_000` early-exit if needed. |
| YAML frontmatter injection via `reasoning_relations` list | Tampering | Use `yaml.safe_dump`; never `yaml.dump`. Coerce all values to str/float before serialization. |

---

## Sources

### Primary (HIGH confidence)
- `graphify/validate.py` (lines 1–277, full file read) — frozenset registration pattern, per-edge validation loop, read/write split, write-mode temporal requirements
- `graphify/build.py` (lines 1–438, full file read) — `_normalize_concept_code_edges`, temporal stamp block, supersession diff call site, `SCHEMA_VERSION = "2.0"` stamping
- `graphify/wiki.py` (full file read) — `_community_article` shape, Phase 71-05 Historical relations precedent at lines 89–110
- `graphify/skill.md` (lines 260–440) — Step 3 Part B subagent prompt with embedded relation taxonomy that must be extended
- `graphify/prompts.py` (full file read) — `PROMPT_VERSION = "1.13.0"`, cache key composition, drift gate reference
- `graphify/temporal.py` and `tests/test_temporal.py` (greps) — `run_now_iso()` env override pattern (`GRAPHIFY_RUN_TS`)
- `graphify/analyze.py` (lines 140–164, 480–520, 655–690) — `_is_concept_node`, `_is_file_node`, `knowledge_gaps`, `suggest_questions` isolated filter
- `graphify/report.py` (lines 420–460) — Temporal Health section precedent
- `graphify/export.py` (lines 571, 780–905) — `to_obsidian` profile pipeline; `split_rendered_note` public helper at line 821
- `docs/RELATIONS.md` (full file read) — canonical relation vocabulary doc; Phase 53 confidence rules
- `.planning/REQUIREMENTS.md` (full file read) — REAS-01..04 specs and traceability
- `.planning/ROADMAP.md` (full file read) — Phase 72 success criteria
- `.planning/phases/71-temp/71-VERIFICATION.md` (full file read) — Phase 71 ship state, 4 analyze.py filter sites, threat-model mitigation table
- `.planning/phases/72-reas/72-CONTEXT.md` (full file read) — locked decisions D-01..D-16

### Secondary (MEDIUM confidence)
- Test fixture inventory (`ls tests/fixtures/`) — confirms availability of `extraction.json`, `graph_legacy_v113.json`, `graph_temporal_v20.json` as pattern bases for new fixtures.

### Tertiary (LOW confidence)
- A4 (skill drift gate covers prompt body, not just metadata) — assumed but not directly verified by reading `tests/test_skill_prompt_drift.py`. Plan should verify in Wave 0.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; all libraries already in pyproject.toml
- Architecture: HIGH — every code site cited has been read directly; integration sequence verified against existing line numbers
- Pitfalls: HIGH for Pitfalls 1–6 (all backed by existing code); MEDIUM for Pitfall 7 (cycle handling — depends on extractor behavior we cannot fully predict)
- Two-pass build pattern: HIGH on the design; MEDIUM on label-resolution heuristic (alternatives exist; plan to discuss in Wave 0)
- Supersedes auto-stamp: HIGH — interaction with Phase 71's `stamp_supersessions` is verified disjoint by code reading

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (30 days; Phase 71 just shipped, schema is stable, no fast-moving external deps)
