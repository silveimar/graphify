# Phase 4: Merge Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 04-merge-engine
**Areas discussed:** A. Note identity / ownership, B. Frontmatter merge model, C. Field ordering, D. Body content merge, E. Phase boundary / dry-run

---

## A. Note identity / ownership detection

### A.1 — Ownership mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Path + fingerprint | Path-based by default; before updating, sniff for graphify fingerprint (frontmatter field OR body sentinel). Missing fingerprint at a classified path → skip with warning. | ✓ |
| Pure path-based | Any file at classified target path is graphify's. Simple but risks silent clobber of pre-existing user files. | |
| Frontmatter marker only | Write `graphify_managed: true` to every note; only touch marked files. Users can strip the marker intentionally or accidentally. | |
| Sidecar manifest | `.graphify/manifest.json` lists every file graphify wrote with hashes. Strongest provenance, but drifts on Obsidian renames. | |

**User's choice:** Path + fingerprint (Recommended)
**Notes:** The dual-signal model gives forensic clarity without introducing a sidecar state file that would drift when Obsidian renames notes silently.

### A.2 — Fingerprint mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Body sentinel comments | Region markers double as fingerprint — presence of any `graphify:<block>:start` comment marks the note as managed. | |
| Frontmatter field only | `graphify_managed: true` scalar in graphify-owned frontmatter region. | |
| Both: frontmatter field AND body sentinels | Belt-and-suspenders — either signal sufficient to claim ownership. More robust to user accidentally stripping one signal. | ✓ |

**User's choice:** Both — frontmatter field AND body sentinels
**Notes:** Maximum robustness. Either signal alone suffices, so accidental frontmatter-stripping doesn't surrender ownership.

### A.3 — First-touch collision (unmanaged file at classified path)

| Option | Description | Selected |
|--------|-------------|----------|
| Skip + warn | Log warning to stderr, skip file, continue with rest of vault. Safest default. | ✓ |
| Skip silently | No warning, just skip. Quieter but opaque. | |
| Rename the unmanaged file | Move existing file aside, write graphify version. Preserves content but mutates vault. | |
| Error out the whole run | Refuse until user resolves conflict. Safest possible but one stray file blocks everything. | |

**User's choice:** Skip + warn (Recommended)
**Notes:** Matches graphify's fail-loudly-continue-when-safe pattern from Phase 1. Power-user `--force` flag deferred to future.

---

## B. Frontmatter field merge model

### B.1 — Merge model semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Per-key policy | Scalars `replace`, graphify-owned lists `union`, `preserve_fields` `preserve`, unknown user keys untouched. | ✓ |
| Blacklist only | Graphify replaces every emitted field except keys in `preserve_fields`. Simple but wipes user list extensions. | |
| Whitelist only | Graphify only touches a fixed set of known keys. Very safe but can't refresh `tags` / `up`. | |

**User's choice:** Per-key policy (Recommended)
**Notes:** Motivating example — user adds `[[Research Log]]` to a note's `collections`; per-key union semantics keep it while graphify still refreshes its own entries.

### B.2 — Policy source

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in + profile overrides | Canonical policy table ships with merge module; users override per-key via `profile.merge.field_policies`. Deep-merges over built-ins. | ✓ |
| Built-in only, no override | Hardcoded table; users configure only `preserve_fields`. Simpler profile surface. | |
| Entirely profile-driven, no default | Profile must declare every policy. Maximum control, zero magic, verbose. | |

**User's choice:** Built-in + profile overrides (Recommended)
**Notes:** Defaults cover 99% of users; power users tune. Matches Phase 1's deep-merge philosophy for profile sections.

---

## C. Field ordering on update (MRG-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve existing + slot-near-neighbor | Existing keys keep position; new keys inserted after their canonical D-24 neighbor; bottom-append fallback. | ✓ |
| Preserve existing + append new at bottom | Simpler: existing untouched, new keys always at bottom. | |
| Always canonical D-24 order | Deterministic, matches new notes. Noisy first merge after any user reordering. | |

**User's choice:** Preserve existing + slot-near-neighbor (Recommended)
**Notes:** Git diff on update shows only actual value changes plus any genuinely new keys, which land near their logical home in the file.

---

## D. Body content merge

### D.1 — Deleted sentinel blocks

| Option | Description | Selected |
|--------|-------------|----------|
| Respect deletion, don't re-insert | Missing block = intentional user choice. Refresh only blocks currently present. State-free rule. | ✓ |
| Re-insert at canonical position | Every graphify block always present; if removed, merge puts it back. Simple but fights the user. | |
| Profile flag: respect_deletions | Expose as toggle (default true), let power users flip. | |

**User's choice:** Respect deletion, don't re-insert (Recommended)
**Notes:** This rule is state-free — no manifest needed. Key insight that justified rejecting the sidecar manifest in A.1.

### D.2 — Malformed sentinel handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip the note + warn | Log warning, skip note entirely, continue. Fail loudly, never lose data. | ✓ |
| Repair by replacing the whole region | Find start marker, replace up to best-guess end. Self-healing but risks eating user prose. | |
| Treat note as fully user-owned, skip silently | Malformed = not ours. Back off. Quieter but opaque. | |

**User's choice:** Skip the note + warn (Recommended)
**Notes:** Never auto-repair — the cost of an incorrect boundary guess is user data loss.

---

## E. Phase boundary & dry-run affinity

### E.1 — Public API shape

| Option | Description | Selected |
|--------|-------------|----------|
| Two-layer: compute_merge_plan + apply_merge_plan | Pure compute returns `MergePlan` dataclass; apply writes to disk. Dry-run calls compute only. Mirrors Phase 3's `MappingResult`. | ✓ |
| Single merge() with dry_run flag | One function, threads `dry_run: bool`. Simpler surface, uglier internals. | |
| Pure compute only, Phase 5 owns all IO | Merge never writes. Cleanest boundary, but Phase 5 reimplements sentinel-aware write logic. | |

**User's choice:** Two-layer API (Recommended)
**Notes:** Mirrors Phase 3's `MappingResult` precedent. Dry-run becomes a 3-line wrapper in Phase 5.

### E.2 — Orphaned notes (node disappeared between runs)

| Option | Description | Selected |
|--------|-------------|----------|
| Leave alone + report | compute emits ORPHAN action; apply never deletes. User decides. | ✓ |
| Delete orphans on update strategy | Update actively deletes orphan notes. Tidy vault, risk of lost user content. | |
| Move orphans to `.graphify/orphans/` | Apply moves orphan notes to holding folder. Preserves content. | |
| Profile flag: `merge.orphan_action` | Expose as config: `leave` (default), `delete`, `archive`. | |

**User's choice:** Leave alone + report (Recommended)
**Notes:** Graphify never destroys user-touched content. Auto-delete/archive deferred to future profile flag.

---

## Follow-ups (Claude's Discretion)

Two items offered for discussion, resolved as Claude's Discretion at the user's request:

### F.1 — YAML parsing approach

**Resolved:** Symmetric hand-rolled reader matching `_dump_frontmatter` (profile.py:359). No PyYAML dependency on the read path. Edge cases to test: block-form lists, quoted wikilinks, ISO dates, bool/null coercion, Templater `<% %>` tokens as literal strings.

### F.2 — Atomic write semantics

**Resolved:** `.tmp + os.replace` for crash safety. Content-hash compare before `os.replace` to skip writes when new content is identical to existing content (zero mtime churn, zero git diff noise on no-op re-runs). Stale `.tmp` cleanup as a defensive pass at the top of `apply_merge_plan`.

---

## Deferred Ideas

(See CONTEXT.md `<deferred>` section for full list. Summary:)

- `--force` flag for first-touch override of unmanaged files
- `merge.orphan_action` profile flag for auto-delete or auto-archive of orphaned notes
- Sidecar manifest for forensic merge (rejected in Area A)
- Per-field provenance tracking
- Interactive conflict resolution prompts
- Structured diff in `MergeAction` for UPDATE actions
- Three-way merge with git ancestor
- LLM-assisted merge of user prose
- Merge preview in HTML export

---

*Phase: 04-merge-engine*
*Discussion gathered: 2026-04-11*
