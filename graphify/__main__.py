"""graphify CLI - `graphify install` sets up the Claude Code skill."""
from __future__ import annotations
import json
import platform
import re
import shutil
import sys
from pathlib import Path

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("graphifyy")
except Exception:
    __version__ = "unknown"


def _check_skill_version(skill_dst: Path) -> None:
    """Warn if the installed skill is from an older graphify version."""
    version_file = skill_dst.parent / ".graphify_version"
    if not version_file.exists():
        return
    installed = version_file.read_text(encoding="utf-8").strip()
    if installed != __version__:
        print(f"  warning: skill is from graphify {installed}, package is {__version__}. Run 'graphify install' to update.")

_SETTINGS_HOOK = {
    "matcher": "Glob|Grep",
    "hooks": [
        {
            "type": "command",
            "command": (
                "[ -f graphify-out/graph.json ] && "
                r"""echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files."}}' """
                "|| true"
            ),
        }
    ],
}

_SKILL_REGISTRATION = (
    "\n# graphify\n"
    "- **graphify** (`~/.claude/skills/graphify/SKILL.md`) "
    "- any input to knowledge graph. Trigger: `/graphify`\n"
    "When the user types `/graphify`, invoke the Skill tool "
    "with `skill: \"graphify\"` before doing anything else.\n"
)


_PLATFORM_CONFIG: dict[str, dict] = {
    "claude": {
        "skill_file": "skill.md",
        "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
        "claude_md": True,
    },
    "codex": {
        "skill_file": "skill-codex.md",
        "skill_dst": Path(".agents") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "opencode": {
        "skill_file": "skill-opencode.md",
        "skill_dst": Path(".config") / "opencode" / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "aider": {
        "skill_file": "skill-aider.md",
        "skill_dst": Path(".aider") / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "copilot": {
        "skill_file": "skill-copilot.md",
        "skill_dst": Path(".copilot") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "claw": {
        "skill_file": "skill-claw.md",
        "skill_dst": Path(".openclaw") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "droid": {
        "skill_file": "skill-droid.md",
        "skill_dst": Path(".factory") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "trae": {
        "skill_file": "skill-trae.md",
        "skill_dst": Path(".trae") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "trae-cn": {
        "skill_file": "skill-trae.md",
        "skill_dst": Path(".trae-cn") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "antigravity": {
        "skill_file": "skill.md",
        "skill_dst": Path(".agent") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
    "windows": {
        "skill_file": "skill-windows.md",
        "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
        "claude_md": True,
    },
}


def install(platform: str = "claude") -> None:
    if platform == "gemini":
        gemini_install()
        return
    if platform == "cursor":
        _cursor_install()
        return
    if platform not in _PLATFORM_CONFIG:
        print(
            f"error: unknown platform '{platform}'. Choose from: {', '.join(_PLATFORM_CONFIG)}, gemini, cursor, antigravity",
            file=sys.stderr,
        )
        sys.exit(1)

    cfg = _PLATFORM_CONFIG[platform]
    skill_src = Path(__file__).parent / cfg["skill_file"]
    if not skill_src.exists():
        print(f"error: {cfg['skill_file']} not found in package - reinstall graphify", file=sys.stderr)
        sys.exit(1)

    skill_dst = Path.home() / cfg["skill_dst"]
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(skill_src, skill_dst)
    (skill_dst.parent / ".graphify_version").write_text(__version__, encoding="utf-8")
    print(f"  skill installed  ->  {skill_dst}")

    if cfg["claude_md"]:
        # Register in ~/.claude/CLAUDE.md (Claude Code only)
        claude_md = Path.home() / ".claude" / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            if "graphify" in content:
                print(f"  CLAUDE.md        ->  already registered (no change)")
            else:
                claude_md.write_text(content.rstrip() + _SKILL_REGISTRATION, encoding="utf-8")
                print(f"  CLAUDE.md        ->  skill registered in {claude_md}")
        else:
            claude_md.parent.mkdir(parents=True, exist_ok=True)
            claude_md.write_text(_SKILL_REGISTRATION.lstrip(), encoding="utf-8")
            print(f"  CLAUDE.md        ->  created at {claude_md}")

    print()
    print("Done. Open your AI coding assistant and type:")
    print()
    print("  /graphify .")
    print()


_CLAUDE_MD_SECTION = """\
## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/obsidian/ exists, navigate its _COMMUNITY_*.md overview notes and follow [[wikilinks]] between nodes instead of reading raw files
- If graphify-out/wiki/index.md exists (and no obsidian/ vault), navigate the wiki instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
"""

_CLAUDE_MD_MARKER = "## graphify"

# AGENTS.md section for Codex, OpenCode, and OpenClaw.
# All three platforms read AGENTS.md in the project root for persistent instructions.
_AGENTS_MD_SECTION = """\
## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/obsidian/ exists, navigate its _COMMUNITY_*.md overview notes and follow [[wikilinks]] between nodes instead of reading raw files
- If graphify-out/wiki/index.md exists (and no obsidian/ vault), navigate the wiki instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
"""

_AGENTS_MD_MARKER = "## graphify"

_GEMINI_MD_SECTION = """\
## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
"""

_GEMINI_MD_MARKER = "## graphify"

_GEMINI_HOOK = {
    "matcher": "read_file|list_directory",
    "hooks": [
        {
            "type": "command",
            "command": (
                "[ -f graphify-out/graph.json ] && "
                r"""echo '{"decision":"allow","additionalContext":"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files."}' """
                r"""|| echo '{"decision":"allow"}'"""
            ),
        }
    ],
}


def gemini_install(project_dir: Path | None = None) -> None:
    """Copy skill file to ~/.gemini/skills/graphify/, write GEMINI.md section, and install BeforeTool hook."""
    # Copy skill file to ~/.gemini/skills/graphify/SKILL.md
    skill_src = Path(__file__).parent / "skill.md"
    skill_dst = Path.home() / ".gemini" / "skills" / "graphify" / "SKILL.md"
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(skill_src, skill_dst)
    (skill_dst.parent / ".graphify_version").write_text(__version__, encoding="utf-8")
    print(f"  skill installed  ->  {skill_dst}")

    target = (project_dir or Path(".")) / "GEMINI.md"

    if target.exists():
        content = target.read_text(encoding="utf-8")
        if _GEMINI_MD_MARKER in content:
            print("graphify already configured in GEMINI.md")
        else:
            target.write_text(content.rstrip() + "\n\n" + _GEMINI_MD_SECTION, encoding="utf-8")
            print(f"graphify section written to {target.resolve()}")
    else:
        target.write_text(_GEMINI_MD_SECTION, encoding="utf-8")
        print(f"graphify section written to {target.resolve()}")

    _install_gemini_hook(project_dir or Path("."))
    print()
    print("Gemini CLI will now check the knowledge graph before answering")
    print("codebase questions and rebuild it after code changes.")


def _install_gemini_hook(project_dir: Path) -> None:
    settings_path = project_dir / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    except json.JSONDecodeError:
        settings = {}
    before_tool = settings.setdefault("hooks", {}).setdefault("BeforeTool", [])
    settings["hooks"]["BeforeTool"] = [h for h in before_tool if "graphify" not in str(h)]
    settings["hooks"]["BeforeTool"].append(_GEMINI_HOOK)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print("  .gemini/settings.json  ->  BeforeTool hook registered")


def _uninstall_gemini_hook(project_dir: Path) -> None:
    settings_path = project_dir / ".gemini" / "settings.json"
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    before_tool = settings.get("hooks", {}).get("BeforeTool", [])
    filtered = [h for h in before_tool if "graphify" not in str(h)]
    if len(filtered) == len(before_tool):
        return
    settings["hooks"]["BeforeTool"] = filtered
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print("  .gemini/settings.json  ->  BeforeTool hook removed")


def gemini_uninstall(project_dir: Path | None = None) -> None:
    """Remove the graphify section from GEMINI.md, uninstall hook, and remove skill file."""
    # Remove skill file
    skill_dst = Path.home() / ".gemini" / "skills" / "graphify" / "SKILL.md"
    if skill_dst.exists():
        skill_dst.unlink()
        print(f"  skill removed    ->  {skill_dst}")
    version_file = skill_dst.parent / ".graphify_version"
    if version_file.exists():
        version_file.unlink()
    for d in (skill_dst.parent, skill_dst.parent.parent):
        try:
            d.rmdir()
        except OSError:
            break

    target = (project_dir or Path(".")) / "GEMINI.md"
    if not target.exists():
        print("No GEMINI.md found in current directory - nothing to do")
        return
    content = target.read_text(encoding="utf-8")
    if _GEMINI_MD_MARKER not in content:
        print("graphify section not found in GEMINI.md - nothing to do")
        return
    cleaned = re.sub(r"\n*## graphify\n.*?(?=\n## |\Z)", "", content, flags=re.DOTALL).rstrip()
    if cleaned:
        target.write_text(cleaned + "\n", encoding="utf-8")
        print(f"graphify section removed from {target.resolve()}")
    else:
        target.unlink()
        print(f"GEMINI.md was empty after removal - deleted {target.resolve()}")
    _uninstall_gemini_hook(project_dir or Path("."))


_ANTIGRAVITY_RULES_PATH = Path(".agent") / "rules" / "graphify.md"
_ANTIGRAVITY_WORKFLOW_PATH = Path(".agent") / "workflows" / "graphify.md"

_ANTIGRAVITY_RULES = """\
## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
"""

_ANTIGRAVITY_WORKFLOW = """\
# Workflow: graphify
**Command:** /graphify
**Description:** Turn any folder of files into a navigable knowledge graph

## Steps
Follow the graphify skill installed at ~/.agent/skills/graphify/SKILL.md to run the full pipeline.

If no path argument is given, use `.` (current directory).
"""


def _antigravity_install(project_dir: Path) -> None:
    """Install graphify for Google Antigravity: skill + .agent/rules + .agent/workflows."""
    # 1. Copy skill file to ~/.agent/skills/graphify/SKILL.md
    install(platform="antigravity")

    # 2. Write .agent/rules/graphify.md
    rules_path = project_dir / _ANTIGRAVITY_RULES_PATH
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    if rules_path.exists():
        print(f"graphify rule already exists at {rules_path} (no change)")
    else:
        rules_path.write_text(_ANTIGRAVITY_RULES, encoding="utf-8")
        print(f"graphify rule written to {rules_path.resolve()}")

    # 3. Write .agent/workflows/graphify.md
    wf_path = project_dir / _ANTIGRAVITY_WORKFLOW_PATH
    wf_path.parent.mkdir(parents=True, exist_ok=True)
    if wf_path.exists():
        print(f"graphify workflow already exists at {wf_path} (no change)")
    else:
        wf_path.write_text(_ANTIGRAVITY_WORKFLOW, encoding="utf-8")
        print(f"graphify workflow written to {wf_path.resolve()}")

    print()
    print("Antigravity will now check the knowledge graph before answering")
    print("codebase questions. Run /graphify first to build the graph.")


def _antigravity_uninstall(project_dir: Path) -> None:
    """Remove graphify Antigravity rules, workflow, and skill files."""
    # Remove rules file
    rules_path = project_dir / _ANTIGRAVITY_RULES_PATH
    if rules_path.exists():
        rules_path.unlink()
        print(f"graphify rule removed from {rules_path.resolve()}")
    else:
        print("No graphify Antigravity rule found - nothing to do")

    # Remove workflow file
    wf_path = project_dir / _ANTIGRAVITY_WORKFLOW_PATH
    if wf_path.exists():
        wf_path.unlink()
        print(f"graphify workflow removed from {wf_path.resolve()}")

    # Remove skill file
    skill_dst = Path.home() / _PLATFORM_CONFIG["antigravity"]["skill_dst"]
    if skill_dst.exists():
        skill_dst.unlink()
        print(f"graphify skill removed from {skill_dst}")
    version_file = skill_dst.parent / ".graphify_version"
    if version_file.exists():
        version_file.unlink()
    for d in (skill_dst.parent, skill_dst.parent.parent, skill_dst.parent.parent.parent):
        try:
            d.rmdir()
        except OSError:
            break


_CURSOR_RULE_PATH = Path(".cursor") / "rules" / "graphify.mdc"
_CURSOR_RULE = """\
---
description: graphify knowledge graph context
alwaysApply: true
---

This project has a graphify knowledge graph at graphify-out/.

- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
"""


def _cursor_install(project_dir: Path) -> None:
    """Write .cursor/rules/graphify.mdc with alwaysApply: true."""
    rule_path = (project_dir or Path(".")) / _CURSOR_RULE_PATH
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    if rule_path.exists():
        print(f"graphify rule already exists at {rule_path} (no change)")
        return
    rule_path.write_text(_CURSOR_RULE, encoding="utf-8")
    print(f"graphify rule written to {rule_path.resolve()}")
    print()
    print("Cursor will now always include the knowledge graph context.")
    print("Run /graphify . first to build the graph if you haven't already.")


def _cursor_uninstall(project_dir: Path) -> None:
    """Remove .cursor/rules/graphify.mdc."""
    rule_path = (project_dir or Path(".")) / _CURSOR_RULE_PATH
    if not rule_path.exists():
        print("No graphify Cursor rule found - nothing to do")
        return
    rule_path.unlink()
    print(f"graphify Cursor rule removed from {rule_path.resolve()}")


# OpenCode tool.execute.before plugin — fires before every tool call.
# Injects a graph reminder into bash command output when graph.json exists.
_OPENCODE_PLUGIN_JS = """\
// graphify OpenCode plugin
// Injects a knowledge graph reminder before bash tool calls when the graph exists.
import { existsSync } from "fs";
import { join } from "path";

export const GraphifyPlugin = async ({ directory }) => {
  let reminded = false;

  return {
    "tool.execute.before": async (input, output) => {
      if (reminded) return;
      if (!existsSync(join(directory, "graphify-out", "graph.json"))) return;

      if (input.tool === "bash") {
        output.args.command =
          'echo "[graphify] Knowledge graph available. Read graphify-out/GRAPH_REPORT.md for god nodes and architecture context before searching files." && ' +
          output.args.command;
        reminded = true;
      }
    },
  };
};
"""

_OPENCODE_PLUGIN_PATH = Path(".opencode") / "plugins" / "graphify.js"
_OPENCODE_CONFIG_PATH = Path("opencode.json")


def _install_opencode_plugin(project_dir: Path) -> None:
    """Write graphify.js plugin and register it in opencode.json."""
    plugin_file = project_dir / _OPENCODE_PLUGIN_PATH
    plugin_file.parent.mkdir(parents=True, exist_ok=True)
    plugin_file.write_text(_OPENCODE_PLUGIN_JS, encoding="utf-8")
    print(f"  {_OPENCODE_PLUGIN_PATH}  ->  tool.execute.before hook written")

    config_file = project_dir / _OPENCODE_CONFIG_PATH
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}

    plugins = config.setdefault("plugin", [])
    entry = str(_OPENCODE_PLUGIN_PATH)
    if entry not in plugins:
        plugins.append(entry)
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"  {_OPENCODE_CONFIG_PATH}  ->  plugin registered")
    else:
        print(f"  {_OPENCODE_CONFIG_PATH}  ->  plugin already registered (no change)")


def _uninstall_opencode_plugin(project_dir: Path) -> None:
    """Remove graphify.js plugin and deregister from opencode.json."""
    plugin_file = project_dir / _OPENCODE_PLUGIN_PATH
    if plugin_file.exists():
        plugin_file.unlink()
        print(f"  {_OPENCODE_PLUGIN_PATH}  ->  removed")

    config_file = project_dir / _OPENCODE_CONFIG_PATH
    if not config_file.exists():
        return
    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    plugins = config.get("plugin", [])
    entry = str(_OPENCODE_PLUGIN_PATH)
    if entry in plugins:
        plugins.remove(entry)
        if not plugins:
            config.pop("plugin")
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(f"  {_OPENCODE_CONFIG_PATH}  ->  plugin deregistered")


_CODEX_HOOK = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": (
                            "[ -f graphify-out/graph.json ] && "
                            r"""echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files."}}' """
                            "|| true"
                        ),
                    }
                ],
            }
        ]
    }
}


def _install_codex_hook(project_dir: Path) -> None:
    """Add graphify PreToolUse hook to .codex/hooks.json."""
    hooks_path = project_dir / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)

    if hooks_path.exists():
        try:
            existing = json.loads(hooks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}

    pre_tool = existing.setdefault("hooks", {}).setdefault("PreToolUse", [])
    existing["hooks"]["PreToolUse"] = [h for h in pre_tool if "graphify" not in str(h)]
    existing["hooks"]["PreToolUse"].extend(_CODEX_HOOK["hooks"]["PreToolUse"])
    hooks_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"  .codex/hooks.json  ->  PreToolUse hook registered")


def _uninstall_codex_hook(project_dir: Path) -> None:
    """Remove graphify PreToolUse hook from .codex/hooks.json."""
    hooks_path = project_dir / ".codex" / "hooks.json"
    if not hooks_path.exists():
        return
    try:
        existing = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    pre_tool = existing.get("hooks", {}).get("PreToolUse", [])
    filtered = [h for h in pre_tool if "graphify" not in str(h)]
    existing["hooks"]["PreToolUse"] = filtered
    hooks_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"  .codex/hooks.json  ->  PreToolUse hook removed")


def _agents_install(project_dir: Path, platform: str) -> None:
    """Write the graphify section to the local AGENTS.md (Codex/OpenCode/OpenClaw)."""
    target = (project_dir or Path(".")) / "AGENTS.md"

    if target.exists():
        content = target.read_text(encoding="utf-8")
        if _AGENTS_MD_MARKER in content:
            print(f"graphify already configured in AGENTS.md")
        else:
            target.write_text(content.rstrip() + "\n\n" + _AGENTS_MD_SECTION, encoding="utf-8")
            print(f"graphify section written to {target.resolve()}")
    else:
        target.write_text(_AGENTS_MD_SECTION, encoding="utf-8")
        print(f"graphify section written to {target.resolve()}")

    if platform == "codex":
        _install_codex_hook(project_dir or Path("."))
    elif platform == "opencode":
        _install_opencode_plugin(project_dir or Path("."))

    print()
    print(f"{platform.capitalize()} will now check the knowledge graph before answering")
    print("codebase questions and rebuild it after code changes.")
    if platform not in ("codex", "opencode"):
        print()
        print("Note: unlike Claude Code, there is no PreToolUse hook equivalent for")
        print(f"{platform.capitalize()} — the AGENTS.md rules are the always-on mechanism.")


def _agents_uninstall(project_dir: Path) -> None:
    """Remove the graphify section from the local AGENTS.md."""
    target = (project_dir or Path(".")) / "AGENTS.md"

    if not target.exists():
        print("No AGENTS.md found in current directory - nothing to do")
        return

    content = target.read_text(encoding="utf-8")
    if _AGENTS_MD_MARKER not in content:
        print("graphify section not found in AGENTS.md - nothing to do")
        return

    cleaned = re.sub(
        r"\n*## graphify\n.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()
    if cleaned:
        target.write_text(cleaned + "\n", encoding="utf-8")
        print(f"graphify section removed from {target.resolve()}")
    else:
        target.unlink()
        print(f"AGENTS.md was empty after removal - deleted {target.resolve()}")

    _uninstall_opencode_plugin(project_dir or Path("."))


def claude_install(project_dir: Path | None = None) -> None:
    """Write the graphify section to the local CLAUDE.md."""
    target = (project_dir or Path(".")) / "CLAUDE.md"

    if target.exists():
        content = target.read_text(encoding="utf-8")
        if _CLAUDE_MD_MARKER in content:
            print("graphify already configured in CLAUDE.md")
            return
        new_content = content.rstrip() + "\n\n" + _CLAUDE_MD_SECTION
    else:
        new_content = _CLAUDE_MD_SECTION

    target.write_text(new_content, encoding="utf-8")
    print(f"graphify section written to {target.resolve()}")

    # Also write Claude Code PreToolUse hook to .claude/settings.json
    _install_claude_hook(project_dir or Path("."))

    print()
    print("Claude Code will now check the knowledge graph before answering")
    print("codebase questions and rebuild it after code changes.")


def _install_claude_hook(project_dir: Path) -> None:
    """Add graphify PreToolUse hook to .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    hooks = settings.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])

    hooks["PreToolUse"] = [h for h in pre_tool if not (h.get("matcher") == "Glob|Grep" and "graphify" in str(h))]
    hooks["PreToolUse"].append(_SETTINGS_HOOK)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"  .claude/settings.json  ->  PreToolUse hook registered")


def _uninstall_claude_hook(project_dir: Path) -> None:
    """Remove graphify PreToolUse hook from .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    pre_tool = settings.get("hooks", {}).get("PreToolUse", [])
    filtered = [h for h in pre_tool if not (h.get("matcher") == "Glob|Grep" and "graphify" in str(h))]
    if len(filtered) == len(pre_tool):
        return
    settings["hooks"]["PreToolUse"] = filtered
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print(f"  .claude/settings.json  ->  PreToolUse hook removed")


def claude_uninstall(project_dir: Path | None = None) -> None:
    """Remove the graphify section from the local CLAUDE.md."""
    target = (project_dir or Path(".")) / "CLAUDE.md"

    if not target.exists():
        print("No CLAUDE.md found in current directory - nothing to do")
        return

    content = target.read_text(encoding="utf-8")
    if _CLAUDE_MD_MARKER not in content:
        print("graphify section not found in CLAUDE.md - nothing to do")
        return

    # Remove the ## graphify section: from the marker to the next ## heading or EOF
    cleaned = re.sub(
        r"\n*## graphify\n.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()
    if cleaned:
        target.write_text(cleaned + "\n", encoding="utf-8")
        print(f"graphify section removed from {target.resolve()}")
    else:
        target.unlink()
        print(f"CLAUDE.md was empty after removal - deleted {target.resolve()}")

    _uninstall_claude_hook(project_dir or Path("."))


# ---------------------------------------------------------------------------
# Approve CLI helper functions (Phase 07, Plan 03)
# ---------------------------------------------------------------------------

def _list_pending_proposals(out_dir: Path) -> list[dict]:
    """Return all proposals with status 'pending', sorted by timestamp ascending.

    Reads every .json file in out_dir/proposals/. Silently skips corrupt files.
    Returns [] when the proposals directory does not exist.
    """
    proposals_dir = out_dir / "proposals"
    if not proposals_dir.exists():
        return []
    records: list[dict] = []
    for fpath in proposals_dir.glob("*.json"):
        try:
            record = json.loads(fpath.read_text(encoding="utf-8"))
            if record.get("status") == "pending":
                records.append(record)
        except (json.JSONDecodeError, OSError):
            continue
    records.sort(key=lambda r: r.get("timestamp", ""))
    return records


def _reject_proposal(proposals_dir: Path, record_id: str) -> dict:
    """Set status to 'rejected' for the given proposal. Rewrites the file atomically.

    Raises FileNotFoundError if the proposal does not exist.
    Raises ValueError if record_id attempts path traversal.
    """
    # Path confinement: ensure resolved path stays inside proposals_dir
    path = (proposals_dir / f"{record_id}.json").resolve()
    if not str(path).startswith(str(proposals_dir.resolve())):
        raise ValueError(f"Invalid proposal ID: {record_id}")
    if not path.exists():
        raise FileNotFoundError(f"Proposal not found: {record_id}")
    import os as _os
    record = json.loads(path.read_text(encoding="utf-8"))
    record["status"] = "rejected"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        _os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return record


# Indirection helpers so tests can monkeypatch individual calls without
# modifying the internal import machinery of _approve_and_write_proposal.

def _load_profile_for_approve(vault_path: Path) -> dict:
    from graphify.profile import load_profile
    return load_profile(vault_path)


def _validate_vault_path_for_approve(candidate: str, vault_path: Path):
    from graphify.profile import validate_vault_path
    return validate_vault_path(candidate, vault_path)


def _compute_merge_plan_for_approve(vault_path, rendered_notes, profile, **kwargs):
    from graphify.merge import compute_merge_plan
    return compute_merge_plan(vault_path, rendered_notes, profile, **kwargs)


def _apply_merge_plan_for_approve(plan, vault_path, rendered_notes, profile):
    from graphify.merge import apply_merge_plan
    return apply_merge_plan(plan, vault_path, rendered_notes, profile)


def _approve_and_write_proposal(proposals_dir: Path, record_id: str, vault_path: Path) -> dict:
    """Approve a proposal and write it to the vault via the merge engine.

    Raises FileNotFoundError if the proposal does not exist.
    Raises ValueError if record_id attempts path traversal.
    Calls validate_vault_path on the suggested_folder to confine vault writes (T-07-11).
    """
    import os as _os
    # Path confinement: ensure resolved path stays inside proposals_dir
    path = (proposals_dir / f"{record_id}.json").resolve()
    if not str(path).startswith(str(proposals_dir.resolve())):
        raise ValueError(f"Invalid proposal ID: {record_id}")
    if not path.exists():
        raise FileNotFoundError(f"Proposal not found: {record_id}")

    proposal = json.loads(path.read_text(encoding="utf-8"))

    # Path confinement gate (T-07-11): validate suggested_folder before any write
    suggested_folder = proposal.get("suggested_folder", "")
    _validate_vault_path_for_approve(suggested_folder, vault_path)

    # Load vault profile (falls back to built-in default when no .graphify/profile.yaml)
    profile = _load_profile_for_approve(vault_path)

    # Build RenderedNote dict from proposal fields
    from graphify.merge import RenderedNote
    target_rel = Path(suggested_folder) / (proposal["title"] + ".md") if suggested_folder else Path(proposal["title"] + ".md")
    rn: RenderedNote = {
        "node_id": proposal["record_id"],
        "target_path": str(target_rel),
        "frontmatter_fields": {
            "tags": proposal.get("tags", []),
            "note_type": proposal.get("note_type", "note"),
        },
        "body": proposal.get("body_markdown", ""),
    }
    rendered = {proposal["record_id"]: rn}

    # Run through the merge engine
    plan = _compute_merge_plan_for_approve(vault_path, rendered, profile)
    _apply_merge_plan_for_approve(plan, vault_path, rendered, profile)

    # Mark approved and rewrite proposal file
    proposal["status"] = "approved"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8")
        _os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return proposal


def _format_proposal_summary(proposal: dict) -> str:
    """Return a human-readable one-line summary of a proposal for the list view."""
    return (
        f"  {proposal['record_id'][:8]}  "
        f"{proposal.get('title', 'untitled'):40s}  "
        f"{proposal.get('note_type', 'note'):12s}  "
        f"{proposal.get('peer_id', 'anonymous'):12s}  "
        f"{proposal.get('timestamp', ''):25s}"
    )


def main() -> None:
    # Check all known skill install locations for a stale version stamp.
    # Skip during install/uninstall (hook writes trigger a fresh check anyway).
    # Deduplicate paths so platforms sharing the same install dir don't warn twice.
    if not any(arg in ("install", "uninstall") for arg in sys.argv):
        for skill_dst in {Path.home() / cfg["skill_dst"] for cfg in _PLATFORM_CONFIG.values()}:
            _check_skill_version(skill_dst)

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: graphify <command>")
        print()
        print("Commands:")
        print("  install [--platform P]  copy skill to platform config dir (claude|windows|codex|opencode|aider|claw|droid|trae|trae-cn|gemini|cursor|antigravity)")
        print("  query \"<question>\"       BFS traversal of graph.json for a question")
        print("    --dfs                   use depth-first instead of breadth-first")
        print("    --budget N              cap output at N tokens (default 2000)")
        print("    --graph <path>          path to graph.json (default graphify-out/graph.json)")
        print("  save-result             save a Q&A result to graphify-out/memory/ for graph feedback loop")
        print("    --question Q            the question asked")
        print("    --answer A              the answer to save")
        print("    --type T                query type: query|path_query|explain (default: query)")
        print("    --nodes N1 N2 ...       source node labels cited in the answer")
        print("    --memory-dir DIR        memory directory (default: graphify-out/memory)")
        print("  --validate-profile <vault-path>")
        print("                          run four-layer profile preflight against a vault (PROF-05)")
        print("                          \u2014 prints errors/warnings, exits 1 on errors, 0 otherwise")
        print("  --obsidian              export an already-built graphify-out/graph.json to an Obsidian vault (MRG-03)")
        print("    --graph <path>          path to graph.json (default graphify-out/graph.json)")
        print("    --obsidian-dir <path>   output vault directory (default graphify-out/obsidian)")
        print("    --dry-run               print the merge plan via format_merge_plan without writing files")
        print("  snapshot               save current graph.json as a snapshot (DELTA-07)")
        print("    --name <label>         optional label suffix for snapshot filename")
        print("    --cap <N>              max snapshots to retain (default: 10)")
        print("    --graph <path>         path to graph.json (default graphify-out/graph.json)")
        print("    --from <path>          compare FROM this snapshot (for delta generation)")
        print("    --to <path>            compare TO this snapshot (for delta generation)")
        print("    --delta                also generate GRAPH_DELTA.md comparing against previous snapshot")
        print("  benchmark [graph.json]  measure token reduction vs naive full-corpus approach")
        print("  hook install            install post-commit/post-checkout git hooks (all platforms)")
        print("  hook uninstall          remove git hooks")
        print("  hook status             check if git hooks are installed")
        print("  gemini install          write GEMINI.md section + BeforeTool hook (Gemini CLI)")
        print("  gemini uninstall        remove GEMINI.md section + BeforeTool hook")
        print("  cursor install          write .cursor/rules/graphify.mdc (Cursor)")
        print("  cursor uninstall        remove .cursor/rules/graphify.mdc")
        print("  claude install          write graphify section to CLAUDE.md + PreToolUse hook (Claude Code)")
        print("  claude uninstall        remove graphify section from CLAUDE.md + PreToolUse hook")
        print("  codex install           write graphify section to AGENTS.md (Codex)")
        print("  codex uninstall         remove graphify section from AGENTS.md")
        print("  opencode install        write graphify section to AGENTS.md + tool.execute.before plugin (OpenCode)")
        print("  opencode uninstall      remove graphify section from AGENTS.md + plugin")
        print("  aider install           write graphify section to AGENTS.md (Aider)")
        print("  aider uninstall         remove graphify section from AGENTS.md")
        print("  copilot install         copy graphify skill to ~/.copilot/skills (GitHub Copilot CLI)")
        print("  copilot uninstall       remove graphify skill from ~/.copilot/skills")
        print("  claw install            write graphify section to AGENTS.md (OpenClaw)")
        print("  claw uninstall          remove graphify section from AGENTS.md")
        print("  droid install           write graphify section to AGENTS.md (Factory Droid)")
        print("  droid uninstall        remove graphify section from AGENTS.md")
        print("  trae install            write graphify section to AGENTS.md (Trae)")
        print("  trae uninstall         remove graphify section from AGENTS.md")
        print("  trae-cn install         write graphify section to AGENTS.md (Trae CN)")
        print("  trae-cn uninstall      remove graphify section from AGENTS.md")
        print("  antigravity install     write .agent/rules + .agent/workflows + skill (Google Antigravity)")
        print("  antigravity uninstall   remove .agent/rules, .agent/workflows, and skill")
        print()
        return

    cmd = sys.argv[1]

    # --validate-profile <vault-path> (D-78, PROF-05)
    # Thin wrapper over graphify.profile.validate_profile_preflight. Read-only.
    # Never writes. Never runs the extract/build/cluster pipeline.
    if cmd == "--validate-profile":
        if len(sys.argv) < 3:
            print("Usage: graphify --validate-profile <vault-path>", file=sys.stderr)
            sys.exit(2)
        from graphify.profile import validate_profile_preflight
        result = validate_profile_preflight(Path(sys.argv[2]))
        for err in result.errors:
            print(f"error: {err}", file=sys.stderr)
        for warn in result.warnings:
            print(f"warning: {warn}", file=sys.stderr)
        if result.errors:
            sys.exit(1)
        # D-77a literal: "profile ok — N rules, M templates validated"
        print(
            f"profile ok \u2014 {result.rule_count} rules, "
            f"{result.template_count} templates validated"
        )
        sys.exit(0)

    # --obsidian [--graph <path>] [--obsidian-dir <path>] [--dry-run] (D-78, MRG-03, MRG-05)
    # Thin wrapper over graphify.export.to_obsidian. Loads an already-built
    # graph.json from disk (same pattern as the `query` command), reconstructs
    # `communities: dict[int, list[str]]` from node.community attributes, and
    # calls to_obsidian. Never runs extract/build/cluster. The skill is still
    # the pipeline driver for non-standalone use.
    if cmd == "--obsidian":
        graph_path = "graphify-out/graph.json"
        obsidian_dir = "graphify-out/obsidian"
        dry_run = False
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--graph" and i + 1 < len(args):
                graph_path = args[i + 1]; i += 2
            elif args[i].startswith("--graph="):
                graph_path = args[i].split("=", 1)[1]; i += 1
            elif args[i] == "--obsidian-dir" and i + 1 < len(args):
                obsidian_dir = args[i + 1]; i += 2
            elif args[i].startswith("--obsidian-dir="):
                obsidian_dir = args[i].split("=", 1)[1]; i += 1
            elif args[i] == "--dry-run":
                dry_run = True; i += 1
            else:
                print(f"error: unknown --obsidian option: {args[i]}", file=sys.stderr)
                sys.exit(2)

        # Load graph.json — reuse the exact query-command pattern.
        gp = Path(graph_path).resolve()
        if not gp.exists():
            print(f"error: graph file not found: {gp}", file=sys.stderr)
            print("hint: run /graphify to produce graphify-out/graph.json first", file=sys.stderr)
            sys.exit(1)
        if gp.suffix != ".json":
            print("error: graph file must be a .json file", file=sys.stderr)
            sys.exit(1)
        try:
            import json as _json
            from networkx.readwrite import json_graph
            _raw = _json.loads(gp.read_text(encoding="utf-8"))
            try:
                G = json_graph.node_link_graph(_raw, edges="links")
            except TypeError:
                G = json_graph.node_link_graph(_raw)
        except Exception as exc:
            print(f"error: could not load graph: {exc}", file=sys.stderr)
            sys.exit(1)

        # Reconstruct communities dict from node["community"] attribute
        # (written by to_json at graphify/export.py). Nodes with a
        # None community (isolates) are skipped.
        communities: dict[int, list[str]] = {}
        for node_id, data in G.nodes(data=True):
            cid = data.get("community")
            if cid is None:
                continue
            try:
                cid_int = int(cid)
            except (TypeError, ValueError):
                continue
            communities.setdefault(cid_int, []).append(node_id)

        # Call the library — profile discovery happens inside to_obsidian
        # itself (load_profile(out) falls back to _DEFAULT_PROFILE when the
        # vault has no .graphify/profile.yaml). The CLI passes profile=None.
        from graphify.export import to_obsidian
        from graphify.merge import MergePlan, format_merge_plan
        try:
            result = to_obsidian(
                G,
                communities,
                obsidian_dir,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(f"error: to_obsidian failed: {exc}", file=sys.stderr)
            sys.exit(1)

        if isinstance(result, MergePlan):
            # Dry-run path: print the full grouped plan via the Phase 5 D-76 helper
            print(format_merge_plan(result), end="")
        else:
            # Normal run: print a one-line summary from MergeResult.plan.summary
            summary = getattr(getattr(result, "plan", None), "summary", {}) or {}
            total = sum(summary.values()) if summary else 0
            created = summary.get("CREATE", 0)
            updated = summary.get("UPDATE", 0)
            print(
                f"wrote obsidian vault at {Path(obsidian_dir).resolve()} "
                f"\u2014 {total} actions ({created} CREATE, {updated} UPDATE)"
            )
        sys.exit(0)

    if cmd == "snapshot":
        graph_path = "graphify-out/graph.json"
        name = None
        cap = 10
        from_path = None
        to_path = None
        gen_delta = False
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--graph" and i + 1 < len(args):
                graph_path = args[i + 1]; i += 2
            elif args[i].startswith("--graph="):
                graph_path = args[i].split("=", 1)[1]; i += 1
            elif args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]; i += 2
            elif args[i].startswith("--name="):
                name = args[i].split("=", 1)[1]; i += 1
            elif args[i] == "--cap" and i + 1 < len(args):
                cap = int(args[i + 1]); i += 2
                if cap < 1:
                    print("error: --cap must be at least 1", file=sys.stderr)
                    sys.exit(2)
            elif args[i].startswith("--cap="):
                cap = int(args[i].split("=", 1)[1]); i += 1
                if cap < 1:
                    print("error: --cap must be at least 1", file=sys.stderr)
                    sys.exit(2)
            elif args[i] == "--from" and i + 1 < len(args):
                from_path = args[i + 1]; i += 2
            elif args[i].startswith("--from="):
                from_path = args[i].split("=", 1)[1]; i += 1
            elif args[i] == "--to" and i + 1 < len(args):
                to_path = args[i + 1]; i += 2
            elif args[i].startswith("--to="):
                to_path = args[i].split("=", 1)[1]; i += 1
            elif args[i] == "--delta":
                gen_delta = True; i += 1
            else:
                print(f"error: unknown snapshot option: {args[i]}", file=sys.stderr)
                sys.exit(2)

        # Validate --from/--to pairing
        if bool(from_path) != bool(to_path):
            print("error: --from and --to must be specified together", file=sys.stderr)
            sys.exit(2)

        # If --from and --to are specified, compare two snapshots (D-07)
        if from_path and to_path:
            from graphify.snapshot import load_snapshot
            from graphify.delta import compute_delta, render_delta_md
            G_old, comm_old, _ = load_snapshot(Path(from_path))
            G_new, comm_new, _ = load_snapshot(Path(to_path))
            d = compute_delta(G_old, comm_old, G_new, comm_new)
            md = render_delta_md(d, G_new=G_new, communities_new=comm_new)
            # Derive output dir from graph path so it works from any cwd
            graph_root = Path(graph_path).resolve().parent.parent
            out = graph_root / "graphify-out" / "GRAPH_DELTA.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding="utf-8")
            print(f"delta written: {out}")
            return

        # Load graph.json — reuse the exact --obsidian pattern
        gp = Path(graph_path).resolve()
        if not gp.exists():
            print(f"error: graph file not found: {gp}", file=sys.stderr)
            print("hint: run /graphify to produce graphify-out/graph.json first", file=sys.stderr)
            sys.exit(1)
        if gp.suffix != ".json":
            print("error: graph file must be a .json file", file=sys.stderr)
            sys.exit(1)
        try:
            import json as _json
            from networkx.readwrite import json_graph
            _raw = _json.loads(gp.read_text(encoding="utf-8"))
            try:
                G = json_graph.node_link_graph(_raw, edges="links")
            except TypeError:
                G = json_graph.node_link_graph(_raw)
        except Exception as exc:
            print(f"error: could not load graph: {exc}", file=sys.stderr)
            sys.exit(1)

        # Reconstruct communities dict from node["community"] attribute
        communities: dict[int, list[str]] = {}
        for node_id, data in G.nodes(data=True):
            cid = data.get("community")
            if cid is None:
                continue
            try:
                cid_int = int(cid)
            except (TypeError, ValueError):
                continue
            communities.setdefault(cid_int, []).append(node_id)

        from graphify.snapshot import save_snapshot
        saved = save_snapshot(G, communities, name=name, cap=cap)
        print(f"snapshot saved: {saved}")

        if gen_delta:
            from graphify.snapshot import list_snapshots, load_snapshot
            from graphify.delta import compute_delta, render_delta_md
            # Use graph root so paths resolve correctly from any cwd
            graph_root = gp.parent.parent
            snaps = list_snapshots(graph_root)
            if len(snaps) >= 2:
                prev = snaps[-2]  # second-to-last is previous
                G_old, comm_old, _ = load_snapshot(prev)
                d = compute_delta(G_old, comm_old, G, communities)
                md = render_delta_md(d, G_new=G, communities_new=communities)
            else:
                md = render_delta_md({}, first_run=True)
            out = graph_root / "graphify-out" / "GRAPH_DELTA.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding="utf-8")
            print(f"delta written: {out}")
        return

    if cmd == "approve":
        args = sys.argv[2:]
        vault_path = None
        reject = False
        reject_all = False
        approve_all = False
        target_id = None
        out_dir = Path("graphify-out")
        i = 0
        while i < len(args):
            if args[i] == "--vault" and i + 1 < len(args):
                vault_path = Path(args[i + 1]); i += 2
            elif args[i].startswith("--vault="):
                vault_path = Path(args[i].split("=", 1)[1]); i += 1
            elif args[i] == "--reject":
                reject = True; i += 1
            elif args[i] == "--reject-all":
                reject_all = True; i += 1
            elif args[i] == "--all":
                approve_all = True; i += 1
            elif args[i] == "--out-dir" and i + 1 < len(args):
                out_dir = Path(args[i + 1]); i += 2
            elif args[i].startswith("--out-dir="):
                out_dir = Path(args[i].split("=", 1)[1]); i += 1
            elif not args[i].startswith("-"):
                target_id = args[i]; i += 1
            else:
                print(f"error: unknown approve option: {args[i]}", file=sys.stderr)
                sys.exit(2)

        proposals_dir = out_dir / "proposals"

        # No args: list all pending proposals
        if not target_id and not approve_all and not reject_all and not reject:
            proposals = _list_pending_proposals(out_dir)
            if not proposals:
                print("No pending proposals.")
                sys.exit(0)
            print(f"Pending proposals ({len(proposals)}):\n")
            print(f"  {'ID':8s}  {'Title':40s}  {'Type':12s}  {'Peer':12s}  {'Timestamp':25s}")
            _hr = "\u2500"
            print(f"  {_hr*8}  {_hr*40}  {_hr*12}  {_hr*12}  {_hr*25}")
            for p in proposals:
                print(_format_proposal_summary(p))
            print(f"\nApprove: graphify approve <id> --vault <path>")
            print(f"Reject:  graphify approve --reject <id>")
            sys.exit(0)

        # --reject-all: reject all pending
        if reject_all:
            proposals = _list_pending_proposals(out_dir)
            for p in proposals:
                _reject_proposal(proposals_dir, p["record_id"])
                print(f"Rejected: {p['record_id'][:8]} \u2014 {p.get('title', 'untitled')}")
            print(f"\n{len(proposals)} proposal(s) rejected.")
            sys.exit(0)

        # --reject <id>: reject single
        if reject and target_id:
            try:
                r = _reject_proposal(proposals_dir, target_id)
                print(f"Rejected: {r['record_id'][:8]} \u2014 {r.get('title', 'untitled')}")
            except FileNotFoundError as exc:
                print(f"error: {exc}", file=sys.stderr)
                sys.exit(1)
            sys.exit(0)

        if reject and not target_id:
            print("error: --reject requires a proposal ID", file=sys.stderr)
            sys.exit(2)

        # --all --vault <path>: batch approve
        if approve_all:
            if not vault_path:
                print("error: --vault is required for approve operations", file=sys.stderr)
                sys.exit(2)
            proposals = _list_pending_proposals(out_dir)
            if not proposals:
                print("No pending proposals to approve.")
                sys.exit(0)
            for p in proposals:
                try:
                    _approve_and_write_proposal(proposals_dir, p["record_id"], vault_path)
                    print(f"Approved: {p['record_id'][:8]} \u2014 {p.get('title', 'untitled')}")
                except Exception as exc:
                    print(f"error approving {p['record_id'][:8]}: {exc}", file=sys.stderr)
            sys.exit(0)

        # <id> --vault <path>: approve single
        if target_id:
            if not vault_path:
                print("error: --vault is required for approve operations", file=sys.stderr)
                sys.exit(2)
            try:
                r = _approve_and_write_proposal(proposals_dir, target_id, vault_path)
                print(f"Approved: {r['record_id'][:8]} \u2014 {r.get('title', 'untitled')}")
            except FileNotFoundError as exc:
                print(f"error: {exc}", file=sys.stderr)
                sys.exit(1)
            except Exception as exc:
                print(f"error: {exc}", file=sys.stderr)
                sys.exit(1)
            sys.exit(0)

    if cmd == "install":
        # Default to windows platform on Windows, claude elsewhere
        default_platform = "windows" if platform.system() == "Windows" else "claude"
        chosen_platform = default_platform
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i].startswith("--platform="):
                chosen_platform = args[i].split("=", 1)[1]
                i += 1
            elif args[i] == "--platform" and i + 1 < len(args):
                chosen_platform = args[i + 1]
                i += 2
            else:
                i += 1
        install(platform=chosen_platform)
    elif cmd == "claude":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            claude_install()
        elif subcmd == "uninstall":
            claude_uninstall()
        else:
            print("Usage: graphify claude [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "gemini":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            gemini_install()
        elif subcmd == "uninstall":
            gemini_uninstall()
        else:
            print("Usage: graphify gemini [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "cursor":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            _cursor_install(Path("."))
        elif subcmd == "uninstall":
            _cursor_uninstall(Path("."))
        else:
            print("Usage: graphify cursor [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "copilot":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            install(platform="copilot")
        elif subcmd == "uninstall":
            skill_dst = Path.home() / _PLATFORM_CONFIG["copilot"]["skill_dst"]
            removed = []
            if skill_dst.exists():
                skill_dst.unlink()
                removed.append(f"skill removed: {skill_dst}")
            version_file = skill_dst.parent / ".graphify_version"
            if version_file.exists():
                version_file.unlink()
            for d in (skill_dst.parent, skill_dst.parent.parent, skill_dst.parent.parent.parent):
                try:
                    d.rmdir()
                except OSError:
                    break
            print("; ".join(removed) if removed else "nothing to remove")
        else:
            print("Usage: graphify copilot [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd in ("aider", "codex", "opencode", "claw", "droid", "trae", "trae-cn"):
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            _agents_install(Path("."), cmd)
        elif subcmd == "uninstall":
            _agents_uninstall(Path("."))
            if cmd == "codex":
                _uninstall_codex_hook(Path("."))
        else:
            print(f"Usage: graphify {cmd} [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "antigravity":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            _antigravity_install(Path("."))
        elif subcmd == "uninstall":
            _antigravity_uninstall(Path("."))
        else:
            print("Usage: graphify antigravity [install|uninstall]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "hook":
        from graphify.hooks import install as hook_install, uninstall as hook_uninstall, status as hook_status
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "install":
            print(hook_install(Path(".")))
        elif subcmd == "uninstall":
            print(hook_uninstall(Path(".")))
        elif subcmd == "status":
            print(hook_status(Path(".")))
        else:
            print("Usage: graphify hook [install|uninstall|status]", file=sys.stderr)
            sys.exit(1)
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Usage: graphify query \"<question>\" [--dfs] [--budget N] [--graph path]", file=sys.stderr)
            sys.exit(1)
        from graphify.serve import _score_nodes, _bfs, _dfs, _subgraph_to_text
        from graphify.security import sanitize_label
        from networkx.readwrite import json_graph
        question = sys.argv[2]
        use_dfs = "--dfs" in sys.argv
        budget = 2000
        graph_path = "graphify-out/graph.json"
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--budget" and i + 1 < len(args):
                try:
                    budget = int(args[i + 1])
                except ValueError:
                    print(f"error: --budget must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 2
            elif args[i].startswith("--budget="):
                try:
                    budget = int(args[i].split("=", 1)[1])
                except ValueError:
                    print(f"error: --budget must be an integer", file=sys.stderr)
                    sys.exit(1)
                i += 1
            elif args[i] == "--graph" and i + 1 < len(args):
                graph_path = args[i + 1]; i += 2
            else:
                i += 1
        # Load graph directly — validate_graph_path restricts to graphify-out/
        # so for custom --graph paths we resolve and load directly after existence check
        gp = Path(graph_path).resolve()
        if not gp.exists():
            print(f"error: graph file not found: {gp}", file=sys.stderr)
            sys.exit(1)
        if not gp.suffix == ".json":
            print(f"error: graph file must be a .json file", file=sys.stderr)
            sys.exit(1)
        try:
            import json as _json
            import networkx as _nx
            _raw = _json.loads(gp.read_text(encoding="utf-8"))
            try:
                G = json_graph.node_link_graph(_raw, edges="links")
            except TypeError:
                G = json_graph.node_link_graph(_raw)
        except Exception as exc:
            print(f"error: could not load graph: {exc}", file=sys.stderr)
            sys.exit(1)
        terms = [t.lower() for t in question.split() if len(t) > 2]
        scored = _score_nodes(G, terms)
        if not scored:
            print("No matching nodes found.")
            sys.exit(0)
        start = [nid for _, nid in scored[:5]]
        nodes, edges = (_dfs if use_dfs else _bfs)(G, start, depth=2)
        print(_subgraph_to_text(G, nodes, edges, token_budget=budget))
    elif cmd == "save-result":
        # graphify save-result --question Q --answer A --type T [--nodes N1 N2 ...]
        import argparse as _ap
        p = _ap.ArgumentParser(prog="graphify save-result")
        p.add_argument("--question", required=True)
        p.add_argument("--answer", required=True)
        p.add_argument("--type", dest="query_type", default="query")
        p.add_argument("--nodes", nargs="*", default=[])
        p.add_argument("--memory-dir", default="graphify-out/memory")
        opts = p.parse_args(sys.argv[2:])
        from graphify.ingest import save_query_result as _sqr
        out = _sqr(
            question=opts.question,
            answer=opts.answer,
            memory_dir=Path(opts.memory_dir),
            query_type=opts.query_type,
            source_nodes=opts.nodes or None,
        )
        print(f"Saved to {out}")
    elif cmd == "benchmark":
        from graphify.benchmark import run_benchmark, print_benchmark
        graph_path = sys.argv[2] if len(sys.argv) > 2 else "graphify-out/graph.json"
        # Try to load corpus_words from detect output
        corpus_words = None
        detect_path = Path(".graphify_detect.json")
        if detect_path.exists():
            try:
                detect_data = json.loads(detect_path.read_text(encoding="utf-8"))
                corpus_words = detect_data.get("total_words")
            except Exception:
                pass
        result = run_benchmark(graph_path, corpus_words=corpus_words)
        print_benchmark(result)
    else:
        print(f"error: unknown command '{cmd}'", file=sys.stderr)
        print("Run 'graphify --help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
