---
title: Create Graphify master key files in work vault
date: 2026-04-22
priority: high
---

# Create Graphify master key files in work vault

Add the 4 new master key files to `/Users/silveimar/Documents/work-vault/x/Templates/Master Keys/` so Dataview queries and tag pickers in Obsidian can enumerate all valid graphify tag values.

## Files to create

- [x] `Master Key (Graphify Source).md` — `source/*` tag namespace (confluence, readme, doc, code, paper, pdf, jira, slack, github, notion, obsidian, web)
- [x] `Master Key (Graphify Tech).md` — `tech/*` tag namespace (python, typescript, javascript, go, rust, java, sql, graphql, docker, k8s)
- [x] `Master Key (Graphify Node).md` — `graph/*` tag namespace (entity types + confidence: extracted, inferred, ambiguous)
- [x] `Master Key (Graphify Meta).md` — frontmatter properties (graphifyProject, graphifyRun, graphifyScore, graphifyThreshold)

## Done

All 4 files created 2026-04-22. Verify they appear in Obsidian tag suggester on next vault open.
