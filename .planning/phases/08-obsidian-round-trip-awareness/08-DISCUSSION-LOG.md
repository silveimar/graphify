# Phase 8: Obsidian Round-Trip Awareness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 08-obsidian-round-trip-awareness
**Areas discussed:** User block sentinels, Change detection, Merge conflict policy, Dry-run presentation

---

## User Block Sentinels

### Q1: Sentinel relationship to graphify sentinels

| Option | Description | Selected |
|--------|-------------|----------|
| Separate zones (Recommended) | User sentinels mark user-authored blocks OUTSIDE graphify-managed sections. Simple, clear ownership boundary. | ✓ |
| Inline within graphify sections | Users can place USER_START/END inside a graphify-managed section. More flexible but harder to implement. | |
| You decide | Claude picks the simplest approach | |

**User's choice:** Separate zones (Recommended)

### Q2: Multiple blocks per note

| Option | Description | Selected |
|--------|-------------|----------|
| Multiple blocks allowed | Users can sprinkle USER_START/END pairs throughout the note. | |
| One block per note | Only the first pair is honored. Simpler implementation. | |
| You decide | Claude picks based on implementation complexity | ✓ |

**User's choice:** You decide

### Q3: Malformed sentinels

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and skip preservation | Print warning to stderr, treat note as having no user blocks. | ✓ |
| Warn and protect everything after START | If END is missing, treat everything from START to EOF as protected. | |
| You decide | Claude picks the safest approach | |

**User's choice:** Warn and skip preservation

---

## Change Detection

### Q1: Hash strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Whole-file content hash (Recommended) | SHA256 of entire file content. Simple, reliable. Uses cache.py pattern. | ✓ |
| Per-section hashes | Separate hashes for frontmatter, each section, each user block. | |
| You decide | Claude picks based on requirements | |

**User's choice:** Whole-file content hash (Recommended)

### Q2: Manifest metadata

| Option | Description | Selected |
|--------|-------------|----------|
| Hash + timestamp + path only | Minimal: content_hash, last_merged, target_path per note. | |
| Hash + metadata + source info | Also store: node_id, note_type, community_id, has_user_blocks. | ✓ |
| You decide | Claude picks based on requirements | |

**User's choice:** Hash + metadata + source info

---

## Merge Conflict Policy

### Q1: Content outside sentinel blocks

| Option | Description | Selected |
|--------|-------------|----------|
| Graphify wins outside sentinels | Graphify refreshes all managed sections; user edits outside sentinels overwritten. | |
| Preserve all user changes | If user modified anything, skip update entirely (SKIP_PRESERVE). | ✓ |
| Smart merge | Update graphify sections, preserve user sentinels, keep user frontmatter changes. | |

**User's choice:** Preserve all user changes

### Q2: Refresh mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Delete note to refresh | User deletes file, next run creates fresh. | |
| graphify refresh command | New CLI subcommand for force re-merge. | |
| Both: delete works + flag for force | Delete always works; also add --force flag to --obsidian. | ✓ |

**User's choice:** Both: delete works + flag for force

---

## Dry-Run Presentation

### Q1: Dry-run format

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing table (Recommended) | Add Source column + summary line at top. Minimal change to format_merge_plan. | ✓ |
| Separate user-modified section | New section listing user-modified notes with detail. | |
| You decide | Claude picks based on existing pattern | |

**User's choice:** Extend existing table (Recommended)

---

## Claude's Discretion

- Multiple vs single USER_START/END blocks per note
- vault-manifest.json internal format details
- Hash algorithm reuse from cache.py
- Error handling for manifest corruption
- --force + --dry-run interaction

## Deferred Ideas

None — discussion stayed within phase scope
