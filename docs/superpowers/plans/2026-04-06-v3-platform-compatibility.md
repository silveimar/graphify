# v3 Platform Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Codex, OpenCode, and OpenClaw platform support via platform-specific skill files and a `graphify install --platform X` flag.

**Architecture:** The only section that differs between platforms is Step B2 (semantic extraction subagent dispatch) in skill.md. Three new skill files are created — one per platform — each identical to skill.md except for that one section. The `install()` function in `__main__.py` gains a `--platform` flag that copies the right skill file to the right config directory.

**Tech Stack:** Python 3.10+, pathlib, shutil, argparse (no new deps)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `graphify/skill.md` | Read-only | Source of truth — unchanged |
| `graphify/skill-codex.md` | Create | Codex variant (spawn_agent + wait) |
| `graphify/skill-opencode.md` | Create | OpenCode variant (@mention dispatch) |
| `graphify/skill-claw.md` | Create | OpenClaw variant (sequential extraction) |
| `graphify/__main__.py` | Modify | Add --platform flag to install() and main() |
| `pyproject.toml` | Modify | Add 3 new skill files to package-data |
| `tests/test_install.py` | Create | Platform routing tests |
| `README.md` | Modify | Platform table + token efficiency clarification |

---

## Task 1: Create the v3 branch

**Files:** none (git only)

- [ ] **Step 1: Create and switch to v3 branch**

```bash
cd /home/safi/graphify
git checkout -b v3
```

Expected: `Switched to a new branch 'v3'`

- [ ] **Step 2: Verify branch**

```bash
git branch --show-current
```

Expected: `v3`

---

## Task 2: Create `skill-codex.md`

skill-codex.md is identical to skill.md with one change: Step B2 replaces `Agent` tool calls with `spawn_agent` + `wait` + `close_agent` calls.

**Files:**
- Create: `graphify/skill-codex.md`

- [ ] **Step 1: Copy skill.md as the base**

```bash
cp graphify/skill.md graphify/skill-codex.md
```

- [ ] **Step 2: Open `graphify/skill-codex.md` and replace the Step B2 section**

Find this block (starts at "**Step B2 - Dispatch ALL subagents in a single message**", ends before "**Step B3**"):

Replace the entire Step B2 section with:

```markdown
**Step B2 - Dispatch ALL subagents in a single message (Codex)**

> **Codex platform:** This step uses `spawn_agent` + `wait` + `close_agent` instead of the Agent tool.
> Requires `multi_agent = true` in `~/.codex/config.toml`. If you get an error about multi-agent support, ask the user to add that config line and restart Codex.

Call `spawn_agent` once per chunk — all in the same response so they run in parallel:

```
spawn_agent(agent_type="worker", message="Your task is to perform the following. Follow the instructions below exactly.\n\n<agent-instructions>\nYou are a graphify extraction subagent. Read the files listed and extract a knowledge graph fragment.\nOutput ONLY valid JSON matching the schema below - no explanation, no markdown fences, no preamble.\n\nFiles (chunk CHUNK_NUM of TOTAL_CHUNKS):\nFILE_LIST\n\n[copy the extraction rules and JSON schema verbatim from the existing Step B2 content — it's already in the file from the cp step]\n</agent-instructions>\n\nExecute this now. Output ONLY the structured JSON response.")
```

Collect all handles. Then for each handle:
```
result = wait(handle)
close_agent(handle)
```

Parse each result as JSON. Accumulate nodes/edges/hyperedges across all results into `.graphify_semantic_new.json`.

If `spawn_agent` is not available, tell the user: "Codex multi-agent support is not enabled. Add `multi_agent = true` under `[features]` in `~/.codex/config.toml` and restart Codex."
```

- [ ] **Step 3: Verify the file looks correct**

```bash
grep -n "spawn_agent\|Step B2\|Step B3" graphify/skill-codex.md | head -20
```

Expected: lines showing spawn_agent in B2 and Step B3 after it.

- [ ] **Step 4: Commit**

```bash
git add graphify/skill-codex.md
git commit -m "add skill-codex.md for Codex platform (spawn_agent parallel extraction)"
```

---

## Task 3: Create `skill-opencode.md`

**Files:**
- Create: `graphify/skill-opencode.md`

- [ ] **Step 1: Copy skill.md as the base**

```bash
cp graphify/skill.md graphify/skill-opencode.md
```

- [ ] **Step 2: Open `graphify/skill-opencode.md` and replace the Step B2 section**

Replace the entire Step B2 section with:

```markdown
**Step B2 - Dispatch ALL subagents in a single message (OpenCode)**

> **OpenCode platform:** This step uses OpenCode's `@mention` dispatch instead of the Agent tool.

Dispatch all chunks in a single response. Each `@mention` runs in parallel:

```
@agent Chunk CHUNK_NUM of TOTAL_CHUNKS: You are a graphify extraction subagent. Read the files listed and extract a knowledge graph fragment. Output ONLY valid JSON matching the schema below.

Files:
FILE_LIST

[copy the extraction rules and JSON schema verbatim from the existing Step B2 content — already in the file from the cp step]
```

One `@mention` block per chunk. All in the same message — this is what makes them parallel.

Wait for all agents to return. Parse each response as JSON. Accumulate nodes/edges/hyperedges across all results into `.graphify_semantic_new.json`.
```

- [ ] **Step 3: Verify the file looks correct**

```bash
grep -n "@mention\|Step B2\|Step B3" graphify/skill-opencode.md | head -20
```

Expected: lines showing @mention in B2 and Step B3 after it.

- [ ] **Step 4: Commit**

```bash
git add graphify/skill-opencode.md
git commit -m "add skill-opencode.md for OpenCode platform (@mention parallel extraction)"
```

---

## Task 4: Create `skill-claw.md`

OpenClaw's agent support is MVP/incomplete so extraction is sequential — the orchestrating LLM reads each file and extracts directly.

**Files:**
- Create: `graphify/skill-claw.md`

- [ ] **Step 1: Copy skill.md as the base**

```bash
cp graphify/skill.md graphify/skill-claw.md
```

- [ ] **Step 2: Open `graphify/skill-claw.md` and replace the Step B2 section**

Replace the entire Step B2 section with:

```markdown
**Step B2 - Sequential extraction (OpenClaw)**

> **OpenClaw platform:** OpenClaw's multi-agent support is still early. Extraction runs sequentially — you read each file yourself and extract directly. This is slower than parallel platforms but reliable.

Load files from `.graphify_uncached.txt`. For each file, one at a time:

1. Read the file contents
2. Extract nodes, edges, and hyperedges following the same rules and schema as the parallel variant (see schema below)
3. Accumulate results into a running JSON object

Apply all the same extraction rules:
- EXTRACTED / INFERRED / AMBIGUOUS confidence with confidence_score on every edge
- rationale_for nodes for design decisions and WHY comments
- semantically_similar_to edges for cross-file conceptual links (non-obvious only)
- hyperedges for groups of 3+ nodes (max 3 per file)
- DEEP_MODE: more aggressive INFERRED edges if --mode deep was given

Schema (same as parallel variant):
{"nodes":[{"id":"filestem_entityname","label":"Human Readable Name","file_type":"code|document|paper|image","source_file":"relative/path","source_location":null,"source_url":null,"captured_at":null,"author":null,"contributor":null}],"edges":[{"source":"node_id","target":"node_id","relation":"calls|implements|references|cites|conceptually_related_to|shares_data_with|semantically_similar_to|rationale_for","confidence":"EXTRACTED|INFERRED|AMBIGUOUS","confidence_score":1.0,"source_file":"relative/path","source_location":null,"weight":1.0}],"hyperedges":[{"id":"snake_case_id","label":"Human Readable Label","nodes":["node_id1","node_id2","node_id3"],"relation":"participate_in|implement|form","confidence":"EXTRACTED|INFERRED","confidence_score":0.75,"source_file":"relative/path"}],"input_tokens":0,"output_tokens":0}

After processing all files, write the accumulated result to `.graphify_semantic_new.json`.
```

- [ ] **Step 3: Also remove the timing estimate block from Step B**

In skill-claw.md, find and remove this paragraph (it only applies to parallel dispatch):

```
Before dispatching subagents, print a timing estimate:
- Load `total_words` and file counts from `.graphify_detect.json`
- Estimate agents needed: `ceil(uncached_non_code_files / 22)` (chunk size is 20-25)
- Estimate time: ~45s per agent batch (they run in parallel, so total ≈ 45s × ceil(agents/parallel_limit))
- Print: "Semantic extraction: ~N files → X agents, estimated ~Ys"
```

Replace with:

```
Print: "Semantic extraction: N files (sequential — OpenClaw platform)"
```

- [ ] **Step 4: Verify**

```bash
grep -n "sequential\|Step B2\|Step B3\|spawn_agent\|@mention" graphify/skill-claw.md | head -20
```

Expected: "sequential" appears in B2, no spawn_agent or @mention.

- [ ] **Step 5: Commit**

```bash
git add graphify/skill-claw.md
git commit -m "add skill-claw.md for OpenClaw platform (sequential extraction)"
```

---

## Task 5: Update `pyproject.toml` package-data

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update package-data to include the three new skill files**

In `pyproject.toml`, find:

```toml
[tool.setuptools.package-data]
graphify = ["skill.md"]
```

Replace with:

```toml
[tool.setuptools.package-data]
graphify = ["skill.md", "skill-codex.md", "skill-opencode.md", "skill-claw.md"]
```

- [ ] **Step 2: Verify**

```bash
grep -A2 "package-data" pyproject.toml
```

Expected: all four skill files listed.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "include platform skill files in package-data"
```

---

## Task 6: Add `--platform` flag to install command

**Files:**
- Modify: `graphify/__main__.py`

- [ ] **Step 1: Write the failing test first**

Create `tests/test_install.py`:

```python
"""Tests for graphify install --platform routing."""
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch


PLATFORMS = {
    "claude": ("skill.md", ".claude/skills/graphify/SKILL.md"),
    "codex": ("skill-codex.md", ".agents/skills/graphify/SKILL.md"),
    "opencode": ("skill-opencode.md", ".config/opencode/skills/graphify/SKILL.md"),
    "claw": ("skill-claw.md", ".claw/skills/graphify/SKILL.md"),
}


def test_install_default_uses_claude_skill(tmp_path):
    """install() with no platform copies skill.md to ~/.claude/skills/graphify/SKILL.md"""
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
    dst = tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md"
    assert dst.exists()


def test_install_codex_copies_correct_file(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="codex")
    dst = tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md"
    assert dst.exists()


def test_install_opencode_copies_correct_file(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="opencode")
    dst = tmp_path / ".config" / "opencode" / "skills" / "graphify" / "SKILL.md"
    assert dst.exists()


def test_install_claw_copies_correct_file(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claw")
    dst = tmp_path / ".claw" / "skills" / "graphify" / "SKILL.md"
    assert dst.exists()


def test_install_unknown_platform_exits(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        with pytest.raises(SystemExit):
            install(platform="unknown")


def test_all_skill_files_exist_in_package():
    """Verify all platform skill files are present in the installed package."""
    import graphify
    pkg_dir = Path(graphify.__file__).parent
    for src_name, _ in PLATFORMS.values():
        skill_path = pkg_dir / src_name
        assert skill_path.exists(), f"Missing skill file: {src_name}"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python -m pytest tests/test_install.py -v --tb=short 2>&1 | head -40
```

Expected: FAIL — `install()` doesn't accept a `platform` argument yet.

- [ ] **Step 3: Update `install()` in `graphify/__main__.py`**

Replace the current `install()` function and add `_PLATFORM_CONFIG`:

```python
_PLATFORM_CONFIG = {
    "claude": {
        "skill_file": "skill.md",
        "skill_dst": Path(".claude") / "skills" / "graphify" / "SKILL.md",
        "claude_md": True,   # only Claude Code gets CLAUDE.md registration
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
    "claw": {
        "skill_file": "skill-claw.md",
        "skill_dst": Path(".claw") / "skills" / "graphify" / "SKILL.md",
        "claude_md": False,
    },
}


def install(platform: str = "claude") -> None:
    if platform not in _PLATFORM_CONFIG:
        print(f"error: unknown platform '{platform}'. Choose from: {', '.join(_PLATFORM_CONFIG)}", file=sys.stderr)
        sys.exit(1)

    cfg = _PLATFORM_CONFIG[platform]
    skill_src = Path(__file__).parent / cfg["skill_file"]
    if not skill_src.exists():
        print(f"error: {cfg['skill_file']} not found in package - reinstall graphify", file=sys.stderr)
        sys.exit(1)

    skill_dst = Path.home() / cfg["skill_dst"]
    skill_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(skill_src, skill_dst)
    print(f"  skill installed  →  {skill_dst}")

    if cfg["claude_md"]:
        # Register in ~/.claude/CLAUDE.md (Claude Code only)
        claude_md = Path.home() / ".claude" / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            if "graphify" in content:
                print(f"  CLAUDE.md        →  already registered (no change)")
            else:
                claude_md.write_text(content.rstrip() + _SKILL_REGISTRATION)
                print(f"  CLAUDE.md        →  skill registered in {claude_md}")
        else:
            claude_md.parent.mkdir(parents=True, exist_ok=True)
            claude_md.write_text(_SKILL_REGISTRATION.lstrip())
            print(f"  CLAUDE.md        →  created at {claude_md}")

    print()
    print("Done. Open your AI coding assistant and type:")
    print()
    print("  /graphify .")
    print()
```

- [ ] **Step 4: Update `main()` to pass `--platform` to `install()`**

In `main()`, find the `if cmd == "install":` block:

```python
    if cmd == "install":
        install()
```

Replace with:

```python
    if cmd == "install":
        platform = "claude"
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i].startswith("--platform="):
                platform = args[i].split("=", 1)[1]
                i += 1
            elif args[i] == "--platform" and i + 1 < len(args):
                platform = args[i + 1]
                i += 2
            else:
                i += 1
        install(platform=platform)
```

- [ ] **Step 5: Update the help text in `main()`**

Find:
```python
        print("  install                 copy skill to ~/.claude/skills/ and register in CLAUDE.md")
```

Replace with:
```python
        print("  install [--platform P]  copy skill to platform config dir (claude|codex|opencode|claw)")
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/test_install.py -v --tb=short
```

Expected: all 6 tests PASS.

- [ ] **Step 7: Run the full test suite to check for regressions**

```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

Expected: existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add graphify/__main__.py tests/test_install.py
git commit -m "add --platform flag to graphify install (codex, opencode, claw)"
```

---

## Task 7: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add platform support table under the Install section**

After the `pip install graphifyy && graphify install` code block, add:

```markdown
### Platform support

| Platform | Install command |
|----------|----------------|
| Claude Code | `graphify install` |
| Codex | `graphify install --platform codex` |
| OpenCode | `graphify install --platform opencode` |
| OpenClaw | `graphify install --platform claw` |

Codex users also need `multi_agent = true` under `[features]` in `~/.codex/config.toml` for parallel extraction. OpenClaw uses sequential extraction (parallel agent support is still early on that platform).
```

- [ ] **Step 2: Clarify token efficiency — find the benchmark section**

Find the line:
```
**Token benchmark** - printed automatically after every run. On a mixed corpus (Karpathy repos + papers + images): **71.5x** fewer tokens per query vs reading raw files.
```

Replace with:
```
**Token benchmark** - printed automatically after every run. On a mixed corpus (Karpathy repos + papers + images): **71.5x** fewer tokens per query vs reading raw files. The first run extracts and builds the graph (this costs tokens). Every subsequent query reads the compact graph instead of raw files — that's where the savings compound. The SHA256 cache means re-runs only re-process changed files.
```

- [ ] **Step 3: Verify README renders correctly**

```bash
grep -n "Platform support\|multi_agent\|first run extracts" README.md
```

Expected: all three lines found.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "add platform support table and clarify token efficiency in README"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

Expected: all tests pass, no regressions.

- [ ] **Step 2: Verify all four skill files are present in the package**

```bash
ls graphify/skill*.md
```

Expected:
```
graphify/skill.md
graphify/skill-codex.md
graphify/skill-opencode.md
graphify/skill-claw.md
```

- [ ] **Step 3: Smoke test each install path**

```bash
python -m graphify.__main__ install --platform codex 2>&1 | head -5
python -m graphify.__main__ install --platform opencode 2>&1 | head -5
python -m graphify.__main__ install --platform claw 2>&1 | head -5
python -m graphify.__main__ install --platform unknown 2>&1
```

Expected: first three print "skill installed →", last prints "error: unknown platform".

- [ ] **Step 4: Push v3 branch**

```bash
git push -u origin v3
```
