---
status: complete
phase: 10-cross-file-semantic-extraction
source: [10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md, 10-04-SUMMARY.md, 10-05-SUMMARY.md, 10-06-SUMMARY.md, 10-07-SUMMARY.md]
started: 2026-04-16T20:57:00-05:00
updated: 2026-04-16T22:05:00-05:00
---

## Current Test

[testing complete]

## Tests

### 1. CLI Help — Dedup Flags Listed
expected: Running `graphify --help` lists `--dedup`, `--dedup-fuzzy-threshold`, `--dedup-embed-threshold`, `--dedup-cross-type`, `--batch-token-budget` in the help output.
result: pass

### 2. Dedup on Empty Extraction
expected: Running `graphify --dedup --graph <path-to-empty-extraction.json> --out-dir <tmpdir>` exits 0, writes `dedup_report.json` (with `merges: []`, zero counts) and `dedup_report.md` into `<tmpdir>`. No crash when there is nothing to merge.
result: issue
reported: "I created an empty json file and the result was: graphify --dedup --graph empty-extraction.json — error: could not read extraction from empty-extraction.json: Expecting value: line 1 column 1 (char 0)"
severity: minor
followup: Claude re-ran with a valid empty-content JSON `{"nodes":[],"edges":[]}` — that path works correctly (0 -> 0 nodes, 0 merges, reports written). The original failure was on a zero-byte file, which the CLI rejects as malformed JSON. UX polish: consider treating a zero-byte file as empty extraction.

### 3. Dedup on Extraction with Near-Duplicates
expected: Running `graphify --dedup` on a real/test extraction containing near-duplicate entities produces a `dedup_report.json` with one or more merge entries — each showing a canonical id, eliminated ids, and fuzzy/cosine scores. `dedup_report.md` renders the same merges with HTML-escaped labels (no raw `<script>` etc.).
result: pass
verified_by: Claude ran `graphify --dedup --graph tests/fixtures/multi_file_extraction.json --out-dir graphify-out/uat-test`. Output: 7 -> 6 nodes, 1 merge. Reports match spec (canonical_id, canonical_label, eliminated[].id/label/source_file, fuzzy_score=1.0, cos_score=1.0, sanitized labels in .md).

### 4. YAML Config Layering — .graphify/dedup.yaml
expected: With `.graphify/dedup.yaml` containing thresholds (e.g. `fuzzy_threshold: 0.95`), running `graphify --dedup` without CLI overrides uses the YAML value. Passing `--dedup-fuzzy-threshold 0.80` on the CLI overrides the YAML value.
result: pass
verified_by: Claude wrote `.graphify/dedup.yaml` with `fuzzy_threshold: 0.95, embed_threshold: 0.95`. First run logged `fuzzy>=0.95, cos>=0.95`. Second run with `--dedup-fuzzy-threshold 0.80` logged `fuzzy>=0.8, cos>=0.95` (CLI override confirmed).

### 5. Unknown Dedup Flag Rejected
expected: Running `graphify --dedup --dedup-bogus` exits with code 2 and prints an error mentioning `unknown --dedup option` (or similar) to stderr.
result: pass
verified_by: Claude ran `graphify --dedup --dedup-bogus` via subprocess — returncode=2, stderr='error: unknown --dedup option: --dedup-bogus'.

### 6. GRAPH_REPORT.md — Entity Dedup Section
expected: After a pipeline run that produces dedup merges, the rendered report contains a `## Entity Dedup` section with summary + merge entries in the form `` `canonical_label` ← elim1 [fuzzy=..., cos=...] ``. When no merges or dedup_report=None, the section is absent (backward compatible).
result: pass
verified_by: Claude called `report.generate(..., dedup_report=<from uat-test>)` directly. Output included `## Entity Dedup\n- 1 entities merged · 7 nodes → 6 nodes` and the merge row ``- `AuthService` ← AuthService  [fuzzy=1.000, cos=1.000]``. Both `dedup_report=None` and `dedup_report={merges:[]}` produced reports WITHOUT the section.

### 7. Obsidian Aliases Frontmatter (--obsidian-dedup)
expected: Canonical-entity Obsidian notes with `merged_from` emit an `aliases:` YAML list in frontmatter. Eliminated IDs are sanitized (no `]`, `|`, newlines). Nodes without `merged_from` omit the key entirely.
result: pass
verified_by: Claude built an nx.Graph with a node carrying `merged_from=["auth_svc","authsvc","auth]|bad"]` and called `templates.render_note()`. Frontmatter contained `aliases:` with sorted/deduped/sanitized values (`auth]|bad` → `"auth]-bad"`). A second node without `merged_from` rendered with NO `aliases:` key.

### 8. MCP Serve Alias Redirect (D-16)
expected: With an alias_map loaded, calling `_run_query_graph` with a merged-away identifier (via any of node_id/source/target/seed/start/seed_nodes) returns the canonical seed and meta includes `resolved_from_alias: {canonical_id: [alias, ...]}`. Without alias_map, the field is absent.
result: pass
verified_by: Claude called `_run_query_graph(G, communities, 0.0, 1.0, telemetry, {node_id:'auth', question:'authservice', ...}, alias_map={'auth':'authentication_service'})`. Response meta included `"resolved_from_alias": {"authentication_service": ["auth"]}` (list-per-canonical shape from WR-02 fix). Backward-compat call without alias_map produced meta without the key.

### 9. Skill Files — Per-Cluster Dispatch in All 9 Variants
expected: Each of 9 skill files references `cluster_files` (Step B0.5) and includes an optional `graphify --dedup` post-step (Step C.5).
result: pass
verified_by: Claude grep'd all 9 files — every variant has 3 `cluster_files`/B0.5 hits AND 3 `graphify --dedup`/C.5 hits (uniform across skill.md, skill-codex.md, skill-opencode.md, skill-aider.md, skill-claw.md, skill-droid.md, skill-trae.md, skill-windows.md, skill-copilot.md).

## Summary

total: 9
passed: 8
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "graphify --dedup on a zero-byte --graph file should treat it as empty extraction (exit 0, empty report) rather than surface a JSON parse error"
  status: failed
  reason: "User reported: I created an empty json file and the result was: graphify --dedup --graph empty-extraction.json — error: could not read extraction from empty-extraction.json: Expecting value: line 1 column 1 (char 0). Note: a file containing `{\"nodes\":[],\"edges\":[]}` works fine (Claude verified); only the zero-byte case errors."
  severity: minor
  test: 2
  artifacts:
    - path: "graphify/__main__.py"
      issue: "--dedup handler surfaces JSONDecodeError text when the --graph file is empty — not a crash, but a confusing UX"
  missing:
    - "Short-circuit: if --graph file size is 0 bytes, treat as {\"nodes\":[],\"edges\":[]} or print a clearer 'extraction file is empty' hint"

- truth: "The dedup → build → analyze pipeline composes cleanly when source_file is list-valued (D-12 schema extension)"
  status: failed
  reason: "Claude verified end-to-end via `dedup.dedup()` → `build.build_from_json()` → `analyze.god_nodes()`. god_nodes crashes with TypeError because `_is_file_node` in analyze.py calls `Path(source_file).name` on a node whose `source_file` is now a `list[str]` (D-12). The unit tests for dedup and analyze pass in isolation but the composed flow is broken."
  severity: major
  test: 6
  artifacts:
    - path: "graphify/analyze.py:27"
      issue: "_is_file_node treats source_file as str and passes it to Path(); after dedup folds multiple source_files into a list, this raises TypeError: expected str, bytes or os.PathLike object, not list"
  missing:
    - "Update analyze._is_file_node to handle source_file: str | list[str] (e.g. iterate if list, match if any file's name == label)"
    - "Audit other call sites that read `source_file`: analyze.py:11-38, report.py, export.py — anywhere that does Path(source_file) must handle list"
    - "Add an integration test: dedup_then_analyze fixture that exercises the composed pipeline"

- truth: "graphify --dedup should surface friendly errors (not Python tracebacks) when sentence-transformers is missing or when --out-dir escapes cwd"
  status: failed
  reason: "Claude verified: (a) missing [dedup] extra → uncaught RuntimeError traceback printed to stderr, though exit code is correctly 1 (CLI argparse catches it). (b) --out-dir /tmp/... → uncaught ValueError traceback from T-10-01 path confinement, exit code 1. Both error paths work functionally but leak Python internals to the user."
  severity: minor
  test: 3
  artifacts:
    - path: "graphify/__main__.py"
      issue: "--dedup handler does not wrap dedup()/write_dedup_reports() in try/except for RuntimeError (missing dep) or ValueError (path confinement) — the exception reaches sys.excepthook"
    - path: "graphify/dedup.py:172-177, 218-224"
      issue: "_get_model() and write_dedup_reports() raise cleanly-worded exceptions — just not caught at CLI boundary"
  missing:
    - "try/except RuntimeError around dedup() in --dedup handler: print clean 'error: <message>' and sys.exit(1)"
    - "try/except ValueError around write_dedup_reports() in --dedup handler: print clean 'error: <message>' and sys.exit(1)"

- truth: "MCP alias redirect should surface resolved_from_alias in meta even on the no_seed_nodes short-circuit path"
  status: failed
  reason: "Claude verified: when a query passes only node_id='auth' (no question text) and alias_map resolves it to canonical, the request short-circuits to status='no_seed_nodes' BEFORE the meta-merge that includes resolved_from_alias. An agent passing only node_id won't see that alias resolution happened. Happy path (with findable question) correctly surfaces the field."
  severity: minor
  test: 8
  artifacts:
    - path: "graphify/serve.py:843-856"
      issue: "no_seed_nodes early-return returns a meta dict that omits _resolved_aliases even when _resolved_aliases is non-empty"
    - path: "graphify/serve.py:779-822"
      issue: "arguments['node_id'] is rewritten via _resolve_alias but _score_nodes only consumes question text — the rewritten node_id never becomes a seed on its own"
  missing:
    - "Include resolved_from_alias in the no_seed_nodes early-return meta when _resolved_aliases is non-empty"
    - "Consider whether arguments['node_id'] should be a seed source in _score_nodes (or documented as metadata-only)"
