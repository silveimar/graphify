"""Tests for graphify install --platform routing."""
import re
from pathlib import Path
from unittest.mock import patch
import pytest


PLATFORMS = {
    "claude": (".claude/skills/graphify/SKILL.md",),
    "codex": (".agents/skills/graphify/SKILL.md",),
    "opencode": (".config/opencode/skills/graphify/SKILL.md",),
    "claw": (".openclaw/skills/graphify/SKILL.md",),
    "droid": (".factory/skills/graphify/SKILL.md",),
    "trae": (".trae/skills/graphify/SKILL.md",),
    "trae-cn": (".trae-cn/skills/graphify/SKILL.md",),
    "windows": (".claude/skills/graphify/SKILL.md",),
}


def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)


def test_install_default_claude(tmp_path):
    _install(tmp_path, "claude")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_codex(tmp_path):
    _install(tmp_path, "codex")
    assert (tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_opencode(tmp_path):
    _install(tmp_path, "opencode")
    assert (tmp_path / ".config" / "opencode" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_claw(tmp_path):
    _install(tmp_path, "claw")
    assert (tmp_path / ".openclaw" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_droid(tmp_path):
    _install(tmp_path, "droid")
    assert (tmp_path / ".factory" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_trae(tmp_path):
    _install(tmp_path, "trae")
    assert (tmp_path / ".trae" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_trae_cn(tmp_path):
    _install(tmp_path, "trae-cn")
    assert (tmp_path / ".trae-cn" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_windows(tmp_path):
    _install(tmp_path, "windows")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_unknown_platform_exits(tmp_path):
    with pytest.raises(SystemExit):
        _install(tmp_path, "unknown")


def test_codex_skill_contains_spawn_agent():
    """Codex skill file must reference spawn_agent."""
    import graphify
    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
    assert "spawn_agent" in skill


def test_opencode_skill_contains_mention():
    """OpenCode skill file must reference @mention."""
    import graphify
    skill = (Path(graphify.__file__).parent / "skill-opencode.md").read_text()
    assert "@mention" in skill


def test_claw_skill_is_sequential():
    """OpenClaw skill file must describe sequential extraction."""
    import graphify
    skill = (Path(graphify.__file__).parent / "skill-claw.md").read_text()
    assert "sequential" in skill.lower()
    assert "spawn_agent" not in skill
    assert "@mention" not in skill


def test_all_skill_files_exist_in_package():
    """All installable platform skill files must be present in the installed package."""
    import graphify
    pkg = Path(graphify.__file__).parent
    for name in ("skill.md", "skill-codex.md", "skill-opencode.md", "skill-claw.md", "skill-windows.md", "skill-droid.md", "skill-trae.md"):
        assert (pkg / name).exists(), f"Missing: {name}"


def test_claude_install_registers_claude_md(tmp_path):
    """Claude platform install writes CLAUDE.md; others do not."""
    _install(tmp_path, "claude")
    assert (tmp_path / ".claude" / "CLAUDE.md").exists()


def test_codex_install_does_not_write_claude_md(tmp_path):
    _install(tmp_path, "codex")
    assert not (tmp_path / ".claude" / "CLAUDE.md").exists()


# --- always-on AGENTS.md install/uninstall tests ---

def _agents_install(tmp_path, platform):
    from graphify.__main__ import _agents_install as _install_fn
    _install_fn(tmp_path, platform)


def _agents_uninstall(tmp_path):
    from graphify.__main__ import _agents_uninstall as _uninstall_fn
    _uninstall_fn(tmp_path)


def test_codex_agents_install_writes_agents_md(tmp_path):
    _agents_install(tmp_path, "codex")
    agents_md = tmp_path / "AGENTS.md"
    assert agents_md.exists()
    assert "graphify" in agents_md.read_text()
    assert "GRAPH_REPORT.md" in agents_md.read_text()


def test_opencode_agents_install_writes_agents_md(tmp_path):
    _agents_install(tmp_path, "opencode")
    assert (tmp_path / "AGENTS.md").exists()


def test_claw_agents_install_writes_agents_md(tmp_path):
    _agents_install(tmp_path, "claw")
    assert (tmp_path / "AGENTS.md").exists()


def test_agents_install_idempotent(tmp_path):
    """Installing twice does not duplicate the section."""
    _agents_install(tmp_path, "codex")
    _agents_install(tmp_path, "codex")
    content = (tmp_path / "AGENTS.md").read_text()
    assert content.count("## graphify") == 1


def test_agents_install_appends_to_existing(tmp_path):
    """Installs into an existing AGENTS.md without overwriting other content."""
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# Existing rules\n\nDo not break things.\n")
    _agents_install(tmp_path, "codex")
    content = agents_md.read_text()
    assert "Do not break things." in content
    assert "## graphify" in content


def test_agents_uninstall_removes_section(tmp_path):
    _agents_install(tmp_path, "codex")
    _agents_uninstall(tmp_path)
    agents_md = tmp_path / "AGENTS.md"
    # File deleted when it only contained graphify section
    assert not agents_md.exists()


def test_agents_uninstall_preserves_other_content(tmp_path):
    """Uninstall keeps pre-existing content."""
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# Existing rules\n\nDo not break things.\n")
    _agents_install(tmp_path, "codex")
    _agents_uninstall(tmp_path)
    assert agents_md.exists()
    content = agents_md.read_text()
    assert "Do not break things." in content
    assert "## graphify" not in content


def test_agents_uninstall_no_op_when_not_installed(tmp_path, capsys):
    _agents_uninstall(tmp_path)
    out = capsys.readouterr().out
    assert "nothing to do" in out


# --- OpenCode plugin tests ---

def test_opencode_agents_install_writes_plugin(tmp_path):
    """opencode install writes .opencode/plugins/graphify.js."""
    _agents_install(tmp_path, "opencode")
    plugin = tmp_path / ".opencode" / "plugins" / "graphify.js"
    assert plugin.exists()
    assert "tool.execute.before" in plugin.read_text()


def test_opencode_agents_install_registers_plugin_in_config(tmp_path):
    """opencode install registers the plugin in opencode.json."""
    _agents_install(tmp_path, "opencode")
    config_file = tmp_path / "opencode.json"
    assert config_file.exists()
    import json as _json
    config = _json.loads(config_file.read_text())
    assert any("graphify.js" in p for p in config.get("plugin", []))


def test_opencode_agents_install_merges_existing_config(tmp_path):
    """opencode install preserves existing opencode.json keys."""
    import json as _json
    config_file = tmp_path / "opencode.json"
    config_file.write_text(_json.dumps({"model": "claude-opus-4-5", "plugin": []}))
    _agents_install(tmp_path, "opencode")
    config = _json.loads(config_file.read_text())
    assert config["model"] == "claude-opus-4-5"
    assert any("graphify.js" in p for p in config["plugin"])


def test_opencode_agents_uninstall_removes_plugin(tmp_path):
    """opencode uninstall removes the plugin file and deregisters from opencode.json."""
    import json as _json
    _agents_install(tmp_path, "opencode")
    _agents_uninstall(tmp_path)
    plugin = tmp_path / ".opencode" / "plugins" / "graphify.js"
    assert not plugin.exists()
    config_file = tmp_path / "opencode.json"
    if config_file.exists():
        config = _json.loads(config_file.read_text())
        assert not any("graphify.js" in p for p in config.get("plugin", []))


# ── Cursor ────────────────────────────────────────────────────────────────────

def test_cursor_install_writes_rule(tmp_path):
    """cursor install writes .cursor/rules/graphify.mdc."""
    from graphify.__main__ import _cursor_install
    _cursor_install(tmp_path)
    rule = tmp_path / ".cursor" / "rules" / "graphify.mdc"
    assert rule.exists()
    content = rule.read_text()
    assert "alwaysApply: true" in content
    assert "graphify-out/GRAPH_REPORT.md" in content


def test_cursor_install_idempotent(tmp_path):
    """cursor install does not overwrite an existing rule file."""
    from graphify.__main__ import _cursor_install
    _cursor_install(tmp_path)
    rule = tmp_path / ".cursor" / "rules" / "graphify.mdc"
    original = rule.read_text()
    _cursor_install(tmp_path)
    assert rule.read_text() == original


def test_cursor_uninstall_removes_rule(tmp_path):
    """cursor uninstall removes the rule file."""
    from graphify.__main__ import _cursor_install, _cursor_uninstall
    _cursor_install(tmp_path)
    _cursor_uninstall(tmp_path)
    rule = tmp_path / ".cursor" / "rules" / "graphify.mdc"
    assert not rule.exists()


def test_cursor_uninstall_noop_if_not_installed(tmp_path):
    """cursor uninstall does nothing if rule was never written."""
    from graphify.__main__ import _cursor_uninstall
    _cursor_uninstall(tmp_path)  # should not raise


def test_install_cursor_via_install_helper(tmp_path, monkeypatch):
    """Regression CR-02: install(platform='cursor') must not raise TypeError.

    Before the fix, _cursor_install() was called with zero arguments inside
    install(), but the function signature requires project_dir: Path.
    This test calls the public install() helper with platform='cursor' and
    verifies it succeeds without TypeError.
    """
    import graphify.__main__ as m
    # Patch _cursor_install to write into tmp_path instead of cwd
    called_with = []

    def _fake_cursor_install(project_dir):
        called_with.append(project_dir)
        # Simulate the real function writing to project_dir
        rule = project_dir / ".cursor" / "rules" / "graphify.mdc"
        rule.parent.mkdir(parents=True, exist_ok=True)
        rule.write_text("# graphify cursor rule\nalwaysApply: true\n")

    monkeypatch.setattr(m, "_cursor_install", _fake_cursor_install)

    # Must not raise TypeError
    m.install(platform="cursor")

    assert called_with, "_cursor_install was never called"
    # Argument must be a Path (not missing)
    assert isinstance(called_with[0], m.Path), (
        f"_cursor_install was called with {called_with[0]!r}, expected a Path"
    )


# ── Gemini CLI ────────────────────────────────────────────────────────────────

def test_gemini_install_writes_gemini_md(tmp_path):
    from graphify.__main__ import gemini_install
    gemini_install(tmp_path)
    md = tmp_path / "GEMINI.md"
    assert md.exists()
    assert "graphify-out/GRAPH_REPORT.md" in md.read_text()

def test_gemini_install_writes_hook(tmp_path):
    import json as _json
    from graphify.__main__ import gemini_install
    gemini_install(tmp_path)
    settings = _json.loads((tmp_path / ".gemini" / "settings.json").read_text())
    hooks = settings["hooks"]["BeforeTool"]
    assert any("graphify" in str(h) for h in hooks)

def test_gemini_install_idempotent(tmp_path):
    from graphify.__main__ import gemini_install
    gemini_install(tmp_path)
    gemini_install(tmp_path)
    md = tmp_path / "GEMINI.md"
    assert md.read_text().count("## graphify") == 1

def test_gemini_install_merges_existing_gemini_md(tmp_path):
    from graphify.__main__ import gemini_install
    (tmp_path / "GEMINI.md").write_text("# My project rules\n")
    gemini_install(tmp_path)
    content = (tmp_path / "GEMINI.md").read_text()
    assert "# My project rules" in content
    assert "graphify-out/GRAPH_REPORT.md" in content

def test_gemini_uninstall_removes_section(tmp_path):
    from graphify.__main__ import gemini_install, gemini_uninstall
    gemini_install(tmp_path)
    gemini_uninstall(tmp_path)
    md = tmp_path / "GEMINI.md"
    assert not md.exists()

def test_gemini_uninstall_removes_hook(tmp_path):
    import json as _json
    from graphify.__main__ import gemini_install, gemini_uninstall
    gemini_install(tmp_path)
    gemini_uninstall(tmp_path)
    settings_path = tmp_path / ".gemini" / "settings.json"
    if settings_path.exists():
        settings = _json.loads(settings_path.read_text())
        hooks = settings.get("hooks", {}).get("BeforeTool", [])
        assert not any("graphify" in str(h) for h in hooks)

def test_gemini_uninstall_noop_if_not_installed(tmp_path):
    from graphify.__main__ import gemini_uninstall
    gemini_uninstall(tmp_path)  # should not raise


# ── Phase 11: command file install/uninstall tests ────────────────────────────

def test_install_command_files_claude(tmp_path):
    """D-13: install on claude copies all 5 core command files to .claude/commands/."""
    from unittest.mock import patch
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
    commands_dir = tmp_path / ".claude" / "commands"
    for name in ("context.md", "trace.md", "connect.md", "drift.md", "emerge.md"):
        assert (commands_dir / name).exists(), f"Missing {name} after install"


def test_install_command_files_windows(tmp_path):
    """Plan-checker BLOCKER 3: windows uses the same .claude/commands/ convention as claude.

    RESEARCH.md §Install Path Extension confirms windows has native Claude Code
    commands support. Without this test, a regression that disables commands on
    windows (commands_enabled=False) would silently ship.
    """
    from unittest.mock import patch
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="windows")
    commands_dir = tmp_path / ".claude" / "commands"
    for name in ("context.md", "trace.md", "connect.md", "drift.md", "emerge.md"):
        assert (commands_dir / name).exists(), f"Missing {name} after install on windows"


def test_install_no_commands_flag(tmp_path):
    """D-14: --no-commands skips command-file copy."""
    from unittest.mock import patch
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude", no_commands=True)
    commands_dir = tmp_path / ".claude" / "commands"
    assert not commands_dir.exists() or not any(commands_dir.glob("*.md"))


def test_install_idempotent_commands(tmp_path):
    """D-14: re-running install is idempotent — overwrites in place."""
    from unittest.mock import patch
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        install(platform="claude")   # second run must not raise
    assert (tmp_path / ".claude" / "commands" / "context.md").exists()


def test_uninstall_removes_commands(tmp_path):
    """D-14: uninstall removes previously-installed command files."""
    from unittest.mock import patch
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        uninstall(platform="claude")
    commands_dir = tmp_path / ".claude" / "commands"
    for name in ("context.md", "trace.md", "connect.md", "drift.md", "emerge.md"):
        assert not (commands_dir / name).exists(), f"{name} not removed after uninstall"


def test_uninstall_directory_scan(tmp_path):
    """OBSCMD-01: _uninstall_commands scans graphify/commands/*.md,
    not a hardcoded whitelist."""
    from unittest.mock import patch
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        uninstall(platform="claude")
    dst = tmp_path / ".claude" / "commands"
    # Both legacy and non-legacy names must be removed (proves source-driven scan)
    for name in ["connect.md", "ask.md", "argue.md", "context.md", "trace.md"]:
        assert not (dst / name).exists(), f"{name} not removed by directory-scan uninstall"


def test_uninstall_idempotent(tmp_path):
    """OBSCMD-01: repeated uninstall is a no-op (no exceptions)."""
    from unittest.mock import patch
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        uninstall(platform="claude")
        uninstall(platform="claude")  # must not raise


def test_install_non_claude_platform_skips_commands(tmp_path):
    """D-13: non-Claude platforms (commands_enabled=False) do not receive command files.

    Note: `windows` IS Claude Code (commands_enabled=True); this test uses `codex`
    which has no native slash-command support.
    """
    from unittest.mock import patch
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="codex")   # commands_enabled=False for codex
    # .claude/commands/ should not exist (or be empty) for a codex install
    assert not (tmp_path / ".claude" / "commands").exists() or \
        not any((tmp_path / ".claude" / "commands").glob("*.md"))


# ============================================================
# Phase 14 Plan 01 — OBSCMD-02: target filter + --no-obsidian-commands
# ============================================================

LEGACY_COMMAND_NAMES = (
    "argue", "ask", "challenge", "connect", "context",
    "drift", "emerge", "ghost", "trace",
)


def test_install_missing_target_defaults_both(tmp_path):
    """OBSCMD-02: a command file without `target:` frontmatter defaults to 'both'."""
    from graphify.__main__ import _read_command_target
    f = tmp_path / "nofield.md"
    f.write_text(
        "---\nname: foo\ndisable-model-invocation: true\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert _read_command_target(f) == "both"


def test_read_command_target_parses_obsidian(tmp_path):
    """_read_command_target extracts target: obsidian from frontmatter."""
    from graphify.__main__ import _read_command_target
    f = tmp_path / "vault-only.md"
    f.write_text(
        "---\nname: graphify-vault\ntarget: obsidian\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert _read_command_target(f) == "obsidian"


def test_read_command_target_parses_code(tmp_path):
    """_read_command_target extracts target: code from frontmatter."""
    from graphify.__main__ import _read_command_target
    f = tmp_path / "code-only.md"
    f.write_text(
        "---\nname: graphify-code\ntarget: code\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert _read_command_target(f) == "code"


def test_install_filters_by_target(tmp_path, monkeypatch):
    """OBSCMD-02: _install_commands skips files whose target is not in platform supports."""
    from graphify.__main__ import _install_commands
    # Build synthetic src dir with an obsidian-only file and a both file
    src_dir = tmp_path / "src_commands"
    src_dir.mkdir()
    (src_dir / "vault-only.md").write_text(
        "---\nname: graphify-vault\ntarget: obsidian\n---\nBody\n",
        encoding="utf-8",
    )
    (src_dir / "universal.md").write_text(
        "---\nname: graphify-universal\ntarget: both\n---\nBody\n",
        encoding="utf-8",
    )
    dst_dir = tmp_path / ".claude" / "commands"
    cfg = {
        "commands_enabled": True,
        "commands_dst": Path(".claude") / "commands",
        "supports": ["code"],  # NOT including obsidian
    }
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        _install_commands(cfg, src_dir, verbose=False)
    assert (dst_dir / "universal.md").exists(), "target: both must install on code-only platform"
    assert not (dst_dir / "vault-only.md").exists(), "target: obsidian must be filtered out"


def test_install_filter_allows_matching_target(tmp_path):
    """OBSCMD-02: target: obsidian installs on a platform whose supports includes obsidian."""
    from graphify.__main__ import _install_commands
    src_dir = tmp_path / "src_commands"
    src_dir.mkdir()
    (src_dir / "vault-only.md").write_text(
        "---\nname: graphify-vault\ntarget: obsidian\n---\nBody\n",
        encoding="utf-8",
    )
    cfg = {
        "commands_enabled": True,
        "commands_dst": Path(".claude") / "commands",
        "supports": ["code", "obsidian"],
    }
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        _install_commands(cfg, src_dir, verbose=False)
    assert (tmp_path / ".claude" / "commands" / "vault-only.md").exists()


def test_no_obsidian_commands_flag(tmp_path):
    """OBSCMD-02: --no-obsidian-commands suppresses target: obsidian files."""
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude", no_obsidian_commands=True)
    dst = tmp_path / ".claude" / "commands"
    # All 9 legacy commands are target: both → survive the flag
    for name in LEGACY_COMMAND_NAMES:
        assert (dst / f"{name}.md").exists(), f"{name}.md (target: both) must survive --no-obsidian-commands"


def test_legacy_commands_still_install(tmp_path):
    """Regression: all 9 legacy commands still install on claude after Plan 01."""
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
    dst = tmp_path / ".claude" / "commands"
    for name in LEGACY_COMMAND_NAMES:
        assert (dst / f"{name}.md").exists(), f"{name}.md must still install"


def test_platform_config_has_supports_key():
    """Every _PLATFORM_CONFIG entry must declare a `supports` list."""
    from graphify.__main__ import _PLATFORM_CONFIG
    for plat, cfg in _PLATFORM_CONFIG.items():
        assert "supports" in cfg, f"platform {plat!r} missing 'supports' key"
        assert isinstance(cfg["supports"], list) and cfg["supports"], (
            f"platform {plat!r}: 'supports' must be a non-empty list"
        )
        for s in cfg["supports"]:
            assert s in ("code", "obsidian"), (
                f"platform {plat!r}: unknown support target {s!r}"
            )


# ---------------------------------------------------------------------------
# Phase 22 — Excalidraw skill (Tasks 1, 5; install/uninstall in plan 22-02)
# ---------------------------------------------------------------------------


def _read_excalidraw_skill() -> str:
    import graphify
    return (Path(graphify.__file__).parent / "skill-excalidraw.md").read_text(
        encoding="utf-8"
    )


# --- Skill content tests (Task 5) ------------------------------------------


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — skill file authored in Task 5")
def test_excalidraw_skill_in_package():
    import graphify
    pkg = Path(graphify.__file__).parent
    assert (pkg / "skill-excalidraw.md").exists()


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — skill file authored in Task 5")
def test_excalidraw_skill_has_seven_steps():
    body = _read_excalidraw_skill()
    # Either 7 numbered list items at line start, or an explicit
    # "## What I do (7 steps)" section with 7 numbered children.
    numbered = re.findall(r"^[1-7]\.", body, re.M)
    assert len(numbered) >= 7, f"expected >=7 numbered steps, got {len(numbered)}"


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — skill file authored in Task 5")
def test_excalidraw_skill_calls_seed_tools():
    body = _read_excalidraw_skill()
    assert "list_diagram_seeds" in body
    assert "get_diagram_seed" in body


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — skill file authored in Task 5")
def test_excalidraw_skill_has_mcp_json():
    body = _read_excalidraw_skill()
    assert "mcpServers" in body


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — skill file authored in Task 5")
def test_excalidraw_skill_has_style_rules():
    body = _read_excalidraw_skill()
    assert "fontFamily: 5" in body
    assert "#1e1e2e" in body
    assert "transparent" in body
    assert "compress: false" in body


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — skill file authored in Task 5")
def test_excalidraw_skill_has_guard_list():
    body = _read_excalidraw_skill().lower()
    # Forbidden mentions in guard list
    assert "lzstring" in body
    assert "label" in body  # "label-derived" guard
    assert "multi-seed" in body or "multi seed" in body
    assert "frontmatter" in body
    assert ".mcp.json" in body


# --- Install/uninstall/idempotency tests (Plan 22-02) ----------------------


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")
def test_install_excalidraw(tmp_path):
    _install(tmp_path, "excalidraw")
    assert (
        tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md"
    ).exists()


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")
def test_uninstall_excalidraw(tmp_path):
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="excalidraw")
        uninstall(platform="excalidraw")
    assert not (
        tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md"
    ).exists()


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")
def test_install_excalidraw_idempotent(tmp_path):
    _install(tmp_path, "excalidraw")
    target = tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md"
    first = target.read_text(encoding="utf-8")
    _install(tmp_path, "excalidraw")
    second = target.read_text(encoding="utf-8")
    assert first == second


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")
def test_uninstall_excalidraw_idempotent(tmp_path):
    from graphify.__main__ import uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        uninstall(platform="excalidraw")  # absent → no-op
        uninstall(platform="excalidraw")  # absent again → still no-op


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")
def test_install_excalidraw_does_not_touch_claude_skill(tmp_path):
    _install(tmp_path, "claude")
    _install(tmp_path, "excalidraw")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()
    assert (
        tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md"
    ).exists()


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — install wiring in Plan 22-02")
def test_platform_config_has_excalidraw():
    from graphify.__main__ import _PLATFORM_CONFIG
    assert "excalidraw" in _PLATFORM_CONFIG
