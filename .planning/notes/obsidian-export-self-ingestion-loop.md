---
title: "Obsidian export self-ingestion loop — root cause"
date: 2026-04-27
context: Diagnosed during /gsd-explore session investigating doubled folder path `~/Documents/work-vault/graphify-out/obsidian/graphify-out/obsidian/Atlas/...` reported by the user. Captures the diagnostic chain so the next person debugging an "obsidian export looks weird" report has the trail.
---

# Obsidian export self-ingestion loop

## Symptom

User reported nested folder structure after running `graphify --obsidian` from `~/Documents/work-vault/`:

```
~/Documents/work-vault/
└── graphify-out/
    └── obsidian/
        ├── (vault notes — first run output)
        └── graphify-out/
            └── obsidian/
                └── Atlas/...
```

The user's hypothesis was an exporter path-construction bug.

## Actual cause

Not an exporter bug — a **detection feedback loop**:

1. `detect.collect_files()` walks the working directory. The default ignore set does **not** include `graphify-out/`.
2. When run from a vault root, the first run writes notes into `graphify-out/obsidian/`. A *second* run picks those notes up as fresh `document` inputs.
3. The re-ingested nodes have `source_file = "graphify-out/obsidian/<original-name>.md"`.
4. `export.to_obsidian()` (`graphify/export.py:518`) writes each node into a path derived from its `source_file` — so the new output ends up at `graphify-out/obsidian/graphify-out/obsidian/<original-name>.md`.
5. Every subsequent run nests one level deeper.

## Why this matters beyond the immediate fix

The exporter's "mirror `source_file` under output dir" policy is fragile in two scenarios:

- Running from inside the vault (this bug — fixed by detect-side ignore)
- Running with `--obsidian-dir <target_vault>` where the target is a real Obsidian vault — source-path mirroring produces meaningless folder structure that doesn't match the vault's organization

The second scenario is what v1.7 "Configurable Vault Adapter" exists to solve: vault profiles dictate placement, not source-file paths. See `.planning/notes/v1.7-input-vault-adapter-no-source-mirroring.md`.

## Related decisions

- D-73: CLI is utilities-only; skill is the pipeline driver
- D-74: `to_obsidian()` is a notes pipeline, not a vault-config-file manager
- See also: `.planning/notes/folder-architecture-graphify-out-vs-vault.md` (v1.2 UAT note covering an adjacent — but distinct — folder-layout question)

## Files involved

- `graphify/detect.py` — `collect_files()` and default ignore set (the fix surface)
- `graphify/export.py:518` — `to_obsidian()` (the symptom surface — correct as written)
- `graphify/extract.py` — populates `source_file` on nodes (correct as written)
