# Phase 22: Excalidraw Skill & Vault Bridge - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 8 (3 NEW, 5 MODIFY)
**Analogs found:** 8 / 8 (all in-tree)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/skill-excalidraw.md` (NEW) | skill prompt (runtime artifact) | agent-driven orchestration | `graphify/skill.md` (frontmatter); `graphify/skill-codex.md` (alt-platform variant) | exact (same kind of artifact) |
| `graphify/excalidraw.py` (MODIFY) | library (renderer + writer) | file-I/O, deterministic transform | itself — `render_stub` / `write_stubs` (extend, don't duplicate) | exact (same module, Phase 21 stub) |
| `graphify/__main__.py` (MODIFY: `_PLATFORM_CONFIG`) | CLI registry (dispatch dict) | config table | `antigravity` entry at L131–139 | exact (same shape: `claude_md=False`, `commands_enabled=False`) |
| `graphify/profile.py` (MODIFY: `_VALID_DT_KEYS`, `_DEFAULT_PROFILE`) | validator + defaults | schema validation | existing `diagram_types` block (L361–388) | exact (additive extension) |
| `pyproject.toml` (MODIFY: `[tool.setuptools.package-data]`) | packaging manifest | build-time include | existing list at L64 | exact (append filename) |
| `tests/test_excalidraw_layout.py` (NEW) | unit test (pure, `tmp_path`) | file-I/O fixtures | `tests/test_init_templates.py::test_write_stubs_*` | exact |
| `tests/test_install.py` (MODIFY) | unit test (install/uninstall) | file-I/O via `Path.home` patch | `test_install_codex` + `test_install_idempotent_commands` + `test_uninstall_idempotent` | exact |
| `tests/test_profile.py` (MODIFY) | unit test (schema) | dict validation | `test_validate_profile_unknown_key`, `test_validate_profile_accepts_default_profile_unchanged` | exact |

---

## Pattern Assignments

### `graphify/skill-excalidraw.md` (skill prompt)

**Analog:** `graphify/skill.md` (frontmatter shape only — content body is fully greenfield)

**Frontmatter pattern** (mirrors `skill.md` L1–6):
```markdown
---
name: excalidraw-diagram
description: Build an Excalidraw diagram from a graphify diagram seed and write it into the Obsidian vault.
trigger: /excalidraw-diagram
---
```

**Body skeleton** — see RESEARCH.md "Skill markdown skeleton (Plan 22-01)" §lines 528–591 (already written by researcher; planner copies verbatim).

**Required content checks for tests** (per RESEARCH validation matrix, lines 657–668):
- 7 numbered steps in pipeline (`test_excalidraw_skill_has_seven_steps`)
- references `list_diagram_seeds` and `get_diagram_seed` MCP tools (`test_excalidraw_skill_calls_seed_tools`)
- `.mcp.json` fenced block (`test_excalidraw_skill_has_mcp_json`)
- Style rules: `fontFamily: 5`, `#1e1e2e`, `transparent`, `compress: false` (`test_excalidraw_skill_has_style_rules`)
- Guard list: no LZ-String, no label-derived IDs, no multi-seed v1.5, no `.mcp.json` write, no direct frontmatter (`test_excalidraw_skill_has_guard_list`)

---

### `graphify/excalidraw.py` (extend with `layout_for` + `write_diagram`)

**Analog:** itself — Phase 21 `render_stub` / `write_stubs` (`graphify/excalidraw.py:46–106`).

**Imports pattern to keep** (lines 22–26):
```python
from __future__ import annotations

import json
from pathlib import Path

from graphify.profile import safe_frontmatter_value, validate_vault_path
```

**Path-confinement + atomic write pattern from `write_stubs`** (lines 90–106):
```python
vault_root = Path(vault_dir)
written: list[Path] = []
for dt in diagram_types:
    rel = dt.get("template_path") or f"Excalidraw/Templates/{dt.get('name', 'diagram')}.excalidraw.md"
    # Path confinement — raises ValueError on ``..`` or absolute escape
    target = validate_vault_path(rel, vault_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        continue
    target.write_text(render_stub(dt), encoding="utf-8")
    written.append(target)
return written
```

**`write_diagram` MUST mirror this**: `validate_vault_path` first, then `target.parent.mkdir(parents=True, exist_ok=True)`, then `target.write_text(..., encoding="utf-8")`. Difference vs `write_stubs`: collision on `force=False` raises `FileExistsError` (D-08) instead of silent skip — this is the only behavior delta.

**Scene skeleton to deep-copy** (lines 32–43):
```python
SCENE_JSON_SKELETON: dict = {
    "type": "excalidraw",
    "version": 2,
    "source": "graphify",
    "elements": [],
    "appState": {
        "viewBackgroundColor": "#ffffff",
        "gridSize": None,
        "currentItemFontFamily": 5,  # Excalifont
    },
    "files": {},
}
```
**Use `copy.deepcopy(SCENE_JSON_SKELETON)`** before injecting `elements[]` — shallow `dict(...)` would alias `elements: []`.

**`render_stub` body shape to reuse** (lines 56–67) — frontmatter + `## Text Elements` + `## Drawing` + ` ```json ` fence. Either call `render_stub` directly, or factor a `_render_excalidraw_md(name, scene)` helper that both stub-rendering and diagram-writing share.

**Layout signature** — see RESEARCH §"Fallback layout signature (Plan 22-01)" lines 348–375 for the full canonical dispatch dict (6 layout_types → helper functions, default `_layout_radial`).

**Element ID convention** (per D-12 guard list, anti-pattern in RESEARCH line 266): deterministic counter `f"elem-{i:04d}"`, never `slugify(label)`.

---

### `graphify/__main__.py` — `_PLATFORM_CONFIG` extension

**Analog:** `antigravity` entry at L131–139 — exact precedent for `claude_md: False`, `commands_enabled: False`.

**Existing `antigravity` block** (`graphify/__main__.py:131–139`):
```python
"antigravity": {
    "skill_file": "skill.md",
    "skill_dst": Path(".agent") / "skills" / "graphify" / "SKILL.md",
    "claude_md": False,
    "commands_src_dir": "commands",   # required key, even when commands disabled
    "commands_dst": None,
    "commands_enabled": False,
    "supports": ["code"],
},
```

**New entry to add** (per CONTEXT D-05; place between `antigravity` and `windows` so the cleanup comprehension at `__main__.py:~1157` sees it):
```python
"excalidraw": {
    "skill_file": "skill-excalidraw.md",
    "skill_dst": Path(".claude") / "skills" / "excalidraw-diagram" / "SKILL.md",
    "claude_md": False,
    "commands_src_dir": "commands",
    "commands_dst": None,
    "commands_enabled": False,
    "supports": ["obsidian", "code"],
},
```

**Install handler — DO NOT MODIFY.** It is dict-driven (`__main__.py:230–286`):
```python
cfg = _PLATFORM_CONFIG[platform]
# ...
skill_src = Path(__file__).parent / cfg["skill_file"]
if not skill_src.exists():
    print(f"error: {cfg['skill_file']} not found in package - reinstall graphify", file=sys.stderr)
    sys.exit(1)

skill_dst = Path.home() / cfg["skill_dst"]
skill_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(skill_src, skill_dst)
(skill_dst.parent / ".graphify_version").write_text(__version__, encoding="utf-8")
```
Adding the dict entry propagates automatically (verified by D-07 + RESEARCH Pitfall 6).

**Uninstall handler — DO NOT MODIFY.** Already dict-driven (`__main__.py:289–310`):
```python
cfg = _PLATFORM_CONFIG[platform]
skill_dst = Path.home() / cfg["skill_dst"]
if skill_dst.exists():
    skill_dst.unlink()
    print(f"  skill removed    ->  {skill_dst}")
version_file = skill_dst.parent / ".graphify_version"
if version_file.exists():
    version_file.unlink()
```

---

### `graphify/profile.py` — `_VALID_DT_KEYS` + `_DEFAULT_PROFILE` extension

**Analog:** existing `diagram_types` validator at L361–388 (added Phase 21).

**Current `_VALID_DT_KEYS`** (`profile.py:367–368`):
```python
_VALID_DT_KEYS = {"name", "template_path", "trigger_node_types",
                  "trigger_tags", "min_main_nodes", "naming_pattern"}
```

**Extend to** (RESEARCH Pitfall 3, lines 309–313):
```python
_VALID_DT_KEYS = {"name", "template_path", "trigger_node_types",
                  "trigger_tags", "min_main_nodes", "naming_pattern",
                  "layout_type", "output_path"}
```

**Type-check pattern to mirror** (each new key follows the same `if "X" in entry and not isinstance(...)` shape as existing checks at L370–386):
```python
if "layout_type" in entry and not isinstance(entry["layout_type"], str):
    errors.append(f"diagram_types[{i}].layout_type must be str")
if "output_path" in entry and not isinstance(entry["output_path"], str):
    errors.append(f"diagram_types[{i}].output_path must be str")
```

**Path-traversal validation for `output_path`** — defer to write-time `validate_vault_path` (already used by `write_stubs`); the validator-time check is optional (RESEARCH §test row "Profile schema | Path-traversal in `output_path` rejected at validation OR write time"). Recommended path: validate at write time only (one source of truth).

**`_DEFAULT_PROFILE` extension** (`profile.py:74–95`) — append `"layout_type": "<same-as-name>"` and `"output_path": "Excalidraw/Diagrams/"` to each of the 6 entries. Existing entry shape:
```python
{"name": "architecture", "template_path": "Excalidraw/Templates/architecture.excalidraw.md",
 "trigger_node_types": ["module", "service"], "trigger_tags": ["architecture"],
 "min_main_nodes": 3, "naming_pattern": "{topic}-architecture"},
```
Add: `"layout_type": "architecture", "output_path": "Excalidraw/Diagrams/"`. Note: 6 canonical `layout_type` values match the 6 `name` values 1:1 (verified via `seed.py:35–42` ↔ `profile.py:74–95`).

---

### `pyproject.toml` — `[tool.setuptools.package-data]`

**Analog:** existing line 64 — explicit list, no wildcard.

**Current state** (`pyproject.toml:63–64`):
```toml
[tool.setuptools.package-data]
graphify = ["skill.md", "skill-codex.md", "skill-opencode.md", "skill-aider.md", "skill-copilot.md", "skill-claw.md", "skill-windows.md", "skill-droid.md", "skill-trae.md", "builtin_templates/*.md", "commands/*.md", "routing_models.yaml", "capability_manifest.schema.json", "capability_tool_meta.yaml"]
```

**Add `"skill-excalidraw.md"` to the list** (mandatory; without this the install fails at runtime per RESEARCH Pitfall 1, lines 298–303). No `MANIFEST.in` exists in this repo (verified absent — pyproject is single source).

---

### `tests/test_excalidraw_layout.py` (NEW)

**Analog:** `tests/test_init_templates.py:75–119` (`test_write_stubs_*` series).

**Imports + fixtures pattern** (`tests/test_init_templates.py:14–27`):
```python
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from graphify.excalidraw import render_stub, write_stubs
from graphify.profile import _DEFAULT_PROFILE
```
For Phase 22, replace last two imports with `from graphify.excalidraw import layout_for, write_diagram, _VALID_LAYOUT_TYPES`.

**Path-traversal test pattern** (`test_init_templates.py:115–118`) — mirror exactly for `write_diagram`:
```python
def test_write_stubs_path_traversal_blocked(tmp_path):
    bad = [{"name": "evil", "template_path": "../../etc/passwd"}]
    with pytest.raises(ValueError, match="escape vault directory"):
        write_stubs(tmp_path, bad)
```
Phase 22 equivalent: `output_path: "../../etc"` → `pytest.raises(ValueError, match="escape vault directory")`.

**Idempotency / collision test pattern** (`test_init_templates.py:82–104`) — Phase 22's collision behavior is **stricter** (raises `FileExistsError` instead of silent skip). RESEARCH §lines 495–503 has the canonical shape — copy verbatim:
```python
def test_write_diagram_collision_refuses(tmp_path):
    seed = {"seed_id": "x", "main_node_label": "X", "main_nodes": [], "supporting_nodes": [],
            "relations": [], "suggested_layout_type": "mind-map"}
    profile = {"diagram_types": [{"name": "mind-map", "layout_type": "mind-map",
                                  "output_path": "Excalidraw/Diagrams"}]}
    write_diagram(tmp_path, seed, profile)
    import pytest
    with pytest.raises(FileExistsError):
        write_diagram(tmp_path, seed, profile)
    write_diagram(tmp_path, seed, profile, force=True)  # ok with force
```

**Frontmatter assertion pattern** (`test_init_templates.py:35–55`):
```python
def test_render_stub_contains_compress_false():
    out = render_stub({"name": "architecture"})
    assert "compress: false" in out
    assert "excalidraw-plugin: parsed" in out
```
Phase 22 equivalent: read written file body, assert `"compress: false" in body`, `"excalidraw-plugin: parsed" in body`, parse JSON inside ` ```json ` fence, assert `scene["appState"]["currentItemFontFamily"] == 5`.

**Determinism test** — see RESEARCH §lines 485–489. Two consecutive `layout_for(...)` calls must produce `json.dumps(..., sort_keys=True)`-equal output (D-02 byte-identical).

**Full canonical test bodies:** RESEARCH lines 471–526 — planner copies all 5 functions verbatim (`test_layout_for_all_six_layout_types`, `test_layout_for_is_deterministic`, `test_layout_for_unknown_falls_back_to_mind_map`, `test_write_diagram_collision_refuses`, `test_write_diagram_path_confined`, `test_write_diagram_compress_false`).

---

### `tests/test_install.py` — additions

**Analog:** `test_install_codex` (L30–33) for the install case; `test_install_idempotent_commands` (L393–399) for idempotency; `test_uninstall_idempotent` (L429–436) for uninstall idempotency; `test_codex_skill_contains_spawn_agent` (L142–146) for skill-content checks.

**Install fixture pattern** (`tests/test_install.py:19–28`):
```python
def _install(tmp_path, platform):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform=platform)


def test_install_default_claude(tmp_path):
    _install(tmp_path, "claude")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()
```
Phase 22 equivalent (RESEARCH lines 426–430):
```python
def test_install_excalidraw(tmp_path):
    _install(tmp_path, "excalidraw")
    assert (tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md").exists()
```

**Idempotency pattern** (`tests/test_install.py:393–399`):
```python
def test_install_idempotent_commands(tmp_path):
    """D-14: re-running install is idempotent — overwrites in place."""
    from unittest.mock import patch
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        install(platform="claude")   # second run must not raise
    assert (tmp_path / ".claude" / "commands" / "context.md").exists()
```

**Uninstall idempotency pattern** (`tests/test_install.py:429–436`):
```python
def test_uninstall_idempotent(tmp_path):
    """OBSCMD-01: repeated uninstall is a no-op (no exceptions)."""
    from unittest.mock import patch
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        uninstall(platform="claude")
        uninstall(platform="claude")  # must not raise
```

**Skill-content grep pattern** (`tests/test_install.py:142–146`):
```python
def test_codex_skill_contains_spawn_agent():
    """Codex skill file must reference spawn_agent."""
    import graphify
    skill = (Path(graphify.__file__).parent / "skill-codex.md").read_text()
    assert "spawn_agent" in skill
```
Phase 22 reuses this shape for: 7-step check, MCP tool refs, `.mcp.json` snippet, style rules, guard list (5 separate tests per validation matrix lines 657–668).

**Isolation test (D-07)** — RESEARCH lines 456–462:
```python
def test_install_excalidraw_does_not_touch_claude_skill(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        install(platform="excalidraw")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md").exists()
```

**Package-bundled file test** — RESEARCH lines 464–467:
```python
def test_excalidraw_skill_in_package():
    import graphify
    pkg = Path(graphify.__file__).parent
    assert (pkg / "skill-excalidraw.md").exists()
```

---

### `tests/test_profile.py` — additions

**Analog:** `test_validate_profile_unknown_key` (L137–141) and `test_validate_profile_accepts_default_profile_unchanged` (L695+).

**Acceptance test pattern** (mirror `test_validate_profile_accepts_default_profile_unchanged` shape):
```python
def test_diagram_types_layout_type_accepted():
    from graphify.profile import validate_profile
    p = {"diagram_types": [{"name": "mind-map", "layout_type": "mind-map",
                            "output_path": "Excalidraw/Diagrams/"}]}
    assert validate_profile(p) == []
```

**Type-error test pattern** (mirror existing per-key error tests at `profile.py:370–386`):
```python
def test_diagram_types_layout_type_must_be_str():
    from graphify.profile import validate_profile
    errors = validate_profile({"diagram_types": [{"layout_type": 123}]})
    assert any("layout_type must be str" in e for e in errors)
```

**Path-traversal test** (RESEARCH validation matrix line 677) — at write time via `write_diagram`, NOT validator. Belongs in `test_excalidraw_layout.py::test_write_diagram_path_confined` (already covered above). Optionally add a complementary validator-level guard.

---

## Shared Patterns

### Path Confinement
**Source:** `graphify/profile.py:407–422` (`validate_vault_path`)
**Apply to:** `write_diagram` (new), all vault writes
```python
def validate_vault_path(candidate: str | Path, vault_dir: str | Path) -> Path:
    vault_base = Path(vault_dir).resolve()
    resolved = (vault_base / candidate).resolve()
    try:
        resolved.relative_to(vault_base)
    except ValueError:
        raise ValueError(
            f"Profile-derived path {candidate!r} would escape vault directory {vault_base}. "
            "Check folder_mapping values for path traversal sequences."
        )
    return resolved
```
Always resolve target via this helper **before** `mkdir(parents=True, exist_ok=True)` and `write_text(...)`.

### Frontmatter Sanitization
**Source:** `graphify/profile.py::safe_frontmatter_value`
**Apply to:** any seed-label-derived `{topic}` slug used in filename or YAML frontmatter
- Run `safe_frontmatter_value(label)` first (handles YAML edge cases)
- Then `re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")` for filename slug (RESEARCH Don't-Hand-Roll table line 280)

### Atomic Write w/ Force Semantics
**Source:** `graphify/excalidraw.py:90–106` (`write_stubs`)
**Apply to:** `write_diagram`
- Behavior delta: `write_stubs` silently skips on collision when `force=False`; `write_diagram` MUST raise `FileExistsError` (per CONTEXT D-08).

### LZ-String Denylist (Cross-Cutting Negative Rule)
**Source:** `tests/test_denylist.py:83–93` (`test_no_lzstring_import_anywhere`)
**Apply to:** all new Python code in Phase 22
```python
def test_no_lzstring_import_anywhere():
    """compress: false one-way door — no lzstring imports in graphify/."""
    offenders: list[str] = []
    for py in (REPO_ROOT / "graphify").rglob("*.py"):
        src = py.read_text(encoding="utf-8")
        if re.search(r"^\s*(?:from|import)\s+lzstring", src, re.M | re.I):
            offenders.append(str(py.relative_to(REPO_ROOT)))
    assert not offenders, ("lzstring import forbidden ...")
```
Existing test will catch any regression automatically — new code must never `import lzstring` directly or transitively.

### Test Isolation (`tmp_path` + `Path.home` patch)
**Source:** `tests/test_install.py:19–22`
**Apply to:** every install/uninstall test
```python
from unittest.mock import patch
with patch("graphify.__main__.Path.home", return_value=tmp_path):
    install(platform=...)
```
No real filesystem writes outside `tmp_path` (CLAUDE.md test convention).

---

## No Analog Found

None. Every Phase 22 file has a direct in-tree analog. The only genuinely new code is:
1. The 6 layout helper functions (`_layout_grid`, `_layout_horizontal`, `_layout_radial`, `_layout_tree`) — RESEARCH §"Fallback layout signature" provides the dispatch shape; individual layout math is pure deterministic geometry (no analog needed beyond stdlib).
2. The skill markdown body — RESEARCH §"Skill markdown skeleton" lines 528–591 has the full draft.

---

## Metadata

**Analog search scope:**
- `graphify/__main__.py` (lines 49–145, 230–310 — `_PLATFORM_CONFIG` + install/uninstall)
- `graphify/excalidraw.py` (full file — Phase 21 stub renderer)
- `graphify/profile.py` (lines 60–95 default profile; 340–390 validator; 407–422 vault path)
- `graphify/skill.md`, `graphify/skill-codex.md` (frontmatter shape)
- `tests/test_install.py` (lines 1–90, 142–146, 385–475)
- `tests/test_init_templates.py` (lines 1–120 — fixture + assertion patterns)
- `tests/test_denylist.py` (lines 75–95 — LZ-String guard)
- `tests/test_profile.py` (validator test naming conventions)
- `pyproject.toml` (lines 63–64 — package-data list)

**Files scanned:** 9 Python source files, 4 test files, 1 packaging manifest, 2 skill files.
**Pattern extraction date:** 2026-04-27.
