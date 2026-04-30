# Phase 49: add --version flag… - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 49 — CLI `--version`, command footer, skill/package validation, version module consolidation
**Areas discussed:** `--version` semantics, version footer, skill stamp messaging, `graphify.version` consolidation  
**Mode:** `/gsd-discuss-phase 49 --chain` — compact single-pass lock of all gray areas (equivalent to selecting every area) using roadmap + codebase review.

---

## `--version` / `-V` semantics

| Option | Description | Selected |
|--------|-------------|----------|
| A | Single-line stdout, exit 0, no skill check on this path | ✓ |
| B | Print full multi-line banner including skill paths | |
| C | Require subcommand (`graphify run --version`) | |

**User's choice:** Compact discuss defaults (chain).
**Notes:** Align with common Python CLI behavior; stderr reserved for warnings on normal commands.

---

## Version echo on successful commands

| Option | Description | Selected |
|--------|-------------|----------|
| A | One `[graphify] version …` line on stderr after success; omit pure `--version` path | ✓ |
| B | Always print twice (start + end) | |
| C | stdout only | |

**User's choice:** Compact discuss defaults (chain).
**Notes:** Prefer omitting footer on `install`/`uninstall` success to reduce noise — planner may refine.

---

## Skill vs package validation

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep `.graphify_version` equality check; improve directional copy (older vs newer stamp) | ✓ |
| B | Parse embedded SKILL.md for version string | |
| C | Warn on missing stamp | |

**User's choice:** Compact discuss defaults (chain).
**Notes:** Avoid new required deps for semver unless `packaging` already present.

---

## Single source of truth

| Option | Description | Selected |
|--------|-------------|----------|
| A | New `graphify.version.package_version()`; migrate `__main__`, capability, harness_interchange, elicit | ✓ |
| B | Leave duplicated metadata reads | |

**User's choice:** Compact discuss defaults (chain).

---

## Claude's Discretion

- Argparse vs manual early parse for `--version`.
- Exact set of subcommands that suppress the success footer (`install`/`uninstall` at minimum).

## Deferred Ideas

- JSON/machine-readable version output for agents.
- Automated `server.json` sync outside documented release flow.

---

## Auto session — `/gsd-discuss-phase 49 --chain --auto` (2026-04-30)

**Mode:** `--auto` — single pass; no `AskUserQuestion`. `[--auto] Context exists — updating with auto-selected decisions.`

| Gray area | Auto-resolution (recommended default) |
|-----------|----------------------------------------|
| Version flag surface | **D-49.01–D-49.02** — `--version`/`-V`, one stdout line, exit 0, no skill sidecar on introspection path |
| Success footer | **D-49.03–D-49.04** — `[graphify] version` on stderr after success (`_cli_exit`); omit duplicate on pure `--version`; omit/noise policy for install/uninstall per CONTEXT |
| Skill vs package | **D-49.05–D-49.06** — directional stamp messaging; silent if `.graphify_version` missing |
| Consolidation | **D-49.07–D-49.08** — `graphify.version.package_version()` only reader outside tests |

**Implementation spot-check:** `graphify/version.py`; `__main__.py` `_cli_exit`, early version argv handling; migrated imports in `capability`, `harness_interchange`, `elicit`.

**Cross-reference todos:** `[auto]` skipped — `gsd-sdk query todo.match-phase` unavailable; no folded todos.

**Next:** Auto-advance → `/gsd-plan-phase 49 --auto` (or close-out with `/gsd-validate-phase 49` if execution already merged).
