# Phase 31: Template Engine Extensions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 31-template-engine-extensions
**Areas discussed:** Conditional predicates, Connection loop scope, Nested loops/conds policy, Dataview per-note-type shape

---

## Conditional Predicates (TMPL-01)

### Predicate model

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed catalog only | Hardcoded set of predicates; unknown → validate_template error. Predictable and validatable. | |
| Dynamic attribute lookup | `if_<attr>` reads node attribute and tests truthiness. Maximum flexibility, harder preflight validation. | |
| Hybrid: catalog + namespaced attr | Named catalog predicates PLUS `if_attr_<name>` raw escape hatch. Catalog stays validatable; escape hatch stays explicit. | ✓ |

**User's choice:** Hybrid: catalog + namespaced attr
**Notes:** Catalog covers the common cases visibly; `if_attr_<name>` keeps the surface extensible without forcing every new attribute through a new phase.

### Initial catalog content (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| if_god_node | Node is in analyze.py god-node ranking. Required by success criterion 1. | ✓ |
| if_isolated | Node has no edges (analyze.py knowledge-gap pass already detects). | ✓ |
| if_has_connections | Node has ≥1 edge; convenience for hiding empty connection sections. | ✓ |
| if_has_dataview | Rendered note will include non-empty `${dataview_block}`. | ✓ |

**User's choice:** All four ship in the initial catalog.
**Notes:** Each maps to a computation already performed by the pipeline — no new analysis stage required.

---

## Connection Loop Scope (TMPL-02)

### Iteration variable shape

| Option | Description | Selected |
|--------|-------------|----------|
| Bare names, core fields only | `${label}`, `${relation}`, `${target}`, `${confidence}` shadow outer scope. Minimal. | |
| Namespaced (`${conn.X}`) | `${conn.label}`, `${conn.relation}`, `${conn.target}`, `${conn.confidence}`, `${conn.community}`. No shadowing; richer fields; needs string.Template parser extension. | ✓ |
| Bare names, full field set | Bare names with full set; shadowing risk on `label`/`source_file` but no parser changes. | |

**User's choice:** Namespaced (`${conn.X}`)
**Notes:** Avoids shadowing the outer-scope `${label}` (the parent node's label) and keeps loop-body intent obvious in template source.

### Dot-syntax implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Subclass `string.Template` | Extend `idpattern` to allow one optional dot segment. | |
| Pre-flatten to `${conn_label}` | Block pre-pass converts `${conn.label}` → `${conn_label}` before stock substitution. | |
| Both (accept either) | Subclass + pre-flatten fallback so users can author either form. | ✓ |

**User's choice:** Both (accept either)
**Notes:** Forgiving; users authoring templates by hand don't have to remember which form is canonical. Doubles validation surface but the validator is internal.

---

## Nesting Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Reject with clear error | validate_template rejects any nested `{{#…}}` block with a specific error. | ✓ |
| Allow `if` inside `connections` | Permit the realistic 'show only high-confidence connections' use case; reject loop-in-loop. | |
| Full nesting | Stack-based parser with depth limit. | |

**User's choice:** Reject with clear error
**Notes:** Smallest parser, fully predictable, satisfies criterion 2's "rejected with clear error" alternative. Future phase can lift the restriction if real-world templates demand nesting.

---

## Validation Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Preflight only (validate_template) | All block errors surface from validate_template before rendering. | ✓ |
| Preflight + render-time fallback | Static errors at preflight; dynamic errors at render. Two error paths. | |

**User's choice:** Preflight only (validate_template)
**Notes:** Mirrors Phase 30's `--validate-profile` graph-blind philosophy — fail fast at profile/template load, never mid-pipeline.

---

## Dataview Per-Note-Type Shape (TMPL-03)

### Profile location

| Option | Description | Selected |
|--------|-------------|----------|
| Top-level `dataview_queries` | New top-level key `dataview_queries: {note_type: query}`. Mirrors `mapping_rules`/`community_templates`. Adds one entry to `_VALID_TOP_LEVEL_KEYS`. | ✓ |
| Nested under `obsidian.note_types` | Co-locate with template path, folder, naming convention already configured per note type. | |
| Per-rule on `community_templates` | Extend Phase 30 entries with `dataview_query`. Tightly coupled — only covers community/MOC. | |

**User's choice:** Top-level `dataview_queries`
**Notes:** Stays portable to non-Obsidian export targets. Composes cleanly with Phase 30 `extends:`/`includes:` deep-merge.

### Key validation

| Option | Description | Selected |
|--------|-------------|----------|
| Restrict to `_KNOWN_NOTE_TYPES` | Keys must be in {moc, community, thing, statement, person, source}; unknown → validate_profile error. | ✓ |
| Allow any key, warn on unknown | Forward-compatible for future custom note types; warns rather than errors. | |

**User's choice:** Restrict to `_KNOWN_NOTE_TYPES`
**Notes:** Prevents silent typos like `mocs:` from doing nothing. New note types are themselves a phase-level addition; gating Dataview keys on the known set keeps both in lockstep.

---

## Claude's Discretion

- Exact regex / parser shape for the block pre-processor (suggested: small finite-state pass, not recursive regex).
- Module placement of the `_BlockTemplate` subclass.
- Whether predicate catalog is a `_PREDICATE_CATALOG: dict[str, Callable]` or distributed function definitions.
- Whether `validate_template`'s signature grows or returns richer error objects.

## Deferred Ideas

- Per-rule Dataview query on `community_templates` entries (community-specific, not just per-note-type).
- Nested block support (loop-in-loop, if-in-loop).
- Predicate catalog expansion beyond the four shipped predicates.
- Render-time predicate evaluation against MCP write-back state or dynamic graph mutations.
- Loop blocks over members / sub-communities (`{{#members}}…{{/members}}`).
</content>
</invoke>