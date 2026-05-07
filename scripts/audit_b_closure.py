"""audit_b_closure.py — Phase 68 / AUDIT-01 closure script.

Re-runs the 5 retroactive Nyquist tests cited in
.planning/milestones/v1.12-VALIDATION.md and proves the citation
list and the @pytest.mark.audit_v112 marker set agree.

Exit codes (per CONTEXT.md D-01):
    0 = all marked tests pass
    1 = test failure
    2 = citation/marker drift
"""
from __future__ import annotations

import re
import subprocess
import sys

CITATION_LIST: list[str] = [
    "tests/test_vault_cwd.py::test_refusal_exit_code_and_format",       # Phase 59,   SHA 5eb2c17
    "tests/test_version_sync.py::test_heal_happy_path_silent",          # Phase 59.1, SHA 671045f
    "tests/test_e2e_integration.py::test_e2e_elicit_then_update_vault", # Phase 60,   SHA b6378b9
    "tests/test_cluster.py::test_cluster_is_deterministic_across_runs", # Phase 60.1, SHA a96435a
    "tests/test_harness_import.py::test_import_refuses_vault_rooted_output",  # Phase 61, SHA 2413f18
]


def collect_marked() -> list[str]:
    """Return list of pytest node IDs that carry @pytest.mark.audit_v112."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "audit_v112"],
        capture_output=True,
        text=True,
        check=False,
    )
    # pytest -q --collect-only emits one node ID per line, then a summary line.
    # Filter to lines that look like 'path/to/test.py::test_name'.
    node_re = re.compile(r"^[^:\s]+\.py::[A-Za-z_][A-Za-z0-9_]*$")
    return [ln.strip() for ln in result.stdout.splitlines() if node_re.match(ln.strip())]


def main() -> int:
    collected = collect_marked()
    if set(collected) != set(CITATION_LIST):
        missing = set(CITATION_LIST) - set(collected)
        extra = set(collected) - set(CITATION_LIST)
        print("[audit_b] Citation/marker drift detected", file=sys.stderr)
        if missing:
            print(f"  hint: missing markers on: {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"  hint: unexpected markers on: {sorted(extra)}", file=sys.stderr)
        return 2
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "audit_v112", "-v"],
        check=False,
    )
    return 1 if result.returncode != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
