---
phase: 31
slug: template-engine-extensions
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-28
audited: 2026-04-28
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
| 31-01-01 | 01 | 1 | TMPL-01 / TMPL-02 | T-31-01/02/03 | block engine + sanitization + preflight | unit | `pytest tests/test_templates.py -q` | ✅ | ✅ green (205) |
| 31-01-02 | 01 | 1 | TMPL-01 / TMPL-02 | T-31-01/02/03 | adversarial label + ordering + entry-point integration | unit | `pytest tests/test_templates.py -q` | ✅ | ✅ green |
| 31-02-01 | 02 | 2 | TMPL-03 (D-11/D-12) | — | top-level `dataview_queries` + `_KNOWN_NOTE_TYPES` validation | unit | `pytest tests/test_profile.py -q` | ✅ | ✅ green (173) |
| 31-02-02 | 02 | 2 | TMPL-03 (D-13/D-14, W5/W7) | — | per-note-type lookup chain + empty-output gate + provenance | unit | `pytest tests/test_templates.py tests/test_profile.py -q` | ✅ | ✅ green |
| audit | — | post | TMPL-01 disjointness | — | catalog vs `if_attr_*` are independent evaluators | unit | `pytest tests/test_templates.py::test_if_attr_disjoint_from_catalog_name -q` | ✅ | ✅ green |
| audit | — | post | TMPL-02 nested-if-in-if | — | preflight rejects `{{#if}}…{{#if}}` | unit | `pytest tests/test_templates.py::test_nested_if_in_if_rejected -q` | ✅ | ✅ green |
| audit | — | post | Sanitization on iteration | — | `_sanitize_wikilink_alias` applied to `${conn.label}`/`${conn.target}` | unit | `pytest tests/test_templates.py::test_connection_field_sanitization_blocks_label_injection -q` | ✅ | ✅ green |

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

- [x] `tests/test_templates.py` — extended with TMPL-01 / TMPL-02 / sanitization classes (Plan 01: 34 new tests; audit: +3)
- [x] `tests/test_profile.py` — extended with `dataview_queries` validation cases (Plan 02: 9 new tests)
- [x] `tests/fixtures/template_context.py` — `make_block_context` helper present
- [x] `tests/fixtures/profiles/dataview_queries_*.yaml` — `dataview_queries_valid.yaml`, `dataview_queries_unknown_key.yaml`, `dataview_queries_legacy_fallback.yaml`
- [x] `tests/fixtures/templates/blocks_*.md` — `with_if_block.md`, `with_connections_block.md`, `with_if_attr.md`, `nested_blocks_invalid.md`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none expected_ | — | All Phase 31 behaviors are pure-function rendering, fully unit-testable | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full suite ~12s wall-clock)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-28

---

## Validation Audit 2026-04-28

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

**Gaps filled (added to `tests/test_templates.py`):**
1. `test_if_attr_disjoint_from_catalog_name` — locks TMPL-01 catalog vs `if_attr_*` independence (catalog evaluator never short-circuits the attr escape hatch and vice-versa)
2. `test_nested_if_in_if_rejected` — locks D-08-style preflight rejection for `{{#if}}…{{#if}}` (the previously-tested nested case was only `{{#if}}` inside `{{#connections}}`)
3. `test_connection_field_sanitization_blocks_label_injection` — locks that `_sanitize_wikilink_alias` is applied to `${conn.label}` / `${conn.target}` iteration values for the chars it handles (`]]`, `|`, `\n`)

**Auditor note:** Block-opener (`{{#`) injection on loop iteration values is held by D-16 single-pass ordering (block expansion runs *before* substitution), already locked by `test_block_expansion_runs_before_substitution` and `test_label_injection_block_opener`. The implementation deliberately layers the defense — char-stripping for wikilink/markdown breakers, ordering for block-syntax breakers — and the new sanitization test asserts the half not previously covered.

**Suite status post-audit:** 1801 passed, 1 xfailed (was 1798 + 1 xfailed). Quick-run: `pytest tests/test_templates.py tests/test_profile.py -q` → 378 passed, 1 xfailed in <1s.
</content>
</invoke>