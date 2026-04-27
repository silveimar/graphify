# Phase 25 — Discussion Log

**Date:** 2026-04-27
**Mode:** discuss (default), `--chain`
**Phase:** 25 — Mandatory Dual-Artifact Persistence in Skill Files

## Areas selected by user
All four presented gray areas:
- Canary + filename schema
- Artifact content schema
- Verbatim vs platform-paraphrase
- Trigger scope + placement

## Q&A

### Q1 — Canary string for SKILLMEM-04 grep
- **Options:** Hidden HTML-comment sentinel (Recommended) / Verbatim section heading / Literal filename token
- **User chose:** Hidden HTML-comment sentinel
- **Locked value:** `<!-- graphify:persistence-contract:v1 -->`

### Q2 — Filename `<TS>_<SLUG>` format for `CMD_<TS>_<SLUG>.{graph,human}.md`
- **Options:** UTC compact ISO + slug-6 (Recommended) / Epoch ms + sha8 / Leave format to harness
- **User chose:** UTC compact ISO + slug-6
- **Locked value:** `CMD_YYYYMMDDTHHMMSSZ_<command-kind>-<first-6-tokens>.{graph,human}.md`

### Q3 — Artifact content schema
- **Options:** Split by audience (Recommended) / Mirror with frontmatter on both / Minimal contract
- **User chose:** Split by audience
- **Locked value:**
  - `.human.md` = prose only
  - `.graph.md` = YAML frontmatter (`command`, `prompt`, `timestamp`, `graph_path`,
    `status`, `nodes_touched`, `edges_touched`, `communities_touched`) + fenced JSON body

### Q4 — Propagation across 10+ skill-*.md variants
- **Options:** Single source, copied verbatim (Recommended) / Source + per-platform paraphrase / Derive at install time
- **User chose:** Single source, copied verbatim
- **Locked value:** Author once in `graphify/skill.md`, copy byte-for-byte
  into all in-scope variants. `skill-excalidraw.md` excluded (different
  skill, no `query/path/explain/analyze`). Augment SKILLMEM-04 with a
  byte-equality check across blocks.

### Q5 — Trigger scope
- **Options:** Always including errors (Recommended) / Only successful non-empty / Errors to separate dir
- **User chose:** Always including errors
- **Locked value:**
  - Fires on every `query/path/explain/analyze` invocation
  - `status: error` (failure) and `status: empty` (no graph touch) emit valid pairs
  - Sub-second collisions resolved by appending `-1`, `-2`, …

### Q6 — Section placement in `graphify/skill.md`
- **Options:** Top-of-file global preamble (Recommended) / Appended per-command / Single section near end
- **User chose:** Top-of-file global preamble
- **Locked value:** Insert between current `## Usage` (line 12) and
  `## Available slash commands` (line 46), with sentinel on the line above
  the `## Mandatory response persistence` heading.

## Deferred / out-of-scope
- `graphify add` persistence — not in SKILLMEM-01..04 success criteria
- `skill-excalidraw.md` persistence — different skill
- Memory-dir retention/GC policy
- Harness-side validator subcommand

## Claude's discretion (not raised with user)
- Drift-defense byte-equality check across variants is added on top of
  SKILLMEM-04's grep — interpreted as the natural extension of "single
  source, verbatim copy" rather than a new requirement.
- `skill-excalidraw.md` excluded from in-scope variants because its skill
  surface (creating diagrams from prompts) does not include the four
  commands SKILLMEM-01 names. If user disagrees, this is the cheapest
  decision to flip.
