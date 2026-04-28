# Phase 29: Doctor Diagnostics & Dry-Run Preview - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 29-doctor-diagnostics-dry-run-preview
**Areas discussed:** Doctor command surface, Dry-run flag placement, Report format & exit codes, Dry-run preview content & fixes

---

## Doctor command surface

### Q1: How should `graphify doctor` be exposed?

| Option | Description | Selected |
|--------|-------------|----------|
| New top-level subcommand | Joins `install`/`run`/`query`/`watch`/`enrich`/`vault-promote` in `__main__.py` dispatch | ✓ |
| Flag on existing run | `graphify --doctor` — lighter, no new dispatch branch | |
| Both | Subcommand AND aliased flag | |

**User's choice:** New top-level subcommand (Recommended)
**Notes:** Locked as D-30. Mirrors every other utility verb.

### Q2: Where should the doctor implementation live?

| Option | Description | Selected |
|--------|-------------|----------|
| New `graphify/doctor.py` module | Pure `run_doctor()` / `format_report()` functions | ✓ |
| Inline in `__main__.py` | Keep dispatch + impl together | |

**User's choice:** New `graphify/doctor.py` module (Recommended)
**Notes:** Locked as D-32. Matches per-stage-module convention.

---

## Dry-run flag placement

### Q1: Where should the new vault-aware `--dry-run` live?

| Option | Description | Selected |
|--------|-------------|----------|
| Only on `graphify doctor --dry-run` | Single home; zero collision with existing `--dry-run` flags | ✓ |
| Top-level `graphify --dry-run` only | Bare invocation flag — risks overlap with existing subcommand `--dry-run` | |
| Both | Same backend exposed at two entry points | |

**User's choice:** Only on `graphify doctor --dry-run` (Recommended)
**Notes:** Locked as D-31. Explicitly rejects top-level `graphify --dry-run` for v1.7. Existing `--dry-run` on vault-promote, --obsidian, and enrich keep current semantics.

---

## Report format & exit codes

### Q1: What output format should `graphify doctor` produce?

| Option | Description | Selected |
|--------|-------------|----------|
| Sectioned human text | Fixed sections, `[graphify]`-prefixed | ✓ |
| Sectioned text + optional `--json` | Add scriptable mode | |
| Single flowing text block | Narrative, no headers | |

**User's choice:** Sectioned human text (Recommended)
**Notes:** Locked as D-34. JSON mode deferred until concrete demand.

### Q2: What exit-code convention for `graphify doctor`?

| Option | Description | Selected |
|--------|-------------|----------|
| 0 = OK, 1 = any misconfig | Binary; CI gate stays simple | ✓ |
| Distinct codes per failure class | 1=invalid, 2=unresolvable, 3=self-ingest | |
| Always 0; warnings only | Loses success-criterion #2 contract | |

**User's choice:** 0 = OK, 1 = any misconfig (Recommended)
**Notes:** Locked as D-35. Failures co-occur; a code table would lock us in.

---

## Dry-run preview content & fixes

### Q1: What should `graphify doctor --dry-run` actually display?

| Option | Description | Selected |
|--------|-------------|----------|
| Counts + sample | Bounded output even on huge corpora | ✓ |
| Full file lists | Complete but potentially thousands of lines | |
| Counts only | Compact, no verification capability | |

**User's choice:** Counts + sample (Recommended)
**Notes:** Locked as D-38. First 10 ingest paths + grouped skip reasons (first 5 each).

### Q2: How should dry-run gather the file list?

| Option | Description | Selected |
|--------|-------------|----------|
| Call real `detect()` | Preview ≡ actual scan; structurally impossible to diverge | ✓ |
| Reimplement a lighter scanner | Faster but risks divergence — the exact bug doctor exists to surface | |

**User's choice:** Call real `detect()` (Recommended)
**Notes:** Locked as D-39. Phase 28 manifest/nesting/exclude logic exercised for free.

### Q3: How should 'recommended fixes' lines be generated?

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded mapping in `doctor.py` | `_FIX_HINTS` dict; one place to edit | ✓ |
| Paired with each validator | Validators return `(error, fix_hint)` tuples — invasive | |

**User's choice:** Hardcoded mapping in doctor.py (Recommended)
**Notes:** Locked as D-40. Keeps `validate_profile()` ABI stable (D-36).

---

## Claude's Discretion

- Exact `DoctorReport` form (dataclass vs. NamedTuple) — D-33
- How `detect()` surfaces skip reasons (extend return shape vs. predicate instrumentation vs. explain-mode flag) — D-39
- TTY/colorized output — nice-to-have if trivially free
- Exact `_FIX_HINTS` wording beyond the three example mappings — D-40
- MCP exposure via `serve.py` — deferred to v1.8 unless trivially free

## Deferred Ideas

- `graphify doctor --json` machine-readable output
- Distinct exit codes per failure class
- Top-level `graphify --dry-run` aliasing
- `graphify doctor --fix` auto-fix mode
- Per-fix priority/severity ranking
