# Project Research Summary

**Project:** graphify v1.5 — Diagram Intelligence & Excalidraw Bridge
**Domain:** Knowledge graph → diagram generation pipeline with Obsidian vault integration
**Researched:** 2026-04-22
**Confidence:** HIGH

## Executive Summary

graphify v1.5 extends the existing graph analysis pipeline with a diagram seed generation layer that converts high-value graph nodes into structured artifacts consumable by Excalidraw. The pipeline is additive: a new `seed.py` module slots after `analyze.py`, emitting `graphify-out/seeds/*.json` files; two new MCP tools expose seeds to agents; `--init-diagram-templates` bootstraps vault templates; and a deployable `excalidraw-diagram` SKILL.md orchestrates the full seeds → mcp_excalidraw → vault flow.

No new required Python dependencies are needed. The entire seed generation and template writing stack runs on stdlib (`uuid`, `json`, `time`, `random`, `hashlib`) plus the already-present `networkx` and `PyYAML`. mcp_excalidraw is a Node.js external service accessed only via the skill; graphify's Python code never imports it. The pure-Python output path (`.excalidraw.md` file generation) must be complete and tested independently of mcp_excalidraw.

The highest-risk decision is the Excalidraw JSON compression format — a one-way door that must be resolved in Phase 21's first plan. The Obsidian Excalidraw plugin silently compresses raw JSON blocks on first save; using `compress: false` in the `.excalidraw.md` frontmatter keeps templates human-readable and avoids this. Two other high-risk areas are seed explosion (mitigated by a hard `max_seeds=20` cap) and element ID collisions (mitigated by `sha256(node_id)[:16]`).

## Key Findings

### Recommended Stack

No stack additions required for the core seed engine or template generator. `seed.py` is pure stdlib + networkx. The `.excalidraw.md` writer is `json.dumps()` + string formatting. The only optional new dependency is `lzstring` (PyPI) if LZ-String compression is chosen over `compress: false` — but `compress: false` frontmatter is the recommended choice since it avoids a new dep.

**Core technologies (all already present):**
- `networkx`: ego-graph extraction (`nx.ego_graph`, `nx.compose_all`) for seed subgraph building
- `PyYAML`: profile.yaml `diagram_types` section parsing (already optional dep)
- `stdlib (uuid, json, random, hashlib)`: seed IDs, scene JSON generation, element ID derivation

**Critical format spec (verified from Obsidian Excalidraw plugin source):**
- Frontmatter: `excalidraw-plugin: parsed` required; add `compress: false` to prevent silent compression on save
- Drawing block: `%%\n## Drawing\n` ` ```json` `\n{...}\n` ` ``` ` `\n%%` — raw JSON; `## Text Elements` section always present even when empty
- Scene JSON top-level: `{"type":"excalidraw","version":2,"source":"graphify","elements":[],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}`
- Font families: 5=Excalifont (current default), 6=Nunito, 8=Comic Shanns (code identifiers)
- All elements require: `id`, `type`, `x`, `y`, `width`, `height`, `angle:0`, `strokeColor`, `backgroundColor`, `fillStyle`, `strokeWidth`, `strokeStyle`, `roughness`, `opacity`, `updated` (epoch ms), `seed` (random int), `version:1`, `versionNonce` (random int), `isDeleted:false`, `groupIds:[]`, `frameId:null`, `roundness`, `boundElements:[]`, `link:null`, `locked:false`, `index:null`

### Expected Features

**Must have (table stakes for v1.5):**
- `--diagram-seeds` flag: auto-tag god nodes + cross-community bridges, write seeds to `graphify-out/seeds/`
- `gen-diagram-seed` vault tag round-trip: user tags → graph attribute → seed inclusion
- `list_diagram_seeds` + `get_diagram_seed` MCP tools with D-02 envelope
- `--init-diagram-templates`: 6 layout-type stubs (architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph)
- `profile.yaml` `diagram_types` section with graceful fallback when absent
- `excalidraw-diagram` SKILL.md with full orchestration sequence
- `graphify install --excalidraw`
- Tag write-back: auto-detected nodes get `gen-diagram-seed` written to vault frontmatter

**Should have (differentiators for v1.5):**
- Seed merge for >60% node overlap (cleaner diagrams, fewer duplicates)
- Layout type auto-selection heuristic (6 NetworkX predicates: is_tree, is_dag, degree distribution, community count, edge directionality ratio)
- `gen-diagram-seed/architecture` slash-type-hint in tags for explicit layout override

**Defer (v1.6+):**
- LLM-assisted seed narrative descriptions
- Multi-seed diagram (combining two seeds into one diagram)
- Real-time seed refresh via watch mode

**mcp_excalidraw verified API (21 tools, critical 3):**
- `batch_create_elements` — atomic diagram creation from element array
- `import_scene` — merge mode: inject elements into existing template
- `export_scene` — get current scene as JSON

### Architecture Approach

`seed.py` is a pure consumer of `analyze.py` primitives (D-18 hard invariant). It calls `god_nodes()` and `detect_user_seeds()` from `analyze.py` and never re-implements detection logic. `serve.py` extensions follow the existing `_tool_*` pattern with D-02 envelope and D-16 alias threading. Tag write-back routes through the Phase 7 merge layer (`merge.py::_DEFAULT_FIELD_POLICIES["tags"] = "union"` at line 70) — direct frontmatter writes are forbidden.

**Build order (dependency-driven):**
1. `analyze.py` extension — emits `possible_diagram_seed` on god nodes + bridges; `detect_user_seeds(G)`
2. `profile.py` extension — `_VALID_TOP_LEVEL_KEYS`, `_DEFAULT_PROFILE`, `diagram_types` schema **(ATOMIC: must land in same plan as first `diagram_types` read)**
3. `seed.py` new module — `build_seed`, `build_all_seeds`, layout heuristic, dedup, file output
4+5. `mcp_tool_registry.py` + `serve.py` **(ATOMIC PAIR — MANIFEST-05 assertion)**
6. `vault_adapter.py` tag inject — independent of MCP
7. `__main__.py` + `skill-excalidraw.md` — CLI plumbing, no upstream blockers after step 3

**D-02 envelope for `get_diagram_seed`:** `text_body + "\n---GRAPHIFY-META---\n" + json(meta)` with keys: `status`, `layer`, `search_strategy`, `cardinality_estimate`, `continuation_token`

### Critical Pitfalls

1. **Excalidraw JSON compression** — Plugin silently compresses raw JSON on first vault save. Use `compress: false` in `.excalidraw.md` frontmatter. **One-way door: decide in Phase 21 Plan 01 before writing any stub files.**

2. **`_VALID_TOP_LEVEL_KEYS` in `profile.py`** — Closed set by design (line 67). Adding `diagram_types` to the set, `_DEFAULT_PROFILE`, and `validate_profile()` must all land atomically in the same plan as the first code that reads `diagram_types`.

3. **Seed explosion** — god nodes + bridge nodes can produce 50+ seeds on a 300-node graph. Enforce `max_seeds=20` cap before any file I/O. Deduplicate candidates before `ego_graph` calls.

4. **Element ID collisions** — Label-derived IDs collide on common names (`__init__`, `utils`). Use `sha256(node_id)[:16]`. Include `versionNonce` (random int) on all elements.

5. **Tag write-back trust boundary** — Writing `gen-diagram-seed` directly to vault frontmatter bypasses `preserve_fields` and the Phase 7 trust boundary. Route through `vault_adapter.py::compute_merge_plan` with `tags: "union"` policy.

6. **mcp_excalidraw is optional** — Canvas is in-memory (lost on restart), export requires a live browser. Pure-Python `.excalidraw.md` output path must be complete before any mcp_excalidraw integration.

7. **Circular merge explosion** — Mutually-containing ego-graphs trigger recursive re-merge. Use union-of-node-sets (never recompute from winning center), single-pass dedup sorted by degree descending.

## Implications for Roadmap

### Phase 20: Diagram Seed Engine
**Rationale:** Foundation for everything else — MCP tools and profile extension both depend on `seed.py` existing
**Delivers:** `analyze.py` detection, `profile.py` `diagram_types` schema, `seed.py` module, `graphify-out/seeds/`, `--diagram-seeds` CLI, `list_diagram_seeds` + `get_diagram_seed` MCP tools
**Addresses:** seed generation, layout heuristics, seed dedup, MCP exposure
**Avoids:** seed explosion (max_seeds cap), circular merge, `_VALID_TOP_LEVEL_KEYS` atomicity, element ID collisions

### Phase 21: Profile Extension & Template Bootstrap
**Rationale:** Template stubs require the compression format decision locked first; tag write-back is independent
**Delivers:** `--init-diagram-templates` command, 6 real `.excalidraw.md` JSON stubs with `compress: false`, `gen-diagram-seed` tag write-back via vault adapter merge layer
**Uses:** Compression format decision, profile `diagram_types`, `merge.py` `tags: "union"` policy
**Avoids:** compression surprise, direct frontmatter write trust violation

### Phase 22: Excalidraw Skill & Vault Bridge
**Rationale:** Skill depends on seeds (Phase 20) and templates (Phase 21) both existing
**Delivers:** `excalidraw-diagram` SKILL.md, `graphify install --excalidraw`, `.mcp.json` snippet
**Implements:** Full orchestration: list seeds → get seed → read template → mcp_excalidraw → vault
**Avoids:** mcp_excalidraw as required dep (pure-Python path already complete in Phase 21)

### Phase Ordering Rationale
- Phase 20 first: `seed.py` is the dependency for all downstream work; `_VALID_TOP_LEVEL_KEYS` atomicity is safest in the first phase alongside the detection logic
- Phase 21 second: compression format one-way door must be locked before any stub file is written; tag write-back can be independently validated via existing merge layer
- Phase 22 last: skill is pure orchestration over already-complete Python infrastructure; mcp_excalidraw integration is an optional enhancement layer

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 21:** Obsidian Excalidraw plugin `compress: false` frontmatter support — verify against current plugin version; frame element `containerId` reference pattern
- **Phase 22:** mcp_excalidraw `import_scene` merge vs replace semantics; `batch_create_elements` `label` support in MCP wrapper

**Phases with standard patterns (skip research phase):**
- **Phase 20:** All patterns established in existing codebase (`god_nodes`, `_multi_seed_ego`, `_tool_*` MCP pattern, `_deep_merge` profile extension)

### Open Questions (resolve before planning phases)

| Question | Impact | Recommended Answer |
|---|---|---|
| Compression format | One-way door Phase 21 | `compress: false` frontmatter (no new dep) |
| Ego-graph radius default | seed.py spec | 2 (consistent with `get_focus_context` traversal depth) |
| `versionNonce` stability | vault noise on re-runs | Deterministic `int(sha256(node_id+str(x)+str(y))[:8], 16)` |
| Tag write-back path | trust boundary | Route through `vault_adapter.py::compute_merge_plan`, never direct write |
| `max_seeds` cap | seed explosion | 20 auto-seeds max; unlimited user-tagged seeds |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (no new deps) | HIGH | stdlib coverage verified; font map from plugin constants.ts |
| Excalidraw file format | HIGH | Verified from plugin source: constants.ts + ExcalidrawData.ts |
| mcp_excalidraw API | MEDIUM | 21 tools verified from src/index.ts; `import_scene` merge semantics not confirmed |
| Architecture integration | HIGH | All function signatures verified from live source; MANIFEST-05 confirmed |
| Layout heuristics | MEDIUM | NetworkX predicates grounded; not empirically validated on real graphify graphs |
| Pitfalls | HIGH | `_VALID_TOP_LEVEL_KEYS` confirmed line 67 profile.py; merge policy confirmed merge.py line 70 |

**Overall confidence:** HIGH

### Gaps to Address

- **mcp_excalidraw `import_scene` merge semantics**: verify whether it merges elements or replaces scene — critical for SKILL.md logic in Phase 22 planning
- **Frame `containerId` pattern**: verify which element fields reference frame containment in current Excalidraw element schema — needed for Phase 21 frame-based layout stubs
- **`cuadro-sinoptico` coordinate formula**: elbowed arrow branching math needs a concrete formula before Phase 22 Plan 01

## Sources

### Primary (HIGH confidence)
- Obsidian Excalidraw plugin source (constants.ts, ExcalidrawData.ts) — file format, font map, frontmatter keys
- `graphify/profile.py` line 67 — `_VALID_TOP_LEVEL_KEYS` confirmed closed set
- `graphify/merge.py` line 70 — `tags: "union"` policy confirmed
- `graphify/serve.py` lines ~3115–3117 — MANIFEST-05 assertion confirmed

### Secondary (MEDIUM confidence)
- mcp_excalidraw src/index.ts + types.ts + server.ts — 21 tools inventory
- NetworkX docs — `is_tree`, `is_dag`, `topological_generations`, degree predicates

### Tertiary (needs validation)
- mcp_excalidraw `import_scene` merge behavior — structure inferred; needs validation in Phase 22 planning

---
*Research completed: 2026-04-22*
*Ready for roadmap: yes*
