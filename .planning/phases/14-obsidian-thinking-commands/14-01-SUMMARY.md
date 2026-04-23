---
phase: 14-obsidian-thinking-commands
plan: 01
subsystem: installer
tags: [installer, cli, frontmatter, platform-filter, tdd]
requires: [14-00]
provides:
  - target-frontmatter-parse
  - platform-target-filter
  - no-obsidian-commands-flag
  - legacy-target-backfill
  - graphify-prefix-enforcement
affects:
  - graphify/__main__.py
  - graphify/commands/argue.md
  - graphify/commands/ask.md
  - graphify/commands/challenge.md
  - graphify/commands/connect.md
  - graphify/commands/context.md
  - graphify/commands/drift.md
  - graphify/commands/emerge.md
  - graphify/commands/ghost.md
  - graphify/commands/trace.md
  - tests/test_install.py
  - tests/test_commands.py
tech-stack:
  added: []
  patterns:
    - "stdlib re-module head-only frontmatter parse (no PyYAML dep)"
    - "permissive-default supports list for back-compat during partial rollout"
    - "shallow-copy cfg for per-install mutations (never mutate module dict)"
key-files:
  created: []
  modified:
    - graphify/__main__.py
    - graphify/commands/argue.md
    - graphify/commands/ask.md
    - graphify/commands/challenge.md
    - graphify/commands/connect.md
    - graphify/commands/context.md
    - graphify/commands/drift.md
    - graphify/commands/emerge.md
    - graphify/commands/ghost.md
    - graphify/commands/trace.md
    - tests/test_install.py
    - tests/test_commands.py
decisions:
  - "Head-only 1024-byte read in _read_command_target — bounds memory and exposure per T-14-01-01; sufficient because frontmatter always appears at file start."
  - "Missing target: frontmatter defaults to \"both\" — Pitfall-1 mitigation from 14-RESEARCH.md; preserves behavior for any pre-Phase-14 command file authored without the field."
  - "_PLATFORM_CONFIG['supports'] default falls back to permissive [code, obsidian] inside _install_commands, so third-party callers passing ad-hoc cfg dicts still install both kinds."
  - "no_obsidian_commands shallow-copies cfg and filters its 'supports' list rather than mutating the module-level _PLATFORM_CONFIG dict — defense-in-depth for TM-14-02 (drift)."
  - "Prefix-enforcement is test-level (test_graphify_prefix_enforced), not runtime — keeps the installer path simple; the invariant fails loudly at CI time for any command file added without the graphify- prefix or a spot in the legacy allow-list."
metrics:
  duration_seconds: 253
  tasks_completed: 2
  files_modified: 12
  completed_date: 2026-04-22
requirements_completed:
  - OBSCMD-02
  - OBSCMD-07
threat_mitigations:
  - TM-14-02
  - TM-14-04
---

# Phase 14 Plan 01: Platform-Aware Command Filter Summary

**One-liner:** Introduced `target: obsidian|code|both` frontmatter + per-platform `supports: [...]` filter in `_install_commands`, added `--no-obsidian-commands` CLI flag, backfilled `target: both` on all 9 legacy commands, and enforced the `/graphify-*` prefix invariant for all future commands — unblocking Wave 2 obsidian-only command additions without a parallel whitelist.

## What Shipped

- **`graphify/__main__.py`**
  - `_TARGET_RE = re.compile(r"^target:\s*(obsidian|code|both)\s*$", re.MULTILINE)` — stdlib-only parser; no PyYAML dependency added.
  - `_read_command_target(src: Path) -> str`: head-only (1024-byte) read with `errors="replace"`; returns `"both"` on missing field or OSError.
  - `_install_commands` extended with per-file target filter: `if target != "both" and target not in supports: continue`.
  - Every `_PLATFORM_CONFIG` entry (11 platforms) now declares `"supports": [...]`. `claude` and `windows` get `["code", "obsidian"]`; all 9 others get `["code"]`.
  - `install()` signature gains `no_obsidian_commands: bool = False`; when True, shallow-copies `cfg` and filters `"obsidian"` out of its `supports` list (never mutates module-level dict).
  - CLI `install` subcommand parses `--no-obsidian-commands` and threads it through, mirroring the existing `--no-commands` pattern at lines 1738-1741.
- **`graphify/commands/{argue,ask,challenge,connect,context,drift,emerge,ghost,trace}.md`** — `target: both` inserted as the last frontmatter key on each of the 9 legacy files.
- **`tests/test_install.py`** — 8 new tests: `test_install_missing_target_defaults_both`, `test_read_command_target_parses_obsidian`, `test_read_command_target_parses_code`, `test_install_filters_by_target`, `test_install_filter_allows_matching_target`, `test_no_obsidian_commands_flag`, `test_legacy_commands_still_install`, `test_platform_config_has_supports_key`.
- **`tests/test_commands.py`** — 2 new tests (`test_legacy_commands_have_target`, `test_graphify_prefix_enforced`) plus 2 assertion flips (`test_ask_md_frontmatter` and `test_argue_md_frontmatter` now require `fm.get("target") == "both"`).

## Commits

| Task | Type | Hash      | Message |
| ---- | ---- | --------- | ------- |
| 1    | test | `17f3cb4` | `test(14-01): add failing target-filter, prefix-enforcement, legacy-backfill tests` |
| 2    | feat | `346bee9` | `feat(14-01): target-filter installer + --no-obsidian-commands + legacy backfill (OBSCMD-02, OBSCMD-07)` |

## Verification

- `pytest tests/test_install.py tests/test_commands.py -q` → **76 passed**
- `pytest tests/ -q` → **1422 passed, 2 warnings** (baseline 1412 + 10 new; 0 regressions)
- `grep -l "^target: both$" graphify/commands/*.md | wc -l` → **9** (all legacy files backfilled)
- `grep -n "_read_command_target\|_TARGET_RE" graphify/__main__.py` → **4 matches** (definition + usages)
- `grep -c '"supports":' graphify/__main__.py` → **12** (11 platform entries + 1 permissive default in `_install_commands`)
- `grep -n "no_obsidian_commands\|no-obsidian-commands" graphify/__main__.py` → **9 matches** (signature, cfg mutate, CLI parse, threading)

## Success Criteria

- [x] All 9 legacy command files carry `target: both`
- [x] `_read_command_target` + `_TARGET_RE` in `__main__.py`
- [x] Every `_PLATFORM_CONFIG` entry has `supports: [...]`
- [x] `--no-obsidian-commands` CLI flag parsed and threaded through `install()`
- [x] `test_install_filters_by_target`, `test_no_obsidian_commands_flag`, `test_legacy_commands_have_target`, `test_graphify_prefix_enforced`, `test_legacy_commands_still_install`, `test_install_missing_target_defaults_both` all pass
- [x] Full `pytest tests/ -q` green (1422 passed)

## Threat Mitigations

- **TM-14-02 (Whitelist drift, _PLATFORM_CONFIG vs commands/):** Mitigated. `_PLATFORM_CONFIG['supports']` is a **capability intent list** (e.g. `["code", "obsidian"]`) — never a filename whitelist. The single source of truth for *which files exist* remains `graphify/commands/*.md`; the source of truth for *which install* remains the file's own `target:` frontmatter. `test_graphify_prefix_enforced` at test-time catches any new file that violates the `/graphify-*` naming convention and so can't silently drift into a foreign namespace.
- **TM-14-04 (Command name spoofing / shadow-collision):** Mitigated. `test_graphify_prefix_enforced` requires every new command to either begin with `graphify-` or appear in the closed 9-name legacy allow-list. A command file named e.g. `deploy.md` that would shadow a user's existing slash command cannot land without first being added to the legacy allow-list in `tests/test_commands.py` — a visible code-review trigger.
- **T-14-01-01 (Info disclosure via `_read_command_target`):** Accepted. Reads only the first 1024 bytes of each command file (head-only) with `errors="replace"`; defaults to `"both"` on OSError. No file content is logged or embedded in output beyond the `(target=...)` stdout line (which reveals only the three-valued classification).
- **T-14-01-02 (Assertion-flip contract change):** Accepted. `test_ask_md_frontmatter` and `test_argue_md_frontmatter` flipped from `"target" not in fm` to `fm.get("target") == "both"` — this is an intentional invariant update (the 9 legacy files now carry `target: both`), not a regression of prior guarantees.

## Deviations from Plan

None — plan executed as written. One minor hardening beyond the spec: added three extra tests (`test_read_command_target_parses_obsidian`, `test_read_command_target_parses_code`, `test_platform_config_has_supports_key`) to give the `_read_command_target` helper and the `supports` invariant their own direct coverage. These are additive and cost nothing at runtime.

## TDD Gate Compliance

- RED gate: `test(14-01): add failing target-filter, prefix-enforcement, legacy-backfill tests` — commit `17f3cb4` (9 tests failing on merge; no implementation yet) ✓
- GREEN gate: `feat(14-01): target-filter installer + --no-obsidian-commands + legacy backfill` — commit `346bee9` (all 76 tests green) ✓
- REFACTOR gate: not needed; implementation is minimal and the GREEN commit doubles as the final shape.

## Known Stubs

None. The `--no-obsidian-commands` flag is fully wired from CLI argv parse → `install()` kwarg → `cfg` shallow-copy → `_install_commands` filter. Every platform's `supports` list reflects deliberate per-platform intent (not a placeholder), and every legacy command file carries a real `target: both` rather than a TODO marker.

## Self-Check: PASSED

- FOUND: `graphify/__main__.py` (modified)
- FOUND: `graphify/commands/argue.md` through `trace.md` (9 files, each with `target: both`)
- FOUND: `tests/test_install.py` (8 new tests)
- FOUND: `tests/test_commands.py` (2 new tests + 2 flips)
- FOUND: commit `17f3cb4` in `git log`
- FOUND: commit `346bee9` in `git log`
- FOUND: `.planning/phases/14-obsidian-thinking-commands/14-01-SUMMARY.md`
