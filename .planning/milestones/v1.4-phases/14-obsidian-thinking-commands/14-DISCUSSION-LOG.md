# Phase 14: Obsidian Thinking Commands - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 14-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 14-obsidian-thinking-commands
**Areas discussed:** P2 scope, Active-note inference, MOC template source, Filter location + orphan shape

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| P2 scope | Ship bridge/voice/drift-notes + trigger_pipeline flag in Phase 14, or defer to v1.4.x | ✓ |
| Active-note inference | How /graphify-related knows 'current note' | ✓ |
| MOC template source | Vault profile vs built-in template | ✓ |
| Filter + orphan shape | Frontmatter filter location + orphan output shape | ✓ |

**User's choice:** All four areas (multi-select).

---

## P2 Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Defer all P2 (Recommended) | 4 P1 commands + Plan 00 refactor + Plan 01 filter. 5 plans. P2 rolls to v1.4.x. | ✓ |
| Bridge only | +1 plan — /graphify-bridge via analyze.py surprising-connections | |
| Bridge + drift-notes | +2 plans — both pure rendering | |
| All P2 | +3 plans + trigger_pipeline flag; voice needs anti-impersonation guard (scope risk) | |

**User's choice:** Defer all P2.
**Notes:** First pass was multi-select and user selected all options; clarified as mutually-exclusive single-select and user picked the recommended (defer-all). Drives D-01.

---

## Active-Note Inference (/graphify-related)

| Option | Description | Selected |
|--------|-------------|----------|
| $ARGUMENT path required (Recommended) | Explicit `<note-path>` arg; skill.md reads frontmatter source_file → get_focus_context | ✓ |
| Frontmatter source_file auto-detect | Infer via vault 'active note' signal; fragile across platforms | |
| Two modes: arg OR prompt | Arg if given, else interactive prompt; doubles test surface | |

**User's choice:** $ARGUMENT path required.
**Notes:** Matches /graphify-ask pattern from Phase 17 — explicit, testable, platform-agnostic. Drives D-02.

---

## MOC Template Source (/graphify-moc)

| Option | Description | Selected |
|--------|-------------|----------|
| Vault profile first, built-in fallback (Recommended) | `.graphify/profile.yaml` if present, else built-in Ideaverse default. Aligns milestone constraint. | ✓ |
| Built-in default only (Phase 14) | Hardcoded template; defer adapter wiring | |
| Profile required, no fallback | Refuse to run without profile; breaks first-run UX | |

**User's choice:** Vault profile first, built-in fallback.
**Notes:** Code scout confirmed `graphify.profile.load_profile` already exists with fallback behavior — de-risks Plan 02. Drives D-03.

---

## Filter Location (Installer)

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime parse (Recommended) | _install_commands reads frontmatter per file; _PLATFORM_CONFIG gets `supports:` list | ✓ |
| Platform config whitelist | Add command list per platform in _PLATFORM_CONFIG; re-introduces Plan-00 anti-pattern | |
| Both (defense-in-depth) | Frontmatter is truth, config override; overkill for 4 commands | |

**User's choice:** Runtime parse.
**Notes:** Single source of truth is the command file itself; consistent with Plan 00 directory-scan philosophy. 9 existing commands need `target: both` backfill. Drives D-04.

---

## Orphan Output Shape (/graphify-orphan)

| Option | Description | Selected |
|--------|-------------|----------|
| Two labeled sections (Recommended) | `## Isolated Nodes` + `## Stale/Ghost Nodes` — distinct semantics, distinct remediations | ✓ |
| Unified list with tag column | Single table, `reason:` column; collapses semantic categories | |
| Isolated only (ghost separate command) | Splits into two commands; pushes ghost out of P1 scope | |

**User's choice:** Two labeled sections.
**Notes:** Ghost source is Phase 15 `enrichment.json` — planner must make the second section graceful when enrichment is absent. Drives D-05.

---

## Claude's Discretion

- Plan 00 refactor shape (glob-at-uninstall vs install manifest) — planner chooses.
- `/graphify-wayfind` MOC-root heuristic — planner picks default (suggested: largest community's MOC, tie-break lowest community_id).

## Deferred Ideas

- `/graphify-bridge` (OBSCMD-09) → v1.4.x
- `/graphify-voice` (OBSCMD-10) → v1.4.x + anti-impersonation guard design
- `/graphify-drift-notes` (OBSCMD-11) → v1.4.x
- `trigger_pipeline` frontmatter + cost-preview banner (OBSCMD-12) → v1.4.x
- Productizing user-designated MOC home note — future milestone
