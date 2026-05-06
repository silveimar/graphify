# Phase 63 — Discussion Log

**Date:** 2026-05-05
**Mode:** discuss (default)

## Areas Selected
All four presented gray areas: breadcrumb format, trigger precedence, `--explain-paths` format, legacy dir handling.

## Q1 — Breadcrumb wording & format
**Options presented:**
1. Two-line, matches Phase 64 contract (Recommended)
2. Single line, terse
3. New `notice:` keyword, two-line

**Selected:** Option 1 (two-line `info: / hint:`).
**Rationale:** Reuses the locked Phase 64 stderr shape with minimal contract drift; only adds `info:` as a second valid prefix.

## Q2 — Option B trigger precedence
**Options presented:**
1. Strict: vault CWD + no profile + no path flags (Recommended)
2. Also fire when `--obsidian-dir` points at CWD vault
3. Fire whenever vault CWD detected, regardless of flags

**Selected:** Option 1 (strict).
**Rationale:** Slots cleanly into the legacy-default position of the 70.1 precedence chain; explicit path flags always win.

## Q3 — `--explain-paths` output format
**Options presented:**
1. Plain text table on stdout, exit 0 (Recommended)
2. JSON only on stdout, exit 0
3. Plain text default + `--json` flag for JSON

**Selected:** Option 1 (plain text only).
**Rationale:** Human-readable now; JSON deferred to a future phase if scripting need emerges.

## Q4 — Legacy `graphify-out/` handling
**Options presented:**
1. Detect + one-line warning in breadcrumb (Recommended)
2. Ignore silently
3. Migrate automatically

**Selected:** Option 1 (detect + third `hint:` line).
**Rationale:** Preserves Phase 70.1's no-delete posture while still pointing the user at `graphify doctor` for cleanup.

## Deferred Ideas
- JSON output for `--explain-paths` (`--json` overlay)
- Auto-migration of legacy `graphify-out/` (belongs in `graphify doctor` / VPROF-04)
- User-configurable vault-out dir name (speculative)

## Scope-Creep Redirects
None — all discussion stayed inside VOPT-01/02/03 boundaries.
