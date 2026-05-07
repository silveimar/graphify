"""Unit tests for scripts/audit_b_closure.py — exit code matrix (0/1/2) + integration smoke.

Import pattern: importlib.util.spec_from_file_location to avoid sys.path mutation.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


def _load_closure() -> ModuleType:
    """Load scripts/audit_b_closure.py as a module without installing it."""
    script_path = Path(__file__).parent.parent / "scripts" / "audit_b_closure.py"
    spec = importlib.util.spec_from_file_location("audit_b_closure", script_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_drift_missing_marker() -> None:
    """Exit 2 when collected set is a strict subset of CITATION_LIST (marker missing)."""
    mod = _load_closure()
    # Return only 4 of the 5 entries — simulates one test losing its decorator
    subset = mod.CITATION_LIST[:-1]
    with patch.object(mod, "collect_marked", return_value=subset):
        code = mod.main()
    assert code == 2, f"expected 2 (drift), got {code}"


def test_drift_extra_marker() -> None:
    """Exit 2 when collected set has an entry not in CITATION_LIST (spurious marker)."""
    mod = _load_closure()
    extra = mod.CITATION_LIST + ["tests/test_fake.py::test_fake_extra"]
    with patch.object(mod, "collect_marked", return_value=extra):
        code = mod.main()
    assert code == 2, f"expected 2 (drift), got {code}"


def test_pass_path() -> None:
    """Exit 0 when collected set equals CITATION_LIST and pytest returns 0."""
    mod = _load_closure()
    run_result = MagicMock()
    run_result.returncode = 0
    with patch.object(mod, "collect_marked", return_value=list(mod.CITATION_LIST)):
        with patch.object(mod.subprocess, "run", return_value=run_result):
            code = mod.main()
    assert code == 0, f"expected 0 (pass), got {code}"


def test_failure_path() -> None:
    """Exit 1 when collected set equals CITATION_LIST but pytest run returns non-zero."""
    mod = _load_closure()
    run_result = MagicMock()
    run_result.returncode = 1
    with patch.object(mod, "collect_marked", return_value=list(mod.CITATION_LIST)):
        with patch.object(mod.subprocess, "run", return_value=run_result):
            code = mod.main()
    assert code == 1, f"expected 1 (test failure), got {code}"


def test_integration_smoke() -> None:
    """Integration: run the real script as a subprocess — must exit 0 from repo root."""
    script = Path(__file__).parent.parent / "scripts" / "audit_b_closure.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(Path(__file__).parent.parent),
        check=False,
    )
    assert result.returncode == 0, (
        f"audit_b_closure.py exited {result.returncode} (expected 0)"
    )
