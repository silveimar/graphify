"""Harness schema loader (HARNESS-02).

Bundled, declarative YAML schemas describe the SOUL/HEARTBEAT/USER blocks
that `graphify.harness_export.export_claude_harness` renders. Only one target
is supported at launch (``claude``) — multi-target plugin discovery is
explicitly deferred (SEED-002 OQ-5 lock).
"""
from __future__ import annotations

from pathlib import Path

_HERE = Path(__file__).parent


def schema_path(target: str) -> Path:
    """Return the path to a bundled harness schema YAML.

    Only the ``claude`` target is supported at launch; passing anything else
    raises ``ValueError`` so callers fail loudly rather than falling through
    to a surprise filesystem read.
    """
    if target != "claude":
        raise ValueError(
            f"Unknown harness target: {target!r}. Supported: 'claude'."
        )
    return _HERE / f"{target}.yaml"
