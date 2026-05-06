# Phase 66 — CFED: Cross-Repo Concept Federation (`federate.py`)

**Date**: 2026-05-06
**Mode**: discuss (--chain)

<domain>
Opt-in, deterministic, build-time merge of concept nodes across multiple graphify repos.
- ID-namespacing of all nodes (`{repo}::{id}`).
- Multi-signal AND merge gate: label match + 1-hop neighborhood Jaccard + source-path overlap.
- Per-merge provenance manifest under `graphify-out/`.
- Federation section in `GRAPH_REPORT.md`.
- Pipeline slot: after `_normalize_concept_code_edges` in `build.py`, before `cluster.py`.
- Hard constraints (CFED-02): no embeddings, no LLM arbitration; default off; deterministic.
</domain>

<carry_forward>
- **Phase 65 (CCONF)**: per-edge `confidence_score` is available on INFERRED edges → consumed only as a tiebreaker (see decision T-66.4).
- **Phase 64 (AUDIT-A)**: stderr two-line format `[graphify] error:\n  hint:` is locked. Any federation breadcrumb must conform.
- **Phase 63 (VOPT)**: vault-aware output routing via `default_graphify_artifacts_dir()` / Option B reroute. Manifest path MUST go through that resolver — never hardcode `graphify-out/`.
- **Phase 53 invariant**: `_normalize_concept_code_edges` runs before federation; federation must not violate the normalized concept↔code edge contract.
</carry_forward>

<canonical_refs>
- `.planning/ROADMAP.md` — Phase 66 goal + success criteria (lines 62–72)
- `.planning/REQUIREMENTS.md` — CFED-01..05 (lines 20–24, 73, 94–98)
- `.planning/phases/65-cconf-per-edge-confidence-cache-split-schema-version/65-VERIFICATION.md` — confidence_score availability + calibration semantics
- `.planning/phases/64-audit-a-stderr-format-snapshot-lock-sweep/` — locked stderr contract
- `.planning/phases/63-vopt-vault-option-b-silent-reroute-explain-paths/` — vault-aware output routing
- `graphify/build.py` — `_normalize_concept_code_edges` insertion point for federation step
- `graphify/cluster.py` — downstream consumer (must see post-federation graph)
- `graphify/export.py` — produces the peer `export.json` that federation will read
- `graphify/report.py` — host for new Federation section
- `graphify/__main__.py` — CLI surface for `--federate-with` flag
- `CLAUDE.md` — no new required deps; vault output rules
</canonical_refs>

<decisions>

### D-66.1 — CLI invocation
- **Flag**: repeatable `--federate-with PATH` on `graphify run`.
- `PATH` points at a peer repo's `graphify-out/` directory.
- Default behavior unchanged when flag absent (CFED-01).
- No new config file (`.graphify/federate.yaml` rejected — keeps surface minimal).

### D-66.2 — Peer artifact
- Federation reads each peer's existing `graphify-out/export.json`.
- No new producer-side artifact, no peer re-extraction.
- If a peer's `export.json` is missing or unreadable → fail loudly with two-line stderr (Phase 64 contract): `[graphify] error: peer export not found at {path}\n  hint: run \`graphify run\` in the peer repo first`.

### D-66.3 — Repo namespace label
- `{repo}` in `{repo}::{id}` = `basename(parent_of_PATH)` of the `--federate-with` argument.
  - e.g. `--federate-with ../graphify/graphify-out` → repo label `graphify`.
- Local repo label = basename of the current run's project root.
- **Collision policy**: if two `--federate-with` paths resolve to the same basename, hard-fail with two-line stderr asking the user to disambiguate (no implicit suffixing).
- Alias syntax (`PATH=ALIAS`) NOT included this phase — deferred.

### D-66.4 — Multi-signal merge gate (AND of all three)
For each candidate concept-node pair (one from local, one from a peer) to merge, ALL of:

1. **Label match**: case-folded exact match on `label`.
2. **Neighborhood overlap**: Jaccard ≥ **0.5** over the set of 1-hop neighbor **labels** (case-folded). Label-based (not id-based) to avoid chicken-and-egg with iterative merges.
3. **Source-path overlap**: ≥1 shared `source_file` **basename** across the two concepts' source attributes.

**Tiebreaker** (T-66.4): when two candidate merges compete for the same target concept, pick the pair with higher mean Phase 65 `confidence_score` across the contributing INFERRED edges in the neighborhood. Otherwise `confidence_score` is unused. Keeps gate deterministic-AND.

### D-66.5 — Manifest
- **Path**: `{vault_aware_artifacts_dir}/federation-manifest.json` — resolved via `default_graphify_artifacts_dir()` / Option B router (NOT hardcoded `graphify-out/`).
- **Format**: JSON, stdlib only, no new deps.
- **Lifecycle**: rewritten each run (single source of truth for current graph). History/append-only is deferred to Phase 67 drift work.
- **Schema** per merged-concept entry (full provenance):
  ```json
  {
    "merged_id": "<namespaced canonical id>",
    "contributing": [
      {"repo": "<label>", "original_id": "...", "label": "...", "source_files": ["..."]},
      ...
    ],
    "signals": {
      "label_match": "<the matched label>",
      "neighborhood_jaccard": 0.67,
      "shared_basenames": ["token.py", "auth.py"]
    },
    "tiebreaker_score": 0.82
  }
  ```
  `tiebreaker_score` field present only when tiebreaker fired; omitted otherwise.

### D-66.6 — GRAPH_REPORT.md Federation section
- **Placement**: after Communities, before Calibration (Phase 65 self-check section).
- **Rendering**: markdown table.
  - Columns: `Merged Concept | Repos | Jaccard | Shared Basenames | Tiebreaker`.
- **Zero-merges policy**: section omitted entirely (matches the Phase 67 drift-section "absent ⇒ omit" convention noted in ROADMAP SC for CDRIFT).
- Driven directly off `federation-manifest.json`; no separate report-side state.

### D-66.7 — Pipeline placement & invariants
- New module: `graphify/federate.py` exposing a single entrypoint (e.g. `federate(graph, peers) -> graph`).
- Called from `build.py` after `_normalize_concept_code_edges` and before `cluster.py` returns.
- Federation MUST preserve the normalized concept↔code edge contract from Phase 53.
- All node ids (local AND peer) get namespaced before federation logic runs; merge produces a single canonical id (lexicographic min across namespaced contributing ids, deterministic).

</decisions>

<deferred>
- `--federate-with PATH=ALIAS` syntax for explicit namespace overrides (only needed when basename collisions occur in practice).
- Append-only `federation-history.jsonl` for cross-run drift — deferred to Phase 67 (CDRIFT).
- `.graphify/federate.yaml` declarative manifest — re-evaluate if user adopts >2 stable peers.
- Hard floor on `confidence_score` (drop low-confidence INFERRED neighbors before AND-check) — defer to a tuning phase once Phase 65 calibration data lands.
- Auto-derivation of repo label from peer's PROJECT.md / pyproject metadata.
- Bullet/verbose rendering of Federation section for small-N cases.
</deferred>

<code_context>
- **Insertion point**: `graphify/build.py` — after `_normalize_concept_code_edges` call site, before returning the graph that `cluster.py` consumes.
- **CLI plumbing**: `graphify/__main__.py` — `_PLATFORM_CONFIG`-adjacent run command needs an `action="append"` arg for `--federate-with`.
- **Peer reader**: `graphify/export.py` already produces `export.json`; federate.py reads it via stdlib `json`.
- **Output routing**: `graphify/output_resolution.py` (Phase 63) → `default_graphify_artifacts_dir()` is the canonical artifact-dir resolver; manifest writer must use it.
- **Report integration**: `graphify/report.py` — current sections (confidence breakdown, communities, gaps, calibration) — Federation section slots between communities and calibration.
- **Validation**: `graphify/validate.py` — peer-imported nodes/edges should pass through existing schema check before merge.
- **No new deps**: stdlib `json` + existing networkx; aligns with CLAUDE.md "no new required dependencies" rule.
</code_context>

<success_signals>
- Default-off proven by full existing test suite passing unchanged with `--federate-with` absent.
- Two-repo fixture where labels match but neighborhoods diverge → ZERO merges.
- Two-repo fixture with full multi-signal agreement → exactly 1 merge with full provenance in manifest and a row in GRAPH_REPORT.
- Manifest path respects vault-aware routing (test asserts under `.graphify-out/` when run from a vault CWD).
- Stderr breadcrumbs (when peer load fails) conform to Phase 64 two-line snapshot test.
</success_signals>
