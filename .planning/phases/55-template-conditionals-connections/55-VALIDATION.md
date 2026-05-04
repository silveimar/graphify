---
phase: 55
slug: template-conditionals-connections
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
post_execution_audit: 2026-05-03 (v1.11-MILESTONE-AUDIT) — full suite green at 2034 passed, 1 xfailed
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Sourced from 55-RESEARCH.md `## Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in `pyproject.toml`) |
| **Config file** | `pyproject.toml` (no separate `pytest.ini`) |
| **Quick run command** | `pytest tests/test_templates.py tests/test_profile.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~3s quick / ~30s full (Phase 54 close baseline: 1995 passed) |

---

## Sampling Rate

- **After every task commit:** `pytest tests/test_templates.py tests/test_profile.py -q`
- **After every plan wave:** `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3s quick / ~30s full

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-XX-XX | TBD | 0 | TMPL-01/02 | — | RED scaffolds: update `BlockContext` defaults, add `if_note_type_*` and `if_flag_*` test stubs | unit | `pytest tests/test_templates.py tests/test_profile.py -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-01 | — | `if_note_type_<X>` predicate (6 note types, true/false × 2 = 12 cases) | unit | `pytest tests/test_templates.py -k "if_note_type" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-01 | — | Unknown `if_note_type_<X>` rejected at preflight (D-55.05) | unit | `pytest tests/test_templates.py -k "note_type_unknown" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 2 | TMPL-01 | — | `predicate_flags: {is_published: {attr: is_published}}` truthy-flag block render | unit | `pytest tests/test_templates.py -k "if_flag" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 2 | TMPL-01 | — | `predicate_flags: {is_reviewed: {attr: status, equals: done}}` equality-flag block render | unit | `pytest tests/test_templates.py -k "if_flag" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 2 | TMPL-01 | T-55-FLAG-VAL | `predicate_flags` validation rejects: duplicates, catalog collision, `attr_` prefix, unknown attr (best-effort) | unit | `pytest tests/test_profile.py -k "predicate_flags" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 2 | TMPL-01 | — | `validate_profile_preflight` surfaces `predicate_flags` errors via same channel as block-validation errors | unit | `pytest tests/test_profile.py -k "preflight.*flag" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-01 | — | `BlockContext` accepts `note_type` and `flag_predicates` with default values (frozen-dataclass safe) | unit | `pytest tests/test_templates.py -k "block_context" -q` | ❌ Wave 0 | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-02 | — | Phase 31 nested-rejection held green (no regression, L2838) | unit | `pytest tests/test_templates.py::test_nested_blocks_rejected_with_specific_error -q` | ✅ exists | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-02 | — | Phase 31 nested-if-in-if held green (L2852) | unit | `pytest tests/test_templates.py::test_nested_if_in_if_rejected -q` | ✅ exists | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-02 | — | Phase 31 empty-iterable connections loop held green (L2767) | unit | `pytest tests/test_templates.py::test_connections_empty_loop_renders_nothing -q` | ✅ exists | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-01/02 | — | Block-free byte-identical gate (ROADMAP-31 criterion 4) updated for new `BlockContext` defaults | unit | `pytest tests/test_templates.py::test_block_free_template_renders_byte_identical -q` | ✅ exists (needs update) | ⬜ pending |
| 55-XX-XX | TBD | 1 | TMPL-01 | T-55-INJ | Sanitization regression — new predicates emit boolean only; existing label-injection tests stay green | unit | `pytest tests/test_templates.py -k "sanitize or inject" -q` | ✅ exists | ⬜ pending |
| 55-XX-XX | TBD | 3 | TMPL-01 | — | `docs/TEMPLATES.md` examples lifted as fixtures and run through `_expand_blocks` (D-55.12) | integration | `pytest tests/test_docs_templates_examples.py -q` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Plan IDs (`55-XX-XX`) populated by gsd-planner; this VALIDATION.md uses placeholders.*

---

## Wave 0 Requirements

- [ ] `tests/test_templates.py` — update `test_block_free_template_renders_byte_identical` (L3249) and any other direct `BlockContext(...)` constructions to include new fields with defaults
- [ ] `tests/test_templates.py` — add RED stubs for `if_note_type_*` predicate (6 note types × 2 = 12 minimum cases + unknown-suffix rejection)
- [ ] `tests/test_templates.py` — add RED stubs for `if_flag_*` predicate (truthy, equality, false)
- [ ] `tests/test_profile.py` — add RED stubs for `predicate_flags` validation (4 rejection rules + valid cases)
- [ ] `tests/test_docs_templates_examples.py` — new file scaffold; tests are RED until `docs/TEMPLATES.md` exists
- [ ] `docs/TEMPLATES.md` — new file (8 locked sections per CONTEXT.md D-55.11)
- [ ] `docs/PROFILE-CONFIGURATION.md` — 1-line pointer (D-55.13)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Authoring ergonomics of `predicate_flags:` in a real vault profile | TMPL-01 | Subjective UX — does the YAML shape feel natural? | After landing, draft a `predicate_flags:` block in a sample vault; confirm `graphify doctor` accepts it and a `{{#if_flag_*}}` template renders correctly. Capture in 55-VERIFICATION.md as a worked example. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (full) / < 3s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter once execution closes

**Approval:** pending — finalize after gsd-planner produces concrete plan IDs and waves.
