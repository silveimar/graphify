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


def test_security_md_phase40_harness_traceability() -> None:
    """SEC-04 / 40-04: SECURITY.md retains harness I/O subsection + requirement IDs."""
    sec = Path(__file__).resolve().parents[1] / "SECURITY.md"
    text = sec.read_text(encoding="utf-8")
    assert "Harness memory import/export" in text
    assert "PORT-01" in text
    assert "SEC-01" in text or "SEC-04" in text
