# Template block engine reference

Block engine added in Phase 31 (TMPL-01/TMPL-02). Extends graphify's `${placeholder}` substitution with conditional sections and per-edge loops. Applies to `.graphify/templates/*.md` override files and the built-in templates in `graphify/builtin_templates/`.

Pattern follows `docs/RELATIONS.md`: terse reference. Each section: what / when / example / pitfall.

Profile-level template overrides (per-mapping-rule, per-community, per-note-type) and the precedence ladder that resolves between them are documented in [`docs/PROFILE-CONFIGURATION.md`](PROFILE-CONFIGURATION.md) (Phase 56 additions). This document scopes to the block engine; override resolution lives in the profile composition layer.

---

## Conditional blocks

**What:** `{{#if_<name>}}…{{/if}}` renders its body only when the named predicate is `True` for the current node. Body is elided entirely (no blank line) when `False`.

**When:** Use to show sections only relevant to certain node types or graph positions — e.g. a "hub note" callout only on god nodes.

**Predicates (built-in):**

| Predicate | Fires when… |
|-----------|-------------|
| `if_god_node` | Node is a god node (top-degree hub) |
| `if_isolated` | Node has no edges |
| `if_has_connections` | Node has ≥1 edge |
| `if_has_dataview` | The rendered Dataview block is non-empty |

**Attribute escape hatch:** `{{#if_attr_<name>}}…{{/if}}` fires when `node.get("<name>")` is truthy. No profile declaration needed.

**Note-type predicates:** `{{#if_note_type_<X>}}…{{/if}}` fires when the render context's `note_type` equals `<X>`. Known types: `thing`, `statement`, `person`, `source`, `code`, `moc`.

<!-- test:conditional-blocks -->
```markdown
{{#if_god_node}}
> [!hub] Hub note — highly connected
{{/if}}

{{#if_attr_published}}
**Published**
{{/if}}

{{#if_note_type_thing}}
${label}
{{/if}}
```

**Pitfall:** Nesting `{{#…}}` inside another block is a validation error. Pre-compute complex conditions via `if_attr_*` or `if_flag_*` and set the attribute before rendering.

---

## Connection loops

**What:** `{{#connections}}…{{/connections}}` repeats the body once per outgoing edge, in `(relation ASC, label ASC)` sort order. Inside the loop, use `${conn.<field>}` substitutions.

**When:** Use in connection callouts or Dataview-adjacent tables to list every linked note.

**Available fields (`${conn.<field>}`):**

| Field | Source |
|-------|--------|
| `conn.label` | Target node `label` attribute |
| `conn.relation` | Edge `relation` key |
| `conn.target` | Same as `conn.label` (alias) |
| `conn.confidence` | Edge `confidence` value |
| `conn.community` | Target node `community` attribute |
| `conn.source_file` | Edge `source_file` key |

Both dot-form `${conn.label}` and flat-form `${conn_label}` are accepted (D-05).

**Sort:** `(relation ASC, label ASC)` — deterministic across runs.

<!-- test:connection-loops -->
```markdown
{{#connections}}
- [[${conn.label}]] — ${conn.relation} (${conn.confidence})
{{/connections}}
```

**Pitfall:** `${conn.community}` is empty unless the target node carries a `community` attribute — set this before rendering (e.g. after `cluster()`).

---

## Ordering invariant

**What:** Block expansion (`{{#…}}…{{/…}}`) runs *before* `${placeholder}` substitution. This is the D-16 ordering invariant.

**When:** Always applies. You cannot use `${label}` inside a block opener — the opener is matched by a regex before any `${}` values are resolved.

**Why it matters:** A node whose `label` contains `{{`, `}}`, or `${}` cannot inject block syntax into the template. The sanitization layer strips control characters from labels before substitution, but even without stripping, expansion happens first so the label value never reaches the block parser.

<!-- test:ordering-invariant -->
```markdown
{{#if_has_connections}}
${label} has connections.
{{/if}}
```

**Pitfall:** Do not attempt `{{#if_${label}}}` — the opener is matched before `${}` expansion, so `${label}` inside `{{#…}}` is a literal string, not a substitution site. `validate_template` rejects the opener name as unknown.

---

## Sanitization

**What:** Node labels and edge fields flowing into templates are HTML-escaped and control-char stripped before substitution (T-31-01 contract). This applies to all `${label}`, `${conn.*}` sinks.

**When:** Every render path. Sanitization is applied by `_build_edge_records` (for connection loop fields) and by the caller before passing values to `string.Template.safe_substitute`.

**T-31-01 contract:** `<`, `>`, `"`, `'`, and `&` are HTML-escaped in label and wikilink-alias values. Control characters (U+0000–U+001F) are stripped. Length is capped at 256 characters.

<!-- test:sanitization -->
```markdown
{{#if_has_connections}}
${label}
{{/if}}
```

**Pitfall:** `${conn.source_file}` carries the raw path string from edge data, not a wikilink. Do not embed it as a wikilink target without additional sanitization.

---

## Predicate catalog

**What:** The built-in predicate catalog maps predicate names to evaluator functions. Validated at preflight via `validate_template`; render path never re-validates.

**When:** Reference when writing templates or adding `predicate_flags` in `profile.yaml`.

| Predicate | Evaluator | Notes |
|-----------|-----------|-------|
| `if_god_node` | `_pred_god_node` | Checks `is_god_node` attr or `graph.graph["god_nodes"]` list |
| `if_isolated` | `_pred_isolated` | `graph.degree(node_id) == 0` |
| `if_has_connections` | `_pred_has_connections` | `graph.degree(node_id) > 0` |
| `if_has_dataview` | `_pred_has_dataview` | `ctx.dataview_nonempty` flag |
| `if_attr_<name>` | attr escape hatch | `bool(node.get("<name>"))` — no catalog entry needed |
| `if_note_type_<X>` | note-type family | `ctx.note_type == "<X>"` — X must be a known type |
| `if_flag_<X>` | user-defined | Dispatched via `ctx.flag_predicates[X]` |

<!-- test:predicate-catalog -->
```markdown
{{#if_god_node}}
> [!caution] Hub node — review connections
{{/if}}

{{#if_has_connections}}
${connections_callout}
{{/if}}

{{#if_isolated}}
> [!warning] No connections found
{{/if}}
```

**Pitfall:** `if_note_type_<X>` rejects unknown suffixes at preflight — use only the six known types (`thing`, `statement`, `person`, `source`, `code`, `moc`).

---

## Predicate flags

**What:** `predicate_flags` in `profile.yaml` lets you define custom boolean predicates driven by node attributes. Registered flags become valid `{{#if_flag_<X>}}` predicates.

**When:** Use when built-in predicates and `if_attr_*` are insufficient — e.g. equality checks (`status == "published"`).

**Profile YAML syntax:**

```yaml
predicate_flags:
  published:
    attr: status
    equals: published
  has_owner:
    attr: owner
  reviewed:
    attr: review_score
    equals: 5
```

Two rule shapes:
- `{attr: <name>}` — truthy check: `bool(node.get("<name>"))`
- `{attr: <name>, equals: <value>}` — equality check: `node.get("<name>") == <value>`

Invalid or unknown flag names in templates cause a `validate_template` error — declare the flag before using it.

<!-- test:predicate-flags -->
```markdown
{{#if_god_node}}
> [!hub] Hub node
{{/if}}

{{#if_attr_published}}
This note is marked published.
{{/if}}
```

**Pitfall:** `if_flag_<X>` where `X` is not declared in `predicate_flags` is rejected at preflight. The render path treats an unknown flag as `False` (defensive elision), but `validate_template` flags it as an error.

---

## Validation

**What:** `validate_template(text, required)` returns a list of error strings. Empty list = valid. Runs at preflight via `graphify --validate-profile <vault>` or `graphify doctor`.

**When:** Run before deploying custom templates. Errors from template validation cause `load_templates` to fall back to the built-in template and log to stderr.

**Checked invariants:**

| Check | Error message |
|-------|---------------|
| Unclosed `{{#X}}` | `validate_template: unclosed block '{{#X}}'` |
| Nested blocks | `validate_template: nested template blocks are not supported` |
| Mismatched closer | `validate_template: block mismatch` |
| Unknown predicate | `validate_template: unknown predicate '{{#X}}'` |
| Unknown `conn.<field>` | `validate_template: unknown connection field 'conn.X'` |
| Unknown `${var}` | `unknown placeholder ${var}` |
| Missing required `${var}` | `missing required placeholder ${var}` |
| Unknown `if_flag_X` | `validate_template: unknown flag predicate '{{#if_flag_X}}'` |
| Unknown `if_note_type_X` | `validate_template: unknown note type suffix 'X'` |

**Fallback contract:** If `profile.yaml` exists but fails validation, graphify prints errors to stderr and falls back to built-in defaults. The export still runs.

<!-- test:validation -->
```markdown
${frontmatter}

# ${label}

{{#if_has_connections}}
${connections_callout}
{{/if}}

${body}
```

**Pitfall:** `--validate-profile` validates profile YAML *and* templates. A template error does not abort the export — it causes silent fallback to defaults, which can look like "my profile was ignored."

---

## Backward compatibility

**What:** Templates with no block syntax (`{{#…}}…{{/…}}`) render byte-identical to the output from the pre-Phase-31 substitution engine. This is ROADMAP-31 criterion 4.

**When:** Always. Block-free templates are untouched by `_expand_blocks` — the function returns the original string unchanged when no block openers are found.

**Why:** `_BlockTemplate` extends `string.Template` with a one-segment dot idpattern (`${conn.label}` style). For templates that do not use `conn.*` placeholders, `_BlockTemplate.safe_substitute` behaves identically to stock `string.Template.safe_substitute`. No migration needed for existing block-free templates.

<!-- test:backward-compat -->
```markdown
${frontmatter}

# ${label}

${body}
```

**Pitfall:** Adding a `{{#…}}` block to an existing template requires re-running `validate_template` — the block engine's single-pass FSM is strict about openers and closers. Use `graphify --validate-profile <vault>` after any template edit.
