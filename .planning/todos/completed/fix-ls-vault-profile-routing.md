---
created: 2026-04-28
title: Fix ls-vault profile routing so graphify output stops dumping into vault root
area: vault-config
priority: high
resolves_phase: 32
files:
  - /Users/silveimar/Documents/ls-vault/.graphify/profile.yaml
---

# Fix ls-vault profile routing

## Problem

Currently running:

```
cd /Users/silveimar/Documents/work-vault
graphify --obsidian-dir /Users/silveimar/Documents/ls-vault/
```

Output dumps into `ls-vault/` root and `Atlas/Dots/` because the built-in default profile uses `folder_mapping.default: Atlas/Dots/`. The ls-vault has no `.graphify/profile.yaml` (or has one that doesn't override `folder_mapping`), so the legacy default leaks through.

## Solution (5-minute fix, no code change)

Edit (or create) `/Users/silveimar/Documents/ls-vault/.graphify/profile.yaml` with:

```yaml
folder_mapping:
  moc: Atlas/Sources/Graphify/MOCs/
  thing: Atlas/Sources/Graphify/Docs/
  statement: Atlas/Sources/Graphify/Docs/
  person: Atlas/Sources/Graphify/Docs/
  source: Atlas/Sources/Graphify/Sources/
  default: Atlas/Sources/Graphify/Docs/
```

Then re-run graphify. New notes will land in `Atlas/Sources/Graphify/`. Existing `_COMMUNITY_*.md` notes scattered around the vault will need to be moved or deleted manually (the merge engine will surface them as orphans on next run — see ORPHAN action in PROJECT.md v1.0 requirements).

## Verification

```bash
graphify --obsidian-dir /Users/silveimar/Documents/ls-vault/ --validate-profile
graphify --obsidian-dir /Users/silveimar/Documents/ls-vault/ --dry-run
```

The dry-run output should report `output destination: Atlas/Sources/Graphify/...` instead of `Atlas/Dots/...`.

## Why this is a todo, not a phase

This is config-only (no graphify code change), only affects the user's personal vault, and unblocks daily usage immediately. The "make this the built-in default for everyone" work belongs in milestone v1.8 (see `.planning/MILESTONE-CONTEXT.md`).

## Followup

After v1.8 ships, this profile.yaml should be revisited to:
- Add `clustering.min_community_size: 6` (or higher if vault is large)
- Add `repo_name:` per-source if multiple repos get ingested into ls-vault
- Possibly remove this entire override file once v1.8's built-in default does the right thing out of the box.
