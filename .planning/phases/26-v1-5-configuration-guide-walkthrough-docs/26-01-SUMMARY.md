---
phase: 26
plan: 01
subsystem: docs
tags: [docs, v1.5, configuration-guide, mcp-tools, profile-yaml, tracker-hygiene]
dependency_graph:
  requires:
    - graphify/__main__.py (vault-promote, --diagram-seeds, --init-diagram-templates dispatch)
    - graphify/seed.py (D-06/D-07 gate logic at lines 265-289)
    - graphify/serve.py (mcp tool cores + _resolve_alias at 1234-1250)
    - graphify/skill-excalidraw.md (.mcp.json reference block)
    - README.md (insertion point at vault-promote subsection / Worked examples H2)
  provides:
    - CONFIGURING_V1_5.md (v1.5 end-to-end guide)
    - README v1.5 Configuration Guide cross-link
    - REQUIREMENTS DOCS-01..04 -> 26-01-PLAN.md mapping
    - ROADMAP Phase 26 plan list correction
  affects:
    - none (docs-only; no code, no tests, no dependencies)
tech_stack:
  added: []
  patterns:
    - Single-file user-facing guide at repo root (matches INSTALLATION.md / ARCHITECTURE.md / SECURITY.md convention)
    - Verbatim quoting of source (Tool declarations, _resolve_alias closure) to make the guide reference-quality
    - Annotated YAML with inline policy comments (vs. introducing new schema keys)
key_files:
  created:
    - CONFIGURING_V1_5.md
    - .planning/phases/26-v1-5-configuration-guide-walkthrough-docs/26-01-SUMMARY.md
  modified:
    - README.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - Quoted source verbatim (mcp_tool_registry.py declarations, serve.py:1234-1250 _resolve_alias) rather than paraphrasing — guarantees DOCS-03 contract (agent author can integrate without reading source)
  - decision-tree custom diagram_type maps to layout_type=mind-map because the heuristic recommender only emits the 6 built-in layouts; documented honestly with a comment
  - D-05/D-06 policy values (>=3 outbound branches, betweenness centrality) ship as inline `# comments`, not as new YAML keys, because the loader's allowlist would reject them
metrics:
  duration_seconds: 237
  task_count: 3
  files_changed: 4
  completed_date: 2026-04-27
requirements_completed: [DOCS-01, DOCS-02, DOCS-03, DOCS-04]
---

# Phase 26 Plan 01: v1.5 Configuration Guide & Walkthrough Docs Summary

**One-liner:** Authored CONFIGURING_V1_5.md as a single-file root-level guide walking the v1.5 pipeline end-to-end (vault-promote → --diagram-seeds → --init-diagram-templates → install excalidraw → /excalidraw-diagram), including a complete annotated `.graphify/profile.yaml` with all six built-in `diagram_types` plus a custom `decision-tree` entry, a reference-quality MCP tool integration section quoting `list_diagram_seeds` / `get_diagram_seed` / `_resolve_alias` verbatim from source, plus a one-line README cross-link and tracker-hygiene fixes for REQUIREMENTS.md and ROADMAP.md.

## What Shipped

- **`CONFIGURING_V1_5.md`** (414 lines) — H1 + framing, Prerequisites, Sample vault layout, five pipeline-step H2s, profile YAML reference (strict superset of `README.md:343-365` example), MCP Tool Integration section with verbatim Tool declarations / arg tables / return-meta tables / invocation+return examples / `_resolve_alias` traversal-defense subsection.
- **`README.md`** — new H3 `### v1.5 Configuration Guide` placed between `### Vault Promotion — graphify vault-promote` and `## Worked examples` (verified line ordering vp=377 < v15=398 < we=402). One-line pitch + markdown link.
- **`.planning/REQUIREMENTS.md`** — DOCS-01..04 mapping rows changed from `Phase 26 | TBD` to `Phase 26 | 26-01-PLAN.md`. Zero TBDs remain for DOCS IDs.
- **`.planning/ROADMAP.md`** — Phase 26 plan list line replaced (was a copy-paste artifact from Phase 23: `23-01-PLAN.md — Patch dedup.py...`) with the actual `26-01-PLAN.md — Author CONFIGURING_V1_5.md...` entry. Verified: only one occurrence of the Phase 23 stub remains (in Phase 23's own block).

## Tasks Executed

| Task | Name                                                                       | Commit  | Files                                                                            |
| ---- | -------------------------------------------------------------------------- | ------- | -------------------------------------------------------------------------------- |
| 1    | Author CONFIGURING_V1_5.md (DOCS-01, DOCS-02, DOCS-03)                     | 07a6e16 | CONFIGURING_V1_5.md                                                              |
| 2    | Insert v1.5 Configuration Guide cross-link in README.md (DOCS-04)          | 6f59e51 | README.md                                                                        |
| 3    | Tracker hygiene — REQUIREMENTS mapping + ROADMAP stale stub fix            | c3fce18 | .planning/REQUIREMENTS.md, .planning/ROADMAP.md                                  |

## Verification Commands That Passed

```
# Task 1 — content presence
grep -q "vault-promote" CONFIGURING_V1_5.md
grep -q "\\-\\-diagram-seeds" CONFIGURING_V1_5.md
grep -q "\\-\\-init-diagram-templates" CONFIGURING_V1_5.md
grep -q "install --platform excalidraw" CONFIGURING_V1_5.md
grep -q "/excalidraw-diagram" CONFIGURING_V1_5.md
grep -q "diagram_types:" CONFIGURING_V1_5.md
grep -q "decision-tree" CONFIGURING_V1_5.md
grep -q "min_main_nodes" CONFIGURING_V1_5.md
grep -q "list_diagram_seeds" CONFIGURING_V1_5.md
grep -q "get_diagram_seed" CONFIGURING_V1_5.md
grep -q "_resolve_alias" CONFIGURING_V1_5.md
grep -q "\\[graphify\\] vault-promote complete" CONFIGURING_V1_5.md
grep -q "\\[graphify\\] diagram-seeds complete" CONFIGURING_V1_5.md
grep -q "\\[graphify\\] init-diagram-templates complete" CONFIGURING_V1_5.md

# Task 1 — YAML parses cleanly via yaml.safe_load
# Top keys: ['folder_mapping', 'naming', 'merge', 'mapping_rules', 'diagram_types']  (subset of 10 allowlisted)
# diagram_types[*] keys: ['name','template_path','trigger_node_types','trigger_tags','min_main_nodes','naming_pattern','layout_type','output_path']  (exactly the 8 allowlisted)
# diagram_types names: architecture, workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph, decision-tree

# Task 1 — no emojis (codepoints 0x2600-0x27BF absent)

# Task 2 — README ordering
# vp=377 v15=398 we=402  -> Vault Promotion < v1.5 Configuration Guide < Worked examples

# Task 3 — REQUIREMENTS rows
grep -E "^\\| DOCS-0[1-4] \\| Phase 26 \\| 26-01-PLAN.md \\|" .planning/REQUIREMENTS.md   # 4 lines
grep -c "DOCS-0[1-4] | Phase 26 | TBD" .planning/REQUIREMENTS.md                          # 0

# Task 3 — ROADMAP fix
grep -q "26-01-PLAN.md — Author CONFIGURING_V1_5.md" .planning/ROADMAP.md
grep -c "23-01-PLAN.md — Patch dedup.py" .planning/ROADMAP.md                             # 1 (only Phase 23's own block)
```

All verifications passed.

## Honesty Annotation Note

The guide explicitly distinguishes **loader-enforced gates** from **author-declared policies**. Per RESEARCH §4 (sourced from `seed.py:265-289`):

- The loader enforces only `min_main_nodes` as a numeric gate; D-07 tiebreak is "highest `min_main_nodes` wins, ties resolve via stable `max()` declaration order".
- The CONTEXT-prescribed policies (`>=3 outbound branches`, `betweenness centrality`) are NOT enforced by the loader. They appear in the example profile as inline `# comments` next to the `decision-tree` entry, with a clarifying paragraph below the YAML block stating that profile authors enforce these policies in their own downstream skill / agent logic.

This prevents the documented threat T-26-01 (Information Disclosure via misleading docs).

## Deviations from Plan

None — plan executed exactly as written. All grep-checkable acceptance criteria from the plan satisfied on first pass; no auto-fixes required.

## Self-Check: PASSED

- `CONFIGURING_V1_5.md` exists at repo root (414 lines).
- All three commits present in `git log`:
  - `07a6e16` docs(26-01): author CONFIGURING_V1_5.md v1.5 walkthrough + MCP tool reference
  - `6f59e51` docs(26-01): link CONFIGURING_V1_5.md from README v1.5 Configuration Guide section (DOCS-04)
  - `c3fce18` docs(26-01): map DOCS-01..04 to 26-01-PLAN.md and replace stale Phase 23 stub in ROADMAP Phase 26 entry
- Modified files (`README.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`) all contain the required strings.
- Embedded YAML parses via `yaml.safe_load` and uses only allowlisted keys.
