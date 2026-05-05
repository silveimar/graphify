# Phase 70: VRSYNC — Vault → Input Reverse-Sync & User-File Augmentation - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver `graphify reverse-sync`: a one-direction sync that pulls new/changed user-authored markdown from the vault back into `profile.input_path`, plus a strict frontmatter-augmentation contract for any graphify-side writes that touch user files. Phase 69 already established the user-namespace write-refusal half (VPROF-03 refusal); this phase implements the augmentation half plus the full reverse-sync command (VRSYNC-01).

In scope: reverse-sync command + flags + modes; JSONL audit log; auto_on_run hook into `graphify run` and `graphify update-vault`; allowlist frontmatter merge; `augment.allow_community` gate.

Out of scope: bidirectional sync, two-way conflict resolution, watch-mode reverse-sync, deletion propagation (logged only), non-markdown asset mirroring.

</domain>

<decisions>
## Implementation Decisions

### Conflict resolution & prompt UX (always_ask)
- **D-01:** Per-file interactive prompt with keys `[Y]es / [n]o / [d]iff / [A]ll yes / [Q]uit`. Mirrors `git add -p` ergonomics; requires TTY. Non-TTY behavior governed by D-08.
- **D-02:** `[d]` shows the unified diff inline then re-prompts for the same file (does not auto-accept).
- **D-03:** `diff_summary` field in JSONL is a compact stats string: `"+N -M lines, +A -B bytes"`. No diff body in the log — keeps JSONL parseable, avoids leaking file content into the audit trail.

### Augmentation merge semantics (user-file frontmatter)
- **D-04:** **List-typed allowlist keys** (`tags`, `related_to`, `up`, `references`): union with user's existing list, preserve user order, append graphify-derived items not already present. Idempotent.
- **D-05:** **Scalar allowlist keys** (`type`, `comments`, `analysis`): preserve user value if present; only write when key is absent. User authorship wins.
- **D-06:** **Stateless re-add:** if the user deletes a key graphify previously added, graphify will re-add it on the next run. To suppress, the user sets `profile.augment.allow_<key>: false` or removes the key from the allowlist. No tombstone state.
- **D-07:** Body content (post-frontmatter) is byte-identical before and after augmentation. Property test required (per success criterion 5).

### User-folder detection & file scope
- **D-08:** `reverse-sync` scans exactly the folders listed in `profile.user_only_folders` (the VPROF-02 list). Symmetric with the write-refusal contract: folders that graphify must not write into are exactly the folders it mirrors back.
- **D-09:** Markdown only (`*.md`), recursive under each user folder. Subdirectory structure preserved when copying into `input_path` (mirror relative path).
- **D-10:** Vault-side deletions are never propagated to input. They are logged as a `vault_deleted` JSONL event for audit; user removes from input manually if intended. Avoids destructive consequences from vault renames.

### Failure mode & flag precedence (auto_on_run)
- **D-11:** When `auto_on_run: true` and reverse-sync hits an unanswerable prompt or read error mid `graphify run` / `update-vault`: warn-and-continue. Sync clean adds (no conflict), print `[graphify] reverse-sync: N conflicts skipped — run 'graphify reverse-sync' to resolve` to stderr, then continue the parent command. Non-blocking.
- **D-12:** `--yes` overrides `always_ask` only. It does NOT override `never_copy`. `never_copy` is an explicit contract (log only, never write) and `--yes` is a prompt-answer flag — orthogonal knobs. To copy without prompting, set `mode: always_copy`.
- **D-13:** Non-TTY environments (CI, piped) default to skip-conflicts under `always_ask` (treated like an unanswerable prompt per D-11). They do NOT auto-accept. CI must opt in via `--yes` or `mode: always_copy`.

### JSONL audit log
- **D-14:** Every detected change is logged, regardless of whether a copy occurred. Action enum: `copied`, `skipped_user`, `skipped_conflict`, `skipped_never_copy`, `vault_deleted`. Full audit trail; doctor can summarize.
- **D-15:** Default log path: `.graphify/reverse-sync-log.jsonl` (per `profile.reverse_sync.memory_path`). Append-only; never rotated/truncated by graphify (user-managed file like `.graphify/profile.yaml.bak`).

### `community` frontmatter gate
- **D-16:** The `community` key is added to user files only when `profile.augment.allow_community: true`. Default profile keeps it `false`. Per success criterion 6.

### Claude's Discretion
- Exact prompt rendering (colors, multi-line formatting) — match existing graphify CLI prompt style.
- Diff renderer choice (stdlib `difflib.unified_diff` is the obvious pick; no need for `rich`).
- Internal module layout (`graphify/reverse_sync.py` vs splitting into `reverse_sync/` package) — planner's call.
- Whether augmentation merge lives in `vault_promote.py` (extension of existing pipeline) or a new `augment.py` — planner's call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 70: VRSYNC" (lines 104–116) — 6 success criteria, dependencies, requirement IDs (VPROF-03 augmentation half, VRSYNC-01).
- `.planning/REQUIREMENTS.md` — VPROF-03 and VRSYNC-01 full text.

### Phase 69 artifacts (locked precedents this phase builds on)
- `.planning/phases/69-vprof-vault-profile-driven-folder-resolution-user-namespace-guard/69-CONTEXT.md` — profile schema v2, `graphify_folder_mapping`, `user_only_folders`, two-flag CLI safety pattern.
- `.planning/phases/69-vprof-vault-profile-driven-folder-resolution-user-namespace-guard/69-VERIFICATION.md` — validated v2 schema invariants.

### Code touchpoints
- `graphify/profile.py` — `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS`, `migrate_profile_v1_to_v2`. Add `reverse_sync` and `augment` schema sections; reuse `.bak` backup pattern if migration is needed.
- `graphify/vault_promote.py` — pre-flight refusal + chokepoint guard (D-04 fallback, `_resolve_folder_prefix`). Augmentation merge integrates here.
- `graphify/cache.py` — SHA256 hashing utility reused for `hash_before` / `hash_after`.
- `graphify/doctor.py` — `DoctorReport` already has `legacy_artifact_paths` (Phase 69-04). Add a non-blocking reverse-sync section summarizing pending conflicts.
- `graphify/__main__.py` — register `reverse-sync` subcommand; wire `auto_on_run` into `run` and `update-vault` entrypoints.
- `graphify/security.py` — path confinement for vault → input file copies.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cache.py` SHA256 hashing — reuse directly for change detection (success criterion 1) and JSONL `hash_before` / `hash_after`.
- `migrate_profile_v1_to_v2` `.bak` write pattern — model for any reverse-sync state files that need atomic writes.
- Phase 69's two-flag pattern (`--migrate-legacy` dry-run / `--migrate-legacy-apply`) — informs `--yes` flag design.
- `DoctorReport` extension pattern (Phase 69-04 added `legacy_artifact_paths` + `=== Legacy Artifacts ===` section) — same pattern for a `=== Reverse-Sync ===` non-blocking section.
- Pre-flight refusal `_preflight_check_user_only_folders()` — reuse the same folder list for the symmetric reverse-sync scan source (D-08).

### Established Patterns
- All external input through `security.py` (path confinement to expected roots). Reverse-sync writes into `profile.input_path` — must validate paths stay inside that root.
- Stderr `[graphify] ...` prefix for warnings, stdout for user-facing output.
- Validation returns `list[str]` of errors, not exceptions.
- Append-only state files live under `.graphify/` (precedent: `profile.yaml.bak`, future `reverse-sync-log.jsonl`).

### Integration Points
- `graphify run` and `graphify update-vault` entrypoints in `__main__.py` — add early-stage hook for `auto_on_run: true`.
- Profile schema additions go through `_VALID_TOP_LEVEL_KEYS` allowlist (Phase 69-01 pattern) and may need a v2→v2.1 minor migration (idempotent additive).
- `doctor` command output gains a new section.

</code_context>

<specifics>
## Specific Ideas

- Prompt UX explicitly modeled on `git add -p` (Y/n/d/A/Q semantics).
- Diff rendering uses stdlib `difflib.unified_diff`; no third-party dep.
- `community` frontmatter key gated behind `profile.augment.allow_community` (default false) — prevents leaking graphify-internal labels into user notes by default.

</specifics>

<deferred>
## Deferred Ideas

- **Bidirectional / forward+reverse merge:** Out of scope. This phase is one-direction (vault → input).
- **Watch-mode reverse-sync:** `watchdog`-driven continuous mirroring — possible future phase.
- **Asset mirroring (images/PDFs alongside markdown):** Considered and rejected for Phase 70 (D-09). Future phase if needed.
- **Tombstone tracking for user-deleted keys:** Rejected per D-06 (stateless re-add). Could be revisited if users complain about re-adds.
- **Vault-deletion propagation to input:** Logged only (D-10). A future phase could add an opt-in `mode: mirror_deletes` setting.
- **Doctor command summary of recent reverse-sync activity:** Light version in this phase (count of pending conflicts); deeper analytics deferred.

</deferred>
