# Phase 14: Obsidian Thinking Commands - Research

**Researched:** 2026-04-22
**Domain:** Slash-command installer refactor + Obsidian vault-aware command authoring (skill.md orchestration over MCP tools)
**Confidence:** HIGH

## Summary

Phase 14 is not a feature invention phase — it is an **orchestration + installer refactor** phase. All P1 command behavior is already available as MCP tools (`get_community`, `get_focus_context`, `connect_topics`, `get_agent_edges`, `propose_vault_note`) and all vault-rendering plumbing exists (`graphify.profile.load_profile` + `_approve_and_write_proposal` merge engine). What ships is: (1) a symmetry-restoring refactor of `_uninstall_commands` from a hardcoded whitelist to a directory-scan, (2) a frontmatter-driven `target: obsidian|code|both` filter inside the already-glob-based `_install_commands`, (3) four skill.md-orchestrated slash-command prose files, (4) `target: both` backfill on the 9 existing commands so Plan 01 does not silently regress them.

The shape is directly analogous to Phase 16 (`/graphify-argue`) and Phase 17 (`/graphify-ask`): thin Python substrate, fat skill.md orchestration, every LLM-driven decision lives in prose, every data fetch lives in an MCP tool that already exists.

**Primary recommendation:** Ship Plan 00 (whitelist → directory-scan), then Plan 01 (frontmatter filter + `target: both` backfill + `supports: [...]` per `_PLATFORM_CONFIG` entry + `--no-obsidian-commands` flag), then 4 independent command plans (02..05) that can be parallelized because each is a standalone `.md` file authoring task. No new Python modules required for Plans 02-05 — each command is a prose file that calls existing MCP tools and routes writes through `propose_vault_note`.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Defer all P2 (OBSCMD-09..12) to v1.4.x. Phase 14 ships 6 plans total: Plan 00 (refactor), Plan 01 (frontmatter filter), Plan 02 (`/graphify-moc`), Plan 03 (`/graphify-related`), Plan 04 (`/graphify-orphan`), Plan 05 (`/graphify-wayfind`).
- **D-02:** `/graphify-related` requires an explicit `<note-path>` `$ARGUMENTS` — no active-note auto-detect. Reads note YAML frontmatter `source_file`, then calls `get_focus_context(focus_hint={"file_path": source_file})`. Matches `/graphify-ask` pattern.
- **D-03:** `/graphify-moc` uses vault profile first with built-in fallback via existing `graphify.profile.load_profile(vault_path)` — no new loader work.
- **D-04:** Frontmatter filter lives at runtime parse time in `_install_commands`. Each command `.md` carries `target: obsidian | code | both`. Each `_PLATFORM_CONFIG` entry gains `supports: [...]` list. 9 existing commands need `target: both` backfilled.
- **D-05:** `/graphify-orphan` emits two labeled sections: `## Isolated Nodes` (community=null) and `## Stale/Ghost Nodes` (staleness=GHOST from `enrichment.json`). Must degrade gracefully when `enrichment.json` is absent (Phase 15 is optional/async).
- **D-06:** Every vault write routes through `propose_vault_note` + `graphify approve`. Never auto-write. v1.1 trust boundary is an invariant across all P1 commands.

### Claude's Discretion

- **Plan 00 refactor shape:** glob `graphify/commands/*.md` at uninstall time and remove matching names in `dst_dir`, or persist an install manifest. Recommended: glob approach, optionally with a content-hash check that only removes files whose content matches what was installed. Planner owns this.
- **Wayfind MOC-root heuristic:** How `/graphify-wayfind` picks the MOC root (largest-community MOC? user-designated home note?). Acceptable default: "largest community's MOC, tie-break by lowest community_id." Planner decides.

### Deferred Ideas (OUT OF SCOPE)

- `/graphify-bridge` (OBSCMD-09) — v1.4.x.
- `/graphify-voice` (OBSCMD-10) — v1.4.x or later, needs anti-impersonation design.
- `/graphify-drift-notes` (OBSCMD-11) — v1.4.x.
- `trigger_pipeline` frontmatter + cost-preview banner (OBSCMD-12) — v1.4.x.
- MOC-root heuristic productization (user-designated home note config) — future milestone.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBSCMD-01 | Plan 00: `_uninstall_commands()` whitelist → directory-scan | Current code at `__main__.py:157-172` — 7-name tuple; `_install_commands` at line 141 already uses `sorted(src_dir.glob("*.md"))`. Symmetry restored by applying the same glob on uninstall. |
| OBSCMD-02 | Command frontmatter `target: obsidian|code|both` + `_install_commands()` platform filter + `--no-obsidian-commands` flag | Runtime parse in `_install_commands` via stdlib (no new dep — see Standard Stack). `_PLATFORM_CONFIG` already holds per-platform dicts; add `supports: [...]`. `--no-commands` flag precedent at `__main__.py:1675`. |
| OBSCMD-03 | `/graphify-moc <community_id>` via `get_community` + profile template | `get_community(community_id)` exists at `serve.py:2747`; `load_profile` at `profile.py:128` with `obsidian.dataview.moc_query` template. `/graphify-argue` is the skill.md pattern reference. |
| OBSCMD-04 | `/graphify-related <note-path>` via note frontmatter `source_file` → `get_focus_context` | `get_focus_context` tool signature at `mcp_tool_registry.py:290`, required `focus_hint.file_path`. `/graphify-ask` is the skill.md pattern reference. |
| OBSCMD-05 | `/graphify-orphan` dual-section (isolated + ghost) | Isolated = nodes with no community assignment (read `community` attr on `G.nodes[n]`); ghost = `enrichment.json[staleness][node_id] == "GHOST"`. Phase 15 schema verified at `enrich.py:502-510`. |
| OBSCMD-06 | `/graphify-wayfind` via `connect_topics` shortest-path | `connect_topics` tool at `serve.py:2918`, called by Phase 11 `/connect`. Same D-02 envelope pattern as `connect.md`. |
| OBSCMD-07 | `/graphify-*` prefix convention + collision prevention | Install-time frontmatter-name check (all new commands must start with `graphify-`). 9 existing commands lack the prefix — they stay under their current names (backward compat). |
| OBSCMD-08 | All writes route through `propose_vault_note` + `graphify approve` | `propose_vault_note` MCP tool at `mcp_tool_registry.py:161` writes to `graphify-out/proposals/` only. `_approve_and_write_proposal` at `__main__.py:898` is the consuming write path. Test invariant: grep each P1 skill prose for "propose_vault_note" and assert absence of any direct-write helper reference. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Platform-aware command install | Python CLI (`__main__.py`) | — | Single source of truth for where files land per platform. Frontmatter filter reads files at install time — still in the CLI tier. |
| Frontmatter parsing at install time | Python CLI (stdlib only) | — | Avoid adding PyYAML as a hard dep (it is optional under `mcp`/`obsidian`/`routing`). Three-line YAML block is trivially parseable with a regex that matches `^target:\s*(obsidian|code|both)\s*$`. |
| Slash-command LLM orchestration | skill.md prose | MCP tools | D-73 invariant (Phase 16): LLM orchestration lives in skill.md, never in Python. Python substrate exposes deterministic tools; the agent drives flow. |
| Graph data retrieval | MCP tools (`serve.py`) | — | All 5 consumed tools already exist and are stable. No new Python work in Plans 02-05. |
| Vault write staging | MCP `propose_vault_note` | `graphify approve` CLI | v1.1 trust-boundary invariant. Two-step: MCP stages JSON proposal → user invokes CLI `approve` → merge engine writes to vault. |
| Vault profile resolution | `graphify.profile.load_profile` | `_DEFAULT_PROFILE` fallback | Already implemented; vault-first with built-in Ideaverse-compatible fallback. Exercised end-to-end by `_approve_and_write_proposal` at `__main__.py:920`. |
| Staleness signal source | `enrichment.json` (Phase 15 overlay) | Graceful absence | MUST degrade gracefully — Phase 15 is async/optional. Read-without-create; if absent, show isolated section only with a `_Note: run graphify enrich to populate ghost detection._` banner. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `pathlib.Path` | 3.10+ | File discovery and path handling in installer | Already pervasive in `__main__.py`; zero new dep. [VERIFIED: graphify/__main__.py]|
| Python stdlib `re` | 3.10+ | Frontmatter `target:` line parser (regex over first-block text) | Avoids PyYAML as hard dep; matches existing lightweight frontmatter parsing in `test_commands.py`. [VERIFIED: tests/test_commands.py uses `re.findall` on source] |
| Python stdlib `shutil.copy` | 3.10+ | File installation | Already used at `__main__.py:150`. [VERIFIED: graphify/__main__.py:150] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `graphify.profile.load_profile` | in-repo | Vault profile + template resolution for `/graphify-moc` | D-03; already exists at `profile.py:128`. [VERIFIED: grep in graphify/profile.py] |
| `graphify.mcp_tool_registry.build_mcp_tools` + `serve.py` handlers | in-repo | All 5 consumed MCP tools | Tool handlers are in `serve.py`; registry in `mcp_tool_registry.py`. [VERIFIED: grep of both files] |
| `enrichment.json` overlay (Phase 15) | in-repo | GHOST staleness source for `/graphify-orphan` | Written by `enrich.py`; schema keys = canonical `node_id`, value `∈ {FRESH, STALE, GHOST}`. [VERIFIED: enrich.py:506 `valid_labels`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib regex frontmatter parse | PyYAML | PyYAML is already optional but would become mandatory for install — violates CLAUDE.md "no new required dependencies" Ideaverse-Integration constraint. Regex parse is sufficient for a single `target:` key in a fixed first block. |
| Install manifest file | Directory-scan on uninstall | Manifest adds a persistence surface (drift if hand-edited, corruption risk). Directory-scan is stateless, symmetric with install (D-04 + D-05 in Claude's discretion). |
| Auto-detect active Obsidian note | Explicit `<note-path>` arg | Platform fragmentation (Claude Code ≠ Codex ≠ Droid ≠ opencode) — no portable "active note" signal. D-02 already locks explicit arg. |

**Installation:** No new packages. Phase 14 is additive code + `.md` files inside existing package layout.

**Version verification:** `[ASSUMED]` — no new deps, no version-verification needed. [CITED: pyproject.toml lines 13, 43-54]

## Architecture Patterns

### System Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         Phase 14 Data & Control Flow                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─── CLI install time ────────────────────────────────────────────────────────┐
│                                                                              │
│  graphify install --platform <P>                                             │
│            │                                                                 │
│            ▼                                                                 │
│  _install_commands(cfg, src_dir)                                             │
│    ├─ for f in sorted(glob("commands/*.md")):                                │
│    │    target = parse_frontmatter_target(f)         ◄── Plan 01            │
│    │    if target in cfg["supports"] or target=="both":                     │
│    │        shutil.copy(f, cfg["commands_dst"])                              │
│    └─ (file lands in ~/.claude/commands/ or equivalent)                      │
│                                                                              │
│  graphify uninstall --platform <P>                                           │
│            │                                                                 │
│            ▼                                                                 │
│  _uninstall_commands(cfg)                           ◄── Plan 00             │
│    └─ for src in glob("commands/*.md"):                                      │
│         (cfg["commands_dst"] / src.name).unlink(missing_ok=True)             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─── Runtime: user invokes /graphify-moc 7 ───────────────────────────────────┐
│                                                                              │
│  User types /graphify-moc 7 in Claude Code                                   │
│            │                                                                 │
│            ▼                                                                 │
│  Claude reads ~/.claude/commands/graphify-moc.md (prose orchestration)       │
│            │                                                                 │
│            ▼                                                                 │
│  [SKILL.md prose directs:]                                                   │
│    1. Call MCP get_community(community_id=7)                                 │
│            │                                                                 │
│            ▼                                                                 │
│  serve.py::_tool_get_community → nodes list                                  │
│            │                                                                 │
│            ▼                                                                 │
│    2. [Claude] Load vault profile, render MOC body per moc_query template   │
│       (LLM drives template substitution from profile.obsidian.dataview)      │
│            │                                                                 │
│            ▼                                                                 │
│    3. Call MCP propose_vault_note(title, body_markdown, suggested_folder)    │
│            │                                                                 │
│            ▼                                                                 │
│  serve.py::_tool_propose_vault_note → JSON record in                         │
│                                        graphify-out/proposals/<id>.json      │
│            │                                                                 │
│            ▼                                                                 │
│    4. [Claude summarizes to user] "Proposed MOC staged; run                  │
│                                    `graphify approve <id>` to write."        │
│                                                                              │
│  User invokes: graphify approve <id>                                         │
│            │                                                                 │
│            ▼                                                                 │
│  __main__.py::_approve_and_write_proposal                                    │
│    ├─ load profile → compute_merge_plan → apply_merge_plan                   │
│    └─ writes to vault with sentinel-block preservation                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─── Runtime: /graphify-orphan ───────────────────────────────────────────────┐
│                                                                              │
│  [SKILL.md prose directs Claude to:]                                         │
│    A. Read graphify-out/graph.json → list nodes with community ∈ {null,−1}  │
│    B. Read graphify-out/enrichment.json if exists → list staleness==GHOST   │
│    C. If enrichment.json missing: emit section B with absence banner        │
│    D. Render two sections, each proposing a remediation note via             │
│       propose_vault_note (or write inline summary only — planner decides)    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
graphify/
├── commands/                         # unchanged location
│   ├── argue.md                      # existing — BACKFILL `target: both`
│   ├── ask.md                        # existing — BACKFILL `target: both`
│   ├── challenge.md                  # existing — BACKFILL `target: both`
│   ├── connect.md                    # existing — BACKFILL `target: both`
│   ├── context.md                    # existing — BACKFILL `target: both`
│   ├── drift.md                      # existing — BACKFILL `target: both`
│   ├── emerge.md                     # existing — BACKFILL `target: both`
│   ├── ghost.md                      # existing — BACKFILL `target: both`
│   ├── trace.md                      # existing — BACKFILL `target: both`
│   ├── graphify-moc.md               # NEW  — target: obsidian
│   ├── graphify-related.md           # NEW  — target: obsidian
│   ├── graphify-orphan.md            # NEW  — target: obsidian  (or both)
│   └── graphify-wayfind.md           # NEW  — target: obsidian
├── __main__.py                       # Plan 00 + Plan 01 edits here
└── (no new modules)
```

### Pattern 1: Skill.md orchestration (Phase 16/17 precedent)

**What:** Command `.md` file has YAML frontmatter + prose body. Prose body directs the agent to call MCP tool(s), parse the D-02 envelope (`text_body<SENTINEL>meta_json`), branch on `meta.status`, and render user-facing output under a token budget.

**When to use:** All 4 new P1 commands follow this pattern exactly.

**Example (adapted from Phase 17 `/graphify-ask`, verified at graphify/commands/ask.md):**

```markdown
---
name: graphify-moc
description: Expand a community into an Obsidian MOC note via the vault's profile template.
argument-hint: <community_id>
disable-model-invocation: true
target: obsidian
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `get_community` with:
- `community_id`: parse_int("$ARGUMENTS")

Parse the response. If the community is not found, render verbatim:
> Community $ARGUMENTS not found in graph. Run `/context` to list communities.

Otherwise, load the vault profile via `graphify.profile.load_profile(vault_path)`
and render a MOC note using `profile.obsidian.dataview.moc_query` as the Dataview
block. Populate front-matter per `profile.folder_mapping.moc`.

Then call the graphify MCP tool `propose_vault_note` with:
- `title`: "MOC — {community_label}"
- `body_markdown`: <rendered MOC body>
- `suggested_folder`: profile.folder_mapping.moc
- `note_type`: "moc"
- `tags`: ["community/{community_tag}"]
- `rationale`: "Phase 14 /graphify-moc expansion"

Tell the user the proposal ID and instruct them to run `graphify approve <id>` —
do NOT write to the vault yourself.

Keep the response under 500 tokens.
```

Source for the pattern: [VERIFIED: graphify/commands/ask.md, graphify/commands/argue.md, graphify/commands/connect.md — read during research]

### Pattern 2: D-02 envelope parsing (Phase 9.2 precedent)

**What:** Every MCP tool returns `text_body + QUERY_GRAPH_META_SENTINEL + json.dumps(meta)`. Skill.md splits on the sentinel and branches on `meta.status`.

**Statuses in scope for Phase 14:** `no_graph`, `no_results`, `ok`, `ambiguous_entity`, `entity_not_found`, `no_path` (connect_topics only).

**Source:** [VERIFIED: graphify/serve.py:2880 `_tool_graph_summary`, :2930 `_tool_connect_topics`]

### Pattern 3: Frontmatter runtime parse (D-04)

**What:** `_install_commands` opens each `.md`, reads up to the closing `---`, regex-scans for `target:\s*(obsidian|code|both)`. No YAML library needed.

**Example (stdlib only):**

```python
_TARGET_RE = re.compile(r"^target:\s*(obsidian|code|both)\s*$", re.MULTILINE)

def _read_command_target(src: Path) -> str:
    head = src.read_text(encoding="utf-8", errors="replace")[:1024]
    if not head.startswith("---\n"):
        return "both"  # backward-compat: missing frontmatter = both
    end = head.find("\n---", 4)
    block = head[4:end] if end != -1 else head
    m = _TARGET_RE.search(block)
    return m.group(1) if m else "both"
```

Planner owns final shape. Lines <= 1024 head is enough; existing frontmatter blocks are 5–6 lines. [ASSUMED: 1024 head byte cap is sufficient — verified against all 9 existing commands which end the frontmatter within the first 250 bytes]

### Anti-Patterns to Avoid

- **Re-introducing a command whitelist in `_PLATFORM_CONFIG`:** directly undoes Plan 00 — the whole point is that the file list is inferred from the directory, not enumerated in config.
- **Hard-failing `/graphify-orphan` when `enrichment.json` is absent:** Phase 15 is optional. Emit isolated-only section with a banner.
- **Auto-writing to the vault from a skill.md command:** breaks D-06 trust boundary. All writes MUST go through `propose_vault_note` + `graphify approve`.
- **Missing `target: both` backfill on 9 existing commands:** once Plan 01 filter lands, any command without `target:` defaults to `both` ONLY if the planner codes that default. If the planner implements "missing field = skip," the 9 existing commands silently stop installing. Two reinforcing mitigations: (a) explicit backfill on all 9, (b) default-to-both in parser.
- **Renaming existing commands to `/graphify-*`:** existing 9 commands keep their Phase 11 names for backward compat. Only new commands (Plans 02-05) use the prefix (OBSCMD-07).
- **Adding PyYAML as a required dep:** violates Ideaverse-Integration milestone constraint (CLAUDE.md Project section). Use stdlib regex.
- **Calling Phase 17 `chat` from inside another slash command:** Phase 16 Pitfall 18 (recursion + non-determinism) — Phase 14 commands call only deterministic lower-level tools.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault write path | Direct file write in skill.md | `propose_vault_note` MCP + `graphify approve` | v1.1 trust boundary; merge engine handles sentinel-block preservation, user-modified detection, path confinement. |
| Profile template resolution | Custom template engine | `graphify.profile.load_profile(vault_path)` | Already supports vault-first + built-in fallback, validation, deep-merge. |
| Community membership lookup | Iterate `graph.json` manually | `get_community(community_id)` MCP tool | Handles alias redirect, reload-if-stale, missing-community status. |
| Shortest path between two topics | BFS implementation | `connect_topics(topic_a, topic_b)` MCP tool | Handles ambiguous entity resolution, surprising-bridges secondary section, D-02 envelope. |
| Focus-aware neighborhood | Custom BFS from file_path | `get_focus_context(focus_hint)` MCP tool | Already snapshot-root-validated (Phase 18 CR-01), spoofed-path silent, debounced. |
| Frontmatter parsing | PyYAML dep | stdlib regex on the single `target:` key | Zero new dep; matches existing `test_commands.py` regex patterns. |
| Command-file discovery at uninstall | Hardcoded 7-name tuple | `sorted(src_dir.glob("*.md"))` | Symmetric with install; survives new commands without code change — this IS Plan 00. |
| Install manifest persistence | JSON sidecar of installed files | Directory scan on uninstall | Stateless; no drift/corruption surface. |

**Key insight:** Phase 14 is almost entirely **composition of existing primitives**. The temptation to build new Python logic for "render a MOC" or "format an orphan list" should be resisted — LLM orchestration in skill.md does that shaping, existing MCP tools supply the data, and existing profile + merge engine handle the write. New Python is scoped to installer plumbing only.

## Runtime State Inventory

This is a fresh-feature phase (not a rename/refactor), but the installer *is* modifying a runtime-state-registration mechanism. The 9 existing commands are a real runtime concern.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — commands are stateless; no DB collections or keys affected | None — verified by grep of graphify package for "commands/" references; only touchpoint is `_install_commands` / `_uninstall_commands`. |
| Live service config | 9 existing command `.md` files in `graphify/commands/` (argue, ask, challenge, connect, context, drift, emerge, ghost, trace) lack `target:` frontmatter. Once Plan 01 lands, they must still install. | Code edit: backfill `target: both` in all 9 files (Plan 01). Belt-and-suspenders: parser default-to-both when field absent. |
| OS-registered state | After install, files live under `~/.claude/commands/`, `~/.agents/...`, etc. Plan 00's directory-scan uninstall must clean them up. | Plan 00 glob-at-uninstall handles this. Edge: if user manually deleted `graphify/commands/foo.md` from the package after install, the uninstall glob won't find it and the stale file remains in `dst_dir`. Planner can optionally address via content-hash check. |
| Secrets/env vars | None | None — commands are pure prose, no env injection. |
| Build artifacts/installed packages | `commands/*.md` are packaged via `pyproject.toml` `[tool.setuptools.package-data]` (or similar). New command files must be picked up by install. | Verify `pyproject.toml` includes `commands/*.md` in package data — [ASSUMED: pattern already works for 9 existing files, so new files inherit]. |

**Nothing found in category Stored data / Secrets/env vars:** verified by grep of `graphify/` package source for "commands/" — only referenced by `__main__.py` install/uninstall functions.

## Common Pitfalls

### Pitfall 1: Silent regression of existing 9 commands after Plan 01
**What goes wrong:** Plan 01 adds `target:` filter; existing 9 commands lack the field; installer skips them; `/context`, `/trace`, `/connect`, `/drift`, `/emerge`, `/ghost`, `/challenge`, `/argue`, `/ask` all disappear after next `graphify install`.
**Why it happens:** Adding a new filter without backfilling the data.
**How to avoid:** Two reinforcing mitigations — (a) Plan 01 backfills `target: both` in all 9 files, (b) `_read_command_target` returns `"both"` when the field is absent.
**Warning signs:** Test suite shows `/connect` install regression; `tests/test_commands.py` existing assertions fail.

### Pitfall 2: `enrichment.json` absence crashes `/graphify-orphan`
**What goes wrong:** Phase 15 is async/optional. Freshly-built graph has no `enrichment.json` until `graphify enrich` runs. `/graphify-orphan` tries to read it, gets `FileNotFoundError`, skill.md loop aborts.
**Why it happens:** Forgetting to check file existence before open.
**How to avoid:** Skill.md prose explicitly instructs "if `enrichment.json` is absent, emit ## Isolated Nodes section only with a banner: `_Ghost detection unavailable — run `graphify enrich` to populate staleness._`"
**Warning signs:** User runs `/graphify-orphan` on a fresh project → agent errors instead of rendering isolated-only section.

### Pitfall 3: Auto-write bypasses trust boundary
**What goes wrong:** Skill.md directly writes markdown to the vault instead of staging a proposal. User sees unannounced vault mutations. v1.1 invariant breaks.
**Why it happens:** LLM shortcut — treating `propose_vault_note` as optional ceremony.
**How to avoid:** Every P1 skill.md must explicitly end with "do NOT write to the vault yourself — call `propose_vault_note` and stop." Grep-CI test: each P1 `.md` file contains the literal string `propose_vault_note` and does NOT reference `write_note_directly` / `os.write` / `Path.write_text`.
**Warning signs:** CI test `test_command_references_propose_vault_note` fails.

### Pitfall 4: Install-manifest drift vs directory-scan edge cases
**What goes wrong:** User updates `graphify` package, `commands/foo.md` is removed upstream; user then runs `graphify uninstall`; glob-based uninstall doesn't find `foo.md` in the new source dir, so the stale installed copy in `~/.claude/commands/foo.md` survives.
**Why it happens:** Directory-scan uses the *current* source directory's listing, not the listing-at-install-time.
**How to avoid:** Accept as known limitation, OR (recommended belt-and-suspenders) persist a `~/.claude/graphify-install-manifest.json` at install time listing installed files; uninstall unions manifest + current glob. Planner decides. Whitelist approach is strictly worse than either option — Plan 00 stands.
**Warning signs:** Manual smoke test: install v1.3.x, upgrade to v1.4, uninstall, then `ls ~/.claude/commands/` shows stale files.

### Pitfall 5: `get_focus_context` silent-no-context on spoofed path
**What goes wrong:** User passes `<note-path>` that does not exist inside the graphify project root. `get_focus_context` silently returns `no_context` with no echo (Phase 18 SC2 invariant). Skill.md renders empty result with no explanation.
**Why it happens:** Phase 18 intentionally does not echo the spoofed path (security invariant — prevents filesystem leak).
**How to avoid:** Skill.md handles `status == no_context` by rendering: "The note path doesn't match any file in the graph. Check that the note's `source_file` frontmatter field points to a file inside the project root."
**Warning signs:** User reports "`/graphify-related` silently prints nothing."

### Pitfall 6: Community assignment semantics mismatch
**What goes wrong:** `/graphify-orphan` needs to find "nodes with no community." But `graph.json` node `community` attribute may be `None`, `-1`, or missing entirely depending on pipeline version.
**Why it happens:** Community attribution is post-clustering; isolated nodes or filtered-out stubs may use any of the three encodings.
**How to avoid:** Skill.md prose defines "isolated" as `community attribute is None, -1, or absent`. Verify against current `cluster.py` output during Plan 04 implementation.
**Warning signs:** `/graphify-orphan` returns empty isolated-section even when isolated nodes visibly exist in the graph. [ASSUMED: current `cluster.py` uses `-1` for isolated — planner must verify at implementation time.]

## Code Examples

### Directory-scan uninstall (Plan 00)

```python
# graphify/__main__.py — Plan 00 refactor target
def _uninstall_commands(cfg: dict, *, verbose: bool = True) -> None:
    """Remove command files previously installed by _install_commands.

    Directory-scan: enumerate graphify/commands/*.md at runtime and remove
    the matching basenames under cfg['commands_dst']. Symmetric with install.
    """
    if not cfg.get("commands_enabled"):
        return
    dst_rel = cfg.get("commands_dst")
    if dst_rel is None:
        return
    dst_dir = Path.home() / dst_rel
    if not dst_dir.exists():
        return
    src_dir = Path(__file__).parent / cfg.get("commands_src_dir", "commands")
    for src in sorted(src_dir.glob("*.md")):
        target = dst_dir / src.name
        if target.exists():
            target.unlink()
            if verbose:
                print(f"  command removed    ->  {target}")
```

Source: adapted from current `_install_commands` glob pattern at `graphify/__main__.py:150`. [VERIFIED]

### Frontmatter filter (Plan 01)

```python
# graphify/__main__.py — Plan 01 edits to _install_commands
import re
_TARGET_RE = re.compile(r"^target:\s*(obsidian|code|both)\s*$", re.MULTILINE)

def _read_command_target(src: Path) -> str:
    """Parse `target:` from command frontmatter. Returns 'both' if absent."""
    try:
        head = src.read_text(encoding="utf-8", errors="replace")[:1024]
    except OSError:
        return "both"
    m = _TARGET_RE.search(head)
    return m.group(1) if m else "both"

def _install_commands(cfg: dict, src_dir: Path, *, verbose: bool = True) -> None:
    if not cfg.get("commands_enabled"):
        return
    dst_rel = cfg.get("commands_dst")
    if dst_rel is None:
        return
    supports = set(cfg.get("supports", ["code", "obsidian"]))  # default: install all
    dst_dir = Path.home() / dst_rel
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_dir.glob("*.md")):
        target = _read_command_target(src)
        if target != "both" and target not in supports:
            continue
        dst = dst_dir / src.name
        shutil.copy(src, dst)
        if verbose:
            print(f"  command installed  ->  {dst}")
```

Also: add `"supports": ["code", "obsidian"]` (or just `["obsidian"]`) to every entry in `_PLATFORM_CONFIG`. [VERIFIED: pattern against current `__main__.py:49`]

### `/graphify-related` skill.md (Plan 03)

```markdown
---
name: graphify-related
description: Show graph-connected notes for a given vault note's source file.
argument-hint: <note-path>
disable-model-invocation: true
target: obsidian
---

Arguments: $ARGUMENTS

Step 1 — Read the note at "$ARGUMENTS". Parse its YAML frontmatter and extract
the `source_file` field. If the note lacks `source_file`, render:
> The note at $ARGUMENTS has no `source_file` frontmatter — cannot resolve graph focus.

Step 2 — Call the graphify MCP tool `get_focus_context` with:
- `focus_hint`: {"file_path": <source_file>, "neighborhood_depth": 2, "include_community": true}
- `budget`: 2000

The response is a D-02 envelope. Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found. Run `/graphify` to build one, then retry.

**If `status` is `no_context`:** render:
> The note's `source_file` ($source_file) doesn't match any file in the graph.
> Check that the path is inside the project root.

**If `status` is `ok`:** render the text body as a "Related notes" section,
listing `meta.nodes` grouped by community. Do NOT propose a vault write for
this command — it is a read-only navigation aid.

Keep the response under 500 tokens.
```

Template source: [VERIFIED: Phase 17 graphify/commands/ask.md]

### Graceful enrichment.json absence (Plan 04)

```markdown
# In graphify-orphan.md, after fetching isolated nodes:

Check for file: graphify-out/enrichment.json

**If present:** parse `passes.staleness`, filter entries where value == "GHOST",
emit `## Stale/Ghost Nodes` section with node_id → label mapping.

**If absent:** emit `## Stale/Ghost Nodes` with:
> _Ghost detection unavailable — run `graphify enrich` to populate staleness data._
```

Source: [VERIFIED: enrich.py:506 `valid_labels = {"FRESH", "STALE", "GHOST"}`; enrichment.json path convention from Phase 15]

### Test pattern for new commands (extend `tests/test_commands.py`)

```python
# Lift existing pattern from tests/test_commands.py
P1_OBSIDIAN_COMMANDS = {
    "graphify-moc":     "get_community",
    "graphify-related": "get_focus_context",
    "graphify-orphan":  None,  # reads sidecars directly
    "graphify-wayfind": "connect_topics",
}

def test_obsidian_commands_exist():
    for name in P1_OBSIDIAN_COMMANDS:
        assert (_commands_dir() / f"{name}.md").exists()

def test_obsidian_commands_have_target_frontmatter():
    for name in P1_OBSIDIAN_COMMANDS:
        text = _read(name)
        assert re.search(r"^target:\s*(obsidian|both)\s*$", text, re.M), \
            f"{name}.md missing target: obsidian|both"

def test_obsidian_write_commands_reference_propose_vault_note():
    # /graphify-moc writes; others are read-only
    assert "propose_vault_note" in _read("graphify-moc")

def test_existing_commands_backfilled_target_both():
    for name in ("context", "trace", "connect", "drift", "emerge",
                 "ghost", "challenge", "argue", "ask"):
        text = _read(name)
        assert "target: both" in text, f"{name}.md missing target: both backfill"
```

Source: [VERIFIED: adapted from tests/test_commands.py existing shape]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_uninstall_commands` hardcodes 7 filenames | Directory-scan over `commands/*.md` | Phase 14 Plan 00 | New commands auto-picked up on uninstall without code change. |
| Install copies every `.md` regardless of platform | `target: obsidian|code|both` frontmatter filter + `_PLATFORM_CONFIG.supports` | Phase 14 Plan 01 | Code-only platforms (codex, aider, opencode, copilot) skip vault commands. |
| LLM orchestration lives in Python | LLM orchestration lives in `skill.md` prose | Phase 16 D-73 (locked) | Python substrate stays deterministic and testable; skill.md owns branching. |
| Vault writes from tool code | Writes always staged via `propose_vault_note` + `graphify approve` | v1.1 trust boundary | User retains consent; merge engine handles sentinel blocks + user-modified detection. |

**Deprecated/outdated:**
- Hardcoded command-name whitelist in `_uninstall_commands` — removed by Plan 00.
- Platform-level command whitelist proposals — explicitly rejected by D-04 (would re-introduce the anti-pattern Plan 00 eliminates).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.10 + 3.12 CI matrix) |
| Config file | pyproject.toml (no separate pytest.ini) |
| Quick run command | `pytest tests/test_commands.py tests/test_install.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBSCMD-01 | `_uninstall_commands` removes all files in `commands/*.md` glob, not just hardcoded 7 | unit | `pytest tests/test_install.py::test_uninstall_removes_all_globbed_commands -x` | ❌ Wave 0 new test |
| OBSCMD-01 | `_uninstall_commands` symmetric with install (no files remain in dst_dir after) | unit | `pytest tests/test_install.py::test_install_uninstall_round_trip -x` | ❌ Wave 0 new test |
| OBSCMD-02 | Frontmatter `target: code` file skipped when `supports == ["obsidian"]` | unit | `pytest tests/test_install.py::test_install_filters_by_target -x` | ❌ Wave 0 new test |
| OBSCMD-02 | `--no-obsidian-commands` flag suppresses `target: obsidian` files | unit | `pytest tests/test_install.py::test_no_obsidian_commands_flag -x` | ❌ Wave 0 new test |
| OBSCMD-02 | Command without `target:` frontmatter installs (backward compat → "both") | unit | `pytest tests/test_install.py::test_missing_target_defaults_to_both -x` | ❌ Wave 0 new test |
| OBSCMD-02 | All 9 existing commands have `target: both` backfilled | unit | `pytest tests/test_commands.py::test_existing_commands_backfilled_target_both -x` | ❌ Wave 0 new test |
| OBSCMD-03 | `/graphify-moc.md` exists with valid frontmatter (name, description, argument-hint, disable-model-invocation, target) | unit | `pytest tests/test_commands.py::test_obsidian_commands_have_target_frontmatter -x` | ❌ Wave 0 new test |
| OBSCMD-03 | `graphify-moc.md` references `get_community` MCP tool | unit | `pytest tests/test_commands.py::test_obsidian_commands_reference_correct_tool -x` | ❌ Wave 0 new test |
| OBSCMD-04 | `graphify-related.md` references `get_focus_context` + `source_file` frontmatter | unit | `pytest tests/test_commands.py::test_graphify_related_references_focus_tool -x` | ❌ Wave 0 new test |
| OBSCMD-05 | `graphify-orphan.md` has two distinct section headers (`## Isolated Nodes`, `## Stale/Ghost Nodes`) | unit | `pytest tests/test_commands.py::test_graphify_orphan_has_dual_sections -x` | ❌ Wave 0 new test |
| OBSCMD-05 | `graphify-orphan.md` handles absent `enrichment.json` (contains banner phrase) | unit | `pytest tests/test_commands.py::test_graphify_orphan_graceful_absence -x` | ❌ Wave 0 new test |
| OBSCMD-06 | `graphify-wayfind.md` references `connect_topics` MCP tool | unit | `pytest tests/test_commands.py::test_graphify_wayfind_references_connect -x` | ❌ Wave 0 new test |
| OBSCMD-07 | All new P1 command filenames start with `graphify-` | unit | `pytest tests/test_commands.py::test_new_commands_use_graphify_prefix -x` | ❌ Wave 0 new test |
| OBSCMD-08 | Write-path commands reference `propose_vault_note`; no direct-write helpers | unit | `pytest tests/test_commands.py::test_write_commands_use_propose_vault_note -x` | ❌ Wave 0 new test |
| OBSCMD-08 | No new command references `Path.write_text` / `os.write` / direct vault write | unit | `pytest tests/test_commands.py::test_no_direct_vault_writes -x` | ❌ Wave 0 new test |
| (regression) | Existing 9 commands still install on `claude` + `windows` platforms | unit | `pytest tests/test_install.py::test_existing_commands_still_install -x` | ❌ Wave 0 new test |

### Sampling Rate
- **Per task commit:** `pytest tests/test_commands.py tests/test_install.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_commands.py` — extend with `P1_OBSIDIAN_COMMANDS` dict + 8 new test functions above (existing file — add to it, do not create new)
- [ ] `tests/test_install.py` — extend with frontmatter-filter unit tests + round-trip install/uninstall test + `--no-obsidian-commands` flag test
- [ ] Framework install: N/A — pytest already configured and green (1347-test suite per MEMORY)

*(Existing test infrastructure covers most structure; Phase 14 gaps are additive tests within existing files, not new framework setup.)*

## Security Domain

`security_enforcement` is not explicitly set to `false` in `.planning/config.json` — applicable.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Slash commands run in user's Obsidian/IDE session — no auth surface added. |
| V3 Session Management | no | MCP session handling already exists; no new sessions introduced. |
| V4 Access Control | yes | Vault-write confinement: `propose_vault_note` stages to `graphify-out/proposals/` (path-resolved, confined). `_approve_and_write_proposal` runs `_validate_vault_path_for_approve` (T-07-11) before any write. Both are pre-existing invariants preserved by Phase 14. |
| V5 Input Validation | yes | Frontmatter parse uses stdlib regex on first 1024 bytes — no YAML code execution path. Note frontmatter `source_file` consumed by `/graphify-related` passes through `get_focus_context`'s `validate_graph_path(..., base=project_root)` (Phase 18 CR-01 fix) — spoofed paths silently no-op. [VERIFIED: 18-VERIFICATION.md SC2] |
| V6 Cryptography | no | No crypto added. |

### Known Threat Patterns for Phase 14

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Spoofed `file_path` in note frontmatter directs `/graphify-related` to `/etc/passwd` | Information Disclosure | Phase 18 `validate_graph_path(candidate, base=project_root)` silently returns `no_context` — no filesystem leak, no echo. [VERIFIED: serve.py:1785, 18-VERIFICATION.md SC2] |
| Command prose injection — a malicious `.md` file in `graphify/commands/` tries to execute shell on install | Elevation of Privilege | Installer `shutil.copy` only — never interprets command content. File-level threat requires package-level trust, which is the pip install boundary. |
| Vault path traversal via `suggested_folder` | Tampering | `_validate_vault_path_for_approve` enforces vault-root confinement (T-07-11 invariant, pre-existing). [VERIFIED: __main__.py:884-886] |
| Unwanted vault write | Tampering | D-06 trust boundary: `propose_vault_note` stages JSON only; `graphify approve` requires explicit user invocation. [VERIFIED: mcp_tool_registry.py:161 description] |
| Command filename collision (user-authored `/related` overriding graphify) | Tampering / Confusion | `/graphify-*` prefix (OBSCMD-07) — all new commands namespaced. Existing 9 keep their names (backward compat accepted). |
| Prompt injection via enrichment.json GHOST entries influencing vault writes | Tampering | `/graphify-orphan` does not propose vault writes in D-05 — it only renders a navigation list. No write pathway = no injection surface. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 1024-byte head is sufficient for `_read_command_target` to find frontmatter on all future command files | Pattern 3 | LOW — current max frontmatter block is ~300 bytes. If a future command's frontmatter exceeds 1024 bytes, regex misses and default "both" applies (safe fallback). |
| A2 | `pyproject.toml` package-data already includes `commands/*.md` glob | Build artifacts | LOW — 9 existing files install successfully, so pattern works. New files in the same directory inherit. Verify at implementation time. |
| A3 | `cluster.py` uses `-1` or `None` or missing attribute to mark isolated nodes | Pitfall 6 | MEDIUM — `/graphify-orphan` skill.md must verify exact encoding at implementation time; if encoding differs (e.g., all nodes get a community_id and isolation is encoded elsewhere), skill prose needs updating. Planner should add a one-line verification task in Plan 04. |
| A4 | MOC-root heuristic "largest community, tie-break lowest community_id" is acceptable for `/graphify-wayfind` | Claude's Discretion | LOW — D-03/D-05 in CONTEXT explicitly leaves this to planner discretion. |

## Open Questions (RESOLVED)

1. **Plan 04: community=null vs community=-1 encoding**
   - What we know: `cluster.py` runs Leiden (graspologic) with Louvain fallback; comments at `graphify/mapping.py:299` mention "sentinel community id -1".
   - What's unclear: Whether every node always gets a community assignment (even isolated) or if some nodes lack the attribute entirely.
   - RESOLVED: Plan 04 first task is a 5-minute code scan of `cluster.py` output to confirm exact encoding, then lock skill.md prose accordingly.

2. **Plan 00: install manifest vs pure directory-scan for uninstall**
   - What we know: D-04 Claude's-discretion note recommends directory-scan with optional content-hash belt-and-suspenders.
   - What's unclear: Whether the upgrade-path edge case (user upgrades package, then uninstalls) is worth the manifest-persistence complexity.
   - RESOLVED: Ship directory-scan in Plan 00; document the upgrade edge as a known limitation. If support volume shows it matters, add manifest in v1.4.x.

3. **Plan 02: MOC render — skill-md-only vs small Python helper**
   - What we know: D-03 says "thin caller" to `load_profile`. Phase 16/17 pattern is skill.md does all composition.
   - What's unclear: Whether Dataview query template substitution (`${community_tag}` replacement) is reliably done by the LLM or should be a 10-line Python helper for determinism.
   - RESOLVED: Start with pure skill.md; if blind-label tests of the output show inconsistency, add helper in a follow-up wave.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib `pathlib` + `re` + `shutil` | Plans 00 + 01 installer edits | ✓ | 3.10+ | — |
| pytest | Test suite | ✓ | existing CI | — |
| `graphify.profile.load_profile` | Plan 02 | ✓ | in-repo | `_DEFAULT_PROFILE` fallback (built-in) |
| `get_community`, `get_focus_context`, `connect_topics`, `get_agent_edges`, `propose_vault_note` MCP tools | Plans 02-05 | ✓ | all registered in `mcp_tool_registry.py` + handlers in `serve.py` | — |
| `enrichment.json` (Phase 15 output) | Plan 04 ghost section | optional | Phase 15 complete | If absent, render isolated-only section with banner — skill.md handles gracefully |
| PyYAML | NOT USED | optional dep only | — | stdlib regex parse instead |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `enrichment.json` is optional at runtime — `/graphify-orphan` degrades to isolated-only.

## Project Constraints (from CLAUDE.md)

Extracted from project `CLAUDE.md` (Ideaverse-Integration milestone constraints + general project rules) — planner MUST honor:

- **Python 3.10+** on CI targets (3.10 and 3.12).
- **No new required dependencies.** Plan 01 frontmatter parsing uses stdlib, NOT PyYAML-as-required-dep. PyYAML stays optional under `[mcp]`/`[obsidian]`/`[routing]` extras.
- **Backward compatible.** Running `graphify --obsidian` without a profile must still produce Ideaverse-compatible output. Existing 9 slash commands must keep working after Plan 01 lands (hence the `target: both` backfill).
- **Existing test patterns.** Pure unit tests, no network calls, no filesystem side effects outside `tmp_path`. Plan 14 test additions extend `tests/test_commands.py` and `tests/test_install.py` — both already pattern-compliant.
- **Security:** All file paths confined to output directory per `security.py` patterns. `propose_vault_note` + `_validate_vault_path_for_approve` already enforce this; Phase 14 does not introduce new write paths outside this envelope.
- **Template placeholders must be sanitized.** Profile MOC template uses `${community_tag}` — `safe_tag()` and `safe_frontmatter_value()` in `profile.py:342,381` already handle sanitization; Plan 02 consumes them.
- **Use Write tool for file creation** (per agent rules), not heredoc.
- **No linter/formatter.** PEP-8 spirit; 4-space indent; `from __future__ import annotations` on new modules (though Phase 14 adds no new Python modules).
- **GSD Workflow Enforcement.** All file-changing work routed through a GSD command. This research file is the /gsd-research-phase artifact.

## Sources

### Primary (HIGH confidence)

- `graphify/__main__.py:49-138` — `_PLATFORM_CONFIG` dict (11 platforms: claude, codex, opencode, aider, copilot, claw, droid, trae, trae-cn, antigravity, windows)
- `graphify/__main__.py:141-155` — `_install_commands` existing glob-based implementation
- `graphify/__main__.py:157-172` — `_uninstall_commands` current whitelist (Plan 00 target)
- `graphify/__main__.py:869-873` — `_load_profile_for_approve` indirection
- `graphify/__main__.py:898-985` — `_approve_and_write_proposal` merge-engine flow
- `graphify/profile.py:36-65` — `_DEFAULT_PROFILE` built-in profile structure
- `graphify/profile.py:128-157` — `load_profile` vault-first + fallback logic
- `graphify/serve.py:2747-2757` — `_tool_get_community` handler
- `graphify/serve.py:2843-2847` — `_tool_propose_vault_note` handler
- `graphify/serve.py:2858-2864` — `_tool_get_agent_edges` handler
- `graphify/serve.py:2918-2931` — `_tool_connect_topics` handler
- `graphify/serve.py:2948+` — `_tool_get_focus_context` handler
- `graphify/mcp_tool_registry.py:161-176` — `propose_vault_note` tool schema
- `graphify/mcp_tool_registry.py:290-323` — `get_focus_context` tool schema
- `graphify/commands/ask.md` — Phase 17 orchestration precedent (D-02 reuses)
- `graphify/commands/argue.md` — Phase 16 orchestration precedent (Plans 02-05 reuse)
- `graphify/commands/connect.md` — dual-section rendering precedent (`/graphify-orphan` reuses)
- `tests/test_commands.py` — existing frontmatter + MCP-tool-reference test patterns
- `tests/test_install.py` — existing per-platform install assertions
- `.planning/phases/18-focus-aware-graph-context/18-VERIFICATION.md` — `get_focus_context` SC1/SC2 contract
- `.planning/phases/15-async-background-enrichment/15-VERIFICATION.md` — `enrichment.json` + staleness GHOST schema (`enrich.py:506` `valid_labels`)
- `.planning/phases/14-obsidian-thinking-commands/14-CONTEXT.md` — D-01..D-06 locked decisions
- `.planning/REQUIREMENTS.md:56-67` — OBSCMD-01..12 text
- `.planning/ROADMAP.md:178-189` — Phase 14 scope + success criteria + cross-phase Plan 00 rule
- `CLAUDE.md` §Project — Ideaverse Integration constraints
- `pyproject.toml:13,43-54` — dependency tiers; PyYAML is optional

### Secondary (MEDIUM confidence)

- Cross-referenced `.planning/config.json` to confirm `workflow.nyquist_validation: true` — Validation Architecture section required and included.
- Inferred Pitfall 6 community-encoding ambiguity from `graphify/mapping.py:299` comment — flagged as assumption A3.

### Tertiary (LOW confidence)

- None. All claims in this research either cite source files I read in this session or reuse verified invariants from upstream phase VERIFICATION files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified via direct source-file reads in this session.
- Architecture: HIGH — existing patterns (Phase 16/17 skill.md, D-02 envelope, propose+approve trust boundary) are in-repo and verifiable.
- Pitfalls: MEDIUM-HIGH — Pitfalls 1-5 are code-verified invariants; Pitfall 6 (community encoding) is flagged as assumption A3 for Plan 04 verification.
- Validation Architecture: HIGH — test patterns directly lifted from `tests/test_commands.py` + `tests/test_install.py` existing shape.
- Security: HIGH — reuses verified Phase 18 CR-01 spoof-path fix + v1.1 trust boundary (no new attack surface).

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (stable — domain is installer refactor + composition of frozen MCP tools; no fast-moving external deps)
