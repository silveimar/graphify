# Phase 57: Elicitation & harness increment - Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 6 (4 tests/docs + 2 possible source edits)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/test_elicit.py` (extend) | test (unit) | request-response (pure) | `tests/test_elicit.py:102-148` (existing `test_build_includes_elicitation_last_wins`) | exact (same module) |
| `tests/test_harness_import.py` (extend) | test (unit + subprocess CLI smoke + AST scan) | subprocess + file-I/O | `tests/test_harness_import.py:82-117` (`test_cli_import_harness_smoke`) | exact (same module) |
| `tests/test_mcp_harness_io.py` (extend) | test (unit, MCP closure) | request-response | `tests/test_mcp_harness_io.py:9-29` (registry + handler reference checks) | exact (same module) |
| `docs/ELICITATION.md` (in-place edit) | documentation | docs | `docs/ELICITATION.md` existing sections (`## Where artifacts land`, `## Non-goals (other phases)`) | exact (same file) |
| `graphify/__main__.py` (extend `import-harness` block) | CLI (argparse) | request-response | `graphify/__main__.py:2512-2585` (existing `import-harness` cmd) | exact (same block) |
| `graphify/harness_import.py` (optional vault-output guard hook) | library (path policy) | request-response | `graphify/harness_import.py:216-268` (`import_harness_path` + `validate_graph_path`) | exact (same function) |

## Pattern Assignments

### `tests/test_elicit.py` (test, unit, sidecar collision scenarios — ELIC-01 + ELIC-02 doc-content checks)

**Analog:** `tests/test_elicit.py:1-148` (extend in place — file already established)

**Imports pattern** (lines 1-18):
```python
"""Tests for tacit-to-explicit elicitation (Phase 39)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.build import build
from graphify.elicit import (
    ELICITATION_SIDECAR_FILENAME,
    build_extraction_from_session,
    load_elicitation_sidecar,
    merge_elicitation_into_build_inputs,
    run_scripted_elicitation,
    save_elicitation_sidecar,
)
from graphify.validate import validate_extraction
```

**Core pattern — sidecar-merge build assertion** (lines 102-124):
```python
def test_build_includes_elicitation_last_wins(tmp_path: Path) -> None:
    """Sidecar merges after base extraction; duplicate node id uses elicitation."""
    adir = tmp_path / "art"
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext_elic = build_extraction_from_session(session)
    save_elicitation_sidecar(adir, ext_elic, force=True)

    base_like = {
        "nodes": [
            {"id": "elicitation_hub", "label": "from code",
             "file_type": "code", "source_file": "x.py"}
        ],
        "edges": [],
    }
    seq = merge_elicitation_into_build_inputs([base_like], adir)
    G = build(seq)
    hub = G.nodes.get("elicitation_hub")
    assert hub is not None
    assert hub.get("file_type") == "rationale"
```

**Path-escape rejection pattern** (lines 76-82) — reuse for malformed-sidecar tests:
```python
def test_save_rejects_path_escape(tmp_path: Path) -> None:
    adir = tmp_path / "safe"
    adir.mkdir()
    (tmp_path / "outside").mkdir()
    session = run_scripted_elicitation(_sample_answers(), auto_confirm=True)
    ext = build_extraction_from_session(session)
    with pytest.raises(ValueError, match="escapes"):
        save_elicitation_sidecar(adir, ext, filename="../outside/elicitation.json")
```

**Doc-content assertion pattern** (mirror `tests/test_mcp_harness_io.py:24-30` `test_security_md_phase40_harness_traceability`):
```python
def test_doc_has_trust_boundaries_section() -> None:
    doc = (Path(__file__).resolve().parents[1] / "docs" / "ELICITATION.md").read_text(encoding="utf-8")
    assert "## Trust Boundaries" in doc
    assert "## Milestone Non-Goals (v1.11)" in doc
```

---

### `tests/test_harness_import.py` (test, unit + subprocess + AST scan — HARN-02)

**Analog:** `tests/test_harness_import.py:82-117` (existing CLI smoke test)

**Imports pattern** (lines 1-15):
```python
"""Phase 40 — harness import pipeline (PORT-03/05, SEC-01)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from graphify.harness_import import import_harness_bytes, import_harness_path
from graphify.harness_interchange import INTERCHANGE_SCHEMA_ID, export_interchange_v1
from graphify.security import MAX_HARNESS_IMPORT_BYTES, guard_harness_injection_patterns
from graphify.validate import validate_extraction
```

**CLI subprocess smoke pattern** (lines 82-117) — adapt for vault-rooted-output guard:
```python
def test_cli_import_harness_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "graphify-out"
    root.mkdir()
    harness = root / "harness"
    harness.mkdir()
    env = export_interchange_v1(
        json.loads(
            (Path(__file__).parent / "fixtures" / "harness" / "graph.json").read_text(encoding="utf-8")
        ),
        out_path=None,
    )
    src = harness / "harness_memory.v1.json"
    src.write_text(json.dumps(env), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rc = subprocess.run(
        [sys.executable, "-m", "graphify", "import-harness", str(src), "--format", "json"],
        capture_output=True, text=True, timeout=60,
    )
    assert rc.returncode == 0, rc.stderr
    out_j = root / "harness_import.json"
    assert out_j.exists()
    loaded = json.loads(out_j.read_text(encoding="utf-8"))
    assert validate_extraction(loaded) == []
```

**Adaptation for HARN-02 vault-output refusal:** create a `(vault / ".obsidian").mkdir(parents=True)` to make a vault, point `--output` at it, and assert `rc.returncode != 0` and `"vault" in rc.stderr.lower()`. Then a parallel test passing `--allow-vault-write` and asserting `rc.returncode == 0`.

**ValueError-match pattern from `test_import_oversized_file`** (lines 41-47):
```python
def test_import_oversized_file(tmp_path: Path) -> None:
    root = tmp_path / "graphify-out"
    root.mkdir()
    p = root / "big.json"
    p.write_bytes(b"x" * (MAX_HARNESS_IMPORT_BYTES + 2))
    with pytest.raises(ValueError, match="max size"):
        import_harness_path(p, format="json", artifacts_root=root)
```

**AST call-site allowlist pattern (new)** — analog `tests/test_mcp_harness_io.py:15-21` (text-grep over `serve.py`); upgrade to AST per RESEARCH §"Anti-Patterns to Avoid" (avoids docstring false-positives):
```python
import ast, pathlib
def test_no_auto_invocation_of_import_harness() -> None:
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

---

### `tests/test_mcp_harness_io.py` (test, MCP explicit-path-required — HARN-02 #3)

**Analog:** `tests/test_mcp_harness_io.py:1-30` (entire existing file)

**Imports pattern + handler reference style** (lines 1-21):
```python
"""Phase 40 — MCP harness tools registry parity (MANIFEST-05, SEC-03)."""
from __future__ import annotations

from pathlib import Path

from graphify.mcp_tool_registry import tool_names_ordered


def test_mcp_registry_includes_harness_tools() -> None:
    names = tool_names_ordered()
    assert "import_harness" in names
    assert "export_harness_interchange" in names


def test_serve_handlers_reference_library_functions() -> None:
    serve_src = Path(__file__).resolve().parents[1] / "graphify" / "serve.py"
    text = serve_src.read_text(encoding="utf-8")
    assert "import_harness_path" in text
    assert '"import_harness": _tool_import_harness' in text
```

**Adaptation for empty-path refusal:** the actual `_tool_import_harness` lives inside a closure (`graphify/serve.py:3724-3745`); per RESEARCH Pitfall 4 and §"HARN-02: MCP requires explicit path", drive the test through the same factory used for handler construction (or via a static-source assertion that the handler's first action is `validate_graph_path(Path(raw_path), base=_out_dir)` where `raw_path = (arguments or {}).get("path") or ""`). Concrete handler under test (`graphify/serve.py:3724-3745`):
```python
def _tool_import_harness(arguments: dict) -> str:
    """Phase 40: delegate harness import to graphify.harness_import (CLI parity, SEC-03)."""
    raw_path = (arguments or {}).get("path") or ""
    fmt = str((arguments or {}).get("format") or "auto")
    strict = bool((arguments or {}).get("strict", False))
    try:
        resolved = validate_graph_path(Path(raw_path), base=_out_dir)
    except (ValueError, FileNotFoundError, OSError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)
```
Empty `path` → `validate_graph_path(Path(""), base=_out_dir)` raises → handler returns `{"status": "error", ...}`. Assert this branch by feeding `{}` and `{"path": ""}`.

---

### `docs/ELICITATION.md` (documentation, in-place edit — ELIC-02 + HARN-01 mapping)

**Analog:** `docs/ELICITATION.md` itself (52 lines today)

**Existing section heading style** (existing file):
```markdown
## Where artifacts land

Paths follow **`resolve_output()`** (see `graphify/output.py`): with a vault + profile,
artifacts typically resolve to the sibling **`graphify-out/`** next to the vault; without a
vault, **`./graphify-out`** under the working directory. Outputs include:

| Artifact | Location |
|----------|----------|
| Sidecar (merged by `build()`) | `<artifacts_dir>/elicitation.json` |
| Harness markdown (fast path) | `<artifacts_dir>/harness/claude-*.md` + `fidelity.json` |
```

**Non-goals section style** (existing) — replace/extend:
```markdown
## Non-goals (other phases)

- **Phase 40** — harness **import**, injection defenses, inverse import.
- **Phase 41** — **`--vault`** selector / multi-root UX productization.
```

**New sections to add** (sibling H2s, per RESEARCH Open Question #3 — between current "Where sidecar merge runs" and the existing "Non-goals" which becomes "Milestone Non-Goals (v1.11)"):
1. `## Trust Boundaries` — three subsections: where elicitation reads/writes; what `import-harness` will/won't do; LLM trust posture during `elicit`.
2. `## Canonical Harness Interchange (v1) Mapping` — prose mirror of `graphify.harness_interchange.graph_data_to_extraction` field mapping; references `INTERCHANGE_SCHEMA_ID = "graphify.harness.interchange/v1"`.
3. `## Milestone Non-Goals (v1.11)` — supersedes existing `## Non-goals (other phases)`.

**Token style:** existing doc uses backtick-bold for code identifiers (`**`graphify run`**`), single-row tables for artifact mappings, and stderr-warning prose. Match this voice.

---

### `graphify/__main__.py` (CLI, `--allow-vault-write` flag for `import-harness` — HARN-02 #1)

**Analog:** `graphify/__main__.py:2512-2589` (existing `import-harness` block)

**Argparse flag pattern** (lines 2520-2543):
```python
parser = _ap.ArgumentParser(prog="graphify import-harness")
parser.add_argument(
    "path",
    help="Harness file under graphify-out/ (interchange JSON or Claude markdown)",
)
parser.add_argument(
    "--format",
    default="auto",
    choices=["auto", "json", "claude"],
    help="Parser selector (default: sniff by extension/content)",
)
parser.add_argument(
    "--strict",
    action="store_true",
    help="Reject on high-confidence injection-pattern matches",
)
parser.add_argument(
    "--output",
    default=None,
    help="Override artifacts root (same precedence as graphify run / elicit)",
)
```

**Pattern to add** (mirror `--strict`):
```python
parser.add_argument(
    "--allow-vault-write",
    action="store_true",
    help="Permit --output to resolve under an Obsidian vault root (off by default; HARN-02).",
)
```

**Existing post-resolve guard pattern** (lines 2552-2563) — slot the vault check immediately after `_resolve_cli_paths`:
```python
resolved = _resolve_cli_paths(
    opts.output,
    global_explicit=g_vault_exp,
    global_list=g_vault_list,
    local_explicit=_lv_ih,
    local_list=_lv_ih2,
)
artifacts = resolved.artifacts_dir
artifacts.mkdir(parents=True, exist_ok=True)
```

**Refusal pattern** to insert before `artifacts.mkdir`:
```python
from graphify.output import is_obsidian_vault
if not opts.allow_vault_write and is_obsidian_vault(artifacts):
    print(
        f"[graphify] refusing to write harness import under vault root {artifacts}; "
        "pass --allow-vault-write to override",
        file=sys.stderr,
    )
    sys.exit(2)
```
Style cited from existing `_refuse` in `graphify/output.py:67-69` (`[graphify] ` prefix + actionable message + `SystemExit(1)`) and existing `import-harness` `sys.exit(2)` on `stdin/URL` rejection (`__main__.py:2546-2551`).

---

### `graphify/harness_import.py` (library — possible single-source-of-truth vault check)

**Analog:** `graphify/harness_import.py:216-268` (`import_harness_path`)

**Existing path-policy pattern** (lines 230-241):
```python
base = (
    Path(artifacts_root).resolve()
    if artifacts_root is not None
    else Path("graphify-out").resolve()
)
resolved = Path(path).resolve()
validate_graph_path(resolved, base=base)
```

**Decision (per CONTEXT.md "Integration Points"):** the vault-output guard is preferred at the CLI argparse layer (single call site, easier to thread `--allow-vault-write` through), NOT inside `import_harness_path` whose `artifacts_root` semantics already constrain *source-file* placement, not output. RESEARCH Pitfall 2 confirms: `import_harness_path` does not check vault-ness of its base, and shouldn't (separation of concerns). **Recommendation:** do not modify `harness_import.py` for HARN-02; keep the guard CLI-side. The MCP path already enforces explicit-path-required transitively (`validate_graph_path("")` raises).

---

## Shared Patterns

### Path confinement
**Source:** `graphify/security.py::validate_graph_path`
**Apply to:** All path-touching tests (already used by `import_harness_path`, `save_elicitation_sidecar`).
**Pattern:** raise `ValueError`/`OSError`; tests assert via `pytest.raises(ValueError, match="...")`.

### Vault detection (single source of truth)
**Source:** `graphify/output.py:67`
```python
def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only detection (D-04). No parent-walking."""
    return (path / ".obsidian").is_dir()
```
**Apply to:** Vault-output guard in `__main__.py`; vault test fixture setup `(tmp_path / ".obsidian").mkdir()`.

### Stderr-prefixed refusal
**Source:** `graphify/output.py:71-74` (`_refuse`)
```python
def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)
```
**Apply to:** Vault-output refusal in `__main__.py` (use `[graphify] ` prefix; existing `import-harness` block uses `sys.exit(2)` for argparse-class failures — match that exit code).

### `from __future__ import annotations` first
**Source:** every existing test module (`tests/test_elicit.py:2`, `tests/test_harness_import.py:2`, `tests/test_mcp_harness_io.py:2`)
**Apply to:** All edits — additions inside an existing module inherit the pragma; new top-level test functions don't need anything extra.

### CLI subprocess test driver
**Source:** `tests/test_harness_import.py:82-117`
**Pattern:** `monkeypatch.chdir(tmp_path)` → `subprocess.run([sys.executable, "-m", "graphify", ...], capture_output=True, text=True, timeout=60)` → assert `rc.returncode` and parse `rc.stderr`.
**Apply to:** Both HARN-02 vault-output tests (refusal + `--allow-vault-write` accept).

### Doc-content regression-lock test
**Source:** `tests/test_mcp_harness_io.py:24-30` (`test_security_md_phase40_harness_traceability`)
**Pattern:** `Path(__file__).resolve().parents[1] / "docs" / "ELICITATION.md"`, `read_text(encoding="utf-8")`, `assert "## Trust Boundaries" in text`.
**Apply to:** ELIC-02 + HARN-01 doc-section existence checks.

### MCP handler-source assertion (avoids closure setup)
**Source:** `tests/test_mcp_harness_io.py:15-21` (text-grep over `graphify/serve.py`)
**Pattern:** when handler is closure-bound, assert via source-file substring rather than wiring the closure. Equally valid alongside an explicit-path behavioral test if the closure factory is reachable.

---

## No Analog Found

None — every Phase 57 surface has a strong existing analog in the codebase. This is consistent with the phase intent (lock-down phase against frozen surfaces; no new abstractions).

## Metadata

**Analog search scope:**
- `tests/test_elicit.py`, `tests/test_harness_import.py`, `tests/test_mcp_harness_io.py`, `tests/test_harness_interchange.py`
- `graphify/__main__.py:2510-2585` (`import-harness` block), `graphify/harness_import.py` (full module), `graphify/serve.py:3720-3795`
- `graphify/output.py:40-200` (`ResolvedOutput`, `is_obsidian_vault`, `_refuse`)
- `docs/ELICITATION.md` (52 lines, full)

**Files scanned:** 8 source files + 4 test files + 1 doc

**Pattern extraction date:** 2026-05-03
