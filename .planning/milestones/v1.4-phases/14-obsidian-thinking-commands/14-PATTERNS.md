# Phase 14: Obsidian Thinking Commands — Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 8 (3 Python edit targets, 4 new `.md` commands, 9 existing `.md` to backfill, 2 test files)
**Analogs found:** 8 / 8 (all with exact or role-match analogs in-repo)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/__main__.py` (`_uninstall_commands` refactor) | installer / CLI | file-I/O (directory-scan) | `graphify/__main__.py:141-154` (`_install_commands`) | exact (symmetric pair) |
| `graphify/__main__.py` (`_install_commands` frontmatter filter) | installer / CLI | file-I/O + parse | `graphify/__main__.py:141-154` (self, same fn) + `graphify/profile.py:128-158` (load_profile) | exact |
| `graphify/__main__.py` (`_PLATFORM_CONFIG` extension) | config dict | static config | `graphify/__main__.py:49-128` (current entries) | exact |
| `graphify/__main__.py` (`--no-obsidian-commands` CLI flag) | CLI arg parse | argv scan | `graphify/__main__.py:1674-1677` (existing `--no-commands` flag) | exact |
| `graphify/commands/graphify-moc.md` (NEW) | skill orchestration | event-driven (slash cmd → MCP) | `graphify/commands/argue.md` (Phase 16) + `graphify/commands/ask.md` (Phase 17) | exact (D-02 envelope) |
| `graphify/commands/graphify-related.md` (NEW) | skill orchestration | event-driven | `graphify/commands/ask.md` (single-arg, $ARGUMENTS → MCP) | exact |
| `graphify/commands/graphify-orphan.md` (NEW) | skill orchestration | request-response, dual-section | `graphify/commands/connect.md` (dual-section render) | role-match |
| `graphify/commands/graphify-wayfind.md` (NEW) | skill orchestration | event-driven | `graphify/commands/connect.md` (connect_topics shortest-path) | exact |
| `graphify/commands/{argue,ask,challenge,connect,context,drift,emerge,ghost,trace}.md` (MODIFY) | skill orchestration | n/a (frontmatter backfill only) | self | trivial edit |
| `tests/test_commands.py` (MODIFY) | test | file-read + regex | `tests/test_commands.py:195-230` (`test_ask_md_frontmatter`, `test_argue_md_frontmatter`) | exact |
| `tests/test_install.py` (MODIFY) | test | filesystem mock | `tests/test_install.py:19-66` (existing `_install(tmp_path, platform)` harness) | exact |

## Pattern Assignments

### `graphify/__main__.py` — `_uninstall_commands` directory-scan refactor (Plan 00, OBSCMD-01)

**Analog:** `graphify/__main__.py:141-154` — the sibling `_install_commands` function. It already uses the directory-scan idiom that `_uninstall_commands` must mirror.

**Current broken pattern (to replace, lines 157-172):**
```python
def _uninstall_commands(cfg: dict, *, verbose: bool = True) -> None:
    """Remove command files previously installed by _install_commands."""
    if not cfg.get("commands_enabled"):
        return
    dst_rel = cfg.get("commands_dst")
    if dst_rel is None:
        return
    dst_dir = Path.home() / dst_rel
    if not dst_dir.exists():
        return
    # Remove only the files we know Phase 11 installs (core 5 + stretch placeholders)
    for name in ("context.md", "trace.md", "connect.md", "drift.md", "emerge.md", "ghost.md", "challenge.md"):
        target = dst_dir / name
        if target.exists():
            target.unlink()
            if verbose:
                print(f"  command removed    ->  {target}")
```

**Copy-from pattern (install side, lines 141-154):**
```python
def _install_commands(cfg: dict, src_dir: Path, *, verbose: bool = True) -> None:
    """Copy all command .md files from src_dir to cfg['commands_dst'] under Path.home()."""
    if not cfg.get("commands_enabled"):
        return
    dst_rel = cfg.get("commands_dst")
    if dst_rel is None:
        return
    dst_dir = Path.home() / dst_rel
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_dir.glob("*.md")):
        dst = dst_dir / src.name
        shutil.copy(src, dst)
        if verbose:
            print(f"  command installed  ->  {dst}")
```

**Adaptation:** The refactored `_uninstall_commands` must accept (or recompute) `src_dir = Path(__file__).parent / cfg["commands_src_dir"]`, iterate `sorted(src_dir.glob("*.md"))`, and unlink `dst_dir / src.name` with `missing_ok=True` (or `.exists()` guard). The existing call site at line 247 (`_uninstall_commands(cfg)`) will need a second arg or an internal recompute — planner's choice.

---

### `graphify/__main__.py` — `_install_commands` frontmatter filter (Plan 01, OBSCMD-02)

**Analog 1 (structural):** same function, lines 141-154 (shown above). Add frontmatter parse + `supports` check inside the `for src in sorted(...)` loop.

**Analog 2 (stdlib regex precedent, no PyYAML):** `tests/test_commands.py:195-212` shows the existing `_parse_frontmatter` helper pattern that reads a single `target:`-style key via line split. The same idiom, scoped to regex, belongs in `__main__.py`.

**Copy-from pattern (RESEARCH.md §"Pattern 3", already validated against 9 existing commands):**
```python
import re
_TARGET_RE = re.compile(r"^target:\s*(obsidian|code|both)\s*$", re.MULTILINE)

def _read_command_target(src: Path) -> str:
    """Parse `target:` from command frontmatter. Returns 'both' if absent (backward-compat)."""
    try:
        head = src.read_text(encoding="utf-8", errors="replace")[:1024]
    except OSError:
        return "both"
    m = _TARGET_RE.search(head)
    return m.group(1) if m else "both"
```

**Integration into `_install_commands` loop:**
```python
supports = set(cfg.get("supports", ["code", "obsidian"]))  # default: install all
for src in sorted(src_dir.glob("*.md")):
    target = _read_command_target(src)
    if target != "both" and target not in supports:
        continue  # skip files whose target is not supported by this platform
    dst = dst_dir / src.name
    shutil.copy(src, dst)
    if verbose:
        print(f"  command installed  ->  {dst} (target={target})")
```

**Double-default invariant (Pitfall 1 mitigation):** parser defaults to `"both"` when `target:` is absent AND Plan 01 backfills `target: both` in all 9 existing command files. The 9-file backfill is a pure YAML-block edit — insert `target: both` as the last field before the closing `---`.

---

### `graphify/__main__.py` — `_PLATFORM_CONFIG` extension (Plan 01, OBSCMD-02)

**Analog:** `graphify/__main__.py:49-128` — the dict itself. Every entry is a shallow dict; adding a `"supports"` key is additive and safe.

**Current entry shape (lines 50-57, `claude` platform):**
```python
"claude": {
    "skill_file": "skill.md",
    "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
    "claude_md": True,
    "commands_src_dir": "commands",
    "commands_dst": Path(".claude") / "commands",
    "commands_enabled": True,
},
```

**Adapted entry with `supports` (Plan 01 target):**
```python
"claude": {
    "skill_file": "skill.md",
    "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
    "claude_md": True,
    "commands_src_dir": "commands",
    "commands_dst": Path(".claude") / "commands",
    "commands_enabled": True,
    "supports": ["code", "obsidian"],   # Claude Code supports both
},
```

**Per-platform supports assignment (planner's judgment — D-04):**
- `claude`, `windows`: `["code", "obsidian"]` (Claude Code user may have Obsidian vault)
- `codex`, `opencode`, `aider`, `copilot`, `claw`, `droid`, `trae`, `trae-cn`, `antigravity`: all have `"commands_enabled": False`, so `supports` is moot. Safe default: `["code"]` for future-proofing.

---

### `graphify/__main__.py` — `--no-obsidian-commands` CLI flag (Plan 01, OBSCMD-02)

**Analog:** `graphify/__main__.py:1674-1677` — the exact precedent for `--no-commands`.

**Copy-from pattern (lines 1673-1689):**
```python
# --no-commands flag: skip command file installation
no_commands = "--no-commands" in sys.argv
if no_commands:
    sys.argv.remove("--no-commands")
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
install(platform=chosen_platform, no_commands=no_commands)
```

**Adaptation:** add a sibling `no_obsidian_commands = "--no-obsidian-commands" in sys.argv` scan-and-remove block. Thread it into `install(..., no_obsidian_commands=no_obsidian_commands)`. Inside `install()`, if `no_obsidian_commands`, mutate `cfg["supports"]` to drop `"obsidian"` before calling `_install_commands`.

---

### `graphify/commands/graphify-moc.md` — NEW (Plan 02, OBSCMD-03)

**Analog:** `graphify/commands/argue.md` — closest shape (single $ARGUMENTS, D-02 envelope parse, multi-step skill orchestration ending in a persisted artifact).

**Copy-from pattern (full `argue.md`, 24 lines):**
```markdown
---
name: graphify-argue
description: Run a structurally-enforced multi-perspective graph debate on a decision question, grounded in the knowledge graph.
argument-hint: <decision question>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `argue_topic` with:
- `topic`: "$ARGUMENTS"
- `scope`: "topic"

The response is a D-02 envelope: a short text body, then `---GRAPHIFY-META---`, then a JSON object.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim — "No graph loaded. Run `/graphify` first to build a knowledge graph, then retry `/graphify-argue`."

**If `status` is `no_results`:** render — "The question didn't match any nodes in the graph. Try rephrasing with terms that appear in the codebase, or widen scope with the `argue_topic` tool."

**If `status` is `ok`:**
[... multi-step orchestration ...]
```

**Adaptation for `graphify-moc`:** swap MCP tool to `get_community(community_id=int($ARGUMENTS))`; add `target: obsidian` to frontmatter; skill body directs LLM to `load_profile(vault_path)` → render MOC using `profile.obsidian.dataview.moc_query` → call `propose_vault_note(title, body_markdown, suggested_folder=profile.folder_mapping.moc, note_type="moc")`. Research doc §"Pattern 1" has the full example template at lines 200-233 — copy verbatim and substitute.

**Trust-boundary suffix (D-06, OBSCMD-08) — every write command ends with:**
> Tell the user the proposal ID and instruct them to run `graphify approve <id>` — do NOT write to the vault yourself.

---

### `graphify/commands/graphify-related.md` — NEW (Plan 03, OBSCMD-04)

**Analog:** `graphify/commands/ask.md` — closest shape (single $ARGUMENTS, D-02 envelope, single MCP call, status-branched render).

**Copy-from pattern (full `ask.md`, 29 lines):**
```markdown
---
name: graphify-ask
description: Ask a natural-language question about the codebase and receive a graph-grounded narrative answer with citations.
argument-hint: <question>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Call the graphify MCP tool `chat` with:
- `query`: "$ARGUMENTS"

The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `no_results`:** render the fuzzy suggestions from `meta.suggestions` as "Did you mean: A, B, C?".

**If `status` is `ok`:** render `text_body` verbatim (it is already token-capped and cited). Do NOT re-summarize.
```

**Adaptation for `graphify-related`:** frontmatter gains `target: obsidian`, `argument-hint: <note-path>`. Two-step skill: (1) read YAML frontmatter of `$ARGUMENTS` note → extract `source_file`, (2) call `get_focus_context(focus_hint={"file_path": source_file})`. Status branches include `no_context` (Pitfall 5): render "The note path doesn't match any file in the graph. Check that the note's `source_file` frontmatter field points to a file inside the project root."

---

### `graphify/commands/graphify-orphan.md` — NEW (Plan 04, OBSCMD-05)

**Analog:** `graphify/commands/connect.md:28-38` — the dual-section render pattern.

**Copy-from pattern (connect.md lines 28-40):**
```markdown
**If `status` is `ok`:** render TWO DISTINCT SECTIONS. Do NOT merge them. Do NOT present the surprising bridges as "the path between A and B" — they are globally surprising cross-community edges, not an alternative path.

    ## Shortest path (N hops)
    [Render the path from the tool's text_body's "Shortest Path" section — a chain of labels.]

    ## Surprising bridges in the graph
    [Render the tool's "Surprising Bridges" section separately — these are globally surprising edges in the full graph, relevant context but not the path between the two topics.]
```

**Adaptation:** two sections become `## Isolated Nodes` (from `graph.json` nodes where `community in {None, -1, <missing>}`) and `## Stale/Ghost Nodes` (from `enrichment.json` where `staleness == "GHOST"`). Graceful absence of `enrichment.json` (Pitfall 2): emit section A only + banner `_Ghost detection unavailable — run `graphify enrich` to populate staleness._`. No $ARGUMENTS needed (parameter-less command).

---

### `graphify/commands/graphify-wayfind.md` — NEW (Plan 05, OBSCMD-06)

**Analog:** `graphify/commands/connect.md` (full file, 40 lines — same MCP tool, `connect_topics`).

**Copy-from pattern (connect.md lines 1-40):**
```markdown
---
name: connect
description: Find the shortest path and surprising bridge paths between two topics in the graph.
argument-hint: <topic-a> <topic-b>
disable-model-invocation: true
---

Arguments: $ARGUMENTS

Parse: `topic_a` is the first word or phrase, `topic_b` is the second distinct term. Split on the literal word "and" if present, else split on whitespace.

Call the graphify MCP tool `connect_topics` with:
- `topic_a`: [first topic parsed from $ARGUMENTS]
- `topic_b`: [second topic parsed from $ARGUMENTS]
- `budget`: 500

Parse `meta.status`.
[... status branches for no_graph, ambiguous_entity, entity_not_found, no_path, ok ...]
```

**Adaptation:** arg is a single `<topic>` — the other endpoint is the **MOC root**. Planner's MOC-root heuristic (Claude's Discretion D-05 in CONTEXT): "largest community's MOC, tie-break by lowest community_id." Skill.md prose chooses the MOC root internally (via `get_community(0)` or equivalent) then calls `connect_topics(topic_a=<resolved MOC node>, topic_b=$ARGUMENTS)`. Frontmatter gains `target: obsidian`.

---

### `graphify/commands/{argue,ask,challenge,connect,context,drift,emerge,ghost,trace}.md` — MODIFY (Plan 01)

**Analog:** self. Pure frontmatter-block edit — add one line `target: both` before closing `---`.

**Current frontmatter (e.g. `connect.md` lines 1-5):**
```markdown
---
name: connect
description: Find the shortest path and surprising bridge paths between two topics in the graph.
argument-hint: <topic-a> <topic-b>
disable-model-invocation: true
---
```

**Adapted (add `target: both`):**
```markdown
---
name: connect
description: Find the shortest path and surprising bridge paths between two topics in the graph.
argument-hint: <topic-a> <topic-b>
disable-model-invocation: true
target: both
---
```

**Reinforcement:** `test_ask_md_frontmatter` and `test_argue_md_frontmatter` currently assert `"target" not in fm` (lines 204, 222 of `test_commands.py`). **Plan 01 must flip those assertions** to `fm.get("target") == "both"` for the 9 commands being backfilled (and `target: obsidian` for the 4 new ones). Legacy-regression test coverage required per `test_install.py` spec in upstream prompt.

---

### `tests/test_commands.py` — MODIFY (frontmatter-schema + trust-boundary + contract tests)

**Analog 1 (frontmatter schema):** lines 195-230 — `test_ask_md_frontmatter` + `test_argue_md_frontmatter`.

**Copy-from pattern (test_ask_md_frontmatter, lines 195-211):**
```python
def test_ask_md_frontmatter():
    """CHAT-06: /graphify-ask command file exists with connect.md-style frontmatter."""
    path = _commands_dir() / "ask.md"
    assert path.exists(), "graphify/commands/ask.md missing"
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-ask"
    assert fm.get("description"), "description field required"
    assert fm.get("argument-hint"), "argument-hint field required"
    assert fm.get("disable-model-invocation") == "true"
    # Per CONTEXT.md Clarification: no `target:` field
    assert "target" not in fm, "ask.md must NOT have a target: field per CONTEXT.md Clarification"
    body = path.read_text()
    assert "chat" in body, "ask.md body must invoke the chat MCP tool"
    assert "$ARGUMENTS" in body, "ask.md must pass $ARGUMENTS to query"
```

**Adaptation — new tests to add (one per new P1 command):**
```python
def test_graphify_moc_md_frontmatter():
    """OBSCMD-03: /graphify-moc command file with vault-target frontmatter."""
    path = _commands_dir() / "graphify-moc.md"
    assert path.exists()
    fm = _parse_frontmatter(path)
    assert fm.get("name") == "graphify-moc"
    assert fm.get("target") == "obsidian", "graphify-moc must declare target: obsidian"
    assert fm.get("disable-model-invocation") == "true"
    body = path.read_text()
    assert "get_community" in body, "body must invoke get_community MCP tool"
    assert "propose_vault_note" in body, "OBSCMD-08: all writes via propose_vault_note"
    assert "$ARGUMENTS" in body
```

**Analog 2 (trust-boundary grep, Pitfall 3):**
```python
def test_all_p1_commands_route_through_propose_vault_note():
    """OBSCMD-08 / D-06: every vault-writing P1 command mentions propose_vault_note
    and never references a direct-write helper."""
    P1_WRITE_COMMANDS = ["graphify-moc", "graphify-orphan"]  # those that stage notes
    FORBIDDEN = ["Path.write_text", "os.write", "open(.*'w'", "write_note_directly"]
    for name in P1_WRITE_COMMANDS:
        body = _read(name.replace("graphify-", "graphify-"))  # file-name lookup
        assert "propose_vault_note" in body, f"{name} must call propose_vault_note"
        for pattern in FORBIDDEN:
            assert not re.search(pattern, body), f"{name} must not call {pattern} directly"
```

**Analog 3 (legacy backfill assertion — flip existing asserts):**
```python
def test_legacy_commands_backfilled_with_target_both():
    """Plan 01 pitfall 1: all 9 pre-Phase-14 commands must declare target: both
    so Plan 01's runtime filter does not silently drop them."""
    LEGACY = ["argue", "ask", "challenge", "connect", "context", "drift", "emerge", "ghost", "trace"]
    for name in LEGACY:
        fm = _parse_frontmatter(_commands_dir() / f"{name}.md")
        assert fm.get("target") == "both", f"{name}.md must carry target: both (Plan 01 backfill)"
```

**Analog 4 (dual-section test, for orphan):** reuse `test_connect_md_has_distinct_sections` pattern (test_commands.py lines 76-88):
```python
def test_connect_md_has_distinct_sections():
    text = _read("connect")
    assert "Shortest path" in text
    assert "Surprising bridges" in text

def test_connect_md_does_not_conflate_sections():
    text = _read("connect")
    idx_path = text.find("Shortest path")
    idx_bridges = text.find("Surprising bridges")
    assert idx_path < idx_bridges, "... must not be conflated (Pitfall 4)"
```

**Adaptation:** `test_graphify_orphan_has_dual_sections` asserting `## Isolated Nodes` precedes `## Stale/Ghost Nodes` AND graceful-absence banner `"run `graphify enrich`"` appears in prose.

---

### `tests/test_install.py` — MODIFY (directory-scan, target-filter, --no-obsidian-commands, default-both, legacy-regression)

**Analog 1 (install harness):** lines 19-26 — `_install(tmp_path, platform)` with `patch("graphify.__main__.Path.home")`.

**Copy-from pattern (lines 19-32):**
```python
def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)


def test_install_default_claude(tmp_path):
    _install(tmp_path, "claude")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()


def test_install_codex(tmp_path):
    _install(tmp_path, "codex")
```

**New tests to add (one per required coverage):**

```python
def test_install_legacy_commands_still_install_after_plan_01(tmp_path):
    """Pitfall 1 regression guard: existing 9 commands carry target: both
    and must land on disk for claude platform."""
    _install(tmp_path, "claude")
    dst = tmp_path / ".claude" / "commands"
    for name in ["argue", "ask", "challenge", "connect", "context", "drift", "emerge", "ghost", "trace"]:
        assert (dst / f"{name}.md").exists(), f"{name}.md must still install after Plan 01 filter"

def test_install_new_obsidian_commands_land_for_claude(tmp_path):
    """OBSCMD-02: target: obsidian commands install when platform supports obsidian."""
    _install(tmp_path, "claude")
    dst = tmp_path / ".claude" / "commands"
    for name in ["graphify-moc", "graphify-related", "graphify-orphan", "graphify-wayfind"]:
        assert (dst / f"{name}.md").exists()

def test_no_obsidian_commands_flag_skips_obsidian_target(tmp_path):
    """OBSCMD-02: --no-obsidian-commands excludes target: obsidian files."""
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude", no_obsidian_commands=True)
    dst = tmp_path / ".claude" / "commands"
    assert not (dst / "graphify-moc.md").exists()
    assert (dst / "connect.md").exists()  # target: both still installs

def test_uninstall_directory_scan_removes_new_commands(tmp_path):
    """OBSCMD-01: Plan 00 directory-scan uninstall picks up new commands
    without being named in a whitelist."""
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        uninstall(platform="claude")
    dst = tmp_path / ".claude" / "commands"
    for name in ["graphify-moc", "graphify-wayfind", "connect", "ask"]:
        assert not (dst / f"{name}.md").exists(), f"{name}.md should be uninstalled"

def test_default_target_is_both_when_frontmatter_missing(tmp_path, monkeypatch):
    """Plan 01 parser: a file without `target:` defaults to 'both' (belt-and-suspenders)."""
    from graphify.__main__ import _read_command_target
    f = tmp_path / "nofield.md"
    f.write_text("---\nname: foo\ndisable-model-invocation: true\n---\n\nBody.\n")
    assert _read_command_target(f) == "both"
```

---

## Shared Patterns

### Pattern: D-02 envelope parse (skill.md status-branch render)
**Source:** `graphify/commands/ask.md:14-29`, `graphify/commands/connect.md:15-38`, `graphify/commands/argue.md:12-22`
**Apply to:** all 4 new `graphify-*.md` commands
```markdown
The response is a D-02 envelope: text body, then `---GRAPHIFY-META---`, then JSON.

Parse `meta.status`.

**If `status` is `no_graph`:** render verbatim:
> No graph found at graphify-out/graph.json. Run `/graphify` to build one, then re-invoke this command.

**If `status` is `no_results`:** [case-specific fallback render]

**If `status` is `ok`:** [main render path]
```

### Pattern: Trust-boundary suffix (D-06, OBSCMD-08)
**Source:** synthetic (enforced by `test_all_p1_commands_route_through_propose_vault_note`)
**Apply to:** every new P1 command that writes to the vault (`graphify-moc`, optionally `graphify-orphan`)
```markdown
Call the graphify MCP tool `propose_vault_note` with:
- `title`: "<computed title>"
- `body_markdown`: <rendered body>
- `suggested_folder`: profile.folder_mapping.<type>
- `note_type`: "<moc|orphan|...>"
- `rationale`: "Phase 14 /<command> output"

Tell the user the proposal ID and instruct them to run `graphify approve <id>` —
do NOT write to the vault yourself.
```

### Pattern: Frontmatter stdlib parser (no PyYAML dep)
**Source:** `tests/test_commands.py` existing `_parse_frontmatter` helper + RESEARCH.md §"Pattern 3"
**Apply to:** `_install_commands` (`__main__.py`) and new tests
```python
_TARGET_RE = re.compile(r"^target:\s*(obsidian|code|both)\s*$", re.MULTILINE)

def _read_command_target(src: Path) -> str:
    try:
        head = src.read_text(encoding="utf-8", errors="replace")[:1024]
    except OSError:
        return "both"
    m = _TARGET_RE.search(head)
    return m.group(1) if m else "both"
```

### Pattern: Profile load with built-in fallback
**Source:** `graphify/profile.py:128-158` (`load_profile`)
**Apply to:** `graphify-moc.md` skill body (LLM instructs tool-layer to call this)
```python
def load_profile(vault_dir: str | Path) -> dict:
    """Discover and load a vault profile, merging over built-in defaults."""
    profile_path = Path(vault_dir) / ".graphify" / "profile.yaml"
    if not profile_path.exists():
        return _deep_merge(_DEFAULT_PROFILE, {})
    # ... YAML load + validate + deep_merge over _DEFAULT_PROFILE
    return _deep_merge(_DEFAULT_PROFILE, user_data)
```

### Pattern: Install harness mock (`Path.home()` → `tmp_path`)
**Source:** `tests/test_install.py:19-22`
**Apply to:** every new `test_install_*` test in Plan 01
```python
def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)
```

## No Analog Found

None — every file in Phase 14 has a strong in-repo analog. This phase is, as Research observed, "almost entirely composition of existing primitives."

## Metadata

**Analog search scope:**
- `graphify/__main__.py` (installer + CLI arg parse)
- `graphify/commands/*.md` (9 existing skill files)
- `graphify/profile.py` (vault profile loader)
- `tests/test_commands.py` (frontmatter schema + drift tests)
- `tests/test_install.py` (install harness)

**Files scanned:** 14
**Pattern extraction date:** 2026-04-22
