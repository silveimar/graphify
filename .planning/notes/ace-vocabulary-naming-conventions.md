---
title: ACE Vocabulary, Linking & Naming Conventions
date: 2026-04-22
context: gsd-explore session — PKM Integration / Layer C design
status: ready-for-phase
---

# ACE Vocabulary, Linking & Naming Conventions

Design decisions captured from exploration of the Ideaverse Pro 2.5 ACE framework and how
graphify's internal vocabulary, exported frontmatter, dynamic view support, and file naming
should align with it.

---

## 1. ACE → Graphify Vocabulary Mapping

Graphify keeps its internal graph topology terms (`community`, `moc`, `node`, etc.) unchanged.
The `project.yaml` vocabulary section defines how those internal types translate to ACE
note types and vault folder placements on export. No translation layer — the config IS the
shared vocabulary between graphify and the vault.

| ACE concept | ACE folder | Graphify internal sources | Note |
|---|---|---|---|
| Map (MOC) | `Atlas/Maps` | `community`, `moc` | Graph cluster → navigational Map note |
| Dot | `Atlas/Dots` | `concept`, `god_node`, `component`, `domain`, `workflow`, `decision` | High-value promoted entity |
| Thing | `Atlas/Dots/Things` | `node` (default, low-score) | Supporting object; promote_threshold: 0.65 |
| Statement | `Atlas/Dots/Statements` | `insight`, `claim` | From analyze.py output |
| Question | `Atlas/Dots/Questions` | `suggested_question`, `knowledge_gap` | Currently only in GRAPH_REPORT.md — needs vault promotion |
| Person | `Atlas/Dots/People` | `person` | Direct match to existing graphify type |
| Source | `Atlas/Sources` | `document`, `paper` | Books, papers, repos analyzed |
| Work | `Efforts/Works` | `run` | One note per graphify run — the artifact record |

> Key: ACE "Works" are for notes that always leave behind a created artifact.
> A graphify run does exactly this. `Efforts/Projects` is wrong here.

---

## 2. project.yaml Vocabulary Section

```yaml
vocabulary:
  note_types:

    map:
      label: "Map"
      ace_folder: "Atlas/Maps"
      graphify_sources: [community, moc]
      tags: [map, graphify]
      template: map-template.md

    dot:
      label: "Dot"
      ace_folder: "Atlas/Dots"
      graphify_sources: [concept, god_node, component, domain, workflow, decision]
      tags: [dot, graphify]
      template: dot-template.md
      subtypes: [concept, component, service, domain, workflow, decision, glossary-term]

    thing:
      label: "Thing"
      ace_folder: "Atlas/Dots/Things"
      graphify_sources: [node]
      tags: [thing]
      template: thing-template.md
      promote_threshold: 0.65

    statement:
      label: "Statement"
      ace_folder: "Atlas/Dots/Statements"
      graphify_sources: [insight, claim]
      tags: [statement, graphify]
      template: statement-template.md

    question:
      label: "Question"
      ace_folder: "Atlas/Dots/Questions"
      graphify_sources: [suggested_question, knowledge_gap]
      tags: [question, graphify]
      template: question-template.md

    person:
      label: "Person"
      ace_folder: "Atlas/Dots/People"
      graphify_sources: [person]
      tags: [person]
      template: person-template.md

    source:
      label: "Source"
      ace_folder: "Atlas/Sources"
      graphify_sources: [document, paper]
      tags: [source, graphify]
      template: source-template.md

    work:
      label: "Work"
      ace_folder: "Efforts/Works"
      graphify_sources: [run]
      tags: [work, graphify]
      template: work-template.md

  tags:
    taxonomy:
      # graphify provenance
      - graphify
      - extracted
      - inferred
      - ambiguous
      # note types
      - map
      - dot
      - thing
      - statement
      - question
      - person
      - source
      - work
      # content vocabulary
      - architecture
      - workflow
      - decision
      - glossary-term
      - god-node
      - risk
      - promoted
      - reviewed
    inferred: []    # graphify appends discovered tag candidates here after each run

  diagrams:
    vault_root: "x/Excalidraw"
    folders:
      annotations:        "x/Excalidraw/annotations"
      cropped:            "x/Excalidraw/cropped"
      diagrams:           "x/Excalidraw/diagrams"
      palettes:           "x/Excalidraw/palettes"
      templates:          "x/Excalidraw/templates"
      seeds:              "x/Excalidraw/seeds"
      scripts_downloaded: "x/Excalidraw/scripts/downloaded"
      scripts_custom:     "x/Excalidraw/scripts/custom"

    defaults:
      layout: hierarchical
      style: ideaverse
      palette:
        map:       "#5BA65B"
        dot:       "#4A90D9"
        thing:     "#7B7B7B"
        statement: "#D4A843"
        source:    "#A67B5B"
        question:  "#9B59B6"
        work:      "#E67E22"

    templates:
      architecture:
        stencil: "x/Excalidraw/templates/architecture-template.excalidraw"
        include_types: [dot, map]
      workflow:
        stencil: "x/Excalidraw/templates/workflow-template.excalidraw"
        include_types: [dot, statement]
      glossary-graph:
        stencil: "x/Excalidraw/templates/glossary-graph-template.excalidraw"
        include_types: [dot]
        filter: "subtype == glossary-term"
```

---

## 3. Confidence Tags

All graphify-generated notes include one confidence tag reflecting how the node and its
primary edges were discovered:

| Tag | Meaning | Source |
|---|---|---|
| `extracted` | Node found by deterministic tree-sitter AST parsing; edges are EXTRACTED confidence | `extract.py` AST paths |
| `inferred` | Node found by LLM semantic analysis; edges are INFERRED with confidence_score | `extract.py` LLM paths |
| `ambiguous` | Node has majority AMBIGUOUS edges; connections uncertain | Edge confidence analysis |

These plug directly into Ideaverse's DYNAMIC TAGS base — "all inferred dots" or
"all ambiguous things" become zero-config Obsidian views for review and triage.

---

## 4. Backlinks & Frontmatter Properties

Ideaverse's dynamic views (DOTS.base, DYNAMIC LINKS.base, DYNAMIC TAGS.base) rely on:
1. **Folder path** — `FROM "Atlas/Dots"`, `file.folder.containsAny()` — free once ACE folders used
2. **Frontmatter wikilinks** — `up`, `related`, `collections` — Obsidian auto-tracks as backlinks
3. **`file.tags`** — powers DYNAMIC TAGS shared-tag views

Graphify has all this data in the graph. Full frontmatter target for a promoted Dot:

```yaml
---
up:
  - "[[map-graphify-core|Graphify Core Map]]"
related:
  - "[[dot-extract-pipeline|Extract Pipeline]]"
  - "[[dot-build-graph|Build Graph]]"
down:
  - "[[thing-tree-sitter-parser|Tree-sitter Parser]]"
collections:
  - "[[Dots]]"
source: graphify
source_run: 2026-04-22T14:28
rank: 4.2                     # from node score in mapping.py
created: 2026-04-22
tags: [dot, graphify, extracted]
---
```

Full frontmatter target for a Work note:

```yaml
---
up:
  - "[[Efforts]]"
collections:
  - "[[Works]]"
source_run: 2026-04-22T14:28
created: 2026-04-22
tags: [work, graphify, extracted]
produced:
  - "[[map-graphify-core|Graphify Core Map]]"
  - "[[dot-extract-pipeline|Extract Pipeline]]"
  - "[[question-why-community-zero-large|Why Is Community Zero So Large?]]"
artifact: "graphify-out/GRAPH_REPORT-2026-04-22.md"
---
```

### Current gap vs. target

| Frontmatter field | Status in graphify today |
|---|---|
| `up` | ✅ Partial — `parent_moc_label` covers community parent only |
| `related` | ❌ Not emitted — top neighbors exist in graph, not written |
| `down` | ❌ Not emitted |
| `collections` | ❌ Not emitted — type known, collection name not mapped |
| `rank` | ❌ Not emitted — score exists in `mapping.py`, not written |
| `created` | ✅ Run timestamp already written |
| Confidence tags | ❌ Not emitted — confidence exists per edge, not aggregated to note |
| Body wikilinks | ✅ `${members_section}` in Map template covers community members |

---

## 5. Naming Conventions

### Tags
- **Format**: `lowercase-hyphen-separated`
- **Allowed**: nouns, adjectives, verbs, content vocabulary, graphify-specific terms
- **Prohibited**: random numbers, opaque IDs, symbols, underscores, spaces
- **Valid**: `dot`, `thing`, `map`, `extracted`, `inferred`, `ambiguous`, `graphify`, `workflow`,
  `decision`, `glossary-term`, `god-node`, `risk`, `promoted`, `reviewed`
- **Invalid**: `node-123`, `item_1`, `2026tag`, `#abc`, `tag-xyz`

### Master Keys (ACE anchor/collection note titles)
- **Format**: `PascalCase`, max 4 meaningful words
- **Same spirit as tags** — no opaque IDs, no numbers, no symbols
- **Valid**: `Dots`, `Things`, `Maps`, `Sources`, `Atlas`, `Efforts`, `GraphifyRun`, `ArchitectureMap`
- **Invalid**: `MyDots2`, `Map_v1`, `note-123`

### MD file names (all vault notes)
- **Format**: `lowercase-hyphen-separated-words`
- No spaces, symbols, underscores, or meaningless numbers
- Always link with human-readable alias: `[[dot-extract-pipeline|Extract Pipeline]]`

**Prefixes for graphify-generated notes:**

| Type | Prefix | Example |
|---|---|---|
| Map | `map-` | `map-graphify-core.md` |
| Dot | `dot-` | `dot-extract-pipeline.md` |
| Thing | `thing-` | `thing-tree-sitter-parser.md` |
| Statement | `statement-` | `statement-graph-is-cyclic.md` |
| Question | `question-` | `question-why-community-zero-large.md` |
| Person | `person-` | `person-nick-milo.md` |
| Source | `source-` | `source-graphify-readme.md` |
| Work | `work-` | `work-graphify-analysis-april-twenty-two.md` |

### Template files
- **Format**: `lowercase-hyphen-template` before `.md`
- **Location**: `x/Templates/`
- **Examples**: `dot-template.md`, `map-template.md`, `work-template.md`, `thing-template.md`

### Diagram seeds
- **Format**: `lowercase-hyphen-separated`, **ends with `-seed`** before `.md`
- **Location**: `x/Excalidraw/seeds/`
- **Examples**: `graphify-core-architecture-seed.md`, `extract-pipeline-workflow-seed.md`

### Diagram files
- **Format**: `lowercase-hyphen-separated`, no spaces or symbols
- **Location**: `x/Excalidraw/diagrams/`
- **Examples**: `graphify-core-architecture.excalidraw.md`, `extract-pipeline-workflow.excalidraw.md`

### Excalidraw support files

| Subfolder | Convention | Example |
|---|---|---|
| `annotations/` | `lowercase-hyphen` | `graphify-core-annotation.md` |
| `cropped/` | `lowercase-hyphen` | `diagram-cropped-detail.png` |
| `palettes/` | `lowercase-hyphen` | `ideaverse-palette.json` |
| `templates/` | `lowercase-hyphen-template` suffix | `architecture-template.excalidraw` |
| `scripts/custom/` | `lowercase-hyphen` | `auto-seed-generator.js` |
| `scripts/downloaded/` | preserve original; rename on conflict | — |

---

## 6. Impact on Graphify Code

| File | Change needed |
|---|---|
| `profile.py` | Parse `vocabulary:` section; expose `note_types`, `tags`, `diagrams` as typed dicts |
| `templates.py` | Replace hardcoded `_NOTE_TYPES` frozenset with `vocab.note_types.keys()` from profile |
| `mapping.py` | `classify()` uses profile vocabulary rules; `rank` score written to frontmatter |
| `export.py` | Emit `related`, `collections`, `down`, `rank`, confidence tags in all promoted notes |
| `builtin_templates/` | Add `map-template.md`, `dot-template.md`, `work-template.md`, `question-template.md` |
| `profile.py::safe_filename()` | Must emit `lowercase-hyphen` (not underscore) for vault file names |
| `seeds.py` (new) | Reads `vocab.diagrams` for template/stencil/palette; emits `-seed.md` files to `x/Excalidraw/seeds/` |
| `extract.py::_make_id()` | Keep `lowercase_underscore` for internal graph IDs only — never used as vault filenames |

**Key invariant**: `_make_id()` (underscore, internal) and `safe_filename()` (hyphen, vault) must
never be confused. Internal graph IDs are stable topology references; vault filenames are ACE-aligned
human-readable slugs.
