"""Phase 21 TMPL-06: grep-scope denylist for direct vault .md writes.

Enforces the invariant that the only sanctioned writer of vault ``.md``
files is ``graphify.merge.compute_merge_plan`` (via its companion writer
in ``graphify.merge``). Modules ``seed.py``, ``export.py``, and
``__main__.py`` must NOT call ``Path.write_text``, ``write_note_directly``,
or ``open(..., 'w')`` on ``.md`` targets except within
``Excalidraw/Templates/*.excalidraw.md`` context (Plan 21-02 allowance).

Also enforces the ``compress: false`` one-way door: the ``lzstring``
package must not be imported anywhere in ``graphify/``.
"""
from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_PATTERNS = [
    r"\.write_text\(",
    r"write_note_directly",
    r"open\(['\"][^'\"]*\.md['\"]\s*,\s*['\"]w",  # open('xxx.md', 'w')
]

SCANNED = ["graphify/seed.py", "graphify/export.py", "graphify/__main__.py"]

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_no_direct_md_writes_in_seed_export_main():
    """TMPL-06: no direct vault .md writes outside Excalidraw/Templates."""
    violations: list[str] = []
    for rel in SCANNED:
        src = (REPO_ROOT / rel).read_text(encoding="utf-8")
        lines = src.splitlines()
        for pat in FORBIDDEN_PATTERNS:
            for m in re.finditer(pat, src):
                line_no = src[: m.start()].count("\n") + 1
                line = lines[line_no - 1]
                # Allowance 1: Excalidraw/Templates/*.excalidraw.md writes
                # (Plan 21-02 sanctioned scope via graphify.excalidraw).
                if "Excalidraw/Templates" in line or "excalidraw.md" in line:
                    continue
                # Allowance 1b: graphify's own output directory (graphify-out/)
                # is not a user vault — reports like GRAPH_DELTA.md, REPORT.md
                # are graphify's own audit artifacts, not vault notes.
                window_full = "\n".join(
                    lines[max(0, line_no - 5) : min(len(lines), line_no + 1)]
                )
                if "graphify-out" in window_full or "GRAPH_DELTA" in window_full or "GRAPH_REPORT" in window_full:
                    continue
                # Allowance 2: write_text targeting non-.md extensions
                # (.json, .yaml, .html, etc.) is out of scope for TMPL-06.
                if pat == r"\.write_text\(":
                    # Look at the current line and the ~2 preceding lines to
                    # capture the target path expression that may span lines.
                    window = "\n".join(lines[max(0, line_no - 3) : line_no])
                    # Skip if the target is plainly a non-.md file
                    if not re.search(
                        r"\.md['\"]|\.md\s*\)|\.md\.tmp|\.md\b", window
                    ):
                        continue
                    # Skip explicit skill/agent/config .md installers
                    # (CLAUDE.md, AGENTS.md, GEMINI.md, etc. — NOT vault notes).
                    if re.search(
                        r"CLAUDE\.md|AGENTS\.md|GEMINI\.md|OPENCODE\.md|"
                        r"\.graphify_version|skill[_\-]?dst|skill_path|"
                        r"_SKILL_|_CURSOR_|_OPENCODE_|_AGENTS_|_GEMINI_|"
                        r"_ANTIGRAVITY_|claude_md|settings_path|hooks_path|"
                        r"rules_path|rule_path|wf_path|plugin_file|config_file|"
                        r"cleaned\b|_content\b",
                        window,
                    ):
                        continue
                violations.append(f"{rel}:{line_no}: {line.strip()}")
    assert not violations, (
        "Direct vault .md write detected. Route through "
        "graphify.merge.compute_merge_plan (vault notes) or "
        "graphify.excalidraw.write_stubs (Excalidraw/Templates/ only). "
        "Violations:\n" + "\n".join(violations)
    )


def test_no_lzstring_import_anywhere():
    """compress: false one-way door — no lzstring imports in graphify/."""
    offenders: list[str] = []
    for py in (REPO_ROOT / "graphify").rglob("*.py"):
        src = py.read_text(encoding="utf-8")
        if re.search(r"^\s*(?:from|import)\s+lzstring", src, re.M | re.I):
            offenders.append(str(py.relative_to(REPO_ROOT)))
    assert not offenders, (
        "lzstring import forbidden — compress: false one-way door. "
        "Offenders: " + ", ".join(offenders)
    )


def test_only_merge_exposes_compute_merge_plan():
    """Sanity: compute_merge_plan is the sanctioned vault .md writer."""
    from graphify.merge import compute_merge_plan

    assert callable(compute_merge_plan)
