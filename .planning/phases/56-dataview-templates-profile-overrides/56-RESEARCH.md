# Phase 56: Dataview templates & profile overrides - Research

**Researched:** 2026-05-02
**Domain:** Profile composition surface (validators + render-time resolvers) for declarative template overrides
**Confidence:** HIGH (pure codebase research, all claims cited file:line)

## Summary

Phase 56 is a pure profile-composition-surface phase: two new top-level keys (`mapping_rule_templates:`, `note_type_templates:`), one optional `id:` field on `mapping_rules`, four new dead-rule classes for the existing `dataview_queries:` validator, and a precedence ladder applied at render-time template selection. Zero engine work — Phase 31 (block engine), Phase 30 (composition with provenance), and Phase 55 (`predicate_flags:`) are all locked.

Every needed extension point is already in place: `_VALID_TOP_LEVEL_KEYS` (profile.py:172-179), `_KNOWN_NOTE_TYPES` (profile.py:181-184), `_deep_merge_with_provenance` (profile.py:245-274), the canonical-pattern `community_templates:` validator (profile.py:682-735), the `dataview_queries:` validator to extend (profile.py:737-763), the mapping-rules entry point (profile.py:1041-1051) → `validate_rules` (mapping.py:841-925), and the runtime resolver `_pick_community_template` (templates.py:1572-1610) which the two new override resolvers must compose with under the D-56.05 ladder.

**Primary recommendation:** Mirror `community_templates:` byte-for-byte for both new lists. Extend (not replace) `_deep_merge_with_provenance` to track a *list* of contributing paths per leaf — the current `dict[str, Path]` shape stores only the last writer, which is insufficient for D-56.06 §4's "cite all source paths" error contract. Refactor render-time selection into a single `_resolve_note_template(...)` that consults the three lists in ladder order; do **not** duplicate the warn-and-fall-back pattern three times.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-56.01:** TMPL-03 = dead-rule hardening only on the existing `dataview_queries:` validator at profile.py:741+. No new shape, no engine plumbing, no scope axis.
- **D-56.02:** Four dead-rule classes added at `validate_profile_preflight` for `dataview_queries:`:
  1. Unknown `${var}` references — reject query strings referencing variables outside the allowlist (planner enumerates from `_build_dataview_block` callers).
  2. Note-type with no possible mapped nodes — reject `dataview_queries.<note_type>` when `mapping_rules` + `folder_mapping` prove no node will resolve to that note_type.
  3. Empty/whitespace-only after substitution — extend Phase 31's empty-string check to (a) whitespace-only after strip and (b) renders empty if every `${var}` expanded to empty.
  4. Duplicate keys across `extends:`/`includes:` chain — reuses CFG-02 collision machinery (D-56.06 §4).
- **D-56.03:** Sibling keys, not unified discriminator. Three top-level lists, each `{match, pattern, template}`:
  - `community_templates:` — untouched from Phase 30
  - `mapping_rule_templates:` — match=`rule_id`, pattern=`<slug>`, template=`<fragment-path>`
  - `note_type_templates:` — match=`note_type`, pattern=`<one of _KNOWN_NOTE_TYPES>`, template=`<fragment-path>`
  Both new keys register into `_VALID_TOP_LEVEL_KEYS`.
- **D-56.04:** `mapping_rules` grows optional `id:` (slug `[a-z][a-z0-9_-]*`, unique within list). `validate_rules` in mapping.py is the injection point. Rules without `id:` stay valid (backward-compat).
- **D-56.05:** Strict precedence ladder, applied silently at render-time:
  1. `mapping_rule_templates`
  2. `community_templates`
  3. `note_type_templates`
  4. base profile template
  No error on cross-scope overlap. Within a list: first matching rule wins.
- **D-56.06:** CFG-02 collision detection is schema-only at `validate_profile_preflight`. Four collision classes:
  1. Duplicate `id:` in `mapping_rule_templates` (two entries same `pattern`/rule_id)
  2. Duplicate exact `pattern` within the same list
  3. Duplicate `note_type` keys in `note_type_templates`
  4. Duplicate `dataview_queries.<note_type>` across `extends:`/`includes:` chain
  **NOT detected:** glob/regex pattern overlap.
- **D-56.07:** Collision matrix as parametric tests under `tests/test_profile.py` or a new `tests/test_template_overrides.py` (planner discretion). Each of four classes gets ≥1 positive + ≥1 negative test.
- **D-56.08:** Every override `template:` is a whole template path (fragment under `.graphify/`). No merging, no patching, no per-block surgery. Path-confinement (`..`, absolute, leading `~`) ports verbatim from `community_templates:` validator.
- **D-56.09:** The three new lists inherit standard `_deep_merge_with_provenance` semantics (last-wins on lists). Cross-chain collision surfaces via D-56.06 §4 only for `dataview_queries:` (per-key dict merge).
- **D-56.10:** Update `docs/PROFILE-CONFIGURATION.md`: subsection per new key, precedence ladder as numbered list, four collision classes, one worked example.
- **D-56.11:** `docs/TEMPLATES.md` (Phase 55) gets one-paragraph forward-pointer to PROFILE-CONFIGURATION.md.
- **D-56.12:** No `docs/MIGRATION_V1_11.md`. No `community_templates:` deprecation.
- **D-56.13:** Per Phase 55 D-55.14: warn + fall back to default template on missing/unreadable override files. Port `_load_override_template`'s pattern (templates.py:1521-1568) verbatim.

### Claude's Discretion

- Test layout: new `tests/test_template_overrides.py` vs additions to `tests/test_profile.py` or `tests/test_profile_composition.py`.
- Slug regex for `mapping_rules.id:` — suggested `^[a-z][a-z0-9_-]*$`, max length aligned with existing slug validators (suggest reusing `_REPO_IDENTITY_MAX_LEN = 80` from naming.py:34).
- Validation message format — match Phase 30/31 wording exactly.
- Whether `mapping_rule_templates:` needs a graph-aware "unreachable rule" check (default: no).

### Deferred Ideas (OUT OF SCOPE)

- Per-block / per-frontmatter partial overrides (`blocks:` dict, `frontmatter_extra:` patch).
- Unified `template_overrides:` with `scope:` discriminator.
- Glob/regex pattern-overlap detection within a list.
- Graph-aware collision pass after build.
- `docs/MIGRATION_V1_11.md`.
- `graphify doctor` non-zero exit on override errors.
- Author-declared per-rule `priority:`.
- Promoting `dataview_queries:` to block-engine templates.
- `note_type_templates:` collapsed to `{note_type: path}` dict shape.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| TMPL-03 | Profile may declare per-note-type Dataview query templates validated at `validate_profile_preflight` (schema + dead-rule checks) | Phase 31 already shipped the schema half (profile.py:737-763 validator + templates.py:1240-1308 builder). Phase 56 adds four dead-rule classes (D-56.02). Allowlist enumeration from `_build_dataview_block` callsites — see §1 below. |
| CFG-01 | Composed profiles support scoped template overrides without breaking `extends:`/`includes:` merge semantics | Two new top-level keys `mapping_rule_templates:` + `note_type_templates:` mirror `community_templates:` (profile.py:682-735) byte-for-byte. Optional `id:` on `mapping_rules` enables targeting (D-56.04). Render-time ladder in templates.py composes with `_pick_community_template`. |
| CFG-02 | Deterministic validation errors when override precedence is ambiguous; collision matrix encoded in tests | Schema-only collision detection at `validate_profile_preflight`. Four classes (D-56.06). The §4 cross-chain `dataview_queries:` case requires extending `_deep_merge_with_provenance` to record a *list* of contributors per leaf — current shape `dict[str, Path]` is last-writer-only (profile.py:35, 56). |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| New top-level key validation (`mapping_rule_templates:`, `note_type_templates:`) | profile.py preflight | — | All schema validation lives here per established pattern (community_templates:682-735, dataview_queries:737-763) |
| Optional `id:` on mapping_rules | mapping.py `validate_rules` | profile.py (entry point at 1041-1051) | profile.py delegates mapping-rule validation to mapping.py; new field validation lands inside `validate_rules` (mapping.py:841) |
| Cross-chain collision detection (D-56.06 §4) | profile.py composition layer | provenance map | Requires extending `_deep_merge_with_provenance` provenance shape from `dict[str, Path]` to `dict[str, list[Path]]` |
| Render-time precedence ladder (D-56.05) | templates.py | — | Co-located with `_pick_community_template` (1572-1610); refactor into `_resolve_note_template` consuming all three lists |
| Warn-and-fall-back on bad override file | templates.py `_load_override_template` | — | Existing pattern (1521-1568); two new resolvers reuse same helper |
| Documentation | docs/PROFILE-CONFIGURATION.md | docs/TEMPLATES.md (forward pointer only) | Per D-56.10 / D-56.11 |

## Standard Stack

### Core (already in repo, no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `string.Template` | 3.10+ | `${var}` substitution for DV queries | Phase 31 standard; CLAUDE.md forbids Jinja2 |
| Python stdlib `re` | 3.10+ | Slug regex for `mapping_rules.id:` and `${var}` extraction | Used throughout codebase (mapping.py:3) |
| Python stdlib `fnmatch` | 3.10+ | Glob matching for label patterns | Used by `_pick_community_template` (templates.py:1572-1610) |
| Python stdlib `pathlib.Path` | 3.10+ | Path-confinement checks | Used in existing community_templates: validator (profile.py:716-728) |
| PyYAML | optional, already declared | Parse profile.yaml | Optional dep — preflight checks PyYAML availability before parsing (profile.py:1485-1495). New validators run on already-parsed dicts so they don't need PyYAML at runtime. |

**Installation:** No new dependencies. Project constraint per CLAUDE.md: "No new required dependencies".

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dict[str, list[Path]]` provenance shape | New parallel `dict[str, list[Path]]` map alongside existing | Parallel map keeps `_deep_merge_with_provenance` signature stable for callers but doubles memory. Recommended: extend in place; only one caller (`_resolve_profile_chain`) and the field type is internal. |
| Three sequential resolver calls | Single `_resolve_note_template(node, profile, default)` consulting all three lists | Single resolver eliminates duplicate fall-back logic and makes the ladder explicit in one place. Recommended. |
| `note_type_templates: {note_type: path}` dict shape | Parallel list shape `[{match, pattern, template}, ...]` | Per CONTEXT.md deferred ideas: dict shape is cleaner but parallel-list shape was chosen for sibling consistency. Locked. |

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       profile.yaml + extends/includes                    │
└────────────────┬────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ _resolve_profile_chain (profile.py:350)                                  │
│   walks extends → includes → own                                         │
│   merges via _deep_merge_with_provenance                                 │
│   → ResolvedProfile{composed, chain, provenance: dict[str, Path]}        │
│   ⚠ Phase 56 EXTENDS provenance shape → dict[str, list[Path]]            │
└────────────────┬────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ validate_profile_preflight (profile.py:1426)                             │
│   Layer 1: validate_profile (schema, profile.py:651)                     │
│     • community_templates: validator (existing, 682-735)                 │
│     • dataview_queries: validator (existing, 737-763)                    │
│     ➕ NEW: mapping_rule_templates: validator (mirror 682-735)           │
│     ➕ NEW: note_type_templates: validator (mirror 682-735)              │
│     ➕ NEW: dataview_queries: dead-rule checks D-56.02 §1-3              │
│     • mapping_rules: → validate_rules (mapping.py:841)                   │
│       ➕ NEW: optional id: field validation (slug + uniqueness)         │
│   Layer 2: NEW collision detection (CFG-02, D-56.06 §1-4)                │
│     consumes provenance map for §4 enumeration                           │
└────────────────┬────────────────────────────────────────────────────────┘
                 │ (errors aggregated, never raised)
                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Render path (templates.py)                                               │
│   render_note (1316+)              render_moc / community (1614+)        │
│       │                                  │                                │
│       ▼                                  ▼                                │
│   _build_dataview_block (1240) — substitutes ${community_tag}, ${folder} │
│       │                                  │                                │
│       ▼                                  ▼                                │
│   ➕ NEW: _resolve_note_template(node, profile, default)                 │
│         consults in ladder order (D-56.05):                              │
│           1. mapping_rule_templates  (NEW)                               │
│           2. _pick_community_template (existing 1572-1610)               │
│           3. note_type_templates     (NEW)                               │
│           4. default base template                                       │
│         delegates file load to _load_override_template (1521)            │
│         → warn + fall back to default on missing/invalid                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new files required (planner discretion on test layout):

```
graphify/
├── profile.py            # ➕ extend _VALID_TOP_LEVEL_KEYS, ➕ 2 new validators,
│                         #    ➕ 4 collision detectors, extend provenance shape
├── mapping.py            # ➕ extend validate_rules with optional id: field
└── templates.py          # ➕ refactor _pick_community_template into
                          #    _resolve_note_template (or compose 3 resolvers)

tests/
├── test_profile.py                # OR test_profile_composition.py — extend
│                                  # collision-class parametric tests
├── test_template_overrides.py     # NEW (optional per D-56.07) — collision matrix
└── test_mapping.py                # ➕ id: field validation tests

docs/
├── PROFILE-CONFIGURATION.md       # ➕ D-56.10 — major update
└── TEMPLATES.md                   # ➕ D-56.11 — one-paragraph forward pointer
```

### Pattern 1: Mirror community_templates: validator
**What:** Port profile.py:682-735 verbatim, swapping `match` allowlist and `pattern` type rules.
**When to use:** For both `mapping_rule_templates:` and `note_type_templates:` validation blocks.
**Example structure (canonical, profile.py:682-735):**
```python
ct = profile.get("community_templates")
if ct is not None:
    if not isinstance(ct, list):
        errors.append("'community_templates' must be a list")
    else:
        for idx, rule in enumerate(ct):
            prefix = f"community_templates[{idx}]"
            if not isinstance(rule, dict):
                errors.append(f"{prefix}: must be a mapping (dict)")
                continue
            match = rule.get("match")
            if match not in {"label", "id"}:           # ← Phase 56 swaps this allowlist
                errors.append(f"{prefix}.match must be 'label' or 'id' (got {match!r})")
            pattern = rule.get("pattern")
            # ... pattern type checks per match value ...
            template = rule.get("template")
            if not isinstance(template, str) or not template:
                errors.append(f"{prefix}.template must be a non-empty string")
            elif ".." in template:                       # ← path-confinement, ports verbatim
                errors.append(f"{prefix}.template contains '..' — fragment paths must stay inside .graphify/")
            elif Path(template).is_absolute():
                errors.append(f"{prefix}.template is an absolute path — must be relative to .graphify/")
            elif template.startswith("~"):
                errors.append(f"{prefix}.template starts with '~' — must be relative to .graphify/")
            extra = set(rule) - {"match", "pattern", "template"}
            if extra:
                errors.append(f"{prefix}: unknown keys {sorted(extra)} — only 'match', 'pattern', 'template' are supported")
```

### Pattern 2: Render-time runtime resolver with warn-and-fall-back
**What:** A pick function returns the override template, or default; a load helper handles every failure mode by warning + returning default.
**When to use:** For all three override lists.
**Example (canonical, templates.py:1521-1568):**
```python
def _load_override_template(rel_path: str, vault_dir, default_template):
    if vault_dir is None:
        return default_template
    try:
        graphify_dir = Path(vault_dir) / ".graphify"
        canonical = validate_vault_path(rel_path, graphify_dir)
    except (ValueError, OSError) as exc:
        print(f"[graphify] community_templates override path rejected ({rel_path}): {exc} — using default", file=sys.stderr)
        return default_template
    if not canonical.exists():
        print(f"[graphify] community_templates override missing ({rel_path}) — using default", file=sys.stderr)
        return default_template
    # ... read + validate_template + warn-and-fall-back ...
    return _BlockTemplate(text)
```
**Phase 56 extension:** Generalize the warn prefix to take the override-list name (e.g., `mapping_rule_templates`, `note_type_templates`) so users can tell which list's override failed.

### Anti-Patterns to Avoid
- **Duplicating fall-back logic three times** — refactor `_load_override_template` to take a `list_name: str` parameter and reuse it across all three resolvers.
- **Detecting glob/regex overlap (e.g., `Auth*` vs `AuthService`)** — explicitly out of scope per D-56.06.
- **Raising on validation errors** — every validator must return `list[str]` and let preflight aggregate (mapping.py:841 contract: "Returns a list of error strings — empty means valid. Never raises.")
- **Using last-writer-only provenance for collision enumeration** — current shape `dict[str, Path]` (profile.py:35, 56) records only the most recent contributor; D-56.06 §4 needs *all* contributors.
- **Adding `id:` validation in profile.py instead of mapping.py** — `validate_rules` is the canonical mapping-rule validator (mapping.py:841); profile.py delegates to it (profile.py:1050).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path-confinement (`..`, absolute, `~`) | Custom regex / string checks | Port profile.py:716-728 verbatim | Three-line pattern, already battle-tested by Phase 30 |
| Template fall-back UX | Custom error/warn handling | Existing `_load_override_template` (templates.py:1521) | D-56.13 explicitly requires byte-for-byte parity |
| Glob matching for `pattern` | Regex translation | `fnmatch.fnmatchcase` (used by `_pick_community_template` 1572-1610, templates.py:1602) | Portable, case-sensitive, already standard in this codebase |
| `${var}` extraction from query strings | Hand-written parser | `string.Template.pattern` regex or `re.findall(r'\$\{(\w+)\}', text)` | stdlib, sufficient for D-56.02 §1 unknown-var detection |
| Slug validation | Custom string check | `re.fullmatch(r'^[a-z][a-z0-9_-]*$', slug)` | Standard pattern; mirror style of `normalize_repo_identity` (naming.py:53-64) |
| Cross-chain provenance enumeration | New side-channel structure | Extend `_deep_merge_with_provenance` provenance shape to `dict[str, list[Path]]` | Already-correct merge order (extends → includes → own) means the list is already in priority sequence |

**Key insight:** Phase 56 is overwhelmingly a "port and parameterize" exercise. The two new override-list validators are 95% identical to community_templates: at profile.py:682-735. The two new render-time resolvers are 95% identical to `_pick_community_template` at templates.py:1572-1610. The single most novel piece of work is the provenance-shape extension to support D-56.06 §4 multi-source error enumeration.

## Common Pitfalls

### Pitfall 1: Provenance map is last-writer-only
**What goes wrong:** D-56.06 §4 requires "deterministic error citing all source paths" for `dataview_queries.<note_type>` collisions across the extends/includes chain, but the current `provenance: dict[str, Path]` (profile.py:35, 56, 252) records only the *most recent* writer at each leaf — earlier contributors are silently overwritten on every merge.
**Why it happens:** `_deep_merge_with_provenance` writes `provenance[dotted] = source_path` unconditionally on every leaf overwrite (profile.py:274). The merge order `extends → includes → own` (profile.py:464-491) means the "own" file ends up as the recorded provenance for any colliding leaf.
**How to avoid:** Extend the provenance shape to `dict[str, list[Path]]` (or `dict[str, list[tuple[Path, Any]]]` if you also want to capture the conflicting *values*). Append on every leaf write instead of overwriting. Update the type alias at profile.py:35 and the `ResolvedProfile` field at profile.py:56. Audit existing call sites for assumptions about scalar shape (search: `provenance[`, `.provenance[`).
**Warning signs:** Tests for D-56.06 §4 that assert "error message names FILE_A and FILE_B" — they fail because only FILE_B (the last writer) is recorded.

### Pitfall 2: PyYAML not always available at validation time
**What goes wrong:** A new validator that calls `yaml.safe_load` would fail in environments where PyYAML is not installed.
**Why it happens:** PyYAML is an optional dep (`graphifyy[obsidian]`); preflight checks for it explicitly at profile.py:1485-1495 before parsing the entry profile.yaml.
**How to avoid:** Phase 56 validators run on already-parsed dicts (the `composed` field of `ResolvedProfile`); they never re-parse YAML. As long as new validators take a `profile: dict` argument and return `list[str]`, PyYAML availability is irrelevant.
**Warning signs:** None expected if the pattern is followed; this is a "do not introduce" pitfall.

### Pitfall 3: `_KNOWN_NOTE_TYPES` vs `_NOTE_TYPES` confusion
**What goes wrong:** Validating `note_type_templates.pattern` against the wrong allowlist.
**Why it happens:** Two distinct sets exist:
- `profile._KNOWN_NOTE_TYPES` (profile.py:184) — `{moc, community, thing, statement, person, source, code}` — the Phase 31 allowlist used by `dataview_queries:` validation.
- `templates._NOTE_TYPES` (templates.py:50-52) — same seven values, but defined separately to break the templates ↔ profile import cycle (per profile.py:179 comment).
**How to avoid:** `note_type_templates.pattern` validation lives in profile.py and must use `profile._KNOWN_NOTE_TYPES`. Mirror the existing `dataview_queries:` validator at profile.py:752-758 exactly.
**Warning signs:** ImportError or stale-allowlist drift if the wrong constant is referenced.

### Pitfall 4: D-56.02 §2 ("note-type with no possible mapped nodes") false positives
**What goes wrong:** Rejecting a valid `dataview_queries.thing` entry because no `mapping_rules` rule mentions `thing` — but `mapping.py:401-403` has a built-in topology fallback that produces `note_type=thing` for any non-code god node, even with zero mapping_rules. Same for `note_type=statement` (mapping.py:405) and `note_type=code` (mapping.py:401-402).
**Why it happens:** The naive algorithm "set of `then.note_type` across all mapping_rules" misses the topology fallback path at mapping.py:397-406.
**How to avoid:** The reachable note_type set is **always** `{thing, statement, code} ∪ {then.note_type for rule in mapping_rules}`. For MOC and community, the set always includes `{moc, community}` (rendered via `_render_moc_like` at templates.py:1614+ regardless of mapping_rules). Net effect: the only note_types that can ever be "unreachable" are `person` and `source` — and only when no `mapping_rules` rule produces them. Be conservative: emit only when fully provable, never on heuristic.
**Warning signs:** Tests that exercise `dataview_queries.code` with empty mapping_rules and expect rejection — they would falsely reject valid configs.

### Pitfall 5: D-56.02 §1 allowlist must be derived from actual substitution call sites
**What goes wrong:** Allowlisting variables that aren't actually substituted (false negatives at runtime — `${vault_root}` in the query stays literal).
**Why it happens:** The CONTEXT.md hint mentions `${community_tag}, ${note_type}, ${vault_root}` as the *expected* set, but the actual substitution at templates.py:1290-1293 plumbs only **two** variables: `community_tag` and `folder`. (See §1 below for the full enumeration.)
**How to avoid:** The allowlist for D-56.02 §1 is exactly `{community_tag, folder}` — nothing else. If the planner wants future-extension headroom they can codify the allowlist as a module-level constant adjacent to `_build_dataview_block`, but the *value today* is two strings.
**Warning signs:** Allowlist that includes `note_type` or `vault_root` will incorrectly accept queries that render with literal `${...}` text in them.

### Pitfall 6: Edge case — `mapping_rule_templates: []` must be a no-op
**What goes wrong:** Validating an empty list as an error.
**Why it happens:** Pattern in profile.py:683-684 explicitly handles this — `ct is not None` guards entry, then `isinstance(ct, list)` validates shape; empty list iterates zero times, no errors emitted. Mirror exactly.
**How to avoid:** Use the same `ct is not None` then `isinstance(ct, list)` then `for idx, rule in enumerate(ct)` shape.
**Warning signs:** Test `test_mapping_rule_templates_empty_list_accepted` failing with "list must contain at least one entry" — wrong error.

### Pitfall 7: Edge case — render-time fall-back vs preflight rejection
**What goes wrong:** Render-time resolver tries to handle preflight-caught errors (path traversal, absolute path) and silently falls back, masking a bug.
**Why it happens:** `_load_override_template` at templates.py:1521-1568 is defensive — it catches path-escape via `validate_vault_path`. Preflight already rejects these via path-confinement checks at profile.py:716-728.
**How to avoid:** Preflight is the canonical defense. Render-time fall-back exists for runtime conditions only: missing file, unreadable file, invalid template body. The two are not redundant — preflight protects users who run `--validate-profile`; render-time fall-back protects users who skip preflight or whose vault state changes between preflight and render. Keep both.
**Warning signs:** None; this is correct-by-design. Just don't try to consolidate.

## Code Examples

### Verified pattern: Slug regex in this codebase
```python
# Source: graphify/naming.py:53-64 (canonical slug normalization style)
_REPO_IDENTITY_MAX_LEN = 80

def normalize_repo_identity(value: str) -> str:
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError("repo identity must not contain path segments or '..'")
    raw = value.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    # ...
```
**Phase 56 adaptation (D-56.04, suggested):**
```python
_RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
_RULE_ID_MAX_LEN = 80  # mirror _REPO_IDENTITY_MAX_LEN

# Inside validate_rules (mapping.py:841+), after shape checks per rule:
rule_id = rule.get("id")
if rule_id is not None:
    if not isinstance(rule_id, str):
        errors.append(f"{prefix}.id: must be a string (got {type(rule_id).__name__})")
    elif len(rule_id) > _RULE_ID_MAX_LEN:
        errors.append(f"{prefix}.id: length {len(rule_id)} exceeds cap {_RULE_ID_MAX_LEN}")
    elif not _RULE_ID_PATTERN.fullmatch(rule_id):
        errors.append(f"{prefix}.id: must match pattern {_RULE_ID_PATTERN.pattern!r} (got {rule_id!r})")

# After per-rule loop, uniqueness check:
seen_ids: dict[str, int] = {}
for idx, rule in enumerate(rules):
    if not isinstance(rule, dict):
        continue
    rid = rule.get("id")
    if isinstance(rid, str) and rid in seen_ids:
        errors.append(
            f"mapping_rules[{idx}].id: duplicate id {rid!r} — also defined at "
            f"mapping_rules[{seen_ids[rid]}]"
        )
    elif isinstance(rid, str):
        seen_ids[rid] = idx
```

### Verified pattern: Two-phase substitution for ${var} extraction (D-56.02 §1)
```python
# Source: graphify/templates.py:1240-1300 (_build_dataview_block)
import string

# Phase 56 D-56.02 §1: derive allowlist from THIS call site
_DATAVIEW_QUERY_VARS = frozenset({"community_tag", "folder"})

def _validate_dataview_query_vars(query: str, key: str) -> list[str]:
    """Reject ${var} references outside the allowlist."""
    errors: list[str] = []
    # string.Template.pattern matches ${name} and $name
    for match in string.Template.pattern.finditer(query):
        name = match.group("named") or match.group("braced")
        if name and name not in _DATAVIEW_QUERY_VARS:
            errors.append(
                f"dataview_queries.{key}: unknown ${{{name}}} — "
                f"valid vars are: {sorted(_DATAVIEW_QUERY_VARS)}"
            )
    return errors
```

### Verified pattern: Provenance enumeration for D-56.06 §4
```python
# Phase 56 extension to graphify/profile.py:35, 56
# (current shape):
provenance: dict[str, Path] = {}

# (extended shape):
provenance: dict[str, list[Path]] = {}

# Inside _deep_merge_with_provenance (profile.py:264-273):
# (current):
provenance[dotted] = source_path
# (extended — append-on-write):
provenance.setdefault(dotted, []).append(source_path)

# Collision detector (Phase 56 D-56.06 §4):
def _detect_dataview_collisions(provenance: dict[str, list[Path]]) -> list[str]:
    errors: list[str] = []
    for dotted, sources in provenance.items():
        if not dotted.startswith("dataview_queries."):
            continue
        if len(sources) > 1:
            note_type = dotted.split(".", 1)[1]
            paths = ", ".join(str(p) for p in sources)
            errors.append(
                f"dataview_queries.{note_type}: collision across composition chain — "
                f"defined in: {paths}"
            )
    return errors
```

## Allowlist of `${var}` names for D-56.02 §1 (HIGH confidence — exhaustive enumeration)

Every callsite of `_build_dataview_block` plus the substitution call inside it:

| File:Line | Caller | Substituted vars |
|-----------|--------|------------------|
| `graphify/templates.py:1290-1293` | `_build_dataview_block` itself (the only `safe_substitute` on the DV query string) | `community_tag`, `folder` |
| `graphify/templates.py:1439-1444` | `render_note` calls `_build_dataview_block(profile, community_tag or "", ctx.get("folder", ""), note_type)` | (delegates to above; same allowlist) |
| `graphify/templates.py:1707-1710` | `_render_moc_like` calls `_build_dataview_block(profile, community_tag, folder, effective_note_type)` | (delegates to above; same allowlist) |

**Final allowlist:** `{community_tag, folder}` — exactly two strings.

**Important nuances:**
1. The default `obsidian.dataview.moc_query` (profile.py:109) already uses `${community_tag}`. This must validate clean.
2. `note_type` is **NOT** a substituted var — it is the *key* used to *look up* the query (profile.py:115, templates.py:1273), not a value injected into the query body.
3. `vault_root` is **NOT** plumbed — the CONTEXT.md hint that mentioned it was speculative.
4. Any extension in a future phase (e.g., adding `${node_id}` substitution) requires extending both the allowlist constant AND the `safe_substitute` call site at templates.py:1290 — they are paired.

## Existing `community_templates:` runtime resolver call chain (HIGH confidence)

```
render_note (templates.py:1316)                 _render_moc_like (templates.py:1614)
       │                                                  │
       │ (no override consultation today)                 ▼
       │                                       _pick_community_template (1572-1610)
       │                                                  │
       │                                                  ▼
       │                                       fnmatch.fnmatchcase  OR  exact-id compare
       │                                                  │
       │                                                  ▼
       │                                       _load_override_template (1521-1568)
       │                                                  │
       │                                                  ▼
       │                                       validate_vault_path → exists → read_text → validate_template
       │                                                  │
       └──────────────────────────────────────────────────▼
                                              return _BlockTemplate(text)  OR  default_template + stderr warn
```

**Phase 56 insertion proposal:** Refactor into a single `_resolve_note_template`:

```python
def _resolve_note_template(
    *,
    node_id: str | None,        # for mapping_rule_templates lookup; None for MOC/community
    rule_id: str | None,        # the mapping_rule.id that classified this node, if any
    community_id: int | None,   # for community_templates lookup; None for non-community contexts
    community_name: str | None,
    note_type: str,             # for note_type_templates lookup
    profile: dict,
    vault_dir,
    default_template: "string.Template",
) -> "string.Template":
    """Resolve the template for a node by walking the D-56.05 ladder."""
    # 1. mapping_rule_templates (NEW)
    if rule_id is not None:
        rules = profile.get("mapping_rule_templates") or []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            if rule.get("match") == "rule_id" and rule.get("pattern") == rule_id:
                return _load_override_template(
                    rule.get("template"), vault_dir, default_template,
                    list_name="mapping_rule_templates",
                )
    # 2. community_templates (existing)
    if community_id is not None and community_name is not None:
        result = _pick_community_template(
            community_id, community_name, profile, vault_dir, default_template,
        )
        if result is not default_template:
            return result
    # 3. note_type_templates (NEW)
    rules = profile.get("note_type_templates") or []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if rule.get("match") == "note_type" and rule.get("pattern") == note_type:
            return _load_override_template(
                rule.get("template"), vault_dir, default_template,
                list_name="note_type_templates",
            )
    # 4. base template
    return default_template
```

**Insertion points:**
- `_render_moc_like` at templates.py:1748-1750 — currently calls `_pick_community_template(community_id, community_name, profile, vault_dir, default_template)`. Replace with `_resolve_note_template(rule_id=None, community_id=community_id, community_name=community_name, note_type=template_key, ...)`.
- `render_note` at templates.py:1487-1494 — currently uses `templates[note_type]` directly. Wrap with `_resolve_note_template(rule_id=ctx.get("rule_id"), community_id=None, community_name=None, note_type=note_type, default_template=templates[note_type], ...)`.

**To pass `rule_id`:** `ClassificationContext` (mapping.py, dataclass) doesn't currently expose the matched mapping_rules index. Either (a) extend it with an optional `rule_id: str | None` field populated when the matched rule has `id:`, or (b) thread it via the `classification_context` dict path. (a) is cleaner and aligns with how Phase 55 added fields to substitution_ctx.

## `_deep_merge_with_provenance` provenance map shape (HIGH confidence)

**Current shape (profile.py:35, 56, 252, 274):**
```python
provenance: dict[str, Path]
# Each leaf write: provenance[dotted] = source_path  ← OVERWRITES previous writer
```

**Merge order (profile.py:445-491):**
1. Each `extends:` parent (line 464-467: `_deep_merge_with_provenance(composed, parent_data, parent_path, provenance)`)
2. Each `includes:` entry (line 485-487: same call)
3. Own data LAST (line 490-491: `_deep_merge_with_provenance(composed, data, canonical, provenance)`)

**Implication for D-56.06 §4:** With current shape, after composition the provenance for `dataview_queries.moc` will be the *last* writer in the chain — typically the user's `profile.yaml`. Earlier contributors (parents in `extends:`, files in `includes:`) are lost. Cannot enumerate "all source profiles" as D-56.06 §4 requires.

**Required Phase 56 change:**
- profile.py:35 and profile.py:56: change type from `dict[str, Path]` to `dict[str, list[Path]]`.
- profile.py:274: change `provenance[dotted] = source_path` to `provenance.setdefault(dotted, []).append(source_path)`.
- The list will be in deterministic merge order: extends-parent(s) first, then includes, then own — matching D-56.05 priority order naturally.
- Auditing existing readers: only `validate_profile_preflight` (profile.py:1481, 1503) and `report_validate_profile_text` (search) currently consume provenance. Update those call sites to handle the new list shape.

**Test reference for current shape:** `test_dataview_queries_provenance_in_validate_profile_output` (tests/test_profile.py:1711+) — Phase 56 must extend or amend this test for the new list shape.

## Mapping rules schema injection point for `id:` (HIGH confidence)

**Where:** Inside `validate_rules` at `graphify/mapping.py:841-925`, specifically inside the per-rule loop at lines 863-921.

**Pattern for optional-field validation in this validator:**
- Optional `then.folder` (mapping.py:910-913): pulled with `.get`, validated only when `is not None`, errors aggregated to the same list. Mirror this exactly.
- Unknown-keys rejection (mapping.py:916-921): `set(then) - {"note_type", "folder"}` — the analogous check for the rule top level should be extended to allow `"id"`. **Currently no top-level unknown-key check exists** for mapping_rules — confirm by reading lines 863-921 (only `when`, `then` are required; no rejection of extras). Phase 56 may want to *add* a rule-top-level unknown-key rejection at the same time it adds `id:`.

**Suggested injection (after line 871, before the matcher logic at 873):**
```python
# Optional id: field validation (Phase 56, D-56.04)
rule_id = rule.get("id")
if rule_id is not None:
    if not isinstance(rule_id, str):
        errors.append(f"{prefix}.id: must be a string (got {type(rule_id).__name__})")
    elif len(rule_id) > _RULE_ID_MAX_LEN:
        errors.append(f"{prefix}.id: length {len(rule_id)} exceeds cap {_RULE_ID_MAX_LEN}")
    elif not _RULE_ID_PATTERN.fullmatch(rule_id):
        errors.append(f"{prefix}.id: must match pattern '^[a-z][a-z0-9_-]*$' (got {rule_id!r})")
```

**Uniqueness check:** Add a single post-loop pass (after line 921, before the dead-rule detection at line 924), iterating once over rules to collect seen ids and flag duplicates. Pattern shown in "Code Examples" above.

## "Note-type with no possible mapped nodes" detection (D-56.02 §2) — HIGH confidence

**Algorithm:**
```python
# Phase 56, D-56.02 §2
def _reachable_note_types(profile: dict) -> set[str]:
    """The set of note_types any node could resolve to under this profile.

    Sources:
    - Explicit mapping_rules: every then.note_type value
    - Built-in topology fallback (mapping.py:397-406):
        * code god nodes → "code"
        * other god nodes → "thing"
        * everything else → "statement"
    - MOC + community rendering paths (templates.py:1614+) always produce these
      regardless of mapping_rules.
    """
    reachable = {"moc", "community", "thing", "statement", "code"}
    for rule in profile.get("mapping_rules") or []:
        if not isinstance(rule, dict):
            continue
        then = rule.get("then")
        if isinstance(then, dict) and isinstance(then.get("note_type"), str):
            reachable.add(then["note_type"])
    return reachable
```

**Practical impact:** Of the seven values in `_KNOWN_NOTE_TYPES = {moc, community, thing, statement, person, source, code}`, only `person` and `source` are *ever* potentially unreachable. All five others have a built-in production path independent of mapping_rules.

**Cite:**
- Built-in topology fallback: mapping.py:397-406 (note_type assignment without mapping_rules match)
- Mapping rule extraction: mapping.py:383-386 (then.note_type validated against `_NOTE_TYPES` allowlist)
- MOC/community rendering: templates.py:1614+ (`_render_moc_like` always renders moc/community per community in `communities` dict)

**`folder_mapping` does NOT contribute additional note_types** — `_resolve_folder` (mapping.py:248-256) only looks up the folder *for* a given note_type; it does not produce note_types. Confirmed by reading `_effective_folder_mapping` (mapping.py:269-288): the dict is `{note_type: folder_path}`, not the inverse.

## Test infrastructure patterns (HIGH confidence)

**Existing `community_templates:` validation tests:** Located in `tests/test_profile_composition.py:385+`. Pattern:
- Fixture vault copied via `_copy_fixture("community_templates", tmp_path)` (line 391).
- Helper `_render_moc_with_profile(vault, profile_overrides, community_id, community_name)` (line 414) loads the profile, applies overrides, builds a 1-node nx.Graph, and calls `_render_moc_like` directly.
- Override-marker assertion pattern: `assert "OVERRIDE_TEMPLATE_MARKER" in text`.
- Warn-and-fall-back tests use `capsys` (e.g., `test_override_template_path_escape_falls_back` at line 540): assert `OVERRIDE_TEMPLATE_MARKER not in text` AND `"[graphify] community_templates override" in captured.err`.
- Tests for schema validation (line 508-541) construct profile dicts inline and pass to `validate_profile`, asserting expected error substring.

**Existing `dataview_queries:` validation tests:** Located in `tests/test_profile.py:1612-1740`. Pattern:
- Direct `validate_profile(dict)` calls — no fixture vault needed for schema-only checks.
- One assertion per test (single error class).
- Provenance test at line 1711+ uses `tmp_path` to build a real extends/includes chain and reads the resolved provenance map.

**Phase 56 recommendation per D-56.07:**
- Schema-only tests for the four collision classes → extend `tests/test_profile.py` (matches existing dataview_queries pattern).
- Runtime resolver tests for the precedence ladder + warn-and-fall-back → extend `tests/test_profile_composition.py` (matches existing community_templates pattern; reuse the fixture vault).
- `mapping_rules.id:` field validation → extend `tests/test_mapping.py`.
- Whether to create a dedicated `tests/test_template_overrides.py` is genuinely planner discretion — the codebase pattern is "one test file per module," and `test_profile.py` is already 1700+ lines. Splitting is reasonable; consolidating is also reasonable.

**Parametric test pattern:** No prior `pytest.mark.parametrize` on validation tests in test_profile.py; existing style is one test function per assertion. Phase 56 D-56.07 ("collision matrix") may prefer parametrize for compactness (4 classes × 2 cases = 8 tests as one parametrized function), but the existing style of one test function per case is also acceptable.

## `mapping_rules.id:` rejection rules (HIGH confidence)

| Check | Rule | Error pattern |
|-------|------|---------------|
| Type | Must be `str` | `"mapping_rules[N].id: must be a string (got <type>)"` |
| Length | ≤ 80 chars (mirror `_REPO_IDENTITY_MAX_LEN` at naming.py:34) | `"mapping_rules[N].id: length L exceeds cap 80"` |
| Pattern | `^[a-z][a-z0-9_-]*$` (matches CONTEXT.md D-56.04 suggestion) | `"mapping_rules[N].id: must match pattern '^[a-z][a-z0-9_-]*$' (got 'X')"` |
| Uniqueness within mapping_rules | Two rules with same `id` → error citing both indices | `"mapping_rules[N].id: duplicate id 'X' — also defined at mapping_rules[M]"` |
| Optional | Absent `id:` → no error (backward-compat per D-56.04) | (no error emitted) |

**Existing slug validators in this codebase:**
- `naming.py:53-64` (`normalize_repo_identity`) — uses `r"[^a-z0-9]+"` collapse + `_REPO_IDENTITY_MAX_LEN = 80` cap. Style/regex match.
- `elicit.py:64+` (`_slug_dimension`) — internal slug derivation, not user-facing.
- `ingest.py:255` — `re.sub(r"[^\w]", "_", question.lower())` truncated to 50 — for filenames, not validation.

The `^[a-z][a-z0-9_-]*$` pattern from CONTEXT.md is novel to Phase 56 (no exact prior use), but matches conventional slug discipline and is consistent with `naming.py` style.

## Path-confinement port (HIGH confidence)

**Canonical pattern (profile.py:716-728):**
```python
elif ".." in template:
    errors.append(f"{prefix}.template contains '..' — fragment paths must stay inside .graphify/")
elif Path(template).is_absolute():
    errors.append(f"{prefix}.template is an absolute path — must be relative to .graphify/")
elif template.startswith("~"):
    errors.append(f"{prefix}.template starts with '~' — must be relative to .graphify/")
```

**Subtleties:**
1. Uses `Path(template).is_absolute()` — `pathlib`, not `os.path`. Consistent with rest of profile.py (e.g., line 257-265 `_taxonomy_path_errors`).
2. The `..` check is a substring check (`".." in template`), not a `Path.parts` check. This catches `foo/../bar` but NOT something like `foo/..bar` — the substring is overly permissive for matching `..bar`. Mirror exactly to maintain parity (Phase 30 chose substring intentionally — `..bar` is a valid filename and shouldn't be rejected, but the test for that nuance can be checked at `tests/test_profile.py` if needed).
3. Order of checks matters: `..` before absolute, absolute before `~`. Each elif means only the first matching error fires per rule. Mirror exactly.
4. Error wording uses `.graphify/` (with trailing slash). Mirror exactly.
5. `_taxonomy_path_errors` (profile.py:277-296) uses a slightly different check style (`path.is_absolute()` from `Path(value)`, `value.startswith("~")`, `".." in path.parts`). The `community_templates:` validator uses substring `".." in template`. **Use the community_templates: style for Phase 56 parity** (not the taxonomy style).

## Tempting but out of scope

Per CONTEXT.md `<deferred>` and `<domain>` Out-of-scope sections — do not let research surface tempt scope creep:

- **Per-block / per-frontmatter overrides** — would require `blocks:` dict + naming convention. Defer.
- **Unified `template_overrides:` with `scope:` discriminator** — would require `community_templates:` deprecation. Defer.
- **Glob/regex pattern overlap detection** — undecidable in general; out of scope per D-56.06.
- **Graph-aware collision pass after build** — changes validation contract from graph-blind to graph-aware. Defer.
- **`graphify doctor` non-zero exit** — keeps Phase 55 D-55.14 stance (warn + fall back).
- **Author-declared per-rule `priority:`** — the strict ladder IS the design.
- **Promoting `dataview_queries:` to block-engine templates** — would couple `_BlockTemplate` to a config key it doesn't touch.
- **Dict-shape `note_type_templates:`** — parallel-list shape chosen for sibling consistency with the other two override lists.

## Project Constraints (from CLAUDE.md)

- **Python 3.10+** — use `dict[K, V]`, `str | None`; no `Dict`, no `Optional[]`. (CLAUDE.md "Type Hints")
- **Stdlib only** — no new required deps. PyYAML stays optional. (CLAUDE.md Constraints, "No new required dependencies")
- **`from __future__ import annotations` first import** — present in every existing module; Phase 56 additions to existing modules inherit this.
- **No Jinja2 / no template lib** — `string.Template` only. Already enforced; Phase 56 adds no template-library work.
- **Pure unit tests, no fs side effects outside `tmp_path`** — all collision/validator tests can use in-memory dicts; render tests use `tmp_path` per existing community_templates: test pattern.
- **One test file per module** — convention; planner discretion to add `tests/test_template_overrides.py` despite slight tension with this rule (existing precedent: `tests/test_profile_composition.py` is a sibling to `test_profile.py`).
- **Docstrings on public functions and classes** — preserve (existing validators all have detailed docstrings, e.g., mapping.py:842-855).
- **Error wording style** — deterministic, includes index/key + bad value + rule. Mirror Phase 30/31 wording verbatim per D-56.13 (CONTEXT.md "Validation message format").
- **Stderr for warnings** — `print(f"[graphify] ...", file=sys.stderr)` pattern. Mirror community_templates: resolver (templates.py:1541-1564) verbatim.
- **GSD workflow enforcement** — Phase 56 changes routed through `/gsd-execute-phase`.

## Runtime State Inventory

**N/A — Phase 56 is a code/schema-only addition.** No rename, refactor, migration, or string replacement. No runtime state outside the codebase exists for this surface (no databases, no external service config, no OS registrations, no installed-package artifacts that embed override identifiers). Stored data category: empty by inspection — `dataview_queries:`, `community_templates:`, `mapping_rule_templates:`, `note_type_templates:` are all schema-only profile keys consumed at render time, never persisted. Confirmed by grepping: no `pickle`, no DB writes, no service registration touch the override surface.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All code | ✓ | per pyproject.toml | — |
| PyYAML | parsing profile.yaml at preflight entry | optional dep, already declared | — | preflight emits actionable error if missing (profile.py:1487-1494); validators receive already-parsed dicts |
| pytest | tests | ✓ | per dev deps | — |
| networkx | graph fixtures in render tests | ✓ | required | — |

No new external dependencies. No filesystem dependencies beyond `tmp_path` for tests. No services, no databases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (per pyproject.toml; CI on Python 3.10 and 3.12) |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_profile.py tests/test_profile_composition.py tests/test_mapping.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMPL-03 §1 | Reject unknown ${var} in dataview_queries | unit | `pytest tests/test_profile.py -k "dataview_queries_unknown_var" -q` | ❌ Wave 0 |
| TMPL-03 §2 | Reject dataview_queries.<note_type> with no possible mapped nodes | unit | `pytest tests/test_profile.py -k "dataview_queries_unreachable_note_type" -q` | ❌ Wave 0 |
| TMPL-03 §3 | Reject whitespace-only / empty-after-substitution queries | unit | `pytest tests/test_profile.py -k "dataview_queries_empty_after_substitution" -q` | ❌ Wave 0 |
| TMPL-03 §4 | Reject duplicate dataview_queries.<note_type> across extends/includes | unit | `pytest tests/test_profile.py -k "dataview_queries_collision_across_chain" -q` | ❌ Wave 0 |
| CFG-01a | mapping_rule_templates: schema validates | unit | `pytest tests/test_profile.py -k "mapping_rule_templates_validates" -q` | ❌ Wave 0 |
| CFG-01b | note_type_templates: schema validates | unit | `pytest tests/test_profile.py -k "note_type_templates_validates" -q` | ❌ Wave 0 |
| CFG-01c | mapping_rules.id: optional slug validates + uniqueness | unit | `pytest tests/test_mapping.py -k "validate_rules_id_field" -q` | ❌ Wave 0 |
| CFG-01d | Render-time precedence ladder selects correct override | integration | `pytest tests/test_profile_composition.py -k "override_precedence_ladder" -q` | ❌ Wave 0 |
| CFG-01e | Warn + fall back on missing override file (both new lists) | unit (capsys) | `pytest tests/test_profile_composition.py -k "override_warn_fallback" -q` | ❌ Wave 0 |
| CFG-02 §1 | Duplicate id in mapping_rule_templates | unit | `pytest tests/test_profile.py -k "collision_duplicate_rule_id" -q` | ❌ Wave 0 |
| CFG-02 §2 | Duplicate exact pattern within same list | unit | `pytest tests/test_profile.py -k "collision_duplicate_pattern" -q` | ❌ Wave 0 |
| CFG-02 §3 | Duplicate note_type in note_type_templates | unit | `pytest tests/test_profile.py -k "collision_duplicate_note_type" -q` | ❌ Wave 0 |
| CFG-02 §4 | Duplicate dataview_queries.<note_type> across chain | unit | `pytest tests/test_profile.py -k "collision_duplicate_dv_across_chain" -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_profile.py tests/test_mapping.py tests/test_profile_composition.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** `pytest tests/ -q` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] No new test files mandated; all gaps are test functions added to existing files (`tests/test_profile.py`, `tests/test_profile_composition.py`, `tests/test_mapping.py`).
- [ ] Optional new file `tests/test_template_overrides.py` per D-56.07 — planner discretion.
- Framework install: none needed; pytest already in dev deps.

## Security Domain

`security_enforcement` not explicitly disabled in `.planning/config.json` — treat as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth surface) |
| V3 Session Management | no | — (no sessions) |
| V4 Access Control | no | — (no multi-user model) |
| V5 Input Validation | yes | Schema validation in `validate_profile_preflight`; path-confinement (`..`, absolute, `~`) on every override `template:` field; slug regex on `mapping_rules.id:`; allowlist (`_KNOWN_NOTE_TYPES`) on `note_type_templates.pattern` and `dataview_queries:` keys; cap on `mapping_rules.id:` length (80) |
| V6 Cryptography | no | — |
| V12 File and Resources | yes | Path-confinement at validate-time (preflight rejects `..`, absolute, `~`); `validate_vault_path` at render-time confines override file resolution to `<vault_dir>/.graphify/` (templates.py:1535) |

### Known Threat Patterns for Profile Schema Surface

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `template:` field (`../../../etc/passwd`) | Information Disclosure | Preflight `..` substring check (profile.py:721) + render-time `validate_vault_path` (templates.py:1535) — defense in depth, both ports verbatim to new lists |
| Absolute path injection (`/etc/passwd`) | Information Disclosure | Preflight `Path(template).is_absolute()` rejection (profile.py:723) — port verbatim |
| Home-relative path (`~/secret.md`) | Information Disclosure | Preflight `template.startswith("~")` rejection (profile.py:725) — port verbatim |
| Dataview fence breakout via `${community_tag}` containing backticks/newlines | Tampering | Existing sanitization at templates.py:1287-1288 (`replace("`", "")`, `replace("\n", "")`) — Phase 56 does NOT touch this; relies on Phase 31 defense |
| Malicious `${var}` in user-authored DV query template (e.g., `${../../escape}`) | Tampering | New D-56.02 §1 dead-rule: unknown ${var} rejected; allowlist is `{community_tag, folder}` only |
| Slug-injection via `mapping_rules.id:` (e.g., `../foo`, `\x00abc`) | Tampering | New D-56.04 slug regex `^[a-z][a-z0-9_-]*$` rejects everything outside the safe charset |
| Resource exhaustion via huge `mapping_rules.id:` | DoS | New D-56.04 length cap (suggested 80) |
| ReDoS via user pattern | DoS | Phase 56 patterns are exact strings (no regex from user); no ReDoS surface introduced. Existing `mapping_rules.when.regex` ReDoS mitigation (mapping.py:_MAX_PATTERN_LEN = 512, line 26) unaffected |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| (none) | All factual claims in this research are verified against the cited file:line in graphify source. | — | — |

All claims VERIFIED against codebase. No assumptions requiring user confirmation.

## Open Questions

1. **Should `_RULE_ID_MAX_LEN` be 80 (mirror `_REPO_IDENTITY_MAX_LEN`) or smaller?**
   - What we know: 80 is the established cap for slug-like fields in this codebase.
   - What's unclear: Whether `mapping_rules.id:` warrants a tighter cap given it'll appear in error messages and override-pattern strings.
   - Recommendation: Use 80 for consistency. Authors with shorter ids self-limit naturally.

2. **Should validate_profile signal collision *errors* or *warnings*?**
   - What we know: D-56.06 says "deterministic errors." Existing dead-rule detection in `validate_rules` (mapping.py:923) is documented as "warnings" but added to the same `errors` list — there is one channel. preflight (profile.py:1426) keeps `errors` and `warnings` distinct.
   - What's unclear: D-56.06 §4 collision flows through `validate_profile` (which only has `errors`). Suggest: emit as errors per D-56.06 wording. Planner confirms.

3. **`ClassificationContext` field for `rule_id` — extend dataclass or thread via dict?**
   - What we know: `ClassificationContext` is a frozen dataclass at mapping.py:57. `render_note` accepts `classification_context: ClassificationContext | dict`.
   - What's unclear: Cleanest extension path. Recommend (a) add optional `rule_id: str | None = None` to the dataclass, (b) populate in `classify` (mapping.py:296) when matched rule has `id`. Planner discretion.

## Sources

### Primary (HIGH confidence — codebase grep + line read)
- `graphify/profile.py` — `_DEFAULT_PROFILE` (90-167), `_VALID_TOP_LEVEL_KEYS` (172-179), `_KNOWN_NOTE_TYPES` (181-184), `_deep_merge_with_provenance` (245-274), `_resolve_profile_chain` (350-510), `community_templates:` validator (682-735), `dataview_queries:` validator (737-763), `mapping_rules` entry point (1041-1051), `validate_profile` (651), `validate_profile_preflight` (1426-1490)
- `graphify/mapping.py` — `_NOTE_TYPES` import (16), `_VALID_TOPOLOGY_KINDS` (28-34), `_NOTE_TYPES` allowlist usage (384, 925), `validate_rules` (841-925), built-in note_type fallback (397-406), `_resolve_folder` (248-256), `_effective_folder_mapping` (269-288)
- `graphify/templates.py` — `_NOTE_TYPES` (50-52), `_KNOWN_NOTE_TYPES` (201), `_build_dataview_block` (1240-1308), substitution call (1290-1293), `render_note` callsite (1439-1444), `_render_moc_like` callsite (1707-1710), `_load_override_template` (1521-1568), `_pick_community_template` (1572-1610)
- `graphify/naming.py` — slug pattern reference (53-64), `_REPO_IDENTITY_MAX_LEN = 80` (34)
- `tests/test_profile_composition.py` — community_templates: test patterns (385-590)
- `tests/test_profile.py` — dataview_queries: test patterns (1612-1740)

### Secondary
- `.planning/phases/56-dataview-templates-profile-overrides/56-CONTEXT.md` — locked decisions (D-56.01..D-56.13)
- `.planning/REQUIREMENTS.md` — TMPL-03, CFG-01, CFG-02 wording
- `.planning/ROADMAP.md` §"Phase 56" (lines 597-611) — success criteria

### Tertiary
- (none — no web searches performed; pure codebase research)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library is already in repo and verified by file:line
- Architecture (validators + resolver wiring): HIGH — every extension point grep-confirmed
- Pitfalls: HIGH — derived from reading actual code paths, not speculation
- Provenance shape extension: HIGH — current shape is `dict[str, Path]` confirmed at profile.py:35, 56, 274; required shape `dict[str, list[Path]]` is mechanically derivable
- Allowlist enumeration: HIGH — exhaustive grep of `_build_dataview_block` callsites + the substitution call inside it
- D-56.02 §2 algorithm: HIGH — built-in topology fallback paths verified at mapping.py:397-406

**Research date:** 2026-05-02
**Valid until:** ~2026-06-01 (30 days; profile.py and templates.py are stable Phase 30/31/55 deliverables)
