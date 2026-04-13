# Phase 8: Obsidian Round-Trip Awareness - Research

**Researched:** 2026-04-12
**Domain:** Merge engine extension — vault manifest, user-modified detection, sentinel preservation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** User sentinel blocks (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) are separate zones placed OUTSIDE graphify-managed sections. Non-overlapping ownership. Graphify sections managed by graphify; user blocks never touched.
- **D-02:** Malformed user sentinels (START without END, nested pairs, sentinels inside graphify-managed sections) trigger stderr warning. Note treated as if no user blocks — graphify proceeds with normal merge.
- **D-04:** `vault-manifest.json` stores whole-file SHA256 per note, computed at merge time. Uses `file_hash()` pattern from `cache.py`. Any file change (whitespace, frontmatter, body) counts as user-modified.
- **D-05:** `vault-manifest.json` written atomically via `os.replace()` after each successful `apply_merge_plan` call.
- **D-06:** Manifest entries include: `content_hash`, `last_merged` (ISO timestamp), `target_path`, `node_id`, `note_type`, `community_id`, `has_user_blocks` (boolean).
- **D-07:** User-modified notes (hash mismatch against manifest) receive `SKIP_PRESERVE` action — entire note left untouched. User content always wins. Default behavior on re-run.
- **D-08:** Content inside `<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->` is never overwritten by any merge action, even `REPLACE`. Sentinel blocks are inviolable.
- **D-09:** To refresh a user-modified note: delete the file. Next `--obsidian` run detects missing file (no manifest match) and creates fresh as CREATE action.
- **D-10:** `--obsidian --force` overrides D-07 for all notes: user-modified notes updated/replaced as if unmodified. User sentinel blocks (D-08) still preserved even with `--force`.
- **D-11:** Extend `format_merge_plan` table with `Source` column showing: `graphify` (unmodified), `user` (user-modified), or `both` (has sentinel blocks AND graphify sections).
- **D-12:** Dry-run output includes summary line: "{N} notes user-modified (will be preserved), {M} notes graphify-only (will update), {K} new notes (will create)".

### Claude's Discretion
- Multiple vs single USER_START/END blocks per note (D-03)
- `vault-manifest.json` file format details (JSON structure, indentation)
- Hash algorithm implementation details (whether to reuse `cache.file_hash()` directly or adapt)
- Error messages for manifest corruption, missing manifest on first run
- How `--force` interacts with `--dry-run` (likely: shows what would happen with force)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRIP-01 | `apply_merge_plan` writes `vault-manifest.json` recording content hash per note at merge time | `apply_merge_plan` already has a clear extension point at the end of its write loop; `file_hash()` from `cache.py` is the exact reuse target |
| TRIP-02 | On `--obsidian` re-run, graphify detects which notes user modified since last merge (hash comparison against manifest) | `compute_merge_plan` reads `previously_managed_paths` — manifest extends this with hash data; detection is pure dict comparison |
| TRIP-03 | User-modified notes receive `UPDATE_PRESERVE_USER_BLOCKS` merge action (locked to SKIP_PRESERVE per D-07) | CONTEXT.md locks this to `SKIP_PRESERVE`, not a new action type; the existing `MergeAction` dataclass and action vocabulary are reused |
| TRIP-04 | User-space sentinel blocks provide explicit preservation zones | New regex pair alongside existing `_SENTINEL_START_RE/_SENTINEL_END_RE`; `_parse_user_sentinel_blocks()` mirrors `_parse_sentinel_blocks()` |
| TRIP-05 | `--dry-run` output shows user modifications and merge plan | Extend `format_merge_plan()` with Source column (D-11) and summary line (D-12); `MergeAction` gains `user_modified: bool` and `has_user_blocks: bool` fields |
| TRIP-06 | User content always wins — never overwrite content between user sentinel blocks | Preserved in `_synthesize_file_text()` for `UPDATE`/`REPLACE`; sentinel extraction + re-injection pattern identical to existing graphify sentinel handling |
| TRIP-07 | Merge plan includes per-note modification source for audit trail | `MergeAction` extended with `source` field (`graphify`/`user`/`both`); emitted by both `compute_merge_plan` and `format_merge_plan` |
</phase_requirements>

## Summary

Phase 8 is a focused extension of the v1.0 merge engine (`merge.py`) with three additive changes: (1) a `vault-manifest.json` file written atomically after every `apply_merge_plan` call recording per-note SHA256 hashes; (2) a user-modified detection pass at the start of `compute_merge_plan` that reads the manifest and routes modified notes to `SKIP_PRESERVE`; and (3) a user-space sentinel block grammar (`<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->`) parsed alongside the existing graphify sentinel grammar and respected by all write paths.

The implementation footprint is small because all infrastructure already exists: `file_hash()` from `cache.py` provides the hash primitive; the atomic write pattern (`tmp + os.replace`) from `cache.py` and `merge._write_atomic` is the exact model; the sentinel block parser (`_parse_sentinel_blocks`) is the exact model for the user sentinel parser; and the `MergeAction` dataclass is frozen but gains two new optional fields (`user_modified`, `source`). The manifest itself is a flat JSON dict keyed by `target_path` string with the six D-06 fields per entry.

`--force` is the only new CLI flag. It threads through `__main__.py` → `to_obsidian()` → `compute_merge_plan()` as a keyword boolean. `format_merge_plan` gains a `Source` column and a two-line preamble summary (D-12). No new modules are needed — all work lands in `merge.py` with minor touch-points in `export.py` (manifest path threading) and `__main__.py` (`--force` parsing).

**Primary recommendation:** Extend `merge.py` with four new internal functions (`_load_manifest`, `_save_manifest`, `_detect_user_edits`, `_parse_user_sentinel_blocks`) and extend `MergeAction` with two optional fields. Touch `export.py` only to pass `manifest_path` through to `apply_merge_plan`. Parse `--force` in `__main__.py` and forward to `to_obsidian`.

## Standard Stack

### Core (all stdlib — no new dependencies)
| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `hashlib` (stdlib) | Python 3.10+ | SHA256 content hashing | Already used in `cache.py` and `merge._hash_bytes` |
| `json` (stdlib) | Python 3.10+ | Manifest serialization | Already used throughout codebase |
| `os.replace` (stdlib) | Python 3.10+ | Atomic file writes | Already the project pattern — `cache.save_cached`, `merge._write_atomic` |
| `datetime` (stdlib) | Python 3.10+ | ISO timestamp for `last_merged` | Already imported in `merge.py` |
| `pathlib.Path` (stdlib) | Python 3.10+ | Path handling | Project standard |

### No new dependencies
Phase 8 is entirely stdlib. The `[ASSUMED]` risk here is zero — the existing codebase confirms this.

**Installation:** No `pip install` required. `[VERIFIED: codebase grep]`

## Architecture Patterns

### Vault Manifest JSON Structure
```json
{
  "vault/path/to/Note.md": {
    "content_hash": "abc123...",
    "last_merged": "2026-04-12T10:30:00",
    "target_path": "vault/path/to/Note.md",
    "node_id": "transformer",
    "note_type": "thing",
    "community_id": 0,
    "has_user_blocks": false
  }
}
```

**Key design decisions (Claude's Discretion):**
- Keys are the string form of the vault-relative target_path (not absolute) — this makes manifests portable when the vault moves
- `indent=2` for human readability (matches existing JSON outputs like `graph.json`)
- Missing manifest on first run: `_load_manifest()` returns `{}` silently — graceful degradation to v1.0 behavior
- Corrupted manifest (JSONDecodeError): log warning to stderr, return `{}` — never abort

**Manifest path:** `graphify-out/vault-manifest.json` (alongside `graph.json`, `annotations.jsonl`)
[VERIFIED: codebase grep — all graphify sidecars live in `graphify-out/`]

### Pattern 1: Manifest Load/Save Helpers
```python
# Source: cache.py atomic write pattern (VERIFIED: codebase read)
def _load_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load vault-manifest.json, returning {} on missing or corrupt."""
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("[graphify] vault-manifest.json corrupted or unreadable — treating all notes as unmodified", file=sys.stderr)
        return {}

def _save_manifest(manifest_path: Path, manifest: dict[str, dict]) -> None:
    """Write manifest atomically via tmp + os.replace."""
    tmp = manifest_path.with_suffix(".json.tmp")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        os.replace(tmp, manifest_path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```
[VERIFIED: mirrors `cache.save_cached` pattern at cache.py lines 63-77]

### Pattern 2: User-Modified Detection in compute_merge_plan
```python
# Source: merge.py compute_merge_plan signature (VERIFIED: codebase read)
def compute_merge_plan(
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],
    profile: dict,
    *,
    skipped_node_ids: set[str] | None = None,
    previously_managed_paths: set[Path] | None = None,
    manifest: dict[str, dict] | None = None,   # NEW: pre-loaded manifest
    force: bool = False,                         # NEW: override SKIP_PRESERVE
) -> MergePlan:
    ...
    # In the per-file loop, after fingerprint check:
    if not force and manifest:
        key = str(target_path.relative_to(vault_dir))
        entry = manifest.get(key)
        if entry:
            stored_hash = entry.get("content_hash", "")
            current_hash = file_hash(target_path)
            if current_hash != stored_hash:
                # User modified — SKIP_PRESERVE
                actions.append(MergeAction(
                    path=target_path,
                    action="SKIP_PRESERVE",
                    reason="user-modified since last merge",
                    user_modified=True,
                    has_user_blocks=entry.get("has_user_blocks", False),
                    source="user",
                ))
                continue
```
[VERIFIED: merge.py lines 710-848 — compute_merge_plan signature and action dispatch]

### Pattern 3: User Sentinel Parser
```python
# Source: merge.py _parse_sentinel_blocks (VERIFIED: codebase read lines 267-328)
# Mirror the existing parser, replace regex with user sentinel patterns.
_USER_SENTINEL_START_RE = re.compile(r"<!--\s*GRAPHIFY_USER_START\s*-->")
_USER_SENTINEL_END_RE = re.compile(r"<!--\s*GRAPHIFY_USER_END\s*-->")

def _parse_user_sentinel_blocks(body: str) -> list[tuple[int, int]]:
    """Return list of (start_line_idx, end_line_idx) for user sentinel regions.
    
    D-03 (Claude's Discretion): supports multiple USER_START/END pairs per note.
    Multiple pairs are simpler for users (they can protect several content
    regions) and no harder to implement than single-pair support.
    
    Malformed pair (START without END, or END before START) → returns []
    and logs a warning. Per D-02: treat as if no user blocks, proceed normally.
    """
```

The multiple-pairs approach is recommended for D-03 because:
- Simpler implementation: just a list of ranges, no single-region invariant to enforce
- More useful for users protecting multiple sections
- Degenerate case (zero pairs) returns `[]` naturally
[ASSUMED: Claude's Discretion from D-03 — multiple pairs is simpler to use and equally simple to implement]

### Pattern 4: User Block Preservation in _synthesize_file_text
```python
# Source: merge.py _synthesize_file_text lines 901-938 (VERIFIED: codebase read)
# Extension for UPDATE/REPLACE actions: extract user sentinel regions BEFORE
# rewriting, then splice them back in AFTER.

def _extract_user_blocks(body: str) -> list[tuple[int, int, str]]:
    """Return list of (start_line, end_line, content) for user regions."""
    ...

def _restore_user_blocks(new_body: str, user_regions: list[tuple[int, int, str]]) -> str:
    """Re-insert user regions into new_body at corresponding line offsets.
    
    Challenge: line numbers shift when graphify-managed sections change.
    Resolution: use the sentinel markers themselves as anchor points — find
    GRAPHIFY_USER_START in new_body and splice content after it.
    """
```

**CRITICAL INSIGHT:** With D-07 locking user-modified notes to SKIP_PRESERVE, the case where a user sentinel block must survive a write is narrow: only notes NOT flagged as user-modified but containing user blocks (i.e., the hash still matches but the note has sentinel blocks). With `--force`, all notes are written, so sentinel preservation must be active. The preservation logic in `_synthesize_file_text` is the D-08 guarantee.

[VERIFIED: D-07 and D-08 from CONTEXT.md — two distinct mechanisms that together provide the guarantee]

### Pattern 5: MergeAction Extension
```python
# Source: merge.py MergeAction dataclass lines 83-95 (VERIFIED: codebase read)
@dataclass(frozen=True)
class MergeAction:
    path: Path
    action: Literal["CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"]
    reason: str
    changed_fields: list[str] = field(default_factory=list)
    changed_blocks: list[str] = field(default_factory=list)
    conflict_kind: str | None = None
    # New fields for Phase 8 (D-06, D-07, D-11):
    user_modified: bool = False
    has_user_blocks: bool = False
    source: str = "graphify"  # "graphify" | "user" | "both"
```

`MergeAction` is a frozen dataclass. Adding fields with defaults is backward-compatible — existing construction calls don't need to change. [VERIFIED: codebase read — all existing `MergeAction(...)` calls use keyword args for optional fields]

### Pattern 6: format_merge_plan Extension (D-11, D-12)
```python
# Source: merge.py format_merge_plan lines 1036-1079 (VERIFIED: codebase read)
# Add Source column to per-action lines:
#   SKIP_PRESERVE  vault/Note.md  [user-modified]
# Add preamble summary (D-12) before the "Merge Plan — N actions" header:
#   3 notes user-modified (will be preserved), 12 notes graphify-only (will update), 5 new notes (will create)
```

### Pattern 7: Manifest Written in apply_merge_plan
```python
# Source: merge.py apply_merge_plan lines 941-1029 (VERIFIED: codebase read)
def apply_merge_plan(
    plan: MergePlan,
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],
    profile: dict,
    *,
    manifest_path: Path | None = None,   # NEW: if None, skip manifest write
) -> MergeResult:
    ...
    # At end, after all writes succeed:
    if manifest_path is not None:
        new_manifest = _build_manifest_from_result(result, rendered_notes, vault_dir)
        _save_manifest(manifest_path, new_manifest)
```

**Key design:** Manifest is rebuilt from the full result (not incrementally updated). This avoids stale entries from prior runs — on each successful `apply_merge_plan`, the manifest reflects exactly what graphify last wrote. Notes in the vault that were SKIP_PRESERVE are NOT written to the manifest (their prior entry from the last merge remains, if any). [ASSUMED: this is the simplest correct behavior — a SKIP_PRESERVE note was not re-merged, so its last_merged timestamp should not update]

### Recommended Project Structure (no new files)
All changes land in existing modules:
```
graphify/
├── merge.py          # EXTEND: manifest helpers, user sentinel parser,
│                     #         MergeAction fields, compute/apply/format changes
├── export.py         # TOUCH: thread manifest_path through to_obsidian()
├── __main__.py       # TOUCH: parse --force, pass to to_obsidian()
└── builtin_templates/
    ├── thing.md      # TOUCH: add USER_START/END placeholder section
    ├── statement.md  # TOUCH: same
    ├── person.md     # TOUCH: same
    ├── source.md     # TOUCH: same
    ├── moc.md        # TOUCH: same
    └── community.md  # TOUCH: same
```

**Template placement:** User sentinel block placeholder should appear at the bottom of each built-in template's body section, after all graphify-managed callouts. It should be emitted as an EMPTY sentinel pair (no content) so users know where to place their content. The empty-string contract from D-18/templates.py is for graphify sections — user sentinel blocks are always emitted in templates regardless of content. [ASSUMED: empty-pair placement at bottom is the most discoverable location]

### Anti-Patterns to Avoid
- **Incremental manifest update:** Don't read old manifest and patch it — rebuild from result each time. Avoids stale entries when nodes are removed from the graph.
- **Hashing inside compute_merge_plan inner loop unconditionally:** Only hash when a manifest entry exists for that path. Avoids N disk reads for vaults where no manifest exists yet.
- **New action type for user-modified:** CONTEXT.md D-07 explicitly uses `SKIP_PRESERVE` — do NOT add `UPDATE_PRESERVE_USER_BLOCKS` as a new action enum value. The REQUIREMENTS.md TRIP-03 language ("UPDATE_PRESERVE_USER_BLOCKS") describes intent, but D-07 locks the implementation to `SKIP_PRESERVE`.
- **Storing absolute paths in manifest:** Store vault-relative paths as keys. Absolute paths break when vault is moved/synced.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHA256 hashing | Custom hash function | `cache.file_hash()` or `hashlib.sha256()` directly | Already tested, handles path disambiguation |
| Atomic file write | Custom temp-file strategy | `_write_atomic()` from `merge.py` or `os.replace()` + tmp | Already handles fsync, cleanup, OSError recovery |
| Sentinel block parsing | New regex-based parser from scratch | Mirror `_parse_sentinel_blocks` exactly | The existing parser has edge-case handling for nested, malformed, and duplicate blocks |
| Path confinement | Custom path validation | `_validate_target()` already in merge.py | Already guards against vault escape |

**Key insight:** Phase 8 has near-zero hand-rolling risk because every required primitive already exists in `cache.py` and `merge.py`.

## Common Pitfalls

### Pitfall 1: hash mismatch due to file_hash() including the resolved path
**What goes wrong:** `cache.file_hash()` hashes both content AND resolved path (`str(p.resolve()).encode()`). If the manifest is written with one resolved path and read later with another (e.g., symlink differences, macOS `/private/tmp` vs `/tmp`), hashes won't match even if content is identical.
**Why it happens:** `file_hash()` was designed for cache disambiguation, not for round-trip content tracking.
**How to avoid:** For manifest content hashing, use `hashlib.sha256(path.read_bytes()).hexdigest()` directly — hash ONLY the file content, not the path. This is a whole-file content hash, not a cache key. The manifest key (path string) is separate from the hash value.
**Warning signs:** Tests pass on Linux but fail on macOS due to symlink resolution differences.
[VERIFIED: cache.py lines 20-33 — file_hash() includes resolved path in hash input]

### Pitfall 2: Treating missing manifest as an error
**What goes wrong:** First run after upgrading to v1.1, or after a user deleted `graphify-out/`, raises FileNotFoundError instead of gracefully falling back.
**How to avoid:** `_load_manifest()` must return `{}` silently when file missing. Missing manifest = "no prior merge" = treat all existing notes as unmodified (v1.0 behavior).
[VERIFIED: CONTEXT.md and SUMMARY.md both specify graceful degradation]

### Pitfall 3: User sentinel blocks inside graphify-managed sections
**What goes wrong:** User places `<!-- GRAPHIFY_USER_START -->` inside a `<!-- graphify:connections:start -->` block. The graphify section refresh would overwrite the user content.
**Why it happens:** D-01 says they must be separate, but users can ignore this.
**How to avoid:** Per D-02: detect the overlap in `_parse_user_sentinel_blocks` — if any user sentinel line falls within a graphify sentinel range, log a warning and treat as malformed (return `[]` for that note). The note is then processed without user block preservation (regular merge).
**Warning signs:** User reports their content being overwritten after edits.
[VERIFIED: D-01 and D-02 from CONTEXT.md]

### Pitfall 4: SKIP_PRESERVE note's manifest entry not updated
**What goes wrong:** A note is SKIP_PRESERVE (user-modified). The manifest still holds the old content_hash from the last merge. On the NEXT run, the hash comparison runs against the still-outdated manifest entry, and the note is SKIP_PRESERVE again even if the user has reverted their changes.
**Why it matters:** This is actually CORRECT behavior. SKIP_PRESERVE notes should remain preserved until the user explicitly deletes them (D-09) or `--force` is used. The manifest should only update for notes that were actually re-written by graphify.
**Warning signs:** Tests incorrectly checking that manifest updates for SKIP_PRESERVE notes.
[VERIFIED: D-07, D-09 from CONTEXT.md]

### Pitfall 5: MergeAction frozen dataclass — adding fields breaks existing tests
**What goes wrong:** `MergeAction` is `@dataclass(frozen=True)`. Adding new fields with defaults is backward-compatible for construction, but any test that does `MergeAction(path=..., action=..., reason=...)` and then checks `dataclasses.asdict(action)` will now see extra keys.
**How to avoid:** New fields (`user_modified`, `has_user_blocks`, `source`) need default values (`False`, `False`, `"graphify"`). Existing test assertions on `asdict` output may need updating. Check test_merge.py for `asdict` usage.
[VERIFIED: merge.py lines 82-95 — dataclass is frozen; test_merge.py has 110 passing tests to protect]

### Pitfall 6: Built-in template user sentinel block position
**What goes wrong:** Placing the user sentinel placeholder INSIDE a graphify-managed section (e.g., inside the body sentinel region) violates D-01 and creates the overlap from Pitfall 3.
**How to avoid:** Place `<!-- GRAPHIFY_USER_START -->` / `<!-- GRAPHIFY_USER_END -->` markers at the END of the note body, AFTER the last graphify-managed sentinel pair. They should be outside all `<!-- graphify:*:start/end -->` blocks.
[VERIFIED: D-01 from CONTEXT.md]

### Pitfall 7: --force with --dry-run
**What goes wrong:** `--force --dry-run` shows the dry-run plan as-if force were active (modified notes would be updated, not skipped). If `--force` is silently ignored in dry-run, users get misleading output.
**How to avoid:** Claude's Discretion from CONTEXT.md suggests `--force --dry-run` shows what would happen with force. Pass `force=True` into `compute_merge_plan` even in dry-run mode — the plan reflects the forced strategy without writing.
[ASSUMED: consistent with "dry-run shows what would happen" design principle]

## Code Examples

### Example 1: Manifest write after apply_merge_plan
```python
# Source: merge.py apply_merge_plan + cache.py atomic write (VERIFIED: codebase read)
# At end of apply_merge_plan, after the write loop:
if manifest_path is not None:
    manifest: dict[str, dict] = {}
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for action in plan.actions:
        if action.action not in ("CREATE", "UPDATE", "REPLACE"):
            continue  # Only record notes graphify actually wrote
        rn = notes_by_path.get(action.path)
        if rn is None:
            continue
        if action.path in [p for p, _ in failed]:
            continue  # Don't record failed writes
        try:
            h = hashlib.sha256(action.path.read_bytes()).hexdigest()
        except OSError:
            continue
        key = str(action.path.relative_to(vault_dir))
        manifest[key] = {
            "content_hash": h,
            "last_merged": now,
            "target_path": key,
            "node_id": rn["node_id"],
            "note_type": rn.get("note_type", ""),
            "community_id": rn.get("community_id"),
            "has_user_blocks": _has_user_blocks(action.path.read_text(encoding="utf-8")),
        }
    _save_manifest(manifest_path, manifest)
```

### Example 2: User sentinel detection in compute_merge_plan
```python
# Source: merge.py compute_merge_plan existing fingerprint path (VERIFIED: codebase read lines 783-848)
# After fingerprint check passes, before strategy dispatch:
if not force and manifest:
    manifest_key = str(target_path.relative_to(vault_dir))
    entry = manifest.get(manifest_key)
    if entry:
        current_bytes = target_path.read_bytes()
        current_hash = hashlib.sha256(current_bytes).hexdigest()
        if current_hash != entry.get("content_hash", ""):
            # Detect user blocks in existing file
            has_blocks = bool(_parse_user_sentinel_blocks(existing_body))
            actions.append(MergeAction(
                path=target_path,
                action="SKIP_PRESERVE",
                reason="user-modified since last merge",
                user_modified=True,
                has_user_blocks=has_blocks,
                source="both" if has_blocks else "user",
            ))
            continue
```

### Example 3: format_merge_plan Source column (D-11)
```python
# Source: merge.py format_merge_plan lines 1036-1079 (VERIFIED: codebase read)
# D-12 preamble before the "Merge Plan" header:
user_mod_count = sum(1 for a in plan.actions if getattr(a, "user_modified", False))
graphify_only = sum(1 for a in plan.actions
                    if a.action in ("UPDATE", "REPLACE")
                    and not getattr(a, "user_modified", False))
new_count = sum(1 for a in plan.actions if a.action == "CREATE")
lines.insert(0, f"{user_mod_count} notes user-modified (will be preserved), "
               f"{graphify_only} notes graphify-only (will update), "
               f"{new_count} new notes (will create)")
lines.insert(1, "")

# D-11 Source column in per-action suffix:
def _format_action_suffix(action: MergeAction) -> str:
    source = getattr(action, "source", "graphify")
    source_tag = f"  [source:{source}]" if source != "graphify" else ""
    if action.action == "SKIP_PRESERVE":
        if getattr(action, "user_modified", False):
            return f"  [user-modified]{source_tag}"
    ...
```

### Example 4: to_obsidian manifest threading
```python
# Source: export.py to_obsidian lines 449-590 (VERIFIED: codebase read)
def to_obsidian(
    G, communities, output_dir, *, profile=None, community_labels=None,
    cohesion=None, dry_run=False, force=False,  # NEW: force kwarg
) -> "MergeResult | MergePlan":
    ...
    manifest_path = out.parent / "vault-manifest.json"  # graphify-out/vault-manifest.json
    manifest = _load_manifest(manifest_path) if not dry_run or force else {}
    # Actually load manifest even in dry-run to show accurate Source info:
    manifest = _load_manifest(manifest_path)

    result = compute_merge_plan(
        vault_dir=out,
        rendered_notes=rendered_notes,
        profile=profile,
        manifest=manifest,
        force=force,
        ...
    )
    if dry_run:
        return result  # MergePlan
    
    merge_result = apply_merge_plan(
        result, out, rendered_notes, profile,
        manifest_path=manifest_path,
    )
    return merge_result
```

**Note:** `manifest_path` should be `graphify-out/vault-manifest.json` — in the sibling directory of `obsidian_dir`, not inside it. `out` is the Obsidian vault output dir; its parent is `graphify-out/`. [VERIFIED: __main__.py line 974 — obsidian_dir defaults to "graphify-out/obsidian"]

### Example 5: --force CLI parsing
```python
# Source: __main__.py --obsidian block lines 965-1056 (VERIFIED: codebase read)
# Extend the existing arg parse loop:
elif args[i] == "--force":
    force = True; i += 1

# Pass through to_obsidian:
result = to_obsidian(G, communities, obsidian_dir, dry_run=dry_run, force=force)
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Multiple USER_START/END pairs per note is the better D-03 choice | Architecture Patterns (Pattern 3) | Low — both options work; multiple pairs is strictly more useful |
| A2 | Manifest keys are vault-relative paths (not absolute) | Architecture Patterns (Manifest JSON) | Medium — if absolute, manifests break on vault moves; easy to fix in tests |
| A3 | Empty user sentinel pair emitted in built-in templates at note bottom | Architecture Patterns (Project Structure) | Low — placement preference only, functional either way |
| A4 | `--force --dry-run` shows force-mode plan without writing | Common Pitfalls (Pitfall 7) | Low — Claude's Discretion from CONTEXT.md supports this reading |
| A5 | SKIP_PRESERVE notes are NOT updated in manifest (old hash preserved) | Common Pitfalls (Pitfall 4) | Low — D-07/D-09 logically imply this; no explicit statement in CONTEXT.md |
| A6 | manifest_path = graphify-out/vault-manifest.json (not inside obsidian_dir) | Code Examples (Example 4) | Medium — if inside obsidian_dir, Obsidian UI shows the JSON file as a vault note |

## Open Questions

1. **`note_type` and `community_id` in RenderedNote TypedDict**
   - What we know: `RenderedNote` TypedDict (merge.py lines 432-442) has fields `node_id`, `target_path`, `frontmatter_fields`, `body`. It does NOT have `note_type` or `community_id`.
   - What's unclear: To write these to the manifest (D-06), they must come from somewhere. `frontmatter_fields` contains `type` (note_type) and `community` (community display name, not community_id).
   - Recommendation: Extract `note_type` from `rn["frontmatter_fields"].get("type", "")` and `community_id` from the community's integer key in `rendered_notes` mapping (passed via the RenderedNote or retrieved from graph node data). Alternatively, add `note_type` and `community_id` to `RenderedNote` TypedDict (backward-compatible — both optional). The planner should decide whether to extend `RenderedNote` or derive from `frontmatter_fields`.

2. **has_user_blocks detection in manifest write**
   - What we know: After writing a note, we need to check if it has user sentinel blocks to record `has_user_blocks` in the manifest.
   - What's unclear: This requires reading the just-written file (or the written content) to detect user blocks.
   - Recommendation: Pass the written content string to `_has_user_blocks(text)` — no extra disk read needed since we already have `new_text` from `_synthesize_file_text()`.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — all stdlib additions, no new tools or services required).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_merge.py -q` |
| Full suite command | `pytest tests/ -q` |

[VERIFIED: `python3 -m pytest tests/test_merge.py -q` runs 110 tests in 0.15s]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRIP-01 | `apply_merge_plan` writes manifest after successful merge | unit | `pytest tests/test_merge.py -q -k "manifest"` | ❌ Wave 0 |
| TRIP-01 | Manifest written atomically (tmp + replace) | unit | `pytest tests/test_merge.py -q -k "manifest_atomic"` | ❌ Wave 0 |
| TRIP-01 | Manifest not written when no manifest_path passed | unit | `pytest tests/test_merge.py -q -k "manifest_none"` | ❌ Wave 0 |
| TRIP-02 | Hash mismatch → SKIP_PRESERVE with user_modified=True | unit | `pytest tests/test_merge.py -q -k "user_modified"` | ❌ Wave 0 |
| TRIP-02 | Hash match → normal merge action | unit | `pytest tests/test_merge.py -q -k "hash_match"` | ❌ Wave 0 |
| TRIP-02 | Missing manifest → graceful fallback (no skip) | unit | `pytest tests/test_merge.py -q -k "missing_manifest"` | ❌ Wave 0 |
| TRIP-02 | Corrupted manifest JSON → warning + fallback | unit | `pytest tests/test_merge.py -q -k "corrupt_manifest"` | ❌ Wave 0 |
| TRIP-03 | SKIP_PRESERVE reason contains "user-modified" | unit | `pytest tests/test_merge.py -q -k "skip_preserve_user"` | ❌ Wave 0 |
| TRIP-04 | `_parse_user_sentinel_blocks` finds paired markers | unit | `pytest tests/test_merge.py -q -k "user_sentinel"` | ❌ Wave 0 |
| TRIP-04 | Malformed user sentinels → warning + empty list | unit | `pytest tests/test_merge.py -q -k "user_sentinel_malformed"` | ❌ Wave 0 |
| TRIP-04 | Multiple USER_START/END pairs detected | unit | `pytest tests/test_merge.py -q -k "user_sentinel_multiple"` | ❌ Wave 0 |
| TRIP-05 | `format_merge_plan` includes preamble summary line (D-12) | unit | `pytest tests/test_merge.py -q -k "format_preamble"` | ❌ Wave 0 |
| TRIP-05 | `format_merge_plan` Source column shows "user" for modified note | unit | `pytest tests/test_merge.py -q -k "format_source"` | ❌ Wave 0 |
| TRIP-06 | User sentinel content preserved in REPLACE action | unit | `pytest tests/test_merge.py -q -k "sentinel_preserve_replace"` | ❌ Wave 0 |
| TRIP-06 | User sentinel content preserved in UPDATE action | unit | `pytest tests/test_merge.py -q -k "sentinel_preserve_update"` | ❌ Wave 0 |
| TRIP-07 | MergeAction.source field populated correctly | unit | `pytest tests/test_merge.py -q -k "merge_action_source"` | ❌ Wave 0 |
| TRIP-07 | Audit trail includes "both" for note with user blocks + graphify sections | unit | `pytest tests/test_merge.py -q -k "source_both"` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_merge.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
All Phase 8 test functions are new additions to the existing `tests/test_merge.py` file.
- [ ] Test class `TestVaultManifest` — covers TRIP-01
- [ ] Test class `TestUserModifiedDetection` — covers TRIP-02, TRIP-03
- [ ] Test class `TestUserSentinelParser` — covers TRIP-04
- [ ] Test class `TestFormatMergePlanRoundTrip` — covers TRIP-05, TRIP-07
- [ ] Test class `TestUserSentinelPreservation` — covers TRIP-06

Existing tests in `test_merge.py` (110 passing) must remain green — new tests are additive.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `sanitize_label()` from `security.py` for any user-supplied content in manifest; `_validate_target()` for path confinement |
| V6 Cryptography | no | SHA256 is for content fingerprinting, not security-sensitive |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via vault-relative manifest key | Tampering | `_validate_target()` already in merge.py; manifest key written from already-validated `action.path.relative_to(vault_dir)` — cannot escape |
| User sentinel content injection via node labels | Tampering | `sanitize_label()` from `security.py` already applied at extraction time; user sentinel CONTENT is never read by graphify (only preserved as-is) |
| Manifest poisoning (corrupt JSON to disable round-trip) | Denial of Service | `_load_manifest()` falls back to `{}` on corrupt JSON — user-visible warning, no crash |
| `--force` bypassing preservation | Elevation of Privilege | Expected behavior per D-10; user sentinels still preserved even with `--force` — D-08 is inviolable |

**Security assessment:** Phase 8 has LOW security surface area. The critical invariant is that `vault-manifest.json` is written to `graphify-out/` (not inside the vault), and all path handling goes through the existing `_validate_target()` gate. No new external input paths are opened.

## Sources

### Primary (HIGH confidence)
- `graphify/merge.py` (codebase read) — `MergeAction`, `MergePlan`, `compute_merge_plan`, `apply_merge_plan`, `format_merge_plan`, `_parse_sentinel_blocks`, `_write_atomic` — all verified in session
- `graphify/cache.py` (codebase read) — `file_hash()`, `save_cached()` atomic write pattern, `_body_content()` — verified in session
- `graphify/templates.py` (codebase read) — `_SENTINEL_START_FMT/_SENTINEL_END_FMT`, sentinel grammar — verified in session
- `graphify/export.py` (codebase read) — `to_obsidian()` signature and pipeline — verified in session
- `graphify/__main__.py` (codebase read) — `--obsidian` arg parsing lines 965-1056 — verified in session
- `.planning/phases/08-obsidian-round-trip-awareness/08-CONTEXT.md` (project read) — all locked decisions D-01 through D-12 — verified in session
- `pytest tests/test_merge.py -q` (live run) — 110 tests pass, 0.15s — verified in session

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — Phase 8 architecture note: "extends merge.py with detect_user_edits(), merge_with_user_blocks(), and PARTIAL_UPDATE action type" — note: D-07 locks action to SKIP_PRESERVE, not a new PARTIAL_UPDATE action; STATE.md predates the CONTEXT.md discussion
- `.planning/research/SUMMARY.md` — Phase 8 deliverables summary — consistent with CONTEXT.md

### Tertiary (LOW confidence)
None — all claims verified against codebase or CONTEXT.md.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, verified in codebase
- Architecture: HIGH — all patterns derived directly from existing `merge.py` code, verified line-by-line
- Pitfalls: HIGH — all derived from code analysis (file_hash path inclusion, frozen dataclass, sentinel overlap)
- Test mapping: HIGH — test framework verified running, test class structure derived from REQUIREMENTS.md

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable — all v1.0 code is locked, no fast-moving dependencies)

---
*Phase: 08-obsidian-round-trip-awareness*
*Research completed: 2026-04-12*
