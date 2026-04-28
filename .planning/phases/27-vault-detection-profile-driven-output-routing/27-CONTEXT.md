# Phase 27: Vault Detection & Profile-Driven Output Routing - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

When `graphify` is invoked from a directory whose CWD is itself an Obsidian vault (signaled by a `.obsidian/` directory at CWD), it must:

1. Detect the vault and report detection in CLI output (VAULT-08).
2. Auto-adopt profile-driven placement (SEED-vault-root-aware-cli **Option C**) — CWD is treated as both input corpus and output target without an explicit flag, gated on a present-and-valid `.graphify/profile.yaml` (VAULT-09).
3. Resolve the output destination from a new `output:` block in the profile schema, supporting vault-relative, absolute, and sibling-of-vault modes (VAULT-10).
4. Allow a new unified `--output <path>` CLI flag to override the profile output, with precedence reported on stderr (VAULT-10).

Out of scope for this phase (other v1.7 phases own them):
- Self-ingestion pruning of the resolved output destination → Phase 28
- Manifest-based ignore list, recursive `**/graphify-out/**` guard → Phase 28
- `graphify doctor` diagnostic command, `--dry-run` preview → Phase 29
- Profile composition (`extends:`/`includes:`), per-community templates → Phase 30
- Conditional / loop template syntax → Phase 31

</domain>

<decisions>
## Implementation Decisions

### Profile schema — output destination
- **D-01:** New top-level `output:` block in profile.yaml with explicit struct shape `{ mode: vault-relative | absolute | sibling-of-vault, path: <string> }`. Add to `_VALID_TOP_LEVEL_KEYS` in `graphify/profile.py`. Self-documenting and validates cleanly without prefix-parsing tricks.
- **D-02:** No source-path mirroring fallback (carried forward from `.planning/notes/v1.7-input-vault-adapter-no-source-mirroring.md`). When auto-adopt fires and the profile is silent on `output:`, refuse loudly with an actionable error message — do **not** default to `<vault>/graphify-out/`, do **not** mirror `source_file` paths.
- **D-03:** `mode: sibling-of-vault` resolves to `<vault>/../<path>` and intentionally steps outside `validate_vault_path()`'s vault-confinement check. A new validator in `profile.py` (or `security.py`) must explicitly authorize this mode while still rejecting traversal beyond a sane boundary (e.g., reject empty `path`, reject `path` that resolves to filesystem root or above the vault parent).

### Vault detection trigger semantics
- **D-04:** Detection is **strict CWD-only** — `Path('.obsidian').is_dir()` from the process working directory. No parent-walking. Predictable, matches "I cd'd into a vault" mental model, avoids surprise auto-adopt when CWD is a sub-folder of a vault.
- **D-05:** When `.obsidian/` is present at CWD but `.graphify/profile.yaml` is missing, **refuse with an actionable message** (SEED Option A safety net). Do not silently auto-write a default profile, do not warn-and-fall-back to current placement. Suggested message shape: `"CWD is an Obsidian vault but no .graphify/profile.yaml found. Create one (see docs/vault-adapter.md), or pass --output <path> to write outside the vault."`
- **D-06:** Auto-adopt is wired into **both** the build pipeline (the default `graphify <args>` invocation that produces `graphify-out/`) AND the `--obsidian` export sub-command. Consistent UX — the user shouldn't have to remember which sub-command honors profile output. Other commands (watch, vault-promote) are out of scope for this phase.
- **D-07:** When auto-adopt fires, the **input corpus root is forced to CWD** (the vault). This is the literal SEED Option C contract. Other commands that already accept a positional source path keep their own semantics; auto-adopt only governs the default invocation.

### CLI override + precedence reporting
- **D-08:** Introduce a new unified `--output <path>` flag. Existing `--out-dir` (build pipeline) and `--obsidian-dir` (export) are retained as-is for backward compatibility — they keep working when no vault is detected and no `--output` is given. When `--output` is present, it takes precedence over both legacy flags AND over the profile's `output:` block.
- **D-09:** When CLI `--output` overrides the profile's `output:`, print a single stderr line, **always shown** (not gated by a verbosity flag): `[graphify] --output=<flag-path> overrides profile output (mode=<m>, path=<resolved-p>)`. Predictable for scripts and easily suppressed via `2>/dev/null`.
- **D-10:** `--output <path>` interprets the path as the user typed it — no `mode:` inference. The user is taking explicit control; treat it as an absolute or CWD-relative literal path.

### Scope of resolved destination (what "output" actually controls)
- **D-11:** When auto-adopt fires, the profile's resolved `output:` destination governs **only the rendered Obsidian markdown notes** (the `--obsidian` export tree). Build artifacts (`graph.json`, `extraction.json`, `cache/`, `GRAPH_REPORT.md`, manifests, `vault-manifest.json`, etc.) go to `<vault>/../graphify-out/` automatically (sibling-of-vault default for build artifacts). Rationale: keeps machine artifacts and cache directories out of the user's vault index, and makes Phase 28's self-ingest hardening straightforward (one rendered-notes path + one sibling artifacts path to prune).
- **D-12:** When **no vault is detected** at CWD (and no `--output` flag), preserve current v1.0 paths exactly: build artifacts to `graphify-out/`, obsidian export to `graphify-out/obsidian/`. Backward compatibility is non-negotiable per PROJECT.md constraints.
- **D-13:** The phase ships a single resolved-destination data structure (e.g., `ResolvedOutput` namedtuple/dataclass returned by a new function in `profile.py` or `detect.py`) that carries: `vault_detected: bool`, `vault_path: Path | None`, `notes_dir: Path`, `artifacts_dir: Path`, `source: Literal["profile", "cli-flag", "default"]`. Phase 28's self-ingest hardening, Phase 29's doctor command, and the CLI runner all consume this single resolution result. This is the integration contract for v1.7.

### Claude's Discretion
- Exact Python type / location of `ResolvedOutput` (function in `profile.py` vs new tiny module) — planner picks, but it must be importable by `__main__.py`, `detect.py` (Phase 28 dependency), and a future `doctor.py` (Phase 29 dependency).
- Exact wording of error messages for D-05 and the sibling-of-vault validator (D-03), beyond the suggested shapes above.
- Whether vault-detection report (VAULT-08) is a single line or a small block — keep terse.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 27 inputs (decisions locked outside this discussion)
- `.planning/seeds/SEED-vault-root-aware-cli.md` — defines Option A / B / C; VAULT-09 commits to **Option C** auto-adopt
- `.planning/notes/v1.7-input-vault-adapter-no-source-mirroring.md` — locks "no source-path mirroring fallback" (D-02)
- `.planning/notes/obsidian-export-self-ingestion-loop.md` — root cause analysis from the v1.6 bug that motivated this milestone
- `.planning/notes/folder-architecture-graphify-out-vs-vault.md` — folder architecture context
- `.planning/REQUIREMENTS.md` (v1.7) — VAULT-08, VAULT-09, VAULT-10 (the three Phase 27 requirements)
- `.planning/ROADMAP.md` §"Phase 27: Vault Detection & Profile-Driven Output Routing" — success criteria and dependency declaration

### v1.0 vault adapter foundations (this phase extends them)
- `.planning/milestones/v1.0-ROADMAP.md` — original vault-adapter contract
- `.planning/milestones/v1.0-REQUIREMENTS.md` — PROF-* and the original output-related decisions
- `graphify/profile.py` — `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `load_profile()`, `validate_profile()`, `validate_vault_path()` are the integration surface
- `graphify/__main__.py` — `--obsidian`, `--obsidian-dir`, `--out-dir` flag handling lives here (~lines 1285–1382 and 1503–1535)
- `graphify/detect.py` — Phase 28 will add output-path pruning here; this phase must not break existing `_is_noise_dir` / `graphify-out/` defaults
- `SECURITY.md` — path-confinement model that `mode: sibling-of-vault` deliberately reaches outside; D-03 must respect spirit
- `CLAUDE.md` (project) — Constraints section: Python 3.10+, no new required deps, backward compat, pure unit tests

### Codebase intel maps (read before planning)
- `.planning/codebase/STRUCTURE.md` — module layout
- `.planning/codebase/CONVENTIONS.md` — `from __future__ import annotations`, type hints, naming
- `.planning/codebase/INTEGRATIONS.md` — how CLI, profile loader, and pipeline talk to each other

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`graphify/profile.py:_DEFAULT_PROFILE`** — already a nested dict with sections (`folder_mapping`, `obsidian`, `merge`, `topology`, `mapping`, `tag_taxonomy`, `profile_sync`, `diagram_types`). Adding a new top-level `output:` block follows the established pattern.
- **`graphify/profile.py:_VALID_TOP_LEVEL_KEYS`** — single set governing allowed top-level profile keys. Add `"output"`. (Same single-line change pattern used for `diagram_types` in Phase 21.)
- **`graphify/profile.py:validate_profile()`** — returns `list[str]` of errors. Extend to validate the new `output:` struct: presence of `mode` (must be in `{vault-relative, absolute, sibling-of-vault}`), presence of `path` (must be non-empty `str`).
- **`graphify/profile.py:validate_vault_path()`** — current vault-confinement validator. Reuse for `mode: vault-relative`. New sibling validator for `mode: sibling-of-vault` lives next to it.
- **`graphify/profile.py:load_profile()`** — already accepts `vault_dir` and applies `_deep_merge` against `_DEFAULT_PROFILE`. Auto-adopt path can call this with the detected vault dir.
- **`graphify/__main__.py` flag-parsing pattern** (~line 1304: `--obsidian-dir`, ~line 1503: `--out-dir`) — use the same manual-loop parser style for the new `--output` flag.
- **`_load_profile_for_approve()` (line 939)** — established pattern for "load profile for a vault path"; the auto-adopt code path can do the same.

### Established Patterns
- **Argparse-free manual flag loop** in `__main__.py` — keep consistent.
- **Stderr for warnings/info** prefixed with `[graphify]` (`graphify/build.py`, `graphify/cluster.py`). The precedence-message in D-09 follows this.
- **Validate-first, fail-loudly** — `validate_profile()` returns errors; `validate_profile_preflight()` aggregates. The "no profile but vault detected" refusal in D-05 follows this pattern.
- **`from __future__ import annotations` first**, single-line module docstring next.

### Integration Points
- **CLI runner in `__main__.py`** — needs a new "resolve output before pipeline starts" step that decides `(vault_detected, notes_dir, artifacts_dir)` and emits the precedence message when applicable.
- **`graphify/detect.py`** — read-only consumer in this phase (no behavioral change). Phase 28 will modify `_is_noise_dir` / `_SELF_OUTPUT_DIRS` to prune the resolved `notes_dir` and `artifacts_dir`.
- **`graphify/profile.py`** — primary surface for D-01, D-02, D-03 (schema, defaults, validation).
- **Eventual Phase 29 `doctor` command** — depends on the `ResolvedOutput` data structure from D-13.

</code_context>

<specifics>
## Specific Ideas

- The user accepted every recommended option. The recommendations themselves are the specifics.
- Anchor wording from SEED + carry-forward note: "Option C auto-adopt", "no source-path mirroring fallback", "CWD is both input corpus and output target".
- The phase ROADMAP success criterion #4 explicitly mentions stderr precedence reporting — D-09 satisfies this verbatim.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-write a minimal default profile** when vault detected but no profile present — rejected for D-05 (mutates user's vault on first run, surprising side effect). Could surface again in a v1.8 onboarding phase tied to SEED-001 (Tacit-to-Explicit Elicitation Engine).
- **Walking-up parent detection** for `.obsidian/` — rejected for D-04. If users report needing it, revisit as a v1.8 enhancement.
- **`--quiet` flag** to suppress the precedence stderr line — rejected for D-09 in favor of `2>/dev/null`. Revisit only if scripting users complain.
- **Two separate profile fields** (`output.notes` and `output.artifacts`) — rejected for D-11 in favor of a single `output:` block governing rendered notes only, with build artifacts auto-routed sibling-of-vault. Could become a real need if power users want artifact paths inside the vault.
- **Multi-line precedence-resolution trace block** — rejected for D-09. Revisit if Phase 29's doctor command needs richer reporting (it likely will, but that's doctor's job).
- **`graphify init-profile` scaffolding command** — implied by the D-05 error message, but actual implementation is not part of Phase 27. Capture as a v1.8 candidate or Phase 29 stretch goal.

</deferred>

---

*Phase: 27-vault-detection-profile-driven-output-routing*
*Context gathered: 2026-04-27*
