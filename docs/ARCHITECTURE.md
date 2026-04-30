# Architecture

graphify is a Claude Code skill backed by a Python library. The skill orchestrates the library; the library can be used standalone.

## Pipeline

```
detect()  →  extract()  →  build_graph()  →  cluster()  →  analyze()  →  report()  →  export()
```

Each stage is a single function in its own module. They communicate through plain Python dicts and NetworkX graphs - no shared state, no side effects outside `graphify-out/`.

## Module responsibilities

| Module | Function | Input → Output |
|--------|----------|----------------|
| `detect.py` | `collect_files(root)` | directory → `[Path]` filtered list |
| `extract.py` | `extract(path)` | file path → `{nodes, edges}` dict |
| `build.py` | `build_graph(extractions)` | list of extraction dicts → `nx.Graph` |
| `cluster.py` | `cluster(G)` | graph → graph with `community` attr on each node |
| `analyze.py` | `analyze(G)` | graph → analysis dict (god nodes, surprises, questions) |
| `report.py` | `render_report(G, analysis)` | graph + analysis → GRAPH_REPORT.md string |
| `export.py` | `export(G, out_dir, ...)` | graph → Obsidian vault, graph.json, graph.html, graph.svg |
| `profile.py` | `load_profile(vault_dir)` | vault path → merged profile dict (`.graphify/profile.yaml` + defaults) |
| `templates.py` | `render_note(node_id, G, ...)` | node + profile → rendered markdown with frontmatter and wikilinks |
| `mapping.py` | `classify(G, communities, profile)` | graph + profile → `MappingResult` (note type, folder, context per node) |
| `merge.py` | `compute_merge_plan(vault_dir, notes, profile)` | rendered notes + existing vault → `MergePlan` (CREATE/UPDATE/SKIP actions) |
| `ingest.py` | `ingest(url, ...)` | URL → file saved to corpus dir |
| `cache.py` | `check_semantic_cache / save_semantic_cache` | files → (cached, uncached) split |
| `security.py` | validation helpers | URL / path / label → validated or raises |
| `validate.py` | `validate_extraction(data)` | extraction dict → raises on schema errors |
| `serve.py` | `serve()` / stdio server | graph file path → MCP stdio server (tool schemas co-owned with `mcp_tool_registry.py`) |
| `watch.py` | `watch(root, flag_path)` | directory → writes flag file on change |
| `benchmark.py` | `run_benchmark(graph_path)` | graph file → corpus vs subgraph token comparison |

## Extraction output schema

Every extractor returns:

```json
{
  "nodes": [
    {"id": "unique_string", "label": "human name", "source_file": "path", "source_location": "L42"}
  ],
  "edges": [
    {"source": "id_a", "target": "id_b", "relation": "calls|imports|uses|...", "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"}
  ]
}
```

`validate.py` enforces this schema before `build_graph()` consumes it.

## Confidence labels

| Label | Meaning |
|-------|---------|
| `EXTRACTED` | Relationship is explicitly stated in the source (e.g., an import statement, a direct call) |
| `INFERRED` | Relationship is a reasonable deduction (e.g., call-graph second pass, co-occurrence in context) |
| `AMBIGUOUS` | Relationship is uncertain; flagged for human review in GRAPH_REPORT.md |

## Adding a new language extractor

1. Add a `extract_<lang>(path: Path) -> dict` function in `extract.py` following the existing pattern (tree-sitter parse → walk nodes → collect `nodes` and `edges` → call-graph second pass for INFERRED `calls` edges).
2. Register the file suffix in `extract()` dispatch and `collect_files()`.
3. Add the suffix to `CODE_EXTENSIONS` in `detect.py` and `_WATCHED_EXTENSIONS` in `watch.py`.
4. Add the tree-sitter package to `pyproject.toml` dependencies.
5. Add a fixture file to `tests/fixtures/` and tests to `tests/test_languages.py`.

## Security

All external input passes through `graphify/security.py` before use:

- URLs → `validate_url()` (http/https only) + `_NoFileRedirectHandler` (blocks file:// redirects)
- Fetched content → `safe_fetch()` / `safe_fetch_text()` (size cap, timeout)
- Graph file paths → `validate_graph_path()` (must resolve inside `graphify-out/`)
- Node labels → `sanitize_label()` (strips control chars, caps 256 chars, HTML-escapes)

See [`SECURITY.md`](../SECURITY.md) for the full threat model.

## Obsidian vault adapter (Ideaverse integration)

The `--obsidian` export is profile-driven. Four new modules form a pipeline within the export stage:

```
load_profile() → classify() → render_note()/render_moc() → compute_merge_plan() → apply_merge_plan()
```

| Module | Role |
|--------|------|
| `profile.py` | Discovers `.graphify/profile.yaml` in vault, deep-merges over built-in defaults (Ideaverse ACE structure). Validates schema, provides safety helpers (`safe_filename`, `safe_frontmatter_value`, `safe_tag`, `validate_vault_path`). |
| `templates.py` | 6 built-in note templates (moc, thing, statement, person, source, community) using `${placeholder}` syntax. User overrides via `.graphify/templates/<type>.md`. Renders frontmatter, wikilinks, Dataview queries, navigation callouts. |
| `mapping.py` | Routes nodes to note types via attribute rules (`file_type: person`) and topology rules (god nodes → things, communities → MOCs). Returns `MappingResult` with per-node and per-community classification contexts. |
| `merge.py` | Plans and executes vault writes. Compares rendered notes against existing vault files. Preserves user-edited fields, handles orphans (never auto-deletes), supports three strategies: `update`, `skip`, `replace`. `--dry-run` returns the plan without writing. |

The `to_obsidian()` function in `export.py` orchestrates these four modules. When no profile exists, the built-in default produces Ideaverse-compatible output (`Atlas/Maps/`, `Atlas/Dots/Things/`, etc.).

## Testing

One test file per module under `tests/`. Run with:

```bash
pytest tests/ -q
```

All tests are pure unit tests - no network calls, no file system side effects outside `tmp_path`.
