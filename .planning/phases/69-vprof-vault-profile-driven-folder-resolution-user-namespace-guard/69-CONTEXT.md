# Phase 69: VPROF — Vault Profile-Driven Folder Resolution & User-Namespace Guard - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace hardcoded `Atlas/...` write paths in `graphify/vault_promote.py` with profile-driven resolution under `Atlas/Sources/Graphify/<type>/`, refuse writes that would land under `profile.user_only_folders` pre-flight, and surface/migrate legacy graphify-shaped artifacts via `graphify doctor` + `graphify update-vault --migrate-legacy`.

**In scope (Phase 69):**
- Profile schema v2 keys: `input_path`, `vault_path`, `graphify_folder_mapping`, `user_only_folders`, `augment.allow_community`, `reverse_sync.{mode,memory_path,auto_on_run}`.
- One-shot `folder_mapping` → `graphify_folder_mapping` migrator (silent in-place rewrite).
- Removal of hardcoded `folder = "Atlas/..."` literals at `vault_promote.py:206-299` and `_DEFAULT_LAYERS` at `vault_promote.py:873-879`.
- Pre-flight refusal of writes that target `user_only_folders` (refusal half of VPROF-03).
- `graphify doctor` legacy-artifact section + `graphify update-vault --migrate-legacy` (dry-run + `--apply`).
- Manifest-hash overwrite guard at `vault_promote.py:702-732` is preserved with a regression test.

**Explicitly NOT in this phase (deferred to Phase 70):**
- Frontmatter-augmentation merge contract (augmentation half of VPROF-03).
- `graphify reverse-sync` command, modes (`always_ask`/`never_copy`/`always_copy`), JSONL diff memory.
- `auto_on_run` integration with `graphify run` / `update-vault`.

</domain>

<decisions>
## Implementation Decisions

### Folder mapping defaults
- **D-01:** `graphify_folder_mapping` defaults mirror Ideaverse's plural-capitalized vault convention. Concrete defaults:
  ```yaml
  graphify_folder_mapping:
    thing:     Atlas/Sources/Graphify/Things/
    question:  Atlas/Sources/Graphify/Questions/
    map:       Atlas/Sources/Graphify/Maps/
    person:    Atlas/Sources/Graphify/People/
    quote:     Atlas/Sources/Graphify/Quotes/
    statement: Atlas/Sources/Graphify/Statements/
    source:    Atlas/Sources/Graphify/Sources/
  ```
- **D-02:** The `map` record type stays named `Maps/` (not `MOCs/` or `Communities/`). The `Atlas/Sources/Graphify/` parent path disambiguates from user-owned `Atlas/Maps/` — there is no path collision.
- **D-03:** Lookup keys are **singular nouns** (`thing`, `question`, `map`, `person`, `quote`, `statement`, `source`). The internal result-dict keys (`things`, `questions`, ...) are translated to singular config keys via a small mapping. Singular reads more naturally in YAML.
- **D-04:** Unknown record types (future additions like `concept`) **fall back to `Atlas/Sources/Graphify/<Type>/`** (capitalized first letter, plural). The fallback stays inside the safe pinned subtree. A one-line stderr note at INFO suggests adding the key to the profile. Never silently drop; never refuse — refusal is reserved for `user_only_folders` violations.

### Profile migrator UX
- **D-05:** **Silent in-place rewrite** of `profile.yaml` on first read of a v1 profile. The migrator renames `folder_mapping` → `graphify_folder_mapping` and writes the result back to the same path. Idempotent: if `graphify_folder_mapping` is already present, no rewrite occurs.
- **D-06:** A single `profile.yaml.bak` is written alongside before each rewrite. The `.bak` always reflects the *previous* state immediately before the latest migration. Subsequent migrations overwrite the same `.bak` (no `.bak.bak` accumulation, no timestamped variants).
- **D-07:** The migrator is the only graphify code path that writes to the user's `.graphify/` directory in this phase. All other writes still target `Atlas/Sources/Graphify/<type>/` per D-01.
- **D-16 (added 2026-05-05 post-research):** `user_only_folders` defaults to `[]` (empty list — opt-in). graphify cannot know which folders a given vault treats as user-owned without the user's input; an empty default avoids false-refusals on non-Ideaverse vaults. Users declare `user_only_folders` in their `profile.yaml`. The Ideaverse-specific list (`Atlas/`, `Calendar/`, `Efforts/`, `+/`, `x/`, vault root) is documented as the recommended user-side configuration but ships nowhere as a hardcoded default.

### Refusal pre-flight scope
- **D-08:** **Defense in depth — pre-flight pass + chokepoint guard.**
  - Pre-flight pass: before any writes occur, every resolved target path is validated against `profile.user_only_folders`. ALL violations are collected and surfaced together in one error message.
  - Chokepoint guard: a single `_write_record(record_type, ...)` helper routes all vault writes through `_resolve_target_path(record_type, profile)` followed by `_assert_under_pinned_subtree(path, profile)`. New record types or call sites added later cannot bypass the check.
- **D-09:** **Atomic batch refusal.** When the pre-flight pass finds any refused target, the entire run aborts with non-zero exit and **zero partial writes**. This matches VPROF-03 / Phase 69 success criterion #3 ("no partial writes occur") literally.
- **D-10:** Refusal stderr format follows the v1.12 two-line convention:
  ```
  [graphify] error: refused N write(s) targeting user-owned folders
    hint: <actionable guidance — list every offending target with its mapped record_type and the user_only_folders rule it violated; suggest editing graphify_folder_mapping>
  ```
- **D-11:** The manifest-hash overwrite guard at `vault_promote.py:702-732` is preserved untouched. The new pre-flight runs **before** the manifest-hash check (refuse user-namespace violations first; manifest-hash is a separate within-pinned-subtree safety net). A regression test simulates a name collision under the pinned subtree to prove the manifest-hash guard still fires.

### doctor + migrate-legacy semantics
- **D-12:** **Hardcoded glob list** for legacy detection — deterministic, zero false positives. Initial pattern set:
  - `_COMM*.md` at vault root
  - `Community*.md` under `Atlas/Maps/`
  - Any file outside `Atlas/Sources/Graphify/` carrying the `graphify_manifest_hash` frontmatter key (catches manifest-tagged outputs that escaped the pinned subtree)
  Pattern list lives in a single module-level constant so it's trivially extensible as new legacy shapes surface.
- **D-13:** **`graphify update-vault --migrate-legacy` is dry-run by default.** The flag prints the move plan (`old_path → new_path` per file) to stdout and exits without touching files. **`--migrate-legacy --apply`** performs the moves. This matches the safety stance for the only graphify command that touches user-owned vault space outside the pinned subtree.
- **D-14:** **In-place manifest update during migrate.** Each move updates the manifest's path entry for that file atomically (move + manifest write together; rollback the move if the manifest write fails, and vice versa). The manifest-hash overwrite guard stays intact for future runs. No stale-manifest window; no full rebuild.
- **D-15:** `graphify doctor`'s legacy-artifact section runs by default (read-only — detection only, no writes without `--migrate-legacy --apply`). Exit code semantics: doctor exits non-zero if blocking issues are found (consistent with existing `graphify doctor` behavior); legacy-artifact findings are reported as a non-blocking warning section unless explicitly elevated by future flags.

### Claude's Discretion
- Exact wording of the `[graphify] error:` + `  hint:` strings (D-10) — Claude may iterate during planning/implementation as long as the two-line format and content (offending targets, mapped record types, violated rule, suggested action) are present.
- The internal name of the singular→plural translation helper (D-03).
- The exact location of the legacy pattern constant (D-12) — `vault_promote.py` module-level vs. a small `_legacy_patterns.py` — planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 69" — goal, depends-on, requirements, 6 success criteria.
- `.planning/REQUIREMENTS.md` §VPROF (lines 41–45) — VPROF-01 (schema v2 + migrator), VPROF-02 (folder resolution + literal removal), VPROF-03 (refusal half + manifest-hash preservation), VPROF-04 (legacy detection + migration).
- `.planning/PROJECT.md` — Ideaverse Integration mandate; "All generated files belong under `Atlas/Sources/Graphify/`" (project scope rule).

### Bug epicenter (read these — they define the literals to remove)
- `graphify/vault_promote.py:195-300` — the hardcoded `folder = "Atlas/..."` literals across the 7 record-type classifiers (things/questions/maps/people/quotes/statements/sources).
- `graphify/vault_promote.py:702-732` — manifest-hash overwrite guard (PRESERVE; cover with regression test).
- `graphify/vault_promote.py:873-879` — `_FOLDER_PATH_PREFIX` dict (the actual symbol name in code; CONTEXT originally used the alias `_DEFAULT_LAYERS`). REMOVE; replaced by profile-derived mapping via `_resolve_folder_prefix()`.

### Convention contracts
- `CLAUDE.md` §Security and §"All external input passes through graphify/security.py" — path confinement convention; the new pre-flight reuses this discipline.
- `.planning/codebase/CONVENTIONS.md` — `[graphify]` two-line stderr format (`error:` / `  hint:`) — locked by AUDIT-02 sweep planned for Phase 64; Phase 69's refusal messages MUST conform.
- `.planning/codebase/ARCHITECTURE.md` — pipeline stage separation; `vault_promote.py` is the export-stage chokepoint that this phase hardens.

### Adjacent phase coordination
- Phase 70 (`VRSYNC`) depends on Phase 69's profile schema v2 and `user_only_folders` contract being settled. Augmentation half of VPROF-03 lives there — do NOT implement frontmatter merge in Phase 69.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`graphify/security.py`** — path-confinement validators already exist for `graphify-out/`. The new `_assert_under_pinned_subtree(path, profile)` follows the same pattern (resolve, check `is_relative_to` against the allowed root, raise on mismatch).
- **`graphify/cache.py`** — SHA256 hashing primitive; not used in Phase 69 itself but Phase 70's reverse-sync hashes will reuse it (mentioned to keep the contract aligned).
- **`graphify/__main__.py`** — existing `[graphify]` stderr formatter helpers (used by `update-vault`, `vault-promote`, `doctor` commands) — refusal messages plug into the same printer.
- **YAML loader for profile** — already optional via PyYAML (`pyproject.toml` extra). Migrator code reuses it; no new dependency.

### Established Patterns
- **Single chokepoint for write side effects** — `vault_promote.py` is already the one module that writes to the vault. D-08's `_write_record()` helper formalizes a pattern that's implicit in the current code.
- **Read-only validators return list of errors** — `validate.py` returns `list[str]` instead of raising on first error. The refusal pre-flight follows the same shape: collect all violations, present them together (D-08, D-09).
- **Idempotent migrators** — graphify already prefers idempotent operations (extract cache, install command). Profile migrator follows suit (D-05).
- **Dry-run + `--apply` for destructive operations** — graphify currently has no destructive commands; D-13 establishes this pattern for `--migrate-legacy` and sets precedent for future destructive work.

### Integration Points
- `graphify update-vault` and `graphify vault-promote --write-into-vault` (the two commands in scope per ROADMAP) both flow through `vault_promote.py`. The `_write_record()` chokepoint sits at the seam between path resolution and disk write.
- `graphify doctor` is a separate command in `__main__.py` — adds a new section that calls a new `_detect_legacy_artifacts(profile, vault_path)` function in `vault_promote.py`.
- Profile read happens early in both commands — that's where the migrator hooks in (read → if v1 detected, migrate in-place + write `.bak` → return v2 dict).

</code_context>

<specifics>
## Specific Ideas

- The bug we're fixing was diagnosed in memory observations 5421–5425, 5432, 5438. The user has already lived with the consequence: community MOC files written to `Atlas/Maps/` instead of `Atlas/Sources/Graphify/Maps/`, polluting their user-curated maps folder.
- The user explicitly chose the *plural-capitalized Ideaverse-style* names (D-01) because the vault should "feel native" when graphify writes into it.
- The `Maps/` (not `MOCs/`) decision (D-02) was deliberate: the `Atlas/Sources/Graphify/` parent path is doing the disambiguation work; users browsing the vault tree see consistent plural-capitalized folders inside the Graphify-owned subtree.
- Defense-in-depth (D-08) was chosen over a single mechanism specifically because this is a regression-fix phase — the user wants structural enforcement that a future writer cannot accidentally re-introduce the bug.

</specifics>

<deferred>
## Deferred Ideas

- **Frontmatter augmentation contract** (allowlist-merge of `related_to`, `up`, `tags`, `comments`, `analysis`, `references`, `type`) — Phase 70 (VPROF-03 augmentation half).
- **`graphify reverse-sync` command** + `always_ask`/`never_copy`/`always_copy` modes + JSONL diff memory — Phase 70 (VRSYNC-01).
- **`reverse_sync.auto_on_run` integration** with `graphify run` / `update-vault` start — Phase 70.
- **`augment.allow_community: true` opt-in** for adding `community` frontmatter to user files — Phase 70.
- **`graphify undo-migrate` command** to reverse a `--migrate-legacy --apply` operation — not needed in v1.13; `.bak` strategy for profile migrator (D-06) is the closest analog. Capture for backlog if real users hit this.
- **Profile-derived legacy detection** (anything matching a record_type filename pattern outside its mapped folder) — explored and rejected for Phase 69 (D-12) due to false-positive risk on user-authored notes. Could be revisited as an opt-in `--strict` mode for `doctor` later.
- **Timestamped `.bak.{ts}` migration history** — explored and rejected (D-06). Could become a future `--keep-history` flag if users request it.

</deferred>

---

*Phase: 69-VPROF*
*Context gathered: 2026-05-05*
