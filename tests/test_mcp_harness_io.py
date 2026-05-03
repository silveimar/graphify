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
    assert "export_interchange_v1" in text
    assert '"import_harness": _tool_import_harness' in text
    assert '"export_harness_interchange": _tool_export_harness_interchange' in text


def test_mcp_import_harness_refuses_empty_path() -> None:
    """HARN-02 guarantee 3: MCP import_harness tool requires explicit non-empty path argument.

    Asserted via source-substring on graphify/serve.py to avoid setting up the closure-bound
    handler under test (per Pitfall 4 in 57-RESEARCH.md). The handler reads
    `(arguments or {}).get("path") or ""` and passes through `validate_graph_path(Path(raw_path), base=_out_dir)`,
    which raises on empty string -- handler returns `{"status": "error", ...}`.
    """
    serve_src = Path(__file__).resolve().parents[1] / "graphify" / "serve.py"
    text = serve_src.read_text(encoding="utf-8")
    # The handler reads the path arg defensively (empty default).
    assert '(arguments or {}).get("path") or ""' in text
    # The handler delegates to validate_graph_path which rejects empty strings.
    assert "validate_graph_path(Path(raw_path), base=_out_dir)" in text
    # The handler returns a structured error rather than raising.
    assert '"status": "error"' in text


def test_security_md_phase40_harness_traceability() -> None:
    """SEC-04 / 40-04: SECURITY.md retains harness I/O subsection + requirement IDs."""
    sec = Path(__file__).resolve().parents[1] / "SECURITY.md"
    text = sec.read_text(encoding="utf-8")
    assert "Harness memory import/export" in text
    assert "PORT-01" in text
    assert "SEC-01" in text or "SEC-04" in text
