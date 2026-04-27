---
phase: 22
slug: excalidraw-skill-vault-bridge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `22-RESEARCH.md` Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already in project) |
| **Config file** | `pyproject.toml` (no separate `pytest.ini`) |
| **Quick run command** | `pytest tests/test_install.py tests/test_excalidraw_layout.py tests/test_profile.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~60 seconds (full suite, ~1554 existing tests + new) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_install.py tests/test_excalidraw_layout.py tests/test_profile.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-W0 | 01 | 0 | SKILL-06 | T-22-V12 | Wave 0 stubs (xfail) for layout + write | unit | `pytest tests/test_excalidraw_layout.py -x -q` | ❌ W0 | ⬜ pending |
| 22-01-W0 | 01 | 0 | profile schema | T-22-V5 | Wave 0 stubs for `layout_type` / `output_path` | unit | `pytest tests/test_profile.py -x -q` | ❌ W0 (extension) | ⬜ pending |
| 22-01-PROF | 01 | 1 | profile schema | T-22-V5 | `layout_type` + `output_path` accepted by `validate_profile` | unit | `pytest tests/test_profile.py::test_diagram_types_layout_type_accepted -x` | ❌ W0 | ⬜ pending |
| 22-01-PROF-SEC | 01 | 1 | profile schema | T-22-V12 | Path-traversal in `output_path` rejected | unit | `pytest tests/test_profile.py::test_diagram_types_output_path_traversal -x` | ❌ W0 | ⬜ pending |
| 22-01-LAY-1 | 01 | 1 | SKILL-06 | — | `layout_for` covers all 6 valid layout types | unit | `pytest tests/test_excalidraw_layout.py::test_layout_for_all_six_layout_types -x` | ❌ W0 | ⬜ pending |
| 22-01-LAY-2 | 01 | 1 | SKILL-06 | — | `layout_for` is byte-deterministic | unit | `pytest tests/test_excalidraw_layout.py::test_layout_for_is_deterministic -x` | ❌ W0 | ⬜ pending |
| 22-01-LAY-3 | 01 | 1 | SKILL-06 | — | Unknown layout falls back to `mind-map` | unit | `pytest tests/test_excalidraw_layout.py::test_layout_for_unknown_falls_back_to_mind_map -x` | ❌ W0 | ⬜ pending |
| 22-01-WD-1 | 01 | 1 | SKILL-06 | T-22-V12 | `write_diagram` collision: refuses without force | unit | `pytest tests/test_excalidraw_layout.py::test_write_diagram_collision_refuses -x` | ❌ W0 | ⬜ pending |
| 22-01-WD-2 | 01 | 1 | SKILL-06 | T-22-V12 | `write_diagram` blocks path traversal | unit | `pytest tests/test_excalidraw_layout.py::test_write_diagram_path_confined -x` | ❌ W0 | ⬜ pending |
| 22-01-WD-3 | 01 | 1 | SKILL-06 | — | Output contains `compress: false`, `excalidraw-plugin: parsed`, fontFamily 5, valid scene JSON | unit | `pytest tests/test_excalidraw_layout.py::test_write_diagram_compress_false -x` | ❌ W0 | ⬜ pending |
| 22-01-LZ | 01 | 1 | SKILL-06 (ordering) | T-22-V12 | LZ-String denylist still passes | unit | `pytest tests/test_denylist.py::test_no_lzstring_import_anywhere -x` | ✅ exists | ⬜ pending |
| 22-01-SK-7STEP | 01 | 1 | SKILL-04 | — | Skill file references all 7 pipeline steps | unit (text grep) | `pytest tests/test_install.py::test_excalidraw_skill_has_seven_steps -x` | ❌ W0 | ⬜ pending |
| 22-01-SK-MCP | 01 | 1 | SKILL-04 | — | Skill references `list_diagram_seeds` + `get_diagram_seed` | unit | `pytest tests/test_install.py::test_excalidraw_skill_calls_seed_tools -x` | ❌ W0 | ⬜ pending |
| 22-01-SK-MCPJSON | 01 | 1 | SKILL-05 | T-22-V5 | Skill contains `.mcp.json` snippet block | unit | `pytest tests/test_install.py::test_excalidraw_skill_has_mcp_json -x` | ❌ W0 | ⬜ pending |
| 22-01-SK-STYLE | 01 | 1 | SKILL-05 | — | Skill contains style rules (Excalifont 5, `#1e1e2e`, transparent) | unit | `pytest tests/test_install.py::test_excalidraw_skill_has_style_rules -x` | ❌ W0 | ⬜ pending |
| 22-01-SK-GUARD | 01 | 1 | SKILL-05 | T-22-V12 | Skill contains guard list (compress:false, no LZ-String, no label-IDs, no multi-seed) | unit | `pytest tests/test_install.py::test_excalidraw_skill_has_guard_list -x` | ❌ W0 | ⬜ pending |
| 22-02-INST-1 | 02 | 2 | SKILL-01 | — | `graphify install excalidraw` writes skill at expected path | unit | `pytest tests/test_install.py::test_install_excalidraw -x` | ❌ W0 | ⬜ pending |
| 22-02-INST-2 | 02 | 2 | SKILL-01 | — | Skill file packaged in wheel | unit | `pytest tests/test_install.py::test_excalidraw_skill_in_package -x` | ❌ W0 | ⬜ pending |
| 22-02-INST-3 | 02 | 2 | SKILL-01 | — | New `excalidraw` entry exists in `_PLATFORM_CONFIG` | unit | `pytest tests/test_install.py::test_platform_config_has_excalidraw -x` | ❌ W0 | ⬜ pending |
| 22-02-UNIN-1 | 02 | 2 | SKILL-02 | — | `graphify uninstall excalidraw` removes skill | unit | `pytest tests/test_install.py::test_uninstall_excalidraw -x` | ❌ W0 | ⬜ pending |
| 22-02-IDEM-1 | 02 | 2 | SKILL-03 | — | Install twice = identical content | unit | `pytest tests/test_install.py::test_install_excalidraw_idempotent -x` | ❌ W0 | ⬜ pending |
| 22-02-IDEM-2 | 02 | 2 | SKILL-03 | — | Uninstall when absent = no-op | unit | `pytest tests/test_install.py::test_uninstall_excalidraw_idempotent -x` | ❌ W0 | ⬜ pending |
| 22-02-ISOL | 02 | 2 | SKILL-03 (D-07) | — | Install excalidraw does not affect claude install | unit | `pytest tests/test_install.py::test_install_excalidraw_does_not_touch_claude_skill -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_excalidraw_layout.py` — new file; xfail stubs for SKILL-06 (`layout_for`, `write_diagram`)
- [ ] `tests/test_install.py` — extension; xfail stubs for SKILL-01..SKILL-05 (skill file content + install/uninstall/idempotency/isolation)
- [ ] `tests/test_profile.py` — extension; xfail stubs for `layout_type` + `output_path` schema
- [ ] No framework install needed — pytest already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end skill invocation through Claude Code agent calling `mcp_excalidraw` | SKILL-04 (MCP path) | Requires running Claude Code instance with `mcp_excalidraw` server registered; outside scope of pure unit tests (CLAUDE.md: "no network calls, no filesystem side effects outside `tmp_path`"). | After `graphify install excalidraw`, in a vault with `.graphify/profile.yaml`, run `/excalidraw-diagram`, select a seed, confirm `.excalidraw.md` appears at `Excalidraw/Diagrams/{topic}-{layout_type}.excalidraw.md` and renders in Obsidian's Excalidraw plugin. |
| `.excalidraw.md` opens in Obsidian and displays nodes/edges visually | SKILL-06 | Visual rendering can't be asserted from a unit test — only file-format compliance. | Open the fallback-generated file in Obsidian with the Excalidraw plugin; confirm nodes appear at expected layout coordinates and arrows bind. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (3 test files: layout, install ext, profile ext)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (set at planner sign-off)

**Approval:** pending
