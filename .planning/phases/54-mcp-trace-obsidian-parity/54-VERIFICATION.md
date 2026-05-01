---
phase: 54-mcp-trace-obsidian-parity
requirements: [CGRAPH-03, CGRAPH-04]
status: passed
verified: 2026-05-01
pytest: "1995 passed, 1 xfailed, 0 failed"
baseline: "1979 passed, 1 xfailed (Phase 53 close)"
---

# Phase 54 Verification — MCP, trace & Obsidian parity

CGRAPH-03 and CGRAPH-04 traced from sub-requirement → MCP tool / vault location → source line → test. A1 carve-out resolved (ADOPTED). Full pytest suite green; +16 net new passes vs Phase 53 baseline.

## CGRAPH-03 Mapping Table

> CGRAPH-03 — *MCP exposes typed concept↔code hop/query behavior consistent with v1.10 `concept_code_hops` and slash `/trace` expectations (documented mapping table in verification).*

| Sub-requirement | MCP tool / parameter | Source (file:line) | Test |
|-----------------|----------------------|--------------------|------|
| MCP exposes typed concept↔code hop with 5-relation filter | `concept_code_hops` / `relations` param | `graphify/serve.py:_run_concept_code_hops` (≈L2345); `graphify/mcp_tool_registry.py:305-345` (`concept_code_hops` Tool registration) | `tests/test_concept_code_mcp.py::test_concept_code_hops_default_relations`, `test_concept_code_hops_multi_relation_traversal`, `test_concept_code_hops_payload_steps_by_relation` |
| Backward-compat with v1.10 `concept_code_hops` (Phase 47) | shim `implements_traversal_steps` (set-equality on `relations == ["implements"]`) | `graphify/serve.py:2507` (payload conditional `meta["implements_traversal_steps"] = traversals`) | `tests/test_concept_code_mcp.py::test_concept_code_hops_backward_compat_implements_steps_key` |
| Unknown / empty `relations` rejected with structured error | `_validate_relations_arg` | `graphify/serve.py:2246` (`_validate_relations_arg`) | `tests/test_concept_code_mcp.py::test_concept_code_hops_unknown_relation_errors`, `test_concept_code_hops_empty_relations_errors` |
| Helper rename + 5-relation generalization | `_concept_code_hop_kind` / `_concept_code_hop_allowed` (renamed from `_implements_hop_*` per D-54.03) | `graphify/serve.py:2205` (`_concept_code_hop_kind`), `graphify/serve.py:2228` (`_concept_code_hop_allowed`) | exercised transitively by all `test_concept_code_hops_*` cases |
| Payload exposes `traversal_steps` + `steps_by_relation` | meta envelope construction in `_run_concept_code_hops` | `graphify/serve.py:_run_concept_code_hops` (≈L2490 meta dict) | `tests/test_concept_code_mcp.py::test_concept_code_hops_payload_steps_by_relation` |
| `entity_trace` covers concept↔code per D-54.05 (in lieu of `/trace` slash workflow widening) | `entity_trace.include_concept_code` (default `false`) | `graphify/serve.py:1979` (`include_cc = bool(arguments.get("include_concept_code", False))`); `graphify/mcp_tool_registry.py:283-304` (`entity_trace` Tool registration) | `tests/test_serve.py::test_entity_trace_default_excludes_concept_code` (backward-compat seal), `test_entity_trace_includes_concept_code_when_requested` |
| Default `include_concept_code=false` is byte-identical to Phase 11 | early-return path skips `_bfs_concept_code_from` merge | `graphify/serve.py:_run_entity_trace` body (gating on `include_cc`) | `tests/test_serve.py::test_entity_trace_default_excludes_concept_code` |
| MCP capability schema declares new params | tool registry `inputSchema.properties.relations` + `inputSchema.properties.include_concept_code` | `graphify/mcp_tool_registry.py:286-345` | `tests/test_capability.py::test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code` |
| Edge-budget cap respected across multi-relation traversal | `_IMPL_EDGE_BUDGET = 500` global cap; `truncated=true` in payload when hit | `graphify/serve.py:2198` constant; `graphify/serve.py:2324` cap check | shared with `test_concept_code_hops_payload_steps_by_relation` and existing Phase 47 truncation tests |
| Manifest binding for new schemas | `server.json::_meta.manifest_content_hash` rotates on schema changes | `graphify/capability.py:build_manifest_dict` + `scripts/sync_mcp_server_json.py` | `tests/test_capability.py` (26 tests, all green) |

### Note on `/trace` slash workflow (D-54.05)

Per D-54.05 the `/trace` slash workflow itself remains scoped to temporal evolution and is **not** updated in Phase 54. CGRAPH-03's "consistent with `/trace` expectations" is satisfied through `entity_trace`'s new `include_concept_code` flag (the data path the slash command would invoke if widened in a later phase). Concept↔code surfacing inside the user-visible `/trace` command body is deferred.

## CGRAPH-04 Mapping Table

> CGRAPH-04 — *Obsidian CODE / concept MOC export does not contradict graph-level concept↔code edges (single source of truth from the graph).*

| Sub-requirement | Vault location | Source (file:line) | Test |
|-----------------|----------------|--------------------|------|
| CODE notes contain forward per-relation sections in canonical order | `${body}` slot in `code.md`, end of template | `graphify/templates.py:_build_concept_code_sections_for_code`; `graphify/builtin_templates/code.md` (`${body}` placeholder at end) | `tests/test_concept_code_obsidian.py::test_code_note_per_relation_sections_canonical_order` |
| Inverse per-relation sections render on rationale notes (not on community MOCs — Plan 04 deviation #4) | `${body}` slot, invoked from `render_note` rationale dispatch | `graphify/templates.py:_build_concept_code_sections_for_moc` (despite name, invoked from rationale render path); `graphify/builtin_templates/moc.md` (`${body}` placeholder, A1 carve-out — present but unused for typed-edge view) | `tests/test_concept_code_obsidian.py::test_concept_moc_inverse_sections_canonical_order` |
| Empty per-relation sections suppressed | empty-list short-circuit inside section builder loops | `graphify/templates.py` builder loops (`if not items: continue`) | `tests/test_concept_code_obsidian.py::test_empty_relation_section_suppressed` |
| Forward parity (graph → vault) | every concept↔code edge with `_src` = code/document appears as `[[Label]]` under matching forward H2 in src's note | `graphify/templates.py:_build_concept_code_sections_for_code` (walks `G.edges(node_id, data=True)`) | `tests/test_concept_code_obsidian.py::test_forward_parity_edges_to_wikilinks` |
| Backward parity (vault → graph) | every wikilink under any of the 10 Phase 54 H2 sections corresponds to a graph edge with the matching relation | both builders (deterministic edge iteration) | `tests/test_concept_code_obsidian.py::test_backward_parity_wikilinks_to_edges` |
| Per-relation count parity (5 separate counts) | `forward_count == inverse_count == graph_edge_count` per relation | both builders + Phase 53's canonical sort in `_normalize_concept_code_edges` | `tests/test_concept_code_obsidian.py::test_per_relation_count_parity` |
| Round-trip idempotence | `<!-- graphify:concept_code_relations:start -->` / `:end -->` sentinel block byte-identical across two consecutive `to_obsidian` runs | `graphify/templates.py:_wrap_sentinel("concept_code_relations", ...)` + builders | `tests/test_concept_code_obsidian.py::test_round_trip_per_relation_sections_idempotent` |
| Connections callout does NOT double-render typed concept↔code edges | filter in `_build_connections_callout` skips the 5 typed relations | `graphify/templates.py:_build_connections_callout` (Plan 04 deviation #3) | implicit (covered by forward+backward parity tests; double-rendering would inflate counts) |
| Bare `[[Label]]` form (case-preserving) | `_emit_concept_code_wikilink` (no title-case slugifier — labels survive round-trip) | `graphify/templates.py:_emit_concept_code_wikilink` | `tests/test_concept_code_obsidian.py::test_round_trip_per_relation_sections_idempotent` |

## A1 Carve-out Resolution (ADOPTED)

**Question.** Is adding a `${body}` slot to `graphify/builtin_templates/moc.md` allowed under D-54.10 ("no new templates, no profile changes")?

**Resolution.** **ADOPTED.** Rationale:

- D-54.10's intent is "no NEW template files, no profile-knob changes". Adding a `${body}` placeholder to an existing builtin template is a 1-line additive edit, parallel to the slot already present in `code.md`.
- Phase 30's profile composition is unaffected — vault overrides of `moc.md` continue to win, and overrides that omit `${body}` naturally suppress per-relation sections (this is a feature for users who want to opt out without code changes).
- Plan 04 implemented the slot and committed it (`371c2ee`).

**Honest deviation note (Plan 04 deviation #4).** Although the slot was added to `moc.md` to satisfy A1, inverse per-relation sections actually render on individual **rationale notes** through the `render_note` rationale dispatch path — **NOT** on community MOC bodies. This was a Rule 4 architectural deviation discovered during Task 2 of Plan 04: emitting inverse sections on the community MOC made `_find_md_for_label` non-deterministic (an MOC's H1 is `# <Slug> ... <hash>`, not `# AuthService`), and would have inflated the count parity contract because one MOC aggregates many concepts. Routing inverse sections to per-rationale notes preserves the 1:1-per-edge count parity (D-54.12) and keeps deterministic H1-title lookup. The `${body}` slot in `moc.md` is still present for a future phase (e.g., community-level summaries) — it is currently unused in the typed-edge view.

## Plan 04 Deviations Summary

| # | Rule | Issue | Resolution | Commit |
|---|------|-------|-----------|--------|
| 1 | Rule 1 (test bug) | `_find_md_for_label` non-deterministic across filesystems (`Path.rglob` order + over-broad regex matched community wayfinder `up:` field) | Two-pass deterministic lookup: prefer H1-title match, then fall back to whole-word body match against `sorted(rglob(...))` | `90c9178` |
| 2 | Rule 1 (test bug) | `test_backward_parity_wikilinks_to_edges` expected total = single-side count, but test scans both forward AND inverse sections | `expected_total = 2 * edge_count` (forward + inverse) | `371c2ee` |
| 3 | Rule 2 (correctness) | Generic Connections callout double-rendered the 5 typed concept↔code relations alongside the new H2 sections — broke "single source of truth" contract | Filter the 5 typed relations out of `_build_connections_callout`; other relations (`contains`, `references`, etc.) unchanged | `90c9178` |
| 4 | Rule 4 (architectural) | Original plan emitted inverse sections on community MOC; this broke deterministic H1-title lookup AND inflated count parity | Route inverse sections to per-rationale notes via `render_note` rationale dispatch; keep `${body}` in `moc.md` for future use | `371c2ee` |

## Must-haves Verification Status

### Plan 01 (RED)

- [x] 16 RED tests committed (9 MCP + 7 Obsidian) — `ab9ec93`, `14fad1d`
- [x] 5 vault_parity fixtures created — committed in `14fad1d`
- [x] `test_entity_trace_default_excludes_concept_code` (backward-compat seal) GREEN through Wave 2

### Plan 02 (concept_code_hops 5-relation widening)

- [x] `_concept_code_hop_kind` / `_concept_code_hop_allowed` renamed (D-54.03) — `373e250`
- [x] `_validate_relations_arg` rejects empty/unknown — `tests/test_concept_code_mcp.py::test_concept_code_hops_unknown_relation_errors,_empty_relations_errors`
- [x] Payload `traversal_steps` + `steps_by_relation` populated — `test_concept_code_hops_payload_steps_by_relation`
- [x] `implements_traversal_steps` shim conditional on `relations == ["implements"]` (set-equality) — `test_concept_code_hops_backward_compat_implements_steps_key`
- [x] All 6 MCP RED tests GREEN — `75dbd59`

### Plan 03 (entity_trace include_concept_code)

- [x] `_bfs_concept_code_from` factored from `_run_concept_code_hops` — `1f16c5c`
- [x] `entity_trace` accepts `include_concept_code: bool = False` — `1f16c5c`
- [x] Default omitted → byte-identical Phase 11 envelope — `test_entity_trace_default_excludes_concept_code`
- [x] `include_concept_code=true` adds `concept_code_reachable` + `concept_code_steps_by_relation` — `test_entity_trace_includes_concept_code_when_requested`
- [x] Tool registry `entity_trace` schema declares `include_concept_code` — `b2aaae9`
- [x] Capability test: schema includes both `relations` and `include_concept_code` — `test_concept_code_hops_schema_includes_relations_and_entity_trace_includes_concept_code`

### Plan 04 (Obsidian per-relation sections + parity)

- [x] CODE notes get forward H2 sections in canonical order — `test_code_note_per_relation_sections_canonical_order`
- [x] Inverse sections rendered on rationale notes (Plan 04 dev. #4) — `test_concept_moc_inverse_sections_canonical_order`
- [x] Empty sections suppressed — `test_empty_relation_section_suppressed`
- [x] Forward parity — `test_forward_parity_edges_to_wikilinks`
- [x] Backward parity (forward + inverse = 2× edge count) — `test_backward_parity_wikilinks_to_edges`
- [x] Per-relation count parity — `test_per_relation_count_parity`
- [x] Round-trip sentinel idempotence — `test_round_trip_per_relation_sections_idempotent`
- [x] `${body}` slot added to `moc.md` (A1 carve-out adopted) — `371c2ee`

### Plan 05 (close-out — this document)

- [x] `docs/RELATIONS.md` `## MCP traversal` section published — commit `1f6d22b`
- [x] `server.json` regenerated via `python scripts/sync_mcp_server_json.py` — already in sync (Plans 02/03 triggered regen; current hash `ac31ce60c04bee38…` matches `build_manifest_dict()`)
- [x] CGRAPH-03 mapping table — this file (above)
- [x] CGRAPH-04 mapping table — this file (above)
- [x] A1 carve-out documented as ADOPTED — this file
- [x] Plan 04 deviations honestly captured — this file
- [x] Full pytest suite green — see "Full-suite gate" below

## Full-suite gate

```
$ pytest tests/ -q
1995 passed, 1 xfailed, 8 warnings in 69.63s
```

| Metric | Phase 53 baseline | Phase 54 close | Delta |
|--------|-------------------|----------------|-------|
| passed | 1979 | 1995 | +16 (matches Plan 01's 16 RED tests now GREEN) |
| xfailed | 1 | 1 | 0 |
| failed | 0 | 0 | 0 |

**Status: passed.** Zero failures attributable to Phase 54.

## server.json regeneration note (deviation from Plan 05 acceptance criteria)

Plan 05 Task 2 acceptance criteria expected `grep -c "concept_code_hops" server.json ≥ 1` and similar greps for `relations` / `include_concept_code` directly inside `server.json`. **The current `server.json` is the slim hash-only form** (29 lines: `name`, `version`, `packages`, `_meta`); tool schemas live in `graphify/capability.py::build_manifest_dict()` at runtime, and `server.json::_meta.manifest_content_hash` binds the committed manifest to the live schemas. The script `scripts/sync_mcp_server_json.py` writes only version + hash + tool_count, NOT raw tool schemas.

The hash binding (verified by 26 tests in `tests/test_capability.py`, all green) provides the equivalent guarantee — any schema drift (renamed tool, added/removed property) flips the hash. Since Plans 02/03 already triggered regeneration during their schema edits, re-running the sync script in Plan 05 produced no diff: the on-disk hash already reflects the Phase 54 schemas. This is operationally correct; the plan's grep criteria assumed a different `server.json` shape than the one actually committed in this repo.

## Outstanding / Deferred

- **`graphifyy` PyPI version bump** — deferred to v1.11 milestone close (per CLAUDE.md release flow). `pyproject.toml` and `server.json` still report `1.0.0`.
- **Profile-driven `concept_code_layout`** — deferred to CFG-01 / Phase 56.
- **`/trace` slash command concept↔code surfacing (D-54.05)** — deferred. CGRAPH-03 satisfied via `entity_trace.include_concept_code`; user-facing `/trace` body widening is a future milestone.

---

## Phase 54 status: passed
