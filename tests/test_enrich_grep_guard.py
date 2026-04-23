"""Grep-CI whitelist guard (Phase 15 SC-5 enforcement).

This file codifies the v1.1 D-invariant: ``graph.json`` is the pipeline
artifact and may be written ONLY by a small, deliberate set of modules.
Every other module in ``graphify/`` is structurally forbidden from calling
``to_json`` / ``_write_graph_json``. Phase 15's enrichment layer must NEVER
mutate ``graph.json`` — overlay data belongs in ``enrichment.json`` only.

Whitelist:
  - build.py       — legitimate graph construction / persistence
  - __main__.py    — CLI dispatcher (delegates graph writes; commented refs to
                     the exporter are allowed here but no actual call-sites live here)
  - watch.py       — post-rebuild hook dispatched from ``__main__.py::watch``

Any other ``graphify/*.py`` file that contains ``to_json(`` on a non-import,
non-def, non-comment line fails CI. Mitigates T-15-02 (Pitfall 3 — graph.json
overwrite by future enrichment-layer code).
"""
from __future__ import annotations

import re
from pathlib import Path

_GRAPHIFY_DIR = Path(__file__).resolve().parent.parent / "graphify"

# Only these three files may contain a call to `to_json(` / `_write_graph_json`.
_ALLOWED_CALLERS = {"build.py", "__main__.py", "watch.py"}

# The module where `to_json` is DEFINED — excluded because the `def` line
# literally contains `to_json(` but is not a call-site.
_DEFINER = "export.py"

# Regex for a call-site (function invocation), not a definition.
# `\bto_json\s*\(` matches any line mentioning the token followed by `(`.
_CALL_PATTERN = re.compile(r"\bto_json\s*\(")
_WRITE_GRAPH_JSON_PATTERN = re.compile(r"\b_write_graph_json\s*\(")


def _is_definition(line: str) -> bool:
    """Skip `def to_json(...)` lines — those are definitions, not calls."""
    return bool(re.match(r"\s*(async\s+)?def\s+", line))


def _is_import(line: str) -> bool:
    """Skip `from X import to_json` / `import to_json` lines."""
    stripped = line.strip()
    return stripped.startswith(("from ", "import "))


def _is_comment(line: str) -> bool:
    """Skip lines that are entirely a comment."""
    return line.strip().startswith("#")


def _collect_call_offenders(pattern: re.Pattern[str]) -> list[str]:
    """Scan all graphify/*.py for call-sites matching ``pattern`` in non-allowed files."""
    offenders: list[str] = []
    for py_file in sorted(_GRAPHIFY_DIR.glob("*.py")):
        if py_file.name in _ALLOWED_CALLERS:
            continue
        if py_file.name == _DEFINER:
            # export.py defines to_json; skip definition line but still flag stray calls.
            src = py_file.read_text(encoding="utf-8")
            stray = [
                f"{py_file.name}:{i+1}: {ln.rstrip()}"
                for i, ln in enumerate(src.splitlines())
                if pattern.search(ln)
                and not _is_definition(ln)
                and not _is_import(ln)
                and not _is_comment(ln)
            ]
            if stray:
                offenders.extend(stray)
            continue
        src = py_file.read_text(encoding="utf-8")
        hits = [
            f"{py_file.name}:{i+1}: {ln.rstrip()}"
            for i, ln in enumerate(src.splitlines())
            if pattern.search(ln)
            and not _is_definition(ln)
            and not _is_import(ln)
            and not _is_comment(ln)
        ]
        if hits:
            offenders.extend(hits)
    return offenders


def test_to_json_caller_whitelist() -> None:
    """SC-5: only build.py, __main__.py, watch.py may CALL to_json()."""
    offenders = _collect_call_offenders(_CALL_PATTERN)
    assert not offenders, (
        "SC-5 violation — only build.py, __main__.py, watch.py may CALL to_json(). "
        f"Offenders:\n  " + "\n  ".join(offenders) + "\n\n"
        "If a new call-site is needed, update the whitelist AND get approval from "
        "the Phase 15 invariant-owner. graph.json is the pipeline artifact — "
        "overlay data belongs in enrichment.json only."
    )


def test_write_graph_json_caller_whitelist() -> None:
    """SC-5 companion: _write_graph_json calls are similarly whitelisted."""
    offenders = _collect_call_offenders(_WRITE_GRAPH_JSON_PATTERN)
    assert not offenders, (
        "SC-5 violation — only whitelisted files may call _write_graph_json(). "
        f"Offenders:\n  " + "\n  ".join(offenders)
    )


def test_enrich_py_never_imports_to_json() -> None:
    """enrich.py is structurally forbidden from referencing to_json at all."""
    src = (_GRAPHIFY_DIR / "enrich.py").read_text(encoding="utf-8")
    assert "to_json" not in src, (
        "enrich.py must NEVER reference to_json — graph.json is read-only to Phase 15. "
        "Overlay data goes to enrichment.json only."
    )


def test_enrich_py_never_writes_graph_json() -> None:
    """enrich.py must not contain any write-side mention of graph.json.

    enrich.py reads graph.json (existence check in run_enrichment); but it must
    NEVER write it. The regex below catches the common write patterns:
      - `(...).write_text(... graph.json ...)`
      - `os.replace(..., "graph.json")`
      - `_write_graph_json(...)`
    """
    src = (_GRAPHIFY_DIR / "enrich.py").read_text(encoding="utf-8")
    assert "_write_graph_json" not in src, (
        "enrich.py must not reference _write_graph_json at all."
    )
    write_patterns = [
        r"\.write_text\s*\([^)]*graph\.json",
        r"os\.replace\s*\([^,]*,[^)]*graph\.json",
        r"open\s*\([^)]*graph\.json[^)]*['\"]w",
    ]
    for pat in write_patterns:
        assert not re.search(pat, src), (
            f"enrich.py contains a graph.json write pattern (regex {pat!r}). "
            "Violates Phase 15 v1.1 D-invariant."
        )
