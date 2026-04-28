# Phase 29: Doctor Diagnostics & Dry-Run Preview - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface the resolved vault/profile/output state — already computed by Phases 27 and 28 — as a single human-readable diagnostic report, and offer a non-destructive preview of what a real run would do.

Two independent surfaces:

1. **`graphify doctor` (VAULT-14)** — Reads vault detection (`is_obsidian_vault`), profile validation (`validate_profile`), resolved output destination (`ResolvedOutput`), and the active ignore-list (`.graphifyignore` patterns + `output.exclude` globs + `_SELF_OUTPUT_DIRS` + `output-manifest.json` history). Prints a sectioned report. Exits non-zero on misconfiguration. Ends with concrete "Recommended fixes" lines.
2. **`graphify doctor --dry-run` (VAULT-15)** — Same report PLUS a preview section showing which input files would be ingested (counts + sample), which would be skipped (grouped by reason), and which output paths would be written. Calls real `detect()` so preview ≡ actual scan. No disk writes.

**Out of scope** (other v1.7 phases own these):
- Profile composition (`extends:` / `includes:`) → Phase 30
- Conditional / loop template syntax → Phase 31
- Top-level `graphify --dry-run` (no subcommand) — explicitly rejected (D-31).
- Changing `validate_profile()` signature — keep `list[str]` ABI stable (D-36).

**Carried in from Phase 27 (locked, do not re-discuss):**
- `ResolvedOutput` NamedTuple (`vault_detected`, `vault_path`, `notes_dir`, `artifacts_dir`, `source`, `exclude_globs`) is the integration contract — `doctor.py` consumes it directly. (D-13, D-18 of Phase 28)
- Strict CWD-only `.obsidian/` detection. (D-04)
- `--output` CLI flag overrides profile destination; precedence reported on stderr. (D-08, D-09)
- v1.0 backcompat default paths preserved when no vault detected. (D-12)

**Carried in from Phase 28 (locked, do not re-discuss):**
- `output-manifest.json` lives at `<resolved.artifacts_dir>/output-manifest.json` with FIFO N=5 history. (D-22, D-24)
- Nesting guard `_is_nested_output()` matches `_SELF_OUTPUT_DIRS` ∪ basenames of `resolved.notes_dir` / `resolved.artifacts_dir`. (D-18)
- `output.exclude:` globs in `profile.yaml` apply via `_is_ignored()` (`fnmatch`). (D-15, D-16)
- Manifest read-failure mode: warn-and-proceed-with-empty-history. (D-25)

</domain>

<decisions>
## Implementation Decisions

### Doctor command surface (VAULT-14)

- **D-30: New top-level subcommand.** `graphify doctor` joins `install`/`run`/`query`/`watch`/`enrich`/`vault-promote` in `__main__.py`'s dispatch table. Discoverable via `--help`. Mirrors every other utility verb. No flag-on-existing-run aliasing — single entry point.
- **D-31: Dry-run lives ONLY on `graphify doctor --dry-run`.** Bare `graphify --dry-run` is NOT introduced in v1.7. Existing `--dry-run` flags on `vault-promote` (MRG-05), `--obsidian` export (D-78), and `enrich` (ENRICH-10) keep their current semantics unchanged — zero collision. Single home for vault-aware preview.
- **D-32: New `graphify/doctor.py` module.** Pure functions: `run_doctor(cwd: Path, *, dry_run: bool = False) -> DoctorReport` and `format_report(report: DoctorReport) -> str`. `__main__.py` only orchestrates (parse args → call `run_doctor` → print → exit). Matches the per-stage-module pattern (detect/extract/build/cluster/analyze/report). Importable for unit tests and a possible future MCP exposure (deferred).
- **D-33: `DoctorReport` shape** (planner picks exact dataclass/NamedTuple form): carries `vault_detection`, `profile_validation_errors: list[str]`, `resolved_output: ResolvedOutput | None` (None when profile invalid), `ignore_list: list[str]` (the union surface — see D-37), `manifest_history: list[dict] | None`, `would_self_ingest: bool`, `recommended_fixes: list[str]`, and (when `dry_run=True`) `preview: PreviewSection`. Enables structured tests without parsing formatted text.

### Report format & exit codes (VAULT-14)

- **D-34: Sectioned human text only in v1.7.** Fixed sections in this order: Vault Detection / Profile Validation / Output Destination / Ignore-List / (Preview, when `--dry-run`) / Recommended Fixes. Each line `[graphify]`-prefixed per the existing stderr/stdout convention. No `--json` flag in v1.7 — add later only if scripting demand emerges. Keeps surface small.
- **D-35: Binary exit codes — 0 OK, 1 misconfigured.** Non-zero on ANY of: profile validation errors present, output destination unresolvable (e.g., D-05 missing-profile refusal, D-03 sibling-of-vault traversal rejection), or `would_self_ingest = True` (computed by re-running the nesting guard against the resolved destinations). Detail goes in the report body. CI gate stays simple. No distinct-codes-per-failure table — failures co-occur and the table would lock us in.
- **D-36: `validate_profile()` signature unchanged.** Keep `list[str]` return. Doctor calls it as-is and maps strings to fix hints via D-39. Avoids invasive changes to every existing caller.

### Ignore-list surface (VAULT-14, success criterion #1 "active ignore-list")

- **D-37: Ignore-list is the UNION of four sources, displayed grouped by source:**
  1. `_SELF_OUTPUT_DIRS` literal set (`graphify-out`, `graphify_out`)
  2. Resolved-basename additions (`resolved.notes_dir.name`, `resolved.artifacts_dir.name` when they differ)
  3. `.graphifyignore` patterns (via existing `_load_graphifyignore()`)
  4. Profile `output.exclude` globs (via `resolved.exclude_globs`)
  Each source labeled in the report so the user knows where to edit. No deduplication across sources (an entry appearing in two sources signals user intent — preserve it).

### Dry-run preview content (VAULT-15)

- **D-38: Counts + bounded sample.** Preview section shows:
  - "Would ingest: N files" + first 10 paths + "... +K more" if N > 10
  - "Would skip: M files" grouped by reason (`nesting`, `exclude-glob`, `manifest`, `sensitive`, `noise-dir`), each group with first 5 paths + "... +K more" if needed
  - "Would write to: <notes_dir>" and "Would write artifacts to: <artifacts_dir>" from `ResolvedOutput`
  Bounded output even on 10k-file vaults. The user can re-run a real `graphify` if they need full lists.
- **D-39: Dry-run calls real `detect()`.** No reimplemented lighter scanner — guarantees preview ≡ actual scan. Phase 28's manifest/nesting/exclude logic is exercised for free, and any divergence between dry-run and a real run is structurally impossible. Skip-reason annotation requires `detect()` to surface why each pruned path was pruned (planner: extend `detect()` return shape OR have doctor instrument the predicate calls — planner picks; the constraint is "single source of truth for skip decisions").

### Recommended-fixes generation (VAULT-14, success criterion #4)

- **D-40: Hardcoded `_FIX_HINTS` table in `doctor.py`.** Pattern-keyed mapping (substring or regex on validator error strings → actionable fix line). Single place to edit fix wording. Validators (`validate_profile`, `is_obsidian_vault`, `resolve_output`) stay unchanged. Examples:
  - `"missing .graphify/profile.yaml"` → `"Create .graphify/profile.yaml — see docs/vault-adapter.md"`
  - `"sibling-of-vault path escapes"` → `"Set output.path to a directory adjacent to your vault, not above it"`
  - `would_self_ingest=True` → `"Move existing graphify-out/ outside the input scan, or add 'graphify-out/**' to .graphifyignore"`
- **D-41: One fix line per detected issue.** No clustering, no priority ranking in v1.7. Listed in the order issues were detected during `run_doctor`.

### Claude's Discretion

- Exact `DoctorReport` dataclass vs. NamedTuple form (D-33) — planner picks; must be importable from tests.
- How `detect()` surfaces skip reasons for D-39 (extend return shape vs. predicate instrumentation vs. a parallel "explain mode" flag) — planner picks; constraint is single source of truth.
- Whether to colorize report sections when stdout is a TTY — nice-to-have, planner can include if trivially free; otherwise defer.
- Exact wording of every `_FIX_HINTS` entry beyond the three examples — planner drafts, must be actionable (verb-first imperative).
- Whether `doctor` is wired through `serve.py` MCP — deferred to v1.8 unless trivially free during planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 29 inputs (Phase 27 / 28 contracts — locked)
- `.planning/phases/27-vault-detection-profile-driven-output-routing/27-CONTEXT.md` — `ResolvedOutput` shape, `--output` precedence, vault detection semantics (D-01..D-13)
- `.planning/phases/28-self-ingestion-hardening/28-CONTEXT.md` — `output-manifest.json` schema, nesting guard, `output.exclude` semantics (D-14..D-29)
- `.planning/phases/27-vault-detection-profile-driven-output-routing/27-VERIFICATION.md` — confirms which Phase 27 contracts shipped
- `.planning/phases/28-self-ingestion-hardening/28-VERIFICATION.md` — confirms which Phase 28 contracts shipped

### Source-of-truth modules
- `graphify/output.py` — `ResolvedOutput`, `is_obsidian_vault`, `resolve_output`
- `graphify/profile.py` §`validate_profile` (line ~209) — returns `list[str]` of errors (ABI to preserve, D-36)
- `graphify/detect.py` §`_is_nested_output` (line ~273), §`_load_output_manifest` (line ~363), §`_save_output_manifest` (line ~385), §`_is_ignored` (line ~332), §`detect` (line ~442) — all inputs the doctor consumes; dry-run preview re-uses these (D-39)

### Project-level constraints
- `CLAUDE.md` — "No new required dependencies" constraint and "All file paths confined to output directory per `security.py` patterns"
- `.planning/REQUIREMENTS.md` — VAULT-14, VAULT-15 definitions
- `.planning/ROADMAP.md` — Phase 29 success criteria (the four MUST-be-true gates)
- `.planning/PROJECT.md` — v1.7 milestone scope and Python 3.10+ / no-new-deps constraints

### Codebase maps (consulted during scout)
- `.planning/codebase/ARCHITECTURE.md` — pipeline stage pattern (per-module function), validates D-32
- `.planning/codebase/CONVENTIONS.md` — `[graphify]`-prefixed stderr/stdout, `from __future__ import annotations`, type hints, validators-return-error-lists pattern (validates D-34, D-36)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `graphify/output.py:ResolvedOutput` — single integration contract; doctor reads it directly with no transformation
- `graphify/output.py:is_obsidian_vault` / `:resolve_output` — vault detection + destination resolution; doctor calls both unchanged
- `graphify/profile.py:validate_profile` — returns `list[str]`; doctor consumes the list as-is and maps via `_FIX_HINTS` (D-40)
- `graphify/detect.py:_load_output_manifest` — already returns empty envelope on failure with the right warning shape (D-25 from Phase 28); doctor reuses
- `graphify/detect.py:_is_nested_output`, `_is_ignored`, `_load_graphifyignore` — the four ignore-list sources for D-37
- `graphify/detect.py:detect` — full scan logic; dry-run calls it for parity (D-39)

### Established Patterns
- One-stage-per-module convention (detect.py, extract.py, build.py, cluster.py, analyze.py, report.py, export.py) — `doctor.py` joins this set (D-32)
- Pure functions returning plain dicts/dataclasses — no shared state, no side effects outside `graphify-out/` (CLAUDE.md "Architecture")
- Validators return `list[str]` of errors, not raised exceptions (`validate.py`, `profile.py`); doctor matches this style for collecting issues before formatting
- `[graphify] WARNING: …` / `[graphify] ERROR: …` stderr lines (`build.py`, `cluster.py`, `detect.py`); doctor's report uses the same prefix per D-34
- Atomic write via tmp+rename (Phase 24, D-29 of Phase 28) — doctor itself writes nothing in v1.7, but the dry-run preview must NOT trigger any writer

### Integration Points
- `graphify/__main__.py:main` dispatch table — add a `doctor` branch alongside `run`, `query`, `watch`, `enrich`, `vault-promote` (D-30)
- `graphify/__main__.py` `--help` block — add `doctor` subcommand line; document `--dry-run` only under that subcommand (D-31)
- `tests/test_doctor.py` (new) — pure unit tests against `run_doctor()` and `format_report()`; no filesystem side effects outside `tmp_path` per CLAUDE.md testing conventions

</code_context>

<specifics>
## Specific Ideas

- Sections in the report appear in a fixed order so users can grep/scroll predictably (D-34): Vault Detection → Profile Validation → Output Destination → Ignore-List → Preview (if `--dry-run`) → Recommended Fixes.
- Recommended Fixes section appears even when there are zero issues — in that case it prints `[graphify] No issues detected.` so the section is never absent (predictable shape).
- Skip-reason groups in the dry-run preview use the literal labels `nesting`, `exclude-glob`, `manifest`, `sensitive`, `noise-dir` so future doc/test references are stable.

</specifics>

<deferred>
## Deferred Ideas

- `graphify doctor --json` machine-readable output for CI/scripting (D-34 says no in v1.7; revisit when concrete demand appears).
- Distinct exit codes per failure class (D-35 says no — failures co-occur).
- Top-level `graphify --dry-run` aliasing (D-31 explicitly rejected for v1.7 to avoid `--dry-run` overload).
- MCP exposure of `doctor` via `serve.py` — possible v1.8.
- Auto-fix mode (`graphify doctor --fix`) that applies recommended fixes — out of scope; doctor is read-only by design.
- Color/TTY-aware report formatting beyond plain `[graphify]`-prefixed text — Claude's Discretion if trivially free.
- Per-fix priority/severity ranking (D-41 says no in v1.7).

</deferred>
