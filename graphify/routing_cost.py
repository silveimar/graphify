"""Pre-flight cost projection (ROUTE-09, Phase 12)."""
from __future__ import annotations

import os
from pathlib import Path

from graphify.routing import Router

# Reuse batch heuristic (chars per token)
_CHARS_PER_TOKEN = 4


class CostCeilingError(Exception):
    """Raised when projected run cost exceeds GRAPHIFY_COST_CEILING."""


def estimate_run_cost(files: list[Path], router: Router) -> int:
    """Rough token estimate × tier weight; no file contents echoed in errors."""
    tier_w = {"trivial": 1, "simple": 2, "complex": 4, "vision": 3}
    total = 0
    for p in files:
        r = router.resolve(p)
        w = tier_w.get(r.tier, 2)
        try:
            sz = p.stat().st_size
        except OSError:
            sz = 1024
        tokens = max(1, sz // _CHARS_PER_TOKEN)
        total += tokens * w
    return int(total)


def enforce_cost_ceiling(files: list[Path], router: Router) -> None:
    raw = os.environ.get("GRAPHIFY_COST_CEILING")
    if not raw:
        return
    ceiling = int(raw)
    est = estimate_run_cost(files, router)
    if est > ceiling:
        raise CostCeilingError(
            f"projected cost estimate {est} exceeds GRAPHIFY_COST_CEILING={ceiling}"
        )
