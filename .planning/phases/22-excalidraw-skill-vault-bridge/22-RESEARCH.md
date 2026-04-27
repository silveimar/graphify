# Phase 22: Excalidraw Skill & Vault Bridge - Research

**Researched:** 2026-04-27
**Domain:** Skill packaging + Excalidraw scene generation + vault write pipeline
**Confidence:** HIGH (all inputs verified in-tree; no external library research needed)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Pure-Python fallback layout**
- **D-01:** When `mcp_excalidraw` is unavailable, the fallback dispatches on `profile.diagram_types[*].layout_type`. Each layout maps to a small deterministic algorithm so output is stable for unit tests.
- **D-02:** Fallback algorithms are deterministic — no randomness, no seeded RNG, no external numerical libs. Coordinates integer-rounded; identical SeedDict + profile produces byte-identical scene JSON.
- **D-03:** Fallback reuses `graphify/excalidraw.py::render_stub` / `write_stubs` primitives; new layout helpers live in the same module.

**Install surface (`_PLATFORM_CONFIG`)**
- **D-04:** `excalidraw` becomes a new top-level key in `_PLATFORM_CONFIG`. Invoked as `graphify install excalidraw` / `graphify uninstall excalidraw` (positional, matching every existing platform).
- **D-05:** Entry shape — `skill_file: "skill-excalidraw.md"`, `skill_dst: Path(".claude") / "skills" / "excalidraw-diagram" / "SKILL.md"`, `claude_md: False`, `commands_enabled: False`, `supports: ["obsidian", "code"]`.
- **D-06:** Install/uninstall idempotent: install creates parents and overwrites only if content differs; uninstall removes if present, no-op otherwise.
- **D-07:** Existing platform entries (claude/codex/...) MUST NOT be modified — tests assert this.

**Vault write semantics**
- **D-08:** On collision: refuse by default + report; user passes skill-level `force: true` arg to overwrite.
- **D-09:** Output path comes from `profile.diagram_types[].output_path` (or analogous field — confirm in research) with fallback `Excalidraw/Diagrams/`.
- **D-10:** Filename pattern: `{topic}-{layout_type}.excalidraw.md`. `{topic}` slugified from seed; `{layout_type}` from the profile entry. Reuse `safe_frontmatter_value`-style sanitization.

**`.mcp.json` delivery**
- **D-11:** `.mcp.json` snippet (obsidian + excalidraw servers) lives **inside `skill-excalidraw.md`** as a fenced copy-pasteable block. Graphify never reads/writes/merges user `.mcp.json`.
- **D-12:** SKILL-05 guard list is a literal section in `skill-excalidraw.md`: `compress: false` assertion, no LZ-String, no label-derived element IDs, no direct frontmatter writes from skill, no multi-seed in v1.5.

**Skill orchestration**
- **D-13:** Fixed 7-step pipeline: (1) `list_diagram_seeds`; (2) user selects; (3) `get_diagram_seed(seed_id)` → SeedDict; (4) read template via mcp-obsidian (or pure-Python file read in fallback); (5) build via `mcp_excalidraw` OR fallback; (6) export → vault output path; (7) report seed_id, node count, template, vault path.
- **D-14:** Style locked: Excalifont (font family 5), `strokeColor: "#1e1e2e"`, `backgroundColor: "transparent"`, `compress: false`.

### Claude's Discretion
- Names of new layout helpers (`layout_for`, `_grid_layout`, `_tree_layout`, …).
- Module placement: `graphify/excalidraw.py` vs `graphify/excalidraw/layout.py`.
- Test fixture shape — explicit per-layout vs parametrized.
- Skill prompt phrasing for the `force` argument.

### Deferred Ideas (OUT OF SCOPE)
- Auto-merge `.mcp.json`. Multi-seed diagrams. Layout customization beyond `layout_type`. Force-directed/spring layouts. Inline overwrite-vs-cancel prompt. Auto-suffix-on-collision.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILL-01 | `graphify install --excalidraw` installs `skill-excalidraw.md` to `.claude/skills/excalidraw-diagram/SKILL.md`; new `excalidraw` entry in `_PLATFORM_CONFIG`. | `_PLATFORM_CONFIG` pattern at `graphify/__main__.py:49–145`; install handler at L230–286 already iterates the dict generically. New entry per D-05. Plan stub: 22-02. |
| SKILL-02 | `graphify uninstall --excalidraw` removes installed skill file. | Existing `uninstall()` at L286–310 already iterates `_PLATFORM_CONFIG[platform]`. No code change beyond entry add. Plan stub: 22-02. |
| SKILL-03 | Install + uninstall idempotent. | Existing pattern: `shutil.copy` overwrites in place; `unlink()` only if `exists()`. Same precedent enforced by `test_install_idempotent_commands` (test_install.py:393). Plan stub: 22-02. |
| SKILL-04 | `skill-excalidraw.md` orchestrates 7-step pipeline. | MCP tools `list_diagram_seeds` + `get_diagram_seed` already implemented (`serve.py:2553–2740`). SeedDict shape verified (`seed.py:289–301`). Plan stub: 22-01. |
| SKILL-05 | `skill-excalidraw.md` includes `.mcp.json` snippet, vault rules, style rules, guard list. | All literal content authored inside the skill markdown. No code logic. Plan stub: 22-01. |
| SKILL-06 | mcp_excalidraw is optional; pure-Python fallback writes a complete `.excalidraw.md`. **Pure-Python path complete BEFORE mcp_excalidraw integration.** | Existing `render_stub` returns valid scene skeleton (`excalidraw.py:36–66`); fallback extends with `layout_for(layout_type, nodes, edges) -> elements`. Plan stub: 22-01. |
</phase_requirements>

## Summary

Phase 22 is largely a **packaging + content-authoring** phase. The heavy MCP plumbing (Phase 20), template generation (Phase 21), and scene-skeleton renderer (`render_stub` / `write_stubs`, Phase 21) all already exist. What remains:

1. Add **one `_PLATFORM_CONFIG` entry** plus a packaging glob update — the existing `install()` / `uninstall()` handlers in `__main__.py` are already dict-driven and need no code changes for the new entry to work (verified `antigravity` precedent at L132–139).
2. Author **`graphify/skill-excalidraw.md`** — a runtime artifact prompt, not Python. Contains the 7-step pipeline, `.mcp.json` block, style rules, guard list.
3. Extend **`graphify/excalidraw.py`** with a deterministic `layout_for(layout_type, nodes, edges, **opts)` helper that injects real `elements[]` into the `SCENE_JSON_SKELETON` for the SKILL-06 fallback. The 6 valid `layout_type` values are already canonical (`seed.py:35–42`).
4. Add **profile schema fields** (`layout_type`, `output_path`) to `diagram_types` — currently only `name`, `template_path`, `trigger_node_types`, `trigger_tags`, `min_main_nodes`, `naming_pattern` are validated (`profile.py:362–390`).
5. Add **install/idempotency tests** in `tests/test_install.py` (or a new `test_install_excalidraw.py`) and **fallback-path tests** extending `tests/test_init_templates.py` patterns.

**Primary recommendation:** Plan 22-01 = skill markdown + pure-Python fallback (`layout_for`) + profile schema extension. Plan 22-02 = `_PLATFORM_CONFIG` entry + packaging + install/uninstall tests. Wire SKILL-06 ordering by gating mcp_excalidraw references inside the skill markdown behind an explicit "Step 5b: fallback" branch that calls into the Python path.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill prompt orchestration (7 steps) | Skill markdown (runtime artifact, agent-side) | — | Skill is interpreted by Claude/Codex/etc. — no Python execution |
| MCP tool calls (`list_diagram_seeds`, `get_diagram_seed`) | Existing `graphify/serve.py` | Skill markdown invokes via MCP | Already implemented Phase 20 |
| Pure-Python fallback (scene element layout) | `graphify/excalidraw.py` (Python lib) | — | Deterministic Python, no agent-side reasoning needed |
| Vault write (write file at output path) | Skill (via mcp-obsidian) OR Python fallback (via `excalidraw.py` writer) | Both paths share path-confinement via `validate_vault_path` | Two paths converge on same security primitive |
| Profile schema (`layout_type`, `output_path`) | `graphify/profile.py` | — | Profile validators are project-local Python |
| Install / uninstall / packaging | `graphify/__main__.py` `_PLATFORM_CONFIG` + `pyproject.toml` `package_data` | — | Existing dict-driven flow; only entry add needed |
| `.mcp.json` snippet | Skill markdown (literal text) | — | Documentation only — graphify never touches user `.mcp.json` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `json` | — | Scene JSON serialization | `[VERIFIED: graphify/excalidraw.py:24]` already in use |
| stdlib `pathlib` | — | Path manipulation, vault confinement | `[VERIFIED]` project-wide convention |
| `graphify.profile.validate_vault_path` | in-repo | Path traversal protection | `[VERIFIED: profile.py:407]` `[CITED: SECURITY.md]` already enforces vault confinement |
| `graphify.profile.safe_frontmatter_value` | in-repo | YAML-safe label/topic injection | `[VERIFIED: profile.py:425+]` covers `:#[]{},`, leading indicators, YAML 1.1 reserved words, control char strip |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `graphify.excalidraw.SCENE_JSON_SKELETON` | in-repo | Base scene dict (`type=excalidraw, version=2, source=graphify, appState.currentItemFontFamily=5`) | `[VERIFIED: excalidraw.py:32–43]` deep-copy and inject `elements[]` for fallback path |
| `graphify.excalidraw.render_stub` | in-repo | Stub markdown shell (frontmatter + sections) | `[VERIFIED: excalidraw.py:46–69]` reuse for fallback file shell |
| `graphify.excalidraw.write_stubs` | in-repo | Atomic vault writer with `force` flag | `[VERIFIED: excalidraw.py:72+]` mirror its pattern for diagram writer |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom Python fallback | Defer everything to mcp_excalidraw | Violates SKILL-06 ordering invariant |
| External layout lib (`graphviz`, `networkx.drawing`, `pydot`) | — | Adds required dep; CONTEXT D-02 forbids non-stdlib numerical libs |

**Installation:** None required. Phase adds zero new Python deps.

**Version verification:** N/A — pure-stdlib + in-repo.

## Architecture Patterns

### System Architecture Diagram

```
                ┌────────────────────────────────────────────────┐
                │  User invokes /excalidraw-diagram (skill)      │
                └─────────────────────┬──────────────────────────┘
                                      │
                                      ▼
                ┌────────────────────────────────────────────────┐
                │  Step 1: MCP list_diagram_seeds (graphify)     │ ──► serve.py:2562
                └─────────────────────┬──────────────────────────┘
                                      │ rows: seed_id, label, layout_type
                                      ▼
                ┌────────────────────────────────────────────────┐
                │  Step 2: User selects seed_id                  │
                └─────────────────────┬──────────────────────────┘
                                      ▼
                ┌────────────────────────────────────────────────┐
                │  Step 3: MCP get_diagram_seed → SeedDict       │ ──► serve.py:2667
                └─────────────────────┬──────────────────────────┘
                                      │ {main_nodes, supporting_nodes,
                                      │  relations, suggested_layout_type,
                                      │  suggested_template, ...}
                                      ▼
                ┌────────────────────────────────────────────────┐
                │  Step 4: Read matching template from vault     │
                │   - mcp-obsidian read_file (primary)           │
                │   - Python file read (fallback)                │
                └─────────────────────┬──────────────────────────┘
                                      ▼
                          ┌──────────────────────────┐
                          │  mcp_excalidraw avail?   │
                          └────────┬───────┬─────────┘
                            YES    │       │   NO
                                   ▼       ▼
                ┌──────────────────────┐  ┌────────────────────────────┐
                │ Step 5a: build via   │  │ Step 5b: pure-Python       │
                │ mcp_excalidraw       │  │  layout_for(layout_type,   │
                │ (skill instructs     │  │     nodes, edges) →        │
                │  agent calls MCP)    │  │  elements[]                │
                └──────────┬───────────┘  │ inject into SCENE_JSON_    │
                           │              │ SKELETON; render via       │
                           │              │ render_stub()-style shell  │
                           │              └────────────┬───────────────┘
                           │                           │
                           ▼                           ▼
                ┌────────────────────────────────────────────────┐
                │  Step 6: Resolve output path                   │
                │   profile.diagram_types[].output_path          │
                │     ?? "Excalidraw/Diagrams/"                  │
                │   filename = {topic}-{layout_type}.excalidraw.md│
                │   validate_vault_path(...) → confined           │
                │   if exists and not force: refuse              │
                └─────────────────────┬──────────────────────────┘
                                      ▼
                ┌────────────────────────────────────────────────┐
                │  Step 7: Write file + report                   │
                │   {seed_id, node_count, template, vault_path}  │
                └────────────────────────────────────────────────┘
```

### Component Responsibilities

| File | New / Existing | Role |
|------|----------------|------|
| `graphify/skill-excalidraw.md` | **NEW** | 7-step pipeline prompt; `.mcp.json` snippet; style rules; guard list |
| `graphify/excalidraw.py` | **EXTEND** | Add `layout_for(layout_type, nodes, edges, **opts) -> list[dict]`; add `write_diagram(vault_dir, seed, profile, force=False) -> Path` |
| `graphify/profile.py` | **EXTEND** | Add `layout_type` + `output_path` to `_VALID_DT_KEYS` and `_DEFAULT_PROFILE.diagram_types` entries |
| `graphify/__main__.py` | **EXTEND** | Add `excalidraw` entry to `_PLATFORM_CONFIG` (per D-05) |
| `pyproject.toml` | **EXTEND** | Add `skill-excalidraw.md` to `[tool.setuptools.package-data] graphify` glob |
| `MANIFEST.in` | **N/A** | Project has no `MANIFEST.in` (verified absent); `package-data` in `pyproject.toml` is the single source of truth |
| `tests/test_install.py` | **EXTEND** | Add `test_install_excalidraw`, `test_uninstall_excalidraw`, `test_install_excalidraw_idempotent`, `test_existing_platforms_unchanged` |
| `tests/test_init_templates.py` | **EXTEND** | OR new `tests/test_excalidraw_layout.py` — fallback path tests for `layout_for` per layout_type |

### Recommended Project Structure
```
graphify/
├── excalidraw.py              # extended: + layout_for, write_diagram
├── skill-excalidraw.md        # NEW (skill prompt)
├── __main__.py                # extended: + excalidraw entry in _PLATFORM_CONFIG
├── profile.py                 # extended: + layout_type, output_path schema
└── ...
tests/
├── test_install.py            # extended: 4 new tests
├── test_excalidraw_layout.py  # NEW: layout_for + write_diagram tests
└── ...
```

### Pattern 1: Platform entry — `antigravity` precedent
**What:** Existing platform with `claude_md: False`, `commands_enabled: False` — exactly the shape D-05 prescribes.
**Source:** `graphify/__main__.py:131–140`
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
The new entry must include `commands_src_dir` and `commands_dst` keys (even if `None` / unused) because `_install_commands(cfg, ...)` reads them. `[VERIFIED: __main__.py:280–283]`

### Pattern 2: Idempotent install via `shutil.copy`
**What:** `shutil.copy(skill_src, skill_dst)` overwrites in place. Re-run = same content rewritten. No append, no duplication.
**Source:** `graphify/__main__.py:256–259`
```python
skill_dst = Path.home() / cfg["skill_dst"]
skill_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(skill_src, skill_dst)
(skill_dst.parent / ".graphify_version").write_text(__version__, encoding="utf-8")
```
D-06's "overwrites only if content differs" is **stricter** than the existing pattern but compatible: if the planner wants strict content-diff idempotency for the new platform only, it can wrap the copy with a hash check. The existing precedent (overwrite-in-place) already satisfies "running twice is safe."

### Pattern 3: Path confinement via `validate_vault_path`
**What:** All vault writes pass through `profile.validate_vault_path(candidate, vault_dir)` which raises `ValueError` if the resolved path escapes the vault root.
**Source:** `graphify/profile.py:407–422`
```python
target = validate_vault_path(rel_path, vault_root)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(body, encoding="utf-8")
```
Used by `excalidraw.py::write_stubs`. The new diagram writer MUST follow the same pattern. Tests must include a path-traversal-blocked case (precedent: `test_write_stubs_path_traversal_blocked`).

### Pattern 4: Scene element shapes
**What:** Excalidraw scene element minimum schema for the fallback path.
```json
{
  "id": "elem-001",
  "type": "rectangle",  // or "ellipse", "diamond", "arrow", "text"
  "x": 0, "y": 0,
  "width": 200, "height": 80,
  "strokeColor": "#1e1e2e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "seed": 1,
  "version": 1,
  "fontFamily": 5
}
```
For text labels add: `"text": "<label>"`, `"fontSize": 20`, `"textAlign": "center"`.
For arrows add: `"startBinding": {"elementId": "<src-id>", ...}`, `"endBinding": {"elementId": "<dst-id>", ...}`, `"points": [[0,0], [dx,dy]]`.

`[CITED: graphify/excalidraw.py:32–43 SCENE_JSON_SKELETON]`
`[ASSUMED: full element field list]` — the minimum set above is what Excalidraw needs to render; richer fields are optional. Verify against an Excalidraw plugin sample export when implementing if uncertainty remains; not a blocker for planning since fallback output only needs to be parseable, not pixel-perfect.

### Anti-Patterns to Avoid
- **Importing `mcp_excalidraw` from Python.** Never. Skill prompt only.
- **Using `lzstring` to compress the scene JSON.** Forbidden by `tests/test_denylist.py:83` — CI will fail.
- **Deriving element IDs from labels** (e.g., `id = slugify(label)`). Per D-12 guard list. Use deterministic counter: `f"elem-{i:04d}"`.
- **Auto-merging user `.mcp.json`.** Per D-11. Snippet is documentation in the skill, not a write target.
- **Writing frontmatter directly in the skill** instead of going through `render_stub`. Per D-12.
- **Per-run randomness** in fallback layout — breaks D-02 byte-identical determinism.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault path safety | Custom `Path.resolve` + parent walk | `profile.validate_vault_path` | Already covers symlink + `..` escape; integrated with existing tests |
| YAML-safe topic strings | `quote = '"' + s + '"'` | `profile.safe_frontmatter_value` | Handles 8 categories of edge cases (PROF-21 WR-01) |
| Scene markdown shell | Hand-build frontmatter + headings | `excalidraw.render_stub` (or extracted helper) | Already enforces `compress: false`, `excalidraw-plugin: parsed`, headings |
| Atomic vault write w/ force | New writer | `excalidraw.write_stubs` pattern (path confine → mkdir parents → write_text) | Already battle-tested in Phase 21 tests |
| Platform install loop | New install function | Existing dict-driven `install()` | Adding entry to `_PLATFORM_CONFIG` propagates automatically |
| Slug generation for `{topic}` | New regex | `safe_frontmatter_value` first, then `re.sub(r"[^a-z0-9-]+", "-", s.lower())` keeps it 5 lines | Project pattern; no slugify dep |

**Key insight:** Phase 22 is mostly *gluing existing primitives*. The only genuinely new code is `layout_for(layout_type, nodes, edges)` (≤ ~150 LOC) and the skill markdown.

## Runtime State Inventory

This is a greenfield additive phase (new skill file, new platform entry, new layout function). No rename/refactor.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — phase only adds new files. | None |
| Live service config | None — `.mcp.json` snippet is documentation, not written by graphify. | None |
| OS-registered state | New skill file at `~/.claude/skills/excalidraw-diagram/SKILL.md` is *created* by `graphify install excalidraw` (per D-05) — not an existing registration to migrate. | None pre-Phase-22; user re-runs `graphify install excalidraw` to register. |
| Secrets/env vars | None. | None |
| Build artifacts | `pyproject.toml` `package-data` glob currently lists explicit filenames (no wildcard for `skill-*.md`). New file MUST be added explicitly to `[tool.setuptools.package-data] graphify`, otherwise it ships missing from the wheel and `install()` fails at L253: `"error: ... not found in package - reinstall graphify"`. | Add `"skill-excalidraw.md"` to the list. |

## Common Pitfalls

### Pitfall 1: Forgetting `package-data` glob update
**What goes wrong:** Skill file works locally but missing from `pip install graphifyy` wheel.
**Why it happens:** Project does not use a wildcard glob in `pyproject.toml`; every `skill-*.md` is listed explicitly. `[VERIFIED: pyproject.toml]`
**How to avoid:** Plan 22-02 explicitly adds `"skill-excalidraw.md"` to the `graphify` package-data list. Add a test (`test_all_skill_files_exist_in_package` precedent at `tests/test_install.py:91+`) that asserts the file is bundled.
**Warning signs:** `error: skill-excalidraw.md not found in package - reinstall graphify` at install time.

### Pitfall 2: Platform name collision in CLAUDE.md cleanup loop
**What goes wrong:** Existing global cleanup at `__main__.py:~1157` iterates `set(cfg["skill_dst"] for cfg in _PLATFORM_CONFIG.values())`. Two entries (`claude` and `excalidraw`) both write under `.claude/skills/...` (different subfolders: `graphify/` vs `excalidraw-diagram/`) — verify the cleanup loop does NOT delete the wrong one.
**Why it happens:** Subfolder is part of `skill_dst` so they're distinct paths, but if any code uses parent-folder pruning the conflict surfaces.
**How to avoid:** Plan 22-02 includes `test_install_excalidraw_does_not_remove_claude_skill` (and inverse). D-07 already mandates this assertion.

### Pitfall 3: `layout_type` schema gap
**What goes wrong:** D-09 references `profile.diagram_types[].output_path` and CONTEXT presumes `layout_type` exists per entry. **Both fields are absent from the current schema** (`profile.py:365–367` `_VALID_DT_KEYS` = `{name, template_path, trigger_node_types, trigger_tags, min_main_nodes, naming_pattern}`).
**Why it happens:** Phase 21 implemented schema-up-to-recommender. Phase 22 needs additional fields to drive layout dispatch and output path resolution.
**How to avoid:** Plan 22-01 adds `layout_type` and `output_path` to `_VALID_DT_KEYS` + adds default values to each of the 6 entries in `_DEFAULT_PROFILE.diagram_types`. Default `layout_type` is the same string as `name` (the 6 names match `_VALID_LAYOUT_TYPES` in `seed.py:35–42`). Default `output_path` is `"Excalidraw/Diagrams/"`. Validator must accept `output_path` as `str` and reject path-traversal at validation time (or defer to write-time `validate_vault_path`). Update `profile.py` validator unit tests.
**Warning signs:** `validate_profile` returns `"diagram_types[i] unknown key 'layout_type'"`.

### Pitfall 4: SeedDict already carries `suggested_layout_type` — don't re-derive
**What goes wrong:** Fallback re-runs `_select_layout_type` instead of trusting `seed["suggested_layout_type"]`.
**Why it happens:** Plumbing oversight.
**How to avoid:** Fallback reads `seed["suggested_layout_type"]` directly. If the value is not in `_VALID_LAYOUT_TYPES`, fall back to `mind-map`.
**Source:** `seed.py:297` writes `"suggested_layout_type": layout_type`.

### Pitfall 5: `compress: false` test will catch any LZ-String reach
**What goes wrong:** Importing `lzstring` even transitively fails CI.
**Source:** `tests/test_denylist.py:83 test_no_lzstring_import_anywhere`.
**How to avoid:** Never import `lzstring`. Document explicitly in skill guard list.

### Pitfall 6: `cfg["commands_src_dir"]` required key
**What goes wrong:** New entry omits `commands_src_dir`; install handler crashes on `_install_commands(cfg, commands_src)` even when `commands_enabled: False`.
**Source:** `__main__.py:280–283` calls `_install_commands` only inside `if not no_commands:` but `commands_src_dir` may still be referenced.
**How to avoid:** New entry sets `"commands_src_dir": "commands"`, `"commands_dst": None`, `"commands_enabled": False` — same shape as `antigravity`.

## Code Examples

### `_PLATFORM_CONFIG` entry (Plan 22-02)
```python
# graphify/__main__.py — append after "antigravity" entry, before "windows"
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

### Fallback layout signature (Plan 22-01)
```python
# graphify/excalidraw.py
_VALID_LAYOUT_TYPES = {
    "architecture", "workflow", "mind-map",
    "cuadro-sinoptico", "repository-components", "glossary-graph",
}

def layout_for(
    layout_type: str,
    nodes: list[dict],   # [{"id": ..., "label": ..., "element_id": ...}, ...]
    edges: list[dict],   # [{"source": ..., "target": ..., "relation": ...}, ...]
) -> list[dict]:
    """Return Excalidraw scene elements[] for the given layout type.

    Deterministic: same inputs → byte-identical output (D-02).
    Dispatches to _layout_<name> helpers; unknown layout_type falls back
    to _layout_mind_map.
    """
    dispatch = {
        "architecture":          _layout_grid,        # community-clustered grid
        "workflow":              _layout_horizontal,  # left→right pipeline
        "mind-map":              _layout_radial,      # hub-and-spoke
        "cuadro-sinoptico":      _layout_tree,        # left-anchored hierarchy
        "repository-components": _layout_grid,
        "glossary-graph":        _layout_radial,
    }
    return dispatch.get(layout_type, _layout_radial)(nodes, edges)
```

### Diagram writer (Plan 22-01)
```python
# graphify/excalidraw.py
def write_diagram(
    vault_dir: str | Path,
    seed: dict,
    profile: dict,
    force: bool = False,
) -> Path:
    """SKILL-06 fallback: write a complete .excalidraw.md from a SeedDict.

    Returns the written Path. Raises ValueError on path-traversal or
    FileExistsError when target exists and force is False.
    """
    layout_type = seed.get("suggested_layout_type", "mind-map")
    if layout_type not in _VALID_LAYOUT_TYPES:
        layout_type = "mind-map"

    # Resolve output_path from profile.diagram_types matching this layout_type
    dt = next(
        (dt for dt in profile.get("diagram_types", [])
         if dt.get("layout_type") == layout_type or dt.get("name") == layout_type),
        {},
    )
    out_dir = dt.get("output_path") or "Excalidraw/Diagrams"
    topic = _slugify(seed.get("main_node_label", seed.get("seed_id", "diagram")))
    fname = f"{topic}-{layout_type}.excalidraw.md"

    rel = f"{out_dir.rstrip('/')}/{fname}"
    target = validate_vault_path(rel, vault_dir)
    if target.exists() and not force:
        raise FileExistsError(f"{target} exists; pass force=True to overwrite")

    nodes = seed.get("main_nodes", []) + seed.get("supporting_nodes", [])
    edges = seed.get("relations", [])
    elements = layout_for(layout_type, nodes, edges)

    scene = dict(SCENE_JSON_SKELETON)
    scene["elements"] = elements
    body = _render_diagram_md({"name": layout_type}, scene)  # adapt render_stub

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target
```

### Test pattern — install/uninstall idempotent (Plan 22-02)
```python
# tests/test_install.py — append
def test_install_excalidraw(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="excalidraw")
    assert (tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md").exists()

def test_install_excalidraw_idempotent(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="excalidraw")
        install(platform="excalidraw")
    skill = tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md"
    assert skill.exists()
    # Content matches packaged source byte-for-byte (overwrite-in-place idempotency)
    pkg_src = (Path(__import__("graphify").__file__).parent / "skill-excalidraw.md").read_text()
    assert skill.read_text() == pkg_src

def test_uninstall_excalidraw(tmp_path):
    from graphify.__main__ import install, uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="excalidraw")
        uninstall(platform="excalidraw")
    assert not (tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md").exists()

def test_uninstall_excalidraw_idempotent(tmp_path):
    from graphify.__main__ import uninstall
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        uninstall(platform="excalidraw")  # no-op when not installed
        uninstall(platform="excalidraw")  # no-op again

def test_install_excalidraw_does_not_touch_claude_skill(tmp_path):
    from graphify.__main__ import install
    with patch("graphify.__main__.Path.home", return_value=tmp_path):
        install(platform="claude")
        install(platform="excalidraw")
    assert (tmp_path / ".claude" / "skills" / "graphify" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "excalidraw-diagram" / "SKILL.md").exists()

def test_excalidraw_skill_in_package():
    import graphify
    pkg = Path(graphify.__file__).parent
    assert (pkg / "skill-excalidraw.md").exists()
```

### Test pattern — fallback layout (Plan 22-01)
```python
# tests/test_excalidraw_layout.py
import json, re
from graphify.excalidraw import layout_for, write_diagram, _VALID_LAYOUT_TYPES

def test_layout_for_all_six_layout_types():
    nodes = [{"id": f"n{i}", "label": f"N{i}", "element_id": f"elem-{i:04d}"} for i in range(5)]
    edges = [{"source": "n0", "target": "n1", "relation": "calls", "confidence": "EXTRACTED"}]
    for lt in _VALID_LAYOUT_TYPES:
        elems = layout_for(lt, nodes, edges)
        assert len(elems) >= len(nodes), f"{lt}: missing node elements"
        ids = [e["id"] for e in elems]
        assert len(ids) == len(set(ids)), f"{lt}: duplicate element ids"

def test_layout_for_is_deterministic():
    nodes = [{"id": "a", "label": "A", "element_id": "elem-0001"}]
    a = layout_for("mind-map", nodes, [])
    b = layout_for("mind-map", nodes, [])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

def test_layout_for_unknown_falls_back_to_mind_map():
    nodes = [{"id": "a", "label": "A", "element_id": "elem-0001"}]
    assert layout_for("not-a-layout", nodes, []) == layout_for("mind-map", nodes, [])

def test_write_diagram_collision_refuses(tmp_path):
    seed = {"seed_id": "x", "main_node_label": "X", "main_nodes": [], "supporting_nodes": [],
            "relations": [], "suggested_layout_type": "mind-map"}
    profile = {"diagram_types": [{"name": "mind-map", "layout_type": "mind-map", "output_path": "Excalidraw/Diagrams"}]}
    write_diagram(tmp_path, seed, profile)
    import pytest
    with pytest.raises(FileExistsError):
        write_diagram(tmp_path, seed, profile)
    write_diagram(tmp_path, seed, profile, force=True)  # ok with force

def test_write_diagram_path_confined(tmp_path):
    import pytest
    seed = {"seed_id": "x", "main_node_label": "X", "main_nodes": [], "supporting_nodes": [],
            "relations": [], "suggested_layout_type": "mind-map"}
    profile = {"diagram_types": [{"name": "mind-map", "layout_type": "mind-map",
                                  "output_path": "../../etc"}]}
    with pytest.raises(ValueError, match="escape vault directory"):
        write_diagram(tmp_path, seed, profile)

def test_write_diagram_compress_false(tmp_path):
    seed = {"seed_id": "x", "main_node_label": "X", "main_nodes": [], "supporting_nodes": [],
            "relations": [], "suggested_layout_type": "mind-map"}
    profile = {"diagram_types": [{"name": "mind-map", "layout_type": "mind-map", "output_path": "Excalidraw/Diagrams"}]}
    out = write_diagram(tmp_path, seed, profile)
    body = out.read_text()
    assert "compress: false" in body
    assert "excalidraw-plugin: parsed" in body
    m = re.search(r"```json\n(.+?)\n```", body, re.S)
    scene = json.loads(m.group(1))
    assert scene["appState"]["currentItemFontFamily"] == 5
    assert scene["type"] == "excalidraw" and scene["version"] == 2
```

### Skill markdown skeleton (Plan 22-01)
```markdown
---
name: excalidraw-diagram
description: Build an Excalidraw diagram from a graphify diagram seed and write it into the Obsidian vault.
trigger: /excalidraw-diagram
---

# /excalidraw-diagram

Pick a graphify diagram seed, build the Excalidraw scene from it, and write the
result into the vault under `Excalidraw/Diagrams/`. Falls back to a pure-Python
deterministic layout when `mcp_excalidraw` is not configured.

## Required MCP servers

Add this to your `.mcp.json` (do NOT let me edit your `.mcp.json` — copy this
yourself):

```jsonc
{
  "mcpServers": {
    "graphify": { "command": "graphify", "args": ["serve"] },
    "obsidian": { "command": "uvx", "args": ["mcp-obsidian"] },
    "excalidraw": { "command": "npx", "args": ["-y", "@excalidraw/mcp-server"] }
  }
}
```

## What I do (7 steps)

1. Call MCP `list_diagram_seeds` …
2. Show you the seeds and ask which `seed_id` to use …
3. Call MCP `get_diagram_seed(seed_id)` …
4. Read the matching template …
5. Build the diagram. **Two paths:**
   - **5a (preferred):** call `mcp_excalidraw` to add elements + export scene.
   - **5b (fallback):** if `mcp_excalidraw` is not available, run
     `python -m graphify excalidraw build --seed <seed_id>` (pure-Python
     deterministic layout). I will tell you which path I'm taking.
6. Resolve output path, refuse on collision unless you said `force: true` …
7. Report `seed_id`, `node_count`, `template`, `vault_path`.

## Vault conventions

- Templates live at `Excalidraw/Templates/{name}.excalidraw.md`.
- Diagrams write to `Excalidraw/Diagrams/{topic}-{layout_type}.excalidraw.md`.
- File frontmatter MUST contain `excalidraw-plugin: parsed` and `compress: false`.

## Style rules (locked)

- `fontFamily: 5` (Excalifont) on text elements.
- `strokeColor: "#1e1e2e"`.
- `backgroundColor: "transparent"`.
- `compress: false` always.

## Do not (guard list)

- Do **not** import `lzstring` or compress the scene.
- Do **not** derive element IDs from labels — use deterministic counters.
- Do **not** write frontmatter directly; go through the renderer.
- Do **not** edit `.mcp.json` on the user's behalf.
- Do **not** combine multiple seeds into one diagram (v1.5 limit).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Skill files use sole `name:` frontmatter | Skill files use `name + description + trigger` (and optional `capability_manifest`) | Phase 14 | New skill must follow same shape |
| `_PLATFORM_CONFIG` dict with `claude_md` always True | Mixed: `antigravity` was first `claude_md: False` precedent | Phase 19 | New entry follows `antigravity` shape |
| Compressed Excalidraw scenes | `compress: false` one-way door | Phase 21 | LZ-String forbidden by `tests/test_denylist.py:83` |
| Profile schema 4 keys | 6 keys (added `min_main_nodes`, `naming_pattern`) | Phase 21 | Phase 22 adds 2 more (`layout_type`, `output_path`) — total 8 |

**Deprecated/outdated:**
- `--obsidian-no-commands` flag predated `_PLATFORM_CONFIG.supports`. Don't rely on it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Excalidraw plugin scene element minimum schema (id/type/x/y/w/h/strokeColor/etc.) is sufficient for the plugin to render the file. | Pattern 4 | Pure-Python fallback file opens but renders empty; cosmetic only — file is still valid markdown and the scene JSON is parseable. Mitigation: when implementing, sample a real plugin export once and snapshot a fixture. |
| A2 | `cfg["commands_src_dir"]` is required even when `commands_enabled: False`. | Pitfall 6 | If actually optional, no harm — entry simply has an unused key (matches `antigravity` precedent). |
| A3 | `_PLATFORM_CONFIG` global cleanup at `__main__.py:~1157` is folder-aware. | Pitfall 2 | If it isn't, installing `excalidraw` then uninstalling `claude` (or vice versa) could remove the wrong file. Mitigation: dedicated regression test (`test_install_excalidraw_does_not_touch_claude_skill`). |
| A4 | `output_path` is the right field name for D-09. | Pitfall 3 | If a different name is preferred (`diagram_output_path`?), rename in one place — pure additive change. |

**Confirmation needed before execution:** A4 only — planner should pick a final name when wiring D-09. A1–A3 are mitigated by tests inside the phase plan.

## Open Questions

1. **Should `layout_for` live in `graphify/excalidraw.py` or a new submodule?**
   - What we know: `excalidraw.py` is currently 87 lines; adding 6 layout helpers (~150 LOC) keeps it under 250 LOC.
   - What's unclear: D-03 says reuse the same module, but discretion is granted on placement.
   - Recommendation: keep in `graphify/excalidraw.py`. Below 300 LOC, splitting adds import overhead without payoff.

2. **Should the fallback also expose a CLI subcommand (`graphify excalidraw build --seed <id>`) or only a Python API?**
   - What we know: skill markdown sample above references a CLI; current `__main__.py` exposes `--init-diagram-templates` precedent for one-shot vault writes.
   - What's unclear: whether skills should call the CLI directly (subprocess) or instruct the agent to write via mcp-obsidian using Python output.
   - Recommendation: provide a CLI subcommand for parity with `--init-diagram-templates`. Lets the skill be "just shell out" for the fallback path.

3. **Should `force` be a CLI flag or a skill-prompt argument only?**
   - CONTEXT D-08 calls it a "skill-level argument". If a CLI subcommand is added (Q2), it should accept `--force` for parity.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib (json, pathlib, shutil) | All Phase 22 code | ✓ | 3.10+ | — |
| `pytest` | Tests | ✓ (project test runner) | — | — |
| `graphify` package (in-repo) | Tests + skill install | ✓ | dev | — |
| `mcp_excalidraw` | **Skill runtime only — never imported by Python** | ✗/✓ at user side | — | Pure-Python `layout_for` (the whole point of SKILL-06) |
| `mcp-obsidian` | Skill runtime only | ✗/✓ at user side | — | Python file-system read |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** `mcp_excalidraw`, `mcp-obsidian` — both are user-side MCP servers; the skill instructs the user to add them to `.mcp.json`. Phase 22 ships the fallback so the skill works without them.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (already in project) |
| Config file | `pyproject.toml` (no separate `pytest.ini`) |
| Quick run command | `pytest tests/test_install.py tests/test_excalidraw_layout.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-01 | `graphify install excalidraw` writes skill at expected path | unit | `pytest tests/test_install.py::test_install_excalidraw -x` | ❌ Wave 0 |
| SKILL-01 | Skill file is packaged in wheel | unit | `pytest tests/test_install.py::test_excalidraw_skill_in_package -x` | ❌ Wave 0 |
| SKILL-01 | New `excalidraw` entry exists in `_PLATFORM_CONFIG` | unit | `pytest tests/test_install.py::test_platform_config_has_excalidraw -x` | ❌ Wave 0 |
| SKILL-02 | `graphify uninstall excalidraw` removes skill | unit | `pytest tests/test_install.py::test_uninstall_excalidraw -x` | ❌ Wave 0 |
| SKILL-03 | Install twice = same content (idempotent) | unit | `pytest tests/test_install.py::test_install_excalidraw_idempotent -x` | ❌ Wave 0 |
| SKILL-03 | Uninstall when absent = no-op | unit | `pytest tests/test_install.py::test_uninstall_excalidraw_idempotent -x` | ❌ Wave 0 |
| SKILL-03 (D-07) | Install excalidraw does not affect claude install | unit | `pytest tests/test_install.py::test_install_excalidraw_does_not_touch_claude_skill -x` | ❌ Wave 0 |
| SKILL-04 | Skill file references all 7 pipeline steps + MCP tool names | unit (text grep) | `pytest tests/test_install.py::test_excalidraw_skill_has_seven_steps -x` | ❌ Wave 0 |
| SKILL-04 | Skill references `list_diagram_seeds` and `get_diagram_seed` MCP tools | unit | `pytest tests/test_install.py::test_excalidraw_skill_calls_seed_tools -x` | ❌ Wave 0 |
| SKILL-05 | Skill contains `.mcp.json` snippet block | unit | `pytest tests/test_install.py::test_excalidraw_skill_has_mcp_json -x` | ❌ Wave 0 |
| SKILL-05 | Skill contains style rules (Excalifont 5, `#1e1e2e`, transparent) | unit | `pytest tests/test_install.py::test_excalidraw_skill_has_style_rules -x` | ❌ Wave 0 |
| SKILL-05 | Skill contains guard list (compress:false, no LZ-String, no label-IDs, no multi-seed) | unit | `pytest tests/test_install.py::test_excalidraw_skill_has_guard_list -x` | ❌ Wave 0 |
| SKILL-06 | `layout_for` returns elements for all 6 valid layout types | unit | `pytest tests/test_excalidraw_layout.py::test_layout_for_all_six_layout_types -x` | ❌ Wave 0 |
| SKILL-06 | `layout_for` is byte-deterministic | unit | `pytest tests/test_excalidraw_layout.py::test_layout_for_is_deterministic -x` | ❌ Wave 0 |
| SKILL-06 | Unknown layout falls back to `mind-map` | unit | `pytest tests/test_excalidraw_layout.py::test_layout_for_unknown_falls_back_to_mind_map -x` | ❌ Wave 0 |
| SKILL-06 | `write_diagram` refuses collision; force=True overwrites | unit | `pytest tests/test_excalidraw_layout.py::test_write_diagram_collision_refuses -x` | ❌ Wave 0 |
| SKILL-06 | `write_diagram` blocks path traversal | unit | `pytest tests/test_excalidraw_layout.py::test_write_diagram_path_confined -x` | ❌ Wave 0 |
| SKILL-06 | Output file contains `compress: false`, `excalidraw-plugin: parsed`, fontFamily 5, valid scene JSON | unit | `pytest tests/test_excalidraw_layout.py::test_write_diagram_compress_false -x` | ❌ Wave 0 |
| SKILL-06 (ordering) | LZ-String denylist still passes after Phase 22 | unit | `pytest tests/test_denylist.py::test_no_lzstring_import_anywhere -x` | ✅ exists |
| Profile schema | `layout_type` and `output_path` accepted by `validate_profile` | unit | `pytest tests/test_profile.py::test_diagram_types_layout_type_accepted -x` | ❌ Wave 0 |
| Profile schema | Path-traversal in `output_path` rejected at validation OR write time | unit | `pytest tests/test_profile.py::test_diagram_types_output_path_traversal -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_install.py tests/test_excalidraw_layout.py tests/test_profile.py -x -q`
- **Per wave merge:** `pytest tests/ -q` (full suite, < 60s)
- **Phase gate:** Full suite green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_excalidraw_layout.py` — covers SKILL-06 (new file)
- [ ] Test additions in `tests/test_install.py` — covers SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05 (extension)
- [ ] Test additions in `tests/test_profile.py` — covers `layout_type` + `output_path` schema (extension)
- [ ] No framework install needed; pytest already configured.

## Security Domain

Project security baseline: `graphify/security.py` for URL/label sanitization; `graphify/profile.py::validate_vault_path` for filesystem confinement; `tests/test_denylist.py` for forbidden imports.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local CLI / skill prompt |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes | `validate_profile`, `safe_frontmatter_value`, `validate_vault_path` |
| V6 Cryptography | no | N/A |
| V12 File Handling | yes | Path confinement via `validate_vault_path`; existing `write_stubs` precedent |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via profile `output_path` (e.g., `../../etc/`) | Tampering | `validate_vault_path` at write time + a profile-validator check |
| YAML injection via `{topic}` in filename → frontmatter | Tampering | `safe_frontmatter_value` on label before slugification |
| LZ-String supply-chain reach | Tampering | `tests/test_denylist.py::test_no_lzstring_import_anywhere` already enforces |
| Skill file overwriting unrelated file in `~/.claude/skills/...` | Tampering | Distinct subfolder (`excalidraw-diagram` vs `graphify`); regression test asserts |
| Untrusted MCP server in `.mcp.json` snippet | Tampering | Snippet is documentation; user copies it themselves; no auto-write (D-11) |

## Project Constraints (from CLAUDE.md)

- Python 3.10+ — works on CI (3.10 + 3.12).
- **No new required dependencies.** Optional deps must remain optional.
- **Backward compatible:** existing platforms continue to install/uninstall identically.
- Pure unit tests, side-effects confined to `tmp_path`.
- All file paths through `security.py` / `profile.py::validate_vault_path`.
- Template placeholders sanitized via `safe_frontmatter_value` (no injection via node labels).
- Tests under `tests/test_<module>.py`, one file per module.
- Skill files packaged via `pyproject.toml` `[tool.setuptools.package-data] graphify` (no `MANIFEST.in` in this project — verified absent).

## Sources

### Primary (HIGH confidence — in-repo verified)
- `graphify/__main__.py:49–145` — `_PLATFORM_CONFIG` dict shape (10 entries).
- `graphify/__main__.py:230–310` — `install()` / `uninstall()` handlers (dict-driven, generic).
- `graphify/excalidraw.py:1–100` — `SCENE_JSON_SKELETON`, `render_stub`, `write_stubs`, `compress: false` enforcement.
- `graphify/profile.py:74–95` — `_DEFAULT_PROFILE.diagram_types` (6 entries, current schema).
- `graphify/profile.py:359–390` — `validate_profile` `_VALID_DT_KEYS` (6 keys; missing `layout_type`, `output_path`).
- `graphify/profile.py:407–422` — `validate_vault_path`.
- `graphify/profile.py:425+` — `safe_frontmatter_value`.
- `graphify/seed.py:35–46` — `_VALID_LAYOUT_TYPES` (the 6 canonical names).
- `graphify/seed.py:139–304` — `_select_layout_type` + SeedDict construction.
- `graphify/serve.py:2553–2740` — `_run_list_diagram_seeds_core`, `_run_get_diagram_seed_core`.
- `graphify/skill.md:1–6` — skill frontmatter shape (`name`, `description`, `trigger`).
- `graphify/skill-codex.md:1–5` — same.
- `tests/test_install.py:1–100, 142–250, 393–429` — install/uninstall idempotency precedent.
- `tests/test_init_templates.py:1–120` — fallback path test patterns (`test_render_stub_*`, `test_write_stubs_path_traversal_blocked`).
- `tests/test_denylist.py:83+` — LZ-String denylist guard.
- `pyproject.toml [tool.setuptools.package-data]` — explicit skill-file list (no wildcard).
- `MANIFEST.in` — verified absent (no file in repo root).

### Secondary (MEDIUM confidence)
- Excalidraw scene element schema — derived from existing `SCENE_JSON_SKELETON` and Phase 21 `test_render_stub_scene_json_parses`. Sufficient for valid file generation; full element field set is `[ASSUMED]`.

### Tertiary (LOW confidence)
- None — all claims grounded in repo files.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all in-repo, verified.
- Architecture: HIGH — every component already exists or has direct precedent.
- Pitfalls: HIGH — all six grounded in specific file/line citations.
- Excalidraw scene element fields: MEDIUM — A1 in Assumptions Log.

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (30 days; in-repo APIs are stable).

## RESEARCH COMPLETE

**Phase:** 22 - excalidraw-skill-vault-bridge
**Confidence:** HIGH

### Key Findings
- Phase 22 is glue-work: skill markdown + one `_PLATFORM_CONFIG` entry + one new function (`layout_for`) + profile schema extension. Existing dict-driven install handler needs **zero changes** (verified via `antigravity` precedent at `__main__.py:131–139`).
- Profile schema **gap**: `layout_type` and `output_path` are NOT in current `_VALID_DT_KEYS` (only 6 keys). Plan 22-01 must extend the validator AND default-profile entries — small change but a hard prerequisite for D-09.
- The 6 canonical `layout_type` values are identical to the 6 `diagram_types[].name` values (`seed.py:35–42` matches `profile.py:74–95`). Mapping is 1-to-1.
- `pyproject.toml` lists every `skill-*.md` explicitly (no wildcard). Adding `skill-excalidraw.md` to `[tool.setuptools.package-data] graphify` is mandatory, otherwise install fails at runtime.
- LZ-String denylist test already exists (`tests/test_denylist.py:83`) — Phase 22 just needs to not break it.
- Pure-Python fallback can read `seed["suggested_layout_type"]` directly — don't re-derive layout.

### File Created
`.planning/phases/22-excalidraw-skill-vault-bridge/22-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All in-repo, citations to file/line |
| Architecture | HIGH | Direct precedents (antigravity, write_stubs) |
| Pitfalls | HIGH | Six pitfalls all grounded in specific file/line |
| Test patterns | HIGH | Phase 21 `test_init_templates.py` patterns directly applicable |
| Excalidraw scene element fields | MEDIUM | Schema sketched from `SCENE_JSON_SKELETON` + Phase 21 tests; full field list assumed |

### Open Questions
1. Module placement of `layout_for` (in-place vs new submodule) — recommend in-place per D-03.
2. CLI subcommand for fallback (`graphify excalidraw build --seed <id>`) — recommend yes, parity with `--init-diagram-templates`.
3. Final name of the profile field for diagram output path — recommend `output_path`.

### Ready for Planning
Research complete. Planner can author 22-01 (skill + fallback + schema) and 22-02 (platform entry + packaging + tests).
