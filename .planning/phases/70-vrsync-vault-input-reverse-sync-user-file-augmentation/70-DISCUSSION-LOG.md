# Phase 70: VRSYNC — Discussion Log

**Date:** 2026-05-05
**Mode:** discuss (default), --chain

## Areas Selected by User

Conflict resolution in always_ask · Augmentation merge semantics · User-folder detection source · auto_on_run failure + flag precedence

## Q&A

### Area 1 — Conflict resolution in always_ask

**Q:** In always_ask mode, how should reverse-sync prompt when a vault file differs from its input counterpart?
- Per-file Y/n/d/A/Q (Recommended) ✅ selected
- Per-file Y/n only + always show diff first
- Batch summary then single confirm

**Q:** What should the diff_summary field in reverse-sync-log.jsonl contain?
- Stats string "+N -M" + bytes (Recommended) ✅ selected
- Unified diff snippet (capped)
- Hash-only

→ D-01, D-02, D-03

### Area 2 — Augmentation merge semantics

**Q:** How should graphify merge list-typed allowlist keys (tags, related_to, up, references)?
- Union, preserve user order, append new (Recommended) ✅ selected
- Replace with graphify's set
- Union + namespace graphify items

**Q:** How should graphify handle scalar allowlist keys (type, comments, analysis) when the user has set them?
- Preserve user value, never overwrite (Recommended) ✅ selected
- Overwrite with graphify value
- Preserve user value but log divergence

**Q:** What if the user deletes a key that graphify previously added?
- Re-add (stateless merge) (Recommended) ✅ selected
- Track tombstones in profile/log

→ D-04, D-05, D-06, D-07

### Area 3 — User-folder detection source

**Q:** Which folders does reverse-sync scan?
- profile.user_only_folders (Recommended) ✅ selected
- Everything not in graphify_folder_mapping
- Explicit profile.reverse_sync.scan_folders

**Q:** Which file types and how to handle nested subdirectories?
- Markdown only, recursive (Recommended) ✅ selected
- Markdown + attached assets, recursive
- Markdown only, top-level only

**Q:** What about files that exist in input but were deleted in vault?
- Never delete; log only (Recommended) ✅ selected
- Prompt to delete (always_ask) / honor mode

→ D-08, D-09, D-10

### Area 4 — auto_on_run failure + flag precedence

**Q:** If reverse-sync fails or hits an unanswerable prompt during graphify run / update-vault?
- Warn-and-continue, skip pending conflicts (Recommended) ✅ selected
- Abort the parent command on any conflict
- Treat non-TTY as --yes (always copy)

**Q:** Does --yes override never_copy mode, or only always_ask?
- Only overrides always_ask (Recommended) ✅ selected
- Overrides both (forces copy)

**Q:** Should the JSONL log capture conflicts/skips even when no copy occurred?
- Log every detected change, with action field (Recommended) ✅ selected
- Log only successful copies

→ D-11, D-12, D-13, D-14, D-15

## Notes

- All recommended options accepted. Decisions consistent with Phase 69 patterns: symmetric folder-list reuse (`user_only_folders`), two-knob safety design (`--yes` orthogonal to `mode`), append-only `.graphify/` state files, doctor extension.
- D-16 (`augment.allow_community` gate, default false) carried directly from roadmap success criterion 6 — not explicitly asked but locked.
- No scope creep raised. No deferred ideas surfaced from user; deferred section seeded from out-of-scope alternatives presented in the questions.
