# Phase 19: Vault Promotion Script (Layer B) - Research

**Researched:** 2026-04-22
**Domain:** Python file I/O, NetworkX graph traversal, Obsidian note generation, profile-layer merging
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 19 ships VAULT-01..07 (7 REQ-IDs). VAULT-06 and VAULT-07 rows must be added to REQUIREMENTS.md during planning.
- **D-02:** Tag taxonomy ships 4 namespaces: `garden/*`, `source/*`, `graph/*`, `tech/*`. All are required.
- **D-03:** Layer 3 auto-detected tags apply to the run's notes AND write back to `.graphify/profile.yaml` via union-merge (VAULT-06). Write-back is atomic; union-only; gated by `profile_sync.auto_update` (default true).
- **D-04:** `vault_promote.py` is standalone — does NOT import `graphify.export.to_obsidian` or `graphify.merge.compute_merge_plan`.
- **D-05:** CLI subcommand `graphify vault-promote --vault PATH --threshold N`.
- **D-06:** Reuses `profile.py` (`load_profile`, `validate_profile`), `security.py` guards, `builtin_templates/` (+ new `question.md`, `quote.md`), `analyze.py` (`god_nodes`, `knowledge_gaps`).
- **D-07:** `vault-promote` and `graphify approve` coexist independently.
- **D-08:** `--threshold N` gates on node degree only. `graphifyScore` = degree value.
- **D-09:** Questions folder populated from `analyze.py::knowledge_gaps()` — always promoted regardless of threshold.
- **D-10:** Things folder = `god_nodes()` filtered to `file_type != "code"`.
- **D-11:** All 7 folders with heuristic dispatch: Things, Questions, Maps, Sources, People (regex), Quotes (doc+quote-marks), Statements (relation='defines').
- **D-12:** Map MOC frontmatter: `stateMaps: 🟥`, `collections:` union of members, `up: [[Atlas]]`. No `related:`.
- **D-13:** Re-run via sidecar `graphify-out/vault-manifest.json`. Path→hash decision table: match=overwrite, mismatch or absent=skip+log, absent+no file=write.
- **D-14:** Collision: skip + log in import-log.md `## Skipped` section. No stderr warning.
- **D-15:** `import-log.md`: append, latest-first, prepend `## Run YYYY-MM-DDTHH:MM` block.
- **D-16:** All file writes atomic: tempfile + `os.replace`.
- **D-17:** `_DEFAULT_PROFILE` tag_taxonomy baseline verbatim from design note: garden/graph/source/tech namespaces.
- **D-18:** `_VALID_TOP_LEVEL_KEYS` gains `tag_taxonomy` and `profile_sync`.
- **D-19:** Layer 1=`_DEFAULT_PROFILE`, Layer 2=user profile.yaml (deep-merged), Layer 3=auto-detected (applied in-memory + written back via VAULT-06).
- **D-20:** Every promoted note carries full Ideaverse frontmatter including all VAULT-02 required fields.
- **D-21:** `related:` populated from EXTRACTED-confidence edges only. INFERRED/AMBIGUOUS edges omitted from wikilinks.

### Claude's Discretion

- Exact regex/predicate tuning for People/Quotes/Statements heuristics (locale/Unicode handling).
- Internal JSON shape of `graphify-out/vault-manifest.json` (versioning, timestamp fields).
- Whether `question.md` and `quote.md` templates are separate files or inlined strings (lean toward separate files per convention).
- Test file organization: new `tests/test_vault_promote.py` (per CLAUDE.md one-file-per-module rule).

### Deferred Ideas (OUT OF SCOPE)

- Sentinel-block preservation (`GRAPHIFY_USER_START/END`) inside promoted notes.
- ACE-Aligned Vocabulary candidate phase (ROADMAP.md §146).
- Extended Map frontmatter (`mapRank`, `mapConfidence`, `stateReviewed`).
- More precise detectors for People/Quotes/Statements.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VAULT-01 | `graphify vault-promote --vault PATH --threshold N` CLI reads graph.json + GRAPH_REPORT.md, writes promoted notes without touching foreign files | D-05 subcommand pattern verified in `__main__.py`; graph.json load pattern from `--obsidian` handler confirmed |
| VAULT-02 | Every promoted note has valid Ideaverse frontmatter: up, related, created, collections, graphifyProject, graphifyRun, graphifyScore, graphifyThreshold, min one tag from garden/*, source/*, graph/* | `_dump_frontmatter` in profile.py is the serializer; `safe_frontmatter_value` handles quoting |
| VAULT-03 | Node-type → folder dispatch correct: god-node domain concepts → Things/, knowledge gaps → Questions/, clusters → Maps/ with stateMaps: 🟥 | `god_nodes()` confirmed in analyze.py; gap logic identified as NEEDING NEW `knowledge_gaps()` function |
| VAULT-04 | `related:` wikilinks from EXTRACTED-confidence edges only | Edge confidence field confirmed in graph.json schema; filter is a simple `data.get("confidence") == "EXTRACTED"` check |
| VAULT-05 | `graphify-out/import-log.md` written after each run with vault path, timestamp, promoted-count by type, threshold, skipped-count | Pattern mirrors existing sidecar writing in `serve.py`/`enrich.py` |
| VAULT-06 | Profile write-back: union-merge detected tags into `.graphify/profile.yaml`, gated by `profile_sync.auto_update` (default true) | `_VALID_TOP_LEVEL_KEYS` must gain `tag_taxonomy` and `profile_sync`; validated YAML write pattern in enrich.py |
| VAULT-07 | Hybrid 3-layer tag taxonomy: Layer 1 `_DEFAULT_PROFILE`, Layer 2 user profile.yaml, Layer 3 auto-detected (persists via VAULT-06) | `_deep_merge` in profile.py handles Layers 1+2; Layer 3 union-merge is additive only |
</phase_requirements>

---

## Summary

Phase 19 adds `graphify/vault_promote.py` and the `vault-promote` CLI subcommand. The module reads `graphify-out/graph.json` from disk (using the NetworkX `json_graph.node_link_graph` round-trip pattern already in `__main__.py`), classifies nodes into 7 Obsidian destination folders via heuristic dispatch, renders notes using the existing `string.Template`-based template system, and writes atomically. It is entirely standalone — no imports of `to_obsidian` or `compute_merge_plan`.

The critical discovery this research uncovered is that **`analyze.py::knowledge_gaps()` does not exist** as a named function. Gap detection logic lives inline inside `report.py::generate()` (lines 194–217). Phase 19 must either (a) extract that inline logic into a new `knowledge_gaps()` function in `analyze.py`, or (b) re-implement equivalent detection inline in `vault_promote.py`. Option (a) is preferred because the CONTEXT.md locks `knowledge_gaps()` as the API and makes it reusable for future phases. The planner must include a Wave 0 task to create `analyze.py::knowledge_gaps()`.

A second important finding: `_VALID_TOP_LEVEL_KEYS` and `_DEFAULT_PROFILE` in `profile.py` currently contain 7 keys each (`folder_mapping`, `naming`, `merge`, `mapping_rules`, `obsidian`, `topology`, `mapping`). Neither `tag_taxonomy` nor `profile_sync` are present yet. The planner must include tasks to add both keys to the profile module, with validation logic mirroring the existing `topology` section pattern.

**Primary recommendation:** Plan as three logical waves — Wave 0 (infrastructure: extract `knowledge_gaps()`, add profile keys, create two new templates), Wave 1 (classifier + writer core: the `vault_promote.py` module), Wave 2 (CLI plumbing and profile write-back).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Graph loading from disk | CLI / `__main__.py` entrypoint | `vault_promote.py` | Follows existing `--obsidian`/`approve` pattern: __main__ validates path, passes G + communities to library function |
| Node classification (7-folder dispatch) | `vault_promote.py` | `analyze.py` (god_nodes) | Classification is business logic specific to vault-promote; analyze.py provides raw metrics |
| Frontmatter rendering | `vault_promote.py` using `profile.py::_dump_frontmatter` | `templates.py::render_note` (not called — see below) | vault_promote builds its own frontmatter dict and calls `_dump_frontmatter` directly; does NOT call `render_note` (that function is tied to the merge-engine context) |
| Template substitution | `graphify/builtin_templates/*.md` + `string.Template.safe_substitute` | `templates.py::_load_builtin_template` | vault_promote re-uses the template files and the `importlib.resources` loader; does not call `render_note` |
| Path safety | `security.py::validate_vault_path`, `safe_filename`, `safe_tag` | `profile.py::validate_vault_path` | All external vault paths routed through security guards before any write |
| Atomic file write | `vault_promote.py` using `os.replace` | Idiom from `merge.py`, `enrich.py`, `cache.py` | Same idiom used project-wide; vault_promote implements its own thin helper |
| Sidecar manifest | `vault_promote.py` writes `graphify-out/vault-manifest.json` | `security.py::validate_graph_path` (base confinement) | Manifest lives in graphify-out/ (the writable output dir), not in the vault |
| Profile write-back (VAULT-06) | `vault_promote.py` | `profile.py::_deep_merge` | Union-merge detected tags into user profile.yaml; uses profile.py's merge primitive |
| Tag taxonomy (VAULT-07) | `profile.py::_DEFAULT_PROFILE` (Layer 1) + `load_profile` (Layers 1+2) | `vault_promote.py` (Layer 3 detection) | Same 3-layer merge as folder_mapping; vault_promote adds Layer 3 at runtime |
| Knowledge gap detection | New `analyze.py::knowledge_gaps()` (to be created in Wave 0) | Inline logic migrated from `report.py::generate()` lines 194–217 | Currently no standalone function exists; extraction is a Wave 0 prerequisite |
| Import log | `vault_promote.py` writes `graphify-out/import-log.md` | — | Append-only sidecar in graphify-out/, prepend latest run |

---

## Standard Stack

### Core (all already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `networkx` | ≥3.x (no pin) | Graph loading via `json_graph.node_link_graph` | Already core dependency |
| `string` (stdlib) | stdlib | Template substitution via `string.Template.safe_substitute` | Already used in `templates.py` |
| `hashlib` (stdlib) | stdlib | SHA-256 content hashing for vault-manifest.json | Already used in `merge.py._content_hash` |
| `importlib.resources` (stdlib) | stdlib | Loading builtin templates | Already used in `templates.py::_load_builtin_template` |
| `tempfile` (stdlib) | stdlib | Not actually used — project uses `.with_suffix(".tmp")` + `os.replace` | See atomic write pattern below |
| `os` (stdlib) | stdlib | `os.replace` for atomic writes | Already used project-wide |
| `re` (stdlib) | stdlib | People regex `^[A-Z][a-z]+ [A-Z][a-z]+$`, quote-mark detection | Already used in `profile.py` |
| `yaml` (PyYAML) | optional dep | Reading/writing profile.yaml for VAULT-06 | Already optional dep; same guard pattern as `load_profile` |
| `unicodedata` (stdlib) | stdlib | NFC normalization in `safe_filename` (already handles Unicode) | Used in `profile.py::safe_filename` |

### No New Dependencies

Phase 19 introduces zero new required dependencies. All needed functionality is available via stdlib or existing optional deps (PyYAML). [VERIFIED: CLAUDE.md constraint "No new required dependencies"]

---

## Architecture Patterns

### System Architecture Diagram

```
[graph.json + GRAPH_REPORT.md]  [.graphify/profile.yaml]
         |                                |
         v                               v
   __main__.py                    load_profile()        [vault-manifest.json]
   vault-promote CMD               (3-layer merge)            |
         |                               |                    |
         v                               v                    v
   json_graph.node_link_graph()   merged_profile         _load_manifest()
         |                               |                    |
         v                               |                    |
   G (nx.Graph)                          |                    |
   communities dict                      |                    |
         |                               |                    |
         v                               v                    v
   ┌─────────────────────────────────────────────────────────────────┐
   │                    vault_promote.py                             │
   │                                                                 │
   │  classify_nodes(G, communities, merged_profile, threshold)      │
   │     ├─ god_nodes() → Things (file_type != code)                │
   │     ├─ knowledge_gaps() → Questions (always promoted)           │
   │     ├─ community iter → Maps (MOC per cluster)                  │
   │     ├─ unique source_files → Sources                            │
   │     ├─ People regex → People                                    │
   │     ├─ doc+quote-marks → Quotes                                 │
   │     └─ relation='defines' → Statements                          │
   │                                                                 │
   │  render_note(node, folder_type, G, profile)                     │
   │     ├─ _build_frontmatter_fields()                              │
   │     ├─ _dump_frontmatter() [from profile.py]                    │
   │     ├─ _load_builtin_template(type) [from templates.py]         │
   │     └─ template.safe_substitute(ctx)                            │
   │                                                                 │
   │  write_note(path, content, manifest) → atomic via os.replace    │
   │     ├─ manifest[path] matches disk hash? → overwrite            │
   │     ├─ manifest[path] mismatch? → skip + log                    │
   │     ├─ not in manifest + file exists? → skip + log (foreign)    │
   │     └─ not in manifest + file absent? → write                   │
   │                                                                 │
   │  _detect_tech_tags(G) → auto Layer 3 tags                       │
   │  _writeback_profile(vault, detected_tags) [if auto_update]      │
   │                                                                 │
   │  write_import_log(graphify-out/, run_summary)                   │
   │  write_manifest(graphify-out/vault-manifest.json, manifest)     │
   └─────────────────────────────────────────────────────────────────┘
         |                                       |
         v                                       v
   [Atlas/Dots/Things/*.md]           [graphify-out/import-log.md]
   [Atlas/Dots/Questions/*.md]        [graphify-out/vault-manifest.json]
   [Atlas/Dots/Statements/*.md]       [.graphify/profile.yaml] (write-back)
   [Atlas/Dots/Quotes/*.md]
   [Atlas/Dots/People/*.md]
   [Atlas/Maps/*.md]
   [Atlas/Sources/Clippings/*.md]
```

### Recommended Project Structure

```
graphify/
├── vault_promote.py             # new — standalone promotion engine
├── builtin_templates/
│   ├── thing.md                 # existing
│   ├── moc.md                   # existing
│   ├── statement.md             # existing
│   ├── person.md                # existing
│   ├── source.md                # existing
│   ├── community.md             # existing
│   ├── question.md              # NEW — Wave 0
│   └── quote.md                 # NEW — Wave 0
├── analyze.py                   # add knowledge_gaps() — Wave 0
├── profile.py                   # add tag_taxonomy + profile_sync keys — Wave 0
└── __main__.py                  # add vault-promote subcommand — Wave 2

tests/
└── test_vault_promote.py        # NEW — all tests for vault_promote.py
```

### Pattern 1: Graph Loading from Disk (verified in `__main__.py` lines 1303–1335)

```python
# Source: graphify/__main__.py::_load_graph_from_disk (--obsidian handler pattern)
import json
from networkx.readwrite import json_graph

gp = Path(graph_path).resolve()
_raw = json.loads(gp.read_text(encoding="utf-8"))
try:
    G = json_graph.node_link_graph(_raw, edges="links")
except TypeError:
    G = json_graph.node_link_graph(_raw)

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
```

### Pattern 2: Atomic Write (verified in `merge.py::_write_atomic` lines 1153–1165)

```python
# Source: graphify/merge.py::_write_atomic
def _write_atomic(target: Path, content: str) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

Note: `merge.py` uses `fsync` before `os.replace`; `enrich.py` uses a simpler `tmp.write_text() + os.replace` without `fsync`. For vault notes (not critical data), the simpler form is acceptable and matches project convention in most modules. The planner should pick the simpler pattern for notes and the `fsync` pattern for the manifest.

### Pattern 3: Content Hashing for vault-manifest.json (verified in `merge.py` lines 1056–1063)

```python
# Source: graphify/merge.py::_content_hash
import hashlib
def _content_hash(path: Path) -> str:
    """SHA-256 of raw file bytes only — no path mixed in."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
```

The manifest entry shape used by `merge.py` (the reference implementation):
```json
{
  "Atlas/Dots/Things/Transformer.md": {
    "content_hash": "<sha256-hex>",
    "last_merged": "2026-04-22T14:28:00+00:00",
    "target_path": "Atlas/Dots/Things/Transformer.md",
    "node_id": "transformer",
    "note_type": "thing",
    "community_id": 0
  }
}
```

Phase 19's manifest uses `path → sha256_hex_of_raw_bytes`. The algorithm is SHA-256 raw bytes (not content-normalized). This matches `merge.py._content_hash` exactly, ensuring future interop if the two manifests are ever merged.

### Pattern 4: Template Substitution (verified in `templates.py` lines 194–203, 697–699)

```python
# Source: graphify/templates.py::_load_builtin_template + render usage
import importlib.resources as ilr
import string

_BUILTIN_TEMPLATES_ROOT = ilr.files("graphify").joinpath("builtin_templates")

def _load_builtin_template(note_type: str) -> string.Template:
    ref = _BUILTIN_TEMPLATES_ROOT.joinpath(f"{note_type}.md")
    text = ref.read_text(encoding="utf-8")
    return string.Template(text)

# Render:
template = _load_builtin_template("thing")
text = template.safe_substitute({
    "frontmatter": "---\nup:\n  ...\n---",
    "label": "Transformer",
    "wayfinder_callout": "",
    "body": "",
    "connections_callout": "",
    "metadata_callout": "",
    # MOC-only vars must be passed as "" for safe_substitute idempotence
    "members_section": "",
    "sub_communities_callout": "",
    "dataview_block": "",
})
```

`safe_substitute` (not `substitute`) is used so missing keys produce the literal `${key}` rather than raising `KeyError`. All MOC-only vars must be passed as `""` even in non-MOC templates to prevent leftover `${...}` tokens.

### Pattern 5: Template File Layout (existing templates show the exact placeholders)

```
thing.md:   ${frontmatter}, ${label}, ${wayfinder_callout}, ${body}, ${connections_callout}, ${metadata_callout}
moc.md:     ${frontmatter}, ${label}, ${wayfinder_callout}, ${members_section}, ${sub_communities_callout}, ${dataview_block}, ${metadata_callout}
source.md:  same as thing.md
```

New `question.md` and `quote.md` should follow the `thing.md` structure (same required placeholders): `${frontmatter}`, `${label}`, `${wayfinder_callout}`, `${body}`, `${connections_callout}`, `${metadata_callout}`.

### Pattern 6: CLI Subcommand Registration (verified in `__main__.py` dispatch chain)

```python
# Source: graphify/__main__.py — approve/harness dispatch pattern
# Add BEFORE the final `else: print("error: unknown command")` block

elif cmd == "vault-promote":
    import argparse as _ap
    parser = _ap.ArgumentParser(prog="graphify vault-promote")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    parser.add_argument("--threshold", type=int, default=3,
                        help="Minimum node degree for promotion (default: 3)")
    parser.add_argument(
        "--graph", default="graphify-out/graph.json",
        help="Path to graph.json (default graphify-out/graph.json)"
    )
    opts = parser.parse_args(sys.argv[2:])
    from graphify.vault_promote import promote
    promote(
        graph_path=Path(opts.graph),
        vault_path=Path(opts.vault),
        threshold=opts.threshold,
    )
```

### Pattern 7: Profile Validation Extension (for `tag_taxonomy` + `profile_sync`)

The existing validation pattern in `validate_profile()` for `topology` (lines ~290–310) is the direct model:

```python
# Add to validate_profile() in profile.py following topology/mapping pattern:
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

profile_sync = profile.get("profile_sync")
if profile_sync is not None:
    if not isinstance(profile_sync, dict):
        errors.append("'profile_sync' must be a mapping (dict)")
    else:
        auto_update = profile_sync.get("auto_update")
        if auto_update is not None and not isinstance(auto_update, bool):
            errors.append("'profile_sync.auto_update' must be a boolean")
```

### Anti-Patterns to Avoid

- **Calling `render_note` from `templates.py`:** `render_note()` requires a `ClassificationContext` and is tightly coupled to the merge-engine's note-type vocabulary (`thing`/`statement`/`person`/`source`). `vault_promote.py` builds frontmatter dict directly and calls `_dump_frontmatter` + `safe_substitute` instead. [VERIFIED: render_note's `_KNOWN_NOTE_TYPES` is locked to 4 types, not the 7 vault-promote needs]
- **Using `_NOTE_TYPES` from templates.py:** This frozenset only has 6 types (moc/community/thing/statement/person/source). It does not include `question` or `quote`. vault_promote must manage its own type registry.
- **Calling `validate_vault_path` from `security.py`:** There are TWO functions with this name — one in `security.py` (does NOT exist; the grep found none) and one in `profile.py` (lines ~350–370). The correct reuse target is `profile.py::validate_vault_path`. [VERIFIED: grepped security.py — no `validate_vault_path` there; function is in profile.py]
- **Importing `FileType` enum from `detect.py`:** Use the string values directly (`"code"`, `"document"`, `"paper"`, `"image"`) as they appear in graph.json nodes. The enum is only for detect-phase classification; graph.json stores the `.value` string.
- **Reading file_type from extraction fixture:** The fixture uses only `code` and `document`. Production graphs can have `paper`, `image`, `rationale` types too — the classifier must handle all five.

---

## Critical Discovery: `knowledge_gaps()` Does Not Exist

**This is the most important finding for planning.**

[VERIFIED: grepped entire codebase]

`analyze.py::knowledge_gaps()` referenced in CONTEXT.md D-06/D-09 and in REQUIREMENTS.md descriptions **does not exist as a Python function**. The gap detection logic lives **inline** inside `report.py::generate()` at lines 194–217:

```python
# Source: graphify/report.py::generate() lines 194-217 (the inline gap logic)
from .analyze import _is_file_node, _is_concept_node

isolated = [
    n for n in G.nodes()
    if G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n)
]
thin_communities = {
    cid: nodes for cid, nodes in communities.items() if len(nodes) < 3
}
# High-ambiguity check:
ambiguous = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("confidence") == "AMBIGUOUS"]
amb_pct = round(len(ambiguous) / G.number_of_edges() * 100) if G.number_of_edges() else 0
```

**Wave 0 must create `analyze.py::knowledge_gaps(G, communities)` by extracting this logic.** The return shape should be a list of node IDs (or dicts with `id`, `label`, `reason` fields) suitable for promotion to the Questions folder.

Suggested signature:
```python
def knowledge_gaps(
    G: nx.Graph,
    communities: dict[int, list[str]],
    ambiguity_threshold: float = 0.20,
) -> list[dict]:
    """Return nodes representing knowledge gaps: isolated, thin-community, or high-ambiguity context.
    
    Returns list of dicts with keys: id, label, reason (one of: isolated, thin_community, high_ambiguity_context)
    These are always promoted to Questions/ regardless of threshold.
    """
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHA-256 content hash | Custom hasher | `hashlib.sha256(path.read_bytes()).hexdigest()` | Already used in `merge.py::_content_hash` — identical algorithm guarantees future interop |
| YAML frontmatter emission | Custom YAML serializer | `profile.py::_dump_frontmatter(fields_dict)` | Handles quoting of reserved words, booleans, lists, dates, control chars — many edge cases |
| Filename/slug generation | Custom slugifier | `profile.py::safe_filename(label)` | NFC normalization + OS-illegal char stripping + hash suffix for collisions |
| Tag slugification | Custom | `profile.py::safe_tag(name)` | Lowercase, hyphen-separated, leading-digit guard |
| Path confinement check | `str.startswith` | `profile.py::validate_vault_path(candidate, vault_dir)` | Handles symlinks via `.resolve()` — naive startswith fails on symlinked paths |
| Profile deep merge | Custom recursive merge | `profile.py::_deep_merge(base, override)` | Already tested, handles nested dicts correctly |
| Template loading | `open()` direct | `templates.py::_load_builtin_template(note_type)` | Uses `importlib.resources` — works under editable install, wheel, and zip-archive |
| Atomic file write | `f.write()` direct | `target.with_suffix(".tmp")` + `os.replace()` idiom | Thread-safe, crash-safe — any write failure leaves original intact |

---

## graph.json Schema (Verified)

[VERIFIED: extracted from `to_json()` in export.py + fixture inspection + `node_link_graph` round-trip]

**Node fields** (as loaded into `G.nodes[node_id]`):

| Field | Type | Notes |
|-------|------|-------|
| `id` | str | Stable slug (lowercase alphanumeric + underscores) |
| `label` | str | Human-readable display name — verbatim as extracted, may contain spaces/caps/Unicode |
| `file_type` | str | One of: `"code"`, `"document"`, `"paper"`, `"image"`, `"rationale"` |
| `source_file` | `str \| list[str]` | Phase 10 D-12: may be a list when node was merged from multiple files |
| `source_location` | str | e.g., `"L42"` or `"§3.1"` (optional) |
| `community` | int or None | Written by `to_json()` from the community partition |
| `merged_from` | list[str] or absent | Phase 10 dedup: list of eliminated node IDs |

**Edge fields** (as loaded into `G.edges[u, v]`):

| Field | Type | Notes |
|-------|------|-------|
| `source` | str | Source node ID |
| `target` | str | Target node ID |
| `relation` | str | e.g., `"defines"`, `"calls"`, `"imports"`, `"references"`, `"implements"`, `"semantically_similar_to"` |
| `confidence` | str | One of: `"EXTRACTED"`, `"INFERRED"`, `"AMBIGUOUS"` |
| `source_file` | str | Where the edge was detected |
| `weight` | float | Usually 1.0 |
| `confidence_score` | float | Only on INFERRED edges (0.0–1.0) |

**Key insight for heuristic dispatch:**
- `label` is preserved verbatim in graph.json — People regex `^[A-Z][a-z]+ [A-Z][a-z]+$` can be applied directly. Unicode accented names (e.g., `"José García"`) will NOT match ASCII `[a-z]` — this is a known limitation (see Deferred).
- `file_type="document"` is confirmed as a valid enum value in `detect.py::FileType.DOCUMENT`. Document nodes in the test fixture have labels like `"attention mechanism"` (lowercase concept labels from LLM extraction).
- `relation="defines"` IS emitted by extractors: confirmed in `extract.py` (Go/Rust/Julia/Kotlin/C/C++/Java extractors all call `add_edge(scope, target, "defines", line)`). Also appears in the Julia test cache fixture.

---

## Heuristic Dispatch: Feasibility Analysis

[VERIFIED: by code inspection of extract.py, detect.py, and graph.json fixture]

### People: `^[A-Z][a-z]+ [A-Z][a-z]+$`

- **Feasible** for ASCII names in source code.
- **Limitation:** Does NOT match accented names (`José`, `García`). This is acceptable per the Deferred clause — the heuristic is intentionally simple.
- `label` is verbatim in graph.json — regex can be applied directly.
- **Unicode-safe approach (Claude's Discretion):** Use `unicodedata.normalize("NFC", label)` before regex. Consider `re.match(r"^\p{Lu}\p{Ll}+ \p{Lu}\p{Ll}+$", label)` via the `regex` package (not installed) — or stick with ASCII `[A-Z][a-z]` for simplicity. Recommend ASCII regex for Phase 19 (simple, consistent with Deferred clause).

### Quotes: `file_type="document"` AND label containing `"`, `"`, `"`, `«`, `»`

- **Feasible.** `file_type="document"` is confirmed valid.
- LLM-extracted document nodes typically have concept-phrase labels (`"attention mechanism"`), not verbatim quotes. Quote-mark detection will match rarely unless the corpus includes explicitly labeled quote nodes.
- Quote marks to detect: `'"'` (U+0022), `'“'` (U+201C `"`), `'”'` (U+201D `"`), `'«'` (U+00AB `«`), `'»'` (U+00BB `»`).
- Implementation: `any(c in label for c in ('"', '“', '”', '«', '»'))`.

### Statements: At least one outgoing edge where `relation='defines'`

- **Feasible.** `relation="defines"` IS emitted by Go, Rust, Julia, Kotlin, C, C++, Java extractors.
- **Important constraint:** The CONTEXT.md says "nodes with at least one outgoing edge where `relation='defines'`". In an undirected NetworkX graph (`nx.Graph`, which is what graphify uses), `G.edges(node_id)` returns all edges regardless of direction. The planner must decide whether "outgoing" means checking `data.get("_src", u) == node_id` or simply "any adjacent edge with relation='defines'". Recommend "any adjacent" for simplicity (undirected graph semantics).
- `relation="defines"` is commonly on code-type nodes (module→class/function). The Statements classifier will predominantly fire on code entities. Combined with the Things classifier which excludes `file_type="code"`, Statements may end up being code-heavy — this is expected behavior, not a bug.

---

## Common Pitfalls

### Pitfall 1: `safe_filename` Truncates Long Labels

**What goes wrong:** A node label like "A Very Long Community Name That Exceeds 200 Characters..." gets truncated with a hash suffix. If the wikilink `[[label]]` uses the original label but the file is written as `Label_Long_With_Hash.md`, wikilink resolution breaks in Obsidian.

**Why it happens:** `safe_filename(label, max_len=200)` appends `_<8hex>.md` when `len(name) > 200`. The wikilink target and the filename must match.

**How to avoid:** Always generate the filename stem via `safe_filename(label)` FIRST, then use that stem as both the filesystem path AND the wikilink target: `[[{stem}|{label}]]`. This is the pattern used in `templates.py::resolve_filename`.

### Pitfall 2: Manifest Keyed by Relative vs. Absolute Path

**What goes wrong:** Manifest is built with absolute paths during run A, but relative paths during run B (or vice versa). Hash lookups miss, treating all prior notes as foreign.

**Why it happens:** `Path` comparison is sensitive to whether paths are relative to vault or absolute.

**How to avoid:** Always store manifest keys as relative paths from `vault_dir`. When loading a note to compute its disk hash, resolve to absolute: `(vault_dir / rel_key).read_bytes()`. Use `str(path.relative_to(vault_dir))` as the manifest key — matches `merge.py`'s existing convention.

### Pitfall 3: Two `validate_vault_path` Functions

**What goes wrong:** Implementer imports `validate_vault_path` from `security.py` — but it doesn't exist there. The function is in `profile.py`.

**Why it happens:** `security.py` has `validate_graph_path` (confines to graphify-out/) while `profile.py` has `validate_vault_path` (confines to vault dir). Names are similar.

**How to avoid:** Import explicitly: `from graphify.profile import validate_vault_path`. Never import from `security.py` for vault path validation.

### Pitfall 4: `_dump_frontmatter` Skips None Values

**What goes wrong:** A frontmatter field like `community_id: None` is silently omitted from the output. If the caller expects the key to be present for downstream parsing, the note is malformed.

**Why it happens:** `_dump_frontmatter` explicitly `continue`s when `value is None`.

**How to avoid:** Pass `""` (empty string) or `[]` (empty list) instead of `None` for fields that must always be present.

### Pitfall 5: source_file May Be a List

**What goes wrong:** `node.get("source_file")` returns `["src/auth.py", "lib/auth.py"]` (list) rather than a string. Code using `source_file.split("/")` raises `AttributeError`.

**Why it happens:** Phase 10 D-12 allows deduped nodes to have `source_file: list[str]`.

**How to avoid:** Use `analyze.py::_iter_sources(source_file)` helper: returns a flat list of strings in all cases. Import: `from graphify.analyze import _iter_sources`.

### Pitfall 6: `knowledge_gaps()` Does Not Exist Yet

**What goes wrong:** `vault_promote.py` calls `from graphify.analyze import knowledge_gaps` at import time — raises `ImportError` until Wave 0 creates it.

**Why it happens:** The function name was used in CONTEXT.md as aspirational API — the underlying logic exists in `report.py` but has not been extracted.

**How to avoid:** Wave 0 task creates `analyze.py::knowledge_gaps()` BEFORE any vault_promote.py code is written.

### Pitfall 7: PyYAML Optional Guard for Profile Write-Back

**What goes wrong:** Profile write-back (VAULT-06) calls `yaml.dump(...)` without guarding for PyYAML not being installed. Crashes on minimal installs.

**Why it happens:** PyYAML is optional (`pip install graphifyy[obsidian]`).

**How to avoid:** Follow the guard pattern in `load_profile()`:
```python
try:
    import yaml
except ImportError:
    print("[graphify] PyYAML not installed — profile write-back skipped. "
          "Install with: pip install graphifyy[obsidian]", file=sys.stderr)
    return
```

### Pitfall 8: Template Substitution Leaves Literal `${...}` Tokens

**What goes wrong:** A template has `${wayfinder_callout}` but the substitution dict omits that key. With `safe_substitute`, the literal string `${wayfinder_callout}` appears in the output note.

**Why it happens:** `string.Template.safe_substitute` does not raise on missing keys — it silently leaves the placeholder.

**How to avoid:** Always pass ALL placeholder keys in the substitution dict, using `""` for any section that is intentionally empty. The existing `render_note()` in `templates.py` demonstrates this with `"members_section": ""` and `"body": ""`.

---

## Code Examples

### Reading graph.json and reconstructing communities

```python
# Source: graphify/__main__.py lines 1303-1335 (--obsidian handler)
from pathlib import Path
import json
from networkx.readwrite import json_graph

def _load_graph_and_communities(graph_path: Path):
    _raw = json.loads(graph_path.read_text(encoding="utf-8"))
    try:
        G = json_graph.node_link_graph(_raw, edges="links")
    except TypeError:
        G = json_graph.node_link_graph(_raw)
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
    return G, communities
```

### Manifest write-back (sha256 hash)

```python
# Source: merge.py::_content_hash + _save_manifest pattern
import hashlib, json, os

def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _write_manifest(manifest_path: Path, manifest: dict[str, str]) -> None:
    """manifest: {relative_path_str → sha256_hex}"""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, manifest_path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

### Inline gap detection (to be extracted to `analyze.py::knowledge_gaps`)

```python
# Source: graphify/report.py::generate() lines 194-217
# This logic must be extracted to analyze.py::knowledge_gaps() in Wave 0.
from graphify.analyze import _is_file_node, _is_concept_node

def knowledge_gaps(G, communities, ambiguity_threshold=0.20):
    results = []
    isolated = [
        n for n in G.nodes()
        if G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n)
    ]
    for n in isolated:
        results.append({"id": n, "label": G.nodes[n].get("label", n), "reason": "isolated"})
    thin = {cid: nodes for cid, nodes in communities.items() if len(nodes) < 3}
    for cid, nodes in thin.items():
        for n in nodes:
            if not _is_file_node(G, n) and not _is_concept_node(G, n):
                results.append({"id": n, "label": G.nodes[n].get("label", n), "reason": "thin_community"})
    ambiguous = [e for e in G.edges(data=True) if e[2].get("confidence") == "AMBIGUOUS"]
    total = G.number_of_edges()
    if total and len(ambiguous) / total >= ambiguity_threshold:
        # High ambiguity context — flag adjacent nodes as gaps
        for u, v, _ in ambiguous:
            for n in (u, v):
                if not _is_file_node(G, n) and not _is_concept_node(G, n):
                    results.append({"id": n, "label": G.nodes[n].get("label", n), "reason": "high_ambiguity_context"})
    # Deduplicate by node ID
    seen = set()
    deduped = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            deduped.append(r)
    return deduped
```

### Profile write-back union merge (VAULT-06)

```python
# Pattern: read → union-merge → write atomically
def _writeback_profile(vault_dir: Path, detected_tags: dict[str, list[str]]) -> None:
    try:
        import yaml
    except ImportError:
        print("[graphify] PyYAML not installed — profile write-back skipped.", file=sys.stderr)
        return

    profile_path = vault_dir / ".graphify" / "profile.yaml"
    existing: dict = {}
    if profile_path.exists():
        existing = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}

    taxonomy = existing.setdefault("tag_taxonomy", {})
    for ns, tags in detected_tags.items():
        current = taxonomy.get(ns, [])
        merged = sorted(set(current) | set(tags))
        taxonomy[ns] = merged

    existing["tag_taxonomy"] = taxonomy
    tmp = profile_path.with_suffix(".yaml.tmp")
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp.write_text(yaml.dump(existing, allow_unicode=True, sort_keys=True), encoding="utf-8")
        os.replace(tmp, profile_path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

---

## Runtime State Inventory

This is a greenfield module (new file, new subcommand). No rename/migration involved.

**Nothing found in any category** — Phase 19 adds new files; it does not rename existing ones.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Core requirement | ✓ | 3.x (CI tests 3.10+3.12) | None needed |
| networkx | Graph loading | ✓ | no pin | None needed |
| PyYAML | Profile read/write-back | Optional dep | already in `[obsidian]` extra | Skip write-back with stderr warning |
| pytest | Test execution | ✓ | installed | None needed |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** PyYAML absence → write-back gracefully skipped (existing pattern).

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | None detected — uses `pyproject.toml` [tool.pytest.ini_options] if present |
| Quick run command | `pytest tests/test_vault_promote.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAULT-01 | CLI reads graph.json, writes notes without overwriting foreign files | integration | `pytest tests/test_vault_promote.py::test_cli_does_not_overwrite_foreign -x` | ❌ Wave 0 |
| VAULT-01 | Write-only: file absent → write; foreign present → skip | unit | `pytest tests/test_vault_promote.py::test_write_decision_table -x` | ❌ Wave 0 |
| VAULT-02 | Every promoted note has required frontmatter fields | unit | `pytest tests/test_vault_promote.py::test_frontmatter_has_required_fields -x` | ❌ Wave 0 |
| VAULT-02 | Tags include min one from garden/*, source/*, graph/* | unit | `pytest tests/test_vault_promote.py::test_frontmatter_tags_namespaces -x` | ❌ Wave 0 |
| VAULT-03 | god_nodes non-code → Things folder | unit | `pytest tests/test_vault_promote.py::test_things_dispatch -x` | ❌ Wave 0 |
| VAULT-03 | knowledge_gaps → Questions folder always promoted | unit | `pytest tests/test_vault_promote.py::test_questions_always_promoted -x` | ❌ Wave 0 |
| VAULT-03 | Communities → Maps with stateMaps: 🟥 | unit | `pytest tests/test_vault_promote.py::test_maps_moc_frontmatter -x` | ❌ Wave 0 |
| VAULT-04 | related: only from EXTRACTED edges | unit | `pytest tests/test_vault_promote.py::test_related_extracted_only -x` | ❌ Wave 0 |
| VAULT-05 | import-log.md written and contains required fields | unit | `pytest tests/test_vault_promote.py::test_import_log_written -x` | ❌ Wave 0 |
| VAULT-05 | import-log.md is append, latest-first across runs | unit | `pytest tests/test_vault_promote.py::test_import_log_append_latest_first -x` | ❌ Wave 0 |
| VAULT-06 | Profile write-back union-merges detected tags | unit | `pytest tests/test_vault_promote.py::test_profile_writeback_union_merge -x` | ❌ Wave 0 |
| VAULT-06 | Write-back skipped when profile_sync.auto_update=false | unit | `pytest tests/test_vault_promote.py::test_profile_writeback_opt_out -x` | ❌ Wave 0 |
| VAULT-07 | Tag taxonomy 3-layer merge: default < user < auto-detected | unit | `pytest tests/test_vault_promote.py::test_tag_taxonomy_layer_merge -x` | ❌ Wave 0 |
| n/a | knowledge_gaps() extracted to analyze.py returns correct shape | unit | `pytest tests/test_analyze.py::test_knowledge_gaps_returns_list -x` | ❌ Wave 0 |
| n/a | profile.py validate_profile accepts tag_taxonomy section | unit | `pytest tests/test_profile.py::test_validate_profile_tag_taxonomy -x` | ❌ Wave 0 |
| n/a | profile.py validate_profile accepts profile_sync section | unit | `pytest tests/test_profile.py::test_validate_profile_profile_sync -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_vault_promote.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_vault_promote.py` — new file covering all VAULT-01..07 behaviors
- [ ] `graphify/analyze.py` — add `knowledge_gaps()` function (extracted from report.py)
- [ ] `graphify/profile.py` — add `tag_taxonomy` and `profile_sync` to `_VALID_TOP_LEVEL_KEYS` and `_DEFAULT_PROFILE`; add validation in `validate_profile()`
- [ ] `graphify/builtin_templates/question.md` — new template file
- [ ] `graphify/builtin_templates/quote.md` — new template file
- [ ] Tests for new `knowledge_gaps()`: add cases to `tests/test_analyze.py`
- [ ] Tests for new profile keys: add cases to `tests/test_profile.py`

---

## Security Domain

`security_enforcement` not explicitly set in config.json — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not applicable (local CLI tool) |
| V3 Session Management | No | Not applicable |
| V4 Access Control | Yes | Path confinement via `profile.py::validate_vault_path` |
| V5 Input Validation | Yes | `safe_filename`, `safe_tag`, `safe_frontmatter_value` from profile.py |
| V6 Cryptography | No | SHA-256 for content hashing only (not security crypto) |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `--vault PATH` | Tampering | `profile.py::validate_vault_path(candidate, vault_dir)` — resolves + checks `relative_to` |
| Path traversal via node labels used in filenames | Tampering | `profile.py::safe_filename(label)` — strips `../`, OS-illegal chars |
| Tag injection via node labels (e.g., `tag: injected\n`) | Tampering | `profile.py::safe_tag(name)` — allows only `[a-z0-9-]` |
| YAML injection in profile write-back via node label as tag value | Tampering | Use `yaml.dump()` (never string concat); pass tag values through `safe_tag` before writing |
| Writing outside vault (foreign file overwrite) | Tampering | vault-manifest.json skip-foreign decision table; `validate_vault_path` on every write path |
| Infinite loop from circular graph | Denial of Service | Use `G.nodes()` iteration (not recursive traversal) — NetworkX graph is finite |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `question.md` and `quote.md` templates should follow `thing.md` structure (same required placeholders) | Architecture Patterns §5 | If different placeholders are needed, template validation in `validate_template()` would fail — minor; easily fixed |
| A2 | `vault-promote` subcommand should be added before the final `else: unknown command` block in `main()` | Architecture Patterns §6 | Incorrect — no functional impact as long as it's inside `main()` before the else |
| A3 | The manifest JSON shape for Phase 19 should be `{path_str: {content_hash: ..., ...}}` (dict of dicts) rather than simple `{path_str: hash_str}` | Code Examples §manifest | Using dict-of-dicts matches merge.py for future interop; flat dict would also work for Phase 19's use case |
| A4 | Statements heuristic fires on "any adjacent edge where relation='defines'" (undirected graph semantics) rather than strictly outgoing | Heuristic Dispatch §Statements | Directional semantics would require checking `_src` field — more complex; undirected is conservative |

**Only 4 assumed claims total — all low-risk and easily resolved during implementation.**

---

## Open Questions

1. **`knowledge_gaps()` return shape for Questions notes**
   - What we know: Report.py identifies 3 gap types: isolated nodes, thin-community nodes, high-ambiguity-context nodes.
   - What's unclear: Should high-ambiguity-context nodes promote as individual notes (one per node adjacent to ambiguous edges) or as a single summary note?
   - Recommendation: One note per unique gap node ID. Dedup by node_id prevents duplicates when a node is both isolated AND adjacent to an ambiguous edge.

2. **`import-log.md` skipped-count format**
   - What we know: D-14 says "skip + record in import-log.md under `## Skipped` with path and reason".
   - What's unclear: The exact format of the per-run block is not fully specified in CONTEXT.md D-15 beyond "promoted-count by type, skipped-count by reason, and per-skipped-path breakdown".
   - Recommendation: The planner should define the exact log format as a code example in PLAN.md and have the implementer match it. Suggested:
     ```
     ## Run 2026-04-22T14:28
     - vault: /Users/.../vault
     - threshold: 5
     - promoted: things=3, questions=2, maps=1, sources=5, people=0, quotes=0, statements=1
     - skipped: user_modified=1, foreign=2
     ## Skipped
     - Atlas/Dots/Things/Transformer.md — user_modified (hash mismatch)
     - Atlas/Docs/Some_Note.md — foreign (not in manifest)
     ```

3. **Tech tag detection: which extensions map to which tech tags**
   - What we know: `source_file` extensions can be extracted from graph.json nodes. `detect.py::CODE_EXTENSIONS` is the authoritative list.
   - What's unclear: The exact extension→tag mapping is not specified in CONTEXT.md (e.g., does `.ts` → `tech/typescript` or `tech/javascript`?).
   - Recommendation: Planner should define a mapping table in PLAN.md. Suggested: `.py`→`python`, `.ts`/`.tsx`→`typescript`, `.js`/`.jsx`→`javascript`, `.go`→`go`, `.rs`→`rust`, `.java`→`java`, `.sql`→`sql`, `.graphql`→`graphql`, `.kt`/`.kts`→`typescript` (or a new `kotlin` tag).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `graphify --obsidian` flag (merge-with-review) | `graphify vault-promote` subcommand (write-only) | Phase 19 | New independent path; old path unchanged |
| Gap detection inline in report.py | `analyze.py::knowledge_gaps()` (to be extracted) | Phase 19 Wave 0 | Makes gap data available to non-report consumers |
| profile.py has 7 top-level keys | profile.py gains `tag_taxonomy` and `profile_sync` | Phase 19 Wave 0 | Additive; existing validation unaffected |

**Deprecated/outdated:**
- Nothing deprecated in Phase 19. All additions are additive.

---

## Sources

### Primary (HIGH confidence)
- `graphify/analyze.py` — god_nodes() signature and return shape [VERIFIED: grepped + executed]
- `graphify/profile.py` — _DEFAULT_PROFILE, _VALID_TOP_LEVEL_KEYS, validate_profile pattern, _dump_frontmatter, safe_filename, safe_tag, safe_frontmatter_value, validate_vault_path [VERIFIED: full file read]
- `graphify/security.py` — confirmed validate_vault_path is NOT in security.py; validate_graph_path IS [VERIFIED: grepped]
- `graphify/templates.py` — _NOTE_TYPES, _REQUIRED_PER_TYPE, _load_builtin_template, render_note, safe_substitute pattern [VERIFIED: read lines 48–260, 566–710]
- `graphify/__main__.py` — graph.json loading pattern, subcommand dispatch structure, approve/harness patterns [VERIFIED: read lines 1245–1345, 1623–1730, 1930–1965]
- `graphify/merge.py` — _content_hash (SHA-256 raw bytes), _write_atomic, _save_manifest, manifest schema [VERIFIED: read lines 1045–1170]
- `graphify/enrich.py` — atomic write idiom [VERIFIED: read lines 380–460]
- `graphify/report.py` — inline knowledge_gaps logic (lines 194–217) [VERIFIED: read]
- `graphify/extract.py` — relation='defines' emitted by Go/Rust/Julia/C/C++/Java/Kotlin extractors [VERIFIED: grepped lines 1340–1411]
- `graphify/detect.py` — FileType enum, DOC/CODE/PAPER/IMAGE extensions [VERIFIED: read lines 11–105]
- `tests/fixtures/extraction.json` — confirmed file_type values ('code','document'), edge confidence values, node/edge key schemas [VERIFIED: executed python3 inspection]
- `.planning/phases/19-vault-promotion-script-layer-b/19-CONTEXT.md` — all locked decisions [VERIFIED: full read]
- `.planning/notes/layer-b-vault-promotion-design.md` — tag taxonomy verbatim values, frontmatter schema [VERIFIED: full read]
- `.planning/config.json` — nyquist_validation: true [VERIFIED: read]

### Secondary (MEDIUM confidence)
- `.planning/milestones/v1.2-phases/09-multi-perspective-analysis-autoreason-tournament/09-PATTERNS.md` — confirms knowledge_gaps() does not exist in analyze.py [CITED: phase 9 PATTERNS.md line 457]

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; no new deps
- Architecture: HIGH — patterns verified by direct code inspection of all referenced modules
- Critical finding (knowledge_gaps missing): HIGH — verified by exhaustive grep across entire codebase
- Pitfalls: HIGH — all verified against actual code
- Heuristic feasibility: MEDIUM — feasibility confirmed; exact behavior under edge cases (accented names, quote-less document nodes) is LOW

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (stable codebase; no fast-moving external deps)
