# Phase 41: Vault CLI — vault flag & Multi-Vault Selector - Context

**Gathered:** 2026-04-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver **explicit `--vault <path>`** as the primary way to pin an Obsidian vault root **without relying on CWD**, **multi-root vault discovery and selection** that stays **scriptable and CI-safe**, and **consistent diagnostics**: `doctor`, **dry-run**, and preview surfaces must report the **same resolved vault**, **notes/output paths**, and **detection source** as the main `run` / `--obsidian` flows (v1.7–v1.8 behavior). Satisfies **VCLI-01–VCLI-06**.

Phase **40** harness import/export and Phase **39** elicitation shapes stay authoritative — Phase **41** only adds vault-resolution UX and CLI flags; no change to harness interchange schemas.

**Discuss session note:** Phase 41 was not listed as a ROADMAP `<details>` block and had no `.planning/phases/41-*` directory initially (`init.phase-op` failed). That is fixed. Gray-area decisions below are **locked from `.planning/REQUIREMENTS.md` (VCLI-*)**, **Phase 40 deferred items**, and **`graphify/output.py` / Phase 27 `ResolvedOutput` patterns** so planning can proceed without blocking on live chat; refine in-plan if user overrides.

</domain>

<decisions>
## Implementation Decisions

### Flag precedence & resolution (VCLI-01)
- **D-01:** **`--vault <path>`** (when added to global/run-related parsers) **outranks strict CWD-only vault detection** for “which vault root governs profile load and sibling `graphify-out` placement.” Precedence order is documented in CLI help: **`--vault` > env pin (see D-05) > `resolve_output(cwd)` auto-detect**. Resolved paths are **normalized** (`Path.resolve()`), with **one stderr summary line** when an explicit flag overrides auto detection (mirror **output.py D-09** tone).
- **D-02:** **`--vault` does not replace `--output`** — they compose: vault root selects profile/context; **`--output`** remains the notes/output override per existing Phase 27 rules when both apply.

### Multi-vault selection (VCLI-02)
- **D-03:** **Minimal selector stack:** (1) **`--vault`** single path; (2) optional **`GRAPHIFY_VAULT`** env as default pin when no `--vault`; (3) optional **`--vault-list <file>`** — newline-separated repo-relative or absolute vault roots for scripted “pick first existing” or ordered preference; (4) **interactive prompt** only when **stderr is a TTY**, **multiple** roots are discovered (e.g. scan roots), and **no** `--vault` / env / list pin — **never block CI** (non-TTY → deterministic error listing candidates unless one match).
- **D-04:** “Discovery” scope for Phase 41 is **documented and bounded** (e.g. explicit paths only, or shallow scan of a user-provided parent) — **not** full-disk search; planner fills exact algorithm in RESEARCH.

### Doctor alignment (VCLI-03)
- **D-05:** **`graphify doctor`** uses the **same resolver entry** as run preview: print **resolved vault root** (or explicit “none”), **`ResolvedOutput.notes_dir` / `artifacts_dir`**, **`vault_detected`**, and **`source`** (`profile` / `cli-flag` / `default`). Any future `--vault` must appear in that banner.

### Dry-run / preview (VCLI-04)
- **D-06:** **`--dry-run`** on ingest/export/doctor paths shows **the same skip reasons and paths** as today’s detect pruning + profile validation — after vault resolution, not before (no divergent “phantom” vault).

### Testing (VCLI-05)
- **D-07:** **`tmp_path` fixtures** build tiny vaults with **`.obsidian/`** + optional **`.graphify/profile.yaml`**; tests cover **precedence matrix** (vault flag vs CWD vs env), **invalid path**, and **list file** parsing.

### Docs surface (VCLI-06)
- **D-08:** **README** gets a short **“Vault selection for scripting”** subsection; **`graphify --help`** (or run subgroup) lists **`--vault`**, **`GRAPHIFY_VAULT`**, and **`--vault-list`** in one table.

### Claude's Discretion
- Exact **argparse** placement (top-level vs `run` subcommand), **env var exact name** if `GRAPHIFY_VAULT` conflicts (planner checks ecosystem), **default discovery radius** for multi-root scan, and **wording** of interactive selector — within D-01–D-08.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — **VCLI-01–VCLI-06** (vault-root CLI surface).
- `.planning/ROADMAP.md` — Milestone v1.9 Phase 41 goal and dependency note.
- `.planning/PROJECT.md` — v1.9 themes (vault CLI).

### Prior phase contracts
- `.planning/phases/40-multi-harness-memory-inverse-import-injection-defenses/40-CONTEXT.md` — Phase 41 explicitly deferred; harness parity unchanged.
- `.planning/phases/39-tacit-to-explicit-onboarding-elicitation/39-CONTEXT.md` — Elicit/`resolve_output` integration; Phase 41 must not break sidecar paths.

### Implementation surfaces
- `graphify/output.py` — **`ResolvedOutput`**, **`is_obsidian_vault`**, **`resolve_output()`**, Phase 27 D-* decisions in module docstring.
- `graphify/__main__.py` — CLI wiring, `doctor`, `--obsidian`, existing `--vault` on subcommands (extend consistently).
- `graphify/profile.py` — **`validate_vault_path`**, profile load relative to vault root.
- `graphify/detect.py` — Self-ingestion pruning vs resolved output (Phase 28).

### Security & docs
- `SECURITY.md` — Path confinement expectations for user-supplied roots (Phase 41 should not weaken).
- `docs/vault-adapter.md` (if present) — End-user vault adoption narrative; cross-link when `--vault` lands.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- **`resolve_output(cwd, cli_output=...)`** — Single structure for **vault detection**, **notes vs artifacts** placement, and **source** labeling; Phase 41 should thread an optional **explicit vault root** into the same tuple rather than fork logic.
- **`is_obsidian_vault`** — Strict CWD check; **`--vault`** path must use the same `.obsidian` rule after resolve.
- **Existing `--vault` on** `init-diagram-templates`, **`approve`**, etc. — Precedent for flag naming; Phase 41 generalizes **global** vault pinning for the main pipeline.

### Established patterns
- **Stderr one-liners** for precedence (`[graphify] ...`) from Phase 27 — keep consistent for `--vault` vs auto-detect.
- **`doctor` + dry-run** already preview ingest — extend banners only; avoid duplicate resolver implementations (**single function** for “resolved execution context”).

### Integration points
- **`__main__.py`**: argument parsing for `run`, `doctor`, `--obsidian`, `elicit`, `update-vault` — any command that calls **`resolve_output`** or loads a profile must receive the **same resolved vault**.

</code_context>

<specifics>
## Specific Ideas

- Prefer **environment pin** (`GRAPHIFY_VAULT` or final name) for **Docker/CI** scripts over interactive selection (from SEED-vault-root-aware-cli intent).

</specifics>

<deferred>
## Deferred Ideas

- **GUI / Obsidian plugin** vault picker — out of scope (PROJECT out-of-scope list).
- **Automatic vault discovery** across arbitrary drives — not implied by VCLI-02 “minimal selector”; needs future phase if requested.

</deferred>

---

*Phase: 41-vault-cli-vault-flag-multi-vault-selector*
*Context gathered: 2026-04-30*
