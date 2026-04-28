# Phase 28: Self-Ingestion Hardening - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Re-running graphify inside (or near) a vault must never re-ingest its own previous output, across three independent failure surfaces:

1. **Profile-aware exclusion (VAULT-11)** — `detect.py` reads the resolved output destination from Phase 27's `ResolvedOutput` AND a new `output.exclude:` glob list from `profile.yaml`, and prunes both from the input scan.
2. **Recursive nesting guard (VAULT-12)** — `detect.py` refuses to ingest paths matching `**/graphify-out/**` (and any user-renamed output dir basename) at any depth, with a single summary warning per run.
3. **Manifest-based ignore (VAULT-13)** — Each run writes an `output-manifest.json` listing root output dirs + every file written; subsequent runs read it to skip prior outputs even when the user renamed `profile.output.path` between runs.

**Out of scope** (other v1.7 phases own these):
- `graphify doctor` command + `--dry-run` preview → Phase 29
- Profile composition (`extends:`/`includes:`) → Phase 30
- Conditional / loop template syntax → Phase 31

**Carried in from Phase 27 (locked, do not re-discuss):**
- `ResolvedOutput` NamedTuple (`vault_detected`, `vault_path`, `notes_dir`, `artifacts_dir`, `source`) is the integration contract — `detect.py` consumes it directly. (D-13)
- `notes_dir` governs rendered Obsidian markdown only; `artifacts_dir` is sibling-of-vault and holds machine artifacts (cache, graph.json, manifests). (D-11)
- Strict CWD-only `.obsidian/` detection. (D-04)
- v1.0 backcompat default: no vault → `Path("graphify-out/obsidian")` + `Path("graphify-out")`. (D-12)
- The recent quick-fix already prunes literal `graphify-out/` from the default scan via `_SELF_OUTPUT_DIRS`; Phase 28 generalizes and supersedes it.

</domain>

<decisions>
## Implementation Decisions

### Profile schema — exclusion globs (VAULT-11)

- **D-14: Co-location.** Exclusion globs live under the existing `output:` block as `exclude: list[str]`, alongside `mode` and `path`. `ResolvedOutput` grows a sixth field `exclude_globs: tuple[str, ...]` (use `tuple` for immutability — NamedTuple-friendly). Single integration surface for `detect.py`. Add `exclude` to the `output:` schema branch in `validate_profile()`.
- **D-15: Always-on application.** `output.exclude` globs apply whenever the profile is loaded and validates — including when `--output` flag overrides the destination. The `--output` precedence (D-08) governs *destination* only; *exclusions* are a separate, additive guarantee.
- **D-16: Glob syntax.** Use the existing `fnmatch`-based `_is_ignored()` matcher at `detect.py:307`. Stdlib-only, already battle-tested in `.graphifyignore` handling. Patterns like `**/cache/**`, `*.tmp`, `private/*.md` work as-is. Honors PROJECT.md's "no new required deps" constraint.
- **D-17: Strict validation.** `validate_profile()` rejects malformed `exclude` entries: empty strings, non-string types, paths that escape vault root via traversal (e.g., `/etc/*`, `../../*`). Loud-fail at profile-load time, consistent with D-05/D-02 pattern. No silent skipping.

### Recursive nesting guard (VAULT-12)

- **D-18: Match set.** Guard matches the union of `_SELF_OUTPUT_DIRS = {"graphify-out", "graphify_out"}` AND the basenames of `resolved.notes_dir` and `resolved.artifacts_dir` when they differ from the literal set. Catches v1.0 nesting bug AND user-renamed-output nesting via one match function. Single source of truth derived from Phase 27's contract.
- **D-19: Warn-and-skip, not fatal.** When nesting is detected, prune from scan and continue; do NOT raise SystemExit. Cleanup is explicitly delegated to Phase 29's `graphify doctor`. Rationale: a fatal error would block all graphify commands once nesting exists on disk, even commands the user might run *to* clean up.
- **D-20: One summary line per run.** Aggregate skipped nesting paths during scan; emit a single `[graphify] WARNING: skipped N nested output paths (deepest: <path>)` at end of detect, not per-file or per-root. Matches `[graphify]`-prefixed stderr convention from `build.py` / `cluster.py`.
- **D-21: Universal scope.** Guard applies whether or not a vault is detected. Recovery from the v1.6 self-ingestion bug (already partially fixed in the quick-fix) needs to work for users running `graphify` from any directory, not just vault-CWD. v1.0 backcompat is preserved because the *default* paths still resolve identically per D-12 — the guard only refuses already-pathological nesting.

### Output manifest design (VAULT-13)

- **D-22: New dedicated file.** Write `<resolved.artifacts_dir>/output-manifest.json` — separate from the existing `graphify-out/manifest.json` (which serves `detect_incremental()` for mtime tracking). Separation of concerns: input scan state vs. output write history. Independent schema versioning. Existing manifest readers untouched.
- **D-23: Both granularities.** Schema:
  ```json
  {
    "version": 1,
    "runs": [
      {
        "run_id": "<utc-iso8601>-<short-hash>",
        "timestamp": "<utc-iso8601>",
        "notes_dir": "<absolute-path>",
        "artifacts_dir": "<absolute-path>",
        "files": ["<absolute-path>", ...]
      }
    ]
  }
  ```
  Roots enable cheap directory-prefix prune in `detect.py`; full file list enables precise re-run skipping when only `notes_dir` was renamed (the VAULT-13 #4 case).
- **D-24: Rolling N=5 history.** `runs: []` capped at 5 most recent entries. Old entries dropped FIFO on each write. Covers the common rename-once-or-twice case without unbounded growth. Not user-tunable in v1.7; if power users need more, revisit in v1.8.
- **D-25: Failure-mode behavior.** Missing manifest → silent (expected for first-ever invocation); malformed JSON → `[graphify] WARNING: output-manifest.json unreadable, ignoring history` and proceed with empty history. The literal-name + ResolvedOutput-aware nesting guard (D-18) is the safety net for any case the manifest can't cover.

### Cross-run renamed-output recovery (VAULT-13 #4)

- **D-26: Stable manifest anchor.** `detect.py` always reads `<resolved.artifacts_dir>/output-manifest.json` to find prior runs. `artifacts_dir` is sibling-of-vault per D-11 — stable across `notes_dir` renames in profile.yaml. If `artifacts_dir` itself is changed (currently auto-derived, not profile-controlled in v1.7), the literal nesting guard still catches orphans.
- **D-27: Silent skip of renamed-out content.** When prior-run `notes_dir` differs from current `resolved.notes_dir`, files listed under the old run's `files:` array are silently pruned from the input scan. No warning — rename is a normal user action, not a misconfiguration. Phase 29's doctor command can surface stale outputs explicitly.
- **D-28: Manifest GC on write.** When a manifest entry's listed file no longer exists on disk, drop it from that run's `files:` array on the next manifest write. Mirrors the `deleted_files` cleanup pattern already in `detect_incremental()` at `detect.py:503`. Bounded by the rolling N=5 cap.
- **D-29: Atomic write timing.** Manifest is written only after successful export — after `export.to_obsidian()` and all artifact writers complete cleanly. Use tmp+rename atomic write (matches Phase 24's read-merge-write hardening). Failed runs leave the manifest unchanged so the next run sees prior state, not a half-written record.

### Claude's Discretion

- Exact `run_id` hash construction (e.g., short SHA-256 of `notes_dir + timestamp`, or just a UUID4) — planner picks.
- Exact module location of nesting-detection function (extend `_is_noise_dir` vs. new `_is_nested_output` predicate) — planner picks; must be a single import surface for tests.
- Exact `__main__.py` wire-point for the post-export manifest write — likely a small helper called from the run/--obsidian branches after their existing write paths complete; planner picks.
- Whether `output-manifest.json` is exposed via MCP `serve.py` (Phase 28-2 stretch) — out of scope unless the planner finds it trivially free; otherwise defer.
- Test fixture strategy for nesting scenarios — pure `tmp_path` per CLAUDE.md conventions; planner designs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 28 inputs (decisions locked outside this discussion)
- `.planning/phases/27-vault-detection-profile-driven-output-routing/27-CONTEXT.md` — D-04, D-08, D-11, D-12, D-13 (the integration contract this phase consumes)
- `.planning/phases/27-vault-detection-profile-driven-output-routing/27-02-SUMMARY.md` — `ResolvedOutput` API + behavior matrix as shipped
- `.planning/notes/obsidian-export-self-ingestion-loop.md` — root cause analysis from the v1.6 bug; explains *why* this phase exists
- `.planning/notes/folder-architecture-graphify-out-vs-vault.md` — folder architecture context (notes_dir vs. artifacts_dir reasoning)
- `.planning/notes/v1.7-input-vault-adapter-no-source-mirroring.md` — locks "no source-path mirroring fallback" (relevant because export still mirrors `source_file`; Phase 28 must prevent that mirror from re-ingesting)
- `.planning/REQUIREMENTS.md` (v1.7) — VAULT-11, VAULT-12, VAULT-13
- `.planning/ROADMAP.md` §"Phase 28: Self-Ingestion Hardening" — success criteria

### Phase 27 deliverables (read-only consumers)
- `graphify/output.py` — `ResolvedOutput`, `is_obsidian_vault()`, `resolve_output()` (the integration surface; do not modify in Phase 28 except to extend `ResolvedOutput` with `exclude_globs` per D-14)
- `graphify/profile.py` — `_VALID_TOP_LEVEL_KEYS`, `_VALID_OUTPUT_MODES`, `validate_profile()`, `validate_sibling_path()` (extend the `output:` schema branch with `exclude` validation per D-14/D-17)
- `graphify/__main__.py` — `--output` flag wiring at lines 1327 (`--obsidian` branch) and 2142 (run branch); manifest write call sites land in the same two branches per D-29

### Modification surfaces (this phase changes these)
- `graphify/detect.py` — primary surface:
  - `_SELF_OUTPUT_DIRS` (line 252) → expand or supersede via D-18 match function
  - `_is_noise_dir()` (line 261) → consume `ResolvedOutput` for D-18
  - `_load_graphifyignore()` / `_is_ignored()` (lines 275, 307) → reuse fnmatch matcher for D-16 `output.exclude`
  - `detect()` (line 338) → add nesting-guard summary emission per D-20
  - new helpers: `_load_output_manifest()`, `_save_output_manifest()`, `_is_known_prior_output()` per D-22..D-29
- `graphify/profile.py` — extend `output:` schema branch with `exclude:` validation per D-14/D-17
- `graphify/output.py` — `ResolvedOutput` grows `exclude_globs: tuple[str, ...]`; `resolve_output()` populates it from the loaded profile

### v1.0 / v1.5 / v1.6 foundations (read for pattern fidelity)
- `.planning/milestones/v1.0-REQUIREMENTS.md` — original profile schema decisions
- Phase 24 (manifest writer audit + atomic read-merge-write hardening) — apply the same atomic write pattern for D-29
- `graphify/security.py` — path-traversal validators referenced by D-17

### Codebase intel maps
- `.planning/codebase/STRUCTURE.md` — module layout
- `.planning/codebase/CONVENTIONS.md` — `from __future__ import annotations`, type hints, naming
- `.planning/codebase/INTEGRATIONS.md` — CLI ↔ profile loader ↔ pipeline interactions

### Project-level constraints
- `CLAUDE.md` (project) — Python 3.10+ on CI 3.10/3.12; no new required deps; pure unit tests; backward compat
- `SECURITY.md` — path confinement model; D-17 traversal rejection inherits this

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`graphify/detect.py:_load_graphifyignore` / `_is_ignored` (lines 275, 307)** — `fnmatch`-based glob matcher already in production. D-16 reuses it directly for `output.exclude` evaluation; no new matcher.
- **`graphify/detect.py:_SELF_OUTPUT_DIRS` (line 252) and `_is_noise_dir()` (line 261)** — current literal-match implementation. Phase 28 extends both to consume the basenames of `resolved.notes_dir` and `resolved.artifacts_dir` for D-18.
- **`graphify/detect.py:save_manifest()` / `load_manifest()` (lines 448, 456)** — existing atomic-ish write pattern (parent.mkdir + write_text). Phase 24's atomic write pattern (tmp+rename) is the upgrade target for D-29.
- **`graphify/detect.py:detect_incremental()` deleted-files cleanup (line 503)** — established pattern for "manifest entry's file no longer exists, drop it." D-28 mirrors this.
- **`graphify/profile.py:_VALID_OUTPUT_MODES` and `output:` schema branch in `validate_profile()`** — Phase 27's schema landing zone. Phase 28 extends this branch with `exclude` validation.
- **`graphify/output.py:ResolvedOutput` (NamedTuple)** — Phase 27's integration contract. Phase 28 grows it by one field (`exclude_globs`); existing 5 fields untouched.
- **Phase 24 atomic read-merge-write helpers** — reuse for D-29 manifest writes.

### Established Patterns
- **`[graphify]`-prefixed stderr** for warnings (build.py, cluster.py) — D-20 nesting summary follows this.
- **Validate-first, fail-loudly** — `validate_profile()` returns `list[str]` errors; D-17 follows this.
- **Function-local imports avoid circular deps** — `output.py` already imports `profile.load_profile` lazily; Phase 28 keeps this pattern when `detect.py` needs `ResolvedOutput`.
- **Tuple-based immutable state in NamedTuples** — D-14 uses `tuple[str, ...]` for `exclude_globs` to keep `ResolvedOutput` hashable/frozen.
- **Atomic tmp+rename writes** (Phase 24) — D-29.
- **Argparse-free manual flag loop** in `__main__.py` — no new flags this phase, but consistent with the loaded profile-flow.

### Integration Points
- **`graphify/output.py:resolve_output()`** — populates `exclude_globs` from `prof["output"].get("exclude", [])` after profile load. Tuple-cast at construction.
- **`graphify/detect.py:detect()`** — accepts (or fetches via a small helper) the `ResolvedOutput` produced upstream. Two new behaviors: (a) prune `output.exclude` globs + nesting matches from `_is_noise_dir` walk; (b) load `output-manifest.json` from `resolved.artifacts_dir` and prune known prior outputs.
- **`graphify/__main__.py` run branch (~line 2142) and `--obsidian` branch (~line 1327)** — call `_save_output_manifest()` after successful export, before exit. Atomic write per D-29.
- **`graphify/serve.py` (MCP)** — out of scope; if the manifest needs an MCP query surface in the future, it lands in a Phase 29+ ticket, not here.

### Test Coverage Targets (planner notes)
- Profile schema: malformed `exclude` rejection, valid glob acceptance, traversal rejection (D-17).
- Detect: literal-graphify-out nesting + renamed-output nesting both pruned, single summary line emitted (D-18, D-20); `output.exclude` globs honored (D-15, D-16); applies with and without vault detected (D-21).
- Manifest: atomic write, missing-file silent fallback, malformed-JSON warn-once fallback, rolling N=5 cap, GC of stale file entries, renamed `notes_dir` recovery (D-22..D-29).
- Integration: full run-then-rerun cycle from `tmp_path` reproducing the v1.6 self-ingestion bug shows it cannot recur post-Phase-28.

</code_context>

<specifics>
## Specific Ideas

- The user accepted every recommended option in all four areas; the recommendations are the specifics.
- Anchor wording: "exclude under output:", "ResolvedOutput-aware nesting", "rolling N=5 manifest", "warn-and-skip not fatal", "manifest at artifacts_dir as stable anchor".
- The phase's success-criterion #4 (renamed output between runs) is satisfied by the D-26 + D-27 pair: stable artifacts_dir anchor + silent skip of prior `files:` listings.
- Phase 28 deliberately does NOT change `notes_dir`/`artifacts_dir` resolution — it consumes Phase 27's contract.

</specifics>

<deferred>
## Deferred Ideas

- **`--exclude` CLI flag** mirroring `--output` for power-user override of profile globs — rejected for D-15 in favor of always-applied profile-side globs. Revisit if scripting users complain.
- **Profile field for `output.manifest_history_depth`** — rejected for D-24 in favor of fixed N=5. Add only if real users need tuning.
- **Profile field for `output.manifest_path:`** — rejected for D-26; artifacts_dir is the stable anchor without new schema.
- **MCP query surface for `output-manifest.json`** — out of scope this phase. Reasonable Phase 29 (doctor) or v1.8 ticket if needed.
- **Two separate manifest files** at notes_dir AND artifacts_dir for redundancy — rejected for D-22 in favor of single artifacts_dir file. Revisit if users frequently delete artifacts_dir manually.
- **Per-file warning** on nesting detection — rejected for D-20 in favor of one summary line.
- **Fatal-on-malformed-manifest** behavior — rejected for D-25 in favor of warn-once-and-empty. Less hostile to recovery scenarios.
- **`graphify init-profile` scaffolding** to write a starter `output:` block with sensible `exclude:` defaults — implied by the profile authoring UX but not part of Phase 28. Capture as Phase 29 stretch goal or v1.8 candidate.
- **Discoverable manifest via filesystem walk** — rejected for D-26 in favor of fixed location. Adds expense and ambiguity.
- **Pre-write manifest** (record intended outputs before writing) — rejected for D-29 in favor of post-export atomic write. Correctness wins over crash-resilience here.

</deferred>

---

*Phase: 28-self-ingestion-hardening*
*Context gathered: 2026-04-27*
