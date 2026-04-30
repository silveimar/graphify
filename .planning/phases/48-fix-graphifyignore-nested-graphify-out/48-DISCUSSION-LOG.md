# Phase 48: fix-graphifyignore-nested-graphify-out - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 48-fix-graphifyignore-nested-graphify-out
**Areas discussed:** Ignore diagnostics vs patterns, Canonical output root & legacy trees, Shared primitive & tests, Requirements traceability
**Mode:** `--chain --auto` (all gray areas auto-selected; recommended defaults)

---

## Ignore diagnostics vs declared patterns

| Option | Description | Selected |
|--------|-------------|----------|
| Hints always if nesting detected | Ignore file ignored for UX | |
| Suppress hints when effective ignores already exclude paths | Align with `_is_ignored` / shared eligibility | ✓ |
| Require one canonical pattern spelling | Strict string match only | |

**User's choice:** Auto — suppress duplicate recommendations when paths are already excluded (**D-48.01**, **D-48.02**).
**Notes:** `[auto] [Area] — Q: "Suppress 'add graphify-out/**' when .graphifyignore already covers nested output?" → Selected: "Yes — authoritative effective coverage" (recommended default)`

---

## Canonical output root & legacy nested trees

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-migrate / delete nested outputs | Risky data loss | |
| Warn + document; no destructive cleanup | Conservative operator safety | ✓ |
| Silent coalesce only | Hides state | |

**User's choice:** Auto — **D-48.03** / **D-48.04**.
**Notes:** `[auto] — Q: "Legacy nested graphify-out on disk?" → Selected: "Warn-only + document; no automatic deletion" (recommended default)`

---

## Shared primitive & tests

| Option | Description | Selected |
|--------|-------------|----------|
| Duplicate logic in doctor vs detect | Fast but drifts | |
| Single predicate family shared with D-45.08 | Parity across detect/collect_files/doctor/prompts | ✓ |

**User's choice:** Auto — **D-48.05**.
**Notes:** `[auto] — Q: "Shared helper for ignore-aware nesting hints?" → Selected: "Yes — extend Phase 45 shared corpus alignment"`

---

## Requirements traceability

| Option | Description | Selected |
|--------|-------------|----------|
| Leave roadmap REQ as TBD | | |
| Add explicit REQ rows in REQUIREMENTS.md this phase | Traceability for success criteria | ✓ |

**User's choice:** Auto — **D-48.07**.
**Notes:** `[auto] — Q: "Map success criteria to REQ IDs?" → Selected: "Yes — planner proposes IDs"`

---

## Claude's Discretion

- Helper module split, stderr wording, doc placement (`CLAUDE.md` vs `docs/` vs skills) — planner/executor discretion per CONTEXT.md.

## Deferred Ideas

- None captured during auto-discuss.
