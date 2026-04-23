# Phase 14: Obsidian Thinking Commands - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 ships vault-scoped slash commands that let Obsidian users navigate and expand their graphify-enriched notes from inside the vault, with every vault write routed through the v1.1 `propose_vault_note + approve` trust boundary.

**In scope (P1 only, per D-01):**
- Plan 00 — refactor `_uninstall_commands()` (`graphify/__main__.py:157`) from hardcoded 7-name whitelist to directory-scan over `graphify/commands/*.md` (OBSCMD-01)
- Plan 01 — `target: obsidian | code | both` frontmatter filter in `_install_commands`, plus `--no-obsidian-commands` install flag (OBSCMD-02, OBSCMD-07)
- Plan 02 — `/graphify-moc <community_id>` command, profile-driven template (OBSCMD-03)
- Plan 03 — `/graphify-related <note-path>` command, consumes `get_focus_context` (OBSCMD-04)
- Plan 04 — `/graphify-orphan` command, dual-section output (OBSCMD-05)
- Plan 05 — `/graphify-wayfind` command, `connect_topics` shortest-path (OBSCMD-06)
- OBSCMD-08 is a cross-cutting invariant enforced by every write path (not a plan on its own)

**Out of scope (deferred to v1.4.x, per D-01):**
- OBSCMD-09 `/graphify-bridge`
- OBSCMD-10 `/graphify-voice` (anti-impersonation guard needs separate design)
- OBSCMD-11 `/graphify-drift-notes`
- OBSCMD-12 `trigger_pipeline: true` frontmatter + cost-preview banner

</domain>

<decisions>
## Implementation Decisions

### Scope

- **D-01:** Defer **all P2** (OBSCMD-09..12) to v1.4.x. Phase 14 ships **5 plans** (00 refactor, 01 filter, 02 moc, 03 related, 04 orphan, 05 wayfind — i.e. 6 plans including refactor + filter). P2 roll-up prevents voice anti-impersonation design risk bleeding into milestone close.

### Command contracts

- **D-02:** `/graphify-related` requires an explicit `<note-path>` `$ARGUMENT` — no active-note auto-detect. Skill.md reads the note's YAML frontmatter `source_file`, then calls `get_focus_context(focus_hint={"file_path": source_file})`. Matches `/graphify-ask` pattern from Phase 17 — explicit, testable, platform-agnostic.
  - **Why:** Reliable "active note" signal doesn't exist across all Obsidian-integrated AI coding platforms; explicit arg is the one unambiguous contract.
  - **Downstream:** researcher should verify the `source_file` frontmatter convention used by `propose_vault_note` in `graphify/profile.py`.

- **D-03:** `/graphify-moc` uses **vault profile first, built-in fallback**. Calls existing `graphify.profile.load_profile(vault_path)` which already returns `.graphify/profile.yaml` + templates when present, else the built-in Ideaverse-compatible `_DEFAULT_PROFILE`.
  - **Why:** Aligns with the "Ideaverse Integration — Configurable Vault Adapter" milestone (CLAUDE.md Project section) and its backward-compat constraint: "Running `graphify --obsidian` without a profile in the target vault must produce output similar to current behavior."
  - **Code insight:** Loader already exists — no new plumbing needed (`graphify/profile.py`, called from `__main__.py:869`, `export.py:532`).

- **D-05:** `/graphify-orphan` emits **two labeled sections**:
  - `## Isolated Nodes` — nodes with `community=null` (sourced from community metadata in `graph.json`)
  - `## Stale/Ghost Nodes` — nodes with `staleness=GHOST` in `enrichment.json` (Phase 15 overlay)
  - **Why:** Two distinct semantic categories → two distinct user remediations (cluster vs revisit). Collapsing into one list loses the signal.
  - **Downstream:** planner must make the command graceful when `enrichment.json` is absent (Phase 15 is optional/async) — show isolated-only with a note.

### Installation / platform filtering

- **D-04:** Frontmatter filter lives at **runtime parse time** in `_install_commands`. Each `graphify/commands/*.md` carries `target: obsidian | code | both` in its frontmatter; each entry in `_PLATFORM_CONFIG` gains a `supports: ["obsidian", "code"]`-style list; installer copies a file iff `target in supports or target == "both"`.
  - **Why:** Single source of truth is the command file itself. Adding a platform-config whitelist would re-introduce the exact anti-pattern Plan 00 is eliminating.
  - **Existing commands:** The 9 files already in `graphify/commands/` (`argue.md`, `ask.md`, `challenge.md`, `connect.md`, `context.md`, `drift.md`, `emerge.md`, `ghost.md`, `trace.md`) currently lack a `target:` field — Plan 01 must backfill `target: both` on all of them to stay backward-compatible.

### Trust boundary (invariant — not a plan)

- **D-06:** Every command that writes to the vault emits a `propose_vault_note` call followed by `graphify approve` as the user action — **never** auto-writes. This is the v1.1 sentinel-block contract and must survive into every Phase 14 command unchanged.
  - Enforcement: test that each P1 command's skill.md references `propose_vault_note` and never calls a direct write helper.

### Claude's Discretion

- **Plan 00 refactor shape:** The whitelist → directory-scan migration can either (a) glob `graphify/commands/*.md` at uninstall time and remove matching names in `dst_dir`, or (b) persist an install manifest. Planner picks the simpler option that still handles the "user deleted a command file after install" edge. Recommendation: (a), with a belt-and-suspenders check that only removes files whose content hash matches what was installed — but planner owns this.
- **Wayfind MOC-root heuristic:** How `/graphify-wayfind` picks the MOC root (largest-community MOC? user-designated home note?). Planner decides; acceptable default is "largest community's MOC, tie-break by lowest community_id."

### Folded Todos

_None — cross-reference produced no phase-relevant todos at this time._

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` §"Phase 14: Obsidian Thinking Commands" — goal, REQ-IDs, cross-phase rule (Plan 00 prerequisite), success criteria
- `.planning/REQUIREMENTS.md` OBSCMD-01..OBSCMD-12 — full requirement text
- `.planning/PROJECT.md` — milestone v1.4 vision; "Ideaverse Integration — Configurable Vault Adapter" cross-cut
- `CLAUDE.md` §"Project" — Ideaverse Integration milestone constraints (Python 3.10+, no new required deps, backward compat, template-string-not-Jinja2, security.py confinement)

### Upstream phase contracts (HARD-dep)
- `.planning/phases/18-focus-aware-graph-context/18-VERIFICATION.md` — `get_focus_context(focus_hint)` contract; CR-01 snapshot-root fix codified
- `.planning/phases/18-focus-aware-graph-context/18-CONTEXT.md` — focus-hint schema decisions
- `.planning/phases/17-conversational-graph-chat/17-CONTEXT.md` — `/graphify-ask` skill.md orchestration precedent (D-02 reuses this pattern)
- `.planning/phases/16-graph-argumentation-mode/16-CONTEXT.md` — `/graphify-argue` SPAR-Kit skill.md pattern (Plan 02..05 reuse)
- `.planning/phases/15-async-background-enrichment/15-VERIFICATION.md` — `enrichment.json` overlay schema; `staleness=GHOST` field (D-05 consumer)

### Code entry points (referenced in decisions)
- `graphify/__main__.py:140-172` — `_install_commands`, `_uninstall_commands` (D-04 site; Plan 00 target)
- `graphify/profile.py` `load_profile(vault_path)` — vault profile + built-in fallback (D-03 backbone)
- `graphify/commands/*.md` — 9 existing commands that need `target: both` backfill (D-04 consequence)
- `graphify/__init__.py:23` — `load_profile` lazy import registration

### Trust-boundary precedent
- `graphify/__main__.py:~919` — `_load_profile_for_approve` + existing `propose_vault_note` / `approve` flow (D-06 invariant source)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`graphify.profile.load_profile`** — already implements vault-profile-first + built-in fallback. `/graphify-moc` (Plan 02) is a thin caller; no new loader work needed.
- **`get_focus_context` MCP tool (Phase 18)** — consumed directly by `/graphify-related` (Plan 03) and `/graphify-wayfind` (Plan 05).
- **`get_community` MCP tool** — consumed by `/graphify-moc` (Plan 02) per OBSCMD-03.
- **`connect_topics` shortest-path** — consumed by `/graphify-wayfind` (Plan 05) per OBSCMD-06.
- **`get_agent_edges` + community metadata** — consumed by `/graphify-orphan` (Plan 04) per OBSCMD-05.
- **`enrichment.json` (Phase 15)** — source of `staleness=GHOST` for `/graphify-orphan` second section. Must degrade gracefully when absent.
- **`propose_vault_note` + `graphify approve`** — existing v1.1 trust boundary; every write command wraps this (D-06).
- **9 existing commands in `graphify/commands/`** — template for new command file shape; currently lack `target:` frontmatter (Plan 01 backfills `target: both`).
- **`_PLATFORM_CONFIG` dict in `__main__.py`** — extend each entry with `supports: [...]` for D-04 runtime filter.

### Established Patterns
- **Skill.md orchestration (Phases 16, 17):** Python substrate stays thin; the `skill.md` file drives the LLM. Phase 14 commands follow this — minimal/no new Python in `graphify/` for Plans 02-05; most logic is `*.md` orchestration calling existing MCP tools.
- **Directory-scan over whitelist:** Plan 00 aligns installer with `_install_commands`' existing `sorted(src_dir.glob("*.md"))` pattern (`__main__.py:150`) — `_uninstall_commands` becomes symmetric.
- **Frontmatter-first config:** Command `.md` files are the single source of truth (D-04), not a parallel config structure.

### Integration Points
- **`_PLATFORM_CONFIG`** (`__main__.py`) — 8 platforms; gain `supports` key for D-04 filter.
- **`install()` / `uninstall()` CLI handlers** (`__main__.py:~175, ~228`) — already thread `no_commands` flag; add `--no-obsidian-commands` alongside.
- **Skill.md registration** — each new command may warrant a short mention in the platform skill files (claude, codex, opencode variants); planner decides whether registration is per-platform or global.

</code_context>

<specifics>
## Specific Ideas

- **Milestone cross-cut:** Phase 14 is the user-visible half of the "Ideaverse Integration — Configurable Vault Adapter" milestone. `/graphify-moc` in particular exercises the adapter end-to-end (profile load → template render → `propose_vault_note` → `approve`). Planner should treat this as the headline validation path.
- **Phase 17 pattern reference:** `/graphify-ask` (skill.md orchestration, explicit arg, calls MCP tool) is the closest analog for `/graphify-related`. Researcher should lift the Q&A-shape template and adapt.
- **Phase 16 pattern reference:** `/graphify-argue` (skill.md orchestrating an LLM loop with cited outputs) is the closest analog for `/graphify-moc` rendering — adapt the SPAR-Kit skill.md structure but target MOC template output.

</specifics>

<deferred>
## Deferred Ideas

- **`/graphify-bridge` (OBSCMD-09)** — v1.4.x. Reuses surprising-connections analysis from `analyze.py`. Cheap to ship later; deferred purely to close v1.4.
- **`/graphify-voice` (OBSCMD-10)** — v1.4.x or later. Requires anti-impersonation guard design (labeled output, never attributed to user). Own mini-phase when revisited.
- **`/graphify-drift-notes` (OBSCMD-11)** — v1.4.x. Pure Dataview-embed rendering of existing `/drift` output.
- **`trigger_pipeline` frontmatter + cost-preview banner (OBSCMD-12)** — v1.4.x. Pitfall 15 mitigation; revisit alongside bridge/voice/drift-notes since those may be the first pipeline-trigger candidates.
- **MOC-root heuristic for `/graphify-wayfind`** — planner chooses within Phase 14; no productization of "user-designated home note" yet (could become its own config in a future milestone).

### Reviewed Todos (not folded)
_None reviewed at this stage — run `/gsd-check-todos` if project-level todos accumulated since last phase._

</deferred>

---

*Phase: 14-obsidian-thinking-commands*
*Context gathered: 2026-04-22*
