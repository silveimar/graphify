"""Tests for graphify slash-command prompt files — existence, frontmatter, MCP tool references."""
from __future__ import annotations
from pathlib import Path
import re

import graphify


CORE_COMMANDS = {
    "context": "graph_summary",
    "trace": "entity_trace",
    "connect": "connect_topics",
    "drift": "drift_nodes",
    "emerge": "newly_formed_clusters",
}

SNAPSHOT_COMMANDS = {"trace", "drift", "emerge"}
PARAMETERIZED_COMMANDS = {"trace", "connect"}


def _commands_dir() -> Path:
    return Path(graphify.__file__).parent / "commands"


def _read(name: str) -> str:
    return (_commands_dir() / f"{name}.md").read_text(encoding="utf-8")


def _registered_tool_names() -> set[str]:
    """Regex-extract every types.Tool(name="...") from MCP registry source.

    Tools live in graphify/mcp_tool_registry.py (Phase 13); serve.py imports
    build_mcp_tools(). Regex over source is sufficient for a drift detector.
    """
    reg_src = (Path(graphify.__file__).parent / "mcp_tool_registry.py").read_text(encoding="utf-8")
    return set(re.findall(r'types\.Tool\s*\(\s*name="([^"]+)"', reg_src))


def test_command_files_exist_in_package():
    for name in CORE_COMMANDS:
        assert (_commands_dir() / f"{name}.md").exists(), f"Missing commands/{name}.md"


def test_command_files_have_required_frontmatter():
    for name in CORE_COMMANDS:
        text = _read(name)
        assert text.startswith("---\n"), f"{name}.md missing YAML frontmatter opener"
        for field in (f"name: {name}", "description:", "argument-hint:", "disable-model-invocation: true"):
            assert field in text, f"{name}.md missing {field!r} in frontmatter"


def test_command_files_reference_correct_mcp_tool():
    for name, tool in CORE_COMMANDS.items():
        text = _read(name)
        assert tool in text, f"{name}.md does not reference MCP tool {tool!r}"


def test_command_files_have_no_graph_guard():
    for name in CORE_COMMANDS:
        text = _read(name)
        assert "no_graph" in text, f"{name}.md missing no_graph guard"


def test_snapshot_commands_have_insufficient_history_guard():
    for name in SNAPSHOT_COMMANDS:
        text = _read(name)
        assert "insufficient_history" in text, f"{name}.md missing insufficient_history guard"


def test_trace_md_has_ambiguous_and_not_found_guards():
    text = _read("trace")
    assert "ambiguous_entity" in text
    assert "entity_not_found" in text


def test_connect_md_has_distinct_sections():
    text = _read("connect")
    assert "Shortest path" in text, "connect.md must contain 'Shortest path' section header"
    assert "Surprising bridges" in text, "connect.md must contain 'Surprising bridges' section header"


def test_connect_md_does_not_conflate_sections():
    text = _read("connect")
    idx_path = text.find("Shortest path")
    idx_bridges = text.find("Surprising bridges")
    assert idx_path != -1 and idx_bridges != -1
    assert idx_path < idx_bridges, "Shortest path section must come before Surprising bridges — must not be conflated (Pitfall 4)"


def test_parameterized_commands_reference_arguments():
    for name in PARAMETERIZED_COMMANDS:
        text = _read(name)
        assert "$ARGUMENTS" in text, f"{name}.md missing $ARGUMENTS placeholder"


def test_command_files_reference_registered_tools():
    """Every tool name used by a command file must be registered in the MCP registry.

    Plan-checker WARNING 3: detects tool-name drift. If serve.py renames
    `graph_summary` to `graph_digest` but context.md still says `graph_summary`,
    the command silently breaks at runtime. This test catches it at test time.
    """
    registered = _registered_tool_names()
    referenced = set(CORE_COMMANDS.values())
    missing = referenced - registered
    assert not missing, (
        f"Command files reference tools not registered in mcp_tool_registry.py: {sorted(missing)}. "
        f"Registered tools: {sorted(registered)}"
    )


# ---------------------------------------------------------------------------
# Stretch command tests (plan 11-07 — SLASH-06 /ghost and SLASH-07 /challenge)
# ---------------------------------------------------------------------------

STRETCH_COMMANDS = {
    "ghost": "get_annotations",
    "challenge": "query_graph",
}


def test_stretch_command_files_exist():
    for name in STRETCH_COMMANDS:
        assert (_commands_dir() / f"{name}.md").exists(), f"Missing commands/{name}.md"


def test_stretch_command_files_have_required_frontmatter():
    for name in STRETCH_COMMANDS:
        text = _read(name)
        assert text.startswith("---\n"), f"{name}.md missing YAML frontmatter opener"
        for field in (f"name: {name}", "description:", "argument-hint:", "disable-model-invocation: true"):
            assert field in text, f"{name}.md missing {field!r}"


def test_stretch_command_files_have_no_graph_guard():
    # challenge.md uses query_graph which returns a meta envelope with meta.status,
    # so its no_graph guard is valid and must be present.
    # ghost.md uses get_annotations (JSON array) and god_nodes (plain text) — neither
    # returns a meta envelope, so its guard is based on empty-array/empty-list detection,
    # not meta.status. ghost is excluded from this check; see test_ghost_md_guard_wording.
    for name in ("challenge",):
        assert "no_graph" in _read(name), f"{name}.md missing no_graph guard"


def test_ghost_md_guard_wording():
    """WR-02 regression: ghost.md must NOT instruct parsing meta.status (dead guard).

    get_annotations returns a JSON array and god_nodes returns plain text — neither
    returns a Phase 9.2 meta envelope. The guard must check for empty array/list instead.
    """
    text = _read("ghost")
    assert "JSON array" in text, "ghost.md must describe get_annotations as returning a JSON array"
    assert "empty array" in text or "empty list" in text, (
        "ghost.md must guard on empty array/list, not meta.status"
    )
    assert "meta.status" not in text, (
        "ghost.md must NOT reference meta.status — neither get_annotations nor god_nodes "
        "returns a meta envelope"
    )


def test_ghost_md_references_get_annotations():
    assert "get_annotations" in _read("ghost")


def test_challenge_md_has_evidence_sections():
    text = _read("challenge")
    idx_support = text.find("Evidence supporting")
    idx_contra = text.find("Evidence contradicting")
    assert idx_support != -1 and idx_contra != -1
    assert idx_support < idx_contra, "Evidence supporting must come before Evidence contradicting"


def test_challenge_md_has_anti_fabrication_guard():
    assert "do NOT fabricate" in _read("challenge"), "challenge.md must include anti-fabrication guard"


# ============================================================
# Phase 17 CHAT-06 — /graphify-ask slash command
# ============================================================

def _parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, f"{path} missing YAML frontmatter"
    block = m.group(1)
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def test_ask_md_frontmatter():
    """CHAT-06: /graphify-ask command file exists with connect.md-style frontmatter."""
    path = _commands_dir() / "ask.md"
    assert path.exists(), "graphify/commands/ask.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-ask"
    assert fm.get("description"), "description field required"
    assert fm.get("argument-hint"), "argument-hint field required"
    assert fm.get("disable-model-invocation") == "true"
    # Phase 14 Plan 01 backfill: legacy files now carry `target: both`
    assert fm.get("target") == "both", "ask.md must have target: both (Plan 14-01 backfill)"
    # Body must reference the chat MCP tool
    body = path.read_text()
    assert "chat" in body, "ask.md body must invoke the chat MCP tool"
    assert "$ARGUMENTS" in body, "ask.md must pass $ARGUMENTS to query"


def test_argue_md_frontmatter():
    """ARGUE-10: /graphify-argue command file exists with ask.md-style frontmatter."""
    path = _commands_dir() / "argue.md"
    assert path.exists(), "graphify/commands/argue.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-argue"
    assert fm.get("description"), "description field required"
    assert fm.get("argument-hint"), "argument-hint field required"
    assert fm.get("disable-model-invocation") == "true"
    assert fm.get("target") == "both", "argue.md must have target: both (Plan 14-01 backfill)"
    body = path.read_text()
    assert "argue_topic" in body, "argue.md body must invoke the argue_topic MCP tool"
    assert "$ARGUMENTS" in body, "argue.md must pass $ARGUMENTS to topic"
    # Pitfall 4 guard — the canonical meta key is resolved_from_alias, NOT alias_redirects.
    assert "alias_redirects" not in body, "argue.md must use resolved_from_alias, never alias_redirects"
    # ARGUE-09 advisory-only enforcement — body must state non-mutation invariant.
    assert "advisory" in body.lower(), "argue.md must document advisory-only invariant (ARGUE-09)"


# ============================================================
# Phase 14 Plan 01 — OBSCMD-02 (target filter) + OBSCMD-07 (prefix enforcement)
# ============================================================

LEGACY_COMMANDS = (
    "argue", "ask", "challenge", "connect", "context",
    "drift", "emerge", "ghost", "trace",
)


def test_legacy_commands_have_target():
    """Plan 01 backfill: all 9 pre-Phase-14 commands carry target: both."""
    for name in LEGACY_COMMANDS:
        fm = _parse_frontmatter(_commands_dir() / f"{name}.md")
        assert fm.get("target") == "both", f"{name}.md missing target: both"


def test_graphify_prefix_enforced():
    """OBSCMD-07: every command name is either /graphify-* or in the legacy allow-list."""
    LEGACY_ALLOW = set(LEGACY_COMMANDS)
    for path in sorted(_commands_dir().glob("*.md")):
        fm = _parse_frontmatter(path)
        name = fm.get("name", path.stem)
        stem = path.stem
        if stem in LEGACY_ALLOW:
            continue
        assert name.startswith("graphify-"), (
            f"{path.name}: new commands must start with 'graphify-' (OBSCMD-07)"
        )


# ============================================================
# Phase 14 Plan 02 — OBSCMD-03 (/graphify-moc) + OBSCMD-08 (trust boundary) + TM-14-01
# ============================================================


def test_graphify_moc_frontmatter():
    """OBSCMD-03: /graphify-moc command file exists with vault-target frontmatter."""
    path = _commands_dir() / "graphify-moc.md"
    assert path.exists(), "graphify/commands/graphify-moc.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-moc"
    assert fm.get("description"), "description required"
    assert fm.get("argument-hint"), "argument-hint required"
    assert fm.get("disable-model-invocation") == "true"
    assert fm.get("target") == "obsidian", "graphify-moc must declare target: obsidian"


def test_moc_trust_boundary_and_contract():
    """OBSCMD-03 + OBSCMD-08 + TM-14-01: body invokes correct MCP tools AND routes writes through propose_vault_note."""
    import re as _re
    path = _commands_dir() / "graphify-moc.md"
    body = path.read_text()
    assert "get_community" in body, "body must invoke get_community MCP tool"
    assert "load_profile" in body, "body must call load_profile for profile-first + fallback (D-03)"
    assert "propose_vault_note" in body, "OBSCMD-08: all vault writes via propose_vault_note"
    assert "$ARGUMENTS" in body, "must accept <community_id> as $ARGUMENTS"
    for forbidden in [r"Path\.write_text", r"write_note_directly", r"open\([^)]*['\"]w['\"]"]:
        assert not _re.search(forbidden, body), (
            f"TM-14-01: graphify-moc.md must not call direct-write pattern {forbidden!r}"
        )


def test_related_contract():
    """OBSCMD-04: /graphify-related exists with correct frontmatter and tool dispatch."""
    path = _commands_dir() / "graphify-related.md"
    assert path.exists()
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-related"
    assert fm.get("target") == "obsidian"
    assert fm.get("argument-hint"), "argument-hint required"
    assert fm.get("disable-model-invocation") == "true"
    body = path.read_text()
    assert "$ARGUMENTS" in body, "must accept <note-path> as $ARGUMENTS"
    assert "get_focus_context" in body, "body must invoke get_focus_context"
    assert "source_file" in body, "body must read source_file from note frontmatter (D-02)"


def test_related_handles_no_context():
    """OBSCMD-04 + TM-14-03: /graphify-related explicitly handles status == no_context
    (spoof-silent invariant from Phase 18 SC2 / CR-01)."""
    path = _commands_dir() / "graphify-related.md"
    body = path.read_text()
    assert "no_context" in body, (
        "body must explicitly branch on status == no_context so spoofed/outside-project "
        "source_file values produce a user-visible explanation, not silence"
    )


# ============================================================
# Phase 14 Plan 04 — OBSCMD-05 (/graphify-orphan) + D-05 dual-section render
# ============================================================


def test_orphan_dual_sections():
    """OBSCMD-05 / D-05: /graphify-orphan emits two distinct labeled sections."""
    path = _commands_dir() / "graphify-orphan.md"
    assert path.exists()
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-orphan"
    assert fm.get("target") == "obsidian"
    body = path.read_text()
    assert "## Isolated Nodes" in body, "must have '## Isolated Nodes' section"
    assert "## Stale/Ghost Nodes" in body, "must have '## Stale/Ghost Nodes' section"
    # Isolated section must precede Stale section (remediation ordering)
    idx_iso = body.find("## Isolated Nodes")
    idx_stale = body.find("## Stale/Ghost Nodes")
    assert idx_iso < idx_stale, "Isolated Nodes must render before Stale/Ghost"


def test_orphan_graceful_without_enrichment():
    """OBSCMD-05: graceful degrade when enrichment.json absent (Phase 15 optional)."""
    path = _commands_dir() / "graphify-orphan.md"
    body = path.read_text()
    # Must reference enrichment.json absence + remediation
    assert "enrichment.json" in body, "body must mention enrichment.json file name"
    assert "graphify enrich" in body, "body must instruct user to run `graphify enrich`"
    # Must not imply absence is an error — we want a banner, not a stop.
    # Heuristic: look for a banner/notice phrase tied to absence handling.
    assert ("unavailable" in body.lower() or "not yet" in body.lower()
            or "no enrichment" in body.lower()), (
        "body must render a graceful banner when enrichment.json is missing"
    )
