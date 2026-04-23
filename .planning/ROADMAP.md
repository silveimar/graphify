# Roadmap: graphify

## Milestones

- ✅ **v1.0 Ideaverse Integration — Configurable Vault Adapter** — Phases 1–5 (shipped 2026-04-11)
- 📋 **v1.1 (TBD)** — Not yet defined. Run `/gsd-new-milestone` to scope.

## Phases

<details>
<summary>✅ v1.0 Ideaverse Integration — Configurable Vault Adapter (Phases 1–5) — SHIPPED 2026-04-11</summary>

Configurable output adapter replacing the monolithic `to_obsidian()` with a four-component vault-driven pipeline: profile loading → template rendering → mapping classification → safe merge → CLI wiring. Reads a `.graphify/profile.yaml` from the target vault, falls back to a built-in Ideaverse ACE default when absent, and supports `graphify --obsidian [--dry-run]` plus `graphify --validate-profile` as direct CLI entry points.

**Phases:**

- [x] Phase 1: Foundation — Profile loader, filename safety utilities, and security primitives; FIX-01..05 bug fixes (2/2 plans, completed 2026-04-11)
- [x] Phase 2: Template Engine — Note rendering via `string.Template` with 6 built-in templates (MOC, Thing, Statement, Person, Source, Community Overview) (4/4 plans, completed 2026-04-11)
- [x] Phase 3: Mapping Engine — Topology + attribute classification of nodes into note types and folder placements (4/4 plans, completed 2026-04-11)
- [x] Phase 4: Merge Engine — Safe frontmatter round-trip with `preserve_fields`, field-order preservation, and configurable merge strategies (6/6 plans, completed 2026-04-11)
- [x] Phase 5: Integration & CLI — Wire all four modules into refactored `to_obsidian()`; add `--dry-run` and `--validate-profile` CLI flags (6/6 plans including 05-06 gap-closure, completed 2026-04-11)

**Totals:** 5 phases, 22 plans, 31/31 in-scope requirements satisfied, 2 requirements de-scoped via D-74 (OBS-01/OBS-02).

**Archives:**
- Full phase detail: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

</details>

### 📋 v1.1 (TBD — Not yet defined)

Next milestone is unscoped. Candidate work carried forward from v1.0's v2 Requirements list (`.planning/milestones/v1.0-REQUIREMENTS.md`) and PROJECT.md Active section:

- Conditional template sections (`{{#if_god_node}}...{{/if}}` guards) — TMPL-01
- Loop blocks for template connections (`{{#connections}}...{{/connections}}`) — TMPL-02
- Custom Dataview query templates per note type in profile — TMPL-03
- Profile includes/extends mechanism (compose profiles from fragments) — CFG-02
- Per-community template overrides — CFG-03
- Revisit `.obsidian/graph.json` management (OBS-01/02) as plugin-side integration — if user demand emerges

**Run `/gsd-new-milestone` to formally scope v1.1.**

---

### 🌱 Candidate Phase: ACE-Aligned Vocabulary, Linking & Naming

**Goal:** Replace graphify's hardcoded note-type vocabulary with an ACE-aligned,
profile-driven system. Emit full Ideaverse-compatible frontmatter (backlinks, collections,
rank, confidence tags) and enforce naming conventions across all vault output.

**Scope:**

- `project.yaml` — new `vocabulary:` section (note types, tags taxonomy, `diagrams:` with
  `x/Excalidraw/` folder map and per-template stencil/palette config)
- `profile.py` — parse and validate the `vocabulary:` section; expose typed dicts to all exporters
- `templates.py` — replace hardcoded `_NOTE_TYPES` frozenset with `vocab.note_types.keys()`
  loaded from profile; add `map`, `dot`, `work`, `question` built-in templates
- `mapping.py` — `classify()` driven by profile vocabulary rules; emit `rank` score to frontmatter
- `export.py` — emit full frontmatter: `up`, `related`, `down`, `collections`, `rank`,
  `created`, and confidence tags (`extracted`/`inferred`/`ambiguous`) on all promoted notes;
  all vault filenames use `safe_filename()` → `lowercase-hyphen` slugs with type prefix
- `seeds.py` (new) — generate `-seed.md` files in `x/Excalidraw/seeds/` from promoted Dots
  using `vocab.diagrams` template/stencil/palette config
- `builtin_templates/` — add `map-template.md`, `dot-template.md`, `work-template.md`,
  `question-template.md`; rename existing templates to `lowercase-hyphen-template` convention

**Naming conventions enforced (all output):**
- Tags: `lowercase-hyphen-separated`, no IDs/symbols/numbers
- Master Keys: `PascalCase`, max 4 words
- MD filenames: `lowercase-hyphen-separated` with type prefix
- Wikilinks: always with human-readable alias `[[filename|Human Readable Alias]]`
- Seeds: `name-seed.md` in `x/Excalidraw/seeds/`
- Diagrams: `name.excalidraw.md` in `x/Excalidraw/diagrams/`

**ACE folder targets:**
`Atlas/Maps`, `Atlas/Dots`, `Atlas/Dots/Things`, `Atlas/Dots/Statements`,
`Atlas/Dots/Questions`, `Atlas/Dots/People`, `Atlas/Sources`, `Efforts/Works`,
`x/Excalidraw/{annotations,cropped,diagrams,palettes,templates,seeds,scripts/downloaded,scripts/custom}`

**Design doc:** `.planning/notes/ace-vocabulary-naming-conventions.md`

**Entry point:** Run `/gsd-add-phase` to formally scope and plan this phase.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-04-11 |
| 2. Template Engine | v1.0 | 4/4 | Complete | 2026-04-11 |
| 3. Mapping Engine | v1.0 | 4/4 | Complete | 2026-04-11 |
| 4. Merge Engine | v1.0 | 6/6 | Complete | 2026-04-11 |
| 5. Integration & CLI | v1.0 | 6/6 | Complete | 2026-04-11 |

---
*Last updated: 2026-04-11 after v1.0 milestone completion. Detail-bearing ROADMAP.md archived to `.planning/milestones/v1.0-ROADMAP.md`; this file will be rewritten when v1.1 is defined.*
