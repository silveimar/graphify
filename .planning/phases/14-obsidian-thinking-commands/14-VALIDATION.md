---
phase: 14
slug: obsidian-thinking-commands
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-22
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from 14-RESEARCH.md §Validation Architecture. Planner fills in per-task rows.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — see `pyproject.toml`, CI runs Python 3.10 and 3.12) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_commands.py tests/test_install.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10–30 seconds (full suite pure unit; no network, no FS outside tmp_path) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_commands.py tests/test_install.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Planner populates this table during plan creation. Each P1 requirement must have at least one automated row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-00-XX | 00 | 1 | OBSCMD-01 | — | `_uninstall_commands` removes all installed `.md` files via directory scan (symmetric with install glob) | unit | `pytest tests/test_install.py::test_uninstall_directory_scan -q` | ❌ W0 | ⬜ pending |
| 14-00-XX | 00 | 1 | OBSCMD-01 | — | Idempotent: second uninstall is a no-op (no errors, no extra deletes) | unit | `pytest tests/test_install.py::test_uninstall_idempotent -q` | ❌ W0 | ⬜ pending |
| 14-01-XX | 01 | 1 | OBSCMD-02 | — | `_install_commands` filters by `target:` frontmatter vs platform `supports:` list | unit | `pytest tests/test_install.py::test_install_filters_by_target -q` | ❌ W0 | ⬜ pending |
| 14-01-XX | 01 | 1 | OBSCMD-02 | — | `target:` absent defaults to `both` (backward compat for the 9 legacy commands) | unit | `pytest tests/test_install.py::test_install_missing_target_defaults_both -q` | ❌ W0 | ⬜ pending |
| 14-01-XX | 01 | 1 | OBSCMD-02 | — | `--no-obsidian-commands` CLI flag suppresses vault-only commands on `install` | unit | `pytest tests/test_install.py::test_no_obsidian_commands_flag -q` | ❌ W0 | ⬜ pending |
| 14-01-XX | 01 | 1 | OBSCMD-02 | — | All 9 existing command files carry `target: both` after backfill | unit | `pytest tests/test_commands.py::test_legacy_commands_have_target -q` | ❌ W0 | ⬜ pending |
| 14-01-XX | 01 | 1 | OBSCMD-07 | — | All command files use the `/graphify-*` prefix OR an allow-listed legacy name; no new command without the prefix ships | unit | `pytest tests/test_commands.py::test_graphify_prefix_enforced -q` | ❌ W0 | ⬜ pending |
| 14-02-XX | 02 | 2 | OBSCMD-03 | — | `graphify/commands/graphify-moc.md` exists with valid frontmatter (`name`, `description`, `target: both`) | unit | `pytest tests/test_commands.py::test_graphify_moc_frontmatter -q` | ❌ W0 | ⬜ pending |
| 14-02-XX | 02 | 2 | OBSCMD-03, OBSCMD-08 | TM-14-01 | `graphify-moc.md` body references `get_community`, `load_profile`, AND `propose_vault_note` (never a direct write helper) | unit-grep | `pytest tests/test_commands.py::test_moc_trust_boundary_and_contract -q` | ❌ W0 | ⬜ pending |
| 14-03-XX | 03 | 2 | OBSCMD-04 | — | `graphify-related.md` exists with valid frontmatter; body references `get_focus_context` and reads note frontmatter `source_file` | unit-grep | `pytest tests/test_commands.py::test_related_contract -q` | ❌ W0 | ⬜ pending |
| 14-03-XX | 03 | 2 | OBSCMD-04 | — | Skill text explicitly handles `get_focus_context` `status == no_context` (spoof-silent invariant from Phase 18 SC2) | unit-grep | `pytest tests/test_commands.py::test_related_handles_no_context -q` | ❌ W0 | ⬜ pending |
| 14-04-XX | 04 | 2 | OBSCMD-05 | — | `graphify-orphan.md` exists; body produces two labeled sections: `## Isolated Nodes` and `## Stale/Ghost Nodes` | unit-grep | `pytest tests/test_commands.py::test_orphan_dual_sections -q` | ❌ W0 | ⬜ pending |
| 14-04-XX | 04 | 2 | OBSCMD-05 | — | `/graphify-orphan` degrades gracefully when `enrichment.json` is absent (renders isolated section + banner, not error) | integration | `pytest tests/test_commands.py::test_orphan_graceful_without_enrichment -q` | ❌ W0 | ⬜ pending |
| 14-05-XX | 05 | 2 | OBSCMD-06 | — | `graphify-wayfind.md` exists; body references `connect_topics` shortest-path MCP tool | unit-grep | `pytest tests/test_commands.py::test_wayfind_contract -q` | ❌ W0 | ⬜ pending |
| 14-02..05 | 02-05 | 2 | OBSCMD-08 | TM-14-01 | Every new command skill.md that produces a vault note references `propose_vault_note`; none calls a direct write helper | unit-grep | `pytest tests/test_commands.py::test_trust_boundary_invariant_all_p1 -q` | ❌ W0 | ⬜ pending |
| 14-all | 00-05 | — | regression | — | Existing 9 legacy commands still install on Claude platform after `target` filter lands | integration | `pytest tests/test_install.py::test_legacy_commands_still_install -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*File Exists: ✅ present · ❌ W0 = Wave 0 must create*

---

## Wave 0 Requirements

Each row's test above marked `❌ W0` must exist before Wave 1 starts. Practical minimum:

- [ ] `tests/test_commands.py` — extend existing module with frontmatter-schema, trust-boundary-grep, and dual-section assertions for all 4 P1 commands + the 9 legacy backfill check
- [ ] `tests/test_install.py` — extend with directory-scan uninstall test, target-filter test, `--no-obsidian-commands` flag test, default-both test, legacy-regression test
- [ ] Minimal fixtures in `tests/conftest.py` if any new helpers are needed (existing pytest tmp_path + monkeypatch pattern should suffice)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end `/graphify-moc <community_id>` renders MOC via vault profile template inside an actual Obsidian vault and pends user `graphify approve` | OBSCMD-03 (success criterion #1) | Requires real Obsidian vault + user interaction with the skill-orchestrated LLM loop | Create a test vault with `.graphify/profile.yaml`; run `/graphify-moc 0`; verify a proposal appears in `graphify-out/proposals/` and `graphify approve` writes the MOC to the vault |
| `/graphify-related` inside an Obsidian session shows community + 1-hop neighbors for the active note | OBSCMD-04 (success criterion #2) | Requires real vault + active note context | Open a note whose `source_file` is in the graph; run `/graphify-related <note-path>`; confirm output lists community peers + 1-hop neighbors |
| `/graphify-wayfind` breadcrumb is human-useful (not just technically shortest) | OBSCMD-06 (success criterion #4) | Subjective usefulness | Navigate from MOC to a deep note; verify breadcrumb is readable and accurate |

---

## Threat Model Refs

| Threat ID | Description | Mitigation Reference |
|-----------|-------------|----------------------|
| TM-14-01 | Vault auto-write bypasses `propose_vault_note + approve` trust boundary | Every P1 command skill.md MUST reference `propose_vault_note` literal string; grep-tested per row above (OBSCMD-08 invariant) |
| TM-14-02 | Installer whitelist drifts from actual command files (re-introduces Plan 00 anti-pattern) | `_PLATFORM_CONFIG` gains only a `supports: [...]` list (not a filename whitelist); runtime frontmatter parse is single source of truth |
| TM-14-03 | Spoofed `source_file` path in `/graphify-related` | Phase 18 CR-01 snapshot-root fix already handles this; skill.md must explicitly handle `status == no_context` so the user sees an explanation, not silence |
| TM-14-04 | Command name collision with user-authored commands | `/graphify-*` prefix enforced via `test_graphify_prefix_enforced` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
