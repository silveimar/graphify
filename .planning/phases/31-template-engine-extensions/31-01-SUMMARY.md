---
phase: 31-template-engine-extensions
plan: 01
subsystem: templates
tags: [templates, conditionals, loops, sanitization, string-template]
requires: []
provides:
  - "_BlockTemplate (string.Template subclass)"
  - "_PREDICATE_CATALOG (frozen at 4 members)"
  - "_CONN_FIELDS (frozen at 6 members)"
  - "_build_edge_records (deterministic sorted+sanitized records)"
  - "_expand_blocks (single-pass FSM, preflight-only-trusting)"
  - "BlockContext (frozen dataclass)"
  - "validate_template extended with block-syntax validation"
affects:
  - "render_note: now expands blocks before safe_substitute"
  - "_render_moc_like / render_moc / render_community_overview: same"
  - "All template loaders wrap text in _BlockTemplate"
tech-stack:
  added: ["dataclasses (stdlib)"]
  patterns: ["single-pass FSM block parser", "preflight-only validation", "sanitize-before-render"]
key-files:
  created:
    - tests/fixtures/templates/with_if_block.md
    - tests/fixtures/templates/with_connections_block.md
    - tests/fixtures/templates/with_if_attr.md
    - tests/fixtures/templates/nested_blocks_invalid.md
  modified:
    - graphify/templates.py
    - tests/test_templates.py
    - tests/fixtures/template_context.py
    - tests/test_pyproject.py
decisions:
  - "Wrap all template loaders in _BlockTemplate unconditionally (idpattern is a strict superset; back-compat by construction)"
  - "Use BlockContext.graph: object annotation to avoid networkx import in stdlib-only templates.py (IN-10)"
  - "_expand_blocks raises ValueError defensively for unreachable nested-opener cases (preflight should have rejected)"
metrics:
  duration: "~25 min"
  completed: "2026-04-28"
  tasks_completed: 2
  tests_added: 34
  total_tests_passing: 1777
---

# Phase 31 Plan 01: Block-Template Engine Extensions Summary

`{{#if_X}}…{{/if}}` conditional sections (TMPL-01) and `{{#connections}}…{{/connections}}` iteration blocks (TMPL-02) added to graphify's `string.Template`-based template engine, with sanitization hardening that prevents node-label-driven injection and a byte-identical backward-compatibility gate for block-free templates.

## Symbols Added/Modified in `graphify/templates.py`

| Symbol | Line (approx) | Role |
|--------|---------------|------|
| `_BlockTemplate(string.Template)` | 149 | Subclass with `idpattern = r"(?a:[_a-z][_a-z0-9]*(?:\.[_a-z][_a-z0-9]*)?)"` (D-05; no `pattern` override per RESEARCH §Pitfall 3) |
| `_CONN_FIELDS` | 165 | `frozenset` of exactly six members (D-04, frozen) |
| `_IF_ATTR_RE` | 169 | Compiled regex for `{{#if_attr_<name>}}` escape hatch (D-01/D-03) |
| `_BLOCK_OPEN_RE`, `_BLOCK_CLOSE_RE` | 172, 173 | Block parser regexes (single-pass FSM, no recursion — T-31-03 mitigation) |
| `_CONN_FIELD_RE`, `_CONN_FLAT_FIELD_RE` | 176, 177 | `${conn.X}` and `${conn_X}` recognizers for validation/scrubbing |
| `BlockContext` (frozen `@dataclasses.dataclass`) | 181 | Render-time predicate context |
| `_pred_god_node`, `_pred_isolated`, `_pred_has_connections`, `_pred_has_dataview` | 197–222 | Catalog handlers |
| `_PREDICATE_CATALOG` | 224 | `dict[str, Callable[[BlockContext], bool]]` — exactly four members (frozen) |
| `_eval_predicate` | 233 | Catalog dispatch + `if_attr_<name>` escape hatch |
| `_build_edge_records` | 248 | Deterministic sanitized records sorted by (relation ASC, label ASC) |
| `_expand_blocks` | 295 | Single-pass FSM expanding blocks BEFORE `safe_substitute` (D-16) |
| `validate_template` | 357 (extended) | Now rejects nested blocks (D-08 verbatim), unclosed openers, mismatched closers, unknown predicates, unknown conn fields |
| `_load_builtin_template`, `load_templates`, `_load_override_template` | (existing) | All now wrap in `_BlockTemplate` |
| `render_note`, `_render_moc_like`, `render_moc`, `render_community_overview` | (existing) | All four invoke `_expand_blocks` BEFORE `safe_substitute` |

## Frozen Catalog (D-02)

Exactly four predicates: `if_god_node`, `if_isolated`, `if_has_connections`, `if_has_dataview`.

## Frozen Connection Fields (D-04)

Exactly six fields: `label`, `relation`, `target`, `confidence`, `community`, `source_file`.

Both `${conn.<field>}` (dotted) and `${conn_<field>}` (flat parallel form per D-05) render identically.

## Locked Loop Sort Order

`_build_edge_records` sorts records by `(relation ASC, label ASC)` — RESEARCH OQ3 / VALIDATION ordering invariant. Locked by `test_connections_loop_deterministic_order`.

## Verbatim D-08 Error Message

```
validate_template: nested template blocks are not supported (found '{{#if_god_node}}' inside '{{#connections}}'). Flatten the template or pre-compute the predicate.
```

Asserted with exact `==` equality in `test_nested_blocks_rejected_with_specific_error`.

## D-16 Ordering Invariant (Block Expansion BEFORE Substitution)

Locked adversarially by `test_block_expansion_runs_before_substitution`: a node label set to the literal string `"{{#connections}}{{/connections}}"` cannot smuggle a fake nested loop, because block expansion has already consumed all openers in the template before substitution inserts the label as text.

## Backward-Compatibility Gate (ROADMAP Criterion 4)

`test_block_free_template_renders_byte_identical` loads the existing `graphify/builtin_templates/thing.md` (block-free) and verifies that the new pipeline (`_expand_blocks` → `_BlockTemplate.safe_substitute`) produces output byte-identical to a stock `string.Template.safe_substitute` call with the same substitution context. This is the explicit D-16 / TMPL-01 / ROADMAP criterion 4 backward-compatibility gate.

## Test Counts per Category

| Category | Count | Notes |
|----------|-------|-------|
| TMPL-01 conditional blocks (`if_*`, `if_attr_*`) | 8 | All four catalog members + escape hatch + Plan 02 dataview-empty cross-link |
| TMPL-02 connection loops (`test_connections_*`) | 7 | Iteration, all six fields, flat form, label-not-id (D-06), confidence string, empty case, deterministic order |
| `_build_edge_records` field provenance | 1 | Direct unit test |
| Preflight rejection (nested/unknown/unclosed/mismatched) | 5 | D-08 verbatim asserted |
| Render-entry-point integration (end-to-end) | 4 | One per render entry point — no forgotten call site possible |
| T-31-01 sanitization (label injection) | 6 | `{{`, `}}`, `#` (block opener smuggle), `${`, backtick, newline |
| D-16 ordering invariant adversarial test | 1 | `test_block_expansion_runs_before_substitution` |
| ROADMAP criterion 4 byte-identical gate | 1 | Block-free `thing.md` |
| D-09/D-10 preflight-only invariant | 1 | `test_render_does_not_revalidate_blocks` |
| **Total new tests** | **34** | |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed `import networkx as nx` under `TYPE_CHECKING`**

- **Found during:** Task 1 (initial run of `pytest tests/test_pyproject.py`)
- **Issue:** `tests/test_pyproject.py::test_templates_module_is_pure_stdlib` walks the AST of `graphify/templates.py` and rejects any non-stdlib import — even one guarded by `if TYPE_CHECKING:`. The plan's `<action>` block 6 prescribed adding `if TYPE_CHECKING: import networkx as nx`.
- **Fix:** Removed the TYPE_CHECKING import. Annotated `BlockContext.graph` as `"object"` instead of `"nx.Graph"`; runtime value is unchanged. Added `dataclasses` to the stdlib whitelist (it IS stdlib; the whitelist was simply too narrow).
- **Files modified:** `graphify/templates.py`, `tests/test_pyproject.py`
- **Commit:** 95deb70

**2. [Rule 1 - Test name vs. grep filter false positive] `test_label_injection_double_brace_open`**

- **Found during:** Acceptance criteria verification
- **Issue:** Acceptance criterion `grep -nE "open\(|Path\(" tests/test_templates.py | grep -v "tmp_path\|fixtures" | wc -l == 0` returns 1 because the test function name `test_label_injection_double_brace_open():` matches `open(`. The plan explicitly mandates this exact test name.
- **Fix:** None applied — the explicit naming requirement (mandated verbatim in the plan's `<behavior>` section) takes precedence over an overly broad grep pattern. The grep's intent (no real filesystem access outside `tmp_path`/`fixtures`) is satisfied: the only match is a test function name, not a real `open()` or `Path()` call.
- **Files modified:** none
- **Commit:** N/A (informational)

## Self-Check: PASSED

**Created files (verified present):**
- ✓ `tests/fixtures/templates/with_if_block.md`
- ✓ `tests/fixtures/templates/with_connections_block.md`
- ✓ `tests/fixtures/templates/with_if_attr.md`
- ✓ `tests/fixtures/templates/nested_blocks_invalid.md`

**Commits (verified in git log):**
- ✓ 95deb70 — `feat(31-01-01): add _BlockTemplate, predicate catalog, edge records, and block pre-processor`
- ✓ f100367 — `test(31-01-02): add Phase 31 block-template test suite`

**Test suite status:**
- ✓ `pytest tests/test_templates.py -q -x` exits 0 (190 passed)
- ✓ `pytest tests/ -q` exits 0 (1777 passed, 1 xfailed)

**Acceptance criteria verified:**
- ✓ `_BlockTemplate(string.Template)` exists with verbatim `idpattern`
- ✓ `_PREDICATE_CATALOG` has exactly 4 members; `_CONN_FIELDS` has exactly 6
- ✓ `_build_edge_records` defined and called from all 4 render entry points (grep count = 6)
- ✓ `_expand_blocks` defined and referenced ≥5× (grep count = 10)
- ✓ All template loaders wrap in `_BlockTemplate` (grep count = 6)
- ✓ Verbatim D-08 message asserted
- ✓ All grep-based test count thresholds met (≥6 injection tests, ≥7 connections tests, ≥8 if_* tests)
- ✓ Pytest selector counts: 8 (if), 18 (connections), 10 (rejection), 7 (sanitization)
- ✓ No new required dependencies in `pyproject.toml`
