# Phase 31: Template Engine Extensions - Research

**Researched:** 2026-04-28
**Domain:** `string.Template` block-parser extensions for Obsidian-vault note rendering
**Confidence:** HIGH (CONTEXT.md locks every load-bearing decision; remaining surface is purely concrete-implementation choice over already-locked semantics; all source-line citations verified by direct read of `templates.py` / `profile.py` / `analyze.py`).

## Summary

Phase 31 layers three orthogonal extensions onto graphify's existing `string.Template`-backed renderer in `graphify/templates.py`:

1. **TMPL-01** `{{#if_X}}…{{/if}}` conditional blocks — fixed catalog of four predicates (`if_god_node`, `if_isolated`, `if_has_connections`, `if_has_dataview`) plus an `{{#if_attr_<name>}}` escape hatch reading raw node attributes.
2. **TMPL-02** `{{#connections}}…{{/connections}}` loop blocks — iterates outgoing edges with per-iteration `${conn.<field>}` (and parallel pre-flattened `${conn_<field>}`) variable scope.
3. **TMPL-03** `dataview_queries: {note_type: query}` profile field — per-note-type Dataview blocks, falling back to legacy `obsidian.dataview.moc_query` when not declared.

All three are **pure preprocessing** in front of the existing `safe_substitute` pipeline. The block expander is a new pure function inside `templates.py`; render entry points (`render_note`, `_render_moc_like`, `render_moc`, `render_community_overview`) call it before the existing `template.safe_substitute(substitution_ctx)` call. `validate_template` (line 133) is the *single* place block syntax errors surface — preflight only, never at render time.

**Primary recommendation:** Implement a small finite-state line/character pass `expand_blocks(template_text, ctx) -> str` (no recursive regex). Land the work as **2 plans, not 3** — the sanitization-hardening surface is small enough to merge into Plan 01. Plan 02 isolates TMPL-03 because it touches a different module (`profile.py`) and carries Phase 30 `--validate-profile` provenance debt.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Block syntax recognition + expansion (TMPL-01/02) | Templates / `graphify/templates.py` | — | Same file owns `_sanitize_wikilink_alias` + `_build_*_callout` helpers blocks reuse |
| Predicate catalog evaluation | Templates (catalog dispatch) | Analyze (`analyze.god_nodes` source-of-truth) | Predicates *consult* analyze.py outputs but live in templates.py to keep cycle-free |
| `{{#if_attr_*}}` escape hatch | Templates (regex extraction + `G.nodes[node_id].get(attr)`) | — | Pure node-attribute read; no analyze dependency |
| `${conn.X}` substitution syntax | Templates (`_BlockTemplate(string.Template)` subclass) | — | Subclass of stdlib `string.Template`; idpattern extension only |
| Loop iteration source (edges) | Templates → NetworkX `G.edges(node_id, data=True)` | — | Mirror existing `_build_connections_callout` (line 397) |
| `dataview_queries` schema validation | `graphify/profile.py::validate_profile` | — | Belongs with other top-level key checks |
| `dataview_queries` runtime lookup | `graphify/templates.py::_build_dataview_block` | — | Already the single Dataview-fence builder |
| `--validate-profile` per-key provenance for new key | `graphify/profile.py::validate_profile_preflight` | — | Reuses Phase 30 `provenance` machinery (line 194 `_deep_merge_with_provenance`) |
| Loop body sanitization | Templates → `_sanitize_wikilink_alias` (line 283) + `_build_dataview_block` strip | — | Reuse, never reimplement |

## Project Constraints (from CLAUDE.md + PROJECT.md)

- **Python 3.10+** on CI targets 3.10 and 3.12.
- **No new required dependencies.** No Jinja2. PyYAML stays optional under `[obsidian]`. Block parser uses stdlib only (`re`, `string`).
- **Backward compatibility:** templates without `{{#…}}` blocks must render byte-identical to today.
- **Pure unit tests:** no network, no filesystem outside `tmp_path`.
- **`from __future__ import annotations`** as first import (matches templates.py line 11, profile.py line 2).
- **All file paths confined to output directory** per `security.py::validate_vault_path` patterns. Override template paths in `community_templates` already use this contract via `_load_override_template` (line 713) — Phase 31 does not introduce new path-loading surfaces.
- **No injection via node labels.** All substitution values pass through existing sanitization (`_sanitize_wikilink_alias`, `_build_dataview_block` strip). Block expansion runs **before** scalar substitution to defeat label-injection of `{{`/`}}`/`#`.
- **`templates.py` is pure stdlib** (per the module docstring lines 2–9 of templates.py): does NOT import PyYAML, networkx, or third-party packages directly. Phase 31 must preserve this — predicates read `G.nodes[...]` and `G.edges(...)` via duck-typing only (no `import networkx`).

## User Constraints (from CONTEXT.md)

### Locked Decisions (verbatim from 31-CONTEXT.md `<decisions>`)

**Conditional Predicates (TMPL-01):**
- **D-01:** Hybrid predicate model — fixed catalog **plus** namespaced `{{#if_attr_<name>}}` escape hatch.
- **D-02:** Initial catalog ships exactly four: `if_god_node`, `if_isolated`, `if_has_connections`, `if_has_dataview`.
- **D-03:** `{{#if_attr_<name>}}` reads `G.nodes[node_id].get(<name>)` and tests Python truthiness. Unknown catalog names are a **preflight error** in `validate_template`.

**Connection Loop Scope (TMPL-02):**
- **D-04:** Inside `{{#connections}}…{{/connections}}`, iteration variables are namespaced as `${conn.<field>}`. Full field set: `conn.label`, `conn.relation`, `conn.target`, `conn.confidence`, `conn.community`, `conn.source_file`.
- **D-05:** Dot-syntax implemented **both ways** — subclass `string.Template` with extended `idpattern` `[_a-z][_a-z0-9]*(\.[_a-z][_a-z0-9]*)?`, AND emit a parallel pre-flattened `${conn_<field>}` form so stock `string.Template` works downstream.
- **D-06:** `conn.confidence` renders as the EXTRACTED/INFERRED/AMBIGUOUS string. `conn.target` renders as the **node label**, not raw node id. Per-iteration values sanitized via `_sanitize_wikilink_alias`.

**Nesting Policy:**
- **D-07:** Nested template blocks are **rejected with a clear error** — no nested `{{#connections}}` inside `{{#connections}}`, no `{{#if}}` inside `{{#connections}}`, no nested `{{#if}}`.
- **D-08:** Error message specific and actionable, e.g. `validate_template: nested template blocks are not supported (found '{{#if_god_node}}' inside '{{#connections}}'). Flatten the template or pre-compute the predicate.`

**Validation Timing:**
- **D-09:** All block-related errors (nesting, unclosed `{{#…}}`/`{{/…}}`, unknown predicate, unknown `conn.<field>`) surface from `validate_template` at **preflight time**.
- **D-10:** Render-time only ever sees pre-validated templates.

**Per-Note-Type Dataview Queries (TMPL-03):**
- **D-11:** New top-level profile key `dataview_queries: {note_type: query_string}`. Adds entry to `_VALID_TOP_LEVEL_KEYS`.
- **D-12:** Keys restricted to `_KNOWN_NOTE_TYPES = {moc, community, thing, statement, person, source}`.
- **D-13:** `_build_dataview_block` extended to look up per-note-type query first; falls back to today's hard-coded `moc_query`. Existing two-phase substitution preserved.
- **D-14:** Composes cleanly with Phase 30 `extends:`/`includes:` — `dataview_queries` deep-merges per-key. Per-key field provenance must show in `--validate-profile` output for each `dataview_queries.<note_type>` entry.

**Sanitization (cross-cutting):**
- **D-15:** Substitution values flowing into block-rendered output pass through the same sanitization layer as the existing engine.
- **D-16:** Block parsing happens **before** scalar substitution.

### Claude's Discretion
- Exact regex / parser shape for the block pre-processor (suggested: small finite-state pass, not recursive regex).
- Where the new `_BlockTemplate` subclass lives (suggested: `graphify/templates.py` next to `_BUILTIN_TEMPLATES_ROOT`).
- Whether the catalog table is a module-level dict or distributed function definitions.
- Whether `validate_template`'s signature grows new parameters or returns richer error objects.

### Deferred Ideas (OUT OF SCOPE)
- Per-rule Dataview query on `community_templates` entries.
- Nested block support.
- Predicate catalog expansion beyond the four shipped in D-02.
- Render-time predicate evaluation against MCP write-back state.
- Loop blocks over members / sub-communities (`{{#members}}…{{/members}}`).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TMPL-01 | Conditional template sections — `{{#if_god_node}}...{{/if}}` guards in markdown templates, evaluated against node attributes | §1 Block parser; §3 Predicate catalog; §4 `if_attr_` escape hatch |
| TMPL-02 | Loop blocks for connections — `{{#connections}}...{{/connections}}` iteration with per-iteration variable scope | §1 Block parser; §2 `_BlockTemplate` subclass; §5 Iteration source; §6 Sanitization |
| TMPL-03 | Custom Dataview query templates per note type — profile field declaring per-note-type query strings | §7 TMPL-03 integration; §8 `validate_profile` integration |

## Standard Stack

### Core (already imported / no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `string.Template` | stdlib (Py 3.10+) | Existing scalar substitution surface | Already drives `_build_dataview_block`, `render_note`, `_render_moc_like` — the Phase 31 mandate is to *stay* on it, not replace |
| `re` | stdlib | Block-syntax tokenization, `_BlockTemplate.idpattern` extension, `if_attr_<name>` extraction | Already imported (templates.py line 16) |
| `fnmatch` | stdlib | Already imported by templates.py for Phase 30 community-template matching | Reused for any future glob needs (none in Phase 31) |
| NetworkX (duck-typed) | n/a | Edge enumeration for `{{#connections}}`, node-attr access for predicates | templates.py never `import networkx` directly — only consumes `G.nodes[id]` / `G.edges(id, data=True)` / `id in G` (existing pattern at lines 393–407) |

### Verification

`python3 -c "import string; print(string.Template.idpattern)"` returned `(?a:[_a-z][_a-z0-9]*)` on Python 3.12 (verified 2026-04-28). The default `pattern` uses ASCII-only identifier characters in the `named` and `braced` groups. Subclassing with an extended `idpattern` is the documented stdlib mechanism (CITED: docs.python.org/3/library/string.html#string.Template.idpattern). On Python 3.10+ overriding `idpattern` is sufficient because `string.Template.__init_subclass__` recompiles `pattern` when a subclass redefines either `delimiter`, `idpattern`, `braceidpattern`, or `flags`.

### Don't add

- **No Jinja2.** Locked by REQUIREMENTS.md "Out of Scope" + CONTEXT.md `<deferred>` and reaffirmed by D-16 (sanitization invariants depend on rendering staying single-pass after block expansion).
- **No new sanitization library.** Reuse `_sanitize_wikilink_alias` (templates.py line 283) and the `_build_dataview_block` backtick/newline strip (line 549).

## Architecture Patterns

### System Architecture Diagram

```
                     ┌──────────────────────────────────────────────┐
                     │          render_note (line 569)              │
                     │          _render_moc_like (line 797)         │
                     └────────────────────┬─────────────────────────┘
                                          │ (after sections built;
                                          │  before safe_substitute)
                                          ▼
            ┌─────────────────────────────────────────────────────────┐
            │     expand_blocks(template_text, ctx) -> str   [NEW]    │
            │  ┌────────────────────────────────────────────────┐    │
            │  │ 1. Tokenize: scan for {{#NAME}} … {{/NAME}}    │    │
            │  │ 2. Reject nested blocks → raise / error list   │    │
            │  │ 3. For each block:                             │    │
            │  │    - if connections: enumerate G.edges(node)   │    │
            │  │      → emit dotted + flattened conn vars,      │    │
            │  │        sanitize labels via                     │    │
            │  │        _sanitize_wikilink_alias                │    │
            │  │    - if predicate: dispatch _PREDICATE_CATALOG │    │
            │  │      or {{#if_attr_X}} → bool(G.nodes[id][X])  │    │
            │  │ 4. Splice expanded text in place               │    │
            │  └────────────────────────────────────────────────┘    │
            └────────────────────────┬────────────────────────────────┘
                                     │ block-free expanded text
                                     ▼
                    ┌────────────────────────────────────────┐
                    │  template.safe_substitute(ctx)         │
                    │  ─ template is _BlockTemplate when     │
                    │    block syntax was detected           │
                    │  ─ stock string.Template otherwise     │
                    │    (back-compat path)                  │
                    └────────────────────────────────────────┘

                                  ┌──────────────────────────────┐
                                  │ validate_template (line 133) │
                                  │  ─ extended to detect:       │
                                  │    {{#…}} blocks, nesting,   │
                                  │    unclosed, unknown preds,  │
                                  │    unknown conn.<field>      │
                                  │  ─ runs at preflight via     │
                                  │    load_templates (line 245) │
                                  │    AND _load_override_template│
                                  │    (line 749)                │
                                  └──────────────────────────────┘
```

### Component Responsibilities

| Component | File | Lines | Responsibility (Phase 31) |
|-----------|------|-------|---------------------------|
| `validate_template` | templates.py | 133–169 | EXTEND: detect block syntax, validate nesting/closure/predicate names/conn fields; preserve existing `${var}` checks unchanged |
| `expand_blocks` (NEW) | templates.py | NEW | Pure function: take template text + a `BlockContext` (G, node_id, profile, note_type, dataview_block_value), emit fully-expanded text with all `{{#…}}` blocks replaced |
| `_PREDICATE_CATALOG` (NEW) | templates.py | NEW | Module-level `dict[str, Callable[[BlockContext], bool]]` keyed *with* the `if_` prefix (e.g., `"if_god_node"`) for symmetry with the user-facing syntax |
| `_BlockTemplate` (NEW) | templates.py | NEW | `class _BlockTemplate(string.Template): idpattern = r"(?a:[_a-z][_a-z0-9]*(?:\.[_a-z][_a-z0-9]*)?)"` |
| `_build_dataview_block` | templates.py | 524–562 | EXTEND: accept `note_type` argument; consult `profile["dataview_queries"][note_type]` first; fall back to `obsidian.dataview.moc_query` |
| `render_note` | templates.py | 569–702 | EXTEND: invoke `expand_blocks` before `safe_substitute`; for non-MOC notes also build a `dataview_block` value when `dataview_queries` declares one for the note_type AND template references `${dataview_block}` |
| `_render_moc_like` | templates.py | 797–913 | EXTEND: invoke `expand_blocks`; pass `note_type=template_key` ("moc"/"community") to `_build_dataview_block` |
| `_VALID_TOP_LEVEL_KEYS` | profile.py | 130–135 | EXTEND: add `"dataview_queries"` |
| `validate_profile` | profile.py | 447 | EXTEND: validate `dataview_queries` is a dict, every key ∈ `_KNOWN_NOTE_TYPES`, every value is a non-empty string |
| `validate_profile_preflight` | profile.py | 980 | NO CHANGE — provenance machinery already records `dataview_queries.<note_type>` leaves automatically because `_deep_merge_with_provenance` (line 194) is recursive over any dict-of-scalar leaves; only the `--validate-profile` text formatter (Phase 30 Plan 03) needs to confirm it picks up the new dotted keys cleanly |

### Pattern 1: Pre-flight Validation, Never Render-Time

**What:** All block-related errors surface from `validate_template` at preflight time. `expand_blocks` *assumes* well-formed input.

**When to use:** Always — D-09/D-10 lock this.

**Why:** Mirrors Phase 30 (CFG-02) and Phase 4's "errors-as-list-not-raise" pattern (CITED: profile.py line 447 `validate_profile` returns `list[str]`). `_load_override_template` (templates.py line 713) already runs `validate_template` before promoting an override; Phase 31 piggy-backs on that path for free.

**Example:**
```python
# Source: graphify/templates.py:244–254 (existing pattern Phase 31 mirrors)
if user_text is not None:
    errors = validate_template(user_text, required)
    if errors:
        for err in errors:
            print(f"[graphify] template error: {note_type}.md — {err}", file=sys.stderr)
        templates[note_type] = _load_builtin_template(note_type)
    else:
        templates[note_type] = string.Template(user_text)  # Phase 31: → _BlockTemplate(user_text)
```

### Pattern 2: Two-Phase Substitution (Phase 31 = Three-Phase)

**What:** Render order in Phase 31 is:
1. **Block expansion** (NEW) — `{{#…}}` blocks → expanded literal text (with `${conn.label}` etc. spliced in).
2. **Inner substitution** (existing) — `_build_dataview_block` substitutes `${community_tag}`, `${folder}` into the user's Dataview query string (line 552).
3. **Outer substitution** (existing) — `template.safe_substitute(substitution_ctx)` fills `${frontmatter}`, `${label}`, `${dataview_block}`, etc.

**Why:** D-16 explicitly orders block parsing **before** scalar substitution to prevent label-injection. The two-phase pattern (Pattern 5 in Phase 02 RESEARCH, citation in templates.py line 527) is the single-pass-`string.Template` precedent.

**Example:**
```python
# Source: graphify/templates.py:552–555 (existing two-phase, Phase 31 wraps with block-expand)
query = string.Template(moc_query).safe_substitute(
    community_tag=safe_community_tag,
    folder=safe_folder,
)
# Phase 31 adds an outer block-expand layer BEFORE the outer safe_substitute call
```

### Pattern 3: Errors-as-List

`validate_template` returns `list[str]`; never raises (CITED: templates.py line 144 `errors: list[str] = []`). Phase 31's new error categories append to the same list:
- `"nested template blocks are not supported (found '{{#X}}' inside '{{#Y}}'). …"`
- `"unclosed template block: '{{#connections}}' has no matching '{{/connections}}'"`
- `"unknown predicate '{{#if_foo}}' — valid predicates are: ['if_god_node', 'if_isolated', 'if_has_connections', 'if_has_dataview']. Use {{#if_attr_foo}} for raw node-attribute access."`
- `"unknown connection field '${conn.foo}' — valid fields are: ['confidence', 'community', 'label', 'relation', 'source_file', 'target']"`

### Anti-Patterns to Avoid

- **Recursive regex for block parsing.** Python's `re` is non-recursive; balanced-block matching with regex either drops nesting detection (the wrong answer per D-07) or relies on PCRE features Python lacks. Use a finite-state line/character scan.
- **Importing networkx in `templates.py`.** Module docstring lines 2–9 forbid it. Predicates duck-type via `G.degree(node_id) == 0` style.
- **Reading node attributes inside `expand_blocks` without `node_id in G` guard.** `_build_connections_callout` already does this (line 393): `if node_id not in G: return ""`.
- **Sanitizing predicate-guarded scalars but not loop-iteration scalars** — both must pass through `_sanitize_wikilink_alias`.
- **Letting `safe_substitute` swallow typos like `${conn.lable}`.** `safe_substitute` silently leaves unmatched `${…}` in output (CITED: docs.python.org/3/library/string.html#string.Template.safe_substitute). The block expander MUST validate `conn.<field>` references at preflight.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wikilink alias sanitization | Custom strip for `{{`/`}}`/`#` | Reuse `_sanitize_wikilink_alias` (line 283) — already strips control chars, `]]`, `\|`, newlines | Composability + exhaustive coverage of Unicode line/paragraph separators (line 279) |
| Dataview-fence safety | Custom backtick handling | Reuse `_build_dataview_block`'s `query.replace("```", "")` (line 559) and `community_tag`/`folder` strip (line 549) | One audited site for fence-injection defense |
| Path confinement | Custom path checks for override templates | `validate_vault_path` is already used by `_load_override_template` (line 728) | Phase 31 adds *zero* new file-loading sites |
| YAML schema validation | Per-key custom validators | Append to `validate_profile` (line 447) following the `community_templates` precedent (lines 478–514) — same `errors.append(...)` pattern | Single output channel; integrates with `--validate-profile` for free |
| Provenance tracking | New tracking dict for `dataview_queries` | `_deep_merge_with_provenance` (line 194) already recurses into dict-of-scalar leaves and records dotted keys | `dataview_queries.thing` provenance falls out for free; only the formatter side may need a new section header |
| Edge enumeration | Manual `for u, v in G.edges(): if u == node_id or v == node_id` | `G.edges(node_id, data=True)` returns iterable of `(u, v, data)` already filtered to incident edges (CITED: networkx Graph.edges docstring; used at line 397) | Existing `_build_connections_callout` is the reference implementation |

**Key insight:** Phase 31 is a *composition* phase, not an *infrastructure* phase. Every primitive it needs already exists in templates.py / profile.py / analyze.py. The work is wiring, not building.

## Validation Architecture

> Required because `workflow.nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | `pyproject.toml` (no separate `pytest.ini`) |
| Quick run command | `pytest tests/test_templates.py tests/test_profile.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| TMPL-01 | `{{#if_god_node}}…{{/if}}` renders body when node is in `god_nodes(G)` | unit | `pytest tests/test_templates.py::test_block_if_god_node_true -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_god_node}}…{{/if}}` omits body when node is NOT a god node | unit | `pytest tests/test_templates.py::test_block_if_god_node_false -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_isolated}}…{{/if}}` true when `G.degree(node_id) == 0` | unit | `pytest tests/test_templates.py::test_block_if_isolated_true -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_isolated}}…{{/if}}` false when node has ≥1 edge | unit | `pytest tests/test_templates.py::test_block_if_isolated_false -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_has_connections}}` is truthy inverse of `if_isolated` | unit | `pytest tests/test_templates.py::test_block_if_has_connections_inverse -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_has_dataview}}` true iff rendered `${dataview_block}` non-empty | unit | `pytest tests/test_templates.py::test_block_if_has_dataview -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_attr_pinned}}` reads `G.nodes[id]["pinned"]` truthy | unit | `pytest tests/test_templates.py::test_block_if_attr_truthy -x` | ❌ Wave 0 |
| TMPL-01 | `{{#if_attr_pinned}}` falsy when attr missing or 0/""/None/False | unit | `pytest tests/test_templates.py::test_block_if_attr_falsy -x` | ❌ Wave 0 |
| TMPL-01 | Unknown predicate `{{#if_foobar}}` → `validate_template` error | unit | `pytest tests/test_templates.py::test_block_unknown_predicate_preflight -x` | ❌ Wave 0 |
| TMPL-02 | Loop with N=3 outgoing edges emits 3 expanded copies in deterministic order | unit | `pytest tests/test_templates.py::test_block_connections_n_iterations -x` | ❌ Wave 0 |
| TMPL-02 | Loop with 0 edges emits empty (header omitted via outer `{{#if_has_connections}}`) | unit | `pytest tests/test_templates.py::test_block_connections_empty -x` | ❌ Wave 0 |
| TMPL-02 | Both `${conn.label}` AND `${conn_label}` resolve to same value (parity) | unit | `pytest tests/test_templates.py::test_block_conn_dot_flat_parity -x` | ❌ Wave 0 |
| TMPL-02 | All six fields (`label`, `relation`, `target`, `confidence`, `community`, `source_file`) render correctly | unit | `pytest tests/test_templates.py::test_block_conn_all_fields -x` | ❌ Wave 0 |
| TMPL-02 | `conn.target` renders as node label, not raw id | unit | `pytest tests/test_templates.py::test_block_conn_target_is_label -x` | ❌ Wave 0 |
| TMPL-02 | `conn.confidence` renders as EXTRACTED/INFERRED/AMBIGUOUS string | unit | `pytest tests/test_templates.py::test_block_conn_confidence_string -x` | ❌ Wave 0 |
| TMPL-02 | Loop body sanitizes `]]`/`\|`/`\n`/control chars in labels | unit | `pytest tests/test_templates.py::test_block_conn_label_sanitization -x` | ❌ Wave 0 |
| TMPL-02 | Unknown `${conn.lable}` typo → `validate_template` error (not silent passthrough) | unit | `pytest tests/test_templates.py::test_block_conn_unknown_field_preflight -x` | ❌ Wave 0 |
| Nesting | Nested `{{#connections}}` inside `{{#connections}}` rejected with clear error | unit | `pytest tests/test_templates.py::test_block_nested_loop_rejected -x` | ❌ Wave 0 |
| Nesting | `{{#if}}` inside `{{#connections}}` rejected with clear error | unit | `pytest tests/test_templates.py::test_block_if_in_loop_rejected -x` | ❌ Wave 0 |
| Nesting | Nested `{{#if}}` inside `{{#if}}` rejected | unit | `pytest tests/test_templates.py::test_block_nested_if_rejected -x` | ❌ Wave 0 |
| Closure | Unclosed `{{#connections}}` rejected | unit | `pytest tests/test_templates.py::test_block_unclosed_loop_rejected -x` | ❌ Wave 0 |
| Closure | Mismatched closer `{{#if}}…{{/connections}}` rejected | unit | `pytest tests/test_templates.py::test_block_mismatched_closer_rejected -x` | ❌ Wave 0 |
| Sanitization | Node label containing literal `{{#connections}}` does NOT inject a fake loop after expansion | unit | `pytest tests/test_templates.py::test_block_label_injection_loop_smuggle -x` | ❌ Wave 0 |
| Sanitization | Node label containing `{{/if}}` does NOT close an outer guard | unit | `pytest tests/test_templates.py::test_block_label_injection_if_smuggle -x` | ❌ Wave 0 |
| Sanitization | `${` inside node label survives expansion as literal | unit | `pytest tests/test_templates.py::test_block_label_dollar_brace_literal -x` | ❌ Wave 0 |
| Back-compat | Template with no `{{#…}}` blocks renders byte-identical to today | unit | `pytest tests/test_templates.py::test_block_free_template_byte_identical -x` | ❌ Wave 0 |
| Back-compat | Existing `_render_moc_like` Dataview path unchanged when `dataview_queries` absent | unit | `pytest tests/test_templates.py::test_dataview_block_legacy_fallback_preserved -x` | ❌ Wave 0 |
| TMPL-03 | `dataview_queries.moc` overrides legacy `obsidian.dataview.moc_query` | unit | `pytest tests/test_templates.py::test_dataview_queries_moc_override -x` | ❌ Wave 0 |
| TMPL-03 | `dataview_queries.thing` renders into `${dataview_block}` for thing notes (when slot present in template) | unit | `pytest tests/test_templates.py::test_dataview_queries_thing_renders -x` | ❌ Wave 0 |
| TMPL-03 | `dataview_queries` per-key deep-merges across Phase 30 chain | unit | `pytest tests/test_profile.py::test_dataview_queries_extends_chain_merge -x` | ❌ Wave 0 |
| TMPL-03 | `dataview_queries` unknown key (e.g., `mocs:`) → `validate_profile` error | unit | `pytest tests/test_profile.py::test_dataview_queries_unknown_note_type_rejected -x` | ❌ Wave 0 |
| TMPL-03 | `dataview_queries` non-string value → `validate_profile` error | unit | `pytest tests/test_profile.py::test_dataview_queries_non_string_value_rejected -x` | ❌ Wave 0 |
| TMPL-03 | `dataview_queries` non-dict → `validate_profile` error | unit | `pytest tests/test_profile.py::test_dataview_queries_non_dict_rejected -x` | ❌ Wave 0 |
| TMPL-03 | `--validate-profile` provenance dump shows `dataview_queries.thing ← profile.yaml` | unit | `pytest tests/test_profile.py::test_validate_profile_dumps_dataview_queries_provenance -x` | ❌ Wave 0 |
| Backticks | TMPL-03 query containing literal triple-backtick is stripped before fence wrap | unit | `pytest tests/test_templates.py::test_dataview_queries_strips_triple_backtick -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_templates.py tests/test_profile.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] All ~30 new tests above land in `tests/test_templates.py` and `tests/test_profile.py` — both files exist (2330 + 1395 lines respectively); no new test files needed.
- [ ] Extend `tests/fixtures/template_context.py` with:
  - `make_isolated_node_graph()` — single-node graph for `if_isolated`
  - `make_god_node_graph()` — graph with one clear high-degree node + 4–5 connected satellites for `if_god_node`
  - `make_six_field_edge_graph()` — ensures every `conn.<field>` is non-empty
  - `make_label_injection_graph()` — labels containing `{{#connections}}`, `{{/if}}`, `${`, `]]`, `\|`
- [ ] Extend `tests/fixtures/profiles/` (already used by Phase 30 — see `linear_chain_valid` fixture per STATE.md "Plan 30-03") with `dataview_queries_*.yaml` fixtures for the Phase 30 chain-merge test.
- [ ] Framework install: none — pytest already in CI.

## Common Pitfalls

### Pitfall 1: `safe_substitute` swallows typos

**What goes wrong:** Author writes `${conn.lable}` (typo). `safe_substitute` silently leaves the literal text in the output — no error, no warning.

**Why it happens:** `safe_substitute` is documented to never raise on missing keys (CITED: docs.python.org/3/library/string.html#string.Template.safe_substitute). Phase 31's loop body is run through `safe_substitute`, so unknown fields disappear from validation otherwise.

**How to avoid:** `validate_template` must walk every `${conn.<field>}` occurrence inside any detected `{{#connections}}` block and validate `<field>` is in the locked field set `{label, relation, target, confidence, community, source_file}`. Also walk `${conn_<field>}` flattened form.

**Warning signs:** Output containing literal `${conn.something}` after rendering — means a typo escaped preflight.

### Pitfall 2: Block parsing AFTER scalar substitution

**What goes wrong:** A node label `"My weird {{#connections}}thing{{/connections}}"` would smuggle a fake loop into the output if scalar substitution ran first.

**Why it happens:** `string.Template.safe_substitute` substitutes scalars *into* a text body that subsequently gets parsed for blocks.

**How to avoid:** D-16 locks block-parse → scalar-substitute order. Concretely: `expand_blocks(template_text, ctx)` consumes the *raw* template text (which the author wrote and `validate_template` already vetted) and emits text where `{{#…}}` blocks have been replaced by sanitized literals. Only then does `safe_substitute(substitution_ctx)` run.

**Warning signs:** Test `test_block_label_injection_loop_smuggle` failing — directly catches this.

### Pitfall 3: `string.Template` subclass forgets to recompile `pattern`

**What goes wrong:** Subclass redefines `idpattern` but stale `pattern` regex still uses the parent's identifier rules. `${conn.label}` doesn't match the `braced` group.

**Why it happens:** `string.Template` compiles `pattern` once in `__init_subclass__` based on the subclass's class attributes. If `pattern` is set explicitly on the subclass without referencing the new `idpattern`, the override is dropped.

**How to avoid:** Override **only** `idpattern` (and inherit `delimiter`, `flags`). Do NOT override `pattern`. Verified in CPython 3.10/3.12 (CITED: github.com/python/cpython/blob/main/Lib/string.py — `__init_subclass__` recompiles when any of `delimiter|idpattern|braceidpattern|flags` is set on the subclass class body). Recommended one-liner:

```python
class _BlockTemplate(string.Template):
    idpattern = r"(?a:[_a-z][_a-z0-9]*(?:\.[_a-z][_a-z0-9]*)?)"
```

Backward-compat verification: bare names like `frontmatter`, `label` still match the optional `(?:\.…)?` clause as the no-dot branch — no existing template breaks.

**Warning signs:** `test_block_free_template_byte_identical` failing.

### Pitfall 4: `$conn.label` (no braces) parses as `$conn` then literal `.label`

**What goes wrong:** Per Python `string.Template` docs, the unbraced `$identifier` form stops at the first non-identifier character. So `$conn.label` substitutes `$conn` and leaves `.label` as literal text. Only `${conn.label}` (braced) actually uses the extended `idpattern`.

**Why it happens:** Default `string.Template.pattern` separates `named` (no braces, `$id`) from `braced` (`${id}`) groups; both use `idpattern` but `named` matching is greedy-stops at non-identifier.

**How to avoid:** **Document that authors MUST use the braced form `${conn.field}`** (or the flattened `${conn_field}` / `$conn_field`). The block expander emits *both* forms during pre-substitution, so authors who wrote `$conn_label` (legal Python identifier, no dot) are also covered by the `_BlockTemplate` parsing.

**Warning signs:** Loop body output contains literal `.label` text after first iteration.

### Pitfall 5: Confusing "god node" sources of truth

**What goes wrong:** `analyze.god_nodes(G, top_n=10)` returns a *ranked list* and *side-effects the graph* by setting `G.nodes[node_id]["possible_diagram_seed"] = True` (CITED: analyze.py line 92–94). It is NOT a free predicate.

**Why it happens:** `god_nodes` is degree-ranked AND has a side effect. Calling it from a predicate would mutate the graph during render. The `possible_diagram_seed` attribute is already set at analyze pipeline stage and cached on the graph.

**How to avoid:** The `if_god_node` predicate should test `bool(G.nodes[node_id].get("possible_diagram_seed"))` — read the attribute already set during the analyze pipeline. Do NOT call `god_nodes()` from inside the predicate. If the attribute is absent (caller skipped analyze), the predicate returns False (graceful).

**Warning signs:** Render-time mutations to `G.nodes` from a "read-only" template render.

### Pitfall 6: `if_isolated` source — predicate vs. analyze.py heuristic

**What goes wrong:** `analyze.knowledge_gaps` (line 641, plus the snippet at line ~482 of analyze.py) defines isolation as `G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n)` — i.e., "weakly connected + not a file + not a concept node." A naive `if_isolated` predicate that just checks `G.degree(n) == 0` will diverge from analyze's own definition.

**Why it happens:** Two different definitions of "isolated" exist in the codebase.

**How to avoid:** **Choose explicitly.** CONTEXT.md D-02 says "node has no edges in the graph" — that is `G.degree(node_id) == 0`. Document that this is *strictly* an edge-count check, not analyze.py's "weakly-connected non-file non-concept" gap heuristic. Add a comment in templates.py at the predicate site referencing analyze.py line ~482 to flag the divergence.

**Warning signs:** Confusion between "isolated for the user" (no edges to anything) and "knowledge gap" (analyze.py's richer heuristic). Plan should pick the simpler one (degree==0) per D-02.

### Pitfall 7: TMPL-03 vs. existing `${dataview_block}` slot scope

**What goes wrong:** Today only `moc.md` and `community.md` builtin templates contain a `${dataview_block}` placeholder (verified via direct read of `graphify/builtin_templates/thing.md` — it has only `${frontmatter}`, `${label}`, `${wayfinder_callout}`, `${body}`, `${connections_callout}`, `${metadata_callout}`). `${dataview_block}` is not in `_REQUIRED_PER_TYPE["thing"]` (line 179 — only `{frontmatter, label}`).

**Why it happens:** Phase 02 deliberately scoped Dataview blocks to MOC/community notes only.

**How to avoid:**
- TMPL-03's profile schema accepts `dataview_queries.<note_type>` for ALL six note types (D-12).
- The **builtin templates do not change** in Phase 31. Things/Statements/People/Sources have no `${dataview_block}` slot, so a profile setting `dataview_queries.thing: …` is *latent* — it only surfaces if the user *also* customizes their `thing.md` template to include `${dataview_block}`.
- `_build_dataview_block` is invoked unconditionally for MOC/community in `_render_moc_like` (line 880). For non-MOC notes (`render_note`, line 689), `dataview_block` is currently stuffed with `""`. Phase 31 must conditionally compute the value when `profile["dataview_queries"].get(note_type)` exists, AND pass it into `substitution_ctx["dataview_block"]`. If the user's template doesn't reference the var, `safe_substitute` leaves it as a no-op (per existing behavior).

**Warning signs:** Test `test_dataview_queries_thing_renders` failing because `render_note` always sets `dataview_block=""`. Plan 02 must explicitly extend `render_note`'s `substitution_ctx` to honor TMPL-03 for non-MOC types.

### Pitfall 8: Phase 30 community template + TMPL-01 conditionals interaction

**What goes wrong:** `_pick_community_template` (line 760) picks an override template based on community ID/label match. The override template can contain its own `{{#…}}` blocks. The block expander must run on whichever template ultimately renders, not on the default.

**Why it happens:** The override-vs-default decision happens *after* validation in `_load_override_template` (line 749 — already validates the override, so block syntax in overrides is preflight-checked there).

**How to avoid:** `_load_override_template` (line 713) already calls `validate_template(text, _REQUIRED_PER_TYPE["moc"])` before returning the override. Phase 31 extends `validate_template` to also validate block syntax — overrides get block validation for free. At render time, `expand_blocks` is invoked on whichever `template` was selected by `_pick_community_template`, not on the default. No new code needed beyond making sure `expand_blocks` lives in the call path between `_pick_community_template(...)` returning and `template.safe_substitute(substitution_ctx)` running.

**Warning signs:** Test like `test_community_template_override_with_if_block_renders` covers this composition.

## Code Examples

### `_BlockTemplate` subclass

```python
# Source: graphify/templates.py (NEW — Plan 01)
import string

class _BlockTemplate(string.Template):
    """string.Template subclass with a one-segment dot-extended idpattern.

    Accepts both bare identifiers (``frontmatter``, ``label``) and one
    optional dotted segment (``conn.label``, ``conn.confidence``).
    Backward-compatible: every existing builtin/user template parses
    identically because the dotted clause is optional.

    Note: Python ``string.Template`` recompiles ``pattern`` automatically
    when a subclass overrides ``idpattern``. Do not override ``pattern``
    directly — the parent's __init_subclass__ does the work (verified on
    CPython 3.10 + 3.12).
    """
    idpattern = r"(?a:[_a-z][_a-z0-9]*(?:\.[_a-z][_a-z0-9]*)?)"
```

### Predicate catalog

```python
# Source: graphify/templates.py (NEW — Plan 01)
# Module-level dict; keys keep the user-facing if_ prefix for symmetry
# with the syntax (validate_template's error message can echo keys()
# verbatim).

# Forward reference: BlockContext is a small dataclass / TypedDict carrying
# G, node_id, profile, note_type, dataview_block_value (precomputed scalar).

def _pred_god_node(ctx) -> bool:
    # Read the cached attribute set by analyze.god_nodes (analyze.py line 92).
    # Returns False gracefully if the analyze pipeline didn't run.
    return bool(ctx.G.nodes[ctx.node_id].get("possible_diagram_seed"))

def _pred_isolated(ctx) -> bool:
    # Strict edge-count definition per CONTEXT D-02 — distinct from
    # analyze.knowledge_gaps' "weakly-connected" heuristic (analyze.py L482).
    return ctx.G.degree(ctx.node_id) == 0

def _pred_has_connections(ctx) -> bool:
    return ctx.G.degree(ctx.node_id) > 0

def _pred_has_dataview(ctx) -> bool:
    return bool(ctx.dataview_block_value)

_PREDICATE_CATALOG: dict = {
    "if_god_node": _pred_god_node,
    "if_isolated": _pred_isolated,
    "if_has_connections": _pred_has_connections,
    "if_has_dataview": _pred_has_dataview,
}
```

### `if_attr_<name>` extraction

```python
# Source: graphify/templates.py (NEW — Plan 01)
import re

# Regex used in BOTH validate_template and expand_blocks to detect the
# escape-hatch syntax. Anchored on `if_attr_` to ensure no collision
# with the catalog (catalog keys must NOT start with "if_attr_").
_IF_ATTR_RE = re.compile(r"^if_attr_([a-z_][a-z0-9_]*)$", re.IGNORECASE)

def _eval_predicate(name: str, ctx) -> bool:
    """Evaluate a predicate name. Caller has already validated via validate_template."""
    if name in _PREDICATE_CATALOG:
        return _PREDICATE_CATALOG[name](ctx)
    m = _IF_ATTR_RE.match(name)
    if m:
        attr = m.group(1)
        return bool(ctx.G.nodes[ctx.node_id].get(attr))
    # Defensive: should have been caught at preflight (D-09/D-10).
    raise AssertionError(f"unreachable: unknown predicate {name!r}")
```

**Disjointness:** `_PREDICATE_CATALOG` keys (`if_god_node`, `if_isolated`, `if_has_connections`, `if_has_dataview`) all match `_IF_ATTR_RE` strictly negatively (none start with `if_attr_`). Confirmed disjoint. The dispatch order in `_eval_predicate` is "catalog wins on collision" but no collision is possible by design.

### Connection iteration source

```python
# Source: graphify/templates.py (NEW — Plan 01); mirrors L397
def _iter_connections(G, node_id, convention) -> list[dict]:
    """Enumerate connections for {{#connections}} loop expansion.

    Source-of-truth: G.edges(node_id, data=True) — same call as
    _build_connections_callout (L397). For nx.Graph (undirected, our
    only graph type — verified in build.py), this yields ALL incident
    edges. For deterministic order, sort by (relation, target_label)
    so re-runs are reproducible.

    Returns list of dicts with all six locked fields populated. Labels
    pre-sanitized via _sanitize_wikilink_alias to defeat injection
    via {{}} / # / ]] / | / newlines in node labels.
    """
    if node_id not in G:
        return []
    rows: list[dict] = []
    for u, v, data in G.edges(node_id, data=True):
        target = v if u == node_id else u
        target_label = G.nodes[target].get("label", target)
        relation = str(data.get("relation", "related")).replace("\n", " ").replace("\r", " ").replace("]", "")
        confidence = str(data.get("confidence", "AMBIGUOUS")).replace("\n", " ").replace("\r", " ").replace("]", "")
        community = G.nodes[target].get("community")
        source_file = data.get("source_file") or G.nodes[target].get("source_file") or ""
        # source_file may be list[str] post-Phase-23 dedup (STATE.md note);
        # flatten to first entry for template display.
        if isinstance(source_file, list):
            source_file = source_file[0] if source_file else ""
        rows.append({
            "label": _sanitize_wikilink_alias(str(target_label)),
            "relation": relation,
            "target": _sanitize_wikilink_alias(str(target_label)),  # display label, NOT raw id (D-06)
            "confidence": confidence,
            "community": str(community) if community is not None else "",
            "source_file": str(source_file).replace("\n", " ").replace("\r", " "),
        })
    rows.sort(key=lambda r: (r["relation"], r["label"]))
    return rows
```

### Block expander entry point (signature)

```python
# Source: graphify/templates.py (NEW — Plan 01)
from dataclasses import dataclass

@dataclass(frozen=True)
class BlockContext:
    G: object  # networkx Graph (duck-typed; templates.py never imports networkx)
    node_id: str
    profile: dict
    note_type: str
    convention: str
    dataview_block_value: str  # precomputed scalar (may be "")

def expand_blocks(template_text: str, ctx: BlockContext) -> str:
    """Replace every {{#NAME}}…{{/NAME}} block with rendered text.

    Assumes input is preflight-valid (validate_template was called). Walks
    the text once, finite-state, identifying block start/end markers and
    splicing rendered output. Inside loop bodies, emits BOTH ${conn.<field>}
    (consumed by _BlockTemplate's extended idpattern) and ${conn_<field>}
    (consumed by stock string.Template) so downstream substitution works
    in either configuration.
    """
    # ... finite-state implementation ...
```

### TMPL-03 integration in `_build_dataview_block`

```python
# Source: graphify/templates.py:524 (EXTEND — Plan 02)
def _build_dataview_block(
    profile: dict,
    community_tag: str,
    folder: str,
    note_type: str = "moc",   # NEW parameter (default keeps existing call sites working)
) -> str:
    # NEW: per-note-type lookup wins over legacy obsidian.dataview.moc_query
    per_type = (profile.get("dataview_queries") or {}).get(note_type)
    if isinstance(per_type, str) and per_type:
        moc_query = per_type
    else:
        moc_query = (
            profile.get("obsidian", {})
            .get("dataview", {})
            .get("moc_query")
        ) or _FALLBACK_MOC_QUERY
    # ... existing two-phase substitution (L549–562) unchanged ...
```

### `validate_profile` extension

```python
# Source: graphify/profile.py:447 (EXTEND — Plan 02)
# Append after the community_templates block (lines 478–514):

dvq = profile.get("dataview_queries")
if dvq is not None:
    if not isinstance(dvq, dict):
        errors.append("'dataview_queries' must be a mapping (dict)")
    else:
        # Mirror templates.py _NOTE_TYPES (line 48). Imported lazily
        # to avoid templates.py → profile.py cycle.
        _KNOWN_NOTE_TYPES = {"moc", "community", "thing", "statement", "person", "source"}
        for nt, qs in dvq.items():
            if nt not in _KNOWN_NOTE_TYPES:
                errors.append(
                    f"dataview_queries.{nt}: unknown note type — "
                    f"valid types are: {sorted(_KNOWN_NOTE_TYPES)}"
                )
            elif not isinstance(qs, str) or not qs:
                errors.append(
                    f"dataview_queries.{nt} must be a non-empty string "
                    f"(got {type(qs).__name__})"
                )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `string.Template.safe_substitute` only | Block-expand pre-pass + `_BlockTemplate` subclass + `safe_substitute` | Phase 31 | Adds conditionals + loops without leaving stdlib |
| Hardcoded `obsidian.dataview.moc_query` for MOC notes only | Per-note-type `dataview_queries.<note_type>` with `moc_query` legacy fallback | Phase 31 | Six independent Dataview block contents; Phase 30 chain composition for free |
| Block syntax disallowed entirely | Single-level `{{#…}}` blocks; nested rejected with clear preflight error | Phase 31 | Real authoring power, no template-engine sprawl |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python `string.Template` `__init_subclass__` recompiles `pattern` from new `idpattern` automatically | §Pitfall 3, §Code Examples (`_BlockTemplate`) | If wrong, Plan 01 must override `pattern` explicitly. Verified by reading docs.python.org as recently as the live `python3` shell run during research (returned `(?a:[_a-z][_a-z0-9]*)` for the default idpattern). [VERIFIED: live python3 -c on 2026-04-28] |
| A2 | `if_god_node` predicate sources truth from cached `G.nodes[id]["possible_diagram_seed"]` set by `analyze.god_nodes` (line 92–94) | §3 Predicate eval, §Pitfall 5 | If the Phase 31 user runs templates outside the analyze pipeline, predicate returns False — graceful but documented assumption. [VERIFIED: analyze.py:92–94 read] |
| A3 | `if_isolated` is "G.degree(id) == 0" — NOT analyze.py's "weakly-connected non-file non-concept" heuristic (line ~482) | §Pitfall 6, §Code Examples | If user expects analyze.py semantics, predicate result diverges. Doc comment in templates.py mitigates. [CITED: 31-CONTEXT.md D-02 "node has no edges"] |
| A4 | `dataview_queries` does NOT auto-extend non-MOC builtin templates with a new `${dataview_block}` slot | §Pitfall 7, §7 TMPL-03 | If user expects thing.md to render Dataview automatically, they get nothing. Doc + test coverage explicit. [VERIFIED: read of `graphify/builtin_templates/thing.md`] |
| A5 | `_deep_merge_with_provenance` already records `dataview_queries.<note_type>` leaves correctly without modification | §Component Responsibilities, §8 validate_profile | Provenance dump might miss dataview_queries — minor docs/UX risk only. [VERIFIED: profile.py:194–217 read, recursion is over any dict-of-scalar] |
| A6 | Phase 30 Plan 03 `--validate-profile` text output formatter handles new dotted keys gracefully | §Component Responsibilities | Formatter may need a tiny extension to call out a `dataview_queries` section. Plan 02 should add a confirmation test. [ASSUMED based on STATE.md "Plan 30-03: Extend --validate-profile output: Merge chain + Field provenance + Resolved community templates sections" — provenance is generic dotted-key, but unverified for new top-level key inclusion] |
| A7 | The "deferred" idea of `community_templates.<rule>.dataview_query` does NOT need a Phase 31 hook | §10 Plan decomposition | If users immediately request community-specific Dataview, Phase 32 can extend `community_templates` schema. CONTEXT.md `<deferred>` explicitly defers it. [CITED: 31-CONTEXT.md `<deferred>` first bullet] |

## Open Questions

1. **Should `_BlockTemplate` *replace* stock `string.Template` everywhere, or only when block syntax is detected?**
   - What we know: D-05 specifies the parallel-flattened `${conn_<field>}` form precisely so stock `string.Template` keeps working downstream.
   - What's unclear: Cleaner code might be "always use `_BlockTemplate`" (its idpattern is a strict superset). Performance impact is nil (compiled regex is a one-time cost per template instance).
   - Recommendation: **Always use `_BlockTemplate`.** The dotted clause is optional; back-compat is guaranteed by construction. Drop the `if block syntax detected: wrap in _BlockTemplate else string.Template` branching for simplicity. The flattened `${conn_<field>}` parallel form remains, *not* because it's needed by stock `Template` (we won't be using it), but because some user-authored templates may already include un-dotted forms.

2. **Should the predicate catalog be a single dict, or four module-level functions registered in a dict?**
   - Recommendation: a single dict (see §Code Examples) — testable, introspectable, ships error messages directly via `sorted(_PREDICATE_CATALOG.keys())`.

3. **Loop iteration determinism — sort by what?**
   - Recommendation: sort by `(relation, label)` ascending. Reproducible across re-runs. Communities and confidence are NOT sort keys (would scramble logical groupings). Document this in the planner's task acceptance criteria.

4. **Does `--validate-profile` need a new `Resolved Dataview Queries` section, or is the existing "Field provenance" dump enough for D-14?**
   - Recommendation: existing dump suffices because dotted keys `dataview_queries.thing` etc. appear naturally. Plan 02 should include a test confirming this and add a one-line section header in the output formatter only if visual scanning is awkward — small UX polish, not a correctness gate.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.10+ (CI: 3.10, 3.12) | — |
| pytest | Test execution | ✓ | already in repo | — |
| PyYAML | Profile parsing in tests for TMPL-03 | ✓ (optional `[obsidian]`) | already declared | If absent, `validate_profile_preflight` short-circuits with a clear "PyYAML not installed" error (profile.py:1037–1043) — tests must mark accordingly |
| NetworkX | Test fixtures (`make_*_graph`) | ✓ | already required | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Plan Decomposition Recommendation

**Recommended split: 2 plans, NOT 3.**

### Plan 31-01: Block Engine — TMPL-01 + TMPL-02 + Sanitization Hardening
**Scope:**
- `_BlockTemplate(string.Template)` subclass with extended `idpattern`.
- `_PREDICATE_CATALOG` (4 entries) + `_eval_predicate` + `_IF_ATTR_RE`.
- `expand_blocks(template_text, ctx)` finite-state pass.
- Extend `validate_template` (templates.py:133) to detect blocks, validate nesting (rejected), unclosed (rejected), unknown predicates (rejected), unknown `conn.<field>` references (rejected).
- Wire `expand_blocks` into `render_note` (line 569), `_render_moc_like` (line 797), `render_moc` (line 916), `render_community_overview` (line 937) — all four entry points.
- `load_templates` (line 207) and `_load_override_template` (line 713) wrap loaded user templates with `_BlockTemplate` (always — see Open Question 1).
- Sanitization tests covering label-injection of `{{`/`}}`/`#`/`${`/`]]`/`|`/control chars in loop bodies.
- Backward-compat regression: every block-free template renders byte-identical via golden-file comparison fixture.

**Test coverage:** ~22 new tests (see Validation Architecture table — TMPL-01 + TMPL-02 + Nesting + Closure + Sanitization + Back-compat rows). All in `tests/test_templates.py`.

**File touch count:** 1 prod file (`graphify/templates.py`) + 1 fixture file (`tests/fixtures/template_context.py`) + 1 test file (`tests/test_templates.py`).

**Risk:** Largest plan. ~250 LoC of net new code. Block parser is the algorithmic centerpiece — needs careful state-machine review.

### Plan 31-02: Per-Note-Type Dataview Queries — TMPL-03 + Provenance
**Scope:**
- Add `"dataview_queries"` to `_VALID_TOP_LEVEL_KEYS` (profile.py:130).
- Extend `validate_profile` (profile.py:447) — type-check, key-restriction to `_KNOWN_NOTE_TYPES`, value-non-empty-string check.
- Extend `_build_dataview_block` (templates.py:524) — accept `note_type`, look up `profile["dataview_queries"][note_type]` first, fall back to legacy.
- Wire `note_type=template_key` in `_render_moc_like` (line 880) where `_build_dataview_block` is invoked.
- For non-MOC `render_note`: conditionally compute `dataview_block` value when `profile["dataview_queries"].get(note_type)` exists, populate `substitution_ctx["dataview_block"]` (line 688). Builtin templates won't render it (no slot); user templates with `${dataview_block}` slot will.
- Confirm Phase 30 `_deep_merge_with_provenance` records `dataview_queries.thing` etc. correctly (single test in `test_profile.py`).
- Confirm `--validate-profile` output formatter (Phase 30 Plan 03) surfaces the dotted keys (single test in `test_profile.py`).

**Test coverage:** ~8 new tests (TMPL-03 rows in Validation Architecture table). 4 in `test_templates.py`, 4 in `test_profile.py`.

**File touch count:** 2 prod files (`graphify/profile.py`, `graphify/templates.py`) + 2 test files.

**Risk:** Lower. Reuses Phase 30 provenance machinery wholesale. Main subtlety: extending `render_note`'s `substitution_ctx` without breaking the "non-MOC notes have no Dataview today" invariant for users who haven't customized their templates.

### Why NOT 3 plans

Splitting sanitization into its own plan duplicates fixture setup (label-injection graphs are needed by every block-related test) and forces hand-off of the block-parser surface mid-plan. Folding sanitization into Plan 01 keeps the block engine tested *as one cohesive unit* — exactly Phase 31's success criterion 4.

### Wave order

```
Wave 1: Plan 31-01 (block engine) ─┐
                                   ├── No serial dependency: Plan 02
Wave 1: Plan 31-02 (TMPL-03)    ───┘   doesn't touch the block parser
                                       and Plan 01 doesn't touch profile.py
                                       schema. Both can land in parallel.
Wave 2: Phase verification (/gsd-verify-work)
```

The plans are **fully parallel** — Plan 31-02 only edits `_build_dataview_block` and `_render_moc_like`'s call site; Plan 31-01 doesn't touch either. Both can ship in the same wave.

## Risks / Landmines for the Planner

1. **`safe_substitute` typo silence (Pitfall 1).** `validate_template` MUST validate every `${conn.<field>}` against the locked field set, or typos slip through to render output. Test `test_block_conn_unknown_field_preflight` enforces this.

2. **Non-MOC `${dataview_block}` slot (Pitfall 7).** TMPL-03 expands the *schema* to all six note types but the *builtin templates* still only have a `${dataview_block}` slot in moc/community. Plan 31-02 must NOT silently expand non-MOC builtin templates — that would be a backward-compat break.

3. **`possible_diagram_seed` attribute coupling (Pitfall 5).** `if_god_node` predicate depends on the analyze pipeline having run. If a downstream caller of `render_note` skips analyze, the predicate is False — needs to be documented prominently in the predicate's docstring.

4. **`_render_moc_like` is on the hot path for Phase 30 community-template overrides (Pitfall 8).** Block expansion must happen *between* `_pick_community_template` and `template.safe_substitute`, not before either. The override template's blocks must be expanded against the same `BlockContext` as the default would have been.

5. **Phase 30 Plan 03 formatter assumption (A6).** Provenance is recorded automatically for new dotted keys, BUT the `--validate-profile` text formatter from Phase 30 may not visually call out a "Dataview Queries" subsection. Worst case: dotted keys are buried in the alphabetical provenance dump. Plan 02 should include a small UX test confirming the dump is grep-able.

6. **`source_file` may be `list[str]` for `conn.source_file`.** Phase 23 fixed dedup so `source_file` post-merge can be a list (STATE.md "Phase 23: Dedup `source_file` List-Handling Fix"). The connection-iteration helper (§Code Examples) flattens to first element — document this in the planner's acceptance criteria so a test exercises it.

7. **`fnmatch` is already imported in templates.py.** Don't accidentally re-import or shadow.

8. **Module import cycle.** `templates.py` imports from `graphify.profile` (line 22). `profile.py` extension for `_KNOWN_NOTE_TYPES` should NOT import from `templates.py` — duplicate the small frozenset locally inside `validate_profile` (see §Code Examples), which is exactly the pattern Phase 30 used for `_REQUIRED_PER_TYPE` (`profile.py:1052` does function-local import to break the cycle).

## Test Fixtures Needed

### NetworkX graph fixtures (extend `tests/fixtures/template_context.py`)

```python
def make_god_node_graph() -> nx.Graph:
    """Graph where 'n_hub' is clearly the highest-degree real entity.

    n_hub: label="Hub", degree=5, file_type="code"
    n_a..n_e: label="A".."E", degree=1, all connected to n_hub
    Pre-mark n_hub with possible_diagram_seed=True (mimics analyze.god_nodes).
    """

def make_isolated_node_graph() -> nx.Graph:
    """Graph with one node and zero edges (G.degree('n_lonely') == 0)."""

def make_six_field_edge_graph() -> nx.Graph:
    """Two nodes, one edge. Edge has all six locked fields populated:
    label, relation, target, confidence (EXTRACTED), community, source_file.
    Used to test conn.* field rendering."""

def make_label_injection_graph() -> nx.Graph:
    """Three nodes, edges between each pair. Labels include adversarial
    strings: '{{#connections}}', '{{/if}}', '${conn.label}', ']]', '|',
    '\n', tab, control chars. Used to test sanitization."""
```

### Profile fixtures (extend `tests/fixtures/profiles/`)

```yaml
# dataview_queries_minimal.yaml
dataview_queries:
  moc: "TABLE FROM #${community_tag}"

# dataview_queries_all_types.yaml
dataview_queries:
  moc: "TABLE FROM #${community_tag}"
  thing: "LIST FROM #${community_tag} WHERE type = \"thing\""
  statement: "LIST FROM #${community_tag} WHERE type = \"statement\""
  person: "LIST FROM #${community_tag} WHERE type = \"person\""
  source: "LIST FROM #${community_tag} WHERE type = \"source\""
  community: "TABLE FROM #${community_tag}"

# dataview_queries_unknown_key.yaml (failure fixture)
dataview_queries:
  mocs: "..."  # typo — validate_profile must reject

# dataview_queries_chain_base.yaml + dataview_queries_chain_child.yaml
# Pair of fragments demonstrating per-key deep-merge with extends:
# child's value wins for overlapping keys; base's contributes non-overlapping
```

### Template fixtures (inline strings or `tests/fixtures/templates/` files)

```markdown
# block_if_god_node.md
${frontmatter}
# ${label}
{{#if_god_node}}
> [!note] God Node
> This is a high-connectivity hub.
{{/if}}
${connections_callout}
${metadata_callout}

# block_connections_loop.md
${frontmatter}
# ${label}
{{#connections}}
- ${conn.relation} → [[${conn.target}]] [${conn.confidence}]
{{/connections}}
${metadata_callout}

# block_nested_rejected.md  (must fail validate_template)
{{#connections}}
{{#if_god_node}}
- ${conn.label}
{{/if}}
{{/connections}}

# block_unknown_predicate.md (must fail validate_template)
{{#if_made_up}}stuff{{/if}}

# block_unknown_conn_field.md (must fail validate_template)
{{#connections}}- ${conn.lable}{{/connections}}
```

## Sources

### Primary (HIGH confidence)
- `.planning/phases/31-template-engine-extensions/31-CONTEXT.md` — every D-01..D-16 decision read verbatim.
- `graphify/templates.py` (957 lines, full file read 2026-04-28) — `validate_template` at L133, `load_templates` at L207, `_sanitize_wikilink_alias` at L283, `_build_connections_callout` at L387, `_build_dataview_block` at L524, `render_note` at L569, `_render_moc_like` at L797, `_pick_community_template` at L760, `_load_override_template` at L713.
- `graphify/profile.py` lines 100–230 + 440–600 + 975–1155 — `_VALID_TOP_LEVEL_KEYS` at L130, `_deep_merge` at L183, `_deep_merge_with_provenance` at L194, `validate_profile` at L447, `validate_profile_preflight` at L980, `PreflightResult` at L14.
- `graphify/analyze.py` — `god_nodes` at L76 with side-effect at L92 (`possible_diagram_seed`), `_is_concept_node` at L139, knowledge-gap isolated detection at L482.
- `graphify/builtin_templates/thing.md` and `moc.md` — direct read confirming non-MOC builtins lack `${dataview_block}` slot.
- Live `python3 -c "import string; print(string.Template.idpattern)"` — verified `(?a:[_a-z][_a-z0-9]*)` on Py 3.12, 2026-04-28.
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` §"Phase 31", `.planning/STATE.md` — phase ID mapping, success criteria, prior-phase decisions.
- `.planning/phases/30-profile-composition/30-CONTEXT.md` — `_deep_merge_with_provenance` precedent, `_VALID_TOP_LEVEL_KEYS` extension precedent (`community_templates`), graceful-fallback contract.

### Secondary (MEDIUM confidence)
- docs.python.org/3/library/string.html#string.Template (cited for `safe_substitute` no-raise behavior, `idpattern` subclass override semantics).
- `tests/test_templates.py` (2330 lines) and `tests/test_profile.py` (1395 lines) — existing test patterns surveyed via `grep -n "^def test_"`. Confirms pure-unit-test style with `tmp_path`, `capsys`, no network.
- `tests/fixtures/template_context.py` — existing fixture builder pattern (`make_classification_context`, `make_min_graph`).

### Tertiary (LOW confidence)
- A6 (Phase 30 Plan 03 formatter) — assumed graceful with new dotted keys; planner should add a single confirmation test rather than trust the assumption.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all primitives already in repo, all line numbers verified by direct read.
- Architecture: HIGH — every render entry point, every helper line cited.
- Pitfalls: HIGH — Pitfalls 1, 3, 7 verified against source; Pitfalls 5, 6, 8 cite specific divergences in the codebase.
- TMPL-03 schema: HIGH — full mirror of Phase 30 `community_templates` precedent.
- A6 (Phase 30 formatter behavior): MEDIUM — assumption flagged; mitigation is one extra test.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable surface — `string.Template` semantics are stdlib, in-repo line numbers stable absent intervening commits to templates.py / profile.py).
