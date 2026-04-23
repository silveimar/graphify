# Graph Report - /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify  (2026-04-14)

## Corpus Check
- Large corpus: 1168 files · ~2,340,082 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder, or use --no-semantic to run AST-only.

## Summary
- 2397 nodes · 3787 edges · 73 communities detected
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 582 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_test_templates.py|test_templates.py]]
- [[_COMMUNITY_MergePlan|MergePlan]]
- [[_COMMUNITY_Response|Response]]
- [[_COMMUNITY_test_profile.py|test_profile.py]]
- [[_COMMUNITY_test_languages.py|test_languages.py]]
- [[_COMMUNITY_extract.py|extract.py]]
- [[_COMMUNITY_test_mapping.py|test_mapping.py]]
- [[_COMMUNITY_RenderedNote|RenderedNote]]
- [[_COMMUNITY_test_detect.py|test_detect.py]]
- [[_COMMUNITY_merge.py|merge.py]]
- [[_COMMUNITY_test_serve.py|test_serve.py]]
- [[_COMMUNITY_test_install.py|test_install.py]]
- [[_COMMUNITY_Geometry|Geometry]]
- [[_COMMUNITY_serve.py|serve.py]]
- [[_COMMUNITY_test_delta.py|test_delta.py]]
- [[_COMMUNITY_templates.py|templates.py]]
- [[_COMMUNITY_analyze.py|analyze.py]]
- [[_COMMUNITY_test_snapshot.py|test_snapshot.py]]
- [[_COMMUNITY_DataProcessor|DataProcessor]]
- [[_COMMUNITY_test_extract.py|test_extract.py]]
- [[_COMMUNITY_test_cache.py|test_cache.py]]
- [[_COMMUNITY_ValidationError|ValidationError]]
- [[_COMMUNITY_test_analyze.py|test_analyze.py]]
- [[_COMMUNITY_test_claude_md.py|test_claude_md.py]]
- [[_COMMUNITY_test_multilang.py|test_multilang.py]]
- [[_COMMUNITY_test_security.py|test_security.py]]
- [[_COMMUNITY_test_transcribe.py|test_transcribe.py]]
- [[_COMMUNITY_ingest.py|ingest.py]]
- [[_COMMUNITY_test_wiki.py|test_wiki.py]]
- [[_COMMUNITY_cache.py|cache.py]]
- [[_COMMUNITY_cluster.py|cluster.py]]
- [[_COMMUNITY_test_confidence.py|test_confidence.py]]
- [[_COMMUNITY_test_hypergraph.py|test_hypergraph.py]]
- [[_COMMUNITY_storage.py|storage.py]]
- [[_COMMUNITY_test_semantic_similarity.py|test_semantic_similarity.py]]
- [[_COMMUNITY_test_main_cli.py|test_main_cli.py]]
- [[_COMMUNITY_TestPolicyDispatcher|TestPolicyDispatcher]]
- [[_COMMUNITY_test_hooks.py|test_hooks.py]]
- [[_COMMUNITY_test_benchmark.py|test_benchmark.py]]
- [[_COMMUNITY_security.py|security.py]]
- [[_COMMUNITY_make_graph()|make_graph()]]
- [[_COMMUNITY_test_pipeline.py|test_pipeline.py]]
- [[_COMMUNITY_transcribe.py|transcribe.py]]
- [[_COMMUNITY_processor.py|processor.py]]
- [[_COMMUNITY_parser.py|parser.py]]
- [[_COMMUNITY_test_cluster.py|test_cluster.py]]
- [[_COMMUNITY_hooks.py|hooks.py]]
- [[_COMMUNITY_test_validate.py|test_validate.py]]
- [[_COMMUNITY_snapshot.py|snapshot.py]]
- [[_COMMUNITY_test_integration.py|test_integration.py]]
- [[_COMMUNITY_build()|build()]]
- [[_COMMUNITY_test_rationale.py|test_rationale.py]]
- [[_COMMUNITY_movie.js|movie.js]]
- [[_COMMUNITY_template_context.py|template_context.py]]
- [[_COMMUNITY_make_inputs()|make_inputs()]]
- [[_COMMUNITY_delta.py|delta.py]]
- [[_COMMUNITY_test_watch.py|test_watch.py]]
- [[_COMMUNITY_ApiClient|ApiClient]]
- [[_COMMUNITY_test_ingest.py|test_ingest.py]]
- [[_COMMUNITY_sample_calls.py|sample_calls.py]]
- [[_COMMUNITY_benchmark.py|benchmark.py]]
- [[_COMMUNITY_wiki.py|wiki.py]]
- [[_COMMUNITY_test_pyproject.py|test_pyproject.py]]
- [[_COMMUNITY_test_build.py|test_build.py]]
- [[_COMMUNITY_watch()|watch()]]
- [[_COMMUNITY_Graph|Graph]]
- [[_COMMUNITY_Animal|Animal]]
- [[_COMMUNITY_MyApp.Accounts.User|MyApp.Accounts.User]]
- [[_COMMUNITY_Transformer|Transformer]]
- [[_COMMUNITY__safe_community_name()|_safe_community_name()]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY_manifest.py|manifest.py]]

## God Nodes (most connected - your core abstractions)
1. `MergePlan` - 98 edges
2. `MergeResult` - 79 edges
3. `MergeAction` - 75 edges
4. `ClassificationContext` - 55 edges
5. `_copy_vault_fixture()` - 53 edges
6. `Response` - 45 edges
7. `Request` - 42 edges
8. `_labels()` - 34 edges
9. `RenderedNote` - 33 edges
10. `Cookies` - 27 edges

## Surprising Connections (you probably didn't know these)
- `End-to-end pipeline test: detect → extract → build → cluster → analyze → report` --uses--> `MergeResult`  [INFERRED]
  /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_pipeline.py → /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/graphify/merge.py
- `Run the full pipeline on the fixtures directory. Returns a dict of outputs.` --uses--> `MergeResult`  [INFERRED]
  /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_pipeline.py → /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/graphify/merge.py
- `Second run on unchanged corpus should produce identical node/edge counts.` --uses--> `MergeResult`  [INFERRED]
  /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/tests/test_pipeline.py → /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/graphify/merge.py
- `API module - exposes the document pipeline over HTTP. Thin layer over parser, va` --uses--> `ValidationError`  [INFERRED]
  /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/worked/example/raw/api.py → /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/worked/example/raw/validator.py
- `Accept a list of file paths, run the full pipeline on each,     and return a sum` --uses--> `ValidationError`  [INFERRED]
  /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/worked/example/raw/api.py → /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify/worked/example/raw/validator.py

## Communities

### Community 0 - "test_templates.py"
Cohesion: 0.01
Nodes (111): _assemble_communities(), _build_sibling_labels(), classify(), compile_rules(), _derive_community_label(), _detect_dead_rules(), _inter_community_edges(), _is_shadowed() (+103 more)

### Community 1 - "MergePlan"
Cohesion: 0.02
Nodes (152): MergeAction, MergePlan, MergeResult, Pure data structure produced by compute_merge_plan (Plan 04).      Consumed by a, Mirror of MergePlan recording write outcomes after apply_merge_plan.      succes, One row in a MergePlan — decision for a single file path.      See D-71 for fiel, _make_proposal(), Tests for the graphify approve CLI helper functions. (+144 more)

### Community 2 - "Response"
Cohesion: 0.03
Nodes (101): Auth, BasicAuth, BearerAuth, DigestAuth, NetRCAuth, Authentication handlers. Auth objects are callables that modify a request before, Load credentials from ~/.netrc based on the request host., Base class for all authentication handlers. (+93 more)

### Community 3 - "test_profile.py"
Cohesion: 0.02
Nodes (54): NamedTuple, _deep_merge(), _dump_frontmatter(), load_profile(), PreflightResult, Profile loading, validation, deep merge, and safety helpers for Obsidian export., Recursively merge *override* into a copy of *base*. Override wins at leaf level., Discover and load a vault profile, merging over built-in defaults.      Returns (+46 more)

### Community 4 - "test_languages.py"
Cohesion: 0.03
Nodes (48): _calls(), _labels(), Tests for language extractors: Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Methods on the same receiver type must share one canonical type node., Type node id should be scoped to directory, not file stem., _relations(), test_c_finds_functions(), test_c_finds_includes() (+40 more)

### Community 5 - "extract.py"
Cohesion: 0.04
Nodes (80): _check_tree_sitter_version(), _csharp_extra_walk(), extract(), extract_blade(), extract_c(), extract_cpp(), extract_csharp(), extract_elixir() (+72 more)

### Community 6 - "test_mapping.py"
Cohesion: 0.03
Nodes (66): _profile(), Unit tests for graphify.mapping classify() + matchers (Phase 3, Plan 01)., VALIDATION row 3-01-01: non-god real node defaults to statement., VALIDATION row 3-01-02: then.folder overrides folder_mapping., VALIDATION row 3-01-03: god node falls through to thing when no rule matches., VALIDATION row 3-01-05: no rule match AND not a god node → statement., VALIDATION row 3-01-06: explicit attr rule beats implicit god-node fallback., VALIDATION row 3-01-07: first matching rule wins; trace records rule_index=0. (+58 more)

### Community 7 - "RenderedNote"
Cohesion: 0.05
Nodes (74): attach_hyperedges(), _cypher_escape(), _html_script(), _html_styles(), _hyperedge_script(), push_to_neo4j(), Store hyperedges in the graph's metadata dict., Escape a string for safe embedding in a Cypher single-quoted literal. (+66 more)

### Community 8 - "test_detect.py"
Cohesion: 0.04
Nodes (56): classify_file(), convert_office_file(), count_words(), detect(), detect_incremental(), docx_to_markdown(), extract_pdf_text(), FileType (+48 more)

### Community 9 - "merge.py"
Cohesion: 0.05
Nodes (64): _append_user_block(), _apply_field_policy(), apply_merge_plan(), _build_manifest_from_result(), _cleanup_stale_tmp(), _coerce_scalar(), compute_merge_plan(), _content_hash() (+56 more)

### Community 10 - "test_serve.py"
Cohesion: 0.04
Nodes (25): _make_graph(), Tests for serve.py - MCP graph query helpers (no mcp package required)., Verify the 9-line output format when node has provenance fields., Verify defaults when node has no provenance fields (per D-03)., classify_staleness returns FRESH when source_file or source_hash is missing., classify_staleness returns GHOST when source_file does not exist., test_bfs_depth_1(), test_bfs_depth_2() (+17 more)

### Community 11 - "test_install.py"
Cohesion: 0.05
Nodes (51): _agents_install(), _agents_uninstall(), _install(), Tests for graphify install --platform routing., Claude platform install writes CLAUDE.md; others do not., Installing twice does not duplicate the section., Installs into an existing AGENTS.md without overwriting other content., Uninstall keeps pre-existing content. (+43 more)

### Community 12 - "Geometry"
Cohesion: 0.07
Nodes (19): Base, Server, LinearAlgebra, add(), area(), Circle, Color, Config (+11 more)

### Community 13 - "serve.py"
Cohesion: 0.06
Nodes (35): _append_annotation(), _communities_from_graph(), _compact_annotations(), _filter_agent_edges(), _filter_annotations(), _filter_blank_stdin(), _find_node(), _list_proposals() (+27 more)

### Community 14 - "test_delta.py"
Cohesion: 0.07
Nodes (37): _make_graph(), Node whose source_hash matches current file hash returns FRESH., Node whose source_hash differs from current file hash returns STALE., Node whose source_file does not exist returns GHOST., Node without source_hash returns FRESH (no provenance to check)., Empty delta produces 'No changes detected'., Delta with adds/removes produces Summary + Archive sections., Helper: build nx.Graph from node ID list and optional edge tuples. (+29 more)

### Community 15 - "templates.py"
Cohesion: 0.1
Nodes (37): _build_connections_callout(), _build_dataview_block(), _build_frontmatter_fields(), _build_members_section(), _build_metadata_callout(), _build_sub_communities_callout(), _build_wayfinder_callout(), _emit_wikilink() (+29 more)

### Community 16 - "analyze.py"
Cohesion: 0.1
Nodes (33): _cross_community_surprises(), _cross_file_surprises(), _file_category(), god_nodes(), graph_diff(), _is_concept_node(), _is_file_node(), _node_community_map() (+25 more)

### Community 17 - "test_snapshot.py"
Cohesion: 0.12
Nodes (25): _make_communities(), _make_graph(), Tests for graphify.snapshot — save, load, prune, list., Create a small test graph with 3 nodes and 2 edges., On first call, snapshot is saved and GRAPH_DELTA.md contains 'First run'., After two calls with different graphs, GRAPH_DELTA.md contains change summary., delta_path is {root}/graphify-out/GRAPH_DELTA.md., Nodes from extract_python carry extracted_at, source_hash, source_mtime. (+17 more)

### Community 18 - "DataProcessor"
Cohesion: 0.08
Nodes (13): CacheManager, createProcessor(), DataProcessor, Get-Data(), GraphifyDemo, IProcessor, Loggable, NetworkError (+5 more)

### Community 19 - "test_extract.py"
Cohesion: 0.07
Nodes (18): After merging multiple files, no internal edges should be dangling., Call-graph pass must produce INFERRED calls edges., AST-resolved call edges are deterministic and should be EXTRACTED/1.0., Same input always produces same output., run_analysis() calls compute_score() - must appear as a calls edge., Analyzer.process() calls run_analysis() - cross class→function calls edge., Same caller→callee pair must appear only once even if called multiple times., All edge sources must reference a known node (targets may be external imports). (+10 more)

### Community 20 - "test_cache.py"
Cohesion: 0.07
Nodes (25): Tests for graphify/cache.py., Non-.md files are still hashed by their full content., _body_content correctly strips YAML frontmatter., _body_content returns content unchanged when no frontmatter present., Same file gives same hash on repeated calls., Different file contents give different hashes., Save then load returns the same result dict., After file content changes, load_cached returns None. (+17 more)

### Community 21 - "ValidationError"
Cohesion: 0.11
Nodes (25): handle_delete(), handle_enrich(), handle_get(), handle_list(), handle_search(), handle_upload(), API module - exposes the document pipeline over HTTP. Thin layer over parser, va, Accept a list of file paths, run the full pipeline on each,     and return a sum (+17 more)

### Community 22 - "test_analyze.py"
Cohesion: 0.11
Nodes (23): make_graph(), _make_simple_graph(), Tests for analyze.py., Code↔paper edge should score higher than code↔code edge., Helper: build a small nx.Graph from node/edge specs., Multi-file graph: should find cross-file edges between real entities., Concept nodes (empty source_file) must not appear in surprises., Single-file graph: should return cross-community edges, not empty list. (+15 more)

### Community 23 - "test_claude_md.py"
Cohesion: 0.08
Nodes (25): Tests for graphify claude install / uninstall commands., claude_install also writes .claude/settings.json with PreToolUse hook., Running claude_install twice does not duplicate the PreToolUse hook., Creates CLAUDE.md when none exists., claude_uninstall removes the PreToolUse hook from settings.json., Written section includes the three rules., Appends to an existing CLAUDE.md without clobbering it., Running install twice does not duplicate the section. (+17 more)

### Community 24 - "test_multilang.py"
Cohesion: 0.12
Nodes (17): _call_pairs(), _confidences(), _labels(), Tests for multi-language AST extraction: JS/TS, Go, Rust., test_go_emits_calls(), test_go_finds_constructor(), test_go_finds_methods(), test_go_finds_struct() (+9 more)

### Community 25 - "test_security.py"
Cohesion: 0.1
Nodes (6): _make_mock_response(), Tests for graphify/security.py - URL validation, safe fetch, path guards, label, test_safe_fetch_raises_on_non_2xx(), test_safe_fetch_returns_bytes(), test_safe_fetch_text_decodes_utf8(), test_safe_fetch_text_replaces_bad_bytes()

### Community 26 - "test_transcribe.py"
Cohesion: 0.09
Nodes (21): Tests for graphify.transcribe — video/audio transcription support., ImportError propagates when faster_whisper is not installed., Empty input returns empty list without error., transcribe_all() returns cached paths for already-transcribed files., transcribe_all() warns and skips files that fail to transcribe., Empty god_nodes returns fallback prompt., GRAPHIFY_WHISPER_PROMPT env var short-circuits LLM call., Returns a topic-based prompt from god node labels — no LLM call. (+13 more)

### Community 27 - "ingest.py"
Cohesion: 0.16
Nodes (21): _detect_url_type(), _download_binary(), _fetch_arxiv(), _fetch_html(), _fetch_tweet(), _fetch_webpage(), _html_to_markdown(), ingest() (+13 more)

### Community 28 - "test_wiki.py"
Cohesion: 0.17
Nodes (19): _make_graph(), Tests for graphify.wiki — Wikipedia-style article generation., God node with bad ID should not crash., Communities with more than 25 nodes show a truncation notice., test_article_navigation_footer(), test_community_article_has_audit_trail(), test_community_article_has_cross_links(), test_community_article_shows_cohesion() (+11 more)

### Community 29 - "cache.py"
Cohesion: 0.16
Nodes (18): _body_content(), cache_dir(), cached_files(), check_semantic_cache(), clear_cache(), file_hash(), load_cached(), Strip YAML frontmatter from Markdown content, returning only the body. (+10 more)

### Community 30 - "cluster.py"
Cohesion: 0.16
Nodes (17): build_graph(), cluster(), cohesion_score(), _partition(), Community detection on NetworkX graphs. Uses Leiden (graspologic) if available,, Run a second Leiden pass on a community subgraph to split it further., Context manager to suppress stdout/stderr during library calls.      graspologic, Ratio of actual intra-community edges to maximum possible. (+9 more)

### Community 31 - "test_confidence.py"
Cohesion: 0.14
Nodes (17): _make_extraction(), Tests for confidence_score on edges., Edges lacking confidence_score get sensible defaults in to_json., Report summary line should include avg confidence for INFERRED edges., Surprising connections section shows confidence score next to INFERRED edges., Return a minimal extraction dict with one edge of each confidence type., EXTRACTED edges must have confidence_score == 1.0., INFERRED edges must have confidence_score between 0.0 and 1.0. (+9 more)

### Community 32 - "test_hypergraph.py"
Cohesion: 0.14
Nodes (8): _make_report(), Tests for hyperedge support in graphify., Write graph.json then reload it - hyperedges must survive., test_hyperedges_roundtrip_via_json_file(), test_report_includes_hyperedge_node_list(), test_report_includes_hyperedges_section(), test_report_skips_hyperedges_section_when_empty(), test_report_skips_hyperedges_section_when_key_missing()

### Community 33 - "storage.py"
Cohesion: 0.21
Nodes (16): delete_record(), _ensure_storage(), list_records(), load_index(), load_record(), Storage module - persists documents to disk and maintains the search index. All, Load the full document index from disk., Persist the index to disk. (+8 more)

### Community 34 - "test_semantic_similarity.py"
Cohesion: 0.18
Nodes (16): _make_extraction_with_semantic_edge(), _make_graph_with_semantic_edge(), _make_report_with_semantic_surprise(), _make_two_edge_graph(), Tests for semantically_similar_to edge support., Two nodes in separate files connected by a semantically_similar_to edge., Non-semantic edges must not get the [semantically similar] tag., Graph with one semantically_similar_to edge and one references edge, both cross- (+8 more)

### Community 35 - "test_main_cli.py"
Cohesion: 0.23
Nodes (15): Phase 5 gap-closure (plan 06) — CLI integration tests for the new top-level flag, Invoke `python -m graphify <args...>` and return the completed process.      Use, Build a minimal 4-node / 2-community graph and write it to `path`     via the re, _run_cli(), test_help_mentions_new_flags(), test_obsidian_bad_graph_suffix_exits_1(), test_obsidian_dry_run_prints_plan_and_writes_nothing(), test_obsidian_full_run_writes_atlas_files() (+7 more)

### Community 36 - "TestPolicyDispatcher"
Cohesion: 0.12
Nodes (1): TestPolicyDispatcher

### Community 37 - "test_hooks.py"
Cohesion: 0.23
Nodes (14): _make_git_repo(), Tests for hooks.py - git hook install/uninstall., test_install_appends_to_existing_hook(), test_install_creates_hook(), test_install_creates_post_checkout_hook(), test_install_idempotent(), test_install_is_executable(), test_install_post_checkout_is_executable() (+6 more)

### Community 38 - "test_benchmark.py"
Cohesion: 0.29
Nodes (13): _make_graph(), Tests for graphify/benchmark.py., test_print_benchmark_no_crash(), test_query_bfs_expands_neighbors(), test_query_returns_positive_for_matching_question(), test_query_returns_zero_for_no_match(), test_run_benchmark_corpus_tokens_proportional(), test_run_benchmark_error_on_empty_graph() (+5 more)

### Community 39 - "security.py"
Cohesion: 0.17
Nodes (13): _build_opener(), _NoFileRedirectHandler, Fetch *url* and return decoded text (UTF-8, replacing bad bytes).      Wraps saf, Resolve *path* and verify it stays inside *base*.      *base* defaults to the `g, Strip control characters and cap length.      Safe for embedding in JSON data (i, Raise ValueError if *url* is not http or https, or targets a private/internal IP, Redirect handler that re-validates every redirect target.      Prevents open-red, Fetch *url* and return raw bytes.      Protections applied:     - URL scheme val (+5 more)

### Community 40 - "make_graph()"
Cohesion: 0.26
Nodes (14): make_graph(), test_to_cypher_contains_merge_statements(), test_to_cypher_creates_file(), test_to_graphml_creates_file(), test_to_graphml_has_community_attribute(), test_to_graphml_valid_xml(), test_to_html_contains_legend_with_labels(), test_to_html_contains_nodes_and_edges() (+6 more)

### Community 41 - "test_pipeline.py"
Cohesion: 0.23
Nodes (13): End-to-end pipeline test: detect → extract → build → cluster → analyze → report, Second run on unchanged corpus should produce identical node/edge counts., Run the full pipeline on the fixtures directory. Returns a dict of outputs., # NOTE: .obsidian/graph.json is no longer written by to_obsidian (D-74 refactor), run_pipeline(), test_pipeline_all_nodes_have_community(), test_pipeline_detection_finds_code_and_docs(), test_pipeline_extraction_confidence_labels() (+5 more)

### Community 42 - "transcribe.py"
Cohesion: 0.21
Nodes (13): build_whisper_prompt(), download_audio(), _get_whisper(), _get_yt_dlp(), is_url(), _model_name(), Transcribe a video/audio file or URL to a .txt transcript.      If video_path is, Transcribe a list of video/audio files or URLs, return paths to transcript .txt (+5 more)

### Community 43 - "processor.py"
Cohesion: 0.2
Nodes (13): enrich_document(), extract_keywords(), find_cross_references(), normalize_text(), process_and_save(), Processor module - transforms validated documents into enriched records ready fo, Lowercase, strip extra whitespace, remove control characters., Pull non-stopword tokens from text, deduplicated. (+5 more)

### Community 44 - "parser.py"
Cohesion: 0.2
Nodes (13): batch_parse(), parse_and_save(), parse_file(), parse_json(), parse_markdown(), parse_plaintext(), Parser module - reads raw input documents and converts them into a structured fo, Read a file from disk and return a structured document. (+5 more)

### Community 45 - "test_cluster.py"
Cohesion: 0.23
Nodes (9): make_graph(), Clustering should not emit ANSI escape codes or other output.      graspologic's, Same as above but for stderr — ANSI codes can go to either stream., test_cluster_covers_all_nodes(), test_cluster_does_not_write_to_stderr(), test_cluster_does_not_write_to_stdout(), test_cluster_returns_dict(), test_cohesion_score_range() (+1 more)

### Community 46 - "hooks.py"
Cohesion: 0.22
Nodes (12): _git_root(), install(), _install_hook(), Walk up to find .git directory., Install a single git hook, appending if an existing hook is present., Remove graphify section from a git hook using start/end markers., Install graphify post-commit and post-checkout hooks in the nearest git repo., Remove graphify post-commit and post-checkout hooks. (+4 more)

### Community 47 - "test_validate.py"
Cohesion: 0.17
Nodes (0): 

### Community 48 - "snapshot.py"
Cohesion: 0.24
Nodes (11): auto_snapshot_and_delta(), list_snapshots(), load_snapshot(), graph snapshot persistence - save, load, prune, list., Load a snapshot from disk.      Returns (graph, communities_with_int_keys, metad, Returns graphify-out/snapshots/ - creates it if needed., Return sorted list of snapshot Paths (oldest first by mtime)., Save graph snapshot to graphify-out/snapshots/{timestamp}[_name].json.      Atom (+3 more)

### Community 49 - "test_integration.py"
Cohesion: 0.3
Nodes (10): _make_graph(), _minimal_graph(), test_fix01_frontmatter_special_chars_quoted(), test_fix03_community_tag_sanitization(), test_merge_result_shape_after_normal_run(), test_re_run_is_idempotent(), test_to_obsidian_default_profile_returns_merge_result(), test_to_obsidian_default_profile_writes_atlas_layout() (+2 more)

### Community 50 - "build()"
Cohesion: 0.21
Nodes (9): build(), build_from_json(), Build a NetworkX graph from an extraction dict.      directed=True produces a Di, Merge multiple extraction results into one graph., Merge multiple extraction results into one graph.      directed=True produces a, assert_valid(), Validate an extraction JSON dict against the graphify schema.     Returns a list, Raise ValueError with all errors if extraction is invalid. (+1 more)

### Community 51 - "test_rationale.py"
Cohesion: 0.27
Nodes (11): Tests for rationale/docstring extraction in extract.py., # NOTE: must run before compile() or linker will fail, Trivial docstrings under 20 chars should not become rationale nodes., test_class_docstring_extracted(), test_function_docstring_extracted(), test_module_docstring_extracted(), test_rationale_comment_extracted(), test_rationale_confidence_is_extracted() (+3 more)

### Community 52 - "movie.js"
Cohesion: 0.36
Nodes (8): apiGet(), getByImdbId(), getByQuery(), isImdbId(), linkifyList(), notice(), replaceIllegalFileNameCharactersInString(), start()

### Community 53 - "template_context.py"
Cohesion: 0.2
Nodes (9): make_classification_context(), make_classification_fixture(), make_min_graph(), make_moc_context(), Shared test fixtures for graphify template engine tests (Plans 02-03, 02-04)., Multi-community fixture for Phase 3 classify() tests.      Returns (G, communiti, Return a ClassificationContext-shaped dict for MOC rendering tests.      Default, Return a minimal NetworkX graph with 3 nodes and 2 edges for testing.      Nodes (+1 more)

### Community 54 - "make_inputs()"
Cohesion: 0.38
Nodes (9): make_inputs(), test_report_contains_ambiguous_section(), test_report_contains_communities(), test_report_contains_corpus_check(), test_report_contains_god_nodes(), test_report_contains_header(), test_report_contains_surprising_connections(), test_report_shows_raw_cohesion_scores() (+1 more)

### Community 55 - "delta.py"
Cohesion: 0.24
Nodes (9): classify_staleness(), compute_delta(), _escape_pipe(), graph delta computation — diff, staleness, and GRAPH_DELTA.md rendering., Escape pipe characters in markdown table cells., Render a GRAPH_DELTA.md report from a delta dict.      Returns markdown string w, Compare two graph snapshots and return a structured diff dict.      Returns dict, Classify a node as FRESH, STALE, or GHOST based on source file state.      FRESH (+1 more)

### Community 56 - "test_watch.py"
Cohesion: 0.2
Nodes (1): Tests for watch.py - file watcher helpers (no watchdog required).

### Community 57 - "ApiClient"
Cohesion: 0.24
Nodes (1): ApiClient

### Community 58 - "test_ingest.py"
Cohesion: 0.2
Nodes (1): Tests for graphify.ingest.save_query_result

### Community 59 - "sample_calls.py"
Cohesion: 0.39
Nodes (5): Analyzer, compute_score(), normalize(), Fixture: functions and methods that call each other - for call-graph extraction, run_analysis()

### Community 60 - "benchmark.py"
Cohesion: 0.28
Nodes (8): _estimate_tokens(), print_benchmark(), _query_subgraph_tokens(), Token-reduction benchmark - measures how much context graphify saves vs naive fu, Print a human-readable benchmark report., Run BFS from best-matching nodes and return estimated tokens in the subgraph con, Measure token reduction: corpus tokens vs graphify query tokens.      Args:, run_benchmark()

### Community 61 - "wiki.py"
Cohesion: 0.36
Nodes (8): _community_article(), _cross_community_links(), _god_node_article(), _index_md(), Return (community_label, edge_count) pairs for cross-community connections, sort, Generate a Wikipedia-style wiki from the graph.      Writes:       - index.md, _safe_filename(), to_wiki()

### Community 62 - "test_pyproject.py"
Cohesion: 0.36
Nodes (7): _load_pyproject(), Regression guard for pyproject.toml packaging metadata.  Ensures Phase 1 Foundat, IN-10: graphify/templates.py must not import any third-party package.      The t, test_all_extras_includes_pyyaml(), test_obsidian_extras_group_exists(), test_package_data_includes_builtin_templates(), test_templates_module_is_pure_stdlib()

### Community 63 - "test_build.py"
Cohesion: 0.43
Nodes (6): load_extraction(), test_ambiguous_edge_preserved(), test_build_from_json_edge_count(), test_build_from_json_node_count(), test_edges_have_confidence(), test_nodes_have_label()

### Community 64 - "watch()"
Cohesion: 0.36
Nodes (7): _has_non_code(), _notify_only(), Watch watch_path for new or modified files and auto-update the graph.      For c, Re-run AST extraction + build + cluster + report for code files. No LLM needed., Write a flag file and print a notification (fallback for non-code-only corpora)., _rebuild_code(), watch()

### Community 65 - "Graph"
Cohesion: 0.47
Nodes (2): build_graph(), Graph

### Community 66 - "Animal"
Cohesion: 0.33
Nodes (5): Animal, -initWithName, -speak, Dog, -fetch

### Community 67 - "MyApp.Accounts.User"
Cohesion: 0.5
Nodes (3): MyApp.Accounts.User, create(), validate()

### Community 68 - "Transformer"
Cohesion: 0.5
Nodes (1): Transformer

### Community 69 - "_safe_community_name()"
Cohesion: 0.67
Nodes (3): generate(), Mirrors export.safe_name so community hub filenames and report wikilinks always, _safe_community_name()

### Community 70 - "__init__.py"
Cohesion: 0.67
Nodes (1): graphify - extract · build · cluster · analyze · report.

### Community 71 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "manifest.py"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **456 isolated node(s):** `Merge multiple extraction results into one graph.`, `Build a NetworkX graph from graphify node/edge dicts.      Preserves original ed`, `Run Leiden community detection. Returns {community_id: [node_ids]}.      Communi`, `Run a second Leiden pass on a community subgraph to split it further.`, `Ratio of actual intra-community edges to maximum possible.` (+451 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `manifest.py`** (1 nodes): `manifest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RenderedNote` connect `RenderedNote` to `test_templates.py`, `merge.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `ClassificationContext` connect `test_templates.py` to `templates.py`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `_MalformedSentinel` connect `merge.py` to `Response`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 95 inferred relationships involving `MergePlan` (e.g. with `Tests for the graphify approve CLI helper functions.` and `Write a proposal JSON file to tmp_path/proposals/ and return the record.`) actually correct?**
  _`MergePlan` has 95 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `MergeResult` (e.g. with `Tests for the graphify approve CLI helper functions.` and `Write a proposal JSON file to tmp_path/proposals/ and return the record.`) actually correct?**
  _`MergeResult` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 72 inferred relationships involving `MergeAction` (e.g. with `Tests for the graphify approve CLI helper functions.` and `Write a proposal JSON file to tmp_path/proposals/ and return the record.`) actually correct?**
  _`MergeAction` has 72 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `ClassificationContext` (e.g. with `Unit tests for graphify/templates.py — template engine helpers.` and `UAT Test 5 regression: \\t in alias embeds invisibly inside [[...]].`) actually correct?**
  _`ClassificationContext` has 53 INFERRED edges - model-reasoned connections that need verification._