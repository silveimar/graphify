# Phase 49: add --version flag to graphify command, and also print current version on each command result, Fix skill vs package version validations - Context

**Gathered:** 2026-04-30 (refreshed `/gsd-discuss-phase 49 --chain --auto`)
**Status:** Decisions locked — implementation spot-checked against repo; downstream: verification / milestone close per REQUIREMENTS (**CLI-VER-01/02** marked satisfied)

<domain>
## Phase Boundary

Ship **CLI version discoverability** and **consistent version provenance** across the installed package, command output, and platform skill installs:

1. **`graphify --version` / `-V`** — prints the running package version (PyPI distribution `graphifyy` via `importlib.metadata`) and exits **0** without running normal command dispatch or skill-version sidecar checks (avoid stderr noise on a pure introspection flag).
2. **Version on command results** — after a normal subcommand completes successfully (exit path), emit **one** concise line so logs and terminals show which graphify build ran (stderr, `[graphify]` prefix for consistency with existing CLI diagnostics).
3. **Skill vs package validation** — keep comparing **`.graphify_version`** next to installed `SKILL.md` to **`package_version()`**; refine messaging when stamp is **older vs newer** vs missing; preserve current skips for `install`, `uninstall`, `-h`/`--help`, and deduplicated `skill_dst` paths (`__main__.py` today).
4. **Single source of truth** — introduce a small **`graphify.version`** (or equivalent) module exporting **`package_version() -> str`** used by `__main__.py`, `capability._graphify_version`, `harness_interchange._package_version`, `elicit`, and any other call sites that today re-read `importlib.metadata` independently.

**Depends on:** Phase 48 (canonical output / doctor alignment shipped).

**Out of scope for 49:** Bumping `pyproject.toml` / release process (already documented in `CLAUDE.md`); rewriting embedded skill body text beyond what install already stamps; MCP `server.json` sync (follow existing post-bump checklist).

</domain>

<decisions>
## Implementation Decisions

### `--version` / `-V` flag

- **D-49.01:** Support **`graphify --version`** and **`graphify -V`** (common CLI convention). Print **exactly one line** to **stdout**: `graphify <version>` where `<version>` is the same string as `importlib.metadata.version("graphifyy")` (or `"unknown"` on `Exception` — mirror current `__main__.__version__` behavior). Exit **0**. No trailing skill warning on this path.
- **D-49.02:** Parse **`--version` / `-V` early** (after optional global vault argv strip if those flags must remain composable — planner verifies ordering against `_strip_leading_vault_global_argv`). **`--help`** remains the primary usage surface; version must not require a subcommand.

### Version echo on normal commands

- **D-49.03:** On **successful completion** of dispatched CLI work (exit code 0), print **one** line to **stderr**: `[graphify] version <version>` (same `<version>` as D-49.01). **Do not** print on the `--version` / `-V` early-exit path (avoid duplicate). **Do not** print on `install` / `uninstall` success if that would double noise with existing installer output — planner may fold into install summary or omit for those two commands only; default preference: **omit for install/uninstall**, **include** for all other successful exits including `doctor`, `query`, `--obsidian`, `update-vault` preview, etc.
- **D-49.04:** Errors / exit 2 paths: **no** success footer; optional follow-up phase if product wants version on failure (deferred).

### Skill vs package stamp

- **D-49.05:** **Keep** `.graphify_version` file as the skill-side stamp written by `install` paths. **Warn** when `installed != package_version()` with **directional** copy: if `installed < package` (string compare acceptable if versions are PEP 440; else use `packaging.version` only if already a dependency — **prefer** simple string inequality with clearer message "older stamp" vs "newer stamp" in English text without adding a hard dependency). Minimum bar: distinguish **older skill** (run `graphify install`) vs **newer stamp than package** (dev/editable weirdness — suggest reinstall or ignore).
- **D-49.06:** **Missing** `.graphify_version`: remain **silent** (cannot infer drift); document in `CLAUDE.md` one line if not already.

### Consolidation

- **D-49.07:** Add **`graphify.version`** (`package_version()` + optionally `__version__` alias) as the **only** runtime reader of `importlib.metadata.version("graphifyy")` outside tests. Migrate **`__main__.py`**, **`capability.py`**, **`harness_interchange.py`**, **`elicit.py`** to import it (search repo for `graphifyy` / `metadata.version` for stragglers).
- **D-49.08:** **Tests** (`tmp_path`, no network): `--version` / `-V` stdout + exit 0; footer line on a trivial success path (e.g. `graphify doctor --help` is not success of doctor — pick **`graphify` with a no-op or smallest command** per existing test patterns in `tests/test___main__.py` or add focused tests); skill warning copy when `.graphify_version` mismatches (existing patterns in install tests if any).

### Claude's Discretion

- Exact argparse structure (`argparse` vs manual `sys.argv`) and the **single hook** where the success footer runs — left to planner/impl for minimal diff vs `main()` control flow.
- Whether `packaging.version` comparison is worth a new dependency: **default no**; use string compare + message wording unless `packaging` already required.

### Auto-discuss reaffirmation (`--chain --auto`, 2026-04-30)

`[--auto] Selected all gray areas:` **Version flag surface** (`--version`/`-V`, stdout, exit 0); **Success footer** (stderr `[graphify] version`, success-only, install/uninstall suppression intent); **Skill stamp drift** (directional older/newer copy, silent missing `.graphify_version`); **`graphify.version` consolidation** (single `importlib.metadata` reader).

Each area resolved to the **recommended** option — matches existing **D-49.01–D-49.08** with **no decision drift**.

**Implementation alignment (spot-check, not a full audit):** `graphify/version.py` defines `package_version()`; `graphify/__main__.py` imports it, implements `_cli_exit` footer on `code == 0`, and early-handles `argv` when `--version`/`-V`; `capability.py`, `harness_interchange.py`, `elicit.py` route through `package_version`. Conflicts with this CONTEXT should be treated as bugs, not reinterpretation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap / state

- `.planning/ROADMAP.md` — Phase 49 title and v1.10 placement (CLI `--version` + version echo + skill/package validation).
- `.planning/STATE.md` — Accumulated note on Phase 49 scope.

### Prior phase handoff

- `.planning/phases/48-fix-graphifyignore-nested-graphify-out/48-CONTEXT.md` — Explicitly defers CLI version work to Phase 49.

### Code (integration points)

- `graphify/version.py` — **`package_version()`** (canonical runtime reader).
- `graphify/__main__.py` — `__version__`, `_cli_exit`, early `--version`/`-V`, `_check_skill_version`, `main()` skill check loop, install/uninstall writers of `.graphify_version`.
- `graphify/capability.py` — `_graphify_version()` via `package_version`.
- `graphify/harness_interchange.py` — `_package_version()` wraps `package_version`.
- `graphify/elicit.py` — imports `package_version` for display paths.
- `CLAUDE.md` — Package name `graphifyy`, `importlib.metadata` version note, bump/sync checklist.

### Requirements

- `.planning/REQUIREMENTS.md` — Add/trace **new REQ IDs** for version CLI + footer + consolidation in plan frontmatter (planner proposes IDs, e.g. `CLI-VER-*`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- `graphify/version.py` centralizes distribution version; `__main__.__version__` aliases `package_version()` at import time.
- `graphify/__main__.py` centralizes skill checks in `main()` with deduped `skill_dst` set and skips for `install`/`uninstall`/help; `_cli_exit` is the footer gate.

### Established patterns

- User-facing diagnostics and warnings use **`[graphify]`** or indented **`warning:`** on **stderr** (`_check_skill_version`).

### Integration points

- CLI entry is **`main()`** only; success paths are scattered across subcommand handlers — footer should use a **small helper** (e.g. `_emit_version_footer()`) called from a **single** central exit-success path if one exists, or carefully from branches (planner designs to avoid missing a command).

</code_context>

<specifics>
## Specific Ideas

- Roadmap example: **`update-vault`** showing **skill 0.4.7 vs package 1.0.0** — acceptance should include a **stderr warning** that is **actionable** (`graphify install`) and **not** falsely triggered when stamp matches after reinstall.

</specifics>

<deferred>
## Deferred Ideas

- **Version in JSON / machine-readable CLI output** — not required for 49; separate phase if MCP or `graphify query` gains structured metadata.
- **Auto-bump `server.json` / skills on every commit** — remains manual per `CLAUDE.md` release checklist.

Phase 49 scope only.

</deferred>

---

*Phase: 49-add-version-flag-to-graphify-command-and-also-print-current-version-on-each-command-result-fix-skill-vs-package-version-validations-graphify-update-vault-warning-skill-is-from-graphify-047-package-is-100*
*Context gathered: 2026-04-30*
