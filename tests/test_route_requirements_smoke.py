"""Import smoke for Phase 12 public surface (ROUTE requirements)."""
from __future__ import annotations


def test_imports() -> None:
    from graphify.cache import file_hash
    from graphify.routing import Router, default_router, load_routing_config
    from graphify.routing_audit import RoutingAudit
    from graphify.routing_cost import CostCeilingError, estimate_run_cost, enforce_cost_ceiling
    from graphify.batch import max_tier_route
    from graphify.pipeline import run_corpus

    assert callable(file_hash)
    assert callable(Router)
    assert callable(load_routing_config)
    assert RoutingAudit is not None
    assert callable(estimate_run_cost)
    assert callable(max_tier_route)
    assert callable(run_corpus)
