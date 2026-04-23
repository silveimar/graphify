# Phase 21: Profile Extension & Template Bootstrap - Research

**Researched:** 2026-04-23
**Domain:** profile-driven config extension + Obsidian Excalidraw template file generation
**Confidence:** HIGH (greenfield extension of well-mapped prior art; every extension point is already an anchor in the codebase)

## Summary

Phase 21 ships two deliverables built entirely on top of patterns that already exist in this repo:

1. **Plan 21-01 (ATOMIC profile update):** extend `graphify/profile.py` to recognize a new top-level `diagram_types:` section, populate six built-in entries in `_DEFAULT_PROFILE`, extend `validate_profile()` with the new section's shape checks, and insert a profile-first template resolver in `graphify/seed.py::build_seed` **in the same commit**. PROF-02 atomicity is a hard rule: no half-landed states.
2. **Plan 21-02 (CLI `--init-diagram-templates [--force]`):** add a new CLI flag that writes 6 `.excalidraw.md` file stubs with minimal empty-scene JSON, `compress: false` frontmatter, and no vault note writes. A grep denylist test forbids `Path.write_text`/`write_note_directly`/`open('w')` on vault `.md` paths in `seed.py`, `export.py`, and `__main__.py`, and forbids any `import lzstring` anywhere.

The `gen-diagram-seed` tag write-back (TMPL-06) is **already implemented** for `--diagram-seeds` in `seed.py:559-569` via `graphify.merge.compute_merge_plan`. Phase 21's work for TMPL-06 is primarily the **grep denylist test** that locks that invariant in (not re-implementing the write-back).

**Primary recommendation:** Treat CONTEXT.md's references to `vault_adapter.py::compute_merge_plan` as a conceptual alias — the real module is `graphify/merge.py` (line 863). Use `from graphify.merge import compute_merge_plan` in code and in the grep denylist test spec. Templates do not flow through `compute_merge_plan` — only vault **notes** (`.md` under the vault root, not `.excalidraw.md` under `Excalidraw/Templates/`) are restricted.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Stub content shape**
- **D-01** Each `.excalidraw.md` stub = minimal empty scene: valid frontmatter + empty `## Text Elements` block + `## Drawing` block containing `{"type":"excalidraw","version":2,"source":"graphify","elements":[],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}`. Styled style-guides deferred.
- **D-02** Frontmatter contains exactly: `excalidraw-plugin: parsed`, `compress: false`, and a tag list including the diagram-type name. Font family 5 (Excalifont) declared in `appState` where applicable even though `elements: []`.

**Profile atomicity (Plan 21-01)**
- **D-03** All four profile.py changes land in the same plan and commit sequence: (1) add `"diagram_types"` to `_VALID_TOP_LEVEL_KEYS`; (2) extend `_DEFAULT_PROFILE` with the 6 built-in entries; (3) extend `validate_profile()` with `diagram_types` shape validation; (4) first reader in `seed.py` calls `load_profile()['diagram_types']`.
- **D-04** Each `diagram_types` entry fields: `name` (str, required), `template_path` (str, optional — defaults to `Excalidraw/Templates/{name}.excalidraw.md`), `trigger_node_types` (list[str], default `[]`), `trigger_tags` (list[str], default `[]`), `min_main_nodes` (int, default `2`), `naming_pattern` (str, template-able). Missing optional fields degrade gracefully.
- **D-05** Six built-in defaults: `architecture`, `workflow`, `repository-components`, `mind-map`, `cuadro-sinoptico`, `glossary-graph`.

**Template recommender**
- **D-06** Match = **OR**: a `diagram_types` entry matches a seed if ANY node's type is in `trigger_node_types` OR ANY community tag is in `trigger_tags`. Also requires `|main_nodes| >= min_main_nodes`.
- **D-07** Tiebreak = **highest `min_main_nodes` wins**; fall back to declaration order on ties.
- **D-08** Resolution order: profile `diagram_types` match (D-06/D-07) → existing Phase 20 layout heuristic via `_TEMPLATE_MAP` → built-in fallback. Never throws on missing section/profile.

**CLI `--init-diagram-templates` (Plan 21-02)**
- **D-09** Default path when profile entry omits `template_path` or no profile exists: `{vault_root}/Excalidraw/Templates/{name}.excalidraw.md`.
- **D-10** Without `--force` = idempotent fill-in: write missing stubs, skip existing, print `Wrote N, skipped M (already exist). Use --force to overwrite.`
- **D-11** `--force` overwrites all stubs unconditionally; single flag, global scope.
- **D-12** When `diagram_types:` declares a subset, only those stubs are written. Built-in defaults kick in only when section absent entirely.

**Tag write-back**
- **D-13** Tag write-back triggers during `graphify --diagram-seeds` (NOT `--init-diagram-templates`). Init writes zero vault notes. Already wired in `seed.py:559-569`.
- **D-14** Grep denylist scope: forbids `Path.write_text`, `write_note_directly`, and `open(..., 'w')` calls targeting vault note `.md` paths in `seed.py`, `export.py`, `__main__.py`. Template writes under `Excalidraw/Templates/*.excalidraw.md` by the init command are **allowed** (templates, not notes).
- **D-15** `import lzstring` forbidden by the same denylist — enforces `compress: false` one-way door.

### Claude's Discretion
- Exact tag-merge call shape into `compute_merge_plan` (union vs append).
- Reported counts formatting and argparse wiring.
- Whether to cache profile→recommender resolution per build run.
- Whether to add optional `trigger_mode: and|or` per-entry override (skip unless trivial).

### Deferred Ideas (OUT OF SCOPE)
- Styled style-guide templates (full 8-10 element scenes).
- Per-entry `trigger_mode` override.
- `obsidian.excalidraw_templates_dir` profile key.
- "Most trigger matches wins" scoring tiebreak.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROF-01 | `profile.yaml` accepts top-level `diagram_types:`; graceful fallback to 6 built-ins | `_VALID_TOP_LEVEL_KEYS` (profile.py line 81) and `_DEFAULT_PROFILE` (line 36) are the existing extension points; `_deep_merge` already handles fallback |
| PROF-02 | ATOMIC update across `_VALID_TOP_LEVEL_KEYS`, `_DEFAULT_PROFILE`, `validate_profile()`, **and first reader** | `validate_profile()` at profile.py line 157-282 is an accumulator; first reader insertion point is `build_seed` in seed.py (see below) |
| PROF-03 | Per-entry fields `name`, `template_path`, `trigger_node_types`, `trigger_tags`, `min_main_nodes`, `naming_pattern` — all graceful defaults | Follow the `topology.god_node.top_n` pattern (profile.py:238-256) for int-with-bool-guard validation |
| PROF-04 | Recommender in `seed.py`: profile match → layout heuristic → built-in fallback; never throws | Insertion point: wrap `_TEMPLATE_MAP[layout_type]` lookup inside `build_seed` (seed.py:234) with a profile-first pre-check |
| TMPL-01 | `--init-diagram-templates` writes 6 stubs; idempotent skip unless `--force` | New CLI dispatch block in `__main__.py`, modeled on `--diagram-seeds` at line 1379 |
| TMPL-02 | Each stub has `excalidraw-plugin: parsed`, `compress: false`, `## Text Elements` block, `## Drawing` block with raw JSON (not LZ-String) | See "Excalidraw .md Stub Format" below |
| TMPL-03 | Scene JSON fixed shape; font family 5; `versionNonce` on every element | Reuse `_version_nonce()` at seed.py:61-64 |
| TMPL-04 | Idempotent without `--force`; `--force` overwrites all | Standard filesystem check pattern |
| TMPL-05 | When `diagram_types:` declares subset, only those are written; absent → all 6 built-ins | Read `load_profile(vault)['diagram_types']` and drive iteration off its keys |
| TMPL-06 | `gen-diagram-seed` tag write-back via `compute_merge_plan` with `tags: "union"` policy; grep denylist test forbids direct vault writes | **Already wired** in `seed.py:559-569`. Phase 21 adds only the denylist test |

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** — code must run on 3.10 and 3.12 CI targets.
- **No new required dependencies** — profile parsing uses PyYAML (already optional); template stubs use stdlib `json`. **Do NOT add `lzstring`** — it is explicitly denylisted by D-15.
- **Backward compatible** — `graphify --obsidian` without a profile must still work; `load_profile()` already guarantees this via `_deep_merge(_DEFAULT_PROFILE, {})`.
- **Pure unit tests** — no network, no filesystem writes outside `tmp_path`.
- **Path confinement** — all file writes must be under the output directory (template writes under `vault_root/Excalidraw/Templates/`). Reuse `validate_vault_path()` from `profile.py:353-367`.
- **Sanitize placeholders** — no injection via node labels when `naming_pattern` expands `{topic}`. Use `safe_filename()` (profile.py:399-414) on the result.
- **Atomic commit + test discipline** (CONVENTIONS.md) — PROF-02 atomicity is a CLAUDE.md-level invariant, not a stylistic preference.
- **Before edits:** start work through a GSD command (`/gsd-execute-phase`) per CLAUDE.md's GSD Workflow Enforcement section.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `diagram_types` schema + defaults | profile.py (config layer) | — | All top-level profile keys already land here |
| Profile validation (new `diagram_types` block) | profile.py::validate_profile | — | Existing accumulator pattern; returns `list[str]` errors |
| Template recommendation (profile-first) | seed.py::build_seed | profile.py (for load) | Recommender is seed-local behavior; profile is a pure input |
| CLI dispatch for `--init-diagram-templates` | `__main__.py` | profile.py (path helpers) | Follows `--diagram-seeds` pattern at line 1379 |
| Stub file writing (Excalidraw) | new helper in `__main__.py` or new module | — | Greenfield; no existing excalidraw writer |
| Tag write-back to vault notes | `graphify.merge.compute_merge_plan` | seed.py (caller) | Already wired; sole authorized vault-note writer |
| Grep denylist enforcement | `tests/test_denylist.py` (new) | — | Architectural test — no runtime code |

## Standard Stack

### Core (already in tree — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | optional `[obsidian]` extra | Parse `.graphify/profile.yaml` | Already used by `load_profile`; do NOT make required |
| stdlib `json` | built-in | Emit scene JSON in stubs | No dependency creep |
| stdlib `pathlib.Path` | built-in | All path ops | Project convention |
| stdlib `hashlib` | built-in | `versionNonce` derivation | Existing pattern in `seed.py::_version_nonce` |
| NetworkX | already installed | Graph queries in recommender | Already pipeline primary |

### Supporting (reuse — do not rebuild)
| Function | Location | Purpose |
|----------|----------|---------|
| `_deep_merge` | profile.py:121 | Layer user profile over defaults (handles missing `diagram_types`) |
| `_dump_frontmatter` | profile.py:449 | Emit stub frontmatter; supports lists (`tags:` block form) and bools |
| `safe_frontmatter_value` | profile.py:376 | Quote tag strings that contain YAML specials |
| `validate_vault_path` | profile.py:353 | Confine template writes inside `vault_root` |
| `safe_filename` | profile.py:399 | Sanitize `{topic}` expansions from `naming_pattern` |
| `_version_nonce` | seed.py:61 | Deterministic int IDs (per TMPL-03) |
| `_element_id` | seed.py:53 | `sha256(node_id)[:16]` — reusable even with empty elements |
| `compute_merge_plan` | **merge.py:863** (NOT `vault_adapter.py`) | Tag write-back (already wired in seed.py:559-569) |
| `_VALID_LAYOUT_TYPES` / `_TEMPLATE_MAP` | seed.py:35-44 | Layout heuristic fallback layer |

### Alternatives Considered (rejected per CONTEXT.md)
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw-JSON scene (compress: false) | LZ-String compressed | Blocked by D-15; reversibility + diffability win over ~30% size savings |
| Generate-in-code stubs | Ship as pkg-data files in `graphify/builtin_templates/diagram/` | Generation keeps one source of truth; aligns with D-01 minimal-empty shape |
| argparse subparser | Raw `sys.argv` dispatch (like `--diagram-seeds`) | Follows existing pattern at `__main__.py:1379`; consistent with rest of CLI |
| Jinja2 for `naming_pattern` | stdlib `str.format_map({'topic': topic})` | No new deps; CLAUDE.md forbids Jinja2 for templates |

## Excalidraw `.md` Stub Format (authoritative)

The Obsidian Excalidraw plugin defines `.excalidraw.md` as a four-part document. Phase 21 emits the *uncompressed* variant (D-15 one-way door).

**Verified shape** [CITED: CONTEXT.md D-01/D-02/specifics; REQUIREMENTS.md TMPL-02/TMPL-03; ROADMAP.md Phase 21 success criterion #3]:

```markdown
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
{"type":"excalidraw","version":2,"source":"graphify","elements":[],"appState":{"viewBackgroundColor":"#ffffff","gridSize":null},"files":{}}
```
%%
```

**Key rules:**
1. **Frontmatter fields are exactly three** (D-02): `excalidraw-plugin: parsed`, `compress: false`, `tags:` (list with at least the type name). Font family declaration lives inside `appState`, not frontmatter.
2. **`## Text Elements` block is always present** even when empty (TMPL-02). The plugin uses it to sync text elements back to frontmatter-visible form.
3. **`## Drawing` block holds the raw scene JSON** in a fenced ` ```json ` code block (uncompressed). `compress: true` would replace this with an `## Drawing` block containing LZ-String base64 — we do NOT do that.
4. **`%%` HTML-comment delimiters** wrap the drawing so the JSON does not render in Obsidian preview mode. This is the plugin convention.
5. **Scene JSON top-level keys are byte-fixed** (TMPL-03): `type`, `version`, `source`, `elements`, `appState`, `files`. Phase 21 stubs keep `elements: []` and `files: {}`.
6. **Font family 5** (Excalifont) — declared inside `appState` when applicable. The exact nesting is `appState.currentItemFontFamily: 5`. For D-01 empty stubs this is a no-op (no elements exist), but D-02 requires declaring it so later phases don't need to rewrite `appState`. **Recommended:** add `"currentItemFontFamily": 5` to the `appState` dict.
7. **`versionNonce` on every element** (TMPL-03) — moot for empty stubs (`elements: []`), but the Phase 22 / downstream code that adds elements must reuse `seed.py::_version_nonce`.

**Suggested `appState` for stubs (goes beyond the byte-fixed top-level but stays within TMPL-02/03):**
```json
{"viewBackgroundColor":"#ffffff","gridSize":null,"currentItemFontFamily":5}
```

[ASSUMED] The `%%` comment wrapping and exact `## Drawing` placement are standard Obsidian Excalidraw plugin conventions. No Obsidian Excalidraw plugin README is bundled in this repo; the canonical reference is the plugin's own documentation which the Plan 21-02 agent should spot-verify against a real vault before writing tests.

## Architecture Patterns

### Data Flow (Plan 21-01)

```
User edits .graphify/profile.yaml
        │  (writes diagram_types: section)
        ▼
load_profile(vault_dir)   [profile.py:97]
        │  validate_profile() → validates diagram_types shape
        │  _deep_merge(_DEFAULT_PROFILE, user_data)
        ▼
Full profile dict (diagram_types key guaranteed present via default)
        │
        ▼
seed.py::build_seed(G, node_id, trigger, layout_hint)   [FIRST READER]
        │
        ├─ (NEW) profile-first recommender: scan profile['diagram_types']
        │      match = entry where (trigger_node_types ∩ main_node_types) OR
        │              (trigger_tags ∩ community_tags), and main_nodes >= min_main_nodes
        │      tiebreak: highest min_main_nodes, then declaration order
        │      → if match: use entry.template_path
        │
        ├─ (EXISTING) _select_layout_type heuristic   [seed.py:116]
        │      → _TEMPLATE_MAP[layout_type]
        │
        └─ (FALLBACK) built-in default ("mind-map.excalidraw.md")
```

### Data Flow (Plan 21-02)

```
graphify --init-diagram-templates [--force] --vault <path>
        │
        ▼
__main__.py dispatch block (new, after line 1420)
        │
        ├─ load_profile(vault)
        │      → profile['diagram_types']  (always present due to _DEFAULT_PROFILE)
        │
        ├─ For each (type_name, entry) in profile['diagram_types']:
        │      target = entry.get('template_path') or f"Excalidraw/Templates/{type_name}.excalidraw.md"
        │      resolved = validate_vault_path(target, vault)
        │      if resolved.exists() and not --force:
        │            skip (count++)
        │            continue
        │      content = _render_excalidraw_stub(type_name, appState)
        │      _write_atomic(resolved, content)   [reuse seed.py:83]
        │
        └─ print(f"Wrote {n_wrote}, skipped {n_skipped} (already exist). Use --force to overwrite.")
```

### Recommended New Files / Modifications

```
graphify/
├── profile.py                 # MODIFY: _DEFAULT_PROFILE, _VALID_TOP_LEVEL_KEYS, validate_profile()
├── seed.py                    # MODIFY: build_seed — insert profile-first recommender BEFORE _select_layout_type fallback
├── __main__.py                # MODIFY: new --init-diagram-templates dispatch block
└── excalidraw.py              # NEW (optional): helpers _render_stub(), _scene_json()
                                  Alternative: inline in __main__.py if < 50 lines

tests/
├── test_profile.py            # MODIFY: add diagram_types validation + defaults tests
├── test_seed.py               # MODIFY: add profile-first recommender tests
├── test_init_templates.py     # NEW: CLI behavior (writes, idempotence, --force, subset)
└── test_denylist.py           # NEW: grep denylist for D-14 + D-15
```

### Pattern 1: ATOMIC profile extension (PROF-02)
**What:** All four changes (`_VALID_TOP_LEVEL_KEYS`, `_DEFAULT_PROFILE`, `validate_profile()`, and first reader in seed.py) land in the same commit — no "validation lands in one commit, defaults in the next" split.

**Why:** Splitting leaves a window where `validate_profile` rejects `diagram_types:` as an unknown key, or where defaults exist but no one reads them. Both are user-facing bugs that the atomicity rule prevents.

**Example of the invariant:**
```python
# profile.py — all four hunks in ONE commit
_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync",
    "diagram_types",   # (1) NEW
}

_DEFAULT_PROFILE: dict = {
    # ... existing keys ...
    "diagram_types": {   # (2) NEW
        "architecture": {
            "name": "architecture",
            "template_path": "Excalidraw/Templates/architecture.excalidraw.md",
            "trigger_node_types": [],
            "trigger_tags": [],
            "min_main_nodes": 2,
            "naming_pattern": "{topic} Architecture",
        },
        # ... workflow, repository-components, mind-map, cuadro-sinoptico, glossary-graph ...
    },
}

def validate_profile(profile: dict) -> list[str]:
    # ... existing ...
    # (3) NEW — diagram_types section
    diagram_types = profile.get("diagram_types")
    if diagram_types is not None:
        if not isinstance(diagram_types, dict):
            errors.append("'diagram_types' must be a mapping (dict)")
        else:
            for type_name, entry in diagram_types.items():
                # validate shape per D-04 — see validator pattern below
                ...
    return errors

# seed.py — (4) FIRST READER in same commit
def build_seed(G, node_id, trigger, layout_hint=None, profile=None):
    # ... ego graph build ...
    layout_type = _select_layout_type(subG, main_nodes, layout_hint)
    # NEW: profile-first template selection
    template = _select_template_from_profile(profile, main_nodes, community_tags, layout_type) \
               or _TEMPLATE_MAP[layout_type]
    return {... "suggested_template": template, ...}
```

### Pattern 2: Validator Shape (profile.py:238-256 existing reference)
```python
# This is the EXISTING pattern for validating a nested int with bool guard.
# Use it as the template for diagram_types.{entry}.min_main_nodes.
god_node = topology.get("god_node")
if god_node is not None:
    if not isinstance(god_node, dict):
        errors.append("'topology.god_node' must be a mapping (dict)")
    else:
        top_n = god_node.get("top_n")
        if top_n is not None:
            # bool-before-int guard (T-3-03) — bool is a subclass of int in Python
            if isinstance(top_n, bool) or not isinstance(top_n, int):
                errors.append(
                    f"topology.god_node.top_n must be an integer "
                    f"(got {type(top_n).__name__})"
                )
            elif top_n < 0:
                errors.append(f"topology.god_node.top_n must be ≥ 0 (got {top_n})")
```

### Pattern 3: CLI Dispatch (existing at `__main__.py:1379`)
```python
# Use this as the template for --init-diagram-templates dispatch.
if cmd == "--init-diagram-templates":
    vault_path = None
    force = False
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--vault" and i + 1 < len(args):
            vault_path = Path(args[i + 1]); i += 2
        elif args[i].startswith("--vault="):
            vault_path = Path(args[i].split("=", 1)[1]); i += 1
        elif args[i] == "--force":
            force = True; i += 1
        else:
            print(f"error: unknown --init-diagram-templates option: {args[i]}", file=sys.stderr)
            sys.exit(2)
    if vault_path is None:
        print("error: --vault is required", file=sys.stderr); sys.exit(2)
    # ... writing loop ...
```

### Pattern 4: Atomic Write (existing at `seed.py:83`)
Reuse `_write_atomic(target, content)` **verbatim** for stub writes. It's already the established pattern and survives crash-mid-write via `.tmp` + `os.replace` + `fsync`.

### Anti-Patterns to Avoid
- **Splitting PROF-02 across commits** — violates the phase's one explicit atomicity rule.
- **Using `yaml.dump()` to write frontmatter** — project uses hand-rolled `_dump_frontmatter` (profile.py:449); PyYAML isn't a required dep and its output differs from the reader in `merge.py`.
- **Importing `lzstring`** — tripwire test failure (D-15).
- **Writing stubs via `Path.write_text` without `_write_atomic`** — crash-mid-write leaves partial files.
- **Letting `naming_pattern` format strings execute arbitrary placeholders** — use `str.format_map()` with a whitelist `{topic}` only; never `eval()` or Jinja.
- **Placing `.excalidraw.md` stubs under the vault's note tree** — templates belong in `Excalidraw/Templates/`, which is outside the note-denylist scope. Confusing the two would trigger the grep test to flag the init command as a vault-note writer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parse of profile.yaml | Custom parser | `yaml.safe_load` (already in `load_profile`) | Already wired, error-handled, optional-dep-guarded |
| YAML frontmatter emission | `yaml.dump` | `profile.py::_dump_frontmatter` | Reader/writer symmetry with `merge.py` |
| Atomic file write | Ad-hoc `open('w')` | `seed.py::_write_atomic` | Handles `.tmp` + `os.replace` + `fsync` + cleanup |
| Vault path confinement | Custom `..`/absolute checks | `profile.py::validate_vault_path` | Already covers the Windows/POSIX edge cases |
| Filename sanitization for `naming_pattern` output | Custom regex | `profile.py::safe_filename` | NFC normalization + length cap + collision hash |
| Deterministic element IDs (for future use) | Random UUIDs | `seed.py::_element_id` | TMPL-03 invariant + diff-stable |
| Deterministic versionNonce | `random.randint` | `seed.py::_version_nonce` | TMPL-03 invariant |
| Tag write-back to vault notes | Direct `Path.write_text` | `graphify.merge.compute_merge_plan` | D-14 denylist; already wired in seed.py:559-569 |
| LZ-String compression | `pip install lzstring` | `compress: false` uncompressed JSON | D-15 one-way door |

## Runtime State Inventory

**Not applicable** — Phase 21 is greenfield extension (new top-level profile key + new CLI command). No renames, no migrations, no stored string keys that need re-indexing.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `diagram_types` is a new profile key; no prior vault data uses it | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | If `graphify/builtin_templates/diagram/` is added as pkg-data, must be listed in `pyproject.toml` `[tool.setuptools.package-data]` — but CONTEXT.md favors generation-in-code, so likely None | Verify at plan time |

## Common Pitfalls

### Pitfall 1: CONTEXT.md refers to `vault_adapter.py` but the real module is `merge.py`
**What goes wrong:** Plans or code that does `from graphify.vault_adapter import compute_merge_plan` will `ImportError`. The file does not exist.
**Why it happens:** CONTEXT.md and REQUIREMENTS.md use `vault_adapter.py::compute_merge_plan` as a conceptual alias for the sole-authorized vault-note writer, but the actual module is `graphify/merge.py` (line 863 — verified).
**How to avoid:** Plans MUST say `graphify.merge.compute_merge_plan` in imports and grep denylist matchers. Treat `vault_adapter` as documentation shorthand only.
**Warning signs:** `ModuleNotFoundError: No module named 'graphify.vault_adapter'` at first import; grep test matching on `vault_adapter` will never fire.

### Pitfall 2: `CONTEXT.md` code-anchor line numbers for `suggested_template` are stale
**What goes wrong:** CONTEXT.md says "`suggested_template` output at lines 270, 359-360" in seed.py. Actual references: `seed.py:44` (`_TEMPLATE_MAP` constant), and `seed.py:234` (`"suggested_template": _TEMPLATE_MAP[layout_type]` inside `build_seed`). No references at lines 270 or 359-360 in current seed.py (583 total lines).
**Why it happens:** Lines shifted as Phase 20 landed. The intent — insert profile-first resolution at the template-assignment site — is clear; only the line number is stale.
**How to avoid:** The **true insertion point** is `build_seed` at line ~234. Plans should grep for `suggested_template` rather than navigate by line number.
**Warning signs:** Opening `seed.py` to line 270 shows `_seed_node_ids`, not template code.

### Pitfall 3: Empty YAML file returns `None` from `yaml.safe_load`
**What goes wrong:** `yaml.safe_load("")` returns `None`, not `{}`. Calling `.get()` on it raises `AttributeError`.
**Why it happens:** Documented in `load_profile` as "Pitfall 1" — already guarded by `or {}` at profile.py:114.
**How to avoid:** New validator additions to `diagram_types` should not assume it's a dict without checking — but since `_deep_merge(_DEFAULT_PROFILE, {})` is applied first, the key is always present. Only the raw validation path (pre-merge) needs the isinstance guard.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'items'` when a user's `.graphify/profile.yaml` is empty.

### Pitfall 4: `bool` is a subclass of `int` in Python
**What goes wrong:** `isinstance(True, int)` is `True`. A validator that only checks `isinstance(x, int)` accepts `True` for `min_main_nodes`, which then passes `>= 0` but corrupts the tiebreak.
**Why it happens:** Python type hierarchy.
**How to avoid:** Always gate `int` checks with `isinstance(x, bool) or not isinstance(x, int)` — the existing pattern at profile.py:249-250 for `topology.god_node.top_n`.
**Warning signs:** Users report "my `min_main_nodes: true` silently matched as 1".

### Pitfall 5: Grep denylist false positive on template writes
**What goes wrong:** The init command MUST write files to `Excalidraw/Templates/*.excalidraw.md`. A naive grep denylist regex like `open\(.*['"]w['"]` would flag the init-command writes AS IF they were vault-note writes.
**Why it happens:** Templates are files too; the denylist intends to block **vault note** (`.md` under the vault root, not under `Excalidraw/Templates/`) writes.
**How to avoid:** Scope the grep denylist to patterns that specifically target "vault note-writing code paths." D-14 allows template writes explicitly. Recommended: test the denylist with fixture strings that include both the forbidden pattern (a direct vault-note write) and the allowed pattern (`_write_atomic(Path(vault)/"Excalidraw"/"Templates"/f"{t}.excalidraw.md", ...)`) — the test must PASS for the allowed case.
**Warning signs:** Test fails on `seed.py:559-569` (existing, approved `compute_merge_plan` call) because it doesn't understand function-level semantics.

### Pitfall 6: `_deep_merge` replaces sub-keys wholesale when override is non-dict
**What goes wrong:** If a user sets `diagram_types: null` in their YAML, `_deep_merge` replaces the entire defaults dict with `None`, breaking every reader.
**Why it happens:** profile.py:127 — `else: result[key] = value`. A `None` user value clobbers the default.
**How to avoid:** Validate before merging — `validate_profile` returns errors and `load_profile` falls back to defaults on any error. Ensure the new `diagram_types` validator flags `None` as "must be a mapping (dict)".
**Warning signs:** TypeError on `.items()` or `.get()` downstream of `load_profile`.

## Code Examples

Verified patterns from this repo:

### Example 1: Profile validator accumulator (existing)
```python
# profile.py:157 — pattern for validate_profile's shape
def validate_profile(profile: dict) -> list[str]:
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]
    errors: list[str] = []
    # ... existing sections ...
    return errors
```

### Example 2: Nested-entry validator (follow this for diagram_types)
```python
# profile.py:275-281 — pattern for tag_taxonomy list-of-strings validation
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

### Example 3: Frontmatter emission with list (reuse for stub frontmatter)
```python
# profile.py:_dump_frontmatter handles this shape:
fields = {
    "excalidraw-plugin": "parsed",
    "compress": False,                    # emitted as "compress: false"
    "tags": ["architecture"],             # emitted as YAML block list
}
frontmatter = _dump_frontmatter(fields)
# Output:
# ---
# excalidraw-plugin: parsed
# compress: false
# tags:
#   - architecture
# ---
```

### Example 4: Tag write-back already wired (seed.py:559-569 — DO NOT rewrite)
```python
# seed.py (existing — reference only for TMPL-06 test spec)
if vault is not None:
    from graphify.merge import compute_merge_plan
    auto_node_ids = [s["main_node_id"] for s in deduped if s["trigger"] == "auto"]
    rendered_notes = {}
    for nid in auto_node_ids:
        label = G.nodes[nid].get("label", nid)
        rendered_notes[nid] = {
            "node_id": nid,
            "target_path": Path(vault) / f"{label}.md",
            "frontmatter_fields": {"tags": ["gen-diagram-seed"]},
            "body": "",
        }
    if rendered_notes:
        compute_merge_plan(Path(vault), rendered_notes, profile or {})
```

### Example 5: `compute_merge_plan` signature (merge.py:863)
```python
def compute_merge_plan(
    vault_dir: Path,
    rendered_notes: dict[str, RenderedNote],   # {node_id: {node_id, target_path, frontmatter_fields, body}}
    profile: dict,
    *,
    skipped_node_ids: set[str] | None = None,
    previously_managed_paths: set[Path] | None = None,
    manifest: dict[str, dict] | None = None,
    force: bool = False,
) -> MergePlan: ...
```
The `tags: "union"` policy is the **default** in `_DEFAULT_FIELD_POLICIES` at merge.py:67-70 — no extra wiring needed to achieve D-13's "union" semantics.

### Example 6: Grep denylist test skeleton
```python
# tests/test_denylist.py (NEW, per D-14/D-15)
from pathlib import Path
import re

REPO = Path(__file__).parent.parent / "graphify"

# D-14: direct vault-note writes forbidden
_FORBIDDEN_WRITE_PATTERNS = [
    re.compile(r"\.write_text\("),
    re.compile(r"write_note_directly\("),
    re.compile(r"open\([^)]*['\"]w['\"]"),
]
# Files that must be clean of the above when targeting vault note paths
_SCOPED_FILES = ["seed.py", "export.py", "__main__.py"]

# D-15: lzstring must not be imported
_LZSTRING_IMPORT = re.compile(r"\b(?:import\s+lzstring|from\s+lzstring\b)")

def test_no_direct_vault_note_writes():
    # Note: the test must EXCLUDE calls where the target is template-scoped
    # (e.g., Excalidraw/Templates/*.excalidraw.md). Suggested approach:
    #   - allowlist via inline comment marker: "# allow-vault-write: template"
    #   - OR function-scoped whitelist (inspect AST, skip bodies named _write_template_stub)
    ...

def test_no_lzstring_import_anywhere():
    for py in REPO.rglob("*.py"):
        text = py.read_text()
        assert not _LZSTRING_IMPORT.search(text), f"lzstring import in {py}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_TEMPLATE_MAP` hard-coded selection | Profile-first recommender → heuristic fallback | Phase 21 Plan 21-01 | User vaults can declare custom diagram types without code edits |
| LZ-String compressed `.excalidraw.md` (Excalidraw default) | Raw uncompressed JSON (D-15) | Phase 21 | Diff-stable, grep-able, no lzstring dep — one-way door |
| Template docs as skill guidance | Real on-disk `.excalidraw.md` template files | Phase 21 Plan 21-02 | Obsidian plugin sees real templates in `Excalidraw/Templates/` |

**Deprecated/outdated:**
- None — Phase 21 is additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `%%` HTML-comment wrapping around `## Drawing` is required by the Obsidian Excalidraw plugin convention | Excalidraw .md Stub Format, rule 4 | Low — if the plugin tolerates absence, stubs still work; if required, plugin silently ignores or renders JSON raw. Plan 21-02 should write one stub to a real Obsidian + Excalidraw vault and verify it opens, as a one-time sanity check before coding |
| A2 | `currentItemFontFamily: 5` is the correct `appState` key for Excalifont | Excalidraw .md Stub Format, rule 6 | Low-medium — font family number 5 is documented in Excalidraw source as the Excalifont ID (shipped in recent plugin versions); key name is one of the standard `appState` keys. Verify against plugin source if exact key differs |
| A3 | `tags` union policy is automatic via `_DEFAULT_FIELD_POLICIES` — no per-call wiring needed | Code Examples #5 | Verified — merge.py:70 explicitly sets `"tags": "union"` in defaults |
| A4 | Font family 5 declaration in `appState` is currently a no-op for empty-scene stubs but is required by D-02 | Excalidraw .md Stub Format, rule 6 | None — D-02 is locked; future phases will populate `elements` and inherit the font |

## Open Questions

1. **Should stubs ship as pkg-data files under `graphify/builtin_templates/diagram/`, or be generated in code at init time?**
   - What we know: CONTEXT.md explicitly leaves this to the planner. The existing `builtin_templates/` dir holds note templates (`.md`), not `.excalidraw.md`. Generation-in-code is simpler for D-01 (minimal empty scene).
   - What's unclear: Whether shipping as pkg-data adds value for user inspectability.
   - Recommendation: **Generate in code.** Reasons: (a) D-01 shape is ~200 bytes of JSON and three frontmatter lines — no reason for a separate file; (b) avoids `pyproject.toml` package-data wiring; (c) keeps the `compress: false` and scene-JSON constants in one Python module where they're covered by unit tests.

2. **Where should the `_render_excalidraw_stub` helper live?**
   - What we know: `seed.py` and `export.py` already handle diagram-adjacent concerns. A new `graphify/excalidraw.py` would isolate Excalidraw-format code.
   - What's unclear: Whether Phase 22 (Skill & Vault Bridge) will need the same helper.
   - Recommendation: **Create `graphify/excalidraw.py`** as a new module. Phase 22's downstream code (skill writes styled templates, fills elements) will reuse the same frontmatter + scene-JSON helpers. Keeps `__main__.py` from growing further.

3. **Should the grep denylist test use AST parsing (precise) or regex (simple)?**
   - What we know: Regex is easier; AST is less false-positive-prone.
   - Recommendation: **Start with regex + explicit allowlist comments** (e.g., `# allow-vault-write: template`). Upgrade to AST only if false positives bite. Precedent: no AST-based denylist tests currently exist in this repo.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Core | ✓ | 3.10+ (CI: 3.10, 3.12) | — |
| PyYAML | Reading `.graphify/profile.yaml` | Optional (`[obsidian]` extra) | any | `load_profile` returns `_DEFAULT_PROFILE` with stderr warning — already handled |
| pytest | Tests | ✓ | latest | — |
| NetworkX | `seed.py` profile-first recommender | ✓ | installed | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** PyYAML — already gracefully degraded at `load_profile` (profile.py:108-115). If a user creates a `.graphify/profile.yaml` with `diagram_types:` and PyYAML isn't installed, they get a warning and fall back to built-ins. This is acceptable and matches PROF-04's "never errors" invariant.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (unpinned) |
| Config file | None (settings inferred from file locations) |
| Quick run command | `pytest tests/test_profile.py tests/test_seed.py tests/test_init_templates.py tests/test_denylist.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-01 | `diagram_types` accepted; absent → 6 built-in defaults | unit | `pytest tests/test_profile.py::test_load_profile_diagram_types_defaults -x` | ❌ Wave 0 |
| PROF-02 | ATOMIC — `_VALID_TOP_LEVEL_KEYS` includes `"diagram_types"` AND `validate_profile` accepts it AND `_DEFAULT_PROFILE` has 6 entries AND `build_seed` reads it | unit (asserts all four) | `pytest tests/test_profile.py::test_diagram_types_atomic_landing -x` + `pytest tests/test_seed.py::test_build_seed_reads_diagram_types -x` | ❌ Wave 0 |
| PROF-03 | Each entry's 6 fields validated + graceful defaults for missing optional fields | unit | `pytest tests/test_profile.py::test_diagram_types_entry_shape -x` + `pytest tests/test_profile.py::test_diagram_types_missing_optional_fields_default -x` | ❌ Wave 0 |
| PROF-04 | Recommender: profile match → heuristic → fallback; never throws on missing section | unit | `pytest tests/test_seed.py::test_recommender_profile_match_wins -x`; `pytest tests/test_seed.py::test_recommender_falls_back_to_heuristic -x`; `pytest tests/test_seed.py::test_recommender_survives_absent_diagram_types -x` | ❌ Wave 0 |
| TMPL-01 | `graphify --init-diagram-templates` writes 6 stubs; skip existing | integration | `pytest tests/test_init_templates.py::test_init_writes_six_stubs -x`; `pytest tests/test_init_templates.py::test_init_idempotent_skips_existing -x` | ❌ Wave 0 |
| TMPL-02 | Stub frontmatter exactly `excalidraw-plugin: parsed` + `compress: false` + tag list; `## Text Elements` + `## Drawing` present | unit | `pytest tests/test_init_templates.py::test_stub_frontmatter_shape -x`; `pytest tests/test_init_templates.py::test_stub_has_both_blocks -x` | ❌ Wave 0 |
| TMPL-03 | Scene JSON top-level keys match byte-for-byte; font family 5 declared | unit | `pytest tests/test_init_templates.py::test_scene_json_shape -x`; `pytest tests/test_init_templates.py::test_scene_json_font_family_5 -x` | ❌ Wave 0 |
| TMPL-04 | Re-run without `--force` = zero changes; `--force` = overwrites all | integration | `pytest tests/test_init_templates.py::test_rerun_without_force_no_changes -x`; `pytest tests/test_init_templates.py::test_force_overwrites_all -x` | ❌ Wave 0 |
| TMPL-05 | `diagram_types:` subset → only those stubs; absent → all 6 | integration | `pytest tests/test_init_templates.py::test_subset_writes_only_declared -x`; `pytest tests/test_init_templates.py::test_no_section_writes_six_builtins -x` | ❌ Wave 0 |
| TMPL-06 | `gen-diagram-seed` tag write-back via `compute_merge_plan` (already wired); grep denylist asserts no direct writes + no `lzstring` | architectural | `pytest tests/test_denylist.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_profile.py tests/test_seed.py tests/test_init_templates.py tests/test_denylist.py -x -q` (< 5 s expected)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_init_templates.py` — new file, covers TMPL-01..05
- [ ] `tests/test_denylist.py` — new file, covers TMPL-06 invariants + D-14/D-15
- [ ] Extensions to `tests/test_profile.py` — cover PROF-01/02/03 (file exists, needs new test functions)
- [ ] Extensions to `tests/test_seed.py` — cover PROF-02 reader side + PROF-04 (file exists, needs new test functions)
- [ ] Framework install: already installed — no action

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local CLI, no auth surface |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — user operates on own filesystem |
| V5 Input Validation | **yes** | `validate_profile()` accumulator returns errors before merge; `safe_frontmatter_value()` quotes YAML specials; `safe_filename()` sanitizes `naming_pattern` output |
| V6 Cryptography | no | No secrets; `hashlib.sha256` used only for deterministic IDs, not security |
| V7 Error Handling | yes | Errors printed to stderr with `[graphify]` prefix; never raise past CLI boundary |
| V10 Malicious Code | yes (file I/O) | `validate_vault_path` confines all writes under vault_root |
| V12 File Handling | **yes** | `_write_atomic` pattern; path traversal rejected in folder_mapping |
| V14 Configuration | yes | PyYAML `safe_load` (not `load`); `.graphify/profile.yaml` is user-owned |

### Known Threat Patterns for `profile.py` + template-writing CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `template_path: "../../etc/hosts"` | Tampering | `validate_vault_path` already rejects; extend validator to reject `..` in `template_path` at profile-validation time too |
| YAML injection via user `naming_pattern: "{topic}\nmalicious: true"` in subsequent frontmatter | Tampering | `safe_frontmatter_value` quotes specials; naming_pattern expansion must go through `safe_filename`, not straight into frontmatter |
| Denial of service via very large `diagram_types` dict | Availability | Not mitigated explicitly; acceptable — user owns the profile; iteration is O(n) and n is tiny in practice |
| Malicious `.graphify/profile.yaml` from untrusted vault clone | Tampering | `yaml.safe_load` prevents arbitrary code execution; validator rejects unknown top-level keys |
| Template-path symlink race (TOCTOU) | Tampering | `validate_vault_path` uses `resolve()` before the `relative_to` check; `_write_atomic` uses `os.replace` |
| `lzstring` supply-chain injection if ever added | Tampering | D-15 grep denylist test blocks any import |
| Denylist bypass via `os.open(path, os.O_WRONLY|os.O_CREAT)` instead of `open(path, 'w')` | Tampering | Grep denylist pattern list should include `os\.open\(.*O_WRONLY` too — extend the D-14 regex set in test |

**Recommendation:** Extend the Plan 21-02 denylist regex beyond the three patterns listed in D-14 to also cover `os.open` with write flags and `pathlib.Path(...).open('w')`. This is an expansion of D-14's enumerated patterns but matches its **intent**.

## Sources

### Primary (HIGH confidence)
- `graphify/profile.py` (651 lines) — verified: `_DEFAULT_PROFILE` at line 36, `_VALID_TOP_LEVEL_KEYS` at line 81, `validate_profile` at line 157, `_deep_merge` at line 121, `validate_vault_path` at line 353, `_dump_frontmatter` at line 449, `safe_frontmatter_value` at line 376, `safe_filename` at line 399
- `graphify/seed.py` (583 lines) — verified: `_TEMPLATE_MAP` at line 44, `build_seed` at line 196, `suggested_template` assignment at line 234 (NOT 270 or 359 as CONTEXT.md states — see Pitfall 2), tag write-back at lines 559-569
- `graphify/merge.py` — verified: `compute_merge_plan` at line 863; `_DEFAULT_FIELD_POLICIES` with `"tags": "union"` at line 70
- `graphify/__main__.py` — verified: `--diagram-seeds` dispatch at line 1379 (model for new `--init-diagram-templates`)
- `.planning/phases/21-profile-extension-template-bootstrap/21-CONTEXT.md` — decisions D-01..D-15
- `.planning/REQUIREMENTS.md` lines 43-57 — PROF-01..04, TMPL-01..06 verbatim
- `.planning/ROADMAP.md` Phase 21 section — goal, success criteria, cross-phase rules
- `.planning/codebase/CONVENTIONS.md` — naming, type hints, error handling patterns
- `.planning/codebase/TESTING.md` — pytest conventions, `tmp_path` usage, no external mocking beyond stdlib

### Secondary (MEDIUM confidence)
- Existing test suite files `tests/test_profile.py` (1104 lines) and `tests/test_seed.py` (640 lines) — patterns for extending with `diagram_types` cases
- `graphify/analyze.py:695-725` — documents `possible_diagram_seed` node attr and `gen-diagram-seed` tag semantics that feed the write-back

### Tertiary (LOW confidence — needs validation)
- Obsidian Excalidraw plugin `.excalidraw.md` format conventions (`%%` wrapping, `## Drawing` code-fence placement, `currentItemFontFamily: 5` appState key name). No plugin docs committed to repo. Plan 21-02 should spot-verify one stub by opening it in a real Excalidraw-enabled Obsidian vault before locking test assertions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every reused function is anchored to a verified line in the tree.
- Architecture: HIGH — both plans extend existing, well-documented modules with one-line call-path changes.
- Pitfalls: HIGH — the two CONTEXT.md discrepancies (vault_adapter vs merge; stale line numbers) are verified by direct `grep` and line inspection.
- Excalidraw format: MEDIUM — shape is fixed by REQUIREMENTS.md/CONTEXT.md, but the `%%` wrapping and exact `appState` font key are plugin conventions not documented in this repo (A1, A2).

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (30 days — codebase is stable; Phase 20 just landed)
