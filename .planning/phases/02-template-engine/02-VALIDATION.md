---
phase: 2
slug: template-engine
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-11
updated: 2026-04-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § "Validation Architecture".
> Task IDs bound to Plans 01–04 on 2026-04-11.

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

> Task IDs bound to concrete `{phase}-{plan}-T{task}` addresses. Task ID format: `02-{plan}-T{task_num}` (e.g. `02-01-T3` = Phase 2, Plan 01, Task 3).

| Req | Behavior | Test Type | Automated Command | Task ID | Status |
|-----|----------|-----------|-------------------|---------|--------|
| GEN-01 | MOC frontmatter contains `up`, `related`, `collections`, `tags`, `created` in block-list form | unit | `pytest tests/test_templates.py::test_render_moc_frontmatter_fields -x` | 02-04-T2 | ⬜ pending |
| GEN-01 | All list fields emit as YAML block lists (`tags:\n  - a`) | unit | `pytest tests/test_profile.py::test_dump_frontmatter_block_list_tags -x` | 02-01-T3 | ⬜ pending |
| GEN-01 | Wikilinks in frontmatter are quoted (`"[[...]]"`) | unit | `pytest tests/test_profile.py::test_dump_frontmatter_wikilink_quoted -x` | 02-01-T3 | ⬜ pending |
| GEN-01 | `created:` emitted unquoted as ISO date (parses as YAML date) | unit | `pytest tests/test_profile.py::test_dump_frontmatter_created_date_unquoted -x` | 02-01-T3 | ⬜ pending |
| GEN-01 | `cohesion:` emitted unquoted as float | unit | `pytest tests/test_profile.py::test_dump_frontmatter_cohesion_float_two_decimals -x` | 02-01-T3 | ⬜ pending |
| GEN-02 | Wikilinks are auto-aliased `[[filename\|label]]` uniformly | unit | `pytest tests/test_templates.py::test_emit_wikilink_auto_aliases -x` | 02-03-T1 | ⬜ pending |
| GEN-02 | `resolve_filename` + `safe_filename` dedup stable across re-runs | unit | `pytest tests/test_templates.py::test_resolve_filename_stable_across_calls -x` | 02-02-T1 | ⬜ pending |
| GEN-03 | User template in `<vault>/.graphify/templates/<type>.md` overrides built-in | unit | `pytest tests/test_templates.py::test_load_templates_user_override_replaces_builtin -x` | 02-02-T2 | ⬜ pending |
| GEN-03 | Invalid user template falls back to built-in with stderr warning | unit | `pytest tests/test_templates.py::test_load_templates_invalid_user_template_falls_back_and_warns -x` | 02-02-T2 | ⬜ pending |
| GEN-03 | `validate_template` rejects unknown `${foo}` but accepts `$$` escape and `<% %>` Templater tokens | unit | `pytest tests/test_templates.py::test_validate_template_ignores_dollar_escape tests/test_templates.py::test_validate_template_ignores_templater_tokens tests/test_templates.py::test_validate_template_rejects_unknown_var -x` | 02-02-T2 | ⬜ pending |
| GEN-04 | All 6 built-in templates load successfully via `importlib.resources` | unit | `pytest tests/test_templates.py::test_load_templates_returns_all_builtins_when_no_vault_override -x` | 02-02-T2 | ⬜ pending |
| GEN-04 | `render_note()` returns `(filename, text)` for Thing/Statement/Person/Source | unit | `pytest tests/test_templates.py::test_render_note_all_four_non_moc_types_work -x` | 02-03-T2 | ⬜ pending |
| GEN-04 | `render_moc()` and `render_community_overview()` return `(filename, text)` | unit | `pytest tests/test_templates.py::test_render_moc_returns_tuple tests/test_templates.py::test_render_community_overview_uses_community_template -x` | 02-04-T2 | ⬜ pending |
| GEN-05 | MOC body contains ` ```dataview ` fence with `${community_tag}` substituted | unit | `pytest tests/test_templates.py::test_build_dataview_block_substitutes_community_tag tests/test_templates.py::test_render_moc_contains_dataview_fence -x` | 02-04-T1 | ⬜ pending |
| GEN-05 | Custom `obsidian.dataview.moc_query` profile value overrides default | unit | `pytest tests/test_templates.py::test_build_dataview_block_honors_custom_moc_query tests/test_templates.py::test_render_moc_custom_moc_query_respected -x` | 02-04-T1 | ⬜ pending |
| GEN-05 | Two-phase substitution isolates outer `${label}` from user query contents | unit | `pytest tests/test_templates.py::test_build_dataview_block_two_phase_isolation -x` | 02-04-T1 | ⬜ pending |
| GEN-06 | Notes contain `> [!note] Wayfinder` callout with `Up:` and `Map:` rows | unit | `pytest tests/test_templates.py::test_build_wayfinder_callout_thing_links_to_parent_moc_and_atlas tests/test_templates.py::test_render_note_contains_wayfinder_callout -x` | 02-03-T1 | ⬜ pending |
| GEN-06 | MOC wayfinder links to Atlas; non-MOC links to parent MOC | unit | `pytest tests/test_templates.py::test_build_wayfinder_callout_moc_up_is_atlas tests/test_templates.py::test_render_moc_wayfinder_links_to_atlas -x` | 02-03-T1 | ⬜ pending |
| GEN-07 | `resolve_filename("neural network theory", "title_case")` → `"Neural_Network_Theory"` | unit | `pytest tests/test_templates.py::test_resolve_filename_title_case_basic -x` | 02-02-T1 | ⬜ pending |
| GEN-07 | `resolve_filename("neural network theory", "kebab-case")` → `"neural-network-theory"` | unit | `pytest tests/test_templates.py::test_resolve_filename_kebab_basic -x` | 02-02-T1 | ⬜ pending |
| GEN-07 | `resolve_filename("Neural_Network_Theory", "kebab-case")` → `"neural-network-theory"` (locks r"[ \t_]+" split for kebab) | unit | `pytest tests/test_templates.py::test_resolve_filename_kebab_existing_underscores -x` | 02-02-T1 | ⬜ pending |
| GEN-07 | `resolve_filename("Neural_Network_Theory", "title_case")` preserves word caps (splits on `_` and space) | unit | `pytest tests/test_templates.py::test_resolve_filename_title_case_existing_underscores -x` | 02-02-T1 | ⬜ pending |
| GEN-07 | `resolve_filename("Teoría de Redes", "title_case")` NFC-normalized and unsafe-char-stripped | unit | `pytest tests/test_templates.py::test_resolve_filename_title_case_unicode_nfc -x` | 02-02-T1 | ⬜ pending |
| — | Templater `<% tp.date.now() %>` tokens survive `safe_substitute()` round-trip | unit (regression) | `pytest tests/test_templates.py::test_validate_template_ignores_templater_tokens tests/test_templates.py::test_templater_token_passthrough_in_user_moc_template -x` | 02-02-T2 | ⬜ pending |
| — | MOC section order D-31 correct (frontmatter → heading → wayfinder → members → subs → dataview → metadata) | unit (regression) | `pytest tests/test_templates.py::test_render_moc_section_order_d31 -x` | 02-04-T2 | ⬜ pending |
| — | D-24 frontmatter field order preserved (`up` → `related` → `collections` → `created` → `tags` → graphify-owned) | unit (regression) | `pytest tests/test_profile.py::test_dump_frontmatter_field_order_preserved tests/test_templates.py::test_render_note_frontmatter_field_order -x` | 02-01-T3 | ⬜ pending |
| — | (BLOCKER 3 regression) `render_note(..., vault_dir=None)` uses built-ins only, no file access | unit (regression) | `pytest tests/test_templates.py::test_render_note_without_vault_dir_uses_builtins_only -x` | 02-03-T2 | ⬜ pending |
| — | (BLOCKER 3 regression) `render_moc(..., vault_dir=None)` uses built-ins only, no file access | unit (regression) | `pytest tests/test_templates.py::test_render_moc_without_vault_dir_uses_builtins_only -x` | 02-04-T2 | ⬜ pending |
| — | (BLOCKER 4 regression) `render_moc` derives members from ctx only, never walks G | unit (regression) | `pytest tests/test_templates.py::test_render_moc_does_not_consult_graph -x` | 02-04-T2 | ⬜ pending |
| MAP-05 | Below-threshold sub-communities render as `> [!abstract] Sub-communities` callout inside parent MOC (no separate file) | unit | `pytest tests/test_templates.py::test_build_sub_communities_callout_renders_abstract_callout tests/test_templates.py::test_render_moc_includes_sub_communities_when_present -x` | 02-04-T1 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_templates.py` — create test module with all rows above (created by Plan 02 Task 1)
- [ ] `tests/fixtures/template_context.py` — shared synthetic `make_classification_context` + `make_min_graph` factories (created by Plan 02 Task 1, extended by Plan 04 Task 2 with `make_moc_context`)
- [ ] `graphify/builtin_templates/` directory with 6 `.md` files — must exist before any render test can pass (created by Plan 01 Task 2)

*Existing pytest infrastructure covers the rest — no framework install needed.*

---

## Plan-to-Task Index

| Task ID | Plan | Task Title |
|---------|------|------------|
| 02-01-T1 | 02-01 | Extend pyproject.toml package-data |
| 02-01-T2 | 02-01 | Create 6 built-in .md template files |
| 02-01-T3 | 02-01 | Add `_dump_frontmatter()` + obsidian defaults to profile.py |
| 02-02-T1 | 02-02 | Create templates.py skeleton + `resolve_filename` + `KNOWN_VARS` + `ClassificationContext` |
| 02-02-T2 | 02-02 | Add `validate_template()` + `load_templates()` |
| 02-02-T3 | 02-02 | Wire lazy imports in `__init__.py` |
| 02-03-T1 | 02-03 | Implement section builders (frontmatter/wayfinder/connections/metadata/wikilink) |
| 02-03-T2 | 02-03 | Implement `render_note()` + non-MOC end-to-end tests |
| 02-04-T1 | 02-04 | Implement `_build_members_section` + `_build_sub_communities_callout` + `_build_dataview_block` |
| 02-04-T2 | 02-04 | Implement `render_moc()` + `render_community_overview()` + VALIDATION.md binding + final sweep |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated note looks native in Obsidian with Properties/Dataview/Templater installed | GEN-01, GEN-05 | Requires Obsidian runtime with plugin set; cannot be automated in unit tests | Run `graphify --obsidian out_vault`, open the vault in Obsidian, confirm YAML Properties chips render for `up/related/tags`, confirm Dataview table populates, confirm Templater `<% %>` tokens resolve on open |
| Sefirot callout palette renders with List Callouts plugin styling | GEN-06 (aesthetic) | Visual verification only | Open a generated MOC with List Callouts plugin active, verify `> [!note]`, `> [!info]`, `> [!abstract]` styles apply |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all `❌ W0` references (handled in Plans 01 and 02 first tasks)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter (bound to concrete task IDs 2026-04-11)

**Approval:** bound by planner 2026-04-11
