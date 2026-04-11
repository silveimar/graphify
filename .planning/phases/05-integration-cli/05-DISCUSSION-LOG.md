# Phase 5: Integration & CLI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 05-integration-cli
**Areas discussed:** CLI surface location, Legacy routing strategy, Return type, Dry-run output format, Validate-profile depth

---

## Gray area selection

| Option | Description | Selected |
|--------|-------------|----------|
| CLI surface location | Where --obsidian / --dry-run / --validate-profile actually live: real __main__.py subcommands vs library-only (skill stays the driver). | ✓ |
| Legacy routing strategy | MRG-05 interpretation: branch to old flat to_obsidian() verbatim vs always run new pipeline with default profile. | ✓ |
| Dry-run output format | Summary counts, per-action list, full diff, or JSON. | ✓ |
| Validate-profile depth | Schema only vs schema+templates vs full preflight with path safety. | ✓ |

**User's choice:** All four selected. Module organization explicitly folded into Claude's discretion.

---

## CLI surface location

| Option | Description | Selected |
|--------|-------------|----------|
| Library + skill only | Keep skill as pipeline driver. Add to_obsidian(profile, dry_run) + validate_profile() library calls. __main__.py unchanged. | ✓ |
| Hybrid | validate-profile becomes a real __main__.py subcommand; --obsidian --dry-run stays library-level. | |
| Full CLI pipeline runner | Add `graphify run <path>` as real subcommand orchestrating extract→build→cluster→export. | |
| Defer validate-profile to v2 | Only ship --dry-run in v1. Mark PROF-05 as deferred. | |

**User's choice:** Library + skill only
**Notes:** Matches graphify's existing architecture. Adding a pipeline CLI runner would balloon Phase 5 scope. Non-skill users call `from graphify.export import to_obsidian` directly.

---

## Return type

| Option | Description | Selected |
|--------|-------------|----------|
| Always int, expose MergeResult via kwarg | to_obsidian() returns int always, kwarg switches to MergeResult on demand. Zero test changes. | |
| Always MergeResult, int-castable | MergeResult with __int__ hook. Single return shape, tests stay green via magic. | |
| int for legacy path, MergeResult for profile path | Bifurcated: profile=None returns int (legacy code), profile= returns MergeResult. | ✓ (first pass) |
| You decide at plan time | Pick cleanest at plan time. | |

**User's choice:** int for legacy path, MergeResult for profile path — **superseded** by the Legacy routing choice (see next section). Once legacy code path was deleted, a second Return Type question was asked.

---

## Return type (round 2, after legacy path deletion)

| Option | Description | Selected |
|--------|-------------|----------|
| MergeResult always | Single return contract. Dry-run returns MergePlan; normal returns MergeResult. Union return type. | ✓ |
| MergeResult with __int__ for legacy callers | Safety hook for any stray int() caller. | |
| Still return int, stash plan on side-channel | Awkward dryrun-via-exception or plan_out= parameter. | |

**User's choice:** MergeResult always (recommended)
**Notes:** No __int__ magic. Union return type (MergeResult for writes, MergePlan for dry-run). Tests migrate to assert dataclass shapes.

---

## Legacy routing strategy

**Clarification asked:** User asked whether paths/folder structure are configured in the profile, whether subfolder nesting should be limited, and whether depth factors into efficiency. Answered:
- Folder structure is 100% profile-driven (Phase 1 D-01 `folder_mapping`, Phase 3 D-46 per-rule `then.folder`).
- Subfolder depth has no measurable efficiency impact — `mkdir -p` and filesystem walks are O(files), not O(depth).
- The real depth risk is Windows MAX_PATH (260 chars) — a correctness concern, not a perf one.
- UX degrades past ~4 levels in Obsidian's tree UI (Ideaverse ACE uses 3).

Folded the path-safety concern into the Validate-profile depth discussion.

| Option | Description | Selected |
|--------|-------------|----------|
| Legacy flat code verbatim | Keep existing 240-line body when profile=None. New pipeline only when profile provided. Two code paths. | |
| Auto-discover profile from vault | Sniff vault/.graphify/profile.yaml; use new pipeline if found, legacy if not. | |
| New pipeline always, legacy-shaped default | Delete legacy code. Build _LEGACY_DEFAULT_PROFILE that mimics flat output byte-for-byte. | |
| New pipeline always, break flat shape | Delete legacy code. Always run new pipeline with existing _DEFAULT_PROFILE (Atlas/…). Users see different shape. | ✓ |

**User's choice:** New pipeline always, break flat shape
**Notes:** Cleanest internals. Existing tests get rewritten to assert against MergeResult + Atlas/ paths. Accepted migration cost: pre-profile graphify users see a completely different folder shape. MRG-05 is re-interpreted: "backward compatible" now means "the default profile produces a sensible vault without user config," not byte-for-byte preservation.

---

## Dry-run output format

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped summary + per-action list | Header with counts, then one line per action grouped by action type. | ✓ |
| Summary only | Action counts only, no per-file list. Defeats dry-run purpose. | |
| Full diff per UPDATE | Summary + list + field/block diffs per UPDATE. Very verbose. | |
| JSON output | dataclasses.asdict to stdout. Pipeable, not human-friendly. | |

**User's choice:** Grouped summary + per-action list (recommended)
**Notes:** Ship as `format_merge_plan(plan) -> str` library helper in `merge.py`. Skill calls the formatter; future CLI reuses it. No JSON or verbose mode in v1 (deferred).

---

## Validate-profile depth

| Option | Description | Selected |
|--------|-------------|----------|
| Schema only | Call existing Phase 1 validate_profile(). Fastest, narrowest. | |
| Schema + templates + dead rules | Also validate .graphify/templates/*.md and detect dead mapping rules. | |
| Full preflight (schema + templates + rules + path safety) | Everything above PLUS Windows path-length warning + slow regex flag. | ✓ |
| Schema + templates only | Middle ground, skip dead-rule detection. | |

**User's choice:** Full preflight
**Notes:** Returns (errors, warnings) tuple. Errors block exit 1; warnings surface but exit 0. Path safety uses 240-char threshold (20-char headroom under Windows MAX_PATH 260 with 200-char filename).

---

## Continue or finalize

| Option | Description | Selected |
|--------|-------------|----------|
| Ready — write CONTEXT.md | Close loop, write CONTEXT.md, auto-advance to plan. | ✓ |
| Module organization | Discuss export.py vs new integration.py. | |
| apply_merge_plan partial failure policy | Discuss abort-vs-continue on per-action write failures. | |
| Skill.md update + test migration | Discuss skill update scope and test file strategy. | |

**User's choice:** Ready — write CONTEXT.md
**Notes:** All three unselected candidates captured as Claude's Discretion entries in CONTEXT.md:
- Module organization → export.py (stays put, no new module for v1)
- Partial failure → continue-on-failure with MergeResult.failures field
- Skill update → mechanical edit across 7 platform variants; test migration via new test_integration.py

---

## Claude's Discretion

Areas where the user deferred to Claude at plan time (captured in CONTEXT.md):
- Module organization: refactored to_obsidian() stays in export.py
- apply_merge_plan partial-failure policy: continue-on-failure, MergeResult.failures field
- format_merge_plan location: graphify/merge.py
- Skill update scope: minimal edit to L485–509 + 6 platform variants
- Test fixture strategy: new tests/test_integration.py, FIX-01/02/03 invariants carried over
- profile.load_profile fallback semantics: decide after reading Phase 1 signature

## Deferred Ideas

See CONTEXT.md `<deferred>` section. Highlights:
- `graphify run` pipeline CLI subcommand
- `graphify validate-profile` standalone CLI subcommand
- --verbose dry-run with full diffs
- JSON dry-run output
- Windows long-path opt-in
- Overly-slow regex static analysis
- Platform-variant skill sync automation
- MergeResult.failures surfacing in GRAPH_REPORT.md
