# Requirements: graphify — Milestone v1.5 Diagram Intelligence & Excalidraw Bridge

**Milestone:** v1.5 · **Status:** Planning · **Phases:** 19–22 · **Plans:** 7 + Phase 19 TBD

## Overview

v1.5 has two workstreams. **Layer B (Phase 19, VAULT-01..07)** — a pure-file-I/O vault promotion script that writes `graph.json`-derived Obsidian notes into Ideaverse Pro 2.5 folders with full frontmatter and tag taxonomy. Pulled in from v1.4 scope-reconciliation 2026-04-23. **Diagram pipeline (Phases 20–22)** — turns the knowledge graph into Excalidraw diagrams, strictly ordered by dependency: seed engine first (Phase 20), profile extension + template bootstrap second (Phase 21), skill + install bridge last (Phase 22). Phase 19 is independent of 20–22 and can execute in any order relative to them.

---

## VAULT — Vault Promotion Script Layer B (Phase 19)

Derived from ROADMAP.md Phase 19 success criteria. Full requirement text and plan decomposition to be elaborated during `/gsd-plan-phase 19`.

- [x] **VAULT-01** `graphify vault-promote --vault /path/to/vault --threshold N` CLI reads `graphify-out/graph.json` + `GRAPH_REPORT.md` and writes promoted notes into Ideaverse Pro 2.5 destination folders without touching any existing vault file it did not create (write-only, no overwrite of foreign files).
- [x] **VAULT-02** Every promoted note has valid Ideaverse frontmatter: `up`, `related`, `created`, `collections`, `graphifyProject`, `graphifyRun`, `graphifyScore`, `graphifyThreshold`, and at minimum one tag from each of `garden/*`, `source/*`, `graph/*`.
- [x] **VAULT-03** Node-type → folder dispatch is correct: god-node domain concepts → `Atlas/Dots/Things/`; knowledge gaps → `Atlas/Dots/Questions/`; clusters → `Atlas/Maps/<slug>.md` with `stateMaps: 🟥`.
- [x] **VAULT-04** `related:` wikilinks are populated only from EXTRACTED-confidence edges; INFERRED and AMBIGUOUS edges are omitted.
- [x] **VAULT-05** `graphify-out/import-log.md` is written after each run with vault path, run timestamp, promoted-count by type, threshold, and skipped-count.
- [x] **VAULT-06** Profile write-back: union-merge Layer 3 auto-detected tags into `.graphify/profile.yaml`, gated by `profile_sync.auto_update` (default `true`). Writes atomic (tempfile + os.replace).
- [x] **VAULT-07** Hybrid 3-layer tag taxonomy: Layer 1 `_DEFAULT_PROFILE` baseline → Layer 2 user `.graphify/profile.yaml` (deep-merged) → Layer 3 auto-detected from `graph.json` source_file extensions + file_type (deep-merged in memory; persisted via VAULT-06).

---

## SEED — Diagram Seed Engine (Phase 20)

- [x] **SEED-01** `graphify --diagram-seeds` CLI flag triggers seed generation after the analyze stage and writes seeds to `graphify-out/seeds/`.
- [x] **SEED-02** `analyze.py` auto-tags god nodes and cross-community bridges with `possible_diagram_seed: true` as a node attribute. A new `detect_user_seeds(G)` function reads node `tags` attribute for `gen-diagram-seed` and `gen-diagram-seed/<type>` patterns and returns `auto_seeds` and `user_seeds` lists with extracted type hints.
- [x] **SEED-03** `gen-diagram-seed` / `gen-diagram-seed/<type>` vault tags are round-tripped via the Phase 8 vault_adapter mechanism — tag write-back routes through `vault_adapter.py::compute_merge_plan` with the `tags: "union"` policy (merge.py line 70). Direct frontmatter writes are forbidden.
- [x] **SEED-04** `seed.py` exposes `build_seed(G, node_id, trigger, layout_hint=None) → SeedDict` containing: `main_nodes` (ego-graph radius-1), `supporting_nodes` (radius-2 minus radius-1), `relations` (all edges in subgraph), `suggested_layout_type`, `suggested_template`, `trigger` (`"auto"` or `"user"`). One `{node_id}-seed.json` file written per seed under `graphify-out/seeds/`.
- [x] **SEED-05** `build_all_seeds(G, analysis, profile)` merges seeds with >60% node overlap: union of node sets; user layout hint beats auto; deduplicated via single-pass sort by degree descending (no recursive re-merge).
- [x] **SEED-06** Auto-detected seeds capped at `max_seeds=20` before any file I/O. User-tagged seeds (`gen-diagram-seed`) have no cap.
- [x] **SEED-07** Layout type auto-selected by NetworkX heuristics: `is_tree → cuadro-sinoptico`; DAG + ≥3 topo generations → `workflow`; ≥4 communities → `architecture`; degree-concentrated single community → `mind-map`; concept/doc nodes with labeled relations → `glossary-graph`; code nodes → `repository-components`. `gen-diagram-seed/<type>` slash-type-hint overrides heuristic.
- [x] **SEED-08** Element IDs derived as `sha256(node_id)[:16]`. `versionNonce` is deterministic: `int(sha256(node_id + str(x) + str(y))[:8], 16)`. Label-derived IDs are forbidden.
- [x] **SEED-09** `list_diagram_seeds` MCP tool reads `graphify-out/seeds/`, returns per-seed: `seed_id`, `main_node_label`, `suggested_layout_type`, `trigger`, `node_count`. Response follows D-02 envelope. Node IDs threaded through `_resolve_alias` per D-16.
- [x] **SEED-10** `get_diagram_seed(seed_id)` MCP tool returns full SeedDict for the requested seed. Response follows D-02 envelope (`text_body + "\n---GRAPHIFY-META---\n" + json(meta)`). Node IDs threaded through `_resolve_alias` per D-16.
- [x] **SEED-11** `mcp_tool_registry.py` and `serve.py` extensions for `list_diagram_seeds` / `get_diagram_seed` land in the same plan (MANIFEST-05 atomic pair invariant).

---

## PROF — Profile Extension (Phase 21)

- [ ] **PROF-01** `profile.yaml` accepts a top-level `diagram_types:` section. When absent, graphify falls back to 6 built-in defaults (architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph).
- [ ] **PROF-02** `profile.py` update is ATOMIC: `_VALID_TOP_LEVEL_KEYS` (line 67), `_DEFAULT_PROFILE`, and `validate_profile()` all land in the same plan as the first code that reads `diagram_types`. No partial updates.
- [ ] **PROF-03** Each `diagram_types` entry has: `name`, `template_path`, `trigger_node_types` (list), `trigger_tags` (list), `min_main_nodes` (int), `naming_pattern` (string with `{topic}` placeholder). All fields have graceful defaults when absent.
- [ ] **PROF-04** Template recommender in `seed.py` follows precedence: profile `diagram_types` match → layout heuristic default → built-in fallback. Never errors on missing profile section.

---

## TMPL — Template Bootstrap (Phase 21)

- [ ] **TMPL-01** `graphify --init-diagram-templates` writes 6 `.excalidraw.md` stubs to vault paths from profile (or `Excalidraw/Templates/` by default). Idempotent: skips existing files unless `--force`.
- [ ] **TMPL-02** Every stub has valid `.excalidraw.md` structure: frontmatter with `excalidraw-plugin: parsed` and `compress: false`; a `## Text Elements` block (always present, even if empty); a `## Drawing` block with raw JSON scene (not LZ-String compressed).
- [ ] **TMPL-03** Scene JSON top-level: `{"type":"excalidraw","version":2,"source":"graphify","elements":[...],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}`. Font family 5 (Excalifont) for all text elements. `versionNonce` present on every element.
- [ ] **TMPL-04** `--init-diagram-templates` is idempotent: running twice without `--force` produces no changes. `--force` overwrites all stubs.
- [ ] **TMPL-05** If `profile.yaml` has a `diagram_types:` section, only the listed types are generated. If absent, all 6 built-in types are generated.
- [ ] **TMPL-06** `gen-diagram-seed` tag write-back (auto-detected nodes) routes through `vault_adapter.py::compute_merge_plan` with `tags: "union"` policy. Direct frontmatter writes (`Path.write_text`, `write_note_directly`, `open('w')`) are forbidden — enforced by test-time grep denylist.

---

## SKILL — Excalidraw Skill & Vault Bridge (Phase 22)

- [ ] **SKILL-01** `graphify install excalidraw` installs `skill-excalidraw.md` to `.claude/skills/excalidraw-diagram/SKILL.md`. New `excalidraw` platform entry in `_PLATFORM_CONFIG` in `__main__.py`. *(Positional form per Phase 22 CONTEXT D-04, matching every other platform; the original `--excalidraw` flag wording was prose-shorthand, not a CLI contract.)*
- [ ] **SKILL-02** `graphify uninstall excalidraw` removes the installed skill file. *(Positional form per Phase 22 CONTEXT D-04.)*
- [ ] **SKILL-03** Install and uninstall are idempotent (running twice is safe).
- [x] **SKILL-04** `skill-excalidraw.md` orchestrates the full pipeline: (1) `list_diagram_seeds` → show user available seeds; (2) user selects seed; (3) `get_diagram_seed(seed_id)` → SeedDict; (4) read matching template from vault via mcp-obsidian; (5) build diagram in mcp_excalidraw using SeedDict nodes/edges + template style; (6) export scene → write to vault at `Excalidraw/Diagrams/{naming_pattern}.excalidraw.md`; (7) report: seed_id, node count, template used, vault path written.
- [x] **SKILL-05** `skill-excalidraw.md` includes a `.mcp.json` snippet for obsidian + excalidraw servers, vault convention rules (folder layout, naming), style-matching rules, and a "do not" guard list.
- [x] **SKILL-06** mcp_excalidraw is optional. When unavailable, the skill falls back to generating a `.excalidraw.md` file directly using the seed JSON and built-in template. The pure-Python output path must be complete before mcp_excalidraw integration.

---

## Deferred (not in v1.5)

- **SEED-001** Tacit Elicitation Engine — re-evaluate at v1.6 if onboarding/discovery becomes the milestone theme
- LLM-assisted seed narrative descriptions — v1.6+
- Multi-seed diagram (combining two seeds into one diagram) — v1.6+
- Real-time seed refresh via watch mode — v1.6+
- mcp_excalidraw `import_scene` merge semantics validation — Phase 22 planning research flag

---

## Out of Scope

- mcp_excalidraw as a required Python dependency (graphify never imports it)
- Direct vault frontmatter writes outside `vault_adapter.py::compute_merge_plan`
- LZ-String compression in `.excalidraw.md` stubs (use `compress: false` frontmatter)
- Per-function routing or non-file-level seed granularity (D-73 carry-forward)

---

## Quality Checklist

- [ ] All 3 phases have PLAN.md, VERIFICATION.md, SECURITY.md, VALIDATION.md
- [ ] Zero new required Python dependencies (stdlib + networkx + PyYAML only)
- [ ] `seed.py` composes `analyze.py` primitives only — no new plumbing (D-18)
- [ ] `_VALID_TOP_LEVEL_KEYS` update is atomic with first `diagram_types` reader (PROF-02)
- [ ] MANIFEST-05 atomic pair: `mcp_tool_registry.py` + `serve.py` same plan (SEED-11)
- [ ] D-02 envelope on all new MCP tools (SEED-09, SEED-10)
- [ ] D-16 alias threading on all new MCP tools (SEED-09, SEED-10)
- [ ] `compress: false` in all `.excalidraw.md` stubs — no LZ-String (TMPL-02)
- [ ] Element IDs via `sha256(node_id)[:16]` — no label-derived IDs (SEED-08)
- [ ] Tag write-back via `compute_merge_plan` — no direct writes (SEED-03, TMPL-06)
- [ ] `max_seeds=20` cap enforced before any file I/O (SEED-06)
- [ ] Pure-Python `.excalidraw.md` output path complete before mcp_excalidraw integration (SKILL-06)

---

## Traceability

| REQ-ID | Phase | Plan | Status |
|--------|-------|------|--------|
| VAULT-01 | 19 | 19-03 | — |
| VAULT-02 | 19 | 19-02 | — |
| VAULT-03 | 19 | 19-02 | — |
| VAULT-04 | 19 | 19-02 | — |
| VAULT-05 | 19 | 19-03 | — |
| VAULT-06 | 19 | 19-03 | — |
| VAULT-07 | 19 | 19-01, 19-02 | — |
| SEED-01 | 20 | 20-02 | — |
| SEED-02 | 20 | 20-01 | — |
| SEED-03 | 20 | 20-01 | — |
| SEED-04 | 20 | 20-02 | — |
| SEED-05 | 20 | 20-02 | — |
| SEED-06 | 20 | 20-02 | — |
| SEED-07 | 20 | 20-02 | — |
| SEED-08 | 20 | 20-02 | — |
| SEED-09 | 20 | 20-03 | — |
| SEED-10 | 20 | 20-03 | — |
| SEED-11 | 20 | 20-03 | — |
| PROF-01 | 21 | 21-01 | — |
| PROF-02 | 21 | 21-01 | — |
| PROF-03 | 21 | 21-01 | — |
| PROF-04 | 21 | 21-01 | — |
| TMPL-01 | 21 | 21-02 | — |
| TMPL-02 | 21 | 21-02 | — |
| TMPL-03 | 21 | 21-02 | — |
| TMPL-04 | 21 | 21-02 | — |
| TMPL-05 | 21 | 21-02 | — |
| TMPL-06 | 21 | 21-02 | — |
| SKILL-01 | 22 | 22-02 | — |
| SKILL-02 | 22 | 22-02 | — |
| SKILL-03 | 22 | 22-02 | — |
| SKILL-04 | 22 | 22-01 | — |
| SKILL-05 | 22 | 22-01 | — |
| SKILL-06 | 22 | 22-01 | — |
