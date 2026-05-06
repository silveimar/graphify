# Phase 63 — VOPT: Vault Option B Silent Reroute & `--explain-paths`

**Created:** 2026-05-05
**Milestone:** v1.13
**Requirements:** VOPT-01, VOPT-02, VOPT-03

## Domain

When graphify runs from inside an Obsidian vault that has no `.graphify/profile.yaml`, output is silently rerouted to a hidden `.graphify-out/` inside the vault, every such run emits exactly one informational stderr breadcrumb explaining the reroute, and a new `--explain-paths` flag prints the resolved output paths and active vault profile (if any) without running the pipeline.

This phase fits into the **legacy-default slot** of the precedence chain locked in Phase 70.1:
`--output > profile.output > --obsidian-dir > legacy default`.

## Canonical Refs

- `.planning/ROADMAP.md` — Phase 63 goal & success criteria (lines starting at "Phase 63: VOPT")
- `.planning/REQUIREMENTS.md` — VOPT-01, VOPT-02, VOPT-03 definitions
- `.planning/phases/70.1-vfix-nested-vault-folder-bug-and-output-obsidian-dir-profile/70.1-CONTEXT.md` — established precedence chain that Option B slots into
- `.planning/phases/70-vrsync-vault-input-reverse-sync-user-file-augmentation/70-CONTEXT.md` — vault-detection conventions (`.obsidian/` presence)
- `graphify/__main__.py` — CLI entrypoint where `--obsidian-dir`, `--output`, and (new) `--explain-paths` flags live, and where the Option B reroute branch must be added before the pipeline dispatches
- `graphify/output.py` (function `default_graphify_artifacts_dir()`) — non-vault default that must remain unchanged
- `graphify/security.py` — path confinement rules; the new `.graphify-out/` path must satisfy them

## Decisions

### D-01 — Breadcrumb format (VOPT-02)
Two-line `[graphify] info: / hint:` shape, mirroring the Phase 64 stderr contract. Exact wording:

```
[graphify] info: vault CWD without .graphify/profile.yaml — Option B reroute active
  hint: outputs → <abs path>/.graphify-out/
```

When a legacy `graphify-out/` is also present, append a third line:
```
  hint: legacy graphify-out/ detected — run `graphify doctor` to review
```

Phase 64 (AUDIT-A) will need to extend its valid-prefix list from `error:` to `error: | info:` when locking the snapshot.

### D-02 — Trigger precedence for Option B (VOPT-01)
Strict trigger. Option B fires **only** when ALL are true:
1. CWD contains `.obsidian/`
2. CWD does not contain `.graphify/profile.yaml`
3. CLI invocation does not pass `--output`
4. CLI invocation does not pass `--obsidian-dir`

Any explicit path flag (`--output` or `--obsidian-dir`) suppresses Option B and routes through the higher-precedence layers from 70.1's chain. This keeps Option B as the last fallback before `default_graphify_artifacts_dir()`.

### D-03 — `--explain-paths` output format (VOPT-03)
Plain-text key:value rows on **stdout**, exit code 0, pipeline does **not** run. Output shape:

```
cwd:           <abs cwd>
vault:         yes|no  (.obsidian/ present)
profile:       <abs path to .graphify/profile.yaml>  |  <none>
resolved out:  <abs output dir>
resolution:    flag-output | flag-obsidian-dir | profile | option-b (silent reroute) | default
```

JSON output is deferred — can be layered later as a `--json` overlay if scripting need emerges. Skill files that need machine-readable form can grep the key:value rows.

### D-04 — Legacy `graphify-out/` handling
Detect-only. If `<vault>/graphify-out/` (visible, legacy from pre-v1.13) coexists with the new `.graphify-out/`, the breadcrumb appends a third `hint:` line pointing at `graphify doctor`. **No move, no delete, no migration.** Phase 70.1's no-delete posture for legacy folders holds. (Phase 69 VPROF-04's `update-vault --migrate-legacy` remains the only pathway that ever relocates legacy artifacts, and it stays opt-in.)

## Code Context

- **Reusable assets:**
  - `default_graphify_artifacts_dir()` in `graphify/output.py` — non-vault path, must not change
  - `[graphify]` stderr formatter pattern (search `__main__.py` for existing `print(... file=sys.stderr)` calls) — replicate two-line shape
  - Vault detection by `.obsidian/` directory presence — already used by `vault_promote.py` and Phase 70 reverse-sync code paths
  - `ResolvedOutput` namedtuple-or-dataclass referenced in CLAUDE.md for routing decisions (`source == "default"` vs vault) — extend with `"option-b"` source label
- **Integration points:**
  - CLI argparse setup in `graphify/__main__.py` — add `--explain-paths` (action=store_true) at the same level as `--output`/`--obsidian-dir`
  - Path-resolution helper that today returns the resolved output dir — extend to also return a `resolution` source label so `--explain-paths` can report it without a second pass
- **Tests to mirror:** `tests/test_output.py`, plus the routing-audit tests CLAUDE.md mentions must not regress for non-vault CWDs

## Deferred Ideas

- **JSON output for `--explain-paths`** — add `--json` flag if/when skill files or CI scripts need it. Not in Phase 63.
- **Auto-migration of legacy `graphify-out/`** — out of scope. Belongs in `graphify doctor` / `update-vault --migrate-legacy` (Phase 69 VPROF-04 territory).
- **Dot-prefix override** (e.g., `--vault-out-dir-name .my-graph/`) — speculative; nobody asked. Stays default `.graphify-out/`.

## Acceptance Criteria (from ROADMAP.md)

1. Vault CWD with `.obsidian/` and no profile writes outputs under `<vault>/.graphify-out/` (not legacy `graphify-out/`).
2. Every Option B run emits exactly one two-line `[graphify] info: / hint:` stderr breadcrumb (plus an optional third `hint:` line when legacy `graphify-out/` is detected).
3. `graphify --explain-paths` prints the plain-text resolution table to stdout and exits 0 without running the pipeline.
4. Non-vault CWDs continue to use `default_graphify_artifacts_dir()` — existing routing-audit tests pass unchanged.

## Downstream Notes

- **Researcher:** Confirm where in `__main__.py` the path-resolution branch currently dispatches; identify whether to extend an existing helper or introduce `resolve_option_b()`. Verify Phase 64's snapshot test will accept `info:` as a second valid prefix.
- **Planner:** Likely 3 plans — (a) trigger detection + reroute + breadcrumb, (b) `--explain-paths` flag + resolution-source labeling, (c) legacy-detection hint line + tests. RED-first regression matrix in `tests/test_output_path_matrix.py` (already established by Phase 70.1) is the natural home for Option B coverage.
