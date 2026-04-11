---
phase: 2
slug: template-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` (implicit pytest discovery) |
| **Quick run command** | `pytest tests/test_templates.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds (unit tests, no IO) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_templates.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

> Task IDs will be filled in by `gsd-planner`; this map locks the requirement ↔ test binding. The planner must bind each row below to a concrete task by editing this file during planning.

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| GEN-01 | MOC frontmatter contains `up`, `related`, `collections`, `tags`, `created` in block-list form | unit | `pytest tests/test_templates.py::test_render_moc_frontmatter_fields -x` | ❌ W0 | ⬜ pending |
| GEN-01 | All list fields emit as YAML block lists (`tags:\n  - a`) | unit | `pytest tests/test_templates.py::test_frontmatter_block_lists -x` | ❌ W0 | ⬜ pending |
| GEN-01 | Wikilinks in frontmatter are quoted (`"[[...]]"`) | unit | `pytest tests/test_templates.py::test_frontmatter_wikilinks_quoted -x` | ❌ W0 | ⬜ pending |
| GEN-01 | `created:` emitted unquoted as ISO date (parses as YAML date) | unit | `pytest tests/test_templates.py::test_frontmatter_created_date_type -x` | ❌ W0 | ⬜ pending |
| GEN-01 | `cohesion:` emitted unquoted as float | unit | `pytest tests/test_templates.py::test_frontmatter_cohesion_float -x` | ❌ W0 | ⬜ pending |
| GEN-02 | Wikilinks are auto-aliased `[[filename\|label]]` uniformly | unit | `pytest tests/test_templates.py::test_wikilink_auto_alias -x` | ❌ W0 | ⬜ pending |
| GEN-02 | `resolve_filename` + `safe_filename` dedup stable across re-runs | unit | `pytest tests/test_templates.py::test_resolve_filename_stable -x` | ❌ W0 | ⬜ pending |
| GEN-03 | User template in `<vault>/.graphify/templates/<type>.md` overrides built-in | unit | `pytest tests/test_templates.py::test_user_template_override -x` | ❌ W0 | ⬜ pending |
| GEN-03 | Invalid user template falls back to built-in with stderr warning | unit | `pytest tests/test_templates.py::test_invalid_user_template_fallback -x` | ❌ W0 | ⬜ pending |
| GEN-03 | `validate_template` rejects unknown `${foo}` but accepts `$$` escape and `<% %>` Templater tokens | unit | `pytest tests/test_templates.py::test_validate_template_rules -x` | ❌ W0 | ⬜ pending |
| GEN-04 | All 6 built-in templates load successfully via `importlib.resources` | unit | `pytest tests/test_templates.py::test_all_builtins_load -x` | ❌ W0 | ⬜ pending |
| GEN-04 | `render_note()` returns `(filename, text)` for Thing/Statement/Person/Source | unit | `pytest tests/test_templates.py::test_render_note_all_types -x` | ❌ W0 | ⬜ pending |
| GEN-04 | `render_moc()` and `render_community_overview()` return `(filename, text)` | unit | `pytest tests/test_templates.py::test_render_moc_and_overview -x` | ❌ W0 | ⬜ pending |
| GEN-05 | MOC body contains ` ```dataview ` fence with `${community_tag}` substituted | unit | `pytest tests/test_templates.py::test_render_moc_dataview_block -x` | ❌ W0 | ⬜ pending |
| GEN-05 | Custom `obsidian.dataview.moc_query` profile value overrides default | unit | `pytest tests/test_templates.py::test_custom_moc_query -x` | ❌ W0 | ⬜ pending |
| GEN-05 | Two-phase substitution isolates outer `${label}` from user query contents | unit | `pytest tests/test_templates.py::test_dataview_substitution_isolation -x` | ❌ W0 | ⬜ pending |
| GEN-06 | Notes contain `> [!note] Wayfinder` callout with `Up:` and `Map:` rows | unit | `pytest tests/test_templates.py::test_wayfinder_callout_present -x` | ❌ W0 | ⬜ pending |
| GEN-06 | MOC wayfinder links to Atlas; non-MOC links to parent MOC | unit | `pytest tests/test_templates.py::test_wayfinder_derivation -x` | ❌ W0 | ⬜ pending |
| GEN-07 | `resolve_filename("neural network theory", "title_case")` → `"Neural_Network_Theory"` | unit | `pytest tests/test_templates.py::test_resolve_filename_title_case -x` | ❌ W0 | ⬜ pending |
| GEN-07 | `resolve_filename("neural network theory", "kebab-case")` → `"neural-network-theory"` | unit | `pytest tests/test_templates.py::test_resolve_filename_kebab -x` | ❌ W0 | ⬜ pending |
| GEN-07 | `resolve_filename("Neural_Network_Theory", "title_case")` preserves word caps (splits on `_` and space) | unit | `pytest tests/test_templates.py::test_resolve_filename_existing_underscores -x` | ❌ W0 | ⬜ pending |
| GEN-07 | `resolve_filename("Teoría de Redes", "title_case")` NFC-normalized and unsafe-char-stripped | unit | `pytest tests/test_templates.py::test_resolve_filename_non_ascii -x` | ❌ W0 | ⬜ pending |
| — | Templater `<% tp.date.now() %>` tokens survive `safe_substitute()` round-trip | unit (regression) | `pytest tests/test_templates.py::test_templater_tokens_passthrough -x` | ❌ W0 | ⬜ pending |
| — | MOC section order D-31 correct (frontmatter → heading → wayfinder → members → subs → dataview → metadata) | unit (regression) | `pytest tests/test_templates.py::test_moc_section_order -x` | ❌ W0 | ⬜ pending |
| — | D-24 frontmatter field order preserved (`up` → `related` → `collections` → `created` → `tags` → graphify-owned) | unit (regression) | `pytest tests/test_templates.py::test_frontmatter_field_order -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_templates.py` — create test module with all rows above (stubs acceptable for Wave 0)
- [ ] `tests/fixtures/` — shared minimal graph + synthetic `classification_context` fixture for the 6 note types
- [ ] `graphify/builtin_templates/` directory must exist with 6 `.md` files before any render test can pass

*Existing pytest infrastructure covers the rest — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated note looks native in Obsidian with Properties/Dataview/Templater installed | GEN-01, GEN-05 | Requires Obsidian runtime with plugin set; cannot be automated in unit tests | Run `graphify --obsidian out_vault`, open the vault in Obsidian, confirm YAML Properties chips render for `up/related/tags`, confirm Dataview table populates, confirm Templater `<% %>` tokens resolve on open |
| Sefirot callout palette renders with List Callouts plugin styling | GEN-06 (aesthetic) | Visual verification only | Open a generated MOC with List Callouts plugin active, verify `> [!note]`, `> [!info]`, `> [!abstract]` styles apply |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all `❌ W0` references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter (by planner after task binding)

**Approval:** pending
