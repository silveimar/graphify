# Phase 69: VPROF — Vault Profile-Driven Folder Resolution & User-Namespace Guard - Research

**Researched:** 2026-05-05
**Domain:** vault_promote.py refactor — profile-driven folder resolution, pre-flight refusal, legacy artifact detection
**Confidence:** HIGH (all findings verified from codebase; no external dependencies)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `graphify_folder_mapping` defaults (singular keys, plural-capitalized paths under Atlas/Sources/Graphify/):
```yaml
graphify_folder_mapping:
  thing:     Atlas/Sources/Graphify/Things/
  question:  Atlas/Sources/Graphify/Questions/
  map:       Atlas/Sources/Graphify/Maps/
  person:    Atlas/Sources/Graphify/People/
  quote:     Atlas/Sources/Graphify/Quotes/
  statement: Atlas/Sources/Graphify/Statements/
  source:    Atlas/Sources/Graphify/Sources/
```
**D-02:** `map` bucket → `Maps/` (not `MOCs/`). `Atlas/Sources/Graphify/` parent disambiguates.
**D-03:** Lookup keys are **singular** (`thing`, not `things`). Internal bucket keys translated via small helper.
**D-04:** Unknown types fall back to `Atlas/Sources/Graphify/<Type>/`. One-line INFO to stderr. Never refuse; never drop.
**D-05:** Silent in-place rewrite of `profile.yaml` on first read of v1. Renames `folder_mapping` → `graphify_folder_mapping`. Idempotent.
**D-06:** Single `profile.yaml.bak` alongside; overwrites on each migration (no `.bak.bak`).
**D-07:** Migrator is the ONLY graphify code path that writes to `.graphify/` in this phase.
**D-08:** Defense-in-depth: pre-flight pass (collects ALL violations) + `_write_record()` chokepoint (`_assert_under_pinned_subtree` on every write). Pre-flight runs BEFORE manifest-hash overwrite guard.
**D-09:** Atomic batch refusal — any pre-flight violation aborts the entire run. Zero partial writes.
**D-10:** Two-line stderr format:
```
[graphify] error: refused N write(s) targeting user-owned folders
  hint: <list every offending target with record_type and user_only_folders rule; suggest editing graphify_folder_mapping>
```
**D-11:** Manifest-hash overwrite guard at `vault_promote.py:702-732` is PRESERVED. New pre-flight runs before it. Covered by a regression test simulating a name collision.
**D-12:** Hardcoded glob list for legacy detection — `_COMM*.md` at vault root, `Community*.md` under `Atlas/Maps/`, any file outside `Atlas/Sources/Graphify/` carrying the `graphify_manifest_hash` frontmatter key. Module-level constant.
**D-13:** `--migrate-legacy` is dry-run by default. `--migrate-legacy --apply` performs moves. Applied to `graphify update-vault`.
**D-14:** In-place atomic manifest update during migrate. Move + manifest write are coupled; rollback if either fails. No stale-manifest window.
**D-15:** `graphify doctor` legacy-artifact section is read-only by default. Non-blocking warning section. Doctor exits non-zero only for blocking issues (existing behavior).

### Claude's Discretion
- Exact wording of `[graphify] error:` + `  hint:` strings (must contain offending targets, record types, violated rule, suggested action).
- Name of the singular→plural translation helper (D-03).
- Location of legacy pattern constant (D-12) — `vault_promote.py` module-level or small `_legacy_patterns.py`.

### Deferred Ideas (OUT OF SCOPE)
- Frontmatter augmentation merge contract (Phase 70).
- `graphify reverse-sync` command and modes (Phase 70).
- `auto_on_run` integration (Phase 70).
- `augment.allow_community: true` opt-in (Phase 70).
- `graphify undo-migrate` command.
- Timestamped `.bak.{ts}` history.
- Profile-derived legacy detection (`--strict` mode).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VPROF-01 | Profile schema v2 — add `graphify_folder_mapping`, `user_only_folders`, `augment.allow_community`, `reverse_sync.*`; one-shot migrator from `folder_mapping` → `graphify_folder_mapping` | Profile loaded via `load_profile()` in `profile.py`; migrator hooks there before merge with `_DEFAULT_PROFILE` |
| VPROF-02 | All vault writes resolve folder from `profile.graphify_folder_mapping[<type>]`. Remove hardcoded literals at `vault_promote.py:206-299` and `_DEFAULT_LAYERS` at `vault_promote.py:873-879` | `classify_nodes()` hardcodes `folder` field; `_FOLDER_PATH_PREFIX` dict at line ~873 drives `promote()` loop; both must become profile-derived |
| VPROF-03 (refusal half) | Pre-flight refusal when writes target `user_only_folders`. Manifest-hash guard preserved and covered by regression test | `write_note()` at 702-732 is the existing guard; new `_write_record()` chokepoint wraps it |
| VPROF-04 | `graphify doctor` detects legacy artifacts; `graphify update-vault --migrate-legacy [--apply]` relocates them | Doctor command at `__main__.py:3167`; calls `graphify.doctor.run_doctor`; new section added |
</phase_requirements>

## Summary

Phase 69 is a targeted regression fix: `vault_promote.py` ignores the vault profile for folder routing, writing notes to hardcoded `Atlas/Dots/Things/`, `Atlas/Maps/`, etc. instead of profile-driven paths under `Atlas/Sources/Graphify/`. The fix has four interlocking parts: (1) profile schema upgrade + migrator, (2) removal of two hardcoded routing structures and replacement with profile-derived lookup, (3) pre-flight refusal guard for `user_only_folders`, (4) `graphify doctor` legacy detection + `update-vault --migrate-legacy`.

The codebase is well-structured for this change. All vault writes flow through a single module (`vault_promote.py`) and a single write function (`write_note()`). The profile system (`profile.py`) already has a `load_profile()` entry point and `_DEFAULT_PROFILE` that can be extended. Security patterns (`validate_vault_path`) are established and must be reused for the new `_assert_under_pinned_subtree` guard. The doctor command is a separate module (`graphify/doctor.py`) with a `run_doctor()` + `format_report()` API.

One non-obvious gap: the `graphify_manifest_hash` frontmatter key referenced in D-12 does NOT exist in the codebase yet. Current vault-promote notes embed `graphifyProject` and `graphifyRun` frontmatter keys, not `graphify_manifest_hash`. Either the detection must use `graphifyProject` as the ownership marker, or Phase 69 must introduce `graphify_manifest_hash` to note frontmatter as part of the implementation. This must be resolved before planning the legacy-detection task.

**Primary recommendation:** Implement in four waves — (Wave 1) profile schema + migrator in `profile.py`, (Wave 2) folder-resolution refactor in `vault_promote.py`, (Wave 3) pre-flight refusal, (Wave 4) doctor section + `--migrate-legacy`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile schema v2 + migrator | `profile.py` | `__main__.py` (CLI args for schema keys) | All profile loading/merging is in `profile.py`; `load_profile()` is the single entry point |
| Folder resolution (replace hardcoded paths) | `vault_promote.py` — `classify_nodes()`, `_FOLDER_PATH_PREFIX` | `profile.py` — `_DEFAULT_PROFILE` defaults | classify_nodes builds folder field; `_FOLDER_PATH_PREFIX` drives the promote() loop |
| Pre-flight refusal + chokepoint guard | `vault_promote.py` — new `_preflight_check()` + `_write_record()` | `profile.py` — `validate_vault_path` reuse | All writes are already in vault_promote; refusal must be there |
| Legacy artifact detection | `graphify/doctor.py` — new section | `vault_promote.py` — detection helper | doctor.py calls vault_promote helper; doctor is read-only |
| `--migrate-legacy` moves | `vault_promote.py` — `migrate_legacy_artifacts()` | `__main__.py` — new CLI flag on `update-vault` | Moves are vault writes; must go through vault_promote's write discipline |

## Standard Stack

### Core (no new dependencies)

| Component | Where | Version | Notes |
|-----------|-------|---------|-------|
| `graphify/profile.py` | Profile loading, migrator, schema | existing | `load_profile()`, `_DEFAULT_PROFILE`, `_apply_taxonomy_folder_mapping()`, `validate_vault_path()` all here |
| `graphify/vault_promote.py` | Folder resolution, write guard, migrate | existing | `classify_nodes()`, `_FOLDER_PATH_PREFIX`, `write_note()`, `promote()` |
| `graphify/doctor.py` | Legacy detection report section | existing | `run_doctor()`, `format_report()`, `DoctorReport` dataclass |
| `graphify/__main__.py` | CLI — `update-vault --migrate-legacy` flag, `vault-promote` | existing | `cmd == "update-vault"` block at line 3283 |
| PyYAML (`yaml`) | Profile YAML read/write | optional extra | Already optional; migrator must guard `import yaml` with try/except ImportError |

**Installation:** No new packages. PyYAML is already an optional dependency (`pip install graphifyy[obsidian]`).

### Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path confinement | Custom path escape check | `validate_vault_path(candidate, vault_dir)` from `profile.py` | Already handles symlinks, `..`, absolute paths; tested |
| Atomic file write | Open + write + close directly | `_write_atomic(target, content)` from `vault_promote.py` (uses `os.replace`) | Cross-platform atomic rename already implemented |
| Manifest JSON read/write | Direct `json.loads`/`json.dumps` | `_load_manifest()` / `_save_manifest()` from `vault_promote.py` | Handles corrupt file gracefully; atomic write |
| YAML deep merge | Recursive dict merge | `_deep_merge(base, override)` from `profile.py` | Last-wins merge already tested across profile chain |
| Frontmatter serialization | Custom YAML dump | `_dump_frontmatter(fields)` from `profile.py` | Handles quoting, order, special chars |

## Architecture Patterns

### System Architecture Diagram

```
graphify vault-promote / update-vault
        |
        v
   __main__.py (CLI)
        |
        |---> load_profile(vault_path)        [profile.py]
        |          |
        |          +--> detect v1 profile? --> migrate in-place --> write .bak
        |          |    (folder_mapping → graphify_folder_mapping)
        |          +--> _deep_merge(_DEFAULT_PROFILE, user_profile)
        |          +--> return merged profile with graphify_folder_mapping
        |
        |---> _preflight_check(records, profile)    [vault_promote.py — NEW]
        |          |
        |          +--> for each resolved target path:
        |               is_relative_to(user_only_folder)? → collect violation
        |          |
        |          +--> any violations? → stderr error+hint → sys.exit(non-zero)
        |
        |---> promote(graph_path, vault_path, threshold, profile)
        |          |
        |          +--> classify_nodes(G, communities, profile)
        |          |       |
        |          |       +--> _resolve_folder(record_type, profile)   [NEW]
        |          |            reads profile["graphify_folder_mapping"][singular_key]
        |          |            fallback: Atlas/Sources/Graphify/<Type>/
        |          |
        |          +--> for each record:
        |               _write_record(record_type, rel_path, content, manifest, profile)  [NEW chokepoint]
        |                   |
        |                   +--> _assert_under_pinned_subtree(abs_path, profile)  [NEW]
        |                   +--> write_note(vault_dir, rel_path, content, manifest)  [existing guard D-13]
        |
        +--> _save_manifest(manifest, graphify_out)

graphify doctor
        |
        +--> run_doctor(cwd, ...)               [doctor.py]
        |       |
        |       +--> _detect_legacy_artifacts(profile, vault_path)  [vault_promote.py — NEW]
        |               glob _LEGACY_GLOB_PATTERNS
        |               check frontmatter for ownership marker
        |               return list[LegacyArtifact]
        |
        +--> format_report(report)
                |
                +--> legacy-artifacts section (non-blocking warning)

graphify update-vault --migrate-legacy [--apply]
        |
        +--> _detect_legacy_artifacts(...)
        +--> if dry-run: print move plan, exit
        +--> if --apply: for each artifact:
                move file → new_path (atomic)
                update manifest entry (atomic)
                rollback on failure
```

### Recommended Project Structure

No new files strictly required. Additions within existing modules:

```
graphify/
├── profile.py           # + migrate_profile_v1_to_v2(), _DEFAULT_PROFILE extended
├── vault_promote.py     # + _resolve_folder(), _preflight_check(), _write_record(),
│                        #   _assert_under_pinned_subtree(), _detect_legacy_artifacts(),
│                        #   migrate_legacy_artifacts(), _LEGACY_GLOB_PATTERNS,
│                        #   _FOLDER_PATH_PREFIX removed → profile-derived
├── doctor.py            # + legacy-artifact section in run_doctor() / format_report()
├── __main__.py          # + --migrate-legacy / --apply flags on update-vault
tests/
├── test_vault_promote.py  # + regression test manifest-hash guard (D-11)
│                          # + profile-driven folder routing tests
│                          # + pre-flight refusal tests
│                          # + migrate-legacy tests
└── test_profile.py        # + migrator tests (v1 → v2, idempotent, .bak)
```

## Detailed Code Findings

### Finding 1: Two separate hardcoded-folder structures in vault_promote.py

**`classify_nodes()` at lines 206-299 — the `folder` field in each record dict:**

```python
result["things"].append({
    "node_id": nid,
    "label": gn["label"],
    "folder": "Atlas/Dots/Things/",   # ← HARDCODED
    "score": degree,
})
# ... similarly for questions ("Atlas/"), maps ("Atlas/Maps/"),
#     people ("Atlas/Dots/People/"), quotes ("Atlas/Quotes/"),
#     statements ("Atlas/Dots/Statements/"), sources ("Atlas/Sources/")
```

The `folder` field from `classify_nodes()` is NOT used by `promote()`. Instead, `promote()` ignores `record["folder"]` and uses `_FOLDER_PATH_PREFIX[bucket_key]` for the `rel_path` construction. This means the `folder` field in classification records is only consumed by tests and potentially by `render_note()` for frontmatter.

**`_FOLDER_PATH_PREFIX` at lines ~873-879 — drives the actual writes:**

```python
_FOLDER_PATH_PREFIX: dict[str, str] = {
    "things": "Atlas/Dots/Things",
    "questions": "Atlas/Dots/Questions",
    "statements": "Atlas/Dots/Statements",
    "people": "Atlas/Dots/People",
    "quotes": "Atlas/Dots/Quotes",
    "maps": "Atlas/Maps",
    "sources": "Atlas/Sources/Clippings",
}
```

Used in `promote()` as: `prefix = _FOLDER_PATH_PREFIX[bucket_key]` → `rel_path = f"{prefix}/{filename_stem}.md"`.

**Action:** Both must be replaced. The `folder` field in classification records should be computed from the profile. `_FOLDER_PATH_PREFIX` is removed; `promote()` calls `_resolve_folder(bucket_key, profile)` instead.

### Finding 2: Bucket key translation (plural → singular for D-03)

The internal bucket keys in `classify_nodes()` are plural: `things`, `questions`, `maps`, `people`, `quotes`, `statements`, `sources`. The D-01 profile keys are singular: `thing`, `question`, `map`, `person`, `quote`, `statement`, `source`. A small translation dict is needed:

```python
_BUCKET_TO_SINGULAR: dict[str, str] = {
    "things": "thing",
    "questions": "question",
    "maps": "map",
    "people": "person",
    "quotes": "quote",
    "statements": "statement",
    "sources": "source",
}
```

Used by `_resolve_folder(bucket_key, profile)`.

### Finding 3: Profile load flow — where migrator hooks in

`load_profile()` in `profile.py` (line 554):

```
load_profile(vault_dir)
  → profile_path = vault_dir / ".graphify" / "profile.yaml"
  → if not exists: return _apply_taxonomy_folder_mapping(_deep_merge(_DEFAULT_PROFILE, {}))
  → _resolve_profile_chain(profile_path, vault_dir)  # walks extends/includes
  → _validate_required_v18_user_profile(resolved.composed)
  → validate_profile(resolved.composed)
  → _apply_taxonomy_folder_mapping(_deep_merge(_DEFAULT_PROFILE, resolved.composed))
```

The migrator must run immediately after reading the YAML file (before `_resolve_profile_chain`), or as a separate step called by `load_profile()`. The cleanest hook: after the file exists check and before `_resolve_profile_chain`, call `_migrate_profile_v1_to_v2_if_needed(profile_path)`. This function:

1. Reads the raw YAML.
2. If `folder_mapping` key present AND `graphify_folder_mapping` NOT present: renames, writes `.bak`, rewrites `profile.yaml`.
3. Returns (idempotent — `graphify_folder_mapping` already present → no-op).

**YAML guard:** Must wrap `import yaml` in try/except ImportError. If PyYAML not installed, skip migration (the profile can't be read anyway — `load_profile` already handles this case).

### Finding 4: Manifest-hash overwrite guard at lines 702-732

This is `write_note()`, not a named "manifest-hash guard" function. The decision table:

```python
def write_note(vault_dir, rel_path, content, manifest):
    abs_target = validate_vault_path(vault_dir / rel_path, vault_dir)
    disk_hash = _hash_bytes(abs_target) if abs_target.exists() else None
    prior = manifest.get(rel_path)

    if prior is None and disk_hash is None:     → write ("written")
    if prior is None and disk_hash is not None: → skip ("skipped_foreign")
    if prior == disk_hash:                      → overwrite ("overwritten")
    # else: manifest entry exists but disk differs → skip ("skipped_user_modified")
```

This guard prevents graphify from overwriting user-edited files. It is preserved unchanged. The new `_write_record()` chokepoint calls `write_note()` as its final step.

**Regression test needed:** Simulate a scenario where two different record types produce the same `rel_path` (name collision under the pinned subtree). The second write should return `"skipped_user_modified"` or `"overwritten"` per the decision table — proving the guard fires even within the pinned subtree.

### Finding 5: `graphify_manifest_hash` frontmatter key — gap identified

D-12 specifies detecting files with `graphify_manifest_hash` frontmatter key. This key does NOT exist in the codebase. Current vault-promote notes embed `graphifyProject` and `graphifyRun` in frontmatter (lines 509-510, 626-627). The `vault-manifest.json` file tracks ownership by path+hash but does NOT inject anything into note frontmatter.

**Resolution options (planner must pick one):**

Option A: Use `graphifyProject` (already present in all graphify-written notes) as the ownership marker for D-12 detection. No new frontmatter key needed.

Option B: Introduce `graphify_manifest_hash` as a new frontmatter field in `_build_frontmatter_fields()` — adds it to every note going forward, enabling the D-12 detection pattern. Requires updating existing test assertions that check frontmatter content.

Option A is lower risk for Phase 69. Option B is cleaner but has test churn. The planner should decide.

### Finding 6: `doctor.py` section structure

`doctor.py` has:
- `DoctorReport` dataclass (fields: `profile_validation_errors`, `profile_validation_warnings`, `preview`, `resolved_output`, `has_explicit_route`)
- `is_misconfigured()` → returns `True` for validation errors / unresolvable / would_self_ingest
- `run_doctor(cwd, dry_run, resolved_output)` → populates `DoctorReport`
- `format_report(report)` → renders sectioned `[graphify]-prefixed` text

New legacy-artifact section:
- Populated by `run_doctor()` calling `_detect_legacy_artifacts(profile, vault_path)` from `vault_promote.py`
- Added to `DoctorReport` as a new field (e.g., `legacy_artifacts: list[LegacyArtifact]`)
- Rendered by `format_report()` as a warning section (non-blocking; does NOT set `is_misconfigured()` to True per D-15)

### Finding 7: `update-vault` command — where --migrate-legacy flag attaches

The `update-vault` command at `__main__.py:3283` uses `argparse` with flags: `--input`, `--vault`, `--repo-identity`, `--router`, `--verbose`, `--apply`, `--plan-id`. The `--migrate-legacy` and `--apply` (already exists) flags are added to this subcommand. When `--migrate-legacy` is set: skip the normal migration path (`run_update_vault`) and call `migrate_legacy_artifacts(vault_path, profile, apply=opts.apply)` from `vault_promote.py`.

Note: `--apply` currently means "apply a reviewed migration plan with --plan-id". The `--migrate-legacy --apply` pattern creates a second meaning for `--apply`. The planner may want to use `--migrate-legacy-apply` as a single flag to avoid ambiguity. This is Claude's discretion.

### Finding 8: Existing test fixture patterns

From `test_vault_promote.py`:

- Tests use `tmp_path` exclusively — no real filesystem side effects.
- `_make_graph_json_from_fixture(tmp_path)` helper creates a synthetic graph JSON.
- Tests for `write_note()` create `vault = tmp_path / "vault"`, call `write_note()` directly.
- The `test_end_to_end_all_seven_folders` test (line 652) checks that `promote()` writes to the 7 hardcoded folder paths — **this test will break** after Phase 69's refactor. It must be updated to check the new profile-driven paths.
- All import-log and manifest tests use `graphify_out = tmp_path / "graphify-out"`.

New tests must follow the same `tmp_path` pattern. Profile tests in `test_profile.py` use the same approach.

## Common Pitfalls

### Pitfall 1: `classify_nodes()` folder field vs. `_FOLDER_PATH_PREFIX`

**What goes wrong:** Removing hardcoded `folder` from classification records but forgetting `_FOLDER_PATH_PREFIX` in `promote()` — or vice versa. The two are independent: classification records carry a `folder` field used in test assertions and possibly in `render_note()` frontmatter; `promote()` uses `_FOLDER_PATH_PREFIX` for the actual write path.

**How to avoid:** Trace every consumer of the `folder` field in classification records (tests + `render_note()`). Replace both independently. Verify `render_note()` uses `folder_type` (the `_BUCKET_TO_FOLDER_TYPE` value like `"Things"`) not the `folder` path string.

**Warning signs:** Tests that assert `record["folder"] == "Atlas/Dots/Things/"` will fail — update them to check the profile-derived path.

### Pitfall 2: `_apply_taxonomy_folder_mapping()` silently clobbers `graphify_folder_mapping`

**What goes wrong:** After adding `graphify_folder_mapping` to `_DEFAULT_PROFILE`, `_apply_taxonomy_folder_mapping()` recomputes and writes to `profile["folder_mapping"]` (the legacy surface). If the code reads from `folder_mapping` instead of `graphify_folder_mapping`, the taxonomy-derived paths override the user's explicit mapping.

**How to avoid:** The Phase 69 code must read from `profile["graphify_folder_mapping"]`, not `profile["folder_mapping"]`. After migration, the v1 `folder_mapping` key is retired from being the routing source.

**Warning signs:** Tests with custom profile mappings route to wrong folders.

### Pitfall 3: Pre-flight check runs after profile migration but before classify_nodes

**What goes wrong:** If pre-flight is called with stale profile (before migrator runs), it uses v1 paths that may not match user's intent.

**How to avoid:** Execution order must be: (1) `load_profile()` — migrator fires here, (2) pre-flight on resolved targets, (3) classify + write. Since `promote()` already calls `load_profile()` first, this is naturally handled — but the planner must ensure `_preflight_check()` takes the MERGED profile (post-migration).

### Pitfall 4: `graphify_manifest_hash` key does not exist

**What goes wrong:** The D-12 legacy detection pattern uses `graphify_manifest_hash` frontmatter key that no current note contains. Legacy detection would find zero artifacts even on a vault with real legacy content.

**How to avoid:** Use `graphifyProject` OR `graphifyRun` as the ownership marker (they are present in all graphify-written notes). OR introduce `graphify_manifest_hash` now. Decide before implementing the detection.

### Pitfall 5: YAML round-trip loses comments and key ordering

**What goes wrong:** `yaml.safe_load()` + `yaml.dump()` drops YAML comments and may reorder keys, surprising users who hand-crafted their `profile.yaml`.

**How to avoid:** The migrator only renames ONE key (`folder_mapping` → `graphify_folder_mapping`). Use string manipulation on the raw file content for the rename if preserving format matters, OR accept that `yaml.dump(allow_unicode=True, sort_keys=True)` sorts keys (consistent with `_writeback_profile()` which already does this).

**Warning signs:** User reports that their profile comments disappeared after running graphify.

### Pitfall 6: `--migrate-legacy --apply` ambiguity with existing `--apply`

**What goes wrong:** `update-vault --apply` already means "apply a reviewed migration plan (with --plan-id)". Adding `--migrate-legacy` that also uses `--apply` creates two different meanings for `--apply` depending on whether `--migrate-legacy` is present.

**How to avoid:** Use `--migrate-legacy-apply` as a single combined flag, OR document that `--apply` behavior is determined by the presence of `--migrate-legacy`. The planner must decide the CLI shape.

### Pitfall 7: Test `test_end_to_end_all_seven_folders` hardcodes old paths

**What goes wrong:** The test checks `vault / "Atlas" / "Dots" / "Things"` etc. After Phase 69, the default paths are `Atlas/Sources/Graphify/Things/` etc. Test will fail.

**How to avoid:** Update this test in Wave 2 as part of the folder-resolution refactor. The new paths under `Atlas/Sources/Graphify/` must be what the test asserts.

## Code Examples

### Pattern 1: Profile-driven folder resolution

```python
# In vault_promote.py
_BUCKET_TO_SINGULAR: dict[str, str] = {
    "things": "thing",
    "questions": "question",
    "maps": "map",
    "people": "person",
    "quotes": "quote",
    "statements": "statement",
    "sources": "source",
}

_DEFAULT_GRAPHIFY_FOLDER_MAPPING: dict[str, str] = {
    "thing":     "Atlas/Sources/Graphify/Things/",
    "question":  "Atlas/Sources/Graphify/Questions/",
    "map":       "Atlas/Sources/Graphify/Maps/",
    "person":    "Atlas/Sources/Graphify/People/",
    "quote":     "Atlas/Sources/Graphify/Quotes/",
    "statement": "Atlas/Sources/Graphify/Statements/",
    "source":    "Atlas/Sources/Graphify/Sources/",
}

def _resolve_folder(bucket_key: str, profile: dict) -> str:
    """Resolve the vault-relative folder path for a bucket_key using profile.graphify_folder_mapping."""
    singular = _BUCKET_TO_SINGULAR.get(bucket_key, bucket_key)
    mapping = profile.get("graphify_folder_mapping") or _DEFAULT_GRAPHIFY_FOLDER_MAPPING
    folder = mapping.get(singular)
    if folder is None:
        # D-04: unknown type falls back; emit INFO
        capitalized = singular.capitalize() + "s"
        folder = f"Atlas/Sources/Graphify/{capitalized}/"
        print(f"[graphify] info: unknown record type '{singular}' — writing to {folder}. "
              f"Add it to graphify_folder_mapping in your profile.", file=sys.stderr)
    return folder.rstrip("/")
```

### Pattern 2: Pre-flight refusal (collect-all, atomic batch abort)

```python
# In vault_promote.py
def _assert_under_pinned_subtree(abs_path: Path, vault_dir: Path, profile: dict) -> None:
    """Raise ValueError if abs_path falls under any user_only_folder."""
    user_only = profile.get("user_only_folders") or _DEFAULT_USER_ONLY_FOLDERS
    for uf in user_only:
        blocked = (vault_dir / uf).resolve()
        try:
            abs_path.relative_to(blocked)
            raise ValueError(f"{abs_path} is under user-only folder {uf!r}")
        except ValueError as e:
            if "user-only" in str(e):
                raise

def _preflight_check(resolved_paths: list[tuple[str, Path]], profile: dict, vault_dir: Path) -> None:
    """Collect all user_only_folder violations; raise on first batch (D-08, D-09)."""
    violations = []
    for record_type, abs_path in resolved_paths:
        user_only = profile.get("user_only_folders") or _DEFAULT_USER_ONLY_FOLDERS
        for uf in user_only:
            blocked = (vault_dir / uf).resolve()
            try:
                abs_path.relative_to(blocked)
                violations.append((record_type, abs_path, uf))
                break
            except ValueError:
                pass
    if violations:
        detail = "; ".join(
            f"{rt} → {p} (violates '{uf}')" for rt, p, uf in violations
        )
        print(
            f"[graphify] error: refused {len(violations)} write(s) targeting user-owned folders\n"
            f"  hint: {detail}. Edit graphify_folder_mapping in .graphify/profile.yaml "
            f"to redirect these record types under Atlas/Sources/Graphify/.",
            file=sys.stderr,
        )
        sys.exit(1)
```

### Pattern 3: Profile migrator (v1 → v2 in-place)

```python
# In profile.py
def _migrate_profile_v1_to_v2_if_needed(profile_path: Path) -> None:
    """Rename folder_mapping → graphify_folder_mapping in profile.yaml (idempotent)."""
    try:
        import yaml
    except ImportError:
        return  # can't migrate without PyYAML; load_profile handles this case
    raw = profile_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if "graphify_folder_mapping" in data:
        return  # already v2, idempotent
    if "folder_mapping" not in data:
        return  # no old key to migrate
    # Write .bak then rewrite
    bak_path = profile_path.with_suffix(".yaml.bak")
    bak_path.write_text(raw, encoding="utf-8")
    data["graphify_folder_mapping"] = data.pop("folder_mapping")
    profile_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=True), encoding="utf-8")
```

### Pattern 4: Legacy artifact detection (D-12)

```python
# In vault_promote.py
_LEGACY_GLOB_PATTERNS: list[tuple[str, str]] = [
    # (glob_relative_to_vault_root, description)
    ("_COMM*.md", "community note at vault root"),
    ("Atlas/Maps/Community*.md", "community MOC under Atlas/Maps/"),
]
_LEGACY_FRONTMATTER_OWNERSHIP_KEY = "graphifyProject"  # or "graphify_manifest_hash" if introduced

def _detect_legacy_artifacts(vault_path: Path, profile: dict) -> list[dict]:
    """Detect graphify-written notes outside the profile-pinned subtree."""
    pinned_root = Path(
        (profile.get("graphify_folder_mapping") or {}).get("thing", "Atlas/Sources/Graphify/Things/")
    ).parts[0:3]  # e.g. ("Atlas", "Sources", "Graphify")
    pinned_prefix = Path(*pinned_root)
    results = []
    # Glob-based patterns
    for pattern, desc in _LEGACY_GLOB_PATTERNS:
        for match in vault_path.glob(pattern):
            results.append({"path": match, "reason": desc, "pattern": pattern})
    # Frontmatter-based (files with graphifyProject outside pinned subtree)
    # ... scan vault for .md files with the ownership marker
    return results
```

### Pattern 5: Existing `write_note()` — the guard that must be preserved [VERIFIED: codebase]

```python
# vault_promote.py:702-732 — DO NOT MODIFY
def write_note(vault_dir: Path, rel_path: str, content: str, manifest: dict[str, str]) -> str:
    abs_target = validate_vault_path(vault_dir / rel_path, vault_dir)
    disk_hash = _hash_bytes(abs_target) if abs_target.exists() else None
    prior = manifest.get(rel_path)
    if prior is None and disk_hash is None:
        _write_atomic(abs_target, content)
        manifest[rel_path] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return "written"
    if prior is None and disk_hash is not None:
        return "skipped_foreign"
    if prior == disk_hash:
        _write_atomic(abs_target, content)
        manifest[rel_path] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return "overwritten"
    return "skipped_user_modified"
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path escape check | Custom `".." in str(path)` | `validate_vault_path(candidate, vault_dir)` | Handles symlinks, case; already tested; used in write_note already |
| Atomic file write | `open()` + `write()` | `_write_atomic(target, content)` | Uses `os.replace()` — atomic on POSIX + Windows; already exists |
| YAML safe load | Direct `open` + `yaml.load` | `yaml.safe_load()` | Never `yaml.load()` (code injection risk) |
| Deep dict merge | Custom recursive merge | `_deep_merge(base, override)` from `profile.py` | Last-wins; already tested |
| Frontmatter emit | Custom YAML string concat | `_dump_frontmatter(fields)` from `profile.py` | Handles quoting, insertion order |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `pytest tests/test_vault_promote.py tests/test_profile.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VPROF-01 | Migrator renames `folder_mapping` → `graphify_folder_mapping` | unit | `pytest tests/test_profile.py::test_migrator_renames_key -x` | ❌ Wave 0 |
| VPROF-01 | Migrator is idempotent (second run is no-op) | unit | `pytest tests/test_profile.py::test_migrator_idempotent -x` | ❌ Wave 0 |
| VPROF-01 | Migrator writes `.bak` | unit | `pytest tests/test_profile.py::test_migrator_writes_bak -x` | ❌ Wave 0 |
| VPROF-02 | promote() routes to profile-mapped folder | unit | `pytest tests/test_vault_promote.py::test_profile_folder_routing -x` | ❌ Wave 0 |
| VPROF-02 | Unknown type falls back to Atlas/Sources/Graphify/\<Type\>/ | unit | `pytest tests/test_vault_promote.py::test_unknown_type_fallback -x` | ❌ Wave 0 |
| VPROF-02 | test_end_to_end_all_seven_folders updated to new paths | unit | `pytest tests/test_vault_promote.py::test_end_to_end_all_seven_folders -x` | ✅ (update) |
| VPROF-03 | Pre-flight refuses write targeting user_only_folders (zero partial writes) | unit | `pytest tests/test_vault_promote.py::test_preflight_refusal_atomic -x` | ❌ Wave 0 |
| VPROF-03 | Manifest-hash guard regression — name collision within pinned subtree | unit | `pytest tests/test_vault_promote.py::test_manifest_hash_guard_regression -x` | ❌ Wave 0 |
| VPROF-03 | Pre-flight runs before manifest-hash check (ordering) | unit | `pytest tests/test_vault_promote.py::test_preflight_before_manifest_guard -x` | ❌ Wave 0 |
| VPROF-04 | doctor detects `_COMM*.md` at vault root | unit | `pytest tests/test_vault_promote.py::test_detect_legacy_comm_at_root -x` | ❌ Wave 0 |
| VPROF-04 | doctor detects `Community*.md` under `Atlas/Maps/` | unit | `pytest tests/test_vault_promote.py::test_detect_legacy_community_maps -x` | ❌ Wave 0 |
| VPROF-04 | `--migrate-legacy` dry-run prints plan, no moves | unit | `pytest tests/test_vault_promote.py::test_migrate_legacy_dry_run -x` | ❌ Wave 0 |
| VPROF-04 | `--migrate-legacy --apply` moves files + updates manifest | unit | `pytest tests/test_vault_promote.py::test_migrate_legacy_apply -x` | ❌ Wave 0 |

### Sampling Rate

- Per task commit: `pytest tests/test_vault_promote.py tests/test_profile.py -q`
- Per wave merge: `pytest tests/ -q`
- Phase gate: Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test functions in `tests/test_vault_promote.py` — all VPROF-02/03/04 tests above
- [ ] New test functions in `tests/test_profile.py` — all VPROF-01 migrator tests above
- [ ] Update `test_end_to_end_all_seven_folders` to assert new Atlas/Sources/Graphify/ paths

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `classify_nodes()` `folder` field is NOT used by `promote()` for the write path; `_FOLDER_PATH_PREFIX` drives writes | Code Findings #1 | If `folder` IS used by `promote()`, removing it from records would break write routing |
| A2 | `graphifyProject` frontmatter key is present in ALL graphify-written vault notes (as the ownership marker for D-12 detection) | Code Findings #5 | If some old notes lack it, detection misses them |
| A3 | `--apply` on `update-vault` can safely be overloaded with `--migrate-legacy` to mean "apply the legacy migration" | Code Findings #7 | If users combine flags confusingly, CLI behavior is undefined |

**A1 is HIGH confidence** — verified by reading both `classify_nodes()` (lines 206-299) and `promote()` (lines ~940-975); `promote()` only uses `_FOLDER_PATH_PREFIX[bucket_key]`.

**A2 is MEDIUM confidence** — verified that NEW notes get `graphifyProject` (lines 509-510), but legacy notes from Phase 19 era may predate this field.

**A3 is LOW confidence** — planner should evaluate whether a separate `--migrate-legacy-apply` flag avoids ambiguity.

## Open Questions (RESOLVED)

1. **`graphify_manifest_hash` frontmatter key vs `graphifyProject`** — **RESOLVED:** use `graphifyProject` as the Phase 69 ownership marker for legacy detection. Zero test churn. `graphify_manifest_hash` is deferred to Phase 70 if reverse-sync needs it.

2. **`user_only_folders` default list** — **RESOLVED:** default to `[]` (empty list — opt-in). Users must declare `user_only_folders` explicitly in `profile.yaml`. Rationale: graphify cannot know which folders a given vault treats as user-owned without the user's input; an empty default avoids false-refusals on non-Ideaverse vaults. The Ideaverse-specific list (`Atlas/`, `Calendar/`, `Efforts/`, `+/`, `x/`, vault root) belongs in the user's profile, not as a global default. (Captured as D-16 in CONTEXT.md.)

3. **`--migrate-legacy` CLI flag shape** — **RESOLVED:** use two separate flags. `--migrate-legacy` is dry-run; `--migrate-legacy-apply` is a single combined flag that performs the moves. This avoids collision with `--apply` semantics elsewhere on `update-vault`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | `_assert_under_pinned_subtree` + pre-flight refusal |
| V5 Input Validation | yes | `validate_vault_path()` on all paths; YAML `safe_load()` only |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via profile `graphify_folder_mapping` values | Tampering | `validate_vault_path(candidate, vault_dir)` — already used in `write_note()`; reuse in `_assert_under_pinned_subtree` |
| YAML injection via profile template placeholders | Tampering | `yaml.safe_load()` only; `safe_frontmatter_value()` for any user-derived strings in frontmatter |
| User-only folder bypass via symlink | Tampering | `Path.resolve()` before `relative_to()` check (existing pattern in `validate_vault_path`) |

## Sources

### Primary (HIGH confidence — codebase verification)

- `graphify/vault_promote.py` (994 lines) — lines 195-310 (`classify_nodes`), 636-740 (`write_note` + manifest), 860-994 (`_FOLDER_PATH_PREFIX`, `promote`)
- `graphify/profile.py` — lines 69-100 (`_DEFAULT_PROFILE`), 340-362 (`_apply_taxonomy_folder_mapping`), 554-595 (`load_profile`), 1481-1498 (`validate_vault_path`)
- `graphify/__main__.py` — lines 3167-3400 (`doctor`, `update-vault`, `vault-promote` commands)
- `graphify/doctor.py` — `DoctorReport` dataclass, `run_doctor()`, `format_report()`, `is_misconfigured()`
- `tests/test_vault_promote.py` (860 lines) — all test patterns and fixtures
- `.planning/REQUIREMENTS.md` lines 41-45 — VPROF-01..04 definitions
- `.planning/phases/69-*/69-CONTEXT.md` — all decisions D-01..D-15

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all in existing codebase, no external dependencies
- Architecture: HIGH — verified by reading the actual code paths
- Pitfalls: HIGH for items verified in code; MEDIUM for YAML round-trip behavior (platform-dependent)

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (stable Python codebase; no fast-moving external dependencies)
