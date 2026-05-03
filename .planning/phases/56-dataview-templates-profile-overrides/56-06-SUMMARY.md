---
phase: 56
plan: 06
subsystem: docs
tags: [docs, profile, templates, overrides, CFG-01, CFG-02, TMPL-03]
type: execute
requirements: [TMPL-03, CFG-01, CFG-02]
requires: [56-01, 56-02, 56-03, 56-04, 56-05]
provides:
  - "PROFILE-CONFIGURATION.md sections for mapping_rules[].id, mapping_rule_templates, note_type_templates, override precedence ladder, override collision validation, and worked example"
  - "TEMPLATES.md forward-pointer paragraph to PROFILE-CONFIGURATION.md override surface"
affects:
  - docs/PROFILE-CONFIGURATION.md
  - docs/TEMPLATES.md
tech-stack:
  added: []
  patterns:
    - "documentation-only update mirroring existing community_templates: section style"
    - "forward-pointer pattern (single paragraph, no semantic duplication) per D-56.11"
key-files:
  created: []
  modified:
    - docs/PROFILE-CONFIGURATION.md
    - docs/TEMPLATES.md
decisions:
  - "Encoded D-56.05 ladder as a numbered list with explicit cross-scope-silent-resolution note"
  - "Encoded D-56.06 four collision classes as a table with detector-name, trigger, and error-shape columns to match the validator output format"
  - "Worked example uses an AuthService node hitting all three override scopes simultaneously and walks the ladder explicitly with a step-by-step table"
  - "Top-level keys reference table extended with both new keys (Phase 56 annotation) so the reader sees them next to community_templates"
  - "Backward-compat note for mapping_rules[].id: opt-in only; profiles without it remain valid"
  - "TEMPLATES.md forward-pointer placed immediately after the block-engine intro paragraph (before the first ## Conditional blocks heading) — natural lead-in for readers asking 'how do I scope per community/note_type?'"
metrics:
  duration: ~6 min
  completed: 2026-05-03
---

# Phase 56 Plan 06: Documentation — overrides surface in PROFILE-CONFIGURATION.md + TEMPLATES.md forward-pointer Summary

Documented the Phase 56 profile composition surface (`mapping_rule_templates:`, `note_type_templates:`, `mapping_rules[].id:`, the D-56.05 precedence ladder, the four D-56.06 collision classes, plus a worked example) in `docs/PROFILE-CONFIGURATION.md`, and added a single forward-pointer paragraph in `docs/TEMPLATES.md`. Pure docs — no code changes; full test suite still green (2080 passed).

## Section structure added to docs/PROFILE-CONFIGURATION.md

Inserted after the existing `## community_templates` section, before `## Custom templates (files)`, in the order below. Top-level keys reference table (line ~63) was also extended with two new rows for `mapping_rule_templates` and `note_type_templates`.

1. **`## mapping_rules[].id` (optional)** — slug regex `^[a-z][a-z0-9_-]*$`, ≤ 80 chars, unique within `mapping_rules:`. Backward-compat note ("optional; existing profiles without `id:` remain valid"). YAML example showing two rules with `id:` and one without.
2. **`## mapping_rule_templates`** — `{match: rule_id, pattern: <slug>, template: <fragment-path>}` schema; `match:` allowlist is `{rule_id}` only in v1.11; `pattern:` must reference a `mapping_rules[].id`; path-confinement enforced (no `..`, no absolute, no leading `~`). YAML example pairing one rule with its override.
3. **`## note_type_templates`** — `{match: note_type, pattern: <one of _KNOWN_NOTE_TYPES>, template: <fragment-path>}`; `pattern:` allowlist enumerated as `code, community, moc, person, source, statement, thing`. YAML example with two entries.
4. **`## How overrides resolve (precedence ladder)`** — D-56.05 ladder as a numbered list (`mapping_rule_templates > community_templates > note_type_templates > base profile template`). Narrative explicitly states "cross-scope overlaps resolve silently via this ladder; no error is raised; no warning is emitted" and "within a single list, first-matching-rule wins; intra-list pattern overlap is not detected at preflight."
5. **`## Override collision validation`** — D-56.06 four collision classes encoded as a table with columns `Class | Where | Detected by | Error shape`:
   - Class 1: duplicate `pattern` (rule_id) within `mapping_rule_templates`
   - Class 2: duplicate exact `pattern` within any sibling list (`community_templates`, `mapping_rule_templates`, `note_type_templates`)
   - Class 3: duplicate `pattern` (= note_type) within `note_type_templates`
   - Class 4: cross-chain duplicate `dataview_queries.<note_type>` across `extends:`/`includes:` (provenance-aware error enumerates all contributing source paths)
   Block quote explicitly notes that pattern-overlap detection (e.g., `Auth*` vs `AuthService`) is intentionally NOT performed; render-time list-order resolution applies.
6. **`## Worked example: all three override lists for one note`** — A single conceptual `AuthService` node classified by `mapping_rules[id=service-class]`, in community `Authentication`, with `note_type: thing`. YAML snippet registers an override at every scope (mapping rule, community, note type). Step-by-step ladder-resolution table shows step 1 wins (loads `templates/service-class.md`), with narrative describing what would happen if each successive override were deleted (cascades down to step 2 → 3 → 4 → built-in, with stderr warning + fall-back if any selected file is missing).

## Exact paragraph text added to docs/TEMPLATES.md

Inserted immediately after the existing block-engine intro (between the "Pattern follows `docs/RELATIONS.md`…" paragraph and the `## Conditional blocks` heading):

> Profile-level template overrides (per-mapping-rule, per-community, per-note-type) and the precedence ladder that resolves between them are documented in [`docs/PROFILE-CONFIGURATION.md`](PROFILE-CONFIGURATION.md) (Phase 56 additions). This document scopes to the block engine; override resolution lives in the profile composition layer.

Exactly one paragraph. No override semantics duplicated.

## Verification

| Check | Result |
|-------|--------|
| `grep -c "mapping_rule_templates" docs/PROFILE-CONFIGURATION.md` | 12 (≥ 3 required) |
| `grep -c "note_type_templates" docs/PROFILE-CONFIGURATION.md` | 9 (≥ 3 required) |
| `grep -ci "How overrides resolve\|precedence ladder" docs/PROFILE-CONFIGURATION.md` | 2 (≥ 1 required) |
| `grep -ci "collision\|composition chain" docs/PROFILE-CONFIGURATION.md` | 6 (≥ 4 required) |
| `grep -c "rule_id" docs/PROFILE-CONFIGURATION.md` | 4 (≥ 1 required) |
| `grep -c "match: note_type" docs/PROFILE-CONFIGURATION.md` | 3 (≥ 1 required) |
| `grep -ci "worked example" docs/PROFILE-CONFIGURATION.md` | 1 (≥ 1 required) |
| File grew from 333 → 511 lines | +178 lines (≥ 80 required) |
| `grep -c "PROFILE-CONFIGURATION.md" docs/TEMPLATES.md` | 1 (≥ 1 required) |
| `grep -ci "profile-level template overrides\|profile composition layer" docs/TEMPLATES.md` | 1 (≥ 1 required) |
| `grep -c "mapping_rule_templates\|note_type_templates" docs/TEMPLATES.md` | 0 (must be 0 — no duplication) |
| `test -f docs/MIGRATION_V1_11.md` | Non-zero exit (file does not exist — D-56.12) |
| `grep -ci "deprecat" docs/PROFILE-CONFIGURATION.md` | 0 (no Phase-56 deprecation language for community_templates:) |
| `pytest tests/ -q` | 2080 passed, 1 xfailed (no regressions) |

## Deviations from Plan

None — plan executed exactly as written. All locked out-of-scope content (MIGRATION_V1_11.md, `community_templates:` deprecation, glob/regex pattern-overlap detection, per-block partial overrides, unified `template_overrides:` discriminator, author-declared `priority:`, block-engine templates for `dataview_queries`) was kept out.

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | `f21fdd9` | docs(56-06): document mapping_rule_templates, note_type_templates, mapping_rules.id, ladder, and collision matrix |
| 2 | `162c391` | docs(56-06): add forward-pointer in TEMPLATES.md to PROFILE-CONFIGURATION.md override surface |

## Self-Check: PASSED

- `[ -f docs/PROFILE-CONFIGURATION.md ]` → FOUND (511 lines)
- `[ -f docs/TEMPLATES.md ]` → FOUND
- `git log --oneline | grep f21fdd9` → FOUND
- `git log --oneline | grep 162c391` → FOUND
- `[ ! -f docs/MIGRATION_V1_11.md ]` → CONFIRMED ABSENT (D-56.12)
