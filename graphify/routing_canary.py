"""Canary probes for routing quality (ROUTE-08, Phase 12)."""
from __future__ import annotations

import sys
from typing import TextIO


def edge_count(result: dict) -> int:
    return len(result.get("edges", []))


def ratio_ok(cheap_edges: int, expensive_edges: int) -> bool:
    if cheap_edges <= 0:
        return True
    return (expensive_edges / cheap_edges) >= 0.6


def emit_canary_warning_if_needed(
    cheap_edges: int,
    expensive_edges: int,
    *,
    out: TextIO | None = None,
) -> None:
    """Emit stderr warning when edge-count ratio falls below 0.6 (ROUTE-08)."""
    if ratio_ok(cheap_edges, expensive_edges):
        return
    print("routing quality regressed", file=(out or sys.stderr))
