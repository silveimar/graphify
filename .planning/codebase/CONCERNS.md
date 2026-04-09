# Codebase Concerns

**Analysis Date:** 2025-02-09

## Tech Debt

**Dual extraction complexity in extract.py:**
- Issue: `extract.py` is 2,719 lines with highly repetitive language-specific configuration blocks. Each language requires boilerplate: LanguageConfig dataclass, call edge extraction, import handling, and custom walk functions.
- Files: `graphify/extract.py` (lines 1-100, 620-700, 900-970)
- Impact: Hard to add new languages. Risk of inconsistent behavior across languages. Heavy maintenance burden when updating call edge detection or import extraction.
- Fix approach: Extract common patterns into a tree-sitter visitor framework. Unify call edge extraction (currently language-specific at lines 880-946). Create a composable import handler registry instead of language-specific if/elif chains.

**Silent exception handling in extractors:**
- Issue: Multiple extractors wrap tree-sitter parsing in bare `except Exception` blocks (lines 623-636, 991-1000, 1158-1171), returning `{"nodes": [], "edges": [], "error": str(e)}`. Errors are silently swallowed unless caller checks for "error" key.
- Files: `graphify/extract.py` (lines 623-644, 991-1000, 1158-1171, 1370-1380)
- Impact: Extraction failures go unnoticed if the "error" key is not explicitly checked. The build pipeline doesn't validate extraction errors before merging (see `graphify/build.py` line 31-34 which only warns). Missing languages or corrupted tree-sitter bins can fail silently.
- Fix approach: Raise exceptions instead of returning error dicts. Wrap with context at the CLI level. Add validation in `build_from_json()` to reject extractions with error keys.

**Node deduplication across semantic + AST extraction:**
- Issue: Comments in `graphify/build.py` (lines 10-16) document three layers of deduplication, but the skill is responsible for the third layer (merging cached semantic with new semantic results). The build module doesn't enforce this - it relies on external coordination.
- Files: `graphify/build.py`, implicit dependency on skill merge logic
- Impact: If semantic results aren't deduplicated before calling `build()`, nodes with identical IDs will silently overwrite with the last extraction's attributes. This can lose rich semantic labels if AST results come last, or lose precise source_location if semantic results come last.
- Fix approach: Add explicit `seen_ids` deduplication inside `build()` function with a configurable priority policy (e.g., "semantic wins" or "AST wins"). Document the order assumption prominently.

**Rationale extraction tied to Python-only:**
- Issue: `_extract_python_rationale()` (lines 987-1085) extracts docstrings and `# RATIONALE:` / `# TODO:` / `# FIXME:` comments as `rationale_for` edges. This feature only exists for Python.
- Files: `graphify/extract.py` (lines 984-1095)
- Impact: Users of other languages lose design rationale extraction. Asymmetric feature coverage.
- Fix approach: Generalize to a language-agnostic post-pass that scans source comments for common prefixes (`# NOTE:`, `// WHY:`, `/* RATIONALE */`) and creates rationale nodes. Add to each language extractor.

## Known Bugs

**Cache collision risk with identical file content across paths:**
- Symptoms: Two files with identical content but different paths may share a cache entry.
- Files: `graphify/cache.py` (lines 10-17)
- Trigger: Place two .py files with identical source code in different directories. Re-run graphify twice - the second file will use the first file's cached extraction.
- Workaround: Call `clear_cache()` before re-running on modified corpora.
- Details: `file_hash()` includes the resolved path in the hash computation (line 16), which should prevent collisions. However, the cache key itself is just `{hash}.json`, so two different hashes that collide (extremely unlikely but cryptographically possible) would cause issues. More realistically, this is **not a bug** but the concern is the hash inclusion may be insufficient if hard links or symlinks are used.

**Windows PowerShell ANSI escape sequence corruption (historical, addressed in v0.3.10+):**
- Symptoms: Vertical scrolling breaks in PowerShell terminal after running graphify.
- Files: `graphify/cluster.py` (lines 33-40, context manager suppresses graspologic output)
- Trigger: Run graphify on Windows with PowerShell 5.1 and graspologic installed.
- Workaround: Upgrade graphify to v0.3.10+ which redirects graspologic stderr to suppress ANSI codes.
- Details: Fixed via `_suppress_output()` context manager. This is historical but may recur with new dependencies.

**Broken cross-community edge assumption in analyze.py:**
- Symptoms: `surprising_connections()` may return false positives in single-file codebases if it fails to detect file boundaries.
- Files: `graphify/analyze.py` (lines 75-90, strategy comment references multi-file vs single-file logic)
- Trigger: Extract a single .py file with multiple unrelated classes. Surprising connections may incorrectly report internal couplings as "cross-community" if community detection fails.
- Workaround: Manually review surprising connections in GRAPH_REPORT.md.
- Details: The function identifies unique source files via `source_files = {n.get("source_file") for n in G.nodes() if n.get("source_file")}` but doesn't handle None or empty string values well. If all nodes have empty source_file, `len(source_files)` is 1, triggering the "single-file corpus" logic incorrectly.

## Security Considerations

**URL validation validates but doesn't block all SSRF vectors:**
- Risk: The `validate_url()` function (lines 26-64) blocks private IP ranges and cloud metadata endpoints, but relies on DNS resolution. If DNS is compromised or returns a private IP after resolution, the check passes.
- Files: `graphify/security.py` (lines 26-64)
- Current mitigation: Blocks known metadata endpoints (`_BLOCKED_HOSTS`), uses socket.getaddrinfo() to resolve and check each returned address.
- Recommendations: Add an additional check: if hostname resolves to *any* private IP, fail. Currently handles this (line 56: `if ip.is_private`), so this is **mitigated**. Consider adding a DNS rebinding defense (check multiple times at fetch time).

**Label sanitization cap at 256 chars may truncate important context:**
- Risk: Node labels truncated to 256 chars (line 185). In exports, HTML entities are escaped via `html.escape()` only in a few places, not all label references.
- Files: `graphify/security.py` (line 185), `graphify/export.py` (lines 90-92 do escape, but not all label renders do)
- Current mitigation: `sanitize_label()` removes control characters and caps length. Escape happens in HTML generation.
- Recommendations: Audit all label renders in export.py to ensure HTML escaping. Make escaping mandatory before any label insertion into markup.

**File path validation uses try/except for path.relative_to():**
- Risk: `validate_graph_path()` (lines 165-170) tries `resolved.relative_to(base)` and catches ValueError to detect path traversal. This is correct but could be clearer.
- Files: `graphify/security.py` (lines 144-177)
- Current mitigation: Check is correct. Path must be inside base directory.
- Recommendations: Add a comment explaining that ValueError means path escapes base. Consider using `str.startswith()` for clarity, though relative_to() is more robust.

**External URL fetch has configurable but hardcoded max sizes:**
- Risk: `_MAX_FETCH_BYTES` (50 MB) and `_MAX_TEXT_BYTES` (10 MB) are module-level constants. Users cannot adjust for their environment.
- Files: `graphify/security.py` (lines 15-16), `graphify/ingest.py` (lines 47-48)
- Current mitigation: Constants are reasonable defaults (50 MB for binary, 10 MB for text).
- Recommendations: Make size limits configurable via environment variables or CLI args.

## Performance Bottlenecks

**extract() dispatches per-language via direct function calls without caching language parsers:**
- Problem: Every file in a corpus causes a language-specific tree-sitter Parser to be instantiated (lines 622-643). Parsers are not cached.
- Files: `graphify/extract.py` (lines 620-643)
- Cause: `Language(tspython.language())` and `Parser(language)` are created inside the extract function, which is called per-file by `extract()` at line 610. This is inefficient for large corpora.
- Improvement path: Cache parsers at module level using a dict keyed by language module name. Reuse across files. Benchmark impact on large codebases (100+ Python files).

**N^2 edge validation in build_from_json():**
- Problem: The function creates `node_set = set(G.nodes())` (line 38) then checks every edge against it (line 41-42). For graphs with 10,000+ nodes and 50,000+ edges, this is O(N) per edge check.
- Files: `graphify/build.py` (lines 29-52)
- Cause: No index structure; just repeated set membership tests.
- Improvement path: Keep node_set in memory (already done). The O(N) per edge is actually fine (set lookup is O(1)). **This is not a real bottleneck**. The real cost is graph construction in NetworkX.

**Leiden community detection without optimization for sparse graphs:**
- Problem: `_partition()` (lines 21-52) uses graspologic if available, falls back to networkx.louvain. Neither is tuned for sparse or very large graphs.
- Files: `graphify/cluster.py` (lines 21-52)
- Cause: Leiden is exact and slow on graphs with 50,000+ nodes. Louvain is approximate but better for scale.
- Improvement path: Add `seed` parameter (already done line 48). Consider adding min_edges threshold: if graph is sparse (average degree < 3), use a faster approximation (label propagation). Test on 10,000+ node graphs.

**to_json() in export.py rebuilds the entire graph as dict multiple times:**
- Problem: `to_json()` calls `json_graph.node_link_graph()` to serialize. For large graphs, this is expensive.
- Files: `graphify/export.py` (lines 760-780, implicit NetworkX overhead)
- Cause: No streaming or incremental export. Full graph must be held in memory and serialized at once.
- Improvement path: For graphs > 5,000 nodes, consider generating JSON incrementally or in chunks. Benchmark current performance on graphify repo itself.

**Wiki generation iterates neighbors multiple times per node:**
- Problem: `_community_article()` (lines 25-89) iterates `G.neighbors()` multiple times: once for cross-community links (line 17), once for edge confidence counts (line 37), once for sources (line 44).
- Files: `graphify/wiki.py` (lines 13-89)
- Cause: No caching of neighbor iteration results.
- Improvement path: Pre-compute neighbor maps once per community during `to_wiki()` and pass them to helper functions. Benchmark on large communities (1,000+ nodes).

## Fragile Areas

**Language configuration matrix is error-prone:**
- Files: `graphify/extract.py` (LanguageConfig at lines 23-60)
- Why fragile: Each language has a LanguageConfig with ~12 configurable fields. A small typo (wrong field name, wrong type) breaks extraction silently. Python and JavaScript work because they're heavily tested; new languages are risky.
- Safe modification: Add type hints to LanguageConfig fields. Test each new language config with `pytest tests/test_languages.py` before merging. Add a validator function that checks all required fields are set.
- Test coverage: `tests/test_languages.py` has tests for Python, JavaScript, TypeScript, Go, Rust, Java, C++, Ruby, Swift, Kotlin, Scala, PHP, Lua, Zig, PowerShell, Elixir, Objective-C, Julia. New languages need both positive (extracts correct nodes) and negative (no false nodes) test cases.

**Call edge inference heavily depends on label-to-nid mapping:**
- Files: `graphify/extract.py` (lines 880-970, especially line 949)
- Why fragile: `label_to_nid = {n['label'].lower(): n['id'] for n in nodes}` assumes unique lowercase labels. If two classes have the same name (e.g., `User` in two modules), one will be silently dropped from the mapping, and cross-module calls won't be detected.
- Safe modification: Add error checking: if len(label_to_nid) < len(set(n['label'].lower() for n in nodes)), emit a warning about duplicate labels.
- Test coverage: Add test case with two classes named `Builder` in different scopes; verify both appear in call edges.

**Extract.py's node ID generation via _make_id() is deterministic but fragile:**
- Files: `graphify/extract.py` (lines 14-18)
- Why fragile: `_make_id()` replaces all non-alphanumeric chars with underscores, then strips leading/trailing. For a class `__init__()`, it becomes `init` - no distinguishing prefix. Nested classes with the same local name will collide.
- Safe modification: Include parent scope in ID generation (already done in some places, e.g., line 1070). Ensure all extractors use hierarchical IDs like `module_class_method`.
- Test coverage: `tests/test_extract.py` has tests for ID generation (`test_make_id_*`). Add test for nested class collision.

**Cluster splitting threshold (_MAX_COMMUNITY_FRACTION = 0.25) may cause instability:**
- Files: `graphify/cluster.py` (lines 55-56, 89)
- Why fragile: Community size thresholds are hardcoded. For a graph with 1,000 nodes, communities > 250 nodes get split. This can create pathological behavior if the split produces very small sub-communities that fail to re-partition.
- Safe modification: Make thresholds configurable. Test on graphs of varying sizes (100, 1000, 10,000 nodes) to ensure stable community counts.
- Test coverage: `tests/test_cluster.py` tests clustering but doesn't test stability across different graph sizes.

**Ingest URL type detection via heuristics may fail on edge cases:**
- Files: `graphify/ingest.py` (lines 27-44)
- Why fragile: `_detect_url_type()` uses simple string matching. A GitHub URL might be classified as "github" but could also be a PDF (GitHub Release .pdf link). PDF detection happens last (line 40), so it wins, but the order is fragile.
- Safe modification: Fetch the Content-Type header before downloading to confirm file type. Add a --force-type flag to override detection.
- Test coverage: `tests/test_ingest.py` tests basic fetching but not edge cases like GitHub PDF links.

**Obsidian vault export assumes safe node filenames but doesn't validate all outputs:**
- Files: `graphify/export.py` (lines 689-679, `safe_name()` function)
- Why fragile: `safe_name()` removes special chars but a node label like `"../../../etc/passwd"` could theoretically escape the vault directory if escaping is incomplete.
- Safe modification: Use `pathlib.Path.resolve()` to canonicalize output paths. Reject labels containing path separators.
- Test coverage: No test for path traversal in node labels.

## Scaling Limits

**Tree-sitter parser memory for large files:**
- Current capacity: Successfully tested on individual files up to ~100KB (typical). No testing on files > 1MB.
- Limit: Tree-sitter may OOM or hang on files with deeply nested syntax (e.g., auto-generated code).
- Scaling path: Add a file size cap (e.g., skip files > 1MB). Implement timeout on parsing. Profile memory usage on graphify repo itself.

**Leiden/Louvain community detection limits on graphs > 50,000 nodes:**
- Current capacity: Community detection works on graphs up to ~10,000 nodes without visible slowdown. No benchmarking on 50,000+ node graphs.
- Limit: Leiden is O(N log N) but with high constants. For 50,000 nodes, may take > 10 seconds.
- Scaling path: For graphs > 50K nodes, use label propagation (faster, approximate). Add a --fast flag to skip community detection and use single-node communities. Benchmark on real large codebases.

**Export functions scale poorly to many small files:**
- Current capacity: 5,000 nodes exports to Obsidian in ~1 second. 50,000 nodes likely takes 10+ seconds (linear in nodes).
- Limit: `to_obsidian()` writes one file per node plus one per community (lines 544-545). Filesystem operations dominate.
- Scaling path: Batch writes. Use thread pool for I/O. For very large graphs (> 20K nodes), warn user and offer a sampling option (export every Nth node).

**HTML viz (vis.js) is disabled for graphs > 5,000 nodes:**
- Current capacity: `to_html()` successfully renders 5,000 nodes in the browser.
- Limit: vis.js rendering becomes sluggish > 5,000 nodes. Browser crashes > 10,000 nodes.
- Scaling path: Already documented (see `MAX_NODES_FOR_VIZ = 5_000` in export.py line 19). This is intentional. For larger graphs, users must use Obsidian vault or CLI query tools.

**Cache directory grows linearly with corpus size:**
- Current capacity: Each file generates one cache entry (~5-50 KB depending on extraction size). 1,000 files → ~50 MB cache.
- Limit: No cleanup mechanism. Cache grows forever unless manually cleared.
- Scaling path: Add automatic cache eviction: keep only the 1,000 most recent entries, or entries < 30 days old. Expose via `cache.py` module.

## Dependencies at Risk

**tree-sitter version pin >= 0.23.0:**
- Risk: Recent releases of tree-sitter introduced breaking changes to the Python API (e.g., language loading). The pin at 0.23.0+ ensures compatibility but limits how old the package can be.
- Files: `pyproject.toml` (line 15)
- Impact: Future tree-sitter 2.x may break the language config system entirely.
- Migration plan: Monitor tree-sitter releases. When 2.x arrives, benchmark compatibility and plan a major graphify version bump.

**graspologic (optional, for Leiden) is dormant:**
- Risk: graspologic hasn't had a release since 2021. It depends on deprecated scikit-learn APIs.
- Files: `graphify/cluster.py` (lines 30-41, import is optional)
- Impact: May break on future scikit-learn versions. Fallback to networkx Louvain is acceptable but lower quality.
- Migration plan: If graspologic stops working, keep the fallback. Investigate `igraph` or `cdlib` as alternatives.

**pypdf (optional, for PDF extraction):**
- Risk: Library has had security issues in the past. Currently maintained but extraction is best-effort.
- Files: `graphify/detect.py` (lines 101-113)
- Impact: Corrupt PDFs may cause crashes or hangs. Currently wrapped in `try/except`, so impact is limited.
- Migration plan: No action needed if PDF extraction is optional. Monitor security advisories.

**Six language-specific tree-sitter bindings (tree_sitter_*):**
- Risk: Each language binding is independently maintained. Several are stale (e.g., tree-sitter-julia, tree-sitter-lua).
- Files: `pyproject.toml` (lines 16-36)
- Impact: Language support may bitrot. Tree-sitter grammar updates may not be reflected in bindings.
- Migration plan: Consider consolidating to a single tree-sitter-all package if one exists, or switch to using tree-sitter's web assembly bindings (less mature but more unified).

## Missing Critical Features

**No incremental graph updates:**
- Problem: Every run re-extracts all files and rebuilds the entire graph. There's a cache mechanism but it's per-file, not graph-aware.
- Blocks: Large codebases (10,000+ files) cannot do quick incremental updates. Re-running graphify takes 5+ minutes instead of seconds.
- Implementation notes: Would require storing graph metadata (node/edge counts per file) and only re-extracting files with changed hashes. See `graphify/cache.py` for semantic cache structure.

**No graph diffing:**
- Problem: Users can't see what changed between graph runs.
- Blocks: Understanding the impact of code changes on architecture. Detecting unintended structural changes.
- Implementation notes: Would require storing previous graph snapshots and computing graph diffs (added/removed nodes, edge weight changes).

**No schema versioning for exports:**
- Problem: Old exports (Obsidian vaults, Neo4j dumps) don't have a version marker. If the schema changes, old exports become incompatible.
- Blocks: Long-lived knowledge graphs can't migrate to new schema versions.
- Implementation notes: Add a `schema_version` field to all exports. Write migration code for common schema changes.

**Limited query language for CLI/MCP:**
- Problem: `graphify query` supports BFS/DFS traversal but no way to filter by node properties or relationship types from the command line.
- Blocks: Advanced analysis (find all EXTRACTED edges, find nodes in Community 0 with degree > 5).
- Implementation notes: Would require a small query DSL or integration with an existing one (e.g., Cypher for Neo4j compatibility).

## Test Coverage Gaps

**No negative tests for language extractors:**
- What's not tested: Invalid syntax, syntax errors, edge cases (empty functions, unreachable code).
- Files: `tests/test_languages.py`, `tests/test_extract.py`
- Risk: Extractors may crash or produce incorrect output on malformed code. Currently only positive tests (valid Python, valid JavaScript) are run.
- Priority: **High** - Errors in extraction are silent and can corrupt the graph.

**No fuzz testing for input validation:**
- What's not tested: Security boundaries in security.py (sanitization, URL validation). No test for malformed JSON, huge labels, path traversal attempts.
- Files: `tests/test_security.py` (exists but limited)
- Risk: Security bugs in label handling, URL validation, path validation may only be caught in production.
- Priority: **High** - Security-critical code.

**No integration tests for multi-language extraction:**
- What's not tested: A codebase with Python + Go + Rust together. Extractors may have conflicts (e.g., identifier name collisions across languages).
- Files: `tests/test_multilang.py` (exists but minimal)
- Risk: Multi-language corpora (common in microservices) may produce incorrect graphs.
- Priority: **Medium** - Less common use case but important for accuracy.

**No benchmarks for performance regressions:**
- What's not tested: Extraction speed, clustering speed, export speed on known-size graphs.
- Files: `graphify/benchmark.py` (exists but not run in CI)
- Risk: A change that 10x slows down extraction goes unnoticed until user complains.
- Priority: **Medium** - Performance is not a hard requirement but UX matters.

**No end-to-end tests for exported artifacts:**
- What's not tested: Obsidian vaults actually open in Obsidian, HTML viz renders correctly, Neo4j Cypher queries work.
- Files: `tests/test_export.py` (tests file generation but not artifact validity)
- Risk: Export format changes silently break downstream tools.
- Priority: **Medium** - Would require running external tools in CI.

**No tests for cluster stability across runs:**
- What's not tested: Running cluster() twice on the same graph produces consistent community assignments.
- Files: `tests/test_cluster.py`
- Risk: Community IDs may shift between runs, breaking reproducibility.
- Priority: **Low** - Community detection is approximate by nature, but deterministic output (via seed=42) is expected.

---

*Concerns audit: 2025-02-09*
