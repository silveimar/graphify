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

## Script I/O

**Input:** `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`

**Output:**
- `Atlas/Dots/Things/<slug>.md`
- `Atlas/Dots/Statements/<slug>.md`
- `Atlas/Dots/Questions/<slug>.md`
- `Atlas/Dots/Quotes/<slug>.md`
- `Atlas/Dots/People/<slug>.md`
- `Atlas/Maps/<cluster-slug>.md`
- `Atlas/Sources/Clippings/<slug>.md`
- `graphify-out/import-log.md` (run provenance)
