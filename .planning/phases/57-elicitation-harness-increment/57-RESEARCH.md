# Phase 57: Elicitation & harness increment - Research

**Researched:** 2026-05-03
**Domain:** Test hardening + documentation around the existing elicitation sidecar merge and harness import surface (no new code paths)
**Confidence:** HIGH

## Summary

Phase 57 is a **lock-down phase**: it adds tests around already-shipped code (`graphify/build.py:281-299` sidecar merge, `graphify/harness_import.py` import path, the `import-harness` CLI in `graphify/__main__.py:2510-2585`, and the MCP `import_harness` tool in `graphify/serve.py:3724-3793`) and updates `docs/ELICITATION.md` in place with two new sections. There is **no new code surface**: no new CLI commands, no new MCP tools, no new harness target formats, no real inverse round-trip. Every deliverable points back at code or behavior that already exists today.

The four requirements decompose cleanly: ELIC-01 is pure unit tests against `merge_elicitation_into_build_inputs` and `build()` with sidecar input; ELIC-02 is a docs edit; HARN-01 is prose (canonical mapping for `graphify.harness.interchange/v1`) co-located in the ELIC-02 doc plus regression tests on the existing CLI + MCP surface; HARN-02 is three guard tests proving import refuses vault-rooted output, is never auto-invoked, and requires an explicit MCP `path` argument.

**Primary recommendation:** Extend existing test modules (`tests/test_elicit.py` for ELIC-01, `tests/test_harness_import.py` for HARN-01 lock-in + HARN-02 vault-output guard, `tests/test_mcp_harness_io.py` for HARN-02 MCP guard) rather than creating a new `tests/test_phase57_guards.py`. Add the call-graph "no auto-invocation" guard as a simple AST-grep test that scans `graphify/*.py` for `import_harness_path` / `import_harness_bytes` references and asserts only `__main__.py` and `serve.py` mention them. For ELIC-02/HARN-01 doc sections, edit `docs/ELICITATION.md` in place (currently 52 lines) and add `## Trust Boundaries`, `## Canonical Harness Interchange (v1) Mapping`, and `## Milestone Non-Goals (v1.11)` headings. The existing import surface enforces vault-output refusal **transitively** via `validate_graph_path(resolved, base=artifacts_root)` — guard tests assert this end-to-end rather than building a new vault detector.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**ELIC-01 — Scripted elicitation scenario tests**
- **D-01:** New scenario coverage = **sidecar collision behavior** in `graphify/build.py:281-299` (the `elicitation` arg / `merge_elicitation_into_build_inputs` path).
- **D-02:** Coverage spans **nodes AND edges**: node-id collision (elicitation wins), duplicate edges, same source/target with conflicting `relation`, and confidence preservation across the merge.
- **D-03:** Failure modes in scope: malformed sidecar JSON, missing required fields, sidecar with edges referencing absent nodes. Happy-path artifact-shape assertions on the resulting graph.
- **D-04:** Sidecar on-disk schema assertions (file shape / ordering) are out of scope — `validate.py` territory.

**HARN-01 — Incremental capability lane**
- **D-05:** Lane chosen = **inverse-import guards on the existing surface** (NOT a new export target format, NOT a new round-trip).
- **D-06:** "Inverse-import" in this phase means the **already-shipped** `graphify import-harness` CLI (`graphify/__main__.py:2512+`) and the MCP `import_harness` tool (`graphify/serve.py:3724+`). No new code paths.
- **D-07:** Deliverable = documented canonical mapping (`graphify.harness.interchange/v1` schema as it exists today, in prose) + lock-in guard tests. Doc lives in the ELIC-02 deliverable (`docs/ELICITATION.md`) under the trust-boundaries section, NOT in a new doc.

**HARN-02 — Import off-by-default guard surface**
- **D-08:** Guard tests must prove three guarantees:
  1. **Refuses vault-rooted output** — `import-harness` with `--output` resolving inside any vault path is rejected unless the user passes an explicit confirmation flag.
  2. **Never auto-invoked from pipelines** — no other graphify command (`run`, `watch`, `update-vault`, `elicit`, `doctor`) calls `import_harness_path` / `import_harness_bytes` transitively.
  3. **MCP tool requires explicit args** — `import_harness` MCP tool refuses to run without an explicit `path` argument; no defaults, no auto-discovery.
- **D-09:** Size caps and prompt-injection sanitization (`MAX_HARNESS_IMPORT_BYTES`, `sanitize_harness_text`) are **out of scope** — already covered in Phase 40. Reference, do not re-test.

**ELIC-02 — Trust-boundaries documentation**
- **D-10:** Update `docs/ELICITATION.md` **in place** (not a new `TRUST-BOUNDARIES.md`, not a full rewrite). Add `## Trust Boundaries` and `## Milestone Non-Goals (v1.11)`.
- **D-11:** Trust Boundaries section explicitly addresses three surfaces: where elicitation reads/writes (`resolve_output()` contract; sidecar at `artifacts_dir/elicitation.json`; never reads from vault config without explicit user consent); what `import-harness` will and will not do (off-by-default; refuses vault-rooted output; requires explicit path; no MCP auto-discovery); LLM trust posture during `elicit` (free-text sanitization across `--demo` / interactive paths and label escaping for HTML/Obsidian).
- **D-12:** Sidecar merge precedence is NOT separately documented in the trust boundaries — ELIC-01 tests are the canonical record. Doc may reference the test module.

### Claude's Discretion
- Test file layout: extend `tests/test_elicit.py` and `tests/test_harness_import.py` vs. create new `tests/test_phase57_guards.py`. **Research recommendation:** extend (matches project pattern: one test file per module).
- Exact name of the explicit confirmation flag for vault-rooted output (e.g., `--allow-vault-write`). **Research recommendation:** `--allow-vault-write` — long-form, deliberate, no short alias.
- Whether the "no auto-invocation" guard test uses static import-graph analysis or runtime grep. **Research recommendation:** AST-based scan of `graphify/*.py` for the function names, asserting allowlist of files = `{__main__.py, serve.py, harness_import.py}`. AST avoids false positives in docstrings/comments.

### Deferred Ideas (OUT OF SCOPE)
- **Real inverse round-trip** (harness_export → harness_import → graph equality) — future milestone.
- **New harness target format** — orthogonal capability extension.
- **Sidecar on-disk schema assertions** (field ordering, schema version field) — overlaps with `validate.py`; would expand ELIC-01 beyond "one scenario".
- **Re-testing size caps and prompt-injection sanitization** — already covered by Phase 40.
- **Refactoring `docs/ELICITATION.md` into a milestone-current overview** — bigger writing job.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ELIC-01 | ≥1 additional scripted elicitation→extraction scenario covered by unit tests vs v1.9 baseline (failure modes + happy-path artifact shape) | Sidecar-collision merge contract is fully readable in `graphify/build.py:281-307` and `graphify/elicit.py:182-313`; existing patterns in `tests/test_elicit.py:102-137` show how to build, save, merge, and assert. Edge dedupe key is `(source, target, relation, source_file)` (build.py via `add_edge` semantics; elicit `_merge_extractions_by_node_id` uses identical key) — tests must exercise conflicting `relation` between identical (source, target) pairs and confidence preservation. |
| ELIC-02 | `docs/ELICITATION.md` (or successor) states trust boundaries, artifact locations, and milestone non-goals | Current `docs/ELICITATION.md` is 52 lines, organized around "When to use", "CLI", "Where artifacts land", "Merge order", "Where sidecar merge runs", "Non-goals (other phases)". Two new H2 sections slot cleanly after "Where sidecar merge runs" and before/replacing the existing "Non-goals" section. |
| HARN-01 | Harness export adds documented canonical mapping + tests for one incremental capability (inverse-import remains off-default with explicit guard tests if touched) | `graphify/harness_interchange.py` defines `INTERCHANGE_SCHEMA_ID = "graphify.harness.interchange/v1"` and `graph_data_to_extraction()` is the canonical mapping function. Lock-in tests assert constant value, schema id round-trip through `_parse_interchange_v1`, and prose-doc contains the field table. |
| HARN-02 | Any import entrypoint remains off-by-default and cannot write vault paths without explicit user-approved CLI/MCP semantics; guard tests prove this | `import_harness_path` already calls `validate_graph_path(resolved, base=artifacts_root)` which is path-confined. The "vault-rooted output" guard is about the `--output` arg → `_resolve_cli_paths` resolution landing under a vault root. Only two call sites in `graphify/`: `__main__.py:2517` and `serve.py:3733` — auto-invocation guard has a tiny allowlist. MCP tool reads `arguments.get("path") or ""` — empty/missing fails `validate_graph_path` already. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sidecar collision merge semantics | Library (build.py, elicit.py) | — | Pure dict→graph transform; tests are unit-level against `merge_elicitation_into_build_inputs` + `build()` |
| Harness import path enforcement | Library (harness_import.py) | CLI/MCP entrypoints (call-site only) | `validate_graph_path` lives in `security.py`; CLI/MCP only resolve the path then delegate |
| Vault-output refusal | CLI argparse + `output.resolve_output` chain | harness_import.py (validates final base) | Vault detection is `is_obsidian_vault()` (presence of `.obsidian/`); CLI must short-circuit before delegating |
| MCP arg validation | MCP server (serve.py) | — | Tool dispatcher reads `arguments.get("path")` directly; explicit-path guarantee enforced at MCP boundary |
| Trust-boundary documentation | docs/ELICITATION.md | — | Pure docs; no code |
| Canonical mapping prose | docs/ELICITATION.md | harness_interchange.py (constants are source of truth) | Prose mirrors what `graph_data_to_extraction()` already produces; tests assert constants match doc |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | (project default; `pip install -e .[all]`) | Test runner | Already the project's test framework — `tests/test_*.py` files, `tests/conftest.py` exists `[VERIFIED: ls tests/]` |
| networkx | (no version pin) | Graph assembly target for `build()` output | Project standard `[VERIFIED: pyproject.toml]` |
| stdlib `json`, `pathlib` | py3.10+ | Sidecar JSON I/O, path validation | No new deps allowed per CLAUDE.md `[CITED: CLAUDE.md "No new required dependencies"]` |

### Supporting (already imported by tests being extended)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `subprocess` + `sys.executable` | CLI smoke test driver | Pattern from `tests/test_harness_import.py:82-117` for `--allow-vault-write`-style CLI guard tests |
| `pytest.MonkeyPatch` | `monkeypatch.chdir`, env var stubs | Existing pattern for CLI tests; reuse for vault-rooted-output test |
| `ast` (stdlib) | Static call-site analysis for HARN-02 guarantee #2 | AST scan over `graphify/*.py` to assert `import_harness_path` is referenced only in allowlisted files |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AST scan for auto-invocation guard | `grep -rn "import_harness" graphify/` via `subprocess` | grep is simpler but susceptible to docstring/comment false positives; AST is ~15 lines and precise. Pick AST. |
| New `tests/test_phase57_guards.py` | Extend existing test files | New file would group three logically-related guards but breaks the project's "one test file per module" convention `[CITED: CLAUDE.md "Testing Conventions"]`. Pick extend-existing. |
| New `--allow-vault-write` CLI flag | `GRAPHIFY_ALLOW_VAULT_WRITE` env var | Flag is more discoverable in `--help`; env var is harder to reason about. Pick flag. |

**Installation:** No new dependencies. Run tests as-is:
```bash
pytest tests/test_elicit.py tests/test_harness_import.py tests/test_mcp_harness_io.py -q
```

## Architecture Patterns

### System Architecture Diagram

```
                  ┌─────────────────────────────┐
                  │  graphify elicit --demo     │
                  └──────────────┬──────────────┘
                                 │ writes
                                 ▼
                ┌─────────────────────────────────┐
                │  artifacts_dir/elicitation.json │ ◄── sidecar (versioned envelope)
                └──────────────┬──────────────────┘
                               │ load_elicitation_sidecar()
                               ▼
  ┌───────────────────┐    ┌────────────────────────────────────┐
  │  AST/semantic     │───▶│ merge_elicitation_into_build_inputs│
  │  extractions[]    │    │   (elicit.py)                       │
  └───────────────────┘    └──────────────┬──────────────────────┘
                                          │ list[dict] (elicitation appended last)
                                          ▼
                          ┌──────────────────────────────────┐
                          │ build(extractions,               │
                          │       elicitation=None)          │ ◄── ELIC-01 surface
                          │  (build.py:288-307)              │     (last-wins on node id;
                          │  - extends nodes/edges in order  │      edges keyed by
                          │  - calls build_from_json()       │      (src,tgt,rel,src_file))
                          └──────────────┬───────────────────┘
                                         │
                                         ▼
                                  nx.Graph / DiGraph

  ─── separate, off-by-default surface ──────────────────────────────────
                                                                                          
  ┌───────────────────┐    ┌────────────────────────────────────┐    ┌──────────────────┐
  │ user-supplied     │───▶│ import_harness_path(path,          │───▶│ harness_import.  │
  │ harness file      │    │   format, strict, artifacts_root)  │    │   json (in       │
  └───────────────────┘    │  (harness_import.py:216-268)        │    │   artifacts_dir) │
                           │  - validate_graph_path under base   │    └──────────────────┘
                           │  - sanitize + validate_extraction   │
                           └─────┬────────────────────┬──────────┘
                                 │                    │
                  ┌──────────────┘                    └────────────┐
                  │                                                │
        ┌─────────▼──────────┐                       ┌─────────────▼────────────┐
        │  CLI: graphify     │                       │  MCP: import_harness     │
        │  import-harness    │                       │  tool (serve.py:3724-    │
        │  (__main__.py:2510-│                       │  3793) — requires        │
        │  2585)             │                       │  arguments["path"]       │
        └────────────────────┘                       └──────────────────────────┘
```

### Pattern 1: Sidecar collision merge contract

**What:** `merge_elicitation_into_build_inputs(extractions, artifacts_dir)` returns a list with the loaded sidecar appended **last**; `build()` iterates the list and `add_node`/`add_edge` overwrite on collision (NetworkX semantics). Edge identity for in-list dedupe (in elicit's `_merge_extractions_by_node_id`) uses the 4-tuple `(source, target, relation, source_file)`. **In `build()` itself, edges are appended via `combined["edges"].extend(...)` and then materialized via `G.add_edge(...)` — `add_edge` is idempotent on the (u, v) pair, so the *last* edge attribute write wins per (source, target) but a *different relation* on the same (source, target) silently overwrites attrs in an undirected `nx.Graph`.**

**When to use:** Tests target this contract end-to-end via a base-extraction list + sidecar combination, asserting on the resulting `G.nodes[id]` attrs and `G.edges[u, v]` attrs.

**Example:**
```python
# Source: tests/test_elicit.py:102-124 (existing pattern)
def test_build_includes_elicitation_last_wins(tmp_path: Path) -> None:
    adir = tmp_path / "art"
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext_elic = build_extraction_from_session(session)
    save_elicitation_sidecar(adir, ext_elic, force=True)
    base_like = {"nodes": [{"id": "elicitation_hub", "label": "from code",
                            "file_type": "code", "source_file": "x.py"}], "edges": []}
    seq = merge_elicitation_into_build_inputs([base_like], adir)
    G = build(seq)
    assert G.nodes["elicitation_hub"]["file_type"] == "rationale"
```

### Pattern 2: CLI smoke test via subprocess + monkeypatch.chdir

**What:** Drive `python -m graphify import-harness <path>` via `subprocess.run` from a `tmp_path` cwd; assert exit code and sidecar artifact landed under `tmp_path/graphify-out/`.

**When to use:** HARN-02 vault-rooted-output guard test (assert exit ≠ 0 when `--output` resolves under a fake `.obsidian/`-bearing dir, exit == 0 with `--allow-vault-write`).

**Example:**
```python
# Source: tests/test_harness_import.py:82-117 (existing pattern, adapted)
def test_import_refuses_vault_rooted_output(tmp_path, monkeypatch):
    vault = tmp_path / "myvault"
    (vault / ".obsidian").mkdir(parents=True)            # makes it a vault
    src = tmp_path / "harness_memory.v1.json"
    src.write_text(json.dumps(_minimal_envelope()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = subprocess.run(
        [sys.executable, "-m", "graphify", "import-harness", str(src),
         "--output", str(vault)],
        capture_output=True, text=True, timeout=60,
    )
    assert rc.returncode != 0
    assert "vault" in rc.stderr.lower()
```

### Pattern 3: AST-based call-site allowlist (HARN-02 guarantee #2)

**What:** Walk every `.py` file under `graphify/`, parse with `ast.parse`, and collect any `Name` / `Attribute` referencing `import_harness_path` or `import_harness_bytes`. Assert the set of files referencing them is exactly `{__main__.py, serve.py, harness_import.py}` (the third being the definition site).

**When to use:** "Never auto-invoked" guarantee — meta-test that fails loudly when a future patch wires import into `run` / `watch` / `update-vault` / `elicit` / `doctor`.

**Example:**
```python
import ast, pathlib
def test_no_auto_invocation_of_import_harness():
    root = pathlib.Path(__file__).resolve().parents[1] / "graphify"
    callers: set[str] = set()
    for py in root.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in {"import_harness_path", "import_harness_bytes"}:
                callers.add(py.name)
            elif isinstance(node, ast.Attribute) and node.attr in {"import_harness_path", "import_harness_bytes"}:
                callers.add(py.name)
    assert callers <= {"__main__.py", "serve.py", "harness_import.py"}, callers
```
*(`harness_import.py` shows up because the functions are defined there; the assertion is `<=` not `==` to allow definition site.)*

### Anti-Patterns to Avoid
- **Re-testing size caps or sanitization** — Phase 40 already covers `MAX_HARNESS_IMPORT_BYTES` (`tests/test_harness_import.py:40` `test_import_oversized_file`) and injection guards (`tests/test_harness_import.py:49-80`). New tests must reference these by name, not duplicate.
- **Asserting on sidecar JSON file structure** — D-04 puts that out of scope; assert on the *graph that results* from the merge, not on the JSON envelope.
- **Building a new vault detector** — `graphify/output.py:67 is_obsidian_vault()` is the project's single source of truth (presence of `.obsidian/`). Tests reuse it; CLI guard reuses it.
- **Changing the `import_harness_path` signature** — HARN-02 guards work *outside* the function. The function already enforces `validate_graph_path(resolved, base=artifacts_root)`; the new guard is at the CLI/argparse layer that picks `artifacts_root`.
- **Using `__doc__` / regex grep for the auto-invocation guard** — false positives on docstrings/comments (e.g. `harness_import.py`'s own module docstring mentions itself). Use AST.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault detection | New `is_vault_path` helper | `graphify.output.is_obsidian_vault(path)` | Single source of truth; tested in Phase 28/41. |
| Path-under-base check | New traversal validator | `graphify.security.validate_graph_path(path, base=...)` | Already path-confined (raises `ValueError`/`OSError`); used by `import_harness_path` and `save_elicitation_sidecar`. |
| Edge dedupe key in tests | New tuple ordering | `(source, target, relation, source_file)` per `elicit._merge_extractions_by_node_id:194-198` | Project's canonical edge identity; matches `validate_extraction` field order. |
| Harness envelope construction in tests | Hand-built JSON | `graphify.harness_interchange.export_interchange_v1(graph_dict, out_path=None)` | Used by existing tests (`test_harness_import.py:88-95`); guarantees schema-id and provenance fields are correct. |
| Resolved output from CLI flags | Re-implementing argparse | `graphify.__main__._resolve_cli_paths(...)` (already used by `import-harness` cmd) | Vault-rooted-output guard plugs into the *resolved* `artifacts_dir`, after `_resolve_cli_paths` runs. |

**Key insight:** Every load-bearing primitive for this phase already exists in the codebase. Phase 57 is *test surface* + *prose*, not new abstractions.

## Common Pitfalls

### Pitfall 1: Undirected vs directed graph semantics in edge-collision tests
**What goes wrong:** `build()` defaults to `directed=False` → `nx.Graph`, where (u, v) and (v, u) are the same edge and only one set of attrs survives. A test asserting "two edges with conflicting `relation` both survive" will fail in undirected mode.
**Why it happens:** NetworkX `Graph.add_edge` overwrites attrs on the (u, v) pair; `MultiGraph` would be needed to preserve parallel edges, but graphify uses simple `Graph`.
**How to avoid:** Tests assert *which relation wins* (the elicitation/last one), not "both survive." If multi-relation parallelism matters, run `build(seq, directed=True)` — a `DiGraph` still collapses parallel edges between the same (u, v), so the assertion remains "last write wins on attrs."
**Warning signs:** Test name mentions "both edges preserved" or "edge count == 2 for same (src, tgt)".

### Pitfall 2: `artifacts_root` defaults differ between CLI and library
**What goes wrong:** `import_harness_path` defaults `artifacts_root` to `Path("graphify-out").resolve()` (cwd-relative). The CLI passes a `_resolve_cli_paths(...).artifacts_dir` which may be vault-rooted. The vault-rooted-output guard must trigger on the *CLI-resolved* root, not the library default.
**Why it happens:** Two layers of "what is the base?" — the security check and the artifact landing dir.
**How to avoid:** Guard test exercises the CLI subprocess (Pattern 2 above), not the library function. The library function's `validate_graph_path` is orthogonal — it ensures the *source file* lives under `artifacts_root`, not that the *output* is non-vault.
**Warning signs:** Test calls `import_harness_path(...)` directly and tries to assert vault refusal — won't work; the function doesn't check vault-ness of its base.

### Pitfall 3: Sidecar JSON envelope vs raw extraction confusion
**What goes wrong:** Test writes `{"nodes": [...], "edges": [...]}` directly to `elicitation.json` and expects `load_elicitation_sidecar` to return it. It returns `None` because the loader expects `{"version": 1, "extraction": {...}, "meta": {...}}` and reads `.get("extraction")`.
**Why it happens:** `save_elicitation_sidecar` wraps the extraction in a versioned envelope (`graphify/elicit.py:215-265`); tests bypassing the helper must replicate the envelope.
**How to avoid:** Use `save_elicitation_sidecar(adir, extraction, force=True)` to author fixtures. For malformed-JSON tests, write raw bytes (e.g. `b"{not json"`) and assert the loader emits the `[graphify] elicitation sidecar invalid JSON` warning + returns `None`.
**Warning signs:** Test writes JSON and gets back `None` from `load_elicitation_sidecar`.

### Pitfall 4: MCP tool stub not invoking the real handler
**What goes wrong:** Test imports `_handlers` from `serve.py` to call `_tool_import_harness({})` directly, but `_tool_import_harness` is defined inside a closure that captures `_out_dir` and `validate_graph_path`. Test setup is non-trivial.
**Why it happens:** `serve.py`'s tool registration is closure-based for stateful path resolution.
**How to avoid:** Pattern from `tests/test_mcp_harness_io.py:9-29` — assert *registration* and *behavior* via the same setup function. For HARN-02 MCP guard, follow the existing test layout (mock or build the closure via the same factory) and call the handler with `{"path": ""}` to assert it returns `{"status": "error", ...}` (the existing behavior — `validate_graph_path("")` raises and is caught).
**Warning signs:** Test tries to import `_tool_import_harness` directly.

### Pitfall 5: HARN-01 canonical-mapping doc drift
**What goes wrong:** Prose in `docs/ELICITATION.md` says interchange schema id is `"graphify.harness.interchange/v1"` but a future bump to `/v2` makes the doc stale silently.
**How to avoid:** Add a lock-in test asserting the *constant* matches the *doc*: `assert INTERCHANGE_SCHEMA_ID in (Path("docs/ELICITATION.md").read_text())`. Cheap and self-healing.
**Warning signs:** None until a bump happens.

## Code Examples

### ELIC-01: node-id collision (elicitation wins, confidence preserved)
```python
# Pattern source: tests/test_elicit.py:102-124
def test_sidecar_node_id_collision_elicitation_wins(tmp_path):
    adir = tmp_path / "art"
    elic = {
        "nodes": [{"id": "shared", "label": "from elicit",
                   "file_type": "rationale", "source_file": ""}],
        "edges": [],
    }
    save_elicitation_sidecar(adir, elic, force=True)
    base = {"nodes": [{"id": "shared", "label": "from code",
                       "file_type": "code", "source_file": "x.py"}], "edges": []}
    seq = merge_elicitation_into_build_inputs([base], adir)
    G = build(seq)
    n = G.nodes["shared"]
    assert n["label"] == "from elicit"          # elicitation overwrote
    assert n["file_type"] == "rationale"
```

### ELIC-01: edge with conflicting relation
```python
def test_sidecar_edge_conflicting_relation_last_wins(tmp_path):
    adir = tmp_path / "art"
    base = {
        "nodes": [
            {"id": "a", "label": "A", "file_type": "code", "source_file": "f.py"},
            {"id": "b", "label": "B", "file_type": "code", "source_file": "f.py"},
        ],
        "edges": [{"source": "a", "target": "b", "relation": "calls",
                   "confidence": "EXTRACTED", "source_file": "f.py"}],
    }
    elic = {
        "nodes": [
            {"id": "a", "label": "A", "file_type": "rationale", "source_file": ""},
            {"id": "b", "label": "B", "file_type": "rationale", "source_file": ""},
        ],
        "edges": [{"source": "a", "target": "b", "relation": "depends_on",
                   "confidence": "INFERRED", "source_file": ""}],
    }
    save_elicitation_sidecar(adir, elic, force=True)
    G = build(merge_elicitation_into_build_inputs([base], adir))
    # Undirected Graph; (a,b) is one edge — last write wins on attrs.
    assert G.edges["a", "b"]["relation"] == "depends_on"
    assert G.edges["a", "b"]["confidence"] == "INFERRED"
```

### ELIC-01: malformed sidecar fallback
```python
def test_malformed_sidecar_loader_returns_none(tmp_path, capsys):
    adir = tmp_path / "art"
    adir.mkdir()
    (adir / "elicitation.json").write_bytes(b"{this is not json")
    assert load_elicitation_sidecar(adir) is None
    err = capsys.readouterr().err
    assert "[graphify] elicitation sidecar invalid JSON" in err
```

### ELIC-01: edge referencing absent node (graph stays sane)
```python
def test_sidecar_edge_referencing_absent_node(tmp_path):
    adir = tmp_path / "art"
    elic = {
        "nodes": [{"id": "x", "label": "X", "file_type": "rationale",
                   "source_file": ""}],
        "edges": [{"source": "x", "target": "ghost", "relation": "refs",
                   "confidence": "AMBIGUOUS", "source_file": ""}],
    }
    # validate_extraction allows dangling edges (matches prod behavior:
    # "dangling edges are expected for stdlib imports").
    save_elicitation_sidecar(adir, elic, force=True)
    G = build(merge_elicitation_into_build_inputs([{"nodes":[],"edges":[]}], adir))
    # NetworkX add_edge auto-creates the missing endpoint as a bare node.
    assert "ghost" in G.nodes
```

### HARN-01: schema-id constant lock-in + doc parity
```python
def test_interchange_schema_id_locked_and_documented():
    from graphify.harness_interchange import INTERCHANGE_SCHEMA_ID
    assert INTERCHANGE_SCHEMA_ID == "graphify.harness.interchange/v1"
    doc = pathlib.Path("docs/ELICITATION.md").read_text(encoding="utf-8")
    assert INTERCHANGE_SCHEMA_ID in doc
```

### HARN-02: MCP requires explicit path
```python
def test_mcp_import_harness_refuses_empty_path(tmp_path):
    # Setup follows tests/test_mcp_harness_io.py:9 pattern
    handlers = _build_serve_handlers(out_dir=tmp_path / "graphify-out", ...)
    result = json.loads(handlers["import_harness"]({}))
    assert result["status"] == "error"
    assert "path" in result["error"].lower()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 39: elicitation sidecar merge by ad-hoc kwarg | `build(elicitation=...)` parameter + `merge_elicitation_into_build_inputs` helper | v1.9 (Phase 39) | ELIC-01 tests target the helper, not the kwarg directly. |
| Phase 40: harness import as research/spike | Shipped CLI + MCP surface with size + injection caps | v1.9 (Phase 40) | Phase 57 only adds *guards*; underlying surface is frozen. |
| Phase 28: vault detection via parent walking | Strict CWD-only `is_obsidian_vault()` | v1.0/Phase 28 (D-04) | Vault-output guard reuses this exact predicate. |

**Deprecated/outdated:** None applicable to this phase.

## Runtime State Inventory

> Phase 57 is greenfield-tests + docs. No rename, refactor, or migration.

**N/A — section omitted.**

## Environment Availability

> Phase is pure code/config (test additions + docs edit) — no external dependencies probed.

**N/A — section omitted.**

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project default; see `pyproject.toml` `[all]` extra) |
| Config file | none top-level; `tests/conftest.py` exists for shared fixtures |
| Quick run command | `pytest tests/test_elicit.py tests/test_harness_import.py tests/test_mcp_harness_io.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ELIC-01 | Sidecar node-id collision: elicitation wins | unit | `pytest tests/test_elicit.py::test_sidecar_node_id_collision_elicitation_wins -x` | ❌ Wave 0 (extend existing file) |
| ELIC-01 | Sidecar edge with conflicting relation: last-wins | unit | `pytest tests/test_elicit.py::test_sidecar_edge_conflicting_relation_last_wins -x` | ❌ Wave 0 |
| ELIC-01 | Malformed sidecar JSON: loader returns None + stderr warning | unit | `pytest tests/test_elicit.py::test_malformed_sidecar_loader_returns_none -x` | ❌ Wave 0 |
| ELIC-01 | Sidecar edge with missing required fields: validation error | unit | `pytest tests/test_elicit.py::test_sidecar_missing_required_fields_rejected -x` | ❌ Wave 0 |
| ELIC-01 | Sidecar edge referencing absent node: graph stays sane (dangling edge OK) | unit | `pytest tests/test_elicit.py::test_sidecar_edge_referencing_absent_node -x` | ❌ Wave 0 |
| ELIC-01 | Confidence value preservation across merge | unit | `pytest tests/test_elicit.py::test_sidecar_preserves_confidence -x` | ❌ Wave 0 |
| ELIC-02 | `docs/ELICITATION.md` contains `## Trust Boundaries` section | unit (file content) | `pytest tests/test_elicit.py::test_doc_has_trust_boundaries_section -x` | ❌ Wave 0 |
| ELIC-02 | `docs/ELICITATION.md` contains `## Milestone Non-Goals (v1.11)` section | unit (file content) | `pytest tests/test_elicit.py::test_doc_has_milestone_non_goals_section -x` | ❌ Wave 0 |
| HARN-01 | `INTERCHANGE_SCHEMA_ID == "graphify.harness.interchange/v1"` constant locked | unit | `pytest tests/test_harness_interchange.py::test_interchange_schema_id_locked -x` | ❌ Wave 0 |
| HARN-01 | Doc contains canonical mapping table referencing schema id | unit (file content) | `pytest tests/test_elicit.py::test_doc_has_canonical_mapping -x` | ❌ Wave 0 |
| HARN-01 | Schema id round-trips through `_parse_interchange_v1` (envelope w/ id passes; w/o id rejected) | unit | existing `tests/test_harness_import.py::test_import_rejects_bad_schema` already passes | ✅ extend |
| HARN-02 | CLI refuses `--output` resolving inside vault (no confirmation flag) | integration (subprocess) | `pytest tests/test_harness_import.py::test_import_refuses_vault_rooted_output -x` | ❌ Wave 0 |
| HARN-02 | CLI accepts vault `--output` with `--allow-vault-write` | integration (subprocess) | `pytest tests/test_harness_import.py::test_import_accepts_vault_with_explicit_flag -x` | ❌ Wave 0 |
| HARN-02 | Static AST: `import_harness_*` referenced only by allowlisted files | unit (AST scan) | `pytest tests/test_harness_import.py::test_no_auto_invocation_of_import_harness -x` | ❌ Wave 0 |
| HARN-02 | MCP tool refuses missing/empty `path` argument | unit | `pytest tests/test_mcp_harness_io.py::test_mcp_import_harness_refuses_empty_path -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_elicit.py tests/test_harness_import.py tests/test_mcp_harness_io.py -q` (≈3-5s)
- **Per wave merge:** `pytest tests/ -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Extend `tests/test_elicit.py` — add 6 ELIC-01 tests + 2 ELIC-02 doc-content tests + 1 HARN-01 doc-content test
- [ ] Extend `tests/test_harness_import.py` — add 3 HARN-02 tests (vault-refusal CLI, vault-with-flag CLI, AST auto-invocation guard)
- [ ] Extend `tests/test_harness_interchange.py` — add 1 HARN-01 schema-id constant lock
- [ ] Extend `tests/test_mcp_harness_io.py` — add 1 HARN-02 MCP empty-path test
- No new fixtures required; existing `tests/fixtures/harness/graph.json` powers HARN-02 CLI tests
- No framework install needed

## TDD Eligibility

Per project config (`workflow.tdd_mode: true`):

| Deliverable | TDD-eligible? | Rationale |
|-------------|---------------|-----------|
| ELIC-01 test additions (6 scenarios) | **N/A — these ARE the tests** | The deliverable IS test code; "TDD" reduces to "write test → assert it fails → no production code change needed because the contract already holds → assert green." Useful as a sanity loop: write each test, run it, confirm pass (or red→green if it surfaces a real bug). |
| HARN-02 vault-output refusal CLI behavior | **TDD-eligible** | New CLI behavior (refusal + `--allow-vault-write` flag). Write `test_import_refuses_vault_rooted_output` first → red → add CLI guard in `__main__.py:2510-2585` → green. |
| HARN-02 `--allow-vault-write` flag implementation | **TDD-eligible** | New argparse arg + behavior. Tests drive design. |
| HARN-02 AST auto-invocation guard | **N/A — meta-test, no production code** | Pure introspection; deliverable IS the test. |
| HARN-02 MCP empty-path refusal | **Standard execute** | Behavior already exists (`validate_graph_path("")` raises and is caught). Test is a regression lock, not driving new code. |
| HARN-01 schema-id constant lock + doc parity | **Standard execute** | Tests assert existing constants and doc contents. Doc-edit drives test, not the other way around. |
| ELIC-02 `docs/ELICITATION.md` updates | **Not TDD** | Documentation; "tests" are file-content existence checks (cheap regression locks, not behavior tests). |

**TDD-eligible items: HARN-02 vault-output refusal + `--allow-vault-write` flag.** Plan should call out this red→green→refactor loop explicitly. Everything else is regression-lock or doc-edit.

## Project Constraints (from CLAUDE.md)

The planner MUST verify each task respects these:

- **Python 3.10+** — type hints use `dict | None`, `str | None`, `from __future__ import annotations` first import.
- **No new required dependencies** — stdlib only for new code; tests use existing pytest.
- **Pure unit tests** — no network, no filesystem side effects outside `tmp_path`. Subprocess CLI tests must `monkeypatch.chdir(tmp_path)`.
- **`from __future__ import annotations`** — first import in every new test module / extended file (`tests/test_elicit.py` already has it; verify on additions).
- **Domain-specific exceptions with clear messages** — `--allow-vault-write` refusal raises `SystemExit(2)` and prints `"[graphify] refusing to write harness import under vault root ...; pass --allow-vault-write to override"` on stderr.
- **`[graphify]` stderr prefix** — for warnings and rejections (already convention in `output.py:_refuse` and `harness_import.py`).
- **Tests on Python 3.10 and 3.12** (CI matrix) — avoid 3.11+/3.12-only syntax.
- **PyPI package name `graphifyy`; CLI/imports `graphify`** — relevant only if version metadata is touched (unlikely this phase).
- **Backward compatible** — no changes to `import_harness_path` signature; `--allow-vault-write` is additive.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `--allow-vault-write` flag name is acceptable to the user (D-marked as Claude's discretion). | Standard Stack — Alternatives | If rejected, planner picks an alternate name; no code-shape impact. |
| A2 | "Vault-rooted output" means an `--output` resolving (post-`_resolve_cli_paths`) to a directory containing `.obsidian/` (i.e., `is_obsidian_vault()` returns true on the resolved root or any ancestor up to a sensible bound). | HARN-02 Guarantee 1 | If the user means a different definition (e.g., any path inside a configured vault list, not just `.obsidian/`-bearing), the guard predicate must change. Recommend confirming during plan-discuss. |
| A3 | Refusal raises `SystemExit(2)` (matches existing `import-harness` failure conventions in `__main__.py:2557`) rather than `SystemExit(1)`. | Project Constraints | Different exit code if user prefers; trivial to change. |
| A4 | `validate_extraction` already rejects sidecar edges with missing required fields, so the "missing required fields" failure mode (D-03) surfaces as a `ValueError` from `save_elicitation_sidecar`, not a silent skip. | ELIC-01 test design | If `validate_extraction` is more permissive than expected, the test asserts the wrong error type. Verify by running `validate_extraction({"nodes":[],"edges":[{"source":"a"}]})` once during Wave 0. |
| A5 | The CLI smoke test `test_cli_import_harness_smoke` pattern (subprocess + `monkeypatch.chdir`) works under CI's Python 3.10/3.12 matrix without additional fixture wiring. | Pattern 2 | Already used by `tests/test_harness_import.py:82` — high confidence. |

## Open Questions

1. **What does the user expect when `--output` is *outside* a vault but `--allow-vault-write` is passed?**
   - What we know: Flag is additive — without it, refuse vault-rooted; with it, allow.
   - What's unclear: Should the flag be ignored (no-op) when output is already non-vault, or should it warn?
   - Recommendation: Silent no-op outside vault (zero-friction); warn only when output IS vault-rooted, telling user the flag has activated. Matches "fail loudly with actionable messages" precedent.

2. **Does `validate_extraction` allow dangling edges for the "edge referencing absent node" test?**
   - What we know: `build.py` docstring at line ~310 says "dangling edges are expected for stdlib imports" — strong signal yes.
   - What's unclear: Whether the *sidecar* path (which goes through `validate_extraction` in `save_elicitation_sidecar:240`) treats it identically.
   - Recommendation: Verify in Wave 0 by writing the test; if `validate_extraction` rejects, add a node-existence test instead and document the deviation.

3. **Should the canonical-mapping prose live in `## Trust Boundaries` or its own section?**
   - What we know: D-07 says "in the trust-boundaries section."
   - What's unclear: Strict subsection or sibling H2?
   - Recommendation: Sibling H2 `## Canonical Harness Interchange (v1) Mapping` placed *between* `## Trust Boundaries` and `## Milestone Non-Goals (v1.11)`. Easier to link to from tests.

## Security Domain

> `security_enforcement` is not explicitly disabled in `.planning/config.json` — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no user auth surface |
| V3 Session Management | no | N/A |
| V4 Access Control | yes | Path-confinement: `validate_graph_path(path, base=...)` from `graphify/security.py`. The HARN-02 vault-output guard is an access-control control: it prevents a malicious or accidental `--output` from writing reconstructed extractions into a user's vault notes directory. |
| V5 Input Validation | yes | `validate_extraction` (schema enforcement), `_sanitize_extraction` (label/edge sanitization), `guard_harness_injection_patterns` (Phase 40 — referenced, not re-tested). |
| V6 Cryptography | no | No crypto surface |
| V12 File and Resource | yes | `MAX_HARNESS_IMPORT_BYTES` size cap, `_MAX_SIDECAR_BYTES` for sidecar JSON (out of scope per D-09; reference only). |

### Known Threat Patterns for graphify (Python CLI)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in `--output` to write inside Obsidian vault | Tampering | `is_obsidian_vault()` check on resolved `artifacts_dir`; refuse unless `--allow-vault-write` (HARN-02). |
| Auto-invocation of import path from another command (privilege creep) | Elevation of Privilege | AST-based call-site allowlist test (HARN-02 guarantee 2). |
| MCP tool invoked with empty/missing `path` triggering default discovery | Information Disclosure | Explicit `arguments["path"]` requirement; empty string fails `validate_graph_path` (HARN-02 guarantee 3). |
| Malformed sidecar JSON triggering uncaught exception during `build()` | Denial of Service | `load_elicitation_sidecar` catches `JSONDecodeError`, prints `[graphify]` warning, returns `None` — pipeline continues. |
| Prompt injection in sidecar / harness free-text reaching downstream LLM | Tampering | `sanitize_harness_text` + `guard_harness_injection_patterns` (Phase 40 — out of scope per D-09). |

## Sources

### Primary (HIGH confidence) — read in this session
- `.planning/phases/57-elicitation-harness-increment/57-CONTEXT.md` (132 lines, full)
- `.planning/REQUIREMENTS.md` (71 lines, full)
- `.planning/ROADMAP.md:623-659` (Phase 57 success criteria)
- `graphify/build.py:281-307` (`build()` and elicitation merge contract)
- `graphify/elicit.py:39-313` (sidecar lifecycle: save, load, merge, helpers)
- `graphify/harness_import.py:1-293` (full module — import path policy, sniffer, sanitizer)
- `graphify/harness_interchange.py:1-80` (schema id constant, `graph_data_to_extraction`)
- `graphify/output.py:40-200` (`ResolvedOutput`, `is_obsidian_vault`, `resolve_execution_paths`, `resolve_output`)
- `graphify/__main__.py:2510-2585` (`import-harness` CLI argparse + path resolution)
- `graphify/serve.py:3720-3795` (MCP `_tool_import_harness` + handler registration)
- `graphify/security.py` line index (`MAX_HARNESS_IMPORT_BYTES`, `validate_graph_path`, `sanitize_harness_text`, `guard_harness_injection_patterns`)
- `tests/test_elicit.py:102-148` (existing sidecar build merge patterns)
- `tests/test_harness_import.py:17-122` (existing import + CLI smoke patterns)
- `tests/test_mcp_harness_io.py:9-29` (existing MCP handler test layout)
- `docs/ELICITATION.md` (52 lines — file ELIC-02 will edit in place)
- `CLAUDE.md` (project guidelines, build/test commands, conventions)

### Secondary (MEDIUM confidence)
- None — all claims grounded in directly-read code.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pytest is the verified project framework; no new deps required.
- Architecture: HIGH — sidecar merge code path and import surface read end-to-end in this session.
- Pitfalls: HIGH — pitfalls 1-4 grounded in observed code; pitfall 5 is preventive.
- Security domain: HIGH — directly mapped from `security.py` and existing Phase 40 controls.

**Research date:** 2026-05-03
**Valid until:** 2026-06-02 (30 days; lock-down phase against frozen surfaces — drift risk low)
