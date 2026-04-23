# Phase 21: Profile Extension & Template Bootstrap - Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 7 (3 modify, 1 new-optional module, 2 new tests, 2 modify tests)
**Analogs found:** 7/7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/profile.py` (MODIFY) | config / validator | request-response (dict in → errors out) | `graphify/profile.py` self (tag_taxonomy + topology.god_node sections) | exact (same-file extension) |
| `graphify/seed.py` (MODIFY: `build_seed` + new `_select_template_from_profile`) | service | transform (graph + profile → seed dict) | `graphify/seed.py::build_seed` at line 196; `_TEMPLATE_MAP` at line 44 | exact |
| `graphify/__main__.py` (MODIFY: new `--init-diagram-templates` block) | CLI dispatch | request-response | `graphify/__main__.py::--diagram-seeds` at line 1379 | exact |
| `graphify/excalidraw.py` (NEW, optional) | utility | transform (config → stub string) | `graphify/profile.py::_dump_frontmatter` (line 449) + `seed.py::_write_atomic` (line 83) | role-match (greenfield composition) |
| `tests/test_profile.py` (MODIFY) | test | unit | `tests/test_profile.py` existing tag_taxonomy tests | exact |
| `tests/test_seed.py` (MODIFY) | test | unit | `tests/test_seed.py` existing build_seed tests | exact |
| `tests/test_init_templates.py` (NEW) | test | integration (CLI / tmp_path) | `tests/test_seed.py::build_all_seeds` integration test | role-match |
| `tests/test_denylist.py` (NEW) | test | architectural (regex over source) | none existing — first architectural test in repo | no analog (use RESEARCH.md Example 6) |

## Pattern Assignments

### `graphify/profile.py` (config extension — PROF-01/02/03)

**Analog:** `graphify/profile.py` self — the three existing sections `tag_taxonomy`, `topology.god_node`, and `merge.field_policies` are direct structural precedents for `diagram_types`.

**Pattern A — `_VALID_TOP_LEVEL_KEYS` extension** (profile.py lines 81-84):
```python
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync",
    # ADD: "diagram_types",
}
```

**Pattern B — `_DEFAULT_PROFILE` entry** (profile.py lines 34-73, analogous to `tag_taxonomy` block at 65-70):
Extend the dict with a `"diagram_types"` key containing 6 sub-dicts keyed by D-05 names (`architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`). Per-entry fields per D-04.

**Pattern C — Nested-entry validator** (profile.py lines 275-281, `tag_taxonomy` pattern):
```python
tag_taxonomy = profile.get("tag_taxonomy")
if tag_taxonomy is not None:
    if not isinstance(tag_taxonomy, dict):
        errors.append("'tag_taxonomy' must be a mapping (dict)")
    else:
        for ns, values in tag_taxonomy.items():
            if not isinstance(ns, str):
                errors.append(f"tag_taxonomy namespace key must be a string, got {type(ns).__name__}")
            elif not isinstance(values, list):
                errors.append(f"tag_taxonomy.{ns} must be a list of strings")
            elif not all(isinstance(v, str) for v in values):
                errors.append(f"tag_taxonomy.{ns} must contain only strings")
```
Apply same accumulator shape to `diagram_types` — outer dict check, then per-entry field checks.

**Pattern D — Bool-before-int guard for `min_main_nodes`** (profile.py `topology.god_node.top_n`, the exact pattern noted at lines 249-250 / shown in slice above):
```python
# bool-before-int guard (T-3-03) — bool is a subclass of int in Python
if isinstance(top_n, bool) or not isinstance(top_n, int):
    errors.append(
        f"topology.god_node.top_n must be an integer "
        f"(got {type(top_n).__name__})"
    )
elif top_n < 0:
    errors.append(f"topology.god_node.top_n must be ≥ 0 (got {top_n})")
```
Apply verbatim to `diagram_types.{entry}.min_main_nodes`.

**Pattern E — Path-traversal guard for `template_path`** (profile.py `folder_mapping` validator, visible in slice around lines 350+):
```python
elif ".." in path_val:
    errors.append(
        f"folder_mapping.{name} contains '..' — "
        "path traversal sequences are not allowed in folder mappings"
    )
elif Path(path_val).is_absolute():
    errors.append(f"folder_mapping.{name} is an absolute path — ...")
```
Apply to `diagram_types.{entry}.template_path`.

**Reusable helpers (do not re-implement):**
- `_deep_merge` (line 121) — handles `diagram_types` default fallback automatically.
- `validate_vault_path` (line 353) — confines template writes; use at WRITE time in __main__.py init block, not in the validator.
- `safe_filename` (line 399) — for `naming_pattern` `{topic}` expansion sanitization.
- `safe_frontmatter_value` (line 376) + `_dump_frontmatter` (line 449) — for stub frontmatter emission.

---

### `graphify/seed.py` (MODIFY — PROF-02 first reader + PROF-04 recommender)

**Analog:** `seed.py::build_seed` (line 196) and `_TEMPLATE_MAP` lookup at line 234.

**Pattern — Template assignment insertion point** (current, line ~234):
```python
layout_type = _select_layout_type(subG, main_nodes, layout_hint)
# current: return {... "suggested_template": _TEMPLATE_MAP[layout_type], ...}
```

**New pattern (Phase 21 insertion, D-08 resolution order):**
```python
# NEW: profile-first recommender (PROF-04). Wrap the _TEMPLATE_MAP fallback.
template = (
    _select_template_from_profile(profile, main_nodes, community_tags)
    or _TEMPLATE_MAP.get(layout_type)
    or "mind-map.excalidraw.md"  # built-in fallback per D-08
)
```

**New helper shape** (`_select_template_from_profile`) — OR-match per D-06, tiebreak by `min_main_nodes` desc then declaration order per D-07. Accept `profile: dict | None` and return early `None` on missing/absent section (PROF-04 "never throws"). Signature:
```python
def _select_template_from_profile(
    profile: dict | None,
    main_nodes: list[dict],
    community_tags: list[str] | None = None,
) -> str | None: ...
```

**Call-site update:** `build_seed` signature gains an optional `profile: dict | None = None` parameter. Caller in `build_all_seeds` passes `profile or {}`.

**Reusable helpers (do not re-implement):**
- `_element_id` (line 53), `_version_nonce` (line 61) — for future stub elements; moot for D-01 empty stubs.
- `_write_atomic` (line 83) — reuse verbatim for stub file writes from `__main__.py` init block.

**Do NOT touch:** Tag write-back block (lines 559-569) — already correct, already uses `compute_merge_plan`.

---

### `graphify/__main__.py` (MODIFY — TMPL-01..05 CLI dispatch)

**Analog:** `--diagram-seeds` dispatch at line 1379 (exact pattern for new `--init-diagram-templates`).

**Pattern — Raw sys.argv parsing loop** (verbatim shape from --diagram-seeds, ~lines 1380-1400):
```python
if cmd == "--diagram-seeds":
    graph_path = "graphify-out/graph.json"
    vault_path: Path | None = None
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--vault" and i + 1 < len(args):
            vault_path = Path(args[i + 1]); i += 2
        elif args[i].startswith("--vault="):
            vault_path = Path(args[i].split("=", 1)[1]); i += 1
        else:
            print(f"error: unknown --diagram-seeds option: {args[i]}", file=sys.stderr)
            sys.exit(2)
```

**Adaptation for `--init-diagram-templates`:** same while-loop shape; add `--force` boolean branch (no trailing value); require `--vault` (error exit 2 if missing, matching existing error style).

**Pattern — Error reporting and exit codes** (existing convention in --diagram-seeds):
```python
print(f"error: unknown --init-diagram-templates option: {args[i]}", file=sys.stderr); sys.exit(2)
# success path:
print(f"[graphify] init-diagram-templates: wrote {n_wrote}, skipped {n_skipped}. Use --force to overwrite.")
sys.exit(0)
```

**Pattern — Write loop body** (compose reused helpers):
```python
from graphify.profile import load_profile, validate_vault_path
from graphify.seed import _write_atomic  # reuse atomic writer

profile = load_profile(vault_path)
diagram_types = profile.get("diagram_types", {})  # always present via _DEFAULT_PROFILE
n_wrote = n_skipped = 0
for type_name, entry in diagram_types.items():
    rel = entry.get("template_path") or f"Excalidraw/Templates/{type_name}.excalidraw.md"
    resolved = validate_vault_path(rel, vault_path)
    if resolved.exists() and not force:
        n_skipped += 1
        continue
    content = _render_excalidraw_stub(type_name)  # from graphify.excalidraw
    _write_atomic(resolved, content)
    n_wrote += 1
```

---

### `graphify/excalidraw.py` (NEW module — stub generation)

**No direct analog** (greenfield). Compose from:
- `profile.py::_dump_frontmatter` (line 449) — for frontmatter rendering.
- `profile.py::safe_frontmatter_value` (line 376) — implicitly invoked by `_dump_frontmatter` for tag strings.
- stdlib `json.dumps` — for scene JSON (use `separators=(",", ":")` to match the compact shape shown in CONTEXT.md specifics).

**Suggested public API:**
```python
def render_stub(type_name: str) -> str: ...
def _scene_json(appState_extras: dict | None = None) -> str: ...
```

**Byte-fixed scene JSON** (per CONTEXT.md specifics + RESEARCH.md rule 5):
```python
_SCENE = {
    "type": "excalidraw",
    "version": 2,
    "source": "graphify",
    "elements": [],
    "appState": {
        "viewBackgroundColor": "#ffffff",
        "gridSize": None,          # serialize as JSON null
        "currentItemFontFamily": 5 # Excalifont, per D-02
    },
    "files": {},
}
```

**Frontmatter fields** (per D-02, emitted via reused `_dump_frontmatter`):
```python
fields = {
    "excalidraw-plugin": "parsed",
    "compress": False,          # emits "compress: false"
    "tags": [type_name],        # YAML block list via _dump_frontmatter
}
```

**Full stub shape** (per RESEARCH.md "Excalidraw .md Stub Format"):
```
---
excalidraw-plugin: parsed
compress: false
tags:
  - architecture
---

## Text Elements

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"graphify","elements":[],"appState":{...},"files":{}}
```
%%
```

---

### `tests/test_profile.py` (MODIFY — add diagram_types cases)

**Analog:** existing tag_taxonomy validator tests (same file).

**Patterns to copy:**
- `tmp_path`-based profile.yaml write + `load_profile(tmp_path)` round-trip.
- Assert on `validate_profile(bad_profile)` returning specific error substrings.
- Assert on `_DEFAULT_PROFILE["diagram_types"]` having exactly 6 entries with expected names (PROF-02 "atomic landing" guard).

---

### `tests/test_seed.py` (MODIFY — add recommender cases)

**Analog:** existing `build_seed` unit tests (same file) — in-memory `nx.Graph()` construction, assert on returned seed dict fields.

**Required new tests (per RESEARCH.md §Validation Architecture):**
- `test_recommender_profile_match_wins` — profile entry with matching `trigger_node_types` beats `_TEMPLATE_MAP` fallback.
- `test_recommender_falls_back_to_heuristic` — no profile match → existing `_TEMPLATE_MAP[layout_type]` path.
- `test_recommender_survives_absent_diagram_types` — `profile=None` and `profile={}` both route to heuristic without raising.
- `test_build_seed_reads_diagram_types` — PROF-02 reader side.

---

### `tests/test_init_templates.py` (NEW — TMPL-01..05)

**Analog:** `tests/test_seed.py::test_build_all_seeds` — tmp_path-scoped integration test that invokes the CLI entry in-process (via `subprocess.run([sys.executable, "-m", "graphify", ...])` or direct call into the dispatch function).

**Pattern — tmp_path as vault root:**
```python
def test_init_writes_six_stubs(tmp_path, capsys):
    vault = tmp_path / "vault"
    vault.mkdir()
    # run CLI (subprocess or direct dispatch)
    ...
    templates = vault / "Excalidraw" / "Templates"
    assert sorted(p.name for p in templates.iterdir()) == [
        "architecture.excalidraw.md", "cuadro-sinoptico.excalidraw.md",
        "glossary-graph.excalidraw.md", "mind-map.excalidraw.md",
        "repository-components.excalidraw.md", "workflow.excalidraw.md",
    ]
```

**Required tests:**
- `test_init_writes_six_stubs` (TMPL-01)
- `test_init_idempotent_skips_existing` (TMPL-01/04)
- `test_stub_frontmatter_shape` (TMPL-02)
- `test_stub_has_both_blocks` (TMPL-02)
- `test_scene_json_shape` (TMPL-03)
- `test_scene_json_font_family_5` (TMPL-03)
- `test_rerun_without_force_no_changes` (TMPL-04)
- `test_force_overwrites_all` (TMPL-04)
- `test_subset_writes_only_declared` (TMPL-05)
- `test_no_section_writes_six_builtins` (TMPL-05)

---

### `tests/test_denylist.py` (NEW — TMPL-06 / D-14 / D-15)

**No repo analog** — this is the first architectural test. Use RESEARCH.md Code Example 6 as the skeleton.

**Pattern — regex scan over source tree with scoped files:**
```python
from pathlib import Path
import re

REPO = Path(__file__).parent.parent / "graphify"

_FORBIDDEN_WRITE_PATTERNS = [
    re.compile(r"\.write_text\("),
    re.compile(r"write_note_directly\("),
    re.compile(r"open\([^)]*['\"]w['\"]"),
]
_SCOPED_FILES = ["seed.py", "export.py", "__main__.py"]
_LZSTRING_IMPORT = re.compile(r"\b(?:import\s+lzstring|from\s+lzstring\b)")

def test_no_lzstring_import_anywhere():
    for py in REPO.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert not _LZSTRING_IMPORT.search(text), f"lzstring import in {py}"
```

**Scope notes (per Pitfall 5):** The write-pattern test must allow template writes under `Excalidraw/Templates/*.excalidraw.md`. Recommended approach: allowlist via inline comment marker (`# allow-vault-write: template`) or skip lines whose matched-file path literal contains `"Excalidraw/Templates"`. Existing `seed.py:559-569` tag write-back is NOT a direct `.write_text`/`open('w')` — it goes through `compute_merge_plan`, so the scoped regex will pass cleanly.

**Extended scope (RESEARCH.md Security §):** Also forbid `os.open\(.*O_WRONLY` and `Path(...).open\(['\"]w` to cover denylist-bypass attempts.

---

## Shared Patterns

### 1. Accumulator-style Validation (never raise)
**Source:** `graphify/profile.py::validate_profile` (line 157)
**Apply to:** New `diagram_types` validator block.
```python
def validate_profile(profile: dict) -> list[str]:
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]
    errors: list[str] = []
    # section-by-section accumulator — returns list, never raises
    return errors
```

### 2. Bool-before-int Guard
**Source:** `graphify/profile.py::validate_profile` topology.god_node.top_n (lines ~249-250 in slice)
**Apply to:** Any new integer field validation (i.e., `min_main_nodes`).
```python
if isinstance(value, bool) or not isinstance(value, int):
    errors.append(f"{path} must be an integer (got {type(value).__name__})")
```

### 3. Atomic File Write
**Source:** `graphify/seed.py::_write_atomic` (line 83)
**Apply to:** All new stub writes from the `--init-diagram-templates` CLI block.
```python
def _write_atomic(target: Path, content: str) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        if tmp.exists():
            try: tmp.unlink()
            except OSError: pass
        raise
```

### 4. Path Confinement
**Source:** `graphify/profile.py::validate_vault_path` (line 353)
**Apply to:** Every stub path resolution in the init CLI block before writing.
```python
resolved = validate_vault_path(rel_path, vault_root)  # raises ValueError on escape
```

### 5. CLI Dispatch Skeleton (raw sys.argv, not argparse)
**Source:** `graphify/__main__.py::--diagram-seeds` (line 1379)
**Apply to:** New `--init-diagram-templates` block; follow the same while-loop + `sys.exit(2)` on unknown flag + stderr-prefixed errors.

### 6. Frontmatter Emission
**Source:** `graphify/profile.py::_dump_frontmatter` (line 449)
**Apply to:** Stub frontmatter rendering in `excalidraw.py`.
- Handles `bool → lowercase true/false` (checked before int, since `bool` is subclass of `int`)
- Handles `list → YAML block form with safe_frontmatter_value on each item`
- Reader/writer symmetry with `merge.py` (do not substitute `yaml.dump`).

### 7. Sole Authorized Vault-Note Writer
**Source:** `graphify/merge.py::compute_merge_plan` (line 863), called from `graphify/seed.py:559-569`
**Apply to:** No new call sites in Phase 21 (TMPL-06 already wired). The denylist test enforces this invariant going forward.
**CRITICAL alias note:** CONTEXT.md says `vault_adapter.py::compute_merge_plan`; the actual module is `graphify/merge.py`. Use `from graphify.merge import compute_merge_plan`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_denylist.py` | architectural test | regex over source | No architectural/denylist test exists yet. Use RESEARCH.md §Code Examples #6 as authoritative skeleton. |
| `graphify/excalidraw.py` (stub renderer) | utility | transform | Greenfield — no existing Excalidraw-format writer. Compose from `_dump_frontmatter` + `json.dumps`. |

## Metadata

**Analog search scope:** `graphify/` (all modules), `tests/` (all test files), `.planning/phases/20-diagram-seed-engine/` (for predecessor patterns).
**Files scanned:** profile.py (651 lines, sampled 30-90, 115-290, 350-470), seed.py (583 lines, sampled 30-100, 190-250, 550-580), __main__.py (sampled 1370-1430), RESEARCH.md (670 lines, fully read), CONTEXT.md (133 lines, fully read).
**Pattern extraction date:** 2026-04-23
**Key finding:** Every Phase 21 extension point has a direct in-repo precedent — no novel patterns required. Two tests (`test_init_templates.py`, `test_denylist.py`) are greenfield but compose from existing idioms (tmp_path integration + regex scan).
