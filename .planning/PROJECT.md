# Ideaverse Integration — Configurable Vault Adapter

## What This Is

A configurable output adapter for graphify that injects knowledge graph data (nodes, edges, communities, analysis) into existing Obsidian vaults as properly-structured notes. Instead of graphify's current flat dump, the adapter reads a framework profile from the target vault (`.graphify/profile.yaml` + templates) and produces notes with correct frontmatter, wikilinks, tags, Dataview queries, folder placement, and naming conventions. When no vault profile exists, graphify falls back to a built-in default profile producing Ideaverse-compatible ACE structure.

## Core Value

Graphify can inject knowledge into any Obsidian vault framework — Ideaverse, custom fusions, or future frameworks — without code changes, driven entirely by a declarative vault-side profile.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] `.graphify/` vault-side profile system with `profile.yaml` + `templates/` directory
- [ ] Default built-in profile producing Ideaverse ACE-compatible output (Atlas/Maps, Atlas/Dots, Atlas/Sources)
- [ ] Profile YAML schema: folder mapping, mapping rules, merge behavior, naming conventions, Obsidian config
- [ ] Mapping rules support both graph topology (god node, community hub, leaf node) and node content/attributes (`file_type`, `type`, custom attributes)
- [ ] Vault profile takes precedence over default; graceful fallback when no profile exists
- [ ] Markdown templates with placeholders for note generation per note type (MOC, Dot/Thing, Dot/Statement, Dot/Person, Source, Community Overview)
- [ ] Merge/update strategy for existing notes — update by default, preserve user-specified frontmatter fields, skip or replace as configured
- [ ] Proper Ideaverse frontmatter generation: `up:`, `related:`, `collections:`, `created:`, `tags:` with wikilink format
- [ ] Community-to-MOC mapping: communities above configurable member threshold become MOCs in the configured Maps folder with Dataview queries
- [ ] God-node-to-Dot mapping: high-degree abstraction nodes become Dots (Things) with connections as body content
- [ ] Source-file-to-Source mapping: origin files become Source notes in configured Sources folder
- [ ] Wikilink generation respecting vault naming conventions
- [ ] Wayfinder generation in notes (configurable)
- [ ] Dataview query embedding in MOC notes (configurable)
- [ ] `.obsidian/graph.json` community color generation (configurable)
- [ ] Replaces current `to_obsidian()` in `export.py` while maintaining backward compatibility (no profile = similar output to current)

### Out of Scope

- Designing or generating the vault framework itself (ACE, Sefirot, Guitton, LSA, or fused framework) — separate project
- Wiki article generation (`wiki.py`) — existing separate system, not part of this integration
- Calendar and Efforts population — graphify produces knowledge (Atlas-equivalent), not time/action data
- Obsidian plugin development — output is standard markdown + frontmatter
- Real-time sync or watch mode integration — this is a batch injection operation
- Neo4j or other export formats — this is Obsidian-specific

## Context

- graphify already has a working `to_obsidian()` function in `export.py` (lines 440-679) that produces flat vaults with community tags, basic wikilinks, and a single Dataview query per community. This is the baseline to evolve.
- The target use case is the owner's fused Obsidian framework (Ideaverse ACE + Sefirot + Guitton + LSA Research), being designed in a separate project. graphify must be ready to receive that profile when it's defined.
- Ideaverse Pro 2.5 uses rich YAML frontmatter (`up:`, `related:`, `collections:`, `rank:`, `mapState:`, `tags:`), hierarchical folder structure (Atlas/Dots/{Things,Statements,People,Quotes,Questions}, Atlas/Maps/, Atlas/Sources/{Books,Movies,...}), MOCs with Dataview queries, wayfinders for navigation, and garden/architect maturity tags.
- The `.graphify/` directory pattern follows established conventions (`.editorconfig`, `.obsidian/`) — vault-owned, versioned with the vault, framework-agnostic.
- Graph data available for mapping: node attributes (label, file_type, source_file, source_location, community), edge attributes (relation, confidence, source_file, weight), community data (members, cohesion, labels), analysis data (god nodes, surprising connections, bridge nodes).

## Constraints

- **Python 3.10+**: Must work on CI targets (Python 3.10 and 3.12)
- **No new required dependencies**: Profile parsing uses stdlib (`yaml` via PyYAML already optional, `json` stdlib). Template rendering uses simple string substitution, not Jinja2.
- **Backward compatible**: Running `graphify --obsidian` without a profile in the target vault must produce output similar to current behavior
- **Existing test patterns**: Pure unit tests, no network calls, no filesystem side effects outside `tmp_path`
- **Security**: All file paths confined to output directory per `security.py` patterns. Template placeholders must be sanitized (no injection via node labels).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vault-side `.graphify/` profile over CLI flags | Vault owns its framework definition; portable, versionable, framework-agnostic | — Pending |
| YAML for profile, Markdown for templates | YAML is declarative and familiar; MD templates are native to Obsidian users | — Pending |
| Dual mapping (topology + content attributes) | Some note types are determined by graph position (god node → Thing), others by content (file_type: person → Person) | — Pending |
| Default = Ideaverse ACE structure | Most popular Obsidian framework; sensible fallback; validates the system works | — Pending |
| Update-by-default merge strategy | Users expect injected content to refresh, not duplicate; preserving user-edited fields prevents data loss | — Pending |
| Simple placeholder templating (no Jinja2) | Avoids new dependency; templates stay readable as plain markdown; sufficient for frontmatter + body generation | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 after initialization*
