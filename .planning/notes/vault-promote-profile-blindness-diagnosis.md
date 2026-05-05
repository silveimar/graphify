---
title: "vault-promote profile blindness — root cause + reshape decisions"
date: 2026-05-05
context: UAT against /Users/silveimar/Documents/ls-vault revealed that `graphify update-vault` followed by `graphify vault-promote --write-into-vault` (1) left prior `_COMM*.md` artifacts at the vault root unmoved, and (2) wrote new graphify notes into user folders (`Atlas/Maps/`, `Atlas/Dots/People/`, `Atlas/Dots/Things/`) instead of the profile-pinned subtree (`Atlas/Sources/Graphify/...`). Diagnosis traced both to hardcoded folder paths in `vault_promote.py` that ignore `profile.folder_mapping`. Scope reshape during /gsd-explore expanded the fix into a profile-schema-v2 + bidirectional-sync design.
---

# vault-promote profile blindness — root cause + reshape decisions

## Reproduction

- **Origin corpus**: `/Users/silveimar/Documents/work-vault/`
- **Target vault**: `/Users/silveimar/Documents/ls-vault/` (profile already in place at `.graphify/profile.yaml`, `folder_mapping.moc: Atlas/Sources/Graphify/Maps/`, etc.)
- **Backup**: `/Users/silveimar/Documents/ls-vault-backup-20260504`
- **Commands run**: `graphify update-vault` then `graphify vault-promote --vault /Users/silveimar/Documents/ls-vault --threshold 10 --write-into-vault`

## Observed symptoms

1. `_COMM*.md` files at vault root (and other md at vault root) were not relocated/archived by `vault-promote`. User had to move them manually.
2. Many `Community*.md` notes appeared under `Atlas/Maps/` (~1000+) and additional notes under `Atlas/Dots/People/` and `Atlas/Dots/Things/` — all *outside* the profile-pinned `Atlas/Sources/Graphify/` subtree.

## Diff against backup

`diff -rq` of `Atlas/` showed **no user files deleted or modified** (only `.DS_Store`). The "Only in current" entries are all *new* graphify writes landing in user namespace alongside the (also-correct) `Atlas/Sources/Graphify/` tree.

## Root cause

`graphify/vault_promote.py` constructs every record with a **hardcoded** `folder` literal:

- `vault_promote.py:206` — `"folder": "Atlas/Dots/Things/"`
- `vault_promote.py:219` — `"folder": "Atlas/"`
- `vault_promote.py:231` — `"folder": "Atlas/Maps/"`  (community MOCs — the `Community 0.md`..`Community N.md` flood)
- `vault_promote.py:249` — `"folder": "Atlas/Dots/People/"`
- `vault_promote.py:267` — `"folder": "Atlas/Quotes/"`
- `vault_promote.py:283` — `"folder": "Atlas/Dots/Statements/"`
- `vault_promote.py:299` — `"folder": "Atlas/Sources/"`

The `_DEFAULT_LAYERS` dict at `vault_promote.py:873-879` repeats the same legacy layout. **`profile.folder_mapping` is never consulted** during record construction. The profile-write-back step at `vault_promote.py:822-863` updates the profile *from* graphify but graphify does not read the profile's mapping back into its own write decisions.

## Why no user files were destroyed (the unsung hero)

The atomic writer `write_note` at `vault_promote.py:702-732` checks `manifest[rel_path]` and refuses to overwrite any file whose hash is unknown to graphify's manifest. That guard is what kept `Atlas/Maps/` user content intact when graphify dumped 1000+ `Community*.md` siblings beside it. **This invariant must be preserved** by any fix.

## Issue 1 (root `_COMM*.md`) is a separate symptom of the same blindness

The vault-root `_COMM*.md` files originated from an earlier `update-vault` (or legacy export) cycle, written before vault-promote semantics matured. Nothing in the current vault-promote / update-vault path detects or relocates them. A `doctor` legacy-artifact section + `--migrate-legacy` flag is the right shape — same fix shape as Issue 2 (consult profile + sweep what doesn't conform).

## Reshape decisions (from /gsd-explore conversation, 2026-05-05)

**Q1 — `community` field on user-file augmentation: gated.** Adding automated cluster ids to user-authored notes is invasive and churns on every reclustering. Default `augment.allow_community: false`; users opt in.

**Q2 — reverse-sync semantics: mirror + diff memory, explicit command.** Append-with-versioning was rejected because graphify ingests source code (`.py`, `.ts`, etc.) and embedding `<!-- graphify:vault-update -->` blocks would break tree-sitter parsing. Mirror mode keeps input files in their native shape; diff memory at `.graphify/reverse-sync-log.jsonl` carries provenance. SHA256-based change detection reuses the `cache.py` hashing primitive so there's a single canonical "what changed" computation. Reverse-sync runs as an **explicit `graphify reverse-sync` command** (separation of concerns); a `reverse_sync.auto_on_run: false` profile flag lets users opt into running it implicitly at the start of `graphify run` / `update-vault`.

**Profile schema v2 — additions:**
- `input_path` — replaces ad-hoc `--input` flag in profile-aware runs
- `vault_path` — target vault root
- `graphify_folder_mapping` — renamed from `folder_mapping`; default ALWAYS `Atlas/Sources/Graphify/<type>/` (no fallback to legacy `Atlas/Maps/`, `Atlas/Dots/*`)
- `user_only_folders` — explicit non-write list (e.g. `Atlas/`, `Calendar/`, `Efforts/`, `+/`, `x/`, vault root)
- `augment` — `{ allow_community: false }`
- `reverse_sync` — `{ mode: always_ask | never_copy | always_copy, memory_path, auto_on_run: false }`

**One-shot migrator** for the `folder_mapping` → `graphify_folder_mapping` rename so existing vault profiles upgrade silently.

## Phase split

- **Phase 69** — pure regression fix: profile-driven folder resolution, user-namespace guard, legacy migration. No new surface area; can ship alone and immediately stop the pollution bleed.
- **Phase 70** — additive: `graphify reverse-sync`, JSONL diff memory, augmentation-only frontmatter merge for user files.

Splitting keeps PR review focused and allows halting at 69 if scope pressure arrives late in v1.13.
