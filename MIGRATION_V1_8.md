# v1.8 Obsidian Migration Guide

This guide explains how to update an existing Obsidian vault with graphify v1.8 output. It is generic first: `--input` points at the raw corpus you want graphify to read, and `--vault` points at the target Obsidian vault that should receive reviewed updates.

Canonical example:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

In that example, `work-vault/raw` is only the raw source corpus and `ls-vault` is the target vault. You can replace both paths for any vault framework that graphify can update through a vault-side `.graphify/profile.yaml` or the built-in default profile.

## 1. Back Up The Target Vault

Back up the target vault before apply.

Make a restorable copy of the target vault before running any apply/archive command. The preview step is read-only for vault notes, but apply writes reviewed changes and archives legacy graphify-managed notes under `graphify-out/migrations/archive/`.

Recommended backups:

- Commit or snapshot the target vault if it is version-controlled.
- Copy the vault directory to a separate location.
- Confirm the backup includes `.graphify/`, generated Graphify notes, and any legacy `_COMMUNITY_*` notes you expect to migrate.

Do not continue to `--apply --plan-id` until you know how to restore this backup.

## 2. Validate The Target Vault

Validate the vault profile before previewing migration effects:

```bash
graphify --validate-profile ls-vault
```

Fix reported profile errors first. Warnings may indicate deprecated v1.8 settings such as legacy community overview output; review them before migration so the generated notes match the v1.8 MOC-only contract.

## 3. Preview The Migration

Run the update command without `--apply`:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

Preview is the default. It rebuilds the graph from the raw corpus, renders the target vault output as a dry run, and writes review artifacts under `graphify-out/migrations/`. It does not write vault notes during preview.

Review the command output and the generated migration plan. The plan lists `CREATE`, `UPDATE`, `REPLACE`, `SKIP_PRESERVE`, `SKIP_CONFLICT`, and `ORPHAN` rows so you can see what graphify would write, preserve, refuse, or archive.

## 4. Review The Migration Plan

Review the migration plan before apply.

Open the generated `migration-plan-<id>.md` and `migration-plan-<id>.json` files under `graphify-out/migrations/`.

Check at least:

- The raw input path and target vault path match the command you intended.
- New v1.8 notes land under the Graphify-owned output tree declared by the profile.
- Legacy `_COMMUNITY_*` notes appear only as migration candidates or review-only orphan rows, not as new generated output.
- `SKIP_PRESERVE` rows correspond to user-modified notes you want graphify to leave alone.
- `SKIP_CONFLICT` rows, especially repo identity drift, are expected and understood.

Copy the plan ID from the preview output or from the artifact filename.

## 5. Apply and archive

Apply only after the backup and review are complete:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault --apply --plan-id <id>
```

Apply requires a reviewed plan ID. Graphify reloads the plan artifact, verifies that the current preview still matches the reviewed request, writes only approved `CREATE`, `UPDATE`, and `REPLACE` rows, and archives reviewed legacy notes by default after successful writes.

Archived legacy notes are moved under:

```text
graphify-out/migrations/archive/
```

Graphify does not destructively delete legacy notes. Archive movement preserves relative paths so you can inspect or restore individual files.

## 6. Roll Back If Needed

Rollback immediately after apply/archive if needed.

If the apply result is wrong, roll back before making more graphify runs or manual edits:

1. Restore the target vault from the backup you made before apply.
2. If you only need specific legacy notes, copy them back from `graphify-out/migrations/archive/<plan-id>/` to their original vault-relative paths.
3. Re-run the preview command and confirm the new migration plan reflects the restored state.

The archive is evidence for review and rollback, not a substitute for a full vault backup.

## 7. Rerun And Review Cleanup

Rerun graphify after reviewing the archive.

After apply and any rollback decision, run the preview command again:

```bash
graphify update-vault --input work-vault/raw --vault ls-vault
```

The rerun should show a smaller or empty set of migration rows. Review any remaining legacy or conflict rows before applying another plan. Keep the archive until you are confident the v1.8 output is correct and your vault backup policy has captured the updated state.
