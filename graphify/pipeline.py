"""Thin pipeline wrapper for `graphify run` (Phase 12)."""
from __future__ import annotations

from pathlib import Path


def run_corpus(target: Path, *, use_router: bool) -> dict:
    """detect → extract (optional Router + audit flush). AST-only structural pass."""
    from graphify.detect import detect
    from graphify.extract import extract
    from graphify.routing import default_router
    from graphify.routing_audit import RoutingAudit

    cwd = Path.cwd()
    if target.is_file():
        paths = [target.resolve()]
    else:
        det = detect(target)
        paths = [Path(p) for p in det["files"].get("code", [])]

    router = default_router() if use_router else None
    audit = RoutingAudit() if use_router else None
    result = extract(paths, router=router, audit=audit)
    if audit is not None:
        dest = audit.flush(cwd / "graphify-out")
        print(f"routing audit -> {dest}")
    return result
