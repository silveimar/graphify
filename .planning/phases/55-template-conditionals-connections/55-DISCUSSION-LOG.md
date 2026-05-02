# Phase 55: Template conditionals & connection loops - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 55-template-conditionals-connections
**Areas discussed:** Phase scope, Predicate surface, P55/P56 boundary, Built-in note types, Preflight UX, Documentation location

---

## Phase scope

| Option | Description | Selected |
|--------|-------------|----------|
| Narrow: docs + delta only | Closure phase: docs + missing predicate + preflight-error UX. Smallest surface. | |
| Extend: new predicates + docs | Engine intact, add `if_note_type_<X>` + profile.yaml `predicate_flags:` + docs. Medium surface. | ✓ |
| Reframe: redirect to harden+ship | Mark Criteria 1 & 2 as already satisfied by Phase 31; Phase 55 = docs only. | |

**User's choice:** Extend
**Notes:** Confirmed Phase 31 (v1.7) already shipped block engine, 4 catalog predicates, `if_attr_*` escape hatch, `{{#connections}}` with deterministic sort, sanitization, nested-rejection tests, empty-iterable test. Phase 55 adds only the missing predicate forms + new profile key + the user-facing reference doc.

---

## Predicate surface

| Option | Description | Selected |
|--------|-------------|----------|
| Add `if_note_type_<X>` | Explicit per-note-type predicate | (initial round: ✓) |
| Profile-declared flag predicates | New profile.yaml key registered into catalog | (initial round: ✓) |
| None — `if_attr_*` is enough | Stay with current surface | (initial round: ✓ — contradiction surfaced) |

**Round 2 disambiguation:**

| Option | Description | Selected |
|--------|-------------|----------|
| Add `if_note_type_<X>` only | Smallest engine change | |
| Add note_type AND profile flags | Both new forms | ✓ |
| Surface all 3 in CONTEXT.md, planner picks | Defer to planner | |

**User's choice:** Add note_type AND profile flags
**Notes:** First-round multi-select included a contradictory "None" answer. Round 2 collapsed to "both": `if_note_type_<X>` + `predicate_flags:` profile key (registered into `_PREDICATE_CATALOG` at load) + `if_flag_<name>` template syntax to reference them.

---

## P55 vs P56 boundary

| Option | Description | Selected |
|--------|-------------|----------|
| P55 = engine surface; P56 = profile schema | P55 adds predicate names; P56 adds template-override keys. | ✓ |
| P55 absorbs profile-declared flags | Frontload risk into P55 | |
| Defer the boundary call to Phase 56 | Pure-engine P55, decide later | |

**User's choice:** P55 = engine surface; P56 = profile schema
**Notes:** Reconciled with the "both" selection above by reading "engine surface" as INCLUDING profile keys that register predicate names (engine-shaped) but EXCLUDING profile keys that compose template overrides (composition-shaped). Different keys, different jobs: `predicate_flags:` (P55) vs `template_overrides:` (P56) vs `dataview_queries:` per-note-type (P56). Resolved as D-55.09 / D-55.10 in CONTEXT.md.

---

## Built-in note types

| Option | Description | Selected |
|--------|-------------|----------|
| All 6 (thing/statement/person/source/code/moc) | Symmetric, future-proof | ✓ |
| Only code + moc | Smallest surface | |
| Open-ended `if_note_type_<any>` | Accept any suffix, evaluate at runtime | |

**User's choice:** All 6 (thing/statement/person/source/code/moc)
**Notes:** Matches `_KNOWN_NOTE_TYPES`. Validation rejects unknown suffixes at preflight (D-55.05) — open-ended matching was rejected because it would mask author typos.

---

## Documentation location

| Option | Description | Selected |
|--------|-------------|----------|
| New docs/TEMPLATES.md | Dedicated user reference, canonical | ✓ |
| New docs/MIGRATION_V1_11.md | Changelog-style transition guide | |
| Append to PROFILE-CONFIGURATION.md | Co-located with schema docs | |
| Both TEMPLATES.md + MIGRATION_V1_11.md | Reference + transition note | |

**User's choice:** New docs/TEMPLATES.md
**Notes:** Single canonical reference, no migration note. PROFILE-CONFIGURATION.md gets a 1-line pointer (D-55.13). Examples in TEMPLATES.md are tested as fixtures (D-55.12) to prevent doc rot.

---

## Preflight UX

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current — fall back to builtin | Existing warn-and-continue behavior | ✓ |
| Loud at preflight, fall back at runtime | Asymmetric: strict tooling, lenient runtime | |
| Strict everywhere | Block errors abort load_templates | |

**User's choice:** Keep current — fall back to builtin
**Notes:** No behavior change in Phase 55. The contract is documented in `docs/TEMPLATES.md` (D-55.14). "Loud preflight" deferred for future iteration if CI users request it.

---

## Closure check

| Option | Description | Selected |
|--------|-------------|----------|
| Ready for CONTEXT.md | Lock decisions, advance via --chain | ✓ |
| Discuss test surface | Talk through new test additions | |
| Discuss naming/grammar | `if_note_type_*` vs `if_type_*` vs `if_kind_*` | |
| Discuss docs/TEMPLATES.md outline | Pin section list | |

**User's choice:** Ready for CONTEXT.md
**Notes:** Section list for `docs/TEMPLATES.md` was pinned in CONTEXT.md D-55.11 (8 required sections) without a follow-up turn — pulled from existing Phase 31 invariants and the standard reference-doc pattern in `docs/RELATIONS.md`.

---

## Claude's Discretion

- Test file split (`tests/test_predicate_flags.py` vs append to `tests/test_templates.py`) — planner decides
- `predicate_flags` rule schema inner key names (`{attr, equals}` vs `{path, value}`) — planner aligns with Phase 30 mapping-rules style
- Whether `if_flag_<name>` evaluates rule at render-time (default) vs supports parameterized form
- Doc placement of catalog reference table

## Deferred Ideas

- Composite predicates (`if_X_AND_Y`) — future
- `{{#unless_*}}` / negation — future
- Block-level partials (`{{> snippet}}`) — future
- Override precedence for `predicate_flags` under `extends:` chains — Phase 56
- `docs/MIGRATION_V1_11.md` — explicitly NOT created
- Loud preflight UX (`doctor` exit-nonzero on block errors) — future
