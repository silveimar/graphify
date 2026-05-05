# Feature Landscape

**Milestone:** v1.11 Templates, Graph Semantics & Vault Depth  
**Researched:** 2026-04-30

## Table stakes (must ship for theme to count)

| Theme | Users must be able to… |
|-------|-------------------------|
| **TMPL** | Use **conditional** sections and **connection loops** in vault templates driven by profile flags / graph context; optional **per-note-type Dataview** hooks from profile |
| **CFG / overrides** | Override templates **per community** or note-class where the profile schema allows (without breaking v1.7 composition) |
| **CGRAPH** | See **concept ↔ implementation** as **first-class graph edges** (validated extraction/build), queryable consistently from MCP/slash flows aligned with v1.10 MVP |
| **ELIC / HARN** | Make **elicitation → graph** and **harness export** measurably better than v1.9 baseline (artifacts, tests, documented limits) |
| **VAUX / HYG** | **Vault CLI** parity with doctor/dry-run; close acknowledged **registry/hygiene** items where scope fits |

## Differentiators

- Typed **concept_impl** / **implements_concept** (names TBD) edges with provenance — not only Obsidian frontmatter  
- Template engine remains **readable markdown** — not a generic CMS  
- **Inverse harness import** only behind explicit guards (prompt-injection / trust), not on by default  

## Anti-features / out of scope for this milestone

- Replacing `string.Template` entirely with Jinja2  
- Neo4j / new databases  
- Real-time collaborative editing  

## Dependencies between themes

1. **Validate/build schema** (CGRAPH) before exposing complex template variables that reference those edges  
2. **TMPL** expansion order: block parser **before** placeholder substitution (matches v1.7 TMPL layering discipline)  
