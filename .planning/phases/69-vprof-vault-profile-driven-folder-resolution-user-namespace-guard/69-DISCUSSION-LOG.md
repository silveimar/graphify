# Phase 69: VPROF — Vault Profile-Driven Folder Resolution & User-Namespace Guard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 69-VPROF
**Areas discussed:** Folder mapping defaults, Profile migrator UX, Refusal pre-flight scope, doctor + migrate-legacy semantics

---

## Folder mapping defaults

### Q1: Default subpaths under Atlas/Sources/Graphify/ per record type

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror Ideaverse names | things→Things/, questions→Questions/, maps→Maps/, people→People/, quotes→Quotes/, statements→Statements/, sources→Sources/. Capitalized plurals matching Ideaverse vault conventions. | ✓ |
| Lowercase singular | thing/, question/, map/, etc. Cleaner for code; breaks Ideaverse convention. | |
| Flat under Graphify/ | All records in Atlas/Sources/Graphify/ root with type in frontmatter. Loses visual separation. | |

**User's choice:** Mirror Ideaverse names (Recommended).

### Q2: Naming for the 'maps' record type (community MOCs)

| Option | Description | Selected |
|--------|-------------|----------|
| Maps/ | Atlas/Sources/Graphify/Maps/. Symmetric with other plurals; parent path disambiguates from user-owned Atlas/Maps/. | ✓ |
| MOCs/ | Atlas/Sources/Graphify/MOCs/. Explicit terminology; breaks plural-noun symmetry. | |
| Communities/ | Atlas/Sources/Graphify/Communities/. Most accurate; furthest from existing 'MOC' vocabulary. | |

**User's choice:** Maps/ (Recommended).

### Q3: Lookup key shape in graphify_folder_mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Singular noun | thing, question, map, person, quote, statement, source. Reads naturally in YAML; trivial translation from internal plural keys. | ✓ |
| Plural matching internal dicts | things, questions, maps, etc. Zero translation; awkward YAML. | |

**User's choice:** Singular noun (Recommended).

### Q4: Behavior for unknown future record types (e.g., 'concept') without a profile mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to Atlas/Sources/Graphify/<Type>/ | Stays in safe namespace; INFO note suggesting user add the key. | ✓ |
| Refuse with actionable error | Pre-flight refusal; safest but blocks runs on missing key. | |
| Drop the record silently | Skip writing; violates 'fail loudly' convention. | |

**User's choice:** Fall back to Atlas/Sources/Graphify/<type>/ (Recommended).

---

## Profile migrator UX

### Q5: How folder_mapping → graphify_folder_mapping rename happens on first read

| Option | Description | Selected |
|--------|-------------|----------|
| Silent in-place rewrite + .bak | Rewrite profile.yaml + write profile.yaml.bak. Idempotent. Matches VPROF-01 'silent upgrade'. | ✓ |
| In-memory only (file untouched) | Translate at read time; never modify user's file. Zero side effects but every read pays translation. | |
| Explicit `graphify migrate-profile` command | Most respectful of user files; loudest UX; conflicts with 'silent upgrade' wording. | |

**User's choice:** Silent in-place rewrite + .bak (Recommended).

### Q6: .bak strategy across multiple migrations

| Option | Description | Selected |
|--------|-------------|----------|
| Single .bak, overwrite each migration | One profile.yaml.bak reflecting previous state. Simple; one rollback step. | ✓ |
| Timestamped .bak.{ts} per migration | Full migration history; clutters .graphify/ directory. | |
| No .bak | Smallest footprint; no recovery if migration logic has a bug. | |

**User's choice:** Single .bak, overwrite each migration (Recommended).

---

## Refusal pre-flight scope

### Q7: Where the user_only_folders pre-flight refusal check lives

| Option | Description | Selected |
|--------|-------------|----------|
| Single _write_record() chokepoint | All writes route through one helper. New writers can't bypass. Highest enforcement strength. | (chosen below — combined) |
| Pre-flight pass before any write | Compute targets, validate batch, then write. Easy to reason about; risks future drift. | (chosen below — combined) |
| Both: pre-flight pass + chokepoint guard | Defense in depth. Pre-flight gives clean error UX; chokepoint prevents bypass. | ✓ (after follow-up Q9) |

**User's choice:** Single _write_record() chokepoint (Recommended) — then in follow-up Q9, escalated to defense-in-depth (pre-flight + chokepoint).

### Q8: Behavior when batch contains ANY refused target

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse the whole batch atomically | Pre-flight collects all refusals, prints one error, exits non-zero, no writes. Matches 'no partial writes' criterion. | ✓ |
| Refuse-and-skip per file | Write safe targets, log refusals, exit non-zero at end. Violates 'no partial writes' wording. | |

**User's choice:** Refuse the whole batch atomically (Recommended).

### Q9: Add pre-flight pass on top of chokepoint for cleaner error UX?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — pre-flight + chokepoint | Pre-flight collects ALL bad targets in one error; chokepoint stays as structural backstop. ~30 lines extra. | ✓ |
| No — chokepoint only | First refusal raises; users may need fix-rerun-fix-rerun cycles. | |

**User's choice:** Yes — pre-flight + chokepoint (Recommended). Promotes Q7's chokepoint answer to full defense-in-depth.

---

## doctor + migrate-legacy semantics

### Q10: How `graphify doctor` decides what counts as a legacy graphify-shaped artifact

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded glob list | Known patterns: _COMM*.md at root, Community*.md under Atlas/Maps/, plus graphify_manifest_hash frontmatter outside pinned subtree. Deterministic; zero false positives. | ✓ |
| Manifest-hash frontmatter only | Most accurate; misses pre-frontmatter-era files. | |
| Profile-derived pattern matching | Most general; risks false positives on user notes. | |

**User's choice:** Hardcoded glob list (Recommended).

### Q11: --migrate-legacy safety model

| Option | Description | Selected |
|--------|-------------|----------|
| Dry-run default + explicit --apply | Prints move plan; --apply performs moves + manifest update. Mirrors safety stance for the only command touching user-owned vault space. | ✓ |
| Move-then-log with rollback file | Faster UX; risks unintended moves. | |
| Confirmation prompt (interactive) | Safe; breaks scripted/CI; needs --yes for automation. | |

**User's choice:** Dry-run default + explicit --apply (Recommended).

### Q12: How manifest gets re-pointed after --migrate-legacy --apply moves files

| Option | Description | Selected |
|--------|-------------|----------|
| Update manifest in place during migrate | Atomic move + manifest write per file with rollback on failure. Manifest-hash guard intact. Zero divergence window. | ✓ |
| Trigger a manifest rebuild after migrate | Simpler; loses per-file metadata; brief stale window. | |
| Mark legacy files in manifest, defer rebuild | Smallest impl; leaves manifest temporarily inconsistent. | |

**User's choice:** Update manifest in place during migrate (Recommended).

---

## Claude's Discretion

- Exact string content of the `[graphify] error:` + `  hint:` refusal messages — format locked, content iterable during planning.
- Internal name of the singular→plural translation helper for `graphify_folder_mapping` lookups.
- Module location of the legacy-pattern constant (D-12) — `vault_promote.py` module-level vs. dedicated `_legacy_patterns.py`.

## Deferred Ideas

- Frontmatter augmentation contract (allowlist merge) — Phase 70 (VPROF-03 augmentation half).
- `graphify reverse-sync` command + modes + JSONL diff memory — Phase 70 (VRSYNC-01).
- `reverse_sync.auto_on_run` integration — Phase 70.
- `augment.allow_community: true` opt-in — Phase 70.
- `graphify undo-migrate` command — backlog if real users hit need.
- Profile-derived legacy detection as `--strict` opt-in for `doctor` — backlog.
- Timestamped `.bak.{ts}` migration history as `--keep-history` flag — backlog.
