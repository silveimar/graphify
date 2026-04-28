# Phase 31: Template Engine Extensions - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add three template-engine extensions on top of the existing `graphify/templates.py` `string.Template` block-parser surface:

1. **TMPL-01** — `{{#if_X}}...{{/if}}` conditional sections evaluated against node attributes / classification context.
2. **TMPL-02** — `{{#connections}}...{{/connections}}` loop blocks iterating over a node's edges with per-iteration variable scope.
3. **TMPL-03** — Profile-declared per-note-type Dataview query strings injected at render time.

All three extensions stay inside the `string.Template` block-parser surface (no Jinja2, no new required dependencies) and remain backward-compatible: templates without `{{#…}}` blocks render exactly as today.

</domain>

<decisions>
## Implementation Decisions

### Conditional Predicates (TMPL-01)
- **D-01:** Hybrid predicate model — a fixed catalog of named predicates **plus** a namespaced `{{#if_attr_<name>}}` escape hatch for raw node-attribute truthiness. Catalog stays small and validatable; escape hatch is explicit and never collides with catalog names.
- **D-02:** Initial catalog ships with exactly four predicates:
  - `if_god_node` — node id is in analyze.py's god-node ranking (already computed during the analyze pipeline stage).
  - `if_isolated` — node has no edges in the graph (already detected by analyze.py knowledge-gap pass).
  - `if_has_connections` — node has ≥1 edge (inverse of `if_isolated`; convenience for hiding empty connection sections).
  - `if_has_dataview` — the rendered note will include a non-empty `${dataview_block}` (lets templates hide surrounding headings when the block is empty).
- **D-03:** `{{#if_attr_<name>}}` reads `G.nodes[node_id].get(<name>)` and tests Python truthiness. Unknown catalog names (e.g. `if_foobar` not in catalog and not prefixed with `attr_`) are a **preflight error** in `validate_template`, not a render-time error.

### Connection Loop Scope (TMPL-02)
- **D-04:** Inside `{{#connections}}…{{/connections}}`, iteration variables are **namespaced** as `${conn.<field>}`. Full field set exposed: `conn.label`, `conn.relation`, `conn.target`, `conn.confidence`, `conn.community`, `conn.source_file`. No outer-scope shadowing risk.
- **D-05:** Dot-syntax is implemented **both** ways and either form is accepted in user templates:
  - **Subclass `string.Template`** with extended `idpattern` allowing one optional dot segment: `[_a-z][_a-z0-9]*(\.[_a-z][_a-z0-9]*)?`. Used for templates whose preflight detected `{{#connections}}` blocks.
  - **Pre-flatten** fallback — the block pre-processor also emits a `${conn_label}` style flattened identifier alongside the dotted one, so `safe_substitute` works even on the stock `string.Template` if a downstream module reuses the engine without the subclass.
- **D-06:** `conn.confidence` renders as the EXTRACTED/INFERRED/AMBIGUOUS string (matching the existing edge schema). `conn.target` renders as the **node label**, not the raw node id, so wikilinks remain readable. Per-iteration values are sanitized via the same `_sanitize_wikilink_alias` path used by `_build_connections_callout` so labels containing `{{`, `}}`, `#`, backticks, control chars, etc. cannot break out of the rendered loop body.

### Nesting Policy
- **D-07:** Nested template blocks are **rejected with a clear error** — no nested `{{#connections}}` inside `{{#connections}}`, no `{{#if}}` inside `{{#connections}}`, no nested `{{#if}}` inside `{{#if}}`. Satisfies success criterion 2's "rejected with a clear error" alternative.
- **D-08:** Error message is specific and actionable, e.g. `validate_template: nested template blocks are not supported (found '{{#if_god_node}}' inside '{{#connections}}'). Flatten the template or pre-compute the predicate.` — not a generic regex failure.

### Validation Timing
- **D-09:** All block-related errors (nesting, unclosed `{{#…}}` / `{{/…}}`, unknown predicate name, unknown `conn.<field>` reference) surface from `validate_template` at **preflight time** — never at render time. Mirrors Phase 30's graph-blind `--validate-profile` philosophy: profile load fails fast, never mid-pipeline.
- **D-10:** Render-time only ever sees pre-validated templates; `render_note` / `render_moc` / `render_community_overview` do not need to defensively re-parse blocks.

### Per-Note-Type Dataview Queries (TMPL-03)
- **D-11:** New top-level profile key `dataview_queries: {note_type: query_string}`. Adds one entry to `_VALID_TOP_LEVEL_KEYS` in `graphify/profile.py`. Stays at top level (not nested under `obsidian:`) for portability — same precedent as Phase 30's `community_templates`.
- **D-12:** Keys are **restricted to `_KNOWN_NOTE_TYPES`** (`{moc, community, thing, statement, person, source}`). Unknown keys are a `validate_profile` error — prevents silent typos like `mocs:` or `Things:`.
- **D-13:** `_build_dataview_block` is extended to look up the per-note-type query first; falls back to today's hard-coded `moc_query` when no per-note-type override is declared. Existing two-phase substitution (substitute `${community_tag}`/`${folder}` into the user query first, then wrap in fence and feed to outer template) is preserved unchanged.
- **D-14:** Composes cleanly with Phase 30 `extends:`/`includes:` — `dataview_queries` deep-merges per-key (later definitions win per resolved chain). Per-key field provenance must show in the Phase 30 `--validate-profile` output for each `dataview_queries.<note_type>` entry.

### Sanitization (cross-cutting, success criterion 4)
- **D-15:** Substitution values flowing into block-rendered output (loop iteration values, predicate-guarded scalars) pass through the same sanitization layer the existing engine uses (`_sanitize_wikilink_alias` for labels, `_build_dataview_block`'s backtick/newline strip for query inputs). No node label can introduce a literal `{{`, `}}`, `#` sequence into the post-rendered output that would inject conditional logic or break out of a loop.
- **D-16:** Block parsing happens **before** scalar substitution. The block pre-processor expands `{{#connections}}…{{/connections}}` and `{{#if_X}}…{{/if}}` into a fully expanded text with sanitized inserts; only then does `safe_substitute` run. Order matters: substituting first would let a node label containing `{{#connections}}` smuggle a fake loop into the output.

### Claude's Discretion
- Exact regex / parser shape for the block pre-processor (suggested: a small finite-state pass over the template source rather than a recursive regex; left to the planner).
- Where the new `_BlockTemplate` subclass lives (suggested: `graphify/templates.py` next to `_BUILTIN_TEMPLATES_ROOT`).
- Whether the catalog table is a module-level dict (`_PREDICATE_CATALOG: dict[str, Callable[[Graph, str], bool]]`) or distributed function definitions — left to the planner.
- Whether `validate_template`'s signature grows new parameters or returns richer error objects — interface change left to the planner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 31: Template Engine Extensions" — phase goal, dependency on Phase 30, success criteria 1–4.
- `.planning/REQUIREMENTS.md` — TMPL-01, TMPL-02, TMPL-03 single-line requirements; v1.7 milestone scope.

### Phase 30 Carry-Forward (just-completed dependency)
- `.planning/phases/30-profile-composition/30-CONTEXT.md` — composition rules; `community_templates` precedent for new top-level keys; first-match-wins convention.
- `.planning/phases/30-profile-composition/30-RESEARCH.md` — deep-merge semantics (`_deep_merge` per-key precedence) — `dataview_queries` reuses this.

### Source Code Surfaces (must be edited)
- `graphify/templates.py` — full module. Specifically:
  - `validate_template` (line 134) — extend to detect/validate block syntax preflight.
  - `_KNOWN_NOTE_TYPES` and `_REQUIRED_PER_TYPE` (line 178+) — TMPL-03 keys validate against `_KNOWN_NOTE_TYPES`.
  - `_load_builtin_template` / `load_templates` (line 195, 207) — wrap returned `string.Template` instances in the new `_BlockTemplate` subclass when block syntax is present.
  - `_build_connections_callout` (line 388) — its sanitization pattern (`_sanitize_wikilink_alias`) is the reference for TMPL-02 loop iteration sanitization.
  - `_build_dataview_block` (line 525) — the two-phase substitution pattern; TMPL-03 plugs in here.
  - `render_note` (line 570), `_render_moc_like` (line 798), `render_moc` (line 917), `render_community_overview` (line 938) — render entry points; loop/conditional pre-processing must run inside `safe_substitute` flow.
- `graphify/profile.py` — `_VALID_TOP_LEVEL_KEYS` (line 105), `validate_profile`, `validate_profile_preflight` (`--validate-profile` engine), `_deep_merge` (line 156–166). TMPL-03 adds `dataview_queries` here.
- `graphify/analyze.py` — god-node ranking and isolated-node detection. `if_god_node` and `if_isolated` predicates source their truth from these existing computations.

### Sanitization & Security
- `graphify/security.py` — label sanitization (HTML-escape, control char strip, length cap). Cross-reference for D-15/D-16.
- `SECURITY.md` — full threat model, especially template-injection vectors.

### Testing Patterns
- `tests/test_templates.py` — existing block-parser tests; add TMPL-01/02/03 cases here.
- `tests/test_profile.py` — `validate_profile` test patterns; add `dataview_queries` validation cases here.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `string.Template.safe_substitute` — already wired through `render_note`, `_render_moc_like`, and `_build_dataview_block`. Block pre-processor produces a string; existing `safe_substitute` consumes it unchanged.
- `_sanitize_wikilink_alias` (templates.py line 284) — already strips control chars, backticks, pipes, brackets. Loop iteration values reuse this.
- `_build_dataview_block` two-phase substitution (line 525–559) — exact precedent for TMPL-03's user-query-then-wrap render order.
- `analyze.py` god-node ranking and isolated-node detection — predicates D-02 source from these without recomputation.
- `_deep_merge` in `profile.py` (Phase 30) — `dataview_queries` per-key deep-merge composes for free.

### Established Patterns
- **Top-level profile keys mirror existing shape** — `mapping_rules` (Phase 3), `community_templates` (Phase 30), `dataview_queries` (Phase 31) all live at top level, all validate via `_VALID_TOP_LEVEL_KEYS` whitelist, all participate in `_deep_merge`.
- **Two-phase substitution for nested user content** — established by `_build_dataview_block`; reused by TMPL-02 (loop body is pre-rendered scalar) and TMPL-01 (predicate-guarded section is pre-rendered scalar).
- **Preflight-only validation** — `validate_profile` and `validate_template` both fail at load time, never at render. Phase 31 keeps this invariant for blocks.
- **Sanitize-before-render** — every public render path pre-sanitizes inserts before substitution. Block expansion runs before sanitization-substitution to prevent label-driven block injection.

### Integration Points
- `load_templates` (templates.py line 207) — entry point where user-authored templates are read from `<vault>/.graphify/templates/`. Must wrap with `_BlockTemplate` when block syntax detected.
- `_build_dataview_block` (templates.py line 525) — receives `profile` dict; must look up `profile.get("dataview_queries", {}).get(note_type)` before falling back to legacy `moc_query`.
- `validate_profile_preflight` (profile.py) — must dump `dataview_queries` resolved values in `--validate-profile` output (per Phase 30 D-15/D-16 provenance precedent).
- Block pre-processor is a new pure function in `graphify/templates.py` consumed by `render_note` / `_render_moc_like` / `render_moc` / `render_community_overview` before their existing `safe_substitute` call.

</code_context>

<specifics>
## Specific Ideas

- The block syntax `{{#if_god_node}}…{{/if}}` and `{{#connections}}…{{/connections}}` is locked verbatim by ROADMAP.md success criteria 1 & 2 — no aliases, no alternative spellings.
- The hybrid `if_attr_<name>` escape hatch (D-01) is the user-facing extensibility surface — no need to keep adding catalog entries every phase.
- `${conn.X}` dot syntax with the parallel pre-flattened `${conn_X}` form (D-05) is intentionally forgiving so users authoring templates by hand don't get tripped up by string.Template's stock identifier rules.

</specifics>

<deferred>
## Deferred Ideas

- **Per-rule Dataview query on `community_templates` entries.** Considered as option (c) for TMPL-03 routing; rejected because it only covers community/MOC notes and not Things/Statements/etc. If a future phase needs *community-specific* Dataview queries (different query per community, not just per note type), it can extend `community_templates` entries with an optional `dataview_query` field at that time.
- **Nested block support.** Rejected for Phase 31 (D-07). If a future phase needs `{{#if_high_confidence}}` inside `{{#connections}}` (the realistic use case), it can lift the validate_template restriction and add a stack-based parser.
- **Predicate catalog expansion** beyond the four shipped in D-02. Things like `if_isolated_in_community`, `if_cross_community_bridge`, etc. can be added one-at-a-time as concrete template authors request them.
- **Render-time predicate evaluation against MCP write-back state** or other dynamic graph mutations. Out of scope; Phase 31 evaluates predicates against the immutable `nx.Graph` passed to `render_note`.
- **Loop blocks over members / sub-communities** (`{{#members}}…{{/members}}`). MOC member rendering is already handled by `_build_members_section`; loop syntax for it is not in TMPL-02's scope. Future phase if a real template authoring need surfaces.

</deferred>

---

*Phase: 31-template-engine-extensions*
*Context gathered: 2026-04-28*
</content>
</invoke>