# Phase 25: Mandatory Dual-Artifact Persistence in Skill Files — Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 11 (1 new test file + 9 skill markdown files + pyproject.toml verified)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/test_skill_persistence.py` (NEW) | test (regression / install-emit grep + drift lock) | request-response (parameterized install + file-read assert) | `tests/test_install.py` | exact (same module — install path mocking + skill-file read) |
| `graphify/skill.md` (MODIFIED) | skill prose / source-of-truth | static content (markdown insertion) | self (lines 12 / 46 anchors) | self-anchor |
| `graphify/skill-aider.md` (MODIFIED) | skill prose variant | static content (verbatim copy) | `graphify/skill-codex.md` (lines 12 / 42) | exact (same `## Usage` / `## Available slash commands` neighbors) |
| `graphify/skill-claw.md` (MODIFIED) | skill prose variant | static content | `graphify/skill-codex.md` | exact |
| `graphify/skill-codex.md` (MODIFIED) | skill prose variant | static content | self-anchor (lines 12 / 42) | self-anchor |
| `graphify/skill-copilot.md` (MODIFIED) | skill prose variant | static content | `graphify/skill-codex.md` | exact |
| `graphify/skill-droid.md` (MODIFIED) | skill prose variant | static content | `graphify/skill-codex.md` | exact |
| `graphify/skill-opencode.md` (MODIFIED) | skill prose variant | static content | `graphify/skill-codex.md` | exact |
| `graphify/skill-trae.md` (MODIFIED) | skill prose variant | static content | `graphify/skill-codex.md` | exact |
| `graphify/skill-windows.md` (MODIFIED) | skill prose variant | static content | `graphify/skill-codex.md` | exact |
| `pyproject.toml` (NOT MODIFIED — verified) | build config | static config | self | self-anchor |

**Key resolution:** Research flagged a possible `pyproject.toml` edit if `skill-aider.md` or `skill-copilot.md` were missing from `tool.setuptools.package-data`. **Verified false positive:** both files are already listed (`pyproject.toml:62`). No `pyproject.toml` edit is required for this phase. Plan should explicitly mark this as VERIFIED, not as a deferred task.

## Pattern Assignments

### `tests/test_skill_persistence.py` (NEW — test, request-response)

**Analog:** `tests/test_install.py`

**Imports pattern** (`tests/test_install.py:1-5`):
```python
"""Tests for graphify install --platform routing."""
import re
from pathlib import Path
from unittest.mock import patch
import pytest
```

For Phase 25 the new module should mirror this exactly minus `re` (substring `in` checks suffice). Recommended header:
```python
"""Tests for the mandatory persistence-contract block in skill files (SKILLMEM-01..04)."""
from pathlib import Path
from unittest.mock import patch
import pytest

from graphify.__main__ import _PLATFORM_CONFIG, install
```

**Install + Path.home mock helper** (`tests/test_install.py:18-23`) — copy this shape verbatim:
```python
def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)
```

**Per-platform parameterized read pattern** — `tests/test_install.py:26-66` is currently *unrolled* into 8 individual `def test_install_<platform>` functions. The Phase 25 test should COLLAPSE this shape into a `@pytest.mark.parametrize` over `_PLATFORM_CONFIG.keys()` (minus `excalidraw`), as research recommends:
```python
PERSISTENCE_CANARY = "<!-- graphify:persistence-contract:v1 -->"
_IN_SCOPE_PLATFORMS = sorted(k for k in _PLATFORM_CONFIG if k != "excalidraw")

@pytest.mark.parametrize("platform", _IN_SCOPE_PLATFORMS)
def test_install_emits_persistence_canary(tmp_path, platform):
    """SKILLMEM-03/04: every install destination contains the canary."""
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)
    cfg = _PLATFORM_CONFIG[platform]
    emitted = tmp_path / cfg["skill_dst"]
    assert emitted.exists(), f"{platform}: skill not emitted at {emitted}"
    text = emitted.read_text(encoding="utf-8")
    assert PERSISTENCE_CANARY in text, f"{platform}: canary missing in {emitted}"
```

**Package-file read precedent** (`tests/test_install.py:69-89`) — same shape used for the byte-equality drift lock:
```python
def test_codex_skill_contains_spawn_agent():
    """Codex skill file must reference spawn_agent."""
    import graphify
    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
    assert "spawn_agent" in skill
```

The byte-equality drift test should clone this shape but iterate the 9 source files:
```python
_SOURCE_VARIANTS = [
    "skill.md", "skill-aider.md", "skill-claw.md", "skill-codex.md",
    "skill-copilot.md", "skill-droid.md", "skill-opencode.md",
    "skill-trae.md", "skill-windows.md",
]

def test_persistence_block_byte_equal_across_variants():
    """SKILLMEM-02: contract block must be byte-identical across in-scope variants."""
    import graphify
    pkg = Path(graphify.__file__).parent
    blocks = []
    for name in _SOURCE_VARIANTS:
        text = (pkg / name).read_text(encoding="utf-8")
        start = text.index(PERSISTENCE_CANARY)
        end = text.index("\n## ", start + len(PERSISTENCE_CANARY) + 1)
        blocks.append(text[start:end])
    assert all(b == blocks[0] for b in blocks), "persistence block drift detected"
```

**Error/no-side-effect pattern:** Tests must not write outside `tmp_path`. The `Path.home` mock guarantees this — `install()` resolves all destinations via `Path.home() / cfg["skill_dst"]`. No new fixtures or `conftest.py` changes are needed; `tmp_path` is built into pytest.

**Test naming convention** (from `tests/test_install.py`):
- `test_install_<platform>` for per-platform install tests
- `test_<platform>_skill_contains_<feature>` for skill-content assertions
- For Phase 25 use: `test_install_emits_persistence_canary` (parameterized) and `test_persistence_block_byte_equal_across_variants` (single test).

---

### `graphify/skill.md` (MODIFIED — skill prose, static content)

**Analog:** self (file is the source-of-truth). Insertion site verified at `## Usage` (line 12) and `## Available slash commands` (line 46).

**Concrete diff site shape** — observe the existing neighbor structure in `graphify/skill-codex.md:1-46` (verified identical anchor pattern across all variants):
```markdown
## Usage

```
/graphify                                             # full pipeline ...
... (~30 lines of usage CLI examples) ...
/graphify analyze for <lens>                           # single-lens tournament ...
```

## Available slash commands

After `graphify install`, these commands are available in Claude Code:
- `/context` — full graph-backed summary ...
```

**Insertion rule** — referenced by HEADING anchor, not line number (per Pitfall 2 in research):
1. Locate the line `## Available slash commands`.
2. Insert the contract block IMMEDIATELY ABOVE that line, leaving a blank line above the canary and a blank line between the closing of the contract block and the `## Available slash commands` heading.
3. The contract block begins with the literal line `<!-- graphify:persistence-contract:v1 -->` and ends just before the next `## ` heading.

**Drafted block** — see RESEARCH.md "Code Examples → Drafted Contract Block." Plan should treat the prose as discretionary BUT lock the canary string, the schema (frontmatter keys, fenced JSON), the error/empty semantics, and the collision rule.

---

### `graphify/skill-{aider,claw,codex,copilot,droid,opencode,trae,windows}.md` (MODIFIED × 8)

**Analog:** `graphify/skill.md` (after Wave 1 insertion). Each variant uses the same `## Usage` / `## Available slash commands` anchor pair.

**Insertion site per variant** (verified by research grep, RESEARCH.md "Diff Sites" table):

| File | `## Usage` line | `## Available slash commands` line | Total lines |
|------|----:|----:|----:|
| `graphify/skill.md`         | 12 | 46 | 1819 |
| `graphify/skill-aider.md`   | 11 | 40 | 1294 |
| `graphify/skill-claw.md`    | 11 | 40 | 1294 |
| `graphify/skill-codex.md`   | 12 | 42 | 1373 |
| `graphify/skill-copilot.md` | 11 | 42 | 1375 |
| `graphify/skill-droid.md`   | 11 | 40 | 1349 |
| `graphify/skill-opencode.md`| 11 | 40 | 1348 |
| `graphify/skill-trae.md`    | 11 | 40 | 1318 |
| `graphify/skill-windows.md` | 11 | 43 | 1352 |

**Edit pattern** — copy bytes from `skill.md` between the canary line and the line preceding `\n## Available slash commands`, then paste at the same heading position in each variant. Use `Edit` tool with the exact `## Available slash commands` heading line as the `old_string` anchor and the prepended block + heading as the `new_string`.

**Critical constraint (from CONTEXT.md decision 4):** No paraphrasing. Bytes must be identical to `graphify/skill.md`'s block. The `test_persistence_block_byte_equal_across_variants` test enforces this.

---

### `pyproject.toml` (VERIFIED — NOT MODIFIED)

**Analog:** self. `tool.setuptools.package-data` already includes all 9 in-scope skill files:
```toml
[tool.setuptools.package-data]
graphify = ["skill.md", "skill-codex.md", "skill-opencode.md", "skill-aider.md", "skill-copilot.md", "skill-claw.md", "skill-windows.md", "skill-droid.md", "skill-trae.md", "skill-excalidraw.md", "builtin_templates/*.md", "commands/*.md", "routing_models.yaml", "capability_manifest.schema.json", "capability_tool_meta.yaml"]
```
**Action:** none. Research's RQ2 (Open Question 2) is resolved — no pyproject edit required. Plan should reference this verified state and explicitly say `pyproject.toml: VERIFIED, no change`.

---

## Shared Patterns

### Path.home mock for install tests
**Source:** `tests/test_install.py:21-23`
**Apply to:** `tests/test_skill_persistence.py` (every test that invokes `install()`)
```python
with patch("graphify.__main__.Path.home", return_value=tmp_path):
    install(platform=platform)
```
This is the canonical pattern across the codebase. Do NOT introduce a new fixture in `conftest.py` — research explicitly warns against this (Don't Hand-Roll table).

### Reading skill files by package path
**Source:** `tests/test_install.py:71-73`
**Apply to:** Every test in `tests/test_skill_persistence.py` that needs to read source variants directly (i.e., the byte-equality test).
```python
import graphify
skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
```
For Phase 25 add `encoding="utf-8"` (research recommends explicit encoding for the canary HTML-comment which must be read as raw bytes-ish text, not rendered).

### Iterating `_PLATFORM_CONFIG` for platform-fan-out tests
**Source:** `graphify/__main__.py:49-155` (the dict definition) + Phase 22 precedent (research mentions `test_platform_config_has_excalidraw`)
**Apply to:** `test_install_emits_persistence_canary`
```python
from graphify.__main__ import _PLATFORM_CONFIG
_IN_SCOPE_PLATFORMS = sorted(k for k in _PLATFORM_CONFIG if k != "excalidraw")
```
Iterate the dict directly — do not hardcode the 11 platform names. Adding a future platform must force a deliberate include/exclude decision (Pitfall 4 in research).

### Heading-anchored insertion for skill markdown edits
**Source:** convention across all 9 skill variants — every file has uniform `## Usage` and `## Available slash commands` neighbor headings.
**Apply to:** All 9 skill-file edits in this phase.
**Rule:** Reference HEADING text in plans, never line numbers. Editor tool calls must use the literal `## Available slash commands` heading line as the unique anchor for `Edit`'s `old_string`.

### TDD wave ordering (RED → GREEN → drift-lock)
**Source:** RESEARCH.md "Recommended Task Ordering"
**Apply to:** Every plan in this phase.
- Wave 0: write both tests; assert they fail (RED).
- Wave 1: insert block in `skill.md` only; canary test passes for `claude` and `antigravity`; byte-equality still fails.
- Wave 2: copy block byte-for-byte into the 8 remaining variants; canary test fully green.
- Wave 3: byte-equality test green by construction; full `pytest tests/ -q` green.

## No Analog Found

(none — every file has a clean analog or is the source-of-truth)

## Metadata

**Analog search scope:**
- `tests/` (all test_*.py files)
- `graphify/__main__.py` (lines 40-160 for `_PLATFORM_CONFIG`)
- `graphify/skill.md` and 8 variants (lines 1-55 for insertion-anchor verification)
- `pyproject.toml` (full file for package-data verification)

**Files scanned:** 14 (1 main, 9 skill variants, 1 pyproject, 1 test file, 2 planning docs)

**Pattern extraction date:** 2026-04-27

**Key insight for planner:** This phase has ZERO Python production code changes. All Python changes are in tests; all "implementation" is markdown editing. Plans that introduce helper modules, new fixtures, or refactors are over-engineering and should be rejected.
