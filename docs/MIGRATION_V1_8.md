# v1.8 Obsidian Migration Guide

This guide explains how to update an existing Obsidian vault with graphify v1.8 output. It is generic first: `--input` points at the raw corpus you want graphify to analyze, and `--vault` points at the target Obsidian vault that should receive reviewed generated notes.

The canonical example uses `work-vault/raw` as the raw corpus and `ls-vault` as the target vault:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

Use different paths for your own setup. The command is not a vault-to-vault move; graphify analyzes the raw input, previews the target vault changes, and writes migration review artifacts before any apply step.

## 1. Confirm The Target Vault

The target vault must already be an Obsidian vault with a `.obsidian/` directory. If it has a `.graphify/profile.yaml`, graphify uses that profile. Otherwise, graphify falls back to the built-in v1.8 profile.

Before you start, confirm which directory is your raw corpus and which directory is the Obsidian vault:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

## 2. Validate The Vault Profile

If the target vault has a graphify profile, validate it before migration:

```bash
graphify --validate-profile ls-vault
```

Fix profile errors before continuing. Warnings can usually be reviewed alongside the preview output.

## 3. Preview The Migration

Preview is the default behavior:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

The preview writes migration artifacts under `graphify-out/migrations/` and does not apply vault note writes. Review the generated JSON and Markdown plan before continuing.

## 4. Back Up Before Apply

Back up the target vault before apply. Treat this as a hard prerequisite, not an optional safety tip.

At minimum, make sure you have one of these:

- A clean git commit or branch containing the current vault state.
- A filesystem copy of the target vault.
- A backup from your normal Obsidian sync or backup provider that you have verified can restore files.

Do not run an apply command until the backup exists.

## 5. Review The Migration Plan

Review the migration plan before apply. The plan lists CREATE, UPDATE, REPLACE, SKIP_PRESERVE, SKIP_CONFLICT, and ORPHAN rows so you can see what graphify would do and which legacy notes are review-only.

Look for:

- New v1.8 Graphify-owned paths under the target vault.
- Preserved user edits and conflict rows.
- Legacy `_COMMUNITY_*` notes that will be archived during reviewed apply.
- The plan ID you will pass to the apply command.

## 6. Apply and archive

Apply only a reviewed plan ID:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault --apply --plan-id <id>
```

Apply revalidates the reviewed plan against the current input, vault, repo identity, and preview digest before writing. Legacy notes are archived by default under `graphify-out/migrations/archive/`. Graphify does not destructively delete legacy notes; it moves reviewed legacy files into the archive so you can inspect or restore them.

## 7. Roll Back If Needed

Rollback immediately after apply/archive if needed.

If the applied output is not what you expected:

1. Stop making further vault edits.
2. Restore the target vault from the backup you made before apply.
3. If you only need a legacy note back, copy it from `graphify-out/migrations/archive/` to its original relative path in the vault.
4. Re-run preview and inspect the migration plan again before another apply.

## 8. Rerun After Archive Review

Rerun graphify after reviewing the archive.

Use another preview first:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

The rerun should reflect the current vault state, including generated v1.8 notes and archived legacy notes. Review any remaining SKIP_CONFLICT or ORPHAN rows before applying another plan.

## 9. Cleanup Review

After the migration is stable:

- Keep the latest migration artifacts until you no longer need rollback evidence.
- Review archived files before deleting any local backup copies.
- Leave localized README updates for a later translation pass; this guide is the English v1.8 contract.
