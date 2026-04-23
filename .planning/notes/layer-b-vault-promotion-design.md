---
title: Layer B — Vault Promoted Knowledge Design
date: 2026-04-22
context: Exploration session — graphify-out → Ideaverse Pro 2.5 handoff design
---

# Layer B — Vault Promoted Knowledge Design

## Core principle

`graphify-out/` stays raw machine output. The vault receives promoted, typed notes. The script is the bridge — never a dumb file copy.

## Node → Ideaverse destination mapping

| Graphify node / condition | Vault destination | `up:` |
|---|---|---|
| domain, component, workflow, concept | `Atlas/Dots/Things/` | `[[Dots]]` |
| decision, architectural assertion | `Atlas/Dots/Statements/` | `[[Dots]]` |
| open question / knowledge gap | `Atlas/Dots/Questions/` | `[[Dots]]` |
| extracted quote / key passage | `Atlas/Dots/Quotes/` | `[[Dots]]` |
| person mentioned | `Atlas/Dots/People/` | `[[Dots]]` |
| cluster / community group | `Atlas/Maps/` (MOC per cluster) | `[[Atlas]]` |
| source file / external doc | `Atlas/Sources/Clippings/` | `[[Sources]]` |

Code entities (classes, functions, endpoints) are NOT promoted — they appear as evidence references inside Things notes.

## Promotion scoring gate

Promote a node if ANY of:
- `degree >= N` (tunable CLI flag)
- node appears in graphify's god-nodes list
- node type is decision / question / quote (always promote)

Below threshold → referenced as a backlink inside a promoted note only.

## Frontmatter schema

```yaml
---
up:
  - "[[Dots]]"
related:
  - "[[NodeB]]"          # EXTRACTED-confidence edges only
created: 2026-04-22
collections:
  - "[[ClusterMOC]]"
graphifyProject: my-repo
graphifyRun: 2026-04-22T14:28
graphifyScore: 12
graphifyThreshold: 5
tags:
  - garden/plant          # all auto-generated notes start here
  - source/readme         # origin document type
  - tech/python           # language/stack (if applicable)
  - graph/component       # graphify node kind
  - graph/extracted       # confidence level
---
```

Cluster MOCs start with `stateMaps: 🟥` (auto-generated, not yet reviewed).

## Tag master keys created (work vault)

- `Master Key (Graphify Source)` — `source/*` namespace
- `Master Key (Graphify Tech)` — `tech/*` namespace
- `Master Key (Graphify Node)` — `graph/*` namespace (entity type + confidence)
- `Master Key (Graphify Meta)` — `graphifyProject`, `graphifyRun`, `graphifyScore`, `graphifyThreshold` properties

## Hybrid tag taxonomy (VAULT-07)

Tag taxonomy follows the same 3-layer deep-merge pattern as folder_mapping:

```
Layer 1 — _DEFAULT_PROFILE in profile.py (hardcoded baseline)
  tag_taxonomy:
    garden: [plant, cultivate, probe, repot, revitalize, revisit, question]
    graph:  [component, domain, workflow, decision, concept, integration,
             service, dataset, team, extracted, inferred, ambiguous]
    source: [confluence, readme, doc, code, paper, pdf, jira, slack, github,
             notion, obsidian, web]
    tech:   [python, typescript, javascript, go, rust, java, sql, graphql,
             docker, k8s]

Layer 2 — .graphify/profile.yaml user overrides (deep-merged over defaults)
  tag_taxonomy:
    tech:
      - elixir       # project-specific additions

Layer 3 — Auto-detected per run, written back to profile.yaml (VAULT-06)
  tag_taxonomy:
    tech:
      - python       # inferred from graph.json source_file extensions
```

`_VALID_TOP_LEVEL_KEYS` in `profile.py` gains `tag_taxonomy` and `profile_sync`.

## Profile write-back (VAULT-06)

After each promotion run, `vault_promote.py` union-merges into `.graphify/profile.yaml`:
- Detected `tech/*` tags (from `source_file` extensions in `graph.json`)
- Detected `source/*` tags (from `file_type` field)
- Folder paths actually written this run (confirms folder_mapping is live)

**Write-back rules:**
- Union-only — never removes an existing entry
- Deduplicated and sorted alphabetically within each namespace
- Gated by `profile_sync.auto_update: true` (default) — user can opt out
- Safe write: reads profile → merges → rewrites atomically (temp file + rename)

## Script I/O

**Input:** `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`
**Config:** `.graphify/profile.yaml` (read + write-back)

**Output:**
- `Atlas/Dots/Things/<slug>.md`
- `Atlas/Dots/Statements/<slug>.md`
- `Atlas/Dots/Questions/<slug>.md`
- `Atlas/Dots/Quotes/<slug>.md`
- `Atlas/Dots/People/<slug>.md`
- `Atlas/Maps/<cluster-slug>.md`
- `Atlas/Sources/Clippings/<slug>.md`
- `.graphify/profile.yaml` (write-back: detected tags + used folders)
- `graphify-out/import-log.md` (run provenance)
