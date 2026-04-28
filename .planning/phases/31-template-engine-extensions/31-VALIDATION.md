---
phase: 31
slug: template-engine-extensions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Test categories below are sourced from `31-RESEARCH.md` §"Validation Architecture" (lines 251–321). Per-task rows populated by the planner.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — see `tests/test_templates.py`, `tests/test_profile.py`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_templates.py tests/test_profile.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (full suite); ~5s (quick) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_templates.py tests/test_profile.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _populated by planner_ | _01 / 02_ | _1_ | TMPL-01 / TMPL-02 / TMPL-03 | T-31-* | _per-task_ | unit | `pytest tests/...` | _per-task_ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test Categories (from RESEARCH.md §Validation Architecture)

The planner MUST produce tasks covering every category below. Each row maps one validation behavior to its requirement and a representative test name.

### TMPL-01 (Conditionals)
- **Catalog predicate true** — `if_god_node` renders guarded section when node has `possible_diagram_seed: True`
- **Catalog predicate false** — guarded section omitted cleanly (no leftover `{{#if}}`/`{{/if}}` markers, no blank lines)
- **`if_isolated` true/false** — strict `G.degree == 0` boundary
- **`if_has_connections` true/false** — inverse of `if_isolated`
- **`if_has_dataview` true/false** — empty vs non-empty `${dataview_block}` scalar
- **`if_attr_<name>` truthy** — attribute exists and is truthy
- **`if_attr_<name>` falsy/missing** — attribute is None / absent / empty string / 0
- **Catalog vs `if_attr_*` disjointness** — catalog wins; `if_attr_<catalog_name>` reads attr regardless
- **Unknown predicate name** — `validate_template` returns specific error pre-render
- **Unclosed `{{#if_*}}`** — preflight error
- **Mismatched closer (`{{/connections}}` for `if`)** — preflight error
- **Backward compat** — block-free templates render byte-identical to today

### TMPL-02 (Connection Loops)
- **Loop with N≥1 connections** — body rendered N times, deterministic order (sort by `(relation, label)`)
- **Loop with 0 connections** — body omitted cleanly
- **`${conn.label}` dotted form** — renders connection label (sanitized)
- **`${conn_label}` flattened form** — same value as dotted form
- **Field set parity** — every field (label, relation, target, confidence, community, source_file) renders correctly
- **`conn.target` renders node label, not raw id** — readability invariant
- **`conn.confidence` renders EXTRACTED/INFERRED/AMBIGUOUS string** — schema invariant
- **Unknown `conn.<field>` reference** — preflight error from `validate_template`
- **Nested `{{#connections}}` in `{{#connections}}`** — preflight error with specific message
- **Nested `{{#if}}` in `{{#connections}}`** — preflight error
- **Nested `{{#if}}` in `{{#if}}`** — preflight error
- **Unclosed loop block** — preflight error

### TMPL-03 (Per-Note-Type Dataview Queries)
- **Top-level `dataview_queries` accepted** — entry in `_VALID_TOP_LEVEL_KEYS`
- **Per-note-type lookup** — MOC note uses `dataview_queries.moc` when set
- **Fallback to legacy `moc_query`** — when `dataview_queries.moc` absent
- **Each known note-type honored** — moc, community, thing, statement, person, source
- **Unknown key rejected** — `dataview_queries.things:` (typo) → `validate_profile` error
- **Empty string query** — handled deterministically (omit Dataview block? — define in plan)
- **Phase 30 deep-merge composition** — `extends:`/`includes:` merge `dataview_queries` per-key, later wins
- **`--validate-profile` provenance** — resolved `dataview_queries.<note_type>` shows in provenance dump

### Sanitization (Success Criterion 4 — cross-cutting)
- **Node label containing `{{`** — cannot inject conditional logic (escaped or stripped before substitution)
- **Node label containing `}}`** — cannot break out of loop body
- **Node label containing `#`** — cannot inject block opener
- **Node label containing `${`** — cannot inject scalar reference
- **Node label with backtick** — cannot break Dataview fence (existing WR-05 invariant)
- **Node label with newline** — cannot break callout / fence
- **Block expansion runs BEFORE substitution** — order invariant verified by adversarial fixture
- **Sanitization applied to loop iteration values** — `conn.label`, `conn.target`, etc.

### Render Integration
- **`render_note` invokes block expansion** for every note type
- **`_render_moc_like` invokes block expansion** for MOC + community
- **`render_moc` invokes block expansion** — entry point coverage
- **`render_community_overview` invokes block expansion** — entry point coverage

---

## Wave 0 Requirements

- [ ] `tests/test_templates.py` — extend with TMPL-01 / TMPL-02 / sanitization classes
- [ ] `tests/test_profile.py` — extend with `dataview_queries` validation cases
- [ ] `tests/fixtures/template_context.py` — NetworkX graph fixtures with god-node, isolated-node, connected-node (per RESEARCH.md L740–765)
- [ ] `tests/fixtures/profiles/dataview_queries_*.yaml` — profile fixtures with/without `dataview_queries` (per RESEARCH.md L765–790)
- [ ] `tests/fixtures/templates/blocks_*.md` — template fixtures exercising every block syntax + adversarial label cases (per RESEARCH.md L790–825)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none expected_ | — | All Phase 31 behaviors are pure-function rendering, fully unit-testable | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
</content>
</invoke>