# ls-vault Update Runbook

Use this guide to update your existing vault at `/Users/silveimar/Documents/ls-vault/` so it matches the current graphify implementation and profile behavior.

## Scope

- Target vault: `/Users/silveimar/Documents/ls-vault/`
- Profile source: `/Users/silveimar/Documents/silogia-repos/graphify/profile-example-complete.yaml`
- Update workflow: `graphify update-vault --input <raw-corpus> --vault <target-vault>`

## 0) Set variables once (recommended)

```bash
REPO="/Users/silveimar/Documents/silogia-repos/graphify"
VAULT="/Users/silveimar/Documents/ls-vault"
RAW="work-vault/raw"   # replace if your raw corpus path is different
```

## 1) Update graphify code and local package

```bash
cd "$REPO"
git checkout main
git pull
pip install -e ".[all]"
```

Optional sync of installed skill/hook files:

```bash
graphify install
```

## 2) Back up the vault before apply

Choose one backup strategy (both is better):

```bash
cd "$VAULT"
git add -A && git commit -m "backup before graphify vault update"
```

```bash
cp -R "$VAULT" "${VAULT}-backup-$(date +%Y%m%d-%H%M%S)"
```

Do not run apply until one backup path is complete.

## 3) Install the complete ls-vault profile

```bash
mkdir -p "$VAULT/.graphify"
cp "$REPO/profile-example-complete.yaml" "$VAULT/.graphify/profile.yaml"
```

This profile includes:

- `repo.identity: ls-vault`
- richer `mapping_rules` for `Atlas/Sources/Clippings`, `Atlas/Sources/Graphify/memory`, `Efforts/Works/Notebooks`, and `+/` ticket notes
- `merge.field_policies.tags: union`
- per-note `dataview_queries`

## 4) Validate profile before migration

```bash
graphify --validate-profile "$VAULT"
```

Expected: `profile ok`.

Notes:
- You may see Windows path-budget warnings; those are warnings, not hard failures on macOS.
- If validation fails, fix the reported keys first (especially regex/path issues in `mapping_rules`).

## 5) Preview the vault update (no writes)

```bash
graphify update-vault --input "$RAW" --vault "$VAULT"
```

Preview writes migration artifacts under `graphify-out/migrations/` and does not apply changes to the vault.

## 6) Review the migration plan

Review the latest plan artifacts in `graphify-out/migrations/` and confirm:

- expected CREATE/UPDATE targets under `Atlas/Sources/Graphify/...`
- conflict/preserve rows look reasonable (`SKIP_PRESERVE`, `SKIP_CONFLICT`)
- no unexpected routing from your custom folders
- plan id is captured for apply

If anything is off: edit `"$VAULT/.graphify/profile.yaml"` and rerun preview.

## 7) Apply reviewed plan

```bash
graphify update-vault --input "$RAW" --vault "$VAULT" --apply --plan-id <id>
```

Apply revalidates plan/input/vault identity before writes.
Legacy graphify-owned notes are archived under `graphify-out/migrations/archive/`.

## 8) Verify in Obsidian

Check these quickly:

- Graphify folders populated where expected (`Maps`, `Things`, `Statements`, `People`, `Sources`)
- Dataview blocks render for MOCs and typed notes
- links/tags/frontmatter preserved for previously edited notes
- memory/clippings/notebook routing follows your profile rules

## 9) Roll back if needed

If results are not correct:

1. Stop editing the vault.
2. Restore from your backup commit/copy.
3. Recover specific legacy notes from `graphify-out/migrations/archive/` if needed.
4. Adjust profile and rerun preview.

## 10) Ongoing update pattern

For future runs:

1. `graphify --validate-profile "$VAULT"`
2. `graphify update-vault --input "$RAW" --vault "$VAULT"` (preview)
3. review plan
4. `--apply --plan-id <id>`

## Related docs

- `docs/MIGRATION_V1_8.md` — generic migration contract
- `docs/PROFILE-CONFIGURATION.md` — profile schema and rules
- `profile-example-complete.yaml` — complete ls-vault-oriented profile example
